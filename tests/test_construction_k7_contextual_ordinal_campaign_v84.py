import os

import pytest

from acfqp.construction_k7_contextual_ordinal_campaign_v84 import (
    ConstructionK7ContextualOrdinalCampaignV84Error,
    run_contextual_ordinal_campaign_v84,
    verify_contextual_ordinal_campaign_v84,
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
    gate = document["registered_gate"]
    assert gate["actual_source_member_count"] == 6
    assert gate["actual_compiled_model_count"] >= 1
    assert gate["actual_compiled_source_member_count"] >= 2
    assert gate["every_compilation_eligible_group_compiled"] is True
    assert gate["every_compiled_model_uses_contextual_ordinal_operator"] is True
    assert gate["fresh_target_outcome_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
