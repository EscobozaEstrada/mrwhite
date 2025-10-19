variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where endpoints will be created"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block for security group rules"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for interface endpoints"
  type        = list(string)
}

variable "route_table_ids" {
  description = "List of route table IDs for gateway endpoints (S3)"
  type        = list(string)
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "enable_ecr_endpoints" {
  description = "Enable ECR VPC endpoints (needed if using custom container images)"
  type        = bool
  default     = false
}

variable "enable_cloudwatch_endpoint" {
  description = "Enable CloudWatch Logs VPC endpoint"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
