from acfqp import construction_k7_ten_terminal_aggregation_protocol_v180r12r1 as protocol


def test_v180r12r1_corrects_the_denominator_without_unlocking_gates() -> None:
    document = protocol.freeze_ten_terminal_aggregation_protocol_v180r12r1().to_document()
    assert document["aggregation_protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
    assert document["failed_predecessor_preserved_without_relabeling"] is True
    assert document["terminal_code_count"] == 10
    assert document["completed_terminal_code_count_bound_at_successor_freeze"] == 8
    assert document["pending_terminal_codes_at_successor_freeze"] == [
        "LOCAL_GROUND_RECOVERY",
        "FULL_GROUND_FALLBACK",
    ]
    cached = next(
        row
        for row in document["terminal_sources"]
        if row["terminal_code"] == "CACHED_EXACT_INFEASIBLE"
    )
    assert cached["status_at_successor_freeze"] == (
        "COMPLETED_AND_INDEPENDENTLY_VERIFIED"
    )
    assert cached["verification_relative_path"].endswith("VERIFICATION.json")
    assert document["pending_outcome_bytes_accessed"] is False
    assert document["execution_authorization_issued"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
