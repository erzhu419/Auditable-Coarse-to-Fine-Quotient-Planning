#!/usr/bin/env python3
"""Run the fixed refinement development cohort once to a fresh local report."""

import argparse
import json
from pathlib import Path

from acfqp.science.controlled_predictive_comparison_v3 import run_refinement_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"output already exists: {arguments.output}")
    result = run_refinement_comparison(progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "output": str(arguments.output.resolve())}), flush=True)


if __name__ == "__main__":
    main()
