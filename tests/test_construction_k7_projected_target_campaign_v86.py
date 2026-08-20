import os

import pytest

from acfqp.construction_k7_projected_target_campaign_v86 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    ConstructionK7ProjectedTargetCampaignV86Error,
    run_projected_target_campaign_v86,
    verify_projected_target_campaign_v86,
)


def test_v86_campaign_identity_is_unfrozen_before_outcomes():
    assert CAMPAIGN_ID == "0" * 64
    assert EXPECTED_CANONICAL_BYTE_COUNT == 0
    assert EXPECTED_CANONICAL_SHA256 == "0" * 64


def test_v86_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ProjectedTargetCampaignV86Error):
        verify_projected_target_campaign_v86(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PROJECTED_TARGET_V86") != "1",
    reason="explicit preregistered V86 fresh-target execution",
)
def test_v86_runs_exact_preregistered_target_gate():
    document = run_projected_target_campaign_v86().to_document()
    gate = document["registered_gate"]
    assert gate["actual_target_occurrence_count"] == 6
    assert gate["actual_completed_matched_target_count"] >= 2
    assert gate["passed"] is True
    assert document["certificate_failure_only_local_ground_recovery_observed"] is True
    assert document["query_local_exact_overlay_only_safety_authority"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
