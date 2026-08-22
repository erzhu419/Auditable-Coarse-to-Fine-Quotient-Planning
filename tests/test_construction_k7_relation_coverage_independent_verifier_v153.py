from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_relation_coverage_independent_verifier_v153 import EXPECTED_CANONICAL_BYTE_COUNT, EXPECTED_CANONICAL_SHA256, VERIFICATION_ID, freeze_relation_coverage_verification_v153
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_relation_coverage_verification_v153(
        (FREEZE / "v153_relation_coverage_campaign.json").read_bytes(),
        (FREEZE / "v153_relation_coverage_preregistration.json").read_bytes(),
        (FREEZE / "v153_relation_coverage_operator_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    )


def test_v153_verifier_imports_no_v153_producer_core_or_operator():
    source = (ROOT / "src/acfqp/construction_k7_relation_coverage_independent_verifier_v153.py").read_text()
    imported = {node.module or "" for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)}
    assert not any("relation_coverage_campaign_v153" in name for name in imported)
    assert not any("relation_coverage_planning_campaign_core_v153" in name for name in imported)
    assert not any("relation_coverage_acquisition_operator_v153" in name for name in imported)


def test_v153_frozen_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V153 verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_operator_sample_tax_reduction_independently_verified"] is True
    assert document["official_scalar_cost"] is None
