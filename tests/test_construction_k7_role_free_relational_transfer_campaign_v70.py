import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V70") != "1",
    reason="explicit registered V70 role-free transfer campaign",
)
def test_v70_registered_role_free_transfer_gate_is_frozen():
    from acfqp.construction_k7_role_free_relational_transfer_campaign_v70 import (
        run_role_free_relational_transfer_campaign_v70,
        verify_role_free_relational_transfer_campaign_v70,
    )

    value = verify_role_free_relational_transfer_campaign_v70(
        run_role_free_relational_transfer_campaign_v70()
    )
    document = value.to_document()
    gate = document["registered_role_free_transfer_gate"]
    assert gate["passed"] is True
    assert gate["transferred_plan_success_count"] > 0
    assert gate["incompatible_schema_ood_rejection_count"] == gate[
        "required_ood_rejection_count"
    ]
    assert document["online_transfer_planner_integrated"] is False
    assert document["transferred_abstract_plan_used_as_safety_authority"] is False
