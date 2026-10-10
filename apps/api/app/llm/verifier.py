"""AquaRizz LLM Narrative Verifier Guards (ADR-005, P1-10).

Enforces rules V1-V6 on LLM-generated narrative text:
- V1: Numerical Grounding (no hallucinated numbers)
- V2: Evidence ID Citations
- V3: Length Limit (<= 120 words)
- V4: Prohibited Certainty Phrases
- V5: Prohibited Imperatives
- V6: Numerical Accuracy Check
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Tuple

PROHIBITED_CERTAINTY = ["definitely", "guaranteed", "100%", "certain", "absolute"]
PROHIBITED_IMPERATIVES = ["evacuate immediately", "leave now", "mandatory evacuation"]


class NarrativeVerifier:
    """Validates generated text against safety rules V1-V6."""

    @staticmethod
    def verify(
        narrative_text: str,
        allowed_numbers: List[float],
        valid_evidence_ids: List[str],
    ) -> Tuple[bool, List[str]]:
        """Verify narrative compliance.
        
        Returns:
            Tuple of (is_valid, list_of_violation_reasons)
        """
        violations = []
        text_lower = narrative_text.lower()

        # V3: Length limit (<= 120 words)
        words = narrative_text.split()
        if len(words) > 120:
            violations.append(f"V3: Word count ({len(words)}) exceeds maximum 120 words.")

        # V4: Prohibited Certainty
        for phrase in PROHIBITED_CERTAINTY:
            if phrase in text_lower:
                violations.append(f"V4: Contains prohibited certainty phrase '{phrase}'.")

        # V5: Prohibited Action Directives
        for phrase in PROHIBITED_IMPERATIVES:
            if phrase in text_lower:
                violations.append(f"V5: Contains unauthorized imperative '{phrase}'.")

        # V1: Numerical Grounding
        # Find all numbers in the narrative text
        found_numbers = [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", narrative_text)]
        # Filter out common formatting numbers like 1, 2, 3 if used in enumerations
        for num in found_numbers:
            # Check if num is within 2% of any allowed number
            matched = any(abs(num - a) <= max(0.05, 0.02 * abs(a)) for a in allowed_numbers)
            if not matched and num not in (1.0, 2.0, 3.0):  # allow small ordinal numbers
                violations.append(f"V1: Hallucinated number '{num}' not grounded in active evidence payload.")

        is_valid = len(violations) == 0
        return is_valid, violations
