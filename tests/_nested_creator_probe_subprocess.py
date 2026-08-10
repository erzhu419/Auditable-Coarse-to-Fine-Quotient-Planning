from __future__ import annotations

import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import struct
import sys
import uuid

from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as role


def _write_at(directory_fd: int, name: str, raw: bytes) -> None:
    descriptor = os.open(name, os.O_WRONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise RuntimeError(f"short cgroup write: {name}")
            offset += written
    finally:
        os.close(descriptor)


def _open_dir_at(parent_fd: int, name: str) -> int:
    return os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=parent_fd,
    )


def _read_at(directory_fd: int, name: str, cap: int = 64) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        return os.read(descriptor, cap)
    finally:
        os.close(descriptor)


def _current_scope_path() -> Path:
    relative = next(
        line.removeprefix("0::").strip()
        for line in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        if line.startswith("0::")
    )
    return Path("/sys/fs/cgroup") / relative.lstrip("/")


def _spawn_role(executable_fd: int, child_control_fd: int) -> tuple[int, int]:
    pid = os.fork()
    if pid == 0:
        try:
            os.dup2(child_control_fd, 3, inheritable=True)
            os.dup2(executable_fd, 4, inheritable=True)
            os.closerange(5, 1 << 20)
            os.execve("/proc/self/fd/4", ["acfqp-h1-supervisor-v1"], {})
        except BaseException:
            os._exit(127)
    return pid, os.pidfd_open(pid, 0)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "SUCCESS"
    if mode not in {
        "SUCCESS",
        "AFTER_SESSION_RECORD_REGISTER",
        "AFTER_INNER_CONTROL_CLOSE",
        "AFTER_INNER_PIDFD_CLOSE",
        "AFTER_INNER_PIDFD_CONSUME",
        "ABORT_AFTER_INNER_CONTROL_CLOSE",
        "ABORT_AFTER_INNER_PIDFD_CLOSE",
        "ABORT_UNRELATED_CHILD",
        "ABORT_FAKE_CONTROL_MEMBER",
        "BEFORE_PARENT_RETURN",
        "WRONG_CGROUP_BEFORE_COMMAND",
        "ATFORK_REUSED_CLOSED_CONTROL",
    }:
        raise RuntimeError(f"unknown nested-creator probe mode: {mode}")
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "failed to enable child subreaper")
    scope = _current_scope_path()
    root_fd = os.open(
        scope, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    suffix = f"{os.getpid()}-{uuid.uuid4().hex}"
    guardian_name = f"acfqp-guardian-{suffix}"
    delegated_name = f"acfqp-delegated-{suffix}"
    outer_name = f"acfqp-outer-{suffix}"
    guardian_fd = delegated_fd = outer_fd = control_fd = -1
    parent_control: socket.socket | None = None
    child_control: socket.socket | None = None
    executable_fd = -1
    supervisor_pid = -1
    supervisor_pidfd = -1
    session = None
    moved = False
    try:
        os.mkdir(guardian_name, mode=0o700, dir_fd=root_fd)
        guardian_fd = _open_dir_at(root_fd, guardian_name)
        _write_at(guardian_fd, "cgroup.procs", f"{os.getpid()}\n".encode())
        moved = True
        _write_at(root_fd, "cgroup.subtree_control", b"+memory +pids\n")
        os.mkdir(delegated_name, mode=0o700, dir_fd=root_fd)
        delegated_fd = _open_dir_at(root_fd, delegated_name)
        _write_at(delegated_fd, "cgroup.subtree_control", b"+memory +pids\n")
        os.mkdir(outer_name, mode=0o700, dir_fd=delegated_fd)
        outer_fd = _open_dir_at(delegated_fd, outer_name)
        _write_at(outer_fd, "memory.max", str(64 * 1024 * 1024).encode() + b"\n")
        _write_at(outer_fd, "pids.max", b"3\n")
        _write_at(outer_fd, "cgroup.max.depth", b"1\n")
        _write_at(outer_fd, "cgroup.max.descendants", b"1\n")
        _write_at(outer_fd, "cgroup.subtree_control", b"+memory +pids\n")
        os.mkdir("control", mode=0o700, dir_fd=outer_fd)
        control_fd = _open_dir_at(outer_fd, "control")
        _write_at(control_fd, "pids.max", b"2\n")

        parent_control, child_control = socket.socketpair(
            socket.AF_UNIX,
            socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0),
        )
        parent_control.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        child_control.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
        executable_fd = role.create_sealed_nested_creator_supervisor_memfd_v1()
        supervisor_pid, supervisor_pidfd = _spawn_role(
            executable_fd, child_control.fileno()
        )
        child_control.close()
        child_control = None
        os.close(executable_fd)
        executable_fd = -1
        _write_at(control_fd, "cgroup.procs", f"{supervisor_pid}\n".encode())
        control_channel = parent_control.detach()
        parent_control = None
        if mode == "AFTER_SESSION_RECORD_REGISTER":
            probe._TEST_FAULT_PHASE = mode  # noqa: SLF001
            begin_error_type = ""
            try:
                probe.begin_nested_creator_supervisor_session_v1(
                    supervisor_pid=supervisor_pid,
                    supervisor_pidfd=supervisor_pidfd,
                    control_fd=control_channel,
                )
            except BaseException as error:
                begin_error_type = type(error).__name__
            finally:
                probe._TEST_FAULT_PHASE = None  # noqa: SLF001
            if not begin_error_type:
                raise RuntimeError("session record registration fault did not fail")
            os.close(control_channel)
            os.kill(supervisor_pid, signal.SIGKILL)
            os.waitpid(supervisor_pid, 0)
            supervisor_pid = -1
            os.close(supervisor_pidfd)
            supervisor_pidfd = -1
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "begin_error_type": begin_error_type,
                        "trusted_record_registry_count": len(
                            probe._LIVE_SESSIONS  # noqa: SLF001
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0

        session = probe.begin_nested_creator_supervisor_session_v1(
            supervisor_pid=supervisor_pid,
            supervisor_pidfd=supervisor_pidfd,
            control_fd=control_channel,
        )
        supervisor_pidfd = -1
        if mode == "ATFORK_REUSED_CLOSED_CONTROL":
            probe.run_nested_creator_pidfd_probe_v1(
                session, control_cgroup_fd=control_fd
            )
            closed_control_number = session.control_fd
            inherited_pidfd = session.supervisor_pidfd
            probe._TEST_FAULT_PHASE = "AFTER_INNER_CONTROL_CLOSE"  # noqa: SLF001
            try:
                probe.shutdown_nested_creator_supervisor_v1(session)
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                pass
            finally:
                probe._TEST_FAULT_PHASE = None  # noqa: SLF001
            replacement = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
            if replacement != closed_control_number:
                os.dup2(
                    replacement,
                    closed_control_number,
                    inheritable=False,
                )
                os.close(replacement)
                replacement = closed_control_number
            report_reader, report_writer = os.pipe2(os.O_CLOEXEC)
            fork_pid = os.fork()
            if fork_pid == 0:
                os.close(report_reader)
                try:
                    fcntl.fcntl(replacement, fcntl.F_GETFD)
                except OSError:
                    replacement_open = False
                else:
                    replacement_open = True
                try:
                    fcntl.fcntl(inherited_pidfd, fcntl.F_GETFD)
                except OSError:
                    inherited_pidfd_closed = True
                else:
                    inherited_pidfd_closed = False
                os.write(
                    report_writer,
                    json.dumps(
                        {
                            "replacement_open": replacement_open,
                            "inherited_pidfd_closed": inherited_pidfd_closed,
                            "session_state": session.state,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode(),
                )
                os.close(report_writer)
                os._exit(0)
            os.close(report_writer)
            child_report = json.loads(os.read(report_reader, 4096))
            os.close(report_reader)
            waited_pid, waited_status = os.waitpid(fork_pid, 0)
            reap = probe.finish_nested_creator_supervisor_reap_v1(session)
            os.close(replacement)
            session = None
            supervisor_pid = -1
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "child_report": child_report,
                        "fork_clean": waited_pid == fork_pid
                        and waited_status == 0,
                        "supervisor_reaped": reap[
                            "supervisor_reaped_exactly_once"
                        ],
                        "trusted_record_registry_count": len(
                            probe._LIVE_SESSIONS  # noqa: SLF001
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if mode == "ABORT_UNRELATED_CHILD":
            unrelated_pid = os.fork()
            if unrelated_pid == 0:
                signal.pause()
                os._exit(0)
            session.active_probe_pid = unrelated_pid
            rejected = False
            try:
                probe.abort_nested_creator_supervisor_session_v1(
                    session, control_cgroup_fd=control_fd
                )
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                rejected = True
            unrelated_still_live = Path(f"/proc/{unrelated_pid}").exists()
            session.active_probe_pid = -1
            session_still_live = probe.verify_nested_creator_live_session_v1(
                session
            )["live_session_verified"]
            os.kill(unrelated_pid, signal.SIGKILL)
            waited_unrelated, _ = os.waitpid(unrelated_pid, 0)
            abort_facts = probe.abort_nested_creator_supervisor_session_v1(
                session, control_cgroup_fd=control_fd
            )
            retry_facts = probe.abort_nested_creator_supervisor_session_v1(
                session, control_cgroup_fd=control_fd
            )
            session = None
            supervisor_pid = -1
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "unrelated_rejected": rejected,
                        "unrelated_still_live": unrelated_still_live,
                        "unrelated_reaped_by_test": waited_unrelated
                        == unrelated_pid,
                        "session_still_live": session_still_live,
                        "abort_idempotent": abort_facts == retry_facts,
                        "trusted_record_registry_count": len(
                            probe._LIVE_SESSIONS  # noqa: SLF001
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if mode == "ABORT_FAKE_CONTROL_MEMBER":
            fake_pid = os.fork()
            if fake_pid == 0:
                signal.pause()
                os._exit(0)
            _write_at(control_fd, "cgroup.procs", f"{fake_pid}\n".encode())
            session.active_probe_pid = fake_pid
            rejected = False
            try:
                probe.abort_nested_creator_supervisor_session_v1(
                    session, control_cgroup_fd=control_fd
                )
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                rejected = True
            fake_still_live = Path(f"/proc/{fake_pid}").exists()
            os.kill(fake_pid, signal.SIGKILL)
            waited_fake, _ = os.waitpid(fake_pid, 0)
            session.active_probe_pid = -1
            abort_facts = probe.abort_nested_creator_supervisor_session_v1(
                session, control_cgroup_fd=control_fd
            )
            session = None
            supervisor_pid = -1
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "fake_member_rejected": rejected,
                        "fake_member_still_live": fake_still_live,
                        "fake_member_reaped_by_test": waited_fake == fake_pid,
                        "abort_closed": abort_facts["state"]
                        == "ABORTED_CLOSED",
                        "trusted_record_registry_count": len(
                            probe._LIVE_SESSIONS  # noqa: SLF001
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if mode == "WRONG_CGROUP_BEFORE_COMMAND":
            first_error_type = ""
            try:
                probe.run_nested_creator_pidfd_probe_v1(
                    session, control_cgroup_fd=guardian_fd
                )
            except BaseException as error:
                first_error_type = type(error).__name__
            abort_facts = probe.abort_nested_creator_supervisor_session_v1(
                session, control_cgroup_fd=control_fd
            )
            session = None
            supervisor_pid = -1
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "first_error_type": first_error_type,
                        "abort_closed": abort_facts["state"]
                        == "ABORTED_CLOSED",
                        "trusted_record_registry_count": len(
                            probe._LIVE_SESSIONS  # noqa: SLF001
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if mode == "BEFORE_PARENT_RETURN":
            probe._TEST_FAULT_PHASE = mode  # noqa: SLF001
            first_error_type = ""
            try:
                probe.run_nested_creator_pidfd_probe_v1(
                    session, control_cgroup_fd=control_fd
                )
            except BaseException as error:
                first_error_type = type(error).__name__
            finally:
                probe._TEST_FAULT_PHASE = None  # noqa: SLF001
            abort_facts = probe.abort_nested_creator_supervisor_session_v1(
                session, control_cgroup_fd=control_fd
            )
            unknown_probe_pid = abort_facts["active_probe_pid"]
            reaped_pids = sorted(item["si_pid"] for item in abort_facts["reaped"])
            session_fds_closed = (
                session.control_fd == -1 and session.supervisor_pidfd == -1
            )
            session = None
            supervisor_pid = -1
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "first_error_type": first_error_type,
                        "unknown_probe_pid": unknown_probe_pid,
                        "reaped_pids": reaped_pids,
                        "session_fds_closed": session_fds_closed,
                        "cgroup_empty": not bool(
                            _read_at(control_fd, "cgroup.procs")
                        ),
                        "trusted_record_registry_count": len(
                            probe._LIVE_SESSIONS  # noqa: SLF001
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if mode.startswith("ABORT_AFTER_INNER_"):
            phase = mode.removeprefix("ABORT_")
            probe._TEST_FAULT_PHASE = phase  # noqa: SLF001
            first_error_type = ""
            try:
                probe.abort_nested_creator_supervisor_session_v1(
                    session, control_cgroup_fd=control_fd
                )
            except BaseException as error:
                first_error_type = type(error).__name__
            finally:
                probe._TEST_FAULT_PHASE = None  # noqa: SLF001
            partial_state = session.state
            partial_control_fd = session.control_fd
            partial_pidfd = session.supervisor_pidfd
            retry_facts = probe.abort_nested_creator_supervisor_session_v1(
                session, control_cgroup_fd=control_fd
            )
            second_facts = probe.abort_nested_creator_supervisor_session_v1(
                session, control_cgroup_fd=control_fd
            )
            session = None
            supervisor_pid = -1
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "first_error_type": first_error_type,
                        "partial_state": partial_state,
                        "partial_control_fd": partial_control_fd,
                        "partial_pidfd": partial_pidfd,
                        "retry_idempotent": retry_facts == second_facts,
                        "trusted_record_registry_count": len(
                            probe._LIVE_SESSIONS  # noqa: SLF001
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if mode in {
            "AFTER_INNER_CONTROL_CLOSE",
            "AFTER_INNER_PIDFD_CLOSE",
            "AFTER_INNER_PIDFD_CONSUME",
        }:
            probe.run_nested_creator_pidfd_probe_v1(
                session, control_cgroup_fd=control_fd
            )
            if mode == "AFTER_INNER_CONTROL_CLOSE":
                probe._TEST_FAULT_PHASE = mode  # noqa: SLF001
                first_error_type = ""
                try:
                    probe.shutdown_nested_creator_supervisor_v1(session)
                except BaseException as error:
                    first_error_type = type(error).__name__
                finally:
                    probe._TEST_FAULT_PHASE = None  # noqa: SLF001
                partial_state = session.state
                partial_fd = session.control_fd
                cached_first = session.shutdown_frame
                cached_retry = probe.shutdown_nested_creator_supervisor_v1(session)
                retry_idempotent = cached_first == cached_retry
                reap = probe.finish_nested_creator_supervisor_reap_v1(session)
            else:
                probe.shutdown_nested_creator_supervisor_v1(session)
                probe._TEST_FAULT_PHASE = mode  # noqa: SLF001
                first_error_type = ""
                try:
                    probe.finish_nested_creator_supervisor_reap_v1(session)
                except BaseException as error:
                    first_error_type = type(error).__name__
                finally:
                    probe._TEST_FAULT_PHASE = None  # noqa: SLF001
                partial_state = session.state
                partial_fd = session.supervisor_pidfd
                cached_first = probe.finish_nested_creator_supervisor_reap_v1(
                    session
                )
                cached_retry = probe.finish_nested_creator_supervisor_reap_v1(
                    session
                )
                retry_idempotent = cached_first == cached_retry
                reap = cached_first
            session = None
            supervisor_pid = -1
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "first_error_type": first_error_type,
                        "partial_state": partial_state,
                        "partial_fd": partial_fd,
                        "retry_idempotent": retry_idempotent,
                        "supervisor_reaped": reap[
                            "supervisor_reaped_exactly_once"
                        ],
                        "trusted_record_registry_count": len(
                            probe._LIVE_SESSIONS  # noqa: SLF001
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        verified_before_fork = probe.verify_nested_creator_live_session_v1(session)
        inherited_control_fd = session.control_fd
        inherited_pidfd = session.supervisor_pidfd
        report_reader, report_writer = os.pipe2(os.O_CLOEXEC)
        fork_pid = os.fork()
        if fork_pid == 0:
            os.close(report_reader)

            def descriptor_is_closed(descriptor: int) -> bool:
                try:
                    fcntl.fcntl(descriptor, fcntl.F_GETFD)
                except OSError:
                    return True
                return False

            verify_rejected = False
            try:
                probe.verify_nested_creator_live_session_v1(session)
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                verify_rejected = True
            try:
                os.waitpid(supervisor_pid, os.WNOHANG)
            except ChildProcessError:
                supervisor_not_child = True
            else:
                supervisor_not_child = False
            child_report = json.dumps(
                {
                    "control_fd_closed": descriptor_is_closed(
                        inherited_control_fd
                    ),
                    "pidfd_closed": descriptor_is_closed(inherited_pidfd),
                    "registry_count": len(probe._LIVE_SESSIONS),  # noqa: SLF001
                    "trusted_record_registry_count": len(
                        probe._LIVE_SESSIONS  # noqa: SLF001
                    ),
                    "session_state": session.state,
                    "session_control_fd": session.control_fd,
                    "session_pidfd": session.supervisor_pidfd,
                    "verify_rejected": verify_rejected,
                    "supervisor_not_child": supervisor_not_child,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            os.write(report_writer, child_report)
            os.close(report_writer)
            os._exit(0)
        os.close(report_writer)
        fork_report_raw = bytearray()
        while True:
            chunk = os.read(report_reader, 4096)
            if not chunk:
                break
            fork_report_raw.extend(chunk)
        os.close(report_reader)
        waited_pid, waited_status = os.waitpid(fork_pid, 0)
        if waited_pid != fork_pid or waited_status != 0:
            raise RuntimeError("atfork probe child did not exit cleanly")
        fork_report = json.loads(bytes(fork_report_raw))
        verified_after_fork = probe.verify_nested_creator_live_session_v1(session)
        live_verifier_mutation_rejected = False
        try:
            verified_after_fork["control_socket_fact"]["cloexec"] = False
        except TypeError:
            live_verifier_mutation_rejected = True

        control_substitution_rejected = False
        control_abort_substitution_rejected = False
        control_backup = fcntl.fcntl(
            session.control_fd, fcntl.F_DUPFD_CLOEXEC, 5
        )
        attack_parent, attack_peer = socket.socketpair(
            socket.AF_UNIX,
            socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0),
        )
        attack_parent.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        attack_peer.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
        try:
            os.dup2(attack_parent.fileno(), session.control_fd, inheritable=False)
            try:
                probe.verify_nested_creator_live_session_v1(session)
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                control_substitution_rejected = True
            try:
                probe.abort_nested_creator_supervisor_session_v1(
                    session, control_cgroup_fd=control_fd
                )
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                control_abort_substitution_rejected = True
        finally:
            os.dup2(control_backup, session.control_fd, inheritable=False)
            os.close(control_backup)
            attack_parent.close()
            attack_peer.close()

        pidfd_substitution_rejected = False
        pidfd_abort_substitution_rejected = False
        pidfd_backup = fcntl.fcntl(
            session.supervisor_pidfd, fcntl.F_DUPFD_CLOEXEC, 5
        )
        attack_pidfd = os.pidfd_open(os.getpid(), 0)
        try:
            os.dup2(attack_pidfd, session.supervisor_pidfd, inheritable=False)
            try:
                probe.verify_nested_creator_live_session_v1(session)
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                pidfd_substitution_rejected = True
            try:
                probe.abort_nested_creator_supervisor_session_v1(
                    session, control_cgroup_fd=control_fd
                )
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                pidfd_abort_substitution_rejected = True
        finally:
            os.dup2(pidfd_backup, session.supervisor_pidfd, inheritable=False)
            os.close(pidfd_backup)
            os.close(attack_pidfd)
        verified_after_substitution_attacks = (
            probe.verify_nested_creator_live_session_v1(session)
        )
        observed_facts = probe.run_nested_creator_pidfd_probe_observed_v2(
            session, control_cgroup_fd=control_fd
        )
        facts = observed_facts.raw_facts_v1
        probe.shutdown_nested_creator_supervisor_v1(session)

        victim_pid = os.fork()
        if victim_pid == 0:
            os._exit(0)
        victim_pidfd = os.pidfd_open(victim_pid, 0)
        os.waitid(
            getattr(os, "P_PIDFD", 3),
            victim_pidfd,
            os.WEXITED | os.WNOWAIT,
        )
        finish_pidfd_substitution_rejected = False
        victim_remained_waitable = False
        supervisor_pidfd_backup = fcntl.fcntl(
            session.supervisor_pidfd, fcntl.F_DUPFD_CLOEXEC, 5
        )
        try:
            os.dup2(victim_pidfd, session.supervisor_pidfd, inheritable=False)
            try:
                probe.finish_nested_creator_supervisor_reap_v1(session)
            except probe.ConstructionK7H1NestedCreatorProbeNativeV1Error:
                finish_pidfd_substitution_rejected = True
            victim_observation = os.waitid(
                getattr(os, "P_PIDFD", 3),
                victim_pidfd,
                os.WEXITED | os.WNOWAIT,
            )
            victim_remained_waitable = victim_observation.si_pid == victim_pid
        finally:
            os.dup2(
                supervisor_pidfd_backup,
                session.supervisor_pidfd,
                inheritable=False,
            )
            os.close(supervisor_pidfd_backup)
            os.waitid(getattr(os, "P_PIDFD", 3), victim_pidfd, os.WEXITED)
            os.close(victim_pidfd)
        reap = probe.finish_nested_creator_supervisor_reap_v1(session)
        session = None
        if Path(f"/proc/{supervisor_pid}").exists():
            raise RuntimeError("supervisor remained live after exact reap")
        supervisor_pid = -1
        if _read_at(control_fd, "cgroup.procs"):
            raise RuntimeError("control cgroup did not become empty")
        observed_document = observed_facts.to_document()
        ready_observation = observed_document["supervisor_ready_observation"]
        observations = observed_document["protocol_receive_observations"]
        all_observations = [ready_observation, *observations]

        def decoded_frame(observation: dict[str, object]) -> dict[str, object]:
            frame = probe.NativeProtocolFrameV1.from_bytes(
                bytes.fromhex(str(observation["raw_payload_hex"]))
            )
            return {
                "opcode": frame.opcode,
                "sequence": frame.sequence,
                "nonce_hex": frame.nonce.hex(),
                "pid": frame.pid,
                "status": frame.status,
                "flags": frame.flags,
                "fact_a": frame.fact_a,
            }

        def ancillary_matches(observation: dict[str, object]) -> bool:
            ancillary = observation["ancillary"]
            credentials = observation["credentials"]
            rights_count = observation["rights_count"]
            credential_rows = [
                row
                for row in ancillary
                if row["kind"] == socket.SCM_CREDENTIALS
            ]
            rights_rows = [
                row for row in ancillary if row["kind"] == socket.SCM_RIGHTS
            ]
            if len(credential_rows) != 1:
                return False
            raw_credentials = struct.unpack(
                "=iII", bytes.fromhex(credential_rows[0]["data_hex"])
            )
            if raw_credentials != (
                credentials["pid"],
                credentials["uid"],
                credentials["gid"],
            ):
                return False
            return (
                (len(rights_rows) == 1 and rights_rows[0]["byte_count"] == 4)
                if rights_count == 1
                else not rights_rows
            )
        mutation_rejections = 0
        for target, key, value in (
            (observed_facts.supervisor_ready_observation, "opcode", 0),
            (
                observed_facts.protocol_receive_observations[0][
                    "installed_pidfd_facts"
                ][0],
                "pid",
                0,
            ),
        ):
            try:
                target[key] = value
            except TypeError:
                mutation_rejections += 1
        output = {
            "probe_pid": facts.probe_pid,
            "supervisor_pid": facts.supervisor_pid,
            "guardian_waitid_errno": facts.guardian_waitid_errno,
            "live_population": facts.live_cgroup_snapshots[0]["pids_current"],
            "post_reap_population": facts.post_reap_cgroup_snapshots[0][
                "pids_current"
            ],
            "creator_reap_opcode": facts.creator_reap_frame.opcode,
            "supervisor_reap": reap["supervisor_reaped_exactly_once"],
            "two_birth_prefix_authority_present": facts.to_document()[
                "two_birth_prefix_authority_present"
            ],
            "ready_payload_hex_bytes": len(
                bytes.fromhex(
                    observed_document["supervisor_ready_observation"][
                        "raw_payload_hex"
                    ]
                )
            ),
            "ready_credential_pid": observed_document[
                "supervisor_ready_observation"
            ]["credentials"]["pid"],
            "receive_count": len(observations),
            "receive_opcodes": [item["opcode"] for item in observations],
            "receive_credential_pids": [
                item["credentials"]["pid"] for item in observations
            ],
            "receive_rights_counts": [item["rights_count"] for item in observations],
            "all_payloads_exact_frame_size": all(
                len(bytes.fromhex(item["raw_payload_hex"])) == role.FRAME_BYTES
                for item in observations
            ),
            "all_payload_hashes_match": all(
                hashlib.sha256(bytes.fromhex(item["raw_payload_hex"])).hexdigest()
                == item["payload_sha256"]
                for item in all_observations
            ),
            "all_decoded_frames_match": all(
                decoded_frame(item) == item["decoded_frame"]
                for item in all_observations
            ),
            "all_ancillary_semantics_match": all(
                ancillary_matches(item) for item in all_observations
            ),
            "installed_pidfd_pid": observations[0]["installed_pidfd_facts"][0][
                "pid"
            ],
            "installed_pidfd_cloexec": observations[0][
                "installed_pidfd_facts"
            ][0]["cloexec"],
            "installed_pidfd_descriptor_flags": observations[0][
                "installed_pidfd_facts"
            ][0]["descriptor_flags"],
            "mutation_rejections": mutation_rejections,
            "live_verifier_before_state": verified_before_fork["session_state"],
            "live_verifier_after_state": verified_after_fork["session_state"],
            "live_verifier_parent_pid": verified_after_fork["owner_pid"],
            "live_verifier_pidfd_pid": verified_after_fork[
                "supervisor_pidfd_fact"
            ]["pid"],
            "live_verifier_control_cloexec": verified_after_fork[
                "control_socket_fact"
            ]["cloexec"],
            "live_verifier_verified": verified_after_fork[
                "live_session_verified"
            ],
            "live_verifier_mutation_rejected": live_verifier_mutation_rejected,
            "control_substitution_rejected": control_substitution_rejected,
            "control_abort_substitution_rejected": (
                control_abort_substitution_rejected
            ),
            "pidfd_substitution_rejected": pidfd_substitution_rejected,
            "pidfd_abort_substitution_rejected": (
                pidfd_abort_substitution_rejected
            ),
            "finish_pidfd_substitution_rejected": (
                finish_pidfd_substitution_rejected
            ),
            "finish_attack_victim_remained_waitable": victim_remained_waitable,
            "frozen_control_device": verified_before_fork["control_socket_fact"][
                "device"
            ],
            "frozen_control_inode": verified_before_fork["control_socket_fact"][
                "inode"
            ],
            "frozen_pidfd_device": verified_before_fork[
                "supervisor_pidfd_fact"
            ]["device"],
            "frozen_pidfd_inode": verified_before_fork[
                "supervisor_pidfd_fact"
            ]["inode"],
            "restored_control_device": verified_after_substitution_attacks[
                "control_socket_fact"
            ]["device"],
            "restored_control_inode": verified_after_substitution_attacks[
                "control_socket_fact"
            ]["inode"],
            "restored_pidfd_device": verified_after_substitution_attacks[
                "supervisor_pidfd_fact"
            ]["device"],
            "restored_pidfd_inode": verified_after_substitution_attacks[
                "supervisor_pidfd_fact"
            ]["inode"],
            "frozen_control_peer_pid": verified_after_substitution_attacks[
                "control_socket_fact"
            ]["peer_credentials"]["pid"],
            "terminal_trusted_record_registry_count": len(
                probe._LIVE_SESSIONS  # noqa: SLF001
            ),
            "atfork_child": fork_report,
        }
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0
    finally:
        if session is not None:
            try:
                if session.control_fd >= 0:
                    os.close(session.control_fd)
                    session.control_fd = -1
            except OSError:
                pass
        if supervisor_pid > 0:
            try:
                os.kill(supervisor_pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                os.waitpid(supervisor_pid, 0)
            except OSError:
                pass
        if supervisor_pidfd >= 0:
            os.close(supervisor_pidfd)
        if executable_fd >= 0:
            os.close(executable_fd)
        if child_control is not None:
            child_control.close()
        if parent_control is not None:
            parent_control.close()
        try:
            os.rmdir("control", dir_fd=outer_fd)
        except OSError:
            pass
        try:
            os.rmdir(outer_name, dir_fd=delegated_fd)
        except OSError:
            pass
        try:
            os.rmdir(delegated_name, dir_fd=root_fd)
        except OSError:
            pass
        for descriptor in (control_fd, outer_fd, delegated_fd):
            if descriptor >= 0:
                os.close(descriptor)
        if moved:
            try:
                _write_at(root_fd, "cgroup.procs", f"{os.getpid()}\n".encode())
            except OSError:
                pass
        if guardian_fd >= 0:
            os.close(guardian_fd)
        try:
            os.rmdir(guardian_name, dir_fd=root_fd)
        except OSError:
            pass
        os.close(root_fd)


if __name__ == "__main__":
    raise SystemExit(main())
