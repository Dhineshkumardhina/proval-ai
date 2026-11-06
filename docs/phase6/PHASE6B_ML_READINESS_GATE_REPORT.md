# PropVal AI — Phase 6B: Machine Learning Pre-Training Readiness Gate Report

**Document Reference:** `DOC-PHASE6B-GATE-001`  
**Phase:** 6B — Certified Empirical Transaction Dataset Expansion  
**Author:** Senior Financial Data Governance Specialist & Senior ML Systems Architect  
**Gate Engine:** `app.ml.readiness_gate.evaluate_training_gate`  
**Regulatory / Institutional Standard:** Federal Reserve SR 11-7 / OCC 2011-12 / RBI Model Risk Directives  
**Target Gate Threshold:** $\ge 1,000$ Certified Empirical Deeds  
**Database Audited:** `propval.db`  
**Date:** November 5, 2026  
**Final Gate Decision:** **LOCKED / BLOCKED (`canTrain = False`, `passed = False`)**  

---

## 1. Executive Summary & Gate Status

The PropVal AI Pre-Training Readiness Gate enforces an automated, immutable barrier that prevents premature or unverified training of machine learning automated valuation models (AVMs). 

### Gate Evaluation Results
```
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                               ML READINESS GATE AUDIT SUMMARY                                    ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════╣
║ Final Gate Decision       : BLOCKED (NO-GO)                                                      ║
║ Training Permitted        : FALSE (canTrain = False)                                             ║
║ Minimum Empirical Target  : 1,000 Certified Empirical Deeds                                      ║
║ Current Certified Deeds   : 140 Unique Deeds (204 Verified Records)                              ║
║ Absolute Sample Deficit   : 860 Certified Transactions (796 Verified Records)                    ║
║ Progress Percentage       : 14.0% Certified (20.4% Verified)                                     ║
║ Geographic Diversity      : 1 Dominant Locality (Whitefield: 92.2%) — FAILS Min 3 Requirement    ║
║ Property Typology Diversity: 100% Apartments — FAILS Portfolio Diversity Requirement            ║
║ Synthetic Contamination   : 0% in Certified Cohort (421 Mock Records Strictly Isolated)          ║
║ Operational Mode          : Statutory Rule-Based Baseline Engine (Active)                        ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Gate Criteria & Evaluation Matrix

The pre-training readiness gate evaluates every candidate dataset against 6 institutional risk criteria:

| Gate Criterion | Statutory Requirement | Database Observed Value | Status | Blocking Issue Code |
|:---|:---|:---:|:---:|:---|
| **1. Dataset Approval & Governance** | Institutional reviewer sign-off (`approval_status = 'APPROVED'`) | 57 approved datasets; 25 approved versions | **PASS** | — |
| **2. Licensing & Purpose Authorization** | Contractually permitted for `MODEL_TRAINING` | Verified Zapkey B2B commercial extract | **PASS** | — |
| **3. Non-Synthetic Provenance** | Zero synthetic, mock, or simulated records in certified training cohort | 140 certified deeds have authentic SRO Index II lineage; 421 synthetic records strictly isolated | **PASS** | — |
| **4. Minimum Empirical Sample Size** | **$\ge 1,000$ certified empirical deeds** | **140 unique certified deeds** (204 verified total in staging) | **FAIL** | **`INSUFFICIENT_SAMPLE_SIZE`** (Deficit: 860 deeds) |
| **5. Verified Deed Ratio** | $\ge 80.0\%$ certified registered deeds (not asking prices) | 100.0% registered deeds in certified datasets | **PASS** | — |
| **6. Geographic Micro-Market Diversity** | $\ge 3$ distinct micro-markets with balanced representation | 3 micro-markets total (Whitefield: 188, Indiranagar: 8, Koramangala: 8) — Whitefield is 92.2% | **FAIL** | **`INSUFFICIENT_GEOGRAPHIC_DIVERSITY`** (Spatial Overfitting Risk) |
| **7. Architectural Typology Diversity** | Multi-typology housing portfolio (Apartments, Villas, Houses, Plots) | 100.0% Apartments (196 High-Rise, 8 Mid-Rise); 0 Villas, 0 Plots, 0 Houses | **FAIL** | **`MONOLITHIC_PROPERTY_TYPES`** (Typology Overfitting Risk) |
| **8. Price Sanity & Numerical Variance** | Strictly positive prices, $\sigma \ge \text{₹}1,000$, $\text{Price} \le \text{₹}500\text{ Cr}$ | Prices: ₹1.25Cr – ₹1.98Cr, $\sigma = \text{₹}1,720,400$, 0 negative | **PASS** | — |

---

## 3. Detailed Audit Evidence from Database (`propval.db`)

### 3.1 Empirical Sample Size Deficit Analysis
```
Empirical Target : [██████████████████████████████████████████████████] 1,000 Deeds (100.0%)
Current Certified: [███████                                           ]   140 Deeds ( 14.0%)
Current Verified : [██████████                                        ]   204 Deeds ( 20.4%)
Deficit Remaining:                                                        860 Deeds ( 86.0%)
```

Under model risk guidance (SR 11-7), fitting high-dimensional gradient boosting regressors (e.g., LightGBM, CatBoost) or hedonic spatial splines on fewer than 1,000 empirical deed registrations creates severe statistical overfitting, uncalibrated epistemic uncertainty, and catastrophic out-of-distribution valuation errors. 

**Strict Policy Enforcement:** The threshold of 1,000 certified empirical transactions will **NOT** be lowered under any circumstances.

### 3.2 Geographic Concentration & Spatial Overfitting Risk
The distribution of the 204 verified deeds across micro-markets reveals extreme spatial concentration:
- **Bengaluru Urban — Whitefield:** **188 deeds (92.16%)**
- **Bengaluru Urban — Indiranagar:** **8 deeds (3.92%)**
- **Bengaluru — Koramangala:** **8 deeds (3.92%)**
- **Mumbai Metropolitan Region:** **0 deeds (0.00%)**
- **Delhi-NCR:** **0 deeds (0.00%)**
- **Hyderabad:** **0 deeds (0.00%)**

Training an ML model on this cohort would force the model to memorize the specific pricing surface of Whitefield high-rise societies (e.g. Prestige Shantiniketan, Brigade Metropolis), producing nonsensical valuations for other Indian micro-markets.

### 3.3 Property Typology Monolith
- **High-Rise Apartments:** **196 deeds (96.08%)**
- **Mid-Rise Apartments:** **8 deeds (3.92%)**
- **Independent Houses:** **0 deeds (0.00%)**
- **Villas / Row Houses:** **0 deeds (0.00%)**
- **Residential Plots:** **0 deeds (0.00%)**

An AVM trained on this cohort would lack any mathematical representation of land-to-building ratios, undivided share of land (UDS) depreciation, or plot boundary dimensions.

### 3.4 Rejection of Synthetic Contamination
During the audit, 421 synthetic transactions in `imported_transactions` (originating from test suites `SRC_E2E_*` and `TEST_SRC_*`) were tested against the gate:
- When a synthetic dataset was evaluated (`test_synthetic_data_strictly_disqualified_from_empirical_gate`), the gate triggered an immediate disqualification:
  > `DISQUALIFIED_PROVENANCE: Dataset is flagged as synthetic demonstration or mock data. Institutional governance strictly forbids training ML valuation models on fabricated or demonstration records.`
- Zero synthetic transactions are marked as `is_verified_deed = 1`.
- Zero synthetic transactions reside in approved dataset versions.

---

## 4. Statutory Rule-Based Baseline Engine Fallback

Because the ML training gate remains **`BLOCKED`**, PropVal AI operates strictly in **Deterministic Statutory Valuation Mode**:

```
                              VALUATION EXECUTION ROUTER
                              
                          Incoming Property Valuation Request
                                          │
                                          ▼
                            [Check ML Gate Status]
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
            ML Gate = UNLOCKED                        ML Gate = BLOCKED
        (Requires ≥ 1,000 Certified)                 (Current Status: 140)
                     │                                         │
                     │                                         ▼
           [CatBoost / Conformal]                 [Rule-Based Statutory Engine]
                                                  ├── 1. Circle Rate Base Value
                                                  ├── 2. Time-Indexed SRO Trends
                                                  ├── 3. Locality Boundary Offsets
                                                  ├── 4. Construction Cost Index
                                                  └── 5. 90% Conformal Interval
