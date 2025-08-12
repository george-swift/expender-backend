from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["config"]


class Config(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_file_encoding="utf-8")

    aws_region: str | None = Field(
        default="us-east-1", description="AWS Region with resources"
    )
    assets_bucket_name: str = Field(..., description="S3 bucket for assets")
    appsync_graphql_endpoint: str = Field(
        ..., description="AppSync GraphQL endpoint for smart scans"
    )
    clerk_secret_key: SecretStr = Field(
        ..., description="Clerk secret key for network-based token verification"
    )
    clerk_jwt_public_key: SecretStr = Field(
        ...,
        description="Clerk JWT public key in PEM format for networkless token verification",
    )
    clerk_webhook_signing_secret: SecretStr = Field(
        ..., description="Clerk webhook signing secret for secure webhook handling"
    )
    cloudfront_domain_name: str = Field(
        ..., description="CloudFront domain name for assets"
    )
    events_bus_name: str = Field(..., description="EventBridge event bus name")
    expenses_table_name: str = Field(
        ..., description="DynamoDB table name for expenses"
    )
    expenses_table_stream_arn: str = Field(
        ..., description="DynamoDB stream ARN for expenses table"
    )
    frontend_app_url: str = Field(..., description="URL of the frontend application")
    frontend_dev_app_url: str = Field(
        ..., description="URL of the frontend development application"
    )
    openai_api_key: SecretStr = Field(..., description="OpenAI API key for AI services")
    quotas_table_name: str = Field(..., description="DynamoDB table name for quotas")
    quotas_table_stream_arn: str = Field(
        ..., description="DynamoDB stream ARN for quotas table"
    )
    smartscan_encryption_key: SecretStr = Field(
        ...,
        description="Encryption key for securing temporary auth tokens in S3 metadata",
    )
    smartscans_table_name: str = Field(
        ..., description="DynamoDB table name for smart scans"
    )


@lru_cache
def get_config():
    """Create cached instance of config."""
    return Config()


config = get_config()
