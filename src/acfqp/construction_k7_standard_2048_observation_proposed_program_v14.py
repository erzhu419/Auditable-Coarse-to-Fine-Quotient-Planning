"""Observation-proposed and exhaustively checked deterministic 2048 program."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from itertools import product
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_coordinate_basis_v13 as basis_v13
from acfqp import construction_k7_standard_2048_program_preregistration_v14 as pre
from acfqp.domains.standard_2048 import Swipe2048Action, swipe_board_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = pre.PROFILE_KEY
PROGRAM_PROPOSAL_ID = "7164a54cad13246a55c891a71a1a879b15be7116fbcb49998e8b7619f9c0ce72"
SELECTED_PROGRAM_CANDIDATE_ID = "09e7e07f8d9f854d3385d0c1aa32ff3f86d6aec835c28160819eec1ed88b0c52"
PROGRAM_LINE_PROOF_ID = "3960ef8c496eb00a81d08bf29243ee7f5cd5f50f5302f2b91cb836618bc322b6"
FACTORED_WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
LINE_PROOF_TRACE_SHA256 = "c37bf30f2200c1747c8ed0cfae02e6e0a7d07fca778b73675c65cb8d63def220"


class ConstructionK7Standard2048ObservationProposedProgramV14Error(ValueError):
    """The observed proposal, exhaustive proof, or factored model changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ObservationProposedProgramV14Error(message)


def _line_cells(action: str, line_index: int) -> tuple[int, ...]:
    if action == "LEFT":
        return tuple(line_index * 4 + column for column in range(4))
    if action == "RIGHT":
        return tuple(line_index * 4 + column for column in range(3, -1, -1))
    if action == "UP":
        return tuple(row * 4 + line_index for row in range(4))
    if action == "DOWN":
        return tuple(row * 4 + line_index for row in range(3, -1, -1))
    _fail("program action changed")


def _candidate_line(
    candidate_key: str, line: tuple[int, ...]
) -> tuple[tuple[int, ...], int]:
    if type(line) is not tuple or len(line) != 4 or any(type(rank) is not int or rank < 0 for rank in line):
        _fail("candidate line input changed")
    score = 0
    if candidate_key == "COMPACT_NONZERO_WITHOUT_MERGE":
        output = [rank for rank in line if rank]
    elif candidate_key == "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP":
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
    elif candidate_key == "COMPACT_THEN_CASCADE_EQUAL_MERGES_TO_FIXED_POINT":
        output = []
        for rank in (item for item in line if item):
            output.append(rank)
            while len(output) >= 2 and output[-1] == output[-2]:
                merged = output.pop() + 1
                output.pop()
                output.append(merged)
                score += 1 << merged
    elif candidate_key == "MERGE_ONLY_ORIGINALLY_ADJACENT_THEN_COMPACT":
        output = []
        index = 0
        while index < len(line):
            rank = line[index]
            if (
                rank
                and index + 1 < len(line)
                and line[index + 1] == rank
            ):
                rank += 1
                score += 1 << rank
                output.append(rank)
                index += 2
            else:
                if rank:
                    output.append(rank)
                index += 1
    else:
        _fail("unknown program candidate")
    output.extend([0] * (4 - len(output)))
    if len(output) != 4:
        _fail("program candidate escaped line length")
    return tuple(output), score


def apply_observation_proposed_swipe_program_v14(
    board: tuple[int, ...], action: str, *, candidate_key: str
) -> tuple[tuple[int, ...], int]:
    if type(board) is not tuple or len(board) != 16:
        _fail("program board changed")
    output = list(board)
    score = 0
    for line_index in range(4):
        cells = _line_cells(action, line_index)
        transformed, line_score = _candidate_line(
            candidate_key, tuple(board[cell] for cell in cells)
        )
        score += line_score
        for cell, rank in zip(cells, transformed, strict=True):
            output[cell] = rank
    return tuple(output), score


def _candidate_document(ordinal: int) -> dict[str, Any]:
    key, instructions = pre.PROGRAM_CANDIDATES[ordinal]
    payload = {
        "schema": "acfqp.standard_2048_swipe_program_candidate.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": pre.PREREGISTRATION_ID,
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
        "program_candidate_id": content_id(pre.FUTURE_DOMAINS["candidate"], payload),
    }


