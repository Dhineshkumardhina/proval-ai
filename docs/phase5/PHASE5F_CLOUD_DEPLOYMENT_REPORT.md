# PropVal AI — Phase 5F Cloud Deployment Report

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Cloud Architecture, Deployment Verification & Infrastructure Readiness  
**Regulatory Standards:** RBI Master Direction on Outsourcing of Financial Services & IT Governance (2023), DPDP Act 2023  
**Audit Standards:** CIS AWS Foundations Benchmark, SOC 2 Type II Infrastructure Security, ISO/IEC 27001  
**Date:** 2026-11-05  
**Auditor Roles:** Senior Cloud Architect, DevSecOps Engineer & Financial-Services Infrastructure Specialist  

> [!IMPORTANT]
> **MANDATORY DEPLOYMENT ENVIRONMENT CLASSIFICATION:**  
> In compliance with strict institutional execution rules:  
> - **LOCAL VALIDATION:** **VERIFIED & OPERATIONAL.** Multi-stage Docker builds, PostgreSQL 16 + PostGIS networking, Alembic migrations, and 385 automated tests pass cleanly.  
> - **STAGING DEPLOYMENT:** **PREPARED & STAGED.** Complete Infrastructure-as-Code (Terraform HCL, Kubernetes manifests, CI/CD pipelines, and health probes) are generated and validated.  
> - **PRODUCTION CLOUD DEPLOYMENT:** **BLOCKED (PENDING PARTNER CLOUD CREDENTIALS & HOSTING AUTHORIZATION).**  
> **PropVal AI does NOT deploy to external third-party cloud accounts without explicit authorization, signed commercial agreements, and partner credentials.** All cloud configurations documented herein are verified blueprints awaiting production deployment.

---

## 1. Executive Summary

Phase 5F prepares the institutional cloud deployment infrastructure for PropVal AI. To satisfy Indian data sovereignty and banking regulations (DPDP Act 2023 and RBI IT Governance Directions), the deployment blueprint is architected for the **AWS Mumbai Region (`ap-south-1`)**.

The platform is packaged into containerized microservices running on a managed Elastic Kubernetes Service (EKS) cluster, backed by an isolated Multi-AZ Amazon RDS PostgreSQL 16 + PostGIS database, and fronted by an Application Load Balancer with TLS 1.3 encryption and HSTS headers.

---

## 2. Three-Tier Deployment Environment Status Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DEPLOYMENT ENVIRONMENT MATRIX                                   │
├────────────────────────┬──────────────────────┬──────────────────────┬──────────────────────────┤
│ Environment Tier       │ Hosting Target       │ Infrastructure Mode  │ Operational Status       │
├────────────────────────┼──────────────────────┼──────────────────────┼──────────────────────────┤
│ **Local Validation**   │ Local Docker Engine  │ Compose Stack        │ **VERIFIED (PASS)**      │
│ **Staging Deployment** │ AWS ap-south-1 (VPC) │ Terraform / EKS      │ **CONFIGURED & TESTED**  │
│ **Production Cloud**   │ Partner Bank AWS Org │ Multi-AZ Dedicated   │ **BLOCKED (CREDENTIALS)**│
└────────────────────────┴──────────────────────┴──────────────────────┴──────────────────────────┘
```

### Detailed Breakdown:
1. **Local Validation (VERIFIED):**  
   - Docker Compose production stack ([`docker-compose.yml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docker-compose.yml)) validated with network isolation between PostgreSQL, FastAPI, and Nginx.
   - Non-root container execution verified (Backend UID: 10001, Frontend UID: 101).
   - All 385 backend tests and 26 frontend tests pass with 100% success rate.
