"""Longitudinal V77 results with lifecycle-level comparisons and explicit costs."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


LEARNERS = ("FROZEN", "FIXED", "REVISED")
COMPARATORS = ("FIXED_PLAN", "FROZEN_PLAN", "REVISED_DIRECT", "H2_ONLY")


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values else None


def _games_summary(games):
    games = list(games)
    count = len(games)
    statuses = Counter(game["status"] for game in games)
    return dict(games=count,
        means={key: _mean(game[key] for game in games)
               for key in ("score", "utility", "steps", "max_rank", "seconds")},
        status_counts=dict(statuses),
        win_fraction=statuses["WON"] / count if count else None,
        lost_fraction=statuses["LOST"] / count if count else None,
        cutoff_fraction=statuses["CUTOFF"] / count if count else None)


def _key(game):
    return game["seed"], game["replica"], game["query"]


def _paired(left, right):
    first = {_key(game): game for game in left}
    second = {_key(game): game for game in right}
    complete = (len(first) == len(left) and len(second) == len(right)
                and first.keys() == second.keys())
    if not complete:
        return dict(complete=False, pairs=0, mean_delta=None, differences=[])
    differences = [dict(seed=key[0], replica=key[1],
        utility_delta=first[key]["utility"] - second[key]["utility"])
        for key in sorted(first)]
    return dict(complete=True, pairs=len(differences),
        mean_delta=_mean(item["utility_delta"] for item in differences), differences=differences)


def _paired_summary(rows):
    deltas = [row["mean_delta"] for row in rows]
    complete = bool(rows) and all(row["complete"] and row["pairs"] for row in rows)
    usable = [value for value in deltas if value is not None]
    return dict(complete=complete, lifecycles=rows, lifecycle_mean_deltas=deltas,
        mean_delta=_mean(usable) if complete else None,
        positive_lifecycles=sum(value > 0 for value in usable),
        negative_lifecycles=sum(value < 0 for value in usable),
        tied_lifecycles=sum(value == 0 for value in usable),
        all_lifecycles_positive=complete and all(value > 0 for value in usable))


def analyze_run(run):
    settings = run["settings"]
    methods = settings["methods"]
    queries = list(settings["queries"])
    expected_lives = settings["lifecycles"]
    expected_checkpoints = settings["checkpoints"]
    replicas = settings["evaluation_replicas"]
    lives = run["lifecycles"]
    indexed = {life["id"]: {row["episodes"]: row for row in life["checkpoints"]} for life in lives}
    lifecycle_roster_complete = (len(lives) == len(expected_lives)
        and set(indexed) == set(expected_lives)
        and all(len(life["checkpoints"]) == len(expected_checkpoints)
            and {row["episodes"] for row in life["checkpoints"]} == set(expected_checkpoints)
            for life in lives))
    source_complete = lifecycle_roster_complete and all(
        row["source_summary"]["episodes"] == row["episodes"]
        for life in lives for row in life["checkpoints"])
    game_roster_complete = lifecycle_roster_complete and all(
        set(row["methods"]) == set(methods) and all(
            len(row["methods"][method]["games"]) == len(queries) * replicas
            and all(sum(game["query"] == query for game in row["methods"][method]["games"]) == replicas
                    for query in queries)
            for method in methods)
        for life in lives for row in life["checkpoints"])
    all_games = [game for life in lives for row in life["checkpoints"]
                 for method in row["methods"].values() for game in method["games"]]
    eval_terminal = bool(all_games) and all(game["status"] in ("WON", "LOST") for game in all_games)
    control_changes = []
    seed_pairing_complete = True
    for life in expected_lives:
        prefix = indexed[life][expected_checkpoints[0]]["methods"]
        reference_keys = {_key(game) for game in prefix["H2_ONLY"]["games"]}
        for episodes in expected_checkpoints:
            for method in methods:
                games = indexed[life][episodes]["methods"][method]["games"]
                seed_pairing_complete &= len(games) == len(reference_keys) and {
                    _key(game) for game in games} == reference_keys
            for method in ("H2_ONLY", "FROZEN_PLAN"):
                before = {_key(game): game for game in prefix[method]["games"]}
                for game in indexed[life][episodes]["methods"][method]["games"]:
                    previous = before.get(_key(game))
                    if previous is None or any(game[key] != previous[key]
                                               for key in ("score", "status", "steps")):
                        control_changes.append(dict(id=life, episodes=episodes, method=method,
                            seed=game["seed"], replica=game["replica"], query=game["query"]))

    checkpoint_results = []
    for episodes in expected_checkpoints:
        by_method = {}
        for method in methods:
            by_query = {}
            for query in queries:
                per_life = []
                pooled = []
                for life in expected_lives:
                    games = [game for game in indexed[life][episodes]["methods"][method]["games"]
                             if game["query"] == query]
                    pooled.extend(games)
                    per_life.append(dict(id=life, **_games_summary(games)))
                by_query[query] = dict(pooled=_games_summary(pooled), lifecycles=per_life)
            costs = [dict(id=life, **indexed[life][episodes]["methods"][method]["costs"])
                     for life in expected_lives]
            cost_names = indexed[expected_lives[0]][episodes]["methods"][method]["costs"]
            by_method[method] = dict(queries=by_query,
                cumulative_costs=dict(totals={name: math.fsum(row[name] for row in costs)
                                             for name in cost_names}, lifecycles=costs))
        checkpoint_results.append(dict(episodes=episodes, methods=by_method,
            models=[dict(id=life, **indexed[life][episodes]["models"]) for life in expected_lives]))

    final = expected_checkpoints[-1]
    first = expected_checkpoints[0]
    comparisons = {}
    for comparator in COMPARATORS:
        by_query = {}
        for query in queries:
            paired = []
            for life in expected_lives:
                method_results = indexed[life][final]["methods"]
                left = [g for g in method_results["REVISED_PLAN"]["games"] if g["query"] == query]
                right = [g for g in method_results[comparator]["games"] if g["query"] == query]
                paired.append(dict(id=life, **_paired(left, right)))
            by_query[query] = _paired_summary(paired)
        comparisons[comparator] = by_query
    curves = {}
    for method in methods:
        by_query = {}
        for query in queries:
            paired = []
            for life in expected_lives:
                left = [g for g in indexed[life][final]["methods"][method]["games"] if g["query"] == query]
                right = [g for g in indexed[life][first]["methods"][method]["games"] if g["query"] == query]
                paired.append(dict(id=life, **_paired(left, right)))
            by_query[query] = _paired_summary(paired)
        curves[method] = by_query
    pairing_complete = (seed_pairing_complete and
        all(result["complete"] for values in comparisons.values() for result in values.values())
        and all(result["complete"] for values in curves.values() for result in values.values()))

    common_training = Counter()
    update_training = {mode: Counter() for mode in LEARNERS}
    source_counts = Counter()
    eval_counts = {method: dict(environment=Counter(), planning=Counter(), prediction=Counter())
                   for method in methods}
    revisions = []
    source_rows = []
    source_statuses = Counter()
    validation_weighted = {group: {model: [0.0, 0] for model in ("incumbent", "candidate")}
                           for group in ("old", "new")}
    for life in expected_lives:
        checkpoints = indexed[life]
        common_training.update(checkpoints[first]["initialization"]["counts"])
        source = checkpoints[final]["source_summary"]
        source_counts.update(source["work"])
        source_statuses.update(source["outcomes"])
        source_rows.append(dict(id=life, episodes=source["episodes"], records=source["records"],
            work=source["work"], policy_work=source["policy_work"], seconds=source["seconds"],
            warmup_seconds=source["warmup_seconds"], outcomes=source["outcomes"],
            by_policy=source["by_policy"], exact_teacher_calls=source["exact_teacher_calls"]))
        for episodes in expected_checkpoints:
            row = checkpoints[episodes]
            for mode, update in row["updates"].items():
                update_training[mode].update(update.get("counts", {}))
                if mode != "REVISED":
                    continue
                for policy, result in update.get("policies", {}).items():
                    revisions.append(dict(id=life, episodes=episodes, policy=policy, **result))
                    for group in ("old", "new"):
                        count = result["validation_rows"][group]
                        for model in ("incumbent", "candidate"):
                            loss = result["validation_mse"][group][model]
                            if loss is not None:
                                entry = validation_weighted[group][model]
                                entry[0] += count * loss
                                entry[1] += count
            for method in methods:
                for game in row["methods"][method]["games"]:
                    for group, field in (("environment", "environment_counts"),
                                         ("planning", "planning_counts"),
                                         ("prediction", "prediction_counts")):
                        eval_counts[method][group].update(game[field])
    accepted = [row for row in revisions if row["accepted"]]
    revisions_summary = dict(proposals=len(revisions), accepted=len(accepted),
        rejected=len(revisions) - len(accepted),
        accepted_structure_changes=sum(row["structure_changed"] for row in accepted),
        validation_row_weighted_mse={group: {model: dict(rows=count, mean_mse=total / count if count else None)
            for model, (total, count) in models.items()} for group, models in validation_weighted.items()},
        events=revisions,
        scope="Validation rows can reappear in the old prefix at later updates; these are loss evaluations, not independent samples.")
    quality = {query: comparisons["FIXED_PLAN"][query]["all_lifecycles_positive"] for query in queries}
    source_terminal = (sum(source_statuses.values()) == sum(row["episodes"] for row in source_rows)
                       and not any(count for status, count in source_statuses.items()
                                   if status not in ("WON", "LOST")))
    all_terminal = eval_terminal and source_terminal
    empirical_evidence = bool(revisions_summary["accepted_structure_changes"] and
        any(quality.values()) and pairing_complete and game_roster_complete and not control_changes)
    return dict(schema="acfqp.lifelong_analysis.v77", complete=run["status"] == "complete" and
            lifecycle_roster_complete and game_roster_complete and pairing_complete and not control_changes,
        lifecycle_ids=expected_lives, evaluation_replicas=replicas, query_names=queries,
        cohort=dict(source_streams_complete=source_complete,
                    evaluation_games_complete=game_roster_complete,
                    paired_evaluation_seeds_complete=pairing_complete,
                    fixed_controls_unchanged=not control_changes, fixed_control_changes=control_changes,
                    all_games_terminal=all_terminal, games=len(all_games),
                    all_evaluation_games_terminal=eval_terminal, all_source_games_terminal=source_terminal,
                    source_games=sum(source_statuses.values()), source_status_counts=dict(source_statuses),
                    status_counts=dict(Counter(game["status"] for game in all_games))),
        checkpoints=checkpoint_results,
        final_revised_plan_minus_comparator=comparisons,
        first_to_last_checkpoint_utility_change=curves,
        structure_updates=revisions_summary,
        actual_executed_work=dict(source_once_counts=dict(source_counts), source_lifecycles=source_rows,
            source_records=sum(row["records"] for row in source_rows),
            common_initialization_once_counts=dict(common_training),
            knowledge_update_counts={mode: dict(counts) for mode, counts in update_training.items()},
            evaluation={method: {group: dict(counts) for group, counts in groups.items()}
                        for method, groups in eval_counts.items()},
            actual_wall_seconds=run["actual_wall_seconds"],
            source_sampled_transitions=source_counts["sampled_transitions"],
            evaluation_sampled_transitions=sum(groups["environment"]["sampled_transitions"]
                                               for groups in eval_counts.values()),
            imagined_model_spawn_samples=sum(groups["planning"]["model_spawn_samples"]
                                               for groups in eval_counts.values()),
            tree_fits=common_training["tree_fits"] +
                      sum(counts["tree_fits"] for counts in update_training.values())),
        signals=dict(quality_gain_over_fixed_all_lifecycles_by_query=quality,
            source_streams_complete=source_complete, all_games_terminal=all_terminal,
            observed_evidence_for_further_partition_revision=empirical_evidence),
        evidence_scope="Paired utility changes are summarized within each independent source lifecycle first. "
            "Evaluation replicas and repeated checkpoints are not independent learning runs; no confidence interval is inferred.",
        cost_scope="Method costs are cumulative at each checkpoint. Shared source and initialization work is attributed "
            "to each method that needs it; attributed method costs must not be summed as actual executed cost. "
            "Actual source counts use only each final prefix, initialization is counted once, and all newly executed evaluation games are counted.",
        learning_scope="First-to-last changes reuse the same evaluation seeds and establish no extrapolation beyond these checkpoints. "
            "Accepted proposals revise partitions of fixed features and policies, not the learning algorithm or mechanisms.")


def analyze(directory):
    return analyze_run(json.loads((Path(directory) / "run.json").read_text()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.directory)
    output = args.output or args.directory / "analysis.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(complete=result["complete"], cohort=result["cohort"],
        signals=result["signals"], revised_minus_fixed={query: row["lifecycle_mean_deltas"]
        for query, row in result["final_revised_plan_minus_comparator"]["FIXED_PLAN"].items()},
        revisions={key: result["structure_updates"][key]
                   for key in ("proposals", "accepted", "rejected", "accepted_structure_changes")})))
