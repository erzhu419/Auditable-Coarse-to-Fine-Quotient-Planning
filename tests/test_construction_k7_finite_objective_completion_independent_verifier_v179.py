import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_finite_objective_completion_independent_verifier_v179 as subject
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


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


def test_v179_frozen_independent_verification_and_retained_reconstruction():
    if subject.VERIFICATION_ID == "0" * 64:
        return
    raw = (FREEZE / "v179_finite_objective_completion_verification.json").read_bytes()
    frozen = loads_canonical_json(raw)
    assert frozen["verification_id"] == subject.VERIFICATION_ID
    assert len(raw) == subject.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == subject.EXPECTED_CANONICAL_SHA256
    assert frozen[
        "registered_finite_central_objective_completion_independently_verified"
    ] is True
    assert frozen["complete_ground_world_model_claimed"] is False
    assert frozen["official_execution_allowed"] is False
    assert frozen["official_scalar_cost"] is None
    names = (
        "v179_finite_objective_completion_contract.json",
        "v179_finite_objective_completion_audit.json",
        "v41_standard_2048_complete_episode_campaign.json",
        "v41_standard_2048_complete_episode_verification.json",
        "v124_cross_family_generic_compiler_campaign.json",
        "v124_cross_family_generic_compiler_verification.json",
        "v159_third_dynamics_campaign.json",
        "v159_third_dynamics_verification.json",
        "v168_fifth_family_total_plan_receipt_set_campaign.json",
        "v168_fifth_family_total_plan_receipt_set_verification.json",
        "v178r1_indexed_lazy_invalidation_campaign.json",
        "v178r1_indexed_lazy_invalidation_verification.json",
    )
    replayed = subject.verify_finite_objective_completion_audit_v179(
        *[(FREEZE / name).read_bytes() for name in names]
    )
    assert canonical_json_bytes(replayed) == raw
