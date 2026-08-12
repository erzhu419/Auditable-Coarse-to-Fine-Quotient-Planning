from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as producer
from acfqp import (
    construction_k7_standard_2048_affine_meta_prior_independent_verifier_v4
    as verifier,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_AFFINE_CAMPAIGN_V4_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_affine_meta_prior_campaign_v4()
    verification = verifier.verify_standard_2048_affine_meta_prior_campaign_bytes_independently_v4(
        campaign.canonical_bytes
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {key: value for key, value in document.items() if key != "affine_campaign_id"}
    document["affine_campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_AFFINE_CAMPAIGN_V4_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_replays_affine_and_fallback(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    document = verification.to_document()
    assert document["decision_count"] == 48
    assert document["abstract_route_count"] == 47
    assert document["fallback_route_count"] == 1
    assert document["raw_rank_prefix_replayed"] is True
    assert document["affine_endpoint_certificates_replayed"] is True
    assert document["fallback_and_cold_direct_replayed"] is True
    assert document["broad_sample_efficiency_verified"] is False


def test_verifier_has_no_static_v4_producer_import() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_standard_2048_affine_meta_prior_v4" not in imports


@pytest.mark.parametrize(
    "attack",
    (
        lambda row: row["affine_meta_prior"].__setitem__(
            "offline_prior_training_observation_count", 1
        ),
        lambda row: row["affine_meta_prior"].__setitem__(
            "uniform_position_law_observation_derived", True
        ),
        lambda row: row["episodes"][0]["decisions"][0]["affine_certificate"].__setitem__(
            "cold_direct_accessed", True
        ),
        lambda row: row["episodes"][3]["decisions"][4]["route_decision"].__setitem__(
            "route", "ABSTRACT_AFFINE"
        ),
        lambda row: row.__setitem__("cold_ground_fallback_route_count", 0),
        lambda row: row.__setitem__("tile_2048_reached", True),
        lambda row: row.__setitem__("broad_sample_efficiency_claimed", True),
    ),
)
def test_fully_resigned_attacks_are_rejected(campaign_and_verification, attack) -> None:
    campaign, _ = campaign_and_verification
    document = campaign.to_document()
    attack(document)
    with pytest.raises(
        verifier.ConstructionK7Standard2048AffineMetaPriorIndependentVerifierV4Error
    ):
        verifier.verify_standard_2048_affine_meta_prior_campaign_bytes_independently_v4(
            _resign(document)
        )
