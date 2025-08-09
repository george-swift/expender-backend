from aws_lambda_powertools import Logger
from chalice import Blueprint, NotFoundError

from chalicelib.authorizers import api_gateway_authorizer
from chalicelib.services import QuotaService

logger = Logger(child=True)

quota_router = Blueprint(__name__)
quota_service = QuotaService()

__all__ = ["quota_router"]


@quota_router.route("/quotas", methods=["GET"], authorizer=api_gateway_authorizer)
def get_user_quota():
    user_id = quota_router.current_request.context["authorizer"]["principalId"]
    quota = quota_service.get_user_quota(user_id)

    if not quota:
        raise NotFoundError("Quota not found for the user")

    return quota.api_response
