#!/usr/bin/env python3
"""Plan a new query using only a saved development model's action dynamics."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_model_io_v3 import load_compiled
from acfqp.science.controlled_predictive_quotient_v1 import Query, evaluate_compiled_policy, plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reward-weight", type=float, default=1.0)
    parser.add_argument("--failure-penalty", type=float, default=0.0)
    parser.add_argument("--goal-bonus", type=float, default=0.0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    started = perf_counter()
    model = load_compiled(args.model)
    load_seconds = perf_counter() - started
    query = Query(args.reward_weight, args.failure_penalty, args.goal_bonus)
    started = perf_counter()
    solution = plan(model, query)
    planning_seconds = perf_counter() - started
    started = perf_counter()
    forecast = evaluate_compiled_policy(model, solution, query)
    forecast_seconds = perf_counter() - started
    result = {
        "model_path": str(args.model.resolve()), "query": asdict(query),
        "root_actions": {root: solution.policy.get(root) for root in model.roots},
        "root_metrics": forecast.root_metrics, "planning_counts": solution.counts,
        "forecast_counts": forecast.counts, "load_seconds": load_seconds,
        "planning_seconds": planning_seconds, "forecast_seconds": forecast_seconds,
    }
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
