from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import uuid

from acfqp import construction_k7_h1_two_birth_portable_checkpoint_v1 as producer
from acfqp import construction_k7_h1_domain_registry_extension_v18 as domains_v18
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


def _direct_children() -> str:
    return Path(
        f"/proc/self/task/{threading.get_native_id()}/children"
    ).read_text(encoding="ascii").strip()


def _read_journal(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(item.read_text(encoding="utf-8"))
        for item in sorted(path.iterdir())
    ]


def _run(control_fd: int, mode: str, journal: Path) -> dict[str, object]:
    if mode == "FORGED_SNAPSHOT_RESIGN":
        source_lease, source = producer._freeze_source_closure()  # noqa: SLF001
        handle = runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
            control_cgroup_fd=control_fd
        )
        try:
            snapshot = runtime.snapshot_bounded_nested_creator_two_birth_live_prefix_v1(
                handle
            )
            control_identity = producer._fd_identity(control_fd)  # noqa: SLF001
            credential = producer._FROZEN_CREDENTIAL_BUNDLE(  # noqa: SLF001
                source_closure=source,
                live_observation=snapshot,
                control_identity=control_identity,
            )
            forged_snapshot = producer._thaw_json(snapshot)  # noqa: SLF001
            forged_snapshot["outer_parent_edge"]["clone_result"] = (
                forged_snapshot["probe_pid"]
            )
            try:
                producer._FROZEN_CREDENTIAL_BUNDLE(  # noqa: SLF001
                    source_closure=source,
                    live_observation=forged_snapshot,
                    control_identity=control_identity,
                )
                forged_snapshot_error = ""
            except BaseException as error:
                forged_snapshot_error = str(error)

            forged_credential = producer._thaw_json(credential)  # noqa: SLF001
            forged_credential["probe_pid"] = forged_credential["supervisor_pid"]
            forged_credential.pop("nested_probe_credential_observation_bundle_id")
            forged_credential["nested_probe_credential_observation_bundle_id"] = (
                domains_v18.extension_content_id_v18(
                    domains_v18.CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN,
                    forged_credential,
                )
            )
            try:
                producer._FROZEN_ROOT_CHECKPOINT(  # noqa: SLF001
                    source_closure=source,
                    credential_bundle=forged_credential,
                    live_observation=snapshot,
                    control_identity=control_identity,
                )
                resigned_credential_error = ""
            except BaseException as error:
                resigned_credential_error = str(error)
            return {
                "forged_snapshot_error": forged_snapshot_error,
                "resigned_credential_error": resigned_credential_error,
                "resigned_credential_id_present": len(
                    forged_credential[
                        "nested_probe_credential_observation_bundle_id"
                    ]
                )
                == 64,
            }
        finally:
            runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(handle)
            source_lease.close()
    if mode != "SUCCESS":
        producer._TEST_FAULT_PHASE = mode  # noqa: SLF001
    try:
        graph = producer.run_two_birth_portable_checkpoint_producer_v1(
            control_cgroup_fd=control_fd,
            journal_directory=journal,
        )
    except producer.ConstructionK7H1TwoBirthPortableCheckpointV1Error as error:
        rows = _read_journal(journal)
        closure = rows[-1]
        return {
            "mode": mode,
            "success": False,
            "error_type": type(error).__name__,
            "failure_closure_returned": error.failure_closure is not None,
            "record_count": len(rows),
            "record_schemas": [row["schema"] for row in rows],
            "failure_closure": closure,
            "final_population": len(_read_at(control_fd, "cgroup.procs").split()),
            "direct_children": _direct_children(),
        }
    finally:
        producer._TEST_FAULT_PHASE = None  # noqa: SLF001

    document = graph.to_document()
    rows = _read_journal(journal)
    checkpoint = document["live_checkpoint"]
    return {
        "mode": mode,
        "success": True,
        "record_count": len(rows),
        "record_schemas": [row["schema"] for row in rows],
        "record_sequences": [row["journal_sequence"] for row in rows],
        "record_ids": [
            graph.journal_records[index]["record_id"]
            for index in range(len(graph.journal_records))
        ],
        "source_entry_count": document["source_closure"]["source_entry_count"],
        "issuance_state": checkpoint["issuance_state"],
        "runtime_state_at_root_commit": checkpoint[
            "runtime_state_at_root_commit"
        ],
        "expected_success_return_runtime_state": checkpoint[
            "expected_success_return_runtime_state"
        ],
        "producer_return_runtime_state": document[
            "producer_return_runtime_state"
        ],
        "shutdown_schema": document["shutdown_result"]["schema"],
        "root_embeds_source": (
            checkpoint["execution_source_closure"]
            == document["source_closure"]
        ),
        "root_embeds_credentials": (
            checkpoint["credential_observation_bundle"]
            == document["credential_bundle"]
        ),
        "root_exact_topology": checkpoint[
            "exact_two_birth_os_topology_observed"
        ],
        "root_authority": checkpoint["portable_checkpoint_authority_present"],
        "root_e5a": checkpoint["e5a_runtime_lease_join_present"],
        "root_five_birth": checkpoint["five_birth_process_authority_present"],
        "root_official": checkpoint["official_execution_allowed"],
        "root_counter_gate": checkpoint["COUNTER_COMPLETENESS_GATE"],
        "root_economics_gate": checkpoint["WORKLOAD_ECONOMICS_GATE"],
        "final_population": len(_read_at(control_fd, "cgroup.procs").split()),
        "direct_children": _direct_children(),
    }


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "SUCCESS"
    if mode not in {
        "SUCCESS",
        "SOURCE_CLOSURE_FROZEN",
        "RAW_BEGIN_RETURNED",
        "LIVE_SNAPSHOT_FROZEN",
        "SOURCE_RECORD_FILE_FSYNC",
        "CREDENTIAL_RECORD_FILE_FSYNC",
        "CHECKPOINT_RECORD_FILE_FSYNC",
        "CHECKPOINT_RECORD_DIRECTORY_FSYNC",
        "ROOT_DURABLE_COMMIT",
        "RUNTIME_CLOSED",
        "FORGED_SNAPSHOT_RESIGN",
    }:
        raise RuntimeError(f"unknown portable-checkpoint test mode: {mode}")

    scope = _current_scope_path()
    root_fd = os.open(
        scope, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    suffix = f"{os.getpid()}-{uuid.uuid4().hex}"
    guardian_name = f"acfqp-checkpoint-guardian-{suffix}"
    delegated_name = f"acfqp-checkpoint-delegated-{suffix}"
    outer_name = f"acfqp-checkpoint-outer-{suffix}"
    guardian_fd = delegated_fd = outer_fd = control_fd = -1
    moved = False
    journal = Path(tempfile.mkdtemp(prefix="acfqp-two-birth-checkpoint-"))
    try:
        os.chmod(journal, 0o700)
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
        print(json.dumps(_run(control_fd, mode, journal), sort_keys=True))
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
        if guardian_fd >= 0:
            _wait_empty(guardian_fd)
            os.close(guardian_fd)
            os.rmdir(guardian_name, dir_fd=root_fd)
        if control_fd >= 0:
            os.close(control_fd)
        os.close(root_fd)
        shutil.rmtree(journal)


if __name__ == "__main__":
    raise SystemExit(main())
