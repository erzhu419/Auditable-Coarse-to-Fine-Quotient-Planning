from acfqp.construction_k7_indexed_lazy_invalidation_preregistration_v178r1 import (
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    freeze_indexed_lazy_invalidation_preregistration_v178r1,
)


def test_v178r1_preregistration_is_fresh_outcome_free_and_bounded():
    registration = freeze_indexed_lazy_invalidation_preregistration_v178r1()
    document = registration.to_document()
    assert len(TARGET_OCCURRENCES) == 4
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["preserved_v178_failure_id"] != "0" * 64
    assert document["preregistration_id"] == registration.preregistration_id
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID


def test_v178r1_registers_demand_conditioned_lookup_gate():
    gate = freeze_indexed_lazy_invalidation_preregistration_v178r1().to_document()[
        "registered_gate"
    ]
    assert gate["receipt_reverse_index_construction_required_each_occurrence"] is True
    assert gate["receipt_reverse_index_lookup_required_only_when_invalidation_occurs"] is True
    assert gate["positive_receipt_reverse_index_lookup_required_campaign_wide"] is True
