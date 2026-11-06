# PropVal AI — Phase 5C Provider Configuration Guide

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Enterprise Infrastructure, DevOps & Data Engineering Specification  
**Security Standard:** CIS Benchmarks, NIST SP 800-53 Secrets Management, ISO/IEC 27001  
**Date:** 2026-11-05  
**Target Audience:** Infrastructure Engineers, Enterprise DevOps, Institutional Data Officers  

> [!IMPORTANT]
> **Credential Handling & Security Mandatory Rule:**  
> **Never commit production API keys, bearer tokens, private keys, or partner secrets to version control or Docker images.**  
> All credentials must be injected dynamically at runtime via secure secret managers (e.g., AWS Secrets Manager, Azure Key Vault, HashiCorp Vault, or Kubernetes Secrets).

---

## 1. Overview & Architecture

The PropVal AI data acquisition pipeline utilizes modular, isolated connector classes that inherit from `BaseConnector`. Each connector handles authentication negotiation, rate limiting, resilient retries with exponential jitter, schema mapping, and cryptographic payload hashing.

This document details the exact configuration parameters, environment variables, network firewall rules, and activation procedures required to transition each connector from `BLOCKED` to `ACTIVE` once commercial licensing agreements are signed.

---

## 2. Environment Variable Configuration Matrix

The following environment variables control provider connections. In staging and production environments, configure these via container environment variables or `.env` files (excluded from Git).

### 2.1 PropEquity B2B API (`propequity`)
- **Connector Identifier:** `propequity`
- **Connector Class:** `app.connectors.propequity_connector.PropEquityConnector`
- **Target URL:** `https://api.propequity.in/v2`

| Variable Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PROPEQUITY_API_KEY` | String (Secret) | Yes | None | Production B2B API key issued by PropEquity. |
| `PROPEQUITY_BASE_URL` | String (URL) | No | `https://api.propequity.in/v2` | Primary API endpoint. |
| `PROPEQUITY_CLIENT_ID` | String | No | None | Optional institutional subscriber identifier. |
| `PROPEQUITY_TIMEOUT_SEC` | Integer | No | `30` | Socket timeout for deed search requests. |
| `PROPEQUITY_MAX_RETRIES` | Integer | No | `3` | Max exponential backoff retry attempts. |

---

### 2.2 Zapkey B2B Registered Transactions API (`zapkey_b2b`)
- **Connector Identifier:** `zapkey_b2b`
- **Connector Class:** `app.connectors.zapkey_connector.ZapkeyB2BConnector`
- **Target URL:** `https://api.zapkey.com/v1`

| Variable Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `ZAPKEY_API_KEY` | String (Secret) | Yes | None | B2B API key with registered deed query permissions. |
| `ZAPKEY_BASE_URL` | String (URL) | No | `https://api.zapkey.com/v1` | Production endpoint. Sandbox: `https://sandbox.zapkey.com/v1`. |
| `ZAPKEY_PARTNER_CODE` | String | No | None | Institutional HFC partner code assigned by Zapkey. |
| `ZAPKEY_RATE_LIMIT_RPS` | Integer | No | `5` | Request rate limit per second. |
| `ZAPKEY_TIMEOUT_SEC` | Integer | No | `30` | Request timeout window. |

---

### 2.3 PropStack Enterprise Deeds API (`propstack`)
- **Connector Identifier:** `propstack`
- **Connector Class:** `app.connectors.propstack_connector.PropStackConnector`
- **Target URL:** `https://api.propstack.com/api/v2`

| Variable Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PROPSTACK_API_KEY` | String (Secret) | Yes | None | Enterprise API access token. |
| `PROPSTACK_BASE_URL` | String (URL) | No | `https://api.propstack.com/api/v2` | Base API gateway URL. |
| `PROPSTACK_TIMEOUT_SEC` | Integer | No | `25` | Timeout window. |

---

### 2.4 HFC Banking Consortium Portfolio Feeds (`hfc_banking`)
- **Connector Identifier:** `hfc_banking`
- **Connector Class:** `app.connectors.hfc_connector.HFCBankingPortfolioConnector`
- **Target URL:** `https://consortium-feed.hfc-network.internal/api/v1` (or partner VPN endpoint)

| Variable Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `HFC_CONSORTIUM_API_KEY` | String (Secret) | Yes | None | Mutual consortium shared auth secret. |
| `HFC_CONSORTIUM_BASE_URL` | String (URL) | Yes | None | Internal institutional secure gateway. |
| `HFC_MEMBER_CODE` | String | Yes | None | Reporting institution identifier (e.g., `HFC_IN_009`). |
| `HFC_CLIENT_CERT_PATH` | Path | No | None | Client mTLS certificate for zero-trust VPC peering. |

---

### 2.5 State RERA Developer Disclosures (`rera_developer`)
- **Connector Identifier:** `rera_developer`
- **Connector Class:** `app.connectors.rera_developer_connector.RERADeveloperConnector`
- **Target URL:** `https://maharera.mahaonline.gov.in/api` (or state-specific portal)

| Variable Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `RERA_API_KEY` | String (Secret) | No | None | Partner API key if registered on state portal. |
| `RERA_BASE_URL` | String (URL) | No | `https://maharera.mahaonline.gov.in/api` | State RERA developer portal base URL. |
| `RERA_CACHE_TTL_HOURS` | Integer | No | `72` | Project disclosure caching window. |

