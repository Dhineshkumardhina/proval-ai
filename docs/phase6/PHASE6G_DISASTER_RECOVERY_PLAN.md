# PropVal AI — Phase 6G: Multi-Region Disaster Recovery Plan

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6G — Multi-Region Disaster Recovery & Business Continuity  
**Date:** 2026-11-06  
**Author:** Senior Cloud Reliability Engineer, AWS Disaster Recovery Architect, and Fintech Business Continuity Specialist  
**Primary Cloud Region:** AWS `ap-south-1` (Mumbai, India)  
**Secondary Cloud Region:** AWS `ap-south-2` (Hyderabad, India) — 100% Domestic Sovereign Boundary (DPDP Act 2023)  
**DR Topology:** Warm Standby / Multi-Region Pilot Light with Cross-Region Automated Replication  
**Recovery Targets:** **RPO $\le$ 15 Minutes**, **RTO $\le$ 60 Minutes**

---

## 1. Executive Summary & Regulatory Mandate

Under the Indian Digital Personal Data Protection Act (DPDP) 2023, the Reserve Bank of India (RBI) Cyber Security Framework for Banks and Housing Finance Companies (HFCs), and ISO 22301 Business Continuity Management standards, PropVal AI must guarantee high resilience and rapid disaster recovery against catastrophic infrastructure outages, regional disruptions, and malicious data corruption.

### Data Sovereignty Mandate
Cross-border data replication outside India is strictly prohibited for Indian citizen property ownership, KYC, deed registrations, and mortgage underwritings. Therefore:
* **Primary Region:** AWS `ap-south-1` (Mumbai).
* **Secondary Disaster Recovery Region:** AWS `ap-south-2` (Hyderabad).
* **Geographical Separation:** $> 600 \text{ km}$ distance across separate tectonic zones and independent regional power grids.

---

## 2. Multi-Region Disaster Recovery Architecture

```mermaid
flowchart TD
    subgraph Primary["PRIMARY REGION: ap-south-1 (Mumbai)"]
        ALB_M["Application Load Balancer (Primary)"]
        EKS_M["EKS Cluster (Multi-AZ Nodes)"]
        RDS_M[("RDS PostgreSQL 16 (Multi-AZ Primary)")]
        S3_M["S3 Storage (Docs & Models Vault)"]
        KMS_M["KMS CMK (Mumbai)"]
        Vault_M["AWS Backup Vault (Mumbai)"]
    end

    subgraph Secondary["SECONDARY DR REGION: ap-south-2 (Hyderabad)"]
        ALB_H["Application Load Balancer (Standby)"]
        EKS_H["EKS Cluster (Pilot Light Nodes)"]
        RDS_H[("RDS Read Replica / Restored Primary")]
        S3_H["S3 Storage (Cross-Region Replicated)"]
        KMS_H["KMS CMK (Hyderabad)"]
        Vault_H["AWS Backup Vault (Hyderabad Copy)"]
    end

    DNS["Route 53 DNS\n(Active-Passive Failover Routing Policy)"]
    Health["Route 53 Health Check\n(HTTPS /health/ready on ALB Mumbai)"]

    DNS -->|Primary Healthy| ALB_M
    DNS -.->|Primary Down (Failover)| ALB_H
    Health -->|Monitor Every 10s| ALB_M

    ALB_M --> EKS_M
    EKS_M --> RDS_M
    EKS_M --> S3_M

    ALB_H --> EKS_H
    EKS_H --> RDS_H
    EKS_H --> S3_H

    RDS_M -.->|Asynchronous Replication / Continuous WAL| RDS_H
    S3_M -.->|Cross-Region Replication (CRR)| S3_H
    Vault_M -.->|Cross-Region Backup Copy| Vault_H
```

---

## 3. Core Component Recovery Specifications

