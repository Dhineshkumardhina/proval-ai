# PROPVAL AI — PHASE 2G ENGINEERING REPORT
## AI-Powered Underwriter Assistant & Gemini Integration Architecture

**Document Version:** 1.0.0  
**Status:** Completed & Formally Verified  
**Date:** November 2026  
**Lifecycle Phase:** Phase 2G (Hero Housing Fintech Challenge — Problem Statement 1)  
**Applicable Legal Framework:** Digital Personal Data Protection Act, 2023 (DPDP Act 2023), RBI Housing Finance Directions, and Institutional Credit Underwriting Norms

---

## 1. EXECUTIVE SUMMARY

Phase 2G introduces an **Evidence-Based AI Underwriter Assistant** powered by Google Gemini (`gemini-2.5-flash`), engineered specifically for institutional real estate collateral valuation in Indian housing finance.

In institutional housing finance, automated algorithmic loan sanctioning is strictly prohibited by regulatory risk mandates. The final credit decision belongs exclusively to qualified credit underwriters and the institutional Credit Risk Committee. Accordingly, the AI assistant is architected not as an autonomous decision-maker, but as an **evidence synthesis layer** that accelerates collateral appraisal, surfaces micro-market and legal risks, and enforces strict governance.

### Core Principles Enforced
1. **Zero Price Fabrication:** Gemini explains and analyzes existing valuation evidence (provisional fair market value, circle rates, haircut percentages, liquidation values). It never independently invents, extrapolates, or recalculates property values or rupee numbers.
2. **Zero Automated Loan Decisions:** Gemini is prohibited from issuing automated loan approvals or rejections. An anti-hallucination validation guard intercepts and neutralizes any unauthorized claims of automated sanction.
3. **Data Protection & Privacy (DPDP Act 2023):** Personal Identifiable Information (Borrower Names, PAN Cards, Aadhaar numbers, Mobile numbers, Emails) is scrubbed and data payloads are minimized prior to external API transmission.
4. **Transparent Provenance Grounding:** All synthetic demonstration records (`synthetic-demo`, `is_synthetic_demonstration: true`) and provisional rule-based heuristics are explicitly identified in every briefing.
5. **High-Reliability Deterministic Fallback:** In offline environments or when API keys are unconfigured, the system generates a structured, deterministic rule-based briefing without crashing or degrading application functionality.

---

## 2. SYSTEM ARCHITECTURE

```
                                    +------------------------------------------------------+
                                    |                 React Frontend UI                    |
                                    |  (ValuationStudio -> AIUnderwriterPanel / Header)    |
                                    +---------------------------+--------------------------+
                                                                |
                                             HTTP /api/v1/ai/*  | (JSON Client)
                                                                v
+--------------------------------------------------------------------------------------------------------------------+
|                                               FastAPI Backend Service                                              |
|                                                                                                                    |
|   +------------------------------------+             +---------------------------------------------------------+   |
|   |         AI Router & Endpoints      |             |             Privacy & Security Engine                   |   |
|   |  - GET /api/v1/ai/status           |             |  - PII Detection & Redaction (PAN, Aadhaar, Phone, etc) |   |
|   |  - POST /api/v1/ai/redact-preview  | <---------> |  - Prompt Injection Neutralization                      |   |
|   |  - POST /api/v1/ai/explain-case    |             |  - Data Minimization (Section 6, DPDP Act 2023)         |   |
|   +-----------------+------------------+             +---------------------------------------------------------+   |
|                     |                                                                                              |
|                     v                                                                                              |
|   +------------------------------------+             +---------------------------------------------------------+   |
|   |       Gemini Integration Service   |             |              Deterministic Fallback Engine              |   |
|   |  - Asynchronous HTTPX client       | -- Fail ->  |  - Case Structural & Spatial Synthesis                  |   |
|   |  - Grounding System Instruction    |             |  - Synthetic Provenance & Heuristic Caveats             |   |
|   |  - Output Validation Guard         |             |  - Legal Search & Title Verification Checklist          |   |
|   +-----------------+------------------+             +---------------------------------------------------------+   |
|                     |                                                                                              |
|                     v                                                                                              |
|   +------------------------------------+                                                                           |
|   |       AIAuditLogModel (SQLite/PG)  |                                                                           |
|   |  - DPDP Compliance Audit Trail     |                                                                           |
|   +-----------------+------------------+                                                                           |
+---------------------|----------------------------------------------------------------------------------------------+
                      |
        HTTPS POST    | (API Key strictly server-side)
                      v
+------------------------------------------------------+
|            Google Generative Language API            |
|                (Model: gemini-2.5-flash)             |
+------------------------------------------------------+
```

