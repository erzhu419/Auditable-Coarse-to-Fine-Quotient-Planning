import ast
import hashlib
from pathlib import Path

import pytest

from acfqp.construction_k7_complete_abstract_plan_receipt_taxonomy_independent_verifier_v170 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    ConstructionK7CompleteAbstractPlanReceiptTaxonomyIndependentVerifierV170Error,
    freeze_complete_abstract_plan_receipt_taxonomy_verification_v170,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _inputs(audit=None):
    return (
        (FREEZE / "v170_complete_abstract_plan_receipt_taxonomy_audit.json").read_bytes()
        if audit is None
        else audit,
        (FREEZE / "v170_complete_abstract_plan_receipt_taxonomy_contract.json").read_bytes(),
        (FREEZE / "v168_fifth_family_total_plan_receipt_set_campaign.json").read_bytes(),
    )


def test_v170_verifier_has_no_audit_producer_import():
    path = ROOT / "src/acfqp/construction_k7_complete_abstract_plan_receipt_taxonomy_independent_verifier_v170.py"
    tree = ast.parse(path.read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.complete_abstract_plan_receipt_taxonomy_audit_v170" not in imported


def test_v170_frozen_producer_free_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V170 verification not frozen")
    raw = freeze_complete_abstract_plan_receipt_taxonomy_verification_v170(*_inputs())
    frozen = (FREEZE / "v170_complete_abstract_plan_receipt_taxonomy_verification.json").read_bytes()
    assert raw == frozen
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["verified_typed_plan_receipt_count"] == 832
    assert document["verified_execution_join_receipt_count"] == 112
    assert document["unknown_plan_source_count"] == 0
    assert document["unjoined_executed_action_count"] == 0


def test_v170_rejects_resigned_typed_source_tamper():
    document = loads_canonical_json(_inputs()[0])
    document["episode_rows"][0]["typed_plan_receipts"][0][
        "typed_plan_source"
    ] = "FORGED"
    payload = {key: value for key, value in document.items() if key != "audit_id"}
    from acfqp import construction_k7_domain_registry_extension_v170 as domains

    document["audit_id"] = domains.extension_content_id_v170(
        domains.CONSTRUCTION_K7_AUDIT_V170_DOMAIN, payload
    )
    with pytest.raises(
        ConstructionK7CompleteAbstractPlanReceiptTaxonomyIndependentVerifierV170Error,
        match="frozen audit changed",
    ):
        freeze_complete_abstract_plan_receipt_taxonomy_verification_v170(
            *_inputs(canonical_json_bytes(document))
        )
