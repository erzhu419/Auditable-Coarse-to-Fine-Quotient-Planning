from pathlib import Path
import hashlib

from acfqp.construction_k7_paid_path_continuation_campaign_v161 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    FAILED_PREREGISTRATION_ID,
    FAILURE_RECORD_BYTE_COUNT,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]


def test_v161_pre_document_failure_is_frozen_and_not_rerunnable():
    assert CAMPAIGN_ID == "0" * 64
    raw = (
        ROOT
        / ".tmp/exact-freeze/v161_paid_path_continuation_campaign_failure.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == FAILURE_RECORD_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == FAILURE_RECORD_SHA256
    assert document["preregistration_id"] == FAILED_PREREGISTRATION_ID
    assert document["terminal_state"] == "FAILED_NO_SAME_IDENTITY_RERUN"
    assert document["exception_type"] == "ValueError"
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_FAILURE_BEFORE_CAMPAIGN_DOCUMENT"
