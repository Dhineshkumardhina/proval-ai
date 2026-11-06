# PropVal AI — Phase 5E Model Governance Report

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Institutional Model Risk Governance, Lifecycle Management & Deployment Controls  
**Regulatory Standards:** Federal Reserve SR 11-7 / OCC 2011-12, RBI Master Direction on IT Governance & Risk (2023), NHB HFC Directions  
**Audit Standard:** ISO/IEC 38507 (Governance implications of the use of AI by organizations)  
**Date:** 2026-11-05  
**Governance Roles:** Senior ML Engineer, Chief Credit Officer & Institutional Model Risk Auditor  

> [!IMPORTANT]
> **INSTITUTIONAL MODEL GOVERNANCE PRINCIPLE:**  
> **Under NO circumstances does a trained machine learning model automatically deploy into production.**  
> Deployment of any predictive valuation model requires:
> 1. Independent mathematical validation by a decoupled risk unit.
> 2. Documented sign-off by the Institutional Credit & Risk Committee.
> 3. Cryptographic artifact registration in the model registry (`ml_models`).
> 4. Human-controlled manual promotion to `ACTIVE` status.
> 5. Instant single-click rollback capability to prior verified baselines.

---

## 1. Executive Summary

Phase 5E formalizes the Model Risk Management (MRM) framework for PropVal AI. In wholesale banking and institutional mortgage lending, automated valuation errors carry substantial capital adequacy risks, balance sheet haircuts, and systemic collateral default exposure.

To eliminate model risk, PropVal AI enforces strict lifecycle governance:
- **Pre-Training Gate:** Enforces $\ge 1,000$ verified empirical deeds before training can initiate.
- **Separation of Duties:** Enforces the "Four-Eyes Principle"—the machine learning developer requesting training cannot approve or deploy the model.
- **Model Registry Architecture:** Every training run (including blocked attempts) is permanently recorded in the `ml_models` relational database ledger with full audit metadata.
- **Human-Controlled Promotion:** Promotion from `CANDIDATE` to `ACTIVE` production state is strictly gated behind underwriter and Chief Risk Officer authorization.

---

## 2. Institutional Model Lifecycle Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               PROPVAL AI MODEL LIFECYCLE STAGES                                │
├──────────────────────┬────────────────────────┬─────────────────────────┬──────────────────────┤
│ Lifecycle Stage      │ Gate / Trigger         │ Responsibility          │ Current Status       │
├──────────────────────┼────────────────────────┼─────────────────────────┼──────────────────────┤
│ 1. Data Ingestion    │ SRO deed verification  │ Data Engineering        │ **ACTIVE (46 Deeds)**│
│ 2. Pre-Training Gate │ $\ge 1,000$ deeds check│ Automated Readiness Gate│ **BLOCKED (Deficit)**│
│ 3. Model Training    │ CatBoost Regressor run │ Lead ML Engineer        │ **SUSPENDED**        │
│ 4. Independent Valid.│ OOT split & Conformal  │ Model Risk Validator    │ **SUSPENDED**        │
│ 5. Committee Approval│ Risk Committee sign-off│ Chief Credit Officer    │ **GATED**            │
│ 6. Production Deploy │ Manual activation      │ Enterprise DevOps       │ **BASELINE ENGINE**  │
└──────────────────────┴────────────────────────┴─────────────────────────┴──────────────────────┘
```

---

## 3. Four-Eyes Separation of Duties Governance

To prevent developer bias, self-certification, or unauthorized model deployments, the platform enforces strict role-based separation:

```python
# Enforced in app/ml/trainer.py
if approved_by and user_name:
    clean_user = user_name.split("(")[0].strip().lower()
    clean_approver = approved_by.split("(")[0].strip().lower()
    if clean_user == clean_approver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Separation of duties violation: Training requester cannot be the sole approving authority.",
        )
