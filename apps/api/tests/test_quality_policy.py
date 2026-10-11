import pytest

from app.db.enums import DataQualityState
from app.services.quality_policy import decide_quality_use


@pytest.mark.parametrize("state", list(DataQualityState))
def test_every_non_valid_state_fails_closed_for_critical_inputs(state):
    decision = decide_quality_use(state, critical_input=True)
    assert decision.may_contribute_to_risk is (state is DataQualityState.VALID)
    if state is DataQualityState.VALID:
        assert decision.disposition == "ACCEPT"
    elif state is DataQualityState.INVALID:
        assert decision.disposition == "REJECT"
    else:
        assert decision.disposition == "ABSTAIN"


@pytest.mark.parametrize("state", list(DataQualityState))
def test_non_critical_quality_disposition_is_explicit(state):
    decision = decide_quality_use(state, critical_input=False)
    assert bool(decision.reason)
    if state is DataQualityState.VALID:
        assert decision.disposition == "ACCEPT"
    elif state is DataQualityState.SUSPECT:
        assert decision.disposition == "ACCEPT_WITH_WARNING"
    elif state is DataQualityState.INVALID:
        assert decision.disposition == "REJECT"
    else:
        assert decision.disposition == "EXCLUDE"
