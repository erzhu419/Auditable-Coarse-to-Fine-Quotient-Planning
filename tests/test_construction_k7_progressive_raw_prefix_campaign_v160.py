from pathlib import Path
import hashlib

from acfqp.construction_k7_progressive_raw_prefix_campaign_v160 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_BYTE_COUNT,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]


def test_v160_failed_campaign_and_exact_failure_are_frozen():
    raw = (
        ROOT / ".tmp/exact-freeze/v160_progressive_raw_prefix_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is False
    assert document["accounting"]["additional_classifier_only_target_labels"] == 0
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    failure_raw = (
        ROOT
        / ".tmp/exact-freeze/v160_progressive_raw_prefix_campaign_failure.json"
    ).read_bytes()
    failure = loads_canonical_json(failure_raw)
    assert len(failure_raw) == FAILURE_RECORD_BYTE_COUNT
    assert hashlib.sha256(failure_raw).hexdigest() == FAILURE_RECORD_SHA256
    assert failure["failed_campaign_id"] == CAMPAIGN_ID
    assert failure["same_identity_rerun_forbidden"] is True
    assert failure["failed_result_not_reclassified_as_success"] is True
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_FAILURE"
