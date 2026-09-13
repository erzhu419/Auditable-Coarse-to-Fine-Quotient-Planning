"""Public finite 2048 development slice for controlled predictive quotients.

Every legal action and spawn outcome is enumerated to the requested horizon.
These hand-written dense boards are development examples, not campaign data.
The learned encoder is a lookup table over this explicitly covered state set.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from time import perf_counter
from typing import Any

from acfqp.domains.standard_2048 import (
    Swipe2048Status,
    legal_actions_v1,
    state_from_board_v1,
    step_v1,
)
from acfqp.science.controlled_predictive_quotient_v1 import (
    CompiledModel,
    FiniteModel,
    Outcome,
    Query,
    action_outcome_shuffle,
    audit_policy,
    build_quotient,
    compile_full_state,
    evaluate_compiled_policy,
    plan,
    sample_model,
)


PUBLIC_DEVELOPMENT_BOARDS: dict[str, tuple[int, ...]] = {
    "last_pair_spawn_risk": (
        8, 6, 9, 7,
        5, 9, 7, 10,
        9, 7, 10, 8,
        4, 3, 1, 1,
    ),
    "dense_merge_choice": (
        6, 5, 4, 3,
        5, 4, 3, 2,
        4, 3, 2, 1,
        3, 2, 2, 0,
    ),
    "adjacent_1024_goal": (
        10, 9, 8, 7,
        10, 8, 7, 6,
        8, 7, 6, 5,
        7, 6, 5, 0,
    ),
}

DEVELOPMENT_QUERIES: dict[str, Query] = {
    "merge_reward": Query(reward_weight=1.0, failure_penalty=0.0, goal_bonus=0.0),
    "failure_aware": Query(reward_weight=1.0, failure_penalty=1.0, goal_bonus=0.0),
    "goal_and_failure": Query(reward_weight=1.0, failure_penalty=5.0, goal_bonus=1.0),
}


@dataclass(frozen=True)
class DevelopmentClosure:
    model: FiniteModel
    boards: dict[int, tuple[int, ...]]
    root_names: tuple[str, ...]
    counts: dict[str, int]
    elapsed_seconds: float


def build_development_closure(
    *,
    horizon: int = 3,
    max_nodes: int = 30_000,
    boards: dict[str, tuple[int, ...]] | None = None,
) -> DevelopmentClosure:
    """Build the complete layered reachable model, or fail without truncation."""
    if type(horizon) is not int or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    if type(max_nodes) is not int or max_nodes < 1:
        raise ValueError("max_nodes must be a positive integer")
    fixtures = PUBLIC_DEVELOPMENT_BOARDS if boards is None else boards
    if not fixtures:
        raise ValueError("at least one development board is required")
    started = perf_counter()
    index: dict[tuple[int, tuple[int, ...]], int] = {}
    queue: list[tuple[int, tuple[int, ...]]] = []
    layers: dict[int, int] = {}
    statuses: dict[int, str] = {}
    state_boards: dict[int, tuple[int, ...]] = {}

    def register(remaining: int, board: tuple[int, ...]) -> int:
        key = (remaining, board)
        if key in index:
            return index[key]
        if len(index) >= max_nodes:
            raise ValueError(
                f"complete closure exceeds max_nodes={max_nodes}; no truncated model produced"
            )
        state = state_from_board_v1(board)
        state_id = len(index)
        index[key] = state_id
        queue.append(key)
        layers[state_id] = remaining
        statuses[state_id] = (
            "CUTOFF" if remaining == 0 and state.status is Swipe2048Status.ACTIVE
            else state.status.value
        )
        state_boards[state_id] = board
        return state_id

    roots = tuple(register(horizon, board) for board in fixtures.values())
    rows: dict[tuple[int, str], tuple[Outcome, ...]] = {}
    exact_outcomes = 0
    for remaining, board in queue:
        state_id = index[(remaining, board)]
        if statuses[state_id] != "ACTIVE":
            continue
        state = state_from_board_v1(board)
        for action in legal_actions_v1(board):
            support = step_v1(state, action)
            exact_outcomes += len(support)
            rows[state_id, action.value] = tuple(
                Outcome(
                    probability=float(outcome.probability),
                    next_state=register(remaining - 1, outcome.next_state.board),
                    reward=outcome.merge_score / 2048.0,
                )
                for outcome in support
            )
    model = FiniteModel(layers=layers, terminal=statuses, rows=rows, roots=roots)
    return DevelopmentClosure(
        model=model,
        boards=state_boards,
        root_names=tuple(fixtures),
        counts={
            "states": len(layers),
            "exact_transition_row_calls": len(rows),
            "exact_outcomes_enumerated": exact_outcomes,
            "active_states": sum(status == "ACTIVE" for status in statuses.values()),
        },
        elapsed_seconds=perf_counter() - started,
    )


def _json_bytes(value: Any) -> int:
    return len(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _compiled_inventory(compiled: CompiledModel, closure: DevelopmentClosure) -> dict[str, Any]:
    """Count the actual compiled storage; sizes are JSON bytes, not RAM claims."""
    payload = {
        "cells": {cell: asdict(value) for cell, value in compiled.cells.items()},
        "rows": [
            [cell, action, [asdict(outcome) for outcome in outcomes]]
            for (cell, action), outcomes in sorted(compiled.rows.items())
        ],
        "roots": compiled.roots,
        "diameters": compiled.diameters,
    }
    lookup_payload = [
        [closure.model.layers[state], closure.boards[state], cell]
        for state, cell in sorted(compiled.state_to_cell.items())
    ]
    return {
        "cells": len(compiled.cells),
        "active_cells": sum(cell.terminal == "ACTIVE" for cell in compiled.cells.values()),
        "state_action_rows": len(compiled.rows),
        "successor_entries": sum(len(row) for row in compiled.rows.values()),
        "compiled_model_json_bytes": _json_bytes(payload),
        "state_id_to_cell_json_bytes": _json_bytes(compiled.state_to_cell),
        "board_and_horizon_encoder_json_bytes": _json_bytes(lookup_payload),
        "encoding_note": "The board encoder and integer map are reported separately; they are alternative lookup representations, not additive RAM measurements.",
        "largest_cell_members": max(len(cell.members) for cell in compiled.cells.values()),
        "max_cell_diameters": {
            name: max(values.get(name, 0.0) for values in compiled.diameters.values())
            for name in sorted({key for row in compiled.diameters.values() for key in row})
        },
    }


def _reverse_labels(model: FiniteModel) -> tuple[FiniteModel, dict[int, int]]:
    source_ids = sorted(model.layers)
    relabel = dict(zip(source_ids, reversed(source_ids), strict=True))
    return FiniteModel(
        layers={relabel[state]: depth for state, depth in reversed(tuple(model.layers.items()))},
        terminal={relabel[state]: status for state, status in reversed(tuple(model.terminal.items()))},
        rows={
            (relabel[state], action): tuple(
                Outcome(row.probability, relabel[row.next_state], row.reward) for row in outcomes
            )
            for (state, action), outcomes in reversed(tuple(model.rows.items()))
        },
        roots=tuple(relabel[state] for state in model.roots),
    ), relabel


def run_development(
    *,
    horizon: int = 3,
    max_nodes: int = 30_000,
    samples_per_row: int = 64,
    seed: int = 73129,
    reward_tolerance: float = 0.01,
    tv_tolerance: float = 0.2,
) -> dict[str, Any]:
    """Fit once and reuse the finite models for three development queries."""
    closure = build_development_closure(horizon=horizon, max_nodes=max_nodes)
    started = perf_counter()
    empirical = sample_model(closure.model, samples_per_row=samples_per_row, seed=seed)
    sample_seconds = perf_counter() - started
    builders = {
        "exact_ground": lambda: compile_full_state(closure.model),
        "full_state_empirical": lambda: compile_full_state(empirical),
        "learned_controlled_quotient": lambda: build_quotient(
            empirical, reward_tolerance=reward_tolerance, tv_tolerance=tv_tolerance
        ),
        "action_outcome_shuffle": lambda: build_quotient(
            action_outcome_shuffle(empirical),
            reward_tolerance=reward_tolerance,
            tv_tolerance=tv_tolerance,
        ),
        "oracle_exact_quotient": lambda: build_quotient(closure.model),
    }
    compiled: dict[str, CompiledModel] = {}
    inventories: dict[str, Any] = {}
    for name, builder in builders.items():
        started = perf_counter()
        compiled[name] = builder()
        construction_seconds = perf_counter() - started
        started = perf_counter()
        inventories[name] = _compiled_inventory(compiled[name], closure)
        inventories[name]["construction_seconds"] = construction_seconds
        inventories[name]["inventory_serialization_seconds"] = perf_counter() - started
        inventories[name]["privileged_exact_dynamics"] = name in {
            "exact_ground", "oracle_exact_quotient"
        }
        inventories[name]["fit_count"] = int(name != "exact_ground" and name != "full_state_empirical")

    results: dict[str, Any] = {}
    for query_name, query in DEVELOPMENT_QUERIES.items():
        query_results: dict[str, Any] = {}
        for model_name, model in compiled.items():
            started = perf_counter()
            solved = plan(model, query=query)
            planning_seconds = perf_counter() - started
            started = perf_counter()
            forecast = evaluate_compiled_policy(model, solved, query=query)
            forecast_evaluation_seconds = perf_counter() - started
            started = perf_counter()
            audited = audit_policy(closure.model, model, solved, query=query)
            audit_seconds = perf_counter() - started
            predicted = {
                name: solved.values[model.state_to_cell[source]]
                for name, source in zip(closure.root_names, closure.model.roots, strict=True)
            }
            exact_roots = {
                name: audited.root_metrics[source]
                for name, source in zip(closure.root_names, closure.model.roots, strict=True)
            }
            predicted_metrics = {
                name: forecast.root_metrics[model.state_to_cell[source]]
                for name, source in zip(closure.root_names, closure.model.roots, strict=True)
            }
            query_results[model_name] = {
                "predicted_root_objective": predicted,
                "predicted_root_metrics": predicted_metrics,
                "predicted_equal_root_mean": forecast.aggregate,
                "exact_lifted_root_metrics": exact_roots,
                "exact_lifted_equal_root_mean": audited.aggregate,
                "root_prediction_absolute_errors": {
                    name: {
                        metric: abs(predicted_metrics[name][metric] - exact_roots[name][metric])
                        for metric in ("reward", "failure", "success", "value")
                    }
                    for name in closure.root_names
                },
                "root_actions": {
                    name: solved.policy.get(model.state_to_cell[source])
                    for name, source in zip(closure.root_names, closure.model.roots, strict=True)
                },
                "planning_counts": solved.counts,
                "planning_seconds": planning_seconds,
                "compiled_policy_evaluation_counts": forecast.counts,
                "compiled_policy_evaluation_seconds": forecast_evaluation_seconds,
                "ground_audit_counts": audited.counts,
                "ground_audit_seconds": audit_seconds,
                "recovery_calls": 0,
            }
        ground = query_results["exact_ground"]["exact_lifted_equal_root_mean"]
        for metrics in query_results.values():
            metrics["exact_objective_gap_to_ground"] = (
                ground["value"] - metrics["exact_lifted_equal_root_mean"]["value"]
            )
        results[query_name] = {"query": asdict(query), "models": query_results}

    started = perf_counter()
    relabeled, relabel = _reverse_labels(empirical)
    relabeled_compiled = build_quotient(
        relabeled, reward_tolerance=reward_tolerance, tv_tolerance=tv_tolerance
    )
    inverse = {new: original for original, new in relabel.items()}
    original_partition = {
        frozenset(cell.members) for cell in compiled["learned_controlled_quotient"].cells.values()
    }
    relabeled_partition = {
        frozenset(inverse[state] for state in cell.members)
        for cell in relabeled_compiled.cells.values()
    }
    relabel_errors = {}
    for query_name, query in DEVELOPMENT_QUERIES.items():
        solution = plan(relabeled_compiled, query=query)
        original_prediction = results[query_name]["models"]["learned_controlled_quotient"]["predicted_root_objective"]
        relabel_errors[query_name] = max(
            abs(solution.values[relabeled_compiled.state_to_cell[relabel[source]]] - original_prediction[name])
            for name, source in zip(closure.root_names, closure.model.roots, strict=True)
        )
    relabel_seconds = perf_counter() - started

    return {
        "schema": "acfqp.controlled_predictive_2048_development.v1",
        "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "method": "empirical action-conditioned reward/kernel partition with compiled quotient planning",
        "settings": {
            "horizon": horizon,
            "max_nodes": max_nodes,
            "samples_per_row": samples_per_row,
            "seed": seed,
            "reward_tolerance": reward_tolerance,
            "tv_tolerance": tv_tolerance,
            "reward_units": "merge score / 2048",
        },
        "public_development_boards_rank_encoding": PUBLIC_DEVELOPMENT_BOARDS,
        "coverage": {
            **closure.counts,
            "complete_all_legal_actions_and_outcomes": True,
            "status_counts": dict(Counter(closure.model.terminal.values())),
            "root_legal_actions": {
                name: [action.value for action in legal_actions_v1(board)]
                for name, board in PUBLIC_DEVELOPMENT_BOARDS.items()
            },
        },
        "construction": {
            "exact_closure_seconds": closure.elapsed_seconds,
            "exact_closure_engine_row_calls": len(closure.model.rows),
            "exact_closure_outcomes_enumerated": closure.counts["exact_outcomes_enumerated"],
            "sampling_seconds": sample_seconds,
            "shared_empirical_draws": len(closure.model.rows) * samples_per_row,
            "shared_empirical_rows": len(empirical.rows),
            "models": inventories,
            "accounting_note": "Exact coverage enumeration, shared sampling, model construction, inventory serialization, all-cell per-query optimization, compiled-policy metric evaluation, and exact ground audits are separate costs. No scalar total-economics claim is made.",
        },
        "queries": results,
        "controls": {
            "action_outcome_shuffle": "Within-state action labels receive permuted empirical outcome rows; same samples and action set, action semantics disrupted.",
            "semantic_relabel": {
                "operation": "reverse state IDs and insertion order without changing any transition semantics",
                "partition_invariant": original_partition == relabeled_partition,
                "max_root_prediction_absolute_error": relabel_errors,
                "elapsed_seconds_including_refit_and_three_queries": relabel_seconds,
            },
        },
        "limitations": [
            "Three hand-written dense public boards and a finite horizon are development support only; they do not represent the standard initial-board distribution or full games.",
            "Every legal action row in the covered closure is sampled. The encoder is a covered-state lookup; there is no held-out-state or learned-encoder generalization result.",
            "Exact enumeration supplies coverage and evaluation; the oracle exact quotient is a privileged diagnostic, not an information-matched learned baseline.",
            "The action shuffle also changes the planning model and is a destructive control, not a competitive planner.",
            "Risk penalties are scalarized objectives, not hard chance constraints. Active states at the horizon are cutoff states, not losses.",
            "Recovery is not integrated; zero recovery calls is an architectural fact, not evidence of recovery efficiency.",
            "This result does not change the frozen failed representation experiment or authorize assurance execution.",
        ],
    }


__all__ = (
    "DEVELOPMENT_QUERIES",
    "PUBLIC_DEVELOPMENT_BOARDS",
    "DevelopmentClosure",
    "build_development_closure",
    "run_development",
)
