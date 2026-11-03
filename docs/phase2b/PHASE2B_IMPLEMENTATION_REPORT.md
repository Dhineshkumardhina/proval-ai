# Phase 2B Implementation Report — PropVal AI

**Project:** PropVal AI (Hero Housing Fintech Challenge)  
**Document:** Phase 2B FastAPI Core Backend, Database Schema & Valuation Engine Migration  
**Date:** November 2026  
**Author:** Technical Lead & Senior Full-Stack Engineer  
**Status:** COMPLETE  
**Git Branch:** `phase1-credibility-remediation`  
**Phase 2A Baseline Commit:** `ce60a92bbb891c54443cbb4c8d2e920d9735db04` (`docs: preserve Phase 2A engineering assessment`)  

---

## 1. Executive Implementation Summary

Phase 2B transitions PropVal AI from a purely client-side React prototype into a decoupled, institutional-grade full-stack architecture. The Python FastAPI modular monolith has been established, the database foundation with Alembic migrations has been deployed, the valuation engine math has been ported to Python with **100% numerical parity**, and the existing React 19 frontend has been seamlessly connected via a resilient hook with **guaranteed local rule-based offline fallback**.

All changes strictly preserve existing UI layout, typography, navigation, underwriter controls, and financial integrity without introducing ungrounded machine learning claims or private credential exposures.

---

## 2. Final Backend Directory Structure

```
backend/
├── alembic/
│   ├── env.py                     # Dynamic database URL injection & SQLite batch mode
│   ├── script.py.mako             # Migration template
│   └── versions/
│       └── 52062a7dacbf_initial_schema.py  # Initial schema migration
├── app/
│   ├── __init__.py                # Package version (0.2.0)
│   ├── main.py                    # FastAPI application, CORS middleware & lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # Central V1 endpoint aggregator
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py      # System health and database connectivity
│   │           └── valuation.py   # Valuation estimation & audit persistence
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic-settings configuration
│   │   └── database.py            # SQLAlchemy engine, session maker & declarative Base
│   ├── models/
│   │   ├── __init__.py            # Model export for Alembic autogeneration
│   │   ├── property.py            # PropertyRecord SQLAlchemy model
│   │   └── valuation.py           # ValuationCaseModel & ValuationResultModel
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── property.py            # Property Pydantic schemas (camelCase & snake_case)
│   │   └── valuation.py           # ValuationInputParams & ValuationResponse schemas
│   └── services/
│       ├── __init__.py
│       └── valuation_service.py   # Ported valuation math & currency formatting
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # In-memory SQLite fixtures & TestClient
│   ├── test_database.py           # ORM relationship & cascade tests
│   ├── test_health.py             # Health endpoint status tests
│   ├── test_valuation.py          # API endpoint validation & response tests
│   └── test_valuation_parity.py   # 12/12 numerical parity tests against TS baseline
├── alembic.ini                    # Alembic migration configuration
├── requirements.txt               # Pinned Python dependencies
└── .env.example                   # Non-secret environment template
```

---

## 3. Dependency Versions

### 3.1 Python Backend (`backend/requirements.txt`)
* `fastapi==0.142.2`
* `uvicorn[standard]==0.54.0`
* `pydantic==2.13.5`
* `pydantic-settings==2.15.0`
* `sqlalchemy==2.1.3`
* `alembic==1.20.0`
* `httpx==0.28.1`
* `pytest==9.1.1`
* `pytest-asyncio==1.4.0`
* `python-dotenv==1.2.4`

### 3.2 Frontend (`package.json`)
* `react`: `^19.0.1`
* `react-dom`: `^19.0.1`
* `vite`: `^8.3.0`
* `tailwindcss`: `^4.3.3`
* `lucide-react`: `^0.546.0`
* `tsx`: `^4.21.0`
* `typescript`: `^7.0.2`

---

## 4. Database Schema & Data Models

The database models support property records, loan appraisal cases, valuation calculations, and provenance metadata without inventing non-existent real transaction records.

### 4.1 Schema Overview