def _post_swipe_observation(row: dict[str, Any]) -> tuple[tuple[int, ...], str, tuple[int, ...], int]:
    pre_board = tuple(row["pre_state"]["board_ranks"])
    post_board = list(row["observed_successor"]["board_ranks"])
    cell = row["spawned_cell"]
    rank = row["spawned_rank"]
    if (
        type(cell) is not int
        or not 0 <= cell < 16
        or rank not in (1, 2)
        or post_board[cell] != rank
    ):
        _fail("spawn removal witness changed")
    post_board[cell] = 0
    return pre_board, row["action"], tuple(post_board), row["merge_score"]


def _score_candidate(rows: list[dict[str, Any]], candidate_key: str) -> tuple[int, dict[str, Any] | None]:
    mismatch_count = 0
    first_mismatch = None
    for row in rows:
        pre_board, action, observed_post_swipe, observed_score = _post_swipe_observation(row)
        predicted_board, predicted_score = apply_observation_proposed_swipe_program_v14(
            pre_board, action, candidate_key=candidate_key
        )
        if predicted_board != observed_post_swipe or predicted_score != observed_score:
            mismatch_count += 1
            if first_mismatch is None:
                first_mismatch = {
                    "observation_index": row["observation_index"],
                    "predicted_post_swipe_board": list(predicted_board),
                    "observed_post_swipe_board": list(observed_post_swipe),
                    "predicted_merge_score": predicted_score,
                    "observed_merge_score": observed_score,
                }
    return mismatch_count, first_mismatch


def _proposal_document(
    basis: basis_v13.Standard2048CoordinateBasisEvidenceV13,
) -> dict[str, Any]:
    basis_v13.verify_standard_2048_coordinate_basis_v13(basis)
    evidence = basis.to_document()
    candidates = [_candidate_document(index) for index in range(len(pre.PROGRAM_CANDIDATES))]
    source_evaluations = []
    for candidate in candidates:
        mismatch_count, first = _score_candidate(
            evidence["source_archive"]["rows"], candidate["candidate_key"]
        )
        source_evaluations.append(
            {
                "program_candidate_id": candidate["program_candidate_id"],
                "candidate_key": candidate["candidate_key"],
                "mismatch_count": mismatch_count,
                "first_mismatch": first,
            }
        )
    best_count = min(row["mismatch_count"] for row in source_evaluations)
    best = tuple(row for row in source_evaluations if row["mismatch_count"] == best_count)
    if len(best) != 1 or best_count != 0:
        _fail("source observations did not uniquely select one zero-mismatch program")
    selected = best[0]
    validation_mismatch, validation_first = _score_candidate(
        evidence["validation_archive"]["rows"], selected["candidate_key"]
    )
    payload = {
        "schema": "acfqp.standard_2048_observation_proposed_swipe_program.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": pre.PREREGISTRATION_ID,
        "coordinate_basis_id": basis.coordinate_basis_id,
        "source_observation_archive_id": basis.source_archive_id,
        "validation_observation_archive_id": basis.validation_archive_id,
        "candidate_artifacts": candidates,
        "source_candidate_evaluations": source_evaluations,
        "source_selection_rule": "MINIMUM_MISMATCH_COUNT_THEN_CANDIDATE_ORDINAL",
        "source_unique_zero_mismatch_candidate": True,
        "selected_candidate_id": selected["program_candidate_id"],
        "selected_candidate_key": selected["candidate_key"],
        "selected_candidate_source_mismatch_count": selected["mismatch_count"],
        "validation_mismatch_count": validation_mismatch,
        "validation_first_mismatch": validation_first,
        "heldout_validation_passed": validation_mismatch == 0,
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
        "program_proposal_id": content_id(pre.FUTURE_DOMAINS["proposal"], payload),
    }


