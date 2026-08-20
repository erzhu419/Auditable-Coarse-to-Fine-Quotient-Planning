import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V68") != "1",
    reason="explicit registered V68 relational world-model campaign",
)
def test_v68_registered_relational_world_model_gate_is_frozen():
    from acfqp.construction_k7_relational_world_model_campaign_v68 import (
        run_relational_world_model_campaign_v68,
        verify_relational_world_model_campaign_v68,
    )

    value = verify_relational_world_model_campaign_v68(
        run_relational_world_model_campaign_v68()
    )
    document = value.to_document()
    gate = document["registered_relational_world_model_gate"]
    assert gate["passed"] is True
    assert gate["prior_relational_plan_success_count"] > 0
    assert gate["prior_active_world_model_occurrence_count"] > 0
    assert gate["prior_terminal_candidate_rejection_count"] > 0
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["relational_abstract_plan_used_as_safety_authority"] is False
