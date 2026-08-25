from __future__ import annotations

from collections import Counter
from dataclasses import replace
import stat

import pytest

from acfqp import construction_k7_campaign_measurement_ledger_v180r12r3 as ledger
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r3 as protocol
from acfqp import construction_k7_campaign_measurement_supervisor_v180r12r3 as supervisor
from acfqp import construction_k7_campaign_measurement_worker_v180r12r3 as worker
from acfqp import construction_k7_domain_registry_extension_v180r12r3 as identity_domains
from acfqp.phase3e_ids import canonical_json_bytes


def _parent_fact() -> dict:
    return {
        "schema": "acfqp.v180r12r3_cgroup_parent_fact.v1",
        "mount_point": "/sys/fs/cgroup",
        "mount_fstype": "cgroup2",
        "mount_device": 25,
        "mount_inode": 1,
        "mount_options": ["nodev", "noexec", "nosuid", "nsdelegate", "rw"],
        "parent_path": "/sys/fs/cgroup/delegated",
        "parent_device": 25,
        "parent_inode": 100,
        "owner_uid": 1000,
        "owner_gid": 1000,
        "mode": 0o755,
        "controllers": ["memory", "pids"],
        "subtree_control": ["memory", "pids"],
        "cgroup_type": "domain",
        "cgroup_namespace_inode": 999,
        "cgroup_events_present": True,
        "memory_events_present": True,
        "pids_events_present": True,
        "cgroup_kill_present": True,
        "cgroup_procs_present": True,
        "memory_peak_present": True,
        "pids_peak_present": True,
        "self_membership": "0::/",
    }


def _node(
    role: str,
    path: str,
    parent_path: str | None,
    membership_path: str,
    parent_membership_path: str | None,
    fd: int,
    inode: int,
) -> supervisor.CgroupNodeIdentityV180R12R3:
    return supervisor.CgroupNodeIdentityV180R12R3(
        role,
        path,
        parent_path,
        membership_path,
        parent_membership_path,
        fd,
        25,
        inode,
        stat.S_IFDIR | 0o755,
        2,
        True,
        True,
    )


def _topology() -> supervisor.MeasurementCgroupTopologyReceiptV180R12R3:
    nodes = {
        "DELEGATED_PARENT": _node(
            "DELEGATED_PARENT",
            "/sys/fs/cgroup/delegated",
            "/sys/fs/cgroup",
            "/delegated",
            "/",
            3,
            100,
        ),
        "MEASUREMENT_ROOT": _node(
            "MEASUREMENT_ROOT",
            "/sys/fs/cgroup/delegated/attempt",
            "/sys/fs/cgroup/delegated",
            "/delegated/attempt",
            "/delegated",
            4,
            101,
        ),
        "SUPERVISOR": _node(
            "SUPERVISOR",
            "/sys/fs/cgroup/delegated/attempt/supervisor",
            "/sys/fs/cgroup/delegated/attempt",
            "/delegated/attempt/supervisor",
            "/delegated/attempt",
            5,
            102,
        ),
        "WORKER": _node(
            "WORKER",
            "/sys/fs/cgroup/delegated/attempt/worker",
            "/sys/fs/cgroup/delegated/attempt",
            "/delegated/attempt/worker",
            "/delegated/attempt",
            6,
            103,
        ),
    }
    control_files = tuple(
        supervisor.CgroupControlFileOFDV180R12R3(
            role,
            name,
            100 + index,
            25,
            1_000 + index,
            stat.S_IFREG | 0o444,
            1,
            True,
            True,
            True,
        )
        for index, (role, name) in enumerate(
            supervisor._REQUIRED_CGROUP_CONTROL_FILES
        )
    )
    return supervisor.MeasurementCgroupTopologyReceiptV180R12R3(
        _parent_fact(),
        nodes["DELEGATED_PARENT"],
        nodes["MEASUREMENT_ROOT"],
        nodes["SUPERVISOR"],
        nodes["WORKER"],
        "cgroup2",
        ("memory", "pids"),
        ("memory", "pids"),
        supervisor.MEMORY_MAX_BYTES,
        2,
        1,
        1,
        False,
        0,
        (0, 0),
        control_files,
    )


