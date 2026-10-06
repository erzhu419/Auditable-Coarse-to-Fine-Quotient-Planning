"""Compare frozen candidate ordering against retained paired outcome means."""
import argparse
from collections import Counter, defaultdict
import gzip
from itertools import combinations
import json
from math import fsum
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from acfqp.science.controlled_predictive_fragments_v83 import Selector, OPTIONS, QUERIES, ONE_STEP_OPTIONS
from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector


METHODS = ("JOINT", "JOINT_ONE_STEP", "OLD")


def mean(values):
    values = list(values)
    return fsum(values) / len(values) if values else None


def utility(target, query):
    weights = QUERIES[query]
    return (target[0] * weights["reward_weight"] - target[1] * weights["failure_penalty"]
            + target[2] * weights["goal_bonus"])


def _sign(value):
    return int(value > 0) - int(value < 0)


def candidate_pairs(predictions, observed):
    pairs = []
    for left, right in combinations(OPTIONS[1:], 2):
        predicted_delta = predictions[left]["value"] - predictions[right]["value"]
        observed_delta = observed[left] - observed[right]
        predicted_sign, observed_sign = _sign(predicted_delta), _sign(observed_delta)
        relation = ("observed_tie" if observed_sign == 0 else "predicted_tie" if predicted_sign == 0
                    else "concordant" if predicted_sign == observed_sign else "discordant")
        pairs.append(dict(left=left, right=right,
            same_primitive_duration_pair=left.split("_")[0] == right.split("_")[0],
            predicted_utility_difference=predicted_delta, observed_mean_utility_difference=observed_delta,
            predicted_sign=predicted_sign, observed_sign=observed_sign, relation=relation))
    return pairs


def ranking_summary(pairs):
    pairs = list(pairs)
    strict = [pair for pair in pairs if pair["observed_sign"] != 0]
    counts = Counter(pair["relation"] for pair in pairs)
    return dict(pairs=len(pairs), observed_ties=counts["observed_tie"],
        observed_ties_also_predicted_tied=sum(pair["observed_sign"] == pair["predicted_sign"] == 0 for pair in pairs),
        strict_observed_pairs=len(strict), concordant=counts["concordant"], discordant=counts["discordant"],
        predicted_ties_on_strict_observed_pairs=counts["predicted_tie"],
        observed_strict_order_accuracy=counts["concordant"] / len(strict) if strict else None)


def diagnose_rows(rows, joint, old, lifecycle, checkpoint, counts):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[row["query"], row["episode"]][row["option"]] = row
    counts["retained_option_rows_read"] += len(rows)
    witnesses = []
    for (query, episode), records in sorted(grouped.items()):
        targets = {option: records[option]["target"] for option in OPTIONS[1:]}
        targets["H2"] = [0.0, 0.0, 0.0]
        observed = {option: utility(target, query) for option, target in targets.items()}
        board = records[OPTIONS[1]]["board"]
        choices = dict(JOINT=joint.select(board, query, work=counts),
            JOINT_ONE_STEP=joint.select(board, query, allowed=ONE_STEP_OPTIONS, work=counts),
            OLD=old.select(board, query, work=counts))
        witness = dict(lifecycle=lifecycle, checkpoint=checkpoint, query=query, episode=episode,
            split="heldout" if episode % 5 == 4 else "training", board=board,
            retained_mean_targets=targets, retained_mean_utilities=observed, methods={})
        for method, choice in choices.items():
            # Restricting execution choices leaves the joint model's four output vectors unchanged.
            full_predictions = choices["JOINT" if method == "JOINT_ONE_STEP" else method]["predictions"]
            vectors = [full_predictions[option]["target"] for option in OPTIONS[1:]]
            top = max(prediction["value"] for prediction in choice["predictions"].values())
            option = choice["option"]
            witness["methods"][method] = dict(**choice,
                duration=0 if option == "H2" else int(option.split("_")[1]),
                observed_mean_target=targets[option], observed_mean_utility=observed[option],
                identical_alternative_predictions=all(vector == vectors[0] for vector in vectors[1:]),
                full_candidate_predictions=full_predictions,
                top_score_options=[name for name, prediction in choice["predictions"].items()
                                   if prediction["value"] == top],
                candidate_pairs=candidate_pairs(full_predictions, observed))
        witnesses.append(witness)
    summaries = []
    for query in QUERIES:
        for split in ("training", "heldout"):
            selected = [row for row in witnesses if row["query"] == query and row["split"] == split]
            summary = dict(lifecycle=lifecycle, checkpoint=checkpoint, query=query,
                           split=split, roots=len(selected), methods={})
            for method in METHODS:
                choices = [row["methods"][method] for row in selected]
                pairs = [pair for choice in choices for pair in choice["candidate_pairs"]]
                summary["methods"][method] = dict(
                    selected_options=dict(Counter(choice["option"] for choice in choices)),
                    selected_durations=dict(Counter(choice["duration"] for choice in choices)),
                    h2_fraction=mean(choice["option"] == "H2" for choice in choices),
                    predicted_selected_utility_mean=mean(choice["value"] for choice in choices),
                    observed_selected_utility_mean=mean(choice["observed_mean_utility"] for choice in choices),
                    interventions=sum(choice["option"] != "H2" for choice in choices),
                    negative_interventions=sum(choice["option"] != "H2" and
                        choice["observed_mean_utility"] < 0 for choice in choices),
                    identical_alternative_prediction_roots=sum(choice["identical_alternative_predictions"] for choice in choices),
                    top_score_tie_roots=sum(len(choice["top_score_options"]) > 1 for choice in choices),
                    positive_top_score_tie_roots=sum(choice["value"] > 0 and
                        len(choice["top_score_options"]) > 1 for choice in choices),
                    candidate_ranking=ranking_summary(pairs),
                    same_primitive_duration_ranking=ranking_summary(
                        pair for pair in pairs if pair["same_primitive_duration_pair"]))
            summaries.append(summary)
    return summaries, witnesses


def diagnose(directory):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete":
        raise ValueError("Choice diagnosis runs only after the main experiment is complete")
    summaries, witnesses, counts = [], [], Counter()
    for lifecycle in run["settings"]["lifecycles"]:
        for checkpoint in run["settings"]["checkpoints"]:
            folder = directory / f"life_{lifecycle}" / f"checkpoint_{checkpoint}"
            with gzip.open(folder / "paired_rows.jsonl.gz", "rt") as handle:
                rows = [json.loads(line) for line in handle]
            joint = JointSelector.from_payload(json.loads((folder / "joint_selector.json").read_text()))
            old = Selector.from_payload(json.loads((folder / "old_selector.json").read_text()))
            summary, roots = diagnose_rows(rows, joint, old, lifecycle, checkpoint, counts)
            summaries.extend(summary)
            witnesses.extend(roots)
    return dict(schema="acfqp.joint_fragment_choice_diagnosis.v84", summaries=summaries,
        root_witnesses=witnesses, model_counts=dict(counts), new_training_rows=0,
        new_tree_fits=0, new_environment_transitions=0,
        evidence_scope="Observed values are retained paired eight-replica means, not exact action values. "
            "Training roots are in-sample; heldout episodes have episode % 5 == 4 and were not fitted. "
            "Checkpoint-6 rows reappear at checkpoint 12. All six candidate pairs use the four full predictions; "
            "JOINT_ONE_STEP restricts selection, while its ranking predictions equal JOINT. Two within-primitive "
            "1-versus-4 duration pairs are also reported separately. Strict-order accuracy excludes observed ties "
            "and counts predicted ties on observed strict pairs as incorrect. No new sampling or fitting occurs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.run)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
