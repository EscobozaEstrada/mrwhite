# modules/amplify_hosting/variables.tf
# Variables for the Amplify Hosting module

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

# App Configuration
variable "app_name" {
  description = "Name of the Amplify app"
  type        = string
}

variable "repository_url" {
  description = "Repository URL (GitHub, GitLab, Bitbucket, etc.)"
  type        = string
}

variable "platform" {
  description = "Platform for the Amplify app"
  type        = string
  default     = "WEB"
  
  validation {
    condition     = contains(["WEB", "WEB_COMPUTE"], var.platform)
    error_message = "Platform must be either WEB or WEB_COMPUTE."
  }
}

# Branch Configuration
variable "branch_name" {
  description = "Name of the branch to deploy"
  type        = string
  default     = "main"
}

variable "branch_stage" {
  description = "Stage for the branch"
  type        = string
  default     = "PRODUCTION"
  
  validation {
    condition     = contains(["PRODUCTION", "BETA", "DEVELOPMENT", "EXPERIMENTAL"], var.branch_stage)
    error_message = "Branch stage must be one of: PRODUCTION, BETA, DEVELOPMENT, EXPERIMENTAL."
  }
}

variable "enable_auto_build" {
  description = "Enable automatic builds for the branch"
  type        = bool
  default     = true
}

# Build Configuration
variable "framework" {
  description = "Framework for the application"
  type        = string
  default     = "Next.js - SSG"
}

variable "node_version" {
  description = "Node.js version for builds"
  type        = string
  default     = "18"
}

variable "build_spec" {
  description = "Custom build specification (YAML)"
  type        = string
  default     = ""
}

variable "app_root_path" {
  description = "Root path for monorepo applications"
  type        = string
  default     = ""
}

variable "output_directory" {
  description = "Output directory for built files"
  type        = string
  default     = ".next"
}

variable "cache_paths" {
  description = "Paths to cache during builds"
  type        = list(string)
  default     = ["node_modules/**/*", ".next/cache/**/*"]
}

# Environment Variables
variable "build_environment_variables" {
  description = "Environment variables for build process"
  type        = map(string)
  default     = {}
}

variable "branch_environment_variables" {
  description = "Environment variables for the branch"
  type        = map(string)
  default     = {}
}

# Authentication
variable "github_access_token" {
  description = "GitHub personal access token"
  type        = string
  default     = null
  sensitive   = true
}

variable "oauth_token" {
  description = "OAuth token for repository access"
  type        = string
  default     = null
  sensitive   = true
}

variable "enable_basic_auth" {
  description = "Enable basic authentication for the app"
  type        = bool
  default     = false
}

variable "basic_auth_username" {
  description = "Basic auth username"
  type        = string
  default     = ""
  sensitive   = true
}

variable "basic_auth_password" {
  description = "Basic auth password"
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_branch_basic_auth" {
  description = "Enable basic auth for specific branch"
  type        = bool
  default     = false
}

variable "branch_basic_auth_username" {
  description = "Basic auth username for branch"
  type        = string
  default     = ""
  sensitive   = true
}

variable "branch_basic_auth_password" {
  description = "Basic auth password for branch"
  type        = string
  default     = ""
  sensitive   = true
}

# Custom Domain
variable "custom_domain_name" {
  description = "Custom domain name"
  type        = string
  default     = null
}

variable "subdomain_name" {
  description = "Subdomain prefix"
  type        = string
  default     = ""
}

variable "enable_www_subdomain" {
  description = "Enable www subdomain"
  type        = bool
  default     = false
}

variable "enable_auto_sub_domain" {
  description = "Enable automatic subdomain creation"
  type        = bool
  default     = false
}

# Note: certificate_verification_dns_record is a computed output from aws_amplify_domain_association
# It cannot be provided as an input variable

variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for custom domain"
  type        = string
  default     = null
}

# Custom Rules (Redirects/Rewrites)
variable "custom_rules" {
  description = "List of custom rules for redirects and rewrites"
  type = list(object({
    source    = string
    target    = string
    status    = string
    condition = string
  }))
  default = [
    {
      source    = "/<*>"
      target    = "/index.html"
      status    = "404-200"
      condition = null
    }
  ]
}

# Auto Branch Creation
variable "enable_auto_branch_creation" {
  description = "Enable automatic branch creation"
  type        = bool
  default     = false
}

variable "auto_branch_creation_patterns" {
  description = "Patterns for automatic branch creation"
  type        = list(string)
  default     = ["feature/*", "develop"]
}

variable "auto_branch_enable_auto_build" {
  description = "Enable auto build for auto-created branches"
  type        = bool
  default     = true
}

# Performance and Features
variable "enable_performance_mode" {
  description = "Enable performance mode"
  type        = bool
  default     = false
}

variable "enable_pull_request_preview" {
  description = "Enable pull request previews"
  type        = bool
  default     = true
}

# Webhook
variable "enable_webhook" {
  description = "Enable webhook for manual deployments"
  type        = bool
  default     = false
}

# Backend Environment
variable "enable_backend_environment" {
  description = "Enable Amplify backend environment"
  type        = bool
  default     = false
}

variable "backend_environment_name" {
  description = "Name of the backend environment"
  type        = string
  default     = "staging"
}

variable "deployment_artifacts" {
  description = "Deployment artifacts for backend"
  type        = string
  default     = null
}

variable "cloudformation_stack_name" {
  description = "CloudFormation stack name for backend"
  type        = string
  default     = null
}

# Monitoring and Logging
variable "enable_monitoring" {
  description = "Enable monitoring and alarms"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

# Service Role
variable "create_service_role" {
  description = "Create IAM service role for Amplify"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}