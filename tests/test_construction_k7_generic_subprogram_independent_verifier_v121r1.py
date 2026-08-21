import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_generic_subprogram_independent_verifier_v121r1 as verifier
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
CAMPAIGN = ROOT / "v121r1_generic_subprogram_campaign.json"
FAILED = ROOT / "v121_generic_artifact_subprogram_campaign.json"
VERIFICATION = ROOT / "v121r1_generic_subprogram_verification.json"
FILES = {
    "V117": ROOT / "v117_dependency_derived_program_branch_campaign.json",
    "V118": ROOT / "v118_fourth_family_inventory_campaign.json",
    "V119": ROOT / "v119_source_unseen_residual_campaign.json",
}


def _sources():
    return {key: path.read_bytes() for key, path in FILES.items()}


def test_v121r1_independent_verifier_reconstructs_failure_and_successor():
    result = verifier.freeze_generic_subprogram_verification_v121r1(
        CAMPAIGN.read_bytes(), FAILED.read_bytes(), _sources()
    )
    document = loads_canonical_json(result)
    assert document["campaign_id"] == verifier.CAMPAIGN_ID
    assert document["producer_free_failed_v121_cause_reconstruction"] is True
    failed = document["failed_v121_campaign_verification"]
    assert failed["failed_gate_key"] == "same_epoch_genesis_authorization_observed"
    assert failed["failed_occurrence_all_episodes_succeed"] is True
    assert document["registered_gate_independently_verified"] is True
    assert document["generic_planner_execution_adapter_verified"] is False
    assert document["official_scalar_cost"] is None


def test_v121r1_independent_verifier_rejects_changed_failed_predecessor():
    changed = bytearray(FAILED.read_bytes())
    changed[len(changed) // 2] ^= 1
    with pytest.raises(Exception):
        verifier.freeze_generic_subprogram_verification_v121r1(
            CAMPAIGN.read_bytes(), bytes(changed), _sources()
        )


def test_v121r1_independent_verifier_has_no_v121_producer_import():
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = (
        "generic_artifact_subprogram_instantiator_v121",
        "generic_artifact_subprogram_acquisition_v121",
        "generic_artifact_subprogram_campaign_core_v121",
        "generic_artifact_subprogram_preregistration_v121",
        "generic_artifact_subprogram_campaign_v121",
        "generic_subprogram_opportunity_independent_campaign_core_v121r1",
        "generic_subprogram_preregistration_v121r1",
        "generic_subprogram_campaign_v121r1",
    )
    assert not any(any(name in item for name in forbidden) for item in imported)


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V121r1 independent verification has not been frozen",
)
def test_v121r1_exact_verification_is_preserved():
    assert VERIFICATION.read_bytes() == verifier.freeze_generic_subprogram_verification_v121r1(
        CAMPAIGN.read_bytes(), FAILED.read_bytes(), _sources()
    )
