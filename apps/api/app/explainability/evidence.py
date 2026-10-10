"""AquaRizz Evidence Registry & Content-Hashed Provenance (P1-07, P2-02).

Formats and stores verifiable evidence items:
  ID: EV-<TYPE>-<WARD>-<TIMESTAMP>-<HASH8>
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List


class EvidenceRegistry:
    """Manages immutable, content-hashed evidence records for risk assessments."""

    @staticmethod
    def create_evidence_item(
        evidence_type: str,
        ward_id: str,
        source_id: str,
        value: Any,
        observed_at: datetime,
    ) -> Dict[str, Any]:
        """Create an evidence record with cryptographic SHA-256 hash.
        
        Args:
            evidence_type: RAIN_OBS, SENSOR_OBS, MODEL_OUTPUT, TERRAIN, CONFIG
            ward_id: Ward code (e.g. WARD-112)
            source_id: Origin gauge or model ID
            value: Numerical or structured payload
            observed_at: Observation timestamp
            
        Returns:
            Dict containing id, evidence_type, ward_id, source_id, data_hash, value, observed_at
        """
        payload_bytes = json.dumps(value, sort_keys=True).encode("utf-8")
        full_hash = hashlib.sha256(payload_bytes).hexdigest()
        hash8 = full_hash[:8]

        ts_str = observed_at.strftime("%Y%m%d%H%M")
        evidence_id = f"EV-{evidence_type}-{ward_id}-{ts_str}-{hash8}"

        return {
            "id": evidence_id,
            "evidence_type": evidence_type,
            "ward_id": ward_id,
            "source_id": source_id,
            "data_hash": full_hash,
            "value": value,
            "observed_at": observed_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
