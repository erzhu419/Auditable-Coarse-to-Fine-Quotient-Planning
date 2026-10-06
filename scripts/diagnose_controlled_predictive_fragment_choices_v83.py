"""Compare frozen fragment choices with retained eight-replica outcome means."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from math import fsum
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from acfqp.science.controlled_predictive_fragments_v83 import (
    Selector, QUERIES, ONE_STEP_OPTIONS, FEATURE_NAMES,
)


def mean(values):
    values = list(values)
    return fsum(values) / len(values) if values else None


def utility(target, query):
    weights = QUERIES[query]
    return (target[0] * weights["reward_weight"] - target[1] * weights["failure_penalty"]
            + target[2] * weights["goal_bonus"])


def diagnose_rows(rows, selector, lifecycle, checkpoint, counts):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[row["query"], row["episode"]][row["option"]] = row
    witnesses = []
    for (query, episode), options in sorted(grouped.items()):
        targets = {name: record["target"] for name, record in options.items()}
        targets["H2"] = [0.0, 0.0, 0.0]
        board = next(iter(options.values()))["board"]
        witness = dict(lifecycle=lifecycle, checkpoint=checkpoint, query=query, episode=episode,
            split="heldout" if episode % 5 == 4 else "training", board=board,
            retained_mean_targets=targets, methods={})
        for method, allowed in (("FRAGMENT", None), ("ONE_STEP", ONE_STEP_OPTIONS)):
            choice = selector.select(board, query, allowed=allowed, work=counts)
            target = targets[choice["option"]]
            vectors = [entry["target"] for name, entry in choice["predictions"].items() if name != "H2"]
            top = max(entry["value"] for entry in choice["predictions"].values())
            witness["methods"][method] = dict(**choice, observed_mean_target=target,
                observed_mean_utility=utility(target, query),
                identical_alternative_predictions=all(vector == vectors[0] for vector in vectors),
                top_score_options=[name for name, entry in choice["predictions"].items()
                                   if entry["value"] == top])
        witnesses.append(witness)
    summaries = []
    for query in QUERIES:
        for split in ("training", "heldout"):
            roots = [row for row in witnesses if row["query"] == query and row["split"] == split]
            summary = dict(lifecycle=lifecycle, checkpoint=checkpoint, query=query,
                           split=split, roots=len(roots), methods={})
            for method in ("FRAGMENT", "ONE_STEP"):
                choices = [row["methods"][method] for row in roots]
                summary["methods"][method] = dict(
                    selected_options=dict(Counter(row["option"] for row in choices)),
                    h2_fraction=mean(row["option"] == "H2" for row in choices),
                    predicted_utility_mean=mean(row["value"] for row in choices),
                    observed_utility_mean=mean(row["observed_mean_utility"] for row in choices),
                    overrides=sum(row["option"] != "H2" for row in choices),
                    identical_alternative_prediction_roots=sum(row["identical_alternative_predictions"] for row in choices),
                    top_score_tie_roots=sum(len(row["top_score_options"]) > 1 for row in choices),
                    positive_top_score_tie_roots=sum(row["value"] > 0 and len(row["top_score_options"]) > 1
                                                     for row in choices),
                    negative_selected_overrides=sum(row["option"] != "H2" and
                        row["observed_mean_utility"] < 0 for row in choices))
            summary["observed_fragment_minus_one_step"] = mean(
                row["methods"]["FRAGMENT"]["observed_mean_utility"] -
                row["methods"]["ONE_STEP"]["observed_mean_utility"] for row in roots)
            summaries.append(summary)
    return summaries, witnesses


def evaluation_history_choices(folder, lifecycle, checkpoint):
    with gzip.open(folder / "evaluation_games.jsonl.gz", "rt") as handle:
        games = [json.loads(line) for line in handle]
    histories = {(row["method"], row["query"], row["episode"]["seed"]):
        [(step["board"], step["action"], step["next_board"]) for step in row["episode"]["steps"]]
        for row in games}
    witnesses, summaries = [], []
    for row in games:
        if row["method"] not in ("FRAGMENT", "ONE_STEP", "FROZEN_6"):
            continue
        seed, query = row["episode"]["seed"], row["query"]
        option = row["controller_events"][0]["option"] if row["controller_events"] else None
        witnesses.append(dict(lifecycle=lifecycle, checkpoint=checkpoint, method=row["method"],
            query=query, seed=seed, selected_option=option, selected_non_h2=option not in (None, "H2"),
            identical_to_h2=histories[row["method"], query, seed] == histories["H2_ONLY", query, seed]))
    for method in ("FRAGMENT", "ONE_STEP", "FROZEN_6"):
        for query in QUERIES:
            selected = [row for row in witnesses if row["method"] == method and row["query"] == query]
            summaries.append(dict(lifecycle=lifecycle, checkpoint=checkpoint, method=method, query=query,
                games=len(selected), identical_to_h2=sum(row["identical_to_h2"] for row in selected),
                selected_non_h2=sum(row["selected_non_h2"] for row in selected),
                selected_non_h2_but_identical_to_h2=sum(row["selected_non_h2"] and row["identical_to_h2"]
                                                      for row in selected)))
    return summaries, witnesses


def diagnose(directory):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete":
        raise ValueError("Choice diagnosis runs only after the main experiment is complete")
    counts, summaries, witnesses = Counter(), [], []
    feature_usage, history_summaries, history_witnesses = [], [], []
    for lifecycle in run["settings"]["lifecycles"]:
        rows = []
        for checkpoint in run["settings"]["checkpoints"]:
            folder = directory / f"life_{lifecycle}" / f"checkpoint_{checkpoint}"
            with gzip.open(folder / "new_rows.jsonl.gz", "rt") as handle:
                rows.extend(json.loads(line) for line in handle)
            selector = Selector.from_payload(json.loads((folder / "selector.json").read_text()))
            for query, tree in selector.trees.items():
                splits = Counter(FEATURE_NAMES[index] for index, left in zip(tree["feature"], tree["left"]) if left >= 0)
                feature_usage.append(dict(lifecycle=lifecycle, checkpoint=checkpoint, query=query,
                    split_feature_counts=dict(splits), primitive_split_count=splits["primitive_SPACE"] + splits["primitive_SNAKE"],
                    duration_split_count=splits["duration_fraction"]))
            summary, roots = diagnose_rows(rows, selector, lifecycle, checkpoint, counts)
            summaries.extend(summary)
            witnesses.extend(roots)
            history_summary, history_roots = evaluation_history_choices(folder, lifecycle, checkpoint)
            history_summaries.extend(history_summary)
            history_witnesses.extend(history_roots)
    return dict(schema="acfqp.fragment_choice_diagnosis.v83", summaries=summaries,
        tree_feature_usage=feature_usage, evaluation_history_summaries=history_summaries,
        evaluation_history_witnesses=history_witnesses,
        root_witnesses=witnesses, model_counts=dict(counts), new_training_rows=0,
        new_tree_fits=0, new_environment_transitions=0,
        evidence_scope="Observed values are retained paired eight-replica means, not exact values. "
            "Training roots are in-sample; heldout roots never fitted the selector. Checkpoint-6 roots "
            "reappear in checkpoint-12 summaries. Censored roots have no labels and are excluded. "
            "Choices are evaluated without changing the frozen selectors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.run)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
