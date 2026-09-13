#!/usr/bin/env python3
"""Run fixed exposed diagnosis and nested sampling curve to a fresh compact JSON."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_sampling_diagnosis_v4 import diagnose_original_exposed, run_sampling_curve


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v3-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    started = perf_counter()
    with args.v3_report.open(encoding="utf-8") as handle:
        prior = json.load(handle)
    diagnosis = diagnose_original_exposed(prior)
    print(json.dumps({"stage": "original_exposed_diagnosis", "status": "COMPLETE"}), flush=True)
    curve = run_sampling_curve(progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    result = {"schema": "controlled_predictive_sampling_diagnosis_v4", "status": curve["status"],
              "source_v3_report": str(args.v3_report), "original_exposed_diagnosis": diagnosis,
              "nested_sampling_curve": curve, "elapsed_seconds": perf_counter() - started}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, separators=(",", ":"), sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "output": str(args.output.resolve()),
                      "bytes": args.output.stat().st_size}), flush=True)


if __name__ == "__main__":
    main()
