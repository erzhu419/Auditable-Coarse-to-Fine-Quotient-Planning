from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_occurrence_factor_bank_update_planning_campaign_v143 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_RECORD_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v143_frozen_campaign_passes_registered_gate():
    if ATTEMPT_TERMINAL_STATE == "FROZEN_PREREGISTERED_RESOURCE_CAP_FAILURE":
        raw = (ROOT / "v143_occurrence_factor_bank_update_planning_failure.json").read_bytes()
        failure = loads_canonical_json(raw)
        assert hashlib.sha256(raw).hexdigest() == FAILURE_RECORD_SHA256
        assert failure["outcome_kind"] == "PREREGISTERED_RESOURCE_CAP_FAILURE"
        assert failure["error_type"] == (
            "OccurrenceFactorBankUpdateFactorAcquisitionV143Error"
        )
        assert failure["failed_family"] == "STOCHASTIC_DUAL_BUDGET_COMPOSITION"
        assert failure["failed_seed"] == 1_047_215
        assert failure["frozen_maximum_acquisition_labels"] == 768
        assert failure["same_identity_rerun_forbidden"] is True
        assert failure["official_scalar_cost"] is None
        return
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V143 campaign not frozen")
    raw = (ROOT / "v143_occurrence_factor_bank_update_planning_campaign.json").read_bytes()
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
