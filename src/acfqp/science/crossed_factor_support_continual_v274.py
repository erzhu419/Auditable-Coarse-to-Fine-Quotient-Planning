"""Continual A -> B -> A' diagnostic for a genuine successor-support change."""

from __future__ import annotations

from fractions import Fraction as F
import random
from typing import Any

from .crossed_factor_continual_v271 import (
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
    _projection,
    _stream_seed,
    select_factor_subsets,
)
from .crossed_factor_transfer_v270 import CANDIDATE_SUBSETS, CASE, FEATURES, _law
from .mechanism_switch_task_v205 import ALPHABETS, OPERATORS
from .persistent_consequence_library_v263 import QUERIES, consequence_vector
from .persistent_consequence_library_v267 import _metrics_bank


NEW_SUCCESSOR = "DELAYED"
B_DELAYED_PROBABILITY = F(1, 5)
DELAYED_COST = F(2)
OLD_SUPPORT = {operator: tuple(ALPHABETS[operator]) for operator in OPERATORS}
ARMS = (
    "RESET_DYNAMIC",
    "FROZEN_STATIC",
    "CONTINUAL_FACTOR_EXPANDING",
    "LEGACY_COERCE",
)


def _law_for_phase(context: Any, phase: str) -> dict[str, dict[str, F]]:
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    law = {operator: dict(values) for operator, values in _law(context).items()}
    if phase == "B":
        retry = law["RECOVERY_RETRY"]
        scale = 1 - B_DELAYED_PROBABILITY
        law["RECOVERY_RETRY"] = {
            "DELIVERY": retry["DELIVERY"] * scale,
            "LOST": retry["LOST"] * scale,
            NEW_SUCCESSOR: B_DELAYED_PROBABILITY,
        }
    return law


def _stream_for_phase(context: Any, seed: int, phase: str) -> dict[str, list[str]]:
    rng = random.Random(seed)
    law = _law_for_phase(context, phase)
    return {
        operator: [
            rng.choices(tuple(values), weights=[float(values[category]) for category in values], k=1)[0]
            for _ in range(SAMPLES_PER_OPERATOR)
        ]
        for operator, values in law.items()
    }


def _empty_counts(support: dict[str, tuple[str, ...]] | None = None) -> dict[str, dict[str, int]]:
    alphabet = support or OLD_SUPPORT
    return {operator: {category: 0 for category in alphabet[operator]} for operator in OPERATORS}


def _support_union(*rows_sets: dict[str, list[str]]) -> dict[str, tuple[str, ...]]:
    result = {operator: list(OLD_SUPPORT[operator]) for operator in OPERATORS}
    for rows in rows_sets:
        for operator in OPERATORS:
            for category in rows[operator]:
                if category not in result[operator]:
                    result[operator].append(category)
    return {operator: tuple(categories) for operator, categories in result.items()}


def _add_rows(
    counts: dict[str, dict[str, int]],
    contexts_and_rows: list[tuple[Any, dict[str, list[str]], int]],
    target: Any,
    fields_by_operator: dict[str, tuple[str, ...]],
    *,
    coerce_unknown: bool = False,
) -> None:
    for context, rows, end in contexts_and_rows:
        for operator in OPERATORS:
            if _projection(context, fields_by_operator[operator]) != _projection(target, fields_by_operator[operator]):
                continue
            for successor in rows[operator][:end]:
                if successor not in counts[operator]:
                    if coerce_unknown:
                        successor = "LOST"
                    else:
                        counts[operator][successor] = 0
                counts[operator][successor] += 1


def _posterior(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, F]]:
    result = {}
    for operator, row in counts.items():
        total = sum(row.values())
        denominator = 2 * total + len(row)
        result[operator] = {category: F(2 * count + 1, denominator) for category, count in row.items()}
    return result


