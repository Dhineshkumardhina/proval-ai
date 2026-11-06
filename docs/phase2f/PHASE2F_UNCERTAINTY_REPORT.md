# Phase 2F Statistical Uncertainty Quantification & Conformal Prediction Report — PropVal AI

**Project:** PropVal AI (Hero Housing Fintech Challenge)  
**Document:** Phase 2F Statistical Uncertainty Quantification, Split Conformal Prediction & Calibration Gate Report  
**Date:** November 2026  
**Author:** Technical Lead & Principal ML Engineer  
**Status:** IMPLEMENTED, AUDITED & ETHICALLY GATED  
**Git Branch:** `phase1-credibility-remediation`  

---

## 1. Executive Summary

Phase 2F implements a mathematically sound, distribution-free statistical uncertainty quantification framework for **PropVal AI** using **Split Conformal Prediction**. Designed specifically for institutional mortgage lending and automated collateral appraisal (AVM), this phase establishes rigorous statistical bounds while strictly prohibiting the fabrication of uncalibrated prediction intervals.

### Core Deliverables:
1. **Split Conformal Prediction Engine ([`conformal.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/conformal.py)):** Built finite-sample adjusted conformal quantile estimation guaranteeing theoretical marginal coverage at nominal levels ($1 - \alpha \in \{0.90, 0.95\}$) under exchangeability.
2. **Strict Pre-Calibration Gate ([`calibration_gate.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/calibration_gate.py)):** Enforced multi-point prerequisite checks verifying that an approved ML model exists, training and calibration partitions are strictly disjoint, calibration records have verified deed provenance ($\ge 100$ records), and zero synthetic data is present.
3. **Current Operational Status — Confirmed GATED (`UNCERTAINTY_NOT_CALIBRATED`):**
   - Because Phase 2E correctly gated ML training (repository currently has 14 valid records < 1,000 threshold), **no production-ready ML model exists**.
   - Consequently, **conformal prediction interval generation is strictly GATED**.
   - `POST /api/v1/ml/uncertainty/predict` returns explicit `status: "UNCERTAINTY_NOT_CALIBRATED"` and deliberately withholds `lowerBound` and `upperBound` (`null`), refusing to manufacture simulated numbers.
4. **Subgroup Conditional Coverage Engine:** Implemented automated auditing of empirical coverage across Indian cities, localities, property typologies, area tiers, and transaction quarters to identify micro-market under-coverage.
5. **Rigorous Conceptual Taxonomy Separation:** Established clear architectural separation between heuristic rule consistency scores, data completeness, comparable evidence density, ML epistemic uncertainty, and distribution-free conformal prediction intervals.

---

## 2. Statistical Methodology: Split Conformal Prediction

### 2.1 Theoretical Framework & Finite-Sample Coverage Theorem
Standard Bayesian or heuristic confidence intervals assume normal distributions or asymptotic limits that routinely fail in real estate due to heavy tails, spatial autocorrelation, and illiquid trading. Conformal prediction provides a **distribution-free, finite-sample guarantee**:

Let $(X_1, Y_1), \dots, (X_n, Y_n)$ be exchangeable calibration observations from distribution $P_{X,Y}$, and $(X_{n+1}, Y_{n+1})$ be a new test property from the same distribution. For any nominal significance level $\alpha \in (0, 1)$, split conformal prediction constructs a prediction region $C(X_{n+1})$ such that:

$$1 - \alpha \le P\Big(Y_{n+1} \in C(X_{n+1})\Big) \le 1 - \alpha + \frac{1}{n + 1}$$

### 2.2 Mathematical Algorithm
1. **Model Training:** An approved CatBoost model $\hat{\mu}$ is fitted exclusively on the training partition $\mathcal{D}_{\text{train}}$.
2. **Nonconformity Scores:** On an independent, holdout calibration set $\mathcal{D}_{\text{cal}} = \{(X_i, Y_i)\}_{i=1}^n$, compute absolute residual nonconformity:
   $$s_i = |Y_i - \hat{\mu}(X_i)|, \quad \forall i \in \{1, \dots, n\}$$
