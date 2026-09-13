"""Query-bank refinement of an empirical controlled predictive quotient.

The initial partition is the unchanged V2 candidate. Refinement checks the
candidate's own frozen policy on every state of the supplied empirical kernel.
Action-response signatures determine splits; optimal full-state value labels
and an independent environment model are not inputs to construction.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, replace
import math
from time import perf_counter

from .controlled_predictive_quotient_v1 import (
    Cell,
    CompiledModel,
    FiniteModel,
    Query,
    _actions,
    _compile_rows,
    _distance,
    _evaluate_policy,
    _signature,
    build_quotient,
    plan,
)


@dataclass(frozen=True)
class RefinementResult:
    compiled: CompiledModel
    diagnostics: dict[str, object]


_ERROR_NAMES = (
    "policy_residual", "reward_discrepancy", "failure_discrepancy", "success_discrepancy",
)


def _inventory(model: CompiledModel) -> dict[str, int]:
    return {
        "cells": len(model.cells),
        "active_cells": sum(cell.terminal == "ACTIVE" for cell in model.cells.values()),
        "state_action_rows": len(model.rows),
        "outcomes": sum(len(row) for row in model.rows.values()),
    }


def _add_counts(total: dict[str, int], current: dict[str, int]) -> None:
    for name, value in current.items():
        total[name] = total.get(name, 0) + value


def _signature_counts(model: FiniteModel, members: tuple[int, ...],
                      actions: dict[int, tuple[str, ...]]) -> dict[str, int]:
    return {
        "states": len(members),
        "state_action_rows": sum(len(actions.get(state, ())) for state in members),
        "outcomes": sum(len(model.rows[state, action])
                        for state in members for action in actions.get(state, ())),
    }


def _compile_partition(model: FiniteModel, groups: list[Cell]) -> CompiledModel:
    cells = dict(enumerate(groups))
    mapping = {state: cell for cell, group in cells.items() for state in group.members}
    return CompiledModel(cells, _compile_rows(model, cells, mapping),
                         tuple(mapping[root] for root in model.roots), mapping, {})


def build_refined_quotient(
    model: FiniteModel,
    queries: Mapping[str, Query],
    *,
    numeric_tolerance: float = 1e-10,
) -> RefinementResult:
    """Refine until the selected policies are consistent in the empirical model.

    A selected policy must have no positive one-step improvement and must
    predict each member's reward, failure, and success components to numerical
    tolerance. The checks cover every empirical state, including states not
    reached from a root. Violating cells split by their exact current recursive
    action-response signature, then the policies are recomputed. The returned
    dynamics remain executable with the ordinary compiled-model planner.

    This condition concerns the supplied empirical kernel and finite query bank.
    It is not a statistical certificate for the true environment, and it does
    not require equivalence for queries outside the bank.
    """
    if not queries:
        raise ValueError("refinement requires a nonempty query bank")
    if not math.isfinite(numeric_tolerance) or numeric_tolerance < 0:
        raise ValueError("numeric_tolerance must be finite and nonnegative")
    start = perf_counter()
    initial_start = perf_counter()
    compiled = build_quotient(model, reward_tolerance=0.01, tv_tolerance=0.2)
    initial_seconds = perf_counter() - initial_start
    initial_inventory = _inventory(compiled)
    actions = _actions(model)
    empirical_states = tuple(model.layers)
    active_states = tuple(state for state in model.layers if model.terminal[state] == "ACTIVE")
    work: dict[str, dict[str, int]] = {
        name: {} for name in (
            "planning", "compiled_policy_evaluation", "empirical_policy_evaluation",
            "greedy_scan", "split_signatures", "partition_recompilation",
            "final_diameters",
        )
    }
    iterations: list[dict[str, object]] = []
    rounds = 0
    while True:
        iteration_start = perf_counter()
        worst = dict.fromkeys(_ERROR_NAMES, 0.0)
        violations: dict[int, dict[str, object]] = {}
        per_query: dict[str, dict[str, object]] = {}
        for query_name, query in queries.items():
            fitted = plan(compiled, query)
            predicted = _evaluate_policy(
                {cell: group.terminal for cell, group in compiled.cells.items()},
                compiled.rows, tuple(compiled.cells), fitted.policy, query,
            )
            lifted = {state: fitted.policy[compiled.state_to_cell[state]] for state in active_states}
            empirical = _evaluate_policy(model.terminal, model.rows, empirical_states, lifted, query)
            _add_counts(work["planning"], fitted.counts)
            _add_counts(work["compiled_policy_evaluation"], predicted.counts)
            _add_counts(work["empirical_policy_evaluation"], empirical.counts)
            query_worst = dict.fromkeys(_ERROR_NAMES, 0.0)
            query_violations = 0
            scan_counts = {"active_states": 0, "state_action_rows": 0, "outcomes": 0}
            for state in active_states:
                cell = compiled.state_to_cell[state]
                member = empirical.root_metrics[state]
                prediction = predicted.root_metrics[cell]
                best = -math.inf
                scan_counts["active_states"] += 1
                for action in actions[state]:
                    row = model.rows[state, action]
                    scan_counts["state_action_rows"] += 1
                    scan_counts["outcomes"] += len(row)
                    value = math.fsum(
                        outcome.probability * (
                            query.reward_weight * outcome.reward
                            + empirical.root_metrics[outcome.next_state]["value"]
                        ) for outcome in row
                    )
                    best = max(best, value)
                errors = {"policy_residual": max(0.0, best - member["value"])}
                errors.update({f"{component}_discrepancy": abs(member[component] - prediction[component])
                               for component in ("reward", "failure", "success")})
                for name, error in errors.items():
                    query_worst[name] = max(query_worst[name], error)
                    worst[name] = max(worst[name], error)
                if any(error > numeric_tolerance for error in errors.values()):
                    query_violations += 1
                    record = violations.setdefault(cell, {
                        "states": set(), "query_names": set(), "worst_errors": dict.fromkeys(_ERROR_NAMES, 0.0),
                    })
                    record["states"].add(state)
                    record["query_names"].add(query_name)
                    for name, error in errors.items():
                        record["worst_errors"][name] = max(record["worst_errors"][name], error)
            _add_counts(work["greedy_scan"], scan_counts)
            per_query[query_name] = {
                "worst_errors": query_worst, "violating_states": query_violations,
                "planning_counts": fitted.counts, "compiled_evaluation_counts": predicted.counts,
                "empirical_evaluation_counts": empirical.counts, "greedy_scan_counts": scan_counts,
            }
        iteration: dict[str, object] = {
            "iteration": len(iterations), "inventory": _inventory(compiled),
            "worst_errors": worst, "queries": per_query, "violating_cells": len(violations),
            "violating_states": len(set().union(*(record["states"] for record in violations.values()))),
            "splits": [],
        }
        if not violations:
            iteration["elapsed_seconds"] = perf_counter() - iteration_start
            iterations.append(iteration)
            break
        new_groups: list[Cell] = []
        for cell, group in compiled.cells.items():
            if cell not in violations or len(group.members) == 1:
                new_groups.append(group)
                continue
            buckets: dict[tuple, list[int]] = defaultdict(list)
            for state in group.members:
                signature = _signature(model, state, actions.get(state, ()), compiled.state_to_cell)
                buckets[signature].append(state)
            _add_counts(work["split_signatures"], _signature_counts(model, group.members, actions))
            if len(buckets) == 1:
                new_groups.append(group)
                continue
            replacements = [Cell(group.layer, group.terminal, tuple(sorted(members)))
                            for signature, members in sorted(buckets.items())]
            new_groups.extend(replacements)
            violation = violations[cell]
            iteration["splits"].append({
                "cell": cell, "layer": group.layer, "members_before": list(group.members),
                "members_after": [list(replacement.members) for replacement in replacements],
                "violating_states": sorted(violation["states"]),
                "query_names": sorted(violation["query_names"]),
                "worst_errors": violation["worst_errors"],
            })
        if not iteration["splits"]:
            raise RuntimeError(
                "empirical policy violations remain but no violating cell has distinct "
                "recursive action signatures; refinement cannot progress"
            )
        compiled = _compile_partition(model, new_groups)
        _add_counts(work["partition_recompilation"], {
            "calls": 1, "states": len(model.layers), "state_action_rows": len(model.rows),
            "outcomes": sum(len(row) for row in model.rows.values()),
        })
        rounds += 1
        iteration["elapsed_seconds"] = perf_counter() - iteration_start
        iterations.append(iteration)

    # Splitting successor cells can change retained cells' TV diameters. Report
    # the final geometry rather than carrying the initial approximate bounds.
    diameters = {}
    for cell, group in compiled.cells.items():
        if group.terminal != "ACTIVE":
            diameters[cell] = {"reward": 0.0, "tv": 0.0}
            _add_counts(work["final_diameters"], {"terminal_cells_direct_zero": 1})
            continue
        signatures = sorted({_signature(model, state, actions[state], compiled.state_to_cell)
                             for state in group.members})
        _add_counts(work["final_diameters"], _signature_counts(model, group.members, actions))
        reward_diameter = tv_diameter = 0.0
        for index, left in enumerate(signatures):
            for right in signatures[index + 1:]:
                reward, tv = _distance(left, right)
                reward_diameter, tv_diameter = max(reward_diameter, reward), max(tv_diameter, tv)
                _add_counts(work["final_diameters"], {"pair_comparisons": 1})
        diameters[cell] = {"reward": reward_diameter, "tv": tv_diameter}
    compiled = replace(compiled, diameters=diameters)
    diagnostics = {
        "method": "empirical_query_bank_policy_refinement_v3",
        "queries": {name: {"reward_weight": query.reward_weight,
                           "failure_penalty": query.failure_penalty,
                           "goal_bonus": query.goal_bonus} for name, query in queries.items()},
        "numeric_tolerance": numeric_tolerance,
        "initial_reward_tolerance": 0.01, "initial_tv_tolerance": 0.2,
        "initial_inventory": initial_inventory, "final_inventory": _inventory(compiled),
        "refinement_rounds": rounds, "iterations": iterations,
        "final_worst_errors": iterations[-1]["worst_errors"],
        "empirical_query_bank_consistent": True,
        "work_counts": work,
        "initial_builder": {
            "elapsed_seconds": initial_seconds,
            "input_states": len(model.layers), "input_rows": len(model.rows),
            "input_outcomes": sum(len(row) for row in model.rows.values()),
            "internal_complete_link_comparisons": None,
            "count_scope": "V1 initial builder has no internal traversal instrumentation; input sizes are inventory, not work counts",
        },
        "construction_seconds": perf_counter() - start,
        "construction_scope": "initial fit, repeated planning and all-state policy evaluation, greedy scans, splitting, recompilation, and final diameter calculation",
    }
    return RefinementResult(compiled, diagnostics)
