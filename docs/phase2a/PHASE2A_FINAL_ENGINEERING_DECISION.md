# Phase 2A: Final Engineering Decision — PropVal AI

**Project:** PropVal AI (Hero Housing Fintech Challenge)  
**Document:** Final Engineering Decision, Data Acquisition Strategy & Architectural Roadmap  
**Phase:** Phase 2A Synthesis & Sign-Off  
**Date:** November 2026  
**Author:** Principal Software Architect, Senior Python Engineer, ML Engineer & Fintech Technical Lead  
**Operating System:** Windows  
**Shell Environment:** Windows PowerShell  
**Target Path:** `docs/phase2a/PHASE2A_FINAL_ENGINEERING_DECISION.md`  

---

## 1. Executive Summary

This document represents the final engineering review and synthesis of the four Phase 2A technical reports:
1. [`docs/phase2a/PHASE2A_DATA_SOURCE_FEASIBILITY_REPORT.md`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docs/phase2a/PHASE2A_DATA_SOURCE_FEASIBILITY_REPORT.md)
2. [`docs/phase2a/PHASE2A_BACKEND_ARCHITECTURE_REPORT.md`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docs/phase2a/PHASE2A_BACKEND_ARCHITECTURE_REPORT.md)
3. [`docs/phase2a/PHASE2A_SECURITY_ARCHITECTURE_REPORT.md`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docs/phase2a/PHASE2A_SECURITY_ARCHITECTURE_REPORT.md)
4. [`docs/phase2a/PHASE2A_ML_DATA_REQUIREMENTS.md`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docs/phase2a/PHASE2A_ML_DATA_REQUIREMENTS.md)

### Core Synthesis & Strategic Verdict: **CONDITIONAL GO**
* **Backend Architecture (GO):** Approved to proceed with Phase 2B. Deploy a **Python FastAPI Modular Monolith** with **PostgreSQL 16 + PostGIS**. This backend will serve as a Backend-For-Frontend (BFF), centralize credential management, implement spatial comparable indexing, and execute server-side valuation math.
* **Frontend Integration (GO):** Approved to migrate the React 19 frontend to communicate with the FastAPI backend via an asynchronous hook (`useValuationEngine`) with a **mandatory local offline fallback** to preserve 100% of existing UI capabilities.
* **Machine Learning Training (CONDITIONAL PAUSE / GATED):** We **do not** currently possess legitimate micro-transaction deed data to train a genuine machine learning model. CatBoost training (Phase 2D) is gated until an empirical transaction dataset is ingested. In the interim, the system will operate transparently as a **Provisional Rule-Based Valuation Engine** augmented with published statutory guideline rates.
* **Security Controls (MANDATORY GATE):** Private API keys (Gemini, database) must never enter client-side bundles. PII redaction must be enforced before any future LLM prompt dispatch.

---

## 2. Verified Repository Findings vs. Assumptions

### 2.1 Verified Findings (Confirmed by Direct Inspection)
1. **Frontend Architecture:** React 19.0.1 Single Page Application using Vite 8.3 and Tailwind CSS 4. State is managed transiently via React `useState` at the root [`App.tsx`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/App.tsx) component [`VERIFIED: src/main.tsx`, `src/App.tsx`].
2. **Deterministic Valuation Engine:** The valuation logic in [`src/utils/valuationEngine.ts`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/utils/valuationEngine.ts) is 100% deterministic arithmetic implementing linear hedonic scorecard additions. There are zero machine learning models, weights, or regression artifacts [`VERIFIED: src/utils/valuationEngine.ts:118–144`].
3. **Uncalibrated Confidence:** The confidence score (`confidenceScorePct`) is computed deterministically via rule deductions (`95.5 - circleRatePenalty - legalPenalty`). It measures rule consistency, not calibrated predictive uncertainty [`VERIFIED: src/utils/valuationEngine.ts:187–198`].
4. **Synthetic Demonstration Data:** All 6 collateral cases and comparables carry the machine-readable synthetic marker (`dataSource: 'synthetic-demo'`) implemented in Phase 1 [`VERIFIED: src/data/mockValuationData.ts`].
5. **No Active Backend or API Integrations:** `@google/genai` is present in `package.json`, but there are **zero API call sites** in `src/`. No backend server exists [`VERIFIED: package.json`, code search].
6. **No Leaked Secrets:** Scanned repository for API keys. `.env.example` contains only `GEMINI_API_KEY="MY_GEMINI_API_KEY"`. `.gitignore` correctly blocks `.env*` files [`VERIFIED: .env.example`, `.gitignore`].
7. **Extraneous Dependencies:** `express`, `@types/express`, `dotenv`, and `motion` are installed in `package.json` but completely unimported [`VERIFIED: package.json`].
8. **Mathematical Regression Baseline:** 12/12 unit tests pass cleanly in Node.js test runner via `tsx --test` [`VERIFIED: src/utils/valuationEngine.test.ts`].

