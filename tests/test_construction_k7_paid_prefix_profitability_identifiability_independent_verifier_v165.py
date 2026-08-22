from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_paid_prefix_profitability_identifiability_independent_verifier_v165 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_paid_prefix_profitability_identifiability_verification_v165,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_paid_prefix_profitability_identifiability_verification_v165(
        (
            FREEZE / "v165_paid_prefix_profitability_identifiability_audit.json"
        ).read_bytes(),
        (FREEZE / "v163_safe_paid_path_sample_tax_campaign.json").read_bytes(),
        (FREEZE / "v163_safe_paid_path_sample_tax_verification.json").read_bytes(),
        (FREEZE / "v164_sample_tax_replication_campaign.json").read_bytes(),
        (FREEZE / "v164_sample_tax_replication_verification.json").read_bytes(),
    )


def test_v165_verifier_imports_no_target_producer_or_core():
    source = (
        ROOT
        / "src/acfqp/construction_k7_paid_prefix_profitability_identifiability_independent_verifier_v165.py"
    ).read_text()
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = (
        "paid_prefix_profitability_identifiability_core_v165",
        "construction_k7_paid_prefix_profitability_identifiability_audit_v165",
    )
    assert not any(
        any(fragment in name for fragment in forbidden) for name in imported
    )


def test_v165_frozen_producer_free_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V165 independent verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document[
        "registered_paid_prefix_nonidentifiability_independently_verified"
    ] is True
    assert document["new_target_observation_labels"] == 0
    assert document["official_scalar_cost"] is None
