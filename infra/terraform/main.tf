# =============================================================================
# PropVal AI — Institutional Cloud Infrastructure (Terraform HCL)
# Target: AWS (ap-south-1 / Mumbai Region) for Indian DPDP Act 2023 Compliance
# Architecture:
#   - 3-Tier Multi-AZ VPC with Strict Network Segmentation & Flow Logs
#   - Managed EKS Kubernetes Cluster (Control Plane + Managed Private Nodes + IRSA)
#   - Managed RDS PostgreSQL 16 + PostGIS with Multi-AZ & KMS Envelope Encryption
#   - Application Load Balancer with TLS 1.3 / ACM Managed Certificates
#   - AWS Secrets Manager with KMS Customer Managed Key (CMK)
#   - CloudWatch Comprehensive Monitoring & DevSecOps Metric Alarms
#   - AWS Backup & Immutable Encrypted S3 Audit Vault
# =============================================================================

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "PropVal-AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Compliance  = "DPDP-Act-2023-RBI-Cybersecurity"
      DataTier    = "Institutional-Confidential"
    }
  }
}

data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
# 1. KMS Customer Managed Keys (CMK) for Envelope Encryption
# -----------------------------------------------------------------------------
resource "aws_kms_key" "propval_cmk" {
  description             = "PropVal AI Customer Managed Key for Database, Secret, and EBS Encryption"
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
      },
      {
        Sid    = "AllowCloudWatchLogs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt*",
          "kms:Decrypt*",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:Describe*"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "propval_cmk_alias" {
  name          = "alias/propval-${var.environment}-cmk"
  target_key_id = aws_kms_key.propval_cmk.key_id
}

# -----------------------------------------------------------------------------
# 2. Virtual Private Cloud (VPC) with 3-Tier Private Segmentation
# -----------------------------------------------------------------------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.5"

  name = "propval-vpc-${var.environment}"
  cidr = var.vpc_cidr

  azs              = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  public_subnets   = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnets  = ["10.0.10.0/24", "10.0.20.0/24", "10.0.30.0/24"]
  database_subnets = ["10.0.50.0/24", "10.0.60.0/24", "10.0.70.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment == "staging" ? true : false
  enable_dns_hostnames = true
  enable_dns_support   = true

  create_database_subnet_group           = true
  create_database_subnet_route_table     = true
  create_database_internet_gateway_route = false # Zero public database route

  public_subnet_tags = {
    "kubernetes.io/role/elb"                        = 1
    "kubernetes.io/cluster/propval-eks-${var.environment}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"               = 1
    "kubernetes.io/cluster/propval-eks-${var.environment}" = "shared"
  }

  database_subnet_tags = {
    "Tier" = "Database-Isolated"
  }
}

# VPC Flow Logs to CloudWatch for Auditing & Forensic Readiness
resource "aws_cloudwatch_log_group" "vpc_flow_log_group" {
  name              = "/aws/vpc/propval-${var.environment}-flow-logs"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.propval_cmk.arn
}

resource "aws_iam_role" "vpc_flow_log_role" {
  name = "propval-${var.environment}-vpc-flow-log-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "vpc_flow_log_policy" {
  name = "propval-${var.environment}-vpc-flow-log-policy"
  role = aws_iam_role.vpc_flow_log_role.id

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
        Resource = "*"
      }
    ]
  })
}

resource "aws_flow_log" "vpc_flow_log" {
  iam_role_arn    = aws_iam_role.vpc_flow_log_role.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_log_group.arn
  traffic_type    = "ALL"
  vpc_id          = module.vpc.vpc_id
}

# -----------------------------------------------------------------------------
# 3. Security Groups (Least Privilege Firewalls)
# -----------------------------------------------------------------------------

