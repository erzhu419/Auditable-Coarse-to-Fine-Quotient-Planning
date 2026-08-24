from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_all_path_v36_failure_freeze_v180r6 as failed
from acfqp import construction_k7_all_path_v36_resource_successor_authorization_v180r10 as authorization


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "src" / "acfqp" / "construction_k7_v36_local_recovery_resource_successor_independent_verifier_v180r10.py"
RUNNER = ROOT / "scripts" / "run_v180r10_v36_resource_successor_occurrence.py"


def test_v180r10_authorization_preserves_failure_and_sources() -> None:
    document = authorization.freeze_v36_resource_successor_authorization_v180r10().to_document()
    assert document["v36_resource_successor_authorization_id"] == authorization.EXPECTED_AUTHORIZATION_ID
    assert document["preserved_v180r6_failure_id"] == failed.EXPECTED_FAILURE_ID
    assert document["same_failed_authorization_rerun"] is False
    assert document["scientific_contract_changed"] is False
    assert document["algorithm_changed"] is False
    assert document["worker_resource_schedule_changed"] is False
    assert document["maximum_worker_processes"] == 2
    assert document["fresh_successor_execution_started"] is False
    for fact in document["source_facts"]:
        raw = (ROOT / fact["relative_path"]).read_bytes()
        assert fact["byte_count"] == len(raw)
        assert fact["sha256"] == hashlib.sha256(raw).hexdigest()


def test_v180r10_outputs_are_absent_before_execution() -> None:
    document = authorization.freeze_v36_resource_successor_authorization_v180r10().to_document()
    for key in (
        "output_root_relative_path",
        "terminal_output_relative_path",
        "verification_output_relative_path",
        "failure_output_relative_path",
    ):
        assert not (ROOT / document[key]).exists()


def test_v180r10_verifier_has_no_producer_import() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("production_terminal_finalizer" in name for name in imports)
    assert not any("adaptive_accounted_campaign" in name for name in imports)


def test_v180r10_runner_is_one_shot_and_local_only() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "already has progress" in source
    assert "O_EXCL" in source
    assert "git push" not in source