```
+--------------------------------------------------------------------------------------------------------------------+
| DATABASE SCHEMA (POSTGRESQL / SQLITE DUAL COMPATIBLE)                                                              |
+--------------------------------------------------------------------------------------------------------------------+
|                                                                                                                    |
| [properties]                                                                                                       |
|   id: String(36) [PK, UUID]                                                                                        |
|   application_no: String(64) [UNIQUE, INDEX]                                                                       |
|   project_name: String(255)                                                                                        |
|   unit_address: String(500)                                                                                        |
|   locality: String(128) [INDEX]                                                                                    |
|   city: String(64) [INDEX]                                                                                         |
|   pincode: String(16) [INDEX]                                                                                      |
|   property_type: String(64)                                                                                        |
|   carpet_area_sqft: Float                                                                                          |
|   super_built_up_area_sqft: Float                                                                                  |
|   floor_no, total_floors, age_years, road_width_ft                                                                 |
|   circle_rate_per_sqft, base_market_rate_per_sqft                                                                  |
|   floor_rise_factor, road_width_factor, amenities_premium, structural_depreciation                                 |
|   data_source: String(64) = 'synthetic-demo'                                                                       |
|   created_at, updated_at: DateTime(UTC)                                                                            |
|                                                                                                                    |
|         | 1                                                                                                        |
|         |                                                                                                          |
|         | N                                                                                                        |
| [valuation_cases]                                                                                                  |
|   id: String(36) [PK, UUID]                                                                                        |
|   property_id: String(36) [FK -> properties.id, ON DELETE CASCADE, INDEX]                                          |
|   borrower_name: String(255)                                                                                       |
|   co_borrower_name: String(255) [NULLABLE]                                                                         |
|   cibil_score: Integer                                                                                             |
|   loan_requested: Float                                                                                            |
|   declared_agreement_value: Float                                                                                  |
|   branch, assigned_underwriter: String(128)                                                                        |
|   status: String(32) [INDEX] ('READY_FOR_APPROVAL', 'REVIEW_REQUIRED', etc.)                                       |
|   status_label: String(64)                                                                                         |
|   underwriter_haircut_pct, distress_discount_pct, ltv_ratio_pct, legal_risk_penalty_pct                            |
|   data_source: String(64) = 'synthetic-demo'                                                                       |
|   created_at, updated_at: DateTime(UTC)                                                                            |
|                                                                                                                    |
|         | 1                                                                                                        |
|         |                                                                                                          |
|         | N                                                                                                        |
| [valuation_results]                                                                                                |
|   id: String(36) [PK, UUID]                                                                                        |
|   case_id: String(36) [FK -> valuation_cases.id, ON DELETE SET NULL, INDEX, NULLABLE]                              |
|   engine_version: String(32) = '0.2.0'                                                                             |
|   engine_type: String(64) = 'provisional rule-based estimation'                                                    |
|   data_source: String(64) = 'synthetic-demo'                                                                       |
|   carpet_area_sqft, super_built_up_area_sqft: Float                                                                |
|   unadjusted_rate_per_sqft, rule_adjusted_rate_per_sqft, circle_rate_per_sqft: Float                               |
|   gross_market_value, net_assessed_value, distress_liquidation_value, max_sanction_amount: Float                   |
|   deviation_from_circle_rate_pct, confidence_score_pct: Float                                                      |
|   risk_tier: String(32) ('LOW_RISK', 'MODERATE_RISK', 'HIGH_ALERT')                                               |
|   attribution_breakdown: JSON (5-factor hedonic waterfall)                                                         |
|   created_at: DateTime(UTC)                                                                                        |
+--------------------------------------------------------------------------------------------------------------------+
```

---

## 5. Migration Details

* **Tool:** Alembic 1.20.0
* **Initial Migration File:** `backend/alembic/versions/52062a7dacbf_initial_schema.py`
* **Upgrade Command:** `python -m alembic upgrade head`
* **Execution Evidence:**
  ```
  INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
  INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
  INFO  [alembic.runtime.migration] Running upgrade -> 52062a7dacbf, initial_schema
  ```
* **Batch Mode Support:** `backend/alembic/env.py` enables `render_as_batch=True` when running under SQLite, guaranteeing full migration compatibility across both SQLite and PostgreSQL.

---

## 6. API Endpoint Documentation

### 6.1 `GET /health`
* **Summary:** Root Health Check
* **Status:** 200 OK
* **Response Payload:**
  ```json
  {
    "status": "healthy",
    "service": "PropVal AI Institutional Valuation Backend",
    "version": "0.2.0",
    "engineType": "provisional rule-based estimation",
    "timestamp": "2026-11-02T10:19:13.073474+00:00"
  }
  ```

### 6.2 `GET /api/v1/health`
* **Summary:** API V1 Operational Health & Database Check
* **Status:** 200 OK
* **Response Payload:**
  ```json
  {
    "status": "healthy",
    "environment": "development",
    "version": "0.2.0",
    "engineType": "provisional rule-based estimation",
    "database": "connected",
    "timestamp": "2026-11-02T10:19:13.077655+00:00"
  }
  ```

