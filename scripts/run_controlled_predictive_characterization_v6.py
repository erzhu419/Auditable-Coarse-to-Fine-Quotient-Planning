#!/usr/bin/env python3
"""Characterize every case in the frozen V6 exposure roster exactly once."""

import argparse
import json
from pathlib import Path

from acfqp.science.controlled_predictive_challenges_v6 import V6Case
from acfqp.science.controlled_predictive_characterization_v6 import run_characterization_v6


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-roster", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    roster = json.loads(args.cohort_roster.read_text(encoding="utf-8"))
    cases = tuple(V6Case(**{**row["case"], "board": tuple(row["case"]["board"])}) for row in roster["cases"])
    report = run_characterization_v6(cases=cases, cohort_roster=roster,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, separators=(",", ":"), sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve())}), flush=True)


if __name__ == "__main__":
    main()
