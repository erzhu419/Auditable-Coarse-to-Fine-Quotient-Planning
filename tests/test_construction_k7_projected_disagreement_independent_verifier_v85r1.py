import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_projected_disagreement_independent_verifier_v85r1 import (
    VERIFICATION_ID,
    ConstructionK7ProjectedDisagreementIndependentVerifierV85R1Error,
    verify_projected_disagreement_campaign_bytes_v85r1,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v85r1_independent_verifier_rejects_foreign_bytes():
    assert VERIFICATION_ID == (
        "391038636f3b1744112f1a4a08b9d4acb5d32f8d19c27af603e69431cd40ad0f"
    )
    with pytest.raises(
        ConstructionK7ProjectedDisagreementIndependentVerifierV85R1Error
    ):
        verify_projected_disagreement_campaign_bytes_v85r1(b"{}")


def test_v85r1_independent_verifier_import_surface_excludes_producers():
    path = Path(
        "src/acfqp/construction_k7_projected_disagreement_independent_verifier_v85r1.py"
    )
    tree = ast.parse(path.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = (
        "construction_k7_projected_disagreement_campaign_v85r1",
        "projected_disagreement_source_campaign_core",
        "generic_projected_disagreement_acquisition",
        "generic_projected_disagreement_model_compiler",
        "generic_projected_disagreement_planner",
        "generic_contextual_ordinal",
    )
    assert not any(any(name in row for name in forbidden) for row in imports)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PROJECTED_DISAGREEMENT_V85R1") != "1",
    reason="explicit producer-free V85r1 reconstruction",
)
def test_v85r1_independent_verifier_reconstructs_frozen_campaign():
    raw = Path(
        ".tmp/exact-freeze/v85r1_projected_disagreement_campaign.json"
    ).read_bytes()
    verification = loads_canonical_json(
        verify_projected_disagreement_campaign_bytes_v85r1(raw)
    )
    assert verification["source_member_count"] == 6
    assert verification["compiled_model_count"] == 1
    assert verification["compiled_source_member_count"] == 4
    assert verification["partial_residual_and_terminal_components_replayed_on_full_sources"] is True
    assert verification["fresh_target_outcome_count"] == 0
    assert verification["sample_tax_reduction_verified"] is False
    assert verification["official_scalar_cost"] is None
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
