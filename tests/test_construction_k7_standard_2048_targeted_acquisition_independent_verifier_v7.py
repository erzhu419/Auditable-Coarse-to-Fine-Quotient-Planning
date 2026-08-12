from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_targeted_acquisition_campaign_v7 as producer
from acfqp import (
    construction_k7_standard_2048_targeted_acquisition_independent_verifier_v7
    as verifier,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_targeted_acquisition_campaign_v7()
    verification = (
        verifier.verify_standard_2048_targeted_acquisition_campaign_bytes_independently_v7(
            campaign.canonical_bytes
        )
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "targeted_acquisition_campaign_id"
    }
    document["targeted_acquisition_campaign_id"] = content_id(
        verifier.DOMAINS["campaign"], payload
    )
    return canonical_json_bytes(document)


def test_independent_replay_confirms_scoped_reduction(campaign_and_verification) -> None:
    campaign, verification = campaign_and_verification
    document = verification.to_document()
    assert document["campaign_id"] == campaign.campaign_id
    assert document["decision_count"] == 256
    assert document["targeted_observation_count"] == 55788
    assert document["global_control_observation_count"] == 147456
    assert document["exact_semantic_replay_passed"] is True
    assert document["producer_imported"] is False
    assert document["broad_sample_efficiency_verified"] is False


def test_verifier_has_no_v7_producer_import() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_standard_2048_targeted_acquisition_campaign_v7" not in imports


@pytest.mark.parametrize(
    "attack",
    (
        lambda row: row.__setitem__("targeted_offline_observation_saving", 91669),
        lambda row: row.__setitem__("targeted_offline_sample_tax_reduced", False),
        lambda row: row["frontier_conditioned_arm"].__setitem__(
            "unique_offline_transition_observation_count", 55787
        ),
        lambda row: row["frontier_conditioned_arm"]["episodes"][0]["decisions"][0][
            "certificate_attempts"
        ][0]["acquisition_evidence"].__setitem__(
            "unique_offline_transition_observation_count", 191
        ),
        lambda row: row["frontier_conditioned_arm"]["episodes"][0]["decisions"][0][
            "route_decision"
        ].__setitem__("route", "FORGED_ROUTE"),
        lambda row: row["targeted_source_archive"].__setitem__("packed_sha256", "0" * 64),
        lambda row: row.__setitem__("broad_sample_efficiency_claimed", True),
        lambda row: row.__setitem__("official_execution_allowed", True),
    ),
)
def test_fully_resigned_attacks_are_rejected(
    campaign_and_verification, attack
) -> None:
    campaign, _ = campaign_and_verification
    document = campaign.to_document()
    attack(document)
    with pytest.raises(
        verifier.ConstructionK7Standard2048TargetedAcquisitionIndependentVerifierV7Error
    ):
        verifier.verify_standard_2048_targeted_acquisition_campaign_bytes_independently_v7(
            _resign(document)
        )
