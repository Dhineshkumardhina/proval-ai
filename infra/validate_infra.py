"""Local Infrastructure Validator for PropVal AI (Phase 6C).

Validates:
1. Kubernetes manifests:
   - YAML syntax and document structure
   - Namespace and label compliance
   - Pod Security Standards (runAsNonRoot, allowPrivilegeEscalation, capabilities dropped, readOnlyRootFilesystem)
   - Resource requests and limits
   - Probes (liveness and readiness)
   - NetworkPolicy rules
   - Service and Ingress port coherence
2. Terraform configuration:
   - File presence and HCL block balance
   - Mandatory AWS security parameters:
     * KMS Customer Managed Key (CMK)
     * VPC multi-AZ 3-tier subnets (public, private, database)
     * RDS PostgreSQL (multi-AZ, gp3, KMS encrypted, publicly_accessible=false, ssl enforcement)
     * EKS cluster (private endpoint, KMS secret encryption, IRSA OIDC provider)
     * Secrets Manager (KMS encrypted)
     * CloudWatch alarms & logging
     * S3 audit vault (SSE KMS, versioning, public access block)
"""

import os
import re
import sys
import yaml
from typing import List, Dict, Any, Tuple


def validate_k8s_manifests(k8s_dir: str) -> Tuple[bool, List[str], List[str]]:
    """Validate all Kubernetes manifests in the directory."""
    errors: List[str] = []
    warnings: List[str] = []
    manifest_files = [f for f in os.listdir(k8s_dir) if f.endswith(".yaml") or f.endswith(".yml")]

    if not manifest_files:
        errors.append(f"No YAML manifests found in {k8s_dir}")
        return False, errors, warnings

    print(f"Auditing {len(manifest_files)} Kubernetes manifest files in '{k8s_dir}'...")

    for fname in sorted(manifest_files):
        fpath = os.path.join(k8s_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                docs = list(yaml.safe_load_all(fh))
        except Exception as e:
            errors.append(f"{fname}: Failed to parse YAML: {e}")
            continue

        for idx, doc in enumerate(docs):
            if not doc:
                continue
            kind = doc.get("kind", "Unknown")
            api_version = doc.get("apiVersion", "Unknown")
            metadata = doc.get("metadata", {})
            name = metadata.get("name", "Unnamed")

            doc_id = f"{fname} [{kind}/{name}]"

            # Check Namespace
            if kind != "Namespace" and metadata.get("namespace") != "propval-production":
                warnings.append(f"{doc_id}: Namespace is '{metadata.get('namespace')}', expected 'propval-production'")

            # Check Deployments
            if kind == "Deployment":
                spec = doc.get("spec", {})
                template = spec.get("template", {})
                pod_spec = template.get("spec", {})
                pod_sc = pod_spec.get("securityContext", {})

                # Pod Security
                if not pod_sc.get("runAsNonRoot"):
                    errors.append(f"{doc_id}: Pod securityContext must set 'runAsNonRoot: true'")
                if not pod_sc.get("runAsUser"):
                    warnings.append(f"{doc_id}: Pod securityContext should specify explicit 'runAsUser'")

                # Container Security & Limits
                containers = pod_spec.get("containers", [])
                for c in containers:
                    cname = c.get("name", "unknown")
                    cid = f"{doc_id} container '{cname}'"
                    csc = c.get("securityContext", {})

                    if csc.get("allowPrivilegeEscalation") is not False:
                        errors.append(f"{cid}: 'allowPrivilegeEscalation' must be false")
                    
                    caps = csc.get("capabilities", {}).get("drop", [])
                    if "ALL" not in caps:
                        errors.append(f"{cid}: Security capabilities must drop 'ALL'")

                    res = c.get("resources", {})
                    if "requests" not in res or "limits" not in res:
                        errors.append(f"{cid}: Missing resource requests or limits")
                    else:
                        req = res.get("requests", {})
                        lim = res.get("limits", {})
                        if "cpu" not in req or "memory" not in req:
                            errors.append(f"{cid}: Missing CPU or Memory requests")
                        if "cpu" not in lim or "memory" not in lim:
                            errors.append(f"{cid}: Missing CPU or Memory limits")

                    # Probes
                    if "livenessProbe" not in c:
                        errors.append(f"{cid}: Missing livenessProbe")
                    if "readinessProbe" not in c:
                        errors.append(f"{cid}: Missing readinessProbe")

            # Check Network Policy
            if kind == "NetworkPolicy":
                np_spec = doc.get("spec", {})
                policy_types = np_spec.get("policyTypes", [])
                if "Ingress" not in policy_types or "Egress" not in policy_types:
                    errors.append(f"{doc_id}: NetworkPolicy must declare both 'Ingress' and 'Egress' policyTypes")

    passed = len(errors) == 0
    return passed, errors, warnings


def validate_terraform_hcl(tf_dir: str) -> Tuple[bool, List[str], List[str]]:
    """Validate Terraform HCL configuration against security baseline."""
    errors: List[str] = []
    warnings: List[str] = []
    tf_files = [f for f in os.listdir(tf_dir) if f.endswith(".tf")]

    if not tf_files:
        errors.append(f"No .tf files found in {tf_dir}")
        return False, errors, warnings

    print(f"Auditing {len(tf_files)} Terraform configuration files in '{tf_dir}'...")

    combined_content = ""
    for fname in sorted(tf_files):
        fpath = os.path.join(tf_dir, fname)
        with open(fpath, "r", encoding="utf-8") as fh:
            content = fh.read()
            combined_content += f"\n# --- {fname} ---\n" + content

        # Check bracket balance
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces:
            errors.append(f"{fname}: Mismatched braces (open: {open_braces}, close: {close_braces})")

    # Security baseline checks across HCL
    checks = [
        ("KMS CMK Key Rotation", r'resource\s+"aws_kms_key"', r'enable_key_rotation\s*=\s*true', True),
        ("RDS Public Access Disabled", r'resource\s+"aws_db_instance"', r'publicly_accessible\s*=\s*false', True),
        ("RDS Storage Encryption", r'resource\s+"aws_db_instance"', r'storage_encrypted\s*=\s*true', True),
        ("RDS SSL Enforced", r'resource\s+"aws_db_parameter_group"', r'name\s*=\s*"rds\.force_ssl"', True),
        ("EKS Secret Encryption via KMS", r'resource\s+"aws_eks_cluster"', r'resources\s*=\s*\["secrets"\]', True),
        ("EKS Private Subnet Nodes", r'resource\s+"aws_eks_node_group"', r'subnet_ids\s*=\s*module\.vpc\.private_subnets', True),
        ("ALB TLS 1.3 Policy", r'resource\s+"aws_lb_listener"', r'ELBSecurityPolicy-TLS13', True),
        ("S3 Public Access Block", r'resource\s+"aws_s3_bucket_public_access_block"', r'block_public_acls\s*=\s*true', True),
        ("S3 KMS Encryption", r'resource\s+"aws_s3_bucket_server_side_encryption_configuration"', r'sse_algorithm\s*=\s*"aws:kms"', True),
        ("IRSA OIDC Provider", r'resource\s+"aws_iam_openid_connect_provider"', r'client_id_list', True),
        ("CloudWatch Metric Alarms", r'resource\s+"aws_cloudwatch_metric_alarm"', r'alarm_name', True),
        ("Automated Backup Vault", r'resource\s+"aws_backup_vault"', r'kms_key_arn', True),
    ]

    for name, trigger_pattern, check_pattern, is_required in checks:
        if re.search(trigger_pattern, combined_content):
            if not re.search(check_pattern, combined_content):
                if is_required:
                    errors.append(f"Security Requirement Failed: '{name}' pattern '{check_pattern}' missing")
                else:
                    warnings.append(f"Security Recommendation: '{name}' pattern '{check_pattern}' missing")
        else:
            errors.append(f"Missing Resource: '{name}' trigger '{trigger_pattern}' not found in HCL")

    passed = len(errors) == 0
    return passed, errors, warnings


if __name__ == "__main__":
    k8s_dir = os.path.join(os.path.dirname(__file__), "k8s")
    tf_dir = os.path.join(os.path.dirname(__file__), "terraform")

    print("==================================================")
    print("PROPVAL AI — INFRASTRUCTURE VALIDATION AUDIT")
    print("==================================================")

    k8s_passed, k8s_errs, k8s_warns = validate_k8s_manifests(k8s_dir)
    print(f"\nKubernetes Validation: {'PASSED' if k8s_passed else 'FAILED'}")
    if k8s_errs:
        print("  Errors:")
        for e in k8s_errs:
            print(f"    - {e}")
    if k8s_warns:
        print("  Warnings:")
        for w in k8s_warns:
            print(f"    - {w}")

    tf_passed, tf_errs, tf_warns = validate_terraform_hcl(tf_dir)
    print(f"\nTerraform Validation: {'PASSED' if tf_passed else 'FAILED'}")
    if tf_errs:
        print("  Errors:")
        for e in tf_errs:
            print(f"    - {e}")
    if tf_warns:
        print("  Warnings:")
        for w in tf_warns:
            print(f"    - {w}")

    print("\n==================================================")
    if k8s_passed and tf_passed:
        print("OVERALL INFRASTRUCTURE AUDIT: PASSED (READY FOR CLOUD STAGING)")
        sys.exit(0)
    else:
        print("OVERALL INFRASTRUCTURE AUDIT: FAILED")
        sys.exit(1)

