from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r6 as freeze,
)


def test_ordinal11_failure_freeze_is_exact_and_claim_bounded() -> None:
    frozen = freeze.freeze_ordinal11_failure_v180r12r4r6()
    contract = frozen.to_contract()

    assert frozen.freeze_id == freeze.ORDINAL11_FAILURE_FREEZE_ID
    assert frozen.freeze_id == freeze.EXPECTED_ORDINAL11_FAILURE_FREEZE_ID
    assert contract["full_source_conformance"] is True
    assert contract["source_root_count"] == 25
    assert contract["full_host_conformance"] is True
    assert contract["host_conformance_mismatch_count"] == 0
    assert contract["host_conformance_cause"] is None
    assert contract["host_conformance"]["mismatch_rows"] == []

    assert contract["scientific_attempt_opened"] is True
    assert contract["event_kinds"] == ["ATTEMPT_OPEN"]
    assert contract["completed_event_count"] == 1
    assert contract["failure_code"] == "CGROUP_TOPOLOGY_CONFORMANCE_FAILURE"
    assert contract["full_t1_t2_conformance"] is False
    assert contract["topology_diagnostic_unit_ownership_acquired"] is False
    assert contract["t1_t2_same_formal_service"] is True
    assert contract["t1_t2_same_source_membership"] is True
    assert contract["t1_t2_same_service_directory"] is True
    assert contract["only_mismatch"] == {
        "field": "t2.pid",
        "expected": 528_492,
        "observed": 528_493,
    }
    assert contract["exact_failure_cause"] == "T1_T2_PID_ROLE_CONFLATION"
    assert contract["t1_process_role"] == "SERVICE_ENTRY_LAUNCHER"
    assert contract["t2_process_role"] == "BOOTSTRAP_CHILD"
    assert contract["distinct_process_roles"] is True

    assert contract["predecessor_t2_schema"].endswith("t2.v1")
    assert contract["successor_t2_schema"].endswith("t2.v2")
    assert contract["predecessor_t2_exact_field_count"] == 19
    assert contract["ordinal11_t3_present"] is False

    assert contract["measurement_root_created_before_failure"] is True
    assert contract["cleanup_complete"] is True
    assert contract["post_child_measurement_root_state"] == "ABSENT"
    assert contract["residual_tree_or_process_possible"] is False
    assert contract["process_may_remain"] is False
    assert contract["formal_service_collected"] is True

    assert contract["counter_record_count"] == 0
    assert contract["work_vector_count"] == 0
    assert contract["comparison_vector_count"] == 0
    assert contract["counter_records_issued"] is False
    assert contract["work_vectors_issued"] is False
    assert contract["comparison_vectors_issued"] is False
    assert set(contract["gate_statuses"].values()) == {"NOT_RUN"}
    assert contract["official_execution_allowed"] is False
    assert contract["terminal_present"] is False
    assert contract["independent_replay_present"] is False
    assert contract["scientific_effect_observed"] is False
    assert contract["scientific_effect_claimed"] is False
    assert contract["identity_consumed"] is True
    assert contract["same_identity_rerun_forbidden"] is True
    assert contract["fresh_successor_identity_required"] is True


def test_ordinal11_freeze_uses_predecessor_t2_v1_exact_keyset() -> None:
    documents, raw_by_role = freeze._read_documents(
        freeze._DEFAULT_RETAINED_ROOT
    )

    diagnostic = documents["campaign_failure"][
        "cgroup_topology_conformance_diagnostic"
    ]
    t2 = diagnostic["property_snapshots"]["unit_ownership"][
        "production_runtime_placement_t2"
    ]
    assert t2["schema"] == freeze._PREDECESSOR_T2_V1_SCHEMA
    assert set(t2) == freeze._PREDECESSOR_T2_V1_FIELDS
    assert "parent_pid" not in t2
    assert len(documents) == len(raw_by_role) == 11
    assert documents["attempt_open_event"]["event_kind"] == "ATTEMPT_OPEN"
    assert documents["campaign_failure"]["completed_event_count"] == 1


def test_ordinal11_failure_freeze_rejects_raw_artifact_drift(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "ordinal11"
    shutil.copytree(freeze._DEFAULT_RETAINED_ROOT, candidate)
    target = candidate / "raw/campaign/measurement_failure.json"
    target.chmod(0o600)
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(
        freeze.Ordinal11FailureFreezeV180r12r4r6Error,
        match="campaign_failure raw bytes changed",
    ):
        freeze.freeze_ordinal11_failure_v180r12r4r6(candidate)
