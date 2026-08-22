from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_structural_signature_guarded_independent_verifier_v155 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_structural_signature_guarded_verification_v155,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_structural_signature_guarded_verification_v155(
        (FREEZE / "v155_structural_signature_guarded_campaign.json").read_bytes(),
        (FREEZE / "v155_structural_signature_guarded_preregistration.json").read_bytes(),
        (FREEZE / "v155_structural_signature_query_guard_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        (FREEZE / "v153_relation_coverage_campaign.json").read_bytes(),
        (FREEZE / "v153_relation_coverage_verification.json").read_bytes(),
        (FREEZE / "v154_relation_coverage_cross_structure_campaign.json").read_bytes(),
        (FREEZE / "v154_relation_coverage_cross_structure_failure.json").read_bytes(),
    )


def test_v155_verifier_imports_no_v155_producer_core_or_operator():
    source = (
        ROOT
        / "src/acfqp/construction_k7_structural_signature_guarded_independent_verifier_v155.py"
    ).read_text()
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("construction_k7_structural_signature_guarded_campaign_v155" in name for name in imported)
    assert not any("structural_signature_guarded_campaign_core_v155" in name for name in imported)
    assert not any("structural_signature_guarded_acquisition_operator_v155" in name for name in imported)


def test_v155_frozen_independent_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V155 independent verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_structural_guard_prevented_regression_independently_verified"] is True
    assert document["guard_sample_reduction_vs_legacy_prior"] == 0
    assert document["factor_prior_sample_reduction_within_guarded_operator"] == 10
    assert document["official_scalar_cost"] is None