### 2.2 Unresolved Assumptions & External Dependencies
1. **Public SRO Registry APIs:** While state portals (Kaveri 2.0, IGR Maharashtra, TNREGINET) possess registered deed records, they do **not** provide open public APIs or bulk exports. Access is query-based, CAPTCHA-protected, and scraping is legally prohibited [`VERIFIED` portal findings; automated access remains an unviable `ASSUMPTION`].
2. **Commercial Data Licensing:** Enterprise aggregators (Propstack, Zapkey, Liases Foras) possess structured transaction databases, but access is gated by private B2B contracts and licensing costs [`UNRESOLVED: Requires sponsor commercial decision`].
3. **Challenge Data Sandbox:** Whether the Hero Housing Fintech Challenge organizers will supply an anonymized loan appraisal dataset for model benchmarking is currently unknown [`UNRESOLVED: Requires sponsor confirmation`].

---

## 3. Data Source Decision

### 3.1 Evaluation of Candidate Data Sources

```
+--------------------------------------------------------------------------------------------------------------------+
| DATA SOURCE STATUS & FEASIBILITY MATRIX                                                                            |
|                                                                                                                    |
| 1. State Registration Portals (Kaveri 2.0, Maharashtra IGR, TNREGINET)                                             |
|    * Micro-Transaction Data: YES.                                                                                  |
|    * Programmatic Access: NO (No public API; CAPTCHA & WAF enforced; bulk download absent).                        |
|    * Legal & Compliance: Scraping violates portal Terms of Use and IT Act 2000.                                  |
|    * Decision: REJECTED FOR DIRECT PROGRAMMATIC SCRAPING [REQUIRES LEGAL REVIEW].                                 |
|                                                                                                                    |
| 2. Open Government Data Platform (data.gov.in)                                                                     |
|    * Micro-Transaction Data: NO (Zero deed-level property records hosted).                                         |
|    * Decision: REJECTED (Cannot support micro-market valuation).                                                   |
|                                                                                                                    |
| 3. National Housing Bank RESIDEX & RBI DBIE (HPI)                                                                  |
|    * Micro-Transaction Data: NO (Aggregated city/zone index points only).                                          |
|    * Decision: ADOPTED AS MACRO INFLATION / BENCHMARK SIGNAL ONLY.                                                |
|                                                                                                                    |
| 4. Commercial Aggregators (Propstack, Zapkey, Liases Foras)                                                        |
|    * Micro-Transaction Data: YES (Standardized, geocoded, cleaned registry deeds).                                 |
|    * Programmatic Access: YES (Enterprise REST APIs).                                                              |
|    * Legal & Compliance: Commercial license required; supports PII anonymization.                                 |
|    * Decision: RECOMMENDED FOR PRODUCTION / REJECTED FOR IMMEDIATE HACKATHON WITHOUT BUDGET.                      |
+--------------------------------------------------------------------------------------------------------------------+
```

### 3.2 Legitimate Data Sufficiency Assessment
* **Question:** Do we currently have sufficient legitimate data to train and evaluate a genuine valuation machine learning model?
* **Definitive Answer:** **NO.** The repository contains only 6 synthetic cases. Training an ML model (e.g. CatBoost) on 6 synthetic cases would produce a non-generalizable, overfitted toy that violates institutional fintech credibility standards.

