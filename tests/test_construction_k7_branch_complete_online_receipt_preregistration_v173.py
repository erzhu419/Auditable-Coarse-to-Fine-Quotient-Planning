from pathlib import Path
import hashlib

from acfqp.construction_k7_branch_complete_online_receipt_preregistration_v173 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_branch_complete_online_receipt_preregistration_v173,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v173_preregistration_requires_every_online_source_branch():
    document = freeze_branch_complete_online_receipt_preregistration_v173().to_document()
    gate = document["registered_gate"]
    assert gate["direct_online_source_required"] is True
    assert gate["memoized_online_source_required"] is True
    assert gate["observation_online_source_required"] is True
    assert gate["dependency_revalidated_online_source_required"] is True
    assert document["claim_boundary"]["target_outcomes_accessed"] is False


def test_v173_frozen_preregistration_bytes():
    if PREREGISTRATION_ID == "0" * 64:
        return
    frozen = freeze_branch_complete_online_receipt_preregistration_v173()
    raw = (
        FREEZE / "v173_branch_complete_online_receipt_preregistration.json"
    ).read_bytes()
    assert frozen.canonical_bytes == raw
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
