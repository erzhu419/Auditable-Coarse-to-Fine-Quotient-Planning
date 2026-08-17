"""Anytime-valid predictive-evidence successor to the V11 MDL stop.

Each complete candidate is frozen before the next support batch.  Its exact
prediction of that unseen batch is one Bernoulli success.  Under the registered
null that such a prediction succeeds with conditional probability at most 1/2,
the success factor 3/2 and failure factor 1/2 form an e-process.  Candidate epoch
``j`` receives alpha ``1 / (20 * 2 ** (j + 1))``; the geometric allocation sums
to 1/20.  There is no label floor, confirmation block, fixed confidence reserve,
or reachable-frontier input.

The stop requires exact current replay, the epoch e-value threshold, and a
nonnegative combined MDL plus conservative log2 e-value-surplus margin.  This
is an anytime-valid test of the registered predictive null, not a universal
confidence interval for arbitrary dynamics.
"""

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


def calibrated_mdl_predictive_stop_update_v12(
    candidate: MDLAdaptiveJointCandidateV11,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    factor_prior_enabled: bool,
    invalidated_candidate_count: int,
    candidate_program_disagreement_count: int,
    candidate_epoch: int,
    post_issuance_exact_prediction_success_count: int,
    factor_signature_credit_units: int,
    invalidated_candidate_penalty_units: int,
    minimum_reusable_factor_count: int,
    global_alpha_denominator: int,
    epoch_alpha_spending_base: int,
    success_evalue_multiplier_numerator: int,
    success_evalue_multiplier_denominator: int,
    predictive_evidence_credit_units_per_bit: int,
) -> dict[str, Any]:
    if (
        candidate_epoch < 0
        or post_issuance_exact_prediction_success_count < 0
        or global_alpha_denominator <= 1
        or epoch_alpha_spending_base != 2
        or success_evalue_multiplier_numerator != 3
        or success_evalue_multiplier_denominator != 2
        or predictive_evidence_credit_units_per_bit <= 0
    ):
        raise ValueError("V12 calibrated predictive stopping contract changed")
    base = mdl_confidence_stop_update_v11(
        candidate,
        rows,
        catalogue,
        factor_prior_enabled=factor_prior_enabled,
        invalidated_candidate_count=invalidated_candidate_count,
        candidate_program_disagreement_count=(
            candidate_program_disagreement_count
        ),
        factor_signature_credit_units=factor_signature_credit_units,
        confidence_reserve_units=1,
        invalidated_candidate_penalty_units=(
            invalidated_candidate_penalty_units
        ),
        minimum_reusable_factor_count=minimum_reusable_factor_count,
    )
    threshold = (
        global_alpha_denominator
        * epoch_alpha_spending_base ** (candidate_epoch + 1)
    )
    evalue_numerator = success_evalue_multiplier_numerator ** (
        post_issuance_exact_prediction_success_count
    )
    evalue_denominator = success_evalue_multiplier_denominator ** (
        post_issuance_exact_prediction_success_count
    )
    threshold_denominator = threshold * evalue_denominator
    threshold_met = evalue_numerator >= threshold_denominator
    ratio_floor = evalue_numerator // threshold_denominator if threshold_met else 0
    surplus_bits = ratio_floor.bit_length() - 1 if ratio_floor else 0
    mdl_margin_without_fixed_reserve = base["confidence_margin_units"] + 1
    combined_margin = (
        mdl_margin_without_fixed_reserve
        + surplus_bits * predictive_evidence_credit_units_per_bit
    )
    stopped = (
        base["current_candidate_replay_disagreement_count"] == 0
        and threshold_met
        and combined_margin >= 0
    )
    return {
        **base,
        "schema": "acfqp.generic_calibrated_mdl_predictive_stop_update.v12",
        "candidate_epoch": candidate_epoch,
        "post_issuance_exact_prediction_success_count": (
            post_issuance_exact_prediction_success_count
        ),
        "predictive_null_success_probability_upper_bound": {
            "numerator": 1,
            "denominator": 2,
        },
        "success_evalue_multiplier": {
            "numerator": success_evalue_multiplier_numerator,
            "denominator": success_evalue_multiplier_denominator,
        },
        "failure_evalue_multiplier": {"numerator": 1, "denominator": 2},
        "global_alpha": {"numerator": 1, "denominator": global_alpha_denominator},
        "epoch_alpha_spending_weight": {
            "numerator": 1,
            "denominator": epoch_alpha_spending_base ** (candidate_epoch + 1),
        },
        "evalue_numerator": evalue_numerator,
        "evalue_denominator": evalue_denominator,
        "evalue_threshold": threshold,
        "calibrated_evalue_threshold_met": threshold_met,
        "conservative_log2_evalue_surplus_bits": surplus_bits,
        "mdl_margin_without_fixed_confidence_reserve": (
            mdl_margin_without_fixed_reserve
        ),
        "predictive_evidence_credit_units_per_bit": (
            predictive_evidence_credit_units_per_bit
        ),
        "combined_mdl_predictive_margin_units": combined_margin,
        "fixed_confidence_reserve_consumed": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "anytime_valid_for_registered_predictive_null": True,
        "distribution_free_global_dynamics_confidence_claimed": False,
        "stopped": stopped,
        "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
    }


__all__ = ("calibrated_mdl_predictive_stop_update_v12",)
