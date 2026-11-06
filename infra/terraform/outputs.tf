# =============================================================================
# PropVal AI — Terraform Outputs Specification (Institutional Architecture)
# =============================================================================

output "vpc_id" {
  description = "Identifier of the dedicated PropVal AI VPC"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "Private subnets hosting EKS compute nodes"
  value       = module.vpc.private_subnets
}

output "database_subnets" {
  description = "Isolated database subnets with zero internet ingress/egress"
  value       = module.vpc.database_subnets
}

output "rds_endpoint" {
  description = "Private RDS PostgreSQL endpoint accessible strictly within VPC"
  value       = aws_db_instance.postgres.endpoint
}

output "kms_key_arn" {
  description = "ARN of the Customer Managed Key used for envelope encryption"
  value       = aws_kms_key.propval_cmk.arn
}

output "secrets_manager_secret_arn" {
  description = "ARN of the encrypted AWS Secrets Manager secret"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "eks_cluster_name" {
  description = "Name of the managed Elastic Kubernetes Service (EKS) cluster"
  value       = aws_eks_cluster.eks.name
}

output "eks_cluster_endpoint" {
  description = "Kubernetes API server control plane endpoint"
  value       = aws_eks_cluster.eks.endpoint
}

output "eks_oidc_provider_arn" {
  description = "IAM OIDC Provider ARN for IAM Roles for Service Accounts (IRSA)"
  value       = aws_iam_openid_connect_provider.eks_oidc.arn
}

output "backend_irsa_role_arn" {
  description = "IAM Role ARN for the propval-backend-sa Kubernetes Service Account"
  value       = aws_iam_role.backend_irsa_role.arn
}

output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer"
  value       = aws_lb.main_alb.dns_name
}

output "audit_vault_bucket" {
  description = "Immutable KMS-encrypted S3 bucket for audit logs and Merkle dataset snapshots"
  value       = aws_s3_bucket.audit_vault.bucket
}

output "backup_vault_arn" {
  description = "AWS Backup Vault ARN for automated multi-AZ disaster recovery"
  value       = aws_backup_vault.main_vault.arn
}
