#!/usr/bin/env python3
"""Run the fixed V4 matched development comparison to a fresh compact report."""

import argparse
import json
from pathlib import Path

from acfqp.science.controlled_predictive_comparison_v4 import run_comparison_v4


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    report = run_comparison_v4(progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, separators=(",", ":"), sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve())}), flush=True)


if __name__ == "__main__":
    main()
