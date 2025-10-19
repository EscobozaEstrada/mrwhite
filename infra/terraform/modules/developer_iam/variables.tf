# modules/developer_iam/variables.tf
# Variables for Developer IAM permissions module

variable "username" {
  description = "Name of the existing IAM user to grant developer permissions"
  type        = string
}

variable "project_name" {
  description = "Name of the project (used for naming and tagging)"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "Additional tags to apply to IAM policy"
  type        = map(string)
  default     = {}
}
