"""Producer-free replay of observation-derived standard-2048 coordinates."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from itertools import combinations
from typing import Any, Mapping, NoReturn

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
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_BASIS_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CANDIDATE_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_OBSERVATION_ARCHIVE_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_VERIFICATION_V13_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "13.0.0"
PROFILE_KEY = "construction_k7_standard_2048_coordinate_basis_v13"
PREREGISTRATION_ID = "429280b12fe2518243fa459578efabc965a67e0522cf495cf17cfe63733f5dae"
SOURCE_SEED = "standard-2048-v172-coordinate-source-20260813"
VALIDATION_SEED = "standard-2048-v172-coordinate-validation-20260813"
SOURCE_COUNT = 512
VALIDATION_COUNT = 256
STREAM_DOMAIN = b"acfqp:standard-2048-coordinate-observation-tape:v13\x00"
MAXIMUM_GENERATOR_ATTEMPTS_PER_OBSERVATION = 4096
SOURCE_ARCHIVE_ID = "4347a3cd4782ed9c3f23dc46551cde2d686d24d1b1715df67349489afc6a3f5e"
VALIDATION_ARCHIVE_ID = "f24ab566a50cc73d4c89fb84941913ce2205e05a9947987f53adad2f0b8d927c"
COORDINATE_BASIS_ID = "920eb108ddfc9a5ecefe3c8d38629534667ae740f908c376fbd419ae6cd943ea"

CANDIDATES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("empty_cell_count", ("ZERO_COUNT", "BOARD_RANKS"), "COUNT_ZERO_RANKS"),
    ("rank_histogram", ("HISTOGRAM", "BOARD_RANKS"), "COUNT_EACH_RANK_0_THROUGH_19"),
    ("maximum_rank", ("MAXIMUM", "BOARD_RANKS"), "MAXIMUM_BOARD_RANK"),
    (
        "maximum_rank_corner_class",
        ("CORNER_CLASS", "MAXIMUM", "BOARD_RANKS", "GRID_RELATION"),
        "COUNTS_OF_MAXIMUM_RANK_CELLS_IN_CORNER_EDGE_INTERIOR_CLASSES",
    ),
    (
        "adjacent_equal_pair_count",
        ("ADJACENT_EQUAL_COUNT", "BOARD_RANKS", "GRID_RELATION"),
        "COUNT_NONZERO_EQUAL_HORIZONTAL_OR_VERTICAL_NEIGHBOR_PAIRS",
    ),
    (
        "ordered_line_rank_signature",
        ("ORDERED_GRID_LINE_SCAN", "BOARD_RANKS", "GRID_RELATION"),
        "LEXICOGRAPHIC_MULTISET_OF_FOUR_ORDERED_ROWS_AND_FOUR_ORDERED_COLUMNS",
    ),
    ("legal_action_mask", ("LEGAL_ACTION_SET", "BOARD_RANKS"), "BITMASK_IN_STANDARD_ACTION_ORDER"),
    ("rank_mass", ("RANK_MASS", "BOARD_RANKS"), "SUM_OF_TILE_VALUES_WITH_ZERO_CONTRIBUTING_ZERO"),
    (
        "exact_d4_board_fallback_coordinate",
        ("BOARD_D4_CANONICALIZE", "BOARD_RANKS", "GRID_RELATION"),
        "EXACT_CANONICAL_D4_BOARD_RANK_TUPLE",
    ),
)


class ConstructionK7Standard2048CoordinateBasisIndependentVerifierV13Error(
    ValueError
):
    """The supplied bytes differ from independent archive and basis replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048CoordinateBasisIndependentVerifierV13Error(
        message
    )


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _state_from_document(document: Any) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state schema changed")
    try:
        state = Swipe2048State(
            tuple(document["board_ranks"]), Swipe2048Status(document["status"])
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048CoordinateBasisIndependentVerifierV13Error(
            "state value changed"
        ) from error
    if state_from_board_v1(state.board) != state:
        _fail("state status is not board-derived")
    return state


def _digest(seed: str, index: int, attempt: int, label: str, counter: int) -> bytes:
    return hashlib.sha256(
        STREAM_DOMAIN
        + seed.encode("utf-8")
        + b"\x00"
        + str(index).encode("ascii")
        + b"\x00"
        + str(attempt).encode("ascii")
        + b"\x00"
        + label.encode("ascii")
        + b"\x00"
        + str(counter).encode("ascii")
    ).digest()


def _uniform(
    seed: str, index: int, attempt: int, label: str, bound: int
) -> tuple[int, tuple[bytes, ...]]:
    if type(bound) is not int or bound <= 0:
        _fail("draw bound changed")
    scale = 1 << 256
    limit = scale - scale % bound
    consumed: list[bytes] = []
    counter = 0
    while True:
        row = _digest(seed, index, attempt, label, counter)
        consumed.append(row)
        value = int.from_bytes(row, "big")
        if value < limit:
            return value % bound, tuple(consumed)
        counter += 1


def _sample(seed: str, index: int, attempt: int) -> tuple[Swipe2048State, Swipe2048Action, tuple[bytes, ...]] | None:
    draws: list[bytes] = []
    offset, used = _uniform(seed, index, attempt, "occupied-count", 11)
    draws.extend(used)
    occupied = 2 + offset
    positions = list(range(16))
    for ordinal in range(occupied):
        offset, used = _uniform(
            seed, index, attempt, f"occupied-position-{ordinal}", 16 - ordinal
        )
        draws.extend(used)
        target = ordinal + offset
        positions[ordinal], positions[target] = positions[target], positions[ordinal]
    board = [0] * 16
    for ordinal, position in enumerate(positions[:occupied]):
        offset, used = _uniform(seed, index, attempt, f"occupied-rank-{ordinal}", 6)
        draws.extend(used)
        board[position] = 1 + offset
    state = state_from_board_v1(tuple(board))
    legal = legal_actions_v1(state.board)
    if state.status is not Swipe2048Status.ACTIVE or not legal:
        return None
    offset, used = _uniform(seed, index, attempt, "legal-action", len(legal))
    draws.extend(used)
    return state, legal[offset], tuple(draws)


def _expected_row(seed: str, index: int) -> dict[str, Any]:
    for attempt in range(MAXIMUM_GENERATOR_ATTEMPTS_PER_OBSERVATION):
        sampled = _sample(seed, index, attempt)
        if sampled is None:
            continue
        state, action, draws = sampled
        outcome, tape = select_seeded_outcome_v1(
            step_v1(state, action), seed=seed, decision_index=index
        )
        return {
            "observation_index": index,
            "generator_attempt": attempt,
            "pre_state": _state_document(state),
            "action": action.value,
            "observed_successor": _state_document(outcome.next_state),
            "merge_score": outcome.merge_score,
            "spawned_cell": outcome.spawned_cell,
            "spawned_rank": outcome.spawned_rank,
            "generator_choice_draw_count": len(draws),
            "generator_choice_digest_sha256": hashlib.sha256(b"".join(draws)).hexdigest(),
            "outcome_tape_sha256": tape,
            "outcome_probability_not_disclosed_to_selector": True,
            "unobserved_support_not_disclosed_to_selector": True,
        }
    _fail("registered observation attempt cap exhausted")


def _expected_archive(role: str, seed: str, count: int) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_coordinate_observation_archive.v13",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "coordinate_preregistration_id": PREREGISTRATION_ID,
        "archive_role": role,
        "stream_seed": seed,
        "stream_domain_hex": STREAM_DOMAIN.hex(),
        "observation_count": count,
        "rows": [_expected_row(seed, index) for index in range(count)],
        "deterministic_fixture_replay_not_iid_evidence": True,
        "generator_law_or_probability_available_to_selector": False,
        "exact_ground_kernel_used_by_observer_only": True,
        "target_episode_identity_present": False,
    }
    return {
        **payload,
        "coordinate_observation_archive_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_OBSERVATION_ARCHIVE_V13_DOMAIN,
            payload,
        ),
    }


