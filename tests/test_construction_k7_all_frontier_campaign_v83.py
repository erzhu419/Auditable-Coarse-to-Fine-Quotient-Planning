import os

import pytest

from acfqp.construction_k7_all_frontier_campaign_v83 import (
    ConstructionK7AllFrontierCampaignV83Error,
    run_all_frontier_campaign_v83,
    verify_all_frontier_campaign_v83,
)


def test_v83_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7AllFrontierCampaignV83Error):
        verify_all_frontier_campaign_v83(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_ALL_FRONTIER_V83") != "1",
    reason="explicit preregistered V83 source-only execution",
)
def test_v83_runs_exact_frozen_source_gate():
    document = run_all_frontier_campaign_v83().to_document()
    assert document["preregistration_id"]
    assert document["registered_gate"]["actual_source_member_count"] == 6
    assert document["registered_gate"]["fresh_target_outcome_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
