"""Observation-derived partial 2048 dynamics with multi-seed receding control.

This bounded campaign learns only the rank-two spawn probability interval from
an identity-separated source observation archive.  Board geometry, swipe
semantics, spawn-cell support, and uniform conditional cell placement remain
registered public mechanics.  A persistent D4 quotient model is populated only
after a failed H=3 proof identifies missing support rows.  Three preregistered
held-out episodes execute three receding decisions each, with a cold exact
ground planner used only as a matched evaluation control.

The result is not an IID proof, unknown-support learner, full-game agent, UI
adapter, broad sample-efficiency claim, or official economics artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, Mapping, NoReturn

from acfqp.construction_k7_standard_2048_spawn_observation_v1 import (
    SOURCE_OBSERVATION_SEED,
    SOURCE_SAMPLE_COUNT,
    Standard2048SpawnObservationEvidenceV1,
    build_standard_2048_spawn_observation_evidence_v1,
    verify_standard_2048_spawn_observation_evidence_v1,
)
from acfqp.domains.g2048 import inverse_d4
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    boards_from_rows_v1,
    canonicalize_state_action_v1,
    canonicalize_state_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    support_outcomes_v1,
    transform_action_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_MULTISEED_CAMPAIGN_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PARTIAL_MODEL_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PARTIAL_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ROBUST_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_AUDIT_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_EPISODE_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_MATCHED_DIRECT_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_PREREGISTRATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.155"
PROFILE_KEY = "construction_k7_standard_2048_multiseed_partial_world_model_v1"
PLANNING_HORIZON = 3
EPISODE_DECISION_COUNT = 3
HELDOUT_EPISODE_SEEDS = (
    "standard-2048-heldout-episode-000",
    "standard-2048-heldout-episode-003",
    "standard-2048-heldout-episode-081",
)

DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_PREREGISTRATION_V1_DOMAIN,
    "row": CONSTRUCTION_K7_STANDARD_2048_PARTIAL_ROW_V1_DOMAIN,
    "model": CONSTRUCTION_K7_STANDARD_2048_PARTIAL_MODEL_V1_DOMAIN,
    "audit": CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_AUDIT_V1_DOMAIN,
    "plan": CONSTRUCTION_K7_STANDARD_2048_ROBUST_PLAN_V1_DOMAIN,
    "direct": CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_MATCHED_DIRECT_V1_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_EPISODE_V1_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_MULTISEED_CAMPAIGN_V1_DOMAIN,
}
if len(DOMAINS) != len(set(DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("statistical standard-2048 domains must be unique")
if not set(DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("statistical standard-2048 domains are not registered")

REGISTERED_ROOT_BOARD = boards_from_rows_v1(
    (
        (1, 2, 3, 4),
        (2, 3, 4, 5),
        (3, 4, 5, 6),
        (1, 1, 2, 2),
    )
)


class ConstructionK7Standard2048MultiseedPartialWorldModelV1Error(ValueError):
    """A statistical identity, partial row, proof, or control changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048MultiseedPartialWorldModelV1Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction_from_document(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        try:
            return Fraction(value["numerator"], value["denominator"])
        except (TypeError, ValueError, ZeroDivisionError) as error:
            raise ConstructionK7Standard2048MultiseedPartialWorldModelV1Error(
                "fraction document is invalid"
            ) from error
    _fail("fraction document changed")


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
        raise ConstructionK7Standard2048MultiseedPartialWorldModelV1Error(
            "state document is invalid"
        ) from error
    if state_from_board_v1(state.board) != state:
        _fail("state status is not derived from its board")
    return state


def _row_key(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[tuple[int, ...], str, str]:
    representative, transported_action, _ = canonicalize_state_action_v1(state, action)
    return (
        representative.board,
        representative.status.value,
        transported_action.value,
    )


def _key_document(key: tuple[tuple[int, ...], str, str]) -> dict[str, Any]:
    board, status, action = key
    return {
        "state": {"board_ranks": list(board), "status": status},
        "action": action,
    }


@dataclass(frozen=True, slots=True)
class Standard2048PartialOutcomeV1:
    spawn_rank: int
    conditional_cell_probability: Fraction
    next_state: Swipe2048State
    merge_score: int
    represented_support_outcome_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "conditional_cell_probability", Fraction(self.conditional_cell_probability)
        )
        if (
            self.spawn_rank not in (1, 2)
            or not 0 < self.conditional_cell_probability <= 1
            or type(self.next_state) is not Swipe2048State
            or type(self.merge_score) is not int
            or self.merge_score < 0
            or type(self.represented_support_outcome_count) is not int
            or self.represented_support_outcome_count <= 0
        ):
            _fail("partial outcome changed")

    def to_document(self) -> dict[str, Any]:
        return {
            "spawn_rank": self.spawn_rank,
            "conditional_cell_probability": _fdoc(self.conditional_cell_probability),
            "next_state": _state_document(self.next_state),
            "merge_score": self.merge_score,
            "represented_support_outcome_count": self.represented_support_outcome_count,
        }


@dataclass(frozen=True, slots=True)
class Standard2048PartialRowV1:
    state: Swipe2048State
    action: Swipe2048Action
    outcomes: tuple[Standard2048PartialOutcomeV1, ...]
    support_outcome_count: int
    spawn_probability_interval_id: str

    def __post_init__(self) -> None:
        if (
            type(self.state) is not Swipe2048State
            or canonicalize_state_v1(self.state)[0] != self.state
            or type(self.action) is not Swipe2048Action
            or self.action not in legal_actions_v1(self.state.board)
            or type(self.outcomes) is not tuple
            or not self.outcomes
            or any(type(row) is not Standard2048PartialOutcomeV1 for row in self.outcomes)
            or type(self.support_outcome_count) is not int
            or self.support_outcome_count <= 0
            or type(self.spawn_probability_interval_id) is not str
            or len(self.spawn_probability_interval_id) != 64
        ):
            _fail("partial row changed")
        for rank in (1, 2):
            if sum(
                (
                    row.conditional_cell_probability
                    for row in self.outcomes
                    if row.spawn_rank == rank
                ),
                Fraction(),
            ) != 1:
                _fail("conditional spawn-cell probability is not normalized")
        if (
            sum(row.represented_support_outcome_count for row in self.outcomes)
            != self.support_outcome_count
        ):
            _fail("partial support count changed")

    @property
    def key(self) -> tuple[tuple[int, ...], str, str]:
        return self.state.board, self.state.status.value, self.action.value

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_partial_spawn_row.v1",
            "schema_version": SCHEMA_VERSION,
            "state": _state_document(self.state),
            "action": self.action.value,
            "spawn_probability_interval_id": self.spawn_probability_interval_id,
            "outcomes": [row.to_document() for row in self.outcomes],
            "support_outcome_count": self.support_outcome_count,
            "support_and_position_geometry_known_structural": True,
            "spawn_rank_probability_point_value_absent": True,
            "materialized_only_after_failed_proof": True,
        }

    @property
    def row_id(self) -> str:
        return content_id(DOMAINS["row"], self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "partial_row_id": self.row_id}


