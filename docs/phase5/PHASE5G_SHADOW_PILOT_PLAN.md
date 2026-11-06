# PropVal AI — Phase 5G Shadow Pilot Plan

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Controlled Institutional Shadow Pilot Protocol & Operational Governance Plan  
**Regulatory Frameworks:** RBI Guidelines on Digital Lending & Outsourcing, NHB Valuation Standards, DPDP Act 2023  
**Audit Standard:** ISO/IEC 25010 System Quality & SOC 2 Type II Operational Governance  
**Date:** 2026-11-05  
**Pilot Leads:** Senior Institutional FinTech Architect, Mortgage Underwriting Specialist & QA Lead  

> [!IMPORTANT]
> **MANDATORY SHADOW EVALUATION RULE:**  
> **This pilot is strictly a parallel shadow evaluation.**  
> **PropVal AI does NOT independently approve, sanction, or reject real home loan applications.**  
> All credit decisions during this pilot remain 100% with authorized institutional human underwriters following existing credit policies.

---

## 1. Executive Summary & Precondition Blocker Audit

Phase 5G specifies the operational, technical, and regulatory framework for executing a controlled shadow underwriting pilot with institutional mortgage lending partners (Housing Finance Companies, Scheduled Commercial Banks, or NBFCs).

### 1.1 Precondition Verification Matrix:

| Precondition Requirement | Status | Verification Evidence / Finding |
| :--- | :--- | :--- |
| **1. Institutional Authorization** | **BLOCKED** | Formal bilateral partnership agreements or institutional MoUs are pending execution. |
| **2. Legal Data Licensing** | **BLOCKED** | Commercial API provider contracts (PropEquity, Zapkey) are pending execution (Phase 5C). |
| **3. Security & Privacy Approvals**| **VERIFIED** | DevSecOps security audit passed; DPDP Act 2023 PII scrubbing verified (Phase 5F). |
| **4. Authorized Cloud Deployment** | **BLOCKED** | Production cloud deployment is held pending partner cloud credentials (Phase 5F). |
| **5. Human Underwriting Controls** | **VERIFIED** | Four-eyes approval, manual haircut overrides, and audit chaining operational. |
| **6. Model Governance Gates** | **LOCKED** | Empirical ML gate locked (46 / 1,000 deeds accumulated); rule-based engine active. |

### Institutional Execution Ruling:
Because Preconditions 1, 2, 4, and 6 are pending external commercial/cloud execution, **a live real-world pilot cannot be executed.** In accordance with institutional safety rules, **the pilot is executed in a CONTROLLED SIMULATED SHADOW MODE** using standardized institutional test cases, verified baseline surveyor records, and simulated partner workflows.

---

## 2. Pilot Scope & Governance Architecture

```
[Borrower Loan Application & Property Documents]
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
[Existing Bank Workflow]        [PropVal AI Shadow Engine]
 - Physical Site Inspection      - Automated Circle Rate Lookup
 - Empaneled Surveyor Report     - Rule-Adjusted Hedonic Pricing
 - Manual Underwriter Review     - Cadastral & Legal Risk Penalties
       │                               │
       ▼                               ▼
[Sanction Recommendation]       [Shadow Valuation Estimate]
       │                               │
       └───────────────┬───────────────┘
                       │
                       ▼
        [Underwriter Comparison & Reconciliation]
         - Variance Tracking (System vs. Manual)
         - Haircut & Liquidation Comparison
         - Human Underwriter Override Recording
         - Cryptographic Audit Event Chaining
```

---

## 3. Participating User Roles & Responsibilities

The pilot defines five distinct institutional roles, mapped directly to PropVal AI's Role-Based Access Control (RBAC):

1. **Chief Credit Officer / Pilot Sponsor (`ROLE_ADMIN`):**  
   Oversees the pilot, defines credit policy limits (LTV ceilings, CIBIL floors), and authorizes pilot reports.
2. **Senior Credit Underwriter (`ROLE_SENIOR_UNDERWRITER`):**  
   Conducts head-to-head comparison of PropVal AI estimates against physical valuation reports; applies discretionary haircuts; inputs override rationales.
