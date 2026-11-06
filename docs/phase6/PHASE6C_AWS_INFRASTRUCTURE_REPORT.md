# PropVal AI — Phase 6C: AWS Cloud Infrastructure Architecture Report

**Document Reference:** `DOC-PHASE6C-AWS-ARCH-001`  
**Phase:** 6C — AWS Cloud Infrastructure Deployment  
**Author:** Senior AWS Cloud Architect, Kubernetes Engineer, & DevSecOps Specialist  
**Target Cloud Region:** AWS `ap-south-1` (Mumbai, India) — Mandatory Data Sovereignty under DPDP Act 2023  
**Target Infrastructure Tier:** Production Multi-AZ High-Availability Banking Architecture  
**Deployment Authorization Status:** **`BLOCKED (CREDENTIALS_PENDING)`** — Ready for Execution upon Credential Handover  
**Date:** November 5, 2026  

---

## 1. Executive Summary & Cloud Readiness Posture

Under the institutional deployment framework for PropVal AI, the complete cloud infrastructure architecture has been designed, coded in Terraform HCL, and validated for the AWS Mumbai (`ap-south-1`) region.

### Infrastructure Readiness Summary
- **Architecture Standard:** 3-Tier Multi-AZ VPC, Elastic Kubernetes Service (EKS), Managed RDS PostgreSQL 16 + PostGIS, Application Load Balancer with TLS 1.3, AWS Secrets Manager, and KMS Customer Managed Keys.
- **Compliance Alignment:** Digital Personal Data Protection Act 2023 (DPDP), Reserve Bank of India (RBI) Cybersecurity Framework for Banks, and ISO 27001 Annex A.12/A.13.
- **Deployment Status:** **`BLOCKED (CREDENTIALS_PENDING)`**. In adherence to strict institutional governance (*"Do not pretend that a local deployment is a cloud deployment"*), the infrastructure manifests and Terraform modules have been validated locally via automated CI/CD security tooling, while live cloud tenant deployment remains gated until institutional AWS credentials and tenant provisioning are signed off.

```
                              AWS CLOUD ARCHITECTURE (ap-south-1)
                              
  Internet / Bank VPN
           │
           ▼
    [ Route 53 / DNS ]
           │
           ▼
    [ ACM TLS 1.3 Cert ]
           │
           ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │  VPC: 10.0.0.0/16 (3 Availability Zones: ap-south-1a, ap-south-1b, ap-south-1c)        │
  │                                                                                        │
  │   PUBLIC TIER (10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24)                                  │
  │   ├── Application Load Balancer (ALB) [Port 443 / TLS 1.3]                             │
  │   └── NAT Gateways (Multi-AZ)                                                          │
  │                                                                                        │
  │   PRIVATE APPLICATION TIER (10.0.10.0/24, 10.0.20.0/24, 10.0.30.0/24)                  │
  │   └── Managed EKS Cluster (v1.29)                                                      │
  │       ├── Control Plane (KMS Envelope Encrypted Secrets)                               │
  │       ├── Managed Node Group (m6i.xlarge, Multi-AZ Auto-Scaling 2–8 Nodes)             │
  │       ├── Pod Security: Restricted Profile (Non-Root, Read-Only FS, Drop ALL)          │
  │       └── IAM Roles for Service Accounts (IRSA via OIDC)                               │
  │                                                                                        │
  │   DATABASE ISOLATED TIER (10.0.50.0/24, 10.0.60.0/24, 10.0.70.0/24) [Zero Public Route]│
  │   └── Managed RDS PostgreSQL 16.2 + PostGIS                                            │
  │       ├── Multi-AZ Standby Replica with Auto-Failover                                  │
  │       ├── gp3 Storage (100GB – 1000GB Auto-Scaling, KMS Encrypted)                     │
  │       ├── SSL Forced (rds.force_ssl = 1), Port 5432 Ingress strictly from EKS Nodes    │
  │       └── 30-Day Automated Point-In-Time Continuous Backups                           │
  └────────────────────────────────────────────────────────────────────────────────────────┘
           │                                                │
           ▼                                                ▼
  [ AWS Secrets Manager ]                         [ AWS KMS CMK (Key Rotation) ]
  (App Secrets Encrypted)                         (Envelope Encryption for all Tiers)
           │                                                │
           ▼                                                ▼
  [ CloudWatch Logs & Alarms ]                    [ AWS Backup & S3 Audit Vault ]
  (VPC Flow Logs, RDS, EKS Audit)                 (Daily Backups + WORM-Ready Snapshots)
```

