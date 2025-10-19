# prod.tfvars.example
# Example Terraform variables file for production environment
# Copy this to prod.tfvars and update the values

# === Core Configuration ===
aws_region     = "us-east-1"
project_name   = "mrwhite"
environment    = "prod"
organization   = "monetizespirit"

# === Repository URLs ===
# Monorepo configuration - both backend and frontend in same repo
backend_repository_url  = "https://github.com/nodeexcel/Mr-White-Project"
frontend_repository_url = "https://github.com/nodeexcel/Mr-White-Project"
backend_branch         = "main"
frontend_branch        = "main"

# === Domain Configuration (UPDATE THIS) ===
custom_domain_name    = "sonoradigitalnetworks.com"   # Your actual production domain
app_subdomain_name    = "mrwhite"                     # Creates app.yourdomain.com
api_subdomain_name    = "mrwhite-api"                         # Creates api.yourdomain.com

# === Database Configuration (Production Settings) ===
db_instance_class        = "db.t3.micro"   # Cost-optimized micro instance
db_allocated_storage     = 50               # 50 GB initial storage
db_max_allocated_storage = 500              # Auto-scale up to 500 GB
db_backup_retention_period = 30             # 30 days backup retention

# === App Runner Configuration (Production Settings) ===
app_runner_cpu    = "1"   # 1 vCPU for production
app_runner_memory = "2048"  # 2048 MB for production
app_runner_min_size = 1     # 1 instance
app_runner_max_size = 10    # 10 instances maximum for scaling

# === Feature Flags (Production Settings) ===
# Note: S3 Gateway VPC endpoint is always enabled (free)
# NAT Gateway is disabled - App Runner uses default public egress for cost optimization
enable_bastion_host     = false  # Set to true if you need database access
enable_monitoring       = true   # Always enabled in production
enable_backup           = false   # Always enabled in production

# === Additional Tags for Production ===
additional_tags = {
  CostCenter   = "engineering"
  Owner        = "platform-team"
  Backup       = "tbd"
  Compliance   = "required"
  Environment  = "production"
}

# === Optional Developer Environment (Set only if needed) ===
create_dev_ec2_instance = true
dev_ec2_key_name        = "mrwhite-aws"
dev_ip_address          = "185.153.177.252/32"
dev_username            = "Atul"               # Existing IAM username
dev_instance_type       = "t3.xlarge"        # Default is t3.xlarge

# === RDS Major Upgrade (Temporary toggles) ===
# Allow upgrading RDS across major versions and apply now.
# Set attach_custom_pg_and_og = false for the upgrade apply so AWS uses default v17 groups.
# After the upgrade completes, set attach_custom_pg_and_og = true and apply again to attach custom v17 groups.
allow_major_version_upgrade = true
apply_immediately           = true
attach_custom_pg_and_og     = false
