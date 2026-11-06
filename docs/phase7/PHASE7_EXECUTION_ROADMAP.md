# PropVal AI — Phase 7: Institutional Pilot Execution Roadmap
**Comprehensive Implementation Plan (Phases 7B through 7H)**
**Document Reference:** `docs/phase7/PHASE7_EXECUTION_ROADMAP.md`  
**Execution Date:** November 6, 2026  
**Auditor / Role:** Senior Fintech Project Architect, Chief Information Security Officer, and ML Governance Lead  

---

## 1. Roadmap Architecture & Phased Milestones

Phase 7 executes the transition of PropVal AI from a locally verified codebase to an institutionally deployed, cloud-hosted, bank-integrated valuation platform.

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7A: Evidence Reconciliation & Pilot Planning [COMPLETED]                    │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7B: Commercial Provider Activation & Ingestion (Reach 1,000+ Deeds)         │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7C: AWS Cloud Staging Deployment & Multi-Region DR (ap-south-1 & 2)         │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7D: Third-Party CERT-In Empanelled VAPT & Security Sign-Off                 │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7E: 1,000-Deed Empirical ML CatBoost Training & Conformal Calibration       │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7F: Institutional Pilot Onboarding (HDFC, ICICI, SBI, Bajaj Finance)        │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7G: Live Shadow Pilot Operations & SLA Verification                         │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7H: Pilot Closure, Model Governance Audit & Full Production Gate            │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 7B: Commercial Provider Activation & Ingestion Execution

### 2.1 Primary Objective
Activate commercial real-estate data feeds (Zapkey Commercial API / SRO Index II partners) with live, paid subscription credentials to ingest at least 600 additional verified empirical deeds, surpassing the 1,000-certified-deed threshold.

### 2.2 Prerequisites & Gate Conditions
- Executed commercial data license agreement with Zapkey / vendor partners.
- Phase 7A Data Readiness Assessment signed off.
- Automated SSRF defenses and PII scrubbing verified in connector pipelines.

### 2.3 Detailed Tasks
1. Inject live commercial API keys into AWS Secrets Manager or secure `.env.production`.
2. Execute automated test fetch to verify Zapkey OAuth/Bearer token authentication.
3. Initiate batch ingestion of registered property deeds for Bengaluru Urban, Mumbai (MMR), and Pune micro-markets.
4. Run automated cleansing pipeline: PII scrubbing, deduplication, circle rate anomaly checks, and coordinate normalization.
5. Record verification evidence linking each deed to official Sub-Registrar Office (SRO) registration numbers.
6. Verify transaction count reaches $\ge 1,000$ certified empirical deeds.
7. Create and freeze an immutable snapshot in `dataset_versions` (e.g. `v2.0.0-empirical-1000`).

### 2.4 External Dependencies
- Commercial Data Vendor API uptime and rate limit allocations.
- Legal approval of data license terms for machine learning derivative use.

### 2.5 Stakeholders
- Senior Data Integration Engineer
- Vendor Relationship Manager
- Fintech Data Governance Lead

### 2.6 Acceptance Criteria
- Stored empirical deeds in `imported_transactions` with `is_verified_deed = 1` count $\ge 1,000$.
- Zero synthetic data contamination in the candidate ML dataset snapshot.
- 100% of PII scrubbed to irreversibly hashed tokens under DPDP compliance.

### 2.7 Security & Governance Risks
- Vendor API downtime or throttling: Handled via exponential backoff and persistent batch queues.
- Scraping prohibited: Zero scraping of government portals; all data obtained via authorized commercial feeds.

---

## 3. Phase 7C: Cloud Staging Deployment & Multi-Region Setup

### 3.1 Primary Objective
Deploy the validated PropVal AI Terraform and Kubernetes manifests into an authorized AWS cloud tenant across primary (`ap-south-1` Mumbai) and secondary (`ap-south-2` Hyderabad) regions.

### 3.2 Prerequisites & Gate Conditions
- Tenant AWS Account ID, IAM deployment role, and S3 state backend provisioned.
- Static infrastructure validation (`infra/validate_infra.py`) clean.
- Docker container images scanned and signed in Amazon ECR.

### 3.3 Detailed Tasks
1. Initialize Terraform remote state backend in S3 with DynamoDB state locking.
2. Apply `infra/terraform/main.tf` to provision VPC, EKS cluster, Multi-AZ RDS PostgreSQL 16, and KMS keys in `ap-south-1`.
3. Apply `infra/terraform/dr_secondary_region.tf` to provision warm-standby S3 bucket and Aurora read replica in `ap-south-2`.
4. Deploy Kubernetes manifests to EKS via ArgoCD or `kubectl`: Namespace, Deployment, HPA, PDB, Ingress, and NetworkPolicies.
5. Run Alembic migrations in cloud PostgreSQL to enable native Row-Level Security (`FORCE ROW LEVEL SECURITY`).
6. Configure Route 53 DNS records with health-check-driven failover.
7. Conduct live cloud disaster recovery drill: Measure actual RTO and RPO under simulated AZ failure.

