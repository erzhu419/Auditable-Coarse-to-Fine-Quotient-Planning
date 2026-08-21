import ast
from pathlib import Path

import pytest

from acfqp.construction_k7_abstract_planning_primary_independent_verifier_v90 import (
    VERIFICATION_ID,
    ConstructionK7AbstractPlanningPrimaryIndependentVerifierV90Error,
    verify_abstract_planning_primary_audit_bytes_v90,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v90_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(
        ConstructionK7AbstractPlanningPrimaryIndependentVerifierV90Error
    ):
        verify_abstract_planning_primary_audit_bytes_v90(b"{}", b"{}")


def test_v90_independent_verifier_has_no_v90_producer_import():
    path = Path(
        "src/acfqp/construction_k7_abstract_planning_primary_independent_verifier_v90.py"
    )
    imports = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        row.endswith("construction_k7_abstract_planning_primary_audit_v90")
        for row in imports
    )


def test_v90_independently_reconstructs_complete_audit():
    campaign = Path(
        ".tmp/exact-freeze/v89_permutation_matched_sample_tax_campaign.json"
    ).read_bytes()
    audit = Path(
        "artifacts/world_model/v90_abstract_planning_primary_audit.json"
    ).read_bytes()
    result = loads_canonical_json(
        verify_abstract_planning_primary_audit_bytes_v90(campaign, audit)
    )
    assert result["producer_free_exact_reconstruction"] is True
    assert result["replayed_abstract_plan_count"] == 264
    assert result["proposal_mismatch_count"] == 0
    assert result["non_proposed_ground_action_query_count"] == 0
    assert result["multi_step_planning_primarily_in_abstract_model_verified"] is True
    assert result["official_scalar_cost"] is None


def test_v90_verification_identity_is_frozen():
    assert (
        VERIFICATION_ID
        == "9e98d0c4d4d63b87f5dbad9a21ff61f5509e38f63f08733981dfbe0eb7d5926c"
    )
