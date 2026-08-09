from __future__ import annotations

import copy
from dataclasses import fields
import errno
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace

import pytest

from acfqp import construction_k7_h1_actual_observed_supervisor_birth_v1 as b2c_v1
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1
from acfqp import construction_k7_h1_domain_registry_extension_v12 as domains_v12
from acfqp import construction_k7_h1_domain_registry_extension_v15 as domains_v15
from acfqp import construction_k7_h1_domain_registry_extension_v16 as domains_v16
from acfqp import construction_k7_h1_domain_registry_extension_v17 as domains_v17
from acfqp import phase3e_ids as ids_v1


DELEGATED_PARENT = os.environ.get("ACFQP_E5A_DELEGATED_PARENT_CGROUP")
requires_delegated_parent = pytest.mark.skipif(
    not DELEGATED_PARENT,
    reason="one fresh delegated E5A parent cgroup was not registered",
)
_SUBPROCESS_HELPER = Path(__file__).with_name("_b2c_actual_birth_subprocess.py")


@pytest.fixture
def delegated_parent_fd():
    assert DELEGATED_PARENT is not None
    descriptor = os.open(
        Path(DELEGATED_PARENT),
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    assert e5a_v1._child_directories(descriptor) == ()
    try:
        yield descriptor
    finally:
        assert e5a_v1._child_directories(descriptor) == ()
        os.close(descriptor)


def _run_real_subprocess_case(
    stage: str,
    journals: tuple[Path, Path],
) -> dict:
    completed = subprocess.run(
        [
            sys.executable,
            os.fspath(_SUBPROCESS_HELPER),
            stage,
            os.fspath(journals[0]),
            os.fspath(journals[1]),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )
    return json.loads(completed.stdout)


@pytest.fixture
def private_journal_pair():
    first = Path(tempfile.mkdtemp(prefix="acfqp-b2c-b2b-", dir="/tmp"))
    second = Path(tempfile.mkdtemp(prefix="acfqp-b2c-own-", dir="/tmp"))
    first.chmod(0o700)
    second.chmod(0o700)
    try:
        yield first, second
    finally:
        for directory in (first, second):
            for child in directory.iterdir():
                child.unlink()
            directory.rmdir()


def _content_document(domain: str, id_field: str, **payload: object) -> dict:
    document = dict(payload)
    document[id_field] = b2c_v1._domain_id(domain, document)
    return document


def _reissue_content_document(
    document: dict,
    *,
    domain: str,
    id_field: str,
) -> None:
    payload = dict(document)
    payload.pop(id_field, None)
    document[id_field] = b2c_v1._domain_id(domain, payload)


def _reissue_result(document: dict) -> bytes:
    _reissue_content_document(
        document,
        domain=(
            domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_SLICE_RESULT_V1_DOMAIN
        ),
        id_field="bounded_supervisor_birth_slice_result_id",
    )
    return ids_v1.canonical_json_bytes(document)


def _portable_result_bytes() -> bytes:
    occurrence = {
        "logical_occurrence_id": "occurrence",
        "route_attempt_id": "attempt",
        "decision_point_id": "decision",
        "BuildEpoch_id": "epoch",
    }
    hierarchy = _content_document(
        domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_HIERARCHY_V1_DOMAIN,
        "h1_route_wide_cgroup_hierarchy_id",
        **occurrence,
    )
    hierarchy_id = hierarchy["h1_route_wide_cgroup_hierarchy_id"]
    successor = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_SUCCESSOR_V1_DOMAIN,
        "h1_e5a_runtime_lease_successor_id",
        h1_route_wide_cgroup_hierarchy_id=hierarchy_id,
        **occurrence,
    )
    successor_id = successor["h1_e5a_runtime_lease_successor_id"]
    prebinding = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
        "supervisor_birth_source_prebinding_id",
        runtime_successor_id=successor_id,
    )
    prebinding_id = prebinding["supervisor_birth_source_prebinding_id"]
    preregistration = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_STAGE_PLAN_V1_DOMAIN,
        "guardian_runtime_genesis_preregistration_id",
        role="guardian-preregistration",
    )
    preregistration_id = preregistration[
        "guardian_runtime_genesis_preregistration_id"
    ]
    guardian_source = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
        "execution_source_closure_id",
        preregistration_id=preregistration_id,
    )
    guardian_source_id = guardian_source["execution_source_closure_id"]
    genesis = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_GUARDIAN_SESSION_GENESIS_V1_DOMAIN,
        "guardian_session_genesis_id",
        h1_e5a_runtime_lease_successor_id=successor_id,
        preregistration_id=preregistration_id,
        execution_source_closure_id=guardian_source_id,
    )
    genesis_id = genesis["guardian_session_genesis_id"]
    intent = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_INTENT_V1_DOMAIN,
        "actual_process_birth_intent_id",
        execution_source_closure_id=guardian_source_id,
        guardian_session_genesis_id=genesis_id,
    )
    intent_id = intent["actual_process_birth_intent_id"]
    permit = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_PERMIT_V1_DOMAIN,
        "actual_process_birth_permit_id",
        guardian_session_genesis_id=genesis_id,
        execution_source_closure_id=guardian_source_id,
        actual_process_birth_intent_id=intent_id,
    )
    permit_id = permit["actual_process_birth_permit_id"]
    takeover = _content_document(
        domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN,
        "supervisor_birth_companion_takeover_id",
        supervisor_birth_source_prebinding_id=prebinding_id,
        guardian_session_genesis_id=genesis_id,
        actual_process_birth_intent_id=intent_id,
        actual_process_birth_permit_id=permit_id,
        runtime_successor_id=successor_id,
    )
    takeover_id = takeover["supervisor_birth_companion_takeover_id"]
    consumption = _content_document(
        domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_PERMIT_CONSUMPTION_V1_DOMAIN,
        "actual_process_birth_permit_consumption_id",
        supervisor_birth_companion_takeover_id=takeover_id,
        guardian_session_genesis_id=genesis_id,
        actual_process_birth_intent_id=intent_id,
        actual_process_birth_permit_id=permit_id,
        supervisor_birth_source_prebinding_id=prebinding_id,
        runtime_successor_id=successor_id,
    )
    consumption_id = consumption["actual_process_birth_permit_consumption_id"]

    child_pid = 7331
    protocol: dict[str, dict] = {}
    protocol["pid_cell_binding"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_SHARED_PID_CELL_BINDING_V1_DOMAIN,
        "shared_pid_cell_binding_id",
        actual_process_birth_permit_consumption_id=consumption_id,
        child_pid=child_pid,
    )
    protocol["pidfd_escrow"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_PIDFD_ESCROW_RECEIPT_V2_DOMAIN,
        "pidfd_escrow_receipt_id",
        shared_pid_cell_binding_id=protocol["pid_cell_binding"][
            "shared_pid_cell_binding_id"
        ],
        actual_process_birth_permit_consumption_id=consumption_id,
        child_pid=child_pid,
    )
    protocol["live_cgroup_snapshot_1"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
        "cgroup_membership_observation_id",
        pidfd_escrow_receipt_id=protocol["pidfd_escrow"][
            "pidfd_escrow_receipt_id"
        ],
        child_pid=child_pid,
        observation_ordinal=1,
    )
    protocol["birth_observation"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_OBSERVATION_V1_DOMAIN,
        "actual_process_birth_observation_id",
        actual_process_birth_permit_consumption_id=consumption_id,
        shared_pid_cell_binding_id=protocol["pid_cell_binding"][
            "shared_pid_cell_binding_id"
        ],
        pidfd_escrow_receipt_id=protocol["pidfd_escrow"][
            "pidfd_escrow_receipt_id"
        ],
        cgroup_membership_observation_id=protocol["live_cgroup_snapshot_1"][
            "cgroup_membership_observation_id"
        ],
        child_pid=child_pid,
    )
    birth_id = protocol["birth_observation"]["actual_process_birth_observation_id"]
    protocol["live_cgroup_snapshot_2"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
        "cgroup_membership_observation_id",
        actual_process_birth_observation_id=birth_id,
        child_pid=child_pid,
        observation_ordinal=2,
    )
    protocol["guardian_birth_ack"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_GUARDIAN_BIRTH_ACK_V1_DOMAIN,
        "guardian_birth_ack_id",
        actual_process_birth_observation_id=birth_id,
        first_cgroup_membership_observation_id=protocol[
            "live_cgroup_snapshot_1"
        ]["cgroup_membership_observation_id"],
        second_cgroup_membership_observation_id=protocol[
            "live_cgroup_snapshot_2"
        ]["cgroup_membership_observation_id"],
    )
    protocol["creator_release"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_RELEASE_V1_DOMAIN,
        "actual_process_creator_release_id",
        guardian_birth_ack_id=protocol["guardian_birth_ack"][
            "guardian_birth_ack_id"
        ],
        actual_process_birth_observation_id=birth_id,
    )
    protocol["death_observation"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_DEATH_OBSERVATION_V1_DOMAIN,
        "actual_process_death_observation_id",
        actual_process_creator_release_id=protocol["creator_release"][
            "actual_process_creator_release_id"
        ],
        pidfd_escrow_receipt_id=protocol["pidfd_escrow"][
            "pidfd_escrow_receipt_id"
        ],
        child_pid=child_pid,
    )
    protocol["creator_reap"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_REAP_ATTESTATION_V1_DOMAIN,
        "actual_process_creator_reap_attestation_id",
        actual_process_death_observation_id=protocol["death_observation"][
            "actual_process_death_observation_id"
        ],
        actual_process_birth_observation_id=birth_id,
        child_pid=child_pid,
    )
    reap_id = protocol["creator_reap"][
        "actual_process_creator_reap_attestation_id"
    ]
    protocol["empty_cgroup_snapshot_1"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
        "cgroup_membership_observation_id",
        actual_process_creator_reap_attestation_id=reap_id,
        observation_ordinal=3,
    )
    protocol["empty_cgroup_snapshot_2"] = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
        "cgroup_membership_observation_id",
        first_empty_cgroup_membership_observation_id=protocol[
            "empty_cgroup_snapshot_1"
        ]["cgroup_membership_observation_id"],
        observation_ordinal=4,
    )
    protocol["peak_observation"] = _content_document(
        domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN,
        "bounded_supervisor_birth_peak_observation_id",
        actual_process_creator_reap_attestation_id=reap_id,
        first_empty_cgroup_membership_observation_id=protocol[
            "empty_cgroup_snapshot_1"
        ]["cgroup_membership_observation_id"],
        second_empty_cgroup_membership_observation_id=protocol[
            "empty_cgroup_snapshot_2"
        ]["cgroup_membership_observation_id"],
        runtime_successor_id=successor_id,
        memory_peak_bytes=4096,
    )
    peak_id = protocol["peak_observation"][
        "bounded_supervisor_birth_peak_observation_id"
    ]
    protocol_id_fields = {
        "pid_cell_binding": "shared_pid_cell_binding_id",
        "pidfd_escrow": "pidfd_escrow_receipt_id",
        "live_cgroup_snapshot_1": "cgroup_membership_observation_id",
        "birth_observation": "actual_process_birth_observation_id",
        "live_cgroup_snapshot_2": "cgroup_membership_observation_id",
        "guardian_birth_ack": "guardian_birth_ack_id",
        "creator_release": "actual_process_creator_release_id",
        "death_observation": "actual_process_death_observation_id",
        "creator_reap": "actual_process_creator_reap_attestation_id",
        "empty_cgroup_snapshot_1": "cgroup_membership_observation_id",
        "empty_cgroup_snapshot_2": "cgroup_membership_observation_id",
        "peak_observation": "bounded_supervisor_birth_peak_observation_id",
    }
    protocol_ids = {
        name: protocol[name][protocol_id_fields[name]]
        for name in b2c_v1._RESULT_PROTOCOL_RECORD_ORDER
    }
    barrier = _content_document(
        domains_v17.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_CONSUMED_CLEANUP_BARRIER_V1_DOMAIN,
        "guardian_runtime_consumed_cleanup_barrier_id",
        actual_process_birth_permit_consumption_id=consumption_id,
        actual_process_birth_observation_id=birth_id,
        actual_process_creator_reap_attestation_id=reap_id,
        bounded_supervisor_birth_peak_observation_id=peak_id,
        runtime_successor_id=successor_id,
        cleanup_outcome="BIRTH_REAP_PEAK_COMPLETE",
    )
    source_closure = _content_document(
        domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_CLEANUP_CLOSURE_V1_DOMAIN,
        "h1_route_wide_cgroup_cleanup_closure_id",
        h1_route_wide_cgroup_hierarchy_id=hierarchy_id,
        actual_process_birth_observation_id=birth_id,
        actual_process_creator_reap_attestation_id=reap_id,
        bounded_supervisor_birth_peak_observation_id=peak_id,
        **occurrence,
    )
    source_closure_id = source_closure[
        "h1_route_wide_cgroup_cleanup_closure_id"
    ]
    runtime_closure = _content_document(
        domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN,
        "h1_route_wide_runtime_lease_closure_id",
        h1_e5a_runtime_lease_successor_id=successor_id,
        h1_route_wide_cgroup_hierarchy_id=hierarchy_id,
        source_e5a_cleanup_closure_id=source_closure_id,
        actual_process_birth_observation_id=birth_id,
        actual_process_creator_reap_attestation_id=reap_id,
        bounded_supervisor_birth_peak_observation_id=peak_id,
        **occurrence,
    )

    artifacts = {
        "hierarchy": hierarchy,
        "runtime_successor": successor,
        "source_prebinding": prebinding,
        "guardian_preregistration": preregistration,
        "guardian_source_closure": guardian_source,
        "guardian_genesis": genesis,
        "birth_intent": intent,
        "birth_permit": permit,
        "companion_takeover": takeover,
        "permit_consumption": consumption,
        "protocol_records": protocol,
        "consumed_cleanup_barrier": barrier,
        "source_cgroup_closure": source_closure,
        "runtime_closure": runtime_closure,
    }
    document = {
        "schema": "acfqp.k7_h1_bounded_supervisor_birth_slice_result.v1",
        "schema_version": b2c_v1.SCHEMA_VERSION,
        "proposed_contract_version": b2c_v1.PROPOSED_CONTRACT_VERSION,
        "profile_key": b2c_v1.PROFILE_KEY,
        "readiness": b2c_v1.READINESS,
        "supervisor_birth_companion_takeover_id": takeover_id,
        "actual_process_birth_permit_consumption_id": consumption_id,
        "protocol_record_ids": protocol_ids,
        "guardian_runtime_consumed_cleanup_barrier_id": barrier[
            "guardian_runtime_consumed_cleanup_barrier_id"
        ],
        "h1_route_wide_runtime_lease_closure_id": runtime_closure[
            "h1_route_wide_runtime_lease_closure_id"
        ],
        "source_e5a_cleanup_closure_id": source_closure_id,
        "guardian_session_genesis_id": genesis_id,
        "runtime_successor_id": successor_id,
        "child_pid": child_pid,
        "bounded_actual_peak_bytes": 4096,
        "actual_process_birth_present": True,
        "creator_reap_exactly_once": True,
        "memory_peak_primary_read_count": 1,
        "memory_peak_witness_read_count": 0,
        "birth_journal_closed": True,
        "all_b2c_owned_resources_closed": True,
        "all_upstream_cgroups_and_descriptors_closed": True,
        "consumed_cleanup_outcome": "BIRTH_REAP_PEAK_COMPLETE",
        "actual_peak_issued": True,
        "artifact_documents": artifacts,
        **b2c_v1._locked_claims(),
    }
    return _reissue_result(document)


