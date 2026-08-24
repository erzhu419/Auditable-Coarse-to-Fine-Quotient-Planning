import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_v36_retained_recovery_authorization_v180r10r1 as authorization


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "src" / "acfqp" / "construction_k7_v36_retained_recovery_independent_verifier_v180r10r1.py"


def test_v180r10r1_authorization_is_outcome_free_and_source_closed() -> None:
    frozen = authorization.freeze_v36_retained_recovery_authorization_v180r10r1()
    document = frozen.to_document()
    assert document["scientific_occurrence_rerun_forbidden"] is True
    assert document["retained_actual_occurrence_finish_forward_only"] is True
    assert document["new_scientific_outcome_accessed"] is False
    assert document["actual_worker_process_count"] == 0
    assert document["maximum_retained_replay_processes"] == 1
    assert document["maximum_retained_replay_working_bytes"] == 24 * 1024**3
    assert document["official_execution_allowed"] is False
    for fact in document["source_facts"]:
        raw = (ROOT / fact["relative_path"]).read_bytes()
        assert len(raw) == fact["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == fact["sha256"]


def test_v180r10r1_verifier_does_not_import_terminal_producer() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("retained_recovery_terminal_v180r10r1" in name for name in imports)
    assert "finish_forward_retained_v36_occurrence_v180r10r1" not in source
