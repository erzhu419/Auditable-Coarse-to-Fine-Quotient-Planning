"""Separate first-action and continued-policy effects on the fixed V81 roots."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


METHODS = ("PARENT", "FIRST_ONLY", "FULL_UPDATE")
CONTRASTS = {
    "FIRST_ONLY_minus_PARENT": ("FIRST_ONLY", "PARENT"),
    "FULL_UPDATE_minus_FIRST_ONLY": ("FULL_UPDATE", "FIRST_ONLY"),
    "FULL_UPDATE_minus_PARENT": ("FULL_UPDATE", "PARENT"),
}
METRICS = ("score", "utility", "failure", "success")
TERMINAL = ("WON", "LOST")


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values else None


def _weighted(vector, query):
    return (query["reward_weight"] * vector[0]
            - query["failure_penalty"] * vector[1] + query["goal_bonus"] * vector[2])


def _value(game, metric):
    if metric in ("failure", "success"):
        return int(game["status"] == ("LOST" if metric == "failure" else "WON"))
    return game[metric]


def _root(record, life, settings):
    root, games = record["root"], record["games"]
    replicas = settings["replicas"]
    query = settings["queries"][root["query"]]
    indexed = {(game["replica"], game["method"]): game for game in games}
    expected = {(replica, method) for replica in range(replicas) for method in METHODS}
    roster = len(games) == len(indexed) == len(expected) and set(indexed) == expected
    paired, complete_replicas, censored_replicas, invalid_replicas = True, [], [], []
    paired_rows = []
    for replica in range(replicas):
        arms = {method: indexed.get((replica, method)) for method in METHODS}
        present = all(arm is not None for arm in arms.values())
        same_seeds = present and len({(g["env_seed"], g["model_seed"]) for g in arms.values()}) == 1
        correct_continuation = present and all(g["query"] == root["query"] and
            g["continuation_iteration"] == (1 if method == "FULL_UPDATE" else 0)
            for method, g in arms.items())
        valid = same_seeds and correct_continuation
        paired &= valid
        if not valid:
            invalid_replicas.append(replica)
            continue
        if any(g["status"] not in TERMINAL for g in arms.values()):
            censored_replicas.append(replica)
            continue
        complete_replicas.append(replica)
        paired_rows.append(dict(replica=replica, effects={name: {
            metric: _value(arms[left], metric) - _value(arms[right], metric)
            for metric in METRICS} for name, (left, right) in CONTRASTS.items()}))
    # A duplicate or missing arm invalidates a root instead of choosing a convenient copy.
    usable = roster and paired
    if not usable:
        paired_rows = []
    effects = {}
    for name in CONTRASTS:
        halves = [_mean(row["effects"][name]["utility"] for row in paired_rows
                       if (row["replica"] < replicas // 2) == first) for first in (True, False)]
        effects[name] = {f"mean_{metric}_delta": _mean(row["effects"][name][metric]
                            for row in paired_rows) for metric in METRICS}
        effects[name].update(split_half_utility_means=halves,
            split_half_sign_reversal=halves[0] * halves[1] < 0
                if all(value is not None for value in halves) else None)
    fresh = effects["FIRST_ONLY_minus_PARENT"]["mean_utility_delta"]
    predicted = _weighted(root["predicted_advantage"], query)
    old = _weighted(root["old_observed_advantage"], query)
    override = root["selected_action"] != root["reference_action"]
    return dict(id=life, root=root, overridden=override, games=len(games),
        roster_complete=roster, seeds_and_continuation_complete=paired,
        complete_triplets=len(paired_rows), complete_replicas=complete_replicas if usable else [],
        censored_replicas=censored_replicas, invalid_replicas=invalid_replicas,
        status_counts=dict(Counter(g["status"] for g in games)),
        method_status_counts={method: dict(Counter(g["status"] for g in games
            if g["method"] == method)) for method in METHODS},
        effects=effects, paired_replicas=paired_rows,
        action_estimates=dict(predicted_utility_advantage=predicted,
            old_observed_utility_advantage=old, fresh_mean_utility_advantage=fresh,
            predicted_score_advantage=2048 * root["predicted_advantage"][0],
            old_observed_score_advantage=2048 * root["old_observed_advantage"][0],
            fresh_mean_score_advantage=effects["FIRST_ONLY_minus_PARENT"]["mean_score_delta"],
            negative_override=override and fresh < 0 if fresh is not None else None,
            predicted_to_fresh_sign_reversal=predicted * fresh < 0 if fresh is not None else None,
            old_to_fresh_sign_reversal=old * fresh < 0 if fresh is not None else None),
        wiring=record.get("wiring", {}))


def _aggregate(roots, settings):
    """Average replicas within root, roots within life, then the independent lives."""
    expected_roots = settings["roots_per_query_per_lifecycle"]
    output = {}
    for query in settings["queries"]:
        by_life = []
        for life in settings["lifecycles"]:
            rows = [row for row in roots if row["id"] == life and row["root"]["query"] == query]
            usable = len(rows) == expected_roots and all(row["complete_triplets"] for row in rows)
            by_life.append(dict(id=life, roots=len(rows), usable=usable,
                complete_triplets=sum(row["complete_triplets"] for row in rows),
                effects={name: {f"mean_{metric}_delta": _mean(
                    row["effects"][name][f"mean_{metric}_delta"] for row in rows) if usable else None
                    for metric in METRICS} for name in CONTRASTS}))
        complete = bool(by_life) and all(row["usable"] for row in by_life)
        output[query] = dict(lifecycles=by_life, all_lifecycles_estimable=complete,
            effects={name: {f"mean_{metric}_delta": _mean(
                row["effects"][name][f"mean_{metric}_delta"] for row in by_life) if complete else None
                for metric in METRICS} for name in CONTRASTS})
    return output


def analyze_run(run):
    settings = run["settings"]
    roots = [_root(record, life["id"], settings) for life in run["lifecycles"] for record in life["roots"]]
    expected_roots = len(settings["lifecycles"]) * len(settings["queries"]) * settings["roots_per_query_per_lifecycle"]
    life_ids = [life["id"] for life in run["lifecycles"]]
    root_keys = {(r["id"], r["root"]["query"], r["root"]["episode"], r["root"]["step"]) for r in roots}
    roster = (len(life_ids) == len(set(life_ids)) == len(settings["lifecycles"])
        and set(life_ids) == set(settings["lifecycles"])
        and len(roots) == len(root_keys) == expected_roots
        and all(sum(r["id"] == life and r["root"]["query"] == query for r in roots)
            == settings["roots_per_query_per_lifecycle"] for life in settings["lifecycles"] for query in settings["queries"]))
    games = [game for life in run["lifecycles"] for record in life["roots"] for game in record["games"]]
    environment, planning, outcomes = Counter(), Counter(), Counter()
    by_method = {method: dict(environment_counts=Counter(), planning_counts=Counter(), outcomes=Counter(),
        games=0, seconds=0.0) for method in METHODS}
    for game in games:
        environment.update(game["environment_counts"])
        planning.update(game["planning_counts"])
        outcomes[game["status"]] += 1
        counts = by_method[game["method"]]
        counts["environment_counts"].update(game["environment_counts"])
        counts["planning_counts"].update(game["planning_counts"])
        counts["outcomes"][game["status"]] += 1
        counts["games"] += 1
        counts["seconds"] += game["seconds"]
    estimates = [row for row in roots if row["complete_triplets"]]
    overrides = [row for row in estimates if row["overridden"]]
    no_override = [row for row in roots if not row["overridden"]]
    wiring = dict(first_transition_matches=all(row["wiring"].get("same_first_transition_first_full")
        is True for row in roots), no_override_parent_first_identical=all(
            row["wiring"].get("no_override_parent_first_identical") is True for row in no_override))
    complete = (run["status"] == "complete" and roster and
        all(row["roster_complete"] and row["seeds_and_continuation_complete"] for row in roots)
        and all(wiring.values()))
    diagnostics = dict(estimable_roots=len(estimates), overridden_roots=len(overrides),
        unchanged_roots=len(no_override),
        negative_overrides=sum(row["action_estimates"]["negative_override"] for row in overrides),
        predicted_to_fresh_sign_reversals=sum(row["action_estimates"]["predicted_to_fresh_sign_reversal"]
            for row in overrides),
        old_to_fresh_sign_reversals=sum(row["action_estimates"]["old_to_fresh_sign_reversal"] for row in overrides),
        first_effect_split_half_sign_reversals=sum(row["effects"]["FIRST_ONLY_minus_PARENT"]
            ["split_half_sign_reversal"] is True for row in overrides),
        first_effect_split_half_available=sum(row["effects"]["FIRST_ONLY_minus_PARENT"]
            ["split_half_sign_reversal"] is not None for row in overrides),
        mean_absolute_predicted_utility_error=_mean(abs(row["action_estimates"]["predicted_utility_advantage"]
            - row["action_estimates"]["fresh_mean_utility_advantage"]) for row in overrides),
        mean_absolute_old_observed_utility_error=_mean(abs(row["action_estimates"]["old_observed_utility_advantage"]
            - row["action_estimates"]["fresh_mean_utility_advantage"]) for row in overrides))
    return dict(schema="acfqp.policy_effects_analysis.v82", complete=complete,
        cohort=dict(root_roster_complete=roster, roots=len(roots), expected_roots=expected_roots,
            games=len(games), expected_games=expected_roots * settings["replicas"] * len(METHODS),
            expected_triplets=expected_roots * settings["replicas"],
            complete_triplets=sum(row["complete_triplets"] for row in roots),
            censored_triplets=sum(len(row["censored_replicas"]) for row in roots),
            invalid_triplets=sum(len(row["invalid_replicas"]) for row in roots),
            all_games_terminal=bool(games) and all(game["status"] in TERMINAL for game in games),
            status_counts=dict(outcomes), **wiring),
        paired_effects=_aggregate(roots, settings), root_diagnostics=diagnostics, roots=roots,
        actual_executed_work=dict(environment_counts=dict(environment), planning_counts=dict(planning),
            newly_sampled_transitions=environment["sampled_transitions"], methods=by_method,
            actual_wall_seconds=run.get("actual_wall_seconds"),
            inherited_source="The fixed V81 policies, roots and two-replica targets are reused; no new fitting or source games."),
        inherited_policy_construction=[dict(id=life["id"], **life.get("inherited_policy_construction", {}))
            for life in run["lifecycles"]],
        evidence_scope="Each effect uses the same complete terminal triplets. Censored triplets are omitted from all "
            "three effects together; cutoff is not failure. Replicas are averaged within root, roots within lifecycle, "
            "then the lifecycle means. These fixed heldout roots and descriptive three-lifecycle results are not "
            "a significance claim or a policy promotion. Fresh first-action effects remain noisy Monte Carlo estimates.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("complete", "cohort", "paired_effects", "root_diagnostics")}))


if __name__ == "__main__":
    main()
