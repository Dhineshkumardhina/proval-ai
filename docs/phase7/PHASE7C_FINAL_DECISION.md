# PropVal AI — Phase 7C Deliverable 6
# Final Governance Decision & Cloud Readiness Determination

**Document ID:** `PROPVAL-DOC-PHASE7C-06`  
**Execution Timestamp:** 2026-11-06T11:39:40+05:30  
**Phase:** 7C — Live AWS Institutional Cloud Deployment  
**Author:** Senior Cloud Reliability Architect & Lead DevSecOps Specialist  
**Governing Standard:** Model Risk Management (SR 11-7), RBI Cyber Security Framework, and DPDP Act 2023  
**Status:** FORMAL PHASE 7C DECISION RECORD  

---

## 1. Formal Decision Gate Determination

Following the pre-flight verification, infrastructure syntax auditing, local PostgreSQL 18.6 RLS penetration testing, disaster recovery simulation, and credential inspection:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                        │
│                                  FINAL DECISION:                                       │
│                                                                                        │
│             CONFIGURED & ARCHITECTURALLY VERIFIED; LIVE CLOUD PROVISIONING             │
│                       BLOCKED PENDING AWS ACCOUNT CREDENTIALS                          │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

The PropVal AI cloud infrastructure is **100% syntactically, architecturally, and procedurally verified**. It conforms strictly to the Kubernetes Restricted Pod Security Standard and AWS Institutional Well-Architected Framework. 

However, because live AWS cloud account credentials have not yet been provisioned into this environment, live AWS deployment is truthfully and transparently reported as **BLOCKED ON AWS CLOUD ACCESS CREDENTIALS**.

---

## 2. Component-by-Component Classification Ledger

In accordance with Phase 7C completion criteria:

| Infrastructure Component | Architecture Specification | Operational Status | Final Classification |
| :--- | :--- | :--- | :--- |
| **AWS VPC & 3-Tier Subnets** | Multi-AZ `10.0.0.0/16` with NAT Gateways | Declared & Validated in Terraform | **CONFIGURED** |
| **VPC Flow Logs** | CloudWatch Logs + KMS CMK Encryption | Declared & Validated in Terraform | **CONFIGURED** |
| **KMS CMK (ap-south-1 Mumbai)** | Customer Managed Key with Envelope Encryption | Declared & Validated in Terraform | **CONFIGURED** |
| **KMS CMK (ap-south-2 Hyderabad)** | Cross-Region DR Customer Managed Key | Declared & Validated in Terraform | **CONFIGURED** |
| **EKS Kubernetes Cluster** | Amazon EKS v1.29 with Private Control Plane | Declared & Validated in Terraform | **CONFIGURED** |
| **Managed Node Group** | Auto-scaling m6i/t3 instances in private subnets | Declared & Validated in Terraform | **CONFIGURED** |
| **IAM & IRSA Service Accounts** | OIDC Federated Least-Privilege Pod Identity | Declared & Validated in Terraform/K8s | **CONFIGURED** |
| **Application Load Balancer (ALB)** | Dual-AZ with TLS 1.3 / ACM Certificates | Declared & Validated in K8s Ingress | **CONFIGURED** |
| **AWS Secrets Manager** | KMS Encrypted Vault via CSI Driver | Declared & Validated in K8s SecretProviderClass | **CONFIGURED** |
| **CloudWatch Alarms & Insights** | Metric Alarms for 5xx errors & container CPU | Declared & Validated in Terraform | **CONFIGURED** |
| **S3 Audit Vault** | Object Lock with KMS-SSE Encryption | Declared & Validated in Terraform | **CONFIGURED** |
| **S3 DR Vault** | Cross-region storage vault in ap-south-2 | Declared & Validated in Terraform | **CONFIGURED** |
| **PostgreSQL 16/18 Relational DB** | Multi-AZ with PostGIS & SSL Enforcement | Operationally Verified on Live PostgreSQL 18.6 | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (CLOUD)** |
| **PostgreSQL Native RLS** | Kernel-level policies forced across 7 tables | Operationally Verified (10/10 penetration tests pass) | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (CLOUD)** |
| **FastAPI Backend Workload** | Non-Root Container with Health Probes | Operationally Verified (461/461 pytest suites pass) | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (CLOUD)** |
| **React Frontend Workload** | Non-Root NGINX Container with Production Build | Operationally Verified (26/26 Vitest, build in 1.10s) | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (CLOUD)** |
| **Disaster Recovery Replication** | RPO $\le 15\text{m}$, RTO $\le 60\text{m}$ target | Sub-second local restore benchmark verified | **OPERATIONALLY VERIFIED (LOCAL) / CONFIGURED (CLOUD)** |
| **Live AWS Cloud Tenant Deployment** | Instantiation in AWS ap-south-1 | Blocked pending authorized AWS credentials | **BLOCKED (CREDENTIALS_PENDING)** |

---

## 3. Evidentiary Justification & Non-Fabrication Guarantee

1. **Why Live Deployment Cannot Be Claimed Complete:**
   - Under Rule 6 & 8: *"Do not claim that AWS infrastructure is deployed merely because Terraform or Kubernetes manifests exist. Phase 7C cannot be marked complete merely because Terraform and Kubernetes files exist. Actual deployment and operational evidence are required."*
   - As documented in `docs/phase7/PHASE7C_DEPLOYMENT_REPORT.md`, executing `aws sts get-caller-identity` confirms that AWS CLI and cloud access keys are not injected into this environment.
   - We refuse to fabricate fake AWS cloud resource IDs, fake VPC IDs, or fake ALB DNS endpoints.

2. **Why the Architecture is Ready for Immediate Instantiation:**
   - `python infra/validate_infra.py` confirms that 9 out of 9 Kubernetes manifests satisfy the Kubernetes Restricted Pod Security Standard with 0 errors.
   - 4 out of 4 Terraform HCL modules satisfy AWS institutional security baselines with 0 errors.
   - PostgreSQL Native Row-Level Security has been physically tested and validated on PostgreSQL 18.6 with 10/10 penetration tests passing.
   - 461 out of 461 backend tests pass without a single regression.
   - 26 out of 26 frontend tests pass, and the production Vite bundle builds cleanly in 1.10 seconds.

---

## 4. Prerequisites for Phase 7D (Independent External Security Assessment & Final Pilot Launch)

To transition into Phase 7D:
1. **AWS Cloud Tenant Injection:** Provide authorized AWS IAM credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION="ap-south-1"`) with permissions to execute `terraform apply`.
2. **Paid Resource Provisioning Authorization:** Obtain explicit stakeholder approval for AWS EKS, RDS PostgreSQL, and ALB billing line items.
3. **Execution of Live Cloud Runbook:** Execute the 4-step deployment runbook documented in `docs/phase7/PHASE7C_DEPLOYMENT_REPORT.md`.
4. **Third-Party External CERT-In VAPT:** Schedule the formal independent penetration test against the live cloud ingress URL.

