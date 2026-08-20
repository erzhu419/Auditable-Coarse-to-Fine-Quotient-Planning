import pytest

from acfqp.construction_k7_all_frontier_preregistration_v83 import (
    ConstructionK7AllFrontierPreregistrationV83Error,
    SOURCE_POOL_SEEDS,
    freeze_all_frontier_preregistration_v83,
    verify_all_frontier_preregistration_v83,
)


def test_v83_preregisters_all_frontier_gate_before_outcomes():
    value = verify_all_frontier_preregistration_v83(
        freeze_all_frontier_preregistration_v83()
    )
    document = value.to_document()
    assert tuple(document["identity_contract"]["source_pool_seeds"]) == (
        SOURCE_POOL_SEEDS
    )
    assert len(SOURCE_POOL_SEEDS) == 6
    assert document["failure_driven_successor_contract"][
        "v82_terminal_frontier_compilation_failure_preserved"
    ] is True
    assert document["construction_contract"][
        "all_retained_terminal_trees_checked_before_model_compilation"
    ] is True
    assert document["construction_contract"][
        "residual_successor_consensus_used_before_issuance"
    ] is False
    assert document["resource_schedule"]["maximum_simultaneous_worker_count"] == 2
    assert document["claim_boundary"]["sample_tax_reduction_verified"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["fresh_registered_v83_execution_performed"] is False


def test_v83_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7AllFrontierPreregistrationV83Error):
        verify_all_frontier_preregistration_v83(object())
