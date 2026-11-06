# PropVal AI — Phase 7C Deliverable 2
# Institutional Cloud Deployment Report & Operational Assessment

**Document ID:** `PROPVAL-DOC-PHASE7C-02`  
**Execution Timestamp:** 2026-11-06T11:38:30+05:30  
**Phase:** 7C — Live AWS Institutional Cloud Deployment  
**Author:** Senior Cloud Reliability Engineer & DevSecOps Lead  
**Classification:** CONFIGURED & STAGED (LIVE CLOUD PROVISIONING BLOCKED PENDING AWS CREDENTIALS)  

---

## 1. Executive Summary & Pre-Flight Verification

The pre-flight audit for Phase 7C was initiated by reviewing the governance gates from:
- `docs/phase7/PHASE7A_FINAL_DECISION.md` (`READY WITH CONDITIONS`).
- `docs/phase7/PHASE7B_FINAL_IMPLEMENTATION_REPORT.md` (`COMPLETE WITH EXTERNAL DEPENDENCIES PENDING`).
- Infrastructure manifests in `infra/terraform/` and `infra/k8s/`.

### Pre-Flight Verification Checklist:
- [x] Phase 7B institutional onboarding lifecycle implemented.
- [x] Dual-track engine strategy active (`hedonic-scorecard-v0.2.0` active; CatBoost ML blocked).
- [x] Mandatory pilot safety controls verified (zero automated sanctions; advisory-only stamping).
- [x] PostgreSQL Native Row-Level Security (RLS) active and verified on live PostgreSQL 18.6 (10/10 tests pass).
- [x] Kubernetes manifests satisfy Restricted Pod Security Standard (0 violations).
- [x] Terraform HCL configuration adheres to AWS institutional security baselines (0 violations).
- [!] **Live Cloud Access Gate:** Live AWS tenant credentials are not configured in this execution environment. Live cloud deployment is strictly held in **BLOCKED** status.

---

## 2. Infrastructure Component Status Classification

In accordance with strict audit rules, every component must be classified into one of five formal states:
- `CONFIGURED`: Fully declared and syntactically/architecturally verified in IaC manifests.
- `DEPLOYED`: Instantiated and running in a live environment.
- `OPERATIONALLY VERIFIED`: Tested end-to-end with verified live traffic or functional probes.
- `BLOCKED`: Prevented from deploying due to missing authorized credentials or pending gates.
- `NOT IMPLEMENTED`: Missing from code or configuration.

### Component-by-Component Classification Matrix:

| Component | Target AWS Service / Tech | IaC Location | Local / WSL Status | AWS Cloud Status | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. VPC & Subnets** | AWS VPC (3-Tier Multi-AZ) | `infra/terraform/main.tf` | Syntactically Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **2. VPC Flow Logs** | CloudWatch Logs + KMS | `infra/terraform/main.tf` | Syntactically Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **3. KMS CMK Primary** | AWS KMS (ap-south-1) | `infra/terraform/main.tf` | Syntactically Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **4. KMS CMK DR** | AWS KMS (ap-south-2) | `infra/terraform/dr_secondary_region.tf` | Syntactically Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **5. EKS Cluster** | Amazon EKS v1.29 | `infra/terraform/main.tf` | Manifests Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **6. Managed Node Group** | Amazon EC2 (m6i/t3) | `infra/terraform/main.tf` | Manifests Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **7. IAM & IRSA** | IAM OIDC Provider | `infra/terraform/main.tf` | Manifests Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **8. Ingress ALB** | AWS Application Load Balancer | `infra/k8s/ingress.yaml` | Manifests Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **9. Secrets Manager** | AWS Secrets Manager + CSI | `infra/k8s/secrets-provider-class.yaml` | Manifests Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **10. CloudWatch Alarms** | AWS CloudWatch | `infra/terraform/main.tf` | Manifests Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **11. S3 Audit Vault** | Amazon S3 (Object Lock) | `infra/terraform/main.tf` | Manifests Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **12. S3 DR Vault** | Amazon S3 (ap-south-2) | `infra/terraform/dr_secondary_region.tf` | Manifests Verified | Cloud Pending | **CONFIGURED (BLOCKED)** |
| **13. Database (PostgreSQL)** | PostgreSQL 16/18 + PostGIS | `backend/alembic/`, `init_pg_schema.py` | **OPERATIONALLY VERIFIED** | Cloud Pending | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (AWS)** |
| **14. Native PostgreSQL RLS** | PostgreSQL 18 RLS Policies | `backend/scripts/init_pg_schema.py` | **OPERATIONALLY VERIFIED (10/10 PASS)** | Cloud Pending | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (AWS)** |
| **15. Backend Workload** | FastAPI + Uvicorn | `infra/k8s/backend-deployment.yaml` | **OPERATIONALLY VERIFIED (461/461 PASS)** | Cloud Pending | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (AWS)** |
| **16. Frontend Workload** | React + NGINX | `infra/k8s/frontend-deployment.yaml` | **OPERATIONALLY VERIFIED (26/26 PASS)** | Cloud Pending | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (AWS)** |

