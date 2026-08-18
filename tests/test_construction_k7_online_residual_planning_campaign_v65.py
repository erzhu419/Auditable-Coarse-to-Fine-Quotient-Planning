import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V65") != "1",
    reason="explicit registered V65 online residual campaign",
)
def test_v65_registered_campaign_is_frozen_and_safe():
    from acfqp.construction_k7_online_residual_planning_campaign_v65 import (
        run_online_residual_planning_campaign_v65,
        verify_online_residual_planning_campaign_v65,
    )

    value = verify_online_residual_planning_campaign_v65(
        run_online_residual_planning_campaign_v65()
    )
    document = value.to_document()
    assert document["registered_noninferiority_gate"]["passed"] is True
    assert document["all_ground_queries_followed_failed_certificates"] is True
    assert document["residual_proposals_used_only_for_abstract_action_order"] is True
    assert document["official_execution_allowed"] is False
