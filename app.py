from aws_lambda_powertools import Logger, Tracer
from chalice import Chalice, CORSConfig
from chalice.app import ConvertToMiddleware

from chalicelib.authorizers import authorizers
from chalicelib.events import account_lifecycle, bucket_event, expense_stream
from chalicelib.middleware import handle_errors
from chalicelib.models import config
from chalicelib.routers import (
    billing_router,
    expense_router,
    quota_router,
    smartscan_router,
    webhooks_router,
)

logger = Logger(use_rfc3339=True, utc=True)
tracer = Tracer()

app = Chalice(app_name="expender")

# Configure CORS for the application
cors_config = CORSConfig(
    allow_origin=config.frontend_app_url,
    max_age=600,
    expose_headers=["X-Total-Count"],
    allow_credentials=True,
)

app.api.cors = cors_config

# Register middleware for logging and tracing
app.register_middleware(ConvertToMiddleware(logger.inject_lambda_context))

app.register_middleware(
    ConvertToMiddleware(tracer.capture_lambda_handler(capture_response=False))
)


@app.middleware("http")
def inject_route_info(event, get_response):
    logger.structure_logs(append=True, request_path=event.path)
    return get_response(event)


@app.middleware("all")
def error_handler(event, get_response):
    return handle_errors(event, get_response)


# Register blueprints for different routers, authorizers and event handlers
app.register_blueprint(webhooks_router)
app.register_blueprint(authorizers)
app.register_blueprint(expense_router)
app.register_blueprint(smartscan_router)
app.register_blueprint(quota_router)
app.register_blueprint(billing_router)
app.register_blueprint(account_lifecycle)
app.register_blueprint(bucket_event)
app.register_blueprint(expense_stream)
