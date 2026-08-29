from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import socket
import stat
import sys
import threading
import time
import types
from types import SimpleNamespace

from acfqp import construction_k7_campaign_measurement_ledger_v180r12r4 as ledger
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp import construction_k7_campaign_measurement_supervisor_v180r12r4 as runtime


ROOT = Path(__file__).resolve().parents[1]
_FIXED_INTERNAL_FDS = tuple(range(240, 253))


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run = _load(
    "_effectful_integration_run_v180r12r4",
    "scripts/run_v180r12r4_campaign_measurement.py",
)
supervise = _load(
    "_effectful_integration_supervise_v180r12r4",
    "scripts/supervise_v180r12r4_campaign_measurement.py",
)
work = _load(
    "_effectful_integration_work_v180r12r4",
    "scripts/work_v180r12r4_campaign_measurement.py",
)
ledger_fixture = _load(
    "_effectful_integration_ledger_fixture_v180r12r4",
    "tests/test_construction_k7_campaign_measurement_ledger_v180r12r4.py",
)


class _FixedFDGuard:
    def __init__(self) -> None:
        self.backups: dict[int, tuple[int, bool] | None] = {}

    def __enter__(self):
        for descriptor in _FIXED_INTERNAL_FDS:
            try:
                inheritable = os.get_inheritable(descriptor)
                backup = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 300)
            except OSError:
                self.backups[descriptor] = None
            else:
                self.backups[descriptor] = (backup, inheritable)
            try:
                os.close(descriptor)
            except OSError:
                pass
        return self

    def install(self, target: int, source: int) -> None:
        os.dup2(source, target, inheritable=False)

    def close(self, target: int) -> None:
        try:
            os.close(target)
        except OSError:
            pass

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        for descriptor in _FIXED_INTERNAL_FDS:
            self.close(descriptor)
        for descriptor, saved in self.backups.items():
            if saved is None:
                continue
            backup, inheritable = saved
            try:
                os.dup2(backup, descriptor, inheritable=inheritable)
            finally:
                os.close(backup)


def _authority() -> run.CampaignAttemptAuthorityV180R12R4:
    return run.CampaignAttemptAuthorityV180R12R4(
        protocol_id="1" * 64,
        authorization_id="2" * 64,
        authorization_evidence_id="3" * 64,
        campaign_measurement_execution_slot_id="4" * 64,
        logical_occurrence_id="5" * 64,
        execution_nonce="6" * 64,
        prelaunch_materialization_terminal_id="7" * 64,
        prelaunch_launch_manifest_sha256="8" * 64,
        prelaunch_launch_rule_id="9" * 64,
        measurement_launch_attempt_id="a" * 64,
    )


def _directory_node(
    role: str,
    path: Path,
    parent_path: Path | None,
    membership_path: str,
    parent_membership_path: str | None,
    descriptor: int,
) -> runtime.CgroupNodeIdentityV180R12R4:
    metadata = os.fstat(descriptor)
    return runtime.CgroupNodeIdentityV180R12R4(
        role,
        path.as_posix(),
        None if parent_path is None else parent_path.as_posix(),
        membership_path,
        parent_membership_path,
        descriptor,
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        bool(fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC),
        True,
    )


