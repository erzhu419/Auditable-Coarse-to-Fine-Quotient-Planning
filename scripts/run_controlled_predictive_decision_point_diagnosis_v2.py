#!/usr/bin/env python3
"""Diagnose reached conflicts in one exposed source, then compare every witness once."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from acfqp.science.controlled_predictive_comparison_v2 import run_comparison
from acfqp.science.controlled_predictive_decision_point_diagnosis_v2 import extract_decision_point_cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--discovery-report", type=Path, default=Path("reports/challenge_generator_discovery_v2.json"))
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"output already exists: {arguments.output}")
    discovery = json.loads(arguments.discovery_report.read_text(encoding="utf-8"))
    cases, provenance = extract_decision_point_cases(discovery)
    provenance["discovery_report_path"] = str(arguments.discovery_report.resolve())
    print(json.dumps({"stage": "EXACT_DECISION_POINT_EXTRACTION_COMPLETE",
        "inspected_successors": provenance["inspected_successor_count"],
        "retained_conflict_successors": len(cases)}, sort_keys=True), flush=True)
    comparison = run_comparison(cases=cases, horizon=2,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True)) if cases else None
    result = {
        "schema": "acfqp.controlled_predictive_decision_point_diagnosis.v2",
        "status": "EXPOSED_MECHANISM_DIAGNOSIS_COMPLETE" if cases else "NO_REACHED_DECISION_CONFLICT",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "witness_provenance": provenance, "comparison": comparison,
        "final_challenge_cohort_executed": False,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "output": str(arguments.output.resolve())}), flush=True)


if __name__ == "__main__":
    main()
