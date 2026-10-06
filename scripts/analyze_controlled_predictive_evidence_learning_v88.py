"""Separate evidence-supported new interventions from recovery through H2 fallback."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


ARMS = ("COVERAGE", "REPEAT")
CONTRASTS = tuple((f"{arm}_{left}", f"{arm}_{right}" if right != "H2_ONLY" else right)
    for arm in ARMS for left, right in (("SUPPORTED", "POINT"), ("SUPPORTED", "OLD"),
        ("POINT", "OLD"), ("SUPPORTED", "H2_ONLY"), ("POINT", "H2_ONLY"), ("OLD", "H2_ONLY")))
GATE_CONTRASTS = tuple((f"{arm}_SUPPORTED", f"{arm}_{right}") for arm in ARMS for right in ("POINT", "OLD"))
CATEGORIES = ("enabled", "disabled", "both_h2", "same_fragment", "changed_fragment")
TERMINAL = ("WON", "LOST")
WIRING = ("pretrigger_prefixes_match", "committed_lengths_match", "single_initiations", "model_uniforms_aligned",
          "same_choice_histories_match", "evidence_choices_supported", "point_supported_predictions_match")


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
        completed_four_step_fragments=sum(game["fragment_actions"] == 4 for game in games),
        fragment_actions=sum(game["fragment_actions"] for game in games),
        seconds=math.fsum(game["seconds"] for game in games))


def _cohort(evaluation, query, settings):
    methods, replicas = settings["methods"], settings["evaluation_replicas"]
    grouped = {method: [game for game in evaluation.get("methods", {}).get(method, {}).get("games", [])
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


def _gate_category(old, new):
    old, new = old or "H2", new or "H2"
    return ("both_h2" if old == new == "H2" else "enabled" if old == "H2" else
        "disabled" if new == "H2" else "same_fragment" if old == new else "changed_fragment")


def _gate_decomposition(lives, query, left, right, indexed, pairings):
    rows, complete = [], True
    for life in lives:
        cohort, games = pairings[life, query]
        source = indexed.get(life, {}).get("evaluation", {}).get("gate_changes", {}).get(f"{left}_minus_{right}", [])
        source = [row for row in source if row["query"] == query]
        changes = {_key(row): row for row in source}
        reference = games[right]
        matching = len(source) == len(changes) == len(reference) and changes.keys() == reference.keys()
        matching &= all(row["category"] in CATEGORIES for row in source)
        matching &= all(key in games[left] for key in changes)
        if matching:
            for key, change in changes.items():
                old = reference[key]["selected_option"] or "H2"
                new = games[left][key]["selected_option"] or "H2"
                category = _gate_category(old, new)
                matching &= change["category"] == category
                matching &= (change["old_option"] or "H2") == old and (change["new_option"] or "H2") == new
        complete &= matching
        keys = cohort["keys"] if matching else []
        categories = {}
        for category in CATEGORIES:
            selected = [key for key in keys if changes[key]["category"] == category]
            comparison = {}
            for name, method in (("old", right), ("h2", "H2_ONLY")):
                deltas = {metric: [games[left][key][metric] - games[method][key][metric]
                                  for key in selected] for metric in ("score", "utility")}
                comparison[name] = dict(**{f"mean_{metric}_delta": _mean(values) for metric, values in deltas.items()},
                    **{f"sum_{metric}_delta": math.fsum(values) for metric, values in deltas.items()},
                    **{f"{metric}_contribution": math.fsum(values) / len(keys) if keys else None
                       for metric, values in deltas.items()})
            categories[category] = dict(raw_cases=sum(row["category"] == category for row in source),
                pairs=len(selected), **comparison)
        rows.append(dict(id=life, cohort_pairs=len(keys), record_roster_complete=matching, categories=categories))
    estimable = bool(rows) and all(row["cohort_pairs"] for row in rows)
    categories = {}
    for category in CATEGORIES:
        pairs = sum(row["categories"][category]["pairs"] for row in rows)
        categories[category] = dict(raw_cases=sum(row["categories"][category]["raw_cases"] for row in rows), pairs=pairs,
            **{name: {**{f"conditional_mean_{metric}_delta": math.fsum(row["categories"][category][name]
                [f"sum_{metric}_delta"] for row in rows) / pairs if pairs else None for metric in ("score", "utility")},
                **{f"mean_{metric}_contribution": _mean(row["categories"][category][name]
                    [f"{metric}_contribution"] for row in rows) if estimable else None for metric in ("score", "utility")}}
               for name in ("old", "h2")})
    sums = {name: {metric: math.fsum(categories[category][name][f"mean_{metric}_contribution"]
                    for category in CATEGORIES) if estimable else None for metric in ("score", "utility")}
            for name in ("old", "h2")}
    return dict(new_method=left, comparison_method=right, record_roster_complete=complete,
        all_lifecycles_estimable=bool(estimable),
        lifecycles=rows, categories=categories, summed_contributions=sums)


def analyze_run(run):
    settings = run["settings"]
    lives, methods, queries = settings["lifecycles"], settings["methods"], settings["queries"]
    indexed = {life["id"]: life for life in run["lifecycles"]}
    roster = len(run["lifecycles"]) == len(lives) and set(indexed) == set(lives)
    cohorts, pairings, fitting, inherited_rows, histories, query_histories = [], {}, [], [], [], []
    wiring_complete, training_complete, histories_complete = True, True, True
    fit_counts, reused_data = {arm: Counter() for arm in ARMS}, {arm: Counter() for arm in ARMS}
    evaluation_work = {method: {name: Counter() for name in ("ground", "planning", "outcomes")} for method in methods}
    inherited_work = {name: Counter() for name in ("source_work", "branch_work", "joint_fit_counts", "residual_fit_counts")}
    inherited_allocation = {arm: {name: Counter() for name in ("source_work", "branch_work", "fit_counts")} for arm in ARMS}
    for life in lives:
        row = indexed.get(life, {})
        evaluation = row.get("evaluation", {})
        for arm in ARMS:
            data = row.get("updates", {}).get(arm, {})
            dataset, update = data.get("dataset", {}), data.get("update", {})
            counts = update.get("counts", {})
            training_complete &= (dataset.get("roots") == dataset.get("training_roots", 0) + dataset.get("heldout_roots", 0)
                and dataset.get("records") == 4 * dataset.get("roots", 0)
                and counts.get("fit_roots") == dataset.get("training_roots")
                and counts.get("fit_candidate_labels") == 4 * dataset.get("training_roots", 0)
                and counts.get("tree_fits") == len(queries))
            fit_counts[arm].update(counts)
            reused_data[arm].update(dataset)
            fitting.append(dict(id=life, arm=arm, **data))
        inherited = row.get("inherited", {})
        inherited_rows.append(dict(id=life, **inherited))
        for name in inherited_work:
            inherited_work[name].update(inherited.get(name, {}))
        for arm in ARMS:
            for name in inherited_allocation[arm]:
                inherited_allocation[arm][name].update(inherited.get("allocation", {}).get(arm, {}).get(name, {}))
        wiring_complete &= all(evaluation.get("wiring", {}).get(name) is True for name in WIRING)
        for method in methods:
            games = evaluation.get("methods", {}).get(method, {}).get("games", [])
            for game in games:
                evaluation_work[method]["ground"].update(game["environment_counts"])
                evaluation_work[method]["planning"].update(game["planning_counts"])
                evaluation_work[method]["outcomes"][game["status"]] += 1
            history = evaluation.get("pairwise_histories", {}).get(method, {})
            histories_complete &= history.get("pairs") == len(queries) * settings["evaluation_replicas"]
            histories.append(dict(id=life, method=method, **history))
            query_histories.append(dict(id=life, method=method, **evaluation.get("query_response", {}).get(method, {})))
        for query in queries:
            cohort, grouped = _cohort(evaluation, query, settings)
            pairings[life, query] = cohort, grouped
            cohorts.append(dict(id=life, query=query, **{key: value for key, value in cohort.items() if key != "keys"}))
    def games(life, method, query=None):
        rows = indexed.get(life, {}).get("evaluation", {}).get("methods", {}).get(method, {}).get("games", [])
        return [row for row in rows if query is None or row["query"] == query]
    summaries = {}
    for method in methods:
        costs = [dict(id=life, **indexed.get(life, {}).get("evaluation", {}).get("methods", {}).get(method, {}).get("costs", {})) for life in lives]
        fields = set().union(*(cost.keys() for cost in costs)) - {"id"}
        selected_histories = [row for row in histories if row["method"] == method]
        summaries[method] = dict(queries={query: dict(
            pooled=_summary([game for life in lives for game in games(life, method, query)]),
            lifecycles=[dict(id=life, **_summary(games(life, method, query))) for life in lives]) for query in queries},
            paired_histories=dict(pairs=sum(row.get("pairs", 0) for row in selected_histories),
                identical_to_h2=sum(row.get("identical_to_h2", 0) for row in selected_histories)),
            cumulative_cost_attribution=dict(lifecycles=costs, totals={name: math.fsum(cost[name] for cost in costs)
                if all(name in cost for cost in costs) else None for name in fields}))
    comparisons = {}
    for left, right in CONTRASTS:
        comparisons[f"{left}_minus_{right}"] = {}
        for query in queries:
            rows = []
            for life in lives:
                cohort, grouped = pairings[life, query]
                rows.append(dict(id=life, **_effect(grouped[left], grouped[right], cohort["keys"])))
            comparisons[f"{left}_minus_{right}"][query] = _across_lives(rows)
    decomposition = {f"{left}_minus_{right}": {query: _gate_decomposition(lives, query, left, right, indexed, pairings)
        for query in queries} for left, right in GATE_CONTRASTS}
    gate_complete = all(data["record_roster_complete"] for arm in decomposition.values() for data in arm.values())
    all_games = [game for life in lives for method in methods for game in games(life, method)]
    game_roster = bool(cohorts) and all(row["roster_complete"] for row in cohorts)
    paired = bool(cohorts) and all(row["seeds_paired"] for row in cohorts)
    complete = (run["status"] == "complete" and roster and game_roster and paired and training_complete
        and wiring_complete and histories_complete and gate_complete)
    return dict(schema="acfqp.evidence_learning_analysis.v88", complete=complete,
        cohort=dict(lifecycle_roster_complete=roster, evaluation_roster_complete=game_roster,
            paired_seeds_complete=paired, controller_wiring_complete=wiring_complete,
            training_candidate_label_accounting_complete=training_complete, gate_change_roster_complete=gate_complete,
            paired_histories_complete=histories_complete, paired_terminal_cohorts=cohorts,
            expected_games=len(lives) * len(methods) * len(queries) * settings["evaluation_replicas"],
            all_evaluation_games_terminal=bool(all_games) and all(game["status"] in TERMINAL for game in all_games),
            **_summary(all_games)), methods=summaries, final_comparisons=comparisons,
        gate_decomposition=decomposition, fitting=dict(updates=fitting,
            reused_datasets={arm: dict(counts) for arm, counts in reused_data.items()},
            new_fit_counts={arm: dict(counts) for arm, counts in fit_counts.items()}),
        inherited=dict(lifecycles=inherited_rows, **{name: dict(counts) for name, counts in inherited_work.items()},
            allocation={arm: {name: dict(counts) for name, counts in groups.items()} for arm, groups in inherited_allocation.items()}),
        query_responses=query_histories, pairwise_histories=histories,
        actual_executed_work=dict(new_source_games=0, new_branch_trajectories=0, new_validation_transitions=0,
            new_fit_counts={arm: dict(counts) for arm, counts in fit_counts.items()},
            evaluation={method: {name: dict(counts) for name, counts in groups.items()} for method, groups in evaluation_work.items()},
            newly_sampled_transitions=sum(groups["ground"]["sampled_transitions"] for groups in evaluation_work.values()),
            actual_wall_seconds=run.get("actual_wall_seconds"), workers=settings["workers"]),
        evidence_scope="POINT and SUPPORTED share learned leaves and R/F/S means; SUPPORTED additionally requires "
            "a majority of positive training-root labels. Mean utility plus or minus two standard errors defines "
            "exploratory labels, not confidence intervals or success probabilities. Disabled interventions measure "
            "return to H2; enabled and changed-fragment cases measure added or altered fragment execution. Each category's "
            "contribution divides its paired sum by the full within-lifecycle common terminal cohort before averaging "
            "lifecycles, so contributions sum to the overall effect. Conditional category means are descriptive. "
            "Cutoffs retain cost and are removed jointly across seven methods. V83-V86 construction is inherited; "
            "past validation/evaluation is not new work. Shared method attributions are not additive wall time.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("complete", "final_comparisons", "gate_decomposition")}))


if __name__ == "__main__":
    main()
