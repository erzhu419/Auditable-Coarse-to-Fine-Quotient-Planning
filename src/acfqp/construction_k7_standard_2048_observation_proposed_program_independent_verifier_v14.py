"""Producer-free replay of the observed and proof-checked 2048 program."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from itertools import product
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_coordinate_basis_independent_verifier_v13 as basis_verifier
from acfqp.domains.standard_2048 import Swipe2048Action, swipe_board_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_FACTORED_WORLD_MODEL_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CANDIDATE_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_LINE_PROOF_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PROPOSAL_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_VERIFICATION_V14_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "14.0.0"
PREREGISTRATION_ID = "948020ab2f6ef639899a0913ce68b7cb2573eb8e8d4b6edd07c7550ff08aa62e"
COORDINATE_BASIS_ID = "920eb108ddfc9a5ecefe3c8d38629534667ae740f908c376fbd419ae6cd943ea"
SOURCE_ARCHIVE_ID = "4347a3cd4782ed9c3f23dc46551cde2d686d24d1b1715df67349489afc6a3f5e"
VALIDATION_ARCHIVE_ID = "f24ab566a50cc73d4c89fb84941913ce2205e05a9947987f53adad2f0b8d927c"
PROPOSAL_ID = "7164a54cad13246a55c891a71a1a879b15be7116fbcb49998e8b7619f9c0ce72"
SELECTED_CANDIDATE_ID = "09e7e07f8d9f854d3385d0c1aa32ff3f86d6aec835c28160819eec1ed88b0c52"
LINE_PROOF_ID = "3960ef8c496eb00a81d08bf29243ee7f5cd5f50f5302f2b91cb836618bc322b6"
WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
TRACE_SHA256 = "c37bf30f2200c1747c8ed0cfae02e6e0a7d07fca778b73675c65cb8d63def220"
VERIFICATION_ID = "f739865ab86c0a08bfff43492fa2ca73a10d0d0d6f3bf5732b5f419d7a5b4716"

CANDIDATES = (
    (
        "COMPACT_NONZERO_WITHOUT_MERGE",
        ("ORIENT_ACTION_LINES", "COMPACT_NONZERO", "ZERO_PAD", "RECOMBINE"),
    ),
    (
        "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP",
        (
            "ORIENT_ACTION_LINES",
            "COMPACT_NONZERO",
            "LEFT_GREEDY_EQUAL_ADJACENT_MERGE",
            "SKIP_MERGED_PAIR",
            "ZERO_PAD",
            "RECOMBINE",
        ),
    ),
    (
        "COMPACT_THEN_CASCADE_EQUAL_MERGES_TO_FIXED_POINT",
        (
            "ORIENT_ACTION_LINES",
            "COMPACT_NONZERO",
            "CASCADE_EQUAL_ADJACENT_MERGE_TO_FIXED_POINT",
            "ZERO_PAD",
            "RECOMBINE",
        ),
    ),
    (
        "MERGE_ONLY_ORIGINALLY_ADJACENT_THEN_COMPACT",
        (
            "ORIENT_ACTION_LINES",
            "LEFT_GREEDY_ORIGINALLY_ADJACENT_NONZERO_MERGE",
            "SKIP_MERGED_PAIR",
            "COMPACT_NONZERO",
            "ZERO_PAD",
            "RECOMBINE",
        ),
    ),
)


class ConstructionK7Standard2048ObservationProposedProgramIndependentVerifierV14Error(
    ValueError
):
    """Program bytes differ from producer-free proposal and proof replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ObservationProposedProgramIndependentVerifierV14Error(
        message
    )


def _cells(action: str, index: int) -> tuple[int, ...]:
    if action == "LEFT":
        return tuple(index * 4 + column for column in range(4))
    if action == "RIGHT":
        return tuple(index * 4 + column for column in range(3, -1, -1))
    if action == "UP":
        return tuple(row * 4 + index for row in range(4))
    if action == "DOWN":
        return tuple(row * 4 + index for row in range(3, -1, -1))
    _fail("action changed")


