"""V0-075 process-isolated occurrence transport foundation.

This module is deliberately *not* a scientific campaign runner.  It provides
the transport and failure-accounting substrate needed before a future
production adapter may execute fresh held-out occurrences:

* only canonical bytes and immutable scalar identities cross into a child;
* the parent creates one private journal per occurrence before submission;
* children append content-addressed stage checkpoints and never share a
  mutable journal;
* a strict loader replays the chunk manifest from disk;
* scientific zero-based ordinals are mapped explicitly to one-based transport
  ordinals; and
* physical PIDs are diagnostics only.  They are absent from every content
  identity and are never treated as unique.

Only registered, non-scientific fixture workers are available in V1.  A
production algorithm adapter is intentionally outside this module.
"""

from __future__ import annotations

import hashlib
import os
import stat
from concurrent.futures import Future, ProcessPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from .phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


PROFILE_KEY = "v075_occurrence_cas_transport_fixture_v1"
_STDLIB_PROCESS_POOL_EXECUTOR = ProcessPoolExecutor
SCIENTIFIC_CLAIM = False
MAX_WORKERS = 192
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_CHUNK_BYTES = 16 * 1024 * 1024

INPUT_DOMAIN = "acfqp:v075-occurrence-transport-input:v1"
BATCH_TARGET_COMMITMENT_DOMAIN = (
    "acfqp:v075-occurrence-batch-target-commitment:v1"
)
BATCH_DOMAIN = "acfqp:v075-occurrence-transport-batch:v1"
BATCH_HEADER_DOMAIN = "acfqp:v075-occurrence-transport-batch-header:v1"
JOURNAL_HEADER_DOMAIN = "acfqp:v075-occurrence-private-journal-header:v1"
CHECKPOINT_DOMAIN = "acfqp:v075-occurrence-stage-checkpoint:v1"
FIXTURE_RESULT_DOMAIN = "acfqp:v075-occurrence-fixture-result:v1"
OCCURRENCE_MANIFEST_DOMAIN = "acfqp:v075-occurrence-cas-manifest:v1"
QUARANTINE_MANIFEST_DOMAIN = (
    "acfqp:v075-occurrence-malformed-tail-quarantine:v1"
)
BATCH_MERGE_DOMAIN = "acfqp:v075-occurrence-transport-merge:v1"
BATCH_FAILURE_DOMAIN = "acfqp:v075-occurrence-transport-failure:v1"

ORDINAL_MAPPING = "SCIENTIFIC_ZERO_TO_TRANSPORT_ONE_PLUS_ONE_V1"
CACHE_POLICY = "NO_CACHE_NO_REUSE_V1"

INPUT_SCHEMA = "acfqp.v075.occurrence_transport_input.v1"
BATCH_SCHEMA = "acfqp.v075.occurrence_transport_batch.v1"
BATCH_HEADER_SCHEMA = "acfqp.v075.occurrence_transport_batch_header.v1"
JOURNAL_HEADER_SCHEMA = "acfqp.v075.private_journal_header.v1"
CHECKPOINT_SCHEMA = "acfqp.v075.stage_checkpoint.v1"
FIXTURE_RESULT_SCHEMA = "acfqp.v075.fixture_result.v1"
OCCURRENCE_MANIFEST_SCHEMA = "acfqp.v075.occurrence_cas_manifest.v1"
QUARANTINE_MANIFEST_SCHEMA = (
    "acfqp.v075.occurrence_malformed_tail_quarantine.v1"
)
CHILD_REQUEST_SCHEMA = "acfqp.v075.nonidentity_child_transport_request.v1"
BATCH_MERGE_SCHEMA = "acfqp.v075.transport_merge.v1"
BATCH_FAILURE_SCHEMA = "acfqp.v075.transport_failure.v1"

_CHUNK_DOMAINS = {
    CHECKPOINT_SCHEMA: (CHECKPOINT_DOMAIN, "checkpoint_id", "CHECKPOINT"),
    FIXTURE_RESULT_SCHEMA: (
        FIXTURE_RESULT_DOMAIN,
        "result_id",
        "FIXTURE_RESULT",
    ),
}

_SUCCESS_STAGES = (
    "INPUT_ACCEPTED",
    "SOURCE_BOUND",
    "FIXTURE_EXECUTED",
    "OUTPUT_SEALED",
)
_FAILURE_STAGES = (
    "INPUT_ACCEPTED",
    "SOURCE_BOUND",
    "FAILURE_CLOSED",
)

_WORK_PATHS = (
    "control.parent_journal_prepared",
    "control.child_submit_attempts",
    "control.child_submitted",
    "process.child_process_launches",
    "fixture.stage_checkpoints_completed",
    "fixture.worker_events",
    "io.cas_chunks_written",
    "io.cas_output_bytes",
)


class V075TransportInvariantViolation(ValueError):
    """A V0-075 transport or replay invariant was violated."""


class RegisteredFixtureWorkerV1(str, Enum):
    """Complete V1 registry; neither member carries a scientific claim."""

    SAFE_HASH_V1 = "SAFE_HASH_V1"
    FAIL_AFTER_SOURCE_BINDING_V1 = "FAIL_AFTER_SOURCE_BINDING_V1"


class V075TransportBatchExecutionFailure(RuntimeError):
    """Raised after all occurrence work has been retained without a merge."""

    def __init__(self, closure: "BatchFailureClosureV1") -> None:
        self.closure = closure
        super().__init__(
            "V0-075 transport batch failed closed; "
            f"failure closure={closure.failure_closure_id}; "
            "no scientific merge was produced"
        )


def _fail(message: str) -> None:
    raise V075TransportInvariantViolation(message)


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except (Phase3EIdentityError, ValueError) as error:
        raise V075TransportInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        _fail(f"{field} must be one nonempty canonical string")
    return value


