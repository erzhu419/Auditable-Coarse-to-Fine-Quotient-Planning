from acfqp.construction_k7_relational_world_model_preregistration_v68 import (
    freeze_relational_world_model_preregistration_v68,
    verify_relational_world_model_preregistration_v68,
)


def test_v68_preregistration_is_outcome_free_and_claim_locked():
    value = verify_relational_world_model_preregistration_v68(
        freeze_relational_world_model_preregistration_v68()
    )
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["target_families"]["target_occurrence_count"] == 6
    assert document["world_model_contract"][
        "transition_and_terminal_programs_jointly_selected_for_planning"
    ] is True
    assert document["safety_contract"]["relational_abstract_plan_safety_authority"] is False
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
