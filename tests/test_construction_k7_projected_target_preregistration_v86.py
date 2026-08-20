import pytest

from acfqp.construction_k7_projected_target_preregistration_v86 import (
    ConstructionK7ProjectedTargetPreregistrationV86Error,
    TARGET_SEEDS,
    freeze_projected_target_preregistration_v86,
    verify_projected_target_preregistration_v86,
)


def test_v86_preregistration_fixes_fresh_targets_and_matched_gate():
    document = freeze_projected_target_preregistration_v86().to_document()
    assert list(TARGET_SEEDS) == document["identity_contract"]["target_seeds"]
    assert len(TARGET_SEEDS) == 6
    assert document["source_closure"]["frozen_before_any_registered_v86_target_outcome"] is True
    contract = document["construction_contract"]
    assert contract["same_exact_certificate_engine_in_both_arms"] is True
    assert contract["every_ground_query_must_follow_failed_certificate"] is True
    assert document["registered_gate"]["target_sample_reduction_required"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v86_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7ProjectedTargetPreregistrationV86Error):
        verify_projected_target_preregistration_v86(object())
