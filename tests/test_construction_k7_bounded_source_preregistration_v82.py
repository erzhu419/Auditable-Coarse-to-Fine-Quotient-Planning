import pytest

from acfqp.construction_k7_bounded_source_preregistration_v82 import (
    ConstructionK7BoundedSourcePreregistrationV82Error,
    SOURCE_POOL_SEEDS,
    freeze_bounded_source_preregistration_v82,
    verify_bounded_source_preregistration_v82,
)


def test_v82_preregisters_all_six_sources_before_outcomes():
    value = verify_bounded_source_preregistration_v82(
        freeze_bounded_source_preregistration_v82()
    )
    document = value.to_document()
    assert tuple(document["identity_contract"]["source_pool_seeds"]) == (
        SOURCE_POOL_SEEDS
    )
    assert len(SOURCE_POOL_SEEDS) == 6
    assert document["identity_contract"]["fresh_target_identities_registered"] == []
    assert document["failure_driven_successor_contract"][
        "blind_seed_substitution_or_posthoc_selection_used"
    ] is False
    assert document["construction_contract"][
        "nonempty_residual_version_space_used_as_readiness_gate"
    ] is True
    assert document["construction_contract"][
        "residual_successor_consensus_used_before_issuance"
    ] is False
    assert document["resource_schedule"]["maximum_simultaneous_worker_count"] == 2
    assert document["claim_boundary"]["sample_tax_reduction_verified"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["fresh_registered_v82_execution_performed"] is False


def test_v82_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7BoundedSourcePreregistrationV82Error):
        verify_bounded_source_preregistration_v82(object())