def _birth(
    topology: supervisor.MeasurementCgroupTopologyReceiptV180R12R3,
    attempt_id: str,
    role: supervisor.ProcessRoleV180R12R3,
    pid: int,
    pidfd: int,
) -> supervisor.PidfdBirthReceiptV180R12R3:
    target = (
        topology.supervisor_leaf
        if role is supervisor.ProcessRoleV180R12R3.SUPERVISOR
        else topology.worker_leaf
    )
    plan = next(
        row
        for row in supervisor.build_campaign_operation_schedule_v180r12r3(attempt_id)
        if row.slot == "PROCESS" and row.family == role.value
    )
    return supervisor.PidfdBirthReceiptV180R12R3(
        topology,
        attempt_id,
        plan.operation_id,
        role,
        pid,
        pidfd,
        9,
        2_000 + pid,
        ("CLONE_INTO_CGROUP", "CLONE_PIDFD"),
        target.directory_fd,
        target.device,
        target.inode,
        target.path,
        50_000 + pid,
        pid,
        (pid,),
        f"0::{target.membership_path}",
        True,
        True,
    )


def _reap(
    birth: supervisor.PidfdBirthReceiptV180R12R3,
) -> supervisor.PidfdReapReceiptV180R12R3:
    return supervisor.PidfdReapReceiptV180R12R3(
        birth,
        birth.operation_id,
        birth.pidfd_device,
        birth.pidfd_inode,
        birth.proc_starttime_ticks,
        "P_PIDFD",
        birth.pidfd,
        "CLD_EXITED",
        0,
        True,
        False,
        0,
    )


def _readbacks(topology, memory_peak=4096):
    values = {
        ("MEASUREMENT_ROOT", "cgroup.events"): "populated 0\nfrozen 0\n",
        ("MEASUREMENT_ROOT", "cgroup.procs"): "",
        ("MEASUREMENT_ROOT", "memory.events"): (
            "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n"
        ),
        ("MEASUREMENT_ROOT", "memory.max"): f"{supervisor.MEMORY_MAX_BYTES}\n",
        ("MEASUREMENT_ROOT", "memory.peak"): f"{memory_peak}\n",
        ("MEASUREMENT_ROOT", "pids.events"): "max 0\n",
        ("MEASUREMENT_ROOT", "pids.max"): "2\n",
        ("MEASUREMENT_ROOT", "pids.peak"): "2\n",
        ("SUPERVISOR", "cgroup.events"): "populated 0\nfrozen 0\n",
        ("SUPERVISOR", "cgroup.procs"): "",
        ("SUPERVISOR", "pids.max"): "1\n",
        ("WORKER", "cgroup.events"): "populated 0\nfrozen 0\n",
        ("WORKER", "cgroup.procs"): "",
        ("WORKER", "pids.max"): "1\n",
    }
    return tuple(
        supervisor.CgroupControlFileReadbackV180R12R3(
            row, values[(row.node_role, row.name)], True, True, True
        )
        for row in topology.control_files
    )


