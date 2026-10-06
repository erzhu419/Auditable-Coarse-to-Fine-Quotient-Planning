"""Matched historical data, cross-fitted continuation labels, and fresh decisions."""
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
    pairs = [("DECOMPOSED", "MC")]
    pairs += [(method, "H2_ONLY") for method in methods if method != "H2_ONLY"]
    pairs += [(method, method + "_FROZEN_6") for method in ("MC", "DECOMPOSED")
        if method + "_FROZEN_6" in methods]
    return pairs


def _gate_pairs(methods):
    return [("DECOMPOSED", "MC")] + [(method, method + "_FROZEN_6")
        for method in ("MC", "DECOMPOSED") if method + "_FROZEN_6" in methods]


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
                    attribution = dict(new_or_changed_intervention_h2_score_contribution=math.fsum(
                        categories[name]["h2"]["mean_score_contribution"] for name in ("enabled", "changed_fragment")),
                        cancelled_intervention_recovery_score_contribution=categories["disabled"]["old"]["mean_score_contribution"])
                gate[query] = dict(primary_estimable=primary, primary_attribution=attribution,
                    available_common_terminal=data)
        output[str(checkpoint)] = dict(methods=summaries, comparisons=comparisons,
            gate_decomposition=gates, paired_terminal_cohorts=cohorts)
    return dict(checkpoints=output, checks=checks, work={name: dict(value) for name, value in work.items()})


def _average_records(rows, fields):
    return {name: _mean(row[name] for row in rows) for name in fields}


