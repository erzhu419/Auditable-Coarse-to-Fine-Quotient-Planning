from acfqp.construction_k7_combined_model_planning_preregistration_v66 import (
    freeze_combined_model_planning_preregistration_v66,
    verify_combined_model_planning_preregistration_v66,
)


def test_v66_preregistration_is_outcome_free_and_claim_locked():
    value = verify_combined_model_planning_preregistration_v66(
        freeze_combined_model_planning_preregistration_v66()
    )
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["target_families"]["target_occurrence_count"] == 12
    assert document["safety_contract"]["combined_abstract_plan_safety_authority"] is False
