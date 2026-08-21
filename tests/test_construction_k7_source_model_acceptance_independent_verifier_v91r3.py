import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_source_model_acceptance_independent_verifier_v91r3 as verifier
from acfqp.phase3e_ids import loads_canonical_json


def test_v91r3_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(
        verifier.ConstructionK7SourceModelAcceptanceIndependentVerifierV91R3Error
    ):
        verifier.verify_source_model_acceptance_bytes_v91r3(b"{}")


def test_v91r3_independent_verifier_has_no_acceptance_producer_import():
    path = Path(
        "src/acfqp/construction_k7_source_model_acceptance_independent_verifier_v91r3.py"
    )
    imports = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        row.endswith("construction_k7_source_model_acceptance_v91r3")
        for row in imports
    )


def test_v91r3_independently_verifies_corrected_gate():
    raw = Path(
        ".tmp/exact-freeze/v91r3_source_model_acceptance.json"
    ).read_bytes()
    result = loads_canonical_json(
        verifier.verify_source_model_acceptance_bytes_v91r3(raw)
    )
    assert result["complete_version_space_retention_verified"] is True
    assert result["singleton_without_synthetic_uncertainty_verified"] is True
    assert result["typed_result"] == "SOURCE_MODEL_ACCEPTED_FOR_TARGET_PLANNING"


def test_v91r3_verification_identity_is_frozen():
    assert verifier.VERIFICATION_ID != "0" * 64
