"""Receding abstract planning over contextual-ordinal residual version spaces."""

from __future__ import annotations

from functools import lru_cache
from itertools import product
import math
from typing import Any, Mapping, NoReturn

from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_contextual_ordinal_model_compiler_v54 import (
    verify_contextual_ordinal_model_v54,
)
from acfqp.generic_contextual_ordinal_residual_v54 import _value
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relational_terminal_program_v28 import (
    evaluate_relational_terminal_program_v28,
)


class GenericContextualOrdinalPlannerV54Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericContextualOrdinalPlannerV54Error(message)


def plan_contextual_ordinal_model_v54(
    model: Mapping[str, Any],
    target_candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    *,
    maximum_depth: int,
    maximum_robust_state_depth_evaluations: int = 4096,
    maximum_support_branch_evaluations: int = 1_000_000,
    support_feasible_beam_width: int = 64,
) -> dict[str, Any]:
    verified = verify_contextual_ordinal_model_v54(model)
    if (
        type(target_candidate) is not PartialFactorCandidateV15
        or type(catalogue) is not tuple
        or not catalogue
        or type(initial_raw_state) is not tuple
        or type(maximum_depth) is not int
        or maximum_depth <= 0
        or maximum_robust_state_depth_evaluations <= 0
        or maximum_support_branch_evaluations <= 0
        or support_feasible_beam_width <= 0
    ):
        _fail("V54 planning inventory changed")
    target = target_candidate.public_document
    source_layout = verified["source_layout"]
    target_layout = target.get("layout")
    if (
        type(target_layout) is not dict
        or target.get("state_width") != verified["state_width"]
        or target.get("action_field_width") != verified["action_field_width"]
        or target.get("unknown_residual_target_columns")
        != verified["unknown_residual_target_columns"]
        or target.get("compiled_factor_assignments")
        != verified["known_partial_factor_assignments"]
        or target_layout.get("state_structural_colors")
        != source_layout.get("state_structural_colors")
        or target_layout.get("action_structural_colors")
        != source_layout.get("action_structural_colors")
    ):
        _fail("V54 target occurrence is not structurally compatible with the model")
    state_order = target_layout.get("state_canonical_to_raw")
    action_order = target_layout.get("action_canonical_to_raw")
    if (
        type(state_order) is not list
        or sorted(state_order) != list(range(len(initial_raw_state)))
        or type(action_order) is not list
    ):
        _fail("V54 target layout projection changed")
    initial = tuple(initial_raw_state[index] for index in state_order)
    actions = tuple(
        FlatRawActionV4(
            action.key,
            tuple(action.fields[index] for index in action_order),
        )
        for action in catalogue
    )
    if len({action.key for action in actions}) != len(actions):
        _fail("V54 target action catalogue changed")
    supports = {
        0: tuple(
            tuple(sorted({action.fields[field] for action in actions}))
            for field in range(len(action_order))
        )
    }
    if any(not support for support in supports[0]):
        _fail("V54 target contextual support became empty")
    partial = {
        row["target_column"]: row
        for row in verified["known_partial_factor_assignments"]
    }
    residual = {
        row["target_column"]: row["batch_exact_candidate_frontier"]
        for row in verified["residual_version_spaces"]
    }
    status_target = verified["status_target_column"]
    terminal_frontier = verified["mdl_minimal_terminal_candidate_frontier"]

    def terminal_predictions(state: tuple[int, ...]) -> tuple[tuple[str, int], ...]:
        values = set()
        for row in terminal_frontier:
            result = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": row["decision_tree"],
                },
                state,
            )
            classification = result.get("terminal_class")
            token = result.get("status_token")
            if classification not in ("ACTIVE", "ACCEPT", "REJECT") or type(token) is not int:
                _fail("V54 terminal frontier prediction changed")
            values.add((classification, token))
        return tuple(sorted(values))

    branch_evaluations = 0
    maximum_branch_width = 0

    def successors(
        state: tuple[int, ...], action: FlatRawActionV4
    ) -> tuple[tuple[int, ...], ...]:
        nonlocal maximum_branch_width
        support_rows = []
        targets = sorted((*partial, *residual))
        for column in targets:
            if column in partial:
                values = v42._partial_support(  # noqa: SLF001
                    partial[column], state, action.fields
                )
            else:
                values_set = set()
                for expression in residual[column]:
                    values_set.update(
                        _value(
                            expression["normalized_expression"],
                            state,
                            action.fields,
                            column,
                            expression.get("action_field_binding"),
                            expression.get("anonymous_integer_constant_binding"),
                            0,
                            supports,
                        )
                    )
                values = tuple(sorted(values_set))
            if not values:
                _fail("V54 compiled coordinate support became empty")
            support_rows.append(values)
        width = math.prod(len(values) for values in support_rows)
        if width > maximum_support_branch_evaluations:
            _fail("V54 one-step support crossed its frozen compute cap")
        result = set()
        for values in product(*support_rows):
            projected = list(state)
            for column, value in zip(targets, values, strict=True):
                projected[column] = value
            for _classification, token in terminal_predictions(tuple(projected)):
                row = list(projected)
                row[status_target] = token
                result.add(tuple(row))
        maximum_branch_width = max(maximum_branch_width, len(result))
        return tuple(sorted(result))

    def consensus_class(state: tuple[int, ...]) -> str | None:
        classes = {classification for classification, _token in terminal_predictions(state)}
        return next(iter(classes)) if len(classes) == 1 else None

    robust_calls = 0
    robust_truncated = False
    visiting = set()
    policy = {}

    @lru_cache(maxsize=None)
    def robust(state: tuple[int, ...], depth: int) -> bool:
        nonlocal branch_evaluations, robust_calls, robust_truncated
        robust_calls += 1
        classification = consensus_class(state)
        if classification == "ACCEPT":
            return True
        if classification in (None, "REJECT"):
            return False
        if (
            depth == 0
            or (state, depth) in visiting
            or robust_calls > maximum_robust_state_depth_evaluations
            or branch_evaluations >= maximum_support_branch_evaluations
        ):
            robust_truncated = (
                robust_calls > maximum_robust_state_depth_evaluations
                or branch_evaluations >= maximum_support_branch_evaluations
            )
            return False
        visiting.add((state, depth))
        for action in actions:
            branch = successors(state, action)
            branch_evaluations += len(branch)
            if branch_evaluations > maximum_support_branch_evaluations:
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
    support_path = []
    if not closed:
        predecessor = {initial: None}
        goal = None
        frontier_states = (initial,)
        prototypes = tuple(
            tuple(row) for row in verified["canonical_accepting_state_prototypes"]
        )

        def distance(state: tuple[int, ...]) -> int:
            if not prototypes:
                return 0
            return min(
                sum(abs(left - right) for left, right in zip(state, prototype, strict=True))
                for prototype in prototypes
            )

        for _depth in range(maximum_depth):
            next_rows = {}
            for state in frontier_states:
                if consensus_class(state) != "ACTIVE":
                    continue
                for action in actions:
                    branch = successors(state, action)
                    branch_evaluations += len(branch)
                    if branch_evaluations > maximum_support_branch_evaluations:
                        _fail("V54 support-feasible search crossed its compute cap")
                    for successor in branch:
                        classification = consensus_class(successor)
                        if successor == state or classification in (None, "REJECT") or successor in predecessor:
                            continue
                        edge = (state, action.key)
                        previous = next_rows.get(successor)
                        if previous is None or edge < previous:
                            next_rows[successor] = edge
            ranked = sorted(next_rows, key=lambda row: (distance(row), row))
            frontier_states = tuple(ranked[:support_feasible_beam_width])
            for successor in frontier_states:
                predecessor[successor] = next_rows[successor]
                if consensus_class(successor) == "ACCEPT":
                    goal = successor
                    break
            if goal is not None or not frontier_states:
                break
        if goal is None:
            _fail("V54 contextual model found no conservative abstract continuation")
        cursor = goal
        reversed_actions = []
        while predecessor[cursor] is not None:
            parent, key = predecessor[cursor]
            reversed_actions.append(key)
            cursor = parent
        support_path = list(reversed(reversed_actions))
    first = policy.get(initial) if closed else support_path[0] if support_path else None
    if type(first) is not int:
        _fail("V54 contextual policy omitted its initial action")
    return {
        "schema": "acfqp.generic_contextual_ordinal_plan.v54",
        "contextual_ordinal_successor_model_id": verified[
            "contextual_ordinal_successor_model_id"
        ],
        "target_partial_candidate_id": target["candidate_id"],
        "initial_action_key": first,
        "support_feasible_action_keys": support_path,
        "maximum_depth": maximum_depth,
        "retained_residual_expression_count": sum(len(rows) for rows in residual.values()),
        "retained_terminal_tree_count": len(terminal_frontier),
        "abstract_state_depth_cache_count": robust.cache_info().currsize,
        "abstract_support_branch_evaluations": branch_evaluations,
        "maximum_joint_successor_support_width": maximum_branch_width,
        "robust_all_version_space_branches_closed": closed,
        "robust_search_resource_cap_reached": robust_truncated,
        "support_feasible_receding_plan_found": True,
        "contextual_target_action_supports_derived_without_ground_successors": True,
        "all_residual_version_spaces_jointly_propagated": True,
        "all_mdl_minimal_terminal_trees_jointly_propagated": True,
        "ground_transition_accessed_during_abstract_search": False,
        "abstract_plan_used_as_safety_authority": False,
        "empirical_version_space_promoted_to_global_exact_dynamics": False,
        "complete_world_model_claimed": False,
    }


__all__ = ("plan_contextual_ordinal_model_v54",)
