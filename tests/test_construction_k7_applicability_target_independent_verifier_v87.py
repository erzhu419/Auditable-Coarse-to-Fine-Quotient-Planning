import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_applicability_target_independent_verifier_v87 import (
    VERIFICATION_ID,
    ConstructionK7ApplicabilityTargetIndependentVerifierV87Error,
    verify_applicability_target_campaign_bytes_v87,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v87_failure_verifier_rejects_foreign_bytes():
    with pytest.raises(ConstructionK7ApplicabilityTargetIndependentVerifierV87Error):
        verify_applicability_target_campaign_bytes_v87(b"{}")


def test_v87_failure_verifier_import_surface_excludes_producers():
    path = Path(
        "src/acfqp/construction_k7_applicability_target_independent_verifier_v87.py"
    )
    tree = ast.parse(path.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        "applicability_target_campaign" in row
        or "generic_applicability" in row
        or "true_bit_symmetric" in row
        for row in imports
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_APPLICABILITY_TARGET_V87") != "1",
    reason="explicit producer-free V87 failure reconstruction",
)
def test_v87_failure_verifier_reconstructs_exact_failure():
    raw = Path(
        ".tmp/exact-freeze/v87_applicability_target_campaign.json"
    ).read_bytes()
    verification = loads_canonical_json(
        verify_applicability_target_campaign_bytes_v87(raw)
    )
    assert verification["target_occurrence_count"] == 6
    assert verification["structurally_compatible_target_count"] == 0
    assert verification["matched_target_episode_count"] == 0
    assert verification["all_incompatible_targets_retained_without_episode"] is True
    assert verification["registered_failure_gate_verified"] is True
    assert verification["sample_tax_reduction_verified"] is False
    assert verification["official_scalar_cost"] is None


def test_v87_failure_verification_identity_is_frozen():
    assert VERIFICATION_ID == (
        "d8af2766c723c1b42895f9c4b5d85e2557c366af2ab6473f19516c9b54fe19d5"
    )
