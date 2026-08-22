from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_fifth_family_factor_bank_transfer_campaign_v144 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v144_frozen_campaign_passes_registered_gate():
    if ATTEMPT_TERMINAL_STATE.startswith("FROZEN_PREREGISTERED_"):
        raw = (
            ROOT / "v144_fifth_family_factor_bank_transfer_failure.json"
        ).read_bytes()
        failure = loads_canonical_json(raw)
        assert hashlib.sha256(raw).hexdigest() == FAILURE_RECORD_SHA256
        assert failure["preregistration_id"] == (
            "f2e114e4c00b6a98475cd7548e1d4f3301c76204864453183cdf0df8903f9f38"
        )
        assert failure["outcome_kind"] == (
            "PREREGISTERED_INCREMENTAL_RELATIONAL_PROJECTION_FAILURE"
        )
        assert failure["error_type"] == "GenericCompiledQuotientModelV123Error"
        assert failure["failed_seed"] is None
        assert failure["process_pool_trace_exposed_failed_seed"] is False
        assert failure["failure_reveals_post_certificate_relation_binding_nonclosure"] is True
        assert failure["same_identity_rerun_forbidden"] is True
        assert failure["official_scalar_cost"] is None
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V144 campaign not frozen")
    raw = (
        ROOT / "v144_fifth_family_factor_bank_transfer_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document[
        "registered_workload_sample_efficiency_improvement_observed"
    ] is True
    assert document["fixed_source_campaign_inventory_reintroduced"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
