from acfqp.construction_k7_sample_tax_replication_campaign_v164 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
)


def test_v164_formal_attempt_starts_preregistered_and_unexecuted():
    assert ATTEMPT_TERMINAL_STATE == "UNEXECUTED"
    assert CAMPAIGN_ID == "0" * 64
