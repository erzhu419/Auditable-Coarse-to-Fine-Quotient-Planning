import os

import pytest

from acfqp import construction_k7_post_dependency_campaign_v97 as campaign


def test_v97_campaign_is_staged_after_outcome_free_preregistration():
    assert campaign.pre.PREREGISTRATION_ID == (
        "99c6ae8e5c71ea1f5b92fc01117d979772d0958a255926beb81d032837b008fa"
    )
    assert campaign.CAMPAIGN_ID == "0" * 64
    assert campaign.EXPECTED_CANONICAL_BYTE_COUNT == 0
    assert campaign.EXPECTED_CANONICAL_SHA256 == "0" * 64


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V97") != "1",
    reason="explicit preregistered V97 post-dependency campaign",
)
def test_v97_registered_campaign_runs_only_under_explicit_outcome_flag():
    from pathlib import Path

    value = campaign.run_post_dependency_campaign_v97(
        Path(".tmp/exact-freeze/v96_persistent_multi_residual_campaign.json").read_bytes(),
        Path(".tmp/exact-freeze/v96_persistent_multi_residual_verification.json").read_bytes(),
    )
    document = value.to_document()
    assert document["preregistration_id"] == campaign.pre.PREREGISTRATION_ID
    assert len(document["target_occurrences"]) == 4
    assert document["official_execution_allowed"] is False
