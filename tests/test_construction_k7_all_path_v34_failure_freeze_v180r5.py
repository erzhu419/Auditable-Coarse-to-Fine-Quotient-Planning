from acfqp import construction_k7_all_path_v34_failure_freeze_v180r5 as frozen


def test_v180r5_failure_and_all_partial_outputs_are_retained_exactly() -> None:
    value = frozen.load_frozen_v34_failure_v180r5()
    document = value.to_document()
    assert value.failure_id == frozen.EXPECTED_FAILURE_ID
    assert len(value.partial_inventory) == frozen.EXPECTED_PARTIAL_OUTPUT_FILE_COUNT
    assert document["failure_type"] == (
        "ConstructionK7AllPathProductionTerminalFinalizerV180r3Error"
    )
    assert document["failure_message"] == (
        "V34 operational WorkVector denominator changed"
    )
    assert document["output_root_created"] is True
    assert document["same_authorization_rerun_forbidden"] is True
    assert document["success_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_v180r5_partial_inventory_covers_campaign_model_and_segments() -> None:
    paths = {
        row["relative_path"]
        for row in frozen.load_frozen_v34_failure_v180r5().partial_inventory
    }
    assert "campaign.json" in paths
    assert "model/operational-proof.json" in paths
    assert "segment-00-v24_initial_32/process-supervision.json" in paths
    assert "segment-08-v33/process-supervision.json" in paths
