#!/usr/bin/env python3
"""Replay all declared action histories in a retained V13 policy artifact."""
import argparse
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_history_io_v13 import replay_all_histories


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    started = perf_counter()
    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    result = replay_all_histories(payload)
    result["load_and_replay_seconds"] = perf_counter() - started
    result["artifact_path"] = str(args.artifact.resolve())
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key != "decisions"}, allow_nan=False))


if __name__ == "__main__":
    main()
