#!/usr/bin/env python3
"""Execute declared queries from a saved partial policy, including its fallback."""
import argparse
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_partial_io_v12 import restore_policy_payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--example-root", action="store_true")
    inputs.add_argument("--board", nargs=16, type=int)
    parser.add_argument("--remaining-horizon", type=int)
    parser.add_argument("--query", help="Declared query name; omitted means all declared queries")
    args = parser.parse_args()
    started = perf_counter()
    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    policy = restore_policy_payload(payload)
    load_seconds = perf_counter() - started
    if args.example_root:
        root = payload["example_input"]
        key = (root["remaining_horizon"], tuple(root["board"]))
    else:
        if args.remaining_horizon is None:
            parser.error("--board requires --remaining-horizon")
        key = (args.remaining_horizon, tuple(args.board))
    if args.query is not None and args.query not in payload["queries"]:
        parser.error("only declared queries are available in this partial-policy artifact")
    names = (args.query,) if args.query else tuple(payload["queries"])
    started = perf_counter()
    actions = {name: policy.action(key, name) for name in names}
    execution_seconds = perf_counter() - started
    result = {
        "schema": "controlled_predictive_partial_execution_v12",
        "artifact_path": str(args.artifact.resolve()),
        "input": {"remaining_horizon": key[0], "board": list(key[1])},
        "query_actions": actions,
        "queries": {name: payload["queries"][name] for name in names},
        "work_counts": dict(policy.work_counts),
        "load_seconds": load_seconds, "execution_seconds": execution_seconds,
        "fallback_seconds": policy.fallback_seconds,
        "stochastic_observations_requested": 0,
        "scope": "Declared policy execution; no new-query replanning or exact audit",
    }
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
