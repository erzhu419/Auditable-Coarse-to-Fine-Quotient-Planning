from acfqp import construction_k7_source_model_acceptance_preregistration_v91r3 as pre


def test_v91r3_acceptance_rule_is_frozen_before_construction():
    value = pre.verify_source_model_acceptance_preregistration_v91r3(
        pre.freeze_source_model_acceptance_preregistration_v91r3()
    )
    document = value.to_document()
    gate = document["corrected_gate_contract"]
    assert gate["singleton_version_space_is_not_a_failure"] is True
    assert gate["synthetic_or_duplicate_uncertainty_forbidden"] is True
    assert document["execution_contract"]["new_source_outcomes_forbidden"] is True
    assert document["claim_boundary"]["official_scalar_cost"] is None
