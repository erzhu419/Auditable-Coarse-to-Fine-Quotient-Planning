import hashlib
from pathlib import Path
from acfqp import construction_k7_family_wide_utilization_independent_verifier_v102 as verifier
from acfqp.phase3e_ids import loads_canonical_json

PATH = Path(".tmp/exact-freeze/v102_family_wide_utilization_campaign.json")


def test_v102_producer_free_verification():
    result = verifier.verify_family_wide_utilization_campaign_bytes_v102(PATH.read_bytes()); e = result["verified_aggregate_evidence"]
    assert result["campaign_declared_registered_gate_passed"] is True
    assert result["registered_v102_gate_independently_verified"] is False
    assert e["meta_abstract_execution_match_count"] == 45
    assert e["meta_execution_step_count"] == 72
    assert e["activation_label_reduction"] == 27
    assert e["producer_free_aggregate_later_episode_match_lower_bound_is_majority"] is True
    assert [x["seed"] for x in result["missing_evidence"]["affected_occurrences"]] == [1_013_103, 1_013_104]
    assert result["complete_world_model_synthesized"] is False


def test_v102_verification_artifact_identity():
    raw = verifier.freeze_family_wide_utilization_verification_v102(PATH.read_bytes()); doc = loads_canonical_json(raw)
    assert doc["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
