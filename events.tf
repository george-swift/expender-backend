# ============================================================================
# EVENT-DRIVEN ARCHITECTURE COMPONENTS
# ============================================================================

# Custom EventBridge bus for application events
resource "aws_cloudwatch_event_bus" "event_bus" {
  name = local.event_bus_name

  tags = {
    Environment = var.environment
    Name        = local.event_bus_name
  }
}

# Event rule for user account deletion (triggered by Clerk webhooks)
resource "aws_cloudwatch_event_rule" "user_deleted" {
  name           = "UserDeleted"
  description    = "Trigger deletion of all user data on account deletion"
  event_bus_name = aws_cloudwatch_event_bus.event_bus.name

  event_pattern = jsonencode({
    source        = ["clerk.webhook"]
    "detail-type" = ["UserDeleted"]
  })

  depends_on = [aws_cloudwatch_event_bus.event_bus]
}

resource "aws_cloudwatch_event_target" "user_deletion_handler" {
  rule           = aws_cloudwatch_event_rule.user_deleted.name
  event_bus_name = aws_cloudwatch_event_bus.event_bus.name
  target_id      = "UserDeletionHandlerTarget"
  arn            = "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-deleted_account_handler"
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_user_deletion" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = "expender-${var.environment}-deleted_account_handler"
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.user_deleted.arn
}

# ============================================================================
# APPSYNC GRAPHQL API FOR SMARTSCANS
# ============================================================================

# AppSync GraphQL API with Lambda authorization for SmartScan real-time updates
resource "aws_appsync_graphql_api" "smartscan_api" {
  name                = local.appsync_graphql_api_name
  authentication_type = "AWS_LAMBDA"

  lambda_authorizer_config {
    authorizer_uri = "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-appsync_graphql_authorizer"
  }

  schema = file("schema.graphql")

  xray_enabled = true
}

resource "aws_lambda_permission" "appsync_graphql_authorizer" {
  statement_id  = "appsync_graphql_authorizer"
  action        = "lambda:InvokeFunction"
  function_name = "expender-${var.environment}-appsync_graphql_authorizer"
  principal     = "appsync.amazonaws.com"
  source_arn    = aws_appsync_graphql_api.smartscan_api.arn

  depends_on = [
    aws_appsync_graphql_api.smartscan_api
  ]
}

# DynamoDB data source for SmartScan results table
resource "aws_appsync_datasource" "smartscan_results" {
  api_id = aws_appsync_graphql_api.smartscan_api.id
  name   = "expender_${var.environment}_smartscans"
  type   = "AMAZON_DYNAMODB"

  dynamodb_config {
    table_name = aws_dynamodb_table.smartscans.name
  }

  service_role_arn = aws_iam_role.appsync_service_role.arn
}

# GraphQL mutation resolver for publishing SmartScan results
resource "aws_appsync_resolver" "publish_smartscan_result" {
  api_id           = aws_appsync_graphql_api.smartscan_api.id
  type             = "Mutation"
  field            = "publishSmartScanResult"
  data_source      = aws_appsync_datasource.smartscan_results.name
  request_template = <<EOF
#if($ctx.identity.resolverContext.userId != $ctx.args.userId)
  $util.error("Unauthorized: User ID does not match authenticated user")
#end
#set($expireTime = $util.time.nowEpochSeconds() + 3600)
{
  "version": "2018-05-29",
  "operation": "PutItem",
  "key": {
    "userId": $util.dynamodb.toDynamoDBJson($ctx.args.userId),
    "scanId": $util.dynamodb.toDynamoDBJson($ctx.args.scanId)
  },
  "attributeValues": {
    "result": $util.dynamodb.toDynamoDBJson($ctx.args.result),
    "objectKey": $util.dynamodb.toDynamoDBJson($ctx.args.objectKey),
    "createdAt": $util.dynamodb.toDynamoDBJson($util.time.nowISO8601()),
    "expireAt": $util.dynamodb.toDynamoDBJson($expireTime)
  },
  "condition": {
    "expression": "attribute_not_exists(userId) AND attribute_not_exists(scanId)"
  }
}
EOF

  response_template = <<EOF
#if($ctx.error)
  #if($ctx.error.type == "DynamoDB:ConditionalCheckFailedException")
    ## Item already exists, return existing data
    $util.toJson({
      "userId": "$ctx.args.userId",
      "scanId": "$ctx.args.scanId",
      "objectKey": "$ctx.args.objectKey",
      "result": $ctx.args.result
    })
  #else
    $util.error($ctx.error.message)
  #end
#else
  ## Return the created item
  $util.toJson($ctx.result)
#end
EOF
}


# GraphQL query resolver for retrieving SmartScan results
resource "aws_appsync_resolver" "get_smartscan_result" {
  api_id            = aws_appsync_graphql_api.smartscan_api.id
  type              = "Query"
  field             = "getSmartScanResult"
  data_source       = aws_appsync_datasource.smartscan_results.name
  request_template  = <<EOF
#if($ctx.identity.resolverContext.userId != $ctx.args.userId)
  $util.error("Unauthorized: User ID does not match authenticated user")
#end
{
  "version": "2018-05-29",
  "operation": "GetItem",
  "key": {
    "userId": $util.dynamodb.toDynamoDBJson($ctx.args.userId),
    "scanId": $util.dynamodb.toDynamoDBJson($ctx.args.scanId)
  }
}
EOF
  response_template = <<EOF
$util.toJson($ctx.result)
EOF
}

# ============================================================================
# STEP FUNCTIONS WORKFLOW FOR USER DATA DELETION
# ============================================================================

# Step Functions state machine for orchestrated user data deletion
resource "aws_sfn_state_machine" "user_data_deletion" {
  name     = "user-data-deletion-workflow"
  role_arn = aws_iam_role.step_functions_execution_role.arn
  definition = templatefile("${path.module}/user_data_deletion_workflow.json", {
    InitializeDeletionLambdaArn = "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-initialize_deletion"
    DeleteSmartScansLambdaArn   = "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-delete_smartscans_batch"
    MarkExpensesLambdaArn       = "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-mark_expenses_for_deletion"
    CompleteDeletionLambdaArn   = "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-complete_deletion"
  })

  tags = {
    Environment = var.environment
    Name        = "user-data-deletion-workflow"
  }

  depends_on = [aws_iam_role.step_functions_execution_role]
}