def _exact_document(
    value: Any,
    fields: set[str] | frozenset[str],
    *,
    context: str,
) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{context} must be one object")
    actual = frozenset(value)
    expected = frozenset(fields)
    if actual != expected or any(type(key) is not str for key in value):
        _fail(
            f"{context} field set mismatch: "
            f"missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )
    return value


def _canonical_clone(value: Any, field: str) -> Any:
    try:
        raw = canonical_json_bytes(value)
        return loads_canonical_json(raw)
    except (Phase3EIdentityError, ValueError, TypeError) as error:
        raise V075TransportInvariantViolation(
            f"{field} is outside the canonical transport value language"
        ) from error


def _domain_id(domain: str, body: dict[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(body)
    ).hexdigest()


def _seal_document(
    domain: str,
    body: dict[str, Any],
    identity_field: str,
) -> tuple[dict[str, Any], bytes]:
    sealed = dict(body)
    sealed[identity_field] = _domain_id(domain, body)
    return sealed, canonical_json_bytes(sealed)


def _verify_sealed_document(
    document: dict[str, Any],
    *,
    domain: str,
    identity_field: str,
    context: str,
) -> str:
    if identity_field not in document:
        _fail(f"{context} is missing {identity_field}")
    claimed = _cid(document[identity_field], f"{context} {identity_field}")
    body = dict(document)
    del body[identity_field]
    if _domain_id(domain, body) != claimed:
        _fail(f"{context} content identity mismatch")
    return claimed


def _load_canonical_document(raw: bytes, *, context: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{context} must cross the boundary as canonical bytes")
    if len(raw) > MAX_INPUT_BYTES:
        _fail(f"{context} exceeds the V0-075 byte cap")
    try:
        value = loads_canonical_json(raw)
    except Phase3EIdentityError as error:
        raise V075TransportInvariantViolation(
            f"{context} is not strict canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{context} must decode to one object")
    return value


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": _token(reason, "null reason")}


def _content_ref(value: str) -> dict[str, str]:
    return {"kind": "CONTENT_ID", "value": _cid(value, "content reference")}


def _validate_typed_ref(
    value: Any,
    *,
    field: str,
    allow_content: bool,
) -> str | None:
    if type(value) is not dict:
        _fail(f"{field} must be one typed reference")
    kind = value.get("kind")
    if kind == "CONTENT_ID" and allow_content:
        _exact_document(value, {"kind", "value"}, context=field)
        return _cid(value["value"], field)
    if kind == "NOT_APPLICABLE":
        _exact_document(value, {"kind", "reason"}, context=field)
        _token(value["reason"], f"{field} reason")
        return None
    _fail(f"{field} has an invalid typed-reference kind")


def _validate_fixture_payload(value: Any) -> dict[str, Any]:
    payload = _exact_document(
        _canonical_clone(value, "fixture payload"),
        {"fixture_label", "values"},
        context="fixture payload",
    )
    _token(payload["fixture_label"], "fixture label")
    values = payload["values"]
    if (
        type(values) is not list
        or len(values) > 100_000
        or any(type(item) is not int for item in values)
    ):
        _fail("fixture values must be a bounded list of integers")
    return payload


@dataclass(frozen=True)
class OccurrenceSpecV1:
    """One non-scientific fixture occurrence on a zero-based schedule."""

    scientific_ordinal: int
    occurrence_id: str
    target_scope_id: str
    target_payload: dict[str, Any]
    worker_key: RegisteredFixtureWorkerV1
    _sealed_target_payload: dict[str, Any] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.scientific_ordinal) is not int or self.scientific_ordinal < 0:
            _fail("scientific ordinal must be a nonnegative integer")
        object.__setattr__(
            self,
            "occurrence_id",
            _cid(self.occurrence_id, "occurrence identity"),
        )
        object.__setattr__(
            self,
            "target_scope_id",
            _cid(self.target_scope_id, "target scope identity"),
        )
        if not isinstance(self.worker_key, RegisteredFixtureWorkerV1):
            _fail("worker key must be one registered V0-075 fixture worker")
        sealed = _validate_fixture_payload(self.target_payload)
        object.__setattr__(self, "_sealed_target_payload", sealed)
        object.__setattr__(self, "target_payload", _canonical_clone(sealed, "payload"))

    @property
    def transport_ordinal(self) -> int:
        return self.scientific_ordinal + 1

    @property
    def sealed_target_payload(self) -> dict[str, Any]:
        return _canonical_clone(self._sealed_target_payload, "sealed payload")


@dataclass(frozen=True)
class PreparedOccurrenceJournalV1:
    scientific_ordinal: int
    transport_ordinal: int
    occurrence_id: str
    input_id: str
    input_bytes: bytes
    journal_path: Path


@dataclass(frozen=True)
class PreparedTransportBatchV1:
    batch_id: str
    attempt_nonce_id: str
    source_archive_id: str
    batch_root: Path
    batch_document_bytes: bytes
    batch_header_bytes: bytes
    journals: tuple[PreparedOccurrenceJournalV1, ...]


@dataclass(frozen=True)
class LoadedOccurrenceManifestV1:
    manifest_id: str
    batch_id: str
    input_id: str
    scientific_ordinal: int
    transport_ordinal: int
    occurrence_id: str
    status: str
    failure_code: str | None
    checkpoint_ids: tuple[str, ...]
    result_id: str | None
    work: tuple[tuple[str, int], ...]
    work_tail_unknown: bool
    canonical_bytes: bytes


@dataclass(frozen=True)
class BatchTransportMergeV1:
    merge_id: str
    batch_id: str
    occurrence_manifests: tuple[LoadedOccurrenceManifestV1, ...]
    aggregate_work: tuple[tuple[str, int], ...]
    canonical_bytes: bytes
    physical_pid_diagnostics: tuple[tuple[int, int], ...] = field(
        default=(),
        compare=False,
        repr=False,
    )


@dataclass(frozen=True)
class BatchFailureClosureV1:
    failure_closure_id: str
    batch_id: str
    occurrence_manifests: tuple[LoadedOccurrenceManifestV1, ...]
    aggregate_known_work: tuple[tuple[str, int], ...]
    work_tail_unknown: bool
    canonical_bytes: bytes
    physical_pid_diagnostics: tuple[tuple[int, int], ...] = field(
        default=(),
        compare=False,
        repr=False,
    )


def _real_directory(path: str | os.PathLike[str], *, field: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        _fail(f"{field} must be absolute")
    try:
        info = candidate.lstat()
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise V075TransportInvariantViolation(
            f"{field} must exist as a real directory"
        ) from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        _fail(f"{field} must be a real directory, not a symlink")
    if resolved != candidate:
        _fail(f"{field} must be supplied in resolved form")
    return resolved


def _mkdir_private(path: Path) -> None:
    try:
        os.mkdir(path, mode=0o700)
    except OSError as error:
        raise V075TransportInvariantViolation(
            f"private journal path could not be created exclusively: {path.name}"
        ) from error


def _exclusive_write(path: Path, data: bytes) -> None:
    if type(data) is not bytes:
        _fail("journal writes require bytes")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise V075TransportInvariantViolation(
            f"append-only journal refused an existing or unsafe file: {path.name}"
        ) from error
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        raise
    directory_descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def _read_regular_file(path: Path, *, byte_cap: int, context: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise V075TransportInvariantViolation(
            f"{context} is missing or unsafe"
        ) from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            _fail(f"{context} must be one regular non-symlink file")
        if info.st_size > byte_cap:
            _fail(f"{context} exceeds the byte cap")
        chunks: list[bytes] = []
        remaining = info.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail(f"{context} changed or truncated while being read")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail(f"{context} grew while being read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _quarantine_entry_snapshot_v1(root: Path) -> list[dict[str, Any]]:
    """Describe quarantined bytes without following child-created links."""

    entries: list[dict[str, Any]] = []

    def visit(directory: Path, prefix: tuple[str, ...]) -> None:
        try:
            children = tuple(sorted(os.scandir(directory), key=lambda item: item.name))
        except OSError as error:
            raise V075TransportInvariantViolation(
                "malformed-tail quarantine could not be enumerated"
            ) from error
        for child in children:
            if (
                not child.name
                or child.name in {".", ".."}
                or "/" in child.name
                or "\x00" in child.name
            ):
                _fail("malformed-tail quarantine contains an unsafe name")
            relative = "/".join((*prefix, child.name))
            try:
                info = child.stat(follow_symlinks=False)
            except OSError as error:
                raise V075TransportInvariantViolation(
                    "malformed-tail quarantine entry could not be inspected"
                ) from error
            path = Path(child.path)
            if stat.S_ISREG(info.st_mode):
                raw = _read_regular_file(
                    path,
                    byte_cap=MAX_CHUNK_BYTES,
                    context="quarantined regular file",
                )
                kind = "REGULAR_FILE"
                size = len(raw)
                digest = hashlib.sha256(raw).hexdigest()
            elif stat.S_ISDIR(info.st_mode):
                kind = "DIRECTORY"
                size = 0
                digest = hashlib.sha256(b"DIRECTORY").hexdigest()
            elif stat.S_ISLNK(info.st_mode):
                try:
                    target = os.readlink(path).encode("utf-8")
                except (OSError, UnicodeEncodeError) as error:
                    raise V075TransportInvariantViolation(
                        "quarantined symlink target is not replayable"
                    ) from error
                kind = "SYMLINK"
                size = len(target)
                digest = hashlib.sha256(target).hexdigest()
            else:
                kind = "OTHER_NONREGULAR"
                size = int(info.st_size)
                digest = hashlib.sha256(
                    f"{stat.S_IFMT(info.st_mode)}:{info.st_size}".encode("ascii")
                ).hexdigest()
            entries.append(
                {
                    "content_sha256": digest,
                    "kind": kind,
                    "relative_path": relative,
                    "size_bytes": size,
                }
            )
            if kind == "DIRECTORY":
                visit(path, (*prefix, child.name))

    visit(root, ())
    if len(entries) > 100_000:
        _fail("malformed-tail quarantine exceeds the entry cap")
    return entries


def _quarantine_malformed_tail_v1(
    journal: Path,
    *,
    input_document: dict[str, Any],
) -> tuple[str, bytes]:
    """Move untrusted child output aside and seal a replayable inventory."""

    quarantine = journal / "quarantine"
    _mkdir_private(quarantine)
    quarantined_chunks = quarantine / "chunks"
    _mkdir_private(quarantined_chunks)
    chunks = journal / "chunks"
    try:
        chunk_children = tuple(chunks.iterdir())
    except OSError as error:
        raise V075TransportInvariantViolation(
            "malformed child chunk directory cannot be quarantined"
        ) from error
    for child in chunk_children:
        try:
            os.rename(child, quarantined_chunks / child.name)
        except OSError as error:
            raise V075TransportInvariantViolation(
                "malformed child chunk could not be retained in quarantine"
            ) from error
    protected = {
        "chunks",
        "input.json",
        "journal_header.json",
        "quarantine",
    }
    for child in tuple(journal.iterdir()):
        if child.name in protected:
            continue
        destination = quarantine / f"root--{child.name}"
        try:
            os.rename(child, destination)
        except OSError as error:
            raise V075TransportInvariantViolation(
                "malformed child root output could not be retained"
            ) from error
    entries = _quarantine_entry_snapshot_v1(quarantine)
    body = {
        "batch_id": input_document["batch_id"],
        "entries": entries,
        "input_id": input_document["input_id"],
        "occurrence_id": input_document["occurrence_id"],
        "profile_key": PROFILE_KEY,
        "schema": QUARANTINE_MANIFEST_SCHEMA,
        "scientific_claim": False,
        "scientific_ordinal": input_document["scientific_ordinal"],
        "transport_ordinal": input_document["transport_ordinal"],
        "unknown_malformed_tail": True,
    }
    document, raw = _seal_document(
        QUARANTINE_MANIFEST_DOMAIN,
        body,
        "quarantine_manifest_id",
    )
    _exclusive_write(journal / "quarantine_manifest.json", raw)
    return document["quarantine_manifest_id"], raw


def _verify_quarantine_manifest_v1(
    journal: Path,
    *,
    input_document: dict[str, Any],
    expected_quarantine_id: str,
) -> None:
    raw = _read_regular_file(
        journal / "quarantine_manifest.json",
        byte_cap=MAX_CHUNK_BYTES,
        context="malformed-tail quarantine manifest",
    )
    document = _exact_document(
        _load_canonical_document(
            raw,
            context="malformed-tail quarantine manifest",
        ),
        {
            "batch_id",
            "entries",
            "input_id",
            "occurrence_id",
            "profile_key",
            "quarantine_manifest_id",
            "schema",
            "scientific_claim",
            "scientific_ordinal",
            "transport_ordinal",
            "unknown_malformed_tail",
        },
        context="malformed-tail quarantine manifest",
    )
    identity = _verify_sealed_document(
        document,
        domain=QUARANTINE_MANIFEST_DOMAIN,
        identity_field="quarantine_manifest_id",
        context="malformed-tail quarantine manifest",
    )
    quarantine = _real_directory(
        journal / "quarantine",
        field="malformed-tail quarantine",
    )
    if (
        identity != _cid(expected_quarantine_id, "expected quarantine")
        or document["schema"] != QUARANTINE_MANIFEST_SCHEMA
        or document["profile_key"] != PROFILE_KEY
        or document["scientific_claim"] is not False
        or document["unknown_malformed_tail"] is not True
        or document["batch_id"] != input_document["batch_id"]
        or document["input_id"] != input_document["input_id"]
        or document["occurrence_id"] != input_document["occurrence_id"]
        or document["scientific_ordinal"]
        != input_document["scientific_ordinal"]
        or document["transport_ordinal"]
        != input_document["transport_ordinal"]
        or document["entries"] != _quarantine_entry_snapshot_v1(quarantine)
    ):
        _fail("malformed-tail quarantine replay differs from its manifest")


def _batch_body_v1(
    *,
    attempt_nonce_id: str,
    source_archive_id: str,
    occurrences: tuple[OccurrenceSpecV1, ...],
) -> dict[str, Any]:
    return {
        "attempt_nonce_id": attempt_nonce_id,
        "cache_policy": CACHE_POLICY,
        "occurrences": [
            {
                "occurrence_id": item.occurrence_id,
                "scientific_ordinal": item.scientific_ordinal,
                "target_scope_id": item.target_scope_id,
                "target_payload_id": _domain_id(
                    BATCH_TARGET_COMMITMENT_DOMAIN,
                    item.sealed_target_payload,
                ),
                "transport_ordinal": item.transport_ordinal,
                "worker_key": item.worker_key.value,
            }
            for item in occurrences
        ],
        "ordinal_mapping": ORDINAL_MAPPING,
        "profile_key": PROFILE_KEY,
        "schema": BATCH_SCHEMA,
        "scientific_claim": SCIENTIFIC_CLAIM,
        "source_archive_id": source_archive_id,
    }


def derive_transport_batch_id_v1(
    *,
    attempt_nonce_id: str,
    source_archive_id: str,
    occurrences: tuple[OccurrenceSpecV1, ...],
) -> str:
    nonce = _cid(attempt_nonce_id, "attempt nonce")
    source = _cid(source_archive_id, "source archive")
    schedule = _validate_schedule(occurrences)
    return _domain_id(
        BATCH_DOMAIN,
        _batch_body_v1(
            attempt_nonce_id=nonce,
            source_archive_id=source,
            occurrences=schedule,
        ),
    )


def _validate_schedule(
    occurrences: tuple[OccurrenceSpecV1, ...],
) -> tuple[OccurrenceSpecV1, ...]:
    if (
        type(occurrences) is not tuple
        or not occurrences
        or any(type(item) is not OccurrenceSpecV1 for item in occurrences)
    ):
        _fail("occurrences must be one nonempty tuple of V0-075 specs")
    ordered = tuple(sorted(occurrences, key=lambda item: item.scientific_ordinal))
    if tuple(item.scientific_ordinal for item in ordered) != tuple(
        range(len(ordered))
    ):
        _fail("scientific ordinals must be exactly zero-based and contiguous")
    occurrence_ids = [item.occurrence_id for item in ordered]
    scope_ids = [item.target_scope_id for item in ordered]
    if len(set(occurrence_ids)) != len(occurrence_ids):
        _fail("occurrence identities must be unique")
    if len(set(scope_ids)) != len(scope_ids):
        _fail("target scope identities must be unique")
    return ordered


def _bound_input_v1(
    *,
    spec: OccurrenceSpecV1,
    batch_id: str,
    attempt_nonce_id: str,
    source_archive_id: str,
) -> tuple[str, bytes]:
    body = {
        "attempt_nonce_id": attempt_nonce_id,
        "batch_id": batch_id,
        "cache_policy": CACHE_POLICY,
        "occurrence_id": spec.occurrence_id,
        "ordinal_mapping": ORDINAL_MAPPING,
        "profile_key": PROFILE_KEY,
        "schema": INPUT_SCHEMA,
        "scientific_claim": SCIENTIFIC_CLAIM,
        "scientific_ordinal": spec.scientific_ordinal,
        "source_archive_id": source_archive_id,
        "target_payload": spec.sealed_target_payload,
        "target_scope_id": spec.target_scope_id,
        "transport_ordinal": spec.transport_ordinal,
        "worker_key": spec.worker_key.value,
    }
    document, raw = _seal_document(INPUT_DOMAIN, body, "input_id")
    return document["input_id"], raw


def prepare_transport_batch_v1(
    journal_parent: str | os.PathLike[str],
    *,
    attempt_nonce_id: str,
    source_archive_id: str,
    occurrences: tuple[OccurrenceSpecV1, ...],
) -> PreparedTransportBatchV1:
    """Create all private occurrence journals before any child is submitted."""

    parent = _real_directory(journal_parent, field="journal parent")
    nonce = _cid(attempt_nonce_id, "attempt nonce")
    source = _cid(source_archive_id, "source archive")
    schedule = _validate_schedule(occurrences)
    batch_body = _batch_body_v1(
        attempt_nonce_id=nonce,
        source_archive_id=source,
        occurrences=schedule,
    )
    batch_document, batch_document_bytes = _seal_document(
        BATCH_DOMAIN,
        batch_body,
        "batch_id",
    )
    batch_id = batch_document["batch_id"]
    batch_root = parent / f"v075-{batch_id}"
    _mkdir_private(batch_root)
    _exclusive_write(batch_root / "batch.json", batch_document_bytes)

    bound_inputs = tuple(
        _bound_input_v1(
            spec=spec,
            batch_id=batch_id,
            attempt_nonce_id=nonce,
            source_archive_id=source,
        )
        for spec in schedule
    )
    batch_header_body = {
        "batch_id": batch_id,
        "input_ids": [input_id for input_id, _ in bound_inputs],
        "journal_count": len(schedule),
        "profile_key": PROFILE_KEY,
        "schema": BATCH_HEADER_SCHEMA,
        "scientific_claim": SCIENTIFIC_CLAIM,
    }
    _, batch_header_bytes = _seal_document(
        BATCH_HEADER_DOMAIN,
        batch_header_body,
        "batch_header_id",
    )
    _exclusive_write(batch_root / "batch_header.json", batch_header_bytes)
    journals: list[PreparedOccurrenceJournalV1] = []
    for spec, (input_id, input_bytes) in zip(
        schedule,
        bound_inputs,
        strict=True,
    ):
        journal_path = batch_root / (
            f"occurrence-{spec.transport_ordinal:06d}-{spec.occurrence_id[:16]}"
        )
        _mkdir_private(journal_path)
        _mkdir_private(journal_path / "chunks")
        _exclusive_write(journal_path / "input.json", input_bytes)
        journal_header_body = {
            "batch_id": batch_id,
            "cache_policy": CACHE_POLICY,
            "input_id": input_id,
            "occurrence_id": spec.occurrence_id,
            "ordinal_mapping": ORDINAL_MAPPING,
            "parent_prepared": True,
            "profile_key": PROFILE_KEY,
            "schema": JOURNAL_HEADER_SCHEMA,
            "scientific_claim": SCIENTIFIC_CLAIM,
            "scientific_ordinal": spec.scientific_ordinal,
            "transport_ordinal": spec.transport_ordinal,
        }
        _, journal_header_bytes = _seal_document(
            JOURNAL_HEADER_DOMAIN,
            journal_header_body,
            "journal_header_id",
        )
        _exclusive_write(
            journal_path / "journal_header.json",
            journal_header_bytes,
        )
        journals.append(
            PreparedOccurrenceJournalV1(
                scientific_ordinal=spec.scientific_ordinal,
                transport_ordinal=spec.transport_ordinal,
                occurrence_id=spec.occurrence_id,
                input_id=input_id,
                input_bytes=input_bytes,
                journal_path=journal_path,
            )
        )
    return PreparedTransportBatchV1(
        batch_id=batch_id,
        attempt_nonce_id=nonce,
        source_archive_id=source,
        batch_root=batch_root,
        batch_document_bytes=batch_document_bytes,
        batch_header_bytes=batch_header_bytes,
        journals=tuple(journals),
    )


def _parse_bound_input_v1(
    raw: bytes,
    *,
    expected_input_id: str,
    expected_batch_id: str,
) -> dict[str, Any]:
    document = _exact_document(
        _load_canonical_document(raw, context="occurrence input"),
        {
            "attempt_nonce_id",
            "batch_id",
            "cache_policy",
            "input_id",
            "occurrence_id",
            "ordinal_mapping",
            "profile_key",
            "schema",
            "scientific_claim",
            "scientific_ordinal",
            "source_archive_id",
            "target_payload",
            "target_scope_id",
            "transport_ordinal",
            "worker_key",
        },
        context="occurrence input",
    )
    if document["schema"] != INPUT_SCHEMA or document["profile_key"] != PROFILE_KEY:
        _fail("occurrence input schema/profile mismatch")
    if (
        document["scientific_claim"] is not False
        or document["cache_policy"] != CACHE_POLICY
        or document["ordinal_mapping"] != ORDINAL_MAPPING
    ):
        _fail("occurrence input violates fixture/no-reuse semantics")
    input_id = _verify_sealed_document(
        document,
        domain=INPUT_DOMAIN,
        identity_field="input_id",
        context="occurrence input",
    )
    if input_id != _cid(expected_input_id, "expected input"):
        _fail("occurrence input external identity mismatch")
    if document["batch_id"] != _cid(expected_batch_id, "expected batch"):
        _fail("occurrence input batch mismatch")
    scientific = document["scientific_ordinal"]
    transport = document["transport_ordinal"]
    if (
        type(scientific) is not int
        or scientific < 0
        or type(transport) is not int
        or transport != scientific + 1
    ):
        _fail("occurrence input ordinal +1 mapping mismatch")
    _cid(document["occurrence_id"], "occurrence identity")
    _cid(document["target_scope_id"], "target scope")
    _cid(document["source_archive_id"], "source archive")
    _cid(document["attempt_nonce_id"], "attempt nonce")
    _validate_fixture_payload(document["target_payload"])
    try:
        RegisteredFixtureWorkerV1(document["worker_key"])
    except (TypeError, ValueError) as error:
        raise V075TransportInvariantViolation(
            "occurrence input worker is not registered"
        ) from error
    return document


def _verify_parent_prepared_journal_v1(
    journal_path: str,
    *,
    input_bytes: bytes,
    input_document: dict[str, Any],
) -> Path:
    journal = _real_directory(journal_path, field="occurrence journal")
    chunks = _real_directory(journal / "chunks", field="occurrence chunks")
    if chunks.parent != journal:
        _fail("occurrence chunks escaped the private journal")
    stored_input = _read_regular_file(
        journal / "input.json",
        byte_cap=MAX_INPUT_BYTES,
        context="stored occurrence input",
    )
    if stored_input != input_bytes:
        _fail("stored occurrence input differs from submitted canonical bytes")
    header_raw = _read_regular_file(
        journal / "journal_header.json",
        byte_cap=64 * 1024,
        context="journal header",
    )
    header = _exact_document(
        _load_canonical_document(header_raw, context="journal header"),
        {
            "batch_id",
            "cache_policy",
            "input_id",
            "journal_header_id",
            "occurrence_id",
            "ordinal_mapping",
            "parent_prepared",
            "profile_key",
            "schema",
            "scientific_claim",
            "scientific_ordinal",
            "transport_ordinal",
        },
        context="journal header",
    )
    _verify_sealed_document(
        header,
        domain=JOURNAL_HEADER_DOMAIN,
        identity_field="journal_header_id",
        context="journal header",
    )
    expected = {
        "batch_id": input_document["batch_id"],
        "cache_policy": CACHE_POLICY,
        "input_id": input_document["input_id"],
        "occurrence_id": input_document["occurrence_id"],
        "ordinal_mapping": ORDINAL_MAPPING,
        "parent_prepared": True,
        "profile_key": PROFILE_KEY,
        "schema": JOURNAL_HEADER_SCHEMA,
        "scientific_claim": False,
        "scientific_ordinal": input_document["scientific_ordinal"],
        "transport_ordinal": input_document["transport_ordinal"],
    }
    body = dict(header)
    del body["journal_header_id"]
    if body != expected:
        _fail("journal header does not bind the submitted occurrence")
    return journal


def _checkpoint_document_v1(
    input_document: dict[str, Any],
    *,
    sequence: int,
    stage_index: int,
    stage: str,
    previous_checkpoint_id: str | None,
    event: dict[str, Any],
) -> tuple[str, bytes]:
    body = {
        "batch_id": input_document["batch_id"],
        "event": _canonical_clone(event, "checkpoint event"),
        "input_id": input_document["input_id"],
        "occurrence_id": input_document["occurrence_id"],
        "previous_checkpoint_ref": (
            _typed_null("FIRST_CHECKPOINT")
            if previous_checkpoint_id is None
            else _content_ref(previous_checkpoint_id)
        ),
        "profile_key": PROFILE_KEY,
        "schema": CHECKPOINT_SCHEMA,
        "scientific_claim": False,
        "scientific_ordinal": input_document["scientific_ordinal"],
        "sequence": sequence,
        "stage": stage,
        "stage_index": stage_index,
        "transport_ordinal": input_document["transport_ordinal"],
    }
    document, raw = _seal_document(
        CHECKPOINT_DOMAIN,
        body,
        "checkpoint_id",
    )
    return document["checkpoint_id"], raw


def _append_cas_document_v1(
    journal: Path,
    *,
    content_id_value: str,
    raw: bytes,
) -> None:
    if len(raw) > MAX_CHUNK_BYTES:
        _fail("CAS chunk exceeds the V0-075 byte cap")
    _exclusive_write(
        journal / "chunks" / f"{_cid(content_id_value, 'CAS chunk')}.json",
        raw,
    )


def _fixture_result_v1(
    input_document: dict[str, Any],
    *,
    sequence: int,
) -> tuple[str, bytes]:
    payload = _validate_fixture_payload(input_document["target_payload"])
    body = {
        "batch_id": input_document["batch_id"],
        "fixture_label": payload["fixture_label"],
        "fixture_sum": sum(payload["values"]),
        "input_id": input_document["input_id"],
        "occurrence_id": input_document["occurrence_id"],
        "payload_sha256": hashlib.sha256(
            canonical_json_bytes(payload)
        ).hexdigest(),
        "profile_key": PROFILE_KEY,
        "schema": FIXTURE_RESULT_SCHEMA,
        "scientific_claim": False,
        "scientific_ordinal": input_document["scientific_ordinal"],
        "sequence": sequence,
        "transport_ordinal": input_document["transport_ordinal"],
    }
    document, raw = _seal_document(
        FIXTURE_RESULT_DOMAIN,
        body,
        "result_id",
    )
    return document["result_id"], raw


def _work_document(
    *,
    submit_attempted: int,
    submitted: int,
    process_launches: int,
    checkpoint_count: int,
    worker_events: int,
    chunks: list[tuple[str, str, str, int, int]],
) -> list[dict[str, Any]]:
    values = {
        "control.parent_journal_prepared": 1,
        "control.child_submit_attempts": submit_attempted,
        "control.child_submitted": submitted,
        "process.child_process_launches": process_launches,
        "fixture.stage_checkpoints_completed": checkpoint_count,
        "fixture.worker_events": worker_events,
        "io.cas_chunks_written": len(chunks),
        "io.cas_output_bytes": sum(item[4] for item in chunks),
    }
    return [{"path": path, "value": values[path]} for path in _WORK_PATHS]


def _manifest_document_v1(
    input_document: dict[str, Any],
    *,
    closure_origin: str,
    status: str,
    failure_code: str | None,
    checkpoint_ids: list[str],
    result_id: str | None,
    chunks: list[tuple[str, str, str, int, int]],
    work: list[dict[str, Any]],
    work_tail_unknown: bool,
    superseded_manifest_id: str | None = None,
    quarantine_manifest_id: str | None = None,
) -> tuple[str, bytes]:
    body = {
        "batch_id": input_document["batch_id"],
        "cache_policy": CACHE_POLICY,
        "checkpoint_ids": checkpoint_ids,
        "chunk_manifest": [
            {
                "chunk_id": chunk_id,
                "domain_tag": domain,
                "kind": kind,
                "sequence": sequence,
                "size_bytes": size,
            }
            for chunk_id, domain, kind, sequence, size in chunks
        ],
        "closure_origin": closure_origin,
        "failure_code": (
            _typed_null("SUCCESS")
            if failure_code is None
            else _token(failure_code, "failure code")
        ),
        "input_id": input_document["input_id"],
        "occurrence_id": input_document["occurrence_id"],
        "ordinal_mapping": ORDINAL_MAPPING,
        "profile_key": PROFILE_KEY,
        "quarantine_ref": (
            _typed_null("NO_QUARANTINED_TAIL")
            if quarantine_manifest_id is None
            else _content_ref(quarantine_manifest_id)
        ),
        "result_ref": (
            _typed_null("NO_RESULT")
            if result_id is None
            else _content_ref(result_id)
        ),
        "schema": OCCURRENCE_MANIFEST_SCHEMA,
        "scientific_claim": False,
        "scientific_ordinal": input_document["scientific_ordinal"],
        "status": status,
        "superseded_manifest_ref": (
            _typed_null("NO_SUPERSEDED_MANIFEST")
            if superseded_manifest_id is None
            else _content_ref(superseded_manifest_id)
        ),
        "target_scope_id": input_document["target_scope_id"],
        "transport_ordinal": input_document["transport_ordinal"],
        "work": work,
        "work_tail_unknown": work_tail_unknown,
    }
    document, raw = _seal_document(
        OCCURRENCE_MANIFEST_DOMAIN,
        body,
        "manifest_id",
    )
    return document["manifest_id"], raw


def _execute_child_fixture_v1(
    request_bytes: bytes,
) -> tuple[bytes, int]:
    """Spawn target.  Its sole argument is one canonical byte document."""

    request = _exact_document(
        _load_canonical_document(request_bytes, context="child request"),
        {
            "expected_batch_id",
            "expected_input_id",
            "identity_bearing",
            "input_document",
            "journal_path",
            "physical_capability_only",
            "profile_key",
            "schema",
        },
        context="child request",
    )
    if (
        request["schema"] != CHILD_REQUEST_SCHEMA
        or request["profile_key"] != PROFILE_KEY
        or request["identity_bearing"] is not False
        or request["physical_capability_only"] is not True
    ):
        _fail("child request violates the nonidentity capability profile")
    input_bytes = canonical_json_bytes(request["input_document"])
    document = _parse_bound_input_v1(
        input_bytes,
        expected_input_id=request["expected_input_id"],
        expected_batch_id=request["expected_batch_id"],
    )
    journal = _verify_parent_prepared_journal_v1(
        _token(request["journal_path"], "child journal path"),
        input_bytes=input_bytes,
        input_document=document,
    )
    chunks: list[tuple[str, str, str, int, int]] = []
    checkpoints: list[str] = []

    def checkpoint(stage_index: int, stage: str, event: dict[str, Any]) -> None:
        sequence = len(chunks) + 1
        checkpoint_id, raw = _checkpoint_document_v1(
            document,
            sequence=sequence,
            stage_index=stage_index,
            stage=stage,
            previous_checkpoint_id=(checkpoints[-1] if checkpoints else None),
            event=event,
        )
        _append_cas_document_v1(
            journal,
            content_id_value=checkpoint_id,
            raw=raw,
        )
        checkpoints.append(checkpoint_id)
        chunks.append(
            (
                checkpoint_id,
                CHECKPOINT_DOMAIN,
                "CHECKPOINT",
                sequence,
                len(raw),
            )
        )

    checkpoint(0, "INPUT_ACCEPTED", {"canonical_bytes_verified": True})
    checkpoint(
        1,
        "SOURCE_BOUND",
        {"source_archive_id": document["source_archive_id"]},
    )
    worker = RegisteredFixtureWorkerV1(document["worker_key"])
    if worker is RegisteredFixtureWorkerV1.FAIL_AFTER_SOURCE_BINDING_V1:
        checkpoint(
            2,
            "FAILURE_CLOSED",
            {"registered_failure": "FAIL_AFTER_SOURCE_BINDING_V1"},
        )
        work = _work_document(
            submit_attempted=1,
            submitted=1,
            process_launches=1,
            checkpoint_count=len(checkpoints),
            worker_events=1,
            chunks=chunks,
        )
        _, manifest_raw = _manifest_document_v1(
            document,
            closure_origin="CHILD",
            status="FAILURE",
            failure_code="REGISTERED_FIXTURE_FAILURE",
            checkpoint_ids=checkpoints,
            result_id=None,
            chunks=chunks,
            work=work,
            work_tail_unknown=False,
        )
        _exclusive_write(journal / "manifest.json", manifest_raw)
        return manifest_raw, os.getpid()

    checkpoint(
        2,
        "FIXTURE_EXECUTED",
        {"registered_worker": worker.value},
    )
    result_sequence = len(chunks) + 1
    result_id, result_raw = _fixture_result_v1(
        document,
        sequence=result_sequence,
    )
    _append_cas_document_v1(
        journal,
        content_id_value=result_id,
        raw=result_raw,
    )
    chunks.append(
        (
            result_id,
            FIXTURE_RESULT_DOMAIN,
            "FIXTURE_RESULT",
            result_sequence,
            len(result_raw),
        )
    )
    checkpoint(
        3,
        "OUTPUT_SEALED",
        {"result_id": result_id},
    )
    work = _work_document(
        submit_attempted=1,
        submitted=1,
        process_launches=1,
        checkpoint_count=len(checkpoints),
        worker_events=1,
        chunks=chunks,
    )
    _, manifest_raw = _manifest_document_v1(
        document,
        closure_origin="CHILD",
        status="SUCCESS",
        failure_code=None,
        checkpoint_ids=checkpoints,
        result_id=result_id,
        chunks=chunks,
        work=work,
        work_tail_unknown=False,
    )
    _exclusive_write(journal / "manifest.json", manifest_raw)
    return manifest_raw, os.getpid()


def _child_request_bytes_v1(
    journal: PreparedOccurrenceJournalV1,
    *,
    batch_id: str,
) -> bytes:
    """Build a non-identity execution capability as strict canonical bytes."""

    input_document = _load_canonical_document(
        journal.input_bytes,
        context="prepared occurrence input",
    )
    return canonical_json_bytes(
        {
            "expected_batch_id": batch_id,
            "expected_input_id": journal.input_id,
            "identity_bearing": False,
            "input_document": input_document,
            "journal_path": str(journal.journal_path),
            "physical_capability_only": True,
            "profile_key": PROFILE_KEY,
            "schema": CHILD_REQUEST_SCHEMA,
        }
    )


def _load_chunk_v1(
    raw: bytes,
    *,
    expected_input: dict[str, Any],
    expected_filename_id: str,
) -> tuple[dict[str, Any], str, str, int]:
    document = _load_canonical_document(raw, context="CAS chunk")
    schema = document.get("schema")
    if schema not in _CHUNK_DOMAINS:
        _fail("CAS chunk uses an unregistered V0-075 schema")
    if schema == CHECKPOINT_SCHEMA:
        _exact_document(
            document,
            {
                "batch_id",
                "checkpoint_id",
                "event",
                "input_id",
                "occurrence_id",
                "previous_checkpoint_ref",
                "profile_key",
                "schema",
                "scientific_claim",
                "scientific_ordinal",
                "sequence",
                "stage",
                "stage_index",
                "transport_ordinal",
            },
            context="stage checkpoint",
        )
    else:
        _exact_document(
            document,
            {
                "batch_id",
                "fixture_label",
                "fixture_sum",
                "input_id",
                "occurrence_id",
                "payload_sha256",
                "profile_key",
                "result_id",
                "schema",
                "scientific_claim",
                "scientific_ordinal",
                "sequence",
                "transport_ordinal",
            },
            context="fixture result",
        )
    domain, identity_field, kind = _CHUNK_DOMAINS[schema]
    identity = _verify_sealed_document(
        document,
        domain=domain,
        identity_field=identity_field,
        context="CAS chunk",
    )
    if identity != expected_filename_id:
        _fail("CAS filename/content identity mismatch")
    if (
        document.get("profile_key") != PROFILE_KEY
        or document.get("scientific_claim") is not False
        or document.get("batch_id") != expected_input["batch_id"]
        or document.get("input_id") != expected_input["input_id"]
        or document.get("occurrence_id") != expected_input["occurrence_id"]
        or document.get("scientific_ordinal")
        != expected_input["scientific_ordinal"]
        or document.get("transport_ordinal")
        != expected_input["transport_ordinal"]
    ):
        _fail("CAS chunk binding mismatch")
    sequence = document.get("sequence")
    if type(sequence) is not int or sequence < 1:
        _fail("CAS chunk sequence must be positive")
    if schema == FIXTURE_RESULT_SCHEMA:
        payload = _validate_fixture_payload(expected_input["target_payload"])
        if (
            document["fixture_label"] != payload["fixture_label"]
            or document["fixture_sum"] != sum(payload["values"])
            or document["payload_sha256"]
            != hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        ):
            _fail("fixture result is not a deterministic function of the input")
    return document, domain, kind, sequence


def _scan_chunks_v1(
    journal: Path,
    *,
    expected_input: dict[str, Any],
) -> list[tuple[str, str, str, int, int, dict[str, Any]]]:
    chunks_path = _real_directory(
        journal / "chunks",
        field="occurrence chunks",
    )
    entries: list[tuple[str, str, str, int, int, dict[str, Any]]] = []
    try:
        children = tuple(chunks_path.iterdir())
    except OSError as error:
        raise V075TransportInvariantViolation(
            "CAS directory could not be enumerated"
        ) from error
    for path in children:
        try:
            info = path.lstat()
        except OSError as error:
            raise V075TransportInvariantViolation(
                "CAS entry could not be inspected"
            ) from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            _fail("CAS directory contains a non-regular or symlink entry")
        if path.suffix != ".json":
            _fail("CAS directory contains an unregistered filename")
        filename_id = _cid(path.stem, "CAS filename")
        raw = _read_regular_file(
            path,
            byte_cap=MAX_CHUNK_BYTES,
            context="CAS chunk",
        )
        document, domain, kind, sequence = _load_chunk_v1(
            raw,
            expected_input=expected_input,
            expected_filename_id=filename_id,
        )
        entries.append(
            (
                filename_id,
                domain,
                kind,
                sequence,
                len(raw),
                document,
            )
        )
    entries.sort(key=lambda item: item[3])
    if [item[3] for item in entries] != list(range(1, len(entries) + 1)):
        _fail("CAS chunk sequences must be unique and contiguous")
    return entries


def _validate_checkpoint_chain_v1(
    entries: list[tuple[str, str, str, int, int, dict[str, Any]]],
    *,
    expected_input: dict[str, Any],
    status: str,
    closure_origin: str,
) -> tuple[list[str], str | None]:
    checkpoints = [item for item in entries if item[2] == "CHECKPOINT"]
    results = [item for item in entries if item[2] == "FIXTURE_RESULT"]
    previous: str | None = None
    stages: list[str] = []
    for entry in checkpoints:
        document = entry[5]
        reference = _validate_typed_ref(
            document.get("previous_checkpoint_ref"),
            field="previous checkpoint",
            allow_content=True,
        )
        if reference != previous:
            _fail("checkpoint predecessor chain mismatch")
        expected_predecessor = (
            _typed_null("FIRST_CHECKPOINT")
            if previous is None
            else _content_ref(previous)
        )
        if document["previous_checkpoint_ref"] != expected_predecessor:
            _fail("checkpoint predecessor uses a noncanonical typed reference")
        previous = entry[0]
        stage = document["stage"]
        stage_index = document["stage_index"]
        event = document["event"]
        if stage == "INPUT_ACCEPTED":
            if (
                stage_index != 0
                or event != {"canonical_bytes_verified": True}
            ):
                _fail("INPUT_ACCEPTED checkpoint semantics mismatch")
        elif stage == "SOURCE_BOUND":
            if (
                stage_index != 1
                or event
                != {"source_archive_id": expected_input["source_archive_id"]}
            ):
                _fail("SOURCE_BOUND checkpoint semantics mismatch")
        elif stage == "FIXTURE_EXECUTED":
            if (
                stage_index != 2
                or expected_input["worker_key"]
                != RegisteredFixtureWorkerV1.SAFE_HASH_V1.value
                or event
                != {"registered_worker": RegisteredFixtureWorkerV1.SAFE_HASH_V1.value}
            ):
                _fail("FIXTURE_EXECUTED checkpoint semantics mismatch")
        elif stage == "OUTPUT_SEALED":
            if stage_index != 3:
                _fail("OUTPUT_SEALED checkpoint index mismatch")
            event_document = _exact_document(
                event,
                {"result_id"},
                context="OUTPUT_SEALED event",
            )
            _cid(event_document["result_id"], "sealed result")
        elif stage == "FAILURE_CLOSED":
            if (
                stage_index != 2
                or expected_input["worker_key"]
                != RegisteredFixtureWorkerV1.FAIL_AFTER_SOURCE_BINDING_V1.value
                or event
                != {"registered_failure": "FAIL_AFTER_SOURCE_BINDING_V1"}
            ):
                _fail("FAILURE_CLOSED checkpoint semantics mismatch")
        else:
            _fail("checkpoint stage is not registered")
        stages.append(stage)
    kinds = [item[2] for item in entries]
    if closure_origin == "CHILD" and status == "SUCCESS":
        if (
            tuple(stages) != _SUCCESS_STAGES
            or kinds
            != [
                "CHECKPOINT",
                "CHECKPOINT",
                "CHECKPOINT",
                "FIXTURE_RESULT",
                "CHECKPOINT",
            ]
            or len(results) != 1
        ):
            _fail("successful child manifest lacks the complete stage/result chain")
    elif closure_origin == "CHILD" and status == "FAILURE":
        if (
            tuple(stages) != _FAILURE_STAGES
            or kinds != ["CHECKPOINT", "CHECKPOINT", "CHECKPOINT"]
            or results
        ):
            _fail("registered child failure has an invalid checkpoint chain")
    elif closure_origin == "PARENT":
        success_prefix = tuple(stages) == _SUCCESS_STAGES[: len(stages)]
        failure_prefix = tuple(stages) == _FAILURE_STAGES[: len(stages)]
        success_kind_prefix = [
            "CHECKPOINT",
            "CHECKPOINT",
            "CHECKPOINT",
            "FIXTURE_RESULT",
            "CHECKPOINT",
        ][: len(kinds)]
        failure_kind_prefix = ["CHECKPOINT", "CHECKPOINT", "CHECKPOINT"][
            : len(kinds)
        ]
        if not (
            (success_prefix and kinds == success_kind_prefix)
            or (failure_prefix and kinds == failure_kind_prefix)
        ):
            _fail("parent failure did not retain a valid checkpoint prefix")
        if len(results) > 1:
            _fail("parent failure retained multiple fixture results")
    else:
        _fail("occurrence manifest closure origin/status is invalid")
    result_id = None if not results else results[0][0]
    if stages and stages[-1] == "OUTPUT_SEALED":
        if checkpoints[-1][5]["event"]["result_id"] != result_id:
            _fail("OUTPUT_SEALED checkpoint references the wrong result")
    return [item[0] for item in checkpoints], result_id


def _parse_work_v1(
    value: Any,
    *,
    context: str,
) -> tuple[tuple[str, int], ...]:
    if type(value) is not list:
        _fail(f"{context} must be one work list")
    parsed: list[tuple[str, int]] = []
    for index, entry in enumerate(value):
        item = _exact_document(
            entry,
            {"path", "value"},
            context=f"{context}[{index}]",
        )
        path = item["path"]
        amount = item["value"]
        if path not in _WORK_PATHS:
            _fail(f"{context} contains an unregistered work path")
        if type(amount) is not int or amount < 0:
            _fail(f"{context} values must be nonnegative integers")
        parsed.append((path, amount))
    if tuple(path for path, _ in parsed) != _WORK_PATHS:
        _fail(f"{context} paths must be complete and canonically ordered")
    return tuple(parsed)


def strict_load_occurrence_manifest_v1(
    journal_path: str | os.PathLike[str],
    *,
    expected_input_bytes: bytes,
    expected_input_id: str,
    expected_batch_id: str,
    returned_manifest_bytes: bytes | None = None,
) -> LoadedOccurrenceManifestV1:
    """Replay a journal from bytes and disk, rejecting omissions and extras."""

    input_document = _parse_bound_input_v1(
        expected_input_bytes,
        expected_input_id=expected_input_id,
        expected_batch_id=expected_batch_id,
    )
    journal = _verify_parent_prepared_journal_v1(
        str(journal_path),
        input_bytes=expected_input_bytes,
        input_document=input_document,
    )
    failure_path = journal / "failure_manifest.json"
    child_path = journal / "manifest.json"
    selected_path = failure_path if failure_path.exists() else child_path
    selected_raw = _read_regular_file(
        selected_path,
        byte_cap=MAX_CHUNK_BYTES,
        context="occurrence manifest",
    )
    if returned_manifest_bytes is not None:
        if type(returned_manifest_bytes) is not bytes:
            _fail("returned occurrence manifest must be canonical bytes")
        if selected_raw != returned_manifest_bytes:
            _fail("returned occurrence manifest differs from durable journal")
    manifest = _exact_document(
        _load_canonical_document(selected_raw, context="occurrence manifest"),
        {
            "batch_id",
            "cache_policy",
            "checkpoint_ids",
            "chunk_manifest",
            "closure_origin",
            "failure_code",
            "input_id",
            "manifest_id",
            "occurrence_id",
            "ordinal_mapping",
            "profile_key",
            "quarantine_ref",
            "result_ref",
            "schema",
            "scientific_claim",
            "scientific_ordinal",
            "status",
            "superseded_manifest_ref",
            "target_scope_id",
            "transport_ordinal",
            "work",
            "work_tail_unknown",
        },
        context="occurrence manifest",
    )
    manifest_id = _verify_sealed_document(
        manifest,
        domain=OCCURRENCE_MANIFEST_DOMAIN,
        identity_field="manifest_id",
        context="occurrence manifest",
    )
    if (
        manifest["schema"] != OCCURRENCE_MANIFEST_SCHEMA
        or manifest["profile_key"] != PROFILE_KEY
        or manifest["scientific_claim"] is not False
        or manifest["cache_policy"] != CACHE_POLICY
        or manifest["ordinal_mapping"] != ORDINAL_MAPPING
    ):
        _fail("occurrence manifest schema/profile semantics mismatch")
    for field in (
        "batch_id",
        "input_id",
        "occurrence_id",
        "scientific_ordinal",
        "target_scope_id",
        "transport_ordinal",
    ):
        if manifest[field] != input_document[field]:
            _fail(f"occurrence manifest {field} binding mismatch")
    status = manifest["status"]
    origin = manifest["closure_origin"]
    if status not in {"SUCCESS", "FAILURE"} or origin not in {"CHILD", "PARENT"}:
        _fail("occurrence manifest status/origin is invalid")
    if type(manifest["work_tail_unknown"]) is not bool:
        _fail("work-tail marker must be boolean")
    if status == "SUCCESS":
        if origin != "CHILD" or manifest["work_tail_unknown"]:
            _fail("only a complete child journal may be successful")
        failure_code = _validate_typed_ref(
            manifest["failure_code"],
            field="failure code",
            allow_content=False,
        )
        if failure_code is not None:
            _fail("successful occurrence cannot carry a failure code")
        if manifest["failure_code"] != _typed_null("SUCCESS"):
            _fail("successful occurrence uses a noncanonical failure null")
        failure_label: str | None = None
    else:
        if type(manifest["failure_code"]) is not str:
            _fail("failed occurrence must carry a registered failure string")
        failure_label = _token(manifest["failure_code"], "failure code")
        permitted_failure_codes = (
            {"REGISTERED_FIXTURE_FAILURE"}
            if origin == "CHILD"
            else {
                "PROCESS_POOL_START_FAILURE",
                "PROCESS_SUBMIT_FAILURE",
                "PROCESS_BOUNDARY_FAILURE",
                "MALFORMED_CHILD_JOURNAL",
            }
        )
        if failure_label not in permitted_failure_codes:
            _fail("failed occurrence carries an unregistered origin-specific code")
        if origin == "CHILD" and manifest["work_tail_unknown"]:
            _fail("registered child failure must close an exact work tail")

    quarantine_id = _validate_typed_ref(
        manifest["quarantine_ref"],
        field="quarantine reference",
        allow_content=True,
    )
    malformed_tail = (
        origin == "PARENT"
        and failure_label == "MALFORMED_CHILD_JOURNAL"
    )
    if malformed_tail:
        if (
            quarantine_id is None
            or manifest["quarantine_ref"] != _content_ref(quarantine_id)
            or manifest["work_tail_unknown"] is not True
        ):
            _fail("malformed child failure lacks its typed quarantine")
        _verify_quarantine_manifest_v1(
            journal,
            input_document=input_document,
            expected_quarantine_id=quarantine_id,
        )
    elif (
        quarantine_id is not None
        or manifest["quarantine_ref"]
        != _typed_null("NO_QUARANTINED_TAIL")
    ):
        _fail("only a malformed child failure may carry quarantine")

    entries = _scan_chunks_v1(journal, expected_input=input_document)
    expected_chunk_manifest = [
        {
            "chunk_id": item[0],
            "domain_tag": item[1],
            "kind": item[2],
            "sequence": item[3],
            "size_bytes": item[4],
        }
        for item in entries
    ]
    if manifest["chunk_manifest"] != expected_chunk_manifest:
        _fail("occurrence chunk manifest omits, reorders, or alters CAS files")
    checkpoint_ids, scanned_result_id = _validate_checkpoint_chain_v1(
        entries,
        expected_input=input_document,
        status=status,
        closure_origin=origin,
    )
    if manifest["checkpoint_ids"] != checkpoint_ids:
        _fail("occurrence manifest checkpoint list mismatch")
    result_id = _validate_typed_ref(
        manifest["result_ref"],
        field="result reference",
        allow_content=True,
    )
    if result_id != scanned_result_id:
        _fail("occurrence result reference does not match CAS")
    expected_result_ref = (
        _typed_null("NO_RESULT")
        if scanned_result_id is None
        else _content_ref(scanned_result_id)
    )
    if manifest["result_ref"] != expected_result_ref:
        _fail("occurrence result uses a noncanonical typed reference")
    superseded_id = _validate_typed_ref(
        manifest["superseded_manifest_ref"],
        field="superseded manifest reference",
        allow_content=True,
    )
    expected_superseded_ref = (
        _typed_null("NO_SUPERSEDED_MANIFEST")
        if superseded_id is None
        else _content_ref(superseded_id)
    )
    if manifest["superseded_manifest_ref"] != expected_superseded_ref:
        _fail("superseded manifest uses a noncanonical typed reference")
    root_names = {item.name for item in journal.iterdir()}
    expected_root_names = {
        "chunks",
        "input.json",
        "journal_header.json",
        selected_path.name,
    }
    if malformed_tail:
        expected_root_names.update(
            {"quarantine", "quarantine_manifest.json"}
        )
    if superseded_id is not None:
        if selected_path != failure_path:
            _fail("only a parent failure may supersede a child manifest")
        superseded_raw = _read_regular_file(
            child_path,
            byte_cap=MAX_CHUNK_BYTES,
            context="superseded child manifest",
        )
        superseded = _load_canonical_document(
            superseded_raw,
            context="superseded child manifest",
        )
        actual_superseded = _verify_sealed_document(
            superseded,
            domain=OCCURRENCE_MANIFEST_DOMAIN,
            identity_field="manifest_id",
            context="superseded child manifest",
        )
        if actual_superseded != superseded_id:
            _fail("superseded child manifest identity mismatch")
        expected_root_names.add("manifest.json")
    if root_names != expected_root_names:
        _fail("occurrence journal contains unlisted root files")
    work = _parse_work_v1(manifest["work"], context="occurrence work")
    work_map = dict(work)
    expected_work = dict(
        _parse_work_v1(
            _work_document(
                submit_attempted=work_map["control.child_submit_attempts"],
                submitted=work_map["control.child_submitted"],
                process_launches=work_map["process.child_process_launches"],
                checkpoint_count=len(checkpoint_ids),
                worker_events=work_map["fixture.worker_events"],
                chunks=[
                    (item[0], item[1], item[2], item[3], item[4])
                    for item in entries
                ],
            ),
            context="recomputed occurrence work",
        )
    )
    for exact_path in (
        "control.parent_journal_prepared",
        "fixture.stage_checkpoints_completed",
        "io.cas_chunks_written",
        "io.cas_output_bytes",
    ):
        if work_map[exact_path] != expected_work[exact_path]:
            _fail(f"occurrence work mismatch at {exact_path}")
    if origin == "CHILD":
        required = {
            "control.child_submit_attempts": 1,
            "control.child_submitted": 1,
            "process.child_process_launches": 1,
            "fixture.worker_events": 1,
        }
        if any(work_map[path] != value for path, value in required.items()):
            _fail("child occurrence work does not match executed semantics")
    else:
        parent_profiles = {
            "PROCESS_POOL_START_FAILURE": (0, 0, False),
            "PROCESS_SUBMIT_FAILURE": (1, 0, False),
            "PROCESS_BOUNDARY_FAILURE": (1, 1, True),
            "MALFORMED_CHILD_JOURNAL": (1, 1, True),
        }
        expected_attempted, expected_submitted, expected_unknown = (
            parent_profiles[failure_label]
        )
        if (
            work_map["control.child_submit_attempts"] != expected_attempted
            or work_map["control.child_submitted"] != expected_submitted
            or work_map["process.child_process_launches"] not in (
                (0, 1)
                if failure_label
                in {"PROCESS_BOUNDARY_FAILURE", "MALFORMED_CHILD_JOURNAL"}
                else (0,)
            )
            or work_map["fixture.worker_events"] != 0
            or manifest["work_tail_unknown"] is not expected_unknown
        ):
            _fail("parent occurrence work does not match its failure profile")
    return LoadedOccurrenceManifestV1(
        manifest_id=manifest_id,
        batch_id=manifest["batch_id"],
        input_id=manifest["input_id"],
        scientific_ordinal=manifest["scientific_ordinal"],
        transport_ordinal=manifest["transport_ordinal"],
        occurrence_id=manifest["occurrence_id"],
        status=status,
        failure_code=failure_label,
        checkpoint_ids=tuple(checkpoint_ids),
        result_id=result_id,
        work=work,
        work_tail_unknown=manifest["work_tail_unknown"],
        canonical_bytes=selected_raw,
    )


def _parent_failure_manifest_v1(
    journal: PreparedOccurrenceJournalV1,
    *,
    batch_id: str,
    failure_code: str,
    submit_attempted: int,
    submitted: int,
    process_launches: int,
    work_tail_unknown: bool,
) -> LoadedOccurrenceManifestV1:
    input_document = _parse_bound_input_v1(
        journal.input_bytes,
        expected_input_id=journal.input_id,
        expected_batch_id=batch_id,
    )
    path = _real_directory(journal.journal_path, field="occurrence journal")
    superseded_id: str | None = None
    quarantine_manifest_id: str | None = None
    try:
        entries = _scan_chunks_v1(path, expected_input=input_document)
        checkpoint_ids, result_id = _validate_checkpoint_chain_v1(
            entries,
            expected_input=input_document,
            status="FAILURE",
            closure_origin="PARENT",
        )
        chunks = [
            (item[0], item[1], item[2], item[3], item[4])
            for item in entries
        ]
        child_manifest_path = path / "manifest.json"
        root_names = {item.name for item in path.iterdir()}
        allowed_root_names = {
            "chunks",
            "input.json",
            "journal_header.json",
        }
        if child_manifest_path.exists():
            allowed_root_names.add("manifest.json")
            child_raw = _read_regular_file(
                child_manifest_path,
                byte_cap=MAX_CHUNK_BYTES,
                context="superseded child manifest",
            )
            child_document = _load_canonical_document(
                child_raw,
                context="superseded child manifest",
            )
            superseded_id = _verify_sealed_document(
                child_document,
                domain=OCCURRENCE_MANIFEST_DOMAIN,
                identity_field="manifest_id",
                context="superseded child manifest",
            )
        if root_names != allowed_root_names:
            _fail("malformed child journal contains unregistered root output")
    except V075TransportInvariantViolation:
        quarantine_manifest_id, _ = _quarantine_malformed_tail_v1(
            path,
            input_document=input_document,
        )
        failure_code = "MALFORMED_CHILD_JOURNAL"
        work_tail_unknown = True
        entries = []
        checkpoint_ids = []
        result_id = None
        chunks = []
        superseded_id = None
    work = _work_document(
        submit_attempted=submit_attempted,
        submitted=submitted,
        process_launches=process_launches,
        checkpoint_count=len(checkpoint_ids),
        worker_events=0,
        chunks=chunks,
    )
    _, raw = _manifest_document_v1(
        input_document,
        closure_origin="PARENT",
        status="FAILURE",
        failure_code=failure_code,
        checkpoint_ids=checkpoint_ids,
        result_id=result_id,
        chunks=chunks,
        work=work,
        work_tail_unknown=work_tail_unknown,
        superseded_manifest_id=superseded_id,
        quarantine_manifest_id=quarantine_manifest_id,
    )
    _exclusive_write(path / "failure_manifest.json", raw)
    return strict_load_occurrence_manifest_v1(
        path,
        expected_input_bytes=journal.input_bytes,
        expected_input_id=journal.input_id,
        expected_batch_id=batch_id,
        returned_manifest_bytes=raw,
    )


def _aggregate_work(
    occurrences: tuple[LoadedOccurrenceManifestV1, ...],
) -> tuple[tuple[str, int], ...]:
    totals = {path: 0 for path in _WORK_PATHS}
    for occurrence in occurrences:
        for path, value in occurrence.work:
            totals[path] += value
    return tuple((path, totals[path]) for path in _WORK_PATHS)


def _build_batch_merge_v1(
    *,
    batch_id: str,
    occurrences: tuple[LoadedOccurrenceManifestV1, ...],
    pid_diagnostics: tuple[tuple[int, int], ...],
) -> BatchTransportMergeV1:
    aggregate = _aggregate_work(occurrences)
    body = {
        "aggregate_work": [
            {"path": path, "value": value} for path, value in aggregate
        ],
        "batch_id": batch_id,
        "cache_policy": CACHE_POLICY,
        "occurrence_manifest_ids": [
            item.manifest_id for item in occurrences
        ],
        "ordinal_mapping": ORDINAL_MAPPING,
        "profile_key": PROFILE_KEY,
        "schema": BATCH_MERGE_SCHEMA,
        "scientific_claim": False,
        "scientific_merge_produced": False,
        "status": "TRANSPORT_SUCCESS",
    }
    document, raw = _seal_document(BATCH_MERGE_DOMAIN, body, "merge_id")
    return BatchTransportMergeV1(
        merge_id=document["merge_id"],
        batch_id=batch_id,
        occurrence_manifests=occurrences,
        aggregate_work=aggregate,
        canonical_bytes=raw,
        physical_pid_diagnostics=pid_diagnostics,
    )


def _build_batch_failure_v1(
    *,
    batch_id: str,
    occurrences: tuple[LoadedOccurrenceManifestV1, ...],
    pid_diagnostics: tuple[tuple[int, int], ...],
) -> BatchFailureClosureV1:
    aggregate = _aggregate_work(occurrences)
    tail_unknown = any(item.work_tail_unknown for item in occurrences)
    body = {
        "aggregate_known_work": [
            {"path": path, "value": value} for path, value in aggregate
        ],
        "batch_id": batch_id,
        "cache_policy": CACHE_POLICY,
        "occurrences": [
            {
                "failure_code": item.failure_code,
                "manifest_id": item.manifest_id,
                "occurrence_id": item.occurrence_id,
                "scientific_ordinal": item.scientific_ordinal,
                "status": item.status,
                "transport_ordinal": item.transport_ordinal,
                "work_tail_unknown": item.work_tail_unknown,
            }
            for item in occurrences
        ],
        "ordinal_mapping": ORDINAL_MAPPING,
        "profile_key": PROFILE_KEY,
        "schema": BATCH_FAILURE_SCHEMA,
        "scientific_claim": False,
        "scientific_merge_produced": False,
        "status": "TRANSPORT_FAILURE",
        "work_tail_unknown": tail_unknown,
    }
    document, raw = _seal_document(
        BATCH_FAILURE_DOMAIN,
        body,
        "failure_closure_id",
    )
    return BatchFailureClosureV1(
        failure_closure_id=document["failure_closure_id"],
        batch_id=batch_id,
        occurrence_manifests=occurrences,
        aggregate_known_work=aggregate,
        work_tail_unknown=tail_unknown,
        canonical_bytes=raw,
        physical_pid_diagnostics=pid_diagnostics,
    )


def _verify_prepared_batch_v1(prepared: PreparedTransportBatchV1) -> None:
    if type(prepared) is not PreparedTransportBatchV1:
        _fail("runner requires one parent-prepared V0-075 batch")
    root = _real_directory(prepared.batch_root, field="batch root")
    stored_batch = _read_regular_file(
        root / "batch.json",
        byte_cap=MAX_INPUT_BYTES,
        context="batch document",
    )
    if stored_batch != prepared.batch_document_bytes:
        _fail("prepared batch document bytes differ from durable journal")
    batch_document = _exact_document(
        _load_canonical_document(stored_batch, context="batch document"),
        {
            "attempt_nonce_id",
            "batch_id",
            "cache_policy",
            "occurrences",
            "ordinal_mapping",
            "profile_key",
            "schema",
            "scientific_claim",
            "source_archive_id",
        },
        context="batch document",
    )
    verified_batch_id = _verify_sealed_document(
        batch_document,
        domain=BATCH_DOMAIN,
        identity_field="batch_id",
        context="batch document",
    )
    if (
        verified_batch_id != prepared.batch_id
        or batch_document["attempt_nonce_id"] != prepared.attempt_nonce_id
        or batch_document["source_archive_id"] != prepared.source_archive_id
        or batch_document["cache_policy"] != CACHE_POLICY
        or batch_document["ordinal_mapping"] != ORDINAL_MAPPING
        or batch_document["profile_key"] != PROFILE_KEY
        or batch_document["schema"] != BATCH_SCHEMA
        or batch_document["scientific_claim"] is not False
    ):
        _fail("prepared batch document binding mismatch")
    stored_header = _read_regular_file(
        root / "batch_header.json",
        byte_cap=64 * 1024,
        context="batch header",
    )
    if stored_header != prepared.batch_header_bytes:
        _fail("prepared batch header bytes differ from durable journal")
    header = _exact_document(
        _load_canonical_document(stored_header, context="batch header"),
        {
            "batch_header_id",
            "batch_id",
            "input_ids",
            "journal_count",
            "profile_key",
            "schema",
            "scientific_claim",
        },
        context="batch header",
    )
    _verify_sealed_document(
        header,
        domain=BATCH_HEADER_DOMAIN,
        identity_field="batch_header_id",
        context="batch header",
    )
    if (
        header["batch_id"] != prepared.batch_id
        or header["input_ids"] != [item.input_id for item in prepared.journals]
        or header["journal_count"] != len(prepared.journals)
        or header["profile_key"] != PROFILE_KEY
        or header["schema"] != BATCH_HEADER_SCHEMA
        or header["scientific_claim"] is not False
    ):
        _fail("prepared batch header binding mismatch")
    if tuple(item.transport_ordinal for item in prepared.journals) != tuple(
        range(1, len(prepared.journals) + 1)
    ):
        _fail("prepared journals violate transport ordinal ordering")
    expected_names = {"batch.json", "batch_header.json"} | {
        item.journal_path.name for item in prepared.journals
    }
    if {item.name for item in root.iterdir()} != expected_names:
        _fail("prepared batch root contains unregistered entries")
    parsed_inputs: list[dict[str, Any]] = []
    for item in prepared.journals:
        document = _parse_bound_input_v1(
            item.input_bytes,
            expected_input_id=item.input_id,
            expected_batch_id=prepared.batch_id,
        )
        if (
            document["scientific_ordinal"] != item.scientific_ordinal
            or document["transport_ordinal"] != item.transport_ordinal
            or document["occurrence_id"] != item.occurrence_id
        ):
            _fail("prepared journal metadata differs from bound input")
        _verify_parent_prepared_journal_v1(
            str(item.journal_path),
            input_bytes=item.input_bytes,
            input_document=document,
        )
        parsed_inputs.append(document)
    expected_occurrences = [
        {
            "occurrence_id": document["occurrence_id"],
            "scientific_ordinal": document["scientific_ordinal"],
            "target_scope_id": document["target_scope_id"],
            "target_payload_id": _domain_id(
                BATCH_TARGET_COMMITMENT_DOMAIN,
                document["target_payload"],
            ),
            "transport_ordinal": document["transport_ordinal"],
            "worker_key": document["worker_key"],
        }
        for document in parsed_inputs
    ]
    if batch_document["occurrences"] != expected_occurrences:
        _fail("prepared batch target commitments do not match occurrence inputs")


def run_prepared_transport_batch_v1(
    prepared: PreparedTransportBatchV1,
    *,
    max_workers: int,
) -> BatchTransportMergeV1:
    """Run only the registered fixtures and fail closed with retained work."""

    _verify_prepared_batch_v1(prepared)
    if type(max_workers) is not int or not 1 <= max_workers <= MAX_WORKERS:
        _fail("max_workers is outside the frozen [1, 192] range")
    manifests: list[LoadedOccurrenceManifestV1 | None] = [
        None for _ in prepared.journals
    ]
    diagnostics: list[tuple[int, int]] = []
    # Python 3.10 is part of the declared project support range, but its
    # ProcessPoolExecutor does not yet expose max_tasks_per_child.  Reusing a
    # worker would violate the frozen one-fresh-process-per-occurrence
    # contract.  On that runtime, launch bounded waves of one-shot spawn
    # processes instead.  The child target still receives exactly one
    # canonical-bytes argument and communicates scientifically only through
    # its pre-created append-only journal.
    if (
        ProcessPoolExecutor is _STDLIB_PROCESS_POOL_EXECUTOR
        and "max_tasks_per_child"
        not in __import__("inspect").signature(
            ProcessPoolExecutor
        ).parameters
    ):
        _run_one_shot_spawn_transport_v1(
            prepared=prepared,
            max_workers=max_workers,
            manifests=manifests,
            diagnostics=diagnostics,
        )
    else:
        _run_process_pool_transport_v1(
            prepared=prepared,
            max_workers=max_workers,
            manifests=manifests,
            diagnostics=diagnostics,
        )
    if any(item is None for item in manifests):
        _fail("internal runner error left an occurrence without a closure")
    frozen = tuple(item for item in manifests if item is not None)
    diagnostics_tuple = tuple(sorted(diagnostics))
    if any(item.status != "SUCCESS" for item in frozen):
        closure = _build_batch_failure_v1(
            batch_id=prepared.batch_id,
            occurrences=frozen,
            pid_diagnostics=diagnostics_tuple,
        )
        _exclusive_write(
            prepared.batch_root / "batch_failure_closure.json",
            closure.canonical_bytes,
        )
        raise V075TransportBatchExecutionFailure(closure)
    merge = _build_batch_merge_v1(
        batch_id=prepared.batch_id,
        occurrences=frozen,
        pid_diagnostics=diagnostics_tuple,
    )
    _exclusive_write(
        prepared.batch_root / "batch_merge.json",
        merge.canonical_bytes,
    )
    return merge


def _run_one_shot_spawn_transport_v1(
    *,
    prepared: PreparedTransportBatchV1,
    max_workers: int,
    manifests: list[LoadedOccurrenceManifestV1 | None],
    diagnostics: list[tuple[int, int]],
) -> None:
    """Run bounded waves of fresh spawn children for Python 3.10."""

    try:
        context = get_context("spawn")
    except Exception:
        for index, journal in enumerate(prepared.journals):
            manifests[index] = _parent_failure_manifest_v1(
                journal,
                batch_id=prepared.batch_id,
                failure_code="PROCESS_POOL_START_FAILURE",
                submit_attempted=0,
                submitted=0,
                process_launches=0,
                work_tail_unknown=False,
            )
        return

    for wave_start in range(0, len(prepared.journals), max_workers):
        wave = prepared.journals[wave_start : wave_start + max_workers]
        started: list[tuple[int, PreparedOccurrenceJournalV1, Any]] = []
        for offset, journal in enumerate(wave):
            index = wave_start + offset
            process: Any | None = None
            try:
                process = context.Process(
                    target=_execute_child_fixture_v1,
                    args=(
                        _child_request_bytes_v1(
                            journal,
                            batch_id=prepared.batch_id,
                        ),
                    ),
                )
                process.start()
                started.append((index, journal, process))
            except Exception:
                if process is not None:
                    try:
                        process.close()
                    except Exception:
                        pass
                manifests[index] = _parent_failure_manifest_v1(
                    journal,
                    batch_id=prepared.batch_id,
                    failure_code="PROCESS_SUBMIT_FAILURE",
                    submit_attempted=1,
                    submitted=0,
                    process_launches=0,
                    work_tail_unknown=False,
                )
        for index, journal, process in started:
            physical_pid: Any = None
            try:
                physical_pid = process.pid
                process.join()
                if (
                    type(physical_pid) is not int
                    or physical_pid <= 0
                    or process.exitcode != 0
                ):
                    raise V075TransportInvariantViolation(
                        "one-shot child process did not close normally"
                    )
                manifest = strict_load_occurrence_manifest_v1(
                    journal.journal_path,
                    expected_input_bytes=journal.input_bytes,
                    expected_input_id=journal.input_id,
                    expected_batch_id=prepared.batch_id,
                )
                manifests[index] = manifest
                diagnostics.append((journal.transport_ordinal, physical_pid))
            except Exception:
                try:
                    if process.is_alive():
                        process.terminate()
                        process.join()
                except Exception:
                    pass
                manifests[index] = _parent_failure_manifest_v1(
                    journal,
                    batch_id=prepared.batch_id,
                    failure_code="PROCESS_BOUNDARY_FAILURE",
                    submit_attempted=1,
                    submitted=1,
                    process_launches=1,
                    work_tail_unknown=True,
                )
            finally:
                try:
                    process.close()
                except Exception:
                    pass


def _run_process_pool_transport_v1(
    *,
    prepared: PreparedTransportBatchV1,
    max_workers: int,
    manifests: list[LoadedOccurrenceManifestV1 | None],
    diagnostics: list[tuple[int, int]],
) -> None:
    """Run the Python >=3.11 or injected executor path in fresh workers."""

    futures: list[tuple[int, Future[tuple[bytes, int]]]] = []
    executor: ProcessPoolExecutor | None = None
    try:
        try:
            executor = ProcessPoolExecutor(
                max_workers=min(max_workers, len(prepared.journals)),
                mp_context=get_context("spawn"),
                max_tasks_per_child=1,
            )
        except Exception:
            for index, journal in enumerate(prepared.journals):
                manifests[index] = _parent_failure_manifest_v1(
                    journal,
                    batch_id=prepared.batch_id,
                    failure_code="PROCESS_POOL_START_FAILURE",
                    submit_attempted=0,
                    submitted=0,
                    process_launches=0,
                    work_tail_unknown=False,
                )
        if executor is not None:
            for index, journal in enumerate(prepared.journals):
                try:
                    future = executor.submit(
                        _execute_child_fixture_v1,
                        _child_request_bytes_v1(
                            journal,
                            batch_id=prepared.batch_id,
                        ),
                    )
                    futures.append((index, future))
                except Exception:
                    manifests[index] = _parent_failure_manifest_v1(
                        journal,
                        batch_id=prepared.batch_id,
                        failure_code="PROCESS_SUBMIT_FAILURE",
                        submit_attempted=1,
                        submitted=0,
                        process_launches=0,
                        work_tail_unknown=False,
                    )
            for index, future in futures:
                journal = prepared.journals[index]
                known_process_launches = 0
                try:
                    manifest_bytes, physical_pid = future.result()
                    if type(physical_pid) is not int or physical_pid <= 0:
                        raise V075TransportInvariantViolation(
                            "child PID diagnostic is invalid"
                        )
                    known_process_launches = 1
                    manifest = strict_load_occurrence_manifest_v1(
                        journal.journal_path,
                        expected_input_bytes=journal.input_bytes,
                        expected_input_id=journal.input_id,
                        expected_batch_id=prepared.batch_id,
                        returned_manifest_bytes=manifest_bytes,
                    )
                    manifests[index] = manifest
                    diagnostics.append((journal.transport_ordinal, physical_pid))
                except Exception:
                    manifests[index] = _parent_failure_manifest_v1(
                        journal,
                        batch_id=prepared.batch_id,
                        failure_code="PROCESS_BOUNDARY_FAILURE",
                        submit_attempted=1,
                        submitted=1,
                        process_launches=known_process_launches,
                        work_tail_unknown=True,
                    )
    finally:
        if executor is not None:
            try:
                executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                pass


__all__ = [
    "BatchFailureClosureV1",
    "BatchTransportMergeV1",
    "CACHE_POLICY",
    "LoadedOccurrenceManifestV1",
    "OccurrenceSpecV1",
    "ORDINAL_MAPPING",
    "PreparedOccurrenceJournalV1",
    "PreparedTransportBatchV1",
    "PROFILE_KEY",
    "RegisteredFixtureWorkerV1",
    "V075TransportBatchExecutionFailure",
    "V075TransportInvariantViolation",
    "derive_transport_batch_id_v1",
    "prepare_transport_batch_v1",
    "run_prepared_transport_batch_v1",
    "strict_load_occurrence_manifest_v1",
]
