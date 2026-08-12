"""H=3 standard-2048 D4 world-model construction and matched direct control.

The registered mid-game state uses ordinary 4x4 swipe/spawn mechanics.  An
initially empty query-neutral D4 quotient model cannot certify the H=3 plan.
Each failed proof exposes the exact missing state-action frontier; only those
rows are materialized from the ground kernel.  The resulting model is reused
for a second receding-horizon decision and for a separately preregistered D4
held-out root.  A cold exact ground planner solves the same two source states.

This is a bounded construction control.  It does not claim an entire 2048
game, an observation/UI adapter, learned spawn probabilities, open-ended
coordinates, formal IID sampling, or official execution/economics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from functools import lru_cache
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.domains.g2048 import D4Transform, inverse_d4
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    SPAWN_DISTRIBUTION,
    Swipe2048Action,
    Swipe2048Outcome,
    Swipe2048State,
    Swipe2048Status,
    boards_from_rows_v1,
    canonicalize_state_action_v1,
    canonicalize_state_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    transform_action_v1,
    transform_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_DIRECT_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MODEL_AUDIT_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_QUOTIENT_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_RECEDING_CAMPAIGN_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_WORLD_MODEL_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.154"
PROFILE_KEY = "construction_k7_standard_2048_h3_receding_world_model_v1"
PLANNING_HORIZON = 3
RECEDING_DECISION_COUNT = 2
HELDOUT_TRANSFORM = D4Transform.ROTATE_90
HELDOUT_SPAWN_SEED = "standard-2048-heldout-seed-20260812-v1"

DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_PREREGISTRATION_V1_DOMAIN,
    "row": CONSTRUCTION_K7_STANDARD_2048_QUOTIENT_ROW_V1_DOMAIN,
    "model": CONSTRUCTION_K7_STANDARD_2048_WORLD_MODEL_V1_DOMAIN,
    "audit": CONSTRUCTION_K7_STANDARD_2048_MODEL_AUDIT_V1_DOMAIN,
    "plan": CONSTRUCTION_K7_STANDARD_2048_ABSTRACT_PLAN_V1_DOMAIN,
    "direct": CONSTRUCTION_K7_STANDARD_2048_MATCHED_DIRECT_V1_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_RECEDING_CAMPAIGN_V1_DOMAIN,
}
if len(DOMAINS) != len(set(DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("standard 2048 domains must be unique")
if not set(DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("standard 2048 domains must be centrally registered")

REGISTERED_SOURCE_BOARD = boards_from_rows_v1(
    (
        (1, 2, 3, 4),
        (2, 3, 4, 5),
        (3, 4, 5, 6),
        (1, 1, 2, 2),
    )
)
REGISTERED_HELDOUT_BOARD = transform_board_v1(REGISTERED_SOURCE_BOARD, HELDOUT_TRANSFORM)


class ConstructionK7Standard2048RecedingWorldModelV1Error(ValueError):
    """The preregistration, quotient row, proof, or direct control changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048RecedingWorldModelV1Error(message)


