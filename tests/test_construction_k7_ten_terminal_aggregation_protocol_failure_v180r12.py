from acfqp import construction_k7_ten_terminal_aggregation_protocol_failure_v180r12 as failure


def test_v180r12_failure_preserves_the_misregistered_predecessor() -> None:
    document = (
        failure.freeze_ten_terminal_aggregation_protocol_failure_v180r12().to_document()
    )
    assert document["failure_id"] == failure.EXPECTED_FAILURE_ID
    assert document["failure_kind"] == "HISTORICAL_COMPLETION_STATUS_MISREGISTERED"
    assert document["recorded_status"] == "AUTHORIZED_NOT_STARTED"
    assert document["correct_status"] == (
        "COMPLETED_AND_INDEPENDENTLY_VERIFIED_BEFORE_PROTOCOL_FREEZE"
    )
    assert document["retained_v180r8_evidence"][
        "producer_free_replay_matches_retained_verification_bytes"
    ] is True
    assert document["predecessor_protocol_executed"] is False
    assert document["fresh_successor_required"] is True
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
