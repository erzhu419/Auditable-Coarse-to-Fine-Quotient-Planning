from acfqp.construction_k7_safe_paid_path_sample_tax_campaign_v163 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
)


def test_v163_formal_attempt_starts_preregistered_and_unexecuted():
    assert ATTEMPT_TERMINAL_STATE == "UNEXECUTED"
    assert CAMPAIGN_ID == "0" * 64
