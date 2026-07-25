from chalicelib.services.quotas import QuotaService

__all__ = ["EntitlementService"]


class EntitlementService:
    """Deep module for premium usage access and SmartScan upload intents."""

    def __init__(
        self,
        quota_service: QuotaService | None = None,
    ):
        self.quota_service = quota_service or QuotaService()

    def assert_can_start_smartscan(self, user_id: str) -> None:
        self.quota_service.check_smart_scan_access(user_id)

    def consume_smartscan_usage(self, user_id: str) -> dict:
        return self.quota_service.increment_smart_scan_count(user_id)
