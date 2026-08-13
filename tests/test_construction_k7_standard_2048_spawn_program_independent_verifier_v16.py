from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_spawn_program_independent_verifier_v16 as verifier
from acfqp import construction_k7_standard_2048_spawn_program_v16 as producer
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_spawn_program_campaign_v16()
    verification = verifier.verify_standard_2048_spawn_program_bytes_independently_v16(
        campaign.canonical_bytes
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "spawn_program_campaign_id"
    }
    document["spawn_program_campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_imports_no_v16_producer_or_preregistration() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    assert "acfqp.construction_k7_standard_2048_spawn_program_v16" not in imports
    assert (
        "acfqp.construction_k7_standard_2048_spawn_program_preregistration_v16"
        not in imports
    )


def test_complete_observation_proposal_and_proof_are_replayed(
    campaign_and_verification,
) -> None:
    campaign, verification = campaign_and_verification
    assert verification.campaign_id == campaign.campaign_id
    assert verification.verification_id == verifier.EXPECTED_VERIFICATION_ID
    document = verification.to_document()
    assert document["source_and_validation_observations_independently_replayed"] is True
    assert document["all_25_candidate_programs_independently_scored"] is True
    assert document[
        "unique_source_selection_and_heldout_acceptance_independently_replayed"
    ] is True
    assert document["all_65534_empty_support_subsets_independently_replayed"] is True
    assert document["exact_rational_spawn_equivalence_independently_verified"] is True
    assert document["composed_swipe_and_spawn_world_model_independently_verified"] is True


def test_sample_and_claim_boundaries_remain_scoped(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    document = verification.to_document()
    assert document["registered_observation_axis_reduction_independently_verified"] is True
    assert document["target_planning_or_full_game_verified"] is False
    assert document["broad_sample_efficiency_or_total_work_saving_verified"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize(
    "attack",
    ("observation", "selection", "proof", "model", "sample", "claim"),
)
def test_fully_resigned_attacks_are_rejected_before_expensive_replay(
    campaign_and_verification, attack: str
) -> None:
    campaign, _ = campaign_and_verification
    document = copy.deepcopy(campaign.to_document())
    if attack == "observation":
        document["source_observation_archive"]["rows"][0]["spawned_rank"] = 9
    elif attack == "selection":
        document["spawn_program_proposal"]["selected_candidate_key"] = "FORGED"
    elif attack == "proof":
        document["spawn_program_support_proof"]["mismatch_count"] = 1
    elif attack == "model":
        document["synthesized_world_model"]["ground_access_before_certificate_failure"] = True
    elif attack == "sample":
        document["registered_observation_difference"] = 999999
    else:
        document["full_standard_2048_game_completed"] = True
    forged = _resign(document)
    with pytest.raises(
        verifier.ConstructionK7Standard2048SpawnProgramIndependentVerifierV16Error
    ):
        verifier.verify_standard_2048_spawn_program_bytes_independently_v16(forged)


def test_verification_cannot_be_caller_minted(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    with pytest.raises(
        verifier.ConstructionK7Standard2048SpawnProgramIndependentVerifierV16Error
    ):
        verifier.Standard2048SpawnProgramIndependentVerificationV16(
            object(),
            verification.canonical_bytes,
            verification.verification_id,
            verification.campaign_id,
        )
