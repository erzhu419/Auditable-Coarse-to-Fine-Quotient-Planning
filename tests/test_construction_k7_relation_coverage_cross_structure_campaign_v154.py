from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_relation_coverage_cross_structure_campaign_v154 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v154_frozen_campaign():
    if ATTEMPT_TERMINAL_STATE.startswith("FROZEN_PREREGISTERED_"):
        failure_raw = (
            ROOT / "v154_relation_coverage_cross_structure_failure.json"
        ).read_bytes()
        failure = loads_canonical_json(failure_raw)
        campaign_raw = (
            ROOT / "v154_relation_coverage_cross_structure_campaign.json"
        ).read_bytes()
        campaign = loads_canonical_json(campaign_raw)
        assert hashlib.sha256(failure_raw).hexdigest() == FAILURE_RECORD_SHA256
        assert campaign["campaign_id"] == CAMPAIGN_ID
        assert len(campaign_raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(campaign_raw).hexdigest() == EXPECTED_CANONICAL_SHA256
        assert campaign["registered_gate"]["passed"] is False
        assert failure["same_identity_rerun_forbidden"] is True
        assert failure["fresh_successor_identity_required_for_any_correction"] is True
        assert failure["official_scalar_cost"] is None
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V154 campaign not frozen")
    campaign = loads_canonical_json(
        (ROOT / "v154_relation_coverage_cross_structure_campaign.json").read_bytes()
    )
    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert campaign["registered_gate"]["passed"] is True
    assert campaign["registered_gate"]["nonrelational_ood_rejected_everywhere"] is True
    assert campaign["official_scalar_cost"] is None