---

## 3. Cloud Deployment Verification & Blocking Evidence

### 3.1 AWS Credential & Tooling Audit
* **AWS CLI Execution Attempt:**
  ```powershell
  PS> aws sts get-caller-identity
  aws : The term 'aws' is not recognized as the name of a cmdlet, function, script file...
  ```
* **Environment Credential Audit:**
  ```powershell
  PS> python -c "import os; [print(k) for k in os.environ if 'AWS' in k]"
  # Returns 0 matching variables. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are absent.
  ```
* **DevSecOps Mandate:**
  Under Rule 6 & 8 of the project guidelines:
  > *"Never claim that AWS infrastructure is deployed merely because Terraform or Kubernetes manifests exist. Phase 7C cannot be marked complete merely because Terraform and Kubernetes files exist. Actual deployment and operational evidence are required."*
  
  Therefore, the live AWS deployment phase is explicitly reported as **BLOCKED ON AWS CLOUD ACCESS CREDENTIALS**.

### 3.2 Local Infrastructure Validation Results
To verify that the infrastructure manifests are 100% production-ready and error-free when credentials are provided, `infra/validate_infra.py` was executed:
* **Kubernetes Manifest Audit:** 9 files scanned (`backend-deployment`, `backend-service`, `frontend-deployment`, `hpa`, `ingress`, `namespace`, `network-policy`, `secrets-provider-class`, `service-account`).
  - Pod Security Standards: **PASSED** (0 errors).
  - Resource Requests & Limits: **PASSED** (0 errors).
  - Non-Root Execution (`runAsUser: 10001` / `runAsUser: 101`): **PASSED** (0 errors).
  - Network Policy Isolation: **PASSED** (0 errors).
* **Terraform HCL Audit:** 4 files scanned (`main.tf`, `variables.tf`, `outputs.tf`, `dr_secondary_region.tf`).
  - KMS CMK Envelope Encryption: **PASSED** (0 errors).
  - Multi-AZ 3-Tier VPC Subnetting: **PASSED** (0 errors).
  - RDS SSL Enforcement & Zero Public IP: **PASSED** (0 errors).
  - Overall Local Validation Result: **PASSED (READY FOR CLOUD STAGING)**.

---

## 4. Live Cloud Provisioning Runbook (Step-by-Step for Execution Upon Authorization)

When an authorized institutional AWS account and credentials are provided by the user:

### Step 1: AWS Credentials Authentication
```bash
export AWS_ACCESS_KEY_ID="<AUTHORIZED_INSTITUTIONAL_KEY>"
export AWS_SECRET_ACCESS_KEY="<AUTHORIZED_INSTITUTIONAL_SECRET>"
export AWS_DEFAULT_REGION="ap-south-1"
aws sts get-caller-identity
```

### Step 2: Terraform Infrastructure Provisioning
```bash
cd infra/terraform
terraform init
terraform plan -out=tfplan-production.binary
# Review plan with Institutional Cloud Team
terraform apply tfplan-production.binary
```

### Step 3: Kubernetes Cluster Authentication & Secrets Injection
```bash
aws eks update-kubeconfig --region ap-south-1 --name propval-eks-production
aws secretsmanager put-secret-value \
    --secret-id "propval/production/app-secrets" \
    --secret-string '{"JWT_SECRET":"...","DATABASE_URL":"postgresql://...","GEMINI_API_KEY":"..."}'
```

### Step 4: Container Deployment & Database Migration
```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/service-account.yaml
kubectl apply -f infra/k8s/secrets-provider-class.yaml
kubectl apply -f infra/k8s/network-policy.yaml
kubectl apply -f infra/k8s/backend-service.yaml
kubectl apply -f infra/k8s/backend-deployment.yaml
kubectl apply -f infra/k8s/frontend-deployment.yaml
kubectl apply -f infra/k8s/ingress.yaml
kubectl apply -f infra/k8s/hpa.yaml

# Execute database migration job
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=backend -n propval-production --timeout=300s
kubectl exec -it deployment/propval-backend -n propval-production -- alembic upgrade head
```

