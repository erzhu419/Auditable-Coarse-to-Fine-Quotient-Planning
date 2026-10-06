"""Crossed observable-factor transfer diagnostic for consequence learning."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F
from math import lgamma
from typing import Any

from .mechanism_switch_task_v205 import ALPHABETS, OPERATORS, WEATHER
from .persistent_consequence_library_v263 import QUERIES, consequence_vector, _draw_rows
from .persistent_consequence_library_v267 import _metrics_bank

ROAD_WEATHER = ("normal", "wet", "blocked")
RETRY_WEATHER = ("normal", "wet", "blocked")
SOURCE_PAIRS = ((0, 0), (1, 0), (2, 0), (0, 1), (0, 2))
TARGET_PAIRS = ((1, 1), (1, 2), (2, 1), (2, 2))
TARGET_PREFIXES = (0, 4, 8, 16, 32, 48)
SAMPLES_PER_OPERATOR = 64
SOURCE_FIT = 48
SOURCE_AUDIT = 16
TARGET_AUDIT = 16
SEEDS = (270401, 270402, 270403, 270404)
FEATURES = ("road_profile", "retry_service")
CANDIDATE_SUBSETS = ((), ("road_profile",), ("retry_service",), FEATURES)
CASE = {"operating": "low", "retry_cost": "19/20"}


@dataclass(frozen=True)
class Context:
    context_id: str
    road_profile: int
    retry_service: int

    def as_dict(self) -> dict[str, int | str]:
        return {"id": self.context_id, "road_profile": self.road_profile,
                "retry_service": self.retry_service}


def _contexts(pairs: tuple[tuple[int, int], ...], prefix: str) -> tuple[Context, ...]:
    return tuple(Context(f"{prefix}_{road}_{retry}", road, retry)
                  for road, retry in pairs)


def _law(context: Context) -> dict[str, dict[str, F]]:
    road = WEATHER[ROAD_WEATHER[context.road_profile]]
    retry = WEATHER[RETRY_WEATHER[context.retry_service]]
    return {
        "SHORT_PASS": {"DELIVERY": road[0], "LOST": 1 - road[0]},
        "DETOUR_PASS": {"DELIVERY": road[1], "LOST": road[2], "RECOVERY": road[3]},
        "RECOVERY_RETRY": {"DELIVERY": retry[4], "LOST": 1 - retry[4]},
    }


def _stream(context: Context, seed: int) -> dict[str, list[str]]:
    law = _law(context)
    return _draw_rows(law, seed)


def _projection(context: Context, fields: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(getattr(context, field) for field in fields)


def _source_score(contexts: tuple[Context, ...], streams: dict[str, dict[str, list[str]]],
                  operator: str, fields: tuple[str, ...]) -> float:
    groups: dict[tuple[int, ...], dict[str, int]] = {}
    alphabet = ALPHABETS[operator]
    for context in contexts:
        key = _projection(context, fields)
        counts = groups.setdefault(key, {category: 0 for category in alphabet})
        for successor in streams[context.context_id][operator][:SOURCE_FIT]:
            counts[successor] += 1
    score = 0.0
    for counts in groups.values():
        total = sum(counts.values())
        score += lgamma(len(alphabet) / 2) - lgamma(total + len(alphabet) / 2)
        score += sum(lgamma(count + 0.5) - lgamma(0.5) for count in counts.values())
    return score


def select_factor_subsets(source_contexts: tuple[Context, ...],
                          source_streams: dict[str, dict[str, list[str]]]) -> dict[str, Any]:
    selected, scores = {}, {}
    for operator in OPERATORS:
        ranked = []
        for fields in CANDIDATE_SUBSETS:
            ranked.append({"fields": list(fields), "score": _source_score(source_contexts, source_streams, operator, fields)})
        best = min(ranked, key=lambda row: (-row["score"], len(row["fields"]), tuple(row["fields"])))
        selected[operator] = tuple(best["fields"])
        scores[operator] = ranked
    return {"selected_fields": selected, "scores": scores,
            "source_fit_observations": len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
            "source_audit_observations": len(source_contexts) * len(OPERATORS) * SOURCE_AUDIT}


def _counts_for(contexts: tuple[Context, ...], streams: dict[str, dict[str, list[str]]],
                target: Context, fields_by_operator: dict[str, tuple[str, ...]],
                target_prefix: int) -> dict[str, dict[str, int]]:
    counts = {operator: {category: 0 for category in ALPHABETS[operator]} for operator in OPERATORS}
    for context in contexts:
        for operator in OPERATORS:
            fields = fields_by_operator[operator]
            if _projection(context, fields) != _projection(target, fields):
                continue
            end = target_prefix if context.context_id == target.context_id else SOURCE_FIT
            for successor in streams[context.context_id][operator][:end]:
                counts[operator][successor] += 1
    return counts


def _posterior(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, F]]:
    result = {}
    for operator in OPERATORS:
        alphabet = ALPHABETS[operator]
        total = sum(counts[operator].values())
        denominator = 2 * total + len(alphabet)
        result[operator] = {category: F(2 * counts[operator][category] + 1, denominator)
                            for category in alphabet}
    return result


def _exact_vectors(context: Context) -> dict[str, tuple[F, F, F]]:
    return consequence_vector(CASE, _law(context))


def _model_for_arm(arm: str, source_contexts: tuple[Context, ...], target_context: Context,
                   source_streams: dict[str, dict[str, list[str]]], target_streams: dict[str, list[str]],
                   selected: dict[str, tuple[str, ...]], prefix: int) -> dict[str, dict[str, F]]:
    all_contexts = source_contexts + (target_context,)
    streams = dict(source_streams)
    streams[target_context.context_id] = target_streams
    if arm == "RESET":
        fields = {operator: () for operator in OPERATORS}
        counts = {operator: {category: 0 for category in ALPHABETS[operator]} for operator in OPERATORS}
        for operator in OPERATORS:
            for successor in target_streams[operator][:prefix]:
                counts[operator][successor] += 1
    elif arm == "GLOBAL":
        fields = {operator: () for operator in OPERATORS}
        counts = _counts_for(all_contexts, streams, target_context, fields, prefix)
    elif arm == "FULL_CONTEXT":
        fields = {operator: FEATURES for operator in OPERATORS}
        counts = _counts_for(all_contexts, streams, target_context, fields, prefix)
    else:
        fields = selected if arm == "LEARNED_FACTOR" else {
            "SHORT_PASS": ("road_profile",), "DETOUR_PASS": ("road_profile",),
            "RECOVERY_RETRY": ("retry_service",)}
        counts = _counts_for(all_contexts, streams, target_context, fields, prefix)
    return _posterior(counts)


def _target_record(arm: str, target: Context, prefix: int,
                   source_contexts: tuple[Context, ...], source_streams: dict[str, dict[str, list[str]]],
                   target_streams: dict[str, list[str]], selected: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    model = _model_for_arm(arm, source_contexts, target, source_streams, target_streams, selected, prefix)
    exact = _exact_vectors(target)
    metrics = _metrics_bank(consequence_vector(CASE, model), exact, queries=QUERIES)
    return {"target": target.as_dict(), "prefix_per_operator": prefix,
            "target_audit_per_operator": TARGET_AUDIT, "metrics": metrics}


def run_replication() -> dict[str, Any]:
    source_contexts = _contexts(SOURCE_PAIRS, "source")
    target_contexts = _contexts(TARGET_PAIRS, "target")
    arms = ("RESET", "GLOBAL", "FULL_CONTEXT", "LEARNED_FACTOR", "SUPPLIED_FACTOR")
    records = []
    for seed in SEEDS:
        all_contexts = source_contexts + target_contexts
        streams = {context.context_id: _stream(context, seed + index)
                   for index, context in enumerate(all_contexts)}
        source_streams = {context.context_id: streams[context.context_id] for context in source_contexts}
        selected = select_factor_subsets(source_contexts, source_streams)
        target_records = {arm: [] for arm in arms}
        for target in target_contexts:
            for prefix in TARGET_PREFIXES:
                for arm in arms:
                    target_records[arm].append(_target_record(
                        arm, target, prefix, source_contexts, source_streams,
                        streams[target.context_id], selected["selected_fields"]))
        records.append({"seed": seed, "selected": selected, "source_contexts": [c.as_dict() for c in source_contexts],
                        "target_contexts": [c.as_dict() for c in target_contexts], "arms": target_records})
    summary = {}
    for arm in arms:
        summary[arm] = {}
        for prefix in TARGET_PREFIXES:
            summary[arm][str(prefix)] = {}
            for record in records:
                rows = [row for row in record["arms"][arm] if row["prefix_per_operator"] == prefix]
                metrics = [item for row in rows for item in row["metrics"].values()]
                bucket = summary[arm][str(prefix)]
                bucket.setdefault("policy_correct_counts", []).append(sum(item["policy_correct"] for item in metrics))
                bucket.setdefault("set_action_agreement_counts", []).append(sum(item["set_action_agreement"] for item in metrics))
                bucket.setdefault("exact_regrets", []).append(str(sum((F(item["exact_value_regret"]) for item in metrics), F(0))))
            bucket["mean_policy_correct"] = sum(bucket["policy_correct_counts"]) / len(bucket["policy_correct_counts"])
            bucket["mean_set_action_agreement"] = sum(bucket["set_action_agreement_counts"]) / len(bucket["set_action_agreement_counts"])
            bucket["mean_exact_regret"] = str(sum((F(value) for value in bucket["exact_regrets"]), F(0)) / len(bucket["exact_regrets"]))
    return {"schema": "acfqp.crossed_factor_transfer.v270", "status": "DEVELOPMENT_COMPLETE",
            "scientific_gate": "NOT_A_FORMAL_GATE", "settings": {
                "seeds": list(SEEDS), "source_pairs": SOURCE_PAIRS, "target_pairs": TARGET_PAIRS,
                "target_prefixes": TARGET_PREFIXES, "samples_per_operator": SAMPLES_PER_OPERATOR,
                "source_fit": SOURCE_FIT, "source_audit": SOURCE_AUDIT, "target_audit": TARGET_AUDIT,
                "candidate_subsets": CANDIDATE_SUBSETS,
                "true_generator_dependency": {"SHORT_PASS": "road_profile", "DETOUR_PASS": "road_profile", "RECOVERY_RETRY": "retry_service"}},
            "records": records, "summary": summary,
            "limitations": ["This is a synthetic crossed task flow built by recombining V205 numeric laws.",
                            "SUPPLIED_FACTOR uses true factor roles and is a reference, not a learned result or universal upper bound.",
                            "Four target pairs and four seeds are a development transfer diagnostic, not evidence for the original Gate."]}


__all__ = [name for name in globals() if not name.startswith("_")]