3. **Credit Underwriter (`ROLE_CREDIT_UNDERWRITER`):**  
   Reviews borrower financials, verifies document completeness (RERA, BBMP approvals, 30-year title search), and initiates shadow valuation runs.
4. **Empaneled Valuation Surveyor (`VALUATION_SURVEYOR`):**  
   Provides independent physical inspection reports (carpet area measurements, structural condition, road width) as the ground-truth baseline.
5. **Quality Assurance & Audit Lead (`ROLE_RISK_COMMITTEE_MEMBER`):**  
   Monitors system latency, error rates, and ensures tamper-evident audit chaining in `audit_events`.

---

## 4. Eligible Property Case Cohort

The shadow pilot restricts eligibility to residential collateral properties satisfying institutional credit criteria:

- **Property Typology:** High-Rise Apartments, Gated Community Villas, and Independent Floors.
- **Geographic Coverage:** Tier-1 Metropolitan Hubs:
  - Bengaluru (Whitefield, Indiranagar, Koramangala, Panathur)
  - Mumbai (Bandra-Kurla Complex, Andheri East)
  - Delhi-NCR (Gurugram Cyber City, South Delhi)
  - Hyderabad (Madhapur Financial District)
  - Pune (Hinjewadi IT Corridor, Shivajinagar)
  - Chennai (OMR Corridor, Medavakkam)
- **Financial Bounds:**
  - Property Declared Agreement Value: ₹50 Lakhs to ₹10 Crores.
  - Loan Requested: Up to 80% LTV.
  - Borrower CIBIL Score: $\ge 700$.
- **Statutory Requirements:**
  - Mandatory RERA project registration.
  - Approved municipal building sanction plan.
  - Clear 30-year non-encumbrance certificate.

---

## 5. Institution-Specific Valuation Policy Configuration

Using the multi-tenant policy engine introduced in Phase 5B ([`backend/app/models/institution.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/models/institution.py)), the participating pilot institution is configured with customized risk parameters:

```json
{
  "institution_code": "HFC_PILOT_ALPHA",
  "institution_name": "Alpha Housing Finance Corporation Ltd",
  "policy_config": {
    "max_ltv_percentage": 75.0,
    "min_cibil_score": 720,
    "distress_discount_pct": 17.5,
    "underwriter_haircut_limit_pct": 25.0,
    "mandatory_title_chain_years": 30,
    "require_rera_registration": true,
    "high_value_case_threshold_inr": 30000000,
    "approval_hierarchy": [
      {"tier": 1, "role": "CREDIT_UNDERWRITER", "max_amount": 10000000},
      {"tier": 2, "role": "SENIOR_UNDERWRITER", "max_amount": 30000000},
      {"tier": 3, "role": "CHIEF_CREDIT_OFFICER", "max_amount": 100000000}
    ]
  }
}
```

---

## 6. Pilot Metrics & Evaluation Framework

The pilot measures performance across nine institutional dimensions:
1. **Valuation Deviation:** $\frac{\text{System Gross Value} - \text{Declared Agreement Value}}{\text{Declared Agreement Value}} \times 100\%$.
2. **Median Absolute Percentage Error (MedAPE):** Median of $| \text{Valuation Deviation} |$.
3. **Case Processing Time:** End-to-end API compute latency in milliseconds vs. manual surveyor turnaround (days).
4. **Data Completeness:** % of required physical, economic, and cadastral attributes populated.
5. **Prediction Interval Coverage:** Empirical reliability of uncertainty boundaries.
6. **Override Frequency:** Percentage of cases where human underwriters modify haircuts or risk tiers.
7. **Explanation Usefulness:** Underwriter qualitative score (1 to 5) on attribution factor clarity.
8. **System Availability:** Uptime percentage of the valuation endpoint during pilot execution.
9. **Failed Valuation Rate:** Percentage of requests resulting in HTTP 5xx or unhandled exceptions.