def _consequence_vector_dynamic(case: dict[str, str], probabilities: dict[str, dict[str, F]]) -> dict[str, tuple[F, F, F]]:
    from .continual_route_kernels_v202 import COST_PRIOR
    short_cost, detour_cost = COST_PRIOR[case["operating"]]
    retry_cost = F(case["retry_cost"])
    short = probabilities["SHORT_PASS"]
    detour = probabilities["DETOUR_PASS"]
    retry = probabilities["RECOVERY_RETRY"]
    delayed = retry.get(NEW_SUCCESSOR, F(0))
    return {
        "WAIT": (F(0), F(0), F(0)),
        "SHORT": (-short_cost, short["LOST"], short["DELIVERY"]),
        "DETOUR_RETURN": (-detour_cost, detour["LOST"], detour["DELIVERY"]),
        "DETOUR_RETRY": (
            -detour_cost - detour["RECOVERY"] * retry_cost - detour["RECOVERY"] * delayed * DELAYED_COST,
            detour["LOST"] + detour["RECOVERY"] * (retry["LOST"] + delayed),
            detour["DELIVERY"] + detour["RECOVERY"] * retry["DELIVERY"],
        ),
    }


def _exact_vectors_for_phase(context: Any, phase: str) -> dict[str, tuple[F, F, F]]:
    return _consequence_vector_dynamic(CASE, _law_for_phase(context, phase))


def _base_model(
    arm: str,
    target: Any,
    source_contexts: tuple[Any, ...],
    source_streams: dict[str, dict[str, list[str]]],
    selected: dict[str, tuple[str, ...]],
    prior_episodes: list[tuple[str, dict[str, list[str]]]],
    current_stream: dict[str, list[str]],
    prefix: int,
) -> tuple[dict[str, dict[str, F]], int, bool, int]:
    fields = selected if arm != "RESET_DYNAMIC" else {operator: () for operator in OPERATORS}
    source_rows = [(context, source_streams[context.context_id], SOURCE_FIT) for context in source_contexts]
    current_rows = [(target, current_stream, prefix)]
    unknown_count = sum(
        1 for operator in OPERATORS for successor in current_stream[operator][:prefix]
        if successor not in OLD_SUPPORT[operator]
    )
    if arm == "FROZEN_STATIC":
        counts = _empty_counts()
        _add_rows(counts, source_rows, target, selected)
        return _posterior(counts), unknown_count, unknown_count > 0, 0
    if arm == "LEGACY_COERCE":
        counts = _empty_counts()
        _add_rows(counts, source_rows, target, selected, coerce_unknown=True)
        _add_rows(counts, [(target, rows, TARGET_FIT) for _phase, rows in prior_episodes] + current_rows,
                  target, selected, coerce_unknown=True)
        prior_unknown_count = sum(
            1 for _phase, rows in prior_episodes
            for operator in OPERATORS
            for successor in rows[operator][:TARGET_FIT]
            if successor not in OLD_SUPPORT[operator]
        )
        return _posterior(counts), unknown_count, False, unknown_count + prior_unknown_count
    if arm == "RESET_DYNAMIC":
        current_prefix_rows = {operator: rows[:prefix] for operator, rows in current_stream.items()}
        support = _support_union(current_prefix_rows)
        counts = _empty_counts(support)
        _add_rows(counts, current_rows, target, fields)
        return _posterior(counts), unknown_count, False, 0
    current_prefix_rows = {operator: rows[:prefix] for operator, rows in current_stream.items()}
    prior_fit_rows = [
        {operator: rows[operator][:TARGET_FIT] for operator in OPERATORS}
        for _phase, rows in prior_episodes
    ]
    all_rows = prior_fit_rows + [current_prefix_rows]
    support = _support_union(*all_rows)
    counts = _empty_counts(support)
    _add_rows(counts, source_rows, target, fields)
    _add_rows(counts, [(target, rows, TARGET_FIT) for _phase, rows in prior_episodes] + current_rows,
              target, fields)
    return _posterior(counts), unknown_count, False, 0


