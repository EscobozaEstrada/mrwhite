# outputs.tf
# Global outputs from the root Terraform module

# === Application URLs ===
output "app_runner_url" {
  description = "The URL of the AWS App Runner backend service"
  value       = module.app_runner.app_runner_service_url
}

output "amplify_app_url" {
  description = "The default URL of the AWS Amplify Hosting frontend application"
  value       = module.amplify_hosting.amplify_default_domain
}

output "custom_frontend_url" {
  description = "The custom domain URL for the frontend application"
  value       = var.custom_domain_name != "yourdomain.com" ? "https://${var.app_subdomain_name}.${var.custom_domain_name}" : "Not configured"
}

# === Database Information ===
output "rds_endpoint" {
  description = "The endpoint for the RDS PostgreSQL database"
  value       = module.rds.rds_endpoint
}

output "rds_port" {
  description = "The port for the RDS PostgreSQL database"
  value       = module.rds.rds_port
}

output "rds_database_name" {
  description = "The name of the RDS PostgreSQL database"
  value       = module.rds.rds_db_name
}

output "rds_username" {
  description = "The username for the RDS PostgreSQL database"
  value       = module.rds.rds_db_username
  sensitive   = true
}

# === Storage Information ===
output "s3_bucket_name" {
  description = "The name of the S3 bucket for document storage"
  value       = module.s3_storage.s3_bucket_id
}

output "s3_bucket_arn" {
  description = "The ARN of the S3 bucket for document storage"
  value       = module.s3_storage.s3_bucket_arn
}

output "s3_bucket_domain_name" {
  description = "The domain name of the S3 bucket"
  value       = module.s3_storage.s3_bucket_domain_name
}

# === Networking Information ===
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

# Note: NAT Gateway is not deployed in this cost-optimized architecture
# App Runner uses default public egress for external traffic

# === Security Information ===
output "app_runner_security_group_id" {
  description = "Security group ID for App Runner service"
  value       = module.vpc.app_runner_sg_id
}

output "rds_security_group_id" {
  description = "Security group ID for RDS database"
  value       = module.vpc.rds_sg_id
}

# === IAM Information ===
output "app_runner_instance_role_arn" {
  description = "ARN of the App Runner instance role"
  value       = module.iam_roles.app_runner_instance_role_arn
}

output "app_runner_access_role_arn" {
  description = "ARN of the App Runner access role"
  value       = module.iam_roles.app_runner_access_role_arn
}

output "amplify_service_role_arn" {
  description = "ARN of the Amplify service role with SSM access"
  value       = module.amplify_hosting.amplify_service_role_arn
}

output "amplify_ssm_policy_arn" {
  description = "ARN of the Amplify SSM access policy"
  value       = module.amplify_hosting.amplify_ssm_policy_arn
}

# === Secrets Management ===
# All secrets are stored in SSM Parameter Store and managed outside Terraform
# Path: /monetizespirit/mrwhite/{environment}/*
output "ssm_parameter_path" {
  description = "SSM Parameter Store path prefix for all secrets"
  value       = "/${var.organization}/${var.project_name}/${var.environment}/"
}

output "amplify_cname_validation_records" {
  description = "CNAME records to add to your DNS provider for custom domain validation"
  value       = try(module.amplify_hosting.amplify_domain_association_cname_records, [])
}

# === Environment Configuration ===
output "environment_variables_summary" {
  description = "Summary of environment variables configured for App Runner"
  value = {
    secrets_managed_in_ssm = "Yes - All secrets in SSM Parameter Store"
    database_password      = "AWS RDS Managed Password (Secrets Manager)"
    s3_bucket_configured   = "Yes"
    ssm_parameter_path     = "/${var.organization}/${var.project_name}/${var.environment}/"
  }
}

# === Deployment Information ===
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    project_name = var.project_name
    environment  = var.environment
    aws_region   = var.aws_region
    vpc_cidr     = var.vpc_cidr
    deployed_at  = timestamp()
  }
}

# === Developer Environment (Optional) ===
output "dev_ec2_connection" {
  description = "Connection details for the developer EC2 workstation (if created)"
  value       = var.create_dev_ec2_instance ? module.dev_ec2[0].connection_info : null
}

output "dev_ec2_public_ip" {
  description = "Public IP of developer workstation (if created)"
  value       = var.create_dev_ec2_instance ? module.dev_ec2[0].instance_public_ip : null
}

output "developer_policy_arn" {
  description = "IAM policy ARN attached to developer user (if created)"
  value       = var.create_dev_ec2_instance ? module.developer_iam[0].policy_arn : null
}