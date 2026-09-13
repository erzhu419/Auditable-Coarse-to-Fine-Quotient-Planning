#!/usr/bin/env python3
"""Read retained V20 outcomes and traces once; issue no planning observations."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path

from analyze_controlled_predictive_quality_v15 import comparison, mean, outcome

METHODS = dict(FULL="full_state_empirical", EXACT="exact_empirical_quotient",
    BASE="online_mass_bound", CACHED="online_cached_balanced_gap_stop", VARIANCE="online_variance_gap_stop")
ONLINE = tuple(METHODS)[2:]
PAIRS = (("VARIANCE", "CACHED"), ("VARIANCE", "BASE"), ("CACHED", "BASE"))
DEPLOYMENT = ("expected_total_batches", "maximum_total_batches", "expected_total_draws",
    "maximum_total_draws", "expected_total_distinct_rows", "expected_standalone_seconds",
    "maximum_standalone_seconds", "expected_batch_amortized_seconds", "expected_suffix_seconds")
TOL = 1e-10


def _aggregate_maps(rows, section, field, divisor=1):
    maps = [row[section].get(field, {}) for row in rows]
    keys = sorted(set().union(*(value.keys() for value in maps)))
    return {key: math.fsum(value.get(key, 0) for value in maps) / divisor for key in keys}


def summaries(contexts, *, include_work=False):
    output = {}
    for alias in METHODS:
        rows = [c["methods"][alias] for c in contexts]
        output[alias] = {
            "optimal_first_actions": sum(r["quality"]["root_action_in_exact_optimal_set"] for r in rows),
            "optimal_full_policies": sum(r["quality"]["root_optimal_full_policy"] for r in rows),
            "worse_than_full": sum(r["quality"]["root_extra_regret_over_full_state"] > TOL for r in rows),
            "maximum_regret": max(r["quality"]["root_regret"] for r in rows),
            "mean_components": {k: mean([r["root_metrics"][k] for r in rows]) for k in ("reward", "failure", "success", "value")},
            "mean_deployment": {k: mean([r["deployment"][k] for r in rows]) for k in DEPLOYMENT},
            "maximum_path_draws": max(r["deployment"]["maximum_total_draws"] for r in rows)}
        if include_work:
            output[alias]["mean_expected_seconds_by_stage"] = _aggregate_maps(rows, "deployment", "expected_seconds_by_stage", len(rows))
            output[alias]["mean_expected_suffix_work_counts"] = _aggregate_maps(rows, "deployment", "expected_suffix_work_counts", len(rows))
            output[alias]["physical"] = {
                "all_history_decision_seconds_by_stage": _aggregate_maps(rows, "physical_audit", "all_history_decision_seconds_by_stage"),
                "all_history_decision_work_counts": _aggregate_maps(rows, "physical_audit", "all_history_decision_work_counts"),
                "counterfactual_branch_clone_work_counts": _aggregate_maps(rows, "physical_audit", "counterfactual_branch_clone_work_counts"),
                "counterfactual_branch_clone_seconds": math.fsum(r["physical_audit"]["counterfactual_branch_clone_seconds"] for r in rows),
                "whole_evaluation_seconds": math.fsum(r["physical_audit"]["whole_evaluation_seconds"] for r in rows)}
    return output


def paired(contexts, candidate, comparator):
    result = comparison(contexts, candidate, comparator)
    pairs = [(row["methods"][candidate], row["methods"][comparator]) for row in contexts]
    result["mean_deployment_difference"] = {field: math.fsum(
        left["deployment"][field] - right["deployment"][field] for left, right in pairs) / len(pairs)
        for field in DEPLOYMENT}
    deltas = [left["deployment"]["expected_total_draws"] - right["deployment"]["expected_total_draws"]
              for left, right in pairs]
    result["expected_sample_counts"] = {"reduced": sum(value < -TOL for value in deltas),
        "equal": sum(abs(value) <= TOL for value in deltas), "increased": sum(value > TOL for value in deltas)}
    return result


def stopped_nodes(node, reach=1.0):
    if "action" not in node:
        return
    yield node, reach
    for edge in node["children"]:
        yield from stopped_nodes(edge["node"], reach * edge["probability"])


def summarize(payload):
    contexts, runs, checks = [], [], defaultdict(list)
    diagnostics = {alias: {"counts": Counter(), "weighted": Counter(), "reasons": Counter()}
                   for alias in ("CACHED", "VARIANCE")}
    source_witnesses = payload["cohort_roster"]["source_witnesses"]
    source_index = {(row["case"], row["seed"], row["query"]): row for row in source_witnesses}
    fixed_witnesses = []
    physical = {alias: Counter() for alias in ONLINE}
    for case in payload["cases"]:
        for run in case["sampled_runs"]:
            runs.append(run)
            if run["status"] != "COMPLETE":
                raise ValueError("The declared campaign contains an incomplete run")
            warm = run["shared_warm"]["prefix"]
            for query in payload["settings"]["query_order"]:
                context = {"identity": {"case": case["case"]["name"], "seed": run["sample_seed"], "query": query},
                    "methods": {alias: run["methods"][method][query] for alias, method in METHODS.items()}}
                contexts.append(context)
                for alias in ONLINE:
                    row = context["methods"][alias]
                    deploy, provider = row["deployment"], row["physical_audit"]["provider_counts"]
                    physical[alias].update(provider)
                    conversion = 0.0 if alias == "BASE" else run[{
                        "CACHED": "shared_cached_gap_conversion", "VARIANCE": "shared_variance_conversion"}[alias]]["conversion_seconds"]
                    setup = warm["warm_start_preparation_seconds"] + conversion
                    checks["path_caps"].append(deploy["maximum_total_batches"] <= 128 and deploy["maximum_total_draws"] <= 32768)
                    checks["sample_units"].append(deploy["maximum_total_draws"] == 256 * deploy["maximum_total_batches"] and abs(deploy["expected_total_draws"] - 256 * deploy["expected_total_batches"]) <= TOL)
                    checks["initial_batches"].append(deploy["initial_batches"] == warm["actual_rows_acquired"])
                    checks["conversion_attribution"].append(deploy["integer_count_conversion_seconds"] == conversion)
                    checks["setup_attribution"].append(abs(deploy["expected_standalone_seconds"] - setup - deploy["expected_suffix_seconds"]) <= TOL and abs(deploy["expected_batch_amortized_seconds"] - setup / 10 - deploy["expected_suffix_seconds"]) <= TOL)
                    checks["provider_draws"].append(provider.get("row_requests", 0) == provider.get("first_batch_requests", 0) + provider.get("repeat_batch_requests", 0) and provider.get("physical_draws", 0) == 256 * provider.get("row_requests", 0))
                for alias, diagnostic in diagnostics.items():
                    counts, weighted, reasons = diagnostic["counts"], diagnostic["weighted"], diagnostic["reasons"]
                    for node, reach in stopped_nodes(context["methods"][alias]["trace"]):
                        counts["decisions"] += 1
                        weighted["decisions"] += reach
                        reasons[node["acquisition_stop_reason"]] += 1
                        if node["acquisition_stop_reason"] == "HEURISTIC_GAP_SEPARATED":
                            counts["separated"] += 1
                            weighted["separated"] += reach
                            if node["upper"] - node["lower"] > TOL:
                                counts["separated_unresolved"] += 1
                                weighted["separated_unresolved"] += reach
    by_case = defaultdict(list)
    for context in contexts:
        by_case[context["identity"]["case"]].append(context)
    old_five = {(f"v6_crossing_rescue_pair_{c}", s, q) for c, s, q in (
        (0, 832101, "goal_1_risk_1"), (0, 832101, "probe_goal_2_risk_0_5"),
        (2, 832101, "goal_1_risk_1"), (2, 832102, "goal_1_risk_1"), (2, 832102, "probe_goal_2_risk_0_5"))}
    previous_eight, previous_five, samples = [], [], Counter()
    for context in contexts:
        identity, methods = context["identity"], context["methods"]
        witness = {**identity, "methods": {alias: outcome(row) for alias, row in methods.items()}}
        source = source_index.get((identity["case"], identity["seed"], identity["query"]))
        if source is not None:
            retained = {**witness, "source_group": source["group"],
                "source_first_divergence_count": source["first_divergence_count"],
                "source_cached_minus_base_value": source["cached_minus_base_value"]}
            for alias, row in methods.items():
                retained["methods"][alias]["deployment"] = {field: row["deployment"][field] for field in DEPLOYMENT}
                retained["methods"][alias]["physical_suffix_provider_counts"] = row["physical_audit"].get("provider_counts", {})
            left, right = methods["VARIANCE"], methods["CACHED"]
            retained["variance_minus_cached"] = {
                "root_components": {key: left["root_metrics"][key] - right["root_metrics"][key] for key in ("reward", "failure", "success", "value")},
                "deployment": {field: left["deployment"][field] - right["deployment"][field] for field in DEPLOYMENT}}
            fixed_witnesses.append(retained)
            if source["group"] == "original_eight_base_worse_than_full":
                previous_eight.append(witness)
        if (identity["case"], identity["seed"], identity["query"]) in old_five:
            previous_five.append(witness)
        delta = methods["VARIANCE"]["deployment"]["expected_total_draws"] - methods["CACHED"]["deployment"]["expected_total_draws"]
        samples["reduced" if delta < -TOL else "increased" if delta > TOL else "equal"] += 1
    accounting = payload["accounting"]
    checks["declared_contexts"] = [len(runs) == 48, len(contexts) == 480, len(previous_eight) == 8, len(previous_five) == 5]
    checks["physical_conversion_counts"] = [accounting[k] == n for k, n in (("shared_warm_trajectory_count", 48), ("shared_cached_gap_conversion_count", 48), ("shared_variance_conversion_count", 48), ("actual_conversion_count", 96))]
    for group in ("cached_gap", "variance"):
        total = math.fsum(run[f"shared_{group}_conversion"]["conversion_seconds"] for run in runs)
        checks["physical_conversion_seconds"].append(abs(total - accounting[f"actual_{group}_conversion_seconds"]) <= TOL)
    checks["physical_warm_draws"] = [accounting["actual_warm_physical_draws"] == sum(run["shared_warm"]["trajectory"]["physical_sample_draws"] for run in runs), accounting["actual_warm_physical_draws"] == 256 * sum(run["shared_warm"]["prefix"]["actual_rows_acquired"] for run in runs)]
    checks["full_acquisition_draws"] = [accounting["full_target_acquisition_count"] == 48, accounting["actual_full_benchmark_physical_draws"] == sum(run["full_target_acquisition"]["physical_sample_draws"] for run in runs)]
    checks["physical_execution_draws"] = [accounting["actual_execution_physical_suffix_draws"] == sum(row["physical_draws"] for row in physical.values())]
    for alias, method in zip(ONLINE, tuple(METHODS.values())[2:]):
        checks["physical_method_totals"].append(all(physical[alias][k] == v for k, v in accounting["actual_execution_provider_counts_by_method"][method].items()))
    reference = {name: {k: v for k, v in payload[name].items() if k in (
        "prefix_equal_count", "execution_equal_count", "all_prefixes_equal", "all_execution_trees_equal")}
        for name in ("baseline_reference_validation", "cached_reference_validation")}
    checks["historical_reproduction"] = [
        reference["baseline_reference_validation"] == dict(prefix_equal_count=48, execution_equal_count=480, all_prefixes_equal=True, all_execution_trees_equal=True),
        reference["cached_reference_validation"] == dict(execution_equal_count=480, all_execution_trees_equal=True),
        payload["cached_reference_validation"]["trace_fields_excluded"] == []]
    checks["all_ten_source_witnesses_included"] = [len(fixed_witnesses) == len(source_witnesses) == 10,
        {(row["case"], row["seed"], row["query"]) for row in fixed_witnesses} == set(source_index),
        sum(row["source_group"] == "two_cached_regressions_versus_base" for row in fixed_witnesses) == 2,
        sum(row["source_first_divergence_count"] == 0 for row in fixed_witnesses) == 4]
    witness_groups = {group: [context for context in contexts
        if (source_index.get((context["identity"]["case"], context["identity"]["seed"], context["identity"]["query"])) or {}).get("group") == group]
        for group in sorted({row["group"] for row in source_witnesses})}
    pairs = {f"{a}_versus_{b}": paired(contexts, a, b) for a, b in PAIRS}
    return {"schema": "acfqp.controlled_predictive_variance_analysis.v20", "methods": summaries(contexts, include_work=True), "pairs": pairs,
        "elapsed_seconds": payload["elapsed_seconds"], "contexts_per_method": len(contexts), "variance_versus_cached_expected_sample_counts": {k: samples[k] for k in ("reduced", "equal", "increased")},
        "by_case": {name: {"methods": summaries(rows), "pairs": {f"{a}_versus_{b}": {
            k: v for k, v in paired(rows, a, b).items() if k != "nonzero_component_contexts"} for a, b in PAIRS}} for name, rows in by_case.items()},
        "previous_v14_eight": previous_eight, "previous_v13_five": previous_five,
        "fixed_source_witnesses": fixed_witnesses,
        "witness_group_comparisons": {group: paired(rows, "VARIANCE", "CACHED") for group, rows in witness_groups.items()},
        "stop_diagnostics": {alias: {
            "history_node_counts": dict(diag["counts"]), "stop_reason_node_counts": dict(diag["reasons"]),
            "sum_expected_events_over_contexts": dict(diag["weighted"]),
            "mean_expected_separated_stops": diag["weighted"]["separated"] / len(contexts),
            "separated_node_unresolved_fraction": diag["counts"]["separated_unresolved"] / diag["counts"]["separated"] if diag["counts"]["separated"] else None,
        } for alias, diag in diagnostics.items()},
        "verification": {name: {"passed": all(values), "comparison_count": len(values), "failed_count": sum(not v for v in values)} for name, values in checks.items()},
        "historical_reproduction": reference, "physical_accounting": accounting,
        "scope": "Retained root qualities and history traces only. Original CACHED must reproduce V18 complete histories; VARIANCE may change histories and actual sample counts under the same total cap. All ten fixed source witnesses remain included. Expected stage costs include deployment scoring, cache copying and updates; counterfactual sibling clones remain physical audit work. Stop events use retained true transition weights but are not optimality labels or confidence guarantees. Full empirical benchmarks have larger sample budgets."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_variance_v20.json.gz"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_variance_analysis_v20.json"))
    args = parser.parse_args()
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        report = summarize(json.load(handle))
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: report[k] for k in ("methods", "variance_versus_cached_expected_sample_counts", "stop_diagnostics", "verification")}, indent=2))