def _line(candidate: str, line: tuple[int, ...]) -> tuple[tuple[int, ...], int]:
    score = 0
    if candidate == CANDIDATES[0][0]:
        output = [rank for rank in line if rank]
    elif candidate == CANDIDATES[1][0]:
        values = [rank for rank in line if rank]
        output = []
        index = 0
        while index < len(values):
            rank = values[index]
            if index + 1 < len(values) and values[index + 1] == rank:
                rank += 1
                score += 1 << rank
                index += 2
            else:
                index += 1
            output.append(rank)
    elif candidate == CANDIDATES[2][0]:
        output = []
        for rank in (item for item in line if item):
            output.append(rank)
            while len(output) >= 2 and output[-1] == output[-2]:
                merged = output.pop() + 1
                output.pop()
                output.append(merged)
                score += 1 << merged
    elif candidate == CANDIDATES[3][0]:
        output = []
        index = 0
        while index < len(line):
            rank = line[index]
            if rank and index + 1 < len(line) and line[index + 1] == rank:
                rank += 1
                score += 1 << rank
                output.append(rank)
                index += 2
            else:
                if rank:
                    output.append(rank)
                index += 1
    else:
        _fail("candidate changed")
    output.extend([0] * (4 - len(output)))
    return tuple(output), score


def _board(board: tuple[int, ...], action: str, candidate: str) -> tuple[tuple[int, ...], int]:
    result = list(board)
    score = 0
    for index in range(4):
        cells = _cells(action, index)
        output, line_score = _line(candidate, tuple(board[cell] for cell in cells))
        score += line_score
        for cell, rank in zip(cells, output, strict=True):
            result[cell] = rank
    return tuple(result), score


def apply_independently_replayed_swipe_program_v14(
    board: tuple[int, ...], action: str
) -> tuple[tuple[int, ...], int]:
    """Apply only the independently selected and exhaustively proved program."""

    if (
        type(board) is not tuple
        or len(board) != 16
        or any(type(rank) is not int or not 0 <= rank <= 19 for rank in board)
        or action not in {"LEFT", "RIGHT", "UP", "DOWN"}
    ):
        _fail("independent swipe-program input changed")
    return _board(board, action, CANDIDATES[1][0])


def _candidate_document(ordinal: int) -> dict[str, Any]:
    key, instructions = CANDIDATES[ordinal]
    payload = {
        "schema": "acfqp.standard_2048_swipe_program_candidate.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": PREREGISTRATION_ID,
        "candidate_ordinal": ordinal,
        "candidate_key": key,
        "instruction_sequence": list(instructions),
        "line_length": 4,
        "action_orientation_then_shared_line_program": True,
        "spawn_operator_present": False,
        "query_reward_value_policy_or_target_access": False,
    }
    return {
        **payload,
        "program_candidate_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CANDIDATE_V14_DOMAIN, payload
        ),
    }


def _score(rows: list[dict[str, Any]], candidate: str) -> tuple[int, dict[str, Any] | None]:
    mismatch = 0
    first = None
    for row in rows:
        pre_board = tuple(row["pre_state"]["board_ranks"])
        observed = list(row["observed_successor"]["board_ranks"])
        cell = row["spawned_cell"]
        if observed[cell] != row["spawned_rank"]:
            _fail("spawn removal changed")
        observed[cell] = 0
        predicted, predicted_score = _board(pre_board, row["action"], candidate)
        if predicted != tuple(observed) or predicted_score != row["merge_score"]:
            mismatch += 1
            if first is None:
                first = {
                    "observation_index": row["observation_index"],
                    "predicted_post_swipe_board": list(predicted),
                    "observed_post_swipe_board": observed,
                    "predicted_merge_score": predicted_score,
                    "observed_merge_score": row["merge_score"],
                }
    return mismatch, first


def _proposal(basis: dict[str, Any]) -> dict[str, Any]:
    candidates = [_candidate_document(index) for index in range(4)]
    evaluations = []
    for candidate in candidates:
        count, first = _score(basis["source_archive"]["rows"], candidate["candidate_key"])
        evaluations.append(
            {
                "program_candidate_id": candidate["program_candidate_id"],
                "candidate_key": candidate["candidate_key"],
                "mismatch_count": count,
                "first_mismatch": first,
            }
        )
    best_count = min(row["mismatch_count"] for row in evaluations)
    selected_rows = [row for row in evaluations if row["mismatch_count"] == best_count]
    if len(selected_rows) != 1 or best_count != 0:
        _fail("source did not independently select a unique program")
    selected = selected_rows[0]
    validation_count, validation_first = _score(
        basis["validation_archive"]["rows"], selected["candidate_key"]
    )
    payload = {
        "schema": "acfqp.standard_2048_observation_proposed_swipe_program.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": PREREGISTRATION_ID,
        "coordinate_basis_id": COORDINATE_BASIS_ID,
        "source_observation_archive_id": SOURCE_ARCHIVE_ID,
        "validation_observation_archive_id": VALIDATION_ARCHIVE_ID,
        "candidate_artifacts": candidates,
        "source_candidate_evaluations": evaluations,
        "source_selection_rule": "MINIMUM_MISMATCH_COUNT_THEN_CANDIDATE_ORDINAL",
        "source_unique_zero_mismatch_candidate": True,
        "selected_candidate_id": selected["program_candidate_id"],
        "selected_candidate_key": selected["candidate_key"],
        "selected_candidate_source_mismatch_count": selected["mismatch_count"],
        "validation_mismatch_count": validation_count,
        "validation_first_mismatch": validation_first,
        "heldout_validation_passed": validation_count == 0,
        "source_selected_before_validation_read": True,
        "spawned_tile_removed_using_observed_cell_and_rank": True,
        "exact_ground_swipe_reference_read_during_proposal": False,
        "target_episode_reward_value_policy_read_during_proposal": False,
        "proposal_has_certificate_authority": False,
        "exhaustive_line_proof_run": False,
        "target_execution_performed": False,
    }
    return {
        **payload,
        "program_proposal_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PROPOSAL_V14_DOMAIN, payload
        ),
    }


