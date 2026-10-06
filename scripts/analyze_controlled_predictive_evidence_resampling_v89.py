"""Compare evidence-driven and balanced sampling with fixed learners and roots."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.analyze_controlled_predictive_evidence_learning_v88 import (
    CATEGORIES, TERMINAL, WIRING, _mean, _key, _summary, _cohort, _effect,
    _across_lives, _gate_category, _gate_decomposition,
)
from acfqp.science.controlled_predictive_evidence_fragments_v88 import (
    EvidenceSelector, OPTIONS, paired_evidence,
)

ARMS = ("BALANCED", "EVIDENCE")
VARIANTS = ("BASE", *ARMS)
KINDS = ("POINT", "SUPPORTED")
CONTRASTS = tuple(dict.fromkeys(
    [(f"EVIDENCE_{kind}", f"BALANCED_{kind}") for kind in KINDS]
    + [(f"{arm}_{kind}", f"BASE_{kind}") for arm in ARMS for kind in KINDS]
    + [(f"{variant}_{kind}", "H2_ONLY") for variant in VARIANTS for kind in KINDS]
    + [(f"{variant}_SUPPORTED", f"{variant}_POINT") for variant in VARIANTS]))
GATE_CONTRASTS = tuple((f"{variant}_SUPPORTED", f"{variant}_POINT") for variant in VARIANTS) + (
    ("BALANCED_SUPPORTED", "BASE_SUPPORTED"), ("EVIDENCE_SUPPORTED", "BASE_SUPPORTED"),
    ("EVIDENCE_SUPPORTED", "BALANCED_SUPPORTED"))


def _counters(groups):
    return {key: dict(value) for key, value in groups.items()}


def analyze_run(run):
    settings = run["settings"]
    lives, methods, queries = settings["lifecycles"], settings["methods"], settings["queries"]
    indexed = {life["id"]: life for life in run["lifecycles"]}
    roster = len(indexed) == len(run["lifecycles"]) == len(lives) and set(indexed) == set(lives)
    cohorts, pairings, fit_rows, budget_rows, confirmation_rows = [], {}, [], [], []
    histories, query_histories, inherited_rows = [], [], []
    wiring_ok, fit_ok, budget_ok, confirmation_ok, histories_ok = (True,) * 5
    fits = {variant: Counter() for variant in VARIANTS}
    acquired = {arm: {name: Counter() for name in ("branch_work", "planning_counts", "outcomes", "counts")} for arm in ARMS}
    confirmed = {name: Counter() for name in ("branch_work", "planning_counts", "outcomes", "counts")}
    executed = {method: {name: Counter() for name in ("ground", "planning", "outcomes")} for method in methods}
    inherited_work = {name: Counter() for name in ("source_work", "branch_work")}
    for life in lives:
        row = indexed.get(life, {})
        evaluation = row.get("evaluation", {})
        base = row.get("updates", {}).get("BASE", {}).get("dataset", {})
        for variant in VARIANTS:
            data = row.get("updates", {}).get(variant, {})
            dataset, update = data.get("dataset", {}), data.get("update", {})
            counts = update.get("counts", {})
            fit_ok &= (dataset.get("roots") == dataset.get("training_roots", 0) + dataset.get("heldout_roots", 0)
                and dataset.get("records") == 4 * dataset.get("roots", 0)
                and dataset.get("training_roots") == 10 * len(queries)
                and dataset.get("heldout_roots") == 2 * len(queries)
                and all(dataset.get(key) == base.get(key) for key in ("roots", "training_roots", "heldout_roots", "records"))
                and counts.get("fit_roots") == dataset.get("training_roots")
                and counts.get("fit_candidate_labels") == 4 * dataset.get("training_roots", 0)
                and counts.get("tree_fits") == len(queries))
            fits[variant].update(counts)
            fit_rows.append(dict(id=life, variant=variant, **data))
        for arm in ARMS:
            data = row.get("allocation", {}).get(arm, {})
            aq = data.get("queries", {})
            budget_ok &= set(aq) == set(queries)
            for query in queries:
                source = aq.get(query, {})
                actual = source.get("branch_work", {}).get("sampled_transitions", 0)
                matched = source.get("budget") == source.get("used_transitions") == actual == settings["training_budget_per_query_allocation"]
                budget_ok &= matched
                budget_rows.append(dict(id=life, arm=arm, query=query, actual_transitions=actual,
                    actual_budget_matched=matched, **source))
                for name in ("branch_work", "planning_counts", "outcomes"):
                    acquired[arm][name].update(source.get(name, {}))
                for name in ("branch_trajectories", "completed_blocks", "incomplete_blocks"):
                    acquired[arm]["counts"][name] += source.get(name, 0)
        confirmation = row.get("confirmation", {})
        max_trajectories = len(OPTIONS) * settings["confirmation_replicas"]
        confirmation_ok &= (confirmation.get("roots") == base.get("training_roots")
            and confirmation.get("roots") == confirmation.get("complete_roots", 0) + confirmation.get("incomplete_roots", 0)
            and confirmation.get("complete_roots", 0) * max_trajectories <= confirmation.get("branch_trajectories", -1)
                <= confirmation.get("roots", 0) * max_trajectories)
        for name in ("branch_work", "planning_counts", "outcomes"):
            confirmed[name].update(confirmation.get(name, {}))
        for name in ("roots", "complete_roots", "incomplete_roots", "branch_trajectories"):
            confirmed["counts"][name] += confirmation.get(name, 0)
        confirmation_rows.append(dict(id=life, **confirmation))
        inherited = row.get("inherited", {})
        inherited_rows.append(dict(id=life, **inherited))
        for name in inherited_work:
            inherited_work[name].update(inherited.get(name, {}))
        wiring_ok &= all(evaluation.get("wiring", {}).get(name) is True for name in WIRING)
        for method in methods:
            games = evaluation.get("methods", {}).get(method, {}).get("games", [])
            for game in games:
                executed[method]["ground"].update(game["environment_counts"])
                executed[method]["planning"].update(game["planning_counts"])
                executed[method]["outcomes"][game["status"]] += 1
            history = evaluation.get("pairwise_histories", {}).get(method, {})
            histories_ok &= history.get("pairs") == len(queries) * settings["evaluation_replicas"]
            histories.append(dict(id=life, method=method, **history))
            query_histories.append(dict(id=life, method=method, **evaluation.get("query_response", {}).get(method, {})))
        for query in queries:
            cohort, grouped = _cohort(evaluation, query, settings)
            pairings[life, query] = cohort, grouped
            cohorts.append(dict(id=life, query=query, **{key: value for key, value in cohort.items() if key != "keys"}))
    def games(life, method, query=None):
        rows = indexed.get(life, {}).get("evaluation", {}).get("methods", {}).get(method, {}).get("games", [])
        return [row for row in rows if query is None or row["query"] == query]
    summaries = {}
    for method in methods:
        costs = [dict(id=life, **indexed.get(life, {}).get("evaluation", {}).get("methods", {}).get(method, {}).get("costs", {})) for life in lives]
        fields = set().union(*(cost.keys() for cost in costs)) - {"id"}
        selected = [row for row in histories if row["method"] == method]
        summaries[method] = dict(queries={query: dict(
            pooled=_summary([game for life in lives for game in games(life, method, query)]),
            lifecycles=[dict(id=life, **_summary(games(life, method, query))) for life in lives]) for query in queries},
            paired_histories=dict(pairs=sum(row.get("pairs", 0) for row in selected),
                identical_to_h2=sum(row.get("identical_to_h2", 0) for row in selected)),
            cumulative_cost_attribution=dict(lifecycles=costs, totals={name: math.fsum(cost[name] for cost in costs)
                if all(name in cost for cost in costs) else None for name in fields}))
    comparisons = {f"{left}_minus_{right}": {query: _across_lives([
        dict(id=life, **_effect(pairings[life, query][1][left], pairings[life, query][1][right],
                             pairings[life, query][0]["keys"])) for life in lives]) for query in queries}
        for left, right in CONTRASTS}
    decomposition = {f"{left}_minus_{right}": {query: _gate_decomposition(lives, query, left, right, indexed, pairings)
        for query in queries} for left, right in GATE_CONTRASTS}
    gate_ok = all(data["record_roster_complete"] for contrast in decomposition.values() for data in contrast.values())
    all_games = [game for life in lives for method in methods for game in games(life, method)]
    game_ok = bool(cohorts) and all(row["roster_complete"] for row in cohorts)
    paired_ok = bool(cohorts) and all(row["seeds_paired"] for row in cohorts)
    training_transitions = sum(groups["branch_work"]["sampled_transitions"] for groups in acquired.values())
    confirmation_transitions = confirmed["branch_work"]["sampled_transitions"]
    evaluation_transitions = sum(groups["ground"]["sampled_transitions"] for groups in executed.values())
    return dict(schema="acfqp.evidence_resampling_analysis.v89", complete=(run["status"] == "complete" and roster
        and game_ok and paired_ok and wiring_ok and fit_ok and budget_ok and confirmation_ok and histories_ok and gate_ok),
        cohort=dict(lifecycle_roster_complete=roster, evaluation_roster_complete=game_ok, paired_seeds_complete=paired_ok,
            controller_wiring_complete=wiring_ok, training_root_and_candidate_accounting_complete=fit_ok,
            actual_acquisition_budgets_matched=budget_ok, confirmation_roster_complete=confirmation_ok,
            paired_histories_complete=histories_ok, gate_change_roster_complete=gate_ok,
            paired_terminal_cohorts=cohorts, expected_games=len(lives) * len(methods) * len(queries) * settings["evaluation_replicas"],
            all_evaluation_games_terminal=bool(all_games) and all(game["status"] in TERMINAL for game in all_games), **_summary(all_games)),
        methods=summaries, final_comparisons=comparisons, gate_decomposition=decomposition,
        fitting=dict(updates=fit_rows, new_fit_counts=_counters(fits)), allocation=dict(queries=budget_rows),
        confirmation=dict(lifecycles=confirmation_rows, **_counters(confirmed)),
        inherited=dict(lifecycles=inherited_rows, **_counters(inherited_work)),
        query_responses=query_histories, pairwise_histories=histories,
        actual_executed_work=dict(new_source_games=0, acquisition={arm: _counters(groups) for arm, groups in acquired.items()},
            confirmation=_counters(confirmed), evaluation={method: _counters(groups) for method, groups in executed.items()},
            new_fit_counts=_counters(fits), new_acquisition_transitions=training_transitions,
            new_confirmation_transitions=confirmation_transitions, new_evaluation_transitions=evaluation_transitions,
            newly_sampled_transitions=training_transitions + confirmation_transitions + evaluation_transitions,
            actual_wall_seconds=run.get("actual_wall_seconds"), workers=settings["workers"]),
        evidence_scope="Fixed roots, candidates, classifier and support rule; only allocation changes. Budgets include "
            "unfinished branches; complete paired blocks alone update labels. Confirmation and natural evaluation "
            "are additional independent sampling work. Natural effects share the seven-method terminal cohort and "
            "average lifecycles equally; cutoff costs remain. Disabled interventions recover H2, while enabled or "
            "changed fragments alter execution. Method cost attributions overlap and are not additive wall time. "
            "Adaptive two-standard-error labels are operational training targets, not confidence statements.")


def _root_key(root):
    return root["query"], root["episode"], tuple(root["board"])


def _read_rows(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def diagnose_confirmation(life_inputs, settings):
    """Fresh suffixes evaluate frozen labels; all candidate counts are descriptive."""
    details, root_checks, selection_rows = [], [], []
    valid = True
    for data in life_inputs:
        life, roots, logs, updates, selectors = (data[key] for key in ("id", "roots", "logs", "updates", "selectors"))
        indexed = {variant: {_root_key(root): root for root in roots[variant]} for variant in VARIANTS}
        base = indexed["BASE"]
        training_keys = {key for key, root in base.items() if root["episode"] % 5 != 4}
        log_index = {_root_key(log["root"]): log for log in logs}
        same_roots = all(set(group) == set(base) and len(group) == len(roots[variant]) for variant, group in indexed.items())
        confirmation_roster = len(logs) == len(log_index) and set(log_index) == training_keys
        heldout_unchanged = all(indexed[variant].get(key) == root for variant in ARMS
                               for key, root in base.items() if key not in training_keys)
        fit_replica_counts = {variant: updates[variant]["update"]["counts"].get("paired_root_replicas_read") ==
            sum(indexed[variant][key]["n_replicas"] for key in training_keys) for variant in VARIANTS} if same_roots else {}
        valid &= same_roots and confirmation_roster and heldout_unchanged and all(fit_replica_counts.values())
        root_checks.append(dict(id=life, frozen_roots_match=same_roots, heldout_roots_unchanged=heldout_unchanged,
            confirmation_training_roster_matches=confirmation_roster, fit_replica_counts_match_frozen_training=fit_replica_counts,
            training_roots=len(training_keys), complete_confirmation_roots=sum(log.get("complete_block", False) for log in logs)))
        if not same_roots or not confirmation_roster:
            continue
        for key in sorted(training_keys):
            query, episode, board = key
            log = log_index[key]
            complete = log["complete_block"]
            independent = {option: paired_evidence(log["pair_deltas"][option], query) for option in OPTIONS[1:]} if complete else {}
            if complete:
                valid &= all(item["n"] == settings["confirmation_replicas"] for item in independent.values())
            for variant in ARMS:
                for option in OPTIONS[1:]:
                    old, new = base[key]["evidence"][option], indexed[variant][key]["evidence"][option]
                    fresh = independent.get(option)
                    details.append(dict(id=life, variant=variant, query=query, episode=episode, board=list(board), option=option,
                        old_status=old["status"], new_status=new["status"], newly_positive=old["label"] != 1 and new["label"] == 1,
                        unresolved_to_positive=old["label"] == 0 and new["label"] == 1,
                        training_n_before=old["n"], training_n_after=new["n"], confirmation_complete=complete,
                        confirmation=fresh))
            if complete:
                for variant in VARIANTS:
                    for kind in KINDS:
                        choice = selectors[variant].with_mode(kind).select(list(board), query)["option"]
                        utility = independent[choice]["mean_utility"] if choice != "H2" else 0.0
                        selection_rows.append(dict(id=life, query=query, episode=episode, method=f"{variant}_{kind}",
                            option=choice, observed_utility=utility))
    transitions, confirmations, choices = {}, {}, {}
    for variant in ARMS:
        transitions[variant], confirmations[variant] = {}, {}
        for query in settings["queries"]:
            selected = [row for row in details if row["variant"] == variant and row["query"] == query]
            transitions[variant][query] = dict(counts=dict(Counter(f'{row["old_status"]}_to_{row["new_status"]}' for row in selected)),
                by_option={option: dict(Counter(f'{row["old_status"]}_to_{row["new_status"]}' for row in selected if row["option"] == option))
                    for option in OPTIONS[1:]})
            life_rows = []
            for life in settings["lifecycles"]:
                newly = [row for row in selected if row["id"] == life and row["newly_positive"]]
                usable = [row for row in newly if row["confirmation_complete"]]
                root_utilities = {}
                for row in usable:
                    root_utilities.setdefault(row["episode"], []).append(row["confirmation"]["mean_utility"])
                life_rows.append(dict(id=life, newly_positive_candidates=len(newly), complete_candidates=len(usable),
                    distinct_roots=len(root_utilities), independent_positive_means=sum(row["confirmation"]["mean_utility"] > 0 for row in usable),
                    independent_status_counts=dict(Counter(row["confirmation"]["status"] for row in usable)),
                    observed_utility_sum=math.fsum(row["confirmation"]["mean_utility"] for row in usable),
                    observed_candidate_mean_utility=_mean(row["confirmation"]["mean_utility"] for row in usable),
                    observed_root_mean_utility=_mean(_mean(values) for values in root_utilities.values())))
            usable = [row for row in selected if row["newly_positive"] and row["confirmation_complete"]]
            unresolved = [row for row in selected if row["unresolved_to_positive"]]
            confirmed_unresolved = [row for row in unresolved if row["confirmation_complete"]]
            confirmations[variant][query] = dict(lifecycles=life_rows,
                unresolved_to_positive=dict(candidates=len(unresolved), complete_candidates=len(confirmed_unresolved),
                    independent_positive_means=sum(row["confirmation"]["mean_utility"] > 0 for row in confirmed_unresolved),
                    independent_status_counts=dict(Counter(row["confirmation"]["status"] for row in confirmed_unresolved)),
                    descriptive_mean_utility=_mean(row["confirmation"]["mean_utility"] for row in confirmed_unresolved)),
                newly_positive_candidates=sum(row["newly_positive"] for row in selected), complete_candidates=len(usable),
                independent_positive_means=sum(row["confirmation"]["mean_utility"] > 0 for row in usable),
                independent_status_counts=dict(Counter(row["confirmation"]["status"] for row in usable)),
                descriptive_pooled_candidate_mean_utility=_mean(row["confirmation"]["mean_utility"] for row in usable),
                equal_lifecycle_root_mean_utility=_mean(row["observed_root_mean_utility"] for row in life_rows)
                    if all(row["observed_root_mean_utility"] is not None for row in life_rows) else None)
    for method in [f"{variant}_{kind}" for variant in VARIANTS for kind in KINDS]:
        choices[method] = {}
        for query in settings["queries"]:
            rows = [row for row in selection_rows if row["method"] == method and row["query"] == query]
            lives = [dict(id=life, roots=sum(row["id"] == life for row in rows),
                mean_utility=_mean(row["observed_utility"] for row in rows if row["id"] == life),
                interventions=sum(row["id"] == life and row["option"] != "H2" for row in rows)) for life in settings["lifecycles"]]
            choices[method][query] = dict(lifecycles=lives,
                equal_lifecycle_mean_utility=_mean(row["mean_utility"] for row in lives) if all(row["roots"] for row in lives) else None)
    return dict(schema="acfqp.evidence_resampling_confirmation.v89", complete=bool(valid), root_checks=root_checks,
        label_transitions=transitions, newly_positive_confirmation=confirmations, learned_choices_on_training_roots=choices,
        candidate_details=details, learned_choice_details=selection_rows,
        evidence_scope="All original training roots receive the same fixed fresh confirmation replica count after "
            "models are frozen; incomplete roots remain counted and supply no labels. Confirmation never enters "
            "the training-root files. Two-standard-error status is an operational label, not a calibrated interval. "
            "Four candidates share each root and H2 suffix; candidate counts and pooled utilities are descriptive, "
            "not independent replication. Root and lifecycle summaries preserve this grouping. These familiar "
            "training states test suffix repeatability; fresh natural games separately test deployment generalization.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    run = json.loads((args.directory / "run.json").read_text())
    result = analyze_run(run)
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    inputs = []
    for life in run["lifecycles"]:
        folder = args.directory / f'life_{life["id"]}'
        roots = {"BASE": _read_rows(folder / "base_paired_roots.jsonl.gz")}
        roots.update({variant: _read_rows(folder / variant.lower() / "training_roots.jsonl.gz") for variant in ARMS})
        inputs.append(dict(id=life["id"], roots=roots, updates=life["updates"],
            logs=json.loads((folder / "confirmation/root_logs.json").read_text()),
            selectors={variant: EvidenceSelector.from_payload(json.loads((folder / f"{variant.lower()}_selector.json").read_text()))
                       for variant in VARIANTS}))
    diagnosis = diagnose_confirmation(inputs, run["settings"])
    (args.directory / "confirmation_diagnosis.json").write_text(json.dumps(diagnosis, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(complete=result["complete"], confirmation_diagnosis_complete=diagnosis["complete"],
                         final_comparisons=result["final_comparisons"])))


if __name__ == "__main__":
    main()
