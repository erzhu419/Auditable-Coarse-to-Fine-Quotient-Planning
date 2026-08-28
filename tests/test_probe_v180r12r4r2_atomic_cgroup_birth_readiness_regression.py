from __future__ import annotations

import errno
import ast
import base64
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import stat
import sys
import tempfile
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe_v180r12r4r2_atomic_cgroup_birth_readiness.py"
SPEC = importlib.util.spec_from_file_location("v180r12r4r2_atomic_birth_probe", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)
TOOLCHAIN_FIXTURE_FACTS = probe.observe_toolchain_facts()
PREDECESSOR_PROBE_RAW = (
    ROOT / probe.PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH
).read_bytes()
PREDECESSOR_ARTIFACT_FIXTURE_FACTS = (
    probe.observe_predecessor_terminal_artifact_facts(ROOT)
)


@pytest.fixture
def tmp_path() -> Path:
    path = Path(tempfile.mkdtemp(prefix="v180r12r4r2-atomic-birth-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _source_fact(relative_path: str, marker: str) -> dict[str, object]:
    return {
        "schema": probe.SOURCE_FACT_SCHEMA,
        "relative_path": relative_path,
        "git_mode": "100644",
        "git_blob_id": marker * 40,
        "byte_count": 1234,
        "sha256": marker * 64,
    }


def _source_fact_for_bytes(relative_path: str, raw: bytes) -> dict[str, object]:
    return {
        "schema": probe.SOURCE_FACT_SCHEMA,
        "relative_path": relative_path,
        "git_mode": "100644",
        "git_blob_id": probe._git_blob_id(raw),
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _host_parent_fact() -> dict[str, object]:
    return {
        "schema": probe.HOST_PARENT_SCHEMA,
        "mount_point": "/sys/fs/cgroup",
        "mount_device": 31,
        "mount_inode": 32,
        "app_slice_path": (
            "/sys/fs/cgroup/user.slice/user-1000.slice/"
            "user@1000.service/app.slice"
        ),
        "app_slice_device": 31,
        "app_slice_inode": 33,
        "owner_uid": 1000,
        "owner_gid": 1000,
        "mode": 0o755,
        "controllers": ["memory", "pids"],
        "subtree_control": ["memory", "pids"],
        "cgroup_type": "domain",
        "cgroup_namespace_inode": 34,
        "cgroup_procs_device": 31,
        "cgroup_procs_inode": 35,
        "cgroup_procs_owner_uid": 1000,
        "cgroup_procs_owner_gid": 1000,
        "cgroup_procs_mode": 0o644,
        "runtime_dir_path": "/run/user/1000",
        "runtime_dir_device": 41,
        "runtime_dir_inode": 42,
        "runtime_dir_owner_uid": 1000,
        "runtime_dir_owner_gid": 1000,
        "runtime_dir_mode": 0o700,
        "user_bus_path": "/run/user/1000/bus",
        "user_bus_device": 41,
        "user_bus_inode": 43,
        "user_bus_owner_uid": 1000,
        "user_bus_owner_gid": 1000,
        "user_bus_mode": 0o777,
        "user_bus_file_type": "socket",
        "toolchain_facts": json.loads(json.dumps(TOOLCHAIN_FIXTURE_FACTS)),
    }


def _materialize_predecessor_closure(repository_root: Path) -> None:
    source_path = repository_root / probe.PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(PREDECESSOR_PROBE_RAW)
    for spec in probe.PREDECESSOR_TERMINAL_ARTIFACT_SPECS:
        target = repository_root / spec["relative_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / spec["relative_path"]).read_bytes())


def _authority(repository_root: Path) -> tuple[dict[str, object], bytes, dict[str, str]]:
    _materialize_predecessor_closure(repository_root)
    external_path = repository_root / probe.EXTERNAL_ROOT_RELATIVE_PATH
    artifact_root = repository_root / probe.ARTIFACT_ROOT_RELATIVE_PATH
    invocation = probe.build_systemd_invocation_contract(
        repository_root=repository_root,
        external_root_path=external_path,
        artifact_root=artifact_root,
    )
    authority = probe.build_external_root_document(
        c_probe_commit_id="c" * 40,
        c_probe_tree_id="d" * 40,
        probe_source_fact=_source_fact(probe.PROBE_SOURCE_RELATIVE_PATH, "a"),
        predecessor_probe_source_fact=_source_fact_for_bytes(
            probe.PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH,
            PREDECESSOR_PROBE_RAW,
        ),
        predecessor_terminal_artifact_facts=json.loads(
            json.dumps(PREDECESSOR_ARTIFACT_FIXTURE_FACTS)
        ),
        host_parent_fact=_host_parent_fact(),
        systemd_invocation_contract=invocation,
    )
    raw = probe.canonical_json_bytes(authority)
    environment = probe.expected_clean_environment(
        str(external_path), hashlib.sha256(raw).hexdigest()
    )
    return authority, raw, environment


def _artifact_store(
    repository_root: Path,
    *,
    checkpoint=None,
) -> probe.DurableArtifactStore:
    root = repository_root / probe.ARTIFACT_ROOT_RELATIVE_PATH
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    return probe.DurableArtifactStore(root, publication_checkpoint=checkpoint)


def _seed_outer_attempt(
    store: probe.DurableArtifactStore,
    authority: dict[str, object],
    raw: bytes,
) -> dict[str, object]:
    if store.inventory_names(phase="FIXTURE_SEED_OUTER_ENTRY") == frozenset():
        _seed_prepared(store, authority, raw)
    attempt = probe.build_outer_launch_attempt_document(authority, raw)
    store.write_once(
        probe.OUTER_LAUNCH_ATTEMPT_NAME,
        probe.canonical_json_bytes(attempt),
    )
    return attempt


def _seed_prepared(
    store: probe.DurableArtifactStore,
    authority: dict[str, object],
    raw: bytes,
) -> tuple[dict[str, object], dict[str, object]]:
    repository_root = store.root.parents[2]
    external = Path(
        authority["systemd_invocation_contract"]["external_root_path"]
    )
    external.write_bytes(raw)
    external.chmod(0o400)
    with probe._open_prepare_parent_chain(
        repository_root, create=False
    ) as parent:
        claim = probe._claim_artifact_root(parent, create=False)
        journal = probe.PrepareJournalStore(parent)
        attempt = probe.build_prepare_attempt_document(authority, raw)
        receipt = probe.build_prepare_receipt_document(
            attempt, authority, raw, claim
        )
        journal.write_once(
            probe.PREPARE_ATTEMPT_NAME,
            probe.canonical_json_bytes(attempt),
            token=probe.PublicationOwnershipToken(probe.PREPARE_ATTEMPT_NAME),
        )
        journal.write_once(
            probe.PREPARE_RECEIPT_NAME,
            probe.canonical_json_bytes(receipt),
            token=probe.PublicationOwnershipToken(probe.PREPARE_RECEIPT_NAME),
        )
    return attempt, receipt


class FakeRuntime:
    """Pure state-machine fixture; no cgroup, syscall, socket, or child."""

    def __init__(
        self,
        *,
        fail_method: str | None = None,
        cleanup_failures: frozenset[str] = frozenset(),
        handshake_membership_drift: bool = False,
    ) -> None:
        self.fail_method = fail_method
        self.cleanup_failures = cleanup_failures
        self.handshake_membership_drift = handshake_membership_drift
        self.calls: list[str] = []
        self.removed = False
        self.target_created = False
        self.child: probe.ChildHandle | None = None

    def _call(self, name: str) -> None:
        self.calls.append(name)
        if self.fail_method == name or name in self.cleanup_failures:
            raise OSError(errno.EACCES, f"fixture failure at {name}")

    @staticmethod
    def _memberships() -> tuple[str, str, str]:
        app = "/user.slice/user-1000.slice/user@1000.service/app.slice"
        source = f"{app}/{probe.SERVICE_UNIT_NAME}"
        target = f"{app}/{probe.TARGET_CGROUP_NAME}"
        return app, source, target

    @staticmethod
    def _manager_absent_properties() -> dict[str, str]:
        return {
            "LoadState": "loaded",
            "ActiveState": "inactive",
            "SubState": "dead",
            "ControlGroup": "",
            "BindsTo": "",
            "After": probe.SERVICE_SLICE,
            "Delegate": "no",
            "CollectMode": "inactive",
            "Slice": probe.SERVICE_SLICE,
            "Transient": "no",
            "FragmentPath": "",
            "UnitFileState": "",
            "Job": "",
        }

    @staticmethod
    def _manager_active_properties(target_membership: str) -> dict[str, str]:
        contract = probe.build_target_lifecycle_contract(os.geteuid())
        return {
            "LoadState": "loaded",
            "ActiveState": "active",
            "SubState": "active",
            "ControlGroup": target_membership,
            "BindsTo": probe.SERVICE_UNIT_NAME,
            "After": f"app.slice {probe.SERVICE_UNIT_NAME}",
            "Delegate": "no",
            "CollectMode": "inactive-or-failed",
            "Slice": probe.SERVICE_SLICE,
            "Transient": "yes",
            "FragmentPath": contract["transient_fragment_path"],
            "UnitFileState": "transient",
            "Job": "",
        }

    @staticmethod
    def _parent_absent_observation() -> dict[str, object]:
        return {
            "name": probe.TARGET_CGROUP_NAME,
            "stat_errno": errno.ENOENT,
            "openat_errno": errno.ENOENT,
            "named_device": None,
            "named_inode": None,
            "opened_device": None,
            "opened_inode": None,
            "parent_inventory": [],
            "name_absent": True,
            "name_present_identity_exact": False,
        }

    @staticmethod
    def _success_fragment_path() -> str:
        return probe.build_target_lifecycle_contract(os.geteuid())[
            "transient_fragment_path"
        ]

    @staticmethod
    def _retained_ofd_detach_fact(
        target: probe.TargetHandle,
    ) -> dict[str, object]:
        return {
            "device": target.device,
            "inode": target.inode,
            "mode": stat.S_IFDIR | 0o755,
            "nlink": 2,
            "fstatfs_type": probe.CGROUP2_SUPER_MAGIC,
            "proc_fd_link": f"{target.path} (deleted)",
            "proc_fd_link_errno": None,
            "deleted_marker": True,
            "cgroup_type_errno": errno.ENOENT,
            "cgroup_events_errno": errno.ENOENT,
            "cgroup_procs_errno": errno.ENOENT,
            "conformant": True,
        }

    @staticmethod
    def _property_raw(properties: dict[str, str], keys) -> bytes:
        return "".join(f"{key}={properties[key]}\n" for key in keys).encode(
            "utf-8"
        )

    @classmethod
    def _success_create_diagnostic(
        cls, target: probe.TargetHandle
    ) -> dict[str, object]:
        contract = probe.build_target_lifecycle_contract(os.geteuid())
        active = cls._manager_active_properties(target.membership)
        _conformance, trace = probe.poll_target_manager_conformance(
            lambda: probe.BoundedProcessResult(
                tuple(contract["active_show_argv"]),
                0,
                cls._property_raw(
                    active, probe.TARGET_MANAGER_ACTIVE_PROPERTIES
                ),
                b"",
                False,
                False,
            ),
            expected_control_group=target.membership,
            deadline_ns=10**30,
            sleep=lambda _seconds: None,
        )
        absent = cls._manager_absent_properties()
        return probe.build_target_create_diagnostic(
            target_membership=target.membership,
            precreate_absence_show_result=probe.BoundedProcessResult(
                tuple(contract["absence_show_argv"]),
                0,
                cls._property_raw(
                    absent, probe.TARGET_MANAGER_ABSENCE_PROPERTIES
                ),
                b"",
                False,
                False,
            ),
            precreate_manager_properties=absent,
            precreate_manager_implicit_absence=True,
            precreate_target_path_absent=True,
            precreate_transient_fragment_absent=True,
            precreate_transient_fragment_path=contract[
                "transient_fragment_path"
            ],
            precreate_transient_fragment_stat_errno=errno.ENOENT,
            precreate_parent_stat_errno=errno.ENOENT,
            precreate_parent_openat_errno=errno.ENOENT,
            precreate_parent_inventory=[],
            manager_create_result=probe.BoundedProcessResult(
                tuple(contract["create_argv"]),
                0,
                b'o "/org/freedesktop/systemd1/job/123"\n',
                b"",
                False,
                False,
            ),
            manager_create_job_path="/org/freedesktop/systemd1/job/123",
            ownership_acquired=True,
            trace=trace,
            full_target_path_ofd_conformance=True,
            target_device=target.device,
            target_inode=target.inode,
            exception_phase=None,
            exception_cause=None,
            target_creation_error=None,
        )

    def inspect_service(self, _authority: object, _deadline_ns: int):
        self._call("inspect_service")
        app, source, target = self._memberships()
        authority = dict(_authority)
        host = authority["host_parent_fact"]
        contract = authority["systemd_invocation_contract"][
            "target_lifecycle_contract"
        ]
        nca_permission = {
            "opened_for_write": True,
            "errno": None,
            "errno_name": None,
            "device": host["cgroup_procs_device"],
            "inode": host["cgroup_procs_inode"],
            "mode": host["cgroup_procs_mode"],
            "owner_uid": host["cgroup_procs_owner_uid"],
            "owner_gid": host["cgroup_procs_owner_gid"],
        }
        detail = {
            "pid": 7001,
            "uid": host["owner_uid"],
            "gid": host["owner_gid"],
            "membership_line": f"0::{source}",
            "app_slice_membership": app,
            "source_membership": source,
            "target_membership": target,
            "nearest_common_ancestor": app,
            "service_path": f"{host['app_slice_path']}/{probe.SERVICE_UNIT_NAME}",
            "service_device": 31,
            "service_inode": 36,
            "service_owner_uid": host["owner_uid"],
            "service_owner_gid": host["owner_gid"],
            "service_mode": 0o755,
            "nca_cgroup_procs_write": nca_permission,
            "app_slice_cgroup_procs_write": nca_permission,
            "app_slice_cgroup_procs_write_required": True,
            "service_cgroup_procs_write": {
                "opened_for_write": True,
                "errno": None,
                "errno_name": None,
                "device": 31,
                "inode": 37,
                "mode": 0o644,
                "owner_uid": 1000,
                "owner_gid": 1000,
            },
            "service_procs": [7001],
            "service_type_from_outer_context": "exec",
            "delegate_from_outer_context": True,
            "fixed_target_absent_before_create": True,
            "target_manager_implicit_absence_before_create": True,
            "target_manager_precreate_properties": self._manager_absent_properties(),
            "target_lifecycle_contract": contract,
            "target_lifecycle_unique_authority": (
                "SYSTEMD_USER_MANAGER_ONLY"
            ),
        }
        return (
            probe.ServiceHandle(
                -1,
                -1,
                host["app_slice_path"],
                f"{host['app_slice_path']}/{probe.SERVICE_UNIT_NAME}",
                source,
                target,
                detail,
            ),
            detail,
        )

    def create_target(
        self, service: probe.ServiceHandle, _deadline_ns: int
    ):
        self._call("create_target")
        self.target_created = True
        target = probe.TargetHandle(
            79,
            probe.TARGET_CGROUP_NAME,
            f"{service.app_slice_path}/{probe.TARGET_CGROUP_NAME}",
            service.target_membership,
            31,
            92,
            owned=True,
            manager_created=True,
            identity_continuous=True,
            residual_possible=False,
            manager_unit_ownership_acquired=True,
            full_target_path_ofd_conformance=True,
        )
        target.create_diagnostic = self._success_create_diagnostic(target)
        return target, {
            "target_name": target.name,
            "target_unit_name": probe.TARGET_SERVICE_UNIT_NAME,
            "target_token": probe.TARGET_TOKEN,
            "target_path": target.path,
            "target_membership": target.membership,
            "target_device": target.device,
            "target_inode": target.inode,
            "target_cgroup_type": "domain",
            "target_cgroup_procs_write": {
                "opened_for_write": True,
                "errno": None,
                "errno_name": None,
                "device": target.device,
                "inode": 93,
                "mode": 0o644,
                "owner_uid": 1000,
                "owner_gid": 1000,
            },
            "initial_cgroup_procs": [],
            "initial_cgroup_events": {"frozen": "0", "populated": "0"},
            "transient_fragment_path": service.observation[
                "target_lifecycle_contract"
            ]["transient_fragment_path"],
            "manager_create_argv": service.observation[
                "target_lifecycle_contract"
            ]["create_argv"],
            "manager_create_environment": service.observation[
                "target_lifecycle_contract"
            ]["environment"],
            "manager_create_returncode": 0,
            "manager_create_job_path": "/org/freedesktop/systemd1/job/123",
            "manager_create_stdout": probe._output_fact(
                b'o "/org/freedesktop/systemd1/job/123"\n'
            ),
            "manager_create_stderr": probe._output_fact(b""),
            "manager_properties": self._manager_active_properties(
                target.membership
            ),
            "manager_poll_count": 1,
            "manager_owned_lifecycle": True,
            "manager_create_diagnostic": target.create_diagnostic,
            "probe_path_deletion_calls": 0,
        }

    def clone_child(self, target: probe.TargetHandle, _deadline_ns: int):
        self._call("clone_child")
        self.child = probe.ChildHandle(7002, 81, None)
        return self.child, {
            "pid": 7002,
            "pidfd": 81,
            "clone3_flags": ["CLONE_INTO_CGROUP", "CLONE_PIDFD"],
            "target_cgroup_fd": target.directory_fd,
        }

    def receive_handshake(self, child: probe.ChildHandle, _deadline_ns: int):
        self._call("receive_handshake")
        _app, _source, target = self._memberships()
        membership = "/drift" if self.handshake_membership_drift else target
        payload = {
            "schema": probe.HANDSHAKE_SCHEMA,
            "preflight_token": probe.PREFLIGHT_TOKEN,
            "pid": child.pid,
            "ppid": 7001,
            "membership_line": f"0::{membership}",
        }
        document = probe._self_id_document(
            probe.HANDSHAKE_DOMAIN, "handshake_id", payload
        )
        raw = probe.canonical_json_bytes(document)
        return {
            "handshake_id": document["handshake_id"],
            "pid": document["pid"],
            "ppid": document["ppid"],
            "membership_line": document["membership_line"],
            "canonical_byte_count": len(raw),
            "canonical_sha256": hashlib.sha256(raw).hexdigest(),
        }

    def inspect_child(self, child: probe.ChildHandle, target: probe.TargetHandle):
        self._call("inspect_child")
        return {
            "pid": child.pid,
            "pidfd": child.pidfd,
            "pidfd_device": 93,
            "pidfd_inode": 94,
            "fdinfo_pid": child.pid,
            "fdinfo_nspid": [child.pid],
            "proc_starttime_ticks": 95,
            "membership_line": f"0::{target.membership}",
            "target_device": target.device,
            "target_inode": target.inode,
            "pidfd_cloexec": True,
        }

    def release_child(self, child: probe.ChildHandle):
        self._call("release_child")
        child.released = True
        return {"ack_hex": "06", "released": True}

    def reap_exit_zero(self, child: probe.ChildHandle, _deadline_ns: int):
        self._call("reap_exit_zero")
        child.reaped = True
        return {"pid": child.pid, "si_code": 1, "si_status": 0, "exit_zero": True}

    def kill_child(self, child: probe.ChildHandle):
        self._call("kill_child")
        if child.reaped:
            return {"signal": "NONE", "already_reaped": True}
        return {"signal": "SIGKILL", "pidfd_send_signal_errno": None}

    def reap_cleanup(self, child: probe.ChildHandle, _deadline_ns: int):
        self._call("reap_cleanup")
        already = child.reaped
        child.reaped = True
        if already:
            return {"already_reaped": True, "pid": child.pid}
        return {
            "already_reaped": False,
            "pid": child.pid,
            "si_code": os.CLD_KILLED,
            "si_status": 9,
        }

    def target_empty(self, _target: probe.TargetHandle):
        self._call("target_empty")
        return {"cgroup_procs": [], "populated": 0}

    def remove_target(
        self,
        _service: probe.ServiceHandle,
        _target: probe.TargetHandle | None,
        _deadline_ns: int,
    ):
        assert _target is not None and _target.owned is True
        self.calls.append("remove_target")
        if (
            self.fail_method == "remove_target"
            or "remove_target" in self.cleanup_failures
        ):
            _target.stop_requested = True
            _target.residual_possible = True
            cause = OSError(errno.EACCES, "fixture failure at remove_target")
            outer = probe.make_target_removal_error(
                error_number=errno.EACCES,
                message="owned target unit stop subprocess failed",
                cause=cause,
                diagnostic_arguments={
                    "target": _target,
                    "manager_stop_result": None,
                    "manager_stop_requested": True,
                    "manager_poll_count": 0,
                    "last_manager_properties": None,
                    "target_path_absent": None,
                    "transient_fragment_absent": None,
                    "transient_fragment_path": None,
                    "transient_fragment_stat_errno": None,
                    "parent_named_path_observation": None,
                    "retained_ofd_detach_fact": None,
                    "replacement_detected": False,
                    "manager_implicit_absence_proven": False,
                    "named_path_detached_and_manager_implicit_absence": False,
                    "exception_phase": "STOP_SUBPROCESS",
                },
            )
            raise outer from cause
        self.removed = True
        _target.stop_requested = True
        _target.manager_implicit_absence_proven = True
        _target.residual_possible = False
        _target.named_path_detached_and_manager_implicit_absence = True
        stop_result = probe.BoundedProcessResult(
            tuple(
                _service.observation["target_lifecycle_contract"]["stop_argv"]
            ),
            0,
            b"",
            b"",
            False,
            False,
        )
        cleanup_diagnostic = probe.build_target_cleanup_diagnostic(
            target=_target,
            manager_stop_result=stop_result,
            manager_stop_requested=True,
            manager_poll_count=1,
            last_manager_properties=self._manager_absent_properties(),
            target_path_absent=True,
            transient_fragment_absent=True,
            transient_fragment_path=self._success_fragment_path(),
            transient_fragment_stat_errno=errno.ENOENT,
            parent_named_path_observation=self._parent_absent_observation(),
            retained_ofd_detach_fact=self._retained_ofd_detach_fact(_target),
            replacement_detected=False,
            manager_implicit_absence_proven=True,
            named_path_detached_and_manager_implicit_absence=True,
            exception_phase=None,
            exception_cause=None,
            target_removal_error=None,
        )
        return {
            "removed": True,
            "already_absent": False,
            "ownership_scope": "UNIT_PATH_OFD",
            "manager_unit_ownership_acquired": True,
            "full_target_path_ofd_conformance": True,
            "owned_device": _target.device,
            "owned_inode": _target.inode,
            "manager_stop_argv": _service.observation[
                "target_lifecycle_contract"
            ]["stop_argv"],
            "manager_stop_environment": _service.observation[
                "target_lifecycle_contract"
            ]["environment"],
            "manager_stop_returncode": 0,
            "manager_stop_stdout": probe._output_fact(b""),
            "manager_stop_stderr": probe._output_fact(b""),
            "manager_final_properties": self._manager_absent_properties(),
            "manager_poll_count": 1,
            "manager_implicit_absence_proven": True,
            "target_path_absent": True,
            "transient_fragment_absent": True,
            "transient_fragment_path": self._success_fragment_path(),
            "transient_fragment_stat_errno": errno.ENOENT,
            "parent_named_path_observation": self._parent_absent_observation(),
            "retained_ofd_detach_fact": self._retained_ofd_detach_fact(_target),
            "replacement_detected": False,
            "named_path_detached_and_manager_implicit_absence": True,
            "posix_inode_unlink_claimed": False,
            "probe_path_deletion_calls": 0,
            "cleanup_diagnostic": cleanup_diagnostic,
        }

    def target_absent(
        self,
        _service: probe.ServiceHandle,
        _target: probe.TargetHandle | None,
        _deadline_ns: int,
    ):
        self._call("target_absent")
        if not self.target_created:
            return {
                "target_absent": True,
                "target_transient_instance_implicit_absence": True,
                "target_path_absent": True,
                "transient_fragment_absent": True,
                "transient_fragment_path": self._success_fragment_path(),
                "transient_fragment_stat_errno": errno.ENOENT,
                "parent_named_path_observation": self._parent_absent_observation(),
                "named_path_detached_and_manager_implicit_absence": True,
                "posix_inode_unlink_claimed": False,
                "manager_implicit_absence_proven": True,
                "manager_properties": self._manager_absent_properties(),
                "manager_lifecycle_authority": (
                    "SYSTEMD_USER_MANAGER_ONLY"
                ),
                "probe_path_deletion_calls": 0,
            }
        if not self.removed:
            raise OSError(errno.EEXIST, "fixture target remains")
        return {
            "target_absent": True,
            "target_transient_instance_implicit_absence": True,
            "target_path_absent": True,
            "transient_fragment_absent": True,
            "transient_fragment_path": self._success_fragment_path(),
            "transient_fragment_stat_errno": errno.ENOENT,
            "parent_named_path_observation": self._parent_absent_observation(),
            "named_path_detached_and_manager_implicit_absence": True,
            "posix_inode_unlink_claimed": False,
            "manager_implicit_absence_proven": True,
            "manager_properties": self._manager_absent_properties(),
            "manager_lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
            "probe_path_deletion_calls": 0,
        }

    def close_child(self, _child: probe.ChildHandle) -> None:
        self.calls.append("close_child")

    def close_service(self, _service: probe.ServiceHandle) -> None:
        self.calls.append("close_service")


class FakeGit:
    def __init__(self, blobs: dict[str, bytes], *, dirty: bytes = b"") -> None:
        self.blobs = blobs
        self.dirty = dirty
        self.commit_id = "c" * 40
        self.tree_id = "d" * 40
        self.calls: list[tuple[str, ...]] = []
        self.facts = {
            path: _source_fact_for_bytes(path, raw) for path, raw in blobs.items()
        }
        self.current_paths = {
            probe.PROBE_SOURCE_RELATIVE_PATH,
            *(
                spec["relative_path"]
                for spec in probe.PREDECESSOR_TERMINAL_ARTIFACT_SPECS
            ),
        }
        self.frozen_paths = {
            probe.PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH,
            *(
                spec["relative_path"]
                for spec in probe.PREDECESSOR_TERMINAL_ARTIFACT_SPECS
            ),
        }

    def __call__(self, _root: Path, arguments) -> bytes:
        arguments = tuple(arguments)
        self.calls.append(arguments)
        if arguments == ("status", "--porcelain=v1", "--untracked-files=no"):
            return self.dirty
        if arguments == ("rev-parse", "--verify", "HEAD^{commit}"):
            return (self.commit_id + "\n").encode("ascii")
        if arguments == (
            "rev-parse",
            "--verify",
            f"{self.commit_id}^{{commit}}",
        ):
            return (self.commit_id + "\n").encode("ascii")
        if arguments == (
            "rev-parse",
            "--verify",
            f"{self.commit_id}^{{tree}}",
        ):
            return (self.tree_id + "\n").encode("ascii")
        if arguments == (
            "rev-parse",
            "--verify",
            f"{probe.PREDECESSOR_FROZEN_SOURCE_COMMIT_ID}^{{commit}}",
        ):
            return (
                probe.PREDECESSOR_FROZEN_SOURCE_COMMIT_ID + "\n"
            ).encode("ascii")
        if arguments == (
            "rev-parse",
            "--verify",
            f"{probe.PREDECESSOR_FROZEN_SOURCE_COMMIT_ID}^{{tree}}",
        ):
            return (
                probe.PREDECESSOR_FROZEN_SOURCE_TREE_ID + "\n"
            ).encode("ascii")
        if arguments[:1] == ("ls-tree",):
            commit = arguments[1]
            requested = tuple(arguments[3:])
            if commit == self.commit_id:
                assert set(requested) == self.current_paths
            elif commit == probe.PREDECESSOR_FROZEN_SOURCE_COMMIT_ID:
                assert set(requested) == self.frozen_paths
            else:
                raise AssertionError(arguments)
            return "".join(
                f"100644 blob {self.facts[relative]['git_blob_id']}\t"
                f"{relative}\n"
                for relative in sorted(requested)
            ).encode("utf-8")
        if arguments[:2] == ("cat-file", "blob"):
            blob_id = arguments[2]
            return next(
                raw
                for relative, raw in self.blobs.items()
                if self.facts[relative]["git_blob_id"] == blob_id
            )
        raise AssertionError(arguments)


class FakeAbsenceObserver:
    def __init__(self, *, fail_after: int | None = None) -> None:
        self.calls = 0
        self.fail_after = fail_after

    def observe_absence(self, authority, *, deadline_ns: int):
        assert type(deadline_ns) is int and deadline_ns > 0
        self.calls += 1
        if self.fail_after == self.calls:
            raise OSError(errno.ETIMEDOUT, "fixture residual")
        host = authority["host_parent_fact"]
        systemctl_argv = probe._systemctl_absence_argv()
        contract = probe.build_target_lifecycle_contract(os.geteuid())
        show_argv = tuple(contract["absence_show_argv"])
        properties = FakeRuntime._manager_absent_properties()
        show_raw = FakeRuntime._property_raw(
            properties, probe.TARGET_MANAGER_ABSENCE_PROPERTIES
        )
        return {
            "unit_absent": True,
            "target_absent": True,
            "source_unit_absent": True,
            "source_path_absent": True,
            "target_transient_instance_implicit_absence": True,
            "target_path_absent": True,
            "target_manager_implicit_absence": True,
            "target_manager_properties": properties,
            "target_manager_show_argv": list(show_argv),
            "target_manager_show_result": probe._bounded_process_result_fact(
                probe.BoundedProcessResult(
                    show_argv, 0, show_raw, b"", False, False
                )
            ),
            "transient_fragment_path": contract["transient_fragment_path"],
            "transient_fragment_absent": True,
            "transient_fragment_stat_errno": errno.ENOENT,
            "parent_absence_observation": {
                "app_slice_path": host["app_slice_path"],
                "app_slice_named_device": host["app_slice_device"],
                "app_slice_named_inode": host["app_slice_inode"],
                "app_slice_opened_device": host["app_slice_device"],
                "app_slice_opened_inode": host["app_slice_inode"],
                "app_slice_mode": host["mode"],
                "app_slice_owner_uid": host["owner_uid"],
                "app_slice_owner_gid": host["owner_gid"],
                "app_slice_fstatfs_type": probe.CGROUP2_SUPER_MAGIC,
                "source_stat_errno": errno.ENOENT,
                "target_parent_observation": (
                    FakeRuntime._parent_absent_observation()
                ),
            },
            "named_path_detached_and_manager_implicit_absence": True,
            "posix_inode_unlink_claimed": False,
            "poll_count": 1,
            "systemctl_argv": list(systemctl_argv),
            "systemctl_result": probe._bounded_process_result_fact(
                probe.BoundedProcessResult(
                    systemctl_argv, 0, b"", b"", False, False
                )
            ),
            "source_path": str(probe._source_absence_path(authority)),
            "target_path": str(probe._target_absence_path(authority)),
        }


class FakeLaunchProcess:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.calls: list[dict[str, object]] = []

    def run(
        self,
        argv,
        *,
        timeout_seconds: int,
        stdout_cap: int,
        stderr_cap: int,
        env=None,
        start_new_session: bool = False,
    ):
        self.calls.append(
            {
                "argv": tuple(argv),
                "timeout_seconds": timeout_seconds,
                "stdout_cap": stdout_cap,
                "stderr_cap": stderr_cap,
                "env": env,
                "start_new_session": start_new_session,
            }
        )
        return self.callback(tuple(argv))


def test_outer_absence_observer_proves_source_and_target_implicit_detach(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _raw, _environment = _authority(tmp_path)

    class Process:
        def run(
            self,
            argv,
            *,
            timeout_seconds,
            stdout_cap,
            stderr_cap,
            env=None,
            start_new_session=False,
        ):
            assert start_new_session is False
            actual = tuple(argv)
            if actual == probe._systemctl_absence_argv():
                stdout = b""
            else:
                contract = probe.build_target_lifecycle_contract(os.geteuid())
                assert actual == tuple(contract["absence_show_argv"])
                stdout = FakeRuntime._property_raw(
                    FakeRuntime._manager_absent_properties(),
                    probe.TARGET_MANAGER_ABSENCE_PROPERTIES,
                )
            return probe.BoundedProcessResult(
                actual, 0, stdout, b"", False, False
            )

    synthetic = FakeAbsenceObserver().observe_absence(
        authority, deadline_ns=10**30
    )
    monkeypatch.setattr(
        probe,
        "_observe_outer_parent_absence",
        lambda _authority: synthetic["parent_absence_observation"],
    )
    monkeypatch.setattr(
        probe,
        "_observe_fragment_absence",
        lambda path: {"path": path, "stat_errno": errno.ENOENT, "absent": True},
    )
    observed = probe.SystemdCgroupAbsenceObserver(Process()).observe_absence(
        authority, deadline_ns=10**30
    )
    assert set(observed) == probe.ABSENCE_FACT_FIELDS
    assert observed["unit_absent"] is True
    assert observed["target_absent"] is True
    assert observed["source_unit_absent"] is True
    assert observed["source_path_absent"] is True
    assert observed["target_transient_instance_implicit_absence"] is True
    assert observed["target_path_absent"] is True
    assert observed["target_manager_implicit_absence"] is True
    assert observed["transient_fragment_absent"] is True
    assert observed["named_path_detached_and_manager_implicit_absence"] is True
    assert observed["posix_inode_unlink_claimed"] is False
    assert probe._validate_success_absence_fact(observed, authority) == observed
    for mutate in (
        lambda value: value["target_manager_properties"].update(
            {"ControlGroup": "/foreign"}
        ),
        lambda value: value.update(
            {"transient_fragment_path": "/run/user/1000/foreign.slice"}
        ),
        lambda value: value["parent_absence_observation"].update(
            {"app_slice_opened_inode": 999999}
        ),
    ):
        tampered = json.loads(json.dumps(observed))
        mutate(tampered)
        with pytest.raises(probe.AuthorityError):
            probe._validate_success_absence_fact(tampered, authority)


class FakeMonotonicClock:
    def __init__(self, now_ns: int = 1_000_000_000) -> None:
        self.now_ns = now_ns

    def read(self) -> int:
        return self.now_ns

    def advance_seconds(self, seconds: int) -> None:
        self.now_ns += seconds * 1_000_000_000


def _successful_inner_callback(
    authority: dict[str, object],
    external_root_raw: bytes,
    environment: dict[str, str],
    store: probe.DurableArtifactStore,
):
    def launch(argv):
        receipt = probe.run_probe_once(
            authority=authority,
            external_root_raw=external_root_raw,
            store=store,
            runtime=FakeRuntime(),
            environ=environment,
            monotonic_ns=lambda: 1_000_000,
        )
        return probe.BoundedProcessResult(
            argv,
            0,
            probe.canonical_json_bytes(receipt) + b"\n",
            b"",
            False,
            False,
        )

    return launch


def _reidentified_outer_failure_raw(failure, mutate) -> bytes:
    payload = json.loads(json.dumps(failure))
    payload.pop("outer_launch_failure_id")
    mutate(payload)
    return probe.canonical_json_bytes(
        probe._self_id_document(
            probe.OUTER_LAUNCH_FAILURE_DOMAIN,
            "outer_launch_failure_id",
            payload,
        )
    )


def _inject_outer_failure_read(
    store: probe.DurableArtifactStore,
    monkeypatch: pytest.MonkeyPatch,
    forged_raw: bytes,
) -> None:
    original_read = store.read_exact

    def read_exact(name: str, *, allow_empty: bool = False):
        if name == probe.OUTER_LAUNCH_FAILURE_NAME:
            return forged_raw
        return original_read(name, allow_empty=allow_empty)

    monkeypatch.setattr(store, "read_exact", read_exact)


def _materialize_committed_fixture(repository_root: Path) -> FakeGit:
    blobs = {
        probe.PROBE_SOURCE_RELATIVE_PATH: b"committed probe fixture\n",
        probe.PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH: PREDECESSOR_PROBE_RAW,
        **{
            spec["relative_path"]: (
                ROOT / spec["relative_path"]
            ).read_bytes()
            for spec in probe.PREDECESSOR_TERMINAL_ARTIFACT_SPECS
        },
    }
    for relative, raw in blobs.items():
        path = repository_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return FakeGit(blobs)


def test_token_names_and_domains_are_version_specific_full64_ordinal_two() -> None:
    policy = probe.build_same_uid_manager_concurrency_policy()
    policy_id = policy["same_uid_manager_concurrency_policy_id"]
    assert probe.validate_same_uid_manager_concurrency_policy(policy) == policy
    assert policy["status"] == "UNVERIFIED_THREAT_MODEL_EXCLUSION"
    assert policy["unconditional_same_uid_replacement_safety_claimed"] is False
    lineage = probe.preflight_lineage()
    assert set(lineage) == probe.LINEAGE_FIELDS
    assert probe.derive_preflight_token(lineage) == probe.PREFLIGHT_TOKEN
    assert len(probe.PREFLIGHT_TOKEN) == 64
    assert lineage["ordinal"] == 2
    assert lineage["same_uid_manager_concurrency_policy_id"] == policy_id
    assert probe.SERVICE_UNIT_NAME == (
        f"acfqp-v180r12r4r2-preflight-{probe.PREFLIGHT_TOKEN}.service"
    )
    assert probe.SERVICE_UNIT_NAME.endswith(".service")
    target_lineage = probe.target_lineage()
    assert set(target_lineage) == probe.TARGET_LINEAGE_FIELDS
    assert target_lineage["purpose"] == "PREFLIGHT_TARGET"
    assert target_lineage["ordinal"] == 2
    assert target_lineage["same_uid_manager_concurrency_policy_id"] == policy_id
    assert probe.derive_target_token(target_lineage) == probe.TARGET_TOKEN
    assert len(probe.TARGET_TOKEN) == 64
    assert probe.TARGET_SERVICE_UNIT_NAME == (
        f"app-acfqpv180r12r4r2target{probe.TARGET_TOKEN}.slice"
    )
    assert probe.TARGET_CGROUP_NAME == probe.TARGET_SERVICE_UNIT_NAME
    assert probe.TARGET_TOKEN != probe.PREFLIGHT_TOKEN
    domains = [
        value
        for name, value in vars(probe).items()
        if name.endswith("_DOMAIN") and isinstance(value, str)
    ]
    assert domains
    assert all("v180r12r4r2" in value for value in domains)
    assert all(
        name.startswith(
            "v180r12r4r2_atomic_birth_readiness_PREFLIGHT_ordinal-2_PREPARE_"
        )
        for name in probe.PREPARE_JOURNAL_NAMES
    )
    assert len(probe.PREPARE_JOURNAL_NAMES) == 3
    assert probe.prepare_journal_relative_paths() == {
        "attempt": f".tmp/exact-freeze/{probe.PREPARE_ATTEMPT_NAME}",
        "failure": f".tmp/exact-freeze/{probe.PREPARE_FAILURE_NAME}",
        "receipt": f".tmp/exact-freeze/{probe.PREPARE_RECEIPT_NAME}",
    }
    with pytest.raises(probe.AuthorityError):
        probe.derive_preflight_token({**lineage, "r4_protocol_id": "0" * 64})
    forged_lineage = {
        **lineage,
        "same_uid_manager_concurrency_policy_id": "0" * 64,
    }
    assert probe._domain_id(probe.TOKEN_DOMAIN, forged_lineage) != (
        probe.PREFLIGHT_TOKEN
    )
    with pytest.raises(probe.AuthorityError):
        probe.derive_preflight_token(forged_lineage)


def test_target_manager_contract_is_exact_no_shell_and_manager_owned() -> None:
    uid = os.geteuid()
    contract = probe.build_target_lifecycle_contract(uid)
    assert set(contract) == probe.TARGET_LIFECYCLE_FIELDS
    assert contract == probe.validate_target_lifecycle_contract(contract, uid=uid)
    assert contract["purpose"] == "PREFLIGHT_TARGET"
    assert contract["ordinal"] == 2
    assert contract["target_token"] == probe.TARGET_TOKEN
    assert contract["unit_name"] == probe.TARGET_SERVICE_UNIT_NAME
    assert contract["cgroup_name"] == probe.TARGET_CGROUP_NAME
    assert contract["unit_type"] == "slice"
    assert contract["direct_child_of_app_slice"] is True
    assert contract["transient"] is True
    assert contract["delegate"] is False
    assert contract["collect_mode"] == "inactive-or-failed"
    assert contract["lifecycle_authority"] == "SYSTEMD_USER_MANAGER_ONLY"
    policy = probe.build_same_uid_manager_concurrency_policy()
    assert contract["same_uid_manager_concurrency_policy_id"] == policy[
        "same_uid_manager_concurrency_policy_id"
    ]
    assert contract["same_uid_manager_concurrency_policy_status"] == policy[
        "status"
    ]
    assert contract["unconditional_same_uid_replacement_safety_claimed"] is False
    assert contract["manager_stop_identity_binding_contract"] == (
        probe.MANAGER_STOP_IDENTITY_BINDING
    )
    for field, value in (
        ("same_uid_manager_concurrency_policy_status", "VERIFIED"),
        ("unconditional_same_uid_replacement_safety_claimed", True),
        ("manager_stop_identity_binding_contract", "ATOMIC_BY_INODE"),
    ):
        with pytest.raises(probe.AuthorityError):
            probe.validate_target_lifecycle_contract(
                {**contract, field: value}, uid=uid
            )
    assert contract["create_argv"] == [
        "/usr/bin/busctl",
        "--user",
        "--no-pager",
        f"--timeout={probe.TARGET_MANAGER_CALL_TIMEOUT_SECONDS}s",
        "--allow-interactive-authorization=no",
        "call",
        "org.freedesktop.systemd1",
        "/org/freedesktop/systemd1",
        "org.freedesktop.systemd1.Manager",
        "StartTransientUnit",
        "ssa(sv)a(sa(sv))",
        probe.TARGET_SERVICE_UNIT_NAME,
        "fail",
        "4",
        "Description",
        "s",
        probe.TARGET_DESCRIPTION,
        "CollectMode",
        "s",
        "inactive-or-failed",
        "BindsTo",
        "as",
        "1",
        probe.SERVICE_UNIT_NAME,
        "After",
        "as",
        "1",
        probe.SERVICE_UNIT_NAME,
        "0",
    ]
    assert contract["binds_to_unit"] == probe.SERVICE_UNIT_NAME
    assert contract["after_unit"] == probe.SERVICE_UNIT_NAME
    assert contract["transient_fragment_path"].endswith(
        "/systemd/transient/" + probe.TARGET_SERVICE_UNIT_NAME
    )
    assert contract["absence_show_argv"][-1] == probe.TARGET_SERVICE_UNIT_NAME
    assert contract["active_show_argv"][-1] == probe.TARGET_SERVICE_UNIT_NAME
    assert contract["stop_argv"] == [
        "/usr/bin/systemctl",
        "--user",
        "--no-block",
        "--no-ask-password",
        "stop",
        probe.TARGET_SERVICE_UNIT_NAME,
    ]
    assert contract["environment"] == probe.expected_outer_launch_environment(uid)
    assert "--scope" not in contract["create_argv"]
    assert probe.SYSTEMD_RUN not in contract["create_argv"]
    assert contract["create_argv"][-1] == "0"
    tampered = json.loads(json.dumps(contract))
    tampered["create_argv"].insert(2, "--scope")
    with pytest.raises(probe.AuthorityError):
        probe.validate_target_lifecycle_contract(tampered, uid=uid)


def test_target_manager_active_replay_locks_direct_transient_slice() -> None:
    contract = probe.build_target_lifecycle_contract(os.geteuid())
    properties = {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "active",
        "ControlGroup": f"/fixture/{probe.TARGET_CGROUP_NAME}",
        "BindsTo": probe.SERVICE_UNIT_NAME,
        "After": f"app.slice {probe.SERVICE_UNIT_NAME}",
        "Delegate": "no",
        "CollectMode": "inactive-or-failed",
        "Slice": "app.slice",
        "Transient": "yes",
        "FragmentPath": contract["transient_fragment_path"],
        "UnitFileState": "transient",
        "Job": "",
    }
    assert probe._target_manager_active(
        properties,
        expected_control_group=f"/fixture/{probe.TARGET_CGROUP_NAME}",
    ).conformant
    for field, replacement in (
        ("BindsTo", "foreign.service"),
        ("After", "basic.target"),
        ("SubState", "exited"),
        ("Delegate", "yes"),
        ("CollectMode", "inactive"),
        ("Slice", "foreign.slice"),
        ("Transient", "no"),
        ("FragmentPath", "/run/user/1000/systemd/transient/foreign.slice"),
        ("UnitFileState", "disabled"),
        ("Job", "/org/freedesktop/systemd1/job/7"),
    ):
        mutated = dict(properties)
        mutated[field] = replacement
        assert not probe._target_manager_active(
            mutated,
            expected_control_group=f"/fixture/{probe.TARGET_CGROUP_NAME}",
        ).conformant


def test_six_binary_toolchain_facts_pin_requested_links_and_resolved_files() -> None:
    facts = json.loads(json.dumps(TOOLCHAIN_FIXTURE_FACTS))
    assert [row["path"] for row in facts] == list(
        probe.TOOLCHAIN_EXECUTABLE_PATHS
    )
    assert len(facts) == 6
    assert probe.validate_toolchain_facts(facts) == facts
    for fact in facts:
        assert set(fact) == probe.TOOLCHAIN_EXECUTABLE_FIELDS
        assert fact["requested_kind"] in {"REGULAR", "SYMLINK"}
        assert Path(fact["resolved_path"]).is_absolute()
        assert fact["resolved_path"].startswith("/usr/bin/")
        assert stat.S_IMODE(fact["mode"]) & 0o111
        assert fact["byte_count"] > 0
        assert len(fact["sha256"]) == 64
    assert facts[0] == probe.observe_toolchain_executable_fact(probe.GIT_BINARY)
    tampered = json.loads(json.dumps(facts))
    tampered[-1]["sha256"] = "0" * 64
    with pytest.raises(probe.AuthorityError):
        probe.validate_live_toolchain_facts(tampered)


def test_probe_source_is_zero_freeze_neutral() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "FROZEN_C_PRE_COMMIT" not in source
    assert "EXPECTED_SOURCE_SHA256" not in source
    assert "EXPECTED_GIT_BLOB_ID" not in source
    assert "SOURCE_PIN_LITERAL" not in source
    assert "c_probe_commit_id" in source
    assert "c_probe_tree_id" in source
    assert "probe_source_fact" in source


def test_external_root_is_exact_post_commit_authority(tmp_path: Path) -> None:
    authority, raw, _environment = _authority(tmp_path)
    assert set(authority) == probe.EXTERNAL_ROOT_FIELDS
    assert len(probe.EXTERNAL_ROOT_FIELDS) == 21
    assert probe.loads_canonical_json(raw) == authority
    assert probe.validate_external_root_document(authority) == authority
    assert authority["preflight_token"] == probe.PREFLIGHT_TOKEN
    policy = probe.build_same_uid_manager_concurrency_policy()
    assert authority["same_uid_manager_concurrency_policy"] == policy
    assert authority["same_uid_manager_concurrency_policy_id"] == policy[
        "same_uid_manager_concurrency_policy_id"
    ]
    assert policy["status"] == "UNVERIFIED_THREAT_MODEL_EXCLUSION"
    assert policy["unconditional_same_uid_replacement_safety_claimed"] is False
    assert authority["predecessor_inner_failure_id"] == (
        probe.PREDECESSOR_INNER_FAILURE_ID
    )
    assert authority["predecessor_outer_launch_failure_id"] == (
        probe.PREDECESSOR_OUTER_LAUNCH_FAILURE_ID
    )
    assert authority["predecessor_terminal_artifact_facts"] == (
        PREDECESSOR_ARTIFACT_FIXTURE_FACTS
    )
    assert authority["c_probe_commit_id"] == "c" * 40
    assert authority["c_probe_tree_id"] == "d" * 40


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("status", "VERIFIED_THREAT_MODEL_GUARANTEE"),
        ("unconditional_same_uid_replacement_safety_claimed", True),
    ),
)
def test_reidentified_policy_upgrade_is_rejected_before_live_prepare_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    authority, _raw, _environment = _authority(tmp_path)
    policy_payload = dict(authority["same_uid_manager_concurrency_policy"])
    policy_payload.pop("same_uid_manager_concurrency_policy_id")
    policy_payload[field] = value
    forged_policy = probe._self_id_document(
        probe.SAME_UID_MANAGER_CONCURRENCY_POLICY_DOMAIN,
        "same_uid_manager_concurrency_policy_id",
        policy_payload,
    )
    authority_payload = json.loads(json.dumps(authority))
    authority_payload.pop("external_root_id")
    authority_payload["same_uid_manager_concurrency_policy"] = forged_policy
    authority_payload["same_uid_manager_concurrency_policy_id"] = forged_policy[
        "same_uid_manager_concurrency_policy_id"
    ]
    forged_authority = probe._self_id_document(
        probe.EXTERNAL_ROOT_DOMAIN, "external_root_id", authority_payload
    )
    forged_raw = probe.canonical_json_bytes(forged_authority)
    live_called = False

    def forbidden_live_check(_facts) -> None:
        nonlocal live_called
        live_called = True
        pytest.fail("policy tamper reached live toolchain observation")

    monkeypatch.setattr(
        probe, "validate_live_toolchain_facts", forbidden_live_check
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_prepared_authority(forged_authority, forged_raw)
    assert live_called is False


def test_c_probe_commit_tree_and_both_blob_rows_are_verified_without_live_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    invocation = probe.build_systemd_invocation_contract(
        repository_root=tmp_path,
        external_root_path=tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH,
        artifact_root=tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH,
    )
    authority = probe.build_external_root_document(
        c_probe_commit_id=fake_git.commit_id,
        c_probe_tree_id=fake_git.tree_id,
        probe_source_fact=fake_git.facts[probe.PROBE_SOURCE_RELATIVE_PATH],
        predecessor_probe_source_fact=fake_git.facts[
            probe.PREDECESSOR_PROBE_SOURCE_RELATIVE_PATH
        ],
        predecessor_terminal_artifact_facts=(
            probe.observe_predecessor_terminal_artifact_facts(tmp_path)
        ),
        host_parent_fact=_host_parent_fact(),
        systemd_invocation_contract=invocation,
    )
    monkeypatch.setattr(probe, "_git_stdout", fake_git)
    probe._validate_c_probe_git_authority(tmp_path, authority)


def test_systemd_run_command_is_exact_service_delegate_and_clean_env(
    tmp_path: Path,
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    digest = hashlib.sha256(raw).hexdigest()
    invocation = authority["systemd_invocation_contract"]
    argv = probe.build_systemd_run_command(
        invocation, external_root_sha256=digest
    )
    assert argv[0] == "/usr/bin/systemd-run"
    assert "--quiet" in argv
    assert "--scope" not in argv
    assert "--service-type=exec" in argv
    assert "--property=Delegate=yes" in argv
    assert "--property=UMask=0077" in argv
    assert "--property=Delegate=false" not in argv
    assert f"--unit={probe.SERVICE_UNIT_NAME}" in argv
    assert "--slice=app.slice" in argv
    assert invocation["outer_launch_environment"] == (
        probe.expected_outer_launch_environment(os.geteuid())
    )
    assert invocation["prepare_journal_relative_paths"] == (
        probe.prepare_journal_relative_paths()
    )
    env_index = argv.index("/usr/bin/env")
    python_index = argv.index("/usr/bin/python3")
    assert argv[env_index + 1] == "-i"
    assignments = argv[env_index + 2 : python_index]
    assert len(assignments) == len(probe.STATIC_CLEAN_ENVIRONMENT) + 2
    assert (
        f"{probe.EXTERNAL_ROOT_SHA256_ENV}={digest}" in assignments
    )
    assert probe.validate_systemd_run_command(
        argv, invocation, external_root_sha256=digest
    ) == argv


@pytest.mark.parametrize("drift", ["scope", "delegate", "umask", "environment"])
def test_systemd_run_validator_rejects_scope_delegate_false_and_env_drift(
    tmp_path: Path, drift: str
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    digest = hashlib.sha256(raw).hexdigest()
    invocation = authority["systemd_invocation_contract"]
    argv = list(
        probe.build_systemd_run_command(invocation, external_root_sha256=digest)
    )
    if drift == "scope":
        argv.insert(1, "--scope")
    elif drift == "delegate":
        index = argv.index("--property=Delegate=yes")
        argv[index] = "--property=Delegate=false"
    elif drift == "umask":
        index = argv.index("--property=UMask=0077")
        argv[index] = "--property=UMask=0022"
    else:
        index = next(
            index
            for index, item in enumerate(argv)
            if item.startswith("LC_ALL=")
        )
        argv[index] = "LC_ALL=C"
    with pytest.raises(probe.AuthorityError):
        probe.validate_systemd_run_command(
            argv, invocation, external_root_sha256=digest
        )


def test_external_root_loader_requires_canonical_0400_path_sha_and_clean_env(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    external = tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH
    external.parent.mkdir(parents=True, exist_ok=True)
    external.write_bytes(raw)
    external.chmod(0o400)
    loaded, loaded_raw = probe.load_external_root_from_clean_environment(
        environment, validate_live_sources=False
    )
    assert loaded == authority
    assert loaded_raw == raw
    dirty = {**environment, "HOME": "/tmp"}
    with pytest.raises(probe.AuthorityError):
        probe.load_external_root_from_clean_environment(
            dirty, validate_live_sources=False
        )
    wrong_sha = dict(environment)
    wrong_sha[probe.EXTERNAL_ROOT_SHA256_ENV] = "0" * 64
    with pytest.raises(probe.AuthorityError):
        probe.load_external_root_from_clean_environment(
            wrong_sha, validate_live_sources=False
        )


def test_external_root_loader_rejects_hardlink_and_noncanonical_bytes(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    external = tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH
    external.parent.mkdir(parents=True, exist_ok=True)
    external.write_bytes(raw)
    external.chmod(0o400)
    hardlink = external.with_name("external-root-hardlink.json")
    os.link(external, hardlink)
    with pytest.raises(probe.AuthorityError):
        probe.load_external_root_from_clean_environment(
            environment, validate_live_sources=False
        )
    hardlink.unlink()
    external.chmod(0o600)
    external.write_bytes(json.dumps(authority, indent=2).encode("utf-8"))
    external.chmod(0o400)
    noncanonical_environment = probe.expected_clean_environment(
        str(external), hashlib.sha256(external.read_bytes()).hexdigest()
    )
    with pytest.raises(probe.AuthorityError):
        probe.load_external_root_from_clean_environment(
            noncanonical_environment, validate_live_sources=False
        )


def test_durable_store_emits_canonical_0400_o_excl_files(tmp_path: Path) -> None:
    authority, raw, _environment = _authority(tmp_path)
    attempt = probe.build_attempt_document(authority, raw)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        probe.claim_attempt(store, attempt)
        retained = store.root / probe.ATTEMPT_NAME
        assert stat.S_IMODE(retained.stat().st_mode) == 0o400
        assert retained.stat().st_nlink == 1
        assert retained.read_bytes() == probe.canonical_json_bytes(attempt)
        with pytest.raises(probe.ReplayForbidden):
            probe.claim_attempt(store, attempt)


def test_fixture_success_proves_sibling_shape_pidfd_exit_and_absence(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    runtime = FakeRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        receipt = probe.run_probe_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            runtime=runtime,
            environ=environment,
            monotonic_ns=lambda: 1_000_000,
        )
        assert receipt["nearest_common_ancestor_is_app_slice"] is True
        assert receipt["app_slice_cgroup_procs_write_required"] is True
        assert receipt["child_handshake_complete"] is True
        assert receipt["pidfd_identity_complete"] is True
        assert receipt["child_exit_zero"] is True
        assert receipt["target_absent"] is True
        assert (store.root / probe.ATTEMPT_NAME).exists()
        assert (store.root / probe.RECEIPT_NAME).exists()
        assert not (store.root / probe.FAILURE_NAME).exists()
        assert stat.S_IMODE((store.root / probe.RECEIPT_NAME).stat().st_mode) == 0o400
    names = [row["substage"] for row in receipt["substage_records"]]
    assert names == [
        "ATTEMPT_PUBLICATION",
        "OUTER_CONTEXT",
        "SERVICE_PLACEMENT_AND_NCA_PERMISSION",
        "TARGET_CREATE",
        "CLONE3_ATOMIC_BIRTH",
        "CHILD_HANDSHAKE",
        "PIDFD_AND_MEMBERSHIP",
        "HANDSHAKE_MEMBERSHIP_CONSISTENCY",
        "CHILD_RELEASE",
        "CHILD_EXIT_ZERO",
        "CHILD_HANDLE_CLOSE",
        "TARGET_EMPTY",
        "TARGET_REMOVE",
        "TARGET_ABSENT",
        "SERVICE_HANDLE_CLOSE",
    ]
    service_row = receipt["substage_records"][2]["detail"]
    assert service_row["source_membership"].endswith(
        f"/{probe.SERVICE_UNIT_NAME}"
    )
    assert service_row["target_membership"].endswith(
        f"/app.slice/{probe.TARGET_CGROUP_NAME}"
    )
    assert service_row["nearest_common_ancestor"].endswith("/app.slice")
    assert service_row["app_slice_cgroup_procs_write"]["opened_for_write"] is True


def test_direct_inner_entry_replays_six_toolchain_before_attempt_o_excl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    order: list[str] = []

    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)

        def replay_toolchain(expected) -> None:
            assert len(expected) == 6
            assert store.inventory_names(phase="TOOLCHAIN_BEFORE_ATTEMPT") == {
                probe.OUTER_LAUNCH_ATTEMPT_NAME
            }
            order.append("toolchain")

        monkeypatch.setattr(probe, "validate_live_toolchain_facts", replay_toolchain)

        class OrderedRuntime(FakeRuntime):
            def inspect_service(self, authority_value, deadline_ns: int):
                assert (store.root / probe.ATTEMPT_NAME).exists()
                order.append("runtime")
                return super().inspect_service(authority_value, deadline_ns)

        probe.run_probe_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            runtime=OrderedRuntime(),
            environ=environment,
            monotonic_ns=lambda: 1_000_000,
        )
    assert order == ["toolchain", "runtime"]


@pytest.mark.parametrize(
    ("method", "failed_substage"),
    [
        ("inspect_service", "SERVICE_PLACEMENT_AND_NCA_PERMISSION"),
        ("create_target", "TARGET_CREATE"),
        ("clone_child", "CLONE3_ATOMIC_BIRTH"),
        ("receive_handshake", "CHILD_HANDSHAKE"),
        ("inspect_child", "PIDFD_AND_MEMBERSHIP"),
        ("release_child", "CHILD_RELEASE"),
        ("reap_exit_zero", "CHILD_EXIT_ZERO"),
        ("target_empty", "TARGET_EMPTY"),
    ],
)
def test_each_runtime_failure_is_typed_with_errno_and_bounded_cleanup(
    tmp_path: Path, method: str, failed_substage: str
) -> None:
    authority, raw, environment = _authority(tmp_path)
    runtime = FakeRuntime(fail_method=method)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        failure = raised.value.failure_document
        assert failure["failed_substage"] == failed_substage
        assert failure["errno"] == errno.EACCES
        assert failure["errno_name"] == "EACCES"
        assert failure["scientific_occurrence_started"] is False
        assert failure["campaign_actual_measurement"] is False
        assert (store.root / probe.ATTEMPT_NAME).exists()
        assert (store.root / probe.FAILURE_NAME).exists()
        assert not (store.root / probe.RECEIPT_NAME).exists()
        assert stat.S_IMODE((store.root / probe.FAILURE_NAME).stat().st_mode) == 0o400
    failed_rows = [
        row for row in failure["substage_records"] if row["status"] == "FAILED"
    ]
    assert failed_rows
    assert failed_rows[0]["substage"] == failed_substage
    assert failed_rows[0]["errno"] == errno.EACCES


@pytest.mark.parametrize(
    "failure_stage",
    [
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_CLOSE",
        "AFTER_ROOT_FSYNC",
        "AFTER_READBACK",
    ],
)
def test_inner_exact_failure_is_stabilized_before_exact_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    failure_checkpoint_hits = 0

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        nonlocal failure_checkpoint_hits
        if name == probe.FAILURE_NAME and stage == failure_stage:
            failure_checkpoint_hits += 1
            raise OSError(errno.EIO, "fixture exact inner failure")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_outer_attempt(store, authority, raw)
        original_stabilize = store.stabilize_exact
        stabilized: list[tuple[str, bytes]] = []

        def record_stabilization(name: str, artifact_raw: bytes) -> None:
            stabilized.append((name, artifact_raw))
            original_stabilize(name, artifact_raw)

        monkeypatch.setattr(store, "stabilize_exact", record_stabilization)
        with pytest.raises(probe.DurableWriteError):
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(fail_method="inspect_service"),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        failure_raw = store.read_exact(probe.FAILURE_NAME)
        observation, observed_raw = probe.observe_inner_launch_state(
            store, authority, raw
        )
        assert observation["state"] == "FAILURE"
        assert observed_raw == failure_raw
        assert stabilized == [(probe.FAILURE_NAME, failure_raw)]
        assert failure_checkpoint_hits == 1


def test_inner_failure_postreturn_interrupt_is_stabilized_before_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        original_write = store.write_once
        original_stabilize = store.stabilize_exact
        stabilized: list[tuple[str, bytes]] = []

        def write_then_interrupt(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )
            if name == probe.FAILURE_NAME:
                raise KeyboardInterrupt("fixture inner failure post-return")

        def record_stabilization(name: str, artifact_raw: bytes) -> None:
            stabilized.append((name, artifact_raw))
            original_stabilize(name, artifact_raw)

        monkeypatch.setattr(store, "write_once", write_then_interrupt)
        monkeypatch.setattr(store, "stabilize_exact", record_stabilization)
        with pytest.raises(KeyboardInterrupt):
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(fail_method="inspect_service"),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        failure_raw = store.read_exact(probe.FAILURE_NAME)
        observation, observed_raw = probe.observe_inner_launch_state(
            store, authority, raw
        )
        assert observation["state"] == "FAILURE"
        assert observed_raw == failure_raw
        assert stabilized == [(probe.FAILURE_NAME, failure_raw)]


def test_inner_failure_stabilization_error_is_closed_by_outer_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.FAILURE_NAME and stage == "AFTER_FULL_WRITE":
            raise OSError(errno.EIO, "fixture exact inner failure")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_stabilize = store.stabilize_exact

        def reject_inner_failure_stabilization(
            name: str, artifact_raw: bytes
        ) -> None:
            if name == probe.FAILURE_NAME:
                raise OSError(errno.EIO, "fixture inner failure fsync")
            original_stabilize(name, artifact_raw)

        monkeypatch.setattr(
            store, "stabilize_exact", reject_inner_failure_stabilization
        )

        def launch_callback(argv):
            with pytest.raises(probe.DurableWriteError):
                probe.run_probe_once(
                    authority=authority,
                    external_root_raw=raw,
                    store=store,
                    runtime=FakeRuntime(fail_method="inspect_service"),
                    environ=environment,
                    monotonic_ns=lambda: 1_000_000,
                )
            return probe.BoundedProcessResult(
                argv, 2, b"", b"", False, False
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["inner_observation"] is None
        assert "INNER_OBSERVATION_ERROR" in failure["failure_reason"]

        monkeypatch.setattr(store, "stabilize_exact", original_stabilize)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("outer failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert replayed.value.failure_document == failure
        assert no_relaunch.calls == []


def test_inner_partial_failure_is_closed_by_same_outer_failure_on_replay(
    tmp_path: Path
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.FAILURE_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial inner failure")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)

        def launch_callback(argv):
            with pytest.raises(probe.DurableWriteError):
                probe.run_probe_once(
                    authority=authority,
                    external_root_raw=raw,
                    store=store,
                    runtime=FakeRuntime(fail_method="inspect_service"),
                    environ=environment,
                    monotonic_ns=lambda: 1_000_000,
                )
            return probe.BoundedProcessResult(
                argv, 2, b"", b"", False, False
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        inner = failure["inner_observation"]
        assert inner["state"] == "FAILURE_PARTIAL"
        assert inner["inner_terminal_id"] is None
        assert store.read_exact(probe.FAILURE_NAME, allow_empty=True) == b"{"

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("outer failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert replayed.value.failure_document == failure
        assert no_relaunch.calls == []


def test_membership_disagreement_is_its_own_structured_substage(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    runtime = FakeRuntime(handshake_membership_drift=True)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "HANDSHAKE_MEMBERSHIP_CONSISTENCY"
    assert failure["errno"] == errno.EXDEV
    assert failure["child_reaped"] is True
    assert failure["target_absent"] is True


def test_cleanup_failure_is_retained_and_never_claimed_as_absence(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    runtime = FakeRuntime(
        fail_method="receive_handshake",
        cleanup_failures=frozenset({"remove_target", "target_absent"}),
    )
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "CHILD_HANDSHAKE"
    assert failure["child_reaped"] is True
    assert failure["target_absent"] is False
    assert failure["target_may_remain"] is True
    cleanup_failures = [
        row
        for row in failure["substage_records"]
        if row["substage"].startswith("CLEANUP_") and row["status"] == "FAILED"
    ]
    assert {row["substage"] for row in cleanup_failures} == {
        "CLEANUP_TARGET_REMOVE",
        "CLEANUP_TARGET_ABSENT",
    }
    by_name = {row["substage"]: row for row in cleanup_failures}
    assert by_name["CLEANUP_TARGET_REMOVE"]["errno"] == errno.EACCES
    assert by_name["CLEANUP_TARGET_ABSENT"]["errno"] == errno.ESTALE
    assert failure["target_manager_stop_requested"] is True
    assert failure["requested_manager_stop_identity_binding"] == (
        probe.MANAGER_STOP_IDENTITY_BINDING
    )
    assert probe.validate_target_cleanup_diagnostic(
        by_name["CLEANUP_TARGET_REMOVE"]["detail"]
    )["manager_stop_requested"] is True


def test_malformed_cleanup_kill_becomes_failed_row_and_preserves_primary(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class MalformedKillRuntime(FakeRuntime):
        def kill_child(self, _child: probe.ChildHandle):
            self.calls.append("kill_child")
            return {"signal": "BAD"}

    runtime = MalformedKillRuntime(fail_method="receive_handshake")
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
        assert store.exists(probe.FAILURE_NAME)
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "CHILD_HANDSHAKE"
    assert failure["errno"] == errno.EACCES
    kill = next(
        row
        for row in failure["substage_records"]
        if row["substage"] == "CLEANUP_PIDFD_KILL"
    )
    reap = next(
        row
        for row in failure["substage_records"]
        if row["substage"] == "CLEANUP_CHILD_REAP"
    )
    assert kill["status"] == "FAILED"
    assert kill["error_type"] == "AuthorityError"
    assert kill["detail"] == {}
    assert reap["status"] == "OK"
    assert failure["child_reaped"] is True
    assert probe.validate_failure_document(failure, attempt, authority) == failure


@pytest.mark.parametrize("malformed_stage", ["remove", "absence"])
def test_malformed_cleanup_target_evidence_still_publishes_typed_failure(
    tmp_path: Path, malformed_stage: str
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class MalformedTargetCleanupRuntime(FakeRuntime):
        def remove_target(self, service, target, deadline_ns: int):
            if malformed_stage == "remove":
                self.calls.append("remove_target")
                return {"removed": True}
            return super().remove_target(service, target, deadline_ns)

        def target_absent(self, service, target, deadline_ns: int):
            if malformed_stage == "absence":
                self.calls.append("target_absent")
                return {"target_absent": True}
            return super().target_absent(service, target, deadline_ns)

    runtime = MalformedTargetCleanupRuntime(fail_method="receive_handshake")
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        expected_error = (
            probe.AuthorityError
            if malformed_stage == "remove"
            else probe.ProbeRunFailure
        )
        with pytest.raises(expected_error) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        if malformed_stage == "remove":
            assert not store.exists(probe.FAILURE_NAME)
            return
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
        assert store.exists(probe.FAILURE_NAME)
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "CHILD_HANDSHAKE"
    cleanup = next(
        row
        for row in failure["substage_records"]
        if row["substage"]
        == (
            "CLEANUP_TARGET_REMOVE"
            if malformed_stage == "remove"
            else "CLEANUP_TARGET_ABSENT"
        )
    )
    service_close = next(
        row
        for row in failure["substage_records"]
        if row["substage"] == "CLEANUP_SERVICE_CLOSE"
    )
    assert cleanup["status"] == "FAILED"
    assert cleanup["errno"] == errno.EPROTO
    assert cleanup["detail"] == {}
    assert service_close["status"] == "OK"
    assert failure["target_absent"] is False
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_consumed_failure_identity_cannot_rerun_or_overwrite(tmp_path: Path) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure):
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(fail_method="clone_child"),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        retained_attempt = (store.root / probe.ATTEMPT_NAME).read_bytes()
        retained_failure = (store.root / probe.FAILURE_NAME).read_bytes()
        with pytest.raises(probe.ReplayForbidden):
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 2_000_000,
            )
        assert (store.root / probe.ATTEMPT_NAME).read_bytes() == retained_attempt
        assert (store.root / probe.FAILURE_NAME).read_bytes() == retained_failure


def test_external_authority_and_main_reject_before_any_real_adapter(tmp_path: Path) -> None:
    authority, raw, environment = _authority(tmp_path)
    drifted = dict(authority)
    drifted["target_cgroup_name"] = "foreign-target"
    with _artifact_store(tmp_path) as store:
        with pytest.raises(probe.AuthorityError):
            probe.run_probe_once(
                authority=drifted,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
            )
        assert not any(store.exists(name) for name in (
            probe.ATTEMPT_NAME,
            probe.RECEIPT_NAME,
            probe.FAILURE_NAME,
        ))
    assert probe.main([]) == 2
    assert probe.main(["--probe", "--extra"]) == 2


def test_real_membership_formula_is_production_sibling_shape() -> None:
    app, source, target = probe.LinuxRuntimeAdapter._expected_memberships(1000)
    assert source == f"{app}/{probe.SERVICE_UNIT_NAME}"
    assert target == f"{app}/{probe.TARGET_CGROUP_NAME}"
    assert probe._nearest_common_ancestor(source, target) == app
    assert PurePosixPath(source).parent == PurePosixPath(target).parent


def test_prepare_collects_exact_head_but_deliberately_ignores_untracked(
    tmp_path: Path,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    untracked = tmp_path / "r4-untracked-scaffold.txt"
    untracked.write_text("outside authority\n", encoding="utf-8")
    result = probe.prepare_external_root_once(
        tmp_path,
        git_stdout=fake_git,
        host_observer=_host_parent_fact,
        require_running_source=False,
    )
    external = tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH
    artifact_root = tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
    assert result["schema"] == probe.PREPARE_RESULT_SCHEMA
    assert result["tracked_and_index_clean"] is True
    assert result["untracked_files_in_authority"] is False
    assert stat.S_IMODE(external.stat().st_mode) == 0o400
    assert external.stat().st_nlink == 1
    assert stat.S_IMODE(artifact_root.stat().st_mode) == 0o700
    assert list(artifact_root.iterdir()) == []
    parent = artifact_root.parent
    assert {
        path.name for path in parent.iterdir() if path.name in probe.PREPARE_JOURNAL_NAMES
    } == {probe.PREPARE_ATTEMPT_NAME, probe.PREPARE_RECEIPT_NAME}
    assert all(
        stat.S_IMODE((parent / name).stat().st_mode) == 0o400
        for name in (probe.PREPARE_ATTEMPT_NAME, probe.PREPARE_RECEIPT_NAME)
    )
    assert len(fake_git.calls) == probe.PREPARE_GIT_CALL_COUNT
    assert ("status", "--porcelain=v1", "--untracked-files=no") in fake_git.calls
    authority, raw = probe.load_external_root_for_outer(
        tmp_path,
        git_stdout=fake_git,
        host_observer=_host_parent_fact,
        require_running_source=False,
    )
    assert authority["c_probe_commit_id"] == fake_git.commit_id
    assert hashlib.sha256(raw).hexdigest() == result["external_root_sha256"]
    assert untracked.exists()
    with pytest.raises(probe.ReplayForbidden):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )


def test_prepare_rejects_tracked_or_index_drift_before_writes(tmp_path: Path) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    fake_git.dirty = b" M scripts/probe.py\n"
    with pytest.raises(probe.AuthorityError):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert not (tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH).exists()
    assert not (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).exists()


def test_git_rc0_stderr_rejects_before_prepare_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)

    class WarningGitProcess:
        calls = 0

        def run(
            self,
            argv,
            *,
            timeout_seconds,
            stdout_cap,
            stderr_cap,
            env=None,
            start_new_session=False,
        ):
            self.calls += 1
            arguments = tuple(argv[3:])
            stdout = fake_git(tmp_path, arguments)
            return probe.BoundedProcessResult(
                tuple(argv),
                0,
                stdout,
                b"warning: fixture Git authority ambiguity\n",
                False,
                False,
            )

    process = WarningGitProcess()
    monkeypatch.setattr(probe, "DEFAULT_SUBPROCESS_ADAPTER", process)
    with pytest.raises(
        probe.AuthorityError,
        match="fixture Git authority ambiguity",
    ):
        probe.prepare_external_root_once(
            tmp_path,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert process.calls == 1
    assert not (tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH).exists()
    assert not (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).exists()
    prepare_parent = (
        tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
    ).parent
    assert prepare_parent.is_dir()
    assert probe.observe_predecessor_terminal_artifact_facts(tmp_path) == (
        PREDECESSOR_ARTIFACT_FIXTURE_FACTS
    )


def test_prepare_pins_git_before_calls_and_replays_it_with_full_toolchain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    events: list[str] = []
    git_fact = json.loads(json.dumps(TOOLCHAIN_FIXTURE_FACTS[0]))

    def observe_git_executable(path: str):
        assert path == probe.GIT_BINARY
        events.append("GIT_EXECUTABLE_BEFORE")
        return json.loads(json.dumps(git_fact))

    def observe_git(root: Path, arguments) -> bytes:
        events.append("GIT_CALL")
        return fake_git(root, arguments)

    def observe_host():
        events.append("HOST_AND_TOOLCHAIN_AFTER")
        return _host_parent_fact()

    monkeypatch.setattr(
        probe,
        "observe_toolchain_executable_fact",
        observe_git_executable,
    )
    authority = probe.collect_post_c_probe_authority(
        tmp_path,
        git_stdout=observe_git,
        host_observer=observe_host,
        require_running_source=False,
    )
    assert events == [
        "GIT_EXECUTABLE_BEFORE",
        *("GIT_CALL" for _ in range(probe.PREPARE_GIT_CALL_COUNT)),
        "HOST_AND_TOOLCHAIN_AFTER",
    ]
    assert authority["host_parent_fact"]["toolchain_facts"][0] == git_fact

    bad_host = _host_parent_fact()
    bad_host["toolchain_facts"][0]["sha256"] = "0" * 64
    with pytest.raises(
        probe.AuthorityError,
        match="Git executable changed across prepare authority collection",
    ):
        probe.collect_post_c_probe_authority(
            tmp_path,
            git_stdout=fake_git,
            host_observer=lambda: bad_host,
            require_running_source=False,
        )


@pytest.mark.parametrize("stage", ["AFTER_INITIAL_FCHMOD", "AFTER_FULL_WRITE"])
def test_attempt_publication_fault_closes_once_with_typed_failure(
    tmp_path: Path, stage: str
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(actual_stage: str, name: str, descriptor: int) -> None:
        if name == probe.ATTEMPT_NAME and actual_stage == stage:
            if stage == "AFTER_INITIAL_FCHMOD":
                assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, f"fixture {stage}")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        failure = raised.value.failure_document
        assert failure["failed_substage"] == "ATTEMPT_PUBLICATION"
        assert store.inventory_names(phase="TEST") == frozenset(
            {
                probe.OUTER_LAUNCH_ATTEMPT_NAME,
                probe.ATTEMPT_NAME,
                probe.FAILURE_NAME,
            }
        )
        assert not store.exists(probe.RECEIPT_NAME)
        if stage == "AFTER_INITIAL_FCHMOD":
            assert store.read_exact(probe.ATTEMPT_NAME, allow_empty=True) == b"{"
        else:
            assert store.read_exact(probe.ATTEMPT_NAME) == probe.canonical_json_bytes(
                probe.build_attempt_document(authority, raw)
            )


def test_inner_attempt_post_write_return_interrupt_closes_typed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        original_write = store.write_once

        def write_then_interrupt(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )
            if name == probe.ATTEMPT_NAME:
                raise KeyboardInterrupt("fixture interrupt after ATTEMPT return")

        monkeypatch.setattr(store, "write_once", write_then_interrupt)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        assert raised.value.failure_document["failed_substage"] == (
            "ATTEMPT_PUBLICATION"
        )
        assert store.inventory_names(phase="TEST") == frozenset(
            {
                probe.OUTER_LAUNCH_ATTEMPT_NAME,
                probe.ATTEMPT_NAME,
                probe.FAILURE_NAME,
            }
        )


@pytest.mark.parametrize(
    "fault_stage",
    [
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_ROOT_FSYNC",
        "AFTER_READBACK",
    ],
)
def test_inner_exact_receipt_fault_recovers_durability_without_failure(
    tmp_path: Path, fault_stage: str
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.RECEIPT_NAME and stage == fault_stage:
            raise KeyboardInterrupt("fixture exact receipt async fault")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_outer_attempt(store, authority, raw)
        receipt = probe.run_probe_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            runtime=FakeRuntime(),
            environ=environment,
            monotonic_ns=lambda: 1_000_000,
        )
        assert probe.validate_receipt_document(
            receipt, probe.build_attempt_document(authority, raw), authority
        ) == receipt
        assert store.inventory_names(phase="TEST") == frozenset(
            {
                probe.OUTER_LAUNCH_ATTEMPT_NAME,
                probe.ATTEMPT_NAME,
                probe.RECEIPT_NAME,
            }
        )
        assert not store.exists(probe.FAILURE_NAME)


def test_inner_receipt_post_write_return_interrupt_recovers_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        original_write = store.write_once

        def write_then_interrupt(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )
            if name == probe.RECEIPT_NAME:
                raise KeyboardInterrupt("fixture interrupt after RECEIPT return")

        monkeypatch.setattr(store, "write_once", write_then_interrupt)
        receipt = probe.run_probe_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            runtime=FakeRuntime(),
            environ=environment,
            monotonic_ns=lambda: 1_000_000,
        )
        assert receipt["schema"] == probe.RECEIPT_SCHEMA
        assert not store.exists(probe.FAILURE_NAME)


def test_pre_receipt_inventory_failure_is_a_typed_receipt_build_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        original_require = store.require_inventory

        def fail_prepublication(*args, phase: str, **kwargs):
            if phase == "INNER_BEFORE_RECEIPT_PUBLICATION":
                raise OSError(errno.EIO, "fixture pre-receipt inventory failure")
            return original_require(*args, phase=phase, **kwargs)

        monkeypatch.setattr(store, "require_inventory", fail_prepublication)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "RECEIPT_BUILD"
    assert failure["errno"] == errno.EIO
    assert failure["target_absent"] is True
    assert any(
        row["substage"] == "CLEANUP_SERVICE_ALREADY_CLOSED"
        and row["status"] == "OK"
        for row in failure["substage_records"]
    )
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_outer_consumer_types_failure_when_exact_inner_receipt_cannot_recover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_stabilize = store.stabilize_exact

        def reject_inner_receipt(name: str, artifact_raw: bytes) -> None:
            if name == probe.RECEIPT_NAME:
                raise OSError(errno.EIO, "fixture persistent receipt fsync failure")
            original_stabilize(name, artifact_raw)

        monkeypatch.setattr(store, "stabilize_exact", reject_inner_receipt)

        def launch_callback(argv):
            receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(receipt) + b"\n",
                b"",
                False,
                False,
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["inner_observation"]["state"] == "RECEIPT_UNCERTAIN"
        assert "INNER_NOT_RECEIPT" in failure["failure_reason"]
        assert store.exists(probe.RECEIPT_NAME)
        assert not store.exists(probe.FAILURE_NAME)
        assert store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


def test_store_rejects_foreign_inventory_and_root_path_swap(tmp_path: Path) -> None:
    with _artifact_store(tmp_path) as store:
        foreign = store.root / "FOREIGN.json"
        foreign.write_bytes(b"{}")
        foreign.chmod(0o400)
        with pytest.raises(probe.ForeignArtifactError):
            store.inventory_names(phase="FOREIGN_ATTACK")
    swapped_root = tmp_path / "swap-root"
    swapped_root.mkdir(mode=0o700)
    swapped_root.chmod(0o700)
    with probe.DurableArtifactStore(swapped_root) as store:
        retained = tmp_path / "swap-root-retained"
        swapped_root.rename(retained)
        swapped_root.mkdir(mode=0o700)
        swapped_root.chmod(0o700)
        with pytest.raises(probe.AuthorityError):
            store.inventory_names(phase="ROOT_SWAP_ATTACK")


def test_durability_recovery_rejects_exact_bytes_on_replacement_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _artifact_store(tmp_path) as store:
        raw = b'{"fixture":"exact"}'
        store.write_once(probe.ATTEMPT_NAME, raw)
        artifact = store.root / probe.ATTEMPT_NAME
        retained = store.root / "retained-attempt-fixture"
        original_fsync = os.fsync
        swapped = False

        def swap_before_parent_fsync(descriptor: int) -> None:
            nonlocal swapped
            if descriptor == store.root_fd and not swapped:
                swapped = True
                artifact.rename(retained)
                artifact.write_bytes(raw)
                artifact.chmod(0o400)
            original_fsync(descriptor)

        monkeypatch.setattr(probe.os, "fsync", swap_before_parent_fsync)
        with pytest.raises(probe.AuthorityError):
            store.stabilize_exact(probe.ATTEMPT_NAME, raw)
        assert swapped is True
        assert retained.stat().st_ino != artifact.stat().st_ino


def test_durability_recovery_rejects_same_inode_same_size_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _artifact_store(tmp_path) as store:
        raw = b'{"fixture":"first"}'
        replacement = b'{"fixture":"other"}'
        assert len(raw) == len(replacement)
        store.write_once(probe.ATTEMPT_NAME, raw)
        artifact = store.root / probe.ATTEMPT_NAME
        original_inode = artifact.stat().st_ino
        original_fsync = os.fsync
        overwritten = False

        def overwrite_before_parent_fsync(descriptor: int) -> None:
            nonlocal overwritten
            if descriptor == store.root_fd and not overwritten:
                overwritten = True
                artifact.chmod(0o600)
                writer = os.open(artifact, os.O_WRONLY | os.O_CLOEXEC)
                try:
                    assert os.write(writer, replacement) == len(replacement)
                finally:
                    os.close(writer)
                artifact.chmod(0o400)
            original_fsync(descriptor)

        monkeypatch.setattr(probe.os, "fsync", overwrite_before_parent_fsync)
        with pytest.raises(probe.AuthorityError):
            store.stabilize_exact(probe.ATTEMPT_NAME, raw)
        assert overwritten is True
        assert artifact.stat().st_ino == original_inode
        assert artifact.read_bytes() == replacement


class FakeTargetManagerProcess:
    """Manager-only target mutator used by Linux adapter fixture tests."""

    def __init__(
        self,
        app: Path,
        control_group: str,
        *,
        fail_create: bool = False,
        fail_stop: bool = False,
    ) -> None:
        self.app = app
        self.control_group = control_group
        self.contract = probe.build_target_lifecycle_contract(os.geteuid())
        self.fail_create = fail_create
        self.fail_stop = fail_stop
        self.state = "NOT_FOUND"
        self.calls: list[tuple[str, ...]] = []
        self.stop_calls = 0
        self.before_stop = None
        self.owned_identity: tuple[int, int] | None = None
        # These saved functions model mutations performed by the trusted
        # manager, even when a test instruments probe.os deletion APIs.
        self._manager_unlink = os.unlink
        self._manager_rmdir = os.rmdir

    @property
    def target_path(self) -> Path:
        return self.app / probe.TARGET_CGROUP_NAME

    def _absence_properties_raw(self) -> bytes:
        rows = (
            FakeRuntime._manager_active_properties(self.control_group)
            if self.state == "ACTIVE"
            else FakeRuntime._manager_absent_properties()
        )
        return "".join(
            f"{key}={rows[key]}\n"
            for key in probe.TARGET_MANAGER_ABSENCE_PROPERTIES
        ).encode()

    def _active_properties_raw(self) -> bytes:
        assert self.state == "ACTIVE"
        rows = FakeRuntime._manager_active_properties(self.control_group)
        return "".join(
            f"{key}={rows[key]}\n"
            for key in probe.TARGET_MANAGER_ACTIVE_PROPERTIES
        ).encode()

    def _create_owned_target(self) -> None:
        self.target_path.mkdir()
        (self.target_path / "cgroup.type").write_text("domain\n")
        (self.target_path / "cgroup.procs").write_text("")
        (self.target_path / "cgroup.events").write_text("populated 0\n")
        metadata = self.target_path.stat()
        self.owned_identity = (metadata.st_dev, metadata.st_ino)

    def _remove_owned_target_if_still_named(self) -> None:
        try:
            metadata = self.target_path.stat()
        except FileNotFoundError:
            return
        if (metadata.st_dev, metadata.st_ino) != self.owned_identity:
            return
        for name in ("cgroup.type", "cgroup.procs", "cgroup.events"):
            self._manager_unlink(self.target_path / name)
        self._manager_rmdir(self.target_path)

    @staticmethod
    def _result(
        argv: tuple[str, ...],
        *,
        returncode: int = 0,
        stdout: bytes = b"",
        stderr: bytes = b"",
    ) -> probe.BoundedProcessResult:
        return probe.BoundedProcessResult(
            argv, returncode, stdout, stderr, False, False
        )

    def run(
        self,
        argv,
        *,
        timeout_seconds: int,
        stdout_cap: int,
        stderr_cap: int,
        env=None,
        start_new_session: bool = False,
    ) -> probe.BoundedProcessResult:
        actual = tuple(argv)
        self.calls.append(actual)
        assert 1 <= timeout_seconds <= probe.TARGET_MANAGER_CALL_TIMEOUT_SECONDS
        assert stdout_cap == probe.TARGET_MANAGER_OUTPUT_CAP_BYTES
        assert stderr_cap == probe.TARGET_MANAGER_OUTPUT_CAP_BYTES
        assert env == self.contract["environment"]
        assert start_new_session is False
        if actual == tuple(self.contract["absence_show_argv"]):
            return self._result(actual, stdout=self._absence_properties_raw())
        if actual == tuple(self.contract["create_argv"]):
            if self.fail_create:
                return self._result(actual, returncode=1, stderr=b"create failed\n")
            assert self.state == "NOT_FOUND"
            self._create_owned_target()
            self.state = "ACTIVE"
            return self._result(
                actual,
                stdout=b'o "/org/freedesktop/systemd1/job/123"\n',
            )
        if actual == tuple(self.contract["stop_argv"]):
            self.stop_calls += 1
            if self.before_stop is not None:
                callback = self.before_stop
                self.before_stop = None
                callback()
            if self.fail_stop:
                return self._result(actual, returncode=1, stderr=b"stop failed\n")
            self._remove_owned_target_if_still_named()
            self.state = "NOT_FOUND"
            return self._result(actual)
        raise AssertionError(actual)


def _manager_linux_fixture(
    tmp_path: Path,
    *,
    fail_create: bool = False,
    fail_stop: bool = False,
) -> tuple[
    Path,
    probe.ServiceHandle,
    probe.LinuxRuntimeAdapter,
    FakeTargetManagerProcess,
]:
    app = tmp_path / "app.slice"
    app.mkdir()
    app_fd = os.open(app, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    target_membership = f"/fixture/app.slice/{probe.TARGET_CGROUP_NAME}"
    process = FakeTargetManagerProcess(
        app,
        target_membership,
        fail_create=fail_create,
        fail_stop=fail_stop,
    )
    observation = {"target_lifecycle_contract": process.contract}
    service = probe.ServiceHandle(
        app_fd,
        -1,
        str(app),
        str(app / probe.SERVICE_UNIT_NAME),
        f"/fixture/app.slice/{probe.SERVICE_UNIT_NAME}",
        target_membership,
        observation,
    )
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.process_adapter = process
    adapter._fstatfs_type = lambda _descriptor: probe.CGROUP2_SUPER_MAGIC

    def emulate_kernfs_detach(target: probe.TargetHandle) -> dict[str, object]:
        fact = probe._observe_retained_ofd_detach(target)
        if fact["deleted_marker"] is True:
            fact["nlink"] = 2
            fact["fstatfs_type"] = probe.CGROUP2_SUPER_MAGIC
            fact["conformant"] = (
                fact["device"] == target.device
                and fact["inode"] == target.inode
                and stat.S_ISDIR(fact["mode"])
                and fact["cgroup_type_errno"] == errno.ENOENT
                and fact["cgroup_events_errno"] == errno.ENOENT
                and fact["cgroup_procs_errno"] == errno.ENOENT
            )
        return fact

    adapter._retained_ofd_detach_fact = emulate_kernfs_detach
    return app, service, adapter, process


@pytest.mark.parametrize(
    "mode", ["SUCCESS", "FOREIGN_TARGET", "SERVICE_BUSY", "MANAGER_PREEXISTS"]
)
def test_linux_inspect_service_full_branch_is_fail_closed_and_closes_fds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    uid = os.geteuid()
    gid = os.getegid()
    app_membership, source_membership, target_membership = (
        probe.LinuxRuntimeAdapter._expected_memberships(uid)
    )
    mount = tmp_path / "cgroup"
    app = Path(str(mount) + app_membership)
    service_path = app / probe.SERVICE_UNIT_NAME
    service_path.mkdir(parents=True)
    (app / "cgroup.controllers").write_text("memory pids\n")
    (app / "cgroup.subtree_control").write_text("memory pids\n")
    (app / "cgroup.type").write_text("domain\n")
    (app / "cgroup.procs").write_text("")
    service_pid = os.getpid() if mode != "SERVICE_BUSY" else os.getpid() + 1
    (service_path / "cgroup.procs").write_text(f"{service_pid}\n")
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(mode=0o700)
    runtime_dir.chmod(0o700)
    bus_path = runtime_dir / "bus"
    bus_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    bus_socket.bind(str(bus_path))
    if mode == "FOREIGN_TARGET":
        (app / probe.TARGET_CGROUP_NAME).mkdir()

    mount_stat = mount.stat()
    app_stat = app.stat()
    procs_stat = (app / "cgroup.procs").stat()
    runtime_stat = runtime_dir.stat()
    bus_stat = bus_path.stat()
    host = {
        "schema": probe.HOST_PARENT_SCHEMA,
        "mount_point": str(mount),
        "mount_device": mount_stat.st_dev,
        "mount_inode": mount_stat.st_ino,
        "app_slice_path": str(app),
        "app_slice_device": app_stat.st_dev,
        "app_slice_inode": app_stat.st_ino,
        "owner_uid": app_stat.st_uid,
        "owner_gid": app_stat.st_gid,
        "mode": stat.S_IMODE(app_stat.st_mode),
        "controllers": ["memory", "pids"],
        "subtree_control": ["memory", "pids"],
        "cgroup_type": "domain",
        "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
        "cgroup_procs_device": procs_stat.st_dev,
        "cgroup_procs_inode": procs_stat.st_ino,
        "cgroup_procs_owner_uid": procs_stat.st_uid,
        "cgroup_procs_owner_gid": procs_stat.st_gid,
        "cgroup_procs_mode": stat.S_IMODE(procs_stat.st_mode),
        "runtime_dir_path": str(runtime_dir),
        "runtime_dir_device": runtime_stat.st_dev,
        "runtime_dir_inode": runtime_stat.st_ino,
        "runtime_dir_owner_uid": runtime_stat.st_uid,
        "runtime_dir_owner_gid": runtime_stat.st_gid,
        "runtime_dir_mode": stat.S_IMODE(runtime_stat.st_mode),
        "user_bus_path": str(bus_path),
        "user_bus_device": bus_stat.st_dev,
        "user_bus_inode": bus_stat.st_ino,
        "user_bus_owner_uid": bus_stat.st_uid,
        "user_bus_owner_gid": bus_stat.st_gid,
        "user_bus_mode": stat.S_IMODE(bus_stat.st_mode),
        "user_bus_file_type": "socket",
        "toolchain_facts": [],
    }
    manager = FakeTargetManagerProcess(app, target_membership)
    if mode == "MANAGER_PREEXISTS":
        manager.state = "ACTIVE"
    invocation = {
        "target_lifecycle_contract": manager.contract,
    }
    authority = {
        "host_parent_fact": host,
        "systemd_invocation_contract": invocation,
    }
    monkeypatch.setattr(
        probe, "validate_host_parent_fact", lambda value: dict(value)
    )
    monkeypatch.setattr(
        probe,
        "validate_systemd_invocation_contract",
        lambda value: dict(value),
    )
    monkeypatch.setattr(
        probe,
        "_proc_cgroup",
        lambda pid: f"0::{source_membership}" if pid == os.getpid() else "",
    )

    def writable_fact(path: Path) -> dict[str, object]:
        metadata = path.stat()
        return {
            "opened_for_write": True,
            "errno": None,
            "errno_name": None,
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode),
            "owner_uid": metadata.st_uid,
            "owner_gid": metadata.st_gid,
        }

    monkeypatch.setattr(probe, "_open_write_permission", writable_fact)
    real_open = os.open
    tracked_fds: list[int] = []

    def tracked_open(path, flags, mode_bits=0o777, *, dir_fd=None):
        descriptor = real_open(path, flags, mode_bits, dir_fd=dir_fd)
        if dir_fd is None and Path(path) in {app, service_path}:
            tracked_fds.append(descriptor)
        return descriptor

    monkeypatch.setattr(probe.os, "open", tracked_open)
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.process_adapter = manager
    adapter._fstatfs_type = lambda _descriptor: probe.CGROUP2_SUPER_MAGIC
    try:
        if mode == "SUCCESS":
            service, detail = adapter.inspect_service(authority, 10**30)
            assert detail["source_membership"] == source_membership
            assert detail["target_membership"] == target_membership
            assert detail["target_manager_implicit_absence_before_create"] is True
            assert service.app_slice_fd >= 0 and service.service_fd >= 0
            adapter.close_service(service)
        else:
            with pytest.raises(OSError):
                adapter.inspect_service(authority, 10**30)
        assert tracked_fds
        for descriptor in tracked_fds:
            with pytest.raises(OSError) as closed:
                os.fstat(descriptor)
            assert closed.value.errno == errno.EBADF
    finally:
        bus_socket.close()


def test_target_eexist_and_unowned_target_never_start_manager_stop(
    tmp_path: Path,
) -> None:
    app = tmp_path / "app.slice"
    app, service, adapter, process = _manager_linux_fixture(tmp_path)
    target_path = app / probe.TARGET_CGROUP_NAME
    target_path.mkdir()
    try:
        with pytest.raises(probe.TargetCreationError) as raised:
            adapter.create_target(service, 10**30)
        assert raised.value.errno == errno.EEXIST
        assert raised.value.target is None
        with pytest.raises(OSError) as deletion:
            adapter.remove_target(service, None, 10**30)
        assert deletion.value.errno == errno.EPERM
        assert process.stop_calls == 0
        assert target_path.exists()
    finally:
        adapter.close_service(service)


def test_inspection_absence_gate_rejects_fixed_foreign_target(tmp_path: Path) -> None:
    app = tmp_path / "app.slice"
    app.mkdir()
    app_fd = os.open(app, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert probe._require_fixed_target_absent(app_fd) == {
            "fixed_target_absent_before_create": True
        }
        (app / probe.TARGET_CGROUP_NAME).mkdir()
        with pytest.raises(OSError) as raised:
            probe._require_fixed_target_absent(app_fd)
        assert raised.value.errno == errno.EEXIST
        assert (app / probe.TARGET_CGROUP_NAME).exists()
    finally:
        os.close(app_fd)


def test_manager_create_failure_carries_residual_claim_without_stop(
    tmp_path: Path,
) -> None:
    _app, service, adapter, process = _manager_linux_fixture(
        tmp_path, fail_create=True
    )
    try:
        with pytest.raises(probe.TargetCreationError) as raised:
            adapter.create_target(service, 10**30)
        claim = raised.value.target
        assert claim is not None and claim.owned is True
        assert claim.directory_fd == -1
        assert claim.identity_continuous is False
        assert claim.manager_unit_ownership_acquired is False
        assert claim.residual_possible is False
        diagnostic = probe.validate_target_create_diagnostic(
            raised.value.diagnostic
        )
        assert diagnostic["exception_phase"] == "MANAGER_CREATE"
        assert diagnostic["manager_create_result"] is not None
        assert diagnostic["unique_manager_unit_ownership_acquired"] is False
        probe.validate_target_creation_error_join(raised.value)
        with pytest.raises(OSError) as forbidden:
            adapter.remove_target(service, claim, 10**30)
        assert forbidden.value.errno == errno.EPERM
        assert process.stop_calls == 0
    finally:
        adapter.close_service(service)


def test_manager_create_named_stat_race_closes_partial_target_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _app, service, adapter, _process = _manager_linux_fixture(tmp_path)
    real_open = os.open
    real_stat = os.stat
    target_stats = 0
    opened_target_fds: list[int] = []

    def tracked_open(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == probe.TARGET_CGROUP_NAME and dir_fd == service.app_slice_fd:
            opened_target_fds.append(descriptor)
        return descriptor

    def fail_second_target_stat(path, *args, dir_fd=None, **kwargs):
        nonlocal target_stats
        if path == probe.TARGET_CGROUP_NAME and dir_fd == service.app_slice_fd:
            target_stats += 1
            if target_stats == 2:
                raise FileNotFoundError(errno.ENOENT, "fixture target stat race")
        return real_stat(path, *args, dir_fd=dir_fd, **kwargs)

    monkeypatch.setattr(probe.os, "open", tracked_open)
    monkeypatch.setattr(probe.os, "stat", fail_second_target_stat)
    try:
        with pytest.raises(probe.TargetCreationError) as raised:
            adapter.create_target(service, 10**30)
        claim = raised.value.target
        assert claim is not None
        assert claim.directory_fd == -1
        assert claim.identity_continuous is False
        assert claim.residual_possible is True
        assert len(opened_target_fds) == 1
        with pytest.raises(OSError) as closed:
            os.fstat(opened_target_fds[0])
        assert closed.value.errno == errno.EBADF
    finally:
        adapter.close_service(service)


def test_manager_stop_failure_is_typed_residual(tmp_path: Path) -> None:
    app, service, adapter, process = _manager_linux_fixture(
        tmp_path, fail_stop=True
    )
    try:
        target, _detail = adapter.create_target(service, 10**30)
        with pytest.raises(probe.TargetRemovalError) as raised:
            adapter.remove_target(service, target, 10**30)
        probe.validate_target_removal_error_join(raised.value)
        assert raised.value.diagnostic["exception_phase"] == "STOP_SUBPROCESS"
        assert target.stop_requested is True
        assert target.manager_implicit_absence_proven is False
        assert target.residual_possible is True
        assert process.stop_calls == 1
        assert (app / probe.TARGET_CGROUP_NAME).exists()
        with pytest.raises(OSError) as residual:
            adapter.target_absent(service, target, 10**30)
        assert residual.value.errno == errno.ESTALE
    finally:
        adapter.close_service(service)


@pytest.mark.parametrize("replacement", [False, True])
def test_manager_cleanup_rename_away_or_replacement_never_stops_or_claims_clean(
    tmp_path: Path, replacement: bool
) -> None:
    app, service, adapter, process = _manager_linux_fixture(tmp_path)
    retained = app / "retained-manager-owned-target"
    try:
        target, _detail = adapter.create_target(service, 10**30)
        os.rename(process.target_path, retained)
        if replacement:
            process.target_path.mkdir()
        with pytest.raises(OSError) as drift:
            adapter.remove_target(service, target, 10**30)
        assert drift.value.errno == errno.ESTALE
        assert process.stop_calls == 0
        assert target.identity_continuous is False
        assert target.manager_implicit_absence_proven is False
        assert target.residual_possible is True
        assert retained.exists()
        assert process.target_path.exists() is replacement
        with pytest.raises(OSError) as residual:
            adapter.target_absent(service, target, 10**30)
        assert residual.value.errno == errno.ESTALE
    finally:
        adapter.close_service(service)


def test_manager_stop_race_preserves_replacement_and_fails_closed(
    tmp_path: Path,
) -> None:
    app, service, adapter, process = _manager_linux_fixture(tmp_path)
    retained = app / "retained-manager-owned-target"

    def swap_after_probe_identity_check() -> None:
        os.rename(process.target_path, retained)
        process.target_path.mkdir()

    try:
        target, _detail = adapter.create_target(service, 10**30)
        process.before_stop = swap_after_probe_identity_check
        with pytest.raises(OSError) as drift:
            adapter.remove_target(service, target, 10**30)
        assert drift.value.errno == errno.ESTALE
        assert process.stop_calls == 1
        assert retained.exists()
        assert process.target_path.exists()
        assert target.identity_continuous is False
        assert target.residual_possible is True
    finally:
        adapter.close_service(service)


def test_manager_stop_race_rename_away_without_replacement_cannot_fake_unlink(
    tmp_path: Path,
) -> None:
    app, service, adapter, process = _manager_linux_fixture(tmp_path)
    retained = app / "retained-manager-owned-target"

    def rename_away_after_probe_identity_check() -> None:
        os.rename(process.target_path, retained)

    try:
        target, _detail = adapter.create_target(service, 10**30)
        process.before_stop = rename_away_after_probe_identity_check
        with pytest.raises(OSError) as drift:
            adapter.remove_target(service, target, 10**30)
        assert drift.value.errno == errno.ESTALE
        assert process.stop_calls == 1
        assert retained.exists()
        assert not process.target_path.exists()
        assert target.named_path_detached_and_manager_implicit_absence is False
        assert target.identity_continuous is False
        assert target.residual_possible is True
    finally:
        adapter.close_service(service)


def test_manager_success_uses_no_probe_path_deletion_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _app, service, adapter, process = _manager_linux_fixture(tmp_path)
    probe_deletions: list[str] = []

    def forbidden(*_args, **_kwargs):
        probe_deletions.append("called")
        raise AssertionError("probe attempted a path deletion API")

    monkeypatch.setattr(probe.os, "rmdir", forbidden)
    monkeypatch.setattr(probe.os, "unlink", forbidden)
    monkeypatch.setattr(probe.os, "rename", forbidden)
    try:
        target, create_detail = adapter.create_target(service, 10**30)
        assert create_detail["manager_owned_lifecycle"] is True
        assert adapter.target_empty(target)["populated"] == 0
        remove_detail = adapter.remove_target(service, target, 10**30)
        assert remove_detail["manager_implicit_absence_proven"] is True
        assert remove_detail["named_path_detached_and_manager_implicit_absence"] is True
        assert target.named_path_detached_and_manager_implicit_absence is True
        absent = adapter.target_absent(service, target, 10**30)
        assert absent["target_absent"] is True
        assert absent["probe_path_deletion_calls"] == 0
        assert probe_deletions == []
        assert process.stop_calls == 1
    finally:
        adapter.close_service(service)


def test_probe_source_has_no_target_path_deletion_primitive() -> None:
    tree = ast.parse(SCRIPT.read_text())
    forbidden = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr in {"rmdir", "unlink", "rename", "renameat"}
        ):
            forbidden.append((node.func.attr, node.lineno))
    assert forbidden == []


def test_outer_launch_failure_publication_has_one_writer_and_six_call_sites() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    writer_functions: list[str] = []
    caller_functions: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for descendant in ast.walk(node):
            if not isinstance(descendant, ast.Call):
                continue
            if (
                isinstance(descendant.func, ast.Attribute)
                and descendant.func.attr == "write_once"
                and descendant.args
                and isinstance(descendant.args[0], ast.Name)
                and descendant.args[0].id == "OUTER_LAUNCH_FAILURE_NAME"
            ):
                writer_functions.append(node.name)
            if (
                isinstance(descendant.func, ast.Name)
                and descendant.func.id
                == "_publish_outer_launch_failure_terminal"
            ):
                caller_functions.append(node.name)
    assert writer_functions == ["_publish_outer_launch_failure_terminal"]
    assert sorted(caller_functions) == sorted(
        [
            "_publish_outer_launch_failure",
            "_publish_outer_receipt_postpublication_deadline_failure",
            "_publish_outer_receipt_recovery_failure",
            "_publish_outer_success_seal_failure",
            "run_outer_launch_once",
            "run_outer_launch_once",
        ]
    )


def test_prepare_failure_publication_has_one_writer_and_six_call_sites() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    writer_functions: list[str] = []
    builder_callers: list[str] = []
    terminal_callers: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for descendant in ast.walk(node):
            if not isinstance(descendant, ast.Call):
                continue
            if (
                isinstance(descendant.func, ast.Attribute)
                and descendant.func.attr == "write_once"
                and descendant.args
                and isinstance(descendant.args[0], ast.Name)
                and descendant.args[0].id == "PREPARE_FAILURE_NAME"
            ):
                writer_functions.append(node.name)
            if isinstance(descendant.func, ast.Name):
                if descendant.func.id == "_publish_prepare_failure":
                    builder_callers.append(node.name)
                elif (
                    descendant.func.id == "_publish_prepare_failure_terminal"
                ):
                    terminal_callers.append(node.name)
    assert writer_functions == ["_publish_prepare_failure_terminal"]
    assert builder_callers == ["prepare_external_root_once"] * 6
    assert terminal_callers == ["_publish_prepare_failure"]


def test_generic_target_creation_error_cannot_authorize_manager_stop(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class PostManagerCreateFailureRuntime(FakeRuntime):
        def create_target(
            self, service: probe.ServiceHandle, _deadline_ns: int
        ):
            self.calls.append("create_target")
            self.target_created = True
            claim = probe.TargetHandle(
                77,
                probe.TARGET_CGROUP_NAME,
                f"{service.app_slice_path}/{probe.TARGET_CGROUP_NAME}",
                service.target_membership,
                91,
                92,
                True,
            )
            raise probe.TargetCreationError(
                errno.EACCES,
                "fixture failure after continuous manager target claim",
                target=claim,
            )

    runtime = PostManagerCreateFailureRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "TARGET_CREATE"
    assert failure["error_type"] == "AuthorityError"
    assert failure["message"] == "TargetCreationError omitted its diagnostic"
    assert failure["target_manager_stop_requested"] is False
    assert "remove_target" not in runtime.calls
    assert (store.root / probe.FAILURE_NAME).exists()
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_open_write_permission_uses_exact_owronly_flags_and_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "cgroup.procs"
    path.write_bytes(b"")
    observed: list[int] = []
    real_open = os.open

    def recording_open(actual_path, flags, *args, **kwargs):
        assert Path(actual_path) == path
        observed.append(flags)
        return real_open(actual_path, flags, *args, **kwargs)

    monkeypatch.setattr(probe.os, "open", recording_open)
    fact = probe._open_write_permission(path)
    named = path.stat()
    assert observed == [os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC]
    assert fact["opened_for_write"] is True
    assert (fact["device"], fact["inode"]) == (named.st_dev, named.st_ino)


def test_clone3_adapter_passes_atomic_flags_pidfd_pointer_and_cgroup_fd() -> None:
    class FakeLibc:
        def __init__(self) -> None:
            self.observation = None

        def syscall(self, number, pointer, size):
            args = ctypes.cast(pointer, ctypes.POINTER(probe._CloneArgs)).contents
            self.observation = {
                "number": number,
                "size": size,
                "flags": args.flags,
                "pidfd": args.pidfd,
                "exit_signal": args.exit_signal,
                "cgroup": args.cgroup,
            }
            ctypes.set_errno(errno.EACCES)
            return -1

    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = FakeLibc()
    target = probe.TargetHandle(-1, "target", "/target", "/target", 1, 2)
    target.directory_fd = 77
    with pytest.raises(OSError) as raised:
        adapter.clone_child(target, 1_000_000)
    assert raised.value.errno == errno.EACCES
    observation = adapter.libc.observation
    assert observation == {
        "number": probe.CLONE3_SYSCALL_X86_64,
        "size": ctypes.sizeof(probe._CloneArgs),
        "flags": probe.CLONE_PIDFD | probe.CLONE_INTO_CGROUP,
        "pidfd": observation["pidfd"],
        "exit_signal": probe.signal.SIGCHLD,
        "cgroup": 77,
    }
    assert observation["pidfd"] != 0


class _ProvisionalCloneLibc:
    def __init__(
        self,
        pid: int,
        pidfd: int,
        *,
        real_kill,
        pidfd_signal_errno: int | None = None,
    ) -> None:
        self.pid = pid
        self.pidfd = pidfd
        self.real_kill = real_kill
        self.pidfd_signal_errno = pidfd_signal_errno
        self.pidfd_signal_calls = 0

    def syscall(self, number, *arguments):
        if number == probe.CLONE3_SYSCALL_X86_64:
            clone_args = ctypes.cast(
                arguments[0], ctypes.POINTER(probe._CloneArgs)
            ).contents
            ctypes.cast(
                clone_args.pidfd, ctypes.POINTER(ctypes.c_int)
            ).contents.value = self.pidfd
            return self.pid
        assert number == probe.PIDFD_SEND_SIGNAL_SYSCALL_X86_64
        assert arguments == (self.pidfd, probe.signal.SIGKILL, 0, 0)
        self.pidfd_signal_calls += 1
        if self.pidfd_signal_errno is not None:
            ctypes.set_errno(self.pidfd_signal_errno)
            return -1
        self.real_kill(self.pid, probe.signal.SIGKILL)
        return 0


class _CloseFaultSocket:
    def __init__(self, inner: socket.socket, *, fail_count: int) -> None:
        self.inner = inner
        self.fail_count = fail_count
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        if self.close_calls <= self.fail_count:
            raise OSError(errno.EIO, "injected child socket close failure")
        self.inner.close()

    def fileno(self) -> int:
        return self.inner.fileno()


def _fork_provisional_child() -> tuple[int, int]:
    pid = os.fork()
    if pid == 0:
        try:
            while True:
                probe.signal.pause()
        finally:
            os._exit(127)
    try:
        return pid, os.pidfd_open(pid, 0)
    except BaseException:
        os.kill(pid, probe.signal.SIGKILL)
        os.waitpid(pid, 0)
        raise


def _reap_provisional_child(pid: int, *, real_waitpid, real_kill) -> None:
    try:
        waited, _status = real_waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return
    if waited == pid:
        return
    assert waited == 0
    try:
        real_kill(pid, probe.signal.SIGKILL)
    except ProcessLookupError:
        pass
    while True:
        try:
            real_waitpid(pid, 0)
            return
        except InterruptedError:
            continue
        except ChildProcessError:
            return


def _assert_descriptor_closed(descriptor: int) -> None:
    with pytest.raises(OSError) as raised:
        os.fstat(descriptor)
    assert raised.value.errno == errno.EBADF


def test_clone_child_branch_parent_socket_close_fault_exits_127(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ChildResultLibc:
        def syscall(self, _number, *_arguments):
            return 0

    class ExitCalled(BaseException):
        def __init__(self, code: int) -> None:
            self.code = code

    real_socketpair = probe.socket.socketpair
    raw_parent_socket, child_socket = real_socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
    )
    parent_socket = _CloseFaultSocket(raw_parent_socket, fail_count=1)
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = ChildResultLibc()
    monkeypatch.setattr(
        probe.socket,
        "socketpair",
        lambda *_args, **_kwargs: (parent_socket, child_socket),
    )
    monkeypatch.setattr(
        probe.os, "_exit", lambda code: (_ for _ in ()).throw(ExitCalled(code))
    )
    target = probe.TargetHandle(77, "target", "/target", "/target", 1, 2)
    try:
        with pytest.raises(ExitCalled) as raised:
            adapter.clone_child(target, 0)
        assert raised.value.code == 127
        assert parent_socket.close_calls == 1
    finally:
        raw_parent_socket.close()
        child_socket.close()


def test_clone_child_socket_close_fault_kills_reaps_and_closes_provisional_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_socketpair = probe.socket.socketpair
    real_waitpid = probe.os.waitpid
    real_kill = probe.os.kill
    real_close = probe.os.close
    pid, pidfd = _fork_provisional_child()
    parent_socket, raw_child_socket = real_socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
    )
    child_socket = _CloseFaultSocket(raw_child_socket, fail_count=1)
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = _ProvisionalCloneLibc(
        pid, pidfd, real_kill=real_kill
    )
    monkeypatch.setattr(
        probe.socket,
        "socketpair",
        lambda *_args, **_kwargs: (parent_socket, child_socket),
    )
    target = probe.TargetHandle(77, "target", "/target", "/target", 1, 2)
    try:
        with pytest.raises(probe.CloneProvisionalContainmentError) as raised:
            adapter.clone_child(
                target, probe.time.monotonic_ns() + 2_000_000_000
            )
        error = raised.value
        assert error.child_pid == pid
        assert error.child_pidfd == pidfd
        assert error.child_reaped is True
        assert error.resources_closed is True
        assert error.containment_complete is True
        assert error.containment_errors == ()
        assert child_socket.close_calls == 2
        assert parent_socket.fileno() == -1
        assert raw_child_socket.fileno() == -1
        _assert_descriptor_closed(pidfd)
    finally:
        _reap_provisional_child(
            pid, real_waitpid=real_waitpid, real_kill=real_kill
        )
        raw_child_socket.close()
        parent_socket.close()
        try:
            real_close(pidfd)
        except OSError as error:
            assert error.errno == errno.EBADF


def test_clone_f_setfd_fault_kills_reaps_and_closes_provisional_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_fcntl = probe.fcntl.fcntl
    real_waitpid = probe.os.waitpid
    real_kill = probe.os.kill
    real_close = probe.os.close
    pid, pidfd = _fork_provisional_child()
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = _ProvisionalCloneLibc(
        pid, pidfd, real_kill=real_kill
    )

    def fail_f_setfd(descriptor, command, argument=0):
        if descriptor == pidfd and command == probe.fcntl.F_SETFD:
            raise OSError(errno.EIO, "injected F_SETFD failure")
        return real_fcntl(descriptor, command, argument)

    monkeypatch.setattr(probe.fcntl, "fcntl", fail_f_setfd)
    target = probe.TargetHandle(77, "target", "/target", "/target", 1, 2)
    try:
        with pytest.raises(probe.CloneProvisionalContainmentError) as raised:
            adapter.clone_child(
                target, probe.time.monotonic_ns() + 2_000_000_000
            )
        error = raised.value
        assert error.child_reaped is True
        assert error.resources_closed is True
        assert error.containment_complete is True
        assert error.containment_errors == ()
        assert adapter.libc.pidfd_signal_calls == 1
        _assert_descriptor_closed(pidfd)
    finally:
        _reap_provisional_child(
            pid, real_waitpid=real_waitpid, real_kill=real_kill
        )
        try:
            real_close(pidfd)
        except OSError as error:
            assert error.errno == errno.EBADF


def test_clone_setup_fault_gets_independent_reap_grace_after_expired_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_fcntl = probe.fcntl.fcntl
    real_waitpid = probe.os.waitpid
    real_kill = probe.os.kill
    real_close = probe.os.close
    pid, pidfd = _fork_provisional_child()
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = _ProvisionalCloneLibc(
        pid, pidfd, real_kill=real_kill
    )
    wait_calls = 0

    def fail_f_setfd(descriptor, command, argument=0):
        if descriptor == pidfd and command == probe.fcntl.F_SETFD:
            raise OSError(errno.EIO, "injected F_SETFD failure")
        return real_fcntl(descriptor, command, argument)

    def delay_reap(actual_pid: int, flags: int):
        nonlocal wait_calls
        assert actual_pid == pid and flags == os.WNOHANG
        wait_calls += 1
        if wait_calls <= 3:
            return 0, 0
        return real_waitpid(actual_pid, flags)

    monkeypatch.setattr(probe.fcntl, "fcntl", fail_f_setfd)
    monkeypatch.setattr(probe.os, "waitpid", delay_reap)
    target = probe.TargetHandle(77, "target", "/target", "/target", 1, 2)
    try:
        with pytest.raises(probe.CloneProvisionalContainmentError) as raised:
            adapter.clone_child(target, 0)
        assert wait_calls >= 4
        assert raised.value.child_reaped is True
        assert raised.value.containment_complete is True
        _assert_descriptor_closed(pidfd)
    finally:
        _reap_provisional_child(
            pid, real_waitpid=real_waitpid, real_kill=real_kill
        )
        try:
            real_close(pidfd)
        except OSError as error:
            assert error.errno == errno.EBADF


def test_clone_missing_pidfd_kills_reaps_and_closes_by_fresh_child_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_socketpair = probe.socket.socketpair
    real_waitpid = probe.os.waitpid
    real_kill = probe.os.kill
    real_close = probe.os.close
    pid, unused_pidfd = _fork_provisional_child()
    real_close(unused_pidfd)
    sockets: list[socket.socket] = []
    fallback_kills: list[tuple[int, int]] = []

    def capture_socketpair(*args, **kwargs):
        pair = real_socketpair(*args, **kwargs)
        sockets.extend(pair)
        return pair

    def record_kill(actual_pid: int, actual_signal: int) -> None:
        fallback_kills.append((actual_pid, actual_signal))
        real_kill(actual_pid, actual_signal)

    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = _ProvisionalCloneLibc(
        pid, -1, real_kill=real_kill
    )
    monkeypatch.setattr(probe.socket, "socketpair", capture_socketpair)
    monkeypatch.setattr(probe.os, "kill", record_kill)
    target = probe.TargetHandle(77, "target", "/target", "/target", 1, 2)
    try:
        with pytest.raises(probe.CloneProvisionalContainmentError) as raised:
            adapter.clone_child(
                target, probe.time.monotonic_ns() + 2_000_000_000
            )
        error = raised.value
        assert error.child_pidfd == -1
        assert isinstance(error.setup_error, OSError)
        assert error.setup_error.errno == errno.EPROTO
        assert error.containment_complete is True
        assert fallback_kills == [(pid, probe.signal.SIGKILL)]
        assert len(sockets) == 2
        assert all(item.fileno() == -1 for item in sockets)
    finally:
        _reap_provisional_child(
            pid, real_waitpid=real_waitpid, real_kill=real_kill
        )
        for item in sockets:
            item.close()


def test_clone_pidfd_signal_fault_uses_fresh_child_pid_kill_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_fcntl = probe.fcntl.fcntl
    real_waitpid = probe.os.waitpid
    real_kill = probe.os.kill
    real_close = probe.os.close
    pid, pidfd = _fork_provisional_child()
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = _ProvisionalCloneLibc(
        pid,
        pidfd,
        real_kill=real_kill,
        pidfd_signal_errno=errno.EIO,
    )
    fallback_kills: list[tuple[int, int]] = []

    def fail_f_setfd(descriptor, command, argument=0):
        if descriptor == pidfd and command == probe.fcntl.F_SETFD:
            raise OSError(errno.EIO, "injected F_SETFD failure")
        return real_fcntl(descriptor, command, argument)

    def record_kill(actual_pid: int, actual_signal: int) -> None:
        fallback_kills.append((actual_pid, actual_signal))
        real_kill(actual_pid, actual_signal)

    monkeypatch.setattr(probe.fcntl, "fcntl", fail_f_setfd)
    monkeypatch.setattr(probe.os, "kill", record_kill)
    target = probe.TargetHandle(77, "target", "/target", "/target", 1, 2)
    try:
        with pytest.raises(probe.CloneProvisionalContainmentError) as raised:
            adapter.clone_child(
                target, probe.time.monotonic_ns() + 2_000_000_000
            )
        assert raised.value.containment_complete is True
        assert raised.value.containment_errors == ()
        assert fallback_kills == [(pid, probe.signal.SIGKILL)]
        _assert_descriptor_closed(pidfd)
    finally:
        _reap_provisional_child(
            pid, real_waitpid=real_waitpid, real_kill=real_kill
        )
        try:
            real_close(pidfd)
        except OSError as error:
            assert error.errno == errno.EBADF


def test_clone_cleanup_wait_fault_is_typed_as_unreaped_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_fcntl = probe.fcntl.fcntl
    real_waitpid = probe.os.waitpid
    real_kill = probe.os.kill
    real_close = probe.os.close
    pid, pidfd = _fork_provisional_child()
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = _ProvisionalCloneLibc(
        pid, pidfd, real_kill=real_kill
    )

    def fail_f_setfd(descriptor, command, argument=0):
        if descriptor == pidfd and command == probe.fcntl.F_SETFD:
            raise OSError(errno.EIO, "injected F_SETFD failure")
        return real_fcntl(descriptor, command, argument)

    def fail_waitpid(actual_pid: int, flags: int):
        assert actual_pid == pid and flags == os.WNOHANG
        raise OSError(errno.EIO, "injected provisional waitpid failure")

    monkeypatch.setattr(probe.fcntl, "fcntl", fail_f_setfd)
    monkeypatch.setattr(probe.os, "waitpid", fail_waitpid)
    target = probe.TargetHandle(77, "target", "/target", "/target", 1, 2)
    try:
        with pytest.raises(probe.CloneProvisionalContainmentError) as raised:
            adapter.clone_child(
                target, probe.time.monotonic_ns() + 2_000_000_000
            )
        error = raised.value
        assert error.child_reaped is False
        assert error.resources_closed is True
        assert error.containment_complete is False
        assert any(
            isinstance(item, OSError) and item.errno == errno.EIO
            for item in error.containment_errors
        )
        _assert_descriptor_closed(pidfd)
    finally:
        _reap_provisional_child(
            pid, real_waitpid=real_waitpid, real_kill=real_kill
        )
        try:
            real_close(pidfd)
        except OSError as error:
            assert error.errno == errno.EBADF


def test_clone_cleanup_close_fault_is_typed_after_child_reap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_fcntl = probe.fcntl.fcntl
    real_waitpid = probe.os.waitpid
    real_kill = probe.os.kill
    real_close = probe.os.close
    pid, pidfd = _fork_provisional_child()
    adapter = object.__new__(probe.LinuxRuntimeAdapter)
    adapter.libc = _ProvisionalCloneLibc(
        pid, pidfd, real_kill=real_kill
    )

    def fail_f_setfd(descriptor, command, argument=0):
        if descriptor == pidfd and command == probe.fcntl.F_SETFD:
            raise OSError(errno.EIO, "injected F_SETFD failure")
        return real_fcntl(descriptor, command, argument)

    def close_then_fail(descriptor: int) -> None:
        real_close(descriptor)
        if descriptor == pidfd:
            raise OSError(errno.EIO, "injected provisional pidfd close failure")

    target = probe.TargetHandle(77, "target", "/target", "/target", 1, 2)
    try:
        with monkeypatch.context() as fault_patch:
            fault_patch.setattr(probe.fcntl, "fcntl", fail_f_setfd)
            fault_patch.setattr(probe.os, "close", close_then_fail)
            with pytest.raises(probe.CloneProvisionalContainmentError) as raised:
                adapter.clone_child(
                    target, probe.time.monotonic_ns() + 2_000_000_000
                )
        error = raised.value
        assert error.child_reaped is True
        assert error.resources_closed is False
        assert error.containment_complete is False
        assert any(
            "pidfd close failure" in str(item)
            for item in error.containment_errors
        )
        _assert_descriptor_closed(pidfd)
    finally:
        _reap_provisional_child(
            pid, real_waitpid=real_waitpid, real_kill=real_kill
        )
        try:
            real_close(pidfd)
        except OSError as error:
            assert error.errno == errno.EBADF


def test_outer_launch_success_closes_exact_inventory_with_fake_process(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        def launch_callback(argv):
            receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(receipt) + b"\n",
                b"",
                False,
                False,
            )

        process = FakeLaunchProcess(launch_callback)
        outer_receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=process,
            absence_observer=FakeAbsenceObserver(),
        )
        assert outer_receipt["schema"] == probe.OUTER_LAUNCH_RECEIPT_SCHEMA
        assert outer_receipt["inner_observation"]["state"] == "RECEIPT"
        assert outer_receipt["source_unit_absent"] is True
        assert outer_receipt["source_path_absent"] is True
        assert outer_receipt[
            "target_transient_instance_implicit_absence"
        ] is True
        assert outer_receipt["target_path_absent"] is True
        assert store.inventory_names(phase="TEST") == frozenset(
            {
                probe.OUTER_LAUNCH_ATTEMPT_NAME,
                probe.ATTEMPT_NAME,
                probe.RECEIPT_NAME,
                probe.OUTER_LAUNCH_RECEIPT_NAME,
                probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME,
            }
        )
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)
        outer_attempt = probe.build_outer_launch_attempt_document(
            authority, raw
        )
        receipt_raw = store.read_exact(probe.OUTER_LAUNCH_RECEIPT_NAME)
        seal_raw = store.read_exact(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        seal = probe.validate_outer_launch_success_seal_document(
            probe.loads_canonical_json(seal_raw),
            outer_attempt=outer_attempt,
            receipt=outer_receipt,
            receipt_raw=receipt_raw,
        )
        inner_attempt = probe.loads_canonical_json(
            store.read_exact(probe.ATTEMPT_NAME)
        )
        inner_receipt = probe.loads_canonical_json(
            store.read_exact(probe.RECEIPT_NAME)
        )
        policy = probe.build_same_uid_manager_concurrency_policy()
        policy_id = policy["same_uid_manager_concurrency_policy_id"]
        for document in (
            outer_attempt,
            inner_attempt,
            inner_receipt,
            outer_receipt["inner_observation"],
            outer_receipt,
            seal,
        ):
            assert document["same_uid_manager_concurrency_policy_id"] == policy_id
            assert document["same_uid_manager_concurrency_policy_status"] == (
                probe.SAME_UID_MANAGER_CONCURRENCY_POLICY_STATUS
            )
            assert document[
                "unconditional_same_uid_replacement_safety_claimed"
            ] is False
            assert document["manager_stop_identity_binding_contract"] == (
                probe.MANAGER_STOP_IDENTITY_BINDING
            )
        for document in (
            inner_receipt,
            outer_receipt["inner_observation"],
            outer_receipt,
            seal,
        ):
            assert document["requested_manager_stop_identity_binding"] == (
                probe.MANAGER_STOP_IDENTITY_BINDING
            )
        forged_seal_payload = dict(seal)
        forged_seal_payload.pop("outer_launch_success_seal_id")
        forged_seal_payload[
            "unconditional_same_uid_replacement_safety_claimed"
        ] = True
        forged_seal = probe._self_id_document(
            probe.OUTER_LAUNCH_SUCCESS_SEAL_DOMAIN,
            "outer_launch_success_seal_id",
            forged_seal_payload,
        )
        with pytest.raises(probe.AuthorityError):
            probe.validate_outer_launch_success_seal_document(
                forged_seal,
                outer_attempt=outer_attempt,
                receipt=outer_receipt,
                receipt_raw=receipt_raw,
            )
        assert seal["decision_stage"] == probe.OUTER_RECEIPT_DECISION_STAGE
        assert seal["remaining_after_launch_receipt_publication_ns"] > 0
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("receipt recovery must not relaunch")
        )
        recovered = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=no_relaunch,
            absence_observer=FakeAbsenceObserver(),
        )
        assert recovered == outer_receipt
        assert no_relaunch.calls == []
    assert process.calls[0]["env"] == probe.expected_outer_launch_environment(
        os.geteuid()
    )
    assert process.calls[0]["start_new_session"] is True
    assert process.calls[0]["timeout_seconds"] == probe.OUTER_LAUNCH_TIMEOUT_SECONDS


def test_outer_nonzero_preserves_bounded_streams_and_launch_failure(
    tmp_path: Path,
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def launch_callback(argv):
        return probe.BoundedProcessResult(
            argv, 17, b"bounded stdout", b"bounded stderr", False, False
        )

    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["schema"] == probe.OUTER_LAUNCH_FAILURE_SCHEMA
        assert "SYSTEMD_RUN_NONZERO" in failure["failure_reason"]
        assert base64.b64decode(failure["stdout"]["base64"]) == b"bounded stdout"
        assert base64.b64decode(failure["stderr"]["base64"]) == b"bounded stderr"
        assert failure["same_uid_manager_concurrency_policy_status"] == (
            probe.SAME_UID_MANAGER_CONCURRENCY_POLICY_STATUS
        )
        assert failure[
            "unconditional_same_uid_replacement_safety_claimed"
        ] is False
        assert failure["manager_stop_identity_binding_contract"] == (
            probe.MANAGER_STOP_IDENTITY_BINDING
        )
        assert failure["requested_manager_stop_identity_binding"] == (
            probe.MANAGER_STOP_IDENTITY_UNKNOWN
        )
        assert store.inventory_names(phase="TEST") == frozenset(
            {
                probe.OUTER_LAUNCH_ATTEMPT_NAME,
                probe.OUTER_LAUNCH_FAILURE_NAME,
            }
        )
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == raised.value.failure_document


def test_outer_failure_reason_is_derived_from_retained_process_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def launch_callback(argv):
        return probe.BoundedProcessResult(argv, 17, b"", b"", False, False)

    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        genuine = raised.value.failure_document
        assert "SYSTEMD_RUN_NONZERO" in genuine["failure_reason"]
        payload = dict(genuine)
        payload.pop("outer_launch_failure_id")
        payload["returncode"] = 0
        forged = probe._self_id_document(
            probe.OUTER_LAUNCH_FAILURE_DOMAIN,
            "outer_launch_failure_id",
            payload,
        )
        forged_raw = probe.canonical_json_bytes(forged)
        original_read = store.read_exact

        def read_with_forged_failure(name: str, *, allow_empty: bool = False):
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                return forged_raw
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(store, "read_exact", read_with_forged_failure)
        with pytest.raises(
            probe.AuthorityError,
            match="ordinary failure reason changed",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)


@pytest.mark.parametrize("malformation", ["object", "returncode_bool"])
def test_outer_malformed_process_result_closes_typed_failure(
    tmp_path: Path, malformation: str
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def launch_callback(argv):
        if malformation == "object":
            return object()
        return probe.BoundedProcessResult(
            argv, True, b"", b"", False, False
        )

    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["returncode"] is None
        assert failure["failure_reason"].split("+")[0] == (
            "PROCESS_ADAPTER_ERROR"
        )
        assert failure["failure_components"]["process_adapter_error"][
            "error_type"
        ] == "AuthorityError"
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure


def test_outer_closes_inner_failure_with_zero_byte_partial_attempt(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.ATTEMPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            raise OSError(errno.EIO, "fixture zero-byte inner ATTEMPT")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)

        def launch_callback(argv):
            with pytest.raises(probe.ProbeRunFailure) as inner_failure:
                probe.run_probe_once(
                    authority=authority,
                    external_root_raw=raw,
                    store=store,
                    runtime=FakeRuntime(),
                    environ=environment,
                    monotonic_ns=lambda: 1_000_000,
                )
            return probe.BoundedProcessResult(
                argv,
                1,
                b"",
                (
                    "preflight failure: "
                    f"{inner_failure.value.failure_document['preflight_failure_id']}\n"
                ).encode("ascii"),
                False,
                False,
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["inner_observation"]["state"] == "FAILURE"
        assert failure["inner_observation"]["inner_attempt_exact"] is False
        assert store.read_exact(probe.ATTEMPT_NAME, allow_empty=True) == b""
        assert store.inventory_names(phase="TEST") == frozenset(
            {
                probe.OUTER_LAUNCH_ATTEMPT_NAME,
                probe.ATTEMPT_NAME,
                probe.FAILURE_NAME,
                probe.OUTER_LAUNCH_FAILURE_NAME,
            }
        )
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure


def test_outer_failure_replay_reconstructs_inner_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def launch_callback(argv):
        return probe.BoundedProcessResult(
            argv, 17, b"bounded stdout", b"bounded stderr", False, False
        )

    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        genuine = raised.value.failure_document
        assert genuine["inner_observation"]["state"] == "NONE"
        expected_attempt = probe.build_attempt_document(authority, raw)
        forged_inner = {
            "state": "RECEIPT",
            **probe._same_uid_manager_concurrency_policy_join(),
            "manager_stop_identity_binding_contract": (
                probe.MANAGER_STOP_IDENTITY_BINDING
            ),
            "inner_terminal_manager_stop_requested": True,
            "requested_manager_stop_identity_binding": (
                probe.MANAGER_STOP_IDENTITY_BINDING
            ),
            "inner_attempt_exact": True,
            "inner_probe_attempt_id": expected_attempt["probe_attempt_id"],
            "inner_terminal_id": "f" * 64,
            "artifact_inventory": sorted(
                (
                    genuine["inner_observation"]["artifact_inventory"][0],
                    probe._artifact_fact(
                        probe.ATTEMPT_NAME,
                        probe.canonical_json_bytes(expected_attempt),
                        exact=True,
                    ),
                    probe._artifact_fact(
                        probe.RECEIPT_NAME,
                        b'{"forged":true}',
                        exact=True,
                    ),
                ),
                key=lambda row: row["name"],
            ),
        }
        payload = dict(genuine)
        payload.pop("outer_launch_failure_id")
        payload["inner_observation"] = forged_inner
        payload["requested_manager_stop_identity_binding"] = (
            probe.MANAGER_STOP_IDENTITY_BINDING
        )
        forged = probe._self_id_document(
            probe.OUTER_LAUNCH_FAILURE_DOMAIN,
            "outer_launch_failure_id",
            payload,
        )
        outer_attempt = probe.build_outer_launch_attempt_document(
            authority, raw
        )
        assert probe.validate_outer_launch_failure_document(
            forged,
            outer_attempt=outer_attempt,
            authority=authority,
        ) == forged
        forged_raw = probe.canonical_json_bytes(forged)
        original_read = store.read_exact

        def read_with_forged_failure(name: str, *, allow_empty: bool = False):
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                return forged_raw
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(store, "read_exact", read_with_forged_failure)
        with pytest.raises(
            probe.AuthorityError,
            match="inner observation changed on replay",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("invalid retained failure must not relaunch")
        )
        with pytest.raises(
            probe.AuthorityError,
            match="inner observation changed on replay",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_failure_replay_preserves_transient_inner_observation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    original_observe = probe.observe_inner_launch_state
    calls = 0

    def transient_observation(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError(errno.EIO, "fixture transient inner observation")
        return original_observe(*args, **kwargs)

    monkeypatch.setattr(
        probe, "observe_inner_launch_state", transient_observation
    )

    def launch_callback(argv):
        return probe.BoundedProcessResult(argv, 17, b"", b"", False, False)

    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["inner_observation"] is None
        assert "INNER_OBSERVATION_ERROR" in failure["failure_reason"]
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("retained failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert replayed.value.failure_document == failure
        assert no_relaunch.calls == []


def test_outer_postlaunch_absence_failure_is_typed_residual(tmp_path: Path) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def launch_callback(argv):
        return probe.BoundedProcessResult(argv, 1, b"", b"", False, False)

    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(fail_after=2),
            )
    failure = raised.value.failure_document
    assert "POSTLAUNCH_ABSENCE_UNPROVEN" in failure["failure_reason"]
    assert failure["postlaunch_absence"] is None
    assert failure["unit_absent"] is None
    assert failure["target_absent"] is None
    assert failure["launch_error"]["errno"] == errno.ETIMEDOUT


def test_outer_ordinary_failure_rejects_receipt_inserted_before_bound_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_inventory = store.inventory_names
        original_write = store.write_once
        inserted_receipt = False

        def insert_receipt_before_bound_validation(*, phase: str):
            nonlocal inserted_receipt
            if phase == "OUTER_FAILURE_AUTHORITY" and not inserted_receipt:
                original_write(
                    probe.OUTER_LAUNCH_RECEIPT_NAME,
                    b"{}",
                    token=probe.PublicationOwnershipToken(
                        probe.OUTER_LAUNCH_RECEIPT_NAME
                    ),
                )
                inserted_receipt = True
            return original_inventory(phase=phase)

        monkeypatch.setattr(
            store, "inventory_names", insert_receipt_before_bound_validation
        )

        successful_inner = _successful_inner_callback(
            authority, raw, environment, store
        )

        def nonzero_with_inner_receipt(argv):
            result = successful_inner(argv)
            return probe.BoundedProcessResult(
                argv,
                17,
                result.stdout,
                result.stderr,
                result.timed_out,
                result.output_limit_exceeded,
            )

        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(nonzero_with_inner_receipt),
                absence_observer=FakeAbsenceObserver(),
            )
        assert inserted_receipt is True
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        monkeypatch.setattr(store, "inventory_names", original_inventory)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("uncertain receipt must not relaunch")
        )
        with pytest.raises(probe.OuterReceiptPublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


@pytest.mark.parametrize(
    "failure_stage",
    [
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_CLOSE",
        "AFTER_ROOT_FSYNC",
        "AFTER_READBACK",
    ],
)
def test_outer_launch_failure_exact_checkpoint_fault_recovers_typed_failure(
    tmp_path: Path, failure_stage: str
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    failure_writes = 0

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        nonlocal failure_writes
        if name == probe.OUTER_LAUNCH_FAILURE_NAME and stage == failure_stage:
            failure_writes += 1
            raise OSError(errno.EIO, "fixture exact failure checkpoint")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        failure_raw = store.read_exact(probe.OUTER_LAUNCH_FAILURE_NAME)
        assert probe.canonical_json_bytes(failure) == failure_raw
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure
        assert failure_writes == 1

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("recovered failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert replayed.value.failure_document == failure
        assert store.read_exact(probe.OUTER_LAUNCH_FAILURE_NAME) == failure_raw
        assert failure_writes == 1
        assert no_relaunch.calls == []


@pytest.mark.parametrize(
    ("origin", "expected_reason"),
    [
        ("ordinary", "SYSTEMD_RUN_NONZERO+INNER_NOT_RECEIPT"),
        ("partial_attempt", "LAUNCH_ATTEMPT_PUBLICATION_FAILED"),
        (
            "receipt_pre_o_excl",
            "LAUNCH_RECEIPT_PUBLICATION_FAILED_BEFORE_O_EXCL",
        ),
        (
            "receipt_recovery",
            "OUTER_RECEIPT_DURABILITY_RECOVERY_FAILED",
        ),
        (
            "receipt_postdeadline",
            "OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED",
        ),
        (
            "seal_recovery",
            "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED",
        ),
    ],
)
def test_every_outer_failure_caller_recovers_exact_failure_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
    expected_reason: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    failure_writes = 0
    failure_attempts = 0

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        nonlocal failure_writes
        if (
            origin == "partial_attempt"
            and name == probe.OUTER_LAUNCH_ATTEMPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer attempt")
        if (
            origin == "receipt_recovery"
            and name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer receipt")
        if (
            origin == "seal_recovery"
            and name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer success seal")
        if (
            name == probe.OUTER_LAUNCH_FAILURE_NAME
            and stage == "AFTER_FULL_WRITE"
        ):
            failure_writes += 1
            raise OSError(errno.EIO, "fixture exact outer failure")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once
        original_require = store.require_inventory

        def count_failure_and_reject_receipt(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            nonlocal failure_attempts
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                failure_attempts += 1
            if (
                origin == "receipt_pre_o_excl"
                and name == probe.OUTER_LAUNCH_RECEIPT_NAME
            ):
                raise OSError(errno.EIO, "fixture failure before O_EXCL")
            return original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )

        monkeypatch.setattr(
            store, "write_once", count_failure_and_reject_receipt
        )

        launch_kwargs: dict[str, object] = {}
        if origin == "receipt_postdeadline":
            clock = FakeMonotonicClock()
            entry_ns = clock.now_ns
            deadline_ns = (
                entry_ns + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
            )

            def expire_after_receipt(
                expected_names,
                *,
                phase: str,
                allow_partial_names=frozenset(),
            ):
                rows = original_require(
                    expected_names,
                    phase=phase,
                    allow_partial_names=allow_partial_names,
                )
                if phase == "OUTER_LAUNCH_RECEIPT_PUBLISHED":
                    clock.now_ns = deadline_ns
                return rows

            monkeypatch.setattr(store, "require_inventory", expire_after_receipt)
            launch_kwargs = {
                "monotonic_ns": clock.read,
                "formal_process_entry_ns": entry_ns,
                "deadline_ns": deadline_ns,
            }

        if origin == "ordinary":
            process = FakeLaunchProcess(
                lambda argv: probe.BoundedProcessResult(
                    argv, 17, b"", b"", False, False
                )
            )
        elif origin == "partial_attempt":
            process = FakeLaunchProcess(
                lambda _argv: pytest.fail("partial attempt must not launch")
            )
        else:
            process = FakeLaunchProcess(
                _successful_inner_callback(authority, raw, environment, store)
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
                **launch_kwargs,
            )
        failure = raised.value.failure_document
        assert failure["failure_reason"] == expected_reason
        assert set(failure) == probe.OUTER_LAUNCH_FAILURE_FIELDS
        retained_attempt_raw = store.read_exact(
            probe.OUTER_LAUNCH_ATTEMPT_NAME, allow_empty=True
        )
        assert failure["launch_attempt_observed_exact"] is (
            origin != "partial_attempt"
        )
        assert failure["launch_attempt_recovery_raw_byte_count"] == len(
            retained_attempt_raw
        )
        assert failure["launch_attempt_recovery_raw_sha256"] == (
            hashlib.sha256(retained_attempt_raw).hexdigest()
        )
        failure_raw = store.read_exact(probe.OUTER_LAUNCH_FAILURE_NAME)
        assert probe.canonical_json_bytes(failure) == failure_raw
        assert failure_writes == 1
        assert failure_attempts == 1
        assert store.inventory_names(phase="TEST_FAILURE_FINAL") == frozenset(
            {
                *failure["inventory_before_launch_failure"],
                probe.OUTER_LAUNCH_FAILURE_NAME,
            }
        )
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure

        monkeypatch.setattr(store, "require_inventory", original_require)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("retained failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert replayed.value.failure_document == failure
        assert store.read_exact(probe.OUTER_LAUNCH_FAILURE_NAME) == failure_raw
        assert failure_writes == 1
        assert failure_attempts == 1
        assert no_relaunch.calls == []


@pytest.mark.parametrize(
    "origin",
    [
        "ordinary",
        "partial_attempt",
        "receipt_pre_o_excl",
        "receipt_recovery",
        "receipt_postdeadline",
        "seal_recovery",
    ],
)
def test_every_outer_failure_caller_rejects_terminal_boundary_raw_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            origin == "partial_attempt"
            and name == probe.OUTER_LAUNCH_ATTEMPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer attempt")
        if (
            origin == "receipt_recovery"
            and name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer receipt")
        if (
            origin == "seal_recovery"
            and name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer success seal")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once
        original_require = store.require_inventory
        failure_attempts = 0
        failure_token: probe.PublicationOwnershipToken | None = None
        mutated = False

        def drift_before_failure_pre_open(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            nonlocal failure_attempts, failure_token, mutated
            if (
                origin == "receipt_pre_o_excl"
                and name == probe.OUTER_LAUNCH_RECEIPT_NAME
            ):
                raise OSError(errno.EIO, "fixture receipt pre-O_EXCL failure")
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                failure_attempts += 1
                failure_token = token
                if not mutated:
                    attempt_path = (
                        store.root / probe.OUTER_LAUNCH_ATTEMPT_NAME
                    )
                    before = os.stat(attempt_path, follow_symlinks=False)
                    retained = store.read_exact(
                        probe.OUTER_LAUNCH_ATTEMPT_NAME,
                        allow_empty=True,
                    )
                    replacement = b'{"' if retained == b"{" else b"{"
                    _overwrite_prepare_artifact_same_inode(
                        attempt_path, replacement
                    )
                    after = os.stat(attempt_path, follow_symlinks=False)
                    assert (after.st_dev, after.st_ino) == (
                        before.st_dev,
                        before.st_ino,
                    )
                    mutated = True
            return original_write(
                name,
                artifact_raw,
                token=token,
                pre_open=pre_open,
            )

        monkeypatch.setattr(store, "write_once", drift_before_failure_pre_open)
        launch_kwargs: dict[str, object] = {}
        if origin == "receipt_postdeadline":
            clock = FakeMonotonicClock()
            entry_ns = clock.now_ns
            deadline_ns = (
                entry_ns + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
            )

            def expire_after_receipt(
                expected_names,
                *,
                phase: str,
                allow_partial_names=frozenset(),
            ):
                rows = original_require(
                    expected_names,
                    phase=phase,
                    allow_partial_names=allow_partial_names,
                )
                if phase == "OUTER_LAUNCH_RECEIPT_PUBLISHED":
                    clock.now_ns = deadline_ns
                return rows

            monkeypatch.setattr(store, "require_inventory", expire_after_receipt)
            launch_kwargs = {
                "monotonic_ns": clock.read,
                "formal_process_entry_ns": entry_ns,
                "deadline_ns": deadline_ns,
            }

        if origin == "ordinary":
            process = FakeLaunchProcess(
                lambda argv: probe.BoundedProcessResult(
                    argv, 17, b"", b"", False, False
                )
            )
        elif origin == "partial_attempt":
            process = FakeLaunchProcess(
                lambda _argv: pytest.fail("partial attempt must not launch")
            )
        else:
            process = FakeLaunchProcess(
                _successful_inner_callback(authority, raw, environment, store)
            )

        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
                **launch_kwargs,
            )
        assert mutated is True
        assert failure_attempts == 1
        assert failure_token is not None
        assert failure_token.path_created is False
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        monkeypatch.setattr(store, "write_once", original_write)
        monkeypatch.setattr(store, "require_inventory", original_require)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("uncertain terminal must not relaunch")
        )
        with pytest.raises(probe.PreflightError):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert failure_attempts == 1
        assert no_relaunch.calls == []


def test_outer_failure_pre_open_candidate_validation_is_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once
        original_prepare_stabilize = probe.PrepareJournalStore.stabilize_exact
        original_artifact_stabilize = (
            probe.DurableArtifactStore.stabilize_exact
        )
        original_fsync = probe.os.fsync
        candidate_active = False
        normal_validation_active = False
        candidate_calls = 0
        candidate_stabilizations = 0
        candidate_artifact_stabilizations = 0
        candidate_fsyncs = 0
        normal_validation_fsyncs = 0

        def track_prepare_stabilization(self, name, artifact_raw):
            nonlocal candidate_stabilizations
            if candidate_active:
                candidate_stabilizations += 1
            return original_prepare_stabilize(self, name, artifact_raw)

        def track_artifact_stabilization(self, name, artifact_raw):
            nonlocal candidate_artifact_stabilizations
            if candidate_active:
                candidate_artifact_stabilizations += 1
            return original_artifact_stabilize(self, name, artifact_raw)

        def track_fsync(descriptor):
            nonlocal candidate_fsyncs, normal_validation_fsyncs
            if candidate_active:
                candidate_fsyncs += 1
            if normal_validation_active:
                normal_validation_fsyncs += 1
            return original_fsync(descriptor)

        def mark_candidate_validation(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            if name != probe.OUTER_LAUNCH_FAILURE_NAME or pre_open is None:
                return original_write(
                    name,
                    artifact_raw,
                    token=token,
                    pre_open=pre_open,
                )

            def guarded_pre_open():
                nonlocal candidate_active, candidate_calls
                candidate_calls += 1
                candidate_active = True
                try:
                    pre_open()
                finally:
                    candidate_active = False

            return original_write(
                name,
                artifact_raw,
                token=token,
                pre_open=guarded_pre_open,
            )

        monkeypatch.setattr(
            probe.PrepareJournalStore,
            "stabilize_exact",
            track_prepare_stabilization,
        )
        monkeypatch.setattr(
            probe.DurableArtifactStore,
            "stabilize_exact",
            track_artifact_stabilization,
        )
        monkeypatch.setattr(probe.os, "fsync", track_fsync)
        monkeypatch.setattr(store, "write_once", mark_candidate_validation)
        with pytest.raises(probe.OuterLaunchFailure):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert candidate_calls == 1
        assert candidate_stabilizations == 0
        assert candidate_artifact_stabilizations == 0
        assert candidate_fsyncs == 0

        normal_validation_active = True
        try:
            probe.validate_prepared_authority(
                authority, raw, artifact_store=store
            )
        finally:
            normal_validation_active = False
        assert normal_validation_fsyncs > 0


def test_outer_launch_failure_postreturn_interrupt_recovers_typed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once
        failure_writes = 0

        def write_then_interrupt(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            nonlocal failure_writes
            original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                failure_writes += 1
                raise KeyboardInterrupt("fixture failure post-return interrupt")

        monkeypatch.setattr(store, "write_once", write_then_interrupt)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure
        assert failure_writes == 1

        monkeypatch.setattr(store, "write_once", original_write)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("post-return failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert replayed.value.failure_document == failure
        assert failure_writes == 1
        assert no_relaunch.calls == []


@pytest.mark.parametrize(
    "retained_raw",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"{", id="prefix"),
        pytest.param(b"X", id="corrupt"),
    ],
)
def test_outer_launch_failure_inexact_checkpoint_fault_is_uncertain_on_replay(
    tmp_path: Path, retained_raw: bytes
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    failure_writes = 0

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        nonlocal failure_writes
        if (
            name == probe.OUTER_LAUNCH_FAILURE_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            failure_writes += 1
            if retained_raw:
                assert os.write(descriptor, retained_raw) == len(retained_raw)
            raise OSError(errno.EIO, "fixture inexact failure checkpoint")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert store.read_exact(
            probe.OUTER_LAUNCH_FAILURE_NAME, allow_empty=True
        ) == retained_raw
        assert failure_writes == 1

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("uncertain failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert store.read_exact(
            probe.OUTER_LAUNCH_FAILURE_NAME, allow_empty=True
        ) == retained_raw
        assert failure_writes == 1
        assert no_relaunch.calls == []


def test_outer_launch_failure_before_o_excl_is_uncertain_and_never_relaunches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once
        failure_attempts = 0

        def reject_failure(name, artifact_raw, *, token=None, pre_open=None):
            nonlocal failure_attempts
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                failure_attempts += 1
                raise OSError(errno.EIO, "fixture failure before O_EXCL")
            return original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )

        monkeypatch.setattr(store, "write_once", reject_failure)
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert failure_attempts == 1
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("consumed outer attempt must not relaunch")
        )
        with pytest.raises(probe.ReplayForbidden):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert failure_attempts == 1
        assert no_relaunch.calls == []


def test_outer_launch_failure_exact_recovery_can_resume_after_transient_stabilize_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_FAILURE_NAME
            and stage == "AFTER_FULL_WRITE"
        ):
            raise OSError(errno.EIO, "fixture exact failure checkpoint")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_stabilize = store.stabilize_exact

        def reject_failure_stabilization(name: str, artifact_raw: bytes) -> None:
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                raise OSError(errno.EIO, "fixture transient failure fsync")
            original_stabilize(name, artifact_raw)

        monkeypatch.setattr(
            store, "stabilize_exact", reject_failure_stabilization
        )
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        failure_raw = store.read_exact(probe.OUTER_LAUNCH_FAILURE_NAME)

        monkeypatch.setattr(store, "stabilize_exact", original_stabilize)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("retained failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert probe.canonical_json_bytes(
            replayed.value.failure_document
        ) == failure_raw
        assert no_relaunch.calls == []


def test_outer_launch_failure_exact_recovery_can_resume_after_transient_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_FAILURE_NAME
            and stage == "AFTER_FULL_WRITE"
        ):
            raise OSError(errno.EIO, "fixture exact failure checkpoint")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        reject_once = True

        def reject_first_failure_read(name: str, **kwargs):
            nonlocal reject_once
            if name == probe.OUTER_LAUNCH_FAILURE_NAME and reject_once:
                reject_once = False
                raise OSError(errno.EIO, "fixture transient failure read")
            return original_read(name, **kwargs)

        monkeypatch.setattr(store, "read_exact", reject_first_failure_read)
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )

        monkeypatch.setattr(store, "read_exact", original_read)
        failure_raw = store.read_exact(probe.OUTER_LAUNCH_FAILURE_NAME)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("retained failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert probe.canonical_json_bytes(
            replayed.value.failure_document
        ) == failure_raw
        assert no_relaunch.calls == []


@pytest.mark.parametrize("recover_in_same_call", [True, False])
def test_outer_launch_failure_postwrite_validation_read_is_typed_or_uncertain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recover_in_same_call: bool,
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        original_write = store.write_once
        failure_reads = 0
        failure_writes = 0

        def count_failure_write(name: str, artifact_raw: bytes, **kwargs) -> None:
            nonlocal failure_writes
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                failure_writes += 1
            original_write(name, artifact_raw, **kwargs)

        def reject_postwrite_validation_read(name: str, **kwargs):
            nonlocal failure_reads
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                failure_reads += 1
                if failure_reads == 2 or (
                    not recover_in_same_call and failure_reads >= 2
                ):
                    raise OSError(
                        errno.EIO,
                        "fixture postwrite outer failure validation read",
                    )
            return original_read(name, **kwargs)

        monkeypatch.setattr(store, "write_once", count_failure_write)
        monkeypatch.setattr(
            store, "read_exact", reject_postwrite_validation_read
        )
        expected_exception = (
            probe.OuterLaunchFailure
            if recover_in_same_call
            else probe.OuterLaunchFailurePublicationUncertain
        )
        with pytest.raises(expected_exception) as first:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert failure_writes == 1

        monkeypatch.setattr(store, "read_exact", original_read)
        failure_raw = original_read(probe.OUTER_LAUNCH_FAILURE_NAME)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("retained failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert probe.canonical_json_bytes(
            replayed.value.failure_document
        ) == failure_raw
        if recover_in_same_call:
            assert first.value.failure_document == replayed.value.failure_document
        assert failure_writes == 1
        assert no_relaunch.calls == []


@pytest.mark.parametrize("persistent", [False, True])
def test_outer_launch_failure_exception_write_validation_is_typed_or_uncertain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    persistent: bool,
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    validation_calls = 0
    failure_attempts = 0

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_FAILURE_NAME
            and stage == "AFTER_FULL_WRITE"
        ):
            raise OSError(errno.EIO, "fixture exact failure exception-write")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_validate = probe.validate_outer_launch_failure_state
        original_write = store.write_once

        def validate_with_fault(*args, **kwargs):
            nonlocal validation_calls
            validation_calls += 1
            if validation_calls == 1 or persistent:
                raise OSError(
                    errno.EIO,
                    "fixture exception-write failure validation",
                )
            return original_validate(*args, **kwargs)

        def count_failure_write(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            nonlocal failure_attempts
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                failure_attempts += 1
            return original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )

        monkeypatch.setattr(
            probe, "validate_outer_launch_failure_state", validate_with_fault
        )
        monkeypatch.setattr(store, "write_once", count_failure_write)
        expected_exception = (
            probe.OuterLaunchFailurePublicationUncertain
            if persistent
            else probe.OuterLaunchFailure
        )
        with pytest.raises(expected_exception) as first:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert validation_calls == 2
        assert failure_attempts == 1
        failure_raw = store.read_exact(probe.OUTER_LAUNCH_FAILURE_NAME)

        monkeypatch.setattr(
            probe, "validate_outer_launch_failure_state", original_validate
        )
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("retained failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        if not persistent:
            assert first.value.failure_document == replayed.value.failure_document
        assert probe.canonical_json_bytes(
            replayed.value.failure_document
        ) == failure_raw
        assert failure_attempts == 1
        assert no_relaunch.calls == []


@pytest.mark.parametrize("persistent", [False, True])
def test_outer_launch_failure_clean_write_authority_validation_is_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    persistent: bool,
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_validate = probe.validate_outer_launch_failure_state
        original_write = store.write_once
        validation_calls = 0
        failure_attempts = 0

        def validate_with_authority_fault(*args, **kwargs):
            nonlocal validation_calls
            validation_calls += 1
            if validation_calls == 1 or persistent:
                raise probe.AuthorityError(
                    "fixture clean-write outer failure validation"
                )
            return original_validate(*args, **kwargs)

        def count_failure_write(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            nonlocal failure_attempts
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                failure_attempts += 1
            return original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )

        monkeypatch.setattr(
            probe,
            "validate_outer_launch_failure_state",
            validate_with_authority_fault,
        )
        monkeypatch.setattr(store, "write_once", count_failure_write)
        expected_exception = (
            probe.OuterLaunchFailurePublicationUncertain
            if persistent
            else probe.OuterLaunchFailure
        )
        with pytest.raises(expected_exception) as first:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert validation_calls == 2
        assert failure_attempts == 1

        monkeypatch.setattr(
            probe, "validate_outer_launch_failure_state", original_validate
        )
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("retained failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        if not persistent:
            assert first.value.failure_document == replayed.value.failure_document
        assert failure_attempts == 1
        assert no_relaunch.calls == []


def test_outer_launch_failure_validation_rejects_same_inode_byte_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_require = store.require_inventory
        mutated = False

        def mutate_failure_before_post_rows(
            expected_names,
            *,
            phase: str,
            allow_partial_names=frozenset(),
        ):
            nonlocal mutated
            if (
                phase == "OUTER_FAILURE_AUTHORITY_POST"
                and store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)
                and not mutated
            ):
                path = store.root / probe.OUTER_LAUNCH_FAILURE_NAME
                before = os.stat(path, follow_symlinks=False)
                os.chmod(path, 0o600, follow_symlinks=False)
                descriptor = os.open(
                    path,
                    os.O_WRONLY
                    | os.O_TRUNC
                    | os.O_NOFOLLOW
                    | os.O_CLOEXEC,
                )
                try:
                    assert os.write(descriptor, b"X") == 1
                    os.fchmod(descriptor, 0o400)
                finally:
                    os.close(descriptor)
                after = os.stat(path, follow_symlinks=False)
                assert (after.st_dev, after.st_ino) == (
                    before.st_dev,
                    before.st_ino,
                )
                mutated = True
            return original_require(
                expected_names,
                phase=phase,
                allow_partial_names=allow_partial_names,
            )

        monkeypatch.setattr(
            store, "require_inventory", mutate_failure_before_post_rows
        )
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert mutated is True

        monkeypatch.setattr(store, "require_inventory", original_require)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("drifted failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


@pytest.mark.parametrize(
    ("case", "artifact_name"),
    [
        ("inner_receipt", probe.RECEIPT_NAME),
        ("inner_failure", probe.FAILURE_NAME),
        ("outer_receipt", probe.OUTER_LAUNCH_RECEIPT_NAME),
        ("outer_seal", probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME),
    ],
)
def test_outer_failure_validator_final_rows_precede_every_raw_reread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    artifact_name: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            case == "outer_receipt"
            and name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer receipt")
        if (
            case == "outer_seal"
            and name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer seal")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        if case == "inner_receipt":
            successful_inner = _successful_inner_callback(
                authority, raw, environment, store
            )

            def launch_callback(argv):
                result = successful_inner(argv)
                return probe.BoundedProcessResult(
                    argv,
                    17,
                    result.stdout,
                    result.stderr,
                    result.timed_out,
                    result.output_limit_exceeded,
                )

        elif case == "inner_failure":

            def launch_callback(argv):
                with pytest.raises(probe.ProbeRunFailure):
                    probe.run_probe_once(
                        authority=authority,
                        external_root_raw=raw,
                        store=store,
                        runtime=FakeRuntime(fail_method="inspect_service"),
                        environ=environment,
                        monotonic_ns=lambda: 1_000_000,
                    )
                return probe.BoundedProcessResult(
                    argv, 2, b"", b"", False, False
                )

        else:
            launch_callback = _successful_inner_callback(
                authority, raw, environment, store
            )

        with pytest.raises(probe.OuterLaunchFailure):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )

        original_inventory = store.inventory_names
        mutated = False

        def mutate_after_final_rows(*, phase: str):
            nonlocal mutated
            names = original_inventory(phase=phase)
            if (
                phase == "OUTER_FAILURE_AUTHORITY_POST_POST_READ"
                and not mutated
            ):
                path = store.root / artifact_name
                before = os.stat(path, follow_symlinks=False)
                _overwrite_prepare_artifact_same_inode(path, b'{"')
                after = os.stat(path, follow_symlinks=False)
                assert (after.st_dev, after.st_ino) == (
                    before.st_dev,
                    before.st_ino,
                )
                mutated = True
            return names

        monkeypatch.setattr(store, "inventory_names", mutate_after_final_rows)
        with pytest.raises(
            probe.AuthorityError,
            match="after final inventory rows",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)
        assert mutated is True


@pytest.mark.parametrize("stage", ["AFTER_INITIAL_FCHMOD", "AFTER_FULL_WRITE"])
def test_outer_attempt_publication_fault_closes_without_launch(
    tmp_path: Path, stage: str
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def checkpoint(actual_stage: str, name: str, descriptor: int) -> None:
        if name == probe.OUTER_LAUNCH_ATTEMPT_NAME and actual_stage == stage:
            if stage == "AFTER_INITIAL_FCHMOD":
                assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture outer attempt ambiguity")

    process = FakeLaunchProcess(lambda _argv: pytest.fail("launch must not occur"))
    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
            )
        assert raised.value.failure_document["failure_reason"] == (
            "LAUNCH_ATTEMPT_PUBLICATION_FAILED"
        )
        failure = raised.value.failure_document
        attempt_raw = store.read_exact(
            probe.OUTER_LAUNCH_ATTEMPT_NAME, allow_empty=True
        )
        assert failure["launch_attempt_observed_exact"] is (
            stage == "AFTER_FULL_WRITE"
        )
        assert failure["launch_attempt_recovery_raw_byte_count"] == len(
            attempt_raw
        )
        assert failure["launch_attempt_recovery_raw_sha256"] == (
            hashlib.sha256(attempt_raw).hexdigest()
        )
        assert process.calls == []
        assert store.inventory_names(phase="TEST") == frozenset(
            {
                probe.OUTER_LAUNCH_ATTEMPT_NAME,
                probe.OUTER_LAUNCH_FAILURE_NAME,
            }
        )
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("retained attempt failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert replayed.value.failure_document == failure
        assert replayed.value.failure_document["outer_launch_failure_id"] == (
            failure["outer_launch_failure_id"]
        )
        assert no_relaunch.calls == []


def test_outer_attempt_nonprefix_publication_fault_has_no_typed_failure(
    tmp_path: Path,
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_ATTEMPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"X") == 1
            raise OSError(errno.EIO, "fixture nonprefix outer attempt")

    process = FakeLaunchProcess(lambda _argv: pytest.fail("launch must not occur"))
    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(
            probe.AuthorityError,
            match="neither exact nor a strict canonical prefix",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
            )
        assert process.calls == []
        assert store.read_exact(
            probe.OUTER_LAUNCH_ATTEMPT_NAME, allow_empty=True
        ) == b"X"
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("nonprefix attempt must not relaunch")
        )
        with pytest.raises(probe.ReplayForbidden):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_attempt_unreadable_recovery_has_no_typed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_ATTEMPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer attempt")

    process = FakeLaunchProcess(lambda _argv: pytest.fail("launch must not occur"))
    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact

        def reject_attempt_read(name: str, *, allow_empty: bool = False):
            if name == probe.OUTER_LAUNCH_ATTEMPT_NAME:
                raise OSError(errno.EIO, "fixture unreadable outer attempt")
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(store, "read_exact", reject_attempt_read)
        with pytest.raises(
            probe.AuthorityError,
            match="unavailable for terminal classification",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
            )
        assert process.calls == []
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


def test_outer_attempt_prefix_drift_before_failure_o_excl_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_ATTEMPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer attempt")

    process = FakeLaunchProcess(lambda _argv: pytest.fail("launch must not occur"))
    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once
        drifted = False

        def drift_attempt_then_write(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            nonlocal drifted
            if name == probe.OUTER_LAUNCH_FAILURE_NAME and not drifted:
                path = store.root / probe.OUTER_LAUNCH_ATTEMPT_NAME
                before = os.stat(path, follow_symlinks=False)
                os.chmod(path, 0o600, follow_symlinks=False)
                descriptor = os.open(
                    path,
                    os.O_WRONLY
                    | os.O_TRUNC
                    | os.O_NOFOLLOW
                    | os.O_CLOEXEC,
                )
                try:
                    assert os.write(descriptor, b'{"') == 2
                    os.fchmod(descriptor, 0o400)
                finally:
                    os.close(descriptor)
                after = os.stat(path, follow_symlinks=False)
                assert (after.st_dev, after.st_ino) == (
                    before.st_dev,
                    before.st_ino,
                )
                drifted = True
            return original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )

        monkeypatch.setattr(store, "write_once", drift_attempt_then_write)
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
            )
        assert drifted is True
        assert process.calls == []
        assert store.read_exact(
            probe.OUTER_LAUNCH_ATTEMPT_NAME, allow_empty=True
        ) == b'{"'
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        monkeypatch.setattr(store, "write_once", original_write)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("drifted attempt must not relaunch")
        )
        with pytest.raises(probe.ReplayForbidden):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_attempt_post_write_return_interrupt_closes_without_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    process = FakeLaunchProcess(lambda _argv: pytest.fail("launch must not occur"))
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once

        def write_then_interrupt(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )
            if name == probe.OUTER_LAUNCH_ATTEMPT_NAME:
                raise KeyboardInterrupt("fixture interrupt after LAUNCH_ATTEMPT return")

        monkeypatch.setattr(store, "write_once", write_then_interrupt)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
            )
        assert raised.value.failure_document["failure_reason"] == (
            "LAUNCH_ATTEMPT_PUBLICATION_FAILED"
        )
        assert process.calls == []


def test_outer_partial_attempt_failure_rejects_late_inner_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_ATTEMPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer attempt")

    process = FakeLaunchProcess(lambda _argv: pytest.fail("launch must not occur"))
    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_inventory = store.inventory_names
        original_write = store.write_once
        inserted_attempt = False

        def insert_inner_attempt_before_bound_validation(*, phase: str):
            nonlocal inserted_attempt
            if phase == "OUTER_FAILURE_AUTHORITY" and not inserted_attempt:
                original_write(
                    probe.ATTEMPT_NAME,
                    b"{",
                    token=probe.PublicationOwnershipToken(probe.ATTEMPT_NAME),
                )
                inserted_attempt = True
            return original_inventory(phase=phase)

        monkeypatch.setattr(
            store,
            "inventory_names",
            insert_inner_attempt_before_bound_validation,
        )
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
            )
        assert inserted_attempt is True
        assert process.calls == []
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        monkeypatch.setattr(store, "inventory_names", original_inventory)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("uncertain partial attempt must not relaunch")
        )
        with pytest.raises(
            probe.ForeignArtifactError,
            match="outer prelaunch inventory is illegal",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


@pytest.mark.parametrize(
    "fault_stage",
    [
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_ROOT_FSYNC",
        "AFTER_READBACK",
    ],
)
def test_outer_exact_receipt_fault_recovers_without_launch_failure(
    tmp_path: Path, fault_stage: str
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.OUTER_LAUNCH_RECEIPT_NAME and stage == fault_stage:
            raise KeyboardInterrupt("fixture exact outer receipt async fault")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        def launch_callback(argv):
            receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(receipt) + b"\n",
                b"",
                False,
                False,
            )

        receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=FakeLaunchProcess(launch_callback),
            absence_observer=FakeAbsenceObserver(),
        )
        assert receipt["schema"] == probe.OUTER_LAUNCH_RECEIPT_SCHEMA
        assert store.exists(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


def test_outer_receipt_post_write_return_interrupt_recovers_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once

        def write_then_interrupt(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )
            if name == probe.OUTER_LAUNCH_RECEIPT_NAME:
                raise KeyboardInterrupt("fixture interrupt after LAUNCH_RECEIPT return")

        monkeypatch.setattr(store, "write_once", write_then_interrupt)

        def launch_callback(argv):
            receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(receipt) + b"\n",
                b"",
                False,
                False,
            )

        receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=FakeLaunchProcess(launch_callback),
            absence_observer=FakeAbsenceObserver(),
        )
        assert receipt["schema"] == probe.OUTER_LAUNCH_RECEIPT_SCHEMA
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


def test_outer_exact_success_replay_stabilization_failure_is_uncertain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)

        def launch_callback(argv):
            receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(receipt) + b"\n",
                b"",
                False,
                False,
            )

        receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=FakeLaunchProcess(launch_callback),
            absence_observer=FakeAbsenceObserver(),
        )
        original_stabilize = store.stabilize_exact

        def reject_outer_receipt(name: str, artifact_raw: bytes) -> None:
            if name == probe.OUTER_LAUNCH_RECEIPT_NAME:
                raise OSError(errno.EIO, "fixture persistent launch receipt fsync")
            original_stabilize(name, artifact_raw)

        monkeypatch.setattr(store, "stabilize_exact", reject_outer_receipt)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("uncertain receipt must not relaunch")
        )
        for _ in range(2):
            with pytest.raises(probe.OuterReceiptPublicationUncertain):
                probe.run_outer_launch_once(
                    authority=authority,
                    external_root_raw=raw,
                    store=store,
                    process_adapter=no_relaunch,
                    absence_observer=FakeAbsenceObserver(),
                )
        assert no_relaunch.calls == []
        assert probe.loads_canonical_json(
            store.read_exact(probe.OUTER_LAUNCH_RECEIPT_NAME)
        ) == receipt
        seal_raw = store.read_exact(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert probe.loads_canonical_json(seal_raw)[
            "outer_launch_receipt_id"
        ] == receipt["outer_launch_receipt_id"]
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


def test_outer_postreceipt_deadline_sample_closes_typed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    clock = FakeMonotonicClock()
    entry_ns = clock.now_ns
    deadline_ns = (
        entry_ns + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
    )
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_require = store.require_inventory

        def expire_after_receipt(
            expected_names,
            *,
            phase: str,
            allow_partial_names=frozenset(),
        ):
            rows = original_require(
                expected_names,
                phase=phase,
                allow_partial_names=allow_partial_names,
            )
            if phase == "OUTER_LAUNCH_RECEIPT_PUBLISHED":
                clock.now_ns = deadline_ns
            return rows

        monkeypatch.setattr(store, "require_inventory", expire_after_receipt)
        process = FakeLaunchProcess(
            _successful_inner_callback(authority, raw, environment, store)
        )
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=FakeAbsenceObserver(),
                monotonic_ns=clock.read,
                formal_process_entry_ns=entry_ns,
                deadline_ns=deadline_ns,
            )
        failure = raised.value.failure_document
        assert failure["failure_reason"] == (
            "OUTER_RECEIPT_POSTPUBLICATION_DEADLINE_FAILED"
        )
        assert failure["launch_receipt_publication_completion_claim"] is True
        assert failure["launch_receipt_observed_exact"] is True
        assert failure["launch_receipt_publication_stage_class"] == (
            probe.OUTER_RECEIPT_DECISION_STAGE
        )
        assert failure["launch_receipt_verified_monotonic_ns"] == deadline_ns
        assert failure[
            "remaining_after_launch_receipt_publication_ns"
        ] == 0
        assert failure["failure_components"]["deadline_gate_error"] == (
            failure["launch_error"]
        )
        receipt_raw = store.read_exact(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert failure["launch_receipt_raw_sha256"] == hashlib.sha256(
            receipt_raw
        ).hexdigest()
        assert not store.exists(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        clock.now_ns = entry_ns
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("late receipt failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
                monotonic_ns=clock.read,
                formal_process_entry_ns=entry_ns,
                deadline_ns=deadline_ns,
            )
        assert replayed.value.failure_document == failure
        assert no_relaunch.calls == []


def test_outer_receipt_only_replay_never_recovers_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_complete = probe._complete_outer_success_decision

        def interrupt_before_decision(**_kwargs):
            raise KeyboardInterrupt("fixture receipt-only crash gap")

        monkeypatch.setattr(
            probe, "_complete_outer_success_decision", interrupt_before_decision
        )
        with pytest.raises(KeyboardInterrupt):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert store.exists(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)
        monkeypatch.setattr(
            probe, "_complete_outer_success_decision", original_complete
        )
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("receipt-only replay must not relaunch")
        )
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="lacks its write-once success decision seal",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_deadline_error_reidentification_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    clock = FakeMonotonicClock()
    entry_ns = clock.now_ns
    deadline_ns = (
        entry_ns + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
    )

    def launch(argv):
        clock.advance_seconds(probe.OUTER_PROCESS_TOTAL_BOUND_SECONDS)
        return probe.BoundedProcessResult(argv, 0, b"", b"", False, False)

    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch),
                absence_observer=FakeAbsenceObserver(),
                monotonic_ns=clock.read,
                formal_process_entry_ns=entry_ns,
                deadline_ns=deadline_ns,
            )
        forged_error = probe._error_fact(
            OSError(errno.EIO, "forged deadline component")
        )

        def mutate(payload):
            payload["failure_components"]["deadline_gate_error"] = forged_error
            payload["launch_error"] = forged_error

        _inject_outer_failure_read(
            store,
            monkeypatch,
            _reidentified_outer_failure_raw(
                raised.value.failure_document, mutate
            ),
        )
        with pytest.raises(
            probe.AuthorityError,
            match="deadline component disagrees with its exact timeline",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)


def test_outer_complete_success_context_cannot_be_reidentified_as_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        successful_inner = _successful_inner_callback(
            authority, raw, environment, store
        )

        def nonzero_with_success_context(argv):
            result = successful_inner(argv)
            return probe.BoundedProcessResult(
                argv,
                17,
                result.stdout,
                result.stderr,
                result.timed_out,
                result.output_limit_exceeded,
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    nonzero_with_success_context
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert raised.value.failure_document["failure_reason"] == (
            "SYSTEMD_RUN_NONZERO"
        )

        def mutate(payload):
            payload["returncode"] = 0

        _inject_outer_failure_read(
            store,
            monkeypatch,
            _reidentified_outer_failure_raw(
                raised.value.failure_document, mutate
            ),
        )
        with pytest.raises(
            probe.AuthorityError,
            match="ordinary outer failure reconstructs complete success",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)


def test_outer_process_result_and_adapter_error_cannot_coexist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    lambda argv: probe.BoundedProcessResult(
                        argv, 17, b"", b"", False, False
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        forged_error = probe._error_fact(
            OSError(errno.EIO, "forged adapter error beside a result")
        )

        def mutate(payload):
            payload["failure_components"][
                "process_adapter_error"
            ] = forged_error
            payload["launch_error"] = forged_error

        _inject_outer_failure_read(
            store,
            monkeypatch,
            _reidentified_outer_failure_raw(
                raised.value.failure_document, mutate
            ),
        )
        with pytest.raises(
            probe.AuthorityError,
            match="process result/error acquisition is not exact",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)


@pytest.mark.parametrize("observation", ["attempted", "skipped"])
def test_outer_absence_component_requires_exact_observation_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation: str,
) -> None:
    repository_root = tmp_path / observation
    authority, raw, _environment = _authority(repository_root)
    clock = FakeMonotonicClock()
    entry_ns = clock.now_ns
    deadline_ns = (
        entry_ns + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
    )

    def launch(argv):
        if observation == "skipped":
            clock.advance_seconds(
                probe.FORMAL_TOTAL_CAP_SECONDS
                - probe.OUTER_REQUIRED_AFTER_PROCESS_SECONDS
            )
        return probe.BoundedProcessResult(argv, 17, b"", b"", False, False)

    with _artifact_store(repository_root) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch),
                absence_observer=FakeAbsenceObserver(),
                monotonic_ns=clock.read,
                formal_process_entry_ns=entry_ns,
                deadline_ns=deadline_ns,
            )
        forged_error = probe._error_fact(
            OSError(errno.EIO, "forged absence component")
        )

        def mutate(payload):
            payload["failure_components"][
                "postlaunch_absence_error"
            ] = forged_error
            payload["launch_error"] = forged_error

        _inject_outer_failure_read(
            store,
            monkeypatch,
            _reidentified_outer_failure_raw(
                raised.value.failure_document, mutate
            ),
        )
        message = (
            "postlaunch absence result/error is not exact"
            if observation == "attempted"
            else "skipped absence observation retained a result or error"
        )
        with pytest.raises(probe.AuthorityError, match=message):
            probe.validate_outer_launch_failure_state(store, authority, raw)


def test_outer_partial_receipt_adds_typed_launch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise KeyboardInterrupt("fixture partial outer receipt")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)

        def launch_callback(argv):
            receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(receipt) + b"\n",
                b"",
                False,
                False,
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        assert raised.value.failure_document[
            "launch_receipt_observed_exact"
        ] is False
        assert store.read_exact(
            probe.OUTER_LAUNCH_RECEIPT_NAME, allow_empty=True
        ) == b"{"
        assert store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("typed partial receipt failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure) as replayed:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert replayed.value.failure_document[
            "outer_launch_failure_id"
        ] == raised.value.failure_document["outer_launch_failure_id"]
        assert no_relaunch.calls == []
        genuine = raised.value.failure_document
        payload = dict(genuine)
        payload.pop("outer_launch_failure_id")
        payload["failure_reason"] = "SYSTEMD_RUN_NONZERO"
        forged = probe._self_id_document(
            probe.OUTER_LAUNCH_FAILURE_DOMAIN,
            "outer_launch_failure_id",
            payload,
        )
        forged_raw = probe.canonical_json_bytes(forged)
        original_read = store.read_exact

        def read_with_forged_failure(name: str, *, allow_empty: bool = False):
            if name == probe.OUTER_LAUNCH_FAILURE_NAME:
                return forged_raw
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(store, "read_exact", read_with_forged_failure)
        with pytest.raises(
            probe.AuthorityError,
            match="special reason or receipt ownership changed",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)


def test_outer_corrupt_partial_receipt_never_gets_failure(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"X") == 1
            raise OSError(errno.EIO, "fixture corrupt outer receipt")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="neither exact nor a strict canonical prefix",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert store.read_exact(
            probe.OUTER_LAUNCH_RECEIPT_NAME, allow_empty=True
        ) == b"X"
        assert not store.exists(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("corrupt receipt replay must not relaunch")
        )
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="lacks its write-once success decision seal",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_exact_receipt_with_unavailable_recovery_reads_gets_no_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_FULL_WRITE"
        ):
            raise OSError(errno.EIO, "fixture receipt write after full bytes")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        receipt_reads = 0

        def unavailable_receipt_read(
            name: str, *, allow_empty: bool = False
        ):
            nonlocal receipt_reads
            if name == probe.OUTER_LAUNCH_RECEIPT_NAME:
                receipt_reads += 1
                if receipt_reads <= 2:
                    raise OSError(errno.EIO, "fixture unavailable receipt read")
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(store, "read_exact", unavailable_receipt_read)
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="bytes are unavailable for terminal classification",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert receipt_reads == 2
        monkeypatch.setattr(store, "read_exact", original_read)
        assert store.read_exact(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("receipt-only replay must not relaunch")
        )
        with pytest.raises(probe.OuterReceiptPublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_receipt_classification_binds_last_inventory_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer receipt")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        receipt_reads = 0

        def drift_before_bound_inventory_read(
            name: str, *, allow_empty: bool = False
        ):
            nonlocal receipt_reads
            if name == probe.OUTER_LAUNCH_RECEIPT_NAME:
                receipt_reads += 1
                if receipt_reads == 3:
                    path = store.root / probe.OUTER_LAUNCH_RECEIPT_NAME
                    before = os.stat(path, follow_symlinks=False)
                    os.chmod(path, 0o600, follow_symlinks=False)
                    descriptor = os.open(
                        path,
                        os.O_WRONLY
                        | os.O_TRUNC
                        | os.O_NOFOLLOW
                        | os.O_CLOEXEC,
                    )
                    try:
                        assert os.write(descriptor, b"X") == 1
                        os.fchmod(descriptor, 0o400)
                    finally:
                        os.close(descriptor)
                    after = os.stat(path, follow_symlinks=False)
                    assert (after.st_dev, after.st_ino) == (
                        before.st_dev,
                        before.st_ino,
                    )
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(
            store, "read_exact", drift_before_bound_inventory_read
        )
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="bytes changed after terminal classification",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert receipt_reads == 3
        monkeypatch.setattr(store, "read_exact", original_read)
        assert store.read_exact(
            probe.OUTER_LAUNCH_RECEIPT_NAME, allow_empty=True
        ) == b"X"
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "launch_receipt_publication_completion_claim",
            True,
            "outer receipt recovery stage class or completion claim changed",
        ),
        (
            "launch_receipt_publication_stage_class",
            "AFTER_FULL_WRITE",
            "outer receipt recovery stage class or completion claim changed",
        ),
        (
            "launch_receipt_publication_stage_class",
            "AFTER_OPEN",
            "outer receipt recovery stage class or completion claim changed",
        ),
    ],
)
def test_outer_partial_receipt_cannot_reidentify_publication_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
    message: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer receipt")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        genuine = raised.value.failure_document
        assert genuine["launch_receipt_publication_completion_claim"] is None
        assert genuine["launch_receipt_observed_exact"] is False

        def mutate(payload):
            payload[field] = value

        _inject_outer_failure_read(
            store,
            monkeypatch,
            _reidentified_outer_failure_raw(genuine, mutate),
        )
        with pytest.raises(probe.AuthorityError, match=message):
            probe.validate_outer_launch_failure_state(store, authority, raw)


@pytest.mark.parametrize(
    ("forged_stage", "forged_completed", "message"),
    [
        (
            "AFTER_READBACK",
            False,
            "outer receipt recovery stage class or completion claim changed",
        ),
        (
            probe.OUTER_RECEIPT_POST_RETURN_STAGE,
            True,
            "outer receipt recovery stage class or completion claim changed",
        ),
    ],
)
def test_outer_exact_receipt_cannot_reidentify_stage_or_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forged_stage: str,
    forged_completed: bool,
    message: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_RECEIPT_NAME
            and stage == "AFTER_FULL_WRITE"
        ):
            raise OSError(errno.EIO, "fixture exact outer receipt write")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        receipt_reads = 0

        def fail_first_receipt_recovery_read(
            name: str, *, allow_empty: bool = False
        ):
            nonlocal receipt_reads
            if name == probe.OUTER_LAUNCH_RECEIPT_NAME:
                receipt_reads += 1
                if receipt_reads == 1:
                    raise OSError(errno.EIO, "fixture receipt recovery read")
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(
            store, "read_exact", fail_first_receipt_recovery_read
        )
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        genuine = raised.value.failure_document
        assert genuine["launch_receipt_publication_stage_class"] == (
            probe.OUTER_EXACT_BYTES_RECOVERY_STAGE
        )
        assert genuine["launch_receipt_publication_completion_claim"] is None
        assert genuine["launch_receipt_observed_exact"] is True
        monkeypatch.setattr(store, "read_exact", original_read)

        def mutate(payload):
            payload["launch_receipt_publication_stage_class"] = forged_stage
            payload["launch_receipt_publication_completion_claim"] = (
                forged_completed
            )

        _inject_outer_failure_read(
            store,
            monkeypatch,
            _reidentified_outer_failure_raw(genuine, mutate),
        )
        with pytest.raises(probe.AuthorityError, match=message):
            probe.validate_outer_launch_failure_state(store, authority, raw)


@pytest.mark.parametrize(
    "internal_stage",
    [
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_CLOSE",
        "AFTER_ROOT_FSYNC",
        "AFTER_READBACK",
    ],
)
def test_outer_exact_receipt_internal_stages_collapse_to_verifiable_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    internal_stage: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.OUTER_LAUNCH_RECEIPT_NAME and stage == internal_stage:
            raise OSError(errno.EIO, "fixture internal receipt checkpoint")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_stabilize = store.stabilize_exact

        def reject_receipt_recovery_stabilization(name: str, artifact_raw: bytes):
            if name == probe.OUTER_LAUNCH_RECEIPT_NAME:
                raise OSError(errno.ESTALE, "fixture receipt stabilization")
            return original_stabilize(name, artifact_raw)

        monkeypatch.setattr(
            store, "stabilize_exact", reject_receipt_recovery_stabilization
        )
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["launch_receipt_publication_stage_class"] == (
            probe.OUTER_EXACT_BYTES_RECOVERY_STAGE
        )
        assert failure["launch_receipt_publication_completion_claim"] is None
        assert failure["launch_receipt_observed_exact"] is True
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure


def test_outer_postreturn_receipt_failure_uses_verifiable_exact_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    publication_error = OSError(
        errno.EIO, "fixture post-return receipt inventory failure"
    )
    recovery_error = OSError(
        errno.ESTALE, "fixture post-return receipt recovery failure"
    )
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_require = store.require_inventory

        def fail_postreturn_receipt_inventories(
            expected_names,
            *,
            phase: str,
            allow_partial_names=frozenset(),
        ):
            if phase == "OUTER_LAUNCH_RECEIPT_PUBLISHED":
                raise publication_error
            if phase == "OUTER_LAUNCH_RECEIPT_RECOVERED":
                raise recovery_error
            return original_require(
                expected_names,
                phase=phase,
                allow_partial_names=allow_partial_names,
            )

        monkeypatch.setattr(
            store, "require_inventory", fail_postreturn_receipt_inventories
        )
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["launch_receipt_publication_stage_class"] == (
            probe.OUTER_EXACT_BYTES_RECOVERY_STAGE
        )
        assert failure["launch_receipt_publication_completion_claim"] is None
        assert failure["launch_receipt_observed_exact"] is True
        assert failure["launch_receipt_recovery_error"] == (
            probe._error_fact(recovery_error)
        )
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("post-return failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_receipt_pre_o_excl_failure_rejects_late_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once
        captured_receipt_raw: bytes | None = None
        inserted_receipt = False

        def fail_receipt_then_insert_before_failure(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            nonlocal captured_receipt_raw, inserted_receipt
            if name == probe.OUTER_LAUNCH_RECEIPT_NAME:
                captured_receipt_raw = artifact_raw
                raise OSError(
                    errno.EIO, "fixture receipt failure before O_EXCL"
                )
            if name == probe.OUTER_LAUNCH_FAILURE_NAME and not inserted_receipt:
                assert captured_receipt_raw is not None
                original_write(
                    probe.OUTER_LAUNCH_RECEIPT_NAME,
                    captured_receipt_raw,
                    token=probe.PublicationOwnershipToken(
                        probe.OUTER_LAUNCH_RECEIPT_NAME
                    ),
                )
                inserted_receipt = True
            return original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )

        monkeypatch.setattr(
            store, "write_once", fail_receipt_then_insert_before_failure
        )
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert inserted_receipt is True
        assert store.exists(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        monkeypatch.setattr(store, "write_once", original_write)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("uncertain receipt must not relaunch")
        )
        with pytest.raises(probe.OuterReceiptPublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_success_seal_failure_before_o_excl_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once

        def reject_seal(name, artifact_raw, *, token=None, pre_open=None):
            if name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME:
                raise OSError(errno.EIO, "fixture seal failure before O_EXCL")
            return original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )

        monkeypatch.setattr(store, "write_once", reject_seal)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["failure_reason"] == (
            "OUTER_SUCCESS_SEAL_PUBLICATION_FAILED_BEFORE_O_EXCL"
        )
        assert failure["launch_success_seal_path_created"] is False
        assert (
            failure["launch_success_seal_publication_completion_claim"]
            is False
        )
        assert failure["launch_success_seal_publication_stage_class"] is None
        assert failure["launch_success_seal_observed_exact"] is False
        assert store.exists(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure


def test_outer_partial_success_seal_failure_is_strict_prefix_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial success seal")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        failure = raised.value.failure_document
        assert failure["failure_reason"] == (
            "OUTER_SUCCESS_SEAL_DURABILITY_RECOVERY_FAILED"
        )
        assert failure["launch_success_seal_path_created"] is True
        assert (
            failure["launch_success_seal_publication_completion_claim"]
            is None
        )
        assert failure["launch_success_seal_publication_stage_class"] == (
            probe.OUTER_STRICT_PREFIX_RECOVERY_STAGE
        )
        assert failure["launch_success_seal_observed_exact"] is False
        assert store.read_exact(
            probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME, allow_empty=True
        ) == b"{"
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("partial seal failure must not relaunch")
        )
        with pytest.raises(probe.OuterLaunchFailure):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []

        outer_attempt = probe.build_outer_launch_attempt_document(
            authority, raw
        )
        receipt_raw = store.read_exact(probe.OUTER_LAUNCH_RECEIPT_NAME)
        receipt = probe.loads_canonical_json(receipt_raw)
        exact_seal_raw = probe.canonical_json_bytes(
            probe._build_outer_launch_success_seal(
                outer_attempt,
                receipt,
                receipt_raw,
                verified_monotonic_ns=failure[
                    "launch_receipt_verified_monotonic_ns"
                ],
                remaining_after_publication_ns=failure[
                    "remaining_after_launch_receipt_publication_ns"
                ],
            )
        )
        original_read = store.read_exact

        def read_exact_seal(name: str, *, allow_empty: bool = False):
            if name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME:
                return exact_seal_raw
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(store, "read_exact", read_exact_seal)
        with pytest.raises(
            probe.AuthorityError,
            match="outer success-seal recovery raw identity changed",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)


def test_outer_partial_success_seal_cannot_reidentify_publication_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial success seal")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        genuine = raised.value.failure_document
        def mutate(payload):
            payload["launch_success_seal_publication_stage_class"] = (
                "AFTER_OPEN"
            )

        _inject_outer_failure_read(
            store,
            monkeypatch,
            _reidentified_outer_failure_raw(genuine, mutate),
        )
        with pytest.raises(
            probe.AuthorityError,
            match="partial success-seal recovery facts changed",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)


def test_outer_exact_success_seal_survives_postreturn_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once

        def interrupt_after_seal(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )
            if name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME:
                raise KeyboardInterrupt("fixture interrupt after exact seal")

        monkeypatch.setattr(store, "write_once", interrupt_after_seal)
        with pytest.raises(probe.OuterReceiptPublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert store.exists(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)
        monkeypatch.setattr(store, "write_once", original_write)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("exact sealed replay must not relaunch")
        )
        receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=no_relaunch,
            absence_observer=FakeAbsenceObserver(),
        )
        assert receipt["schema"] == probe.OUTER_LAUNCH_RECEIPT_SCHEMA
        assert no_relaunch.calls == []


def test_outer_exact_seal_after_transient_recovery_read_never_gets_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_FULL_WRITE"
        ):
            raise OSError(errno.EIO, "fixture seal write after full bytes")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        seal_reads = 0

        def transient_seal_read(name: str, *, allow_empty: bool = False):
            nonlocal seal_reads
            if name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME:
                seal_reads += 1
                if seal_reads == 1:
                    raise OSError(errno.EIO, "fixture transient seal read")
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(store, "read_exact", transient_seal_read)
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="exact success decision seal appeared",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert seal_reads == 2
        assert store.exists(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        monkeypatch.setattr(store, "read_exact", original_read)
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("exact sealed replay must not relaunch")
        )
        receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=no_relaunch,
            absence_observer=FakeAbsenceObserver(),
        )
        assert receipt["schema"] == probe.OUTER_LAUNCH_RECEIPT_SCHEMA
        assert no_relaunch.calls == []


def test_outer_corrupt_partial_success_seal_never_gets_failure(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"X") == 1
            raise OSError(errno.EIO, "fixture corrupt success seal")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="neither exact nor a strict canonical prefix",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert store.read_exact(
            probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME, allow_empty=True
        ) == b"X"
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("corrupt sealed replay must not relaunch")
        )
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="retained success seal is not exact enough",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_exact_seal_with_unavailable_recovery_reads_gets_no_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_FULL_WRITE"
        ):
            raise OSError(errno.EIO, "fixture seal write after full bytes")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        seal_reads = 0

        def unavailable_seal_read(name: str, *, allow_empty: bool = False):
            nonlocal seal_reads
            if name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME:
                seal_reads += 1
                if seal_reads <= 2:
                    raise OSError(errno.EIO, "fixture unavailable seal read")
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(store, "read_exact", unavailable_seal_read)
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="bytes are unavailable for terminal classification",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert seal_reads == 2
        monkeypatch.setattr(store, "read_exact", original_read)
        assert store.read_exact(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("exact sealed replay must not relaunch")
        )
        receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=no_relaunch,
            absence_observer=FakeAbsenceObserver(),
        )
        assert receipt["schema"] == probe.OUTER_LAUNCH_RECEIPT_SCHEMA
        assert no_relaunch.calls == []


