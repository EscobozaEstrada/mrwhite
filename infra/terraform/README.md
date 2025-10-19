# Infrastructure as Code for Mr. White Project

This Terraform configuration provides a complete, production-ready infrastructure for the Mr. White AI-powered pet health management application. The infrastructure is designed to be reusable across similar projects with minimal changes.

## Architecture Overview

The infrastructure uses a **cost-optimized networking architecture** with the following components:

- **VPC with Public/Private Subnets** - Secure network isolation (No NAT Gateway)
- **AWS App Runner** - Scalable backend service hosting with default public egress
- **AWS Amplify** - Frontend hosting with CI/CD
- **RDS PostgreSQL** - Managed database with AWS-managed passwords
- **S3 Storage** - Document and file storage with Gateway VPC Endpoint
- **SSM Parameter Store** - Secure secrets management
- **CloudWatch** - Monitoring and alerting
- **IAM Roles** - Least-privilege access control

## Cost-Optimized Networking Strategy

This infrastructure implements a **cost-first approach** that saves ~$100+/month:

### ✅ Zero NAT Gateways
- **No NAT Gateway costs** (~$45/month per AZ saved)
- App Runner uses **default public egress** for external traffic
- Private subnets have no internet route - only VPC-local traffic

### ✅ Single S3 Gateway VPC Endpoint
- **FREE** S3 access from private subnets
- No expensive Interface VPC Endpoints (~$7.20/endpoint/month saved)
- All other AWS services accessed via App Runner's public egress

### ✅ Traffic Flow
```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   App Runner    │───▶│ Private RDS  │    │  S3 (Gateway)   │
│  (VPC Connector)│    │   (5432)     │    │   Endpoint      │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │
         ▼ (Default Public Egress)
┌─────────────────────────────────────────────────────────────┐
│  External APIs: OpenAI, Pinecone, Stripe, SSM, SES, etc.   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.0 installed
3. **Domain name** (optional, but recommended for production)

### Initial Setup

1. **Create S3 bucket for Terraform state:**
   ```bash
   aws s3 mb s3://monetizespirit-terraform-state-bucket --region us-east-1
   aws s3api put-bucket-versioning --bucket monetizespirit-terraform-state-bucket --versioning-configuration Status=Enabled
   aws s3api put-bucket-encryption --bucket monetizespirit-terraform-state-bucket --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
   ```

2. **Create DynamoDB table for state locking:**
   ```bash
   aws dynamodb create-table \
     --table-name monetizespirit-terraform-state-lock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-1
   ```

3. **Update backend configuration in `backend.tf`:**
   ```hcl
   terraform {
     backend "s3" {
       bucket         = "monetizespirit-terraform-state-bucket"
       key            = "mrwhite/terraform.tfstate"
       region         = "us-east-1"
       encrypt        = true
       dynamodb_table = "monetizespirit-terraform-state-lock"
     }
   }
   ```

### Deployment

1. **Clone and navigate to terraform directory:**
   ```bash
   cd infra/terraform
   ```

2. **Create your configuration file:**
   ```bash
   cp dev.tfvars.example dev.tfvars
   # Edit dev.tfvars with your specific values
   ```

3. **Upload secrets to SSM Parameter Store:**
   ```bash
   cd ../../backend/tools
   python upload_secrets_to_ssm.py --env prod
   # This uploads all secrets from .env file to SSM
   # Includes multiline secrets and Firebase service account JSON
   ```

4. **Initialize and deploy:**
   ```bash
   terraform init
   terraform plan -var-file=dev.tfvars
   terraform apply -var-file=dev.tfvars
   ```

## Configuration for Different Projects

This Terraform code is designed to be reusable. To adapt it for another project:

### 1. Update Project-Specific Variables

In your `.tfvars` file, update:

```hcl
project_name   = "your-new-project"
organization   = "monetizespirit"
custom_domain_name = "your-domain.com"
backend_repository_url  = "https://github.com/monetizespirit/your-backend.git"
frontend_repository_url = "https://github.com/monetizespirit/your-frontend.git"
```

### 2. Update Backend State Configuration

In `backend.tf`, update the bucket name and key:

```hcl
terraform {
  backend "s3" {
    bucket = "monetizespirit-new-project-terraform-state"
    key    = "your-new-project/terraform.tfstate"
    # ... rest of configuration
  }
}
```

### 3. Customize Module Parameters

The infrastructure is cost-optimized by default. You can adjust:

```hcl
# Cost optimization is built-in - no expensive NAT Gateway or Interface VPC Endpoints
enable_bastion_host = false
enable_monitoring = true

