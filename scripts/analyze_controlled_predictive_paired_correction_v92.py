"""Paired continuation models and independent terminal residual correction."""
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


def _vector_mean(vectors):
    return [_mean(vector[index] for vector in vectors) for index in range(3)]


def _paired_summary(vectors, query):
    utilities = [_utility(vector, QUERIES[query]) for vector in vectors]
    mean = _mean(utilities)
    variance = statistics.variance(utilities) if len(utilities) > 1 else None
    se = math.sqrt(variance / len(utilities)) if variance is not None else None
    return dict(replicas=len(vectors), mean_rfs=_vector_mean(vectors), mean_utility=mean,
        utility_sample_variance=variance, standard_error=se,
        two_se_lower=mean - 2 * se if se is not None else None,
        two_se_upper=mean + 2 * se if se is not None else None)


def _comparisons(methods):
    pairs = [("CORRECTED", other) for other in ("MC", "PAIR_ONLY", "V91_DECOMPOSED")]
    pairs += [("PAIR_ONLY", "MC")]
    pairs += [(method, "H2_ONLY") for method in methods if method != "H2_ONLY"]
    if "CORRECTED_FROZEN_6" in methods:
        pairs.append(("CORRECTED", "CORRECTED_FROZEN_6"))
    return pairs


def _gate_pairs(methods):
    pairs = [("CORRECTED", "MC"), ("CORRECTED", "PAIR_ONLY"),
        ("CORRECTED", "V91_DECOMPOSED"), ("CORRECTED", "H2_ONLY"), ("PAIR_ONLY", "MC")]
    if "CORRECTED_FROZEN_6" in methods:
        pairs.append(("CORRECTED", "CORRECTED_FROZEN_6"))
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
        output[str(checkpoint)] = dict(methods=summaries, comparisons=comparisons,
            gate_decomposition=gates, paired_terminal_cohorts=cohorts)
    return dict(checkpoints=output, checks=checks, work={name: dict(value) for name, value in work.items()})


def _average_records(rows, fields):
    return {name: _mean(row[name] for row in rows) for name in fields}


def compare_estimators(full_vectors, full_predictions, short_predictions, reference_vectors, query):
    """Disjoint full/prefix batches; the terminal reference never enters an estimate."""
    if len(full_vectors) != len(full_predictions):
        raise ValueError("full predictions must match the terminal estimation batch")
    residual_vectors = [[observed - prediction for observed, prediction in zip(full, modeled)]
        for full, modeled in zip(full_vectors, full_predictions)]
    mc = _paired_summary(full_vectors, query)
    short = _paired_summary(short_predictions, query)
    residual = _paired_summary(residual_vectors, query)
    reference = _paired_summary(reference_vectors, query)
    mc_variance = mc["utility_sample_variance"] / mc["replicas"]
    prefix_variance = short["utility_sample_variance"] / short["replicas"]
    residual_variance = residual["utility_sample_variance"] / residual["replicas"]
    inputs = {
        "MC": (mc["mean_rfs"], mc_variance),
        "PAIR_ONLY": (short["mean_rfs"], prefix_variance),
        "CORRECTED": ([first + second for first, second in zip(short["mean_rfs"], residual["mean_rfs"])],
            prefix_variance + residual_variance),
    }
    estimates = {}
    for name, (vector, variance) in inputs.items():
        utility = _utility(vector, QUERIES[query])
        error = utility - reference["mean_utility"]
        se = math.sqrt(variance)
        estimates[name] = dict(mean_rfs=vector, mean_utility=utility, conditional_variance_of_mean=variance,
            conditional_standard_error=se, conditional_two_se_lower=utility - 2 * se,
            conditional_two_se_upper=utility + 2 * se, reference_utility_error=error,
            reference_squared_utility_error=error * error,
            reference_rfs_error=[left - right for left, right in zip(vector, reference["mean_rfs"])])
    return dict(estimates=estimates, full_terminal_estimation_batch=mc, independent_prefix_batch=short,
        full_terminal_residual=residual, independent_terminal_reference=reference,
        corrected_variance_components=dict(prefix_mean_variance=prefix_variance,
            terminal_residual_mean_variance=residual_variance),
        corrected_to_mc_conditional_variance_ratio=(prefix_variance + residual_variance) / mc_variance
            if mc_variance else None)


