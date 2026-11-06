"""Data Sources, Acquisition, Provider Monitoring & Ingestion API endpoints (Phase 5C)."""

import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import (
    require_roles,
    UserSession,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_ADMIN,
    ROLE_INSTITUTION_ADMIN,
)
from app.models.data_source import DataSourceModel, IngestionJobModel, SourceAuthorizationStatus
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceStatusUpdateRequest,
    IngestionJobResponse,
    IngestionJobListResponse,
    TriggerAcquisitionRequest,
    ConnectorTestResponse,
    ProviderConnectionStatus,
    ProviderStatusBoardResponse,
    RotateSecretRequest,
    SecretRotationResponse,
)
from app.connectors.registry import ConnectorRegistry
from app.connectors.base import ConnectorConfig, SyncCursor
from app.connectors.circuit_breaker import CircuitBreakerRegistry
from app.services.secret_manager import SecretManagerService, mask_credential
from app.services.acquisition_service import AcquisitionOrchestrator
from app.services.audit_service import (
    record_audit_event,
    EVENT_DATA_SOURCE_REGISTERED,
    EVENT_DATA_SOURCE_STATUS_CHANGED,
    EVENT_DATA_SOURCE_REVOKED,
    EVENT_SECRET_ROTATED,
)

router = APIRouter()


def resolve_connector_type(source: DataSourceModel) -> str:
    """Resolve specific connector implementation for a data source."""
    code = (source.source_code or "").lower()
    tier = (source.access_tier or "").upper()
    if "MOCK" in tier or "MOCK" in code:
        return "mock_deed"
    if "propequity" in code:
        return "propequity"
    if "propstack" in code:
        return "propstack"
    if "hfc" in code or "banking" in code:
        return "hfc_banking"
    if "rera" in code:
        return "rera_developer"
    if "ogd" in code or "gov" in code:
        return "ogd_india"
    if "igr" in code or "sro" in code:
        return "state_igr"
    if "zapkey" in code:
        return "zapkey_b2b"
    return "zapkey_b2b"


@router.get(
    "/sources",
    response_model=List[DataSourceResponse],
    summary="List Registered Property Data Sources",
)
def list_sources(
    authorization_status: Optional[str] = Query(None, description="Filter by authorization status"),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    query = db.query(DataSourceModel)
    if authorization_status:
        query = query.filter(DataSourceModel.authorization_status == authorization_status)
    return query.order_by(desc(DataSourceModel.created_at)).all()


@router.post(
    "/sources",
    response_model=DataSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Authorized Property Data Source",
)
def create_source(
    data: DataSourceCreate,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN])),
):
    existing = db.query(DataSourceModel).filter(DataSourceModel.source_code == data.source_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source with code '{data.source_code}' already exists.",
        )
    src_data = data.model_dump()
    src_data["status_updated_by"] = user.username
    src_data["status_change_reason"] = "Initial source registration"
    src = DataSourceModel(**src_data)
    db.add(src)
    db.commit()
    db.refresh(src)

    # Record institutional audit event
    record_audit_event(
        db=db,
        event_type=EVENT_DATA_SOURCE_REGISTERED,
        actor_id=user.username,
        actor_role=user.role,
        payload={
            "source_id": src.id,
            "source_code": src.source_code,
            "provider_name": src.provider_name,
            "authorization_status": src.authorization_status,
            "data_owner": src.data_owner,
            "permitted_purposes": src.permitted_purposes,
        },
    )

    return src


@router.patch(
    "/sources/{source_id}/status",
    response_model=DataSourceResponse,
    summary="Update Source Authorization Status & Permissions (Admin Only)",
)
def update_source_status(
    source_id: str,
    req: DataSourceStatusUpdateRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN])),
):
    source = db.query(DataSourceModel).filter(DataSourceModel.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    old_status = source.authorization_status
    new_status = req.authorization_status

    if old_status == new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source '{source.source_code}' already has authorization status '{new_status}'.",
        )

    # Never silently change source authorization status (Security Requirement)
    source.authorization_status = new_status
    source.status_updated_by = user.username
    source.status_change_reason = req.status_change_reason
    if req.compliance_reviewer:
        source.compliance_reviewer = req.compliance_reviewer

    event_type = EVENT_DATA_SOURCE_REVOKED if new_status in (
        SourceAuthorizationStatus.REVOKED, SourceAuthorizationStatus.BLOCKED
    ) else EVENT_DATA_SOURCE_STATUS_CHANGED

    record_audit_event(
        db=db,
        event_type=event_type,
        actor_id=user.username,
        actor_role=user.role,
        payload={
            "source_id": source.id,
            "source_code": source.source_code,
            "previous_status": old_status,
            "new_status": new_status,
            "status_change_reason": req.status_change_reason,
            "compliance_reviewer": source.compliance_reviewer,
        },
    )

    db.commit()
    db.refresh(source)
    return source


