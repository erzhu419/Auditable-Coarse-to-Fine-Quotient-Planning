"""Continual A -> B -> A' diagnostic for the V270 crossed-factor learner."""

from __future__ import annotations

from fractions import Fraction as F
from typing import Any

from .crossed_factor_transfer_v270 import (
    CANDIDATE_SUBSETS,
    CASE,
    FEATURES,
    SEEDS,
    SOURCE_AUDIT,
    SOURCE_FIT,
    SOURCE_PAIRS,
    TARGET_AUDIT,
    TARGET_PAIRS,
    TARGET_PREFIXES,
    Context,
    _contexts,
    _law,
    _posterior,
    _projection,
    select_factor_subsets,
)
from .mechanism_switch_task_v205 import ALPHABETS, OPERATORS
from .persistent_consequence_library_v263 import QUERIES, _draw_rows, consequence_vector
from .persistent_consequence_library_v267 import _metrics_bank


PHASES = ("A", "B", "A_prime")
SAMPLES_PER_OPERATOR = 64
TARGET_FIT = 48
# B changes one retry-law parameter for every target context.  The value is
# frozen here before any target stream is generated; A_prime restores A exactly.
B_RETRY_DELIVERY = F(1, 20)
B_RETRY_LOST = 1 - B_RETRY_DELIVERY
ARMS = ("RESET", "FROZEN_FACTOR", "CONTINUAL_FACTOR")


def _law_for_phase(context: Context, phase: str) -> dict[str, dict[str, F]]:
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    law = {operator: dict(values) for operator, values in _law(context).items()}
    if phase == "B":
        law["RECOVERY_RETRY"] = {
            "DELIVERY": B_RETRY_DELIVERY,
            "LOST": B_RETRY_LOST,
        }
    return law


def _stream_for_phase(context: Context, seed: int, phase: str) -> dict[str, list[str]]:
    return _draw_rows(_law_for_phase(context, phase), seed)


def _exact_vectors_for_phase(context: Context, phase: str) -> dict[str, tuple[F, F, F]]:
    return consequence_vector(CASE, _law_for_phase(context, phase))


def _empty_counts() -> dict[str, dict[str, int]]:
    return {operator: {category: 0 for category in ALPHABETS[operator]}
            for operator in OPERATORS}


def _add_grouped_rows(
    counts: dict[str, dict[str, int]],
    contexts_and_rows: list[tuple[Context, dict[str, list[str]], int]],
    target: Context,
    fields_by_operator: dict[str, tuple[str, ...]],
) -> None:
    """Add rows whose visible-factor projection matches ``target``."""
    for context, rows, end in contexts_and_rows:
        for operator in OPERATORS:
            if _projection(context, fields_by_operator[operator]) != _projection(
                target, fields_by_operator[operator]
            ):
                continue
            for successor in rows[operator][:end]:
                counts[operator][successor] += 1


def _source_counts(
    target: Context,
    source_contexts: tuple[Context, ...],
    source_streams: dict[str, dict[str, list[str]]],
    fields_by_operator: dict[str, tuple[str, ...]],
) -> dict[str, dict[str, int]]:
    counts = _empty_counts()
    _add_grouped_rows(
        counts,
        [(context, source_streams[context.context_id], SOURCE_FIT)
         for context in source_contexts],
        target,
        fields_by_operator,
    )
    return counts


def _model_for_arm(
    arm: str,
    target: Context,
    source_contexts: tuple[Context, ...],
    source_streams: dict[str, dict[str, list[str]]],
    selected: dict[str, tuple[str, ...]],
    prior_episodes: list[tuple[str, dict[str, list[str]]]],
    current_stream: dict[str, list[str]],
    prefix: int,
) -> dict[str, dict[str, F]]:
    if prefix not in TARGET_PREFIXES:
        raise ValueError(f"prefix is not frozen: {prefix}")
    if arm == "RESET":
        fields = {operator: () for operator in OPERATORS}
        counts = _empty_counts()
        _add_grouped_rows(counts, [(target, current_stream, prefix)], target, fields)
    elif arm == "FROZEN_FACTOR":
        counts = _source_counts(target, source_contexts, source_streams, selected)
    elif arm == "CONTINUAL_FACTOR":
        counts = _source_counts(target, source_contexts, source_streams, selected)
        _add_grouped_rows(
            counts,
            [(target, rows, TARGET_FIT) for _phase, rows in prior_episodes]
            + [(target, current_stream, prefix)],
            target,
            selected,
        )
    else:
        raise ValueError(f"unknown arm: {arm}")
    return _posterior(counts)


def _target_record(
    arm: str,
    phase: str,
    target: Context,
    prefix: int,
    source_contexts: tuple[Context, ...],
    source_streams: dict[str, dict[str, list[str]]],
    selected: dict[str, tuple[str, ...]],
    prior_episodes: list[tuple[str, dict[str, list[str]]]],
    current_stream: dict[str, list[str]],
) -> dict[str, Any]:
    model = _model_for_arm(
        arm, target, source_contexts, source_streams, selected,
        prior_episodes, current_stream, prefix,
    )
    exact = _exact_vectors_for_phase(target, phase)
    metrics = _metrics_bank(consequence_vector(CASE, model), exact, queries=QUERIES)
    return {
        "target": target.as_dict(),
        "phase": phase,
        "prefix_per_operator": prefix,
        "target_audit_per_operator": TARGET_AUDIT,
        "source_fit_observations_used": 0 if arm == "RESET" else len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
        "prior_fit_observations_used": len(prior_episodes) * TARGET_FIT * len(OPERATORS) if arm == "CONTINUAL_FACTOR" else 0,
        "current_fit_observations_used": prefix * len(OPERATORS) if arm != "FROZEN_FACTOR" else 0,
        "shared_target_fit_observations_available": (len(prior_episodes) * TARGET_FIT + prefix) * len(OPERATORS),
        "retry_delivery_estimate": str(model["RECOVERY_RETRY"]["DELIVERY"]),
        "metrics": metrics,
    }


