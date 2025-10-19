# modules/iam_roles/outputs.tf
# Outputs from the IAM roles module

output "app_runner_instance_role_arn" {
  description = "ARN of the App Runner instance role"
  value       = aws_iam_role.app_runner_instance.arn
}

output "app_runner_instance_role_name" {
  description = "Name of the App Runner instance role"
  value       = aws_iam_role.app_runner_instance.name
}

output "app_runner_access_role_arn" {
  description = "ARN of the App Runner access role"
  value       = aws_iam_role.app_runner_access.arn
}

output "app_runner_access_role_name" {
  description = "Name of the App Runner access role"
  value       = aws_iam_role.app_runner_access.name
}

# Policy ARNs
output "s3_access_policy_arn" {
  description = "ARN of the S3 access policy"
  value       = aws_iam_policy.s3_access.arn
}

output "ssm_access_policy_arn" {
  description = "ARN of the SSM access policy"
  value       = aws_iam_policy.ssm_access.arn
}

output "cloudwatch_logs_policy_arn" {
  description = "ARN of the CloudWatch Logs policy"
  value       = var.enable_cloudwatch_access ? aws_iam_policy.cloudwatch_logs[0].arn : null
}

output "ses_access_policy_arn" {
  description = "ARN of the SES access policy"
  value       = var.enable_ses_access ? aws_iam_policy.ses_access[0].arn : null
}

# SNS access policy removed for security (least privilege principle)

output "bedrock_access_policy_arn" {
  description = "ARN of the Bedrock access policy"
  value       = var.enable_bedrock_access ? aws_iam_policy.bedrock_access[0].arn : null
}

output "secrets_manager_policy_arn" {
  description = "ARN of the Secrets Manager access policy"
  value       = var.enable_secrets_manager_access ? aws_iam_policy.secrets_manager_access[0].arn : null
}

output "lambda_invoke_policy_arn" {
  description = "ARN of the Lambda invoke policy"
  value       = var.enable_lambda_invoke ? aws_iam_policy.lambda_invoke[0].arn : null
}

output "dynamodb_access_policy_arn" {
  description = "ARN of the DynamoDB access policy"
  value       = var.enable_dynamodb_access ? aws_iam_policy.dynamodb_access[0].arn : null
}

output "custom_policy_arn" {
  description = "ARN of the custom policy"
  value       = var.custom_policy_json != "" ? aws_iam_policy.custom[0].arn : null
}

# Role information for other modules
output "role_summary" {
  description = "Summary of IAM roles and their permissions"
  value = {
    instance_role = {
      arn  = aws_iam_role.app_runner_instance.arn
      name = aws_iam_role.app_runner_instance.name
      permissions = [
        "S3 Access",
        "SSM Parameter Store",
        var.enable_cloudwatch_access ? "CloudWatch Logs" : null,
        var.enable_ses_access ? "SES Email" : null,
        var.enable_sns_access ? "SNS" : null,
        var.enable_bedrock_access ? "Bedrock" : null,
        var.enable_secrets_manager_access ? "Secrets Manager" : null,
        var.enable_lambda_invoke ? "Lambda Invoke" : null,
        var.enable_dynamodb_access ? "DynamoDB" : null
      ]
    }
    access_role = {
      arn  = aws_iam_role.app_runner_access.arn
      name = aws_iam_role.app_runner_access.name
      permissions = ["ECR Access"]
    }
  }
}