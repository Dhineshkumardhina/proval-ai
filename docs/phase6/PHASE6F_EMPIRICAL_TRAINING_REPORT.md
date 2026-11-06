# PropVal AI — Phase 6F: Empirical CatBoost Training Report

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6F — Empirical CatBoost Training & Model Certification  
**Date:** 2026-11-05  
**Author:** Senior Quantitative ML Engineer, Financial Model Validation Specialist, and ML Governance Officer  
**Training Gate Evaluation Status:** **FAILED / TRAINING STRICTLY BLOCKED**  
**Execution Outcome:** **NO MODEL TRAINED — FALLBACK DETERMINISTIC RULE-BASED ENGINE ACTIVE**

---

## 1. Executive Summary & Critical Precondition Audit

Under PropVal AI Quantitative Governance Standard §6.1 and the Phase 6F requirements, empirical machine learning model training is strictly conditioned on passing the **Pre-Training ML Readiness Gate**:
1. Minimum of **1,000 unique certified empirical transactions** with registered SRO deed verification.
2. Legitimate data source attribution and commercial licensing allowing model training.
3. Dataset quality, geographical diversity ($\ge 3$ micro-markets), and property typology sanity verified.
4. Total isolation and exclusion of synthetic demonstration and mock records.
5. Sealed, immutable, versioned dataset snapshot signed with a cryptographic SHA-256 Merkle root.

### Critical Precondition Audit Outcome
An exhaustive audit of `propval.db`, the Certified Dataset Register, and `dataset_versions` was conducted prior to executing any training routines:

| Gate Criterion | Required Institutional Threshold | Actual Certified Register Value | Audit Status |
|:---|:---:|:---:|:---:|
| **Certified Empirical Sample Size** | $\ge 1,000$ unique verified deeds | **140 unique approved deeds** (364 staged deeds total across DB) | **BLOCKED (Deficit: 860 deeds)** |
| **Commercial Licensing for ML** | Signed B2B License permitting ML derivation | Pending commercial execution (Phase 6A Staging) | **BLOCKED** |
| **Synthetic Provenance Isolation** | 0% synthetic or demonstration records | Cleanly isolated (0 synthetic in certified corpus) | **PASSED** |
| **Geographic Diversity** | $\ge 3$ micro-markets / sub-districts | Concentrated primarily in Whitefield / Bengaluru | **BLOCKED** |
| **Dataset Version Immutability** | Sealed Merkle checksum in `dataset_versions` | 25 approved version snapshots registered | **PASSED** |
| **Overall ML Readiness Gate** | **ALL 5 CRITERIA PASSED** | **FAILED (2 of 5 Passed, 3 Blocked)** | **STRICTLY BLOCKED** |

---

## 2. Refusal to Train Under Insufficient Sample Size

In strict compliance with the Phase 6F directive:
> *"IF THE GATE FAILS: Do not train. Do not lower the minimum threshold. Do not generate fake model metrics. Do not reuse synthetic demonstration data. Generate a blocked-training report."*

The quantitative engineering team has **refused to train the CatBoost regressor** or fabricate synthetic performance metrics:
1. **No Threshold Lowering:** The 1,000-record threshold established in Phase 2D and reaffirmed in Phase 6B remains non-negotiable. Lowering the threshold to fit the existing 140 certified deeds would induce severe high-variance overfitting, sampling bias, and catastrophic estimation error across unrepresented micro-markets.
2. **No Metric Fabrication:** No artificial MAE, MAPE, or $R^2$ figures have been generated. Reporting speculative metrics without empirical execution violates financial model risk governance (RBI Draft Directions on Model Risk Management).
3. **No Synthetic Training Data:** Synthetic demonstration cases (`dataSource="synthetic-demo"`) remain strictly confined to UI demonstration pipelines and are blocked from entering training matrices.

---

## 3. Training Pipeline Architecture & Gate Enforcement

The training pipeline in [`backend/app/ml/trainer.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/trainer.py) programmatically intercepts training requests:

```python
# Evaluate Strict Pre-Training Gate
gate_audit = evaluate_training_gate(db, dataset_id)

if not gate_audit.canTrain:
    blocked_model = MLModelRegistryModel(
        version=f"BLOCKED-{int(time.time())}",
        dataset_id=dataset_id,
        algorithm=algorithm,
        hyperparameters={"blocked": True},
        status="BLOCKED",
        is_production_ready=False,
        training_records_count=0,
        readiness_gate_audit=gate_audit.model_dump(by_alias=True),
    )
    db.add(blocked_model)
    db.commit()
    raise HTTPException(status_code=422, detail="TRAINING_BLOCKED_BY_READINESS_GATE")
```

### Audit Record in `ml_models`
A permanent audit record documenting the blocked training attempt is persisted in the database:
* **Model Version:** `BLOCKED-1793895149`
* **Algorithm:** `CatBoostRegressor`
* **Status:** `BLOCKED`
* **Production Ready:** `False`
* **Training Records:** `0`
* **Blocking Reasons:**
  1. `INSUFFICIENT_SAMPLE_SIZE: Dataset contains fewer than 1,000 certified empirical transaction records.`
  2. `PURPOSE_RESTRICTION: Commercial data provider license agreements remain pending activation.`
  3. `GEOGRAPHIC_CONCENTRATION: Insufficient multi-city representation across Mumbai, NCR, and Hyderabad.`

---

## 4. Active Operational State: Deterministic Rule-Based Fallback

While empirical ML model training remains gated, the PropVal AI valuation platform remains **100% operational** using the deterministic hedonic scorecard valuation engine:
* **Engine Type:** `provisional rule-based estimation`
* **Engine Version:** `0.2.0`
* **Mechanism:** Rule-adjusted rate estimation incorporating circle rate floors, floor-rise factors, road-width multipliers, amenities premiums, structural depreciation, and underwriter risk haircuts.
* **Audit Integrity:** Every valuation case generated explicitly displays the machine-readable disclaimer: *"Advisory valuation generated by provisional deterministic hedonic scorecard engine. ML training gated pending 1,000 certified deed threshold."*

