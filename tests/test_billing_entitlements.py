import pytest

from chalicelib import constants
from chalicelib.services.billing import BillingService


class FakeBillingEvents:
    def __init__(self, is_new=True):
        self.is_new = is_new
        self.calls = []
        self.processed = []
        self.failed = []

    def record_event_once(self, event_id, event_type):
        self.calls.append((event_id, event_type))
        return self.is_new

    def mark_event_processed(self, event_id):
        self.processed.append(event_id)

    def mark_event_failed(self, event_id):
        self.failed.append(event_id)


class FakeQuotas:
    def __init__(self):
        self.snapshots = []
        self.customers = {}

    def get_user_quota(self, user_id):
        return self.customers.get(user_id, {"userId": user_id})

    def get_user_quota_by_stripe_customer_id(self, customer_id):
        for quota in self.customers.values():
            if quota.get("stripeCustomerId") == customer_id:
                return quota
        return None

    def update_stripe_customer_id(self, user_id, customer_id):
        quota = self.customers.setdefault(user_id, {"userId": user_id})
        quota["stripeCustomerId"] = customer_id
        return quota

    def apply_subscription_snapshot(self, user_id, snapshot):
        self.snapshots.append((user_id, snapshot))
        quota = self.customers.setdefault(user_id, {"userId": user_id})
        quota.update(snapshot)
        quota["plan"] = (
            constants.USER_PRO_PLAN
            if snapshot["subscriptionStatus"] in constants.PAID_SUBSCRIPTION_STATUSES
            else constants.USER_FREE_PLAN
        )
        return quota


def test_stripe_webhook_event_is_idempotent():
    quotas = FakeQuotas()
    events = FakeBillingEvents(is_new=False)
    service = BillingService(quota_repository=quotas, event_repository=events)

    result = service.handle_subscription_event(
        {
            "id": "evt_123",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_123", "metadata": {"user_id": "user_1"}}},
        }
    )

    assert result == {"status": "duplicate"}
    assert quotas.snapshots == []


@pytest.mark.parametrize(
    ("status", "expected_plan"),
    [
        ("active", constants.USER_PRO_PLAN),
        ("trialing", constants.USER_PRO_PLAN),
        ("past_due", constants.USER_FREE_PLAN),
        ("canceled", constants.USER_FREE_PLAN),
    ],
)
def test_subscription_status_projects_to_entitlement_plan(status, expected_plan):
    quotas = FakeQuotas()
    service = BillingService(
        quota_repository=quotas, event_repository=FakeBillingEvents(is_new=True)
    )

    result = service.handle_subscription_event(
        {
            "id": f"evt_{status}",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": status,
                    "metadata": {"user_id": "user_1"},
                    "current_period_end": 1770000000,
                    "cancel_at_period_end": False,
                    "items": {
                        "data": [
                            {"price": {"id": "price_monthly", "unit_amount": 2000}}
                        ]
                    },
                }
            },
        }
    )

    assert result["plan"] == expected_plan
    assert quotas.snapshots[-1][0] == "user_1"
    assert quotas.snapshots[-1][1]["stripeSubscriptionId"] == "sub_123"


def test_subscription_event_can_resolve_user_from_customer_mapping():
    quotas = FakeQuotas()
    quotas.customers["user_1"] = {"userId": "user_1", "stripeCustomerId": "cus_123"}
    service = BillingService(
        quota_repository=quotas, event_repository=FakeBillingEvents(is_new=True)
    )

    result = service.handle_subscription_event(
        {
            "id": "evt_customer",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "canceled",
                    "metadata": {},
                    "current_period_end": 1770000000,
                    "cancel_at_period_end": False,
                    "items": {"data": []},
                }
            },
        }
    )

    assert result["userId"] == "user_1"
    assert result["plan"] == constants.USER_FREE_PLAN


class FakeStripe:
    class billing_portal:
        class Session:
            @staticmethod
            def create(**kwargs):
                return {"url": "https://billing.stripe.test/portal"}

    class checkout:
        class Session:
            @staticmethod
            def create(**kwargs):
                raise AssertionError("checkout should not run for active subscribers")

    class Customer:
        @staticmethod
        def create(**kwargs):
            raise AssertionError(
                "customer create should not run for active subscribers"
            )


def test_create_checkout_session_routes_active_subscribers_to_portal(monkeypatch):
    quotas = FakeQuotas()
    quotas.customers["user_1"] = {
        "userId": "user_1",
        "stripeCustomerId": "cus_123",
        "subscriptionStatus": "active",
    }
    service = BillingService(
        quota_repository=quotas,
        event_repository=FakeBillingEvents(),
        stripe_client=FakeStripe,
    )
    monkeypatch.setattr(
        "chalicelib.services.billing.config.stripe_price_id_monthly", "price_monthly"
    )
    monkeypatch.setattr(
        "chalicelib.services.billing.config.stripe_success_url",
        "https://app.test/billing/success",
    )
    monkeypatch.setattr(
        "chalicelib.services.billing.config.stripe_cancel_url",
        "https://app.test/billing/cancel",
    )
    monkeypatch.setattr(
        "chalicelib.services.billing.config.stripe_secret_key.get_secret_value",
        lambda: "sk_test",
    )
    monkeypatch.setattr(
        "chalicelib.services.billing.config.frontend_app_url", "https://app.test"
    )

    result = service.create_checkout_session("user_1", email="user@test.com")

    assert result == {"portalUrl": "https://billing.stripe.test/portal"}
