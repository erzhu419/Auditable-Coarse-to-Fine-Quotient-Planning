from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_fourth_family_sample_tax_failure_v166 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_ID,
    freeze_fourth_family_sample_tax_failure_v166,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_fourth_family_sample_tax_failure_v166(
        (FREEZE / "v166_fourth_family_sample_tax_preregistration.json").read_bytes()
    )


def test_v166_failure_is_typed_and_forbids_same_identity_rerun():
    document = loads_canonical_json(_run())
    assert document["attempt_terminal_state"] == "FROZEN_PROTOCOL_FAILURE"
    assert document["primary_exception_type"] == "ValueError"
    assert document["same_identity_rerun_forbidden"] is True
    assert document["failed_result_not_reclassified_as_success"] is True
    assert document["durable_partial_occurrence_artifact_count"] == 0
    assert document["failed_occurrence_identity"]["occurrence_id"] is None
    assert document["registered_gate_evaluated"] is False


def test_v166_frozen_failure_identity():
    if FAILURE_ID == "0" * 64:
        pytest.skip("V166 failure not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["failure_id"] == FAILURE_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
