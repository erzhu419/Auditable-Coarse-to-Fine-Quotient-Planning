#!/usr/bin/env python3
"""Evaluate all declared public challenges and write one compact JSON artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from acfqp.science.controlled_predictive_comparison_v2 import SAMPLE_SEEDS, run_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--max-nodes", type=int, default=30_000)
    parser.add_argument("--samples-per-row", type=int, default=64)
    parser.add_argument("--sample-seeds", type=int, nargs="+", default=SAMPLE_SEEDS)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"output already exists: {arguments.output}")
    result = run_comparison(horizon=arguments.horizon, max_nodes=arguments.max_nodes,
        samples_per_row=arguments.samples_per_row, sample_seeds=arguments.sample_seeds,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "output": str(arguments.output.resolve())}), flush=True)


if __name__ == "__main__":
    main()
