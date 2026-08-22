from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_anonymous_relational_factor_bank_independent_verifier_v146 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_anonymous_relational_factor_bank_verification_v146,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_anonymous_relational_factor_bank_verification_v146(
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v145_certificate_local_recovery_union_campaign.json").read_bytes(),
        (ROOT / "v145_certificate_local_recovery_union_verification.json").read_bytes(),
    )


def test_v146_independently_reconstructs_alpha_normalized_relational_bank():
    document = loads_canonical_json(_freeze())
    assert document["verified_source_occurrence_count"] == 6
    assert document["verified_selected_template_count"] == 6
    assert document["verified_selected_relational_template_count"] == 1
    assert document[
        "producer_free_constant_relation_and_coordinate_alpha_normalization"
    ] is True
    assert document["producer_free_support_threshold_and_mdl_selection"] is True
    assert document["new_target_outcomes_accessed"] is False
    assert document["relational_instantiator_execution_claimed"] is False
    assert document["official_scalar_cost"] is None


def test_v146_verifier_does_not_import_bank_producer():
    path = Path(__file__).resolve().parents[1] / "src/acfqp/construction_k7_anonymous_relational_factor_bank_independent_verifier_v146.py"
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(name.endswith("anonymous_relational_factor_bank_v146") for name in imported)


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V146 verification not frozen")
def test_v146_frozen_verification_bytes():
    raw = (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
