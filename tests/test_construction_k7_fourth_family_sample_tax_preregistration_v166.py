import hashlib

import pytest

from acfqp.construction_k7_fourth_family_sample_tax_preregistration_v166 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    campaign_config_v166,
    freeze_fourth_family_sample_tax_preregistration_v166,
)


def test_v166_preregistration_is_outcome_free_and_binds_four_families():
    frozen = freeze_fourth_family_sample_tax_preregistration_v166()
    document = frozen.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"][
        "fourth_family_sample_tax_transfer_observed"
    ] is False
    assert document["claim_boundary"]["profitability_classifier_issued"] is False
    assert document["target_occurrences"] == [
        {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
    ]
    assert len({row["family"] for row in document["target_occurrences"]}) == 4
    assert document["target_worker_count"] == 2
    assert all(document["registered_gate"].values())
    config = campaign_config_v166()
    assert config["required_target_occurrence_count"] == 8


def test_v166_frozen_preregistration_identity():
    if PREREGISTRATION_ID == "0" * 64:
        pytest.skip("V166 preregistration not frozen")
    frozen = freeze_fourth_family_sample_tax_preregistration_v166()
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert (
        hashlib.sha256(frozen.canonical_bytes).hexdigest()
        == EXPECTED_CANONICAL_SHA256
    )
