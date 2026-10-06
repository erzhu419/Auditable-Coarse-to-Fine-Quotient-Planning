"""Continual A -> B -> A' diagnostic for an action-support structure change."""

from __future__ import annotations

from fractions import Fraction as F
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
    _model_for_arm,
    _stream_for_phase,
    _stream_seed,
)
from .crossed_factor_transfer_v270 import CANDIDATE_SUBSETS, CASE, FEATURES, select_factor_subsets
from .persistent_consequence_library_v263 import QUERIES, consequence_vector
from .mechanism_switch_task_v205 import OPERATORS


ACTION_MASKS = {
    "A": frozenset(("RETURN", "RETRY")),
    "B": frozenset(("RETURN",)),
    "A_prime": frozenset(("RETURN", "RETRY")),
}
BASE_ARMS = ("RESET", "FROZEN_FACTOR", "CONTINUAL_FACTOR")
ARMS = ("RESET_AWARE", "FROZEN_FACTOR_AWARE", "CONTINUAL_FACTOR_AWARE", "LEGACY_UNMASKED")
POLICY_TO_RECOVERY_ACTION = {"DETOUR_RETURN": "RETURN", "DETOUR_RETRY": "RETRY"}


def _law_for_phase(context: Any, phase: str) -> dict[str, dict[str, F]]:
    from .crossed_factor_transfer_v270 import _law
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    return {operator: dict(values) for operator, values in _law(context).items()}


def _stream_for_phase(context: Any, seed: int, phase: str) -> dict[str, list[str]]:
    from .persistent_consequence_library_v263 import _draw_rows
    return _draw_rows(_law_for_phase(context, phase), seed)


def _exact_vectors_for_phase(context: Any, phase: str) -> dict[str, tuple[F, F, F]]:
    return consequence_vector(CASE, _law_for_phase(context, phase))


def _observed_stream_for_phase(stream: dict[str, list[str]], phase: str) -> dict[str, list[str]]:
    """Return only outcomes available from actions that remain enabled."""
    if phase == "B":
        return {operator: ([] if operator == "RECOVERY_RETRY" else list(rows))
                for operator, rows in stream.items()}
    return {operator: list(rows) for operator, rows in stream.items()}


def _legal_policies(vectors: dict[str, tuple[F, F, F]], mask: frozenset[str]) -> dict[str, tuple[F, F, F]]:
    return {
        policy: vector for policy, vector in vectors.items()
        if policy not in POLICY_TO_RECOVERY_ACTION or POLICY_TO_RECOVERY_ACTION[policy] in mask
    }


def _optimal_actions(vectors: dict[str, tuple[F, F, F]], weights: tuple[F, F, F]) -> frozenset[str]:
    def utility(vector: tuple[F, F, F]) -> F:
        reward, failure, success = vector
        return weights[0] * reward - weights[1] * failure + weights[2] * success
    values = {policy: utility(vector) for policy, vector in vectors.items()}
    optimum = max(values.values())
    return frozenset(policy for policy, value in values.items() if value == optimum)


def _masked_metrics(
    predicted: dict[str, tuple[F, F, F]],
    exact: dict[str, tuple[F, F, F]],
    phase: str,
    *,
    apply_mask: bool,
) -> dict[str, Any]:
    mask = ACTION_MASKS[phase]
    exact_legal = _legal_policies(exact, mask)
    predicted_legal = _legal_policies(predicted, mask) if apply_mask else predicted
    rows = {}
    for name, weights in QUERIES.items():
        predicted_set = _optimal_actions(predicted_legal, weights)
        exact_set = _optimal_actions(exact_legal, weights)
        predicted_policy = min(predicted_set)
        exact_policy = min(exact_set)
        invalid = (not apply_mask and predicted_policy not in exact_legal)
        if invalid:
            regret: str | None = None
        else:
            exact_value = weights[0] * exact[exact_policy][0] - weights[1] * exact[exact_policy][1] + weights[2] * exact[exact_policy][2]
            chosen_value = weights[0] * exact[predicted_policy][0] - weights[1] * exact[predicted_policy][1] + weights[2] * exact[predicted_policy][2]
            regret = str(exact_value - chosen_value)
        rows[name] = {
            "predicted_policy": predicted_policy,
            "exact_policy": exact_policy,
            "policy_correct": predicted_policy == exact_policy and not invalid,
            "predicted_optimal_actions": sorted(predicted_set),
            "exact_optimal_actions": sorted(exact_set),
            "set_action_agreement": predicted_set == exact_set and not invalid,
            "invalid_action": invalid,
            "exact_value_regret": regret,
        }
    return rows


