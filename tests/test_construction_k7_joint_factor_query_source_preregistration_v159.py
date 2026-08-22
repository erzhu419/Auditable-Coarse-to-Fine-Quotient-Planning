from pathlib import Path
import hashlib

from acfqp.construction_k7_joint_factor_query_source_preregistration_v159 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    SOURCE_CALIBRATION_SEEDS,
    SOURCE_PREREGISTRATION_ID,
    freeze_joint_factor_query_source_preregistration_v159,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v159_source_is_preregistered_before_factorization_outcomes():
    result = freeze_joint_factor_query_source_preregistration_v159()
    document = result.to_document()
    assert document["source_calibration_seeds"] == list(SOURCE_CALIBRATION_SEEDS)
    assert document["claim_boundary"]["source_outcomes_accessed"] is False
    assert document["claim_boundary"]["fresh_v159_target_outcomes_accessed"] is False
    if SOURCE_PREREGISTRATION_ID != "0" * 64:
        raw = (FREEZE / "v159_joint_factor_query_source_preregistration.json").read_bytes()
        assert result.canonical_bytes == raw
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
