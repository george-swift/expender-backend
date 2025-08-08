# ============================================================================
# API GATEWAY RATE LIMITING AND THROTTLING CONFIGURATION
# ============================================================================
#
# This configuration sets appropriate throttling limits
# based on Expender's usage patterns and user quotas.

# Usage plan for free tier users with conservative limits
resource "aws_api_gateway_usage_plan" "free_tier" {
  name         = "expender-${var.environment}-free-tier"
  description  = "Usage plan for free tier users with conservative limits"

  api_stages {
    api_id = aws_api_gateway_rest_api.rest_api.id
    stage  = aws_api_gateway_stage.rest_api.stage_name
  }

  # Free tier: 1,000 requests per day (aligned with 30 smart scans/month)
  quota_settings {
    limit  = 1000
    period = "DAY"
  }

  # Conservative rate limits for free users
  throttle_settings {
    rate_limit  = 10   # 10 requests per second
    burst_limit = 20   # 20 request burst capacity
  }

  tags = {
    Environment = var.environment
    Plan        = "free"
  }

  depends_on = [
    aws_api_gateway_rest_api.rest_api,
    aws_api_gateway_stage.rest_api
  ]
}

# Usage plan for pro tier users with higher limits
resource "aws_api_gateway_usage_plan" "pro_tier" {
  name         = "expender-${var.environment}-pro-tier"
  description  = "Usage plan for pro tier users with higher limits"

  api_stages {
    api_id = aws_api_gateway_rest_api.rest_api.id
    stage  = aws_api_gateway_stage.rest_api.stage_name
  }

  # Pro tier: 10,000 requests per day (supports unlimited smart scans)
  quota_settings {
    limit  = 10000
    period = "DAY"
  }

  # Higher rate limits for pro users
  throttle_settings {
    rate_limit  = 50   # 50 requests per second
    burst_limit = 100  # 100 request burst capacity
  }

  tags = {
    Environment = var.environment
    Plan        = "pro"
  }

  depends_on = [
    aws_api_gateway_rest_api.rest_api,
    aws_api_gateway_stage.rest_api
  ]
}

# Stage-level throttling (global limits across all users)
resource "aws_api_gateway_method_settings" "global_throttling" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = aws_api_gateway_stage.rest_api.stage_name
  method_path = "*/*"

  settings {
    # Global stage limits - conservative for development
    throttling_rate_limit  = var.environment == "prod" ? 1000 : 100
    throttling_burst_limit = var.environment == "prod" ? 2000 : 200

    # Enable detailed metrics and logging
    metrics_enabled = true
    logging_level   = "INFO"

    # Caching disabled for dynamic content
    caching_enabled = false
  }

  depends_on = [
    aws_api_gateway_rest_api.rest_api,
    aws_api_gateway_stage.rest_api,
    aws_api_gateway_account.main
  ]
}

# Method-specific throttling for resource-intensive endpoints
resource "aws_api_gateway_method_settings" "smartscan_throttling" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = aws_api_gateway_stage.rest_api.stage_name
  method_path = "smartscans/POST"

  settings {
    # Lower limits for AI-powered SmartScan endpoint (resource intensive)
    throttling_rate_limit  = var.environment == "prod" ? 10 : 5
    throttling_burst_limit = var.environment == "prod" ? 20 : 10

    metrics_enabled = true
    logging_level   = "INFO"
  }

  depends_on = [
    aws_api_gateway_rest_api.rest_api,
    aws_api_gateway_stage.rest_api,
    aws_api_gateway_account.main
  ]
}

resource "aws_api_gateway_method_settings" "export_throttling" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = aws_api_gateway_stage.rest_api.stage_name
  method_path = "expenses/export/POST"

  settings {
    # Lower limits for CSV export endpoint (memory intensive)
    throttling_rate_limit  = var.environment == "prod" ? 5 : 2
    throttling_burst_limit = var.environment == "prod" ? 10 : 5

    metrics_enabled = true
    logging_level   = "INFO"
  }

  depends_on = [
    aws_api_gateway_rest_api.rest_api,
    aws_api_gateway_stage.rest_api,
    aws_api_gateway_account.main
  ]
}

resource "aws_api_gateway_method_settings" "batch_post_throttling" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = aws_api_gateway_stage.rest_api.stage_name
  method_path = "expenses/batch/POST"

  settings {
    # Moderate limits for batch operations (up to 25 expenses)
    throttling_rate_limit  = var.environment == "prod" ? 20 : 10
    throttling_burst_limit = var.environment == "prod" ? 40 : 20

    metrics_enabled = true
    logging_level   = "INFO"
  }

  depends_on = [
    aws_api_gateway_rest_api.rest_api,
    aws_api_gateway_stage.rest_api,
    aws_api_gateway_account.main
  ]
}

resource "aws_api_gateway_method_settings" "batch_delete_throttling" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = aws_api_gateway_stage.rest_api.stage_name
  method_path = "expenses/batch/DELETE"

  settings {
    # Moderate limits for batch operations (up to 25 expenses)
    throttling_rate_limit  = var.environment == "prod" ? 20 : 10
    throttling_burst_limit = var.environment == "prod" ? 40 : 20

    metrics_enabled = true
    logging_level   = "INFO"
  }

  depends_on = [
    aws_api_gateway_rest_api.rest_api,
    aws_api_gateway_stage.rest_api,
    aws_api_gateway_account.main
  ]
}

# Webhook endpoint - higher burst for external service callbacks
resource "aws_api_gateway_method_settings" "webhooks_throttling" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = aws_api_gateway_stage.rest_api.stage_name
  method_path = "webhooks/POST"

  settings {
    # Higher burst capacity for webhook callbacks from Clerk
    throttling_rate_limit  = var.environment == "prod" ? 100 : 50
    throttling_burst_limit = var.environment == "prod" ? 200 : 100

    metrics_enabled = true
    logging_level   = "INFO"
  }

  depends_on = [
    aws_api_gateway_rest_api.rest_api,
    aws_api_gateway_stage.rest_api,
    aws_api_gateway_account.main
  ]
}