3. **Finite-Sample Adjusted Quantile:** The critical threshold is the $k$-th order statistic:
   $$k = \left\lceil (n + 1)(1 - \alpha) \right\rceil, \quad \hat{q}_{\alpha} = s_{(k)}$$
4. **Prediction Interval Construction:** For any query feature vector $x$:
   $$C(x) = \Big[ \max\big(0.0, \, \hat{\mu}(x) - \hat{q}_{\alpha}\big), \; \hat{\mu}(x) + \hat{q}_{\alpha} \Big]$$
5. **Sample Size Constraint:** To guarantee nominal coverage $1 - \alpha$, the calibration set must satisfy:
   $$n \ge \frac{1}{\alpha} - 1$$
   - For $90\%$ coverage ($\alpha = 0.10$): $n \ge 9$.
   - For $95\%$ coverage ($\alpha = 0.05$): $n \ge 19$.
   - **Institutional Fintech Policy:** PropVal AI mandates a minimum of **$n \ge 100$ independent holdout calibration deeds** to ensure finite-sample stability and avoid excessively wide intervals.

---

## 3. Strict Calibration Gate & Current Ground Truth Status

### 3.1 Pre-Calibration Gate Checklist

| Prerequisite Check | Condition / Institutional Standard | Evaluation on Current Repository | Status |
| :--- | :--- | :--- | :---: |
| **1. Validated Model Existence** | Active, production-ready ML model in `ml_models` | No model active (Phase 2E ML training gated at 14/1,000 records) | **FAILED** |
| **2. Calibration Dataset Exists** | Distinct dataset registered in `datasets` | No separate calibration dataset cataloged | **FAILED** |
| **3. Dataset Disjointness** | $\mathcal{D}_{\text{cal}} \cap \mathcal{D}_{\text{train}} = \emptyset$ (Zero data leakage) | Cannot evaluate without separate dataset | **BLOCKED** |
| **4. Provenance Integrity** | Must not be synthetic, demo, or mock data | Repository sample flagged as verification set | **BLOCKED** |
| **5. Minimum Holdout Volume** | $\ge 100$ verified registered deed records | 0 calibration holdouts available | **FAILED** |
| **6. Target Sanity** | Non-negative, finite variance, no missing targets | Evaluated during ingestion | **PASSED** |

### 3.2 Formal Calibration Gate Verdict

```
+-----------------------------------------------------------------------------------+
|                        PRE-CALIBRATION GATE AUDIT RESULT                          |
+===================================================================================+
|  Status:                     UNCERTAINTY_NOT_CALIBRATED                           |
|  Can Calibrate:              FALSE                                                |
|  Active ML Model:            NONE (Model training gated in Phase 2E)              |
|  Calibration Records Count:  0 records                                            |
|  Minimum Required Records:   100 holdout records                                  |
|  Disjoint from Training:     FALSE                                                |
+-----------------------------------------------------------------------------------+
|  BLOCKING ISSUES IDENTIFIED:                                                      |
|  1. MISSING_VALIDATED_MODEL: No production-ready ML model exists in registry.     |
|     Model training remains GATED due to insufficient empirical records (<1,000).  |
|     Statistical conformal calibration requires an underlying validated model.    |
+-----------------------------------------------------------------------------------+
|  GOVERNANCE DIRECTIVE:                                                            |
|  UNCERTAINTY_NOT_CALIBRATED: Prediction interval generation is BLOCKED.           |
|  PropVal AI strictly refuses to manufacture simulated intervals or uncalibrated  |
|  confidence percentages. All prediction intervals are deliberately withheld.      |
+-----------------------------------------------------------------------------------+
```

---

## 4. Rule-Based Uncertainty vs. Statistical Confidence Separation

To prevent institutional lenders from confusing heuristic credit adjustments with mathematical probabilities, Phase 2F enforces strict conceptual separation across 5 distinct appraisal dimensions:

