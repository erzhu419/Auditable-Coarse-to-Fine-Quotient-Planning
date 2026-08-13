"""Generic exact H-step planner for a structural-expression spawn program."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Any, Callable, NoReturn

from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as swipe_v14
from acfqp.domains.g2048 import D4_ELEMENTS, transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Outcome,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
)


SELECTED_SWIPE_PROGRAM = "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP"
OutcomeProvider = Callable[[Swipe2048State, Swipe2048Action], tuple[Swipe2048Outcome, ...]]


class ConstructionK7Standard2048ExpressionPlannerV1Error(ValueError):
    """The expression AST, exact program, state, or Bellman recurrence changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionPlannerV1Error(message)


@lru_cache(maxsize=None)
def _canonical(board: tuple[int, ...]) -> tuple[int, ...]:
    candidates = []
    for transform in D4_ELEMENTS:
        result = [0] * 16
        for source, rank in enumerate(board):
            result[transform_cell(source, 4, transform)] = rank
        candidates.append(tuple(result))
    return min(candidates)


@lru_cache(maxsize=None)
def _swipe(board: tuple[int, ...], action: str) -> tuple[tuple[int, ...], int]:
    return swipe_v14.apply_observation_proposed_swipe_program_v14(
        board, action, candidate_key=SELECTED_SWIPE_PROGRAM
    )


@lru_cache(maxsize=None)
def _actions(board: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(
        action.value
        for action in ACTION_ORDER
        if _swipe(board, action.value)[0] != board
    )


@lru_cache(maxsize=None)
def _status(board: tuple[int, ...]) -> str:
    if max(board) >= GOAL_RANK:
        return Swipe2048Status.WON.value
    return Swipe2048Status.ACTIVE.value if _actions(board) else Swipe2048Status.LOST.value


def _adjacent_equal_nonzero(board: tuple[int, ...]) -> int:
    return sum(
        1
        for row in range(4)
        for column in range(4)
        for dr, dc in ((0, 1), (1, 0))
        if row + dr < 4
        and column + dc < 4
        and board[row * 4 + column]
        and board[row * 4 + column] == board[(row + dr) * 4 + column + dc]
    )


def evaluate_structural_expression_v1(
    expression_ast: dict[str, Any],
    *,
    pre_board: tuple[int, ...],
    action: str,
    post_swipe_board: tuple[int, ...],
    merge_score: int,
) -> int:
    """Evaluate one registered depth-one expression on an exact raw context."""

    if type(expression_ast) is not dict or type(pre_board) is not tuple or type(post_swipe_board) is not tuple:
        _fail("expression evaluation input changed")
    source_name = expression_ast.get("vector_source")
    board = (
        pre_board
        if source_name == "PRE_BOARD_RANKS"
        else post_swipe_board
        if source_name == "POST_SWIPE_BOARD_RANKS"
        else None
    )
    operator = expression_ast.get("operator")
    if operator == "COUNT_EQ" and board is not None and set(expression_ast) == {
        "operator", "vector_source", "constant"
    }:
        constant = expression_ast["constant"]
        if type(constant) is not int:
            _fail("COUNT_EQ constant changed")
        return board.count(constant)
    if board is not None and set(expression_ast) == {"operator", "vector_source"}:
        if operator == "MAX":
            return max(board)
        if operator == "SUM":
            return sum(board)
        if operator == "DISTINCT_NONZERO_COUNT":
            return len(set(board) - {0})
        if operator == "ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT":
            return _adjacent_equal_nonzero(board)
    if operator == "RAW_SCALAR" and set(expression_ast) == {"operator", "source"}:
        if expression_ast["source"] == "MERGE_SCORE":
            return merge_score
        if expression_ast["source"] == "ACTION_ORDINAL":
            return tuple(item.value for item in ACTION_ORDER).index(action)
    _fail("expression AST is outside the registered depth-one grammar")


@dataclass(frozen=True, slots=True)
class _Value:
    score: Fraction
    loss: Fraction
    action: str | None


def _better(candidate: _Value, current: _Value | None) -> bool:
    if current is None:
        return True
    if candidate.action is None or current.action is None:
        _fail("terminal value entered action comparison")
    order = tuple(action.value for action in ACTION_ORDER)
    return (candidate.score, -candidate.loss, -order.index(candidate.action)) > (
        current.score, -current.loss, -order.index(current.action)
    )


def _best(values: tuple[_Value, ...]) -> _Value:
    best = None
    for value in values:
        if _better(value, best):
            best = value
    if best is None or best.action is None:
        _fail("active root has no selected action")
    return best


def _rows(values: tuple[_Value, ...]) -> list[dict[str, Any]]:
    return [
        {
            "action": value.action,
            "expected_merge_score": value.score,
            "loss_probability_within_horizon": value.loss,
        }
        for value in values
    ]


class _ExpressionPlanner:
    def __init__(
        self, expression_ast: dict[str, Any], threshold: int,
        base: Fraction, override: Fraction,
    ) -> None:
        self.expression_ast = expression_ast
        self.threshold = threshold
        self.base = base
        self.override = override
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

    def action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        self.rows += 1
        post, merge = _swipe(board, action)
        value = evaluate_structural_expression_v1(
            self.expression_ast,
            pre_board=board,
            action=action,
            post_swipe_board=post,
            merge_score=merge,
        )
        p2 = self.override if value <= self.threshold else self.base
        empty = tuple(index for index, rank in enumerate(post) if rank == 0)
        if not empty:
            _fail("legal expression-model swipe has no spawn support")
        self.outcomes += 2 * len(empty)
        score = loss = Fraction()
        for cell in empty:
            for rank, mass in ((1, 1 - p2), (2, p2)):
                child = list(post)
                child[cell] = rank
                child_board = tuple(child)
                child_value = self.state_value(child_board, _status(child_board), remaining - 1)
                probability = mass / len(empty)
                score += probability * (merge + child_value.score)
                loss += probability * child_value.loss
        return _Value(score, loss, action)

    def state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        if remaining == 0 or status == "WON":
            result = _Value(Fraction(), Fraction(), None)
        elif status == "LOST":
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in _actions(board):
                candidate = self.action_value(board, action, remaining)
                if _better(candidate, best):
                    best = candidate
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State, horizon: int) -> tuple[_Value, ...]:
        return tuple(self.action_value(state.board, action, horizon) for action in _actions(state.board))


