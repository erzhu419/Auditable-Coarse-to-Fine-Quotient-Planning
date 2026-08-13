"""Target-agnostic local expression synthesis for registered 2048 frontiers."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from types import MappingProxyType
from typing import Any, Iterable, Mapping, NoReturn

from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as pre
from acfqp import construction_k7_standard_2048_expression_planner_v1 as expression
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    canonicalize_state_v1,
    legal_actions_v1,
    state_from_board_v1,
    swipe_board_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


BASE_RANK_TWO_PROBABILITY = Fraction(1, 10)
_VECTOR_SOURCES = ("PRE_BOARD_RANKS", "POST_SWIPE_BOARD_RANKS")
_UNARY_REDUCERS = (
    "MAX",
    "SUM",
    "DISTINCT_NONZERO_COUNT",
    "ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT",
)
_PROGRAM_DIRECTIONS = ("LE_OVERRIDE", "GT_OVERRIDE")


class ConstructionK7Standard2048AdaptiveExpressionRuntimeV35Error(ValueError):
    """A raw context, generated program, label, or local proof changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveExpressionRuntimeV35Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _validate_board(board: tuple[int, ...]) -> tuple[int, ...]:
    if (
        type(board) is not tuple
        or len(board) != 16
        or any(type(rank) is not int or rank < 0 for rank in board)
    ):
        _fail("raw 2048 board changed")
    return board


@dataclass(frozen=True, slots=True)
class RawExpressionContextV35:
    pre_board: tuple[int, ...]
    action: str
    post_swipe_board: tuple[int, ...]
    merge_score: int
    context_sha256: str

    def __post_init__(self) -> None:
        _validate_board(self.pre_board)
        _validate_board(self.post_swipe_board)
        if self.action not in tuple(action.value for action in ACTION_ORDER):
            _fail("raw expression action changed")
        if type(self.merge_score) is not int or self.merge_score < 0:
            _fail("raw expression merge score changed")
        expected_post, expected_merge, moved = swipe_board_v1(
            self.pre_board, Swipe2048Action(self.action)
        )
        if (
            not moved
            or expected_post != self.post_swipe_board
            or expected_merge != self.merge_score
        ):
            _fail("raw expression context does not replay standard swipe")
        if self.context_sha256 != hashlib.sha256(
            canonical_json_bytes(self.to_payload())
        ).hexdigest():
            _fail("raw expression context digest changed")

    def to_payload(self) -> dict[str, Any]:
        return {
            "pre_state_board_ranks": list(self.pre_board),
            "action": self.action,
            "post_swipe_board_ranks": list(self.post_swipe_board),
            "merge_score": self.merge_score,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self.to_payload(), "structural_context_sha256": self.context_sha256}


def raw_expression_context_v35(
    board: tuple[int, ...], action: str
) -> RawExpressionContextV35:
    _validate_board(board)
    if action not in tuple(item.value for item in ACTION_ORDER):
        _fail("raw expression action is outside the standard order")
    post, merge, moved = swipe_board_v1(board, Swipe2048Action(action))
    if not moved:
        _fail("raw expression context requires a legal swipe")
    payload = {
        "pre_state_board_ranks": list(board),
        "action": action,
        "post_swipe_board_ranks": list(post),
        "merge_score": merge,
    }
    return RawExpressionContextV35(
        board,
        action,
        post,
        merge,
        hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    )


