import hashlib

from acfqp import construction_k7_receipted_utilization_preregistration_v103 as pre


def test_v103_is_frozen_before_fresh_outcomes():
    value = pre.verify_receipted_utilization_preregistration_v103(
        pre.freeze_receipted_utilization_preregistration_v103()
    )
    document = value.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["source_closure"]["frozen_before_any_registered_v103_target_outcome"] is True
    assert document["construction_contract"]["every_executed_action_requires_an_independent_receipt"] is True
    assert document["frozen_predecessors"]["v102_gate_independently_verified"] is False
    assert document["claim_boundary"]["complete_world_model_synthesized"] is False
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
