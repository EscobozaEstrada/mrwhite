# modules/amplify_hosting/main.tf
# AWS Amplify Hosting module for frontend applications

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# === Amplify App ===
resource "aws_amplify_app" "main" {
  name       = var.app_name
  repository = var.repository_url
  platform   = var.platform
  iam_service_role_arn = var.create_service_role ? aws_iam_role.amplify_service[0].arn : null

  # Environment variables for build
  environment_variables = merge(
    var.build_environment_variables,
    {
      # Monorepo configuration - only build when frontend/ changes
      AMPLIFY_DIFF_DEPLOY           = "true"  # Enable differential deploys
      AMPLIFY_MONOREPO_APP_ROOT     = var.app_root_path  # Root path for this app
      AMPLIFY_DIFF_DEPLOY_ROOT      = var.app_root_path  # Only watch this directory
      _CUSTOM_IMAGE                 = "amplify:al2023"    # Use Amazon Linux 2023 image
    }
  )

  # Access token for GitHub (if using GitHub)
  access_token = var.github_access_token

  # OAuth token (alternative to access token)
  oauth_token = var.oauth_token

  # Basic auth credentials (if enabled)
  enable_basic_auth = var.enable_basic_auth
  
  # Custom rules for redirects and rewrites
  dynamic "custom_rule" {
    for_each = var.custom_rules
    content {
      source    = custom_rule.value.source
      target    = custom_rule.value.target
      status    = custom_rule.value.status
      condition = custom_rule.value.condition
    }
  }

  # Auto branch creation patterns
  enable_auto_branch_creation = var.enable_auto_branch_creation
  auto_branch_creation_patterns = var.auto_branch_creation_patterns
  
  dynamic "auto_branch_creation_config" {
    for_each = var.enable_auto_branch_creation ? [1] : []
    content {
      enable_auto_build     = var.auto_branch_enable_auto_build
      environment_variables = var.build_environment_variables
      framework             = var.framework
      stage                 = "DEVELOPMENT"
    }
  }

  tags = merge(var.tags, {
    Name = var.app_name
  })
}

# === Branch ===
resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.main.id
  branch_name = var.branch_name
  stage       = var.branch_stage

  # Framework detection
  framework = var.framework
  
  # Enable auto build
  enable_auto_build = var.enable_auto_build

  # Environment variables for this branch
  environment_variables = var.branch_environment_variables

  # Basic auth for branch (if enabled)
  enable_basic_auth = var.enable_branch_basic_auth

  # Performance mode
  enable_performance_mode = var.enable_performance_mode

  # Pull request preview
  enable_pull_request_preview = var.enable_pull_request_preview

  tags = var.tags
}

# === Custom Domain (Optional) ===
resource "aws_amplify_domain_association" "main" {
  count = var.custom_domain_name != null ? 1 : 0

  app_id      = aws_amplify_app.main.id
  domain_name = var.custom_domain_name

  # Certificate settings
  enable_auto_sub_domain = var.enable_auto_sub_domain

  # Subdomains
  sub_domain {
    branch_name = aws_amplify_branch.main.branch_name
    prefix      = var.subdomain_name
  }

  # WWW subdomain (optional)
  dynamic "sub_domain" {
    for_each = var.enable_www_subdomain ? [1] : []
    content {
      branch_name = aws_amplify_branch.main.branch_name
      prefix      = "www"
    }
  }

  # Wait for certificate if using ACM
  depends_on = [
    aws_amplify_branch.main
  ]
  
  # Note: aws_amplify_domain_association does not support tags
}

# === Webhook (Optional) ===
resource "aws_amplify_webhook" "main" {
  count = var.enable_webhook ? 1 : 0

  app_id      = aws_amplify_app.main.id
  branch_name = aws_amplify_branch.main.branch_name
  description = "Webhook for ${var.app_name} ${var.branch_name}"
  
  # Note: aws_amplify_webhook does not support tags
}

# === Backend Environment (Optional) ===
resource "aws_amplify_backend_environment" "main" {
  count = var.enable_backend_environment ? 1 : 0

  app_id           = aws_amplify_app.main.id
  environment_name = var.backend_environment_name

  deployment_artifacts = var.deployment_artifacts
  stack_name          = var.cloudformation_stack_name
  
  # Note: aws_amplify_backend_environment does not support tags
}

# === CloudWatch Log Groups ===
resource "aws_cloudwatch_log_group" "amplify_builds" {
  name              = "/aws/amplify/${aws_amplify_app.main.name}/builds"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name        = "${local.name_prefix}-amplify-builds"
    LogType     = "AmplifyBuilds"
  })
}

# === CloudWatch Alarms for Monitoring ===
resource "aws_cloudwatch_metric_alarm" "build_failures" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-amplify-build-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BuildFailures"
  namespace           = "AWS/Amplify"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors Amplify build failures"
  treat_missing_data  = "notBreaching"

  dimensions = {
    App = aws_amplify_app.main.name
  }

  tags = var.tags
}

# === IAM Role for Amplify Service (if needed) ===
resource "aws_iam_role" "amplify_service" {
  count = var.create_service_role ? 1 : 0

  name = "${local.name_prefix}-amplify-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "amplify.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "amplify_service" {
  count = var.create_service_role ? 1 : 0

  role       = aws_iam_role.amplify_service[0].name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess-Amplify"
}