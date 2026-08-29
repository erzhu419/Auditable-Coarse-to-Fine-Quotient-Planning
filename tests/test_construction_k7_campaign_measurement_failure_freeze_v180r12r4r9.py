from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

import pytest

from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r9 as freeze,
)


def test_ordinal14_failure_freeze_is_exact_and_claim_bounded() -> None:
    frozen = freeze.freeze_ordinal14_failure_v180r12r4r9()
    contract = frozen.to_contract()

    assert frozen.freeze_id == freeze.ORDINAL14_FAILURE_FREEZE_ID
    assert frozen.freeze_id == freeze.EXPECTED_ORDINAL14_FAILURE_FREEZE_ID
    assert contract["formal_artifact_count"] == 21
    assert contract["post_failure_diagnostic_artifact_count"] == 1
    assert contract["post_failure_diagnostic_is_formal_campaign_artifact"] is False
    assert contract["all_retained_document_self_ids_verified"] is True
    assert contract["self_id_document_count"] == 18
    assert contract["unique_self_id_count"] == 17

    assert contract["campaign_attempt_id"] == freeze.EXPECTED_CAMPAIGN_ATTEMPT_ID
    assert (
        contract["campaign_attempt_record_id"]
        == freeze.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID
    )
    assert (
        contract["measurement_terminal_id"]
        == freeze.EXPECTED_MEASUREMENT_TERMINAL_ID
    )
    assert contract["verification_id"] == freeze.EXPECTED_VERIFICATION_ID
    assert (
        contract["verification_inner_launch_failure_id"]
        == freeze.EXPECTED_INNER_LAUNCH_FAILURE_ID
    )
    assert (
        contract["verification_outer_service_failure_id"]
        == freeze.EXPECTED_OUTER_SERVICE_FAILURE_ID
    )

    assert contract["source_root_count"] == 28
    assert contract["full_source_conformance"] is True
    assert contract["full_host_conformance"] is True
    assert contract["measurement_succeeded"] is True
    assert contract["measurement_full_cgroup_topology_conformance"] is True
    assert contract["measurement_runtime_placement_t1_t2_t3_complete"] is True
    assert contract["verification_unit_ownership_t1_acquired"] is True
    assert contract["verification_payload_conformance"] is True
    assert contract["verification_payload_and_replay_byte_identical"] is True
    assert contract["verification_transport_success"] is False
    assert contract["full_verification_launch_conformance"] is False
    assert contract["producer_free_verification_attempted"] is True
    assert contract["producer_free_verification_completed"] is False
    assert contract["verification_inner_launch_receipt_present"] is False
    assert contract["verification_outer_service_receipt_present"] is False

    assert contract["formal_mismatch_count"] == 1
    assert contract["formal_mismatch_rows"] == [
        {
            "expected": True,
            "field": "source_bound_runner_git_audit.complete",
            "observed": False,
        }
    ]
    assert contract["diagnosed_exact_cause"] == {
        "diagnosis_basis": (
            "EXACT_UNTRUNCATED_CHILD_STDERR_PLUS_FROZEN_MANIFEST_AND_"
            "VERIFICATION_RUNNER_CONTROL_FLOW"
        ),
        "error_type": "_RunnerSecondaryObservation",
        "failure_code": (
            "TARGET_AGNOSTIC_SIX_PROCESS_GIT_AUDIT_APPLIED_TO_"
            "VERIFICATION_RUNNER"
        ),
        "message": freeze.EXPECTED_DIAGNOSED_MESSAGE,
        "scope": (
            "POST_RUN_BOOTSTRAP_SECONDARY_OBSERVATION_AFTER_DURABLE_"
            "VERIFICATION_PUBLICATION"
        ),
    }

    gates = contract["gate_statuses_by_layer"]
    assert gates["measurement_terminal"]["COUNTER_COMPLETENESS_GATE"] == (
        "PENDING_INDEPENDENT_REPLAY"
    )
    assert gates["verification_payload"]["COUNTER_COMPLETENESS_GATE"] == "PASS"
    assert gates["verification_payload"][
        "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS"
    ] == "PASS"
    assert set(gates["verification_transport"].values()) == {"NOT_RUN"}
    assert contract["counter_pass_is_payload_level_only"] is True
    assert contract["counter_record_count"] == 9
    assert contract["path_receipt_count"] == 9
    assert contract["work_vector_count"] == 1
    assert contract["comparison_vector_count"] == 1
    assert contract["native_zero_attestation_count"] == 1
    assert contract["official_execution_allowed"] is False
    assert contract["scientific_success_claimed"] is False
    assert contract["full_ordinal14_occurrence_success"] is False
    assert contract["identity_consumed"] is True
    assert contract["same_identity_rerun_forbidden"] is True
    assert contract["fresh_successor_identity_required"] is True
    assert contract["repair_scope"] == freeze.REPAIR_SCOPE


