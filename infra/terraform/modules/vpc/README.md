# VPC Module

This module creates a complete VPC infrastructure including:

## Resources Created

- **VPC** with configurable CIDR block
- **Public Subnets** across multiple Availability Zones
- **Private Subnets** across multiple Availability Zones
- **Internet Gateway** for public subnet internet access
- **NAT Gateways** for private subnet internet access (optional)
- **Route Tables** and associations
- **Security Groups** for different services:
  - App Runner security group
  - RDS security group
  - VPC Endpoints security group
  - Bastion Host security group (optional)
- **Bastion Host** for secure database access (optional)
- **VPN Gateway** (optional)

## Usage

```hcl
module "vpc" {
  source = "./modules/vpc"
  
  aws_region           = "us-east-1"
  project_name         = "myproject"
  environment          = "prod"
  organization         = "monetizespirit"
  
  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.101.0/24", "10.0.102.0/24"]
  azs                  = ["us-east-1a", "us-east-1b"]
  
  enable_nat_gateway   = true
  enable_bastion_host  = false
  
  tags = {
    Project = "MyProject"
    Environment = "Production"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| aws_region | AWS region | string | n/a | yes |
| project_name | Name of the project | string | n/a | yes |
| environment | Deployment environment | string | n/a | yes |
| organization | Organization name | string | n/a | yes |
| vpc_cidr | CIDR block for VPC | string | n/a | yes |
| public_subnet_cidrs | List of CIDR blocks for public subnets | list(string) | n/a | yes |
| private_subnet_cidrs | List of CIDR blocks for private subnets | list(string) | n/a | yes |
| azs | List of Availability Zones | list(string) | n/a | yes |
| enable_nat_gateway | Enable NAT Gateway | bool | true | no |
| enable_bastion_host | Enable bastion host | bool | false | no |

## Outputs

| Name | Description |
|------|-------------|
| vpc_id | ID of the VPC |
| public_subnet_ids | List of public subnet IDs |
| private_subnet_ids | List of private subnet IDs |
| app_runner_sg_id | Security Group ID for App Runner |
| rds_sg_id | Security Group ID for RDS |

## Security Considerations

- Private subnets have no direct internet access
- NAT Gateways provide controlled outbound internet access
- Security groups follow principle of least privilege
- Bastion host access is restricted to specified CIDR blocks

## Cost Optimization

- NAT Gateways can be disabled for development environments
- Bastion host is optional and uses minimal instance type
- VPC Endpoints can be used to reduce NAT Gateway costs