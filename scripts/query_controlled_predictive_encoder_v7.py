#!/usr/bin/env python3
"""Encode a board and plan a numeric query using a saved V7 rule model."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_encoder_io_v7 import restore_artifact_payload
from acfqp.science.controlled_predictive_quotient_v1 import Query, plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--board", nargs=16, type=int)
    inputs.add_argument("--example-root", action="store_true")
    parser.add_argument("--remaining-horizon", type=int)
    parser.add_argument("--reward-weight", type=float, default=1.0)
    parser.add_argument("--failure-penalty", type=float, default=0.3)
    parser.add_argument("--goal-bonus", type=float, default=0.2)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    started = perf_counter()
    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    encoder, model, code_to_cell = restore_artifact_payload(payload)
    load_seconds = perf_counter() - started
    if args.example_root:
        board = tuple(payload["example_input"]["board"])
        horizon = payload["example_input"]["remaining_horizon"]
        if args.remaining_horizon is not None:
            horizon = args.remaining_horizon
    else:
        board = tuple(args.board)
        horizon = args.remaining_horizon
        if horizon is None:
            parser.error("--board requires --remaining-horizon")
    started = perf_counter()
    code = encoder.encode(board, horizon)
    encoding_seconds = perf_counter() - started
    if code not in code_to_cell:
        parser.error("encoded board is outside this artifact's represented cell codes")
    cell = code_to_cell[code]
    query = Query(args.reward_weight, args.failure_penalty, args.goal_bonus)
    started = perf_counter()
    solution = plan(model, query)
    planning_seconds = perf_counter() - started
    result = {
        "artifact_path": str(args.artifact.resolve()),
        "input": {"board": board, "remaining_horizon": horizon},
        "code": code, "resolved_cell": cell,
        "query": asdict(query), "action": solution.policy.get(cell),
        "predicted_value": solution.values[cell],
        "policy_count": len(solution.policy), "planning_counts": solution.counts,
        "load_seconds": load_seconds, "encoding_seconds": encoding_seconds,
        "planning_seconds": planning_seconds,
        "exact_model_or_state_lookup_used": False,
        "query_result_scope": "portable execution smoke test; no independent exact audit",
    }
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
