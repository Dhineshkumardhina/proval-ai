# PropVal AI — Phase 6E: Regression & Validation Test Report

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6E — Dependency Harmonization & Observability Remediation  
**Date:** 2026-11-05  
**Author:** Senior Python Backend Engineer, DevSecOps Engineer, and OpenTelemetry Specialist  
**Status:** **100% PASSED (ALL TIERS GREEN)**

---

## 1. Test Summary Overview

Phase 6E completed comprehensive multi-tier regression testing across Python backend dependencies, OpenTelemetry distributed tracing, operational monitoring, frontend unit tests, TypeScript type safety, production asset compilation, and security vulnerability scanning.

| Test Category | Target Scope | Tests Passed | Pass Rate | Duration |
|:---|:---|:---:|:---:|:---:|
| **Dependency Integrity** | `pip check` | Clean (0 conflicts) | 100% | 0.8s |
| **Vulnerability Audit** | `pip-audit -r backend/requirements.txt` | Clean (0 CVEs) | 100% | 1.8s |
| **Phase 6E Verification Suite** | `backend/tests/test_observability_and_dependencies_phase6e.py` | 11 / 11 | 100% | 1.19s |
| **Full Backend Automated Suite** | All `backend/tests/` (Pytest) | 434 / 434 | 100% | 66.15s |
| **Frontend Unit & Component Suite** | Vitest (`src/**/*.test.ts`) | 26 / 26 | 100% | 0.43s |
| **TypeScript Strict Typecheck** | `npx tsc --noEmit` | Clean (0 errors) | 100% | 2.5s |
| **Production Bundle Compilation** | `npm run build` (Vite) | 1682 modules | 100% | 1.51s |

---

## 2. Phase 6E Dedicated Verification Suite

Executed: `python -m pytest backend/tests/test_observability_and_dependencies_phase6e.py -v`

```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\PROJECTS\dhina projects\proval ai\proval-ai
configfile: pyproject.toml
plugins: anyio-4.15.1, locust-2.47.0, platformdirs-4.13.0, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 11 items

backend/tests/test_observability_and_dependencies_phase6e.py::test_pip_check_clean PASSED [  9%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_opentelemetry_version_harmonization PASSED [ 18%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_otlp_http_exporter_compatibility PASSED [ 27%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_structured_logging_json_schema PASSED [ 36%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_structured_logging_trace_correlation PASSED [ 45%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_span_processor_redacts_credentials_and_pii PASSED [ 54%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_monitoring_failure_resilience PASSED [ 63%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_trace_headers_injection PASSED [ 72%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_observability_registry_record_and_summary PASSED [ 81%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_metrics_endpoints_available PASSED [ 90%]
backend/tests/test_observability_and_dependencies_phase6e.py::test_health_includes_component_metrics PASSED [100%]

============================= 11 passed in 1.19s ==============================
```

---

## 3. Full Backend Automated Test Suite Execution

Executed: `python -m pytest backend/tests -q`

```text
........................................................................ [ 16%]
........................................................................ [ 33%]
........................................................................ [ 49%]
........................................................................ [ 66%]
........................................................................ [ 82%]
........................................................................ [ 99%]
..                                                                       [100%]
============================== warnings summary ===============================
backend/tests/test_production_readiness.py::test_upload_exceeding_max_size_rejected
  StarletteDeprecationWarning: 'HTTP_413_REQUEST_ENTITY_TOO_LARGE' is deprecated. Use 'HTTP_413_CONTENT_TOO_LARGE' instead.
434 passed, 1 warning in 66.15s (0:01:06)
```

**Result:** **434 passed**, 0 failed out of 434 tests.

---

## 4. Frontend & Build Validation

