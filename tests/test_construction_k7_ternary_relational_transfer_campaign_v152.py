from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_ternary_relational_transfer_campaign_v152 import ATTEMPT_TERMINAL_STATE, CAMPAIGN_ID, EXPECTED_CANONICAL_BYTE_COUNT, EXPECTED_CANONICAL_SHA256, FAILURE_RECORD_SHA256
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v152_frozen_campaign_or_failure():
    if ATTEMPT_TERMINAL_STATE.startswith("FROZEN_PREREGISTERED_"):
        raw = (ROOT / "v152_ternary_relational_transfer_failure.json").read_bytes()
        failure = loads_canonical_json(raw)
        assert FAILURE_RECORD_SHA256 is not None
        assert hashlib.sha256(raw).hexdigest() == FAILURE_RECORD_SHA256
        assert failure["same_identity_rerun_forbidden"] is True
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V152 campaign not frozen")
    raw = (ROOT / "v152_ternary_relational_transfer_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["changed_relation_cardinality_transfer_everywhere"] is True
    assert document["official_scalar_cost"] is None
