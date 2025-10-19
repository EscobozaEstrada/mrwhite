# modules/s3_storage/main.tf
# S3 bucket module for application storage

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# === S3 Bucket ===
resource "aws_s3_bucket" "main" {
  bucket = var.bucket_name

  tags = merge(var.tags, {
    Name = var.bucket_name
  })

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = false  # Set to true for production
  }
}

# === S3 Bucket Versioning ===
resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

# === S3 Bucket Encryption ===
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  count = var.enable_encryption ? 1 : 0

  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = var.kms_key_id != null ? true : false
  }
}

# === S3 Bucket Public Access Block ===
resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  # Block all public access by default (secure by default)
  block_public_acls       = !var.enable_public_read_access
  block_public_policy     = !var.enable_public_read_access
  ignore_public_acls      = !var.enable_public_read_access
  restrict_public_buckets = !var.enable_public_read_access
}

# === S3 Bucket Policy ===
resource "aws_s3_bucket_policy" "main" {
  count = var.enable_public_read_access ? 1 : 0

  bucket = aws_s3_bucket.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.main.arn}/*"
        Condition = {
          StringEquals = {
            "s3:ExistingObjectTag/PublicRead" = "true"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.main]
}

# === S3 Bucket CORS Configuration ===
resource "aws_s3_bucket_cors_configuration" "main" {
  count = length(var.cors_allowed_origins) > 0 ? 1 : 0

  bucket = aws_s3_bucket.main.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = var.cors_allowed_origins
    # Wildcards are not supported in expose_headers; list explicit headers used by the app
    expose_headers  = [
      "ETag",
      "x-amz-meta-custom",
      "x-amz-request-id",
      "x-amz-id-2"
    ]
    max_age_seconds = 3000
  }
}

# === S3 Bucket Lifecycle Configuration ===
resource "aws_s3_bucket_lifecycle_configuration" "main" {
  count = var.enable_lifecycle_rules ? 1 : 0

  bucket = aws_s3_bucket.main.id

  # Transition to IA after 30 days
  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    filter {
      prefix = "documents/"
    }
  }

  # Transition to Glacier after 90 days
  rule {
    id     = "transition_to_glacier"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    filter {
      prefix = "documents/"
    }
  }

  # Delete old versions after 365 days
  rule {
    id     = "delete_old_versions"
    status = var.enable_versioning ? "Enabled" : "Disabled"

    noncurrent_version_expiration {
      noncurrent_days = 365
    }

    filter {}
  }

  # Delete incomplete multipart uploads after 1 day
  rule {
    id     = "delete_incomplete_uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }

    filter {}
  }

  # Auto-delete temporary files after 1 day
  rule {
    id     = "delete_temp_files"
    status = "Enabled"

    expiration {
      days = 1
    }

    filter {
      prefix = "temp/"
    }
  }

  depends_on = [aws_s3_bucket_versioning.main]
}

# === S3 Bucket Logging ===
resource "aws_s3_bucket" "logs" {
  count = var.enable_access_logging ? 1 : 0

  bucket = "${var.bucket_name}-logs"

  tags = merge(var.tags, {
    Name = "${var.bucket_name}-logs"
    Purpose = "AccessLogging"
  })
}

resource "aws_s3_bucket_public_access_block" "logs" {
  count = var.enable_access_logging ? 1 : 0

  bucket = aws_s3_bucket.logs[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  count = var.enable_access_logging ? 1 : 0

  bucket = aws_s3_bucket.logs[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  count = var.enable_access_logging ? 1 : 0

  bucket = aws_s3_bucket.logs[0].id

  rule {
    id     = "delete_logs"
    status = "Enabled"

    expiration {
      days = var.access_logs_retention_days
    }

    filter {}
  }
}

resource "aws_s3_bucket_logging" "main" {
  count = var.enable_access_logging ? 1 : 0

  bucket = aws_s3_bucket.main.id

  target_bucket = aws_s3_bucket.logs[0].id
  target_prefix = "access-logs/"
}

# === S3 Bucket Notification ===
resource "aws_s3_bucket_notification" "main" {
  count = var.enable_event_notifications ? 1 : 0

  bucket = aws_s3_bucket.main.id

  # SNS notification for object creation
  dynamic "topic" {
    for_each = var.notification_topics
    content {
      topic_arn     = topic.value.arn
      events        = topic.value.events
      filter_prefix = topic.value.prefix
      filter_suffix = topic.value.suffix
    }
  }

  # Lambda notification for object processing
  dynamic "lambda_function" {
    for_each = var.notification_lambdas
    content {
      lambda_function_arn = lambda_function.value.arn
      events             = lambda_function.value.events
      filter_prefix      = lambda_function.value.prefix
      filter_suffix      = lambda_function.value.suffix
    }
  }
}

# === CloudWatch Metrics ===
resource "aws_cloudwatch_metric_alarm" "bucket_size" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-s3-bucket-size"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 hours
  statistic           = "Average"
  threshold           = var.bucket_size_alarm_threshold
  alarm_description   = "This metric monitors S3 bucket size"
  treat_missing_data  = "notBreaching"

  dimensions = {
    BucketName  = aws_s3_bucket.main.id
    StorageType = "StandardStorage"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "object_count" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-s3-object-count"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "NumberOfObjects"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 hours
  statistic           = "Average"
  threshold           = var.object_count_alarm_threshold
  alarm_description   = "This metric monitors S3 object count"
  treat_missing_data  = "notBreaching"

  dimensions = {
    BucketName  = aws_s3_bucket.main.id
    StorageType = "AllStorageTypes"
  }

  tags = var.tags
}

# === S3 Bucket Intelligent Tiering ===
resource "aws_s3_bucket_intelligent_tiering_configuration" "main" {
  count = var.enable_intelligent_tiering ? 1 : 0

  bucket = aws_s3_bucket.main.id
  name   = "intelligent-tiering"

  filter {
    prefix = "documents/"
  }

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}