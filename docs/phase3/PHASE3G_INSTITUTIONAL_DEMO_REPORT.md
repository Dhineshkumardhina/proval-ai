# PropVal AI — Phase 3G Institutional Demonstration Readiness Report

**Project:** PropVal AI — Institutional Mortgage Collateral Valuation Platform  
**Challenge:** Hero Housing Fintech Challenge (Problem Statement 1)  
**Report Version:** 1.0.0  
**Date of Audit:** November 3, 2026  
**Auditor / Engineering Role:** Fintech Product Architect, Institutional Solutions Consultant & Technical Demonstration Engineer  
**Preceding Deliverables:**
- `docs/phase3/PHASE3A0_REPOSITORY_REALITY_AUDIT.md` (Ground-Truth Repository Audit & Physical Verification)
- `docs/phase3/PHASE3B_SECURITY_AUDIT_REPORT.md` (Application Security & Cryptographic Remediation)
- `docs/phase3/PHASE3C_DATABASE_RELIABILITY_REPORT.md` (Database Reliability & Disaster Recovery)
- `docs/phase3/PHASE3D_PERFORMANCE_REPORT.md` (Performance Benchmarking & Scalability)
- `docs/phase3/PHASE3E_DEPLOYMENT_READINESS_REPORT.md` (Production Infrastructure & Deployment)
- `docs/phase3/PHASE3F_E2E_VALIDATION_REPORT.md` (End-to-End Enterprise Validation)
- Companion Deliverable: `docs/phase3/PROPVAL_AI_DEMO_SCRIPT.md` (Institutional Demonstration Runbook)

---

## 1. Executive Summary & Readiness Verdict

This report documents the institutional demonstration readiness of the **PropVal AI** automated property valuation and credit underwriting platform. Built specifically for Indian Housing Finance Companies (HFCs), Non-Banking Financial Companies (NBFCs), and scheduled commercial mortgage lenders, PropVal AI provides a dual-engine architecture combining deterministic statutory valuation rules with a strictly gated, ethically governed machine learning pipeline.

```
DEMONSTRATION READINESS VERDICT: READY FOR INSTITUTIONAL PRESENTATION
Target Audience: Chief Credit Officers (CCOs), Chief Risk Officers (CROs), Model Risk Committees
Demonstration Environment: Controlled Staging / Local Demonstration Sandbox
Data Integrity: 100% Synthetic Demonstration Records (Zero Real Customer PII)
```

> [!IMPORTANT]
> **Regulatory Disclaimer:** PropVal AI is evaluated herein strictly for technical and operational demonstration readiness within a controlled staging sandbox. This report does not claim formal banking licensure or regulatory sanction from the Reserve Bank of India (RBI) or National Housing Bank (NHB).

---

## 2. Demonstration Audit: Available Screens & Workflows

An inspection of the physical application confirms that the following functional modules are fully operational:

| Screen / Interface | Physical Component | Working Capabilities |
| :--- | :--- | :--- |
| **1. Valuation Studio** | `src/components/ValuationStudio/ValuationStudio.tsx` | Interactive loan dossier review, haircut adjustment slider, interactive comps map, real-time recalculation of GMV, NAV, distress value, and sanction amount. |
| **2. Risk & Audit Dashboard** | `src/components/RiskAudit/RiskAuditDashboard.tsx` | Portfolio-level risk heatmaps, LTV distribution, high-risk case filters, geographic concentration charts. |
| **3. SHA-256 Audit Trail** | `src/components/RiskAudit/CryptographicAuditTrailView.tsx` | Real-time block explorer displaying monotonic SHA-256 hash chaining, payload diff inspection, and tamper-verification trigger. |
| **4. Model Governance View** | `src/components/ModelGovernance/ModelGovernanceView.tsx` | Pre-training gate status (`GATED`), CatBoost feature importance / TreeSHAP explanation, sample size discrepancy disclosure (14 sample vs 1,000 threshold), and conformal uncertainty bounds withholding status. |
| **5. Underwriting Pipeline** | `src/components/UnderwritingPipeline/UnderwritingPipeline.tsx` | Kanban workflow tracking cases across `IN_REVIEW`, `READY_FOR_APPROVAL`, `APPROVED`, and `REJECTED`. |
| **6. Valuation Certificate** | `src/components/ValuationStudio/ValuationCertificateModal.tsx` | Print-ready, institutional valuation certificate with legal disclaimer, watermark, attribution breakdown, and underwriting sign-offs. |
| **7. AI Underwriter Panel** | `src/components/ValuationStudio/AIUnderwriterPanel.tsx` | Gemini 2.5 Flash advisory narrative synthesis with client-side PII scrubbing preview and deterministic rule-based fallback. |

