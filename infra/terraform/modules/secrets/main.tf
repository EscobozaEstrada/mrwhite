# modules/secrets/main.tf
# SSM Parameter Store module for secure secrets management

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# === SSM Parameters for Secrets ===
resource "aws_ssm_parameter" "secrets" {
  for_each = var.secrets_map

  name        = "${var.secret_name_prefix}${each.key}"
  description = "Secret parameter for ${each.key}"
  type        = "SecureString"
  value       = each.value
  
  # Use AWS managed KMS key for encryption
  key_id = "alias/aws/ssm"

  tags = merge(var.tags, {
    Name        = "${local.name_prefix}-${each.key}"
    SecretType  = each.key
    Environment = var.environment
  })

  # Ignore changes to value after initial creation to prevent drift
  # This is useful when secrets are rotated outside of Terraform
  lifecycle {
    ignore_changes = [value]
  }
}

# === Random Password Generation (Optional) ===
# Generate random passwords for secrets that don't have values provided
resource "random_password" "generated_secrets" {
  for_each = var.generate_random_secrets

  length  = each.value.length
  special = each.value.special
  upper   = each.value.upper
  lower   = each.value.lower
  numeric  = each.value.numeric

  # Ensure password meets complexity requirements
  min_upper   = each.value.min_upper
  min_lower   = each.value.min_lower
  min_numeric = each.value.min_numeric
  min_special = each.value.min_special
}

# Store generated passwords in SSM
resource "aws_ssm_parameter" "generated_secrets" {
  for_each = var.generate_random_secrets

  name        = "${var.secret_name_prefix}${each.key}"
  description = "Auto-generated secret parameter for ${each.key}"
  type        = "SecureString"
  value       = random_password.generated_secrets[each.key].result
  
  key_id = "alias/aws/ssm"

  tags = merge(var.tags, {
    Name        = "${local.name_prefix}-${each.key}"
    SecretType  = each.key
    Environment = var.environment
    Generated   = "true"
  })
}

# === KMS Key for Additional Encryption (Optional) ===
resource "aws_kms_key" "secrets" {
  count = var.create_kms_key ? 1 : 0

  description = "KMS key for ${var.project_name} ${var.environment} secrets"
  
  # Key rotation
  enable_key_rotation = true
  
  # Key policy
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow use of the key for SSM"
        Effect = "Allow"
        Principal = {
          Service = "ssm.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-secrets-kms-key"
  })
}

# KMS Key Alias
resource "aws_kms_alias" "secrets" {
  count = var.create_kms_key ? 1 : 0

  name          = "alias/${var.project_name}-${var.environment}-secrets"
  target_key_id = aws_kms_key.secrets[0].key_id
}

# === Data Sources ===
data "aws_caller_identity" "current" {}

# === Secrets Rotation (Optional) ===
# Lambda function for secrets rotation
resource "aws_lambda_function" "secrets_rotation" {
  count = var.enable_secrets_rotation ? 1 : 0

  filename         = "secrets_rotation.zip"
  function_name    = "${local.name_prefix}-secrets-rotation"
  role            = aws_iam_role.secrets_rotation[0].arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.secrets_rotation[0].output_base64sha256
  runtime         = "python3.9"
  timeout         = 60

  environment {
    variables = {
      SECRET_NAME_PREFIX = var.secret_name_prefix
      PROJECT_NAME       = var.project_name
      ENVIRONMENT        = var.environment
    }
  }

  tags = var.tags
}

# IAM role for secrets rotation Lambda
resource "aws_iam_role" "secrets_rotation" {
  count = var.enable_secrets_rotation ? 1 : 0

  name = "${local.name_prefix}-secrets-rotation-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM policy for secrets rotation
resource "aws_iam_role_policy" "secrets_rotation" {
  count = var.enable_secrets_rotation ? 1 : 0

  name = "${local.name_prefix}-secrets-rotation-policy"
  role = aws_iam_role.secrets_rotation[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter",
          "ssm:DeleteParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.secret_name_prefix}*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = var.create_kms_key ? [aws_kms_key.secrets[0].arn] : ["arn:aws:kms:*:*:alias/aws/ssm"]
      }
    ]
  })
}

# Lambda deployment package
data "archive_file" "secrets_rotation" {
  count = var.enable_secrets_rotation ? 1 : 0

  type        = "zip"
  output_path = "secrets_rotation.zip"
  
  source {
    content = templatefile("${path.module}/templates/secrets_rotation.py", {
      secret_name_prefix = var.secret_name_prefix
      project_name       = var.project_name
      environment        = var.environment
    })
    filename = "lambda_function.py"
  }
}

# EventBridge rule for scheduled rotation
resource "aws_cloudwatch_event_rule" "secrets_rotation" {
  count = var.enable_secrets_rotation ? 1 : 0

  name        = "${local.name_prefix}-secrets-rotation"
  description = "Trigger secrets rotation"
  
  # Rotate secrets monthly
  schedule_expression = var.secrets_rotation_schedule

  tags = var.tags
}

# EventBridge target
resource "aws_cloudwatch_event_target" "secrets_rotation" {
  count = var.enable_secrets_rotation ? 1 : 0

  rule      = aws_cloudwatch_event_rule.secrets_rotation[0].name
  target_id = "SecretsRotationTarget"
  arn       = aws_lambda_function.secrets_rotation[0].arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  count = var.enable_secrets_rotation ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.secrets_rotation[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.secrets_rotation[0].arn
}