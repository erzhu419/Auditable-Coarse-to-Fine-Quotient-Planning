import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_finite_objective_completion_audit_v179 as subject
from acfqp.phase3e_ids import loads_canonical_json


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


def test_v179_frozen_audit_marks_only_the_registered_finite_scope_complete():
    if subject.EXPECTED_AUDIT_ID == "0" * 64:
        return
    raw = (FREEZE / "v179_finite_objective_completion_audit.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["completion_audit_id"] == subject.EXPECTED_AUDIT_ID
    assert len(raw) == subject.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == subject.EXPECTED_CANONICAL_SHA256
    assert document["registered_finite_central_objective_completed"] is True
    assert document["completion_scope"] == (
        "FINITE_COVERAGE_BOUNDED_REGISTERED_SYMBOLIC_FAMILIES"
    )
    assert document["production_prior_receipt_event_scan_count"] == 0
    assert document["production_eager_retained_authorization_update_count"] == 0
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["arbitrary_unseen_domain_transfer_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
