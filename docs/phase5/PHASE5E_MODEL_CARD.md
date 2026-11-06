# PropVal AI — Phase 5E Model Card: PropVal-CatBoost-AVM

**Model Name:** `PropVal-CatBoost-AVM`  
**Model Architecture:** Gradient-Boosted Oblivious Decision Trees (`CatBoostRegressor`)  
**Document Standard:** Mitchell et al. (2019) *Model Cards for Model Reporting* & Federal Reserve SR 11-7  
**Model Lifecycle Status:** **CANDIDATE-IN-PREPARATION (UNTRAINED DUE TO PREREQUISITE GATE)**  
**Production Registry Status:** **INACTIVE / NO ACTIVE PRODUCTION ML MODEL**  
**Production Fallback:** Statutory Rule-Based Hedonic Engine ([`backend/app/schemas/valuation.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/schemas/valuation.py))  
**Date:** 2026-11-05  

---

## 1. Model Details

### 1.1 Overview
- **Developer:** PropVal AI Quantitative Risk & Data Science Team.
- **Model Type:** Supervised Regression on Tabular Real-Estate Data.
- **Algorithm:** CatBoost Regressor (Oblivious Trees with native categorical feature handling and Ordered Boosting).
- **Target Variable:** `transaction_price` (Total registered capital consideration in Indian Rupees, INR).
- **Loss Function:** Root Mean Squared Error (RMSE) with L2 leaf regularization ($\lambda = 3.0$).
- **Explainability Engine:** TreeSHAP (SHapley Additive exPlanations) for exact, local, attribution of valuation drivers.
- **Uncertainty Quantification:** Inductive Distribution-Free Conformal Prediction ($1 - \alpha = 90\%$ calibrated coverage guarantee).

### 1.2 Model Hyperparameters (Staged Specification)
```python
{
    "iterations": 1000,
    "learning_rate": 0.05,
    "depth": 6,
    "l2_leaf_reg": 3.0,
    "loss_function": "RMSE",
    "eval_metric": "MAPE",
    "random_seed": 42,
    "od_type": "Iter",
    "od_wait": 50,
    "has_time": True  # Enforces temporal order preservation during tree growth
}
```

---

## 2. Intended Use & Scope

### 2.1 Primary Intended Applications
- **Mortgage Collateral Underwriting:** Providing an objective, automated statistical valuation benchmark to Indian Housing Finance Companies (HFCs), NBFCs, and Scheduled Commercial Banks.
- **LTV Risk Assessment:** Assisting credit underwriters in identifying inflated or under-reported property purchase agreements against empirical sub-market trends.
- **Distress Liquidation Discounting:** Calibrating forced-sale liquidation values using calibrated uncertainty prediction intervals.

### 2.2 Prohibited & Out-of-Scope Uses
- **Autonomous Credit Decisioning:** The model is strictly an underwriting copilot; it is **PROHIBITED** from automatically approving or denying home loans without human credit officer review.
- **Agricultural & Commercial Land:** Not valid for agricultural land, tea estates, or industrial SEZ plots.
- **Litigated / Disputed Titles:** Properties with encumbrances, title defects, or court stays cannot be valued solely by ML without legal title clearance.

---

## 3. Data Schema & Feature Taxonomy

The model utilizes 10 core features comprising physical, administrative, economic, and temporal attributes:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MODEL FEATURE TAXONOMY                                       │
├────┬─────────────────────────────┬─────────────┬──────────┬─────────────────────────────────────┤
│ #  │ Feature Name                │ Type        │ DataType │ Economic Role                       │
├────┼─────────────────────────────┼─────────────┼──────────┼─────────────────────────────────────┤
│ 1  │ `carpet_area_sqft`          │ Continuous  │ Float    │ Primary physical scale driver       │
│ 2  │ `floor_no`                  │ Continuous  │ Integer  │ Floor level in multi-story tower    │
│ 3  │ `total_floors`              │ Continuous  │ Integer  │ Total tower elevation               │
│ 4  │ `floor_ratio`               │ Continuous  │ Float    │ Relative floor height (floor/total) │
│ 5  │ `guideline_rate_per_sqft`   │ Continuous  │ Float    │ Official circle rate statutory anchor│
│ 6  │ `age_years`                 │ Continuous  │ Integer  │ Building physical depreciation      │
│ 7  │ `city`                      │ Categorical │ String   │ Primary administrative district     │
│ 8  │ `locality`                  │ Categorical │ String   │ Micro-market locality cluster       │
│ 9  │ `property_type`             │ Categorical │ String   │ Architectural typology              │
│ 10 │ `transaction_quarter`       │ Categorical │ String   │ Temporal market quarter index       │
└────┴─────────────────────────────┴─────────────┴──────────┴─────────────────────────────────────┘
```

---

## 4. Training Data Prerequisites & Gate Criteria

Before any model artifact can be trained and registered:
1. **Sample Size:** Minimum **1,000 unique certified empirical deeds** ([`readiness_gate.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/readiness_gate.py)).
2. **Deed Proof:** SRO Index II registration references on all records.
3. **Data Purity:** Zero mock, simulation, or synthetic benchmark rows.
4. **Data Privacy:** Full DPDP Act 2023 compliance; all citizen names, PAN, and contact identifiers redacted.
5. **Split Methodology:** Strict 70% Train / 15% Calibration / 15% Out-of-Time Test chronological split.

---

## 5. Current Production Status & Fail-Safe Fallback

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           CURRENT PRODUCTION REALITY                             │
├────────────────────────────┬─────────────────────────────────────────────────────┤
│ Production Model State     │ UNTRAINED (BLOCKED by 1,000-record readiness gate)  │
│ Active Empirical Deeds     │ 46 / 1,000 records accumulated (Deficit: 954 deeds) │
│ Production Engine Active   │ Statutory Rule-Based Baseline Engine (Phase 1)      │
│ Model Registry Artifacts   │ 0 Active Models, 1 BLOCKED Training Record          │
└────────────────────────────┴─────────────────────────────────────────────────────┘
```

### Fallback Engine Guarantee:
When a valuation request is dispatched, the system routes through [`ValuationEngine`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/src/utils/valuationEngine.ts). The statutory baseline engine applies:
- Localized circle rate guideline valuation.
- Floor height adjustments ($+0.5\%$ per floor above floor 4).
- Age depreciation ($1.5\%$ linear haircut per year of age).
- Mandatory distress liquidation haircut ($15\% - 20\%$).
- Conformal uncertainty indicator flagged as `PROVISIONAL_RULE_BASED`.

---

## 6. Model Governance & Operational Controls

- **Model Ownership:** Institutional Data Science & Quantitative Underwriting Committee.
- **Approval Protocol:** Four-eyes review requiring joint approval from Lead ML Engineer and Chief Credit Officer.
- **Rollback Capability:** Full cryptographic model registry supporting single-command rollback to prior approved versions.
- **Monitoring & Retraining Trigger:** Quarterly drift audit; retraining triggered if mean absolute error exceeds 10% on rolling 90-day SRO deed samples.

