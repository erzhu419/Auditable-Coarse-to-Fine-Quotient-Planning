from acfqp.construction_k7_online_residual_planning_preregistration_v65 import (
    freeze_online_residual_planning_preregistration_v65,
    verify_online_residual_planning_preregistration_v65,
)


def test_v65_preregistration_is_outcome_free_and_fresh():
    value = verify_online_residual_planning_preregistration_v65(
        freeze_online_residual_planning_preregistration_v65()
    )
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["claim_boundary"]["registered_outcome_observed"] is False
    assert document["safety_contract"]["residual_proposal_safety_authority"] is False
    assert document["target_families"]["target_occurrence_count"] == 18