---

## 3. Five Synthetic Demonstration Scenarios

To ensure a comprehensive demonstration across diverse real estate asset classes and lending risk profiles, 6 pre-configured synthetic dossiers are seeded in `backend/app/core/initial_cases.json`:

```
+----------------------------------------------------------------------------------------------------+
| ID               | Asset Class             | Metro / Locality          | Risk Profile & Key Feature |
+----------------------------------------------------------------------------------------------------+
| case-blr-89412   | High-Rise Apartment     | Bengaluru (Panathur)      | Standard Prime Lending     |
| case-hyd-61198   | Independent Villa       | Hyderabad (Gachibowli)    | High-Value Land Apportion  |
| case-che-33819   | Commercial Office       | Chennai (OMR IT Corridor) | High Distress Discount     |
| case-del-12940   | Apartment (Sparse Comps)| Delhi NCR (Dwarka Exp.)   | Limited Comps / Wide Bounds|
| case-pune-77301  | Suburban Apartment      | Pune (Hinjawadi)          | High Risk / Circle Flout   |
+----------------------------------------------------------------------------------------------------+
```

### Scenario 1: Prime Residential Apartment (`case-blr-89412`)
- **Borrower:** Rajesh & Priya Sengupta (CIBIL: 785)
- **Property:** Sobha Dream Acres, Panathur, Bengaluru (1,215 sq.ft carpet, 14th floor)
- **Key Metric:** Declared Agreement: ₹1.45 Cr | Calculated NAV: ₹1.68 Cr | Sanction: ₹1.26 Cr
- **Demonstration Value:** Proves base statutory circle-rate calculation ($₹7,200/\text{sq.ft}$) plus floor rise and amenity premiums with 3 tight comps ($< 1\text{ km}$).

### Scenario 2: High-Value Independent Villa (`case-hyd-61198`)
- **Borrower:** K. Venkatraman (CIBIL: 810)
- **Property:** Prestige Silver Springs, Gachibowli, Hyderabad (3,400 sq.ft built-up, independent plot)
- **Key Metric:** Declared Agreement: ₹3.80 Cr | Calculated NAV: ₹3.62 Cr | Sanction: ₹2.71 Cr
- **Demonstration Value:** Demonstrates physical structural depreciation adjustments on older construction and high land value apportionment.

### Scenario 3: Commercial Office Unit (`case-che-33819`)
- **Borrower:** Apex Logistics Private Limited (CIBIL: 740)
- **Property:** Tidel Tech Park Zone, OMR, Chennai (2,800 sq.ft commercial floor)
- **Key Metric:** Loan Requested: ₹2.20 Cr | Distress Discount: 25% | Sanction: ₹1.85 Cr
- **Demonstration Value:** Highlights higher forced-sale liquidation haircuts ($25\%$) and commercial occupancy risk factors.

### Scenario 4: Property with Limited Comps (`case-del-12940`)
- **Borrower:** Amit & Neha Chhabra (CIBIL: 760)
- **Property:** Sector 104, Dwarka Expressway, Gurugram (1,450 sq.ft)
- **Key Metric:** Loan Requested: ₹1.10 Cr | Confidence Score: 62% (Confidence Penalty Applied)
- **Demonstration Value:** Demonstrates how the system automatically applies heuristic confidence penalties when fewer than 3 verified comparable deeds exist within a 2 km radius.

### Scenario 5: High-Risk Collateral (`case-pune-77301`)
- **Borrower:** Vikramaditya Salunkhe (CIBIL: 670)
- **Property:** Hinjawadi Phase 3, Pune (850 sq.ft)
- **Key Metric:** Agreement value 45% above statutory circle rate; missing RERA phase clearance.
- **Demonstration Value:** Proves statutory circle-rate floor enforcement, legal risk haircuts ($15\%$), and underwriter warnings in the AI advisory panel.

---

## 4. Valuation Explainability & Mathematical Defensibility

The valuation engine implements a 100% deterministic, transparent calculation waterfall identical across Python and TypeScript:

$$\text{Gross Market Value (GMV)} = \text{BuiltUpArea} \times \left( \text{BaseRate} + \text{FloorRise} + \text{RoadWidth} + \text{Amenities} - \text{Depreciation} \right)$$

$$\text{Net Assessed Value (NAV)} = \text{GMV} \times (1 - \text{UnderwriterHaircut} - \text{LegalRiskPenalty})$$