def test_public_api_exposes_only_closed_runner_and_portable_verifiers() -> None:
    public_callables = {name for name in b2c_v1.__all__ if callable(getattr(b2c_v1, name))}
    assert public_callables == {
        "ConstructionK7H1ActualObservedSupervisorBirthV1Error",
        "H1ActualObservedSupervisorBirthResultV1",
        "H1SupervisorBirthSourcePrebindingV1",
        "run_h1_actual_observed_supervisor_birth_v1",
        "verify_h1_actual_observed_supervisor_birth_result_bytes_v1",
        "verify_h1_actual_observed_supervisor_birth_result_v1",
    }
    for name in (
        "prebind_h1_actual_observed_supervisor_birth_v1",
        "verify_h1_supervisor_birth_source_prebinding_v1",
        "close_h1_supervisor_birth_source_prebinding_v1",
        "complete_h1_actual_observed_supervisor_birth_v1",
    ):
        assert name not in b2c_v1.__all__


def test_caller_minted_and_live_authority_copy_pickle_fail_closed() -> None:
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="caller-minted",
    ):
        b2c_v1.H1ActualObservedSupervisorBirthResultV1(b"{}")
    prebinding_arguments = {
        item.name: None for item in fields(b2c_v1.H1SupervisorBirthSourcePrebindingV1)
    }
    prebinding_arguments["_issuer"] = object()
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="caller-minted",
    ):
        b2c_v1.H1SupervisorBirthSourcePrebindingV1(**prebinding_arguments)

    for authority_type in (
        b2c_v1.H1SupervisorBirthSourcePrebindingV1,
        b2c_v1._H1SupervisorBirthTakeoverV1,
        b2c_v1._H1SupervisorNativeLaunchPrefixV1,
    ):
        fake = object.__new__(authority_type)
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(
                b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error
            ):
                operation(fake)


