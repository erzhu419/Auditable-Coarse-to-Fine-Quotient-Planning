from acfqp.construction_k7_abstract_planning_primary_preregistration_v90 import (
    PREREGISTRATION_ID,
    _frozen_source_facts,
    _source_facts,
    freeze_abstract_planning_primary_preregistration_v90,
)


def test_v90_preregistration_identity_is_frozen():
    assert PREREGISTRATION_ID == (
        "848a6858108179348d53176e6113eeae145c3ce4f18c4181268e482cf2384c28"
    )


def test_v90_registration_is_honest_posthoc_deterministic_analysis():
    document = freeze_abstract_planning_primary_preregistration_v90().to_document()
    assert _source_facts() == _frozen_source_facts()
    assert document["analysis_contract"][
        "posthoc_deterministic_audit_of_already_frozen_v89_evidence"
    ] is True
    assert document["analysis_contract"]["fresh_target_outcome_claimed"] is False
    assert document["claim_boundary"][
        "multi_step_planning_primarily_in_abstract_model_verified"
    ] is False
