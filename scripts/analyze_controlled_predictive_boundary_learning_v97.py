"""Within-pair boundary emphasis with unchanged trajectory mass and independent references."""
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
    _lifecycle_uncertainty, _paired_summary, predictive_error, _history_summary,
)
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility

TERMINAL = ("WON", "LOST")
WIRING = ("pretrigger_prefixes_match", "committed_lengths_match", "single_initiations",
    "model_uniforms_aligned", "same_choice_histories_match", "simulated_prefixes_paired", "simulated_work_matches")
from scripts.run_controlled_predictive_boundary_learning_v97 import CONTRASTS
from scripts.analyze_controlled_predictive_direct_value_v95 import analyze_validation


def _gate_pairs(methods):
    return list(CONTRASTS)


def _comparisons(methods):
    pairs = _gate_pairs(methods)
    pairs += [(method, "H2_ONLY") for method in methods
        if method != "H2_ONLY" and (method, "H2_ONLY") not in pairs]
    return pairs


def analyze_natural(run):
    settings, output = run["settings"], {}
    lives, queries = settings["lifecycles"], settings["queries"]
    indexed = {life["id"]: life for life in run["lifecycles"]}
    checks = dict(lifecycle_roster_complete=len(indexed) == len(run["lifecycles"]) == len(lives)
        and set(indexed) == set(lives), checkpoint_rosters_complete=True,
        natural_rosters_complete=True, natural_streams_paired=True, controller_wiring_complete=True,
        gate_rosters_complete=True, all_natural_games_terminal=True)
    for life in run["lifecycles"]:
        checks["checkpoint_rosters_complete"] &= (len(life["checkpoints"]) == len(settings["checkpoints"])
            and {stage["episodes"] for stage in life["checkpoints"]} == set(settings["checkpoints"]))
    work = {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
    for checkpoint in settings["checkpoints"]:
        methods = settings["methods_by_checkpoint"][str(checkpoint)]
        stages = {life: next(stage for stage in indexed[life]["checkpoints"] if stage["episodes"] == checkpoint)
            for life in lives}
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
                    available_common_terminal=available,
                    descriptive_lifecycle_uncertainty=_lifecycle_uncertainty(rows) if primary else None)
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
        output[str(checkpoint)] = dict(methods=summaries, comparisons=comparisons,
            gate_decomposition=gates, paired_terminal_cohorts=cohorts)
    return dict(checkpoints=output, checks=checks, work={name: dict(value) for name, value in work.items()})





SIMULATION_WIRING = ("spawn_uniforms_aligned", "model_uniforms_aligned", "single_initiations",
    "committed_lengths_match", "terminal_absorbs")


def analyze_simulation(run):
    settings = run["settings"]
    methods = [name for name in settings["methods_by_checkpoint"]["12"] if "_DIRECT" in name]
    totals = {name: Counter() for name in ("model_work", "planning_counts", "value_counts", "outcomes")}
    groups, rows, trajectories, seconds = {}, [], 0, 0.
    checks = dict(simulated_rosters_complete=True, simulated_work_accounted=True,
        simulated_actor_rng_separate=True, simulated_terminal_semantics_match=True)
    for method in methods:
        groups[method] = dict(decisions=0, trajectories=0, seconds=0.,
            **{name: Counter() for name in totals})
    for life in run["lifecycles"]:
        stage = life["checkpoints"][0]
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


def boundary_diagnostic_checks(log, settings):
    models = {"PAIR_MC", "PAIR_FQE", "BOUNDARY_MC", "BOUNDARY_FQE"}
    valid = log["scoring_weight"] == 1 / 32 and set(log["queries"]) == set(settings["queries"])
    for row in log["queries"].values():
        strata = row["strata"]
        valid &= (set(strata) == {"all", "boundary", "tail"}
            and row["rows"] == strata["all"]["rows"] == strata["boundary"]["rows"] + strata["tail"]["rows"]
            and all(episode < log["checkpoint"] and episode % 5 == 4 for episode in row["episodes"]))
        for stratum in strata.values():
            valid &= stratum["weight_sum"] == stratum["rows"] / 32 and set(stratum["models"]) == models
    counted = Counter(log["feature_counts"])
    for value in log["model_counts"].values():
        counted.update(value)
    return dict(heldout_scoring_unchanged=valid,
        boundary_diagnostic_work_accounted=dict(counted) == log["counts"]
            and counted.get("tree_fits", 0) == counted.get("new_environment_transitions", 0) == 0)