def _make_synthetic_cgroup_tree(
    root: Path,
    authority: run.CampaignAttemptAuthorityV180R12R4,
    fixed: _FixedFDGuard,
) -> tuple[run.CgroupTreeV180R12R4, dict[tuple[str, str], str]]:
    parent_path = root / "app.slice"
    source_service_path = (
        parent_path / protocol.PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME
    )
    measurement_path = parent_path / f"v180r12r4-{authority.attempt_id}"
    supervisor_path = measurement_path / "SUPERVISOR"
    worker_path = measurement_path / "WORKER"
    for path in (
        parent_path,
        source_service_path,
        measurement_path,
        supervisor_path,
        worker_path,
    ):
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o755)
    (parent_path / "cgroup.procs").write_text("", encoding="ascii")
    (parent_path / "cgroup.procs").chmod(0o600)
    (source_service_path / "cgroup.procs").write_text(
        f"{os.getpid()}\n", encoding="ascii"
    )
    (source_service_path / "cgroup.procs").chmod(0o400)

    raw_values = {
        ("MEASUREMENT_ROOT", "cgroup.events"): "frozen 0\npopulated 0\n",
        ("MEASUREMENT_ROOT", "cgroup.procs"): "",
        ("MEASUREMENT_ROOT", "cgroup.subtree_control"): "memory pids\n",
        ("MEASUREMENT_ROOT", "memory.events"): (
            "high 0\nlow 0\nmax 0\noom 0\noom_group_kill 0\noom_kill 0\n"
        ),
        ("MEASUREMENT_ROOT", "memory.max"): "17179869184\n",
        ("MEASUREMENT_ROOT", "memory.peak"): "4096\n",
        ("MEASUREMENT_ROOT", "pids.events"): "max 0\n",
        ("MEASUREMENT_ROOT", "pids.max"): "2\n",
        ("MEASUREMENT_ROOT", "pids.peak"): "2\n",
        ("SUPERVISOR", "cgroup.events"): "frozen 0\npopulated 0\n",
        ("SUPERVISOR", "cgroup.procs"): "",
        ("SUPERVISOR", "pids.max"): "1\n",
        ("WORKER", "cgroup.events"): "frozen 0\npopulated 0\n",
        ("WORKER", "cgroup.procs"): "",
        ("WORKER", "pids.max"): "1\n",
    }
    path_by_role = {
        "MEASUREMENT_ROOT": measurement_path,
        "SUPERVISOR": supervisor_path,
        "WORKER": worker_path,
    }
    for (role, name), raw in raw_values.items():
        target = path_by_role[role] / name
        target.write_text(raw, encoding="ascii")
        target.chmod(0o400)

    open_directory = lambda path: os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    parent_source = open_directory(parent_path)
    fixed.install(run.DELEGATED_CGROUP_PARENT_FD, parent_source)
    os.close(parent_source)
    parent_fd = run.DELEGATED_CGROUP_PARENT_FD
    mount_source = os.open(root, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    fixed.install(run.CGROUP2_MOUNT_FD, mount_source)
    os.close(mount_source)
    mount_fd = run.CGROUP2_MOUNT_FD
    source_service_source = open_directory(source_service_path)
    fixed.install(run.SOURCE_SYSTEMD_SERVICE_FD, source_service_source)
    os.close(source_service_source)
    source_service_fd = run.SOURCE_SYSTEMD_SERVICE_FD
    measurement_fd = open_directory(measurement_path)
    supervisor_fd = open_directory(supervisor_path)
    worker_source = open_directory(worker_path)
    fixed.install(run.SUPERVISOR_WORKER_CGROUP_FD, worker_source)
    os.close(worker_source)
    worker_fd = run.SUPERVISOR_WORKER_CGROUP_FD

    delegated_membership = "/app.slice"
    measurement_membership = delegated_membership + "/" + measurement_path.name
    delegated = _directory_node(
        "DELEGATED_PARENT",
        parent_path,
        root,
        delegated_membership,
        "/",
        parent_fd,
    )
    measurement = _directory_node(
        "MEASUREMENT_ROOT",
        measurement_path,
        parent_path,
        measurement_membership,
        delegated_membership,
        measurement_fd,
    )
    supervisor = _directory_node(
        "SUPERVISOR",
        supervisor_path,
        measurement_path,
        measurement_membership + "/SUPERVISOR",
        measurement_membership,
        supervisor_fd,
    )
    worker = _directory_node(
        "WORKER",
        worker_path,
        measurement_path,
        measurement_membership + "/WORKER",
        measurement_membership,
        worker_fd,
    )
    parent_metadata = os.fstat(parent_fd)
    mount_metadata = os.fstat(mount_fd)
    source_service_metadata = os.fstat(source_service_fd)
    parent_fact = {
        "schema": "acfqp.v180r12r4_cgroup_parent_fact.v1",
        "mount_point": root.as_posix(),
        "mount_fstype": "cgroup2",
        "mount_device": mount_metadata.st_dev,
        "mount_inode": mount_metadata.st_ino,
        "mount_options": ["nodev", "noexec", "nosuid", "nsdelegate", "rw"],
        "parent_path": parent_path.as_posix(),
        "parent_device": parent_metadata.st_dev,
        "parent_inode": parent_metadata.st_ino,
        "owner_uid": parent_metadata.st_uid,
        "owner_gid": parent_metadata.st_gid,
        "mode": stat.S_IMODE(parent_metadata.st_mode),
        "controllers": ["memory", "pids"],
        "subtree_control": ["memory", "pids"],
        "cgroup_type": "domain",
        "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
        "cgroup_events_present": True,
        "memory_events_present": True,
        "pids_events_present": True,
        "cgroup_kill_present": True,
        "cgroup_procs_present": True,
        "memory_peak_present": True,
        "pids_peak_present": True,
        "self_membership": run._proc_cgroup(os.getpid()),
    }
    controls = []
    retained = []
    for role, name in run.LinuxCgroupV2V180R12R4.retained_names:
        descriptor = os.open(
            path_by_role[role] / name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        metadata = os.fstat(descriptor)
        control = runtime.CgroupControlFileOFDV180R12R4(
            role,
            name,
            descriptor,
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_nlink,
            True,
            True,
            True,
        )
        controls.append(control)
        retained.append((role, name, descriptor, metadata.st_dev, metadata.st_ino))
    token = protocol.PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN
    unit_name = protocol.PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME

    def fd_fact(
        fd: int, role: str, access: str, path: str, metadata: os.stat_result
    ) -> dict[str, object]:
        return {
            "fd": fd,
            "role": role,
            "access": access,
            "path": path,
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode),
            "owner_uid": metadata.st_uid,
            "owner_gid": metadata.st_gid,
            "nlink": metadata.st_nlink,
        }

    service_metadata = source_service_metadata
    source_membership = f"0::/app.slice/{unit_name}"
    placement_t1 = {
        "schema": protocol.PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA,
        "target": "measurement",
        "token": token,
        "unit_name": unit_name,
        "slice": "app.slice",
        "source_membership": source_membership,
        "expected_source_membership": source_membership,
        "self_pid": os.getpid(),
        "self_pid_in_source_cgroup_procs": True,
        "cgroup_namespace_inode": parent_fact["cgroup_namespace_inode"],
        "delegated_parent_fd_fact": fd_fact(
            250, "DELEGATED_CGROUP_PARENT_DIRECTORY", "O_RDONLY",
            parent_path.as_posix(), parent_metadata,
        ),
        "cgroup2_mount_fd_fact": fd_fact(
            251, "CGROUP2_MOUNT_DIRECTORY", "O_PATH",
            root.as_posix(), mount_metadata,
        ),
        "source_service_fd_fact": fd_fact(
            252, "SOURCE_SYSTEMD_SERVICE_DIRECTORY", "O_RDONLY",
            source_service_path.as_posix(), service_metadata,
        ),
        "nearest_common_ancestor_path": parent_path.as_posix(),
        "nearest_common_ancestor_is_app_slice": True,
        "parent_cgroup_procs_o_wronly_openable": True,
        "planned_measurement_root_observation": {
            "phase": "BEFORE_POPEN",
            "campaign_attempt_id": authority.attempt_id,
            "root_name": measurement_path.name,
            "ownership_acquired": False,
            "root_state": "ABSENT",
            "residual_tree_or_process_possible": False,
        },
        "planned_measurement_root_absent": True,
        "t1_complete_before_child_popen": True,
    }
    placement_t2 = {
        "schema": protocol.PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA,
        "boundary": "T2_BEFORE_SCIENTIFIC_ATTEMPT_O_EXCL",
        "target": "measurement",
        "token": token,
        "unit_name": unit_name,
        "source_membership": source_membership,
        "expected_source_membership": source_membership,
        "self_pid": os.getpid(),
        "self_pid_in_source_cgroup_procs": True,
        "source_service_fd": 252,
        "source_service_device": service_metadata.st_dev,
        "source_service_inode": service_metadata.st_ino,
        "cgroup_namespace_inode": parent_fact["cgroup_namespace_inode"],
        "nearest_common_ancestor_path": parent_path.as_posix(),
        "nearest_common_ancestor_is_app_slice": True,
        "parent_cgroup_procs_o_wronly_openable": True,
        "planned_measurement_root_state": "ABSENT",
        "scientific_progress_present_paths": [],
        "scientific_progress_absent": True,
    }
    topology = runtime.MeasurementCgroupTopologyReceiptV180R12R4(
        parent_fact,
        delegated,
        measurement,
        supervisor,
        worker,
        "cgroup2",
        ("memory", "pids"),
        ("memory", "pids"),
        16 * 1024 * 1024 * 1024,
        2,
        1,
        1,
        False,
        0,
        (0, 0),
        tuple(controls),
        placement_t1,
        placement_t2,
    )
    return (
        run.CgroupTreeV180R12R4(
            parent_path,
            measurement_path,
            supervisor_path,
            worker_path,
            measurement_fd,
            supervisor_fd,
            worker_fd,
            parent_fd,
            mount_fd,
            source_service_fd,
            tuple(retained),
            topology,
        ),
        raw_values,
    )


class _SyntheticCgroupManager:
    def __init__(self, tree, raw_values) -> None:
        self.tree = tree
        self.raw_values = raw_values
        self.closed = False

    def create(
        self,
        parent_fact,
        attempt_id,
        *,
        production_runtime_placement_t1,
        production_runtime_placement_t2,
    ):
        assert parent_fact == dict(self.tree.topology_receipt.cgroup_parent_fact)
        assert attempt_id in self.tree.root_path.name
        assert production_runtime_placement_t1 == dict(
            self.tree.topology_receipt.production_runtime_placement_t1
        )
        assert production_runtime_placement_t2 == dict(
            self.tree.topology_receipt.production_runtime_placement_t2
        )
        return self.tree

    def observe_receipt(
        self,
        tree,
        *,
        supervisor_reap_receipt,
        worker_reap_receipt,
        operation_id,
    ):
        assert tree is self.tree
        readbacks = tuple(
            runtime.CgroupControlFileReadbackV180R12R4(
                control,
                self.raw_values[(control.node_role, control.name)],
                True,
                True,
                True,
            )
            for control in tree.topology_receipt.control_files
        )
        return runtime.CgroupV2ObservationReceiptV180R12R4(
            tree.topology_receipt,
            supervisor_reap_receipt,
            worker_reap_receipt,
            operation_id,
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
            readbacks,
            True,
        )

    def kill(self, tree) -> None:  # failure-only synthetic cleanup
        assert tree is self.tree

    def observe_failure(self, tree):  # pragma: no cover - success must not call it
        return {"observation_errors": (f"unexpected failure: {tree}",)}

    def close(self, tree) -> None:
        assert tree is self.tree and not self.closed
        descriptors = {
            tree.topology_receipt.delegated_parent.directory_fd,
            tree.root_fd,
            tree.supervisor_fd,
            tree.worker_fd,
            *(row[2] for row in tree.retained_control_fds),
        }
        for descriptor in descriptors:
            os.close(descriptor)
        self.closed = True


def _verified_internal_context(payload, secret, *, target_payload, roles):
    return types.MappingProxyType(
        {
            "schema": "acfqp.v180r12r4_verified_internal_launch_context.v1",
            "target": payload["target"],
            "actor_role": payload["actor_role"],
            "parent_actor_role": payload["parent_actor_role"],
            "protocol_id": payload["protocol_id"],
            "authorization_id": payload["authorization_id"],
            "authorization_evidence_id": payload["authorization_evidence_id"],
            "attempt_id": payload["attempt_id"],
            "campaign_measurement_execution_slot_id": payload[
                "campaign_measurement_execution_slot_id"
            ],
            "logical_occurrence_id": payload["logical_occurrence_id"],
            "execution_nonce": payload["execution_nonce"],
            "prelaunch_materialization_terminal_id": payload[
                "prelaunch_materialization_terminal_id"
            ],
            "prelaunch_launch_rule_id": payload["prelaunch_launch_rule_id"],
            "measurement_launch_attempt_id": payload[
                "measurement_launch_attempt_id"
            ],
            "launch_operation_id": payload["launch_operation_id"],
            "manifest_sha256": payload["launch_manifest_sha256"],
            "precompiled_source_bundle_sha256": payload[
                "precompiled_source_bundle_sha256"
            ],
            "inherited_fd_roles": roles,
            "target_payload": types.MappingProxyType(dict(target_payload)),
            "parent_to_child_mac_key": secret,
            "parent_context_mac": payload["context_mac"],
            "context_consumed_once": True,
        }
    )


class _SyntheticWorkerAdapter:
    def __init__(self, fixed: _FixedFDGuard) -> None:
        self.fixed = fixed
        self.thread: threading.Thread | None = None
        self.errors: list[BaseException] = []
        self.pipe_writer = -1
        self.closed = False

    def launch_worker(
        self,
        *,
        context,
        start,
        topology,
        stage_effects,
        subject_output,
        operation_id,
    ):
        del start
        parent, child = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
        )
        supervise.configure_seqpacket_pair_v180r12r4(parent, child)
        secret = b"w" * 32
        pipe_reader, self.pipe_writer = os.pipe2(os.O_CLOEXEC)
        pipe_metadata = os.fstat(pipe_reader)
        pid = os.getpid()
        starttime = work._proc_starttime_ticks_v180r12r4(pid)
        target = topology.worker_leaf
        membership = "0::" + target.membership_path
        handle = supervise._WorkerProcessHandleV180R12R4(
            pid,
            pipe_reader,
            pipe_metadata.st_dev,
            pipe_metadata.st_ino,
            starttime,
            pid,
            (pid,),
            membership,
            parent,
        )
        birth = runtime.PidfdBirthReceiptV180R12R4(
            topology,
            context["attempt_id"],
            operation_id,
            runtime.ProcessRoleV180R12R4.WORKER,
            pid,
            pipe_reader,
            pipe_metadata.st_dev,
            pipe_metadata.st_ino,
            ("CLONE_INTO_CGROUP", "CLONE_PIDFD"),
            supervise.WORKER_CGROUP_FD,
            os.fstat(supervise.WORKER_CGROUP_FD).st_dev,
            os.fstat(supervise.WORKER_CGROUP_FD).st_ino,
            target.path,
            starttime,
            pid,
            (pid,),
            membership,
            True,
            True,
            None,
        )
        self.fixed.install(work.INTERNAL_IPC_FD, child.fileno())
        self.fixed.install(
            work.TERMINAL_STAGE_FD,
            stage_effects.terminal_stage.worker_source_descriptor,
        )
        self.fixed.install(
            work.VERIFICATION_STAGE_FD,
            stage_effects.verification_stage.worker_source_descriptor,
        )
        self.fixed.install(
            work.SUBJECT_RESULT_FD, subject_output.worker_source_descriptor
        )
        for descriptor in (
            work.INTERNAL_IPC_FD,
            work.TERMINAL_STAGE_FD,
            work.VERIFICATION_STAGE_FD,
            work.SUBJECT_RESULT_FD,
        ):
            os.set_inheritable(descriptor, False)
        payload = {
            "target": "worker",
            "actor_role": "WORKER",
            "parent_actor_role": "SUPERVISOR",
            "protocol_id": context["protocol_id"],
            "authorization_id": context["authorization_id"],
            "authorization_evidence_id": context["authorization_evidence_id"],
            "attempt_id": context["attempt_id"],
            "campaign_measurement_execution_slot_id": context[
                "campaign_measurement_execution_slot_id"
            ],
            "logical_occurrence_id": context["logical_occurrence_id"],
            "execution_nonce": context["execution_nonce"],
            "prelaunch_materialization_terminal_id": context[
                "prelaunch_materialization_terminal_id"
            ],
            "prelaunch_launch_rule_id": context["prelaunch_launch_rule_id"],
            "measurement_launch_attempt_id": context[
                "measurement_launch_attempt_id"
            ],
            "launch_operation_id": operation_id,
            "launch_manifest_sha256": context["manifest_sha256"],
            "precompiled_source_bundle_sha256": context[
                "precompiled_source_bundle_sha256"
            ],
            "context_mac": "b" * 64,
        }
        worker_context = _verified_internal_context(
            payload,
            secret,
            target_payload={
                "terminal_stage_byte_count": 199_755,
                "verification_stage_byte_count": 2_752,
                "subject_result_initial_byte_count": 0,
            },
            roles=work._EXPECTED_FD_ROLES,
        )
        ready = threading.Event()

        def worker_main() -> None:
            duplicate = socket.fromfd(
                child.fileno(), socket.AF_UNIX, socket.SOCK_SEQPACKET
            )
            ready.set()
            try:
                channel = work._AuthenticatedWorkerChannelV180R12R4(
                    duplicate, secret, worker_context
                )
                frame_type, body = channel.receive()
                assert frame_type == "WORKER_HANDOFF"
                handoff = work.validate_supervisor_worker_handoff_v180r12r4(
                    body, verified_context=worker_context
                )
                bridge = work._AuthenticatedWorkerBridgeV180R12R4(
                    channel,
                    handoff,
                    handoff.document["next_campaign_event_sequence"],
                )
                work.run_validated_worker_handoff_v180r12r4(
                    handoff, bridge=bridge
                )
                assert bridge.open_event is None
                assert bridge.campaign_event_sequence == 609
                duplicate.shutdown(socket.SHUT_WR)
            except BaseException as error:
                self.errors.append(error)
                try:
                    duplicate.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            finally:
                duplicate.close()
                for descriptor in (
                    work.INTERNAL_IPC_FD,
                    work.TERMINAL_STAGE_FD,
                    work.VERIFICATION_STAGE_FD,
                    work.SUBJECT_RESULT_FD,
                ):
                    self.fixed.close(descriptor)

        self.thread = threading.Thread(target=worker_main, daemon=True)
        self.thread.start()
        assert ready.wait(5)
        child.close()
        return handle, birth, secret

    def reap_worker(self, handle, birth):
        assert self.thread is not None
        self.thread.join(60)
        assert not self.thread.is_alive(), "synthetic worker thread deadlocked"
        if self.errors:
            raise self.errors[0]
        os.close(self.pipe_writer)
        self.pipe_writer = -1
        poller = select.poll()
        poller.register(handle.pidfd, select.POLLIN)
        assert poller.poll(0)
        return runtime.PidfdReapReceiptV180R12R4(
            birth,
            birth.operation_id,
            handle.pidfd_device,
            handle.pidfd_inode,
            handle.proc_starttime_ticks,
            "P_PIDFD",
            handle.pidfd,
            "CLD_EXITED",
            0,
            True,
            False,
            0,
        )

    def close_reaped_worker(self, handle) -> None:
        assert not self.closed
        os.close(handle.pidfd)
        handle.channel.close()
        self.closed = True

    def terminate_worker(self, handle) -> None:  # pragma: no cover
        if self.pipe_writer >= 0:
            os.close(self.pipe_writer)
            self.pipe_writer = -1
        try:
            os.close(handle.pidfd)
        except OSError:
            pass
        handle.channel.close()


