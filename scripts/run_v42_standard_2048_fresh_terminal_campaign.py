#!/usr/bin/env python3
"""Prepare and one-shot supervise the committed formal V42 campaign.

``--prepare`` is outcome-free and writes one fixed committed-source receipt.
``--launch`` has no output-path argument: it consumes the single fixed V42
identity, durably publishes ATTEMPT, supervises an isolated worker, and closes
with either typed TERMINAL or typed FAILURE.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import signal
import selectors
import stat
import subprocess
import sys
import time
from typing import Any, NoReturn, Sequence

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp import construction_k7_standard_2048_execution_authority_v42 as authority
from acfqp import construction_k7_standard_2048_fresh_terminal_preregistration_v42 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SUPERVISED_WORKER_RELATIVE = (
    "scripts/supervise_v42_standard_2048_fresh_terminal_campaign.py"
)
WORKER_TIMEOUT_SECONDS = 7 * 24 * 60 * 60
MAX_SUPERVISOR_STDOUT_BYTES = 576 * 1024 * 1024
MAX_SUPERVISOR_STDERR_BYTES = 1024 * 1024
MAX_EXCEPTION_MESSAGE_BYTES = 4096


class V42FormalRunnerError(RuntimeError):
    """The fixed prepare, one-shot launch, worker, or publication failed."""


class V42WorkerProcessError(V42FormalRunnerError):
    """The supervised worker exited without one valid scientific envelope."""

    def __init__(
        self,
        message: str,
        *,
        returncode: int | None,
        stdout: bytes,
        stderr: bytes,
        classification: str,
    ) -> None:
        super().__init__(_bounded_text(message))
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.classification = classification


def _fail(message: str) -> NoReturn:
    raise V42FormalRunnerError(_bounded_text(message))


def _bounded_text(value: object) -> str:
    raw = str(value).encode("utf-8", errors="replace")[:MAX_EXCEPTION_MESSAGE_BYTES]
    return raw.decode("utf-8", errors="replace")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_once(path: Path, raw: bytes) -> dict[str, object]:
    """Publish one O_EXCL file and verify its exact durable readback."""

    if type(raw) is not bytes:
        _fail("V42 publication bytes changed type")
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
                raise OSError("V42 publication short write")
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode) or stat.S_IMODE(observed.st_mode) != 0o400:
        _fail("V42 publication is not one immutable regular file")
    retained = path.read_bytes()
    if retained != raw:
        _fail("V42 publication readback changed")
    _fsync_directory(path.parent)
    return {
        "relative_name": path.name,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _create_one_shot_root(path: Path) -> None:
    """Create one already-resolved fixed root; callers never accept user paths."""

    if not path.is_absolute() or path == Path(path.anchor) or path == ROOT:
        _fail("V42 fixed root is not one narrow absolute repository path")
    parent = path.parent
    parent_stat = parent.lstat()
    if not stat.S_ISDIR(parent_stat.st_mode):
        _fail("V42 fixed-root parent is not a directory")
    try:
        os.mkdir(path, mode=0o700)
    except FileExistsError as error:
        raise V42FormalRunnerError(
            "V42 fixed one-shot identity already exists; rerun is forbidden"
        ) from error
    os.chmod(path, 0o700)
    _fsync_directory(parent)
    _fsync_directory(path)


def _ensure_fixed_container(path: Path) -> None:
    """Create only fixed parent components, rejecting symlink redirection."""

    resolved_root = ROOT.resolve()
    if path != resolved_root / ".tmp" / "exact-freeze":
        _fail("V42 fixed container path changed")
    current = resolved_root
    for component in (".tmp", "exact-freeze"):
        child = current / component
        try:
            observed = child.lstat()
        except FileNotFoundError:
            os.mkdir(child, mode=0o700)
            _fsync_directory(current)
            observed = child.lstat()
        if not stat.S_ISDIR(observed.st_mode):
            _fail("V42 fixed container component is not a directory")
        current = child


def _journal_document(
    *, schema: str, domain: str, id_key: str, fields: dict[str, Any]
) -> dict[str, Any]:
    payload = {"schema": schema, "schema_version": pre.SCHEMA_VERSION, **fields}
    return {
        **payload,
        id_key: domains.extension_content_id_v42(domain, payload),
    }


def _artifact_fact(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "relative_name": path.name,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _failure_stream_fact(raw: bytes) -> dict[str, object]:
    return {
        "captured_byte_count": len(raw),
        "capture_cap_bytes": max(
            MAX_SUPERVISOR_STDOUT_BYTES, MAX_SUPERVISOR_STDERR_BYTES
        ),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "capture_was_bounded": True,
    }


def _worker_failure_classification(returncode: int) -> str:
    if returncode < 0:
        number = -returncode
        try:
            name = signal.Signals(number).name
        except ValueError:
            name = "UNKNOWN"
        return f"WORKER_SIGNAL_{name}_{number}"
    if returncode in (137, 9):
        return "WORKER_OOM_OR_SIGKILL_STYLE_EXIT"
    return "WORKER_NONZERO_EXIT"


def _typed_supervisor_failure_classification(raw: bytes, fallback: str) -> str:
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


def _scientific_exit_code(all_terminal: bool) -> int:
    if type(all_terminal) is not bool:
        _fail("V42 scientific terminal flag changed type")
    return 0 if all_terminal else 2


def _run_supervised_worker() -> subprocess.CompletedProcess[bytes]:
    environment = {"PATH": os.defpath, "LC_ALL": "C.UTF-8"}
    command = (
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(ROOT / SUPERVISED_WORKER_RELATIVE),
        "--formal-supervisor",
    )
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        _fail("V42 supervisor pipes are unavailable")
    selector = selectors.DefaultSelector()
    selector.register(
        process.stdout,
        selectors.EVENT_READ,
        ("stdout", MAX_SUPERVISOR_STDOUT_BYTES),
    )
    selector.register(
        process.stderr,
        selectors.EVENT_READ,
        ("stderr", MAX_SUPERVISOR_STDERR_BYTES),
    )
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + WORKER_TIMEOUT_SECONDS
    classification: str | None = None
    returncode: int | None = None
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                classification = "WORKER_TIMEOUT"
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
                    classification = f"WORKER_{stream_name.upper()}_CAP_EXCEEDED"
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
    stdout = bytes(buffers["stdout"][:MAX_SUPERVISOR_STDOUT_BYTES])
    stderr = bytes(buffers["stderr"][:MAX_SUPERVISOR_STDERR_BYTES])
    if classification is not None:
        raise V42WorkerProcessError(
            f"V42 supervised worker failed: {classification}",
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            classification=classification,
        )
    return subprocess.CompletedProcess(command, int(returncode), stdout, stderr)


def _parse_worker_envelope(
    completed: subprocess.CompletedProcess[bytes],
    *,
    receipt: dict[str, Any],
    attempt: dict[str, Any],
) -> tuple[bytes, bytes, bool]:
    if completed.returncode not in (0, 2):
        fallback = _worker_failure_classification(completed.returncode)
        raise V42WorkerProcessError(
            f"V42 supervised worker exited {completed.returncode}",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            classification=_typed_supervisor_failure_classification(
                completed.stderr, fallback
            ),
        )
    if not completed.stdout.endswith(b"\n") or completed.stdout.endswith(b"\n\n"):
        raise V42WorkerProcessError(
            "V42 supervised worker stdout has noncanonical trailing bytes",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            classification="WORKER_RESULT_MALFORMED",
        )
    raw = completed.stdout[:-1]
    try:
        envelope = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V42WorkerProcessError(
            "V42 supervised worker result is not canonical",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            classification="WORKER_RESULT_MALFORMED",
        ) from error
    exact_fields = {
        "schema",
        "schema_version",
        "formal_identity",
        "prepare_receipt_id",
        "runner_attempt_id",
        "worker_start_id",
        "authority_consumption_id",
        "producer_process_isolated",
        "verifier_process_isolated",
        "isolated_python_flags",
        "fresh_terminal_campaign",
        "fresh_terminal_independent_verification",
        "all_registered_episodes_terminal",
        "scientific_exit_code",
    }
    if (
        type(envelope) is not dict
        or set(envelope) != exact_fields
        or canonical_json_bytes(envelope) != raw
        or envelope.get("schema")
        != "acfqp.standard_2048_fresh_terminal_supervised_result.v42"
        or envelope.get("schema_version") != pre.SCHEMA_VERSION
        or envelope.get("formal_identity") != authority.FORMAL_IDENTITY
        or envelope.get("prepare_receipt_id") != receipt["prepare_receipt_id"]
        or envelope.get("runner_attempt_id") != attempt["runner_attempt_id"]
        or type(envelope.get("worker_start_id")) is not str
        or type(envelope.get("authority_consumption_id")) is not str
        or envelope.get("producer_process_isolated") is not True
        or envelope.get("verifier_process_isolated") is not True
        or envelope.get("isolated_python_flags") != ["-I", "-S", "-B"]
        or type(envelope.get("all_registered_episodes_terminal")) is not bool
        or envelope.get("scientific_exit_code") != completed.returncode
        or completed.returncode
        != _scientific_exit_code(envelope.get("all_registered_episodes_terminal"))
    ):
        raise V42WorkerProcessError(
            "V42 supervised worker envelope semantics changed",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            classification="WORKER_RESULT_MALFORMED",
        )
    campaign_bytes = canonical_json_bytes(envelope["fresh_terminal_campaign"])
    verification_bytes = canonical_json_bytes(
        envelope["fresh_terminal_independent_verification"]
    )
    campaign_document = envelope["fresh_terminal_campaign"]
    verification_document = envelope["fresh_terminal_independent_verification"]
    if type(campaign_document) is not dict or type(verification_document) is not dict:
        raise V42WorkerProcessError(
            "V42 supervised worker returned non-object scientific artifacts",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            classification="WORKER_RESULT_MALFORMED",
        )
    campaign_payload = dict(campaign_document)
    campaign_id = campaign_payload.pop("fresh_terminal_campaign_id", None)
    verification_payload = dict(verification_document)
    verification_id = verification_payload.pop("fresh_terminal_verification_id", None)
    if (
        type(campaign_id) is not str
        or domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN, campaign_payload
        )
        != campaign_id
        or type(verification_id) is not str
        or domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_VERIFICATION_V42_DOMAIN, verification_payload
        )
        != verification_id
        or verification_document.get("fresh_terminal_campaign_id") != campaign_id
        or verification_document.get("prepare_receipt_id")
        != receipt["prepare_receipt_id"]
        or verification_document.get("runner_attempt_id")
        != attempt["runner_attempt_id"]
        or verification_document.get("worker_start_id")
        != envelope["worker_start_id"]
        or verification_document.get("authority_consumption_id")
        != envelope["authority_consumption_id"]
        or verification_document.get("producer_or_runner_module_imported") is not False
        or campaign_document.get("all_registered_episodes_terminal")
        is not envelope["all_registered_episodes_terminal"]
    ):
        raise V42WorkerProcessError(
            "V42 isolated campaign/verification content-ID join changed",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            classification="WORKER_RESULT_REPLAY_MISMATCH",
        )
    return campaign_bytes, verification_bytes, bool(
        envelope["all_registered_episodes_terminal"]
    )


def _failure_document(
    *,
    stage: str,
    error: BaseException,
    receipt: dict[str, Any],
    attempt: dict[str, Any],
    evidence_root: Path,
    expected_attempt_bytes: bytes,
    launch_attempt_journal_id: str | None = None,
    expected_launch_attempt_journal_bytes: bytes | None = None,
) -> dict[str, Any]:
    if isinstance(error, V42WorkerProcessError):
        worker_classification = error.classification
        worker_returncode = error.returncode
        worker_stdout = _failure_stream_fact(error.stdout)
        worker_stderr = _failure_stream_fact(error.stderr)
    else:
        worker_classification = None
        worker_returncode = None
        worker_stdout = _failure_stream_fact(b"")
        worker_stderr = _failure_stream_fact(b"")
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_runner_failure.v42",
        "schema_version": pre.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "prepare_receipt_id": receipt["prepare_receipt_id"],
        "runner_attempt_id": attempt["runner_attempt_id"],
        "launch_attempt_journal_id": launch_attempt_journal_id,
        "fresh_terminal_preregistration_id": pre.PREREGISTRATION_ID,
        "source_commit": receipt["source_commit"],
        "source_tree": receipt["source_tree"],
        "source_manifest_id": receipt["source_manifest_id"],
        "failure_stage": stage,
        "failure_type": type(error).__name__,
        "failure_message": _bounded_text(error),
        "failure_message_cap_bytes": MAX_EXCEPTION_MESSAGE_BYTES,
        "worker_failure_classification": worker_classification,
        "worker_returncode": worker_returncode,
        "worker_stdout": worker_stdout,
        "worker_stderr": worker_stderr,
        "fixed_parent_launch_attempt_state": authority.classify_artifact_bytes_v42(
            ROOT / authority.LAUNCH_ATTEMPT_JOURNAL_NAME,
            expected_launch_attempt_journal_bytes,
        ),
        "evidence_root_state": _path_state(evidence_root),
        "artifact_states": {
            name: authority.classify_artifact_bytes_v42(
                evidence_root / name,
                expected_attempt_bytes if name == authority.ATTEMPT_NAME else None,
            )
            for name in (
                authority.ATTEMPT_NAME,
                authority.WORKER_START_NAME,
                authority.AUTHORITY_CONSUMPTION_NAME,
                authority.CAMPAIGN_NAME,
                authority.VERIFICATION_NAME,
                authority.TERMINAL_NAME,
            )
        },
        "scientific_success": False,
        "same_identity_rerun_forbidden": True,
        "crash_resume_claimed": False,
        "broad_iid_or_total_work_claimed": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "runner_failure_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_RUNNER_FAILURE_V42_DOMAIN, payload
        ),
    }


def _path_state(path: Path) -> str:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    if stat.S_ISDIR(observed.st_mode):
        return "DIRECTORY"
    if stat.S_ISREG(observed.st_mode):
        return "REGULAR_FILE"
    return "NONREGULAR"


def _prepare() -> int:
    history_manifest = pre._freshness()  # noqa: SLF001
    prepare_attempt = _journal_document(
        schema="acfqp.standard_2048_fresh_terminal_prepare_attempt_journal.v42",
        domain=domains.CONSTRUCTION_K7_PREPARE_JOURNAL_V42_DOMAIN,
        id_key="prepare_attempt_journal_id",
        fields={
            "formal_identity": authority.FORMAL_IDENTITY,
            "fresh_terminal_preregistration_id": pre.PREREGISTRATION_ID,
            "history_freshness_manifest_id": history_manifest[
                "history_freshness_manifest_id"
            ],
            "prepare_ordinal": 1,
            "authority_root_relative": authority.AUTHORITY_ROOT_RELATIVE,
            "evidence_root_relative": authority.EVIDENCE_ROOT_RELATIVE,
            "outcome_or_tape_materialized": False,
            "formal_execution_performed": False,
        },
    )
    prepare_attempt_bytes = canonical_json_bytes(prepare_attempt)
    authority_root = authority.fixed_authority_root_v42(ROOT)
    evidence_root = authority.fixed_evidence_root_v42(ROOT)
    receipt: dict[str, Any] | None = None
    raw: bytes | None = None
    stage = "PREPARE_ATTEMPT_PUBLICATION"
    try:
        _write_once(
            ROOT / authority.PREPARE_ATTEMPT_JOURNAL_NAME,
            prepare_attempt_bytes,
        )
        stage = "PREREGISTRATION_AND_SOURCE_PREFLIGHT"
        frozen = pre.verify_standard_2048_fresh_terminal_preregistration_v42(
            pre.freeze_standard_2048_fresh_terminal_preregistration_v42()
        )
        receipt = authority.build_prepare_receipt_v42(
            ROOT,
            fresh_terminal_preregistration_id=frozen.preregistration_id,
            history_freshness_manifest_id=history_manifest[
                "history_freshness_manifest_id"
            ],
        )
        raw = canonical_json_bytes(receipt)
        if evidence_root.exists():
            _fail("V42 evidence identity already exists before prepare")
        stage = "FIXED_CONTAINER_CREATION"
        _ensure_fixed_container(authority_root.parent)
        stage = "AUTHORITY_ROOT_CREATION"
        _create_one_shot_root(authority_root)
        stage = "PREPARE_RECEIPT_PUBLICATION"
        _write_once(authority_root / authority.PREPARE_RECEIPT_NAME, raw)
    except BaseException as error:
        failure = _journal_document(
            schema="acfqp.standard_2048_fresh_terminal_prepare_failure_journal.v42",
            domain=domains.CONSTRUCTION_K7_PREPARE_JOURNAL_V42_DOMAIN,
            id_key="prepare_failure_journal_id",
            fields={
                "formal_identity": authority.FORMAL_IDENTITY,
                "prepare_attempt_journal_id": prepare_attempt[
                    "prepare_attempt_journal_id"
                ],
                "failure_stage": stage,
                "failure_type": type(error).__name__,
                "failure_message": _bounded_text(error),
                "failure_message_cap_bytes": MAX_EXCEPTION_MESSAGE_BYTES,
                "source_commit": None if receipt is None else receipt["source_commit"],
                "authority_root_state": _path_state(authority_root),
                "evidence_root_state": _path_state(evidence_root),
                "prepare_receipt_state": authority.classify_artifact_bytes_v42(
                    authority_root / authority.PREPARE_RECEIPT_NAME, raw
                ),
                "prepare_attempt_journal_state": authority.classify_artifact_bytes_v42(
                    ROOT / authority.PREPARE_ATTEMPT_JOURNAL_NAME,
                    prepare_attempt_bytes,
                ),
                "outcome_or_tape_materialized": False,
                "formal_execution_performed": False,
                "same_identity_prepare_retry_forbidden": True,
            },
        )
        publication_error: BaseException | None = None
        try:
            _write_once(
                ROOT / authority.PREPARE_FAILURE_JOURNAL_NAME,
                canonical_json_bytes(failure),
            )
        except BaseException as journal_error:
            publication_error = journal_error
        if publication_error is not None:
            raise V42FormalRunnerError(
                "V42 prepare failed and fixed-parent failure journal also failed: "
                + _bounded_text(publication_error)
            ) from error
        raise
    if raw is None:
        raise AssertionError("V42 successful prepare omitted receipt bytes")
    sys.stdout.write(raw.decode("utf-8") + "\n")
    return 0


def _launch() -> int:
    history_manifest = pre._freshness()  # noqa: SLF001
    authority_root = authority.fixed_authority_root_v42(ROOT)
    evidence_root = authority.fixed_evidence_root_v42(ROOT)
    receipt_bytes = (authority_root / authority.PREPARE_RECEIPT_NAME).read_bytes()
    receipt = authority.verify_prepare_receipt_v42(
        receipt_bytes,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=history_manifest[
            "history_freshness_manifest_id"
        ],
        root=ROOT,
        require_live_source=True,
    )
    # All source/commit/blob preflight happens before the fixed evidence root,
    # ATTEMPT, worker start, or any registered outcome tape can exist.
    authority.verify_live_source_matches_manifest_v42(ROOT, receipt["source_manifest"])
    attempt = authority.build_runner_attempt_v42(
        receipt,
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
    )
    attempt_bytes = canonical_json_bytes(attempt)
    launch_attempt = _journal_document(
        schema="acfqp.standard_2048_fresh_terminal_launch_attempt_journal.v42",
        domain=domains.CONSTRUCTION_K7_LAUNCH_JOURNAL_V42_DOMAIN,
        id_key="launch_attempt_journal_id",
        fields={
            "formal_identity": authority.FORMAL_IDENTITY,
            "prepare_receipt_id": receipt["prepare_receipt_id"],
            "runner_attempt_id": attempt["runner_attempt_id"],
            "source_commit": receipt["source_commit"],
            "source_tree": receipt["source_tree"],
            "source_manifest_id": receipt["source_manifest_id"],
            "launch_ordinal": 1,
            "fixed_evidence_root_relative": authority.EVIDENCE_ROOT_RELATIVE,
            "outcome_fields_present": False,
            "formal_execution_performed": False,
        },
    )
    launch_attempt_bytes = canonical_json_bytes(launch_attempt)
    stage = "LAUNCH_ATTEMPT_JOURNAL_PUBLICATION"
    try:
        _write_once(
            ROOT / authority.LAUNCH_ATTEMPT_JOURNAL_NAME,
            launch_attempt_bytes,
        )
        stage = "EVIDENCE_ROOT_CREATION"
        _create_one_shot_root(evidence_root)
        stage = "ATTEMPT_PUBLICATION"
        attempt_fact = _write_once(
            evidence_root / authority.ATTEMPT_NAME, attempt_bytes
        )
        stage = "SUPERVISED_WORKER"
        completed = _run_supervised_worker()
        campaign_bytes, verification_bytes, all_terminal = _parse_worker_envelope(
            completed, receipt=receipt, attempt=attempt
        )
        stage = "CAMPAIGN_PUBLICATION"
        campaign_fact = _write_once(
            evidence_root / authority.CAMPAIGN_NAME, campaign_bytes
        )
        stage = "VERIFICATION_PUBLICATION"
        verification_fact = _write_once(
            evidence_root / authority.VERIFICATION_NAME, verification_bytes
        )
        worker_start_fact = _artifact_fact(
            evidence_root / authority.WORKER_START_NAME
        )
        authority_consumption_fact = _artifact_fact(
            evidence_root / authority.AUTHORITY_CONSUMPTION_NAME
        )
        terminal_payload = {
            "schema": "acfqp.standard_2048_fresh_terminal_runner_terminal.v42",
            "schema_version": pre.SCHEMA_VERSION,
            "formal_identity": authority.FORMAL_IDENTITY,
            "prepare_receipt_id": receipt["prepare_receipt_id"],
            "runner_attempt_id": attempt["runner_attempt_id"],
            "fresh_terminal_preregistration_id": pre.PREREGISTRATION_ID,
            "source_commit": receipt["source_commit"],
            "source_tree": receipt["source_tree"],
            "source_manifest_id": receipt["source_manifest_id"],
            "attempt_artifact": attempt_fact,
            "worker_start_artifact": worker_start_fact,
            "authority_consumption_artifact": authority_consumption_fact,
            "campaign_artifact": campaign_fact,
            "verification_artifact": verification_fact,
            "status": (
                "PASS_FRESH_FROM_INITIAL_TO_TERMINAL"
                if all_terminal
                else "FAIL_CLOSED_ACTIVE_AT_2048_DECISION_CAP"
            ),
            "scientific_success": all_terminal,
            "all_registered_episodes_terminal": all_terminal,
            "crash_resume_claimed": False,
            "broad_iid_or_total_work_claimed": False,
            "official_execution_allowed": False,
            "same_identity_rerun_forbidden": True,
        }
        terminal = {
            **terminal_payload,
            "runner_terminal_id": domains.extension_content_id_v42(
                domains.CONSTRUCTION_K7_RUNNER_TERMINAL_V42_DOMAIN,
                terminal_payload,
            ),
        }
        stage = "TERMINAL_PUBLICATION"
        terminal_bytes = canonical_json_bytes(terminal)
        _write_once(evidence_root / authority.TERMINAL_NAME, terminal_bytes)
        sys.stdout.write(terminal_bytes.decode("utf-8") + "\n")
        return _scientific_exit_code(all_terminal)
    except BaseException as error:
        failure = _failure_document(
            stage=stage,
            error=error,
            receipt=receipt,
            attempt=attempt,
            evidence_root=evidence_root,
            expected_attempt_bytes=attempt_bytes,
            launch_attempt_journal_id=launch_attempt["launch_attempt_journal_id"],
            expected_launch_attempt_journal_bytes=launch_attempt_bytes,
        )
        failure_error: BaseException | None = None
        failure_bytes = canonical_json_bytes(failure)
        try:
            _write_once(
                ROOT / authority.LAUNCH_FAILURE_JOURNAL_NAME,
                failure_bytes,
            )
        except BaseException as publication_error:
            failure_error = publication_error
        if failure_error is None and _path_state(evidence_root) == "DIRECTORY":
            try:
                _write_once(evidence_root / authority.FAILURE_NAME, failure_bytes)
            except BaseException:
                # The fixed-parent journal is the total failure authority.  A
                # partial or conflicting evidence-root mirror is classified in
                # that journal and never authorizes a retry.
                pass
        if failure_error is not None:
            raise V42FormalRunnerError(
                "V42 launch failed and durable FAILURE publication also failed: "
                f"{failure_error}"
            ) from error
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare or one-shot launch the fixed committed V42 identity"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--launch", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    return _prepare() if arguments.prepare else _launch()


if __name__ == "__main__":
    raise SystemExit(main())
