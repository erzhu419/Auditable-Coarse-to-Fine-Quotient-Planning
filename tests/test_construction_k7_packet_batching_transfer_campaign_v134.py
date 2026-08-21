from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_packet_batching_transfer_campaign_v134 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@pytest.mark.skipif(CAMPAIGN_ID == "0" * 64, reason="V134 campaign not frozen")
def test_v134_frozen_source_unseen_campaign_passes():
    raw = (ROOT / "v134_packet_batching_transfer_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document[
        "registered_source_unseen_domain_sample_efficiency_improvement_observed"
    ] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