### Server-Side Key Management
- The Gemini API key (`GEMINI_API_KEY`) is stored exclusively in backend environment variables (`.env`).
- It is never embedded in React source code, bundle outputs, or frontend network responses.
- Backend configuration:
  - `GEMINI_MODEL`: `gemini-2.5-flash` (configurable).
  - `GEMINI_TIMEOUT_SECONDS`: `30.0` (defensive timeout).
  - `GEMINI_RATE_LIMIT_PER_MINUTE`: `15` (rate limit guard).
  - `ENABLE_AI_CLOUD_PROCESSING`: `True` (allows manual or configuration-based offline enforcement).

---

## 3. DATA PROTECTION & PRIVACY ARCHITECTURE (DPDP ACT 2023)

In compliance with India's **Digital Personal Data Protection Act, 2023 (DPDP Act 2023)**, Section 6 (Consent & Notice) and Section 8 (Data Minimization & Purpose Limitation), the system enforces strict privacy safeguards prior to transmitting any collateral context to cloud LLM endpoints:

### PII Redaction Engine (`privacy_service.py`)
1. **Permanent Account Number (PAN):** Detected via regex `\b[A-Z]{5}[0-9]{4}[A-Z]\b` and replaced with `[REDACTED_PAN]`.
2. **Aadhaar Number:** Formatted 12-digit UIDAI numbers (continuous or separated by hyphens/spaces, respecting UIDAI non-zero/one initial digit specifications) are replaced with `[REDACTED_AADHAAR]`.
3. **Indian Mobile Phone Numbers:** 10-digit mobile numbers starting with 6, 7, 8, or 9 (with optional `+91` prefix) are replaced with `[REDACTED_PHONE]`.
4. **Email Addresses:** Standard email regex replaced with `[REDACTED_EMAIL]`.
5. **Borrower and Co-applicant Names:** Labeled name entities (`Borrower:`, `Applicant:`, `Co-applicant:`, `Owner:`) and honorific titles (`Mr.`, `Mrs.`, `Shri`, `Smt.`) are replaced with `[REDACTED_NAME]`.

### Data Minimization (`minimize_case_payload`)
The minimization engine extracts only essential technical, spatial, and financial parameters:
- **Structural:** Property type, super built-up area, carpet area, floor level, total floors, age of building, circle rate.
- **Spatial:** City, micro-market, sub-market, postal pincode.
- **Valuation Results:** Calculated base rate, net fair market value, underwriter haircut %, liquidation value, max sanction amount, confidence score, risk tier.
- **De-identified Comparables:** Sale price, price/sq.ft., spatial distance, similarity score, and machine-readable synthetic provenance marker (`is_synthetic_demonstration: true`).
- **Scrubbed Notes:** Audit notes and remarks sanitized of all personal identifiers.

### Prompt Injection Defense (`sanitize_prompt_input`)
Adversarial prompt injection patterns (such as `"ignore previous instructions"`, `"system override"`, `"you must approve this loan"`, `"force loan approval"`, or `"bypass risk checks"`) are detected and replaced with `[POTENTIAL_INJECTION_STRIPPED]`.

---