### 3.4 External Dependencies
- AWS cloud account service quotas (VPC, EKS, RDS instance limits).
- Enterprise DNS delegation and ACM SSL certificates.

### 3.5 Stakeholders
- Senior AWS Cloud Architect
- DevSecOps Engineer
- Infrastructure Site Reliability Engineer (SRE)

### 3.6 Acceptance Criteria
- EKS pods healthy with 0 CrashLoopBackOff events.
- RDS PostgreSQL active with forced RLS across all 7 institutional tables.
- End-to-end API latency for `/api/v1/health` and `/api/v1/valuation/estimate` $< 100\text{ ms}$ (p95).
- Cloud RTO confirmed $\le 20\text{ minutes}$, RPO $\le 5\text{ minutes}$.

---

## 4. Phase 7D: Third-Party External Security & CERT-In VAPT Audit

### 4.1 Primary Objective
Engage a CERT-In empanelled cybersecurity auditing agency to conduct a formal Vulnerability Assessment and Penetration Testing (VAPT) exercise against the cloud staging environment.

### 4.2 Prerequisites & Gate Conditions
- Cloud staging deployment (Phase 7C) fully accessible over private/staged ingress.
- WAF rules, SSL pinning, and rate-limiting active.
- Target scope document and non-destructive testing rules of engagement approved.

### 4.3 Detailed Tasks
1. Deliver architecture diagrams, API specifications, and authenticated test credentials to CERT-In auditor.
2. Conduct black-box, grey-box, and white-box penetration testing:
   - OWASP API Security Top 10 (Broken Object Level Auth, SSRF, Injection, Excessive Data Exposure).
   - PostgreSQL Row-Level Security cross-tenant bypass attempts.
   - Cryptographic audit trail tampering simulation.
3. Receive formal interim findings report; triage any Critical, High, or Medium vulnerabilities.
4. Implement rapid remediations and submit for re-testing.
5. Obtain the formal, signed **CERT-In Empanelled Certificate of Security Audit**.

### 4.4 External Dependencies
- Third-party CERT-In auditing firm engagement schedule (typically 2–3 weeks).

### 4.5 Stakeholders
- Chief Information Security Officer (CISO)
- Lead Penetration Tester (External CERT-In Auditor)
- Principal Backend Security Engineer

### 4.6 Acceptance Criteria
- Zero Critical or High severity vulnerabilities remaining.
- Official CERT-In Certificate of Security Audit issued and committed to compliance archive.

---

## 5. Phase 7E: 1,000-Deed Empirical ML Training & CatBoost Certification

### 5.1 Primary Objective
Unlock the CatBoost pre-training readiness gate using the certified 1,000+ empirical deed snapshot and train, validate, and conformalize the empirical valuation model.

### 5.2 Prerequisites & Gate Conditions
- Phase 7B completed: $\ge 1,000$ verified deeds sealed in approved `dataset_versions` snapshot.
- Zero synthetic transactions in training or calibration sets.
- Model registry governance initialized.

### 5.3 Detailed Tasks
1. Run `backend/app/ml/readiness_gate.py`: Confirm all 7 criteria pass (Sample Size $\ge 1,000$, Commercial License Valid, Synthetic Excluded, Geographic Entropy Passed).
2. Execute chronological train / validation / test splits ($60\% / 20\% / 20\%$) to prevent temporal lookahead bias.
3. Train CatBoost regressor with spatial target encoding, micro-market clustering, and area polynomial features.
4. Compute SHAP value feature attributions for model explainability.
5. Train split conformal prediction intervals on the held-out calibration set ($N \ge 200$) at $90\%$ and $95\%$ confidence levels.
6. Evaluate error metrics: $R^2 \ge 0.80$, MAPE $\le 12.0\%$, Conformal empirical coverage $\ge 90\%$.
7. Seal model artifact in S3 with SHA-256 digest; register in `ml_models` with `certified_for_production = 1`.

### 5.4 External Dependencies
- GPU/Compute instance for hyperparameter tuning (AWS `g5.xlarge` or high-memory CPU).

### 5.5 Stakeholders
- Quantitative Machine Learning Engineer
- Real-Estate Valuation Specialist
- Model Risk Officer

### 5.6 Acceptance Criteria
- Readiness gate passes and returns `GateDecision.APPROVED`.
- Model artifact registered with immutable SHA-256 hash.
- Independent validation confirms finite-sample conformal coverage $\ge 90\%$.