def _stream_seed(seed: int, target_index: int, phase_index: int) -> int:
    # Separate source and phase streams while preserving a simple auditable map.
    return seed * 1_000 + 10_000 + target_index * 100 + phase_index


def run_replication() -> dict[str, Any]:
    source_contexts = _contexts(SOURCE_PAIRS, "source")
    target_contexts = _contexts(TARGET_PAIRS, "target")
    records = []
    for seed in SEEDS:
        source_streams = {
            context.context_id: _stream_for_phase(context, seed + index, "A")
            for index, context in enumerate(source_contexts)
        }
        selected = select_factor_subsets(source_contexts, source_streams)
        target_records = {arm: [] for arm in ARMS}
        lifecycle_streams = {}
        for target_index, target in enumerate(target_contexts):
            phase_rows = {
                phase: _stream_for_phase(
                    target,
                    _stream_seed(seed, target_index, phase_index),
                    phase,
                )
                for phase_index, phase in enumerate(PHASES)
            }
            lifecycle_streams[target.context_id] = phase_rows
            prior_episodes: list[tuple[str, dict[str, list[str]]]] = []
            for phase in PHASES:
                current_stream = phase_rows[phase]
                for prefix in TARGET_PREFIXES:
                    for arm in ARMS:
                        target_records[arm].append(_target_record(
                            arm, phase, target, prefix, source_contexts,
                            source_streams, selected["selected_fields"],
                            prior_episodes, current_stream,
                        ))
                # Only the fit prefix is committed before the next phase; the
                # 16-row suffix remains audit-only.
                prior_episodes.append((phase, current_stream))
        records.append({
            "seed": seed,
            "selected": selected,
            "source_contexts": [context.as_dict() for context in source_contexts],
            "target_contexts": [context.as_dict() for context in target_contexts],
            "arms": target_records,
            "phase_order": list(PHASES),
            "stream_seeds": {
                target_id: {
                    phase: _stream_seed(seed, target_index, phase_index)
                    for phase_index, phase in enumerate(PHASES)
                }
                for target_index, target_id in enumerate(lifecycle_streams)
            },
        })

    summary: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in ARMS:
        summary[arm] = {}
        for phase in PHASES:
            summary[arm][phase] = {}
            for prefix in TARGET_PREFIXES:
                bucket: dict[str, Any] = {
                    "policy_correct_counts": [],
                    "set_action_agreement_counts": [],
                    "exact_regrets": [],
                    "denominator_per_seed": len(target_contexts) * len(QUERIES),
                }
                for record in records:
                    rows = [
                        row for row in record["arms"][arm]
                        if row["phase"] == phase and row["prefix_per_operator"] == prefix
                    ]
                    metrics = [item for row in rows for item in row["metrics"].values()]
                    bucket["policy_correct_counts"].append(
                        sum(item["policy_correct"] for item in metrics)
                    )
                    bucket["set_action_agreement_counts"].append(
                        sum(item["set_action_agreement"] for item in metrics)
                    )
                    bucket["exact_regrets"].append(
                        str(sum((F(item["exact_value_regret"]) for item in metrics), F(0)))
                    )
                bucket["mean_policy_correct"] = sum(bucket["policy_correct_counts"]) / len(records)
                bucket["mean_set_action_agreement"] = sum(bucket["set_action_agreement_counts"]) / len(records)
                bucket["mean_exact_regret"] = str(
                    sum((F(value) for value in bucket["exact_regrets"]), F(0)) / len(records)
                )
                summary[arm][phase][str(prefix)] = bucket

    return {
        "schema": "acfqp.crossed_factor_continual.v271",
        "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "settings": {
            "seeds": list(SEEDS),
            "source_pairs": SOURCE_PAIRS,
            "target_pairs": TARGET_PAIRS,
            "phase_order": PHASES,
            "target_prefixes": TARGET_PREFIXES,
            "samples_per_operator": SAMPLES_PER_OPERATOR,
            "source_fit": SOURCE_FIT,
            "source_audit": SOURCE_AUDIT,
            "target_fit": TARGET_FIT,
            "target_audit": TARGET_AUDIT,
            "candidate_subsets": CANDIDATE_SUBSETS,
            "visible_features": FEATURES,
            "source_fit_observations_generated_per_seed": len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
            "source_audit_observations_generated_per_seed": len(source_contexts) * len(OPERATORS) * SOURCE_AUDIT,
            "target_fit_observations_generated_per_seed": len(target_contexts) * len(PHASES) * TARGET_FIT * len(OPERATORS),
            "target_audit_observations_generated_per_seed": len(target_contexts) * len(PHASES) * TARGET_AUDIT * len(OPERATORS),
            "b_changed_operator": "RECOVERY_RETRY",
            "b_retry_delivery": str(B_RETRY_DELIVERY),
            "b_retry_lost": str(B_RETRY_LOST),
            "arms": ARMS,
        },
        "records": records,
        "summary": summary,
        "limitations": [
            "This is a synthetic continuation of the V270 crossed-factor task, not the original Gate.",
            "The source selector and factor roles are frozen from the V270 source slice.",
            "Source and target row costs are reported separately; RESET is not a total-cost comparison.",
            "Four target corners and four seeds are an exploratory continual-transfer diagnostic.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("_")]
