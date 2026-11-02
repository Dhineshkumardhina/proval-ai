# PropVal AI — Digital Property Valuation Engine for India

**Competition:** Hero Housing Fintech Challenge  
**Problem Statement:** Problem Statement 1 — AI-Powered Digital Property Valuation Engine for India  
**Status:** Phase 1 Prototype (Credibility Remediated & Audited)

---

## 1. Executive Summary

PropVal AI is a specialized valuation and collateral risk appraisal prototype built for Indian Housing Finance Companies (HFCs) and bank credit committees. It combines micro-market comparable tracking, spatial GIS visualization, cadastral layout inspection, title discrepancy flagging, and explainable hedonic valuation scorecard rules.

### Prototype Transparency & Integrity Notice
* **Engine Type:** Deterministic rule-based hedonic valuation engine (`src/utils/valuationEngine.ts`). It is **not** a trained black-box machine learning model.
* **Data Sources:** All properties, borrower profiles, registry deed records, and survey photos are **synthetic demonstration data** crafted for UI and workflow evaluation. Live government SRO APIs (e.g., Kaveri 2.0, TNREGINET) are simulated in this prototype.
* **Confidence & Uncertainty:** The reported confidence score is a deterministic rule-based heuristic based on circle-rate deviation and title discrepancies, rather than a statistically calibrated Bayesian or conformal prediction interval.
* **Governance Status:** The governance module presents an architectural blueprint and design specification targeting alignment with NHB & RBI guidelines; it does not claim external regulatory certification.

---

## 2. Core Functional Modules

1. **Valuation Studio (`ValuationStudio`):**
   * High-density collateral metrics: Net Assessed Value, Circle Rate Deviation, Distress Liquidation Value, and Maximum Sanction under NHB LTV bounds.
   * Split-screen analytical canvas: Interactive GIS spatial proximity rings, Title & OCR document verification matrix, and physical survey evidence frames.
   * Hedonic Scorecard Waterfall (`XaiAttributionWaterfall`): Decomposes adjustments across Floor Rise, Master Road Access, Gated Amenities, and Vintage Depreciation.
   * Sub-Market Comparables Grid (`ComparablesGrid`): Distance filtering (500m / 1km / 2km) and comparable deed inspection.
   * Underwriter Controls (`UnderwriterControls`): Interactive haircut sliders, distress discount tuning, and policy overrides.
   * Formal Collateral Valuation Memo Modal (`ValuationCertificateModal`).

2. **Underwriting Pipeline (`UnderwritingPipeline`):**
   * Multi-metro portfolio monitoring across 6 key Indian real estate hubs (Bengaluru, Mumbai, Delhi-NCR, Hyderabad, Pune, Chennai).
   * Filtering by risk stage, circle rate spread, and title encumbrance status.

3. **Risk & Collateral Audit Console (`RiskAuditDashboard`):**
   * Macro price correction shock simulator (-5% to -25%).
   * Deterministic scenario collateral loss sensitivity (clarified from statistical VaR misnomers).
   * Stressed Book LTV tracking under market downturns.
   * Dual audit tab for High Circle Rate Spreads (>15%) and Active Legal Title Charges.

4. **Model Governance Blueprint (`ModelGovernanceView`):**
   * Transparent prototype state indicators (Pending Evaluation / Not Configured / In-Memory Audit).
   * Indicative scorecard factor weighting target blueprint.

---

## 3. Getting Started

### Prerequisites
* Node.js (v18+ or v20+ recommended)
* npm (v9+)

### Installation & Execution
```bash
# 1. Install dependencies
npm install

# 2. Run unit tests
npm test

# 3. Type-check TypeScript code
npm run lint

# 4. Build production bundle
npm run build

# 5. Start development server
npm run dev
```

---

## 4. Engineering Verification

| Check | Tool / Command | Result |
| :--- | :--- | :--- |
| **Unit Testing** | `npm test` (`tsx --test`) | 5/5 tests passing |
| **TypeScript Validation** | `npm run lint` (`tsc --noEmit`) | 0 type errors |
| **Production Build** | `npm run build` (`vite build`) | Clean build in ~300ms |

