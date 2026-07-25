from aws_lambda_powertools import Logger
from chalice import Blueprint, Response
from svix.webhooks import Webhook, WebhookVerificationError

from chalicelib.models import config
from chalicelib.resources import EventBridge
from chalicelib.services import QuotaService
from chalicelib.services.billing import BillingService

logger = Logger(child=True)
quota_service = QuotaService()
billing_service = BillingService()
event_bridge = EventBridge()
webhooks_router = Blueprint(__name__)

__all__ = ["webhooks_router"]


@webhooks_router.route("/webhooks", methods=["POST"], authorizer=None)
def handle_webhooks():
    """
    Handle webhook events from Clerk auth service.

    Currently supported events and subsequent actions:
    - user.created: Creates a new user entry in the quotas table
    - user.deleted: Removes user data from databases and object storage
    """
    headers = webhooks_router.current_request.headers
    body = webhooks_router.current_request._body

    try:
        wh = Webhook(config.clerk_webhook_signing_secret.get_secret_value())
        payload = wh.verify(body, headers)

        event_type = payload.get("type")
        user_id = payload.get("data", {}).get("id")

        if not user_id:
            logger.warning(
                f"Missing user ID in webhook data for event type: {event_type}"
            )
            return Response(
                status_code=400, body={"message": "Missing user ID in webhook data"}
            )

        if event_type == "user.created":
            try:
                quota = quota_service.create_user_quota(user_id)
            except Exception as e:
                logger.error(f"Failed to create quota for user {user_id}: {str(e)}")
                return Response(
                    status_code=500, body={"message": "Failed to create user quota"}
                )
            else:
                return Response(status_code=201, body={"quota": quota})
        elif event_type == "user.deleted":
            response = event_bridge.put_events(
                source="clerk.webhook",
                detail_type="UserDeleted",
                detail={"user_id": user_id},
            )
            if response["success"]:
                return Response(status_code=204, body="")
            else:
                return Response(
                    status_code=500, body={"message": "Failed to process user deletion"}
                )
        else:
            logger.info(f"Unsupported event type: {event_type}")
            return Response(status_code=400, body={"message": "Unsupported event type"})
    except WebhookVerificationError:
        logger.warning("Clerk webhook signature verification failed")
        return Response(status_code=401, body={"message": "Invalid webhook signature"})


@webhooks_router.route("/webhooks/stripe", methods=["POST"], authorizer=None)
def handle_stripe_webhooks():
    """
    Handle Stripe billing webhooks.

    Supported events:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    """
    headers = webhooks_router.current_request.headers
    raw_body = webhooks_router.current_request._body
    signature = headers.get("stripe-signature")

    if not signature:
        return Response(status_code=400, body={"message": "Missing Stripe signature"})

    try:
        event = billing_service.construct_webhook_event(raw_body, signature)
    except ValueError:
        logger.warning("Invalid Stripe webhook payload")
        return Response(status_code=400, body={"message": "Invalid webhook payload"})
    except Exception as exc:
        if exc.__class__.__name__ == "SignatureVerificationError":
            logger.warning("Stripe webhook signature verification failed")
            return Response(
                status_code=401, body={"message": "Invalid webhook signature"}
            )
        raise

    event_type = event.get("type")
    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        billing_service.handle_subscription_event(event)

    return Response(status_code=200, body={"received": True})
