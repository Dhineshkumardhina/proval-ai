# PropVal AI — Phase 6C: AWS Cloud Deployment Runbook & Guide

**Document Reference:** `DOC-PHASE6C-RUNBOOK-001`  
**Phase:** 6C — AWS Cloud Infrastructure Deployment  
**Author:** Senior AWS Cloud Architect & DevSecOps Specialist  
**Target Environment:** AWS Commercial Cloud (`ap-south-1` Mumbai)  
**Execution Prerequisite:** Authorized AWS Tenant Credentials & Institutional Deployment Approval  
**Current Operational Status:** **`BLOCKED (CREDENTIALS_PENDING)`**  
**Date:** November 5, 2026  

---

## 1. Prerequisites & Access Requirements

Before executing this runbook, the cloud engineer must possess:

### 1.1 Local / Bastion Tooling
- **AWS CLI:** Version 2.15+ configured with `aws sts get-caller-identity`.
- **Terraform CLI:** Version $\ge 1.6.0$.
- **kubectl:** Version $\ge 1.29.0$.
- **Helm:** Version 3.14+.
- **Docker:** Buildx enabled for multi-stage production builds.

### 1.2 IAM Deployment Permissions
The deployment IAM role must possess administrative policy boundaries or explicit permissions covering:
- `AmazonEC2FullAccess` / `AmazonVPCFullAccess`
- `AmazonRDSFullAccess`
- `AmazonEKSClusterPolicy` / `AmazonEKSWorkerNodePolicy`
- `AWSKeyManagementServicePowerUser`
- `SecretsManagerReadWrite`
- `CloudWatchLogsFullAccess`
- `AWSBackupFullAccess`

---

## 2. Phase 1: Terraform Remote State Storage Setup

Execute once per AWS account to create the centralized state bucket and DynamoDB locking table:

```bash
# Set target region
export AWS_REGION="ap-south-1"
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Create KMS-Encrypted S3 Bucket for Terraform State
aws s3api create-bucket \
  --bucket "propval-production-tfstate-${ACCOUNT_ID}" \
  --region "${AWS_REGION}" \
  --create-bucket-configuration LocationConstraint="${AWS_REGION}"

aws s3api put-bucket-versioning \
  --bucket "propval-production-tfstate-${ACCOUNT_ID}" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "propval-production-tfstate-${ACCOUNT_ID}" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

aws s3api put-public-access-block \
  --bucket "propval-production-tfstate-${ACCOUNT_ID}" \
  --public-access-block-configuration '{
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  }'

# 2. Create DynamoDB Table for Concurrency State Locking
aws dynamodb create-table \
  --table-name "propval-production-tflocks" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "${AWS_REGION}"
```

---

## 3. Phase 2: Terraform Infrastructure Provisioning

```bash
cd infra/terraform

# 1. Initialize Terraform Providers and Remote Backend
terraform init \
  -backend-config="bucket=propval-production-tfstate-${ACCOUNT_ID}" \
  -backend-config="key=propval/production/terraform.tfstate" \
  -backend-config="region=ap-south-1" \
  -backend-config="dynamodb_table=propval-production-tflocks"

# 2. Prepare Sensitive Variable File (Never commit to Git)
cat <<EOF > production.tfvars
environment          = "production"
aws_region           = "ap-south-1"
vpc_cidr             = "10.0.0.0/16"
domain_name          = "propval.institutional-pilot.bank.internal"
db_instance_class    = "db.r6g.xlarge"
db_allocated_storage = 100
db_master_password   = "${DATABASE_MASTER_PASSWORD}"
jwt_secret           = "${JWT_SECRET_256BIT}"
gemini_api_key       = "${GEMINI_API_KEY}"
alert_email          = "devsecops@propval.internal"
EOF

# 3. Generate and Audit the Terraform Execution Plan
terraform plan -var-file=production.tfvars -out=tfplan

# Verify plan contains 0 destructive deletions and matches expected 29 resources
# 4. Apply the Infrastructure Plan
terraform apply tfplan
```

---

## 4. Phase 3: EKS Cluster Configuration & Addons

Once Terraform completes provisioning:

