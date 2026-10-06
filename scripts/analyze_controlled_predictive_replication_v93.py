"""Independent learning histories with equally charged extra environment work."""
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


def _gate_pairs(methods):
    pairs = [("CORRECTED", name) for name in ("MC", "MC_EXTRA", "V91_DECOMPOSED", "PAIR_ONLY", "H2_ONLY")]
    pairs += [("MC_EXTRA", "MC"), ("MC_EXTRA", "H2_ONLY"), ("PAIR_ONLY", "MC")]
    for method in ("CORRECTED", "MC_EXTRA"):
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



def analyze_training_variance(run):
    """OOF training diagnostics; there is no independent terminal reference in V93."""
    fields = ("mc_sample_variance", "short_sample_variance", "residual_sample_variance",
        "mc_variance_of_mean", "corrected_variance_of_mean")
    output = {}
    for checkpoint in run["settings"]["checkpoints"]:
        queries = {}
        for query in run["settings"]["queries"]:
            lives = []
            for life in run["lifecycles"]:
                stage = next(row for row in life["checkpoints"] if row["episodes"] == checkpoint)
                roots = [row for row in stage["updates"]["paired_selectors"]["root_estimates"]
                    if row["query"] == query and row["episode"] % 5 != 4]
                complete = [row for row in roots if row["complete"]]
                values = [root["details"][option] for root in complete for option in OPTIONS[1:]]
                means = {name: _mean(row[name] for row in values) for name in fields}
                lives.append(dict(id=life["id"], training_roots=len(roots), complete_roots=len(complete),
                    root_options=len(values), **means))
            means = {name: _mean(row[name] for row in lives) if all(row[name] is not None for row in lives)
                else None for name in fields}
            denominator = means["mc_variance_of_mean"]
            queries[query] = dict(lifecycles=lives, equal_lifecycle_means=means,
                ratio_of_equal_lifecycle_mean_variances=means["corrected_variance_of_mean"] / denominator
                    if denominator else None)
        output[str(checkpoint)] = queries
    return dict(checkpoints=output, scope="Descriptive training-root OOF diagnostics, with equal lifecycle "
        "weights and equal root/option weights within lifecycle. These are not independent validation errors. "
        "Conditional variances omit fitted-model uncertainty. No fresh reference cohort was sampled in V93.")

def _root_key(root):
    return root["episode"], root["query"], tuple(root["board"])


def _extra_checks(log, prefix_transitions, life, previous_checkpoint):
    blocks, roster = log["blocks"], log["roster"]
    used = log["ground_work"].get("sampled_transitions", 0)
    incorporated = log["incorporated_ground_work"].get("sampled_transitions", 0)
    unincorporated = log["unincorporated_ground_work"].get("sampled_transitions", 0)
    keys = [_root_key(root) for root in roster]
    rotation = (life + log["checkpoint"]) % len(keys) if keys else 0
    ordered = sorted(keys)
    expected = ordered[rotation:] + ordered[:rotation]
    allocation = (keys == expected and len(set(keys)) == len(keys) and log["roster_rotation"] == rotation
        and all(previous_checkpoint <= root["episode"] < log["checkpoint"] and root["episode"] % 5 != 4
            for root in roster)
        and all(block["attempt"] == index and _root_key(block["root"]) == keys[index % len(keys)]
            for index, block in enumerate(blocks)))
    complete_blocks = [block for block in blocks if block["complete_block"]]
    partial_blocks = [block for block in blocks if not block["complete_block"]]
    work = (used == incorporated + unincorporated
        and used == sum(block["ground_work"].get("sampled_transitions", 0) for block in blocks)
        and incorporated == sum(block["ground_work"].get("sampled_transitions", 0) for block in complete_blocks)
        and unincorporated == sum(block["ground_work"].get("sampled_transitions", 0) for block in partial_blocks)
        and log["attempted_blocks"] == len(blocks)
        and log["complete_blocks"] == len(complete_blocks)
        and log["incomplete_blocks"] == len(partial_blocks)
        and log["trajectories"] == sum(block["trajectories"] for block in blocks)
        and log["trajectories"] == sum(log["outcomes"].values())
        and log["planning_counts"].get("model_uniform_draws", 0) == 4 * used)
    return dict(extra_environment_budget_matched=log["budget"] == log["used_transitions"] == used == prefix_transitions
            and log["unused_budget"] == 0,
        extra_work_including_partial_blocks_accounted=work,
        extra_new_batch_round_robin_valid=allocation)


