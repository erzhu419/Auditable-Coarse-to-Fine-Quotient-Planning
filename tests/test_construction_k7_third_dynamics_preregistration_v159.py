from pathlib import Path
import hashlib

from acfqp.construction_k7_third_dynamics_preregistration_v159 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_third_dynamics_preregistration_v159,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v159_third_dynamics_targets_are_frozen_before_outcomes():
    result = freeze_third_dynamics_preregistration_v159(
        (FREEZE / "v159_joint_factor_query_classifier_receipt.json").read_bytes()
    )
    document = result.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["target_worker_count"] == 2
    assert len(document["target_occurrences"]) == 4
    if PREREGISTRATION_ID != "0" * 64:
        raw = (FREEZE / "v159_third_dynamics_preregistration.json").read_bytes()
        assert result.canonical_bytes == raw
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
