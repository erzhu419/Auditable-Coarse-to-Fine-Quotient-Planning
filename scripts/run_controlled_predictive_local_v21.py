#!/usr/bin/env python3
"""Run the frozen common-snapshot, fixed-batch local allocation comparison."""

import argparse
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_local_v21 import run_local_allocation, evaluate_local_snapshot, evaluate_panel
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_snapshot_v21 import reconstruct_common_snapshots, common_record, state_record

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_LOCAL_ALLOCATION_V21.md")
DEFAULT_INPUT = Path("reports/controlled_predictive_variance_v20.json.gz")
DEFAULT_ROSTER = Path("reports/controlled_predictive_cohort_roster_v21.json")
DEFAULT_COMMON = Path("reports/controlled_predictive_common_snapshots_v21.json.gz")
DEFAULT_ENDPOINTS = Path("reports/controlled_predictive_local_endpoints_v21.json.gz")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_local_v21.json")
TRACE_FIELDS = ("requested_batches", "observed_batches", "gap_assessments")


def _write_gzip(path, payload):
    started = perf_counter()
    with gzip.open(path, "xt", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"), allow_nan=False)
        handle.write("\n")
    return {"seconds": perf_counter() - started, "bytes": path.stat().st_size}


def validate_source_prefix(local, source, request_index):
    """Preserve the original local process until its original stopping point."""
    expected = {field: source[field][request_index:] for field in TRACE_FIELDS}
    checks = {field: local[field][:len(rows)] == rows for field, rows in expected.items()}
    checks["first_request"] = bool(expected["requested_batches"]) and local["requested_batches"][:1] == expected["requested_batches"][:1]
    original_stop = next((index for index, row in enumerate(expected["gap_assessments"]) if row["separated"]), None)
    if original_stop is not None:
        checks["first_original_stop_index"] = local["first_original_stop_index"] == original_stop
    return {"passed": all(checks.values()), "checks": checks,
        "source_remaining_request_count": len(expected["requested_batches"]),
        "source_remaining_diagnostic_count": len(expected["gap_assessments"]),
        "source_gap_stop_index": original_stop,
        "intervention_batches_after_source_stop": max(0, local["completed_batches"] - len(expected["requested_batches"]))}


def run_comparison(input_path, roster_path, common_path, endpoints_path, output_path):
    started_all = perf_counter()
    for path in (common_path, endpoints_path, output_path):
        if path.exists():
            raise FileExistsError(f"V21 output already exists: {path}")
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    started = perf_counter()
    with gzip.open(input_path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    raw_seconds = perf_counter() - started
    snapshots, records, validation, accounting = reconstruct_common_snapshots(payload, roster)
    del payload
    accounting["raw_result_read_seconds"] = raw_seconds
    started = perf_counter()
    initial_records = [common_record(snapshot) for snapshot in snapshots]
    accounting["common_snapshot_materialization_seconds"] = perf_counter() - started
    accounting["common_snapshot_serialization"] = _write_gzip(common_path, {
        "schema": "acfqp.controlled_predictive_common_snapshots.v21", "cohort_roster": roster,
        "identity_statuses": records, "snapshots": initial_records, "validation": validation,
        "reconstruction_accounting": accounting, "local_acquisition_started": False, "oracle_constructed": False})
    common_lookup = {row.identity["context_index"]: row for row in snapshots}
    final_states, endpoint_records, results = {}, [], []
    for record in records:
        identity = record["identity"]
        index = identity["context_index"]
        if record["status"] != "READY":
            results.append(record)
            continue
        snapshot = common_lookup[index]
        order = ("CACHED", "VARIANCE") if index % 2 == 0 else ("VARIANCE", "CACHED")
        result = {"identity": identity, "target_key": [snapshot.target_key[0], list(snapshot.target_key[1])],
            "panel": [[key[0], list(key[1])] for key in snapshot.panel],
            "requested_batch_count": snapshot.requested_batch_count, "initial_batches": snapshot.state.spent_batches,
            "request_index": snapshot.request_index, "run_order": list(order), "arms": {}}
        endpoint = {key: value for key, value in result.items() if key != "arms"}
        endpoint["arms"] = {}
        states = {}
        for arm in order:
            provider = BatchRowSampleProvider(identity["sample_seed"])
            state, local = run_local_allocation(snapshot.state, arm, provider, snapshot.query_name,
                snapshot.target_key, requested_batches=snapshot.requested_batch_count)
            states[arm] = state
            started = perf_counter()
            source_validation = validate_source_prefix(local, snapshot.source_nodes[arm], snapshot.request_index)
            accounting["source_prefix_validation_seconds"] = accounting.get("source_prefix_validation_seconds", 0.0) + perf_counter() - started
            result["arms"][arm] = {"local": {key: value for key, value in local.items() if key not in TRACE_FIELDS},
                                  "source_validation": source_validation}
            started = perf_counter()
            endpoint["arms"][arm] = {"state": state_record(state, snapshot.query_name), "local": local,
                                      "source_validation": source_validation}
            accounting["endpoint_materialization_seconds"] = accounting.get("endpoint_materialization_seconds", 0.0) + perf_counter() - started
        passed = all(row["source_validation"]["passed"] for row in result["arms"].values())
        complete = all(row["local"]["completed_fixed_budget"] for row in result["arms"].values())
        result["paired_complete"] = passed and complete
        result["status"] = "SOURCE_VALIDATION_MISMATCH" if not passed else "LOCAL_COMPLETE" if complete else "FIXED_BUDGET_INCOMPLETE"
        endpoint.update(status=result["status"], paired_complete=result["paired_complete"])
        final_states[index] = states
        endpoint_records.append(endpoint)
        results.append(result)
    accounting["endpoint_serialization"] = _write_gzip(endpoints_path, {
        "schema": "acfqp.controlled_predictive_local_endpoints.v21", "cohort_roster": roster,
        "contexts": endpoint_records, "excluded_contexts": [row for row in results if "arms" not in row],
        "oracle_constructed": False, "common_snapshot_artifact": str(common_path)})
    # Both empirical artifacts are complete before the first exact value is read.
    if snapshots:
        case = roster["contexts"][0]["case"]
        started = perf_counter()
        closure = build_development_closure(horizon=case["horizon"], max_nodes=30_000,
                                           boards={case["name"]: tuple(case["board"])})
        accounting["exact_closure_construction_seconds"] = perf_counter() - started
        accounting["exact_closure_counts"] = closure.counts
        oracle = ExactOracle.from_closure(closure)
        started = perf_counter()
        for result in results:
            if "arms" not in result:
                continue
            index = result["identity"]["context_index"]
            snapshot = common_lookup[index]
            def evaluate(state):
                return {"target": evaluate_local_snapshot(state, snapshot.query_name, snapshot.target_key, oracle),
                        "panel": evaluate_panel(state, snapshot.query_name, snapshot.panel, oracle)}
            result["initial_evaluation"] = evaluate(snapshot.state)
            for arm, state in final_states[index].items():
                result["arms"][arm]["evaluation"] = evaluate(state)
        accounting["all_evaluation_wall_seconds"] = perf_counter() - started
        accounting["oracle"] = oracle.accounting()
    locals_ = [arm["local"] for row in results if "arms" in row for arm in row["arms"].values()]
    accounting["local_physical_batches"] = sum(row["completed_batches"] for row in locals_)
    accounting["local_physical_draws"] = sum(row["actual_draws"] for row in locals_)
    accounting["total_physical_draws_including_warm_regeneration"] = accounting["warm_physical_draws"] + accounting["local_physical_draws"]
    accounting["local_allocation_wall_seconds"] = math.fsum(row["accounting"]["whole_run_seconds"] for row in locals_)
    report = {"schema": "acfqp.controlled_predictive_local.v21", "cohort_roster": roster,
        "status": "LOCAL_COMPLETE" if all(row["status"] == "LOCAL_COMPLETE" for row in results) else "LOCAL_COMPLETE_WITH_DECLARED_ISSUES",
        "contexts": results, "context_count": len(results), "paired_complete_count": sum(row.get("paired_complete", False) for row in results),
        "reconstruction_validation": validation, "accounting": accounting,
        "common_snapshots_persisted_before_local_acquisition": True, "all_endpoints_persisted_before_oracle": True,
        "source_result": str(input_path), "common_snapshot_artifact": str(common_path), "endpoint_artifact": str(endpoints_path),
        "elapsed_seconds_before_report_serialization": perf_counter() - started_all,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False, "deferred_v2_24_case_cohort_executed": False,
        "scope": "Posthoc common-state local allocation intervention with original decision quota remaining and gap stopping disabled in both arms. Target and fixed-panel optimal-continuation action regret are not complete adaptive policy values. All warm and local provider draws are physical work, including reused source streams; no independent-confirmation claim. Stage timings nested inside reconstruction/local/evaluation walls are not added twice."}
    started = perf_counter()
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return report, {"report_serialization_seconds": perf_counter() - started, "report_bytes": output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--cohort-roster", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--common-snapshots", type=Path, default=DEFAULT_COMMON)
    parser.add_argument("--endpoints", type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.cohort_roster.is_file():
        parser.error("the frozen V21 protocol and roster must exist before reconstruction")
    report, serialization = run_comparison(args.input, args.cohort_roster, args.common_snapshots, args.endpoints, args.output)
    print(json.dumps({"status": report["status"], "context_count": report["context_count"],
        "paired_complete_count": report["paired_complete_count"], "output": str(args.output), **serialization}), flush=True)


if __name__ == "__main__":
    main()