def enumerate_raw_frontier_contexts_v35(
    state: Swipe2048State, *, horizon: int
) -> tuple[RawExpressionContextV35, ...]:
    """Enumerate the exact support-only contexts visited by an H-step planner."""

    if type(state) is not Swipe2048State or type(horizon) is not int or horizon <= 0:
        _fail("raw frontier input changed")
    contexts: dict[str, RawExpressionContextV35] = {}
    expanded: set[tuple[tuple[int, ...], str, int]] = set()

    def visit(current: Swipe2048State, remaining: int, *, root: bool) -> None:
        if remaining == 0 or current.status is not Swipe2048Status.ACTIVE:
            return
        if root:
            working = current
        else:
            working = canonicalize_state_v1(current)[0]
        state_key = (working.board, working.status.value, remaining)
        if state_key in expanded:
            return
        expanded.add(state_key)
        for action in legal_actions_v1(working.board):
            context = raw_expression_context_v35(working.board, action.value)
            contexts.setdefault(context.context_sha256, context)
            empty_cells = tuple(
                index
                for index, rank in enumerate(context.post_swipe_board)
                if rank == 0
            )
            if not empty_cells:
                _fail("legal raw frontier swipe has no spawn support")
            for cell in empty_cells:
                for rank in (1, 2):
                    child = list(context.post_swipe_board)
                    child[cell] = rank
                    visit(state_from_board_v1(tuple(child)), remaining - 1, root=False)

    visit(state, horizon, root=True)
    return tuple(contexts[key] for key in sorted(contexts))


def _expression_specs(
    contexts: tuple[RawExpressionContextV35, ...],
) -> tuple[dict[str, Any], ...]:
    constants = sorted(
        {
            rank
            for context in contexts
            for board in (context.pre_board, context.post_swipe_board)
            for rank in board
        }
    )
    result: list[dict[str, Any]] = []
    for source in _VECTOR_SOURCES:
        result.extend(
            {
                "operator": "COUNT_EQ",
                "vector_source": source,
                "constant": constant,
            }
            for constant in constants
        )
        result.extend(
            {"operator": operator, "vector_source": source}
            for operator in _UNARY_REDUCERS
        )
    result.extend(
        {"operator": "RAW_SCALAR", "source": source}
        for source in ("MERGE_SCORE", "ACTION_ORDINAL")
    )
    result.sort(key=lambda row: canonical_json_bytes(row))
    return tuple(result)


def _expression_value(
    ast: dict[str, Any], context: RawExpressionContextV35
) -> int:
    return expression.evaluate_structural_expression_v1(
        ast,
        pre_board=context.pre_board,
        action=context.action,
        post_swipe_board=context.post_swipe_board,
        merge_score=context.merge_score,
    )


@dataclass(frozen=True, slots=True)
class ExpressionProgramCandidateV35:
    expression_ast: Mapping[str, Any]
    threshold: int
    override_probability: Fraction
    direction: str
    candidate_id: str

    def __post_init__(self) -> None:
        if type(self.expression_ast) is not MappingProxyType:
            _fail("expression candidate AST is not immutable")
        if (
            type(self.threshold) is not int
            or type(self.override_probability) is not Fraction
            or self.direction not in _PROGRAM_DIRECTIONS
            or type(self.candidate_id) is not str
            or len(self.candidate_id) != 64
        ):
            _fail("expression candidate fields changed")
        payload = _candidate_payload(
            dict(self.expression_ast),
            self.threshold,
            self.override_probability,
            self.direction,
        )
        if content_id(pre.FUTURE_DOMAINS["candidate"], payload) != self.candidate_id:
            _fail("expression candidate identity changed")

    def predict(self, context: RawExpressionContextV35) -> Fraction:
        value = _expression_value(dict(self.expression_ast), context)
        use_override = (
            value <= self.threshold
            if self.direction == "LE_OVERRIDE"
            else value > self.threshold
        )
        return (
            self.override_probability
            if use_override
            else BASE_RANK_TWO_PROBABILITY
        )

    def to_document(self) -> dict[str, Any]:
        payload = _candidate_payload(
            dict(self.expression_ast),
            self.threshold,
            self.override_probability,
            self.direction,
        )
        return {**payload, "expression_candidate_id": self.candidate_id}


def _candidate_payload(
    ast: dict[str, Any], threshold: int, override: Fraction, direction: str
) -> dict[str, Any]:
    return {
        "schema": "acfqp.standard_2048_adaptive_expression_candidate.v35",
        "schema_version": pre.SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "expression_ast": ast,
        "threshold": threshold,
        "direction": direction,
        "base_rank_two_probability": _fdoc(BASE_RANK_TWO_PROBABILITY),
        "override_rank_two_probability": _fdoc(override),
        "expression_and_threshold_generated_from_frozen_raw_contexts": True,
        "override_probability_generated_from_acquired_label": True,
        "target_formula_used_to_generate_candidate": False,
    }


