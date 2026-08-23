from pathlib import Path

from acfqp.certificate_delta_invalidation_campaign_core_v175r1 import (
    PACKET_FAMILY,
    V175_FAILURE_ID,
    _frozen_failure,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v175r1_failure_predecessor_is_exact_and_nonrerunnable():
    document = _frozen_failure(
        (FREEZE / "v175_certificate_delta_invalidation_failure.json").read_bytes()
    )
    assert document["failure_id"] == V175_FAILURE_ID
    assert document["same_preregistration_identity_may_be_rerun"] is False
    assert document["target_outcomes_accessed"] is False
    assert PACKET_FAMILY