def test_contract_rows_manifests_and_expanded_schedule_are_cross_exact() -> None:
    runtime_rows = (
        worker.EVIDENCE_DOCUMENT_CONTRACT_ROWS
        + supervisor.EVIDENCE_DOCUMENT_CONTRACT_ROWS
    )
    protocol_rows = tuple(row[:4] for row in protocol.EVIDENCE_INVENTORY_ROWS)
    assert len(runtime_rows) == len(protocol_rows) == 18
    assert set(runtime_rows) == set(protocol_rows)
    assert supervisor.HASH_OPERATION_FAMILIES == (
        protocol.SEMANTIC_HASH_OPERATION_FAMILIES
    )
    assert supervisor.INTEGRITY_OPERATION_FAMILIES == (
        protocol.INTEGRITY_CHECK_OPERATION_FAMILIES
    )
    assert worker.PROTOCOL_CHECK_FAMILIES == protocol.PROTOCOL_CHECK_FAMILIES
    assert worker.PROTOCOL_CHECK_OPERATION_LABELS == (
        protocol.PROTOCOL_CHECK_OPERATION_LABELS
    )
    attempt_id = "a" * 64
    local_operations = supervisor.build_campaign_operation_schedule_v180r12r3(
        attempt_id
    )
    kernel_operations = ledger.build_campaign_operation_schedule_v180r12r3(attempt_id)
    assert tuple(
        (row.slot, row.family, row.ordinal, row.phase, row.actor_role, row.operation_id)
        for row in local_operations
    ) == tuple(
        (row.slot, row.family, row.ordinal, row.phase, row.actor_role, row.operation_id)
        for row in kernel_operations
    )
    local_events = supervisor.build_campaign_success_event_plan_v180r12r3(attempt_id)
    kernel_events = ledger.build_campaign_success_event_schedule_v180r12r3(attempt_id)
    assert tuple(
        (row.event_kind, row.actor_role, row.phase, row.operation_id)
        for row in local_events
    ) == tuple(
        (row.event_kind, row.actor_role, row.phase, row.operation_id)
        for row in kernel_events
    )
    assert len(local_events) == 625
    direct = sum(row.event_kind in supervisor.EVIDENCE_REQUIRED_EVENT_KINDS for row in local_events)
    assert (direct, len(local_events) - direct) == (317, 308)
    for index, row in enumerate(local_events[:-1]):
        if row.event_kind.endswith("_INTENT") and not row.event_kind.startswith(
            "PROCESS_BIRTH"
        ):
            assert local_events[index + 1].operation_id == row.operation_id
            assert local_events[index + 1].event_kind == row.event_kind.replace(
                "_INTENT", "_OUTCOME"
            )


def test_state_machine_rejects_same_count_permutation_and_unregistered_evidence() -> None:
    protocol_id, authorization_id = "1" * 64, "2" * 64
    attempt_authority = {
        "authorization_evidence_id": "3" * 64,
        "campaign_measurement_execution_slot_id": "4" * 64,
        "logical_occurrence_id": "5" * 64,
        "execution_nonce": "6" * 64,
    }
    attempt_id = identity_domains.derive_campaign_measurement_attempt_id_v180r12r3(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        **attempt_authority,
    )
    runtime = supervisor.CampaignMeasurementSupervisorV180R12R3(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
    )
    topology = _topology()
    topology_id = runtime.register_evidence_document(topology)
    manifest = ledger.campaign_operation_manifest_v180r12r3(attempt_id)
    manifest_id = runtime.register_evidence_document(manifest)
    attempt_plan = runtime.success_event_plan[0]
    attempt = ledger.issue_campaign_attempt_record_v180r12r3(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        **attempt_authority,
        prelaunch_materialization_terminal_id="7" * 64,
        prelaunch_launch_manifest_sha256="8" * 64,
        prelaunch_launch_rule_id="9" * 64,
        measurement_launch_attempt_id="a" * 64,
        attempt_id=attempt_id,
        operation_id=attempt_plan.operation_id,
        operation_manifest_id=manifest_id,
    )
    runtime.append_event(
        phase=attempt_plan.phase,
        actor_role=attempt_plan.actor_role,
        operation_id=attempt_plan.operation_id,
        event_kind=attempt_plan.event_kind,
        monotonic_ns=1,
        evidence_document=attempt,
    )
    expected_birth_intent = runtime.success_event_plan[1]
    wrong_operation = next(
        row.operation_id
        for row in runtime.operation_schedule
        if row.slot == "PROCESS" and row.family == "WORKER"
    )
    with pytest.raises(
        supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error,
        match="next exact",
    ):
        runtime.append_event(
            phase=expected_birth_intent.phase,
            actor_role=expected_birth_intent.actor_role,
            operation_id=wrong_operation,
            event_kind=expected_birth_intent.event_kind,
            monotonic_ns=2,
        )
    runtime.append_event(
        phase=expected_birth_intent.phase,
        actor_role=expected_birth_intent.actor_role,
        operation_id=expected_birth_intent.operation_id,
        event_kind=expected_birth_intent.event_kind,
        monotonic_ns=2,
    )
    birth_plan = runtime.success_event_plan[2]
    with pytest.raises(
        supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error,
        match="registered first",
    ):
        runtime.append_event(
            phase=birth_plan.phase,
            actor_role=birth_plan.actor_role,
            operation_id=birth_plan.operation_id,
            event_kind=birth_plan.event_kind,
            monotonic_ns=3,
            evidence_id="f" * 64,
            measured_value=1,
        )
    birth = _birth(
        topology, attempt_id, supervisor.ProcessRoleV180R12R3.SUPERVISOR, 501, 51
    )
    runtime.append_event(
        phase=birth_plan.phase,
        actor_role=birth_plan.actor_role,
        operation_id=birth_plan.operation_id,
        event_kind=birth_plan.event_kind,
        monotonic_ns=3,
        evidence_document=birth,
        measured_value=1,
    )
    assert runtime.event_count == 3


