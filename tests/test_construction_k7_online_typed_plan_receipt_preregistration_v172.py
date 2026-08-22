from pathlib import Path
import hashlib

from acfqp.construction_k7_online_typed_plan_receipt_preregistration_v172 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    freeze_online_typed_plan_receipt_preregistration_v172,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v172_preregistration_is_outcome_free_and_online_receipt_bound():
    document = freeze_online_typed_plan_receipt_preregistration_v172().to_document()
    assert len(TARGET_OCCURRENCES) == 2
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "each_abstract_plan_receipt_issued_before_orderer_return_required"
    ] is True
    assert document["registered_gate"][
        "each_executed_action_joined_to_prior_online_receipt_required"
    ] is True
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v172_frozen_preregistration_bytes():
    if PREREGISTRATION_ID == "0" * 64:
        return
    frozen = freeze_online_typed_plan_receipt_preregistration_v172()
    raw = (FREEZE / "v172_online_typed_plan_receipt_preregistration.json").read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
