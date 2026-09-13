#!/usr/bin/env python3
"""Compare three fixed-budget allocation rules on reused V22 suffix streams."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import (
    IDENTITY_FIELDS, PRIMARY, TOL, differences, mean, metrics, monte_carlo_interval)

ARMS = ("CACHED", "VARIANCE", "FRONTIER")
CONTROLS = ARMS[:2]
PAIRS = (("FRONTIER", "CACHED"), ("FRONTIER", "VARIANCE"), ("VARIANCE", "CACHED"))


def points(contexts):
    values = {arm: [metrics(c["arms"][arm]["evaluation"]) for c in contexts] for arm in ARMS}
    keys = list(values["CACHED"][0]) if contexts else []
    return {"triplet_context_instances": len(contexts),
        **{arm: {key: mean([row[key] for row in values[arm] if row[key] is not None]) for key in keys} for arm in ARMS},
        "comparisons": {f"{candidate}_minus_{control}": {
            key: differences([left[key] - right[key] for left, right in zip(values[candidate], values[control])
                              if left[key] is not None and right[key] is not None]) for key in keys}
            for candidate, control in PAIRS}}


def stream_statistics(repetitions):
    streams = []
    for repetition in repetitions:
        if not repetition["complete"]:
            continue
        values = {arm: {key: mean([metrics(c["arms"][arm]["evaluation"])[key] for c in repetition["contexts"]]) for key in PRIMARY} for arm in ARMS}
        streams.append({"replicate_index": repetition["replicate_index"], "base_seed": repetition["base_seed"],
            "arms": values, "comparisons": {f"{candidate}_minus_{control}": {
                key: values[candidate][key] - values[control][key] for key in PRIMARY} for candidate, control in PAIRS}})
    primary = {"complete_stream_count": len(streams), "unit": "one reused suffix stream, equal weights over all22 contexts"}
    for key in PRIMARY:
        primary[key] = {f"{candidate}_minus_{control}": monte_carlo_interval([
            row["comparisons"][f"{candidate}_minus_{control}"][key] for row in streams]) for candidate, control in PAIRS}
    return primary, streams


def control_reproduction(repetitions, reference):
    expected_reps = {r["replicate_index"]: r for r in reference["repetitions"]}
    by_context, rep_checks, context_checks = defaultdict(list), [], []
    for rep in repetitions:
        contexts = [c for c in rep["contexts"] if all("evaluation" in c["arms"].get(arm, {}) for arm in CONTROLS)]
        expected = expected_reps[rep["replicate_index"]]
        equal = {"all22_controls": len(contexts) == 22, "base_seed": rep["base_seed"] == expected["base_seed"]}
        for arm in CONTROLS:
            for key in PRIMARY:
                equal[f"{arm}.{key}"] = mean([metrics(c["arms"][arm]["evaluation"])[key] for c in contexts]) == expected[arm][key]
        rep_checks.append({"replicate_index": rep["replicate_index"], "field_equal": equal, "passed": all(equal.values())})
        for context in contexts:
            by_context[context["identity"]["context_index"]].append(context)
    for expected in reference["contexts"]:
        index = expected["identity"]["context_index"]
        contexts = by_context[index]
        equal = {"all64_controls": len(contexts) == 64}
        for arm in CONTROLS:
            values = [metrics(c["arms"][arm]["evaluation"]) for c in contexts]
            for key, value in expected["point_estimates"][arm].items():
                equal[f"{arm}.{key}"] = mean([row[key] for row in values if row[key] is not None]) == value
        context_checks.append({"context_index": index, "field_equal": equal, "passed": all(equal.values())})
    return {"numeric_comparison": "EXACT", "replicate_comparisons": rep_checks, "context_comparisons": context_checks,
        "all_passed": len(rep_checks) == 64 and len(context_checks) == 22 and all(row["passed"] for row in rep_checks + context_checks)}


def costs(repetitions):
    result = {}
    for arm in ARMS:
        rows = [c["arms"][arm]["local"] for r in repetitions for c in r["contexts"] if "local" in c["arms"].get(arm, {})]
        provider, stages, work, stops = Counter(), Counter(), Counter(), Counter()
        for local in rows:
            provider.update(local["provider_counts"])
            stages.update(local["accounting"]["seconds_by_stage"])
            work.update(local["accounting"]["work_counts"])
            stops[local["stop_reason"]] += 1
            index = local["first_original_stop_index"]
            stops["gap_separated"] += index is not None
            stops["batches_after_first_original_stop"] += local["completed_batches"] - index if index is not None else 0
        new_row_repeats = sum(row["repeat_batches_on_rows_absent_from_common"] for row in rows)
        wall = [row["accounting"]["whole_run_seconds"] for row in rows]
        result[arm] = {"actual_arm_count": len(rows), "provider_counts": dict(provider),
            "seconds_by_stage": dict(stages), "work_counts": dict(work),
            "whole_run_seconds": math.fsum(wall), "mean_arm_seconds": mean(wall),
            "local_first_observed_rows": provider.get("first_batch_requests", 0),
            "repeat_batches_on_new_rows": new_row_repeats,
            "repeat_batches_on_initial_rows": provider.get("repeat_batch_requests", 0) - new_row_repeats,
            "frontier_selection_diagnostics": {key: work.get(key, 0) for key in (
                "frontier_selection_calls", "frontier_original_structure_selected", "frontier_extension_calls",
                "frontier_extension_selected", "frontier_to_balanced_fallbacks")},
            "stop_diagnostics": dict(stops)}
    return result


def summarize(payload, reference):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    planned = {row["context_index"]: row for row in plan["contexts"]}
    identities = [{key: row.get(key) for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    checks = defaultdict(list)
    checks["frozen_cohort"] = [len(planned) == plan["context_count"] == 22,
        Counter(c["group"] for c in plan["contexts"]) == {"improvement": 7, "regression": 13, "old_witness_only": 2},
        sum(c["source_old_witness"] for c in plan["contexts"]) == 10,
        sum(c["source_v20_changed"] for c in plan["contexts"]) == 20,
        sum(c["requested_batch_count"] for c in plan["contexts"]) == plan["batches_per_arm_per_replicate"] == 494]
    checks["frozen_reused_streams_and_comparisons"] = [len(repetitions) == plan["replicate_count"] == 64,
        [{"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"]} for rep in repetitions] == plan["replicates"],
        [list(pair) for pair in PAIRS] == plan["primary_comparisons"], list(ARMS) == plan["arms"]]
    checks["persistence_before_truth"] = [payload["all_sampling_endpoints_closed_before_oracle"], not payload["endpoint_reload_uses_provider"]]
    checks["common_restoration"] = [payload["restoration_validation"]["all_passed"], payload["plan_binding_validation"]["passed"]] + [row["passed"] for row in payload["plan_snapshot_validation"]]
    checked, incomplete = [], []
    for rep in repetitions:
        same_ids = [{key: c["identity"].get(key) for key in IDENTITY_FIELDS} for c in rep["contexts"]] == identities
        checks["replicate_identities"].append(same_ids)
        complete_count = 0
        for context in rep["contexts"]:
            fixed = planned[context["identity"]["context_index"]]
            K, initial = fixed["requested_batch_count"], fixed["initial_batches"]
            checks["fixed_K"].append(context["requested_batch_count"] == K and context["initial_batches"] == initial and initial + K <= 128)
            offset = (rep["replicate_index"] + fixed["context_index"]) % 3
            checks["rotating_three_arms"].append(context["run_order"] == list(ARMS[offset:] + ARMS[:offset]))
            complete = context["initial_snapshot_validation"]["passed"] and set(context["arms"]) == set(ARMS)
            for arm, current in context["arms"].items():
                local, provider = current["local"], current["local"]["provider_counts"]
                n = local["completed_batches"]
                reset = local["initial_batches_matches_common"] and local["initial_batches"] == initial
                checks["common_reset"].append(reset)
                checks["actual_batches_and_draws"].append(local["requested_batch_count"] == K and 0 <= n <= K and local["final_batches"] == initial + n and local["actual_draws"] == 256 * n and provider.get("row_requests", 0) == n and provider.get("physical_draws", 0) == 256 * n and provider.get("first_batch_requests", 0) + provider.get("repeat_batch_requests", 0) == n)
                checks["repeat_classification"].append(0 <= local["repeat_batches_on_rows_absent_from_common"] <= provider.get("repeat_batch_requests", 0))
                checks["completion_labels"].append(local["completed_fixed_budget"] == (n == K))
                restored = current["endpoint_restoration"]["passed"]
                checks["endpoint_restoration"].append(restored)
                valid = n == K and reset and restored
                if arm in CONTROLS:
                    historical = current["first_request_validation"]["passed"] and current["source_reference_validation"]["passed"]
                    checks["old_control_trace_reproduction"].append(historical)
                    valid &= historical
                complete &= valid
                if "evaluation" in current:
                    target, panel = current["evaluation"]["target"], current["evaluation"]["panel"]
                    checks["fixed_target_panel"].append(target["target_key"] == fixed["target_key"] and [s["key"] for s in panel["states"]] == fixed["panel"])
                    checks["A_plus_D_identity"].append(target["identities_pass"] and target["maximum_absolute_identity_residual"] <= TOL)
            checks["triplet_complete_label"].append(context["paired_complete"] == complete)
            complete_count += complete
            if not complete:
                incomplete.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
                    "identity": context["identity"], "status": context["status"],
                    "arms": {arm: {key: value for key, value in row.items() if key != "evaluation"} for arm, row in context["arms"].items()}})
        complete = same_ids and complete_count == 22
        checks["stream_complete_label"].append(rep["complete"] == complete)
        checked.append({**rep, "complete": complete})
    all_costs = costs(repetitions)
    reproduction = control_reproduction(repetitions, reference)
    checks["V22_control_metric_reproduction"] = [reproduction["all_passed"]]
    checks["V22_control_trace_summary"] = [payload["source_reference_validation"]["all_passed"]]
    checks["V22_control_provider_reproduction"] = [all_costs[arm]["provider_counts"] == reference["all_actual_arm_costs"][arm]["provider_counts"] for arm in CONTROLS]
    primary, streams = stream_statistics(checked)
    complete_contexts = [c for rep in checked if rep["complete"] for c in rep["contexts"]]
    account = payload["accounting"]
    arm_count = sum(row["actual_arm_count"] for row in all_costs.values())
    checks["total_physical_work"] = [account.get("local_arm_run_count", 0) == account.get("reset_from_original_common_snapshot_count", 0) == arm_count,
        account["warm_provider_calls"] == account["warm_physical_draws"] == 0,
        account["local_physical_batches"] == sum(row["provider_counts"].get("row_requests", 0) for row in all_costs.values()),
        account["local_physical_draws"] == sum(row["provider_counts"].get("physical_draws", 0) for row in all_costs.values()),
        abs(account.get("local_allocation_wall_seconds", 0) - math.fsum(row["whole_run_seconds"] for row in all_costs.values())) <= TOL]
    checks["per_arm_provider_totals"] = [all_costs[arm]["provider_counts"] == account["provider_counts_by_arm"][arm] for arm in ARMS]
    checks["complete_stream_count"] = [primary["complete_stream_count"] == payload["complete_repetition_count"]]
    if primary["complete_stream_count"] == 64:
        checks["full_budget"] = [arm_count == plan["expected_arm_count"] == 4224,
            account["local_physical_batches"] == plan["expected_physical_batches"] == 94848,
            account["local_physical_draws"] == plan["expected_physical_draws"] == 24281088]
    results = {name: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for name, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_frontier_analysis.v24", "status": payload["status"],
        "complete_stream_count": primary["complete_stream_count"], "excluded_stream_count": len(checked) - primary["complete_stream_count"],
        "primary": primary, "complete_stream_point_estimates": points(complete_contexts),
        "groups": {group: points([c for c in complete_contexts if c["identity"]["group"] == group]) for group in ("improvement", "regression", "old_witness_only")},
        "contexts": [{"identity": {key: fixed.get(key) for key in IDENTITY_FIELDS}, "requested_batch_count": fixed["requested_batch_count"],
            "point_estimates": points([c for c in complete_contexts if c["identity"]["context_index"] == index])} for index, fixed in planned.items()],
        "repetitions": streams, "stream_statuses": [{key: rep[key] for key in ("replicate_index", "base_seed", "complete", "status")} for rep in checked],
        "incomplete_context_instances": incomplete, "all_actual_arm_costs": all_costs,
        "V22_control_metric_reproduction": reproduction, "accounting": account,
        "source_reference_validation": payload["source_reference_validation"],
        "restoration_validation": payload["restoration_validation"], "checks": results,
        "all_analysis_checks_passed": all(row["passed"] for row in results.values()),
        "analysis_seconds": perf_counter() - started,
        "elapsed_seconds_before_report_serialization": payload["elapsed_seconds_before_report_serialization"],
        "scope": "Three allocation rules on the fixed exposed V21 starts and reused V22 suffix streams. Complete streams with all22 valid triplets are the Monte Carlo units, not individual contexts or dependent panel states. Intervals are descriptive and not a new formal Gate. All physical provider calls and costs are retained, including incomplete triplets; first-observed row counts sum local arm instances. Target regret assumes optimal continuation and is not full online policy value. Costs compare this run's contemporaneous arms, not old wall-clock timings.",
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_frontier_v24.json"))
    parser.add_argument("--reference", type=Path, default=Path("reports/controlled_predictive_repetition_analysis_v22.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_frontier_analysis_v24.json"))
    args = parser.parse_args()
    started = perf_counter()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    read_seconds = perf_counter() - started
    result = summarize(payload, reference)
    result["analysis_result_read_seconds"] = read_seconds
    started = perf_counter()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "complete_stream_count": result["complete_stream_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"],
        "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
