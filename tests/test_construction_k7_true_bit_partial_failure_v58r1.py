import pytest

from acfqp import construction_k7_true_bit_partial_campaign_v58r1 as producer
from acfqp import construction_k7_true_bit_partial_failure_v58r1 as subject


def test_v58r1_failure_is_frozen_and_requires_fresh_identity():
    failure = subject.freeze_true_bit_partial_failure_v58r1()
    assert failure["campaign_artifact_returned"] is False
    assert failure["same_identity_rerun_forbidden"] is True
    assert failure["fresh_successor_identity_required"] is True
    assert failure["failed_occurrence_identity"] is None
    assert failure["successor_correction"] == (
        "COMPARE_BOTH_ARMS_OVER_SYMMETRIC_MINIMUM_COMMON_PREFIX"
    )
    with pytest.raises(Exception, match=failure["failure_id"]):
        producer.run_true_bit_partial_campaign_v58r1()