---

## 2. Component Architecture Specifications

### 2.1 Networking & Segmentation (VPC)
- **VPC CIDR:** `10.0.0.0/16` partitioned across 3 Availability Zones (`ap-south-1a`, `ap-south-1b`, `ap-south-1c`).
- **Subnet Layout:**
  - `Public Subnets` (`10.0.1.0/24`, `10.0.2.0/24`, `10.0.3.0/24`): Hosts public ALB and NAT Gateways.
  - `Private Subnets` (`10.0.10.0/24`, `10.0.20.0/24`, `10.0.30.0/24`): Hosts EKS worker nodes and internal services. Egress to internet is routed strictly via NAT Gateways.
  - `Database Subnets` (`10.0.50.0/24`, `10.0.60.0/24`, `10.0.70.0/24`): Hosts RDS PostgreSQL. Route table contains zero internet gateway or NAT gateway routes, preventing any outbound or inbound internet connectivity.
- **VPC Flow Logs:** 100% of IP traffic is captured and streamed to CloudWatch Log Group `/aws/vpc/propval-production-flow-logs` with 90-day retention for compliance audit trails.

### 2.2 Managed Relational Database (RDS PostgreSQL 16 + PostGIS)
- **Engine Version:** PostgreSQL 16.2 with PostGIS 3.4 spatial extensions for cadastral boundaries.
- **Instance Sizing:** `db.r6g.xlarge` (4 vCPU, 32 GiB RAM, AWS Graviton3 architecture).
- **Storage:** 100 GiB baseline `gp3` storage with 12,000 IOPS and 500 MB/s throughput, auto-scaling up to 1,000 GiB.
- **Envelope Encryption:** Storage volume encrypted with dedicated KMS Customer Managed Key (CMK) `alias/propval-production-cmk`.
- **High Availability:** Multi-AZ synchronous replication with automated failover in $< 60$ seconds.
- **SSL / TLS Enforcement:** Custom parameter group enforces `rds.force_ssl = 1`. Unencrypted connections on port 5432 are rejected at the TCP handshake.
- **Backup & Recovery:** 30-day continuous Point-In-Time Recovery (PITR) window with 5-minute RPO.

### 2.3 Elastic Kubernetes Service (EKS) Cluster
- **Kubernetes Version:** `1.29` (Extended support release).
- **Control Plane Security:**
  - Cluster API server endpoint is private-enabled with IAM authenticator.
  - KMS encryption provider enabled for Kubernetes secrets (`resources = ["secrets"]`).
  - Control plane audit logs (`api`, `audit`, `authenticator`, `controllerManager`, `scheduler`) enabled and shipped to CloudWatch.
- **Worker Node Infrastructure:**
  - Managed Node Group deployed strictly in private subnets across 3 AZs.
  - Instance types: `m6i.xlarge` / `m6a.xlarge` (4 vCPU, 16 GiB RAM).
  - Auto-scaling configuration: Min 2 nodes, Max 8 nodes, Desired 3 nodes.
  - Nodes run optimized Amazon Linux 2 / Bottlerocket with kernel security hardening.
- **IAM Roles for Service Accounts (IRSA):**
  - EKS OIDC identity provider configured.
  - Service account `propval-backend-sa` assumes IAM role `propval-production-backend-irsa-role` via `sts:AssumeRoleWithWebIdentity` to retrieve secrets without static AWS access keys.

