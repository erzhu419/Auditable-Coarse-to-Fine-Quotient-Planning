import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_reusable_amortization_independent_verifier_v74 import (
    ConstructionK7ReusableAmortizationIndependentVerifierV74Error,
    verify_reusable_amortization_campaign_bytes_v74,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v74_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(ConstructionK7ReusableAmortizationIndependentVerifierV74Error):
        verify_reusable_amortization_campaign_bytes_v74(b"{}")


def test_v74_independent_verifier_import_surface_excludes_v74_producer_and_algorithms():
    path = Path(
        "src/acfqp/construction_k7_reusable_amortization_independent_verifier_v74.py"
    )
    tree = ast.parse(path.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("construction_k7_reusable_amortization_campaign_v74" in row for row in imports)
    assert not any("reusable_amortization_campaign_core_v74" in row for row in imports)
    assert not any("generic_joint_successor_version_space_planner_v42" in row for row in imports)
    assert not any("generic_reusable_version_space_certificate_planner_v43" in row for row in imports)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V74") != "1",
    reason="explicit producer-free V74 reconstruction",
)
def test_v74_independent_verifier_reconstructs_frozen_campaign():
    from acfqp.construction_k7_reusable_amortization_campaign_v74 import (
        run_reusable_amortization_campaign_v74,
    )

    campaign = run_reusable_amortization_campaign_v74()
    verification = loads_canonical_json(
        verify_reusable_amortization_campaign_bytes_v74(campaign.canonical_bytes)
    )
    assert verification["status"] == (
        "PRODUCER_FREE_REUSABLE_AMORTIZATION_EVIDENCE_VERIFIED"
    )
    assert verification["joint_successor_version_space_models_reconstructed"] == 3
    assert verification["target_certificate_episode_traces_replayed"] == 192
    assert verification["incremental_source_model_label_investment"] == 76
    assert verification["empirical_incremental_break_even_episode_ordinal"] == 7
    assert verification["final_cumulative_target_label_savings"] == 384
    assert verification["all_32_episode_amortization_rows_recomputed"] is True
    assert verification["v74_campaign_producer_imported_or_called"] is False
    assert verification["v74_campaign_core_imported_or_called"] is False
    assert verification["v42_model_compiler_called"] is False
    assert verification["v43_target_planner_called"] is False
    assert verification["official_execution_allowed"] is False
    assert verification["official_scalar_cost"] is None
    assert verification["official_N_break_even"] is None
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