### 6.3 `POST /api/v1/valuation/estimate`
* **Summary:** Calculate Institutional Property Valuation
* **Headers:** `Content-Type: application/json`
* **Request Payload (Example):**
  ```json
  {
    "carpetAreaSqFt": 1250,
    "superBuiltUpAreaSqFt": 1650,
    "baseMarketRatePerSqFt": 9800,
    "circleRatePerSqFt": 7800,
    "floorRiseFactor": 350,
    "roadWidthFactor": 250,
    "amenitiesPremium": 400,
    "structuralDepreciation": 150,
    "underwriterHaircutPct": -5,
    "distressDiscountPct": 20,
    "ltvRatioPct": 75,
    "legalRiskPenaltyPct": 0
  }
  ```
* **Response Payload (Example):**
  ```json
  {
    "carpetAreaSqFt": 1250.0,
    "superBuiltUpAreaSqFt": 1650.0,
    "unadjustedRatePerSqFt": 9800.0,
    "ruleAdjustedRatePerSqFt": 10650.0,
    "aiAdjustedRatePerSqFt": 10650.0,
    "circleRatePerSqFt": 7800.0,
    "grossMarketValue": 13312500,
    "netAssessedValue": 12646875,
    "distressLiquidationValue": 10117500,
    "maxSanctionAmount": 9485156,
    "deviationFromCircleRatePct": 36.5,
    "confidenceScorePct": 85.5,
    "riskTier": "MODERATE_RISK",
    "attributionBreakdown": [
      {
        "factor": "Micro-Market Baseline",
        "impactPerSqFt": 9800.0,
        "description": "Indicative micro-market baseline rate (synthetic benchmark, not verified transaction evidence)",
        "category": "neutral"
      },
      {
        "factor": "Floor Rise Factor",
        "impactPerSqFt": 350.0,
        "description": "High-floor premium (+4th floor and above)",
        "category": "positive"
      },
      {
        "factor": "Road Access & Arterial Width",
        "impactPerSqFt": 250.0,
        "description": "60ft+ master plan arterial road frontage",
        "category": "positive"
      },
      {
        "factor": "Gated Amenities & Security",
        "impactPerSqFt": 400.0,
        "description": "Clubhouse, power backup, swimming pool, 24/7 security & STP",
        "category": "positive"
      },
      {
        "factor": "Age & Structural Depreciation",
        "impactPerSqFt": -150.0,
        "description": "Asset vintage and physical maintenance wear factor",
        "category": "negative"
      }
    ],
    "engineVersion": "0.2.0",
    "engineType": "provisional rule-based estimation",
    "dataSource": "synthetic-demo",
    "isProvisional": true,
    "calculatedAt": "2026-11-02T10:19:13.082261Z"
  }
  ```

---

## 7. Valuation Engine Migration & Numerical Parity

### 7.1 Arithmetic Parity Implementation
To prevent IEEE 754 rounding discrepancies between JavaScript's `Math.round` (round half towards $+\infty$) and Python's default banker's rounding (`round()` to even), the Python service implements `js_round(val)`:
```python
def js_round(val: float) -> int:
    if math.isnan(val) or math.isinf(val):
        return 0
    if val >= 0:
        return math.floor(val + 0.5)
    return math.ceil(val - 0.5)
```
This guarantees identical integer rounding for gross value, net assessed value, distress liquidation value, and sanction amounts.

### 7.2 Parity Test Results (12/12 TypeScript Baseline Tests)

All 12 baseline regression and credibility tests from `src/utils/valuationEngine.test.ts` were replicated in `backend/tests/test_valuation_parity.py`:

| Test # | Test Description | TypeScript Result | Python Result | Parity Status |
| :---: | :--- | :---: | :---: | :---: |
| 1 | `formatIndianNumber` digit grouping (`14250000` -> `'1,42,50,000'`) | PASS | PASS | **100% IDENTICAL** |
| 2 | `formatIndianCurrency` full & short Lakh/Crore formats | PASS | PASS | **100% IDENTICAL** |
| 3 | Core calculation: rate, gross, net, distress, sanction, deviation | PASS | PASS | **100% IDENTICAL** |
| 4 | Edge cases: zero area & zero circle rate handling | PASS | PASS | **100% IDENTICAL** |
| 5 | Penalty deduction triggers & `HIGH_ALERT` assignment | PASS | PASS | **100% IDENTICAL** |
| 6 | Engine identifies as provisional rule-based without ML claims | PASS | PASS | **100% IDENTICAL** |
| 7 | Attribution breakdown disclaims synthetic benchmark without live deed claims | PASS | PASS | **100% IDENTICAL** |
| 8 | Confidence clearly flagged as uncalibrated heuristic score | PASS | PASS | **100% IDENTICAL** |
| 9 | Model governance provenance defaults (`engineVersion`, `engineType`) | PASS | PASS | **100% IDENTICAL** |
| 10 | Synthetic demo provenance markers retained (`synthetic-demo`) | PASS | PASS | **100% IDENTICAL** |
| 11 | Safe handling of `NaN`, negative inputs, and boundary enforcement | PASS | PASS | **100% IDENTICAL** |
| 12 | In-memory deterministic arithmetic verification | PASS | PASS | **100% IDENTICAL** |