### 3.3 Recommended Data Acquisition Strategy
Adopt a pragmatic **Two-Track Data Acquisition Roadmap**:
1. **Track 1 (Immediate MVP & Hackathon Scope — Level 0 & Level 1):**
   * **Guideline Rate Matrix Ingestion:** Ingest published statutory Circle Rate / Ready Reckoner gazette tables across target metro localities (Bengaluru, Mumbai, Pune, Delhi-NCR, Hyderabad, Chennai).
   * **Macro Trend Indexation:** Ingest official quarterly city index series from NHB RESIDEX and RBI DBIE to provide macroeconomic time-series scaling.
   * **Standardized Synthetic Demonstration Corpus:** Expand the Phase 1 synthetic dataset to 50–100 realistic, edge-case-rich collateral files clearly marked with `dataSource: 'synthetic-demo'` to comprehensively evaluate all underwriting workflows, spatial GIS canvases, and audit logging.
2. **Track 2 (Institutional Production Scope — Level 2 & Level 3):**
   * Formal sponsor/lender outreach for an anonymized sample of 1,000–5,000 historical collateral valuations, or commercial evaluation access to Zapkey/Propstack.

---

## 4. Backend Technology Decision

### 4.1 Architecture Evaluation: Modular Monolith vs. Microservices
* **Evaluation:** Microservices introduce distributed tracing overhead, network serialization latency, multi-container orchestration failure points, and data consistency hazards across audit ledgers.
* **Decision:** **Adopt a Python FastAPI Modular Monolith.**
  * Single deployable unit with sub-millisecond in-process function calls between service layers.
  * Shared database connection pool and strict ACID transaction boundaries.
  * Native Python ecosystem enabling seamless transition to CatBoost, Scikit-learn, Shap, and Pydantic.

### 4.2 Frontend-Backend Communication & Working Functionality Preservation
* **Protocol:** Standard RESTful JSON over HTTPS.
* **Communication Interface:** A dedicated client service (`src/services/apiClient.ts`) paired with a custom React hook `useValuationEngine`:
  * Asynchronously invokes `POST /api/v1/valuation/calculate`.
  * If the backend is running, the UI displays real-time backend calculations with badge `Engine: FastAPI Service (v0.2.0)`.
  * **Zero Breaking Changes / Mandatory Fallback:** If the backend is unreachable or returns a network error, the hook automatically and transparently executes the existing local TypeScript `calculateValuation` function and displays `Engine: Local Rule-Based Fallback (Offline)`.
  * All existing UI layouts ([`ValuationStudio`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/components/ValuationStudio/ValuationStudio.tsx), [`GisMapCanvas`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/components/ValuationStudio/GisMapCanvas.tsx), [`ComparablesGrid`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/components/ValuationStudio/ComparablesGrid.tsx), [`UnderwriterControls`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/components/ValuationStudio/UnderwriterControls.tsx)) are strictly preserved.

### 4.3 Database Technology
* **Primary Recommendation:** **PostgreSQL 16 + PostGIS**.
  * Essential for spatial indexing (`ST_DWithin`, `ST_Distance_Sphere`) allowing sub-5ms comparable deed retrieval.
  * Native JSONB support for document verification OCR extracts.
  * ACID row locking (`FOR UPDATE`) to prevent audit ledger sequence collisions.
* **Development Strategy:** Containerized via Docker Compose for local development; lightweight SQLite fallback with bounding-box arithmetic for environments lacking Docker.

---

## 5. Security & Cryptographic Requirements

### 5.1 Credential & Key Protection
* **Mandatory Rule:** **Zero Private Keys in Frontend Bundles.** Vite client environment variables (`VITE_*`) must never hold Google Gemini API keys, database credentials, or JWT signing secrets.
* **BFF Pattern:** All external API communications (Google Gemini, database) are brokered exclusively by the FastAPI server reading from system environment variables via `pydantic-settings`.

