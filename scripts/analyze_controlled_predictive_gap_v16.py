#!/usr/bin/env python3
"""Read retained V16 outcomes and traces once; issue no planning observations."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path

from analyze_controlled_predictive_quality_v15 import comparison, mean, outcome

METHODS = dict(FULL="full_state_empirical", EXACT="exact_empirical_quotient",
    BASE="online_mass_bound", BALANCED="online_balanced_resampling",
    CONTINUE="online_gap_continue", STOP="online_gap_stop")
ONLINE = tuple(METHODS)[2:]
PAIRS = (("STOP", "CONTINUE"), ("CONTINUE", "BALANCED"), ("STOP", "BALANCED"), ("STOP", "BASE"))
DEPLOYMENT = ("expected_total_batches", "maximum_total_batches", "expected_total_draws",
    "maximum_total_draws", "expected_total_distinct_rows", "expected_standalone_seconds",
    "maximum_standalone_seconds", "expected_batch_amortized_seconds", "expected_suffix_seconds")
TOL = 1e-10


def summaries(contexts):
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
    return output


def stopped_nodes(node, reach=1.0):
    if "action" not in node:
        return
    yield node, reach
    for edge in node["children"]:
        yield from stopped_nodes(edge["node"], reach * edge["probability"])


def summarize(payload):
    contexts, runs, checks = [], [], defaultdict(list)
    counts, weighted, reasons = Counter(), Counter(), Counter()
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
                    conversion = 0.0 if alias == "BASE" else run["shared_balanced_conversion" if alias == "BALANCED" else "shared_gap_conversion"]["conversion_seconds"]
                    setup = warm["warm_start_preparation_seconds"] + conversion
                    checks["path_caps"].append(deploy["maximum_total_batches"] <= 128 and deploy["maximum_total_draws"] <= 32768)
                    checks["sample_units"].append(deploy["maximum_total_draws"] == 256 * deploy["maximum_total_batches"] and abs(deploy["expected_total_draws"] - 256 * deploy["expected_total_batches"]) <= TOL)
                    checks["initial_batches"].append(deploy["initial_batches"] == warm["actual_rows_acquired"])
                    checks["conversion_attribution"].append(deploy["integer_count_conversion_seconds"] == conversion)
                    checks["setup_attribution"].append(abs(deploy["expected_standalone_seconds"] - setup - deploy["expected_suffix_seconds"]) <= TOL and abs(deploy["expected_batch_amortized_seconds"] - setup / 10 - deploy["expected_suffix_seconds"]) <= TOL)
                    checks["provider_draws"].append(provider.get("row_requests", 0) == provider.get("first_batch_requests", 0) + provider.get("repeat_batch_requests", 0) and provider.get("physical_draws", 0) == 256 * provider.get("row_requests", 0))
                for node, reach in stopped_nodes(context["methods"]["STOP"]["trace"]):
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
        if identity["case"] == "v6_crossing_rescue_pair_3" and identity["seed"] == 832102 and methods["BASE"]["quality"]["root_extra_regret_over_full_state"] > TOL:
            previous_eight.append(witness)
        if (identity["case"], identity["seed"], identity["query"]) in old_five:
            previous_five.append(witness)
        delta = methods["STOP"]["deployment"]["expected_total_draws"] - methods["CONTINUE"]["deployment"]["expected_total_draws"]
        samples["reduced" if delta < -TOL else "increased" if delta > TOL else "equal"] += 1
    accounting = payload["accounting"]
    checks["declared_contexts"] = [len(runs) == 48, len(contexts) == 480, len(previous_eight) == 8, len(previous_five) == 5]
    checks["physical_conversion_counts"] = [accounting[k] == n for k, n in (("shared_warm_trajectory_count", 48), ("shared_balanced_conversion_count", 48), ("shared_gap_conversion_count", 48), ("actual_conversion_count", 96))]
    for group in ("balanced", "gap"):
        total = math.fsum(run[f"shared_{group}_conversion"]["conversion_seconds"] for run in runs)
        checks["physical_conversion_seconds"].append(abs(total - accounting[f"actual_{group}_conversion_seconds"]) <= TOL)
    checks["physical_warm_draws"] = [accounting["actual_warm_physical_draws"] == sum(run["shared_warm"]["trajectory"]["physical_sample_draws"] for run in runs), accounting["actual_warm_physical_draws"] == 256 * sum(run["shared_warm"]["prefix"]["actual_rows_acquired"] for run in runs)]
    checks["full_acquisition_draws"] = [accounting["full_target_acquisition_count"] == 48, accounting["actual_full_benchmark_physical_draws"] == sum(run["full_target_acquisition"]["physical_sample_draws"] for run in runs)]
    checks["physical_execution_draws"] = [accounting["actual_execution_physical_suffix_draws"] == sum(row["physical_draws"] for row in physical.values())]
    for alias, method in zip(ONLINE, tuple(METHODS.values())[2:]):
        checks["physical_method_totals"].append(all(physical[alias][k] == v for k, v in accounting["actual_execution_provider_counts_by_method"][method].items()))
    reference = {name: {k: v for k, v in payload[name].items() if k in ("prefix_equal_count", "execution_equal_count", "all_prefixes_equal", "all_execution_trees_equal")}
        for name in ("baseline_reference_validation", "balanced_reference_validation")}
    checks["historical_reproduction"] = [reference["baseline_reference_validation"] == dict(prefix_equal_count=48, execution_equal_count=480, all_prefixes_equal=True, all_execution_trees_equal=True), reference["balanced_reference_validation"] == dict(execution_equal_count=480, all_execution_trees_equal=True)]
    pairs = {f"{a}_versus_{b}": comparison(contexts, a, b) for a, b in PAIRS}
    return {"schema": "acfqp.controlled_predictive_gap_analysis.v16", "methods": summaries(contexts), "pairs": pairs,
        "contexts_per_method": len(contexts), "stop_versus_continue_expected_sample_counts": {k: samples[k] for k in ("reduced", "equal", "increased")},
        "by_case": {name: {"methods": summaries(rows), "pairs": {f"{a}_versus_{b}": {
            k: v for k, v in comparison(rows, a, b).items() if k != "nonzero_component_contexts"} for a, b in PAIRS}} for name, rows in by_case.items()},
        "previous_v14_eight": previous_eight, "previous_v13_five": previous_five,
        "stop_diagnostics": {"history_node_counts": dict(counts), "stop_reason_node_counts": dict(reasons),
            "sum_expected_events_over_contexts": dict(weighted), "mean_expected_separated_stops": weighted["separated"] / len(contexts),
            "separated_node_unresolved_fraction": counts["separated_unresolved"] / counts["separated"] if counts["separated"] else None,
            "weighted_separated_unresolved_fraction": weighted["separated_unresolved"] / weighted["separated"] if weighted["separated"] else None},
        "verification": {name: {"passed": all(values), "comparison_count": len(values), "failed_count": sum(not v for v in values)} for name, values in checks.items()},
        "historical_reproduction": reference, "physical_accounting": accounting,
        "scope": "Retained root qualities and history traces only. Stop events use retained true transition weights but are not optimality labels or confidence guarantees. Full empirical benchmarks have larger sample budgets."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_gap_v16.json.gz"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_gap_analysis_v16.json"))
    args = parser.parse_args()
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        report = summarize(json.load(handle))
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: report[k] for k in ("methods", "stop_versus_continue_expected_sample_counts", "stop_diagnostics", "verification")}, indent=2))