def _candidate_document(ordinal: int) -> dict[str, Any]:
    key, expression, semantics = CANDIDATES[ordinal]
    payload = {
        "schema": "acfqp.standard_2048_coordinate_candidate.v13",
        "schema_version": SCHEMA_VERSION,
        "coordinate_preregistration_id": PREREGISTRATION_ID,
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
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CANDIDATE_V13_DOMAIN,
            payload,
        ),
    }


def _coordinate(key: str, state: Swipe2048State) -> Any:
    board = state.board
    if canonicalize_state_v1(state)[0] != state:
        _fail("noncanonical state reached coordinate evaluator")
    if key == "empty_cell_count":
        return board.count(0)
    if key == "rank_histogram":
        return [board.count(rank) for rank in range(GOAL_RANK + 9)]
    if key == "maximum_rank":
        return max(board)
    if key == "maximum_rank_corner_class":
        maximum = max(board)
        cells = tuple(index for index, rank in enumerate(board) if rank == maximum)
        corners = {0, 3, 12, 15}
        edges = {1, 2, 4, 7, 8, 11, 13, 14}
        return [
            sum(cell in corners for cell in cells),
            sum(cell in edges for cell in cells),
            sum(cell not in corners and cell not in edges for cell in cells),
        ]
    if key == "adjacent_equal_pair_count":
        return sum(
            board[row * 4 + column] != 0
            and board[row * 4 + column] == board[row * 4 + column + 1]
            for row in range(4)
            for column in range(3)
        ) + sum(
            board[row * 4 + column] != 0
            and board[row * 4 + column] == board[(row + 1) * 4 + column]
            for row in range(3)
            for column in range(4)
        )
    if key == "ordered_line_rank_signature":
        rows = [list(board[row * 4 : (row + 1) * 4]) for row in range(4)]
        rows.extend([[board[row * 4 + column] for row in range(4)] for column in range(4)])
        return sorted(rows)
    if key == "legal_action_mask":
        legal = set(legal_actions_v1(board))
        return sum(1 << index for index, action in enumerate(ACTION_ORDER) if action in legal)
    if key == "rank_mass":
        return sum((1 << rank) if rank else 0 for rank in board)
    if key == "exact_d4_board_fallback_coordinate":
        return list(board)
    _fail("coordinate key changed")


