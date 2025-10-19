# modules/developer_iam/outputs.tf
# Outputs from Developer IAM module

output "policy_arn" {
  description = "ARN of the developer EC2 access policy"
  value       = aws_iam_policy.developer_ec2_access.arn
}

output "policy_name" {
  description = "Name of the developer EC2 access policy"
  value       = aws_iam_policy.developer_ec2_access.name
}

output "username" {
  description = "IAM username that was granted permissions"
  value       = var.username
}
