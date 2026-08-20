import ast
import os
from pathlib import Path

import pytest


def test_v71_independent_verifier_import_surface_excludes_the_producer_path():
    path = Path(
        "src/acfqp/construction_k7_role_free_prequential_independent_verifier_v71.py"
    )
    tree = ast.parse(path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = (
        "construction_k7_role_free_prequential_campaign_v71",
        "role_free_prequential_campaign_core_v71",
        "generic_role_free_acquisition_operator_v36",
        "generic_prequential_role_free_acquisition_v37",
    )
    assert not any(any(name.endswith(value) for value in forbidden) for name in imported)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V71") != "1",
    reason="explicit retained V71 producer-free replay",
)
def test_v71_frozen_campaign_is_reconstructed_without_its_producer():
    from acfqp.construction_k7_role_free_prequential_campaign_v71 import (
        run_role_free_prequential_campaign_v71,
    )
    from acfqp.construction_k7_role_free_prequential_independent_verifier_v71 import (
        verify_role_free_prequential_campaign_bytes_v71,
    )
    from acfqp.phase3e_ids import loads_canonical_json

    campaign = run_role_free_prequential_campaign_v71()
    raw = verify_role_free_prequential_campaign_bytes_v71(campaign.canonical_bytes)
    document = loads_canonical_json(raw)
    assert document["prequential_arm_histories_reconstructed"] == 24
    assert document["incompatible_schema_ood_controls_reexecuted"] == 6
    assert document["fresh_joint_prior_label_reduction_observed"] is False
    assert document["joint_prior_minus_strict_labels"] == 3
    assert document["official_scalar_cost"] is None