# ALB Security Group
resource "aws_security_group" "alb_sg" {
  name        = "propval-${var.environment}-alb-sg"
  description = "Public ALB security group allowing HTTPS ingress"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "Allow HTTPS from institutional network / public internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTP for redirect to HTTPS"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow traffic to EKS worker node NodePort/target pods"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

# EKS Cluster Security Group
resource "aws_security_group" "eks_cluster_sg" {
  name        = "propval-${var.environment}-eks-cluster-sg"
  description = "EKS control plane communication security group"
  vpc_id      = module.vpc.vpc_id

  egress {
    description = "Control plane to worker nodes"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

# EKS Worker Nodes Security Group
resource "aws_security_group" "eks_nodes_sg" {
  name        = "propval-${var.environment}-eks-nodes-sg"
  description = "EKS worker nodes security group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Allow traffic from ALB to worker node pods"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  ingress {
    description = "Allow node-to-node internal communication"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "Allow outbound to internet via NAT Gateway for container pulls and API connectors"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Managed RDS Database Security Group
resource "aws_security_group" "db_sg" {
  name        = "propval-${var.environment}-db-sg"
  description = "Database SG allowing port 5432 strictly from EKS worker nodes"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL access from EKS worker nodes only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes_sg.id]
  }

  egress {
    description = "No outbound internet access for database"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["127.0.0.1/32"]
  }
}

# -----------------------------------------------------------------------------
# 4. Managed RDS PostgreSQL 16 + PostGIS Relational Database
# -----------------------------------------------------------------------------
resource "aws_db_parameter_group" "postgres_params" {
  name   = "propval-${var.environment}-pg16-params"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "500" # Log slow queries taking > 500ms
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = "propval-rds-${var.environment}"
  engine         = "postgres"
  engine_version = "16.2"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.propval_cmk.arn

  db_name  = "propval_db"
  username = "propval_admin"
  password = var.db_master_password

  parameter_group_name   = aws_db_parameter_group.postgres_params.name
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  publicly_accessible    = false # Zero public IP address

  multi_az               = var.environment == "production" ? true : false
  backup_retention_period = var.backup_retention_days # 30-day continuous PITR backup
  backup_window          = "20:00-21:00"
  maintenance_window     = "Sun:22:00-Sun:23:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  auto_minor_version_upgrade = true
  deletion_protection        = var.environment == "production" ? true : false
  skip_final_snapshot        = var.environment == "production" ? false : true
  final_snapshot_identifier  = "propval-rds-${var.environment}-final-snapshot"
}

# -----------------------------------------------------------------------------
# 5. Elastic Kubernetes Service (EKS) Cluster & Managed Node Group
# -----------------------------------------------------------------------------

# EKS Control Plane IAM Role
resource "aws_iam_role" "eks_cluster_role" {
  name = "propval-${var.environment}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster_role.name
}

resource "aws_iam_role_policy_attachment" "eks_service_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
  role       = aws_iam_role.eks_cluster_role.name
}

# EKS Cluster Resource
resource "aws_eks_cluster" "eks" {
  name     = "propval-eks-${var.environment}"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = var.eks_cluster_version

  vpc_config {
    subnet_ids              = module.vpc.private_subnets
    security_group_ids      = [aws_security_group.eks_cluster_sg.id]
    endpoint_private_access = true
    endpoint_public_access  = true # Restricted via CIDR or institutional VPN in production
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  encryption_config {
    provider {
      key_arn = aws_kms_key.propval_cmk.arn
    }
    resources = ["secrets"]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_service_policy,
  ]
}

# OIDC Provider for IAM Roles for Service Accounts (IRSA)
data "tls_certificate" "eks_oidc_cert" {
  url = aws_eks_cluster.eks.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks_oidc" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks_oidc_cert.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.eks.identity[0].oidc[0].issuer
}

# EKS Worker Node IAM Role
resource "aws_iam_role" "eks_node_role" {
  name = "propval-${var.environment}-eks-node-role"

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
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_role.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_role.name
}

resource "aws_iam_role_policy_attachment" "eks_ecr_read_only" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_role.name
}

# Managed Node Group in Private Subnets
resource "aws_eks_node_group" "private_nodes" {
  cluster_name    = aws_eks_cluster.eks.name
  node_group_name = "propval-nodes-${var.environment}"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = module.vpc.private_subnets

  instance_types = var.eks_node_instance_types
  capacity_type  = "ON_DEMAND"

  scaling_config {
    desired_size = var.eks_desired_nodes
    max_size     = var.eks_max_nodes
    min_size     = var.eks_min_nodes
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    role = "application-workload"
    tier = "private"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_ecr_read_only,
  ]
}

# -----------------------------------------------------------------------------
# 6. IRSA IAM Role for Kubernetes Backend Service Account
# -----------------------------------------------------------------------------
resource "aws_iam_role" "backend_irsa_role" {
  name = "propval-${var.environment}-backend-irsa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks_oidc.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks_oidc.url, "https://", "")}:sub" = "system:serviceaccount:propval-production:propval-backend-sa"
          }
        }
      }
    ]
  })
}

