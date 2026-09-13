#!/usr/bin/env python3
"""Run the frozen four-arm factorial allocation comparison and replay its controls."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_local_v21 import run_local_allocation, evaluate_local_snapshot, evaluate_panel
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_snapshot_v21 import state_record
from acfqp.science.controlled_predictive_restore_v22 import load_common_snapshots, restore_state
from run_controlled_predictive_frontier_v24 import (
    _compact_target, _initial_checks, _reference_checks, TRACE_FIELDS, REFERENCE_FIELDS)

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_FACTORIAL_V26.md")
DEFAULT_PLAN = Path("reports/controlled_predictive_factorial_plan_v26.json")
DEFAULT_ENDPOINTS = Path("reports/controlled_predictive_factorial_endpoints_v26.jsonl.gz")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_factorial_v26.json")
ARMS = ("CACHED", "VARIANCE", "FRONTIER", "FRONTIER_VARIANCE")
REFERENCE_ARMS = ARMS[:3]



def run_factorial(plan_path, endpoints_path, output_path, progress=None):
    started_all = perf_counter()
    for path in (endpoints_path, output_path):
        if path.exists():
            raise FileExistsError(f"V26 output already exists: {path}")
    accounting = Counter()
    tick = perf_counter()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    reference_plan = json.loads(Path(plan["source_frontier_plan"]).read_text(encoding="utf-8"))
    binding_checks = {key: plan[key] == reference_plan[key] for key in
        ("source_common_snapshots", "source_query_order", "queries", "contexts", "replicates", "context_count", "replicate_count")}
    plan_binding = {"passed": all(binding_checks.values()), "checks": binding_checks}
    accounting["frozen_plan_read_and_binding_seconds"] = perf_counter() - tick
    tick = perf_counter()
    with gzip.open(plan["source_common_snapshots"], "rt", encoding="utf-8") as reader:
        common_payload = json.load(reader)
    accounting["common_snapshot_read_seconds"] = perf_counter() - tick
    tick = perf_counter()
    snapshots, restoration_validation, preparation_accounting = load_common_snapshots(common_payload)
    accounting["common_restoration_wall_seconds"] = perf_counter() - tick
    source_queries_equal = (common_payload["cohort_roster"]["initial_query_order"] == plan["source_query_order"]
                            and common_payload["cohort_roster"]["queries"] == plan["queries"])
    del common_payload, reference_plan
    snapshot_lookup = {snapshot.identity["context_index"]: snapshot for snapshot in snapshots}
    plan_checks = {}
    for context in plan["contexts"]:
        index = context["context_index"]
        checks = _initial_checks(snapshot_lookup[index], context) if index in snapshot_lookup else {"source_snapshot_found": False}
        checks.update(source_queries=source_queries_equal, frozen_plan_binding=plan_binding["passed"])
        plan_checks[index] = {"passed": all(checks.values()), "checks": checks}
    provider_totals, arm_stage_seconds, arm_work = ({arm: Counter() for arm in ARMS} for _ in range(3))
    tick = perf_counter()
    writer = gzip.open(endpoints_path, "xt", encoding="utf-8")
    accounting["endpoint_stream_open_seconds"] = perf_counter() - tick
    try:
        for repetition in plan["replicates"]:
            replicate_index, seed = repetition["replicate_index"], repetition["base_seed"]
            complete_count = 0
            for context in plan["contexts"]:
                index = context["context_index"]
                identity = {key: value for key, value in context.items() if key not in
                    ("case", "query", "target_key", "panel", "requested_batch_count", "request_index", "initial_batches")}
                offset = (replicate_index + index) % len(ARMS)
                order = ARMS[offset:] + ARMS[:offset]
                pair = {**repetition, "identity": identity, "target_key": context["target_key"], "panel": context["panel"],
                    "requested_batch_count": context["requested_batch_count"], "initial_batches": context["initial_batches"],
                    "request_index": context["request_index"], "run_order": list(order), "arms": {},
                    "initial_snapshot_validation": plan_checks[index]}
                if not plan_checks[index]["passed"]:
                    pair.update(status="SOURCE_RESTORATION_MISMATCH", paired_complete=False)
                else:
                    snapshot = snapshot_lookup[index]
                    for arm in order:
                        provider = BatchRowSampleProvider(seed)
                        state, local = run_local_allocation(snapshot.state, arm, provider, snapshot.query_name,
                            snapshot.target_key, requested_batches=context["requested_batch_count"])
                        accounting["local_arm_run_count"] += 1
                        accounting["reset_from_original_common_snapshot_count"] += 1
                        accounting["local_allocation_wall_seconds"] += local["accounting"]["whole_run_seconds"]
                        provider_totals[arm].update(local["provider_counts"])
                        arm_stage_seconds[arm].update(local["accounting"]["seconds_by_stage"])
                        arm_work[arm].update(local["accounting"]["work_counts"])
                        tick = perf_counter()
                        if arm in ("CACHED", "VARIANCE"):
                            expected = snapshot.source_nodes[arm]["requested_batches"][snapshot.request_index]
                            first = local["requested_batches"][0] if local["requested_batches"] else None
                            first_validation = {"passed": first == expected, "applicable": True, "expected": expected, "actual": first}
                        else:
                            first_validation = {"passed": True, "applicable": False,
                                "scope": "No V21 first-request control for this arm. The common start and fixed budget are checked; V24 full traces are checked for the three retained controls."}
                        local["initial_batches_matches_common"] = local["initial_batches"] == context["initial_batches"]
                        local["repeat_batches_on_rows_absent_from_common"] = sum(
                            request["kind"] == "REPEAT_OBSERVATION" and
                            ((request["row_key"][0][0], tuple(request["row_key"][0][1])), request["row_key"][1]) not in snapshot.state.rows
                            for request in local["requested_batches"])
                        accounting["first_request_reset_and_repeat_accounting_seconds"] += perf_counter() - tick
                        tick = perf_counter()
                        pair["arms"][arm] = {"state": state_record(state, snapshot.query_name), "local": local,
                                             "first_request_validation": first_validation}
                        accounting["endpoint_materialization_seconds"] += perf_counter() - tick
                        del state
                    complete = all(row["local"]["completed_fixed_budget"] for row in pair["arms"].values())
                    valid = all(row["first_request_validation"]["passed"] and row["local"]["initial_batches_matches_common"]
                                for row in pair["arms"].values())
                    pair["paired_complete"] = complete and valid
                    pair["status"] = "FIXED_BUDGET_INCOMPLETE" if not complete else "FIRST_REQUEST_OR_RESET_MISMATCH" if not valid else "PAIR_COMPLETE"
                complete_count += pair["paired_complete"]
                tick = perf_counter()
                json.dump(pair, writer, separators=(",", ":"), allow_nan=False)
                writer.write("\n")
                accounting["endpoint_stream_write_seconds"] += perf_counter() - tick
                accounting["endpoint_group_records_written"] += 1
            if progress:
                progress({"stage": "SAMPLING", **repetition, "groups_written": len(plan["contexts"]), "complete_groups": complete_count})
    finally:
        tick = perf_counter()
        writer.close()
        accounting["endpoint_stream_close_seconds"] += perf_counter() - tick
    # All physical acquisition and endpoint serialization finish before truth.
    queries = {name: Query(**plan["queries"][name]) for name in plan["source_query_order"]}
    eligible_snapshots = [snapshot_lookup[row["context_index"]] for row in plan["contexts"] if plan_checks[row["context_index"]]["passed"]]
    initial_evaluations, oracle, exact_closure_counts = [], None, {}
    if eligible_snapshots:
        case = plan["contexts"][0]["case"]
        tick = perf_counter()
        closure = build_development_closure(horizon=case["horizon"], max_nodes=30_000,
                                           boards={case["name"]: tuple(case["board"])})
        accounting["exact_closure_construction_seconds"] = perf_counter() - tick
        exact_closure_counts = closure.counts
        oracle = ExactOracle.from_closure(closure)
        for snapshot in eligible_snapshots:
            tick = perf_counter()
            initial_evaluations.append({"identity": snapshot.identity,
                "target": _compact_target(evaluate_local_snapshot(snapshot.state, snapshot.query_name, snapshot.target_key, oracle)),
                "panel": evaluate_panel(snapshot.state, snapshot.query_name, snapshot.panel, oracle)})
            accounting["initial_evaluation_seconds"] += perf_counter() - tick
    repetitions = [{**replicate, "contexts": []} for replicate in plan["replicates"]]
    repetition_lookup = {row["replicate_index"]: row for row in repetitions}
    reference_counts = {arm: Counter() for arm in REFERENCE_ARMS}
    with gzip.open(endpoints_path, "rt", encoding="utf-8") as reader, gzip.open(plan["source_control_endpoints"], "rt", encoding="utf-8") as source_reader:
        while True:
            tick = perf_counter()
            line = reader.readline()
            endpoint = json.loads(line) if line else None
            accounting["endpoint_reload_read_seconds"] += perf_counter() - tick
            if endpoint is None:
                break
            accounting["endpoint_group_records_reloaded"] += 1
            tick = perf_counter()
            source_line = source_reader.readline()
            source = json.loads(source_line) if source_line else None
            accounting["source_reference_read_seconds"] += perf_counter() - tick
            accounting["source_reference_pair_records_read"] += source is not None
            result = {key: value for key, value in endpoint.items() if key not in ("arms", "replicate_index", "base_seed")}
            result["arms"] = {}
            for arm, row in endpoint["arms"].items():
                compact = {"local": {key: value for key, value in row["local"].items() if key not in TRACE_FIELDS},
                           "first_request_validation": row["first_request_validation"]}
                if arm in REFERENCE_ARMS:
                    tick = perf_counter()
                    validation = _reference_checks(endpoint, source, arm)
                    accounting["source_reference_comparison_seconds"] += perf_counter() - tick
                    compact["source_reference_validation"] = validation
                    reference_counts[arm].update(checked=1, passed=validation["passed"], failed=not validation["passed"])
                    if not validation["passed"]:
                        result.update(status="SOURCE_REFERENCE_MISMATCH", paired_complete=False)
                else:
                    compact["source_reference_validation"] = {"passed": True, "applicable": False}
                tick = perf_counter()
                try:
                    state = restore_state(row["state"], queries, query_name=endpoint["identity"]["query_name"])
                except ValueError as error:
                    compact["endpoint_restoration"] = {"passed": False, "reason": str(error)}
                    result.update(status="ENDPOINT_RESTORATION_MISMATCH", paired_complete=False)
                else:
                    compact["endpoint_restoration"] = {"passed": True}
                    accounting["endpoint_states_restored"] += 1
                accounting["endpoint_restoration_seconds"] += perf_counter() - tick
                if compact["endpoint_restoration"]["passed"]:
                    target = endpoint["target_key"][0], tuple(endpoint["target_key"][1])
                    panel = tuple((key[0], tuple(key[1])) for key in endpoint["panel"])
                    tick = perf_counter()
                    compact["evaluation"] = {
                        "target": _compact_target(evaluate_local_snapshot(state, endpoint["identity"]["query_name"], target, oracle)),
                        "panel": evaluate_panel(state, endpoint["identity"]["query_name"], panel, oracle)}
                    accounting["endpoint_evaluation_seconds"] += perf_counter() - tick
                    del state
                result["arms"][arm] = compact
            repetition_lookup[endpoint["replicate_index"]]["contexts"].append(result)
            current_rep = repetition_lookup[endpoint["replicate_index"]]
            if progress and len(current_rep["contexts"]) == len(plan["contexts"]):
                progress({"stage": "EVALUATION", "replicate_index": current_rep["replicate_index"],
                    "base_seed": current_rep["base_seed"],
                    "complete_groups": sum(row["paired_complete"] for row in current_rep["contexts"])})
        tick = perf_counter()
        accounting["unexpected_source_reference_records"] = sum(1 for _ in source_reader)
        accounting["source_reference_read_seconds"] += perf_counter() - tick
    for repetition in repetitions:
        repetition["complete"] = (len(repetition["contexts"]) == len(plan["contexts"])
            and all(row["paired_complete"] for row in repetition["contexts"]))
        repetition["status"] = "REPETITION_COMPLETE" if repetition["complete"] else "REPETITION_INCOMPLETE"
    reference_validation = {"numeric_comparison": "EXACT", "fields": list(REFERENCE_FIELDS),
        "by_arm": {arm: dict(counts) for arm, counts in reference_counts.items()},
        "all_passed": not accounting["unexpected_source_reference_records"] and all(
            counts["checked"] == len(plan["replicates"]) * len(plan["contexts"]) and not counts["failed"]
            for counts in reference_counts.values()), "costs_compared_separately": True}
    report = {"schema": "acfqp.controlled_predictive_factorial.v26", "plan": plan,
        "status": "REPETITIONS_COMPLETE" if all(row["complete"] for row in repetitions) and reference_validation["all_passed"] else "REPETITIONS_COMPLETE_WITH_DECLARED_ISSUES",
        "initial_evaluations": initial_evaluations, "repetitions": repetitions,
        "complete_repetition_count": sum(row["complete"] for row in repetitions),
        "restoration_validation": restoration_validation, "plan_binding_validation": plan_binding,
        "source_reference_validation": reference_validation,
        "plan_snapshot_validation": [{"context_index": index, **checks} for index, checks in plan_checks.items()],
        "accounting": {**accounting, "common_preparation": preparation_accounting,
            "warm_provider_calls": 0, "warm_physical_draws": 0,
            "local_physical_batches": sum(counts.get("row_requests", 0) for counts in provider_totals.values()),
            "local_physical_draws": sum(counts.get("physical_draws", 0) for counts in provider_totals.values()),
            "provider_counts_by_arm": {arm: dict(counts) for arm, counts in provider_totals.items()},
            "local_seconds_by_stage_by_arm": {arm: dict(values) for arm, values in arm_stage_seconds.items()},
            "local_work_counts_by_arm": {arm: dict(values) for arm, values in arm_work.items()},
            "endpoint_artifact_bytes": endpoints_path.stat().st_size, "exact_closure_counts": exact_closure_counts,
            "oracle": oracle.accounting() if oracle is not None else None},
        "all_sampling_endpoints_closed_before_oracle": True, "endpoint_reload_uses_provider": False,
        "endpoint_artifact": str(endpoints_path), "elapsed_seconds_before_report_serialization": perf_counter() - started_all,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Four methods reset from the same exposed common starts and receive identical fixed local batch budgets. Same repetition seeds correlate contexts and arms; complete repetitions are the Monte Carlo unit. Target/panel optimal-continuation action regret is not complete online policy value. All new provider calls are physically charged, including replayed controls. The frontier extension is included in structural_selection timing. In FRONTIER_VARIANCE, frontier_to_balanced_fallbacks marks entry to resampling; variance_fallback_calls counts actual variance-to-balanced fallback. Nested preparation/local/evaluation stage timings are not additive."}
    tick = perf_counter()
    with output_path.open("x", encoding="utf-8") as writer:
        json.dump(report, writer, separators=(",", ":"), allow_nan=False)
        writer.write("\n")
    return report, {"report_serialization_seconds": perf_counter() - tick, "report_bytes": output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--endpoints", type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error("the frozen V26 protocol and plan must exist before sampling")
    report, serialization = run_factorial(args.plan, args.endpoints, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({"status": report["status"], "complete_repetition_count": report["complete_repetition_count"],
        "source_reference_passed": report["source_reference_validation"]["all_passed"], "output": str(args.output), **serialization}), flush=True)


if __name__ == "__main__":
    main()
