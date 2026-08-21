import os

import pytest

from acfqp.construction_k7_applicability_target_campaign_v87 import (
    CAMPAIGN_ID,
    ConstructionK7ApplicabilityTargetCampaignV87Error,
    run_applicability_target_campaign_v87,
    verify_applicability_target_campaign_v87,
)


def test_v87_failed_campaign_identity_is_frozen():
    assert CAMPAIGN_ID == (
        "e5432505db2bf911324d3d719986493bfa81aa131439ee31367da9329cc2b0d8"
    )


def test_v87_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ApplicabilityTargetCampaignV87Error):
        verify_applicability_target_campaign_v87(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_APPLICABILITY_TARGET_V87") != "1",
    reason="explicit preregistered V87 fresh-target execution",
)
def test_v87_runs_exact_preregistered_target_gate():
    document = run_applicability_target_campaign_v87().to_document()
    gate = document["registered_gate"]
    assert gate["actual_target_occurrence_count"] == 6
    assert gate["actual_completed_matched_target_count"] == 0
    assert gate["actual_structurally_compatible_target_count"] == 0
    assert gate["passed"] is False
    assert document["query_local_exact_overlay_only_safety_authority"] is True
    assert document["multi_step_planning_primarily_in_abstract_model_claimed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
