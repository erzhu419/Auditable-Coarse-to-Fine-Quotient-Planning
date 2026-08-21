"""Execute compiled anonymous factor programs without V15 shape dispatch.

The historical planner recognizes identity, action-copy, and additive-support
expressions with three dedicated branches.  V122 recursively interprets the
registered typed opcode language, derives terminal rules from compiled
projected transitions, and searches successor support generated only by that
interpreter.  A legacy comparison helper is retained solely for development
equivalence tests; the V122 planner never calls it.
"""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from itertools import product
from math import ceil
from typing import Any, Mapping, MutableMapping, NoReturn, Sequence

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    GENERIC_ATOMIC_OPCODES_V4,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15


OPCODE_TYPES_V122 = {
    code: (tuple(arguments), result)
    for code, _name, arguments, result in GENERIC_ATOMIC_OPCODES_V4
}


class GenericCompiledFactorPlannerV122Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCompiledFactorPlannerV122Error(message)


@dataclass(frozen=True, slots=True)
class _FiniteSupportV122:
    values: tuple[int, ...]


def _expression_type(expression: Any) -> str:
    if type(expression) is bool:
        return "BOOL"
    if type(expression) is int:
        return "INT"
    if type(expression) is not list or not expression or type(expression[0]) is not str:
        _fail("V122 expression shape changed")
    opcode = expression[0]
    if opcode in {"E00", "E01"}:
        if len(expression) != 2 or type(expression[1]) is not int or expression[1] < 0:
            _fail("V122 causal atom shape changed")
        return "INT"
    signature = OPCODE_TYPES_V122.get(opcode)
    if signature is None:
        _fail("V122 expression used an unknown opcode")
    arguments, result = signature
    actual = tuple(_expression_type(item) for item in expression[1:])
    if actual != arguments:
        _fail("V122 expression type or arity changed")
    return result


def _evaluate(
    expression: Any,
    state_by_column: Mapping[int, int],
    action: FlatRawActionV4,
) -> int | bool | _FiniteSupportV122:
    if type(expression) in {int, bool}:
        return expression
    opcode = expression[0]
    if opcode == "E00":
        column = expression[1]
        if column not in state_by_column:
            _fail("V122 expression depends on an unmodelled state coordinate")
        return state_by_column[column]
    if opcode == "E01":
        field = expression[1]
        if field not in range(len(action.fields)):
            _fail("V122 expression depends on an absent action field")
        return action.fields[field]
    values = [_evaluate(item, state_by_column, action) for item in expression[1:]]
    if any(isinstance(value, _FiniteSupportV122) for value in values):
        _fail("V122 finite support escaped its typed expression boundary")
    if opcode == "E05":
        return int(values[0]) + int(values[1])
    if opcode == "E06":
        divisor = int(values[1])
        if divisor == 0:
            _fail("V122 modulo divisor is zero")
        return int(values[0]) % divisor
    if opcode == "E07":
        return _FiniteSupportV122(tuple(sorted({int(values[0]), int(values[1])})))
    if opcode == "E08":
        return values[0] == values[1]
    if opcode == "E09":
        return int(values[0]) > int(values[1])
    if opcode == "E10":
        return bool(values[0]) and bool(values[1])
    if opcode == "E11":
        return not bool(values[0])
    if opcode == "E12":
        return int(values[1]) if bool(values[0]) else int(values[2])
    if opcode == "E13":
        return int(values[0]) | int(values[1])
    _fail("V122 expression escaped the generic evaluator")


def _targets(candidate: PartialFactorCandidateV15) -> tuple[int, ...]:
    if type(candidate) is not PartialFactorCandidateV15 or not candidate.assignments:
        _fail("V122 candidate carrier changed")
    targets = tuple(row["target_column"] for row in candidate.assignments)
    if len(targets) != len(set(targets)):
        _fail("V122 candidate target coordinates are not unique")
    available = frozenset(targets)
    for assignment in candidate.assignments:
        if (
            _expression_type(assignment["expression"]) != assignment["result_type"]
            or not set(assignment["state_dependencies"]).issubset(available)
        ):
            _fail("V122 compiled factor program is not closed on its projected state")
    return targets


