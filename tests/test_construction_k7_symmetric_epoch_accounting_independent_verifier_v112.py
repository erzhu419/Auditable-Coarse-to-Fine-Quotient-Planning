import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_symmetric_epoch_accounting_independent_verifier_v112 as verifier


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v112_symmetric_epoch_accounting_campaign.json"
)
VERIFICATION_PATH = Path(
    ".tmp/exact-freeze/v112_symmetric_epoch_accounting_verification.json"
)


def test_v112_verifier_does_not_import_v112_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden = {
        "acfqp.construction_k7_symmetric_epoch_accounting_campaign_v112",
        "acfqp.construction_k7_symmetric_epoch_accounting_preregistration_v112",
        "acfqp.symmetric_epoch_accounting_campaign_core_v112",
        "acfqp.identity_short_circuited_epoch_campaign_core_v111",
        "acfqp.generic_identity_short_circuited_epoch_sequence_v111",
    }
    assert imported.isdisjoint(forbidden)


def test_v112_independent_replay_verifies_registered_success():
    document = verifier.verify_symmetric_epoch_accounting_campaign_bytes_v112(
        CAMPAIGN_PATH.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is True
    assert document["producer_free_symmetric_accounting_reconstruction"] is True
    assert document["verified_accounting"][
        "maintenance_events_avoided_against_fully_accounted_full_diff"
    ] == 474


def test_v112_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7SymmetricEpochAccountingIndependentVerifierV112Error
    ):
        verifier.verify_symmetric_epoch_accounting_campaign_bytes_v112(bytes(raw))


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION_PATH.exists(),
    reason="V112 independent verification has not been frozen",
)
def test_v112_exact_independent_verification_is_preserved():
    assert verifier.freeze_symmetric_epoch_accounting_verification_v112(
        CAMPAIGN_PATH.read_bytes()
    ) == VERIFICATION_PATH.read_bytes()
