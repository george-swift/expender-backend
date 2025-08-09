from chalice import BadRequestError, Blueprint, Response

from chalicelib.authorizers import api_gateway_authorizer
from chalicelib.resources import S3
from chalicelib.services import QuotaService

s3 = S3()
smartscan_router = Blueprint(__name__)
quota_service = QuotaService()

__all__ = ["smartscan_router"]


@smartscan_router.route(
    "/smartscans", methods=["POST"], authorizer=api_gateway_authorizer
)
def initiate_smartscan():
    user_id = smartscan_router.current_request.context["authorizer"]["principalId"]

    payload = smartscan_router.current_request.json_body
    content_type = payload.get("contentType")

    if not content_type:
        raise ValueError("Invalid content type")

    accessible = quota_service.check_smart_scan_access(user_id)

    if not accessible:
        raise BadRequestError("User can not initiate a Smart Scan due to quota limits")

    token = smartscan_router.current_request.headers.get("Authorization", "").replace(
        "Bearer ", ""
    )

    presigned_post = s3.create_presigned_post_url(user_id, content_type, token)

    return Response(body=presigned_post, status_code=201)