def test_bytes_only_verifier_accepts_complete_embedded_dependency_graph() -> None:
    raw = _portable_result_bytes()
    document = b2c_v1.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(raw)
    assert document["actual_process_birth_present"] is True
    assert document["bounded_actual_peak_bytes"] == 4096
    assert set(document["artifact_documents"]["protocol_records"]) == set(
        b2c_v1._RESULT_PROTOCOL_RECORD_ORDER
    )


def test_bytes_only_verifier_rejects_embedded_content_tamper() -> None:
    document = ids_v1.loads_canonical_json(_portable_result_bytes())
    document["artifact_documents"]["protocol_records"]["peak_observation"][
        "memory_peak_bytes"
    ] += 1
    raw = _reissue_result(document)
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="embedded peak_observation content ID changed",
    ):
        b2c_v1.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(raw)


def test_bytes_only_verifier_rejects_deleted_embedded_artifact() -> None:
    document = ids_v1.loads_canonical_json(_portable_result_bytes())
    del document["artifact_documents"]["birth_intent"]
    raw = _reissue_result(document)
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="artifact inventory changed",
    ):
        b2c_v1.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(raw)


def test_bytes_only_verifier_rejects_valid_record_swap() -> None:
    document = ids_v1.loads_canonical_json(_portable_result_bytes())
    protocol = document["artifact_documents"]["protocol_records"]
    protocol["live_cgroup_snapshot_1"], protocol["live_cgroup_snapshot_2"] = (
        protocol["live_cgroup_snapshot_2"],
        protocol["live_cgroup_snapshot_1"],
    )
    raw = _reissue_result(document)
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="artifact dependency graph changed",
    ):
        b2c_v1.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(raw)


