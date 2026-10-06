"""Describe query-dependent actions from retained V77 evaluation trajectories."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def compare_pair(first, second, query_names):
    """Compare observations only while the actual action histories still agree."""
    left, right = first["episode"], second["episode"]
    result = dict(seed=left["seed"], queries=query_names,
                  episode_steps={query_names[0]: len(left["steps"]),
                                 query_names[1]: len(right["steps"])},
                  identical_action_prefix_steps=0, first_action_difference=None,
                  prefix_drift=None)
    if left["initial_board"] != right["initial_board"]:
        result["prefix_drift"] = dict(step=0, field="initial_board")
        return result
    for index, (a, b) in enumerate(zip(left["steps"], right["steps"])):
        if a["board"] != b["board"]:
            result["prefix_drift"] = dict(step=index, field="board")
            return result
        if a["action"] != b["action"]:
            result["first_action_difference"] = dict(
                step=index, board=a["board"],
                actions={query_names[0]: a["action"], query_names[1]: b["action"]},
            )
            return result
        result["identical_action_prefix_steps"] += 1
        for field in ("next_board", "score", "status"):
            if a[field] != b[field]:
                result["prefix_drift"] = dict(step=index, field=field)
                return result
    if len(left["steps"]) != len(right["steps"]):
        result["prefix_drift"] = dict(
            step=result["identical_action_prefix_steps"], field="episode_length")
    elif left["final_board"] != right["final_board"] or left["status"] != right["status"]:
        result["prefix_drift"] = dict(
            step=result["identical_action_prefix_steps"], field="final_observation")
    return result


def summarize(pairs):
    different = [row for row in pairs if row["first_action_difference"] is not None]
    drifted = [row for row in pairs if row["prefix_drift"] is not None]
    return dict(
        pairs=len(pairs), query_response_pairs=len(different),
        unchanged_action_pairs=len(pairs) - len(different) - len(drifted),
        prefix_drift_pairs=len(drifted),
        first_difference_steps=[row["first_action_difference"]["step"] for row in different],
    )


def run(directory):
    started = perf_counter()
    manifest = json.loads((directory / "run.json").read_text())
    settings = manifest["settings"]
    query_names = list(settings["queries"])
    if len(query_names) != 2:
        raise ValueError("V77 query comparison requires its two frozen queries")
    rows, errors, sources = [], [], []
    for life in settings["lifecycles"]:
        for checkpoint in settings["checkpoints"]:
            path = directory / f"life_{life}/checkpoint_{checkpoint}/evaluation_episodes.jsonl.gz"
            groups = defaultdict(dict)
            duplicates = []
            with gzip.open(path, "rt") as stream:
                for line in stream:
                    record = json.loads(line)
                    key = (record["method"], record["episode"]["seed"])
                    if record["query"] in groups[key]:
                        duplicates.append(dict(method=key[0], seed=key[1], query=record["query"]))
                    groups[key][record["query"]] = record
            sources.append(dict(path=str(path.relative_to(directory)), compressed_bytes=path.stat().st_size,
                                game_pairs=len(groups)))
            if duplicates:
                errors.append(dict(lifecycle=life, checkpoint=checkpoint, duplicate_games=duplicates))
            method_counts = Counter(method for method, _ in groups)
            expected_counts = {method: settings["evaluation_replicas"] for method in settings["methods"]}
            if dict(method_counts) != expected_counts:
                errors.append(dict(lifecycle=life, checkpoint=checkpoint,
                                   actual_method_pairs=dict(method_counts), expected_method_pairs=expected_counts))
            for (method, seed), records in sorted(groups.items()):
                if set(records) != set(query_names):
                    errors.append(dict(lifecycle=life, checkpoint=checkpoint, method=method,
                                       seed=seed, actual_queries=sorted(records)))
                    continue
                paired = compare_pair(records[query_names[0]], records[query_names[1]], query_names)
                paired.update(lifecycle=life, checkpoint=checkpoint, method=method)
                rows.append(paired)
    grouped = []
    for checkpoint in settings["checkpoints"]:
        for method in settings["methods"]:
            matching = [row for row in rows if row["checkpoint"] == checkpoint and row["method"] == method]
            grouped.append(dict(checkpoint=checkpoint, method=method, **summarize(matching)))
    overall = summarize(rows)
    expected_pairs = (len(settings["lifecycles"]) * len(settings["checkpoints"])
                      * len(settings["methods"]) * settings["evaluation_replicas"])
    return dict(
        schema="acfqp.lifelong_query_response.v77", complete=not errors and len(rows) == expected_pairs,
        paired_prefixes_valid=overall["prefix_drift_pairs"] == 0,
        expected_pairs=expected_pairs, query_names=query_names, overall=overall,
        by_method_and_checkpoint=grouped,
        by_method={method: summarize([row for row in rows if row["method"] == method])
                   for method in settings["methods"]},
        pairs=rows, cohort_errors=errors, sources=sources,
        work=dict(new_ground_calls=0, new_training_calls=0, retained_episode_files_read=len(sources)),
        seconds=perf_counter() - started,
        evidence_scope="Describes the first different action on an identical observation/action prefix. "
                       "Later divergent trajectories are not compared as if they were the same states. "
                       "Query response establishes neither optimality nor reduced risk. "
                       "Repeated checkpoints and shared evaluation seeds are not independent learning runs.",
        step_numbering="zero_based",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path,
                        default=ROOT / "reports/controlled_predictive_lifelong_v77")
    args = parser.parse_args()
    result = run(args.directory)
    output = args.directory / "query_response.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(output=str(output), complete=result["complete"],
                          paired_prefixes_valid=result["paired_prefixes_valid"],
                          overall=result["overall"], by_method=result["by_method"],
                          seconds=result["seconds"])))
    if not result["complete"] or not result["paired_prefixes_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
