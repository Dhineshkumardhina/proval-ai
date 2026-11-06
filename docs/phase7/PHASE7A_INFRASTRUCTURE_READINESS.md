# PropVal AI — Phase 7A: Infrastructure Readiness Assessment
**Cloud Infrastructure Architecture, Security Baseline, & Staging Plan**
**Document Reference:** `docs/phase7/PHASE7A_INFRASTRUCTURE_READINESS.md`  
**Execution Date:** November 6, 2026  
**Auditor / Role:** Senior AWS Cloud Architect, Kubernetes Security Specialist, and DevSecOps Engineer  

---

## 1. Executive Summary

This assessment audits the cloud infrastructure blueprints, container specifications, Kubernetes manifests, and disaster recovery architectures developed in Phase 6C and Phase 6G.

### Key Finding:
* **Infrastructure Manifest Code:** **100% COMPLETE & VALIDATED** (`infra/validate_infra.py` passed).
* **Local Development & WSL Environment:** **FULLY OPERATIONAL** (PostgreSQL 18.6 with Native RLS, Docker Compose, Python 3.14, Node 22).
* **Live AWS Cloud Deployment:** **BLOCKED (`AWS_CREDENTIALS_PENDING`)**
  - No AWS resources have been provisioned in a live cloud account.
  - Terraform state is uninitialized on remote S3/DynamoDB backends.
  - Live deployment is scheduled for Phase 7C once authorized cloud tenant credentials are provided.

---

## 2. Infrastructure Inventory & Manifest Audit

The PropVal AI infrastructure codebase consists of **13 modular configuration files** located under `infra/`:

```
infra/
├── k8s/                               # 9 Kubernetes Manifests
│   ├── configmap.yaml                 # Application configuration & OTel settings
│   ├── deployment.yaml                # FastAPI deployment (non-root, read-only rootfs)
│   ├── hpa.yaml                       # Horizontal Pod Autoscaler (min 2, max 10)
│   ├── ingress.yaml                   # AWS ALB Ingress with TLS & SSL redirect
│   ├── namespace.yaml                 # Dedicated 'propval' namespace with PSA restricted
│   ├── networkpolicy.yaml             # Zero-trust ingress/egress network policies
│   ├── pdb.yaml                       # PodDisruptionBudget (minAvailable: 1)
│   ├── secret.yaml                    # Sealed/KMS encrypted database & JWT secrets
│   └── service.yaml                   # Headless cluster IP service with named ports
├── terraform/                         # 4 Terraform Modules
│   ├── main.tf                        # VPC (3 AZs), EKS 1.30, RDS Multi-AZ, KMS keys
│   ├── variables.tf                   # Strict variable type definitions & defaults
│   ├── outputs.tf                     # Cluster endpoints, ARN references, VPC IDs
│   └── dr_secondary_region.tf         # Secondary DR region (ap-south-2 Hyderabad)
└── validate_infra.py                  # Static validation & CIS benchmark audit script
```

### Static Validation Results (`infra/validate_infra.py`):
- **Kubernetes Validation:** **PASSED (9/9 manifests)**
  - Pod Security Standards: `enforce: "restricted"`, `audit: "restricted"`
  - Container Security: `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `drop: ["ALL"]`
  - Health Probes: `livenessProbe` and `readinessProbe` correctly mapped to `/api/v1/health`
  - Resource Requests & Limits: Fully defined (CPU: 250m–1000m, Memory: 512Mi–2Gi)
- **Terraform Validation:** **PASSED (4/4 HCL files)**
  - KMS Customer-Managed Key encryption enabled across EBS, RDS, S3, and EKS secrets.
  - RDS Multi-AZ configured with private subnets only (`publicly_accessible = false`).
  - Strict IAM role boundaries with least-privilege policies.

---

## 3. Environment Classification: Local vs Cloud Ground Truth

To eliminate any ambiguity between development and production capabilities:

| Architecture Layer | Local WSL / Docker Environment | AWS Cloud Staging / Production | Status Classification |
| :--- | :--- | :--- | :--- |
| **Compute Orchestration** | Local Process / Docker Compose | Amazon EKS v1.30 (Managed Node Groups) | `CONFIGURED` (Waiting for Phase 7C) |
| **Relational Database** | PostgreSQL 18.6 in Ubuntu WSL | Amazon RDS PostgreSQL 16 Multi-AZ | `OPERATIONALLY VERIFIED` (Local) / `CONFIGURED` (AWS) |
| **Database Security** | Native RLS Enabled & Forced | Native RLS Enabled + AWS IAM DB Auth | `OPERATIONALLY VERIFIED` (Local) |
| **Secrets Management** | Local `.env` / Process Env | AWS Secrets Manager + HashiCorp Vault | `IMPLEMENTED` in Code / `CONFIGURED` |
| **Telemetry & Traces** | In-Memory OpenTelemetry Registry | AWS CloudWatch + OTLP Collector (Jaeger) | `IMPLEMENTED` in Code / `CONFIGURED` |
| **Disaster Recovery** | Scripted point-in-time restore | Cross-Region S3 + RDS Aurora Replica | `TESTED` (Local) / `CONFIGURED` (AWS) |
| **DNS & Ingress** | `localhost:3000` / `localhost:8000` | AWS ALB + Route 53 Multi-AZ Failover | `CONFIGURED` |

---

## 4. AWS Cloud Prerequisites for Phase 7C Deployment

Before executing `terraform apply` and deploying the Kubernetes manifests in Phase 7C, the following external cloud prerequisites must be fulfilled by the institutional tenant:

### 4.1 Cloud Tenant Credentials & Permissions
1. **AWS Account ID:** Target dedicated AWS institutional account.
2. **Primary Region:** `ap-south-1` (Mumbai, India).
3. **Disaster Recovery Region:** `ap-south-2` (Hyderabad, India).
4. **Terraform Execution IAM Role (`arn:aws:iam::<ACCOUNT_ID>:role/PropValTerraformDeployer`):**
   - Must have permissions to manage VPC, EKS, RDS, S3, KMS, Route 53, and IAM roles.
   - Enforce MFA on deployment credentials.
5. **Remote State Backend:**
   - S3 Bucket: `propval-terraform-state-<account_id>-ap-south-1` (Encrypted with AWS KMS, versioning enabled, public access blocked).
   - DynamoDB Table: `propval-terraform-locks` for distributed state locking.

### 4.2 Network & Security Boundaries
1. **Domain Names & ACM Certificates:**
   - Domain: e.g., `pilot.propval.ai` or bank-specific subdomain (`propval.bank-internal.net`).
   - ACM Certificate validated in `ap-south-1` and `ap-south-2`.
2. **Database Isolation:**
   - Private subnets with zero internet gateway ingress.
   - Bastion host or AWS SSM Session Manager access only.
3. **Container Registry (Amazon ECR):**
   - Private ECR repositories with automated image vulnerability scanning on push (`scan_on_push = true`).

---

## 5. Security & DevSecOps Validation Summary

* **CIS AWS Foundation Benchmark Compliance:** The Terraform manifests enforce customer-managed KMS keys, non-public database endpoints, flow logs, and encrypted EBS volumes.
* **Kubernetes Hardening:** Pods run as unprivileged UID 10001, immutable root filesystems, Linux capabilities dropped, zero host network access.
* **Conclusion:** The infrastructure code is structurally verified and ready for cloud staging execution in Phase 7C upon receipt of tenant credentials.

