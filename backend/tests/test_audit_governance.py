"""Tests for Phase 2H: Tamper-Evident SHA-256 Audit Trail & Model Governance.

Validates:
1. Event creation with deterministic canonical serialization.
2. SHA-256 hash generation and genesis block anchoring.
3. Cryptographic hash-chain continuity across sequential events.
4. Tampering detection on payload modification (HASH_MISMATCH).
5. Deletion detection on middle event removal (SEQUENCE_GAP / PREV_HASH_MISMATCH).
6. Unauthorized modification prevention (immutable endpoints).
7. Live audit recording on authentication, valuation, and case workflow events.
8. Audit API endpoints (/events, /verify, /summary).
9. Security boundary notice inclusion in verification reports.
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit import AuditEventModel
from app.services.audit_service import (
    record_audit_event,
    verify_audit_chain,
    list_audit_events,
    get_audit_summary,
    compute_event_hash,
    canonical_serialize_payload,
    GENESIS_HASH,
    SECURITY_BOUNDARY_NOTICE,
    EVENT_AUTH_LOGIN_FAILED,
    EVENT_CASE_CREATED,
    EVENT_VALUATION_CALCULATED,
    EVENT_CASE_APPROVED,
)


# ---------------------------------------------------------------------------
# 1. Unit Tests: Hash Computation & Canonical Serialization
# ---------------------------------------------------------------------------

def test_canonical_serialization_determinism():
    """Verify that dictionaries with different key orders produce bit-for-bit identical JSON."""
    dict_a = {"z": 100, "a": "hello", "m": [3, 2, 1], "nested": {"b": 2, "a": 1}}
    dict_b = {"a": "hello", "nested": {"a": 1, "b": 2}, "z": 100, "m": [3, 2, 1]}

    canon_a = canonical_serialize_payload(dict_a)
    canon_b = canonical_serialize_payload(dict_b)

    assert canon_a == canon_b
    assert canon_a == '{"a":"hello","m":[3,2,1],"nested":{"a":1,"b":2},"z":100}'


def test_compute_event_hash_reproducibility():
    """Verify that compute_event_hash produces deterministic 64-char SHA-256 hex strings."""
    h1 = compute_event_hash(
        sequence_number=1,
        event_id="evt_test_01",
        event_type="CASE_CREATED",
        actor_id="underwriter_1",
        case_id="case_001",
        timestamp_iso="2026-11-02T12:00:00Z",
        payload_canonical='{"amount":1000000}',
        prev_hash=GENESIS_HASH,
    )
    h2 = compute_event_hash(
        sequence_number=1,
        event_id="evt_test_01",
        event_type="CASE_CREATED",
        actor_id="underwriter_1",
        case_id="case_001",
        timestamp_iso="2026-11-02T12:00:00Z",
        payload_canonical='{"amount":1000000}',
        prev_hash=GENESIS_HASH,
    )
    assert len(h1) == 64
    assert h1 == h2


# ---------------------------------------------------------------------------
# 2. Hash Chain Recording & Continuity Tests
# ---------------------------------------------------------------------------

def test_record_audit_events_continuity(db_session: Session):
    """Verify sequential creation of events maintains unbroken cryptographic links."""
    # Record 5 test events
    events = []
    for i in range(1, 6):
        evt = record_audit_event(
            db=db_session,
            event_type=f"TEST_EVENT_{i}",
            actor_id="test_actor",
            actor_role="SENIOR_UNDERWRITER",
            payload={"step": i, "data": f"value_{i}"},
            case_id="case-blr-89412",
        )
        events.append(evt)

    # Check sequence continuity
    for idx in range(1, len(events)):
        curr_evt = events[idx]
        prev_evt = events[idx - 1]
        assert curr_evt.sequence_number == prev_evt.sequence_number + 1
        assert curr_evt.prev_hash == prev_evt.current_hash


def test_verify_audit_chain_intact(db_session: Session):
    """Verify that an untampered audit chain passes complete cryptographic verification."""
    report = verify_audit_chain(db_session)
    assert report.is_valid is True
    assert report.total_events >= 1
    assert report.verified_events == report.total_events
    assert report.error_type is None
    assert report.broken_index is None
    assert report.genesis_hash == GENESIS_HASH
    assert len(report.latest_hash) == 64
    assert SECURITY_BOUNDARY_NOTICE == report.security_boundary_notice


# ---------------------------------------------------------------------------
# 3. Tampering & Fraud Detection Tests
# ---------------------------------------------------------------------------

def test_tamper_detection_modified_payload(db_session: Session):
    """Tampering with an event payload directly in the database is detected by verification."""
    # Find an event to tamper with
    target_event = db_session.query(AuditEventModel).filter(AuditEventModel.sequence_number == 2).first()
    if not target_event:
        target_event = record_audit_event(
            db=db_session,
            event_type="TEST_TAMPER",
            actor_id="fraudster",
            payload={"sanction": 5000000},
        )

    tampered_seq = target_event.sequence_number
    # Maliciously modify the payload directly in the database row
    target_event.payload_json = '{"sanction":999999999}'
    db_session.commit()

    # Verification must flag the tampering
    report = verify_audit_chain(db_session)
    assert report.is_valid is False
    assert report.error_type == "HASH_MISMATCH"
    assert report.broken_index == tampered_seq
    assert "Cryptographic tampering detected" in report.details


def test_tamper_detection_deleted_middle_event(db_session: Session):
    """Deleting a middle block breaks sequence and triggers failure."""
    # Create 3 events
    e1 = record_audit_event(db=db_session, event_type="STEP_1", actor_id="a1", payload={"s": 1})
    e2 = record_audit_event(db=db_session, event_type="STEP_2", actor_id="a2", payload={"s": 2})
    e3 = record_audit_event(db=db_session, event_type="STEP_3", actor_id="a3", payload={"s": 3})

    deleted_seq = e2.sequence_number
    # Maliciously delete middle event #2 directly from table
    db_session.delete(e2)
    db_session.commit()

    report = verify_audit_chain(db_session)
    assert report.is_valid is False
    # Either SEQUENCE_GAP or PREV_HASH_MISMATCH is detected
    assert report.error_type in ("SEQUENCE_GAP", "PREV_HASH_MISMATCH")


# ---------------------------------------------------------------------------
# 4. Live Workflow Event Recording Tests
# ---------------------------------------------------------------------------

def test_auth_failure_recorded_in_audit_chain(client: TestClient, db_session: Session):
    """Failed login attempts are appended to the cryptographic audit chain."""
    initial_summary = get_audit_summary(db_session)
    initial_count = initial_summary.total_events

    # Attempt login with invalid credentials
    resp = client.post("/api/v1/auth/token", json={"username": "malicious_user", "password": "wrongpassword"})
    assert resp.status_code == 401

    updated_summary = get_audit_summary(db_session)
    assert updated_summary.total_events == initial_count + 1
    assert updated_summary.latest_event_type == EVENT_AUTH_LOGIN_FAILED
    assert updated_summary.is_chain_intact is True


def test_case_status_update_recorded_in_audit_chain(client: TestClient, db_session: Session):
    """Approving a case appends CASE_APPROVED to the cryptographic audit chain."""
    # Pick a seeded case
    case_resp = client.get("/api/v1/cases?limit=1")
    assert case_resp.status_code == 200
    case_id = case_resp.json()["items"][0]["id"]

    # Transition status
    patch_resp = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "auditNote": "Digitally certified by Credit Committee"},
    )
    assert patch_resp.status_code == 200

    # Verify event recorded
    events, total = list_audit_events(db_session, limit=5, case_id=case_id)
    assert total >= 1
    assert any(e.event_type == EVENT_CASE_APPROVED for e in events)


# ---------------------------------------------------------------------------
# 5. API Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_list_audit_events(client: TestClient):
    """GET /api/v1/audit/events returns paginated audit records."""
    resp = client.get("/api/v1/audit/events?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["items"]) <= 10

    first = data["items"][0]
    assert "event_id" in first
    assert "sequence_number" in first
    assert "prev_hash" in first
    assert "current_hash" in first
    assert "payload" in first


def test_api_get_event_by_id(client: TestClient):
    """GET /api/v1/audit/events/{event_id} returns single block details."""
    list_resp = client.get("/api/v1/audit/events?limit=1")
    assert list_resp.status_code == 200
    event_id = list_resp.json()["items"][0]["event_id"]

    detail_resp = client.get(f"/api/v1/audit/events/{event_id}")
    assert detail_resp.status_code == 200
    event_data = detail_resp.json()
    assert event_data["event_id"] == event_id
    assert len(event_data["current_hash"]) == 64


def test_api_get_event_not_found(client: TestClient):
    """GET /api/v1/audit/events/nonexistent returns 404."""
    resp = client.get("/api/v1/audit/events/evt_nonexistent_99999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_api_verify_audit_trail_endpoint(client: TestClient):
    """POST /api/v1/audit/verify verifies the entire SHA-256 chain."""
    resp = client.post("/api/v1/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["total_events"] >= 1
    assert "security_boundary_notice" in data
    assert "DBA" in data["security_boundary_notice"]


def test_api_audit_summary_endpoint(client: TestClient):
    """GET /api/v1/audit/summary returns summary stats."""
    resp = client.get("/api/v1/audit/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_events"] >= 1
    assert data["is_chain_intact"] is True
    assert "event_counts_by_type" in data


def test_audit_immutability_prohibits_updates_and_deletes(client: TestClient):
    """Audit events have no PUT or DELETE endpoints, returning 405 Method Not Allowed."""
    list_resp = client.get("/api/v1/audit/events?limit=1")
    event_id = list_resp.json()["items"][0]["event_id"]

    put_resp = client.put(f"/api/v1/audit/events/{event_id}", json={"hacked": True})
    assert put_resp.status_code == 405

    delete_resp = client.delete(f"/api/v1/audit/events/{event_id}")
    assert delete_resp.status_code == 405


def test_empty_chain_verification(db_session: Session):
    """Empty audit table returns valid genesis state report."""
    # Delete all audit events in this transaction
    db_session.query(AuditEventModel).delete()
    db_session.commit()

    report = verify_audit_chain(db_session)
    assert report.is_valid is True
    assert report.total_events == 0
    assert report.verified_events == 0
    assert "empty (Genesis state)" in report.details


def test_verification_after_database_restart(db_session: Session):
    """Verify that recreating or clearing session cache preserves hash verification continuity."""
    # Add an event
    record_audit_event(
        db=db_session,
        event_type="RESTART_TEST",
        actor_id="admin",
        payload={"param": "persisted"},
    )
    db_session.commit()

    # Expire all cached objects to simulate restart
    db_session.expire_all()

    report = verify_audit_chain(db_session)
    assert report.is_valid is True
    assert report.total_events >= 1
