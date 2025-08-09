import os
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger
from cryptography.fernet import Fernet

from chalicelib import constants
from chalicelib.models import config

logger = Logger(child=True)

__all__ = ["S3"]


class S3:
    def __init__(self):
        self._client = boto3.client("s3")
        self.bucket = config.assets_bucket_name
        self._cipher = None

    @property
    def cipher(self):
        """
        Get or initialize the Fernet cipher for encryption operations.

        :returns: Fernet cipher instance for encryption/decryption
        """
        if self._cipher is None:
            if (
                not os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
                and not config.smartscan_encryption_key
            ):
                raise ValueError(
                    "Encryption not available during packaging - this is expected"
                )

            if not config.smartscan_encryption_key:
                raise ValueError("Smart Scan encryption key is required")

            try:
                encryption_key = config.smartscan_encryption_key.get_secret_value()
                self._cipher = Fernet(encryption_key.encode())
            except Exception as e:
                logger.error(f"Failed to initialize encryption suite: {str(e)}")
                raise ValueError("Invalid encryption key format")

        return self._cipher

    def get_headers(self, key: str) -> dict:
        """
        Get HTTP headers for an S3 object.

        :param key: The S3 object key
        :returns: Dictionary of HTTP headers from the object metadata
        """
        response = self._client.head_object(Bucket=self.bucket, Key=key)
        headers = response.get("ResponseMetadata", {}).get("HTTPHeaders", {})
        return headers

    def delete_object(self, key: str) -> None:
        """
        Delete an object from S3.

        :param key: The S3 object key to delete
        """
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def create_presigned_post_url(
        self, user_id: str, content_type: str, token: str
    ) -> dict:
        """
        Create a presigned POST URL for uploading files to S3.

        :param user_id: The user ID for metadata tagging
        :param content_type: The MIME type of the file to upload
        :param token: The authentication token to encrypt in metadata
        :returns: Dictionary with CloudFront URL, form data, and form URL
        """
        if content_type not in constants.ALLOWED_CONTENT_TYPES:
            raise ValueError("Invalid content type")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_id = str(uuid.uuid4())[:8]
        file_extension = self._get_file_extension(content_type)
        key = f"smartscans/{timestamp}_{random_id}.{file_extension}"

        # Encrypt the token
        try:
            encrypted_token = urlsafe_b64encode(
                self.cipher.encrypt(token.encode())
            ).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt token: {str(e)}")
            raise ValueError("Token encryption failed")

        presigned_post = self._client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Conditions=[
                {"bucket": self.bucket},
                {"key": key},
                {"content-type": content_type},
                [
                    "content-length-range",
                    constants.MIN_FILE_SIZE,
                    constants.MAX_FILE_SIZE,
                ],
                {"x-amz-meta-user-id": user_id},
                {"x-amz-meta-token": encrypted_token},
            ],
            Fields={
                "content-type": content_type,
                "x-amz-meta-user-id": user_id,
                "x-amz-meta-token": encrypted_token,
            },
            ExpiresIn=300,  # URL valid for 5 minutes
        )

        cloudfront_url = f"https://{config.cloudfront_domain_name}/{key}"

        return {
            "url": cloudfront_url,
            "formData": presigned_post["fields"],
            "formUrl": presigned_post["url"],
        }

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt the auth token from S3 metadata.

        :param encrypted_token: The base64 encoded encrypted token
        :returns: Decrypted authentication token string
        """
        try:
            decrypted_bytes = self.cipher.decrypt(
                urlsafe_b64decode(encrypted_token.encode())
            )
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt token: {str(e)}")
            raise ValueError("Invalid or expired encrypted token")

    def _get_file_extension(self, content_type: str) -> str:
        """
        Get file extension from content type.

        :param content_type: The MIME content type
        :returns: File extension string
        """
        content_type_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "application/pdf": "pdf",
        }
        return content_type_map.get(content_type, "jpg")