def test_outer_success_seal_classification_binds_last_inventory_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial success seal")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        seal_reads = 0

        def drift_before_bound_inventory_read(
            name: str, *, allow_empty: bool = False
        ):
            nonlocal seal_reads
            if name == probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME:
                seal_reads += 1
                if seal_reads == 3:
                    path = store.root / probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME
                    before = os.stat(path, follow_symlinks=False)
                    os.chmod(path, 0o600, follow_symlinks=False)
                    descriptor = os.open(
                        path,
                        os.O_WRONLY
                        | os.O_TRUNC
                        | os.O_NOFOLLOW
                        | os.O_CLOEXEC,
                    )
                    try:
                        assert os.write(descriptor, b"X") == 1
                        os.fchmod(descriptor, 0o400)
                    finally:
                        os.close(descriptor)
                    after = os.stat(path, follow_symlinks=False)
                    assert (after.st_dev, after.st_ino) == (
                        before.st_dev,
                        before.st_ino,
                    )
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(
            store, "read_exact", drift_before_bound_inventory_read
        )
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="bytes changed after terminal classification",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert seal_reads == 3
        monkeypatch.setattr(store, "read_exact", original_read)
        assert store.read_exact(
            probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME, allow_empty=True
        ) == b"X"
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


