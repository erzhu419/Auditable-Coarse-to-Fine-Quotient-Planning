from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r8 as freeze,
)


def test_ordinal13_failure_freeze_is_exact_and_claim_bounded() -> None:
    frozen = freeze.freeze_ordinal13_failure_v180r12r4r8()
    contract = frozen.to_contract()

    assert frozen.freeze_id == freeze.ORDINAL13_FAILURE_FREEZE_ID
    assert frozen.freeze_id == freeze.EXPECTED_ORDINAL13_FAILURE_FREEZE_ID
    assert contract["formal_artifact_count"] == 13
    assert contract["post_failure_diagnostic_artifact_count"] == 1
    assert contract["post_failure_diagnostic_is_formal_campaign_artifact"] is False
    assert contract["all_self_ids_verified"] is True
    assert contract["self_id_count"] == 10
    assert contract["campaign_attempt_id"] == freeze.ORDINAL13_CAMPAIGN_ATTEMPT_ID
    assert (
        contract["inner_launch_failure_id"]
        == freeze.ORDINAL13_INNER_LAUNCH_FAILURE_ID
    )
    assert (
        contract["outer_service_failure_id"]
        == freeze.ORDINAL13_OUTER_SERVICE_FAILURE_ID
    )
    assert contract["event_ids"] == list(freeze.EXPECTED_EVENT_IDS)
    assert contract["event_kinds"] == [
        "ATTEMPT_OPEN",
        "PROCESS_BIRTH_INTENT",
        "PROCESS_BIRTH_OUTCOME",
    ]
    assert contract["completed_event_count"] == 3
    assert contract["successful_process_birth_outcome_recorded"] is True

    assert contract["source_root_count"] == 27
    assert contract["full_source_conformance"] is True
    assert contract["source_conformance_mismatch_count"] == 0
    assert contract["source_conformance_cause"] is None
    assert contract["full_host_conformance"] is True
    assert contract["host_conformance_mismatch_count"] == 0
    assert contract["host_conformance_cause"] is None
    assert contract["socket_buffer_capability_host_conformant"] is True
    assert contract["production_runtime_placement_t1_complete"] is True
    assert contract["production_unit_ownership_t1_acquired"] is True
    assert contract["formal_cgroup_topology_conformance_diagnostic"] is None
    assert contract["full_cgroup_topology_conformance_recorded"] is False
    assert contract["t2_t3_full_conformance_claimed"] is False

    assert contract["formal_failure_classification"] == {
        "failure_code": "INPUT_DRIFT",
        "message": "ConnectionResetError: (104, 'Connection reset by peer')",
    }
    assert contract["formal_failure_is_secondary"] is True
    assert contract["diagnosed_exact_cause"] == {
        "error_type": "RuntimeError",
        "message": "V180r12r4 precompiled source binding changed",
    }
    assert contract["diagnosed_exact_cause_is_primary"] is True
    assert contract["formal_campaign_failure_launch_child_created"] is False
    assert contract["formal_campaign_failure_launch_exec_observed"] is False
    assert contract["formal_campaign_failure_launch_pidfd_acquired"] is False

    assert contract["application_source_record_count"] == 85
    assert contract["third_party_source_record_count"] == 21
    assert contract["total_source_record_count"] == 106
    assert contract["source_binding_full_conformance"] is False
    assert contract["source_binding_mismatch_count"] == 21
    assert len(contract["source_binding_mismatch_rows"]) == 21
    assert contract["first_source_binding_mismatch_index"] == 85
    assert contract["first_source_binding_mismatch_module"] == "packaging"
    assert contract["source_binding_mismatch_rows"][0]["field"] == (
        "source_records[85].source_path.repository_prefix"
    )
    assert contract["source_binding_mismatch_rows"][-1]["field"] == (
        "source_records[105].source_path.repository_prefix"
    )
    observation = contract["binding_observation"]
    population = observation["property_snapshots"]["record_population"]
    assert population == {
        "acfqp_record_count": 85,
        "first_mismatch_index": 85,
        "first_mismatch_module": "packaging",
        "packaging_record_count": 17,
        "third_party_record_count": 21,
        "tomli_record_count": 4,
        "total_source_record_count": 106,
    }
    assert observation["production_unit_ownership_t1_acquired"] is True
    assert observation["source_binding_unit_ownership_evaluated"] is False
    assert observation["source_binding_full_conformance"] is False
    assert observation["full_cgroup_topology_conformance_recorded"] is False
    assert observation["formal_failure_classification"][
        "secondary_to_child_bootstrap_failure"
    ] is True

    assert contract["cleanup_complete"] is True
    assert contract["post_failure_measurement_root_state"] == "ABSENT"
    assert contract["formal_service_collected"] is True
    assert contract["process_may_remain"] is False
    assert contract["oom_event_count"] == 0
    assert contract["memory_peak_bytes"] == 68_714_496
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