### 5.2 Application Security Controls
1. **Input Validation:** 100% of incoming payloads validated via Pydantic v2 schemas with defensive numerical bounds (e.g. carpet area $50 \le x \le 50,000$ sq ft; LTV ratio cap $\le 80\%$).
2. **Authentication & RBAC:** Stateless JWT tokens implementing institutional role-based access control (`CREDIT_UNDERWRITER`, `SENIOR_UNDERWRITER`, `RISK_COMMITTEE_MEMBER`, `COMPLIANCE_AUDITOR`).
3. **CORS Policy:** Strict origin whitelisting (`http://localhost:3000` for development; production frontend domain). Wildcard origins (`"*"`) are strictly prohibited.
4. **Rate Limiting:** IP-based and user-based throttling via Redis/slowapi on auth and calculation endpoints.
5. **PII Redaction & DPDP Act 2023 Compliance:** Pre-LLM redaction pipeline stripping borrower names, Aadhaar/PAN references, and contact details before dispatching prompts to Google Gemini [`REQUIRES LEGAL REVIEW`].

### 5.3 Cryptographic SHA-256 Audit Chain
* **Implementation:** Append-only database table (`audit_events`) cryptographically linked via SHA-256 digests computed over RFC 8785 canonical JSON representations.
* **Mathematical Formula:**
  $$\text{CurrentHash}_n = \text{SHA256}\left(\text{PreviousHash}_{n-1} \,\|\, \text{PayloadHash}_n \,\|\, \text{TimestampISO}_n \,\|\, \text{ActorID}_n\right)$$
* **Truthful Claim Boundary:** The report and UI must state clearly that the audit chain provides **tamper-evidence** across underwriting sessions, but does **not** provide absolute immutability or regulatory accreditation without external RFC 3161 timestamp authority anchoring.

---

## 6. Machine Learning Readiness & Evaluation Standards

### 6.1 Readiness Verdict: Gated
* **Status:** The platform is **NOT READY** for live ML model deployment due to absence of an empirical transaction training corpus.
* **Phase 2D Gate:** CatBoost training is gated until a verified dataset ($\ge 1,000$ records with verified carpet areas and transaction dates) is ingested.

### 6.2 Mandatory Evaluation & Leakage Prevention Standards
When empirical data is ingested in Phase 2D:
1. **Out-of-Time (OOT) Temporal Split:** Train strictly on past quarters; evaluate on subsequent quarters to eliminate lookahead bias.
2. **Spatial Block Cross-Validation:** Partition cross-validation folds by Project/Society and Pin Code to prevent spatial autocorrelation leakage.
3. **Property Fingerprint Deduplication:** Deduplicate repeated resale records of identical units before splitting.
4. **Benchmark Hurdle:** The CatBoost model must beat two mandatory baselines:
   * *Baseline 1:* Locality Median Price per Sq Ft.
   * *Baseline 2:* Regularized Hedonic OLS (Ridge Regression).
5. **Strict Accuracy Claim Ban:** **No accuracy metrics (MAPE, $R^2$) may be rendered in the UI** until generated by a reproducible evaluation script executing on verified out-of-time registered deeds.

### 6.3 Uncertainty Quantification Architecture
* **Roadmap:**
  * *Current (Phase 1/2B):* Heuristic Rule Consistency Score (uncalibrated penalty index).
  * *Intermediate (Phase 2D):* Empirical residual standard deviation bands.
  * *Target (Phase 2E):* Locally-weighted split-conformal prediction intervals with finite-sample coverage guarantees.
* **Separation of Concepts:** The API and UI must maintain strict conceptual and visual separation between:
  1. *Data Completeness Index* (% of inputs provided vs imputed).
  2. *Evidence Coverage Score* (density and proximity of comparables).
  3. *Model Uncertainty* (ensemble prediction variance).
  4. *Prediction Interval* (calibrated lower and upper price bounds in ₹).

---

## 7. Recommended Implementation Sequence & Phase 2B Scope

