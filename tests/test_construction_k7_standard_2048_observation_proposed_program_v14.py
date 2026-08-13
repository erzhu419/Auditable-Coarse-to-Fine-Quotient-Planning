from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_coordinate_basis_v13 as basis_v13
from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as program
from acfqp.domains.standard_2048 import Swipe2048Action, swipe_board_v1


@pytest.fixture(scope="module")
def proposal_and_model():
    proposal = program.propose_standard_2048_swipe_program_v14()
    model = program.prove_standard_2048_swipe_program_and_build_world_model_v14(
        proposal
    )
    return proposal, model


def test_observations_uniquely_propose_the_correct_line_program(
    proposal_and_model,
) -> None:
    proposal, _ = proposal_and_model
    document = proposal.to_document()
    assert proposal.program_proposal_id == program.PROGRAM_PROPOSAL_ID
    assert proposal.selected_candidate_key == (
        "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP"
    )
    assert document["selected_candidate_id"] == program.SELECTED_PROGRAM_CANDIDATE_ID
    assert [row["mismatch_count"] for row in document["source_candidate_evaluations"]] == [
        214,
        0,
        29,
        66,
    ]
    assert document["validation_mismatch_count"] == 0
    assert document["heldout_validation_passed"] is True
    assert document["source_selected_before_validation_read"] is True
    assert document["proposal_has_certificate_authority"] is False


def test_program_proposal_does_not_read_exact_swipe_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    basis = basis_v13.build_standard_2048_coordinate_basis_v13()

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("proposal read exact swipe reference")

    monkeypatch.setattr(program, "swipe_board_v1", forbidden)
    proposal = program.propose_standard_2048_swipe_program_v14(basis)
    assert proposal.program_proposal_id == program.PROGRAM_PROPOSAL_ID


def test_exhaustive_line_proof_lifts_to_reusable_deterministic_model(
    proposal_and_model,
) -> None:
    _, model = proposal_and_model
    assert program.verify_standard_2048_observation_proposed_world_model_v14(model) is model
    document = model.to_document()
    proof = document["line_proof"]
    assert model.program_line_proof_id == program.PROGRAM_LINE_PROOF_ID
    assert model.factored_world_model_id == program.FACTORED_WORLD_MODEL_ID
    assert proof["exhaustive_line_input_count"] == 160000
    assert proof["candidate_line_evaluation_count"] == 160000
    assert proof["reference_swipe_line_evaluation_count"] == 160000
    assert proof["mismatch_count"] == 0
    assert proof["first_mismatch"] is None
    assert proof["evaluation_trace_checksum_sha256"] == program.LINE_PROOF_TRACE_SHA256
    assert proof["whole_board_equivalence_derived_from_four_independent_oriented_lines"] is True


@pytest.mark.parametrize(
    ("board", "action"),
    (
        ((1, 1, 1, 1) + (0,) * 12, Swipe2048Action.LEFT),
        ((1, 0, 1, 1) + (0,) * 12, Swipe2048Action.RIGHT),
        ((1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0), Swipe2048Action.UP),
        ((2, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0), Swipe2048Action.DOWN),
    ),
)
def test_program_matches_public_swipe_on_directional_cases(board, action) -> None:
    expected_board, expected_score, _ = swipe_board_v1(board, action)
    observed_board, observed_score = program.apply_observation_proposed_swipe_program_v14(
        board,
        action.value,
        candidate_key="COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP",
    )
    assert (observed_board, observed_score) == (expected_board, expected_score)


def test_spawn_uncertainty_and_sample_tax_claims_remain_locked(
    proposal_and_model,
) -> None:
    _, model = proposal_and_model
    document = model.to_document()["world_model"]
    assert document["deterministic_swipe_component"]["status"] == (
        "EXACT_BOUNDED_PROGRAM_EQUIVALENCE_VERIFIED"
    )
    spawn = document["stochastic_spawn_component"]
    assert spawn["status"] == "UNKNOWN_PENDING_EXACT_LOCAL_OBLIGATION_CLOSURE"
    assert spawn["support_probability_or_independence_authority_present"] is False
    assert document["model_can_issue_sound_plan_certificate_without_spawn_closure"] is False
    assert document["exact_local_spawn_obligation_closure_still_required"] is True
    assert document["offline_transition_observation_count"] == 768
    assert document["matched_fixed_control_offline_transition_observation_count"] == 8192
    assert document["exhaustive_program_proof_compute_evaluation_count"] == 160000
    assert document["observation_and_compute_axes_reported_separately"] is True
    assert document["target_execution_performed"] is False
    assert document["sample_tax_reduction_claimed"] is False


def test_bad_reference_or_object_tampering_fails_closed(
    proposal_and_model, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal, model = proposal_and_model
    original = program.swipe_board_v1

    def wrong_reference(board, action):
        moved, score, changed = original(board, action)
        return moved, score + 1, changed

    monkeypatch.setattr(program, "swipe_board_v1", wrong_reference)
    with pytest.raises(program.ConstructionK7Standard2048ObservationProposedProgramV14Error):
        program.prove_standard_2048_swipe_program_and_build_world_model_v14(proposal)

    forged = copy.copy(model)
    object.__setattr__(forged, "factored_world_model_id", "f" * 64)
    with pytest.raises(program.ConstructionK7Standard2048ObservationProposedProgramV14Error):
        program.verify_standard_2048_observation_proposed_world_model_v14(forged)
    with pytest.raises(program.ConstructionK7Standard2048ObservationProposedProgramV14Error):
        program.Standard2048SwipeProgramProposalV14(
            object(),
            proposal.canonical_bytes,
            proposal.program_proposal_id,
            proposal.selected_candidate_key,
        )