```
+----------------------------------------------------------------------------------------------------+
|                         PROPVAL AI UNCERTAINTY & SCORING TAXONOMY                                  |
+====================================================================================================+
| 1. Rule Consistency Score       | Deterministic scorecard heuristic evaluating alignment between   |
|    (e.g., 88.0%)                | property inputs, circle rate benchmarks, and haircut parameters.  |
|                                 | NOT A STATISTICAL CONFIDENCE PERCENTAGE.                         |
+---------------------------------+------------------------------------------------------------------+
| 2. Data Completeness Score      | Proportion of mandatory statutory, title, physical, and survey   |
|    (e.g., 95.0%)                | fields populated in the intake dossier (e.g., 8/9 fields).       |
+---------------------------------+------------------------------------------------------------------+
| 3. Comparable Evidence Coverage | Density, spatial radius (<1.5 km), and recency (<12 months) of    |
|    (e.g., "5 Certified Comps")  | registered SRO deed transactions in the micro-market.            |
+---------------------------------+------------------------------------------------------------------+
| 4. ML Epistemic Uncertainty     | Algorithmic variance across decision trees in the gradient       |
|    (e.g., CatBoost tree spread) | boosting ensemble (currently gated).                             |
+---------------------------------+------------------------------------------------------------------+
| 5. Conformal Prediction         | Finite-sample mathematical region [Lower, Upper] guaranteeing     |
|    Interval (90% / 95%)         | 90%/95% marginal coverage under exchangeability.                 |
|                                 | STATUS: UNCALIBRATED (GATED). NEVER MANUFACTURED.                |
+----------------------------------------------------------------------------------------------------+
```

---

## 5. Subgroup Conditional Coverage Analysis Architecture

While split conformal prediction guarantees **marginal coverage** over the entire population:
$$P(Y \in C(X)) \ge 1 - \alpha$$
It does not guarantee **conditional coverage** for every micro-market stratum:
$$P(Y \in C(X) \mid X \in \text{Locality}_j) \ge 1 - \alpha$$

The module [`backend/app/ml/conformal.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/conformal.py) implements automated subgroup auditing (`evaluate_subgroup_coverage`):
- **Stratification Dimensions:**
  1. **City:** Macro-market jurisdiction.
  2. **Locality:** Micro-market neighborhood.
  3. **Property Type:** High-Rise Apartment, Villa, Independent House.
  4. **Area Tiers:** Compact ($< 900\text{ sq ft}$), Mid-Size ($900 - 1600\text{ sq ft}$), Large ($> 1600\text{ sq ft}$).
  5. **Transaction Quarter:** Time periods to detect macroeconomic drift.
- **Under-Coverage Flagging:** If a subgroup's empirical coverage falls $> 5\%$ below nominal ($\text{Empirical} < 1 - \alpha - 0.05$), the system flags `isUnderCovered = True`.

---

## 6. Runtime Uncertainty Service & API Implementation

The uncertainty service ([`backend/app/ml/uncertainty_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/uncertainty_service.py)) exposes endpoints under `/api/v1/ml/uncertainty`:

### 6.1 Endpoints Catalog

