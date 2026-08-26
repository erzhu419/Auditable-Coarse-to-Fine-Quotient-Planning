from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import types
import ctypes

import pytest

from acfqp import construction_k7_campaign_measurement_worker_v180r12r3r2 as core


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


supervise = _load(
    "_test_supervise_v180r12r3r2", "scripts/supervise_v180r12r3r2_campaign_measurement.py"
)
work = _load("_test_work_for_supervise_v180r12r3r2", "scripts/work_v180r12r3r2_campaign_measurement.py")


def _sealed_read_only(raw: bytes) -> int:
    writable = supervise._memfd_create("v180r12r3r2-test")
    os.write(writable, raw)
    os.fchmod(writable, 0o400)
    fcntl.fcntl(writable, supervise.F_ADD_SEALS, supervise.REQUIRED_SEAL_MASK)
    readonly = os.open(f"/proc/self/fd/{writable}", os.O_RDONLY | os.O_CLOEXEC)
    os.close(writable)
    return readonly


def _close_if_open(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        pass


def test_stable_openat_and_symlink_attack(tmp_path: Path) -> None:
    fact = core.FROZEN_INPUT_FACTS_V180R12R3R2[1]
    target = tmp_path / fact.relative_path
    target.parent.mkdir(parents=True)
    target.write_bytes(b"v" * fact.byte_count)
    root_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        observed = supervise.read_frozen_input_openat_v180r12r3r2(root_fd, fact)
        assert observed.returned_bytes == b"v" * fact.byte_count
        assert sum(observed.returned_chunk_byte_counts) == fact.byte_count
        target.unlink()
        target.symlink_to("missing")
        with pytest.raises(OSError):
            supervise.read_frozen_input_openat_v180r12r3r2(root_fd, fact)
    finally:
        os.close(root_fd)


def test_sealed_memfd_visibility_and_subject_noreplace_commit(tmp_path: Path) -> None:
    stage = supervise.stage_sealed_memfd_v180r12r3r2(
        core.CampaignInputRoleV180R12R3R2.TERMINAL, b"payload" * 10
    )
    try:
        assert stage.observed_seal_mask == supervise.REQUIRED_SEAL_MASK
        assert stat.S_IMODE(os.fstat(stage.worker_source_descriptor).st_mode) == 0o400
        assert fcntl.fcntl(stage.worker_source_descriptor, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
    finally:
        supervise.close_sealed_stage_v180r12r3r2(stage)

    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        local = Path(local_text)
        directory_fd = os.open(local, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        handle = supervise.preopen_subject_output_v180r12r3r2(directory_fd)
        raw = b'{"subject":"synthetic"}'
        try:
            write = work.write_subject_result_v180r12r3r2(handle.worker_source_descriptor, raw)
            assert write.returned_byte_count == len(raw)
            commit = supervise.commit_subject_output_v180r12r3r2(handle, raw)
            assert commit.returned_bytes == raw
            assert (local / handle.final_name).read_bytes() == raw
            assert (local / handle.final_name).stat().st_mode & 0o777 == 0o400
            with pytest.raises(supervise.V180R12R3R2SupervisorRuntimeError):
                supervise.preopen_subject_output_v180r12r3r2(directory_fd)
        finally:
            _close_if_open(handle.worker_source_descriptor)
            _close_if_open(handle.descriptor)
            os.close(directory_fd)


def test_subject_and_stage_modes_ignore_hostile_umask(tmp_path: Path) -> None:
    assert supervise.SUBJECT_RESULT_RUNTIME_BYTE_CAP == 768 * 1024
    assert (
        supervise.SUBJECT_RESULT_RUNTIME_BYTE_CAP
        == work.SUBJECT_RESULT_RUNTIME_BYTE_CAP
    )
    # Desktop pytest may place tmp_path on drvfs, which does not necessarily
    # preserve chmod bits.  The runtime contract is Linux-only, so exercise it
    # on a native temporary filesystem.
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        previous = os.umask(0o777)
        try:
            stage = supervise.stage_sealed_memfd_v180r12r3r2(
                core.CampaignInputRoleV180R12R3R2.VERIFICATION, b"sealed"
            )
            directory_fd = os.open(
                local_text, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
            )
            handle = supervise.preopen_subject_output_v180r12r3r2(directory_fd)
        finally:
            os.umask(previous)
        try:
            assert stat.S_IMODE(os.fstat(stage.supervisor_descriptor).st_mode) == 0o400
            assert stat.S_IMODE(os.fstat(stage.worker_source_descriptor).st_mode) == 0o400
            assert stat.S_IMODE(os.fstat(handle.descriptor).st_mode) == 0o600
        finally:
            supervise.close_sealed_stage_v180r12r3r2(stage)
            _close_if_open(handle.worker_source_descriptor)
            _close_if_open(handle.descriptor)
            os.close(directory_fd)


def test_bootstrap_context_dispatch_validates_fixed_fds_and_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_source = _sealed_read_only(b"precompiled")
    observer, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    repo_source = os.open(tmp_path, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    cgroup_source = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    fixed = (240, 241, 244, 245)
    for descriptor in (242, 243):
        _close_if_open(descriptor)
    try:
        for source, target in (
            (bundle_source, 240), (child.fileno(), 241),
            (repo_source, 244), (cgroup_source, 245),
        ):
            os.dup2(source, target, inheritable=False)
        payload = types.MappingProxyType(
            {"repository_root_fd": 244, "worker_cgroup_fd": 245}
        )
        protocol_id = "1" * 64
        authorization_id = "2" * 64
        authorization_evidence_id = "3" * 64
        execution_slot_id = "4" * 64
        logical_occurrence_id = "5" * 64
        execution_nonce = "6" * 64
        attempt_id = supervise.identity_domains.derive_campaign_measurement_attempt_id_v180r12r3r2(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            authorization_evidence_id=authorization_evidence_id,
            campaign_measurement_execution_slot_id=execution_slot_id,
            logical_occurrence_id=logical_occurrence_id,
            execution_nonce=execution_nonce,
        )
        launch_operation_id = (
            supervise.supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r3r2(
                attempt_id
            )[1].operation_id
        )
        context = types.MappingProxyType(
            {
                "schema": "acfqp.v180r12r3r2_verified_internal_launch_context.v1",
                "target": "supervisor",
                "actor_role": "SUPERVISOR",
                "parent_actor_role": "OBSERVER",
                "protocol_id": protocol_id,
                "authorization_id": authorization_id,
                "authorization_evidence_id": authorization_evidence_id,
                "attempt_id": attempt_id,
                "campaign_measurement_execution_slot_id": execution_slot_id,
                "logical_occurrence_id": logical_occurrence_id,
                "execution_nonce": execution_nonce,
                "prelaunch_materialization_terminal_id": "7" * 64,
                "prelaunch_launch_rule_id": "8" * 64,
                "measurement_launch_attempt_id": "9" * 64,
                "launch_operation_id": launch_operation_id,
                "manifest_sha256": "a" * 64,
                "precompiled_source_bundle_sha256": "b" * 64,
                "inherited_fd_roles": supervise._EXPECTED_FD_ROLES,
                "target_payload": payload,
                "parent_to_child_mac_key": b"k" * 32,
                "parent_context_mac": "c" * 64,
                "context_consumed_once": True,
            }
        )
        seen = []
        monkeypatch.setattr(
            supervise,
            "_run_bootstrap_verified_supervisor_v180r12r3r2",
            lambda value: seen.append(value),
        )
        assert supervise.bootstrap_entrypoint_v180r12r3r2(context) is None
        assert seen == [context]
        bad = dict(context)
        bad["actor_role"] = "WORKER"
        with pytest.raises(supervise.V180R12R3R2SupervisorRuntimeError):
            supervise.bootstrap_entrypoint_v180r12r3r2(types.MappingProxyType(bad))
    finally:
        for descriptor in fixed:
            _close_if_open(descriptor)
        for descriptor in (bundle_source, repo_source, cgroup_source):
            _close_if_open(descriptor)
        observer.close()
        child.close()


def test_subject_writer_close_rejects_same_inode_write_alias() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        directory_fd = os.open(
            local_text, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        )
        handle = supervise.preopen_subject_output_v180r12r3r2(directory_fd)
        alias = -1
        raw = b"subject-alias-attack"
        try:
            work.write_subject_result_v180r12r3r2(
                handle.worker_source_descriptor, raw
            )
            alias = os.open(
                f"/proc/self/fd/{handle.worker_source_descriptor}",
                os.O_WRONLY | os.O_CLOEXEC,
            )
            with pytest.raises(supervise.V180R12R3R2SupervisorRuntimeError):
                supervise.close_subject_writer_before_readback_v180r12r3r2(
                    handle, expected_byte_count=len(raw)
                )
        finally:
            _close_if_open(alias)
            _close_if_open(handle.worker_source_descriptor)
            _close_if_open(handle.descriptor)
            os.close(directory_fd)


def test_failure_cleanup_never_closes_a_reused_foreign_descriptor() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        owned_path = Path(local_text) / "owned"
        foreign_path = Path(local_text) / "foreign"
        owned_path.write_bytes(b"owned")
        foreign_path.write_bytes(b"foreign")
        descriptor = os.open(owned_path, os.O_RDONLY | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        os.close(descriptor)
        foreign = os.open(foreign_path, os.O_RDONLY | os.O_CLOEXEC)
        try:
            if foreign != descriptor:
                os.dup2(foreign, descriptor, inheritable=False)
                os.close(foreign)
                foreign = descriptor
            supervise._close_descriptor_if_same_inode_v180r12r3r2(
                descriptor,
                device=metadata.st_dev,
                inode=metadata.st_ino,
            )
            assert os.fstat(descriptor).st_ino == foreign_path.stat().st_ino
        finally:
            _close_if_open(foreign)


def _synthetic_worker_launch_arguments() -> dict:
    context = {
        "protocol_id": "1" * 64,
        "authorization_id": "2" * 64,
        "authorization_evidence_id": "3" * 64,
        "attempt_id": "4" * 64,
        "campaign_measurement_execution_slot_id": "5" * 64,
        "logical_occurrence_id": "6" * 64,
        "execution_nonce": "7" * 64,
        "prelaunch_materialization_terminal_id": "8" * 64,
        "prelaunch_launch_rule_id": "9" * 64,
        "measurement_launch_attempt_id": "a" * 64,
        "manifest_sha256": "b" * 64,
        "precompiled_source_bundle_sha256": "c" * 64,
    }
    stage = types.SimpleNamespace(
        terminal_stage=types.SimpleNamespace(
            byte_count=199_755, worker_source_descriptor=1001
        ),
        verification_stage=types.SimpleNamespace(
            byte_count=2_752, worker_source_descriptor=1002
        ),
    )
    return {
        "context": context,
        "start": {},
        "topology": object(),
        "stage_effects": stage,
        "subject_output": types.SimpleNamespace(worker_source_descriptor=1003),
        "operation_id": "d" * 64,
    }


def test_worker_clone_rejects_short_random_key_before_clone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = object.__new__(supervise._LinuxWorkerProcessAdapterV180R12R3R2)
    adapter.libc = types.SimpleNamespace(
        syscall=lambda *args: (_ for _ in ()).throw(
            AssertionError("clone3 must not run after short getrandom")
        )
    )
    monkeypatch.setattr(
        supervise,
        "_internal_exec_argv_v180r12r3r2",
        lambda target: tuple(str(index) for index in range(11)),
    )
    monkeypatch.setattr(supervise.os, "getrandom", lambda count: b"x" * 31)
    with pytest.raises(
        supervise.V180R12R3R2SupervisorRuntimeError,
        match="short worker channel key",
    ):
        adapter.launch_worker(**_synthetic_worker_launch_arguments())


def test_positive_clone_without_pidfd_kills_and_reaps_direct_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = object.__new__(supervise._LinuxWorkerProcessAdapterV180R12R3R2)
    adapter.libc = types.SimpleNamespace(syscall=lambda *args: 4321)
    monkeypatch.setattr(
        supervise,
        "_internal_exec_argv_v180r12r3r2",
        lambda target: (
            "/usr/bin/python3", "-I", "-S", "-B", "-X", "pycache", "/b",
            target, "/repo", "/pre", "/pre/manifest",
        ),
    )
    monkeypatch.setattr(supervise.os, "getrandom", lambda count: b"x" * count)
    opened: list[int] = []

    def sealed(name, raw):
        del name, raw
        descriptor = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(supervise, "_sealed_read_only_memfd_v180r12r3r2", sealed)
    killed: list[tuple[int, int]] = []
    waited: list[tuple[int, int]] = []
    monkeypatch.setattr(
        supervise.os, "kill", lambda pid, sig: killed.append((pid, sig))
    )
    monkeypatch.setattr(
        supervise.os, "waitpid", lambda pid, flags: waited.append((pid, flags))
    )
    with pytest.raises(
        supervise.V180R12R3R2SupervisorRuntimeError,
        match="without its pidfd",
    ):
        adapter.launch_worker(**_synthetic_worker_launch_arguments())
    assert killed == [(4321, supervise.signal.SIGKILL)]
    assert waited == [(4321, 0)]
    assert all(_fd_is_closed(descriptor) for descriptor in opened)


def test_pidfd_signal_failure_falls_back_to_direct_child_and_closes_pidfd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pidfd, pidfd_writer = os.pipe2(os.O_CLOEXEC)

    class Libc:
        def syscall(self, number, *arguments):
            if number == supervise._LinuxWorkerProcessAdapterV180R12R3R2.clone3_number:
                clone_arguments = arguments[0]._obj
                ctypes.c_int.from_address(clone_arguments.pidfd).value = pidfd
                return 4321
            assert number == supervise._LinuxWorkerProcessAdapterV180R12R3R2.pidfd_send_signal_number
            return -1

    adapter = object.__new__(supervise._LinuxWorkerProcessAdapterV180R12R3R2)
    adapter.libc = Libc()
    monkeypatch.setattr(
        supervise,
        "_internal_exec_argv_v180r12r3r2",
        lambda target: (
            "/usr/bin/python3", "-I", "-S", "-B", "-X", "pycache", "/b",
            target, "/repo", "/pre", "/pre/manifest",
        ),
    )
    monkeypatch.setattr(supervise.os, "getrandom", lambda count: b"x" * count)
    monkeypatch.setattr(
        supervise,
        "_sealed_read_only_memfd_v180r12r3r2",
        lambda name, raw: os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC),
    )
    monkeypatch.setattr(
        supervise,
        "_pidfd_info_v180r12r3r2",
        lambda descriptor: (_ for _ in ()).throw(RuntimeError("synthetic birth observation")),
    )
    killed: list[tuple[int, int]] = []
    waited: list[tuple[int, int]] = []
    monkeypatch.setattr(
        supervise.os, "kill", lambda pid, sig: killed.append((pid, sig))
    )
    monkeypatch.setattr(
        supervise.os, "waitpid", lambda pid, flags: waited.append((pid, flags))
    )
    try:
        with pytest.raises(RuntimeError, match="synthetic birth observation"):
            adapter.launch_worker(**_synthetic_worker_launch_arguments())
        assert killed == [(4321, supervise.signal.SIGKILL)]
        assert waited == [(4321, 0)]
        assert _fd_is_closed(pidfd)
    finally:
        _close_if_open(pidfd)
        _close_if_open(pidfd_writer)


def _fd_is_closed(descriptor: int) -> bool:
    try:
        os.fstat(descriptor)
    except OSError:
        return True
    return False


def test_direct_main_is_forbidden() -> None:
    with pytest.raises(supervise.V180R12R3R2SupervisorRuntimeError):
        supervise.main([])
