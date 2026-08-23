from pathlib import Path
import hashlib

from acfqp.construction_k7_certificate_delta_invalidation_preregistration_v175 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    freeze_certificate_delta_invalidation_preregistration_v175,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v175_preregistration_is_fresh_outcome_free_and_delta_bound():
    document = freeze_certificate_delta_invalidation_preregistration_v175().to_document()
    assert len(TARGET_OCCURRENCES) == 4
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "certificate_delta_required_for_every_episode"
    ] is True
    assert document["registered_gate"][
        "zero_serialized_full_graph_scan_on_decision_path_required"
    ] is True
    assert document["registered_gate"][
        "delta_frontier_must_match_uncharged_full_diff_control"
    ] is True
    assert document["claim_boundary"][
        "query_local_exact_overlay_remains_only_safety_authority"
    ] is True
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v175_frozen_preregistration_bytes():
    frozen = freeze_certificate_delta_invalidation_preregistration_v175()
    raw = (
        FREEZE / "v175_certificate_delta_invalidation_preregistration.json"
    ).read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
