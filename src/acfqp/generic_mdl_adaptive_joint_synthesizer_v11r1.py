"""Exact-frontier closure successor for the V11 MDL stop update."""

from __future__ import annotations

from typing import Any

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    MDLAdaptiveJointCandidateV11,
    mdl_confidence_stop_update_v11,
)


def mdl_confidence_or_exact_frontier_stop_update_v11r1(
    candidate: MDLAdaptiveJointCandidateV11,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    factor_prior_enabled: bool,
    invalidated_candidate_count: int,
    candidate_program_disagreement_count: int,
    factor_signature_credit_units: int,
    confidence_reserve_units: int,
    invalidated_candidate_penalty_units: int,
    minimum_reusable_factor_count: int,
    witness_blind_reachable_frontier_exhausted: bool,
) -> dict[str, Any]:
    base = mdl_confidence_stop_update_v11(
        candidate,
        rows,
        catalogue,
        factor_prior_enabled=factor_prior_enabled,
        invalidated_candidate_count=invalidated_candidate_count,
        candidate_program_disagreement_count=candidate_program_disagreement_count,
        factor_signature_credit_units=factor_signature_credit_units,
        confidence_reserve_units=confidence_reserve_units,
        invalidated_candidate_penalty_units=invalidated_candidate_penalty_units,
        minimum_reusable_factor_count=minimum_reusable_factor_count,
    )
    exact_frontier_closure = (
        witness_blind_reachable_frontier_exhausted
        and base["current_candidate_replay_disagreement_count"] == 0
        and base["unresolved_frontier_disagreement_units"] == 0
    )
    return {
        **base,
        "schema": "acfqp.generic_mdl_confidence_stop_update.v11r1",
        "witness_blind_reachable_frontier_exhausted": (
            witness_blind_reachable_frontier_exhausted
        ),
        "exact_reachable_frontier_closure_stop": exact_frontier_closure,
        "stopped_by_mdl_confidence_margin": base["stopped"],
        "stopped": base["stopped"] or exact_frontier_closure,
        "same_frontier_closure_rule_in_both_arms": True,
        "successor_change_from_v11": (
            "ALLOW_EXACT_REACHABLE_FRONTIER_CLOSURE_WHEN_MDL_MARGIN_IS_NEGATIVE"
        ),
    }


__all__ = ("mdl_confidence_or_exact_frontier_stop_update_v11r1",)