def _materialize_partial_row(
    key: tuple[tuple[int, ...], str, str], interval_id: str
) -> Standard2048PartialRowV1:
    """Read support geometry only; exact spawn probabilities are inaccessible here."""

    board, status_value, action_value = key
    state = Swipe2048State(board, Swipe2048Status(status_value))
    action = Swipe2048Action(action_value)
    raw_support = support_outcomes_v1(state, action)
    empty_count = len(raw_support) // 2
    if empty_count <= 0 or len(raw_support) != 2 * empty_count:
        _fail("public spawn support cardinality changed")
    grouped: dict[tuple[int, tuple[int, ...], str, int], int] = {}
    for outcome in raw_support:
        representative, _ = canonicalize_state_v1(outcome.next_state)
        group_key = (
            outcome.spawned_rank,
            representative.board,
            representative.status.value,
            outcome.merge_score,
        )
        grouped[group_key] = grouped.get(group_key, 0) + 1
    outcomes = tuple(
        Standard2048PartialOutcomeV1(
            rank,
            Fraction(count, empty_count),
            Swipe2048State(next_board, Swipe2048Status(next_status)),
            merge_score,
            count,
        )
        for (rank, next_board, next_status, merge_score), count in sorted(grouped.items())
    )
    return Standard2048PartialRowV1(
        state, action, outcomes, len(raw_support), interval_id
    )


