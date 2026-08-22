from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_cross_domain_relational_bank_campaign_v149 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v149_frozen_campaign_or_failure():
    if ATTEMPT_TERMINAL_STATE.startswith("FROZEN_PREREGISTERED_"):
        raw = (ROOT / "v149_cross_domain_relational_bank_failure.json").read_bytes()
        failure = loads_canonical_json(raw)
        assert FAILURE_RECORD_SHA256 is not None
        assert hashlib.sha256(raw).hexdigest() == FAILURE_RECORD_SHA256
        assert failure["same_identity_rerun_forbidden"] is True
        assert failure["official_scalar_cost"] is None
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V149 campaign not frozen")
    raw = (ROOT / "v149_cross_domain_relational_bank_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "every_family_has_positive_aggregate_reduction"
    ] is True
    assert document["relational_template_selection_itself_claimed_cross_domain"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
