from pathlib import Path
import hashlib

from acfqp.construction_k7_certificate_delta_only_invalidation_preregistration_v176 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    freeze_certificate_delta_only_invalidation_preregistration_v176,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v176_preregistration_defers_full_graph_control_before_outcomes():
    document = freeze_certificate_delta_only_invalidation_preregistration_v176().to_document()
    assert len(TARGET_OCCURRENCES) == 4
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "zero_production_full_graph_diff_control_required"
    ] is True
    assert document["registered_gate"][
        "producer_free_full_graph_diff_control_required"
    ] is True
    assert document["claim_boundary"][
        "query_local_exact_overlay_remains_only_safety_authority"
    ] is True


def test_v176_frozen_preregistration_bytes():
    frozen = freeze_certificate_delta_only_invalidation_preregistration_v176()
    raw = (
        FREEZE / "v176_certificate_delta_only_invalidation_preregistration.json"
    ).read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