@pytest.mark.parametrize(
    "terminal_name",
    [
        probe.OUTER_LAUNCH_RECEIPT_NAME,
        probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME,
    ],
)
def test_outer_terminal_classification_rechecks_after_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal_name: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == terminal_name and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer terminal")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_read = store.read_exact
        terminal_reads = 0
        inventory_terminal_seen = False
        mutated = False

        def drift_after_inventory_terminal_row(
            name: str, *, allow_empty: bool = False
        ):
            nonlocal terminal_reads, inventory_terminal_seen, mutated
            if name == terminal_name:
                terminal_reads += 1
                retained = original_read(name, allow_empty=allow_empty)
                if terminal_reads == 3:
                    inventory_terminal_seen = True
                return retained
            if (
                name == probe.RECEIPT_NAME
                and inventory_terminal_seen
                and not mutated
            ):
                path = store.root / terminal_name
                before = os.stat(path, follow_symlinks=False)
                os.chmod(path, 0o600, follow_symlinks=False)
                descriptor = os.open(
                    path,
                    os.O_WRONLY
                    | os.O_TRUNC
                    | os.O_NOFOLLOW
                    | os.O_CLOEXEC,
                )
                try:
                    assert os.write(descriptor, b"X") == 1
                    os.fchmod(descriptor, 0o400)
                finally:
                    os.close(descriptor)
                after = os.stat(path, follow_symlinks=False)
                assert (after.st_dev, after.st_ino) == (
                    before.st_dev,
                    before.st_ino,
                )
                mutated = True
            return original_read(name, allow_empty=allow_empty)

        monkeypatch.setattr(
            store, "read_exact", drift_after_inventory_terminal_row
        )
        with pytest.raises(
            probe.OuterReceiptPublicationUncertain,
            match="bytes changed after bound inventory readback",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert terminal_reads == 4
        assert mutated is True
        monkeypatch.setattr(store, "read_exact", original_read)
        assert store.read_exact(terminal_name, allow_empty=True) == b"X"
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


@pytest.mark.parametrize(
    "terminal_name",
    [
        probe.OUTER_LAUNCH_RECEIPT_NAME,
        probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME,
    ],
)
def test_outer_failure_rejects_classified_raw_drift_before_failure_o_excl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal_name: str,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == terminal_name and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial outer terminal")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        original_write = store.write_once
        mutated = False

        def mutate_before_failure_o_excl(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            nonlocal mutated
            if name == probe.OUTER_LAUNCH_FAILURE_NAME and not mutated:
                path = store.root / terminal_name
                before = os.stat(path, follow_symlinks=False)
                os.chmod(path, 0o600, follow_symlinks=False)
                descriptor = os.open(
                    path,
                    os.O_WRONLY
                    | os.O_TRUNC
                    | os.O_NOFOLLOW
                    | os.O_CLOEXEC,
                )
                try:
                    assert os.write(descriptor, b'{"') == 2
                    os.fchmod(descriptor, 0o400)
                finally:
                    os.close(descriptor)
                after = os.stat(path, follow_symlinks=False)
                assert (after.st_dev, after.st_ino) == (
                    before.st_dev,
                    before.st_ino,
                )
                mutated = True
            return original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )

        monkeypatch.setattr(store, "write_once", mutate_before_failure_o_excl)
        with pytest.raises(probe.OuterLaunchFailurePublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
            )
        assert mutated is True
        monkeypatch.setattr(store, "write_once", original_write)
        assert store.read_exact(terminal_name, allow_empty=True) == b'{"'
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)

        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("uncertain terminal must not relaunch")
        )
        with pytest.raises(probe.OuterReceiptPublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
            )
        assert no_relaunch.calls == []


