from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_ternary_relational_transfer_independent_verifier_v152 import EXPECTED_CANONICAL_BYTE_COUNT, EXPECTED_CANONICAL_SHA256, VERIFICATION_ID, freeze_ternary_relational_transfer_verification_v152
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_ternary_relational_transfer_verification_v152(
        (FREEZE / "v152_ternary_relational_transfer_campaign.json").read_bytes(),
        (FREEZE / "v152_ternary_relational_transfer_preregistration.json").read_bytes(),
        (FREEZE / "v151_relation_keyed_bank_campaign.json").read_bytes(),
        (FREEZE / "v151_relation_keyed_bank_verification.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    )


def test_v152_verifier_imports_no_v152_producer_or_core():
    source = (ROOT / "src/acfqp/construction_k7_ternary_relational_transfer_independent_verifier_v152.py").read_text()
    imported = {node.module or "" for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)}
    assert not any("ternary_relational_transfer_campaign_v152" in name for name in imported)
    assert not any("ternary_relational_transfer_campaign_core_v152" in name for name in imported)


def test_v152_frozen_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V152 verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["producer_free_changed_cardinality_template_selection_reconstruction"] is True
    assert document["official_scalar_cost"] is None
