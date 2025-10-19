# variables.tf
# Global variables for the root Terraform module
# These can be overridden via .tfvars files
# NOTE: Sensitive secrets are NOT managed via Terraform variables - they are stored in SSM Parameter Store

# === Core Configuration ===
variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
  
  validation {
    condition = can(regex("^(us|eu|ap|sa|ca|me|af)-(north|south|east|west|central|northeast|northwest|southeast|southwest)-[0-9]+$", var.aws_region))
    error_message = "AWS region must be a valid AWS region format."
  }
}

variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  default     = "mrwhite"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "organization" {
  description = "Organization name (used for resource naming and tagging)"
  type        = string
  default     = "monetizespirit"
}

# === Networking Configuration ===
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "List of CIDR blocks for public subnets across AZs"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "List of CIDR blocks for private subnets across AZs"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "azs" {
  description = "List of Availability Zones to use (leave empty for automatic selection)"
  type        = list(string)
  default     = []
}

# === Database Configuration ===
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "RDS maximum allocated storage for autoscaling"
  type        = number
  default     = 100
}

variable "db_backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

# RDS upgrade controls
variable "allow_major_version_upgrade" {
  description = "Allow upgrading the RDS engine across major versions (e.g., 15 -> 17)"
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply RDS modifications immediately (may cause downtime)"
  type        = bool
  default     = false
}

variable "attach_custom_pg_and_og" {
  description = "Attach custom RDS parameter and option groups to the DB instance; set to false during major upgrade to use defaults, then true to reattach v17 groups"
  type        = bool
  default     = true
}

# === App Runner Configuration ===
variable "app_runner_cpu" {
  description = "App Runner CPU units (0.25, 0.5, 1, 2, 4 vCPU)"
  type        = string
  default     = "0.25"
}

variable "app_runner_memory" {
  description = "App Runner memory in MB (512, 1024, 2048, 4096, 8192, 12288 MB)"
  type        = string
  default     = "512"
}

variable "app_runner_min_size" {
  description = "Minimum number of App Runner instances"
  type        = number
  default     = 1
}

variable "app_runner_max_size" {
  description = "Maximum number of App Runner instances"
  type        = number
  default     = 3
}

# === Repository Configuration ===
variable "backend_repository_url" {
  description = "GitHub repository URL for the backend application"
  type        = string
  default     = "https://github.com/your-org/your-backend-repo.git"
}

variable "frontend_repository_url" {
  description = "GitHub repository URL for the frontend application"
  type        = string
  default     = "https://github.com/your-org/your-frontend-repo.git"
}

variable "backend_branch" {
  description = "Git branch for backend deployment"
  type        = string
  default     = "main"
}

variable "frontend_branch" {
  description = "Git branch for frontend deployment"
  type        = string
  default     = "main"
}

# === Domain Configuration ===
variable "custom_domain_name" {
  description = "Custom domain name for the application (e.g., example.com)"
  type        = string
  default     = "yourdomain.com"
}

variable "app_subdomain_name" {
  description = "Subdomain for the frontend application (e.g., app, www)"
  type        = string
  default     = "app"
}

variable "api_subdomain_name" {
  description = "Subdomain for the API/backend (e.g., api, backend)"
  type        = string
  default     = "api"
}

# === Secrets Management ===
# All sensitive secrets (API keys, passwords, etc.) are stored in AWS SSM Parameter Store
# and accessed at runtime by the application. No secrets are passed through Terraform.
# Database passwords are automatically generated and managed by AWS RDS.
# This ensures zero secrets in Terraform state for maximum security.

# === Feature Flags ===
# Note: S3 Gateway VPC endpoint is always enabled for cost optimization
# No enable_vpc_endpoints flag needed - networking is optimized by default

variable "enable_bastion_host" {
  description = "Enable bastion host for database access"
  type        = bool
  default     = false
}

variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring and alerting"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated backups for RDS and S3"
  type        = bool
  default     = true
}

# === Additional Configuration ===
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "port" {
  description = "Port on which the application listens"
  type        = string
  default     = "8000"
}

# === Developer Environment (Optional) ===
variable "create_dev_ec2_instance" {
  description = "Create optional developer EC2 workstation (set to true to provision)"
  type        = bool
  default     = false
}

variable "dev_ec2_key_name" {
  description = "Name of EC2 key pair for developer SSH access (required if create_dev_ec2_instance is true)"
  type        = string
  default     = ""
}

variable "dev_ip_address" {
  description = "Developer's IP address for SSH access in CIDR format (e.g., '1.2.3.4/32')"
  type        = string
  default     = ""
}

variable "dev_username" {
  description = "IAM username for the developer (must already exist)"
  type        = string
  default     = "Atul"
}

variable "dev_instance_type" {
  description = "EC2 instance type for developer workstation"
  type        = string
  default     = "t3.xlarge"
}
