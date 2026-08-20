import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V69") != "1",
    reason="explicit registered V69 source-complete relational campaign",
)
def test_v69_registered_source_complete_gate_is_frozen():
    from acfqp.construction_k7_source_complete_relational_campaign_v69 import (
        run_source_complete_relational_campaign_v69,
        verify_source_complete_relational_campaign_v69,
    )

    value = verify_source_complete_relational_campaign_v69(
        run_source_complete_relational_campaign_v69()
    )
    document = value.to_document()
    gate = document["registered_source_complete_gate"]
    assert gate["passed"] is True
    assert gate["prior_relational_plan_success_count"] > 0
    assert gate["prior_active_world_model_occurrence_count"] > 0
    assert gate["source_complete_episode_count"] == gate[
        "required_source_complete_episode_count"
    ]
    assert document["all_v28_source_rows_retained"] is True
    assert document["relational_abstract_plan_used_as_safety_authority"] is False
