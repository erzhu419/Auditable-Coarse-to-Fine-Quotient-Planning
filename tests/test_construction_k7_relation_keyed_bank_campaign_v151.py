from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_relation_keyed_bank_campaign_v151 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v151_frozen_campaign_or_failure():
    if ATTEMPT_TERMINAL_STATE.startswith("FROZEN_PREREGISTERED_"):
        raw = (ROOT / "v151_relation_keyed_bank_failure.json").read_bytes()
        failure = loads_canonical_json(raw)
        assert FAILURE_RECORD_SHA256 is not None
        assert hashlib.sha256(raw).hexdigest() == FAILURE_RECORD_SHA256
        assert failure["same_identity_rerun_forbidden"] is True
        assert failure["official_scalar_cost"] is None
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V151 campaign not frozen")
    raw = (ROOT / "v151_relation_keyed_bank_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "relational_artifact_selected_in_prior_everywhere"
    ] is True
    assert document["relational_template_selection_itself_claimed_cross_domain"] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
