import pytest

from acfqp.construction_k7_structural_route_preregistration_v80 import (
    ConstructionK7StructuralRoutePreregistrationV80Error,
    SOURCE_POOL_SEEDS,
    freeze_structural_route_preregistration_v80,
    verify_structural_route_preregistration_v80,
)


def test_v80_preregisters_structural_routing_before_outcomes():
    value = verify_structural_route_preregistration_v80(
        freeze_structural_route_preregistration_v80()
    )
    document = value.to_document()
    assert tuple(document["identity_contract"]["source_pool_seeds"]) == (
        SOURCE_POOL_SEEDS
    )
    assert document["identity_contract"]["fresh_target_identities_registered"] == []
    assert document["failure_driven_successor_contract"][
        "v79_structural_incompatibility_preserved"
    ] is True
    assert document["construction_contract"][
        "partition_uses_only_discovered_layout_and_schema_signature"
    ] is True
    assert document["construction_contract"][
        "incompatible_sources_forced_into_one_model"
    ] is False
    assert document["registered_gate"]["target_execution_forbidden_in_this_slice"] is True
    assert document["claim_boundary"]["sample_tax_reduction_verified"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["fresh_registered_v80_execution_performed"] is False


def test_v80_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7StructuralRoutePreregistrationV80Error):
        verify_structural_route_preregistration_v80(object())
