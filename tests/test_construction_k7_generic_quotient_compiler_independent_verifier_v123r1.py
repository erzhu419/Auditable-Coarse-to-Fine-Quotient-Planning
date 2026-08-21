from pathlib import Path
import ast
import hashlib

from acfqp.construction_k7_generic_quotient_compiler_independent_verifier_v123r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_generic_quotient_compiler_verification_v123r1,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return (
        (ROOT / "v123r1_generic_quotient_compiler_campaign.json").read_bytes(),
        (ROOT / "v122_generic_factor_planner_campaign.json").read_bytes(),
        (ROOT / "v122_generic_factor_planner_verification.json").read_bytes(),
        (ROOT / "v123_generic_quotient_compiler_failure.json").read_bytes(),
        (ROOT / "v121r1_generic_subprogram_campaign.json").read_bytes(),
        (ROOT / "v121_generic_artifact_subprogram_campaign.json").read_bytes(),
        (ROOT / "v121r1_generic_subprogram_verification.json").read_bytes(),
        source,
    )


def test_v123r1_producer_free_verifier_rebuilds_models_and_plans():
    raw = freeze_generic_quotient_compiler_verification_v123r1(*_inputs())
    document = loads_canonical_json(raw)
    assert document["registered_gate_independently_verified"] is True
    assert document["producer_free_raw_transition_model_epoch_reconstruction"] is True
    assert sum(row["independently_rebuilt_model_epoch_count"] for row in document["verified_occurrences"]) == 12
    assert sum(row["independent_plan_path_support_checks"] for row in document["verified_occurrences"]) > 0
    assert document["legacy_shape_specific_model_builder_used_as_planning_input"] is False
    assert document["official_scalar_cost"] is None


def test_v123r1_frozen_verification_bytes_and_import_surface():
    raw = (ROOT / "v123r1_generic_quotient_compiler_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    path = Path(__file__).resolve().parents[1] / "src/acfqp/construction_k7_generic_quotient_compiler_independent_verifier_v123r1.py"
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        name.endswith("construction_k7_generic_quotient_compiler_campaign_v123r1")
        or name.endswith("generic_quotient_compiler_campaign_core_v123r1")
        or name.endswith("generic_compiled_quotient_model_v123")
        for name in imported
    )
