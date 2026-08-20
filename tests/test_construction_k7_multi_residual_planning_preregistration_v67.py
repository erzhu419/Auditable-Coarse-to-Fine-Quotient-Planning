from acfqp.construction_k7_multi_residual_planning_preregistration_v67 import (
    freeze_multi_residual_planning_preregistration_v67,
    verify_multi_residual_planning_preregistration_v67,
)


def test_v67_preregistration_is_outcome_free_and_claim_locked():
    value = verify_multi_residual_planning_preregistration_v67(
        freeze_multi_residual_planning_preregistration_v67()
    )
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["target_families"]["target_occurrence_count"] == 12
    assert document["joint_model_contract"][
        "at_least_two_compilable_proposals_required_before_joint_planning"
    ] is True
    assert document["safety_contract"]["joint_abstract_plan_safety_authority"] is False
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
