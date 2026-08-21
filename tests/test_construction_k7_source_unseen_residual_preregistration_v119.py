from acfqp import construction_k7_source_unseen_residual_preregistration_v119 as pre


def test_v119_preregistration_is_fresh_outcome_free_and_claim_locked():
    value = pre.freeze_source_unseen_residual_preregistration_v119()
    document = value.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["source_closure"][
        "frozen_before_any_registered_v119_target_outcome"
    ] is True
    assert document["construction_contract"][
        "higher_order_residual_must_remain_explicitly_unknown"
    ] is True
    assert document["sample_tax_contract"][
        "strict_control_is_not_an_adaptive_no_prior_sample_baseline"
    ] is True
    boundary = document["claim_boundary"]
    assert boundary["registered_v119_target_outcome_observed"] is False
    assert boundary["arbitrary_unseen_domain_transfer_claimed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v119_source_closure_and_resource_schedule_are_exact():
    document = pre.freeze_source_unseen_residual_preregistration_v119().to_document()
    assert document["source_closure"]["source_facts"] == pre._frozen_source_facts()
    assert document["resource_schedule"]["target_worker_count"] == 2
    assert document["resource_schedule"]["maximum_acquisition_labels"] == 320
    assert document["resource_schedule"][
        "strict_complete_model_attempts_per_occurrence"
    ] == 1