def _proof(proposal: dict[str, Any]) -> dict[str, Any]:
    candidate = proposal["selected_candidate_key"]
    mismatch = 0
    first = None
    checksum = hashlib.sha256()
    for line in product(range(20), repeat=4):
        output, score = _line(candidate, line)
        reference_board, reference_score, _ = swipe_board_v1(
            tuple(line) + (0,) * 12, Swipe2048Action.LEFT
        )
        reference = reference_board[:4]
        checksum.update(bytes(line))
        checksum.update(bytes(output))
        checksum.update(score.to_bytes(8, "big"))
        if output != reference or score != reference_score:
            mismatch += 1
            if first is None:
                first = {
                    "input_line": list(line),
                    "candidate_output_line": list(output),
                    "reference_output_line": list(reference),
                    "candidate_merge_score": score,
                    "reference_merge_score": reference_score,
                }
    payload = {
        "schema": "acfqp.standard_2048_swipe_program_exhaustive_line_proof.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": PREREGISTRATION_ID,
        "program_proposal_id": PROPOSAL_ID,
        "selected_candidate_id": SELECTED_CANDIDATE_ID,
        "selected_candidate_key": candidate,
        "line_rank_minimum": 0,
        "line_rank_maximum": 19,
        "exhaustive_line_input_count": 160000,
        "reference_swipe_line_evaluation_count": 160000,
        "candidate_line_evaluation_count": 160000,
        "mismatch_count": mismatch,
        "first_mismatch": first,
        "evaluation_trace_checksum_sha256": checksum.hexdigest(),
        "whole_board_equivalence_derived_from_four_independent_oriented_lines": mismatch == 0,
        "proof_scope": "STANDARD_4X4_BOARD_RANKS_0_THROUGH_19",
        "proof_compute_is_not_transition_observation_sampling": True,
        "stochastic_spawn_component_verified": False,
        "sound_plan_certificate_authority_present": False,
    }
    return {
        **payload,
        "program_line_proof_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_LINE_PROOF_V14_DOMAIN, payload
        ),
    }


