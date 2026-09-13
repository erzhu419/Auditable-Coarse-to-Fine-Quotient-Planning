#!/usr/bin/env python3
"""Summarize retained V15 outcomes without sampling, planning, or truth queries."""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import json
import math
from pathlib import Path

METHODS = {
    "FULL": "full_state_empirical", "EXACT": "exact_empirical_quotient",
    "BASE": "online_mass_bound", "BALANCED": "online_balanced_resampling",
    "DIRECTED": "online_directed_resampling",
}
COMPONENTS = ("reward", "failure", "success", "value")
DEPLOYMENT = ("expected_total_batches", "maximum_total_batches",
    "expected_total_distinct_rows", "expected_total_draws", "expected_standalone_seconds",
    "expected_batch_amortized_seconds", "expected_suffix_seconds")
TOL = 1e-10


def outcome(row):
    return {"action": row["root_action"], "metrics": row["root_metrics"],
        "regret": row["quality"]["root_regret"],
        "extra_regret_over_full": row["quality"]["root_extra_regret_over_full_state"],
        "first_action_optimal": row["quality"]["root_action_in_exact_optimal_set"],
        "full_policy_optimal": row["quality"]["root_optimal_full_policy"],
        "expected_batches": row["deployment"]["expected_total_batches"],
        "maximum_batches": row["deployment"]["maximum_total_batches"]}


def mean(values):
    return math.fsum(values) / len(values)


def methods_summary(contexts):
    result = {}
    for alias in METHODS:
        rows = [context["methods"][alias] for context in contexts]
        result[alias] = {"contexts": len(rows),
            "optimal_first_actions": sum(r["quality"]["root_action_in_exact_optimal_set"] for r in rows),
            "optimal_full_policies": sum(r["quality"]["root_optimal_full_policy"] for r in rows),
            "worse_than_full": sum(r["quality"]["root_extra_regret_over_full_state"] > TOL for r in rows),
            "maximum_regret": max(r["quality"]["root_regret"] for r in rows),
            "mean_components": {k: mean([r["root_metrics"][k] for r in rows]) for k in COMPONENTS},
            "mean_deployment": {k: mean([r["deployment"][k] for r in rows]) for k in DEPLOYMENT}}
    return result


def comparison(contexts, candidate, comparator):
    counts = defaultdict(int)
    differences, nonzero = [], []
    for context in contexts:
        left, right = (context["methods"][name] for name in (candidate, comparator))
        delta = {k: left["root_metrics"][k] - right["root_metrics"][k] for k in COMPONENTS}
        value = delta["value"]
        counts["better" if value > TOL else "worse" if value < -TOL else "equal"] += 1
        differences.append(delta)
        if any(abs(v) > TOL for v in delta.values()):
            nonzero.append({**context["identity"], "candidate_minus_comparator": delta,
                "candidate": outcome(left), "comparator": outcome(right)})
    return {"candidate": candidate, "comparator": comparator,
        **{k: counts[k] for k in ("better", "worse", "equal")},
        "mean_component_difference": {k: mean([d[k] for d in differences]) for k in COMPONENTS},
        "minimum_value_difference": min(d["value"] for d in differences),
        "maximum_value_difference": max(d["value"] for d in differences),
        "nonzero_component_contexts": nonzero}


def summarize(payload):
    contexts = []
    for case in payload["cases"]:
        for run in case["sampled_runs"]:
            if run["status"] != "COMPLETE":
                raise ValueError("The declared campaign has an incomplete run")
            for query in payload["settings"]["query_order"]:
                contexts.append({"identity": {"case": case["case"]["name"],
                    "seed": run["sample_seed"], "query": query},
                    "methods": {alias: run["methods"][method][query] for alias, method in METHODS.items()}})
    pairs = (("BALANCED", "BASE"), ("DIRECTED", "BASE"), ("BALANCED", "FULL"),
        ("DIRECTED", "FULL"), ("DIRECTED", "BALANCED"))
    by_case = defaultdict(list)
    for context in contexts:
        by_case[context["identity"]["case"]].append(context)
    old_five = {(f"v6_crossing_rescue_pair_{case}", seed, query) for case, seed, query in (
        (0, 832101, "goal_1_risk_1"), (0, 832101, "probe_goal_2_risk_0_5"),
        (2, 832101, "goal_1_risk_1"), (2, 832102, "goal_1_risk_1"),
        (2, 832102, "probe_goal_2_risk_0_5"))}
    previous_eight, previous_five = [], []
    for context in contexts:
        identity = context["identity"]
        witness = {**identity, "methods": {alias: outcome(row) for alias, row in context["methods"].items()}}
        if (identity["case"] == "v6_crossing_rescue_pair_3" and identity["seed"] == 832102
                and context["methods"]["BASE"]["quality"]["root_extra_regret_over_full_state"] > TOL):
            previous_eight.append(witness)
        if (identity["case"], identity["seed"], identity["query"]) in old_five:
            previous_five.append(witness)
    if len(contexts) != 480 or len(previous_eight) != 8 or len(previous_five) != 5:
        raise ValueError("Retained context or historical witness counts differ from the declared roster")
    return {"schema": "acfqp.controlled_predictive_quality_analysis.v15", "contexts_per_method": len(contexts),
        "method_names": METHODS, "methods": methods_summary(contexts),
        "pairs": {f"{a}_versus_{b}": comparison(contexts, a, b) for a, b in pairs},
        "by_case": {name: {"methods": methods_summary(rows), "pairs": {
            f"{a}_versus_{b}": {k: v for k, v in comparison(rows, a, b).items()
                if k != "nonzero_component_contexts"} for a, b in pairs}} for name, rows in by_case.items()},
        "previous_v14_eight": previous_eight, "previous_v13_five": previous_five,
        "baseline_reference_validation": {k: v for k, v in payload["baseline_reference_validation"].items()
            if k in ("prefix_equal_count", "execution_equal_count", "all_prefixes_equal", "all_execution_trees_equal")},
        "scope": "Read-only aggregation of retained root outcomes. Nonzero means any component differs by more than 1e-10. No new observations or truth evaluations."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_resampling_v15.json.gz"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_quality_analysis_v15.json"))
    args = parser.parse_args()
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        report = summarize(json.load(handle))
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "methods": report["methods"], "pairs": {
        name: {k: v for k, v in row.items() if k != "nonzero_component_contexts"}
        for name, row in report["pairs"].items()}}, indent=2))
