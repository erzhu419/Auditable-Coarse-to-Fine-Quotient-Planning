#!/usr/bin/env python3
"""Diagnose signed action errors using only the retained V24 target numbers."""

import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_signed_errors_v25 import diagnose_target

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_SIGNED_ERRORS_V25.md")
DEFAULT_PLAN = Path("reports/controlled_predictive_signed_errors_plan_v25.json")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_signed_errors_v25.json")
ARMS = ("CACHED", "VARIANCE", "FRONTIER")
CONTEXT_FIELDS = ("target_key", "requested_batch_count", "initial_batches", "request_index")
SOURCE_TARGET_FIELDS = ("target_key", "query_name", "selected_action", "lower", "upper",
    "selected_action_observed", "interval_closed", "local_true_optimal_actions",
    "selected_action_in_true_optimal_set", "local_regret", "v_star")


def _identity(context):
    return {key: value for key, value in context.items() if key not in ("case", "query", "panel", *CONTEXT_FIELDS)}


def _arm_checks(source_arm, context, arm):
    local = (source_arm or {}).get("local", {})
    target = (source_arm or {}).get("evaluation", {}).get("target", {})
    n, K, initial = local.get("completed_batches"), context["requested_batch_count"], context["initial_batches"]
    checks = {"source_arm_present": source_arm is not None, "source_target_present": bool(target),
        "requested_batch_count": local.get("requested_batch_count") == K,
        "initial_batches": local.get("initial_batches") == initial,
        "completed_fixed_budget": n == K and local.get("completed_fixed_budget") is True,
        "final_batches": n is not None and local.get("final_batches") == initial + n,
        "actual_draws": n is not None and local.get("actual_draws") == 256 * n,
        "common_reset": local.get("initial_batches_matches_common") is True,
        "endpoint_restoration": (source_arm or {}).get("endpoint_restoration", {}).get("passed") is True,
        "target_key": target.get("target_key") == context["target_key"],
        "query_name": target.get("query_name") == context["query_name"],
        "selected_action": bool(target) and target.get("selected_action") == local.get("final_action"),
        "lower": bool(target) and target.get("lower") == local.get("lower"),
        "upper": bool(target) and target.get("upper") == local.get("upper")}
    if arm != "FRONTIER":
        checks.update(first_request=(source_arm or {}).get("first_request_validation", {}).get("passed") is True,
            historical_control=(source_arm or {}).get("source_reference_validation", {}).get("passed") is True)
    return checks