def test_ordinal13_freeze_verifies_all_formal_self_ids() -> None:
    documents, raw_by_role = freeze._read_documents(
        freeze._DEFAULT_RETAINED_ROOT
    )

    assert len(freeze._FORMAL_ARTIFACT_FACTS) == 13
    assert len(documents) == len(raw_by_role) == 14
    assert all(fact.formal for fact in freeze._FORMAL_ARTIFACT_FACTS)
    assert freeze._DIAGNOSTIC_ARTIFACT_FACT.formal is False
    specifications = (
        (
            "materialization",
            "materialization_terminal_id",
            freeze.EXPECTED_MATERIALIZATION_TERMINAL_ID,
            None,
        ),
        (
            "outer_service_attempt",
            "service_launch_attempt_id",
            freeze.EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID,
            freeze._SERVICE_ATTEMPT_DOMAIN,
        ),
        (
            "inner_launch_attempt",
            "launch_attempt_id",
            freeze.EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
            None,
        ),
        (
            "outer_service_failure",
            "service_launch_failure_id",
            freeze.EXPECTED_OUTER_SERVICE_FAILURE_ID,
            freeze._SERVICE_FAILURE_DOMAIN,
        ),
        (
            "inner_launch_failure",
            "launch_failure_id",
            freeze.EXPECTED_INNER_LAUNCH_FAILURE_ID,
            None,
        ),
        (
            "campaign_attempt",
            "campaign_attempt_record_id",
            freeze.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
            freeze._ATTEMPT_RECORD_DOMAIN,
        ),
        (
            "campaign_failure",
            "failure_state_id",
            freeze.EXPECTED_CAMPAIGN_FAILURE_ID,
            freeze._FAILURE_DOMAIN,
        ),
    )
    for role, field, expected, domain in specifications:
        assert freeze._require_self_id(
            documents[role], field, expected, domain=domain
        ) == expected
    for role, expected in zip(
        (
            "attempt_open_event",
            "process_birth_intent_event",
            "process_birth_outcome_event",
        ),
        freeze.EXPECTED_EVENT_IDS,
        strict=True,
    ):
        assert freeze._require_self_id(
            documents[role],
            "event_id",
            expected,
            domain=freeze._EVENT_DOMAIN,
        ) == expected


@pytest.mark.parametrize(
    ("relative_path", "role"),
    [
        ("raw/campaign/measurement_failure.json", "campaign_failure"),
        (
            "raw/post_failure_precompiled_source_binding_observation.json",
            "precompiled_source_binding_observation",
        ),
    ],
)
def test_ordinal13_failure_freeze_rejects_raw_artifact_drift(
    tmp_path: Path,
    relative_path: str,
    role: str,
) -> None:
    candidate = tmp_path / "ordinal13"
    shutil.copytree(freeze._DEFAULT_RETAINED_ROOT, candidate)
    target = candidate / relative_path
    target.chmod(0o600)
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(
        freeze.Ordinal13FailureFreezeV180r12r4r8Error,
        match=rf"{role} raw bytes changed",
    ):
        freeze.freeze_ordinal13_failure_v180r12r4r8(candidate)
