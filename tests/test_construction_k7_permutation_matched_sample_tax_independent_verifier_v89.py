import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_permutation_matched_sample_tax_independent_verifier_v89 import (
    VERIFICATION_ID,
    ConstructionK7PermutationMatchedSampleTaxIndependentVerifierV89Error,
    verify_permutation_matched_sample_tax_campaign_bytes_v89,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v89_verifier_rejects_foreign_bytes():
    with pytest.raises(
        ConstructionK7PermutationMatchedSampleTaxIndependentVerifierV89Error
    ):
        verify_permutation_matched_sample_tax_campaign_bytes_v89(b"{}")


def test_v89_verifier_has_no_campaign_or_permutation_producer_import():
    path = Path(
        "src/acfqp/construction_k7_permutation_matched_sample_tax_independent_verifier_v89.py"
    )
    imports = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("permutation_matched_sample_tax_campaign_v89" in row for row in imports)
    assert not any("permutation_matched_sample_tax_campaign_core_v89" in row for row in imports)
    assert not any("generic_action_key_permutation_adapter_v62" in row for row in imports)
    assert not any("generic_coordinate_alignment_v60" in row for row in imports)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PERMUTATION_MATCHED_V89") != "1",
    reason="explicit V89 producer-free reconstruction",
)
def test_v89_reconstructs_permutations_alignments_and_sample_reduction():
    raw = Path(
        ".tmp/exact-freeze/v89_permutation_matched_sample_tax_campaign.json"
    ).read_bytes()
    result = loads_canonical_json(
        verify_permutation_matched_sample_tax_campaign_bytes_v89(raw)
    )
    assert result["independently_rederived_permutation_count"] == 6
    assert result["independently_rederived_alignment_count"] == 6
    assert result["matched_ground_execution_verified"] is True
    assert result["sample_tax_reduction_verified"] is True
    assert result["target_labels_avoided"] == 157
    assert result["official_scalar_cost"] is None


def test_v89_verification_identity_is_frozen():
    assert VERIFICATION_ID == (
        "6dd9d5c1dab579ef7e0192bc64d486b82468e56a28d1d7a92595505c77dc8f39"
    )