def test_outer_clock_rollback_cannot_publish_validator_invalid_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    clock = FakeMonotonicClock()
    entry_ns = clock.now_ns
    deadline_ns = (
        entry_ns + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
    )
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original_require = store.require_inventory

        def roll_back_after_receipt(
            expected_names,
            *,
            phase: str,
            allow_partial_names=frozenset(),
        ):
            rows = original_require(
                expected_names,
                phase=phase,
                allow_partial_names=allow_partial_names,
            )
            if phase == "OUTER_LAUNCH_RECEIPT_PUBLISHED":
                clock.now_ns = entry_ns - 1
            return rows

        monkeypatch.setattr(store, "require_inventory", roll_back_after_receipt)
        with pytest.raises(
            probe.AuthorityError,
            match="outer success-seal decision input changed",
        ):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(
                    _successful_inner_callback(
                        authority, raw, environment, store
                    )
                ),
                absence_observer=FakeAbsenceObserver(),
                monotonic_ns=clock.read,
                formal_process_entry_ns=entry_ns,
                deadline_ns=deadline_ns,
            )
        assert store.exists(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_SUCCESS_SEAL_NAME)
        assert not store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)
        clock.now_ns = entry_ns
        no_relaunch = FakeLaunchProcess(
            lambda _argv: pytest.fail("rollback receipt-only state must not relaunch")
        )
        with pytest.raises(probe.OuterReceiptPublicationUncertain):
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=no_relaunch,
                absence_observer=FakeAbsenceObserver(),
                monotonic_ns=clock.read,
                formal_process_entry_ns=entry_ns,
                deadline_ns=deadline_ns,
            )
        assert no_relaunch.calls == []


