from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_fair_unified_factor_prior_ablation_campaign_v129r1 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v129r1_frozen_campaign_identity_sample_tax_and_claim_locks():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("registered V129r1 outcome has not been executed")
    raw = (ROOT / "v129r1_fair_unified_factor_prior_ablation_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document[
        "registered_workload_sample_efficiency_improvement_observed"
    ] is True
    assert document["accounting"]["acquisition_labels_avoided_by_factor_prior"] > 0
    assert document["failed_v129_identity_rerun"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
