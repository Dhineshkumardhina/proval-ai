# PropVal AI — Phase 6G: Business Continuity & Operational Resilience Report

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6G — Multi-Region Disaster Recovery & Business Continuity  
**Date:** 2026-11-06  
**Author:** Fintech Business Continuity Specialist & Cloud Reliability Architect  
**Standard Compliance:** ISO 22301:2019 (BCMS) & RBI Cyber Security Framework for Financial Entities

---

## 1. Business Impact Analysis (BIA)

A rigorous Business Impact Analysis was conducted for PropVal AI across institutional HFC workflows:

| Critical Business Function | Financial / Operational Impact of Downtime | Maximum Tolerable Downtime (MTD) | Target RTO | Target RPO |
|:---|:---|:---:|:---:|:---:|
| **Collateral Valuation Calculation** | Stoppage of mortgage loan sanctioning pipelines; loss of customer deals | 4 Hours | **$\le 60$ Minutes** | **$\le 15$ Minutes** |
| **Audit Ledger & Fraud Verification** | Inability to certify legal encumbrance or title chain continuity | 8 Hours | **$\le 60$ Minutes** | **0 Minutes (Immutable)** |
| **Document Processing & OCR** | Delays in processing title deeds and surveyor site inspection photos | 12 Hours | **$\le 120$ Minutes** | **$\le 30$ Minutes** |
| **Institutional Multi-Tenant API** | Partner bank LOS (Loan Origination System) integration timeout | 2 Hours | **$\le 30$ Minutes** | **$\le 15$ Minutes** |
| **Model Retraining & Governance** | Paused model calibration or quarterly risk reporting | 72 Hours | **$\le 24$ Hours** | **$\le 24$ Hours** |

---

## 2. Recovery Strategies by Operational Tier

### 2.1 Critical Path: Real-Time Valuation Service
* **Zero Downtime Rule-Based Fallback:** If the machine learning or uncertainty prediction service experiences a cluster disruption, the system automatically falls back to deterministic hedonic scorecard valuation in $< 10 \text{ ms}$.
* **Multi-AZ Availability:** Within the primary AWS region (`ap-south-1` Mumbai), the application is deployed across 3 distinct Availability Zones (`ap-south-1a`, `ap-south-1b`, `ap-south-1c`). Loss of an entire AWS data center induces zero service interruption (managed by Kubernetes pod anti-affinity and AWS ALB health checks).

### 2.2 Secondary Region Warm Standby (ap-south-2 Hyderabad)
* The secondary region maintains an active EKS cluster running in a "Pilot Light" profile (minimal compute footprint).
* If the Mumbai metropolitan region suffers an extended catastrophic event (e.g. coastal fiber cut, major power grid disruption), the Hyderabad cluster scales up to full production capacity within $< 15 \text{ minutes}$ using Terraform GitOps definitions.

---

## 3. Communication, Escalation & Regulatory Reporting

In compliance with RBI Master Directions on IT and Cyber Security:
1. **Initial Incident Detection ($T + 0$ to $T + 15\text{ min}$):** CloudWatch alarms notify DevSecOps on-call via SNS and PagerDuty.
2. **Executive Escalation ($T + 30\text{ min}$):** If incident cannot be resolved within 30 minutes, the Incident Commander convenes the Business Continuity Committee (CRO, CTO, Head of Underwriting).
3. **Partner Bank Notification ($T + 60\text{ min}$):** Automated webhooks and status page updates inform institutional HFC partners of failover status.
4. **Regulatory Reporting ($T + 2\text{ hours}$):** Formal notification of major cyber or infrastructure disruption submitted to RBI Cyber Security Cell (CSITE) within the mandatory 2-hour window.

---

## 4. Continuous Resilience & Disaster Drill Schedule

| Drill Type | Frequency | Scope | Responsibility |
|:---|:---:|:---|:---|
| **Automated Backup Restoration Test** | **Daily** | Automated restoration of latest snapshot into ephemeral container with checksum & audit verification | Automated CI/CD DevSecOps Runner |
| **Storage Vault Integrity Audit** | **Weekly** | Full SHA-256 scan of S3 secondary replicated documents & model weights | Reliability Engineering |
| **Database Failover Simulation** | **Monthly** | Controlled failover from RDS primary to multi-AZ standby | Cloud Engineering |
| **Full Regional Failover Drill** | **Semi-Annual** | Complete simulated failover from Mumbai (`ap-south-1`) to Hyderabad (`ap-south-2`) | Joint CRO, CTO, & External Auditor Panel |