def _normalized(row: Mapping[str, Any]) -> tuple[Swipe2048State, str, int, int, Swipe2048State, int]:
    state = _state_from_document(row.get("pre_state"))
    successor = _state_from_document(row.get("observed_successor"))
    try:
        action = Swipe2048Action(row.get("action"))
    except ValueError as error:
        raise ConstructionK7Standard2048CoordinateBasisIndependentVerifierV13Error(
            "row action changed"
        ) from error
    representative, transform = canonicalize_state_v1(state)
    next_representative, _ = canonicalize_state_v1(successor)
    return (
        representative,
        transform_action_v1(action, transform).value,
        transform_cell(row["spawned_cell"], 4, transform),
        row["spawned_rank"],
        next_representative,
        row["merge_score"],
    )


def _witness(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any]:
    relation: dict[bytes, bytes] = {}
    contradictions = 0
    duplicates = 0
    first: dict[str, Any] | None = None
    for row in rows:
        state, action, cell, rank, successor, score = _normalized(row)
        condition = {
            "coordinate": [_coordinate(key, state) for key in keys],
            "action": action,
            "spawned_cell_in_canonical_prestate_frame": cell,
            "spawned_rank": rank,
        }
        result = {
            "successor_coordinate": [_coordinate(key, successor) for key in keys],
            "successor_status": successor.status.value,
            "merge_score": score,
        }
        condition_bytes = canonical_json_bytes(condition)
        result_bytes = canonical_json_bytes(result)
        previous = relation.get(condition_bytes)
        if previous is None:
            relation[condition_bytes] = result_bytes
        else:
            duplicates += 1
            if previous != result_bytes:
                contradictions += 1
                if first is None:
                    first = {
                        "condition": condition,
                        "first_result": loads_canonical_json(previous),
                        "conflicting_result": result,
                    }
    return {
        "observation_count": len(rows),
        "distinct_condition_count": len(relation),
        "duplicate_condition_count": duplicates,
        "transition_congruence_contradiction_count": contradictions,
        "first_contradiction": first,
    }


