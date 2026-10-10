import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.db.models import AuditLog

def utcnow():
    return datetime.now(timezone.utc)

class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

    def log_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str,
        details: Dict[str, Any]
    ) -> AuditLog:
        last_log = self.db.query(AuditLog).order_by(AuditLog.created_at.desc()).first()
        prev_hash = last_log.row_hash if last_log else "GENESIS"
        
        details_json = json.dumps(details, sort_keys=True)
        hash_input = f"{prev_hash}{details_json}"
        row_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        audit_log = AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            details=details,
            prev_hash=prev_hash,
            row_hash=row_hash,
            created_at=utcnow()
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log