def test_outer_closes_inner_partial_receipt_without_inner_failure(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.RECEIPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            raise OSError(errno.EIO, "fixture empty receipt")

    with _artifact_store(tmp_path, checkpoint=checkpoint) as store:
        _seed_prepared(store, authority, raw)
        def launch_callback(argv):
            with pytest.raises(probe.ReceiptPublicationUncertain):
                probe.run_probe_once(
                    authority=authority,
                    external_root_raw=raw,
                    store=store,
                    runtime=FakeRuntime(),
                    environ=environment,
                    monotonic_ns=lambda: 1_000_000,
                )
            return probe.BoundedProcessResult(
                argv, 2, b"", b"inner authority failure\n", False, False
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=FakeAbsenceObserver(),
            )
        assert raised.value.failure_document["inner_observation"]["state"] == (
            "RECEIPT_PARTIAL"
        )
        assert not store.exists(probe.FAILURE_NAME)
        assert store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)


def test_bounded_subprocess_adapter_caps_stdout_without_system_effects() -> None:
    result = probe.BoundedSubprocessAdapter().run(
        (
            "/usr/bin/python3",
            "-c",
            "import sys; sys.stdout.buffer.write(b'x' * 4096)",
        ),
        timeout_seconds=2,
        stdout_cap=32,
        stderr_cap=32,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert len(result.stdout) == 32
    assert result.output_limit_exceeded is True


def test_bounded_subprocess_continuous_writer_cannot_starve_kill_and_reap() -> None:
    started = probe.time.monotonic()
    result = probe.BoundedSubprocessAdapter().run(
        (
            "/usr/bin/python3",
            "-c",
            (
                "import os, signal\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                "block = b'x' * 65536\n"
                "while True:\n"
                "    os.write(1, block)\n"
            ),
        ),
        timeout_seconds=8,
        stdout_cap=4096,
        stderr_cap=32,
        env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        start_new_session=True,
    )
    elapsed = probe.time.monotonic() - started
    assert elapsed < 4
    assert result.returncode == -probe.signal.SIGKILL
    assert result.timed_out is False
    assert result.output_limit_exceeded is True
    assert result.stdout == b"x" * 4096
    assert result.stderr == b""


@pytest.mark.parametrize(
    ("fault_api", "fault_call"),
    (("set_blocking", 1), ("set_blocking", 2), ("register", 1), ("register", 2)),
)
def test_bounded_subprocess_setup_fault_kills_reaps_and_closes_pipes(
    monkeypatch: pytest.MonkeyPatch, fault_api: str, fault_call: int,
) -> None:
    real_popen = probe.subprocess.Popen
    real_set_blocking = probe.os.set_blocking
    real_poll = probe.select.poll
    children = []
    set_blocking_calls = 0
    register_calls = 0

    def capture_child(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    def maybe_fail_set_blocking(descriptor, blocking) -> None:
        nonlocal set_blocking_calls
        set_blocking_calls += 1
        if fault_api == "set_blocking" and set_blocking_calls == fault_call:
            raise OSError(errno.EIO, "injected set_blocking failure")
        real_set_blocking(descriptor, blocking)

    class FailingPoller:
        def __init__(self) -> None:
            self.inner = real_poll()

        def register(self, descriptor, events) -> None:
            nonlocal register_calls
            register_calls += 1
            if fault_api == "register" and register_calls == fault_call:
                raise OSError(errno.EIO, "injected poll registration failure")
            self.inner.register(descriptor, events)

        def unregister(self, descriptor) -> None:
            self.inner.unregister(descriptor)

    monkeypatch.setattr(probe.subprocess, "Popen", capture_child)
    monkeypatch.setattr(probe.os, "set_blocking", maybe_fail_set_blocking)
    monkeypatch.setattr(probe.select, "poll", FailingPoller)
    with pytest.raises(probe.AuthorityError, match="setup failed"):
        probe.BoundedSubprocessAdapter().run(
            ("/usr/bin/python3", "-c", "import time; time.sleep(60)"),
            timeout_seconds=8,
            stdout_cap=32,
            stderr_cap=32,
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True,
        )
    assert len(children) == 1
    child = children[0]
    assert child.poll() is not None
    assert child.stdout is not None and child.stdout.closed
    assert child.stderr is not None and child.stderr.closed


@pytest.mark.parametrize("fault_api", ("poll", "read"))
def test_bounded_subprocess_runtime_fault_kills_reaps_and_closes_pipes(
    monkeypatch: pytest.MonkeyPatch, fault_api: str,
) -> None:
    real_popen = probe.subprocess.Popen
    real_poll = probe.select.poll
    real_read = probe.os.read
    children = []
    runtime_pipe_fds = set()

    def capture_child(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        assert child.stdout is not None and child.stderr is not None
        runtime_pipe_fds.update((child.stdout.fileno(), child.stderr.fileno()))
        return child

    class FailingPoller:
        def __init__(self) -> None:
            self.inner = real_poll()

        def register(self, descriptor, events) -> None:
            self.inner.register(descriptor, events)

        def unregister(self, descriptor) -> None:
            self.inner.unregister(descriptor)

        def poll(self, timeout_ms):
            if fault_api == "poll":
                raise OSError(errno.EIO, "injected runtime poll failure")
            return self.inner.poll(timeout_ms)

    def maybe_fail_read(descriptor, size):
        if fault_api == "read" and descriptor in runtime_pipe_fds:
            raise OSError(errno.EIO, "injected runtime read failure")
        return real_read(descriptor, size)

    monkeypatch.setattr(probe.subprocess, "Popen", capture_child)
    monkeypatch.setattr(probe.select, "poll", FailingPoller)
    monkeypatch.setattr(probe.os, "read", maybe_fail_read)
    with pytest.raises(probe.AuthorityError, match="supervision failed"):
        probe.BoundedSubprocessAdapter().run(
            ("/usr/bin/python3", "-c", "import time; time.sleep(60)"),
            timeout_seconds=8,
            stdout_cap=32,
            stderr_cap=32,
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True,
        )
    assert len(children) == 1
    child = children[0]
    assert child.poll() is not None
    assert child.stdout is not None and child.stdout.closed
    assert child.stderr is not None and child.stderr.closed


def test_bounded_subprocess_drain_close_fault_contains_child_and_pipes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_popen = probe.subprocess.Popen
    children = []

    class FailFirstClose:
        def __init__(self, stream) -> None:
            self.stream = stream
            self.failed = False

        def fileno(self) -> int:
            return self.stream.fileno()

        def close(self) -> None:
            if not self.failed:
                self.failed = True
                raise OSError(errno.EIO, "injected drain close failure")
            self.stream.close()

        @property
        def closed(self) -> bool:
            return self.stream.closed

    def capture_child(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        assert child.stdout is not None
        child.stdout = FailFirstClose(child.stdout)
        children.append(child)
        return child

    monkeypatch.setattr(probe.subprocess, "Popen", capture_child)
    with pytest.raises(probe.AuthorityError, match="supervision failed"):
        probe.BoundedSubprocessAdapter().run(
            ("/usr/bin/python3", "-c", "pass"),
            timeout_seconds=8,
            stdout_cap=32,
            stderr_cap=32,
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True,
        )
    assert len(children) == 1
    child = children[0]
    assert child.poll() is not None
    assert child.stdout is not None and child.stdout.closed
    assert child.stderr is not None and child.stderr.closed


def test_bounded_subprocess_runtime_signal_fault_contains_child_and_pipes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_popen = probe.subprocess.Popen
    real_killpg = probe.os.killpg
    children = []
    killpg_calls = 0

    def capture_child(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    def fail_first_killpg(pid, sig) -> None:
        nonlocal killpg_calls
        killpg_calls += 1
        if killpg_calls == 1:
            raise OSError(errno.EIO, "injected runtime signal failure")
        real_killpg(pid, sig)

    monkeypatch.setattr(probe.subprocess, "Popen", capture_child)
    monkeypatch.setattr(probe.os, "killpg", fail_first_killpg)
    with pytest.raises(probe.AuthorityError, match="supervision failed"):
        probe.BoundedSubprocessAdapter().run(
            (
                "/usr/bin/python3",
                "-c",
                "import sys; sys.stdout.buffer.write(b'x' * 4096)",
            ),
            timeout_seconds=8,
            stdout_cap=32,
            stderr_cap=32,
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True,
        )
    assert len(children) == 1
    child = children[0]
    assert child.poll() is not None
    assert child.stdout is not None and child.stdout.closed
    assert child.stderr is not None and child.stderr.closed


def test_bounded_subprocess_setup_fault_reports_final_group_kill_uncertainty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_popen = probe.subprocess.Popen
    real_killpg = probe.os.killpg
    children = []
    killpg_calls = 0

    def capture_child(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    def fail_final_killpg(pid, sig) -> None:
        nonlocal killpg_calls
        killpg_calls += 1
        if killpg_calls == 1:
            real_killpg(pid, sig)
            return
        raise OSError(errno.EIO, "injected final killpg failure")

    class FailingPoller:
        def register(self, _descriptor, _events) -> None:
            raise OSError(errno.EIO, "injected setup failure")

        def unregister(self, _descriptor) -> None:
            return None

    monkeypatch.setattr(probe.subprocess, "Popen", capture_child)
    monkeypatch.setattr(probe.os, "killpg", fail_final_killpg)
    monkeypatch.setattr(probe.select, "poll", FailingPoller)
    with pytest.raises(probe.AuthorityError, match="setup failure cleanup failed") as caught:
        probe.BoundedSubprocessAdapter().run(
            ("/usr/bin/python3", "-c", "import time; time.sleep(60)"),
            timeout_seconds=8,
            stdout_cap=32,
            stderr_cap=32,
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True,
        )
    assert "containment or close was uncertain" in str(caught.value.__cause__)
    assert len(children) == 1 and children[0].poll() is not None
    assert children[0].stdout is not None and children[0].stdout.closed
    assert children[0].stderr is not None and children[0].stderr.closed


def test_formal_main_routes_three_exact_modes_without_effects(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        probe,
        "validate_runtime_contract",
        lambda mode: calls.append(f"runtime:{mode}"),
    )
    monkeypatch.setattr(
        probe,
        "run_prepare_mode",
        lambda **_kwargs: (calls.append("prepare"), {"mode": "prepare"})[1],
    )
    monkeypatch.setattr(
        probe,
        "run_launch_mode",
        lambda **_kwargs: (calls.append("launch"), {"mode": "launch"})[1],
    )
    monkeypatch.setattr(
        probe,
        "run_probe_mode",
        lambda **_kwargs: (calls.append("probe"), {"mode": "probe"})[1],
    )
    for argument, expected in (
        ("--prepare", "prepare"),
        ("--launch", "launch"),
        ("--probe", "probe"),
    ):
        assert probe.main([argument]) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        assert captured.out == f'{{"mode":"{expected}"}}\n'
    assert calls == [
        "runtime:--prepare",
        "prepare",
        "runtime:--launch",
        "launch",
        "runtime:--probe",
        "probe",
    ]
    assert probe.main(["--launch", "--probe"]) == 2


def test_handshake_failure_uses_pidfd_kill_reap_and_close_cleanup(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    runtime = FakeRuntime(fail_method="receive_handshake")
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure):
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
    assert runtime.calls.count("kill_child") == 1
    assert runtime.calls.count("reap_cleanup") == 1
    assert runtime.calls.count("close_child") == 1


def test_runtime_contract_is_exact_for_all_three_modes_and_rejects_drift() -> None:
    flags = SimpleNamespace(
        isolated=1,
        no_site=1,
        no_user_site=1,
        dont_write_bytecode=1,
    )
    probe_environment = probe.expected_clean_environment(
        "/tmp/external-root.json", "a" * 64
    )
    cases = (
        ("--prepare", probe.expected_prepare_environment()),
        ("--launch", probe.expected_outer_launch_environment(os.geteuid())),
        ("--probe", probe_environment),
    )
    for mode, environment in cases:
        result = probe.validate_runtime_contract(
            mode,
            environ=environment,
            executable=probe.PYTHON_BINARY,
            flags=flags,
            orig_argv=[
                probe.PYTHON_BINARY,
                "-I",
                "-S",
                "-B",
                str(SCRIPT.resolve()),
                mode,
            ],
            source_path=SCRIPT,
            umask_observer=lambda: 0o077,
        )
        assert result["environment"] == environment
        assert result["umask"] == 0o077
    with pytest.raises(probe.AuthorityError):
        probe.validate_runtime_contract(
            "--launch",
            environ={
                **probe.expected_outer_launch_environment(os.geteuid()),
                "GIT_DIR": "/tmp/forbidden",
            },
            executable=probe.PYTHON_BINARY,
            flags=flags,
            orig_argv=[
                probe.PYTHON_BINARY,
                "-I",
                "-S",
                "-B",
                str(SCRIPT.resolve()),
                "--launch",
            ],
            source_path=SCRIPT,
            umask_observer=lambda: 0o077,
        )
    with pytest.raises(probe.AuthorityError):
        probe.validate_runtime_contract(
            "--prepare",
            environ=probe.expected_prepare_environment(),
            executable=probe.PYTHON_BINARY,
            flags=flags,
            orig_argv=[
                probe.PYTHON_BINARY,
                "-I",
                "-S",
                "-B",
                str(SCRIPT.resolve()),
                "--prepare",
            ],
            source_path=SCRIPT,
            umask_observer=lambda: 0o022,
        )


def test_main_captures_one_process_entry_deadline_before_runtime_gate(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class Clock:
        now = 1_000_000_000

        def read(self) -> int:
            return self.now

    clock = Clock()
    observed: dict[str, int] = {}

    def validate(mode: str) -> None:
        assert mode == "--probe"
        clock.now += 2_000_000_000

    def route(**kwargs):
        observed.update(kwargs)
        return {"mode": "probe"}

    monkeypatch.setattr(probe.time, "monotonic_ns", clock.read)
    monkeypatch.setattr(probe, "validate_runtime_contract", validate)
    monkeypatch.setattr(probe, "run_probe_mode", route)
    assert probe.main(["--probe"]) == 0
    assert capsys.readouterr().out == '{"mode":"probe"}\n'
    assert observed["process_entry_ns"] == 1_000_000_000
    assert observed["deadline_ns"] - observed["process_entry_ns"] == (
        probe.INNER_TOTAL_TIMEOUT_NS
    )


def test_deadline_arithmetic_and_outer_terminal_contract_are_strict(
    tmp_path: Path,
) -> None:
    assert (
        probe.INNER_GIT_CALL_COUNT * probe.GIT_PROCESS_TOTAL_BOUND_SECONDS
        < probe.INNER_TOTAL_TIMEOUT_SECONDS
        < probe.UNIT_RUNTIME_MAX_SECONDS
    )
    assert (
        probe.UNIT_RUNTIME_MAX_SECONDS + probe.UNIT_STOP_TIMEOUT_SECONDS
        < probe.OUTER_LAUNCH_TIMEOUT_SECONDS
    )
    assert (
        probe.FORMAL_PREWORK_RESERVE_SECONDS
        + probe.OUTER_PROCESS_TOTAL_BOUND_SECONDS
        + probe.OUTER_POST_ABSENCE_SECONDS
        + probe.FORMAL_DEADLINE_MARGIN_SECONDS
        < probe.FORMAL_TOTAL_CAP_SECONDS
    )
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)

        def launch_callback(argv):
            receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 10_000,
            )
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(receipt) + b"\n",
                b"",
                False,
                False,
            )

        receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=FakeLaunchProcess(launch_callback),
            absence_observer=FakeAbsenceObserver(),
        )
        assert probe.validate_outer_deadline_contract(
            receipt["deadline_contract"]
        ) == receipt["deadline_contract"]
        context = receipt["inner_observation"]
        assert context["state"] == "RECEIPT"


def test_outer_attempt_publication_consumes_reserve_without_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    clock = FakeMonotonicClock()
    observer = FakeAbsenceObserver()
    process = FakeLaunchProcess(lambda _argv: pytest.fail("must not launch"))
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        original = probe.DurableArtifactStore.write_once

        def delayed_write(
            self, name, payload, *, token=None, pre_open=None
        ):
            original(
                self, name, payload, token=token, pre_open=pre_open
            )
            if name == probe.OUTER_LAUNCH_ATTEMPT_NAME:
                clock.advance_seconds(78)

        monkeypatch.setattr(
            probe.DurableArtifactStore, "write_once", delayed_write
        )
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=observer,
                monotonic_ns=clock.read,
                formal_process_entry_ns=1_000_000_000,
                deadline_ns=(
                    1_000_000_000
                    + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
                ),
            )
        failure = raised.value.failure_document
        assert failure["failure_reason"] == (
            "AFTER_ATTEMPT_DEADLINE_GATE_FAILED"
        )
        assert failure["launch_error"]["errno"] == errno.ETIMEDOUT
        deadline = failure["deadline_contract"]
        assert deadline["remaining_after_attempt_publication_ns"] == (
            probe.OUTER_REQUIRED_AFTER_ATTEMPT_PUBLICATION_SECONDS
            * 1_000_000_000
        )
        assert deadline["remaining_before_terminal_publication_ns"] == (
            deadline["remaining_after_attempt_publication_ns"]
        )
        assert process.calls == []
        assert observer.calls == 1
        assert store.inventory_names(phase="TEST") == frozenset(
            {
                probe.OUTER_LAUNCH_ATTEMPT_NAME,
                probe.OUTER_LAUNCH_FAILURE_NAME,
            }
        )
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure
        inner_attempt = probe.build_attempt_document(authority, raw)
        store.write_once(
            probe.ATTEMPT_NAME,
            probe.canonical_json_bytes(inner_attempt),
        )
        with pytest.raises(
            probe.AuthorityError,
            match="pre-process outer failure acquired a later inner artifact",
        ):
            probe.validate_outer_launch_failure_state(store, authority, raw)


def test_outer_post_absence_uses_local_cap_and_preserves_closure_margin(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    clock = FakeMonotonicClock()
    observed_deadlines: list[int] = []

    class ExhaustingObserver(FakeAbsenceObserver):
        def observe_absence(self, actual_authority, *, deadline_ns: int):
            observed_deadlines.append(deadline_ns)
            fact = super().observe_absence(
                actual_authority, deadline_ns=deadline_ns
            )
            if self.calls == 1:
                clock.advance_seconds(probe.FORMAL_PREWORK_RESERVE_SECONDS)
            elif self.calls == 2:
                clock.now_ns = deadline_ns
            return fact

    observer = ExhaustingObserver()
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)

        def launch_callback(argv):
            inner_receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 10_000,
            )
            clock.advance_seconds(probe.OUTER_PROCESS_TOTAL_BOUND_SECONDS)
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(inner_receipt) + b"\n",
                b"",
                False,
                False,
            )

        receipt = probe.run_outer_launch_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            process_adapter=FakeLaunchProcess(launch_callback),
            absence_observer=observer,
            monotonic_ns=clock.read,
            formal_process_entry_ns=1_000_000_000,
            deadline_ns=(
                1_000_000_000
                + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
            ),
        )
        deadline = receipt["deadline_contract"]
        assert observed_deadlines[0] == deadline[
            "formal_deadline_monotonic_ns"
        ]
        assert observed_deadlines[1] == (
            1_000_000_000
            + probe.FORMAL_PREWORK_RESERVE_SECONDS * 1_000_000_000
            + probe.OUTER_PROCESS_TOTAL_BOUND_SECONDS * 1_000_000_000
            + probe.OUTER_POST_ABSENCE_SECONDS * 1_000_000_000
        )
        assert deadline["post_absence_deadline_monotonic_ns"] == (
            observed_deadlines[1]
        )
        assert deadline["remaining_after_post_absence_ns"] >= (
            probe.FORMAL_DEADLINE_MARGIN_SECONDS * 1_000_000_000
        )
        assert deadline["remaining_after_inner_observation_ns"] > 0
        assert deadline["remaining_before_terminal_publication_ns"] > 0
        tampered_payload = dict(receipt)
        tampered_payload.pop("outer_launch_receipt_id")
        tampered_payload["deadline_contract"] = dict(deadline)
        tampered_payload["deadline_contract"][
            "post_absence_deadline_monotonic_ns"
        ] += 1
        tampered = probe._self_id_document(
            probe.OUTER_LAUNCH_RECEIPT_DOMAIN,
            "outer_launch_receipt_id",
            tampered_payload,
        )
        stdout = base64.b64decode(receipt["stdout"]["base64"])
        with pytest.raises(
            probe.AuthorityError,
            match="post-absence deadline escaped its closure reserve",
        ):
            probe.validate_outer_launch_receipt_document(
                tampered,
                outer_attempt=probe.build_outer_launch_attempt_document(
                    authority, raw
                ),
                inner_observation=receipt["inner_observation"],
                inner_terminal_raw=stdout[:-1],
                authority=authority,
            )


