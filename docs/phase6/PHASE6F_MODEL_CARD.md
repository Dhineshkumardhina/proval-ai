# PropVal AI — Phase 6F: Model Card (Candidate Valuation Architecture)

**Model Name:** PropVal AI Empirical CatBoost Real-Estate Valuation Regressor  
**Model Version:** `v0.2.0-candidate` (`BLOCKED-1793895149` in registry)  
**Date:** 2026-11-05  
**Type:** Gradient Boosted Decision Trees on Oblivious Trees (`CatBoostRegressor`)  
**Deployment Status:** **INACTIVE / GATED (Deterministic Rule-Based Fallback Serving All Requests)**  
**License:** Proprietary Institutional Fintech  

---

## 1. Intended Use & Target Users

* **Primary Intended Use:** Automated Collateral Valuation (AVM), loan-to-value (LTV) verification, and credit risk haircut estimation for Indian Housing Finance Companies (HFCs) and Non-Banking Financial Companies (NBFCs).
* **Target Users:** Institutional Underwriters, Chief Risk Officers (CROs), Property Appraisers, and Internal Credit Audit Committees.
* **Out-of-Scope Uses:**
  * Speculative retail real-estate trading.
  * Commercial office or industrial complex appraisals (the architecture is scoped to residential property typologies).
  * Automated unassisted loan sanctioning without qualified human underwriter review.

---

## 2. Training Data & Dataset Requirements

* **Target Training Corpus:** $\ge 1,000$ unique empirical registered deed transactions certified by SRO Index II filings.
* **Current Certified Register Volume:** **140 unique approved deeds** (364 staged records across DB).
* **Deficit to Certification:** **860 records**.
* **Target Geographic Coverage:**
  * Bengaluru (Tier-1 IT corridors and residential micro-markets).
  * Mumbai Metropolitan Region (MMR).
  * Delhi-NCR (Gurugram, Noida, New Delhi).
  * Hyderabad (Hitec City, Gachibowli, Kondapur).
* **Target Architectural Typologies:**
  * Apartments / Multi-story residential flats.
  * Independent houses / Builder floors.
  * Gated community villas.
  * Residential plots.

---

## 3. Factors & Subgroup Performance Evaluation Plan

When empirical training is executed upon dataset threshold achievement, performance must be disaggregated and reported across key subgroups:
1. **By City & Micro-Market:** Verifying that model accuracy does not degrade in lower-volume micro-markets (e.g. peripheral suburban corridors vs established central business districts).
2. **By Property Typology:** Separate error metrics for high-density apartments vs unique independent structures.
3. **By Ticket Size (Valuation Tiers):**
   * Affordable Housing ($\le ₹45 \text{ Lakhs}$).
   * Mid-Market ($₹45 \text{ Lakhs} - ₹1.5 \text{ Crores}$).
   * Premium / Luxury ($> ₹1.5 \text{ Crores}$).
4. **By Circle Rate Deviation:** Detecting properties transacting near or below government circle rate guidance values.

---

## 4. Ethical Considerations, Fairness & Regulatory Compliance

* **Fair Lending & Anti-Redlining:** The model feature set strictly excludes borrower demographics, religion, caste, gender, marital status, or socio-economic indicators. Only objective physical, structural, and spatial property characteristics are ingested.
* **Under-collateralization Protection:** Financial safety is prioritized by combining point predictions with asymmetric conformal prediction lower bounds ($q_{0.05}$ or $q_{0.10}$ distress liquidation value).
* **Advisory Principle:** All valuation estimates output by PropVal AI carry explicit machine-readable metadata mandating human underwriter concurrence before loan sanction.

---

## 5. Model Limitations & Caveats

* **Empirical Training Gate Active:** Because the certified training dataset currently contains fewer than 1,000 records, **no empirical ML model is currently active in production**.
* **Active Production Engine:** The system currently serves all valuation calculations through the deterministic hedonic scorecard engine (`provisional rule-based estimation v0.2.0`).
* **Uncalibrated ML Claims Blocked:** The system will not output ML prediction intervals or CatBoost feature attributions until the model passes independent validation.

