# modules/networking_egress/variables.tf
# Variables for cost-optimized networking (S3 Gateway Endpoint only)

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

variable "vpc_id" {
  description = "VPC ID where the S3 Gateway endpoint will be created"
  type        = string
}

variable "private_route_table_ids" {
  description = "List of private route table IDs for the S3 Gateway endpoint"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Note: All endpoint feature flags removed - only S3 Gateway endpoint is created
# App Runner handles all other external traffic via default public egress