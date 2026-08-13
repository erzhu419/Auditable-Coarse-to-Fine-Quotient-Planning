from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as pre


def test_outcome_free_long_real_start_preregistration() -> None:
    value = pre.freeze_standard_2048_expression_long_preregistration_v23()
    assert pre.verify_standard_2048_expression_long_preregistration_v23(value) is value
    document = value.to_document()
    assert len(document["long_real_start_workload"]["initial_boards"]) == 4
    assert document["long_real_start_workload"]["maximum_decision_count"] == 128
    assert all(sum(rank != 0 for rank in board) == 2 for board in pre.INITIAL_BOARDS)
    freshness = document["long_real_start_workload"]["freshness_evidence"]
    assert freshness["target_orbits_pairwise_distinct"] is True
    assert freshness["target_orbits_disjoint_from_v11_v12_v13"] is True
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False


def test_v22_binding_and_exact_persistent_cache_are_frozen() -> None:
    document = pre.freeze_standard_2048_expression_long_preregistration_v23().to_document()
    predecessor = document["frozen_v22_predecessor"]
    assert predecessor["campaign_id"] == pre.V22_CAMPAIGN_ID
    assert predecessor["independent_verification_id"] == pre.V22_VERIFICATION_ID
    assert predecessor["world_model_immutable_during_long_workload"] is True
    protocol = document["persistent_proof_protocol"]
    assert protocol["one_bellman_subproof_cache_per_episode"] is True
    assert protocol["cache_reused_across_receding_horizon_decisions"] is True
    assert protocol["approximation_or_precision_reduction_allowed"] is False
    assert protocol["cold_evaluation_checkpoint_indices"] == [0, 15, 31]


def test_sample_tax_and_official_claims_are_bounded() -> None:
    document = pre.freeze_standard_2048_expression_long_preregistration_v23().to_document()
    tax = document["sample_tax_contract"]
    assert tax["inherited_target_probability_label_count"] == 4
    assert tax["additional_model_acquisition_label_budget"] == 0
    assert tax["strict_no_prior_context_label_count"] == 8
    assert tax["online_execution_transitions_reported_separately"] is True
    assert document["full_standard_2048_game_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_and_caller_mint_are_rejected() -> None:
    value = pre.freeze_standard_2048_expression_long_preregistration_v23()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7Standard2048ExpressionLongPreregistrationV23Error):
        pre.verify_standard_2048_expression_long_preregistration_v23(tampered)
    with pytest.raises(pre.ConstructionK7Standard2048ExpressionLongPreregistrationV23Error):
        pre.Standard2048ExpressionLongPreregistrationV23(
            object(), value.canonical_bytes, value.preregistration_id
        )
