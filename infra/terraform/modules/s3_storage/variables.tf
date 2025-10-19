# modules/s3_storage/variables.tf
# Variables for the S3 storage module

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

variable "bucket_name" {
  description = "Name of the S3 bucket (must be globally unique)"
  type        = string
}

# Security Configuration
variable "enable_encryption" {
  description = "Enable server-side encryption"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (uses AWS managed key if not specified)"
  type        = string
  default     = null
}

variable "enable_public_read_access" {
  description = "Enable public read access for specific objects"
  type        = bool
  default     = false
}

# Versioning and Lifecycle
variable "enable_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "enable_lifecycle_rules" {
  description = "Enable S3 lifecycle rules"
  type        = bool
  default     = true
}

variable "enable_intelligent_tiering" {
  description = "Enable S3 Intelligent Tiering"
  type        = bool
  default     = false
}

# CORS Configuration
variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = []
}

# Logging
variable "enable_access_logging" {
  description = "Enable S3 access logging"
  type        = bool
  default     = true
}

variable "access_logs_retention_days" {
  description = "Number of days to retain access logs"
  type        = number
  default     = 90
}

# Notifications
variable "enable_event_notifications" {
  description = "Enable S3 event notifications"
  type        = bool
  default     = false
}

variable "notification_topics" {
  description = "SNS topics for S3 event notifications"
  type = list(object({
    arn    = string
    events = list(string)
    prefix = string
    suffix = string
  }))
  default = []
}

variable "notification_lambdas" {
  description = "Lambda functions for S3 event notifications"
  type = list(object({
    arn    = string
    events = list(string)
    prefix = string
    suffix = string
  }))
  default = []
}

# Monitoring
variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "bucket_size_alarm_threshold" {
  description = "Bucket size alarm threshold in bytes"
  type        = number
  default     = 10737418240  # 10 GB
}

variable "object_count_alarm_threshold" {
  description = "Object count alarm threshold"
  type        = number
  default     = 10000
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}