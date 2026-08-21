import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_dependency_revalidated_quotient_independent_verifier_v109 as verifier


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v109_dependency_revalidated_quotient_campaign.json"
)
VERIFICATION_PATH = Path(
    ".tmp/exact-freeze/v109_dependency_revalidated_quotient_verification.json"
)


def test_v109_verifier_does_not_import_v109_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = {
        "acfqp.construction_k7_dependency_revalidated_quotient_campaign_v109",
        "acfqp.dependency_revalidated_quotient_campaign_core_v109",
        "acfqp.generic_dependency_revalidated_quotient_sequence_v109",
        "acfqp.generic_quotient_plan_dependency_receipt_v109",
        "acfqp.generic_dependency_revalidated_execution_receipt_v109",
    }
    assert imported.isdisjoint(forbidden)


def test_v109_independent_replay_verifies_registered_success():
    raw = CAMPAIGN_PATH.read_bytes()
    document = verifier.verify_dependency_revalidated_quotient_campaign_bytes_v109(
        raw
    )
    assert document["registered_gate_independently_verified"] is True
    assert document["producer_free_minimal_bfs_dependency_reconstruction"] is True
    assert document["verified_dependency_revalidated_cache_hit_count"] == 121
    assert document["verified_accounting"]["planning_compute_events_avoided"] == 1740
    assert document["verified_accounting"]["dependency_validation_checks"] == 4477
    assert document["cached_heuristic_used_as_safety_authority"] is False
    assert document["official_scalar_cost"] is None


def test_v109_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[-2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7DependencyRevalidatedQuotientIndependentVerifierV109Error
    ):
        verifier.verify_dependency_revalidated_quotient_campaign_bytes_v109(bytes(raw))


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION_PATH.exists(),
    reason="V109 independent verification has not been frozen",
)
def test_v109_exact_independent_verification_is_preserved():
    raw = VERIFICATION_PATH.read_bytes()
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert verifier.freeze_dependency_revalidated_quotient_verification_v109(
        CAMPAIGN_PATH.read_bytes()
    ) == raw
