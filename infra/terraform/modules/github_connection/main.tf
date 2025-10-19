# modules/github_connection/main.tf
# AWS App Runner GitHub Connection Module

# Note: The GitHub connection must be manually activated in the AWS Console
# after it's created, as it requires GitHub OAuth authentication.

resource "aws_apprunner_connection" "github" {
  connection_name = "${var.project_name}-${var.environment}-github"
  provider_type   = "GITHUB"

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-github-connection"
  })
}

# Output the connection ARN for use by App Runner services
output "connection_arn" {
  description = "ARN of the GitHub connection"
  value       = aws_apprunner_connection.github.arn
}

output "connection_status" {
  description = "Status of the GitHub connection"
  value       = aws_apprunner_connection.github.status
}