def _model_document(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048PartialRowV1],
    archive_id: str,
    interval_id: str,
) -> dict[str, Any]:
    row_documents = [rows[key].to_document() for key in sorted(rows)]
    payload = {
        "schema": "acfqp.standard_2048_partial_d4_world_model.v1",
        "schema_version": SCHEMA_VERSION,
        "semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_PARTIAL_SPAWN_V1",
        "abstraction": "D4_STATE_ACTION_QUOTIENT_WITH_RANK_INTERVAL_V1",
        "query_neutral": True,
        "spawn_observation_archive_id": archive_id,
        "spawn_probability_interval_id": interval_id,
        "support_and_position_geometry_known_structural": True,
        "rank_probability_observation_derived_interval": True,
        "rectangular_rowwise_interval_relaxation": True,
        "rows": row_documents,
        "row_count": len(row_documents),
        "support_outcome_count": sum(row.support_outcome_count for row in rows.values()),
    }
    return {**payload, "partial_world_model_id": content_id(DOMAINS["model"], payload)}


@dataclass(frozen=True, slots=True)
class _RobustValueV1:
    score_lower: Fraction
    score_upper: Fraction
    loss_upper: Fraction
    selected_action: Swipe2048Action | None


@dataclass(frozen=True, slots=True)
class _ExactValueV1:
    expected_score: Fraction
    loss_probability: Fraction
    selected_action: Swipe2048Action | None


def _better_robust(candidate: _RobustValueV1, current: _RobustValueV1 | None) -> bool:
    if current is None:
        return True
    candidate_key = (
        candidate.score_lower,
        -candidate.loss_upper,
        candidate.score_upper,
        -ACTION_ORDER.index(candidate.selected_action),
    )
    current_key = (
        current.score_lower,
        -current.loss_upper,
        current.score_upper,
        -ACTION_ORDER.index(current.selected_action),
    )
    return candidate_key > current_key


def _better_exact(candidate: _ExactValueV1, current: _ExactValueV1 | None) -> bool:
    if current is None:
        return True
    candidate_key = (
        candidate.expected_score,
        -candidate.loss_probability,
        -ACTION_ORDER.index(candidate.selected_action),
    )
    current_key = (
        current.expected_score,
        -current.loss_probability,
        -ACTION_ORDER.index(current.selected_action),
    )
    return candidate_key > current_key


def _missing_frontier(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048PartialRowV1],
    root: Swipe2048State,
    horizon: int,
) -> tuple[tuple[tuple[int, ...], str, str], ...]:
    missing: set[tuple[tuple[int, ...], str, str]] = set()
    visited: set[tuple[tuple[int, ...], str, int]] = set()

    def walk(state: Swipe2048State, remaining: int) -> None:
        representative, _ = canonicalize_state_v1(state)
        visit_key = (representative.board, representative.status.value, remaining)
        if (
            remaining == 0
            or representative.status is not Swipe2048Status.ACTIVE
            or visit_key in visited
        ):
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