def _expected_basis(source: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    candidates = [_candidate_document(index) for index in range(len(CANDIDATES))]
    selected: tuple[int, ...] | None = None
    source_witness: dict[str, Any] | None = None
    enumerated = 0
    rejected = 0
    consistent_count = 0
    for cardinality in range(1, len(CANDIDATES) + 1):
        consistent: list[tuple[tuple[int, ...], dict[str, Any]]] = []
        for ordinals in combinations(range(len(CANDIDATES)), cardinality):
            enumerated += 1
            keys = tuple(CANDIDATES[index][0] for index in ordinals)
            witness = _witness(source["rows"], keys)
            if witness["transition_congruence_contradiction_count"] == 0:
                consistent.append((ordinals, witness))
            else:
                rejected += 1
        if consistent:
            selected, source_witness = consistent[0]
            consistent_count = len(consistent)
            break
    if selected is None or source_witness is None:
        _fail("independent replay found no source-consistent basis")
    keys = tuple(CANDIDATES[index][0] for index in selected)
    validation_witness = _witness(validation["rows"], keys)
    heldout = validation_witness["transition_congruence_contradiction_count"] == 0
    payload = {
        "schema": "acfqp.standard_2048_coordinate_basis.v13",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "coordinate_preregistration_id": PREREGISTRATION_ID,
        "source_observation_archive_id": source["coordinate_observation_archive_id"],
        "validation_observation_archive_id": validation["coordinate_observation_archive_id"],
        "candidate_artifacts": candidates,
        "candidate_count": len(candidates),
        "selection_order": "INCREASING_SUBSET_CARDINALITY_THEN_CANDIDATE_ORDINAL",
        "selected_candidate_ordinals": list(selected),
        "selected_candidate_keys": list(keys),
        "selected_candidate_ids": [candidates[index]["coordinate_candidate_id"] for index in selected],
        "selected_basis_cardinality": len(selected),
        "enumerated_subset_count_through_selected_cardinality": enumerated,
        "rejected_subset_count_before_selected_cardinality": rejected,
        "source_consistent_subset_count_at_selected_cardinality": consistent_count,
        "source_congruence_witness": source_witness,
        "source_selected_before_validation_read": True,
        "validation_congruence_witness": validation_witness,
        "heldout_validation_passed": heldout,
        "result_classification": (
            "POSITIVE_REGISTERED_COORDINATE_SYNTHESIS_RESULT"
            if heldout
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
        "coordinate_basis_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_BASIS_V13_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048CoordinateBasisIndependentVerificationV13:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    coordinate_basis_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("independent verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("coordinate_verification_id") != self.verification_id
            or document.get("coordinate_basis_id") != self.coordinate_basis_id
        ):
            _fail("independent verification bytes changed")
        payload = {key: value for key, value in document.items() if key != "coordinate_verification_id"}
        if content_id(CONSTRUCTION_K7_STANDARD_2048_COORDINATE_VERIFICATION_V13_DOMAIN, payload) != self.verification_id:
            _fail("independent verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("independent verification is not an object")
        return document


def verify_standard_2048_coordinate_basis_bytes_independently_v13(
    canonical_bytes: bytes,
) -> Standard2048CoordinateBasisIndependentVerificationV13:
    if type(canonical_bytes) is not bytes:
        _fail("coordinate basis verifier requires bytes")
    document = loads_canonical_json(canonical_bytes)
    if (
        type(document) is not dict
        or set(document) != {"source_archive", "validation_archive", "basis"}
        or canonical_json_bytes(document) != canonical_bytes
    ):
        _fail("coordinate basis root is not exact canonical JSON")

    expected_bytes = replay_standard_2048_coordinate_basis_bytes_independently_v13()
    expected = loads_canonical_json(expected_bytes)
    if type(expected) is not dict:
        raise AssertionError("independent coordinate basis replay is not an object")
    source = expected["source_archive"]
    validation = expected["validation_archive"]
    if source["coordinate_observation_archive_id"] != SOURCE_ARCHIVE_ID:
        _fail("independent source archive identity changed")
    if validation["coordinate_observation_archive_id"] != VALIDATION_ARCHIVE_ID:
        _fail("independent validation archive identity changed")
    basis = expected["basis"]
    if basis["coordinate_basis_id"] != COORDINATE_BASIS_ID:
        _fail("independent coordinate basis identity changed")
    if document != expected:
        _fail("coordinate basis bytes differ from independent replay")

    payload = {
        "schema": "acfqp.standard_2048_coordinate_basis_independent_verification.v13",
        "schema_version": SCHEMA_VERSION,
        "coordinate_preregistration_id": PREREGISTRATION_ID,
        "source_observation_archive_id": SOURCE_ARCHIVE_ID,
        "validation_observation_archive_id": VALIDATION_ARCHIVE_ID,
        "coordinate_basis_id": COORDINATE_BASIS_ID,
        "selected_candidate_keys": basis["selected_candidate_keys"],
        "source_observation_rows_independently_replayed": SOURCE_COUNT,
        "validation_observation_rows_independently_replayed": VALIDATION_COUNT,
        "sha_tape_board_action_and_outcome_replayed": True,
        "exact_standard_2048_transition_semantics_replayed": True,
        "d4_transport_and_all_candidate_projections_replayed": True,
        "source_first_subset_enumeration_replayed": True,
        "heldout_validation_read_after_selection_replayed": True,
        "finite_observation_congruence_verified": True,
        "global_lumpability_or_sound_plan_certificate_verified": False,
        "partial_quotient_model_or_target_execution_verified": False,
        "sample_tax_reduction_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_COORDINATE_VERIFICATION_V13_DOMAIN, payload
    )
    result = {**payload, "coordinate_verification_id": verification_id}
    return Standard2048CoordinateBasisIndependentVerificationV13(
        _ISSUER, canonical_json_bytes(result), verification_id, COORDINATE_BASIS_ID
    )


def replay_standard_2048_coordinate_basis_bytes_independently_v13() -> bytes:
    """Regenerate immutable producer-free coordinate evidence for consumers."""

    source = _expected_archive("SOURCE_SELECTION", SOURCE_SEED, SOURCE_COUNT)
    validation = _expected_archive(
        "HELDOUT_VALIDATION", VALIDATION_SEED, VALIDATION_COUNT
    )
    basis = _expected_basis(source, validation)
    if (
        source["coordinate_observation_archive_id"] != SOURCE_ARCHIVE_ID
        or validation["coordinate_observation_archive_id"]
        != VALIDATION_ARCHIVE_ID
        or basis["coordinate_basis_id"] != COORDINATE_BASIS_ID
    ):
        _fail("producer-free coordinate replay identity changed")
    return canonical_json_bytes(
        {
            "source_archive": source,
            "validation_archive": validation,
            "basis": basis,
        }
    )


__all__ = (
    "COORDINATE_BASIS_ID",
    "ConstructionK7Standard2048CoordinateBasisIndependentVerifierV13Error",
    "Standard2048CoordinateBasisIndependentVerificationV13",
    "replay_standard_2048_coordinate_basis_bytes_independently_v13",
    "verify_standard_2048_coordinate_basis_bytes_independently_v13",
)
