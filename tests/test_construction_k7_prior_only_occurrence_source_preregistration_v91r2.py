from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as pre


def test_v91r2_preregistration_freezes_before_outcomes():
    value = pre.verify_prior_only_occurrence_source_preregistration_v91r2(
        pre.freeze_prior_only_occurrence_source_preregistration_v91r2()
    )
    document = value.to_document()
    assert document["fresh_registered_v91r2_execution_performed"] is False
    assert document["source_partial_acquisition_contract"][
        "strict_complete_model_arm_executed"
    ] is False
    assert document["model_acquisition_contract"][
        "prequential_confidence_denominator"
    ] == 4096
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v91r2_config_uses_only_fresh_registered_source_ids():
    config = pre.campaign_config_v91r2()
    assert config["source_pool_seeds"] == (941101, 941102)
    assert config["source_worker_count"] == 2
    assert config["source_partial_acquisition_maximum_ground_labels"] == 160
