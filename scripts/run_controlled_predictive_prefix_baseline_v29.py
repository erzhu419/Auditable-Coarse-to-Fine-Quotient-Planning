#!/usr/bin/env python3
"""Evaluate retained V28 prefix policies once and reuse their endpoint results."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_quotient_v1 import Query

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_PREFIX_BASELINE_V29.md")
DEFAULT_PLAN = Path("reports/controlled_predictive_prefix_baseline_plan_v29.json")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_prefix_baseline_v29.json.gz")
ARMS = ("CACHED", "VARIANCE")
IDENTITY_FIELDS = ("context_index", "board_index", "case_name", "query_name")


def _identity(context):
    return {key: context[key] for key in IDENTITY_FIELDS}


def _key(value):
    return value[0], tuple(value[1])


def _prefix_validation(item, prefix, preparation, retained_prefix, context, board, plan):
    state = item.get("state", {})
    rows, records = state.get("rows", []), prefix.get("batches", [])
    policy = next((row for row in state.get("policy_and_intervals", []) if row["key"] == context["target_key"]), None)
    profile = next((row for row in state.get("profiles", []) if row["key"] == context["target_key"]), None)
    counts = {}
    for record in records:
        pair = _key(record["row_key"][0]), record["row_key"][1]
        counts.setdefault(pair, Counter()).update({(_key(successor), reward): round(probability*256)
            for probability, successor, reward in record["outcomes"]})
    observed_counts = {(_key(row["row_key"][0]), row["row_key"][1]): Counter({(_key(entry["successor"]), entry["reward"]): entry["count"]
        for entry in row["integer_counts"]}) for row in rows}
    actions = board["legal_actions"]
    checks = {"identity": item.get("identity") == _identity(context),
        "preparation_record": {key: value for key, value in item.items() if key != "state"} == preparation,
        "prefix_record": {key: value for key, value in prefix.items() if key != "batches"} == retained_prefix,
        "retained_validations": item.get("validation", {}).get("passed", False) and prefix.get("validation", {}).get("passed", False),
        "root": state.get("root") == context["target_key"] == [board["horizon"], board["board"]],
        "query": state.get("query") == plan["queries"][context["query_name"]],
        "initial_batches": state.get("spent_batches") == context["initial_batches"] == len(records) == plan["prefix_batches_per_board"],
        "model_batches": sum(row["batch_count"] for row in rows) == context["initial_batches"],
        "root_round_robin_batches": all(record["row_key"] == [context["target_key"], actions[j % len(actions)]]
            and record["batch_index"] == j // len(actions) for j, record in enumerate(records)),
        "observed_integer_counts": observed_counts == counts,
        "row_order": state.get("row_order") == [row["row_key"] for row in rows] == [[context["target_key"], action] for action in actions],
        "root_policy": policy is not None and profile is not None and policy["action"] in profile["legal_actions"]
            and policy["lower"] <= policy["upper"]}
    return {"passed": all(checks.values()), "checks": checks}, policy


def run_prefix_baseline(plan_path, output_path, progress=None):
    started = perf_counter()
    if output_path.exists():
        raise FileExistsError(f"V29 output already exists: {output_path}")
    accounting = Counter()
    tick = perf_counter()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    accounting["frozen_plan_read_seconds"] = perf_counter() - tick
    sources = {}
    for field in ("source_plan", "source_analysis", "source_prefixes", "source_endpoints_result"):
        tick = perf_counter()
        path = Path(plan[field])
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as reader:
                sources[field] = json.load(reader)
        else:
            sources[field] = json.loads(path.read_text(encoding="utf-8"))
        accounting[field + "_read_seconds"] = perf_counter() - tick
        accounting[field + "_reads"] = 1
    source_plan, reference, retained, endpoints = (sources[field] for field in
        ("source_plan", "source_analysis", "source_prefixes", "source_endpoints_result"))
    tick = perf_counter()
    copied_fields = ("boards", "contexts", "queries", "source_query_order", "replicates", "arms", "board_count",
        "context_count", "query_count", "replicate_count", "prefix_batches_per_board", "requested_batches_per_arm", "samples_per_batch")
    checks = {"frozen_plan": all(plan[key] == source_plan[key] for key in copied_fields),
        "prefix_plan": retained["plan"] == source_plan, "endpoint_plan": endpoints["plan"] == source_plan,
        "source_analysis": reference["all_analysis_checks_passed"],
        "source_accounting": endpoints["accounting"] == reference["accounting"],
        "historical_batches": endpoints["accounting"]["total_physical_batches"] == plan["historical_physical_batches"],
        "historical_draws": endpoints["accounting"]["total_physical_draws"] == plan["historical_physical_draws"],
        "source_counts": endpoints["source_valid_repetition_count"] == reference["source_valid_stream_count"]
            and endpoints["complete_repetition_count"] == reference["quality_complete_stream_count"],
        "prefix_count": len(retained["query_starts"]) == len(endpoints["query_preparations"]) == plan["expected_prefix_evaluations"],
        "board_prefix_count": len(retained["prefixes"]) == len(endpoints["prefixes"]) == plan["board_count"],
        "repetition_order": [{key: rep[key] for key in ("replicate_index", "base_seed")} for rep in endpoints["repetitions"]] == plan["replicates"],
        "context_orders": all([row["identity"] for row in rep["contexts"]] == [_identity(c) for c in plan["contexts"]] for rep in endpoints["repetitions"]),
        "source_frozen_before_sampling_and_truth": retained["local_acquisition_started"] is False and retained["oracle_constructed"] is False
            and endpoints["all_prefix_snapshots_closed_before_local"] and endpoints["all_sampling_endpoints_closed_before_oracle"]}
    binding = {"passed": all(checks.values()), "checks": checks}
    boards = {row["board_index"]: row for row in plan["boards"]}
    prefix_by_board = {row["board_index"]: row for row in retained["prefixes"]}
    source_prefixes = {row["board_index"]: row for row in endpoints["prefixes"]}
    preparations = {row["identity"]["context_index"]: row for row in endpoints["query_preparations"]}
    baselines, source_states, source_actions = [], [], []
    # All retained policies and their provenance are bound before any exact model.
    for position, context in enumerate(plan["contexts"]):
        index, board_index = context["context_index"], context["board_index"]
        item = retained["query_starts"][position] if position < len(retained["query_starts"]) else {}
        validation, initial = _prefix_validation(item, prefix_by_board[board_index], preparations[index],
            source_prefixes[board_index], context, boards[board_index], plan)
        validation["checks"]["plan_binding"] = binding["passed"]
        validation["passed"] = all(validation["checks"].values())
        prefix_seconds = source_prefixes[board_index]["accounting"]["whole_seconds"]
        prepare_seconds = preparations[index]["accounting"]["whole_seconds"]
        baselines.append({"context_index": index, "identity": _identity(context), "target_key": context["target_key"],
            "initial_batches": context["initial_batches"], "source_validation": validation, "source_valid": validation["passed"],
            "policy_evaluable": False, "first_action_validation": {"passed": False, "reason": "POLICY_NOT_EVALUATED"},
            "evaluation_validation": {"passed": False, "reason": "POLICY_NOT_EVALUATED"},
            "costs": {"prefix_sampling_seconds": prefix_seconds, "single_query_prepare_seconds": prepare_seconds,
                "independent_query_seconds": prefix_seconds + prepare_seconds}})
        source_states.append(item.get("state"))
        source_actions.append(initial)
    accounting["source_validation_seconds"] = perf_counter() - tick
    if progress:
        progress({"stage": "ALL_PREFIX_POLICIES_BOUND", "prefix_count": len(baselines), "source_valid": sum(row["source_valid"] for row in baselines)})
    oracles, closure_counts = {}, {}
    for board in plan["boards"]:
        tick = perf_counter()
        closure = build_development_closure(horizon=board["horizon"], max_nodes=30_000, boards={board["name"]: tuple(board["board"])})
        accounting["exact_closure_construction_seconds"] += perf_counter() - tick
        tick = perf_counter()
        oracles[board["board_index"]] = ExactOracle.from_closure(closure)
        accounting["oracle_initialization_seconds"] += perf_counter() - tick
        closure_counts[board["board_index"]] = closure.counts
    work, stages = Counter(), Counter()
    for baseline, state, initial in zip(baselines, source_states, source_actions):
        if state is None:
            baseline["evaluation_validation"] = {"passed": False, "reason": "MISSING_PREFIX_STATE"}
            continue
        identity = baseline["identity"]
        tick = perf_counter()
        accounting["prefix_policy_evaluation_calls"] += 1
        try:
            evaluation = evaluate_frozen_policy(state, baseline["target_key"], Query(**plan["queries"][identity["query_name"]]), oracles[identity["board_index"]])
        except ValueError as error:
            baseline["evaluation_validation"] = {"passed": False, "reason": str(error)}
        else:
            baseline.update(evaluation=evaluation, evaluation_validation={"passed": True}, policy_evaluable=evaluation["policy_evaluable"])
            observed = initial is not None and any(row["row_key"] == [baseline["target_key"], initial["action"]] for row in state["rows"])
            checks = {key: initial is not None and evaluation[key] == initial[source_key]
                for key, source_key in (("initial_action", "action"), ("lower", "lower"), ("upper", "upper"))}
            checks["selected_action_observed"] = evaluation["selected_action_observed"] == observed
            baseline["first_action_validation"] = {"passed": all(checks.values()), "checks": checks}
            work.update(evaluation["accounting"]["work_counts"])
            stages.update({key: evaluation["accounting"][key] for key in ("policy_extraction_seconds", "fixed_policy_evaluation_seconds")})
        accounting["prefix_policy_evaluation_seconds"] += perf_counter() - tick
    # Preserve all original endpoint values, costs, and source/quality masks.
    repetitions = endpoints["repetitions"]
    tick = perf_counter()
    for rep in repetitions:
        for position, context in enumerate(rep["contexts"]):
            expected, baseline = plan["contexts"][position], baselines[position]
            checks = {"identity": context["identity"] == _identity(expected),
                "target_key": context["target_key"] == expected["target_key"],
                "initial_batches": context["initial_batches"] == expected["initial_batches"],
                "requested_batch_count": context["requested_batch_count"] == expected["requested_batch_count"], "plan_binding": binding["passed"]}
            context["prefix_context_index"] = baseline["context_index"]
            context["prefix_binding_validation"] = {"passed": all(checks.values()), "checks": checks}
            context["comparison_source_valid"] = context["source_valid"] and baseline["source_valid"] and all(checks.values())
            value = baseline.get("evaluation", {})
            context["comparison_complete"] = bool(context["comparison_source_valid"] and context["paired_complete"]
                and baseline["evaluation_validation"]["passed"] and baseline["first_action_validation"]["passed"]
                and value.get("policy_evaluable") and value.get("identities_pass") and value.get("reach_probability_pass"))
        rep["comparison_source_valid"] = rep["source_valid"] and all(row["comparison_source_valid"] for row in rep["contexts"])
        rep["comparison_complete"] = rep["complete"] and all(row["comparison_complete"] for row in rep["contexts"])
    accounting["endpoint_result_binding_seconds"] = perf_counter() - tick
    complete = sum(rep["comparison_complete"] for rep in repetitions)
    report = {"schema": "acfqp.controlled_predictive_prefix_baseline.v29", "plan": plan,
        "status": "PREFIX_BASELINE_COMPLETE" if complete == plan["replicate_count"] else "PREFIX_BASELINE_COMPLETE_WITH_DECLARED_ISSUES",
        "prefix_baselines": baselines, "repetitions": repetitions, "plan_binding_validation": binding,
        "comparison_source_valid_repetition_count": sum(rep["comparison_source_valid"] for rep in repetitions),
        "comparison_complete_repetition_count": complete,
        "source_actual_costs": reference["all_actual_arm_costs"], "source_accounting": endpoints["accounting"],
        "source_analysis_accounting": {key: reference.get(key) for key in ("analysis_seconds", "analysis_result_read_seconds")},
        "accounting": {**accounting, "historical_physical_batches": endpoints["accounting"]["total_physical_batches"],
            "historical_physical_draws": endpoints["accounting"]["total_physical_draws"],
            "new_sampling_calls": 0, "new_physical_batches": 0, "new_physical_draws": 0, "new_planner_solves": 0,
            "new_model_restores": 0, "endpoint_evaluation_calls": 0, "evaluation_work_counts": dict(work), "evaluation_seconds_by_stage": dict(stages),
            "exact_closure_counts_by_board": closure_counts, "oracle_by_board": {index: oracle.accounting() for index, oracle in oracles.items()}},
        "all_prefix_policies_bound_before_oracle": True, "endpoint_evaluations_reused_without_recalculation": True,
        "elapsed_seconds_before_report_serialization": perf_counter() - started,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Each retained prefix policy is evaluated once and referenced across the original suffix streams. V28 endpoint evaluations, source flags and costs are reused unchanged. Historical acquisition is not repeated or refunded. Added reading, binding and exact evaluation are audit overhead; nested evaluation spans are not additive."}
    tick = perf_counter()
    with gzip.open(output_path, "xt", encoding="utf-8") as writer:
        json.dump(report, writer, separators=(",", ":"), allow_nan=False)
    return report, {"report_serialization_seconds": perf_counter() - tick, "report_bytes": output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error("the frozen V29 protocol and plan must exist before evaluation")
    report, serialization = run_prefix_baseline(args.plan, args.output, progress=lambda row: print(json.dumps(row), flush=True))
    print(json.dumps({"status": report["status"], "output": str(args.output),
        "comparison_complete_repetition_count": report["comparison_complete_repetition_count"], **serialization}), flush=True)


if __name__ == "__main__":
    main()
