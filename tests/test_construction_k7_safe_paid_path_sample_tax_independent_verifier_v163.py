from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_safe_paid_path_sample_tax_independent_verifier_v163 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_safe_paid_path_sample_tax_verification_v163,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_safe_paid_path_sample_tax_verification_v163(
        (FREEZE / "v163_safe_paid_path_sample_tax_campaign.json").read_bytes(),
        (FREEZE / "v163_safe_paid_path_sample_tax_preregistration.json").read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        (
            FREEZE / "v162_certified_paid_path_switch_campaign_failure.json"
        ).read_bytes(),
    )


def test_v163_verifier_imports_no_v163_or_v162_target_producer():
    source = (
        ROOT
        / "src/acfqp/construction_k7_safe_paid_path_sample_tax_independent_verifier_v163.py"
    ).read_text()
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = (
        "construction_k7_safe_paid_path_sample_tax_campaign_v163",
        "construction_k7_safe_paid_path_sample_tax_preregistration_v163",
        "safe_paid_path_sample_tax_campaign_core_v163",
        "certified_paid_path_switch_campaign_core_v162",
        "certified_paid_path_switch_acquisition_operator_v162",
    )
    assert not any(
        any(fragment in name for fragment in forbidden) for name in imported
    )


def test_v163_frozen_independent_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V163 independent verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document[
        "safe_query_and_factor_prior_sample_tax_evidence_independently_verified"
    ] is True
    assert document["query_policy_labels_avoided_vs_exact_path_first"] == 49
    assert document["factor_prior_labels_avoided_within_same_query_policy"] == 43
    assert document["official_scalar_cost"] is None
