"""Frozen gap-triggered resampling, stopping ablation and paid historical controls."""
from __future__ import annotations

from dataclasses import asdict
import gzip
import json
from pathlib import Path
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import build_development_closure
from .controlled_predictive_cohort_v7 import V7Case
from .controlled_predictive_cohort_v16 import build_cohort_roster_v16, cases_v16
from .controlled_predictive_comparison_v3 import (
    COMPARISON_QUERIES, PROBE_QUERIES, SAMPLE_SEEDS, COMPONENTS, NUMERIC_TOLERANCE, _reference,
)
from .controlled_predictive_comparison_v12 import _acquire_complete, _full_arms
from .controlled_predictive_comparison_v14 import _stage_a, _root_quality, _mass_certificate, _json_structure
from .controlled_predictive_execution_v13 import ExactEnvironment, evaluate_execution, evaluate_frozen_policy
from .controlled_predictive_execution_v15 import evaluate_resampling_execution
from .controlled_predictive_resampling_v15 import ResamplingPlannerState
from .controlled_predictive_gap_v16 import GapPlannerState
from .controlled_predictive_execution_v16 import evaluate_gap_execution
from .controlled_predictive_comparison_v15 import (
    _unify_first_batch_deployment, _attribute_execution, _validate_reference,
    _method_summary, _paired_summary,
)
from .controlled_predictive_sampling_v15 import BatchRowSampleProvider
from .controlled_predictive_quotient_v1 import Query, compile_full_state

EXECUTION_METHODS = ("online_mass_bound", "online_balanced_resampling",
                     "online_gap_continue", "online_gap_stop")
FULL_METHODS = ("full_state_empirical", "exact_empirical_quotient")
METHODS = (*FULL_METHODS, *EXECUTION_METHODS)
GAP_MODES = {"online_gap_continue": "CONTINUE", "online_gap_stop": "STOP"}
INITIAL_BATCH_CAP = 32
TOTAL_BATCH_CAP = 128
SAMPLES_PER_BATCH = 256


def _validate_balanced_reference(records: Sequence[Mapping[str, Any]], queries: Mapping[str, Query],
                                 reference_path: str | Path) -> dict[str, Any]:
    """Compare retained V15 semantics after every current history is frozen."""
    started = perf_counter()
    with gzip.open(reference_path, "rt", encoding="utf-8") as handle:
        old = json.load(handle)
    index = {(record["case"]["name"], run["sample_seed"]): run
             for record in old["cases"] for run in record["sampled_runs"]}
    comparisons = []
    for record in records:
        for run in record["sampled_runs"]:
            if run["status"] != "COMPLETE":
                continue
            identity = {"case_name": record["case"]["name"], "sample_seed": run["sample_seed"]}
            previous = index.get((identity["case_name"], identity["sample_seed"]))
            for name in queries:
                current = run["methods"]["online_balanced_resampling"][name]
                before = previous.get("methods", {}).get("online_balanced_resampling", {}).get(name) if previous else None
                checks = {field: before is not None and _json_structure(current[field]) == before.get(field)
                          for field in ("trace", "root_metrics")}
                comparisons.append({**identity, "query_name": name, "field_equal": checks,
                    "all_equal": all(checks.values()), "historical_execution_found": before is not None})
    return {"reference_path": str(reference_path), "reference_method": "online_balanced_resampling",
        "reference_read_after_all_current_construction": True,
        "execution_comparison_count": len(comparisons),
        "execution_equal_count": sum(row["all_equal"] for row in comparisons),
        "all_execution_trees_equal": all(row["all_equal"] for row in comparisons),
        "execution_comparisons": comparisons,
        "numeric_comparison": "EXACT_AFTER_JSON_STRUCTURE_NORMALIZATION",
        "validation_seconds": perf_counter() - started}


PAIRS = {"gap_stop_versus_continue": ("online_gap_stop", "online_gap_continue"),
    "gap_continue_versus_balanced": ("online_gap_continue", "online_balanced_resampling"),
    "gap_stop_versus_balanced": ("online_gap_stop", "online_balanced_resampling"),
    "gap_stop_versus_base": ("online_gap_stop", "online_mass_bound")}


