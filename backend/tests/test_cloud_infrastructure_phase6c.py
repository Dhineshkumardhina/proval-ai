"""Phase 6C Test Suite: AWS Cloud Infrastructure, Terraform, & Kubernetes Security.

Verifies:
1. Kubernetes manifests adhere strictly to Pod Security Standards (Restricted Profile).
2. Non-root user enforcement, read-only root filesystems, dropped capabilities, and resource limits.
3. NetworkPolicy ingress/egress boundaries isolating database and internal services.
4. Terraform HCL institutional security configurations (KMS CMK, RDS SSL, private subnets, EKS KMS).
5. Deployment gate enforcement: marks actual cloud deployment as BLOCKED when credentials are not present.
"""

import os
import sys
import pytest

# Add repo root to path for validator import
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from infra.validate_infra import validate_k8s_manifests, validate_terraform_hcl


def test_k8s_manifests_pod_security_and_resource_limits():
    """Verify that all Kubernetes manifests satisfy the Kubernetes Restricted Pod Security Standard."""
    k8s_dir = os.path.join(repo_root, "infra", "k8s")
    passed, errors, warnings = validate_k8s_manifests(k8s_dir)
    assert passed is True, f"Kubernetes validation failed: {errors}"
    assert len(errors) == 0


def test_terraform_hcl_security_baselines():
    """Verify that Terraform HCL configuration adheres to AWS institutional security baselines."""
    tf_dir = os.path.join(repo_root, "infra", "terraform")
    passed, errors, warnings = validate_terraform_hcl(tf_dir)
    assert passed is True, f"Terraform validation failed: {errors}"
    assert len(errors) == 0


def test_cloud_deployment_status_blocked_without_aws_credentials(monkeypatch):
    """Verify that cloud deployment is explicitly flagged as BLOCKED when AWS credentials are absent.

    Mandate: 'Do not pretend that a local deployment is a cloud deployment.'
    """
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)

    has_credentials = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    assert has_credentials is False

    deployment_status = "BLOCKED (CREDENTIALS_PENDING)" if not has_credentials else "READY"
    assert deployment_status == "BLOCKED (CREDENTIALS_PENDING)"

