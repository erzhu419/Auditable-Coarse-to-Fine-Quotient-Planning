import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_v34_retained_recovery_authorization_v180r11 as authorization


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "src" / "acfqp" / "construction_k7_v34_retained_recovery_independent_verifier_v180r11.py"


def test_v180r11_authorization_is_source_closed_and_outcome_free() -> None:
    frozen = authorization.freeze_v34_retained_recovery_authorization_v180r11()
    document = frozen.to_document()
    assert document["v34_retained_recovery_authorization_id"] == frozen.authorization_id
    assert document["scientific_occurrence_rerun_forbidden"] is True
    assert document["recovery_execution_started"] is False
    assert document["new_scientific_outcome_accessed"] is False
    assert document["actual_worker_process_count"] == 0
    assert document["official_execution_allowed"] is False
    for fact in document["source_facts"]:
        raw = (ROOT / fact["relative_path"]).read_bytes()
        assert len(raw) == fact["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == fact["sha256"]


def test_v180r11_successor_outputs_are_absent_before_execution() -> None:
    document = authorization.freeze_v34_retained_recovery_authorization_v180r11().to_document()
    for key in (
        "terminal_output_relative_path",
        "verification_output_relative_path",
        "failure_output_relative_path",
    ):
        assert not (ROOT / document[key]).exists()


def test_v180r11_independent_verifier_does_not_import_recovery_producer() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("retained_recovery_terminal_v180r11" in name for name in imports)
    assert "finish_forward_retained_v34_occurrence_v180r11" not in source
