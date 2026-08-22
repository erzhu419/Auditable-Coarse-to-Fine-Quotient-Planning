from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_structural_margin_guarded_campaign_v156 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_BYTE_COUNT,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v156_frozen_campaign():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V156 campaign not frozen")
    raw = (ROOT / "v156_structural_margin_guarded_campaign.json").read_bytes()
    campaign = loads_canonical_json(raw)
    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_PREREGISTERED_GATE_FAILURE"
    assert campaign["registered_gate"]["passed"] is False
    assert campaign["registered_gate"]["exact_signature_registry_absent_everywhere"] is True
    failure_raw = (ROOT / "v156_structural_margin_guarded_failure.json").read_bytes()
    failure = loads_canonical_json(failure_raw)
    assert len(failure_raw) == FAILURE_RECORD_BYTE_COUNT
    assert hashlib.sha256(failure_raw).hexdigest() == FAILURE_RECORD_SHA256
    assert failure["campaign_id"] == CAMPAIGN_ID
    assert failure["same_identity_rerun_forbidden"] is True
    assert failure["fresh_successor_identity_required_for_any_correction"] is True
    assert campaign["official_scalar_cost"] is None
