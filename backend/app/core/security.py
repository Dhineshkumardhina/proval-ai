"""Institutional authentication, role-based authorization, and security utilities."""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set
import bcrypt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)

# Institutional Underwriting Roles
ROLE_CREDIT_UNDERWRITER = "CREDIT_UNDERWRITER"
ROLE_SENIOR_UNDERWRITER = "SENIOR_UNDERWRITER"
ROLE_RISK_COMMITTEE_MEMBER = "RISK_COMMITTEE_MEMBER"
ROLE_COMPLIANCE_AUDITOR = "COMPLIANCE_AUDITOR"
ROLE_ADMIN = "ADMIN"


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with 12 salt rounds."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash in constant time."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# In-memory revocation blacklist (persisted per runtime instance)
_REVOKED_TOKENS: Set[str] = set()


def revoke_token(token: str) -> None:
    """Add a JWT signature or token string to the revocation blacklist."""
    _REVOKED_TOKENS.add(token.strip())


def is_token_revoked(token: str) -> bool:
    """Check whether a token has been revoked."""
    return token.strip() in _REVOKED_TOKENS


# Institutional Demo Accounts with verified bcrypt hashes (rounds=12)
# NOTE: Static tokens have been removed to prevent authentication bypass.
# All users must authenticate via /api/v1/auth/token to obtain cryptographically signed JWTs.
DEMO_USERS = {
    "underwriter": {
        "username": "underwriter",
        "name": "R. Sharma (Credit Underwriter)",
        "role": ROLE_CREDIT_UNDERWRITER,
        # Default password: "CreditUnderwriter@2026!"
        "hashed_password": "$2b$12$ovib4tuCJxwcagwuxI6E0.wY6j/6sfBglsBytQS6llFWZHOCR/Fie",
    },
    "v.sundaram": {
        "username": "v.sundaram",
        "name": "V. Sundaram (Sr. Underwriter - Tech Risk)",
        "role": ROLE_SENIOR_UNDERWRITER,
        # Default password: "SrUnderwriter@2026!"
        "hashed_password": "$2b$12$GQxIpXxUYOojgg3YMrm42eED1cR0wp1LDfHm6zUW8ZJ.lZWlLkBHm",
    },
    "senior_underwriter": {
        "username": "v.sundaram",
        "name": "V. Sundaram (Sr. Underwriter - Tech Risk)",
        "role": ROLE_SENIOR_UNDERWRITER,
        # Default password: "SrUnderwriter@2026!"
        "hashed_password": "$2b$12$GQxIpXxUYOojgg3YMrm42eED1cR0wp1LDfHm6zUW8ZJ.lZWlLkBHm",
    },
    "committee": {
        "username": "committee",
        "name": "Credit Risk & Audit Committee",
        "role": ROLE_RISK_COMMITTEE_MEMBER,
        # Default password: "RiskCommittee@2026!"
        "hashed_password": "$2b$12$7ftb6p9yDe0hgoL3uzqOa.jhqEAEGrSTv.QaD7UYPYV3BKBx7qgoy",
    },
    "risk_committee": {
        "username": "committee",
        "name": "Credit Risk & Audit Committee",
        "role": ROLE_RISK_COMMITTEE_MEMBER,
        # Default password: "RiskCommittee@2026!"
        "hashed_password": "$2b$12$7ftb6p9yDe0hgoL3uzqOa.jhqEAEGrSTv.QaD7UYPYV3BKBx7qgoy",
    },
    "admin": {
        "username": "admin",
        "name": "System Administrator",
        "role": ROLE_ADMIN,
        # Default password: "SystemAdmin@2026!"
        "hashed_password": "$2b$12$aGYBIVTVP.AL.nmRODBG/uVVI.9z5QwVUFig5l1jvwrSRuyptPKq.",
    },
}


class UserSession(BaseModel):
    """Authenticated user context."""

    username: str
    name: str
    role: str
    is_authenticated: bool = True


def _base64url_encode(data: bytes) -> str:
    """Encode bytes using URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    """Decode URL-safe base64 string with restored padding."""
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed cryptographic HS256 JWT access token."""
    to_encode = data.copy()
    now_ts = int(time.time())
    if expires_delta:
        expire_ts = now_ts + int(expires_delta.total_seconds())
    else:
        expire_ts = now_ts + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    import uuid
    header = {"alg": "HS256", "typ": "JWT"}
    to_encode.update({
        "iat": now_ts,
        "exp": expire_ts,
        "iss": "propval-ai-backend",
        "jti": uuid.uuid4().hex,
    })

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify cryptographic signature, algorithm, revocation, mandatory claims, and expiration of an HS256 JWT token."""
    if is_token_revoked(token):
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts
    try:
        header_bytes = _base64url_decode(header_b64)
        header = json.loads(header_bytes.decode("utf-8"))

        # Explicit algorithm pinning: reject "none" or mismatched algorithms
        if header.get("alg") != settings.JWT_ALGORITHM or header.get("typ") != "JWT":
            return None

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check jti revocation if present
        if payload.get("jti") and is_token_revoked(str(payload["jti"])):
            return None

        now_ts = int(time.time())
        # Mandatory expiration claim enforcement (tokens without exp are strictly invalid)
        if "exp" not in payload or not isinstance(payload["exp"], (int, float)):
            return None
        if payload["exp"] < now_ts:
            return None

        # Mandatory identity subject claim enforcement
        if not (payload.get("sub") or payload.get("username")):
            return None

        # Check future clock skew tolerance (reject tokens issued >60s in future)
        if payload.get("iat") and payload["iat"] > now_ts + 60:
            return None

        return payload
    except Exception:
        return None


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> UserSession:
    """Resolve active user session from cryptographic JWT.

    Strictly enforces authentication: rejects missing, invalid, or revoked credentials with HTTP 401.
    All authentications must use cryptographically signed JWT access tokens.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials.strip()

    # 1. Check revocation
    if is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Institutional token has been revoked. Please authenticate again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Cryptographic JWT verification (RFC 7519 HS256)
    jwt_payload = verify_jwt_token(token)
    if jwt_payload:
        return UserSession(
            username=jwt_payload.get("sub") or jwt_payload.get("username", "underwriter"),
            name=jwt_payload.get("name", "Institutional User"),
            role=jwt_payload.get("role", ROLE_CREDIT_UNDERWRITER),
            is_authenticated=True,
        )

    # 3. If token provided is invalid, expired, or unrecognized
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired institutional credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_optional_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> Optional[UserSession]:
    """Resolve active user session if credentials are provided, or return None for public access."""
    if not auth or not auth.credentials:
        return None
    try:
        return get_current_user(auth)
    except HTTPException:
        return None


def require_roles(allowed_roles: List[str]):
    """Enforce institutional role-based access control.

    Raises HTTP 403 Forbidden if user lacks required role and is not an administrator.
    """

    def role_checker(user: UserSession = Depends(get_current_user)):
        if user.role not in allowed_roles and user.role != ROLE_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Operation requires one of roles: {', '.join(allowed_roles)}. Current role: {user.role}",
            )
        return user

    return role_checker