def test_outer_process_completion_gate_skips_post_observation_at_30_seconds(
    tmp_path: Path,
) -> None:
    authority, raw, _environment = _authority(tmp_path)
    clock = FakeMonotonicClock()
    observer = FakeAbsenceObserver()

    def launch_callback(argv):
        clock.advance_seconds(200)
        return probe.BoundedProcessResult(argv, 0, b"", b"", False, False)

    process = FakeLaunchProcess(launch_callback)
    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)
        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=process,
                absence_observer=observer,
                monotonic_ns=clock.read,
                formal_process_entry_ns=1_000_000_000,
                deadline_ns=(
                    1_000_000_000
                    + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
                ),
            )
        failure = raised.value.failure_document
        assert "DEADLINE_GATE_FAILED" in failure["failure_reason"]
        assert failure["deadline_contract"]["remaining_after_process_ns"] == (
            probe.OUTER_REQUIRED_AFTER_PROCESS_SECONDS * 1_000_000_000
        )
        assert failure["deadline_contract"][
            "post_absence_deadline_monotonic_ns"
        ] is None
        assert observer.calls == 1
        assert len(process.calls) == 1
        assert not store.exists(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure


def test_outer_rejects_post_absence_observer_local_deadline_overrun(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    clock = FakeMonotonicClock()

    class OverrunningObserver(FakeAbsenceObserver):
        def observe_absence(self, actual_authority, *, deadline_ns: int):
            fact = super().observe_absence(
                actual_authority, deadline_ns=deadline_ns
            )
            if self.calls == 1:
                clock.advance_seconds(probe.FORMAL_PREWORK_RESERVE_SECONDS)
            elif self.calls == 2:
                clock.now_ns = deadline_ns + 1
            return fact

    with _artifact_store(tmp_path) as store:
        _seed_prepared(store, authority, raw)

        def launch_callback(argv):
            inner_receipt = probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=lambda: 10_000,
            )
            clock.advance_seconds(probe.OUTER_PROCESS_TOTAL_BOUND_SECONDS)
            return probe.BoundedProcessResult(
                argv,
                0,
                probe.canonical_json_bytes(inner_receipt) + b"\n",
                b"",
                False,
                False,
            )

        with pytest.raises(probe.OuterLaunchFailure) as raised:
            probe.run_outer_launch_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                process_adapter=FakeLaunchProcess(launch_callback),
                absence_observer=OverrunningObserver(),
                monotonic_ns=clock.read,
                formal_process_entry_ns=1_000_000_000,
                deadline_ns=(
                    1_000_000_000
                    + probe.FORMAL_TOTAL_CAP_SECONDS * 1_000_000_000
                ),
            )
        failure = raised.value.failure_document
        assert "POSTLAUNCH_ABSENCE_UNPROVEN" in failure["failure_reason"]
        assert failure["launch_error"]["errno"] == errno.ETIMEDOUT
        assert failure["postlaunch_absence"] is None
        assert not store.exists(probe.OUTER_LAUNCH_RECEIPT_NAME)
        assert store.exists(probe.OUTER_LAUNCH_FAILURE_NAME)
        assert probe.validate_outer_launch_failure_state(
            store, authority, raw
        ) == failure


