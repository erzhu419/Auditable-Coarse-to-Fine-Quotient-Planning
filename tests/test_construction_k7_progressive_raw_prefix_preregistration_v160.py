from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_progressive_raw_prefix_preregistration_v160 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_progressive_raw_prefix_preregistration_v160,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v160_target_preregistration_is_outcome_free_and_frozen():
    if PREREGISTRATION_ID == "0" * 64:
        pytest.skip("V160 target preregistration not frozen")
    classifier = (
        ROOT
        / ".tmp/exact-freeze/v160_progressive_raw_prefix_classifier_receipt.json"
    ).read_bytes()
    receipt = freeze_progressive_raw_prefix_preregistration_v160(classifier)
    document = receipt.to_document()
    assert receipt.preregistration_id == PREREGISTRATION_ID
    assert len(receipt.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(receipt.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["target_worker_count"] == 2
    assert document["required_target_occurrence_count"] == 6
