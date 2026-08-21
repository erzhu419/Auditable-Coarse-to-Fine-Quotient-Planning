import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_identity_short_circuited_epoch_independent_verifier_v111 as verifier


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v111_identity_short_circuited_epoch_campaign.json"
)
VERIFICATION_PATH = Path(
    ".tmp/exact-freeze/v111_identity_short_circuited_epoch_verification.json"
)


def test_v111_verifier_does_not_import_v111_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden = {
        "acfqp.construction_k7_identity_short_circuited_epoch_campaign_v111",
        "acfqp.construction_k7_identity_short_circuited_epoch_preregistration_v111",
        "acfqp.identity_short_circuited_epoch_campaign_core_v111",
        "acfqp.generic_identity_short_circuited_epoch_sequence_v111",
    }
    assert imported.isdisjoint(forbidden)


def test_v111_independent_replay_preserves_exact_registered_failure():
    document = verifier.verify_identity_short_circuited_epoch_campaign_bytes_v111(
        CAMPAIGN_PATH.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is False
    assert document["fresh_successor_required"] is True
    assert document["producer_free_identity_short_circuit_reconstruction"] is True
    assert document["verified_accounting"]["maintenance_events_avoided_against_full_diff"] == 666


def test_v111_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7IdentityShortCircuitedEpochIndependentVerifierV111Error
    ):
        verifier.verify_identity_short_circuited_epoch_campaign_bytes_v111(
            bytes(raw)
        )


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION_PATH.exists(),
    reason="V111 independent verification has not been frozen",
)
def test_v111_exact_independent_verification_is_preserved():
    assert verifier.freeze_identity_short_circuited_epoch_verification_v111(
        CAMPAIGN_PATH.read_bytes()
    ) == VERIFICATION_PATH.read_bytes()
