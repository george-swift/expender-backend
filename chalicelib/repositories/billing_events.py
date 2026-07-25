from datetime import datetime, timedelta, timezone

import boto3

from chalicelib.models import config

__all__ = ["BillingEventRepository"]


class BillingEventRepository:
    """Repository for idempotent third-party billing event processing."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(config.billing_events_table_name)

    def record_event_once(self, event_id: str, event_type: str) -> bool:
        """
        Record a billing event if it has not been processed.

        :returns: True when this invocation owns processing; False for replays.
        """
        now = datetime.now(timezone.utc)
        item = {
            "eventId": event_id,
            "provider": "stripe",
            "eventType": event_type,
            "status": "processing",
            "processedAt": now.isoformat(),
            "expireAt": int((now + timedelta(days=90)).timestamp()),
        }

        try:
            self.table.put_item(
                Item=item, ConditionExpression="attribute_not_exists(eventId)"
            )
            return True
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            try:
                self.table.update_item(
                    Key={"eventId": event_id},
                    UpdateExpression=(
                        "SET #status = :processing, eventType = :eventType, "
                        "processedAt = :processedAt"
                    ),
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":failed": "failed",
                        ":processing": "processing",
                        ":eventType": event_type,
                        ":processedAt": now.isoformat(),
                    },
                    ConditionExpression="#status = :failed",
                )
                return True
            except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
                return False

    def mark_event_processed(self, event_id: str) -> None:
        self._set_event_status(event_id, "processed")

    def mark_event_failed(self, event_id: str) -> None:
        self._set_event_status(event_id, "failed")

    def _set_event_status(self, event_id: str, status: str) -> None:
        self.table.update_item(
            Key={"eventId": event_id},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": status},
            ConditionExpression="attribute_exists(eventId)",
        )
