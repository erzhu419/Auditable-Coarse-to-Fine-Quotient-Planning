"""Summarize on-policy paired-action improvement across independent V81 lives."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


CONTROLS = ("H2_ONLY", "FROZEN_1", "SHORT_REF", "TERMINAL_REF")
METRICS = ("score", "utility", "steps", "max_rank", "seconds")


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values else None


def _key(game):
    return game["seed"], game["replica"], game["query"]


def _summary(games):
    outcomes = Counter(game["status"] for game in games)
    decisions = sum(game.get("decisions", 0) for game in games)
    overrides = sum(game.get("top_layer_overrides", 0) for game in games)
    return dict(games=len(games), means={name: _mean(g[name] for g in games)
        for name in METRICS}, status_counts=dict(outcomes),
        terminal_games=outcomes["WON"] + outcomes["LOST"],
        cutoff_games=outcomes["CUTOFF"],
        top_layer_overrides=overrides, decisions=decisions,
        top_layer_override_rate=overrides / decisions if decisions else None,
        win_fraction=outcomes["WON"] / len(games) if games else None)


def _paired(left, right, replicas):
    first, second = {_key(g): g for g in left}, {_key(g): g for g in right}
    complete = (len(left) == len(right) == len(first) == len(second) == replicas
                and first.keys() == second.keys())
    return dict(complete=complete, pairs=len(first) if complete else 0,
        **{f"mean_{metric}_delta": _mean(first[key][metric] - second[key][metric]
            for key in first) if complete else None for metric in ("utility", "score")})


def _comparison(rows):
    complete = bool(rows) and all(row["complete"] for row in rows)
    deltas = [row["mean_utility_delta"] for row in rows]
    return dict(complete=complete, lifecycles=rows, lifecycle_mean_deltas=deltas,
        mean_delta=_mean(deltas) if complete else None,
        mean_score_delta=_mean(row["mean_score_delta"] for row in rows) if complete else None,
        positive_lifecycles=sum(value is not None and value > 0 for value in deltas),
        negative_lifecycles=sum(value is not None and value < 0 for value in deltas))


def _same_outcomes(left, right):
    first, second = {_key(g): g for g in left}, {_key(g): g for g in right}
    return (len(left) == len(first) == len(right) == len(second) and bool(first)
        and first.keys() == second.keys()
        and all(all(first[key][field] == second[key][field]
            for field in ("score", "utility", "status", "steps", "max_rank")) for key in first))


def analyze_run(run):
    settings = run["settings"]
    lives, iterations = settings["lifecycles"], settings["iterations"]
    methods, queries = settings["methods"], list(settings["queries"])
    replicas = settings["evaluation_replicas"]
    actual_lives = run["lifecycles"]
    indexed = {life["id"]: {row["iteration"]: row for row in life["rounds"]}
               for life in actual_lives}
    roster = (len(actual_lives) == len(lives) and set(indexed) == set(lives)
        and all(len(life["rounds"]) == len(iterations)
            and {row["iteration"] for row in life["rounds"]} == set(iterations)
            for life in actual_lives))

    def stage(life, iteration):
        return indexed.get(life, {}).get(iteration, {})

    def games(life, iteration, method, query=None):
        rows = stage(life, iteration).get("methods", {}).get(method, {}).get("games", [])
        return [g for g in rows if query is None or g["query"] == query]

    game_roster, paired = roster, roster
    control_changes, first_round_changes, query_histories = [], [], []
    results = []
    for iteration in iterations:
        by_method = {}
        for life in lives:
            reference = games(life, iterations[0], "H2_ONLY")
            reference_keys = {_key(g) for g in reference}
            game_roster &= set(stage(life, iteration).get("methods", {})) == set(methods)
            for method in methods:
                rows = games(life, iteration, method)
                game_roster &= (len(rows) == len(queries) * replicas
                    and {(g["query"], g["replica"]) for g in rows}
                    == {(q, r) for q in queries for r in range(replicas)})
                paired &= (len(rows) == len(reference_keys)
                           and {_key(g) for g in rows} == reference_keys)
                if method in CONTROLS and not _same_outcomes(
                        games(life, iterations[0], method), rows):
                    control_changes.append(dict(id=life, iteration=iteration, method=method))
                retained = stage(life, iteration).get("query_response", {}).get(method)
                query_histories.append(dict(id=life, iteration=iteration, method=method,
                    complete=retained is not None and retained["pairs"] == replicas,
                    pairs=retained["pairs"] if retained is not None else 0,
                    identical_trajectory_pairs=retained["identical_trajectory_pairs"]
                        if retained is not None else None))
            if iteration == iterations[0] and not _same_outcomes(
                    games(life, iteration, "CURRENT"), games(life, iteration, "FROZEN_1")):
                first_round_changes.append(dict(id=life, iteration=iteration))
        for method in methods:
            costs = [dict(id=life, **stage(life, iteration).get("methods", {})
                          .get(method, {}).get("costs", {})) for life in lives]
            names = set().union(*(row.keys() for row in costs)) - {"id"}
            by_method[method] = dict(queries={query: dict(
                pooled=_summary([g for life in lives for g in games(life, iteration, method, query)]),
                lifecycles=[dict(id=life, **_summary(games(life, iteration, method, query))) for life in lives])
                for query in queries}, cumulative_costs=dict(lifecycles=costs,
                    totals={name: math.fsum(row[name] for row in costs) if all(name in row for row in costs)
                            else None for name in sorted(names)}))
        results.append(dict(iteration=iteration, methods=by_method))

    comparisons = {f"CURRENT_minus_{other}": {query: _comparison([
        dict(id=life, **_paired(games(life, iterations[-1], "CURRENT", query),
            games(life, iterations[-1], other, query), replicas)) for life in lives])
        for query in queries} for other in CONTROLS}
    learning = {method: {query: _comparison([dict(id=life, **_paired(
        games(life, iterations[-1], method, query), games(life, iterations[0], method, query), replicas))
        for life in lives]) for query in queries} for method in methods}
    work = _work_and_labels(run, lives, iterations, methods, stage, games)
    all_games = [game for life in actual_lives for row in life["rounds"]
                 for method in row.get("methods", {}).values() for game in method["games"]]
    complete = (run["status"] == "complete" and roster and game_roster and paired
                and not control_changes and not first_round_changes and work["parent_lineage_complete"]
                and work["source_streams_complete"])
    return dict(schema="acfqp.policy_iteration_analysis.v81", complete=complete,
        cohort=dict(lifecycle_roster_complete=roster, evaluation_games_complete=game_roster,
            paired_evaluation_seeds_complete=paired, fixed_controls_unchanged=not control_changes,
            fixed_control_changes=control_changes, first_round_current_matches_frozen=not first_round_changes,
            first_round_changes=first_round_changes, parent_lineage_complete=work["parent_lineage_complete"],
            source_streams_complete=work["source_streams_complete"],
            expected_games=len(lives) * len(iterations) * len(methods) * len(queries) * replicas,
            all_evaluation_games_terminal=bool(all_games) and all(g["status"] in ("WON", "LOST") for g in all_games),
            **_summary(all_games)), iterations=results, final_comparisons=comparisons,
        first_to_last_iteration_utility_change=learning, learning_sources=work["learning_sources"],
        actual_executed_work=work["actual_executed_work"],
        paired_query_trajectories=dict(rows=query_histories,
            complete=bool(query_histories) and all(row["complete"] for row in query_histories),
            pairs=sum(row["pairs"] for row in query_histories),
            identical_trajectory_pairs=sum(row["identical_trajectory_pairs"] or 0 for row in query_histories),
            by_method={method: dict(pairs=sum(row["pairs"] for row in query_histories if row["method"] == method),
                identical_trajectory_pairs=sum(row["identical_trajectory_pairs"] or 0
                    for row in query_histories if row["method"] == method)) for method in methods}),
        evidence_scope="Completeness describes execution and pairing, not policy improvement. "
            "Within-lifecycle paired means precede averaging across three independent lifecycles; "
            "these results do not establish significance. Query trajectory differences are response, not optimality. "
            "V80 references differ in architecture and experience as well as labels. Their inherited training "
            "cost is separate from new V81 sampling. Shared method cost attributions must not be summed as actual "
            "execution cost. A terminal advantage under the parent policy does not guarantee the return of "
            "the revised policy that changes later actions.")


def _work_and_labels(run, lives, iterations, methods, stage, games):
    behavior_work, behavior_planning = Counter(), Counter()
    branch_work, continuation_work, branch_known_model = Counter(), Counter(), Counter()
    behavior_outcomes, branch_outcomes, source_counts, model_fit = Counter(), Counter(), Counter(), Counter()
    evaluation = {method: {name: Counter() for name in ("environment", "planning", "prediction")}
                  for method in methods}
    noise_pairs, sign_reversals, noise_sums = 0, 0, [0.0, 0.0, 0.0]
    label_totals, source_rows = Counter(), []
    parent_lineage, source_complete = True, True
    for life in lives:
        for iteration in iterations:
            row = stage(life, iteration)
            behavior, branches = row.get("behavior", {}), row.get("branches", {})
            dataset, update = row.get("dataset", {}), row.get("update", {})
            lineage = (behavior.get("policy_iteration") == branches.get("continuation_iteration")
                == update.get("parent_iteration") == iteration - 1
                and update.get("iteration") == iteration)
            parent_lineage &= lineage
            source_complete &= (behavior.get("games") == len(run["settings"]["queries"]) * 12
                and sum(behavior.get("outcomes", {}).values()) == behavior.get("games")
                and sum(branches.get("outcomes", {}).values()) == branches.get("trajectories")
                and dataset.get("records") == update.get("input_records")
                and dataset.get("training_records") == update.get("training_records")
                and dataset.get("heldout_records") == update.get("heldout_records"))
            behavior_work.update(behavior.get("work", {}))
            behavior_planning.update(behavior.get("planning_counts", {}))
            branch_work.update(branches.get("work", {}))
            continuation_work.update(branches.get("continuation_work", {}))
            branch_known_model.update(branches.get("known_model_counts", {}))
            behavior_outcomes.update(behavior.get("outcomes", {}))
            branch_outcomes.update(branches.get("outcomes", {}))
            source_counts["behavior_games"] += behavior.get("games", 0)
            for name in ("roots", "trajectories", "censored_roots"):
                source_counts[name] += branches.get(name, 0)
            model_fit.update(update.get("counts", {}))
            for name in ("records", "training_records", "heldout_records"):
                label_totals[name] += dataset.get(name, 0)
            for query in dataset.get("queries", {}).values():
                for name in ("nonzero_failure_deltas", "nonzero_success_deltas"):
                    label_totals[name] += query.get(name, 0)
            noise = dataset.get("replica_noise", {})
            n = noise.get("pairs", 0)
            noise_pairs += n
            sign_reversals += noise.get("reward_sign_reversals", 0)
            if n:
                for component, value in enumerate(noise["mean_abs_component_difference"]):
                    noise_sums[component] += n * value
            source_rows.append(dict(id=life, iteration=iteration, correct_parent=lineage,
                behavior={key: behavior.get(key) for key in
                    ("policy_iteration", "games", "outcomes", "state_coverage")},
                branches={key: branches.get(key) for key in
                    ("continuation_iteration", "roots", "trajectories", "censored_roots", "outcomes")},
                dataset=dataset, update=update))
            for method in methods:
                for game in games(life, iteration, method):
                    for group in evaluation[method]:
                        evaluation[method][group].update(game.get(f"{group}_counts", {}))
    label_totals = dict(label_totals)
    labels = dict(**label_totals, replica_noise=dict(pairs=noise_pairs,
        mean_abs_component_difference=[value / noise_pairs for value in noise_sums] if noise_pairs else None,
        reward_sign_reversals=sign_reversals,
        reward_sign_reversal_fraction=sign_reversals / noise_pairs if noise_pairs else None))
    return dict(parent_lineage_complete=bool(source_rows) and parent_lineage,
        source_streams_complete=bool(source_rows) and source_complete,
        learning_sources=dict(rounds=source_rows, totals=labels),
        actual_executed_work=dict(**source_counts, behavior_outcomes=dict(behavior_outcomes),
            branch_outcomes=dict(branch_outcomes), new_behavior_counts=dict(behavior_work),
            behavior_planning_counts=dict(behavior_planning), new_branch_counts=dict(branch_work),
            branch_continuation_counts=dict(continuation_work), branch_known_model_counts=dict(branch_known_model),
            new_model_fit_counts=dict(model_fit),
            evaluation={method: {group: dict(counts) for group, counts in groups.items()}
                        for method, groups in evaluation.items()},
            newly_sampled_transitions=behavior_work["sampled_transitions"] + branch_work["sampled_transitions"]
                + sum(groups["environment"]["sampled_transitions"] for groups in evaluation.values()),
            inherited_reference_training="V80 SHORT_REF and TERMINAL_REF acquisition/fitting are charged "
                "in each method's inherited cost fields, not sampled again or added to new V81 transitions.",
            actual_wall_seconds=run.get("actual_wall_seconds")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"complete": result["complete"], "games": result["cohort"]["games"],
        "final_current_minus_h2": result["final_comparisons"]["CURRENT_minus_H2_ONLY"]}))


if __name__ == "__main__":
    main()
