"""Database-Native Multi-Tenant Row-Level Security (RLS) Context Manager.

Provides transaction-scoped session variable management for PostgreSQL native RLS.
Ensures zero context leakage across connection pools, fails closed when context is absent,
and sanitizes tenant inputs against injection attacks.
"""

import contextlib
import logging
import re
from typing import Optional, Generator
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    UserSession,
    get_current_user,
    get_optional_current_user,
    ROLE_ADMIN,
    ROLE_COMPLIANCE_AUDITOR,
)

logger = logging.getLogger(__name__)

# Strict identifier regex (UUIDs, alphanumeric codes, hyphens, underscores)
TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
    """Sanitize and validate tenant ID against SQL injection and parameter corruption."""
    if not tenant_id:
        return None
    cleaned = tenant_id.strip()
    if not cleaned:
        return None
    if not TENANT_ID_PATTERN.match(cleaned):
        raise ValueError(f"Invalid tenant_id format: '{cleaned}'. Must be alphanumeric with hyphens or underscores.")
    return cleaned


def set_db_tenant_context(
    session: Session,
    tenant_id: Optional[str] = None,
    is_admin: bool = False,
    is_auditor: bool = False,
) -> None:
    """Set transaction-scoped PostgreSQL session configuration parameters for RLS.

    Uses `set_config('parameter', value, is_local=true)`:
    - `is_local=true` guarantees the parameter is strictly bound to the active transaction.
    - Upon COMMIT or ROLLBACK, PostgreSQL automatically discards the parameter.
    - Zero context leaks into subsequent queries checked out from the connection pool.
    - Safely no-ops on SQLite / non-PostgreSQL dialects.
    """
    bind = session.get_bind()
    if not bind or bind.dialect.name != "postgresql":
        return

    clean_tenant = validate_tenant_id(tenant_id) or ""
    admin_flag = "true" if is_admin else "false"
    auditor_flag = "true" if is_auditor else "false"

    # Set transaction-local configuration parameters via parameterized query
    session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": clean_tenant},
    )
    session.execute(
        text("SELECT set_config('app.is_platform_admin', :is_admin, true)"),
        {"is_admin": admin_flag},
    )
    session.execute(
        text("SELECT set_config('app.is_compliance_auditor', :is_auditor, true)"),
        {"is_auditor": auditor_flag},
    )


def reset_db_tenant_context(session: Session) -> None:
    """Explicitly clear transaction-local RLS session parameters."""
    bind = session.get_bind()
    if not bind or bind.dialect.name != "postgresql":
        return

    session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))
    session.execute(text("SELECT set_config('app.is_platform_admin', 'false', true)"))
    session.execute(text("SELECT set_config('app.is_compliance_auditor', 'false', true)"))


@contextlib.contextmanager
def tenant_context_scope(
    session: Session,
    user: Optional[UserSession] = None,
    tenant_id: Optional[str] = None,
):
    """Context manager setting transaction-local RLS variables for the duration of a code block."""
    effective_tenant = tenant_id or (user.institution_id if user else None)
    is_admin = bool(user and user.role == ROLE_ADMIN and not user.institution_id)
    is_auditor = bool(user and user.role == ROLE_COMPLIANCE_AUDITOR)

    set_db_tenant_context(
        session,
        tenant_id=effective_tenant,
        is_admin=is_admin,
        is_auditor=is_auditor,
    )
    try:
        yield session
    finally:
        reset_db_tenant_context(session)


def get_tenant_db(
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Generator[Session, None, None]:
    """FastAPI dependency injecting a database session with active RLS tenant context.

    Automatically binds the authenticated user's institution_id into PostgreSQL
    before executing endpoint business logic.
    """
    is_admin = bool(user.role == ROLE_ADMIN and not user.institution_id)
    is_auditor = bool(user.role == ROLE_COMPLIANCE_AUDITOR)

    set_db_tenant_context(
        db,
        tenant_id=user.institution_id,
        is_admin=is_admin,
        is_auditor=is_auditor,
    )
    try:
        yield db
    finally:
        reset_db_tenant_context(db)

