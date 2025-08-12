from aws_lambda_powertools import Logger
from clerk_backend_api.security import (AuthStatus, RequestState,
                                        TokenVerificationError,
                                        VerifyTokenOptions, verify_token)

from chalicelib.models import config

logger = Logger(child=True)

__all__ = ["Clerk"]


class Clerk:
    @classmethod
    def authenticate_request(cls, token: str, use_networkless: bool = True):
        """
        Authenticate a request using Clerk JWT token verification.

        :param token: The Bearer token from the request header
        :param use_networkless: Whether to use networkless verification with JWT key
        :returns: RequestState object with authentication status and payload
        :raises: TokenVerificationError if authentication fails
        """
        session_token = token.replace("Bearer ", "")

        try:
            if use_networkless:
                # Primary: Use networkless verification with JWT public key to eliminate unnecessary requests and/or latency
                logger.info("Using networkless JWT verification")
                options = VerifyTokenOptions(
                    authorized_parties=[
                        config.frontend_app_url,
                        config.frontend_dev_app_url,
                    ],
                    jwt_key=config.clerk_jwt_public_key.get_secret_value(),
                )
                payload = verify_token(token, options)
            else:
                # Fallback: Use network-based verification with secret key
                logger.info("Using network-based JWT verification")
                options = VerifyTokenOptions(
                    authorized_parties=[
                        config.frontend_app_url,
                        config.frontend_dev_app_url,
                    ],
                    secret_key=config.clerk_secret_key.get_secret_value(),
                )
                payload = verify_token(token, options)

        except TokenVerificationError as e:
            if use_networkless:
                # If networkless fails, try fallback to network-based verification
                logger.warning(
                    f"Networkless verification failed: {e}, attempting fallback"
                )
                try:
                    options = VerifyTokenOptions(
                        authorized_parties=[
                            config.frontend_app_url,
                            config.frontend_dev_app_url,
                        ],
                        secret_key=config.clerk_secret_key.get_secret_value(),
                    )
                    payload = verify_token(token, options)
                    logger.info("Fallback network verification successful")
                except TokenVerificationError as fallback_error:
                    logger.error(
                        f"Both networkless and network verification failed: {fallback_error}"
                    )
                    raise fallback_error
            else:
                logger.error(f"Network verification failed: {e}")
                raise e

        request_state = RequestState(
            status=AuthStatus.SIGNED_IN, token=session_token, payload=payload
        )
        return request_state
