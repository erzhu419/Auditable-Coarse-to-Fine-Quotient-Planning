"""Compare root coverage and repeat sampling at matched actual acquisition cost."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


ARMS = ("COVERAGE", "REPEAT")
CONTRASTS = (("COVERAGE", "REPEAT"), ("COVERAGE", "FROZEN_V85"),
             ("COVERAGE", "H2_ONLY"), ("REPEAT", "FROZEN_V85"), ("REPEAT", "H2_ONLY"))
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


def analyze_run(run):
    settings = run["settings"]
    lives, methods, queries = settings["lifecycles"], settings["methods"], settings["queries"]
    indexed = {life["id"]: life for life in run["lifecycles"]}
    roster = len(run["lifecycles"]) == len(lives) and set(indexed) == set(lives)
    cohorts, pairings, budget_rows, training_rows, validation_rows, inherited_rows = [], {}, [], [], [], []
    wiring_complete, budget_complete, training_complete, validation_complete, histories_complete = (True,) * 5
    histories, query_histories = [], []
    acquisition = {arm: {name: Counter() for name in ("source_work", "branch_work", "counts", "fit_counts")} for arm in ARMS}
    validation_work = {name: Counter() for name in ("source_work", "branch_work", "counts")}
    evaluation_work = {method: {name: Counter() for name in ("ground", "planning", "outcomes")} for method in methods}
    inherited_work = {name: Counter() for name in ("source_work", "branch_work", "joint_fit_counts", "residual_fit_counts")}
    for life in lives:
        row = indexed.get(life, {})
        allocation, evaluation = row.get("allocation", {}), row.get("evaluation", {})
        for arm in ARMS:
            data = allocation.get(arm, {})
            arm_queries, dataset, update = data.get("queries", {}), data.get("dataset", {}), data.get("update", {})
            budget_complete &= set(arm_queries) == set(queries)
            added = 0
            for query in queries:
                source = arm_queries.get(query, {})
                actual = source.get("source_work", {}).get("sampled_transitions", 0) + source.get("branch_work", {}).get("sampled_transitions", 0)
                matched = source.get("budget") == source.get("used_transitions") == actual == settings["budget_per_query"]
                budget_complete &= matched
                budget_rows.append(dict(id=life, arm=arm, query=query, actual_transitions=actual,
                    actual_budget_matched=matched, **source))
                for name in ("source_work", "branch_work"):
                    acquisition[arm][name].update(source.get(name, {}))
                for name in ("source_games", "branch_trajectories", "completed_blocks", "incomplete_blocks", "training_roots_added"):
                    acquisition[arm]["counts"][name] += source.get(name, 0)
                added += source.get("training_roots_added", 0)
            counts = update.get("counts", {})
            training_complete &= (dataset.get("roots") == dataset.get("training_roots", 0) + dataset.get("heldout_roots", 0)
                and dataset.get("records") == 4 * dataset.get("roots", 0)
                and counts.get("fit_roots") == dataset.get("training_roots")
                and counts.get("fit_output_vectors") == 4 * dataset.get("training_roots", 0)
                and dataset.get("training_roots") == 10 * len(queries) + added
                and (arm != "REPEAT" or added == 0))
            acquisition[arm]["fit_counts"].update(counts)
            training_rows.append(dict(id=life, arm=arm, dataset=dataset, update=update,
                construction_seconds=data.get("construction_seconds")))
        validation = row.get("validation", {})
        trajectories_per_root = 5 * settings["validation_replicas"]
        validation_complete &= (validation.get("roots") == settings["validation_roots_per_query"] * len(queries)
            and validation.get("source_games") == validation.get("roots")
            and validation.get("roots") == validation.get("complete_roots", 0) + validation.get("incomplete_roots", 0)
            and 0 <= validation.get("branch_trajectories", -1) <= validation.get("roots", 0) * trajectories_per_root
            and validation.get("branch_trajectories", -1) >= validation.get("complete_roots", 0) * trajectories_per_root)
        for name in ("source_work", "branch_work"):
            validation_work[name].update(validation.get(name, {}))
        for name in ("source_games", "roots", "complete_roots", "incomplete_roots", "branch_trajectories"):
            validation_work["counts"][name] += validation.get(name, 0)
        validation_rows.append(dict(id=life, **validation))
        inherited = row.get("inherited", {})
        inherited_rows.append(dict(id=life, **inherited))
        for name in inherited_work:
            inherited_work[name].update(inherited.get(name, {}))
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
    all_games = [game for life in lives for method in methods for game in games(life, method)]
    game_roster = bool(cohorts) and all(row["roster_complete"] for row in cohorts)
    paired = bool(cohorts) and all(row["seeds_paired"] for row in cohorts)
    complete = (run["status"] == "complete" and roster and game_roster and paired and training_complete
        and budget_complete and wiring_complete and validation_complete and histories_complete)
    new_acquisition = sum(groups[name]["sampled_transitions"] for groups in acquisition.values() for name in ("source_work", "branch_work"))
    new_validation = sum(validation_work[name]["sampled_transitions"] for name in ("source_work", "branch_work"))
    new_evaluation = sum(groups["ground"]["sampled_transitions"] for groups in evaluation_work.values())
    return dict(schema="acfqp.budget_allocation_analysis.v86", complete=complete,
        cohort=dict(lifecycle_roster_complete=roster, evaluation_roster_complete=game_roster,
            paired_seeds_complete=paired, controller_wiring_complete=wiring_complete,
            actual_acquisition_budgets_matched=budget_complete, training_root_accounting_complete=training_complete,
            validation_roster_complete=validation_complete, paired_histories_complete=histories_complete,
            paired_terminal_cohorts=cohorts, expected_games=len(lives) * len(methods) * len(queries) * settings["evaluation_replicas"],
            all_evaluation_games_terminal=bool(all_games) and all(game["status"] in TERMINAL for game in all_games),
            **_summary(all_games)), methods=summaries, final_comparisons=comparisons,
        allocation=dict(queries=budget_rows, training=training_rows),
        validation=dict(lifecycles=validation_rows, **{name: dict(counts) for name, counts in validation_work.items()}),
        inherited=dict(lifecycles=inherited_rows, **{name: dict(counts) for name, counts in inherited_work.items()}),
        query_responses=query_histories, pairwise_histories=histories,
        actual_executed_work=dict(acquisition={arm: {name: dict(counts) for name, counts in groups.items()} for arm, groups in acquisition.items()},
            validation={name: dict(counts) for name, counts in validation_work.items()},
            evaluation={method: {name: dict(counts) for name, counts in groups.items()} for method, groups in evaluation_work.items()},
            new_acquisition_transitions=new_acquisition, new_validation_transitions=new_validation,
            new_evaluation_transitions=new_evaluation, newly_sampled_transitions=new_acquisition + new_validation + new_evaluation,
            actual_wall_seconds=run.get("actual_wall_seconds"), workers=settings["workers"]),
        evidence_scope="Acquisition budgets count actual source and branch transitions, including unfinished blocks. "
            "Validation and evaluation are independent additional work; inherited acquisition and fits are separate. "
            "Effects use the same terminal cohort across four methods, paired within lifecycle and averaged equally "
            "across lifecycles. Cutoffs retain costs but are not terminal failures. Complete execution does not certify "
            "scientific benefit; method cost attributions are not additive actual wall time.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("complete", "final_comparisons", "actual_executed_work")}))


if __name__ == "__main__":
    main()
