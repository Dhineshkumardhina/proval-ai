# PropVal AI — Phase 5F Infrastructure as Code Report

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Infrastructure as Code (IaC) Blueprint, Cloud Topography & Kubernetes Manifests  
**IaC Tooling:** HashiCorp Terraform ($\ge 1.6.0$) & Kubernetes Core APIs ($1.28+$)  
**Security Standard:** CIS Amazon Web Services Benchmark v2.0 & CIS Kubernetes Benchmark v1.8  
**Date:** 2026-11-05  
**Auditor Roles:** Senior Cloud Architect & Infrastructure Security Specialist  

---

## 1. Executive Summary

This report documents the official Infrastructure as Code (IaC) blueprints developed for PropVal AI. All infrastructure definitions are version-controlled, auditable, and modularized into:
1. **Terraform Modules ([`infra/terraform/`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/terraform/)):** Managing cloud networking, IAM service accounts, AWS KMS customer-managed keys, managed RDS PostgreSQL 16 + PostGIS, and AWS Secrets Manager.
2. **Kubernetes Production Manifests ([`infra/k8s/`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/)):** Managing pod security standards, zero-trust network policies, rolling update deployments, deep health probes, and TLS ingress controllers.

---

## 2. Terraform Cloud Architecture Blueprint

The Terraform topology is defined in [`infra/terraform/main.tf`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/terraform/main.tf), [`variables.tf`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/terraform/variables.tf), and [`outputs.tf`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/terraform/outputs.tf).

### 2.1 KMS Customer Managed Key (CMK)
```hcl
resource "aws_kms_key" "propval_cmk" {
  description             = "PropVal AI Customer Managed Key for Database and Secret Encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}
```
- **Envelope Encryption:** Used to encrypt RDS EBS volumes, PostgreSQL automated backups, and AWS Secrets Manager secrets.
- **Key Rotation:** Automatic 365-day cryptographic key rotation enabled.

---

### 2.2 3-Tier Multi-AZ VPC Segmentation
- **CIDR:** `10.0.0.0/16` in region `ap-south-1` (Mumbai).
- **Public Subnets (`10.0.1.0/24`, `10.0.2.0/24`, `10.0.3.0/24`):** Hosts the Application Load Balancer (ALB) and NAT Gateway.
- **Private Compute Subnets (`10.0.10.0/24`, `10.0.20.0/24`, `10.0.30.0/24`):** Hosts EKS worker nodes and application pods; routes outbound traffic exclusively via the NAT Gateway.
- **Isolated Database Subnets (`10.0.50.0/24`, `10.0.60.0/24`, `10.0.70.0/24`):** Hosts managed RDS PostgreSQL; **contains zero route to the internet gateway and zero route to the NAT gateway.**

---

### 2.3 Managed RDS PostgreSQL 16 + PostGIS
```hcl
resource "aws_db_instance" "postgres" {
  identifier     = "propval-rds-${var.environment}"
  engine         = "postgres"
  engine_version = "16.2"
  instance_class = var.db_instance_class

  allocated_storage     = 100
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.propval_cmk.arn

  db_name  = "propval_db"
  username = "propval_admin"

  publicly_accessible   = false
  multi_az              = true
  backup_retention_period = 30
  deletion_protection   = true
}
```
- **PostGIS Extension Support:** High-performance spatial indexing (`GIST`) for geospatial comparables, BBMP/municipal ward boundaries, and cadastral parcel geometries.
- **High Availability:** Synchronous Multi-AZ standby replication across availability zones with automatic failover ($< 60\text{ seconds}$).
- **Continuous Backup:** 30-day continuous Point-in-Time Recovery (PITR).

---

## 3. Kubernetes Production Manifests Blueprint

All container workloads are governed by declarative Kubernetes manifests in [`infra/k8s/`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/):

### 3.1 Restricted Pod Security Standard
Declared in [`infra/k8s/namespace.yaml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/namespace.yaml):
- Labels namespace with `pod-security.kubernetes.io/enforce: restricted`.
- Enforces non-root execution, seccomp runtime default, and blocks host namespace sharing.

### 3.2 Zero-Trust Network Policy
Declared in [`infra/k8s/network-policy.yaml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/network-policy.yaml):
- **Ingress Isolation:** Frontend pods accept traffic strictly from the Nginx Ingress Controller on port 8080.
- **Backend Isolation:** Backend pods accept traffic strictly from frontend pods on port 8000; all direct external internet ingress is blocked.
- **Database Egress:** Backend pods can route egress strictly to the internal database subnet CIDRs on port 5432. All other internet egress is blocked except CoreDNS (port 53).

---

### 3.3 Backend Deployment & Rolling Update Strategy
Declared in [`infra/k8s/backend-deployment.yaml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/backend-deployment.yaml):
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```
- **Zero Downtime:** Guarantees that at least 3 healthy replicas remain available during new version rollouts.
- **Non-Root Execution:** `runAsUser: 10001`, `runAsGroup: 10001`, `allowPrivilegeEscalation: false`.
- **Resource Guarantees:** 500m CPU / 1Gi RAM request, 2000m CPU / 2Gi RAM limit.
- **Deep Health Probes:** Probes `/health/live` and `/health/ready` prevent unready pods from receiving incoming traffic.

---

### 3.4 Pre-Deploy Database Migration Job
Declared in [`infra/k8s/ingress.yaml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/ingress.yaml):
- Implements a Kubernetes `batch/v1 Job` executing `alembic upgrade head`.
- Runs as a pre-install / pre-upgrade Helm hook before any pod traffic is shifted to new application versions.

---

### 3.5 TLS Ingress & HTTP Security Headers
Declared in [`infra/k8s/ingress.yaml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/ingress.yaml):
- **Protocols:** Strict `TLSv1.2 TLSv1.3`.
- **HSTS:** `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`.
- **Defensive Headers:** `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 4. Secret Management & Injection Architecture

```
[AWS Secrets Manager (KMS CMK Encrypted)]
                     │
                     ▼
[External Secrets Operator / CSI Secret Store]
                     │
                     ▼
[Kubernetes Secret: propval-secrets (In-Memory)]
                     │
                     ▼
[Injected as Environment Variables into Pods at Runtime]
 - DATABASE_URL (postgresql://...)
 - JWT_SECRET (256-bit secure key)
 - GEMINI_API_KEY
```

- **Zero Plaintext Secrets:** No credentials, tokens, or connection strings are committed to Git.
- **In-Memory Storage:** Secrets are mounted via `tmpfs` volume or direct container environment bindings.
- **Rotation Ready:** Secrets Manager supports automatic secret rotation without modifying deployment YAMLs.

