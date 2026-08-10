from __future__ import annotations

from array import array
import errno
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import sys
import uuid

from acfqp import construction_k7_h1_nested_creator_broker_native_v2 as broker_v2
from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as role_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v2 as role_v2
from acfqp import construction_k7_h1_nested_creator_two_birth_runtime_v1 as runtime_v1


UCRED = struct.Struct("3i")


def _load_two_birth_helper() -> object:
    helper_path = Path(__file__).with_name(
        "_nested_creator_two_birth_runtime_subprocess.py"
    )
    spec = importlib.util.spec_from_file_location("_acfqp_v2_prefix_helper", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("V2 prefix compatibility helper could not be loaded")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def _receive_broker_frame(
    endpoint: socket.socket,
    *,
    expected_pid: int,
) -> broker_v2.BrokerRoleFrameV2:
    raw, ancillary, flags, address = endpoint.recvmsg(
        broker_v2.FRAME_BYTES + 1,
        socket.CMSG_SPACE(UCRED.size) + socket.CMSG_SPACE(array("i").itemsize),
        getattr(socket, "MSG_CMSG_CLOEXEC", 0),
    )
    credentials: list[tuple[int, int, int]] = []
    rights: list[int] = []
    try:
        for level, kind, data in ancillary:
            if level != socket.SOL_SOCKET:
                raise RuntimeError("BROKER branch returned an unknown cmsg level")
            if kind == socket.SCM_CREDENTIALS:
                if credentials or len(data) != UCRED.size:
                    raise RuntimeError("BROKER branch credentials grammar changed")
                credentials.append(UCRED.unpack(data))
            elif kind == socket.SCM_RIGHTS:
                installed = array("i")
                installed.frombytes(data)
                rights.extend(installed)
            else:
                raise RuntimeError("BROKER branch returned an unknown cmsg type")
        address_is_connected = address in {None, "", b""}
        address_is_linux_autobind = (
            type(address) is bytes
            and len(address) == 6
            and address[:1] == b"\x00"
            and all(value in b"0123456789abcdef" for value in address[1:])
        )
        if (
            len(raw) != broker_v2.FRAME_BYTES
            or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
            or not (address_is_connected or address_is_linux_autobind)
            or credentials != [(expected_pid, os.getuid(), os.getgid())]
            or rights
        ):
            raise RuntimeError(
                "BROKER branch frame transport changed: "
                f"bytes={len(raw)},flags={flags:#x},address={address!r},"
                f"credentials={credentials!r},expected_pid={expected_pid},"
                f"rights={rights!r},raw={raw.hex()}"
            )
        return broker_v2.BrokerRoleFrameV2.from_bytes(raw)
    finally:
        for descriptor in rights:
            os.close(descriptor)


def _send_broker_frame(
    endpoint: socket.socket,
    frame: broker_v2.BrokerRoleFrameV2,
) -> None:
    sent = endpoint.send(frame.to_bytes(), getattr(socket, "MSG_NOSIGNAL", 0))
    if sent != broker_v2.FRAME_BYTES:
        raise RuntimeError("BROKER branch frame send was short")


def _read_parent_pid(pid: int) -> int:
    tail = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").rsplit(") ", 1)[1]
    return int(tail.split()[1])


def _guardian_waitid_echild(pidfd: int) -> int:
    try:
        os.waitid(
            getattr(os, "P_PIDFD", 3),
            pidfd,
            os.WEXITED | os.WNOHANG,
        )
    except ChildProcessError:
        return errno.ECHILD
    except OSError as error:
        if error.errno == errno.ECHILD:
            return error.errno
        raise
    raise RuntimeError("external guardian unexpectedly acquired BROKER wait authority")


