from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_relation_keyed_bank_independent_verifier_v151 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_relation_keyed_bank_verification_v151,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run() -> bytes:
    return freeze_relation_keyed_bank_verification_v151(
        (FREEZE / "v151_relation_keyed_bank_campaign.json").read_bytes(),
        (FREEZE / "v151_relation_keyed_bank_preregistration.json").read_bytes(),
        (FREEZE / "v150_certified_planner_abstention_campaign.json").read_bytes(),
        (FREEZE / "v150_certified_planner_abstention_verification.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    )


def test_v151_verifier_has_no_producer_or_campaign_core_import():
    source = (ROOT / "src/acfqp/construction_k7_relation_keyed_bank_independent_verifier_v151.py").read_text()
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("relation_keyed_bank_campaign_v151" in name for name in imported)
    assert not any("relation_keyed_relational_bank_campaign_core_v151" in name for name in imported)


def test_v151_frozen_producer_free_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V151 verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["producer_free_relational_template_selection_reconstruction"] is True
    assert document["registered_relation_keyed_sample_efficiency_improvement_independently_verified"] is True
    assert document["official_scalar_cost"] is None
