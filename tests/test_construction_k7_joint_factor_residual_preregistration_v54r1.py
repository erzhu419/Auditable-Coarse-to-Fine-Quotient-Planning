import pytest

from acfqp.construction_k7_joint_factor_residual_preregistration_v54r1 import (
    JointFactorResidualPreregistrationV54R1,
    freeze_joint_factor_residual_preregistration_v54r1,
    verify_joint_factor_residual_preregistration_v54r1,
)


def test_v54r1_is_fresh_outcome_free_and_preserves_failed_v54():
    value = verify_joint_factor_residual_preregistration_v54r1(
        freeze_joint_factor_residual_preregistration_v54r1()
    )
    document = value.to_document()
    assert document["fresh_v54r1_registered_outcome_execution_performed"] is False
    assert document["frozen_predecessors"]["v54_same_identity_rerun_forbidden"] is True
    assert document["frozen_predecessors"]["v54_registered_failure_id"] == "f5dbecac001b91c3a460fe4f7d4559a45bef631640f881c29e6e484f95c8b785"
    assert document["source_closure"]["frozen_before_any_v54r1_registered_outcome"] is True


def test_v54r1_repair_and_joint_discovery_are_frozen_without_claim_upgrade():
    document = freeze_joint_factor_residual_preregistration_v54r1().to_document()
    assert document["repair_contract"]["development_unique_layout_matches"] == 64
    assert document["repair_contract"]["development_maximum_layout_labels"] == 76
    assert document["joint_discovery_contract"]["v51_target_program_consumed"] is False
    assert document["joint_discovery_contract"]["shared_residual_scaffold_consumed"] is False
    assert document["joint_discovery_contract"]["predeclared_reusable_factor_slots_consumed"] is False
    assert document["claim_boundary"]["registered_outcome_observed"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["official_N_break_even"] is None


def test_v54r1_preregistration_rejects_foreign_values():
    value = freeze_joint_factor_residual_preregistration_v54r1()
    with pytest.raises(Exception):
        JointFactorResidualPreregistrationV54R1(
            object(), value.canonical_bytes, value.preregistration_id
        )
    with pytest.raises(Exception):
        verify_joint_factor_residual_preregistration_v54r1(object())