def _summary(records: Sequence[Mapping[str, Any]], queries: Mapping[str, Query]) -> dict[str, Any]:
    runs = [run for record in records for run in record["sampled_runs"] if run["status"] == "COMPLETE"]
    return {"declared_case_count": len(records), "completed_case_seed_runs": len(runs),
        "query_context_count_per_method": len(runs) * len(queries),
        "methods": {method: _method_summary([run["methods"][method][name] for run in runs for name in queries]) for method in METHODS},
        "paired_methods": {name: _paired_summary(runs, queries, *pair) for name, pair in PAIRS.items()}}


def run_comparison_v16(*, cases: Sequence[V7Case] | None = None,
                       cohort_roster: Mapping[str, Any] | None = None,
                       sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                       queries: Mapping[str, Query] | None = None,
                       initial_batch_cap: int = INITIAL_BATCH_CAP,
                       total_batch_cap: int = TOTAL_BATCH_CAP,
                       max_nodes: int = 30_000,
                       progress: Callable[[dict[str, Any]], None] | None = None,
                       reference_path: str | Path = "reports/controlled_predictive_mass_bound_v14.json",
                       balanced_reference_path: str | Path = "reports/controlled_predictive_resampling_v15.json.gz") -> dict[str, Any]:
    declared = tuple(cases_v16() if cases is None else cases)
    roster = build_cohort_roster_v16() if cohort_roster is None else cohort_roster
    queries = dict({**COMPARISON_QUERIES, **PROBE_QUERIES} if queries is None else queries)
    if not declared or not queries or not sample_seeds or not 0 < initial_batch_cap <= total_batch_cap:
        raise ValueError("nonempty inputs and positive warm budget within total batch cap are required")
    started_all = perf_counter()
    records = [{"case": asdict(case), "sampled_runs": [], "status": "NOT_RUN"} for case in declared]
    closures, closure_records, examples = {}, {}, []
    for case_index, (case, record) in enumerate(zip(declared, records)):
        root_key = (case.horizon, tuple(case.board))
        for seed_index, seed in enumerate(sample_seeds):
            snapshots, trajectory = _stage_a(root_key, seed, queries, "MASS_BOUND", (initial_batch_cap,), SAMPLES_PER_BATCH)
            warm = snapshots[initial_batch_cap]
            converted = ResamplingPlannerState.from_warm(warm.state)
            gap_converted = GapPlannerState.from_warm(warm.state)
            def conversion_record(state, methods):
                return {"conversion_seconds": state.conversion_seconds,
                    "work_counts": {key: value - warm.state.work_counts.get(key, 0) for key, value in state.work_counts.items()
                        if value != warm.state.work_counts.get(key, 0)},
                    "initial_batches": state.spent_batches, "initial_distinct_rows": len(state.rows),
                    "physically_converted_once": True, "shared_by_methods": list(methods)}
            run = {"sample_seed": seed, "status": "WARM_FROZEN", "mass_certificate": _mass_certificate(case),
                "shared_warm": {"trajectory": trajectory, "prefix": warm.report},
                "shared_balanced_conversion": conversion_record(converted, ("online_balanced_resampling",)),
                "shared_gap_conversion": conversion_record(gap_converted, GAP_MODES),
                "source_fits": 0, "source_setup_seconds": 0.0}
            record["sampled_runs"].append(run)
            if progress:
                progress({"case": case.name, "sample_seed": seed, "stage": "A", "status": "WARM_FROZEN", "batches": len(warm.state.rows)})
            if case.name not in closure_records:
                started = perf_counter()
                try:
                    closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes, boards={case.name: case.board})
                except ValueError as error:
                    if "complete closure exceeds max_nodes=" not in str(error):
                        raise
                    closure_records[case.name] = {"case_name": case.name, "status": "CLOSURE_BUDGET_EXCEEDED", "reason": str(error), "seconds": perf_counter() - started}
                else:
                    closures[case.name] = closure
                    closure_records[case.name] = {"case_name": case.name, "status": "CLOSURE_COMPLETE", "seconds": closure.elapsed_seconds, "coverage": closure.counts}
            if case.name not in closures:
                run["status"] = record["status"] = "CLOSURE_BUDGET_EXCEEDED"
                continue
            closure = closures[case.name]
            started = perf_counter()
            environment = ExactEnvironment.from_closure(closure)
            environment_seconds = perf_counter() - started
            empirical, acquisition = _acquire_complete(closure, seed, SAMPLES_PER_BATCH)
            full_frozen = _full_arms(empirical, closure, queries)
            run.update(full_target_acquisition=acquisition, environment_assembly_seconds=environment_seconds,
                methods={method: {} for method in METHODS}, execution_order_by_query={}, paired_method_differences={})
            key_to_state = {(closure.model.layers[state], board): state for state, board in closure.boards.items()}
            known_rows = {((closure.model.layers[state], closure.boards[state]), action) for state, action in empirical.rows}
            active_keys = {key for key, state in key_to_state.items() if closure.model.terminal[state] == "ACTIVE"}
            run["full_benchmark_costs"] = {arm: {"inventory": inventory,
                "compile_and_plan_seconds": inventory["construction_seconds"] + math.fsum(value[1] for value in plans.values())}
                for arm, (_, inventory, plans) in full_frozen.items()}
            for query_index, (name, query) in enumerate(queries.items()):
                offset = (case_index + seed_index + query_index) % len(EXECUTION_METHODS)
                order = EXECUTION_METHODS[offset:] + EXECUTION_METHODS[:offset]
                run["execution_order_by_query"][name] = order
                for method in order:
                    provider = BatchRowSampleProvider(seed)
                    if method == "online_mass_bound":
                        result = evaluate_execution(warm.state, provider, name, environment, mode="online", total_row_cap=total_batch_cap)
                        _unify_first_batch_deployment(result)
                        conversion_cost = 0.0
                    elif method == "online_balanced_resampling":
                        result = evaluate_resampling_execution(converted, provider, name, environment,
                            mode="BALANCED", total_batch_cap=total_batch_cap)
                        conversion_cost = converted.conversion_seconds
                    else:
                        result = evaluate_gap_execution(gap_converted, provider, name, environment,
                            mode=GAP_MODES[method], total_batch_cap=total_batch_cap)
                        conversion_cost = gap_converted.conversion_seconds
                    _attribute_execution(result, warm.report["warm_start_preparation_seconds"], conversion_cost, len(queries))
                    deploy = result["deployment"]
                    result["path_batch_budget_satisfied"] = (deploy["expected_total_batches"] <= deploy["maximum_total_batches"] + NUMERIC_TOLERANCE
                        and deploy["maximum_total_batches"] <= total_batch_cap
                        and deploy["maximum_total_draws"] == SAMPLES_PER_BATCH * deploy["maximum_total_batches"])
                    run["methods"][method][name] = result
                for arm, (compiled, inventory, plans) in full_frozen.items():
                    solution = plans[name][0]
                    result = evaluate_frozen_policy(root_key, query,
                        lambda key, sol=solution, model=compiled: sol.policy[model.state_to_cell[key_to_state[key]]],
                        environment, known_rows=known_rows, known_policy_keys=active_keys, initial_rows=len(empirical.rows))
                    _unify_first_batch_deployment(result)
                    preparation = closure.elapsed_seconds + acquisition["acquisition_and_model_assembly_seconds"] + inventory["construction_seconds"]
                    result["deployment"].update(
                        expected_standalone_seconds=preparation + plans[name][1] + result["deployment"]["expected_suffix_seconds"],
                        maximum_standalone_seconds=preparation + plans[name][1] + result["deployment"]["maximum_suffix_seconds"],
                        expected_batch_amortized_seconds=preparation / len(queries) + plans[name][1] + result["deployment"]["expected_suffix_seconds"],
                        prefix_amortization_query_count=len(queries), budget_scope="ALL_ROWS_COST_AND_QUALITY_BENCHMARK")
                    run["methods"][arm][name] = result
                if progress:
                    progress({"case": case.name, "sample_seed": seed, "query": name, "stage": "B", "status": "EXECUTION_TREES_FROZEN"})
            selected = ((case.name == "v6_spawn_edge_rescue_2" and seed == 832101)
                or (case.name in ("v6_crossing_rescue_pair_3", "v6_crossing_rescue_pair_2") and seed == 832102))
            if selected:
                chosen = list(queries) if case.name == "v6_spawn_edge_rescue_2" else (["risk_5"] if case.name == "v6_crossing_rescue_pair_3"
                    else [name for name in queries if name in ("risk_1", "goal_1_risk_1", "probe_risk_0_5", "probe_goal_2_risk_0_5")])
                chosen_results = run["methods"]["online_gap_stop"]
                examples.append({"case_name": case.name, "sample_seed": seed, "method": "online_gap_stop", "root": root_key,
                    "queries": {name: asdict(queries[name]) for name in chosen}, "query_order": chosen,
                    "traces": {name: chosen_results[name]["trace"] for name in chosen},
                    "expected_root_metrics": {name: chosen_results[name]["root_metrics"] for name in chosen}})
            run["status"] = record["status"] = "COMPLETE"
    # Every current history is fixed before any true optimal label is computed.
    for case, record in zip(declared, records):
        if case.name not in closures:
            continue
        closure = closures[case.name]
        for run in record["sampled_runs"]:
            if run["status"] != "COMPLETE":
                continue
            seed = run["sample_seed"]
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
                for method in METHODS:
                    result = run["methods"][method][name]
                    result["quality"] = _root_quality(result, references[name], root, full, case, name, seed)
                run["paired_method_differences"][name] = {pair_name: {
                    "root_components": {component: run["methods"][left][name]["root_metrics"][component] - run["methods"][right][name]["root_metrics"][component] for component in COMPONENTS},
                    "deployment": {field: run["methods"][left][name]["deployment"][field] - run["methods"][right][name]["deployment"][field]
                        for field in ("expected_total_batches", "expected_total_distinct_rows", "expected_standalone_seconds", "expected_batch_amortized_seconds")}}
                    for pair_name, (left, right) in PAIRS.items()}
    runs = [run for record in records for run in record["sampled_runs"]]
    completed = [run for run in runs if run["status"] == "COMPLETE"]
    histories = [row for run in completed for method in EXECUTION_METHODS for row in run["methods"][method].values()]
    all_histories = [row for run in completed for method in METHODS for row in run["methods"][method].values()]
    reference_validation = _validate_reference(records, queries, reference_path)
    balanced_validation = _validate_balanced_reference(records, queries, balanced_reference_path)
    return {"schema": "acfqp.controlled_predictive_gap.v16",
        "status": "DEVELOPMENT_COMPLETE" if len(completed) == len(declared) * len(sample_seeds) else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES",
        "scientific_gate": "NOT_A_FORMAL_GATE", "case_count": len(declared), "completed_case_seed_runs": len(completed),
        "query_contexts_per_method": len(completed) * len(queries),
        "settings": {"sample_seeds": list(sample_seeds), "samples_per_batch": SAMPLES_PER_BATCH,
            "initial_batch_cap": initial_batch_cap, "total_batch_cap": total_batch_cap, "query_order": list(queries),
            "queries": {name: asdict(query) for name, query in queries.items()}, "all_queries_declared": True,
            "methods": METHODS, "source_fits": 0, "stage_a_128_continuation_executed": False, "max_nodes": max_nodes},
        "cohort_roster": roster, "cases": records, "closure_records": list(closure_records.values()),
        "baseline_reference_validation": reference_validation,
        "balanced_reference_validation": balanced_validation,
        "all_path_batch_budgets_satisfied": all(row["path_batch_budget_satisfied"] for row in histories),
        "summary_by_split": {split: _summary(records if split == "ALL" else [record for record in records if record["case"]["split"] == split], queries)
            for split in ("ALL", *sorted({case.split for case in declared}))},
        "summary_by_mass_certificate": {label: _summary([record for record in records if _mass_certificate(V7Case(**record["case"]))["goal_mass_excluded"] == excluded], queries)
            for label, excluded in (("goal_mass_excluded", True), ("goal_mass_not_excluded", False))},
        "summary_by_family": {family: _summary([record for record in records if record["case"]["family"] == family], queries) for family in sorted({case.family for case in declared})},
        "history_policy_examples": examples,
        "accounting": {"source_fits": 0, "source_setup_seconds": 0.0,
            "shared_warm_trajectory_count": len(runs),
            "shared_balanced_conversion_count": len(runs), "shared_gap_conversion_count": len(runs),
            "actual_conversion_count": 2 * len(runs),
            "query_execution_count": len(histories), "full_target_acquisition_count": len(completed),
            "actual_warm_physical_draws": sum(run["shared_warm"]["trajectory"]["physical_sample_draws"] for run in runs),
            "actual_execution_physical_suffix_draws": sum(row["physical_audit"].get("provider_counts", {}).get("physical_draws", 0) for row in histories),
            "actual_full_benchmark_physical_draws": sum(run["full_target_acquisition"]["physical_sample_draws"] for run in completed),
            "actual_execution_provider_counts_by_method": {method: {key: sum(row["physical_audit"].get("provider_counts", {}).get(key, 0) for run in completed for row in run["methods"][method].values())
                for key in ("row_requests", "first_batch_requests", "repeat_batch_requests", "physical_draws", "exact_transition_row_calls", "support_entries_enumerated", "sampled_successor_entries_returned")}
                for method in EXECUTION_METHODS},
            "actual_warm_trajectory_seconds": math.fsum(run["shared_warm"]["trajectory"]["actual_trajectory_seconds"] for run in runs),
            "actual_balanced_conversion_seconds": math.fsum(run["shared_balanced_conversion"]["conversion_seconds"] for run in runs),
            "actual_gap_conversion_seconds": math.fsum(run["shared_gap_conversion"]["conversion_seconds"] for run in runs),
            "actual_shared_conversion_seconds": math.fsum(run[field]["conversion_seconds"] for run in runs
                for field in ("shared_balanced_conversion", "shared_gap_conversion")),
            "actual_complete_closure_seconds": math.fsum(row["seconds"] for row in closure_records.values()),
            "actual_environment_assembly_seconds": math.fsum(run["environment_assembly_seconds"] for run in completed),
            "actual_full_target_sampling_seconds": math.fsum(run["full_target_acquisition"]["acquisition_and_model_assembly_seconds"] for run in completed),
            "actual_full_benchmark_compile_and_plan_seconds": math.fsum(arm["compile_and_plan_seconds"] for run in completed for arm in run["full_benchmark_costs"].values()),
            "actual_full_benchmark_inventory_serialization_seconds": math.fsum(arm["inventory"]["inventory_serialization_seconds"] for run in completed for arm in run["full_benchmark_costs"].values()),
            "actual_history_evaluation_seconds": math.fsum(row["physical_audit"]["whole_evaluation_seconds"] for row in all_histories),
            "actual_counterfactual_branch_clone_seconds_included_in_history": math.fsum(row["physical_audit"]["counterfactual_branch_clone_seconds"] for row in all_histories),
            "actual_initial_query_clone_seconds_included_in_history": math.fsum(row.get("initial_query_clone_seconds", 0.0) for row in histories),
            "actual_baseline_validation_seconds": reference_validation["validation_seconds"],
            "actual_balanced_validation_seconds": balanced_validation["validation_seconds"],
            "actual_exact_reference_seconds": math.fsum(sum(run["exact_reference_cost"].values()) for run in completed),
            "physical_rule": "One paid 32-cap warm trajectory per case/seed, with no 128 continuation. V15 integer-count conversion occurs once for BALANCED; GAP conversion occurs separately once and is shared by CONTINUE and STOP. All history-branch suffix batch requests are physical draws, including repeated rows. Full benchmarks share one complete acquisition per case/seed.",
            "deployment_rule": "Each method bears the complete warm cost; BALANCED also bears its V15 conversion; both GAP methods bear their complete shared GAP conversion. Standalone attribution is full, batch attribution divides this setup by declared query count. Initial query cloning belongs to deployment; sibling-history cloning only to physical audit."},
        "limitations": ["All roots, queries and split labels are exposed development material; no independent confirmation.",
            "Gap separation uses heuristic sampling envelopes, not confidence intervals or calibrated probabilities of error.",
            "All GAP scores are recomputed fully; this experiment does not test score computation optimization.",
            "Resampling batches are distinct from unique observed rows. The path cap counts every 256-draw batch including warm observations.",
            "The methods are history-dependent root execution policies, with no arbitrary re-entry or static all-state policy claim.",
            "Path-weighted local operation timings are not measured end-to-end online latency. Counterfactual history observations remain physical work.",
            "Full-row references use larger observation budgets. Source transfer is not tested."],
        "u006_assurance_started": False, "deferred_v2_24_case_cohort_executed": False,
        "all_declared_cases_retained": True, "elapsed_seconds": perf_counter() - started_all}


__all__ = ("run_comparison_v16", "METHODS", "EXECUTION_METHODS")
