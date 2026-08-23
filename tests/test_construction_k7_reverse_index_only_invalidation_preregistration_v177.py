from pathlib import Path

from acfqp.construction_k7_reverse_index_only_invalidation_preregistration_v177 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_reverse_index_only_invalidation_preregistration_v177,
)


def test_v177_preregistration_is_outcome_free_and_frozen():
    receipt = freeze_reverse_index_only_invalidation_preregistration_v177()
    document = receipt.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "zero_production_live_dependency_projection_scan_required"
    ] is True
    assert document["target_worker_count"] == 2
    if PREREGISTRATION_ID != "0" * 64:
        assert receipt.preregistration_id == PREREGISTRATION_ID
        assert len(receipt.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        import hashlib

        assert hashlib.sha256(receipt.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256


def test_v177_preregistration_artifact_matches_when_frozen():
    if PREREGISTRATION_ID == "0" * 64:
        return
    root = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
    raw = (root / "v177_reverse_index_only_invalidation_preregistration.json").read_bytes()
    assert raw == freeze_reverse_index_only_invalidation_preregistration_v177().canonical_bytes
