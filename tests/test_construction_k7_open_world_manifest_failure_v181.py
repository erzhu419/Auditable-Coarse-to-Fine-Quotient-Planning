from pathlib import Path

from acfqp.construction_k7_open_world_manifest_failure_v181 import (
    freeze_open_world_manifest_failure_v181,
)


def test_failure_preserves_missing_reveal_without_outcome_access() -> None:
    document = freeze_open_world_manifest_failure_v181().to_document()
    assert document["failure_code"] == "COMMITTED_REVEAL_PREIMAGE_NOT_RETAINED"
    assert document["recovered_manifest_indices"] == [0]
    assert document["missing_manifest_indices"] == [1, 2]
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False
    assert document["same_identity_rerun_forbidden"] is True


def test_failure_keeps_all_positive_and_official_claims_locked() -> None:
    document = freeze_open_world_manifest_failure_v181().to_document()
    assert document["success_claimed"] is False
    assert document["sample_efficiency_claimed"] is False
    assert document["total_work_dominance_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_retained_failure_bytes_are_exact() -> None:
    value = freeze_open_world_manifest_failure_v181()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181_open_world_manifest_failure.json"
    )
    assert path.read_bytes() == value.canonical_bytes
