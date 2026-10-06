"""Evaluate centered candidate residuals with frozen V84 common-value anchors."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


CONTROLS = ("H2_ONLY", "CENTERED_ONE_STEP", "CENTERED_FROZEN6", "JOINT", "FIXED_SPACE4")
FIXED = ("H2_ONLY", "CENTERED_FROZEN6", "FIXED_SPACE4")
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
        four_step_selections=sum(game["duration_budget"] == 4 for game in games),
        completed_four_step_fragments=sum(game["fragment_actions"] == 4 for game in games),
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

    cohorts, pairings, checkpoint_results, fitting = [], {}, [], []
    control_changes, first_snapshot_changes, histories, query_histories = [], [], [], []
    selector_checkpoints, wiring_complete, training_complete, histories_complete = True, True, True, True
    fit_work, inherited_source, inherited_branch, inherited_counts, final_dataset = (Counter() for _ in range(5))
    anchor_costs, anchor_fit_counts = Counter(), Counter()
    evaluation = {method: {name: Counter() for name in ("ground", "planning", "outcomes")} for method in methods}
    inherited_rows = []
    for life in lives:
        for checkpoint in checkpoints:
            row = stage(life, checkpoint)
            dataset, update = row.get("dataset", {}), row.get("update", {})
            counts = update.get("counts", {})
            training_complete &= (dataset.get("records") == 4 * dataset.get("roots", 0)
                and dataset.get("training_records") == 4 * dataset.get("training_roots", 0)
                and dataset.get("heldout_records") == 4 * dataset.get("heldout_roots", 0)
                and dataset.get("roots") == dataset.get("training_roots", 0) + dataset.get("heldout_roots", 0)
                and counts.get("fit_roots") == dataset.get("training_roots")
                and counts.get("fit_output_vectors") == dataset.get("training_records"))
            fit_work.update(counts)
            fitting.append(dict(id=life, checkpoint=checkpoint, dataset=dataset, update=update,
                input_preparation_seconds=row.get("input_preparation_seconds"), new_fitting_seconds=row.get("new_fitting_seconds")))
            if checkpoint == checkpoints[-1]:
                inherited = row.get("inherited", {})
                inherited_rows.append(dict(id=life, **inherited))
                inherited_source.update(inherited.get("source_work", {}))
                inherited_branch.update(inherited.get("branch_work", {}))
                inherited_counts.update({name: inherited.get(name, 0) for name in ("source_games", "branch_trajectories")})
                anchor_costs.update(inherited.get("joint_costs", {}))
                anchor_fit_counts.update(inherited.get("joint_fit_counts", {}))
                final_dataset.update(dataset)
            wiring_complete &= all(row.get("wiring", {}).get(name) is True for name in WIRING)
            for method in methods:
                method_games = games(life, checkpoint, method)
                expected_selector = checkpoints[0] if method == "CENTERED_FROZEN6" else checkpoint if method in ("CENTERED", "CENTERED_ONE_STEP", "JOINT") else None
                selector_checkpoints &= all(game["selector_checkpoint"] == expected_selector for game in method_games)
                if method in FIXED and not _same(games(life, checkpoints[0], method), method_games):
                    control_changes.append(dict(id=life, checkpoint=checkpoint, method=method))
                for game in method_games:
                    evaluation[method]["ground"].update(game["environment_counts"])
                    evaluation[method]["planning"].update(game["planning_counts"])
                    evaluation[method]["outcomes"][game["status"]] += 1
                response = row.get("query_response", {}).get(method, {})
                query_histories.append(dict(id=life, checkpoint=checkpoint, method=method, **response))
                history = row.get("pairwise_histories", {}).get(method, {})
                histories_complete &= history.get("pairs") == len(queries) * settings["evaluation_replicas"]
                histories.append(dict(id=life, checkpoint=checkpoint, method=method, **history))
            if checkpoint == checkpoints[0] and not _same(games(life, checkpoint, "CENTERED"), games(life, checkpoint, "CENTERED_FROZEN6")):
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
            selected_histories = [row for row in histories if row["checkpoint"] == checkpoint and row["method"] == method]
            by_method[method] = dict(queries={query: dict(
                pooled=_summary([game for life in lives for game in games(life, checkpoint, method, query)]),
                lifecycles=[dict(id=life, **_summary(games(life, checkpoint, method, query))) for life in lives]) for query in queries},
                paired_histories=dict(pairs=sum(row.get("pairs", 0) for row in selected_histories),
                    identical_to_h2=sum(row.get("identical_to_h2", 0) for row in selected_histories)),
                cumulative_cost_attribution=dict(lifecycles=costs, totals={name: math.fsum(cost[name] for cost in costs)
                    if all(name in cost for cost in costs) else None for name in fields}))
        checkpoint_results.append(dict(episodes=checkpoint, methods=by_method))
    comparisons = {}
    for other in CONTROLS:
        comparisons[f"CENTERED_minus_{other}"] = {}
        for query in queries:
            rows = []
            for life in lives:
                cohort, grouped = pairings[life, checkpoints[-1], query]
                rows.append(dict(id=life, **_effect(grouped["CENTERED"], grouped[other], cohort["keys"])))
            comparisons[f"CENTERED_minus_{other}"][query] = _across_lives(rows)
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
    complete = (run["status"] == "complete" and roster and game_roster and paired and training_complete
        and selector_checkpoints and wiring_complete and histories_complete and not control_changes and not first_snapshot_changes)
    return dict(schema="acfqp.centered_fragments_analysis.v85", complete=complete,
        cohort=dict(lifecycle_roster_complete=roster, evaluation_roster_complete=game_roster, paired_seeds_complete=paired,
            fixed_controls_unchanged=not control_changes, fixed_control_changes=control_changes,
            first_centered_matches_frozen=not first_snapshot_changes, first_snapshot_changes=first_snapshot_changes,
            selector_checkpoints_match=selector_checkpoints, controller_wiring_complete=wiring_complete,
            paired_histories_complete=histories_complete, training_root_accounting_complete=training_complete,
            paired_terminal_cohorts=cohorts,
            expected_games=len(lives) * len(checkpoints) * len(methods) * len(queries) * settings["evaluation_replicas"],
            all_evaluation_games_terminal=bool(all_games) and all(game["status"] in TERMINAL for game in all_games),
            **_summary(all_games)), checkpoints=checkpoint_results, final_comparisons=comparisons,
        first_to_last_checkpoint_change=learning, fitting=dict(checkpoints=fitting,
            unique_reused_dataset=dict(final_dataset), new_fit_counts=dict(fit_work)),
        inherited_acquisition=dict(lifecycles=inherited_rows, **dict(inherited_counts),
            source_work=dict(inherited_source), branch_work=dict(inherited_branch)),
        inherited_anchor_construction=dict(cumulative_costs=dict(anchor_costs),
            cumulative_fit_counts=dict(anchor_fit_counts)),
        query_responses=query_histories, pairwise_histories=histories,
        actual_executed_work=dict(new_source_games=0, new_branch_trajectories=0,
            evaluation={method: {name: dict(counts) for name, counts in groups.items()} for method, groups in evaluation.items()},
            new_fit_counts=dict(fit_work),
            newly_sampled_transitions=sum(groups["ground"]["sampled_transitions"] for groups in evaluation.values()),
            actual_wall_seconds=run.get("actual_wall_seconds"), workers=settings["workers"],
            lifecycle_phase_seconds=[dict(id=life, seconds=math.fsum(stage(life, checkpoint).get("phase_seconds", 0)
                for checkpoint in checkpoints)) for life in lives]),
        evidence_scope="Effects use one common terminal cohort across all six methods, paired within lifecycle "
            "then averaged equally across lifecycles. Selecting four steps demonstrates candidate differentiation, "
            "not improved return. Cutoffs retain costs but are not terminal failures. V83 acquisition and V84 anchor fitting are reused "
            "and reported once from final checkpoints; new work consists of residual fitting and evaluation. Shared "
            "method construction attributions and concurrent lifecycle seconds must not be summed as actual wall time.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("complete", "final_comparisons", "actual_executed_work")}))


if __name__ == "__main__":
    main()
