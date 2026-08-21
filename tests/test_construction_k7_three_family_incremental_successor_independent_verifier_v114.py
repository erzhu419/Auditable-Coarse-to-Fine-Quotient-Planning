import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_three_family_incremental_successor_independent_verifier_v114 as verifier


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v114_three_family_incremental_successor_campaign.json"
VERIFICATION = ROOT / ".tmp/exact-freeze/v114_three_family_incremental_successor_verification.json"


def test_v114_verifier_does_not_import_v114_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    forbidden = (
        "three_family_incremental_successor_campaign_core_v114",
        "construction_k7_three_family_incremental_successor_campaign_v114",
        "construction_k7_three_family_incremental_successor_preregistration_v114",
        "incremental_abstract_successor_campaign_core_v113",
        "generic_incremental_abstract_successor_v113",
        "generic_incremental_abstract_successor_sequence_v113",
        "construction_k7_incremental_abstract_successor_campaign_v113",
        "construction_k7_incremental_abstract_successor_preregistration_v113",
    )
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(any(name in item for name in forbidden) for item in imported)


def test_v114_independent_replay_verifies_three_family_success():
    document = verifier.verify_three_family_incremental_successor_campaign_bytes_v114(
        CAMPAIGN.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is True
    assert document["verified_target_family_counts"] == {
        "BALANCED_BATCH_REFINEMENT": 2,
        "COUPLED_EXCHANGE": 2,
        "MAINTENANCE_CASCADE": 2,
    }
    assert document["verified_accounting"][
        "model_compilation_events_avoided_against_full_rebuild"
    ] == 27_029
    assert document["verified_accounting"][
        "incremental_quotient_lifetime_target_labels"
    ] == 368
    assert document["official_scalar_cost"] is None


def test_v114_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7ThreeFamilyIncrementalSuccessorIndependentVerifierV114Error
    ):
        verifier.verify_three_family_incremental_successor_campaign_bytes_v114(
            bytes(raw)
        )


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V114 independent verification has not been frozen",
)
def test_v114_exact_independent_verification_is_preserved():
    assert verifier.freeze_three_family_incremental_successor_verification_v114(
        CAMPAIGN.read_bytes()
    ) == VERIFICATION.read_bytes()