def _solve_robust(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048PartialRowV1],
    root: Swipe2048State,
    horizon: int,
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> tuple[_RobustValueV1, tuple[str, ...]]:
    dependencies: set[str] = set()

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _RobustValueV1:
        state = Swipe2048State(board, Swipe2048Status(status_value))
        representative, _ = canonicalize_state_v1(state)
        if remaining == 0 or representative.status is Swipe2048Status.WON:
            return _RobustValueV1(Fraction(), Fraction(), Fraction(), None)
        if representative.status is Swipe2048Status.LOST:
            return _RobustValueV1(Fraction(), Fraction(), Fraction(1), None)
        best: _RobustValueV1 | None = None
        for action in legal_actions_v1(representative.board):
            key = _row_key(representative, action)
            row = rows.get(key)
            if row is None:
                _fail("robust solve reached an unresolved support row")
            dependencies.add(row.row_id)
            by_rank: dict[int, tuple[Fraction, Fraction, Fraction]] = {}
            for rank in (1, 2):
                lower = Fraction()
                upper = Fraction()
                loss = Fraction()
                for outcome in row.outcomes:
                    if outcome.spawn_rank != rank:
                        continue
                    child = solve(
                        outcome.next_state.board,
                        outcome.next_state.status.value,
                        remaining - 1,
                    )
                    weight = outcome.conditional_cell_probability
                    lower += weight * (outcome.merge_score + child.score_lower)
                    upper += weight * (outcome.merge_score + child.score_upper)
                    loss += weight * child.loss_upper
                by_rank[rank] = lower, upper, loss
            lower_endpoints = tuple(
                (1 - probability) * by_rank[1][0] + probability * by_rank[2][0]
                for probability in (rank_two_lower, rank_two_upper)
            )
            upper_endpoints = tuple(
                (1 - probability) * by_rank[1][1] + probability * by_rank[2][1]
                for probability in (rank_two_lower, rank_two_upper)
            )
            loss_endpoints = tuple(
                (1 - probability) * by_rank[1][2] + probability * by_rank[2][2]
                for probability in (rank_two_lower, rank_two_upper)
            )
            candidate = _RobustValueV1(
                min(lower_endpoints),
                max(upper_endpoints),
                max(loss_endpoints),
                action,
            )
            if _better_robust(candidate, best):
                best = candidate
        if best is None:
            return _RobustValueV1(Fraction(), Fraction(), Fraction(1), None)
        return best

    representative, transform = canonicalize_state_v1(root)
    result = solve(representative.board, representative.status.value, horizon)
    if result.selected_action is None:
        return result, tuple(sorted(dependencies))
    lifted = transform_action_v1(result.selected_action, inverse_d4(transform))
    return (
        _RobustValueV1(
            result.score_lower, result.score_upper, result.loss_upper, lifted
        ),
        tuple(sorted(dependencies)),
    )


def _audit_document(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048PartialRowV1],
    root: Swipe2048State,
    horizon: int,
    archive_id: str,
    interval_id: str,
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> dict[str, Any]:
    model = _model_document(rows, archive_id, interval_id)
    missing = _missing_frontier(rows, root, horizon)
    payload: dict[str, Any] = {
        "schema": "acfqp.standard_2048_statistical_partial_model_audit.v1",
        "schema_version": SCHEMA_VERSION,
        "partial_world_model_id": model["partial_world_model_id"],
        "spawn_probability_interval_id": interval_id,
        "root_state": _state_document(root),
        "horizon": horizon,
        "objective": "MAX_ROBUST_SCORE_LOWER_THEN_MIN_ROBUST_LOSS_UPPER_V1",
        "status": "FAILED_PROOF_FRONTIER" if missing else "CERTIFIED_INTERVAL_ROBUST",
        "missing_frontier": [_key_document(key) for key in missing],
        "missing_frontier_count": len(missing),
    }
    if missing:
        payload.update(
            {
                "selected_action": None,
                "robust_score_lower": None,
                "robust_score_upper": None,
                "robust_loss_probability_upper": None,
                "ordered_dependency_row_ids": [],
                "robust_plan_id": None,
            }
        )
    else:
        value, dependencies = _solve_robust(
            rows, root, horizon, rank_two_lower, rank_two_upper
        )
        if value.selected_action is None:
            _fail("active root produced no interval-robust action")
        plan_payload = {
            "schema": "acfqp.standard_2048_interval_robust_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_world_model_id": model["partial_world_model_id"],
            "spawn_probability_interval_id": interval_id,
            "root_state": _state_document(root),
            "horizon": horizon,
            "objective": "MAX_ROBUST_SCORE_LOWER_THEN_MIN_ROBUST_LOSS_UPPER_V1",
            "selected_action": value.selected_action.value,
            "robust_score_lower": _fdoc(value.score_lower),
            "robust_score_upper": _fdoc(value.score_upper),
            "robust_loss_probability_upper": _fdoc(value.loss_upper),
            "ordered_dependency_row_ids": list(dependencies),
        }
        payload.update(
            {
                "selected_action": value.selected_action.value,
                "robust_score_lower": _fdoc(value.score_lower),
                "robust_score_upper": _fdoc(value.score_upper),
                "robust_loss_probability_upper": _fdoc(value.loss_upper),
                "ordered_dependency_row_ids": list(dependencies),
                "robust_plan_id": content_id(DOMAINS["plan"], plan_payload),
            }
        )
    return {**payload, "audit_id": content_id(DOMAINS["audit"], payload)}


