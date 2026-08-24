from acfqp import construction_k7_ten_terminal_aggregation_protocol_v180r12 as protocol


def test_v180r12_protocol_freezes_pending_ten_terminal_denominator() -> None:
    document = protocol.freeze_ten_terminal_aggregation_protocol_v180r12().to_document()
    assert document["aggregation_protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
    assert document["terminal_code_count"] == 10
    assert document["completed_terminal_code_count_at_protocol_freeze"] == 7
    assert document["pending_terminal_codes_at_protocol_freeze"] == [
        "LOCAL_GROUND_RECOVERY",
        "FULL_GROUND_FALLBACK",
        "CACHED_EXACT_INFEASIBLE",
    ]
    assert document["pending_outcome_bytes_accessed"] is False
    assert document["every_terminal_requires_counter_record_work_vector_comparison_vector"] is True
    assert document["scalarization_in_this_protocol"] is False
    assert document["separate_fresh_calibration_successor_required_for_scalar_and_break_even"] is True
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
