import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_generic_factor_planner_independent_verifier_v122 as verifier
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
CAMPAIGN = ROOT / "v122_generic_factor_planner_campaign.json"
VERIFICATION = ROOT / "v122_generic_factor_planner_verification.json"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def _verify(raw=None):
    return verifier.freeze_generic_factor_planner_verification_v122(
        CAMPAIGN.read_bytes() if raw is None else raw,
        (ROOT / "v121r1_generic_subprogram_campaign.json").read_bytes(),
        (ROOT / "v121_generic_artifact_subprogram_campaign.json").read_bytes(),
        (ROOT / "v121r1_generic_subprogram_verification.json").read_bytes(),
        _sources(),
    )


def test_v122_independent_verifier_reconstructs_generic_planning():
    document = loads_canonical_json(_verify())
    assert document["registered_gate_independently_verified"] is True
    assert document["producer_free_expression_successor_reconstruction"] is True
    assert document["producer_free_program_and_graph_path_reachability_reconstruction"] is True
    assert document["generic_planner_execution_adapter_verified"] is True
    assert document["legacy_shape_specific_planner_execution_adapter_present"] is False
    assert document["official_scalar_cost"] is None


def test_v122_independent_verifier_rejects_changed_campaign():
    changed = bytearray(CAMPAIGN.read_bytes())
    changed[len(changed) // 2] ^= 1
    with pytest.raises(Exception):
        _verify(bytes(changed))


def test_v122_independent_verifier_has_no_v122_producer_import():
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = (
        "generic_compiled_factor_planner_v122",
        "generic_factor_planner_sequence_v122",
        "generic_factor_planner_campaign_core_v122",
        "generic_factor_planner_preregistration_v122",
        "generic_factor_planner_campaign_v122",
    )
    assert not any(any(name in item for name in forbidden) for item in imported)


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V122 independent verification has not been frozen",
)
def test_v122_exact_verification_is_preserved():
    assert VERIFICATION.read_bytes() == _verify()
