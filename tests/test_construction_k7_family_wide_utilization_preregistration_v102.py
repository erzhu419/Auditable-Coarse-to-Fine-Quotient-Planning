import hashlib
from acfqp import construction_k7_family_wide_utilization_preregistration_v102 as pre


def test_v102_is_frozen_before_fresh_outcomes():
    value = pre.verify_family_wide_utilization_preregistration_v102(pre.freeze_family_wide_utilization_preregistration_v102())
    doc = value.to_document()
    assert doc["preregistration_id"] == pre.PREREGISTRATION_ID
    assert doc["source_closure"]["frozen_before_any_registered_v102_target_outcome"] is True
    assert doc["construction_contract"]["v102_coverage_unit"] == "EVERY_TARGET_FAMILY"
    assert doc["claim_boundary"]["complete_world_model_synthesized"] is False
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