PREFIX_WIRING = ("environment_uniforms_aligned", "model_uniforms_aligned", "single_initiations", "committed_lengths_match")
HEAD_METHODS = ("MC", "PAIR_ONLY", "CORRECTED", "V91_DECOMPOSED", "MC_EXTRA")
WORK_KINDS = ("source", "base_branch", "prefix", "extra_terminal")


def _prefix_complete(log, replicas):
    transitions = log["ground_work"].get("sampled_transitions", 0)
    return (log["requested_replicas"] == replicas and log["trajectories"] == replicas * len(OPTIONS)
        and sum(log["outcomes"].values()) == log["trajectories"]
        and set(log["outcomes"]) <= {"ACTIVE", "WON", "LOST"}
        and 0 < transitions <= 4 * log["trajectories"]
        and log["planning_counts"].get("model_uniform_draws", 0) == 4 * transitions
        and all(log["wiring"].get(name) is True for name in PREFIX_WIRING))


def _fit_roster_valid(fits, checkpoint, queries, tree_kind):
    valid = set(fits) == {"full", "fold_0", "fold_1"}
    for name, log in fits.items():
        excluded = None if name == "full" else int(name[-1])
        valid &= (log["checkpoint"] == checkpoint and log["excluded_fold"] == excluded
            and log["counts"]["tree_fits"] == log["counts"][tree_kind] == len(queries))
        for query in queries:
            valid &= all(episode < checkpoint and episode % 5 != 4
                and (excluded is None or episode % 2 != excluded)
                for episode in log["queries"][query]["training_episodes"])
    return valid


