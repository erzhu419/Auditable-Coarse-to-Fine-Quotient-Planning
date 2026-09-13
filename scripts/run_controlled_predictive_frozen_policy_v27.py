#!/usr/bin/env python3
"""Evaluate complete retained V26 policies without restoring or replanning models."""

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

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_FROZEN_POLICY_V27.md")
DEFAULT_PLAN = Path("reports/controlled_predictive_frozen_policy_plan_v27.json")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_frozen_policy_v27.json")
ARMS = ("CACHED", "VARIANCE", "FRONTIER", "FRONTIER_VARIANCE")
CONTEXT_FIELDS = ("target_key", "panel", "requested_batch_count", "initial_batches", "request_index")
LOCAL_FIELDS = ("arm", "query_name", "target_key", "requested_batch_count", "completed_batches",
    "completed_fixed_budget", "initial_batches", "final_batches", "actual_draws", "final_action",
    "lower", "upper", "unresolved", "selected_action_observed", "stop_reason")


def _identity(context):
    return {key: value for key, value in context.items() if key not in ("case", "query", *CONTEXT_FIELDS)}


def _source_arm_checks(row, context, arm, queries):
    local, state = (row or {}).get("local", {}), (row or {}).get("state", {})
    n, K, initial = local.get("completed_batches"), context["requested_batch_count"], context["initial_batches"]
    provider = local.get("provider_counts", {})
    checks = {"source_arm_found": row is not None, "state_found": bool(state), "arm": local.get("arm") == arm,
        "query_name": local.get("query_name") == context["query_name"], "query_weights": state.get("query") == queries[context["query_name"]],
        "target_key": local.get("target_key") == context["target_key"],
        "fixed_K": local.get("requested_batch_count") == K and n == K,
        "completed_fixed_budget": local.get("completed_fixed_budget") is True,
        "initial_batches": local.get("initial_batches") == initial and local.get("initial_batches_matches_common") is True,
        "final_batches": n is not None and local.get("final_batches") == initial + n and initial + n <= 128,
        "draws": n is not None and local.get("actual_draws") == 256*n and provider.get("physical_draws", 0) == 256*n,
        "provider_batches": provider.get("row_requests", 0) == n,
        "retained_model_batches": bool(state) and state.get("spent_batches") == local.get("final_batches")
            and sum(row["batch_count"] for row in state.get("rows", [])) == state.get("spent_batches"),
        "retained_row_count": bool(state) and len(state.get("row_order", [])) == len(state.get("rows", [])),
        "first_request_validation": (row or {}).get("first_request_validation", {}).get("passed") is True}
    return checks