def _run_broker_activation(
    helper: object,
    *,
    bad_ack: bool = False,
    unsealed_exec: bool = False,
) -> int:
    scope = helper._current_scope_path()  # type: ignore[attr-defined]
    root_fd = os.open(
        scope, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    suffix = f"{os.getpid()}-{uuid.uuid4().hex}"
    guardian_name = f"acfqp-v2-guardian-{suffix}"
    delegated_name = f"acfqp-v2-delegated-{suffix}"
    outer_name = f"acfqp-v2-outer-{suffix}"
    guardian_fd = delegated_fd = outer_fd = control_fd = cgroup_grant_fd = -1
    pid_cell_fd = broker_image_fd = broker_pidfd = -1
    guardian_channel: socket.socket | None = None
    child_channel: socket.socket | None = None
    handle = None
    moved = False
    baseline_fd_count = -1
    baseline_subreaper = False
    try:
        os.mkdir(guardian_name, mode=0o700, dir_fd=root_fd)
        guardian_fd = helper._open_dir_at(root_fd, guardian_name)  # type: ignore[attr-defined]
        helper._write_at(  # type: ignore[attr-defined]
            guardian_fd, "cgroup.procs", f"{os.getpid()}\n".encode()
        )
        moved = True
        helper._write_at(  # type: ignore[attr-defined]
            root_fd, "cgroup.subtree_control", b"+memory +pids\n"
        )
        os.mkdir(delegated_name, mode=0o700, dir_fd=root_fd)
        delegated_fd = helper._open_dir_at(root_fd, delegated_name)  # type: ignore[attr-defined]
        helper._write_at(  # type: ignore[attr-defined]
            delegated_fd, "cgroup.subtree_control", b"+memory +pids\n"
        )
        os.mkdir(outer_name, mode=0o700, dir_fd=delegated_fd)
        outer_fd = helper._open_dir_at(delegated_fd, outer_name)  # type: ignore[attr-defined]
        helper._write_at(outer_fd, "memory.max", b"67108864\n")  # type: ignore[attr-defined]
        helper._write_at(outer_fd, "pids.max", b"3\n")  # type: ignore[attr-defined]
        helper._write_at(outer_fd, "cgroup.max.depth", b"1\n")  # type: ignore[attr-defined]
        helper._write_at(outer_fd, "cgroup.max.descendants", b"1\n")  # type: ignore[attr-defined]
        helper._write_at(  # type: ignore[attr-defined]
            outer_fd, "cgroup.subtree_control", b"+memory +pids\n"
        )
        os.mkdir("control", mode=0o700, dir_fd=outer_fd)
        control_fd = helper._open_dir_at(outer_fd, "control")  # type: ignore[attr-defined]
        helper._write_at(control_fd, "pids.max", b"2\n")  # type: ignore[attr-defined]

        baseline_fd_count = len(os.listdir("/proc/self/fd"))
        baseline_subreaper = runtime_v1._get_subreaper()  # noqa: SLF001
        handle = runtime_v1.begin_bounded_nested_creator_two_birth_live_prefix_v1(
            control_cgroup_fd=control_fd
        )
        record = runtime_v1._LIVE_PREFIXES[id(handle)]  # noqa: SLF001
        session_record = probe_v1._LIVE_SESSIONS.record(  # noqa: SLF001
            record.nested_session
        )
        if session_record is None:
            raise RuntimeError("V2 live SUPERVISOR session disappeared")
        supervisor_control_fd = session_record.control_fd
        supervisor_pid = record.supervisor_pid
        supervisor_only_before = (
            probe_v1.observe_nested_creator_control_population_v1(
                control_fd,
                expected_pids=(supervisor_pid,),
                sequence=2099,
            )
        )

        cgroup_grant_fd = os.open(
            f"/proc/self/fd/{control_fd}", os.O_PATH | os.O_CLOEXEC
        )
        pid_cell_fd = os.memfd_create(
            "acfqp-v2-broker-pid-cell",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        os.ftruncate(pid_cell_fd, role_v2.PID_CELL_BYTES)
        if unsealed_exec:
            broker_image_fd = os.memfd_create(
                "acfqp-v2-unsealed-broker-image",
                os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
            )
            offset = 0
            while offset < len(broker_v2.ROLE_ELF_BYTES):
                written = os.write(
                    broker_image_fd,
                    broker_v2.ROLE_ELF_BYTES[offset:],
                )
                if written <= 0:
                    raise RuntimeError("unsealed BROKER image write was short")
                offset += written
            os.lseek(broker_image_fd, 0, os.SEEK_SET)
        else:
            broker_image_fd = broker_v2.create_sealed_nested_creator_broker_memfd_v2()
        guardian_channel, child_channel = socket.socketpair(
            socket.AF_UNIX,
            socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC,
        )
        guardian_channel.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        nonce = os.getrandom(16)
        command = probe_v1.NativeProtocolFrameV1(
            role_v2.OPCODES["BROKER_COMMAND"], 2, nonce, supervisor_pid
        )
        probe_v1._send_frame(  # noqa: SLF001
            supervisor_control_fd,
            command,
            rights=(
                cgroup_grant_fd,
                pid_cell_fd,
                broker_image_fd,
                child_channel.fileno(),
            ),
        )
        child_channel.close()
        child_channel = None
        if unsealed_exec:
            failure, failure_rights = probe_v1._recv_frame(  # noqa: SLF001
                supervisor_control_fd,
                expected_credentials=(
                    supervisor_pid,
                    os.getuid(),
                    os.getgid(),
                ),
                expected_rights=0,
            )
            expected_failure = probe_v1.NativeProtocolFrameV1(
                role_v2.OPCODES["PROTOCOL_FAILURE"],
                2,
                nonce,
                supervisor_pid,
                status=-47,
            )
            untouched_pid_cell = os.pread(
                pid_cell_fd, role_v2.PID_CELL_BYTES + 1, 0
            )
            if (
                failure_rights
                or failure != expected_failure
                or untouched_pid_cell != bytes(role_v2.PID_CELL_BYTES)
            ):
                raise RuntimeError("V2 unsealed executable rejection changed")
            abort_facts = (
                runtime_v1.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                    handle
                )
            )
            handle = None
            final_empty = probe_v1.observe_nested_creator_control_population_v1(
                control_fd, expected_pids=(), sequence=2104
            )
            for descriptor_name in (
                "cgroup_grant_fd",
                "pid_cell_fd",
                "broker_image_fd",
            ):
                descriptor = locals()[descriptor_name]
                os.close(descriptor)
                if descriptor_name == "cgroup_grant_fd":
                    cgroup_grant_fd = -1
                elif descriptor_name == "pid_cell_fd":
                    pid_cell_fd = -1
                else:
                    broker_image_fd = -1
            guardian_channel.close()
            guardian_channel = None
            print(
                json.dumps(
                    {
                        "failure_status": failure.status,
                        "failure_sequence": failure.sequence,
                        "pre_command_population": supervisor_only_before[
                            "pids_current"
                        ],
                        "pid_cell_untouched": True,
                        "final_population": final_empty["pids_current"],
                        "abort_state": abort_facts["state"],
                        "fd_count_restored": len(os.listdir("/proc/self/fd"))
                        == baseline_fd_count,
                        "subreaper_restored": runtime_v1._get_subreaper()  # noqa: SLF001
                        == baseline_subreaper,
                        "direct_children": Path(
                            f"/proc/self/task/{os.getpid()}/children"
                        ).read_text(encoding="ascii").strip(),
                        "descriptor_rejected_before_clone": True,
                        "three_birth_prefix_authority_present": False,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        parent_return, rights = probe_v1._recv_frame(  # noqa: SLF001
            supervisor_control_fd,
            expected_credentials=(supervisor_pid, os.getuid(), os.getgid()),
            expected_rights=1,
        )
        if len(rights) != 1:
            raise RuntimeError("V2 BROKER parent return lost its pidfd")
        broker_pidfd = rights.pop()
        broker_pid = parent_return.pid
        pidfd_fact = probe_v1._pidfd_fact(broker_pidfd)  # noqa: SLF001
        guardian_echild_while_live = _guardian_waitid_echild(broker_pidfd)
        fcntl.fcntl(pid_cell_fd, fcntl.F_ADD_SEALS, role_v2.REQUIRED_SEALS)
        pid_cell = os.pread(pid_cell_fd, role_v2.PID_CELL_BYTES + 1, 0)
        broker_observed_parent_pid = _read_parent_pid(broker_pid)
        if (
            parent_return
            != probe_v1.NativeProtocolFrameV1(
                role_v2.OPCODES["BROKER_PARENT_RETURN"],
                2,
                nonce,
                broker_pid,
                0,
                0x1F,
                supervisor_pid,
            )
            or pidfd_fact["pid"] != broker_pid
            or len(pid_cell) != role_v2.PID_CELL_BYTES
            or int.from_bytes(pid_cell[:4], "little", signed=True) != broker_pid
            or any(pid_cell[4:])
            or broker_observed_parent_pid != supervisor_pid
        ):
            raise RuntimeError("V2 BROKER parent/PID-cell/pidfd join changed")
        live_two = probe_v1.observe_nested_creator_control_population_v1(
            control_fd,
            expected_pids=(supervisor_pid, broker_pid),
            sequence=2100,
        )

        ack = probe_v1.NativeProtocolFrameV1(
            role_v2.OPCODES["BROKER_ACK"],
            2,
            nonce,
            broker_pid,
            status=1 if bad_ack else 0,
        )
        probe_v1._send_frame(supervisor_control_fd, ack)  # noqa: SLF001
        if bad_ack:
            failure, failure_rights = probe_v1._recv_frame(  # noqa: SLF001
                supervisor_control_fd,
                expected_credentials=(
                    supervisor_pid,
                    os.getuid(),
                    os.getgid(),
                ),
                expected_rights=0,
            )
            expected_failure = probe_v1.NativeProtocolFrameV1(
                role_v2.OPCODES["PROTOCOL_FAILURE"],
                2,
                nonce,
                supervisor_pid,
                status=-33,
            )
            if failure_rights or failure != expected_failure:
                raise RuntimeError("V2 BROKER bad-ACK failure frame changed")
            guardian_echild_after_failure = _guardian_waitid_echild(broker_pidfd)
            os.close(broker_pidfd)
            broker_pidfd = -1
            abort_facts = (
                runtime_v1.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                    handle
                )
            )
            handle = None
            final_empty = probe_v1.observe_nested_creator_control_population_v1(
                control_fd, expected_pids=(), sequence=2103
            )
            for descriptor_name in (
                "cgroup_grant_fd",
                "pid_cell_fd",
                "broker_image_fd",
            ):
                descriptor = locals()[descriptor_name]
                os.close(descriptor)
                if descriptor_name == "cgroup_grant_fd":
                    cgroup_grant_fd = -1
                elif descriptor_name == "pid_cell_fd":
                    pid_cell_fd = -1
                else:
                    broker_image_fd = -1
            guardian_channel.close()
            guardian_channel = None
            print(
                json.dumps(
                    {
                        "failure_status": failure.status,
                        "failure_sequence": failure.sequence,
                        "broker_pidfd_pid": pidfd_fact["pid"],
                        "broker_pid_cell_value": int.from_bytes(
                            pid_cell[:4], "little", signed=True
                        ),
                        "pre_failure_population": live_two["pids_current"],
                        "guardian_echild_while_live": guardian_echild_while_live,
                        "guardian_echild_after_failure": (
                            guardian_echild_after_failure
                        ),
                        "final_population": final_empty["pids_current"],
                        "abort_state": abort_facts["state"],
                        "fd_count_restored": len(os.listdir("/proc/self/fd"))
                        == baseline_fd_count,
                        "subreaper_restored": runtime_v1._get_subreaper()  # noqa: SLF001
                        == baseline_subreaper,
                        "direct_children": Path(
                            f"/proc/self/task/{os.getpid()}/children"
                        ).read_text(encoding="ascii").strip(),
                        "clone_failure_cleanup_observed": True,
                        "three_birth_prefix_authority_present": False,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        ack_echo, ack_echo_rights = probe_v1._recv_frame(  # noqa: SLF001
            supervisor_control_fd,
            expected_credentials=(supervisor_pid, os.getuid(), os.getgid()),
            expected_rights=0,
        )
        if ack_echo_rights or ack_echo != probe_v1.NativeProtocolFrameV1(
            role_v2.OPCODES["BROKER_ACK_ECHO"], 2, nonce, broker_pid
        ):
            raise RuntimeError("V2 BROKER ACK echo changed")

        ready = _receive_broker_frame(guardian_channel, expected_pid=broker_pid)
        if ready != broker_v2.BrokerRoleFrameV2(
            broker_v2.OPCODES["BROKER_READY"],
            0,
            bytes(16),
            broker_pid,
            fact_a=supervisor_pid,
        ):
            raise RuntimeError("V2 BROKER READY parent fact changed")
        broker_nonce = os.getrandom(16)
        _send_broker_frame(
            guardian_channel,
            broker_v2.BrokerRoleFrameV2(
                broker_v2.OPCODES["BROKER_GO"], 1, broker_nonce, broker_pid
            ),
        )
        go_echo = _receive_broker_frame(guardian_channel, expected_pid=broker_pid)
        if go_echo != broker_v2.BrokerRoleFrameV2(
            broker_v2.OPCODES["BROKER_GO_ECHO"],
            1,
            broker_nonce,
            broker_pid,
        ):
            raise RuntimeError("V2 BROKER GO echo changed")
        shutdown_nonce = os.getrandom(16)
        _send_broker_frame(
            guardian_channel,
            broker_v2.BrokerRoleFrameV2(
                broker_v2.OPCODES["BROKER_SHUTDOWN"],
                4,
                shutdown_nonce,
                broker_pid,
            ),
        )
        broker_bye = _receive_broker_frame(guardian_channel, expected_pid=broker_pid)
        if broker_bye != broker_v2.BrokerRoleFrameV2(
            broker_v2.OPCODES["BROKER_BYE"],
            4,
            shutdown_nonce,
            broker_pid,
        ):
            raise RuntimeError("V2 BROKER BYE changed")
        broker_reap, broker_reap_rights = probe_v1._recv_frame(  # noqa: SLF001
            supervisor_control_fd,
            expected_credentials=(supervisor_pid, os.getuid(), os.getgid()),
            expected_rights=0,
        )
        if broker_reap_rights or broker_reap != probe_v1.NativeProtocolFrameV1(
            role_v2.OPCODES["BROKER_REAP"],
            2,
            nonce,
            broker_pid,
            0,
            1,
            10,
        ):
            raise RuntimeError("V2 BROKER WNOWAIT/consume/ECHILD report changed")
        guardian_echild_after_reap = _guardian_waitid_echild(broker_pidfd)
        supervisor_only = probe_v1.observe_nested_creator_control_population_v1(
            control_fd,
            expected_pids=(supervisor_pid,),
            sequence=2101,
        )
        os.close(broker_pidfd)
        broker_pidfd = -1
        abort_facts = runtime_v1.abort_bounded_nested_creator_two_birth_live_prefix_v1(
            handle
        )
        handle = None
        final_empty = probe_v1.observe_nested_creator_control_population_v1(
            control_fd, expected_pids=(), sequence=2102
        )
        for descriptor_name in (
            "cgroup_grant_fd",
            "pid_cell_fd",
            "broker_image_fd",
        ):
            descriptor = locals()[descriptor_name]
            os.close(descriptor)
            if descriptor_name == "cgroup_grant_fd":
                cgroup_grant_fd = -1
            elif descriptor_name == "pid_cell_fd":
                pid_cell_fd = -1
            else:
                broker_image_fd = -1
        guardian_channel.close()
        guardian_channel = None
        print(
            json.dumps(
                {
                    "birth_order": ["SUPERVISOR", "PIDFD_PROBE", "BROKER"],
                    "creator_by_slot": {
                        "SUPERVISOR": "EXTERNAL_GUARDIAN",
                        "PIDFD_PROBE": "SUPERVISOR",
                        "BROKER": "SUPERVISOR",
                    },
                    "supervisor_pid": supervisor_pid,
                    "broker_pid": broker_pid,
                    "broker_observed_parent_pid": broker_observed_parent_pid,
                    "broker_pidfd_pid": pidfd_fact["pid"],
                    "broker_pid_cell_value": int.from_bytes(
                        pid_cell[:4], "little", signed=True
                    ),
                    "maximum_observed_control_population": live_two[
                        "pids_current"
                    ],
                    "pre_broker_population": supervisor_only_before[
                        "pids_current"
                    ],
                    "post_broker_population": supervisor_only["pids_current"],
                    "final_population": final_empty["pids_current"],
                    "broker_reap_status": broker_reap.status,
                    "broker_reap_code": broker_reap.flags,
                    "broker_reap_echild": broker_reap.fact_a,
                    "guardian_echild_while_live": guardian_echild_while_live,
                    "guardian_echild_after_reap": guardian_echild_after_reap,
                    "ack_echo_before_broker_shutdown": True,
                    "abort_state": abort_facts["state"],
                    "fd_count_restored": len(os.listdir("/proc/self/fd"))
                    == baseline_fd_count,
                    "subreaper_restored": runtime_v1._get_subreaper()  # noqa: SLF001
                    == baseline_subreaper,
                    "direct_children": Path(
                        f"/proc/self/task/{os.getpid()}/children"
                    ).read_text(encoding="ascii").strip(),
                    "raw_broker_branch_observed": True,
                    "three_birth_prefix_authority_present": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    finally:
        if broker_pidfd >= 0:
            os.close(broker_pidfd)
        if handle is not None:
            try:
                runtime_v1.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                    handle
                )
            except Exception:
                pass
        if child_channel is not None:
            child_channel.close()
        if guardian_channel is not None:
            guardian_channel.close()
        for descriptor in (broker_image_fd, pid_cell_fd, cgroup_grant_fd):
            if descriptor >= 0:
                os.close(descriptor)
        if control_fd >= 0:
            helper._write_at(control_fd, "cgroup.kill", b"1\n")  # type: ignore[attr-defined]
            helper._wait_empty(control_fd)  # type: ignore[attr-defined]
            os.rmdir("control", dir_fd=outer_fd)
        if outer_fd >= 0:
            os.close(outer_fd)
            outer_fd = -1
            os.rmdir(outer_name, dir_fd=delegated_fd)
        if delegated_fd >= 0:
            os.close(delegated_fd)
            delegated_fd = -1
            os.rmdir(delegated_name, dir_fd=root_fd)
        if moved:
            helper._write_at(  # type: ignore[attr-defined]
                root_fd, "cgroup.subtree_control", b"-memory -pids\n"
            )
            helper._write_at(  # type: ignore[attr-defined]
                root_fd, "cgroup.procs", f"{os.getpid()}\n".encode()
            )
        if guardian_fd >= 0:
            helper._wait_empty(guardian_fd)  # type: ignore[attr-defined]
            os.close(guardian_fd)
            os.rmdir(guardian_name, dir_fd=root_fd)
        if control_fd >= 0:
            os.close(control_fd)
        os.close(root_fd)


def main() -> int:
    """Run the established raw two-birth harness with the exact V2 role ELF.

    This compatibility harness deliberately exercises only the direct-shutdown
    branch.  It neither activates the BROKER command nor mints a V2 runtime
    artifact or authority.
    """

    role_v1.ROLE_ELF_BYTES = role_v2.ROLE_ELF_BYTES
    role_v1.ELF_BYTE_COUNT = role_v2.ELF_BYTE_COUNT
    role_v1.ELF_SHA256 = role_v2.ELF_SHA256
    role_v1.OPCODES = role_v2.OPCODES
    role_v1.verify_nested_creator_supervisor_native_image_v1 = (
        role_v2.verify_nested_creator_supervisor_native_image_v2
    )
    role_v1.create_sealed_nested_creator_supervisor_memfd_v1 = (
        role_v2.create_sealed_nested_creator_supervisor_memfd_v2
    )

    helper = _load_two_birth_helper()
    if len(sys.argv) > 1 and sys.argv[1] in {
        "BROKER",
        "BROKER_BAD_ACK",
        "BROKER_UNSEALED_EXEC",
    }:
        return _run_broker_activation(
            helper,
            bad_ack=sys.argv[1] == "BROKER_BAD_ACK",
            unsealed_exec=sys.argv[1] == "BROKER_UNSEALED_EXEC",
        )
    helper_path = Path(__file__).with_name(
        "_nested_creator_two_birth_runtime_subprocess.py"
    )
    sys.argv = [str(helper_path), "SUCCESS"]
    return int(helper.main())  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
