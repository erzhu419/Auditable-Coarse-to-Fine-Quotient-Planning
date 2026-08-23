import ast
from pathlib import Path

from acfqp import construction_k7_finite_objective_completion_independent_verifier_v179 as subject


def test_v179_independent_verifier_does_not_import_audit_producer():
    tree = ast.parse(Path(subject.__file__).read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any(
        name.endswith("construction_k7_finite_objective_completion_audit_v179")
        for name in imported
    )


def test_v179_independent_verifier_remains_blocked_before_terminal_inputs():
    if subject.V178R1_CAMPAIGN_ID != "0" * 64:
        return
    assert subject.AUDIT_ID == "0" * 64
    assert subject.VERIFICATION_ID == "0" * 64
