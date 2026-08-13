"""Observation-derived coordinate synthesis for standard 2048.

This bounded slice first freezes two raw transition archives and then selects
the smallest preregistered coordinate basis that has no *observed*
transition-congruence contradiction.  The held-out archive is read only after
the source-selected basis is frozen.  Passing this finite check does not make
the learned row model sound: a later planner must close every relevant local
Bellman obligation with exact rows before issuing a certificate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from itertools import combinations
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_standard_2048_coordinate_preregistration_v13 as prereg
from acfqp.domains.g2048 import transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    canonicalize_state_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    transform_action_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "13.0.0"
PROFILE_KEY = "construction_k7_standard_2048_coordinate_basis_v13"
STREAM_DOMAIN = b"acfqp:standard-2048-coordinate-observation-tape:v13\x00"
MAXIMUM_GENERATOR_ATTEMPTS_PER_OBSERVATION = 4096
SOURCE_ARCHIVE_ID = "4347a3cd4782ed9c3f23dc46551cde2d686d24d1b1715df67349489afc6a3f5e"
VALIDATION_ARCHIVE_ID = "f24ab566a50cc73d4c89fb84941913ce2205e05a9947987f53adad2f0b8d927c"
COORDINATE_BASIS_ID = "920eb108ddfc9a5ecefe3c8d38629534667ae740f908c376fbd419ae6cd943ea"
SELECTED_COORDINATE_KEYS = ("rank_histogram",)


class ConstructionK7Standard2048CoordinateBasisV13Error(ValueError):
    """An archive, candidate projection, or basis-selection witness changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048CoordinateBasisV13Error(message)


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _state_from_document(document: Any) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("observation state schema changed")
    try:
        state = Swipe2048State(
            tuple(document["board_ranks"]), Swipe2048Status(document["status"])
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048CoordinateBasisV13Error(
            "observation state is invalid"
        ) from error
    if state_from_board_v1(state.board) != state:
        _fail("observation state status is not board-derived")
    return state


def _draw_digest(
    seed: str, observation_index: int, attempt: int, label: str, counter: int
) -> bytes:
    return hashlib.sha256(
        STREAM_DOMAIN
        + seed.encode("utf-8")
        + b"\x00"
        + str(observation_index).encode("ascii")
        + b"\x00"
        + str(attempt).encode("ascii")
        + b"\x00"
        + label.encode("ascii")
        + b"\x00"
        + str(counter).encode("ascii")
    ).digest()


def _uniform_below(
    seed: str,
    observation_index: int,
    attempt: int,
    label: str,
    bound: int,
) -> tuple[int, tuple[bytes, ...]]:
    if type(bound) is not int or bound <= 0:
        _fail("uniform draw bound changed")
    scale = 1 << 256
    limit = scale - (scale % bound)
    consumed: list[bytes] = []
    counter = 0
    while True:
        digest = _draw_digest(seed, observation_index, attempt, label, counter)
        consumed.append(digest)
        value = int.from_bytes(digest, "big")
        if value < limit:
            return value % bound, tuple(consumed)
        counter += 1


def _sample_board_and_action(
    seed: str, observation_index: int, attempt: int
) -> tuple[Swipe2048State, Swipe2048Action, tuple[bytes, ...]] | None:
    draws: list[bytes] = []
    occupied_offset, consumed = _uniform_below(
        seed, observation_index, attempt, "occupied-count", 11
    )
    draws.extend(consumed)
    occupied_count = 2 + occupied_offset

    positions = list(range(16))
    for offset in range(occupied_count):
        selected_offset, consumed = _uniform_below(
            seed,
            observation_index,
            attempt,
            f"occupied-position-{offset}",
            16 - offset,
        )
        draws.extend(consumed)
        selected = offset + selected_offset
        positions[offset], positions[selected] = positions[selected], positions[offset]

    board = [0] * 16
    for ordinal, position in enumerate(positions[:occupied_count]):
        rank_offset, consumed = _uniform_below(
            seed, observation_index, attempt, f"occupied-rank-{ordinal}", 6
        )
        draws.extend(consumed)
        board[position] = 1 + rank_offset

    state = state_from_board_v1(tuple(board))
    legal = legal_actions_v1(state.board)
    if state.status is not Swipe2048Status.ACTIVE or not legal:
        return None
    action_offset, consumed = _uniform_below(
        seed, observation_index, attempt, "legal-action", len(legal)
    )
    draws.extend(consumed)
    return state, legal[action_offset], tuple(draws)


def _observation_row(seed: str, observation_index: int) -> dict[str, Any]:
    for attempt in range(MAXIMUM_GENERATOR_ATTEMPTS_PER_OBSERVATION):
        sampled = _sample_board_and_action(seed, observation_index, attempt)
        if sampled is None:
            continue
        state, action, choice_draws = sampled
        outcome, outcome_tape = select_seeded_outcome_v1(
            step_v1(state, action), seed=seed, decision_index=observation_index
        )
        choice_digest = hashlib.sha256(b"".join(choice_draws)).hexdigest()
        return {
            "observation_index": observation_index,
            "generator_attempt": attempt,
            "pre_state": _state_document(state),
            "action": action.value,
            "observed_successor": _state_document(outcome.next_state),
            "merge_score": outcome.merge_score,
            "spawned_cell": outcome.spawned_cell,
            "spawned_rank": outcome.spawned_rank,
            "generator_choice_draw_count": len(choice_draws),
            "generator_choice_digest_sha256": choice_digest,
            "outcome_tape_sha256": outcome_tape,
            "outcome_probability_not_disclosed_to_selector": True,
            "unobserved_support_not_disclosed_to_selector": True,
        }
    _fail("observation generator exhausted its registered attempt cap")


def _archive_document(role: str, seed: str, count: int) -> dict[str, Any]:
    if role not in {"SOURCE_SELECTION", "HELDOUT_VALIDATION"}:
        _fail("observation archive role changed")
    rows = [_observation_row(seed, index) for index in range(count)]
    payload = {
        "schema": "acfqp.standard_2048_coordinate_observation_archive.v13",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "coordinate_preregistration_id": prereg.PREREGISTRATION_ID,
        "archive_role": role,
        "stream_seed": seed,
        "stream_domain_hex": STREAM_DOMAIN.hex(),
        "observation_count": count,
        "rows": rows,
        "deterministic_fixture_replay_not_iid_evidence": True,
        "generator_law_or_probability_available_to_selector": False,
        "exact_ground_kernel_used_by_observer_only": True,
        "target_episode_identity_present": False,
    }
    return {
        **payload,
        "coordinate_observation_archive_id": content_id(
            prereg.FUTURE_DOMAINS["observation_archive"], payload
        ),
    }


def _validate_archive_document(
    document: Any, *, expected_role: str, expected_seed: str, expected_count: int
) -> dict[str, Any]:
    keys = {
        "schema",
        "schema_version",
        "profile_key",
        "coordinate_preregistration_id",
        "archive_role",
        "stream_seed",
        "stream_domain_hex",
        "observation_count",
        "rows",
        "deterministic_fixture_replay_not_iid_evidence",
        "generator_law_or_probability_available_to_selector",
        "exact_ground_kernel_used_by_observer_only",
        "target_episode_identity_present",
        "coordinate_observation_archive_id",
    }
    if type(document) is not dict or set(document) != keys:
        _fail("coordinate observation archive schema changed")
    if (
        document["schema"]
        != "acfqp.standard_2048_coordinate_observation_archive.v13"
        or document["schema_version"] != SCHEMA_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["coordinate_preregistration_id"] != prereg.PREREGISTRATION_ID
        or document["archive_role"] != expected_role
        or document["stream_seed"] != expected_seed
        or document["stream_domain_hex"] != STREAM_DOMAIN.hex()
        or document["observation_count"] != expected_count
        or document["deterministic_fixture_replay_not_iid_evidence"] is not True
        or document["generator_law_or_probability_available_to_selector"] is not False
        or document["exact_ground_kernel_used_by_observer_only"] is not True
        or document["target_episode_identity_present"] is not False
    ):
        _fail("coordinate observation archive identity or claim changed")
    rows = document["rows"]
    if type(rows) is not list or len(rows) != expected_count:
        _fail("coordinate observation archive cardinality changed")
    row_keys = {
        "observation_index",
        "generator_attempt",
        "pre_state",
        "action",
        "observed_successor",
        "merge_score",
        "spawned_cell",
        "spawned_rank",
        "generator_choice_draw_count",
        "generator_choice_digest_sha256",
        "outcome_tape_sha256",
        "outcome_probability_not_disclosed_to_selector",
        "unobserved_support_not_disclosed_to_selector",
    }
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != row_keys:
            _fail("coordinate observation row schema changed")
        if (
            row["observation_index"] != index
            or type(row["generator_attempt"]) is not int
            or not 0 <= row["generator_attempt"] < MAXIMUM_GENERATOR_ATTEMPTS_PER_OBSERVATION
            or type(row["generator_choice_draw_count"]) is not int
            or row["generator_choice_draw_count"] <= 0
            or type(row["generator_choice_digest_sha256"]) is not str
            or len(row["generator_choice_digest_sha256"]) != 64
            or type(row["outcome_tape_sha256"]) is not str
            or len(row["outcome_tape_sha256"]) != 64
            or row["outcome_probability_not_disclosed_to_selector"] is not True
            or row["unobserved_support_not_disclosed_to_selector"] is not True
        ):
            _fail("coordinate observation row identity or claim changed")
        _normalized_transition(row)
    payload = {key: value for key, value in document.items() if key != "coordinate_observation_archive_id"}
    if document["coordinate_observation_archive_id"] != content_id(
        prereg.FUTURE_DOMAINS["observation_archive"], payload
    ):
        _fail("coordinate observation archive content identity changed")
    return document


def _candidate_document(ordinal: int, key: str, expression: tuple[str, ...]) -> dict[str, Any]:
    semantics = {
        "empty_cell_count": "COUNT_ZERO_RANKS",
        "rank_histogram": "COUNT_EACH_RANK_0_THROUGH_19",
        "maximum_rank": "MAXIMUM_BOARD_RANK",
        "maximum_rank_corner_class": (
            "COUNTS_OF_MAXIMUM_RANK_CELLS_IN_CORNER_EDGE_INTERIOR_CLASSES"
        ),
        "adjacent_equal_pair_count": (
            "COUNT_NONZERO_EQUAL_HORIZONTAL_OR_VERTICAL_NEIGHBOR_PAIRS"
        ),
        "ordered_line_rank_signature": (
            "LEXICOGRAPHIC_MULTISET_OF_FOUR_ORDERED_ROWS_AND_FOUR_ORDERED_COLUMNS"
        ),
        "legal_action_mask": "BITMASK_IN_STANDARD_ACTION_ORDER",
        "rank_mass": "SUM_OF_TILE_VALUES_WITH_ZERO_CONTRIBUTING_ZERO",
        "exact_d4_board_fallback_coordinate": "EXACT_CANONICAL_D4_BOARD_RANK_TUPLE",
    }[key]
    payload = {
        "schema": "acfqp.standard_2048_coordinate_candidate.v13",
        "schema_version": SCHEMA_VERSION,
        "coordinate_preregistration_id": prereg.PREREGISTRATION_ID,
        "candidate_ordinal": ordinal,
        "candidate_key": key,
        "compiled_expression": list(expression),
        "evaluation_semantics": semantics,
        "input_is_canonical_d4_state": True,
        "query_reward_value_policy_or_target_access": False,
    }
    return {
        **payload,
        "coordinate_candidate_id": content_id(
            prereg.FUTURE_DOMAINS["candidate"], payload
        ),
    }


def _coordinate_value(key: str, state: Swipe2048State) -> Any:
    board = state.board
    if canonicalize_state_v1(state)[0] != state:
        _fail("coordinate input is not a canonical D4 state")
    if key == "empty_cell_count":
        return board.count(0)
    if key == "rank_histogram":
        return [board.count(rank) for rank in range(GOAL_RANK + 9)]
    if key == "maximum_rank":
        return max(board)
    if key == "maximum_rank_corner_class":
        maximum = max(board)
        maximum_cells = tuple(index for index, rank in enumerate(board) if rank == maximum)
        corners = {0, 3, 12, 15}
        edges = {1, 2, 4, 7, 8, 11, 13, 14}
        return [
            sum(cell in corners for cell in maximum_cells),
            sum(cell in edges for cell in maximum_cells),
            sum(cell not in corners and cell not in edges for cell in maximum_cells),
        ]
    if key == "adjacent_equal_pair_count":
        horizontal = sum(
            board[row * 4 + column] != 0
            and board[row * 4 + column] == board[row * 4 + column + 1]
            for row in range(4)
            for column in range(3)
        )
        vertical = sum(
            board[row * 4 + column] != 0
            and board[row * 4 + column] == board[(row + 1) * 4 + column]
            for row in range(3)
            for column in range(4)
        )
        return horizontal + vertical
    if key == "ordered_line_rank_signature":
        lines = [list(board[row * 4 : (row + 1) * 4]) for row in range(4)]
        lines.extend([[board[row * 4 + column] for row in range(4)] for column in range(4)])
        return sorted(lines)
    if key == "legal_action_mask":
        legal = set(legal_actions_v1(board))
        return sum(1 << ordinal for ordinal, action in enumerate(ACTION_ORDER) if action in legal)
    if key == "rank_mass":
        return sum((1 << rank) if rank else 0 for rank in board)
    if key == "exact_d4_board_fallback_coordinate":
        return list(board)
    _fail("unknown coordinate candidate")


def _normalized_transition(document: Mapping[str, Any]) -> tuple[Swipe2048State, str, int, int, Swipe2048State, int]:
    state = _state_from_document(document.get("pre_state"))
    successor = _state_from_document(document.get("observed_successor"))
    try:
        action = Swipe2048Action(document.get("action"))
    except ValueError as error:
        raise ConstructionK7Standard2048CoordinateBasisV13Error(
            "observation action changed"
        ) from error
    if action not in legal_actions_v1(state.board):
        _fail("observation action is not legal")
    spawned_cell = document.get("spawned_cell")
    spawned_rank = document.get("spawned_rank")
    merge_score = document.get("merge_score")
    if (
        type(spawned_cell) is not int
        or not 0 <= spawned_cell < 16
        or spawned_rank not in (1, 2)
        or type(merge_score) is not int
        or merge_score < 0
    ):
        _fail("observation outcome fields changed")
    representative, transform = canonicalize_state_v1(state)
    successor_representative, _ = canonicalize_state_v1(successor)
    return (
        representative,
        transform_action_v1(action, transform).value,
        transform_cell(spawned_cell, 4, transform),
        spawned_rank,
        successor_representative,
        merge_score,
    )


def _congruence_witness(
    rows: list[dict[str, Any]], selected_keys: tuple[str, ...]
) -> dict[str, Any]:
    transitions: dict[bytes, bytes] = {}
    contradictions = 0
    duplicate_condition_count = 0
    first_contradiction: dict[str, Any] | None = None
    for row in rows:
        state, action, cell, rank, successor, merge_score = _normalized_transition(row)
        condition = {
            "coordinate": [_coordinate_value(key, state) for key in selected_keys],
            "action": action,
            "spawned_cell_in_canonical_prestate_frame": cell,
            "spawned_rank": rank,
        }
        result = {
            "successor_coordinate": [
                _coordinate_value(key, successor) for key in selected_keys
            ],
            "successor_status": successor.status.value,
            "merge_score": merge_score,
        }
        condition_bytes = canonical_json_bytes(condition)
        result_bytes = canonical_json_bytes(result)
        previous = transitions.get(condition_bytes)
        if previous is None:
            transitions[condition_bytes] = result_bytes
        else:
            duplicate_condition_count += 1
            if previous != result_bytes:
                contradictions += 1
                if first_contradiction is None:
                    first_contradiction = {
                        "condition": condition,
                        "first_result": loads_canonical_json(previous),
                        "conflicting_result": result,
                    }
    return {
        "observation_count": len(rows),
        "distinct_condition_count": len(transitions),
        "duplicate_condition_count": duplicate_condition_count,
        "transition_congruence_contradiction_count": contradictions,
        "first_contradiction": first_contradiction,
    }


def _basis_document(source: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        _candidate_document(ordinal, key, expression)
        for ordinal, (key, expression) in enumerate(prereg.COORDINATE_CANDIDATES)
    ]
    source_rows = source["rows"]
    validation_rows = validation["rows"]
    selected_ordinals: tuple[int, ...] | None = None
    selected_source_witness: dict[str, Any] | None = None
    enumerated_subset_count = 0
    rejected_before_selection = 0
    source_consistent_at_selected_cardinality = 0
    for cardinality in range(1, len(candidates) + 1):
        consistent: list[tuple[tuple[int, ...], dict[str, Any]]] = []
        for ordinals in combinations(range(len(candidates)), cardinality):
            enumerated_subset_count += 1
            keys = tuple(candidates[ordinal]["candidate_key"] for ordinal in ordinals)
            witness = _congruence_witness(source_rows, keys)
            if witness["transition_congruence_contradiction_count"] == 0:
                consistent.append((ordinals, witness))
            else:
                rejected_before_selection += 1
        if consistent:
            selected_ordinals, selected_source_witness = consistent[0]
            source_consistent_at_selected_cardinality = len(consistent)
            break
    if selected_ordinals is None or selected_source_witness is None:
        _fail("registered exact fallback coordinate failed source congruence")

    selected_keys = tuple(candidates[index]["candidate_key"] for index in selected_ordinals)
    validation_witness = _congruence_witness(validation_rows, selected_keys)
    heldout_pass = validation_witness["transition_congruence_contradiction_count"] == 0
    payload = {
        "schema": "acfqp.standard_2048_coordinate_basis.v13",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "coordinate_preregistration_id": prereg.PREREGISTRATION_ID,
        "source_observation_archive_id": source["coordinate_observation_archive_id"],
        "validation_observation_archive_id": validation[
            "coordinate_observation_archive_id"
        ],
        "candidate_artifacts": candidates,
        "candidate_count": len(candidates),
        "selection_order": "INCREASING_SUBSET_CARDINALITY_THEN_CANDIDATE_ORDINAL",
        "selected_candidate_ordinals": list(selected_ordinals),
        "selected_candidate_keys": list(selected_keys),
        "selected_candidate_ids": [
            candidates[index]["coordinate_candidate_id"] for index in selected_ordinals
        ],
        "selected_basis_cardinality": len(selected_ordinals),
        "enumerated_subset_count_through_selected_cardinality": enumerated_subset_count,
        "rejected_subset_count_before_selected_cardinality": rejected_before_selection,
        "source_consistent_subset_count_at_selected_cardinality": (
            source_consistent_at_selected_cardinality
        ),
        "source_congruence_witness": selected_source_witness,
        "source_selected_before_validation_read": True,
        "validation_congruence_witness": validation_witness,
        "heldout_validation_passed": heldout_pass,
        "result_classification": (
            "POSITIVE_REGISTERED_COORDINATE_SYNTHESIS_RESULT"
            if heldout_pass
            else "NEGATIVE_REGISTERED_COORDINATE_SYNTHESIS_RESULT"
        ),
        "transition_condition_includes_observed_spawn_rank_and_canonical_cell": True,
        "finite_observation_congruence_not_global_lumpability_proof": True,
        "generator_law_probability_query_reward_value_policy_or_target_read_by_selector": False,
        "statistical_basis_can_issue_sound_plan_certificate": False,
        "exact_local_obligation_closure_still_required": True,
        "partial_quotient_model_constructed": False,
        "target_execution_performed": False,
        "sample_tax_reduction_claimed": False,
        "broad_world_model_synthesis_claimed": False,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
    }
    return {
        **payload,
        "coordinate_basis_id": content_id(prereg.FUTURE_DOMAINS["basis"], payload),
    }


_OBSERVATION_ISSUER = object()
_BASIS_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048CoordinateObservationEvidenceV13:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    source_archive_id: str
    validation_archive_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _OBSERVATION_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("coordinate observations are not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or set(document) != {"source_archive", "validation_archive"}
            or canonical_json_bytes(document) != self.canonical_bytes
            or document["source_archive"].get("coordinate_observation_archive_id")
            != self.source_archive_id
            or document["validation_archive"].get("coordinate_observation_archive_id")
            != self.validation_archive_id
        ):
            _fail("coordinate observation evidence changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("coordinate observation evidence is not an object")
        return document


@dataclass(frozen=True, slots=True)
class Standard2048CoordinateBasisEvidenceV13:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    source_archive_id: str
    validation_archive_id: str
    coordinate_basis_id: str
    selected_candidate_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if self._issuer is not _BASIS_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("coordinate basis is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or set(document) != {"source_archive", "validation_archive", "basis"}
            or canonical_json_bytes(document) != self.canonical_bytes
            or document["source_archive"].get("coordinate_observation_archive_id")
            != self.source_archive_id
            or document["validation_archive"].get("coordinate_observation_archive_id")
            != self.validation_archive_id
            or document["basis"].get("coordinate_basis_id") != self.coordinate_basis_id
            or tuple(document["basis"].get("selected_candidate_keys", ()))
            != self.selected_candidate_keys
        ):
            _fail("coordinate basis evidence changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("coordinate basis evidence is not an object")
        return document


def acquire_standard_2048_coordinate_observations_v13(
) -> Standard2048CoordinateObservationEvidenceV13:
    source = _archive_document(
        "SOURCE_SELECTION",
        prereg.SOURCE_STREAM_SEED,
        prereg.SOURCE_TRANSITION_OBSERVATION_COUNT,
    )
    validation = _archive_document(
        "HELDOUT_VALIDATION",
        prereg.VALIDATION_STREAM_SEED,
        prereg.VALIDATION_TRANSITION_OBSERVATION_COUNT,
    )
    if (
        source["coordinate_observation_archive_id"] != SOURCE_ARCHIVE_ID
        or validation["coordinate_observation_archive_id"] != VALIDATION_ARCHIVE_ID
    ):
        _fail("frozen coordinate observation archive identity changed")
    document = {"source_archive": source, "validation_archive": validation}
    return Standard2048CoordinateObservationEvidenceV13(
        _OBSERVATION_ISSUER,
        canonical_json_bytes(document),
        source["coordinate_observation_archive_id"],
        validation["coordinate_observation_archive_id"],
    )


def verify_standard_2048_coordinate_observations_v13(
    evidence: Standard2048CoordinateObservationEvidenceV13,
) -> Standard2048CoordinateObservationEvidenceV13:
    if type(evidence) is not Standard2048CoordinateObservationEvidenceV13:
        _fail("coordinate observation verifier rejects foreign values")
    evidence.__post_init__()
    expected = acquire_standard_2048_coordinate_observations_v13()
    if evidence.canonical_bytes != expected.canonical_bytes:
        _fail("coordinate observation archives differ from exact replay")
    return evidence


def synthesize_standard_2048_coordinate_basis_v13(
    observations: Standard2048CoordinateObservationEvidenceV13,
) -> Standard2048CoordinateBasisEvidenceV13:
    if type(observations) is not Standard2048CoordinateObservationEvidenceV13:
        _fail("coordinate selector rejects foreign observation evidence")
    observations.__post_init__()
    archives = observations.to_document()
    source = _validate_archive_document(
        archives["source_archive"],
        expected_role="SOURCE_SELECTION",
        expected_seed=prereg.SOURCE_STREAM_SEED,
        expected_count=prereg.SOURCE_TRANSITION_OBSERVATION_COUNT,
    )
    validation = _validate_archive_document(
        archives["validation_archive"],
        expected_role="HELDOUT_VALIDATION",
        expected_seed=prereg.VALIDATION_STREAM_SEED,
        expected_count=prereg.VALIDATION_TRANSITION_OBSERVATION_COUNT,
    )
    if source["coordinate_observation_archive_id"] == validation["coordinate_observation_archive_id"]:
        _fail("source and validation archives are not identity-separated")
    basis = _basis_document(source, validation)
    document = {
        "source_archive": source,
        "validation_archive": validation,
        "basis": basis,
    }
    return Standard2048CoordinateBasisEvidenceV13(
        _BASIS_ISSUER,
        canonical_json_bytes(document),
        observations.source_archive_id,
        observations.validation_archive_id,
        basis["coordinate_basis_id"],
        tuple(basis["selected_candidate_keys"]),
    )


def build_standard_2048_coordinate_basis_v13(
) -> Standard2048CoordinateBasisEvidenceV13:
    observations = acquire_standard_2048_coordinate_observations_v13()
    verify_standard_2048_coordinate_observations_v13(observations)
    evidence = synthesize_standard_2048_coordinate_basis_v13(observations)
    if (
        evidence.coordinate_basis_id != COORDINATE_BASIS_ID
        or evidence.selected_candidate_keys != SELECTED_COORDINATE_KEYS
    ):
        _fail("frozen source-selected coordinate basis changed")
    return evidence


def verify_standard_2048_coordinate_basis_v13(
    evidence: Standard2048CoordinateBasisEvidenceV13,
) -> Standard2048CoordinateBasisEvidenceV13:
    if type(evidence) is not Standard2048CoordinateBasisEvidenceV13:
        _fail("coordinate basis verifier rejects foreign values")
    evidence.__post_init__()
    expected = build_standard_2048_coordinate_basis_v13()
    if evidence.canonical_bytes != expected.canonical_bytes:
        _fail("coordinate basis differs from exact observation and selection replay")
    return evidence


__all__ = (
    "COORDINATE_BASIS_ID",
    "ConstructionK7Standard2048CoordinateBasisV13Error",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SELECTED_COORDINATE_KEYS",
    "SOURCE_ARCHIVE_ID",
    "Standard2048CoordinateBasisEvidenceV13",
    "Standard2048CoordinateObservationEvidenceV13",
    "VALIDATION_ARCHIVE_ID",
    "acquire_standard_2048_coordinate_observations_v13",
    "build_standard_2048_coordinate_basis_v13",
    "synthesize_standard_2048_coordinate_basis_v13",
    "verify_standard_2048_coordinate_basis_v13",
    "verify_standard_2048_coordinate_observations_v13",
)
