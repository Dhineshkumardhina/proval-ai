# PropVal AI — Phase 6F: Conformal Prediction & Statistical Calibration Report

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6F — Empirical CatBoost Training & Model Certification  
**Date:** 2026-11-05  
**Author:** Quantitative Risk Modeling Specialist & Conformal Prediction Engineer  
**Calibration Gate Status:** **GATED / INACTIVE (Requires Active Empirical ML Model)**

---

## 1. Conformal Prediction Theoretical Framework

PropVal AI implements **Split-Conformal Prediction** (Vovk et al., Angelopoulos & Bates) to deliver distribution-free, finite-sample valid prediction intervals for property valuation.

Unlike heuristic confidence intervals or Gaussian assumptions, conformal prediction provides a rigorous mathematical coverage guarantee under the exchangeability assumption:

$$P\left(Y_{n+1} \in \hat{C}(X_{n+1})\right) \ge 1 - \alpha$$

Where:
* $1 - \alpha$ is the target marginal coverage rate (standard: $90\%$, $\alpha = 0.10$).
* $\hat{C}(X) = [\hat{y}(X) - \hat{q}_{1-\alpha}, \hat{y}(X) + \hat{q}_{1-\alpha}]$ is the calibrated prediction interval.
* $\hat{q}_{1-\alpha}$ is the finite-sample adjusted empirical quantile of non-conformity scores computed on an independent calibration split:

$$\hat{q}_{1-\alpha} = \text{Quantile}\left(s_1, \dots, s_n; \frac{\lceil(n+1)(1-\alpha)\rceil}{n}\right)$$

---

## 2. Calibration Prerequisites & Gate Verification

Under PropVal AI Statistical Governance Policy §5.3, conformal calibration cannot be computed on uncalibrated heuristics or synthetic test cases. The calibration pipeline enforces three strict gates:

| Calibration Gate Criterion | Standard Requirement | Current System State | Gate Audit |
|:---|:---:|:---:|:---:|
| **Active Validated Model** | Approved empirical ML model in `ml_models` | `BLOCKED` (0 active empirical models) | **BLOCKED** |
| **Independent Calibration Partition** | $N_{cal} \ge 150$ certified empirical deeds | Partition pending dataset expansion | **BLOCKED** |
| **Target Coverage Target** | Coverage $\ge 90.0\%$ at $\alpha = 0.10$ | Calibration run blocked | **GATED** |
| **Subgroup Exchangeability** | Balanced coverage across property typologies | Unverified pending empirical data | **GATED** |

### Verified by Test Suite
As verified in `test_conformal_calibration_blocked_without_active_model` (`backend/tests/test_empirical_training_phase6f.py`), calling the conformal prediction service without an approved empirical model returns `None` and safely falls back to the deterministic risk haircut scorecard.

---

## 3. Asymmetric Liquidation Bounds for Credit Underwriting

For mortgage lending and collateral appraisal, symmetric intervals are insufficient because overvaluation risk is financially catastrophic to lenders.

PropVal AI defines an asymmetric non-conformity score:
1. **Upper Bound (Max Market Ceiling):** $\hat{y} + \hat{q}_{upper}$, identifying peak market bubble exposure.
2. **Lower Bound (Distress Liquidation Value):** $\hat{y} - \hat{q}_{lower}$, calibrated at a 95% conservative confidence floor ($1 - \alpha = 0.95$). This floor governs maximum loan sanction amounts ($LTV \times \text{Lower Bound}$).

---

## 4. Subgroup Conditional Coverage Monitoring Plan

Once empirical calibration is active, the system will execute automated subgroup conditional coverage audits:
* **Micro-Market Conditional Coverage:** Measuring whether peripheral suburbs achieve the same 90% coverage as prime localities.
* **Property Typology Coverage:** Ensuring standalone villas (which exhibit higher price dispersion) receive appropriately wider prediction intervals than homogeneous multi-story apartments.
* **Interval Width Efficiency:** Evaluating mean prediction interval width (MPIW) to verify that coverage is achieved through precision rather than uninformative excessively wide bands.

