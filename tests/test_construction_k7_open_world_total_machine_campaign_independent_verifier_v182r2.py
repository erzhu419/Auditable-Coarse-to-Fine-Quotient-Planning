from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_open_world_total_machine_campaign_independent_verifier_v182r2 as verifier


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_PATH = (
    ROOT / ".tmp" / "v182r2-open-world-total-machine-campaign" / "CAMPAIGN.json"
)
PROGRESS_ROOT = CAMPAIGN_PATH.parent / "progress"
VERIFIER_SOURCE = (
    ROOT
    / "src"
    / "acfqp"
    / "construction_k7_open_world_total_machine_campaign_independent_verifier_v182r2.py"
)


def test_v182r2_verifier_import_surface_is_producer_free() -> None:
    source = VERIFIER_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("campaign_v182r2" in item for item in imports)
    assert "run_open_world_total_machine_campaign_v182r2" not in source


def test_v182r2_retained_campaign_replays_when_present() -> None:
    if not CAMPAIGN_PATH.is_file():
        pytest.skip("retained V182r2 campaign is absent")
    from acfqp import construction_k7_open_world_total_machine_execution_preregistration_v182r2 as preregistration

    result = verifier.verify_open_world_total_machine_campaign_independently_v182r2(
        CAMPAIGN_PATH.read_bytes(),
        PROGRESS_ROOT,
        expected_execution_preregistration_id=(
            preregistration.EXPECTED_PREREGISTRATION_ID
        ),
    )
    assert result["exact_campaign_reconstructed_from_committed_manifests"] is True
    assert result["target_labels_avoided"] > 0
    assert result["producer_module_imported"] is False
    assert result["broad_iid_sample_efficiency_claimed"] is False
    assert result["arbitrary_domain_transfer_claimed"] is False
    assert result["total_work_dominance_claimed"] is False
    assert result["official_execution_allowed"] is False
