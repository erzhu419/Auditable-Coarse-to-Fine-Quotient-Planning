#!/usr/bin/env python3
"""Isolated outer worker supervisor for the fixed formal V42 identity.

The supervisor itself imports neither the campaign producer nor the independent
verifier. It creates one durable, secret-bound worker authorization, then runs
the producer and verifier in two different fresh ``python -I -S -B`` processes.
Only the outer runner publishes the returned campaign, verification, and typed
terminal/failure artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import secrets
import selectors
import signal
import stat
import subprocess
import sys
import time
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
# ``-I -S`` intentionally omits cwd and site-packages. The committed source
# root is the sole application bootstrap location.
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from acfqp import construction_k7_standard_2048_execution_authority_v42 as authority
from acfqp import construction_k7_standard_2048_fresh_terminal_preregistration_v42 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CHILD_TIMEOUT_SECONDS = 7 * 24 * 60 * 60
MAX_PRODUCER_STDOUT_BYTES = 512 * 1024 * 1024
MAX_VERIFIER_STDOUT_BYTES = 32 * 1024 * 1024
MAX_CHILD_STDERR_BYTES = 1024 * 1024
MAX_EXCEPTION_MESSAGE_BYTES = 4096


class V42SupervisedWorkerError(RuntimeError):
    """The isolated producer/verifier pipeline or worker claim failed."""


class V42IsolatedChildError(V42SupervisedWorkerError):
    def __init__(
        self,
        message: str,
        *,
        role: str,
        returncode: int | None,
        stdout: bytes,
        stderr: bytes,
        classification: str,
    ) -> None:
        super().__init__(message)
        self.role = role
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.classification = classification


def _fail(message: str) -> NoReturn:
    raise V42SupervisedWorkerError(message[:MAX_EXCEPTION_MESSAGE_BYTES])


def _require_isolated_python() -> None:
    if not (
        sys.flags.isolated == 1
        and sys.flags.no_site == 1
        and sys.dont_write_bytecode is True
    ):
        _fail("formal V42 worker role requires fresh python -I -S -B")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_worker_start_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC,
        0o400,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V42 worker-start short write")
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode) or stat.S_IMODE(observed.st_mode) != 0o400:
        _fail("V42 worker start is not one immutable regular file")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        retained = _read_fd_capped(descriptor, len(raw), "worker start readback")
    finally:
        os.close(descriptor)
    if retained != raw:
        _fail("V42 worker start readback changed")
    _fsync_directory(path.parent)


def _worker_start_document(
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_authorization_secret_sha256: str = "0" * 64,
) -> dict[str, Any]:
    return authority.build_worker_start_v42(
        prepare_receipt=prepare_receipt,
        runner_attempt=runner_attempt,
        worker_authorization_secret_sha256=worker_authorization_secret_sha256,
    )


def _isolated_command(
    role_flag: str, inherited_fd_flag: str, descriptor: int
) -> tuple[str, ...]:
    return (
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(Path(__file__).resolve()),
        role_flag,
        inherited_fd_flag,
        str(descriptor),
    )


def _memfd_from_bytes(label: str, raw: bytes) -> int:
    if type(raw) is not bytes:
        _fail("V42 child input changed type")
    descriptor = os.memfd_create(label, flags=os.MFD_CLOEXEC)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V42 memfd short write")
            view = view[written:]
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_fd_capped(descriptor: int, maximum: int, label: str) -> bytes:
    chunks: list[bytes] = []
    byte_count = 0
    while True:
        remaining = maximum + 1 - byte_count
        if remaining <= 0:
            _fail(f"V42 {label} exceeds its byte cap")
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        byte_count += len(chunk)
        if byte_count > maximum:
            _fail(f"V42 {label} exceeds its byte cap")
    return b"".join(chunks)


def _child_classification(role: str, returncode: int) -> str:
    if returncode < 0:
        number = -returncode
        try:
            name = signal.Signals(number).name
        except ValueError:
            name = "UNKNOWN"
        return f"{role}_SIGNAL_{name}_{number}"
    if returncode in (9, 137):
        return f"{role}_OOM_OR_SIGKILL_STYLE_EXIT"
    return f"{role}_NONZERO_EXIT"


def _bounded_message(error: BaseException) -> str:
    raw = str(error).encode("utf-8", errors="replace")[:MAX_EXCEPTION_MESSAGE_BYTES]
    return raw.decode("utf-8", errors="replace")


def _typed_failure_classification(raw: bytes, fallback: str) -> str:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        return fallback
    try:
        document = loads_canonical_json(raw[:-1])
    except (TypeError, ValueError):
        return fallback
    if (
        type(document) is dict
        and document.get("schema")
        == "acfqp.standard_2048_fresh_terminal_isolated_process_failure.v42"
        and type(document.get("failure_classification")) is str
    ):
        return document["failure_classification"]
    return fallback


def _run_capped_child(
    *,
    role: str,
    command: tuple[str, ...],
    inherited_descriptor: int,
    stdout_cap: int,
) -> subprocess.CompletedProcess[bytes]:
    environment = {"PATH": os.defpath, "LC_ALL": "C.UTF-8"}
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        pass_fds=(inherited_descriptor,),
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        _fail("V42 isolated child pipes are unavailable")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, ("stdout", stdout_cap))
    selector.register(
        process.stderr,
        selectors.EVENT_READ,
        ("stderr", MAX_CHILD_STDERR_BYTES),
    )
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + CHILD_TIMEOUT_SECONDS
    classification: str | None = None
    returncode: int | None = None
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                classification = f"{role}_TIMEOUT"
                process.kill()
                break
            for key, _ in selector.select(timeout=min(remaining, 1.0)):
                stream_name, cap = key.data
                chunk = os.read(key.fd, 64 * 1024)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                buffers[stream_name].extend(chunk)
                if len(buffers[stream_name]) > cap:
                    classification = f"{role}_{stream_name.upper()}_CAP_EXCEEDED"
                    process.kill()
                    break
            if classification is not None:
                break
        returncode = process.wait(timeout=30)
    finally:
        selector.close()
        for pipe in (process.stdout, process.stderr):
            if not pipe.closed:
                pipe.close()
    stdout = bytes(buffers["stdout"][:stdout_cap])
    stderr = bytes(buffers["stderr"][:MAX_CHILD_STDERR_BYTES])
    if classification is not None:
        raise V42IsolatedChildError(
            f"V42 {role} child failed: {classification}",
            role=role,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            classification=classification,
        )
    if returncode != 0:
        child_classification = _typed_failure_classification(
            stderr, _child_classification(role, int(returncode))
        )
        raise V42IsolatedChildError(
            f"V42 {role} child exited {returncode}",
            role=role,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            classification=child_classification,
        )
    if stderr:
        raise V42IsolatedChildError(
            f"V42 {role} child emitted unexpected stderr",
            role=role,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            classification=f"{role}_UNEXPECTED_STDERR",
        )
    return subprocess.CompletedProcess(command, int(returncode), stdout, stderr)


def _one_canonical_stdout(
    completed: subprocess.CompletedProcess[bytes], label: str
) -> bytes:
    if not completed.stdout.endswith(b"\n") or completed.stdout.endswith(b"\n\n"):
        _fail(f"V42 {label} stdout has noncanonical trailing bytes")
    raw = completed.stdout[:-1]
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V42SupervisedWorkerError(
            f"V42 {label} stdout is not canonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"V42 {label} stdout canonical bytes changed")
    return raw


def _read_fixed_artifact(path: Path, maximum: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        observed = os.fstat(descriptor)
        if not stat.S_ISREG(observed.st_mode) or observed.st_size > maximum:
            _fail(f"V42 fixed artifact is nonregular or exceeds cap: {path.name}")
        return _read_fd_capped(descriptor, maximum, path.name)
    finally:
        os.close(descriptor)


def _producer_worker(authorization_fd: int) -> int:
    _require_isolated_python()
    forbidden = {
        "acfqp.construction_k7_standard_2048_fresh_terminal_independent_verifier_v42",
        "scripts.run_v42_standard_2048_fresh_terminal_campaign",
    }
    if forbidden.intersection(sys.modules):
        _fail("V42 producer process imported verifier or runner")
    try:
        secret = _read_fd_capped(authorization_fd, 32, "worker authorization")
    finally:
        os.close(authorization_fd)
    if len(secret) != 32:
        _fail("V42 producer authorization has the wrong length")
    receipt_bytes = _read_fixed_artifact(
        authority.fixed_authority_root_v42(ROOT) / authority.PREPARE_RECEIPT_NAME,
        64 * 1024 * 1024,
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_bytes,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
        root=ROOT,
        require_live_source=True,
    )
    authority.install_runtime_repository_import_guard_v42(
        ROOT, receipt["source_manifest"]
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    from acfqp import construction_k7_standard_2048_fresh_terminal_campaign_v42 as campaign

    formal_authority = campaign._issue_formal_execution_authority_v42(  # noqa: SLF001
        repository_root=ROOT,
        worker_authorization_secret=secret,
    )
    produced = campaign._run_standard_2048_fresh_terminal_campaign_v42(  # noqa: SLF001
        formal_authority=formal_authority
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, formal_authority.prepare_receipt["source_manifest"]
    )
    sys.stdout.buffer.write(produced.canonical_bytes + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _verifier_worker(campaign_fd: int) -> int:
    _require_isolated_python()
    forbidden = {
        "acfqp.construction_k7_standard_2048_fresh_terminal_campaign_v42",
        "acfqp.construction_k7_standard_2048_adaptive_expression_target_v35",
        "acfqp.construction_k7_standard_2048_observation_proposed_program_v14",
        "acfqp.construction_k7_standard_2048_expression_planner_v1",
        "scripts.run_v42_standard_2048_fresh_terminal_campaign",
    }
    if forbidden.intersection(sys.modules):
        _fail("V42 verifier process imported campaign producer or runner")
    try:
        campaign_bytes = _read_fd_capped(
            campaign_fd, MAX_PRODUCER_STDOUT_BYTES, "campaign input"
        )
    finally:
        os.close(campaign_fd)
    authority_root = authority.fixed_authority_root_v42(ROOT)
    evidence_root = authority.fixed_evidence_root_v42(ROOT)
    receipt_bytes = _read_fixed_artifact(
        authority_root / authority.PREPARE_RECEIPT_NAME, 64 * 1024 * 1024
    )
    attempt_bytes = _read_fixed_artifact(
        evidence_root / authority.ATTEMPT_NAME, 1024 * 1024
    )
    worker_start_bytes = _read_fixed_artifact(
        evidence_root / authority.WORKER_START_NAME, 1024 * 1024
    )
    consumption_bytes = _read_fixed_artifact(
        evidence_root / authority.AUTHORITY_CONSUMPTION_NAME, 1024 * 1024
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_bytes,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
        root=ROOT,
        require_live_source=True,
    )
    authority.install_runtime_repository_import_guard_v42(
        ROOT, receipt["source_manifest"]
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    from acfqp import construction_k7_standard_2048_fresh_terminal_independent_verifier_v42 as verifier

    checked = verifier.verify_standard_2048_fresh_terminal_bytes_independently_v42(
        campaign_bytes,
        prepare_receipt_bytes=receipt_bytes,
        runner_attempt_bytes=attempt_bytes,
        worker_start_bytes=worker_start_bytes,
        authority_consumption_bytes=consumption_bytes,
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    sys.stdout.buffer.write(checked.canonical_bytes + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _formal_supervisor() -> int:
    _require_isolated_python()
    history_manifest = pre._freshness()  # noqa: SLF001
    authority_root = authority.fixed_authority_root_v42(ROOT)
    evidence_root = authority.fixed_evidence_root_v42(ROOT)
    receipt_bytes = _read_fixed_artifact(
        authority_root / authority.PREPARE_RECEIPT_NAME, 64 * 1024 * 1024
    )
    attempt_bytes = _read_fixed_artifact(
        evidence_root / authority.ATTEMPT_NAME, 1024 * 1024
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_bytes,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=history_manifest[
            "history_freshness_manifest_id"
        ],
        root=ROOT,
        require_live_source=True,
    )
    attempt = authority.verify_runner_attempt_v42(
        attempt_bytes,
        prepare_receipt=receipt,
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
    )
    authority.verify_live_source_matches_manifest_v42(ROOT, receipt["source_manifest"])
    authority.install_runtime_repository_import_guard_v42(
        ROOT, receipt["source_manifest"]
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    secret = secrets.token_bytes(32)
    worker_start = _worker_start_document(
        receipt, attempt, hashlib.sha256(secret).hexdigest()
    )
    _write_worker_start_once(
        evidence_root / authority.WORKER_START_NAME,
        canonical_json_bytes(worker_start),
    )

    authorization_fd = _memfd_from_bytes("v42-worker-authorization", secret)
    try:
        producer_completed = _run_capped_child(
            role="PRODUCER",
            command=_isolated_command(
                "--producer-worker", "--authorization-fd", authorization_fd
            ),
            inherited_descriptor=authorization_fd,
            stdout_cap=MAX_PRODUCER_STDOUT_BYTES + 1,
        )
    finally:
        os.close(authorization_fd)
    campaign_bytes = _one_canonical_stdout(producer_completed, "producer")
    campaign_fd = _memfd_from_bytes(
        "v42-campaign-for-independent-verifier", campaign_bytes
    )
    try:
        verifier_completed = _run_capped_child(
            role="VERIFIER",
            command=_isolated_command(
                "--verifier-worker", "--campaign-fd", campaign_fd
            ),
            inherited_descriptor=campaign_fd,
            stdout_cap=MAX_VERIFIER_STDOUT_BYTES + 1,
        )
    finally:
        os.close(campaign_fd)
    verification_bytes = _one_canonical_stdout(verifier_completed, "verifier")
    campaign_document = loads_canonical_json(campaign_bytes)
    verification_document = loads_canonical_json(verification_bytes)
    consumption_bytes = _read_fixed_artifact(
        evidence_root / authority.AUTHORITY_CONSUMPTION_NAME, 1024 * 1024
    )
    consumption = authority.verify_authority_consumption_v42(
        consumption_bytes,
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_start=worker_start,
    )
    if (
        type(campaign_document) is not dict
        or type(verification_document) is not dict
        or verification_document.get("fresh_terminal_campaign_id")
        != campaign_document.get("fresh_terminal_campaign_id")
    ):
        _fail("V42 isolated producer/verifier join changed")
    all_terminal = campaign_document.get("all_registered_episodes_terminal")
    if type(all_terminal) is not bool:
        _fail("V42 campaign terminal flag changed type")
    envelope = {
        "schema": "acfqp.standard_2048_fresh_terminal_supervised_result.v42",
        "schema_version": pre.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "prepare_receipt_id": receipt["prepare_receipt_id"],
        "runner_attempt_id": attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "authority_consumption_id": consumption["authority_consumption_id"],
        "producer_process_isolated": True,
        "verifier_process_isolated": True,
        "isolated_python_flags": ["-I", "-S", "-B"],
        "fresh_terminal_campaign": campaign_document,
        "fresh_terminal_independent_verification": verification_document,
        "all_registered_episodes_terminal": all_terminal,
        "scientific_exit_code": 0 if all_terminal else 2,
    }
    sys.stdout.buffer.write(canonical_json_bytes(envelope) + b"\n")
    sys.stdout.buffer.flush()
    return 0 if all_terminal else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one fixed V42 isolated role")
    roles = parser.add_mutually_exclusive_group(required=True)
    roles.add_argument("--formal-supervisor", action="store_true")
    roles.add_argument("--producer-worker", action="store_true")
    roles.add_argument("--verifier-worker", action="store_true")
    parser.add_argument("--authorization-fd", type=int)
    parser.add_argument("--campaign-fd", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.formal_supervisor:
        if arguments.authorization_fd is not None or arguments.campaign_fd is not None:
            _fail("V42 supervisor accepts no inherited worker descriptor")
        return _formal_supervisor()
    if arguments.producer_worker:
        if arguments.authorization_fd is None or arguments.campaign_fd is not None:
            _fail("V42 producer requires only its authorization descriptor")
        return _producer_worker(arguments.authorization_fd)
    if arguments.campaign_fd is None or arguments.authorization_fd is not None:
        _fail("V42 verifier requires only its campaign descriptor")
    return _verifier_worker(arguments.campaign_fd)


def _emit_typed_process_failure(error: BaseException) -> None:
    if "--producer-worker" in sys.argv:
        process_role = "PRODUCER"
    elif "--verifier-worker" in sys.argv:
        process_role = "VERIFIER"
    else:
        process_role = "SUPERVISOR"
    if isinstance(error, V42IsolatedChildError):
        classification = error.classification
        nested_role = error.role
        nested_returncode = error.returncode
        nested_stdout = error.stdout
        nested_stderr = error.stderr
    else:
        classification = f"{process_role}_EXCEPTION"
        nested_role = None
        nested_returncode = None
        nested_stdout = b""
        nested_stderr = b""
    document = {
        "schema": "acfqp.standard_2048_fresh_terminal_isolated_process_failure.v42",
        "schema_version": pre.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "process_role": process_role,
        "failure_classification": classification,
        "failure_type": type(error).__name__,
        "failure_message": _bounded_message(error),
        "failure_message_cap_bytes": MAX_EXCEPTION_MESSAGE_BYTES,
        "nested_role": nested_role,
        "nested_returncode": nested_returncode,
        "nested_stdout": {
            "captured_byte_count": len(nested_stdout),
            "sha256": hashlib.sha256(nested_stdout).hexdigest(),
        },
        "nested_stderr": {
            "captured_byte_count": len(nested_stderr),
            "sha256": hashlib.sha256(nested_stderr).hexdigest(),
        },
        "stdout_cap_bytes": MAX_PRODUCER_STDOUT_BYTES,
        "stderr_cap_bytes": MAX_CHILD_STDERR_BYTES,
        "scientific_success": False,
    }
    sys.stderr.buffer.write(canonical_json_bytes(document) + b"\n")
    sys.stderr.buffer.flush()


if __name__ == "__main__":
    try:
        _exit_code = main()
    except BaseException as _error:
        _emit_typed_process_failure(_error)
        _exit_code = 70
    raise SystemExit(_exit_code)
