from aws_lambda_powertools import Logger
from chalice import Blueprint, Response
from svix.webhooks import Webhook, WebhookVerificationError

from chalicelib.models import config
from chalicelib.resources import EventBridge
from chalicelib.services import QuotaService

logger = Logger(child=True)
quota_service = QuotaService()
event_bridge = EventBridge()
webhooks_router = Blueprint(__name__)

__all__ = ["webhooks_router"]


@webhooks_router.route("/webhooks", methods=["POST"], authorizer=None)
def handle_webhooks():
    """
    Handle webhook events from Clerk auth service.

    Currently supported events and subsequent actions:
    - user.created: Creates a new user entry in the quotas table
    - user.deleted: Removes user data from databases and object storage
    """
    headers = webhooks_router.current_request.headers
    body = webhooks_router.current_request._body

    try:
        wh = Webhook(config.clerk_webhook_signing_secret.get_secret_value())
        payload = wh.verify(body, headers)

        event_type = payload.get("type")
        user_id = payload.get("data", {}).get("id")

        if not user_id:
            logger.warning(
                f"Missing user ID in webhook data for event type: {event_type}"
            )
            return Response(
                status_code=400, body={"message": "Missing user ID in webhook data"}
            )

        if event_type == "user.created":
            try:
                quota = quota_service.create_user_quota(user_id)
            except Exception as e:
                logger.error(f"Failed to create quota for user {user_id}: {str(e)}")
                return Response(
                    status_code=500, body={"message": "Failed to create user quota"}
                )
            else:
                return Response(status_code=201, body={"quota": quota})
        elif event_type == "user.deleted":
            response = event_bridge.put_events(
                source="clerk.webhook",
                detail_type="UserDeleted",
                detail={"user_id": user_id},
            )
            if response["success"]:
                return Response(status_code=204, body="")
            else:
                return Response(
                    status_code=500, body={"message": "Failed to process user deletion"}
                )
        else:
            logger.info(f"Unsupported event type: {event_type}")
            return Response(status_code=400, body={"message": "Unsupported event type"})
    except WebhookVerificationError as e:
        logger.error(f"Webhook verification failed: {str(e)}")
        return Response(status_code=500, body={"message": "Invalid webhook signature"})
