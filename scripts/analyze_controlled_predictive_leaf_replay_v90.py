"""Fresh paired replay of fixed V89 targets and their actual training leaf members."""
from collections import Counter
import argparse
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from acfqp.science.controlled_predictive_fragments_v83 import QUERIES, _utility

TERMINAL = {"WON", "LOST"}
WIRING = ("model_uniforms_aligned", "single_initiations", "committed_lengths_match")


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values else None


def _band(mean, variance):
    se = math.sqrt(variance)
    lower, upper = mean - 2 * se, mean + 2 * se
    return dict(mean_utility=mean, variance_of_mean=variance, standard_error=se,
        two_se_lower=lower, two_se_upper=upper,
        status="positive" if lower > 0 else "negative" if upper < 0 else "unresolved",
        mean_score_delta=2048 * mean, score_standard_error=2048 * se,
        two_se_score_lower=2048 * lower, two_se_score_upper=2048 * upper)


def _samples(pairs, query):
    vectors = [pair["target"] for pair in pairs]
    if not vectors:
        return None
    utilities = [_utility(vector, QUERIES[query]) for vector in vectors]
    mean_rfs = [_mean(vector[index] for vector in vectors) for index in range(3)]
    if len(utilities) < 2:
        return dict(n=len(utilities), mean_rfs=mean_rfs, mean_utility=utilities[0],
            mean_score_delta=2048 * utilities[0], sample_variance=None, variance_of_mean=None)
    sample_variance = statistics.variance(utilities)
    return dict(n=len(utilities), mean_rfs=mean_rfs, sample_variance=sample_variance,
        **_band(_mean(utilities), sample_variance / len(utilities)))


def _weighted(root_index, weights):
    if not weights or any(root_index[root_id]["estimate"] is None for root_id in weights):
        return None
    estimates = {root_id: root_index[root_id]["estimate"] for root_id in weights}
    mean = math.fsum(weight * estimates[root_id]["mean_utility"] for root_id, weight in weights.items())
    variance = math.fsum(weight ** 2 * estimates[root_id]["variance_of_mean"]
        for root_id, weight in weights.items())
    return dict(roots=len(weights), mean_rfs=[math.fsum(weight * estimates[root_id]["mean_rfs"][index]
        for root_id, weight in weights.items()) for index in range(3)], **_band(mean, variance))


def _comparison(target, training):
    if target is None or training is None:
        return dict(estimable=False, target=target, training=training, difference=None,
            opposite_mean_signs=None, opposite_two_se_signs=None)
    return dict(estimable=True, target=target, training=training,
        difference=_band(target["mean_utility"] - training["mean_utility"],
            target["variance_of_mean"] + training["variance_of_mean"]),
        opposite_mean_signs=target["mean_utility"] * training["mean_utility"] < 0,
        opposite_two_se_signs=(target["two_se_upper"] < 0 < training["two_se_lower"]
            or training["two_se_upper"] < 0 < target["two_se_lower"]))


