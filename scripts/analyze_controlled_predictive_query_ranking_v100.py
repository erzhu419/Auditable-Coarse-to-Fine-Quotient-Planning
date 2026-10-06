"""Direct query-conditioned candidate ranking on retained complete roots."""
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
    _paired_summary, _history_summary,
)
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility

TERMINAL = ("WON", "LOST")
WIRING = ("pretrigger_prefixes_match", "committed_lengths_match", "single_initiations",
    "model_uniforms_aligned", "same_choice_histories_match", "simulated_prefixes_paired", "simulated_work_matches")
FAMILIES = ("UTILITY_MSE", "PAIRWISE_RANK")
CONTRASTS = tuple(
    [(f"R{r}_PAIRWISE_RANK_DIRECT{s}", f"R{r}_UTILITY_MSE_DIRECT{s}")
        for s in ("", "_FROZEN_HALF") for r in (8, 4)]
    + [(f"R{r}_{f}_DIRECT", f"R{r}_{f}_DIRECT_FROZEN_HALF") for r in (8, 4) for f in FAMILIES]
    + [(f"R{r}_{f}_DIRECT", "H2_ONLY") for r in (8, 4) for f in FAMILIES]
    + [(f"R{r}_PAIRWISE_RANK_DIRECT{s}", "PREFIX_ONLY_DIRECT")
        for s in ("", "_FROZEN_HALF") for r in (8, 4)])


def _gate_pairs(methods):
    return list(CONTRASTS)


def _comparisons(methods):
    return list(CONTRASTS)

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
                            categories["disabled"]["old"][f"mean_{metric}_contribution"],
                        new_or_changed_choice_comparator_contribution=math.fsum(
                            categories[name]["old"][f"mean_{metric}_contribution"]
                            for name in ("enabled", "changed_fragment")))
                    for metric in ("score", "utility")}

            gate[query] = dict(primary_estimable=primary, primary_attribution=attribution,
                available_common_terminal=data)
    return dict(methods=summaries, comparisons=comparisons, gate_decomposition=gates,
        paired_terminal_cohorts=cohorts, checks=checks,
        work={name: dict(value) for name, value in work.items()},
        scope="Two independent learning histories form a pilot. Report each history and equal-history "
            "means; no two-SE efficacy band or scientific Gate is computed.")


def ranking_error(scores, reference, selected):
    """Ten within-root comparisons; scalar score scale is deliberately irrelevant."""
    losses, weights = [], []
    for index, left in enumerate(OPTIONS):
        for right in OPTIONS[index + 1:]:
            difference = reference[left] - reference[right]
            predicted = scores[left] - scores[right]
            weight = abs(difference)
            weights.append(weight)
            losses.append(weight * (0.5 if predicted == 0 else float(difference * predicted < 0)))
    total = math.fsum(weights)
    return dict(pairwise_weighted_error=math.fsum(losses) / total if total else 0.,
        reference_pair_difference_mass=total,
        selected_reference_utility=reference[selected],
        selected_reference_regret=max(reference.values()) - reference[selected])