| Method | Endpoint | Description | Behavior When Calibration Gated |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/ml/uncertainty/status` | Query calibration state, supported coverage levels, and taxonomy | Returns `calibrationStatus: "UNCERTAINTY_NOT_CALIBRATED"`, `isCalibrated: false`, with full audit diagnostics. |
| `POST` | `/api/v1/ml/uncertainty/predict` | Predict valuation with conformal prediction bounds | Returns point estimate from verified rule engine; sets `lowerBound: null`, `upperBound: null`, and explains that bounds are withheld. |
| `GET` | `/api/v1/ml/uncertainty/gate-check/{id}` | Audit a candidate dataset for calibration eligibility | Checks disjointness, sample size ($\ge 100$), and provenance integrity. |

### 6.2 Live API Prediction Response in Current Gated State

```json
{
  "status": "UNCERTAINTY_NOT_CALIBRATED",
  "isCalibrated": false,
  "pointEstimate": 14250000.0,
  "pointEstimatePerSqFt": 11875.0,
  "nominalCoverage": 0.90,
  "lowerBound": null,
  "upperBound": null,
  "intervalWidth": null,
  "relativeIntervalWidthPct": null,
  "empiricalCoverage": null,
  "modelVersion": null,
  "calibrationVersion": null,
  "ruleConsistencyScore": 88.0,
  "dataCompletenessScore": 95.0,
  "evidenceCoverageTier": "PROVISIONAL_RULE_BASED",
  "governanceDisclaimer": "Statistical conformal prediction intervals are UNCALIBRATED. Nominal coverage of 90% cannot be certified without genuine holdout calibration deeds. Prediction intervals and confidence bounds are deliberately withheld to prevent misleading credit committee underwriting. The Rule Consistency Score is a heuristic scorecard factor and must NOT be interpreted as a statistical confidence interval.",
  "blockingReasons": [
    "MISSING_VALIDATED_MODEL: No production-ready ML model exists in registry. Model training remains GATED due to insufficient empirical records (<1,000 threshold). Statistical conformal calibration requires an underlying validated predictive model."
  ]
}
```

---

## 7. Frontend Integration & UI Credibility

### 7.1 Preserved Design & Layout
* **Zero Visual Breakages:** All existing layouts in [`ValuationStudio.tsx`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/components/ValuationStudio/ValuationStudio.tsx), GIS maps, OCR viewers, and underwriter controls are 100% preserved.
* **Separation of Scores:** The Rule Consistency KPI card explicitly displays badge `"Uncalibrated Heuristic"` alongside notice `"Calibrated Uncertainty: Not available: no calibrated model"`.
* **Governance Dashboard ([`ModelGovernanceView.tsx`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/components/ModelGovernance/ModelGovernanceView.tsx)):** Enhanced with an enterprise-grade conceptual taxonomy matrix explicitly defining the separation between Rule Consistency, Data Completeness, Comps Evidence, and Conformal Prediction Intervals.
* **API Client Layer ([`apiClient.ts`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/services/apiClient.ts)):** Added [`fetchUncertaintyStatus`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/services/apiClient.ts#L383-L397) and [`requestUncertaintyPrediction`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/services/apiClient.ts#L402-L422) with guaranteed offline resilience.

---

## 8. Verification & Test Evidence

### 8.1 Backend Automated Pytest Suite
Command: `python -m pytest backend/tests/ -v` (PowerShell, Windows, Python 3.14.7)
- **Total Tests Passed:** **64 / 64** (100% pass rate in 21.13s)
  - Conformal & Uncertainty Tests ([`test_uncertainty.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_uncertainty.py)): **12 / 12 passed**
  - ML Engine Tests ([`test_ml_engine.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_ml_engine.py)): **12 / 12 passed**
  - Ingestion Tests ([`test_ingestion.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_ingestion.py)): **9 / 9 passed**
  - Parity & Credibility Tests ([`test_valuation_parity.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_valuation_parity.py)): **12 / 12 passed**
  - Case Management Tests ([`test_cases.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_cases.py), [`test_e2e_workflow.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_e2e_workflow.py)): **19 / 19 passed**

### 8.2 Frontend Automated Test Suite & Build
- **Unit Tests (`npm test`):** **21 / 21 passed** (in 1.12s)
  - Verified offline handling for `fetchUncertaintyStatus` and `requestUncertaintyPrediction`.
- **TypeScript Linter (`npm run lint`):** **0 errors** (`tsc --noEmit`).
- **Production Build (`npm run build`):** **Clean Vite build** completed in 2.02s.

---

## 9. Final Conclusion & Uncertainty Determination

### **CALIBRATION DETERMINATION: STRICTLY GATED (`UNCERTAINTY_NOT_CALIBRATED`)**
* **Point Estimates:** Genuinely available via the statutory rule-based hedonic engine.
* **Calibrated Prediction Intervals:** **NOT AVAILABLE / GATED**.
* **Reason:** In accordance with fintech risk management ethics and the prompt's strict rules, calibrated intervals $[L, U]$ and nominal coverage claims ($90\%/95\%$) are refused until an authentic ML model is trained and an independent empirical calibration holdout dataset ($\ge 100$ deeds) is registered.
* **Integrity Guarantee:** Zero intervals, zero pseudo-confidence bounds, and zero synthetic calibration numbers have been manufactured.

