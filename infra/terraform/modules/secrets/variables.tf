# modules/secrets/variables.tf
# Variables for the secrets management module

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

variable "secret_name_prefix" {
  description = "Prefix for SSM parameter names (e.g., /myorg/myproject/prod/)"
  type        = string
  
  validation {
    condition     = can(regex("^/.*/$", var.secret_name_prefix))
    error_message = "Secret name prefix must start and end with '/'."
  }
}

variable "secrets_map" {
  description = "Map of secret names to values"
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "generate_random_secrets" {
  description = "Map of secret names to password generation configuration"
  type = map(object({
    length      = number
    special     = bool
    upper       = bool
    lower       = bool
    numeric     = bool
    min_upper   = number
    min_lower   = number
    min_numeric = number
    min_special = number
  }))
  default = {}
}

variable "create_kms_key" {
  description = "Create a dedicated KMS key for secrets encryption"
  type        = bool
  default     = false
}

variable "enable_secrets_rotation" {
  description = "Enable automatic secrets rotation"
  type        = bool
  default     = false
}

variable "secrets_rotation_schedule" {
  description = "EventBridge schedule expression for secrets rotation"
  type        = string
  default     = "rate(30 days)"
}

variable "rotation_lambda_timeout" {
  description = "Timeout for secrets rotation Lambda function"
  type        = number
  default     = 60
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}