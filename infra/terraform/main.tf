# main.tf
# Top-level orchestrator for all infrastructure modules

# === Data Sources ===
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values for consistent naming and tagging
locals {
  # Use provided AZs or automatically select available ones
  availability_zones = length(var.azs) > 0 ? var.azs : slice(data.aws_availability_zones.available.names, 0, 2)
  
  # Common naming convention
  name_prefix = "${var.project_name}-${var.environment}"
  
  # Common tags
  common_tags = merge(
    {
      Project      = var.project_name
      Environment  = var.environment
      Organization = var.organization
      ManagedBy    = "terraform"
      CreatedBy    = "terraform-cli"
    },
    var.additional_tags
  )
  
  # Environment-specific configurations
  db_instance_class = var.db_instance_class
  
  # Generate secure random identifier for resources that need global uniqueness
  resource_suffix = random_id.resource_suffix.hex
}

# Random ID for resource naming
resource "random_id" "resource_suffix" {
  byte_length = 4
}

data "aws_ssm_parameter" "github_token" {
  name            = "/monetizespirit/mrwhite/prod/github_token"
  with_decryption = true
}

# === Frontend Environment Variables ===
# Amplify will fetch SSM parameters directly during build via AWS CLI
# This avoids storing secrets in Terraform state

# === VPC and Networking ===
module "vpc" {
  source = "./modules/vpc"
  
  aws_region           = var.aws_region
  project_name         = var.project_name
  environment          = var.environment
  organization         = var.organization
  
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  azs                  = local.availability_zones
  
  # Enable NAT Gateway for App Runner's outbound traffic from private subnets
  enable_nat_gateway   = true
  enable_vpn_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = local.common_tags
}

# === Secrets Management (SSM Parameter Store) ===
# All secrets are uploaded directly to SSM Parameter Store using the upload_secrets_to_ssm.py script
# Path: /monetizespirit/mrwhite/{environment}/parameter_name
# No secrets are managed through Terraform to ensure zero secrets in Terraform state
# The application retrieves secrets at runtime using SSM-aware configuration

# === IAM Roles and Policies ===
module "iam_roles" {
  source = "./modules/iam_roles"
  
  aws_region         = var.aws_region
  project_name       = var.project_name
  environment        = var.environment
  organization       = var.organization
  
  # Will be provided by S3 module
  s3_bucket_arn = module.s3_storage.s3_bucket_arn
  
