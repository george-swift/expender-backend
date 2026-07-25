from aws_lambda_powertools import Logger
from chalice import BadRequestError, Blueprint, Response

from chalicelib.authorizers import api_gateway_authorizer
from chalicelib.services.billing import BillingService

logger = Logger(child=True)
billing_router = Blueprint(__name__)
billing_service = BillingService()

__all__ = ["billing_router"]


def get_authorized_user(current_request):
    return current_request.context["authorizer"]["principalId"]


@billing_router.route(
    "/billing/checkout-session", methods=["POST"], authorizer=api_gateway_authorizer
)
def create_checkout_session():
    user_id = get_authorized_user(billing_router.current_request)
    payload = billing_router.current_request.json_body or {}

    try:
        session = billing_service.create_checkout_session(
            user_id=user_id, email=payload.get("email")
        )
    except ValueError as exc:
        raise BadRequestError(str(exc))

    return Response(body=session, status_code=201)


@billing_router.route(
    "/billing/portal-session", methods=["POST"], authorizer=api_gateway_authorizer
)
def create_portal_session():
    user_id = get_authorized_user(billing_router.current_request)

    try:
        session = billing_service.create_portal_session(user_id)
    except ValueError as exc:
        raise BadRequestError(str(exc))

    return Response(body=session, status_code=201)


@billing_router.route(
    "/billing/subscription", methods=["GET"], authorizer=api_gateway_authorizer
)
def get_subscription():
    user_id = get_authorized_user(billing_router.current_request)
    quota = billing_service.quotas.get_user_quota(user_id)

    if not quota:
        raise BadRequestError("User quota not found")

    return {
        "plan": quota.get("plan"),
        "stripeCustomerId": quota.get("stripeCustomerId"),
        "stripeSubscriptionId": quota.get("stripeSubscriptionId"),
        "subscriptionStatus": quota.get("subscriptionStatus"),
        "stripePriceId": quota.get("stripePriceId"),
        "currentPeriodEnd": quota.get("currentPeriodEnd"),
        "cancelAtPeriodEnd": quota.get("cancelAtPeriodEnd", False),
    }
