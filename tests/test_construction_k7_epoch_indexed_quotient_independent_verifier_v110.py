import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_epoch_indexed_quotient_independent_verifier_v110 as verifier


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v110_epoch_indexed_quotient_campaign.json"
)
VERIFICATION_PATH = Path(
    ".tmp/exact-freeze/v110_epoch_indexed_quotient_verification.json"
)


def test_v110_verifier_does_not_import_v110_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden = {
        "acfqp.construction_k7_epoch_indexed_quotient_campaign_v110",
        "acfqp.construction_k7_epoch_indexed_quotient_preregistration_v110",
        "acfqp.epoch_indexed_quotient_campaign_core_v110",
        "acfqp.generic_epoch_indexed_quotient_sequence_v110",
    }
    assert imported.isdisjoint(forbidden)


def test_v110_independent_replay_preserves_exact_registered_failure():
    document = verifier.verify_epoch_indexed_quotient_campaign_bytes_v110(
        CAMPAIGN_PATH.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is False
    assert document["fresh_successor_required"] is True
    assert document["producer_free_epoch_delta_and_reverse_index_reconstruction"] is True
    assert document["verified_accounting"]["dependency_maintenance_events_avoided"] == 2358


def test_v110_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7EpochIndexedQuotientIndependentVerifierV110Error
    ):
        verifier.verify_epoch_indexed_quotient_campaign_bytes_v110(bytes(raw))


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION_PATH.exists(),
    reason="V110 independent verification has not been frozen",
)
def test_v110_exact_independent_verification_is_preserved():
    raw = CAMPAIGN_PATH.read_bytes()
    frozen = VERIFICATION_PATH.read_bytes()
    assert verifier.freeze_epoch_indexed_quotient_verification_v110(raw) == frozen
