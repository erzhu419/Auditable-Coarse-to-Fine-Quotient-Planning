"""Warm-started Bellman fitting versus matched full-return state-value targets."""
from collections import Counter
import argparse
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.analyze_controlled_predictive_evidence_learning_v88 import (
    _mean, _summary, _cohort, _effect, _across_lives, _gate_decomposition,
)
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility

TERMINAL = ("WON", "LOST")
WIRING = ("pretrigger_prefixes_match", "committed_lengths_match", "single_initiations",
    "model_uniforms_aligned", "same_choice_histories_match")
VALUE_METHODS = ("MC_TAIL", "FQE")


def _gate_pairs(methods):
    pairs = [("FQE", name) for name in
        ("MC_TAIL", "MC", "MC_EXTRA", "H2_ONLY", "V91_DECOMPOSED", "V92_CORRECTED")]
    pairs += [("MC_TAIL", "V91_DECOMPOSED"), ("MC_TAIL", "H2_ONLY")]
    for method in VALUE_METHODS:
        frozen = method + "_FROZEN_6"
        if frozen in methods:
            pairs.append((method, frozen))
    return pairs


def _comparisons(methods):
    pairs = _gate_pairs(methods)
    pairs += [(method, "H2_ONLY") for method in methods
        if method != "H2_ONLY" and (method, "H2_ONLY") not in pairs]
    return pairs


def _lifecycle_uncertainty(rows):
    result = {}
    for metric in ("score", "utility"):
        values = [row[f"mean_{metric}_delta"] for row in rows]
        mean = _mean(values)
        se = statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else None
        result[metric] = dict(lifecycles=len(values), standard_error=se,
            two_se_lower=mean - 2 * se if se is not None else None,
            two_se_upper=mean + 2 * se if se is not None else None)
    return dict(**result, scope="Descriptive standard error across independent learning histories. "
        "The two-SE band is not a calibrated 95% confidence interval or an acceptance gate.")


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




def _vector_mean(rows):
    return [_mean(row[index] for row in rows) for index in range(3)]


def _paired_summary(vectors, query):
    utilities = [_utility(vector, QUERIES[query]) for vector in vectors]
    mean = _mean(utilities)
    variance = statistics.variance(utilities) if len(utilities) > 1 else None
    se = math.sqrt(variance / len(utilities)) if variance is not None else None
    return dict(replicas=len(vectors), mean_rfs=_vector_mean(vectors), mean_utility=mean,
        utility_sample_variance=variance, standard_error=se,
        two_se_lower=mean - 2 * se if se is not None else None,
        two_se_upper=mean + 2 * se if se is not None else None)


def predictive_error(predictions, targets, query):
    """Matched realized-return errors; no MC estimate is compared to itself."""
    errors = [[left - right for left, right in zip(prediction, target)]
        for prediction, target in zip(predictions, targets)]
    utilities = [_utility(error, QUERIES[query]) for error in errors]
    return dict(observations=len(errors), mean_utility_bias=_mean(utilities),
        mean_utility_mse=_mean(value * value for value in utilities),
        mean_rfs_bias=_vector_mean(errors),
        mean_rfs_mse=_vector_mean([[value * value for value in row] for row in errors]),
        predicted_terminal_mass=_mean(row[1] + row[2] for row in predictions),
        observed_terminal_mass=_mean(row[1] + row[2] for row in targets),
        paired_error=_paired_summary(errors, query))


def _history_summary(rows, settings, methods, fields):
    summary = {}
    for method in methods:
        summary[method] = {}
        for query in settings["queries"]:
            lives = []
            for life in settings["lifecycles"]:
                selected = [row for row in rows if row["life"] == life and row["query"] == query and row["method"] == method]
                lives.append(dict(id=life, roots=len(selected), **{name: _mean(row[name] for row in selected) for name in fields}))
            primary = all(row["roots"] == settings["validation_roots_per_query"] for row in lives)
            summary[method][query] = dict(primary_estimable=primary, descriptive_lifecycles=lives,
                primary={name: _mean(row[name] for row in lives) for name in fields} if primary else None)
    return summary

