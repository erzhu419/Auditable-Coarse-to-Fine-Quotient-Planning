from __future__ import annotations

from dataclasses import dataclass
import array
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import types
from types import SimpleNamespace

import pytest

from acfqp import (
    construction_k7_campaign_measurement_authorization_evidence_freeze_v180r12r4
    as authorization_evidence,
)
from acfqp import (
    construction_k7_campaign_measurement_execution_authorization_v180r12r4
    as authorization,
)
from acfqp import construction_k7_campaign_measurement_ledger_v180r12r4 as ledger
from acfqp import construction_k7_campaign_measurement_supervisor_v180r12r4 as supervisor
from acfqp import construction_k7_campaign_measurement_worker_v180r12r4 as worker
from test_construction_k7_campaign_measurement_protocol_v180r12r4 import (
    cgroup_parent_fact,
    runtime_capability_fact,
)


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run = _load("_test_run_v180r12r4", "scripts/run_v180r12r4_campaign_measurement.py")


def _attempt_fixture():
    authority = run.CampaignAttemptAuthorityV180R12R4(
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
    document, manifest = run.build_campaign_attempt_record_v180r12r4(authority)
    return authority, document, manifest


def _ids() -> tuple[str, str, str]:
    authority, _document, _manifest = _attempt_fixture()
    return authority.protocol_id, authority.authorization_id, authority.attempt_id


def _production_invocation(target: str) -> dict[str, object]:
    token, unit_name = run.PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
    return {
        "schema": run.protocol.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_SCHEMA,
        "token_domain": run.PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN,
        "target": target,
        "token_input": {},
        "token": token,
        "unit_name": unit_name,
        "unit_kind": "SERVICE_NOT_SCOPE",
        "slice": "app.slice",
        "service_type": "exec",
        "delegate": True,
        "umask": "0077",
        "launcher_command": [],
        "systemd_run_argv": [],
    }


def _placement_t1(target: str) -> dict[str, object]:
    token, unit_name = run.PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
    return {
        "schema": run.PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA,
        "target": target,
        "token": token,
        "unit_name": unit_name,
        "slice": "app.slice",
        "source_membership": "0::/app.slice/" + unit_name,
        "expected_source_membership": "0::/app.slice/" + unit_name,
        "self_pid": 123,
        "self_pid_in_source_cgroup_procs": True,
        "cgroup_namespace_inode": 456,
        "delegated_parent_fd_fact": {},
        "cgroup2_mount_fd_fact": {},
        "source_service_fd_fact": {"device": 1, "inode": 2},
        "nearest_common_ancestor_path": "/sys/fs/cgroup/app.slice",
        "nearest_common_ancestor_is_app_slice": True,
        "parent_cgroup_procs_o_wronly_openable": True,
        "planned_measurement_root_observation": {"root_state": "ABSENT"},
        "planned_measurement_root_absent": True,
        "t1_complete_before_child_popen": True,
    }


def test_emergency_reserve_is_exact_committed_heap_and_precedes_attempt(
    tmp_path: Path,
) -> None:
    store = run.DurableStoreV180R12R4(tmp_path)
    try:
        reserve = store.reserve_failure_space()
        assert type(reserve) is bytearray
        assert len(reserve) == run.protocol.FAILURE_EMERGENCY_RESERVE_BYTES == 4 * 1024 * 1024
        assert reserve[0] == reserve[4096] == 1
        reserve.clear()

        order: list[str] = []
        original_reserve = store.reserve_failure_space
        original_write = store.write_once

        def reserve_first():
            order.append("reserve")
            return original_reserve()

        def write_after(relative_path, raw, *, mode=0o400):
            if relative_path == run.ATTEMPT_RELATIVE_PATH:
                order.append("attempt")
            return original_write(relative_path, raw, mode=mode)

        store.reserve_failure_space = reserve_first
        store.write_once = write_after
        authority, attempt, _manifest = _attempt_fixture()
        claim = run.claim_attempt_before_effects_v180r12r4(
            store,
            attempt,
            authority=authority,
            forbidden_progress_paths=(),
        )
        assert order == ["reserve", "attempt"]
        claim.failure_reserve.clear()
    finally:
        store.close()


def test_t2_failure_precedes_scientific_attempt_o_excl(tmp_path: Path) -> None:
    authority, attempt, _manifest = _attempt_fixture()
    store = run.DurableStoreV180R12R4(tmp_path)
    primary = OSError(errno.EPERM, "injected T2 placement drift")

    def fail_t2() -> None:
        raise primary

    try:
        with pytest.raises(OSError) as captured:
            run.run_one_shot_outer_v180r12r4(
                store=store,
                adapter=object(),
                attempt_document=attempt,
                attempt_authority=authority,
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
                campaign_deadline_ns=(
                    run.time.monotonic_ns() + 30 * run.NANOSECONDS_PER_SECOND
                ),
                forbidden_progress_paths=(run.ATTEMPT_RELATIVE_PATH,),
                pre_attempt_revalidate=fail_t2,
            )
        assert captured.value is primary
        assert not (tmp_path / run.ATTEMPT_RELATIVE_PATH).exists()
        assert not (tmp_path / run.FAILURE_RELATIVE_PATH).exists()
    finally:
        store.close()


@pytest.mark.parametrize(
    "substage,flags",
    [
        ("T3_BEFORE_GETRANDOM", (False, False, False)),
        ("GETRANDOM", (False, False, False)),
        ("SOCKETPAIR", (False, False, False)),
        ("SOCKET_BUFFER_CONFIGURATION", (False, False, False)),
        ("SUPERVISOR_ARGV_AND_CONTEXT_BUILD", (False, False, False)),
        ("KEY_MEMFD_CREATE", (False, False, False)),
        ("CONTEXT_MEMFD_CREATE", (False, False, False)),
        ("TARGET_CGROUP_FSTAT", (False, False, False)),
        ("T3_IMMEDIATELY_BEFORE_CLONE3", (False, False, False)),
        ("EXEC_STATUS_PIPE", (False, False, False)),
        ("CLONE3", (False, False, False)),
        ("CHILD_PREEXEC", (True, True, False)),
        ("PIDFD_ACQUISITION", (True, True, False)),
        ("PROC_CHILD_IDENTITY_OBSERVATION", (True, True, True)),
        ("BIRTH_RECEIPT_CONSTRUCTION", (True, True, True)),
        ("AUTHENTICATED_CHANNEL_CONSTRUCTION", (True, True, True)),
    ],
)
def test_each_typed_launch_os_boundary_preserves_injected_primary(
    substage: str, flags: tuple[bool, bool, bool]
) -> None:
    primary = OSError(errno.EACCES, "injected launch boundary")

    def inject(observed: str) -> None:
        assert observed == substage
        raise primary

    with pytest.raises(OSError) as captured:
        run._launch_boundary_v180r12r4(
            substage,
            lambda: None,
            fault_injector=inject,
            child_created=flags[0],
            pidfd_acquired=flags[1],
            exec_observed=flags[2],
        )
    assert captured.value is primary
    assert primary.errno == errno.EACCES
    assert primary.launch_substage == substage
    assert primary.launch_errno == errno.EACCES
    assert (
        primary.launch_child_created,
        primary.launch_pidfd_acquired,
        primary.launch_exec_observed,
    ) == flags


def test_cloexec_status_pipe_distinguishes_exec_from_original_errno() -> None:
    status_read, status_write = os.pipe2(os.O_CLOEXEC)
    os.close(status_write)
    try:
        assert run._observe_child_exec_status_v180r12r4(status_read) is None
    finally:
        os.close(status_read)


def test_t3_revalidation_is_the_last_callback_before_real_clone3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeLibc:
        @staticmethod
        def syscall(*_arguments: object) -> int:
            events.append("clone3")
            run.ctypes.set_errno(errno.EPERM)
            return -1

    launcher = object.__new__(run.LinuxClone3V180R12R4)
    launcher.libc = FakeLibc()
    launcher.fault_injector = None
    monkeypatch.setattr(
        run.LinuxClone3V180R12R4,
        "validate_internal_exec_contract",
        staticmethod(lambda **_arguments: None),
    )
    target_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    try:
        with pytest.raises(OSError) as captured:
            launcher.launch_exec(
                role="SUPERVISOR",
                target_cgroup_fd=target_fd,
                expected_cgroup_membership_line="0::/app.slice/test.service/root/SUPERVISOR",
                argv=(),
                env={},
                inherited_fd_map={},
                pre_clone_revalidate=lambda: events.append("t3"),
            )
        assert captured.value.errno == errno.EPERM
        assert captured.value.launch_substage == "CLONE3"
        assert events == ["t3", "clone3"]
    finally:
        os.close(target_fd)


def test_adjacent_t3_injection_prevents_clone3_and_preserves_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = OSError(errno.EAGAIN, "injected adjacent T3")
    syscalls: list[str] = []

    class FakeLibc:
        @staticmethod
        def syscall(*_arguments: object) -> int:
            syscalls.append("clone3")
            return -1

    launcher = object.__new__(run.LinuxClone3V180R12R4)
    launcher.libc = FakeLibc()
    launcher.fault_injector = None
    monkeypatch.setattr(
        run.LinuxClone3V180R12R4,
        "validate_internal_exec_contract",
        staticmethod(lambda **_arguments: None),
    )

    def revalidate() -> None:
        run._launch_boundary_v180r12r4(
            "T3_IMMEDIATELY_BEFORE_CLONE3",
            lambda: None,
            fault_injector=lambda _substage: (_ for _ in ()).throw(primary),
        )

    target_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    try:
        with pytest.raises(OSError) as captured:
            launcher.launch_exec(
                role="SUPERVISOR",
                target_cgroup_fd=target_fd,
                expected_cgroup_membership_line="0::/app.slice/test.service/root/SUPERVISOR",
                argv=(),
                env={},
                inherited_fd_map={},
                pre_clone_revalidate=revalidate,
            )
        assert captured.value is primary
        assert primary.errno == errno.EAGAIN
        assert primary.launch_substage == "T3_IMMEDIATELY_BEFORE_CLONE3"
        assert primary.launch_errno == errno.EAGAIN
        assert syscalls == []
    finally:
        os.close(target_fd)


def test_sigalrm_mask_starts_after_preclone_fstat_and_pipe_and_wraps_second_t3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    masked = False
    original_fstat = run.os.fstat
    original_pipe2 = run.os.pipe2

    def tracked_fstat(descriptor: int):
        assert masked is False
        events.append("target_fstat")
        return original_fstat(descriptor)

    def tracked_pipe2(flags: int):
        assert masked is False
        events.append("status_pipe")
        return original_pipe2(flags)

    def fake_pthread_sigmask(how: int, mask: object):
        nonlocal masked
        if how == run.signal.SIG_BLOCK:
            assert masked is False
            assert mask == {run.signal.SIGALRM}
            masked = True
            events.append("mask_block")
            return set()
        assert how == run.signal.SIG_SETMASK
        assert masked is True
        assert mask == set()
        masked = False
        events.append("mask_restore")
        return {run.signal.SIGALRM}

    class FakeLibc:
        @staticmethod
        def syscall(*_arguments: object) -> int:
            assert masked is True
            events.append("clone3")
            run.ctypes.set_errno(errno.EPERM)
            return -1

    launcher = object.__new__(run.LinuxClone3V180R12R4)
    launcher.libc = FakeLibc()
    launcher.fault_injector = None
    monkeypatch.setattr(
        run.LinuxClone3V180R12R4,
        "validate_internal_exec_contract",
        staticmethod(lambda **_arguments: None),
    )
    monkeypatch.setattr(run.os, "fstat", tracked_fstat)
    monkeypatch.setattr(run.os, "pipe2", tracked_pipe2)
    monkeypatch.setattr(run.signal, "pthread_sigmask", fake_pthread_sigmask)

    target_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    try:
        with pytest.raises(OSError) as captured:
            launcher.launch_exec(
                role="SUPERVISOR",
                target_cgroup_fd=target_fd,
                expected_cgroup_membership_line=(
                    "0::/app.slice/test.service/root/SUPERVISOR"
                ),
                argv=(),
                env={},
                inherited_fd_map={},
                pre_clone_revalidate=lambda: (
                    events.append("second_t3")
                    if masked
                    else pytest.fail("second T3 was not masked")
                ),
            )
        assert captured.value.errno == errno.EPERM
        assert masked is False
        assert events == [
            "target_fstat",
            "status_pipe",
            "mask_block",
            "second_t3",
            "clone3",
            "mask_restore",
        ]
        source = Path(run.__file__).read_text(encoding="utf-8")
        outer_start = source.index("def launch_supervisor")
        first_t3 = source.index('"T3_BEFORE_GETRANDOM"', outer_start)
        launch_call = source.index("self.launcher.launch_exec", first_t3)
        assert first_t3 < launch_call
        assert "pthread_sigmask" not in source[first_t3:launch_call]
    finally:
        os.close(target_fd)


def test_pidfd_written_before_timeout_is_killed_reaped_closed_and_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = run.V180R12R4RuntimeTimeout(
        "synthetic SIGALRM after clone3 wrote pidfd"
    )
    mask_events: list[int] = []
    signal_calls: list[tuple[object, ...]] = []
    wait_calls: list[tuple[object, ...]] = []
    pipe_fds: list[int] = []
    original_pipe2 = run.os.pipe2

    def fake_pthread_sigmask(how: int, mask: object):
        mask_events.append(how)
        if how == run.signal.SIG_BLOCK:
            assert mask == {run.signal.SIGALRM}
            return set()
        assert how == run.signal.SIG_SETMASK
        assert mask == set()
        return {run.signal.SIGALRM}

    owned_pidfd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    target_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)

    def tracked_pipe2(flags: int) -> tuple[int, int]:
        descriptors = original_pipe2(flags)
        pipe_fds.extend(descriptors)
        return descriptors

    class FakeLibc:
        @staticmethod
        def syscall(number: int, *arguments: object) -> int:
            if number == run.LinuxClone3V180R12R4.clone3_number:
                clone_args = arguments[0]._obj
                run.ctypes.cast(
                    clone_args.pidfd, run.ctypes.POINTER(run.ctypes.c_int)
                ).contents.value = owned_pidfd
                raise primary
            signal_calls.append((number, *arguments))
            return 0

    def fake_waitid(*arguments: object):
        wait_calls.append(arguments)
        return SimpleNamespace()

    launcher = object.__new__(run.LinuxClone3V180R12R4)
    launcher.libc = FakeLibc()
    launcher.fault_injector = None
    monkeypatch.setattr(
        run.LinuxClone3V180R12R4,
        "validate_internal_exec_contract",
        staticmethod(lambda **_arguments: None),
    )
    monkeypatch.setattr(run.signal, "pthread_sigmask", fake_pthread_sigmask)
    monkeypatch.setattr(run.os, "waitid", fake_waitid)
    monkeypatch.setattr(run.os, "pipe2", tracked_pipe2)
    try:
        with pytest.raises(run.V180R12R4RuntimeTimeout) as captured:
            launcher.launch_exec(
                role="SUPERVISOR",
                target_cgroup_fd=target_fd,
                expected_cgroup_membership_line=(
                    "0::/app.slice/test.service/root/SUPERVISOR"
                ),
                argv=(),
                env={},
                inherited_fd_map={},
                pre_clone_revalidate=lambda: None,
            )
        assert captured.value is primary
        assert (
            primary.launch_substage,
            primary.launch_errno,
            primary.launch_child_created,
            primary.launch_pidfd_acquired,
            primary.launch_exec_observed,
        ) == ("CLONE3", None, True, True, False)
        assert mask_events == [run.signal.SIG_BLOCK, run.signal.SIG_SETMASK]
        assert signal_calls == [
            (
                run.LinuxClone3V180R12R4.pidfd_send_signal_number,
                owned_pidfd,
                run.signal.SIGKILL,
                0,
                0,
            )
        ]
        assert wait_calls == [
            (run.os.P_PIDFD, owned_pidfd, run.os.WEXITED)
        ]
        with pytest.raises(OSError) as closed:
            os.fstat(owned_pidfd)
        assert closed.value.errno == errno.EBADF
        assert len(pipe_fds) == 2
        for descriptor in pipe_fds:
            with pytest.raises(OSError) as pipe_closed:
                os.fstat(descriptor)
            assert pipe_closed.value.errno == errno.EBADF
    finally:
        os.close(target_fd)
        try:
            os.close(owned_pidfd)
        except OSError:
            pass