def _abstain_metrics() -> dict[str, Any]:
    return {
        name: {
            "predicted_policy": None,
            "exact_policy": None,
            "policy_correct": False,
            "predicted_optimal_actions": [],
            "exact_optimal_actions": [],
            "set_action_agreement": False,
            "abstain": True,
            "exact_value_regret": None,
        }
        for name in QUERIES
    }


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
    model, unknown_count, should_abstain, coerced_count = _base_model(
        arm, target, source_contexts, source_streams, selected, prior_episodes, current_stream, prefix
    )
    exact = _exact_vectors_for_phase(target, phase)
    metrics = _abstain_metrics() if should_abstain else _metrics_bank(
        _consequence_vector_dynamic(CASE, model), exact, queries=QUERIES
    )
    if not should_abstain:
        for row in metrics.values():
            row["abstain"] = False
    current_fit = sum(min(prefix, len(current_stream[operator])) for operator in OPERATORS)
    prior_fit = sum(min(TARGET_FIT, len(rows[operator])) for _phase, rows in prior_episodes for operator in OPERATORS)
    support_seen = {operator: sorted(set(current_stream[operator][:prefix])) for operator in OPERATORS}
    model_support = {operator: sorted(model[operator]) for operator in OPERATORS}
    audit_new_rows = sum(category == NEW_SUCCESSOR for category in current_stream["RECOVERY_RETRY"][TARGET_FIT:])
    unsupported_audit_rows = audit_new_rows if NEW_SUCCESSOR not in model_support["RECOVERY_RETRY"] else 0
    return {
        "target": target.as_dict(),
        "phase": phase,
        "prefix_per_operator": prefix,
        "target_audit_per_operator": TARGET_AUDIT,
        "support_seen": support_seen,
        "new_successor_discovered": NEW_SUCCESSOR in support_seen["RECOVERY_RETRY"],
        "model_support": model_support,
        "audit_new_successor_rows": audit_new_rows,
        "unsupported_audit_rows": unsupported_audit_rows,
        "support_recall": audit_new_rows == 0 or NEW_SUCCESSOR in model_support["RECOVERY_RETRY"],
        "unknown_outcome_count": unknown_count,
        "coerced_unknown_count": coerced_count,
        "abstain": should_abstain,
        "source_fit_observations_used": 0 if arm == "RESET_DYNAMIC" else len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
        "prior_fit_observations_used": prior_fit if arm == "CONTINUAL_FACTOR_EXPANDING" else (prior_fit if arm == "LEGACY_COERCE" else 0),
        "current_fit_observations_used": current_fit if arm != "FROZEN_STATIC" else 0,
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
        for target_index, target in enumerate(target_contexts):
            phase_rows = {
                phase: _stream_for_phase(target, _stream_seed(seed, target_index, phase_index), phase)
                for phase_index, phase in enumerate(PHASES)
            }
            prior_episodes: list[tuple[str, dict[str, list[str]]]] = []
            for phase in PHASES:
                current_stream = phase_rows[phase]
                for prefix in TARGET_PREFIXES:
                    for arm in ARMS:
                        target_records[arm].append(_target_record(
                            arm, phase, target, prefix, source_contexts, source_streams,
                            selected["selected_fields"], prior_episodes, current_stream,
                        ))
                prior_episodes.append((phase, current_stream))
        records.append({
            "seed": seed,
            "selected": selected,
            "source_contexts": [context.as_dict() for context in source_contexts],
            "target_contexts": [context.as_dict() for context in target_contexts],
            "phase_order": list(PHASES),
            "stream_seeds": {
                target.context_id: {
                    phase: _stream_seed(seed, target_index, phase_index)
                    for phase_index, phase in enumerate(PHASES)
                }
                for target_index, target in enumerate(target_contexts)
            },
            "arms": target_records,
        })

    summary: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in ARMS:
        summary[arm] = {}
        for phase in PHASES:
            summary[arm][phase] = {}
            for prefix in TARGET_PREFIXES:
                bucket: dict[str, Any] = {
                    "policy_correct_counts": [], "set_action_agreement_counts": [],
                    "abstain_counts": [], "unknown_outcome_counts": [],
                    "coerced_unknown_counts": [], "exact_regrets": [],
                    "support_discovery_counts": [],
                    "support_recall_counts": [], "unsupported_audit_counts": [],
                    "denominator_per_seed": len(target_contexts) * len(QUERIES),
                }
                for record in records:
                    rows = [row for row in record["arms"][arm]
                            if row["phase"] == phase and row["prefix_per_operator"] == prefix]
                    metrics = [item for row in rows for item in row["metrics"].values()]
                    bucket["policy_correct_counts"].append(sum(item["policy_correct"] for item in metrics))
                    bucket["set_action_agreement_counts"].append(sum(item["set_action_agreement"] for item in metrics))
                    bucket["abstain_counts"].append(sum(item["abstain"] for item in metrics))
                    bucket["unknown_outcome_counts"].append(sum(row["unknown_outcome_count"] for row in rows))
                    bucket["coerced_unknown_counts"].append(sum(row["coerced_unknown_count"] for row in rows))
                    bucket["support_discovery_counts"].append(sum(row["new_successor_discovered"] for row in rows))
                    bucket["support_recall_counts"].append(sum(row["support_recall"] for row in rows))
                    bucket["unsupported_audit_counts"].append(sum(row["unsupported_audit_rows"] for row in rows))
                    valid = [F(item["exact_value_regret"]) for item in metrics if item["exact_value_regret"] is not None]
                    bucket["exact_regrets"].append(str(sum(valid, F(0))))
                bucket["mean_policy_correct"] = sum(bucket["policy_correct_counts"]) / len(records)
                bucket["mean_set_action_agreement"] = sum(bucket["set_action_agreement_counts"]) / len(records)
                bucket["mean_abstains"] = sum(bucket["abstain_counts"]) / len(records)
                bucket["mean_unknown_outcomes"] = sum(bucket["unknown_outcome_counts"]) / len(records)
                bucket["mean_coerced_unknowns"] = sum(bucket["coerced_unknown_counts"]) / len(records)
                bucket["mean_support_discoveries"] = sum(bucket["support_discovery_counts"]) / len(records)
                bucket["mean_support_recall"] = sum(bucket["support_recall_counts"]) / len(records)
                bucket["mean_unsupported_audit_rows"] = sum(bucket["unsupported_audit_counts"]) / len(records)
                bucket["mean_exact_regret"] = str(sum((F(value) for value in bucket["exact_regrets"]), F(0)) / len(records))
                summary[arm][phase][str(prefix)] = bucket

    return {
        "schema": "acfqp.crossed_factor_support_continual.v274",
        "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "settings": {
            "seeds": list(SEEDS), "source_pairs": SOURCE_PAIRS, "target_pairs": TARGET_PAIRS,
            "phase_order": PHASES, "target_prefixes": TARGET_PREFIXES,
            "samples_per_operator": SAMPLES_PER_OPERATOR, "source_fit": SOURCE_FIT,
            "source_audit": SOURCE_AUDIT, "target_fit": TARGET_FIT, "target_audit": TARGET_AUDIT,
            "candidate_subsets": CANDIDATE_SUBSETS, "visible_features": FEATURES,
            "dynamics_changed": True, "query_changed": False,
            "support_changed_phase": "B", "new_successor": NEW_SUCCESSOR,
            "b_delayed_probability": str(B_DELAYED_PROBABILITY), "delayed_cost": str(DELAYED_COST),
            "old_support": OLD_SUPPORT, "arms": ARMS,
        },
        "records": records, "summary": summary,
        "limitations": [
            "This is a synthetic successor-support continuation of V270-V273, not the original Gate.",
            "DELAYED is predeclared as a failure with an additional cost; this semantic is fixed before scoring.",
            "Unknown-category handling is reported separately from ordinary regret.",
            "Source and target row costs are reported separately; RESET_DYNAMIC is not a total-cost comparison.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("_")]
