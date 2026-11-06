# PropVal AI — Phase 6H: Remaining Risk Register

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6H — Independent External Security Assessment & Final Production Readiness Audit  
**Date:** 2026-11-06  
**Author:** Chief Risk Officer, Enterprise Information Security Specialist & Quantitative Auditor  
**Audit Baseline:** Post-Phase 6G Implementation  
**Review Frequency:** Bi-Weekly during Controlled Institutional Pilot

---

## 1. Risk Governance & Scoring Methodology

Risks are quantified using standard financial enterprise risk matrix scoring:
$$\text{Risk Score} = \text{Severity (1–5)} \times \text{Likelihood (1–5)}$$

* **Critical (16–25):** Unacceptable for production release; mandatory blocker.
* **High (10–15):** Permitted only under controlled pilot with active human guardrails.
* **Medium (5–9):** Managed via operational controls and monitoring alarms.
* **Low (1–4):** Acceptable residual risk.

---

## 2. Comprehensive Inventory of Remaining Open Risks

| Risk ID | Risk Title & Description | Domain | Severity (1–5) | Likelihood (1–5) | Score (1–25) | Impact & Current Mitigation | Remediation Exit Criteria | Status |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|:---:|
| **RSK-DATA-001** | **Empirical Dataset Threshold Deficit (< 1,000 Certified Deeds)**<br>Current approved dataset snapshots contain 140 unique verified deeds against the 1,000 requirement. | Data / ML | 4 | 5 | **20 (High)** | *Impact:* CatBoost empirical model cannot be trained or promoted.<br>*Mitigation:* CatBoost model training is strictly gated (`status='BLOCKED'`). All valuations are served by the deterministic rule-based hedonic engine. | Ingestion and certification of $\ge 1,000$ unique empirical registered deeds. | **OPEN (MITIGATED FOR PILOT)** |
| **RSK-DATA-002** | **Commercial Provider Agreements Pending**<br>Live commercial data provider agreements (e.g. Zapkey) and authenticated credentials remain in staging. | Commercial / Legal | 4 | 4 | **16 (High)** | *Impact:* Live real-time SRO deed streaming is inactive.<br>*Mitigation:* Connector technical integration is built, validated, and staged with SSRF/rate-limit controls. | Execution of commercial agreements and injection of production API keys into AWS Secrets Manager. | **OPEN (PENDING CONTRACT)** |
| **RSK-CLOUD-001** | **Live AWS Cloud Tenant Deployment Pending**<br>Terraform and Kubernetes manifests are validated locally, but live deployment into an AWS account is blocked awaiting enterprise credentials. | Cloud / Infra | 4 | 4 | **16 (High)** | *Impact:* System is currently validated on local / WSL PostgreSQL and container test environments.<br>*Mitigation:* Automated validation scripts (`validate_infra.py`) verify 100% manifest and HCL compliance. | Provisioning of institutional AWS tenant, IAM credentials, and execution of `terraform apply`. | **OPEN (CREDENTIALS PENDING)** |
| **RSK-SEC-001** | **External CERT-In Empanelled VAPT Pending**<br>Comprehensive internal security testing has passed, but formal external penetration testing by a certified firm has not yet been conducted. | Security / Compliance | 4 | 3 | **12 (Medium)** | *Impact:* Regulatory requirement for commercial bank deployment.<br>*Mitigation:* Internal OWASP API Top 10 defenses, native RLS, rate limiting, and SSRF controls are verified. | Commissioning and successful completion of third-party CERT-In empanelled VAPT engagement. | **OPEN (PREPARED FOR AUDIT)** |
| **RSK-DR-001** | **Live Multi-Region Drill Unexecuted in Cloud**<br>Disaster recovery restoration was timed and validated in controlled environments, but a live cloud failover drill between Mumbai and Hyderabad has not occurred. | Cloud / Resilience | 3 | 3 | **9 (Medium)** | *Impact:* Real cloud replication latency and DNS TTL variance untested on live AWS backbones.<br>*Mitigation:* Warm standby Terraform architecture configured; RTO/RPO targets mathematically validated. | Execution of live disaster recovery drill during staged cloud deployment. | **OPEN (PLANNED FOR STAGING)** |
| **RSK-MODEL-001** | **Lack of Empirically Calibrated Prediction Intervals**<br>Conformal prediction calibration requires an active empirical ML model, and is currently gated. | Quantitative Risk | 3 | 3 | **9 (Medium)** | *Impact:* Uncertainty bands currently rely on rule-based haircut bounds rather than statistical non-conformity quantiles.<br>*Mitigation:* Conservative heuristic haircuts ($10\% - 25\%$) protect against overvaluation. | Conformal calibration execution post-CatBoost empirical model training. | **OPEN (GATED)** |
| **RSK-OPS-001** | **Human Underwriter Workflow Reliance**<br>The platform relies on human underwriters to review and approve provisional valuations. | Operational | 2 | 4 | **8 (Medium)** | *Impact:* Workflow throughput constrained by underwriter availability.<br>*Mitigation:* Underwriter approval is an intentional regulatory safeguard (Four-Eyes Principle). | Transition to semi-automated straight-through processing (STP) only after empirical model certification. | **ACCEPTED CONTROL** |

---

## 3. Risk Mitigation Governance During Controlled Pilot

During the **Controlled Institutional Pilot**, the platform's risk profile is effectively managed through four interlocking guardrails:
1. **Scope Boundary:** Valuation outputs are strictly **advisory** and must be reviewed and signed off by a qualified HFC credit officer before any loan sanction.
2. **Deterministic Predictability:** The valuation engine uses deterministic, auditable hedonic scorecards rather than black-box statistical models.
3. **Data Isolation:** PostgreSQL native RLS guarantees that pilot institutions cannot view or contaminate each other's valuation cases or applicant data.
4. **Audit Trail:** Every calculation, case update, and sign-off creates an immutable SHA-256 block in the cryptographic ledger for supervisory review.

