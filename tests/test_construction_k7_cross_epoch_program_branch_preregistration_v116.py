from acfqp import construction_k7_cross_epoch_program_branch_preregistration_v116 as pre


def test_v116_preregistration_is_outcome_free_and_exact():
    value = pre.freeze_cross_epoch_program_branch_preregistration_v116()
    document = pre.verify_cross_epoch_program_branch_preregistration_v116(
        value
    ).to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["registered_gate"][
        "every_occurrence_planning_compute_not_above_v115"
    ] is True
    assert document["claim_boundary"]["registered_v116_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
