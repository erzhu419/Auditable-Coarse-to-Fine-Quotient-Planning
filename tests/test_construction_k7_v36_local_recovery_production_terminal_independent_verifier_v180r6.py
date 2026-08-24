from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_v36_local_recovery_production_terminal_independent_verifier_v180r6 as verifier


def test_verifier_import_surface_is_producer_free() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("adaptive_accounted_campaign_v36" in name for name in imported)
    assert not any("adaptive_accounted_independent_verifier_v36" in name for name in imported)
    assert not any("production_terminal_finalizer" in name for name in imported)


def test_verifier_rejects_absent_retained_output(tmp_path: Path) -> None:
    with pytest.raises(
        verifier.ConstructionK7V36ProductionTerminalIndependentVerifierV180r6Error,
        match="output root is absent",
    ):
        verifier.verify_v36_production_terminal_independently_v180r6(
            b"{}", tmp_path / "absent"
        )


def test_outcome_constants_are_unfrozen_before_first_execution() -> None:
    if verifier.EXPECTED_TERMINAL_BUNDLE_ID == "0" * 64:
        assert verifier.EXPECTED_TERMINAL_BYTE_COUNT == 0
        assert verifier.EXPECTED_VERIFICATION_ID == "0" * 64
