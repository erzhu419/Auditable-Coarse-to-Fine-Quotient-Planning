from __future__ import annotations

import dataclasses

import pytest

from acfqp.construction_k7_joint_factor_residual_preregistration_v54 import (
    JointFactorResidualPreregistrationV54,
    campaign_config_v54,
    freeze_joint_factor_residual_preregistration_v54,
    verify_joint_factor_residual_preregistration_v54,
)


def test_v54_preregistration_is_outcome_free_and_forbids_target_scaffolds():
    value = verify_joint_factor_residual_preregistration_v54(
        freeze_joint_factor_residual_preregistration_v54()
    )
    document = value.to_document()
    assert document["fresh_v54_registered_outcome_execution_performed"] is False
    assert document["source_closure"]["frozen_before_any_v54_registered_outcome"] is True
    forbidden = document["joint_discovery_contract"]["forbidden_constructor_inputs"]
    assert "V51_TARGET_PROGRAM" in forbidden
    assert "V51_SHARED_RESIDUAL_SCAFFOLD" in forbidden
    assert "V51_REUSED_FACTOR_SUBPROGRAM_SLOTS" in forbidden
    assert document["claim_boundary"]["registered_outcome_observed"] is False


def test_v54_registered_and_development_identities_are_disjoint_and_gates_locked():
    document = freeze_joint_factor_residual_preregistration_v54().to_document()
    assert document["source_closure"]["development_seed_identities_disjoint_from_registered_identities"] is True
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["official_N_break_even"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["claim_boundary"]["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    config = campaign_config_v54()
    assert len(config["source_seeds"]) == 3
    assert len(config["target_seeds"]) == 8


def test_v54_preregistration_rejects_foreign_or_copied_values():
    value = freeze_joint_factor_residual_preregistration_v54()
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.preregistration_id = "f" * 64
    with pytest.raises(Exception):
        JointFactorResidualPreregistrationV54(
            object(), value.canonical_bytes, value.preregistration_id
        )
    with pytest.raises(Exception):
        verify_joint_factor_residual_preregistration_v54(object())
