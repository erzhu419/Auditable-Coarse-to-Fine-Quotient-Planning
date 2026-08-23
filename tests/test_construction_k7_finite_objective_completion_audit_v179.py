import ast
from pathlib import Path

from acfqp import construction_k7_finite_objective_completion_audit_v179 as subject


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v179_audit_does_not_import_scientific_producers():
    tree = ast.parse(Path(subject.__file__).read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any("campaign_v" in name for name in imported)


def test_v179_audit_is_blocked_until_v178r1_is_frozen_and_verified():
    if subject.V178R1_CAMPAIGN_ID != "0" * 64:
        return
    assert subject.EXPECTED_AUDIT_ID == "0" * 64
