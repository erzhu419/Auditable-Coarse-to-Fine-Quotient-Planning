from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_structural_margin_guarded_campaign_v156 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
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
    assert campaign["registered_gate"]["passed"] is True
    assert campaign["registered_gate"]["exact_signature_registry_absent_everywhere"] is True
    assert campaign["official_scalar_cost"] is None
