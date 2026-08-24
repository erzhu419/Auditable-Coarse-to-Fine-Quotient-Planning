from acfqp import construction_k7_open_world_total_machine_protocol_v182r2 as protocol


def test_v182r2_protocol_is_outcome_free_and_references_frozen_failure() -> None:
    document = protocol.freeze_open_world_total_machine_protocol_v182r2().to_document()
    assert document["protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
    assert document["failed_predecessor_failure_id"] != "0" * 64
    assert document[
        "failed_predecessor_preserved_and_same_identity_rerun_forbidden"
    ] is True
    assert document["fresh_successor_identity_required"] is True
    assert document["source_and_target_manifest_preimages_revealed"] is False
    assert document["source_or_target_transition_outcomes_accessed"] is False
    assert document[
        "candidate_admission_requires_full_finite_carrier_totality"
    ] is True
    assert document["full_finite_carrier_totality_is_not_unbounded_totality"] is True
    assert document["official_execution_allowed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v182r2_protocol_has_fresh_manifest_commitments() -> None:
    assert len(protocol.MANIFEST_COMMITMENTS_V182R2) == 3
    assert len(set(protocol.MANIFEST_COMMITMENTS_V182R2)) == 3
    assert all(len(value) == 64 for value in protocol.MANIFEST_COMMITMENTS_V182R2)
