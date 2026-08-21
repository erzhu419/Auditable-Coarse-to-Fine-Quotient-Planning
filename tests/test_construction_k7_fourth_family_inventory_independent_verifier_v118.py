import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_fourth_family_inventory_independent_verifier_v118 as verifier


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v118_fourth_family_inventory_campaign.json"
VERIFICATION = ROOT / ".tmp/exact-freeze/v118_fourth_family_inventory_verification.json"


def test_v118_verifier_does_not_import_v118_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    forbidden = (
        "fourth_family_inventory_campaign_core_v118",
        "generic_inventory_assembly_adapter_v118",
        "construction_k7_fourth_family_inventory_campaign_v118",
        "construction_k7_fourth_family_inventory_preregistration_v118",
        "domains.stochastic_inventory_assembly",
    )
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(any(name in item for name in forbidden) for item in imported)


def test_v118_independent_replay_verifies_registered_success_and_sample_delta():
    document = verifier.verify_fourth_family_inventory_campaign_bytes_v118(
        CAMPAIGN.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is True
    assert document["verified_accounting"]["prior_on_acquisition_labels"] == 35
    assert document["verified_accounting"]["strict_no_prior_acquisition_labels"] == 50
    assert document["verified_accounting"][
        "prior_minus_no_prior_acquisition_labels"
    ] == -15
    assert document["sample_efficiency_improvement_claimed"] is False
    assert document["arbitrary_unseen_domain_transfer_claimed"] is False


def test_v118_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7FourthFamilyInventoryIndependentVerifierV118Error
    ):
        verifier.verify_fourth_family_inventory_campaign_bytes_v118(bytes(raw))


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V118 independent verification has not been frozen",
)
def test_v118_exact_independent_verification_is_preserved():
    assert verifier.freeze_fourth_family_inventory_verification_v118(
        CAMPAIGN.read_bytes()
    ) == VERIFICATION.read_bytes()
