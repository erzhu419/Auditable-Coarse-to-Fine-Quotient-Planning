from pathlib import Path

from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    SAME_IDENTITY_RERUN_FORBIDDEN,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v161_classifier_receipt_is_frozen_and_preserves_v160_failure():
    raw = (
        ROOT / ".tmp/exact-freeze/v161_paid_path_prefix_classifier_receipt.json"
    ).read_bytes()
    document = verify_frozen_paid_path_prefix_classifier_receipt_v161(raw)
    assert document["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
    assert document["derived_stable_prefix_observation_count"] == 7
    assert document["v160_failure_preserved_not_reclassified"] is True
    assert SAME_IDENTITY_RERUN_FORBIDDEN is True
