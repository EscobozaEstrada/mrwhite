# modules/app_runner/outputs.tf
# Outputs from the App Runner module

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.main.arn
}

output "app_runner_service_id" {
  description = "ID of the App Runner service"
  value       = aws_apprunner_service.main.service_id
}

output "app_runner_service_url" {
  description = "URL of the App Runner service"
  value       = "https://${aws_apprunner_service.main.service_url}"
}

output "app_runner_service_domain" {
  description = "Domain name of the App Runner service"
  value       = aws_apprunner_service.main.service_url
}

output "app_runner_service_name" {
  description = "Name of the App Runner service"
  value       = aws_apprunner_service.main.service_name
}

# Custom Domain
output "custom_domain_association_id" {
  description = "ID of the custom domain association"
  value       = var.custom_domain_name != null ? aws_apprunner_custom_domain_association.main[0].id : null
}

output "custom_domain_certificate_validation_records" {
  description = "Certificate validation records for custom domain"
  value       = var.custom_domain_name != null ? aws_apprunner_custom_domain_association.main[0].certificate_validation_records : []
}

# VPC Connector
output "vpc_connector_arn" {
  description = "ARN of the VPC connector"
  value       = aws_apprunner_vpc_connector.main.arn
}

output "vpc_connector_name" {
  description = "Name of the VPC connector"
  value       = aws_apprunner_vpc_connector.main.vpc_connector_name
}

# Auto Scaling
output "auto_scaling_configuration_arn" {
  description = "ARN of the auto scaling configuration"
  value       = aws_apprunner_auto_scaling_configuration_version.main.arn
}

output "auto_scaling_configuration_name" {
  description = "Name of the auto scaling configuration"
  value       = aws_apprunner_auto_scaling_configuration_version.main.auto_scaling_configuration_name
}

# Observability
output "observability_configuration_arn" {
  description = "ARN of the observability configuration"
  value       = var.enable_observability && var.observability_configuration_arn == null ? aws_apprunner_observability_configuration.main[0].arn : var.observability_configuration_arn
}

# CloudWatch Log Groups
output "application_log_group_name" {
  description = "Name of the application log group"
  value       = aws_cloudwatch_log_group.app_runner.name
}

output "system_log_group_name" {
  description = "Name of the system log group"
  value       = aws_cloudwatch_log_group.app_runner_system.name
}

output "application_log_group_arn" {
  description = "ARN of the application log group"
  value       = aws_cloudwatch_log_group.app_runner.arn
}

# CloudWatch Alarms
output "cloudwatch_alarm_names" {
  description = "List of CloudWatch alarm names"
  value = var.enable_monitoring ? [
    aws_cloudwatch_metric_alarm.app_runner_cpu[0].alarm_name,
    aws_cloudwatch_metric_alarm.app_runner_memory[0].alarm_name,
    aws_cloudwatch_metric_alarm.app_runner_requests[0].alarm_name,
    aws_cloudwatch_metric_alarm.app_runner_4xx_errors[0].alarm_name,
    aws_cloudwatch_metric_alarm.app_runner_5xx_errors[0].alarm_name,
    aws_cloudwatch_metric_alarm.app_runner_response_time[0].alarm_name
  ] : []
}

# Service Configuration Summary
output "service_configuration" {
  description = "Summary of App Runner service configuration"
  value = {
    service_name    = aws_apprunner_service.main.service_name
    service_url     = "https://${aws_apprunner_service.main.service_url}"
    custom_domain   = var.custom_domain_name
    runtime         = var.runtime
    cpu_units       = var.cpu_units
    memory_units    = var.memory_units
    min_instances   = var.min_size
    max_instances   = var.max_size
    auto_deploy     = var.enable_auto_deployments
    observability   = var.enable_observability
    monitoring      = var.enable_monitoring
  }
}