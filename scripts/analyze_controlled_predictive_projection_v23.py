#!/usr/bin/env python3
"""Analyze frozen initial-row projections of already sampled V22 endpoints."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import (
    ARMS, IDENTITY_FIELDS, PRIMARY, TOL, differences, mean, metrics, monte_carlo_interval)

MODELS = ("FULL", "PROJECTED")
CONTRASTS = ("FULL_VARIANCE_minus_CACHED", "PROJECTED_VARIANCE_minus_CACHED",
             "CACHED_PROJECTED_minus_FULL", "VARIANCE_PROJECTED_minus_FULL",
             "allocation_difference_change")


def contrasts(values):
    full = values["FULL"]["VARIANCE"] - values["FULL"]["CACHED"]
    projected = values["PROJECTED"]["VARIANCE"] - values["PROJECTED"]["CACHED"]
    return {CONTRASTS[0]: full, CONTRASTS[1]: projected,
            CONTRASTS[2]: values["PROJECTED"]["CACHED"] - values["FULL"]["CACHED"],
            CONTRASTS[3]: values["PROJECTED"]["VARIANCE"] - values["FULL"]["VARIANCE"],
            CONTRASTS[4]: projected - full}


def point_estimates(contexts):
    rows = {model: {arm: [metrics(c["arms"][arm]["evaluations"][model]) for c in contexts]
                    for arm in ARMS} for model in MODELS}
    keys = list(rows["FULL"]["CACHED"][0]) if contexts else []
    output = {"paired_context_instances": len(contexts),
        **{model: {arm: {key: mean([r[key] for r in rows[model][arm] if r[key] is not None]) for key in keys}
                   for arm in ARMS} for model in MODELS}, "contrasts": {name: {} for name in CONTRASTS}}
    for key in keys:
        paired = []
        for index in range(len(contexts)):
            values = {model: {arm: rows[model][arm][index][key] for arm in ARMS} for model in MODELS}
            if all(value is not None for group in values.values() for value in group.values()):
                paired.append(contrasts(values))
        for name in CONTRASTS:
            output["contrasts"][name][key] = differences([row[name] for row in paired])
    return output


def stream_statistics(repetitions):
    streams = []
    for rep in repetitions:
        if not rep["complete"]:
            continue
        values = {model: {arm: {key: mean([metrics(c["arms"][arm]["evaluations"][model])[key]
                                         for c in rep["contexts"]]) for key in PRIMARY}
                         for arm in ARMS} for model in MODELS}
        paired = {key: contrasts({model: {arm: values[model][arm][key] for arm in ARMS} for model in MODELS}) for key in PRIMARY}
        streams.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
                        "models": values, "contrasts": paired})
    primary = {"complete_stream_count": len(streams), "unit": "one suffix stream, equal weights over all22 contexts"}
    for key in PRIMARY:
        primary[key] = {name: monte_carlo_interval([row["contrasts"][key][name] for row in streams]) for name in CONTRASTS}
    return primary, streams


def full_reproduction(repetitions, reference):
    """Use all available FULL controls, irrespective of their projected partner."""
    expected_reps = {row["replicate_index"]: row for row in reference["repetitions"]}
    expected_contexts = {row["identity"]["context_index"]: row for row in reference["contexts"]}
    rep_comparisons, context_comparisons = [], []
    by_context = defaultdict(list)
    for rep in repetitions:
        rows = [c for c in rep["contexts"] if all("FULL" in c["arms"].get(arm, {}).get("evaluations", {}) for arm in ARMS)]
        expected = expected_reps[rep["replicate_index"]]
        equal = {"all22_FULL_controls": len(rows) == 22, "base_seed": rep["base_seed"] == expected["base_seed"]}
        for arm in ARMS:
            for key in PRIMARY:
                actual = mean([metrics(c["arms"][arm]["evaluations"]["FULL"])[key] for c in rows])
                equal[f"{arm}.{key}"] = actual == expected[arm][key]
        rep_comparisons.append({"replicate_index": rep["replicate_index"], "field_equal": equal, "passed": all(equal.values())})
        for context in rows:
            by_context[context["identity"]["context_index"]].append(context)
    for index, expected in expected_contexts.items():
        rows = by_context[index]
        equal = {"all64_FULL_controls": len(rows) == 64}
        for arm in ARMS:
            observed = [metrics(c["arms"][arm]["evaluations"]["FULL"]) for c in rows]
            for key, value in expected["point_estimates"][arm].items():
                equal[f"{arm}.{key}"] = mean([r[key] for r in observed if r[key] is not None]) == value
        context_comparisons.append({"context_index": index, "field_equal": equal, "passed": all(equal.values())})
    return {"numeric_comparison": "EXACT", "replicate_comparisons": rep_comparisons,
        "context_comparisons": context_comparisons,
        "all_passed": len(rep_comparisons) == 64 and len(context_comparisons) == 22 and all(row["passed"] for row in rep_comparisons + context_comparisons)}


def source_cost_totals(repetitions):
    output = {}
    for arm in ARMS:
        locals_ = [c["arms"][arm]["source_local"] for rep in repetitions for c in rep["contexts"] if "source_local" in c["arms"].get(arm, {})]
        provider, stages, work = Counter(), Counter(), Counter()
        for local in locals_:
            provider.update(local["provider_counts"])
            stages.update(local["accounting"]["seconds_by_stage"])
            work.update(local["accounting"]["work_counts"])
        return_value = {"actual_arm_count": len(locals_), "provider_counts": dict(provider),
            "seconds_by_stage": dict(stages), "work_counts": dict(work),
            "whole_run_seconds": math.fsum(row["accounting"]["whole_run_seconds"] for row in locals_)}
        output[arm] = return_value
    return output


def summarize(payload, reference):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    planned = {c["context_index"]: c for c in plan["contexts"]}
    identities = [{key: c.get(key) for key in IDENTITY_FIELDS} for c in plan["contexts"]]
    checks = defaultdict(list)
    checks["frozen_cohort"] = [len(planned) == plan["context_count"] == 22,
        Counter(c["group"] for c in plan["contexts"]) == {"improvement": 7, "regression": 13, "old_witness_only": 2},
        sum(c["source_old_witness"] for c in plan["contexts"]) == 10, sum(c["source_v20_changed"] for c in plan["contexts"]) == 20]
    checks["retained_streams"] = [len(repetitions) == plan["replicate_count"] == 64,
        [{"replicate_index": r["replicate_index"], "base_seed": r["base_seed"]} for r in repetitions] == plan["replicates"]]
    checks["frozen_projection_and_evaluation_order"] = [payload["plan_binding_validation"]["passed"],
        payload["all_projected_endpoints_closed_before_oracle"], list(CONTRASTS) == plan["primary_contrasts"],
        payload["restoration_validation"]["all_passed"]] + [row["passed"] for row in payload["plan_snapshot_validation"]]
    checked_reps, issues = [], []
    projection_counts = {arm: Counter() for arm in ARMS}
    projection_work = {arm: Counter() for arm in ARMS}
    for rep in repetitions:
        correct_identity = [{key: c["identity"].get(key) for key in IDENTITY_FIELDS} for c in rep["contexts"]] == identities
        checks["replicate_identities"].append(correct_identity)
        complete_pairs = 0
        for context in rep["contexts"]:
            index = context["identity"]["context_index"]
            fixed = planned[index]
            checks["fixed_target_panel_budget"].append(context["target_key"] == fixed["target_key"] and context["panel"] == fixed["panel"] and context["requested_batch_count"] == fixed["requested_batch_count"] and context["initial_batches"] == fixed["initial_batches"])
            complete = context["source_paired_complete"]
            for arm in ARMS:
                current = context["arms"].get(arm)
                if current is None:
                    complete = False
                    continue
                valid = current["projection_validation"]["passed"] and current["full_control_validation"]["passed"] and all(model in current.get("evaluations", {}) and current["evaluation_restoration"][model]["passed"] for model in MODELS)
                checks["source_and_projection_validation"].append(valid)
                complete &= valid
                for model, evaluation in current.get("evaluations", {}).items():
                    target, panel = evaluation["target"], evaluation["panel"]
                    checks["evaluation_target_and_panel"].append(target["target_key"] == fixed["target_key"] and [s["key"] for s in panel["states"]] == fixed["panel"])
                    checks["A_plus_D_identity"].append(target["identities_pass"] and target["maximum_absolute_identity_residual"] <= TOL)
                if valid:
                    full_actions = current["evaluations"]["FULL"]["target"]["actions"]
                    projected_actions = current["evaluations"]["PROJECTED"]["target"]["actions"]
                    initial_actions = {pair[1] for pair in fixed["initial_row_keys"] if pair[0] == fixed["target_key"]}
                    for action in initial_actions:
                        full, projected = full_actions[action], projected_actions[action]
                        if full["observed"] and projected["observed"]:
                            checks["retained_target_A_unchanged"].append(full["A_transition_error"] == projected["A_transition_error"] and abs((projected["q_hat"] - full["q_hat"]) - (projected["D_continuation_error"] - full["D_continuation_error"])) <= TOL)
                if "projection" in current:
                    projection = current["projection"]
                    checks["retained_information_accounting"].append(projection["original_common_batches"] == fixed["initial_batches"] and projection["retained_action_row_count"] == fixed["initial_observed_row_count"] and projection["original_endpoint_batches"] == projection["retained_model_batches"] + projection["masked_observation_batches"] and projection["masked_draws"] == 256 * projection["masked_observation_batches"] and not projection["original_acquisition_cost_refunded"])
                    checks["no_new_sampling_or_projection_truth"].append(projection["new_provider_calls"] == projection["new_physical_draws"] == projection["truth_calls"] == 0)
                    projection_counts[arm]["endpoint_count"] += 1
                    for key in ("original_endpoint_batches", "original_local_observation_batches", "retained_model_batches", "retained_repeat_batches", "retained_action_row_count", "masked_new_row_count", "masked_observation_batches", "masked_draws", "retained_new_successor_profile_count", "removed_profile_count", "projection_seconds"):
                        projection_counts[arm][key] += projection[key]
                    projection_work[arm].update(projection["projection_work_counts"])
            checks["complete_pair_label"].append(context["paired_complete"] == complete)
            complete_pairs += complete
            if not complete:
                issues.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
                    "identity": context["identity"], "status": context["status"],
                    "arms": {arm: {key: value for key, value in row.items() if key != "evaluations"} for arm, row in context["arms"].items()}})
        complete = correct_identity and complete_pairs == 22
        checks["complete_stream_label"].append(rep["complete"] == complete)
        checked_reps.append({**rep, "complete": complete})
    primary, streams = stream_statistics(checked_reps)
    eligible_contexts = [c for rep in checked_reps if rep["complete"] for c in rep["contexts"]]
    context_points = [{"identity": {key: fixed.get(key) for key in IDENTITY_FIELDS},
        "initial_observed_row_count": fixed["initial_observed_row_count"],
        "point_estimates": point_estimates([c for c in eligible_contexts if c["identity"]["context_index"] == index])}
        for index, fixed in planned.items()]
    reproduction = full_reproduction(repetitions, reference)
    checks["FULL_reproduces_V22"] = [reproduction["all_passed"]]
    source_costs = source_cost_totals(repetitions)
    checks["original_acquisition_costs_retained"] = [source_costs[arm][key] == reference["all_actual_arm_costs"][arm][key]
        for arm in ARMS for key in source_costs[arm]]
    accounting = payload["accounting"]
    checks["historical_cost_copy"] = [payload["source_actual_arm_costs"] == reference["all_actual_arm_costs"],
        accounting["source_physical_batches"] == plan["source_physical_batches"] == reference["accounting"]["local_physical_batches"] == 63232,
        accounting["source_physical_draws"] == plan["source_physical_draws"] == reference["accounting"]["local_physical_draws"] == 16187392]
    checks["V23_new_sampling_zero"] = [payload["new_provider_calls"] == payload["new_physical_draws"] == accounting["new_provider_calls"] == accounting["new_physical_draws"] == 0]
    checks["projection_totals"] = [projection_counts[arm][key] == value for arm in ARMS for key, value in accounting["projection_counts_by_arm"][arm].items()]
    checks["complete_stream_count"] = [payload["complete_repetition_count"] == primary["complete_stream_count"]]
    results = {name: {"passed": all(values), "checked": len(values), "failed": sum(not v for v in values)} for name, values in checks.items()}
    return {
        "schema": "acfqp.controlled_predictive_projection_analysis.v23", "status": payload["status"],
        "declared_stream_count": 64, "complete_stream_count": primary["complete_stream_count"],
        "excluded_stream_count": len(checked_reps) - primary["complete_stream_count"], "context_count": 22,
        "primary": primary, "complete_stream_point_estimates": point_estimates(eligible_contexts),
        "groups": {group: point_estimates([c for c in eligible_contexts if c["identity"]["group"] == group]) for group in ("improvement", "regression", "old_witness_only")},
        "contexts": context_points, "repetitions": streams,
        "stream_statuses": [{"replicate_index": r["replicate_index"], "base_seed": r["base_seed"], "status": r["status"], "complete": r["complete"]} for r in checked_reps],
        "incomplete_context_instances": issues, "FULL_reference_reproduction": reproduction,
        "retained_V22_acquisition_costs": payload["source_actual_arm_costs"],
        "reloaded_source_cost_totals": source_costs, "accounting": accounting,
        "projection_retained_information": {arm: {**dict(projection_counts[arm]), "projection_work_counts": dict(projection_work[arm])} for arm in ARMS},
        "restoration_validation": payload["restoration_validation"], "checks": results,
        "all_analysis_checks_passed": all(row["passed"] for row in results.values()),
        "analysis_seconds": perf_counter() - started,
        "elapsed_seconds_before_report_serialization": payload["elapsed_seconds_before_report_serialization"],
        "scope": "Information ablation of already realized acquisition paths. FULL and PROJECTED retain the original64 suffix streams and22 common starts; stream means are the Monte Carlo units. Projection restores unknown boundaries and can change selected actions without implying worse sampling-estimation accuracy. Removed rows/batches are retained-information counts, not acquisition savings. All original acquisition remains charged; V23 draws no new samples. This does not identify an algorithm that disables structural acquisition and reallocates K, nor complete-policy or independent-scenario effects.",
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_projection_v23.json"))
    parser.add_argument("--reference", type=Path, default=Path("reports/controlled_predictive_repetition_analysis_v22.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_projection_analysis_v23.json"))
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
