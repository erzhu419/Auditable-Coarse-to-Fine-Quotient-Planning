from pathlib import Path

import pytest

from acfqp.construction_k7_relation_coverage_cross_structure_campaign_v154 import (
    CAMPAIGN_ID,
    run_relation_coverage_cross_structure_campaign_v154,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v154_frozen_campaign():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V154 campaign not frozen")
    campaign = run_relation_coverage_cross_structure_campaign_v154(
        (ROOT / "v154_relation_coverage_application_receipt.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    ).to_document()
    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert campaign["registered_gate"]["passed"] is True
    assert campaign["registered_gate"]["nonrelational_ood_rejected_everywhere"] is True
    assert campaign["official_scalar_cost"] is None
