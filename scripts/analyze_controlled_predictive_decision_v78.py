"""V78 natural-game comparisons, with independent lifecycle and cost accounting."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


COMPARATORS = ("MSE_PLAN", "FIXED_PLAN", "FROZEN_PLAN", "H2_ONLY")


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values else None


def _key(game):
    return game["seed"], game["replica"], game["query"]


def _summary(games):
    statuses = Counter(game["status"] for game in games)
    return dict(games=len(games), means={name: _mean(g[name] for g in games)
        for name in ("score", "utility", "steps", "max_rank", "seconds")},
        status_counts=dict(statuses), terminal_games=statuses["WON"] + statuses["LOST"],
        cutoff_games=statuses["CUTOFF"],
        win_fraction=statuses["WON"] / len(games) if games else None)


def analyze_run(run):
    settings = run["settings"]
    lives, checkpoints = settings["lifecycles"], settings["checkpoints"]
    methods, queries = settings["methods"], list(settings["queries"])
    replicas = settings["evaluation_replicas"]
    actual_lives = run["lifecycles"]
    indexed = {life["id"]: {stage["episodes"]: stage for stage in life["stages"]}
               for life in actual_lives}
    roster = (len(actual_lives) == len(lives) and set(indexed) == set(lives)
        and all(len(life["stages"]) == len(checkpoints)
            and {stage["episodes"] for stage in life["stages"]} == set(checkpoints)
            for life in actual_lives))

    def stage(life, episodes):
        return indexed.get(life, {}).get(episodes, {})

    def games(life, episodes, method, query=None):
        rows = stage(life, episodes).get("methods", {}).get(method, {}).get("games", [])
        return [g for g in rows if query is None or g["query"] == query]

    game_roster = roster
    paired = roster
    control_changes = []
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
                paired &= len(rows) == len(reference_keys) and {_key(g) for g in rows} == reference_keys
            for method in ("H2_ONLY", "FROZEN_PLAN"):
                before = {_key(g): g for g in games(life, checkpoints[0], method)}
                after = {_key(g): g for g in games(life, episodes, method)}
                changed = before.keys() != after.keys() or any(
                    any(g[name] != before[key][name] for name in ("score", "utility", "status", "steps"))
                    for key, g in after.items() if key in before)
                if changed:
                    control_changes.append(dict(id=life, episodes=episodes, method=method))

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

    comparisons = {}
    for comparator in COMPARATORS:
        comparisons[comparator] = {}
        for query in queries:
            rows = []
            for life in lives:
                left = games(life, checkpoints[-1], "DECISION_PLAN", query)
                right = games(life, checkpoints[-1], comparator, query)
                first, second = {_key(g): g for g in left}, {_key(g): g for g in right}
                complete = (len(left) == len(right) == len(first) == len(second) == replicas
                            and first.keys() == second.keys())
                rows.append(dict(id=life, complete=complete, pairs=len(first) if complete else 0,
                    **{f"mean_{metric}_delta": _mean(first[key][metric] - second[key][metric]
                        for key in first) if complete else None for metric in ("utility", "score")}))
            complete = all(row["complete"] for row in rows)
            deltas = [row["mean_utility_delta"] for row in rows]
            comparisons[comparator][query] = dict(complete=complete, lifecycles=rows,
                lifecycle_mean_deltas=deltas, mean_delta=_mean(deltas) if complete else None,
                mean_score_delta=_mean(row["mean_score_delta"] for row in rows) if complete else None,
                positive_lifecycles=sum(x is not None and x > 0 for x in deltas),
                negative_lifecycles=sum(x is not None and x < 0 for x in deltas))

    source_work, training_work, acceptance_work = Counter(), Counter(), Counter()
    branch_summaries = {name: Counter() for name in ("training_branches", "acceptance_rollouts")}
    branch_outcomes = {name: Counter() for name in branch_summaries}
    selection_work, training_policy_work, acceptance_planning_work = Counter(), Counter(), Counter()
    update_work = {name: Counter() for name in ("candidate_log", "fixed_log", "mse_acceptance")}
    evaluation = {method: {name: Counter() for name in ("environment", "planning", "prediction")}
                  for method in methods}
    acceptance = {name: [] for name in ("mse", "decision")}
    source_rows = []
    for life in lives:
        source = stage(life, checkpoints[-1]).get("source_summary", {})
        source_work.update(source.get("work", {}))
        source_rows.append(dict(id=life, **source))
        matching_life = next((row for row in actual_lives if row["id"] == life), {})
        selection_work.update(matching_life.get("warmup_selection", {}).get("planning_counts", {}))
        for episodes in checkpoints:
            row = stage(life, episodes)
            for name, counter in (("training_branches", training_work), ("acceptance_rollouts", acceptance_work)):
                branch = row.get(name, {})
                counter.update(branch.get("work", {}))
                branch_outcomes[name].update(branch.get("outcomes", {}))
                branch_summaries[name].update({field: branch[field] for field in
                    ("roots", "trajectories", "records", "success_labels", "failure_labels", "pairs", "first_action_disagreements")
                    if field in branch})
            selection_work.update(row.get("selection", {}).get("planning_counts", {}))
            training_policy_work.update(row.get("training_branches", {}).get("policy_work", {}))
            acceptance_planning_work.update(row.get("acceptance_rollouts", {}).get("planning_counts", {}))
            for name in update_work:
                update_work[name].update(row.get(name, {}).get("counts", {}))
            for name in acceptance:
                if f"{name}_acceptance" in row:
                    acceptance[name].append(dict(id=life, episodes=episodes, **row[f"{name}_acceptance"]))
            for method in methods:
                for game in games(life, episodes, method):
                    for group in evaluation[method]:
                        evaluation[method][group].update(game.get(f"{group}_counts", {}))
    all_games = [game for life in actual_lives for row in life["stages"]
                 for method in row.get("methods", {}).values() for game in method["games"]]
    source_complete = roster and all(stage(life, episodes).get("source_summary", {}).get("episodes") == episodes
                                    for life in lives for episodes in checkpoints)
    complete = (run["status"] == "complete" and roster and game_roster and paired
                and source_complete and not control_changes)
    return dict(schema="acfqp.decision_analysis.v78", complete=complete,
        cohort=dict(lifecycle_roster_complete=roster, source_streams_complete=source_complete,
            evaluation_games_complete=game_roster, paired_evaluation_seeds_complete=paired,
            fixed_controls_unchanged=not control_changes, fixed_control_changes=control_changes,
            expected_games=len(lives) * len(checkpoints) * len(methods) * len(queries) * replicas,
            all_evaluation_games_terminal=bool(all_games) and all(g["status"] in ("WON", "LOST") for g in all_games),
            **_summary(all_games)), checkpoints=results, final_decision_plan_minus_comparator=comparisons,
        acceptance={name: dict(proposals=len(events), accepted=sum(bool(e["accepted"]) for e in events),
            rejected=sum(not e["accepted"] for e in events), events=events) for name, events in acceptance.items()},
        actual_executed_work=dict(inherited_source_once_counts=dict(source_work), inherited_source_lifecycles=source_rows,
            new_training_branch_counts=dict(training_work), new_acceptance_rollout_counts=dict(acceptance_work),
            branch_summaries={name: dict(**values, outcomes=dict(branch_outcomes[name]))
                              for name, values in branch_summaries.items()},
            selection_planning_counts=dict(selection_work), training_policy_counts=dict(training_policy_work),
            acceptance_planning_counts=dict(acceptance_planning_work),
            model_update_counts={name: dict(counts) for name, counts in update_work.items()},
            evaluation={method: {group: dict(counts) for group, counts in groups.items()}
                        for method, groups in evaluation.items()},
            newly_sampled_transitions=training_work["sampled_transitions"] + acceptance_work["sampled_transitions"]
                + sum(groups["environment"]["sampled_transitions"] for groups in evaluation.values()),
            actual_wall_seconds=run.get("actual_wall_seconds")),
        evidence_scope="Completeness describes execution and pairing, not scientific success. Utility differences are "
            "averaged within each independent lifecycle before across-lifecycle means; three lifecycles do not establish "
            "statistical significance. Inherited source interactions are separate from newly sampled training, acceptance "
            "and evaluation interactions. Each method receives its cumulative cost attribution; shared method costs "
            "must not be summed as actual execution cost. Bounded acceptance rollouts are not full-game evaluations.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"complete": result["complete"], "games": result["cohort"]["games"],
                      "acceptance": {k: {name: v[name] for name in ("proposals", "accepted", "rejected")}
                                     for k, v in result["acceptance"].items()}}))


if __name__ == "__main__":
    main()