def analyze_construction(run):
    settings, rows, seconds = run["settings"], [], Counter()
    head_counts = {name: Counter() for name in HEAD_METHODS}
    model_counts = {name: Counter() for name in ("paired", "v91_continuation")}
    work = {kind: {name: Counter() for name in ("ground_work", "planning_counts", "outcomes")} for kind in WORK_KINDS}
    trajectories, extra_totals = Counter(), Counter()
    checks = dict(fresh_source_rosters_complete=True, base_branch_work_accounted=True,
        shared_training_roots_match=True, fitting_accounting_complete=True,
        training_prefix_rosters_complete=True, all_training_estimates_complete=True,
        extra_environment_budget_matched=True, extra_work_including_partial_blocks_accounted=True,
        extra_new_batch_round_robin_valid=True, extra_labels_use_complete_blocks=True,
        method_training_charges_match=True)
    for life in run["lifecycles"]:
        previous, cumulative, complete_extra = 0, Counter(), 0
        frozen_costs = None
        for stage in sorted(life["checkpoints"], key=lambda row: row["episodes"]):
            checkpoint, dataset, updates = stage["episodes"], stage["dataset"], stage["updates"]
            source, branch = stage["source"], stage["branches"]
            prefix, extra = stage["acquisition_prefix"], stage["acquisition_extra"]
            checks["fresh_source_rosters_complete"] &= (source["games"] == (checkpoint - previous) * len(settings["queries"])
                and source["games"] == sum(source["outcomes"].values())
                and stage["source_sampling_lifecycle"] == 9300 + life["id"])
            checks["base_branch_work_accounted"] &= (branch["roots"] == source["roots"]
                and branch["trajectories"] == branch["roots"] * settings["branch_replicas"] * len(OPTIONS)
                and branch["trajectories"] == sum(branch["outcomes"].values())
                and branch["planning_counts"].get("model_uniform_draws", 0) == 4 * branch["work"].get("sampled_transitions", 0))
            for kind, log, count_key in (("source", source, "work"), ("base_branch", branch, "work"),
                    ("prefix", prefix, "ground_work"), ("extra_terminal", extra, "ground_work")):
                work[kind]["ground_work"].update(log[count_key])
                for name in ("planning_counts", "outcomes"):
                    work[kind][name].update(log[name])
                cumulative[kind + "_transitions"] += log[count_key].get("sampled_transitions", 0)
                trajectories[kind] += log["games" if kind == "source" else "trajectories"]
                seconds[kind + "_acquisition"] += log["seconds"]
            for name, value in _extra_checks(extra, prefix["ground_work"].get("sampled_transitions", 0), life["id"], previous).items():
                checks[name] &= value
            for name in ("attempted_blocks", "complete_blocks", "incomplete_blocks", "budget_truncated_blocks",
                    "budget_cutoff_trajectories", "max_step_cutoff_trajectories"):
                extra_totals[name] += extra[name]
            for name in ("incorporated", "unincorporated"):
                extra_totals[name + "_transitions"] += extra[name + "_ground_work"].get("sampled_transitions", 0)
            complete_extra += extra["complete_blocks"]
            merge = stage["extra_merge"]
            checks["extra_labels_use_complete_blocks"] &= (merge["complete_extra_blocks"] == complete_extra
                and sum(root["extra_replicas"] for root in merge["root_statistics"]) == complete_extra
                and all(root["base_replicas"] == settings["branch_replicas"]
                    and root["total_replicas"] == root["base_replicas"] + root["extra_replicas"]
                    and (root["root"]["episode"] % 5 != 4 or root["extra_replicas"] == 0)
                    for root in merge["root_statistics"]))
            checks["training_prefix_rosters_complete"] &= (len(prefix["roots"]) == branch["roots"] - branch["censored_roots"]
                and all(_prefix_complete(root["log"], settings["prefix_replicas"]) for root in prefix["roots"])
                and prefix["trajectories"] == len(prefix["roots"]) * settings["prefix_replicas"] * len(OPTIONS))
            checks["shared_training_roots_match"] &= stage["input"]["agreement"]["root_cohorts_identical"] is True
            pair, selectors, unary = updates["paired_models"], updates["paired_selectors"], updates["v91_decomposed"]
            valid = (_fit_roster_valid(pair["fits"], checkpoint, settings["queries"], "paired_continuation_tree_fits")
                and _fit_roster_valid(unary["tail_fits"], checkpoint, settings["queries"], "continuation_tree_fits")
                and dataset["roots"] == dataset["training_roots"] + dataset["heldout_roots"]
                and dataset["records"] == 4 * dataset["roots"]
                and selectors["oof_episode_isolation"] is True and unary["oof_episode_isolation"] is True)
            for name, fits in (("paired", pair["fits"]), ("v91_continuation", unary["tail_fits"])):
                for log in fits.values():
                    model_counts[name].update(log["counts"])
                    seconds[name + "_fitting"] += log["seconds"]
            heads = dict(selectors["head_fits"], V91_DECOMPOSED=unary["head_fit"], MC_EXTRA=updates["mc_extra"])
            valid &= set(heads) == set(HEAD_METHODS)
            for name, log in heads.items():
                head_counts[name].update(log["counts"])
                valid &= (log["counts"]["tree_fits"] == len(settings["queries"])
                    and log["counts"]["fit_roots"] == dataset["training_roots"]
                    and log["counts"]["fit_output_vectors"] == 4 * dataset["training_roots"])
                seconds[name + "_head_fitting"] += log["seconds"]
            valid &= updates["counts"]["tree_fits"] + updates["mc_extra"]["counts"]["tree_fits"] == 11 * len(settings["queries"])
            checks["fitting_accounting_complete"] &= valid
            estimates = selectors["root_estimates"]
            checks["all_training_estimates_complete"] &= (len(estimates) == dataset["roots"]
                and all(root["complete"] and root["episode"] < checkpoint
                    and root["continuation_model"] == ("full" if root["episode"] % 5 == 4 else f"fold_{root['episode'] % 2}")
                    for root in estimates))
            seconds["input_preparation"] += stage["input_preparation_seconds"]
            seconds["paired_label_reconstruction"] += selectors["label_seconds"]
            seconds["v91_label_reconstruction"] += unary["label_seconds"]
            actual_charges = stage["method_acquisition"]
            expected_charges = {}
            for method in settings["methods_by_checkpoint"][str(checkpoint)]:
                if method.endswith("_FROZEN_6"):
                    expected_charges[method] = frozen_costs[method.removesuffix("_FROZEN_6")]
                    continue
                charges = {name + "_transitions": 0 for name in WORK_KINDS}
                if method != "H2_ONLY":
                    charges.update(source_transitions=cumulative["source_transitions"],
                        base_branch_transitions=cumulative["base_branch_transitions"])
                if method in ("PAIR_ONLY", "CORRECTED"):
                    charges["prefix_transitions"] = cumulative["prefix_transitions"]
                if method == "MC_EXTRA":
                    charges["extra_terminal_transitions"] = cumulative["extra_terminal_transitions"]
                charges["total_training_transitions"] = sum(charges.values())
                expected_charges[method] = charges
            if checkpoint == 6:
                frozen_costs = expected_charges
            checks["method_training_charges_match"] &= actual_charges == expected_charges
            rows.append(dict(life=life["id"], checkpoint=checkpoint, dataset=dataset,
                method_acquisition=actual_charges, extra_budget=extra["budget"],
                extra_root_statistics=extra["root_statistics"], cumulative_extra_root_statistics=merge["root_statistics"],
                complete_extra_blocks=extra["complete_blocks"], incomplete_extra_blocks=extra["incomplete_blocks"],
                source_outcomes=source["outcomes"], base_branch_outcomes=branch["outcomes"],
                base_censored_roots=branch["censored_roots"]))
            previous = checkpoint
    return dict(checks=checks, stages=rows, work={kind: {name: dict(value) for name, value in groups.items()}
            for kind, groups in work.items()}, trajectories=dict(trajectories), extra_allocation_totals=dict(extra_totals),
        head_counts={name: dict(counts) for name, counts in head_counts.items()},
        model_counts={name: dict(counts) for name, counts in model_counts.items()}, seconds=dict(seconds),
        actual_tree_fits=sum(counts["tree_fits"] for counts in head_counts.values())
            + sum(counts["tree_fits"] for counts in model_counts.values()))