```

The statutory rule-based baseline engine provides deterministic, legally defensible property appraisals backed by the official Karnataka Kaveri and Maharashtra IGR circle rates, fully compliant with Section 56(2)(x) of the Indian Income Tax Act.

---

## 5. Unlock Conditions & Gate Re-Evaluation Trigger

The ML Pre-Training Gate will automatically re-evaluate and transition to **`UNLOCKED (`canTrain = True`)`** when and only when all of the following empirical conditions are simultaneously met:

1. **Certified Volume Milestone:** Exactly $\ge 1,000$ unique empirical property transactions with SRO Index II or B2B attestation are stored in `imported_transactions` with `is_verified_deed = 1`.
2. **Geographic Diversity Milestone:** At least 3 metropolitan clusters (e.g. Bengaluru, Mumbai, Hyderabad) with $\ge 200$ verified transactions per cluster, spanning at least 15 distinct micro-markets.
3. **Typology Diversity Milestone:** A minimum of 3 distinct property typologies (Apartments $\le 60\%$, Villas/Houses $\ge 20\%$, Plots $\ge 15\%$).
4. **Licensing Certification:** Executed commercial provider licenses on file with purpose authorization for `MODEL_TRAINING`.
5. **Quality Scorecard Sign-Off:** ISO 8000 completeness $\ge 95\%$ across all Tier-1 and Tier-2 valuation attributes.

---

## 6. Official Governance Sign-Off

- **Gate Status:** **`BLOCKED / GATED`**
- **Dataset ID Audited:** All active versions in `propval.db`
- **Certified Deeds Count:** **140**
- **Verified Deeds Count:** **204**
- **Target Threshold:** **1,000**
- **Deficit:** **860**
- **Authorized Action:** Maintain rule-based statutory engine; proceed with commercial provider data onboarding (Phase 6C/6D).

