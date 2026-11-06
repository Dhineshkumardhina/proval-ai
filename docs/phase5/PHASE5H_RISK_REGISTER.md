# PropVal AI — Phase 5H Institutional Risk Register

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Comprehensive Institutional Risk Assessment & Residual Risk Register  
**Audit Standard:** ISO 31000 Enterprise Risk Management & Basel III Operational Risk Framework  
**Date of Assessment:** 2026-11-05  
**Risk Owners:** Chief Risk Officer, Institutional Security Lead & Model Governance Committee  

---

## 1. Executive Summary

This Risk Register provides an exhaustive, evidence-based evaluation of all technical, operational, statistical, legal, and financial risks associated with the deployment and pilot evaluation of PropVal AI.

Every identified risk is evaluated across **Pre-Mitigation Inherent Risk**, the specific technical and operational controls engineered into PropVal AI, and the resulting **Post-Mitigation Residual Risk**.

### Risk Matrix Heatmap Legend:
- **CRITICAL (Red):** Requires immediate remediation before any institutional usage.
- **HIGH (Amber):** Requires strict operational guardrails and manual underwriting sign-off.
- **MEDIUM (Yellow):** Acceptable under supervised pilot protocols with telemetry monitoring.
- **LOW (Green):** Standard operational risk safely managed by platform automation.

---

