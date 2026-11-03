"""Application configuration powered by pydantic-settings."""

import os
from typing import List, Optional, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime settings and environment variables."""

    # API Metadata
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PropVal AI Institutional Valuation Backend"
    VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    @field_validator("DEBUG")
    @classmethod
    def validate_production_debug(cls, v: bool, info) -> bool:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production":
            return False
        return v

    # Server Bindings
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # URLs
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # CORS Origins (supports both CORS_ORIGINS and BACKEND_CORS_ORIGINS)
    CORS_ORIGINS: Optional[Union[str, List[str]]] = None
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]], info) -> List[str]:
        origins: List[str] = []
        if isinstance(v, str) and not v.startswith("["):
            origins = [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            origins = [str(x).strip() for x in v] if isinstance(v, list) else [v.strip()]
        else:
            raise ValueError(v)

        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and ("*" in origins):
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Wildcard '*' in BACKEND_CORS_ORIGINS "
                "is strictly prohibited in production environment!"
            )
        return origins

    # Database Settings
    DATABASE_URL: str = "sqlite:///./propval.db"

    # Credibility & Provenance Standards
    DEFAULT_DATA_SOURCE: str = "synthetic-demo"
    ENGINE_TYPE: str = "provisional rule-based estimation"
    ENGINE_VERSION: str = "0.2.0"

    # Gemini & AI Underwriter Configuration (Phase 2G)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 30.0
    GEMINI_RATE_LIMIT_PER_MINUTE: int = 15
    ENABLE_AI_CLOUD_PROCESSING: bool = True
    AI_DISCLAIMER_TEXT: str = (
        "AI underwriter synthesis is advisory. All credit underwriting and collateral "
        "decisions require human review by a qualified institutional credit officer."
    )

    # Production Security, JWT & RBAC (Phase 3)
    # Supports both JWT_SECRET and SECRET_KEY
    JWT_SECRET: Optional[str] = None
    SECRET_KEY: str = "propval-institutional-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for institutional shift

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_production_secret_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and ("change-in-production" in v or len(v) < 32):
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY must be set to a secure, "
                "unique cryptographic string (>= 32 characters) in production environment!"
            )
        return v

    # File Upload Security & Guardrails
    MAX_UPLOAD_SIZE_BYTES: int = 26214400  # 25 Megabytes
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls"]

    # Rate Limiting & Throttling
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_GLOBAL_PER_MINUTE: int = 120
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20

    # Production Database Connection Pooling (PostgreSQL)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_PRE_PING: bool = True
    DB_POOL_RECYCLE_SECONDS: int = 300

    @model_validator(mode="after")
    def synchronize_aliases(self) -> "Settings":
        # Synchronize JWT_SECRET and SECRET_KEY
        if self.JWT_SECRET and self.JWT_SECRET.strip():
            self.SECRET_KEY = self.JWT_SECRET.strip()
        elif self.SECRET_KEY and not self.JWT_SECRET:
            self.JWT_SECRET = self.SECRET_KEY

        # Synchronize CORS_ORIGINS with BACKEND_CORS_ORIGINS
        if self.CORS_ORIGINS:
            if isinstance(self.CORS_ORIGINS, str):
                self.BACKEND_CORS_ORIGINS = [i.strip() for i in self.CORS_ORIGINS.split(",") if i.strip()]
            elif isinstance(self.CORS_ORIGINS, list):
                self.BACKEND_CORS_ORIGINS = [str(x).strip() for x in self.CORS_ORIGINS if str(x).strip()]

        return self

    def validate_production_startup(self) -> None:
        """Strict fail-fast validation of required environment variables for production deployments."""
        if self.ENVIRONMENT != "production":
            return

        errors: List[str] = []

        # 1. Database URL validation
        if not self.DATABASE_URL or self.DATABASE_URL.startswith("sqlite"):
            errors.append(
                "DATABASE_URL must be configured with a production PostgreSQL connection string "
                "(e.g., postgresql://user:pass@host:5432/dbname). SQLite is strictly prohibited in production."
            )
        elif "replace-with" in self.DATABASE_URL or "propval_password" in self.DATABASE_URL:
            errors.append("DATABASE_URL contains an insecure default password placeholder.")

        # 2. Secret Key validation
        effective_secret = self.JWT_SECRET or self.SECRET_KEY
        if not effective_secret or len(effective_secret) < 32:
            errors.append("JWT_SECRET / SECRET_KEY must be a cryptographically random token of at least 32 characters.")
        if "change-in-production" in effective_secret or "replace-with" in effective_secret:
            errors.append("JWT_SECRET / SECRET_KEY contains default placeholder text. Generate a secure secret before deployment.")

        # 3. CORS validation
        if not self.BACKEND_CORS_ORIGINS:
            errors.append("CORS_ORIGINS / BACKEND_CORS_ORIGINS cannot be empty in production.")
        elif "*" in self.BACKEND_CORS_ORIGINS:
            errors.append("Wildcard '*' in CORS allowlist is strictly forbidden in production.")

        # 4. Debug validation
        if self.DEBUG:
            errors.append("DEBUG mode must be set to 'false' in production.")

        if errors:
            formatted_errors = "\n  - ".join(errors)
            raise ValueError(
                f"\n=======================================================\n"
                f"CRITICAL PRODUCTION ENVIRONMENT CONFIGURATION FAILURE:\n"
                f"  - {formatted_errors}\n"
                f"Halting startup to prevent insecure deployment.\n"
                f"======================================================="
            )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