def _recover_to_certificate(
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048PartialRowV1],
    root: Swipe2048State,
    horizon: int,
    archive_id: str,
    interval_id: str,
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> tuple[list[dict[str, Any]], dict[str, Any], int, int]:
    transactions: list[dict[str, Any]] = []
    added_rows = 0
    added_support = 0
    for transaction_index in range(1, horizon + 2):
        failed = _audit_document(
            rows,
            root,
            horizon,
            archive_id,
            interval_id,
            rank_two_lower,
            rank_two_upper,
        )
        if failed["status"] == "CERTIFIED_INTERVAL_ROBUST":
            return transactions, failed, added_rows, added_support
        frontier = tuple(
            _row_key(
                _state_from_document(item["state"]),
                Swipe2048Action(item["action"]),
            )
            for item in failed["missing_frontier"]
        )
        predecessor = _model_document(rows, archive_id, interval_id)[
            "partial_world_model_id"
        ]
        recovered: list[Standard2048PartialRowV1] = []
        for key in frontier:
            if key not in rows:
                row = _materialize_partial_row(key, interval_id)
                rows[key] = row
                recovered.append(row)
                added_rows += 1
                added_support += row.support_outcome_count
        successor = _model_document(rows, archive_id, interval_id)[
            "partial_world_model_id"
        ]
        transactions.append(
            {
                "transaction_index": transaction_index,
                "failed_audit_id": failed["audit_id"],
                "failed_status": failed["status"],
                "predecessor_partial_world_model_id": predecessor,
                "recovered_frontier_count": len(recovered),
                "recovered_partial_row_ids": [row.row_id for row in recovered],
                "recovered_support_outcome_count": sum(
                    row.support_outcome_count for row in recovered
                ),
                "successor_partial_world_model_id": successor,
                "ground_support_access_before_failed_audit": False,
                "exact_spawn_probability_accessed_by_recovery": False,
            }
        )
    _fail("bounded interval recovery did not converge")


def _direct_plan(root: Swipe2048State, horizon: int) -> dict[str, Any]:
    touched_rows: set[tuple[tuple[int, ...], str, str]] = set()
    outcome_count = 0

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _ExactValueV1:
        nonlocal outcome_count
        state = Swipe2048State(board, Swipe2048Status(status_value))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            return _ExactValueV1(Fraction(), Fraction(), None)
        if state.status is Swipe2048Status.LOST:
            return _ExactValueV1(Fraction(), Fraction(1), None)
        best: _ExactValueV1 | None = None
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
                    outcome.merge_score + child.expected_score
                )
                loss += outcome.probability * child.loss_probability
            candidate = _ExactValueV1(score, loss, action)
            if _better_exact(candidate, best):
                best = candidate
        if best is None:
            return _ExactValueV1(Fraction(), Fraction(1), None)
        return best

    value = solve(root.board, root.status.value, horizon)
    if value.selected_action is None:
        _fail("matched direct root produced no action")
    payload = {
        "schema": "acfqp.standard_2048_statistical_matched_direct.v1",
        "schema_version": SCHEMA_VERSION,
        "root_state": _state_document(root),
        "horizon": horizon,
        "objective": "MAX_EXACT_EXPECTED_SCORE_THEN_MIN_LOSS_V1",
        "selected_action": value.selected_action.value,
        "expected_merge_score": _fdoc(value.expected_score),
        "loss_probability_within_horizon": _fdoc(value.loss_probability),
        "ground_state_action_row_count": len(touched_rows),
        "ground_outcome_count": outcome_count,
        "cold_model_per_decision": True,
        "evaluation_lane_only": True,
        "partial_model_or_source_observations_used": False,
    }
    return {**payload, "matched_direct_plan_id": content_id(DOMAINS["direct"], payload)}