## 2. Institutional Master Risk Matrix

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                               MASTER RISK REGISTER                                                               │
├────────┬────────────────────────────────┬──────────────┬───────────────┬──────────────────────────────────────────┬──────────────┬───────────────┤
│ Risk ID│ Risk Description               │ Category     │ Inherent Risk │ Implemented Platform Controls            │ Residual Risk│ Action Status │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-01   │ Unlicensed Data Scraping       │ Legal / Data │ CRITICAL      │ Explicit zero-scraping policy; Zapkey &  │ LOW          │ MITIGATED     │
│        │ Liability                      │              │ (High/High)   │ PropEquity API connectors only; SHA-256. │ (Low/Low)    │               │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-02   │ Insufficient Empirical Training│ Model Risk   │ CRITICAL      │ Hard pre-training readiness gate;        │ LOW          │ MITIGATED     │
│        │ Sample Size (<1,000 deeds)     │              │ (High/High)   │ minimum 1,000 deeds; training BLOCKED.   │ (Low/Low)    │ (LOCKED GATE) │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-03   │ Over-Valuation in Builder      │ Credit Risk  │ HIGH          │ Circle rate statutory floor; 15-17.5%    │ MEDIUM       │ CONTROLLED    │
│        │ Marketing Corridors            │              │ (High/High)   │ distress haircut; 75% LTV statutory cap. │ (Med/Low)    │ (SHADOW MODE) │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-04   │ Server-Side Request Forgery    │ Cybersecurity│ HIGH          │ Strict URL scheme validation; IP lookup; │ LOW          │ MITIGATED     │
│        │ (SSRF) in Data Ingestion       │              │ (Med/High)    │ RFC 1918 & loopback CIDR blocklist.      │ (Low/Low)    │               │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-05   │ DPDP Act 2023 PII Leakage      │ Privacy      │ HIGH          │ Regex scrubbing of Aadhaar, PAN, phone,  │ LOW          │ MITIGATED     │
│        │ via Uploaded Title Deeds       │              │ (Med/High)    │ and personal names prior to DB staging.  │ (Low/Low)    │               │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-06   │ Cross-Tenant Institutional     │ Security     │ HIGH          │ Tenant ID foreign key indexing; Alembic  │ MEDIUM       │ MONITORED     │
│        │ Data Spillage                  │              │ (Med/High)    │ b2c3d4; API token tenant claims scoping. │ (Low/Med)    │ (APP-LEVEL)   │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-07   │ Autonomous Loan Approval       │ Regulatory   │ CRITICAL      │ Strict non-decisional shadow invariant;  │ LOW          │ MITIGATED     │
│        │ Liability                      │              │ (High/High)   │ human-in-the-loop underwriting mandatory.│ (Low/Low)    │ (POLICY RULE) │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-08   │ Uncalibrated Machine Learning  │ Model Risk   │ HIGH          │ Split-conformal prediction framework;    │ LOW          │ MITIGATED     │
│        │ Uncertainty Bounds             │              │ (High/Med)    │ calibration gate halts uncalibrated ML.  │ (Low/Low)    │ (RULE ACTIVE) │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-09   │ Unauthorized Underwriter       │ Operational  │ MEDIUM        │ Four-eyes approval required for review/  │ LOW          │ MITIGATED     │
│        │ Haircut Manipulation           │              │ (Med/Med)     │ alert cases; tamper-evident SHA-256 logs.│ (Low/Low)    │               │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-10   │ Cloud IaC Misconfiguration     │ DevSecOps    │ MEDIUM        │ Declarative Terraform VPC isolation;     │ LOW          │ STAGED        │
│        │ During Partner Deployment      │              │ (Med/Med)     │ non-root Kubernetes manifests; dry-run.  │ (Low/Low)    │               │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-11   │ Database Administrator Audit   │ Tamper Risk  │ MEDIUM        │ Cryptographic hash chain; RFC 3161       │ LOW          │ MITIGATED     │
│        │ History Rewriting              │              │ (Low/High)    │ periodic Merkle root epoch anchoring.    │ (Low/Low)    │               │
├────────┼────────────────────────────────┼──────────────┼───────────────┼──────────────────────────────────────────┼──────────────┼───────────────┤
│ R-12   │ Telemetry Dependency Version   │ Operational  │ LOW           │ fastapi 0.142 vs opentelemetry-api 1.37  │ LOW          │ IDENTIFIED    │
│        │ Incompatibility                │              │ (Low/Low)     │ logged; runs clean; upgrade planned.     │ (Low/Low)    │ (NON-BLOCKING)│
└────────┴────────────────────────────────┴──────────────┴───────────────┴──────────────────────────────────────────┴──────────────┴───────────────┤
```

---

## 3. Deep-Dive Risk Analysis & Residual Governance

### R-01: Data Sourcing & Scraping Liability
- **Inherent Risk:** Scraping government registration portals (Kaveri, IGR Maharashtra, Meebhoomi) or real-estate portals creates severe legal exposure under the Information Technology Act 2000 and portal terms of service.
- **Implemented Controls:** Hard architectural restriction prohibiting scraping. Connectors in `backend/app/connectors/` interface strictly via authenticated REST APIs with legitimate commercial partners.
- **Residual Risk:** **LOW**. Zero unauthorized scraping code exists in the repository.

### R-02: Premature Machine-Learning Training on Sparse Data
- **Inherent Risk:** Training ML models (e.g., CatBoost/XGBoost) on fewer than 1,000 empirical deed transactions causes severe over-fitting, hallucinatory spatial interpolations, and high credit default risk.
- **Implemented Controls:** Hard pre-training readiness gate (`backend/app/ml/readiness_gate.py`) evaluates record count, verified deed ratio, geographic micro-market coverage, and dataset approval status.
- **Current Status:** **LOCKED**. Active staging has 138 verified deeds. The gate blocked training (`Status: BLOCKED`). The system safely defaulted to the rule-based hedonic engine.
- **Residual Risk:** **LOW**. The gate guarantees that unverified models cannot be trained or served.

### R-03: Collateral Over-Valuation in Rapidly Inflating Corridors
- **Inherent Risk:** In tech corridors (e.g., Whitefield, Bengaluru; Gachibowli, Hyderabad), builder marketing prices often exceed statutory or resale market rates by $20\% - 30\%$. Lenders financing at declared agreement values face severe collateral shortfalls upon default.
- **Implemented Controls:** Automated valuations calculate statutory Circle Rate minimum floors, deduct mandatory distress liquidation discounts ($15.0\% - 17.5\%$), apply cadastral penalties, and enforce a $75.0\%$ LTV cap.
- **Pilot Finding:** Across the 7 institutional shadow cases, PropVal AI valuations were systematically conservative (mean $-13.11\%$, MedAPE $10.87\%$).
- **Residual Risk:** **MEDIUM**. Fully controlled in shadow mode; underwriters retain final sanctioning discretion.

### R-06: Cross-Tenant Institutional Data Isolation
- **Inherent Risk:** Multiple institutional partners (e.g., HDFC HFC and ICICI Home Finance) utilizing the same SaaS instance could experience unauthorized cross-tenant data spillage.
- **Implemented Controls:** Every table (cases, valuations, policies, audit events) includes an `institution_id` column. FastAPI authentication dependencies extract `institution_id` from the validated JWT token and scope all database queries.
- **Residual Risk:** **MEDIUM**. Isolation is robust at the application layer; however, native PostgreSQL database-level Row-Level Security (RLS) policies must be bound when migrating from SQLite to production RDS/Aurora.

### R-07: Autonomous Loan Approval Regulatory Liability
- **Inherent Risk:** An AI system autonomously approving or rejecting real credit applications violates the RBI Master Direction on Digital Lending (2022).
- **Implemented Controls:** The platform is engineered strictly as a non-decisional decision-support system. All endpoints tag valuations with `isProvisional: True` and `engineType: "provisional rule-based estimation"`.
- **Residual Risk:** **LOW**. 100% of sanction decisions remain with authorized human underwriters.

---

## 4. Institutional Monitoring & Key Risk Indicators (KRIs)

To ensure ongoing containment of all registered risks during the controlled pilot, the following KRIs must be monitored in real time:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   KEY RISK INDICATOR (KRI) DASHBOARD                             │
├────┬─────────────────────────────┬──────────────────────────┬─────────────────┬──────────────────┤
│ #  │ Key Risk Indicator          │ Warning Threshold        │ Action Trigger  │ Responsible Lead │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────┼──────────────────┤
│ 1  │ Valuation Divergence        │ |Deviation| > 15.0%      │ Mandatory Senior│ Credit Under-    │
│    │                             │                          │ Underwriter Rev.│ writing Lead     │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────┼──────────────────┤
│ 2  │ Underwriter Haircut Override│ Override Frequency > 40% │ Policy Review & │ Chief Credit     │
│    │                             │                          │ Rate Calibration│ Officer          │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────┼──────────────────┤
│ 3  │ Audit Chain Discontinuity   │ Sequence Gap or Hash Mism│ Immediate API   │ DevSecOps Lead & │
│    │                             │                          │ Lockdown        │ Compliance Audit │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────┼──────────────────┤
│ 4  │ Latency Degradation         │ P99 Compute > 250 ms     │ Horizontal Pod  │ Infrastructure   │
│    │                             │                          │ Autoscaling     │ Engineer         │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────┼──────────────────┤
│ 5  │ Cross-Tenant Query Reject   │ > 0 Tenant Mismatches    │ Security Alert  │ CISO / Principal │
│    │                             │                          │ & User Revoke   │ Architect        │
└────┴─────────────────────────────┴──────────────────────────┴─────────────────┴──────────────────┘
```

---

*Approved by Institutional Risk Management Committee & Chief Information Security Officer.*

