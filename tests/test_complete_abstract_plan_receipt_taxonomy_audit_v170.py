from pathlib import Path
import hashlib

from acfqp.complete_abstract_plan_receipt_taxonomy_audit_v170 import (
    AUDIT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    freeze_complete_abstract_plan_receipt_taxonomy_audit_v170,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _inputs():
    return (
        (FREEZE / "v170_complete_abstract_plan_receipt_taxonomy_contract.json").read_bytes(),
        (FREEZE / "v168_fifth_family_total_plan_receipt_set_campaign.json").read_bytes(),
    )


def test_v170_totalizes_every_plan_source_and_execution_join():
    document = freeze_complete_abstract_plan_receipt_taxonomy_audit_v170(
        *_inputs()
    ).to_document()
    assert document["typed_plan_receipt_count"] == 832
    assert document["execution_join_receipt_count"] == 112
    assert document["typed_plan_source_histogram"] == {
        "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE": 391,
        "DIRECT_COMPILED_PROGRAM_ORDER": 223,
        "OBSERVATION_DERIVED_QUOTIENT_ORDER": 208,
        "SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE": 10,
    }
    assert document["untyped_abstract_plan_receipt_count"] == 0
    assert document["unjoined_executed_action_count"] == 0
    assert document["registered_gate"]["passed"] is True
    assert document["taxonomy_is_model_or_safety_authority"] is False


def test_v170_frozen_audit_bytes():
    if AUDIT_ID == "0" * 64:
        return
    frozen = freeze_complete_abstract_plan_receipt_taxonomy_audit_v170(*_inputs())
    raw = (FREEZE / "v170_complete_abstract_plan_receipt_taxonomy_audit.json").read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.audit_id == AUDIT_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