def _fraction(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _state_from_document(document: Mapping[str, Any]) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state document changed")
    try:
        state = Swipe2048State(
            tuple(document["board_ranks"]), Swipe2048Status(document["status"])
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048RecedingWorldModelV1Error(
            "state document is invalid"
        ) from error
    if state_from_board_v1(state.board) != state:
        _fail("state document status is not derived from the board")
    return state


def _row_key(state: Swipe2048State, action: Swipe2048Action) -> tuple[tuple[int, ...], str, str]:
    representative, transformed_action, _ = canonicalize_state_action_v1(state, action)
    return representative.board, representative.status.value, transformed_action.value


def _key_document(key: tuple[tuple[int, ...], str, str]) -> dict[str, Any]:
    board, status, action = key
    return {"state": {"board_ranks": list(board), "status": status}, "action": action}


@dataclass(frozen=True, slots=True)
class Standard2048QuotientOutcomeV1:
    probability: Fraction
    next_state: Swipe2048State
    merge_score: int
    represented_ground_outcome_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "probability", Fraction(self.probability))
        if (
            not 0 < self.probability <= 1
            or type(self.next_state) is not Swipe2048State
            or type(self.merge_score) is not int
            or self.merge_score < 0
            or type(self.represented_ground_outcome_count) is not int
            or self.represented_ground_outcome_count <= 0
        ):
            _fail("quotient outcome changed")

    def to_document(self) -> dict[str, Any]:
        return {
            "probability": _fraction(self.probability),
            "next_state": _state_document(self.next_state),
            "merge_score": self.merge_score,
            "represented_ground_outcome_count": self.represented_ground_outcome_count,
        }


@dataclass(frozen=True, slots=True)
class Standard2048QuotientRowV1:
    state: Swipe2048State
    action: Swipe2048Action
    outcomes: tuple[Standard2048QuotientOutcomeV1, ...]
    ground_outcome_count: int

    def __post_init__(self) -> None:
        if (
            type(self.state) is not Swipe2048State
            or canonicalize_state_v1(self.state)[0] != self.state
            or type(self.action) is not Swipe2048Action
            or self.action not in legal_actions_v1(self.state.board)
            or type(self.outcomes) is not tuple
            or not self.outcomes
            or any(type(row) is not Standard2048QuotientOutcomeV1 for row in self.outcomes)
            or type(self.ground_outcome_count) is not int
            or self.ground_outcome_count <= 0
            or sum((row.probability for row in self.outcomes), Fraction()) != 1
            or sum(row.represented_ground_outcome_count for row in self.outcomes)
            != self.ground_outcome_count
        ):
            _fail("quotient row changed")

    @property
    def key(self) -> tuple[tuple[int, ...], str, str]:
        return self.state.board, self.state.status.value, self.action.value

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_quotient_row.v1",
            "schema_version": SCHEMA_VERSION,
            "state": _state_document(self.state),
            "action": self.action.value,
            "outcomes": [row.to_document() for row in self.outcomes],
            "ground_outcome_count": self.ground_outcome_count,
            "ground_row_materialized_after_failed_proof": True,
            "spawn_law_known_exact_not_learned": True,
        }

    @property
    def row_id(self) -> str:
        return content_id(DOMAINS["row"], self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "quotient_row_id": self.row_id}


def _materialize_row(
    key: tuple[tuple[int, ...], str, str]
) -> Standard2048QuotientRowV1:
    board, status, action_value = key
    state = Swipe2048State(board, Swipe2048Status(status))
    action = Swipe2048Action(action_value)
    raw = step_v1(state, action)
    grouped: dict[tuple[tuple[int, ...], str, int], list[Any]] = {}
    for outcome in raw:
        representative, _ = canonicalize_state_v1(outcome.next_state)
        group_key = (representative.board, representative.status.value, outcome.merge_score)
        if group_key not in grouped:
            grouped[group_key] = [Fraction(), 0]
        grouped[group_key][0] += outcome.probability
        grouped[group_key][1] += 1
    outcomes = tuple(
        Standard2048QuotientOutcomeV1(
            probability,
            Swipe2048State(next_board, Swipe2048Status(next_status)),
            merge_score,
            count,
        )
        for (next_board, next_status, merge_score), (probability, count) in sorted(
            grouped.items()
        )
    )
    return Standard2048QuotientRowV1(state, action, outcomes, len(raw))


def _model_document(rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048QuotientRowV1]) -> dict[str, Any]:
    documents = [rows[key].to_document() for key in sorted(rows)]
    payload = {
        "schema": "acfqp.standard_2048_d4_world_model.v1",
        "schema_version": SCHEMA_VERSION,
        "semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_EXACT_SPAWN_V1",
        "abstraction": "EXACT_D4_STATE_ACTION_QUOTIENT_V1",
        "query_neutral": True,
        "known_spawn_distribution": [
            {"rank": rank, "probability": _fraction(probability)}
            for rank, probability in SPAWN_DISTRIBUTION
        ],
        "rows": documents,
        "row_count": len(documents),
        "ground_outcome_count": sum(row.ground_outcome_count for row in rows.values()),
    }
    return {**payload, "world_model_id": content_id(DOMAINS["model"], payload)}


@dataclass(frozen=True, slots=True)
class _ValueV1:
    expected_merge_score: Fraction
    loss_probability: Fraction
    selected_action: Swipe2048Action | None


