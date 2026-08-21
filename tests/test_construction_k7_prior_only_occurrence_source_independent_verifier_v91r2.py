import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_prior_only_occurrence_source_independent_verifier_v91r2 as verifier
from acfqp.phase3e_ids import loads_canonical_json


def test_v91r2_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(
        verifier.ConstructionK7PriorOnlyOccurrenceSourceIndependentVerifierV91R2Error
    ):
        verifier.verify_prior_only_occurrence_source_campaign_bytes_v91r2(b"{}")


def test_v91r2_independent_verifier_has_no_campaign_producer_import():
    path = Path(
        "src/acfqp/construction_k7_prior_only_occurrence_source_independent_verifier_v91r2.py"
    )
    imports = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        row.endswith("construction_k7_prior_only_occurrence_source_campaign_v91r2")
        for row in imports
    )


def test_v91r2_independently_reconstructs_frozen_result():
    raw = Path(
        ".tmp/exact-freeze/v91r2_prior_only_occurrence_source_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(
        verifier.verify_prior_only_occurrence_source_campaign_bytes_v91r2(raw)
    )
    assert document["producer_free_pool_reconstruction"] is True
    assert document["producer_free_acquisition_reconstruction"] is True
    assert document["producer_free_model_reconstruction"] is True
    assert document["single_residual_proposal_gate_failure_verified"] is True
    assert document["typed_result"] == (
        "SOURCE_MODEL_COMPILED_MULTIPLICITY_GATE_FAILURE_VERIFIED"
    )


def test_v91r2_verification_identity_is_frozen():
    assert verifier.VERIFICATION_ID != "0" * 64
