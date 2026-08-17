from __future__ import annotations

import inspect

import pytest

from acfqp import generic_universal_mixture_mdl_synthesizer_v13 as universal


def test_v13_public_signature_removes_bet_and_epoch_base_but_reports_legacy_credit():
    parameters = inspect.signature(
        universal.universal_mixture_mdl_predictive_stop_update_v13
    ).parameters
    assert "success_evalue_multiplier_numerator" not in parameters
    assert "success_evalue_multiplier_denominator" not in parameters
    assert "epoch_alpha_spending_base" not in parameters
    assert "predictive_evidence_credit_units_per_bit" in parameters
    assert "global_alpha_denominator" in parameters


@pytest.mark.parametrize(
    ("epoch", "successes", "numerator", "denominator", "threshold"),
    (
        (0, 0, 1, 1, 40),
        (0, 9, 1_023, 10, 40),
        (1, 11, 4_095, 12, 120),
        (2, 13, 16_383, 14, 240),
    ),
)
def test_v13_closed_form_universal_evalue_and_telescoping_threshold(
    monkeypatch, epoch, successes, numerator, denominator, threshold
):
    monkeypatch.setattr(
        universal,
        "mdl_confidence_stop_update_v11",
        lambda *_args, **_kwargs: {
            "confidence_margin_units": 0,
            "current_candidate_replay_disagreement_count": 0,
        },
    )
    result = universal.universal_mixture_mdl_predictive_stop_update_v13(
        object(),
        (),
        (),
        factor_prior_enabled=True,
        invalidated_candidate_count=0,
        candidate_program_disagreement_count=0,
        candidate_epoch=epoch,
        post_issuance_exact_prediction_success_count=successes,
        factor_signature_credit_units=16,
        invalidated_candidate_penalty_units=16,
        minimum_reusable_factor_count=3,
        global_alpha_denominator=20,
        predictive_evidence_credit_units_per_bit=2,
    )
    assert result["universal_mixture_evalue_numerator"] == numerator
    assert result["universal_mixture_evalue_denominator"] == denominator
    assert result["evalue_threshold"] == threshold
    assert result["betting_fraction_selected"] is False
    assert result["success_evalue_multiplier_selected"] is False
    assert result["epoch_spending_base_selected"] is False
    assert result["predictive_evidence_to_mdl_credit_selected"] is True
    assert result["predictive_evidence_to_mdl_credit_inherited_from_v57"] is True
    assert result["reachable_frontier_exhaustion_input_consumed"] is False


def test_v13_rejects_invalid_statistical_contract(monkeypatch):
    monkeypatch.setattr(
        universal, "mdl_confidence_stop_update_v11", lambda *_a, **_k: {}
    )
    with pytest.raises(ValueError):
        universal.universal_mixture_mdl_predictive_stop_update_v13(
            object(),
            (),
            (),
            factor_prior_enabled=False,
            invalidated_candidate_count=0,
            candidate_program_disagreement_count=0,
            candidate_epoch=-1,
            post_issuance_exact_prediction_success_count=0,
            factor_signature_credit_units=16,
            invalidated_candidate_penalty_units=16,
            minimum_reusable_factor_count=3,
            global_alpha_denominator=20,
            predictive_evidence_credit_units_per_bit=2,
        )
