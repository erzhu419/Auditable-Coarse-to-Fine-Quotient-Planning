from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import uuid

from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe
from acfqp import construction_k7_h1_nested_creator_two_birth_runtime_v1 as runtime


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


def _read_at(directory_fd: int, name: str) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        return os.read(descriptor, 65537)
    finally:
        os.close(descriptor)


def _wait_empty(directory_fd: int) -> None:
    deadline = time.monotonic() + 10.0
    while _read_at(directory_fd, "cgroup.procs"):
        if time.monotonic() >= deadline:
            raise RuntimeError("test cgroup did not empty")
        time.sleep(0.005)


def _current_scope_path() -> Path:
    relative = next(
        line.removeprefix("0::").strip()
        for line in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        if line.startswith("0::")
    )
    return Path("/sys/fs/cgroup") / relative.lstrip("/")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "SUCCESS"
    if mode not in {"SUCCESS", "NATIVE_RETURN_TAKEOVER", "PROBE_PARENT_RETURN"}:
        raise RuntimeError(f"unknown two-birth test mode: {mode}")
    scope = _current_scope_path()
    root_fd = os.open(
        scope, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    suffix = f"{os.getpid()}-{uuid.uuid4().hex}"
    guardian_name = f"acfqp-guardian-{suffix}"
    delegated_name = f"acfqp-delegated-{suffix}"
    outer_name = f"acfqp-outer-{suffix}"
    guardian_fd = delegated_fd = outer_fd = control_fd = -1
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

        baseline_fd_count = len(os.listdir("/proc/self/fd"))
        baseline_subreaper = runtime._get_subreaper()  # noqa: SLF001
        if mode == "NATIVE_RETURN_TAKEOVER":
            runtime._TEST_FAULT_PHASE = mode  # noqa: SLF001
        elif mode == "PROBE_PARENT_RETURN":
            probe._TEST_FAULT_PHASE = mode  # noqa: SLF001
        try:
            result = runtime.run_bounded_nested_creator_two_birth_runtime_v1(
                control_cgroup_fd=control_fd
            )
        except Exception as error:
            if mode == "SUCCESS":
                raise
            empty = probe.observe_nested_creator_control_population_v1(
                control_fd, expected_pids=(), sequence=10001
            )
            children = Path(
                f"/proc/self/task/{os.getpid()}/children"
            ).read_text(encoding="ascii").strip()
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "error_type": type(error).__name__,
                        "final_population": empty["pids_current"],
                        "fd_count_restored": len(os.listdir("/proc/self/fd"))
                        == baseline_fd_count,
                        "subreaper_restored": runtime._get_subreaper()  # noqa: SLF001
                        == baseline_subreaper,
                        "direct_children": children,
                        "live_session_count": len(probe._LIVE_SESSIONS),  # noqa: SLF001
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if mode != "SUCCESS":
            raise RuntimeError(f"fault mode did not fail: {mode}")
        document = result.to_document()
        mutation_rejections = 0
        for target, key, value in (
            (result.outer_parent_edge, "status_bits", 0),
            (result.outer_live_snapshots[0]["events"], "populated", 0),
            (result.probe_facts.pidfd_fact, "pid", 0),
        ):
            try:
                target[key] = value
            except TypeError:
                mutation_rejections += 1
        json.loads(json.dumps(document, sort_keys=True, separators=(",", ":")))
        print(
            json.dumps(
                {
                    "birth_order": document["birth_order"],
                    "creator_by_slot": document["creator_by_slot"],
                    "maximum_observed_control_population": document[
                        "maximum_observed_control_population"
                    ],
                    "supervisor_pid": document["supervisor_pid"],
                    "probe_pid": document["probe_pid"],
                    "final_population": document["final_empty_snapshots"][0][
                        "pids_current"
                    ],
                    "memory_peak_read_count": document["memory_peak_read_count"],
                    "outer_gate_fact_count": len(document["outer_gate_facts"]),
                    "outer_nonce_hex": document["outer_nonce_hex"],
                    "outer_seal_set": document["outer_seal_set"],
                    "outer_pidfd_pid": document["outer_pidfd_fact"]["pid"],
                    "outer_role_witness_same_identity": document[
                        "outer_role_source_fact"
                    ]["source_witness_same_identity"],
                    "mutation_rejections": mutation_rejections,
                    "fd_count_restored": len(os.listdir("/proc/self/fd"))
                    == baseline_fd_count,
                    "subreaper_restored": runtime._get_subreaper()  # noqa: SLF001
                    == baseline_subreaper,
                    "direct_children": Path(
                        f"/proc/self/task/{os.getpid()}/children"
                    ).read_text(encoding="ascii").strip(),
                    "live_session_count": len(probe._LIVE_SESSIONS),  # noqa: SLF001
                    "target_two_birth_creator_chain_observed": document[
                        "target_two_birth_creator_chain_observed"
                    ],
                    "exact_two_birth_os_topology_observed": document[
                        "exact_two_birth_os_topology_observed"
                    ],
                    "exclusive_two_birth_topology_authority_present": document[
                        "exclusive_two_birth_topology_authority_present"
                    ],
                    "two_birth_prefix_authority_present": document[
                        "two_birth_prefix_authority_present"
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    finally:
        if control_fd >= 0:
            _write_at(control_fd, "cgroup.kill", b"1\n")
            _wait_empty(control_fd)
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
            _write_at(root_fd, "cgroup.subtree_control", b"-memory -pids\n")
            _write_at(root_fd, "cgroup.procs", f"{os.getpid()}\n".encode())
            moved = False
        if guardian_fd >= 0:
            _wait_empty(guardian_fd)
            os.close(guardian_fd)
            guardian_fd = -1
            os.rmdir(guardian_name, dir_fd=root_fd)
        if control_fd >= 0:
            os.close(control_fd)
        os.close(root_fd)


if __name__ == "__main__":
    raise SystemExit(main())
