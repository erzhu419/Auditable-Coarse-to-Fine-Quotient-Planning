from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r7 as freeze,
)


def test_ordinal12_failure_freeze_is_exact_and_claim_bounded() -> None:
    frozen = freeze.freeze_ordinal12_failure_v180r12r4r7()
    contract = frozen.to_contract()

    assert frozen.freeze_id == freeze.ORDINAL12_FAILURE_FREEZE_ID
    assert frozen.freeze_id == freeze.EXPECTED_ORDINAL12_FAILURE_FREEZE_ID
    assert contract["formal_artifact_count"] == 12
    assert contract["post_failure_diagnostic_artifact_count"] == 1
    assert contract["post_failure_diagnostic_is_formal_campaign_artifact"] is False
    assert contract["all_self_ids_verified"] is True
    assert contract["self_id_count"] == 9

    assert contract["campaign_attempt_id"] == freeze.ORDINAL12_CAMPAIGN_ATTEMPT_ID
    assert (
        contract["inner_launch_failure_id"]
        == freeze.ORDINAL12_INNER_LAUNCH_FAILURE_ID
    )
    assert (
        contract["outer_service_failure_id"]
        == freeze.ORDINAL12_OUTER_SERVICE_FAILURE_ID
    )
    assert contract["event_ids"] == list(freeze.EXPECTED_EVENT_IDS)
    assert contract["event_kinds"] == [
        "ATTEMPT_OPEN",
        "PROCESS_BIRTH_INTENT",
    ]
    assert contract["completed_event_count"] == 2

    assert contract["prelaunch_materialization_succeeded"] is True
    assert contract["source_root_count"] == 26
    assert contract["full_source_conformance"] is True
    assert contract["source_conformance_mismatch_count"] == 0
    assert contract["source_conformance_cause"] is None
    assert contract["full_host_conformance"] is True
    assert contract["host_conformance_mismatch_count"] == 0
    assert contract["host_conformance_cause"] is None

    assert contract["failure_code"] == "SUPERVISOR_BIRTH_FAILURE"
    assert contract["failure_stage"] == "SOCKET_BUFFER_CONFIGURATION"
    assert contract["launch_child_created"] is False
    assert contract["launch_exec_observed"] is False
    assert contract["launch_pidfd_acquired"] is False
    assert contract["production_runtime_placement_t1_complete"] is True
    assert contract["production_runtime_placement_t2_reached"] is False
    assert contract["production_runtime_placement_t3_reached"] is False
    assert contract["t2_t3_full_conformance_reached"] is False
    assert contract["cgroup_topology_conformance_diagnostic"] is None

    assert contract["socket_capability_full_conformance"] is False
    assert contract["socket_capability_mismatch_count"] == 6
    assert len(contract["socket_capability_mismatch_rows"]) == 6
    assert contract["socket_capability_cause"] == {
        "error_type": "V180R12R4RuntimeError",
        "failure_code": "SOCKET_BUFFER_CAPABILITY_CONFORMANCE_FAILURE",
        "message": (
            "effective seqpacket send/receive buffers are below the frozen "
            "two-frame minimum"
        ),
        "scope": "PRE_CHILD_IPC_SEQPACKET_CAPABILITY",
    }
    assert contract["socket_request_bytes"] == 1_048_576
    assert contract["socket_required_effective_min_bytes"] == 2_097_152

    assert contract["cleanup_complete"] is True
    assert contract["post_failure_measurement_root_state"] == "ABSENT"
    assert contract["formal_service_collected"] is True
    assert contract["process_may_remain"] is False
    assert contract["oom_event_count"] == 0
    assert contract["memory_peak_bytes"] == 262_144
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
    assert contract["repair_scope"] == freeze.REPAIR_SCOPE


def test_ordinal12_freeze_verifies_every_canonical_self_id() -> None:
    documents, raw_by_role = freeze._read_documents(
        freeze._DEFAULT_RETAINED_ROOT
    )

    assert len(freeze._FORMAL_ARTIFACT_FACTS) == 12
    assert len(documents) == len(raw_by_role) == 13
    assert all(fact.formal for fact in freeze._FORMAL_ARTIFACT_FACTS)
    assert freeze._DIAGNOSTIC_ARTIFACT_FACT.formal is False
    assert freeze._require_self_id(
        documents["materialization"],
        "materialization_terminal_id",
        freeze.EXPECTED_MATERIALIZATION_TERMINAL_ID,
    ) == freeze.EXPECTED_MATERIALIZATION_TERMINAL_ID
    assert freeze._require_self_id(
        documents["outer_service_attempt"],
        "service_launch_attempt_id",
        freeze.EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID,
        domain=freeze._SERVICE_ATTEMPT_DOMAIN,
    ) == freeze.EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID
    assert freeze._require_self_id(
        documents["inner_launch_attempt"],
        "launch_attempt_id",
        freeze.EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
    ) == freeze.EXPECTED_INNER_LAUNCH_ATTEMPT_ID
    assert freeze._require_self_id(
        documents["outer_service_failure"],
        "service_launch_failure_id",
        freeze.EXPECTED_OUTER_SERVICE_FAILURE_ID,
        domain=freeze._SERVICE_FAILURE_DOMAIN,
    ) == freeze.EXPECTED_OUTER_SERVICE_FAILURE_ID
    assert freeze._require_self_id(
        documents["inner_launch_failure"],
        "launch_failure_id",
        freeze.EXPECTED_INNER_LAUNCH_FAILURE_ID,
    ) == freeze.EXPECTED_INNER_LAUNCH_FAILURE_ID
    assert freeze._require_self_id(
        documents["campaign_attempt"],
        "campaign_attempt_record_id",
        freeze.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        domain=freeze._ATTEMPT_RECORD_DOMAIN,
    ) == freeze.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID
    for role, expected in zip(
        ("attempt_open_event", "process_birth_intent_event"),
        freeze.EXPECTED_EVENT_IDS,
        strict=True,
    ):
        assert freeze._require_self_id(
            documents[role],
            "event_id",
            expected,
            domain=freeze._EVENT_DOMAIN,
        ) == expected
    assert freeze._require_self_id(
        documents["campaign_failure"],
        "failure_state_id",
        freeze.EXPECTED_CAMPAIGN_FAILURE_ID,
        domain=freeze._FAILURE_DOMAIN,
    ) == freeze.EXPECTED_CAMPAIGN_FAILURE_ID


@pytest.mark.parametrize(
    ("relative_path", "role"),
    [
        ("raw/campaign/measurement_failure.json", "campaign_failure"),
        (
            "raw/post_failure_socket_capability_observation.json",
            "socket_capability_observation",
        ),
    ],
)
def test_ordinal12_failure_freeze_rejects_raw_artifact_drift(
    tmp_path: Path,
    relative_path: str,
    role: str,
) -> None:
    candidate = tmp_path / "ordinal12"
    shutil.copytree(freeze._DEFAULT_RETAINED_ROOT, candidate)
    target = candidate / relative_path
    target.chmod(0o600)
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(
        freeze.Ordinal12FailureFreezeV180r12r4r7Error,
        match=rf"{role} raw bytes changed",
    ):
        freeze.freeze_ordinal12_failure_v180r12r4r7(candidate)
