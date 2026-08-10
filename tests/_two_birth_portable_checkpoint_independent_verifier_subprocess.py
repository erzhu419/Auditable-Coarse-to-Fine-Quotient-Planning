from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

import _two_birth_portable_checkpoint_subprocess as producer_helper

from acfqp import construction_k7_h1_two_birth_portable_checkpoint_independent_verifier_v1 as verifier


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
    }:
        raise RuntimeError(f"unknown independent-verifier mode: {mode}")

    scope = producer_helper._current_scope_path()  # noqa: SLF001
    root_fd = os.open(
        scope, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    suffix = f"{os.getpid()}-{uuid.uuid4().hex}"
    guardian_name = f"acfqp-verifier-guardian-{suffix}"
    delegated_name = f"acfqp-verifier-delegated-{suffix}"
    outer_name = f"acfqp-verifier-outer-{suffix}"
    guardian_fd = delegated_fd = outer_fd = control_fd = -1
    moved = False
    journal = Path(tempfile.mkdtemp(prefix="acfqp-two-birth-verifier-"))
    try:
        os.chmod(journal, 0o700)
        os.mkdir(guardian_name, mode=0o700, dir_fd=root_fd)
        guardian_fd = producer_helper._open_dir_at(  # noqa: SLF001
            root_fd, guardian_name
        )
        producer_helper._write_at(  # noqa: SLF001
            guardian_fd, "cgroup.procs", f"{os.getpid()}\n".encode()
        )
        moved = True
        producer_helper._write_at(  # noqa: SLF001
            root_fd, "cgroup.subtree_control", b"+memory +pids\n"
        )
        os.mkdir(delegated_name, mode=0o700, dir_fd=root_fd)
        delegated_fd = producer_helper._open_dir_at(  # noqa: SLF001
            root_fd, delegated_name
        )
        producer_helper._write_at(  # noqa: SLF001
            delegated_fd, "cgroup.subtree_control", b"+memory +pids\n"
        )
        os.mkdir(outer_name, mode=0o700, dir_fd=delegated_fd)
        outer_fd = producer_helper._open_dir_at(  # noqa: SLF001
            delegated_fd, outer_name
        )
        producer_helper._write_at(  # noqa: SLF001
            outer_fd, "memory.max", str(64 * 1024 * 1024).encode() + b"\n"
        )
        producer_helper._write_at(outer_fd, "pids.max", b"3\n")  # noqa: SLF001
        producer_helper._write_at(  # noqa: SLF001
            outer_fd, "cgroup.max.depth", b"1\n"
        )
        producer_helper._write_at(  # noqa: SLF001
            outer_fd, "cgroup.max.descendants", b"1\n"
        )
        producer_helper._write_at(  # noqa: SLF001
            outer_fd, "cgroup.subtree_control", b"+memory +pids\n"
        )
        os.mkdir("control", mode=0o700, dir_fd=outer_fd)
        control_fd = producer_helper._open_dir_at(outer_fd, "control")  # noqa: SLF001
        producer_helper._write_at(control_fd, "pids.max", b"2\n")  # noqa: SLF001

        producer_result = producer_helper._run(  # noqa: SLF001
            control_fd, mode, journal
        )
        raw_records = tuple(
            path.read_bytes() for path in sorted(journal.iterdir())
        )
        verification = (
            verifier.verify_two_birth_portable_checkpoint_journal_bytes_v1(
                raw_records
            )
        )
        print(
            json.dumps(
                {
                    "mode": mode,
                    "producer_success": producer_result["success"],
                    "record_count": len(raw_records),
                    "verifier_outcome": verification.outcome,
                    "success_observation_verified": (
                        verification.success_observation_verified
                    ),
                    "typed_noncertificate_verified": (
                        verification.typed_noncertificate_verified
                    ),
                    "portable_checkpoint_authority_present": (
                        verification.portable_checkpoint_authority_present
                    ),
                    "official_execution_allowed": (
                        verification.official_execution_allowed
                    ),
                    "final_population": len(
                        producer_helper._read_at(  # noqa: SLF001
                            control_fd, "cgroup.procs"
                        ).split()
                    ),
                    "direct_children": producer_helper._direct_children(),  # noqa: SLF001
                },
                sort_keys=True,
            )
        )
        return 0
    finally:
        if control_fd >= 0:
            producer_helper._write_at(control_fd, "cgroup.kill", b"1\n")  # noqa: SLF001
            producer_helper._wait_empty(control_fd)  # noqa: SLF001
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
            producer_helper._write_at(  # noqa: SLF001
                root_fd, "cgroup.subtree_control", b"-memory -pids\n"
            )
            producer_helper._write_at(  # noqa: SLF001
                root_fd, "cgroup.procs", f"{os.getpid()}\n".encode()
            )
        if guardian_fd >= 0:
            producer_helper._wait_empty(guardian_fd)  # noqa: SLF001
            os.close(guardian_fd)
            os.rmdir(guardian_name, dir_fd=root_fd)
        if control_fd >= 0:
            os.close(control_fd)
        os.close(root_fd)
        shutil.rmtree(journal)


if __name__ == "__main__":
    raise SystemExit(main())
