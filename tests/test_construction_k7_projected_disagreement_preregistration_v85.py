import pytest

from acfqp.construction_k7_projected_disagreement_preregistration_v85 import (
    ConstructionK7ProjectedDisagreementPreregistrationV85Error,
    SOURCE_POOL_SEEDS,
    freeze_projected_disagreement_preregistration_v85,
    verify_projected_disagreement_preregistration_v85,
)


def test_v85_preregistration_is_outcome_free_and_fixes_all_sources():
    document = freeze_projected_disagreement_preregistration_v85().to_document()
    assert list(SOURCE_POOL_SEEDS) == document["identity_contract"]["source_pool_seeds"]
    assert len(SOURCE_POOL_SEEDS) == 6
    assert document["failure_driven_successor_contract"]["no_outcome_executed_under_withdrawn_preregistration"] is True
    assert document["source_closure"]["frozen_before_any_registered_v85_source_outcome"] is True
    contract = document["failure_driven_successor_contract"]
    assert contract["query_selection_uses_only_pre_state_action_and_model_projections"] is True
    assert contract["unacquired_post_state_or_label_access_for_query_selection"] is False
    assert document["registered_gate"]["minimum_compiled_model_count"] == 1
    assert document["registered_gate"]["minimum_compiled_source_member_count"] == 2
    assert document["claim_boundary"]["fresh_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v85_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7ProjectedDisagreementPreregistrationV85Error):
        verify_projected_disagreement_preregistration_v85(object())