def _better(candidate: _ValueV1, current: _ValueV1 | None) -> bool:
    if current is None:
        return True
    if candidate.expected_merge_score != current.expected_merge_score:
        return candidate.expected_merge_score > current.expected_merge_score
    if candidate.loss_probability != current.loss_probability:
        return candidate.loss_probability < current.loss_probability
    if candidate.selected_action is None:
        return False
    if current.selected_action is None:
        return True
    return ACTION_ORDER.index(candidate.selected_action) < ACTION_ORDER.index(current.selected_action)


def _missing_frontier(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048QuotientRowV1],
    root: Swipe2048State,
    horizon: int,
) -> tuple[tuple[tuple[int, ...], str, str], ...]:
    missing: set[tuple[tuple[int, ...], str, str]] = set()
    visited: set[tuple[tuple[int, ...], str, int]] = set()

    def walk(state: Swipe2048State, remaining: int) -> None:
        representative, _ = canonicalize_state_v1(state)
        visit_key = (representative.board, representative.status.value, remaining)
        if remaining == 0 or representative.status is not Swipe2048Status.ACTIVE or visit_key in visited:
            return
        visited.add(visit_key)
        for action in legal_actions_v1(representative.board):
            key = _row_key(representative, action)
            row = rows.get(key)
            if row is None:
                missing.add(key)
            else:
                for outcome in row.outcomes:
                    walk(outcome.next_state, remaining - 1)

    walk(root, horizon)
    return tuple(sorted(missing))


def _solve_model(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048QuotientRowV1],
    root: Swipe2048State,
    horizon: int,
) -> tuple[_ValueV1, tuple[str, ...]]:
    dependencies: set[str] = set()

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _ValueV1:
        state = Swipe2048State(board, Swipe2048Status(status_value))
        representative, _ = canonicalize_state_v1(state)
        if remaining == 0 or representative.status is Swipe2048Status.WON:
            return _ValueV1(Fraction(), Fraction(), None)
        if representative.status is Swipe2048Status.LOST:
            return _ValueV1(Fraction(), Fraction(1), None)
        best: _ValueV1 | None = None
        for action in legal_actions_v1(representative.board):
            key = _row_key(representative, action)
            row = rows.get(key)
            if row is None:
                _fail("model solve reached an unresolved row")
            dependencies.add(row.row_id)
            score = Fraction()
            loss = Fraction()
            for outcome in row.outcomes:
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (
                    outcome.merge_score + child.expected_merge_score
                )
                loss += outcome.probability * child.loss_probability
            candidate = _ValueV1(score, loss, action)
            if _better(candidate, best):
                best = candidate
        if best is None:
            return _ValueV1(Fraction(), Fraction(1), None)
        return best

    representative, transform = canonicalize_state_v1(root)
    result = solve(representative.board, representative.status.value, horizon)
    if result.selected_action is None:
        return result, tuple(sorted(dependencies))
    lifted = transform_action_v1(result.selected_action, inverse_d4(transform))
    return (
        _ValueV1(result.expected_merge_score, result.loss_probability, lifted),
        tuple(sorted(dependencies)),
    )


def _audit_document(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048QuotientRowV1],
    root: Swipe2048State,
    horizon: int,
) -> dict[str, Any]:
    model = _model_document(rows)
    missing = _missing_frontier(rows, root, horizon)
    payload: dict[str, Any] = {
        "schema": "acfqp.standard_2048_partial_model_audit.v1",
        "schema_version": SCHEMA_VERSION,
        "world_model_id": model["world_model_id"],
        "root_state": _state_document(root),
        "horizon": horizon,
        "objective": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_PROBABILITY_V1",
        "status": "FAILED_PROOF_FRONTIER" if missing else "CERTIFIED",
        "missing_frontier": [_key_document(key) for key in missing],
        "missing_frontier_count": len(missing),
    }
    if not missing:
        value, dependencies = _solve_model(rows, root, horizon)
        if value.selected_action is None:
            _fail("active registered root produced no certified action")
        plan_payload = {
            "schema": "acfqp.standard_2048_abstract_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "world_model_id": model["world_model_id"],
            "root_state": _state_document(root),
            "horizon": horizon,
            "objective": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_PROBABILITY_V1",
            "selected_action": value.selected_action.value,
            "expected_merge_score": _fraction(value.expected_merge_score),
            "loss_probability_within_horizon": _fraction(value.loss_probability),
            "ordered_dependency_row_ids": list(dependencies),
        }
        payload.update(
            {
                "selected_action": value.selected_action.value,
                "expected_merge_score": _fraction(value.expected_merge_score),
                "loss_probability_within_horizon": _fraction(value.loss_probability),
                "ordered_dependency_row_ids": list(dependencies),
                "abstract_plan_id": content_id(DOMAINS["plan"], plan_payload),
            }
        )
    else:
        payload.update(
            {
                "selected_action": None,
                "expected_merge_score": None,
                "loss_probability_within_horizon": None,
                "ordered_dependency_row_ids": [],
                "abstract_plan_id": None,
            }
        )
    return {**payload, "audit_id": content_id(DOMAINS["audit"], payload)}


