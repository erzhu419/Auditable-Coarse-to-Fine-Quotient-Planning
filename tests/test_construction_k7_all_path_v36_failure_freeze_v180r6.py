from acfqp import construction_k7_all_path_v36_failure_freeze_v180r6 as frozen


def test_v180r6_failure_and_all_partial_outputs_are_retained_exactly() -> None:
    value = frozen.load_frozen_v36_failure_v180r6()
    document = value.to_document()
    assert value.failure_id == frozen.EXPECTED_FAILURE_ID
    assert value.partial_output_facts == frozen.EXPECTED_PARTIAL_OUTPUT_FACTS
    assert document["failure_type"] == "BrokenProcessPool"
    assert document["output_root_created"] is True
    assert document["retained_output_file_count"] == 6
    assert document["same_authorization_rerun_forbidden"] is True
    assert document["success_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
