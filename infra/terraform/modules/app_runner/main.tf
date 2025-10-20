# modules/app_runner/main.tf
# AWS App Runner service module

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  # Normalize CPU value to match provider expectations
  # Accepts either raw sizes (256/512/1024/2048/4096) or "0.25|0.5|1|2|4 vCPU"
  cpu_value = can(regex("^(0\\.25|0\\.5|1|2|4)$", var.cpu_units)) ? "${var.cpu_units} vCPU" : var.cpu_units
}

# === VPC Connector ===
resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "${local.name_prefix}-vpc-connector"
  subnets           = var.subnet_ids
  security_groups   = [var.app_runner_sg_id]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc-connector"
  })
}

# === Auto Scaling Configuration ===
resource "aws_apprunner_auto_scaling_configuration_version" "main" {
  auto_scaling_configuration_name = "${local.name_prefix}-autoscaling"

  min_size = var.min_size
  max_size = var.max_size

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-autoscaling"
  })
}

# === App Runner Service ===
resource "aws_apprunner_service" "main" {
  service_name = var.service_name

  # Source configuration
  source_configuration {
    # Authentication configuration for GitHub
    authentication_configuration {
      connection_arn = var.github_connection_arn
    }
    
    # GitHub repository configuration
    code_repository {
      repository_url = var.source_repository_url
      
      code_configuration {
        configuration_source = "REPOSITORY"  # Use apprunner.yaml from repository
        
        # Fallback configuration if no apprunner.yaml found
        code_configuration_values {
          runtime = var.runtime
          
          port            = var.port
          build_command   = var.build_command
          start_command   = var.start_command
          runtime_environment_variables = var.environment_variables
          
          runtime_environment_secrets = {
            for key, value in var.environment_secrets : key => value
          }
        }
      }
      
      source_code_version {
        type  = "BRANCH"
        value = var.branch_name
      }
    }
    
    # Auto deployments configuration
    auto_deployments_enabled = var.enable_auto_deployments
  }

  # Instance configuration
  instance_configuration {
    cpu               = local.cpu_value
    memory            = var.memory_units
    instance_role_arn = var.app_runner_instance_role_arn
  }

  # Auto scaling configuration
  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.main.arn

  # Network configuration
  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.main.arn
    }
    
    ingress_configuration {
      is_publicly_accessible = var.is_publicly_accessible
    }
  }

  # Health check configuration
  health_check_configuration {
    healthy_threshold   = var.health_check_healthy_threshold
    interval            = var.health_check_interval
    path                = var.health_check_path
    protocol            = var.health_check_protocol
    timeout             = var.health_check_timeout
    unhealthy_threshold = var.health_check_unhealthy_threshold
  }

  # Observability configuration
  observability_configuration {
    observability_enabled = var.enable_observability

    # Use provided observability configuration ARN, or the one we create when enabled
    observability_configuration_arn = var.observability_configuration_arn != null ? var.observability_configuration_arn : try(aws_apprunner_observability_configuration.main[0].arn, null)
  }

  tags = merge(var.tags, {
    Name = var.service_name
  })

  lifecycle {
    ignore_changes = [
      # Ignore changes to code_configuration_values to prevent errors on update
      # when configuration_source is REPOSITORY. Secrets and env vars are set
      # on creation and managed outside of Terraform updates thereafter.
      source_configuration[0].code_repository[0].code_configuration[0].code_configuration_values,
    ]
  }

  depends_on = [
    aws_apprunner_vpc_connector.main,
    aws_apprunner_auto_scaling_configuration_version.main
  ]
}

# === Custom Domain Association (Optional) ===
resource "aws_apprunner_custom_domain_association" "main" {
  count = var.custom_domain_name != null ? 1 : 0

  domain_name = var.custom_domain_name
  service_arn = aws_apprunner_service.main.arn

  enable_www_subdomain = var.enable_www_subdomain
  
  # Note: aws_apprunner_custom_domain_association does not support tags
}

# === Observability Configuration ===
resource "aws_apprunner_observability_configuration" "main" {
  count = var.enable_observability && var.observability_configuration_arn == null ? 1 : 0

  observability_configuration_name = "${local.name_prefix}-observability"

  # X-Ray tracing
  trace_configuration {
    vendor = "AWSXRAY"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-observability"
  })
}

# === CloudWatch Log Group ===
resource "aws_cloudwatch_log_group" "app_runner" {
  name              = "/aws/apprunner/${var.service_name}/application"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-app-logs"
  })
}

# === CloudWatch Log Group for System Logs ===
resource "aws_cloudwatch_log_group" "app_runner_system" {
  name              = "/aws/apprunner/${var.service_name}/system"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-system-logs"
  })
}

# === CloudWatch Alarms ===
resource "aws_cloudwatch_metric_alarm" "app_runner_cpu" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-app-runner-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Average"
  threshold           = var.cpu_alarm_threshold
  alarm_description   = "This metric monitors App Runner CPU utilization"
  alarm_actions       = var.alarm_actions

  dimensions = {
    ServiceName = aws_apprunner_service.main.service_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "app_runner_memory" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-app-runner-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Average"
  threshold           = var.memory_alarm_threshold
  alarm_description   = "This metric monitors App Runner memory utilization"
  alarm_actions       = var.alarm_actions

  dimensions = {
    ServiceName = aws_apprunner_service.main.service_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "app_runner_requests" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-app-runner-high-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "RequestCount"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.request_count_threshold
  alarm_description   = "This metric monitors App Runner request count"
  alarm_actions       = var.alarm_actions

  dimensions = {
    ServiceName = aws_apprunner_service.main.service_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "app_runner_4xx_errors" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-app-runner-high-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4xxStatusResponses"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.error_4xx_threshold
  alarm_description   = "This metric monitors App Runner 4xx errors"
  alarm_actions       = var.alarm_actions

  dimensions = {
    ServiceName = aws_apprunner_service.main.service_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "app_runner_5xx_errors" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-app-runner-high-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5xxStatusResponses"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.error_5xx_threshold
  alarm_description   = "This metric monitors App Runner 5xx errors"
  alarm_actions       = var.alarm_actions

  dimensions = {
    ServiceName = aws_apprunner_service.main.service_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "app_runner_response_time" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-app-runner-high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "ResponseTime"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Average"
  threshold           = var.response_time_threshold
  alarm_description   = "This metric monitors App Runner response time"
  alarm_actions       = var.alarm_actions

  dimensions = {
    ServiceName = aws_apprunner_service.main.service_name
  }

  tags = var.tags
}