import os

import pytest

from acfqp.construction_k7_projected_disagreement_campaign_v85r1 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    ConstructionK7ProjectedDisagreementCampaignV85R1Error,
    run_projected_disagreement_campaign_v85r1,
    verify_projected_disagreement_campaign_v85r1,
)


def test_v85r1_campaign_identity_is_frozen_after_registered_execution():
    assert CAMPAIGN_ID == (
        "da749b6ad8996aba86896476fd7293540cca77cd1b4db7145b9bf4fe2759ec70"
    )
    assert EXPECTED_CANONICAL_BYTE_COUNT == 6_400_725
    assert EXPECTED_CANONICAL_SHA256 == (
        "9371c385cdbfa795752c79e57e3a557f278707df5341b52f81cfdc291e440541"
    )


def test_v85r1_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ProjectedDisagreementCampaignV85R1Error):
        verify_projected_disagreement_campaign_v85r1(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PROJECTED_DISAGREEMENT_V85R1") != "1",
    reason="explicit preregistered V85r1 source-only execution",
)
def test_v85r1_runs_exact_preregistered_source_gate():
    document = run_projected_disagreement_campaign_v85r1().to_document()
    gate = document["registered_gate"]
    assert gate["actual_source_member_count"] == 6
    assert gate["actual_compiled_model_count"] >= 1
    assert gate["actual_compiled_source_member_count"] >= 2
    assert gate["passed"] is True
    assert gate["fresh_target_outcome_count"] == 0
    assert document["predecessor_producer_dereference_used"] is False
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
