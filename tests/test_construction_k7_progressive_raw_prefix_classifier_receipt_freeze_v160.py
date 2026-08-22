from pathlib import Path

from acfqp.construction_k7_progressive_raw_prefix_classifier_receipt_freeze_v160 import (
    ATTEMPT_TERMINAL_STATE,
    CLASSIFIER_RECEIPT_ID,
    SAME_IDENTITY_RERUN_FORBIDDEN,
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v160_classifier_receipt_is_frozen_without_target_outcomes():
    raw = (
        ROOT
        / ".tmp/exact-freeze/v160_progressive_raw_prefix_classifier_receipt.json"
    ).read_bytes()
    document = verify_frozen_progressive_raw_prefix_classifier_receipt_v160(raw)
    assert document["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
    assert document["fresh_v160_target_outcomes_accessed"] is False
    assert document["derived_stable_prefix_observation_count"] == 2
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_SUCCESS_BY_SUCCESSOR_LOCK"
    assert SAME_IDENTITY_RERUN_FORBIDDEN is True
