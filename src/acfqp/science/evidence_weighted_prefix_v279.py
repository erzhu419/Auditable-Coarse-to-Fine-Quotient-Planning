"""Structure uncertainty on immutable V278 execution histories."""

from fractions import Fraction as F
import gzip
import json
from math import exp
from pathlib import Path

from .crossed_factor_transfer_v270 import CANDIDATE_SUBSETS
from . import query_relevant_coverage_v278 as v278

HISTORY_ARMS = ("PASSIVE_REVISED", "RELEVANT_REVISED")


def evidence_weights(selection):
    """Uniform structure prior, no temperature; exact normalization of floats."""
    weights = {}
    for operator, ranked in selection["scores"].items():
        best = max(row["score"] for row in ranked)
        raw = {tuple(row["fields"]): F(exp(row["score"] - best)) for row in ranked}
        total = sum(raw.values(), F(0))
        weights[operator] = {fields: value / total for fields, value in raw.items()}
    return weights


def candidate_learners(source_contexts, streams):
    return {fields: v278.OnlineLearner("CONTINUAL_FACTOR_ONLINE",
            {op: fields for op in v278.OPERATORS}, source_contexts, streams)
            for fields in CANDIDATE_SUBSETS}


def weighted_model(candidates, target, weights):
    predictions = {fields: learner.model(target) for fields, learner in candidates.items()}
    result = {}
    for operator in v278.OPERATORS:
        support = set().union(*(model[operator] for model in predictions.values()))
        result[operator] = {outcome: sum((weight * predictions[fields][operator].get(outcome, F(0))
            for fields, weight in weights[operator].items()), F(0)) for outcome in sorted(support)}
    return result


def serialized_weights(weights):
    return {op: [{"fields": fields, "weight": float(value)} for fields, value in row.items()]
            for op, row in weights.items()}


def replay_arm(record, arm, source_contexts, streams):
    hard = v278.OnlineLearner("CONTINUAL_FACTOR_ONLINE",
        dict(record["initial_selection"]["selected_fields"]), source_contexts, streams)
    candidates = candidate_learners(source_contexts, streams)
    selections = {(s["phase"], s["episode"]): s for s in record["selections"][arm]}
    weights, active_episode = None, None
    totals = {phase: {"opportunities": 0, "map_regret": F(0), "weighted_regret": F(0),
              "changed": 0, "improved_equal_worse": [0, 0, 0]} for phase in v278.PHASES}
    changed_rows = []
    for ordinal, row in enumerate(record["arms"][arm]):
        phase, episode, trial = row["phase"], row["episode"], row["trial"]
        visible = row["context"]
        target = v278._contexts(((visible["road_profile"], visible["retry_service"]),), "target")[0]
        key = (phase, episode)
        if key != active_episode:
            selection = selections[key]
            if selection["online_events_used"] != len(hard.history):
                raise ValueError("episode selection does not match committed prefix")
            hard.selected = {op: tuple(fields) for op, fields in selection["selected_fields"].items()}
            weights, active_episode = evidence_weights(selection), key
        if row["history_before"] != len(hard.history):
            raise ValueError("decision does not match committed prefix")
        hard_vectors = v278._consequence_vector_dynamic(v278.CASE, hard.model(target))
        weighted_vectors = v278._consequence_vector_dynamic(v278.CASE, weighted_model(candidates, target, weights))
        query = row["query"]
        hard_policy = v278._choose_policy(hard_vectors, v278.QUERIES[query])
        weighted_policy = v278._choose_policy(weighted_vectors, v278.QUERIES[query])
        exact = v278._exact_vectors(target, phase)
        hard_regret, mixed_regret = (v278.regret(exact, query, policy) for policy in (hard_policy, weighted_policy))
        if hard_policy != row["recommended_policy"] or hard_regret != F(row["recommendation_regret"]):
            raise ValueError("hard-MAP replay differs from immutable history")
        delta = mixed_regret - hard_regret
        total = totals[phase]
        total["opportunities"] += 1
        total["map_regret"] += hard_regret
        total["weighted_regret"] += mixed_regret
        total["improved_equal_worse"][0 if delta < 0 else 2 if delta > 0 else 1] += 1
        if weighted_policy != hard_policy:
            total["changed"] += 1
            changed_rows.append({"ordinal": ordinal, "phase": phase, "episode": episode,
                "trial": trial, "context": visible, "query": query, "history_before": len(hard.history),
                "map_policy": hard_policy, "weighted_policy": weighted_policy,
                "map_regret": str(hard_regret), "weighted_regret": str(mixed_regret), "delta": str(delta),
                "weights": serialized_weights(weights),
                "map_utilities": {p: float(v278.utility(v, query)) for p, v in hard_vectors.items()},
                "weighted_utilities": {p: float(v278.utility(v, query)) for p, v in weighted_vectors.items()}})
        for event in row["events"]:
            for learner in (hard, *candidates.values()):
                learner.observe(target, phase, episode, trial, event["operator"], event["outcome"])
        if row["history_after"] != len(hard.history):
            raise ValueError("committed event count differs from immutable history")
    map_total = sum((p["map_regret"] for p in totals.values()), F(0))
    mixed_total = sum((p["weighted_regret"] for p in totals.values()), F(0))
    return {"map_regret": str(map_total), "weighted_regret": str(mixed_total),
            "delta": str(mixed_total - map_total), "opportunities": sum(p["opportunities"] for p in totals.values()),
            "changed": len(changed_rows), "improved_equal_worse": [sum(p["improved_equal_worse"][i] for p in totals.values()) for i in range(3)],
            "phases": {phase: {**p, "map_regret": str(p["map_regret"]), "weighted_regret": str(p["weighted_regret"])}
                       for phase, p in totals.items()}, "changed_rows": changed_rows}


