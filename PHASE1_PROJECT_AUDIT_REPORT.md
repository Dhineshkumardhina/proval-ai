# Phase 1: Project Audit Report — PropVal AI

**Project:** PropVal AI (Hero Housing Fintech Challenge)  
**Role:** Senior Frontend Engineer & Technical Lead  
**Audit Scope:** Credibility, Veracity, and Architectural Audit of Existing Codebase  
**Date:** November 2026  
**Auditor Environment:** Windows (PowerShell)  
**Branch:** `phase1-credibility-remediation`  
**Starting Commit:** `ea2d6966086421469e17a6dcce993c21b7473d49`  

---

## 1. Executive Summary

A comprehensive, evidence-based technical and credibility audit was conducted on the PropVal AI React + TypeScript codebase. PropVal AI is designed as a digital property valuation and collateral appraisal engine for Indian Housing Finance Companies (HFCs) and bank credit committees.

The audit verified that the application possesses a functional, high-density financial appraisal user interface and a working deterministic valuation math engine. However, the codebase contained significant **credibility discrepancies**, including:
1. Branding and UI copy claiming "AI-Powered", "algorithmic hedonic model", and "XAI Engine" when the underlying logic is entirely a deterministic rule-based calculation.
2. An uncalibrated heuristic penalty score presented with percentage formatting that could be mistaken for statistical confidence or calibrated predictive certainty.
3. Completely synthetic demonstration records and mock SRO extracts styled to resemble official statutory government records from state registration departments without machine-readable markers.
4. A claimed SHA-256 cryptographic audit ledger that was actually a hardcoded static text string with no hashing implementation.
5. Unconnected Gemini API dependencies in `package.json` with zero actual API calls or network integrations in application code.

Preserving existing working functionality was maintained as the highest priority throughout. No UI architectures were rebuilt, no external databases or fake backend endpoints were added, and no calculation mathematics were altered.

---

## 2. Step 0: Baseline & Safety Verification

All commands in this section were executed in **Windows PowerShell**.

### 2.1 Git Version Control & Working State
* **Git Repository Status:** Initialized git repository. Prior to audit, untracked files were present with no commits.
* **Safety Baseline Established:** All untracked files were cleanly staged and committed to branch `main` as baseline commit `ea2d6966086421469e17a6dcce993c21b7473d49` (`chore: initial baseline before phase 1 audit`).
* **Audit Working Branch:** Created and checked out working branch `phase1-credibility-remediation`.

### 2.2 Package Manager Detection
* **Detection:** Detected `package-lock.json` (151 KB) in repository root.
* **Package Manager Used:** `npm` (v10+ / Node.js v22).

### 2.3 Baseline Command Executions & Outputs
Before applying any edits, all existing `package.json` scripts were executed in PowerShell to record baseline performance:

1. **Lint / Type-Check (`npm run lint` -> `tsc --noEmit`):**
   * Command: `npm run lint`
   * Shell: PowerShell
   * Exit Code: 0
   * Result: Passed with 0 TypeScript compilation errors.

2. **Unit Test Suite (`npm test` -> `tsx --test src/utils/valuationEngine.test.ts`):**
   * Command: `npm test`
   * Shell: PowerShell
   * Exit Code: 0
   * Result: 5 tests passed, 0 failed, duration ~156ms.
     * `✔ formatIndianNumber groups digits using Indian numeral system`
     * `✔ formatIndianCurrency formats full and short (Lakh / Crore) modes`
     * `✔ calculateValuation computes correct gross, haircut, liquidation and sanction values`
     * `✔ calculateValuation handles edge cases: zero area and zero circle rate safely`
     * `✔ calculateValuation applies confidence penalties and assigns HIGH_ALERT risk tier`

3. **Production Build (`npm run build` -> `vite build`):**
   * Command: `npm run build`
   * Shell: PowerShell
   * Exit Code: 0
   * Result: Built successfully in 687ms (`dist/index.html` 1.43 kB, `dist/assets/index-CzUEo8Kw.css` 34.91 kB, `dist/assets/index-CWMhsNhg.js` 343.98 kB).

### 2.4 Secrets and API Key Audit
* **Scan Scope:** Recursively scanned all repository files (excluding `node_modules`, `.git`, and `dist`) using regex patterns for Google API keys, Bearer tokens, secrets, and private keys.
* **Findings:**
  * File `.env.example`, Line 5: Comment placeholder `# GEMINI_API_KEY: Optional starter placeholder for future Gemini API extensions.`
  * File `.env.example`, Line 7: `GEMINI_API_KEY="MY_GEMINI_API_KEY"` (safe dummy placeholder).
  * No live, active, or private secrets were detected anywhere in tracked or untracked repository code.

