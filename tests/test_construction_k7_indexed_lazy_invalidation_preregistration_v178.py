from acfqp.construction_k7_indexed_lazy_invalidation_preregistration_v178 import (
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    freeze_indexed_lazy_invalidation_preregistration_v178,
)


def test_v178_preregistration_is_outcome_free_and_two_worker_bounded():
    registration = freeze_indexed_lazy_invalidation_preregistration_v178()
    document = registration.to_document()
    assert len(TARGET_OCCURRENCES) == 4
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["preregistration_id"] == registration.preregistration_id
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID


def test_v178_preregisters_zero_scan_and_lazy_update_gates():
    gate = freeze_indexed_lazy_invalidation_preregistration_v178().to_document()[
        "registered_gate"
    ]
    assert gate["zero_production_prior_receipt_event_scan_required"] is True
    assert gate["zero_eager_retained_authorization_update_required"] is True
    assert gate["lazy_authorization_receipt_and_issuance_join_required"] is True
