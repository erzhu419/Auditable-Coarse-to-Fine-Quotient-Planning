import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_projected_program_memo_independent_verifier_v115 as verifier


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v115_projected_program_memo_campaign.json"
VERIFICATION = ROOT / ".tmp/exact-freeze/v115_projected_program_memo_verification.json"


def test_v115_verifier_does_not_import_v115_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    forbidden = (
        "projected_program_memo_campaign_core_v115",
        "generic_projected_program_memo_sequence_v115",
        "construction_k7_projected_program_memo_campaign_v115",
        "construction_k7_projected_program_memo_preregistration_v115",
        "generic_incremental_abstract_successor_sequence_v113",
        "generic_incremental_abstract_successor_v113",
    )
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(any(name in item for name in forbidden) for item in imported)


def test_v115_independent_replay_verifies_registered_success():
    document = verifier.verify_projected_program_memo_campaign_bytes_v115(
        CAMPAIGN.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is True
    assert document["verified_accounting"][
        "planning_compute_events_avoided_by_program_memo"
    ] == 22_416
    assert document["verified_accounting"][
        "projected_program_memo_lifetime_target_labels"
    ] == 145
    assert document["fresh_v115_full_dynamics_rederivation_performed"] is False
    assert document["official_scalar_cost"] is None


def test_v115_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7ProjectedProgramMemoIndependentVerifierV115Error
    ):
        verifier.verify_projected_program_memo_campaign_bytes_v115(bytes(raw))


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V115 independent verification has not been frozen",
)
def test_v115_exact_independent_verification_is_preserved():
    assert verifier.freeze_projected_program_memo_verification_v115(
        CAMPAIGN.read_bytes()
    ) == VERIFICATION.read_bytes()
