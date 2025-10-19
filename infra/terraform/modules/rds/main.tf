# modules/rds/main.tf
# RDS PostgreSQL database module

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# Discover the latest available minor version for the specified Postgres major
data "aws_rds_engine_version" "postgres" {
  engine                  = "postgres"
  parameter_group_family  = "postgres${var.postgres_version}"
  default_only            = true
}

# === RDS Subnet Group ===
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })
}

# === RDS Parameter Group ===
resource "aws_db_parameter_group" "main" {
  family = "postgres${var.postgres_version}"
  name   = "${local.name_prefix}-db-params-v${var.postgres_version}"

  # Performance and connection optimization parameters
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "log_statement"
    value        = var.environment == "prod" ? "none" : "all"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "log_min_duration_statement"
    value        = var.environment == "prod" ? "1000" : "100"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "max_connections"
    value        = var.max_connections
    apply_method = "pending-reboot"
  }

  # Connection pooling optimization
  parameter {
    name         = "shared_buffers"
    value        = "{DBInstanceClassMemory/32768}"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "effective_cache_size"
    value        = "{DBInstanceClassMemory/16384}"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "maintenance_work_mem"
    value        = "{DBInstanceClassMemory/65536}"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "checkpoint_completion_target"
    value        = "0.7"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "wal_buffers"
    value        = "{DBInstanceClassMemory/131072}"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "default_statistics_target"
    value        = "100"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "random_page_cost"
    value        = "1.1"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "effective_io_concurrency"
    value        = "200"
    apply_method = "pending-reboot"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-db-params-v${var.postgres_version}"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# === RDS Option Group ===
resource "aws_db_option_group" "main" {
  name                     = "${local.name_prefix}-db-options-v${var.postgres_version}"
  option_group_description = "Option group for ${local.name_prefix} PostgreSQL"
  engine_name              = "postgres"
  major_engine_version     = var.postgres_version

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-db-options-v${var.postgres_version}"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# === RDS Instance ===
resource "aws_db_instance" "main" {
  # Basic configuration
  identifier = "${local.name_prefix}-db"
  
  # Engine configuration
  engine         = "postgres"
  engine_version = data.aws_rds_engine_version.postgres.version
  instance_class = var.db_instance_class
  
  # Storage configuration
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = var.storage_type
  storage_encrypted     = true
  kms_key_id           = var.kms_key_id
  
  # Database configuration
  db_name  = var.db_name
  username = var.db_username
  password = null  # Always use AWS-managed password for security
  port     = var.db_port
  
  # Use AWS managed master user password (stored in AWS Secrets Manager)
  manage_master_user_password = true
  
  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_sg_id]
  publicly_accessible    = false
  
  # Parameter and option groups - can be temporarily detached during major version upgrades
  parameter_group_name = var.attach_custom_pg_and_og ? aws_db_parameter_group.main.name : null
  option_group_name    = var.attach_custom_pg_and_og ? aws_db_option_group.main.name : null
  
  # Backup configuration
  backup_retention_period = var.backup_retention_period
  backup_window          = var.backup_window
  maintenance_window     = var.maintenance_window
  copy_tags_to_snapshot  = true
  
  # Deletion protection
  deletion_protection = var.deletion_protection
  skip_final_snapshot = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.name_prefix}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  # Monitoring
  monitoring_interval = var.enable_monitoring ? 60 : 0
  monitoring_role_arn = var.enable_monitoring ? aws_iam_role.rds_monitoring[0].arn : null
  
  performance_insights_enabled = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? var.performance_insights_retention : null
  
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports
  
  # Auto minor version upgrade
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  allow_major_version_upgrade = var.allow_major_version_upgrade
  apply_immediately           = var.apply_immediately
  
  # Multi-AZ deployment - disabled for cost optimization
  # Can be enabled by setting var.multi_az = true if high availability is required
  multi_az = var.multi_az
  
  tags = merge(var.tags, {
    Name = "${local.name_prefix}-database"
  })

  lifecycle {
    prevent_destroy = false  # Set to true for production
    ignore_changes = [
      password,  # Ignore password changes to prevent drift when using SSM
      final_snapshot_identifier,
    ]
  }

  depends_on = [
    aws_db_subnet_group.main,
    aws_db_parameter_group.main,
    aws_db_option_group.main
  ]
}

# === RDS Monitoring Role ===
resource "aws_iam_role" "rds_monitoring" {
  count = var.enable_monitoring ? 1 : 0

  name = "${local.name_prefix}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count = var.enable_monitoring ? 1 : 0

  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# === Read Replica (Optional) ===
resource "aws_db_instance" "read_replica" {
  count = var.create_read_replica ? 1 : 0

  identifier = "${local.name_prefix}-db-read-replica"
  
  # Read replica configuration
  replicate_source_db = aws_db_instance.main.identifier
  instance_class      = var.read_replica_instance_class
  
  # Network configuration
  publicly_accessible = false
  
  # Monitoring
  monitoring_interval = var.enable_monitoring ? 60 : 0
  monitoring_role_arn = var.enable_monitoring ? aws_iam_role.rds_monitoring[0].arn : null
  
  performance_insights_enabled = var.enable_performance_insights
  
  # Auto minor version upgrade
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  
  tags = merge(var.tags, {
    Name = "${local.name_prefix}-database-read-replica"
    Role = "ReadReplica"
  })

  depends_on = [aws_db_instance.main]
}

# === CloudWatch Alarms ===
resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-rds-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "120"
  statistic           = "Average"
  threshold           = var.max_connections * 0.8  # 80% of max connections
  alarm_description   = "This metric monitors RDS connection count"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "database_free_storage" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-rds-low-free-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "2000000000"  # 2GB in bytes
  alarm_description   = "This metric monitors RDS free storage space"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = var.tags
}