# Adjust compute resources
app_runner_cpu = "0.25"
app_runner_memory = "512"
db_instance_class = "db.t3.micro"
```

### 4. Add Project-Specific Resources

You can extend the infrastructure by adding resources to `main.tf` or creating additional modules.

## Module Structure

```
modules/
├── vpc/                 # VPC, subnets, security groups (No NAT Gateway)
├── rds/                 # PostgreSQL with AWS-managed passwords
├── s3_storage/          # S3 buckets with lifecycle policies
├── app_runner/          # Backend service hosting with VPC connector
├── amplify_hosting/     # Frontend hosting and CI/CD
├── iam_roles/           # IAM roles and policies
├── secrets/             # SSM Parameter Store management
└── networking_egress/   # S3 Gateway VPC Endpoint (cost-optimized)
```

Each module is self-contained with:
- `main.tf` - Resource definitions
- `variables.tf` - Input parameters
- `outputs.tf` - Output values
- `README.md` - Module documentation

## Security Best Practices

### Secrets Management
- **Database passwords:** AWS RDS managed passwords (never in Terraform state)
- **API keys:** Stored in SSM Parameter Store with encryption
- **IAM roles:** Follow least-privilege principle
- **No secrets in Terraform state:** Complete security isolation

### Network Security
- **Private subnets:** Database isolation from internet
- **Security groups:** App Runner can only access RDS (port 5432)
- **No NAT Gateway:** Eliminates potential attack vector
- **VPC isolation:** RDS completely private, accessed only via App Runner

### Data Protection
- RDS encryption at rest and in transit
- S3 bucket encryption and versioning
- Regular automated backups

## Cost Optimization

This infrastructure is designed for **maximum cost efficiency**:

### ✅ **~$100+/month Savings Achieved**
- **$0 NAT Gateway costs** (was ~$45/month per AZ)
- **$0 Interface VPC Endpoint costs** (was ~$7.20/endpoint/month)
- **FREE S3 Gateway Endpoint** for private S3 access
- **App Runner default public egress** handles all external traffic

### Development vs Production
**Development:**
- Smaller instance sizes: `db.t3.micro`, App Runner `0.25 vCPU`
- Single AZ deployment
- Reduced backup retention (1 day)
- **Cost: ~$30-50/month**

**Production:**
- Larger instances: `db.t3.small`, App Runner `0.5+ vCPU` 
- Multi-AZ RDS deployment
- Extended backup retention (7+ days)
- **Cost: ~$100-200/month** (still $100+ savings from networking optimization)

## Monitoring and Alerting

The infrastructure includes comprehensive monitoring:

- **CloudWatch Alarms** for CPU, memory, disk, and error rates
- **Log aggregation** for application and system logs
- **Performance insights** for database monitoring
- **Custom metrics** for application-specific monitoring

## Maintenance and Updates

### Terraform State Management
- State is stored in S3 with versioning
- DynamoDB provides state locking
- Remote state enables team collaboration

### Infrastructure Updates
- Use `terraform plan` to preview changes
- Apply changes during maintenance windows
- Keep Terraform and provider versions updated

### Disaster Recovery
- Regular RDS snapshots
- Cross-region S3 replication (if needed)
- Infrastructure as Code enables quick recovery

## Support and Troubleshooting

### Common Issues

1. **State bucket access errors**: Ensure AWS credentials have S3 permissions
2. **Domain validation failures**: Check DNS configuration for certificate validation
3. **App Runner deployment failures**: Verify repository access and build configuration
4. **Database connection issues**: Check security group rules and network ACLs

### Getting Help

- Review CloudWatch logs for application issues
- Use `terraform show` to inspect current state
- Check AWS Service Health Dashboard for service issues
- Review module README files for specific configuration options

## Network Architecture Decisions

### Why This Cost-Optimized Approach?

**Traditional Approach (Expensive):**
```
App Runner → NAT Gateway (~$45/mo) → Internet APIs
App Runner → Interface VPC Endpoints (~$7.20/mo each) → AWS APIs  
```

**Our Optimized Approach (Cost-Free):**
```
App Runner → Default Public Egress (FREE) → All External APIs
App Runner → S3 Gateway Endpoint (FREE) → S3 Storage
App Runner → Private Subnets → RDS Database
```

### Traffic Flow Details

1. **Database Access:** App Runner VPC Connector → Private Subnets → RDS (5432) ✅
2. **S3 Storage:** Private Subnets → S3 Gateway VPC Endpoint → S3 (FREE) ✅  
3. **External APIs:** App Runner → Default Public Egress → Internet ✅
   - OpenAI API calls
   - Pinecone vector database
   - Stripe payment processing
   - AWS SSM Parameter Store
   - AWS Secrets Manager
   - Amazon SES email service
   - Firebase/FCM notifications
   - External SMS services

### Security Considerations

- **RDS:** Completely isolated in private subnets, no internet access
- **App Runner:** Managed AWS service with built-in DDoS protection
- **No NAT Gateway:** Eliminates a potential network attack vector
- **Security Groups:** Restrictive rules (App Runner can only reach RDS)

## License

This infrastructure code is provided as-is for the Mr. White project and can be adapted for similar applications following the same architectural patterns.