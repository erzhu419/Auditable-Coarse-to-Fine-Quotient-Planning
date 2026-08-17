"""Parameter-free betting successor to the V57 predictive stop.

For one frozen candidate epoch, let a success mean exact prediction of the next
previously unseen support batch.  Under the composite registered null that the
conditional success probability is at most one half, every fixed alternative
``p in (1/2, 1]`` supplies a test supermartingale.  Uniformly mixing those
alternatives gives, after ``n`` consecutive successes and before the first
failure, the exact e-value

    (2 ** (n + 1) - 1) / (n + 1).

Thus no betting fraction or success multiplier is selected.  Candidate epoch
``j`` receives the canonical telescoping alpha
weight ``1 / ((j + 1) * (j + 2))``.  The weights sum to one, without a spending
base.  This bounded successor deliberately retains V57's explicit conversion
between conservative log2 e-value surplus bits and the predecessor's heuristic
MDL units.  Removing that final conversion requires replacing those units with
a genuine bit codelength; the retained conversion is reported, not hidden.

The only retained policy input is the global error level.  The result is
anytime-valid for the stated predictive null, not a distribution-free global
dynamics confidence interval.
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


def universal_mixture_mdl_predictive_stop_update_v13(
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
    predictive_evidence_credit_units_per_bit: int,
) -> dict[str, Any]:
    if (
        candidate_epoch < 0
        or post_issuance_exact_prediction_success_count < 0
        or global_alpha_denominator <= 1
        or predictive_evidence_credit_units_per_bit <= 0
    ):
        raise ValueError("V13 universal-mixture predictive contract changed")
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
    successes = post_issuance_exact_prediction_success_count
    evalue_numerator = 2 ** (successes + 1) - 1
    evalue_denominator = successes + 1
    epoch_weight_denominator = (candidate_epoch + 1) * (candidate_epoch + 2)
    evalue_threshold = global_alpha_denominator * epoch_weight_denominator
    threshold_met = (
        evalue_numerator >= evalue_denominator * evalue_threshold
    )
    threshold_denominator = evalue_denominator * evalue_threshold
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
        "schema": "acfqp.generic_universal_mixture_mdl_stop_update.v13",
        "candidate_epoch": candidate_epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "predictive_null_success_probability_upper_bound": {
            "numerator": 1,
            "denominator": 2,
        },
        "alternative_success_probability_mixture": "UNIFORM_OPEN_HALF_TO_ONE",
        "universal_mixture_evalue_numerator": evalue_numerator,
        "universal_mixture_evalue_denominator": evalue_denominator,
        "global_alpha": {"numerator": 1, "denominator": global_alpha_denominator},
        "epoch_alpha_spending_weight": {
            "numerator": 1,
            "denominator": epoch_weight_denominator,
        },
        "evalue_threshold": evalue_threshold,
        "universal_mixture_evalue_threshold_met": threshold_met,
        "conservative_log2_evalue_surplus_bits": surplus_bits,
        "mdl_margin_without_fixed_confidence_reserve": (
            mdl_margin_without_fixed_reserve
        ),
        "predictive_evidence_credit_units_per_bit": (
            predictive_evidence_credit_units_per_bit
        ),
        "combined_mdl_predictive_margin_units": combined_margin,
        "betting_fraction_selected": False,
        "success_evalue_multiplier_selected": False,
        "epoch_spending_base_selected": False,
        "predictive_evidence_to_mdl_credit_selected": True,
        "predictive_evidence_to_mdl_credit_inherited_from_v57": True,
        "fixed_confidence_reserve_consumed": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "anytime_valid_for_registered_predictive_null": True,
        "distribution_free_global_dynamics_confidence_claimed": False,
        "stopped": stopped,
        "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
    }


__all__ = ("universal_mixture_mdl_predictive_stop_update_v13",)