def analyze_validation(run):
    settings = run["settings"]
    checkpoint = max(settings["checkpoints"])
    methods = [name for name in settings["methods_by_checkpoint"][str(checkpoint)] if name != "H2_ONLY"]
    replicas = settings["reference_replicas"]
    roots, heads, values, reconstruction, option_errors, missing = [], [], [], [], [], []
    work = {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
    prediction_work, trajectories, seconds = Counter(), 0, 0.
    checks = dict(validation_roster_complete=True, validation_work_accounted=True,
        all_validation_games_terminal=True, independent_reference_complete=True,
        head_prediction_rosters_complete=True, boundary_prediction_rosters_complete=True,
        reconstruction_rosters_complete=True)
    for life in run["lifecycles"]:
        stage = next(stage for stage in life["checkpoints"] if stage["episodes"] == checkpoint)
        data = stage["validation"]
        missing.extend(dict(row, life=life["id"]) for row in data["missing_roots"])
        prediction_work.update(data["prediction_work"])
        seconds += data["seconds"]
        for query in settings["queries"]:
            selected = [row for row in data["roots"] if row["root"]["query"] == query]
            checks["validation_roster_complete"] &= (len(selected) == settings["validation_roots_per_query"]
                and len({row["root"]["episode"] for row in selected}) == len(selected))
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
            reference_complete = (terminal and record["reference_complete"]
                and set(reference) == set(OPTIONS[1:]) and all(len(vectors) == replicas for vectors in reference.values()))
            checks["validation_work_accounted"] &= accounting
            checks["all_validation_games_terminal"] &= terminal
            checks["independent_reference_complete"] &= reference_complete
            head_complete = set(record["head_predictions"]) == set(methods) and all(
                set(prediction["predictions"]) == set(OPTIONS) for prediction in record["head_predictions"].values())
            checks["head_prediction_rosters_complete"] &= head_complete
            boundary_records = record["value_records"]
            boundary_keys = {(row["option"], row["replica"]) for row in boundary_records}
            boundaries_valid = (len(boundary_keys) == len(boundary_records)
                and all(row["option"] in OPTIONS and 0 <= row["replica"] < replicas
                    and set(row["predictions"]) == set(VALUE_METHODS) for row in boundary_records)
                and (not terminal or len(boundary_records) == record["active_boundaries"]))
            checks["boundary_prediction_rosters_complete"] &= boundaries_valid
            reconstructed = record["reconstruction"]
            reconstruction_keys = {(row["option"], row["replica"]) for row in reconstructed}
            reconstruction_valid = (len(reconstruction_keys) == len(reconstructed)
                and all(row["option"] in OPTIONS[1:] and 0 <= row["replica"] < replicas
                    and set(row["Z"]) == set(VALUE_METHODS) for row in reconstructed))
            if reference_complete:
                reconstruction_valid &= (reconstruction_keys == {(option, replica) for option in OPTIONS[1:] for replica in range(replicas)}
                    and all(all(math.isclose(value, expected, abs_tol=1e-12, rel_tol=0)
                        for value, expected in zip(row["Y"], reference[row["option"]][row["replica"]])) for row in reconstructed))
            checks["reconstruction_rosters_complete"] &= reconstruction_valid
            summaries = {option: _paired_summary(vectors, query) for option, vectors in reference.items()}
            roots.append(dict(root=root, primary_estimable=reference_complete,
                active_boundaries=record["active_boundaries"], scored_boundary_records=len(boundary_records),
                paired_reference=summaries, terminal_outcomes=log["outcomes"]))
            if not reference_complete:
                continue
            identity = dict(life=life["id"], query=query, episode=root["episode"])
            if head_complete:
                for method, prediction in record["head_predictions"].items():
                    predicted = [prediction["predictions"][option]["target"] for option in OPTIONS[1:]]
                    targets = [summaries[option]["mean_rfs"] for option in OPTIONS[1:]]
                    error = predictive_error(predicted, targets, query)
                    selected = prediction["option"]
                    heads.append(dict(**identity, method=method, **error,
                        predicted_delta_terminal_mass=error["predicted_terminal_mass"],
                        implied_candidate_terminal_mass=1. + error["predicted_terminal_mass"],
                        reference_delta_terminal_mass=error["observed_terminal_mass"],
                        selected_option=selected,
                        selected_empirical_utility=0. if selected == "H2" else summaries[selected]["mean_utility"]))
            if boundaries_valid and boundary_records:
                complete_boundaries = [row for row in boundary_records if row["terminal"]]
                if len(complete_boundaries) == len(boundary_records):
                    for method in VALUE_METHODS:
                        values.append(dict(**identity, method=method,
                            **predictive_error([row["predictions"][method] for row in complete_boundaries],
                                [row["remaining_target"] for row in complete_boundaries], query)))
            if reconstruction_valid:
                for method in VALUE_METHODS:
                    reconstruction.append(dict(**identity, method=method,
                        **predictive_error([row["Z"][method] for row in reconstructed], [row["Y"] for row in reconstructed], query)))
                    for option in OPTIONS[1:]:
                        selected = sorted([row for row in reconstructed if row["option"] == option], key=lambda row: row["replica"])
                        option_errors.append(dict(**identity, method=method, option=option,
                            **predictive_error([row["Z"][method] for row in selected], [row["Y"] for row in selected], query)))
    checks["validation_roster_complete"] &= not missing
    error_fields = ("mean_utility_bias", "mean_utility_mse", "predicted_terminal_mass", "observed_terminal_mass")
    return dict(roots=roots, missing_roots=missing, checks=checks,
        heads=_history_summary(heads, settings, methods,
            ("mean_utility_bias", "mean_utility_mse", "selected_empirical_utility",
                "predicted_delta_terminal_mass", "implied_candidate_terminal_mass", "reference_delta_terminal_mass")),
        values=_history_summary(values, settings, VALUE_METHODS, error_fields),
        reconstruction=_history_summary(reconstruction, settings, VALUE_METHODS, error_fields),
        head_roots=heads, value_roots=values, reconstruction_roots=reconstruction, reconstruction_root_options=option_errors,
        work=dict(**{name: dict(counts) for name, counts in work.items()}, trajectories=trajectories,
            prediction_work=dict(prediction_work), seconds=seconds),
        scope="Head predictions precede a fresh independent terminal reference batch; its finite Monte Carlo "
            "uncertainty remains in head errors. State-value and reconstructed-return errors use matched observed "
            "prefixes and realized suffixes, so they measure predictive error, not an independent MC-estimator "
            "comparison. Active state boundaries are counted once per option/replica, including H2 once. "
            "Head terminal mass is a candidate-minus-H2 difference; 1 plus that difference is the implied candidate "
            "mass under a terminal H2 reference. Warm-started F+S conservation does not establish convergence. "
            "All primary summaries require the fixed root cohort; incomplete roots retain all acquisition cost.")

def analyze_construction(run):
    settings, stages, diagnostics, seconds = run["settings"], [], [], Counter()
    value_counts, head_counts, cache_counts = Counter(), Counter(), Counter()
    families = {name: Counter() for name in VALUE_METHODS}
    inherited = {name: Counter() for name in ("source", "branches")}
    historical_fits = 0
    checks = dict(retained_training_extraction_complete=True, no_new_training_acquisition=True,
        checkpoint_and_episode_fold_isolation=True, warm_start_and_fixed_rounds_match=True,
        fitting_accounting_complete=True, head_training_rosters_complete=True,
        inherited_method_costs_match=True)
    for life in run["lifecycles"]:
        totals, frozen_cost = Counter(), None
        cumulative_source, cumulative_branches = Counter(), Counter()
        for stage in sorted(life["checkpoints"], key=lambda row: row["episodes"]):
            cp, dataset, source = stage["episodes"], stage["dataset"], stage["input"]
            model, heads = stage["updates"]["value"], stage["updates"]["heads"]
            counts = source["counts"]
            totals.update(counts)
            for name in inherited:
                inherited[name].update(stage["inherited_acquisition"][name])
            cumulative_source.update(stage["inherited_acquisition"]["source"])
            cumulative_branches.update(stage["inherited_acquisition"]["branches"])
            checks["retained_training_extraction_complete"] &= (source["complete_root_execution_contract_matches"] is True
                and source["retained_means_match"] is True and source["n_step"] == settings["n_step"]
                and source["stride"] == settings["stride"] and source["row_weight"] == 1.
                and source["inherited_environment_work"] == stage["inherited_acquisition"]["branches"]
                and dataset["roots"] == totals["eligible_roots"]
                and dataset["training_roots"] == totals["training_eligible_roots"]
                and dataset["heldout_roots"] == totals["heldout_eligible_roots"]
                and dataset["records"] == 4 * dataset["roots"]
                and dataset["bellman_rows"] == totals["bellman_rows"])
            checks["no_new_training_acquisition"] &= (stage["new_training_environment_transitions"] == 0
                and counts["new_environment_transitions"] == counts["tree_fits"] == 0)
            checks["checkpoint_and_episode_fold_isolation"] &= (model["checkpoint"] == heads["checkpoint"] == cp
                and heads["oof_episode_isolation"] is True and heads["future_roots_excluded"] == 0
                and set(model["folds"]) == {"full", "fold_0", "fold_1"})
            expected_models = Counter()
            for name, fold in model["folds"].items():
                excluded = None if name == "full" else int(name[-1])
                checks["checkpoint_and_episode_fold_isolation"] &= fold["excluded_fold"] == excluded
                cache_counts.update(fold["cache_counts"])
                seconds["feature_cache"] += fold["cache_seconds"]
                for query in settings["queries"]:
                    episodes = fold["training_episodes"][query]
                    roster = fold["queries"][query]
                    checks["checkpoint_and_episode_fold_isolation"] &= (episodes == roster["training_episodes"]
                        and all(episode < cp and episode % 5 != 4
                            and (excluded is None or episode % 2 != excluded) for episode in episodes))
                    checks["fitting_accounting_complete"] &= roster["training_rows"] == roster["bootstrap_rows"] + roster["terminal_anchor_rows"]
                mc, fqe = fold["MC_TAIL"], fold["FQE"]
                iterations = fqe["iterations"]
                checks["warm_start_and_fixed_rounds_match"] &= (model["iterations"] == settings["fqe_iterations"]
                    and fqe["initialization"] == "MC_TAIL"
                    and [row["iteration"] for row in iterations] == list(range(1, settings["fqe_iterations"] + 1)))
                iteration_fits = sum(row["queries"][query]["counts"]["tree_fits"]
                    for row in iterations for query in settings["queries"])
                checks["fitting_accounting_complete"] &= (
                    mc["counts"]["tree_fits"] == mc["counts"]["mc_tail_tree_fits"] == len(settings["queries"])
                    and fqe["counts"]["tree_fits"] == fqe["counts"]["fqe_tree_fits"] == iteration_fits
                    == len(settings["queries"]) * settings["fqe_iterations"])
                for family in VALUE_METHODS:
                    families[family].update(fold[family]["counts"])
                    expected_models.update(fold[family]["counts"])
                    seconds[family + "_value_fitting"] += fold[family]["seconds"]
                for query in settings["queries"]:
                    diagnostics.append(dict(life=life["id"], checkpoint=cp, fold=name, query=query,
                        training=fold["queries"][query], initial_mc=mc["queries"][query],
                        first_fqe=iterations[0]["queries"][query], final_fqe=iterations[-1]["queries"][query]))
            value_counts.update(model["counts"])
            head_counts.update(heads["counts"])
            checks["fitting_accounting_complete"] &= model["counts"]["tree_fits"] == expected_models["tree_fits"]
            checks["head_training_rosters_complete"] &= (set(heads["head_fits"]) == set(VALUE_METHODS)
                and heads["input_roots"] == totals["roots"]
                and heads["censored_roots_excluded"] == totals["censored_roots"])
            head_fits, head_fit_seconds = 0, 0.
            for name, log in heads["head_fits"].items():
                head_fits += log["counts"]["tree_fits"]
                head_fit_seconds += log["seconds"]
                checks["head_training_rosters_complete"] &= (log["counts"]["fit_roots"] == dataset["training_roots"]
                    and log["counts"]["fit_output_vectors"] == 4 * dataset["training_roots"])
            checks["fitting_accounting_complete"] &= head_fits == heads["counts"]["tree_fits"] == 2 * len(settings["queries"])
            costs = stage["method_acquisition"]
            checks["inherited_method_costs_match"] &= (costs["MC_TAIL"] == costs["FQE"] == costs["MC"]
                and costs["MC"]["source_transitions"] == cumulative_source.get("sampled_transitions", 0)
                and costs["MC"]["base_branch_transitions"] == cumulative_branches.get("sampled_transitions", 0)
                and costs["MC"]["prefix_transitions"] == costs["MC"]["extra_terminal_transitions"] == 0)
            if cp == 6:
                frozen_cost = costs["MC"]
            else:
                checks["inherited_method_costs_match"] &= all(costs[name + "_FROZEN_6"] == frozen_cost for name in VALUE_METHODS)
            historical_fits += stage["inherited_v93_baselines"]["original_stage_tree_fits"]
            seconds["retained_data_extraction"] += source["seconds"]
            seconds["value_models_total"] += model["seconds"]
            seconds["heads_total"] += heads["seconds"]
            seconds["head_tree_fitting"] += head_fit_seconds
            seconds["head_label_and_other_preparation"] += heads["seconds"] - head_fit_seconds
            stages.append(dict(life=life["id"], checkpoint=cp, dataset=dataset,
                incremental_data_counts=counts, method_acquisition=costs,
                value_model_counts=model["counts"], head_counts=heads["counts"],
                inherited_v93_baselines=stage["inherited_v93_baselines"]))
    return dict(checks=checks, stages=stages, value_counts=dict(value_counts), head_counts=dict(head_counts),
        value_family_counts={name: dict(counts) for name, counts in families.items()},
        cache_counts=dict(cache_counts), seconds=dict(seconds), training_diagnostics=diagnostics,
        actual_tree_fits=value_counts["tree_fits"] + head_counts["tree_fits"],
        inherited_acquisition={name: dict(counts) for name, counts in inherited.items()},
        original_v93_stage_tree_fits=historical_fits,
        diagnostic_scope="MC_TAIL initializes each FQE fold once; copying that model incurs no extra fit. "
            "Fit-target MSE describes regression to that round's frozen target, not a fixed-point Bellman residual. "
            "The initial, first-round and last-round logs are training diagnostics, not convergence or success gates. "
            "Heads total includes label prediction and tree fitting; component seconds are not additional work.")


def analyze_run(run):
    natural, validation, construction = analyze_natural(run), analyze_validation(run), analyze_construction(run)
    checks = dict(**natural["checks"], **validation["checks"], **construction["checks"])
    terminal_checks = {"all_natural_games_terminal", "all_validation_games_terminal", "independent_reference_complete"}
    complete = run["status"] == "complete" and all(value for name, value in checks.items() if name not in terminal_checks)
    primary = complete and all(checks.values())
    natural_transitions = natural["work"]["ground_work"].get("sampled_transitions", 0)
    reference_transitions = validation["work"]["ground_work"].get("sampled_transitions", 0)
    return dict(schema="acfqp.shared_bellman_analysis.v94", complete=complete, primary_complete=primary,
        checks=checks, natural=natural, validation=validation, construction=construction,
        inherited_data=run["inherited_data"],
        actual_executed_work=dict(new_training_environment_transitions=0,
            new_natural_transitions=natural_transitions, new_reference_transitions=reference_transitions,
            newly_sampled_transitions=natural_transitions + reference_transitions,
            new_mc_tail_tree_fits=construction["value_family_counts"]["MC_TAIL"].get("tree_fits", 0),
            new_fqe_tree_fits=construction["value_family_counts"]["FQE"].get("tree_fits", 0),
            new_head_tree_fits=construction["head_counts"].get("tree_fits", 0),
            actual_tree_fits=construction["actual_tree_fits"],
            construction_seconds=construction["seconds"], validation_seconds=validation["work"]["seconds"],
            natural_evaluation_seconds=sum(cost["evaluation_seconds"] for stage in natural["checkpoints"].values()
                for method in stage["methods"].values() for cost in method["costs"]),
            actual_wall_seconds=run["actual_wall_seconds"]),
        evidence_scope="Frozen MC-initialized 128-round Bellman fitting versus matched-grid full-return targets; "
            "loaded baselines and historical data acquisition are inherited, not rerun. "
            "Natural effects receive equal learning-history weights. Fresh terminal suffixes evaluate previously "
            "fixed head predictions and matched-boundary predictive errors; no fresh independent estimator "
            "comparison or sample-saving claim is made. Full cutoffs retain costs and invalidate full primary evidence.")


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
