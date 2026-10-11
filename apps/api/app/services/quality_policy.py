"""Fail-closed policy for translating input quality into model-use decisions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.db.enums import DataQualityState

QualityDisposition = Literal["ACCEPT", "ACCEPT_WITH_WARNING", "EXCLUDE", "ABSTAIN", "REJECT"]


@dataclass(frozen=True)
class QualityDecision:
    disposition: QualityDisposition
    may_contribute_to_risk: bool
    reason: str


def decide_quality_use(state: DataQualityState, *, critical_input: bool) -> QualityDecision:
    """Return a deterministic model-use decision for one classified input.

    Critical inputs never enter a risk calculation unless quality is VALID.
    Invalid inputs are rejected regardless of whether they are critical.
    """
    if state is DataQualityState.VALID:
        return QualityDecision("ACCEPT", True, "Input passed quality checks.")
    if state is DataQualityState.SUSPECT:
        if critical_input:
            return QualityDecision("ABSTAIN", False, "Critical input is suspect; risk calculation is withheld.")
        return QualityDecision("ACCEPT_WITH_WARNING", True, "Non-critical input is suspect and must remain flagged.")
    if state is DataQualityState.INVALID:
        return QualityDecision("REJECT", False, "Input is invalid and must not be used.")
    if critical_input:
        return QualityDecision("ABSTAIN", False, f"Critical input is {state.value.lower()}; risk calculation is withheld.")
    return QualityDecision("EXCLUDE", False, f"Non-critical input is {state.value.lower()} and is excluded.")