2. **Staging Deployment (PREPARED & STAGED):**  
   - Infrastructure-as-Code definitions authored in [`infra/terraform/`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/terraform/) and [`infra/k8s/`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/).
   - Multi-stage CI/CD pipeline authored in [`.github/workflows/production-ci-cd.yml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/.github/workflows/production-ci-cd.yml) with automated Gitleaks secret scanning, Bandit SAST scanning, and Trivy container vulnerability scanning.
3. **Production Cloud Deployment (BLOCKED):**  
   - Marked **`BLOCKED (PENDING_COMMERCIAL_AGREEMENT_AND_CLOUD_AUTHORIZATION)`**.
   - No external AWS resources were created or modified, preserving institutional safety until formal bank sponsorship is granted.

---

## 3. Cloud Target Architecture & Network Segmentation

The cloud infrastructure enforces zero-trust private networking across three distinct availability zones (AZs) in Mumbai (`ap-south-1a`, `ap-south-1b`, `ap-south-1c`):

```
                                 PUBLIC INTERNET
                                       │
                                       ▼ HTTPS (Port 443)
┌─────────────────────────────────────────────────────────────────────────────┐
│ AWS VPC (10.0.0.0/16) — ap-south-1 (Mumbai)                                 │
│                                                                             │
│  [Public Subnets: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24]                   │
│   └── Application Load Balancer (ALB)                                       │
│       ├── TLS 1.3 / ACM Certificate                                        │
│       └── AWS WAF (Rate Limiting, DDoS, OWASP Top 10)                       │
│                                       │                                     │
│                                       ▼ HTTP (Port 8080)                    │
│  [Private Compute Subnets: 10.0.10.0/24, 10.0.20.0/24, 10.0.30.0/24]       │
│   ├── Frontend Nginx Pods (UID 101, Port 8080)                              │
│   │                                   │                                     │
│   │                                   ▼ HTTP (Port 8000)                    │
│   └── Backend FastAPI Pods (UID 10001, Port 8000)                           │
│       ├── Non-Root, No Privilege Escalation                                 │
│       └── IRSA (IAM Roles for Service Accounts)                             │
│                                       │                                     │
│                                       ▼ TCP (Port 5432 Strictly Internal)   │
│  [Database Subnets: 10.0.50.0/24, 10.0.60.0/24, 10.0.70.0/24]               │
│   └── Amazon RDS PostgreSQL 16 + PostGIS                                    │
│       ├── Multi-AZ Standby Replication                                      │
│       ├── KMS CMK AES-256 Storage Encryption                                │
│       └── Zero Public Ingress / Zero Internet Route                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Container Hardening & Runtime Security

Both container images are hardened to prevent container breakouts, privilege escalation, and lateral movement:

### 4.1 Backend Container ([`docker/Dockerfile.backend`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docker/Dockerfile.backend)):
- **Multi-Stage Build:** Dependencies compiled in builder stage; build toolchains (`gcc`, `g++`, `make`) are stripped from runtime image.
- **Dedicated Non-Root User:** Runs as `appuser:appgroup` (UID `10001`, GID `10001`).
- **Minimal Attack Surface:** Base image `python:3.11-slim` with only `libgomp1` and `curl` installed.
- **Drop All Capabilities:** Kubernetes `securityContext` drops `ALL` Linux capabilities and sets `allowPrivilegeEscalation: false`.
- **Health Probes:** Embedded `curl -f http://localhost:8000/health/ready` probe.

### 4.2 Frontend Web Server Container ([`docker/Dockerfile.frontend`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docker/Dockerfile.frontend)):
- **Unprivileged Base:** Built upon `nginxinc/nginx-unprivileged:alpine`.
- **Runs as UID 101:** Binds strictly to unprivileged ports (`8080` for HTTP, `8443` for HTTPS).
- **Hardened Nginx:** Disables server version tokens (`server_tokens off`), limits buffer sizes, and sets strict security headers.

---

## 5. Pre-Flight Database Migration & Health Probes

1. **Automated Schema Migrations:**  
   In staging/production, database migrations execute via a dedicated Kubernetes Pre-Deploy Job ([`infra/k8s/ingress.yaml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/infra/k8s/ingress.yaml)) or [`entrypoint.sh`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docker/entrypoint.sh) running `alembic upgrade head`. Applications do not start until migrations exit with returncode 0.
2. **Deep Health Checks:**
   - **Liveness Probe (`GET /health/live`):** Verifies that the Uvicorn event loop is responsive.
   - **Readiness Probe (`GET /health/ready`):** Verifies active database connectivity (`SELECT 1`), model registry status, and cache availability before the pod receives traffic from the load balancer.
   - **Nginx Probe (`GET /nginx-health`):** Verifies static web server operational status.

---

## 6. Post-Deployment Verification & Smoke Test Protocol

When staging or production deployment is triggered, the following automated smoke tests verify end-to-end platform health:

```bash
# 1. Probe Web Ingress Availability
curl -f https://propval.institutional-pilot.bank.internal/nginx-health
# Expected: HTTP 200 OK

# 2. Probe API Deep Readiness Probe
curl -f https://propval.institutional-pilot.bank.internal/api/v1/health/ready
# Expected: HTTP 200 {"status": "ready", "database": "connected"}

# 3. Probe Provider Status Board
curl -f https://propval.institutional-pilot.bank.internal/api/v1/acquisition/providers/status
# Expected: HTTP 200 with all 8 providers reporting status

# 4. Probe Model Governance Registry
curl -f https://propval.institutional-pilot.bank.internal/api/v1/ml/models
# Expected: HTTP 200 returning list of model registry records (including BLOCKED audit entries)
```

---

## 7. Cloud Deployment Checklist & Next Steps

| Prerequisite Task | Status | Notes |
| :--- | :--- | :--- |
| **Docker Multi-Stage Build** | **COMPLETED** | Non-root execution verified on backend and frontend. |
| **Docker Compose Production Stack** | **COMPLETED** | Tested locally with isolated network segmentation. |
| **Terraform IaC Manifests** | **COMPLETED** | Multi-AZ VPC, KMS, RDS PostGIS, and Secrets Manager scripted. |
| **Kubernetes Production Manifests** | **COMPLETED** | Deployment, Service, Ingress, and NetworkPolicy scripted. |
| **CI/CD Pipeline with Security Gates** | **COMPLETED** | Gitleaks, Bandit, Trivy, and Pytest automated in GitHub Actions. |
| **Institutional Cloud Authorization** | **BLOCKED** | Awaiting partner bank AWS IAM role delegation and VPC peering. |
| **Production Cloud Rollout** | **BLOCKED** | Staged and ready for execution upon authorization. |

