from pathlib import Path
import hashlib

from acfqp.construction_k7_certificate_delta_invalidation_preregistration_v175r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    freeze_certificate_delta_invalidation_preregistration_v175r1,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v175r1_preregistration_fixes_classifier_before_fresh_outcomes():
    document = freeze_certificate_delta_invalidation_preregistration_v175r1().to_document()
    assert len(TARGET_OCCURRENCES) == 4
    assert document["corrected_classifier_receipt"]["schema"] == (
        "acfqp.paid_path_prefix_classifier_receipt.v161"
    )
    assert document["preserved_failed_v175"]["same_identity_rerun_forbidden"] is True
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "zero_serialized_full_graph_scan_on_decision_path_required"
    ] is True


def test_v175r1_frozen_preregistration_bytes():
    frozen = freeze_certificate_delta_invalidation_preregistration_v175r1()
    raw = (
        FREEZE / "v175r1_certificate_delta_invalidation_preregistration.json"
    ).read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
