import os

import pytest

from acfqp.construction_k7_applicability_target_campaign_v87 import (
    CAMPAIGN_ID,
    ConstructionK7ApplicabilityTargetCampaignV87Error,
    run_applicability_target_campaign_v87,
    verify_applicability_target_campaign_v87,
)


def test_v87_campaign_identity_is_unfrozen_before_outcomes():
    assert CAMPAIGN_ID == "0" * 64


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
    assert gate["actual_completed_matched_target_count"] >= 2
    assert gate["every_successful_abstract_output_accepted_as_legal"] is True
    assert gate[
        "multi_step_abstract_ordering_coverage_on_every_completed_target"
    ] is True
    assert gate["passed"] is True
    assert document["query_local_exact_overlay_only_safety_authority"] is True
    assert document["multi_step_planning_primarily_in_abstract_model_claimed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