def _candidate(
    ast: dict[str, Any], threshold: int, override: Fraction, direction: str
) -> ExpressionProgramCandidateV35:
    payload = _candidate_payload(ast, threshold, override, direction)
    return ExpressionProgramCandidateV35(
        MappingProxyType(dict(ast)),
        threshold,
        override,
        direction,
        content_id(pre.FUTURE_DOMAINS["candidate"], payload),
    )


def generate_consistent_expression_candidates_v35(
    *,
    archived_contexts: Iterable[RawExpressionContextV35],
    labels: Mapping[str, Fraction],
) -> tuple[tuple[ExpressionProgramCandidateV35, ...], dict[str, int]]:
    """Generate the exact depth-one version space from raw rows and labels."""

    by_id: dict[str, RawExpressionContextV35] = {}
    for context in archived_contexts:
        if type(context) is not RawExpressionContextV35:
            _fail("expression archive contains a foreign context")
        context.__post_init__()
        by_id[context.context_sha256] = context
    contexts = tuple(by_id[key] for key in sorted(by_id))
    if not contexts:
        _fail("expression archive is empty")
    normalized_labels: dict[str, Fraction] = {}
    for context_id, value in labels.items():
        if context_id not in by_id:
            _fail("expression label does not bind an archived context")
        exact = Fraction(value)
        if exact < 0 or exact > 1:
            _fail("expression probability label is outside [0,1]")
        normalized_labels[context_id] = exact
    overrides = tuple(
        sorted(set(normalized_labels.values()) - {BASE_RANK_TWO_PROBABILITY})
    )
    consistency_checks = 0
    value_evaluations = 0
    candidates: dict[str, ExpressionProgramCandidateV35] = {}
    for ast in _expression_specs(contexts):
        values = tuple(_expression_value(ast, context) for context in contexts)
        value_evaluations += len(contexts)
        for threshold in sorted(set(values)):
            for override in overrides:
                for direction in _PROGRAM_DIRECTIONS:
                    candidate = _candidate(ast, threshold, override, direction)
                    predictions = tuple(candidate.predict(context) for context in contexts)
                    value_evaluations += len(contexts)
                    if len(set(predictions)) == 1:
                        continue
                    consistent = True
                    for context_id, observed in normalized_labels.items():
                        consistency_checks += 1
                        if candidate.predict(by_id[context_id]) != observed:
                            consistent = False
                            break
                    if consistent:
                        candidates[candidate.candidate_id] = candidate
    ordered = tuple(candidates[key] for key in sorted(candidates))
    return ordered, {
        "model.structural_context_rows_frozen": len(contexts),
        "model.structural_expression_value_evaluations": value_evaluations,
        "model.expression_candidates_materialized": len(ordered),
        "model.candidate_label_consistency_checks": consistency_checks,
    }


def filter_expression_candidates_v35(
    *,
    candidates: tuple[ExpressionProgramCandidateV35, ...],
    contexts_by_id: Mapping[str, RawExpressionContextV35],
    labels: Mapping[str, Fraction],
) -> tuple[tuple[ExpressionProgramCandidateV35, ...], int]:
    """Monotonically filter the first-frontier candidate universe."""

    normalized_contexts: dict[str, RawExpressionContextV35] = {}
    for context_id, context in contexts_by_id.items():
        if (
            type(context_id) is not str
            or type(context) is not RawExpressionContextV35
            or context.context_sha256 != context_id
        ):
            _fail("candidate-filter context binding changed")
        context.__post_init__()
        normalized_contexts[context_id] = context
    normalized_labels: dict[str, Fraction] = {}
    for context_id, value in labels.items():
        if context_id not in normalized_contexts:
            _fail("candidate-filter label lacks its raw context")
        normalized_labels[context_id] = Fraction(value)
    checks = 0
    retained = []
    for candidate in candidates:
        if type(candidate) is not ExpressionProgramCandidateV35:
            _fail("candidate-filter version space contains a foreign value")
        candidate.__post_init__()
        keep = True
        for context_id, observed in normalized_labels.items():
            checks += 1
            if candidate.predict(normalized_contexts[context_id]) != observed:
                keep = False
                break
        if keep:
            retained.append(candidate)
    retained.sort(key=lambda item: item.candidate_id)
    return tuple(retained), checks


