from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_plan_mode_margin_campaign_v157 import CAMPAIGN_ID, EXPECTED_CANONICAL_BYTE_COUNT, EXPECTED_CANONICAL_SHA256
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v157_frozen_campaign():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V157 campaign not frozen")
    raw = (ROOT / "v157_plan_mode_margin_campaign.json").read_bytes()
    campaign = loads_canonical_json(raw)
    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert campaign["registered_gate"]["passed"] is True
    assert campaign["registered_gate"]["both_registered_plan_modes_observed"] is True
    assert campaign["official_scalar_cost"] is None