def test_pending_alarm_during_parent_mask_restore_uses_captured_pid_and_pidfd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = run.V180R12R4RuntimeTimeout(
        "synthetic pending SIGALRM on parent mask restore"
    )
    owned_pidfd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    target_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    mask_events: list[int] = []
    signal_calls: list[tuple[object, ...]] = []
    wait_calls: list[tuple[object, ...]] = []

    def fake_pthread_sigmask(how: int, mask: object):
        mask_events.append(how)
        if how == run.signal.SIG_BLOCK:
            return set()
        assert how == run.signal.SIG_SETMASK
        if mask_events.count(run.signal.SIG_SETMASK) == 1:
            raise primary
        return set()

    class FakeLibc:
        @staticmethod
        def syscall(number: int, *arguments: object) -> int:
            if number == run.LinuxClone3V180R12R4.clone3_number:
                clone_args = arguments[0]._obj
                run.ctypes.cast(
                    clone_args.pidfd, run.ctypes.POINTER(run.ctypes.c_int)
                ).contents.value = owned_pidfd
                return 12345
            signal_calls.append((number, *arguments))
            return 0

    launcher = object.__new__(run.LinuxClone3V180R12R4)
    launcher.libc = FakeLibc()
    launcher.fault_injector = None
    monkeypatch.setattr(
        run.LinuxClone3V180R12R4,
        "validate_internal_exec_contract",
        staticmethod(lambda **_arguments: None),
    )
    monkeypatch.setattr(run.signal, "pthread_sigmask", fake_pthread_sigmask)
    monkeypatch.setattr(
        run.os,
        "waitid",
        lambda *arguments: wait_calls.append(arguments),
    )
    try:
        with pytest.raises(run.V180R12R4RuntimeTimeout) as captured:
            launcher.launch_exec(
                role="SUPERVISOR",
                target_cgroup_fd=target_fd,
                expected_cgroup_membership_line=(
                    "0::/app.slice/test.service/root/SUPERVISOR"
                ),
                argv=(),
                env={},
                inherited_fd_map={},
                pre_clone_revalidate=lambda: None,
            )
        assert captured.value is primary
        assert (
            primary.launch_substage,
            primary.launch_child_created,
            primary.launch_pidfd_acquired,
            primary.launch_exec_observed,
        ) == ("CLONE3", True, True, False)
        assert mask_events == [
            run.signal.SIG_BLOCK,
            run.signal.SIG_SETMASK,
            run.signal.SIG_SETMASK,
        ]
        assert signal_calls == [
            (
                run.LinuxClone3V180R12R4.pidfd_send_signal_number,
                owned_pidfd,
                run.signal.SIGKILL,
                0,
                0,
            )
        ]
        assert wait_calls == [
            (run.os.P_PIDFD, owned_pidfd, run.os.WEXITED)
        ]
        with pytest.raises(OSError) as closed:
            os.fstat(owned_pidfd)
        assert closed.value.errno == errno.EBADF
    finally:
        os.close(target_fd)
        try:
            os.close(owned_pidfd)
        except OSError:
            pass


def test_clone3_child_restores_inherited_mask_before_first_child_os_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SyntheticChildExit(BaseException):
        pass

    events: list[str] = []

    def fake_pthread_sigmask(how: int, mask: object):
        if how == run.signal.SIG_BLOCK:
            events.append("mask_block")
            return set()
        assert how == run.signal.SIG_SETMASK
        events.append("child_mask_restore")
        return set()

    class FakeLibc:
        @staticmethod
        def syscall(number: int, *_arguments: object) -> int:
            assert number == run.LinuxClone3V180R12R4.clone3_number
            events.append("clone3_child_return")
            return 0

    def fail_first_child_boundary(*_arguments: object) -> None:
        events.append("child_setrlimit")
        raise OSError(errno.EPERM, "stop synthetic child")

    def fake_write(_descriptor: int, raw: bytes) -> int:
        events.append("child_status_write")
        return len(raw)

    def fake_exit(code: int) -> None:
        assert code == 127
        events.append("child_exit")
        raise SyntheticChildExit()

    launcher = object.__new__(run.LinuxClone3V180R12R4)
    launcher.libc = FakeLibc()
    launcher.fault_injector = None
    monkeypatch.setattr(
        run.LinuxClone3V180R12R4,
        "validate_internal_exec_contract",
        staticmethod(lambda **_arguments: None),
    )
    monkeypatch.setattr(run.signal, "pthread_sigmask", fake_pthread_sigmask)
    monkeypatch.setattr(run.resource, "setrlimit", fail_first_child_boundary)
    monkeypatch.setattr(run.os, "write", fake_write)
    monkeypatch.setattr(run.os, "_exit", fake_exit)
    target_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    try:
        with pytest.raises(SyntheticChildExit):
            launcher.launch_exec(
                role="SUPERVISOR",
                target_cgroup_fd=target_fd,
                expected_cgroup_membership_line=(
                    "0::/app.slice/test.service/root/SUPERVISOR"
                ),
                argv=(),
                env={},
                inherited_fd_map={},
                pre_clone_revalidate=lambda: events.append("second_t3"),
            )
        assert events == [
            "mask_block",
            "second_t3",
            "clone3_child_return",
            "child_mask_restore",
            "child_setrlimit",
            "child_status_write",
            "child_exit",
        ]
    finally:
        os.close(target_fd)


def test_second_t3_exception_restores_mask_without_killing_absent_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = OSError(errno.EAGAIN, "synthetic no-child T3 failure")
    mask_events: list[int] = []
    syscalls: list[tuple[object, ...]] = []

    def fake_pthread_sigmask(how: int, mask: object):
        mask_events.append(how)
        return set()

    class FakeLibc:
        @staticmethod
        def syscall(*arguments: object) -> int:
            syscalls.append(arguments)
            return -1

    launcher = object.__new__(run.LinuxClone3V180R12R4)
    launcher.libc = FakeLibc()
    launcher.fault_injector = None
    monkeypatch.setattr(
        run.LinuxClone3V180R12R4,
        "validate_internal_exec_contract",
        staticmethod(lambda **_arguments: None),
    )
    monkeypatch.setattr(run.signal, "pthread_sigmask", fake_pthread_sigmask)
    monkeypatch.setattr(
        run.os,
        "kill",
        lambda *_arguments: pytest.fail("no-child path attempted kill"),
    )
    monkeypatch.setattr(
        run.os,
        "waitpid",
        lambda *_arguments: pytest.fail("no-child path attempted waitpid"),
    )
    monkeypatch.setattr(
        run.os,
        "waitid",
        lambda *_arguments: pytest.fail("no-child path attempted waitid"),
    )
    target_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    baseline_fds = set(os.listdir("/proc/self/fd"))
    try:
        with pytest.raises(OSError) as captured:
            launcher.launch_exec(
                role="SUPERVISOR",
                target_cgroup_fd=target_fd,
                expected_cgroup_membership_line=(
                    "0::/app.slice/test.service/root/SUPERVISOR"
                ),
                argv=(),
                env={},
                inherited_fd_map={},
                pre_clone_revalidate=lambda: (_ for _ in ()).throw(primary),
            )
        assert captured.value is primary
        assert (
            primary.launch_child_created,
            primary.launch_pidfd_acquired,
            primary.launch_exec_observed,
        ) == (False, False, False)
        assert mask_events == [run.signal.SIG_BLOCK, run.signal.SIG_SETMASK]
        assert syscalls == []
        assert set(os.listdir("/proc/self/fd")) == baseline_fds
    finally:
        os.close(target_fd)


