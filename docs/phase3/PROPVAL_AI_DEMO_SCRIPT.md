# PropVal AI — Step-by-Step Institutional Demonstration Script

**Document:** Institutional Demonstration Runbook & Presenter Script  
**Target Audience:** Bank Executives, Chief Credit Officers (CCOs), Chief Risk Officers (CROs), Model Governance Committees  
**Platform Version:** PropVal AI v0.2.0  
**Estimated Run Time:** 15 – 20 Minutes  

---

## 1. Demonstration Preparation Checklist

Before initiating the executive presentation:

1. **Verify Backend Status:**
   - Confirm backend is running on `http://localhost:8000`.
   - Test probe: `curl http://localhost:8000/health/live` returns `{"status": "alive"}`.
2. **Verify Frontend Status:**
   - Confirm frontend is running on `http://localhost:3000` or via production proxy on port `8080`.
3. **Seeded Account Credentials:**
   - **Senior Underwriter (Primary Presenter):** `v.sundaram` / `SrUnderwriter@2026!`
   - **Credit Underwriter (Junior Persona):** `underwriter` / `CreditUnderwriter@2026!`
   - **Risk Committee Member (Governance Persona):** `committee` / `RiskCommittee@2026!`
   - **Administrator (System Persona):** `admin` / `SystemAdmin@2026!`
4. **Data Reset (Optional Pre-Flight):**
   - If previous test runs modified records, execute:
     `py backend/scripts/reset_demo_env.py` to restore the 6 canonical demonstration cases.

---

## 2. 15-Step Repeatable Demonstration Script

### Step 1: Officer Login & Persona Authentication (0:00 - 1:30)
- **Presenter Action:** Open browser to `http://localhost:3000`. Log in with username `v.sundaram` and password `SrUnderwriter@2026!`.
- **Narrative:** *"Notice that PropVal AI enforces strict institutional authentication. There are no client-side mock sessions; every authentication request yields an RFC 7519 HS256 JWT signed server-side with 12-round bcrypt salted password verification."*
- **Visual Callout:** Note the active user header badge showing `V. Sundaram (Sr. Underwriter - Tech Risk)`.

### Step 2: Risk & Audit Portfolio Dashboard (1:30 - 3:00)
- **Presenter Action:** Click the **Risk & Audit** tab in the top navigation bar.
- **Narrative:** *"Before drilling into individual properties, senior credit risk officers view portfolio concentration. Here we see real-time LTV distribution heatmaps, high-risk collateral alerts, and micro-market geographic clusters across Bengaluru, Mumbai, Hyderabad, and Chennai."*
- **Visual Callout:** Point out the "High Risk" filter badge showing cases where agreement value deviates by more than 30% from the statutory circle rate.

### Step 3: Open Underwriting Pipeline (3:00 - 4:15)
- **Presenter Action:** Click the **Underwriting Pipeline** tab.
- **Narrative:** *"The pipeline view provides a complete workflow kanban separating files into 'In Review', 'Ready for Underwriter Sign-off', and finalized 'Approved' or 'Rejected' cases."*
- **Visual Callout:** Select case `HFC-BLR-2026-89412` (Rajesh & Priya Sengupta - Sobha Dream Acres).

### Step 4: Enter Valuation Studio & Inspect Physical Data (4:15 - 5:30)
- **Presenter Action:** Click **"Open Valuation Studio"** for the selected Bengaluru apartment case.
- **Narrative:** *"In the Valuation Studio, we see the complete appraisal dossier: 1,215 sq.ft carpet area, 14th floor out of 18, 2 years building age, 60 ft approach road, and RERA registration PRM/KA/RERA/1251/446/PR/171014/000641."*
- **Visual Callout:** Point out the explicit `"Data Source: synthetic-demo"` badge in the case header.

