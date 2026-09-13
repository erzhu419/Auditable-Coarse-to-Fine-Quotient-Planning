#!/usr/bin/env python3
"""Diagnose the frozen V19 snapshot roster from retained V18 observations."""

import argparse
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle, TERMS, evaluate_snapshot
from acfqp.science.controlled_predictive_snapshot_v19 import reconstruct_snapshots, snapshot_record

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_DECOMPOSITION_V19.md")
DEFAULT_INPUT = Path("reports/controlled_predictive_score_cache_v18.json.gz")
DEFAULT_ROSTER = Path("reports/controlled_predictive_cohort_roster_v19.json")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_decomposition_v19.json")
DEFAULT_SNAPSHOTS = Path("reports/controlled_predictive_snapshots_v19.json.gz")


def _last_batch_effect(before, after):
    observation = after["last_observation"]
    pair = observation["row_key"]
    target = after["decomposition"]["target_key"]
    location = ("TARGET_LEFT_RIGHT" if pair[0] == target and pair[1] in ("LEFT", "RIGHT")
                else "OTHER_TARGET_ACTION" if pair[0] == target else "CONTINUATION_STATE")
    return {"context_index": after["identity"]["context_index"], "method": after["identity"]["method"],
        "last_observation_row": pair, "last_observation_batch_index": observation.get("batch_index", 0),
        "last_batch_location": location,
        "selected_action_before": before["decomposition"]["empirical"]["selected_action"],
        "selected_action_after": after["decomposition"]["empirical"]["selected_action"],
        "actions_after_minus_before": {action: {term: after["decomposition"]["actions"][action][term]
            - before["decomposition"]["actions"][action][term] for term in TERMS} for action in ("LEFT", "RIGHT")},
        "left_minus_right_after_minus_before": {term: after["decomposition"]["left_minus_right"][term]
            - before["decomposition"]["left_minus_right"][term] for term in TERMS}}


def run_decomposition(input_path, roster_path, output_path, snapshots_path):
    """Persist every empirical snapshot before constructing the exact evaluator."""
    started_all = perf_counter()
    for path in (output_path, snapshots_path):
        if path.exists():
            raise FileExistsError(f"V19 output already exists: {path}")
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    started = perf_counter()
    with gzip.open(input_path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    raw_read_seconds = perf_counter() - started
    frozen, validation, accounting = reconstruct_snapshots(payload, roster)
    del payload
    accounting["raw_result_read_seconds"] = raw_read_seconds
    started = perf_counter()
    records = [snapshot_record(snapshot) for snapshot in frozen]
    accounting["snapshot_materialization_seconds"] = perf_counter() - started
    snapshot_payload = {"schema": "acfqp.controlled_predictive_snapshots.v19",
        "source_result": str(input_path), "cohort_roster": roster, "snapshots": records,
        "validation": validation, "reconstruction_accounting": accounting,
        "exact_evaluator_constructed": False, "new_independent_statistical_draws": 0}
    started = perf_counter()
    with gzip.open(snapshots_path, "xt", encoding="utf-8") as handle:
        json.dump(snapshot_payload, handle, separators=(",", ":"), allow_nan=False)
        handle.write("\n")
    accounting["snapshot_serialization_seconds"] = perf_counter() - started
    accounting["snapshot_artifact_bytes"] = snapshots_path.stat().st_size
    # The completed snapshot artifact is now independent of evaluator truth.
    case = roster["contexts"][0]["case"]
    started = perf_counter()
    closure = build_development_closure(horizon=case["horizon"], max_nodes=30_000,
                                        boards={case["name"]: tuple(case["board"])})
    accounting["exact_closure_construction_seconds"] = perf_counter() - started
    accounting["exact_closure_counts"] = closure.counts
    oracle = ExactOracle.from_closure(closure)
    results = []
    for snapshot in frozen:
        result = evaluate_snapshot(snapshot.state, snapshot.query_name, snapshot.target_key, oracle)
        results.append({"identity": snapshot.identity, "last_observation": snapshot.last_observation,
                        "decomposition": result})
    accounting["oracle"] = oracle.accounting()
    accounting["snapshot_evaluation_seconds"] = math.fsum(row["decomposition"]["accounting"]["whole_evaluation_seconds"] for row in results)
    accounting["snapshot_evaluation_clone_and_solve_seconds"] = math.fsum(row["decomposition"]["accounting"]["snapshot_clone_and_solve_seconds"] for row in results)
    accounting["decomposition_seconds"] = math.fsum(row["decomposition"]["accounting"]["decomposition_seconds"] for row in results)
    effects = [_last_batch_effect(results[index], results[index + 1]) for index in range(0, len(results), 2)]
    report = {"schema": "acfqp.controlled_predictive_decomposition.v19",
        "status": "DIAGNOSTIC_COMPLETE" if all(row["decomposition"]["identities_pass"] for row in results) else "IDENTITY_CHECK_FAILED",
        "source_result": str(input_path), "snapshot_artifact": str(snapshots_path), "cohort_roster": roster,
        "snapshot_count": len(results), "snapshots": results, "last_batch_effects": effects,
        "reconstruction_validation": validation, "all_snapshots_persisted_before_oracle": True,
        "accounting": accounting, "elapsed_seconds_before_report_serialization": perf_counter() - started_all,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "deferred_v2_24_case_cohort_executed": False,
        "scope": "Posthoc decomposition of the frozen observed V18 models. Warm streams are regenerated audit work; suffix batches are retained observations, with no new independent draws. Reconstruction wall time includes its stage times; evaluator wall time includes clone, oracle and decomposition times. Local frozen-policy effects are not adaptive whole-policy treatment effects."}
    started = perf_counter()
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return report, {"report_serialization_seconds": perf_counter() - started,
                    "report_bytes": output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--cohort-roster", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--snapshots", type=Path, default=DEFAULT_SNAPSHOTS)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.cohort_roster.is_file():
        parser.error("the frozen V19 protocol and roster must exist before reconstruction")
    report, serialization = run_decomposition(args.input, args.cohort_roster, args.output, args.snapshots)
    print(json.dumps({"status": report["status"], "snapshot_count": report["snapshot_count"],
        "output": str(args.output), "snapshots": str(args.snapshots), **serialization}), flush=True)


if __name__ == "__main__":
    main()