ESTIMATORS = ("MC", "PAIR_ONLY", "CORRECTED")
PREFIX_WIRING = ("environment_uniforms_aligned", "model_uniforms_aligned", "single_initiations", "committed_lengths_match")


def _prefix_complete(log, replicas):
    transitions = log["ground_work"]["sampled_transitions"]
    return (log["requested_replicas"] == replicas and log["trajectories"] == replicas * len(OPTIONS)
        and sum(log["outcomes"].values()) == log["trajectories"]
        and set(log["outcomes"]) <= {"ACTIVE", "WON", "LOST"}
        and 0 < transitions <= 4 * log["trajectories"]
        and log["planning_counts"]["model_uniform_draws"] == 4 * transitions
        and all(log["wiring"].get(name) is True for name in PREFIX_WIRING))


def _selected_option(values, query):
    chosen, best = "H2", 0.
    for option in OPTIONS[1:]:
        value = _utility(values[option], QUERIES[query])
        if value > best:
            chosen, best = option, value
    return chosen


def _error_record(predictions, reference, chosen, query):
    errors = [[predicted - observed for predicted, observed in zip(predictions[option], reference[option]["mean_rfs"])]
        for option in OPTIONS[1:]]
    utility_errors = [_utility(error, QUERIES[query]) for error in errors]
    return dict(mean_utility_bias=_mean(utility_errors), mean_utility_mse=_mean(value * value for value in utility_errors),
        mean_rfs_bias=_vector_mean(errors), mean_rfs_mse=_vector_mean([[value * value for value in row] for row in errors]),
        selected_option=chosen, selected_empirical_utility=0. if chosen == "H2" else reference[chosen]["mean_utility"])


def _summarize_errors(rows, methods, settings, extra_fields=()):
    fields = ("mean_utility_bias", "mean_utility_mse", "selected_empirical_utility", *extra_fields)
    result = {}
    for method in methods:
        result[method] = {}
        for query in settings["queries"]:
            lives = []
            for life in settings["lifecycles"]:
                selected = [row for row in rows if row["life"] == life and row["query"] == query and row["method"] == method]
                lives.append(dict(id=life, roots=len(selected), **_average_records(selected, fields),
                    mean_rfs_bias=[_mean(row["mean_rfs_bias"][i] for row in selected) for i in range(3)],
                    mean_rfs_mse=[_mean(row["mean_rfs_mse"][i] for row in selected) for i in range(3)],
                    selected_options=dict(Counter(row["selected_option"] for row in selected))))
            complete = all(row["roots"] == settings["validation_roots_per_query"] for row in lives)
            result[method][query] = dict(primary_estimable=complete, available_root_descriptions=lives,
                primary=dict(**_average_records(lives, fields),
                    mean_rfs_bias=[_mean(row["mean_rfs_bias"][i] for row in lives) for i in range(3)],
                    mean_rfs_mse=[_mean(row["mean_rfs_mse"][i] for row in lives) for i in range(3)]) if complete else None)
    return result


