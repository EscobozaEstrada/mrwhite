# modules/vpc/outputs.tf
# Outputs from the VPC module

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "List of private route table IDs"
  value       = aws_route_table.private[*].id
}

# NAT Gateway outputs removed - using App Runner default public egress instead

output "app_runner_sg_id" {
  description = "Security Group ID for App Runner service"
  value       = aws_security_group.app_runner.id
}

output "rds_sg_id" {
  description = "Security Group ID for RDS database"
  value       = aws_security_group.rds.id
}

output "vpc_endpoints_sg_id" {
  description = "Security Group ID for VPC endpoints"
  value       = aws_security_group.vpc_endpoints.id
}

output "bastion_sg_id" {
  description = "Security Group ID for bastion host"
  value       = var.enable_bastion_host ? aws_security_group.bastion[0].id : null
}

output "bastion_instance_id" {
  description = "Instance ID of bastion host"
  value       = var.enable_bastion_host ? aws_instance.bastion[0].id : null
}

output "bastion_public_ip" {
  description = "Public IP of bastion host"
  value       = var.enable_bastion_host ? aws_instance.bastion[0].public_ip : null
}

output "availability_zones" {
  description = "List of availability zones used"
  value       = var.azs
}