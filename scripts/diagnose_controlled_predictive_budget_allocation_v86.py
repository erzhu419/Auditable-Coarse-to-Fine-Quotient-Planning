"""Independent-root candidate accuracy and split-half reference reproducibility."""
import argparse
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES
from acfqp.science.controlled_predictive_centered_fragments_v85 import CenteredSelector
from diagnose_controlled_predictive_joint_fragments_v84 import mean, utility, candidate_pairs, ranking_summary
from diagnose_controlled_predictive_centered_fragments_v85 import prediction_errors

MODEL_FILES = dict(FROZEN_V85="frozen_selector.json", COVERAGE="coverage_selector.json", REPEAT="repeat_selector.json")
REPLICAS = 16


def _targets(deltas, start, stop):
    targets = {option: [mean(vector[j] for vector in deltas[option][start:stop])
                        for j in range(3)] for option in OPTIONS[1:]}
    targets["H2"] = [0.0, 0.0, 0.0]
    return targets


def split_half_pairs(first, second, query):
    pairs = []
    for left, right in combinations(OPTIONS[1:], 2):
        first_difference = utility(first[left], query) - utility(first[right], query)
        second_difference = utility(second[left], query) - utility(second[right], query)
        first_sign = int(first_difference > 0) - int(first_difference < 0)
        second_sign = int(second_difference > 0) - int(second_difference < 0)
        pairs.append(dict(left=left, right=right,
            same_primitive_duration_pair=left.split("_")[0] == right.split("_")[0],
            first_half_utility_difference=first_difference, second_half_utility_difference=second_difference,
            first_half_sign=first_sign, second_half_sign=second_sign,
            both_strict=first_sign != 0 and second_sign != 0,
            same_order=first_sign == second_sign,
            strict_sign_reversal=first_sign * second_sign < 0))
    return pairs


def stability_summary(pairs):
    pairs = list(pairs)
    strict = [pair for pair in pairs if pair["both_strict"]]
    same_strict = sum(pair["same_order"] for pair in strict)
    return dict(pairs=len(pairs), both_strict_pairs=len(strict), same_strict_order=same_strict,
        strict_sign_reversals=sum(pair["strict_sign_reversal"] for pair in pairs),
        any_half_tie_pairs=len(pairs) - len(strict),
        both_halves_tied=sum(pair["first_half_sign"] == pair["second_half_sign"] == 0 for pair in pairs),
        strict_order_agreement=same_strict / len(strict) if strict else None)