@router.get(
    "/sources/{source_id}/test",
    response_model=ConnectorTestResponse,
    summary="Test Connection & Health to Source Gateway",
)
async def test_source_connection(
    source_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    source = db.query(DataSourceModel).filter(DataSourceModel.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    conn_type = resolve_connector_type(source)
    config = ConnectorConfig(
        source_id=source.id,
        source_code=source.source_code,
        base_url=source.api_base_url or "https://api.zapkey.com",
        rate_limit_per_minute=source.rate_limit_per_minute,
        auth_token_env_var=source.auth_secret_env_var,
    )
    connector = ConnectorRegistry.create(conn_type, config)
    res = await connector.test_connection()
    return ConnectorTestResponse(**res.model_dump())


@router.post(
    "/acquire",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Automated Property Acquisition Job",
)
async def trigger_acquisition(
    req: TriggerAcquisitionRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN])),
):
    source = db.query(DataSourceModel).filter(DataSourceModel.id == req.source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    conn_type = resolve_connector_type(source)
    config = ConnectorConfig(
        source_id=source.id,
        source_code=source.source_code,
        base_url=source.api_base_url or "https://api.zapkey.com",
        rate_limit_per_minute=source.rate_limit_per_minute,
        auth_token_env_var=source.auth_secret_env_var,
    )
    connector = ConnectorRegistry.create(conn_type, config)
    cursor = SyncCursor(page=req.page, page_size=req.page_size)

    orchestrator = AcquisitionOrchestrator(db)
    job = await orchestrator.execute_acquisition_job(
        source_id=source.id,
        connector=connector,
        cursor=cursor,
        target_dataset_name=req.target_dataset_name,
        max_batches=req.max_batches,
    )
    return job


@router.get(
    "/jobs",
    response_model=IngestionJobListResponse,
    summary="List Ingestion Jobs",
    description="Retrieve paginated history of ingestion jobs with record counts and statuses.",
)
def list_ingestion_jobs(
    source_id: Optional[str] = Query(None, description="Filter by Source ID"),
    job_status: Optional[str] = Query(None, alias="status", description="Filter by Job Status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    query = db.query(IngestionJobModel)
    if source_id:
        query = query.filter(IngestionJobModel.source_id == source_id)
    if job_status:
        query = query.filter(IngestionJobModel.status == job_status)

    total = query.count()
    items = query.order_by(desc(IngestionJobModel.started_at)).offset(offset).limit(limit).all()
    return IngestionJobListResponse(items=items, total=total)


@router.get(
    "/jobs/{job_id}",
    response_model=IngestionJobResponse,
    summary="Get Ingestion Job Details",
    description="Retrieve execution state, record counts, staged records, and error summaries for an ingestion job.",
)
def get_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    job = db.query(IngestionJobModel).filter(IngestionJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ingestion job '{job_id}' not found.")
    return job


@router.get(
    "/providers/status",
    response_model=ProviderStatusBoardResponse,
    summary="Real-Time Provider Activation & Health Monitoring Board",
    description="Inspect connection status, credentials configuration, and commercial availability for all property data providers.",
)
async def get_providers_status_board(
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    """Institutional monitoring board evaluating active credentials and readiness for all 8 providers."""
    providers_def = [
        {
            "code": "propequity",
            "name": "PropEquity (P.E. Analytics)",
            "tier": "CLASS_C_INSTITUTIONAL",
            "category": "LICENSED_PROVIDER",
            "env_var": "PROPEQUITY_API_KEY",
            "base_url": "https://api.propequity.in",
        },
        {
            "code": "zapkey_b2b",
            "name": "Zapkey B2B Deed Intelligence",
            "tier": "CLASS_C_INSTITUTIONAL",
            "category": "LICENSED_PROVIDER",
            "env_var": "ZAPKEY_API_KEY",
            "base_url": "https://api.zapkey.com",
        },
        {
            "code": "propstack",
            "name": "PropStack Commercial Intelligence",
            "tier": "CLASS_C_INSTITUTIONAL",
            "category": "LICENSED_PROVIDER",
            "env_var": "PROPSTACK_API_KEY",
            "base_url": "https://api.propstack.com",
        },
        {
            "code": "hfc_banking",
            "name": "HFC & Bank Portfolio Exchange",
            "tier": "CLASS_C_INSTITUTIONAL",
            "category": "HOUSING_FINANCE",
            "env_var": "HFC_CONSORTIUM_API_KEY",
            "base_url": "https://consortium.hfc-exchange.in",
        },
        {
            "code": "rera_developer",
            "name": "RERA Developer Allotment Feed",
            "tier": "CLASS_B_BULK",
            "category": "DEVELOPER_DIRECT",
            "env_var": "RERA_DEVELOPER_FEED_KEY",
            "base_url": "https://feed.rera-developer.org.in",
        },
        {
            "code": "ogd_india",
            "name": "Open Government Data (data.gov.in)",
            "tier": "CLASS_E_PUBLIC",
            "category": "GOVERNMENT_OPEN_DATA",
            "env_var": "OGD_INDIA_API_KEY",
            "base_url": "https://api.data.gov.in",
        },
        {
            "code": "state_igr",
            "name": "State IGR / SRO Direct Gateway",
            "tier": "CLASS_A_API",
            "category": "STATE_REGISTRATION_DEPT",
            "env_var": "STATE_IGR_GATEWAY_TOKEN",
            "base_url": "https://igrmaharashtra.gov.in/api/v1",
        },
        {
            "code": "mock_deed",
            "name": "Mock Simulation Connector",
            "tier": "CLASS_F_MOCK",
            "category": "TEST_ONLY",
            "env_var": "MOCK_CONNECTOR_ENABLED",
            "base_url": "http://127.0.0.1:8000/mock",
        },
    ]

    status_list: List[ProviderConnectionStatus] = []
    live_count = 0
    blocked_count = 0

    for p in providers_def:
        secret_val = SecretManagerService.get_secret(p["env_var"], fallback_env_var=p["env_var"])
        env_configured = bool(secret_val)
        masked = mask_credential(secret_val) if env_configured else "[NOT_CONFIGURED]"
        is_mock = p["code"] == "mock_deed"
        cb = CircuitBreakerRegistry.get_or_create(p["code"])

        if is_mock:
            status_list.append(
                ProviderConnectionStatus(
                    source_code=p["code"],
                    provider_name=p["name"],
                    access_tier=p["tier"],
                    source_category=p["category"],
                    auth_secret_env_var=p["env_var"],
                    env_var_configured=True,
                    connection_status="MOCK_ACTIVE",
                    commercial_status="SANDBOX_ACTIVE",
                    classification="IMPLEMENTED",
                    is_healthy=True,
                    latency_ms=1.5,
                    message="Mock sandbox connector active for development and simulation.",
                    secret_manager_bound=True,
                    circuit_breaker_state=cb.state.value,
                    license_reference="MOCK_DEV_FIXTURE_V1",
                    masked_credential="[MOCK_FIXTURE_ACTIVE]",
                )
            )
            continue

        if not env_configured:
            blocked_count += 1
            status_list.append(
                ProviderConnectionStatus(
                    source_code=p["code"],
                    provider_name=p["name"],
                    access_tier=p["tier"],
                    source_category=p["category"],
                    auth_secret_env_var=p["env_var"],
                    env_var_configured=False,
                    connection_status="CONFIG_MISSING",
                    commercial_status="BLOCKED_COMMERCIAL_AGREEMENT_REQUIRED",
                    classification="BLOCKED",
                    is_healthy=False,
                    latency_ms=None,
                    message=f"Commercial access unavailable: Environment variable / secret '{p['env_var']}' not configured. Partnership agreement required.",
                    secret_manager_bound=False,
                    circuit_breaker_state=cb.state.value,
                    masked_credential="[NOT_CONFIGURED]",
                )
            )
        else:
            # When configured, attempt live connectivity test
            try:
                config = ConnectorConfig(
                    source_id=f"src_{p['code']}",
                    source_code=p["code"],
                    base_url=p["base_url"],
                    auth_token_env_var=p["env_var"],
                )
                conn = ConnectorRegistry.create(p["code"], config)
                health = await conn.test_connection()
                if health.is_healthy:
                    # Note: AUTHENTICATED means credentials validated via handshake.
                    # LIVE is strictly reserved for live certified pipelines.
                    status_list.append(
                        ProviderConnectionStatus(
                            source_code=p["code"],
                            provider_name=p["name"],
                            access_tier=p["tier"],
                            source_category=p["category"],
                            auth_secret_env_var=p["env_var"],
                            env_var_configured=True,
                            connection_status="CONNECTED",
                            commercial_status="DOCUMENTED_AND_AUTHORIZED",
                            classification="AUTHENTICATED",
                            is_healthy=True,
                            latency_ms=health.latency_ms,
                            message=health.message,
                            secret_manager_bound=True,
                            circuit_breaker_state=cb.state.value,
                            masked_credential=masked,
                        )
                    )
                else:
                    blocked_count += 1
                    status_list.append(
                        ProviderConnectionStatus(
                            source_code=p["code"],
                            provider_name=p["name"],
                            access_tier=p["tier"],
                            source_category=p["category"],
                            auth_secret_env_var=p["env_var"],
                            env_var_configured=True,
                            connection_status="AUTHENTICATION_FAILED",
                            commercial_status="BLOCKED_COMMERCIAL_AGREEMENT_REQUIRED",
                            classification="CONFIGURED",
                            is_healthy=False,
                            latency_ms=health.latency_ms,
                            message=health.message,
                            secret_manager_bound=True,
                            circuit_breaker_state=cb.state.value,
                            masked_credential=masked,
                        )
                    )
            except Exception as e:
                blocked_count += 1
                status_list.append(
                    ProviderConnectionStatus(
                        source_code=p["code"],
                        provider_name=p["name"],
                        access_tier=p["tier"],
                        source_category=p["category"],
                        auth_secret_env_var=p["env_var"],
                        env_var_configured=True,
                        connection_status="UNREACHABLE",
                        commercial_status="BLOCKED_COMMERCIAL_AGREEMENT_REQUIRED",
                        classification="CONFIGURED",
                        is_healthy=False,
                        latency_ms=None,
                        message=f"Connection error: {str(e)}",
                        secret_manager_bound=True,
                        circuit_breaker_state=cb.state.value,
                        masked_credential=masked,
                    )
                )

    return ProviderStatusBoardResponse(
        providers=status_list,
        total_providers=len(providers_def),
        live_providers_count=live_count,
        blocked_providers_count=blocked_count,
        timestamp=datetime.now(timezone.utc),
    )


@router.post(
    "/sources/{source_id}/rotate-secret",
    response_model=SecretRotationResponse,
    summary="Cryptographic Rotation of Provider Secret (Admin Only)",
)
def rotate_source_secret(
    source_id: str,
    req: RotateSecretRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN])),
):
    source = db.query(DataSourceModel).filter(DataSourceModel.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    secret_key = source.secret_manager_key or source.auth_secret_env_var
    receipt = SecretManagerService.rotate_secret(
        key_or_name=secret_key,
        new_secret_value=req.new_secret,
        rotated_by=user.username,
    )

    record_audit_event(
        db=db,
        event_type=EVENT_SECRET_ROTATED,
        actor_id=user.username,
        actor_role=user.role,
        payload={
            "source_id": source.id,
            "source_code": source.source_code,
            "secret_key_reference": secret_key,
            "rotation_reason": req.reason,
            "masked_secret": receipt["masked_value"],
            "fingerprint_sha256_prefix": receipt["fingerprint_sha256_prefix"],
        },
    )
    db.commit()

    return SecretRotationResponse(
        source_id=source.id,
        source_code=source.source_code,
        secret_key_reference=secret_key,
        masked_secret=receipt["masked_value"],
        fingerprint_sha256_prefix=receipt["fingerprint_sha256_prefix"],
        rotation_timestamp=datetime.now(timezone.utc),
        status="ROTATED_AND_AUDITED",
    )


@router.get(
    "/sources/{source_id}/credential-health",
    summary="Inspect Provider Credential and License Health",
)
def get_source_credential_health(
    source_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    source = db.query(DataSourceModel).filter(DataSourceModel.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    secret_key = source.secret_manager_key or source.auth_secret_env_var
    health = SecretManagerService.validate_credential_health(
        provider_code=source.source_code,
        secret_key_or_env=secret_key,
        license_expiration=source.valid_until,
    )
    return health
