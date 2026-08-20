import os

import pytest

from acfqp.construction_k7_structural_route_campaign_v80 import (
    ConstructionK7StructuralRouteCampaignV80Error,
    run_structural_route_campaign_v80,
    verify_structural_route_campaign_v80,
)


def test_v80_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7StructuralRouteCampaignV80Error):
        verify_structural_route_campaign_v80(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_STRUCTURAL_ROUTE_V80") != "1",
    reason="explicit preregistered V80 source-only execution",
)
def test_v80_runs_exact_frozen_source_gate():
    document = run_structural_route_campaign_v80().to_document()
    assert document["preregistration_id"]
    assert document["registered_gate"]["actual_source_member_count"] == 2
    assert document["registered_gate"]["fresh_target_outcome_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
