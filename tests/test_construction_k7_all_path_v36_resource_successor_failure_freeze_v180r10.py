from acfqp import construction_k7_all_path_v36_resource_successor_failure_freeze_v180r10 as frozen


def test_v180r10_failure_and_complete_output_tree_are_frozen() -> None:
    value = frozen.load_frozen_v36_resource_successor_failure_v180r10()
    document = value.to_document()
    assert value.failure_id == frozen.EXPECTED_FAILURE_ID
    assert len(value.output_facts) == 20
    assert document["same_authorization_rerun_forbidden"] is True
    assert document["success_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False