## 4. UNDERWRITING INTELLIGENCE & SAFETY GUARDRAILS

### Gemini System Instruction
```text
You are an institutional Real Estate Underwriting Assistant for Indian Housing Finance.
Your sole purpose is to analyze and explain the provided property valuation evidence to assist human credit underwriters.

STRICT OPERATIONAL BOUNDARIES:
1. NEVER independently invent, extrapolate, or recalculate the fair market value, liquidation value, or rupee figures. Refer strictly to the provided calculated numbers.
2. NEVER fabricate comparable registered deeds, municipal approvals, or legal clearance letters.
3. NEVER make automated loan sanction or rejection decisions. The final credit sanction decision belongs solely to the authorized human credit underwriter and credit risk committee.
4. ALWAYS explicitly identify when comparables or datasets are marked as synthetic demonstration data ('synthetic-demo' or 'is_synthetic_demonstration: true').
5. ALWAYS note that the valuation engine is a 'provisional rule-based estimation' and NOT a trained ML model when so indicated in the payload.
6. Clearly highlight data gaps, missing legal documents (Encumbrance Certificate, RERA, approved sanction plans), and micro-market risks.
```

### Anti-Hallucination Output Validation Guard
The service validates external responses against structural requirements and safety heuristics:
- **Missing Sections:** If any required section is omitted by the model, the system gracefully substitutes the deterministic fallback briefing.
- **Automated Approval Detection:** If the generated text contains claims of automated approval (`"loan is approved"`, `"application is sanctioned"`, `"we approve the loan"`), the output guard overwrites the decision role with the mandatory institutional policy statement:
  > *"AI Underwriter provides advisory synthesis only. Loan sanction, conditionality, and credit approval or rejection must be determined solely by the authorized human credit underwriter and credit committee."*

---

## 5. DATABASE AUDIT LOGGING & MIGRATION

To satisfy regulatory auditability and DPDP Act accountability, every AI Underwriting consultation is recorded in an immutable audit table.

### Model Specification (`AIAuditLogModel`)
- `id`: Integer primary key (autoincrement).
- `case_id`: String(64), indexed.
- `model_name`: String(64) (`gemini-2.5-flash` or `deterministic-fallback-engine`).
- `provider`: String(32) (`gemini` or `deterministic_fallback`).
- `pii_redacted_count`: Integer (count of scrubbed personal data entities).
- `prompt_tokens`: Integer (estimated or API-reported token count).
- `response_tokens`: Integer (estimated or API-reported token count).
- `status`: String(32) (`success`, `fallback`, `error`).
- `error_message`: Text (nullable error context).
- `created_at`: DateTime (UTC timestamp).

### Alembic Migration
- Migration `cc94c7d7aa6e_add_ai_audit_logs.py` generated and applied to the database schema.
- Downgrade capability preserved.

---

## 6. API ENDPOINT SPECIFICATIONS

