import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_artifact_derived_factor_independent_verifier_v120 as verifier
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"
CAMPAIGN = FREEZE / "v120_artifact_derived_factor_campaign.json"
VERIFICATION = FREEZE / "v120_artifact_derived_factor_verification.json"
FILES = {
    "V117": FREEZE / "v117_dependency_derived_program_branch_campaign.json",
    "V118": FREEZE / "v118_fourth_family_inventory_campaign.json",
    "V119": FREEZE / "v119_source_unseen_residual_campaign.json",
}


def _sources():
    return {key: path.read_bytes() for key, path in FILES.items()}


def test_v120_independent_verifier_reconstructs_library_and_campaign():
    raw = CAMPAIGN.read_bytes()
    result = verifier.freeze_artifact_derived_factor_verification_v120(
        raw, _sources()
    )
    document = loads_canonical_json(result)
    assert document["campaign_id"] == verifier.CAMPAIGN_ID
    assert document["artifact_factor_library_id"] == verifier.FACTOR_LIBRARY_ID
    assert document["producer_free_artifact_factor_library_reconstruction"] is True
    assert document["registered_gate_independently_verified"] is True
    assert document["arbitrary_unseen_domain_transfer_claimed"] is False
    assert document["official_scalar_cost"] is None


def test_v120_independent_verifier_rejects_changed_source_bytes():
    sources = _sources()
    changed = bytearray(sources["V117"])
    changed[len(changed) // 2] ^= 1
    sources["V117"] = bytes(changed)
    with pytest.raises(Exception):
        verifier.freeze_artifact_derived_factor_verification_v120(
            CAMPAIGN.read_bytes(), sources
        )


def test_v120_independent_verifier_has_no_producer_import():
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = (
        "artifact_derived_factor_projection_v120",
        "artifact_derived_partial_acquisition_v120",
        "artifact_derived_factor_campaign_core_v120",
        "artifact_derived_factor_preregistration_v120",
        "artifact_derived_factor_campaign_v120",
    )
    assert not any(any(name in item for name in forbidden) for item in imported)


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V120 independent verification has not been frozen",
)
def test_v120_exact_verification_is_preserved():
    assert VERIFICATION.read_bytes() == verifier.freeze_artifact_derived_factor_verification_v120(
        CAMPAIGN.read_bytes(), _sources()
    )
