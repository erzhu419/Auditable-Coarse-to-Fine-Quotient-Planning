from acfqp import construction_k7_all_path_v34_failure_freeze_v180r4 as frozen


def test_v180r4_pre_execution_failure_is_retained_without_success_claim() -> None:
    value = frozen.load_frozen_v34_failure_v180r4()
    document = value.to_document()
    assert value.failure_id == frozen.EXPECTED_FAILURE_ID
    assert document["output_root_created"] is False
    assert document["retained_output_file_count"] == 0
    assert document["success_claimed"] is False
    assert document["same_authorization_rerun_forbidden"] is True
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
