# =============================================================================
# PropVal AI — Multi-Region Disaster Recovery Architecture (Phase 6G)
# Primary Region:   ap-south-1 (Mumbai, India)
# Secondary Region: ap-south-2 (Hyderabad, India)
# Compliance:       DPDP Act 2023 (100% Domestic Sovereign Boundaries)
# Recovery Goals:   RPO <= 15 minutes, RTO <= 60 minutes
# =============================================================================

provider "aws" {
  alias  = "dr_region"
  region = var.dr_aws_region

  default_tags {
    tags = {
      Project     = "PropVal-AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Tier        = "DisasterRecovery-Secondary"
      Compliance  = "DPDP-Act-2023-RBI-Cybersecurity"
    }
  }
}

# -----------------------------------------------------------------------------
# 1. Secondary KMS Customer Managed Key (CMK) in ap-south-2
# -----------------------------------------------------------------------------
resource "aws_kms_key" "dr_cmk" {
  provider                = aws.dr_region
  description             = "PropVal AI Disaster Recovery KMS Key (Hyderabad ap-south-2)"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "dr_cmk_alias" {
  provider      = aws.dr_region
  name          = "alias/propval-${var.environment}-dr-cmk"
  target_key_id = aws_kms_key.dr_cmk.key_id
}

# -----------------------------------------------------------------------------
# 2. Secondary AWS Backup Vault in ap-south-2
# -----------------------------------------------------------------------------
resource "aws_backup_vault" "dr_vault" {
  provider    = aws.dr_region
  name        = "propval-${var.environment}-dr-vault-hyd"
  kms_key_arn = aws_kms_key.dr_cmk.arn
}

# -----------------------------------------------------------------------------
# 3. Secondary S3 Storage Bucket for Document & Model Backups (ap-south-2)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "dr_storage_vault" {
  provider      = aws.dr_region
  bucket        = "propval-${var.environment}-dr-vault-hyd-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "dr_storage_versioning" {
  provider = aws.dr_region
  bucket   = aws_s3_bucket.dr_storage_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dr_storage_encryption" {
  provider = aws.dr_region
  bucket   = aws_s3_bucket.dr_storage_vault.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.dr_cmk.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "dr_storage_public_block" {
  provider = aws.dr_region
  bucket   = aws_s3_bucket.dr_storage_vault.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# 4. Route 53 Active-Passive Multi-Region DNS Failover
# -----------------------------------------------------------------------------
resource "aws_route53_health_check" "primary_api_health" {
  fqdn              = "api.${var.domain_name}"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health/ready"
  failure_threshold = 3
  request_interval  = 10

  tags = {
    Name = "propval-primary-mumbai-health-check"
  }
}

# -----------------------------------------------------------------------------
# 5. CloudWatch DR Notification & Recovery Alarm Topic
# -----------------------------------------------------------------------------
resource "aws_sns_topic" "dr_notifications" {
  provider = aws.dr_region
  name     = "propval-${var.environment}-dr-alerts-hyd"
}

resource "aws_cloudwatch_metric_alarm" "primary_region_unhealthy" {
  alarm_name          = "propval-${var.environment}-primary-mumbai-down"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  alarm_description   = "Triggered when Primary Mumbai Region health checks fail continuously for 120 seconds."
  alarm_actions       = [aws_sns_topic.dr_notifications.arn]

  dimensions = {
    HealthCheckId = aws_route53_health_check.primary_api_health.id
  }
}

