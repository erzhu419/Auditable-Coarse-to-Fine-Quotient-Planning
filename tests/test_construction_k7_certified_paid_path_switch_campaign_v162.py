from pathlib import Path
import hashlib

from acfqp.construction_k7_certified_paid_path_switch_campaign_v162 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_BYTE_COUNT,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v162_failed_registered_gate_is_frozen_and_not_rerunnable():
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_FAILED_REGISTERED_GATE"
    campaign_raw = (
        FREEZE / "v162_certified_paid_path_switch_campaign.json"
    ).read_bytes()
    campaign = loads_canonical_json(campaign_raw)
    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert len(campaign_raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(campaign_raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert campaign["registered_gate"]["passed"] is False
    failure_raw = (
        FREEZE / "v162_certified_paid_path_switch_campaign_failure.json"
    ).read_bytes()
    failure = loads_canonical_json(failure_raw)
    assert len(failure_raw) == FAILURE_RECORD_BYTE_COUNT
    assert hashlib.sha256(failure_raw).hexdigest() == FAILURE_RECORD_SHA256
    assert failure["failed_campaign_id"] == CAMPAIGN_ID
    assert failure["failed_result_not_reclassified_as_success"] is True
    assert failure["observed_failure"] == (
        "PAID_RELATION_WITNESS_WAS_NOT_SUFFICIENT_TO_PREDICT_STRICT_QUERY_SAMPLE_REDUCTION"
    )
