#!/usr/bin/env python3
"""Run frozen V278 and retain compressed traces plus a small receipt."""

import argparse
import gzip
import json
from pathlib import Path

from acfqp.science.query_relevant_coverage_v278 import run_replication


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    traces, summary = args.output / "records.json.gz", args.output / "summary.json"
    if traces.exists() or summary.exists():
        parser.error(f"results already exist in {args.output}")
    result = run_replication()
    with gzip.open(traces, "xt", encoding="utf-8") as handle:
        json.dump(result, handle, separators=(",", ":"), allow_nan=False)
        handle.write("\n")
    with summary.open("x", encoding="utf-8") as handle:
        json.dump({key: value for key, value in result.items() if key != "records"}, handle,
                  indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "primary_result": result["primary_result"], "summary": str(summary.resolve())}), flush=True)


if __name__ == "__main__":
    main()
