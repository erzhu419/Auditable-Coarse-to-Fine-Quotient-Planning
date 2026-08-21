from acfqp.construction_k7_reference_aligned_source_campaign_v91 import CAMPAIGN_ID


def test_v91_campaign_starts_unfrozen_without_running_outcomes():
    assert CAMPAIGN_ID == "0" * 64