def analyze_validation(run):
    settings = run["settings"]
    methods = [name for name in settings["methods"] if name != "H2_ONLY"]
    replicas = settings["reference_replicas"]
    roots, errors, calibrated, missing = [], [], [], []
    work = {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
    trajectories, seconds = 0, 0.
    checks = dict(validation_roster_complete=True, reference_work_accounted=True,
        all_reference_trajectories_terminal=True, independent_reference_complete=True,
        deployed_prediction_rosters_complete=True, rank_scores_not_utility_estimates=True)
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
            for method, prediction in predictions.items():
                expected = ("rank_score" if "PAIRWISE_RANK" in method else
                    "prefix_utility" if method == "PREFIX_ONLY_DIRECT" else "utility_estimate")
                checks["rank_scores_not_utility_estimates"] &= prediction["score_semantics"] == expected
            checks["reference_work_accounted"] &= accounting
            checks["all_reference_trajectories_terminal"] &= terminal
            checks["independent_reference_complete"] &= complete
            checks["deployed_prediction_rosters_complete"] &= roster
            summaries = {option: _paired_summary(vectors, query) for option, vectors in reference.items()}
            roots.append(dict(root=root, primary_estimable=complete and roster,
                paired_reference=summaries, outcomes=log["outcomes"]))
            if not complete or not roster:
                continue
            utility = dict(H2=0., **{option: value["mean_utility"] for option, value in summaries.items()})
            for method, prediction in predictions.items():
                scores = {option: prediction["predictions"][option]["value"] for option in OPTIONS}
                errors.append(dict(life=life["id"], query=query, episode=root["episode"], method=method,
                    selected_option=prediction["option"], **ranking_error(scores, utility, prediction["option"])))
                if "PAIRWISE_RANK" not in method:
                    differences = [scores[option] - utility[option] for option in OPTIONS[1:]]
                    calibrated.append(dict(life=life["id"], query=query, episode=root["episode"], method=method,
                        mean_utility_bias=_mean(differences), mean_utility_mse=_mean(value * value for value in differences)))
    checks["validation_roster_complete"] &= not missing
    return dict(checks=checks, roots=roots, missing_roots=missing, root_errors=errors,
        methods=_history_summary(errors, settings, methods,
            ("pairwise_weighted_error", "selected_reference_utility", "selected_reference_regret")),
        calibrated_utility_errors=_history_summary(calibrated, settings,
            [method for method in methods if "PAIRWISE_RANK" not in method], ("mean_utility_bias", "mean_utility_mse")),
        work=dict(**{name: dict(counts) for name, counts in work.items()}, trajectories=trajectories, seconds=seconds),
        scope="Scores and selections are the deployed events fixed before independent terminal references. "
            "Ranking uses ten within-root option pairs weighted by absolute finite-reference utility difference; "
            "score ties count half an inversion and reference ties carry zero weight. All-reference-tied roots "
            "have zero weighted error. Rank scores receive no utility MSE. Selected reference regret uses the "
            "maximum of five noisy reference means and is descriptive, not true-policy regret. Roots receive "
            "equal weights within each history/query, then histories receive equal weights. Reference uncertainty "
            "and finite model-prefix noise are retained; incomplete roots retain costs without replacement.")



SIMULATION_WIRING = ("spawn_uniforms_aligned", "model_uniforms_aligned", "single_initiations",
    "committed_lengths_match", "terminal_absorbs")


def analyze_simulation(run):
    settings = run["settings"]
    methods = [name for name in settings["methods"] if "_DIRECT" in name]
    totals = {name: Counter() for name in ("model_work", "planning_counts", "feature_counts", "value_counts", "outcomes")}
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
                    and log["value_counts"].get("prefix_only_decisions" if method == "PREFIX_ONLY_DIRECT"
                        else "neural_candidate_predictions", 0) == (1 if method == "PREFIX_ONLY_DIRECT" else len(OPTIONS))
                    and (method != "PREFIX_ONLY_DIRECT" or log["value_counts"].get("neural_candidate_predictions", 0) == 0))
                checks["simulated_terminal_semantics_match"] &= (set(log["outcomes"]) <= {"ACTIVE", "WON", "LOST"}
                    and all(log["wiring"].get(name) is True for name in SIMULATION_WIRING))
                expected_actor = Counter()
                for name in ("model_work", "planning_counts", "feature_counts", "value_counts"):
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


