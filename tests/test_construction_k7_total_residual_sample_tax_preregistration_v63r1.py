from acfqp.construction_k7_total_residual_sample_tax_preregistration_v63r1 import (
    FAILED_V63_REGISTERED_FAILURE_ID,
    campaign_config_v63r1,
    freeze_total_residual_sample_tax_preregistration_v63r1,
    verify_total_residual_sample_tax_preregistration_v63r1,
)


def test_v63r1_preregistration_is_fresh_total_and_outcome_free():
    value = verify_total_residual_sample_tax_preregistration_v63r1(
        freeze_total_residual_sample_tax_preregistration_v63r1()
    )
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["frozen_predecessors"]["failed_v63_registered_failure_id"] == FAILED_V63_REGISTERED_FAILURE_ID
    assert document["totalization_contract"]["insufficient_calibrated_evidence_returns_typed_abstention"] is True
    assert document["totalization_contract"]["query_pool_exhaustion_used_as_positive_stop"] is False
    assert document["matched_ablation_contract"]["positive_label_reduction_required_in_every_family_projection"] is False
    assert document["claim_boundary"]["official_N_break_even"] is None
    assert campaign_config_v63r1()["worker_count"] == 4
