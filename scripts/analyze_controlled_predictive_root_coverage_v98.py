"""Two-history pilot of root coverage at fixed physical acquisition budgets."""
from collections import Counter
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.analyze_controlled_predictive_evidence_learning_v88 import (
    _mean, _summary, _cohort, _effect, _across_lives, _gate_decomposition,
)
from scripts.analyze_controlled_predictive_bellman_v94 import (
    _paired_summary, predictive_error, _history_summary,
)
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility

TERMINAL = ("WON", "LOST")
WIRING = ("pretrigger_prefixes_match", "committed_lengths_match", "single_initiations",
    "model_uniforms_aligned", "same_choice_histories_match", "simulated_prefixes_paired", "simulated_work_matches")
from scripts.run_controlled_predictive_root_coverage_v98 import CONTRASTS


def _gate_pairs(methods):
    return list(CONTRASTS)


def _comparisons(methods):
    pairs = _gate_pairs(methods)
    pairs += [(method, "H2_ONLY") for method in methods
        if method != "H2_ONLY" and (method, "H2_ONLY") not in pairs]
    return pairs


def analyze_natural(run):
    settings = run["settings"]
    lives, queries = settings["lifecycles"], settings["queries"]
    indexed = {life["id"]: life for life in run["lifecycles"]}
    checks = dict(lifecycle_roster_complete=len(indexed) == len(run["lifecycles"]) == len(lives)
        and set(indexed) == set(lives), natural_rosters_complete=True, natural_streams_paired=True,
        controller_wiring_complete=True, gate_rosters_complete=True, all_natural_games_terminal=True)
    work = {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
    methods = settings["methods"]
    stages = {life: indexed[life]["evaluation"] for life in lives}
    wrapped = {life: {"evaluation": stage} for life, stage in stages.items()}
    pairings, cohorts, summaries = {}, [], {}
    for life, stage in stages.items():
        checks["controller_wiring_complete"] &= all(stage["wiring"].get(key) is True for key in WIRING)
        for method in methods:
            for game in stage["methods"][method]["games"]:
                work["ground_work"].update(game["environment_counts"])
                work["planning_counts"].update(game["planning_counts"])
                work["outcomes"][game["status"]] += 1
                checks["all_natural_games_terminal"] &= game["status"] in TERMINAL
        for query in queries:
            cohort, grouped = _cohort(stage, query, dict(settings, methods=methods))
            pairings[life, query] = cohort, grouped
            cohorts.append(dict(id=life, query=query, **{k: v for k, v in cohort.items() if k != "keys"}))
            checks["natural_rosters_complete"] &= cohort["roster_complete"]
            checks["natural_streams_paired"] &= cohort["seeds_paired"]
    for method in methods:
        summary = {}
        for query in queries:
            rows = [dict(id=life, **_summary([game for game in stages[life]["methods"][method]["games"]
                if game["query"] == query])) for life in lives]
            primary = all(row["games"] == row["terminal_games"] == settings["evaluation_replicas"] for row in rows)
            summary[query] = dict(lifecycles=rows, primary_estimable=primary,
                primary_mean_score=_mean(row["terminal_means"]["score"] for row in rows) if primary else None,
                primary_mean_utility=_mean(row["terminal_means"]["utility"] for row in rows) if primary else None)
        summaries[method] = dict(queries=summary,
            costs=[dict(id=life, **stages[life]["methods"][method]["costs"]) for life in lives])
    comparisons, gates = {}, {}
    for left, right in _comparisons(methods):
        comparison = comparisons[f"{left}_minus_{right}"] = {}
        for query in queries:
            rows = [dict(id=life, **_effect(pairings[life, query][1][left], pairings[life, query][1][right],
                pairings[life, query][0]["keys"])) for life in lives]
            available = _across_lives(rows)
            primary = all(row["pairs"] == settings["evaluation_replicas"] for row in rows)
            comparison[query] = dict(primary_estimable=primary,
                mean_score_delta=available["mean_score_delta"] if primary else None,
                mean_utility_delta=available["mean_utility_delta"] if primary else None,
                available_common_terminal=available)
    for left, right in _gate_pairs(methods):
        gate = gates[f"{left}_minus_{right}"] = {}
        for query in queries:
            data = _gate_decomposition(lives, query, left, right, wrapped, pairings)
            primary = data["record_roster_complete"] and all(
                row["cohort_pairs"] == settings["evaluation_replicas"] for row in data["lifecycles"])
            checks["gate_rosters_complete"] &= data["record_roster_complete"]
            categories = data["categories"]
            attribution = None
            if primary:
                attribution = {
                    metric: dict(new_or_changed_intervention_h2_contribution=math.fsum(
                        categories[name]["h2"][f"mean_{metric}_contribution"]
                        for name in ("enabled", "changed_fragment")),
                        cancelled_intervention_recovery_contribution=
                            categories["disabled"]["old"][f"mean_{metric}_contribution"])
                    for metric in ("score", "utility")}

            gate[query] = dict(primary_estimable=primary, primary_attribution=attribution,
                available_common_terminal=data)
    return dict(methods=summaries, comparisons=comparisons, gate_decomposition=gates,
        paired_terminal_cohorts=cohorts, checks=checks,
        work={name: dict(value) for name, value in work.items()},
        scope="Two independent learning histories form a pilot. Report each history and equal-history "
            "means; no two-SE efficacy band or scientific Gate is computed.")


def analyze_validation(run):
    settings = run["settings"]
    methods = [name for name in settings["methods"] if name != "H2_ONLY"]
    replicas = settings["reference_replicas"]
    roots, errors, missing = [], [], []
    work = {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
    trajectories, seconds = 0, 0.
    checks = dict(validation_roster_complete=True, reference_work_accounted=True,
        all_reference_trajectories_terminal=True, independent_reference_complete=True,
        deployed_prediction_rosters_complete=True)
    for life in run["lifecycles"]:
        stage = life["evaluation"]
        data = stage["validation"]
        seconds += data["seconds"]
        missing.extend(dict(row, life=life["id"]) for row in data["missing_roots"])
        games = {name: {(game["seed"], game["query"], game["replica"]): game
            for game in stage["methods"][name]["games"]} for name in methods}
        for query in settings["queries"]:
            selected = [row for row in data["roots"] if row["root"]["query"] == query]
            checks["validation_roster_complete"] &= (len(selected) == settings["validation_roots_per_query"]
                and {row["root"]["episode"] for row in selected} == set(range(settings["validation_roots_per_query"])))
        for record in data["roots"]:
            root, log = dict(record["root"], life=life["id"]), record["terminal_log"]
            query = root["query"]
            for name in work:
                work[name].update(log[name])
            trajectories += log["trajectories"]
            accounting = (log["trajectories"] == len(OPTIONS) * replicas
                and sum(log["outcomes"].values()) == log["trajectories"]
                and log["planning_counts"].get("model_uniform_draws", 0) == 4 * log["ground_work"].get("sampled_transitions", 0))
            terminal = accounting and not log["censored_root"] and set(log["outcomes"]) <= set(TERMINAL)
            reference = record["paired_reference"]
            complete = (terminal and record["reference_complete"] and set(reference) == set(OPTIONS[1:])
                and all(len(vectors) == replicas for vectors in reference.values()))
            predictions = record["predictions"]
            roster = set(predictions) == set(methods) and all(set(row["predictions"]) == set(OPTIONS)
                for row in predictions.values())
            key = root["source_seed"], query, root["episode"]
            roster &= all(key in games[method] and row["option"] == games[method][key]["selected_option"]
                and row["step"] == games[method][key]["initiation_step"] == root["step"]
                and row["board"] == root["board"] for method, row in predictions.items())
            checks["reference_work_accounted"] &= accounting
            checks["all_reference_trajectories_terminal"] &= terminal
            checks["independent_reference_complete"] &= complete
            checks["deployed_prediction_rosters_complete"] &= roster
            summaries = {option: _paired_summary(vectors, query) for option, vectors in reference.items()}
            roots.append(dict(root=root, primary_estimable=complete and roster,
                paired_reference=summaries, outcomes=log["outcomes"]))
            if not complete or not roster:
                continue
            for method, prediction in predictions.items():
                predicted = [prediction["predictions"][option]["target"] for option in OPTIONS[1:]]
                target = [summaries[option]["mean_rfs"] for option in OPTIONS[1:]]
                error = predictive_error(predicted, target, query)
                selected = prediction["option"]
                errors.append(dict(life=life["id"], query=query, episode=root["episode"], method=method,
                    **error, selected_option=selected,
                    selected_reference_utility=0. if selected == "H2" else summaries[selected]["mean_utility"]))
    checks["validation_roster_complete"] &= not missing
    return dict(checks=checks, roots=roots, missing_roots=missing, root_errors=errors,
        methods=_history_summary(errors, settings, methods,
            ("mean_utility_bias", "mean_utility_mse", "selected_reference_utility")),
        work=dict(**{name: dict(counts) for name, counts in work.items()}, trajectories=trajectories, seconds=seconds),
        scope="The original deployed predictions and selections are frozen before natural outcomes and before "
            "the independent terminal reference. No selector or simulated prefix is rerun for validation. "
            "Prediction MSE includes finite reference uncertainty and, for DIRECT, the deployed finite-prefix "
            "simulation error. This is not a comparison of MC against itself. Root/option weights are equal "
            "within each learning history, then histories receive equal weights. Cutoffs retain all costs "
            "and exclude the fixed cohort from primary estimation without replacement.")

SIMULATION_WIRING = ("spawn_uniforms_aligned", "model_uniforms_aligned", "single_initiations",
    "committed_lengths_match", "terminal_absorbs")


def analyze_simulation(run):
    settings = run["settings"]
    methods = [name for name in settings["methods"] if "_DIRECT" in name]
    totals = {name: Counter() for name in ("model_work", "planning_counts", "value_counts", "outcomes")}
    groups, rows, trajectories, seconds = {}, [], 0, 0.
    checks = dict(simulated_rosters_complete=True, simulated_work_accounted=True,
        simulated_actor_rng_separate=True, simulated_terminal_semantics_match=True)
    for method in methods:
        groups[method] = dict(decisions=0, trajectories=0, seconds=0.,
            **{name: Counter() for name in totals})
    for life in run["lifecycles"]:
        stage = life["evaluation"]
        for method in methods:
            for game in stage["methods"][method]["games"]:
                log = game["candidate_evaluation"]
                checks["simulated_actor_rng_separate"] &= game["planning_counts"].get("model_uniform_draws", 0) == 4 * game["steps"]
                if log is None:
                    checks["simulated_rosters_complete"] &= game["initiation_step"] is None and game["selected_option"] is None
                    continue
                count = log["model_work"].get("synthetic_transitions", 0)
                checks["simulated_rosters_complete"] &= (game["initiation_step"] is not None
                    and log["replicas"] == settings["prefix_replicas"]
                    and log["trajectories"] == settings["prefix_replicas"] * len(OPTIONS))
                checks["simulated_work_accounted"] &= (sum(log["outcomes"].values()) == log["trajectories"]
                    and 0 < count <= settings["horizon"] * log["trajectories"]
                    and log["model_work"].get("spawn_uniform_draws", 0) == 2 * count
                    and log["model_work"].get("model_spawn_samples", 0) == count
                    and log["planning_counts"].get("model_uniform_draws", 0) == 4 * count
                    and log["value_counts"].get("paired_continuation_predictions", 0) == settings["prefix_replicas"] * (len(OPTIONS) - 1))
                checks["simulated_terminal_semantics_match"] &= (set(log["outcomes"]) <= {"ACTIVE", "WON", "LOST"}
                    and all(log["wiring"].get(name) is True for name in SIMULATION_WIRING))
                expected_actor = Counter()
                for name in ("model_work", "planning_counts", "value_counts"):
                    expected_actor.update(log[name])
                checks["simulated_work_accounted"] &= (all(game["planning_counts"].get("candidate_" + name, 0) == value
                    for name, value in expected_actor.items())
                    and game["planning_counts"].get("candidate_selector_decisions", 0) == 1
                    and game["planning_counts"].get("candidate_trajectories", 0) == log["trajectories"])
                for name in totals:
                    totals[name].update(log[name])
                    groups[method][name].update(log[name])
                groups[method]["decisions"] += 1
                groups[method]["trajectories"] += log["trajectories"]
                groups[method]["seconds"] += log["seconds"]
                trajectories += log["trajectories"]
                seconds += log["seconds"]
                rows.append(dict(life=life["id"], method=method, query=game["query"], replica=game["replica"],
                    synthetic_transitions=count, trajectories=log["trajectories"], outcomes=log["outcomes"], seconds=log["seconds"]))
    return dict(checks=checks, decisions=len(rows), trajectories=trajectories, seconds=seconds,
        **{name: dict(value) for name, value in totals.items()},
        methods={method: {name: dict(value) if isinstance(value, Counter) else value for name, value in data.items()}
            for method, data in groups.items()}, decisions_by_game=rows,
        scope="Simulation work is counted once from candidate_evaluation. The matching candidate_ counters "
            "inside actor planning logs are a duplicated accounting view, not additional executed work. "
            "Simulated selector seconds are already included in natural evaluation seconds. "
            "ACTIVE after four actions is an intended model boundary; it is not a terminal reference cutoff.")


def weighting_checks(log):
    close = lambda a, b: math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    summaries = [log["totals"], *log["queries"].values()]
    mass = log["totals"]["max_pair_mass_error"] <= 1e-12
    share = log["target_boundary_share"] == .5
    for row in summaries:
        prior, current = row["prior_total_mass"], row["new_total_mass"]
        mass &= (close(prior, current) and close(prior, row["rows"] / 32)
            and close(row["prior_boundary_mass"], row["groups"] / 32)
            and close(row["singleton_boundary_mass"], row["singletons"] / 32)
            and close(prior, row["prior_boundary_mass"] + row["prior_tail_mass"])
            and close(current, row["new_boundary_mass"] + row["new_tail_mass"]))
        if current:
            share &= (close(row["new_boundary_share"], .5 + .5 * row["singleton_boundary_mass"] / current)
                and close(row["new_boundary_share"], row["new_boundary_mass"] / current))
        else:
            share &= row["new_boundary_share"] is None
    mass &= (log["counts"]["groups"] == log["totals"]["groups"]
        and log["counts"]["training_rows"] == log["totals"]["rows"])
    return dict(boundary_pair_mass_preserved=mass, boundary_weight_share_matches=share)


def analyze_training(run):
    settings = run["settings"]
    queries, budgets, iterations = settings["queries"], settings["budgets"], settings["iterations"]
    families = ("PAIR_FQE", "BOUNDARY_FQE")
    checks = dict(allocation_rosters_complete=True, acquisition_budgets_match=True,
        acquisition_work_accounted=True, discarded_roots_have_no_labels=True,
        acquisition_cursors_continue=True, cumulative_coverage_matches=True,
        new_fitting_accounted=True, whole_episode_isolation=True,
        boundary_pair_mass_preserved=True, boundary_weight_share_matches=True,
        deployed_budget_and_episode_metadata_match=True, validation_reuses_deployed_predictions=True,
        primary_contrast_roster_matches=settings["contrasts"] == [list(pair) for pair in CONTRASTS])
    work = {kind: {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
        for kind in ("source", "branches")}
    partition = {kind: Counter() for kind in ("training", "heldout", "unincorporated")}
    counts, fit_counts = Counter(), Counter()
    seconds = dict(acquisition=0., weighting=0., fitting=0.)
    summaries, fit_summaries = [], []
    for life in run["lifecycles"]:
        allocations = life["allocations"]
        checks["allocation_rosters_complete"] &= (len(allocations) == len(settings["allocations"])
            and {row["replicas"] for row in allocations} == set(settings["allocations"]))
        model_metadata = {}
        for allocation in allocations:
            replicas = allocation["replicas"]
            stages = allocation["construction"]
            checks["allocation_rosters_complete"] &= [stage["budget"] for stage in stages] == budgets
            previous_budget = previous_cursor = used = allocation_fits = cumulative_rows = 0
            roots = []
            for stage in stages:
                budget, cutoff, acquisition = stage["budget"], stage["episode_cutoff"], stage["acquisition"]
                expected = budget - previous_budget
                source = acquisition["source"]["ground_work"].get("sampled_transitions", 0)
                branches = acquisition["branches"]["ground_work"].get("sampled_transitions", 0)
                used += acquisition["used_transitions"]
                checks["acquisition_budgets_match"] &= (acquisition["budget"] == acquisition["used_transitions"] == expected
                    and acquisition["unused_budget"] == 0 and acquisition["budget_exhausted"] is True and used == budget)
                parts = acquisition["cost_partition"]
                checks["acquisition_work_accounted"] &= (source + branches == acquisition["used_transitions"]
                    and sum(row["source_transitions"] for row in parts.values()) == source
                    and sum(row["branch_transitions"] for row in parts.values()) == branches
                    and set(parts) == set(partition)
                    and all(row["total_transitions"] == row["source_transitions"] + row["branch_transitions"] for row in parts.values()))
                for kind in work:
                    for name in work[kind]:
                        work[kind][name].update(acquisition[kind][name])
                    checks["acquisition_work_accounted"] &= acquisition[kind]["planning_counts"].get("model_uniform_draws", 0) == 4 * acquisition[kind]["ground_work"].get("sampled_transitions", 0)
                recorded = acquisition["root_records"]
                checks["acquisition_cursors_continue"] &= (acquisition["start_cursor"] == previous_cursor
                    and [row["cursor"] for row in recorded] == list(range(previous_cursor, acquisition["next_cursor"]))
                    and acquisition["next_cursor"] == stage["next_cursor"]
                    and cutoff == acquisition["episode_cutoff"] == acquisition["next_cursor"] // len(queries) + 1)
                checks["discarded_roots_have_no_labels"] &= all(row["complete_block"] or row["paired_rows"] == 0 for row in recorded)
                acounts = acquisition["counts"]
                checks["acquisition_work_accounted"] &= (acounts["source_games"] == len(recorded) == sum(acquisition["source"]["outcomes"].values())
                    and acounts["branch_trajectories"] == sum(acquisition["branches"]["outcomes"].values())
                    and acounts["source_transitions"] == source and acounts["branch_transitions"] == branches)
                completed = acquisition["completed_roots"]
                checks["cumulative_coverage_matches"] &= (len(completed) == acounts["complete_roots"]
                    and sum(root["paired_rows"] for root in completed) == acounts["paired_rows"]
                    and all(root["replicas"] == replicas and root["heldout"] == (root["episode"] % 5 == 4) for root in completed))
                roots.extend(completed)
                cumulative_rows += acounts["paired_rows"]
                coverage = {query: {role: sorted(root["episode"] for root in roots if root["query"] == query
                    and (root["episode"] % 5 == 4) == (role == "heldout"))
                    for role in ("training", "heldout")} for query in queries}
                checks["cumulative_coverage_matches"] &= (coverage == stage["cumulative_roots"]
                    and cumulative_rows == stage["cumulative_rows"])
                weighting = stage["weighting"]
                for key, value in weighting_checks(weighting).items():
                    checks[key] &= value
                checks["whole_episode_isolation"] &= weighting["checkpoint"] == cutoff
                checks["new_fitting_accounted"] &= set(stage["fit_logs"]) == set(families)
                for family, log in stage["fit_logs"].items():
                    expected_mc, expected_fqe = len(queries), len(queries) * iterations
                    expected_fits = expected_mc + expected_fqe
                    checks["new_fitting_accounted"] &= (log["checkpoint"] == cutoff and log["iterations"] == iterations
                        and log["counts"].get("tree_fits", 0) == expected_fits
                        and log["counts"].get("pair_mc_tree_fits", 0) == expected_mc
                        and log["counts"].get("pair_fqe_tree_fits", 0) == expected_fqe
                        and log["PAIR_FQE"]["initialization"] == "PAIR_MC"
                        and [row["iteration"] for row in log["PAIR_FQE"]["iterations"]] == list(range(1, iterations + 1)))
                    checks["whole_episode_isolation"] &= (set(log["training_episodes"]) == set(queries)
                        and log["training_episodes"] == weighting["eligible_episodes"])
                    for query, episodes in log["training_episodes"].items():
                        checks["whole_episode_isolation"] &= (all(episode < cutoff and episode % 5 != 4 for episode in episodes)
                            and set(episodes) <= set(coverage[query]["training"]))
                    allocation_fits += log["counts"]["tree_fits"]
                    fit_counts.update(log["counts"])
                    seconds["fitting"] += log["seconds"]
                    fit_summaries.append(dict(life=life["id"], replicas=replicas, budget=budget, family=family,
                        counts=log["counts"], seconds=log["seconds"], training_episodes=log["training_episodes"],
                        final_iteration=log["PAIR_FQE"]["iterations"][-1], heldout=log["heldout"]))
                for kind in partition:
                    partition[kind].update(parts[kind])
                counts.update(acounts)
                seconds["acquisition"] += acquisition["seconds"]
                seconds["weighting"] += weighting["seconds"]
                summaries.append(dict(life=life["id"], replicas=replicas, budget=budget,
                    episode_cutoff=cutoff, counts=acounts, cumulative_rows=cumulative_rows,
                    cumulative_roots=coverage, queries=acquisition["queries"], cost_partition=parts,
                    source_outcomes=acquisition["source"]["outcomes"], branch_outcomes=acquisition["branches"]["outcomes"],
                    incremental_transitions=source + branches, cumulative_transitions=used,
                    weighting=weighting["totals"]))
                previous_budget, previous_cursor = budget, acquisition["next_cursor"]
            checks["new_fitting_accounted"] &= allocation["new_tree_fits"] == allocation_fits
            checks["acquisition_budgets_match"] &= allocation["new_training_environment_transitions"] == used == budgets[-1]
            model_metadata.update(allocation["model_metadata"])
        evaluation = life["evaluation"]
        checks["deployed_budget_and_episode_metadata_match"] &= (model_metadata == evaluation["model_metadata"]
            and set(model_metadata) == set(settings["methods"]) - {"H2_ONLY"})
        for method, metadata in model_metadata.items():
            replicas = int(method.split("_")[0][1:])
            budget = budgets[0] if method.endswith("_FROZEN_HALF") else budgets[-1]
            matching = next(stage for allocation in allocations if allocation["replicas"] == replicas
                for stage in allocation["construction"] if stage["budget"] == budget)
            checks["deployed_budget_and_episode_metadata_match"] &= (metadata["replicas"] == replicas
                and metadata["budget"] == budget and metadata["episode_cutoff"] == matching["episode_cutoff"]
                and metadata["weighting"] == ("boundary_0.5" if "_BOUNDARY_" in method else "uniform")
                and all(game["selector_checkpoint"] == metadata["episode_cutoff"] for game in evaluation["methods"][method]["games"]))
        validation = evaluation["validation"]
        checks["validation_reuses_deployed_predictions"] &= validation["new_selector_calls"] == validation["new_model_transitions"] == 0
    return dict(checks=checks, checkpoints=summaries, counts=dict(counts), fit_counts=dict(fit_counts),
        fit_summaries=fit_summaries, work={kind: {name: dict(value) for name, value in group.items()} for kind, group in work.items()},
        cost_partition={kind: dict(value) for kind, value in partition.items()}, seconds=seconds,
        scope="Account only lifecycle allocations; run.allocations is a duplicate progress view. Source, "
            "heldout, cutoff and incomplete-root work is charged to the same physical budget. A partial "
            "root is discarded at the checkpoint and its roster item is not resumed. Fixed-budget stopping "
            "does not create an unbiased Monte Carlo estimator. Four versus eight replicas changes the "
            "realized root roster and precision jointly; it is a budgeted allocation comparison.")


def analyze_run(run):
    natural, validation = analyze_natural(run), analyze_validation(run)
    simulation, training = analyze_simulation(run), analyze_training(run)
    checks = dict(**natural["checks"], **validation["checks"], **simulation["checks"], **training["checks"])
    terminal = {"all_natural_games_terminal", "all_reference_trajectories_terminal", "independent_reference_complete"}
    complete = run["status"] == "complete" and all(value for name, value in checks.items() if name not in terminal)
    training_transitions = sum(group["ground_work"].get("sampled_transitions", 0) for group in training["work"].values())
    natural_transitions = natural["work"]["ground_work"].get("sampled_transitions", 0)
    reference_transitions = validation["work"]["ground_work"].get("sampled_transitions", 0)
    return dict(schema="acfqp.root_coverage_analysis.v98", complete=complete, primary_complete=complete and all(checks.values()),
        checks=checks, natural=natural, validation=validation, simulation=simulation, training=training,
        actual_executed_work=dict(new_tree_fits=training["fit_counts"].get("tree_fits", 0),
            new_mc_warm_start_fits=training["fit_counts"].get("pair_mc_tree_fits", 0),
            new_fqe_fits=training["fit_counts"].get("pair_fqe_tree_fits", 0),
            new_training_environment_transitions=training_transitions,
            new_natural_transitions=natural_transitions, new_reference_transitions=reference_transitions,
            newly_sampled_environment_transitions=training_transitions + natural_transitions + reference_transitions,
            training_seconds=training["seconds"], new_simulated_transitions=simulation["model_work"].get("synthetic_transitions", 0),
            simulated_trajectories=simulation["trajectories"], simulated_selector_calls=simulation["decisions"],
            simulated_model_work=simulation["model_work"], simulated_planning_counts=simulation["planning_counts"],
            simulated_value_counts=simulation["value_counts"], simulated_selection_seconds=simulation["seconds"],
            natural_evaluation_seconds=sum(cost["evaluation_seconds"] for method in natural["methods"].values() for cost in method["costs"]),
            reference_seconds=validation["work"]["seconds"], actual_wall_seconds=run["actual_wall_seconds"]),
        evidence_scope="Two-history exploratory pilot. Equal physical acquisition budgets include unsuccessful "
            "and heldout acquisition, and allocation arms share corresponding indexed streams. Within each "
            "allocation, uniform and boundary models share the same retained data. Independent references "
            "evaluate original deployed predictions, not retrained or resampled selectors. Report each history "
            "and the equal-history mean without an efficacy confidence interval or a new scientific Gate.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / "run.json").read_text()))
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(complete=result["complete"], primary_complete=result["primary_complete"],
        actual_executed_work=result["actual_executed_work"]), allow_nan=False))


if __name__ == "__main__":
    main()

