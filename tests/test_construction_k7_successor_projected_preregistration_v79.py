import pytest

from acfqp.construction_k7_successor_projected_preregistration_v79 import (
    ConstructionK7SuccessorProjectedPreregistrationV79Error,
    SOURCE_FAMILY,
    SOURCE_POOL_SEEDS,
    freeze_successor_projected_preregistration_v79,
    verify_successor_projected_preregistration_v79,
)


def test_v79_preregisters_successor_projected_source_gate_before_outcomes():
    value = verify_successor_projected_preregistration_v79(
        freeze_successor_projected_preregistration_v79()
    )
    document = value.to_document()
    assert SOURCE_FAMILY == "BALANCED_BATCH_REFINEMENT"
    assert tuple(document["identity_contract"]["source_pool_seeds"]) == (
        SOURCE_POOL_SEEDS
    )
    assert document["identity_contract"]["fresh_target_identities_registered"] == []
    assert document["failure_driven_successor_contract"][
        "v78_pooled_abstention_preserved"
    ] is True
    assert document["construction_contract"][
        "query_prestates_not_used_as_terminal_frontier_vote_inputs"
    ] is True
    assert document["registered_gate"]["target_execution_forbidden_in_this_slice"] is True
    assert document["claim_boundary"]["sample_tax_reduction_verified"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["fresh_registered_v79_execution_performed"] is False


def test_v79_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7SuccessorProjectedPreregistrationV79Error):
        verify_successor_projected_preregistration_v79(object())
