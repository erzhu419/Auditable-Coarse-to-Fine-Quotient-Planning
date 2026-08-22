import hashlib

import pytest

from acfqp.construction_k7_fifth_family_total_plan_receipt_set_preregistration_v168 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    campaign_config_v168,
    freeze_fifth_family_total_plan_receipt_set_preregistration_v168,
)


def test_v168_preregistration_is_outcome_free_and_preserves_v167():
    frozen = freeze_fifth_family_total_plan_receipt_set_preregistration_v168()
    document = frozen.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["v168_fifth_family_transfer_observed"] is False
    assert document["receipt_set_totalization"]["finite_classes"] == [
        "DIRECT_ONLY",
        "MEMOIZED_ONLY",
        "MIXED",
        "NONE",
    ]
    assert document["receipt_set_totalization"]["empty_set_is_failure"] is False
    assert all(document["registered_gate"].values())
    assert len(TARGET_OCCURRENCES) == 2
    assert len({row[0] for row in TARGET_OCCURRENCES}) == 1
    assert campaign_config_v168()["target_worker_count"] == 2


def test_v168_frozen_preregistration_identity():
    if PREREGISTRATION_ID == "0" * 64:
        pytest.skip("V168 preregistration not frozen")
    frozen = freeze_fifth_family_total_plan_receipt_set_preregistration_v168()
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