---

## 6. Phase 7F: Institutional Multi-Tenant Pilot Onboarding

### 6.1 Primary Objective
Onboard initial pilot financial institutions into isolated multi-tenant workspaces:
1. **HDFC Bank** (Retail Mortgage Underwriting)
2. **ICICI Bank** (Secured Loan Against Property)
3. **State Bank of India (SBI)** (Housing Finance Division)
4. **Bajaj Finance** (Commercial & LAP Credit Appraisal)

### 6.2 Prerequisites & Gate Conditions
- Phase 7C (Cloud Staging) and Phase 7D (CERT-In Audit) complete.
- PostgreSQL Native RLS actively enforcing tenant boundaries.
- Institutional pilot agreements signed with defined data-sharing protocols.

### 6.3 Detailed Tasks
1. Execute institution registration script via `/api/v1/institutions/onboard`.
2. Generate institution-specific UUIDs, dedicated API keys, and asymmetric JWT signing secrets.
3. Configure institution-specific loan-to-value (LTV) limits, haircut thresholds, and risk tolerances.
4. Establish secure VPN / AWS Direct Connect / PrivateLink endpoints for pilot bank networks.
5. Conduct institutional tenant isolation verification tests: Ensure each bank sees only its own submitted cases.
6. Conduct orientation and technical briefing for bank credit underwriters.

### 6.4 External Dependencies
- Bank IT and information security clearance for pilot environment connectivity.

### 6.5 Stakeholders
- Institutional Relationship Director
- Bank Credit Risk Officers & Technical Leads
- Solutions Architect

### 6.6 Acceptance Criteria
- 4 institutional tenants provisioned with verified RLS isolation.
- Each institution successfully authenticates and receives tenant-scoped tokens.

---

## 7. Phase 7G: Live Shadow Pilot Operations & SLA Verification

### 7.1 Primary Objective
Operate a 30-day live shadow valuation pilot with participating institutions, processing real loan applications side-by-side with bank internal appraisal workflows.

### 7.2 Prerequisites & Gate Conditions
- Phase 7F onboarding complete.
- Live telemetry and error monitoring active with PagerDuty / CloudWatch alerts.

### 7.3 Detailed Tasks
1. Ingest loan applicant collateral records into PropVal AI in shadow mode.
2. Execute automated dual-engine valuation:
   - Primary: Audited rule-based hedonic valuation engine.
   - Secondary: Empirical CatBoost model with conformal confidence bounds.
3. Compare PropVal AI valuations against bank empaneled physical valuer reports.
4. Track operational metrics:
   - Valuation latency ($< 2.0\text{ seconds}$ end-to-end).
   - Valuation variance against physical inspection (target: within $\pm 8\%$).
   - System availability ($99.95\%$ uptime).
5. Review weekly exception logs and circle rate quarantine cases with bank credit committees.

### 7.4 External Dependencies
- Participating banks submitting loan appraisal files regularly.

### 7.5 Stakeholders
- Senior Valuation Underwriter
- DevOps On-Call Engineer
- Bank Credit Underwriting Teams

### 7.6 Acceptance Criteria
- At least 250 shadow valuations processed across the 4 institutions.
- Zero cross-tenant data leakage incidents.
- Availability $\ge 99.95\%$; p95 valuation response time $\le 500\text{ ms}$.

---

## 8. Phase 7H: Pilot Closure, Governance Sign-Off & Production Rollout

### 8.1 Primary Objective
Synthesize shadow pilot findings, conduct the final model governance review, secure bank steering committee sign-offs, and transition PropVal AI to general institutional production.

### 8.2 Prerequisites & Gate Conditions
- 30-day shadow pilot completed with all SLAs met.
- Zero unresolved critical audit defects or security incidents.

### 8.3 Detailed Tasks
1. Aggregate and verify cryptographic audit chain for all pilot transactions (confirm 100% hash continuity).
2. Prepare Pilot Performance Report: Valuer variance analysis, turnaround time reduction (from 4 days to 30 seconds), and risk alert efficacy.
3. Present findings to Bank Model Risk & Credit Risk Committees.
4. Execute formal Production Acceptance Certificates.
5. Transition deployment from Pilot Staging to Production Multi-AZ environment with automated autoscaling.

### 8.4 External Dependencies
- Formal sign-off signatures from participating institutional credit committees.

### 8.5 Stakeholders
- Chief Executive Officer / Product Sponsor
- Bank Chief Risk Officers (CROs)
- Model Governance Board

### 8.6 Acceptance Criteria
- Formal institutional acceptance sign-offs executed by participating banks.
- Production deployment operational with full commercial SLA guarantees.

