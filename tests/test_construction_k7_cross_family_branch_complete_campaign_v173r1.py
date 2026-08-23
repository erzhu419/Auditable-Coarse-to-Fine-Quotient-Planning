from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_cross_family_branch_complete_campaign_v173r1 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    run_cross_family_branch_complete_campaign_v173r1,
)
from acfqp.phase3e_ids import loads_canonical_json


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    return (
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        (FREEZE / "v172r1_online_typed_plan_receipt_campaign.json").read_bytes(),
        (
            FREEZE / "v172r1_online_typed_plan_receipt_verification.json"
        ).read_bytes(),
        (FREEZE / "v173_branch_complete_online_receipt_failure.json").read_bytes(),
    )


def test_v173r1_frozen_campaign_covers_all_sources():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V173r1 campaign not frozen")
    raw = (FREEZE / "v173r1_cross_family_branch_complete_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "all_four_online_typed_plan_sources_observed"
    ] is True
    assert all(
        count > 0 for count in document["online_typed_plan_source_histogram"].values()
    )
    assert document["accounting"]["factor_prior_labels_avoided"] > 0
    assert document["official_scalar_cost"] is None
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_SUCCESS"


def test_v173r1_frozen_producer_refuses_rerun():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V173r1 campaign not frozen")
    with pytest.raises(ValueError, match="terminal"):
        run_cross_family_branch_complete_campaign_v173r1(*_inputs())