def test_ordinal14_failure_freeze_retains_complete_property_snapshots() -> None:
    documents, _raw_by_role = freeze._read_documents(
        freeze._DEFAULT_RETAINED_ROOT
    )
    snapshots = freeze.freeze_ordinal14_failure_v180r12r4r9().to_contract()[
        "property_snapshots"
    ]

    assert set(snapshots) == {
        "source_conformance",
        "host_conformance",
        "measurement_cgroup_topology",
        "measurement_runtime_placement_t1",
        "measurement_runtime_placement_t2",
        "measurement_runtime_placement_t3",
        "measurement_cgroup_lifecycle",
        "verification_runtime_placement_t1",
        "verification_payload",
        "verification_transport",
        "runner_git_contract_observation",
    }
    assert snapshots["host_conformance"] == documents["host_conformance"]
    assert snapshots["verification_payload"] == documents["verification"]
    assert snapshots["verification_transport"] == {
        "inner_failure": documents["verification_inner_failure"],
        "outer_failure": documents["verification_outer_failure"],
    }
    assert (
        snapshots["runner_git_contract_observation"]
        == documents["runner_git_contract_observation"]
    )

    os_documents = documents["os_receipt"]["os_receipt_documents"]
    assert snapshots["measurement_cgroup_topology"] in os_documents
    assert snapshots["measurement_cgroup_lifecycle"] in os_documents
    assert snapshots["measurement_runtime_placement_t1"] == snapshots[
        "measurement_cgroup_topology"
    ]["production_runtime_placement_t1"]
    assert snapshots["measurement_runtime_placement_t2"] == snapshots[
        "measurement_cgroup_topology"
    ]["production_runtime_placement_t2"]
    t3 = snapshots["measurement_runtime_placement_t3"]
    assert t3["stable_across_boundaries"] is True
    assert set(t3) == {
        "before_getrandom",
        "immediately_before_clone3",
        "schema",
        "stable_across_boundaries",
        "target",
        "token",
        "unit_name",
    }
    assert t3["before_getrandom"]["boundary"] == "T3_BEFORE_GETRANDOM"
    assert t3["immediately_before_clone3"]["boundary"] == (
        "T3_IMMEDIATELY_BEFORE_CLONE3"
    )
    assert snapshots["verification_runtime_placement_t1"] == documents[
        "verification_inner_failure"
    ]["production_runtime_placement_t1"]


def test_ordinal14_freeze_does_not_invent_failure_ids_or_runtime_count() -> None:
    contract = freeze.freeze_ordinal14_failure_v180r12r4r9().to_contract()

    assert freeze._values_for_key(contract, "campaign_failure_id") == []
    assert freeze._values_for_key(contract, "verification_failure_id") == []
    assert contract["campaign_failure_artifact_present"] is False
    assert contract["verification_failure_artifact_present"] is False
    assert contract["runtime_observed_git_process_count"] is None
    assert contract["runtime_observed_git_process_count_recorded"] is False
    assert freeze._values_for_key(contract, "observed_process_count") == [None]

    inference = contract["static_control_flow_inference"]
    assert inference["runtime_observation"] is False
    assert inference["inferred_schedule_mismatch_rows"][0] == {
        "expected": 6,
        "field": "verification_runner_git_process_count",
        "inferred": 0,
    }


@pytest.mark.parametrize(
    ("relative_path", "role", "mode"),
    [
        (
            "v180r12r4_campaign_measurement_verification.json",
            "verification",
            0o400,
        ),
        (
            "raw/post_failure_runner_git_contract_observation.json",
            "runner_git_contract_observation",
            0o644,
        ),
    ],
)
def test_ordinal14_failure_freeze_rejects_raw_artifact_drift(
    relative_path: str,
    role: str,
    mode: int,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-ordinal14-", dir="/tmp") as root:
        candidate = Path(root) / "ordinal14"
        shutil.copytree(freeze._DEFAULT_RETAINED_ROOT, candidate)
        target = candidate / relative_path
        target.chmod(0o600)
        target.write_bytes(target.read_bytes() + b"\n")
        target.chmod(mode)

        with pytest.raises(
            freeze.Ordinal14FailureFreezeV180r12r4r9Error,
            match=rf"{role} raw bytes changed",
        ):
            freeze.freeze_ordinal14_failure_v180r12r4r9(candidate)


def test_ordinal14_failure_freeze_accepts_git_checkout_mode() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-ordinal14-", dir="/tmp") as root:
        candidate = Path(root) / "ordinal14"
        shutil.copytree(freeze._DEFAULT_RETAINED_ROOT, candidate)
        target = candidate / "v180r12r4_campaign_measurement_verification.json"
        target.chmod(0o644)

        contract = freeze.freeze_ordinal14_failure_v180r12r4r9(candidate).to_contract()
        assert contract["formal_artifact_facts"]["verification"]["mode"] == 0o400