### Step 5: Explain Deterministic Valuation Waterfall (5:30 - 7:00)
- **Presenter Action:** Scroll to the **"Valuation Breakdown"** panel.
- **Narrative:** *"PropVal AI implements a 100% deterministic valuation engine with identical parity across our Python backend and TypeScript client. The base circle rate is ₹7,200/sq.ft. The statutory engine adds ₹350 for 14th floor rise, ₹280 for the 60ft road width, and ₹520 for gated amenities, minus ₹120 structural depreciation."*
- **Key Metrics to Highlight:**
  - **Gross Market Value (GMV):** ₹1.68 Crore
  - **Net Assessed Value (NAV):** ₹1.68 Crore (at 0% underwriter haircut)
  - **Distress Liquidation Value (DLV):** ₹1.38 Crore (at 18% forced sale haircut)
  - **Max Permissible Sanction:** ₹1.05 Crore (loan requested is fully covered within 75% LTV limit)

### Step 6: Interactive Underwriter Haircut Sensitivity (7:00 - 8:15)
- **Presenter Action:** Drag the **"Underwriter Haircut"** slider from 0% to 10%.
- **Narrative:** *"If an underwriter identifies local micro-market softness or pending civic construction, they can apply a discretionary technical haircut. As we slide to 10%, the Net Assessed Value immediately recalculates to ₹1.51 Crore, and the Maximum Permissible Sanction dynamically adjusts to ₹1.05 Crore. This sensitivity analysis happens instantly in real-time."*
- **Presenter Action:** Return slider to 0%.

### Step 7: Inspect Market Comparable Deed Evidence (8:15 - 9:30)
- **Presenter Action:** Scroll to the **"Comparable Transaction Evidence"** map and grid.
- **Narrative:** *"The system anchors valuations against real sub-registrar registered deeds. Here we have 3 nearby deeds within 1 km in the same micro-market. Notice the registered transaction prices: ₹1.32 Cr (Sobha Dream Acres C-Wing), ₹1.41 Cr (Prestige Lakeside Habitat), and ₹1.27 Cr (Brigade Cornerstone Utopia). Every comparable is weighted by physical similarity and distance."*
- **Visual Callout:** Emphasize that all demonstration comparables carry verified synthetic SRO registration numbers.

### Step 8: Model Governance & Ethical AI Readiness Gate (9:30 - 11:30)
- **Presenter Action:** Click the **Model Governance** tab.
- **Narrative:** *"Now we come to the most critical compliance feature of PropVal AI: our Model Governance framework. Many automated valuation tools irresponsibly train machine learning models on a few dozen records and claim 99% accuracy. In PropVal AI, our CatBoost ML engine is strictly GATED."*
- **Key Explanations for the Board:**
  - *"Our pre-training readiness gate requires a minimum of 1,000 verified empirical transaction deeds before an ML model is permitted to train."*
  - *"Because our demo environment contains only 14 sample records, the system reports `Status: GATED (Dataset Size Insufficient)`."*
  - *"Rather than manufacturing fake AI predictions, our backend truthfully falls back to the deterministic statutory rule engine. This satisfies RBI model risk management norms."*
  - *"Conformal uncertainty intervals are transparently withheld until empirical calibration datasets are ingested."*

### Step 9: AI Underwriter Assistant (Gemini 2.5 Flash) (11:30 - 13:00)
- **Presenter Action:** Return to Valuation Studio and open the **AI Underwriter Assistant** panel.
- **Narrative:** *"We integrate Google Gemini 2.5 Flash, but with strict institutional guardrails. Gemini serves as a qualitative advisory assistant, not a replacement for human credit underwriters."*
- **Demonstrate PII Scrub Preview:**
  - Toggle the **"PII Scrub Preview"** switch.
  - Show how borrower names, Aadhaar numbers, and PAN cards are redacted to `[AADHAAR_REDACTED]` and `[PAN_REDACTED]` before leaving the browser.
- **Demonstrate Advisory Boundaries:**
  - Click **"Generate Underwriter Briefing"**.
  - Show that Gemini summarizes the micro-market legal risks, road access, and data quality concerns without altering any rupee numbers.
  - Point out the disclaimer: *"AI underwriter synthesis is advisory. All credit decisions require human review."*