def summarize(records):
    summaries = {}
    for arm in HISTORY_ARMS:
        items = [r["arms"][arm] for r in records]
        deltas = [F(item["delta"]) for item in items]
        summaries[arm] = {"mean_map_regret": str(sum((F(i["map_regret"]) for i in items), F(0)) / len(items)),
            "mean_weighted_regret": str(sum((F(i["weighted_regret"]) for i in items), F(0)) / len(items)),
            "mean_delta": str(sum(deltas, F(0)) / len(items)), "per_source_delta": list(map(str, deltas)),
            "sources_improved_equal_worse": [sum(d < 0 for d in deltas), sum(d == 0 for d in deltas), sum(d > 0 for d in deltas)],
            "changed": sum(i["changed"] for i in items),
            "decisions_improved_equal_worse": [sum(i["improved_equal_worse"][n] for i in items) for n in range(3)],
            "opportunities": sum(i["opportunities"] for i in items)}
    return summaries


def run_diagnostic(input_path):
    with gzip.open(input_path, "rt", encoding="utf-8") as handle:
        retained = json.load(handle)
    records = []
    for original in retained["records"]:
        contexts = v278._contexts(v278.SOURCE_PAIRS, "source")
        streams = {c.context_id: v278._stream(c, original["source_seed"] + index) for index, c in enumerate(contexts)}
        records.append({"source_seed": original["source_seed"], "seed": original["seed"],
                        "arms": {arm: replay_arm(original, arm, contexts, streams) for arm in HISTORY_ARMS}})
        print(f"replayed {len(records)}/{len(retained['records'])} source_seed={original['source_seed']}", flush=True)
    return {"schema": "acfqp.evidence_weighted_prefix.v279", "status": "DIAGNOSTIC_COMPLETE",
            "scientific_gate": "NOT_A_FORMAL_GATE", "input": str(Path(input_path).resolve()),
            "settings": {"histories": HISTORY_ARMS, "structure_prior": "uniform",
                         "weights": "exp(score-max) normalized; episode-start only",
                         "support": "unchanged projection-local observed support",
                         "endpoint": "fixed-history recommendation regret; no counterfactual feedback"},
            "accounting": {"new_source_observations": 0, "new_target_observations": 0,
                           "replayed_decisions": sum(r["arms"][arm]["opportunities"] for r in records for arm in HISTORY_ARMS)},
            "records": records, "summary": summarize(records)}