---

### 2.6 Open Government Data (OGD India / Data.gov.in) (`ogd_india`)
- **Connector Identifier:** `ogd_india`
- **Connector Class:** `app.connectors.ogd_connector.OpenGovernmentDataConnector`
- **Target URL:** `https://data.gov.in/api/datastore/resource.json`

| Variable Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `OGD_INDIA_API_KEY` | String (Secret) | Yes | None | Registered API key from National Informatics Centre (NIC). |
| `OGD_INDIA_BASE_URL` | String (URL) | No | `https://data.gov.in/api/datastore/resource.json` | National Open Data portal endpoint. |
| `OGD_RESOURCE_ID` | String | No | None | Circle rate / guideline value dataset catalog ID. |

---

### 2.7 State Registration Department / IGR (`state_igr`)
- **Connector Identifier:** `state_igr`
- **Connector Class:** `app.connectors.state_igr_connector.StateRegistrationDepartmentConnector`
- **Target URL:** `https://igrmaharashtra.gov.in/e-search`

| Variable Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `STATE_IGR_API_KEY` | String (Secret) | Yes | None | Official B2B gateway token under state MoU. |
| `STATE_IGR_BASE_URL` | String (URL) | No | `https://igrmaharashtra.gov.in/e-search` | State Inspector General of Registration URL. |
| `STATE_IGR_CLIENT_CERT_PATH` | Path | No | None | Path to state-issued mTLS certificate. |

---

## 3. Network Egress & Firewall Governance

To prevent data exfiltration, man-in-the-middle attacks, and unauthorized access:

### Outbound Firewall Rules (Egress Security Group):
```
PROTOCOL: TCP
PORTS:    443 (HTTPS only — HTTP port 80 is strictly blocked)
DESTINATIONS:
  - 103.206.x.x/24   (PropEquity API Gateway)
  - 13.234.x.x/32    (Zapkey Production Ingress)
  - 164.100.x.x/16   (NIC National Data Center — data.gov.in)
  - 115.112.x.x/24   (MahaOnline / Maharashtra State Data Center)
```

### SSRF Hostname Whitelist:
The application enforces hostname validation at the transport level. Destination URLs must strictly match `PRODUCTION_ALLOWED_HOSTNAMES` in [`backend/app/connectors/http_client.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/connectors/http_client.py).

If a new licensed partner endpoint is added, DevOps must update the whitelist in `http_client.py` and execute the full test suite before deploying to production.

---

## 4. Rate Limiting, Backoff & Resilience Policies

All connectors inherit retry logic powered by `tenacity` or `ResilientHTTPClient`:

1. **Exponential Backoff:**  
   $T_{\text{wait}} = 2^{\text{attempt}} + \text{jitter}(0, 1)$ seconds.
2. **Transient Error Handling:**  
   Automatically retries HTTP `429 Too Many Requests`, `502 Bad Gateway`, `503 Service Unavailable`, and `504 Gateway Timeout`.
3. **Permanent Failure Handling:**  
   HTTP `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, and `404 Not Found` immediately fail without retry and log an alert for operational intervention.
4. **Circuit Breaker Window:**  
   If 5 consecutive requests fail within a 60-second window, the connector circuit opens for 120 seconds, preventing provider endpoint saturation.

---

## 5. Step-by-Step Provider Activation Procedure

When a commercial agreement or government MoU is executed, follow this verified procedure to activate the provider:

```
[Commercial Agreement Finalized]
             │
             ▼
[Step 1: Obtain Production Credentials & IP Whitelist confirmation]
             │
             ▼
[Step 2: Inject Secrets into Vault / Deployment Environment]
             │
             ▼
[Step 3: Verify Destination Hostname in http_client.py Whitelist]
             │
             ▼
[Step 4: Execute Non-Destructive Health Check via Test Endpoint]
        POST /api/v1/acquisition/sources/{source_id}/test
             │
             ├── If HTTP 200: Proceed
             └── If HTTP 401/403/500: Review Credentials & Network Rules
             │
             ▼
[Step 5: Execute Staged Pilot Ingestion Job (50 records)]
        POST /api/v1/acquisition/sources/{source_id}/trigger
             │
             ▼
[Step 6: Inspect Ingestion Job Status & Quality Metrics]
        GET /api/v1/acquisition/jobs/{job_id}
             │
             ▼
[Step 7: Verify Cryptographic Evidence in Verification Ledger]
        Check verification_evidence table for is_ml_eligible = True
             │
             ▼
[Provider Transitioned to ACTIVE Status]
```

---

## 6. Operational Logging & Alerting

- **Audit Logging:** Every connector invocation logs structured JSON events containing `provider`, `records_fetched`, `duration_ms`, `http_status`, and `payload_sha256`.
- **Sensitive Data Masking:** API keys and bearer tokens are automatically masked in logs (e.g., `Bearer pk_live_***8942`).
- **Alert Triggers:** PagerDuty/Slack alerts fire if:
  - Connector error rate exceeds 5% over 10 minutes.
  - SRO duplicate rate exceeds 20% on any single ingestion batch.
  - Unexpected schema alterations are detected during Pydantic normalization.

