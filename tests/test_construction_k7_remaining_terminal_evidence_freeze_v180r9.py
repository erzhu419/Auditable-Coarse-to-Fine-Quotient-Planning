from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_remaining_terminal_evidence_freeze_v180r9 as freeze


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / ".tmp" / "exact-freeze" / "v180r9_remaining_terminal_production"
SOURCE = ROOT / "src" / "acfqp" / "construction_k7_remaining_terminal_evidence_freeze_v180r9.py"


def _retained() -> tuple[bytes, bytes]:
    terminal = OUTPUT_ROOT / "TERMINAL.json"
    verification = OUTPUT_ROOT / "VERIFICATION.json"
    if not terminal.is_file() or not verification.is_file():
        pytest.skip("retained V180r9 evidence is absent")
    return terminal.read_bytes(), verification.read_bytes()


def test_v180r9_retained_evidence_replays_exactly() -> None:
    result = freeze.verify_frozen_remaining_terminal_evidence_v180r9(*_retained())
    assert result["verification_id"] == freeze.EXPECTED_VERIFICATION_ID
    assert result["verified_terminal_count"] == 6


def test_v180r9_frozen_evidence_rejects_byte_mutation() -> None:
    terminal, verification = _retained()
    with pytest.raises(ValueError):
        freeze.verify_frozen_remaining_terminal_evidence_v180r9(
            terminal + b"\n",
            verification,
        )


def test_v180r9_freeze_surface_remains_producer_free() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("remaining_terminal_production_v180r9" in item for item in imports)
