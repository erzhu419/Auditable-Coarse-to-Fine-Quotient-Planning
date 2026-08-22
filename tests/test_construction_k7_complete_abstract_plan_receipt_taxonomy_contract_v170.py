from pathlib import Path
import hashlib

from acfqp.construction_k7_complete_abstract_plan_receipt_taxonomy_contract_v170 import (
    CONTRACT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    freeze_complete_abstract_plan_receipt_taxonomy_contract_v170,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v170_contract_totalizes_four_sources_without_authority_change():
    document = freeze_complete_abstract_plan_receipt_taxonomy_contract_v170().to_document()
    assert len(document["finite_typed_taxonomy"]) == 4
    assert document["required_joins"][
        "every_abstract_plan_instance_has_exactly_one_typed_receipt"
    ] is True
    assert document["claim_boundary"]["taxonomy_changes_planning_or_execution"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v170_frozen_contract_bytes():
    if CONTRACT_ID == "0" * 64:
        return
    frozen = freeze_complete_abstract_plan_receipt_taxonomy_contract_v170()
    raw = (FREEZE / "v170_complete_abstract_plan_receipt_taxonomy_contract.json").read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.contract_id == CONTRACT_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