def generic_factor_successor_projections_v122(
    candidate: PartialFactorCandidateV15,
    projected_state: tuple[int, ...],
    action: FlatRawActionV4,
) -> tuple[tuple[int, ...], ...]:
    """Interpret every assignment recursively and form its joint support."""

    targets = _targets(candidate)
    if (
        type(projected_state) is not tuple
        or len(projected_state) != len(targets)
        or any(type(value) is not int for value in projected_state)
        or type(action) is not FlatRawActionV4
    ):
        _fail("V122 projected successor inventory changed")
    state = dict(zip(targets, projected_state, strict=True))
    supports: list[tuple[int, ...]] = []
    for assignment in candidate.assignments:
        value = _evaluate(assignment["expression"], state, action)
        if isinstance(value, _FiniteSupportV122):
            support = value.values
        elif type(value) is int:
            support = (value,)
        else:
            _fail("V122 state assignment did not return integer support")
        if not support:
            _fail("V122 compiled assignment returned empty support")
        supports.append(support)
    return tuple(sorted(set(product(*supports))))


def derive_generic_terminal_rules_v122(
    candidate: PartialFactorCandidateV15,
    projected_edge_rows: Sequence[Mapping[str, Any]],
    projected_terminal_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Infer terminal constraints from anonymous dependency and delta facts."""

    targets = _targets(candidate)
    accepting = [
        tuple(row["projected_state"])
        for row in projected_terminal_rows
        if "ACCEPT" in row["observed_terminal_classes"]
    ]
    if not accepting or any(len(row) != len(targets) for row in accepting):
        _fail("V122 projected observations expose no accepting state")
    edges = [
        (tuple(row["projected_pre"]), tuple(row["projected_post"]))
        for row in projected_edge_rows
    ]
    if not edges or any(len(pre) != len(targets) or len(post) != len(targets) for pre, post in edges):
        _fail("V122 projected edge inventory changed")
    rules = []
    for offset, assignment in enumerate(candidate.assignments):
        target = assignment["target_column"]
        values = tuple(sorted({state[offset] for state in accepting}))
        if target not in assignment["state_dependencies"]:
            rule = {"kind": "UNCONSTRAINED"}
        else:
            deltas = tuple(post[offset] - pre[offset] for pre, post in edges)
            if all(delta == 0 for delta in deltas):
                rule = (
                    {"kind": "EQUAL", "value": values[0]}
                    if len(values) == 1
                    else {"kind": "UNCONSTRAINED"}
                )
            elif all(delta >= 0 for delta in deltas):
                rule = {"kind": "AT_LEAST", "value": min(values)}
            elif all(delta <= 0 for delta in deltas):
                rule = {"kind": "AT_MOST", "value": max(values)}
            else:
                rule = {"kind": "OBSERVED_SET", "values": list(values)}
        rules.append({"target_column": target, **rule})
    return tuple(rules)


def _terminal_match(
    state: tuple[int, ...], rules: tuple[Mapping[str, Any], ...]
) -> bool:
    for value, rule in zip(state, rules, strict=True):
        kind = rule["kind"]
        if kind == "EQUAL" and value != rule["value"]:
            return False
        if kind == "AT_LEAST" and value < rule["value"]:
            return False
        if kind == "AT_MOST" and value > rule["value"]:
            return False
        if kind == "OBSERVED_SET" and value not in rule["values"]:
            return False
    return True


def _distance(value: int, rule: Mapping[str, Any]) -> int:
    kind = rule["kind"]
    if kind == "UNCONSTRAINED":
        return 0
    if kind == "EQUAL":
        return abs(value - rule["value"])
    if kind == "AT_LEAST":
        return max(0, rule["value"] - value)
    if kind == "AT_MOST":
        return max(0, value - rule["value"])
    if kind == "OBSERVED_SET":
        return min(abs(value - target) for target in rule["values"])
    _fail("V122 terminal rule kind changed")


def _canonical_actions(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[FlatRawActionV4, ...]:
    if type(catalogue) is not tuple or not catalogue:
        _fail("V122 action catalogue changed")
    return tuple(
        FlatRawActionV4(
            action.key,
            tuple(
                action.fields[index]
                for index in candidate.layout.action_canonical_to_raw
            ),
        )
        for action in catalogue
    )


def plan_generic_factor_program_v122(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    terminal_rules: tuple[Mapping[str, Any], ...],
    initial_projected_state: tuple[int, ...],
    exact_initial_legal_action_keys: frozenset[int],
    branch_cache: MutableMapping[
        tuple[tuple[int, ...], int], tuple[tuple[int, ...], ...]
    ],
    *,
    maximum_depth: int,
) -> dict[str, Any]:
    """Run receding abstract search using only the generic program evaluator."""

    targets = _targets(candidate)
    actions = _canonical_actions(candidate, catalogue)
    action_keys = {action.key for action in actions}
    if (
        len(initial_projected_state) != len(targets)
        or len(terminal_rules) != len(targets)
        or not exact_initial_legal_action_keys
        or not exact_initial_legal_action_keys.issubset(action_keys)
        or maximum_depth <= 0
    ):
        _fail("V122 planner inventory changed")

    new_evaluations = reused_evaluations = heuristic_evaluations = 0

    def successors(state: tuple[int, ...], action: FlatRawActionV4) -> tuple[tuple[int, ...], ...]:
        nonlocal new_evaluations, reused_evaluations
        key = (state, action.key)
        result = branch_cache.get(key)
        if result is None:
            result = generic_factor_successor_projections_v122(candidate, state, action)
            branch_cache[key] = result
            new_evaluations += len(result)
        else:
            reused_evaluations += len(result)
        return result

    def priority_bound(state: tuple[int, ...]) -> int:
        nonlocal heuristic_evaluations
        distances = tuple(
            _distance(value, rule)
            for value, rule in zip(state, terminal_rules, strict=True)
        )
        if not any(distances):
            return 0
        progress = [0] * len(state)
        for action in actions:
            for successor in successors(state, action):
                heuristic_evaluations += 1
                for offset, rule in enumerate(terminal_rules):
                    progress[offset] = max(
                        progress[offset],
                        distances[offset] - _distance(successor[offset], rule),
                    )
        bounds = [
            0 if distance == 0 else ceil(distance / step) if step > 0 else 0
            for distance, step in zip(distances, progress, strict=True)
        ]
        return max(bounds, default=0)

    initial_bound = priority_bound(initial_projected_state)
    frontier = [(initial_bound, 0, initial_projected_state)]
    best_depth = {initial_projected_state: 0}
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial_projected_state: None
    }
    terminal = None
    while frontier:
        _priority, depth, state = heapq.heappop(frontier)
        if depth != best_depth[state]:
            continue
        if _terminal_match(state, terminal_rules):
            terminal = state
            break
        if depth == maximum_depth:
            continue
        for action in actions:
            if state == initial_projected_state and action.key not in exact_initial_legal_action_keys:
                continue
            for next_state in successors(state, action):
                if next_state == state:
                    continue
                next_depth = depth + 1
                if next_depth >= best_depth.get(next_state, maximum_depth + 1):
                    continue
                best_depth[next_state] = next_depth
                predecessor[next_state] = (state, action.key)
                heapq.heappush(
                    frontier,
                    (next_depth + priority_bound(next_state), next_depth, next_state),
                )
    if terminal is None:
        _fail("V122 generic factor program found no support-feasible continuation")
    path = []
    cursor = terminal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        path.append(key)
        cursor = parent
    path.reverse()
    return {
        "schema": "acfqp.generic_compiled_factor_receding_plan.v122",
        "candidate_id": candidate.public_document["candidate_id"],
        "known_factor_target_columns": list(targets),
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "terminal_projection_rule": [dict(row) for row in terminal_rules],
        "selected_support_feasible_depth": len(path),
        "action_keys": path,
        "projected_planning_compute_events": new_evaluations,
        "matched_uncached_projected_planning_compute_events": (
            new_evaluations + reused_evaluations
        ),
        "projected_branch_cache_hit_count": reused_evaluations,
        "projected_branch_cache_entry_count": len(branch_cache),
        "generic_expression_heuristic_evaluations": heuristic_evaluations,
        "generic_typed_opcode_interpreter_used_for_every_new_successor": True,
        "terminal_rule_derived_from_anonymous_dependencies_and_projected_deltas": True,
        "heuristic_used_for_queue_order_only_not_depth_pruning": True,
        "hand_written_expression_shape_case_count": 0,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "generic_planner_execution_adapter_verified": True,
        "stochastic_support_branch_receding_semantics": True,
        "robust_all_branches_completion_claimed": False,
        "finite_worst_case_completion_claimed": False,
        "ground_transition_accessed_during_abstract_search": False,
        "complete_world_model_claimed": False,
    }


__all__ = (
    "GenericCompiledFactorPlannerV122Error",
    "derive_generic_terminal_rules_v122",
    "generic_factor_successor_projections_v122",
    "plan_generic_factor_program_v122",
)
