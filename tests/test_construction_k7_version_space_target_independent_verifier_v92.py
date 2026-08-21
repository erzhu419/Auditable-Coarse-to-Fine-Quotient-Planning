from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_version_space_target_independent_verifier_v92 as verifier
from acfqp.phase3e_ids import loads_canonical_json


def test_v92_verifier_rejects_foreign_bytes():
    with pytest.raises(
        verifier.ConstructionK7VersionSpaceTargetIndependentVerifierV92Error
    ):
        verifier.verify_version_space_target_campaign_bytes_v92(b"{}")


def test_v92_verifier_has_no_campaign_producer_or_builder_import():
    path = Path(
        "src/acfqp/construction_k7_version_space_target_independent_verifier_v92.py"
    )
    imports = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("version_space_target_campaign_v92" in row for row in imports)
    assert not any("version_space_target_campaign_core_v92" in row for row in imports)


def test_v92_independent_verifier_preserves_failure_and_replay_gap():
    raw = Path(
        ".tmp/exact-freeze/v92_version_space_target_campaign.json"
    ).read_bytes()
    result = loads_canonical_json(
        verifier.verify_version_space_target_campaign_bytes_v92(raw)
    )
    assert result["frozen_terminal_transfer_failure_preserved"] is True
    assert result["frozen_no_sample_reduction_result_preserved"] is True
    assert result[
        "raw_partial_acquisition_or_alignment_semantics_independently_replayed"
    ] is False
    assert result["official_execution_allowed"] is False
