"""Compile a partial candidate and one residual proposal into abstract search.

This planner never discharges a safety obligation.  It performs multi-step
AND/OR search over only the coordinates represented by the compiled partial
program plus one action-conditioned, zero-excess residual proposal.  A caller
must still certify every selected ground state-action support and recover a
query-local exact distinction when that certificate fails.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import product
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15


class GenericPartialResidualAbstractPlannerV22Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPartialResidualAbstractPlannerV22Error(message)


def _residual_value(
    expression: Any,
    *,
    state_value: int,
    action: tuple[int, ...],
    field: int | None,
    constant: int | None,
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (state_value,)
    if expression == ["R01"] and field is not None:
        return (action[field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R03":
        left = _residual_value(
            expression[1],
            state_value=state_value,
            action=action,
            field=field,
            constant=constant,
        )
        right = _residual_value(
            expression[2],
            state_value=state_value,
            action=action,
            field=field,
            constant=constant,
        )
        if len(left) == len(right) == 1:
            return (left[0] + right[0],)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R04":
        left = _residual_value(
            expression[1],
            state_value=state_value,
            action=action,
            field=field,
            constant=constant,
        )
        right = _residual_value(
            expression[2],
            state_value=state_value,
            action=action,
            field=field,
            constant=constant,
        )
        if len(left) == len(right) == 1:
            return tuple(sorted({left[0], right[0]}))
    _fail("V22 residual expression escaped the finite grammar")


def _partial_support(
    assignment: Mapping[str, Any], current: int, action: tuple[int, ...]
) -> tuple[int, ...]:
    expression = assignment["expression"]
    if expression[0] == "E00":
        return (current,)
    if expression[0] == "E01":
        return (action[expression[1]],)
    if expression[0] == "E07":
        field = expression[2][2][1]
        return tuple(sorted({current, current + action[field]}))
    _fail("V22 partial expression escaped the finite grammar")


def _update_deltas(
    descriptor: Mapping[str, Any], actions: tuple[FlatRawActionV4, ...]
) -> tuple[int, ...]:
    if descriptor["kind"] == "PARTIAL":
        assignment = descriptor["assignment"]
        return tuple(
            sorted(
                {
                    value
                    for action in actions
                    for value in _partial_support(assignment, 0, action.fields)
                }
            )
        )
    residual = descriptor["candidate"]
    return tuple(
        sorted(
            {
                value
                for action in actions
                for value in _residual_value(
                    residual["normalized_expression"],
                    state_value=0,
                    action=action.fields,
                    field=residual["action_field_binding"],
                    constant=residual["anonymous_integer_constant_binding"],
                )
            }
        )
    )


def plan_partial_residual_abstract_program_v22(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    residual_candidate: Mapping[str, Any],
    *,
    maximum_depth: int,
    maximum_robust_state_depth_evaluations: int = 512,
    maximum_support_branch_evaluations: int = 100_000,
    support_feasible_beam_width: int = 32,
) -> dict[str, Any]:
    if (
        maximum_depth <= 0
        or maximum_robust_state_depth_evaluations <= 0
        or maximum_support_branch_evaluations <= 0
        or support_feasible_beam_width <= 0
    ):
        _fail("V22 maximum depth changed")
    if type(candidate) is not PartialFactorCandidateV15 or type(residual_candidate) is not dict:
        _fail("V22 candidate types changed")
    residual_target = residual_candidate.get("target_column")
    if (
        type(residual_target) is not int
        or residual_target
        not in candidate.public_document["unknown_residual_target_columns"]
        or type(residual_candidate.get("action_field_binding")) is not int
        or residual_candidate.get("predictive_support_excess") != 0
    ):
        _fail("V22 requires an actionable zero-excess residual proposal")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        observed_rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    if not aligned_rows or not aligned_catalogue:
        _fail("V22 requires aligned observations and actions")
    state_order = candidate.public_document["layout"]["state_canonical_to_raw"]
    canonical_initial = tuple(initial_raw_state[index] for index in state_order)
    descriptors = [
        {
            "target": assignment["target_column"],
            "kind": "PARTIAL",
            "assignment": assignment,
        }
        for assignment in candidate.assignments
    ]
    descriptors.append(
        {
            "target": residual_target,
            "kind": "RESIDUAL",
            "candidate": residual_candidate,
        }
    )
    descriptors.sort(key=lambda row: row["target"])
    targets = tuple(row["target"] for row in descriptors)
    initial = tuple(canonical_initial[target] for target in targets)
    accepting = tuple(row for row in aligned_rows if row.terminal_acceptance_after is True)
    if not accepting:
        _fail("V22 observations exposed no accepting state")
    terminal_rules = []
    for descriptor in descriptors:
        target = descriptor["target"]
        values = tuple(sorted({row.post[target] for row in accepting}))
        deltas = _update_deltas(descriptor, aligned_catalogue)
        if len(values) == 1 and deltas == (0,):
            rule = {"kind": "EQUAL", "value": values[0]}
        elif deltas and min(deltas) >= 0 and max(deltas) > 0:
            rule = {"kind": "AT_LEAST", "value": min(values)}
        elif deltas and max(deltas) <= 0 and min(deltas) < 0:
            rule = {"kind": "AT_MOST", "value": max(values)}
        else:
            rule = {"kind": "OBSERVED_SET", "values": list(values)}
        terminal_rules.append({"target_column": target, **rule})

    def terminal(state: tuple[int, ...]) -> bool:
        for value, rule in zip(state, terminal_rules, strict=True):
            if rule["kind"] == "EQUAL" and value != rule["value"]:
                return False
            if rule["kind"] == "AT_LEAST" and value < rule["value"]:
                return False
            if rule["kind"] == "AT_MOST" and value > rule["value"]:
                return False
            if rule["kind"] == "OBSERVED_SET" and value not in rule["values"]:
                return False
        return True

    def successors(
        state: tuple[int, ...], action: FlatRawActionV4
    ) -> tuple[tuple[int, ...], ...]:
        supports = []
        for offset, descriptor in enumerate(descriptors):
            if descriptor["kind"] == "PARTIAL":
                values = _partial_support(
                    descriptor["assignment"], state[offset], action.fields
                )
            else:
                residual = descriptor["candidate"]
                values = _residual_value(
                    residual["normalized_expression"],
                    state_value=state[offset],
                    action=action.fields,
                    field=residual["action_field_binding"],
                    constant=residual["anonymous_integer_constant_binding"],
                )
            supports.append(values)
        return tuple(sorted(set(product(*supports))))

    evaluations = 0
    robust_calls = 0
    robust_truncated = False
    visiting: set[tuple[tuple[int, ...], int]] = set()
    policy: dict[tuple[int, ...], int] = {}

    @lru_cache(maxsize=None)
    def robust(state: tuple[int, ...], depth: int) -> bool:
        nonlocal evaluations, robust_calls, robust_truncated
        robust_calls += 1
        if (
            robust_calls > maximum_robust_state_depth_evaluations
            or evaluations >= maximum_support_branch_evaluations
        ):
            robust_truncated = True
            return False
        if terminal(state):
            return True
        if depth == 0 or (state, depth) in visiting:
            return False
        visiting.add((state, depth))
        for action in aligned_catalogue:
            branch = successors(state, action)
            evaluations += len(branch)
            if evaluations > maximum_support_branch_evaluations:
                robust_truncated = True
                visiting.remove((state, depth))
                return False
            progressing = tuple(value for value in branch if value != state)
            if progressing and all(robust(value, depth - 1) for value in progressing):
                policy[state] = action.key
                visiting.remove((state, depth))
                return True
        visiting.remove((state, depth))
        return False

    closed = robust(initial, maximum_depth)
    support_path: list[int] = []
    if not closed:
        predecessor: dict[
            tuple[int, ...], tuple[tuple[int, ...], int] | None
        ] = {initial: None}
        goal = None
        frontier = (initial,)

        def terminal_distance(state: tuple[int, ...]) -> int:
            result = 0
            for value, rule in zip(state, terminal_rules, strict=True):
                if rule["kind"] == "EQUAL":
                    result += abs(value - rule["value"])
                elif rule["kind"] == "AT_LEAST":
                    result += max(0, rule["value"] - value)
                elif rule["kind"] == "AT_MOST":
                    result += max(0, value - rule["value"])
                else:
                    result += min(abs(value - item) for item in rule["values"])
            return result

        for _depth in range(maximum_depth):
            next_rows: dict[tuple[int, ...], tuple[tuple[int, ...], int]] = {}
            for state in frontier:
                for action in aligned_catalogue:
                    branch = successors(state, action)
                    evaluations += len(branch)
                    if evaluations > maximum_support_branch_evaluations:
                        _fail("V22 support-feasible search crossed its compute cap")
                    for successor in branch:
                        if successor == state or successor in predecessor:
                            continue
                        previous = next_rows.get(successor)
                        edge = (state, action.key)
                        if previous is None or edge < previous:
                            next_rows[successor] = edge
            ranked = sorted(next_rows, key=lambda row: (terminal_distance(row), row))
            frontier = tuple(ranked[:support_feasible_beam_width])
            for successor in frontier:
                predecessor[successor] = next_rows[successor]
                if terminal(successor):
                    goal = successor
                    break
            if goal is not None or not frontier:
                break
        if goal is None:
            _fail("V22 combined abstract program found no support-feasible continuation")
        cursor = goal
        reversed_actions = []
        while predecessor[cursor] is not None:
            parent, key = predecessor[cursor]
            reversed_actions.append(key)
            cursor = parent
        support_path = list(reversed(reversed_actions))
    first = policy.get(initial) if closed else support_path[0] if support_path else None
    if type(first) is not int:
        _fail("V22 combined abstract policy omitted its initial action")
    payload = {
        "schema": "acfqp.generic_partial_residual_abstract_plan.v22",
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "residual_candidate_id": residual_candidate["candidate_id"],
        "represented_target_columns": list(targets),
        "remaining_unknown_target_columns": sorted(
            set(candidate.public_document["unknown_residual_target_columns"])
            - {residual_target}
        ),
        "terminal_projection_rules": terminal_rules,
        "initial_action_key": first,
        "maximum_depth": maximum_depth,
        "maximum_robust_state_depth_evaluations": maximum_robust_state_depth_evaluations,
        "maximum_support_branch_evaluations": maximum_support_branch_evaluations,
        "support_feasible_beam_width": support_feasible_beam_width,
        "abstract_state_depth_cache_count": robust.cache_info().currsize,
        "abstract_support_branch_evaluations": evaluations,
        "support_feasible_action_keys": support_path,
        "robust_all_modeled_branches_closed": closed,
        "robust_search_resource_cap_reached": robust_truncated,
        "support_feasible_receding_plan_found": True,
        "ground_transition_accessed_during_abstract_search": False,
        "abstract_plan_used_as_safety_authority": False,
        "unrepresented_residual_targets_assumed_known": False,
        "complete_world_model_claimed": False,
    }
    return payload


__all__ = ("plan_partial_residual_abstract_program_v22",)
