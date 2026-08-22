from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_relation_coverage_campaign_v153 import ATTEMPT_TERMINAL_STATE, CAMPAIGN_ID, EXPECTED_CANONICAL_BYTE_COUNT, EXPECTED_CANONICAL_SHA256, FAILURE_RECORD_SHA256
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v153_frozen_campaign_or_failure():
    if ATTEMPT_TERMINAL_STATE.startswith("FROZEN_PREREGISTERED_"):
        raw = (ROOT / "v153_relation_coverage_failure.json").read_bytes()
        assert FAILURE_RECORD_SHA256 == hashlib.sha256(raw).hexdigest()
        assert loads_canonical_json(raw)["same_identity_rerun_forbidden"] is True
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V153 campaign not frozen")
    raw = (ROOT / "v153_relation_coverage_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["sample_tax_reduction_operator_observed"] is True
    assert document["official_scalar_cost"] is None
