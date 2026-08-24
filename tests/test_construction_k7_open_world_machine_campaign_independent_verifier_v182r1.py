from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_open_world_machine_campaign_independent_verifier_v182r1 as verifier
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_PATH = (
    ROOT / ".tmp" / "v182r1-open-world-machine-campaign" / "CAMPAIGN.json"
)
PROGRESS_ROOT = ROOT / ".tmp" / "v182r1-open-world-machine-campaign" / "progress"
VERIFIER_SOURCE = (
    ROOT
    / "src"
    / "acfqp"
    / "construction_k7_open_world_machine_campaign_independent_verifier_v182r1.py"
)


def test_v182r1_verifier_import_surface_is_producer_free() -> None:
    source = VERIFIER_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("campaign_v182r1" in item for item in imports)
    assert "run_open_world_machine_campaign_v182r1" not in source


def test_v182r1_retained_campaign_replays_when_present() -> None:
    if not CAMPAIGN_PATH.is_file():
        pytest.skip("retained V182r1 campaign is absent")
    raw = CAMPAIGN_PATH.read_bytes()
    result = verifier.verify_open_world_machine_campaign_independently_v182r1(
        raw,
        PROGRESS_ROOT,
    )
    assert result["finite_registered_campaign_verified"] is True
    assert result["target_labels_avoided"] > 0
    assert result["producer_module_imported"] is False
    assert result["broad_iid_sample_efficiency_claimed"] is False
    assert result["arbitrary_domain_transfer_claimed"] is False
    assert result["total_work_dominance_claimed"] is False
    assert result["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert result["official_execution_allowed"] is False
    if verifier.EXPECTED_CAMPAIGN_ID != "0" * 64:
        assert len(raw) == verifier.EXPECTED_CAMPAIGN_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CAMPAIGN_SHA256
        verification_bytes = canonical_json_bytes(result)
        assert result["verification_id"] == verifier.EXPECTED_VERIFICATION_ID
        assert len(verification_bytes) == verifier.EXPECTED_VERIFICATION_BYTE_COUNT
        assert hashlib.sha256(verification_bytes).hexdigest() == (
            verifier.EXPECTED_VERIFICATION_SHA256
        )
