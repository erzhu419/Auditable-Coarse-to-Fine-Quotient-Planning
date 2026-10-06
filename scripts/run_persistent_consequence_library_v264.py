#!/usr/bin/env python3
"""Run the predeclared fresh-stream replication of V263."""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

from acfqp.science.persistent_consequence_library_v263 import run_development

SEEDS = (264401, 264402, 264403, 264404)


def _summarize(records):
    summary = {}
    for arm in ("RESET", "GLOBAL", "LIBRARY"):
        counts = []
        regrets = []
        for record in records:
            rows = record["arms"][arm]
            counts.append(sum(item["policy_correct"] for row in rows for item in row["metrics"].values()))
            regrets.append(sum(Fraction(item["exact_value_regret"])
                               for row in rows for item in row["metrics"].values()))
        summary[arm] = {
            "policy_correct_counts": counts,
            "mean_policy_correct": sum(counts) / len(counts),
            "exact_regrets": [str(value) for value in regrets],
            "mean_exact_regret": str(sum(regrets, Fraction(0)) / len(regrets)),
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    records = [{"seed": seed, **run_development(seed=seed)} for seed in SEEDS]
    result = {
        "schema": "acfqp.persistent_consequence_library_replication.v264",
        "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "seeds": list(SEEDS),
        "records": records,
        "summary": _summarize(records),
        "limitations": [
            "Four finite lifecycles remain a development replication, not a general-learning or confidence claim.",
            "The route grammar, query set and module procedure are supplied and finite.",
            "V263 and all adverse fresh streams remain retained; the original Gate is unchanged.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False, default=str)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