def test_prepare_post_attempt_return_interrupt_is_closed_by_parent_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original = probe.PrepareJournalStore.write_once

    def write_then_interrupt(self, name, raw, *, token, pre_open=None):
        original(self, name, raw, token=token, pre_open=pre_open)
        if name == probe.PREPARE_ATTEMPT_NAME:
            raise KeyboardInterrupt("fixture interrupt after PA return")

    monkeypatch.setattr(probe.PrepareJournalStore, "write_once", write_then_interrupt)
    with pytest.raises(probe.PrepareRunFailure) as raised:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
    )
    failure = raised.value.failure_document
    assert failure["artifact_root_path_present"] is False
    assert failure["artifact_root_device"] is None
    assert failure["artifact_root_inode"] is None
    assert failure["artifact_root_inventory_empty"] is None
    assert failure["external_root_path_present"] is False
    assert failure["external_root_recovery_raw_byte_count"] is None
    assert failure["prepare_failure_state_class"] == "ATTEMPT_EXACT_NO_RECEIPT"
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert not (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).exists()
    assert not (tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH).exists()
    assert {
        path.name for path in parent.iterdir() if path.name in probe.PREPARE_JOURNAL_NAMES
    } == {probe.PREPARE_ATTEMPT_NAME, probe.PREPARE_FAILURE_NAME}


@pytest.mark.parametrize(
    "failure_stage",
    [
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_PARENT_FSYNC",
        "AFTER_READBACK",
    ],
)
def test_prepare_failure_exact_checkpoint_fault_recovers_typed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once
    original_stabilize = probe.PrepareJournalStore.stabilize_exact
    failure_attempts = 0
    failure_checkpoint_hits = 0
    failure_stabilizations = 0

    def count_failure_write(
        self, name, artifact_raw, *, token, pre_open=None
    ):
        nonlocal failure_attempts
        if name == probe.PREPARE_FAILURE_NAME:
            failure_attempts += 1
        return original_write(
            self, name, artifact_raw, token=token, pre_open=pre_open
        )

    def count_failure_stabilization(self, name: str, artifact_raw: bytes):
        nonlocal failure_stabilizations
        if name == probe.PREPARE_FAILURE_NAME:
            failure_stabilizations += 1
        return original_stabilize(self, name, artifact_raw)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        nonlocal failure_checkpoint_hits
        if name == probe.PREPARE_ATTEMPT_NAME and stage == "AFTER_READBACK":
            raise OSError(errno.EIO, "fixture prepare attempt trigger")
        if name == probe.PREPARE_FAILURE_NAME and stage == failure_stage:
            failure_checkpoint_hits += 1
            raise OSError(errno.EIO, "fixture exact prepare failure")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", count_failure_write
    )
    monkeypatch.setattr(
        probe.PrepareJournalStore,
        "stabilize_exact",
        count_failure_stabilization,
    )
    with pytest.raises(probe.PrepareRunFailure) as raised:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    failure = raised.value.failure_document
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()
    assert probe.canonical_json_bytes(failure) == failure_raw
    assert failure_attempts == 1
    assert failure_checkpoint_hits == 1
    assert failure_stabilizations == 1

    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    assert replayed.value.failure_document == failure
    assert (parent / probe.PREPARE_FAILURE_NAME).read_bytes() == failure_raw
    assert failure_attempts == 1
    assert failure_checkpoint_hits == 1
    assert failure_stabilizations == 2


@pytest.mark.parametrize("persistent", [False, True])
def test_prepare_failure_exception_write_validation_is_typed_or_uncertain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    persistent: bool,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once
    original_validate = probe.validate_prepare_failure_state
    failure_attempts = 0
    validation_calls = 0

    def count_failure_write(
        self, name, artifact_raw, *, token, pre_open=None
    ):
        nonlocal failure_attempts
        if name == probe.PREPARE_FAILURE_NAME:
            failure_attempts += 1
        return original_write(
            self, name, artifact_raw, token=token, pre_open=pre_open
        )

    def validate_with_fault(*args, **kwargs):
        nonlocal validation_calls
        validation_calls += 1
        if validation_calls == 1 or persistent:
            raise OSError(
                errno.EIO,
                "fixture exception-write prepare failure validation",
            )
        return original_validate(*args, **kwargs)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.PREPARE_ATTEMPT_NAME and stage == "AFTER_READBACK":
            raise OSError(errno.EIO, "fixture prepare attempt trigger")
        if name == probe.PREPARE_FAILURE_NAME and stage == "AFTER_FULL_WRITE":
            raise OSError(errno.EIO, "fixture exact prepare failure")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", count_failure_write
    )
    monkeypatch.setattr(
        probe, "validate_prepare_failure_state", validate_with_fault
    )
    expected_exception = (
        probe.PrepareFailurePublicationUncertain
        if persistent
        else probe.PrepareRunFailure
    )
    with pytest.raises(expected_exception) as first:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    assert validation_calls == 2
    assert failure_attempts == 1
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()

    monkeypatch.setattr(
        probe, "validate_prepare_failure_state", original_validate
    )
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    if not persistent:
        assert first.value.failure_document == replayed.value.failure_document
    assert probe.canonical_json_bytes(
        replayed.value.failure_document
    ) == failure_raw
    assert failure_attempts == 1


def test_prepare_failure_postreturn_interrupt_recovers_typed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once
    failure_attempts = 0

    def write_then_interrupt(
        self, name, artifact_raw, *, token, pre_open=None
    ):
        nonlocal failure_attempts
        original_write(
            self, name, artifact_raw, token=token, pre_open=pre_open
        )
        if name == probe.PREPARE_ATTEMPT_NAME:
            raise KeyboardInterrupt("fixture prepare attempt post-return")
        if name == probe.PREPARE_FAILURE_NAME:
            failure_attempts += 1
            raise KeyboardInterrupt("fixture prepare failure post-return")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", write_then_interrupt
    )
    with pytest.raises(probe.PrepareRunFailure) as raised:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    failure = raised.value.failure_document
    assert failure_attempts == 1

    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert replayed.value.failure_document == failure
    assert failure_attempts == 1


@pytest.mark.parametrize(
    "retained_raw",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"{", id="prefix"),
        pytest.param(b"X", id="corrupt"),
    ],
)
def test_prepare_failure_inexact_checkpoint_is_uncertain_on_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    retained_raw: bytes,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once
    failure_attempts = 0

    def count_failure_write(
        self, name, artifact_raw, *, token, pre_open=None
    ):
        nonlocal failure_attempts
        if name == probe.PREPARE_FAILURE_NAME:
            failure_attempts += 1
        return original_write(
            self, name, artifact_raw, token=token, pre_open=pre_open
        )

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_ATTEMPT_NAME and stage == "AFTER_READBACK":
            raise OSError(errno.EIO, "fixture prepare attempt trigger")
        if (
            name == probe.PREPARE_FAILURE_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            if retained_raw:
                assert os.write(descriptor, retained_raw) == len(retained_raw)
            raise OSError(errno.EIO, "fixture inexact prepare failure")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", count_failure_write
    )
    with pytest.raises(probe.PrepareFailurePublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert (parent / probe.PREPARE_FAILURE_NAME).read_bytes() == retained_raw
    assert failure_attempts == 1

    with pytest.raises(probe.PrepareFailurePublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    assert (parent / probe.PREPARE_FAILURE_NAME).read_bytes() == retained_raw
    assert failure_attempts == 1


def test_prepare_failure_before_o_excl_can_close_retained_attempt_on_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once
    failure_attempts = 0

    def interrupt_attempt_and_reject_failure(
        self, name, artifact_raw, *, token, pre_open=None
    ):
        nonlocal failure_attempts
        if name == probe.PREPARE_FAILURE_NAME:
            failure_attempts += 1
            raise OSError(errno.EIO, "fixture failure before O_EXCL")
        original_write(
            self, name, artifact_raw, token=token, pre_open=pre_open
        )
        if name == probe.PREPARE_ATTEMPT_NAME:
            raise KeyboardInterrupt("fixture prepare attempt post-return")

    monkeypatch.setattr(
        probe.PrepareJournalStore,
        "write_once",
        interrupt_attempt_and_reject_failure,
    )
    with pytest.raises(probe.PrepareFailurePublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert (parent / probe.PREPARE_ATTEMPT_NAME).exists()
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()
    assert failure_attempts == 1

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", original_write
    )
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert replayed.value.failure_document["prepare_failure_id"]
    assert (parent / probe.PREPARE_FAILURE_NAME).exists()
    assert failure_attempts == 1


def test_prepare_failure_exact_recovery_can_resume_after_transient_stabilize_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_stabilize = probe.PrepareJournalStore.stabilize_exact

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.PREPARE_ATTEMPT_NAME and stage == "AFTER_READBACK":
            raise OSError(errno.EIO, "fixture prepare attempt trigger")
        if name == probe.PREPARE_FAILURE_NAME and stage == "AFTER_FULL_WRITE":
            raise OSError(errno.EIO, "fixture exact prepare failure")

    def reject_failure_stabilization(
        self, name: str, artifact_raw: bytes
    ) -> None:
        if name == probe.PREPARE_FAILURE_NAME:
            raise OSError(errno.EIO, "fixture transient prepare failure fsync")
        original_stabilize(self, name, artifact_raw)

    monkeypatch.setattr(
        probe.PrepareJournalStore,
        "stabilize_exact",
        reject_failure_stabilization,
    )
    with pytest.raises(probe.PrepareFailurePublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()

    monkeypatch.setattr(
        probe.PrepareJournalStore, "stabilize_exact", original_stabilize
    )
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    assert probe.canonical_json_bytes(
        replayed.value.failure_document
    ) == failure_raw


def test_prepare_failure_exact_recovery_can_resume_after_transient_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_read = probe.PrepareJournalStore.read_exact
    reject_once = True

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.PREPARE_ATTEMPT_NAME and stage == "AFTER_READBACK":
            raise OSError(errno.EIO, "fixture prepare attempt trigger")
        if name == probe.PREPARE_FAILURE_NAME and stage == "AFTER_FULL_WRITE":
            raise OSError(errno.EIO, "fixture exact prepare failure")

    def reject_first_failure_read(self, name: str, **kwargs):
        nonlocal reject_once
        if name == probe.PREPARE_FAILURE_NAME and reject_once:
            reject_once = False
            raise OSError(errno.EIO, "fixture transient prepare failure read")
        return original_read(self, name, **kwargs)

    monkeypatch.setattr(
        probe.PrepareJournalStore, "read_exact", reject_first_failure_read
    )
    with pytest.raises(probe.PrepareFailurePublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )

    monkeypatch.setattr(probe.PrepareJournalStore, "read_exact", original_read)
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    assert probe.canonical_json_bytes(
        replayed.value.failure_document
    ) == failure_raw


@pytest.mark.parametrize("recover_in_same_call", [True, False])
def test_prepare_failure_postwrite_validation_read_is_typed_or_uncertain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recover_in_same_call: bool,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_read = probe.PrepareJournalStore.read_exact
    original_write = probe.PrepareJournalStore.write_once
    failure_reads = 0
    failure_writes = 0

    def count_failure_write(
        self, name, artifact_raw, *, token, pre_open=None
    ):
        nonlocal failure_writes
        if name == probe.PREPARE_FAILURE_NAME:
            failure_writes += 1
        return original_write(
            self, name, artifact_raw, token=token, pre_open=pre_open
        )

    def reject_postwrite_validation_read(self, name: str, **kwargs):
        nonlocal failure_reads
        if name == probe.PREPARE_FAILURE_NAME:
            failure_reads += 1
            if failure_reads == 2 or (
                not recover_in_same_call and failure_reads >= 2
            ):
                raise OSError(
                    errno.EIO,
                    "fixture postwrite prepare failure validation read",
                )
        return original_read(self, name, **kwargs)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.PREPARE_ATTEMPT_NAME and stage == "AFTER_READBACK":
            raise OSError(errno.EIO, "fixture prepare attempt trigger")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", count_failure_write
    )
    monkeypatch.setattr(
        probe.PrepareJournalStore,
        "read_exact",
        reject_postwrite_validation_read,
    )
    expected_exception = (
        probe.PrepareRunFailure
        if recover_in_same_call
        else probe.PrepareFailurePublicationUncertain
    )
    with pytest.raises(expected_exception) as first:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    assert failure_writes == 1

    monkeypatch.setattr(
        probe.PrepareJournalStore, "read_exact", original_read
    )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    assert probe.canonical_json_bytes(
        replayed.value.failure_document
    ) == failure_raw
    if recover_in_same_call:
        assert first.value.failure_document == replayed.value.failure_document
    assert failure_writes == 1


@pytest.mark.parametrize("persistent", [False, True])
def test_prepare_clean_failure_authority_validation_closes_broad_catch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    persistent: bool,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once
    original_success_validate = probe.validate_prepare_success_state
    original_failure_validate = probe.validate_prepare_failure_state
    original_build_result = probe._build_prepare_result
    failure_attempts = 0
    success_validation_calls = 0
    failure_validation_calls = 0

    def count_failure_write(
        self, name, artifact_raw, *, token, pre_open=None
    ):
        nonlocal failure_attempts
        if name == probe.PREPARE_FAILURE_NAME:
            failure_attempts += 1
        return original_write(
            self, name, artifact_raw, token=token, pre_open=pre_open
        )

    def validate_success_then_fail(*args, **kwargs):
        nonlocal success_validation_calls
        success_validation_calls += 1
        if success_validation_calls == 2:
            raise OSError(
                errno.EIO,
                "fixture broad-catch prepare receipt validation",
            )
        return original_success_validate(*args, **kwargs)

    def validate_failure_with_authority_fault(*args, **kwargs):
        nonlocal failure_validation_calls
        failure_validation_calls += 1
        if failure_validation_calls == 1 or persistent:
            raise probe.AuthorityError(
                "fixture clean-write prepare failure validation"
            )
        return original_failure_validate(*args, **kwargs)

    def reject_first_result(*_args, **_kwargs):
        raise OSError(errno.EIO, "fixture prepare result construction")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", count_failure_write
    )
    monkeypatch.setattr(
        probe, "validate_prepare_success_state", validate_success_then_fail
    )
    monkeypatch.setattr(
        probe,
        "validate_prepare_failure_state",
        validate_failure_with_authority_fault,
    )
    monkeypatch.setattr(probe, "_build_prepare_result", reject_first_result)
    expected_exception = (
        probe.PrepareFailurePublicationUncertain
        if persistent
        else probe.PrepareRunFailure
    )
    with pytest.raises(expected_exception) as first:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert success_validation_calls == 2
    assert failure_validation_calls == 2
    assert failure_attempts == 1
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()

    monkeypatch.setattr(
        probe, "validate_prepare_success_state", original_success_validate
    )
    monkeypatch.setattr(
        probe, "validate_prepare_failure_state", original_failure_validate
    )
    monkeypatch.setattr(probe, "_build_prepare_result", original_build_result)
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    if not persistent:
        assert first.value.failure_document == replayed.value.failure_document
    assert probe.canonical_json_bytes(
        replayed.value.failure_document
    ) == failure_raw
    assert failure_attempts == 1


@pytest.mark.parametrize(
    ("artifact_name", "replacement_raw"),
    [
        (probe.PREPARE_ATTEMPT_NAME, b"X"),
        (probe.PREPARE_RECEIPT_NAME, b'{"'),
        (probe.PREPARE_FAILURE_NAME, b"X"),
    ],
)
def test_prepare_failure_validation_rejects_same_inode_artifact_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact_name: str,
    replacement_raw: bytes,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_RECEIPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial prepare receipt")

    with pytest.raises(probe.PrepareRunFailure):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    external_raw = (tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH).read_bytes()
    authority = probe.loads_canonical_json(external_raw)
    with probe._open_prepare_parent_chain(tmp_path, create=False) as parent:
        journal = probe.PrepareJournalStore(parent)
        original_require = journal.require_inventory
        mutated = False

        def mutate_before_post_rows(
            expected_names,
            *,
            phase: str,
            allow_partial_names=frozenset(),
        ):
            nonlocal mutated
            if phase == "PREPARE_FAILURE_AUTHORITY_POST" and not mutated:
                path = parent.final_path / artifact_name
                before = os.stat(path, follow_symlinks=False)
                os.chmod(path, 0o600, follow_symlinks=False)
                descriptor = os.open(
                    path,
                    os.O_WRONLY
                    | os.O_TRUNC
                    | os.O_NOFOLLOW
                    | os.O_CLOEXEC,
                )
                try:
                    assert os.write(descriptor, replacement_raw) == len(
                        replacement_raw
                    )
                    os.fchmod(descriptor, 0o400)
                finally:
                    os.close(descriptor)
                after = os.stat(path, follow_symlinks=False)
                assert (after.st_dev, after.st_ino) == (
                    before.st_dev,
                    before.st_ino,
                )
                mutated = True
            return original_require(
                expected_names,
                phase=phase,
                allow_partial_names=allow_partial_names,
            )

        monkeypatch.setattr(journal, "require_inventory", mutate_before_post_rows)
        with pytest.raises(
            probe.AuthorityError,
            match="prepare failure artifact bytes changed during validation",
        ):
            probe.validate_prepare_failure_state(
                journal, authority, external_raw
            )
        assert mutated is True


def test_prepare_post_mkdir_interrupt_binds_live_empty_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original = probe._claim_artifact_root

    def create_then_interrupt(parent, *, create, ownership=None):
        claim = original(parent, create=create, ownership=ownership)
        if create:
            raise KeyboardInterrupt("fixture interrupt after root claim")
        return claim

    monkeypatch.setattr(probe, "_claim_artifact_root", create_then_interrupt)
    with pytest.raises(probe.PrepareRunFailure) as raised:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    failure = raised.value.failure_document
    root = tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
    root_stat = root.stat()
    assert root.exists()
    assert failure["artifact_root_path_present"] is True
    assert (failure["artifact_root_device"], failure["artifact_root_inode"]) == (
        root_stat.st_dev,
        root_stat.st_ino,
    )
    assert failure["artifact_root_mode"] == 0o700
    assert failure["artifact_root_owner_uid"] == root_stat.st_uid
    assert failure["artifact_root_owner_gid"] == root_stat.st_gid
    assert failure["artifact_root_inventory_empty"] is True
    assert failure["external_root_path_present"] is False


def test_prepare_root_path_drift_binds_live_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original = probe._claim_artifact_root
    retained_root: Path | None = None
    replacement_identity: tuple[int, int] | None = None

    def create_then_swap(parent, *, create, ownership=None):
        nonlocal retained_root, replacement_identity
        claim = original(parent, create=create, ownership=ownership)
        if create:
            root = parent.final_path / Path(probe.ARTIFACT_ROOT_RELATIVE_PATH).name
            retained_root = root.with_name(f"{root.name}.retained-fixture")
            root.rename(retained_root)
            root.mkdir(mode=0o700)
            replacement = root.stat()
            replacement_identity = (replacement.st_dev, replacement.st_ino)
        return claim

    monkeypatch.setattr(probe, "_claim_artifact_root", create_then_swap)
    with pytest.raises(probe.PrepareRunFailure) as raised:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    failure = raised.value.failure_document
    root = tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
    assert retained_root is not None and retained_root.exists()
    assert root.exists()
    assert replacement_identity is not None
    assert failure["artifact_root_path_present"] is True
    assert (
        failure["artifact_root_device"],
        failure["artifact_root_inode"],
    ) == replacement_identity
    assert replacement_identity != (
        retained_root.stat().st_dev,
        retained_root.stat().st_ino,
    )
    assert failure["artifact_root_inventory_empty"] is True
    assert failure["external_root_path_present"] is False


def test_prepare_root_removal_after_claim_is_typed_as_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original = probe._claim_artifact_root

    def create_then_remove(parent, *, create, ownership=None):
        claim = original(parent, create=create, ownership=ownership)
        if create:
            os.rmdir(
                Path(probe.ARTIFACT_ROOT_RELATIVE_PATH).name,
                dir_fd=parent.final_fd,
            )
        return claim

    monkeypatch.setattr(probe, "_claim_artifact_root", create_then_remove)
    with pytest.raises(probe.PrepareRunFailure) as raised:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
    )
    failure = raised.value.failure_document
    assert failure["artifact_root_path_present"] is False
    assert failure["artifact_root_device"] is None
    assert failure["artifact_root_inode"] is None
    assert failure["artifact_root_mode"] is None
    assert failure["artifact_root_owner_uid"] is None
    assert failure["artifact_root_owner_gid"] is None
    assert failure["artifact_root_inventory_empty"] is None
    assert not (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).exists()
    assert failure["external_root_path_present"] is False


@pytest.mark.parametrize(
    "fault_stage",
    [
        "AFTER_FULL_WRITE",
        "AFTER_FILE_FSYNC",
        "AFTER_PARENT_FSYNC",
        "AFTER_READBACK",
    ],
)
def test_prepare_exact_receipt_fault_recovers_without_prepare_failure(
    tmp_path: Path, fault_stage: str
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)

    def checkpoint(stage: str, name: str, _descriptor: int) -> None:
        if name == probe.PREPARE_RECEIPT_NAME and stage == fault_stage:
            raise KeyboardInterrupt("fixture exact prepare receipt async fault")

    result = probe.prepare_external_root_once(
        tmp_path,
        git_stdout=fake_git,
        host_observer=_host_parent_fact,
        require_running_source=False,
        publication_checkpoint=checkpoint,
    )
    assert result["schema"] == probe.PREPARE_RESULT_SCHEMA
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert (parent / probe.PREPARE_ATTEMPT_NAME).exists()
    assert (parent / probe.PREPARE_RECEIPT_NAME).exists()
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()


def test_prepare_receipt_post_write_return_interrupt_recovers_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once

    def write_then_interrupt(self, name, raw, *, token, pre_open=None):
        original_write(
            self, name, raw, token=token, pre_open=pre_open
        )
        if name == probe.PREPARE_RECEIPT_NAME:
            raise KeyboardInterrupt("fixture interrupt after PREPARE_RECEIPT return")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", write_then_interrupt
    )
    result = probe.prepare_external_root_once(
        tmp_path,
        git_stdout=fake_git,
        host_observer=_host_parent_fact,
        require_running_source=False,
    )
    assert result["schema"] == probe.PREPARE_RESULT_SCHEMA
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert (parent / probe.PREPARE_RECEIPT_NAME).exists()
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()


def test_prepare_exact_receipt_recovery_failure_persists_typed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    probe.prepare_external_root_once(
        tmp_path,
        git_stdout=fake_git,
        host_observer=_host_parent_fact,
        require_running_source=False,
    )
    original_stabilize = probe.PrepareJournalStore.stabilize_exact

    def reject_prepare_receipt(self, name: str, raw: bytes) -> None:
        if name == probe.PREPARE_RECEIPT_NAME:
            raise OSError(errno.EIO, "fixture persistent prepare receipt fsync")
        original_stabilize(self, name, raw)

    monkeypatch.setattr(
        probe.PrepareJournalStore, "stabilize_exact", reject_prepare_receipt
    )
    for _ in range(2):
        with pytest.raises(probe.PrepareRunFailure) as raised:
            probe.prepare_external_root_once(
                tmp_path,
                git_stdout=fake_git,
                host_observer=_host_parent_fact,
                require_running_source=False,
            )
        assert raised.value.failure_document[
            "prepare_receipt_observed_exact"
        ] is True
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert (parent / probe.PREPARE_RECEIPT_NAME).exists()
    assert (parent / probe.PREPARE_FAILURE_NAME).exists()


def test_prepare_partial_receipt_adds_typed_prepare_failure(
    tmp_path: Path,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if (
            name == probe.PREPARE_RECEIPT_NAME
            and stage == "AFTER_INITIAL_FCHMOD"
        ):
            assert os.write(descriptor, b"{") == 1
            raise KeyboardInterrupt("fixture partial prepare receipt")

    with pytest.raises(probe.PrepareRunFailure) as raised:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    assert raised.value.failure_document[
        "prepare_receipt_observed_exact"
    ] is False
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert (parent / probe.PREPARE_RECEIPT_NAME).read_bytes() == b"{"
    assert (parent / probe.PREPARE_FAILURE_NAME).exists()
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert replayed.value.failure_document[
        "prepare_failure_id"
    ] == raised.value.failure_document["prepare_failure_id"]
    external_raw = (tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH).read_bytes()
    with pytest.raises(probe.ForeignArtifactError):
        probe.validate_prepared_authority(
            probe.loads_canonical_json(external_raw), external_raw
        )


def _overwrite_prepare_artifact_same_inode(path: Path, raw: bytes) -> None:
    before = os.stat(path, follow_symlinks=False)
    os.chmod(path, 0o600, follow_symlinks=False)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            assert written > 0
            remaining = remaining[written:]
        os.fchmod(descriptor, 0o400)
    finally:
        os.close(descriptor)
    after = os.stat(path, follow_symlinks=False)
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)


