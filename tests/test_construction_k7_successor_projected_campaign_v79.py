import os

import pytest

from acfqp.construction_k7_successor_projected_campaign_v79 import (
    ConstructionK7SuccessorProjectedCampaignV79Error,
    run_successor_projected_campaign_v79,
    verify_successor_projected_campaign_v79,
)


def test_v79_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7SuccessorProjectedCampaignV79Error):
        verify_successor_projected_campaign_v79(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_SUCCESSOR_PROJECTED_V79") != "1",
    reason="explicit preregistered V79 source-only execution",
)
def test_v79_runs_exact_frozen_source_gate():
    document = run_successor_projected_campaign_v79().to_document()
    assert document["preregistration_id"]
    assert document["registered_gate"]["actual_source_member_count"] == 2
    assert document["registered_gate"]["fresh_target_outcome_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