def analyze_run(run):
    natural, construction = analyze_natural(run), analyze_construction(run)
    checks = dict(**natural["checks"], **construction["checks"])
    complete = run["status"] == "complete" and all(value for name, value in checks.items() if name != "all_natural_games_terminal")
    primary = complete and checks["all_natural_games_terminal"]
    transitions = {kind + "_transitions": groups["ground_work"].get("sampled_transitions", 0)
        for kind, groups in construction["work"].items()}
    natural_transitions = natural["work"]["ground_work"].get("sampled_transitions", 0)
    return dict(schema="acfqp.independent_history_replication_analysis.v93", complete=complete,
        primary_complete=primary, checks=checks, natural=natural, construction=construction,
        training_variance=analyze_training_variance(run), inherited_dynamics=run["inherited_dynamics"],
        actual_executed_work=dict(**transitions, natural_transitions=natural_transitions,
            newly_sampled_transitions=sum(transitions.values()) + natural_transitions,
            actual_tree_fits=construction["actual_tree_fits"],
            new_pair_tree_fits=construction["model_counts"]["paired"].get("tree_fits", 0),
            new_v91_continuation_tree_fits=construction["model_counts"]["v91_continuation"].get("tree_fits", 0),
            new_head_tree_fits=sum(counts.get("tree_fits", 0) for counts in construction["head_counts"].values()),
            construction_seconds=construction["seconds"],
            natural_evaluation_seconds=sum(cost["evaluation_seconds"] for stage in natural["checkpoints"].values()
                for method in stage["methods"].values() for cost in method["costs"]),
            actual_wall_seconds=run["actual_wall_seconds"]),
        evidence_scope="Fresh source histories and natural evaluation streams; all lifecycle effects receive equal weights. "
            "Source and base branches are shared and counted once in executed work. Prefix and additional terminal "
            "acquisition have exactly matched actual transition budgets, including discarded incomplete blocks. "
            "Budget exhaustion in extra acquisition is an intended algorithm outcome, not a missing natural-game terminal. "
            "MC_EXTRA is the specified round-robin finite-budget algorithm; random length-dependent stopping gives no "
            "unbiasedness or optimal-MC claim. The OOF training variance diagnostic is not independent validation. "
            "Cancelled interventions are kept separate from newly executed or changed fragments.")


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
