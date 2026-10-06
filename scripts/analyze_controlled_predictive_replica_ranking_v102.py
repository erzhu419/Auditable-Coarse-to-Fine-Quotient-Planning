"""Replica disagreement versus matched uniform margin shrinkage."""
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
from scripts.analyze_controlled_predictive_bellman_v94 import _paired_summary, _history_summary
from scripts.analyze_controlled_predictive_query_ranking_v100 import analyze_simulation, ranking_error
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility

TERMINAL = ("WON", "LOST")
WIRING = ("pretrigger_prefixes_match", "committed_lengths_match", "single_initiations",
    "model_uniforms_aligned", "same_choice_histories_match", "simulated_prefixes_paired", "simulated_work_matches")
FAMILIES = ("MEAN_SIGN", "REPLICA", "UNIFORM_SHRINK")
CONTRASTS = tuple(
    [(f"R{r}_REPLICA_DIRECT{s}", f"R{r}_{other}_DIRECT{s}")
        for s in ("", "_FROZEN_HALF") for r in (8, 4) for other in ("MEAN_SIGN", "UNIFORM_SHRINK")]
    + [(f"R{r}_{family}_DIRECT", f"R{r}_{family}_DIRECT_FROZEN_HALF")
        for r in (8, 4) for family in FAMILIES]
    + [(f"R{r}_{family}_DIRECT", "H2_ONLY") for r in (8, 4) for family in FAMILIES]
    + [(f"R{r}_REPLICA_DIRECT{s}", "PREFIX_ONLY_DIRECT") for s in ("", "_FROZEN_HALF") for r in (8, 4)])


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

