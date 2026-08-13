from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_coordinate_basis_v13 as basis_producer
from acfqp import construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14 as verifier
from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as producer
from acfqp.domains.standard_2048 import Swipe2048Action, swipe_board_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_FACTORED_WORLD_MODEL_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_LINE_PROOF_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PROPOSAL_V14_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def evidence_and_verification():
    basis = basis_producer.build_standard_2048_coordinate_basis_v13()
    model = producer.prove_standard_2048_swipe_program_and_build_world_model_v14(
        producer.propose_standard_2048_swipe_program_v14(basis)
    )
    verification = verifier.verify_standard_2048_observation_proposed_program_bytes_independently_v14(
        coordinate_basis_bytes=basis.canonical_bytes,
        factored_world_model_bytes=model.canonical_bytes,
    )
    return basis, model, verification


def _resign(document: dict) -> bytes:
    proposal = document["proposal"]
    payload = {key: value for key, value in proposal.items() if key != "program_proposal_id"}
    proposal["program_proposal_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PROPOSAL_V14_DOMAIN, payload
    )
    proof = document["line_proof"]
    proof["program_proposal_id"] = proposal["program_proposal_id"]
    payload = {key: value for key, value in proof.items() if key != "program_line_proof_id"}
    proof["program_line_proof_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_PROGRAM_LINE_PROOF_V14_DOMAIN, payload
    )
    model = document["world_model"]
    model["program_proposal_id"] = proposal["program_proposal_id"]
    model["program_line_proof_id"] = proof["program_line_proof_id"]
    payload = {key: value for key, value in model.items() if key != "factored_world_model_id"}
    model["factored_world_model_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_FACTORED_WORLD_MODEL_V14_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_has_no_v14_producer_import() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_standard_2048_observation_proposed_program_v14" not in imports
    assert "acfqp.construction_k7_standard_2048_program_preregistration_v14" not in imports


def test_independent_verifier_replays_proposal_and_all_line_inputs(
    evidence_and_verification,
) -> None:
    _, model, verification = evidence_and_verification
    assert verification.factored_world_model_id == model.factored_world_model_id
    document = verification.to_document()
    assert document["source_and_validation_archives_independently_replayed"] is True
    assert document["four_candidate_programs_independently_scored"] is True
    assert document["unique_source_selection_and_heldout_acceptance_independently_replayed"] is True
    assert document["all_160000_line_inputs_independently_replayed"] is True
    assert document["deterministic_swipe_program_equivalence_verified"] is True
    assert document["stochastic_spawn_component_verified"] is False
    assert document["sample_tax_reduction_verified"] is False


def test_public_replayed_program_primitive_matches_ground_swipe() -> None:
    board = (1, 1, 2, 2, 3, 0, 3, 0, 4, 4, 4, 4, 0, 5, 5, 0)
    for action in Swipe2048Action:
        expected_board, expected_score, _ = swipe_board_v1(board, action)
        assert verifier.apply_independently_replayed_swipe_program_v14(
            board, action.value
        ) == (expected_board, expected_score)
    with pytest.raises(
        verifier.ConstructionK7Standard2048ObservationProposedProgramIndependentVerifierV14Error
    ):
        verifier.apply_independently_replayed_swipe_program_v14(board, "DIAGONAL")


@pytest.mark.parametrize(
    "attack",
    (
        lambda row: row["proposal"].__setitem__(
            "selected_candidate_key", "COMPACT_NONZERO_WITHOUT_MERGE"
        ),
        lambda row: row["proposal"]["source_candidate_evaluations"][1].__setitem__(
            "mismatch_count", 1
        ),
        lambda row: row["line_proof"].__setitem__("mismatch_count", 1),
        lambda row: row["line_proof"].__setitem__(
            "evaluation_trace_checksum_sha256", "f" * 64
        ),
        lambda row: row["world_model"]["stochastic_spawn_component"].__setitem__(
            "support_probability_or_independence_authority_present", True
        ),
        lambda row: row["world_model"].__setitem__("sample_tax_reduction_claimed", True),
    ),
)
def test_fully_resigned_program_proof_and_claim_attacks_are_rejected(
    evidence_and_verification, attack
) -> None:
    basis, model, _ = evidence_and_verification
    document = model.to_document()
    attack(document)
    with pytest.raises(
        verifier.ConstructionK7Standard2048ObservationProposedProgramIndependentVerifierV14Error
    ):
        verifier.verify_standard_2048_observation_proposed_program_bytes_independently_v14(
            coordinate_basis_bytes=basis.canonical_bytes,
            factored_world_model_bytes=_resign(document),
        )