---

## 3. Project Architecture & File Inventory

The application is structured as a client-side React 19 Single Page Application built with Vite 8 and Tailwind CSS 4.

### 3.1 Source File Inventory (21 Files in `src/`)

| Path | Purpose & Responsibility |
| :--- | :--- |
| `src/main.tsx` | React 19 client bootstrap (`createRoot`). |
| `src/App.tsx` | Application state root: tab switching, case state management, appraisal status handler. |
| `src/index.css` | Tailwind CSS 4 imports, theme CSS custom variables, tabular-nums font configuration. |
| `src/types/valuation.ts` | TypeScript domain interfaces (`ValuationCase`, `ComparableDeed`, `ValuationResult`, risk tiers, case statuses). |
| `src/utils/valuationEngine.ts` | Deterministic valuation calculation, Indian currency formatting, heuristic penalty computation. |
| `src/utils/valuationEngine.test.ts` | Node.js built-in test runner suite executed via `tsx --test`. |
| `src/data/mockValuationData.ts` | 6 synthetic collateral valuation cases across Bengaluru, Mumbai, Delhi-NCR, Hyderabad, Pune, Chennai. |
| `src/components/Header.tsx` | Global top navigation bar with active case selector, new intake trigger, underwriter profile. |
| `src/components/Sidebar.tsx` | 260px institutional left sidebar with module navigation, active case switcher, version footer. |
| `src/components/NewCaseModal.tsx` | Modal form for ingesting new property records into the active evaluation pipeline. |
| `src/components/Pipeline/UnderwritingPipeline.tsx` | Multi-metro portfolio table with search, filters (city, risk status), and aggregate metrics. |
| `src/components/ValuationStudio/ValuationStudio.tsx` | Main appraisal workspace split-screen view with KPI cards, sub-tabs, and underwriter controls. |
| `src/components/ValuationStudio/GisMapCanvas.tsx` | SVG cadastral/satellite spatial canvas rendering concentric radius rings, subject parcel, and comp pins. |
| `src/components/ValuationStudio/DocumentOcrViewer.tsx` | Verification matrix comparing declared property attributes against simulated SRO Index extracts. |
| `src/components/ValuationStudio/FieldSurveyViewer.tsx` | Physical field inspection viewer displaying photos, GPS coordinates, and surveyor notes. |
| `src/components/ValuationStudio/XaiAttributionWaterfall.tsx` | Additive hedonic adjustments waterfall displaying micro-market, floor rise, road, amenities, and age adjustments. |
| `src/components/ValuationStudio/ComparablesGrid.tsx` | Interactive table of nearby comparables with distance radius filtering (500m/1km/2km) and deed modal. |
| `src/components/ValuationStudio/UnderwriterControls.tsx` | Underwriter policy override sliders (haircut, distress liquidation discount, LTV cap) and committee referral. |
| `src/components/ValuationStudio/ValuationCertificateModal.tsx` | Formal valuation memo preview, printing, PDF export, and underwriter sign-off modal. |
| `src/components/RiskAudit/RiskAuditDashboard.tsx` | Collateral risk monitoring console with macro price shock slider (-5% to -25%) and breach filters. |
| `src/components/ModelGovernance/ModelGovernanceView.tsx` | Governance blueprint display showing model version, target guidelines, and performance KPI states. |

---

## 4. Component-to-Metric & Claim Mapping

Every number, metric, and analytical claim displayed in the UI was inspected to identify its true source:

