from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_fresh_board_support_independent_verifier_v2 as verifier
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as producer
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_CAMPAIGN_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_fresh_board_support_world_model_campaign_v2()
    verification = verifier.verify_standard_2048_fresh_board_support_campaign_bytes_independently_v2(
        campaign.canonical_bytes
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_CAMPAIGN_V2_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_verifier_does_not_import_producer_or_observation_module() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_standard_2048_fresh_board_support_world_model_v2" not in imports
    assert "acfqp.construction_k7_standard_2048_spawn_support_observation_v2" not in imports


def test_independent_replay_covers_raw_support_models_plans_and_controls(
    campaign_and_verification,
) -> None:
    _, verification = campaign_and_verification
    document = verification.to_document()
    assert document["raw_source_and_validation_observations_replayed"] is True
    assert document["support_proposal_and_intervals_replayed"] is True
    assert document["partial_rows_and_failed_proof_recovery_replayed"] is True
    assert document["fresh_board_robust_plans_and_direct_controls_replayed"] is True
    assert document["final_world_model_row_count"] == 2067
    assert document["total_receding_decision_count"] == 8
    assert document["physical_iid_or_full_game_authority_verified"] is False


@pytest.mark.parametrize(
    "attack",
    (
        lambda row: row["spawn_support_observation_evidence"]["source_archive"].__setitem__(
            "packed_records_hex",
            "00" + row["spawn_support_observation_evidence"]["source_archive"][
                "packed_records_hex"
            ][2:],
        ),
        lambda row: row["spawn_support_observation_evidence"]["proposal"].__setitem__(
            "selected_support_rule", "FIRST_EMPTY_ORDINAL_ONLY"
        ),
        lambda row: row["final_partial_world_model"]["rows"][0].__setitem__(
            "unknown_support_mass_upper", 0
        ),
        lambda row: row.__setitem__("broad_sample_efficiency_claimed", True),
    ),
)
def test_fully_resigned_semantic_and_claim_attacks_are_rejected(
    campaign_and_verification, attack
) -> None:
    campaign, _ = campaign_and_verification
    document = campaign.to_document()
    attack(document)
    with pytest.raises(
        verifier.ConstructionK7Standard2048FreshBoardSupportIndependentVerifierV2Error
    ):
        verifier.verify_standard_2048_fresh_board_support_campaign_bytes_independently_v2(
            _resign(document)
        )