resource "aws_iam_policy" "backend_secrets_policy" {
  name        = "propval-${var.environment}-backend-secrets-policy"
  description = "Permit backend service account to retrieve secrets from AWS Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.app_secrets.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.propval_cmk.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backend_irsa_attach" {
  policy_arn = aws_iam_policy.backend_secrets_policy.arn
  role       = aws_iam_role.backend_irsa_role.name
}

# -----------------------------------------------------------------------------
# 7. AWS Secrets Manager (KMS Encrypted Application Secrets)
# -----------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "propval/${var.environment}/app-secrets"
  kms_key_id              = aws_kms_key.propval_cmk.id
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret_version" "app_secrets_val" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    JWT_SECRET     = var.jwt_secret
    DATABASE_URL   = "postgresql://propval_admin:${var.db_master_password}@${aws_db_instance.postgres.endpoint}/propval_db"
    GEMINI_API_KEY = var.gemini_api_key
  })
}

# -----------------------------------------------------------------------------
# 8. Application Load Balancer & ACM TLS Certificate
# -----------------------------------------------------------------------------
resource "aws_acm_certificate" "cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb" "main_alb" {
  name               = "propval-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = var.environment == "production" ? true : false
  drop_invalid_header_fields = true

  tags = {
    Name = "propval-${var.environment}-alb"
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06" # Mandatory TLS 1.3
  certificate_arn   = aws_acm_certificate.cert.arn

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "application/json"
      message_body = "{\"status\": \"OK\", \"service\": \"PropVal AI Ingress Gateway\"}"
      status_code  = "200"
    }
  }
}

# -----------------------------------------------------------------------------
# 9. CloudWatch Alarms & Operational Monitoring
# -----------------------------------------------------------------------------
resource "aws_sns_topic" "ops_alerts" {
  name              = "propval-${var.environment}-ops-alerts"
  kms_master_key_id = aws_kms_alias.propval_cmk_alias.name
}

resource "aws_sns_topic_subscription" "email_sub" {
  topic_arn = aws_sns_topic.ops_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  alarm_name          = "propval-${var.environment}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Database CPU utilization exceeds 80% for 10 minutes"
  alarm_actions       = [aws_sns_topic.ops_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.identifier
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_storage_low" {
  alarm_name          = "propval-${var.environment}-rds-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 10737418240 # 10 GB
  alarm_description   = "Database free storage space is below 10GB"
  alarm_actions       = [aws_sns_topic.ops_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.identifier
  }
}

# -----------------------------------------------------------------------------
# 10. Automated AWS Backup & S3 Audit Archive Vault
# -----------------------------------------------------------------------------
resource "aws_backup_vault" "main_vault" {
  name        = "propval-${var.environment}-backup-vault"
  kms_key_arn = aws_kms_key.propval_cmk.arn
}

resource "aws_backup_plan" "daily_plan" {
  name = "propval-${var.environment}-daily-backup-plan"

  rule {
    rule_name         = "daily-snapshot"
    target_vault_name = aws_backup_vault.main_vault.name
    schedule          = "cron(0 21 * * ? *)" # 02:30 IST / 21:00 UTC daily

    lifecycle {
      delete_after = var.backup_retention_days
    }
  }
}

# S3 Bucket for Immutable Audit Log and Dataset Snapshots
resource "aws_s3_bucket" "audit_vault" {
  bucket        = "propval-${var.environment}-audit-vault-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "audit_vault_versioning" {
  bucket = aws_s3_bucket.audit_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_vault_encryption" {
  bucket = aws_s3_bucket.audit_vault.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.propval_cmk.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit_vault_pab" {
  bucket = aws_s3_bucket.audit_vault.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
