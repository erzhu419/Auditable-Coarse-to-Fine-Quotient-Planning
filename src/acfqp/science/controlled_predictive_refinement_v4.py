"""The V3 empirical refinement rule with dependency-local recomputation.

Cell IDs remain stable when a cell splits. Only its children and direct
predecessors need new averaged rows; policy and component caches are refreshed
through the transitive predecessor closure. The graph includes every legal
action, so an unused action cannot hide an affected choice. The stopping rule
and simultaneous signature splits are unchanged from V3.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
import math
from time import perf_counter

from .controlled_predictive_quotient_v1 import (
    Cell, CompiledModel, FiniteModel, Outcome, Query, _actions, _distance,
    _signature, _terminal_value, build_quotient,
)
from .controlled_predictive_refinement_v3 import (
    RefinementResult, _ERROR_NAMES, _add_counts, _inventory, _signature_counts,
)


@dataclass
class _QueryCache:
    values: dict[int, float] = field(default_factory=dict)
    policy: dict[int, str] = field(default_factory=dict)
    predicted: dict[int, dict[str, float]] = field(default_factory=dict)
    empirical: dict[int, dict[str, float]] = field(default_factory=dict)
    errors: dict[int, dict[str, float]] = field(default_factory=dict)


def _components(status, row, successors, query):
    if status != "ACTIVE":
        result = {"reward": 0.0, "failure": float(status == "LOST"),
                  "success": float(status == "WON")}
    else:
        reached = [(outcome, successors[outcome.next_state])
                   for outcome in row if outcome.probability]
        result = {
            "reward": math.fsum(o.probability * (o.reward + m["reward"]) for o, m in reached),
            "failure": math.fsum(o.probability * m["failure"] for o, m in reached),
            "success": math.fsum(o.probability * m["success"] for o, m in reached),
        }
    result["value"] = (query.reward_weight * result["reward"]
                       - query.failure_penalty * result["failure"]
                       + query.goal_bonus * result["success"])
    return result


def _refresh_query(model, compiled, actions, cells, states, query, cache):
    planning = dict.fromkeys(("active_states", "state_action_rows", "outcomes", "visited_cells"), 0)
    predicted = dict.fromkeys(("active_states", "state_action_rows", "outcomes", "visited_states"), 0)
    empirical = dict(predicted)
    scanning = dict.fromkeys(("active_states", "state_action_rows", "outcomes"), 0)
    for cell in cells:
        group = compiled.cells[cell]
        planning["visited_cells"] += 1
        predicted["visited_states"] += 1
        row = ()
        if group.terminal != "ACTIVE":
            cache.values[cell] = _terminal_value(group.terminal, query)
        else:
            planning["active_states"] += 1
            best, chosen = -math.inf, ""
            for action in actions[group.members[0]]:
                candidate = compiled.rows[cell, action]
                planning["state_action_rows"] += 1
                planning["outcomes"] += len(candidate)
                value = math.fsum(o.probability * (
                    query.reward_weight * o.reward + cache.values[o.next_state]
                ) for o in candidate)
                if value > best:
                    best, chosen = value, action
            cache.values[cell], cache.policy[cell] = best, chosen
            row = compiled.rows[cell, chosen]
            predicted["active_states"] += 1
            predicted["state_action_rows"] += 1
            predicted["outcomes"] += len(row)
        cache.predicted[cell] = _components(group.terminal, row, cache.predicted, query)
    for state in states:
        status = model.terminal[state]
        empirical["visited_states"] += 1
        row = ()
        if status == "ACTIVE":
            row = model.rows[state, cache.policy[compiled.state_to_cell[state]]]
            empirical["active_states"] += 1
            empirical["state_action_rows"] += 1
            empirical["outcomes"] += len(row)
        cache.empirical[state] = _components(status, row, cache.empirical, query)
    for state in states:
        if model.terminal[state] != "ACTIVE":
            continue
        cell = compiled.state_to_cell[state]
        member, prediction = cache.empirical[state], cache.predicted[cell]
        best = -math.inf
        scanning["active_states"] += 1
        for action in actions[state]:
            row = model.rows[state, action]
            scanning["state_action_rows"] += 1
            scanning["outcomes"] += len(row)
            value = math.fsum(o.probability * (
                query.reward_weight * o.reward + cache.empirical[o.next_state]["value"]
            ) for o in row)
            best = max(best, value)
        cache.errors[state] = {
            "policy_residual": max(0.0, best - member["value"]),
            **{f"{name}_discrepancy": abs(member[name] - prediction[name])
               for name in ("reward", "failure", "success")},
        }
    return {"planning": planning, "compiled_policy_evaluation": predicted,
            "empirical_policy_evaluation": empirical, "greedy_scan": scanning}


def _recompile_rows(model, compiled, cell_ids, actions, work):
    """Average exactly the same member rows as V3, for changed sources only."""
    counts = {"calls": 1, "cells": len(cell_ids), "states": 0,
              "state_action_rows": 0, "outcomes": 0}
    for cell in cell_ids:
        group = compiled.cells[cell]
        counts["states"] += len(group.members)
        for action in actions.get(group.members[0], ()):
            mass, reward_mass = defaultdict(list), defaultdict(list)
            for state in group.members:
                row = model.rows[state, action]
                counts["state_action_rows"] += 1
                counts["outcomes"] += len(row)
                for outcome in row:
                    if outcome.probability:
                        target = compiled.state_to_cell[outcome.next_state]
                        mass[target].append(outcome.probability)
                        reward_mass[target].append(outcome.probability * outcome.reward)
            compiled.rows[cell, action] = tuple(
                Outcome(math.fsum(parts) / len(group.members), target,
                        math.fsum(reward_mass[target]) / math.fsum(parts))
                for target, parts in sorted(mass.items())
            )
    _add_counts(work, counts)


def _update_dependencies(compiled, cell_ids, actions, successors, predecessors, work):
    for cell in cell_ids:
        for target in successors.get(cell, ()):
            predecessors[target].discard(cell)
            _add_counts(work, {"removed_graph_edges": 1})
        targets = set()
        group = compiled.cells[cell]
        for action in actions.get(group.members[0], ()):
            row = compiled.rows[cell, action]
            targets.update(outcome.next_state for outcome in row if outcome.probability)
            _add_counts(work, {"graph_rows_read": 1, "graph_outcomes_read": len(row)})
        successors[cell] = targets
        for target in targets:
            predecessors[target].add(cell)
            _add_counts(work, {"added_graph_edges": 1})
        _add_counts(work, {"graph_cells_refreshed": 1})


def build_refined_quotient_v4(
    model: FiniteModel,
    queries: Mapping[str, Query],
    *,
    numeric_tolerance: float = 1e-10,
) -> RefinementResult:
    """Apply V3's all-state empirical rule, caching dependency-unaffected work.

    No full-state optimal values or independent environment kernel enter the
    builder. Cached checks are included in every round's stopping decision.
    Construction time includes graph maintenance, cache operations, reporting
    summaries and the unchanged initial fit and final diameter calculation.
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
    work = {name: {} for name in (
        "planning", "compiled_policy_evaluation", "empirical_policy_evaluation",
        "greedy_scan", "split_signatures", "partition_recompilation",
        "final_diameters", "dependency_metadata", "cached_error_summary",
    )}
    metadata = work["dependency_metadata"]
    _add_counts(metadata, {"action_index_rows_read": len(model.rows)})
    successors, predecessors = {}, defaultdict(set)
    _update_dependencies(compiled, compiled.cells, actions, successors, predecessors, metadata)
    caches = {name: _QueryCache() for name in queries}
    dirty = set(compiled.cells)
    iterations = []
    rounds = 0
    while True:
        iteration_start = perf_counter()
        ordered_cells = sorted(dirty, key=lambda cell: (compiled.cells[cell].layer, cell))
        ordered_states = sorted(
            (state for cell in dirty for state in compiled.cells[cell].members),
            key=lambda state: (model.layers[state], state),
        )
        _add_counts(metadata, {"ordered_dirty_cells": len(ordered_cells),
                               "ordered_dirty_states": len(ordered_states)})
        worst = dict.fromkeys(_ERROR_NAMES, 0.0)
        violations, per_query = {}, {}
        for query_name, query in queries.items():
            cache = caches[query_name]
            counts = _refresh_query(model, compiled, actions, ordered_cells, ordered_states, query, cache)
            for name, current in counts.items():
                _add_counts(work[name], current)
            query_worst = dict.fromkeys(_ERROR_NAMES, 0.0)
            query_violations = 0
            for state, errors in cache.errors.items():
                for name, error in errors.items():
                    query_worst[name] = max(query_worst[name], error)
                    worst[name] = max(worst[name], error)
                if any(error > numeric_tolerance for error in errors.values()):
                    query_violations += 1
                    cell = compiled.state_to_cell[state]
                    record = violations.setdefault(cell, {
                        "states": set(), "query_names": set(),
                        "worst_errors": dict.fromkeys(_ERROR_NAMES, 0.0),
                    })
                    record["states"].add(state)
                    record["query_names"].add(query_name)
                    for name, error in errors.items():
                        record["worst_errors"][name] = max(record["worst_errors"][name], error)
            _add_counts(work["cached_error_summary"], {
                "state_error_records_read": len(cache.errors),
                "error_coordinates_read": len(cache.errors) * len(_ERROR_NAMES),
            })
            per_query[query_name] = {
                "worst_errors": query_worst, "violating_states": query_violations,
                "planning_counts": counts["planning"],
                "compiled_evaluation_counts": counts["compiled_policy_evaluation"],
                "empirical_evaluation_counts": counts["empirical_policy_evaluation"],
                "greedy_scan_counts": counts["greedy_scan"],
            }
        iteration = {
            "iteration": len(iterations), "inventory": _inventory(compiled),
            "worst_errors": worst, "queries": per_query, "violating_cells": len(violations),
            "violating_states": len(set().union(*(r["states"] for r in violations.values()))),
            "recomputed_cells": len(ordered_cells), "recomputed_states": len(ordered_states),
            "cached_cells": len(compiled.cells) - len(ordered_cells),
            "cached_states": len(model.layers) - len(ordered_states), "splits": [],
        }
        if not violations:
            iteration["elapsed_seconds"] = perf_counter() - iteration_start
            iterations.append(iteration)
            break
        replacements = {}
        for cell, violation in violations.items():
            group = compiled.cells[cell]
            if len(group.members) == 1:
                continue
            buckets = defaultdict(list)
            for state in group.members:
                buckets[_signature(model, state, actions.get(state, ()), compiled.state_to_cell)].append(state)
            _add_counts(work["split_signatures"], _signature_counts(model, group.members, actions))
            if len(buckets) == 1:
                continue
            children = [Cell(group.layer, group.terminal, tuple(sorted(members)))
                        for signature, members in sorted(buckets.items())]
            replacements[cell] = children
            iteration["splits"].append({
                "cell": cell, "layer": group.layer, "members_before": list(group.members),
                "members_after": [list(child.members) for child in children],
                "violating_states": sorted(violation["states"]),
                "query_names": sorted(violation["query_names"]),
                "worst_errors": violation["worst_errors"],
            })
        if not replacements:
            raise RuntimeError(
                "empirical policy violations remain but no violating cell has distinct "
                "recursive action signatures; refinement cannot progress"
            )

        # The old union graph contains all dependencies of every split child.
        # Compute closure before changing it, including every member of affected
        # averaged cells. Raw-state ancestors alone would miss those members.
        dirty = set(replacements)
        queue = list(dirty)
        direct_parents = set()
        for cell in replacements:
            direct_parents.update(predecessors[cell])
            _add_counts(metadata, {"direct_predecessor_edges_read": len(predecessors[cell])})
        while queue:
            cell = queue.pop()
            _add_counts(metadata, {"closure_cells_popped": 1,
                                   "closure_predecessor_edges_read": len(predecessors[cell])})
            for parent in predecessors[cell]:
                if parent not in dirty:
                    dirty.add(parent)
                    queue.append(parent)
        rows_to_rebuild = set(replacements) | direct_parents
        for cell, children in replacements.items():
            for index, child in enumerate(children):
                child_id = cell if index == 0 else len(compiled.cells)
                compiled.cells[child_id] = child
                compiled.state_to_cell.update((state, child_id) for state in child.members)
                dirty.add(child_id)
                rows_to_rebuild.add(child_id)
                _add_counts(metadata, {"mapping_states_written": len(child.members), "child_cells_written": 1})
        compiled = replace(compiled, roots=tuple(compiled.state_to_cell[root] for root in model.roots))
        _add_counts(metadata, {"root_mapping_lookups": len(model.roots)})
        _recompile_rows(model, compiled, rows_to_rebuild, actions, work["partition_recompilation"])
        _update_dependencies(compiled, rows_to_rebuild, actions, successors, predecessors, metadata)
        rounds += 1
        iteration["elapsed_seconds"] = perf_counter() - iteration_start
        iterations.append(iteration)

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
        "method": "empirical_query_bank_dependency_refinement_v4",
        "queries": {name: {"reward_weight": query.reward_weight,
                           "failure_penalty": query.failure_penalty,
                           "goal_bonus": query.goal_bonus} for name, query in queries.items()},
        "numeric_tolerance": numeric_tolerance,
        "initial_reward_tolerance": 0.01, "initial_tv_tolerance": 0.2,
        "initial_inventory": initial_inventory, "final_inventory": _inventory(compiled),
        "refinement_rounds": rounds, "iterations": iterations,
        "final_worst_errors": iterations[-1]["worst_errors"],
        "empirical_query_bank_consistent": True, "work_counts": work,
        "initial_builder": {
            "elapsed_seconds": initial_seconds,
            "input_states": len(model.layers), "input_rows": len(model.rows),
            "input_outcomes": sum(len(row) for row in model.rows.values()),
            "internal_complete_link_comparisons": None,
            "count_scope": "V1 initial builder has no internal traversal instrumentation; input sizes are inventory, not work counts",
        },
        "cache_scope": "Per-query compiled values/policies, compiled and empirical components, and state checks; all-action predecessor closure invalidation",
        "construction_scope": "initial fit, dependency indexing, affected planning and evaluation, cached-error summaries, splitting, local recompilation, graph updates, and final diameters",
        "count_scope": "Traversal work and graph/cache-summary operations are separate categories; dictionary accesses, allocations and sorting comparisons are timed but not individually counted",
        "construction_seconds": perf_counter() - start,
    }
    return RefinementResult(compiled, diagnostics)
