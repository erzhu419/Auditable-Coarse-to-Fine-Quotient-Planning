"""Fresh-board receding control with observation-derived spawn support.

Raw source and validation transitions select a spawn-support program from a
finite meta-grammar and bound position, rank, and unknown-support masses.  A
persistent D4 partial world model is then grown only on failed H=3 proofs while
two fresh boards execute four decisions each.  Exact dynamics are isolated to
the target transition tape and matched evaluation control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, Mapping, NoReturn

from acfqp.construction_k7_standard_2048_spawn_support_observation_v2 import (
    SELECTED_SUPPORT_RULE,
    SOURCE_RECORDS_PER_CARDINALITY,
    SOURCE_SEED,
    UNKNOWN_SUPPORT_MASS_UPPER,
    VALIDATION_RECORDS_PER_CARDINALITY,
    VALIDATION_SEED,
    Standard2048SpawnSupportEvidenceV2,
    build_standard_2048_spawn_support_evidence_v2,
    support_ordinals_from_proposal_v2,
    verify_standard_2048_spawn_support_evidence_v2,
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
    swipe_board_v1,
    transform_action_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_CAMPAIGN_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_EPISODE_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_AUDIT_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_MATCHED_DIRECT_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_MODEL_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_ROW_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PREREGISTRATION_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_ROBUST_PLAN_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.156"
PROFILE_KEY = "construction_k7_standard_2048_fresh_board_support_world_model_v2"
PLANNING_HORIZON = 3
EPISODE_DECISION_COUNT = 4
HELDOUT_EPISODE_SEEDS = (
    "standard-2048-fresh-board-a-20260812-v2",
    "standard-2048-fresh-board-b-20260812-v2",
)

DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PREREGISTRATION_V2_DOMAIN,
    "row": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_ROW_V2_DOMAIN,
    "model": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_MODEL_V2_DOMAIN,
    "audit": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_AUDIT_V2_DOMAIN,
    "plan": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_ROBUST_PLAN_V2_DOMAIN,
    "direct": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_MATCHED_DIRECT_V2_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_EPISODE_V2_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_CAMPAIGN_V2_DOMAIN,
}
if len(DOMAINS) != len(set(DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("support partial-dynamics domains must be unique")
if not set(DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("support partial-dynamics domains are not registered")

REGISTERED_FRESH_BOARDS = (
    boards_from_rows_v1((
        (1, 3, 2, 4),
        (2, 4, 3, 5),
        (3, 5, 4, 6),
        (1, 1, 2, 2),
    )),
    boards_from_rows_v1((
        (2, 1, 2, 3),
        (3, 2, 3, 4),
        (4, 3, 4, 5),
        (1, 1, 2, 2),
    )),
)
LEGACY_V1_ROOT_BOARD = boards_from_rows_v1((
        (1, 2, 3, 4),
        (2, 3, 4, 5),
        (3, 4, 5, 6),
        (1, 1, 2, 2),
    ))
if any(board == LEGACY_V1_ROOT_BOARD for board in REGISTERED_FRESH_BOARDS):  # pragma: no cover
    raise RuntimeError("fresh boards must not reuse the V1 root")


class ConstructionK7Standard2048FreshBoardSupportWorldModelV2Error(ValueError):
    """A support identity, partial row, proof, or control changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048FreshBoardSupportWorldModelV2Error(message)


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
            raise ConstructionK7Standard2048FreshBoardSupportWorldModelV2Error(
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
        raise ConstructionK7Standard2048FreshBoardSupportWorldModelV2Error(
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
class Standard2048SupportPartialOutcomeV2:
    spawn_rank: int
    sorted_empty_ordinal: int
    position_probability_lower: Fraction
    position_probability_upper: Fraction
    next_state: Swipe2048State
    merge_score: int
    represented_support_outcome_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "position_probability_lower", Fraction(self.position_probability_lower)
        )
        object.__setattr__(
            self, "position_probability_upper", Fraction(self.position_probability_upper)
        )
        if (
            self.spawn_rank not in (1, 2)
            or type(self.sorted_empty_ordinal) is not int
            or self.sorted_empty_ordinal < 0
            or not 0 <= self.position_probability_lower
            <= self.position_probability_upper
            <= 1
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
            "sorted_empty_ordinal": self.sorted_empty_ordinal,
            "position_probability_lower": _fdoc(self.position_probability_lower),
            "position_probability_upper": _fdoc(self.position_probability_upper),
            "next_state": _state_document(self.next_state),
            "merge_score": self.merge_score,
            "represented_support_outcome_count": self.represented_support_outcome_count,
        }


@dataclass(frozen=True, slots=True)
class Standard2048SupportPartialRowV2:
    state: Swipe2048State
    action: Swipe2048Action
    outcomes: tuple[Standard2048SupportPartialOutcomeV2, ...]
    support_outcome_count: int
    partial_dynamics_interval_id: str
    support_proposal_id: str
    unknown_support_mass_upper: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.state) is not Swipe2048State
            or canonicalize_state_v1(self.state)[0] != self.state
            or type(self.action) is not Swipe2048Action
            or self.action not in legal_actions_v1(self.state.board)
            or type(self.outcomes) is not tuple
            or not self.outcomes
            or any(type(row) is not Standard2048SupportPartialOutcomeV2 for row in self.outcomes)
            or type(self.support_outcome_count) is not int
            or self.support_outcome_count <= 0
            or type(self.partial_dynamics_interval_id) is not str
            or len(self.partial_dynamics_interval_id) != 64
            or type(self.support_proposal_id) is not str
            or len(self.support_proposal_id) != 64
        ):
            _fail("partial row changed")
        object.__setattr__(
            self, "unknown_support_mass_upper", Fraction(self.unknown_support_mass_upper)
        )
        if not 0 <= self.unknown_support_mass_upper < 1:
            _fail("unknown support mass changed")
        for rank in (1, 2):
            rank_rows = tuple(row for row in self.outcomes if row.spawn_rank == rank)
            if not (
                sum((row.position_probability_lower for row in rank_rows), Fraction())
                <= 1
                <= sum((row.position_probability_upper for row in rank_rows), Fraction())
            ):
                _fail("position probability box does not intersect the simplex")
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
            "schema": "acfqp.standard_2048_support_partial_spawn_row.v2",
            "schema_version": SCHEMA_VERSION,
            "state": _state_document(self.state),
            "action": self.action.value,
            "partial_dynamics_interval_id": self.partial_dynamics_interval_id,
            "support_proposal_id": self.support_proposal_id,
            "unknown_support_mass_upper": _fdoc(self.unknown_support_mass_upper),
            "outcomes": [row.to_document() for row in self.outcomes],
            "support_outcome_count": self.support_outcome_count,
            "support_and_position_law_observation_derived": True,
            "spawn_rank_probability_point_value_absent": True,
            "materialized_only_after_failed_proof": True,
        }

    @property
    def row_id(self) -> str:
        return content_id(DOMAINS["row"], self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "partial_row_id": self.row_id}


