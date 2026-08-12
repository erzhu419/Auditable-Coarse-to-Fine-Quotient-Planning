from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_adaptive_sample_tax_v3 as producer
from acfqp import (
    construction_k7_standard_2048_adaptive_sample_tax_independent_verifier_v3
    as verifier,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_CAMPAIGN_V3_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_adaptive_sample_tax_campaign_v3()
    verification = verifier.verify_standard_2048_adaptive_sample_tax_campaign_bytes_independently_v3(
        campaign.canonical_bytes
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_CAMPAIGN_V3_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verification_replays_stopping_and_controls(
    campaign_and_verification,
) -> None:
    _, verification = campaign_and_verification
    document = verification.to_document()
    assert document["fixed_budget_draws"] == 147456
    assert document["adaptive_meta_draws"] == 192
    assert document["adaptive_no_prior_draws"] == 192
    assert document["raw_prefixes_and_stopping_replayed"] is True
    assert document["matched_certificate_and_direct_controls_replayed"] is True
    assert document["meta_prior_and_ood_authority_replayed"] is True
    assert document["broad_sample_efficiency_verified"] is False


def test_verifier_has_no_static_producer_import() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_standard_2048_adaptive_sample_tax_v3" not in imports


@pytest.mark.parametrize(
    "attack",
    (
        lambda row: row["identity_bound_meta_prior_arm"].__setitem__(
            "offline_transition_observation_count", 1
        ),
        lambda row: row["identity_bound_meta_prior"].__setitem__(
            "certificate_authority", True
        ),
        lambda row: row["strict_no_prior_arm"]["checkpoints"][0].__setitem__(
            "source_prefix_sha256", "0" * 64
        ),
        lambda row: row.__setitem__("broad_sample_efficiency_claimed", True),
        lambda row: row["actual_initial_board_long_episode_control"].__setitem__(
            "long_initial_board_sample_tax_solved", True
        ),
        lambda row: row["fresh_unselected_midgame_control"].__setitem__(
            "cross_board_family_sample_tax_solved", True
        ),
    ),
)
def test_fully_resigned_attacks_are_rejected(
    campaign_and_verification, attack
) -> None:
    campaign, _ = campaign_and_verification
    document = campaign.to_document()
    attack(document)
    with pytest.raises(
        verifier.ConstructionK7Standard2048AdaptiveSampleTaxIndependentVerifierV3Error
    ):
        verifier.verify_standard_2048_adaptive_sample_tax_campaign_bytes_independently_v3(
            _resign(document)
        )