def test_bytes_only_verifier_rejects_rehashed_occurrence_identity_mismatch() -> None:
    document = ids_v1.loads_canonical_json(_portable_result_bytes())
    runtime_closure = document["artifact_documents"]["runtime_closure"]
    runtime_closure["logical_occurrence_id"] = "different-occurrence"
    _reissue_content_document(
        runtime_closure,
        domain=(
            domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN
        ),
        id_field="h1_route_wide_runtime_lease_closure_id",
    )
    document["h1_route_wide_runtime_lease_closure_id"] = runtime_closure[
        "h1_route_wide_runtime_lease_closure_id"
    ]
    raw = _reissue_result(document)
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="artifact dependency graph changed",
    ):
        b2c_v1.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(raw)


def test_bytes_only_verifier_rejects_top_level_peak_value_mismatch() -> None:
    document = ids_v1.loads_canonical_json(_portable_result_bytes())
    document["bounded_actual_peak_bytes"] += 1
    raw = _reissue_result(document)
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="artifact dependency graph changed",
    ):
        b2c_v1.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(raw)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("child_pid", 7332),
        ("h1_route_wide_runtime_lease_closure_id", "wrong-runtime-closure"),
        ("source_e5a_cleanup_closure_id", "wrong-source-closure"),
        ("guardian_session_genesis_id", "wrong-genesis"),
        ("runtime_successor_id", "wrong-successor"),
    ),
)
def test_bytes_only_verifier_rejects_top_level_identity_join_mismatch(
    field: str,
    replacement: object,
) -> None:
    document = ids_v1.loads_canonical_json(_portable_result_bytes())
    document[field] = replacement
    raw = _reissue_result(document)
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="artifact dependency graph changed",
    ):
        b2c_v1.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(raw)


