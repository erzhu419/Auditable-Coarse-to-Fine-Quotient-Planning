"""Retained-data diagnosis of shared-mean updates and H2 intervention gates."""
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
from acfqp.science.controlled_predictive_mean_fragments_v87 import MeanSelector
from diagnose_controlled_predictive_joint_fragments_v84 import mean, utility, candidate_pairs, ranking_summary
from diagnose_controlled_predictive_centered_fragments_v85 import prediction_errors

MODEL_FILES = dict(COVERAGE_OLD="coverage_old_selector.json", COVERAGE_MEAN="coverage_mean_selector.json",
                   REPEAT_OLD="repeat_old_selector.json", REPEAT_MEAN="repeat_mean_selector.json")
FAMILIES = ("COVERAGE", "REPEAT")


def compare_update(old, updated):
    before, after = old["predictions"], updated["predictions"]
    pairs = []
    for left, right in combinations(OPTIONS[1:], 2):
        old_rank = before[left]["value"] - before[right]["value"]
        new_rank = after[left]["ranking_value"] - after[right]["ranking_value"]
        pairs.append(dict(left=left, right=right,
            vector_difference_change=[(after[left]["target"][j] - after[right]["target"][j])
                - (before[left]["target"][j] - before[right]["target"][j]) for j in range(3)],
            original_rank_difference=old_rank, retained_rank_difference=new_rank,
            rank_disagrees=(int(old_rank > 0) - int(old_rank < 0)) !=
                          (int(new_rank > 0) - int(new_rank < 0))))
    old_winner = max(OPTIONS[1:], key=lambda option: before[option]["value"])
    new_winner = max(OPTIONS[1:], key=lambda option: after[option]["ranking_value"])
    a, b = old["option"], updated["option"]
    category = ("enabled" if a == "H2" and b != "H2" else
                "disabled" if a != "H2" and b == "H2" else
                "both_h2" if a == b == "H2" else
                "same_fragment" if a == b else "changed_fragment")
    return dict(candidate_pairs=pairs,
        max_candidate_pair_vector_difference_change=max(abs(value) for pair in pairs
                                                        for value in pair["vector_difference_change"]),
        exact_original_ranking_disagreements=sum(pair["rank_disagrees"] for pair in pairs),
        original_ranking_value_mismatches=sum(after[option]["ranking_value"] != before[option]["value"]
                                             for option in OPTIONS[1:]),
        original_non_h2_winner=old_winner, updated_non_h2_winner=new_winner,
        non_h2_winner_disagrees=old_winner != new_winner,
        max_residual_mse_change=max(abs(a - b) for a, b in zip(old["centered_residual_mse_components"],
                                                              updated["centered_residual_mse_components"])),
        gate_category=category,
        observed_utility_delta_vs_old=updated["observed_mean_utility"] - old["observed_mean_utility"],
        updated_observed_utility_vs_h2=updated["observed_mean_utility"],
        old_observed_utility_vs_h2=old["observed_mean_utility"])


def diagnose_entries(entries, selectors, lifecycle, counts):
    witnesses, excluded = [], []
    counts["retained_root_records_read"] += len(entries)
    for entry in entries:
        root, deltas = entry["root"], entry["pair_deltas"]
        replica_counts = {option: len(deltas.get(option, [])) for option in OPTIONS[1:]}
        counts["retained_delta_vectors_read"] += sum(replica_counts.values())
        if not entry["complete_block"] or any(value != 16 for value in replica_counts.values()):
            excluded.append(dict(lifecycle=lifecycle, root=root, complete_block=entry["complete_block"],
                replica_counts=replica_counts,
                reason="source_missing_trigger" if root["board"] is None else "incomplete_terminal_block"))
            continue
        targets = {option: [mean(vector[j] for vector in deltas[option]) for j in range(3)]
                   for option in OPTIONS[1:]}
        targets["H2"] = [0.0, 0.0, 0.0]
        observed = {option: utility(target, root["query"]) for option, target in targets.items()}
        witness = dict(lifecycle=lifecycle, root=root, retained_mean_targets=targets,
            retained_mean_utilities=observed, methods={}, comparisons={})
        for method, selector in selectors.items():
            choice = selector.select(root["board"], root["query"], work=counts)
            ranks = {option: dict(value=entry["ranking_value"] if method.endswith("_MEAN") else entry["value"])
                     for option, entry in choice["predictions"].items()}
            witness["methods"][method] = dict(**choice,
                observed_mean_utility=observed[choice["option"]],
                original_candidate_ranking=candidate_pairs(ranks, observed),
                **prediction_errors(choice["predictions"], targets))
        for family in FAMILIES:
            witness["comparisons"][family] = compare_update(witness["methods"][family + "_OLD"],
                                                           witness["methods"][family + "_MEAN"])
        witnesses.append(witness)
    return witnesses, excluded


