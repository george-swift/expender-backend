from aws_lambda_powertools import Logger
from chalice import AuthResponse, Blueprint

from chalicelib.resources import Clerk

logger = Logger(child=True)
authorizers = Blueprint(__name__)

__all__ = ["authorizers"]


@authorizers.authorizer()
def api_gateway_authorizer(auth_request):
    request_state = Clerk.authenticate_request(auth_request.token)
    if request_state.is_signed_in:
        user_id = request_state.payload.get("sub")
        return AuthResponse(routes=["*"], principal_id=user_id)
    else:
        return AuthResponse(routes=[], principal_id="")


@authorizers.lambda_function()
def appsync_graphql_authorizer(event, context):
    token = event.get("authorizationToken")

    if not token:
        raise ValueError("Missing authorization token")

    try:
        request_state = Clerk.authenticate_request(token)
        if request_state.is_signed_in:
            user_id = request_state.payload.get("sub")
            return {
                "isAuthorized": True,
                "resolverContext": {"userId": user_id},
            }
        else:
            return {"isAuthorized": False}
    except Exception:
        raise