def test_prepare_failure_store_pre_open_callback_closes_wrapper_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once
    failure_attempts = 0
    failure_token: probe.PublicationOwnershipToken | None = None
    mutated = False

    def drift_before_failure_pre_open(
        self, name, raw, *, token, pre_open=None
    ):
        nonlocal failure_attempts, failure_token, mutated
        if name == probe.PREPARE_FAILURE_NAME:
            failure_attempts += 1
            failure_token = token
            if not mutated:
                receipt_path = (
                    tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
                ).parent / probe.PREPARE_RECEIPT_NAME
                _overwrite_prepare_artifact_same_inode(receipt_path, b'{"')
                mutated = True
        return original_write(
            self,
            name,
            raw,
            token=token,
            pre_open=pre_open,
        )

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_RECEIPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial prepare receipt")

    monkeypatch.setattr(
        probe.PrepareJournalStore,
        "write_once",
        drift_before_failure_pre_open,
    )
    with pytest.raises(probe.PrepareReceiptPublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert mutated is True
    assert failure_attempts == 1
    assert failure_token is not None
    assert failure_token.path_created is False
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()


def test_prepare_failure_final_root_hook_cannot_drift_receipt_before_o_excl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_terminal = probe._publish_prepare_failure_terminal
    original_observe_root = probe._observe_prepare_artifact_root_state
    original_write = probe.PrepareJournalStore.write_once
    inside_terminal = False
    terminal_root_observations = 0
    failure_attempts = 0
    failure_token: probe.PublicationOwnershipToken | None = None
    mutated = False

    def mark_terminal(**kwargs):
        nonlocal inside_terminal
        inside_terminal = True
        try:
            return original_terminal(**kwargs)
        finally:
            inside_terminal = False

    def mutate_receipt_in_final_root_observer(parent):
        nonlocal terminal_root_observations, mutated
        state = original_observe_root(parent)
        if inside_terminal:
            terminal_root_observations += 1
            if terminal_root_observations == 2:
                receipt_path = (
                    tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
                ).parent / probe.PREPARE_RECEIPT_NAME
                _overwrite_prepare_artifact_same_inode(receipt_path, b'{"')
                mutated = True
        return state

    def count_failure_attempt(self, name, raw, *, token, pre_open=None):
        nonlocal failure_attempts, failure_token
        if name == probe.PREPARE_FAILURE_NAME:
            failure_attempts += 1
            failure_token = token
        return original_write(
            self,
            name,
            raw,
            token=token,
            pre_open=pre_open,
        )

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_RECEIPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial prepare receipt")

    monkeypatch.setattr(probe, "_publish_prepare_failure_terminal", mark_terminal)
    monkeypatch.setattr(
        probe,
        "_observe_prepare_artifact_root_state",
        mutate_receipt_in_final_root_observer,
    )
    monkeypatch.setattr(
        probe.PrepareJournalStore,
        "write_once",
        count_failure_attempt,
    )
    with pytest.raises(probe.PrepareReceiptPublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert terminal_root_observations == 2
    assert mutated is True
    assert failure_attempts == 1
    assert failure_token is not None
    assert failure_token.path_created is False
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()


@pytest.mark.parametrize(
    ("drift", "replacement_raw"),
    [
        ("nonprefix", b"X"),
        ("different_prefix", b'{"'),
        ("unreadable", None),
    ],
)
def test_prepare_failure_terminal_rechecks_receipt_before_o_excl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
    replacement_raw: bytes | None,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_terminal = probe._publish_prepare_failure_terminal
    original_write = probe.PrepareJournalStore.write_once
    write_counts: dict[str, int] = {}

    def count_writes(self, name, raw, *, token, pre_open=None):
        write_counts[name] = write_counts.get(name, 0) + 1
        return original_write(
            self, name, raw, token=token, pre_open=pre_open
        )

    def drift_at_terminal_entry(**kwargs):
        receipt_path = (
            tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
        ).parent / probe.PREPARE_RECEIPT_NAME
        if replacement_raw is None:
            receipt_path.chmod(0o000)
        else:
            _overwrite_prepare_artifact_same_inode(
                receipt_path, replacement_raw
            )
        return original_terminal(**kwargs)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_RECEIPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial prepare receipt")

    monkeypatch.setattr(probe.PrepareJournalStore, "write_once", count_writes)
    monkeypatch.setattr(
        probe, "_publish_prepare_failure_terminal", drift_at_terminal_entry
    )
    with pytest.raises(probe.PrepareReceiptPublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert write_counts[probe.PREPARE_ATTEMPT_NAME] == 1
    assert write_counts[probe.PREPARE_RECEIPT_NAME] == 1
    assert write_counts.get(probe.PREPARE_FAILURE_NAME, 0) == 1
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()
    with pytest.raises(probe.PrepareReceiptPublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert write_counts[probe.PREPARE_ATTEMPT_NAME] == 1
    assert write_counts[probe.PREPARE_RECEIPT_NAME] == 1
    assert write_counts.get(probe.PREPARE_FAILURE_NAME, 0) == 1


def test_prepare_failure_terminal_rechecks_attempt_then_replay_writes_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_terminal = probe._publish_prepare_failure_terminal
    original_write = probe.PrepareJournalStore.write_once
    failure_writes = 0

    def count_failure_writes(self, name, raw, *, token, pre_open=None):
        nonlocal failure_writes
        if name == probe.PREPARE_FAILURE_NAME:
            failure_writes += 1
        return original_write(
            self, name, raw, token=token, pre_open=pre_open
        )

    def drift_at_terminal_entry(**kwargs):
        attempt_path = (
            tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
        ).parent / probe.PREPARE_ATTEMPT_NAME
        _overwrite_prepare_artifact_same_inode(attempt_path, b'{"')
        return original_terminal(**kwargs)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_ATTEMPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial prepare attempt")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", count_failure_writes
    )
    monkeypatch.setattr(
        probe, "_publish_prepare_failure_terminal", drift_at_terminal_entry
    )
    with pytest.raises(probe.PrepareFailurePublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert failure_writes == 1
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()

    monkeypatch.setattr(
        probe, "_publish_prepare_failure_terminal", original_terminal
    )
    with pytest.raises(probe.PrepareRunFailure) as closed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()
    assert failure_writes == 2
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert replayed.value.failure_document == closed.value.failure_document
    assert (parent / probe.PREPARE_FAILURE_NAME).read_bytes() == failure_raw
    assert failure_writes == 2


def test_prepare_failure_terminal_rechecks_root_then_replay_writes_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_claim = probe._claim_artifact_root
    original_terminal = probe._publish_prepare_failure_terminal
    original_write = probe.PrepareJournalStore.write_once
    retained_root: Path | None = None
    failure_writes = 0

    def create_then_interrupt(parent, *, create, ownership=None):
        claim = original_claim(parent, create=create, ownership=ownership)
        if create:
            raise KeyboardInterrupt("fixture interrupt after root claim")
        return claim

    def count_failure_writes(self, name, raw, *, token, pre_open=None):
        nonlocal failure_writes
        if name == probe.PREPARE_FAILURE_NAME:
            failure_writes += 1
        return original_write(
            self, name, raw, token=token, pre_open=pre_open
        )

    def replace_root_at_terminal_entry(**kwargs):
        nonlocal retained_root
        root = tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
        retained_root = root.with_name(f"{root.name}.retained-terminal-fixture")
        root.rename(retained_root)
        root.mkdir(mode=0o700)
        root.chmod(0o700)
        return original_terminal(**kwargs)

    monkeypatch.setattr(probe, "_claim_artifact_root", create_then_interrupt)
    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", count_failure_writes
    )
    monkeypatch.setattr(
        probe,
        "_publish_prepare_failure_terminal",
        replace_root_at_terminal_entry,
    )
    with pytest.raises(probe.PrepareFailurePublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert retained_root is not None and retained_root.exists()
    assert failure_writes == 1
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()

    monkeypatch.setattr(
        probe, "_publish_prepare_failure_terminal", original_terminal
    )
    with pytest.raises(probe.PrepareRunFailure) as closed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()
    assert failure_writes == 2
    with pytest.raises(probe.PrepareRunFailure) as replayed:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert replayed.value.failure_document == closed.value.failure_document
    assert (parent / probe.PREPARE_FAILURE_NAME).read_bytes() == failure_raw
    assert failure_writes == 2


def test_prepare_failure_validator_final_rows_precede_final_byte_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_write = probe.PrepareJournalStore.write_once
    failure_writes = 0

    def count_failure_writes(self, name, raw, *, token, pre_open=None):
        nonlocal failure_writes
        if name == probe.PREPARE_FAILURE_NAME:
            failure_writes += 1
        return original_write(
            self, name, raw, token=token, pre_open=pre_open
        )

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_RECEIPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial prepare receipt")

    monkeypatch.setattr(
        probe.PrepareJournalStore, "write_once", count_failure_writes
    )
    with pytest.raises(probe.PrepareRunFailure):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    parent_path = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent_path / probe.PREPARE_FAILURE_NAME).read_bytes()
    external_raw = (tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH).read_bytes()
    authority = probe.loads_canonical_json(external_raw)
    with probe._open_prepare_parent_chain(tmp_path, create=False) as parent:
        journal = probe.PrepareJournalStore(parent)
        original_inventory = journal.inventory_names
        mutated = False

        def mutate_after_final_names(*, phase: str):
            nonlocal mutated
            names = original_inventory(phase=phase)
            if phase == "PREPARE_FAILURE_AUTHORITY_FINAL" and not mutated:
                _overwrite_prepare_artifact_same_inode(
                    parent_path / probe.PREPARE_RECEIPT_NAME, b'{"'
                )
                mutated = True
            return names

        monkeypatch.setattr(journal, "inventory_names", mutate_after_final_names)
        with pytest.raises(
            probe.AuthorityError,
            match="prepare failure artifact bytes changed during final validation",
        ):
            probe.validate_prepare_failure_state(
                journal, authority, external_raw
            )
        assert mutated is True
    assert failure_writes == 1
    assert (parent_path / probe.PREPARE_FAILURE_NAME).read_bytes() == failure_raw
    with pytest.raises(
        probe.AuthorityError,
        match="PREPARE_FAILURE disagrees with live retained state",
    ):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert failure_writes == 1


def test_prepare_partial_attempt_raw_identity_rejects_prefix_drift_on_replay(
    tmp_path: Path,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_ATTEMPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial prepare attempt")

    with pytest.raises(probe.PrepareRunFailure) as first:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    failure = first.value.failure_document
    assert failure["prepare_attempt_observed_exact"] is False
    assert failure["prepare_attempt_recovery_raw_byte_count"] == 1
    assert failure["prepare_attempt_recovery_raw_sha256"] == hashlib.sha256(
        b"{"
    ).hexdigest()
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()
    _overwrite_prepare_artifact_same_inode(
        parent / probe.PREPARE_ATTEMPT_NAME, b'{"'
    )
    with pytest.raises(
        probe.AuthorityError,
        match="PREPARE_FAILURE disagrees with live retained state",
    ):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert (parent / probe.PREPARE_FAILURE_NAME).read_bytes() == failure_raw


def test_prepare_partial_receipt_raw_identity_rejects_prefix_drift_on_replay(
    tmp_path: Path,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_RECEIPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial prepare receipt")

    with pytest.raises(probe.PrepareRunFailure) as first:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    failure = first.value.failure_document
    assert failure["prepare_receipt_observed_exact"] is False
    assert failure["prepare_receipt_recovery_raw_byte_count"] == 1
    assert failure["prepare_receipt_recovery_raw_sha256"] == hashlib.sha256(
        b"{"
    ).hexdigest()
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()
    _overwrite_prepare_artifact_same_inode(
        parent / probe.PREPARE_RECEIPT_NAME, b'{"'
    )
    with pytest.raises(
        probe.AuthorityError,
        match="PREPARE_FAILURE disagrees with live retained state",
    ):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert (parent / probe.PREPARE_FAILURE_NAME).read_bytes() == failure_raw


@pytest.mark.parametrize("fault", ["nonprefix", "unreadable"])
def test_prepare_receipt_unclassifiable_state_is_uncertain_before_failure_o_excl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_read = probe.PrepareJournalStore.read_exact

    def checkpoint(stage: str, name: str, descriptor: int) -> None:
        if name == probe.PREPARE_RECEIPT_NAME and stage == "AFTER_INITIAL_FCHMOD":
            raw = b"X" if fault == "nonprefix" else b"{"
            assert os.write(descriptor, raw) == len(raw)
            raise OSError(errno.EIO, "fixture unclassifiable prepare receipt")

    def reject_receipt_read(self, name: str, **kwargs):
        if fault == "unreadable" and name == probe.PREPARE_RECEIPT_NAME:
            raise OSError(errno.EIO, "fixture unreadable prepare receipt")
        return original_read(self, name, **kwargs)

    monkeypatch.setattr(
        probe.PrepareJournalStore, "read_exact", reject_receipt_read
    )
    with pytest.raises(probe.PrepareReceiptPublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            publication_checkpoint=checkpoint,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert (parent / probe.PREPARE_RECEIPT_NAME).exists()
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()


def test_prepare_external_root_raw_identity_rejects_prefix_drift_on_replay(
    tmp_path: Path,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)

    def checkpoint(stage: str, _name: str, descriptor: int) -> None:
        if stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"{") == 1
            raise OSError(errno.EIO, "fixture partial external root")

    with pytest.raises(probe.PrepareRunFailure) as first:
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            external_root_checkpoint=checkpoint,
        )
    failure = first.value.failure_document
    assert failure["external_root_path_present"] is True
    assert failure["external_root_observed_exact"] is False
    assert failure["external_root_recovery_raw_byte_count"] == 1
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_raw = (parent / probe.PREPARE_FAILURE_NAME).read_bytes()
    _overwrite_prepare_artifact_same_inode(
        tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH, b'{"'
    )
    external_root_raw = probe.canonical_json_bytes(
        probe.collect_post_c_probe_authority(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    )
    with probe._open_prepare_parent_chain(tmp_path, create=False) as opened_parent:
        with pytest.raises(
            probe.AuthorityError,
            match="PREPARE_FAILURE disagrees with live retained state",
        ):
            probe.validate_prepare_failure_state(
                probe.PrepareJournalStore(opened_parent),
                probe.loads_canonical_json(external_root_raw),
                external_root_raw,
            )
    assert (parent / probe.PREPARE_FAILURE_NAME).read_bytes() == failure_raw


def test_prepare_external_root_nonprefix_is_uncertain_before_failure_o_excl(
    tmp_path: Path,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)

    def checkpoint(stage: str, _name: str, descriptor: int) -> None:
        if stage == "AFTER_INITIAL_FCHMOD":
            assert os.write(descriptor, b"X") == 1
            raise OSError(errno.EIO, "fixture corrupt external root")

    with pytest.raises(probe.PrepareFailurePublicationUncertain):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
            external_root_checkpoint=checkpoint,
        )
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    assert not (parent / probe.PREPARE_FAILURE_NAME).exists()


@pytest.mark.parametrize("relabel", ["external", "artifact", "error"])
def test_prepare_failure_self_id_cannot_hide_live_state_or_error_relabel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relabel: str,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_publish = probe._publish_external_root_once

    def publish_then_interrupt(*args, **kwargs):
        original_publish(*args, **kwargs)
        raise KeyboardInterrupt("fixture interrupt after external-root return")

    monkeypatch.setattr(
        probe, "_publish_external_root_once", publish_then_interrupt
    )
    with pytest.raises(probe.PrepareRunFailure):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    external_raw = (tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH).read_bytes()
    authority = probe.loads_canonical_json(external_raw)
    parent = (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH).parent
    failure_path = parent / probe.PREPARE_FAILURE_NAME
    retained = probe.loads_canonical_json(failure_path.read_bytes())
    payload = dict(retained)
    payload.pop("prepare_failure_id")
    if relabel == "external":
        payload["external_root_observed_exact"] = False
    elif relabel == "artifact":
        payload["artifact_root_inode"] += 1
    else:
        payload["prepare_error"] = {
            "error_type": "RelabeledError",
            "message": "not externally observable",
            "errno": None,
            "errno_name": None,
        }
    tampered = probe._self_id_document(
        probe.PREPARE_FAILURE_DOMAIN, "prepare_failure_id", payload
    )
    _overwrite_prepare_artifact_same_inode(
        failure_path, probe.canonical_json_bytes(tampered)
    )
    with probe._open_prepare_parent_chain(tmp_path, create=False) as opened_parent:
        with pytest.raises(probe.AuthorityError):
            probe.validate_prepare_failure_state(
                probe.PrepareJournalStore(opened_parent),
                authority,
                external_raw,
            )


@pytest.mark.parametrize("drift", ["mode", "inventory"])
def test_prepare_failure_validator_rebuilds_live_artifact_root_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    original_publish = probe._publish_external_root_once

    def publish_then_interrupt(*args, **kwargs):
        original_publish(*args, **kwargs)
        raise KeyboardInterrupt("fixture interrupt after external-root return")

    monkeypatch.setattr(
        probe, "_publish_external_root_once", publish_then_interrupt
    )
    with pytest.raises(probe.PrepareRunFailure):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    external_raw = (tmp_path / probe.EXTERNAL_ROOT_RELATIVE_PATH).read_bytes()
    authority = probe.loads_canonical_json(external_raw)
    root = tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
    if drift == "mode":
        root.chmod(0o750)
    else:
        (root / "FOREIGN").write_bytes(b"X")
    with probe._open_prepare_parent_chain(tmp_path, create=False) as opened_parent:
        with pytest.raises(probe.AuthorityError):
            probe.validate_prepare_failure_state(
                probe.PrepareJournalStore(opened_parent),
                authority,
                external_raw,
            )


def test_prepare_refuses_unjournaled_same_uid_empty_root(tmp_path: Path) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    root = tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    with pytest.raises(probe.ForeignArtifactError):
        probe.prepare_external_root_once(
            tmp_path,
            git_stdout=fake_git,
            host_observer=_host_parent_fact,
            require_running_source=False,
        )
    assert not any((root.parent / name).exists() for name in probe.PREPARE_JOURNAL_NAMES)


def test_inventory_scandir_stops_exactly_at_cap_plus_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _artifact_store(tmp_path) as store:
        class Entry:
            def __init__(self, name: str) -> None:
                self.name = name

        class Scan:
            def __init__(self) -> None:
                self.count = 0
                self.entries = [Entry(name) for name in sorted(probe.ROOT_ARTIFACT_NAMES)]
                self.entries.extend(Entry("FOREIGN.json") for _ in range(100))

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def __iter__(self):
                return self

            def __next__(self):
                if self.count >= len(self.entries):
                    raise StopIteration
                entry = self.entries[self.count]
                self.count += 1
                return entry

        scan = Scan()
        monkeypatch.setattr(probe.os, "scandir", lambda _fd: scan)
        with pytest.raises(probe.ForeignArtifactError, match="entry cap"):
            store.inventory_names(phase="CAP_PLUS_ONE")
        assert scan.count == probe.MAX_ARTIFACT_INVENTORY_ENTRIES + 1


def test_strict_inner_validators_reject_reidentified_semantic_tampering(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        receipt = probe.run_probe_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            runtime=FakeRuntime(),
            environ=environment,
            monotonic_ns=lambda: 1_000_000,
        )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
        assert probe.validate_attempt_document(attempt, authority, raw) == attempt
        assert probe.validate_receipt_document(receipt, attempt, authority) == receipt
        assert receipt["unconditional_same_uid_replacement_safety_claimed"] is False
        assert receipt["manager_stop_identity_binding_contract"] == (
            probe.MANAGER_STOP_IDENTITY_BINDING
        )
        assert receipt["requested_manager_stop_identity_binding"] == (
            probe.MANAGER_STOP_IDENTITY_BINDING
        )
        for field, value in (
            ("target_absent", False),
            ("unconditional_same_uid_replacement_safety_claimed", True),
            (
                "requested_manager_stop_identity_binding",
                probe.MANAGER_STOP_NOT_DISPATCHED,
            ),
        ):
            payload = dict(receipt)
            del payload["preflight_receipt_id"]
            payload[field] = value
            tampered = probe._self_id_document(
                probe.RECEIPT_DOMAIN, "preflight_receipt_id", payload
            )
            with pytest.raises(probe.AuthorityError):
                probe.validate_receipt_document(tampered, attempt, authority)


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("target_unit_name", "attacker-target.service"),
        ("manager_owned_lifecycle", False),
    ],
)
def test_receipt_reidentified_target_create_semantics_are_rejected(
    tmp_path: Path, field: str, forged: object
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        receipt = probe.run_probe_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            runtime=FakeRuntime(),
            environ=environment,
            monotonic_ns=lambda: 1_000_000,
        )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    payload = dict(receipt)
    payload.pop("preflight_receipt_id")
    records = [dict(row) for row in payload["substage_records"]]
    row = dict(records[3])
    row.pop("substage_record_id")
    detail = dict(row["detail"])
    detail[field] = forged
    row["detail"] = detail
    records[3] = probe._self_id_document(
        probe.SUBSTAGE_DOMAIN, "substage_record_id", row
    )
    payload["substage_records"] = records
    tampered = probe._self_id_document(
        probe.RECEIPT_DOMAIN, "preflight_receipt_id", payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_receipt_document(tampered, attempt, authority)


def test_receipt_reidentified_pidfd_membership_is_rejected(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        receipt = probe.run_probe_once(
            authority=authority,
            external_root_raw=raw,
            store=store,
            runtime=FakeRuntime(),
            environ=environment,
            monotonic_ns=lambda: 1_000_000,
        )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    payload = dict(receipt)
    payload.pop("preflight_receipt_id")
    records = [dict(row) for row in payload["substage_records"]]
    row = dict(records[6])
    row.pop("substage_record_id")
    detail = dict(row["detail"])
    detail["membership_line"] = "0::/attacker.slice/reidentified.scope"
    row["detail"] = detail
    records[6] = probe._self_id_document(
        probe.SUBSTAGE_DOMAIN, "substage_record_id", row
    )
    payload["substage_records"] = records
    tampered = probe._self_id_document(
        probe.RECEIPT_DOMAIN, "preflight_receipt_id", payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_receipt_document(tampered, attempt, authority)


def test_failure_reidentified_absence_cannot_override_failed_manager_cleanup(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    runtime = FakeRuntime(
        fail_method="receive_handshake",
        cleanup_failures=frozenset({"remove_target", "target_absent"}),
    )
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert probe.validate_failure_document(failure, attempt, authority) == failure
    payload = dict(failure)
    payload.pop("preflight_failure_id")
    records = [dict(row) for row in payload["substage_records"]]
    absence_index = next(
        index
        for index, row in enumerate(records)
        if row["substage"] == "CLEANUP_TARGET_ABSENT"
    )
    absence = dict(records[absence_index])
    absence.pop("substage_record_id")
    absence.update(
        {
            "status": "OK",
            "errno": None,
            "errno_name": None,
            "error_type": None,
            "message": None,
                "detail": {
                    "target_absent": True,
                    "target_transient_instance_implicit_absence": True,
                    "target_path_absent": True,
                    "transient_fragment_absent": True,
                    "transient_fragment_path": (
                        FakeRuntime._success_fragment_path()
                    ),
                    "transient_fragment_stat_errno": errno.ENOENT,
                    "parent_named_path_observation": (
                        FakeRuntime._parent_absent_observation()
                    ),
                    "named_path_detached_and_manager_implicit_absence": True,
                    "posix_inode_unlink_claimed": False,
                    "manager_implicit_absence_proven": True,
                "manager_properties": FakeRuntime._manager_absent_properties(),
                "manager_lifecycle_authority": "SYSTEMD_USER_MANAGER_ONLY",
                "probe_path_deletion_calls": 0,
            },
        }
    )
    records[absence_index] = probe._self_id_document(
        probe.SUBSTAGE_DOMAIN, "substage_record_id", absence
    )
    payload["substage_records"] = records
    payload["target_absent"] = True
    payload["target_may_remain"] = False
    payload["target_manager_implicit_absence_proven"] = True
    tampered = probe._self_id_document(
        probe.FAILURE_DOMAIN, "preflight_failure_id", payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_failure_document(tampered, attempt, authority)


def test_failure_cannot_invent_full_removal_without_target_create_claim(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(fail_method="create_target"),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["target_identity_continuous"] is False
    assert failure["target_manager_stop_requested"] is False
    payload = dict(failure)
    payload.pop("preflight_failure_id")
    records = [dict(row) for row in payload["substage_records"]]
    primary_index = next(
        index
        for index, row in enumerate(records)
        if row["substage"] == "TARGET_CREATE"
    )
    primary = dict(records[primary_index])
    primary.pop("substage_record_id")
    marker_error = probe.TargetPostClaimValidationError(
        probe.TargetHandle(77, "forged", "/forged", "/forged", 91, 92)
    )
    error_type, message, error_number, error_name = probe._bounded_error(
        marker_error
    )
    primary.update(
        {
            "errno": error_number,
            "errno_name": error_name,
            "error_type": error_type,
            "message": message,
        }
    )
    records[primary_index] = probe._self_id_document(
        probe.SUBSTAGE_DOMAIN, "substage_record_id", primary
    )
    removal_index = next(
        index
        for index, row in enumerate(records)
        if row["substage"] == "CLEANUP_TARGET_REMOVE"
    )
    removal = dict(records[removal_index])
    removal.pop("substage_record_id")
    contract = authority["systemd_invocation_contract"][
        "target_lifecycle_contract"
    ]
    removal["detail"] = {
        "removed": True,
        "already_absent": False,
        "owned_device": 91,
        "owned_inode": 92,
        "manager_stop_argv": contract["stop_argv"],
        "manager_stop_environment": contract["environment"],
        "manager_stop_returncode": 0,
        "manager_stop_stdout": probe._output_fact(b""),
        "manager_stop_stderr": probe._output_fact(b""),
        "manager_final_properties": FakeRuntime._manager_absent_properties(),
        "manager_poll_count": 1,
        "probe_path_deletion_calls": 0,
        "manager_implicit_absence_proven": True,
        "named_path_detached_and_manager_implicit_absence": True,
    }
    records[removal_index] = probe._self_id_document(
        probe.SUBSTAGE_DOMAIN, "substage_record_id", removal
    )
    payload["substage_records"] = records
    payload.update(
        {
            "errno": error_number,
            "errno_name": error_name,
            "error_type": error_type,
            "message": message,
        }
    )
    payload["target_identity_continuous"] = True
    payload["target_manager_stop_requested"] = True
    tampered = probe._self_id_document(
        probe.FAILURE_DOMAIN, "preflight_failure_id", payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_failure_document(tampered, attempt, authority)


def test_target_create_deadline_gate_preserves_typed_precreate_absence_failure(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    samples = iter((1, 1, 1, 1, 1, probe.INNER_TOTAL_TIMEOUT_NS))
    runtime = FakeRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: next(samples),
                process_entry_ns=0,
                deadline_ns=probe.INNER_TOTAL_TIMEOUT_NS,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "TARGET_CREATE"
    assert failure["errno"] == errno.ETIMEDOUT
    assert failure["target_absent"] is True
    assert "create_target" not in runtime.calls
    removal = next(
        row
        for row in failure["substage_records"]
        if row["substage"] == "CLEANUP_TARGET_REMOVE"
    )
    assert removal["detail"]["reason"] == "MANAGER_ABSENCE_ALREADY_PROVEN"
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_service_close_crossing_deadline_publishes_typed_failure(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    clock = FakeMonotonicClock(now_ns=1)
    deadline_ns = probe.INNER_TOTAL_TIMEOUT_NS

    class LateCloseRuntime(FakeRuntime):
        def close_service(self, service: probe.ServiceHandle) -> None:
            super().close_service(service)
            clock.now_ns = deadline_ns

    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=LateCloseRuntime(),
                environ=environment,
                monotonic_ns=clock.read,
                process_entry_ns=0,
                deadline_ns=deadline_ns,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
        assert not store.exists(probe.RECEIPT_NAME)
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "SERVICE_HANDLE_CLOSE"
    assert failure["errno"] == errno.ETIMEDOUT
    assert failure["substage_records"][-1]["substage"] == (
        "CLEANUP_SERVICE_ALREADY_CLOSED"
    )
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_receipt_prepublication_deadline_gate_closes_typed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    clock = FakeMonotonicClock(now_ns=1)
    deadline_ns = probe.INNER_TOTAL_TIMEOUT_NS
    original_build = probe._build_receipt

    def build_then_expire(*args, **kwargs):
        receipt = original_build(*args, **kwargs)
        clock.now_ns = deadline_ns
        return receipt

    monkeypatch.setattr(probe, "_build_receipt", build_then_expire)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=clock.read,
                process_entry_ns=0,
                deadline_ns=deadline_ns,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
        assert not store.exists(probe.RECEIPT_NAME)
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "RECEIPT_PUBLICATION"
    assert failure["errno"] == errno.ETIMEDOUT
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_exact_receipt_published_after_deadline_is_uncertain_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, raw, environment = _authority(tmp_path)
    clock = FakeMonotonicClock(now_ns=1)
    deadline_ns = probe.INNER_TOTAL_TIMEOUT_NS
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        original_write = store.write_once

        def write_then_expire(
            name, artifact_raw, *, token=None, pre_open=None
        ):
            original_write(
                name, artifact_raw, token=token, pre_open=pre_open
            )
            if name == probe.RECEIPT_NAME:
                clock.now_ns = deadline_ns

        monkeypatch.setattr(store, "write_once", write_then_expire)
        with pytest.raises(probe.ReceiptPublicationUncertain):
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(),
                environ=environment,
                monotonic_ns=clock.read,
                process_entry_ns=0,
                deadline_ns=deadline_ns,
            )
        assert store.exists(probe.RECEIPT_NAME)
        assert not store.exists(probe.FAILURE_NAME)


def test_target_remove_identity_loss_publishes_typed_conservative_failure(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class IdentityLossRuntime(FakeRuntime):
        def remove_target(self, _service, target, _deadline_ns: int):
            self.calls.append("remove_target")
            assert target is not None
            target.identity_continuous = False
            target.residual_possible = True
            cause = OSError(errno.ESTALE, "fixture manager/path identity loss")
            outer = probe.make_target_removal_error(
                error_number=errno.ESTALE,
                message="owned target pre-stop identity failed",
                cause=cause,
                diagnostic_arguments={
                            "target": target,
                            "manager_stop_result": None,
                            "manager_stop_requested": False,
                            "manager_poll_count": 0,
                        "last_manager_properties": None,
                        "target_path_absent": None,
                        "transient_fragment_absent": None,
                        "transient_fragment_path": None,
                        "transient_fragment_stat_errno": None,
                        "parent_named_path_observation": None,
                        "retained_ofd_detach_fact": None,
                        "replacement_detected": False,
                        "manager_implicit_absence_proven": False,
                    "named_path_detached_and_manager_implicit_absence": False,
                    "exception_phase": "PRESTOP_IDENTITY",
                },
            )
            raise outer from cause

    runtime = IdentityLossRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "TARGET_REMOVE"
    assert failure["errno"] == errno.ESTALE
    assert failure["target_absent"] is False
    assert failure["target_identity_continuous"] is False
    cleanup_remove = next(
        row
        for row in failure["substage_records"]
        if row["substage"] == "CLEANUP_TARGET_REMOVE"
    )
    assert cleanup_remove["status"] == "FAILED"
    cleanup_diagnostic = probe.validate_target_cleanup_diagnostic(
        cleanup_remove["detail"]
    )
    assert cleanup_diagnostic["exception_phase"] == "PRESTOP_IDENTITY"
    assert cleanup_diagnostic["manager_stop_requested"] is False
    assert failure["target_manager_stop_requested"] is False
    assert failure["requested_manager_stop_identity_binding"] == (
        probe.MANAGER_STOP_NOT_DISPATCHED
    )
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_bad_service_detail_retains_handle_but_publishes_typed_failure(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class BadServiceDetailRuntime(FakeRuntime):
        def inspect_service(self, authority_value, deadline_ns: int):
            service, detail = super().inspect_service(
                authority_value, deadline_ns
            )
            forged = {**detail, "service_device": detail["service_device"] + 1}
            return service, forged

    runtime = BadServiceDetailRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
        assert store.exists(probe.FAILURE_NAME)
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "SERVICE_PLACEMENT_AND_NCA_PERMISSION"
    assert failure["error_type"] == "AuthorityError"
    assert failure["target_absent"] is True
    assert failure["target_manager_implicit_absence_proven"] is True
    removal = next(
        row
        for row in failure["substage_records"]
        if row["substage"] == "CLEANUP_TARGET_REMOVE"
    )
    absence = next(
        row
        for row in failure["substage_records"]
        if row["substage"] == "CLEANUP_TARGET_ABSENT"
    )
    assert removal["detail"]["reason"] == (
        "NO_CONTINUOUS_MANAGER_OWNERSHIP_CLAIM"
    )
    assert absence["status"] == "OK"
    assert probe.validate_failure_document(failure, attempt, authority) == failure


@pytest.mark.parametrize(
    ("malformation", "failed_substage"),
    [
        ("service_return", "SERVICE_PLACEMENT_AND_NCA_PERMISSION"),
        ("target_return", "TARGET_CREATE"),
        ("target_exception", "TARGET_CREATE"),
    ],
)
def test_malformed_runtime_handles_publish_typed_failure_without_dereference(
    tmp_path: Path, malformation: str, failed_substage: str
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class MalformedHandleRuntime(FakeRuntime):
        def inspect_service(self, authority_value, deadline_ns: int):
            if malformation == "service_return":
                self.calls.append("inspect_service")
                return object(), {}
            return super().inspect_service(authority_value, deadline_ns)

        def create_target(self, service, deadline_ns: int):
            if malformation == "target_return":
                self.calls.append("create_target")
                return object(), {}
            if malformation == "target_exception":
                self.calls.append("create_target")
                raise probe.TargetCreationError(
                    errno.EPROTO,
                    "fixture malformed target claim",
                    target=object(),
                )
            return super().create_target(service, deadline_ns)

    runtime = MalformedHandleRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == failed_substage
    assert failure["target_identity_continuous"] is False
    assert failure["target_manager_stop_requested"] is False
    assert probe.validate_failure_document(failure, attempt, authority) == failure
    if malformation == "service_return":
        assert "close_service" not in runtime.calls
    else:
        assert "close_service" in runtime.calls


def test_nonwrapper_create_detail_drift_with_valid_claim_closes_typed_failure(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class MalformedDetailRuntime(FakeRuntime):
        def create_target(self, service, deadline_ns: int):
            target, detail = super().create_target(service, deadline_ns)
            return target, {**detail, "target_name": "forged-target-name"}

    runtime = MalformedDetailRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "TARGET_CREATE"
    assert failure["errno"] == errno.EPROTO
    assert failure["error_type"] == "TargetPostClaimValidationError"
    assert failure["target_absent"] is True
    assert failure["target_identity_continuous"] is True
    assert failure["target_manager_stop_requested"] is True
    assert "remove_target" in runtime.calls
    cleanup_remove = next(
        row
        for row in failure["substage_records"]
        if row["substage"] == "CLEANUP_TARGET_REMOVE"
    )
    assert cleanup_remove["status"] == "OK"
    assert (store.root / probe.FAILURE_NAME).exists()
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_generic_clone_failure_cannot_forge_partial_child_cleanup_proof(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=FakeRuntime(fail_method="clone_child"),
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "CLONE3_ATOMIC_BIRTH"
    assert failure["error_type"] != "ClonePostAcquireValidationError"
    assert failure["child_reaped"] is False
    payload = dict(failure)
    payload.pop("preflight_failure_id")
    original = [dict(row) for row in payload["substage_records"]]
    primary_index = next(
        index
        for index, row in enumerate(original)
        if row["substage"] == "CLONE3_ATOMIC_BIRTH"
    )
    records = original[: primary_index + 1]
    primary = dict(records[primary_index])
    primary.pop("substage_record_id")
    marker_error = probe.ClonePostAcquireValidationError(
        probe.ChildHandle(999999, 77, None)
    )
    error_type, message, error_number, error_name = probe._bounded_error(
        marker_error
    )
    primary.update(
        {
            "errno": error_number,
            "errno_name": error_name,
            "error_type": error_type,
            "message": message,
        }
    )
    records[primary_index] = probe._self_id_document(
        probe.SUBSTAGE_DOMAIN, "substage_record_id", primary
    )
    records.extend(
        (
            probe._substage_record(
                len(records),
                "CLEANUP_PIDFD_KILL",
                "OK",
                {"signal": "SIGKILL", "pidfd_send_signal_errno": None},
            ),
            probe._substage_record(
                len(records) + 1,
                "CLEANUP_CHILD_REAP",
                "OK",
                {
                    "already_reaped": False,
                    "pid": 999999,
                    "si_code": os.CLD_KILLED,
                    "si_status": 9,
                },
            ),
            probe._substage_record(
                len(records) + 2,
                "CLEANUP_CHILD_CLOSE",
                "OK",
                {"child_handle_closed": True},
            ),
        )
    )
    for retained in original[primary_index + 1 :]:
        row = dict(retained)
        row.pop("substage_record_id")
        row["index"] = len(records)
        records.append(
            probe._self_id_document(
                probe.SUBSTAGE_DOMAIN, "substage_record_id", row
            )
        )
    payload["substage_records"] = records
    payload.update(
        {
            "errno": error_number,
            "errno_name": error_name,
            "error_type": error_type,
            "message": message,
        }
    )
    payload["child_reaped"] = True
    payload["process_may_remain"] = False
    tampered = probe._self_id_document(
        probe.FAILURE_DOMAIN, "preflight_failure_id", payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_failure_document(tampered, attempt, authority)


def test_uncertain_provisional_clone_containment_publishes_process_may_remain(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class UncertainProvisionalCloneRuntime(FakeRuntime):
        def clone_child(self, _target, _deadline_ns: int):
            self.calls.append("clone_child")
            setup_error = OSError(errno.EIO, "injected post-clone setup failure")
            raise probe.CloneProvisionalContainmentError(
                setup_error,
                child_pid=7002,
                child_pidfd=81,
                child_reaped=False,
                resources_closed=True,
                containment_errors=(
                    OSError(errno.EIO, "injected provisional wait failure"),
                ),
            )

    runtime = UncertainProvisionalCloneRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "CLONE3_ATOMIC_BIRTH"
    assert failure["error_type"] == "CloneProvisionalContainmentError"
    assert failure["child_reaped"] is False
    assert failure["process_may_remain"] is True
    assert not any(
        row["substage"].startswith("CLEANUP_CHILD_")
        or row["substage"] == "CLEANUP_PIDFD_KILL"
        for row in failure["substage_records"]
    )
    assert probe.validate_failure_document(failure, attempt, authority) == failure


@pytest.mark.parametrize("bad_detail", [["not-a-pair"], {"pid": -1}])
def test_partial_clone_child_with_bad_detail_has_typed_cleanup_failure(
    tmp_path: Path, bad_detail: object
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class BadCloneDetailRuntime(FakeRuntime):
        def clone_child(self, target, deadline_ns: int):
            child, _detail = super().clone_child(target, deadline_ns)
            return child, bad_detail

    runtime = BadCloneDetailRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
        attempt = probe.loads_canonical_json(store.read_exact(probe.ATTEMPT_NAME))
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "CLONE3_ATOMIC_BIRTH"
    assert failure["error_type"] == "ClonePostAcquireValidationError"
    assert failure["child_reaped"] is False
    assert failure["process_may_remain"] is True
    assert failure["target_absent"] is True
    cleanup_names = [
        row["substage"]
        for row in failure["substage_records"]
        if row["substage"].startswith("CLEANUP_CHILD_")
        or row["substage"] == "CLEANUP_PIDFD_KILL"
    ]
    assert cleanup_names == [
        "CLEANUP_PIDFD_KILL",
        "CLEANUP_CHILD_REAP",
        "CLEANUP_CHILD_CLOSE",
    ]
    assert probe.validate_failure_document(failure, attempt, authority) == failure


def test_eexist_before_service_claim_keeps_failure_absence_conservative(
    tmp_path: Path,
) -> None:
    authority, raw, environment = _authority(tmp_path)

    class EexistRuntime(FakeRuntime):
        def inspect_service(self, _authority, _deadline_ns: int):
            self.calls.append("inspect_service")
            raise OSError(errno.EEXIST, "fixture fixed target is foreign")

    runtime = EexistRuntime()
    with _artifact_store(tmp_path) as store:
        _seed_outer_attempt(store, authority, raw)
        with pytest.raises(probe.ProbeRunFailure) as raised:
            probe.run_probe_once(
                authority=authority,
                external_root_raw=raw,
                store=store,
                runtime=runtime,
                environ=environment,
                monotonic_ns=lambda: 1_000_000,
            )
    failure = raised.value.failure_document
    assert failure["failed_substage"] == "SERVICE_PLACEMENT_AND_NCA_PERMISSION"
    assert failure["errno"] == errno.EEXIST
    assert failure["target_absent"] is False
    assert failure["target_may_remain"] is True
    assert "remove_target" not in runtime.calls
    attempt = probe.loads_canonical_json(
        (tmp_path / probe.ARTIFACT_ROOT_RELATIVE_PATH / probe.ATTEMPT_NAME).read_bytes()
    )
    assert probe.validate_failure_document(failure, attempt, authority) == failure
    payload = dict(failure)
    del payload["preflight_failure_id"]
    payload["target_absent"] = True
    tampered = probe._self_id_document(
        probe.FAILURE_DOMAIN, "preflight_failure_id", payload
    )
    with pytest.raises(probe.AuthorityError):
        probe.validate_failure_document(tampered, attempt, authority)


def test_git_call_counts_and_shared_hard_timeout_are_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = _materialize_committed_fixture(tmp_path)
    authority = probe.collect_post_c_probe_authority(
        tmp_path,
        git_stdout=fake_git,
        host_observer=_host_parent_fact,
        require_running_source=False,
    )
    assert len(fake_git.calls) == probe.PREPARE_GIT_CALL_COUNT
    fake_git.calls.clear()
    probe._validate_c_probe_git_authority(
        tmp_path, authority, git_stdout=fake_git
    )
    assert len(fake_git.calls) == probe.INNER_GIT_CALL_COUNT

    class Process:
        timeout: int | None = None

        def run(self, argv, *, timeout_seconds, stdout_cap, stderr_cap, env=None, start_new_session=False):
            self.timeout = timeout_seconds
            return probe.BoundedProcessResult(tuple(argv), 0, b"ok\n", b"", False, False)

    process = Process()
    monkeypatch.setattr(probe, "DEFAULT_SUBPROCESS_ADAPTER", process)
    now = probe.time.monotonic_ns()
    assert probe._git_stdout(
        tmp_path,
        ("rev-parse", "--verify", "HEAD"),
        deadline_ns=now + 20_000_000_000,
    ) == b"ok\n"
    assert process.timeout == probe.GIT_CALL_TIMEOUT_SECONDS


def test_module_ast_has_no_duplicate_top_level_definitions() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assert node.name not in names
            names.add(node.name)
