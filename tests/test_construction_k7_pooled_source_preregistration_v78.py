import pytest

from acfqp.construction_k7_pooled_source_preregistration_v78 import (
    ConstructionK7PooledSourcePreregistrationV78Error,
    SOURCE_FAMILY,
    SOURCE_POOL_SEEDS,
    freeze_pooled_source_preregistration_v78,
    verify_pooled_source_preregistration_v78,
)


def test_v78_preregisters_source_only_pool_before_outcomes():
    value = verify_pooled_source_preregistration_v78(
        freeze_pooled_source_preregistration_v78()
    )
    document = value.to_document()
    assert SOURCE_FAMILY == "BALANCED_BATCH_REFINEMENT"
    assert tuple(document["identity_contract"]["source_pool_seeds"]) == (
        SOURCE_POOL_SEEDS
    )
    assert document["identity_contract"]["fresh_target_identities_registered"] == []
    assert document["construction_contract"]["target_outcome_used_by_pooling_or_acquisition"] is False
    assert document["registered_gate"]["target_execution_forbidden_in_this_slice"] is True
    assert document["claim_boundary"]["sample_tax_reduction_verified"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["fresh_registered_v78_execution_performed"] is False


def test_v78_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7PooledSourcePreregistrationV78Error):
        verify_pooled_source_preregistration_v78(object())
