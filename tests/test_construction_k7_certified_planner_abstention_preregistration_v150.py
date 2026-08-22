from pathlib import Path
import hashlib

from acfqp.construction_k7_certified_planner_abstention_preregistration_v150 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_certified_planner_abstention_preregistration_v150,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_certified_planner_abstention_preregistration_v150(
        (ROOT / "v149_cross_domain_relational_bank_preregistration.json").read_bytes(),
        (ROOT / "v149_cross_domain_relational_bank_failure.json").read_bytes(),
    )


def test_v150_preregisters_fresh_successor_without_outcomes():
    document = _freeze().to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"]["v149_identity_not_rerun"] is True
    assert document["registered_gate"][
        "incomplete_abstract_path_must_abstain_not_fail_or_execute"
    ] is True
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v150_preregistration_bytes_when_frozen():
    result = _freeze()
    if PREREGISTRATION_ID != "0" * 64:
        assert result.preregistration_id == PREREGISTRATION_ID
        assert len(result.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(result.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
