#!/usr/bin/env python3
"""Replay all V280 relevant histories and retain V281 contribution costs."""

import argparse
import gzip
import json
from pathlib import Path
from time import process_time, perf_counter

from acfqp.science import contribution_replay_v282 as core


def run(online_input, natural_summary, output):
    began, cpu = perf_counter(), process_time()
    with gzip.open(online_input, "rt", encoding="utf-8") as handle:
        retained = json.load(handle)
    if (retained["schema"] != "acfqp.net_learning_campaign.v280"
            or retained["settings"]["source_seeds"] != list(core.online.SOURCE_SEEDS)
            or retained["settings"]["seeds"] != list(core.online.SEEDS)
            or [(record["source_seed"], record["seed"]) for record in retained["records"]]
                != list(zip(core.online.SOURCE_SEEDS, core.online.SEEDS))):
        raise ValueError("the complete frozen 128-source V280 cohort is required")
    natural = json.loads(Path(natural_summary).read_text(encoding="utf-8"))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    changed_path, summary_path = output/"changed_predictions.jsonl.gz", output/"summary.json"
    if changed_path.exists() or summary_path.exists():
        raise ValueError("V282 output already exists")
    records, changed_count = [], 0
    source_contexts = core.route._contexts(core.online.SOURCE_PAIRS, "source")
    with gzip.open(changed_path, "xt", encoding="utf-8") as handle:
        for original in retained["records"]:
            # Reconstruct the original immutable seeded corpus; these are replay
            # reads, never additional acquired source or target observations.
            streams = {context.context_id: core.route._stream(context, original["source_seed"]+index)
                       for index, context in enumerate(source_contexts)}
            result = core.replay_history(original, source_contexts, streams)
            for row in result.pop("changed_prediction_rows"):
                json.dump(dict(source_seed=original["source_seed"], seed=original["seed"], **row),
                          handle, separators=(",", ":"), allow_nan=False)
                handle.write("\n")
                changed_count += 1
            records.append(result)
            print(f"replayed {len(records)}/128 source_seed={original['source_seed']}", flush=True)
    summary = dict(schema="acfqp.contribution_replay.v282", status="DIAGNOSTIC_COMPLETE",
        scientific_gate="NOT_A_FORMAL_GATE", online_input=str(Path(online_input).resolve()),
        natural_summary=str(Path(natural_summary).resolve()),
        settings=dict(history=core.HISTORY_ARM, variants=core.VARIANTS,
            endpoint="fixed-history recommendation regret before each row's current events",
            contribution_scope="source-factor transfer, parameter update and structure update diagnostics",
            source_factor_scope="source and learned factor grouping together versus full-context local history"),
        accounting=dict(new_source_observations=0, new_target_observations=0,
            reconstructed_source_rows=len(records)*len(core.online.SOURCE_PAIRS)*len(core.online.OPERATORS)
                                      *(core.online.SOURCE_FIT+core.online.SOURCE_RESERVED),
            replayed_opportunities=sum(record["opportunities"] for record in records),
            replayed_committed_events=sum(record["committed_events"] for record in records),
            changed_prediction_rows=changed_count,
            cpu_seconds=process_time()-cpu, wall_seconds=perf_counter()-began),
        records=records, fixed_history=core.summarize_replay(records),
        online_actual_costs=core.online_cost_table(retained),
        natural_planning_contribution=core.natural_cost_contribution(natural),
        limitations=["Fixed-history variants do not execute their counterfactual recommendations.",
                     "Source-factor transfer changes both source availability and grouping.",
                     "Natural planning contrast is conditional on the same retained parent/leaf models."])
    summary["retained_storage"] = dict(changed_predictions_gzip_bytes=changed_path.stat().st_size,
        online_input_gzip_bytes=Path(online_input).stat().st_size,
        natural_summary_bytes=Path(natural_summary).stat().st_size)
    summary["accounting"].update(cpu_seconds=process_time()-cpu, wall_seconds=perf_counter()-began,
        timing_scope="input reads, source reconstruction, fixed-prefix replay and cost summaries; output summary serialization excluded")
    with summary_path.open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online-input", type=Path, required=True)
    parser.add_argument("--natural-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.online_input, args.natural_summary, args.output)
    print(json.dumps(dict(status=result["status"], sources=len(result["records"]),
        accounting=result["accounting"], summary=str((args.output/"summary.json").resolve()))), flush=True)


if __name__ == "__main__":
    main()