| UI Component | Displayed Metric / Claim | Actual Code Source | Classification |
| :--- | :--- | :--- | :--- |
| `ValuationStudio` | Net Assessed Value (`netAssessedValue`) | Formula in `calculateValuation`: `grossMarketValue * (1 + haircut) * (1 - legalPenalty)` | **Computed** (Deterministic) |
| `ValuationStudio` | Heuristic Confidence (`confidenceScorePct`) | Formula: `baseConfidence(95.5) - circleRatePenalty - legalPenalty` | **Computed** (Heuristic Deduction, Uncalibrated) |
| `ValuationStudio` | Rate / sq ft Carpet | Formula: `netAssessedValue / carpetAreaSqFt` | **Computed** (Deterministic) |
| `ValuationStudio` | Rate / sq ft SBUA | Formula: `netAssessedValue / superBuiltUpAreaSqFt` | **Computed** (Deterministic) |
| `ValuationStudio` | Circle Rate Deviation % | Formula: `((adjustedRate - circleRate) / circleRate) * 100` | **Computed** (Deterministic) |
| `ValuationStudio` | Max Loan Sanction | Formula: `netAssessedValue * (ltvRatioPct / 100)` | **Computed** (Deterministic) |
| `XaiAttributionWaterfall` | Micro-Market Baseline Rate | `baseMarketRatePerSqFt` from case input data | **Mock Data** |
| `XaiAttributionWaterfall` | "SRO registered median sales within 1.0 km" | Hardcoded string in `valuationEngine.ts` line 158 | **Unsupported Claim** |
| `XaiAttributionWaterfall` | Floor Rise Adjustment | `floorRiseFactor` parameter | **Mock Data / Input** |
| `XaiAttributionWaterfall` | Road Width Adjustment | `roadWidthFactor` parameter | **Mock Data / Input** |
| `XaiAttributionWaterfall` | Gated Amenities Premium | `amenitiesPremium` parameter | **Mock Data / Input** |
| `XaiAttributionWaterfall` | Vintage Depreciation | `structuralDepreciation` parameter | **Mock Data / Input** |
| `ComparablesGrid` | 5 Nearby Comparables | `currentCase.comparables` array in `mockValuationData.ts` | **Mock Data** (Synthetic) |
| `ComparablesGrid` | "Official SRO Deed Extract" | Tooltip in `ComparablesGrid.tsx` line 135 | **Unsupported Claim** |
| `ComparablesGrid` | Model Weight % | Hardcoded `weightInEstimate` property on comparable | **Mock Data** (Static float) |
| `DocumentOcrViewer` | "GOVERNMENT OF KARNATAKA / MAHARASHTRA" | Hardcoded template header in `DocumentOcrViewer.tsx` line 158 | **Misleading Styling** |
| `DocumentOcrViewer` | OCR Matched Fields | Hardcoded `documentFields` array with simulated text | **Mock Data** (Static) |
| `DocumentOcrViewer` | "VERIFIED" Badges | Green badges in table line 136 | **Misleading Badge** |
| `ValuationCertificateModal` | "SHA-256: simulated-8f4b7a1290ed31c890f92ab8" | Hardcoded string literal in modal line 161 | **Unsupported Claim** (No hashing code) |
| `ValuationCertificateModal` | "cryptographically logged" | Hardcoded toast notification in `ValuationStudio.tsx` line 84 | **Unsupported Claim** |
| `RiskAuditDashboard` | Simulated Stress Loss | Formula: `totalOriginalAssessed * (macroShockPct / 100)` | **Computed** (Linear sensitivity, NOT statistical VaR) |
| `RiskAuditDashboard` | Stressed Book LTV | Formula: `75 / (1 - macroShockPct / 100)` | **Computed** (Deterministic ratio) |
| `ModelGovernanceView` | Training Corpus | Text: "Not Configured / Deterministic rules" | **Supported Truth** |
| `ModelGovernanceView` | MAPE / R-squared | Text: "Not Yet Measured / Pending Evaluation" | **Supported Truth** (Uncalibrated) |
| `ModelGovernanceView` | Audit Trail | Text: "Local Prototype / In-memory log" | **Supported Truth** |

---

## 5. Detailed Findings by Area

### 5.1 Valuation Engine Audit (`src/utils/valuationEngine.ts`)
* **Finding:** The valuation engine is 100% deterministic arithmetic. It evaluates property value using:
  $$\text{Adjusted Rate} = \max\left(1000, \text{BaseRate} + \text{FloorRise} + \text{RoadWidth} + \text{Amenities} - |\text{Depreciation}|\right)$$
  $$\text{Gross Market Value} = \text{Adjusted Rate} \times \text{CarpetAreaSqFt}$$
  $$\text{Net Assessed Value} = \text{Gross Market Value} \times (1 + \text{Haircut}) \times (1 - \text{LegalPenalty})$$
* **No Machine Learning:** There are zero model weights, zero PyTorch/TensorFlow/ONNX artifacts, zero inference calls, and zero regression coefficients.
* **Misleading Artifacts:** The internal variable and property name was `aiAdjustedRatePerSqFt`, and UI labels repeatedly used "AI Engine" or "Algorithmic appraisal".

