"""Compare matched short and terminal targets using independent V80 lifecycles."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


COMPARISONS = (
    ("TERMINAL_PLAN", "SHORT_PLAN"),
    ("SHORT_PLAN", "SHORT_FROZEN"),
    ("TERMINAL_PLAN", "TERMINAL_FROZEN"),
    ("SHORT_PLAN", "H2_ONLY"),
    ("TERMINAL_PLAN", "H2_ONLY"),
)
CONTROLS = ("H2_ONLY", "SHORT_FROZEN", "TERMINAL_FROZEN")


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values else None


def _key(game):
    return game["seed"], game["replica"], game["query"]


def _summary(games):
    statuses = Counter(g["status"] for g in games)
    return dict(games=len(games), means={name: _mean(g[name] for g in games)
        for name in ("score", "utility", "steps", "max_rank", "seconds")},
        status_counts=dict(statuses), terminal_games=statuses["WON"] + statuses["LOST"],
        cutoff_games=statuses["CUTOFF"],
        win_fraction=statuses["WON"] / len(games) if games else None)


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


def analyze_run(run):
    settings = run["settings"]
    lives, checkpoints = settings["lifecycles"], settings["checkpoints"]
    methods, queries = settings["methods"], list(settings["queries"])
    replicas = settings["evaluation_replicas"]
    actual_lives = run["lifecycles"]
    indexed = {life["id"]: {row["episodes"]: row for row in life["stages"]}
               for life in actual_lives}
    roster = (len(actual_lives) == len(lives) and set(indexed) == set(lives)
        and all(len(life["stages"]) == len(checkpoints)
            and {row["episodes"] for row in life["stages"]} == set(checkpoints)
            for life in actual_lives))

    def stage(life, episodes):
        return indexed.get(life, {}).get(episodes, {})

    def games(life, episodes, method, query=None):
        rows = stage(life, episodes).get("methods", {}).get(method, {}).get("games", [])
        return [g for g in rows if query is None or g["query"] == query]

    game_roster, paired = roster, roster
    control_changes, query_outcomes, query_histories = [], [], []
    for life in lives:
        reference = games(life, checkpoints[0], "H2_ONLY")
        reference_keys = {_key(g) for g in reference}
        for episodes in checkpoints:
            game_roster &= set(stage(life, episodes).get("methods", {})) == set(methods)
            for method in methods:
                rows = games(life, episodes, method)
                game_roster &= (len(rows) == len(queries) * replicas
                    and {(g["query"], g["replica"]) for g in rows}
                    == {(q, r) for q in queries for r in range(replicas)})
                paired &= (len(rows) == len(reference_keys)
                           and {_key(g) for g in rows} == reference_keys)
                if method in CONTROLS:
                    before = {_key(g): g for g in games(life, checkpoints[0], method)}
                    after = {_key(g): g for g in rows}
                    changed = before.keys() != after.keys() or any(
                        any(g[name] != before[key][name] for name in ("score", "utility", "status", "steps"))
                        for key, g in after.items() if key in before)
                    if changed:
                        control_changes.append(dict(id=life, episodes=episodes, method=method))
                query_maps = {query: {(g["seed"], g["replica"]): g
                    for g in rows if g["query"] == query} for query in queries}
                query_keys = [set(mapping) for mapping in query_maps.values()]
                complete_pair = (all(len(keys) == replicas for keys in query_keys)
                                 and all(keys == query_keys[0] for keys in query_keys))
                equal = sum(all(all(mapping[key][field] == query_maps[queries[0]][key][field]
                    for field in ("score", "status", "steps", "max_rank"))
                    for mapping in query_maps.values()) for key in query_keys[0]) if complete_pair else None
                query_outcomes.append(dict(id=life, episodes=episodes, method=method,
                    complete=complete_pair, pairs=replicas if complete_pair else 0,
                    identical_outcomes=equal))
                retained = stage(life, episodes).get("query_response", {}).get(method)
                query_histories.append(dict(id=life, episodes=episodes, method=method,
                    complete=retained is not None and retained["pairs"] == replicas,
                    pairs=retained["pairs"] if retained is not None else 0,
                    identical_trajectory_pairs=retained["identical_trajectory_pairs"]
                        if retained is not None else None))

    results = []
    for episodes in checkpoints:
        by_method = {}
        for method in methods:
            costs = [dict(id=life, **stage(life, episodes).get("methods", {})
                          .get(method, {}).get("costs", {})) for life in lives]
            names = set().union(*(row.keys() for row in costs)) - {"id"}
            by_method[method] = dict(queries={query: dict(
                pooled=_summary([g for life in lives for g in games(life, episodes, method, query)]),
                lifecycles=[dict(id=life, **_summary(games(life, episodes, method, query))) for life in lives])
                for query in queries}, cumulative_costs=dict(lifecycles=costs,
                    totals={name: math.fsum(row[name] for row in costs) if all(name in row for row in costs)
                            else None for name in sorted(names)}))
        results.append(dict(episodes=episodes, methods=by_method))

    comparisons = {f"{left}_minus_{right}": {query: _comparison([
        dict(id=life, **_paired(games(life, checkpoints[-1], left, query),
            games(life, checkpoints[-1], right, query), replicas)) for life in lives])
        for query in queries} for left, right in COMPARISONS}
    learning = {method: {query: _comparison([dict(id=life, **_paired(
        games(life, checkpoints[-1], method, query), games(life, checkpoints[0], method, query), replicas))
        for life in lives]) for query in queries} for method in methods}
    work = _work_and_labels(run, lives, checkpoints, methods, stage, games)
    all_games = [game for life in actual_lives for row in life["stages"]
                 for method in row.get("methods", {}).values() for game in method["games"]]
    source_complete = roster and all(stage(life, episodes).get("source_summary", {}).get("episodes") == episodes
                                    for life in lives for episodes in checkpoints)
    complete = (run["status"] == "complete" and roster and game_roster and paired
                and source_complete and not control_changes and work["matched_training_rows"])
    return dict(schema="acfqp.target_horizon_analysis.v80", complete=complete,
        cohort=dict(lifecycle_roster_complete=roster, source_streams_complete=source_complete,
            evaluation_games_complete=game_roster, paired_evaluation_seeds_complete=paired,
            fixed_controls_unchanged=not control_changes, fixed_control_changes=control_changes,
            matched_training_rows=work["matched_training_rows"],
            expected_games=len(lives) * len(checkpoints) * len(methods) * len(queries) * replicas,
            all_evaluation_games_terminal=bool(all_games) and all(g["status"] in ("WON", "LOST") for g in all_games),
            **_summary(all_games)), checkpoints=results,
        final_comparisons=comparisons, first_to_last_checkpoint_utility_change=learning,
        labels=work["labels"], actual_executed_work=work["actual_executed_work"],
        paired_query_outcomes=dict(rows=query_outcomes,
            complete=all(row["complete"] for row in query_outcomes),
            pairs=sum(row["pairs"] for row in query_outcomes),
            identical_outcomes=sum(row["identical_outcomes"] or 0 for row in query_outcomes),
            interpretation="Equal game summaries do not establish equal action histories or query invariance."),
        paired_query_trajectories=dict(rows=query_histories,
            complete=all(row["complete"] for row in query_histories),
            pairs=sum(row["pairs"] for row in query_histories),
            identical_trajectory_pairs=sum(row["identical_trajectory_pairs"] or 0 for row in query_histories),
            by_method={method: dict(
                pairs=sum(row["pairs"] for row in query_histories if row["method"] == method),
                identical_trajectory_pairs=sum(row["identical_trajectory_pairs"] or 0
                    for row in query_histories if row["method"] == method)) for method in methods},
            interpretation="Runner compares every board, action and next board for paired query games; "
                "agreement establishes observed trajectory equality, not optimality or improved risk."),
        evidence_scope="Completeness describes execution and pairing, not scientific success. Within-lifecycle paired "
            "means precede averaging across independent lifecycles; three lifecycles do not establish significance. "
            "Short and terminal models fit the same eligible rows; censored trajectories are excluded from terminal "
            "labels. Inherited source and branch prefixes are separate from newly sampled suffixes and evaluations. "
            "Shared method cost attributions must not be summed as actual execution cost. Policy-conditioned terminal "
            "targets do not certify the outcome of a replanning policy.")


def _work_and_labels(run, lives, checkpoints, methods, stage, games):
    source_work, model_work = Counter(), Counter()
    branch_prefix, branch_suffix, branch_policy = Counter(), Counter(), Counter()
    branch_outcomes, prefix_outcomes, branch_totals = Counter(), Counter(), Counter()
    source_rows, labels = [], []
    matched = True
    evaluation = {method: {name: Counter() for name in ("environment", "planning", "prediction")}
                  for method in methods}
    for life in lives:
        source = stage(life, checkpoints[-1]).get("source_summary", {})
        source_work.update(source.get("work", {}))
        source_rows.append(dict(id=life, **source))
        for episodes in checkpoints:
            row = stage(life, episodes)
            models = row.get("models", {})
            logs = {scope: models.get(scope, {}).get("fit_log", {}) for scope in ("SHORT", "TERMINAL")}
            short, terminal = logs["SHORT"], logs["TERMINAL"]
            fields = ("input_records", "prefix_records", "future_records_excluded",
                      "training_records", "heldout_records", "feature_context_horizon")
            row_match = (bool(short) and bool(terminal) and all(name in short and name in terminal
                and short[name] == terminal[name] for name in fields)
                and short.get("checkpoint") == terminal.get("checkpoint") == episodes
                and short.get("target_scope") == "SHORT" and terminal.get("target_scope") == "TERMINAL"
                and set(short.get("policies", {})) == set(terminal.get("policies", {}))
                and all(all(short["policies"][policy][name] == terminal["policies"][policy][name]
                    for name in ("training_rows", "heldout_rows")) for policy in short.get("policies", {})))
            matched &= row_match
            target_means = {scope: {policy: values["training_target_mean"]
                for policy, values in log.get("policies", {}).items()} for scope, log in logs.items()}
            labels.append(dict(id=life, episodes=episodes, matched_fit_row_counts=row_match,
                dataset=row.get("dataset", {}), training_target_means=target_means,
                terminal_training_failure_is_constant_one=bool(target_means["TERMINAL"])
                    and all(mean[1] == 1 for mean in target_means["TERMINAL"].values()),
                terminal_training_success_is_constant_zero=bool(target_means["TERMINAL"])
                    and all(mean[2] == 0 for mean in target_means["TERMINAL"].values())))
            for log in logs.values():
                model_work.update(log.get("counts", {}))
            # Branch summaries are stage-local; the runner retains reused prefixes separately.
            branch = row.get("branch_completion", {})
            branch_prefix.update(branch.get("prefix_work", {}))
            branch_suffix.update(branch.get("new_work", {}))
            branch_policy.update(branch.get("policy_work", {}))
            branch_outcomes.update(branch.get("outcomes", {}))
            prefix_outcomes.update(branch.get("prefix_outcomes", {}))
            branch_totals.update({name: branch[name] for name in
                ("trajectories", "resumed", "records", "restoration_random_draws")
                if name in branch})
            for method in methods:
                for game in games(life, episodes, method):
                    for group in evaluation[method]:
                        evaluation[method][group].update(game.get(f"{group}_counts", {}))
    return dict(matched_training_rows=bool(labels) and matched, labels=labels,
        actual_executed_work=dict(inherited_natural_source_once_counts=dict(source_work),
            inherited_natural_source_lifecycles=source_rows,
            inherited_training_branch_prefix_counts=dict(branch_prefix),
            new_training_branch_suffix_counts=dict(branch_suffix),
            branch_completion=dict(**branch_totals, outcomes=dict(branch_outcomes), prefix_outcomes=dict(prefix_outcomes)),
            suffix_policy_counts=dict(branch_policy), model_fit_counts=dict(model_work),
            evaluation={method: {group: dict(counts) for group, counts in groups.items()}
                        for method, groups in evaluation.items()},
            newly_sampled_transitions=branch_suffix["sampled_transitions"]
                + sum(groups["environment"]["sampled_transitions"] for groups in evaluation.values()),
            actual_wall_seconds=run.get("actual_wall_seconds")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"complete": result["complete"], "games": result["cohort"]["games"],
        "final_terminal_minus_short": result["final_comparisons"]["TERMINAL_PLAN_minus_SHORT_PLAN"]}))


if __name__ == "__main__":
    main()