### 2.4 Ingress, Load Balancing, & TLS Termination
- **Application Load Balancer (ALB):** Public-facing multi-AZ load balancer in public subnets.
- **TLS Configuration:**
  - SSL certificate provisioned via AWS Certificate Manager (ACM) with DNS validation.
  - Ingress listener enforces `ELBSecurityPolicy-TLS13-1-2-2021-06` (TLS 1.3 only; legacy TLS 1.0/1.1 disabled).
  - Port 80 HTTP listener automatically issues HTTP 301 Permanent Redirect to HTTPS port 443.
- **Header Hardening:** HSTS (`max-age=63072000; includeSubDomains; preload`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.

### 2.5 Secrets Management & Cryptographic Security
- **AWS Secrets Manager:** Secrets stored under `propval/production/app-secrets` encrypted with KMS CMK.
- **Stored Secrets:**
  - `DATABASE_URL`: Authenticated connection string with dynamic endpoint and password.
  - `JWT_SECRET`: 256-bit institutional signing key.
  - `GEMINI_API_KEY`: API credential for secondary valuation intelligence.
- **Key Rotation:** Automated annual key rotation enabled on KMS CMK.
- **Secret Delivery:** Injected into Kubernetes pods via the AWS Secrets Store CSI Driver, mounting secrets as ephemeral volumes and synchronizing them into Kubernetes Secret objects.

### 2.6 Monitoring, Alerting, & DevSecOps
- **CloudWatch Alarms:**
  - `RDS CPU High`: Triggers when database CPU exceeds 80% for 10 minutes.
  - `RDS FreeStorageSpace Low`: Triggers when database available storage drops below 10 GiB.
  - `EKS Node CPU / Memory High`: Triggers horizontal pod or cluster auto-scaler.
- **Alert Dispatch:** Routed to AWS SNS Topic `propval-production-ops-alerts` with email dispatch to the DevSecOps on-call distribution.

### 2.7 Backup & Disaster Recovery Architecture
- **AWS Backup Vault:** Multi-region automated backup vault `propval-production-backup-vault`.
- **Backup Schedule:** Daily snapshot at 21:00 UTC (02:30 IST) with 30-day retention.
- **Immutable Audit Archive (S3):**
  - Dedicated bucket `propval-production-audit-vault-<account-id>` for cryptographic Merkle root archives and valuation audit event export.
  - S3 Versioning enabled.
  - SSE-KMS default encryption.
  - S3 Public Access Block enabled across all 4 dimensions (block public ACLs, block public policies, ignore public ACLs, restrict public buckets).

---

## 3. Deployment Feasibility & Pre-Requisite Checklist

To execute the live cloud deployment once AWS credentials are provided:

| Requirement | Specification | Verification Status |
|:---|:---|:---:|
| **Target AWS Account** | Dedicated institutional AWS account (ap-south-1) | Awaiting Tenant Assignment |
| **IAM Deployment Role** | AdministratorAccess or scoped InfrastructureAutomationPolicy | Awaiting Credentials |
| **Domain & DNS Zone** | Route 53 Hosted Zone for SSL Certificate Validation | Awaiting Domain Delegation |
| **Terraform Tooling** | Terraform CLI $\ge 1.6.0$ | Configured in CI/CD pipeline |
| **Kubernetes Tooling**| kubectl $\ge 1.29.0$ | Verified locally (`v1.36.1`) |
| **Docker Registry** | Amazon ECR repositories (`propval-backend`, `propval-frontend`) | Target defined in manifests |

---

## 4. Current Status: Gated & Blocked

In accordance with Section 8 of the Phase 6C specification:
1. **Local Validation:** All Terraform modules and Kubernetes manifests have completed 100% successful local validation.
2. **Cloud Tenant Connection:** Because live AWS credentials and tenant provisioning have not yet been granted, the physical deployment to AWS is formally marked:
   $$\mathbf{STATUS:\; BLOCKED\; (CREDENTIALS\_PENDING)}$$
3. **Integrity Rule:** PropVal AI does not simulate or claim cloud deployment without live AWS infrastructure test evidence.

