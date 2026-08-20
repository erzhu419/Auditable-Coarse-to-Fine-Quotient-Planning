import os

import pytest

from acfqp.construction_k7_pooled_source_campaign_v78 import (
    ConstructionK7PooledSourceCampaignV78Error,
    run_pooled_source_campaign_v78,
    verify_pooled_source_campaign_v78,
)


def test_v78_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7PooledSourceCampaignV78Error):
        verify_pooled_source_campaign_v78(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_POOLED_SOURCE_V78") != "1",
    reason="explicit preregistered V78 source-only execution",
)
def test_v78_registered_source_only_gate_and_claim_boundary():
    document = run_pooled_source_campaign_v78().to_document()
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["actual_source_member_count"] == 2
    assert document["registered_gate"]["pooled_proposal_heldout_validated"] is True
    assert document["registered_gate"]["pooled_model_compiled"] is True
    assert document["registered_gate"]["fresh_target_outcome_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["complete_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
