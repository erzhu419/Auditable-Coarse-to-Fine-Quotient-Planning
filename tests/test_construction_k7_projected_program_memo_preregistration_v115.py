from acfqp import construction_k7_projected_program_memo_preregistration_v115 as pre


def test_v115_preregistration_is_outcome_free_and_exact():
    value = pre.freeze_projected_program_memo_preregistration_v115()
    document = pre.verify_projected_program_memo_preregistration_v115(
        value
    ).to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["registered_gate"][
        "every_occurrence_planning_compute_below_v113"
    ] is True
    assert document["claim_boundary"][
        "registered_v115_target_outcome_observed"
    ] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