def _preregistration_document(
    evidence: Standard2048SpawnObservationEvidenceV1,
) -> dict[str, Any]:
    evidence_document = evidence.to_document()
    root = state_from_board_v1(REGISTERED_ROOT_BOARD)
    payload = {
        "schema": "acfqp.standard_2048_multiseed_statistical_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "environment_semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_SPAWN_V1",
        "registered_root_state": _state_document(root),
        "planning_horizon": PLANNING_HORIZON,
        "episode_decision_count": EPISODE_DECISION_COUNT,
        "heldout_episode_seeds": list(HELDOUT_EPISODE_SEEDS),
        "source_observation_seed": SOURCE_OBSERVATION_SEED,
        "source_sample_count": SOURCE_SAMPLE_COUNT,
        "spawn_observation_archive_id": evidence.spawn_observation_archive_id,
        "spawn_probability_interval_id": evidence.spawn_probability_interval_id,
        "goal_rank": GOAL_RANK,
        "source_archive_frozen_before_target_preregistration": evidence_document[
            "archive"
        ]["source_archive_frozen_before_target_preregistration"],
        "source_and_target_identities_disjoint": (
            SOURCE_OBSERVATION_SEED not in HELDOUT_EPISODE_SEEDS
            and len(set(HELDOUT_EPISODE_SEEDS)) == len(HELDOUT_EPISODE_SEEDS)
        ),
        "episode_seeds_and_matched_controls_frozen_before_model_construction": True,
        "known_structural_mechanics": [
            "WHOLE_BOARD_SWIPE",
            "SPAWN_CELL_SUPPORT",
            "UNIFORM_CELL_GIVEN_RANK",
            "D4_TRANSPORT",
        ],
        "observation_derived_parameter": "P_SPAWN_RANK_TWO_INTERVAL",
    }
    return {
        **payload,
        "statistical_preregistration_id": content_id(DOMAINS["preregistration"], payload),
    }


