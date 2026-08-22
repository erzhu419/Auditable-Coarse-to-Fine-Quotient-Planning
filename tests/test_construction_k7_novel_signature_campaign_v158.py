from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_novel_signature_campaign_v158 import CAMPAIGN_ID, EXPECTED_CANONICAL_BYTE_COUNT, EXPECTED_CANONICAL_SHA256
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v158_frozen_campaign():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V158 campaign not frozen")
    raw = (ROOT / "v158_novel_signature_campaign.json").read_bytes(); campaign = loads_canonical_json(raw)
    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert campaign["registered_gate"]["passed"] is True
    assert campaign["registered_gate"]["all_target_exact_signatures_novel"] is True
    assert campaign["official_scalar_cost"] is None
