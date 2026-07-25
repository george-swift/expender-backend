from typing import Any

from aws_lambda_powertools import Logger

from chalicelib import constants
from chalicelib.models import config
from chalicelib.repositories import BillingEventRepository, QuotaRepository

logger = Logger(child=True)

__all__ = ["BillingService"]


class BillingService:
    """Stripe billing operations and subscription entitlement projection."""

    def __init__(
        self,
        quota_repository: QuotaRepository | None = None,
        event_repository: BillingEventRepository | None = None,
        stripe_client: Any | None = None,
    ):
        self.quotas = quota_repository or QuotaRepository()
        self.events = event_repository or BillingEventRepository()
        self._stripe = stripe_client

    @property
    def stripe(self):
        if self._stripe is None:
            import stripe

            stripe.api_key = config.stripe_secret_key.get_secret_value()
            self._stripe = stripe
        return self._stripe

    def create_checkout_session(self, user_id: str, email: str | None = None) -> dict:
        self._assert_stripe_configured()
        quota = self.quotas.get_user_quota(user_id)
        if not quota:
            raise ValueError("User quota not found")

        if quota.get("subscriptionStatus") in constants.PAID_SUBSCRIPTION_STATUSES:
            if quota.get("stripeCustomerId"):
                return self.create_portal_session(user_id)
            raise ValueError(
                "You already have an active Pro subscription. Use Manage billing."
            )

        try:
            customer_id = quota.get("stripeCustomerId")
            if not customer_id:
                customer = self.stripe.Customer.create(
                    email=email,
                    metadata={"user_id": user_id},
                )
                customer_id = (
                    customer["id"] if isinstance(customer, dict) else customer.id
                )
                self.quotas.update_stripe_customer_id(user_id, customer_id)

            session = self.stripe.checkout.Session.create(
                mode="subscription",
                customer=customer_id,
                line_items=[{"price": config.stripe_price_id_monthly, "quantity": 1}],
                success_url=config.stripe_success_url,
                cancel_url=config.stripe_cancel_url,
                client_reference_id=user_id,
                subscription_data={"metadata": {"user_id": user_id}},
                metadata={"user_id": user_id},
                allow_promotion_codes=True,
            )
            return {
                "checkoutUrl": (
                    session["url"] if isinstance(session, dict) else session.url
                )
            }
        except Exception as exc:
            raise ValueError(self._stripe_error_message(exc, "checkout")) from exc

    def create_portal_session(self, user_id: str) -> dict:
        quota = self.quotas.get_user_quota(user_id)
        if not quota or not quota.get("stripeCustomerId"):
            raise ValueError("Stripe customer not found")

        try:
            session = self.stripe.billing_portal.Session.create(
                customer=quota["stripeCustomerId"],
                return_url=f"{config.frontend_app_url.rstrip('/')}/settings",
            )
            return {
                "portalUrl": (
                    session["url"] if isinstance(session, dict) else session.url
                )
            }
        except Exception as exc:
            raise ValueError(self._stripe_error_message(exc, "portal")) from exc

    def construct_webhook_event(self, raw_body: bytes, signature: str):
        self._assert_webhook_configured()
        return self.stripe.Webhook.construct_event(
            raw_body,
            signature,
            config.stripe_webhook_secret.get_secret_value(),
        )

    def handle_subscription_event(self, event: dict) -> dict:
        event_id = event.get("id")
        event_type = event.get("type")

        if not event_id or not event_type:
            raise ValueError("Invalid Stripe event")

        event_started = self.events.record_event_once(event_id, event_type)
        if not event_started:
            return {"status": "duplicate"}

        try:
            subscription = event.get("data", {}).get("object", {})
            user_id = self._resolve_subscription_user_id(subscription)
            if not user_id:
                raise ValueError("Unable to resolve subscription user")

            snapshot = self._subscription_snapshot(subscription)
            updated_quota = self.quotas.apply_subscription_snapshot(user_id, snapshot)
            self.events.mark_event_processed(event_id)
            return {
                "status": "processed",
                "userId": user_id,
                "plan": updated_quota.get("plan"),
                "subscriptionStatus": snapshot["subscriptionStatus"],
            }
        except Exception:
            self.events.mark_event_failed(event_id)
            raise

    def _subscription_snapshot(self, subscription: dict) -> dict:
        price_id = None
        items = subscription.get("items", {}).get("data", [])
        if items:
            price = items[0].get("price") or {}
            price_id = price.get("id")

        status = subscription.get("status")
        return {
            "stripeCustomerId": subscription.get("customer"),
            "stripeSubscriptionId": subscription.get("id"),
            "subscriptionStatus": status,
            "stripePriceId": price_id,
            "currentPeriodEnd": subscription.get("current_period_end"),
            "cancelAtPeriodEnd": subscription.get("cancel_at_period_end", False),
        }

    def _resolve_subscription_user_id(self, subscription: dict) -> str | None:
        metadata = subscription.get("metadata") or {}
        user_id = metadata.get("user_id")
        if user_id:
            return user_id

        customer_id = subscription.get("customer")
        if not customer_id:
            return None

        quota = self.quotas.get_user_quota_by_stripe_customer_id(customer_id)
        return quota.get("userId") if quota else None

    def _stripe_error_message(self, exc: Exception, operation: str) -> str:
        error_type = type(exc).__name__
        message = str(exc).strip() or "Unknown Stripe error"

        if "Stripe" in error_type or "stripe" in message.lower():
            logger.warning(
                "Stripe %s failed",
                operation,
                extra={"error_type": error_type, "error": message},
            )
            if "No such price" in message:
                return "Stripe price is not configured correctly"
            if "No such customer" in message:
                return "Stripe customer could not be found"
            if "Invalid API Key" in message or "api_key" in message.lower():
                return "Stripe secret key is not configured correctly"
            return f"Unable to start Stripe {operation}. Please try again."

        return message

    def _assert_stripe_configured(self) -> None:
        if not config.stripe_price_id_monthly:
            raise ValueError("Stripe monthly price ID is not configured")
        if not config.stripe_success_url or not config.stripe_cancel_url:
            raise ValueError("Stripe checkout URLs are not configured")
        if not config.stripe_secret_key.get_secret_value():
            raise ValueError("Stripe secret key is not configured")

    def _assert_webhook_configured(self) -> None:
        if not config.stripe_webhook_secret.get_secret_value():
            raise ValueError("Stripe webhook secret is not configured")
