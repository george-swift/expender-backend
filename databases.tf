# ============================================================================
# DYNAMODB TABLES AND STREAM CONFIGURATIONS
# ============================================================================

# Main expenses table with date and category indexes for efficient querying
resource "aws_dynamodb_table" "expenses" {
  name             = local.expenses_table_name
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "userId"
  range_key        = "expenseId"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "expenseId"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  ttl {
    attribute_name = "expireAt"
    enabled        = true
  }

  # GSI for date-based queries (e.g., recent expenses)
  global_secondary_index {
    name               = "DateIndex"
    hash_key           = "userId"
    range_key          = "date"
    projection_type    = "INCLUDE"
    non_key_attributes = ["expenseId", "amount", "category", "currency", "description", "merchant", "receipt", "scanId"]
  }

  # GSI for category-based queries (e.g., top category metric)
  global_secondary_index {
    name               = "CategoryIndex"
    hash_key           = "userId"
    range_key          = "category"
    projection_type    = "INCLUDE"
    non_key_attributes = ["expenseId", "amount", "date", "currency", "merchant", "receipt", "scanId"]
  }

  tags = {
    Name        = local.expenses_table_name
    Environment = var.environment
  }
}

# Filtered stream mapping - only processes expenses with scanId (from SmartScans)
resource "aws_lambda_event_source_mapping" "expense_stream_handler" {
  event_source_arn                   = aws_dynamodb_table.expenses.stream_arn
  function_name                      = "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:expender-${var.environment}-expense_stream_handler"
  starting_position                  = "LATEST"
  batch_size                         = 100
  maximum_batching_window_in_seconds = 0

  filter_criteria {
    filter {
      # Filter for INSERT events with scanId in NewImage (expense created from a Smart Scan)
      pattern = jsonencode({
        "eventName" = ["INSERT"],
        "dynamodb" = {
          "NewImage" = {
            "scanId" = {
              "S" = [
                {
                  "exists" = true
                }
              ]
            }
          }
        }
      })
    }

    filter {
      # Filter for REMOVE events with scanId in OldImage (deleted expense which was created from a Smart Scan)
      pattern = jsonencode({
        "eventName" = ["REMOVE"],
        "dynamodb" = {
          "OldImage" = {
            "scanId" = {
              "S" = [
                {
                  "exists" = true
                }
              ]
            }
          }
        }
      })
    }
  }

  tags = {
    Environment = var.environment
    Name        = "expenses-stream-mapping"
  }

  depends_on = [aws_lambda_function.expense_stream_handler]
}

# SmartScan results table with TTL
resource "aws_dynamodb_table" "smartscans" {
  name         = local.smartscans_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "scanId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "scanId"
    type = "S"
  }

  ttl {
    attribute_name = "expireAt"
    enabled        = true
  }

  tags = {
    Environment = var.environment
    Name        = local.smartscans_table_name
  }
}

# User quotas and plan management table
resource "aws_dynamodb_table" "quotas" {
  name             = local.quotas_table_name
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "userId"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "plan"
    type = "S"
  }

  ttl {
    attribute_name = "expireAt"
    enabled        = true
  }

  # GSI for plan-based queries (e.g., to check plan limits)
  global_secondary_index {
    name               = "PlanIndex"
    hash_key           = "plan"
    range_key          = "userId"
    projection_type    = "INCLUDE"
    non_key_attributes = ["smartScanCount", "expireAt"]
  }

  tags = {
    Environment = var.environment
    Name        = local.quotas_table_name
  }
}