def _materialize_partial_row(
    key: tuple[tuple[int, ...], str, str],
    interval_id: str,
    support_proposal_id: str,
    position_bounds: Mapping[int, tuple[tuple[Fraction, Fraction], ...]],
) -> Standard2048SupportPartialRowV2:
    """Execute the learned support program without reading exact transition rows."""

    board, status_value, action_value = key
    state = Swipe2048State(board, Swipe2048Status(status_value))
    action = Swipe2048Action(action_value)
    moved, merge_score, changed = swipe_board_v1(state.board, action)
    if not changed:
        _fail("legal action did not change the board")
    empty_cells = tuple(index for index, rank in enumerate(moved) if rank == 0)
    ordinals = support_ordinals_from_proposal_v2(
        support_proposal_id=support_proposal_id,
        selected_support_rule=SELECTED_SUPPORT_RULE,
        empty_count=len(empty_cells),
    )
    if ordinals != tuple(range(len(empty_cells))):
        _fail("selected support program output changed")
    bounds = position_bounds.get(len(empty_cells))
    if bounds is None or len(bounds) != len(empty_cells):
        _fail("position interval cardinality changed")
    grouped: dict[tuple[int, int, tuple[int, ...], str, int, Fraction, Fraction], int] = {}
    for ordinal in ordinals:
        for rank in (1, 2):
            spawned = list(moved)
            spawned[empty_cells[ordinal]] = rank
            representative, _ = canonicalize_state_v1(
                state_from_board_v1(tuple(spawned))
            )
            lower, upper = bounds[ordinal]
            group_key = (
                rank,
                ordinal,
                representative.board,
                representative.status.value,
                merge_score,
                lower,
                upper,
            )
            grouped[group_key] = grouped.get(group_key, 0) + 1
    outcomes = tuple(
        Standard2048SupportPartialOutcomeV2(
            rank,
            ordinal,
            lower,
            upper,
            Swipe2048State(next_board, Swipe2048Status(next_status)),
            merge_score,
            count,
        )
        for (
            rank, ordinal, next_board, next_status, merge_score, lower, upper
        ), count in sorted(grouped.items())
    )
    return Standard2048SupportPartialRowV2(
        state,
        action,
        outcomes,
        2 * len(ordinals),
        interval_id,
        support_proposal_id,
        UNKNOWN_SUPPORT_MASS_UPPER,
    )


