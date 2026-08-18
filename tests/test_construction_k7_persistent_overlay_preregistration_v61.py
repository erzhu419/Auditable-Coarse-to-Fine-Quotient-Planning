import hashlib

from acfqp import construction_k7_persistent_overlay_preregistration_v61 as pre


def test_v61_preregistration_is_outcome_free_and_fresh():
    value = pre.freeze_persistent_overlay_preregistration_v61()
    assert pre.verify_persistent_overlay_preregistration_v61(value) is value
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["source_closure"]["frozen_before_any_registered_outcome"] is True
    assert document["matched_overlay_contract"]["only_switched_variable"] == (
        "OCCURRENCE_LOCAL_PROOF_OVERLAY_PERSISTENCE"
    )
    assert document["matched_overlay_contract"]["cross_occurrence_ground_fact_reuse_allowed"] is False
    assert document["stopping_contract"]["reachable_frontier_exhaustion_stop_available"] is False
    raw = value.canonical_bytes
    if pre.PREREGISTRATION_ID != "0" * 64:
        assert value.preregistration_id == pre.PREREGISTRATION_ID
        assert len(raw) == pre.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