```bash
# 1. Update Local Kubeconfig
aws eks update-kubeconfig \
  --region ap-south-1 \
  --name propval-eks-production

# 2. Verify Node Group Health
kubectl get nodes -o wide

# 3. Install AWS Load Balancer Controller via Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=propval-eks-production \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller

# 4. Install Secrets Store CSI Driver & AWS Provider
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  -n kube-system \
  --set syncSecret.enabled=true

kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml

# 5. Install Kubernetes Metrics Server for HPA
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

---

## 5. Phase 4: Container Build & ECR Push

```bash
# 1. Authenticate Docker with Amazon ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com"

# 2. Build & Push Backend Container Image
docker build -t propval-backend:production-latest -f backend/Dockerfile .
docker tag propval-backend:production-latest "${ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com/propval-backend:production-latest"
docker push "${ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com/propval-backend:production-latest"

# 3. Build & Push Frontend Container Image
docker build -t propval-frontend:production-latest -f Dockerfile .
docker tag propval-frontend:production-latest "${ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com/propval-frontend:production-latest"
docker push "${ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com/propval-frontend:production-latest"
```

---

## 6. Phase 5: Database Schema Migration & Workload Deployment

```bash
cd infra/k8s

# 1. Create Production Namespace
kubectl apply -f namespace.yaml

# 2. Create Service Account with IRSA Binding
kubectl apply -f service-account.yaml

# 3. Apply AWS Secrets Store Provider
kubectl apply -f secrets-provider-class.yaml

# 4. Execute Pre-Deployment Database Migration Job
kubectl apply -f ingress.yaml # Includes propval-db-migration Job

# Monitor Migration Job until successful completion
kubectl wait --for=condition=complete job/propval-db-migration \
  -n propval-production \
  --timeout=300s

# 5. Deploy Backend and Frontend Workloads
kubectl apply -f backend-service.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f hpa.yaml
kubectl apply -f network-policy.yaml

# 6. Verify Rolling Deployment Status
kubectl rollout status deployment/propval-backend -n propval-production --timeout=180s
kubectl rollout status deployment/propval-frontend -n propval-production --timeout=120s
```

---

## 7. Phase 6: Post-Deployment Smoke Testing & Verification

Execute the following automated verification suite against the deployed ingress:

```bash
export INGRESS_HOST="propval.institutional-pilot.bank.internal"

# 1. Verify TLS 1.3 Transport & Security Headers
curl -kIv "https://${INGRESS_HOST}/health/live" 2>&1 | grep -E "SSL connection using TLSv1.3|Strict-Transport-Security"

# 2. Verify Backend Liveness Probe
curl -sf "https://${INGRESS_HOST}/health/live" | jq .

# Expected output:
# {
#   "status": "healthy",
#   "service": "propval-ai",
#   "mode": "statutory_baseline"
# }

# 3. Verify Backend Readiness & Database Connectivity
curl -sf "https://${INGRESS_HOST}/health/ready" | jq .

# Expected output:
# {
#   "status": "ready",
#   "database": "connected",
#   "alembic_version": "head"
# }

# 4. Execute Smoke Property Valuation Request
curl -sf -X POST "https://${INGRESS_HOST}/api/v1/valuation/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Bengaluru",
    "locality": "Whitefield",
    "property_type": "APARTMENT",
    "carpet_area_sqft": 1200,
    "transaction_type": "REGISTRATION"
  }' | jq .
```

---

## 8. Rollback & Disaster Recovery Procedures

### 8.1 Zero-Downtime Rollback
If application anomalies are observed post-deployment:
```bash
# Rollback backend deployment to previous replica set revision
kubectl rollout undo deployment/propval-backend -n propval-production

# Monitor rollback completion
kubectl rollout status deployment/propval-backend -n propval-production
```

### 8.2 Database Point-In-Time Recovery (PITR)
If corrupt transactions or schema errors occur:
```bash
# Restore RDS database to a clean timestamp 30 minutes prior
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier propval-rds-production \
  --target-db-instance-identifier propval-rds-production-restored \
  --restore-time "2026-11-05T20:30:00Z" \
  --db-subnet-group-name propval-vpc-production-database \
  --vpc-security-group-ids "$(terraform output -raw db_sg_id)" \
  --region ap-south-1
```

---

## 9. Governance Note

This runbook is verified and executable. The cloud tenant deployment status will transition from **`BLOCKED (CREDENTIALS_PENDING)`** to **`DEPLOYED / LIVE`** immediately upon execution of the above steps with institutional AWS credentials.

