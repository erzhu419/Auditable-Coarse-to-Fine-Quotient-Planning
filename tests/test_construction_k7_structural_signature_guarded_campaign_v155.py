from pathlib import Path

import pytest

from acfqp.construction_k7_structural_signature_guarded_campaign_v155 import (
    CAMPAIGN_ID,
    run_structural_signature_guarded_campaign_v155,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v155_frozen_campaign():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V155 campaign not frozen")
    campaign = run_structural_signature_guarded_campaign_v155(
        (ROOT / "v155_structural_signature_query_guard_receipt.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    ).to_document()
    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert campaign["registered_gate"]["passed"] is True
    assert campaign["registered_gate"]["zero_guard_regression_everywhere"] is True
    assert campaign["official_scalar_cost"] is None
