output "ssm_endpoint_id" {
  description = "SSM VPC endpoint ID"
  value       = aws_vpc_endpoint.ssm.id
}

output "secrets_manager_endpoint_id" {
  description = "Secrets Manager VPC endpoint ID"
  value       = aws_vpc_endpoint.secrets_manager.id
}

output "vpc_endpoints_security_group_id" {
  description = "Security group ID for VPC endpoints"
  value       = aws_security_group.vpc_endpoints.id
}
