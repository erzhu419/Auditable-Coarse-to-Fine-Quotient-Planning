#!/usr/bin/env python3
"""Run fixed V277 cohort, saving compressed traces and a compact receipt."""

import argparse
import gzip
import json
from pathlib import Path

from acfqp.science.online_factor_confirmation_v277 import run_replication


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new run directory")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    traces = args.output / "records.json.gz"
    summary = args.output / "summary.json"
    if traces.exists() or summary.exists():
        parser.error(f"results already exist in {args.output}")
    result = run_replication()
    with gzip.open(traces, "xt", encoding="utf-8") as handle:
        json.dump(result, handle, separators=(",", ":"), allow_nan=False)
        handle.write("\n")
    small = {key: value for key, value in result.items() if key != "records"}
    with summary.open("x", encoding="utf-8") as handle:
        json.dump(small, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "confirmation": result["confirmation"], "summary": str(summary.resolve())}), flush=True)


if __name__ == "__main__":
    main()
