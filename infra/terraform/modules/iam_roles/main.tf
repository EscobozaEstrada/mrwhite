# modules/iam_roles/main.tf
# IAM roles and policies module

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# === App Runner Instance Role ===
resource "aws_iam_role" "app_runner_instance" {
  name = "${local.name_prefix}-app-runner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# === App Runner Access Role ===
resource "aws_iam_role" "app_runner_access" {
  name = "${local.name_prefix}-app-runner-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# === S3 Access Policy ===
resource "aws_iam_policy" "s3_access" {
  name        = "${local.name_prefix}-s3-access-policy"
  description = "Policy for S3 bucket access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObjectVersion",
          "s3:PutObjectAcl",
          "s3:GetObjectAcl"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })

  tags = var.tags
}

# === SSM Parameter Access Policy ===
resource "aws_iam_policy" "ssm_access" {
  name        = "${local.name_prefix}-ssm-access-policy"
  description = "Policy for SSM Parameter Store access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [var.ssm_parameter_path_prefix]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = var.tags
}

# === CloudWatch Logs Policy ===
resource "aws_iam_policy" "cloudwatch_logs" {
  count = var.enable_cloudwatch_access ? 1 : 0

  name        = "${local.name_prefix}-cloudwatch-logs-policy"
  description = "Policy for CloudWatch Logs access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })

  tags = var.tags
}

# === SES Access Policy ===
resource "aws_iam_policy" "ses_access" {
  count = var.enable_ses_access ? 1 : 0

  name        = "${local.name_prefix}-ses-access-policy"
  description = "Policy for SES email sending"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail",
          "ses:SendTemplatedEmail",
          "ses:SendBulkTemplatedEmail"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

# === Bedrock Access Policy ===
resource "aws_iam_policy" "bedrock_access" {
  count = var.enable_bedrock_access ? 1 : 0

  name        = "${local.name_prefix}-bedrock-access-policy"
  description = "Policy for Amazon Bedrock access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

# === Secrets Manager Access Policy ===
resource "aws_iam_policy" "secrets_manager_access" {
  count = var.enable_secrets_manager_access ? 1 : 0

  name        = "${local.name_prefix}-secrets-manager-policy"
  description = "Policy for AWS Secrets Manager access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.project_name}/*",
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:rds-db-credentials/*"
        ]
      }
    ]
  })

  tags = var.tags
}

# === Lambda Invoke Policy ===
resource "aws_iam_policy" "lambda_invoke" {
  count = var.enable_lambda_invoke ? 1 : 0

  name        = "${local.name_prefix}-lambda-invoke-policy"
  description = "Policy for Lambda function invocation"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:*:function:${var.project_name}-*"
      }
    ]
  })

  tags = var.tags
}

# === DynamoDB Access Policy ===
resource "aws_iam_policy" "dynamodb_access" {
  count = var.enable_dynamodb_access ? 1 : 0

  name        = "${local.name_prefix}-dynamodb-access-policy"
  description = "Policy for DynamoDB access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:*:table/${var.project_name}-*"
      }
    ]
  })

  tags = var.tags
}

# === Custom Policy ===
resource "aws_iam_policy" "custom" {
  count = var.custom_policy_json != "" ? 1 : 0

  name        = "${local.name_prefix}-custom-policy"
  description = "Custom IAM policy"
  policy      = var.custom_policy_json

  tags = var.tags
}

# === Policy Attachments for App Runner Instance Role ===
resource "aws_iam_role_policy_attachment" "app_runner_instance_s3" {
  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.s3_access.arn
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_ssm" {
  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.ssm_access.arn
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_cloudwatch" {
  count = var.enable_cloudwatch_access ? 1 : 0

  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.cloudwatch_logs[0].arn
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_ses" {
  count = var.enable_ses_access ? 1 : 0

  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.ses_access[0].arn
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_bedrock" {
  count = var.enable_bedrock_access ? 1 : 0

  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.bedrock_access[0].arn
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_secrets_manager" {
  count = var.enable_secrets_manager_access ? 1 : 0

  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.secrets_manager_access[0].arn
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_lambda" {
  count = var.enable_lambda_invoke ? 1 : 0

  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.lambda_invoke[0].arn
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_dynamodb" {
  count = var.enable_dynamodb_access ? 1 : 0

  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.dynamodb_access[0].arn
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_custom" {
  count = var.custom_policy_json != "" ? 1 : 0

  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.custom[0].arn
}

# === Policy Attachments for App Runner Access Role ===
# ECR access for App Runner to pull images
resource "aws_iam_role_policy_attachment" "app_runner_access_ecr" {
  role       = aws_iam_role.app_runner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# === Additional AWS Managed Policies ===
resource "aws_iam_role_policy_attachment" "additional_policies" {
  for_each = toset(var.additional_managed_policy_arns)

  role       = aws_iam_role.app_runner_instance.name
  policy_arn = each.value
}