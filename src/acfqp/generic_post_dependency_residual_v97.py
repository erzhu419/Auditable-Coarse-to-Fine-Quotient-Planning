"""Anonymous successor-coordinate dependency residual synthesis and planning.

The finite grammar learns a three-band support tree whose predicate reads one
already-computed successor coordinate.  Column, thresholds, and leaf values
are rebound from target observations; the source prior supplies only the tree
shape.  Every result is a fallible ordering heuristic.  Exact query-local
evidence remains the sole certificate authority.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
from itertools import product
import math
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import align_generic_occurrence_v5
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


POST_DEPENDENCY_GRAMMAR_V97 = (
    "SUCCESSOR_COLUMN",
    "ORDERED_LEQ_THRESHOLD",
    "THREE_BAND_FINITE_SUPPORT",
)
_CANDIDATE_DOMAIN = b"acfqp:post-dependency-residual-candidate:v97\x00"
_ACQUISITION_DOMAIN = b"acfqp:post-dependency-multi-residual-acquisition:v97\x00"


class GenericPostDependencyResidualV97Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPostDependencyResidualV97Error(message)


def _aligned_posts(
    evidence: Mapping[str, Any],
) -> tuple[list[list[int]], list[int], int]:
    layout = evidence.get("layout")
    rows = evidence.get("raw_transition_rows")
    if type(layout) is not dict or type(rows) is not list or not rows:
        _fail("V97 post-dependency evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list:
        _fail("V97 state layout changed")
    result = []
    contexts = set()
    for row in rows:
        action = row.get("selected_action") if type(row) is dict else None
        post = row.get("post_vector") if type(row) is dict else None
        pre = row.get("pre_vector") if type(row) is dict else None
        if (
            type(action) is not dict
            or type(action.get("action_key")) is not int
            or type(post) is not list
            or type(pre) is not list
            or sorted(order) != list(range(len(post)))
            or len(pre) != len(post)
        ):
            _fail("V97 raw transition inventory changed")
        result.append([post[index] for index in order])
        contexts.add((tuple(pre), action["action_key"]))
    return result, order, len(contexts)


def _signed_bits(value: int) -> int:
    return 1 + 2 * int(math.log2(abs(value) + 1))


def _candidate(
    posts: list[list[int]],
    *,
    target: int,
    driver: int,
    lower: int,
    upper: int,
    structural_prior_enabled: bool,
) -> dict[str, Any] | None:
    leaves: list[list[int]] = []
    for band in range(3):
        values = sorted(
            {
                row[target]
                for row in posts
                if (
                    (band == 0 and row[driver] <= lower)
                    or (band == 1 and lower < row[driver] <= upper)
                    or (band == 2 and row[driver] > upper)
                )
            }
        )
        if not values:
            return None
        leaves.append(values)
    excess = sum(
        len(leaves[0 if row[driver] <= lower else 1 if row[driver] <= upper else 2])
        - 1
        for row in posts
    )
    state_bits = max(1, math.ceil(math.log2(max(2, len(posts[0])))))
    support_bits = sum(_signed_bits(value) for leaf in leaves for value in leaf)
    payload = {
        "schema": "acfqp.post_dependency_residual_candidate.v97",
        "candidate_kind": "POST_DEPENDENCY_THREE_BAND_FINITE_SUPPORT",
        "target_column": target,
        "driver_post_column": driver,
        "lower_inclusive_threshold": lower,
        "upper_inclusive_threshold": upper,
        "leaf_supports": leaves,
        "normalized_expression": [
            "PD03",
            ["PD00", driver],
            ["PD01", lower],
            ["PD01", upper],
            [["PD02", *leaf] for leaf in leaves],
        ],
        "predictive_support_excess": excess,
        "description_length_bits": (
            (1 if structural_prior_enabled else 8)
            + 2 * state_bits
            + _signed_bits(lower)
            + _signed_bits(upper)
            + support_bits
        ),
        "structure_prior_enabled": structural_prior_enabled,
        "structure_prior_supplied_driver_thresholds_or_leaf_values": False,
        "fit_on_complete_available_query_pool": True,
        "future_prediction_calibrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "candidate_id": hashlib.sha256(
            _CANDIDATE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def synthesize_post_dependency_multi_residual_v97(
    evidence: Mapping[str, Any],
    base_acquisition: Mapping[str, Any],
    *,
    structural_prior_library: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if (
        type(base_acquisition) is not dict
        or base_acquisition.get("schema")
        != "acfqp.generic_multi_residual_acquisition.v24"
        or base_acquisition.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V97 base multi-residual acquisition changed")
    targets = evidence.get("unknown_residual_target_columns")
    if type(targets) is not list or targets != sorted(set(targets)) or not targets:
        _fail("V97 residual target inventory changed")
    structural_prior_enabled = structural_prior_library is not None
    if structural_prior_enabled and (
        structural_prior_library.get("schema")
        != "acfqp.post_dependency_structure_library.v97"
        or structural_prior_library.get("normalized_structure")
        != [
            "PD03",
            ["PD00", "DRIVER_POST_COLUMN"],
            ["PD01", "LOWER_THRESHOLD"],
            ["PD01", "UPPER_THRESHOLD"],
            ["PD02", "FINITE_LEAF_SUPPORTS"],
        ]
    ):
        _fail("V97 post-dependency structural prior changed")
    posts, _order, physical_labels = _aligned_posts(evidence)
    calibrated = copy.deepcopy(base_acquisition.get("compilable_candidates"))
    if type(calibrated) is not list:
        _fail("V97 calibrated candidate inventory changed")
    calibrated_targets = {row.get("target_column") for row in calibrated}
    completions = []
    evaluation_count = 0
    for target in targets:
        if target in calibrated_targets:
            continue
        candidates = []
        for driver in range(len(posts[0])):
            if driver == target:
                continue
            values = sorted({row[driver] for row in posts})
            for lower_offset in range(len(values) - 2):
                for upper_offset in range(lower_offset + 1, len(values) - 1):
                    evaluation_count += len(posts)
                    found = _candidate(
                        posts,
                        target=target,
                        driver=driver,
                        lower=values[lower_offset],
                        upper=values[upper_offset],
                        structural_prior_enabled=structural_prior_enabled,
                    )
                    if found is not None:
                        candidates.append(found)
        candidates.sort(
            key=lambda row: (
                row["predictive_support_excess"],
                row["description_length_bits"],
                canonical_json_bytes(row),
            )
        )
        if candidates:
            completions.append(candidates[0])
    all_candidates = sorted(
        [*calibrated, *copy.deepcopy(completions)],
        key=lambda row: row["target_column"],
    )
    payload = {
        "schema": "acfqp.post_dependency_multi_residual_acquisition.v97",
        "base_multi_residual_acquisition": copy.deepcopy(base_acquisition),
        "base_multi_residual_acquisition_id": base_acquisition[
            "multi_residual_acquisition_id"
        ],
        "unknown_residual_target_columns": list(targets),
        "shared_physical_ground_support_labels": physical_labels,
        "structural_prior_library_id": (
            None
            if structural_prior_library is None
            else structural_prior_library.get("source_library_id")
        ),
        "structural_prior_enabled": structural_prior_enabled,
        "same_finite_grammar_and_binding_search_in_prior_on_off_arms": True,
        "only_prior_code_length_switched": True,
        "post_dependency_candidate_binding_evaluation_count": evaluation_count,
        "calibrated_predecessor_candidates": calibrated,
        "retrospective_post_dependency_candidates": completions,
        "compilable_candidates": all_candidates,
        "compilable_target_columns": [row["target_column"] for row in all_candidates],
        "compilable_candidate_count": len(all_candidates),
        "all_residual_targets_have_compilable_proposals": (
            [row["target_column"] for row in all_candidates] == targets
        ),
        "successor_coordinate_dependency_discovered_from_raw_differences": bool(
            completions
        ),
        "dependency_program_used_as_fallible_action_ordering_heuristic": True,
        "persistent_exact_overlay_exclusively_discharges_safety": True,
        "ground_fact_transfer_present": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "multi_residual_acquisition_id": hashlib.sha256(
            _ACQUISITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


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
    _fail("V97 partial expression escaped the finite grammar")


def _residual_support(
    expression: Any,
    *,
    current: int,
    action: tuple[int, ...],
    field: int | None,
    constant: int | None,
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (current,)
    if expression == ["R01"] and field is not None:
        return (action[field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R03":
        left = _residual_support(
            expression[1], current=current, action=action, field=field, constant=constant
        )
        right = _residual_support(
            expression[2], current=current, action=action, field=field, constant=constant
        )
        if len(left) == len(right) == 1:
            return (left[0] + right[0],)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R04":
        left = _residual_support(
            expression[1], current=current, action=action, field=field, constant=constant
        )
        right = _residual_support(
            expression[2], current=current, action=action, field=field, constant=constant
        )
        if len(left) == len(right) == 1:
            return tuple(sorted({left[0], right[0]}))
    _fail("V97 residual expression escaped the finite grammar")


def _dependency_support(candidate: Mapping[str, Any], driver_value: int) -> tuple[int, ...]:
    lower = candidate["lower_inclusive_threshold"]
    upper = candidate["upper_inclusive_threshold"]
    band = 0 if driver_value <= lower else 1 if driver_value <= upper else 2
    return tuple(candidate["leaf_supports"][band])


def plan_post_dependency_abstract_program_v97(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    acquisition: Mapping[str, Any],
    *,
    maximum_depth: int,
    maximum_support_branch_evaluations: int = 1_000_000,
    support_feasible_beam_width: int = 16,
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(acquisition) is not dict
        or acquisition.get("schema")
        != "acfqp.post_dependency_multi_residual_acquisition.v97"
        or acquisition.get("proposal_only_not_safety_authority") is not True
        or maximum_depth <= 0
        or maximum_support_branch_evaluations <= 0
        or support_feasible_beam_width <= 0
    ):
        _fail("V97 abstract planner inventory changed")
    residuals = acquisition.get("compilable_candidates")
    if type(residuals) is not list or len(residuals) < 2:
        _fail("V97 requires jointly compilable residual proposals")
    dependencies = [
        row
        for row in residuals
        if row.get("candidate_kind")
        == "POST_DEPENDENCY_THREE_BAND_FINITE_SUPPORT"
    ]
    ordinary = [row for row in residuals if row not in dependencies]
    dependency_targets = {row["target_column"] for row in dependencies}
    independent = {
        row["target_column"]: {"kind": "PARTIAL", "value": row}
        for row in candidate.assignments
    }
    independent.update(
        {
            row["target_column"]: {"kind": "RESIDUAL", "value": row}
            for row in ordinary
        }
    )
    if (
        dependency_targets & set(independent)
        or any(row["driver_post_column"] not in independent for row in dependencies)
    ):
        _fail("V97 dependency graph is not one-step acyclic")
    all_targets = sorted((*independent, *dependency_targets))
    if all_targets != list(range(len(initial_raw_state))):
        _fail("V97 jointly compiled target partition is incomplete")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        observed_rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    state_order = candidate.public_document["layout"]["state_canonical_to_raw"]
    initial = tuple(initial_raw_state[index] for index in state_order)
    accepting = [row for row in aligned_rows if row.terminal_acceptance_after is True]
    if not accepting:
        _fail("V97 abstract planner requires observed acceptance")
    terminal_supports = {
        target: tuple(sorted({row.post[target] for row in accepting}))
        for target in all_targets
    }

    def terminal(state: tuple[int, ...]) -> bool:
        return all(state[target] in terminal_supports[target] for target in all_targets)

    evaluations = 0

    def successors(state: tuple[int, ...], action: FlatRawActionV4):
        nonlocal evaluations
        independent_targets = sorted(independent)
        supports = []
        for target in independent_targets:
            descriptor = independent[target]
            if descriptor["kind"] == "PARTIAL":
                support = _partial_support(
                    descriptor["value"], state[target], action.fields
                )
            else:
                residual = descriptor["value"]
                support = _residual_support(
                    residual["normalized_expression"],
                    current=state[target],
                    action=action.fields,
                    field=residual["action_field_binding"],
                    constant=residual["anonymous_integer_constant_binding"],
                )
            supports.append(support)
        result = set()
        for branch in product(*supports):
            values = dict(zip(independent_targets, branch, strict=True))
            dependent_supports = [
                _dependency_support(row, values[row["driver_post_column"]])
                for row in dependencies
            ]
            for dependent_values in product(*dependent_supports):
                completed = dict(values)
                completed.update(
                    zip(
                        [row["target_column"] for row in dependencies],
                        dependent_values,
                        strict=True,
                    )
                )
                result.add(tuple(completed[target] for target in all_targets))
        evaluations += len(result)
        if evaluations > maximum_support_branch_evaluations:
            _fail("V97 abstract support search crossed its compute cap")
        return tuple(sorted(result))

    def distance(state: tuple[int, ...]) -> int:
        return sum(
            min(abs(state[target] - value) for value in terminal_supports[target])
            for target in all_targets
        )

    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial: None
    }
    frontier = (initial,)
    goal = None
    best_edge = None
    best_rank = None
    for _depth in range(maximum_depth):
        candidates = {}
        for state in frontier:
            for action in aligned_catalogue:
                for successor in successors(state, action):
                    if successor == state:
                        continue
                    rank = (distance(successor), action.key, successor)
                    if best_rank is None or rank < best_rank:
                        best_rank = rank
                        best_edge = (state, action.key, successor)
                    if successor not in predecessor:
                        prior = candidates.get(successor)
                        edge = (state, action.key)
                        if prior is None or edge < prior:
                            candidates[successor] = edge
        ranked = sorted(candidates, key=lambda row: (distance(row), row))
        frontier = tuple(ranked[:support_feasible_beam_width])
        for successor in frontier:
            predecessor[successor] = candidates[successor]
            if terminal(successor):
                goal = successor
                break
        if goal is not None or not frontier:
            break
    path = []
    if goal is not None:
        cursor = goal
        while predecessor[cursor] is not None:
            parent, action_key = predecessor[cursor]
            path.append(action_key)
            cursor = parent
        path.reverse()
    elif best_edge is not None:
        path = [best_edge[1]]
    if not path:
        _fail("V97 dependency successor found no progressing abstract action")
    payload = {
        "schema": "acfqp.post_dependency_abstract_plan.v97",
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "multi_residual_acquisition_id": acquisition[
            "multi_residual_acquisition_id"
        ],
        "residual_candidate_ids": [row["candidate_id"] for row in residuals],
        "dependency_candidate_ids": [row["candidate_id"] for row in dependencies],
        "represented_target_columns": all_targets,
        "initial_action_key": path[0],
        "support_feasible_action_keys": path,
        "support_feasible_goal_reached": goal is not None,
        "maximum_depth": maximum_depth,
        "maximum_support_branch_evaluations": maximum_support_branch_evaluations,
        "support_feasible_beam_width": support_feasible_beam_width,
        "abstract_support_branch_evaluations": evaluations,
        "successor_coordinate_dependencies_evaluated_after_independent_factors": True,
        "ground_transition_accessed_during_abstract_search": False,
        "abstract_plan_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "abstract_plan_id": hashlib.sha256(
            b"acfqp:post-dependency-abstract-plan:v97\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "POST_DEPENDENCY_GRAMMAR_V97",
    "plan_post_dependency_abstract_program_v97",
    "synthesize_post_dependency_multi_residual_v97",
)
