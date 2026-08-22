import hashlib

import pytest

from acfqp.construction_k7_paid_path_prefix_source_preregistration_v161 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    SOURCE_PREREGISTRATION_ID,
    freeze_paid_path_prefix_source_preregistration_v161,
)


def test_v161_source_preregistration_freezes_v160_failure_before_correction():
    if SOURCE_PREREGISTRATION_ID == "0" * 64:
        pytest.skip("V161 source preregistration not frozen")
    r = freeze_paid_path_prefix_source_preregistration_v161()
    d = r.to_document()
    assert r.source_preregistration_id == SOURCE_PREREGISTRATION_ID
    assert len(r.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(r.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert d["registered_source_gate"][
        "safe_fallback_must_resume_the_same_generator_object"
    ] is True
    assert d["claim_boundary"]["v160_failure_reclassified_as_success"] is False
