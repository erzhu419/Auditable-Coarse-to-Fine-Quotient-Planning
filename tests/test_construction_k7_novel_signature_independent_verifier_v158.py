from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_novel_signature_independent_verifier_v158 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_novel_signature_verification_v158,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_novel_signature_verification_v158(
        (FREEZE / "v158_novel_signature_campaign.json").read_bytes(),
        (FREEZE / "v158_novel_signature_preregistration.json").read_bytes(),
        (FREEZE / "v158_anonymous_query_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        (FREEZE / "v157_plan_mode_margin_campaign.json").read_bytes(),
        (FREEZE / "v157_plan_mode_margin_verification.json").read_bytes(),
    )


def test_v158_verifier_imports_no_v158_producer_core_or_operator():
    source = (
        ROOT
        / "src/acfqp/construction_k7_novel_signature_independent_verifier_v158.py"
    ).read_text()
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = (
        "construction_k7_novel_signature_campaign_v158",
        "construction_k7_novel_signature_preregistration_v158",
        "novel_signature_campaign_core_v158",
        "classifier_guarded_acquisition_operator_v158",
        "anonymous_query_classifier_receipt_v158",
    )
    assert not any(
        any(fragment in name for fragment in forbidden) for name in imported
    )


def test_v158_frozen_independent_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V158 independent verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert (
        document[
            "novel_signature_classifier_sample_tax_evidence_independently_verified"
        ]
        is True
    )
    assert document["guard_sample_reduction_vs_legacy_prior"] == 428
    assert document["factor_prior_sample_reduction_within_guarded_operator"] == 28
    assert document["official_scalar_cost"] is None
