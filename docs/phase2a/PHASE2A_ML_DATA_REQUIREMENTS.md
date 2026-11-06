# Phase 2A: Machine Learning Data & Uncertainty Requirements

**Project:** PropVal AI (Hero Housing Fintech Challenge)  
**Document:** Machine Learning Data Architecture, CatBoost Evaluation Standards & Conformal Uncertainty  
**Version:** 1.0.0 (Phase 2A Technical Assessment)  
**Author:** Principal ML Engineer, Data Scientist & Fintech Technical Lead  
**Date:** November 2026  
**Operating System:** Windows  
**Shell Environment:** Windows PowerShell  
**Target Folder:** `docs/phase2a/PHASE2A_ML_DATA_REQUIREMENTS.md`  

---

## 1. Purpose, Assessment Scope & Evidence Framework

### 1.1 Purpose
This document specifies the technical data requirements, evaluation methodology, leakage prevention strategies, and uncertainty calibration frameworks necessary to build a genuine, statistically sound Automated Valuation Model (AVM) for PropVal AI. It establishes an evidence hierarchy that prevents unsupported accuracy claims and defines the mathematical roadmap for moving from heuristic deductions to calibrated prediction intervals.

### 1.2 Evidence Classification Rules
* **[VERIFIED]:** Mathematical facts, established statistical theorems, published machine learning literature, or verified repository code.
* **[ASSUMPTION]:** Applied ML engineering decisions tailored to the Indian real estate domain.
* **[UNRESOLVED]:** Empirical accuracy figures that can only be established after training on a real, ingested dataset.
* **[REQUIRES LEGAL REVIEW]:** Regulatory model risk management guidelines (RBI, NHB, Basel Committee on Banking Supervision principles for model risk).

---

## 2. Objective 6: Machine Learning Data & Evaluation Specification

### 2.1 Minimum Data Volume & Quality Considerations
Rather than fabricating an arbitrary record threshold, data volume must be evaluated against the dimensional complexity of Indian micro-markets [VERIFIED]:
* **Spatial Density over Raw Record Count:** An AVM does not train on a single homogeneous national market; it models thousands of heterogeneous micro-markets. Having 100,000 transactions scattered thinly across 200 cities yields lower predictive power than 5,000 dense transactions concentrated in a single high-velocity corridor (e.g., Whitefield, Bengaluru or Powai, Mumbai) [ASSUMPTION].
* **Feature Dimensionality & Degrees of Freedom:** For an $M$-parameter hedonic model (capturing floor level, age, road width, amenities, RERA area, and locality fixed effects), a micro-market requires at least 30–50 verified recent transactions per sub-locality cluster to achieve parameter convergence without severe overfitting [ASSUMPTION].
* **Noise and Outlier Density:** Indian registration data contains significant noise (unreported cash components, distressed distress sales, family distress transfers at nominal values). An effective training pipeline requires that at least 85% of records have verified carpet areas and realistic consideration-to-circle-rate ratios [ASSUMPTION].

### 2.2 Strict Data Separation & Leakage Prevention Strategies
Standard random train/test splits (e.g. Scikit-learn `train_test_split(shuffle=True)`) are **strictly prohibited** in real estate valuation due to multiple severe data leakage vectors [VERIFIED].

```
+--------------------------------------------------------------------------------------------------------------------+
| DATA LEAKAGE VECTORS & MANDATORY ARCHITECTURAL MITIGATIONS                                                         |
|                                                                                                                    |
| VECTOR 1: Temporal Lookahead Leakage                                                                               |
|   -> Risk: Model trains on future sales to predict past sales; inflated R² that collapses in live production.     |
|   -> Mitigation: Out-of-Time (OOT) Temporal Split. Train on Quarters Q1..Q(T-1); test strictly on Quarter QT.     |
|                                                                                                                    |
| VECTOR 2: Spatial Autocorrelation & Geographic Cluster Leakage                                                     |
|   -> Risk: Random split places Apartment 401 in train and Apartment 402 of the same tower in test.                 |
|            The model simply memorizes the building name rather than learning hedonic relationships.                |
|   -> Mitigation: Spatial Block Cross-Validation. Partition clusters by Project/Society and Pin Code.              |
|                                                                                                                    |
| VECTOR 3: Repeat-Sales & Near-Duplicate Leakage                                                                    |
|   -> Risk: Identical resale records of the same unit appearing across train and test sets.                         |
|   -> Mitigation: Property Fingerprinting. Deduplicate on (City, Locality, Project, Unit, Floor) before splitting.  |
+--------------------------------------------------------------------------------------------------------------------+
```

