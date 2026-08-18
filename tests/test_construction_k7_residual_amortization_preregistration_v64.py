from acfqp.construction_k7_residual_amortization_preregistration_v64 import (
    TARGET_OCCURRENCE_COUNT,
    campaign_config_v64,
    freeze_residual_amortization_preregistration_v64,
    verify_residual_amortization_preregistration_v64,
)


def test_v64_preregistration_freezes_72_fresh_occurrences_before_outcomes():
    value = verify_residual_amortization_preregistration_v64(
        freeze_residual_amortization_preregistration_v64()
    )
    document = value.to_document()
    assert TARGET_OCCURRENCE_COUNT == 72
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["amortization_gate"]["offline_development_label_tax"] == 204
    assert document["resource_schedule"]["worker_count_frozen_cap"] == 12
    assert document["claim_boundary"]["official_N_break_even"] is None
    assert campaign_config_v64()["worker_count"] == 12
