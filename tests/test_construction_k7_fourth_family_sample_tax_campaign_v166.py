from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_fourth_family_sample_tax_campaign_v166 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v166_attempt_state_is_explicit():
    assert ATTEMPT_TERMINAL_STATE in {
        "UNEXECUTED",
        "FROZEN_SUCCESS",
        "FROZEN_FAILURE",
    }
    if ATTEMPT_TERMINAL_STATE == "FROZEN_FAILURE":
        assert FAILURE_ID != "0" * 64


def test_v166_frozen_campaign_bytes():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V166 campaign not executed")
    raw = (FREEZE / "v166_fourth_family_sample_tax_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert canonical_json_bytes(document) == raw
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is (
        ATTEMPT_TERMINAL_STATE == "FROZEN_SUCCESS"
    )
