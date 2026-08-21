from acfqp.construction_k7_permutation_matched_sample_tax_preregistration_v89 import (
    PREREGISTRATION_ID,
    _frozen_source_facts,
    _source_facts,
    freeze_permutation_matched_sample_tax_preregistration_v89,
)


def test_v89_preregistration_identity_is_frozen():
    assert PREREGISTRATION_ID == (
        "e463074f1155bc9510feda4c128c86f7652a8a8719e04ced80a94a2661d770b4"
    )


def test_v89_preregistration_is_outcome_free_and_source_closed():
    registration = freeze_permutation_matched_sample_tax_preregistration_v89()
    document = registration.to_document()
    assert _source_facts() == _frozen_source_facts()
    assert document["fresh_registered_v89_execution_performed"] is False
    assert document["registered_gate"]["aggregate_target_sample_reduction_required"] is True
    assert document["claim_boundary"]["sample_tax_reduction_verified"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
