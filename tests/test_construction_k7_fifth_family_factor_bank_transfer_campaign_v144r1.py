from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_fifth_family_factor_bank_transfer_campaign_v144r1 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v144r1_frozen_campaign_passes_registered_gate():
    if ATTEMPT_TERMINAL_STATE.startswith("FROZEN_PREREGISTERED_"):
        raw = (
            ROOT / "v144r1_fifth_family_factor_bank_transfer_failure.json"
        ).read_bytes()
        failure = loads_canonical_json(raw)
        assert FAILURE_RECORD_SHA256 is not None
        assert hashlib.sha256(raw).hexdigest() == FAILURE_RECORD_SHA256
        assert failure["preregistration_id"] == (
            "34beef0555332e3f95666007a587d9bfef465a82d1f5fed39eccc6d2511584c2"
        )
        assert failure["same_identity_rerun_forbidden"] is True
        assert failure["official_scalar_cost"] is None
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V144R1 campaign not frozen")
    raw = (
        ROOT / "v144r1_fifth_family_factor_bank_transfer_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "query_local_relational_overlay_exercised_at_least_once"
    ] is True
    assert document["registered_workload_sample_efficiency_improvement_observed"] is True
    assert document["query_local_overlay_promoted_to_global_dynamics"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