def analyze_training(run):
    settings = run["settings"]
    queries, budgets = settings["queries"], settings["budgets"]
    checks = dict(allocation_rosters_complete=True, retained_acquisition_accounted=True,
        retained_complete_root_rosters_match=True, no_new_training_acquisition=True,
        new_fitting_accounted=True, whole_episode_isolation=True, training_model_work_accounted=True,
        deployed_model_family_and_age_match=True, validation_reuses_deployed_predictions=True,
        primary_contrast_roster_matches=settings["contrasts"] == [list(pair) for pair in CONTRASTS])
    inherited = {kind: {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
        for kind in ("source", "branches")}
    partition = {kind: Counter() for kind in ("training", "heldout", "unincorporated")}
    prefix = {name: Counter() for name in ("model_work", "planning_counts", "feature_counts", "outcomes")}
    data_counts, fit_counts, diagnostic_counts = Counter(), Counter(), Counter()
    seconds = dict(retained_extraction_and_prefixes=0., fitting_total=0., by_model={family: 0. for family in FAMILIES})
    summaries, fits, prefix_roots, prefix_trajectories = [], [], 0, 0
    for life in run["lifecycles"]:
        allocations, model_metadata = life["allocations"], {}
        checks["allocation_rosters_complete"] &= (len(allocations) == len(settings["allocations"])
            and {row["replicas"] for row in allocations} == set(settings["allocations"]))
        for allocation in allocations:
            replicas, stages = allocation["replicas"], allocation["construction"]
            checks["allocation_rosters_complete"] &= [stage["budget"] for stage in stages] == budgets
            previous_budget = previous_cursor = used = allocation_fits = root_count = 0
            roots = {query: {role: [] for role in ("training", "heldout")} for query in queries}
            for stage in stages:
                budget, cutoff, data, fit = stage["budget"], stage["episode_cutoff"], stage["data"], stage["fit_log"]
                acquisition = data["inherited_acquisition"]
                source = acquisition["source"]["ground_work"].get("sampled_transitions", 0)
                branches = acquisition["branches"]["ground_work"].get("sampled_transitions", 0)
                used += acquisition["used_transitions"]
                checks["retained_acquisition_accounted"] &= (acquisition["budget"] == budget - previous_budget
                    and acquisition["used_transitions"] == source + branches and used == budget
                    and sum(row["total_transitions"] for row in acquisition["cost_partition"].values()) == source + branches)
                complete = acquisition["completed_roots"]
                checks["retained_complete_root_rosters_match"] &= (data["start_cursor"] == previous_cursor
                    and data["next_cursor"] == acquisition["next_cursor"]
                    and data["episode_cutoff"] == cutoff
                    and data["counts"]["complete_roots"] == len(complete))
                for root in complete:
                    role = "heldout" if root["episode"] % 5 == 4 else "training"
                    roots[root["query"]][role].append(root["episode"])
                root_count += len(complete)
                coverage = {query: {role: sorted(values) for role, values in groups.items()} for query, groups in roots.items()}
                checks["retained_complete_root_rosters_match"] &= (coverage == stage["cumulative_roots"]
                    and root_count == stage["cumulative_root_count"]
                    and data["counts"]["training_roots"] + data["counts"]["heldout_roots"] == len(complete))
                checks["no_new_training_acquisition"] &= (data["counts"].get("new_environment_transitions", 0)
                    == data["counts"].get("tree_fits", 0) == 0)
                training_roots = sum(len(row["training"]) for row in coverage.values())
                training_episodes = {query: row["training"] for query, row in coverage.items()}
                checks["whole_episode_isolation"] &= (fit["checkpoint"] == cutoff
                    and fit["training_episodes"] == training_episodes
                    and fit["training_roots"] == fit["normalization_training_roots"] == training_roots
                    and fit["heldout_roots"] == root_count - training_roots
                    and all(episode < cutoff and episode % 5 != 4 for roster in training_episodes.values() for episode in roster))
                counts = fit["counts"]
                checks["new_fitting_accounted"] &= (set(fit["models"]) == set(FAMILIES)
                    and counts["neural_model_fits"] == len(FAMILIES)
                    and counts["optimizer_steps"] == len(FAMILIES) * settings["optimizer_steps"])
                for family, model in fit["models"].items():
                    checks["new_fitting_accounted"] &= (model["counts"]["neural_model_fits"] == 1
                        and model["counts"]["optimizer_steps"] == settings["optimizer_steps"]
                        and model["parameter_count"] == settings["feature_dim"] * settings["hidden"] + 2 * settings["hidden"])
                    diagnostic_counts.update({name: value for name, value in model["counts"].items()
                        if name not in ("neural_model_fits", "optimizer_steps")})
                    seconds["by_model"][family] += model["seconds"]
                allocation_fits += counts["neural_model_fits"]
                fit_counts.update(counts)
                seconds["fitting_total"] += fit["seconds"]
                trajectories, count = data["model_prefix_trajectories"], data["new_model_work"].get("synthetic_transitions", 0)
                checks["training_model_work_accounted"] &= (data["model_prefix_roots"] == len(complete)
                    and trajectories == len(complete) * settings["prefix_replicas"] * len(OPTIONS)
                    and sum(data["new_prefix_outcomes"].values()) == trajectories
                    and count <= trajectories * settings["horizon"]
                    and data["new_model_work"].get("spawn_uniform_draws", 0) == 2 * count
                    and data["new_planning_counts"].get("model_uniform_draws", 0) == 4 * count)
                for kind in inherited:
                    for name in inherited[kind]:
                        inherited[kind][name].update(acquisition[kind][name])
                for kind in partition:
                    partition[kind].update(acquisition["cost_partition"][kind])
                for name, field in (("model_work", "new_model_work"), ("planning_counts", "new_planning_counts"),
                        ("feature_counts", "new_feature_counts"), ("outcomes", "new_prefix_outcomes")):
                    prefix[name].update(data[field])
                prefix_roots += data["model_prefix_roots"]
                prefix_trajectories += trajectories
                data_counts.update(data["counts"])
                seconds["retained_extraction_and_prefixes"] += data["seconds"]
                summaries.append(dict(life=life["id"], replicas=replicas, budget=budget, episode_cutoff=cutoff,
                    cumulative_root_count=root_count, cumulative_roots=coverage,
                    inherited_incremental_transitions=source + branches, inherited_cumulative_transitions=used,
                    data_counts=data["counts"], inherited_cost_partition=acquisition["cost_partition"]))
                fits.append(dict(life=life["id"], replicas=replicas, budget=budget, **fit))
                previous_budget, previous_cursor = budget, data["next_cursor"]
            checks["new_fitting_accounted"] &= allocation["new_neural_model_fits"] == allocation_fits
            checks["no_new_training_acquisition"] &= allocation["new_training_environment_transitions"] == 0
            checks["retained_acquisition_accounted"] &= allocation["inherited_training_environment_transitions"] == used == budgets[-1]
            model_metadata.update(allocation["model_metadata"])
        evaluation = life["evaluation"]
        checks["deployed_model_family_and_age_match"] &= (model_metadata == evaluation["model_metadata"]
            and set(model_metadata) == set(settings["methods"]) - {"H2_ONLY", "PREFIX_ONLY_DIRECT"}
            and all(game["selector_checkpoint"] is None for game in evaluation["methods"]["PREFIX_ONLY_DIRECT"]["games"]))
        for method, metadata in model_metadata.items():
            replicas = int(method.split("_")[0][1:])
            budget = budgets[0] if method.endswith("_FROZEN_HALF") else budgets[-1]
            matching = next(stage for allocation in allocations if allocation["replicas"] == replicas
                for stage in allocation["construction"] if stage["budget"] == budget)
            family = "PAIRWISE_RANK" if "PAIRWISE_RANK" in method else "UTILITY_MSE"
            checks["deployed_model_family_and_age_match"] &= (metadata["replicas"] == replicas and metadata["budget"] == budget
                and metadata["episode_cutoff"] == matching["episode_cutoff"] and metadata["family"] == family
                and all(game["selector_checkpoint"] == metadata["episode_cutoff"] for game in evaluation["methods"][method]["games"]))
        validation = evaluation["validation"]
        checks["validation_reuses_deployed_predictions"] &= validation["new_selector_calls"] == validation["new_model_transitions"] == 0
    return dict(checks=checks, checkpoints=summaries, data_counts=dict(data_counts), fit_counts=dict(fit_counts),
        diagnostic_counts=dict(diagnostic_counts), fit_summaries=fits, seconds=seconds,
        training_prefixes=dict(roots=prefix_roots, trajectories=prefix_trajectories,
            **{name: dict(value) for name, value in prefix.items()}),
        inherited_work={kind: {name: dict(value) for name, value in group.items()} for kind, group in inherited.items()},
        inherited_cost_partition={kind: dict(value) for kind, value in partition.items()},
        scope="Each retained V98 acquisition block is inherited once; top-level allocation views are duplicates. "
            "Each complete root receives one new model-only prefix batch shared by both objectives and reused "
            "at the later budget checkpoint. New training environment acquisition is zero. Model and optimizer "
            "counts are billed from aggregate fit counts; per-model logs describe the same executions. Model "
            "fit times are components of fitting_total. Train/heldout label metrics are not independent validation.")


def analyze_run(run):
    natural, validation = analyze_natural(run), analyze_validation(run)
    simulation, training = analyze_simulation(run), analyze_training(run)
    checks = dict(**natural["checks"], **validation["checks"], **simulation["checks"], **training["checks"])
    terminal = {"all_natural_games_terminal", "all_reference_trajectories_terminal", "independent_reference_complete"}
    complete = run["status"] == "complete" and all(value for name, value in checks.items() if name not in terminal)
    natural_transitions = natural["work"]["ground_work"].get("sampled_transitions", 0)
    reference_transitions = validation["work"]["ground_work"].get("sampled_transitions", 0)
    training_simulated = training["training_prefixes"]["model_work"].get("synthetic_transitions", 0)
    deployed_simulated = simulation["model_work"].get("synthetic_transitions", 0)
    return dict(schema="acfqp.query_ranking_analysis.v100", complete=complete, primary_complete=complete and all(checks.values()),
        checks=checks, natural=natural, validation=validation, simulation=simulation, training=training,
        actual_executed_work=dict(new_neural_model_fits=training["fit_counts"].get("neural_model_fits", 0),
            new_optimizer_steps=training["fit_counts"].get("optimizer_steps", 0), new_tree_fits=0,
            new_training_environment_transitions=0, new_natural_transitions=natural_transitions,
            new_reference_transitions=reference_transitions, newly_sampled_environment_transitions=natural_transitions + reference_transitions,
            training_seconds=training["seconds"], training_simulated_transitions=training_simulated,
            deployed_simulated_transitions=deployed_simulated, new_simulated_transitions=training_simulated + deployed_simulated,
            simulated_trajectories=simulation["trajectories"], simulated_selector_calls=simulation["decisions"],
            simulated_model_work=simulation["model_work"], simulated_planning_counts=simulation["planning_counts"],
            simulated_feature_counts=simulation["feature_counts"], simulated_value_counts=simulation["value_counts"],
            simulated_selection_seconds=simulation["seconds"],
            natural_evaluation_seconds=sum(cost["evaluation_seconds"] for method in natural["methods"].values() for cost in method["costs"]),
            reference_seconds=validation["work"]["seconds"], actual_wall_seconds=run["actual_wall_seconds"]),
        evidence_scope="Matched candidate features, neural capacity, initialization and fixed optimizer schedule "
            "compare direct scalar utility regression with utility-difference-weighted pairwise ranking. This "
            "isolates the prescribed objective change within V100, not capacity or architecture differences "
            "from V99. H2 remains the behavioral baseline and PREFIX_ONLY a diagnostic comparator. Independent "
            "reference means assess ordering and selected returns without treating rank scores as utilities. "
            "Two learning histories remain a descriptive pilot, without an efficacy interval or a new scientific Gate.")


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
