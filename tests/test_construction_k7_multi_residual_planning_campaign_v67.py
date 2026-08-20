import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V67") != "1",
    reason="explicit registered V67 joint residual planning campaign",
)
def test_v67_registered_joint_planning_gate_is_frozen():
    from acfqp.construction_k7_multi_residual_planning_campaign_v67 import (
        run_multi_residual_planning_campaign_v67,
        verify_multi_residual_planning_campaign_v67,
    )

    value = verify_multi_residual_planning_campaign_v67(
        run_multi_residual_planning_campaign_v67()
    )
    document = value.to_document()
    assert document["registered_joint_planning_gate"]["passed"] is True
    assert document["registered_joint_planning_gate"][
        "prior_multi_proposal_occurrence_count"
    ] > 0
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["joint_abstract_plan_used_as_safety_authority"] is False
