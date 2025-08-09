import random
import time

from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from chalice import (BadRequestError, NotFoundError, TooManyRequestsError,
                     UnprocessableEntityError)

logger = Logger(child=True)

__all__ = ["handle_errors", "QuotaExceededError", "DocumentProcessingError"]


class QuotaExceededError(Exception):
    """Raised when user exceeds their quota limits."""

    def __init__(self, user_id, limit_type):
        self.user_id = user_id
        self.limit_type = limit_type
        super().__init__(f"Quota exceeded for {limit_type}")


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""

    pass


def handle_errors(event, get_response):
    """
    Centralized error handling middleware.

    Handles AWS service errors, third-party integrations, security,
    and provides comprehensive logging for observability.
    """
    start_time = time.time()

    try:
        response = get_response(event)
        duration = time.time() - start_time

        # Log based on sampling rate (10% of requests) or importance
        should_log = (
            _is_critical_endpoint(event)
            or duration > 1.0
            or random.random() < 0.1  # 10% sampling
        )
        if should_log:
            logger.info(
                "Request completed successfully",
                extra={
                    "duration_ms": round(duration * 1000, 2),
                    "path": getattr(event, "path", "unknown"),
                },
            )
        return response

    except QuotaExceededError as e:
        logger.info(
            "User quota exceeded",
            extra={
                "user_id": e.user_id,
                "limit_type": e.limit_type,
            },
        )
        raise TooManyRequestsError("Usage quota exceeded. Please upgrade your plan.")

    except ValueError as e:
        error_message = str(e)

        # Sanitize error messages to prevent data leakage while logging full details
        if "No mutable fields provided" in error_message:
            logger.warning(
                "Validation error",
                extra={"error": error_message},
            )
            raise UnprocessableEntityError("Invalid request data")
        elif "No expenses found" in error_message:
            raise NotFoundError("Resource not found")
        elif "Invalid date" in error_message:
            logger.warning(
                "Date validation error",
                extra={"error": error_message},
            )
            raise BadRequestError("Invalid date format provided")
        elif "Token encryption failed" in error_message:
            logger.error(
                "Encryption service error",
                extra={"error": error_message},
            )
            raise BadRequestError("Request processing failed")
        else:
            logger.warning(
                "Validation error",
                extra={"error": error_message},
            )
            raise BadRequestError("Invalid request")

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        request_id = e.response.get("ResponseMetadata", {}).get("RequestId")
        service = e.response.get("Error", {}).get("Service", "unknown")

        logger.error(
            "AWS service error",
            extra={
                "error_code": error_code,
                "request_id": request_id,
                "service": service,
            },
        )

        # Map specific AWS errors to appropriate HTTP responses
        error_mappings = {
            # DynamoDB
            "ConditionalCheckFailedException": NotFoundError("Resource not found"),
            "ValidationException": BadRequestError("Invalid request parameters"),
            "ResourceNotFoundException": NotFoundError("Resource not found"),
            "ProvisionedThroughputExceededException": TooManyRequestsError(
                "Service temporarily unavailable, please try again later"
            ),
            "AccessDeniedException": BadRequestError("Access denied"),
            "ThrottlingException": TooManyRequestsError("Rate limit exceeded"),
            "ServiceUnavailableException": TooManyRequestsError(
                "Service temporarily unavailable"
            ),
            "ItemCollectionSizeLimitExceededException": BadRequestError(
                "Request too large"
            ),
            "RequestLimitExceeded": TooManyRequestsError("Request limit exceeded"),
            # S3
            "NoSuchKey": NotFoundError("File not found"),
            "NoSuchBucket": NotFoundError("Storage location not found"),
            "BucketNotEmpty": BadRequestError("Storage location is not empty"),
            "InvalidBucketName": BadRequestError("Invalid storage configuration"),
            "EntityTooLarge": BadRequestError("File too large"),
            "EntityTooSmall": BadRequestError("File too small"),
            "InvalidRequest": BadRequestError("Invalid request"),
            "MalformedPolicy": BadRequestError("Invalid request configuration"),
            "SignatureDoesNotMatch": BadRequestError("Authentication failed"),
            "TokenRefreshRequired": BadRequestError("Authentication expired"),
            "SlowDown": TooManyRequestsError("Too many requests, please slow down"),
            "RequestTimeout": TooManyRequestsError(
                "Request timed out, please try again"
            ),
            "InternalError": TooManyRequestsError("Service temporarily unavailable"),
            "ServiceUnavailable": TooManyRequestsError(
                "Service temporarily unavailable"
            ),
            "RequestTimeTooSkewed": BadRequestError("System clock error"),
            "ExpiredToken": BadRequestError("Authentication expired"),
            "InvalidObjectState": BadRequestError("File is not available"),
            "RestoreAlreadyInProgress": BadRequestError("File restore in progress"),
        }

        if error_code in error_mappings:
            raise error_mappings[error_code]
        else:
            logger.error(
                "Unknown AWS error",
                extra={"error_code": error_code},
            )
            raise

    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__
        duration = time.time() - start_time

        # Handle specific third-party service errors
        if any(
            keyword in error_str.lower() for keyword in ["openai", "gpt", "completion"]
        ):
            logger.warning(
                "AI categorization service error",
                extra={
                    "error": error_str,
                    "service": "openai",
                },
            )
            # Don't fail the request completely - categorization can fallback to "Other"
            # Re-raise as a handled error that calling code can catch
            raise ValueError("AI categorization temporarily unavailable")

        elif any(
            keyword in error_str.lower()
            for keyword in ["clerk", "jwt", "token verification"]
        ):
            logger.error(
                "Authentication service error",
                extra={
                    "error": error_str,
                    "service": "clerk",
                },
            )
            raise BadRequestError("Authentication failed")

        elif any(
            keyword in error_str.lower()
            for keyword in ["textract", "document processing"]
        ):
            logger.error(
                "Document processing error",
                extra={
                    "error": error_str,
                    "service": "textract",
                },
            )
            raise UnprocessableEntityError("Unable to process document")

        elif "fernet" in error_str.lower() or "encryption" in error_str.lower():
            logger.error(
                "Encryption service error",
                extra={
                    "error": error_str,
                    "service": "encryption",
                },
            )
            raise BadRequestError("Request processing failed")

        else:
            # Log unexpected errors with full context for debugging
            logger.exception(
                "Unexpected error",
                extra={
                    "error": error_str,
                    "error_type": error_type,
                    "path": getattr(event, "path", "unknown"),
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            raise


def _is_critical_endpoint(event):
    """Determine if endpoint should always be logged."""
    critical_paths = [
        "/expenses",  # Expense management operations
        "/smartscans",  # Smart scan uploads
        "/webhooks",  # Webhook integrations
    ]
    path = getattr(event, "path", "")
    return any(critical in path for critical in critical_paths)
