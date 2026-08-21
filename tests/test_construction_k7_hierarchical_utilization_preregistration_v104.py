import hashlib

from acfqp import construction_k7_hierarchical_utilization_preregistration_v104 as pre


def test_v104_is_frozen_before_fresh_outcomes():
    value = pre.verify_hierarchical_utilization_preregistration_v104(
        pre.freeze_hierarchical_utilization_preregistration_v104()
    )
    document = value.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["source_closure"]["frozen_before_any_registered_v104_target_outcome"] is True
    assert document["frozen_predecessors"]["v103_registered_gate_passed"] is False
    assert document["construction_contract"]["full_model_match_never_inferred_from_partial_fallback"] is True
    assert document["claim_boundary"]["complete_world_model_synthesized"] is False
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
