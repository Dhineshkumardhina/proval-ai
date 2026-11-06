# PropVal AI — Phase 5H Technical Remediation Roadmap

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Production Readiness Remediation Plan & Institutional Transition Roadmap  
**Execution Standard:** ISO/IEC 12207 Software Life Cycle Processes & Agile Governance  
**Date of Issue:** 2026-11-05  
**Roadmap Leads:** Chief Technology Officer, Head of Engineering & Chief Risk Officer  

---

## 1. Executive Summary

This Roadmap outlines the exact, prioritized technical, operational, and governance milestones required to transition PropVal AI from its current status of **READY FOR CONTROLLED INSTITUTIONAL PILOT** (in shadow mode) to **PRODUCTION READY**.

Milestones are prioritized into four strict categories:
- **P0: Critical Production Blockers** (Must be resolved before live underwriting deployment).
- **P1: High-Priority Operational Safeguards** (Must be resolved before expanding pilot to multi-branch operations).
- **P2: Medium-Priority Enhancements** (Post-pilot integration with Core Banking and LOS systems).
- **P3: Long-Term Capabilities** (Computer vision, geospatial hazard modeling, and advanced automation).

---

## 2. Prioritized Remediation Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            TECHNICAL REMEDIATION MATRIX                                                │
├────┬──────┬──────────────────────────────────────────┬─────────────────────────────┬──────────────┬────────────────────┤
│ ID │ Pri. │ Remediation Task                         │ Target Component / File     │ Lead Owner   │ Verification Gate  │
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M1 │ P0   │ Execute Commercial Data Vendor Agreements│ Zapkey / PropEquity Legal   │ Head of Data │ Live API Keys in   │
│    │      │ (Real-world transaction data acquisition)│ Business Operations         │ Partnerships │ Vault / Secrets Mgr│
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M2 │ P0   │ Accumulate ≥ 1,000 Certified Deeds       │ Ingestion & Staging Pipeline│ Lead Data    │ Pre-Training Gate  │
│    │      │ (Satisfy pre-training readiness gate)    │ `app.ml.readiness_gate`     │ Scientist    │ Passes in Prod DB  │
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M3 │ P0   │ Provision Partner Cloud Infrastructure   │ `infra/terraform/`          │ DevSecOps    │ `terraform apply`  │
│    │      │ (AWS VPC, EKS, RDS PostGIS, TLS Ingress) │ `infra/k8s/`                │ Lead         │ 200 OK Smoke Test  │
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M4 │ P0   │ Enable Database-Native Row-Level Security│ AWS Aurora PostgreSQL       │ Lead DB      │ Tenant Spillage    │
│    │      │ (Bind PostgreSQL RLS policies to tenants)│ `backend/alembic/`          │ Architect    │ Injection Blocked  │
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M5 │ P1   │ Resolve OpenTelemetry Dependency Mismatch│ `pyproject.toml` /          │ Backend      │ `pip check`        │
│    │      │ (Upgrade opentelemetry-api to ≥ 1.44.0)  │ `requirements.txt`          │ Engineer     │ Returns 0 warnings │
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M6 │ P1   │ Train & Calibrate Empirical CatBoost ML  │ `app.ml.trainer`            │ Quantitative │ Test MAPE ≤ 10.0%, │
│    │      │ (Out-of-time chronological validation)   │ `app.ml.conformal`          │ ML Engineer  │ 90% Coverage Calib │
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M7 │ P1   │ Execute Live Multi-Region DR Drill       │ `PHASE5F_DISASTER_RECOVERY` │ DevSecOps    │ RPO ≤ 15 min,      │
│    │      │ (Verify RDS Aurora Cross-Region Replica) │ Cloud SRE Team              │ Lead         │ RTO ≤ 60 min Met   │
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M8 │ P1   │ External CERT-In Empanelled VAPT Audit   │ Complete External Attack    │ Third-Party  │ Clean VAPT Audit   │
│    │      │ (Penetration testing & OWASP Top 10)     │ Surface & API Gateway       │ Security Lab │ Attestation Report │
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M9 │ P2   │ LOS / Core Banking System Webhook Connect│ Webhook Dispatch Service    │ Integration  │ FinnOne / Finacle  │
│    │      │ (Automate case ingestion from FinnOne)   │ `app.services.institution`  │ Architect    │ End-to-End Callback│
├────┼──────┼──────────────────────────────────────────┼─────────────────────────────┼──────────────┼────────────────────┤
│ M10│ P2   │ Surveyor Geotagged Mobile PWA Support    │ React PWA / Geolocation API │ Frontend     │ Offline Cache &    │
│    │      │ (Offline inspection upload & photo EXIF) │ `src/components/`           │ Tech Lead    │ EXIF Validation    │
└────┴──────┴──────────────────────────────────────────┴─────────────────────────────┴──────────────┴────────────────────┘
```

---

## 3. Deep-Dive Remediation Specifications

### Milestone 1 & 2: Commercial Data Acquisition & ML Gate Unlock (P0)
- **Objective:** Secure valid commercial data licensing and ingest $\ge 1,000$ authentic registration deeds across Bengaluru, Mumbai, Delhi-NCR, and Hyderabad.
- **Action Steps:**
  1. Finalize enterprise data reseller agreement with Zapkey / PropEquity.
  2. Configure `DATA_PROVIDER_API_KEY` and `DATA_PROVIDER_SECRET` in institutional AWS Secrets Manager.
  3. Execute batch ingestion jobs via `backend/app/services/acquisition_service.py`.
  4. Verify deduplication and DPDP Act PII scrubbing.
  5. Run pre-training gate audit:
     ```bash
     python -c "from app.ml.readiness_gate import evaluate_training_gate; ..."
     ```
  6. Transition dataset approval status to `APPROVED`.

### Milestone 3: Cloud Infrastructure Provisioning (P0)
- **Objective:** Provision authorized cloud hosting environment within partner AWS account.
- **Action Steps:**
  1. Initialize Terraform backend with encrypted S3 state bucket and DynamoDB locking.
  2. Deploy `infra/terraform/main.tf` to spin up VPC (three private subnets, NAT Gateway, Security Groups), EKS cluster, and Amazon RDS PostgreSQL instance with PostGIS extension.
  3. Deploy Kubernetes manifests in `infra/k8s/`:
     ```bash
     kubectl apply -f infra/k8s/namespace.yaml
     kubectl apply -f infra/k8s/network-policy.yaml
     kubectl apply -f infra/k8s/backend-deployment.yaml
     kubectl apply -f infra/k8s/backend-service.yaml
     kubectl apply -f infra/k8s/frontend-deployment.yaml
     kubectl apply -f infra/k8s/ingress.yaml
     ```
  4. Bind AWS ACM TLS certificate to Ingress controller.
  5. Verify non-root execution (`appuser`, UID 10001).

### Milestone 4: Native PostgreSQL Row-Level Security (RLS) (P0)
- **Objective:** Move beyond application-level tenant filtering to cryptographically enforced database-native RLS.
- **Action Steps:**
  1. Create Alembic migration script executing PostgreSQL RLS policies:
     ```sql
     ALTER TABLE valuation_cases ENABLE ROW LEVEL SECURITY;
     CREATE POLICY tenant_isolation_policy ON valuation_cases
         USING (institution_id = current_setting('app.current_tenant_id', true));
     ```
  2. Update SQLAlchemy session initialization in `backend/app/core/database.py` to execute `SET LOCAL app.current_tenant_id = :tenant_id` at transaction start.
  3. Run multi-tenant penetration tests verifying that cross-tenant injection attempts return empty result sets even if SQL filters are bypassed.

### Milestone 5: OpenTelemetry Dependency Version Harmonization (P1)
- **Objective:** Resolve dependency warning discovered during independent auditor `pip check`.
- **Finding:** `fastapi 0.142.2` requires `opentelemetry-api >= 1.44.0`, whereas local environment had `1.37.0`.
- **Action Steps:**
  1. Update `pyproject.toml` or `requirements.txt`:
     ```toml
     opentelemetry-api = ">=1.44.0"
     opentelemetry-sdk = ">=1.44.0"
     ```
  2. Run `pip install --upgrade opentelemetry-api opentelemetry-sdk`.
  3. Re-run `python -m pip check` and verify 0 incompatibilities.

### Milestone 6: Empirical ML Model Training & Conformal Calibration (P1)
- **Objective:** Train CatBoost gradient boosting model on $\ge 1,000$ certified deeds and calibrate split-conformal prediction intervals.
- **Action Steps:**
  1. Trigger chronological cross-validation via `backend/app/ml/trainer.py`.
  2. Confirm test MAPE $\le 10.0\%$, RMSE within corridor benchmarks, and $R^2 \ge 0.85$.
  3. Calibrate conformal prediction non-conformity scores on held-out calibration split ($20\%$ sample).
  4. Verify conformal prediction interval coverage $\ge 90.0\%$ via `backend/app/ml/calibration_gate.py`.
  5. Promote model to `ACTIVE` in `ml_models` table; save artifact to encrypted S3 bucket (`s3://propval-models-prod/catboost_v1.0.cbm`).

---

## 4. Implementation Phasing & Estimated Timeline

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              REMEDIATION EXECUTION TIMELINE                            │
├─────────┬───────────────────────────────────────────┬───────────────┬──────────────────┤
│ Phase   │ Scope & Focus                             │ Duration      │ Exit Criteria    │
├─────────┼───────────────────────────────────────────┼───────────────┼──────────────────┤
│ Stage 1 │ P0 Commercial Contracting & Data Ingestion│ Weeks 1–3     │ 1,000 Deeds Ingest│
│ Stage 2 │ P0 Cloud Provisioning & DB Native RLS     │ Weeks 3–5     │ EKS + RDS Live   │
│ Stage 3 │ P1 ML Training & Conformal Calibration    │ Weeks 5–7     │ Model Certified  │
│ Stage 4 │ P1 Third-Party VAPT & DR Drill Execution  │ Weeks 7–8     │ VAPT Cert-In Pass│
│ Stage 5 │ Controlled Institutional Multi-Branch Roll│ Weeks 9–12    │ Pilot Expansion  │
└─────────┴───────────────────────────────────────────┴───────────────┴──────────────────┘
```

---

*Approved for Implementation by Institutional Architecture Review Board.*

