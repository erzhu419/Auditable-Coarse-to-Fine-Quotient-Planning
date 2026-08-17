from __future__ import annotations

import hashlib

from acfqp import construction_k7_atomic_composition_failure_v49r1 as failure


def test_v49r1_failure_preserves_changed_existing_relation_counterexample() -> None:
    frozen = failure.freeze_atomic_composition_failure_v49r1()
    assert frozen.failure_id == failure.FAILURE_ID
    assert len(frozen.canonical_bytes) == failure.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == failure.EXPECTED_CANONICAL_SHA256
    document = frozen.to_document()
    assert document["missing_only_recovery_insufficient"] is True
    assert document["target_local_ground_support_queries_performed"] == 1
    assert document["campaign_artifact_issued"] is False
    assert document["correction_under_same_identity_forbidden"] is True
    assert document["official_execution_allowed"] is False

