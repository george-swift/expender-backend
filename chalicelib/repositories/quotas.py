from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import boto3

from chalicelib import constants
from chalicelib.models import config

__all__ = ["Quota", "QuotaRepository"]


class QuotaRepository:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(config.quotas_table_name)

    def get_user_quota(self, user_id: str) -> dict | None:
        """
        Get quota record for a user.

        :param user_id: The user ID to get quota for
        :returns: Quota dictionary or None if not found
        """
        response = self.table.get_item(Key={"userId": user_id})
        return response.get("Item")

    def deactivate_user_quota(self, user_id: str) -> dict:
        """
        Deactivate a user's quota by setting status to deactivated and immediate TTL.

        :param user_id: The user ID to deactivate quota for
        :returns: Updated quota attributes
        """
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        immediate_expiry = int(now.timestamp())

        update_expression = (
            "SET #status = :status, expireAt = :ttl, updatedAt = :timestamp"
        )
        expression_attribute_names = {"#status": "status"}
        expression_attribute_values = {
            ":status": constants.ACCOUNT_STATUS_DEACTIVATED,
            ":ttl": immediate_expiry,
            ":timestamp": timestamp,
        }

        response = self.table.update_item(
            Key={"userId": user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )

        return response.get("Attributes", {})

    def create_new_user_quota(self, user_id: str) -> dict:
        """
        Create a new quota record for a user with default settings.

        :param user_id: The user ID to create quota for
        :returns: Created quota dictionary
        """
        now = datetime.now(timezone.utc)
        expires_at = int((now + timedelta(days=30)).timestamp())
        timestamp = now.isoformat()

        quota = {
            "userId": user_id,
            "status": constants.ACCOUNT_STATUS_ACTIVE,
            "plan": constants.USER_FREE_PLAN,
            "smartScanCount": 0,
            "smartScanLimit": constants.FREE_PLAN_SMART_SCAN_LIMIT,
            "expireAt": expires_at,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }

        try:
            self.table.put_item(
                Item=quota, ConditionExpression="attribute_not_exists(userId)"
            )
            return quota
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            existing_quota = self.get_user_quota(user_id)
            return existing_quota

    def reset_free_user_quota(self, user_id: str, reactivate: bool = False) -> dict:
        """
        Reset a free user's quota to 0 scans and extend expiration.

        :param user_id: The user ID to reset quota for
        :param reactivate: Whether to reactivate a deactivated account (default: False)
        :returns: Updated quota attributes
        """
        now = datetime.now(timezone.utc)
        expires_at = int((now + timedelta(days=30)).timestamp())
        timestamp = now.isoformat()

        update_expression = (
            "SET smartScanCount = :count, expireAt = :ttl, updatedAt = :updatedAt"
        )

        expression_attribute_values = {
            ":status": constants.ACCOUNT_STATUS_ACTIVE,
            ":count": 0,
            ":ttl": expires_at,
            ":updatedAt": timestamp,
        }

        if reactivate:
            condition_expression = "attribute_exists(userId)"
            update_expression += ", #status = :status"
        else:
            condition_expression = "attribute_exists(userId) AND #status = :status"

        response = self.table.update_item(
            Key={"userId": user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression=condition_expression,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes", {})

    def increment_smart_scan_count(self, user_id: str) -> dict:
        """
        Increment the smart scan count for a user with plan limit validation.

        :param user_id: The user ID to increment count for
        :returns: Updated quota attributes
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        update_expression = (
            "SET smartScanCount = smartScanCount + :inc, updatedAt = :updatedAt"
        )

        condition_expression = """
            attribute_exists(userId) AND
            #status = :status AND
            (
                (#plan = :free_plan AND smartScanCount < :free_limit) OR
                (#plan = :pro_plan)
            )
        """

        expression_attribute_values = {
            ":inc": 1,
            ":updatedAt": timestamp,
            ":free_plan": constants.USER_FREE_PLAN,
            ":pro_plan": constants.USER_PRO_PLAN,
            ":free_limit": constants.FREE_PLAN_SMART_SCAN_LIMIT,
            ":status": constants.ACCOUNT_STATUS_ACTIVE,
        }

        try:
            response = self.table.update_item(
                Key={"userId": user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames={"#status": "status", "#plan": "plan"},
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression=condition_expression,
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes", {})
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            current_quota = self.get_user_quota(user_id)
            if (
                not current_quota
                or current_quota.get("status") != constants.ACCOUNT_STATUS_ACTIVE
            ):
                raise ValueError("User quota not found or account has been deactivated")

            raise ValueError("User has reached their Smart Scan limit")


@dataclass
class Quota:
    status: str
    plan: str
    smart_scan_count: int
    smart_scan_limit: int | str
    remaining_scans: int | str
    expiration_date: str
    can_scan: bool

    @property
    def api_response(self) -> dict:
        return {
            "status": self.status,
            "plan": self.plan,
            "limit": self.smart_scan_limit,
            "used": self.smart_scan_count,
            "remaining": self.remaining_scans,
        }
