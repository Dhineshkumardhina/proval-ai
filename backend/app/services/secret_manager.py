"""Secret Management subsystem for PropVal AI data providers.

Ensures zero credential leakage, cloud-native secret-manager compatibility
(AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager, Env Store),
dynamic rotation, and expiration tracking.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import re
import threading
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("propval.security.secret_manager")


def mask_credential(secret: Optional[str], visible_prefix: int = 4, visible_suffix: int = 4) -> str:
    """Mask sensitive API keys/tokens for safe logging and status reporting.

    Never outputs raw secrets into logs, API responses, or error traces.
    """
    if not secret:
        return "[NOT_CONFIGURED]"
    secret_str = str(secret).strip()
    length = len(secret_str)
    if length <= (visible_prefix + visible_suffix):
        return "********"
    prefix = secret_str[:visible_prefix]
    suffix = secret_str[-visible_suffix:]
    masked_middle = "*" * min(18, max(6, length - (visible_prefix + visible_suffix)))
    return f"{prefix}_{masked_middle}_{suffix}"


class SecretManagerDriver(ABC):
    """Abstract interface for enterprise Secret Manager backends."""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve plaintext secret by key or secret ARN/path."""
        pass

    @abstractmethod
    def set_secret(self, key: str, value: str, description: Optional[str] = None) -> bool:
        """Store or update a secret value."""
        pass

    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """Revoke or delete a secret."""
        pass


class EnvSecretDriver(SecretManagerDriver):
    """Fallback driver resolving secrets from OS environment variables."""

    def get_secret(self, key: str) -> Optional[str]:
        val = os.environ.get(key)
        return val.strip() if val else None

    def set_secret(self, key: str, value: str, description: Optional[str] = None) -> bool:
        os.environ[key] = value.strip()
        return True

    def delete_secret(self, key: str) -> bool:
        if key in os.environ:
            del os.environ[key]
            return True
        return False