def _line_proof_document(proposal: dict[str, Any]) -> dict[str, Any]:
    if proposal["heldout_validation_passed"] is not True:
        _fail("heldout-rejected program cannot enter exact proof")
    candidate_key = proposal["selected_candidate_key"]
    mismatch_count = 0
    first_mismatch = None
    checksum = hashlib.sha256()
    for line in product(
        range(pre.LINE_RANK_MINIMUM, pre.LINE_RANK_MAXIMUM + 1), repeat=4
    ):
        candidate_line, candidate_score = _candidate_line(candidate_key, line)
        reference_board, reference_score, _ = swipe_board_v1(
            tuple(line) + (0,) * 12, Swipe2048Action.LEFT
        )
        reference_line = reference_board[:4]
        checksum.update(bytes(line))
        checksum.update(bytes(candidate_line))
        checksum.update(candidate_score.to_bytes(8, "big"))
        if candidate_line != reference_line or candidate_score != reference_score:
            mismatch_count += 1
            if first_mismatch is None:
                first_mismatch = {
                    "input_line": list(line),
                    "candidate_output_line": list(candidate_line),
                    "reference_output_line": list(reference_line),
                    "candidate_merge_score": candidate_score,
                    "reference_merge_score": reference_score,
                }
    payload = {
        "schema": "acfqp.standard_2048_swipe_program_exhaustive_line_proof.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": pre.PREREGISTRATION_ID,
        "program_proposal_id": proposal["program_proposal_id"],
        "selected_candidate_id": proposal["selected_candidate_id"],
        "selected_candidate_key": candidate_key,
        "line_rank_minimum": pre.LINE_RANK_MINIMUM,
        "line_rank_maximum": pre.LINE_RANK_MAXIMUM,
        "exhaustive_line_input_count": pre.EXHAUSTIVE_LINE_INPUT_COUNT,
        "reference_swipe_line_evaluation_count": pre.EXHAUSTIVE_LINE_INPUT_COUNT,
        "candidate_line_evaluation_count": pre.EXHAUSTIVE_LINE_INPUT_COUNT,
        "mismatch_count": mismatch_count,
        "first_mismatch": first_mismatch,
        "evaluation_trace_checksum_sha256": checksum.hexdigest(),
        "whole_board_equivalence_derived_from_four_independent_oriented_lines": mismatch_count == 0,
        "proof_scope": "STANDARD_4X4_BOARD_RANKS_0_THROUGH_19",
        "proof_compute_is_not_transition_observation_sampling": True,
        "stochastic_spawn_component_verified": False,
        "sound_plan_certificate_authority_present": False,
    }
    return {
        **payload,
        "program_line_proof_id": content_id(pre.FUTURE_DOMAINS["line_proof"], payload),
    }


