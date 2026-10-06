#!/usr/bin/env python3
"""Replay immutable V278 prefixes without sampling new outcomes."""

import argparse
import gzip
import json
from pathlib import Path

from acfqp.science.evidence_weighted_prefix_v279 import run_diagnostic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    traces, summary = args.output / "changes.json.gz", args.output / "summary.json"
    if traces.exists() or summary.exists():
        parser.error(f"results already exist in {args.output}")
    result = run_diagnostic(args.input)
    with gzip.open(traces, "xt", encoding="utf-8") as handle:
        json.dump(result, handle, separators=(",", ":"), allow_nan=False)
        handle.write("\n")
    with summary.open("x", encoding="utf-8") as handle:
        json.dump({k: v for k, v in result.items() if k != "records"}, handle,
                  indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "summary": str(summary.resolve())}), flush=True)


if __name__ == "__main__":
    main()