@dataclass(frozen=True, slots=True)
class LocalExpressionDecisionV35:
    status: str
    candidate_count: int
    selected_candidate_id: str | None
    next_query_context_sha256: str | None
    local_prediction_classes: int
    partition_evaluation_count: int


def local_certificate_or_query_v35(
    *,
    frontier_contexts: Iterable[RawExpressionContextV35],
    candidates: tuple[ExpressionProgramCandidateV35, ...],
    labels: Mapping[str, Fraction],
) -> LocalExpressionDecisionV35:
    """Certify local agreement or select one unresolved failed-frontier row."""

    frontier_by_id: dict[str, RawExpressionContextV35] = {}
    for context in frontier_contexts:
        if type(context) is not RawExpressionContextV35:
            _fail("local frontier contains a foreign context")
        context.__post_init__()
        frontier_by_id[context.context_sha256] = context
    frontier = tuple(frontier_by_id[key] for key in sorted(frontier_by_id))
    if not frontier:
        _fail("local frontier is empty")
    observed = {key: Fraction(value) for key, value in labels.items()}
    nonbase_observed = any(
        value != BASE_RANK_TWO_PROBABILITY for value in observed.values()
    )
    if not nonbase_observed:
        choices = tuple(
            context.context_sha256
            for context in frontier
            if context.context_sha256 not in observed
        )
        return LocalExpressionDecisionV35(
            "QUERY_REQUIRED_NO_NONBASE_LABEL",
            len(candidates),
            None,
            min(choices) if choices else None,
            0,
            0,
        )
    if not candidates:
        return LocalExpressionDecisionV35(
            "COLD_GROUND_FALLBACK_EMPTY_VERSION_SPACE", 0, None, None, 0, 0
        )
    for candidate in candidates:
        if type(candidate) is not ExpressionProgramCandidateV35:
            _fail("local version space contains a foreign candidate")
        candidate.__post_init__()
    prediction_rows = tuple(
        tuple(candidate.predict(context) for candidate in candidates)
        for context in frontier
    )
    partition_evaluations = len(frontier) * len(candidates)
    differing = tuple(
        (context, predictions)
        for context, predictions in zip(frontier, prediction_rows, strict=True)
        if len(set(predictions)) > 1
    )
    if not differing:
        selected = min(candidates, key=lambda item: item.candidate_id)
        prediction_classes = len(set(prediction_rows))
        return LocalExpressionDecisionV35(
            "LOCALLY_CERTIFIED_ALL_SURVIVORS_AGREE",
            len(candidates),
            selected.candidate_id,
            None,
            prediction_classes,
            partition_evaluations,
        )
    choices = []
    for context, predictions in differing:
        if context.context_sha256 in observed:
            continue
        buckets: dict[Fraction, int] = {}
        for prediction in predictions:
            buckets[prediction] = buckets.get(prediction, 0) + 1
        choices.append(
            (max(buckets.values()), len(buckets), context.context_sha256)
        )
    if not choices:
        _fail("candidate disagreement remains only on already labelled contexts")
    _, _, context_id = min(choices, key=lambda row: (row[0], -row[1], row[2]))
    return LocalExpressionDecisionV35(
        "QUERY_REQUIRED_LOCAL_DISAGREEMENT",
        len(candidates),
        None,
        context_id,
        len({tuple(row) for row in prediction_rows}),
        partition_evaluations,
    )


__all__ = (
    "BASE_RANK_TWO_PROBABILITY",
    "ConstructionK7Standard2048AdaptiveExpressionRuntimeV35Error",
    "ExpressionProgramCandidateV35",
    "LocalExpressionDecisionV35",
    "RawExpressionContextV35",
    "enumerate_raw_frontier_contexts_v35",
    "filter_expression_candidates_v35",
    "generate_consistent_expression_candidates_v35",
    "local_certificate_or_query_v35",
    "raw_expression_context_v35",
)
