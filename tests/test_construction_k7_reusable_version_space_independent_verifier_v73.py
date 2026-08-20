import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_reusable_version_space_independent_verifier_v73 import (
    ConstructionK7ReusableVersionSpaceIndependentVerifierV73Error,
    verify_reusable_version_space_campaign_bytes_v73,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v73_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(ConstructionK7ReusableVersionSpaceIndependentVerifierV73Error):
        verify_reusable_version_space_campaign_bytes_v73(b"{}")


def test_v73_independent_verifier_import_surface_excludes_producers_and_new_algorithms():
    path = Path(
        "src/acfqp/construction_k7_reusable_version_space_independent_verifier_v73.py"
    )
    tree = ast.parse(path.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("construction_k7_reusable_version_space_campaign_v73" in row for row in imports)
    assert not any("reusable_version_space_campaign_core_v73" in row for row in imports)
    assert not any("generic_joint_successor_version_space_planner_v42" in row for row in imports)
    assert not any("generic_reusable_version_space_certificate_planner_v43" in row for row in imports)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V73") != "1",
    reason="explicit producer-free V73 reconstruction",
)
def test_v73_independent_verifier_reconstructs_frozen_campaign():
    from acfqp.construction_k7_reusable_version_space_campaign_v73 import (
        run_reusable_version_space_campaign_v73,
    )

    campaign = run_reusable_version_space_campaign_v73()
    verification = loads_canonical_json(
        verify_reusable_version_space_campaign_bytes_v73(campaign.canonical_bytes)
    )
    assert verification["status"] == (
        "PRODUCER_FREE_REUSABLE_VERSION_SPACE_EVIDENCE_VERIFIED"
    )
    assert verification["joint_successor_version_space_models_reconstructed"] == 3
    assert verification["target_certificate_episode_traces_replayed"] == 6
    assert verification["derived_target_certificate_local_labels"] == 94
    assert verification["strict_target_certificate_local_labels"] == 106
    assert verification["fresh_actual_target_sample_reduction_observed"] is True
    assert verification["v73_campaign_producer_imported"] is False
    assert verification["v73_campaign_core_imported"] is False
    assert verification["v42_model_compiler_imported"] is False
    assert verification["v43_target_planner_imported"] is False
    assert verification["official_execution_allowed"] is False
    assert verification["official_scalar_cost"] is None
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