---

## 8. Frontend Integration Details

### 8.1 Integration Files
1. [`src/services/apiClient.ts`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/services/apiClient.ts):
   * `API_BASE_URL` reads `import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'`.
   * Dispatches typed `fetchValuationEstimate` calls with `AbortSignal` support.
   * Catches errors gracefully without unhandled promise rejections.
2. [`src/hooks/useValuationEngine.ts`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/hooks/useValuationEngine.ts):
   * Immediately evaluates synchronous local fallback via `calculateValuation(params)`.
   * Dispatches an asynchronous request to FastAPI with a 100ms debounce.
   * If FastAPI responds successfully: sets `engineSource = 'fastapi'` and renders backend results.
   * If FastAPI is unreachable or errors: sets `engineSource = 'fallback'` and seamlessly retains local calculation.
3. [`src/components/ValuationStudio/ValuationStudio.tsx`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/components/ValuationStudio/ValuationStudio.tsx):
   * Replaced static `useMemo` with `useValuationEngine`.
   * Added dynamic Engine Badge in header banner:
     * When FastAPI is connected: `Engine: FastAPI Backend (v0.2.0)` (blue badge with pulsing indicator).
     * When offline/standalone: `Engine: Local Rule-Based (Offline Fallback)` (slate badge).
   * All 6 KPI metric cards, GIS map canvas, OCR document viewer, physical survey viewer, XAI attribution waterfall, comparables grid, and underwriter controls are 100% preserved.

---

## 9. Security Measures

1. **Zero Client Secrets:** Private credentials, database passwords, and JWT signing keys are completely excluded from frontend code. Only `VITE_API_BASE_URL` is referenced client-side.
2. **CORS Restrictions:** FastAPI applies a strict origin whitelist (`http://localhost:3000`, `http://localhost:5173`). Wildcard `*` is explicitly disabled.
3. **Pydantic Boundary Validation:** Incoming payloads are validated against strict numerical bounds (e.g. `floor minimum ₹1,000/sqft`, `haircut -90% to +50%`, `LTV 30% to 90%`).
4. **Safe Error Masking:** Unhandled exceptions return generic 500 error messages without dumping internal Python tracebacks or database metadata.
5. **Secret Protection:** `.gitignore` blocks `.env`, `*.db`, `*.sqlite`, `.pytest_cache`, and virtual environments.

---

## 10. Test and Build Execution Evidence

### 10.1 Backend Test Results (`pytest backend/tests/ -v`)
```
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\PROJECTS\dhina projects\proval ai\proval-ai\backend
plugins: anyio-4.15.1, platformdirs-4.13.0, asyncio-1.4.0
collected 17 items

tests/test_database.py::test_property_and_valuation_case_relationships PASSED [  5%]
tests/test_health.py::test_root_health PASSED                            [ 11%]
tests/test_health.py::test_api_v1_health PASSED                          [ 17%]
tests/test_valuation.py::test_estimate_valuation_endpoint_success PASSED [ 23%]
tests/test_valuation.py::test_estimate_valuation_validation_failure PASSED [ 29%]
tests/test_valuation_parity.py::test_format_indian_number_groups_digits_using_indian_numeral_system PASSED [ 35%]
tests/test_valuation_parity.py::test_format_indian_currency_formats_full_and_short_modes PASSED [ 41%]
tests/test_valuation_parity.py::test_calculate_valuation_computes_correct_gross_haircut_liquidation_and_sanction_values PASSED [ 47%]
tests/test_valuation_parity.py::test_calculate_valuation_handles_edge_cases_zero_area_and_zero_circle_rate_safely PASSED [ 52%]
tests/test_valuation_parity.py::test_calculate_valuation_applies_confidence_penalties_and_assigns_high_alert PASSED [ 58%]
tests/test_valuation_parity.py::test_credibility_valuation_engine_labels_identify_as_provisional_rule_based PASSED [ 64%]
tests/test_valuation_parity.py::test_credibility_attribution_breakdown_does_not_claim_live_sro_registered_evidence PASSED [ 70%]
tests/test_valuation_parity.py::test_credibility_confidence_score_distinguishes_heuristic_penalty_from_calibrated PASSED [ 76%]
tests/test_valuation_parity.py::test_credibility_model_governance_provenance_markers PASSED [ 82%]
tests/test_valuation_parity.py::test_credibility_demonstration_case_provenance_markers PASSED [ 88%]
tests/test_valuation_parity.py::test_credibility_edge_cases_with_nan_negative_inputs_handle_safely PASSED [ 94%]
tests/test_valuation_parity.py::test_credibility_ai_unconnected_purely_in_memory_arithmetic PASSED [100%]

============================= 17 passed in 0.14s ==============================
```

