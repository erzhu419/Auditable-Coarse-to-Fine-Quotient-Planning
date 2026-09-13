#!/usr/bin/env python3
"""Compare retained frozen policies under true transition probabilities."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import IDENTITY_FIELDS, TOL, differences, mean, monte_carlo_interval
from analyze_controlled_predictive_factorial_v26 import (
    ARMS, PRIMARY_PAIRS, AUXILIARY_PAIRS, PRIMARY_CONTRASTS, AUXILIARY_CONTRASTS, contrasts)

POLICY_METRICS = ("total_regret", "continuation_regret", "optimal_policy_rate")
COMPONENT_METRICS = (*POLICY_METRICS, "first_action_regret")
FIRST_METRICS = ("target_wrong_action_rate", "target_mean_local_regret")
AVAILABILITY_METRICS = ("policy_unavailable_rate", "missing_probability", "weighted_unobserved_choices")


def policy_metrics(row):
    value = row["evaluation"]
    return {**{key: value[key] for key in ("total_regret", "first_action_regret", "continuation_regret")},
        "optimal_policy_rate": float(value["total_regret"] <= TOL)}


def first_metrics(row):
    value = row["evaluation"]
    return {"target_wrong_action_rate": float(value["first_action_wrong"]), "target_mean_local_regret": value["first_action_regret"]}


def availability_metrics(row):
    value = row["evaluation"]
    return {"policy_unavailable_rate": float(not value["policy_evaluable"]),
        "missing_probability": value["missing_probability"], "weighted_unobserved_choices": value["weighted_unobserved_choices"]}


def paired_summary(values, metric, *, interval):
    result = monte_carlo_interval(values) if interval else differences(values)
    higher_better = metric == "optimal_policy_rate"
    result.update(improved=result["positive" if higher_better else "negative"], same=result["zero"],
        worse=result["negative" if higher_better else "positive"])
    return result


def level_interval(values):
    return {key: value for key, value in monte_carlo_interval(values).items() if key not in ("negative", "zero", "positive")}


def stream_statistics(repetitions, value_function, keys):
    streams = []
    for repetition in repetitions:
        values = {arm: {key: mean([value_function(c["arms"][arm])[key] for c in repetition["contexts"]]) for key in keys} for arm in ARMS}
        streams.append({"replicate_index": repetition["replicate_index"], "base_seed": repetition["base_seed"],
            "arms": values, "comparisons": {name: {key: contrasts(values, key)[name] for key in keys}
                for name in PRIMARY_CONTRASTS + AUXILIARY_CONTRASTS}})
    return {"complete_stream_count": len(streams), "unit": "one reused suffix stream, equal weights over all22 contexts",
        "arms": {arm: {key: level_interval([row["arms"][arm][key] for row in streams]) for key in keys} for arm in ARMS},
        "primary_comparisons": {key: {name: paired_summary([row["comparisons"][name][key] for row in streams], key, interval=True)
            for name in PRIMARY_CONTRASTS} for key in keys},
        "auxiliary_comparisons": {key: {name: paired_summary([row["comparisons"][name][key] for row in streams], key, interval=True)
            for name in AUXILIARY_CONTRASTS} for key in keys}}, streams


def points(contexts, value_function, keys):
    values = [{arm: value_function(c["arms"][arm]) for arm in ARMS} for c in contexts]
    return {"four_arm_context_instances": len(contexts),
        **{arm: {key: mean([row[arm][key] for row in values]) for key in keys} for arm in ARMS},
        "comparisons": {name: {key: paired_summary([contrasts(row, key)[name] for row in values], key, interval=False) for key in keys}
            for name in PRIMARY_CONTRASTS + AUXILIARY_CONTRASTS}}


def first_action_reproduction(repetitions, reference):
    expected_reps = {row["replicate_index"]: row for row in reference["repetitions"]}
    _, actual_streams = stream_statistics(repetitions, first_metrics, FIRST_METRICS)
    rep_checks, context_checks = [], []
    for row in actual_streams:
        expected = expected_reps[row["replicate_index"]]
        rep_checks.append({"replicate_index": row["replicate_index"],
            "passed": row["base_seed"] == expected["base_seed"] and row["arms"] == expected["arms"]})
    # The compact V26 source has per-context means over all64 streams only.
    if len(repetitions) == 64:
        rows = [c for rep in repetitions for c in rep["contexts"]]
        for expected in reference["contexts"]:
            index = expected["identity"]["context_index"]
            chosen = [c for c in rows if c["identity"]["context_index"] == index]
            equal = {"all64_instances": len(chosen) == 64}
            for arm in ARMS:
                for metric in FIRST_METRICS:
                    equal[f"{arm}.{metric}"] = mean([first_metrics(c["arms"][arm])[metric] for c in chosen]) == expected["point_estimates"][arm][metric]
            context_checks.append({"context_index": index, "field_equal": equal, "passed": all(equal.values())})
    return {"source_valid_stream_count": len(repetitions), "replicate_comparisons": rep_checks,
        "context_comparisons": context_checks, "per_context_full64_comparison_available": len(repetitions) == 64,
        "numeric_comparison": "EXACT", "all_passed": bool(rep_checks) and all(row["passed"] for row in rep_checks + context_checks)}


def summarize(payload, reference):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    planned = {row["context_index"]: row for row in plan["contexts"]}
    identities = [{key: row.get(key) for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    checks = defaultdict(list)
    checks["frozen_cohort_and_streams"] = [len(planned) == plan["context_count"] == 22,
        Counter(c["group"] for c in plan["contexts"]) == {"improvement": 7, "regression": 13, "old_witness_only": 2},
        sum(c["source_old_witness"] for c in plan["contexts"]) == 10,
        sum(c["source_v20_changed"] for c in plan["contexts"]) == 20,
        sum(c["requested_batch_count"] for c in plan["contexts"]) == 494,
        len(repetitions) == plan["replicate_count"] == 64,
        [{"replicate_index": r["replicate_index"], "base_seed": r["base_seed"]} for r in repetitions] == plan["replicates"]]
    checks["frozen_metrics_and_contrasts"] = [plan["arms"] == list(ARMS), plan["primary_metrics"] == list(POLICY_METRICS),
        plan["primary_comparisons"] == [list(pair) for pair in PRIMARY_PAIRS],
        plan["secondary_comparisons"] == [list(pair) for pair in AUXILIARY_PAIRS],
        plan["interaction_contrast"] == {"FRONTIER_VARIANCE": 1, "FRONTIER": -1, "VARIANCE": -1, "CACHED": 1}]
    checks["source_plan_binding"] = [payload["plan_binding_validation"]["passed"]]
    checks["source_stream_record_count"] = [payload["source_stream_validation"]["passed"]]
    checked, incomplete = [], []
    for rep in repetitions:
        same_ids = [{key: c["identity"].get(key) for key in IDENTITY_FIELDS} for c in rep["contexts"]] == identities
        checks["retained_identities"].append(same_ids)
        source_flags, policy_flags = [], []
        for context in rep["contexts"]:
            fixed = planned[context["identity"]["context_index"]]
            fixed_equal = all(context[key] == fixed[key] for key in ("target_key", "panel", "requested_batch_count", "initial_batches"))
            checks["fixed_target_and_budget"].append(fixed_equal)
            source_valid = (context["source_paired_complete"] and context["source_validation"]["passed"]
                and fixed_equal and set(context["arms"]) == set(ARMS))
            policies_valid = True
            for arm in ARMS:
                row = context["arms"].get(arm, {})
                evaluation = row.get("evaluation")
                current_source = (row.get("source_validation", {}).get("passed", False)
                    and row.get("first_action_validation", {}).get("passed", False) and evaluation is not None)
                checks["arm_source_validity_labels"].append(row.get("source_valid", False) == current_source)
                evaluable = bool(evaluation and evaluation["policy_evaluable"])
                identity_valid = bool(evaluation and evaluation["identities_pass"])
                reach_valid = bool(evaluation and evaluation["reach_probability_pass"]
                    and abs(evaluation["terminal_probability"] + evaluation["missing_probability"] - 1.) <= TOL)
                if evaluation:
                    checks["true_reach_probability_conservation"].append(reach_valid)
                    checks["missing_policy_availability"].append(evaluable == (evaluation["missing_probability"] == 0.))
                    if evaluable:
                        checks["true_reach_decomposition"].append(identity_valid and abs(evaluation["identity_residual"]) <= TOL
                            and abs(evaluation["total_regret"] - evaluation["first_action_regret"] - evaluation["continuation_regret"]) <= TOL)
                    else:
                        checks["undefined_policy_values_not_imputed"].append(all(evaluation[key] is None for key in ("v_pi", "total_regret", "continuation_regret")))
                source_valid &= current_source
                policies_valid &= evaluable and identity_valid and reach_valid
            complete = source_valid and policies_valid
            checks["context_mask_labels"].append(context["source_valid"] == source_valid and context["paired_complete"] == complete)
            source_flags.append(source_valid)
            policy_flags.append(complete)
            if not complete:
                incomplete.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
                    "identity": context["identity"], "status": context["status"], "source_valid": source_valid,
                    "source_validation": context["source_validation"], "arms": {arm: {
                        "source_validation": row["source_validation"], "first_action_validation": row.get("first_action_validation"),
                        "evaluation_validation": row.get("evaluation_validation"),
                        "reach_probability_pass": row.get("evaluation", {}).get("reach_probability_pass"),
                        "missing_probability": row.get("evaluation", {}).get("missing_probability"),
                        "missing_policy_frontier": row.get("evaluation", {}).get("missing_policy_frontier", [])}
                        for arm, row in context["arms"].items()}})
        source_valid = same_ids and payload["source_stream_validation"]["passed"] and rep["source_complete"] and all(source_flags)
        complete = source_valid and all(policy_flags)
        checks["whole_stream_masks"].append(rep["source_valid"] == source_valid and rep["complete"] == complete)
        checked.append({**rep, "source_valid": source_valid, "complete": complete})
    source_reps = [rep for rep in checked if rep["source_valid"]]
    policy_reps = [rep for rep in checked if rep["complete"]]
    source_contexts = [c for rep in source_reps for c in rep["contexts"]]
    policy_contexts = [c for rep in policy_reps for c in rep["contexts"]]
    primary, streams = stream_statistics(policy_reps, policy_metrics, POLICY_METRICS)
    first_primary, first_streams = stream_statistics(policy_reps, first_metrics, FIRST_METRICS)
    reproduction = first_action_reproduction(source_reps, reference)
    checks["V26_first_action_metric_reproduction"] = [reproduction["all_passed"]]
    checks["stream_count_labels"] = [len(source_reps) == payload["source_valid_repetition_count"], len(policy_reps) == payload["complete_repetition_count"]]
    account = payload["accounting"]
    checks["all_historical_costs_retained"] = [payload["source_actual_arm_costs"] == reference["all_actual_arm_costs"],
        payload["source_accounting"] == reference["accounting"],
        account["historical_physical_batches"] == plan["historical_physical_batches"] == 126464,
        account["historical_physical_draws"] == plan["historical_physical_draws"] == 32374784]
    checks["no_new_acquisition_or_replanning"] = [account[key] == 0 for key in (
        "new_sampling_calls", "new_replanning_calls", "new_physical_batches", "new_physical_draws")]
    checks["source_endpoint_read_once"] = [account["source_endpoint_reads"] == 1]
    def selection(predicate):
        return {"policy_main_mask": points([c for c in policy_contexts if predicate(c["identity"])], policy_metrics, COMPONENT_METRICS),
            "availability_source_mask": points([c for c in source_contexts if predicate(c["identity"])], availability_metrics, AVAILABILITY_METRICS)}
    results = {name: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for name, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_frozen_policy_analysis.v27", "status": payload["status"],
        "source_valid_stream_count": len(source_reps), "complete_stream_count": len(policy_reps),
        "primary": primary, "same_main_mask_first_action": first_primary,
        "complete_stream_point_estimates": points(policy_contexts, policy_metrics, COMPONENT_METRICS),
        "availability_source_valid_streams": points(source_contexts, availability_metrics, AVAILABILITY_METRICS),
        "groups": {group: selection(lambda identity: identity["group"] == group) for group in ("improvement", "regression", "old_witness_only")},
        "old_witness_groups": {group: selection(lambda identity: identity.get("source_old_group") == group)
            for group in sorted({c.get("source_old_group") for c in identities if c.get("source_old_group")})},
        "contexts": [{"identity": identity, **selection(lambda row: row["context_index"] == identity["context_index"])} for identity in identities],
        "repetitions": streams, "same_main_mask_first_action_repetitions": first_streams,
        "stream_statuses": [{key: rep[key] for key in ("replicate_index", "base_seed", "source_valid", "complete", "status")} for rep in checked],
        "incomplete_context_instances": incomplete, "V26_first_action_metric_reproduction": reproduction,
        "source_actual_arm_costs": payload["source_actual_arm_costs"], "source_accounting": payload["source_accounting"],
        "source_analysis_accounting": payload["source_analysis_accounting"], "source_stream_validation": payload["source_stream_validation"],
        "accounting": account, "checks": results, "all_analysis_checks_passed": all(row["passed"] for row in results.values()),
        "elapsed_seconds_before_report_serialization": payload["elapsed_seconds_before_report_serialization"],
        "analysis_seconds": perf_counter() - started, "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Fixed endpoint policies from the original H2 targets under true transitions. The source-valid mask preserves first-action reproduction and missing-policy diagnostics; all22 by four evaluable policies are required for the common primary stream mask. Each reused suffix stream is one Monte Carlo unit. Total regret uses true reach probabilities, not unweighted panel sums. weighted_unobserved_choices is an expected number of unobserved action selections, not a probability of at least one. Higher optimal-policy rate and lower regret are improvements. Historical acquisition costs remain paid. This is not the H3 online algorithm with subsequent resampling, independent validation, or a new formal Gate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_frozen_policy_v27.json"))
    parser.add_argument("--reference", type=Path, default=Path("reports/controlled_predictive_factorial_analysis_v26.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_frozen_policy_analysis_v27.json"))
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
    print(json.dumps({"output": str(args.output), "source_valid_stream_count": result["source_valid_stream_count"],
        "complete_stream_count": result["complete_stream_count"], "all_analysis_checks_passed": result["all_analysis_checks_passed"],
        "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
