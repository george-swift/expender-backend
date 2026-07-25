variable "aws_region" {
  type        = string
  description = "AWS region to deploy resources"
  default     = "us-east-1"
}

variable "clerk_secret_key" {
  type        = string
  description = "Clerk secret key for network-based token verification"
  sensitive   = true
}

variable "clerk_jwt_public_key" {
  type        = string
  description = "Clerk JWT public key in PEM format for networkless token verification"
  sensitive   = true
}

variable "clerk_webhook_signing_secret" {
  type        = string
  description = "Clerk webhook signing secret for secure webhook handling"
  sensitive   = true
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  default     = "dev"
}

variable "frontend_app_url" {
  type        = string
  description = "URL of the frontend app."
}

variable "frontend_dev_app_url" {
  type        = string
  description = "URL of the frontend development app."
  default     = "http://localhost:3000"
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API key for AI features"
  sensitive   = true
}

variable "smartscan_encryption_key" {
  description = "Encryption key for securing temporary auth tokens in S3 metadata"
  type        = string
  sensitive   = true
}

variable "stripe_cancel_url" {
  type        = string
  description = "Stripe Checkout cancellation redirect URL"
  default     = ""
}

variable "stripe_price_id_monthly" {
  type        = string
  description = "Stripe Price ID for the $20 monthly premium subscription"
  default     = ""
}

variable "stripe_secret_key" {
  type        = string
  description = "Stripe secret key for billing operations"
  sensitive   = true
  default     = ""
}

variable "stripe_success_url" {
  type        = string
  description = "Stripe Checkout success redirect URL"
  default     = ""
}

variable "stripe_webhook_secret" {
  type        = string
  description = "Stripe webhook endpoint signing secret"
  sensitive   = true
  default     = ""
}