def analyze_run(run, cohort):
    settings = run["settings"]
    replicas, max_steps = settings["replicas"], settings["max_steps"]
    roots = cohort["targets"] + cohort["controls"]
    root_ids = [root["id"] for root in roots]
    declared = {root["id"]: root for root in roots}
    logs = {row["root_id"]: row for row in run["roots"]}
    checks = dict(frozen_cohort_checks=all(value is True for value in cohort["checks"].values()),
        root_roster_complete=len(root_ids) == len(declared) == len(logs) == len(run["roots"])
            and set(declared) == set(logs),
        reward_query_only=all(root["query"] == "reward" for root in roots),
        replica_rosters_complete=True, pair_terminal_labels_consistent=True,
        controller_wiring_complete=True, transition_and_model_draw_counts_match=True,
        independent_root_seed_rosters=True, life_specific_leaf_groups=True)
    ground, planning, outcomes = Counter(), Counter(), Counter()
    trajectories = complete_pairs = seconds = 0
    for row in run["roots"]:
        ground.update(row["ground_work"])
        planning.update(row["planning_counts"])
        outcomes.update(row["outcomes"])
        trajectories += row["trajectories"]
        complete_pairs += row["complete_pairs"]
        seconds += row["seconds"]
    seed_roots, statistics_rows = {}, []
    for root in roots:
        log = logs.get(root["id"])
        if log is None:
            statistics_rows.append(dict(**root, observed_pairs=0, complete_pairs=0,
                estimable=False, estimate=None, complete_pairs_descriptive=None))
            continue
        pairs = log["pairs"]
        usable = [pair for pair in pairs if pair["complete_pair"]]
        roster = (log["requested_replicas"] == replicas and len(pairs) == replicas
            and sorted(pair["replica"] for pair in pairs) == list(range(replicas))
            and log["complete_pairs"] == len(usable) and log["trajectories"] == 2 * replicas)
        checks["replica_rosters_complete"] &= roster
        for pair in pairs:
            terminal = pair["candidate_status"] in TERMINAL and pair["reference_status"] in TERMINAL
            checks["pair_terminal_labels_consistent"] &= (pair["complete_pair"] == terminal
                and ((pair["target"] is not None and len(pair["target"]) == 3) if terminal else pair["target"] is None))
            checks["independent_root_seed_rosters"] &= pair["seed"] not in seed_roots
            seed_roots[pair["seed"]] = root["id"]
        transitions = log["ground_work"]["sampled_transitions"]
        checks["controller_wiring_complete"] &= all(log["wiring"].get(key) is True for key in WIRING)
        checks["transition_and_model_draw_counts_match"] &= (0 < transitions <= log["trajectories"] * max_steps
            and log["planning_counts"]["model_uniform_draws"] == 4 * transitions
            and sum(log["outcomes"].values()) == log["trajectories"])
        descriptive = _samples(usable, root["query"])
        estimable = roster and len(usable) == replicas and replicas >= 2
        statistics_rows.append(dict(**root, requested_replicas=replicas, observed_pairs=len(pairs),
            complete_pairs=len(usable), estimable=estimable, estimate=descriptive if estimable else None,
            complete_pairs_descriptive=descriptive))
    root_index = {row["id"]: row for row in statistics_rows}
    target_ids = [root["id"] for root in cohort["targets"]]
    training_ids = [root["id"] for root in cohort["controls"]]
    grouped_targets, grouped_training, group_ids = [], [], []
    group_rows, overall_target_weights, overall_training_weights = [], {}, {}
    total_targets = len(target_ids)
    for group in cohort["groups"]:
        group_ids.append(group["id"])
        targets, training = group["target_ids"], group["training_ids"]
        grouped_targets.extend(targets)
        grouped_training.extend(training)
        checks["life_specific_leaf_groups"] &= bool(targets and training) and all(
            root_id in declared and all(declared[root_id][name] == group[name]
                for name in ("life", "query", "leaf", "option")) for root_id in targets + training)
        target_weights = {root_id: 1 / len(targets) for root_id in targets}
        training_weights = {root_id: 1 / len(training) for root_id in training}
        group_weight = len(targets) / total_targets
        overall_target_weights.update({root_id: group_weight * weight for root_id, weight in target_weights.items()})
        overall_training_weights.update({root_id: group_weight * weight for root_id, weight in training_weights.items()})
        comparison = _comparison(_weighted(root_index, target_weights), _weighted(root_index, training_weights))
        prediction = group["predicted_utility"]
        group_rows.append(dict(**group, target_weights=target_weights, training_weights=training_weights,
            overall_group_weight=group_weight, **comparison,
            prediction_minus_fresh_target=prediction - comparison["target"]["mean_utility"] if comparison["target"] else None,
            prediction_minus_fresh_training=prediction - comparison["training"]["mean_utility"] if comparison["training"] else None))
    checks["life_specific_leaf_groups"] &= (len(set(group_ids)) == len(group_ids)
        and sorted(grouped_targets) == sorted(target_ids) and sorted(grouped_training) == sorted(training_ids)
        and len(set(grouped_targets)) == len(grouped_targets) and len(set(grouped_training)) == len(grouped_training))
    overall = _comparison(_weighted(root_index, overall_target_weights), _weighted(root_index, overall_training_weights))
    old_mean = _mean(root["v89_utility_delta"] for root in cohort["targets"])
    overall.update(target_weights=overall_target_weights, training_weights=overall_training_weights,
        old_v89_selected_target_mean_utility=old_mean,
        old_v89_selected_target_mean_score_delta=2048 * old_mean,
        fresh_target_minus_old_utility=overall["target"]["mean_utility"] - old_mean if overall["target"] else None,
        fresh_target_minus_old_score_delta=2048 * (overall["target"]["mean_utility"] - old_mean) if overall["target"] else None)
    primary_estimable = all(row["estimable"] for row in statistics_rows) and overall["estimable"]
    return dict(schema="acfqp.leaf_replay_analysis.v90",
        complete=run["status"] == "complete" and all(checks.values()), primary_estimable=primary_estimable,
        cohort_checks=checks, root_statistics=statistics_rows, groups=group_rows, overall=overall,
        work=dict(ground_work=dict(ground), planning_counts=dict(planning), outcomes=dict(outcomes),
            trajectories=trajectories, planned_trajectories=2 * replicas * len(roots),
            requested_pairs=replicas * len(roots), complete_pairs=complete_pairs,
            incomplete_pairs=replicas * len(roots) - complete_pairs,
            sampled_transitions=ground["sampled_transitions"], root_seconds_sum=seconds,
            actual_wall_seconds=run["actual_wall_seconds"], new_tree_fits=0, new_source_games=0,
            new_natural_episodes=0), inherited=run.get("inherited", {}),
        evidence_scope="Fixed selected V89 roots and their actual training leaf members; all primary roots require "
            "the full fixed terminal-pair count. Two-SE bands describe Monte Carlo sampling uncertainty for this "
            "fixed cohort, not calibrated confidence intervals or population generalization. Each unique training "
            "root is sampled and weighted once; old selected outcomes are compared separately, never pooled.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()),
        json.loads((args.directory / "cohort.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(complete=result["complete"], primary_estimable=result["primary_estimable"],
        overall=result["overall"], work=result["work"]), allow_nan=False))


if __name__ == "__main__":
    main()
