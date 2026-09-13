#!/usr/bin/env python3
"""Run the frozen V8 six-arm primary and mechanism-family holdout comparison."""

import argparse
import json
from pathlib import Path

from acfqp.science.controlled_predictive_cohort_v7 import V7Case
from acfqp.science.controlled_predictive_comparison_v8 import run_comparison_v8


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
    report = run_comparison_v8(cases=cases, cohort_roster=roster,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, separators=(",", ":"), sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve())}), flush=True)


if __name__ == "__main__":
    main()
