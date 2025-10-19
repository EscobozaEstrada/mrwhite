# modules/rds/outputs.tf
# Outputs from the RDS module

output "rds_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.main.id
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "rds_db_username" {
  description = "Database username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "rds_hosted_zone_id" {
  description = "RDS instance hosted zone ID"
  value       = aws_db_instance.main.hosted_zone_id
}

output "rds_resource_id" {
  description = "RDS resource ID"
  value       = aws_db_instance.main.resource_id
}

output "rds_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.main.arn
}

output "rds_ca_cert_identifier" {
  description = "RDS instance CA certificate identifier"
  value       = aws_db_instance.main.ca_cert_identifier
}

# AWS Secrets Manager - Master User Secret ARN
output "rds_master_user_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing the master user password"
  value       = aws_db_instance.main.master_user_secret != null ? aws_db_instance.main.master_user_secret[0].secret_arn : null
}

output "rds_master_user_secret_kms_key_id" {
  description = "KMS key ID used to encrypt the AWS Secrets Manager secret"
  value       = aws_db_instance.main.master_user_secret != null ? aws_db_instance.main.master_user_secret[0].kms_key_id : null
}

# Read Replica Outputs
output "read_replica_endpoint" {
  description = "Read replica endpoint"
  value       = var.create_read_replica ? aws_db_instance.read_replica[0].endpoint : null
}

output "read_replica_id" {
  description = "Read replica instance ID"
  value       = var.create_read_replica ? aws_db_instance.read_replica[0].id : null
}

# Subnet Group
output "db_subnet_group_name" {
  description = "Database subnet group name"
  value       = aws_db_subnet_group.main.name
}

output "db_subnet_group_arn" {
  description = "Database subnet group ARN"
  value       = aws_db_subnet_group.main.arn
}

# Parameter Group
output "db_parameter_group_name" {
  description = "Database parameter group name"
  value       = aws_db_parameter_group.main.name
}

output "db_parameter_group_arn" {
  description = "Database parameter group ARN"
  value       = aws_db_parameter_group.main.arn
}

# Option Group
output "db_option_group_name" {
  description = "Database option group name"
  value       = aws_db_option_group.main.name
}

output "db_option_group_arn" {
  description = "Database option group ARN"
  value       = aws_db_option_group.main.arn
}

# Connection Information
output "connection_string" {
  description = "Database connection string template"
  value       = "postgresql://${aws_db_instance.main.username}:PASSWORD@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

# Monitoring
output "monitoring_role_arn" {
  description = "RDS monitoring role ARN"
  value       = var.enable_monitoring ? aws_iam_role.rds_monitoring[0].arn : null
}

# CloudWatch Alarms
output "cloudwatch_alarm_names" {
  description = "List of CloudWatch alarm names"
  value = var.enable_monitoring ? [
    aws_cloudwatch_metric_alarm.database_cpu[0].alarm_name,
    aws_cloudwatch_metric_alarm.database_connections[0].alarm_name,
    aws_cloudwatch_metric_alarm.database_free_storage[0].alarm_name
  ] : []
}