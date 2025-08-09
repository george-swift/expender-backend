import json

import boto3
from aws_lambda_powertools import Logger

from chalicelib.models import config

__all__ = ["EventBridge"]

logger = Logger(child=True)


class EventBridge:
    def __init__(self):
        self._client = boto3.client("events")

    def put_events(self, source: str, detail_type: str, detail: dict) -> dict:
        """
        Put an event to EventBridge for processing.

        :param source: List of event source identifiers
        :param detail_type: The type of event being published
        :param detail: Dictionary containing event details
        :returns: Dictionary with success/error status
        """
        try:
            response = self._client.put_events(
                Entries=[
                    {
                        "Source": source,
                        "DetailType": detail_type,
                        "Detail": json.dumps(detail),
                        "EventBusName": config.events_bus_name,
                    }
                ]
            )

            failed_entry_count = response.get("FailedEntryCount", 0)
            if failed_entry_count > 0:
                failed_entries = [
                    entry
                    for entry in response.get("Entries", [])
                    if "ErrorCode" in entry
                ]
                error_details = "; ".join(
                    [
                        f"{entry['ErrorCode']}: {entry['ErrorMessage']}"
                        for entry in failed_entries
                    ]
                )

                logger.error(
                    {
                        "detail_type": detail_type,
                        "source": source,
                        "error": error_details,
                    }
                )
                return {"success": False, "error": True}

            return {"success": True, "error": False}
        except Exception as e:
            logger.error(
                {
                    "detail_type": detail_type,
                    "source": source,
                    "error": str(e),
                }
            )
            return {"success": False, "error": True}
