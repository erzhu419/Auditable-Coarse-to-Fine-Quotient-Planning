from acfqp.construction_k7_certified_paid_path_switch_campaign_v162 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
)


def test_v162_formal_attempt_starts_preregistered_and_unexecuted():
    assert ATTEMPT_TERMINAL_STATE == "UNEXECUTED"
    assert CAMPAIGN_ID == "0" * 64
