#!/usr/bin/env python3
"""Project retained V22 endpoints onto their original observed rows, then evaluate."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_comparison_v14 import _json_structure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_local_v21 import evaluate_local_snapshot, evaluate_panel
from acfqp.science.controlled_predictive_projection_v23 import project_endpoint
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_restore_v22 import load_common_snapshots, restore_state
from acfqp.science.controlled_predictive_snapshot_v21 import state_record

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_PROJECTION_V23.md")
DEFAULT_PLAN = Path("reports/controlled_predictive_projection_plan_v23.json")
DEFAULT_ENDPOINTS = Path("reports/controlled_predictive_projected_endpoints_v23.jsonl.gz")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_projection_v23.json")
ARMS = ("CACHED", "VARIANCE")
MODELS = ("FULL", "PROJECTED")
TRACE_FIELDS = ("requested_batches", "observed_batches", "gap_assessments")
CONTEXT_FIELDS = ("target_key", "panel", "requested_batch_count", "initial_batches", "request_index")


def _identity(context):
    return {key: value for key, value in context.items() if key not in
        ("case", "query", *CONTEXT_FIELDS, "initial_row_keys", "initial_observed_row_count")}


def _expected_pair(repetition, context):
    order = ARMS if (repetition["replicate_index"] + context["context_index"]) % 2 == 0 else ARMS[::-1]
    return {**repetition, "identity": _identity(context),
        **{key: context[key] for key in CONTEXT_FIELDS}, "run_order": list(order)}


def _alignment(record, expected):
    checks = {key: record is not None and record.get(key) == value for key, value in expected.items()}
    return {"passed": all(checks.values()), "checks": checks,
        "actual_source_identity": None if record is None else {
            key: record.get(key) for key in ("replicate_index", "base_seed", "identity")}}


def _read_pair(reader, accounting, stage):
    tick = perf_counter()
    line = reader.readline()
    record = json.loads(line) if line else None
    accounting[stage + "_seconds"] += perf_counter() - tick
    accounting[stage + "_records"] += record is not None
    return record


def _compact_target(result):
    return {**result, "actions": {action: {key: value for key, value in row.items() if key != "children"}
                                 for action, row in result["actions"].items()}}


def _full_control(target, local):
    checks = {"selected_action": target["selected_action"] == local["final_action"],
        "lower": target["lower"] == local["lower"], "upper": target["upper"] == local["upper"],
        "selected_action_observed": target["selected_action_observed"] == local["selected_action_observed"],
        "interval_closed": target["interval_closed"] == (not local["unresolved"])}
    return {"passed": all(checks.values()), "checks": checks, "numeric_comparison": "EXACT"}


def run_projection(plan_path, endpoints_path, output_path, progress=None):
    started_all = perf_counter()
    for path in (endpoints_path, output_path):
        if path.exists():
            raise FileExistsError(f"V23 output already exists: {path}")
    accounting = Counter()
    tick = perf_counter()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    source_plan = json.loads(Path(plan["source_repetition_plan"]).read_text(encoding="utf-8"))
    reference = json.loads(Path(plan["source_repetition_analysis"]).read_text(encoding="utf-8"))
    accounting["frozen_plan_and_source_analysis_read_seconds"] = perf_counter() - tick
    source_path = Path(plan["source_repetition_endpoints"])
    tick = perf_counter()
    with gzip.open(plan["source_common_snapshots"], "rt", encoding="utf-8") as handle:
        common_payload = json.load(handle)
    accounting["common_snapshot_read_seconds"] = perf_counter() - tick
    snapshots, restoration_validation, preparation_accounting = load_common_snapshots(common_payload)
    snapshot_lookup = {snapshot.identity["context_index"]: snapshot for snapshot in snapshots}
    binding_checks = {key: plan[key] == source_plan[key] for key in
        ("source_common_snapshots", "source_query_order", "queries", "replicates", "context_count", "replicate_count")}
    binding_checks.update(contexts=[{key: value for key, value in row.items()
        if key not in ("initial_row_keys", "initial_observed_row_count")} for row in plan["contexts"]] == source_plan["contexts"],
        source_batches=plan["source_physical_batches"] == reference["accounting"]["local_physical_batches"],
        source_draws=plan["source_physical_draws"] == reference["accounting"]["local_physical_draws"],
        common_queries=common_payload["cohort_roster"]["queries"] == plan["queries"],
        common_query_order=common_payload["cohort_roster"]["initial_query_order"] == plan["source_query_order"])
    plan_binding = {"passed": all(binding_checks.values()), "checks": binding_checks}
    del common_payload, source_plan
    plan_checks = {}
    for context in plan["contexts"]:
        snapshot = snapshot_lookup.get(context["context_index"])
        checks = {"frozen_source_binding": plan_binding["passed"], "common_snapshot_found": snapshot is not None}
        if snapshot is not None:
            checks.update(identity=snapshot.identity == _identity(context),
                target_key=_json_structure(snapshot.target_key) == context["target_key"],
                panel=_json_structure(snapshot.panel) == context["panel"],
                requested_batch_count=snapshot.requested_batch_count == context["requested_batch_count"],
                request_index=snapshot.request_index == context["request_index"],
                initial_batches=snapshot.state.spent_batches == context["initial_batches"],
                initial_row_keys=_json_structure(snapshot.state.row_order) == context["initial_row_keys"],
                initial_observed_row_count=len(snapshot.state.rows) == context["initial_observed_row_count"])
        plan_checks[context["context_index"]] = {"passed": all(checks.values()), "checks": checks}
    queries = {name: Query(**plan["queries"][name]) for name in plan["source_query_order"]}
    projection_counts = {arm: Counter() for arm in ARMS}
    projection_work = {arm: Counter() for arm in ARMS}
    tick = perf_counter()
    writer = gzip.open(endpoints_path, "xt", encoding="utf-8")
    accounting["projected_stream_open_seconds"] = perf_counter() - tick
    try:
        with gzip.open(source_path, "rt", encoding="utf-8") as reader:
            for repetition in plan["replicates"]:
                for context in plan["contexts"]:
                    expected = _expected_pair(repetition, context)
                    source = _read_pair(reader, accounting, "source_first_read")
                    alignment = _alignment(source, expected)
                    initial = plan_checks[context["context_index"]]
                    pair = {**expected, "source_alignment_validation": alignment,
                        "initial_snapshot_validation": initial,
                        "source_paired_complete": bool(source and source.get("paired_complete")), "arms": {}}
                    for arm in ARMS:
                        source_arm = (source or {}).get("arms", {}).get(arm)
                        row = {"projection_validation": {"passed": False}}
                        if not alignment["passed"] or not initial["passed"] or source_arm is None:
                            row["projection_validation"]["reason"] = "SOURCE_IDENTITY_OR_COMMON_SNAPSHOT_MISMATCH" if source_arm is not None else "MISSING_SOURCE_ARM"
                        else:
                            tick = perf_counter()
                            try:
                                full = restore_state(source_arm["state"], queries, query_name=context["query_name"])
                            except ValueError as error:
                                row["projection_validation"]["reason"] = str(error)
                            else:
                                accounting["source_states_restored_for_projection"] += 1
                                row["projection_validation"]["source_restoration_passed"] = True
                            accounting["source_restoration_for_projection_seconds"] += perf_counter() - tick
                            if row["projection_validation"].get("source_restoration_passed"):
                                tick = perf_counter()
                                try:
                                    projected, projection = project_endpoint(snapshot_lookup[context["context_index"]].state,
                                        full, query_name=context["query_name"], panel=tuple((key[0], tuple(key[1])) for key in context["panel"]))
                                except ValueError as error:
                                    row["projection_validation"]["reason"] = str(error)
                                else:
                                    row.update(projection=projection)
                                    row["projection_validation"]["passed"] = True
                                    projection_counts[arm].update({key: projection[key] for key in
                                        ("original_endpoint_batches", "retained_model_batches", "masked_new_row_count", "masked_observation_batches", "masked_draws")})
                                    projection_work[arm].update(projection["projection_work_counts"])
                                accounting["projection_wall_seconds"] += perf_counter() - tick
                                if row["projection_validation"]["passed"]:
                                    tick = perf_counter()
                                    row["state"] = state_record(projected, context["query_name"])
                                    accounting["projected_state_materialization_seconds"] += perf_counter() - tick
                                    accounting["projected_states_written"] += 1
                                    del projected
                                del full
                        pair["arms"][arm] = row
                    tick = perf_counter()
                    json.dump(pair, writer, separators=(",", ":"), allow_nan=False)
                    writer.write("\n")
                    accounting["projected_stream_write_seconds"] += perf_counter() - tick
                    accounting["projected_pair_records_written"] += 1
                if progress:
                    progress({"stage": "PROJECTION", **repetition, "pairs_written": accounting["projected_pair_records_written"]})
            tick = perf_counter()
            accounting["unexpected_source_first_pass_records"] = sum(1 for _ in reader)
            accounting["source_first_read_seconds"] += perf_counter() - tick
    finally:
        tick = perf_counter()
        writer.close()
        accounting["projected_stream_close_seconds"] += perf_counter() - tick
    # All model interventions are now retained and the gzip footer is closed.
    oracle, exact_closure_counts = None, {}
    if accounting["source_states_restored_for_projection"]:
        case = plan["contexts"][0]["case"]
        tick = perf_counter()
        closure = build_development_closure(horizon=case["horizon"], max_nodes=30_000,
                                           boards={case["name"]: tuple(case["board"])})
        accounting["exact_closure_construction_seconds"] = perf_counter() - tick
        exact_closure_counts = closure.counts
        oracle = ExactOracle.from_closure(closure)
    repetitions = []
    with gzip.open(source_path, "rt", encoding="utf-8") as source_reader, gzip.open(endpoints_path, "rt", encoding="utf-8") as projected_reader:
        for repetition in plan["replicates"]:
            result_rep = {**repetition, "contexts": []}
            for context in plan["contexts"]:
                expected = _expected_pair(repetition, context)
                source = _read_pair(source_reader, accounting, "source_second_read")
                projected = _read_pair(projected_reader, accounting, "projected_reload_read")
                source_alignment, projected_alignment = _alignment(source, expected), _alignment(projected, expected)
                result = {**{key: value for key, value in expected.items() if key not in repetition},
                    "source_paired_complete": bool(source and source.get("paired_complete")),
                    "source_alignment_validation": source_alignment, "projected_alignment_validation": projected_alignment,
                    "initial_snapshot_validation": plan_checks[context["context_index"]], "arms": {}}
                for arm in ARMS:
                    source_arm = (source or {}).get("arms", {}).get(arm)
                    projected_arm = (projected or {}).get("arms", {}).get(arm, {})
                    row = {"projection_validation": projected_arm.get("projection_validation", {"passed": False, "reason": "MISSING_PROJECTED_ARM"}),
                        "full_control_validation": {"passed": False, "reason": "FULL_NOT_EVALUATED"},
                        "evaluation_restoration": {}, "evaluations": {}}
                    if "projection" in projected_arm:
                        row["projection"] = projected_arm["projection"]
                    if source_arm is not None:
                        row.update(source_local={key: value for key, value in source_arm["local"].items() if key not in TRACE_FIELDS},
                            first_request_validation=source_arm["first_request_validation"])
                    aligned = source_alignment["passed"] and projected_alignment["passed"] and plan_checks[context["context_index"]]["passed"]
                    if not aligned:
                        row["projection_validation"] = {"passed": False, "reason": "SOURCE_PROJECTED_OR_PLAN_ALIGNMENT_MISMATCH"}
                    for model, model_row in (("FULL", source_arm), ("PROJECTED", projected_arm)):
                        valid = aligned and model_row is not None and "state" in model_row and oracle is not None
                        tick = perf_counter()
                        if not valid:
                            row["evaluation_restoration"][model] = {"passed": False, "reason": "MODEL_MISSING_OR_SOURCE_MISMATCH"}
                        else:
                            try:
                                state = restore_state(model_row["state"], queries, query_name=context["query_name"])
                            except ValueError as error:
                                row["evaluation_restoration"][model] = {"passed": False, "reason": str(error)}
                            else:
                                row["evaluation_restoration"][model] = {"passed": True}
                                accounting[model.lower() + "_evaluation_states_restored"] += 1
                        accounting[model.lower() + "_evaluation_restoration_seconds"] += perf_counter() - tick
                        if row["evaluation_restoration"][model]["passed"]:
                            tick = perf_counter()
                            target_key = context["target_key"][0], tuple(context["target_key"][1])
                            panel = tuple((key[0], tuple(key[1])) for key in context["panel"])
                            try:
                                evaluation = {"target": _compact_target(evaluate_local_snapshot(state, context["query_name"], target_key, oracle)),
                                    "panel": evaluate_panel(state, context["query_name"], panel, oracle)}
                            except ValueError as error:
                                row["evaluation_restoration"][model].update(passed=False, reason=str(error))
                            else:
                                row["evaluations"][model] = evaluation
                                if model == "FULL":
                                    row["full_control_validation"] = _full_control(evaluation["target"], source_arm["local"])
                            accounting[model.lower() + "_evaluation_seconds"] += perf_counter() - tick
                            del state
                    result["arms"][arm] = row
                result["paired_complete"] = result["source_paired_complete"] and all(
                    row["projection_validation"]["passed"] and row["full_control_validation"]["passed"]
                    and all(model in row["evaluations"] for model in MODELS) for row in result["arms"].values())
                result["status"] = "PAIR_COMPLETE" if result["paired_complete"] else "SOURCE_PROJECTION_OR_CONTROL_INCOMPLETE"
                result_rep["contexts"].append(result)
            result_rep["complete"] = all(row["paired_complete"] for row in result_rep["contexts"])
            result_rep["status"] = "REPETITION_COMPLETE" if result_rep["complete"] else "REPETITION_INCOMPLETE"
            repetitions.append(result_rep)
            if progress:
                progress({"stage": "EVALUATION", **repetition, "complete": result_rep["complete"]})
        tick = perf_counter()
        accounting["unexpected_source_second_pass_records"] = sum(1 for _ in source_reader)
        accounting["source_second_read_seconds"] += perf_counter() - tick
        tick = perf_counter()
        accounting["unexpected_projected_records"] = sum(1 for _ in projected_reader)
        accounting["projected_reload_read_seconds"] += perf_counter() - tick
    report = {"schema": "acfqp.controlled_predictive_projection.v23", "plan": plan,
        "status": "PROJECTION_COMPLETE" if all(row["complete"] for row in repetitions) else "PROJECTION_COMPLETE_WITH_DECLARED_ISSUES",
        "repetitions": repetitions, "complete_repetition_count": sum(row["complete"] for row in repetitions),
        "restoration_validation": restoration_validation, "plan_binding_validation": plan_binding,
        "plan_snapshot_validation": [{"context_index": index, **row} for index, row in plan_checks.items()],
        "source_actual_arm_costs": reference["all_actual_arm_costs"],
        "accounting": {**accounting, "common_preparation": preparation_accounting,
            "projection_counts_by_arm": {arm: dict(counts) for arm, counts in projection_counts.items()},
            "projection_work_counts_by_arm": {arm: dict(counts) for arm, counts in projection_work.items()},
            "source_physical_batches": reference["accounting"]["local_physical_batches"],
            "source_physical_draws": reference["accounting"]["local_physical_draws"],
            "new_provider_calls": 0, "new_physical_draws": 0,
            "source_endpoint_artifact_bytes": source_path.stat().st_size, "projected_endpoint_artifact_bytes": endpoints_path.stat().st_size,
            "exact_closure_counts": exact_closure_counts, "oracle": oracle.accounting() if oracle is not None else None},
        "all_projected_endpoints_closed_before_oracle": True, "new_provider_calls": 0, "new_physical_draws": 0,
        "projected_endpoint_artifact": str(endpoints_path),
        "elapsed_seconds_before_report_serialization": perf_counter() - started_all,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Fixed initial-row information projection of retained V22 acquisitions. Retained model batches are information volume, not refunded acquisition costs. Source acquisition is paid in full; V23 calls no provider. Source read passes, projection and evaluation are audit work; nested stage timings are not additive."}
    tick = perf_counter()
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, separators=(",", ":"), allow_nan=False)
        handle.write("\n")
    return report, {"report_serialization_seconds": perf_counter() - tick, "report_bytes": output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--endpoints", type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error("the frozen V23 protocol and plan must exist before projection")
    report, serialization = run_projection(args.plan, args.endpoints, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({"status": report["status"], "complete_repetition_count": report["complete_repetition_count"],
        "output": str(args.output), **serialization}), flush=True)


if __name__ == "__main__":
    main()
