from acfqp.construction_k7_role_free_relational_transfer_preregistration_v70 import (
    freeze_role_free_relational_transfer_preregistration_v70,
    verify_role_free_relational_transfer_preregistration_v70,
)


def test_v70_preregistration_is_outcome_free_and_transfer_claim_locked():
    value = verify_role_free_relational_transfer_preregistration_v70(
        freeze_role_free_relational_transfer_preregistration_v70()
    )
    document = value.to_document()
    assert document["fresh_registered_target_execution_performed"] is False
    assert document["target_families"]["target_occurrence_count"] == 6
    assert document["matched_transfer_contract"][
        "target_observation_exactness_required_before_transfer_planning"
    ] is True
    assert document["matched_transfer_contract"]["online_transfer_planner_integrated"] is False
    assert document["safety_contract"]["transferred_abstract_plan_safety_authority"] is False
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