### 2.3 Baseline Models (Benchmark Hurdle)
Before any complex machine learning algorithm (e.g. CatBoost) is approved, it must demonstrate statistically superior predictive accuracy over two mandatory baselines [ASSUMPTION]:
1. **Baseline 1: Locality Median Price per Sq Ft:**
   $$\hat{y}_{\text{median}} = \text{CarpetArea} \times \text{MedianRate}(\text{Locality})$$
   A naive non-parametric benchmark representing basic market consensus.
2. **Baseline 2: Regularized Hedonic OLS (Ridge / Lasso Regression):**
   $$\hat{y}_{\text{linear}} = \text{CarpetArea} \times \left(\beta_0 + \beta_1 \text{CircleRate} + \beta_2 \text{Floor} + \beta_3 \text{RoadWidth} + \sum \gamma_j \text{Locality}_j\right)$$
   A transparent linear econometric model representing classical banking valuation methodologies.

### 2.4 CatBoost Suitability & Comparative Model Analysis
```
+--------------------------------------------------------------------------------------------------------------------+
| ALGORITHM EVALUATION FOR INDIAN REAL ESTATE VALUATION                                                              |
|                                                                                                                    |
| CatBoost Regressor (RECOMMENDED FIRST CHOICE):                                                                     |
|   * Strengths: Native, superior handling of high-cardinality categorical features (Locality, Builder, Project)     |
|     using target statistics calculated on random permutations without target leakage; resistant to overfitting     |
|     on small/medium datasets; built-in monotonic feature constraints (e.g. higher floor rise must not decrease PSF).|
|   * Weaknesses: Higher training memory footprint; slower inference than simple linear models.                      |
|                                                                                                                    |
| LightGBM / XGBoost (ALTERNATIVE CHOICE):                                                                           |
|   * Strengths: Extremely fast training and lightweight model artifacts; widespread industry support.              |
|   * Weaknesses: Requires manual target encoding or one-hot encoding for high-cardinality project names, which      |
|     drastically increases spatial leakage risk if not carefully isolated inside cross-validation folds.           |
|                                                                                                                    |
| Deep Neural Networks / TabNet (REJECTED FOR TABULAR HEDONIC AVM):                                                  |
|   * Strengths: High capacity for multi-modal fusion (combining inspection photos + tabular features).              |
|   * Weaknesses: Data-hungry; prone to extreme out-of-distribution hallucinations; completely uninterpretable       |
|     for bank credit committees and housing finance regulators.                                                     |
+--------------------------------------------------------------------------------------------------------------------+
```

### 2.5 Evaluation Metrics & Mathematical Limitations
Every model evaluation must report the following metric suite, acknowledging their mathematical trade-offs [VERIFIED]:

1. **Mean Absolute Error (MAE):**
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$$
   *Advantage:* Expressed in Indian Rupees (₹); highly interpretable by credit committees.  
   *Limitation:* Scales with property price; a ₹5 Lakh error on a ₹30 Lakh flat has the same penalty as on a ₹5 Crore luxury villa.

2. **Root Mean Squared Error (RMSE):**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$$
   *Advantage:* Heavily penalizes catastrophic appraisal outliers that could create systemic mortgage under-collateralization.  
   *Limitation:* Extremely sensitive to luxury property anomalies and corrupted registry records.

3. **Mean Absolute Percentage Error (MAPE):**
   $$\text{MAPE} = \frac{100\%}{N} \sum_{i=1}^N \left|\frac{y_i - \hat{y}_i}{y_i}\right|$$
   *Advantage:* Standard metric for international AVM benchmarks (e.g. Standard on Automated Valuation Models by IAAO).  
   *Mathematical Limitation:* Asymmetric penalty. Over-forecasting is penalized more heavily than under-forecasting. Dividing by small consideration values produces mathematical blowups.

4. **Coefficient of Determination ($R^2$):**
   $$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$
   *Limitation:* Highly sensitive to the variance of the sample. In luxury real estate with high price dispersion, $R^2$ can appear deceptively high (>0.90) even when individual flat valuations have unacceptable 20% errors.