def analyze_construction(run):
    settings = run["settings"]
    iterations, queries = settings["iterations"], settings["queries"]
    checkpoints = settings["model_checkpoints"]
    expected_inherited = {name for name in settings["methods_by_checkpoint"]["12"] if name.startswith("PAIR_")}
    checks = dict(construction_rosters_complete=True, new_fitting_accounted=True,
        whole_episode_isolation=True, retained_data_contracts_match=True,
        no_new_training_environment=True, inherited_model_rosters_match=True,
        validation_reuses_deployed_predictions=True,
        primary_contrast_roster_matches=settings["contrasts"] == [list(pair) for pair in CONTRASTS])
    checks.update(boundary_pair_mass_preserved=True, boundary_weight_share_matches=True,
        heldout_scoring_unchanged=True, boundary_diagnostic_work_accounted=True)
    totals, data_counts = Counter(), Counter()
    inherited_work = {name: Counter() for name in ("source", "branches")}
    seconds = dict(input_preparation=0., weighting=0., feature_cache=0., boundary_mc=0., boundary_fqe=0.,
        heldout_evaluation=0., fitting_total=0., boundary_diagnostics=0.)
    records, diagnostics, heldout_diagnostics, inherited_rows = [], [], [], []
    historical_fits, historical_pair_fits = 0, 0
    diagnostic_counts, boundary_rows = Counter(), []
    for life in run["lifecycles"]:
        stage = life["checkpoints"][0]
        constructions = stage["construction"]
        checks["construction_rosters_complete"] &= (len(constructions) == len(checkpoints)
            and [record["checkpoint"] for record in constructions] == checkpoints)
        life_fits = 0
        for record in constructions:
            checkpoint, data, fit = record["checkpoint"], record["data"], record["fit_log"]
            weighting, boundary = record["weighting"], record["diagnostics"]
            for key, value in dict(**weighting_checks(weighting), **boundary_diagnostic_checks(boundary, settings)).items():
                checks[key] &= value
            checks["whole_episode_isolation"] &= (weighting["checkpoint"] == boundary["checkpoint"] == checkpoint
                and weighting["eligible_episodes"] == fit["training_episodes"])
            counts, mc, fqe = fit["counts"], fit["PAIR_MC"], fit["PAIR_FQE"]
            expected_mc, expected_fqe = len(queries), len(queries) * iterations
            checks["new_fitting_accounted"] &= (fit["checkpoint"] == checkpoint
                and fit["iterations"] == iterations and fqe["initialization"] == "PAIR_MC"
                and counts.get("tree_fits", 0) == expected_mc + expected_fqe
                and counts.get("pair_mc_tree_fits", 0) == mc["counts"].get("tree_fits", 0) == expected_mc
                and counts.get("pair_fqe_tree_fits", 0) == fqe["counts"].get("tree_fits", 0) == expected_fqe
                and [row["iteration"] for row in fqe["iterations"]] == list(range(1, iterations + 1)))
            checks["whole_episode_isolation"] &= set(fit["training_episodes"]) == set(fit["queries"]) == set(queries)
            for query in queries:
                roster = fit["training_episodes"][query]
                checks["whole_episode_isolation"] &= (bool(roster)
                    and len(roster) == fit["queries"][query]["training_episode_count"]
                    and all(episode < checkpoint and episode % 5 != 4 for episode in roster))
                checks["new_fitting_accounted"] &= (mc["queries"][query]["counts"].get("tree_fits", 0) == 1
                    and fqe["queries"][query]["counts"].get("tree_fits", 0) == iterations
                    and all(row["queries"][query]["counts"].get("tree_fits", 0) == 1
                        for row in fqe["iterations"]))
                for family, diagnostic in (("PAIR_MC", mc["queries"][query]),
                        ("PAIR_FQE", fqe["iterations"][-1]["queries"][query])):
                    diagnostics.append(dict(life=life["id"], checkpoint=checkpoint, query=query, family=family.replace("PAIR_", "BOUNDARY_"),
                        training_rows=fit["queries"][query]["training_rows"],
                        **{key: diagnostic[key] for key in ("mean_prediction_rfs", "mean_target_rfs",
                            "fit_target_mse_rfs", "mean_terminal_mass_gap", "mean_absolute_terminal_mass_gap")}))
                    diagnostics[-1]["utility_mse"] = diagnostic["utility_mse"]
            heldout = fit["heldout"]
            checks["new_fitting_accounted"] &= heldout["counts"].get("tree_fits", 0) == 0
            for query, diagnostic in heldout["queries"].items():
                checks["whole_episode_isolation"] &= (all(
                    episode < checkpoint and episode % 5 == 4 for episode in diagnostic["episodes"])
                    and not set(diagnostic["episodes"]) & set(fit["training_episodes"][query]))
                heldout_diagnostics.append(dict(life=life["id"], checkpoint=checkpoint, query=query, **diagnostic))
            checks["retained_data_contracts_match"] &= (data["paired_crn_contract_matches"] is True
                and data["retained_means_match"] is True)
            checks["no_new_training_environment"] &= (data["counts"].get("new_environment_transitions", 0)
                == data["counts"].get("tree_fits", 0)
                == weighting["counts"].get("new_environment_transitions", 0)
                == weighting["counts"].get("tree_fits", 0) == 0)
            totals.update(counts)
            totals.update(boundary["counts"])
            diagnostic_counts.update(boundary["counts"])
            boundary_rows.append(dict(life=life["id"], **boundary))
            data_counts.update(data["counts"])
            life_fits += counts["tree_fits"]
            seconds["input_preparation"] += data["seconds"]
            seconds["feature_cache"] += fit["cache_seconds"]
            seconds["weighting"] += weighting["seconds"]
            seconds["boundary_mc"] += mc["seconds"]
            seconds["boundary_fqe"] += fqe["seconds"]
            seconds["boundary_diagnostics"] += boundary["seconds"]
            seconds["heldout_evaluation"] += heldout["seconds"]
            seconds["fitting_total"] += fit["seconds"]
            records.append(dict(life=life["id"], **record))
        checks["new_fitting_accounted"] &= stage["new_tree_fits"] == life_fits
        checks["no_new_training_environment"] &= stage["new_training_environment_transitions"] == 0
        validation = stage["validation"]
        checks["validation_reuses_deployed_predictions"] &= validation["new_selector_calls"] == validation["new_model_transitions"] == 0
        models, history = stage["inherited_models"], stage["inherited_training"]
        checks["inherited_model_rosters_match"] &= set(models) == expected_inherited
        for method in settings["methods_by_checkpoint"]["12"]:
            if method == "H2_ONLY":
                continue
            checkpoint = 6 if method.endswith("_FROZEN_6") else 12
            checks["inherited_model_rosters_match"] &= all(
                game["selector_checkpoint"] == checkpoint for game in stage["methods"][method]["games"])
        for method, model in models.items():
            checkpoint = 6 if method.endswith("_FROZEN_6") else 12
            checks["inherited_model_rosters_match"] &= (model["checkpoint"] == checkpoint
                and set(model["paths"]) == {"value"})
        for name in inherited_work:
            inherited_work[name].update(history[name])
        historical_fits += stage["historical_v94_tree_fits"]
        historical_pair_fits += stage["historical_v96_tree_fits"]
        inherited_rows.append(dict(life=life["id"], models=models,
            historical_v94_tree_fits=stage["historical_v94_tree_fits"],
            historical_v96_tree_fits=stage["historical_v96_tree_fits"]))
    return dict(checks=checks, counts=dict(totals), data_counts=dict(data_counts), seconds=seconds,
        constructions=records, final_training_diagnostics=diagnostics, heldout_diagnostics=heldout_diagnostics,
        boundary_diagnostics=boundary_rows, boundary_diagnostic_counts=dict(diagnostic_counts),
        inherited=dict(lifecycles=inherited_rows, historical_v94_tree_fits=historical_fits,
            historical_v96_tree_fits=historical_pair_fits,
            acquisition={name: dict(counts) for name, counts in inherited_work.items()}),
        scope="Only whole-episode training rows before each model checkpoint enter the full models. "
            "There are no downstream fitted labels requiring OOF models. Iteration errors use that iteration's "
            "frozen targets; they are not fixed-point residuals or convergence evidence. Signed and absolute "
            "terminal-mass gaps are diagnostics, never integrity or adoption gates. All four models receive "
            "the same original 1/32 scoring weights in boundary_diagnostics. These new diagnostic predictions "
            "include calls to inherited models and are charged once in V97. Extraction reads retained "
            "environment work, which is inherited once rather than newly sampled or charged again per checkpoint.")


