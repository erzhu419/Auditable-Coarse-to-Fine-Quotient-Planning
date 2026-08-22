from pathlib import Path

import pytest

from acfqp.construction_k7_progressive_raw_prefix_campaign_v160 import (
    CAMPAIGN_ID,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]


def test_v160_frozen_campaign_gate_and_claim_boundaries():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V160 target campaign not frozen")
    document = loads_canonical_json(
        (ROOT / ".tmp/exact-freeze/v160_progressive_raw_prefix_campaign.json").read_bytes()
    )
    assert document["campaign_id"] == CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["named_initial_catalogue_support_scaffold_removed"] is True
    assert document["accounting"]["additional_classifier_only_target_labels"] == 0
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
