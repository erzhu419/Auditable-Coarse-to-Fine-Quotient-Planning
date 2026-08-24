from __future__ import annotations

import ast
from pathlib import Path

from acfqp import construction_k7_all_path_production_terminal_independent_verifier_v180r5 as verifier


def test_verifier_logic_is_frozen_before_v180r5_terminal() -> None:
    assert verifier.EXPECTED_TERMINAL_BUNDLE_ID == "0" * 64
    assert verifier.EXPECTED_VERIFICATION_ID == "0" * 64


def test_verifier_does_not_import_terminal_or_v34_producer() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(
        name.endswith("production_terminal_finalizer_v180r3")
        or name.endswith("full_accounted_campaign_v34")
        or name.endswith("full_accounted_independent_verifier_v34")
        for name in imported
    )