def _recover_to_certificate(
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048QuotientRowV1],
    root: Swipe2048State,
    horizon: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], int, int]:
    rounds: list[dict[str, Any]] = []
    new_rows = 0
    new_outcomes = 0
    for transaction_index in range(1, horizon + 2):
        failed = _audit_document(rows, root, horizon)
        if failed["status"] == "CERTIFIED":
            return rounds, failed, new_rows, new_outcomes
        frontier = tuple(
            _row_key(
                _state_from_document(item["state"]),
                Swipe2048Action(item["action"]),
            )
            for item in failed["missing_frontier"]
        )
        predecessor = _model_document(rows)["world_model_id"]
        recovered: list[Standard2048QuotientRowV1] = []
        for key in frontier:
            if key not in rows:
                row = _materialize_row(key)
                rows[key] = row
                recovered.append(row)
                new_rows += 1
                new_outcomes += row.ground_outcome_count
        successor = _model_document(rows)["world_model_id"]
        rounds.append(
            {
                "transaction_index": transaction_index,
                "failed_audit_id": failed["audit_id"],
                "failed_status": failed["status"],
                "predecessor_world_model_id": predecessor,
                "recovered_frontier_count": len(recovered),
                "recovered_quotient_row_ids": [row.row_id for row in recovered],
                "recovered_ground_outcome_count": sum(
                    row.ground_outcome_count for row in recovered
                ),
                "successor_world_model_id": successor,
                "ground_access_before_failed_audit": False,
            }
        )
    _fail("bounded H=3 recovery did not converge")


def _direct_plan(root: Swipe2048State, horizon: int) -> dict[str, Any]:
    touched_rows: set[tuple[tuple[int, ...], str, str]] = set()
    outcome_count = 0

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _ValueV1:
        nonlocal outcome_count
        state = Swipe2048State(board, Swipe2048Status(status_value))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            return _ValueV1(Fraction(), Fraction(), None)
        if state.status is Swipe2048Status.LOST:
            return _ValueV1(Fraction(), Fraction(1), None)
        best: _ValueV1 | None = None
        for action in legal_actions_v1(state.board):
            key = (state.board, state.status.value, action.value)
            outcomes = step_v1(state, action)
            if key not in touched_rows:
                touched_rows.add(key)
                outcome_count += len(outcomes)
            score = Fraction()
            loss = Fraction()
            for outcome in outcomes:
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (
                    outcome.merge_score + child.expected_merge_score
                )
                loss += outcome.probability * child.loss_probability
            candidate = _ValueV1(score, loss, action)
            if _better(candidate, best):
                best = candidate
        if best is None:
            return _ValueV1(Fraction(), Fraction(1), None)
        return best

    value = solve(root.board, root.status.value, horizon)
    if value.selected_action is None:
        _fail("matched direct root produced no action")
    payload = {
        "schema": "acfqp.standard_2048_matched_direct_plan.v1",
        "schema_version": SCHEMA_VERSION,
        "root_state": _state_document(root),
        "horizon": horizon,
        "objective": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_PROBABILITY_V1",
        "selected_action": value.selected_action.value,
        "expected_merge_score": _fraction(value.expected_merge_score),
        "loss_probability_within_horizon": _fraction(value.loss_probability),
        "ground_state_action_row_count": len(touched_rows),
        "ground_outcome_count": outcome_count,
        "cold_model_per_decision": True,
        "quotient_or_prior_used": False,
    }
    return {**payload, "matched_direct_plan_id": content_id(DOMAINS["direct"], payload)}


