# modules/iam_roles/variables.tf
# Variables for the IAM roles module

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "organization" {
  description = "Organization name"
  type        = string
}

# Resource ARNs
variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket for access policy"
  type        = string
}

variable "ssm_parameter_path_prefix" {
  description = "ARN path prefix for SSM parameters (e.g., arn:aws:ssm:region:account:parameter/org/project/env/*)"
  type        = string
  default     = ""
}

# Feature flags for different AWS services
variable "enable_cloudwatch_access" {
  description = "Enable CloudWatch Logs access"
  type        = bool
  default     = true
}

variable "enable_ses_access" {
  description = "Enable SES (Simple Email Service) access"
  type        = bool
  default     = true
}

variable "enable_sns_access" {
  description = "Enable SNS (Simple Notification Service) access"
  type        = bool
  default     = true
}

variable "enable_bedrock_access" {
  description = "Enable Amazon Bedrock access"
  type        = bool
  default     = false
}

variable "enable_secrets_manager_access" {
  description = "Enable AWS Secrets Manager access"
  type        = bool
  default     = false
}

variable "enable_lambda_invoke" {
  description = "Enable Lambda function invocation"
  type        = bool
  default     = false
}

variable "enable_dynamodb_access" {
  description = "Enable DynamoDB access"
  type        = bool
  default     = false
}

# Custom policies
variable "custom_policy_json" {
  description = "Custom IAM policy JSON"
  type        = string
  default     = ""
}

variable "additional_managed_policy_arns" {
  description = "List of additional AWS managed policy ARNs to attach"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}