from acfqp import construction_k7_occurrence_balanced_source_preregistration_v91r1 as pre


def test_v91r1_preregistration_freezes_before_outcomes():
    value = pre.verify_occurrence_balanced_source_preregistration_v91r1(
        pre.freeze_occurrence_balanced_source_preregistration_v91r1()
    )
    document = value.to_document()
    assert document["fresh_registered_v91r1_execution_performed"] is False
    assert document["acquisition_contract"][
        "prequential_confidence_denominator"
    ] == 4096
    assert document["acquisition_contract"]["fixed_label_floor_present"] is False
    assert document["construction_contract"][
        "multiple_residual_proposals_required_for_positive_gate"
    ] is True
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v91r1_config_uses_only_fresh_registered_source_ids():
    config = pre.campaign_config_v91r1()
    assert config["source_pool_seeds"] == (931101, 931102)
    assert config["source_worker_count"] == 2
    assert config["prequential_confidence_denominator"] == 4096
