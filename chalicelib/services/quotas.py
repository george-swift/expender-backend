from datetime import datetime, timezone

from aws_lambda_powertools import Logger

from chalicelib import constants
from chalicelib.middleware.exceptions import QuotaExceededError
from chalicelib.repositories.quotas import Quota, QuotaRepository

logger = Logger(child=True)

__all__ = ["QuotaService"]


class QuotaService:
    """Service for managing user quotas in the application."""

    def __init__(self):
        self.db = QuotaRepository()

        self.plan_configs = {
            constants.USER_FREE_PLAN: {
                "display_name": "Free Plan",
                "smart_scan_limit": constants.FREE_PLAN_SMART_SCAN_LIMIT,
                "is_unlimited": False,
            },
            constants.USER_PRO_PLAN: {
                "display_name": "Pro Plan",
                "smart_scan_limit": constants.PRO_PLAN_SMART_SCAN_LIMIT,
                "is_unlimited": True,
            },
        }

    def create_user_quota(self, user_id: str) -> Quota:
        """
        Create a new user quota with default settings.

        :param user_id: The user ID to create quota for
        :returns: The created quota object
        """
        new_quota = self.db.create_new_user_quota(user_id)
        return new_quota

    def deactivate_user_quota(self, user_id: str) -> None:
        """
        Deactivate a user's quota when their account is deleted.

        :param user_id: The user ID to deactivate quota for
        :returns: The deactivated user ID
        """
        deactivated_user_quota = self.db.deactivate_user_quota(user_id)
        return deactivated_user_quota.get("userId")

    def get_user_quota(self, user_id: str) -> Quota | None:
        """
        Get formatted quota information for a user including plan details and limits.

        :param user_id: The user ID to get quota information for
        :returns: Quota object with formatted plan information or None if not found
        """
        quota = self.db.get_user_quota(user_id)

        if not quota:
            logger.warning(f"No quota found for user: {user_id}")
            return None

        plan = quota.get("plan")
        plan_config = self.plan_configs.get(
            plan, self.plan_configs[constants.USER_FREE_PLAN]
        )

        current_count = quota.get("smartScanCount", 0)

        if plan_config["is_unlimited"]:
            remaining_scans = "Unlimited"
            display_limit = "Unlimited"
        else:
            limit = plan_config["smart_scan_limit"]
            remaining_scans = max(0, limit - current_count)
            display_limit = limit

        return Quota(
            status=quota.get("status"),
            plan=plan_config["display_name"],
            smart_scan_count=current_count,
            smart_scan_limit=display_limit,
            remaining_scans=remaining_scans,
            expiration_date=self._format_reset_date(quota.get("expireAt")),
            can_scan=self._can_scan(current_count, plan_config),
        )

    def check_smart_scan_access(self, user_id: str) -> bool:
        """
        Check if a user has access to perform smart scans based on their quota.

        :param user_id: The user ID to check access for
        :returns: True if user can perform smart scans, False otherwise
        """
        quota = self.db.get_user_quota(user_id)

        if not quota:
            logger.warning(f"No quota found for user: {user_id}")
            return False

        if quota.get("status") != constants.ACCOUNT_STATUS_ACTIVE:
            raise QuotaExceededError(user_id, "inactive_account")

        expires_at = quota.get("expireAt")

        if expires_at:
            expires_at = int(expires_at)
            if datetime.fromtimestamp(expires_at, tz=timezone.utc) < datetime.now(
                timezone.utc
            ):
                raise QuotaExceededError(user_id, "expired_quota")

        plan = quota.get("plan")
        current_count = quota.get("smartScanCount", 0)

        plan_config = self.plan_configs.get(
            plan, self.plan_configs[constants.USER_FREE_PLAN]
        )

        if not self._can_scan(current_count, plan_config):
            raise QuotaExceededError(user_id, f"{plan}_plan_limit")

        return True

    def increment_smart_scan_count(self, user_id: str) -> dict:
        """
        Increment the smart scan count for a user.

        :param user_id: The user ID to increment count for
        :returns: Updated quota dictionary
        """
        updated_quota = self.db.increment_smart_scan_count(user_id)
        return updated_quota

    def _format_reset_date(self, reset_timestamp) -> str:
        """
        Format reset timestamp to ISO string.

        :param reset_timestamp: The timestamp to format
        :returns: ISO formatted date string or None if timestamp is invalid
        """
        if not reset_timestamp:
            return None

        reset_timestamp = int(reset_timestamp)
        return datetime.fromtimestamp(reset_timestamp, tz=timezone.utc).isoformat()

    def _can_scan(self, current_count: int, plan_config: dict) -> bool:
        """
        Check if user can perform another Smart Scan based on their plan limits.

        :param current_count: Current scan count for the user
        :param plan_config: Configuration dictionary for the user's plan
        :returns: True if user can scan, False if limit reached
        """
        if plan_config["is_unlimited"]:
            return True
        return current_count < plan_config["smart_scan_limit"]