def test_cgroup_sibling_topology_pidfd_antireuse_and_raw_observation() -> None:
    attempt_id = "4" * 64
    topology = _topology()
    supervisor_birth = _birth(
        topology, attempt_id, supervisor.ProcessRoleV180R12R3.SUPERVISOR, 601, 61
    )
    worker_birth = _birth(
        topology, attempt_id, supervisor.ProcessRoleV180R12R3.WORKER, 602, 62
    )
    supervisor_reap, worker_reap = _reap(supervisor_birth), _reap(worker_birth)
    cgroup_operation = next(
        row.operation_id
        for row in supervisor.build_campaign_operation_schedule_v180r12r3(attempt_id)
        if row.slot == "CGROUP"
    )
    observation = supervisor.CgroupV2ObservationReceiptV180R12R3(
        topology,
        supervisor_reap,
        worker_reap,
        cgroup_operation,
        4096,
        2,
        (
            ("high", 0),
            ("low", 0),
            ("max", 0),
            ("oom", 0),
            ("oom_group_kill", 0),
            ("oom_kill", 0),
        ),
        (("max", 0),),
        (("MEASUREMENT_ROOT", 0), ("SUPERVISOR", 0), ("WORKER", 0)),
        (("MEASUREMENT_ROOT", 0), ("SUPERVISOR", 0), ("WORKER", 0)),
        _readbacks(topology),
        True,
    )
    document = observation.to_document()
    keysets = {
        evidence_type: fields
        for evidence_type, _schema, _identity, fields
        in supervisor.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS
    }
    assert set(topology.to_document()) == keysets["CGROUP_TOPOLOGY_RECEIPT"]
    assert set(supervisor_birth.to_document()) == keysets["PIDFD_BIRTH_RECEIPT"]
    assert set(supervisor_reap.to_document()) == keysets["PIDFD_REAP_RECEIPT"]
    assert set(document) == keysets["CGROUP_OBSERVATION_RECEIPT"]
    assert len(supervisor.RUNTIME_EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS) == 10
    assert document["pids_peak"] == 2
    assert document["memory_peak_bytes"] == 4096
    assert document["memory_events"][4] == {"name": "oom_group_kill", "value": 0}
    with pytest.raises(supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error):
        replace(observation, pids_peak=1)
    with pytest.raises(supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error):
        replace(worker_birth, cgroup_membership_line=f"0::{worker_birth.target_cgroup_path}")
    with pytest.raises(supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error):
        replace(worker_reap, proc_starttime_ticks=worker_reap.proc_starttime_ticks + 1)


