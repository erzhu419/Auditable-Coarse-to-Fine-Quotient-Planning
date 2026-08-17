from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_factor_prior_single_switch_preregistration_v53 as pre


def test_v53_preregistration_is_frozen_and_content_addressed() -> None:
    frozen = pre.freeze_factor_prior_single_switch_preregistration_v53()
    assert pre.verify_factor_prior_single_switch_preregistration_v53(frozen) is frozen
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256


def test_v53_preregisters_only_one_arm_switch() -> None:
    document = pre.freeze_factor_prior_single_switch_preregistration_v53().to_document()
    matched = document["matched_single_switch_arms"]
    assert matched["same_finite_anonymous_candidate_grammar"] is True
    assert matched["same_witness_blind_bfs_query_schedule"] is True
    assert matched["same_exact_zero_one_likelihood"] is True
    assert matched["same_shared_residual_scaffold"] is True
    assert matched["factor_prior_on_multiplier"] == 64
    assert matched["factor_prior_off_multiplier"] == 1
    assert matched["only_switched_variable"] == "CROSS_SCHEMA_FACTOR_SIGNATURE_PRIOR_INITIAL_WEIGHT"


def test_v53_preregisters_conservative_sample_tax_and_validation_subset() -> None:
    document = pre.freeze_factor_prior_single_switch_preregistration_v53().to_document()
    tax = document["sample_tax_contract"]
    assert tax["shared_residual_scaffold_labels_charged_to_each_arm"] == 213
    assert tax["historical_factor_library_labels_charged_only_to_prior_on"] == 370
    assert tax["registered_acquisition_occurrence_count"] == 1_024
    assert document["target_domain"]["planning_validation_seed_count"] == 16
    assert set(pre.DEVELOPMENT_SEEDS).isdisjoint(pre.TARGET_SEEDS)


def test_v53_preregistration_is_outcome_free_and_gates_locked() -> None:
    document = pre.freeze_factor_prior_single_switch_preregistration_v53().to_document()
    assert document["fresh_v53_registered_outcome_execution_performed"] is False
    claims = document["claim_boundary"]
    assert claims["registered_outcome_observed"] is False
    assert claims["official_execution_allowed"] is False
    assert claims["official_scalar_cost"] is None
    assert claims["official_N_break_even"] is None
    assert claims["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert claims["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v53_preregistration_rejects_mutation() -> None:
    frozen = pre.freeze_factor_prior_single_switch_preregistration_v53()
    with pytest.raises(pre.ConstructionK7FactorPriorSingleSwitchPreregistrationV53Error):
        pre.FactorPriorSingleSwitchPreregistrationV53(
            object(), frozen.canonical_bytes, frozen.preregistration_id
        )
    object.__setattr__(frozen, "canonical_bytes", frozen.canonical_bytes + b" ")
    with pytest.raises(ValueError):
        pre.verify_factor_prior_single_switch_preregistration_v53(frozen)
