import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V66") != "1",
    reason="explicit registered V66 combined-model campaign",
)
def test_v66_registered_combined_model_gate_is_frozen():
    from acfqp.construction_k7_combined_model_planning_campaign_v66 import (
        run_combined_model_planning_campaign_v66,
        verify_combined_model_planning_campaign_v66,
    )

    value = verify_combined_model_planning_campaign_v66(
        run_combined_model_planning_campaign_v66()
    )
    document = value.to_document()
    assert document["registered_combined_planning_gate"]["passed"] is True
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["combined_abstract_plan_used_as_safety_authority"] is False
