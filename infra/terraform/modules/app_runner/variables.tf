# modules/app_runner/variables.tf
# Variables for the App Runner module

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

# Service Configuration
variable "service_name" {
  description = "Name of the App Runner service"
  type        = string
}

variable "github_connection_arn" {
  description = "ARN of the GitHub connection for App Runner (required for private repositories)"
  type        = string
}

variable "source_repository_url" {
  description = "GitHub repository URL"
  type        = string
}

variable "branch_name" {
  description = "Git branch name"
  type        = string
  default     = "main"
}

variable "enable_auto_deployments" {
  description = "Enable automatic deployments"
  type        = bool
  default     = true
}

# Runtime Configuration
variable "runtime" {
  description = "Runtime for the application"
  type        = string
  default     = "PYTHON_3"
}

variable "build_command" {
  description = "Build command"
  type        = string
  default     = "pip install -r requirements.txt"
}

variable "start_command" {
  description = "Start command"
  type        = string
  default     = "gunicorn --bind 0.0.0.0:8000 wsgi:application"
}

# Compute Configuration
variable "cpu_units" {
  description = "CPU units: either raw sizes (256, 512, 1024, 2048, 4096) or scalar values (0.25, 0.5, 1, 2, 4)"
  type        = string
  default     = "0.25"

  validation {
    condition = (
      contains(["0.25", "0.5", "1", "2", "4"], var.cpu_units)
      || contains(["256", "512", "1024", "2048", "4096"], var.cpu_units)
    )
    error_message = "CPU units must be one of: 0.25, 0.5, 1, 2, 4 or 256, 512, 1024, 2048, 4096."
  }
}

variable "memory_units" {
  description = "Memory in MB (512, 1024, 2048, 4096, 8192, 12288 MB)"
  type        = string
  default     = "512"
  
  validation {
    condition     = contains(["512", "1024", "2048", "4096", "8192", "12288"], var.memory_units)
    error_message = "Memory units must be one of: 512, 1024, 2048, 4096, 8192, 12288."
  }
}

# Auto Scaling
variable "min_size" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
  
  validation {
    condition     = var.min_size >= 1 && var.min_size <= 25
    error_message = "Minimum size must be between 1 and 25."
  }
}

variable "max_size" {
  description = "Maximum number of instances"
  type        = number
  default     = 3
  
  validation {
    condition     = var.max_size >= 1 && var.max_size <= 25
    error_message = "Maximum size must be between 1 and 25."
  }
}

# Network Configuration
variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "app_runner_sg_id" {
  description = "Security Group ID for App Runner"
  type        = string
}

variable "is_publicly_accessible" {
  description = "Whether the service should be publicly accessible"
  type        = bool
  default     = true
}

# IAM Configuration
variable "app_runner_instance_role_arn" {
  description = "ARN of the App Runner instance role"
  type        = string
}

variable "app_runner_access_role_arn" {
  description = "ARN of the App Runner access role"
  type        = string
}

# Environment Variables
variable "environment_variables" {
  description = "Environment variables for the application"
  type        = map(string)
  default     = {}
}

variable "environment_secrets" {
  description = "Environment secrets (stored in AWS Secrets Manager or SSM)"
  type        = map(string)
  default     = {}
  sensitive   = true
}

# Health Check Configuration
variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/"
}

variable "health_check_protocol" {
  description = "Health check protocol"
  type        = string
  default     = "HTTP"
  
  validation {
    condition     = contains(["HTTP", "TCP"], var.health_check_protocol)
    error_message = "Health check protocol must be HTTP or TCP."
  }
}

variable "health_check_interval" {
  description = "Health check interval in seconds"
  type        = number
  default     = 10
  
  validation {
    condition     = var.health_check_interval >= 5 && var.health_check_interval <= 20
    error_message = "Health check interval must be between 5 and 20 seconds."
  }
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  type        = number
  default     = 5
  
  validation {
    condition     = var.health_check_timeout >= 2 && var.health_check_timeout <= 20
    error_message = "Health check timeout must be between 2 and 20 seconds."
  }
}

variable "health_check_healthy_threshold" {
  description = "Number of consecutive successful health checks"
  type        = number
  default     = 1
  
  validation {
    condition     = var.health_check_healthy_threshold >= 1 && var.health_check_healthy_threshold <= 20
    error_message = "Health check healthy threshold must be between 1 and 20."
  }
}

variable "health_check_unhealthy_threshold" {
  description = "Number of consecutive failed health checks"
  type        = number
  default     = 5
  
  validation {
    condition     = var.health_check_unhealthy_threshold >= 2 && var.health_check_unhealthy_threshold <= 20
    error_message = "Health check unhealthy threshold must be between 2 and 20."
  }
}

# Custom Domain
variable "custom_domain_name" {
  description = "Custom domain name for the service"
  type        = string
  default     = null
}

variable "enable_www_subdomain" {
  description = "Enable www subdomain for custom domain"
  type        = bool
  default     = false
}

# Observability
variable "enable_observability" {
  description = "Enable observability (tracing)"
  type        = bool
  default     = true
}

variable "observability_configuration_arn" {
  description = "ARN of existing observability configuration"
  type        = string
  default     = null
}

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# Monitoring
variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring and alarms"
  type        = bool
  default     = true
}

variable "alarm_actions" {
  description = "List of ARNs to notify when alarms trigger"
  type        = list(string)
  default     = []
}

# Alarm Thresholds
variable "cpu_alarm_threshold" {
  description = "CPU utilization alarm threshold (percentage)"
  type        = number
  default     = 80
}

variable "memory_alarm_threshold" {
  description = "Memory utilization alarm threshold (percentage)"
  type        = number
  default     = 85
}

variable "request_count_threshold" {
  description = "Request count threshold for alarms"
  type        = number
  default     = 1000
}

variable "error_4xx_threshold" {
  description = "4xx error count threshold"
  type        = number
  default     = 50
}

variable "error_5xx_threshold" {
  description = "5xx error count threshold"
  type        = number
  default     = 10
}

variable "response_time_threshold" {
  description = "Response time threshold in milliseconds"
  type        = number
  default     = 5000
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "port" {
  description = "Port on which the application listens"
  type        = string
  default     = "8000"
}
