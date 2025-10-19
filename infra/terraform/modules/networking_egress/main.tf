# modules/networking_egress/main.tf
# Cost-optimized networking: Only S3 Gateway Endpoint
# App Runner handles all other external traffic via default public egress

# === S3 Gateway VPC Endpoint (Only Required Endpoint) ===
resource "aws_vpc_endpoint" "s3_gateway" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.private_route_table_ids

  # Policy allows full S3 access from the VPC (can be restricted to specific buckets if needed)
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action    = "s3:*",     # S3 specific actions only
        Effect    = "Allow",
        Resource  = "*",        # Can be scoped to specific bucket ARN later
        Principal = "*",
      },
    ],
  })

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-s3-gateway-endpoint"
    Project     = var.project_name
    Environment = var.environment
  })
}

# IMPORTANT: No other VPC endpoints are created here
# All other AWS services (SSM, Bedrock, SES, etc.) and external services 
# (OpenAI, Pinecone, Stripe, FCM) are accessed via App Runner's default 
# public egress when no NAT Gateway is present in private subnets