### 5.2 Confidence & Uncertainty (`src/utils/valuationEngine.ts`)
* **Finding:** The confidence score (`confidenceScorePct`) is computed deterministically:
  ```ts
  let baseConfidence = 95.5;
  if (Math.abs(deviationFromCircleRatePct) > 35) baseConfidence -= 10.0;
  else if (Math.abs(deviationFromCircleRatePct) > 20) baseConfidence -= 4.2;
  if (safeLegalPenaltyPct > 0) baseConfidence -= 8.5;
  ```
* **Credibility Issue:** This is a rule-based penalty deduction measuring guideline rate variance and legal risk flags. It does **not** represent statistically calibrated uncertainty, a standard deviation, a Bayesian posterior, or a conformal prediction interval.
* **Remediation Requirement:** Relabel as a heuristic consistency index and state clearly that calibrated uncertainty is "Not available: no calibrated model".

### 5.3 Model Governance & Regulatory Claims
* **SHA-256 Audit Hashing:** `ValuationCertificateModal.tsx` displayed `SHA-256: simulated-8f4b7a1290ed31c890f92ab8 (Mock)`. No crypto library or `crypto.subtle.digest` call exists in the codebase.
* **Certifications:** No third-party certification or regulatory accreditation (RBI, NHB, RICS) has occurred.
* **Benchmark Metrics (MAPE, R²):** Currently unmeasured because no empirical dataset of real Indian registry transactions has been evaluated against the engine.

### 5.4 Demonstration Data (`src/data/mockValuationData.ts`)
* **Finding:** The 6 collateral files and associated comparables are synthetic samples created for UI demonstration.
* **Credibility Issue:** Prior to remediation, records lacked an explicit machine-readable field indicating synthetic origin. Document OCR extracts contained language such as "Verified against Kaveri 2.0 DB" and "Verified in IGR Maharashtra", implying active integration with state land record portals.

### 5.5 Comparable Properties
* **Finding:** Comparables are static synthetic objects stored in an in-memory array.
* **Credibility Issue:** In `valuationEngine.ts` line 158, the baseline rate factor description claimed: `"SRO registered median sales within 1.0 km radius in past 180 days"`. In `ComparablesGrid.tsx`, a button tooltip claimed `"View Official SRO Deed Extract"`. These statements falsely implied real-world registration evidence.

### 5.6 Risk Audit Dashboard
* **Finding:** The portfolio stress test simulates a fixed price shock (-5% to -25%) and computes linear loss:
  $$\text{Loss} = \text{Portfolio Collateral} \times \frac{\text{Shock \%}}{100}$$
* **Terminology Check:** The code comment in `RiskAuditDashboard.tsx` noted "not statistical VaR", but the section was titled "Portfolio Stress Testing & LTV Shock Matrix", which could be confused with econometric stress models or parametric Value-at-Risk.

### 5.7 AI (Gemini) Integration
* **Package Check:** `@google/genai: ^2.4.0` is present in `package.json`.
* **API Call Site Check:** Grepped all source code for `@google/genai`, `GoogleGenAI`, `gemini`, `generateContent`, and HTTP `fetch` calls. Zero occurrences found in `src/`.
* **Configuration:** `.env.example` has a placeholder `GEMINI_API_KEY="MY_GEMINI_API_KEY"`. No browser-reachable `VITE_` prefixed key exists.
* **Status:** Completely unconnected. All UI elements with "AI" badges are actually calling the local deterministic valuation engine.

---

## 6. Security Findings

1. **Client-Side API Key Architecture (Phase 2 Warning):**
   * While no `VITE_GEMINI_API_KEY` is currently defined in code, developers implementing Gemini in Phase 2 must avoid calling Google GenAI directly from browser components, as client-side Vite builds bundle environment variables starting with `VITE_` into public JavaScript assets.
   * **Recommendation:** All future LLM or Gemini integrations must be routed through an authenticated backend service (BFF pattern).

2. **No Secret Leaks:**
   * No active private keys, database credentials, or third-party service tokens exist in the repository.

---

## 7. Audit Conclusion & Remediation Plan

The PropVal AI codebase provides a robust, responsive, and well-organized frontend for housing finance appraisals. The calculations themselves are deterministic, safe, bounded, and regression-tested. To align the application with professional engineering and financial transparency standards, Phase 1 requires surgical remediation of misleading copy, explicit labeling of synthetic data, removal of fake cryptographic claims, and honest representation of model uncertainty and governance states.