def analyze_validation(run):
    settings = run["settings"]
    checkpoint = max(settings["checkpoints"])
    n, m, r = (settings[name] for name in ("validation_estimation_replicas", "validation_prefix_replicas", "validation_reference_replicas"))
    methods = [name for name in settings["methods_by_checkpoint"][str(checkpoint)] if name != "H2_ONLY"]
    root_rows, option_rows, estimator_rows, head_rows, missing = [], [], [], [], []
    checks = dict(validation_roster_complete=True, validation_prefixes_complete=True,
        all_validation_terminal_trajectories_complete=True, independent_reference_rosters_complete=True,
        estimator_sample_accounting_complete=True, stored_estimator_values_match=True, head_prediction_rosters_complete=True)
    work = {kind: {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
        for kind in ("prefix", "terminal")}
    trajectories, prediction_work, seconds = Counter(), Counter(), 0.
    for life in run["lifecycles"]:
        stage = next(stage for stage in life["checkpoints"] if stage["episodes"] == checkpoint)
        data = stage["validation"]
        missing.extend(dict(row, life=life["id"]) for row in data["missing_roots"])
        seconds += data["seconds"]
        prediction_work.update(data.get("prediction_work", {}))
        for query in settings["queries"]:
            records = [row for row in data["roots"] if row["root"]["query"] == query]
            checks["validation_roster_complete"] &= (len(records) == settings["validation_roots_per_query"]
                and len({row["root"]["episode"] for row in records}) == len(records))
        for record in data["roots"]:
            root, estimator = record["root"], record["estimates"]
            query = root["query"]
            for kind in work:
                log = record[kind + "_log"]
                trajectories[kind] += log["trajectories"]
                for name in work[kind]:
                    work[kind][name].update(log[name])
            prefix_complete = _prefix_complete(record["prefix_log"], m)
            terminal = record["terminal_log"]
            terminal_roster = (terminal["trajectories"] == (n + r) * len(OPTIONS)
                and sum(terminal["outcomes"].values()) == terminal["trajectories"])
            checks["estimator_sample_accounting_complete"] &= terminal_roster
            all_terminal = not terminal["censored_root"] and set(terminal["outcomes"]) <= set(TERMINAL)
            checks["all_validation_terminal_trajectories_complete"] &= all_terminal
            reference_complete = (record["reference_complete"] and set(record["reference"]) == set(OPTIONS[1:])
                and all(len(vectors) == r for vectors in record["reference"].values()))
            checks["validation_prefixes_complete"] &= prefix_complete
            checks["independent_reference_rosters_complete"] &= reference_complete
            checks["head_prediction_rosters_complete"] &= set(record["head_predictions"]) == set(methods)
            primary = prefix_complete and terminal_roster and all_terminal and reference_complete and estimator["complete"]
            root_rows.append(dict(root, life=life["id"], primary_estimable=primary,
                estimation_complete=estimator["complete"], reference_complete=reference_complete,
                terminal_trajectories=terminal["trajectories"], terminal_outcomes=terminal["outcomes"]))
            if not primary:
                continue
            references, local = {}, []
            accounting = set(estimator["details"]) == set(OPTIONS[1:]) and set(estimator["estimates"]) == set(ESTIMATORS)
            for option in OPTIONS[1:]:
                detail = estimator["details"][option]
                sizes_match = (len(detail["full_targets"]) == len(detail["full_predictions"]) == len(detail["paired_residuals"]) == n
                    and len(detail["short_predictions"]) == m
                    and detail["full_replicas"] == list(range(n)) and detail["short_replicas"] == list(range(m)))
                accounting &= sizes_match
                if not sizes_match:
                    continue
                comparison = compare_estimators(detail["full_targets"], detail["full_predictions"],
                    detail["short_predictions"], record["reference"][option], query)
                accounting &= all(math.isclose(residual[i], observed[i] - predicted[i], abs_tol=1e-12, rel_tol=0)
                    for observed, predicted, residual in zip(detail["full_targets"], detail["full_predictions"], detail["paired_residuals"])
                    for i in range(3))
                matching = all(math.isclose(a, b, rel_tol=0, abs_tol=1e-12)
                    for method in ESTIMATORS for a, b in zip(estimator["estimates"][method][option], comparison["estimates"][method]["mean_rfs"]))
                matching &= math.isclose(detail["mc_variance_of_mean"], comparison["estimates"]["MC"]["conditional_variance_of_mean"], abs_tol=1e-12, rel_tol=0)
                matching &= math.isclose(detail["corrected_variance_of_mean"], comparison["estimates"]["CORRECTED"]["conditional_variance_of_mean"], abs_tol=1e-12, rel_tol=0)
                checks["stored_estimator_values_match"] &= matching
                references[option] = comparison["independent_terminal_reference"]
                local.append(dict(life=life["id"], query=query, episode=root["episode"], option=option, **comparison))
            checks["estimator_sample_accounting_complete"] &= accounting
            if not accounting:
                continue
            option_rows.extend(local)
            for method in ESTIMATORS:
                values = estimator["estimates"][method]
                chosen = _selected_option(values, query)
                estimator_rows.append(dict(life=life["id"], query=query, episode=root["episode"], method=method,
                    **_error_record(values, references, chosen, query),
                    mean_conditional_variance_of_mean=_mean(row["estimates"][method]["conditional_variance_of_mean"] for row in local),
                    mean_full_terminal_residual_variance=_mean(row["full_terminal_residual"]["utility_sample_variance"] for row in local)))
            for method in methods:
                prediction = record["head_predictions"][method]
                values = {option: prediction["predictions"][option]["target"] for option in OPTIONS[1:]}
                head_rows.append(dict(life=life["id"], query=query, episode=root["episode"], method=method,
                    **_error_record(values, references, prediction["option"], query)))
    checks["validation_roster_complete"] &= not missing
    return dict(checks=checks, roots=root_rows, missing_roots=missing, root_option_estimates=option_rows,
        root_estimator_errors=estimator_rows, head_root_errors=head_rows,
        estimators=_summarize_errors(estimator_rows, ESTIMATORS, settings,
            ("mean_conditional_variance_of_mean", "mean_full_terminal_residual_variance")),
        heads=_summarize_errors(head_rows, methods, settings),
        work=dict(**{kind: {name: dict(value) for name, value in groups.items()} for kind, groups in work.items()},
            trajectories=dict(trajectories), prediction_work=dict(prediction_work), seconds=seconds),
        reference_scope="The last fixed terminal replicas are independent finite Monte Carlo references, never the "
            "first terminal estimation batch. MC, pair prediction and correction share acquisition. Correction "
            "variance includes independent prefix and terminal-residual mean terms, conditional on frozen g; it "
            "omits fitting uncertainty. This comparison does not establish sample savings or unbiasedness. Four-step "
            "ACTIVE prefix boundaries are complete intended observations, not missing terminal outcomes.")


def analyze_construction(run):
    settings = run["settings"]
    head_counts = {name: Counter() for name in ESTIMATORS}
    pair_counts, acquisition = Counter(), {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
    seconds = Counter(input_preparation=0., paired_models=0., label_reconstruction=0., head_fitting=0., prefix_acquisition=0.)
    rows, trajectories, roots = [], 0, 0
    checks = dict(fitting_accounting_complete=True, training_prefix_rosters_complete=True, all_training_estimates_complete=True)
    for life in run["lifecycles"]:
        for stage in life["checkpoints"]:
            dataset, updates, checkpoint = stage["dataset"], stage["updates"], stage["episodes"]
            pair_log, selector_log = updates["paired_models"], updates["selectors"]
            valid = (dataset["roots"] == dataset["training_roots"] + dataset["heldout_roots"]
                and dataset["records"] == 4 * dataset["roots"] and selector_log["oof_episode_isolation"] is True)
            valid &= set(pair_log["fits"]) == {"full", "fold_0", "fold_1"}
            for name, log in pair_log["fits"].items():
                pair_counts.update(log["counts"])
                excluded = None if name == "full" else int(name[-1])
                valid &= (log["checkpoint"] == checkpoint and log["excluded_fold"] == excluded
                    and log["counts"]["paired_continuation_tree_fits"] == len(settings["queries"]))
                for query in settings["queries"]:
                    valid &= all(episode < checkpoint and episode % 5 != 4
                        and (excluded is None or episode % 2 != excluded)
                        for episode in log["queries"][query]["training_episodes"])
            valid &= set(selector_log["head_fits"]) == set(ESTIMATORS)
            for method, log in selector_log["head_fits"].items():
                head_counts[method].update(log["counts"])
                valid &= (log["counts"]["tree_fits"] == len(settings["queries"])
                    and log["counts"]["fit_roots"] == dataset["training_roots"]
                    and log["counts"]["fit_output_vectors"] == 4 * dataset["training_roots"])
                seconds["head_fitting"] += log["seconds"]
            checks["all_training_estimates_complete"] &= (len(selector_log["root_estimates"]) == dataset["roots"]
                and all(row["complete"] for row in selector_log["root_estimates"]))
            checks["fitting_accounting_complete"] &= valid
            source = stage["acquisition"]
            for name in acquisition:
                acquisition[name].update(source[name])
            trajectories += source["trajectories"]
            roots += len(source["roots"])
            checks["training_prefix_rosters_complete"] &= all(_prefix_complete(row["log"], settings["prefix_replicas"]) for row in source["roots"])
            checks["training_prefix_rosters_complete"] &= (source["trajectories"] == len(source["roots"]) * len(OPTIONS) * settings["prefix_replicas"])
            seconds["input_preparation"] += stage["input_preparation_seconds"]
            seconds["paired_models"] += pair_log["seconds"]
            seconds["label_reconstruction"] += selector_log["label_seconds"]
            seconds["prefix_acquisition"] += source["seconds"]
            rows.append(dict(life=life["id"], checkpoint=checkpoint, dataset=dataset,
                paired_fit_counts=pair_log["counts"], selector_fit_counts=selector_log["counts"],
                acquired_prefix_roots=len(source["roots"]), acquired_prefix_transitions=source["ground_work"]["sampled_transitions"]))
    return dict(checks=checks, stages=rows, head_counts={name: dict(value) for name, value in head_counts.items()},
        paired_counts=dict(pair_counts), seconds=dict(seconds),
        acquisition=dict(**{name: dict(value) for name, value in acquisition.items()}, roots=roots, trajectories=trajectories),
        actual_tree_fits=pair_counts["tree_fits"] + sum(value["tree_fits"] for value in head_counts.values()))


def analyze_run(run):
    natural, validation, construction = analyze_natural(run), analyze_validation(run), analyze_construction(run)
    checks = dict(**natural["checks"], **validation["checks"], **construction["checks"])
    terminal_checks = {"all_natural_games_terminal", "all_validation_terminal_trajectories_complete", "independent_reference_rosters_complete"}
    complete = run["status"] == "complete" and all(value for name, value in checks.items() if name not in terminal_checks)
    primary = complete and all(checks.values()) and all(row["primary_estimable"] for row in validation["roots"])
    inherited = {name: Counter() for name in ("source_work", "branch_work")}
    for life in run["lifecycles"]:
        for name in inherited:
            inherited[name].update(life["inherited"][name])
    training = construction["acquisition"]["ground_work"].get("sampled_transitions", 0)
    natural_transitions = natural["work"]["ground_work"].get("sampled_transitions", 0)
    validation_prefix = validation["work"]["prefix"]["ground_work"].get("sampled_transitions", 0)
    validation_terminal = validation["work"]["terminal"]["ground_work"].get("sampled_transitions", 0)
    return dict(schema="acfqp.paired_correction_analysis.v92", complete=complete, primary_complete=primary,
        checks=checks, natural=natural, validation=validation, construction=construction,
        inherited=dict(lifecycles=[dict(id=life["id"], **life["inherited"]) for life in run["lifecycles"]],
            **{name: dict(value) for name, value in inherited.items()}),
        actual_executed_work=dict(new_training_prefix_transitions=training, new_training_terminal_transitions=0,
            new_natural_transitions=natural_transitions, new_validation_prefix_transitions=validation_prefix,
            new_validation_terminal_transitions=validation_terminal,
            newly_sampled_transitions=training + natural_transitions + validation_prefix + validation_terminal,
            new_pair_tree_fits=construction["paired_counts"].get("tree_fits", 0),
            new_head_tree_fits=sum(counts.get("tree_fits", 0) for counts in construction["head_counts"].values()),
            new_v91_baseline_fits=0, actual_tree_fits=construction["actual_tree_fits"],
            construction_seconds=construction["seconds"], validation_seconds=validation["work"]["seconds"],
            actual_wall_seconds=run["actual_wall_seconds"]),
        evidence_scope="Fixed full and short sample counts; all methods are charged the same shared acquisition. "
            "No comparison to a differently allocated optimal MC budget or sample-saving claim is made. Natural "
            "effects average lifecycles equally. Cancelled interventions are separate from newly executed or changed "
            "fragments. Terminal cutoffs and incomplete references retain all work and invalidate full primary evidence.")


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
