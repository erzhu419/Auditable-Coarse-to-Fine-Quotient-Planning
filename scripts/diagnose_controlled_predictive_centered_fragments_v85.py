"""Separate shared-mean and relative-option errors on retained paired outcomes."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, ONE_STEP_OPTIONS
from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector
from acfqp.science.controlled_predictive_centered_fragments_v85 import CenteredSelector
from diagnose_controlled_predictive_joint_fragments_v84 import (
    mean, utility, candidate_pairs, ranking_summary,
)

METHODS = ("CENTERED", "CENTERED_ONE_STEP", "JOINT")


def prediction_errors(predictions, targets):
    predicted_mean = [mean(predictions[option]["target"][j] for option in OPTIONS[1:]) for j in range(3)]
    observed_mean = [mean(targets[option][j] for option in OPTIONS[1:]) for j in range(3)]
    return dict(candidate_prediction_mean=predicted_mean,
        mean_estimation_error=[p - y for p, y in zip(predicted_mean, observed_mean)],
        centered_residual_mse_components=[mean(
            ((predictions[option]["target"][j] - predicted_mean[j])
             - (targets[option][j] - observed_mean[j])) ** 2 for option in OPTIONS[1:]) for j in range(3)],
        full_candidate_mse_components=[mean(
            (predictions[option]["target"][j] - targets[option][j]) ** 2
            for option in OPTIONS[1:]) for j in range(3)])


def diagnose_rows(rows, centered, joint, lifecycle, checkpoint, counts):
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
        choices = dict(CENTERED=centered.select(board, query, work=counts),
            CENTERED_ONE_STEP=centered.select(board, query, allowed=ONE_STEP_OPTIONS, work=counts),
            JOINT=joint.select(board, query, work=counts))
        witness = dict(lifecycle=lifecycle, checkpoint=checkpoint, query=query, episode=episode,
            split="heldout" if episode % 5 == 4 else "training", board=board,
            retained_mean_targets=targets, retained_mean_utilities=observed,
            observed_candidate_mean=[mean(targets[option][j] for option in OPTIONS[1:]) for j in range(3)],
            methods={})
        for method, choice in choices.items():
            full = choices["CENTERED" if method == "CENTERED_ONE_STEP" else method]["predictions"]
            option = choice["option"]
            vectors = [full[name]["target"] for name in OPTIONS[1:]]
            top = max(entry["value"] for entry in choice["predictions"].values())
            witness["methods"][method] = dict(**choice,
                duration=0 if option == "H2" else int(option.split("_")[1]),
                observed_mean_target=targets[option], observed_mean_utility=observed[option],
                full_candidate_predictions=full,
                identical_alternative_predictions=all(vector == vectors[0] for vector in vectors[1:]),
                top_score_options=[name for name, entry in choice["predictions"].items() if entry["value"] == top],
                candidate_pairs=candidate_pairs(full, observed), **prediction_errors(full, targets))
        anchor = witness["methods"]["JOINT"]
        updated = witness["methods"]["CENTERED"]
        discrepancy = [abs(a - b) for a, b in zip(updated["candidate_prediction_mean"],
                                                 anchor["candidate_prediction_mean"])]
        witness.update(mean_prediction_discrepancy_components=discrepancy,
            max_mean_prediction_discrepancy=max(discrepancy),
            anchor_candidate_prediction_mean=anchor["candidate_prediction_mean"],
            anchor_mean_estimation_error=anchor["mean_estimation_error"],
            anchor_mean_squared_error_components=[value ** 2 for value in anchor["mean_estimation_error"]])
        for choice in witness["methods"].values():
            choice["selection_disagrees_with_joint"] = choice["option"] != anchor["option"]
            for pair, reference in zip(choice["candidate_pairs"], anchor["candidate_pairs"]):
                pair["ranking_disagrees_with_joint"] = pair["predicted_sign"] != reference["predicted_sign"]
        witnesses.append(witness)
    summaries = []
    for query in QUERIES:
        for split in ("training", "heldout"):
            roots = [row for row in witnesses if row["query"] == query and row["split"] == split]
            summary = dict(lifecycle=lifecycle, checkpoint=checkpoint, query=query,
                split=split, roots=len(roots), methods={},
                max_mean_prediction_discrepancy=max((row["max_mean_prediction_discrepancy"] for row in roots), default=None),
                max_mean_prediction_discrepancy_components=[max(
                    (row["mean_prediction_discrepancy_components"][j] for row in roots), default=None) for j in range(3)],
                anchor_mean_estimation_error_mean=[mean(row["anchor_mean_estimation_error"][j] for row in roots) for j in range(3)],
                anchor_mean_squared_error_components=[mean(row["anchor_mean_squared_error_components"][j] for row in roots)
                                                      for j in range(3)])
            for method in METHODS:
                choices = [row["methods"][method] for row in roots]
                pairs = [pair for choice in choices for pair in choice["candidate_pairs"]]
                summary["methods"][method] = dict(
                    selected_options=dict(Counter(choice["option"] for choice in choices)),
                    selected_durations=dict(Counter(choice["duration"] for choice in choices)),
                    predicted_selected_utility_mean=mean(choice["value"] for choice in choices),
                    observed_selected_utility_mean=mean(choice["observed_mean_utility"] for choice in choices),
                    interventions=sum(choice["option"] != "H2" for choice in choices),
                    negative_interventions=sum(choice["option"] != "H2" and choice["observed_mean_utility"] < 0
                                               for choice in choices),
                    identical_alternative_prediction_roots=sum(choice["identical_alternative_predictions"] for choice in choices),
                    top_score_tie_roots=sum(len(choice["top_score_options"]) > 1 for choice in choices),
                    positive_top_score_tie_roots=sum(choice["value"] > 0 and len(choice["top_score_options"]) > 1
                                                     for choice in choices),
                    centered_residual_mse_components=[mean(choice["centered_residual_mse_components"][j]
                                                           for choice in choices) for j in range(3)],
                    full_candidate_mse_components=[mean(choice["full_candidate_mse_components"][j]
                                                        for choice in choices) for j in range(3)],
                    selection_disagreements_with_joint=sum(choice["selection_disagrees_with_joint"] for choice in choices),
                    ranking_disagreements_with_joint=sum(pair["ranking_disagrees_with_joint"] for pair in pairs),
                    duration_ranking_disagreements_with_joint=sum(pair["ranking_disagrees_with_joint"]
                        for pair in pairs if pair["same_primitive_duration_pair"]),
                    candidate_ranking=ranking_summary(pairs),
                    same_primitive_duration_ranking=ranking_summary(
                        pair for pair in pairs if pair["same_primitive_duration_pair"]))
            summaries.append(summary)
    return summaries, witnesses


def diagnose(directory):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete":
        raise ValueError("Choice diagnosis runs only after the main experiment is complete")
    counts, summaries, witnesses = Counter(), [], []
    for lifecycle in run["settings"]["lifecycles"]:
        for checkpoint in run["settings"]["checkpoints"]:
            folder = directory / f"life_{lifecycle}" / f"checkpoint_{checkpoint}"
            with gzip.open(folder / "paired_rows.jsonl.gz", "rt") as handle:
                rows = [json.loads(line) for line in handle]
            centered = CenteredSelector.from_payload(json.loads((folder / "centered_selector.json").read_text()))
            joint = JointSelector.from_payload(json.loads((folder / "joint_selector.json").read_text()))
            summary, roots = diagnose_rows(rows, centered, joint, lifecycle, checkpoint, counts)
            summaries.extend(summary)
            witnesses.extend(roots)
    return dict(schema="acfqp.centered_fragment_choice_diagnosis.v85", summaries=summaries,
        root_witnesses=witnesses, model_counts=dict(counts), new_training_rows=0, new_tree_fits=0,
        new_environment_transitions=0,
        evidence_scope="Targets are retained paired eight-replica means, not exact option values. Training roots "
            "are in-sample; episode % 5 == 4 roots were excluded from fitting but have already been inspected. "
            "Checkpoint-6 rows reappear at checkpoint 12. Mean errors use the full four candidates, excluding H2; "
            "residual errors subtract each prediction/observation set's own mean. CENTERED_ONE_STEP restricts "
            "selection only; its six-pair ranking and residual errors use the full CENTERED predictions. Observed "
            "ties are separate; predicted ties on strict observed pairs count as incorrect. No fitting or sampling occurs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.run)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
