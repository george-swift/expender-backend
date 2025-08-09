#!/usr/bin/env python3
"""
AWS Architecture Diagram for Expender - Serverless Expense Management Platform
Generated using Amazon Q and Diagrams library
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb, DynamodbStreams
from diagrams.aws.devtools import XRay
from diagrams.aws.integration import Appsync, Eventbridge, StepFunctions
from diagrams.aws.management import Cloudwatch
from diagrams.aws.ml import Textract
from diagrams.aws.network import APIGateway, CloudFront
from diagrams.aws.security import IAM
from diagrams.aws.storage import S3
from diagrams.onprem.client import Users
from diagrams.saas.chat import \
    Slack  # Using as placeholder for external services

# Configure diagram
graph_attr = {"fontsize": "16", "bgcolor": "white", "pad": "0.5", "splines": "ortho"}

with Diagram(
    "Expender - Serverless Expense Management Architecture",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    filename="expender_architecture",
):

    # External Users and Services
    with Cluster("External"):
        users = Users("NextJS Web App")
        clerk = Slack("Clerk Auth")
        openai = Slack("OpenAI API")

    # CDN Layer
    with Cluster("CDN & Content Delivery"):
        cloudfront = CloudFront("CloudFront\nGlobal CDN")

    # API Layer
    with Cluster("API Layer"):
        api_gateway = APIGateway("API Gateway\nREST API\n+ Rate Limiting")
        lambda_auth = Lambda("Lambda\nAuthorizer")

        with Cluster("Business Logic"):
            lambda_expenses = Lambda("Expenses\nCRUD")
            lambda_smartscan = Lambda("SmartScan\nInitiator")
            lambda_webhooks = Lambda("Clerk\nWebhooks")
            lambda_s3_events = Lambda("S3 Event\nHandler")

    # Real-time & GraphQL
    with Cluster("Real-time Services"):
        appsync = Appsync("AppSync\nGraphQL API\nSubscriptions")

    # Storage Layer
    with Cluster("Storage & Database"):
        s3_bucket = S3("S3 Bucket\nReceipt Storage")

        with Cluster("DynamoDB Tables"):
            ddb_expenses = Dynamodb("expenses")
            ddb_smartscans = Dynamodb("smartscans\n(TTL enabled)")
            ddb_quotas = Dynamodb("quotas")
            ddb_streams = DynamodbStreams("DynamoDB\nStreams")

    # AI & Processing
    with Cluster("AI & Processing"):
        textract = Textract("AWS Textract\nDocument Analysis")
        step_functions = StepFunctions("Step Functions\nUser Data Deletion")

    # Event-Driven Architecture
    with Cluster("Event Processing"):
        eventbridge = Eventbridge("EventBridge\nCustom Event Bus")

    # Monitoring & Security
    with Cluster("Monitoring & Security"):
        cloudwatch = Cloudwatch("CloudWatch\nLogs")
        xray = XRay("X-Ray\nTracing")
        iam = IAM("IAM\nRoles & Policies")

    # Main Data Flows

    # User Authentication Flow
    users >> Edge(label="Auth", style="dashed") >> clerk
    clerk >> Edge(label="JWT") >> users
    users >> Edge(label="API Calls") >> api_gateway
    api_gateway >> Edge(label="Validate") >> lambda_auth
    lambda_auth >> Edge(label="Verify", style="dashed") >> clerk

    # SmartScan Initiation & Receipt Upload Flow
    users >> Edge(label="Request Upload", color="blue") >> api_gateway
    api_gateway >> Edge(color="blue") >> lambda_smartscan
    lambda_smartscan >> Edge(label="Check Quota", color="blue") >> ddb_quotas
    lambda_smartscan >> Edge(label="Presigned URL", color="blue") >> s3_bucket
    users >> Edge(label="Upload Receipt", color="blue") >> s3_bucket
    s3_bucket >> Edge(label="S3 Event", color="blue") >> lambda_s3_events
    lambda_s3_events >> Edge(label="Extract Text", color="blue") >> textract
    lambda_s3_events >> Edge(label="Categorize", color="blue", style="dashed") >> openai
    lambda_s3_events >> Edge(label="Store Result", color="blue") >> ddb_smartscans
    ddb_smartscans >> Edge(label="Real-time Update", color="blue") >> appsync
    appsync >> Edge(label="Subscription", color="blue") >> users

    # Expense CRUD Operations
    api_gateway >> Edge(label="CRUD", color="green") >> lambda_expenses
    lambda_expenses >> Edge(color="green") >> ddb_expenses
    lambda_expenses >> Edge(color="green") >> ddb_quotas

    # User Lifecycle Management
    clerk >> Edge(label="Webhooks", color="red", style="dashed") >> lambda_webhooks
    lambda_webhooks >> Edge(label="Create Quota", color="red") >> ddb_quotas
    lambda_webhooks >> Edge(color="red") >> eventbridge
    eventbridge >> Edge(color="red") >> step_functions
    step_functions >> Edge(color="red") >> ddb_expenses
    step_functions >> Edge(color="red") >> s3_bucket

    # DynamoDB Streams for Real-time Processing
    ddb_expenses >> ddb_streams
    ddb_smartscans >> ddb_streams
    ddb_quotas >> ddb_streams

    # Content Delivery - Receipt Files Only
    users >> Edge(label="Files", color="orange") >> cloudfront
    cloudfront >> Edge(color="orange") >> s3_bucket

    # Monitoring Connections
    lambda_expenses >> cloudwatch
    lambda_smartscan >> cloudwatch
    lambda_webhooks >> cloudwatch
    lambda_s3_events >> cloudwatch

    api_gateway >> xray
    lambda_expenses >> xray
    lambda_smartscan >> xray

    # Security
    iam >> lambda_expenses
    iam >> lambda_smartscan
    iam >> lambda_webhooks
    iam >> lambda_s3_events

print("Architecture diagram generated as 'expender_architecture.png'")
