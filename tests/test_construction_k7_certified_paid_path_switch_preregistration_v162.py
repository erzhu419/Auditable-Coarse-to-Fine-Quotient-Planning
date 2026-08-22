from pathlib import Path
import hashlib

from acfqp.construction_k7_certified_paid_path_switch_preregistration_v162 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_certified_paid_path_switch_preregistration_v162,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v162_preregistration_is_outcome_free_and_exact():
    frozen = freeze_certified_paid_path_switch_preregistration_v162(
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes()
    )
    document = frozen.to_document()
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "switch_requires_classifier_positive_and_paid_relation_witness"
    ] is True
    assert document["frozen_v160_failure"]["document"][
        "failed_result_not_reclassified_as_success"
    ] is True
    assert document["frozen_v161_failure"]["document"]["terminal_state"] == (
        "FAILED_NO_SAME_IDENTITY_RERUN"
    )