```
+--------------------------------------------------------------------------------------------------------------------+
| RECOMMENDED IMPLEMENTATION SEQUENCE                                                                                |
|                                                                                                                    |
| [PHASE 2B: FastAPI Backend Skeleton, Database & Engine Migration] (IMMEDIATE NEXT STEP)                            |
|   -> Setup FastAPI application, Docker Compose for PostgreSQL + PostGIS, Alembic migrations.                       |
|   -> Port valuationEngine.ts math to Python (calculate_valuation) with 100% numerical parity tests.                |
|   -> Implement React useValuationEngine hook with automatic local fallback.                                        |
|   -> Clean up unused frontend dependencies (express, dotenv, motion).                                              |
|                                                                                                                    |
| [PHASE 2C: Ingestion Pipeline & PostGIS Spatial Comparable Engine]                                                 |
|   -> Build CSV/JSON ingestion pipeline for standardized transaction schema.                                        |
|   -> Implement PostGIS spatial radius queries (/api/v1/comparables/search) replacing static SVG percentages.       |
|                                                                                                                    |
| [PHASE 2D: CatBoost Baseline Model & Offline Benchmark] (GATED ON REAL DATA)                                       |
|   -> Implement CatBoost tabular regression pipeline with spatial/temporal CV.                                      |
|   -> Execute offline evaluation benchmark against median price baseline.                                          |
|                                                                                                                    |
| [PHASE 2E: Conformal Uncertainty Intervals & Server-Side SHA-256 Audit Chain]                                      |
|   -> Implement split-conformal calibration pipeline.                                                               |
|   -> Implement RFC 8785 canonical SHA-256 audit ledger and verification endpoint.                                  |
|                                                                                                                    |
| [PHASE 2F: BFF Gemini Explanation Service & Production Hardening]                                                  |
|   -> Connect server-side Google Gemini client with PII redaction pipeline.                                         |
|   -> Final OWASP Top 10 security audit and institutional hardening.                                                |
+--------------------------------------------------------------------------------------------------------------------+
```

### Phase 2B Entry Criteria & Definition of Done
* **Entry Criteria:**
  1. Phase 2A reports completed and signed off.
  2. Agreement on FastAPI modular monolith and PostgreSQL + PostGIS database.
  3. Strict adherence to non-breaking frontend integration (local fallback preserved).
* **Definition of Done for Phase 2B:**
  1. FastAPI server running on port 8000 with interactive Swagger docs (`/docs`).
  2. Database schema migrated via Alembic.
  3. Python `calculate_valuation` unit tests achieve 100% numerical parity with TypeScript test cases.
  4. React frontend successfully calls backend API when online, and falls back seamlessly to local engine when offline.
  5. Zero new lint, build, or type-check failures across frontend and backend.

---

## 8. Risks, Blockers & Mitigations

| Risk / Blocker | Severity | Mitigation Strategy |
| :--- | :---: | :--- |
| **No Access to Real SRO Deed Data** | HIGH | Maintain Track 1 strategy: statutory Circle Rate tables + macro NHB RESIDEX indices + transparently labeled synthetic demonstration cases. Never claim unverified accuracy. |
| **Docker / PostGIS Environment Friction** | MEDIUM | Implement dual database configuration: PostgreSQL + PostGIS for production/docker, with lightweight SQLite fallback for local test runs. |
| **Frontend-Backend Contract Drift** | LOW | Share TypeScript type definitions generated directly from backend Pydantic models (via `openapi-typescript`). |
| **Accidental API Key Leakage** | HIGH | Strict pre-commit hooks, `.gitignore` validation, and enforcement of server-side secret management. |

---

## 9. Final Decision Sign-Off

### **FINAL VERDICT: CONDITIONAL GO**

* **Status: APPROVED TO PROCEED TO PHASE 2B.**
* **Approved Scope:** Backend infrastructure, PostgreSQL database setup, Python valuation engine migration, local fallback integration, and removal of dead frontend dependencies.
* **Gated Scope:** ML model training (Phase 2D) and Gemini LLM synthesis (Phase 2F) remain gated until their respective infrastructure and data requirements are met.

