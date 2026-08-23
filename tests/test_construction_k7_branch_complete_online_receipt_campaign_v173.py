from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_branch_complete_online_receipt_campaign_v173 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILURE_ID,
    run_branch_complete_online_receipt_campaign_v173,
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
    )


def test_v173_frozen_campaign_is_branch_complete():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V173 campaign not frozen")
    raw = (FREEZE / "v173_branch_complete_online_receipt_campaign.json").read_bytes()
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
    assert document["official_scalar_cost"] is None
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_SUCCESS"


def test_v173_frozen_producer_refuses_rerun():
    with pytest.raises(ValueError, match="terminal"):
        run_branch_complete_online_receipt_campaign_v173(*_inputs())


def test_v173_failed_gate_is_frozen_without_subgate_invention():
    raw = (FREEZE / "v173_branch_complete_online_receipt_failure.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["failure_id"] == FAILURE_ID
    assert document["failure_class"] == "REGISTERED_SCIENTIFIC_GATE_FAILED"
    assert document["campaign_artifact_present"] is False
    assert document["inferred_failed_subgate"] is None
    assert document["same_preregistration_identity_may_be_rerun"] is False