def test_bytes_only_verifier_rejects_top_level_protocol_id_join_mismatch() -> None:
    document = ids_v1.loads_canonical_json(_portable_result_bytes())
    document["protocol_record_ids"]["creator_reap"] = "wrong-reap"
    raw = _reissue_result(document)
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="artifact dependency graph changed",
    ):
        b2c_v1.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(raw)


@pytest.mark.parametrize(
    "phase",
    (
        "AFTER_OPEN",
        "AFTER_PARTIAL_WRITE",
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_DIRECTORY_FSYNC",
    ),
)
def test_birth_journal_append_finishes_forward_after_one_shot_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    journal = b2c_v1._BirthJournalV1(tmp_path)
    monkeypatch.setattr(b2c_v1, "_TEST_ONLY_JOURNAL_FAULT_EVENT", "edge")
    monkeypatch.setattr(b2c_v1, "_TEST_ONLY_JOURNAL_FAULT_PHASE", phase)
    record = journal.append(
        domain=(
            domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN
        ),
        id_field="supervisor_birth_companion_takeover_id",
        event="edge",
        payload={"edge": phase},
    )
    journal.verify()
    assert len(journal._records) == 1
    assert os.listdir(tmp_path) == [record.filename]
    journal.close()
    assert journal._state == "CLOSED"


