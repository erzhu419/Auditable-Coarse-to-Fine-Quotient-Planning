#!/usr/bin/env python3
"""Describe every retained trajectory of the V29 induced regression."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

TOL = 1e-10
MARGIN_COMPONENTS = ("q_hat_difference", "q_star_difference", "A_transition_error_difference", "D_continuation_error_difference")
VALIDATIONS = ("source_validation", "prefix_validation", "chronology_validation", "endpoint_validation")


def close(left, right):
    return left is not None and right is not None and abs(left - right) <= TOL


def correctness(boundary, *, policy=False):
    value = boundary["policy_evaluation" if policy else "local_evaluation"]
    regret = value["total_regret" if policy else "local_regret"]
    if regret is None or (policy and not value["policy_evaluable"]):
        return None
    return regret <= TOL


def transitions(boundaries, *, policy=False):
    """Adjacent unknown values never count as correct or bridge a transition."""
    result = []
    for before, after in zip(boundaries, boundaries[1:]):
        a, b = correctness(before, policy=policy), correctness(after, policy=policy)
        if a is None or b is None or a == b:
            continue
        result.append({"from_boundary_index": before["boundary_index"], "to_boundary_index": after["boundary_index"],
            "kind": "CORRECT_TO_WRONG" if a else "WRONG_TO_CORRECT"})
    return result


def transition_keys(rows):
    return [{key: row[key] for key in ("from_boundary_index", "to_boundary_index", "kind")} for row in rows]


def margin_valid(row):
    if not row["observed_both"]:
        return all(row[key] is None for key in ("q_hat_difference", "A_transition_error_difference", "D_continuation_error_difference", "identity_residual"))
    return (close(row["q_hat_difference"] - row["q_star_difference"],
        row["A_transition_error_difference"] + row["D_continuation_error_difference"])
        and close(row["identity_residual"], 0.))


def signed_change(before, after):
    result = {key: after[key] - before[key] if before[key] is not None and after[key] is not None else None for key in MARGIN_COMPONENTS}
    values = list(result.values())
    result["identity_residual"] = (result["q_hat_difference"] - result["q_star_difference"]
        - result["A_transition_error_difference"] - result["D_continuation_error_difference"]) if all(value is not None for value in values) else None
    return result


def numeric_description(values):
    values = [value for value in values if value is not None]
    return {"count": len(values), "minimum": min(values) if values else None,
        "maximum": max(values) if values else None, "mean": math.fsum(values) / len(values) if values else None}


def first_harmful_index(rows):
    return next((row["to_boundary_index"] for row in rows if row["kind"] == "CORRECT_TO_WRONG"), None)


def summarize_trajectory(row):
    boundaries = row["boundaries"]
    root_transitions, policy_transitions = transitions(boundaries), transitions(boundaries, policy=True)
    trigger = row.get("first_harmful_update")
    compact_trigger = None
    if trigger is not None:
        compact_trigger = {key: value for key, value in trigger.items() if key not in ("before_local", "after_local", "before_state", "after_state")}
        compact_trigger["signed_margin_change"] = signed_change(trigger["before_margin"], trigger["after_margin"])
        before_actions, after_actions = trigger["before_local"]["actions"], trigger["after_local"]["actions"]
        compact_trigger["root_batch_counts_unchanged"] = all(before_actions[action]["batch_count"] == after_actions[action]["batch_count"] for action in before_actions)
        compact_trigger["root_transition_error_terms_unchanged"] = all(
            (before_actions[action]["A_transition_error"] == after_actions[action]["A_transition_error"])
            for action in before_actions)
    return {"replicate_index": row["replicate_index"], "base_seed": row["base_seed"], "arm": row["arm"],
        "identity": row["identity"], "status": row["status"],
        **{key: {name: value for name, value in row[key].items() if name != "requests"} for key in VALIDATIONS}, "boundary_count": len(boundaries),
        "first_root_harmful_batch": first_harmful_index(root_transitions),
        "first_policy_harmful_batch": first_harmful_index(policy_transitions),
        "first_positive_policy_regret_boundary": next((b["boundary_index"] for b in boundaries if correctness(b, policy=True) is False), None),
        "root_transitions": root_transitions, "policy_transitions": policy_transitions,
        "root_wrong_boundary_count": sum(correctness(b) is False for b in boundaries),
        "policy_wrong_boundary_count": sum(correctness(b, policy=True) is False for b in boundaries),
        "policy_unknown_boundary_count": sum(correctness(b, policy=True) is None for b in boundaries),
        "root_repair_count": sum(t["kind"] == "WRONG_TO_CORRECT" for t in root_transitions),
        "root_reentry_count": max(0, sum(t["kind"] == "CORRECT_TO_WRONG" for t in root_transitions) - 1),
        "first_harmful_update": compact_trigger,
        "prefix_policy": boundaries[0]["policy_evaluation"] if boundaries else None,
        "endpoint_policy": boundaries[-1]["policy_evaluation"] if boundaries else None,
        "original_costs": row["original_costs"], "original_local_accounting": row["original_local_accounting"],
        "accounting": row["accounting"]}


def validate_trajectory(row, plan, checks):
    boundaries, trigger = row["boundaries"], row.get("first_harmful_update")
    checks["trajectory_completion"].append(row["status"] == "REPLAY_COMPLETE")
    for key in VALIDATIONS:
        checks[key].append(row[key]["passed"])
    checks["all_boundaries_retained_in_order"].append([b["boundary_index"] for b in boundaries] == list(range(plan["expected_boundaries_per_trajectory"])))
    checks["root_transition_reproduction"].append(transition_keys(row["transitions"]) == transitions(boundaries))
    if "policy_transitions" in row:
        checks["policy_transition_reproduction"].append(transition_keys(row["policy_transitions"]) == transitions(boundaries, policy=True))
    first = first_harmful_index(transitions(boundaries))
    checks["first_root_harmful_batch_is_adjacent_update"].append((trigger is None and first is None) or (trigger is not None and trigger["after_boundary_index"] == first))
    for boundary in boundaries:
        local, policy = boundary["local_evaluation"], boundary["policy_evaluation"]
        checks["root_choice_matches_frozen_policy"].append(local["selected_action"] == policy["initial_action"])
        checks["local_decomposition_identities"].append(local["identities_pass"])
        for action in local["actions"].values():
            if action["observed"]:
                checks["local_decomposition_identities"].append(close(action["q_hat"] - action["q_star"], action["A_transition_error"] + action["D_continuation_error"]))
            else:
                checks["unobserved_action_terms_remain_null"].append(all(action[key] is None for key in ("q_hat", "A_transition_error", "D_continuation_error")))
        checks["policy_probability_conservation"].append(policy["reach_probability_pass"] and close(policy["terminal_probability"] + policy["missing_probability"], 1.))
        if policy["policy_evaluable"]:
            checks["policy_regret_identity"].append(policy["identities_pass"] and close(policy["total_regret"], policy["first_action_regret"] + policy["continuation_regret"]) and close(policy["first_action_regret"], local["local_regret"]))
        else:
            checks["unknown_policy_not_imputed"].append(all(policy[key] is None for key in ("v_pi", "total_regret", "continuation_regret")))
        checks["selected_reference_margin_identity"].append(margin_valid(boundary["selected_vs_reference"]))
    if trigger is not None:
        checks["trigger_same_actions_and_decomposition"].extend([margin_valid(trigger["before_margin"]), margin_valid(trigger["after_margin"])])
        for local_name, margin_name in (("before_local", "before_margin"), ("after_local", "after_margin")):
            action = trigger[local_name]["actions"][trigger["new_action"]]
            reference = trigger[local_name]["actions"][trigger["reference_action"]]
            margin = trigger[margin_name]
            checks["trigger_same_actions_and_decomposition"].append(margin["observed_both"] == (action["observed"] and reference["observed"]))
            for key in ("q_star", "q_hat", "A_transition_error", "D_continuation_error"):
                expected = action[key] - reference[key] if action[key] is not None and reference[key] is not None else None
                actual = margin[key + "_difference"]
                checks["trigger_same_actions_and_decomposition"].append(actual is None if expected is None else close(actual, expected))
        delta = signed_change(trigger["before_margin"], trigger["after_margin"])
        checks["trigger_same_actions_and_decomposition"].append(delta["identity_residual"] is None or close(delta["identity_residual"], 0.))


def summarize(payload):
    started = perf_counter()
    plan, trajectories = payload["plan"], payload["trajectories"]
    checks = defaultdict(list)
    expected = [(rep["replicate_index"], rep["base_seed"], arm) for rep in plan["replicates"] for arm in plan["arms"]]
    checks["plan_binding_and_oracle_separation"] = [payload["plan_binding_validation"]["passed"], payload["all_histories_bound_before_oracle"], not payload["oracle_used_for_replay_selection"]]
    checks["frozen_selected_trajectory_roster"] = [len(trajectories) == plan["expected_trajectories"],
        [(row["replicate_index"], row["base_seed"], row["arm"]) for row in trajectories] == expected,
        all(row["identity"][key] == plan["context"][key] for row in trajectories for key in ("context_index", "board_index", "case_name", "query_name"))]
    summaries = []
    for row in trajectories:
        validate_trajectory(row, plan, checks)
        summaries.append(summarize_trajectory(row))
    account, source = payload["accounting"], payload["original_source_accounting"]
    checks["historical_physical_costs_retained"] = [source["total_physical_batches"] == plan["source_historical_physical_batches"],
        source["total_physical_draws"] == plan["source_historical_physical_draws"],
        account["historical_physical_batches"] == source["total_physical_batches"], account["historical_physical_draws"] == source["total_physical_draws"]]
    checks["no_new_acquisition"] = [account[key] == 0 for key in ("new_provider_calls", "new_sampling_calls", "new_physical_draws")]
    checks["selected_retained_samples_replayed"] = [account.get("retained_batches_replayed", 0) == plan["selected_suffix_historical_batches"],
        account.get("retained_draws_replayed", 0) == plan["selected_suffix_historical_draws"]]
    costs, by_arm = {}, {}
    for arm in plan["arms"]:
        rows = [row for row in summaries if row["arm"] == arm]
        complete = [row for row in rows if row["status"] == "REPLAY_COMPLETE" and all(row[key]["passed"] for key in VALIDATIONS)]
        cost_keys = sorted({key for row in rows for key in row["original_costs"]})
        costs[arm] = {"trajectory_count_including_failures": len(rows), "attributed_cost_totals": {
            key: math.fsum(row["original_costs"][key] for row in rows) for key in cost_keys}}
        triggers = [row["first_harmful_update"] for row in complete if row["first_harmful_update"] is not None]
        by_arm[arm] = {"retained_trajectory_count": len(rows), "complete_trajectory_count": len(complete),
            "first_root_harmful_batch_counts": dict(sorted(Counter(str(row["first_root_harmful_batch"]) for row in complete).items())),
            "first_policy_harmful_batch_counts": dict(sorted(Counter(str(row["first_policy_harmful_batch"]) for row in complete).items())),
            "root_repair_total": sum(row["root_repair_count"] for row in complete),
            "root_reentry_total": sum(row["root_reentry_count"] for row in complete),
            "trigger_action_changes": dict(Counter(t["previous_action"] + " -> " + t["new_action"] for t in triggers)),
            "trigger_request_kinds": dict(Counter(t["request"]["kind"] for t in triggers)),
            "trigger_row_locations": dict(Counter(t["update_location"] for t in triggers)),
            "root_batch_counts_unchanged_count": sum(t["root_batch_counts_unchanged"] for t in triggers),
            "root_transition_error_terms_unchanged_count": sum(t["root_transition_error_terms_unchanged"] for t in triggers),
            "before_signed_margins": {key: numeric_description([t["before_margin"][key] for t in triggers]) for key in MARGIN_COMPONENTS},
            "after_signed_margins": {key: numeric_description([t["after_margin"][key] for t in triggers]) for key in MARGIN_COMPONENTS},
            "signed_margin_changes": {key: numeric_description([t["signed_margin_change"][key] for t in triggers]) for key in MARGIN_COMPONENTS}}
    representative = min(trajectories, key=lambda row: (row["replicate_index"], plan["arms"].index(row["arm"]))) if trajectories else None
    check_rows = {key: {"passed": all(values), "check_count": len(values), "failed_count": sum(not value for value in values)} for key, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_regression_analysis.v30", "plan": plan,
        "trajectory_count": len(summaries), "complete_trajectory_count": sum(row["status"] == "REPLAY_COMPLETE" and all(row[key]["passed"] for key in VALIDATIONS) for row in summaries),
        "boundary_count": sum(row["boundary_count"] for row in summaries), "trajectory_statuses": summaries, "by_arm": by_arm,
        "validation_pass_counts": {key: sum(row[key]["passed"] for row in trajectories) for key in VALIDATIONS},
        "representative": None if representative is None else {"replicate_index": representative["replicate_index"],
            "arm": representative["arm"], "status": representative["status"], "first_harmful_update": None if representative.get("first_harmful_update") is None else {key: value for key, value in representative["first_harmful_update"].items() if key not in ("before_state", "after_state")}},
        "selected_original_costs_including_failures": costs, "original_source_accounting": source, "accounting": account,
        "checks": check_rows, "all_analysis_checks_passed": all(row["passed"] for row in check_rows.values()),
        "analysis_seconds": perf_counter() - started,
        "scope": "Descriptive replay of all 32 histories for one selected induced-error context with a shared fixed prefix. Root-choice harm and full-policy harm are separate. No confidence intervals, new sample acquisition, or population efficacy inference."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_regression_v30.json.gz"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_regression_analysis_v30.json"))
    args = parser.parse_args()
    started = perf_counter()
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    read_seconds = perf_counter() - started
    result = summarize(payload)
    result["analysis_result_read_seconds"] = read_seconds
    started = perf_counter()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "complete_trajectory_count": result["complete_trajectory_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"], "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
