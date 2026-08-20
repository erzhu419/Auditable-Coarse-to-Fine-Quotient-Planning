import os

import pytest

from acfqp.construction_k7_contextual_ordinal_campaign_v84 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    ConstructionK7ContextualOrdinalCampaignV84Error,
    run_contextual_ordinal_campaign_v84,
    verify_contextual_ordinal_campaign_v84,
)


def test_v84_failed_campaign_identity_is_frozen():
    assert CAMPAIGN_ID == (
        "1828a9c92459da992f2e691b5a8f935005d4da5981070728f4c5d9a0a4e9db28"
    )
    assert EXPECTED_CANONICAL_BYTE_COUNT == 8_666_449
    assert EXPECTED_CANONICAL_SHA256 == (
        "66bf9d5e1252c527cb4e4208b5590b6047a121921552f66442a6248ed7745c13"
    )


def test_v84_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ContextualOrdinalCampaignV84Error):
        verify_contextual_ordinal_campaign_v84(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_CONTEXTUAL_ORDINAL_V84") != "1",
    reason="explicit preregistered V84 source-only execution",
)
def test_v84_runs_exact_preregistered_source_gate():
    document = run_contextual_ordinal_campaign_v84().to_document()
    assert document["campaign_id"] == CAMPAIGN_ID
    gate = document["registered_gate"]
    assert gate["actual_source_member_count"] == 6
    assert gate["actual_compiled_model_count"] == 0
    assert gate["actual_compiled_source_member_count"] == 0
    assert gate["passed"] is False
    assert gate["fresh_target_outcome_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
