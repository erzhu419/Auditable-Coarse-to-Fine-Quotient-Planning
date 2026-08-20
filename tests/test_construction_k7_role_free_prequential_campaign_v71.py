import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V71") != "1",
    reason="explicit preregistered V71 prequential campaign",
)
def test_v71_registered_prequential_gate_and_accounting_are_frozen():
    from acfqp.construction_k7_role_free_prequential_campaign_v71 import (
        run_role_free_prequential_campaign_v71,
        verify_role_free_prequential_campaign_v71,
    )

    value = verify_role_free_prequential_campaign_v71(
        run_role_free_prequential_campaign_v71()
    )
    document = value.to_document()
    gate = document["registered_prequential_gate"]
    assert gate["passed"] is True
    assert gate["joint_prior_heldout_validated_occurrence_count"] > 0
    assert gate["strict_heldout_validated_occurrence_count"] > 0
    assert gate["all_schedules_outcome_blind"] is True
    assert gate["incompatible_schema_ood_rejection_count"] == gate[
        "required_ood_rejection_count"
    ]
    assert document["accounting"]["all_axes_separate"] is True
    assert document["sample_tax_comparison"][
        "online_actual_sample_reduction_claimed"
    ] is False
    assert document["producer_free_verification_present"] is False
    assert document["online_adaptive_acquisition_integrated"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