class _GroundPlanner:
    def __init__(self, provider: OutcomeProvider) -> None:
        self.provider = provider
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

    def action_value(
        self, state: Swipe2048State, action: Swipe2048Action, remaining: int
    ) -> _Value:
        self.rows += 1
        outcomes = self.provider(state, action)
        self.outcomes += len(outcomes)
        score = loss = Fraction()
        for outcome in outcomes:
            value = self.state_value(
                outcome.next_state.board, outcome.next_state.status.value, remaining - 1
            )
            score += outcome.probability * (outcome.merge_score + value.score)
            loss += outcome.probability * value.loss
        return _Value(score, loss, action.value)

    def state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or status == "WON":
            result = _Value(Fraction(), Fraction(), None)
        elif status == "LOST":
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in legal_actions_v1(state.board):
                candidate = self.action_value(state, action, remaining)
                if _better(candidate, best):
                    best = candidate
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State, horizon: int) -> tuple[_Value, ...]:
        return tuple(self.action_value(state, action, horizon) for action in legal_actions_v1(state.board))


def plan_expression_world_model_root_v1(
    state: Swipe2048State,
    *,
    expression_ast: dict[str, Any],
    threshold: int,
    base_probability: Fraction,
    override_probability: Fraction,
    horizon: int,
) -> dict[str, Any]:
    if type(state) is not Swipe2048State or type(threshold) is not int or type(horizon) is not int or horizon <= 0:
        _fail("expression planner public input changed")
    planner = _ExpressionPlanner(
        expression_ast, threshold, Fraction(base_probability), Fraction(override_probability)
    )
    values = planner.roots(state, horizon)
    selected = _best(values)
    return {
        "root_action_exact_values": _rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": selected.score,
        "selected_loss_probability_within_horizon": selected.loss,
        "factored_action_row_evaluation_count": planner.rows,
        "factored_support_outcome_evaluation_count": planner.outcomes,
        "subproof_cache_hit_count": planner.hits,
        "subproof_cache_miss_count": planner.misses,
        "target_transition_accessed": False,
    }


def evaluate_ground_root_v1(
    state: Swipe2048State, *, outcome_provider: OutcomeProvider, horizon: int
) -> dict[str, Any]:
    if type(state) is not Swipe2048State or not callable(outcome_provider) or type(horizon) is not int or horizon <= 0:
        _fail("ground evaluator public input changed")
    planner = _GroundPlanner(outcome_provider)
    values = planner.roots(state, horizon)
    selected = _best(values)
    return {
        "root_action_exact_values": _rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": selected.score,
        "selected_loss_probability_within_horizon": selected.loss,
        "ground_state_action_row_count": planner.rows,
        "ground_outcome_count": planner.outcomes,
        "subproof_cache_hit_count": planner.hits,
        "subproof_cache_miss_count": planner.misses,
        "lane": "STANDALONE_EVALUATION_ONLY",
        "route_or_certificate_authority": False,
    }


__all__ = (
    "ConstructionK7Standard2048ExpressionPlannerV1Error",
    "evaluate_ground_root_v1",
    "evaluate_structural_expression_v1",
    "plan_expression_world_model_root_v1",
)
