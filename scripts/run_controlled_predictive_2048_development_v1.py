#!/usr/bin/env python3
"""Run the local finite public-board development slice and write one small JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from acfqp.science.controlled_predictive_2048_v1 import run_development


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--max-nodes", type=int, default=30_000)
    parser.add_argument("--samples-per-row", type=int, default=64)
    parser.add_argument("--seed", type=int, default=73129)
    parser.add_argument("--reward-tolerance", type=float, default=0.01)
    parser.add_argument("--tv-tolerance", type=float, default=0.2)
    arguments = parser.parse_args()
    result = run_development(
        horizon=arguments.horizon,
        max_nodes=arguments.max_nodes,
        samples_per_row=arguments.samples_per_row,
        seed=arguments.seed,
        reward_tolerance=arguments.reward_tolerance,
        tv_tolerance=arguments.tv_tolerance,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "output": str(arguments.output.resolve())}))


if __name__ == "__main__":
    main()
