import hashlib

import boto3

from chalicelib.models import config

__all__ = ["SmartScanRepository"]


class SmartScanRepository:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(config.smartscans_table_name)

    def generate_scan_id(self, user_id: str, object_key: str) -> str:
        """
        Generate a deterministic `scanId` for a Smart Scan.

        This ensures the same object_key for the same user always generates
        the same `scanId`, providing idempotency.

        :param user_id: The user ID who owns the scan
        :param object_key: The S3 object key
        :returns: A deterministic `scanId`
        """
        content = f"{user_id}:{object_key}"
        hash_digest = hashlib.sha256(content.encode()).hexdigest()[:12]

        return f"ssc_{hash_digest}"

    def set_smartscan_expiration(
        self, user_id: str, scan_id: str, time: int = 0
    ) -> dict:
        """
        Set the TTL (expiration time) for a smartscan record.

        :param user_id: The user ID who owns the smartscan
        :param scan_id: The scan ID to update
        :param time: The expiration timestamp (default: 0 for immediate expiration)
        :returns: Updated smartscan record
        """
        update_expression = "SET expireAt = :ttl"
        expression_attribute_values = {":ttl": time}

        updated_smartscan = self.table.update_item(
            Key={"userId": user_id, "scanId": scan_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression="attribute_exists(scanId)",
            ReturnValues="ALL_NEW",
        )

        return updated_smartscan

    def delete_smartscan(self, user_id: str, scan_id: str) -> dict:
        """
        Delete a smartscan record from DynamoDB.

        :param user_id: The user ID who owns the smartscan
        :param scan_id: The scan ID to delete
        :returns: The deleted smartscan data
        """
        response = self.table.delete_item(
            Key={"userId": user_id, "scanId": scan_id},
            ConditionExpression="attribute_exists(scanId)",
            ReturnValues="ALL_OLD",
        )
        return response.get("Attributes", {})

    def get_user_smartscans(
        self, user_id: str, limit: int = 25, last_evaluated_key: dict = None
    ) -> list:
        """
        Get smartscans for a user with pagination support.

        :param user_id: The user ID to get smartscans for
        :param limit: Maximum number of items to return
        :param last_evaluated_key: Key to start pagination from
        :return: List of smartscan items
        """
        query_kwargs = {
            "KeyConditionExpression": "userId = :user_id",
            "ExpressionAttributeValues": {":user_id": user_id},
            "Limit": limit,
        }

        if last_evaluated_key:
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = self.table.query(**query_kwargs)
        return response.get("Items", [])

    @property
    def table_name(self) -> str:
        """
        Get the table name for batch operations.

        :returns: The DynamoDB table name for smartscans
        """
        return config.smartscans_table_name