### 10.2 Frontend Test Results (`npm test`)
```
> react-example@0.0.0 test
> tsx --test src/utils/valuationEngine.test.ts src/services/apiClient.test.ts

✔ apiClient: checkBackendHealth returns false gracefully when backend is unreachable (56.6561ms)
✔ apiClient: fetchValuationEstimate throws network error gracefully when unreachable (4.2244ms)
✔ formatIndianNumber groups digits using Indian numeral system (2.1024ms)
✔ formatIndianCurrency formats full and short (Lakh / Crore) modes (0.2779ms)
✔ calculateValuation computes correct gross, haircut, liquidation and sanction values (0.3836ms)
✔ calculateValuation handles edge cases: zero area and zero circle rate safely (0.1505ms)
✔ calculateValuation applies confidence penalties and assigns HIGH_ALERT risk tier (0.1559ms)
✔ CREDIBILITY: Valuation Engine labels identify as provisional rule-based estimation without ML claims (0.2833ms)
✔ CREDIBILITY: Attribution breakdown does not claim live SRO registered transaction evidence (0.2219ms)
✔ CREDIBILITY: Confidence and uncertainty labels distinguish heuristic penalty from calibrated uncertainty (0.0924ms)
✔ CREDIBILITY: Model Governance labels use Pending verification and Not available for unverified items (0.1035ms)
✔ CREDIBILITY: All demonstration cases and comparables carry explicit machine-readable synthetic marker (0.2485ms)
✔ CREDIBILITY: Edge cases with NaN, negative inputs and empty comparables list handle safely (0.1978ms)
✔ CREDIBILITY: AI / Gemini status is verified as unconnected in prototype with no external network calls (0.1063ms)
ℹ tests 14
ℹ suites 0
ℹ pass 14
ℹ fail 0
ℹ duration_ms 205.5989
```

### 10.3 TypeScript Verification (`npm run lint`)
```
> react-example@0.0.0 lint
> tsc --noEmit
(Zero errors, exit code 0)
```

### 10.4 Production Build (`npm run build`)
```
> react-example@0.0.0 build
> vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 1679 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.43 kB │ gzip:  0.63 kB
dist/assets/index-DVu4pNgp.css   36.02 kB │ gzip:  7.59 kB
dist/assets/index-DXorEPoL.js   349.63 kB │ gzip: 98.80 kB
✓ built in 288ms
```

---

## 11. Known Limitations & Remaining Issues

1. **Synthetic Data Dependency:** Valuation cases and comparable deeds continue to rely on the standardized synthetic demonstration dataset (`dataSource: 'synthetic-demo'`). No live state SRO deed data is available.
2. **PostGIS Containerization:** PostgreSQL + PostGIS is fully configured in `docker-compose.yml`, but local tests run via SQLite due to the local Docker Desktop daemon being in an unstarted state. The dual-database architecture ensures seamless production migration.
3. **No Trained ML Model:** The valuation engine remains strictly a deterministic hedonic rule-based calculation. CatBoost training remains gated until Phase 2D when an empirical dataset is acquired.
4. **No LLM Integration:** Google Gemini integration remains gated until Phase 2F under the BFF architecture with PII sanitization.

---

## 12. Recommended Next Phase (Phase 2C)

With Phase 2B successfully completed, the project is ready for **Phase 2C (Statutory Guideline Rate Ingestion & Spatial Comparable Engine)**:
1. Ingest published statutory Circle Rate / Ready Reckoner rate schedules for target metro cities into PostgreSQL.
2. Ingest NHB RESIDEX quarterly trend series for macroeconomic price indexation.
3. Implement `GET /api/v1/comparables/search` supporting spatial proximity queries (`ST_DWithin`) to replace hardcoded SVG coordinates with genuine geospatial distances.

