"""Frozen head versus direct four-step planning with independent terminal references."""
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
VALUE_METHODS = ("MC_TAIL", "FQE")
CONTRASTS = [(name + "_DIRECT" + suffix, name + suffix)
    for suffix in ("", "_FROZEN_6") for name in VALUE_METHODS]
CONTRASTS += [("FQE_DIRECT" + suffix, "MC_TAIL_DIRECT" + suffix) for suffix in ("", "_FROZEN_6")]
CONTRASTS += [(name + "_DIRECT", "H2_ONLY") for name in VALUE_METHODS]
CONTRASTS += [(name + interface, name + interface + "_FROZEN_6")
    for interface in ("", "_DIRECT") for name in VALUE_METHODS]


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





def analyze_validation(run):
    settings = run["settings"]
    methods = [name for name in settings["methods_by_checkpoint"]["12"] if name != "H2_ONLY"]
    replicas = settings["reference_replicas"]
    roots, errors, missing = [], [], []
    work = {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
    trajectories, seconds = 0, 0.
    checks = dict(validation_roster_complete=True, reference_work_accounted=True,
        all_reference_trajectories_terminal=True, independent_reference_complete=True,
        deployed_prediction_rosters_complete=True)
    for life in run["lifecycles"]:
        stage = life["checkpoints"][0]
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
                    and log["value_counts"].get("continuation_predictions", 0) == log["outcomes"].get("ACTIVE", 0))
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


def analyze_inheritance(run):
    settings, rows = run["settings"], []
    expected_methods = set(settings["methods_by_checkpoint"]["12"]) - {"H2_ONLY"}
    work = {name: Counter() for name in ("source", "branches")}
    historical_fits = 0
    checks = dict(no_new_training_or_fitting=True, inherited_model_rosters_match=True,
        validation_reuses_deployed_predictions=True,
        primary_contrast_roster_matches=settings["contrasts"] == [list(pair) for pair in CONTRASTS])
    for life in run["lifecycles"]:
        stage = life["checkpoints"][0]
        checks["no_new_training_or_fitting"] &= stage["new_tree_fits"] == stage["new_training_environment_transitions"] == 0
        validation = stage["validation"]
        checks["validation_reuses_deployed_predictions"] &= validation["new_selector_calls"] == validation["new_model_transitions"] == 0
        models, history = stage["inherited_models"], stage["inherited_training"]
        checks["inherited_model_rosters_match"] &= set(models) == expected_methods
        for method, model in models.items():
            checkpoint = 6 if method.endswith("_FROZEN_6") else 12
            kind = "value" if "_DIRECT" in method else "head"
            checks["inherited_model_rosters_match"] &= (model["checkpoint"] == checkpoint
                and set(model["paths"]) == {kind}
                and all(game["selector_checkpoint"] == checkpoint for game in stage["methods"][method]["games"]))
            if "_DIRECT" in method:
                checks["inherited_model_rosters_match"] &= model["training_acquisition"] == models[method.replace("_DIRECT", "")]["training_acquisition"]
            acquisition = model["training_acquisition"]
            checks["inherited_model_rosters_match"] &= (acquisition["prefix_transitions"] == acquisition["extra_terminal_transitions"] == 0
                and acquisition["total_training_transitions"] == acquisition["source_transitions"] + acquisition["base_branch_transitions"])
            if checkpoint == 12:
                checks["inherited_model_rosters_match"] &= (acquisition["source_transitions"] == history["source"].get("sampled_transitions", 0)
                    and acquisition["base_branch_transitions"] == history["branches"].get("sampled_transitions", 0))
        for name in work:
            work[name].update(history[name])
        historical_fits += stage["historical_v94_tree_fits"]
        rows.append(dict(life=life["id"], inherited_models=models,
            historical_v94_tree_fits=stage["historical_v94_tree_fits"]))
    return dict(checks=checks, lifecycles=rows, acquisition={name: dict(counts) for name, counts in work.items()},
        historical_v94_tree_fits=historical_fits)


def analyze_run(run):
    natural, validation = analyze_natural(run), analyze_validation(run)
    simulation, inherited = analyze_simulation(run), analyze_inheritance(run)
    checks = dict(**natural["checks"], **validation["checks"], **simulation["checks"], **inherited["checks"])
    terminal_checks = {"all_natural_games_terminal", "all_reference_trajectories_terminal", "independent_reference_complete"}
    complete = run["status"] == "complete" and all(value for name, value in checks.items() if name not in terminal_checks)
    primary = complete and all(checks.values())
    natural_work = natural["work"]["ground_work"].get("sampled_transitions", 0)
    reference_work = validation["work"]["ground_work"].get("sampled_transitions", 0)
    return dict(schema="acfqp.direct_shared_value_analysis.v95", complete=complete, primary_complete=primary,
        checks=checks, natural=natural, validation=validation, simulation=simulation,
        inherited=inherited, inherited_data=run["inherited_data"],
        actual_executed_work=dict(new_tree_fits=0, new_training_environment_transitions=0,
            new_natural_transitions=natural_work, new_reference_transitions=reference_work,
            newly_sampled_environment_transitions=natural_work + reference_work,
            new_simulated_transitions=simulation["model_work"].get("synthetic_transitions", 0),
            simulated_trajectories=simulation["trajectories"], simulated_selector_calls=simulation["decisions"],
            simulated_model_work=simulation["model_work"], simulated_planning_counts=simulation["planning_counts"],
            simulated_value_counts=simulation["value_counts"], simulated_selection_seconds=simulation["seconds"],
            natural_evaluation_seconds=sum(cost["evaluation_seconds"] for stage in natural["checkpoints"].values()
                for method in stage["methods"].values() for cost in method["costs"]),
            reference_seconds=validation["work"]["seconds"], actual_wall_seconds=run["actual_wall_seconds"]),
        evidence_scope="All models and training acquisition are inherited. DIRECT uses extra model-based computation "
            "at deployment; a DIRECT-minus-head difference does not isolate removal of the head from that extra "
            "computation. Paired synthetic streams isolate differences among the frozen values. Original deployed "
            "predictions are evaluated against fresh full terminal references without recomputation. Lifecycle "
            "effects receive equal weights; descriptive two-SE bands are not calibrated 95% confidence intervals.")


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
