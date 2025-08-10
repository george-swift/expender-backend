# Terraform configuration for Expender serverless infrastructure
# Manages IAM roles, permissions, and account-level settings

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Get current AWS account information
data "aws_caller_identity" "current" {}

# Centralized resource naming with environment separation
locals {
  account_id                                 = data.aws_caller_identity.current.account_id
  api_gateway_authorizer_role_name           = "expender-${var.environment}-api-gateway-authorizer-role"
  api_service_role_name                      = "expender-${var.environment}-api-service-role"
  appsync_graphql_api_name                   = "expender-${var.environment}-appsync-graphql-api"
  appsync_graphql_authorizer_role_name       = "expender-${var.environment}-appsync-graphql-authorizer-role"
  appsync_service_role_name                  = "expender-${var.environment}-appsync-service-role"
  assets_bucket_name                         = "expender-${var.environment}-assets"
  assets_bucket_event_handler_role_name      = "expender-${var.environment}-bucket-event-handler-role"
  cdn_name                                   = "expender-${var.environment}-cdn"
  event_bus_name                             = "expender-${var.environment}-event-bus"
  expenses_table_name                        = "expender-${var.environment}-expenses"
  quotas_table_name                          = "expender-${var.environment}-quotas"
  step_functions_execution_role_name         = "expender-${var.environment}-step-functions-execution-role"
  smartscans_table_name                      = "expender-${var.environment}-smartscans"
}

# ============================================================================
# IAM ROLES AND POLICIES
# ============================================================================

# API Gateway Lambda authorizer execution role
resource "aws_iam_role" "api_gateway_authorizer_role" {
  name = local.api_gateway_authorizer_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = local.api_gateway_authorizer_role_name
  }
}

resource "aws_iam_role_policy_attachment" "api_gateway_authorizer_basic_execution" {
  role       = aws_iam_role.api_gateway_authorizer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "api_gateway_authorizer_xray_tracing" {
  role       = aws_iam_role.api_gateway_authorizer_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Main API service role with comprehensive permissions
resource "aws_iam_role" "api_service_role" {
  name = local.api_service_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = local.api_service_role_name
  }
}

resource "aws_iam_role_policy" "api_service_role_policy" {
  name        = "${local.api_service_role_name}-policy"
  role        = aws_iam_role.api_service_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:ConditionCheckItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.expenses.arn,
          "${aws_dynamodb_table.expenses.arn}/index/*",
          aws_dynamodb_table.smartscans.arn,
          "${aws_dynamodb_table.smartscans.arn}/index/*",
          aws_dynamodb_table.quotas.arn,
          "${aws_dynamodb_table.quotas.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:DescribeStream",
          "dynamodb:ListStreams"
        ]
        Resource = [
          aws_dynamodb_table.expenses.stream_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketNotification"
        ]
        Resource = [
          aws_s3_bucket.assets.arn,
          "${aws_s3_bucket.assets.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = [
          aws_cloudwatch_event_bus.event_bus.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution",
          "states:ListStateMachines"
        ]
        Resource = "*"
      }
    ]
  })

  depends_on = [
    aws_dynamodb_table.expenses,
    aws_dynamodb_table.smartscans,
    aws_dynamodb_table.quotas,
    aws_s3_bucket.assets,
    aws_cloudwatch_event_bus.event_bus
  ]
}

resource "aws_iam_role_policy_attachment" "api_service_role_basic_execution" {
  role       = aws_iam_role.api_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "api_service_role_xray_tracing" {
  role       = aws_iam_role.api_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# AppSync service role for GraphQL API operations
resource "aws_iam_role" "appsync_service_role" {
  name = local.appsync_service_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "appsync.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = local.appsync_service_role_name
  }
}

resource "aws_iam_role_policy" "appsync_service_role_policy" {
  name = "${local.appsync_service_role_name}-policy"
  role = aws_iam_role.appsync_service_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ],
        Resource = [
          aws_dynamodb_table.smartscans.arn,
          "${aws_dynamodb_table.smartscans.arn}/index/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = "xray:PutTraceSegments",
        Resource = "*"
      },
    ]
  })
}

# AppSync GraphQL Lambda authorizer execution role
resource "aws_iam_role" "appsync_graphql_authorizer_role" {
  name = local.appsync_graphql_authorizer_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = local.appsync_graphql_authorizer_role_name
  }
}

resource "aws_iam_role_policy_attachment" "appsync_graphql_authorizer_basic_execution" {
  role       = aws_iam_role.appsync_graphql_authorizer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "appsync_graphql_authorizer_xray_tracing" {
  role       = aws_iam_role.appsync_graphql_authorizer_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# S3 bucket event handler role for SmartScan processing
resource "aws_iam_role" "bucket_event_handler_role" {
  name = local.assets_bucket_event_handler_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = local.assets_bucket_event_handler_role_name
  }
}

resource "aws_iam_role_policy" "bucket_event_handler_role" {
  name   = "${local.assets_bucket_event_handler_role_name}-policy"
  role   = aws_iam_role.bucket_event_handler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
       {
        Effect = "Allow"
        Action = [
          "textract:AnalyzeExpense"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "arn:aws:s3:::${local.assets_bucket_name}/smartscans/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.smartscans.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.quotas.arn
      },
      {
        Effect = "Allow"
        Action = "appsync:GraphQL"
        Resource = "${aws_appsync_graphql_api.smartscan_api.arn}/types/Mutation/fields/publishSmartScanResult"
      }
    ]
  })

  depends_on = [
    aws_iam_role.bucket_event_handler_role,
    aws_dynamodb_table.smartscans,
    aws_dynamodb_table.quotas,
    aws_appsync_graphql_api.smartscan_api
  ]
}

resource "aws_iam_role_policy_attachment" "bucket_event_handler_basic_execution" {
  role       = aws_iam_role.bucket_event_handler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "bucket_event_handler_xray_tracing" {
  role       = aws_iam_role.bucket_event_handler_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Step Functions execution role for user data deletion workflow
resource "aws_iam_role" "step_functions_execution_role" {
  name = local.step_functions_execution_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = local.step_functions_execution_role_name
  }
}

resource "aws_iam_role_policy" "step_functions_lambda_invoke" {
  name = "${local.step_functions_execution_role_name}-policy"
  role = aws_iam_role.step_functions_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-initialize_deletion",
          "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-delete_smartscans_batch",
          "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-mark_expenses_for_deletion",
          "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-complete_deletion"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:BatchWriteItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = [
          aws_dynamodb_table.smartscans.arn,
          "${aws_dynamodb_table.smartscans.arn}/index/*",
          aws_dynamodb_table.expenses.arn,
          "${aws_dynamodb_table.expenses.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })

  depends_on = [
    aws_dynamodb_table.smartscans,
    aws_dynamodb_table.expenses,
    aws_iam_role.step_functions_execution_role
  ]
}

# ============================================================================
# API GATEWAY CLOUDWATCH LOGGING SETUP
# ============================================================================

# Account-level CloudWatch Logs role for API Gateway (shared across environments)
resource "aws_iam_role" "api_gateway_cloudwatch_logs" {
  name = "APIGatewayCloudWatchLogsRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Purpose     = "api-gateway-logging"
    Description = "Account-level role for API Gateway CloudWatch logging"
  }
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch_logs" {
  role       = aws_iam_role.api_gateway_cloudwatch_logs.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Set API Gateway account-level CloudWatch Logs configuration
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_logs.arn

  depends_on = [
    aws_iam_role_policy_attachment.api_gateway_cloudwatch_logs
  ]
}
