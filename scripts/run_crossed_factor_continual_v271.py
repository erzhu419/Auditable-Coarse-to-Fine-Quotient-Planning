#!/usr/bin/env python3
"""Run the V271 continual crossed-factor diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from acfqp.science.crossed_factor_continual_v271 import run_replication


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    result = run_replication()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False, default=str)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
