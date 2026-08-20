import os

import pytest

from acfqp.construction_k7_all_frontier_campaign_v83 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    ConstructionK7AllFrontierCampaignV83Error,
    run_all_frontier_campaign_v83,
    verify_all_frontier_campaign_v83,
)


def test_v83_failed_campaign_identity_is_frozen():
    assert CAMPAIGN_ID == (
        "9befdfcfd6b5a6673cd9e6a9f88837865f9c535febbc8cf57eadbbaae18e7bb4"
    )
    assert EXPECTED_CANONICAL_BYTE_COUNT == 4_214_582
    assert EXPECTED_CANONICAL_SHA256 == (
        "437cc104ba40ea3e28adcf7c69c0b4a271acd3628947d055dc02a9120f911ca9"
    )


def test_v83_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7AllFrontierCampaignV83Error):
        verify_all_frontier_campaign_v83(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_ALL_FRONTIER_V83") != "1",
    reason="explicit preregistered V83 source-only execution",
)
def test_v83_runs_exact_frozen_source_gate():
    document = run_all_frontier_campaign_v83().to_document()
    assert document["campaign_id"] == CAMPAIGN_ID
    assert document["preregistration_id"]
    assert document["registered_gate"]["actual_source_member_count"] == 6
    assert document["registered_gate"]["fresh_target_outcome_count"] == 0
    assert document["registered_gate"]["passed"] is False
    assert document["retained_model_diagnostics"]["compiled_model_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
