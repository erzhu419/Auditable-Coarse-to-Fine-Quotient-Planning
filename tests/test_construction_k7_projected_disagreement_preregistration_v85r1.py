import pytest

from acfqp.construction_k7_projected_disagreement_preregistration_v85r1 import (
    ConstructionK7ProjectedDisagreementPreregistrationV85R1Error,
    SOURCE_POOL_SEEDS,
    freeze_projected_disagreement_preregistration_v85r1,
    verify_projected_disagreement_preregistration_v85r1,
)


def test_v85r1_preregistration_is_outcome_free_and_self_contained():
    document = freeze_projected_disagreement_preregistration_v85r1().to_document()
    assert list(SOURCE_POOL_SEEDS) == document["identity_contract"]["source_pool_seeds"]
    assert len(SOURCE_POOL_SEEDS) == 6
    contract = document["failure_driven_successor_contract"]
    assert contract["v85_pre_outcome_failure_preserved"] is True
    assert contract["historical_v70_producer_dereference_forbidden"] is True
    assert contract["self_contained_template_bytes_bound_before_outcomes"] is True
    assert document["registered_gate"]["minimum_compiled_source_member_count"] == 2
    assert document["claim_boundary"]["fresh_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v85r1_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7ProjectedDisagreementPreregistrationV85R1Error):
        verify_projected_disagreement_preregistration_v85r1(object())
