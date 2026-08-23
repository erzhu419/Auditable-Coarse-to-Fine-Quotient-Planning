from pathlib import Path
import hashlib

from acfqp.construction_k7_receipt_driven_invalidation_preregistration_v174 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    freeze_receipt_driven_invalidation_preregistration_v174,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v174_preregistration_is_outcome_free_and_dependency_bound():
    document = freeze_receipt_driven_invalidation_preregistration_v174().to_document()
    assert len(TARGET_OCCURRENCES) == 4
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"]["selective_graph_invalidation_required"] is True
    assert document["registered_gate"][
        "incremental_revalidation_without_per_hit_rescan_required"
    ] is True
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v174_frozen_preregistration_bytes():
    if PREREGISTRATION_ID == "0" * 64:
        return
    frozen = freeze_receipt_driven_invalidation_preregistration_v174()
    raw = (FREEZE / "v174_receipt_driven_invalidation_preregistration.json").read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
