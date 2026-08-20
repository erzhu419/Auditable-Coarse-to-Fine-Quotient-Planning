import os

import pytest

from acfqp.construction_k7_projected_disagreement_campaign_v85 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PRE_OUTCOME_FAILURE_ID,
    ConstructionK7ProjectedDisagreementCampaignV85Error,
    run_projected_disagreement_campaign_v85,
    frozen_pre_outcome_failure_v85,
    verify_projected_disagreement_campaign_v85,
)


def test_v85_campaign_identity_is_unfrozen_before_registered_execution():
    assert CAMPAIGN_ID == "0" * 64
    assert EXPECTED_CANONICAL_BYTE_COUNT == 0
    assert EXPECTED_CANONICAL_SHA256 == "0" * 64
    assert PRE_OUTCOME_FAILURE_ID != "0" * 64


def test_v85_pre_outcome_failure_is_frozen_without_source_outcomes():
    document = frozen_pre_outcome_failure_v85()
    assert document["failure_id"] == PRE_OUTCOME_FAILURE_ID
    assert document["fresh_source_member_execution_started"] is False
    assert document["fresh_source_outcome_count"] == 0
    assert document["same_identity_rerun_forbidden"] is True
    assert document["official_execution_allowed"] is False


def test_v85_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ProjectedDisagreementCampaignV85Error):
        verify_projected_disagreement_campaign_v85(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PROJECTED_DISAGREEMENT_V85") != "1",
    reason="explicit preregistered V85 source-only execution",
)
def test_v85_runs_exact_preregistered_source_gate():
    with pytest.raises(
        ConstructionK7ProjectedDisagreementCampaignV85Error,
        match="same-identity rerun forbidden",
    ):
        run_projected_disagreement_campaign_v85()
