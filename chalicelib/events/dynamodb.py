from aws_lambda_powertools import Logger
from chalice import Blueprint

from chalicelib.models import config
from chalicelib.repositories import SmartScanRepository

logger = Logger(child=True)
smartscans = SmartScanRepository()
expense_stream = Blueprint(__name__)

__all__ = ["expense_stream"]


@expense_stream.on_dynamodb_record(stream_arn=config.expenses_table_stream_arn)
def expense_stream_handler(event):
    for record in event:
        try:
            if record.event_name == "INSERT":
                user_id = record.new_image.get("userId", {}).get("S")
                scan_id = record.new_image.get("scanId", {}).get("S")

                if not user_id or not scan_id:
                    logger.warning(
                        f"Missing userId or scanId in record {record.event_id}"
                    )
                    continue

                updated_smartscan = smartscans.set_smartscan_expiration(
                    user_id, scan_id
                )

                if not updated_smartscan:
                    logger.warning(f"Failed to update expiration for scan {scan_id}")
            if record.event_name == "REMOVE":
                user_id = record.old_image.get("userId", {}).get("S")
                scan_id = record.old_image.get("scanId", {}).get("S")

                if not user_id or not scan_id:
                    logger.warning(
                        f"Missing userId or scanId in record {record.event_id}"
                    )
                    continue

                deleted_smartscan = smartscans.delete_smartscan(user_id, scan_id)

                if not deleted_smartscan:
                    logger.warning(
                        f"Failed to delete scan {scan_id} for user {user_id}"
                    )
        except Exception as e:
            logger.error(
                f"Error processing DynamoDB stream event {record.event_id}: {str(e)}"
            )
            raise
