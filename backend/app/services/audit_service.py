"""Tamper-Evident SHA-256 Audit Trail & Model Governance Service (Phase 2H).

Implements:
1. Cryptographic SHA-256 hash chaining with deterministic canonical serialization.
2. Comprehensive event recording for authentication, valuations, underwriting overrides, and AI actions.
3. Cryptographic chain verification engine detecting modifications, deletions, and sequence gaps.
4. Transparent security boundary documentation (application-level vs DBA root write boundaries).
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.audit import AuditEventModel
from app.schemas.audit import AuditVerificationReport, AuditSummaryResponse, AuditEventResponse

logger = logging.getLogger("propval.audit")

GENESIS_HASH = "0" * 64

SECURITY_BOUNDARY_NOTICE = (
    "Tamper-evident verification guarantees cryptographic detection of unauthorized modifications, "
    "insertions, or deletions within the application layer. However, a database hash chain alone cannot "
    "prevent a privileged database administrator (DBA) with direct SQL write access from rewriting the entire "
    "chain from scratch. Future phases should include periodic external anchoring (e.g., RFC 3161 timestamping "
    "or public ledger checkpointing) to prevent DBA-level history replacement."
)

# Standard Institutional Event Types
EVENT_AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
EVENT_AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
EVENT_CASE_CREATED = "CASE_CREATED"
EVENT_CASE_UPDATED = "CASE_UPDATED"
EVENT_PROPERTY_UPDATED = "PROPERTY_UPDATED"
EVENT_VALUATION_CALCULATED = "VALUATION_CALCULATED"
EVENT_UNDERWRITER_PARAM_CHANGED = "UNDERWRITER_PARAM_CHANGED"
EVENT_VALUATION_RECALCULATED = "VALUATION_RECALCULATED"
EVENT_ML_PREDICTION_REQUESTED = "ML_PREDICTION_REQUESTED"
EVENT_ML_FALLBACK_TRIGGERED = "ML_FALLBACK_TRIGGERED"
EVENT_AI_EXPLANATION_GENERATED = "AI_EXPLANATION_GENERATED"
EVENT_CASE_STATUS_CHANGED = "CASE_STATUS_CHANGED"
EVENT_CASE_APPROVED = "CASE_APPROVED"
EVENT_CASE_REJECTED = "CASE_REJECTED"
EVENT_MODEL_REGISTERED = "MODEL_REGISTERED"
EVENT_DATASET_INGESTED = "DATASET_INGESTED"
EVENT_ADMIN_ACTION = "ADMIN_ACTION"

# Phase 4B-1 Institutional Data Governance Event Types
EVENT_DATA_SOURCE_REGISTERED = "DATA_SOURCE_REGISTERED"
EVENT_DATA_SOURCE_STATUS_CHANGED = "DATA_SOURCE_STATUS_CHANGED"
EVENT_DATA_SOURCE_REVOKED = "DATA_SOURCE_REVOKED"
EVENT_DATASET_APPROVAL_STATUS_CHANGED = "DATASET_APPROVAL_STATUS_CHANGED"
EVENT_DATASET_EXPORT_ACCESSED = "DATASET_EXPORT_ACCESSED"
EVENT_DATASET_EXPORT_BLOCKED = "DATASET_EXPORT_BLOCKED"

# Phase 4B-2 Privacy Engineering & DPDP Event Types
EVENT_PII_DETECTED_AND_SCRUBBED = "PII_DETECTED_AND_SCRUBBED"
EVENT_RAW_STAGING_RETENTION_PURGE = "RAW_STAGING_RETENTION_PURGE"
EVENT_DATASET_RECORD_ERASURE = "DATASET_RECORD_ERASURE"
EVENT_DATASET_ERASURE_FAILED = "DATASET_ERASURE_FAILED"
EVENT_SOURCE_PURPOSE_BLOCKED = "SOURCE_PURPOSE_BLOCKED"
EVENT_RETENTION_LEGAL_HOLD_APPLIED = "RETENTION_LEGAL_HOLD_APPLIED"
EVENT_SECRET_ROTATED = "SECRET_ROTATED"


def canonical_serialize_payload(payload: Dict[str, Any]) -> str:
    """Deterministically serialize payload dictionary to a canonical JSON string.

    Guarantees consistent key sorting, strict separators, and ASCII encoding.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def format_canonical_timestamp(dt: Any) -> str:
    """Format timestamp to deterministic UTC string representation.

    Format: 'YYYY-MM-DDTHH:MM:SSZ' (normalizes timezone and second-resolution).
    Guarantees consistent hash calculation across database drivers and restarts.
    """
    if isinstance(dt, str):
        clean_str = dt
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(clean_str)
        except Exception:
            return dt
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_event_hash(
    sequence_number: int,
    event_id: str,
    event_type: str,
    actor_id: str,
    case_id: Optional[str],
    timestamp_iso: str,
    payload_canonical: str,
    prev_hash: str,
) -> str:
    """Compute the cryptographic SHA-256 hash of an audit event block."""
    block = {
        "sequence_number": sequence_number,
        "event_id": event_id,
        "event_type": event_type,
        "actor_id": actor_id,
        "case_id": case_id or "",
        "timestamp": timestamp_iso,
        "payload_json": payload_canonical,
        "prev_hash": prev_hash,
    }
    block_serialized = json.dumps(block, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(block_serialized.encode("utf-8")).hexdigest()


def record_audit_event(
    db: Session,
    event_type: str,
    actor_id: str,
    payload: Dict[str, Any],
    case_id: Optional[str] = None,
    actor_role: str = "CREDIT_UNDERWRITER",
) -> AuditEventModel:
    """Append an immutable event to the cryptographic SHA-256 audit chain."""
    # Find the latest event in the chain to determine sequence number and previous hash
    # Use database-level row locking on PostgreSQL to prevent concurrent sequence collisions
    query = db.query(AuditEventModel).order_by(AuditEventModel.sequence_number.desc())
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name != "sqlite":
            query = query.with_for_update()
    except Exception as lock_err:
        logger.debug("Pessimistic row locking skipped (dialect not supporting FOR UPDATE): %s", lock_err)
    latest = query.first()

    if latest is None:
        sequence_number = 1
        prev_hash = GENESIS_HASH
    else:
        sequence_number = latest.sequence_number + 1
        prev_hash = latest.current_hash

    event_id = f"evt_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc)
    timestamp_iso = format_canonical_timestamp(now)
    payload_canonical = canonical_serialize_payload(payload)

    current_hash = compute_event_hash(
        sequence_number=sequence_number,
        event_id=event_id,
        event_type=event_type,
        actor_id=actor_id,
        case_id=case_id,
        timestamp_iso=timestamp_iso,
        payload_canonical=payload_canonical,
        prev_hash=prev_hash,
    )

    event_model = AuditEventModel(
        event_id=event_id,
        sequence_number=sequence_number,
        event_type=event_type,
        actor_id=actor_id,
        actor_role=actor_role,
        case_id=case_id,
        timestamp=now,
        payload_json=payload_canonical,
        prev_hash=prev_hash,
        current_hash=current_hash,
    )

    try:
        db.add(event_model)
        db.commit()
        db.refresh(event_model)
    except Exception:
        db.rollback()
        raise

    logger.info(
        f"Audit Block #{sequence_number} ({event_type}) recorded for actor '{actor_id}' "
        f"[Hash: {current_hash[:10]}...]"
    )
    return event_model


def verify_audit_chain(db: Session) -> AuditVerificationReport:
    """Verify the integrity of the entire cryptographic audit trail.

    Checks:
    1. Sequence numbers must be strictly sequential (1, 2, 3...) with no gaps.
    2. Previous hash links must match the predecessor's current hash.
    3. Block SHA-256 hashes must match recalculations from block contents.
    """
    events: List[AuditEventModel] = db.query(AuditEventModel).order_by(AuditEventModel.sequence_number.asc()).all()
    verified_at = datetime.now(timezone.utc).isoformat()

    if not events:
        return AuditVerificationReport(
            is_valid=True,
            total_events=0,
            verified_events=0,
            genesis_hash=GENESIS_HASH,
            latest_hash=GENESIS_HASH,
            broken_index=None,
            broken_event_id=None,
            error_type=None,
            details="Audit log is empty (Genesis state).",
            security_boundary_notice=SECURITY_BOUNDARY_NOTICE,
            verified_at=verified_at,
        )

    expected_prev_hash = GENESIS_HASH

    for idx, event in enumerate(events):
        expected_seq = idx + 1

        # 1. Sequence gap check
        if event.sequence_number != expected_seq:
            return AuditVerificationReport(
                is_valid=False,
                total_events=len(events),
                verified_events=idx,
                genesis_hash=events[0].prev_hash,
                latest_hash=events[-1].current_hash,
                broken_index=expected_seq,
                broken_event_id=event.event_id,
                error_type="SEQUENCE_GAP",
                details=f"Sequence gap detected: expected block #{expected_seq}, found #{event.sequence_number}.",
                security_boundary_notice=SECURITY_BOUNDARY_NOTICE,
                verified_at=verified_at,
            )

        # 2. Previous hash link check
        if event.prev_hash != expected_prev_hash:
            return AuditVerificationReport(
                is_valid=False,
                total_events=len(events),
                verified_events=idx,
                genesis_hash=events[0].prev_hash,
                latest_hash=events[-1].current_hash,
                broken_index=event.sequence_number,
                broken_event_id=event.event_id,
                error_type="PREV_HASH_MISMATCH",
                details=(
                    f"Previous hash link broken at block #{event.sequence_number} ({event.event_id}). "
                    f"Expected predecessor hash '{expected_prev_hash[:16]}...', found '{event.prev_hash[:16]}...'."
                ),
                security_boundary_notice=SECURITY_BOUNDARY_NOTICE,
                verified_at=verified_at,
            )

        # 3. Recalculate block hash from contents
        timestamp_iso = format_canonical_timestamp(event.timestamp)
        recalculated_hash = compute_event_hash(
            sequence_number=event.sequence_number,
            event_id=event.event_id,
            event_type=event.event_type,
            actor_id=event.actor_id,
            case_id=event.case_id,
            timestamp_iso=timestamp_iso,
            payload_canonical=event.payload_json,
            prev_hash=event.prev_hash,
        )

        if recalculated_hash != event.current_hash:
            return AuditVerificationReport(
                is_valid=False,
                total_events=len(events),
                verified_events=idx,
                genesis_hash=events[0].prev_hash,
                latest_hash=events[-1].current_hash,
                broken_index=event.sequence_number,
                broken_event_id=event.event_id,
                error_type="HASH_MISMATCH",
                details=(
                    f"Cryptographic tampering detected at block #{event.sequence_number} ({event.event_id}). "
                    f"Stored hash '{event.current_hash[:16]}...' does not match recalculated hash '{recalculated_hash[:16]}...'."
                ),
                security_boundary_notice=SECURITY_BOUNDARY_NOTICE,
                verified_at=verified_at,
            )

        expected_prev_hash = event.current_hash

    return AuditVerificationReport(
        is_valid=True,
        total_events=len(events),
        verified_events=len(events),
        genesis_hash=events[0].prev_hash,
        latest_hash=events[-1].current_hash,
        broken_index=None,
        broken_event_id=None,
        error_type=None,
        details=f"Cryptographic hash chain intact. All {len(events)} events verified successfully.",
        security_boundary_notice=SECURITY_BOUNDARY_NOTICE,
        verified_at=verified_at,
    )


# Alias for backwards compatibility with integrity test suites
verify_audit_chain_integrity = verify_audit_chain


def list_audit_events(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    case_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> Tuple[List[AuditEventResponse], int]:
    """Retrieve paginated audit events with optional filters."""
    query = db.query(AuditEventModel)

    if case_id:
        query = query.filter(AuditEventModel.case_id == case_id)
    if event_type:
        query = query.filter(AuditEventModel.event_type == event_type)

    total = query.count()
    events = query.order_by(AuditEventModel.sequence_number.desc()).offset(offset).limit(limit).all()

    items = []
    for e in events:
        try:
            payload_dict = json.loads(e.payload_json)
        except Exception:
            payload_dict = {"raw": e.payload_json}

        items.append(
            AuditEventResponse(
                id=e.id,
                event_id=e.event_id,
                sequence_number=e.sequence_number,
                event_type=e.event_type,
                actor_id=e.actor_id,
                actor_role=e.actor_role,
                case_id=e.case_id,
                timestamp=e.timestamp,
                payload=payload_dict,
                prev_hash=e.prev_hash,
                current_hash=e.current_hash,
            )
        )

    return items, total


def get_audit_summary(db: Session) -> AuditSummaryResponse:
    """Compute high-level audit summary metrics."""
    total = db.query(func.count(AuditEventModel.id)).scalar() or 0
    latest = db.query(AuditEventModel).order_by(AuditEventModel.sequence_number.desc()).first()

    # Event counts by type
    type_counts_query = (
        db.query(AuditEventModel.event_type, func.count(AuditEventModel.id))
        .group_by(AuditEventModel.event_type)
        .all()
    )
    event_counts = {t: c for t, c in type_counts_query}

    # Verify chain status
    verification = verify_audit_chain(db)

    return AuditSummaryResponse(
        total_events=total,
        latest_sequence_number=latest.sequence_number if latest else 0,
        latest_event_id=latest.event_id if latest else None,
        latest_event_type=latest.event_type if latest else None,
        latest_timestamp=latest.timestamp.isoformat() if latest else None,
        latest_hash=latest.current_hash if latest else GENESIS_HASH,
        is_chain_intact=verification.is_valid,
        event_counts_by_type=event_counts,
    )


class AuditMerkleTree:
    """Cryptographic binary Merkle Tree over audit events."""

    def __init__(self, leaf_hashes: List[str]):
        if not leaf_hashes:
            self.root = hashlib.sha256(b"EMPTY_AUDIT_TREE").hexdigest()
            self.levels: List[List[str]] = [[self.root]]
            self.leaf_hashes: List[str] = []
            return

        self.leaf_hashes = leaf_hashes
        self.levels = [leaf_hashes]
        current = leaf_hashes

        while len(current) > 1:
            next_level: List[str] = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else left
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                next_level.append(parent_hash)
            self.levels.append(next_level)
            current = next_level

        self.root = current[0]

    def get_proof(self, index: int) -> List[Dict[str, str]]:
        """Generate audit inclusion proof for a leaf index."""
        if index < 0 or index >= len(self.leaf_hashes):
            return []

        proof: List[Dict[str, str]] = []
        cur_idx = index
        for level in self.levels[:-1]:
            is_right = cur_idx % 2 == 1
            sibling_index = cur_idx - 1 if is_right else cur_idx + 1
            if sibling_index < len(level):
                sibling_hash = level[sibling_index]
            else:
                sibling_hash = level[cur_idx]

            proof.append({
                "position": "left" if is_right else "right",
                "hash": sibling_hash,
            })
            cur_idx = cur_idx // 2
        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: List[Dict[str, str]], root_hash: str) -> bool:
        """Verify that a leaf hash is part of the Merkle tree with given root hash."""
        current = leaf_hash
        for item in proof:
            sibling = item["hash"]
            if item["position"] == "left":
                combined = sibling + current
            else:
                combined = current + sibling
            current = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return current == root_hash


class ExternalAuditAnchorService:
    """External tamper-evident anchoring and Merkle epoch management (Phase 4B-7)."""

    @staticmethod
    def anchor_epoch(
        db: Session,
        actor_id: str = "SYSTEM_ANCHOR",
    ):
        """Anchor current unanchored audit event sequence into an immutable Merkle root epoch."""
        from app.models.audit import AuditAnchorEpochModel

        latest_epoch = db.query(AuditAnchorEpochModel).order_by(AuditAnchorEpochModel.epoch_number.desc()).first()
        start_seq = (latest_epoch.end_sequence + 1) if latest_epoch else 1
        epoch_num = (latest_epoch.epoch_number + 1) if latest_epoch else 1

        events = (
            db.query(AuditEventModel)
            .filter(AuditEventModel.sequence_number >= start_seq)
            .order_by(AuditEventModel.sequence_number.asc())
            .all()
        )

        if not events:
            if latest_epoch:
                return latest_epoch
            events = []

        leaf_hashes = [e.current_hash for e in events]
        merkle_tree = AuditMerkleTree(leaf_hashes)
        root_hash = merkle_tree.root
        end_seq = events[-1].sequence_number if events else start_seq

        manifest = {
            "epoch_number": epoch_num,
            "merkle_root_hash": root_hash,
            "start_sequence": start_seq,
            "end_sequence": end_seq,
            "event_count": len(events),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "algorithm": "SHA-256",
        }

        token = {
            "tsa_provider": "PropVal-Simulated-RFC3161-TSA",
            "token_format": "RFC-3161-ASN1-SIMULATED",
            "hash_algorithm": "SHA-256",
            "imprint_digest": root_hash,
            "status": "ATTESTED_IN_LOCAL_SANDBOX",
            "external_storage_tier": "LOCAL_APPEND_ONLY_REGISTRY",
            "institutional_disclaimer": (
                "Local cryptographic anchoring active. Live RFC 3161 TSA counterparty integration and "
                "cloud WORM storage (e.g. AWS S3 Object Lock) require institutional counterparty credential provisioning."
            ),
        }

        epoch_record = AuditAnchorEpochModel(
            id=str(uuid.uuid4()),
            epoch_number=epoch_num,
            merkle_root_hash=root_hash,
            start_sequence=start_seq,
            end_sequence=end_seq,
            event_count=len(events),
            anchor_manifest=json.dumps(manifest, sort_keys=True),
            anchor_token=json.dumps(token, sort_keys=True),
            anchored_by=actor_id,
            anchored_at=datetime.now(timezone.utc),
        )
        db.add(epoch_record)
        db.commit()
        db.refresh(epoch_record)
        return epoch_record

    @staticmethod
    def list_anchors(
        db: Session,
        limit: int = 20,
        offset: int = 0,
    ):
        """Retrieve paginated Merkle anchor epochs."""
        from app.models.audit import AuditAnchorEpochModel

        return (
            db.query(AuditAnchorEpochModel)
            .order_by(AuditAnchorEpochModel.epoch_number.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