### 3.1 Database Tier (PostgreSQL + PostGIS)
* **Continuous Point-in-Time Recovery (PITR):** 30-day retention with 5-minute WAL archiving intervals (guaranteeing $\text{RPO} \le 15\text{ min}$).
* **Cross-Region Asynchronous Read Replica:** Continuous streaming replication to `ap-south-2` (Hyderabad). In the event of primary database loss, the replica is promoted to standalone master in $< 5 \text{ minutes}$.
* **Cryptographic Backup Vault:** Daily automated snapshots copied to `aws_backup_vault.dr_vault` (`ap-south-2`) encrypted under secondary KMS CMK `aws_kms_key.dr_cmk`.

### 3.2 Storage Tier (Uploaded Deeds & ML Model Artifacts)
* **S3 Cross-Region Replication (CRR):** S3 bucket `propval-production-storage-mumbai` replicates all uploaded property documents and ML model weights to `propval-production-dr-vault-hyd` via automated S3 replication rules.
* **S3 Versioning & Object Lock:** Enabled in compliance with financial non-erasable recordkeeping standards.
* **Manifest Verification:** Every batch backup includes a SHA-256 `manifest.json` ensuring cryptographic file validation upon restoration.

### 3.3 Compute & Application Cluster (EKS)
* **Stateless Application Layer:** Both frontend (Vite/React) and backend (FastAPI) container images are stored in a multi-region Elastic Container Registry (ECR) replicated across Mumbai and Hyderabad.
* **Automated Infrastructure as Code:** Terraform scripts (`infra/terraform/`) and Kubernetes manifests (`infra/k8s/`) allow full cluster reprovisioning within $< 30 \text{ minutes}$ via GitOps.

### 3.4 DNS & Traffic Routing (Route 53)
* **Active-Passive Failover Routing:**
  * Primary Record (`A / ALIAS`): Routes to Mumbai Application Load Balancer.
  * Secondary Record (`A / ALIAS`): Routes to Hyderabad Application Load Balancer.
  * Health Check: HTTPS probe against `/health/ready` at 10-second intervals with failure threshold of 3 consecutive checks (30 seconds detection time).

---

## 4. Disaster Recovery Runbooks

### Runbook 1: Primary Database Failure (RTO $\le$ 10 min)
1. Detect database connectivity failure via CloudWatch alarm `propval-production-db-down` or `/health/ready` returning HTTP 503.
2. Promote the `ap-south-2` read replica to standalone primary database:
   ```bash
   aws rds promote-read-replica --db-instance-identifier propval-postgres-dr-hyd --region ap-south-2
   ```
3. Update backend database connection string in AWS Secrets Manager (`DATABASE_URL`).
4. Rolling restart of EKS backend pods (`kubectl rollout restart deployment/propval-backend`).
5. Execute automated audit verification (`python -m pytest backend/tests/test_disaster_recovery_phase6g.py -k test_audit_chain`).

### Runbook 2: Full Regional Outage (Mumbai Unreachable, RTO $\le$ 30 min)
1. Route 53 health check detects 3 consecutive failures on Mumbai ALB; automatically updates DNS pointer to Hyderabad ALB.
2. Ensure Hyderabad EKS cluster auto-scales from pilot light baseline (2 nodes) to production capacity (4–8 nodes).
3. Promote Hyderabad database replica to master.
4. Verify application responsiveness at `https://api.propval.internal/health`.
5. Post-incident notification sent to RBI and institutional HFC partners within 2 hours.

### Runbook 3: Corrupted Database Backup Remediation (RTO $\le$ 15 min)
1. Automated restoration script detects SHA-256 mismatch before mounting (`ValueError: CORRUPTED_BACKUP`).
2. Immediate fail-closed isolation: corrupted snapshot is quarantined.
3. Automated rollback script fetches preceding verified snapshot ($T - 15 \text{ min}$) from secondary vault.
4. Restores verified snapshot and executes `PRAGMA integrity_check` / PostGIS geometry sanity checks.

