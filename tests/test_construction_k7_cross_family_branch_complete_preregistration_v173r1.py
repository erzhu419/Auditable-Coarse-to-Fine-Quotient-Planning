from pathlib import Path
import hashlib

from acfqp.construction_k7_cross_family_branch_complete_preregistration_v173r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_cross_family_branch_complete_preregistration_v173r1,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v173r1_preregisters_cross_family_branch_roles_before_outcomes():
    document = freeze_cross_family_branch_complete_preregistration_v173r1().to_document()
    assert set(document["registered_branch_coverage_roles"].values()) == {
        "DIRECT_BRANCH_COVERAGE",
        "MEMOIZED_BRANCH_COVERAGE",
    }
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"]["failed_v173_identity_preserved_not_rerun"] is True


def test_v173r1_frozen_preregistration_bytes():
    if PREREGISTRATION_ID == "0" * 64:
        return
    frozen = freeze_cross_family_branch_complete_preregistration_v173r1()
    raw = (
        FREEZE / "v173r1_cross_family_branch_complete_preregistration.json"
    ).read_bytes()
    assert frozen.canonical_bytes == raw
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
