# PropVal AI — Phase 7B Deliverable 3
# Pilot Safety Controls & Case Management Validation Report

**Document ID:** `PROPVAL-DOC-PHASE7B-03`  
**Execution Timestamp:** 2026-11-06T11:26:30+05:30  
**Phase:** 7B — Institutional Pilot Onboarding & Governance Framework  
**Author:** DevSecOps & Quality Assurance Lead Engineer  
**Status:** COMPLETE WITH EXTERNAL DEPENDENCIES PENDING  

---

## 1. Mandatory Pilot Safety Controls

Phase 7B establishes seven immutable safety controls governing case intake, valuation estimation, risk tiering, and credit approval workflows:

| Safety Control | Mechanism | Enforcement Layer | Failure Action |
| :--- | :--- | :--- | :--- |
| **1. Advisory-Only Valuation** | Case stamped `ADVISORY_ONLY` | Case Service & Pydantic Schema | Valuation output rejected if classification missing |
| **2. Zero Automated Sanction** | Final approval requires `human_sign_off_by` | API Endpoint & Case Service | `HTTP 400 Bad Request` with explicit safety rule detail |
| **3. Divergence Review (>15%)** | Variance vs declared value calculated | Case Service & DB Column | Sets `requires_senior_review = TRUE` |
| **4. Senior Approval Guard** | Role check on divergence > 15% | RBAC Security Interceptor | `HTTP 403 Forbidden` for standard Credit Underwriter |
| **5. Circle Rate Tolerance** | Deviation calculated against state SRO norms | Valuation Engine v0.2.0 | Confidence penalty & `HIGH_ALERT` tier assignment |
| **6. PostgreSQL Native RLS** | Engine-level tenant boundary | PostgreSQL 18 RLS Policies | Zero rows returned across tenant boundaries |
| **7. Cryptographic Chain** | SHA-256 Merkle hash chain | Audit Service & Trigger Hooks | Tamper detection marks chain broken |

---

## 2. Extended Case Management Schema & Fields

The `valuation_cases` table has been upgraded via Alembic migration `d4e5f6a7b8c9` with the following institutional audit columns:

```sql
ALTER TABLE valuation_cases ADD COLUMN case_reference VARCHAR(64) DEFAULT '';
ALTER TABLE valuation_cases ADD COLUMN assigned_valuer VARCHAR(128) DEFAULT '';
ALTER TABLE valuation_cases ADD COLUMN reviewing_credit_officer VARCHAR(128) DEFAULT '';
ALTER TABLE valuation_cases ADD COLUMN valuation_engine_version VARCHAR(64) DEFAULT 'hedonic-scorecard-v0.2.0';
ALTER TABLE valuation_cases ADD COLUMN valuation_methodology VARCHAR(64) DEFAULT 'DETERMINISTIC_HEDONIC';
ALTER TABLE valuation_cases ADD COLUMN advisory_classification VARCHAR(32) DEFAULT 'ADVISORY_ONLY';
ALTER TABLE valuation_cases ADD COLUMN divergence_pct FLOAT DEFAULT 0.0;
ALTER TABLE valuation_cases ADD COLUMN requires_senior_review BOOLEAN DEFAULT FALSE;
ALTER TABLE valuation_cases ADD COLUMN human_sign_off_by VARCHAR(128);
ALTER TABLE valuation_cases ADD COLUMN human_sign_off_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE valuation_cases ADD COLUMN human_sign_off_notes TEXT DEFAULT '';
```

---

## 3. Empirical Divergence & Escalation Verification

When a case is created or updated:
$$\text{Divergence \%} = \frac{|\text{Net Assessed Value} - \text{Declared Agreement Value}|}{\text{Declared Agreement Value}} \times 100$$

### Scenario Test: High Divergence Case (> 15%)
* **Declared Agreement Value:** ₹1,05,00,000 (₹1.05 Cr)
* **Calculated Net Assessed Value:** ₹85,50,000 (₹85.5 Lakh)
* **Calculated Divergence:** $18.6\%$
* **Evaluation:**
  - `divergence_pct` committed as `18.57`
  - `requires_senior_review` set to `True`
  - Credit Underwriter attempt to transition to `APPROVED`: **REJECTED** (`HTTP 403 Forbidden`)
  - Senior Underwriter attempt with human sign-off: **ACCEPTED** (`HTTP 200 OK`)

---

## 4. Institutional Pilot Dashboard Metrics API

The platform provides a centralized, real-time dashboard endpoint:
`GET /api/v1/institutions/pilot-dashboard`

### Live Response Payload Sample:
```json
{
  "totalRegisteredInstitutions": 3,
  "institutionsApprovedForPilot": 0,
  "pendingOnboardingApprovals": 3,
  "activePilotUsers": 5,
  "totalValuationCasesProcessed": 6,
  "pendingHumanReviews": 6,
  "highAlertCases": 1,
  "valuationDivergenceStats": {
    "meanDivergencePct": 8.42,
    "casesExceeding15Pct": 1,
    "maxDivergencePct": 18.57
  },
  "auditChainVerificationStatus": {
    "isValid": true,
    "totalEvents": 13,
    "latestHash": "7130d49c0cae8b15a6b0c2a8f8d9753e1a8a25c7821035b8015560b4bb1f9d51"
  },
  "dataProvenanceStatus": {
    "certifiedDeeds": 0,
    "verifiedDeeds": 410,
    "mlGateStatus": "BLOCKED",
    "activeValuationEngine": "hedonic-scorecard-v0.2.0"
  }
}
```

---

## 5. Verification Conclusion

All mandatory pilot safety controls have been tested and verified under automated unit and integration tests. The platform guarantees that no automated algorithm can sanction a loan, no valuation can be issued without the advisory-only classification, and high divergence cases are escalated to senior risk committees.

