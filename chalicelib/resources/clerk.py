from clerk_backend_api.security import (AuthStatus, RequestState,
                                        VerifyTokenOptions, verify_token)

from chalicelib.models import config

__all__ = ["Clerk"]


class Clerk:
    @classmethod
    def authenticate_request(cls, token: str):
        """
        Authenticate a request using Clerk JWT token verification.

        :param token: The Bearer token from the request header
        :returns: RequestState object with authentication status and payload
        """
        session_token = token.replace("Bearer ", "")
        options = VerifyTokenOptions(
            authorized_parties=[config.frontend_app_url, config.frontend_dev_app_url],
            secret_key=config.clerk_secret_key.get_secret_value(),
        )
        payload = verify_token(token, options)
        request_state = RequestState(
            status=AuthStatus.SIGNED_IN, token=session_token, payload=payload
        )
        return request_state
