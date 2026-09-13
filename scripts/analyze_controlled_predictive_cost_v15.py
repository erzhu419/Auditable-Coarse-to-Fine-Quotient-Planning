#!/usr/bin/env python3
"""Describe retained V15 costs; never acquire data, plan, or re-evaluate policies.

The input is opened once as gzip JSON. Shared preparation is counted once in
physical totals, and separately attributed to the methods that use it. The
result keeps deployment expectations distinct from counterfactual audit work.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
import math
from pathlib import Path
from time import perf_counter


ONLINE = ("online_mass_bound", "online_balanced_resampling", "online_directed_resampling")
METHODS = ("full_state_empirical", "exact_empirical_quotient", *ONLINE)
BATCH_SIZE = 256
TOLERANCE = 1e-9


def _same(left, right):
    return math.isclose(left, right, rel_tol=0.0, abs_tol=TOLERANCE)


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values)


def _sum_counts(values):
    result = Counter()
    for value in values:
        result.update(value)
    return dict(result)


def _paired_consumption(contexts):
    pairs = []
    for identity, run, name in contexts:
        left = run["methods"]["online_directed_resampling"][name]["deployment"]
        right = run["methods"]["online_balanced_resampling"][name]["deployment"]
        pairs.append((identity, left, right))
    result = {"query_context_count": len(pairs), "difference_direction": "DIRECTED_MINUS_BALANCED",
              "expected_count_numeric_tolerance": TOLERANCE, "fields": {}}
    for field in ("expected_total_batches", "maximum_total_batches"):
        comparisons = [{**identity, "directed": left[field], "balanced": right[field],
                        "difference": left[field] - right[field]} for identity, left, right in pairs]
        exact = sum(row["difference"] == 0 for row in comparisons)
        tolerance = TOLERANCE if field.startswith("expected") else 0
        equal = sum(abs(row["difference"]) <= tolerance for row in comparisons)
        result["fields"][field] = {
            "exact_equal_count": exact, "exact_different_count": len(comparisons) - exact,
            "numeric_equal_count": equal, "numeric_different_count": len(comparisons) - equal,
            "directed_more_count": sum(row["difference"] > tolerance for row in comparisons),
            "directed_less_count": sum(row["difference"] < -tolerance for row in comparisons),
            "mean_difference": _mean(row["difference"] for row in comparisons),
            "maximum_absolute_difference": max(abs(row["difference"]) for row in comparisons),
            "largest_absolute_difference_context": max(comparisons, key=lambda row: abs(row["difference"])),
            "minimum_difference_context": min(comparisons, key=lambda row: row["difference"]),
            "maximum_difference_context": max(comparisons, key=lambda row: row["difference"]),
        }
    result["both_fields_exact_equal_count"] = sum(
        left["expected_total_batches"] == right["expected_total_batches"]
        and left["maximum_total_batches"] == right["maximum_total_batches"] for _, left, right in pairs)
    result["both_fields_numeric_equal_count"] = sum(
        _same(left["expected_total_batches"], right["expected_total_batches"])
        and left["maximum_total_batches"] == right["maximum_total_batches"] for _, left, right in pairs)
    result["scope"] = "A common128-batch upper limit does not imply equal actual consumption; terminal/no-eligible stopping and execution histories can differ."
    return result


def analyze_costs(payload):
    records = payload["cases"]
    all_runs = [run for record in records for run in record["sampled_runs"]]
    runs = [run for run in all_runs if run["status"] == "COMPLETE"]
    queries = payload["settings"]["query_order"]
    contexts = [({"case_name": record["case"]["name"], "sample_seed": run["sample_seed"], "query_name": name}, run, name)
                for record in records for run in record["sampled_runs"] if run["status"] == "COMPLETE" for name in queries]
    accounting = payload["accounting"]
    checks, findings = Counter(), []

    def check(name, passed, context=None, actual=None, expected=None):
        checks[name] += 1
        if not passed:
            findings.append({"check": name, "context": context, "actual": actual, "expected": expected})

    check("all48_declared_runs_completed", len(runs) == len(all_runs) == 48,
          actual={"complete": len(runs), "declared": len(all_runs)}, expected=48)
    check("all480_query_contexts_retained", len(contexts) == 480, actual=len(contexts), expected=480)
    methods = {}
    for method in METHODS:
        rows = [run["methods"][method][name] for _, run, name in contexts]
        deployments = [row["deployment"] for row in rows]
        stages = set().union(*(row["expected_seconds_by_stage"] for row in deployments))
        report = {
            "query_context_count": len(rows),
            "mean_expected_batches": _mean(row["expected_total_batches"] for row in deployments),
            "mean_expected_distinct_rows": _mean(row["expected_total_distinct_rows"] for row in deployments),
            "mean_expected_first_batches_including_warm": _mean(row["expected_total_distinct_rows"] for row in deployments),
            "mean_expected_repeat_batches": _mean(row["expected_total_batches"] - row["expected_total_distinct_rows"] for row in deployments),
            "maximum_path_batches": max(row["maximum_total_batches"] for row in deployments),
            "maximum_path_distinct_rows": max(row["maximum_total_distinct_rows"] for row in deployments),
            "mean_expected_draws": _mean(row["expected_total_draws"] for row in deployments),
            "mean_standalone_ms": 1000 * _mean(row["expected_standalone_seconds"] for row in deployments),
            "mean_ten_query_amortized_ms": 1000 * _mean(row["expected_batch_amortized_seconds"] for row in deployments),
            "mean_suffix_ms": 1000 * _mean(row["expected_suffix_seconds"] for row in deployments),
            "mean_suffix_ms_by_stage": {stage: 1000 * _mean(row["expected_seconds_by_stage"].get(stage, 0) for row in deployments) for stage in sorted(stages)},
            "physical_suffix_provider_counts": _sum_counts(row["physical_audit"].get("provider_counts", {}) for row in rows),
            "scope": "Per episode deployment means; physical suffix counts separately sum all enumerated histories. Full benchmarks are not128-batch methods.",
        }
        if method in ONLINE:
            report["mean_shared_warm_attributed_ms"] = 1000 * _mean(row["shared_warm_preparation_seconds"] for row in deployments)
            report["mean_conversion_attributed_ms"] = 1000 * _mean(row["integer_count_conversion_seconds"] for row in deployments)
            report["mean_total_initial_preparation_ms"] = 1000 * _mean(row["warm_prefix_preparation_seconds"] for row in deployments)
            physical = report["physical_suffix_provider_counts"]
            for field in ("row_requests", "first_batch_requests", "repeat_batch_requests", "physical_draws", "exact_transition_row_calls", "support_entries_enumerated", "sampled_successor_entries_returned"):
                check("physical_suffix_method_total", physical.get(field, 0) == accounting["actual_execution_provider_counts_by_method"][method][field],
                      {"method": method, "field": field}, physical.get(field, 0), accounting["actual_execution_provider_counts_by_method"][method][field])
        for (identity, run, name), result in zip(contexts, rows):
            context = identity | {"method": method}
            row = result["deployment"]
            check("batch_to_draw_conversion", _same(row["expected_total_draws"], BATCH_SIZE * row["expected_total_batches"])
                  and row["maximum_total_draws"] == BATCH_SIZE * row["maximum_total_batches"], context)
            check("distinct_rows_not_more_than_batches", row["expected_total_distinct_rows"] <= row["expected_total_batches"] + TOLERANCE
                  and row["maximum_total_distinct_rows"] <= row["maximum_total_batches"], context)
            check("suffix_stage_seconds_sum", _same(row["expected_suffix_seconds"], math.fsum(row["expected_seconds_by_stage"].values())), context)
            if method not in ONLINE:
                continue
            warm = run["shared_warm"]["prefix"]
            conversion = 0.0 if method == ONLINE[0] else run["shared_candidate_conversion"]["conversion_seconds"]
            warm_seconds = warm["warm_start_preparation_seconds"]
            total_setup = warm_seconds + conversion
            check("online128_batch_path_cap", row["expected_total_batches"] <= row["maximum_total_batches"] + TOLERANCE
                  and row["maximum_total_batches"] <= 128 and result["path_batch_budget_satisfied"], context,
                  row["maximum_total_batches"], "<=128")
            check("warm_and_conversion_attribution", _same(row["shared_warm_preparation_seconds"], warm_seconds)
                  and _same(row["integer_count_conversion_seconds"], conversion)
                  and _same(row["warm_prefix_preparation_seconds"], total_setup), context)
            check("standalone_and_ten_query_attribution", row["prefix_amortization_query_count"] == len(queries) == 10
                  and _same(row["expected_standalone_seconds"], total_setup + row["expected_suffix_seconds"])
                  and _same(row["expected_batch_amortized_seconds"], total_setup / 10 + row["expected_suffix_seconds"]), context)
            work = row["expected_suffix_work_counts"]
            first = work.get("provider_first_batch_requests", 0)
            repeat = work.get("provider_repeat_batch_requests", 0)
            warm_batches = warm["actual_rows_acquired"]
            check("deployment_first_repeat_and_warm_balance", row["initial_batches"] == warm_batches
                  and row["initial_distinct_rows"] == warm_batches
                  and _same(row["expected_total_batches"], warm_batches + first + repeat)
                  and _same(row["expected_total_distinct_rows"], warm_batches + first)
                  and _same(row["expected_total_draws"], BATCH_SIZE * warm_batches + work.get("provider_physical_draws", 0)), context)
            physical = result["physical_audit"]["provider_counts"]
            requests = physical.get("row_requests", 0)
            check("physical_batch_calls_are_all_paid", requests == physical.get("first_batch_requests", 0) + physical.get("repeat_batch_requests", 0)
                  and physical.get("physical_draws", 0) == BATCH_SIZE * requests
                  and physical.get("exact_transition_row_calls", 0) == requests, context)
        methods[method] = report

    warm_draws = sum(run["shared_warm"]["trajectory"]["physical_sample_draws"] for run in all_runs)
    suffix_counts = _sum_counts(methods[method]["physical_suffix_provider_counts"] for method in ONLINE)
    full_draws = sum(run["full_target_acquisition"]["physical_sample_draws"] for run in runs)
    conversion_seconds = math.fsum(run["shared_candidate_conversion"]["conversion_seconds"] for run in all_runs)
    for run in all_runs:
        warm = run["shared_warm"]
        converted = run["shared_candidate_conversion"]
        check("shared_warm_first_batches_only", warm["trajectory"]["actual_rows_acquired"] == warm["prefix"]["actual_rows_acquired"]
              and warm["trajectory"]["physical_sample_draws"] == BATCH_SIZE * warm["prefix"]["actual_rows_acquired"])
        check("one_conversion_preserves_initial_counts", converted["initial_batches"] == converted["initial_distinct_rows"] == warm["prefix"]["actual_rows_acquired"]
              and converted["physically_converted_once_shared_by_candidates"])
    for field, computed in (("actual_warm_physical_draws", warm_draws),
                            ("actual_execution_physical_suffix_draws", suffix_counts.get("physical_draws", 0)),
                            ("actual_full_benchmark_physical_draws", full_draws)):
        check("physical_acquisition_totals", accounting[field] == computed, {"field": field}, accounting[field], computed)
    check("shared_work_counted_once", accounting["shared_warm_trajectory_count"] == accounting["shared_candidate_conversion_count"] == len(all_runs)
          and accounting["full_target_acquisition_count"] == len(runs)
          and _same(accounting["actual_shared_conversion_seconds"], conversion_seconds))
    check("source_cost_zero", accounting["source_fits"] == 0 and accounting["source_setup_seconds"] == 0)
    reference = payload["baseline_reference_validation"]
    check("baseline48_warm_and480_tree_reproduction", reference["prefix_comparison_count"] == reference["prefix_equal_count"] == 48
          and reference["execution_comparison_count"] == reference["execution_equal_count"] == 480
          and reference["all_prefixes_equal"] and reference["all_execution_trees_equal"])
    total_draws = warm_draws + suffix_counts.get("physical_draws", 0) + full_draws
    return {
        "schema": "controlled_predictive_cost_analysis_v15",
        "status": "PASS" if not findings else "ACCOUNTING_FINDINGS",
        "source_status": payload["status"],
        "case_seed_runs": len(runs), "query_contexts_per_method": len(contexts),
        "methods": methods,
        "directed_versus_balanced_actual_consumption": _paired_consumption(contexts),
        "shared_preparation": {
            "physical_warm_trajectories": len(all_runs), "warm_first_batches": warm_draws // BATCH_SIZE,
            "warm_physical_draws": warm_draws,
            "mean_warm_preparation_ms": 1000 * _mean(run["shared_warm"]["prefix"]["warm_start_preparation_seconds"] for run in all_runs),
            "physical_integer_count_conversions": len(all_runs),
            "actual_conversion_seconds_counted_once": conversion_seconds,
            "mean_conversion_ms": 1000 * conversion_seconds / len(all_runs),
            "conversion_work_counts": _sum_counts(run["shared_candidate_conversion"]["work_counts"] for run in all_runs),
        },
        "physical_acquisition": {
            "warm_first_batches": warm_draws // BATCH_SIZE,
            "all_history_suffix_counts": suffix_counts,
            "full_benchmark_shared_first_batches": full_draws // BATCH_SIZE,
            "full_benchmark_physical_draws_counted_once": full_draws,
            "total_first_batch_requests": warm_draws // BATCH_SIZE + suffix_counts.get("first_batch_requests", 0) + full_draws // BATCH_SIZE,
            "total_repeat_batch_requests": suffix_counts.get("repeat_batch_requests", 0),
            "total_batch_requests": total_draws // BATCH_SIZE, "total_physical_draws": total_draws,
            "first_request_scope": "A first batch can be physically requested again on another history. This is a request count, not the cardinality of a global row-key union.",
        },
        "recorded_physical_time_components_seconds": {key: value for key, value in accounting.items() if key.endswith("seconds")},
        "time_aggregation_scope": "The history-evaluation total already includes initial query and sibling clones. The warm-trajectory total already includes its prefix snapshot. Do not add these subcomponents again, or add method-attributed preparation to physical totals. Counterfactual branch totals are not deployment expectations.",
        "checks_executed_by_name": dict(checks), "finding_count": len(findings), "findings": findings,
        "baseline_reference_validation": {key: reference[key] for key in ("prefix_comparison_count", "prefix_equal_count", "execution_comparison_count", "execution_equal_count", "all_prefixes_equal", "all_execution_trees_equal")},
        "scope": "Descriptive analysis of the single retained V15 run. No sampling, planning, new policy evaluation, confidence claim, or change to the frozen experiment.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Completed V15 raw JSON gzip artifact")
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_cost_analysis_v15.json"))
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    started = perf_counter()
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    loaded = perf_counter()
    result = analyze_costs(payload)
    result.update(source_artifact=str(args.input), source_gzip_bytes=args.input.stat().st_size,
                  source_load_seconds=loaded - started, cost_analysis_seconds=perf_counter() - loaded)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "findings": result["finding_count"],
                      "output": str(args.output.resolve()), "output_bytes": args.output.stat().st_size}))


if __name__ == "__main__":
    main()
