from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_remaining_terminal_independent_verifier_v180r9 as verifier


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / ".tmp" / "exact-freeze" / "v180r9_remaining_terminal_production"
VERIFIER_SOURCE = ROOT / "src" / "acfqp" / "construction_k7_remaining_terminal_independent_verifier_v180r9.py"


def test_v180r9_verifier_import_surface_is_producer_free() -> None:
    source = VERIFIER_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("remaining_terminal_production_v180r9" in item for item in imports)
    assert "run_remaining_terminal_production_campaign_v180r9" not in source


def test_v180r9_retained_campaign_replays_when_present() -> None:
    if not (OUTPUT_ROOT / "TERMINAL.json").is_file():
        pytest.skip("retained V180r9 campaign is absent")
    from acfqp import construction_k7_remaining_terminal_execution_authorization_v180r9 as authorization

    result = verifier.verify_remaining_terminal_campaign_independently_v180r9(
        (OUTPUT_ROOT / "TERMINAL.json").read_bytes(),
        execution_authorization_id=authorization.EXPECTED_AUTHORIZATION_ID,
        event_manifests=authorization.event_manifests_v180r9(),
    )
    assert result["verified_terminal_count"] == 6
    assert result["all_counter_records_replayed"] is True
    assert result["campaign_orchestration_replayed"] is True
    assert result["all_ten_paths_verified"] is False
    assert result["official_execution_allowed"] is False
