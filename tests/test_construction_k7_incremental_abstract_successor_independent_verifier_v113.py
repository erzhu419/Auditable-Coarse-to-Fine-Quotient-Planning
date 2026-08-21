import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_incremental_abstract_successor_independent_verifier_v113 as verifier


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v113_incremental_abstract_successor_campaign.json"
VERIFICATION = ROOT / ".tmp/exact-freeze/v113_incremental_abstract_successor_verification.json"


def test_v113_verifier_does_not_import_v113_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    forbidden = (
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


def test_v113_independent_replay_verifies_registered_success():
    document = verifier.verify_incremental_abstract_successor_campaign_bytes_v113(
        CAMPAIGN.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is True
    assert document[
        "producer_free_incremental_model_and_terminal_rule_reconstruction"
    ] is True
    assert document["verified_accounting"][
        "model_compilation_events_avoided_against_full_rebuild"
    ] == 18_784
    assert document["official_scalar_cost"] is None


def test_v113_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7IncrementalAbstractSuccessorIndependentVerifierV113Error
    ):
        verifier.verify_incremental_abstract_successor_campaign_bytes_v113(bytes(raw))


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V113 independent verification has not been frozen",
)
def test_v113_exact_independent_verification_is_preserved():
    raw = CAMPAIGN.read_bytes()
    frozen = VERIFICATION.read_bytes()
    assert verifier.freeze_incremental_abstract_successor_verification_v113(raw) == frozen
