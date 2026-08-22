from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_third_dynamics_campaign_v159 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v159_frozen_third_dynamics_campaign():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V159 campaign not frozen")
    raw = (FREEZE / "v159_third_dynamics_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["third_genuinely_distinct_partial_stochastic_dynamics_verified"] is True
    assert document["official_scalar_cost"] is None
