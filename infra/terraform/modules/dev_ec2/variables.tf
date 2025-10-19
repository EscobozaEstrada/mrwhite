# modules/dev_ec2/variables.tf
# Variables for Developer EC2 instance module

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "organization" {
  description = "Organization name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the instance will be created"
  type        = string
}

variable "public_subnet_id" {
  description = "Public subnet ID for the EC2 instance"
  type        = string
}

variable "key_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
}

variable "dev_ip_address" {
  description = "Developer's IP address for SSH access (CIDR format, e.g., '1.2.3.4/32')"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "ssm_parameter_path" {
  description = "SSM Parameter Store path prefix for application secrets"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for development workstation"
  type        = string
  default     = "t3.xlarge"
}

variable "root_volume_size" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 50
}

variable "auto_stop_cpu_threshold" {
  description = "CPU threshold percentage for auto-stop (instance stops if CPU below this for 30 minutes)"
  type        = number
  default     = 5
}

variable "auto_stop_evaluation_periods" {
  description = "Number of periods (each 10 minutes) of low CPU before auto-stop"
  type        = number
  default     = 3
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
