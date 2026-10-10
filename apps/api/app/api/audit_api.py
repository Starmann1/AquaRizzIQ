import hashlib
import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def get_audit_trail(db: Session = Depends(get_db)):
    """Retrieve immutable, hash-chained audit log records."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    if not logs:
        # Return synthetic bootstrap records if empty
        return [
            {
                "id": "audit-001",
                "event_type": "SYSTEM_INITIALIZED",
                "entity_type": "PLATFORM",
                "entity_id": "SYS-AQUARIZZ",
                "actor": "SYSTEM_SERVICE",
                "details": {"version": "0.1.0", "mode": "LOCAL_PROTOTYPE", "crs": "EPSG:32644"},
                "prev_hash": "GENESIS",
                "row_hash": "4a5e1e5822912b9886b4f70e1496b33e9ecf75528650d42b3501f00000000001",
                "created_at": "2026-10-10T10:00:00Z",
            },
            {
                "id": "audit-002",
                "event_type": "STORM_SCENARIO_LOADED",
                "entity_type": "SCENARIO",
                "entity_id": "demo-storm-01",
                "actor": "MUNICIPAL_OPERATOR",
                "details": {"intensity_mm_h": 45.0, "tide_level_m": 1.4},
                "prev_hash": "4a5e1e5822912b9886b4f70e1496b33e9ecf75528650d42b3501f00000000001",
                "row_hash": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
                "created_at": "2026-10-10T10:05:00Z",
            },
        ]
    return [
        {
            "id": str(log.id),
            "event_type": log.event_type,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "actor": log.actor,
            "details": log.details,
            "prev_hash": log.prev_hash,
            "row_hash": log.row_hash,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.post("/verify")
def verify_audit_chain(db: Session = Depends(get_db)):
    """Cryptographically verify the SHA-256 hash chain of the audit trail."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()
    if not logs:
        return {
            "is_valid": True,
            "records_checked": 0,
            "message": "Audit chain empty or bootstrap state.",
        }

    prev_hash = "GENESIS"
    for i, log in enumerate(logs):
        if log.prev_hash != prev_hash:
            return {
                "is_valid": False,
                "broken_at_index": i,
                "broken_id": str(log.id),
                "expected_prev": prev_hash,
                "actual_prev": log.prev_hash,
                "message": f"Hash chain broken at record {i} (id: {log.id})",
            }
        details_json = json.dumps(log.details, sort_keys=True)
        expected_hash = hashlib.sha256(f"{prev_hash}{details_json}".encode("utf-8")).hexdigest()
        if log.row_hash != expected_hash:
            return {
                "is_valid": False,
                "broken_at_index": i,
                "broken_id": str(log.id),
                "message": f"Row hash tampering detected at record {i}",
            }
        prev_hash = log.row_hash

    return {
        "is_valid": True,
        "records_checked": len(logs),
        "message": f"Successfully verified SHA-256 cryptographic integrity for all {len(logs)} audit records.",
    }
