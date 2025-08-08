# ============================================================================
# S3 STORAGE AND CLOUDFRONT DISTRIBUTION
# ============================================================================

# S3 bucket for file assets (receipts, documents)
resource "aws_s3_bucket" "assets" {
  bucket = local.assets_bucket_name

  tags = {
    Environment = var.environment
    Name = local.assets_bucket_name
  }
}

# Server-side encryption for all bucket objects
resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# CORS configuration for frontend file uploads
resource "aws_s3_bucket_cors_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = [var.frontend_app_url, var.frontend_dev_app_url]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Block all public access to S3 bucket
resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Origin Access Control for secure CloudFront-S3 integration
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "${local.assets_bucket_name}-oac"
  description                       = "OAC for ${local.assets_bucket_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}


# CloudFront cache policy for optimized file delivery
resource "aws_cloudfront_cache_policy" "assets_cache_policy" {
  name        = "${local.cdn_name}-cache-policy"
  comment     = "Cache policy for file assets"
  default_ttl = 1800
  max_ttl     = 3600
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

# CloudFront distribution for global file delivery
resource "aws_cloudfront_distribution" "assets" {
  origin {
    domain_name = aws_s3_bucket.assets.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
    origin_id   = "S3-${aws_s3_bucket.assets.id}"
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = ""

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.assets.id}"

    cache_policy_id = aws_cloudfront_cache_policy.assets_cache_policy.id

    viewer_protocol_policy = "https-only"
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Environment = var.environment
    Name        = local.cdn_name
  }

   depends_on = [
    aws_s3_bucket.assets,
    aws_cloudfront_cache_policy.assets_cache_policy
  ]
}

# S3 bucket policy for service access and CloudFront integration
resource "aws_s3_bucket_policy" "assets" {
  bucket = aws_s3_bucket.assets.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          AWS = aws_iam_role.api_service_role.arn
        }
        Action    = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Resource  = "${aws_s3_bucket.assets.arn}/*"
      },
      {
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.assets.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.assets.arn
          }
        }
      }
    ]
  })

  depends_on = [
    aws_iam_role.api_service_role,
    aws_cloudfront_distribution.assets,
    aws_s3_bucket_public_access_block.assets
  ]
}

# S3 event notification for SmartScan processing trigger
resource "aws_s3_bucket_notification" "assets_bucket_notification" {
  bucket = local.assets_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.bucket_event_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "smartscans/"
  }

  depends_on = [
    aws_lambda_function.bucket_event_handler
  ]
}
