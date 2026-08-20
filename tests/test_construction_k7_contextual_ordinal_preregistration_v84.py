import pytest

from acfqp.construction_k7_contextual_ordinal_preregistration_v84 import (
    ConstructionK7ContextualOrdinalPreregistrationV84Error,
    SOURCE_POOL_SEEDS,
    freeze_contextual_ordinal_preregistration_v84,
    verify_contextual_ordinal_preregistration_v84,
)


def test_v84_preregistration_is_outcome_free_and_fixes_all_sources():
    document = freeze_contextual_ordinal_preregistration_v84().to_document()
    assert list(SOURCE_POOL_SEEDS) == document["identity_contract"]["source_pool_seeds"]
    assert len(SOURCE_POOL_SEEDS) == 6
    assert document["source_closure"]["frozen_before_any_registered_v84_source_outcome"] is True
    assert document["construction_contract"]["context_action_supports_derived_from_catalogues_not_outcomes"] is True
    assert document["construction_contract"]["context_local_action_field_ordinal_operator_registered"] is True
    assert document["registered_gate"]["minimum_compiled_model_count"] == 1
    assert document["registered_gate"]["minimum_compiled_source_member_count"] == 2
    assert document["claim_boundary"]["fresh_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v84_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7ContextualOrdinalPreregistrationV84Error):
        verify_contextual_ordinal_preregistration_v84(object())
