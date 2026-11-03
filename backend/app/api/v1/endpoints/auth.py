"""Authentication, password verification, token refresh, and institutional session endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    DEMO_USERS,
    UserSession,
    create_access_token,
    verify_jwt_token,
    verify_password,
    revoke_token,
    get_current_user,
    security_scheme,
)
from app.services import audit_service

router = APIRouter()


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class RevokeRequest(BaseModel):
    token: Optional[str] = None


@router.post("/token", response_model=TokenResponse, summary="Obtain Institutional Access Token")
def login_for_access_token(
    form_data: TokenRequest,
    db: Session = Depends(get_db),
):
    """Authenticate with username and verified bcrypt password."""
    username_clean = form_data.username.strip().lower()
    user = DEMO_USERS.get(username_clean)

    # Constant-time bcrypt password verification (safely handle bcrypt 72-byte limit)
    is_valid_password = False
    password_bytes = form_data.password.encode("utf-8")
    if len(password_bytes) <= 72 and user and user.get("hashed_password"):
        is_valid_password = verify_password(form_data.password, user["hashed_password"])

    if not user or not is_valid_password:
        # Record failed authorization attempt in cryptographic audit chain
        audit_service.record_audit_event(
            db=db,
            event_type=audit_service.EVENT_AUTH_LOGIN_FAILED,
            actor_id=form_data.username[:64],
            actor_role="UNKNOWN",
            payload={
                "attempted_username": form_data.username[:64],
                "failure_reason": "Invalid username or password",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid institutional credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Record successful login
    audit_service.record_audit_event(
        db=db,
        event_type=audit_service.EVENT_AUTH_LOGIN_SUCCESS,
        actor_id=user["username"],
        actor_role=user["role"],
        payload={
            "username": user["username"],
            "role": user["role"],
            "name": user["name"],
        },
    )

    # Generate signed cryptographic JWT token (RFC 7519 HS256)
    jwt_token = create_access_token(
        data={
            "sub": user["username"],
            "username": user["username"],
            "role": user["role"],
            "name": user["name"],
        }
    )

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        role=user["role"],
        name=user["name"],
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh Institutional Access Token")
def refresh_access_token(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db),
):
    """Issue a fresh JWT access token for an active, non-expired session."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required for refresh.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    old_token = auth.credentials.strip()
    payload = verify_jwt_token(old_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cannot refresh invalid, expired, or revoked token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Refresh Token Rotation: Revoke previous token to prevent token reuse
    revoke_token(old_token)

    new_token = create_access_token(
        data={
            "sub": payload.get("sub", "underwriter"),
            "username": payload.get("username", "underwriter"),
            "role": payload.get("role", "CREDIT_UNDERWRITER"),
            "name": payload.get("name", "Institutional User"),
        }
    )

    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        role=payload.get("role", "CREDIT_UNDERWRITER"),
        name=payload.get("name", "Institutional User"),
    )


@router.post("/revoke", summary="Revoke Institutional Token (Logout)")
@router.post("/logout", summary="Revoke Institutional Token (Logout)")
def revoke_active_token(
    payload: Optional[RevokeRequest] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke active JWT token by adding it to the revocation blacklist."""
    token_to_revoke = (payload.token if payload and payload.token else None) or (auth.credentials if auth else None)
    if not token_to_revoke:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token to revoke must be specified in header or request body.",
        )

    revoke_token(token_to_revoke)

    audit_service.record_audit_event(
        db=db,
        event_type=audit_service.EVENT_ADMIN_ACTION,
        actor_id=user.username,
        actor_role=user.role,
        payload={
            "action": "TOKEN_REVOCATION",
            "revoked_by": user.username,
        },
    )

    return {"message": "Institutional token successfully revoked.", "status": "revoked"}


@router.get("/me", response_model=UserSession, summary="Get Active User Session")
def get_user_profile(user: UserSession = Depends(get_current_user)):
    """Retrieve verified profile of the authenticated user."""
    return user
