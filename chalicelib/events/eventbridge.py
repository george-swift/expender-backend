import json
import time

from aws_lambda_powertools import Logger
from chalice import Blueprint

from chalicelib.resources import S3, EventBridge, StateMachine
from chalicelib.services import ExpenseService, QuotaService, SmartScanService

logger = Logger(child=True)
expense_service = ExpenseService()
quota_service = QuotaService()
smartscan_service = SmartScanService()

event_bridge = EventBridge()
step_functions = StateMachine()
s3 = S3()

__all__ = ["account_lifecycle"]

account_lifecycle = Blueprint(__name__)

BATCH_WRITE_SIZE = 25  # DynamoDB batch write limit


@account_lifecycle.lambda_function()
def deleted_account_handler(event, context):
    """
    Handle deleted account events.
    This function is triggered by EventBridge when a user account is deleted.
    """
    user_id = event.get("detail", {}).get("user_id")

    if not user_id:
        raise ValueError("Missing user_id in event detail")

    try:
        # Deactivate user quota first
        deactivated_quota_id = quota_service.deactivate_user_quota(user_id)

        if not deactivated_quota_id:
            logger.warning(
                "Failed to deactivate user quota", extra={"user_id": user_id}
            )

        # Find the Step Function state machine ARN
        state_machine_arn = step_functions.find("user-data-deletion-workflow")

        if not state_machine_arn:
            raise RuntimeError("Step Function state machine not found")

        # Start the Step Function execution
        execution_input = json.dumps(
            {
                "userId": user_id,
                "deletionStartTime": int(time.time()),
                "lastEvaluatedKey": None,
            }
        )

        execution_arn = step_functions.start(state_machine_arn, execution_input)

        logger.info(
            "User data deletion workflow initiated",
            extra={
                "user_id": user_id,
                "execution_arn": execution_arn,
            },
        )

        return {
            "userId": user_id,
            "executionArn": execution_arn,
            "status": "workflow_started",
        }

    except Exception:
        raise


@account_lifecycle.lambda_function()
def initialize_deletion(event, context):
    """
    Initialize the user data deletion process.
    Log the start of deletion and validate the user exists.
    """
    user_id = event.get("userId")

    if not user_id:
        raise ValueError("Missing userId in event")

    logger.info(
        "Starting user data deletion process",
        extra={
            "user_id": user_id,
            "timestamp": event.get("deletionStartTime"),
        },
    )

    try:
        smartscan_batch = smartscan_service.get_smartscans_batch(user_id, limit=1)
        expense_batch = expense_service.get_expenses_batch(user_id, limit=1)

        logger.info(
            "User data assessment complete",
            extra={
                "user_id": user_id,
                "estimated_smartscans": len(smartscan_batch["items"]),
                "estimated_expenses": len(expense_batch["items"]),
            },
        )

    except Exception as e:
        logger.warning(
            "Could not assess user data, proceeding with deletion",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )

    return {
        "userId": user_id,
        "deletionStartTime": event.get("deletionStartTime"),
        "status": "initialized",
    }


@account_lifecycle.lambda_function()
def delete_smartscans_batch(event, context):
    """
    Delete Smart Scans in batches to scale.
    Also deletes associated S3 objects for complete cleanup.
    Returns `hasMore` flag to indicate if more iterations are needed.
    """
    user_id = event.get("userId")
    last_evaluated_key = event.get("lastEvaluatedKey")
    batch_size = BATCH_WRITE_SIZE

    if not user_id:
        raise ValueError("Missing userId in event")

    try:
        batch_result = smartscan_service.get_smartscans_batch(
            user_id, limit=batch_size, last_evaluated_key=last_evaluated_key
        )
        smartscans = batch_result["items"]

        if not smartscans:
            return {
                "userId": user_id,
                "hasMore": False,
                "deletedCount": 0,
                "s3ObjectsDeleted": 0,
                "lastEvaluatedKey": None,
            }

        s3_deleted_count = 0
        for smartscan in smartscans:
            object_key = smartscan.get("objectKey")
            if object_key:
                try:
                    s3.delete_object(object_key)
                    s3_deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete S3 object {object_key}: {str(e)}")

        deletion_result = smartscan_service.delete_smartscans_batch(
            user_id, limit=batch_size, last_evaluated_key=last_evaluated_key
        )

        logger.info(
            "Smart Scans batch deletion with S3 cleanup",
            extra={
                "user_id": user_id,
                "deleted_count": deletion_result["deletedCount"],
                "s3_objects_deleted": s3_deleted_count,
                "has_more": deletion_result["hasMore"],
            },
        )

        return {
            "userId": user_id,
            "hasMore": deletion_result["hasMore"],
            "deletedCount": deletion_result["deletedCount"],
            "s3ObjectsDeleted": s3_deleted_count,
            "lastEvaluatedKey": deletion_result["lastEvaluatedKey"],
        }

    except Exception:
        raise


@account_lifecycle.lambda_function()
def mark_expenses_for_deletion(event, context):
    """
    Mark expenses for deletion by removing scanId and setting TTL to now.
    This prevents DynamoDB stream conflicts while enabling TTL-based cleanup.
    """
    user_id = event.get("userId")
    last_evaluated_key = event.get("lastEvaluatedKey")
    batch_size = BATCH_WRITE_SIZE

    if not user_id:
        raise ValueError("Missing userId in event")

    try:
        marking_result = expense_service.mark_expenses_for_ttl_deletion(
            user_id, limit=batch_size, last_evaluated_key=last_evaluated_key
        )

        logger.info(
            "Expenses batch marked for deletion",
            extra={
                "user_id": user_id,
                "marked_count": marking_result["markedCount"],
                "has_more": marking_result["hasMore"],
            },
        )

        return {
            "userId": user_id,
            "hasMore": marking_result["hasMore"],
            "markedCount": marking_result["markedCount"],
            "lastEvaluatedKey": marking_result["lastEvaluatedKey"],
        }

    except Exception:
        raise


@account_lifecycle.lambda_function()
def complete_deletion(event, context):
    """
    Complete the user data deletion process.
    Log completion and optionally publish completion event.
    """
    user_id = event.get("userId")
    deletion_start_time = event.get("deletionStartTime")

    if not user_id:
        raise ValueError("Missing userId in event")

    try:
        completion_time = int(time.time())
        duration = (
            completion_time - deletion_start_time if deletion_start_time else None
        )

        logger.info(
            "User data deletion completed successfully",
            extra={
                "user_id": user_id,
                "deletion_start_time": deletion_start_time,
                "completion_time": completion_time,
                "duration_seconds": duration,
            },
        )

        # Publish user deletion completion event for future tracking
        try:
            event_bridge.put_events(
                source=["user.deletion"],
                detail_type="UserDeletionCompleted",
                detail={
                    "user_id": user_id,
                    "completion_time": completion_time,
                    "duration_seconds": duration,
                },
            )
            logger.info(
                "User deletion completion event published",
                extra={
                    "user_id": user_id,
                },
            )
        except Exception as e:
            logger.warning(
                "Failed to publish completion event",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                },
            )

        return {
            "userId": user_id,
            "status": "completed",
            "completionTime": completion_time,
            "duration": duration,
        }

    except Exception:
        raise
