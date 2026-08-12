from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_exchangeability_campaign_v5 as producer
from acfqp import (
    construction_k7_standard_2048_exchangeability_independent_verifier_v5
    as verifier,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_exchangeability_campaign_v5()
    verification = (
        verifier.verify_standard_2048_exchangeability_campaign_bytes_independently_v5(
            campaign.canonical_bytes
        )
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "exchangeability_campaign_id"
    }
    document["exchangeability_campaign_id"] = content_id(
        verifier.DOMAINS["campaign"], payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_replays_both_arms(campaign_and_verification) -> None:
    campaign, verification = campaign_and_verification
    document = verification.to_document()
    assert document["campaign_id"] == campaign.campaign_id
    assert document["decision_count"] == 192
    assert document["meta_prior_abstract_route_count"] == 48
    assert document["strict_no_prior_abstract_route_count"] == 42
    assert document["offline_sample_tax_reduced"] is False
    assert document["exact_semantic_replay_passed"] is True
    assert document["producer_imported"] is False


def test_verifier_has_no_v5_producer_import() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_standard_2048_exchangeability_campaign_v5" not in imports


@pytest.mark.parametrize(
    "attack",
    (
        lambda row: row.__setitem__(
            "offline_sample_tax_reduced_below_v156_fixed_budget", True
        ),
        lambda row: row.__setitem__("structural_meta_prior_fallback_route_saving", 7),
        lambda row: row["structural_meta_prior_arm"].__setitem__(
            "fallback_route_count", 47
        ),
        lambda row: row["strict_no_prior_arm"]["episodes"][0]["decisions"][0][
            "certificate_attempts"
        ][0].__setitem__("cold_direct_accessed", True),
        lambda row: row["strict_no_prior_arm"]["episodes"][0]["decisions"][0][
            "route_decision"
        ].__setitem__("route", "FORGED_ROUTE"),
        lambda row: row.__setitem__("formal_confirmatory_gate_claimed", True),
        lambda row: row.__setitem__("broad_sample_efficiency_claimed", True),
    ),
)
def test_fully_resigned_attacks_are_rejected(
    campaign_and_verification, attack
) -> None:
    campaign, _ = campaign_and_verification
    document = campaign.to_document()
    attack(document)
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExchangeabilityIndependentVerifierV5Error
    ):
        verifier.verify_standard_2048_exchangeability_campaign_bytes_independently_v5(
            _resign(document)
        )