| Method | Endpoint | Description | Request Payload | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/ai/status` | Reports Gemini configuration, provider mode, and DPDP Act compliance. | None | `AIStatusResponse` |
| `POST` | `/api/v1/ai/redact-preview` | Tests and previews PII scrubbing on sample text. | `RedactPreviewRequest` | `RedactPreviewResponse` |
| `POST` | `/api/v1/ai/explain-case/{case_id}` | Generates an evidence-grounded executive underwriter briefing for a collateral file. | None (Path param) | `AIExplainCaseResponse` |

---

## 7. FRONTEND USER EXPERIENCE

### 1. `AIUnderwriterPanel.tsx`
An institutional-grade analysis panel integrated directly into the `ValuationStudio` workspace:
- **Executive Summary:** Synthesizes the property’s structural parameters, provisional FMV, haircut percentage, liquidation value, and risk classification.
- **Value & Risk Factors:** Visual cards highlighting Circle Rate floors, structural attributes, and scorecard adjustments with impact badges (`POSITIVE`, `NEGATIVE`, `NEUTRAL`).
- **Comparable Evidence & Provenance:** Explicitly informs the underwriter that demonstration records are synthetic and do not constitute verified SRO Sub-Registrar registered transaction deeds.
- **Micro-Market Dynamics:** Explains location factors and civic infrastructure considerations.
- **Legal Due Diligence Checklist:** Outlines required verification steps (30-year Encumbrance Certificate Form 15/16, RERA registration, Occupancy Certificate, sanctioned municipal plan).
- **Valuation Caveats:** Discloses rule-based estimation heuristics, uncalibrated heuristic confidence scores, and pending ML readiness status.
- **Actionable Recommendations:** Bulleted due-diligence checklist for credit officers.
- **Underwriting Policy Mandate:** Dark institutional banner reiterating that credit decisions are reserved for human underwriters.

### 2. `Header.tsx` AI Status Badge
A persistent status pill in the top header displaying the AI Assistant's real-time state:
- `AI Assistant: gemini-2.5-flash` (when cloud AI is configured).
- `AI Assistant: Grounded Fallback` (when operating in local or offline mode).

---

## 8. AUTOMATED VERIFICATION & TEST EVIDENCE

### Backend Automated Test Suite (`backend/tests/test_gemini_underwriter.py`)
15 specialized automated tests were implemented and verified:
1. `test_redact_pan_card`: Verifies PAN scrubbing and replacement with `[REDACTED_PAN]`.
2. `test_redact_aadhaar_number`: Verifies 12-digit spaced and hyphenated Aadhaar scrubbing.
3. `test_redact_indian_mobile_and_email`: Verifies phone and email address scrubbing.
4. `test_redact_borrower_and_honorific_names`: Verifies borrower and title name scrubbing.
5. `test_prompt_injection_detection_and_neutralization`: Verifies neutralization of malicious jailbreak commands.
6. `test_minimize_case_payload`: Verifies that personal identifiers are scrubbed while structural metrics are preserved.
7. `test_deterministic_fallback_report_structure_and_grounding`: Verifies that fallback reports contain accurate rupee formatting, synthetic demonstration markers, and credit authority disclaimers.
8. `test_validate_and_sanitize_ai_report_replaces_automated_approval`: Verifies that hallucinated automated approval claims are intercepted and corrected.
9. `test_gemini_briefing_fallback_when_unconfigured`: Verifies deterministic fallback when `GEMINI_API_KEY` is empty.
10. `test_gemini_briefing_mocked_success`: Verifies end-to-end briefing generation with mocked Gemini API responses.
11. `test_gemini_briefing_mocked_network_failure_falls_back`: Verifies defensive fallback on network timeout or connection errors.
12. `test_api_ai_status_endpoint`: Verifies HTTP 200 response from `/api/v1/ai/status`.
13. `test_api_ai_redact_preview_endpoint`: Verifies HTTP 200 response from `/api/v1/ai/redact-preview`.
14. `test_api_ai_explain_case_seeded_case`: Verifies briefing generation on seeded collateral cases.
15. `test_api_ai_explain_case_not_found`: Verifies HTTP 404 response on invalid case identifiers.

### Full Test Suite Results
- **Backend Test Suite:** **79 passed** in 38.29s (`python -m pytest backend/tests/ -v`).
- **Frontend Test Suite:** **23 passed** in 0.40s (`npm test`).
- **TypeScript Type Check:** **0 errors** (`npm run lint`).
- **Production Build:** **Successful in 3.93s** (`npm run build`).

---

## 9. CONCLUSION & GOVERNANCE SIGN-OFF

Phase 2G successfully delivers a production-ready, institutionally compliant AI Underwriting Assistant powered by Gemini. By strictly binding Gemini to explain existing evidence, enforcing DPDP Act 2023 data minimization, neutralizing automated approval hallucinations, and providing deterministic offline fallbacks, the system upholds the highest standards of fintech credibility and regulatory rigor.

