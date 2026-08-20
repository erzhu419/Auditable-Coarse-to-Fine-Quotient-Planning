"""Compile partial factors, exact residual supports, and a terminal relation tree.

The status coordinate is no longer approximated by an unrelated arithmetic
support.  V29 evolves every other anonymous coordinate, then evaluates the V28
relation program to derive ACTIVE/ACCEPT/REJECT and its observed status token.
The multi-step plan remains proposal-only and cannot discharge a certificate.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import product
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import align_generic_occurrence_v5
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relational_terminal_program_v28 import (
    evaluate_relational_terminal_program_v28,
)


class GenericRelationalResidualAbstractPlannerV29Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericRelationalResidualAbstractPlannerV29Error(message)


def _residual_value(
    expression: Any,
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
        left = _residual_value(expression[1], state_value, action, field, constant)
        right = _residual_value(expression[2], state_value, action, field, constant)
        if len(left) == len(right) == 1:
            return (left[0] + right[0],)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R04":
        left = _residual_value(expression[1], state_value, action, field, constant)
        right = _residual_value(expression[2], state_value, action, field, constant)
        if len(left) == len(right) == 1:
            return tuple(sorted({left[0], right[0]}))
    _fail("V29 residual expression escaped the finite grammar")


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
    _fail("V29 partial expression escaped the finite grammar")


def plan_relational_residual_abstract_program_v29(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    batch_exact_residual_support: Mapping[str, Any],
    terminal_program: Mapping[str, Any],
    *,
    terminal_candidate_index: int = 0,
    maximum_depth: int,
    maximum_robust_state_depth_evaluations: int = 1_024,
    maximum_support_branch_evaluations: int = 1_000_000,
    support_feasible_beam_width: int = 32,
) -> dict[str, Any]:
    if (
        maximum_depth <= 0
        or maximum_robust_state_depth_evaluations <= 0
        or maximum_support_branch_evaluations <= 0
        or support_feasible_beam_width <= 0
    ):
        _fail("V29 planning cap changed")
    if type(candidate) is not PartialFactorCandidateV15:
        _fail("V29 partial candidate type changed")
    if (
        type(batch_exact_residual_support) is not dict
        or batch_exact_residual_support.get("schema")
        != "acfqp.generic_batch_exact_multi_residual_support.v27"
        or batch_exact_residual_support.get("future_unseen_support_authority_present")
        is not False
        or type(terminal_program) is not dict
        or terminal_program.get("schema")
        != "acfqp.generic_relational_terminal_program.v28"
        or terminal_program.get("future_unseen_terminal_authority_present") is not False
    ):
        _fail("V29 predecessor program changed")
    terminal_frontier = terminal_program.get("decision_tree_candidate_frontier")
    if (
        type(terminal_frontier) is not list
        or type(terminal_candidate_index) is not int
        or not 0 <= terminal_candidate_index < len(terminal_frontier)
        or type(terminal_frontier[terminal_candidate_index]) is not dict
    ):
        _fail("V29 terminal candidate frontier changed")
    selected_terminal = dict(terminal_program)
    selected_terminal["decision_tree"] = terminal_frontier[terminal_candidate_index].get(
        "decision_tree"
    )
    selected_terminal["decision_tree_node_count"] = terminal_frontier[
        terminal_candidate_index
    ].get("decision_tree_node_count")
    residual_candidates = batch_exact_residual_support.get(
        "joint_batch_exact_candidates"
    )
    if type(residual_candidates) is not list or not residual_candidates:
        _fail("V29 requires at least one batch-exact residual support")
    status_target = terminal_program.get("status_target_column")
    unknown = candidate.public_document["unknown_residual_target_columns"]
    if type(status_target) is not int or status_target not in unknown:
        _fail("V29 terminal target changed")
    residual_targets = [row.get("target_column") for row in residual_candidates]
    if (
        any(type(target) is not int for target in residual_targets)
        or residual_targets != sorted(set(residual_targets))
        or status_target in residual_targets
        or set(residual_targets) | {status_target} != set(unknown)
    ):
        _fail("V29 residual/terminal target partition changed")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        observed_rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    if not aligned_rows or not aligned_catalogue:
        _fail("V29 requires aligned observations and actions")
    state_order = candidate.public_document["layout"]["state_canonical_to_raw"]
    initial = tuple(initial_raw_state[index] for index in state_order)
    descriptors: dict[int, dict[str, Any]] = {
        assignment["target_column"]: {
            "kind": "PARTIAL",
            "assignment": assignment,
        }
        for assignment in candidate.assignments
    }
    for residual in residual_candidates:
        target = residual["target_column"]
        descriptors[target] = {"kind": "RESIDUAL", "candidate": residual}
    expected_targets = set(range(len(initial))) - {status_target}
    if set(descriptors) != expected_targets:
        _fail("V29 modeled coordinate coverage changed")

    def terminal_class(state: tuple[int, ...]) -> str:
        result = evaluate_relational_terminal_program_v28(selected_terminal, state)
        if result["status_token"] != state[status_target]:
            _fail("V29 terminal token/program join changed")
        value = result["terminal_class"]
        if value not in ("ACTIVE", "ACCEPT", "REJECT"):
            _fail("V29 terminal class changed")
        return value

    def successors(
        state: tuple[int, ...], action: FlatRawActionV4
    ) -> tuple[tuple[int, ...], ...]:
        ordered_targets = sorted(descriptors)
        supports = []
        for target in ordered_targets:
            descriptor = descriptors[target]
            if descriptor["kind"] == "PARTIAL":
                values = _partial_support(
                    descriptor["assignment"], state[target], action.fields
                )
            else:
                residual = descriptor["candidate"]
                values = _residual_value(
                    residual["normalized_expression"],
                    state[target],
                    action.fields,
                    residual["action_field_binding"],
                    residual["anonymous_integer_constant_binding"],
                )
            supports.append(values)
        result = set()
        for values in product(*supports):
            row = list(state)
            for target, value in zip(ordered_targets, values, strict=True):
                row[target] = value
            projected = tuple(row)
            inferred = evaluate_relational_terminal_program_v28(
                selected_terminal, projected
            )
            row[status_target] = inferred["status_token"]
            result.add(tuple(row))
        return tuple(sorted(result))

    accepting_states = tuple(
        row.post for row in aligned_rows if row.terminal_acceptance_after is True
    )
    if not accepting_states:
        _fail("V29 observations exposed no accepting state")

    evaluations = 0
    robust_calls = 0
    robust_truncated = False
    visiting: set[tuple[tuple[int, ...], int]] = set()
    policy: dict[tuple[int, ...], int] = {}

    @lru_cache(maxsize=None)
    def robust(state: tuple[int, ...], depth: int) -> bool:
        nonlocal evaluations, robust_calls, robust_truncated
        robust_calls += 1
        classification = terminal_class(state)
        if classification == "ACCEPT":
            return True
        if classification == "REJECT":
            return False
        if (
            depth == 0
            or (state, depth) in visiting
            or robust_calls > maximum_robust_state_depth_evaluations
            or evaluations >= maximum_support_branch_evaluations
        ):
            robust_truncated = (
                robust_calls > maximum_robust_state_depth_evaluations
                or evaluations >= maximum_support_branch_evaluations
            )
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
        predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
            initial: None
        }
        goal = None
        frontier = (initial,)

        def distance(state: tuple[int, ...]) -> int:
            return min(
                sum(abs(left - right) for left, right in zip(state, goal_state, strict=True))
                for goal_state in accepting_states
            )

        for _depth in range(maximum_depth):
            next_rows: dict[tuple[int, ...], tuple[tuple[int, ...], int]] = {}
            for state in frontier:
                if terminal_class(state) != "ACTIVE":
                    continue
                for action in aligned_catalogue:
                    branch = successors(state, action)
                    evaluations += len(branch)
                    if evaluations > maximum_support_branch_evaluations:
                        _fail("V29 support-feasible search crossed its compute cap")
                    for successor in branch:
                        if successor == state or successor in predecessor:
                            continue
                        edge = (state, action.key)
                        previous = next_rows.get(successor)
                        if previous is None or edge < previous:
                            next_rows[successor] = edge
            ranked = sorted(next_rows, key=lambda row: (distance(row), row))
            frontier = tuple(ranked[:support_feasible_beam_width])
            for successor in frontier:
                predecessor[successor] = next_rows[successor]
                if terminal_class(successor) == "ACCEPT":
                    goal = successor
                    break
            if goal is not None or not frontier:
                break
        if goal is None:
            _fail("V29 relational residual model found no support-feasible continuation")
        cursor = goal
        reversed_actions = []
        while predecessor[cursor] is not None:
            parent, key = predecessor[cursor]
            reversed_actions.append(key)
            cursor = parent
        support_path = list(reversed(reversed_actions))
    first = policy.get(initial) if closed else support_path[0] if support_path else None
    if type(first) is not int:
        _fail("V29 relational residual policy omitted its initial action")
    return {
        "schema": "acfqp.generic_relational_residual_abstract_plan.v29",
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "batch_exact_multi_residual_id": batch_exact_residual_support[
            "batch_exact_multi_residual_id"
        ],
        "terminal_program_id": terminal_program["terminal_program_id"],
        "selected_terminal_candidate_index": terminal_candidate_index,
        "selected_terminal_tree_sha256": terminal_frontier[terminal_candidate_index][
            "decision_tree_sha256"
        ],
        "residual_candidate_ids": [row["candidate_id"] for row in residual_candidates],
        "residual_target_columns": residual_targets,
        "relational_terminal_target_column": status_target,
        "represented_target_columns": sorted((*expected_targets, status_target)),
        "remaining_unknown_target_columns": [],
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
        "status_successor_derived_from_anonymous_relational_program": True,
        "all_observed_state_coordinates_represented": True,
        "ground_transition_accessed_during_abstract_search": False,
        "abstract_plan_used_as_safety_authority": False,
        "empirical_support_promoted_to_global_exact_dynamics": False,
        "complete_world_model_claimed": False,
    }


def plan_relational_residual_abstract_frontier_v29(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    batch_exact_residual_support: Mapping[str, Any],
    terminal_program: Mapping[str, Any],
    *,
    maximum_depth: int,
    maximum_terminal_program_candidates_to_try: int = 32,
    maximum_robust_state_depth_evaluations: int = 1_024,
    maximum_support_branch_evaluations: int = 1_000_000,
    support_feasible_beam_width: int = 32,
) -> dict[str, Any]:
    frontier = terminal_program.get("decision_tree_candidate_frontier")
    if (
        type(frontier) is not list
        or type(maximum_terminal_program_candidates_to_try) is not int
        or not 1 <= maximum_terminal_program_candidates_to_try <= 128
        or not frontier
    ):
        _fail("V29 terminal frontier search cap changed")
    failures = []
    for index in range(min(maximum_terminal_program_candidates_to_try, len(frontier))):
        try:
            result = plan_relational_residual_abstract_program_v29(
                candidate,
                observed_rows,
                catalogue,
                initial_raw_state,
                batch_exact_residual_support,
                terminal_program,
                terminal_candidate_index=index,
                maximum_depth=maximum_depth,
                maximum_robust_state_depth_evaluations=(
                    maximum_robust_state_depth_evaluations
                ),
                maximum_support_branch_evaluations=(
                    maximum_support_branch_evaluations
                ),
                support_feasible_beam_width=support_feasible_beam_width,
            )
        except GenericRelationalResidualAbstractPlannerV29Error as error:
            failures.append(
                {
                    "candidate_index": index,
                    "decision_tree_sha256": frontier[index].get(
                        "decision_tree_sha256"
                    ),
                    "planner_failure": str(error),
                }
            )
            continue
        return {
            **result,
            "terminal_candidate_attempt_count": index + 1,
            "rejected_terminal_candidate_attempts": failures,
            "terminal_relation_and_transition_program_jointly_selected": True,
            "joint_selection_used_ground_transition_or_certificate_authority": False,
        }
    _fail("V29 terminal candidate frontier found no abstract continuation")


__all__ = (
    "plan_relational_residual_abstract_frontier_v29",
    "plan_relational_residual_abstract_program_v29",
)
