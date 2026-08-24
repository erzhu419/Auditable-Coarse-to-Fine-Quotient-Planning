from acfqp import construction_k7_full_ground_fallback_execution_failure_freeze_v180r7 as frozen


def test_v180r7_failure_and_empty_partial_output_are_frozen() -> None:
    value = frozen.load_frozen_full_ground_fallback_execution_failure_v180r7()
    document = value.to_document()
    assert value.failure_id == frozen.EXPECTED_FAILURE_ID
    assert document["retained_output_file_count"] == 0
    assert document["same_authorization_rerun_forbidden"] is True
    assert document["success_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
