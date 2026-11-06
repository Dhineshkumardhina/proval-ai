# =============================================================================
# PropVal AI — Terraform Variables Specification (Institutional Architecture)
# =============================================================================

variable "aws_region" {
  description = "AWS region for data sovereignty (Mandatory ap-south-1 Mumbai for DPDP Act 2023)"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment tier (staging, production)"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated PropVal AI VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "domain_name" {
  description = "Domain name for institutional AVM API and UI access"
  type        = string
  default     = "propval.institutional-pilot.bank.internal"
}

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------
variable "db_instance_class" {
  description = "Compute instance size for managed RDS PostgreSQL 16"
  type        = string
  default     = "db.r6g.xlarge"
}

variable "db_allocated_storage" {
  description = "Initial allocated storage in GB for PostgreSQL (gp3)"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Maximum auto-scaling storage limit in GB for PostgreSQL"
  type        = number
  default     = 1000
}

variable "db_master_password" {
  description = "Master password for PostgreSQL (injected dynamically via Secret Manager / CI)"
  type        = string
  sensitive   = true
}

variable "backup_retention_days" {
  description = "Continuous point-in-time recovery backup retention period in days"
  type        = number
  default     = 30
}

# -----------------------------------------------------------------------------
# EKS Kubernetes Cluster Configuration
# -----------------------------------------------------------------------------
variable "eks_cluster_version" {
  description = "Target Kubernetes minor version for EKS control plane"
  type        = string
  default     = "1.29"
}

variable "eks_node_instance_types" {
  description = "EC2 instance types for EKS managed node group"
  type        = list(string)
  default     = ["m6i.xlarge", "m6a.xlarge"]
}

variable "eks_min_nodes" {
  description = "Minimum worker node count for high-availability multi-AZ operation"
  type        = number
  default     = 2
}

variable "eks_max_nodes" {
  description = "Maximum worker node count for auto-scaling under peak inference load"
  type        = number
  default     = 8
}

variable "eks_desired_nodes" {
  description = "Desired baseline worker node count"
  type        = number
  default     = 3
}

# -----------------------------------------------------------------------------
# Application Secrets
# -----------------------------------------------------------------------------
variable "jwt_secret" {
  description = "256-bit cryptographically secure secret for institutional JWT signing"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "API key for Google Gemini model access (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "alert_email" {
  description = "DevSecOps on-call distribution email for CloudWatch alarm notifications"
  type        = string
  default     = "devsecops@propval.internal"
}

# -----------------------------------------------------------------------------
# Multi-Region Disaster Recovery Configuration (Phase 6G)
# -----------------------------------------------------------------------------
variable "dr_aws_region" {
  description = "Secondary AWS DR region strictly within India sovereign boundaries (ap-south-2 Hyderabad)"
  type        = string
  default     = "ap-south-2"
}

variable "enable_dr_replication" {
  description = "Enable cross-region continuous replication and backup copy to secondary region"
  type        = bool
  default     = true
}

variable "rpo_target_minutes" {
  description = "Target Recovery Point Objective in minutes (<= 15 minutes)"
  type        = number
  default     = 15
}

variable "rto_target_minutes" {
  description = "Target Recovery Time Objective in minutes (<= 60 minutes)"
  type        = number
  default     = 60
}
