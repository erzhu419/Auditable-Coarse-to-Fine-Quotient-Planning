from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_sample_tax_replication_independent_verifier_v164 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_sample_tax_replication_verification_v164,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_sample_tax_replication_verification_v164(
        (FREEZE / "v164_sample_tax_replication_campaign.json").read_bytes(),
        (FREEZE / "v164_sample_tax_replication_preregistration.json").read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        (
            FREEZE / "v162_certified_paid_path_switch_campaign_failure.json"
        ).read_bytes(),
        (FREEZE / "v163_safe_paid_path_sample_tax_campaign.json").read_bytes(),
        (FREEZE / "v163_safe_paid_path_sample_tax_verification.json").read_bytes(),
    )


def test_v164_verifier_imports_no_v164_target_producer():
    source = (
        ROOT
        / "src/acfqp/construction_k7_sample_tax_replication_independent_verifier_v164.py"
    ).read_text()
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = (
        "construction_k7_sample_tax_replication_campaign_v164",
        "construction_k7_sample_tax_replication_preregistration_v164",
        "sample_tax_replication_campaign_core_v164",
    )
    assert not any(
        any(fragment in name for fragment in forbidden) for name in imported
    )


def test_v164_frozen_independent_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V164 independent verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document[
        "query_and_factor_prior_sample_tax_replication_independently_verified"
    ] is True
    assert document["query_policy_labels_avoided_vs_exact_path_first"] == 88
    assert document["factor_prior_labels_avoided_within_same_query_policy"] == 68
    assert document["official_scalar_cost"] is None