  # SSM Parameter Store access - parameters are managed outside Terraform
  # All SSM parameters under /monetizespirit/mrwhite/{environment}/*
  ssm_parameter_path_prefix = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.organization}/${var.project_name}/${var.environment}/*"
  
  # Additional IAM permissions for specific services
  enable_bedrock_access         = false  # Set to true if using AWS Bedrock
  enable_ses_access            = true   # For email services
  enable_sns_access            = false  # Disabled for security (least privilege principle)
  enable_cloudwatch_access     = var.enable_monitoring
  enable_secrets_manager_access = true   # Required for RDS managed passwords
  
  tags = local.common_tags
}

# === S3 Storage ===
module "s3_storage" {
  source = "./modules/s3_storage"
  
  aws_region     = var.aws_region
  project_name   = var.project_name
  environment    = var.environment
  organization   = var.organization
  
  bucket_name    = "${local.name_prefix}-documents-${local.resource_suffix}"
  
  # Security configurations
  enable_versioning         = var.enable_backup
  enable_encryption         = true
  enable_public_read_access = false
  enable_lifecycle_rules    = true
  
  # CORS configuration for web application
  cors_allowed_origins = [
    "https://${var.app_subdomain_name}.${var.custom_domain_name}",
    "http://localhost:3000",  # For development
    "https://localhost:3000"  # For development with HTTPS
  ]
  
  tags = local.common_tags
}

# === RDS Database ===
module "rds" {
  source = "./modules/rds"
  
  aws_region   = var.aws_region
  project_name = var.project_name
  environment  = var.environment
  organization = var.organization
  
  # Network configuration
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  rds_sg_id          = module.vpc.rds_sg_id
  
  # Database configuration
  db_instance_class          = local.db_instance_class
  db_name                   = "${var.project_name}_${var.environment}_db"
  db_username               = "${var.project_name}user"
  db_port                   = 5432
  allocated_storage         = var.db_allocated_storage
  max_allocated_storage     = var.db_max_allocated_storage
  
  # Security - use AWS managed password (no password in Terraform state)
  db_password_from_ssm      = true  # Forces AWS to manage the password
  backup_retention_period   = var.db_backup_retention_period
  backup_window             = "03:00-04:00"
  maintenance_window        = "Sun:04:00-Sun:05:00"
  
  # Environment-specific settings
  deletion_protection       = var.environment == "prod"
  skip_final_snapshot      = var.environment != "prod"
  
  # Upgrade controls
  allow_major_version_upgrade = var.allow_major_version_upgrade
  apply_immediately           = var.apply_immediately
  attach_custom_pg_and_og     = var.attach_custom_pg_and_og
  
  tags = local.common_tags
}

# === GitHub Connection for App Runner ===
module "github_connection" {
  source = "./modules/github_connection"
  
  project_name = var.project_name
  environment  = var.environment
  
  tags = local.common_tags
}

# === App Runner Backend Service ===
module "app_runner" {
  source = "./modules/app_runner"
  
  aws_region   = var.aws_region
  project_name = var.project_name
  environment  = var.environment
  organization = var.organization
  
  # GitHub connection for private repository access
  github_connection_arn = module.github_connection.connection_arn
  
  # Service configuration
  service_name = "${local.name_prefix}-backend"
  
  # Repository configuration
  source_repository_url = var.backend_repository_url
  branch_name          = var.backend_branch
  
  # Compute configuration
  cpu_units    = var.app_runner_cpu
  memory_units = var.app_runner_memory
  min_size     = var.app_runner_min_size
  max_size     = var.app_runner_max_size
  port         = var.port

  # Network configuration
  vpc_id             = module.vpc.vpc_id
  # NOTE: Using private subnets; outbound traffic goes through NAT Gateway
  subnet_ids         = module.vpc.private_subnet_ids
  app_runner_sg_id   = module.vpc.app_runner_sg_id
  
  # IAM roles
  app_runner_instance_role_arn = module.iam_roles.app_runner_instance_role_arn
  app_runner_access_role_arn   = module.iam_roles.app_runner_access_role_arn
  
  # Environment variables
  environment_variables = {
    # Application configuration
    FLASK_ENV     = var.environment == "prod" ? "production" : "development"
    FLASK_DEBUG   = var.environment == "prod" ? "False" : "True"
    ENVIRONMENT   = var.environment
    AWS_REGION    = var.aws_region
    
    # Database configuration (using AWS Secrets Manager for password)
    DATABASE_URL = "postgresql://${module.rds.rds_db_username}:{{resolve:secretsmanager:${module.rds.rds_master_user_secret_arn}:SecretString:password}}@${module.rds.rds_endpoint}:${module.rds.rds_port}/${module.rds.rds_db_name}"
    
    # Storage configuration
    S3_BUCKET_NAME = module.s3_storage.s3_bucket_id
    AWS_S3_REGION  = var.aws_region
    
    # Frontend URL for CORS - now constructed with the api_subdomain_name
    FRONTEND_URL = "https://${var.app_subdomain_name}.${var.custom_domain_name}"
  }
  
  # Sensitive environment variables from SSM Parameter Store
  environment_secrets = {
    # API Keys
    OPENAI_API_KEY   = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/openai_api_key}}"
    PINECONE_API_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/pinecone_api_key}}"
    STRIPE_SECRET_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/stripe_secret_key}}"
    
    # Application Security
    SECRET_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/app_secret_key}}"
    JWT_SECRET_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/jwt_secret_key}}"
    
    # Payment Processing
    STRIPE_PUBLISHABLE_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/stripe_publishable_key}}"
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/firebase_project_id}}"
    FIREBASE_API_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/firebase_api_key}}"
    FIREBASE_AUTH_DOMAIN = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/firebase_auth_domain}}"
    FIREBASE_STORAGE_BUCKET = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/firebase_storage_bucket}}"
    FIREBASE_MESSAGING_SENDER_ID = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/firebase_messaging_sender_id}}"
    FIREBASE_APP_ID = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/firebase_app_id}}"
    FIREBASE_MEASUREMENT_ID = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/firebase_measurement_id}}"
    
    # Email Configuration  
    SES_SMTP_HOST = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/ses_smtp_host}}"
    SES_SMTP_PORT = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/ses_smtp_port}}"
    SES_SMTP_USERNAME = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/ses_smtp_username}}"
    SES_SMTP_PASSWORD = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/ses_smtp_password}}"
    SES_EMAIL_FROM = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/ses_email_from}}"
    
    # External APIs
    TEXTBELT_API_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/textbelt_api_key}}"
    
    # Pinecone Configuration
    PINECONE_ENVIRONMENT = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/pinecone_environment}}"
    PINECONE_INDEX_NAME = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/pinecone_index_name}}"
    
    # OpenAI Configuration
    OPENAI_EMBEDDING_MODEL = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/openai_embedding_model}}"
    OPENAI_CHAT_MODEL = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/openai_chat_model}}"
    OPENAI_TEMPERATURE = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/openai_temperature}}"
    OPENAI_MAX_TOKENS = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/openai_max_tokens}}"
    OPENAI_FILE_UPLOAD_TEMPERATURE = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/openai_file_upload_temperature}}"
    
    # JWT Configuration
    JWT_EXPIRY_DAYS = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/jwt_expiry_days}}"
    JWT_ALGORITHM = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/jwt_algorithm}}"
    
    # Cookie Configuration
    COOKIE_SECURE = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/cookie_secure}}"
    COOKIE_HTTPONLY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/cookie_httponly}}"
    COOKIE_SAMESITE = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/cookie_samesite}}"
    COOKIE_MAX_AGE = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/cookie_max_age}}"
    
    # Flask Configuration
    FLASK_HOST = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/flask_host}}"
    FLASK_PORT = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/flask_port}}"
    
    # CORS Configuration
    CORS_MAX_AGE = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/cors_max_age}}"
    
    # VAPID Keys for Push Notifications
    VAPID_PRIVATE_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/vapid_private_key}}"
    VAPID_PUBLIC_KEY = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/vapid_public_key}}"
    VAPID_EMAIL = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/vapid_email}}"
    
    # Firebase Service Account JSON
    FIREBASE_SERVICE_ACCOUNT_JSON = "{{resolve:ssm:/${var.organization}/${var.project_name}/${var.environment}/firebase_service_account_json}}"
  }
  
  # Health check configuration
  health_check_path = "/health"
  
  tags = local.common_tags
}

# === Amplify Hosting Frontend Service ===
module "amplify_hosting" {
  source = "./modules/amplify_hosting"
  
  aws_region   = var.aws_region
  project_name = var.project_name
  environment  = var.environment
  organization = var.organization
  
  # Application configuration
  app_name       = "${local.name_prefix}-frontend"
  repository_url = var.frontend_repository_url
  branch_name    = var.frontend_branch
  github_access_token = data.aws_ssm_parameter.github_token.value
  
  # Domain configuration is handled manually in the AWS console
  
  # Build configuration
  # Note: NEXT_PUBLIC_ environment variables are fetched directly from SSM
  # during the Amplify build via AWS CLI in amplify.yml
  # This avoids storing secrets in Terraform state
  build_environment_variables = {
    # --- Dynamically Set ---
    NEXT_PUBLIC_API_BASE_URL = module.app_runner.app_runner_service_url,
    NEXT_PUBLIC_APP_NAME     = var.project_name,
    NEXT_PUBLIC_ENVIRONMENT  = var.environment,
    NEXT_PUBLIC_BUILD_ENV    = var.environment,
  }
  
  # Monorepo configuration - only build when frontend/ directory changes
  app_root_path = "frontend"
  
  # Framework detection
  framework = "Next.js - SSG"
  
  # Create a dedicated service role for Amplify
  create_service_role = true
  
  # SSM Parameter Store access for environment variables
  ssm_parameter_prefix = "${var.organization}/${var.project_name}/${var.environment}"

  tags = local.common_tags
}

# === Developer Environment (Optional) ===
# IAM permissions for developer to manage their EC2 instance
module "developer_iam" {
  count  = var.create_dev_ec2_instance ? 1 : 0
  source = "./modules/developer_iam"
  
  username     = var.dev_username
  project_name = var.project_name
  environment  = var.environment
  
  tags = local.common_tags
}

# Developer EC2 workstation with auto-stop and pre-loaded secrets
module "dev_ec2" {
  count  = var.create_dev_ec2_instance ? 1 : 0
  source = "./modules/dev_ec2"
  
  project_name       = var.project_name
  environment        = var.environment
  organization       = var.organization
  vpc_id             = module.vpc.vpc_id
  public_subnet_id   = module.vpc.public_subnet_ids[0]
  key_name           = var.dev_ec2_key_name
  dev_ip_address     = var.dev_ip_address
  aws_region         = var.aws_region
  ssm_parameter_path = "/${var.organization}/${var.project_name}/${var.environment}"
  instance_type      = var.dev_instance_type
  
  tags = local.common_tags
  
  depends_on = [
    module.vpc,
    module.developer_iam
  ]
}