def _base_arm(arm: str) -> str:
    if arm == "RESET_AWARE":
        return "RESET"
    if arm in ("FROZEN_FACTOR_AWARE", "LEGACY_UNMASKED"):
        return "FROZEN_FACTOR"
    if arm == "CONTINUAL_FACTOR_AWARE":
        return "CONTINUAL_FACTOR"
    raise ValueError(f"unknown arm: {arm}")


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
        _base_arm(arm), target, source_contexts, source_streams, selected,
        prior_episodes, current_stream, prefix,
    )
    metrics = _masked_metrics(
        consequence_vector(CASE, model), _exact_vectors_for_phase(target, phase), phase,
        apply_mask=arm != "LEGACY_UNMASKED",
    )
    current_available = sum(min(prefix, len(current_stream[operator])) for operator in OPERATORS)
    prior_available = sum(
        min(TARGET_FIT, len(rows[operator]))
        for _phase, rows in prior_episodes for operator in OPERATORS
    )
    observed_operators = [operator for operator in OPERATORS if current_stream[operator]]
    return {
        "target": target.as_dict(),
        "phase": phase,
        "prefix_per_operator": prefix,
        "available_recovery_actions": sorted(ACTION_MASKS[phase]),
        "mask_applied": arm != "LEGACY_UNMASKED",
        "potential_target_audit_per_operator": TARGET_AUDIT,
        "observed_operators": observed_operators,
        "observed_audit_observations": len(observed_operators) * TARGET_AUDIT,
        "source_fit_observations_used": 0 if _base_arm(arm) == "RESET" else len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
        "prior_fit_observations_used": prior_available if _base_arm(arm) == "CONTINUAL_FACTOR" else 0,
        "current_fit_observations_used": current_available if _base_arm(arm) != "FROZEN_FACTOR" else 0,
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
                phase: _stream_for_phase(target, _stream_seed(seed, target_index, phase_index), phase)
                for phase_index, phase in enumerate(PHASES)
            }
            stream_seeds[target.context_id] = {
                phase: _stream_seed(seed, target_index, phase_index)
                for phase_index, phase in enumerate(PHASES)
            }
            prior_episodes: list[tuple[str, dict[str, list[str]]]] = []
            for phase in PHASES:
                current_stream = _observed_stream_for_phase(phase_rows[phase], phase)
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
            "action_masks": {phase: sorted(mask) for phase, mask in ACTION_MASKS.items()},
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
                    "invalid_action_counts": [],
                    "valid_regret_counts": [],
                    "exact_regrets": [],
                    "denominator_per_seed": len(target_contexts) * len(QUERIES),
                }
                for record in records:
                    rows = [row for row in record["arms"][arm]
                            if row["phase"] == phase and row["prefix_per_operator"] == prefix]
                    metrics = [item for row in rows for item in row["metrics"].values()]
                    bucket["policy_correct_counts"].append(sum(item["policy_correct"] for item in metrics))
                    bucket["set_action_agreement_counts"].append(sum(item["set_action_agreement"] for item in metrics))
                    bucket["invalid_action_counts"].append(sum(item["invalid_action"] for item in metrics))
                    valid = [F(item["exact_value_regret"]) for item in metrics
                             if item["exact_value_regret"] is not None]
                    bucket["valid_regret_counts"].append(len(valid))
                    bucket["exact_regrets"].append(str(sum(valid, F(0))))
                bucket["mean_policy_correct"] = sum(bucket["policy_correct_counts"]) / len(records)
                bucket["mean_set_action_agreement"] = sum(bucket["set_action_agreement_counts"]) / len(records)
                bucket["mean_invalid_actions"] = sum(bucket["invalid_action_counts"]) / len(records)
                bucket["mean_valid_regret_count"] = sum(bucket["valid_regret_counts"]) / len(records)
                bucket["mean_exact_regret"] = str(sum((F(value) for value in bucket["exact_regrets"]), F(0)) / len(records))
                summary[arm][phase][str(prefix)] = bucket

    return {
        "schema": "acfqp.crossed_factor_structure_continual.v273",
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
            "potential_target_fit_observations_per_seed": len(target_contexts) * len(PHASES) * TARGET_FIT * len(OPERATORS),
            "acquired_target_fit_observations_per_seed": len(target_contexts) * TARGET_FIT * (2 + 3 + 3),
            "acquired_target_audit_observations_per_seed": len(target_contexts) * TARGET_AUDIT * (2 + 3 + 3),
            "candidate_subsets": CANDIDATE_SUBSETS,
            "visible_features": FEATURES,
            "dynamics_changed": False,
            "query_changed": False,
            "structure_changed_phase": "B",
            "structure_change": "RECOVERY_RETRY unavailable at RECOVERY",
            "action_masks": {phase: sorted(mask) for phase, mask in ACTION_MASKS.items()},
            "arms": ARMS,
        },
        "records": records,
        "summary": summary,
        "limitations": [
            "This is a synthetic action-support continuation of V270-V272, not the original Gate.",
            "The B structure change is action availability, not a new categorical successor or altered law.",
            "Invalid actions are reported separately and are not converted into ordinary regret.",
            "Source and target row costs are reported separately; RESET_AWARE is not a total-cost comparison.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("_")]
