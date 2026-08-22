from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_sixth_family_complete_plan_receipt_campaign_v171 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    run_sixth_family_complete_plan_receipt_campaign_v171,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _inputs():
    return (
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        (FREEZE / "v168_fifth_family_total_plan_receipt_set_campaign.json").read_bytes(),
        (FREEZE / "v170_complete_abstract_plan_receipt_taxonomy_audit.json").read_bytes(),
        (FREEZE / "v170_complete_abstract_plan_receipt_taxonomy_verification.json").read_bytes(),
    )


def test_v171_frozen_campaign_identity_and_gates():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V171 campaign not frozen")
    raw = (FREEZE / "v171_sixth_family_complete_plan_receipt_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "sixth_family_factor_prior_strictly_reduces_labels"
    ] is True
    assert document["registered_gate"]["every_abstract_plan_instance_typed"] is True
    assert document["registered_gate"]["every_executed_action_exactly_joined"] is True
    assert document["fresh_reservoir_accounting"][
        "total_factor_prior_labels_avoided_within_same_query_policy"
    ] > 0
    assert document["official_scalar_cost"] is None
    assert ATTEMPT_TERMINAL_STATE == "FROZEN_SUCCESS"


def test_v171_frozen_producer_refuses_rerun():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("V171 campaign not frozen")
    with pytest.raises(ValueError, match="terminal"):
        run_sixth_family_complete_plan_receipt_campaign_v171(*_inputs())