class _SyntheticLauncher:
    def __init__(self, *, fixed: _FixedFDGuard, output_root: Path) -> None:
        self.fixed = fixed
        self.output_root = output_root
        self.thread: threading.Thread | None = None
        self.errors: list[BaseException] = []
        self.pipe_writer = -1
        self.worker_adapter = _SyntheticWorkerAdapter(fixed)
        self.thread_socket: socket.socket | None = None

    def launch_exec(
        self,
        *,
        role,
        target_cgroup_fd,
        expected_cgroup_membership_line,
        argv,
        env,
        inherited_fd_map,
        pre_clone_revalidate,
    ):
        del argv, env
        assert role == "SUPERVISOR"
        secret = os.pread(inherited_fd_map[run.INTERNAL_MAC_KEY_FD], 32, 0)
        raw_context = os.pread(
            inherited_fd_map[run.INTERNAL_CONTEXT_FD], 1024 * 1024, 0
        )
        payload = json.loads(raw_context)
        supervisor_context = _verified_internal_context(
            payload,
            secret,
            target_payload={
                "repository_root_fd": supervise.REPOSITORY_ROOT_FD,
                "worker_cgroup_fd": supervise.WORKER_CGROUP_FD,
            },
            roles=supervise._EXPECTED_FD_ROLES,
        )
        self.fixed.install(
            supervise.INTERNAL_IPC_FD,
            inherited_fd_map[run.INTERNAL_IPC_FD],
        )
        os.set_inheritable(supervise.INTERNAL_IPC_FD, False)
        pipe_reader, self.pipe_writer = os.pipe2(os.O_CLOEXEC)
        pipe_metadata = os.fstat(pipe_reader)
        pid = os.getpid()
        target = os.fstat(target_cgroup_fd)
        pre_clone_revalidate()
        process = run.ProcessHandleV180R12R4(
            role,
            pid,
            pipe_reader,
            pipe_metadata.st_dev,
            pipe_metadata.st_ino,
            run._proc_starttime(pid),
            pid,
            (pid,),
            expected_cgroup_membership_line,
            target_cgroup_fd,
            target.st_dev,
            target.st_ino,
        )
        ready = threading.Event()

        def supervisor_main() -> None:
            duplicate = socket.fromfd(
                inherited_fd_map[run.INTERNAL_IPC_FD],
                socket.AF_UNIX,
                socket.SOCK_SEQPACKET,
            )
            self.thread_socket = duplicate
            ready.set()
            output_root_fd = -1
            try:
                channel = supervise._AuthenticatedSupervisorChannelV180R12R4(
                    duplicate,
                    secret,
                    supervisor_context,
                    parent_actor_role="OBSERVER",
                    child_actor_role="SUPERVISOR",
                    channel_id=supervisor_context["launch_operation_id"],
                )
                received = channel.receive()
                assert received is not None and received[0] == "SUPERVISOR_START"
                start = supervise.validate_observer_supervisor_start_v180r12r4(
                    received[1], verified_context=supervisor_context
                )
                output_root_fd = os.open(
                    self.output_root,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                )
                supervise.run_authenticated_supervisor_lifecycle_v180r12r4(
                    context=supervisor_context,
                    start=start,
                    observer_channel=channel,
                    repository_root_fd=supervise.REPOSITORY_ROOT_FD,
                    output_root_fd=output_root_fd,
                    worker_adapter=self.worker_adapter,
                )
            except BaseException as error:
                self.errors.append(error)
                try:
                    duplicate.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            finally:
                if output_root_fd >= 0:
                    os.close(output_root_fd)
                duplicate.close()

        self.thread = threading.Thread(target=supervisor_main, daemon=True)
        self.thread.start()
        assert ready.wait(5)
        return process

    def reap(self, handle, *, deadline_ns, monotonic_ns):
        del handle, deadline_ns, monotonic_ns
        assert self.thread is not None
        self.thread.join(90)
        assert not self.thread.is_alive(), "synthetic supervisor thread deadlocked"
        if self.errors:
            raise self.errors[0]
        os.close(self.pipe_writer)
        self.pipe_writer = -1
        return SimpleNamespace(
            si_pid=os.getpid(), si_code=os.CLD_EXITED, si_status=0
        )

    def signal(self, handle, sig) -> None:  # pragma: no cover
        del handle, sig
        if self.thread_socket is not None:
            try:
                self.thread_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if self.pipe_writer >= 0:
            os.close(self.pipe_writer)
            self.pipe_writer = -1