def _world_model(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_observation_proposed_factored_world_model.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": PREREGISTRATION_ID,
        "program_proposal_id": PROPOSAL_ID,
        "program_line_proof_id": LINE_PROOF_ID,
        "selected_candidate_id": SELECTED_CANDIDATE_ID,
        "selected_candidate_key": proposal["selected_candidate_key"],
        "deterministic_swipe_component": {
            "status": "EXACT_BOUNDED_PROGRAM_EQUIVALENCE_VERIFIED",
            "line_rank_support": [0, 19],
            "action_transport": "FOUR_ORIENTED_LENGTH_FOUR_LINES",
            "reusable_across_states_actions_decisions_and_episodes": True,
        },
        "stochastic_spawn_component": {
            "status": "UNKNOWN_PENDING_EXACT_LOCAL_OBLIGATION_CLOSURE",
            "support_probability_or_independence_authority_present": False,
            "observed_source_counts_available_for_guidance": True,
        },
        "offline_transition_observation_count": 768,
        "matched_fixed_control_offline_transition_observation_count": 8192,
        "exhaustive_program_proof_compute_evaluation_count": 160000,
        "observation_and_compute_axes_reported_separately": True,
        "program_was_selected_from_observations": True,
        "program_was_not_accepted_by_observations_alone": True,
        "exact_line_proof_reusable": True,
        "model_can_generate_deterministic_swipe_successors": True,
        "model_can_issue_sound_plan_certificate_without_spawn_closure": False,
        "exact_local_spawn_obligation_closure_still_required": True,
        "target_execution_performed": False,
        "sample_tax_reduction_claimed": False,
        "open_ended_program_invention_claimed": False,
        "broad_world_model_synthesis_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "factored_world_model_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_FACTORED_WORLD_MODEL_V14_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ObservationProposedProgramIndependentVerificationV14:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    factored_world_model_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("independent program verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("program_verification_id") != self.verification_id
            or document.get("factored_world_model_id") != self.factored_world_model_id
        ):
            _fail("independent program verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "program_verification_id"
        }
        if (
            content_id(
                CONSTRUCTION_K7_STANDARD_2048_PROGRAM_VERIFICATION_V14_DOMAIN,
                payload,
            )
            != self.verification_id
        ):
            _fail("independent program verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("independent verification is not an object")
        return document


def verify_standard_2048_observation_proposed_program_bytes_independently_v14(
    *, coordinate_basis_bytes: bytes, factored_world_model_bytes: bytes
) -> Standard2048ObservationProposedProgramIndependentVerificationV14:
    observed = loads_canonical_json(factored_world_model_bytes)
    if (
        type(observed) is not dict
        or set(observed) != {"proposal", "line_proof", "world_model"}
        or canonical_json_bytes(observed) != factored_world_model_bytes
    ):
        _fail("program evidence root changed")
    if (
        observed["proposal"].get("program_proposal_id") != PROPOSAL_ID
        or observed["proposal"].get("selected_candidate_id")
        != SELECTED_CANDIDATE_ID
        or observed["line_proof"].get("program_line_proof_id") != LINE_PROOF_ID
        or observed["line_proof"].get("evaluation_trace_checksum_sha256")
        != TRACE_SHA256
        or observed["world_model"].get("factored_world_model_id")
        != WORLD_MODEL_ID
    ):
        _fail("program evidence differs from frozen content identities")
    basis_verifier.verify_standard_2048_coordinate_basis_bytes_independently_v13(
        coordinate_basis_bytes
    )
    basis = loads_canonical_json(coordinate_basis_bytes)
    if type(basis) is not dict:
        _fail("coordinate basis root changed")
    proposal = _proposal(basis)
    proof = _proof(proposal)
    model = _world_model(proposal, proof)
    expected = {"proposal": proposal, "line_proof": proof, "world_model": model}
    if (
        proposal["program_proposal_id"] != PROPOSAL_ID
        or proposal["selected_candidate_id"] != SELECTED_CANDIDATE_ID
        or proof["program_line_proof_id"] != LINE_PROOF_ID
        or proof["evaluation_trace_checksum_sha256"] != TRACE_SHA256
        or model["factored_world_model_id"] != WORLD_MODEL_ID
        or observed != expected
    ):
        _fail("program evidence differs from independent proposal and proof replay")
    payload = {
        "schema": "acfqp.standard_2048_observation_proposed_program_independent_verification.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": PREREGISTRATION_ID,
        "coordinate_basis_id": COORDINATE_BASIS_ID,
        "program_proposal_id": PROPOSAL_ID,
        "program_line_proof_id": LINE_PROOF_ID,
        "factored_world_model_id": WORLD_MODEL_ID,
        "source_and_validation_archives_independently_replayed": True,
        "four_candidate_programs_independently_scored": True,
        "unique_source_selection_and_heldout_acceptance_independently_replayed": True,
        "all_160000_line_inputs_independently_replayed": True,
        "deterministic_swipe_program_equivalence_verified": True,
        "stochastic_spawn_component_verified": False,
        "sound_plan_certificate_or_target_execution_verified": False,
        "sample_tax_reduction_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_PROGRAM_VERIFICATION_V14_DOMAIN, payload
    )
    if verification_id != VERIFICATION_ID:
        _fail("frozen independent program verification identity changed")
    return Standard2048ObservationProposedProgramIndependentVerificationV14(
        _ISSUER,
        canonical_json_bytes({**payload, "program_verification_id": verification_id}),
        verification_id,
        WORLD_MODEL_ID,
    )


__all__ = (
    "apply_independently_replayed_swipe_program_v14",
    "ConstructionK7Standard2048ObservationProposedProgramIndependentVerifierV14Error",
    "Standard2048ObservationProposedProgramIndependentVerificationV14",
    "VERIFICATION_ID",
    "verify_standard_2048_observation_proposed_program_bytes_independently_v14",
)
