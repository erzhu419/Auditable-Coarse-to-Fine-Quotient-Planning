"""Diagnose horizon changes on the fixed V78 paired acceptance trajectories."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path


MODELS = ("incumbent", "candidate")
STRATA = ("old", "new")
TERMINAL = ("WON", "LOST")


def _mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values else None


def _pair_key(row):
    return (row["stratum"], row["query"], row["replica"],
            row["root"]["episode"], row["root"]["step"], row["seed"])


def _sign(value):
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def _summary(pairs):
    pairs = list(pairs)
    statuses = Counter(f'{p["short_sign"]}->{p["full_sign"]}' for p in pairs)
    return dict(pairs=len(pairs), terminal_pairs=sum(p["full_terminal"] for p in pairs),
        mean_short_utility_delta=_mean(p["short_utility_delta"] for p in pairs),
        mean_full_utility_delta=_mean(p["full_utility_delta"] for p in pairs),
        mean_suffix_utility_delta=_mean(p["suffix_utility_delta"] for p in pairs),
        mean_short_score_delta=_mean(p["short_score_delta"] for p in pairs),
        mean_full_score_delta=_mean(p["full_score_delta"] for p in pairs),
        mean_suffix_score_delta=_mean(p["suffix_score_delta"] for p in pairs),
        strict_sign_reversals=sum(p["strict_sign_reversal"] for p in pairs),
        sign_changes=sum(p["short_sign"] != p["full_sign"] for p in pairs),
        sign_transitions=dict(statuses),
        full_outcomes_complete=bool(pairs) and all(p["full_terminal"] for p in pairs))


def _rule(groups, queries, complete, horizon):
    field = f"mean_{horizon}_utility_delta"
    complete_strata = complete and all(groups[s][q]["pairs"] for s in STRATA for q in queries)
    observed = complete_strata and (horizon == "short" or all(
        groups[s][q]["full_outcomes_complete"] for s in STRATA for q in queries))
    accepted = (all(groups[s][q][field] >= 0 for s in STRATA for q in queries)
        and any(groups["new"][q][field] > 0 for q in queries)) if observed else None
    return dict(complete_strata=bool(complete_strata), all_required_outcomes_observed=bool(observed),
                accepted=accepted)


def _natural_comparison(source_run, lives, checkpoint, queries):
    """Use retained natural evaluations only when they represent these two models."""
    if source_run is None:
        return None
    indexed = {life["id"]: life for life in source_run["lifecycles"]}
    results = {query: [] for query in queries}
    for life in lives:
        history = indexed.get(life, {}).get("stages", [])
        stage = next((row for row in history if row["episodes"] == checkpoint), {})
        prior = [row for row in history if row["episodes"] < checkpoint]
        model_alignment = (bool(stage.get("mse_acceptance", {}).get("accepted"))
            and all(not row["decision_acceptance"]["accepted"] for row in prior))
        for query in queries:
            rows = {method: [game for game in stage.get("methods", {}).get(method, {}).get("games", [])
                              if game["query"] == query] for method in ("MSE_PLAN", "FROZEN_PLAN")}
            game_key = lambda game: (game["seed"], game["replica"], game["query"])
            first, second = ({game_key(g): g for g in rows[m]} for m in ("MSE_PLAN", "FROZEN_PLAN"))
            paired = (len(first) == len(second) == source_run["settings"]["evaluation_replicas"]
                and len(first) == len(rows["MSE_PLAN"]) and len(second) == len(rows["FROZEN_PLAN"])
                and first.keys() == second.keys())
            valid = model_alignment and paired
            results[query].append(dict(id=life, model_alignment=model_alignment, paired=paired,
                mean_utility_delta=_mean(first[k]["utility"]-second[k]["utility"] for k in first) if valid else None,
                mean_score_delta=_mean(first[k]["score"]-second[k]["score"] for k in first) if valid else None))
    return dict(episodes=checkpoint, queries={query: dict(lifecycles=rows,
        complete=all(row["model_alignment"] and row["paired"] for row in rows),
        mean_utility_delta=_mean(row["mean_utility_delta"] for row in rows)
            if all(row["mean_utility_delta"] is not None for row in rows) else None)
        for query, rows in results.items()},
        evidence_scope="Previously executed natural games. Their initial-state distribution differs from the fixed "
            "acceptance roots; horizon effects and root-distribution effects must not be conflated.")


def analyze_run(run, source_run=None):
    settings = run["settings"]
    lives, checkpoints, queries = settings["lifecycles"], settings["checkpoints"], list(settings["queries"])
    indexed = {life["id"]: {stage["episodes"]: stage for stage in life["stages"]}
               for life in run["lifecycles"]}
    roster = (len(run["lifecycles"]) == len(lives) and set(indexed) == set(lives)
        and all(len(life["stages"]) == len(checkpoints)
            and {stage["episodes"] for stage in life["stages"]} == set(checkpoints)
            for life in run["lifecycles"]))
    events, pairs, problems, trajectory_counts = [], [], [], Counter()
    source_statuses, full_statuses, status_changes = Counter(), Counter(), Counter()
    inherited_work, extension_work, planning_work, prediction_work = Counter(), Counter(), Counter(), Counter()
    restoration_work = Counter()
    extension_seconds, expected_total = 0.0, 0
    for life in lives:
        for checkpoint in checkpoints:
            stage = indexed.get(life, {}).get(checkpoint, {})
            rows = stage.get("trajectories", [])
            expected = stage.get("expected_trajectories", 0)
            expected_total += expected
            complete = bool(stage) and len(rows) == expected and expected > 0
            groups = defaultdict(list)
            for row in rows:
                groups[_pair_key(row)].append(row)
                trajectory_counts["trajectories"] += 1
                source_statuses[row["short"]["status"]] += 1
                full_statuses[row["full"]["status"]] += 1
                status_changes[f'{row["short"]["status"]}->{row["full"]["status"]}'] += 1
                inherited_work.update(row["short"].get("work", {}))
                extension = row.get("extension", {})
                extension_work.update(extension.get("work", {}))
                planning_work.update(extension.get("planning_counts", {}))
                prediction_work.update(extension.get("prediction_counts", {}))
                restoration_work.update(environment_random_draws=extension.get("restoration_random_draws", 0),
                    model_random_draws=extension.get("model_restoration_random_draws", 0))
                extension_seconds += extension.get("seconds", 0.0)
            stage_pairs = []
            for key, matched in groups.items():
                names = Counter(row["model"] for row in matched)
                valid = names == Counter(MODELS)
                valid = valid and matched[0]["root"]["board"] == matched[1]["root"]["board"]
                valid = valid and key[0] in STRATA and key[1] in queries
                if not valid:
                    problems.append(dict(id=life, episodes=checkpoint, key=list(key), model_counts=dict(names)))
                    complete = False
                    continue
                by_model = {row["model"]: row for row in matched}
                incumbent, candidate = (by_model[name] for name in MODELS)
                deltas = {f"{horizon}_{metric}_delta": candidate[horizon][metric]-incumbent[horizon][metric]
                          for horizon in ("short", "full") for metric in ("score", "utility")}
                short, full = deltas["short_utility_delta"], deltas["full_utility_delta"]
                pair = dict(id=life, episodes=checkpoint, stratum=key[0], query=key[1], replica=key[2],
                    root_episode=key[3], root_step=key[4], seed=key[5], **deltas,
                    suffix_utility_delta=full-short,
                    suffix_score_delta=deltas["full_score_delta"]-deltas["short_score_delta"],
                    short_sign=_sign(short), full_sign=_sign(full), strict_sign_reversal=short*full < 0,
                    full_terminal=all(row["full"]["status"] in TERMINAL for row in matched))
                stage_pairs.append(pair)
            summaries = {stratum: {query: _summary(p for p in stage_pairs
                if p["stratum"] == stratum and p["query"] == query) for query in queries} for stratum in STRATA}
            short_rule = _rule(summaries, queries, complete, "short")
            full_rule = _rule(summaries, queries, complete, "full")
            events.append(dict(id=life, episodes=checkpoint, expected_trajectories=expected,
                trajectories=len(rows), complete=complete, groups=summaries,
                short_rule=short_rule, hypothetical_full_rule=full_rule,
                acceptance_changed=(short_rule["accepted"] != full_rule["accepted"])
                    if short_rule["accepted"] is not None and full_rule["accepted"] is not None else None))
            pairs.extend(stage_pairs)
    by_checkpoint = []
    for checkpoint in checkpoints:
        strata = {}
        for stratum in STRATA:
            strata[stratum] = {}
            for query in queries:
                rows = [dict(id=life, **_summary([p for p in pairs if p["id"] == life
                    and p["episodes"] == checkpoint and p["stratum"] == stratum and p["query"] == query]))
                    for life in lives]
                fields = ["mean_short_utility_delta", "mean_full_utility_delta", "mean_suffix_utility_delta",
                          "mean_short_score_delta", "mean_full_score_delta", "mean_suffix_score_delta"]
                means = {name: _mean(row[name] for row in rows) if all(row[name] is not None for row in rows)
                         else None for name in fields}
                strata[stratum][query] = dict(lifecycles=rows, lifecycle_means=means,
                    lifecycle_mean_sign_reversals=sum(row["mean_short_utility_delta"] is not None
                        and row["mean_full_utility_delta"] is not None
                        and row["mean_short_utility_delta"]*row["mean_full_utility_delta"] < 0 for row in rows))
        by_checkpoint.append(dict(episodes=checkpoint, strata=strata))
    expected_roster = expected_total == settings.get("expected_trajectories", expected_total)
    complete = run["status"] == "complete" and roster and expected_roster and all(event["complete"] for event in events)
    return dict(schema="acfqp.terminal_analysis.v79", complete=complete,
        cohort=dict(lifecycle_roster_complete=roster, expected_trajectory_roster_complete=expected_roster,
            paired_trajectories_complete=complete,
            expected_trajectories=expected_total, trajectories=trajectory_counts["trajectories"], pairs=len(pairs),
            pairing_problems=problems, short_status_counts=dict(source_statuses), full_status_counts=dict(full_statuses),
            status_transitions=dict(status_changes), all_full_outcomes_terminal=bool(pairs)
                and all(pair["full_terminal"] for pair in pairs)),
        checkpoints=by_checkpoint, acceptance_events=events, pairs=pairs,
        acceptance_summary={label: dict(accepted=sum(event[field]["accepted"] is True for event in events),
            rejected=sum(event[field]["accepted"] is False for event in events),
            unresolved=sum(event[field]["accepted"] is None for event in events))
            for label, field in (("reconstructed_short", "short_rule"), ("hypothetical_full", "hypothetical_full_rule"))},
        actual_executed_work=dict(inherited_prefix_counts=dict(inherited_work),
            new_extension_counts=dict(extension_work), new_planning_counts=dict(planning_work),
            new_prediction_counts=dict(prediction_work), restoration_counts=dict(restoration_work),
            extension_seconds_sum=extension_seconds,
            actual_wall_seconds=run.get("actual_wall_seconds")),
        retained_natural_comparison=_natural_comparison(source_run, lives, checkpoints[-1], queries),
        evidence_scope="Candidate minus incumbent on fixed V78 roots, seeds, models and prefixes. Full utility is "
            "truncated whenever an outcome is CUTOFF; such a stage has no hypothetical terminal acceptance verdict. "
            "Lifecycle means are the independent replication summaries. Paired trajectory sign changes are descriptive, "
            "not independent statistical replications. Hypothetical full acceptance does not alter V78 model adoption.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source", type=Path, default=Path("reports/controlled_predictive_decision_v78/run.json"))
    args = parser.parse_args()
    source = json.loads(args.source.read_text()) if args.source.exists() else None
    result = analyze_run(json.loads((args.directory/"run.json").read_text()), source)
    (args.directory/"analysis.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"complete": result["complete"], "cohort": result["cohort"],
                      "acceptance_summary": result["acceptance_summary"]}))


if __name__ == "__main__":
    main()