def diagnose_entries(entries, selectors, lifecycle, counts):
    counts["validation_root_records_read"] += len(entries)
    witnesses, excluded = [], []
    for entry in entries:
        root, deltas = entry["root"], entry["pair_deltas"]
        replica_counts = {option: len(deltas.get(option, [])) for option in OPTIONS[1:]}
        counts["retained_delta_vectors_read"] += sum(replica_counts.values())
        if not entry["complete_block"] or any(value != REPLICAS for value in replica_counts.values()):
            excluded.append(dict(lifecycle=lifecycle, root=root, complete_block=entry["complete_block"],
                replica_counts=replica_counts, outcomes=entry.get("outcomes", {}),
                reason="source_missing_trigger" if root["board"] is None else
                    "Validation root lacks a complete terminal 16-replica block for every option."))
            continue
        query = root["query"]
        targets = _targets(deltas, 0, REPLICAS)
        first, second = _targets(deltas, 0, 8), _targets(deltas, 8, 16)
        observed = {option: utility(target, query) for option, target in targets.items()}
        witness = dict(lifecycle=lifecycle, root=root, replicas=REPLICAS,
            retained_mean_targets=targets, retained_mean_utilities=observed,
            first_half_mean_targets=first, second_half_mean_targets=second,
            split_half_pairs=split_half_pairs(first, second, query), methods={})
        for method, selector in selectors.items():
            choice = selector.select(root["board"], query, work=counts)
            option = choice["option"]
            witness["methods"][method] = dict(**choice,
                duration=0 if option == "H2" else int(option.split("_")[1]),
                observed_mean_target=targets[option], observed_mean_utility=observed[option],
                candidate_pairs=candidate_pairs(choice["predictions"], observed),
                **prediction_errors(choice["predictions"], targets))
        frozen = witness["methods"]["FROZEN_V85"]
        for choice in witness["methods"].values():
            discrepancy = [abs(a - b) for a, b in zip(choice["candidate_prediction_mean"],
                                                     frozen["candidate_prediction_mean"])]
            choice.update(mean_prediction_discrepancy_components=discrepancy,
                max_mean_prediction_discrepancy=max(discrepancy),
                selection_disagrees_with_frozen=choice["option"] != frozen["option"])
        witnesses.append(witness)
    summaries = []
    for query in QUERIES:
        roots = [row for row in witnesses if row["root"]["query"] == query]
        missing = [row for row in excluded if row["root"]["query"] == query]
        reference_pairs = [pair for row in roots for pair in row["split_half_pairs"]]
        summary = dict(lifecycle=lifecycle, query=query, complete_roots=len(roots),
            excluded_roots=len(missing), methods={},
            split_half_reference_stability=stability_summary(reference_pairs),
            split_half_duration_stability=stability_summary(
                pair for pair in reference_pairs if pair["same_primitive_duration_pair"]))
        for method in MODEL_FILES:
            choices = [row["methods"][method] for row in roots]
            pairs = [pair for choice in choices for pair in choice["candidate_pairs"]]
            summary["methods"][method] = dict(roots=len(choices),
                selected_options=dict(Counter(choice["option"] for choice in choices)),
                selected_durations=dict(Counter(choice["duration"] for choice in choices)),
                predicted_selected_utility_mean=mean(choice["value"] for choice in choices),
                observed_selected_utility_mean=mean(choice["observed_mean_utility"] for choice in choices),
                interventions=sum(choice["option"] != "H2" for choice in choices),
                negative_interventions=sum(choice["option"] != "H2" and choice["observed_mean_utility"] < 0
                                           for choice in choices),
                selection_disagreements_with_frozen=sum(choice["selection_disagrees_with_frozen"] for choice in choices),
                max_mean_prediction_discrepancy=max((choice["max_mean_prediction_discrepancy"] for choice in choices), default=None),
                max_mean_prediction_discrepancy_components=[max(
                    (choice["mean_prediction_discrepancy_components"][j] for choice in choices), default=None) for j in range(3)],
                anchor_mean_squared_error_components=[mean(choice["mean_estimation_error"][j] ** 2
                                                           for choice in choices) for j in range(3)],
                centered_residual_mse_components=[mean(choice["centered_residual_mse_components"][j]
                                                       for choice in choices) for j in range(3)],
                full_candidate_mse_components=[mean(choice["full_candidate_mse_components"][j]
                                                    for choice in choices) for j in range(3)],
                candidate_ranking=ranking_summary(pairs),
                same_primitive_duration_ranking=ranking_summary(
                    pair for pair in pairs if pair["same_primitive_duration_pair"]))
        summaries.append(summary)
    return summaries, witnesses, excluded


def diagnose(directory):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete":
        raise ValueError("Choice diagnosis runs only after the main experiment is complete")
    counts, summaries, witnesses, excluded = Counter(), [], [], []
    for lifecycle in run["settings"]["lifecycles"]:
        folder = directory / f"life_{lifecycle}"
        entries = json.loads((folder / "validation/root_logs.json").read_text())
        selectors = {method: CenteredSelector.from_payload(json.loads((folder / filename).read_text()))
                     for method, filename in MODEL_FILES.items()}
        summary, roots, missing = diagnose_entries(entries, selectors, lifecycle, counts)
        summaries.extend(summary)
        witnesses.extend(roots)
        excluded.extend(missing)
    return dict(schema="acfqp.budget_allocation_choice_diagnosis.v86", summaries=summaries,
        root_witnesses=witnesses, excluded_roots=excluded,
        cohort=dict(complete_roots=len(witnesses), excluded_roots=len(excluded),
                    methods=list(MODEL_FILES), validation_replicas=REPLICAS),
        model_counts=dict(counts), new_training_rows=0, new_tree_fits=0, new_environment_transitions=0,
        evidence_scope="Every method uses the same complete validation roots, with all five arms terminal in "
            "each of 16 replicas. Incomplete roots are listed and excluded for all models together; their work "
            "remains in the main run. Targets are paired 16-replica means, not exact option values. Model ranking "
            "uses those full means; independent first-eight/last-eight ordering agreement measures reference "
            "reproducibility and is not model accuracy. Observed ties are separate, with predicted ties on strict "
            "observed pairs counted incorrect. Relative errors exclude the common four-option mean and H2 stays "
            "zero. Validation never refits or updates these frozen selectors. No new sampling occurs in this diagnosis.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.run)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
