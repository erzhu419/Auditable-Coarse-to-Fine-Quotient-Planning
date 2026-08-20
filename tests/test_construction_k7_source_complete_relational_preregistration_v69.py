from acfqp.construction_k7_source_complete_relational_preregistration_v69 import (
    freeze_source_complete_relational_preregistration_v69,
    verify_source_complete_relational_preregistration_v69,
)


def test_v69_preregistration_is_outcome_free_and_source_complete():
    value = verify_source_complete_relational_preregistration_v69(
        freeze_source_complete_relational_preregistration_v69()
    )
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["target_families"]["target_occurrence_count"] == 6
    assert document["source_complete_contract"][
        "independent_decision_tree_frontier_rederivation_required"
    ] is True
    assert document["safety_contract"]["relational_abstract_plan_safety_authority"] is False
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
