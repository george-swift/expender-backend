import os


def pytest_configure():
    os.environ.setdefault("ASSETS_BUCKET_NAME", "test-assets")
    os.environ.setdefault("APPSYNC_GRAPHQL_ENDPOINT", "https://appsync.test/graphql")
    os.environ.setdefault("CLERK_SECRET_KEY", "sk_test")
    os.environ.setdefault(
        "CLERK_JWT_PUBLIC_KEY",
        "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
    )
    os.environ.setdefault("CLERK_WEBHOOK_SIGNING_SECRET", "whsec_clerk")
    os.environ.setdefault("EVENTS_BUS_NAME", "events")
    os.environ.setdefault("EXPENSES_TABLE_NAME", "expenses")
    os.environ.setdefault("EXPENSES_TABLE_STREAM_ARN", "arn:aws:dynamodb:test")
    os.environ.setdefault("FRONTEND_APP_URL", "https://app.test")
    os.environ.setdefault("FRONTEND_DEV_APP_URL", "http://localhost:3000")
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    os.environ.setdefault("QUOTAS_TABLE_NAME", "quotas")
    os.environ.setdefault("QUOTAS_TABLE_STREAM_ARN", "arn:aws:dynamodb:test")
    os.environ.setdefault(
        "SMARTSCAN_ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="
    )
    os.environ.setdefault("SMARTSCANS_TABLE_NAME", "smartscans")
    os.environ.setdefault("BILLING_EVENTS_TABLE_NAME", "billing-events")
    os.environ.setdefault("CATEGORIZATION_CACHE_TABLE_NAME", "categorization-cache")
    os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")
    os.environ.setdefault("STRIPE_PRICE_ID_MONTHLY", "price_monthly")
    os.environ.setdefault("STRIPE_SUCCESS_URL", "https://app.test/billing/success")
    os.environ.setdefault("STRIPE_CANCEL_URL", "https://app.test/billing/cancel")
