from pathlib import Path

import pytest

from acfqp.construction_k7_paid_path_continuation_campaign_v161 import CAMPAIGN_ID
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]


def test_v161_frozen_campaign_gate_and_claim_boundaries():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V161 target campaign not frozen")
    document = loads_canonical_json(
        (ROOT / ".tmp/exact-freeze/v161_paid_path_continuation_campaign.json").read_bytes()
    )
    assert document["campaign_id"] == CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "fallback_and_modular_are_exact_zero_regression_everywhere"
    ] is True
    assert document["v160_failure_preserved_not_reclassified"] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