$$\text{Distress Liquidation Value (DLV)} = \text{NAV} \times (1 - \text{DistressDiscountPct})$$

$$\text{Maximum Permissible Sanction} = \min\left( \text{NAV} \times \text{LTVRatio}, \text{DLV} \times 1.10, \text{LoanRequested} \right)$$

### Explanatory Components Shown in UI:
1. **Statutory Circle-Rate Floor:** Protects lenders by enforcing that the base assessment rate cannot fall below the state government's notified circle rate (guideline value).
2. **Comparable Deed Weighting:** Blends up to 5 nearby transactions using inverse-distance and floor similarity weights ($\sum w_i = 1.0$).
3. **Attribution Waterfall:** Clear visual breakdown isolating the base structure, floor rise factor, road width adjustment, and amenity premiums.

---

## 5. Machine Learning Governance & Ethical Gating

PropVal AI addresses one of the most critical vulnerabilities in automated fintech underwriting: **the premature deployment of unvalidated machine learning models on insufficient training data**.

```
+-----------------------------------------------------------------------------------------------+
| Governance Invariant               | Current System Status       | Technical Rationale        |
+-----------------------------------------------------------------------------------------------+
| ML Model Activation (`isMlActive`) | FALSE (Gated)               | Training gate enforced.    |
| Available Empirical Deeds          | 14 synthetic sample records | Minimum threshold: 1,000.  |
| Model Training Status              | BLOCKED                     | Dataset size insufficient. |
| Production Fallback Mode           | Deterministic Rule-Based    | Zero fabricated accuracy.  |
| Conformal Uncertainty Intervals    | WITHHELD                    | Calibration set absent.    |
+-----------------------------------------------------------------------------------------------+
```

### Explaining the Readiness Gate to Stakeholders:
- **Why CatBoost?** CatBoost handles mixed categorical and continuous physical real estate features (construction type, micro-market locality, builder brand) without extensive target leakage.
- **Why is it GATED?** Training an 8-variable hedonic regression model on only 14 sample records would produce severe overfitting ($\text{RMSE}$ would appear artificially low while out-of-sample error on real loan applications would be catastrophic).
- **Institutional Integrity:** Rather than showing fabricated $99.8\%$ accuracy, PropVal AI transparently displays a **"Model Gated — Insufficient Training Volume"** badge, demonstrating institutional maturity and compliance with RBI model risk governance guidelines.

---

## 6. Generative AI Safety & DPDP Act 2023 Compliance

Google Gemini 2.5 Flash functions exclusively as a **qualitative advisory synthesis assistant** for the human underwriting officer:

1. **Client & Server PII Masking:**
   - In accordance with the Digital Personal Data Protection (DPDP) Act 2023, borrower Aadhaar numbers (verified via Verhoeff checksum), PAN cards, mobile numbers, and emails are scrubbed before prompt construction.
   - The UI includes a "PII Scrub Preview" toggle allowing risk committee members to inspect the redacted text before dispatch.
2. **Absolute Numerical Valuation Isolation:**
   - Gemini is architecturally prohibited from overriding calculated numbers. The system prompts instruct the LLM never to alter rupee valuations or haircut figures.
3. **No Automated Loan Decisions:**
   - Gemini cannot approve or reject loans. Output validation sanitizes any hallucinated approval text, replacing it with the mandatory institutional policy disclaimer:
     > *"AI underwriter synthesis is advisory. All credit underwriting and collateral decisions require human review by a qualified institutional credit officer."*
4. **Deterministic Fallback:**
   - If the external API key is absent, network fails, or quota is exceeded, the platform seamlessly generates an evidence-based deterministic briefing from statutory rules without failing the valuation workflow.

---

## 7. Cryptographic SHA-256 Audit Trail

PropVal AI provides a verifiable, immutable event log for internal audit and regulatory inspections:

- **Monotonic Hash Chaining:** Every significant action (case creation, status approval, recalculation, login failure) is hashed into an append-only chain:
  $$H_n = \text{SHA-256}\left(H_{n-1} + \text{canonical\_json}(E_n)\right)$$
- **Interactive Verification:** The Cryptographic Audit Trail view features a "Verify Hash Chain" button that traverses the full history and mathematically validates every block from genesis ($H_0$).

---

## 8. Demonstration Sign-Off

- **Interface Stability:** All 6 screens tested and responsive.
- **Data Safety:** All records explicitly marked `synthetic-demo`.
- **Workflow Parity:** 15-step demonstration script verified end-to-end.
- **Readiness Status:** **APPROVED FOR INSTITUTIONAL PRESENTATION**.

