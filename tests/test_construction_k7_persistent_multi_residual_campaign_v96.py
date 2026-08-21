import os

import pytest

from acfqp import construction_k7_persistent_multi_residual_campaign_v96 as campaign


def test_v96_campaign_is_staged_only_after_outcome_free_preregistration():
    assert campaign.pre.PREREGISTRATION_ID == (
        "535c2020329e2dc0d6d2c9742dd2be0ddd1b5ec447d9e891b8468d7cc16d0d85"
    )
    assert campaign.CAMPAIGN_ID == "0" * 64
    assert campaign.EXPECTED_CANONICAL_BYTE_COUNT == 0
    assert campaign.EXPECTED_CANONICAL_SHA256 == "0" * 64


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V96") != "1",
    reason="explicit preregistered V96 persistent multi-residual campaign",
)
def test_v96_registered_campaign_runs_only_under_explicit_outcome_flag():
    value = campaign.run_persistent_multi_residual_campaign_v96()
    document = value.to_document()
    assert document["preregistration_id"] == campaign.pre.PREREGISTRATION_ID
    assert len(document["target_occurrences"]) == 2
    assert document["official_execution_allowed"] is False