def analyze_validation(run):
    settings = run["settings"]
    methods = [name for name in settings["methods"] if name != "H2_ONLY"]
    replicas = settings["reference_replicas"]
    roots, errors, calibrated, missing = [], [], [], []
    block_errors = {name: [] for name in ("A", "B")}
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
                expected = "prefix_utility" if method == "PREFIX_ONLY_DIRECT" else "rank_score"
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
                if method == "PREFIX_ONLY_DIRECT":
                    differences = [scores[option] - utility[option] for option in OPTIONS[1:]]
                    calibrated.append(dict(life=life["id"], query=query, episode=root["episode"], method=method,
                        mean_utility_bias=_mean(differences), mean_utility_mse=_mean(value * value for value in differences)))
                for name, start, stop in (("A", 0, replicas // 2), ("B", replicas // 2, replicas)):
                    block = dict(H2=0., **{option: _paired_summary(vectors[start:stop], query)["mean_utility"]
                        for option, vectors in reference.items()})
                    block_errors[name].append(dict(life=life["id"], query=query, episode=root["episode"], method=method,
                        selected_option=prediction["option"], **ranking_error(scores, block, prediction["option"])))
    checks["validation_roster_complete"] &= not missing
    return dict(checks=checks, roots=roots, missing_roots=missing, root_errors=errors,
        methods=_history_summary(errors, settings, methods,
            ("pairwise_weighted_error", "selected_reference_utility", "selected_reference_regret")),
        independent_blocks={name: dict(root_errors=rows, methods=_history_summary(rows, settings, methods,
            ("pairwise_weighted_error", "selected_reference_utility", "selected_reference_regret")))
            for name, rows in block_errors.items()},
        calibrated_utility_errors=_history_summary(calibrated, settings,
            ["PREFIX_ONLY_DIRECT"], ("mean_utility_bias", "mean_utility_mse")),
        work=dict(**{name: dict(counts) for name, counts in work.items()}, trajectories=trajectories, seconds=seconds),
        scope="Scores and selections are the deployed events fixed before independent terminal references. "
            "Ranking uses ten within-root option pairs weighted by absolute finite-reference utility difference; "
            "score ties count half an inversion and reference ties carry zero weight. All-reference-tied roots "
            "have zero weighted error. Rank scores receive no utility MSE. Selected reference regret uses the "
            "maximum of five noisy reference means and is descriptive, not true-policy regret. Roots receive "
            "equal weights within each history/query, then histories receive equal weights. A/B are the first/last16 "
            "independent suffix replicas; they neither select models nor alter the pool32 primary estimate. Reference uncertainty "
            "and finite model-prefix noise are retained; incomplete roots retain costs without replacement.")

def analyze_training(run):
    settings = run["settings"]
    queries, budgets = settings["queries"], settings["budgets"]
    checks = dict(allocation_rosters_complete=True, retained_acquisition_accounted=True,
        retained_complete_root_rosters_match=True, no_new_training_acquisition=True,
        new_fitting_accounted=True, whole_episode_isolation=True, retained_features_reused_without_simulation=True, replica_means_match_retained_labels=True,
        conflict_mass_from_training_roots=True, mean_sign_matches_frozen_v100=True,
        deployed_model_family_and_age_match=True, validation_reuses_deployed_predictions=True,
        primary_contrast_roster_matches=settings["contrasts"] == [list(pair) for pair in CONTRASTS])
    inherited = {kind: {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
        for kind in ("source", "branches")}
    partition = {kind: Counter() for kind in ("training", "heldout", "unincorporated")}
    prefix = {name: Counter() for name in ("model_work", "planning_counts", "feature_counts", "outcomes")}
    data_counts, fit_counts, diagnostic_counts = Counter(), Counter(), Counter()
    seconds = dict(retained_data_reading=0., fitting_total=0., by_model={family: 0. for family in FAMILIES})
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
                checks["no_new_training_acquisition"] &= (data["counts"]["new_environment_transitions"]
                    == data["counts"]["neural_model_fits"] == 0)
                checks["replica_means_match_retained_labels"] &= (data["replicas"] == replicas
                    and data["counts"]["mean_roots_verified"] == len(complete)
                    and data["counts"]["paired_replica_rows"] == replicas * len(complete)
                    and data["max_mean_utility_difference"] <= 1e-12)
                checks["mean_sign_matches_frozen_v100"] &= stage["baseline_equivalence"] is True
                training_roots = sum(len(row["training"]) for row in coverage.values())
                training_episodes = {query: row["training"] for query, row in coverage.items()}
                checks["whole_episode_isolation"] &= (fit["checkpoint"] == cutoff
                    and fit["training_episodes"] == training_episodes
                    and fit["training_roots"] == fit["normalization_training_roots"] == training_roots
                    and fit["heldout_roots"] == root_count - training_roots
                    and all(episode < cutoff and episode % 5 != 4 for roster in training_episodes.values() for episode in roster))
                checks["conflict_mass_from_training_roots"] &= (fit["conflict_mass_training_roots"] == training_roots
                    and fit["total_training_pairs"] == training_roots * 10
                    and fit["training_replica_rows"] == training_roots * replicas
                    and 0 <= fit["conflict_pairs"] <= fit["total_training_pairs"]
                    and math.isfinite(fit["uniform_gamma"]) and fit["uniform_gamma"] >= 0
                    and (fit["conflict_pairs"] > 0 or fit["uniform_gamma"] == 0))
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
                feature_prefixes = data["inherited_feature_prefixes"]
                trajectories = feature_prefixes["trajectories"]
                count = feature_prefixes["model_work"].get("synthetic_transitions", 0)
                checks["retained_features_reused_without_simulation"] &= (
                    data["counts"]["new_synthetic_transitions"] == data["counts"]["model_prefix_trajectories"]
                    == data["counts"]["neural_candidate_predictions"] == 0
                    and feature_prefixes["roots"] == len(complete)
                    and trajectories == len(complete) * settings["prefix_replicas"] * len(OPTIONS)
                    and sum(feature_prefixes["outcomes"].values()) == trajectories
                    and count <= trajectories * settings["horizon"]
                    and feature_prefixes["model_work"].get("spawn_uniform_draws", 0) == 2 * count
                    and feature_prefixes["planning_counts"].get("model_uniform_draws", 0) == 4 * count)
                for kind in inherited:
                    for name in inherited[kind]:
                        inherited[kind][name].update(acquisition[kind][name])
                for kind in partition:
                    partition[kind].update(acquisition["cost_partition"][kind])
                for name in prefix:
                    prefix[name].update(feature_prefixes[name])
                prefix_roots += feature_prefixes["roots"]
                prefix_trajectories += trajectories
                data_counts.update(data["counts"])
                seconds["retained_data_reading"] += data["seconds"]
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
            family = next(family for family in FAMILIES if method.startswith(f"R{replicas}_{family}_DIRECT"))
            checks["deployed_model_family_and_age_match"] &= (metadata["replicas"] == replicas and metadata["budget"] == budget
                and metadata["episode_cutoff"] == matching["episode_cutoff"] and metadata["family"] == family
                and all(game["selector_checkpoint"] == metadata["episode_cutoff"] for game in evaluation["methods"][method]["games"]))
        validation = evaluation["validation"]
        checks["validation_reuses_deployed_predictions"] &= validation["new_selector_calls"] == validation["new_model_transitions"] == 0
    return dict(checks=checks, checkpoints=summaries, data_counts=dict(data_counts), fit_counts=dict(fit_counts),
        diagnostic_counts=dict(diagnostic_counts), fit_summaries=fits, seconds=seconds,
        inherited_training_prefixes=dict(roots=prefix_roots, trajectories=prefix_trajectories,
            **{name: dict(value) for name, value in prefix.items()}),
        inherited_work={kind: {name: dict(value) for name, value in group.items()} for kind, group in inherited.items()},
        inherited_cost_partition={kind: dict(value) for kind, value in partition.items()},
        scope="Each retained V98 acquisition block is inherited once; top-level allocation views are duplicates. "
            "V100 model-prefix features are reused unchanged and charged only as inherited work. Per-replica "
            "terminal differences reproduce the original means. No new training acquisition or prefix simulation "
            "occurs. Uniform shrinkage uses only training-root conflict mass. Model and optimizer "
            "counts are billed from aggregate fit counts; per-model logs describe the same executions. Model "
            "fit times are components of fitting_total. Train/heldout label metrics are not independent validation.")


def analyze_run(run):
    natural, validation = analyze_natural(run), analyze_validation(run)
    simulation, training = analyze_simulation(run), analyze_training(run)
    checks = dict(**natural['checks'], **validation['checks'], **simulation['checks'], **training['checks'])
    terminal = {'all_natural_games_terminal', 'all_reference_trajectories_terminal', 'independent_reference_complete'}
    complete = run['status'] == 'complete' and all(value for name, value in checks.items() if name not in terminal)
    natural_transitions = natural['work']['ground_work'].get('sampled_transitions', 0)
    reference_transitions = validation['work']['ground_work'].get('sampled_transitions', 0)
    training_transitions = training['data_counts'].get('new_environment_transitions', 0)
    training_simulated = training['data_counts'].get('new_synthetic_transitions', 0)
    deployed_simulated = simulation['model_work'].get('synthetic_transitions', 0)
    return dict(schema='acfqp.replica_ranking_analysis.v102', complete=complete,
        primary_complete=complete and all(checks.values()), checks=checks,
        natural=natural, validation=validation, simulation=simulation, training=training,
        actual_executed_work=dict(new_neural_model_fits=training['fit_counts'].get('neural_model_fits', 0),
            new_optimizer_steps=training['fit_counts'].get('optimizer_steps', 0), new_tree_fits=0,
            new_training_environment_transitions=training_transitions, new_natural_transitions=natural_transitions,
            new_reference_transitions=reference_transitions,
            newly_sampled_environment_transitions=training_transitions + natural_transitions + reference_transitions,
            training_seconds=training['seconds'], training_simulated_transitions=training_simulated,
            deployed_simulated_transitions=deployed_simulated, new_simulated_transitions=training_simulated + deployed_simulated,
            inherited_training_prefixes=training['inherited_training_prefixes'],
            simulated_trajectories=simulation['trajectories'], simulated_selector_calls=simulation['decisions'],
            simulated_model_work=simulation['model_work'], simulated_planning_counts=simulation['planning_counts'],
            simulated_feature_counts=simulation['feature_counts'], simulated_value_counts=simulation['value_counts'],
            simulated_selection_seconds=simulation['seconds'],
            natural_evaluation_seconds=sum(cost['evaluation_seconds'] for method in natural['methods'].values() for cost in method['costs']),
            reference_seconds=validation['work']['seconds'], actual_wall_seconds=run['actual_wall_seconds']),
        evidence_scope='Compare empirical per-replica utility-weighted ranking against mean-sign ranking and '
            'a matched uniform margin shrinkage control. All reuse V100 features, network capacity, initialization, '
            'optimizer schedule, and V98 root groups. Gamma is mean absolute replica difference minus absolute '
            'mean difference; uniform gamma averages only eligible training roots and ten candidate pairs. '
            'MEAN_SIGN must reproduce frozen V100 parameters before evaluation. All learned outputs are ordinal. '
            'Reference pool32 is primary and the independent A/B16 blocks are descriptive; no reference outcome '
            'selects a model or enters training. Two histories form a pilot, without efficacy intervals or a scientific Gate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / 'run.json').read_text()))
    (args.directory / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'],
        actual_executed_work=result['actual_executed_work']), allow_nan=False))


if __name__ == '__main__':
    main()
