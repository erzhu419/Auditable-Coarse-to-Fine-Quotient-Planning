from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_fifth_family_factor_bank_transfer_campaign_v144r2 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v144r2_frozen_campaign_or_failure():
    if ATTEMPT_TERMINAL_STATE.startswith("FROZEN_PREREGISTERED_"):
        raw = (ROOT / "v144r2_fifth_family_factor_bank_transfer_failure.json").read_bytes()
        failure = loads_canonical_json(raw)
        assert FAILURE_RECORD_SHA256 is not None
        assert hashlib.sha256(raw).hexdigest() == FAILURE_RECORD_SHA256
        assert failure["preregistration_id"] == (
            "505c219aab3d82ecac7e1b65953e7c56045a56010c6304f35344c4f70249a03f"
        )
        assert failure["same_identity_rerun_forbidden"] is True
        assert failure["campaign_artifact_written"] is True
        assert failure["campaign_id"] == CAMPAIGN_ID
        assert failure["campaign_byte_count"] == EXPECTED_CANONICAL_BYTE_COUNT
        assert failure["campaign_sha256"] == EXPECTED_CANONICAL_SHA256
        assert failure["registered_gate"]["passed"] is False
        assert failure["aggregate_sample_labels_avoided"] == 63
        assert failure["certificate_failure_local_ground_labels"] == 79
        assert failure["query_local_exact_overlay_edge_count"] == 0
        assert failure["observed_local_recovery_branch"] == (
            "PROGRAM_COMPATIBLE_INCREMENTAL_REFINEMENT_ONLY"
        )
        assert failure["official_scalar_cost"] is None
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V144R2 campaign not frozen")
    raw = (ROOT / "v144r2_fifth_family_factor_bank_transfer_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "query_local_relational_overlay_exercised_at_least_once"
    ] is True
    assert document["registered_gate"]["fresh_longer_receding_stress_executed"] is True
    assert document["registered_workload_sample_efficiency_improvement_observed"] is True
    assert document["query_local_overlay_promoted_to_global_dynamics"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
