#!/usr/bin/env python3
"""Summarize frozen signed-error counterfactuals without sampling or oracle access."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import (
    IDENTITY_FIELDS, TOL, differences, mean, monte_carlo_interval)

ARMS = ("CACHED", "VARIANCE", "FRONTIER")
MODES = ("RAW", "REMOVE_A", "REMOVE_D")
PAIRS = (("FRONTIER", "CACHED"), ("FRONTIER", "VARIANCE"), ("VARIANCE", "CACHED"))
METRICS = {"target_wrong_action_rate": "wrong", "target_mean_local_regret": "regret"}


def mode_value(context, arm, mode, field):
    return context["arms"][arm]["diagnostic"]["modes"][mode][field]


def level_interval(values):
    return {key: value for key, value in monte_carlo_interval(values).items() if key not in ("negative", "zero", "positive")}


def mode_streams(repetitions, mode):
    return [{"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
             "arms": {arm: {name: mean([float(mode_value(c, arm, mode, field)) for c in rep["contexts"]])
                            for name, field in METRICS.items()} for arm in ARMS}}
            for rep in repetitions]


def mode_statistics(streams):
    return {"stream_count": len(streams),
        "arms": {arm: {metric: level_interval([r["arms"][arm][metric] for r in streams]) for metric in METRICS} for arm in ARMS},
        "comparisons": {f"{candidate}_minus_{control}": {metric: monte_carlo_interval([
            row["arms"][candidate][metric] - row["arms"][control][metric] for row in streams]) for metric in METRICS}
            for candidate, control in PAIRS}}


def primary_statistics(raw_repetitions, cf_repetitions):
    raw = mode_streams(raw_repetitions, "RAW")
    common = {mode: mode_streams(cf_repetitions, mode) for mode in MODES}
    corrections, difference_changes = {}, {}
    for mode in MODES[1:]:
        corrections[mode], difference_changes[mode] = {}, {}
        for arm in ARMS:
            entry = {metric: monte_carlo_interval([cf["arms"][arm][metric] - original["arms"][arm][metric]
                for original, cf in zip(common["RAW"], common[mode])]) for metric in METRICS}
            for label, field in (("repair_rate", "raw_wrong_repaired"), ("new_error_rate", "raw_correct_new_error"), ("choice_changed_rate", "choice_changed")):
                values = [mean([float(mode_value(c, arm, mode, field)) for c in rep["contexts"]]) for rep in cf_repetitions]
                entry[label] = level_interval(values)
            corrections[mode][arm] = entry
        for control in ("CACHED", "VARIANCE"):
            difference_changes[mode][f"FRONTIER_minus_{control}"] = {metric: monte_carlo_interval([
                (cf["arms"]["FRONTIER"][metric] - cf["arms"][control][metric]) -
                (raw_row["arms"]["FRONTIER"][metric] - raw_row["arms"][control][metric])
                for raw_row, cf in zip(common["RAW"], common[mode])]) for metric in METRICS}
    return {"unit": "one retained suffix stream, equal weights over all22 contexts",
        "RAW_all_evaluable": mode_statistics(raw),
        "common_counterfactual_mask": {mode: mode_statistics(common[mode]) for mode in MODES},
        "counterfactual_minus_RAW": corrections, "excess_difference_changes": difference_changes}, {"RAW_all_evaluable": raw, **common}


def point_estimates(contexts, modes=MODES):
    return {"context_instances": len(contexts),
        **{mode: {arm: {metric: mean([float(mode_value(c, arm, mode, field)) for c in contexts])
                       for metric, field in METRICS.items()} for arm in ARMS} for mode in modes},
        "comparisons": {mode: {f"{candidate}_minus_{control}": {metric: differences([
            float(mode_value(c, candidate, mode, field)) - float(mode_value(c, control, mode, field)) for c in contexts])
            for metric, field in METRICS.items()} for candidate, control in PAIRS} for mode in modes}}


def discordant_groups(contexts):
    result = {}
    for control in ("CACHED", "VARIANCE"):
        pair = {}
        for label, wrong_frontier in (("frontier_wrong_control_correct", True), ("frontier_correct_control_wrong", False)):
            chosen = [c for c in contexts if bool(mode_value(c, "FRONTIER", "RAW", "wrong")) == wrong_frontier
                      and bool(mode_value(c, control, "RAW", "wrong")) != wrong_frontier]
            modes = {}
            for mode in MODES[1:]:
                cells = Counter()
                for c in chosen:
                    frontier_wrong = mode_value(c, "FRONTIER", mode, "wrong")
                    control_wrong = mode_value(c, control, mode, "wrong")
                    cells["both_wrong" if frontier_wrong and control_wrong else "both_correct" if not frontier_wrong and not control_wrong
                          else "frontier_wrong_control_correct" if frontier_wrong else "frontier_correct_control_wrong"] += 1
                modes[mode] = {"counterfactual_outcome_counts": dict(cells), **{arm: {
                    "repaired": sum(mode_value(c, arm, mode, "raw_wrong_repaired") for c in chosen),
                    "new_error": sum(mode_value(c, arm, mode, "raw_correct_new_error") for c in chosen)} for arm in ("FRONTIER", control)}}
            pair[label] = {"context_instance_count": len(chosen), **modes}
        result[f"FRONTIER_minus_{control}"] = pair
    return result


def raw_reproduction(repetitions, reference):
    expected_reps = {row["replicate_index"]: row for row in reference["repetitions"]}
    actual_streams = mode_streams(repetitions, "RAW")
    rep_checks, context_checks = [], []
    for row in actual_streams:
        expected = expected_reps[row["replicate_index"]]
        equal = row["base_seed"] == expected["base_seed"] and row["arms"] == expected["arms"]
        rep_checks.append({"replicate_index": row["replicate_index"], "passed": equal})
    rows = [c for rep in repetitions for c in rep["contexts"]]
    for expected in reference["contexts"]:
        index = expected["identity"]["context_index"]
        chosen = [c for c in rows if c["identity"]["context_index"] == index]
        equal = {"all64_instances": len(chosen) == 64}
        for arm in ARMS:
            for metric, field in METRICS.items():
                equal[f"{arm}.{metric}"] = mean([float(mode_value(c, arm, "RAW", field)) for c in chosen]) == expected["point_estimates"][arm][metric]
        context_checks.append({"context_index": index, "field_equal": equal, "passed": all(equal.values())})
    return {"replicate_comparisons": rep_checks, "context_comparisons": context_checks,
        "numeric_comparison": "EXACT", "all_passed": len(rep_checks) == 64 and len(context_checks) == 22 and all(row["passed"] for row in rep_checks + context_checks)}


def margin_points(rows):
    eligible = [row for row in rows if row["A_transition_error_difference"] is not None and row["D_continuation_error_difference"] is not None]
    return {"record_count": len(rows), "decomposable_count": len(eligible),
        "signed_differences": {field: differences([row[field] for row in rows if row[field] is not None]) for field in (
            "q_hat_difference", "q_star_difference", "A_transition_error_difference", "D_continuation_error_difference")},
        "opposite_sign_A_D_count": sum(row["opposite_sign_A_D"] for row in eligible),
        "opposite_sign_A_D_rate": mean([float(row["opposite_sign_A_D"]) for row in eligible]),
        "mean_cancelled_absolute_error": mean([row["cancelled_absolute_error"] for row in eligible])}


def signed_points(contexts):
    result = {}
    for arm in ARMS:
        diagnoses = [c["arms"][arm]["diagnostic"] for c in contexts]
        pairs = defaultdict(list)
        for diagnostic in diagnoses:
            for row in diagnostic["pair_margins"]:
                pairs["_minus_".join(row["actions"])].append(row)
        choice_pairs, batches = {}, {}
        for mode in MODES:
            rows = []
            for diagnostic in diagnoses:
                selected = diagnostic["modes"][mode]["selected_action"]
                if selected is None:
                    continue
                best = diagnostic["actions"][diagnostic["true_optimal_representative"]]
                chosen = diagnostic["actions"][selected]
                row = {field + "_difference": best[field] - chosen[field] if best[field] is not None and chosen[field] is not None else None
                    for field in ("q_hat", "q_star", "A_transition_error", "D_continuation_error")}
                a, d = row["A_transition_error_difference"], row["D_continuation_error_difference"]
                row["opposite_sign_A_D"] = a * d < 0 and abs(a) > TOL and abs(d) > TOL if a is not None and d is not None else None
                row["cancelled_absolute_error"] = max(0., abs(a) + abs(d) - abs(math.fsum((a, d)))) if a is not None and d is not None else None
                rows.append(row)
            choice_pairs[mode] = margin_points(rows)
        for choice in (*MODES, "true_optimal_representative"):
            counts = [d["choice_batch_counts"][choice]["batch_count"] for d in diagnoses if d["choice_batch_counts"][choice]["batch_count"] is not None]
            batches[choice] = {"count": len(counts), "mean_batch_count": mean(counts), "batch_count_histogram": dict(sorted(Counter(counts).items()))}
        result[arm] = {"alphabetical_action_pairs": {name: margin_points(rows) for name, rows in sorted(pairs.items())},
            "true_optimal_representative_minus_selected": choice_pairs, "selected_row_cumulative_batches": batches}
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
        sum(c["requested_batch_count"] for c in plan["contexts"]) == 494]
    checks["frozen_streams_modes_comparisons"] = [len(repetitions) == plan["replicate_count"] == 64,
        [{"replicate_index": r["replicate_index"], "base_seed": r["base_seed"]} for r in repetitions] == plan["replicates"],
        plan["arms"] == list(ARMS), plan["modes"] == list(MODES), plan["primary_comparisons"] == [list(pair) for pair in PAIRS]]
    checks["source_plan_binding"] = [payload["plan_binding_validation"]["passed"]]
    checked, unavailable = [], []
    for rep in repetitions:
        same_ids = [{key: c["identity"].get(key) for key in IDENTITY_FIELDS} for c in rep["contexts"]] == identities
        checks["retained_identities"].append(same_ids)
        raw_flags, cf_flags = [], []
        for context in rep["contexts"]:
            fixed = planned[context["identity"]["context_index"]]
            fixed_equal = all(context[key] == fixed[key] for key in ("target_key", "requested_batch_count", "initial_batches", "request_index"))
            checks["fixed_target_and_budget"].append(fixed_equal)
            valid = (context["source_paired_complete"] and context["source_validation"]["passed"]
                     and fixed_equal and set(context["arms"]) == set(ARMS))
            available = True
            for arm in ARMS:
                row = context["arms"].get(arm, {})
                diagnostic = row.get("diagnostic", {})
                raw_valid = (row.get("source_validation", {}).get("passed", False)
                    and row.get("diagnostic_validation", {}).get("passed", False)
                    and row.get("raw_reproduction_validation", {}).get("passed", False)
                    and diagnostic.get("validation", {}).get("all_passed", False)
                    and diagnostic.get("modes", {}).get("RAW", {}).get("available", False))
                cf_available = bool(diagnostic) and all(diagnostic["modes"][mode]["available"] for mode in MODES[1:])
                checks["arm_validity_labels"].append(row.get("raw_valid", False) == raw_valid and row.get("counterfactual_available", False) == cf_available)
                if diagnostic:
                    checks["joint_legal_action_eligibility"].append(
                        cf_available == all(action["decomposable"] for action in diagnostic["actions"].values())
                        and diagnostic["modes"]["REMOVE_A"]["available"] == diagnostic["modes"]["REMOVE_D"]["available"])
                    checks["numeric_identity_validation"].append(diagnostic["validation"]["maximum_absolute_checked_residual"] <= TOL)
                valid &= raw_valid
                available &= cf_available
            cf_valid = valid and available
            checks["context_mask_labels"].append(context["raw_valid"] == valid and context["paired_complete"] == cf_valid)
            raw_flags.append(valid)
            cf_flags.append(cf_valid)
            if not cf_valid:
                unavailable.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
                    "identity": context["identity"], "status": context["status"], "raw_valid": valid,
                    "source_validation": context["source_validation"], "arms": {arm: {
                        key: value for key, value in row.items() if key not in ("source_target", "diagnostic")}
                        | {"unavailable_actions": row.get("diagnostic", {}).get("unavailable_actions", [])}
                        for arm, row in context["arms"].items()}})
        raw_complete = same_ids and rep["source_complete"] and rep["source_validation"]["passed"] and all(raw_flags)
        complete = raw_complete and all(cf_flags)
        checks["whole_stream_masks"].append(rep["raw_complete"] == raw_complete and rep["complete"] == complete)
        checked.append({**rep, "raw_complete": raw_complete, "complete": complete})
    raw_reps = [rep for rep in checked if rep["raw_complete"]]
    cf_reps = [rep for rep in checked if rep["complete"]]
    raw_contexts = [c for rep in raw_reps for c in rep["contexts"]]
    cf_contexts = [c for rep in cf_reps for c in rep["contexts"]]
    primary, streams = primary_statistics(raw_reps, cf_reps)
    reproduction = raw_reproduction(raw_reps, reference)
    checks["RAW_V24_metric_reproduction"] = [reproduction["all_passed"]]
    checks["stream_count_labels"] = [len(raw_reps) == payload["raw_complete_repetition_count"], len(cf_reps) == payload["complete_repetition_count"]]
    account = payload["accounting"]
    checks["all_historical_costs_retained"] = [payload["source_actual_arm_costs"] == reference["all_actual_arm_costs"],
        payload["source_accounting"] == reference["accounting"],
        account["historical_physical_batches"] == plan["historical_physical_batches"] == 94848,
        account["historical_physical_draws"] == plan["historical_physical_draws"] == 24281088]
    checks["no_new_sampling_or_truth"] = [payload[key] == account[key] == 0 for key in ("new_provider_calls", "new_oracle_calls", "new_physical_draws")]
    checks["single_numeric_source_read"] = [account["source_result_reads"] == 1, account["model_restore_calls"] == account["source_endpoint_reads"] == 0]
    def selection(predicate):
        return {"RAW_all_evaluable": point_estimates([c for c in raw_contexts if predicate(c["identity"])], ("RAW",)),
            "common_counterfactual_mask": point_estimates([c for c in cf_contexts if predicate(c["identity"])])}
    results = {name: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for name, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_signed_errors_analysis.v25", "status": payload["status"],
        "raw_complete_stream_count": len(raw_reps), "counterfactual_complete_stream_count": len(cf_reps),
        "primary": primary, "repetitions": streams,
        "groups": {group: selection(lambda identity: identity["group"] == group) for group in ("improvement", "regression", "old_witness_only")},
        "old_witness_groups": {group: selection(lambda identity: identity.get("source_old_group") == group) for group in sorted({c.get("source_old_group") for c in identities if c.get("source_old_group")})},
        "contexts": [{"identity": identity, "point_estimates": selection(lambda row: row["context_index"] == identity["context_index"])} for identity in identities],
        "RAW_discordant_group_counterfactual_counts": discordant_groups(cf_contexts),
        "signed_auxiliary_common_counterfactual_mask": signed_points(cf_contexts),
        "stream_statuses": [{key: rep[key] for key in ("replicate_index", "base_seed", "raw_complete", "complete", "status")} for rep in checked],
        "unavailable_context_instances": unavailable, "RAW_V24_metric_reproduction": reproduction,
        "source_actual_arm_costs": payload["source_actual_arm_costs"], "source_accounting": payload["source_accounting"],
        "source_analysis_accounting": payload["source_analysis_accounting"], "accounting": account,
        "checks": results, "all_analysis_checks_passed": all(row["passed"] for row in results.values()),
        "elapsed_seconds_before_report_serialization": payload["elapsed_seconds_before_report_serialization"],
        "analysis_seconds": perf_counter() - started, "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Signed numerical attribution on fixed V24 target endpoints. Each reused suffix stream is one Monte Carlo unit after equal averaging over all22 contexts. Both counterfactuals and their RAW comparators share a joint all-action, all-arm, whole-stream mask. Descriptive intervals are not a new Gate. Group, discordant-instance and signed-pair counts are dependent point summaries. Corrections use retained truth and are not deployable policies; target regret is not full-policy regret. Historical acquisition costs stay paid, with no new samples or oracle calls."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_signed_errors_v25.json"))
    parser.add_argument("--reference", type=Path, default=Path("reports/controlled_predictive_frontier_analysis_v24.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_signed_errors_analysis_v25.json"))
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
    print(json.dumps({"output": str(args.output), "raw_complete_stream_count": result["raw_complete_stream_count"],
        "counterfactual_complete_stream_count": result["counterfactual_complete_stream_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"], "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
