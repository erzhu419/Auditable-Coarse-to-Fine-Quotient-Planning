"""Mass-conservation bounds and end-to-end history-dependent acquisition.

No source prior is trained. Legacy and mass-bound planners each build their own declared-query prefix.
No observations or warm preparation cross between the variants.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import DevelopmentClosure, build_development_closure
from .controlled_predictive_cohort_v7 import V7Case
from .controlled_predictive_cohort_v14 import build_cohort_roster_v14, cases_v14
from .controlled_predictive_comparison_v3 import (
    COMPARISON_QUERIES, PROBE_QUERIES, SAMPLE_SEEDS, COMPONENTS, NUMERIC_TOLERANCE, _reference,
)
from .controlled_predictive_comparison_v12 import _acquire_complete, _full_arms
from .controlled_predictive_incremental_v13 import PlannerState
from .controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from .controlled_predictive_partial_v12 import RowSampleProvider
from .controlled_predictive_execution_v13 import ExactEnvironment, evaluate_execution, evaluate_frozen_policy
from .controlled_predictive_quotient_v1 import Query, compile_full_state

VARIANTS = ("LEGACY", "MASS_BOUND")
GOAL_PAIRS = (("goal_1_risk_1", "risk_1"), ("probe_goal_2_risk_0_5", "probe_risk_0_5"))
EXECUTION_MODES = ("upfront", "online")
PREFIX_BUDGETS = (32, 128)
TOTAL_ROW_CAP = 128
SAMPLES_PER_ROW = 256


def _method_id(mode: str, variant: str) -> str:
    return f"{mode}_{variant.lower()}"


@dataclass
class PrefixSnapshot:
    state: Any
    policy: Any
    intervals: Any
    report: dict[str, Any]


def _stage_a(root: Any, seed: int, queries: Mapping[str, Query], variant: str,
             budgets: Sequence[int], samples_per_row: int) -> tuple[dict[int, PrefixSnapshot], dict[str, Any]]:
    """Measure one independent trajectory and preserve a branch-safe warm prefix."""
    started = perf_counter()
    provider = RowSampleProvider(seed, samples_per_row=samples_per_row)
    planner_type = PlannerState if variant == "LEGACY" else MassBoundPlannerState
    planner = planner_type(root, queries, mode="query_interval", update_mode="incremental")
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


def _mass_certificate(case: V7Case) -> dict[str, Any]:
    mass = sum(1 << rank for rank in case.board if rank)
    return {"total_tile_mass": mass, "mass_plus_4h": mass + 4 * case.horizon,
        "goal_mass_excluded": mass + 4 * case.horizon < 2048}


def _goal_pair_diagnostics(case: V7Case, methods: Mapping[str, Any],
                           queries: Mapping[str, Query]) -> dict[str, Any]:
    """Compare existing trees within each variant, never build an extra policy."""
    started = perf_counter()
    certificate = _mass_certificate(case)
    comparisons = []
    if certificate["goal_mass_excluded"]:
        for variant in VARIANTS:
            for mode in EXECUTION_MODES:
                method = _method_id(mode, variant)
                for goal, no_goal in GOAL_PAIRS:
                    if goal not in queries or no_goal not in queries:
                        continue
                    left, right = methods[method][goal], methods[method][no_goal]
                    trace_equal = left["trace"] == right["trace"]
                    metrics_equal = left["root_metrics"] == right["root_metrics"]
                    comparisons.append({"variant": variant, "mode": mode,
                        "goal_query": goal, "no_goal_query": no_goal,
                        "trace_including_observations_equal": trace_equal,
                        "root_metrics_equal": metrics_equal, "all_equal": trace_equal and metrics_equal,
                        "mass_bound_equivalence_expected": variant == "MASS_BOUND"})
    return {**certificate, "comparisons": comparisons,
        "comparison_seconds": perf_counter() - started}


def _json_structure(value: Any) -> Any:
    """The retained reference has JSON lists where in-memory rows use tuples."""
    if isinstance(value, dict):
        return {str(key): _json_structure(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_structure(item) for item in value]
    return value


def _validate_legacy_reference(records: Sequence[Mapping[str, Any]], queries: Mapping[str, Query],
                                path: str | Path) -> dict[str, Any]:
    """Read old evidence only after the current experiment has finished constructing all trees."""
    started = perf_counter()
    historical = json.loads(Path(path).read_text(encoding="utf-8"))
    old_runs = {(record["case"]["name"], run["sample_seed"]): run
        for record in historical["cases"] for run in record["sampled_runs"]}
    prefixes, executions = [], []
    prefix_fields = ("row_budget", "actual_rows_acquired", "physical_sample_draws_in_prefix",
        "requested_row_order", "stop_reason", "root_intervals")
    for record in records:
        for run in record["sampled_runs"]:
            identity = {"case_name": record["case"]["name"], "sample_seed": run["sample_seed"]}
            old = old_runs.get((identity["case_name"], identity["sample_seed"]))
            for budget, prefix in run["stage_a"]["LEGACY"]["prefixes"].items():
                previous = old.get("stage_a", {}).get("incremental", {}).get("prefixes", {}).get(budget) if old else None
                fields = {field: previous is not None and _json_structure(prefix[field]) == previous.get(field)
                    for field in prefix_fields}
                prefixes.append({**identity, "row_budget": int(budget), "field_equal": fields,
                    "all_equal": all(fields.values()), "historical_prefix_found": previous is not None})
            if run["status"] != "COMPLETE":
                continue
            for mode in EXECUTION_MODES:
                for name in queries:
                    current = run["methods"][_method_id(mode, "LEGACY")][name]
                    previous = old.get("methods", {}).get(mode + "_incremental", {}).get(name) if old else None
                    pair = old.get("paired_execution_semantics", {}).get(mode, {}).get(name, {}) if old else {}
                    old_trace = pair.get("shared_trace", pair.get("unequal_traces", {}).get("incremental"))
                    fields = {"trace_including_observations": old_trace is not None and _json_structure(current["trace"]) == old_trace,
                        "root_metrics": previous is not None and _json_structure(current["root_metrics"]) == previous.get("root_metrics")}
                    executions.append({**identity, "mode": mode, "query_name": name,
                        "field_equal": fields, "all_equal": all(fields.values()),
                        "historical_execution_found": previous is not None and old_trace is not None})
    return {"reference_path": str(path), "reference_update_mode": "incremental",
        "reference_read_after_all_current_construction": True,
        "prefix_comparison_count": len(prefixes), "prefix_equal_count": sum(row["all_equal"] for row in prefixes),
        "execution_comparison_count": len(executions), "execution_equal_count": sum(row["all_equal"] for row in executions),
        "all_prefixes_equal": all(row["all_equal"] for row in prefixes),
        "all_execution_trees_equal": all(row["all_equal"] for row in executions),
        "prefix_comparisons": prefixes, "execution_comparisons": executions,
        "compared_prefix_fields": prefix_fields, "numeric_comparison": "EXACT_AFTER_JSON_STRUCTURE_NORMALIZATION",
        "validation_seconds": perf_counter() - started}


def _paired_summary(runs: Sequence[Mapping[str, Any]], queries: Mapping[str, Query],
                     candidate: str, comparator: str) -> dict[str, Any]:
    pairs = [(run["methods"][candidate][name], run["methods"][comparator][name])
        for run in runs for name in queries]
    if not pairs:
        return {"query_context_count": 0}
    differences = [left["root_metrics"]["value"] - right["root_metrics"]["value"] for left, right in pairs]
    return {"query_context_count": len(pairs), "candidate": candidate, "comparator": comparator,
        "better_value_count": sum(value > NUMERIC_TOLERANCE for value in differences),
        "worse_value_count": sum(value < -NUMERIC_TOLERANCE for value in differences),
        "equal_value_count": sum(abs(value) <= NUMERIC_TOLERANCE for value in differences),
        "different_root_action_count": sum(left["root_action"] != right["root_action"] for left, right in pairs),
        "mean_candidate_minus_comparator_root_components": {component: math.fsum(left["root_metrics"][component] - right["root_metrics"][component] for left, right in pairs) / len(pairs) for component in COMPONENTS},
        "minimum_candidate_minus_comparator_value": min(differences),
        "maximum_candidate_minus_comparator_value": max(differences),
        "mean_candidate_minus_comparator_deployment": {field: math.fsum(left["deployment"][field] - right["deployment"][field] for left, right in pairs) / len(pairs)
            for field in ("expected_total_rows", "maximum_total_rows", "expected_standalone_seconds", "expected_batch_amortized_seconds")}}


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
    methods = ("full_state_empirical", "exact_empirical_quotient", *(_method_id("frozen32", variant) for variant in VARIANTS),
        *(_method_id(mode, update) for mode in EXECUTION_MODES for update in VARIANTS))
    stage_a = {}
    for budget in budgets:
        stage_a[str(budget)] = {update: {
            "case_seed_count": len(runs),
            "mean_rows": math.fsum(run["stage_a"][update]["prefixes"][str(budget)]["actual_rows_acquired"] for run in runs) / len(runs) if runs else None,
            "mean_acquisition_and_engine_seconds": math.fsum(run["stage_a"][update]["prefixes"][str(budget)]["prefix_acquisition_and_engine_seconds"] for run in runs) / len(runs) if runs else None,
        } for update in VARIANTS}
    return {"declared_case_count": len(records), "completed_case_seed_runs": len(runs),
        "query_context_count_per_method": len(runs) * len(queries), "stage_a": stage_a,
        "methods": {method: _method_summary([run["methods"][method][name] for run in runs for name in queries]) for method in methods},
        "mass_bound_versus_legacy": {mode: _paired_summary(runs, queries, _method_id(mode, "MASS_BOUND"), _method_id(mode, "LEGACY")) for mode in ("frozen32", *EXECUTION_MODES)},
        "online_versus_upfront": {variant: _paired_summary(runs, queries, _method_id("online", variant), _method_id("upfront", variant)) for variant in VARIANTS}}


def run_comparison_v14(*, cases: Sequence[V7Case] | None = None,
                       cohort_roster: Mapping[str, Any] | None = None,
                       sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                       queries: Mapping[str, Query] | None = None,
                       samples_per_row: int = SAMPLES_PER_ROW,
                       prefix_budgets: Sequence[int] = PREFIX_BUDGETS,
                       total_row_cap: int = TOTAL_ROW_CAP,
                       max_nodes: int = 30_000,
                       progress: Callable[[dict[str, Any]], None] | None = None,
                       legacy_reference_path: str | Path = "reports/controlled_predictive_execution_acquisition_v13.json") -> dict[str, Any]:
    declared = tuple(cases_v14() if cases is None else cases)
    roster = build_cohort_roster_v14() if cohort_roster is None else cohort_roster
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
            a_order = VARIANTS if (case_index + seed_index) % 2 == 0 else VARIANTS[::-1]
            snapshots, stage_a = {}, {}
            for update in a_order:
                snapshots[update], trajectory = _stage_a(root_key, seed, queries, update, budgets, samples_per_row)
                stage_a[update] = {"trajectory": trajectory,
                    "prefixes": {str(budget): snapshot.report for budget, snapshot in snapshots[update].items()}}
                if progress:
                    progress({"case": case.name, "sample_seed": seed, "stage": "A", "variant": update,
                        "status": "PREFIXES_FROZEN", "rows": trajectory["actual_rows_acquired"]})
            run = {"sample_seed": seed, "status": "STAGE_A_FROZEN", "stage_a_order": a_order,
                "stage_a": stage_a,
                "source_fits": 0, "source_setup_seconds": 0.0, "mass_certificate": _mass_certificate(case)}
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
                methods={method: {} for method in ("full_state_empirical", "exact_empirical_quotient", *(_method_id("frozen32", variant) for variant in VARIANTS),
                    *(_method_id(mode, update) for mode in EXECUTION_MODES for update in VARIANTS))},
                stage_b_order_by_query={}, goal_pair_diagnostics={}, paired_method_differences={})
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
                b_order = [(mode, update) for mode in EXECUTION_MODES for update in VARIANTS]
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
                for method, result in query_results.items():
                    run["methods"][method][name] = result
                raw_traces[name] = query_results["online_mass_bound"]["trace"]
                for variant in VARIANTS:
                    warm = snapshots[variant][budgets[0]]
                    frozen_result = evaluate_frozen_policy(root_key, query,
                        lambda key, n=name, p=warm.policy: p.action(key, n), environment,
                        known_rows=warm.state.rows, known_policy_keys=warm.policy.policies[name], initial_rows=len(warm.state.rows))
                    _attribute_execution(frozen_result, warm.report["warm_start_preparation_seconds"], len(queries))
                    frozen_result["prefix_variant"] = variant
                    frozen_result["prefix_update_mode"] = "incremental"
                    run["methods"][_method_id("frozen32", variant)][name] = frozen_result
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
                for update in VARIANTS:
                    online = run["methods"][_method_id("online", update)][name]
                    upfront = run["methods"][_method_id("upfront", update)][name]
                    frozen = run["methods"][_method_id("frozen32", update)][name]
                    run["paired_method_differences"][name][update] = {
                        "online_minus_upfront_root_components": {component: online["root_metrics"][component] - upfront["root_metrics"][component] for component in COMPONENTS},
                        "online_minus_frozen32_root_components": {component: online["root_metrics"][component] - frozen["root_metrics"][component] for component in COMPONENTS},
                        "online_minus_upfront_expected_rows": online["deployment"]["expected_total_rows"] - upfront["deployment"]["expected_total_rows"],
                        "online_minus_upfront_expected_standalone_seconds": online["deployment"]["expected_standalone_seconds"] - upfront["deployment"]["expected_standalone_seconds"]}
                run["paired_method_differences"][name]["MASS_BOUND_MINUS_LEGACY"] = {
                    mode: {"root_components": {component: run["methods"][_method_id(mode, "MASS_BOUND")][name]["root_metrics"][component] - run["methods"][_method_id(mode, "LEGACY")][name]["root_metrics"][component] for component in COMPONENTS},
                        "expected_rows": run["methods"][_method_id(mode, "MASS_BOUND")][name]["deployment"]["expected_total_rows"] - run["methods"][_method_id(mode, "LEGACY")][name]["deployment"]["expected_total_rows"],
                        "expected_standalone_seconds": run["methods"][_method_id(mode, "MASS_BOUND")][name]["deployment"]["expected_standalone_seconds"] - run["methods"][_method_id(mode, "LEGACY")][name]["deployment"]["expected_standalone_seconds"]}
                    for mode in ("frozen32", *EXECUTION_MODES)}
            run["goal_pair_diagnostics"] = _goal_pair_diagnostics(case, run["methods"], queries)
            selected = ((case.name == "v6_spawn_edge_rescue_2" and seed == 832101)
                or (case.name == "v6_crossing_rescue_pair_3" and seed == 832102)
                or (case.name == "v6_crossing_rescue_pair_2" and seed == 832102))
            if selected:
                if case.name == "v6_spawn_edge_rescue_2":
                    chosen = list(queries)
                elif case.name == "v6_crossing_rescue_pair_3":
                    chosen = ["risk_5"]
                else:
                    selected_names = {name for pair in GOAL_PAIRS for name in pair}
                    chosen = [name for name in queries if name in selected_names]
                examples.append({"case_name": case.name, "sample_seed": seed, "method": "online_mass_bound",
                    "root": root_key, "queries": {name: asdict(queries[name]) for name in chosen},
                    "query_order": chosen, "traces": {name: raw_traces[name] for name in chosen},
                    "expected_root_metrics": {name: run["methods"]["online_mass_bound"][name]["root_metrics"] for name in chosen}})
            run["status"] = record["status"] = "COMPLETE"
    all_runs = [run for record in records for run in record["sampled_runs"]]
    completed = [run for run in all_runs if run["status"] == "COMPLETE"]
    a_trajectories = [run["stage_a"][update]["trajectory"] for run in all_runs for update in VARIANTS]
    b_results = [run["methods"][_method_id(mode, update)][name] for run in completed for mode in EXECUTION_MODES for update in VARIANTS for name in queries]
    all_results = [result for run in completed for rows in run["methods"].values() for result in rows.values()]
    legacy_validation = _validate_legacy_reference(records, queries, legacy_reference_path)
    return {"schema": "acfqp.controlled_predictive_mass_bound.v14",
        "status": "DEVELOPMENT_COMPLETE" if len(completed) == len(declared) * len(sample_seeds) else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES",
        "scientific_gate": "NOT_A_FORMAL_GATE", "case_count": len(declared),
        "completed_case_seed_runs": len(completed), "query_contexts_per_method": len(completed) * len(queries),
        "settings": {"sample_seeds": list(sample_seeds), "samples_per_row": samples_per_row,
            "prefix_budgets": budgets, "total_row_cap": total_row_cap, "query_order": list(queries),
            "queries": {name: asdict(query) for name, query in queries.items()}, "all_queries_declared": True,
            "source_fits": 0, "lofo_scenario_duplicates_executed": 0, "variants": VARIANTS, "update_mode": "incremental", "max_nodes": max_nodes},
        "cohort_roster": roster, "cases": records, "closure_records": list(closure_records.values()),
        "legacy_reference_validation": legacy_validation,
        "goal_pair_summary": {variant: {"eligible_case_seed_runs": sum(run["mass_certificate"]["goal_mass_excluded"] for run in completed),
            "comparison_count": sum(row["variant"] == variant for run in completed for row in run["goal_pair_diagnostics"]["comparisons"]),
            "equal_count": sum(row["variant"] == variant and row["all_equal"] for run in completed for row in run["goal_pair_diagnostics"]["comparisons"]),
            "unequal_comparisons": [{"case_name": record["case"]["name"], "sample_seed": run["sample_seed"], **row}
                for record in records for run in record["sampled_runs"] if run["status"] == "COMPLETE"
                for row in run["goal_pair_diagnostics"]["comparisons"] if row["variant"] == variant and not row["all_equal"]]}
            for variant in VARIANTS},
        "all_path_row_budgets_satisfied": all(row["path_row_budget_satisfied"] for row in b_results),
        "summary_by_split": {split: _summary(records if split == "ALL" else [record for record in records if record["case"]["split"] == split], queries, budgets)
            for split in ("ALL", *sorted({case.split for case in declared}))},
        "summary_by_mass_certificate": {label: _summary([record for record in records if _mass_certificate(V7Case(**record["case"]))["goal_mass_excluded"] == excluded], queries, budgets)
            for label, excluded in (("goal_mass_excluded", True), ("goal_mass_not_excluded", False))},
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
            "actual_goal_pair_comparison_seconds": math.fsum(run["goal_pair_diagnostics"]["comparison_seconds"] for run in completed),
            "actual_legacy_validation_seconds": legacy_validation["validation_seconds"],
            "actual_exact_reference_seconds": math.fsum(sum(run["exact_reference_cost"].values()) for run in completed),
            "physical_rule": "The two variant Stage A trajectories independently acquire their data and continue from32 to128. Their32 snapshots are shared warm preparation only within each variant; Stage B query providers count all actually repeated history-branch suffix draws. Full benchmarks share one paid support/sample acquisition per case/seed. No source setup is used.",
            "deployment_rule": "Expected and worst-path suffix costs include actual query-start cloning, observations and decisions. Counterfactual sibling clones and full history enumeration are audit work. Warm preparation is attributed in full standalone or divided by declared query count for a batch, never physically rebuilt for each alternative."},
        "limitations": ["All original roots, queries and split labels are exposed development material; no independent confirmation.",
            "ONLINE is a history-dependent root execution policy. No static all-state policy or arbitrary re-entry claim is made.",
            "Empirical intervals are not confidence intervals for true dynamics. Full-row benchmarks use larger observation budgets.",
            "Local path-weighted operation timings are not measured end-to-end online latency. All counterfactual acquisition remains in physical totals.",
            "Both variants independently prepare all ten queries, so their warm models can differ even for zero-goal queries. Mechanism equality is tested within each variant only.",
            "Source priority is paused; no source transfer conclusion is tested."],
        "u006_assurance_started": False, "deferred_v2_24_case_cohort_executed": False,
        "all_declared_cases_retained": True, "elapsed_seconds": perf_counter() - started_all}


__all__ = ("run_comparison_v14", "VARIANTS", "EXECUTION_MODES")
