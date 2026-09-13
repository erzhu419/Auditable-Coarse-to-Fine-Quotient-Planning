#!/usr/bin/env python3
"""Run the frozen V14 mass-bound/history-execution comparison from its input roster."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_cohort_v7 import V7Case
from acfqp.science.controlled_predictive_comparison_v14 import run_comparison_v14


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-roster", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    roster = json.loads(args.cohort_roster.read_text(encoding="utf-8"))
    cases = tuple(V7Case(**{**row["case"], "board": tuple(row["case"]["board"])})
                  for row in roster["cases"])
    report = run_comparison_v14(cases=cases, cohort_roster=roster,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, separators=(",", ":"), sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve()),
        "result_serialization_seconds": perf_counter() - started,
        "result_bytes": args.output.stat().st_size}), flush=True)


if __name__ == "__main__":
    main()