def _run_episode(
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048PartialRowV1],
    *,
    episode_index: int,
    seed: str,
    preregistration_id: str,
    archive_id: str,
    interval_id: str,
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> tuple[dict[str, Any], int, int, int, int]:
    state = state_from_board_v1(REGISTERED_ROOT_BOARD)
    initial_model_id = _model_document(rows, archive_id, interval_id)[
        "partial_world_model_id"
    ]
    decisions: list[dict[str, Any]] = []
    episode_rows = 0
    episode_support = 0
    direct_rows = 0
    direct_outcomes = 0
    for decision_index in range(EPISODE_DECISION_COUNT):
        base_audit = _audit_document(
            rows,
            state,
            PLANNING_HORIZON,
            archive_id,
            interval_id,
            rank_two_lower,
            rank_two_upper,
        )
        transactions, certified, added_rows, added_support = _recover_to_certificate(
            rows,
            state,
            PLANNING_HORIZON,
            archive_id,
            interval_id,
            rank_two_lower,
            rank_two_upper,
        )
        direct = _direct_plan(state, PLANNING_HORIZON)
        if certified["selected_action"] != direct["selected_action"]:
            _fail("interval-robust and matched-direct selected actions differ")
        exact_score = _fraction_from_document(direct["expected_merge_score"])
        exact_loss = _fraction_from_document(direct["loss_probability_within_horizon"])
        if not (
            _fraction_from_document(certified["robust_score_lower"])
            <= exact_score
            <= _fraction_from_document(certified["robust_score_upper"])
            and exact_loss
            <= _fraction_from_document(certified["robust_loss_probability_upper"])
        ):
            _fail("exact matched value escaped the registered robust envelope")
        action = Swipe2048Action(certified["selected_action"])
        target_outcomes = step_v1(state, action)
        selected, digest = select_seeded_outcome_v1(
            target_outcomes, seed=seed, decision_index=decision_index
        )
        decision_payload = {
            "episode_index": episode_index,
            "decision_index": decision_index,
            "state_before_decision": _state_document(state),
            "base_audit": base_audit,
            "recovery_transactions": transactions,
            "certified_robust_plan": certified,
            "matched_direct_control": direct,
            "selected_action_agrees_with_matched_direct": True,
            "exact_direct_value_inside_robust_envelope": True,
            "incremental_partial_row_count": added_rows,
            "incremental_support_outcome_count": added_support,
            "executed_target_transition": {
                "target_seed": seed,
                "target_decision_index": decision_index,
                "spawn_tape_digest": digest,
                "selected_action": action.value,
                "selected_outcome_probability_evaluation_only": _fdoc(
                    selected.probability
                ),
                "spawned_cell": selected.spawned_cell,
                "spawned_rank": selected.spawned_rank,
                "merge_score": selected.merge_score,
                "successor_state": _state_document(selected.next_state),
                "target_observation_not_used_before_plan_freeze": True,
            },
        }
        decisions.append(decision_payload)
        state = selected.next_state
        episode_rows += added_rows
        episode_support += added_support
        direct_rows += direct["ground_state_action_row_count"]
        direct_outcomes += direct["ground_outcome_count"]
    final_model_id = _model_document(rows, archive_id, interval_id)[
        "partial_world_model_id"
    ]
    payload = {
        "schema": "acfqp.standard_2048_statistical_receding_episode.v1",
        "schema_version": SCHEMA_VERSION,
        "statistical_preregistration_id": preregistration_id,
        "episode_index": episode_index,
        "heldout_episode_seed": seed,
        "initial_state": _state_document(state_from_board_v1(REGISTERED_ROOT_BOARD)),
        "initial_partial_world_model_id": initial_model_id,
        "decisions": decisions,
        "decision_count": len(decisions),
        "terminal_state_after_registered_prefix": _state_document(state),
        "final_partial_world_model_id": final_model_id,
        "incremental_partial_row_count": episode_rows,
        "incremental_support_outcome_count": episode_support,
        "matched_direct_ground_row_count": direct_rows,
        "matched_direct_ground_outcome_count": direct_outcomes,
    }
    return (
        {**payload, "episode_id": content_id(DOMAINS["episode"], payload)},
        episode_rows,
        episode_support,
        direct_rows,
        direct_outcomes,
    )


