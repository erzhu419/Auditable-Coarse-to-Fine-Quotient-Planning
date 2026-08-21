import ast
from pathlib import Path

import pytest

from acfqp.construction_k7_reference_aligned_source_independent_verifier_v91 import (
    VERIFICATION_ID,
    ConstructionK7ReferenceAlignedSourceIndependentVerifierV91Error,
    verify_reference_aligned_source_campaign_bytes_v91,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v91_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(
        ConstructionK7ReferenceAlignedSourceIndependentVerifierV91Error
    ):
        verify_reference_aligned_source_campaign_bytes_v91(b"{}")


def test_v91_independent_verifier_has_no_campaign_producer_import():
    path = Path(
        "src/acfqp/construction_k7_reference_aligned_source_independent_verifier_v91.py"
    )
    imports = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        row.endswith("construction_k7_reference_aligned_source_campaign_v91")
        for row in imports
    )


def test_v91_independently_reconstructs_frozen_failure():
    raw = Path(
        ".tmp/exact-freeze/v91_reference_aligned_source_campaign.json"
    ).read_bytes()
    result = loads_canonical_json(
        verify_reference_aligned_source_campaign_bytes_v91(raw)
    )
    assert result["producer_free_pool_reconstruction"] is True
    assert result["producer_free_acquisition_reconstruction"] is True
    assert result["reference_alignment_success_verified"] is True
    assert result["heldout_terminal_failure_verified"] is True
    assert result["typed_result"] == "SOURCE_GATE_FAILURE_NONCERTIFICATE_VERIFIED"
    assert result["complete_world_model_synthesized"] is False


def test_v91_verification_identity_is_frozen():
    assert VERIFICATION_ID == (
        "cf5c159ba8fce9c347ec34458f48cf171aa01c753b41c9cf7e27b970176b4b72"
    )
