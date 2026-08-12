from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_multiseed_independent_verifier_v1 as verifier
from acfqp import construction_k7_standard_2048_multiseed_partial_world_model_v1 as producer
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_MULTISEED_CAMPAIGN_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def campaign():
    return producer.run_standard_2048_multiseed_partial_world_model_campaign_v1()


def _resign_campaign(document: dict) -> bytes:
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_MULTISEED_CAMPAIGN_V1_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_has_no_producer_or_observer_import() -> None:
    path = Path(verifier.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_standard_2048_multiseed_partial_world_model_v1" not in imported
    assert "acfqp.construction_k7_standard_2048_spawn_observation_v1" not in imported


def test_independent_replay_covers_raw_observations_rows_plans_and_direct(campaign) -> None:
    result = verifier.verify_standard_2048_multiseed_campaign_bytes_independently_v1(
        campaign.canonical_bytes
    )
    document = result.to_document()
    assert document["raw_source_observations_replayed"] is True
    assert document["partial_support_rows_replayed"] is True
    assert document["robust_receding_plans_replayed"] is True
    assert document["matched_direct_controls_replayed"] is True
    assert document["final_world_model_row_count"] == 980
    assert document["total_receding_decision_count"] == 9
    assert document["process_or_iid_authority_independently_verified"] is False


def test_fully_resigned_raw_observation_attack_is_rejected_early(campaign) -> None:
    attacked = campaign.to_document()
    archive = attacked["source_observation_evidence"]["archive"]
    packed = bytearray.fromhex(archive["packed_rank_two_bits_hex"])
    packed[0] ^= 0x80
    archive["packed_rank_two_bits_hex"] = bytes(packed).hex()
    with pytest.raises(
        verifier.ConstructionK7Standard2048MultiseedIndependentVerifierV1Error
    ):
        verifier.verify_standard_2048_multiseed_campaign_bytes_independently_v1(
            _resign_campaign(attacked)
        )


def test_fully_resigned_claim_upgrade_is_rejected(campaign) -> None:
    attacked = campaign.to_document()
    attacked["broad_sample_efficiency_claimed"] = True
    with pytest.raises(
        verifier.ConstructionK7Standard2048MultiseedIndependentVerifierV1Error
    ):
        verifier.verify_standard_2048_multiseed_campaign_bytes_independently_v1(
            _resign_campaign(attacked)
        )


def test_resigned_unknown_partial_row_field_is_rejected(campaign) -> None:
    attacked = campaign.to_document()
    attacked["final_partial_world_model"]["rows"][0]["forged"] = True
    with pytest.raises(
        verifier.ConstructionK7Standard2048MultiseedIndependentVerifierV1Error
    ):
        verifier.verify_standard_2048_multiseed_campaign_bytes_independently_v1(
            _resign_campaign(attacked)
        )
