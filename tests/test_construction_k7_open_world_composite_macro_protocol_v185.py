from acfqp import construction_k7_open_world_composite_macro_protocol_v185 as protocol


def test_v185_protocol_is_outcome_free_and_only_toggles_derived_macro_prior() -> None:
    document = protocol.freeze_open_world_composite_macro_protocol_v185().to_document()
    assert document["protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
    assert document["manifest_preimages_revealed"] is False
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["source_generation_witness_schedule_supplied"] is False
    assert document["predeclared_reusable_factor_slots"] == []
    assert document["predeclared_macro_bodies"] == []
    assert document["reusable_composite_operator_invention_required"] is True
    assert document["new_low_level_primitive_opcode_invention_claimed"] is False
    assert document["same_synthesizer_and_stop_rule_both_arms"] is True
    assert document["only_macro_library_prior_toggled_between_arms"] is True
    assert document["incompatible_schema_prior_rejected_before_target_query"] is True
    assert document["broad_iid_sample_efficiency_claimed"] is False
    assert document["arbitrary_domain_transfer_claimed"] is False
    assert document["official_execution_allowed"] is False
