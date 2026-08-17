import pytest

from acfqp.construction_k7_adaptive_joint_preregistration_v55 import (
    AdaptiveJointPreregistrationV55,
    freeze_adaptive_joint_preregistration_v55,
    verify_adaptive_joint_preregistration_v55,
)


def test_v55_is_outcome_free_and_removes_full_frontier_calibration():
    value = verify_adaptive_joint_preregistration_v55(
        freeze_adaptive_joint_preregistration_v55()
    )
    document = value.to_document()
    assert document["fresh_v55_registered_outcome_execution_performed"] is False
    assert document["source_closure"][
        "frozen_before_any_v55_registered_outcome"
    ] is True
    assert document["adaptive_joint_contract"][
        "full_frontier_target_layout_calibration_forbidden"
    ] is True
    assert document["adaptive_joint_contract"][
        "shared_residual_scaffold_consumed"
    ] is False
    assert document["adaptive_joint_contract"][
        "predeclared_reusable_factor_slots_consumed"
    ] is False


def test_v55_freezes_one_prior_switch_and_positive_lifetime_horizon():
    document = freeze_adaptive_joint_preregistration_v55().to_document()
    arms = document["matched_single_switch_arms"]
    assert arms["same_complete_program_synthesizer"] is True
    assert arms["same_raw_query_order"] is True
    assert arms["same_exact_replay_likelihood"] is True
    assert arms["only_switched_variable"] == (
        "ANONYMOUS_FACTOR_SIGNATURE_INITIAL_WEIGHT"
    )
    sample = document["sample_tax_contract"]
    assert sample["registered_acquisition_occurrence_count"] == 128
    assert sample[
        "minimum_savings_exceeds_historical_factor_library_tax"
    ] is True
    assert sample["official_break_even_claimed"] is False


def test_v55_freezes_certificate_first_recovery_validation_isolation_and_gates():
    document = freeze_adaptive_joint_preregistration_v55().to_document()
    assert document["planning_and_recovery"][
        "local_ground_query_before_certificate_failure_forbidden"
    ] is True
    assert document["isolated_validation_and_ood"][
        "validation_rows_consumed_for_acquisition_binding_or_planning"
    ] is False
    assert document["claim_boundary"]["global_exact_dynamics_claimed"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["official_N_break_even"] is None


def test_v55_preregistration_rejects_foreign_values():
    value = freeze_adaptive_joint_preregistration_v55()
    with pytest.raises(Exception):
        AdaptiveJointPreregistrationV55(
            object(), value.canonical_bytes, value.preregistration_id
        )
    with pytest.raises(Exception):
        verify_adaptive_joint_preregistration_v55(object())