5. **Mandatory Disaggregated Cohort Metrics:**
   Aggregate national metrics hide localized failure modes. All evaluations must disaggregate metrics:
   * *By Geography:* Separate MAPE for Bengaluru, Mumbai, Pune, Delhi-NCR.
   * *By Price Tier:* Affordable (<₹45L), Mid-Market (₹45L–₹1.5Cr), Luxury (>₹1.5Cr).
   * *By RERA Status:* Completed with OC vs Under Construction.

### 2.6 Accuracy Claim Evidence Hierarchy
To ensure institutional integrity, PropVal AI enforces strict wording constraints based on verified evidence:

```
+--------------------------------------------------------------------------------------------------------------------+
| ACCURACY CLAIM EVIDENCE HIERARCHY                                                                                  |
|                                                                                                                    |
| LEVEL 0 (Current State - Phase 1): Synthetic Demonstration Data                                                    |
|   -> Permitted Claim: "Provisional Rule-Based Estimation Prototype (Uncalibrated; Synthetic Demo Data)"           |
|   -> Prohibited Claims: Cannot publish MAPE, R², or claim predictive accuracy.                                     |
|                                                                                                                    |
| LEVEL 1: Backtested on Historical Guideline Rates Only                                                             |
|   -> Permitted Claim: "Guideline Consistency Score; reflects statutory Ready Reckoner alignment"                   |
|   -> Prohibited Claims: Cannot claim market accuracy or transaction price prediction.                             |
|                                                                                                                    |
| LEVEL 2: In-Sample Fit on Commercial Sample                                                                        |
|   -> Permitted Claim: "Preliminary Model Fit on Internal Sample (Not Independently Validated)"                     |
|   -> Prohibited Claims: Cannot claim generalization to live production loans.                                      |
|                                                                                                                    |
| LEVEL 3: Out-of-Time (OOT) Cross-Validated on Verified Registered Deeds                                            |
|   -> Permitted Claim: "Demonstrates X.X% Out-of-Time MAPE across [Named Metros] on Registered Deeds"               |
|   -> Prohibited Claims: Cannot claim zero bias across un-sampled sub-markets.                                      |
|                                                                                                                    |
| LEVEL 4: Multi-Bank Double-Blind Appraisal Benchmark                                                               |
|   -> Permitted Claim: "Production-Grade Institutional AVM with Validated Risk Coverage"                            |
+--------------------------------------------------------------------------------------------------------------------+
```
* **Strict UI Policy:** No accuracy figure (MAPE, $R^2$) may be rendered in the PropVal AI interface until produced by a verifiable, reproducible offline benchmark script executing on Level 3 or Level 4 data [VERIFIED].

---

## 3. Objective 7A: Uncertainty Architecture & Calibration

### 3.1 Comparison: Conformal Prediction vs. Quantile Regression
```
+--------------------------------------------------------------------------------------------------------------------+
| UNCERTAINTY QUANTIFICATION COMPARISON                                                                              |
|                                                                                                                    |
| Option A: Quantile Regression (e.g. CatBoost with LossFunction='Quantile:alpha=0.1,0.9')                           |
|   * Mechanism: Directly optimizes pinball loss to predict 10th and 90th percentiles.                                |
|   * Data Requirements: Requires sufficient training data in the tails.                                             |
|   * Guarantees: Asymptotic; NO finite-sample distribution-free coverage guarantee. Under covariate shift, coverage |
|     can severely degrade below 80%.                                                                                |
|   * Implementation Complexity: Low. Native to CatBoost.                                                            |
|                                                                                                                    |
| Option B: Split-Conformal Prediction (RECOMMENDED TARGET):                                                         |
|   * Mechanism: Uses a separate calibration set to compute non-conformity scores (residuals) and forms prediction    |
|     intervals using order statistics: $\hat{C}(x) = [\hat{\mu}(x) - q_{1-\alpha}, \hat{\mu}(x) + q_{1-\alpha}]$.   |
|   * Guarantees: Rigorous, finite-sample marginal coverage: $P(Y \in \hat{C}(X)) \ge 1 - \alpha$ under exchangeability|
|     (no distributional assumptions on real estate errors).                                                         |
|   * Limitations: Exchangeability assumption can be violated by strong temporal market shifts (price inflation).     |
|     Requires a dedicated calibration set (typically 1,000+ records) not used in model training.                   |
|   * Implementation Complexity: Moderate. Requires separate calibration pipeline.                                   |
+--------------------------------------------------------------------------------------------------------------------+
```