def test_cgroup_close_preserves_primary_and_always_attempts_fd252_251_250(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = OSError(errno.EIO, "retained close primary")
    closed: list[int] = []
    removed: list[tuple[str, int]] = []

    def fake_close(descriptor: int) -> None:
        closed.append(descriptor)
        if descriptor == 300:
            raise primary
        if descriptor == 252:
            raise OSError(errno.EBUSY, "secondary close")

    def fake_rmdir(name: str, *, dir_fd: int) -> None:
        removed.append((name, dir_fd))

    monkeypatch.setattr(run.os, "close", fake_close)
    monkeypatch.setattr(run.os, "rmdir", fake_rmdir)
    tree = run.CgroupTreeV180R12R4(
        Path("/parent"),
        Path("/parent/root"),
        Path("/parent/root/SUPERVISOR"),
        Path("/parent/root/WORKER"),
        303,
        304,
        305,
        250,
        251,
        252,
        (("MEASUREMENT_ROOT", "cgroup.events", 300, 1, 1),),
        object(),  # type: ignore[arg-type]
    )
    with pytest.raises(OSError) as captured:
        run.LinuxCgroupV2V180R12R4().close(tree)
    assert captured.value is primary
    assert closed == [300, 304, 305, 303, 252, 251, 250]
    assert removed == [
        ("SUPERVISOR", 303),
        ("WORKER", 303),
        ("root", 250),
    ]
    assert primary.cleanup_errors == (
        "source_service_fd:OSError: (16, 'secondary close')",
    )

    status_read, status_write = os.pipe2(os.O_CLOEXEC)
    try:
        assert os.write(status_write, run.struct.pack("!I", errno.ENOEXEC)) == 4
    finally:
        os.close(status_write)
    try:
        with pytest.raises(OSError) as captured:
            run._observe_child_exec_status_v180r12r4(status_read)
        assert captured.value.errno == errno.ENOEXEC
    finally:
        os.close(status_read)


def test_partial_attempt_short_write_freezes_exact_artifact_and_never_creates_cgroup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, attempt_document, _manifest = _attempt_fixture()
    protocol_id, authorization_id, attempt_id = _ids()
    store = run.DurableStoreV180R12R4(tmp_path)
    original_write = store.write_once

    def short_attempt(relative_path, raw, *, mode=0o400):
        if relative_path == run.ATTEMPT_RELATIVE_PATH:
            original_write(relative_path, b"{", mode=mode)
            raise run.V180R12R4DurableWriteFailure(relative_path, True)
        return original_write(relative_path, raw, mode=mode)

    store.write_once = short_attempt

    class Adapter:
        def create_cgroup(self, attempt):  # pragma: no cover - forbidden
            raise AssertionError(attempt)

    try:
        with pytest.raises(run.V180R12R4DurableWriteFailure):
            run.run_one_shot_outer_v180r12r4(
                store=store,
                adapter=Adapter(),
                attempt_document=attempt_document,
                attempt_authority=authority,
                protocol_id=protocol_id,
                authorization_id=authorization_id,
                attempt_id=attempt_id,
                campaign_deadline_ns=(
                    run.time.monotonic_ns() + 60 * run.NANOSECONDS_PER_SECOND
                ),
                forbidden_progress_paths=(),
            )
        failure = json.loads(
            store.read_exact(run.FAILURE_RELATIVE_PATH, 4 * 1024 * 1024)
        )
        rows = {row["relative_path"]: row for row in failure["partial_artifact_observations"]}
        attempt = rows[run.ATTEMPT_RELATIVE_PATH]
        assert attempt["state"] == "PRESENT"
        assert attempt["byte_count"] == 1
        assert attempt["sha256"] == hashlib.sha256(b"{").hexdigest()
        assert failure["same_identity_rerun_forbidden"] is True
        assert failure["cgroup_failure_observation"] is None
    finally:
        store.close()


def test_attempt_write_failure_with_false_path_flag_still_consumes_identity(
    tmp_path: Path,
) -> None:
    """O_EXCL-to-Python bookkeeping interruption never becomes unowned."""

    authority, attempt_document, _manifest = _attempt_fixture()
    store = run.DurableStoreV180R12R4(tmp_path)
    original_write = store.write_once

    def interrupted_before_path_flag(relative_path, raw, *, mode=0o400):
        if relative_path == run.ATTEMPT_RELATIVE_PATH:
            raise run.V180R12R4DurableWriteFailure(relative_path, False)
        return original_write(relative_path, raw, mode=mode)

    store.write_once = interrupted_before_path_flag

    class ForbiddenAdapter:
        def create_cgroup(self, attempt):  # pragma: no cover - forbidden
            raise AssertionError(attempt)

    try:
        with pytest.raises(run.V180R12R4DurableWriteFailure):
            run.run_one_shot_outer_v180r12r4(
                store=store,
                adapter=ForbiddenAdapter(),
                attempt_document=attempt_document,
                attempt_authority=authority,
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
                campaign_deadline_ns=(
                    run.time.monotonic_ns() + 60 * run.NANOSECONDS_PER_SECOND
                ),
                forbidden_progress_paths=(),
            )
        failure = json.loads(
            store.read_exact(run.FAILURE_RELATIVE_PATH, 4 * 1024 * 1024)
        )
        attempt_row = next(
            row
            for row in failure["partial_artifact_observations"]
            if row["relative_path"] == run.ATTEMPT_RELATIVE_PATH
        )
        assert attempt_row["state"] == "ABSENT"
        assert failure["same_identity_rerun_forbidden"] is True
    finally:
        store.close()


def test_async_failure_after_owned_token_keeps_reserve_and_freezes_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, attempt_document, _manifest = _attempt_fixture()
    store = run.DurableStoreV180R12R4(tmp_path)

    def interrupt_return(_attempt, _reserve):
        raise run.V180R12R4RuntimeTimeout("synthetic post-ownership alarm")

    monkeypatch.setattr(run, "AttemptClaimV180R12R4", interrupt_return)
    real_neutralize = run.CampaignDeadlineWatchdogV180R12R4.neutralize
    neutralize_calls = 0

    def alarm_inside_first_neutralize(self):
        nonlocal neutralize_calls
        neutralize_calls += 1
        if neutralize_calls == 1:
            raise run.V180R12R4RuntimeTimeout(
                "synthetic alarm inside exception cleanup"
            )
        return real_neutralize(self)

    monkeypatch.setattr(
        run.CampaignDeadlineWatchdogV180R12R4,
        "neutralize",
        alarm_inside_first_neutralize,
    )

    class ForbiddenAdapter:
        def create_cgroup(self, attempt):  # pragma: no cover - forbidden
            raise AssertionError(attempt)

    try:
        with pytest.raises(run.V180R12R4RuntimeTimeout, match="post-ownership"):
            run.run_one_shot_outer_v180r12r4(
                store=store,
                adapter=ForbiddenAdapter(),
                attempt_document=attempt_document,
                attempt_authority=authority,
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
                campaign_deadline_ns=(
                    run.time.monotonic_ns() + 60 * run.NANOSECONDS_PER_SECOND
                ),
                forbidden_progress_paths=(),
            )
        assert store.exists(run.ATTEMPT_RELATIVE_PATH)
        failure = json.loads(
            store.read_exact(run.FAILURE_RELATIVE_PATH, 4 * 1024 * 1024)
        )
        assert failure["failure_code"] == "CAP_VIOLATION"
        assert failure["same_identity_rerun_forbidden"] is True
        assert neutralize_calls == 2
        assert "synthetic alarm inside exception cleanup" in failure["message"]
    finally:
        store.close()


def test_alarm_at_neutralize_call_entry_preserves_owned_primary_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The caller catches SIGALRM before the helper's own try becomes active."""

    authority, attempt_document, _manifest = _attempt_fixture()
    store = run.DurableStoreV180R12R4(tmp_path)
    original = run.CampaignDeadlineWatchdogV180R12R4.neutralize_preserving_primary
    calls = 0

    def alarm_before_helper_body(self):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise run.V180R12R4RuntimeTimeout(
                "synthetic alarm at neutralize call entry"
            )
        return original(self)

    monkeypatch.setattr(
        run.CampaignDeadlineWatchdogV180R12R4,
        "neutralize_preserving_primary",
        alarm_before_helper_body,
    )

    class FailingAdapter:
        def create_cgroup(self, _attempt):
            raise RuntimeError("synthetic owned primary")

    try:
        with pytest.raises(RuntimeError, match="synthetic owned primary"):
            run.run_one_shot_outer_v180r12r4(
                store=store,
                adapter=FailingAdapter(),
                attempt_document=attempt_document,
                attempt_authority=authority,
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
                campaign_deadline_ns=(
                    run.time.monotonic_ns() + 60 * run.NANOSECONDS_PER_SECOND
                ),
                forbidden_progress_paths=(),
            )
        failure = json.loads(
            store.read_exact(run.FAILURE_RELATIVE_PATH, 4 * 1024 * 1024)
        )
        assert calls == 2
        assert failure["failure_code"] == "SUPERVISOR_BIRTH_FAILURE"
        assert "RuntimeError: synthetic owned primary" in failure["message"]
        assert "synthetic alarm at neutralize call entry" in failure["message"]
    finally:
        store.close()


def test_watchdog_handler_never_replaces_an_active_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watchdog = run.CampaignDeadlineWatchdogV180R12R4(
        10**15, monotonic_ns=lambda: 0
    )
    watchdog._previous_handler = run.signal.SIG_DFL
    watchdog.armed = True
    monkeypatch.setattr(run.signal, "setitimer", lambda *_args: (0.0, 0.0))
    monkeypatch.setattr(run.signal, "signal", lambda *_args: None)

    primary = RuntimeError("active primary")
    observed = None
    try:
        raise primary
    except RuntimeError as caught:
        # This models delivery in the exception prologue before any nested
        # Python try block can become active.
        watchdog._expired(run.signal.SIGALRM, None)
        observed = caught
        watchdog.neutralize()
    assert observed is primary
    assert watchdog.deadline_expired_during_exception is True
    assert watchdog.first_cleanup_error() is watchdog._exception_path_timeout


def test_watchdog_handler_interrupts_normally_without_an_active_primary() -> None:
    watchdog = run.CampaignDeadlineWatchdogV180R12R4(
        10**15, monotonic_ns=lambda: 0
    )
    with pytest.raises(run.V180R12R4RuntimeTimeout, match="shared monotonic"):
        watchdog._expired(run.signal.SIGALRM, None)
    assert watchdog.deadline_expired_during_exception is False


def test_shared_absolute_deadline_contract_never_derives_a_relative_reset() -> None:
    origin_ns = 10 * run.NANOSECONDS_PER_SECOND
    hard_ns = origin_ns + run.HARD_DEADLINE_DURATION_NS
    campaign_ns = hard_ns - run.CAMPAIGN_CLEANUP_GRACE_NS
    context = {
        "monotonic_origin_ns": origin_ns,
        "hard_deadline_ns": hard_ns,
        "campaign_deadline_ns": campaign_ns,
    }
    assert run._validate_shared_deadlines_v180r12r4(
        context, monotonic_ns=lambda: origin_ns + 1
    ) == (origin_ns, hard_ns, campaign_ns)
    drifted = dict(context, campaign_deadline_ns=campaign_ns + 1)
    with pytest.raises(run.V180R12R4RuntimeError, match="deadline contract"):
        run._validate_shared_deadlines_v180r12r4(
            drifted, monotonic_ns=lambda: origin_ns + 1
        )
    with pytest.raises(run.V180R12R4RuntimeTimeout, match="before ATTEMPT"):
        run._validate_shared_deadlines_v180r12r4(
            context, monotonic_ns=lambda: campaign_ns
        )


def test_watchdog_cancel_failure_keeps_sigalrm_ignored_during_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watchdog = run.CampaignDeadlineWatchdogV180R12R4(
        10**15, monotonic_ns=lambda: 0
    )
    previous = object()
    watchdog._previous_handler = previous
    watchdog.armed = True
    installed: list[object] = []

    def cancel_fails(which, duration):
        assert which == run.signal.ITIMER_REAL and duration == 0.0
        raise OSError("synthetic timer cancellation failure")

    monkeypatch.setattr(run.signal, "setitimer", cancel_fails)
    monkeypatch.setattr(
        run.signal,
        "signal",
        lambda signum, handler: installed.append(handler),
    )
    watchdog.neutralize()
    watchdog.restore()
    assert installed == [run.signal.SIG_IGN]
    assert watchdog.cancel_succeeded is False
    assert watchdog.ignore_succeeded is True
    assert watchdog.restore_succeeded is False
    assert isinstance(watchdog.first_cleanup_error(), OSError)


def test_watchdog_does_not_cancel_an_inherited_timer_it_never_owned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watchdog = run.CampaignDeadlineWatchdogV180R12R4(
        10**15, monotonic_ns=lambda: 0
    )
    mutations: list[tuple[object, ...]] = []
    monkeypatch.setattr(run.signal, "getitimer", lambda which: (1.0, 0.0))
    monkeypatch.setattr(
        run.signal,
        "setitimer",
        lambda *args: mutations.append(tuple(args)),
    )
    monkeypatch.setattr(
        run.signal,
        "signal",
        lambda *args: mutations.append(tuple(args)),
    )
    with pytest.raises(run.V180R12R4RuntimeError, match="inherited"):
        watchdog.arm()
    watchdog.neutralize()
    watchdog.restore()
    assert mutations == []


@dataclass(frozen=True)
class _Plan:
    event_kind: str
    actor_role: str
    phase: str
    operation_id: str


class _Event:
    def __init__(self, sequence: int) -> None:
        self.sequence = sequence

    def to_document(self):
        return {"sequence": self.sequence}


def _fake_plan() -> tuple[_Plan, ...]:
    rows = [
        _Plan("ATTEMPT_OPEN", "OBSERVER", "ATTEMPT", "a" * 64),
        _Plan("PROCESS_BIRTH_INTENT", "OBSERVER", "STAGE", "b" * 64),
        _Plan("PROCESS_BIRTH_OUTCOME", "OBSERVER", "STAGE", "b" * 64),
    ]
    rows.extend(
        _Plan("INPUT_READ_INTENT", "SUPERVISOR", "STAGE", f"{index:064x}")
        for index in range(3, 621)
    )
    rows.extend(
        (
            _Plan("WINDOW_CLOSED", "SUPERVISOR", "WINDOW_CLOSE", "c" * 64),
            _Plan("PROCESS_REAP", "OBSERVER", "OS_OBSERVE", "b" * 64),
            _Plan("CGROUP_OBSERVED", "OBSERVER", "OS_OBSERVE", "d" * 64),
            _Plan("LEDGER_CLOSED", "OBSERVER", "LEDGER_CLOSE", "e" * 64),
        )
    )
    assert len(rows) == 625
    return tuple(rows)


def test_outer_lifecycle_event0_before_cgroup_child_stops_at_window_and_observer_owns_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    order: list[str] = []
    plan = _fake_plan()

    class Campaign:
        def __init__(self, **kwargs):
            del kwargs
            self.success_event_plan = plan
            self.event_count = 0

        def register_evidence_document(self, document):
            del document

        def append_event(self, **kwargs):
            expected = self.success_event_plan[self.event_count]
            assert (kwargs["event_kind"], kwargs["actor_role"], kwargs["phase"], kwargs["operation_id"]) == (
                expected.event_kind, expected.actor_role, expected.phase, expected.operation_id
            )
            event = _Event(self.event_count)
            self.event_count += 1
            return event

        def assert_success_schedule_complete(self):
            assert self.event_count == 625

    class Journal:
        def __init__(self, store, **kwargs):
            del store, kwargs
            order.append("journal")
            self.schedule = plan
            self.next_sequence = 0
            self.previous_event_id = None

        def append(self, document):
            assert document["sequence"] == self.next_sequence
            if self.next_sequence == 0:
                order.append("event0_durable")
            ack = {"sequence": self.next_sequence}
            self.previous_event_id = f"{self.next_sequence:064x}"
            self.next_sequence += 1
            return ack

        def assert_complete(self):
            assert self.next_sequence == 625

    class Adapter:
        def create_cgroup(self, attempt):
            assert attempt == _ids()[2]
            order.append("create_cgroup")
            return object(), object()

        def launch_supervisor(self, cgroup, operation_id, deadline):
            del cgroup, deadline
            assert operation_id == "b" * 64
            order.append("launch")
            return object(), object()

        def acknowledge_event(self, child, ack):
            del child
            order.append(f"ack:{ack['sequence']}")

        def receive_event_proposals(self, child, deadline):
            del child, deadline
            for sequence, row in enumerate(plan[3:622], start=3):
                evidence_document = None
                evidence_id = None
                if row.event_kind == "WINDOW_CLOSED":
                    evidence_id = "f" * 64
                    evidence_document = {
                        "schema": "acfqp.synthetic_window_closure.v180r12r4",
                        "synthetic_window_closure_id": evidence_id,
                    }
                payload = supervisor.campaign_event_payload_v180r12r4(
                    event_kind=row.event_kind,
                    evidence_id=evidence_id,
                    measured_value=None,
                    auxiliary_values=(),
                )
                yield run.ObserverEventProposalV180R12R4(
                    sequence,
                    row.phase,
                    row.actor_role,
                    row.event_kind,
                    row.operation_id,
                    payload,
                    evidence_document,
                )

        def reap_supervisor(self, child, operation_id, deadline_ns):
            del child, operation_id
            assert deadline_ns == 10**15
            order.append("observer_reap")
            return object()

        def close_supervisor_pidfd_after_reap_ack(self, child, receipt):
            del child, receipt
            order.append("pidfd_close")

        def observe_cgroup(self, cgroup, reap, operation_id):
            del cgroup, reap, operation_id
            order.append("observer_cgroup")
            return SimpleNamespace(memory_peak_bytes=123)

        def close_cgroup(self, cgroup):
            del cgroup
            order.append("close")

    monkeypatch.setattr(run.runtime, "CampaignMeasurementSupervisorV180R12R4", Campaign)
    monkeypatch.setattr(run, "CanonicalEventJournalV180R12R4", Journal)
    monkeypatch.setattr(
        run,
        "_validate_registered_evidence_document_v180r12r4",
        lambda document, *, expected_schema: (
            dict(document),
            document["synthetic_window_closure_id"],
        ),
    )
    monkeypatch.setattr(
        run,
        "register_campaign_execution_closure_v180r12r4",
        lambda **kwargs: order.append("register_execution_closure"),
    )
    finalizer_input = object()
    monkeypatch.setattr(
        run,
        "build_finalize_success_inputs_v180r12r4",
        lambda *, campaign, journal: (
            order.append("build_finalizer_inputs"), finalizer_input
        )[1],
    )
    monkeypatch.setattr(
        run,
        "finalize_and_materialize_success_v180r12r4",
        lambda *, store, inputs, campaign_deadline_ns, monotonic_ns,
        publication_token: (
            order.append("finalize_and_materialize"),
            inputs is finalizer_input,
            campaign_deadline_ns == 10**15,
            callable(monotonic_ns),
        ),
    )
    store = run.DurableStoreV180R12R4(tmp_path)
    original_write = store.write_once

    def logged_write(relative_path, raw, *, mode=0o400):
        if relative_path == run.ATTEMPT_RELATIVE_PATH:
            order.append("attempt")
        return original_write(relative_path, raw, mode=mode)

    store.write_once = logged_write
    try:
        authority, attempt_document, _manifest = _attempt_fixture()
        result = run.run_one_shot_outer_v180r12r4(
            store=store,
            adapter=Adapter(),
            attempt_document=attempt_document,
            attempt_authority=authority,
            protocol_id=authority.protocol_id,
            authorization_id=authority.authorization_id,
            attempt_id=authority.attempt_id,
            campaign_deadline_ns=10**15,
            forbidden_progress_paths=(),
            monotonic_ns=iter(range(10_000)).__next__,
        )
        assert result.next_sequence == 625
        assert order.index("attempt") < order.index("event0_durable") < order.index("create_cgroup")
        assert order.index("ack:621") < order.index("observer_reap") < order.index("observer_cgroup")
        assert order.index("ack:621") < order.index("register_execution_closure") < order.index("observer_reap")
        assert order.index("observer_reap") < order.index("pidfd_close") < order.index("observer_cgroup")
        assert order.index("close") < order.index("build_finalizer_inputs") < order.index("finalize_and_materialize")
        assert "ack:622" not in order and "ack:623" not in order and "ack:624" not in order
    finally:
        store.close()

    def publish_terminal_then_return(
        *,
        store,
        inputs,
        campaign_deadline_ns,
        monotonic_ns,
        publication_token,
    ):
        del inputs, campaign_deadline_ns, monotonic_ns
        publication_token.started = True
        store.write_once(run.TERMINAL_RELATIVE_PATH, b"{}")

    monkeypatch.setattr(
        run,
        "finalize_and_materialize_success_v180r12r4",
        publish_terminal_then_return,
    )
    monkeypatch.setattr(
        run.CampaignDeadlineWatchdogV180R12R4,
        "teardown",
        lambda self: (_ for _ in ()).throw(
            run.V180R12R4RuntimeTimeout("synthetic post-terminal teardown")
        ),
    )
    def restore_with_secondary(self):
        self.restore_attempted = True
        self.restore_succeeded = False
        self._cleanup_error_0 = OSError(
            "synthetic post-terminal watchdog restore failure"
        )

    monkeypatch.setattr(
        run.CampaignDeadlineWatchdogV180R12R4,
        "restore",
        restore_with_secondary,
    )
    with tempfile.TemporaryDirectory(dir="/tmp") as post_terminal_root:
        post_terminal_store = run.DurableStoreV180R12R4(
            Path(post_terminal_root)
        )
        try:
            with pytest.raises(
                run.V180R12R4RuntimeTimeout, match="post-terminal teardown"
            ) as captured:
                run.run_one_shot_outer_v180r12r4(
                    store=post_terminal_store,
                    adapter=Adapter(),
                    attempt_document=attempt_document,
                    attempt_authority=authority,
                    protocol_id=authority.protocol_id,
                    authorization_id=authority.authorization_id,
                    attempt_id=authority.attempt_id,
                    campaign_deadline_ns=10**15,
                    forbidden_progress_paths=(),
                    monotonic_ns=iter(range(10_000)).__next__,
                )
            assert post_terminal_store.exists(run.TERMINAL_RELATIVE_PATH)
            assert not post_terminal_store.exists(run.FAILURE_RELATIVE_PATH)
            assert captured.value.cleanup_errors == (
                "post_terminal_campaign_watchdog:OSError: synthetic "
                "post-terminal watchdog restore failure",
            )
            assert isinstance(captured.value.__cause__, run.V180R12R4RuntimeError)
            assert "watchdog cleanup failed" in str(captured.value.__cause__)
        finally:
            post_terminal_store.close()


def test_authenticated_seqpacket_rejects_mac_substitution() -> None:
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        protocol_id, authorization_id, attempt_id = _ids()
        channel_id = ledger.build_campaign_success_event_schedule_v180r12r4(
            attempt_id
        )[1].operation_id
        common = {
            "channel_id": channel_id,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "authorization_evidence_id": "3" * 64,
            "attempt_id": attempt_id,
            "parent_actor_role": "OBSERVER",
            "child_actor_role": "SUPERVISOR",
        }
        sender = run.AuthenticatedFrameChannelV180R12R4(
            left, b"k" * 32, local_actor_role="SUPERVISOR", **common
        )
        receiver = run.AuthenticatedFrameChannelV180R12R4(
            right, b"k" * 32, local_actor_role="OBSERVER", **common
        )

        def proposal(sequence: int, measured_value: int):
            return {
                "schema": run.EVENT_PROPOSAL_BODY_SCHEMA,
                "protocol_id": protocol_id,
                "authorization_id": authorization_id,
                "authorization_evidence_id": "3" * 64,
                "attempt_id": attempt_id,
                "campaign_event_sequence": sequence,
                "phase": "STAGE",
                "actor_role": "SUPERVISOR",
                "event_kind": "INPUT_READ_OUTCOME",
                "operation_id": "f" * 64,
                "payload": {
                    "evidence_id": None,
                    "outcome_code": "SUCCESS",
                    "measured_value": measured_value,
                    "auxiliary_values": [],
                },
                "evidence_documents": [],
            }

        sender.send("EVENT_PROPOSAL", 0, proposal(3, 1))
        assert receiver.receive() == ("EVENT_PROPOSAL", 0, proposal(3, 1))
        sender.send("EVENT_PROPOSAL", 1, proposal(4, 2))
        raw = right.recv(run.FRAME_BYTE_CAP)
        document = json.loads(raw)
        document["body"]["payload"]["measured_value"] = 3
        left.send(run._canonical(document))
        with pytest.raises(run.V180R12R4RuntimeError, match="MAC"):
            receiver.receive()
        with pytest.raises(run.V180R12R4RuntimeError, match="sequence"):
            sender.send("EVENT_PROPOSAL", 3, proposal(5, 4))
    finally:
        left.close()
        right.close()


def test_configured_seqpacket_carries_exact_large_snapshot_signed_frame() -> None:
    authority, _attempt, _manifest = _attempt_fixture()
    fact = worker.frozen_campaign_input_facts_v180r12r4()[0]
    snapshot_bytes = (ROOT / fact.relative_path).read_bytes()
    snapshot = worker.StableInputSnapshotReceiptV180R12R4(
        fact, snapshot_bytes
    )
    transport = {
        "schema": run.SNAPSHOT_BYTES_TRANSPORT_SCHEMA,
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "role": fact.role.value,
        "byte_count": len(snapshot_bytes),
        "sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "canonical_bytes_hex": snapshot_bytes.hex(),
    }
    planned = ledger.build_campaign_success_event_schedule_v180r12r4(
        authority.attempt_id
    )[4]
    body = {
        "schema": run.EVENT_PROPOSAL_BODY_SCHEMA,
        "protocol_id": authority.protocol_id,
        "authorization_id": authority.authorization_id,
        "authorization_evidence_id": authority.authorization_evidence_id,
        "attempt_id": authority.attempt_id,
        "campaign_event_sequence": 4,
        "phase": planned.phase,
        "actor_role": planned.actor_role,
        "event_kind": planned.event_kind,
        "operation_id": planned.operation_id,
        "payload": {
            "evidence_id": snapshot.snapshot_receipt_id,
            "outcome_code": "SUCCESS",
            "measured_value": len(snapshot_bytes),
            "auxiliary_values": [],
        },
        "evidence_documents": [snapshot.to_document(), transport],
    }
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        observations = run.configure_seqpacket_pair_v180r12r4(left, right)
        assert run.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES == run.FRAME_BYTE_CAP
        assert run.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES == 2 * run.FRAME_BYTE_CAP
        assert min(value for row in observations for value in row) >= (
            run.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        )
        common = {
            "channel_id": ledger.build_campaign_success_event_schedule_v180r12r4(
                authority.attempt_id
            )[1].operation_id,
            "protocol_id": authority.protocol_id,
            "authorization_id": authority.authorization_id,
            "authorization_evidence_id": authority.authorization_evidence_id,
            "attempt_id": authority.attempt_id,
            "parent_actor_role": "OBSERVER",
            "child_actor_role": "SUPERVISOR",
        }
        sender = run.AuthenticatedFrameChannelV180R12R4(
            left, b"s" * 32, local_actor_role="SUPERVISOR", **common
        )
        receiver = run.AuthenticatedFrameChannelV180R12R4(
            right, b"s" * 32, local_actor_role="OBSERVER", **common
        )
        unsigned = {
            "schema": "acfqp.v180r12r4_runtime_ipc_frame.v1",
            "channel_id": sender.channel_id,
            "direction": sender.send_direction,
            "sender_actor_role": sender.local_actor_role,
            "recipient_actor_role": sender.remote_actor_role,
            "frame_type": "EVENT_PROPOSAL",
            "sequence": 0,
            "body": body,
        }
        signed_size = len(
            run._canonical(
                {
                    **unsigned,
                    "mac": hashlib.blake2s(
                        run._canonical(unsigned),
                        key=sender.send_key,
                        digest_size=32,
                    ).hexdigest(),
                }
            )
        )
        assert 400_000 < signed_size <= run.FRAME_BYTE_CAP
        sender.send("EVENT_PROPOSAL", 0, body)
        assert receiver.receive() == ("EVENT_PROPOSAL", 0, body)
    finally:
        left.close()
        right.close()


def test_journal_accepts_exact_four_field_schedule_signature(tmp_path: Path) -> None:
    authority, attempt, _manifest = _attempt_fixture()
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        store = run.DurableStoreV180R12R4(Path(local_text))
        try:
            journal = run.CanonicalEventJournalV180R12R4(
                store,
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
            )
            state = ledger.open_campaign_ledger_v180r12r4(
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
                max_event_count=run.protocol.MAX_EVENT_COUNT,
                max_event_byte_count=run.protocol.MAX_EVENT_BYTE_COUNT,
                max_ledger_byte_count=run.protocol.MAX_LEDGER_BYTE_COUNT,
            )
            planned = journal.schedule[0]
            _state, event = ledger.append_campaign_event_v180r12r4(
                state,
                phase=planned.phase,
                actor_role=planned.actor_role,
                operation_id=planned.operation_id,
                event_kind=planned.event_kind,
                monotonic_ns=1,
                payload={
                    "evidence_id": attempt["campaign_attempt_record_id"],
                    "outcome_code": "OPEN",
                    "measured_value": None,
                    "auxiliary_values": [],
                },
            )
            ack = journal.append(event.to_document())
            assert ack["sequence"] == 0
            assert journal.next_sequence == 1
        finally:
            store.close()


def test_journal_reconciles_durable_event_when_alarm_hits_before_state_advance(
    tmp_path: Path,
) -> None:
    del tmp_path
    authority, attempt, _manifest = _attempt_fixture()
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        store = run.DurableStoreV180R12R4(Path(local_text))
        try:
            journal = run.CanonicalEventJournalV180R12R4(
                store,
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
            )
            state = ledger.open_campaign_ledger_v180r12r4(
            protocol_id=authority.protocol_id,
            authorization_id=authority.authorization_id,
            attempt_id=authority.attempt_id,
            max_event_count=run.protocol.MAX_EVENT_COUNT,
            max_event_byte_count=run.protocol.MAX_EVENT_BYTE_COUNT,
            max_ledger_byte_count=run.protocol.MAX_LEDGER_BYTE_COUNT,
        )
            planned = journal.schedule[0]
            _state, event = ledger.append_campaign_event_v180r12r4(
            state,
            phase=planned.phase,
            actor_role=planned.actor_role,
            operation_id=planned.operation_id,
            event_kind=planned.event_kind,
            monotonic_ns=1,
            payload={
                "evidence_id": attempt["campaign_attempt_record_id"],
                "outcome_code": "OPEN",
                "measured_value": None,
                "auxiliary_values": [],
            },
        )
            raw = run._canonical(event.to_document())
            original_write = store.write_once

            def durable_then_alarm(relative_path, payload, *, mode=0o400):
                original_write(relative_path, payload, mode=mode)
                if relative_path.startswith(run.EVENTS_RELATIVE_PATH + "/"):
                    raise run.V180R12R4RuntimeTimeout("synthetic post-fsync alarm")

            store.write_once = durable_then_alarm
            with pytest.raises(run.V180R12R4RuntimeTimeout, match="post-fsync"):
                journal.append(event.to_document())
            assert journal.next_sequence == 1
            assert journal.previous_event_id == event.event_id
            assert journal.total_event_bytes == len(raw)
            assert store.read_exact(
                f"{run.EVENTS_RELATIVE_PATH}/000000.json", run.MAX_EVENT_BYTES
            ) == raw
        finally:
            store.close()


def test_authenticated_channel_rejects_ancillary_and_parent_transition_replay(
    tmp_path: Path,
) -> None:
    del tmp_path
    protocol_id, authorization_id, attempt_id = _ids()
    channel_id = ledger.build_campaign_success_event_schedule_v180r12r4(
        attempt_id
    )[1].operation_id
    common = {
        "channel_id": channel_id,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "authorization_evidence_id": "3" * 64,
        "attempt_id": attempt_id,
        "parent_actor_role": "OBSERVER",
        "child_actor_role": "SUPERVISOR",
    }
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        child = run.AuthenticatedFrameChannelV180R12R4(
            left, b"q" * 32, local_actor_role="SUPERVISOR", **common
        )
        parent = run.AuthenticatedFrameChannelV180R12R4(
            right, b"q" * 32, local_actor_role="OBSERVER", **common
        )
        body = {
            "schema": run.EVENT_PROPOSAL_BODY_SCHEMA,
            "protocol_id": protocol_id,
            "authorization_id": authorization_id,
            "authorization_evidence_id": "3" * 64,
            "attempt_id": attempt_id,
            "campaign_event_sequence": 3,
            "phase": "STAGE",
            "actor_role": "SUPERVISOR",
            "event_kind": "INPUT_READ_INTENT",
            "operation_id": "d" * 64,
            "payload": {
                "evidence_id": None,
                "outcome_code": "INTENT",
                "measured_value": None,
                "auxiliary_values": [],
            },
            "evidence_documents": [],
        }
        child.send("EVENT_PROPOSAL", 0, body)
        raw = right.recv(run.FRAME_BYTE_CAP)
        before = len(os.listdir("/proc/self/fd"))
        descriptor = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        try:
            left.sendmsg(
                [raw],
                [
                    (
                        socket.SOL_SOCKET,
                        socket.SCM_RIGHTS,
                        array.array("i", [descriptor]).tobytes(),
                    )
                ],
            )
            with pytest.raises(run.V180R12R4CapViolation, match="ancillary"):
                parent.receive()
        finally:
            os.close(descriptor)
        assert len(os.listdir("/proc/self/fd")) == before
    finally:
        left.close()
        right.close()

    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        parent = run.AuthenticatedFrameChannelV180R12R4(
            left, b"r" * 32, local_actor_role="OBSERVER", **common
        )
        child = run.AuthenticatedFrameChannelV180R12R4(
            right, b"r" * 32, local_actor_role="SUPERVISOR", **common
        )
        start = {key: "e" * 64 for key in run.OBSERVER_SUPERVISOR_START_FIELDS}
        start.update(
            {
                "schema": run.OBSERVER_SUPERVISOR_START_SCHEMA,
                "protocol_id": protocol_id,
                "authorization_id": authorization_id,
                "authorization_evidence_id": "3" * 64,
                "attempt_id": attempt_id,
                "cgroup_topology_document": {},
                "supervisor_birth_document": {},
                "supervisor_birth_event_sequence": 2,
                "next_campaign_event_sequence": 3,
                "one_shot_start": True,
            }
        )
        parent.send("SUPERVISOR_START", 0, start)
        assert child.receive()[0] == "SUPERVISOR_START"
        with pytest.raises(run.V180R12R4RuntimeError, match="transition"):
            parent.send("SUPERVISOR_START", 1, start)
    finally:
        left.close()
        right.close()


def test_signed_proposal_rejects_resigned_payload_semantic_drift() -> None:
    protocol_id, authorization_id, attempt_id = _ids()
    body = {
        "schema": run.EVENT_PROPOSAL_BODY_SCHEMA,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "authorization_evidence_id": "3" * 64,
        "attempt_id": attempt_id,
        "campaign_event_sequence": 3,
        "phase": "STAGE",
        "actor_role": "SUPERVISOR",
        "event_kind": "INPUT_READ_INTENT",
        "operation_id": "d" * 64,
        "payload": {
            "evidence_id": None,
            "outcome_code": "INTENT",
            "measured_value": None,
            "auxiliary_values": [],
        },
        "evidence_documents": [],
    }
    proposal = run.ObserverEventProposalV180R12R4.from_signed_body_v180r12r4(
        body,
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        authorization_evidence_id="3" * 64,
        attempt_id=attempt_id,
    )
    assert (proposal.campaign_event_sequence, proposal.phase, proposal.actor_role) == (
        3,
        "STAGE",
        "SUPERVISOR",
    )
    drifted = json.loads(json.dumps(body))
    drifted["payload"]["outcome_code"] = "PASS"
    with pytest.raises(run.V180R12R4RuntimeError, match="payload"):
        run.ObserverEventProposalV180R12R4.from_signed_body_v180r12r4(
            drifted,
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            authorization_evidence_id="3" * 64,
            attempt_id=attempt_id,
        )


def test_durable_campaign_directories_ignore_hostile_umask(tmp_path: Path) -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as local_text:
        local = Path(local_text)
        store = run.DurableStoreV180R12R4(local)
        previous = os.umask(0o777)
        try:
            store.mkdir_once(run.OUTPUT_ROOT_RELATIVE_PATH)
            store.mkdir_once(run.EVENTS_RELATIVE_PATH)
        finally:
            os.umask(previous)
        try:
            assert stat.S_IMODE(
                os.stat(local / run.OUTPUT_ROOT_RELATIVE_PATH).st_mode
            ) == 0o700
            assert stat.S_IMODE(
                os.stat(local / run.EVENTS_RELATIVE_PATH).st_mode
            ) == 0o700
        finally:
            store.close()


def test_cgroup_membership_uses_delegated_path_not_observer_membership_and_caps_readback_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run.LinuxCgroupV2V180R12R4._membership_for_filesystem_path(
        "/sys/fs/cgroup", "/sys/fs/cgroup/user.slice/delegated"
    ) == "/user.slice/delegated"
    with pytest.raises(run.V180R12R4RuntimeError):
        run.LinuxCgroupV2V180R12R4._membership_for_filesystem_path(
            "/sys/fs/cgroup/other", "/sys/fs/cgroup/user.slice/delegated"
        )

    values = {
        (10, "memory.max"): f"{run.MEMORY_MAX_BYTES}\n",
        (10, "pids.max"): "2\n",
        (10, "cgroup.subtree_control"): "memory pids\n",
        (11, "pids.max"): "1\n",
        (12, "pids.max"): "9\n",
    }
    monkeypatch.setattr(
        run.LinuxCgroupV2V180R12R4,
        "_read_at",
        classmethod(lambda cls, fd, name, byte_cap=0: values[(fd, name)]),
    )
    with pytest.raises(run.V180R12R4RuntimeError, match="drifted"):
        run.LinuxCgroupV2V180R12R4._validate_programmed_limits(10, 11, 12)


def test_internal_exec_contract_rejects_fd_or_dynamic_environment_drift() -> None:
    argv = (
        *run.INTERNAL_BOOTSTRAP_ARGV_PREFIX,
        "/retained/bootstrap.py", "supervisor", "/repo", "/pre", "/pre/manifest.json",
    )
    env = {
        "ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256": "a" * 64,
        "LC_CTYPE": "C.UTF-8",
    }
    descriptors = {target: target + 1000 for target in run.INTERNAL_FD_TARGETS["SUPERVISOR"]}
    run.LinuxClone3V180R12R4.validate_internal_exec_contract(
        role="SUPERVISOR", argv=argv, env=env, inherited_fd_map=descriptors
    )
    with pytest.raises(run.V180R12R4RuntimeError):
        run.LinuxClone3V180R12R4.validate_internal_exec_contract(
            role="SUPERVISOR",
            argv=argv,
            env={**env, "ATTEMPT_ID": "b" * 64},
            inherited_fd_map=descriptors,
        )
    swapped = dict(descriptors)
    swapped.pop(245)
    swapped[246] = 1246
    with pytest.raises(run.V180R12R4RuntimeError):
        run.LinuxClone3V180R12R4.validate_internal_exec_contract(
            role="SUPERVISOR", argv=argv, env=env, inherited_fd_map=swapped
        )


def test_partial_cgroup_create_cleans_owned_root_without_real_cgroup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mount = tmp_path / "mount"
    parent = mount / "delegated"
    parent.mkdir(parents=True)
    values = {
        "cgroup.controllers": "memory pids\n",
        "cgroup.subtree_control": "memory pids\n",
        "cgroup.type": "domain\n",
        "cgroup.events": "populated 0\nfrozen 0\n",
        "memory.events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n",
        "pids.events": "max 0\n",
        "cgroup.kill": "",
        "cgroup.procs": "",
        "memory.peak": "0\n",
        "pids.peak": "0\n",
    }
    for name, raw in values.items():
        (parent / name).write_text(raw, encoding="ascii")
    mount_stat = mount.stat()
    parent_stat = parent.stat()
    fact = {
        "mount_point": str(mount),
        "parent_path": str(parent),
        "mount_device": mount_stat.st_dev,
        "mount_inode": mount_stat.st_ino,
        "parent_device": parent_stat.st_dev,
        "parent_inode": parent_stat.st_ino,
        "owner_uid": parent_stat.st_uid,
        "owner_gid": parent_stat.st_gid,
        "mode": parent_stat.st_mode & 0o777,
        "controllers": ["memory", "pids"],
        "subtree_control": ["memory", "pids"],
        "cgroup_type": "domain",
        "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
        "self_membership": run._proc_cgroup(os.getpid()),
    }
    monkeypatch.setattr(run.protocol, "validate_cgroup_parent_fact_v180r12r4", lambda value: value)
    monkeypatch.setattr(run.LinuxCgroupV2V180R12R4, "_fstatfs_type", staticmethod(lambda fd: run.CGROUP2_SUPER_MAGIC))

    def fail_after_root(name: str) -> None:
        if name == "ROOT_OPENED":
            raise RuntimeError("synthetic partial create")

    adapter = run.LinuxCgroupV2V180R12R4(fail_after_root)
    attempt_id = "a" * 64
    mount_source = os.open(mount, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    parent_source = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.dup2(parent_source, run.DELEGATED_CGROUP_PARENT_FD, inheritable=False)
        os.dup2(mount_source, run.CGROUP2_MOUNT_FD, inheritable=False)
        with pytest.raises(RuntimeError, match="synthetic partial create"):
            adapter.create(fact, attempt_id)
        assert not (parent / f"v180r12r4-{attempt_id}").exists()
    finally:
        for descriptor in (
            run.DELEGATED_CGROUP_PARENT_FD,
            run.CGROUP2_MOUNT_FD,
            mount_source,
            parent_source,
        ):
            try:
                os.close(descriptor)
            except OSError:
                pass

    second_attempt_id = "b" * 64
    root_name = f"v180r12r4-{second_attempt_id}"
    original_rmdir = os.rmdir

    def fail_owned_root_cleanup(path, *args, dir_fd=None, **kwargs):
        if path == root_name and dir_fd == run.DELEGATED_CGROUP_PARENT_FD:
            raise OSError("synthetic retained partial root")
        return original_rmdir(path, *args, dir_fd=dir_fd, **kwargs)

    mount_source = os.open(mount, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    parent_source = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.dup2(parent_source, run.DELEGATED_CGROUP_PARENT_FD, inheritable=False)
        os.dup2(mount_source, run.CGROUP2_MOUNT_FD, inheritable=False)
        with monkeypatch.context() as cleanup_patch:
            cleanup_patch.setattr(os, "rmdir", fail_owned_root_cleanup)
            with pytest.raises(
                run.V180R12R4PartialCgroupCreateFailure
            ) as captured:
                adapter.create(fact, second_attempt_id)
        rows = captured.value.node_observations
        assert tuple(row["role"] for row in rows) == (
            "MEASUREMENT_ROOT", "SUPERVISOR", "WORKER"
        )
        assert rows[0]["path"] == str(parent / root_name)
        assert rows[0]["state"] == "READ_ERROR"
        assert tuple(row["state"] for row in rows[1:]) == ("ABSENT", "ABSENT")
        original_rmdir(parent / root_name)
    finally:
        for descriptor in (
            run.DELEGATED_CGROUP_PARENT_FD,
            run.CGROUP2_MOUNT_FD,
            mount_source,
            parent_source,
        ):
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_timeout_maps_to_cap_and_success_teardown_failure_keeps_reserve_until_terminal_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    order: list[str] = []
    plan = _fake_plan()

    class Campaign:
        def __init__(self, **kwargs):
            del kwargs
            self.success_event_plan = plan
            self.event_count = 0

        def register_evidence_document(self, document):
            del document

        def append_event(self, **kwargs):
            del kwargs
            event = _Event(self.event_count)
            self.event_count += 1
            return event

        def assert_success_schedule_complete(self):
            assert self.event_count == 625

    class Journal:
        def __init__(self, store, **kwargs):
            del store, kwargs
            self.schedule = plan
            self.next_sequence = 0
            self.previous_event_id = None

        def append(self, document):
            del document
            ack = {"sequence": self.next_sequence}
            self.previous_event_id = f"{self.next_sequence:064x}"
            self.next_sequence += 1
            return ack

        def assert_complete(self):
            assert self.next_sequence == 625

    class TrackingReserve(bytearray):
        def clear(self):
            order.append("reserve_clear")
            super().clear()

    class Adapter:
        close_calls = 0

        def create_cgroup(self, attempt):
            del attempt
            return object(), object()

        def launch_supervisor(self, cgroup, operation_id, deadline):
            del cgroup, operation_id, deadline
            return object(), object()

        def acknowledge_event(self, child, ack):
            del child, ack

        def receive_event_proposals(self, child, deadline):
            del child, deadline
            for sequence, row in enumerate(plan[3:622], start=3):
                evidence_document = None
                evidence_id = None
                if row.event_kind == "WINDOW_CLOSED":
                    evidence_id = "f" * 64
                    evidence_document = {
                        "schema": "acfqp.synthetic_window_closure.v180r12r4",
                        "synthetic_window_closure_id": evidence_id,
                    }
                payload = supervisor.campaign_event_payload_v180r12r4(
                    event_kind=row.event_kind,
                    evidence_id=evidence_id,
                    measured_value=None,
                    auxiliary_values=(),
                )
                yield run.ObserverEventProposalV180R12R4(
                    sequence,
                    row.phase,
                    row.actor_role,
                    row.event_kind,
                    row.operation_id,
                    payload,
                    evidence_document,
                )

        def reap_supervisor(self, child, operation_id, deadline_ns):
            del child, operation_id
            assert deadline_ns == 10**15
            return object()

        def close_supervisor_pidfd_after_reap_ack(self, child, receipt):
            del child, receipt
            order.append("pidfd_close")

        def observe_cgroup(self, cgroup, reap, operation_id):
            del cgroup, reap, operation_id
            return SimpleNamespace(memory_peak_bytes=1)

        def kill_cgroup(self, cgroup):
            del cgroup
            order.append("kill")

        def terminate_and_reap(self, child):
            del child
            order.append("reap")

        def observe_cgroup_failure(self, cgroup):
            del cgroup
            order.append("failure_observe")
            return {"observation_errors": ()}

        def close_cgroup(self, cgroup):
            del cgroup
            self.close_calls += 1
            order.append(f"close:{self.close_calls}")
            if self.close_calls == 1:
                raise RuntimeError("synthetic teardown failure")

    monkeypatch.setattr(run.runtime, "CampaignMeasurementSupervisorV180R12R4", Campaign)
    monkeypatch.setattr(run, "CanonicalEventJournalV180R12R4", Journal)
    monkeypatch.setattr(
        run,
        "_validate_registered_evidence_document_v180r12r4",
        lambda document, *, expected_schema: (
            dict(document),
            document["synthetic_window_closure_id"],
        ),
    )
    monkeypatch.setattr(
        run,
        "register_campaign_execution_closure_v180r12r4",
        lambda **kwargs: None,
    )
    store = run.DurableStoreV180R12R4(tmp_path)
    monkeypatch.setattr(
        store,
        "reserve_failure_space",
        lambda byte_count=run.FAILURE_RESERVE_BYTES: TrackingReserve(byte_count),
    )
    adapter = Adapter()
    try:
        with pytest.raises(RuntimeError, match="teardown failure"):
            authority, attempt_document, _manifest = _attempt_fixture()
            run.run_one_shot_outer_v180r12r4(
                store=store,
                adapter=adapter,
                attempt_document=attempt_document,
                attempt_authority=authority,
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
                campaign_deadline_ns=10**15,
                forbidden_progress_paths=(),
                monotonic_ns=iter(range(10_000)).__next__,
            )
        assert order.index("close:1") < order.index("reserve_clear") < order.index("kill")
        assert order[-1] == "close:2"
        failure = json.loads(store.read_exact(run.FAILURE_RELATIVE_PATH, 4 * 1024 * 1024))
        assert failure["failure_code"] == "LEDGER_FAILURE"
        assert failure["cgroup_failure_observation"]["kill_outcome"] == "SUCCESS"
        assert failure["cgroup_failure_observation"]["close_outcome"] == "SUCCESS"
    finally:
        store.close()

    artifacts = tuple(
        supervisor.FailureArtifactObservationV180R12R4(
            path, kind, "ABSENT", None, None, None, None, None, None, None
        )
        for path, kind in supervisor.FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
    )
    timeout = run._failure_document(
        protocol_id="1" * 64,
        authorization_id="2" * 64,
        attempt_id="3" * 64,
        journal=None,
        error=run.V180R12R4RuntimeTimeout("deadline"),
        cleanup_errors=(),
        partial_artifact_observations=artifacts,
        cgroup_failure_observation=None,
    )
    assert timeout["failure_code"] == "CAP_VIOLATION"


def test_malformed_partial_cgroup_nodes_fall_back_without_losing_typed_failure() -> None:
    observation = run._failure_cgroup_observation_v180r12r4(
        {"node_observations": [{"role": "MEASUREMENT_ROOT"}, object(), {}]},
        kill_outcome="NOT_AVAILABLE_PARTIAL_CREATE",
        reap_outcome="NO_CHILD_HANDLE",
        close_outcome="INTERNAL_CLEANUP_INCOMPLETE",
    )
    rows = observation.to_document()["node_observations"]
    assert tuple(row["role"] for row in rows) == (
        "MEASUREMENT_ROOT", "SUPERVISOR", "WORKER"
    )
    assert tuple(row["state"] for row in rows) == (
        "READ_ERROR", "READ_ERROR", "READ_ERROR"
    )


def test_closed_observer_population_calls_one_finalizer_and_commits_four_then_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_module = _load(
        "_test_run_v180r12r4_finalizer_fixture",
        "tests/test_construction_k7_campaign_measurement_finalizer_v180r12r4.py",
    )
    closed = fixture_module._closed_inputs()
    fixture = closed["fixture"]
    inventory = ledger.CampaignEvidenceInventoryV180R12R4.from_documents(
        closed["evidence_documents"]
    )

    class ClosedCampaign:
        protocol_id = fixture["state"].protocol_id
        authorization_id = fixture["state"].authorization_id
        attempt_id = fixture["state"].attempt_id
        ledger_state = fixture["state"]

        @staticmethod
        def assert_success_schedule_complete():
            assert len(fixture["state"].events) == 625

        @staticmethod
        def validate_registered_evidence_bundle():
            return inventory

    class RetainedJournal:
        @staticmethod
        def read_complete_event_documents():
            return tuple(closed["event_documents"])

    inputs = run.build_finalize_success_inputs_v180r12r4(
        campaign=ClosedCampaign(), journal=RetainedJournal()
    )
    assert tuple(inputs.to_kwargs()) == run.FINALIZE_SUCCESS_INPUT_FIELDS
    assert inputs.event_documents == tuple(closed["event_documents"])
    assert inputs.evidence_documents == tuple(closed["evidence_documents"])
    assert inputs.os_receipt_documents == tuple(closed["os_receipt_documents"])
    assert inputs.expected_subject_id == fixture["subject_id"]
    assert inputs.expected_native_zero_source_manifest_id == fixture["source_manifest_id"]
    assert inputs.expected_native_zero_import_inventory_id == fixture["import_inventory_id"]

    calls: list[dict[str, object]] = []
    original_finalize = run.finalizer.finalize_campaign_measurement_terminal_v180r12r4

    def finalize_once(**kwargs):
        calls.append(kwargs)
        return original_finalize(**kwargs)

    monkeypatch.setattr(
        run.finalizer,
        "finalize_campaign_measurement_terminal_v180r12r4",
        finalize_once,
    )
    with tempfile.TemporaryDirectory(prefix="v180r12r4-success-", dir="/tmp") as root:
        store = run.DurableStoreV180R12R4(Path(root))
        writes: list[str] = []
        original_write = store.write_once

        def ordered_write(relative_path, raw, *, mode=0o400):
            writes.append(relative_path)
            return original_write(relative_path, raw, mode=mode)

        store.write_once = ordered_write
        try:
            result = run.finalize_and_materialize_success_v180r12r4(
                store=store,
                inputs=inputs,
                campaign_deadline_ns=(
                    run.time.monotonic_ns() + 60 * run.NANOSECONDS_PER_SECOND
                ),
            )
            expected_paths = [
                run.SUCCESS_ARTIFACT_RELATIVE_PATH_BY_KEY[key]
                for key in run.finalizer.SUCCESS_ARTIFACT_ORDER
            ] + [run.TERMINAL_RELATIVE_PATH]
            assert writes == expected_paths
            assert len(calls) == 1
            assert calls[0] == inputs.to_kwargs()
            assert result.document[
                "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS"
            ] == "PENDING_INDEPENDENT_REPLAY"
            assert result.document["independent_verification_present"] is False
            for key, schema, identity_field, _terminal_prefix in (
                run.finalizer.SUCCESS_ARTIFACT_SCHEMA_ROWS
            ):
                path = run.SUCCESS_ARTIFACT_RELATIVE_PATH_BY_KEY[key]
                raw = store.read_exact(
                    path, run.SUCCESS_ARTIFACT_BYTE_CAP_BY_KEY[key]
                )
                document = json.loads(raw)
                assert document["schema"] == schema
                assert document[identity_field] == result.document[identity_field]
                assert os.stat(Path(root) / path).st_mode & 0o777 == 0o400
            assert store.read_exact(
                run.TERMINAL_RELATIVE_PATH, run.protocol.TERMINAL_BYTE_CAP
            ) == result.canonical_bytes
            assert os.stat(
                Path(root) / run.TERMINAL_RELATIVE_PATH
            ).st_mode & 0o777 == 0o400
        finally:
            store.close()

    os_raw = result.success_artifact_bytes["os_receipt"]
    monkeypatch.setitem(
        run.SUCCESS_ARTIFACT_BYTE_CAP_BY_KEY, "os_receipt", len(os_raw) - 1
    )
    with tempfile.TemporaryDirectory(prefix="v180r12r4-cap-", dir="/tmp") as root:
        store = run.DurableStoreV180R12R4(Path(root))
        try:
            with pytest.raises(run.V180R12R4CapViolation, match="os_receipt"):
                run.finalize_and_materialize_success_v180r12r4(
                    store=store,
                    inputs=inputs,
                    campaign_deadline_ns=(
                        run.time.monotonic_ns()
                        + 60 * run.NANOSECONDS_PER_SECOND
                    ),
                )
            assert not any(
                store.exists(path)
                for path in (
                    *run.SUCCESS_ARTIFACT_RELATIVE_PATH_BY_KEY.values(),
                    run.TERMINAL_RELATIVE_PATH,
                )
            )
        finally:
            store.close()

    # Crossing the shared campaign deadline after pure finalization cannot
    # create even the first success artifact, much less a late TERMINAL.
    monkeypatch.setitem(
        run.SUCCESS_ARTIFACT_BYTE_CAP_BY_KEY, "os_receipt", run.protocol.OS_RECEIPT_BUNDLE_BYTE_CAP
    )
    with tempfile.TemporaryDirectory(prefix="v180r12r4-deadline-", dir="/tmp") as root:
        store = run.DurableStoreV180R12R4(Path(root))
        ticks = iter((4, 5)).__next__
        try:
            with pytest.raises(run.V180R12R4RuntimeTimeout, match="finalizer return"):
                run.finalize_and_materialize_success_v180r12r4(
                    store=store,
                    inputs=inputs,
                    campaign_deadline_ns=5,
                    monotonic_ns=ticks,
                )
            assert not any(
                store.exists(path)
                for path in (
                    *run.SUCCESS_ARTIFACT_RELATIVE_PATH_BY_KEY.values(),
                    run.TERMINAL_RELATIVE_PATH,
                )
            )
        finally:
            store.close()


def test_hostile_cleanup_getattr_and_whole_progress_observer_failure_still_freeze_exact_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class HostileFailure(RuntimeError):
        def __getattribute__(self, name):
            if name == "cleanup_errors":
                raise MemoryError("hostile cleanup attribute")
            return super().__getattribute__(name)

    class BrokenJournal:
        def __init__(self, *args, **kwargs):
            del args, kwargs
            raise HostileFailure("synthetic journal construction failure")

    class ForbiddenAdapter:
        def create_cgroup(self, attempt):  # pragma: no cover - forbidden
            raise AssertionError(attempt)

    store = run.DurableStoreV180R12R4(tmp_path)
    monkeypatch.setattr(run, "CanonicalEventJournalV180R12R4", BrokenJournal)
    monkeypatch.setattr(
        store,
        "observe_failure_progress",
        lambda: (_ for _ in ()).throw(RuntimeError("synthetic observer failure")),
    )
    try:
        with pytest.raises(HostileFailure, match="journal construction"):
            authority, attempt_document, _manifest = _attempt_fixture()
            run.run_one_shot_outer_v180r12r4(
                store=store,
                adapter=ForbiddenAdapter(),
                attempt_document=attempt_document,
                attempt_authority=authority,
                protocol_id=authority.protocol_id,
                authorization_id=authority.authorization_id,
                attempt_id=authority.attempt_id,
                campaign_deadline_ns=(
                    run.time.monotonic_ns() + 60 * run.NANOSECONDS_PER_SECOND
                ),
                forbidden_progress_paths=(),
            )
        failure = json.loads(
            store.read_exact(run.FAILURE_RELATIVE_PATH, 4 * 1024 * 1024)
        )
        assert failure["partial_artifact_observation_boundary"] == (
            supervisor.FAILURE_ARTIFACT_OBSERVATION_BOUNDARY
        )
        rows = failure["partial_artifact_observations"]
        assert [(row["relative_path"], row["kind"]) for row in rows] == list(
            supervisor.FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
        )
        assert all(row["state"] == "READ_ERROR" for row in rows)
        assert next(
            row for row in rows if row["relative_path"] == run.FAILURE_RELATIVE_PATH
        )["state"] == "READ_ERROR"
    finally:
        store.close()


def test_failure_text_uses_base_primitives_for_hostile_str_values() -> None:
    class HostileFailure(RuntimeError):
        def __str__(self):  # pragma: no cover - must never dispatch
            raise MemoryError("hostile exception string")

    class HostileObservation:
        def __str__(self):  # pragma: no cover - must never dispatch
            raise MemoryError("hostile observation string")

    rendered = run._bounded_exception_text(HostileFailure("primary"))
    assert rendered == "HostileFailure: primary"
    assert run._bounded_text_v180r12r4(
        HostileObservation(), byte_cap=512, fallback="fallback"
    ) == "<HostileObservation>"


def test_reaped_pidfd_close_is_exactly_after_receipt_boundary_and_leaks_no_fd() -> None:
    descriptor, writer = os.pipe2(os.O_CLOEXEC)
    metadata = os.fstat(descriptor)
    handle = run.ProcessHandleV180R12R4(
        "WORKER",
        os.getpid(),
        descriptor,
        metadata.st_dev,
        metadata.st_ino,
        1,
        os.getpid(),
        (os.getpid(),),
        "0::/synthetic",
        9,
        10,
        11,
    )
    try:
        run.close_reaped_pidfd_v180r12r4(handle)
        with pytest.raises(OSError):
            os.fstat(descriptor)
        with pytest.raises(OSError):
            run.close_reaped_pidfd_v180r12r4(handle)
    finally:
        os.close(writer)


def test_external_replay_read_rejects_same_bytes_with_mode_drift(
    tmp_path: Path,
) -> None:
    store = run.DurableStoreV180R12R4(tmp_path)
    try:
        store.write_once("mode-bound.json", b"{}", mode=0o400)
        os.chmod(tmp_path / "mode-bound.json", 0o600)
        with pytest.raises(run.V180R12R4RuntimeError, match="bounded single-link"):
            store.read_exact(
                "mode-bound.json", 1024, expected_mode=0o400
            )
    finally:
        store.close()


def test_external_authority_replay_normalizes_post_literal_wrapper_before_exact_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pre-ATTEMPT replay joins the C_pre fact, never raw literal bytes."""

    wrapper_path = authorization._AUTHORIZATION_EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    physical_wrapper_raw = (ROOT / wrapper_path).read_bytes()
    normalized_wrapper_raw = (
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
            physical_wrapper_raw
        )
    )
    post_literal_wrapper_raw = physical_wrapper_raw
    if post_literal_wrapper_raw == normalized_wrapper_raw:
        # Keep this regression executable during C_pre construction too.  At
        # the frozen literal HEAD the physical bytes already have this shape.
        for name, (start, end, _replacement) in sorted(
            authorization._authorization_evidence_literal_spans(  # noqa: SLF001
                physical_wrapper_raw
            ).items(),
            key=lambda item: item[1][0],
            reverse=True,
        ):
            replacement = (
                b'"1111111111111111111111111111111111111111111111111111111111111111"'
                if name
                in authorization._AUTHORIZATION_EVIDENCE_STRING_CONSTANTS  # noqa: SLF001
                else b"123456"
            )
            post_literal_wrapper_raw = (
                post_literal_wrapper_raw[:start]
                + replacement
                + post_literal_wrapper_raw[end:]
            )
    assert post_literal_wrapper_raw != normalized_wrapper_raw
    assert (
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r4(
            post_literal_wrapper_raw
        )
        == normalized_wrapper_raw
    )

    source_raw_by_path = {
        relative_path: (
            post_literal_wrapper_raw
            if relative_path == wrapper_path
            else (ROOT / relative_path).read_bytes()
        )
        for relative_path in authorization.SOURCE_CLOSURE_REQUIRED_ROOTS
    }
    monkeypatch.setattr(
        authorization,
        "_read_regular_stable",
        lambda relative_path: source_raw_by_path[relative_path],
    )
    expected_source_facts = tuple(
        {
            "relative_path": relative_path,
            "byte_count": len(
                normalized_wrapper_raw
                if relative_path == wrapper_path
                else source_raw_by_path[relative_path]
            ),
            "sha256": hashlib.sha256(
                normalized_wrapper_raw
                if relative_path == wrapper_path
                else source_raw_by_path[relative_path]
            ).hexdigest(),
        }
        for relative_path in authorization.SOURCE_CLOSURE_REQUIRED_ROOTS
    )
    raw_wrapper_fact = {
        "relative_path": wrapper_path,
        "byte_count": len(post_literal_wrapper_raw),
        "sha256": hashlib.sha256(post_literal_wrapper_raw).hexdigest(),
    }
    normalized_wrapper_fact = next(
        row for row in expected_source_facts if row["relative_path"] == wrapper_path
    )
    assert raw_wrapper_fact != normalized_wrapper_fact

    cgroup_fact = cgroup_parent_fact()
    capability_fact = runtime_capability_fact()
    frozen_protocol = run.protocol.freeze_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_fact,
        runtime_capability_fact=capability_fact,
    )
    expected_authorization = (
        authorization.freeze_campaign_measurement_execution_authorization_v180r12r4(
            cgroup_parent_fact=cgroup_fact,
            runtime_capability_fact=capability_fact,
            source_facts=expected_source_facts,
        )
    )
    protocol_document = frozen_protocol.to_document()
    authorization_document = expected_authorization.to_document()
    evidence_id = "e" * 64
    evidence_raw = run._canonical(
        {
            "schema": (
                "acfqp.campaign_measurement_authorization_evidence.v180r12r4"
            ),
            "campaign_measurement_protocol_id": (
                frozen_protocol.campaign_measurement_protocol_id
            ),
            "execution_authorization_id": (
                expected_authorization.execution_authorization_id
            ),
            "campaign_measurement_execution_slot_id": authorization_document[
                "campaign_measurement_execution_slot_id"
            ],
            "authorization_evidence_id": evidence_id,
        }
    )
    monkeypatch.setattr(
        authorization_evidence,
        "freeze_campaign_measurement_authorization_evidence_v180r12r4",
        lambda *_args, **_kwargs: SimpleNamespace(canonical_bytes=evidence_raw),
    )

    materialization_id = "7" * 64
    manifest_sha256 = "8" * 64
    launch_rule_id = "9" * 64
    launch_attempt_id = "a" * 64
    materialization_raw = run._canonical(
        {
            "materialization_terminal_id": materialization_id,
            "launch_manifest": {"sha256": manifest_sha256},
        }
    )
    launch_attempt_raw = run._canonical(
        {
            "launch_attempt_id": launch_attempt_id,
            "target": "measurement",
            "materialization_terminal_id": materialization_id,
            "launch_manifest_sha256": manifest_sha256,
            "launch_rule_id": launch_rule_id,
            "production_systemd_service_invocation": (
                _production_invocation("measurement")
            ),
        }
    )
    local_root_resource = tempfile.TemporaryDirectory(dir=ROOT / ".tmp")
    local_root = Path(local_root_resource.name)
    store = run.DurableStoreV180R12R4(local_root)
    try:
        store.write_once(
            run.protocol.PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH,
            materialization_raw,
        )
        store.write_once(
            run.protocol.PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
            launch_attempt_raw,
        )

        logical_occurrence_id = authorization_document["logical_occurrence_id"]
        execution_nonce = authorization_document["execution_nonce"]
        campaign_slot_id = authorization_document[
            "campaign_measurement_execution_slot_id"
        ]
        campaign_attempt_id = (
            run.identity_domains.derive_campaign_measurement_attempt_id_v180r12r4(
                protocol_id=frozen_protocol.campaign_measurement_protocol_id,
                authorization_id=expected_authorization.execution_authorization_id,
                authorization_evidence_id=evidence_id,
                campaign_measurement_execution_slot_id=campaign_slot_id,
                logical_occurrence_id=logical_occurrence_id,
                execution_nonce=execution_nonce,
            )
        )
        origin_ns = 10 * run.NANOSECONDS_PER_SECOND
        hard_deadline_ns = origin_ns + run.HARD_DEADLINE_DURATION_NS
        campaign_deadline_ns = hard_deadline_ns - run.CAMPAIGN_CLEANUP_GRACE_NS
        native_zero_rows = (
            {
                "source_kind": "MODULE",
                "name": "acfqp",
                "source_path": "src/acfqp/__init__.py",
                "is_package": True,
                "marshal_byte_count": 1,
                "marshal_sha256": "b" * 64,
            },
            *(
                {
                    "source_kind": "TARGET",
                    "name": target,
                    "source_path": source_path,
                    "is_package": False,
                    "marshal_byte_count": 1,
                    "marshal_sha256": "c" * 64,
                }
                for target, source_path in sorted(
                    run.ledger.PRECOMPILED_TARGET_SOURCE_PATHS.items()
                )
            ),
        )
        external_values = {
            "schema": run.EXTERNAL_LAUNCH_CONTEXT_SCHEMA,
            "target": "measurement",
            "actor_role": "OBSERVER",
            "repository_root": str(local_root),
            "c_pre_root": str(local_root / "C_pre"),
            "prereg_commit_id": "d" * 40,
            "prelaunch_materialization_terminal_id": materialization_id,
            "prelaunch_materialization_terminal_byte_count": len(materialization_raw),
            "prelaunch_materialization_terminal_sha256": hashlib.sha256(
                materialization_raw
            ).hexdigest(),
            "prelaunch_launch_manifest_sha256": manifest_sha256,
            "prelaunch_launch_rule_id": launch_rule_id,
            "current_launch_attempt_id": launch_attempt_id,
            "current_launch_attempt_byte_count": len(launch_attempt_raw),
            "current_launch_attempt_sha256": hashlib.sha256(
                launch_attempt_raw
            ).hexdigest(),
            "measurement_launch_attempt_id": launch_attempt_id,
            "measurement_launch_attempt_byte_count": len(launch_attempt_raw),
            "measurement_launch_attempt_sha256": hashlib.sha256(
                launch_attempt_raw
            ).hexdigest(),
            "protocol_id": frozen_protocol.campaign_measurement_protocol_id,
            "protocol_byte_count": len(frozen_protocol.canonical_bytes),
            "protocol_sha256": hashlib.sha256(
                frozen_protocol.canonical_bytes
            ).hexdigest(),
            "authorization_id": expected_authorization.execution_authorization_id,
            "authorization_byte_count": len(expected_authorization.canonical_bytes),
            "authorization_sha256": hashlib.sha256(
                expected_authorization.canonical_bytes
            ).hexdigest(),
            "authorization_evidence_id": evidence_id,
            "authorization_evidence_byte_count": len(evidence_raw),
            "authorization_evidence_sha256": hashlib.sha256(evidence_raw).hexdigest(),
            "campaign_measurement_execution_slot_id": campaign_slot_id,
            "logical_occurrence_id": logical_occurrence_id,
            "execution_nonce": execution_nonce,
            "campaign_attempt_id": campaign_attempt_id,
            "monotonic_origin_ns": origin_ns,
            "hard_deadline_ns": hard_deadline_ns,
            "campaign_deadline_ns": campaign_deadline_ns,
            "cgroup_parent_fact": cgroup_fact,
            "runtime_capability_fact": capability_fact,
            "production_systemd_service_invocation": (
                _production_invocation("measurement")
            ),
            "production_runtime_placement_t1": _placement_t1("measurement"),
            "inherited_fd_roles": [
                list(row) for row in run.EXTERNAL_FD_ROLE_ROWS["measurement"]
            ],
            "target_payload": {
                "delegated_cgroup_parent_fd": run.DELEGATED_CGROUP_PARENT_FD,
                "cgroup2_mount_fd": run.CGROUP2_MOUNT_FD,
                "source_systemd_service_fd": run.SOURCE_SYSTEMD_SERVICE_FD,
            },
            "one_shot": True,
        }
        assert tuple(external_values) == run.EXTERNAL_LAUNCH_CONTEXT_FIELDS
        external_context_sha256 = hashlib.sha256(
            run._canonical(external_values)
        ).hexdigest()
        verified_values = {
            **external_values,
            "schema": run.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA,
            "inherited_fd_roles": run.EXTERNAL_FD_ROLE_ROWS["measurement"],
            "precompiled_source_bundle_sha256": "f" * 64,
            "native_zero_precompiled_source_rows": native_zero_rows,
            "external_launch_context_sha256": external_context_sha256,
            "context_consumed_once": True,
        }
        context = types.MappingProxyType(
            {
                name: verified_values[name]
                for name in run.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
            }
        )

        replayed = run.replay_external_authority_documents_v180r12r4(
            context, store=store
        )
        assert replayed["protocol"] == frozen_protocol.canonical_bytes
        assert replayed["authorization"] == expected_authorization.canonical_bytes
        assert replayed["authorization_evidence"] == evidence_raw
        replayed_authorization = json.loads(replayed["authorization"])
        replayed_facts = replayed_authorization["source_closure_candidate"][
            "source_facts"
        ]
        assert normalized_wrapper_fact in replayed_facts
        assert raw_wrapper_fact not in replayed_facts
        assert protocol_document["campaign_measurement_protocol_id"] == context[
            "protocol_id"
        ]

        assert (
            run.validate_verified_external_launch_context_v180r12r4(
                context,
                replayed_documents=replayed,
                monotonic_ns=lambda: origin_ns + 1,
            )
            is context
        )
        for key, _id_key, count_key, sha_key, _identity_field in (
            run.EXTERNAL_REPLAY_DOCUMENT_ROWS
        ):
            assert len(replayed[key]) == context[count_key]
            assert hashlib.sha256(replayed[key]).hexdigest() == context[sha_key]
    finally:
        store.close()
        local_root_resource.cleanup()


def test_snapshot_wire_transport_rehydrates_native_receipt_without_second_read() -> None:
    fact = worker.frozen_campaign_input_facts_v180r12r4()[1]
    raw = (ROOT / fact.relative_path).read_bytes()
    snapshot = worker.StableInputSnapshotReceiptV180R12R4(fact, raw)
    transport = {
        "schema": run.SNAPSHOT_BYTES_TRANSPORT_SCHEMA,
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "role": fact.role.value,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_bytes_hex": raw.hex(),
    }
    registry = run.TypedWireEvidenceRegistryV180R12R4()
    values = registry.decode_batch(
        (snapshot.to_document(), transport),
        campaign_event_sequence=6,
        phase="STAGE",
        actor_role="SUPERVISOR",
        event_kind="INPUT_READ_OUTCOME",
    )
    assert len(values) == 1
    assert type(values[0]) is worker.StableInputSnapshotReceiptV180R12R4
    assert values[0].to_document() == snapshot.to_document()
    assert registry._snapshot_bytes_by_id == {}

    with pytest.raises(run.V180R12R4RuntimeError, match="lacks its authenticated"):
        run.TypedWireEvidenceRegistryV180R12R4().decode(snapshot.to_document())

    drifted = json.loads(json.dumps(transport))
    drifted["canonical_bytes_hex"] = (bytes([raw[0] ^ 1]) + raw[1:]).hex()
    with pytest.raises(run.V180R12R4RuntimeError, match="digest"):
        run.TypedWireEvidenceRegistryV180R12R4().decode_batch(
            (snapshot.to_document(), drifted),
            campaign_event_sequence=6,
            phase="STAGE",
            actor_role="SUPERVISOR",
            event_kind="INPUT_READ_OUTCOME",
        )


def test_snapshot_transport_survives_canonical_wire_order_and_is_exactly_once() -> None:
    fact = worker.frozen_campaign_input_facts_v180r12r4()[1]
    raw = (ROOT / fact.relative_path).read_bytes()
    snapshot = worker.StableInputSnapshotReceiptV180R12R4(fact, raw)
    transport = {
        "schema": run.SNAPSHOT_BYTES_TRANSPORT_SCHEMA,
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "role": fact.role.value,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_bytes_hex": raw.hex(),
    }
    # Exercise the alphabetical key order produced by the authenticated
    # channel's canonical JSON decode, not only constructor-order mappings.
    wire_rows = json.loads(run._canonical([snapshot.to_document(), transport]))
    registry = run.TypedWireEvidenceRegistryV180R12R4()
    value, = registry.decode_batch(
        wire_rows,
        campaign_event_sequence=6,
        phase="STAGE",
        actor_role="SUPERVISOR",
        event_kind="INPUT_READ_OUTCOME",
    )
    assert type(value) is worker.StableInputSnapshotReceiptV180R12R4
    with pytest.raises(run.V180R12R4RuntimeError, match="one-shot"):
        registry.decode_batch(
            wire_rows,
            campaign_event_sequence=6,
            phase="STAGE",
            actor_role="SUPERVISOR",
            event_kind="INPUT_READ_OUTCOME",
        )
    with pytest.raises(run.V180R12R4RuntimeError, match="transport attachment"):
        run.TypedWireEvidenceRegistryV180R12R4().decode_batch(
            wire_rows,
            campaign_event_sequence=8,
            phase="STAGE",
            actor_role="SUPERVISOR",
            event_kind="STAGE_WRITE_OUTCOME",
        )


def test_external_measurement_bootstrap_entrypoint_reaches_concrete_outer_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The retained external target dispatches; direct script invocation does not."""

    authority, attempt, operation_manifest = _attempt_fixture()
    origin_ns = run.time.monotonic_ns()
    hard_deadline_ns = origin_ns + run.HARD_DEADLINE_DURATION_NS
    values = {name: "f" * 64 for name in run.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS}
    values.update(
        {
            "schema": run.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA,
            "target": "measurement",
            "actor_role": "OBSERVER",
            "repository_root": str(tmp_path),
            "c_pre_root": str(tmp_path / "C_pre"),
            "prereg_commit_id": "a" * 40,
            "protocol_id": authority.protocol_id,
            "authorization_id": authority.authorization_id,
            "authorization_evidence_id": authority.authorization_evidence_id,
            "campaign_measurement_execution_slot_id": (
                authority.campaign_measurement_execution_slot_id
            ),
            "logical_occurrence_id": authority.logical_occurrence_id,
            "execution_nonce": authority.execution_nonce,
            "campaign_attempt_id": authority.attempt_id,
            "monotonic_origin_ns": origin_ns,
            "hard_deadline_ns": hard_deadline_ns,
            "campaign_deadline_ns": (
                hard_deadline_ns - run.CAMPAIGN_CLEANUP_GRACE_NS
            ),
            "prelaunch_materialization_terminal_id": (
                authority.prelaunch_materialization_terminal_id
            ),
            "prelaunch_launch_manifest_sha256": (
                authority.prelaunch_launch_manifest_sha256
            ),
            "prelaunch_launch_rule_id": authority.prelaunch_launch_rule_id,
            "measurement_launch_attempt_id": (
                authority.measurement_launch_attempt_id
            ),
            "native_zero_precompiled_source_rows": (),
            "cgroup_parent_fact": types.MappingProxyType({}),
                "runtime_capability_fact": types.MappingProxyType({}),
                "production_systemd_service_invocation": types.MappingProxyType(
                    _production_invocation("measurement")
                ),
                "production_runtime_placement_t1": types.MappingProxyType(
                    _placement_t1("measurement")
                ),
                "inherited_fd_roles": run.EXTERNAL_FD_ROLE_ROWS["measurement"],
            "target_payload": types.MappingProxyType(
                {
                    "delegated_cgroup_parent_fd": run.DELEGATED_CGROUP_PARENT_FD,
                        "cgroup2_mount_fd": run.CGROUP2_MOUNT_FD,
                        "source_systemd_service_fd": (
                            run.SOURCE_SYSTEMD_SERVICE_FD
                        ),
                }
            ),
            "context_consumed_once": True,
        }
    )
    context = types.MappingProxyType(
        {name: values[name] for name in run.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS}
    )

    class Store:
        def __init__(self, root):
            assert root == tmp_path
            self.closed = False

        def close(self):
            self.closed = True

    seen: list[tuple[str, object]] = []
    monkeypatch.setattr(run, "DurableStoreV180R12R4", Store)
    monkeypatch.setattr(
        run,
        "replay_external_authority_documents_v180r12r4",
        lambda supplied, *, store: ({"context": supplied, "store": store}),
    )
    revalidated_values = dict(context)
    revalidated_values["schema"] = (
        run.REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_SCHEMA
    )
    revalidated_values["production_runtime_placement_t2"] = (
        types.MappingProxyType({"schema": run.PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA})
    )
    revalidated_context = types.MappingProxyType(revalidated_values)
    monkeypatch.setattr(
        run,
        "revalidate_external_measurement_pre_attempt_v180r12r4",
        lambda supplied, *, replayed_documents: revalidated_context,
    )
    monkeypatch.setattr(
        run,
        "_revalidate_production_source_placement_v180r12r4",
        lambda *args, **kwargs: {
            "schema": run.PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA
        },
    )
    monkeypatch.setattr(
        run.CampaignAttemptAuthorityV180R12R4,
        "from_external_context",
        classmethod(lambda cls, supplied: authority),
    )
    monkeypatch.setattr(
        run,
        "build_campaign_attempt_record_v180r12r4",
        lambda supplied: (attempt, operation_manifest),
    )
    monkeypatch.setattr(
        run,
        "_validate_native_zero_precompiled_rows_v180r12r4",
        lambda supplied: tuple(supplied),
    )
    source = {"schema": "source"}
    imports = {"schema": "imports"}
    monkeypatch.setattr(
        run.ledger,
        "issue_native_zero_source_manifest_v180r12r4",
        lambda **kwargs: source,
    )
    monkeypatch.setattr(
        run.ledger,
        "issue_native_zero_import_inventory_v180r12r4",
        lambda **kwargs: imports,
    )
    monkeypatch.setattr(run.os, "open", lambda *args, **kwargs: 777)
    monkeypatch.setattr(run.os, "close", lambda descriptor: seen.append(("close", descriptor)))

    class Adapter:
        def __init__(self, **kwargs):
            seen.append(("adapter", kwargs))

    monkeypatch.setattr(run, "LinuxOuterEffectAdapterV180R12R4", Adapter)
    monkeypatch.setattr(
        run,
        "run_one_shot_outer_v180r12r4",
        lambda **kwargs: seen.append(("run", kwargs)),
    )
    assert run.bootstrap_entrypoint_v180r12r4(context) is None
    assert [name for name, _value in seen] == ["adapter", "run", "close"]
    run_kwargs = seen[1][1]
    assert run_kwargs["attempt_document"] == attempt
    assert run_kwargs["campaign_deadline_ns"] == (
        hard_deadline_ns - run.CAMPAIGN_CLEANUP_GRACE_NS
    )
    assert run_kwargs["preregistered_evidence_documents"] == (
        operation_manifest,
        source,
        imports,
    )
    with pytest.raises(run.V180R12R4RuntimeError, match="direct invocation"):
        run.main([])
