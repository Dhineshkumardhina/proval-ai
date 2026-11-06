# PropVal AI — Phase 5F Disaster Recovery & Business Continuity Plan

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Disaster Recovery Plan (DRP), Business Continuity (BCP) & High Availability Architecture  
**Regulatory Standards:** RBI Guidelines on Business Continuity & Disaster Recovery for Banks, ISO/IEC 22301 (Business Continuity Management)  
**Date:** 2026-11-05  
**Disaster Recovery Roles:** Senior Infrastructure Architect & Enterprise Continuity Officer  

---

## 1. Executive Summary & Continuity Objectives

The PropVal AI Disaster Recovery Plan (DRP) ensures operational resilience, continuous collateral risk assessment, and zero catastrophic data loss for partner banks and housing finance companies.

### Core Recovery Objectives:
- **Recovery Point Objective (RPO):** $\le 1\text{ Hour}$  
  Maximum permissible data loss in the event of an unrecoverable failure. Enforced via continuous Amazon RDS Write-Ahead Log (WAL) archiving to encrypted S3 and daily full database backups.
- **Recovery Time Objective (RTO):** $\le 4\text{ Hours}$  
  Maximum permissible system downtime from incident declaration to full service restoration. Enforced via automated Infrastructure-as-Code provisioning (Terraform) and container image registries.

---

## 2. High Availability & Redundancy Topography

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          HIGH AVAILABILITY INFRASTRUCTURE                              │
├────────────────────┬─────────────────────────────┬───────────────────┬─────────────────┤
│ Component          │ Redundancy Mechanism        │ Location          │ Failover Speed  │
├────────────────────┼─────────────────────────────┼───────────────────┼─────────────────┤
│ Primary DB         │ RDS Multi-AZ Synchronous    │ ap-south-1a & 1b  │ $< 60\text{ s}$ │
│ Compute Pods       │ EKS Multi-AZ ReplicaSet (3) │ Across 3 AZs      │ $< 15\text{ s}$ │
│ Web Ingress        │ Dual-AZ ALB + Ingress Nginx │ ap-south-1a, 1b   │ Automatic       │
│ Encrypted Backups  │ S3 Cross-Region Replication │ ap-south-1 / 2    │ Continuous      │
└────────────────────┴─────────────────────────────┴───────────────────┴─────────────────┘
```

---

## 3. Disaster Scenarios & Step-by-Step Recovery Runbooks

### 3.1 Scenario 1: Availability Zone (AZ) Outage
- **Impact:** Complete failure of one AWS data center in Mumbai (`ap-south-1a`).
- **Automated Response:**
  1. Amazon RDS automatically detects primary instance unresponsiveness and flips DNS endpoint to synchronous standby in `ap-south-1b` ($< 60\text{ seconds}$).
  2. Kubernetes cluster autoscaler detects unready nodes and reschedules pods onto surviving worker nodes in `ap-south-1b` and `ap-south-1c`.
  3. Load balancer marks failed AZ targets unhealthy and routes 100% of traffic to surviving healthy targets.
- **Manual Action Required:** None. System achieves self-healing in $< 2\text{ minutes}$.

---

### 3.2 Scenario 2: Data Corruption or Accidental Deletion
- **Impact:** Unintentional bulk update or deletion of valuation cases or transaction deeds.
- **Recovery Procedure (Point-in-Time Recovery):**
  1. Identify the exact UTC timestamp $T_{\text{corrupt}}$ of the corrupting transaction from the immutable [`audit_events`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/models/audit.py) ledger.
  2. Launch an AWS RDS Point-in-Time Recovery instance using timestamp $T = T_{\text{corrupt}} - 1\text{ minute}$:
     ```bash
     aws rds restore-db-instance-to-point-in-time \
       --source-db-instance-identifier propval-rds-production \
       --target-db-instance-identifier propval-rds-restored-pitr \
       --restore-time 2026-11-05T14:30:00Z \
       --db-subnet-group-name propval-vpc-production-db-subnets
     ```
  3. Validate table row counts and verify cryptographic audit hash chain integrity.
  4. Repoint application connection secret in AWS Secrets Manager to `propval-rds-restored-pitr`.
  5. Restart backend deployment pods:
     ```bash
     kubectl rollout restart deployment/propval-backend -n propval-production
     ```
  - **Estimated RTO:** 45 minutes. Data loss: $< 1\text{ minute}$.

---

### 3.3 Scenario 3: Bad Application Deployment / Corrupted Release
- **Impact:** Newly deployed container image introduces regression or crashes on startup.
- **Recovery Procedure (Single-Command Rollback):**
  1. Execute immediate rolling rollback to the previous known-good deployment revision:
     ```bash
     kubectl rollout undo deployment/propval-backend -n propval-production
     kubectl rollout undo deployment/propval-frontend -n propval-production
     ```
  2. If the deployment involved a backward-incompatible database migration, execute Alembic downgrade via the pre-deploy migration container:
     ```bash
     alembic downgrade -1
     ```
  3. Verify system readiness:
     ```bash
     curl -f https://propval.institutional-pilot.bank.internal/health/ready
     ```
  - **Estimated RTO:** $< 3\text{ minutes}$. Data loss: Zero.

---

### 3.4 Scenario 4: Region-Wide Catastrophic Disaster (Force Majeure)
- **Impact:** Total loss of AWS Mumbai Region (`ap-south-1`).
- **Recovery Procedure (Cold Standby in AWS Hyderabad `ap-south-2`):**
  1. Declare disaster event and notify Chief Risk Officer.
  2. Execute Terraform IaC deployment targeting region `ap-south-2`:
     ```bash
     cd infra/terraform
     terraform apply -var="aws_region=ap-south-2" -var="environment=production-dr" -auto-approve
     ```
  3. Restore database from replicated cross-region S3 backup archive:
     ```bash
     ./scripts/restore_database.sh s3://propval-dr-backups-hyderabad/latest_backup.sql.gz
     ```
  4. Deploy Kubernetes workloads via Helm / Kube manifests.
  5. Update Amazon Route 53 DNS failover record to point to Hyderabad ALB.
  - **Estimated RTO:** 3 hours 15 minutes. RPO: $< 1\text{ hour}$.

---

## 4. Backup Verification & Retention Schedule

1. **Daily Full Automated Dumps:**  
   Executed daily at 02:00 UTC via [`scripts/backup_database.sh`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/scripts/backup_database.sh) with SHA-256 metadata verification.
2. **Encryption:**  
   All backup archives are encrypted with AES-256 via AWS KMS Customer Managed Keys.
3. **Retention Policy:**  
   - Continuous PITR retention: 30 days.
   - Monthly archived snapshots: 8 years (in accordance with National Housing Bank guidelines for mortgage records).
4. **Disaster Recovery Drill:**  
   Mandatory quarterly mock restoration drill executed in an isolated staging VPC to verify backup restorable integrity.