def test_full_authenticated_outer_supervisor_worker_lifecycle_consumes_625_and_328(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Exercise all three real bridges with only /tmp and process-boundary mocks."""

    authority = _authority()
    inventory_diagnostic: dict[str, object] = {}
    original_validate_inventory = (
        runtime.CampaignMeasurementSupervisorV180R12R4.
        validate_registered_evidence_bundle
    )

    def capture_inventory(self):
        documents = self._evidence_documents_by_id
        inventory_diagnostic["count"] = len(documents)
        schemas = [document["schema"] for document in documents.values()]
        inventory_diagnostic["schema_counts"] = {
            schema: schemas.count(schema) for schema in sorted(set(schemas))
        }
        return original_validate_inventory(self)

    monkeypatch.setattr(
        runtime.CampaignMeasurementSupervisorV180R12R4,
        "validate_registered_evidence_bundle",
        capture_inventory,
    )
    attempt, operation_manifest = run.build_campaign_attempt_record_v180r12r4(
        authority
    )
    bundle_raw = b"v180r12r4 synthetic sealed application bundle"
    bundle_sha256 = hashlib.sha256(bundle_raw).hexdigest()
    source_manifest = ledger.issue_native_zero_source_manifest_v180r12r4(
        protocol_id=authority.protocol_id,
        authorization_id=authority.authorization_id,
        attempt_id=authority.attempt_id,
        operation_manifest_id=operation_manifest[
            "campaign_operation_manifest_id"
        ],
        prelaunch_launch_manifest_sha256=(
            authority.prelaunch_launch_manifest_sha256
        ),
        precompiled_source_bundle_sha256=bundle_sha256,
        precompiled_source_rows=ledger_fixture._precompiled_source_rows(),
    )
    import_inventory = ledger.issue_native_zero_import_inventory_v180r12r4(
        protocol_id=authority.protocol_id,
        authorization_id=authority.authorization_id,
        attempt_id=authority.attempt_id,
        source_manifest=source_manifest,
    )

    repository = tmp_path / "repository"
    for fact in work.core.FROZEN_INPUT_FACTS_V180R12R4:
        source = ROOT / fact.relative_path
        target = repository / fact.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        target.chmod(0o400)
    output_root = repository.joinpath(*supervise.OUTPUT_ROOT_PARTS)
    output_root.mkdir(parents=True)
    output_root.chmod(0o700)
    c_pre = tmp_path / "c_pre"
    c_pre.mkdir()

    with _FixedFDGuard() as fixed:
        bundle_fd = run._sealed_read_only_runtime_memfd_v180r12r4(
            "v180r12r4-synthetic-bundle", bundle_raw
        )
        repository_fd = os.open(
            repository,
            os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        try:
            fixed.install(run.PRECOMPILED_SOURCE_BUNDLE_FD, bundle_fd)
            fixed.install(run.SUPERVISOR_REPOSITORY_ROOT_FD, repository_fd)
        finally:
            os.close(bundle_fd)
            os.close(repository_fd)
        tree, raw_values = _make_synthetic_cgroup_tree(
            tmp_path / "cgroup-mount", authority, fixed
        )
        manager = _SyntheticCgroupManager(tree, raw_values)
        launcher = _SyntheticLauncher(fixed=fixed, output_root=output_root)
        context = types.MappingProxyType(
            {
                "target": "measurement",
                "campaign_attempt_id": authority.attempt_id,
                "repository_root": repository.as_posix(),
                "c_pre_root": c_pre.as_posix(),
                "prereg_commit_id": "b" * 40,
                "precompiled_source_bundle_sha256": bundle_sha256,
                "cgroup_parent_fact": dict(
                    tree.topology_receipt.cgroup_parent_fact
                ),
                "production_runtime_placement_t1": dict(
                    tree.topology_receipt.production_runtime_placement_t1
                ),
                "production_runtime_placement_t2": dict(
                    tree.topology_receipt.production_runtime_placement_t2
                ),
                "hard_deadline_ns": time.monotonic_ns() + 180_000_000_000,
            }
        )
        expected_source_membership = tree.topology_receipt.production_runtime_placement_t1[
            "expected_source_membership"
        ]
        monkeypatch.setattr(
            run, "_proc_cgroup", lambda pid: expected_source_membership
        )
        monkeypatch.setattr(
            run.LinuxCgroupV2V180R12R4,
            "_fstatfs_type",
            staticmethod(lambda descriptor: run.CGROUP2_SUPER_MAGIC),
        )
        adapter = run.LinuxOuterEffectAdapterV180R12R4(
            context=context,
            authority=authority,
            attempt_document=attempt,
            operation_manifest_document=operation_manifest,
            native_zero_source_manifest_document=source_manifest,
            native_zero_import_inventory_document=import_inventory,
            repository_root_fd=run.SUPERVISOR_REPOSITORY_ROOT_FD,
            launcher=launcher,
            cgroup_manager=manager,
        )
        expected_worker_membership = (
            "0::" + tree.topology_receipt.worker_leaf.membership_path
        )
        monkeypatch.setattr(
            work,
            "_proc_cgroup_line_v180r12r4",
            lambda pid: expected_worker_membership if pid == os.getpid() else "",
        )
        store = run.DurableStoreV180R12R4(output_root)
        try:
            deadline = time.monotonic_ns() + 180_000_000_000
            try:
                journal = run.run_one_shot_outer_v180r12r4(
                    store=store,
                    adapter=adapter,
                    attempt_document=attempt,
                    attempt_authority=authority,
                    protocol_id=authority.protocol_id,
                    authorization_id=authority.authorization_id,
                    attempt_id=authority.attempt_id,
                    campaign_deadline_ns=deadline,
                    forbidden_progress_paths=(),
                    preregistered_evidence_documents=(
                        operation_manifest,
                        source_manifest,
                        import_inventory,
                    ),
                )
            except BaseException as error:
                event_root = output_root / run.EVENTS_RELATIVE_PATH
                raise AssertionError(
                    "combined lifecycle failed; supervisor_errors="
                    + repr(launcher.errors)
                    + "; worker_errors="
                    + repr(launcher.worker_adapter.errors)
                    + "; durable_events="
                    + str(len(tuple(event_root.iterdir())) if event_root.exists() else 0)
                    + "; inventory="
                    + repr(inventory_diagnostic)
                ) from error
            assert journal.next_sequence == 625
            assert len(journal.read_complete_event_documents()) == 625
            terminal = json.loads(
                store.read_exact(run.TERMINAL_RELATIVE_PATH, 16 * 1024 * 1024)
            )
            assert terminal["event_count"] == 625
            assert terminal["evidence_document_count"] == 328
            assert terminal["os_receipt_document_count"] == 12
            evidence = terminal["campaign_measurement_ledger"]["evidence_documents"]
            topology = next(
                row
                for row in evidence
                if row["schema"]
                == "acfqp.campaign_cgroup_topology_receipt.v180r12r4"
            )
            births = {
                row["process_role"]: row
                for row in evidence
                if row["schema"]
                == "acfqp.campaign_pidfd_birth_receipt.v180r12r4"
            }
            assert topology["production_runtime_placement_t1"]["schema"] == (
                protocol.PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
            )
            assert topology["production_runtime_placement_t2"]["schema"] == (
                protocol.PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA
            )
            assert births["SUPERVISOR"]["production_runtime_placement_t3"][
                "schema"
            ] == protocol.PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
            assert births["WORKER"]["production_runtime_placement_t3"] is None
            assert not store.exists(run.FAILURE_RELATIVE_PATH)
            assert manager.closed
            assert launcher.worker_adapter.closed
            assert launcher.errors == []
            assert launcher.worker_adapter.errors == []
        finally:
            store.close()
