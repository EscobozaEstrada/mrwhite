# modules/amplify_hosting/outputs.tf
# Outputs from the Amplify Hosting module

output "amplify_app_id" {
  description = "ID of the Amplify app"
  value       = aws_amplify_app.main.id
}

output "amplify_app_arn" {
  description = "ARN of the Amplify app"
  value       = aws_amplify_app.main.arn
}

output "amplify_app_name" {
  description = "Name of the Amplify app"
  value       = aws_amplify_app.main.name
}

output "amplify_default_domain" {
  description = "Default domain of the Amplify app"
  value       = aws_amplify_app.main.default_domain
}

output "amplify_app_url" {
  description = "URL of the Amplify app"
  value       = "https://${aws_amplify_branch.main.branch_name}.${aws_amplify_app.main.default_domain}"
}

# Branch Information
output "amplify_branch_name" {
  description = "Name of the deployed branch"
  value       = aws_amplify_branch.main.branch_name
}

output "amplify_branch_arn" {
  description = "ARN of the deployed branch"
  value       = aws_amplify_branch.main.arn
}

output "amplify_branch_url" {
  description = "URL of the deployed branch"
  value       = "https://${aws_amplify_branch.main.branch_name}.${aws_amplify_app.main.default_domain}"
}

# Custom Domain (if configured)
output "amplify_domain_association_arn" {
  description = "ARN of the domain association"
  value       = var.custom_domain_name != null ? aws_amplify_domain_association.main[0].arn : null
}

output "amplify_domain_association_cname_records" {
  description = "CNAME records for domain verification (subdomain dns_record values)"
  value       = var.custom_domain_name != null ? [
    for subdomain in aws_amplify_domain_association.main[0].sub_domain : {
      branch_name = subdomain.branch_name
      prefix      = subdomain.prefix
      dns_record  = subdomain.dns_record
      verified    = subdomain.verified
    }
  ] : []
}

output "custom_domain_url" {
  description = "Custom domain URL (if configured)"
  value       = var.custom_domain_name != null ? "https://${var.subdomain_name != "" ? "${var.subdomain_name}." : ""}${var.custom_domain_name}" : null
}

# Webhook (if enabled)
output "amplify_webhook_id" {
  description = "ID of the Amplify webhook"
  value       = var.enable_webhook ? aws_amplify_webhook.main[0].id : null
}

output "amplify_webhook_url" {
  description = "URL of the Amplify webhook"
  value       = var.enable_webhook ? aws_amplify_webhook.main[0].url : null
}

# Backend Environment (if enabled)
output "amplify_backend_environment_arn" {
  description = "ARN of the backend environment"
  value       = var.enable_backend_environment ? aws_amplify_backend_environment.main[0].arn : null
}

# Service Role (if created)
output "amplify_service_role_arn" {
  description = "ARN of the Amplify service role"
  value       = var.create_service_role ? aws_iam_role.amplify_service[0].arn : null
}

# CloudWatch Log Group
output "build_log_group_name" {
  description = "Name of the build log group"
  value       = aws_cloudwatch_log_group.amplify_builds.name
}

output "build_log_group_arn" {
  description = "ARN of the build log group"
  value       = aws_cloudwatch_log_group.amplify_builds.arn
}

# Monitoring
output "build_failure_alarm_name" {
  description = "Name of the build failure alarm"
  value       = var.enable_monitoring ? aws_cloudwatch_metric_alarm.build_failures[0].alarm_name : null
}

# Configuration Summary
output "deployment_configuration" {
  description = "Summary of deployment configuration"
  value = {
    app_name            = aws_amplify_app.main.name
    branch_name         = aws_amplify_branch.main.branch_name
    branch_stage        = aws_amplify_branch.main.stage
    framework           = var.framework
    auto_build_enabled  = var.enable_auto_build
    custom_domain       = var.custom_domain_name
    basic_auth_enabled  = var.enable_basic_auth
    performance_mode    = var.enable_performance_mode
    pr_previews_enabled = var.enable_pull_request_preview
    webhook_enabled     = var.enable_webhook
    monitoring_enabled  = var.enable_monitoring
  }
}

# DNS Configuration Helper
output "dns_configuration_instructions" {
  description = "Instructions for DNS configuration with subdomain details"
  value = var.custom_domain_name != null ? {
    message = "Configure your DNS provider with the following information:"
    domain  = var.custom_domain_name
    subdomains = [
      for subdomain in aws_amplify_domain_association.main[0].sub_domain : {
        prefix      = subdomain.prefix
        branch_name = subdomain.branch_name
        dns_record  = subdomain.dns_record
        verified    = subdomain.verified
      }
    ]
    note = "The dns_record field contains the CNAME value provided by AWS Amplify for domain verification."
  } : null
}