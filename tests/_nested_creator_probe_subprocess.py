from __future__ import annotations

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
        session = probe.begin_nested_creator_supervisor_session_v1(
            supervisor_pid=supervisor_pid,
            supervisor_pidfd=supervisor_pidfd,
            control_fd=control_channel,
        )
        supervisor_pidfd = -1
        observed_facts = probe.run_nested_creator_pidfd_probe_observed_v2(
            session, control_cgroup_fd=control_fd
        )
        facts = observed_facts.raw_facts_v1
        probe.shutdown_nested_creator_supervisor_v1(session)
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
