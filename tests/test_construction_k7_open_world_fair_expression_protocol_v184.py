from acfqp import construction_k7_open_world_fair_expression_protocol_v184 as protocol


def test_v184_protocol_is_outcome_free_and_open_language_bounded() -> None:
    document = protocol.freeze_open_world_fair_expression_protocol_v184().to_document()
    assert document["protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
    assert document["manifest_preimages_revealed"] is False
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["target_distribution_count"] == 4
    assert document["candidate_language_countably_infinite"] is True
    assert document["whole_program_shape_catalog_forbidden"] is True
    assert document["actual_search_prefix_must_be_resource_bounded"] is True
    assert document["resource_cap_exhaustion_is_not_infeasibility"] is True
    assert document["new_primitive_opcode_invention_claimed"] is False
    assert document["componentwise_target_work_dominance_required"] is True
    assert document["broad_iid_sample_efficiency_claimed"] is False
    assert document["arbitrary_domain_transfer_claimed"] is False
    assert document["official_total_work_dominance_claimed"] is False
    assert document["official_execution_allowed"] is False