def summarize(witnesses, excluded, query, lifecycle):
    roots = [row for row in witnesses if (query == "all" or row["root"]["query"] == query)
             and (lifecycle == "all" or row["lifecycle"] == lifecycle)]
    missing = [row for row in excluded if (query == "all" or row["root"]["query"] == query)
               and (lifecycle == "all" or row["lifecycle"] == lifecycle)]
    summary = dict(lifecycle=lifecycle, query=query, complete_roots=len(roots), excluded_roots=len(missing),
                   methods={}, comparisons={})
    for method in MODEL_FILES:
        choices = [row["methods"][method] for row in roots]
        pairs = [pair for choice in choices for pair in choice["original_candidate_ranking"]]
        summary["methods"][method] = dict(selected_options=dict(Counter(choice["option"] for choice in choices)),
            mean_rfs_mse_components=[mean(choice["mean_estimation_error"][j] ** 2 for choice in choices) for j in range(3)],
            centered_residual_mse_components=[mean(choice["centered_residual_mse_components"][j] for choice in choices)
                                               for j in range(3)],
            full_candidate_mse_components=[mean(choice["full_candidate_mse_components"][j] for choice in choices)
                                            for j in range(3)],
            observed_selected_utility_mean=mean(choice["observed_mean_utility"] for choice in choices),
            predicted_selected_utility_mean=mean(choice["value"] for choice in choices),
            interventions=sum(choice["option"] != "H2" for choice in choices),
            negative_interventions=sum(choice["option"] != "H2" and choice["observed_mean_utility"] < 0
                                       for choice in choices),
            original_candidate_ranking=ranking_summary(pairs))
    for family in FAMILIES:
        changes = [row["comparisons"][family] for row in roots]
        comparison = dict(
            max_candidate_pair_vector_difference_change=max(
                (row["max_candidate_pair_vector_difference_change"] for row in changes), default=None),
            exact_original_ranking_disagreements=sum(row["exact_original_ranking_disagreements"] for row in changes),
            original_ranking_value_mismatches=sum(row["original_ranking_value_mismatches"] for row in changes),
            non_h2_winner_disagreements=sum(row["non_h2_winner_disagrees"] for row in changes),
            max_residual_mse_change=max((row["max_residual_mse_change"] for row in changes), default=None),
            observed_utility_delta_vs_old_mean=mean(row["observed_utility_delta_vs_old"] for row in changes),
            gates={})
        for category in sorted({row["gate_category"] for row in changes}):
            group = [row for row in changes if row["gate_category"] == category]
            comparison["gates"][category] = dict(roots=len(group),
                observed_utility_delta_vs_old_mean=mean(row["observed_utility_delta_vs_old"] for row in group),
                updated_observed_utility_vs_h2_mean=mean(row["updated_observed_utility_vs_h2"] for row in group),
                old_observed_utility_vs_h2_mean=mean(row["old_observed_utility_vs_h2"] for row in group))
        summary["comparisons"][family] = comparison
    return summary


def diagnose(directory):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete":
        raise ValueError("Retained diagnosis runs only after the main experiment is complete")
    witnesses, excluded, counts = [], [], Counter()
    for lifecycle in run["settings"]["lifecycles"]:
        folder = directory / f"life_{lifecycle}"
        entries = json.loads((folder / "validation_root_logs.json").read_text())
        selectors = {method: (MeanSelector if method.endswith("_MEAN") else CenteredSelector).from_payload(
            json.loads((folder / filename).read_text())) for method, filename in MODEL_FILES.items()}
        roots, missing = diagnose_entries(entries, selectors, lifecycle, counts)
        witnesses.extend(roots)
        excluded.extend(missing)
    return dict(schema="acfqp.mean_update_retained_diagnosis.v87",
        summaries=[summarize(witnesses, excluded, query, life) for life in run["settings"]["lifecycles"] for query in QUERIES],
        aggregate_summaries=[summarize(witnesses, excluded, query, "all") for query in (*QUERIES, "all")],
        root_witnesses=witnesses, excluded_roots=excluded,
        cohort=dict(complete_roots=len(witnesses), excluded_roots=len(excluded), replicas=16),
        model_counts=dict(counts), new_environment_transitions=0, new_tree_fits=0,
        evidence_scope="This reuses V86 validation roots already inspected when choosing the shared-mean hypothesis; "
            "it is a retained diagnostic, not new independent validation. The same complete roots and 16-replica "
            "paired means serve all four models. Means are Monte Carlo observations, not exact option values. "
            "Candidate ranks use original source utility (ranking_value for mean-updated models), while H2 gates "
            "use updated utility. Pair-vector and residual discrepancies report numerical changes without retuning. "
            "Gate changes compare observed selected utility against the corresponding OLD selection and H2 zero. "
            "Aggregates pool complete roots descriptively. No fitting, sampling or heldout tuning occurs here.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.run)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