def analyze_prediction_mass(run):
    methods = [name for name in run["settings"]["methods_by_checkpoint"]["12"] if name != "H2_ONLY"]
    rows = []
    for life in run["lifecycles"]:
        for record in life["checkpoints"][0]["validation"]["roots"]:
            for method, event in record["predictions"].items():
                gaps = [sum(event["predictions"][option]["target"][1:]) for option in OPTIONS[1:]]
                rows.append(dict(life=life["id"], query=record["root"]["query"],
                    episode=record["root"]["episode"], method=method,
                    mean_terminal_mass_gap=_mean(gaps), mean_absolute_terminal_mass_gap=_mean(map(abs, gaps))))
    return dict(roots=rows, methods=_history_summary(rows, run["settings"], methods,
        ("mean_terminal_mass_gap", "mean_absolute_terminal_mass_gap")),
        scope="At each common active root, true completed candidate-minus-H2 failure plus success is zero. "
            "This diagnostic reuses original deployed predictions; it requires no terminal labels or model calls. "
            "Antisymmetry does not enforce this identity. Missing references do not erase existing predictions.")


def analyze_run(run):
    natural, validation = analyze_natural(run), analyze_validation(run)
    simulation, construction = analyze_simulation(run), analyze_construction(run)
    checks = dict(**natural["checks"], **validation["checks"], **simulation["checks"], **construction["checks"])
    terminal_checks = {"all_natural_games_terminal", "all_reference_trajectories_terminal", "independent_reference_complete"}
    complete = run["status"] == "complete" and all(value for name, value in checks.items() if name not in terminal_checks)
    natural_work = natural["work"]["ground_work"].get("sampled_transitions", 0)
    reference_work = validation["work"]["ground_work"].get("sampled_transitions", 0)
    return dict(schema="acfqp.boundary_learning_analysis.v97", complete=complete,
        primary_complete=complete and all(checks.values()), checks=checks, natural=natural,
        validation=validation, simulation=simulation, construction=construction,
        prediction_mass=analyze_prediction_mass(run), inherited=construction["inherited"],
        inherited_data=run["inherited_data"],
        actual_executed_work=dict(new_tree_fits=construction["counts"].get("tree_fits", 0),
            new_boundary_mc_fits=construction["counts"].get("pair_mc_tree_fits", 0),
            new_boundary_fqe_fits=construction["counts"].get("pair_fqe_tree_fits", 0),
            new_training_environment_transitions=0,
            new_natural_transitions=natural_work, new_reference_transitions=reference_work,
            newly_sampled_environment_transitions=natural_work + reference_work,
            construction_seconds=construction["seconds"],
            new_simulated_transitions=simulation["model_work"].get("synthetic_transitions", 0),
            simulated_trajectories=simulation["trajectories"], simulated_selector_calls=simulation["decisions"],
            simulated_model_work=simulation["model_work"], simulated_planning_counts=simulation["planning_counts"],
            simulated_value_counts=simulation["value_counts"], simulated_selection_seconds=simulation["seconds"],
            natural_evaluation_seconds=sum(cost["evaluation_seconds"] for stage in natural["checkpoints"].values()
                for method in stage["methods"].values() for cost in method["costs"]),
            reference_seconds=validation["work"]["seconds"], actual_wall_seconds=run["actual_wall_seconds"]),
        evidence_scope="Boundary-versus-original comparisons preserve each trajectory pair's total weight, "
            "rows, representation, capacity, data and simulation budget; only within-pair training positions "
            "are reweighted. Original length weighting is retained. Heldout boundary/tail comparisons use "
            "the same original 1/32 scoring weight for all models. Independent finite references evaluate "
            "the original deployed predictions. Histories receive equal weights and descriptive two-SE "
            "bands are not calibrated confidence intervals. No new scientific Gate is introduced.")


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
