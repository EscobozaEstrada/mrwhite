# modules/dev_ec2/main.tf
# Developer EC2 workstation with auto-stop and pre-loaded secrets

locals {
  name_prefix = "${var.project_name}-${var.environment}-dev"
}

# Find the latest Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical's official AWS account ID

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# Security Group for Developer Instance
resource "aws_security_group" "dev_instance" {
  name_prefix = "${local.name_prefix}-sg-"
  description = "Security group for ${var.project_name} developer EC2 instance"
  vpc_id      = var.vpc_id

  # SSH access from developer's IP only
  ingress {
    description = "SSH from developer IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.dev_ip_address]
  }

  # Allow all outbound traffic
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name  = "${local.name_prefix}-security-group"
    Owner = "developer"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# IAM Role for EC2 Instance
resource "aws_iam_role" "dev_instance" {
  name_prefix = "${local.name_prefix}-role-"
  description = "IAM role for developer EC2 instance with full application access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-role"
  })
}

# IAM Policy for comprehensive application access
resource "aws_iam_policy" "dev_instance" {
  name_prefix = "${local.name_prefix}-policy-"
  description = "Policy granting developer EC2 full access to application resources"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # SSM Parameter Store access
      {
        Sid    = "SSMParameterAccess"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath",
          "ssm:PutParameter",
          "ssm:DeleteParameter",
          "ssm:DescribeParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter${var.ssm_parameter_path}*"
      },
      # KMS for SSM decryption
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
          }
        }
      },
      # RDS access
      {
        Sid    = "RDSAccess"
        Effect = "Allow"
        Action = [
          "rds:Describe*",
          "rds:ListTagsForResource",
          "rds-db:connect"
        ]
        Resource = "*"
      },
      # Secrets Manager (for RDS passwords)
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
          "secretsmanager:ListSecrets"
        ]
        Resource = "*"
      },
      # S3 access
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-*",
          "arn:aws:s3:::${var.project_name}-*/*"
        ]
      },
      # App Runner access
      {
        Sid    = "AppRunnerAccess"
        Effect = "Allow"
        Action = [
          "apprunner:Describe*",
          "apprunner:List*",
          "apprunner:StartDeployment",
          "apprunner:PauseService",
          "apprunner:ResumeService"
        ]
        Resource = "*"
      },
      # Amplify access
      {
        Sid    = "AmplifyAccess"
        Effect = "Allow"
        Action = [
          "amplify:Get*",
          "amplify:List*",
          "amplify:StartJob",
          "amplify:StopJob"
        ]
        Resource = "*"
      },
      # CloudWatch Logs
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/${var.project_name}/*"
      },
      # EC2 describe (for troubleshooting)
      {
        Sid    = "EC2DescribeAccess"
        Effect = "Allow"
        Action = [
          "ec2:Describe*"
        ]
        Resource = "*"
      },
      # SES access (for email testing)
      {
        Sid    = "SESAccess"
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail",
          "ses:GetSendQuota"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-policy"
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "dev_instance" {
  role       = aws_iam_role.dev_instance.name
  policy_arn = aws_iam_policy.dev_instance.arn
}

# Instance profile
resource "aws_iam_instance_profile" "dev_instance" {
  name_prefix = "${local.name_prefix}-profile-"
  role        = aws_iam_role.dev_instance.name

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-instance-profile"
  })
}

# Render user data script
data "template_file" "user_data" {
  template = file("${path.module}/user_data.sh.tpl")

  vars = {
    aws_region         = var.aws_region
    ssm_parameter_path = var.ssm_parameter_path
    project_name       = var.project_name
    organization       = var.organization
    environment        = var.environment
  }
}

# Developer EC2 Instance
resource "aws_instance" "dev_workstation" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name              = var.key_name
  subnet_id             = var.public_subnet_id
  vpc_security_group_ids = [aws_security_group.dev_instance.id]
  iam_instance_profile  = aws_iam_instance_profile.dev_instance.name
  user_data             = data.template_file.user_data.rendered

  # Root volume configuration
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true

    tags = merge(var.tags, {
      Name  = "${local.name_prefix}-root-volume"
      Owner = "developer"
    })
  }

  # Enable detailed monitoring for auto-stop alarm
  monitoring = true

  tags = merge(var.tags, {
    Name        = "${local.name_prefix}-workstation"
    Owner       = "developer"
    Purpose     = "Development"
    AutoStop    = "enabled"
    Environment = var.environment
  })

  lifecycle {
    ignore_changes = [
      ami, # Prevent recreation if newer AMI becomes available
      user_data # Prevent recreation if user data changes after initial creation
    ]
  }
}

# CloudWatch Alarm for Auto-Stop
resource "aws_cloudwatch_metric_alarm" "auto_stop" {
  alarm_name          = "${local.name_prefix}-auto-stop"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = var.auto_stop_evaluation_periods
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 600 # 10 minutes
  statistic           = "Maximum"
  threshold           = var.auto_stop_cpu_threshold
  alarm_description   = "Stop ${local.name_prefix} instance after ${var.auto_stop_evaluation_periods * 10} minutes of low CPU usage"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = aws_instance.dev_workstation.id
  }

  # Native AWS action to stop the instance (no Lambda needed!)
  alarm_actions = ["arn:aws:automate:${var.aws_region}:ec2:stop"]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-auto-stop-alarm"
  })
}
