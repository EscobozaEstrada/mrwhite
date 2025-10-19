# modules/secrets/outputs.tf
# Outputs from the secrets module

output "ssm_parameter_names" {
  description = "List of SSM parameter names"
  value       = concat(
    [for k, v in aws_ssm_parameter.secrets : v.name],
    [for k, v in aws_ssm_parameter.generated_secrets : v.name]
  )
}

output "ssm_parameter_paths" {
  description = "Map of secret keys to their SSM parameter paths"
  value = merge(
    { for k, v in aws_ssm_parameter.secrets : k => v.name },
    { for k, v in aws_ssm_parameter.generated_secrets : k => v.name }
  )
}

output "ssm_parameter_arns" {
  description = "List of SSM parameter ARNs for IAM policies"
  value = concat(
    [for k, v in aws_ssm_parameter.secrets : v.arn],
    [for k, v in aws_ssm_parameter.generated_secrets : v.arn]
  )
}

output "kms_key_id" {
  description = "ID of the KMS key used for secrets encryption"
  value       = var.create_kms_key ? aws_kms_key.secrets[0].key_id : null
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for secrets encryption"
  value       = var.create_kms_key ? aws_kms_key.secrets[0].arn : null
}

output "kms_key_alias" {
  description = "Alias of the KMS key used for secrets encryption"
  value       = var.create_kms_key ? aws_kms_alias.secrets[0].name : null
}

output "secrets_rotation_lambda_arn" {
  description = "ARN of the secrets rotation Lambda function"
  value       = var.enable_secrets_rotation ? aws_lambda_function.secrets_rotation[0].arn : null
}

output "secrets_rotation_schedule" {
  description = "Schedule for automatic secrets rotation"
  value       = var.enable_secrets_rotation ? var.secrets_rotation_schedule : null
}

output "parameter_store_prefix" {
  description = "Prefix used for SSM parameters"
  value       = var.secret_name_prefix
}