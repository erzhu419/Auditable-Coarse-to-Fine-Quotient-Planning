from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_ten_terminal_aggregation_independent_verifier_v180r12r1 as verifier


def test_v180r12r1_verifier_import_surface_is_producer_free() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(alias.name for alias in node.names)
    assert not any("aggregation_finalizer_v180r12r1" in name for name in imported)
    assert "materialize_ten_terminal_aggregation_v180r12r1" not in source


def test_v180r12r1_verifier_rejects_an_incomplete_source_denominator(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        verifier.ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R1Error,
        match="V180r11 terminal is absent",
    ):
        verifier.verify_ten_terminal_aggregation_independently_v180r12r1(
            b"{}",
            tmp_path,
        )
