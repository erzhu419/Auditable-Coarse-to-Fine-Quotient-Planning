from acfqp import construction_k7_version_space_target_preregistration_v92 as pre


def test_v92_preregistration_freezes_fresh_target_and_claim_boundaries():
    value = pre.freeze_version_space_target_preregistration_v92()
    assert pre.verify_version_space_target_preregistration_v92(value) is value
    document = value.to_document()
    assert document["identity_contract"]["target_seeds"] == [951101, 951102]
    assert document["identity_contract"][
        "target_seeds_disjoint_from_v91r2_source"
    ] is True
    assert document["construction_contract"][
        "singleton_version_space_propagated_without_synthetic_uncertainty"
    ] is True
    assert document["claim_boundary"]["registered_v92_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
