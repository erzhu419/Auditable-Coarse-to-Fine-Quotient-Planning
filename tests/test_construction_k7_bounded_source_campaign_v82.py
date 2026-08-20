import os

import pytest

from acfqp.construction_k7_bounded_source_campaign_v82 import (
    ConstructionK7BoundedSourceCampaignV82Error,
    run_bounded_source_campaign_v82,
    verify_bounded_source_campaign_v82,
)


def test_v82_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7BoundedSourceCampaignV82Error):
        verify_bounded_source_campaign_v82(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_BOUNDED_SOURCE_V82") != "1",
    reason="explicit preregistered V82 source-only execution",
)
def test_v82_runs_exact_frozen_source_gate():
    document = run_bounded_source_campaign_v82().to_document()
    assert document["preregistration_id"]
    assert document["registered_gate"]["actual_source_member_count"] == 6
    assert document["registered_gate"]["fresh_target_outcome_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
