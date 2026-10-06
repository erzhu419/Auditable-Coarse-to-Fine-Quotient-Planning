"""Four-unit versus frozen sixteen-unit candidate ranking at matched data and losses."""
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
from scripts.analyze_controlled_predictive_query_ranking_v100 import analyze_simulation
from scripts.analyze_controlled_predictive_replica_ranking_v102 import analyze_validation
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS

TERMINAL = ("WON", "LOST")
WIRING = ("pretrigger_prefixes_match", "committed_lengths_match", "single_initiations",
    "model_uniforms_aligned", "same_choice_histories_match", "simulated_prefixes_paired", "simulated_work_matches")
FAMILIES = ("MEAN_SIGN", "REPLICA", "UNIFORM_SHRINK")
CURRENT = tuple(f"R{r}_H{h}_{family}_DIRECT" for r in (8, 4) for h in (4, 16) for family in FAMILIES)
CONTRASTS = tuple(
    [(f"R{r}_H4_{family}_DIRECT{s}", f"R{r}_H16_{family}_DIRECT{s}")
        for s in ("", "_FROZEN_HALF") for r in (8, 4) for family in FAMILIES]
    + [(method, method + "_FROZEN_HALF") for method in CURRENT]
    + [(method, "H2_ONLY") for method in CURRENT]
    + [(f"R{r}_H4_REPLICA_DIRECT{s}", "PREFIX_ONLY_DIRECT") for s in ("", "_FROZEN_HALF") for r in (8, 4)])


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
def analyze_training(run):
    settings = run["settings"]
    queries, budgets = settings["queries"], settings["budgets"]
    checks = dict(allocation_rosters_complete=True, retained_acquisition_accounted=True,
        retained_complete_root_rosters_match=True, no_new_training_acquisition=True,
        new_fitting_accounted=True, whole_episode_isolation=True, retained_features_reused_without_simulation=True, replica_means_match_retained_labels=True,
        conflict_mass_from_training_roots=True, wide_models_match_frozen_v102=True, frozen_baseline_work_accounted=True,
        capacity_parameter_penalty_matched=True, deployed_width_work_accounted=True,
        deployed_model_family_and_age_match=True, validation_reuses_deployed_predictions=True,
        primary_contrast_roster_matches=settings["contrasts"] == [list(pair) for pair in CONTRASTS])
    inherited = {kind: {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
        for kind in ("source", "branches")}
    partition = {kind: Counter() for kind in ("training", "heldout", "unincorporated")}
    prefix = {name: Counter() for name in ("model_work", "planning_counts", "feature_counts", "outcomes")}
    data_counts, fit_counts, diagnostic_counts = Counter(), Counter(), Counter()
    seconds = dict(retained_data_reading=0., fitting_total=0., by_model={family: 0. for family in FAMILIES})
    summaries, fits, frozen_fits, fit_comparisons, prefix_roots, prefix_trajectories = [], [], [], [], 0, 0
    frozen_models = inherited_fits = inherited_optimizer_steps = 0
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
                    and data["counts"]["roots_read"] == len(complete))
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
                    and data["inherited_v102_data_counts"]["paired_replica_rows"] == replicas * len(complete)
                    and data["max_mean_utility_difference"] <= 1e-12)
                frozen_fit = stage["frozen_fit_log"]
                checks["wide_models_match_frozen_v102"] &= (set(stage["baseline_equivalence"]) == set(FAMILIES)
                    and all(value is True for value in stage["baseline_equivalence"].values())
                    and set(stage["baseline_sources"]) == set(FAMILIES))
                checks["frozen_baseline_work_accounted"] &= (stage["frozen_baseline_count"] == len(FAMILIES)
                    and set(frozen_fit["models"]) == set(FAMILIES)
                    and frozen_fit["counts"]["neural_model_fits"] == len(FAMILIES)
                    and frozen_fit["counts"]["optimizer_steps"] == len(FAMILIES) * settings["optimizer_steps"])
                frozen_models += stage["frozen_baseline_count"]
                inherited_fits += frozen_fit["counts"]["neural_model_fits"]
                inherited_optimizer_steps += frozen_fit["counts"]["optimizer_steps"]
                frozen_fits.append(dict(life=life["id"], replicas=replicas, budget=budget, **frozen_fit))
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
                checks["capacity_parameter_penalty_matched"] &= (
                    fit["hidden"] == settings["hidden"] == 4
                    and settings["frozen_hidden"] == 16 and settings["widths"] == [4, 16]
                    and fit["parameter_count"] == settings["feature_dim"] * 4 + 8
                    and fit["l2_coefficient"] == settings["l2_coefficient"]
                    and fit["l2_reference_parameters"] == settings["l2_reference_parameters"] == 1968
                    and all(fit[field] == frozen_fit[field] for field in ("checkpoint", "training_episodes",
                        "training_roots", "heldout_roots", "normalization_training_roots", "uniform_gamma")))
                counts = fit["counts"]
                checks["new_fitting_accounted"] &= (set(fit["models"]) == set(FAMILIES)
                    and counts["neural_model_fits"] == len(FAMILIES)
                    and counts["optimizer_steps"] == len(FAMILIES) * settings["optimizer_steps"])
                for family, model in fit["models"].items():
                    checks["new_fitting_accounted"] &= (model["counts"]["neural_model_fits"] == 1
                        and model["counts"]["optimizer_steps"] == settings["optimizer_steps"]
                        and model["parameter_count"] == settings["feature_dim"] * settings["hidden"] + 2 * settings["hidden"])
                    wide_model = frozen_fit["models"][family]
                    checks["capacity_parameter_penalty_matched"] &= (model["hidden"] == 4
                        and model["l2_coefficient"] == settings["l2_coefficient"]
                        and wide_model["parameter_count"] == settings["feature_dim"] * 16 + 32)
                    fit_comparisons.append(dict(life=life["id"], replicas=replicas, budget=budget, family=family,
                        hidden4_parameter_count=model["parameter_count"], hidden16_parameter_count=wide_model["parameter_count"],
                        training={name: dict(hidden4=model["training"][name], hidden16=wide_model["training"][name],
                            delta=model["training"][name] - wide_model["training"][name])
                            for name in ("pairwise_weighted_error", "selected_empirical_regret")},
                        heldout={name: dict(hidden4=model["heldout"][name], hidden16=wide_model["heldout"][name],
                            delta=model["heldout"][name] - wide_model["heldout"][name]
                                if model["heldout"][name] is not None and wide_model["heldout"][name] is not None else None)
                            for name in ("pairwise_weighted_error", "selected_empirical_regret")}))
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
            replicas, hidden = int(method.split("_")[0][1:]), int(method.split("_")[1][1:])
            budget = budgets[0] if method.endswith("_FROZEN_HALF") else budgets[-1]
            matching = next(stage for allocation in allocations if allocation["replicas"] == replicas
                for stage in allocation["construction"] if stage["budget"] == budget)
            family = next(family for family in FAMILIES if method.startswith(f"R{replicas}_H{hidden}_{family}_DIRECT"))
            checks["deployed_model_family_and_age_match"] &= (metadata["replicas"] == replicas and metadata["budget"] == budget
                and metadata["hidden"] == hidden and hidden in settings["widths"]
                and metadata["parameter_count"] == settings["feature_dim"] * hidden + 2 * hidden
                and metadata["episode_cutoff"] == matching["episode_cutoff"] and metadata["family"] == family
                and all(game["selector_checkpoint"] == metadata["episode_cutoff"] for game in evaluation["methods"][method]["games"]))
            for game in evaluation["methods"][method]["games"]:
                log = game["candidate_evaluation"]
                if log is not None:
                    counts = log["value_counts"]
                    checks["deployed_width_work_accounted"] &= (counts["neural_candidate_predictions"] == len(OPTIONS)
                        and counts["neural_hidden_activations"] == len(OPTIONS) * hidden)
        validation = evaluation["validation"]
        checks["validation_reuses_deployed_predictions"] &= validation["new_selector_calls"] == validation["new_model_transitions"] == 0
    return dict(checks=checks, checkpoints=summaries, data_counts=dict(data_counts), fit_counts=dict(fit_counts),
        diagnostic_counts=dict(diagnostic_counts), fit_summaries=fits, frozen_fit_summaries=frozen_fits,
        capacity_fit_comparisons=fit_comparisons, frozen_baseline_models=frozen_models,
        inherited_v102_fit_counts=dict(neural_model_fits=inherited_fits, optimizer_steps=inherited_optimizer_steps), seconds=seconds,
        inherited_training_prefixes=dict(roots=prefix_roots, trajectories=prefix_trajectories,
            **{name: dict(value) for name, value in prefix.items()}),
        inherited_work={kind: {name: dict(value) for name, value in group.items()} for kind, group in inherited.items()},
        inherited_cost_partition={kind: dict(value) for kind, value in partition.items()},
        scope="Each retained V98 acquisition block is inherited once; top-level allocation views are duplicates. "
            "V100 model-prefix features are reused unchanged and charged only as inherited work. Per-replica "
            "terminal differences reproduce the original means. No new training acquisition or prefix simulation "
            "occurs. Four-unit models are newly fitted; sixteen-unit V102 models and their diagnostics are copied "
            "without fitting. Per-parameter L2 remains .001/1968 at both widths. Uniform shrinkage uses only "
            "training-root conflict mass. New model and optimizer "
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
    return dict(schema='acfqp.capacity_ranking_analysis.v103', complete=complete,
        primary_complete=complete and all(checks.values()), checks=checks,
        natural=natural, validation=validation, simulation=simulation, training=training,
        actual_executed_work=dict(new_neural_model_fits=training['fit_counts'].get('neural_model_fits', 0),
            new_optimizer_steps=training['fit_counts'].get('optimizer_steps', 0), new_tree_fits=0,
            frozen_baseline_models=training['frozen_baseline_models'],
            inherited_v102_fit_counts=training['inherited_v102_fit_counts'],
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
        evidence_scope='Compare a newly fitted four-unit model with the frozen sixteen-unit V102 model within '
            'each of three ordinal losses, two root allocations, and two budget ages. Both reuse identical V100 '
            'features and V98 terminal replica labels. Nonlinear query/candidate interactions remain available. '
            'Per-parameter L2 is fixed at .001/1968, so reducing width does not multiply this coefficient by four. '
            'Training and heldout diagnostics compare the same roots; independent pool32 references evaluate '
            'the deployed choices, with A/B16 retained descriptively. Narrow-model fits are new; copied wide-model '
            'fits and prefix features are inherited. Fixed optimizer steps do not establish equal convergence '
            'across widths, and this comparison does not prove a memorization mechanism. Two histories remain '
            'a descriptive pilot, without efficacy intervals or a scientific Gate.')


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
