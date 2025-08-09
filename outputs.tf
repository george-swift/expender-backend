# ============================================================================
# TERRAFORM OUTPUTS FOR INFRASTRUCTURE RESOURCES
# ============================================================================

# AWS account information
output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "caller_user" {
  value = data.aws_caller_identity.current.user_id
}

# API Gateway endpoints and configuration
output "rest_api_id" {
  value = aws_api_gateway_rest_api.rest_api.id
}

output "endpoint_url" {
  value = aws_api_gateway_stage.rest_api.invoke_url
}

# DynamoDB stream ARNs for event processing
output "expenses_table_stream_arn" {
  value = aws_dynamodb_table.expenses.stream_arn
}

output "quotas_table_stream_arn" {
  value = aws_dynamodb_table.quotas.stream_arn
}

# Usage plan IDs for API key association
output "free_tier_usage_plan_id" {
  description = "Usage plan ID for free tier users"
  value       = aws_api_gateway_usage_plan.free_tier.id
}

output "pro_tier_usage_plan_id" {
  description = "Usage plan ID for pro tier users"
  value       = aws_api_gateway_usage_plan.pro_tier.id
}

# AppSync GraphQL API endpoint
output "graphql_endpoint" {
  value = aws_appsync_graphql_api.smartscan_api.uris["GRAPHQL"]
}