def test_birth_journal_close_retries_without_double_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = b2c_v1._BirthJournalV1(tmp_path)
    record = journal.append(
        domain=(
            domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN
        ),
        id_field="supervisor_birth_companion_takeover_id",
        event="edge",
        payload={"edge": "close-retry"},
    )
    target = record.descriptor
    original_close = os.close
    failed = False

    def fail_once(descriptor: int) -> None:
        nonlocal failed
        if descriptor == target and not failed:
            failed = True
            raise OSError(errno.EIO, "injected retained descriptor")
        original_close(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(b2c_v1.os, "close", fail_once)
        with pytest.raises(OSError, match="injected retained descriptor"):
            journal.close()
    assert journal._state == "CLOSE_PENDING"
    assert record.descriptor == target
    os.fstat(target)

    journal.close()
    assert journal._state == "CLOSED"
    assert record.descriptor == -1
    journal.close()


def test_unconsumed_takeover_cancellation_closes_without_birth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SimpleNamespace(_lock=threading.RLock())
    runtime = SimpleNamespace(_source_lease=source, _lock=threading.RLock())
    session = SimpleNamespace(_runtime=runtime, _state="COMPANION_ESCROW_UNCONSUMED")
    prebinding = SimpleNamespace(
        _code_rx_address=0,
        _source_fds={},
        _code_witness_fd=-1,
        _code_fd=-1,
        _manifest_witness_fd=-1,
        _manifest_fd=-1,
        _code_rx_function=None,
        _state="TAKEN_OVER_UNCONSUMED",
    )
    journal = b2c_v1._BirthJournalV1(tmp_path)
    takeover = b2c_v1._H1SupervisorBirthTakeoverV1(
        session=session,
        prebinding=prebinding,
        permit=object(),
        permit_record=object(),
        journal=journal,
        takeover_record=SimpleNamespace(record_id="takeover-id"),
        owner_pid=os.getpid(),
        owner_thread=threading.current_thread(),
        owner_thread_id=threading.get_ident(),
        state="TAKEN_OVER_UNCONSUMED",
        _issuer=b2c_v1._TAKEOVER_ISSUER,
    )
    b2c_v1._CONSUMED_PREBINDINGS[id(runtime)] = prebinding
    b2c_v1._LIVE_TAKEOVERS[id(session)] = takeover
    closure = SimpleNamespace(closure_id="closure-id")

    def close_companion(candidate: object) -> object:
        assert candidate is session
        session._state = "CLOSED"
        return closure

    monkeypatch.setattr(
        b2c_v1.b2b_v1,
        "close_h1_guardian_runtime_companion_unconsumed_v1",
        close_companion,
    )
    with pytest.raises(
        b2c_v1.ConstructionK7H1ActualObservedSupervisorBirthV1Error,
        match="closed an unconsumed",
    ) as captured:
        b2c_v1._close_unconsumed_takeover_v1(takeover)
    cleanup = captured.value.cleanup_document
    assert cleanup is not None
    assert cleanup["permit_consumed"] is False
    assert cleanup["actual_process_birth_present"] is False
    assert cleanup["all_process_and_cgroup_resources_closed"] is True
    assert captured.value.cleanup_handle is None
    assert takeover.state == "CLOSED_UNCONSUMED_CANCELLED"
    assert journal._state == "CLOSED"
    assert id(runtime) not in b2c_v1._CONSUMED_PREBINDINGS
    assert id(session) not in b2c_v1._LIVE_TAKEOVERS
    assert id(session) not in b2c_v1._QUARANTINED_TAKEOVERS


@requires_delegated_parent
def test_real_bounded_birth_closes_and_portably_replays(
    delegated_parent_fd: int,
    private_journal_pair: tuple[Path, Path],
) -> None:
    del delegated_parent_fd
    document = _run_real_subprocess_case("NONE", private_journal_pair)
    assert document["actual_process_birth_present"] is True
    assert document["creator_reap_exactly_once"] is True
    assert document["memory_peak_primary_read_count"] == 1
    assert document["memory_peak_witness_read_count"] == 0
    assert document["protocol_record_count"] == 12
    assert document["live_prebindings"] == 0
    assert document["consumed_prebindings"] == 0
    assert document["live_takeovers"] == 0
    assert document["quarantined_takeovers"] == 0


@requires_delegated_parent
@pytest.mark.parametrize(
    "stage",
    ("AFTER_READ_RETURNED", "AFTER_PEAK_RECORD_DURABLE"),
)
def test_peak_finish_forward_never_rereads_primary_peak(
    delegated_parent_fd: int,
    private_journal_pair: tuple[Path, Path],
    stage: str,
) -> None:
    del delegated_parent_fd
    document = _run_real_subprocess_case(stage, private_journal_pair)
    assert document["primary_reads_after_retry"] == document[
        "primary_reads_before_retry"
    ]
    assert document["memory_peak_primary_read_count"] == 1
    assert document["memory_peak_witness_read_count"] == 0
