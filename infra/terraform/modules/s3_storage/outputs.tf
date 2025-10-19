# modules/s3_storage/outputs.tf
# Outputs from the S3 storage module

output "s3_bucket_id" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.main.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.main.arn
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.main.bucket_domain_name
}

output "s3_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  value       = aws_s3_bucket.main.bucket_regional_domain_name
}

output "s3_bucket_hosted_zone_id" {
  description = "Hosted zone ID for the S3 bucket's region"
  value       = aws_s3_bucket.main.hosted_zone_id
}

output "s3_bucket_region" {
  description = "AWS region of the S3 bucket"
  value       = aws_s3_bucket.main.region
}

# Logs bucket (if enabled)
output "s3_logs_bucket_id" {
  description = "Name of the S3 logs bucket"
  value       = var.enable_access_logging ? aws_s3_bucket.logs[0].id : null
}

output "s3_logs_bucket_arn" {
  description = "ARN of the S3 logs bucket"
  value       = var.enable_access_logging ? aws_s3_bucket.logs[0].arn : null
}

# Configuration information
output "versioning_enabled" {
  description = "Whether versioning is enabled"
  value       = var.enable_versioning
}

output "encryption_enabled" {
  description = "Whether encryption is enabled"
  value       = var.enable_encryption
}

output "public_read_enabled" {
  description = "Whether public read access is enabled"
  value       = var.enable_public_read_access
}

# CloudWatch alarms
output "bucket_size_alarm_name" {
  description = "Name of the bucket size CloudWatch alarm"
  value       = var.enable_monitoring ? aws_cloudwatch_metric_alarm.bucket_size[0].alarm_name : null
}

output "object_count_alarm_name" {
  description = "Name of the object count CloudWatch alarm"
  value       = var.enable_monitoring ? aws_cloudwatch_metric_alarm.object_count[0].alarm_name : null
}

# URLs for different access patterns
output "s3_website_endpoint" {
  description = "Website endpoint (if static website hosting enabled)"
  value       = "http://${aws_s3_bucket.main.bucket_domain_name}"
}

output "s3_https_endpoint" {
  description = "HTTPS endpoint for API access"
  value       = "https://${aws_s3_bucket.main.bucket_regional_domain_name}"
}