def _preregistration_document() -> dict[str, Any]:
    source = state_from_board_v1(REGISTERED_SOURCE_BOARD)
    heldout = state_from_board_v1(REGISTERED_HELDOUT_BOARD)
    payload = {
        "schema": "acfqp.standard_2048_receding_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "environment_semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_SPAWN_V1",
        "source_root_state": _state_document(source),
        "heldout_root_state": _state_document(heldout),
        "heldout_transform": HELDOUT_TRANSFORM.value,
        "planning_horizon": PLANNING_HORIZON,
        "receding_decision_count": RECEDING_DECISION_COUNT,
        "spawn_tape_seed": HELDOUT_SPAWN_SEED,
        "goal_rank": GOAL_RANK,
        "query_and_seed_frozen_before_model_construction": True,
        "matched_direct_control_frozen_before_model_construction": True,
        "exact_known_spawn_law": [
            {"rank": rank, "probability": _fraction(probability)}
            for rank, probability in SPAWN_DISTRIBUTION
        ],
    }
    return {
        **payload,
        "standard_2048_preregistration_id": content_id(DOMAINS["preregistration"], payload),
    }


def _campaign_document() -> dict[str, Any]:
    preregistration = _preregistration_document()
    source = state_from_board_v1(REGISTERED_SOURCE_BOARD)
    heldout = state_from_board_v1(REGISTERED_HELDOUT_BOARD)
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048QuotientRowV1] = {}

    initial_audit = _audit_document(rows, source, PLANNING_HORIZON)
    if initial_audit["status"] != "FAILED_PROOF_FRONTIER":
        _fail("empty model unexpectedly certified the source plan")
    first_rounds, first_plan, first_rows, first_outcomes = _recover_to_certificate(
        rows, source, PLANNING_HORIZON
    )
    direct_first = _direct_plan(source, PLANNING_HORIZON)
    if (
        first_plan["selected_action"] != direct_first["selected_action"]
        or first_plan["expected_merge_score"] != direct_first["expected_merge_score"]
        or first_plan["loss_probability_within_horizon"]
        != direct_first["loss_probability_within_horizon"]
    ):
        _fail("quotient and matched direct source plans differ")

    source_outcomes = step_v1(source, Swipe2048Action(first_plan["selected_action"]))
    selected_outcome, spawn_digest = select_seeded_outcome_v1(
        source_outcomes, seed=HELDOUT_SPAWN_SEED, decision_index=0
    )
    successor = selected_outcome.next_state
    successor_base_audit = _audit_document(rows, successor, PLANNING_HORIZON)
    successor_rounds, successor_plan, successor_rows, successor_outcomes = (
        _recover_to_certificate(rows, successor, PLANNING_HORIZON)
    )
    direct_successor = _direct_plan(successor, PLANNING_HORIZON)
    if (
        successor_plan["selected_action"] != direct_successor["selected_action"]
        or successor_plan["expected_merge_score"]
        != direct_successor["expected_merge_score"]
        or successor_plan["loss_probability_within_horizon"]
        != direct_successor["loss_probability_within_horizon"]
    ):
        _fail("quotient and matched direct successor plans differ")

    heldout_before = len(rows)
    heldout_audit = _audit_document(rows, heldout, PLANNING_HORIZON)
    if heldout_audit["status"] != "CERTIFIED" or len(rows) != heldout_before:
        _fail("D4 held-out root did not reuse the frozen model exactly")
    expected_heldout_action = transform_action_v1(
        Swipe2048Action(first_plan["selected_action"]), HELDOUT_TRANSFORM
    )
    if heldout_audit["selected_action"] != expected_heldout_action.value:
        _fail("held-out action is not the exact D4 transport")

    final_model = _model_document(rows)
    payload = {
        "schema": "acfqp.standard_2048_receding_world_model_campaign.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration": preregistration,
        "initial_empty_model_audit": initial_audit,
        "first_decision_recovery_transactions": first_rounds,
        "first_decision_plan": first_plan,
        "executed_first_transition": {
            "action": first_plan["selected_action"],
            "selected_spawn_tape_digest": spawn_digest,
            "selected_outcome_probability": _fraction(selected_outcome.probability),
            "spawned_cell": selected_outcome.spawned_cell,
            "spawned_rank": selected_outcome.spawned_rank,
            "merge_score": selected_outcome.merge_score,
            "successor_state": _state_document(successor),
        },
        "successor_base_audit": successor_base_audit,
        "second_decision_recovery_transactions": successor_rounds,
        "second_decision_plan": successor_plan,
        "heldout_d4_reuse_audit": heldout_audit,
        "final_world_model": final_model,
        "matched_direct_baseline": {
            "first_decision": direct_first,
            "second_decision": direct_successor,
            "total_ground_state_action_row_count": (
                direct_first["ground_state_action_row_count"]
                + direct_successor["ground_state_action_row_count"]
            ),
            "total_ground_outcome_count": (
                direct_first["ground_outcome_count"]
                + direct_successor["ground_outcome_count"]
            ),
        },
        "world_model_ground_row_count": first_rows + successor_rows,
        "world_model_ground_outcome_count": first_outcomes + successor_outcomes,
        "first_decision_ground_row_count": first_rows,
        "second_decision_incremental_ground_row_count": successor_rows,
        "heldout_reuse_incremental_ground_row_count": 0,
        "planning_horizon": PLANNING_HORIZON,
        "receding_horizon_decision_count": RECEDING_DECISION_COUNT,
        "standard_4x4_swipe_spawn_semantics_executed": True,
        "reusable_d4_quotient_world_model_synthesized": True,
        "ground_rows_materialized_only_after_failed_proof": True,
        "multi_step_planning_mainly_completed_in_abstract_model": True,
        "matched_cold_direct_baseline_present": True,
        "heldout_d4_model_reuse_without_ground": True,
        "spawn_law_learned_from_observations": False,
        "observation_derived_coordinate_invention_claimed": False,
        "unknown_support_learning_claimed": False,
        "formal_exact_iid_claimed": False,
        "full_standard_2048_game_completed": False,
        "real_game_ui_adapter_present": False,
        "broad_board_or_game_generalization_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(DOMAINS["campaign"], payload)}


_CAMPAIGN_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048RecedingWorldModelCampaignV1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _CAMPAIGN_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
        ):
            _fail("campaign bytes changed")
        expected = content_id(
            DOMAINS["campaign"],
            {key: value for key, value in document.items() if key != "campaign_id"},
        )
        if expected != self.campaign_id:
            _fail("campaign content ID changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("canonical campaign root is not an object")
        return document


def run_standard_2048_receding_world_model_campaign_v1(
) -> Standard2048RecedingWorldModelCampaignV1:
    document = _campaign_document()
    return Standard2048RecedingWorldModelCampaignV1(
        _CAMPAIGN_ISSUER, canonical_json_bytes(document), document["campaign_id"]
    )


def verify_standard_2048_receding_world_model_campaign_v1(
    campaign: Standard2048RecedingWorldModelCampaignV1,
) -> Standard2048RecedingWorldModelCampaignV1:
    if type(campaign) is not Standard2048RecedingWorldModelCampaignV1:
        _fail("campaign verifier rejects foreign values")
    campaign.__post_init__()
    expected = _campaign_document()
    if campaign.canonical_bytes != canonical_json_bytes(expected):
        _fail("campaign differs from exact semantic replay")
    return campaign


__all__ = (
    "ConstructionK7Standard2048RecedingWorldModelV1Error",
    "DOMAINS",
    "HELDOUT_SPAWN_SEED",
    "HELDOUT_TRANSFORM",
    "PLANNING_HORIZON",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RECEDING_DECISION_COUNT",
    "REGISTERED_HELDOUT_BOARD",
    "REGISTERED_SOURCE_BOARD",
    "SCHEMA_VERSION",
    "Standard2048RecedingWorldModelCampaignV1",
    "run_standard_2048_receding_world_model_campaign_v1",
    "verify_standard_2048_receding_world_model_campaign_v1",
)
