# modules/networking_egress/outputs.tf
# Outputs from cost-optimized networking (S3 Gateway endpoint only)

output "s3_gateway_endpoint_id" {
  description = "ID of the S3 Gateway VPC endpoint"
  value       = aws_vpc_endpoint.s3_gateway.id
}

output "s3_gateway_endpoint_prefix_list_id" {
  description = "Prefix list ID of the S3 Gateway VPC endpoint"
  value       = aws_vpc_endpoint.s3_gateway.prefix_list_id
}

output "s3_gateway_endpoint_cidr_blocks" {
  description = "CIDR blocks for the S3 Gateway VPC endpoint"
  value       = aws_vpc_endpoint.s3_gateway.cidr_blocks
}

# Cost Optimization Summary
output "cost_optimization_summary" {
  description = "Cost-optimized networking configuration summary"
  value = {
    gateway_endpoints = ["S3"]
    interface_endpoints = []
    nat_gateways = 0
    monthly_cost = "S3 Gateway endpoint: FREE, NAT Gateway cost: $0 (using App Runner default public egress)"
    external_traffic = "All AWS services (SSM, Bedrock, etc.) and external APIs (OpenAI, Pinecone, Stripe) use App Runner's default public egress"
  }
}