### 4.1 Vitest Unit Suite
Executed: `npm test -- --run`
```text
✔ apiClient: checkBackendHealth returns false gracefully when backend is unreachable (83.3ms)
✔ apiClient: fetchValuationEstimate throws network error gracefully when unreachable (8.8ms)
✔ apiClient: fetchCases and fetchCaseById handle offline state gracefully (9.8ms)
✔ apiClient: createCase, updateCase and updateCaseStatus error handling (14.5ms)
✔ apiClient: fetchComparables returns array or empty list on offline state (4.8ms)
✔ apiClient: fetchMLStatus handles offline state gracefully returning null (4.1ms)
✔ apiClient: requestMLPrediction handles offline state gracefully returning null (4.1ms)
✔ apiClient: fetchUncertaintyStatus handles offline state gracefully returning null (4.9ms)
✔ apiClient: requestUncertaintyPrediction handles offline state gracefully returning null (3.7ms)
✔ apiClient: fetchAIStatus handles offline state gracefully returning null (4.1ms)
✔ apiClient: fetchAIUnderwriterBriefing handles offline state gracefully returning null (3.8ms)
✔ apiClient: fetchAuditEvents handles offline state gracefully returning null (3.5ms)
✔ apiClient: verifyAuditChain handles offline state gracefully returning null (3.6ms)
✔ apiClient: fetchAuditSummary handles offline state gracefully returning null (3.5ms)
✔ formatIndianNumber groups digits using Indian numeral system (2.4ms)
✔ formatIndianCurrency formats full and short (Lakh / Crore) modes (0.6ms)
✔ calculateValuation computes correct gross, haircut, liquidation and sanction values (0.7ms)
✔ calculateValuation handles edge cases: zero area and zero circle rate safely (0.2ms)
✔ calculateValuation applies confidence penalties and assigns HIGH_ALERT risk tier (0.2ms)
✔ CREDIBILITY: Valuation Engine labels identify as provisional rule-based estimation without ML claims (0.3ms)
✔ CREDIBILITY: Attribution breakdown does not claim live SRO registered transaction evidence (0.2ms)
✔ CREDIBILITY: Confidence and uncertainty labels distinguish heuristic penalty from calibrated uncertainty (0.2ms)
✔ CREDIBILITY: Model Governance labels use Pending verification and Not available for unverified items (0.2ms)
✔ CREDIBILITY: All demonstration cases and comparables carry explicit machine-readable synthetic marker (0.4ms)
✔ CREDIBILITY: Edge cases with NaN, negative inputs and empty comparables list handle safely (0.3ms)
✔ CREDIBILITY: AI / Gemini status is verified as unconnected in prototype with no external network calls (0.1ms)
ℹ tests 26 | pass 26 | fail 0 | duration_ms 434.65
```

### 4.2 Production Asset Build
Executed: `npm run build`
```text
vite v8.3.5 building client environment for production...
transforming...
✓ 1682 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                 1.68 kB │ gzip:  0.70 kB
dist/assets/index-DZL5kVWi.css                 39.74 kB │ gzip:  8.46 kB
dist/assets/rolldown-runtime-WkwZ5CU-.js        0.59 kB │ gzip:  0.36 kB
dist/assets/NewCaseModal-DKYRyxJq.js            7.98 kB │ gzip:  2.73 kB
dist/assets/UnderwritingPipeline-BalP3KPN.js    9.57 kB │ gzip:  2.51 kB
dist/assets/vendor-icons-D0ctQliG.js           19.73 kB │ gzip:  7.13 kB
dist/assets/RiskAuditDashboard-BS6QZ5hH.js     23.02 kB │ gzip:  5.63 kB
dist/assets/ModelGovernanceView-Bv1jNNF-.js    33.03 kB │ gzip:  6.58 kB
dist/assets/index-_CPjcRgy.js                 110.03 kB │ gzip: 26.57 kB
dist/assets/vendor-react-CkxBCpPO.js          210.90 kB │ gzip: 65.85 kB

✓ built in 1.51s
```

---

## 5. Security & Vulnerability Scan

Executed: `python -m pip_audit -r backend/requirements.txt`
```text
No known vulnerabilities found
```
**Exit Code:** `0`

---

## 6. Conclusion

Phase 6E has completely resolved the OpenTelemetry version gap identified in Phase 5H:
1. `fastapi 0.142.2` and `opentelemetry-api 1.45.2` operate in complete harmony.
2. `pip check` passes cleanly with 0 broken dependencies.
3. OpenTelemetry distributed tracing and metrics registry provide continuous observability across API, database, ML, ingestion, valuation, authentication, and audit layers.
4. PII, authorization tokens, and database passwords are redacted from spans and logs.
5. All 434 backend tests and 26 frontend tests pass 100%.

