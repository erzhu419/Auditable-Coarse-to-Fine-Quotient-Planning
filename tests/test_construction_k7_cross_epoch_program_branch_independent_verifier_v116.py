import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_cross_epoch_program_branch_independent_verifier_v116 as verifier


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v116_cross_epoch_program_branch_campaign.json"
VERIFICATION = ROOT / ".tmp/exact-freeze/v116_cross_epoch_program_branch_verification.json"


def test_v116_verifier_does_not_import_v116_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    forbidden = (
        "cross_epoch_program_branch_campaign_core_v116",
        "generic_cross_epoch_program_branch_sequence_v116",
        "construction_k7_cross_epoch_program_branch_campaign_v116",
        "construction_k7_cross_epoch_program_branch_preregistration_v116",
        "generic_projected_program_memo_sequence_v115",
    )
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(any(name in item for name in forbidden) for item in imported)


def test_v116_independent_replay_verifies_registered_success():
    document = verifier.verify_cross_epoch_program_branch_campaign_bytes_v116(
        CAMPAIGN.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is True
    assert document["verified_accounting"][
        "planning_compute_events_avoided_against_v115"
    ] == 1_800
    assert document["verified_accounting"][
        "planning_compute_events_avoided_against_uncached_v113"
    ] == 16_088
    assert document["official_scalar_cost"] is None


def test_v116_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7CrossEpochProgramBranchIndependentVerifierV116Error
    ):
        verifier.verify_cross_epoch_program_branch_campaign_bytes_v116(bytes(raw))


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V116 independent verification has not been frozen",
)
def test_v116_exact_independent_verification_is_preserved():
    assert verifier.freeze_cross_epoch_program_branch_verification_v116(
        CAMPAIGN.read_bytes()
    ) == VERIFICATION.read_bytes()