def _world_model_document(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    if proof["mismatch_count"] != 0:
        _fail("failed line program proof cannot construct a world model")
    payload = {
        "schema": "acfqp.standard_2048_observation_proposed_factored_world_model.v14",
        "schema_version": SCHEMA_VERSION,
        "program_preregistration_id": pre.PREREGISTRATION_ID,
        "program_proposal_id": proposal["program_proposal_id"],
        "program_line_proof_id": proof["program_line_proof_id"],
        "selected_candidate_id": proposal["selected_candidate_id"],
        "selected_candidate_key": proposal["selected_candidate_key"],
        "deterministic_swipe_component": {
            "status": "EXACT_BOUNDED_PROGRAM_EQUIVALENCE_VERIFIED",
            "line_rank_support": [pre.LINE_RANK_MINIMUM, pre.LINE_RANK_MAXIMUM],
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
        "exhaustive_program_proof_compute_evaluation_count": pre.EXHAUSTIVE_LINE_INPUT_COUNT,
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
        "factored_world_model_id": content_id(pre.FUTURE_DOMAINS["world_model"], payload),
    }


_PROPOSAL_ISSUER = object()
_MODEL_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SwipeProgramProposalV14:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    program_proposal_id: str
    selected_candidate_key: str

    def __post_init__(self) -> None:
        if self._issuer is not _PROPOSAL_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("program proposal is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("program_proposal_id") != self.program_proposal_id
            or document.get("selected_candidate_key") != self.selected_candidate_key
        ):
            _fail("program proposal bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "program_proposal_id"
        }
        if content_id(pre.FUTURE_DOMAINS["proposal"], payload) != self.program_proposal_id:
            _fail("program proposal identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("program proposal is not an object")
        return document


@dataclass(frozen=True, slots=True)
class Standard2048ObservationProposedFactoredWorldModelV14:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    factored_world_model_id: str
    program_proposal_id: str
    program_line_proof_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _MODEL_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("factored world model is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or set(document) != {"proposal", "line_proof", "world_model"}
            or canonical_json_bytes(document) != self.canonical_bytes
            or document["proposal"].get("program_proposal_id") != self.program_proposal_id
            or document["line_proof"].get("program_line_proof_id") != self.program_line_proof_id
            or document["world_model"].get("factored_world_model_id") != self.factored_world_model_id
        ):
            _fail("factored world model evidence changed")
        proposal_payload = {
            key: value
            for key, value in document["proposal"].items()
            if key != "program_proposal_id"
        }
        proof_payload = {
            key: value
            for key, value in document["line_proof"].items()
            if key != "program_line_proof_id"
        }
        model_payload = {
            key: value
            for key, value in document["world_model"].items()
            if key != "factored_world_model_id"
        }
        if (
            content_id(pre.FUTURE_DOMAINS["proposal"], proposal_payload)
            != self.program_proposal_id
            or content_id(pre.FUTURE_DOMAINS["line_proof"], proof_payload)
            != self.program_line_proof_id
            or content_id(pre.FUTURE_DOMAINS["world_model"], model_payload)
            != self.factored_world_model_id
        ):
            _fail("factored world model content identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("factored world model evidence is not an object")
        return document


def propose_standard_2048_swipe_program_v14(
    basis: basis_v13.Standard2048CoordinateBasisEvidenceV13 | None = None,
) -> Standard2048SwipeProgramProposalV14:
    pre.verify_standard_2048_program_preregistration_v14(
        pre.freeze_standard_2048_program_preregistration_v14()
    )
    if basis is None:
        basis = basis_v13.build_standard_2048_coordinate_basis_v13()
    document = _proposal_document(basis)
    if (
        document["program_proposal_id"] != PROGRAM_PROPOSAL_ID
        or document["selected_candidate_id"] != SELECTED_PROGRAM_CANDIDATE_ID
    ):
        _fail("frozen observation-proposed program changed")
    return Standard2048SwipeProgramProposalV14(
        _PROPOSAL_ISSUER,
        canonical_json_bytes(document),
        document["program_proposal_id"],
        document["selected_candidate_key"],
    )


def prove_standard_2048_swipe_program_and_build_world_model_v14(
    proposal: Standard2048SwipeProgramProposalV14 | None = None,
) -> Standard2048ObservationProposedFactoredWorldModelV14:
    if proposal is None:
        proposal = propose_standard_2048_swipe_program_v14()
    if type(proposal) is not Standard2048SwipeProgramProposalV14:
        _fail("line proof rejects foreign proposal values")
    proposal.__post_init__()
    proposal_document = proposal.to_document()
    proof = _line_proof_document(proposal_document)
    world_model = _world_model_document(proposal_document, proof)
    if (
        proof["program_line_proof_id"] != PROGRAM_LINE_PROOF_ID
        or proof["evaluation_trace_checksum_sha256"] != LINE_PROOF_TRACE_SHA256
        or world_model["factored_world_model_id"] != FACTORED_WORLD_MODEL_ID
    ):
        _fail("frozen exhaustive proof or factored world model changed")
    document = {
        "proposal": proposal_document,
        "line_proof": proof,
        "world_model": world_model,
    }
    return Standard2048ObservationProposedFactoredWorldModelV14(
        _MODEL_ISSUER,
        canonical_json_bytes(document),
        world_model["factored_world_model_id"],
        proposal.program_proposal_id,
        proof["program_line_proof_id"],
    )


def verify_standard_2048_observation_proposed_world_model_v14(
    value: Standard2048ObservationProposedFactoredWorldModelV14,
) -> Standard2048ObservationProposedFactoredWorldModelV14:
    if type(value) is not Standard2048ObservationProposedFactoredWorldModelV14:
        _fail("world model verifier rejects foreign values")
    value.__post_init__()
    expected = prove_standard_2048_swipe_program_and_build_world_model_v14()
    if value.canonical_bytes != expected.canonical_bytes:
        _fail("world model differs from observation proposal and exhaustive proof replay")
    return value


__all__ = (
    "ConstructionK7Standard2048ObservationProposedProgramV14Error",
    "FACTORED_WORLD_MODEL_ID",
    "LINE_PROOF_TRACE_SHA256",
    "PROGRAM_LINE_PROOF_ID",
    "PROGRAM_PROPOSAL_ID",
    "SELECTED_PROGRAM_CANDIDATE_ID",
    "Standard2048ObservationProposedFactoredWorldModelV14",
    "Standard2048SwipeProgramProposalV14",
    "apply_observation_proposed_swipe_program_v14",
    "propose_standard_2048_swipe_program_v14",
    "prove_standard_2048_swipe_program_and_build_world_model_v14",
    "verify_standard_2048_observation_proposed_world_model_v14",
)
