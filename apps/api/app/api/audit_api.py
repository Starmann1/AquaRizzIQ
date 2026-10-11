import hashlib
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def get_audit_trail(db: Session = Depends(get_db)):
    """Retrieve immutable, hash-chained audit log records."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
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
            "message": "Audit chain is empty; no records were verified.",
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
