from pathlib import Path
import hashlib

from acfqp.construction_k7_online_typed_plan_receipt_preregistration_v172r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    freeze_online_typed_plan_receipt_preregistration_v172r1,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v172r1_is_fresh_and_preserves_failed_v172_identity():
    document = freeze_online_typed_plan_receipt_preregistration_v172r1().to_document()
    assert len(TARGET_OCCURRENCES) == 2
    assert document["failed_v172_attempt_id_reused"] is False
    assert document["registered_gate"][
        "failed_v172_identity_preserved_and_not_rerun"
    ] is True
    assert document["claim_boundary"]["target_outcomes_accessed"] is False


def test_v172r1_frozen_preregistration_bytes():
    if PREREGISTRATION_ID == "0" * 64:
        return
    frozen = freeze_online_typed_plan_receipt_preregistration_v172r1()
    raw = (
        FREEZE / "v172r1_online_typed_plan_receipt_preregistration.json"
    ).read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