```

- **Developer Role (`ML_ENGINEER` / `DATA_SCIENTIST`):** Permitted to build pipelines, optimize hyperparameters, and submit training requests. Disallowed from unilaterally approving or deploying models.
- **Approver Role (`CHIEF_CREDIT_OFFICER` / `RISK_COMMITTEE_MEMBER`):** Permitted to review validation reports, inspect SHAP feature attributions, and authorize candidate models for production promotion.

---

## 4. Model Registry Architecture & Artifact Persistence

The platform manages models via the [`ml_models`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/models/ml_model.py) database table and filesystem artifact vault:

```
artifacts/models/
└── v1.0.1793895149/
    ├── model.cbm                # Compiled CatBoost binary artifact
    ├── metadata.json            # Model parameters, feature list, target
    ├── checksums.sha256         # SHA-256 Merkle root hash of all files
    ├── conformal_quantiles.json # Calibrated nonconformity scores (90% interval)
    └── validation_metrics.json  # MAE, RMSE, MAPE, MedAPE, R2
```

### Model Lifecycle States:
- **`BLOCKED`:** Model training was requested but safely aborted by the readiness gate due to prerequisite deficits (e.g. `BLOCKED-1793895149`).
- **`CANDIDATE`:** Model was successfully trained on certified data and passed initial benchmarks; awaiting independent risk validation.
- **`ACTIVE`:** Model has received risk committee approval and is serving live production valuation requests.
- **`DEPRECATED`:** Model has been superseded by a newly approved model version or rolled back.

---

## 5. Rollback Protocol & Version Management

If an active production model demonstrates performance degradation, distribution shift, or anomalous underwriter feedback:

### Rollback Procedure:
1. **Trigger:** Senior Underwriter or Risk Officer submits a rollback request via `POST /api/v1/ml/models/{version_id}/rollback`.
2. **Atomic Demotion:** The current active model's status is atomically changed to `DEPRECATED`, and its `is_production_ready` flag is set to `False`.
3. **Restoration:**
   - If a prior verified model version exists in the registry, it is promoted to `ACTIVE`.
   - If no prior ML model exists (as is the case currently), the platform immediately and seamlessly falls back to the **Statutory Rule-Based Baseline Engine**.
4. **Audit Trail:** An immutable audit block is chained into the `audit_events` ledger:
   ```json
   {
     "event_type": "EVENT_MODEL_ROLLED_BACK",
     "actor": "v.sundaram (CHIEF_CREDIT_OFFICER)",
     "demoted_model_version": "v1.0.1793895149",
     "active_engine": "STATUTORY_RULE_BASED_BASELINE",
     "rollback_reason": "Distributional drift detected in Q3 peripheral ward registrations."
   }
   ```

---

## 6. Audit Trail & Regulatory Compliance Summary

The PropVal AI model governance framework fully satisfies:
- **Federal Reserve SR 11-7 (Model Development, Implementation, and Use):** All model inputs, assumptions, and mathematical operations are documented and verifiable.
- **RBI Information Technology Governance (2023):** Clear audit logging of all automated decision tools and algorithmic models.
- **Fair Lending & Equal Credit Opportunity:** Conformal prediction intervals transparently signal high uncertainty rather than producing biased, arbitrary point valuations.

---

## 7. Sign-off & Institutional Governance Attestation

- **Pre-Training Gate Audit:** Verified and Enforced (**LOCKED**).
- **Production ML Model Count:** **0 Active Models**.
- **Active Valuation Engine:** Statutory Rule-Based Hedonic Engine (Phase 1 Baseline).
- **Separation of Duties:** Fully Implemented and Tested.
- **Model Registry Status:** Operational with 1 permanent `BLOCKED` audit record.

**Chief Credit Officer & Lead ML Engineer Attestation:**  
We hereby certify that no empirical machine learning model has been deployed into production. PropVal AI's machine learning readiness gate remains firmly locked until 1,000 unique certified empirical deeds are accumulated. The platform continues to operate with complete integrity on its rule-based baseline valuation engine.