### Step 10: Cryptographic SHA-256 Audit Trail (13:00 - 14:30)
- **Presenter Action:** Navigate to **Risk & Audit** $\rightarrow$ **Cryptographic Audit Trail**.
- **Narrative:** *"Every action taken in this application—every login, valuation recalculation, and status change—is cryptographically hashed into an append-only SHA-256 chain, structured identically to financial ledger blocks."*
- **Presenter Action:** Click the **"Verify Audit Chain"** button.
- **Expected Output:** Green verification banner displaying:
  > *"Cryptographic Audit Trail Verified: All 34 blocks intact from genesis. Zero tamper detected."*

### Step 11: Institutional Approval Workflow & RBAC (14:30 - 16:00)
- **Presenter Action:** Return to Valuation Studio for `case-blr-89412`. Click the green **"Approve Valuation"** button.
- **Narrative:** *"Because I am logged in as Senior Underwriter V. Sundaram, I have delegated authority to sign off on files up to ₹2.0 Crore. If a junior underwriter attempted this, the backend would reject it with HTTP 403 Forbidden."*
- **Visual Callout:** The case status badge transitions to `APPROVED (Valuation Approved & Finalized)`. The file is now locked against tampering.

### Step 12: Generate Valuation Certificate (16:00 - 17:30)
- **Presenter Action:** Click **"Generate Valuation Certificate"**.
- **Narrative:** *"With the file approved, the system generates an official, bank-ready Valuation Certificate."*
- **Visual Callout:**
  - Official Certificate Header with unique Case ID (`HFC-BLR-2026-89412`).
  - Net Assessed Collateral Value: ₹1,68,00,000.
  - Distress Liquidation Value: ₹1,38,00,000.
  - Maximum Permissible Sanction: ₹1,05,00,000.
  - Model Governance Disclosure: *"Methodology: Statutory Rule-Based Collateral Appraisal (ML Model Gated)"*.
  - Digital Sign-off: V. Sundaram, Senior Underwriter.
- **Presenter Action:** Click **"Print Certificate"** to preview the clean, print-ready CSS layout.

---

## 3. Anticipated Questions & Executive Answers

### Q1: "Can an underwriter override the statutory circle rate?"
**Answer:** *"No. The valuation engine enforces a hard circle-rate floor. If the market rate or declared agreement rate is lower than the circle rate, the statutory circle rate automatically becomes the calculation baseline. This prevents under-collateralization and stamp duty evasion risk."*

### Q2: "Why not enable the machine learning model immediately?"
**Answer:** *"Lending on an ML model trained on 14 sample records would expose the housing finance company to severe catastrophic tail risk and regulatory censure. PropVal AI proves model governance maturity by enforcing an empirical readiness gate ($N \ge 1,000$) before statistical ML predictions can influence mortgage sanction limits."*

### Q3: "What happens if Gemini is offline or unavailable?"
**Answer:** *"The core valuation workflow has zero dependency on cloud availability. If Gemini is unreachable, our backend automatically falls back to our deterministic rule-based underwriter briefing engine, allowing the loan officer to complete the appraisal without delay."*

---

## 4. Troubleshooting & Failsafe Measures

| Issue Encountered | Quick Resolution |
| :--- | :--- |
| **Backend Unreachable in Studio** | Verify terminal running Uvicorn; client automatically falls back to local TypeScript valuation engine with offline indicators. |
| **Token Expired Error (401)** | Click the profile icon in the header, click "Sign Out", and re-authenticate as `v.sundaram`. |
| **Audit Verification Fails** | If manual SQL edits corrupted a row, run `py backend/scripts/reset_demo_env.py` to regenerate a clean cryptographic audit chain. |
| **Gemini Generates Quota Error** | The system automatically engages deterministic fallback; explain to the audience that fallback mode demonstrates zero cloud single-point-of-failure. |

