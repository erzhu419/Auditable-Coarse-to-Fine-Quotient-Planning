"""All-state development audit for the query-consequence refinement.

The fit bank participates in empirical partition construction. Probe queries
reuse the resulting dynamics without participating in refinement. Exact
dynamics audit the frozen lifted policies and never enter fitting.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from itertools import combinations
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from acfqp.science.controlled_predictive_2048_challenges_v2 import FAMILIES, _source_board
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure, _compiled_inventory, build_development_closure
from acfqp.science.controlled_predictive_comparison_v2 import COMPARISON_QUERIES, SAMPLE_SEEDS, optimal_action_set
from acfqp.science.controlled_predictive_quotient_v1 import (
    CompiledModel, FiniteModel, Plan, Query, _actions, _evaluate_policy,
    action_outcome_shuffle, build_quotient, compile_full_state, plan, sample_model,
)
from acfqp.science.controlled_predictive_refinement_v3 import build_refined_quotient
from acfqp.science.controlled_predictive_model_io_v3 import compiled_to_payload


PROBE_QUERIES = {
    "probe_risk_0_1": Query(1.0, 0.1, 0.0),
    "probe_risk_0_5": Query(1.0, 0.5, 0.0),
    "probe_risk_2": Query(1.0, 2.0, 0.0),
    "probe_goal_2_risk_0_5": Query(1.0, 0.5, 2.0),
}
DEVELOPMENT_SEEDS = (835101, 835201, 835301, 835401)
NUMERIC_TOLERANCE = 1e-10
COMPONENTS = ("reward", "failure", "success", "value")


@dataclass(frozen=True)
class RefinementCase:
    name: str
    group: str
    split: str
    board: tuple[int, ...]
    family: str
    seed: int
    horizon: int


def refinement_cases() -> tuple[RefinementCase, ...]:
    exposed = RefinementCase(
        "exposed_left_successor_7", "discovery_cross_axis_pairs_830011",
        "EXPOSED_REGRESSION", (3, 7, 9, 0, 7, 9, 6, 1, 8, 4, 9, 0, 1, 9, 8, 2),
        "exposed_reached_decision_point", 830011, 2,
    )
    return (exposed, *(RefinementCase(
        f"v3_{family}_{seed + index}", f"v3_{family}_{seed + index}",
        "NEW_DEVELOPMENT", _source_board(family, seed + index), family, seed + index, 3,
    ) for index, family in enumerate(FAMILIES) for seed in DEVELOPMENT_SEEDS))


def _reference(closure: DevelopmentClosure, compiled: CompiledModel,
               queries: Mapping[str, Query]) -> dict[str, dict[str, Any]]:
    actions = _actions(closure.model)
    references = {}
    for name, query in queries.items():
        started = perf_counter()
        solution = plan(compiled, query)
        planning_seconds = perf_counter() - started
        started = perf_counter()
        values = {state: solution.values[compiled.state_to_cell[state]] for state in closure.model.layers}
        q_values = {state: {
            action: math.fsum(outcome.probability * (query.reward_weight * outcome.reward + values[outcome.next_state])
                              for outcome in closure.model.rows[state, action])
            for action in legal
        } for state, legal in actions.items()}
        references[name] = {
            "solution": solution, "planning_seconds": planning_seconds, "values": values,
            "optimal_actions": {state: optimal_action_set(row) for state, row in q_values.items()},
            "root_q_values": q_values[closure.model.roots[0]],
            "all_state_action_labeling_seconds": perf_counter() - started,
            "all_state_action_labeling_counts": {"state_action_rows": len(closure.model.rows),
                "outcomes": sum(map(len, closure.model.rows.values()))},
        }
    return references


def _switches(references: Mapping[str, dict[str, Any]], states: Sequence[int],
              query_groups: Mapping[str, Sequence[str]],
              policies: Mapping[str, dict[int, str]] | None = None) -> dict[str, Any]:
    result = {}
    for group, names in query_groups.items():
        pair_count = state_count = preserved_pairs = preserved_states = 0
        for state in states:
            pairs = [(left, right) for left, right in combinations(names, 2)
                     if set(references[left]["optimal_actions"][state]).isdisjoint(
                         references[right]["optimal_actions"][state])]
            pair_count += len(pairs)
            state_count += bool(pairs)
            if policies is not None and pairs:
                kept = sum(
                    policies[left][state] in references[left]["optimal_actions"][state]
                    and policies[right][state] in references[right]["optimal_actions"][state]
                    and policies[left][state] != policies[right][state]
                    for left, right in pairs
                )
                preserved_pairs += kept
                preserved_states += kept == len(pairs)
        result[group] = {"required_state_query_pair_count": pair_count,
                         "states_with_required_switch": state_count}
        if policies is not None:
            result[group].update(preserved_state_query_pair_count=preserved_pairs,
                                 states_preserving_all_required_switches=preserved_states,
                                 all_required_switches_preserved=(preserved_pairs == pair_count if pair_count else None))
    return result


def _evaluate(compiled: CompiledModel, closure: DevelopmentClosure, query: Query,
              reference: Mapping[str, Any], active: tuple[int, ...],
              supplied_plan: tuple[Plan, float] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    started = perf_counter()
    solution = plan(compiled, query) if supplied_plan is None else supplied_plan[0]
    planning_seconds = perf_counter() - started if supplied_plan is None else supplied_plan[1]
    started = perf_counter()
    predicted = _evaluate_policy({cell: row.terminal for cell, row in compiled.cells.items()},
        compiled.rows, tuple(compiled.cells), solution.policy, query)
    forecast_seconds = perf_counter() - started
    started = perf_counter()
    lifted = {state: solution.policy[compiled.state_to_cell[state]] for state in active}
    actual = _evaluate_policy(closure.model.terminal, closure.model.rows,
        tuple(closure.model.layers), lifted, query)
    audit_seconds = perf_counter() - started
    errors = {state: {component: abs(predicted.root_metrics[compiled.state_to_cell[state]][component]
                                     - actual.root_metrics[state][component])
                      for component in COMPONENTS} for state in active}
    regrets = {state: reference["values"][state] - actual.root_metrics[state]["value"] for state in active}
    action_optimal = {state: lifted[state] in reference["optimal_actions"][state] for state in active}
    worst = max(active, key=lambda state: regrets[state])
    root = closure.model.roots[0]
    row = {
        "root_action": lifted[root], "root_action_in_exact_optimal_set": action_optimal[root],
        "predicted_root_metrics": predicted.root_metrics[compiled.state_to_cell[root]],
        "exact_lifted_root_metrics": actual.root_metrics[root],
        "exact_lifted_objective_regret": regrets[root], "root_prediction_absolute_errors": errors[root],
        "all_active_states": {
            "state_count": len(active), "exact_optimal_action_count": sum(action_optimal.values()),
            "optimal_full_policy_count": sum(regret <= NUMERIC_TOLERANCE for regret in regrets.values()),
            "mean_exact_lifted_objective_regret": math.fsum(regrets.values()) / len(active),
            "maximum_exact_lifted_objective_regret": max(regrets.values()),
            "maximum_prediction_absolute_errors": {component: max(row[component] for row in errors.values()) for component in COMPONENTS},
            "worst_regret_witness": {"state": worst, "board": closure.boards[worst],
                "remaining_horizon": closure.model.layers[worst], "action": lifted[worst],
                "exact_optimal_actions": reference["optimal_actions"][worst],
                "exact_optimal_value": reference["values"][worst],
                "exact_lifted_metrics": actual.root_metrics[worst],
                "regret": regrets[worst]},
        },
        "planning_seconds": planning_seconds, "planning_counts": solution.counts,
        "all_cell_forecast_seconds": forecast_seconds, "all_cell_forecast_counts": predicted.counts,
        "all_state_ground_audit_seconds": audit_seconds, "all_state_ground_audit_counts": actual.counts,
        "recovery_calls": 0,
    }
    return row, {"policy": lifted, "actual": actual.root_metrics, "regrets": regrets}


def _fit(builder: Callable[[], Any], closure: DevelopmentClosure, *, refined: bool = False
         ) -> tuple[CompiledModel, dict[str, Any], dict[str, Any] | None]:
    started = perf_counter()
    result = builder()
    construction_seconds = perf_counter() - started
    compiled = result.compiled if refined else result
    started = perf_counter()
    inventory = _compiled_inventory(compiled, closure)
    inventory.update(construction_seconds=construction_seconds,
                     inventory_serialization_seconds=perf_counter() - started,
                     active_state_compression_factor=closure.counts["active_states"] / inventory["active_cells"])
    return compiled, inventory, result.diagnostics if refined else None


def _arm(compiled: CompiledModel, inventory: dict[str, Any], closure: DevelopmentClosure,
         queries: Mapping[str, Query], references: Mapping[str, Any], groups: Mapping[str, Sequence[str]],
         *, sampling_seconds: float, privileged: bool, diagnostics: dict[str, Any] | None = None,
         supplied_plans: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
    rows, private = {}, {}
    for name, query in queries.items():
        supplied = (references[name]["solution"], references[name]["planning_seconds"]) if supplied_plans else None
        rows[name], private[name] = _evaluate(compiled, closure, query, references[name], active, supplied)
    workloads = []
    for count in sorted({1, len(groups["FIT_BANK"]), len(queries)}):
        prefix = list(rows.values())[:count]
        planning = math.fsum(row["planning_seconds"] for row in prefix)
        forecasting = math.fsum(row["all_cell_forecast_seconds"] for row in prefix)
        auditing = math.fsum(row["all_state_ground_audit_seconds"] for row in prefix)
        counted = {}
        for field in ("planning_counts", "all_cell_forecast_counts", "all_state_ground_audit_counts"):
            counter: Counter[str] = Counter()
            for row in prefix:
                counter.update(row[field])
            counted[field] = dict(counter)
        workloads.append({"query_count": count, "query_names": list(queries)[:count],
            "shared_exact_closure_seconds": closure.elapsed_seconds,
            "shared_sampling_seconds": sampling_seconds,
            "one_time_construction_seconds_including_refinement": inventory["construction_seconds"],
            "cumulative_planning_seconds": planning, "cumulative_forecast_seconds": forecasting,
            "cumulative_ground_audit_seconds": auditing, "cumulative_counts": counted,
            "construction_plus_planning_seconds": inventory["construction_seconds"] + planning,
            "including_shared_closure_sample_build_plan_forecast_audit_seconds": (
                closure.elapsed_seconds + sampling_seconds + inventory["construction_seconds"] + planning + forecasting + auditing),
        })
    return {"privileged_exact_dynamics": privileged, "model_build_count": 1,
        "query_count_using_same_compiled_model": len(queries), "inventory": inventory,
        "refinement_diagnostics": diagnostics, "queries": rows,
        "all_state_required_switches": _switches(references, active, groups,
            {name: row["policy"] for name, row in private.items()}),
        "root_required_switches": _switches(references, closure.model.roots, groups,
            {name: row["policy"] for name, row in private.items()}),
        "measured_cumulative_workloads": workloads}, private


def _summarize(records: Sequence[dict[str, Any]], groups: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    completed = [record for record in records if record["status"] == "COMPLETE"]
    arms: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in completed:
        for name, arm in record["references"].items():
            arms[name].append(arm)
        for sampled in record["sampled_runs"]:
            for name, arm in sampled["arms"].items():
                arms[name].append(arm)
    summaries = {}
    for name, runs in arms.items():
        group_summaries = {}
        for group, names in groups.items():
            rows = [run["queries"][query_name] for run in runs for query_name in names]
            state_count = sum(row["all_active_states"]["state_count"] for row in rows)
            group_summaries[group] = {
                "query_evaluation_count": len(rows), "state_query_evaluation_count": state_count,
                "root_exact_optimal_action_count": sum(row["root_action_in_exact_optimal_set"] for row in rows),
                "root_optimal_full_policy_count": sum(row["exact_lifted_objective_regret"] <= NUMERIC_TOLERANCE for row in rows),
                "maximum_root_regret": max(row["exact_lifted_objective_regret"] for row in rows),
                "maximum_all_state_regret": max(row["all_active_states"]["maximum_exact_lifted_objective_regret"] for row in rows),
                "mean_state_regret_with_equal_case_seed_query_weight": math.fsum(
                    row["all_active_states"]["mean_exact_lifted_objective_regret"] for row in rows) / len(rows),
                "all_state_exact_optimal_action_count": sum(row["all_active_states"]["exact_optimal_action_count"] for row in rows),
                "all_state_optimal_full_policy_count": sum(row["all_active_states"]["optimal_full_policy_count"] for row in rows),
                "maximum_all_state_prediction_errors": {component: max(
                    row["all_active_states"]["maximum_prediction_absolute_errors"][component] for row in rows) for component in COMPONENTS},
                "required_state_query_pairs": sum(run["all_state_required_switches"][group]["required_state_query_pair_count"] for run in runs),
                "preserved_state_query_pairs": sum(run["all_state_required_switches"][group]["preserved_state_query_pair_count"] for run in runs),
                "states_with_required_switch": sum(run["all_state_required_switches"][group]["states_with_required_switch"] for run in runs),
                "states_preserving_all_required_switches": sum(run["all_state_required_switches"][group]["states_preserving_all_required_switches"] for run in runs),
            }
        summaries[name] = {"case_seed_run_count": len(runs), "query_groups": group_summaries,
            "mean_active_cells": math.fsum(run["inventory"]["active_cells"] for run in runs) / len(runs),
            "mean_active_state_compression_factor": math.fsum(run["inventory"]["active_state_compression_factor"] for run in runs) / len(runs),
            "mean_construction_seconds": math.fsum(run["inventory"]["construction_seconds"] for run in runs) / len(runs),
            "mean_full_query_workload_seconds": math.fsum(run["measured_cumulative_workloads"][-1][
                "including_shared_closure_sample_build_plan_forecast_audit_seconds"] for run in runs) / len(runs),
        }
    return {"declared_case_count": len(records), "source_group_count": len({record["case"]["group"] for record in records}),
        "status_counts": dict(Counter(record["status"] for record in records)), "completed_case_count": len(completed),
        "arms": summaries}


def run_refinement_comparison(*, cases: Sequence[RefinementCase] | None = None,
        fit_queries: Mapping[str, Query] | None = None, probe_queries: Mapping[str, Query] | None = None,
        samples_per_row: int = 64, sample_seeds: Sequence[int] = SAMPLE_SEEDS, max_nodes: int = 30_000,
        progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    fixtures = tuple(refinement_cases() if cases is None else cases)
    fit_bank = dict(COMPARISON_QUERIES if fit_queries is None else fit_queries)
    probes = dict(PROBE_QUERIES if probe_queries is None else probe_queries)
    if not fixtures or not fit_bank or not sample_seeds:
        raise ValueError("cases, fit queries, and sample seeds must be nonempty")
    if set(fit_bank) & set(probes):
        raise ValueError("fit and probe query names must be disjoint")
    if len({case.name for case in fixtures}) != len(fixtures) or len(set(sample_seeds)) != len(sample_seeds):
        raise ValueError("case names and sample seeds must be unique")
    queries = {**fit_bank, **probes}
    groups = {"FIT_BANK": tuple(fit_bank), **({"PROBES": tuple(probes)} if probes else {}), "ALL": tuple(queries)}
    started_all = perf_counter()
    records = []
    compiled_model_example = None
    board_owners: dict[tuple[int, ...], set[str]] = defaultdict(set)
    root_owners: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for case in fixtures:
        root_owners[case.board].add(case.name)
        started_case = perf_counter()
        record: dict[str, Any] = {"case": asdict(case)}
        try:
            closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes, boards={case.name: case.board})
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            record.update(status="CLOSURE_BUDGET_EXCEEDED", reason=str(error), elapsed_seconds=perf_counter() - started_case)
            records.append(record)
            if progress:
                progress({"case": case.name, "status": record["status"], "completed": len(records), "total": len(fixtures)})
            continue
        for board in set(closure.boards.values()):
            board_owners[board].add(case.name)
        active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
        record["coverage"] = {**closure.counts, "exact_closure_seconds": closure.elapsed_seconds,
            "complete_all_legal_actions_and_outcomes": True, "unique_boards_excluding_horizon": len(set(closure.boards.values()))}
        exact, inventory, _ = _fit(lambda: compile_full_state(closure.model), closure)
        references = _reference(closure, exact, queries)
        root = closure.model.roots[0]
        record["exact_query_references"] = {name: {"root_q_values": row["root_q_values"],
            "root_optimal_actions": row["optimal_actions"][root], "root_optimal_value": row["values"][root],
            "all_state_action_labeling_seconds": row["all_state_action_labeling_seconds"],
            "all_state_action_labeling_counts": row["all_state_action_labeling_counts"]} for name, row in references.items()}
        record["exact_all_state_required_switches"] = _switches(references, active, groups)
        record["exact_root_required_switches"] = _switches(references, closure.model.roots, groups)
        record["references"] = {"exact_ground": _arm(exact, inventory, closure, queries, references, groups,
            sampling_seconds=0, privileged=True, supplied_plans=True)[0]}
        oracle, inventory, _ = _fit(lambda: build_quotient(closure.model), closure)
        record["references"]["oracle_exact_quotient"] = _arm(oracle, inventory, closure, queries, references, groups,
            sampling_seconds=0, privileged=True)[0]
        record["sampled_runs"] = []
        for seed in sample_seeds:
            started = perf_counter()
            empirical = sample_model(closure.model, samples_per_row=samples_per_row, seed=seed)
            sampling_seconds = perf_counter() - started
            sample_run: dict[str, Any] = {"sample_seed": seed, "sampling_seconds": sampling_seconds,
                "empirical_draws": len(empirical.rows) * samples_per_row, "empirical_rows": len(empirical.rows),
                "empirical_model_sample_count": 1, "arms": {}}
            private = {}
            builders = {
                "full_state_empirical": (lambda: compile_full_state(empirical), False),
                "old_tolerance_quotient": (lambda: build_quotient(empirical, reward_tolerance=0.01, tv_tolerance=0.2), False),
                "query_refined_quotient": (lambda: build_refined_quotient(empirical, fit_bank, numeric_tolerance=NUMERIC_TOLERANCE), True),
                "action_shuffle_refined_quotient": (lambda: build_refined_quotient(action_outcome_shuffle(empirical), fit_bank,
                    numeric_tolerance=NUMERIC_TOLERANCE), True),
            }
            for name, (builder, refined) in builders.items():
                compiled, inventory, diagnostics = _fit(builder, closure, refined=refined)
                if name == "query_refined_quotient" and case.name == "exposed_left_successor_7" and seed == 832101:
                    started = perf_counter()
                    compiled_model_example = {"case_name": case.name, "sample_seed": seed,
                        "model": compiled_to_payload(compiled)}
                    compiled_model_example["report_payload_serialization_seconds"] = perf_counter() - started
                sample_run["arms"][name], private[name] = _arm(compiled, inventory, closure, queries, references, groups,
                    sampling_seconds=sampling_seconds, privileged=False, diagnostics=diagnostics)
            sample_run["matched_comparisons"] = {}
            for query_name in queries:
                full = private["full_state_empirical"][query_name]["actual"]
                candidate = private["query_refined_quotient"][query_name]["actual"]
                old = private["old_tolerance_quotient"][query_name]["actual"]
                shuffle = private["action_shuffle_refined_quotient"][query_name]["actual"]
                extra = {state: full[state]["value"] - candidate[state]["value"] for state in active}
                sample_run["matched_comparisons"][query_name] = {
                    "root_refined_extra_regret_over_full_state": extra[root],
                    "maximum_all_state_refined_extra_regret_over_full_state": max(extra.values()),
                    "mean_all_state_refined_extra_regret_over_full_state": math.fsum(extra.values()) / len(active),
                    "root_refined_actual_value_gain_over_old": candidate[root]["value"] - old[root]["value"],
                    "root_refined_actual_value_gain_over_shuffle": candidate[root]["value"] - shuffle[root]["value"],
                }
            record["sampled_runs"].append(sample_run)
            if progress:
                progress({"case": case.name, "sample_seed": seed, "status": "SAMPLE_COMPLETE",
                    "active_states": len(active), "refined_active_cells": sample_run["arms"]["query_refined_quotient"]["inventory"]["active_cells"]})
        record.update(status="COMPLETE", elapsed_seconds=perf_counter() - started_case)
        records.append(record)
        if progress:
            progress({"case": case.name, "status": "COMPLETE", "completed": len(records), "total": len(fixtures),
                "states": len(closure.model.layers), "elapsed_seconds": record["elapsed_seconds"]})
    case_by_name = {case.name: case for case in fixtures}
    overlaps = []
    for left, right in combinations(fixtures, 2):
        common = [board for board, owners in board_owners.items() if {left.name, right.name} <= owners]
        if common:
            overlaps.append({"left": left.name, "right": right.name, "board_count": len(common), "examples": sorted(common)[:1]})
    return {
        "schema": "acfqp.controlled_predictive_refinement_comparison.v3", "scientific_gate": "NOT_A_FORMAL_GATE",
        "status": "DEVELOPMENT_COMPLETE" if all(row["status"] == "COMPLETE" for row in records) else "DEVELOPMENT_COMPLETE_WITH_CLOSURE_EXCLUSIONS",
        "settings": {"fit_queries": {name: asdict(query) for name, query in fit_bank.items()},
            "probe_queries": {name: asdict(query) for name, query in probes.items()}, "query_order": list(queries),
            "sample_seeds": list(sample_seeds), "samples_per_row": samples_per_row,
            "max_nodes": max_nodes, "numeric_tolerance": NUMERIC_TOLERANCE,
            "initial_reward_tolerance": 0.01, "initial_tv_tolerance": 0.2, "reward_units": "merge score / 2048"},
        "case_count": len(fixtures), "all_declared_candidates_retained": True, "cases": records,
        "compiled_model_example": compiled_model_example,
        "summary_by_split": {split: _summarize(records if split == "ALL" else [row for row in records if row["case"]["split"] == split], groups)
            for split in ("ALL", *sorted({case.split for case in fixtures}))},
        "summary_by_source_group": {group: _summarize([row for row in records if row["case"]["group"] == group], groups)
            for group in sorted({case.group for case in fixtures})},
        "board_identity_overlap_excluding_horizon": {
            "scope": "Only this declared cohort's completed closures, including the exposed regression; historical V1 and 36-case discovery closures are not reconstructed for this overlap count.",
            "unique_covered_boards": len(board_owners), "root_overlap_count": sum(len(owners) > 1 for owners in root_owners.values()),
            "cross_case_covered_board_count": sum(len(owners) > 1 for owners in board_owners.values()),
            "new_and_exposed_covered_board_count": sum(
                {case_by_name[name].split for name in owners} >= {"NEW_DEVELOPMENT", "EXPOSED_REGRESSION"}
                for owners in board_owners.values()),
            "nonempty_pairwise_overlaps": overlaps, "unseen_state_generalization_demonstrated": False},
        "original_deferred_24_case_cohort_executed": False, "elapsed_seconds": perf_counter() - started_all,
        "accounting": {
            "fitting": "Only the six-query bank participates in empirical construction. The compiled dynamics are built once and reused for every bank and probe query.",
            "matching": "One sampled kernel per case/seed is shared by full state, old quotient and refined quotient. The shuffle arm refines its action-shuffled empirical kernel, then receives the same unshuffled exact external audit.",
            "audit": "Every covered active state is treated as an audit start. Each cell policy is frozen before exact evaluation; only the exact reference optimizes ground continuation. State averages are unweighted descriptive measures, not root visitation probabilities.",
            "costs": "Model construction includes every refinement round and its internal empirical planning/auditing. Separate timings charge all-cell planning, all-cell component forecasting, and all-state exact policy auditing. Exact action labeling and report-only inventory serialization are reported separately. Cumulative workloads include one model construction; execution uses registered state IDs.",
            "units": "Source groups identify constructed boards. Sampling seeds, queries and covered states are repeated measurements rather than independent replications. Split summaries weight case/seed/query means equally; source summaries are also retained.",
        },
        "limitations": [
            "Exploratory finite-board development only; no confidence interval, confirmatory Gate, full-game, or independent validation claim.",
            "The partition is query-aware at construction. Bank checks concern the empirical kernel; they do not certify true transition probabilities or arbitrary query weights.",
            "Probe queries use the same covered states and empirical model; this does not establish transfer to unseen boards or a learned online encoder.",
            "All-state counts include alternative-action branches and repeated horizon-indexed states, not independent cases or natural-play frequency.",
            "Risk penalties are soft scalar objectives. Horizon cutoff is not failure. Measured workload excludes online board encoding and fresh-process loading.",
            "U005 remains scientifically failed. U006 and the original deferred challenge cohort are not executed.",
        ],
    }


__all__ = ("RefinementCase", "PROBE_QUERIES", "DEVELOPMENT_SEEDS", "refinement_cases", "run_refinement_comparison")
