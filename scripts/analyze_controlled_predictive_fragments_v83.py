"""Describe learned terminating fragments, matched effects and actual acquisition."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


CONTROLS = ("H2_ONLY", "ONE_STEP", "FROZEN_6", "FIXED_SPACE4")
FIXED = ("H2_ONLY", "FROZEN_6", "FIXED_SPACE4")
TERMINAL = ("WON", "LOST")
WIRING = ("pretrigger_prefixes_match", "committed_lengths_match", "single_initiations", "model_uniforms_aligned")


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values else None


def _key(game):
    return game["seed"], game["query"], game["replica"]


def _summary(games):
    terminal = [game for game in games if game["status"] in TERMINAL]
    return dict(games=len(games), terminal_games=len(terminal),
        status_counts=dict(Counter(game["status"] for game in games)),
        terminal_means={metric: _mean(game[metric] for game in terminal)
            for metric in ("score", "utility", "steps", "max_rank")},
        selected_options=dict(Counter(game["selected_option"] or "NO_SELECTION" for game in games)),
        duration_budgets=dict(Counter(str(game["duration_budget"]) for game in games)),
        actual_fragment_lengths=dict(Counter(str(game["fragment_actions"]) for game in games)),
        games_with_fragment=sum(game["fragment_actions"] > 0 for game in games),
        fragment_actions=sum(game["fragment_actions"] for game in games),
        seconds=math.fsum(game["seconds"] for game in games))


def _same(left, right):
    a, b = {_key(game): game for game in left}, {_key(game): game for game in right}
    fields = ("score", "utility", "status", "steps", "max_rank", "selected_option", "fragment_actions")
    return bool(a) and len(a) == len(left) == len(b) == len(right) and a.keys() == b.keys() and all(
        a[key][field] == b[key][field] for key in a for field in fields)


def _cohort(stage, query, settings):
    methods, replicas = settings["methods"], settings["evaluation_replicas"]
    grouped = {method: [game for game in stage.get("methods", {}).get(method, {}).get("games", [])
                       if game["query"] == query] for method in methods}
    indexed = {method: {_key(game): game for game in rows} for method, rows in grouped.items()}
    roster = all(len(rows) == len(indexed[method]) == replicas and
        {game["replica"] for game in rows} == set(range(replicas)) for method, rows in grouped.items())
    reference = indexed[methods[0]]
    paired = roster and all(rows.keys() == reference.keys() for rows in indexed.values())
    keys = sorted(key for key in reference if all(indexed[method][key]["status"] in TERMINAL
        for method in methods)) if paired else []
    return dict(roster_complete=roster, seeds_paired=paired, complete_replicas=len(keys),
        excluded_replicas=sorted(key[2] for key in reference if key not in keys), keys=keys), indexed


def _effect(left, right, keys):
    return dict(pairs=len(keys), estimable=bool(keys), **{f"mean_{metric}_delta":
        _mean(left[key][metric] - right[key][metric] for key in keys) for metric in ("score", "utility")})


def _across_lives(rows):
    usable = bool(rows) and all(row["estimable"] for row in rows)
    return dict(lifecycles=rows, all_lifecycles_estimable=usable,
        mean_score_delta=_mean(row["mean_score_delta"] for row in rows) if usable else None,
        mean_utility_delta=_mean(row["mean_utility_delta"] for row in rows) if usable else None,
        positive_lifecycles=sum(row["mean_utility_delta"] is not None and row["mean_utility_delta"] > 0 for row in rows),
        negative_lifecycles=sum(row["mean_utility_delta"] is not None and row["mean_utility_delta"] < 0 for row in rows))


def analyze_run(run):
    settings = run["settings"]
    lives, checkpoints, methods = settings["lifecycles"], settings["checkpoints"], settings["methods"]
    queries = settings["queries"]
    indexed = {life["id"]: {row["episodes"]: row for row in life["checkpoints"]} for life in run["lifecycles"]}
    roster = len(run["lifecycles"]) == len(lives) and set(indexed) == set(lives) and all(
        len(life["checkpoints"]) == len(checkpoints) and {row["episodes"] for row in life["checkpoints"]}
        == set(checkpoints) for life in run["lifecycles"])

    def stage(life, checkpoint):
        return indexed.get(life, {}).get(checkpoint, {})

    def games(life, checkpoint, method, query=None):
        rows = stage(life, checkpoint).get("methods", {}).get(method, {}).get("games", [])
        return [row for row in rows if query is None or row["query"] == query]

    cohorts, pairings, checkpoint_results = [], {}, []
    control_changes, first_snapshot_changes = [], []
    selector_checkpoints, wiring_complete = True, True
    source_complete, source_rows, label_counts, fitted_counts = True, [], Counter(), Counter()
    actual = {kind: {name: Counter() for name in ("ground", "planning", "outcomes")}
              for kind in ("source", "branches", "evaluation")}
    batch_counts, query_histories = Counter(), []
    for life in lives:
        cumulative_labels, previous = 0, 0
        for checkpoint in checkpoints:
            row = stage(life, checkpoint)
            source, branches = row.get("source", {}), row.get("branches", {})
            dataset, update = row.get("dataset", {}), row.get("update", {})
            new_labels = (branches.get("roots", 0) - branches.get("censored_roots", 0)) * 4
            cumulative_labels += new_labels
            source_complete &= (source.get("games") == (checkpoint - previous) * len(queries)
                and sum(source.get("outcomes", {}).values()) == source.get("games")
                and source.get("roots") == branches.get("roots")
                and branches.get("trajectories") == branches.get("roots", 0) * 5 * 8
                and sum(branches.get("outcomes", {}).values()) == branches.get("trajectories")
                and dataset.get("records") == update.get("input_records") == cumulative_labels
                and dataset.get("training_records") == update.get("training_records")
                and dataset.get("heldout_records") == update.get("heldout_records")
                and dataset.get("records") == dataset.get("training_records", 0) + dataset.get("heldout_records", 0)
                and update.get("counts", {}).get("fit_rows") == dataset.get("training_records"))
            previous = checkpoint
            for kind, part in (("source", source), ("branches", branches)):
                actual[kind]["ground"].update(part.get("work", {}))
                actual[kind]["planning"].update(part.get("planning_counts", {}))
                actual[kind]["outcomes"].update(part.get("outcomes", {}))
            batch_counts["source_games"] += source.get("games", 0)
            for name in ("roots", "trajectories", "censored_roots"):
                batch_counts[name] += branches.get(name, 0)
            batch_counts["new_labels"] += new_labels
            fitted_counts.update(update.get("counts", {}))
            if checkpoint == checkpoints[-1]:
                label_counts.update({name: dataset.get(name, 0) for name in ("records", "training_records", "heldout_records")})
            source_rows.append(dict(id=life, checkpoint=checkpoint, source=source, branches=branches,
                cumulative_dataset=dataset, update=update))
            wiring_complete &= all(row.get("wiring", {}).get(name) is True for name in WIRING)
            for method in methods:
                method_games = games(life, checkpoint, method)
                expected_selector = checkpoints[0] if method == "FROZEN_6" else checkpoint if method in ("FRAGMENT", "ONE_STEP") else None
                selector_checkpoints &= all(game["selector_checkpoint"] == expected_selector for game in method_games)
                if method in FIXED and not _same(games(life, checkpoints[0], method), method_games):
                    control_changes.append(dict(id=life, checkpoint=checkpoint, method=method))
                for game in method_games:
                    actual["evaluation"]["ground"].update(game["environment_counts"])
                    actual["evaluation"]["planning"].update(game["planning_counts"])
                    actual["evaluation"]["outcomes"][game["status"]] += 1
                response = row.get("query_response", {}).get(method, {})
                query_histories.append(dict(id=life, checkpoint=checkpoint, method=method, **response))
            if checkpoint == checkpoints[0] and not _same(games(life, checkpoint, "FRAGMENT"), games(life, checkpoint, "FROZEN_6")):
                first_snapshot_changes.append(life)
            for query in queries:
                cohort, grouped = _cohort(row, query, settings)
                pairings[life, checkpoint, query] = cohort, grouped
                cohorts.append(dict(id=life, checkpoint=checkpoint, query=query, **{key: value for key, value in cohort.items() if key != "keys"}))
    for checkpoint in checkpoints:
        by_method = {}
        for method in methods:
            costs = [dict(id=life, **stage(life, checkpoint).get("methods", {}).get(method, {}).get("costs", {})) for life in lives]
            fields = set().union(*(cost.keys() for cost in costs)) - {"id"}
            by_method[method] = dict(queries={query: dict(
                pooled=_summary([game for life in lives for game in games(life, checkpoint, method, query)]),
                lifecycles=[dict(id=life, **_summary(games(life, checkpoint, method, query))) for life in lives]) for query in queries},
                cumulative_cost_attribution=dict(lifecycles=costs, totals={name: math.fsum(cost[name] for cost in costs)
                    if all(name in cost for cost in costs) else None for name in fields}))
        checkpoint_results.append(dict(episodes=checkpoint, methods=by_method))
    comparisons = {}
    for other in CONTROLS:
        comparisons[f"FRAGMENT_minus_{other}"] = {}
        for query in queries:
            rows = []
            for life in lives:
                cohort, grouped = pairings[life, checkpoints[-1], query]
                rows.append(dict(id=life, **_effect(grouped["FRAGMENT"], grouped[other], cohort["keys"])))
            comparisons[f"FRAGMENT_minus_{other}"][query] = _across_lives(rows)
    learning = {}
    for method in methods:
        learning[method] = {}
        for query in queries:
            rows = []
            for life in lives:
                first, a = pairings[life, checkpoints[0], query]
                last, b = pairings[life, checkpoints[-1], query]
                keys = sorted(set(first["keys"]) & set(last["keys"]))
                rows.append(dict(id=life, **_effect(b[method], a[method], keys)))
            learning[method][query] = _across_lives(rows)
    all_games = [game for life in run["lifecycles"] for row in life["checkpoints"]
                 for method in row["methods"].values() for game in method["games"]]
    game_roster = bool(cohorts) and all(row["roster_complete"] for row in cohorts)
    paired = bool(cohorts) and all(row["seeds_paired"] for row in cohorts)
    complete = (run["status"] == "complete" and roster and game_roster and paired and source_complete
        and selector_checkpoints and wiring_complete and not control_changes and not first_snapshot_changes)
    return dict(schema="acfqp.terminating_fragments_analysis.v83", complete=complete,
        cohort=dict(lifecycle_roster_complete=roster, evaluation_roster_complete=game_roster, paired_seeds_complete=paired,
            fixed_controls_unchanged=not control_changes, fixed_control_changes=control_changes,
            first_fragment_matches_frozen=not first_snapshot_changes, first_snapshot_changes=first_snapshot_changes,
            selector_checkpoints_match=selector_checkpoints, controller_wiring_complete=wiring_complete,
            source_accounting_complete=source_complete, paired_terminal_cohorts=cohorts,
            expected_games=len(lives) * len(checkpoints) * len(methods) * len(queries) * settings["evaluation_replicas"],
            all_evaluation_games_terminal=bool(all_games) and all(game["status"] in TERMINAL for game in all_games),
            **_summary(all_games)), checkpoints=checkpoint_results, final_comparisons=comparisons,
        first_to_last_checkpoint_change=learning, learning_sources=dict(batches=source_rows,
            unique_final_labels=dict(label_counts), cumulative_fit_work=dict(fitted_counts)),
        query_responses=query_histories,
        actual_executed_work=dict(**dict(batch_counts),
            phases={kind: {name: dict(counts) for name, counts in groups.items()} for kind, groups in actual.items()},
            newly_sampled_transitions=sum(groups["ground"]["sampled_transitions"] for groups in actual.values()),
            actual_wall_seconds=run.get("actual_wall_seconds"), workers=settings["workers"],
            lifecycle_phase_seconds=[dict(id=life, seconds=math.fsum(stage(life, checkpoint).get("phase_seconds", 0)
                for checkpoint in checkpoints)) for life in lives]),
        evidence_scope="Effects use a common terminal cohort across all five methods, first paired within lifecycle, "
            "then averaged equally across lifecycles. Cutoffs retain costs but are not failures or terminal utilities. "
            "Completeness describes execution, not scientific improvement. Learned choice uses supplied primitives, "
            "lengths and trigger. Each method's cumulative construction attribution shares the same acquisition and "
            "must not be summed into actual wall time; source and branch batches are counted once.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("complete", "final_comparisons", "actual_executed_work")}))


if __name__ == "__main__":
    main()