def _campaign_document() -> dict[str, Any]:
    evidence = build_standard_2048_spawn_observation_evidence_v1()
    verify_standard_2048_spawn_observation_evidence_v1(evidence)
    evidence_document = evidence.to_document()
    interval = evidence_document["interval"]
    rank_two_lower = Fraction(interval["rank_two_probability_lower"])
    rank_two_upper = Fraction(interval["rank_two_probability_upper"])
    preregistration = _preregistration_document(evidence)
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048PartialRowV1] = {}
    episodes: list[dict[str, Any]] = []
    total_rows = 0
    total_support = 0
    total_direct_rows = 0
    total_direct_outcomes = 0
    for episode_index, seed in enumerate(HELDOUT_EPISODE_SEEDS):
        episode, added_rows, added_support, direct_rows, direct_outcomes = _run_episode(
            rows,
            episode_index=episode_index,
            seed=seed,
            preregistration_id=preregistration["statistical_preregistration_id"],
            archive_id=evidence.spawn_observation_archive_id,
            interval_id=evidence.spawn_probability_interval_id,
            rank_two_lower=rank_two_lower,
            rank_two_upper=rank_two_upper,
        )
        episodes.append(episode)
        total_rows += added_rows
        total_support += added_support
        total_direct_rows += direct_rows
        total_direct_outcomes += direct_outcomes
    final_model = _model_document(
        rows, evidence.spawn_observation_archive_id, evidence.spawn_probability_interval_id
    )
    total_decisions = len(HELDOUT_EPISODE_SEEDS) * EPISODE_DECISION_COUNT
    payload = {
        "schema": "acfqp.standard_2048_multiseed_partial_world_model_campaign.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "source_observation_evidence": evidence_document,
        "statistical_preregistration": preregistration,
        "episodes": episodes,
        "episode_count": len(episodes),
        "total_receding_decision_count": total_decisions,
        "final_partial_world_model": final_model,
        "partial_model_ground_support_row_count": total_rows,
        "partial_model_support_outcome_count": total_support,
        "matched_direct_total_ground_row_count": total_direct_rows,
        "matched_direct_total_ground_outcome_count": total_direct_outcomes,
        "sample_tax_telemetry": {
            "offline_source_rank_observation_count": SOURCE_SAMPLE_COUNT,
            "online_target_transition_observation_count": total_decisions,
            "partial_model_support_row_count": total_rows,
            "partial_model_support_outcome_count": total_support,
            "matched_direct_ground_row_count": total_direct_rows,
            "matched_direct_ground_outcome_count": total_direct_outcomes,
            "scalar_crossing_claimed": False,
        },
        "standard_4x4_swipe_spawn_semantics_executed": True,
        "multiple_heldout_seeds_executed": True,
        "longer_receding_rollout_executed": True,
        "persistent_world_model_reused_across_episodes": True,
        "spawn_rank_law_observation_derived_partial": True,
        "spawn_position_law_known_structural": True,
        "source_target_identity_separated": True,
        "certificate_failure_triggered_ground_recovery": True,
        "ground_support_rows_materialized_only_after_failed_proof": True,
        "all_selected_actions_match_cold_direct": True,
        "exact_target_values_inside_robust_envelopes": True,
        "multi_step_planning_completed_in_partial_abstract_model": True,
        "formal_exact_iid_claimed": False,
        "unknown_support_learning_claimed": False,
        "observation_derived_coordinate_invention_claimed": False,
        "full_standard_2048_game_completed": False,
        "real_game_ui_adapter_present": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(DOMAINS["campaign"], payload)}


_CAMPAIGN_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048MultiseedPartialWorldModelCampaignV1:
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
            or content_id(
                DOMAINS["campaign"],
                {key: value for key, value in document.items() if key != "campaign_id"},
            )
            != self.campaign_id
        ):
            _fail("campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("campaign root is not an object")
        return document


def run_standard_2048_multiseed_partial_world_model_campaign_v1(
) -> Standard2048MultiseedPartialWorldModelCampaignV1:
    document = _campaign_document()
    return Standard2048MultiseedPartialWorldModelCampaignV1(
        _CAMPAIGN_ISSUER, canonical_json_bytes(document), document["campaign_id"]
    )


def verify_standard_2048_multiseed_partial_world_model_campaign_v1(
    campaign: Standard2048MultiseedPartialWorldModelCampaignV1,
) -> Standard2048MultiseedPartialWorldModelCampaignV1:
    if type(campaign) is not Standard2048MultiseedPartialWorldModelCampaignV1:
        _fail("campaign verifier rejects foreign values")
    campaign.__post_init__()
    expected = _campaign_document()
    if campaign.canonical_bytes != canonical_json_bytes(expected):
        _fail("campaign differs from exact semantic replay")
    return campaign


__all__ = (
    "ConstructionK7Standard2048MultiseedPartialWorldModelV1Error",
    "DOMAINS",
    "EPISODE_DECISION_COUNT",
    "HELDOUT_EPISODE_SEEDS",
    "PLANNING_HORIZON",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_ROOT_BOARD",
    "SCHEMA_VERSION",
    "Standard2048MultiseedPartialWorldModelCampaignV1",
    "Standard2048PartialOutcomeV1",
    "Standard2048PartialRowV1",
    "run_standard_2048_multiseed_partial_world_model_campaign_v1",
    "verify_standard_2048_multiseed_partial_world_model_campaign_v1",
)