def run_frozen_policy(plan_path, output_path, progress=None):
    started_all = perf_counter()
    if output_path.exists():
        raise FileExistsError(f"V27 output already exists: {output_path}")
    accounting, evaluation_work, evaluation_stages = Counter(), Counter(), Counter()
    tick = perf_counter()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    factorial_plan = json.loads(Path(plan["source_factorial_plan"]).read_text(encoding="utf-8"))
    reference = json.loads(Path(plan["source_analysis"]).read_text(encoding="utf-8"))
    accounting["frozen_plan_and_source_analysis_read_seconds"] = perf_counter() - tick
    tick = perf_counter()
    binding_checks = {key: plan[key] == factorial_plan[key] for key in
        ("contexts", "context_count", "replicates", "replicate_count", "queries", "source_query_order", "arms")}
    statuses = reference["stream_statuses"]
    binding_checks.update(source_analysis_passed=reference["all_analysis_checks_passed"] is True,
        source_stream_identities=[{key: row[key] for key in ("replicate_index", "base_seed")} for row in statuses] == plan["replicates"],
        source_complete_count=reference["complete_stream_count"] == sum(row["complete"] for row in statuses),
        historical_batches=reference["accounting"]["local_physical_batches"] == plan["historical_physical_batches"],
        historical_draws=reference["accounting"]["local_physical_draws"] == plan["historical_physical_draws"])
    plan_binding = {"passed": all(binding_checks.values()), "checks": binding_checks}
    status_lookup = {row["replicate_index"]: row for row in statuses}
    accounting["source_validation_seconds"] += perf_counter() - tick
    queries = {name: Query(**plan["queries"][name]) for name in plan["source_query_order"]}
    case = plan["contexts"][0]["case"]
    tick = perf_counter()
    closure = build_development_closure(horizon=case["horizon"], max_nodes=30_000,
                                       boards={case["name"]: tuple(case["board"])})
    accounting["exact_closure_construction_seconds"] = perf_counter() - tick
    tick = perf_counter()
    oracle = ExactOracle.from_closure(closure)
    accounting["oracle_initialization_seconds"] = perf_counter() - tick
    repetitions = []
    source_path = Path(plan["source_endpoints"])
    with gzip.open(source_path, "rt", encoding="utf-8") as reader:
        for repetition in plan["replicates"]:
            source_status = status_lookup.get(repetition["replicate_index"])
            source_complete = bool(source_status and source_status.get("complete"))
            result_rep = {**repetition, "source_complete": source_complete, "contexts": []}
            for context in plan["contexts"]:
                tick = perf_counter()
                line = reader.readline()
                endpoint = json.loads(line) if line else None
                accounting["source_endpoint_read_seconds"] += perf_counter() - tick
                accounting["source_endpoint_records_read"] += endpoint is not None
                tick = perf_counter()
                offset = (repetition["replicate_index"] + context["context_index"]) % len(ARMS)
                expected = {**repetition, "identity": _identity(context),
                    **{key: context[key] for key in CONTEXT_FIELDS}, "run_order": list(ARMS[offset:] + ARMS[:offset])}
                checks = {key: endpoint is not None and endpoint.get(key) == value for key, value in expected.items()}
                checks.update(frozen_source_binding=plan_binding["passed"], source_complete_stream=source_complete,
                    initial_snapshot=(endpoint or {}).get("initial_snapshot_validation", {}).get("passed") is True,
                    four_arms=set((endpoint or {}).get("arms", {})) == set(ARMS))
                source_arms = (endpoint or {}).get("arms", {})
                arm_checks = {arm: _source_arm_checks(source_arms.get(arm), context, arm, plan["queries"]) for arm in ARMS}
                complete_from_records = checks["initial_snapshot"] and checks["four_arms"] and all(
                    all(values.values()) for values in arm_checks.values())
                checks["source_complete_label"] = endpoint is not None and endpoint.get("paired_complete") == complete_from_records
                context_validation = {"passed": all(checks.values()), "checks": checks,
                    "actual_source_identity": None if endpoint is None else {key: endpoint.get(key) for key in ("replicate_index", "base_seed", "identity")}}
                result = {"identity": _identity(context), **{key: context[key] for key in CONTEXT_FIELDS},
                    "source_paired_complete": bool(endpoint and endpoint.get("paired_complete")),
                    "source_validation": context_validation, "arms": {}}
                accounting["source_validation_seconds"] += perf_counter() - tick
                for arm in ARMS:
                    source_arm = source_arms.get(arm)
                    local = (source_arm or {}).get("local", {})
                    values = {**arm_checks[arm], "context": context_validation["passed"]}
                    row = {"source_local": {key: local[key] for key in LOCAL_FIELDS if key in local},
                        "source_validation": {"passed": all(values.values()), "checks": values},
                        "first_action_validation": {"passed": False, "reason": "POLICY_NOT_EVALUATED"},
                        "source_valid": False, "policy_evaluable": False}
                    if source_arm is None or "state" not in source_arm:
                        row["evaluation_validation"] = {"passed": False, "reason": "MISSING_RETAINED_POLICY"}
                    else:
                        tick = perf_counter()
                        accounting["frozen_policy_evaluation_calls"] += 1
                        try:
                            evaluation = evaluate_frozen_policy(source_arm["state"], context["target_key"],
                                queries[context["query_name"]], oracle)
                        except ValueError as error:
                            row["evaluation_validation"] = {"passed": False, "reason": str(error)}
                        else:
                            row["evaluation"] = evaluation
                            row["evaluation_validation"] = {"passed": True}
                            evaluation_work.update(evaluation.get("accounting", {}).get("work_counts", {}))
                            evaluation_stages.update({key: evaluation["accounting"][key]
                                for key in ("policy_extraction_seconds", "fixed_policy_evaluation_seconds")})
                        accounting["frozen_policy_evaluation_seconds"] += perf_counter() - tick
                        if row["evaluation_validation"]["passed"]:
                            tick = perf_counter()
                            first_checks = {"initial_action": evaluation["initial_action"] == local.get("final_action"),
                                "lower": evaluation["lower"] == local.get("lower"), "upper": evaluation["upper"] == local.get("upper"),
                                "selected_action_observed": evaluation["selected_action_observed"] == local.get("selected_action_observed")}
                            row["first_action_validation"] = {"passed": all(first_checks.values()), "checks": first_checks, "numeric_comparison": "EXACT"}
                            row["source_valid"] = row["source_validation"]["passed"] and all(first_checks.values())
                            row["policy_evaluable"] = evaluation["policy_evaluable"]
                            accounting["source_validation_seconds"] += perf_counter() - tick
                    result["arms"][arm] = row
                result["source_valid"] = result["source_paired_complete"] and all(row["source_valid"] for row in result["arms"].values())
                result["policy_evaluable"] = all(row["policy_evaluable"] for row in result["arms"].values())
                result["paired_complete"] = result["source_valid"] and result["policy_evaluable"] and all(
                    row["evaluation"]["identities_pass"] and row["evaluation"]["reach_probability_pass"] for row in result["arms"].values())
                result["status"] = ("POLICY_EVALUATION_COMPLETE" if result["paired_complete"] else
                    "SOURCE_OR_FIRST_ACTION_INVALID" if not result["source_valid"] else
                    "POLICY_UNDEFINED_ON_TRUE_REACH" if not result["policy_evaluable"] else "POLICY_EVALUATION_INVALID")
                result_rep["contexts"].append(result)
            result_rep["source_valid"] = source_complete and all(row["source_valid"] for row in result_rep["contexts"])
            result_rep["complete"] = result_rep["source_valid"] and all(row["paired_complete"] for row in result_rep["contexts"])
            result_rep["status"] = "REPETITION_COMPLETE" if result_rep["complete"] else "REPETITION_INCOMPLETE"
            repetitions.append(result_rep)
            if progress:
                progress({"stage": "FROZEN_POLICY_EVALUATION", **repetition,
                    "source_valid": result_rep["source_valid"], "complete": result_rep["complete"]})
        tick = perf_counter()
        accounting["unexpected_source_endpoint_records"] = sum(1 for _ in reader)
        accounting["source_endpoint_read_seconds"] += perf_counter() - tick
    source_stream_validation = {"passed": accounting["source_endpoint_records_read"] == plan["expected_quadruplet_count"]
        and not accounting["unexpected_source_endpoint_records"], "expected_records": plan["expected_quadruplet_count"],
        "records_read": accounting["source_endpoint_records_read"], "unexpected_records": accounting["unexpected_source_endpoint_records"]}
    if not source_stream_validation["passed"]:
        for repetition in repetitions:
            repetition.update(source_valid=False, complete=False, status="SOURCE_STREAM_COUNT_MISMATCH")
    report = {"schema": "acfqp.controlled_predictive_frozen_policy.v27", "plan": plan,
        "status": "FROZEN_POLICY_COMPLETE" if all(row["complete"] for row in repetitions) else "FROZEN_POLICY_COMPLETE_WITH_DECLARED_ISSUES",
        "repetitions": repetitions, "source_valid_repetition_count": sum(row["source_valid"] for row in repetitions),
        "complete_repetition_count": sum(row["complete"] for row in repetitions),
        "plan_binding_validation": plan_binding, "source_stream_validation": source_stream_validation,
        "source_actual_arm_costs": reference["all_actual_arm_costs"], "source_accounting": reference["accounting"],
        "source_elapsed_seconds_before_report_serialization": reference["elapsed_seconds_before_report_serialization"],
        "source_analysis_accounting": {key: reference[key] for key in ("analysis_seconds", "analysis_result_read_seconds") if key in reference},
        "accounting": {**accounting, "evaluation_work_counts": dict(evaluation_work),
            "evaluation_seconds_by_stage": dict(evaluation_stages), "source_endpoint_reads": 1,
            "source_endpoint_bytes": source_path.stat().st_size, "exact_closure_counts": closure.counts, "oracle": oracle.accounting(),
            "historical_physical_batches": reference["accounting"]["local_physical_batches"],
            "historical_physical_draws": reference["accounting"]["local_physical_draws"],
            "new_sampling_calls": 0, "new_provider_calls": 0, "new_physical_batches": 0, "new_physical_draws": 0,
            "new_replanning_calls": 0, "model_restore_calls": 0, "oracle_instance_count": 1},
        "elapsed_seconds_before_report_serialization": perf_counter() - started_all,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Exact evaluation of the complete retained endpoint policy from the original target. No policy is restored, solved, extended or replanned; undefined true-reachable ACTIVE decisions retain missing probability and disable complete-policy metrics. All V26 acquisition remains historical. New source reading, exact model/oracle and fixed-policy evaluation are charged separately; nested evaluation/oracle spans are not additive."}
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
        parser.error("the frozen V27 protocol and plan must exist before policy evaluation")
    report, serialization = run_frozen_policy(args.plan, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({"status": report["status"], "source_valid_repetition_count": report["source_valid_repetition_count"],
        "complete_repetition_count": report["complete_repetition_count"], "output": str(args.output), **serialization}), flush=True)


if __name__ == "__main__":
    main()
