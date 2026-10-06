"""Continual A -> B -> A' diagnostic with a frozen dynamics and query shift."""

from __future__ import annotations

from fractions import Fraction as F
from typing import Any

from .crossed_factor_continual_v271 import (
    ARMS,
    PHASES,
    SAMPLES_PER_OPERATOR,
    SEEDS,
    SOURCE_AUDIT,
    SOURCE_FIT,
    SOURCE_PAIRS,
    TARGET_AUDIT,
    TARGET_FIT,
    TARGET_PAIRS,
    TARGET_PREFIXES,
    _contexts,
    _model_for_arm,
    _stream_seed,
)
from .crossed_factor_transfer_v270 import CANDIDATE_SUBSETS, CASE, FEATURES, _law, select_factor_subsets
from .mechanism_switch_task_v205 import OPERATORS
from .persistent_consequence_library_v263 import QUERIES, _draw_rows, consequence_vector
from .persistent_consequence_library_v267 import _metrics_bank


# B changes only the evaluator's risk preference.  Dynamics and all streams
# remain the A law; A_prime restores the original query bank.
B_QUERIES = dict(QUERIES)
B_QUERIES["risk"] = (F(1), F(1), F(4))
PHASE_QUERIES = {"A": QUERIES, "B": B_QUERIES, "A_prime": QUERIES}


def _law_for_phase(context: Any, phase: str) -> dict[str, dict[str, F]]:
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    return {operator: dict(values) for operator, values in _law(context).items()}


def _stream_for_phase(context: Any, seed: int, phase: str) -> dict[str, list[str]]:
    return _draw_rows(_law_for_phase(context, phase), seed)


def _exact_vectors_for_phase(context: Any, phase: str) -> dict[str, tuple[F, F, F]]:
    return consequence_vector(CASE, _law_for_phase(context, phase))


def _queries_for_phase(phase: str) -> dict[str, tuple[F, F, F]]:
    try:
        return PHASE_QUERIES[phase]
    except KeyError as exc:
        raise ValueError(f"unknown phase: {phase}") from exc


def _target_record(
    arm: str,
    phase: str,
    target: Any,
    prefix: int,
    source_contexts: tuple[Any, ...],
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
    queries = _queries_for_phase(phase)
    metrics = _metrics_bank(consequence_vector(CASE, model), exact, queries=queries)
    return {
        "target": target.as_dict(),
        "phase": phase,
        "prefix_per_operator": prefix,
        "target_audit_per_operator": TARGET_AUDIT,
        "query_bank": {name: [str(value) for value in weights] for name, weights in queries.items()},
        "source_fit_observations_used": 0 if arm == "RESET" else len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
        "prior_fit_observations_used": len(prior_episodes) * TARGET_FIT * len(OPERATORS) if arm == "CONTINUAL_FACTOR" else 0,
        "current_fit_observations_used": prefix * len(OPERATORS) if arm != "FROZEN_FACTOR" else 0,
        "metrics": metrics,
    }


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
        stream_seeds: dict[str, dict[str, int]] = {}
        for target_index, target in enumerate(target_contexts):
            phase_rows = {
                phase: _stream_for_phase(
                    target, _stream_seed(seed, target_index, phase_index), phase
                )
                for phase_index, phase in enumerate(PHASES)
            }
            stream_seeds[target.context_id] = {
                phase: _stream_seed(seed, target_index, phase_index)
                for phase_index, phase in enumerate(PHASES)
            }
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
                prior_episodes.append((phase, current_stream))
        records.append({
            "seed": seed,
            "selected": selected,
            "source_contexts": [context.as_dict() for context in source_contexts],
            "target_contexts": [context.as_dict() for context in target_contexts],
            "phase_order": list(PHASES),
            "stream_seeds": stream_seeds,
            "arms": target_records,
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
                    "denominator_per_seed": len(target_contexts) * len(_queries_for_phase(phase)),
                }
                for record in records:
                    rows = [
                        row for row in record["arms"][arm]
                        if row["phase"] == phase and row["prefix_per_operator"] == prefix
                    ]
                    metrics = [item for row in rows for item in row["metrics"].values()]
                    bucket["policy_correct_counts"].append(sum(item["policy_correct"] for item in metrics))
                    bucket["set_action_agreement_counts"].append(sum(item["set_action_agreement"] for item in metrics))
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
        "schema": "acfqp.crossed_factor_query_continual.v272",
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
            "dynamics_changed": False,
            "query_changed_phase": "B",
            "query_change": {
                "risk_A": [str(value) for value in QUERIES["risk"]],
                "risk_B": [str(value) for value in B_QUERIES["risk"]],
            },
            "arms": ARMS,
        },
        "query_banks": {
            phase: {name: [str(value) for value in weights] for name, weights in queries.items()}
            for phase, queries in PHASE_QUERIES.items()
        },
        "records": records,
        "summary": summary,
        "limitations": [
            "This is a synthetic query-shift continuation of V270/V271, not the original Gate.",
            "The source selector, factor roles, dynamics, and streams are frozen; only the B query weights change.",
            "Source and target row costs are reported separately; RESET is not a total-cost comparison.",
            "Four target corners and four seeds are an exploratory query-adaptation diagnostic.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("_")]