def _model_document(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
) -> dict[str, Any]:
    row_documents = [rows[key].to_document() for key in sorted(rows)]
    payload = {
        "schema": "acfqp.standard_2048_support_partial_d4_world_model.v2",
        "schema_version": SCHEMA_VERSION,
        "semantics": "STANDARD_4X4_SWIPE_THEN_OBSERVATION_DERIVED_PARTIAL_SPAWN_V2",
        "abstraction": "D4_QUOTIENT_WITH_SUPPORT_POSITION_RANK_UNKNOWN_INTERVALS_V2",
        "query_neutral": True,
        "support_source_archive_id": source_archive_id,
        "support_validation_archive_id": validation_archive_id,
        "support_proposal_id": support_proposal_id,
        "partial_dynamics_interval_id": interval_id,
        "support_position_rank_observation_derived": True,
        "unknown_support_mass_bounded": True,
        "unknown_support_score_upper_uses_finite_mass_horizon_cap": True,
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


def _box_expectation_extreme(
    values: tuple[Fraction, ...],
    lower_bounds: tuple[Fraction, ...],
    upper_bounds: tuple[Fraction, ...],
    *,
    maximize: bool,
) -> Fraction:
    """Optimize one linear expectation over a box-constrained probability simplex."""

    if (
        not values
        or len(values) != len(lower_bounds)
        or len(values) != len(upper_bounds)
        or any(not 0 <= lower <= upper <= 1 for lower, upper in zip(lower_bounds, upper_bounds, strict=True))
    ):
        _fail("position probability box changed")
    probabilities = list(lower_bounds)
    remaining = Fraction(1) - sum(probabilities, Fraction())
    if remaining < 0 or sum(upper_bounds, Fraction()) < 1:
        _fail("position probability box misses the simplex")
    order = sorted(
        range(len(values)), key=lambda index: values[index], reverse=maximize
    )
    for index in order:
        addition = min(remaining, upper_bounds[index] - probabilities[index])
        probabilities[index] += addition
        remaining -= addition
        if remaining == 0:
            break
    if remaining:
        _fail("position probability optimization did not close")
    return sum(
        (probability * value for probability, value in zip(probabilities, values, strict=True)),
        Fraction(),
    )


def _unknown_spawn_score_upper(
    state: Swipe2048State, *, merge_score: int, remaining: int
) -> Fraction:
    """Bound score after one unmodelled rank-1/rank-2 spawn location."""

    if type(merge_score) is not int or merge_score < 0 or remaining < 1:
        _fail("unknown-support score-cap input changed")
    future_steps = remaining - 1
    post_spawn_mass_upper = sum((1 << rank) for rank in state.board if rank) + 4
    return Fraction(
        merge_score
        + future_steps * post_spawn_mass_upper
        + 2 * future_steps * (future_steps - 1)
    )


def _missing_frontier(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
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
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
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
                rank_outcomes = tuple(
                    outcome for outcome in row.outcomes if outcome.spawn_rank == rank
                )
                lower_values: list[Fraction] = []
                upper_values: list[Fraction] = []
                loss_values: list[Fraction] = []
                for outcome in rank_outcomes:
                    child = solve(
                        outcome.next_state.board,
                        outcome.next_state.status.value,
                        remaining - 1,
                    )
                    lower_values.append(outcome.merge_score + child.score_lower)
                    upper_values.append(outcome.merge_score + child.score_upper)
                    loss_values.append(child.loss_upper)
                lower_bounds = tuple(
                    outcome.position_probability_lower for outcome in rank_outcomes
                )
                upper_bounds = tuple(
                    outcome.position_probability_upper for outcome in rank_outcomes
                )
                by_rank[rank] = (
                    _box_expectation_extreme(
                        tuple(lower_values), lower_bounds, upper_bounds, maximize=False
                    ),
                    _box_expectation_extreme(
                        tuple(upper_values), lower_bounds, upper_bounds, maximize=True
                    ),
                    _box_expectation_extreme(
                        tuple(loss_values), lower_bounds, upper_bounds, maximize=True
                    ),
                )
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
            known_upper = max(upper_endpoints)
            unknown_score_upper = _unknown_spawn_score_upper(
                representative,
                merge_score=row.outcomes[0].merge_score,
                remaining=remaining,
            )
            score_upper = known_upper + row.unknown_support_mass_upper * max(
                Fraction(), unknown_score_upper - known_upper
            )
            candidate = _RobustValueV1(
                (1 - row.unknown_support_mass_upper) * min(lower_endpoints),
                score_upper,
                min(
                    Fraction(1),
                    row.unknown_support_mass_upper
                    + (1 - row.unknown_support_mass_upper) * max(loss_endpoints),
                ),
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
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    root: Swipe2048State,
    horizon: int,
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> dict[str, Any]:
    model = _model_document(
        rows,
        source_archive_id,
        validation_archive_id,
        support_proposal_id,
        interval_id,
    )
    missing = _missing_frontier(rows, root, horizon)
    payload: dict[str, Any] = {
        "schema": "acfqp.standard_2048_support_partial_model_audit.v2",
        "schema_version": SCHEMA_VERSION,
        "partial_world_model_id": model["partial_world_model_id"],
        "partial_dynamics_interval_id": interval_id,
        "support_proposal_id": support_proposal_id,
        "root_state": _state_document(root),
        "horizon": horizon,
        "objective": "MAX_SUPPORT_POSITION_RANK_ROBUST_SCORE_THEN_MIN_LOSS_V2",
        "status": "FAILED_PROOF_FRONTIER" if missing else "CERTIFIED_PARTIAL_DYNAMICS_ROBUST",
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
            "schema": "acfqp.standard_2048_support_interval_robust_plan.v2",
            "schema_version": SCHEMA_VERSION,
            "partial_world_model_id": model["partial_world_model_id"],
            "partial_dynamics_interval_id": interval_id,
            "support_proposal_id": support_proposal_id,
            "root_state": _state_document(root),
            "horizon": horizon,
            "objective": "MAX_SUPPORT_POSITION_RANK_ROBUST_SCORE_THEN_MIN_LOSS_V2",
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
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    root: Swipe2048State,
    horizon: int,
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
    position_bounds: Mapping[int, tuple[tuple[Fraction, Fraction], ...]],
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
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
            rank_two_lower,
            rank_two_upper,
        )
        if failed["status"] == "CERTIFIED_PARTIAL_DYNAMICS_ROBUST":
            return transactions, failed, added_rows, added_support
        frontier = tuple(
            _row_key(
                _state_from_document(item["state"]),
                Swipe2048Action(item["action"]),
            )
            for item in failed["missing_frontier"]
        )
        predecessor = _model_document(
            rows,
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
        )[
            "partial_world_model_id"
        ]
        recovered: list[Standard2048SupportPartialRowV2] = []
        for key in frontier:
            if key not in rows:
                row = _materialize_partial_row(
                    key, interval_id, support_proposal_id, position_bounds
                )
                rows[key] = row
                recovered.append(row)
                added_rows += 1
                added_support += row.support_outcome_count
        successor = _model_document(
            rows,
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
        )[
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
                "exact_spawn_or_position_probability_accessed_by_recovery": False,
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
        "schema": "acfqp.standard_2048_support_matched_direct.v2",
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


def _direct_plan_forced_action(
    root: Swipe2048State,
    horizon: int,
    forced_action: Swipe2048Action,
) -> dict[str, Any]:
    """Evaluate one registered root action with the same exact continuation."""

    if (
        type(root) is not Swipe2048State
        or type(horizon) is not int
        or horizon <= 0
        or type(forced_action) is not Swipe2048Action
        or forced_action not in legal_actions_v1(root.board)
    ):
        _fail("forced direct evaluation input changed")

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _ExactValueV1:
        state = Swipe2048State(board, Swipe2048Status(status_value))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            return _ExactValueV1(Fraction(), Fraction(), None)
        if state.status is Swipe2048Status.LOST:
            return _ExactValueV1(Fraction(), Fraction(1), None)
        best: _ExactValueV1 | None = None
        for action in legal_actions_v1(state.board):
            score = Fraction()
            loss = Fraction()
            for outcome in step_v1(state, action):
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

    score = Fraction()
    loss = Fraction()
    for outcome in step_v1(root, forced_action):
        child = solve(
            outcome.next_state.board,
            outcome.next_state.status.value,
            horizon - 1,
        )
        score += outcome.probability * (outcome.merge_score + child.expected_score)
        loss += outcome.probability * child.loss_probability
    return {
        "forced_action": forced_action.value,
        "expected_merge_score": _fdoc(score),
        "loss_probability_within_horizon": _fdoc(loss),
        "evaluation_lane_only": True,
    }


def _preregistration_document(
    evidence: Standard2048SpawnSupportEvidenceV2,
) -> dict[str, Any]:
    evidence_document = evidence.to_document()
    payload = {
        "schema": "acfqp.standard_2048_fresh_board_support_preregistration.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "environment_semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_SPAWN_V1",
        "registered_fresh_root_states": [
            _state_document(state_from_board_v1(board))
            for board in REGISTERED_FRESH_BOARDS
        ],
        "planning_horizon": PLANNING_HORIZON,
        "episode_decision_count": EPISODE_DECISION_COUNT,
        "heldout_episode_seeds": list(HELDOUT_EPISODE_SEEDS),
        "support_source_seed": SOURCE_SEED,
        "support_validation_seed": VALIDATION_SEED,
        "support_source_record_count": 16 * SOURCE_RECORDS_PER_CARDINALITY,
        "support_validation_record_count": 16 * VALIDATION_RECORDS_PER_CARDINALITY,
        "support_source_archive_id": evidence.source_archive_id,
        "support_validation_archive_id": evidence.validation_archive_id,
        "support_proposal_id": evidence.support_proposal_id,
        "partial_dynamics_interval_id": evidence.partial_dynamics_interval_id,
        "goal_rank": GOAL_RANK,
        "source_and_validation_archives_frozen_before_target_preregistration": True,
        "source_and_target_identities_disjoint": (
            SOURCE_SEED not in HELDOUT_EPISODE_SEEDS
            and VALIDATION_SEED not in HELDOUT_EPISODE_SEEDS
            and len(set(HELDOUT_EPISODE_SEEDS)) == len(HELDOUT_EPISODE_SEEDS)
        ),
        "fresh_roots_not_equal_to_v1_registered_root": all(
            board != LEGACY_V1_ROOT_BOARD for board in REGISTERED_FRESH_BOARDS
        ),
        "episode_seeds_and_matched_controls_frozen_before_model_construction": True,
        "observation_derived_dynamics_components": [
            "SPAWN_CELL_SUPPORT_PROGRAM",
            "SPAWN_POSITION_INTERVALS",
            "SPAWN_RANK_INTERVAL",
            "UNKNOWN_SUPPORT_MASS_BOUND",
        ],
        "known_structural_mechanics": ["WHOLE_BOARD_SWIPE", "D4_TRANSPORT"],
        "support_validation_passed_before_target_execution": evidence_document[
            "proposal"
        ]["heldout_support_validation_passed"],
    }
    return {
        **payload,
        "support_preregistration_id": content_id(DOMAINS["preregistration"], payload),
    }


def _run_episode(
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    *,
    episode_index: int,
    initial_board: tuple[int, ...],
    seed: str,
    preregistration_id: str,
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
    position_bounds: Mapping[int, tuple[tuple[Fraction, Fraction], ...]],
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> tuple[dict[str, Any], int, int, int, int]:
    initial_state = state_from_board_v1(initial_board)
    state = initial_state
    initial_model_id = _model_document(
        rows,
        source_archive_id,
        validation_archive_id,
        support_proposal_id,
        interval_id,
    )[
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
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
            rank_two_lower,
            rank_two_upper,
        )
        transactions, certified, added_rows, added_support = _recover_to_certificate(
            rows,
            state,
            PLANNING_HORIZON,
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
            position_bounds,
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
    final_model_id = _model_document(
        rows,
        source_archive_id,
        validation_archive_id,
        support_proposal_id,
        interval_id,
    )[
        "partial_world_model_id"
    ]
    payload = {
        "schema": "acfqp.standard_2048_fresh_board_receding_episode.v2",
        "schema_version": SCHEMA_VERSION,
        "support_preregistration_id": preregistration_id,
        "episode_index": episode_index,
        "heldout_episode_seed": seed,
        "initial_state": _state_document(initial_state),
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
    evidence = build_standard_2048_spawn_support_evidence_v2()
    verify_standard_2048_spawn_support_evidence_v2(evidence)
    evidence_document = evidence.to_document()
    interval = evidence_document["interval"]
    rank_two_lower = Fraction(interval["rank_two_probability_lower"])
    rank_two_upper = Fraction(interval["rank_two_probability_upper"])
    position_bounds = {
        row["post_swipe_empty_cardinality"]: tuple(
            (
                Fraction(category["probability_lower"]),
                Fraction(category["probability_upper"]),
            )
            for category in row["categories"]
        )
        for row in interval["position_intervals"]
    }
    preregistration = _preregistration_document(evidence)
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2] = {}
    episodes: list[dict[str, Any]] = []
    total_rows = 0
    total_support = 0
    total_direct_rows = 0
    total_direct_outcomes = 0
    for episode_index, (initial_board, seed) in enumerate(
        zip(REGISTERED_FRESH_BOARDS, HELDOUT_EPISODE_SEEDS, strict=True)
    ):
        episode, added_rows, added_support, direct_rows, direct_outcomes = _run_episode(
            rows,
            episode_index=episode_index,
            initial_board=initial_board,
            seed=seed,
            preregistration_id=preregistration["support_preregistration_id"],
            source_archive_id=evidence.source_archive_id,
            validation_archive_id=evidence.validation_archive_id,
            support_proposal_id=evidence.support_proposal_id,
            interval_id=evidence.partial_dynamics_interval_id,
            position_bounds=position_bounds,
            rank_two_lower=rank_two_lower,
            rank_two_upper=rank_two_upper,
        )
        episodes.append(episode)
        total_rows += added_rows
        total_support += added_support
        total_direct_rows += direct_rows
        total_direct_outcomes += direct_outcomes
    final_model = _model_document(
        rows,
        evidence.source_archive_id,
        evidence.validation_archive_id,
        evidence.support_proposal_id,
        evidence.partial_dynamics_interval_id,
    )
    total_decisions = len(HELDOUT_EPISODE_SEEDS) * EPISODE_DECISION_COUNT
    payload = {
        "schema": "acfqp.standard_2048_fresh_board_support_world_model_campaign.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "spawn_support_observation_evidence": evidence_document,
        "support_preregistration": preregistration,
        "episodes": episodes,
        "episode_count": len(episodes),
        "total_receding_decision_count": total_decisions,
        "final_partial_world_model": final_model,
        "partial_model_ground_support_row_count": total_rows,
        "partial_model_support_outcome_count": total_support,
        "matched_direct_total_ground_row_count": total_direct_rows,
        "matched_direct_total_ground_outcome_count": total_direct_outcomes,
        "sample_tax_telemetry": {
            "offline_source_transition_observation_count": (
                16 * SOURCE_RECORDS_PER_CARDINALITY
            ),
            "offline_validation_transition_observation_count": (
                16 * VALIDATION_RECORDS_PER_CARDINALITY
            ),
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
        "spawn_support_program_observation_derived": True,
        "spawn_position_law_observation_derived_partial": True,
        "spawn_rank_law_observation_derived_partial": True,
        "unknown_support_mass_bounded_from_observations": True,
        "unknown_support_score_upper_uses_finite_mass_horizon_cap": True,
        "fresh_non_v1_boards_executed": True,
        "source_target_identity_separated": True,
        "certificate_failure_triggered_ground_recovery": True,
        "ground_support_rows_materialized_only_after_failed_proof": True,
        "all_selected_actions_match_cold_direct": True,
        "exact_target_values_inside_robust_envelopes": True,
        "multi_step_planning_completed_in_partial_abstract_model": True,
        "formal_exact_iid_claimed": False,
        "unknown_support_complete_learning_claimed": False,
        "open_ended_support_invention_claimed": False,
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


_CAMPAIGN_ISSUER_V2 = object()


@dataclass(frozen=True, slots=True)
class Standard2048FreshBoardSupportWorldModelCampaignV2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _CAMPAIGN_ISSUER_V2 or type(self.canonical_bytes) is not bytes:
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


def run_standard_2048_fresh_board_support_world_model_campaign_v2(
) -> Standard2048FreshBoardSupportWorldModelCampaignV2:
    document = _campaign_document()
    return Standard2048FreshBoardSupportWorldModelCampaignV2(
        _CAMPAIGN_ISSUER_V2, canonical_json_bytes(document), document["campaign_id"]
    )


def verify_standard_2048_fresh_board_support_world_model_campaign_v2(
    campaign: Standard2048FreshBoardSupportWorldModelCampaignV2,
) -> Standard2048FreshBoardSupportWorldModelCampaignV2:
    if type(campaign) is not Standard2048FreshBoardSupportWorldModelCampaignV2:
        _fail("campaign verifier rejects foreign values")
    campaign.__post_init__()
    expected = _campaign_document()
    if campaign.canonical_bytes != canonical_json_bytes(expected):
        _fail("campaign differs from exact semantic replay")
    return campaign


__all__ = (
    "ConstructionK7Standard2048FreshBoardSupportWorldModelV2Error",
    "DOMAINS",
    "EPISODE_DECISION_COUNT",
    "HELDOUT_EPISODE_SEEDS",
    "PLANNING_HORIZON",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_FRESH_BOARDS",
    "SCHEMA_VERSION",
    "Standard2048FreshBoardSupportWorldModelCampaignV2",
    "Standard2048SupportPartialOutcomeV2",
    "Standard2048SupportPartialRowV2",
    "run_standard_2048_fresh_board_support_world_model_campaign_v2",
    "verify_standard_2048_fresh_board_support_world_model_campaign_v2",
)
