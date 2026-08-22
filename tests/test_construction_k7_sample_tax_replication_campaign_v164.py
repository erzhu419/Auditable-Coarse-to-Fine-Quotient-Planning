from pathlib import Path
import hashlib

from acfqp.construction_k7_sample_tax_replication_campaign_v164 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v164_formal_success_is_frozen_and_not_rerunnable():
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_SUCCESS"
    raw = (FREEZE / "v164_sample_tax_replication_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"][
        "total_query_policy_labels_avoided_vs_exact_path_first"
    ] == 88
    assert document["accounting"][
        "total_factor_prior_labels_avoided_within_same_query_policy"
    ] == 68
    assert document["official_execution_allowed"] is False
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
