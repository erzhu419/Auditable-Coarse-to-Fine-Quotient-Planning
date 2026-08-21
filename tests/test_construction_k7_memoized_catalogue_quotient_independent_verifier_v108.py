import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_memoized_catalogue_quotient_independent_verifier_v108 as verifier


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v108_memoized_catalogue_quotient_campaign.json"
)
VERIFICATION_PATH = Path(
    ".tmp/exact-freeze/v108_memoized_catalogue_quotient_verification.json"
)


def test_v108_verifier_does_not_import_v108_producer_or_execution_core():
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = {
        "acfqp.construction_k7_memoized_catalogue_quotient_campaign_v108",
        "acfqp.memoized_catalogue_quotient_campaign_core_v108",
        "acfqp.generic_persistent_memoized_catalogue_quotient_sequence_v108",
    }
    assert imported.isdisjoint(forbidden)


def test_v108_independent_replay_preserves_exact_registered_failure():
    raw = CAMPAIGN_PATH.read_bytes()
    document = verifier.verify_memoized_catalogue_quotient_campaign_bytes_v108(raw)
    assert document["registered_gate_independently_verified"] is False
    assert document["fresh_successor_required"] is True
    assert document["all_orderer_calls_successfully_receipted"] is True
    assert document["verified_cache_hit_count"] == 40
    assert document["verified_accounting"]["planning_compute_events_avoided"] == 550
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v108_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[-2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7MemoizedCatalogueQuotientIndependentVerifierV108Error
    ):
        verifier.verify_memoized_catalogue_quotient_campaign_bytes_v108(bytes(raw))


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION_PATH.exists(),
    reason="V108 independent verification has not been frozen",
)
def test_v108_exact_independent_verification_is_preserved():
    raw = VERIFICATION_PATH.read_bytes()
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert verifier.freeze_memoized_catalogue_quotient_verification_v108(
        CAMPAIGN_PATH.read_bytes()
    ) == raw