def test_cgroup_path_alias_or_cross_device_fails_closed() -> None:
    topology = _topology()
    assert topology.cgroup_parent_fact["self_membership"] == "0::/"
    assert topology.cgroup_parent_fact["self_membership"] != (
        f"0::{topology.delegated_parent.membership_path}"
    )
    with pytest.raises(supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error):
        replace(topology.worker_leaf, path=topology.worker_leaf.path + "/../worker")
    with pytest.raises(supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error):
        replace(topology, worker_leaf=replace(topology.worker_leaf, device=26))
    foreign_path = dict(topology.cgroup_parent_fact)
    foreign_path["parent_path"] = "/sys/fs/cgroup/foreign"
    with pytest.raises(supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error):
        replace(topology, cgroup_parent_fact=foreign_path)
    foreign_device = dict(topology.cgroup_parent_fact)
    foreign_device["parent_device"] = 26
    with pytest.raises(supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error):
        replace(topology, cgroup_parent_fact=foreign_device)


def test_exact_eight_edge_io_graph_and_chunk_receipts_reject_role_swap() -> None:
    protocol_id, authorization_id, attempt_id = "1" * 64, "2" * 64, "3" * 64
    manifest = ledger.campaign_operation_manifest_v180r12r3(attempt_id)
    manifest_id = manifest["campaign_operation_manifest_id"]
    snapshot_ids = {"TERMINAL": "4" * 64, "VERIFICATION": "5" * 64}
    stage_ids = {"TERMINAL": "6" * 64, "VERIFICATION": "7" * 64}
    birth_ids = {"SUPERVISOR": "8" * 64, "WORKER": "9" * 64}
    replay_id, subject_id, subject_bytes = "a" * 64, "b" * 64, 4096
    documents = {
        manifest_id: manifest,
        **{
            snapshot_ids[role]: {
                "schema": "acfqp.campaign_stable_input_snapshot.v180r12r3",
                "role": role,
                "observed_byte_count": byte_count,
                "stable_input_snapshot_id": snapshot_ids[role],
            }
            for role, byte_count in (
                ("TERMINAL", worker.TERMINAL_BYTE_COUNT),
                ("VERIFICATION", worker.VERIFICATION_BYTE_COUNT),
            )
        },
        **{
            stage_ids[role]: {
                "schema": "acfqp.campaign_memfd_stage_receipt.v180r12r3",
                "role": role,
                "input_snapshot_id": snapshot_ids[role],
                "byte_count": byte_count,
                "memfd_stage_receipt_id": stage_ids[role],
            }
            for role, byte_count in (
                ("TERMINAL", worker.TERMINAL_BYTE_COUNT),
                ("VERIFICATION", worker.VERIFICATION_BYTE_COUNT),
            )
        },
        **{
            birth_ids[role]: {
                "schema": "acfqp.campaign_pidfd_birth_receipt.v180r12r3",
                "process_role": role,
                "pidfd_birth_receipt_id": birth_ids[role],
            }
            for role in ("SUPERVISOR", "WORKER")
        },
        replay_id: {
            "schema": "acfqp.campaign_replay_subject_receipt.v180r12r3",
            "replay_subject_receipt_id": replay_id,
            "subject_result_id": subject_id,
            "subject_byte_count": subject_bytes,
        },
        subject_id: {
            "schema": "acfqp.campaign_measurement_subject_result.v180r12r3",
            "subject_result_id": subject_id,
            "subject_byte_count": subject_bytes,
        },
    }
    transfers = tuple(
        row
        for row in supervisor.build_campaign_operation_schedule_v180r12r3(
            attempt_id
        )
        if (row.slot, row.family)
        in {
            ("INPUT_READ", "FROZEN_SOURCE"),
            ("STAGE_WRITE", "SEALED_MEMFD"),
            ("INPUT_READ", "SEALED_STAGE"),
            ("SUBJECT_WRITE", "SUBJECT_RESULT"),
            ("INPUT_READ", "SUBJECT_READBACK"),
        }
    )
    assert len(transfers) == 8
    receipts: dict[str, dict] = {}
    for plan in transfers:
        role = "TERMINAL" if plan.ordinal == 0 else "VERIFICATION"
        if (plan.slot, plan.family) == ("INPUT_READ", "FROZEN_SOURCE"):
            endpoints = manifest_id, snapshot_ids[role]
            measured = (
                worker.TERMINAL_BYTE_COUNT
                if role == "TERMINAL"
                else worker.VERIFICATION_BYTE_COUNT
            )
        elif (plan.slot, plan.family) == ("STAGE_WRITE", "SEALED_MEMFD"):
            endpoints = snapshot_ids[role], stage_ids[role]
            measured = (
                worker.TERMINAL_BYTE_COUNT
                if role == "TERMINAL"
                else worker.VERIFICATION_BYTE_COUNT
            )
        elif (plan.slot, plan.family) == ("INPUT_READ", "SEALED_STAGE"):
            endpoints = stage_ids[role], birth_ids["WORKER"]
            measured = (
                worker.TERMINAL_BYTE_COUNT
                if role == "TERMINAL"
                else worker.VERIFICATION_BYTE_COUNT
            )
        elif plan.slot == "SUBJECT_WRITE":
            endpoints, measured = (subject_id, birth_ids["WORKER"]), subject_bytes
        else:
            endpoints, measured = (subject_id, birth_ids["SUPERVISOR"]), subject_bytes
        event_kind = f"{plan.slot}_OUTCOME"
        chunks = [measured // 2, measured - measured // 2]
        receipt = ledger.issue_campaign_io_transfer_receipt_v180r12r3(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            attempt_id=attempt_id,
            operation_id=plan.operation_id,
            event_kind=event_kind,
            measured_value=measured,
            returned_chunk_byte_counts=chunks,
            source_evidence_id=endpoints[0],
            target_evidence_id=endpoints[1],
        )
        receipts[plan.operation_id] = receipt
        assert supervisor.validate_campaign_io_transfer_edge_v180r12r3(
            plan=plan,
            event_kind=event_kind,
            measured_value=measured,
            receipt_document=receipt,
            evidence_documents_by_id=documents,
        ) == endpoints

    terminal_stage = next(
        row
        for row in transfers
        if (row.slot, row.family, row.ordinal) == ("STAGE_WRITE", "SEALED_MEMFD", 0)
    )
    valid = receipts[terminal_stage.operation_id]
    role_swapped = {
        **valid,
        "source_evidence_id": snapshot_ids["VERIFICATION"],
        "transfer_identity": {
            **valid["transfer_identity"],
            "source_evidence_id": snapshot_ids["VERIFICATION"],
        },
    }
    with pytest.raises(
        supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error,
        match="roles changed",
    ):
        supervisor.validate_campaign_io_transfer_edge_v180r12r3(
            plan=terminal_stage,
            event_kind="STAGE_WRITE_OUTCOME",
            measured_value=worker.TERMINAL_BYTE_COUNT,
            receipt_document=role_swapped,
            evidence_documents_by_id=documents,
        )
    broken_chunks = {**valid, "returned_chunk_byte_counts": [1]}
    with pytest.raises(
        supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error,
        match="returned syscall chunks",
    ):
        supervisor.validate_campaign_io_transfer_edge_v180r12r3(
            plan=terminal_stage,
            event_kind="STAGE_WRITE_OUTCOME",
            measured_value=worker.TERMINAL_BYTE_COUNT,
            receipt_document=broken_chunks,
            evidence_documents_by_id=documents,
        )


def test_payload_auxiliary_and_failure_identity_are_exact() -> None:
    with pytest.raises(supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error):
        supervisor.campaign_event_payload_v180r12r3(
            event_kind="INPUT_READ_INTENT",
            evidence_id=None,
            measured_value=None,
            auxiliary_values=(("forbidden", 1),),
        )
    failure = supervisor.CampaignFailureStateV180R12R3(
        "1" * 64,
        "2" * 64,
        "3" * 64,
        supervisor.FailureCodeV180R12R3.CAP_VIOLATION,
        supervisor.CampaignPhaseV180R12R3.STAGE,
        None,
        None,
        0,
        "synthetic cap violation",
        False,
        False,
        tuple(
            supervisor.FailureArtifactObservationV180R12R3(
                path, kind, "ABSENT", None, None, None, None, None, None, None
            )
            for path, kind in supervisor.FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
        ),
        None,
    )
    assert failure.to_document()["same_identity_rerun_forbidden"] is True
    assert failure.to_document()["partial_artifact_observation_boundary"] == (
        supervisor.FAILURE_ARTIFACT_OBSERVATION_BOUNDARY
    )
    assert len(failure.to_document()["partial_artifact_observations"]) == 15
    assert failure.to_document()["partial_artifact_observations"][0]["state"] == "ABSENT"
    assert failure.to_document()["cgroup_failure_observation"] is None
    assert set(failure.to_document()) == supervisor.FAILURE_STATE_FIELD_KEYS
    assert set(
        failure.to_document()["partial_artifact_observations"][0]
    ) == supervisor.FAILURE_ARTIFACT_OBSERVATION_KEYS
    cgroup_failure = supervisor.FailureCgroupObservationV180R12R3(
        None, None, None, None, None, None, None, None, None, None,
        "NOT_ATTEMPTED", "NOT_ATTEMPTED", "NOT_ATTEMPTED", (),
        tuple(
            supervisor.FailureCgroupNodeObservationV180R12R3(
                role,
                (
                    "/synthetic/MEASUREMENT_ROOT"
                    if role == "MEASUREMENT_ROOT"
                    else f"/synthetic/MEASUREMENT_ROOT/{role}"
                ),
                "ABSENT", None, None, None,
                None, None, None, None, None,
            )
            for role in ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
        ),
    )
    assert set(cgroup_failure.to_document()) == supervisor.FAILURE_CGROUP_OBSERVATION_KEYS
    assert failure.to_document()["successful_ledger_claimed"] is False
    with pytest.raises(
        supervisor.ConstructionK7CampaignMeasurementSupervisorV180R12R3Error,
        match="fixed path inventory",
    ):
        replace(
            failure,
            partial_artifact_observations=(
                failure.partial_artifact_observations[:-1]
            ),
        )


def test_measurement_failure_control_escape_inventory_stays_within_emergency_reserve() -> None:
    events_path = ".tmp/exact-freeze/v180r12r3_campaign_measurement/EVENTS"
    names = tuple(sorted(f"{ordinal:04d}" + "\x01" * 240 for ordinal in range(650)))
    assert sum(len(name.encode("utf-8")) for name in names) < (
        protocol.FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
    )

    observations = []
    for relative_path, kind in supervisor.FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS:
        if relative_path == events_path:
            observations.append(
                supervisor.FailureArtifactObservationV180R12R3(
                    relative_path,
                    kind,
                    "PRESENT",
                    stat.S_IFDIR | 0o500,
                    2,
                    None,
                    None,
                    names,
                    None,
                    None,
                )
            )
        else:
            observations.append(
                supervisor.FailureArtifactObservationV180R12R3(
                    relative_path,
                    kind,
                    "ABSENT",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                )
            )
    observations.extend(
        supervisor.FailureArtifactObservationV180R12R3(
            f"{events_path}/{name}",
            "FILE",
            "ABSENT",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        for name in names
    )
    failure = supervisor.CampaignFailureStateV180R12R3(
        "1" * 64,
        "2" * 64,
        "3" * 64,
        supervisor.FailureCodeV180R12R3.CAP_VIOLATION,
        supervisor.CampaignPhaseV180R12R3.STAGE,
        None,
        None,
        0,
        "bounded control-character directory observation",
        False,
        False,
        tuple(sorted(observations, key=lambda row: row.relative_path)),
        None,
    )
    raw = canonical_json_bytes(failure.to_document())
    assert b"\\u0001" in raw
    assert len(raw) < protocol.FAILURE_EMERGENCY_RESERVE_BYTES
    assert 6 * protocol.FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP + (
        protocol.FAILURE_ARTIFACT_METADATA_BYTE_CAP
    ) < protocol.FAILURE_EMERGENCY_RESERVE_BYTES