def analyze_validation(run):
    settings = run["settings"]
    checkpoint = max(settings["checkpoints"])
    lives, queries = settings["lifecycles"], settings["queries"]
    methods = [method for method in settings["methods_by_checkpoint"][str(checkpoint)] if method != "H2_ONLY"]
    replicas, per_query = settings["validation_replicas"], settings["validation_roots_per_query"]
    root_rows, head_rows, reconstruction_rows, missing = [], [], [], []
    work = {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")}
    prediction_work = Counter()
    trajectories, seconds = 0, 0.
    checks = dict(validation_roster_complete=True, all_validation_roots_terminal=True,
        validation_predictions_complete=True, validation_reconstruction_pairs_match=True)
    for life in run["lifecycles"]:
        stage = next(stage for stage in life["checkpoints"] if stage["episodes"] == checkpoint)
        data = stage["validation"]
        missing.extend(dict(row, life=life["id"]) for row in data["missing_roots"])
        seconds += data["seconds"]
        prediction_work.update(data.get("prediction_work", {}))
        for query in queries:
            selected = [row for row in data["roots"] if row["root"]["query"] == query]
            checks["validation_roster_complete"] &= (len(selected) == per_query
                and len({row["root"]["episode"] for row in selected}) == per_query)
        for record in data["roots"]:
            root, log = record["root"], record["log"]
            query = root["query"]
            for name in work:
                work[name].update(log[name])
            trajectories += log["trajectories"]
            samples = log["pair_deltas"]
            complete = (not log["censored_root"] and set(samples) == set(OPTIONS[1:])
                and all(len(samples[option]) == replicas for option in OPTIONS[1:]))
            checks["all_validation_roots_terminal"] &= complete
            checks["validation_predictions_complete"] &= set(record["predictions"]) == set(methods)
            root_rows.append(dict(root, life=life["id"], primary_estimable=complete,
                trajectories=log["trajectories"], outcomes=log["outcomes"], ground_work=log["ground_work"]))
            if not complete:
                continue
            reference = {option: _paired_summary(samples[option], query) for option in OPTIONS[1:]}
            for method in methods:
                prediction = record["predictions"][method]
                candidate_rows = []
                for option in OPTIONS[1:]:
                    predicted = prediction["predictions"][option]["target"]
                    target = reference[option]["mean_rfs"]
                    errors = [left - right for left, right in zip(predicted, target)]
                    utility_error = _utility(predicted, QUERIES[query]) - reference[option]["mean_utility"]
                    candidate_rows.append(dict(option=option, prediction=predicted, finite_terminal_reference=reference[option],
                        rfs_error=errors, utility_error=utility_error))
                chosen = prediction["option"]
                selected_value = 0. if chosen == "H2" else reference[chosen]["mean_utility"]
                head_rows.append(dict(life=life["id"], query=query, episode=root["episode"], method=method,
                    candidates=candidate_rows, selected_option=chosen, selected_empirical_utility=selected_value,
                    mean_utility_bias=_mean(row["utility_error"] for row in candidate_rows),
                    mean_utility_mse=_mean(row["utility_error"] ** 2 for row in candidate_rows),
                    mean_rfs_bias=[_mean(row["rfs_error"][i] for row in candidate_rows) for i in range(3)],
                    mean_rfs_mse=[_mean(row["rfs_error"][i] ** 2 for row in candidate_rows) for i in range(3)]))
            reconstruction = record["reconstruction"]
            checks["validation_reconstruction_pairs_match"] &= set(reconstruction) == set(OPTIONS[1:])
            for option in OPTIONS[1:]:
                vectors = reconstruction[option]["paired_targets"]
                residuals = reconstruction[option]["paired_residuals"]
                matched = len(vectors) == len(residuals) == replicas
                if matched:
                    matched = all(math.isclose(residual[i], predicted[i] - observed[i], abs_tol=1e-12, rel_tol=0)
                        for predicted, observed, residual in zip(vectors, samples[option], residuals) for i in range(3))
                checks["validation_reconstruction_pairs_match"] &= matched
                if not matched:
                    continue
                mc, decomposed, residual = reference[option], _paired_summary(vectors, query), _paired_summary(residuals, query)
                reconstruction_rows.append(dict(life=life["id"], query=query, episode=root["episode"], option=option,
                    mc=mc, decomposed=decomposed, paired_residual=residual,
                    conditional_variance_ratio=decomposed["utility_sample_variance"] / mc["utility_sample_variance"]
                        if mc["utility_sample_variance"] else None))
    checks["validation_roster_complete"] &= not missing
    heads = {}
    for method in methods:
        heads[method] = {}
        for query in queries:
            rows = [row for row in head_rows if row["method"] == method and row["query"] == query]
            lifecycle_rows = []
            for life in lives:
                selected = [row for row in rows if row["life"] == life]
                lifecycle_rows.append(dict(id=life, roots=len(selected),
                    **_average_records(selected, ("mean_utility_bias", "mean_utility_mse", "selected_empirical_utility")),
                    mean_rfs_bias=[_mean(row["mean_rfs_bias"][i] for row in selected) for i in range(3)],
                    mean_rfs_mse=[_mean(row["mean_rfs_mse"][i] for row in selected) for i in range(3)],
                    selected_options=dict(Counter(row["selected_option"] for row in selected))))
            primary = all(row["roots"] == per_query for row in lifecycle_rows)
            heads[method][query] = dict(primary_estimable=primary, available_root_descriptions=lifecycle_rows,
                primary=dict(**_average_records(lifecycle_rows, ("mean_utility_bias", "mean_utility_mse", "selected_empirical_utility")),
                    mean_rfs_bias=[_mean(row["mean_rfs_bias"][i] for row in lifecycle_rows) for i in range(3)],
                    mean_rfs_mse=[_mean(row["mean_rfs_mse"][i] for row in lifecycle_rows) for i in range(3)]) if primary else None)
    reconstruction_summary = {}
    for query in queries:
        rows = [row for row in reconstruction_rows if row["query"] == query]
        lifecycle_rows = []
        for life in lives:
            selected = [row for row in rows if row["life"] == life]
            lifecycle_rows.append(dict(id=life, root_options=len(selected),
                mean_mc_conditional_variance=_mean(row["mc"]["utility_sample_variance"] for row in selected),
                mean_decomposed_conditional_variance=_mean(row["decomposed"]["utility_sample_variance"] for row in selected),
                mean_paired_residual=_mean(row["paired_residual"]["mean_utility"] for row in selected),
                mean_squared_root_option_residual=_mean(row["paired_residual"]["mean_utility"] ** 2 for row in selected)))
        primary = all(row["root_options"] == per_query * 4 for row in lifecycle_rows)
        reconstruction_summary[query] = dict(primary_estimable=primary, available_root_descriptions=lifecycle_rows,
            primary=_average_records(lifecycle_rows, ("mean_mc_conditional_variance", "mean_decomposed_conditional_variance",
                "mean_paired_residual", "mean_squared_root_option_residual")) if primary else None)
    return dict(checks=checks, roots=root_rows, missing_roots=missing, heads=heads, head_root_errors=head_rows,
        reconstruction=reconstruction_summary, reconstruction_root_options=reconstruction_rows,
        work=dict(**{name: dict(value) for name, value in work.items()}, trajectories=trajectories,
            prediction_work=dict(prediction_work),
            planned_trajectories=len(lives) * len(queries) * per_query * replicas * len(OPTIONS), seconds=seconds),
        reference_scope="Finite independent terminal Monte Carlo references, not oracle values. Head prediction errors "
            "include reference sampling error. Reconstruction and MC use paired suffixes; their conditional variances "
            "and two-SE residual bands exclude continuation-model fitting uncertainty.")


def analyze_fitting(run):
    head_counts, tail_counts = {name: Counter() for name in ("MC", "DECOMPOSED")}, Counter()
    seconds = Counter(input_preparation=0., mc_head=0., decomposed_head=0., continuation=0., label_reconstruction=0.)
    rows, valid = [], True
    queries = run["settings"]["queries"]
    for life in run["lifecycles"]:
        for stage in life["checkpoints"]:
            data, updates, checkpoint = stage["dataset"], stage["updates"], stage["episodes"]
            mc, decomposed = updates["MC"], updates["DECOMPOSED"]
            valid &= (data["roots"] == data["training_roots"] + data["heldout_roots"]
                and data["records"] == 4 * data["roots"] and decomposed["oof_episode_isolation"] is True)
            for name, log in (("MC", mc), ("DECOMPOSED", decomposed["head_fit"])):
                head_counts[name].update(log["counts"])
                valid &= (log["counts"]["tree_fits"] == len(queries)
                    and log["counts"]["fit_roots"] == data["training_roots"]
                    and log["counts"]["fit_output_vectors"] == 4 * data["training_roots"])
            valid &= set(decomposed["tail_fits"]) == {"full", "fold_0", "fold_1"}
            for name, log in decomposed["tail_fits"].items():
                tail_counts.update(log["counts"])
                valid &= log["counts"]["continuation_tree_fits"] == len(queries)
                expected_fold = None if name == "full" else int(name[-1])
                valid &= log["excluded_fold"] == expected_fold and log["checkpoint"] == checkpoint
                for query in queries:
                    episodes = log["queries"][query]["training_episodes"]
                    valid &= all(episode < checkpoint and episode % 5 != 4
                        and (expected_fold is None or episode % 2 != expected_fold) for episode in episodes)
                seconds["continuation"] += log["seconds"]
            seconds["input_preparation"] += stage["input_preparation_seconds"]
            seconds["mc_head"] += mc["seconds"]
            seconds["decomposed_head"] += decomposed["head_fit"]["seconds"]
            seconds["label_reconstruction"] += decomposed["label_seconds"]
            rows.append(dict(life=life["id"], checkpoint=checkpoint, dataset=data, mc=mc, decomposed=decomposed))
    return dict(complete=bool(valid), stages=rows, head_counts={name: dict(value) for name, value in head_counts.items()},
        continuation_counts=dict(tail_counts), seconds=dict(seconds),
        actual_tree_fits=sum(value["tree_fits"] for value in head_counts.values()) + tail_counts["tree_fits"])


def analyze_run(run):
    natural, validation, fitting = analyze_natural(run), analyze_validation(run), analyze_fitting(run)
    inherited = {name: Counter() for name in ("source_work", "branch_work")}
    for life in run["lifecycles"]:
        for name in inherited:
            inherited[name].update(life["inherited"][name])
    terminal_keys = {"all_natural_games_terminal", "all_validation_roots_terminal"}
    checks = dict(**natural["checks"], **validation["checks"], fitting_accounting_complete=fitting["complete"])
    complete = run["status"] == "complete" and all(value for name, value in checks.items() if name not in terminal_keys)
    primary = complete and all(checks.values())
    natural_transitions = natural["work"]["ground_work"].get("sampled_transitions", 0)
    validation_transitions = validation["work"]["ground_work"].get("sampled_transitions", 0)
    return dict(schema="acfqp.shared_continuation_analysis.v91", complete=complete, primary_complete=primary,
        checks=checks, natural=natural, validation=validation, fitting=fitting,
        inherited=dict(lifecycles=[dict(id=life["id"], **life["inherited"]) for life in run["lifecycles"]],
            **{name: dict(value) for name, value in inherited.items()}),
        actual_executed_work=dict(new_training_transitions=0, new_source_games=0,
            new_evaluation_transitions=natural_transitions, new_validation_transitions=validation_transitions,
            newly_sampled_transitions=natural_transitions + validation_transitions,
            head_tree_fits=sum(value.get("tree_fits", 0) for value in fitting["head_counts"].values()),
            continuation_tree_fits=fitting["continuation_counts"].get("tree_fits", 0),
            actual_tree_fits=fitting["actual_tree_fits"], fitting_and_preparation_seconds=fitting["seconds"],
            validation_seconds=validation["work"]["seconds"], actual_wall_seconds=run["actual_wall_seconds"]),
        evidence_scope="Both learned methods reuse the same historical acquisition. Checkpoints are batch updates "
            "using whole-episode cross-fitting, not online per-episode updates. Natural effects average lifecycles "
            "equally; incomplete terminal cohorts retain costs and only supply explicitly descriptive subset results. "
            "Cancelled interventions measure recovery through H2 and are separate from new or changed intervention "
            "benefits. Full primary evidence requires every planned natural game and validation root terminal.")


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
