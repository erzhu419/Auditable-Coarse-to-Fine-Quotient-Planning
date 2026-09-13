#!/usr/bin/env python3
"""Run the frozen V20 variance-based resampling comparison and retain lossless gzip JSON."""

import argparse
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_cohort_v7 import V7Case
from acfqp.science.controlled_predictive_comparison_v20 import run_comparison_v20

DEFAULT_OUTPUT = Path("reports/controlled_predictive_variance_v20.json.gz")
DEFAULT_ROSTER = Path("reports/controlled_predictive_cohort_roster_v20.json")
PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_VARIANCE_ALLOCATION_V20.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-roster", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    if not PROTOCOL.is_file() or not args.cohort_roster.is_file():
        parser.error("the frozen V20 protocol and input roster must exist before execution")
    roster = json.loads(args.cohort_roster.read_text(encoding="utf-8"))
    cases = tuple(V7Case(**{**row["case"], "board": tuple(row["case"]["board"])}) for row in roster["cases"])
    report = run_comparison_v20(cases=cases, cohort_roster=roster,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    opener = gzip.open if args.output.suffix == ".gz" else open
    with opener(args.output, "xt", encoding="utf-8") as handle:
        json.dump(report, handle, separators=(",", ":"), sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve()),
        "result_serialization_seconds": perf_counter() - started,
        "result_bytes": args.output.stat().st_size, "lossless_gzip": args.output.suffix == ".gz"}), flush=True)


if __name__ == "__main__":
    main()
