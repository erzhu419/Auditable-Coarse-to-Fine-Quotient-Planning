"""Persistent interval updates and history-dependent execution on the fixed roots.

No source prior is trained. Independent full and incremental planners share
only the declared observations within their own 32-row prefix and descendants.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from time import perf_counter
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import DevelopmentClosure, build_development_closure
from .controlled_predictive_cohort_v7 import V7Case
from .controlled_predictive_cohort_v13 import build_cohort_roster_v13, cases_v13
from .controlled_predictive_comparison_v3 import (
    COMPARISON_QUERIES, PROBE_QUERIES, SAMPLE_SEEDS, COMPONENTS, NUMERIC_TOLERANCE, _reference,
)
from .controlled_predictive_comparison_v12 import _acquire_complete, _full_arms
from .controlled_predictive_incremental_v13 import PlannerState
from .controlled_predictive_partial_v12 import RowSampleProvider
from .controlled_predictive_partial_io_v12 import freeze_policy_payload
from .controlled_predictive_execution_v13 import ExactEnvironment, evaluate_execution, evaluate_frozen_policy
from .controlled_predictive_quotient_v1 import Query, compile_full_state

UPDATE_MODES = ("full_recompute", "incremental")
EXECUTION_MODES = ("upfront", "online")
PREFIX_BUDGETS = (32, 128)
TOTAL_ROW_CAP = 128
SAMPLES_PER_ROW = 256


def _method_id(mode: str, update: str) -> str:
    return f"{mode}_{'full' if update == 'full_recompute' else 'incremental'}"


@dataclass
class PrefixSnapshot:
    state: Any
    policy: Any
    intervals: Any
    report: dict[str, Any]


def _stage_a(root: Any, seed: int, queries: Mapping[str, Query], update_mode: str,
             budgets: Sequence[int], samples_per_row: int) -> tuple[dict[int, PrefixSnapshot], dict[str, Any]]:
    """Measure one independent trajectory and preserve a branch-safe warm prefix."""
    started = perf_counter()
    provider = RowSampleProvider(seed, samples_per_row=samples_per_row)
    planner = PlannerState(root, queries, mode="query_interval", update_mode=update_mode)
    snapshots = {}
    for budget in budgets:
        while planner.stop_reason is None and len(planner.rows) < budget and planner.sample_next(provider):
            pass
        policy, intervals = planner.freeze()
        prefix_engine_seconds = planner.engine_seconds
        prefix_work = dict(planner.work_counts)
        state_copy = planner.clone()
        snapshot = PrefixSnapshot(state_copy, policy, intervals, {
            "row_budget": budget, "actual_rows_acquired": len(planner.rows),
            "physical_sample_draws_in_prefix": len(planner.rows) * samples_per_row,
            "provider_seconds": provider.provider_seconds, "provider_work_counts": dict(provider.work_counts),
            "engine_seconds_including_policy_freeze": prefix_engine_seconds,
            "prefix_acquisition_and_engine_seconds": provider.provider_seconds + prefix_engine_seconds,
            "prefix_clone_seconds": state_copy.clone_seconds,
            "warm_start_preparation_seconds": provider.provider_seconds + prefix_engine_seconds + state_copy.clone_seconds,
            "work_counts": prefix_work, "requested_row_order": list(planner.row_order),
            "stop_reason": planner.stop_reason or "ROW_BUDGET_REACHED",
            "root_intervals": {name: asdict(interval) for name, interval in intervals.items()},
        })
        snapshots[budget] = snapshot
    return snapshots, {"actual_trajectory_seconds": perf_counter() - started,
        "actual_rows_acquired": len(planner.rows), "physical_sample_draws": len(planner.rows) * samples_per_row,
        "provider_seconds": provider.provider_seconds, "provider_work_counts": dict(provider.work_counts),
        "engine_seconds": planner.engine_seconds, "prefix_cloning_seconds": math.fsum(s.report["prefix_clone_seconds"] for s in snapshots.values()),
        "work_counts": dict(planner.work_counts), "nested_prefixes_are_not_independent_acquisitions": True}


def _snapshot_payload(snapshot: PrefixSnapshot, root: Any, queries: Mapping[str, Query]) -> dict[str, Any]:
    cp = SimpleNamespace(budget=snapshot.report["row_budget"], known_rows=snapshot.state.rows,
        profiles=snapshot.state.profiles, frozen_policy=snapshot.policy, root_intervals=snapshot.intervals)
    return freeze_policy_payload(cp, queries, root)


def _compare_prefixes(full: PrefixSnapshot, incremental: PrefixSnapshot,
                      root: Any, queries: Mapping[str, Query]) -> dict[str, Any]:
    """Compare all retained numeric maps exactly after both independent timings."""
    started = perf_counter()
    checks = {"requested_rows": full.state.row_order == incremental.state.row_order,
        "sampled_rows": full.state.rows == incremental.state.rows,
        "profiles": full.state.profiles == incremental.state.profiles,
        "root_intervals": full.intervals == incremental.intervals,
        "frozen_policy_payload": _snapshot_payload(full, root, queries) == _snapshot_payload(incremental, root, queries)}
    query_checks = {name: {field: getattr(full.state.caches[name], field) == getattr(incremental.state.caches[name], field)
        for field in ("lower", "upper", "q_lower", "q_upper", "policy")} for name in queries}
    result = {"all_equal": all(checks.values()) and all(all(row.values()) for row in query_checks.values()),
        "field_equal": checks, "query_field_equal": query_checks,
        "exact_comparison_without_tolerance": True, "comparison_seconds": perf_counter() - started}
    if not result["all_equal"]:
        result["mismatch_payloads"] = {"full_recompute": _snapshot_payload(full, root, queries),
            "incremental": _snapshot_payload(incremental, root, queries)}
    return result


def _compare_executions(full: Mapping[str, Any], incremental: Mapping[str, Any]) -> dict[str, Any]:
    """Identical traces share storage only after independent execution is checked."""
    started = perf_counter()
    trace_equal = full["trace"] == incremental["trace"]
    metrics_equal = full["root_metrics"] == incremental["root_metrics"]
    result = {"all_equal": trace_equal and metrics_equal,
        "trace_including_observations_equal": trace_equal, "root_metrics_equal": metrics_equal,
        "exact_comparison_without_tolerance": True, "comparison_seconds": perf_counter() - started}
    if trace_equal:
        result["shared_trace"] = full["trace"]
    else:
        result["unequal_traces"] = {"full_recompute": full["trace"], "incremental": incremental["trace"]}
    return result


def _root_quality(result: Mapping[str, Any], reference: Mapping[str, Any], root: int,
                  full: Mapping[str, Any], case: V7Case, query_name: str, seed: int) -> dict[str, Any]:
    actual = result["root_metrics"]
    full_actual = full["root_metrics"]
    regret = reference["values"][root] - actual["value"]
    extra = full_actual["value"] - actual["value"]
    return {"root_action_in_exact_optimal_set": result["root_action"] in reference["optimal_actions"][root],
        "root_optimal_full_policy": regret <= NUMERIC_TOLERANCE,
        "root_exact_optimal_actions": reference["optimal_actions"][root],
        "root_exact_optimal_value": reference["values"][root],
        "root_regret": regret, "root_extra_regret_over_full_state": extra,
        "actual_component_difference_from_full_state": {component: actual[component] - full_actual[component] for component in COMPONENTS},
        "counterexample": {"case_name": case.name, "sample_seed": seed, "query_name": query_name, "board": case.board,
            "remaining_horizon": case.horizon, "action": result["root_action"], "actual_metrics": actual,
            "full_state_action": full["root_action"], "full_state_actual_metrics": full_actual,
            "root_regret": regret, "root_extra_regret_over_full_state": extra}}


def _attribute_execution(result: dict[str, Any], warm_seconds: float, query_count: int) -> None:
    deploy = result["deployment"]
    deploy.update(warm_prefix_preparation_seconds=warm_seconds,
        expected_standalone_seconds=warm_seconds + deploy["expected_suffix_seconds"],
        maximum_standalone_seconds=warm_seconds + deploy["maximum_suffix_seconds"],
        expected_batch_amortized_seconds=warm_seconds / query_count + deploy["expected_suffix_seconds"],
        maximum_batch_amortized_seconds=warm_seconds / query_count + deploy["maximum_suffix_seconds"],
        prefix_amortization_query_count=query_count,
        warm_source_cost_seconds=0.0)


def _method_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"query_context_count": 0}
    count = len(rows)
    worst = max(rows, key=lambda row: row["quality"]["root_extra_regret_over_full_state"])
    result = {"query_context_count": count,
        "root_optimal_first_action_count": sum(row["quality"]["root_action_in_exact_optimal_set"] for row in rows),
        "root_optimal_full_policy_count": sum(row["quality"]["root_optimal_full_policy"] for row in rows),
        "maximum_root_regret": max(row["quality"]["root_regret"] for row in rows),
        "maximum_root_extra_regret_over_full_state": max(row["quality"]["root_extra_regret_over_full_state"] for row in rows),
        "minimum_root_extra_regret_over_full_state": min(row["quality"]["root_extra_regret_over_full_state"] for row in rows),
        "mean_root_extra_regret_over_full_state": math.fsum(row["quality"]["root_extra_regret_over_full_state"] for row in rows) / count,
        "worse_than_full_state_count": sum(row["quality"]["root_extra_regret_over_full_state"] > NUMERIC_TOLERANCE for row in rows),
        "better_than_full_state_count": sum(row["quality"]["root_extra_regret_over_full_state"] < -NUMERIC_TOLERANCE for row in rows),
        "mean_root_metrics": {component: math.fsum(row["root_metrics"][component] for row in rows) / count for component in COMPONENTS},
        "worst_added_loss_counterexample": worst["quality"]["counterexample"]}
    for field in ("expected_total_rows", "maximum_total_rows", "expected_total_draws",
                  "expected_suffix_seconds", "expected_standalone_seconds", "expected_batch_amortized_seconds",
                  "maximum_standalone_seconds", "expected_decisions"):
        if field in rows[0]["deployment"]:
            result["mean_" + field] = math.fsum(row["deployment"][field] for row in rows) / count
    result["maximum_path_rows_over_contexts"] = max(row["deployment"]["maximum_total_rows"] for row in rows)
    event_names = set().union(*(row["deployment"]["expected_events"] for row in rows))
    result["mean_expected_events"] = {name: math.fsum(row["deployment"]["expected_events"].get(name, 0) for row in rows) / count for name in sorted(event_names)}
    result["mean_event_reach_probabilities"] = {name: math.fsum(row["deployment"]["event_probabilities"].get(name, 0) for row in rows) / count for name in sorted(event_names)}
    return result


def _summary(records: Sequence[Mapping[str, Any]], queries: Mapping[str, Query], budgets: Sequence[int]) -> dict[str, Any]:
    runs = [run for record in records for run in record["sampled_runs"] if run["status"] == "COMPLETE"]
    methods = ("full_state_empirical", "exact_empirical_quotient", "frozen32",
        *(_method_id(mode, update) for mode in EXECUTION_MODES for update in UPDATE_MODES))
    stage_a = {}
    for budget in budgets:
        stage_a[str(budget)] = {update: {
            "case_seed_count": len(runs),
            "mean_rows": math.fsum(run["stage_a"][update]["prefixes"][str(budget)]["actual_rows_acquired"] for run in runs) / len(runs) if runs else None,
            "mean_acquisition_and_engine_seconds": math.fsum(run["stage_a"][update]["prefixes"][str(budget)]["prefix_acquisition_and_engine_seconds"] for run in runs) / len(runs) if runs else None,
        } for update in UPDATE_MODES}
    return {"declared_case_count": len(records), "completed_case_seed_runs": len(runs),
        "query_context_count_per_method": len(runs) * len(queries), "stage_a": stage_a,
        "methods": {method: _method_summary([run["methods"][method][name] for run in runs for name in queries]) for method in methods}}


def run_comparison_v13(*, cases: Sequence[V7Case] | None = None,
                       cohort_roster: Mapping[str, Any] | None = None,
                       sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                       queries: Mapping[str, Query] | None = None,
                       samples_per_row: int = SAMPLES_PER_ROW,
                       prefix_budgets: Sequence[int] = PREFIX_BUDGETS,
                       total_row_cap: int = TOTAL_ROW_CAP,
                       max_nodes: int = 30_000,
                       progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    declared = tuple(cases_v13() if cases is None else cases)
    roster = build_cohort_roster_v13() if cohort_roster is None else cohort_roster
    queries = dict({**COMPARISON_QUERIES, **PROBE_QUERIES} if queries is None else queries)
    budgets = tuple(prefix_budgets)
    if not declared or not queries or not sample_seeds or len(budgets) != 2 or not 0 < budgets[0] < budgets[1] <= total_row_cap:
        raise ValueError("two increasing positive prefix budgets within the episode cap are required")
    started_all = perf_counter()
    records = [{"case": asdict(case), "sampled_runs": [], "status": "NOT_RUN"} for case in declared]
    closures, closure_records = {}, {}
    examples = []
    for case_index, (case, record) in enumerate(zip(declared, records)):
        root_key = (case.horizon, tuple(case.board))
        for seed_index, seed in enumerate(sample_seeds):
            a_order = UPDATE_MODES if (case_index + seed_index) % 2 == 0 else UPDATE_MODES[::-1]
            snapshots, stage_a = {}, {}
            for update in a_order:
                snapshots[update], trajectory = _stage_a(root_key, seed, queries, update, budgets, samples_per_row)
                stage_a[update] = {"trajectory": trajectory,
                    "prefixes": {str(budget): snapshot.report for budget, snapshot in snapshots[update].items()}}
                if progress:
                    progress({"case": case.name, "sample_seed": seed, "stage": "A", "update_mode": update,
                        "status": "PREFIXES_FROZEN", "rows": trajectory["actual_rows_acquired"]})
            a_checks = {str(budget): _compare_prefixes(snapshots["full_recompute"][budget], snapshots["incremental"][budget], root_key, queries) for budget in budgets}
            run = {"sample_seed": seed, "status": "STAGE_A_FROZEN", "stage_a_order": a_order,
                "stage_a": stage_a, "stage_a_semantic_comparisons": a_checks,
                "source_fits": 0, "source_setup_seconds": 0.0}
            record["sampled_runs"].append(run)
            if case.name not in closure_records:
                started = perf_counter()
                try:
                    closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes, boards={case.name: case.board})
                except ValueError as error:
                    if "complete closure exceeds max_nodes=" not in str(error):
                        raise
                    closure_records[case.name] = {"case_name": case.name, "status": "CLOSURE_BUDGET_EXCEEDED",
                        "reason": str(error), "seconds": perf_counter() - started}
                else:
                    closures[case.name] = closure
                    closure_records[case.name] = {"case_name": case.name, "status": "CLOSURE_COMPLETE",
                        "seconds": closure.elapsed_seconds, "coverage": closure.counts}
            if case.name not in closures:
                run["status"] = record["status"] = "CLOSURE_BUDGET_EXCEEDED"
                continue
            closure = closures[case.name]
            started = perf_counter()
            environment = ExactEnvironment.from_closure(closure)
            environment_assembly_seconds = perf_counter() - started
            empirical, full_acquisition = _acquire_complete(closure, seed, samples_per_row)
            full_frozen = _full_arms(empirical, closure, queries)
            run.update(full_target_acquisition=full_acquisition, environment_assembly_seconds=environment_assembly_seconds,
                methods={method: {} for method in ("full_state_empirical", "exact_empirical_quotient", "frozen32",
                    *(_method_id(mode, update) for mode in EXECUTION_MODES for update in UPDATE_MODES))},
                stage_b_order_by_query={}, paired_execution_semantics={}, paired_method_differences={})
            key_to_state = {(closure.model.layers[state], board): state for state, board in closure.boards.items()}
            all_known_rows = {((closure.model.layers[state], closure.boards[state]), action) for state, action in empirical.rows}
            active_keys = {key for key, state in key_to_state.items() if closure.model.terminal[state] == "ACTIVE"}
            full_costs = {}
            for arm, (_, inventory, plans) in full_frozen.items():
                full_costs[arm] = {"inventory": inventory,
                    "compile_and_plan_seconds": inventory["construction_seconds"] + math.fsum(value[1] for value in plans.values()),
                    "whole_batch_preparation_seconds": closure.elapsed_seconds + full_acquisition["acquisition_and_model_assembly_seconds"] + inventory["construction_seconds"] + math.fsum(value[1] for value in plans.values())}
            run["full_benchmark_costs"] = full_costs
            raw_traces = {}
            for query_index, (name, query) in enumerate(queries.items()):
                query_results = {}
                b_order = [(mode, update) for mode in EXECUTION_MODES for update in UPDATE_MODES]
                offset = (case_index + seed_index + query_index) % len(b_order)
                b_order = b_order[offset:] + b_order[:offset]
                run["stage_b_order_by_query"][name] = [_method_id(mode, update) for mode, update in b_order]
                for mode, update in b_order:
                    warm = snapshots[update][budgets[0]]
                    provider = RowSampleProvider(seed, samples_per_row=samples_per_row)
                    result = evaluate_execution(warm.state, provider, name, environment, mode=mode, total_row_cap=total_row_cap)
                    _attribute_execution(result, warm.report["warm_start_preparation_seconds"], len(queries))
                    result["path_row_budget_satisfied"] = (result["deployment"]["expected_total_rows"] <= result["deployment"]["maximum_total_rows"] + NUMERIC_TOLERANCE
                        and result["deployment"]["maximum_total_rows"] <= total_row_cap)
                    query_results[_method_id(mode, update)] = result
                for mode in EXECUTION_MODES:
                    full = query_results[_method_id(mode, "full_recompute")]
                    incremental = query_results[_method_id(mode, "incremental")]
                    run["paired_execution_semantics"].setdefault(mode, {})[name] = _compare_executions(full, incremental)
                    if mode == "online":
                        raw_traces[name] = incremental["trace"]
                for method, result in query_results.items():
                    run["methods"][method][name] = {key: value for key, value in result.items() if key != "trace"}
                warm = snapshots["incremental"][budgets[0]]
                frozen_result = evaluate_frozen_policy(root_key, query, lambda key, n=name: warm.policy.action(key, n), environment,
                    known_rows=warm.state.rows, known_policy_keys=warm.policy.policies[name], initial_rows=len(warm.state.rows))
                _attribute_execution(frozen_result, warm.report["warm_start_preparation_seconds"], len(queries))
                frozen_result.pop("trace")
                frozen_result["prefix_update_mode"] = "incremental"
                run["methods"]["frozen32"][name] = frozen_result
                for arm, (compiled, inventory, plans) in full_frozen.items():
                    solution = plans[name][0]
                    result = evaluate_frozen_policy(root_key, query,
                        lambda key, sol=solution, model=compiled: sol.policy[model.state_to_cell[key_to_state[key]]],
                        environment, known_rows=all_known_rows, known_policy_keys=active_keys, initial_rows=len(empirical.rows))
                    preparation = closure.elapsed_seconds + full_acquisition["acquisition_and_model_assembly_seconds"] + inventory["construction_seconds"]
                    result["deployment"].update(
                        expected_standalone_seconds=preparation + plans[name][1] + result["deployment"]["expected_suffix_seconds"],
                        maximum_standalone_seconds=preparation + plans[name][1] + result["deployment"]["maximum_suffix_seconds"],
                        expected_batch_amortized_seconds=preparation / len(queries) + plans[name][1] + result["deployment"]["expected_suffix_seconds"],
                        prefix_amortization_query_count=len(queries),
                        budget_scope="ALL_ROWS_COST_AND_QUALITY_BENCHMARK")
                    result.pop("trace")
                    run["methods"][arm][name] = result
                if progress:
                    progress({"case": case.name, "sample_seed": seed, "query": name, "stage": "B",
                        "status": "EXECUTION_TREES_FROZEN"})
            # True optimal labels are unavailable until every history tree is fixed.
            started = perf_counter()
            ground = compile_full_state(closure.model)
            ground_compile_seconds = perf_counter() - started
            references = _reference(closure, ground, queries)
            run["exact_reference_cost"] = {"compile_seconds": ground_compile_seconds,
                "planning_seconds": math.fsum(row["planning_seconds"] for row in references.values()),
                "labeling_seconds": math.fsum(row["all_state_action_labeling_seconds"] for row in references.values())}
            root = closure.model.roots[0]
            for name in queries:
                full = run["methods"]["full_state_empirical"][name]
                for method in run["methods"]:
                    result = run["methods"][method][name]
                    result["quality"] = _root_quality(result, references[name], root, full, case, name, seed)
                run["paired_method_differences"][name] = {}
                for update in UPDATE_MODES:
                    online = run["methods"][_method_id("online", update)][name]
                    upfront = run["methods"][_method_id("upfront", update)][name]
                    frozen = run["methods"]["frozen32"][name]
                    run["paired_method_differences"][name][update] = {
                        "online_minus_upfront_root_components": {component: online["root_metrics"][component] - upfront["root_metrics"][component] for component in COMPONENTS},
                        "online_minus_frozen32_root_components": {component: online["root_metrics"][component] - frozen["root_metrics"][component] for component in COMPONENTS},
                        "online_minus_upfront_expected_rows": online["deployment"]["expected_total_rows"] - upfront["deployment"]["expected_total_rows"],
                        "online_minus_upfront_expected_standalone_seconds": online["deployment"]["expected_standalone_seconds"] - upfront["deployment"]["expected_standalone_seconds"]}
            if (case.name, seed) in (("v6_spawn_edge_rescue_2", 832101), ("v6_crossing_rescue_pair_3", 832102)):
                chosen = list(queries) if case.name == "v6_spawn_edge_rescue_2" else ["risk_5"]
                examples.append({"case_name": case.name, "sample_seed": seed, "method": "online_incremental",
                    "root": root_key, "queries": {name: asdict(queries[name]) for name in chosen},
                    "query_order": chosen, "traces": {name: raw_traces[name] for name in chosen},
                    "expected_root_metrics": {name: run["methods"]["online_incremental"][name]["root_metrics"] for name in chosen}})
            run["status"] = record["status"] = "COMPLETE"
    all_runs = [run for record in records for run in record["sampled_runs"]]
    completed = [run for run in all_runs if run["status"] == "COMPLETE"]
    a_trajectories = [run["stage_a"][update]["trajectory"] for run in all_runs for update in UPDATE_MODES]
    b_results = [run["methods"][_method_id(mode, update)][name] for run in completed for mode in EXECUTION_MODES for update in UPDATE_MODES for name in queries]
    all_results = [result for run in completed for rows in run["methods"].values() for result in rows.values()]
    a_checks = [check for run in all_runs for check in run["stage_a_semantic_comparisons"].values()]
    b_checks = [check for run in completed for rows in run["paired_execution_semantics"].values() for check in rows.values()]
    return {"schema": "acfqp.controlled_predictive_execution_acquisition.v13",
        "status": "DEVELOPMENT_COMPLETE" if len(completed) == len(declared) * len(sample_seeds) else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES",
        "scientific_gate": "NOT_A_FORMAL_GATE", "case_count": len(declared),
        "completed_case_seed_runs": len(completed), "query_contexts_per_method": len(completed) * len(queries),
        "settings": {"sample_seeds": list(sample_seeds), "samples_per_row": samples_per_row,
            "prefix_budgets": budgets, "total_row_cap": total_row_cap, "query_order": list(queries),
            "queries": {name: asdict(query) for name, query in queries.items()}, "all_queries_declared": True,
            "source_fits": 0, "lofo_scenario_duplicates_executed": 0, "max_nodes": max_nodes},
        "cohort_roster": roster, "cases": records, "closure_records": list(closure_records.values()),
        "semantic_equivalence": {"stage_a_compared_prefixes": len(a_checks), "stage_a_all_equal": all(row["all_equal"] for row in a_checks),
            "stage_a_failed_prefixes": sum(not row["all_equal"] for row in a_checks),
            "stage_b_compared_query_trees": len(b_checks), "stage_b_all_equal": all(row["all_equal"] for row in b_checks),
            "stage_b_failed_query_trees": sum(not row["all_equal"] for row in b_checks)},
        "all_path_row_budgets_satisfied": all(row["path_row_budget_satisfied"] for row in b_results),
        "summary_by_split": {split: _summary(records if split == "ALL" else [record for record in records if record["case"]["split"] == split], queries, budgets)
            for split in ("ALL", *sorted({case.split for case in declared}))},
        "summary_by_family": {family: _summary([record for record in records if record["case"]["family"] == family], queries, budgets) for family in sorted({case.family for case in declared})},
        "history_policy_examples": examples,
        "accounting": {"source_fits": 0, "source_setup_seconds": 0.0,
            "stage_a_trajectory_count": len(a_trajectories), "stage_b_query_execution_count": len(b_results),
            "full_target_acquisition_count": len(completed),
            "actual_stage_a_physical_draws": sum(row["physical_sample_draws"] for row in a_trajectories),
            "actual_stage_b_physical_suffix_draws": sum(row["physical_audit"].get("provider_counts", {}).get("physical_draws", 0) for row in b_results),
            "actual_full_benchmark_physical_draws": sum(run["full_target_acquisition"]["physical_sample_draws"] for run in completed),
            "actual_stage_a_trajectory_seconds": math.fsum(row["actual_trajectory_seconds"] for row in a_trajectories),
            "actual_complete_closure_seconds": math.fsum(row["seconds"] for row in closure_records.values()),
            "actual_environment_assembly_seconds": math.fsum(run["environment_assembly_seconds"] for run in completed),
            "actual_full_target_sampling_seconds": math.fsum(run["full_target_acquisition"]["acquisition_and_model_assembly_seconds"] for run in completed),
            "actual_full_benchmark_compile_and_plan_seconds": math.fsum(arm["compile_and_plan_seconds"] for run in completed for arm in run["full_benchmark_costs"].values()),
            "actual_full_benchmark_inventory_serialization_seconds": math.fsum(arm["inventory"]["inventory_serialization_seconds"] for run in completed for arm in run["full_benchmark_costs"].values()),
            "actual_history_evaluation_seconds": math.fsum(row["physical_audit"]["whole_evaluation_seconds"] for row in all_results),
            "actual_counterfactual_branch_clone_seconds": math.fsum(row["physical_audit"]["counterfactual_branch_clone_seconds"] for row in all_results),
            "actual_initial_query_clone_seconds_included_in_execution": math.fsum(row.get("initial_query_clone_seconds", 0.0) for row in b_results),
            "actual_semantic_comparison_seconds": math.fsum(row["comparison_seconds"] for row in (*a_checks, *b_checks)),
            "actual_exact_reference_seconds": math.fsum(sum(run["exact_reference_cost"].values()) for run in completed),
            "physical_rule": "The two Stage A trajectories independently acquire their data and continue from32 to128. Their32 snapshots are shared warm preparation within each update mode; Stage B query providers count all actually repeated history-branch suffix draws. Full benchmarks share one paid support/sample acquisition per case/seed. No source setup is used.",
            "deployment_rule": "Expected and worst-path suffix costs include actual query-start cloning, observations and decisions. Counterfactual sibling clones and full history enumeration are audit work. Warm preparation is attributed in full standalone or divided by declared query count for a batch, never physically rebuilt for each alternative."},
        "limitations": ["All original roots, queries and split labels are exposed development material; no independent confirmation.",
            "ONLINE is a history-dependent root execution policy. No static all-state policy or arbitrary re-entry claim is made.",
            "Empirical intervals are not confidence intervals for true dynamics. Full-row benchmarks use larger observation budgets.",
            "Local path-weighted operation timings are not measured end-to-end online latency. All counterfactual acquisition remains in physical totals.",
            "Source priority is paused; no source transfer conclusion is tested."],
        "u006_assurance_started": False, "deferred_v2_24_case_cohort_executed": False,
        "all_declared_cases_retained": True, "elapsed_seconds": perf_counter() - started_all}


__all__ = ("run_comparison_v13", "UPDATE_MODES", "EXECUTION_MODES")