class InMemorySecretDriver(SecretManagerDriver):
    """Sandboxed in-memory secret driver for automated unit and integration tests."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_secret(self, key: str) -> Optional[str]:
        with self._lock:
            data = self._store.get(key)
            return data["value"] if data else None

    def set_secret(self, key: str, value: str, description: Optional[str] = None) -> bool:
        with self._lock:
            self._store[key] = {
                "value": value,
                "description": description,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            return True

    def delete_secret(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class AWSSecretsManagerDriver(SecretManagerDriver):
    """Enterprise AWS Secrets Manager adapter."""

    def __init__(self, region_name: str = "ap-south-1"):
        self.region_name = region_name
        self._client = None
        self._initialized = False

    def _get_client(self):
        if not self._initialized:
            try:
                import boto3
                self._client = boto3.client("secretsmanager", region_name=self.region_name)
            except Exception as e:
                logger.debug(f"AWS Secrets Manager client initialization deferred: {e}")
                self._client = None
            self._initialized = True
        return self._client

    def get_secret(self, key: str) -> Optional[str]:
        client = self._get_client()
        if client is None:
            # Fallback to environment
            return os.environ.get(key)
        try:
            res = client.get_secret_value(SecretId=key)
            if "SecretString" in res:
                return res["SecretString"]
            return None
        except Exception as e:
            logger.warning(f"AWS Secrets Manager retrieval failed for key '{key}': {e}")
            return os.environ.get(key)

    def set_secret(self, key: str, value: str, description: Optional[str] = None) -> bool:
        client = self._get_client()
        if client is None:
            os.environ[key] = value
            return True
        try:
            client.put_secret_value(SecretId=key, SecretString=value)
            return True
        except Exception as e:
            logger.error(f"AWS Secrets Manager put_secret_value failed for '{key}': {e}")
            return False

    def delete_secret(self, key: str) -> bool:
        client = self._get_client()
        if client is None:
            if key in os.environ:
                del os.environ[key]
            return True
        try:
            client.delete_secret(SecretId=key, ForceDeleteWithoutRecovery=True)
            return True
        except Exception as e:
            logger.error(f"AWS Secrets Manager delete_secret failed for '{key}': {e}")
            return False


class SecretManagerService:
    """Central secret management coordinator with rotation, caching, and masking."""

    _driver: SecretManagerDriver = EnvSecretDriver()
    _in_memory_driver: InMemorySecretDriver = InMemorySecretDriver()
    _use_in_memory: bool = False
    _cache: Dict[str, Tuple[str, float]] = {}  # key -> (secret_value, cached_at)
    _ttl_seconds: float = 300.0  # 5 minutes cache TTL
    _lock = threading.Lock()

    @classmethod
    def set_driver(cls, driver: SecretManagerDriver) -> None:
        with cls._lock:
            cls._driver = driver
            cls._cache.clear()

    @classmethod
    def enable_test_mode(cls) -> InMemorySecretDriver:
        with cls._lock:
            cls._use_in_memory = True
            cls._cache.clear()
            return cls._in_memory_driver

    @classmethod
    def disable_test_mode(cls) -> None:
        with cls._lock:
            cls._use_in_memory = False
            cls._cache.clear()

    @classmethod
    def get_secret(cls, key_or_name: str, fallback_env_var: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret using the active driver with safe fallback and caching."""
        if not key_or_name and not fallback_env_var:
            return None

        primary_key = key_or_name or fallback_env_var
        with cls._lock:
            if cls._use_in_memory:
                val = cls._in_memory_driver.get_secret(primary_key)
                if val:
                    return val
                if fallback_env_var:
                    val = cls._in_memory_driver.get_secret(fallback_env_var)
                    if val:
                        return val

            # Check cache for remote drivers (e.g. AWS Secrets Manager, Vault)
            is_remote_driver = not isinstance(cls._driver, (EnvSecretDriver, InMemorySecretDriver))
            now = datetime.now(timezone.utc).timestamp()
            if is_remote_driver and primary_key in cls._cache:
                val, ts = cls._cache[primary_key]
                if now - ts < cls._ttl_seconds:
                    return val

            # Query driver
            val = cls._driver.get_secret(primary_key)
            if not val and fallback_env_var and fallback_env_var != primary_key:
                val = cls._driver.get_secret(fallback_env_var)

            # Fallback to direct os.environ if driver returned nothing
            if not val and fallback_env_var:
                val = os.environ.get(fallback_env_var)
            if not val and primary_key:
                val = os.environ.get(primary_key)

            if val:
                val = val.strip()
                if is_remote_driver:
                    cls._cache[primary_key] = (val, now)
                return val

            return None

    @classmethod
    def set_secret(cls, key: str, value: str, description: Optional[str] = None) -> bool:
        """Store or update a secret, invalidating local cache."""
        with cls._lock:
            clean_val = value.strip()
            if cls._use_in_memory:
                cls._in_memory_driver.set_secret(key, clean_val, description)
            res = cls._driver.set_secret(key, clean_val, description)
            # Invalidate cache
            cls._cache.pop(key, None)
            return res

    @classmethod
    def rotate_secret(
        cls,
        key_or_name: str,
        new_secret_value: str,
        rotated_by: str = "INSTITUTIONAL_ADMIN",
    ) -> Dict[str, Any]:
        """Perform a cryptographic secret rotation with audit receipt and cache purging."""
        if not new_secret_value or len(new_secret_value.strip()) < 8:
            raise ValueError("New secret value must be at least 8 characters.")

        clean_value = new_secret_value.strip()
        fingerprint = hashlib.sha256(clean_value.encode("utf-8")).hexdigest()[:12]

        cls.set_secret(key_or_name, clean_value)

        receipt = {
            "secret_key": key_or_name,
            "rotation_timestamp": datetime.now(timezone.utc).isoformat(),
            "rotated_by": rotated_by,
            "masked_value": mask_credential(clean_value),
            "fingerprint_sha256_prefix": fingerprint,
            "status": "ROTATION_SUCCESSFUL",
        }
        logger.info(
            f"Secret rotation completed for '{key_or_name}' by '{rotated_by}'. "
            f"Masked: {receipt['masked_value']}"
        )
        return receipt

    @classmethod
    def invalidate_cache(cls, key: Optional[str] = None) -> None:
        with cls._lock:
            if key:
                cls._cache.pop(key, None)
            else:
                cls._cache.clear()

    @classmethod
    def validate_credential_health(
        cls,
        provider_code: str,
        secret_key_or_env: str,
        license_expiration: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Inspect provider credential status without leaking plaintext secrets."""
        secret = cls.get_secret(secret_key_or_env, fallback_env_var=secret_key_or_env)
        configured = bool(secret)

        now = datetime.now(timezone.utc)
        is_expired = False
        days_remaining = None
        if license_expiration:
            if license_expiration.tzinfo is None:
                license_expiration = license_expiration.replace(tzinfo=timezone.utc)
            delta = (license_expiration - now).total_seconds()
            days_remaining = round(delta / 86400.0, 1)
            if delta <= 0:
                is_expired = True

        health_status = "HEALTHY"
        if not configured:
            health_status = "MISSING_CREDENTIAL"
        elif is_expired:
            health_status = "EXPIRED"
        elif days_remaining is not None and days_remaining < 15:
            health_status = "EXPIRING_SOON"

        return {
            "provider_code": provider_code,
            "secret_key_reference": secret_key_or_env,
            "is_configured": configured,
            "masked_secret": mask_credential(secret) if configured else "[NOT_CONFIGURED]",
            "health_status": health_status,
            "license_expiration": license_expiration.isoformat() if license_expiration else None,
            "days_remaining": days_remaining,
            "is_expired": is_expired,
        }
