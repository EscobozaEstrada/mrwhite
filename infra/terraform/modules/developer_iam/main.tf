# modules/developer_iam/main.tf
# IAM permissions for developer to manage their own EC2 instance

locals {
  policy_name = "${var.project_name}-${var.environment}-developer-ec2-access"
}

# IAM Policy for Developer EC2 Access
resource "aws_iam_policy" "developer_ec2_access" {
  name        = local.policy_name
  description = "Allows ${var.username} to manage their tagged EC2 development instance"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEC2ReadOnly"
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ec2:GetConsole*",
          "ec2:GetPasswordData",
          "ec2:GetSerialConsoleAccessStatus"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowInstanceManagementByTag"
        Effect = "Allow"
        Action = [
          "ec2:StartInstances",
          "ec2:StopInstances",
          "ec2:RebootInstances",
          "ec2:TerminateInstances",
          "ec2:ModifyInstanceAttribute",
          "ec2:CreateTags",
          "ec2:DeleteTags"
        ]
        Resource = "arn:aws:ec2:*:*:instance/*"
        Condition = {
          StringEquals = {
            "ec2:ResourceTag/Owner" = "developer"
          }
        }
      },
      {
        Sid    = "AllowSecurityGroupUpdateByTag"
        Effect = "Allow"
        Action = [
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:RevokeSecurityGroupIngress",
          "ec2:ModifySecurityGroupRules",
          "ec2:UpdateSecurityGroupRuleDescriptionsIngress"
        ]
        Resource = "arn:aws:ec2:*:*:security-group/*"
        Condition = {
          StringEquals = {
            "ec2:ResourceTag/Owner" = "developer"
          }
        }
      },
      {
        Sid    = "AllowKeyPairRead"
        Effect = "Allow"
        Action = [
          "ec2:DescribeKeyPairs"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name        = local.policy_name
    ManagedBy   = "Terraform"
    Purpose     = "Developer EC2 Access"
    Developer   = var.username
  })
}

# Attach Policy to Developer User
resource "aws_iam_group" "developer_group" {
  name = "${var.project_name}-${var.environment}-developers"
}

# Attach policy to the developer group to avoid per-user managed policy quotas
resource "aws_iam_group_policy_attachment" "developer_ec2_access" {
  group      = aws_iam_group.developer_group.name
  policy_arn = aws_iam_policy.developer_ec2_access.arn
}

# Ensure the developer group contains the specified user (without affecting user's other groups)
resource "aws_iam_group_membership" "developer_group_membership" {
  name  = "${var.project_name}-${var.environment}-developers-members"
  group = aws_iam_group.developer_group.name
  users = [var.username]
}