def run_signed_errors(plan_path, output_path, progress=None):
    started_all = perf_counter()
    if output_path.exists():
        raise FileExistsError(f"V25 output already exists: {output_path}")
    accounting, diagnostic_work = Counter(), Counter()
    tick = perf_counter()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    frontier_plan = json.loads(Path(plan["source_frontier_plan"]).read_text(encoding="utf-8"))
    reference = json.loads(Path(plan["source_analysis"]).read_text(encoding="utf-8"))
    accounting["plan_and_source_analysis_read_seconds"] = perf_counter() - tick
    tick = perf_counter()
    source_path = Path(plan["source_result"])
    source = json.loads(source_path.read_text(encoding="utf-8"))
    accounting["source_result_read_seconds"] = perf_counter() - tick
    tick = perf_counter()
    binding_checks = {key: plan[key] == frontier_plan[key] for key in
        ("contexts", "context_count", "queries", "source_query_order", "replicates", "replicate_count", "arms")}
    binding_checks.update(source_plan=source["plan"] == frontier_plan,
        source_accounting=source["accounting"] == reference["accounting"],
        source_complete_count=source["complete_repetition_count"] == reference["complete_stream_count"],
        source_repetition_count=len(source["repetitions"]) == plan["replicate_count"],
        source_complete_labels=source["complete_repetition_count"] == sum(row["complete"] for row in source["repetitions"]),
        historical_batches=source["accounting"]["local_physical_batches"] == plan["historical_physical_batches"],
        historical_draws=source["accounting"]["local_physical_draws"] == plan["historical_physical_draws"])
    plan_binding = {"passed": all(binding_checks.values()), "checks": binding_checks}
    accounting["source_validation_seconds"] += perf_counter() - tick
    repetitions = []
    for rep_position, repetition in enumerate(plan["replicates"]):
        tick = perf_counter()
        source_rep = source["repetitions"][rep_position] if rep_position < len(source["repetitions"]) else None
        rep_checks = {key: source_rep is not None and source_rep.get(key) == value for key, value in repetition.items()}
        source_contexts = (source_rep or {}).get("contexts", [])
        rep_checks.update(context_count=len(source_contexts) == plan["context_count"],
            complete_label=source_rep is not None and source_rep.get("complete") == (
                len(source_contexts) == plan["context_count"] and all(row.get("paired_complete") is True for row in source_contexts)))
        rep_validation = {"passed": all(rep_checks.values()), "checks": rep_checks}
        result_rep = {**repetition, "source_complete": bool(source_rep and source_rep.get("complete")),
            "source_validation": rep_validation, "contexts": []}
        accounting["source_validation_seconds"] += perf_counter() - tick
        for position, context in enumerate(plan["contexts"]):
            tick = perf_counter()
            retained = source_contexts[position] if position < len(source_contexts) else None
            source_arms = (retained or {}).get("arms", {})
            context_checks = {"plan_binding": plan_binding["passed"], "repetition": rep_validation["passed"],
                "identity": retained is not None and retained.get("identity") == _identity(context),
                "arm_set": set(source_arms) == set(ARMS),
                "initial_snapshot": (retained or {}).get("initial_snapshot_validation", {}).get("passed") is True,
                **{key: retained is not None and retained.get(key) == context[key] for key in (*CONTEXT_FIELDS, "panel")}}
            arm_checks = {arm: _arm_checks(source_arms.get(arm), context, arm) for arm in ARMS}
            expected_source_complete = context_checks["initial_snapshot"] and context_checks["arm_set"] and all(
                all(checks.values()) for checks in arm_checks.values())
            context_checks["complete_label"] = retained is not None and retained.get("paired_complete") == expected_source_complete
            context_validation = {"passed": all(context_checks.values()), "checks": context_checks,
                "actual_source_identity": (retained or {}).get("identity")}
            result = {"identity": _identity(context), **{key: context[key] for key in CONTEXT_FIELDS},
                "source_paired_complete": bool(retained and retained.get("paired_complete")),
                "source_validation": context_validation, "arms": {}}
            accounting["source_validation_seconds"] += perf_counter() - tick
            for arm in ARMS:
                source_arm = source_arms.get(arm)
                target = (source_arm or {}).get("evaluation", {}).get("target")
                checks = {**arm_checks[arm], "context": context_validation["passed"]}
                row = {"source_target": {key: target[key] for key in SOURCE_TARGET_FIELDS if key in target} if target else None,
                    "source_validation": {"passed": all(checks.values()), "checks": checks},
                    "raw_valid": False, "counterfactual_available": False}
                if target is None:
                    row["diagnostic_validation"] = {"passed": False, "reason": "MISSING_SOURCE_TARGET"}
                else:
                    tick = perf_counter()
                    try:
                        diagnostic = diagnose_target(target)
                    except ValueError as error:
                        row["diagnostic_validation"] = {"passed": False, "reason": str(error)}
                    else:
                        row["diagnostic"] = diagnostic
                        row["diagnostic_validation"] = {"passed": True}
                        accounting["targets_diagnosed"] += 1
                        diagnostic_work.update({key: diagnostic["accounting"][key]
                            for key in ("action_records_processed", "pair_records_processed")})
                    accounting["numeric_diagnostic_seconds"] += perf_counter() - tick
                    if row["diagnostic_validation"]["passed"]:
                        tick = perf_counter()
                        raw = diagnostic["modes"]["RAW"]
                        raw_checks = {"selected_action": raw["selected_action"] == target["selected_action"],
                            "wrong": raw["wrong"] == (not target["selected_action_in_true_optimal_set"]),
                            "regret": raw["regret"] == target["local_regret"],
                            "lower": raw["lower"] == target["lower"], "upper": raw["upper"] == target["upper"]}
                        row["raw_reproduction_validation"] = {"passed": all(raw_checks.values()), "checks": raw_checks, "numeric_comparison": "EXACT"}
                        row["raw_valid"] = row["source_validation"]["passed"] and raw["available"] and all(raw_checks.values())
                        row["counterfactual_available"] = all(diagnostic["modes"][mode]["available"] for mode in ("REMOVE_A", "REMOVE_D"))
                        accounting["source_validation_seconds"] += perf_counter() - tick
                result["arms"][arm] = row
            result["raw_valid"] = result["source_paired_complete"] and all(row["raw_valid"] for row in result["arms"].values())
            result["paired_complete"] = result["raw_valid"] and all(row["counterfactual_available"] for row in result["arms"].values())
            result["status"] = ("DIAGNOSTIC_COMPLETE" if result["paired_complete"] else
                "COUNTERFACTUAL_UNAVAILABLE" if result["raw_valid"] else "SOURCE_OR_RAW_DIAGNOSTIC_INVALID")
            result_rep["contexts"].append(result)
        result_rep["raw_complete"] = result_rep["source_complete"] and all(row["raw_valid"] for row in result_rep["contexts"])
        result_rep["complete"] = result_rep["raw_complete"] and all(row["paired_complete"] for row in result_rep["contexts"])
        result_rep["status"] = ("REPETITION_COMPLETE" if result_rep["complete"] else
            "RAW_COMPLETE_COUNTERFACTUAL_INCOMPLETE" if result_rep["raw_complete"] else "REPETITION_INVALID")
        repetitions.append(result_rep)
        if progress:
            progress({"stage": "NUMERIC_DIAGNOSIS", **repetition, "raw_complete": result_rep["raw_complete"], "complete": result_rep["complete"]})
    report = {"schema": "acfqp.controlled_predictive_signed_errors.v25", "plan": plan,
        "status": "SIGNED_ERRORS_COMPLETE" if all(row["complete"] for row in repetitions) else "SIGNED_ERRORS_COMPLETE_WITH_DECLARED_ISSUES",
        "repetitions": repetitions, "raw_complete_repetition_count": sum(row["raw_complete"] for row in repetitions),
        "complete_repetition_count": sum(row["complete"] for row in repetitions), "plan_binding_validation": plan_binding,
        "source_actual_arm_costs": reference["all_actual_arm_costs"], "source_accounting": source["accounting"],
        "source_elapsed_seconds_before_report_serialization": source["elapsed_seconds_before_report_serialization"],
        "source_analysis_accounting": {key: reference[key] for key in ("analysis_seconds", "analysis_result_read_seconds") if key in reference},
        "accounting": {**accounting, "diagnostic_work_counts": dict(diagnostic_work), "source_result_reads": 1,
            "source_result_bytes": source_path.stat().st_size, "historical_physical_batches": source["accounting"]["local_physical_batches"],
            "historical_physical_draws": source["accounting"]["local_physical_draws"],
            "new_provider_calls": 0, "new_oracle_calls": 0, "new_physical_draws": 0,
            "model_restore_calls": 0, "source_endpoint_reads": 0},
        "new_provider_calls": 0, "new_oracle_calls": 0, "new_physical_draws": 0,
        "elapsed_seconds_before_report_serialization": perf_counter() - started_all,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Pure numerical attribution of fixed V24 target estimates. RAW source validity is retained separately from counterfactual availability; no argmax over a known-action subset. Historical acquisition and analysis costs remain historical, not newly charged work. All diagnosis uses retained numbers without providers, model restoration or a new oracle."}
    tick = perf_counter()
    with output_path.open("x", encoding="utf-8") as writer:
        json.dump(report, writer, separators=(",", ":"), allow_nan=False)
        writer.write("\n")
    return report, {"report_serialization_seconds": perf_counter() - tick, "report_bytes": output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error("the frozen V25 protocol and plan must exist before numeric diagnosis")
    report, serialization = run_signed_errors(args.plan, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({"status": report["status"], "raw_complete_repetition_count": report["raw_complete_repetition_count"],
        "complete_repetition_count": report["complete_repetition_count"], "output": str(args.output), **serialization}), flush=True)


if __name__ == "__main__":
    main()
