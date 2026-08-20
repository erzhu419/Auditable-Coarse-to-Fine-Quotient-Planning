import os

import pytest

from acfqp.construction_k7_fail_closed_priority_campaign_v75r3 import (
    ConstructionK7FailClosedPriorityCampaignV75R3Error,
    run_fail_closed_priority_campaign_v75r3,
    verify_fail_closed_priority_campaign_v75r3,
)


def test_v75r3_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7FailClosedPriorityCampaignV75R3Error):
        verify_fail_closed_priority_campaign_v75r3(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V75R3") != "1",
    reason="explicit preregistered V75r3 fail-closed campaign execution",
)
def test_v75r3_registered_campaign_preserves_gate_and_claim_boundary():
    document = run_fail_closed_priority_campaign_v75r3().to_document()
    assert document["failed_target_arms_retained_before_aggregation"] is True
    assert type(document["typed_target_arm_failures"]) is list
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