### 3.2 Recommended Staged Uncertainty Roadmap
* **Stage 1 (Current Phase 1): Heuristic Rule Penalty Index:**
  * Label: `"Rule Consistency Score: 85.0% (Uncalibrated Heuristic Penalty Index)"`.
  * Display: `"Calibrated Uncertainty: Not available: no calibrated model"`.
* **Stage 2 (Phase 2D): Empirical Residual Band:**
  * Once a real dataset is ingested, compute the historical standard deviation of residuals by micro-market and display an empirical indicative band:
    $$\text{Indicative Range} = \hat{y} \pm 1.645 \times \hat{\sigma}_{\text{locality}}$$
  * Labeled clearly: `"Empirical Residual Band (Non-Conformal)"`.
* **Stage 3 (Phase 2E): Locally-Weighted Split-Conformal Prediction:**
  * Implement normalized conformal prediction where non-conformity scores are scaled by local variance:
    $$s_i = \frac{|y_i - \hat{\mu}(x_i)|}{\hat{\sigma}(x_i)}$$
  * Delivers exact 90% marginal coverage intervals: $[\hat{y}_{\text{lower}}, \hat{y}_{\text{upper}}]$.

### 3.3 Strict Separation of Uncertainty Concepts in API & UI
To prevent misleading loan committees, the four concepts below must **never** be blended into a single generic "confidence score":

```
+--------------------------------------------------------------------------------------------------------------------+
| DISTINCT UNCERTAINTY CONCEPTS (API & UI DATA CONTRACT)                                                             |
|                                                                                                                    |
| 1. DATA COMPLETENESS INDEX (Input Completeness):                                                                   |
|    * Measures: What percentage of relevant appraisal attributes were provided by the applicant vs imputed.        |
|    * Formula: (Provided Fields / Total Model Fields) * 100%. Range: 0% to 100%.                                    |
|    * Example UI Label: "Data Completeness: 92% (11 of 12 fields verified)".                                        |
|                                                                                                                    |
| 2. EVIDENCE COVERAGE SCORE (Spatial Support):                                                                      |
|    * Measures: The density, distance, and freshness of nearby comparables.                                         |
|    * Formula: Decay function based on distance and age of nearest 5 comparables.                                  |
|    * Example UI Label: "Evidence Coverage: High (5 comparables within 800m transacted in past 90 days)".          |
|                                                                                                                    |
| 3. MODEL UNCERTAINTY (Epistemic / Variance Spread):                                                                |
|    * Measures: The model's internal variance or distance from training distribution.                              |
|    * Formula: Spread of predictions across tree ensemble or normalized non-conformity quantile.                   |
|    * Example UI Label: "Model Uncertainty: Moderate (Ensemble variance +/- 4.2%)".                                 |
|                                                                                                                    |
| 4. PREDICTION INTERVAL (Calibrated Value Bound):                                                                   |
|    * Measures: The statistically calibrated monetary range within which the true value lies with 90% confidence.  |
|    * Metric: [₹1,36,00,000 to ₹1,48,50,000] (90% Calibrated Conformal Band).                                       |
|    * Example UI Label: "90% Calibrated Interval: ₹1.36 Cr - ₹1.48 Cr (Coverage Guaranteed under Exchangeability)".  |
+--------------------------------------------------------------------------------------------------------------------+
```

---

## 4. Open Questions Requiring Human & Sponsor Decision

1. **CatBoost vs Scikit-learn Baseline First:** Does the technical evaluation panel prefer seeing a simple linear baseline running first in Phase 2B, or should we jump straight to CatBoost in Phase 2D?
2. **Conformal Calibration Set Source:** If the project obtains a dataset of 5,000 real transactions, should we partition 3,500 for training, 500 for validation, and 1,000 strictly for conformal interval calibration?
3. **Acceptable Interval Width for Underwriting:** For housing loans, what is the maximum acceptable prediction interval width (e.g. $\pm 7.5\%$ or $\pm 10\%$) before a case must be automatically flagged for physical human inspection?

