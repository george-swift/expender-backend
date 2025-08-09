import time

from aws_lambda_powertools import Logger
from chalice import Blueprint
from openai import InternalServerError

from chalicelib import constants
from chalicelib.models import SmartScanResult, config
from chalicelib.resources import S3, AppSync
from chalicelib.services import QuotaService, SmartScanService

logger = Logger(child=True)

appsync = AppSync()
s3 = S3()
smartscan_service = SmartScanService()
quota_service = QuotaService()

bucket_event = Blueprint(__name__)

__all__ = ["bucket_event"]


@bucket_event.on_s3_event(
    bucket=config.assets_bucket_name,
    events=["s3:ObjectCreated:*"],
    prefix="smartscans/",
)
def bucket_event_handler(event):
    """
    Handle S3 object creation events for the Smart Scans feature.

    When a user uploads a receipt for a smart scan, this function is triggered,
    the Smart Scan service intelligently extracts relevant data, results are saved in the database and published to the user.
    """
    try:
        start_time = time.time()

        object_key = event.key

        headers = s3.get_headers(object_key)
        content_type = headers.get("content-type")
        user_id = headers.get("x-amz-meta-user-id")
        encrypted_token = headers.get("x-amz-meta-token")

        if not user_id:
            logger.warning(f"Missing user ID in headers for object: {object_key}")
            raise ValueError("User ID not found in headers")

        if content_type not in constants.ALLOWED_CONTENT_TYPES:
            logger.warning(
                f"Unsupported content type: {content_type} for object: {object_key}"
            )
            raise ValueError("Unsupported content type")

        if not encrypted_token:
            logger.warning(f"Missing auth token in headers for object: {object_key}")
            raise ValueError("Auth token not found in headers")

        auth_token = s3.decrypt_token(encrypted_token)

        if not auth_token:
            logger.error(f"Token decryption failed for object {object_key}: {str(e)}")
            raise ValueError("Auth token decryption failed")

        raw_data_extracted = smartscan_service.analyze_expense(object_key)
        if not raw_data_extracted:
            logger.warning(f"No data extracted from object: {object_key}")
            raise InternalServerError("No data extracted from the receipt")

        structured_data = smartscan_service.structure_response(raw_data_extracted)
        if not structured_data:
            logger.warning(f"Failed to structure data for object: {object_key}")
            raise InternalServerError("Failed to structure data from the receipt")

        processing_time = time.time() - start_time
        logger.info(
            f"Smart scan processed {object_key} in {processing_time:.2f} seconds with {structured_data.get('confidence', 0)}% confidence"
        )

        try:
            validated_data = SmartScanResult(**structured_data).model_dump()
        except Exception as e:
            raise ValueError(f"Failed to validate structured data: {str(e)}")
        else:
            quota_service.increment_smart_scan_count(user_id)

            appsync.publish_smart_scan_result(
                user_id=user_id,
                token=auth_token,
                object_key=object_key,
                result=validated_data,
            )
    except Exception as e:
        logger.exception(f"Error processing S3 event for object {event.key}: {str(e)}")
        raise
