"""Bounded signer-owning sealed-observer IPC construction for V0-075.

This contract-1.69 Stage-A boundary moves the production observer signer into
one fresh child process.  The child imports ACFQP only from a sealed memfd
source archive, reads private-session material only from a distinct sealed
descriptor, and loads the observer signer itself through the production
private-signer runtime.  The canonical request contains public identities
only; it has no signer, replay-verification, private salt/environment, prior
closure, or prior B3-attestation input channel.

The current bounded implementation deliberately does *not* claim ownership of
an observer session from open through finalization.  Consequently it never
signs B3 and always closes an otherwise-valid finalize request as
``SESSION_OWNERSHIP_NOT_YET_COMPLETE``.  This is preferable to turning an old
closure into a post-hoc signed replay claim.  Every official, scientific,
registry, and certificate lock remains closed.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import ctypes
import fcntl
from functools import lru_cache
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import MappingProxyType
from typing import Any, Mapping, NoReturn
import zipfile

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_production_private_signer_runtime_v1 as signer_runtime
from acfqp import v075_public_campaign_authority_v1 as public


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.69.0"
PROFILE_KEY = "v075_signer_owning_sealed_observer_ipc_v1"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
OBSERVER_SESSION_OWNERSHIP_COMPLETE = False
B3_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_SIGNER_OWNING_SEALED_OBSERVER_STAGE_A_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "SESSION_OWNERSHIP_NOT_YET_COMPLETE"

_CHILD_TERMINAL_CODES = frozenset(
    {
        "SESSION_OWNERSHIP_NOT_YET_COMPLETE",
        "PRIVATE_MATERIAL_COMMITMENT_MISMATCH",
        "SIGNER_LOAD_FAILED",
    }
)
_NO_CHILD_TERMINAL_CODES = frozenset(
    {
        "NONCE_REPLAY_REJECTED",
        "SOURCE_ARCHIVE_STAGING_FAILED",
        "PROCESS_LAUNCH_FAILED",
        "PROCESS_IDENTITY_CAPTURE_FAILED",
        "SUPERVISOR_PROTOCOL_FAILURE",
        "CHILD_RESULT_VALIDATION_FAILED",
        "CHILD_TIMEOUT",
        "CHILD_CRASH",
        "CHILD_FRAME_INVALID",
        "CHILD_EXTRA_OUTPUT",
        "CHILD_OUTPUT_CAP_EXCEEDED",
        "CHILD_STDERR_CAP_EXCEEDED",
        "CHILD_STDERR_FORBIDDEN",
    }
)
_ALLOWED_TERMINAL_CODES = _CHILD_TERMINAL_CODES | _NO_CHILD_TERMINAL_CODES
_PRELAUNCH_TERMINAL_CODES = frozenset(
    {
        "NONCE_REPLAY_REJECTED",
        "SOURCE_ARCHIVE_STAGING_FAILED",
        "PROCESS_LAUNCH_FAILED",
    }
)

MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_CHILD_RESULT_BYTES = 4 * 1024 * 1024
MAX_FINAL_RESULT_BYTES = 16 * 1024 * 1024
MAX_SOURCE_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_PRIVATE_MATERIAL_BYTES = 16 * 1024 * 1024
MAX_STDERR_BYTES = 128 * 1024
MIN_TIMEOUT_MILLISECONDS = 50
MAX_TIMEOUT_MILLISECONDS = 60_000

_FRAME_WIDTH = 8
_F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
_F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
_F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
_F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
_F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
_F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
_MFD_CLOEXEC = getattr(os, "MFD_CLOEXEC", 0x0001)
_MFD_ALLOW_SEALING = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
_REQUIRED_SEALS = (
    _F_SEAL_WRITE | _F_SEAL_GROW | _F_SEAL_SHRINK | _F_SEAL_SEAL
)
_MODULE_NAME = "acfqp.v075_signer_owning_sealed_observer_ipc_v1"

_DOMAINS = MappingProxyType(
    {
        "source_snapshot": (
            "acfqp:v075-signer-owning-observer-source-snapshot:v1"
        ),
        "runtime": "acfqp:v075-signer-owning-observer-runtime:v1",
        "program": "acfqp:v075-signer-owning-observer-program:v1",
        "profile": "acfqp:v075-signer-owning-observer-profile:v1",
        "request": "acfqp:v075-signer-owning-observer-request:v1",
        "private_material": (
            "acfqp:v075-signer-owning-observer-private-material:v1"
        ),
        "child_result": (
            "acfqp:v075-signer-owning-observer-child-result:v1"
        ),
        "process": "acfqp:v075-signer-owning-observer-process:v1",
        "supervisor": "acfqp:v075-signer-owning-observer-supervisor:v1",
        "journal_entry": (
            "acfqp:v075-signer-owning-observer-journal-entry:v1"
        ),
        "invalid_child_payload": (
            "acfqp:v075-signer-owning-observer-invalid-child-payload:v1"
        ),
        "journal": "acfqp:v075-signer-owning-observer-journal:v1",
        "work": "acfqp:v075-signer-owning-observer-work:v1",
        "result": "acfqp:v075-signer-owning-observer-result:v1",
    }
)

if len(_DOMAINS) != len(set(_DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("signer-owning observer IPC domains overlap")


class V075SignerOwningSealedObserverIPCV1InvariantViolation(ValueError):
    """A request, source, runtime, frame, child, or result was invalid."""


class V075SignerOwningSealedObserverProductionV1NotReady(RuntimeError):
    """Stage A cannot authorize production without full session ownership."""


def _fail(message: str) -> NoReturn:
    raise V075SignerOwningSealedObserverIPCV1InvariantViolation(message)


def _canonical(value: Any) -> bytes:
    try:
        return canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            str(error)
        ) from error


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("canonical IPC JSON contains a duplicate key")
        result[key] = value
    return result


def _load(raw: bytes, *, label: str, cap: int) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > cap:
        _fail(f"{label} is empty, mistyped, or over cap")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda token: _fail(
                f"{label} contains non-finite {token}"
            ),
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        if isinstance(
            error,
            V075SignerOwningSealedObserverIPCV1InvariantViolation,
        ):
            raise
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or _canonical(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _exact(
    value: Any,
    keys: frozenset[str] | set[str],
    *,
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        _fail(f"{label} fields are missing, hidden, or malformed")
    return value


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = _DOMAINS[role]
    except KeyError as error:  # pragma: no cover
        raise RuntimeError("unknown signer-owning IPC content domain") from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + _canonical(dict(payload))
    ).hexdigest()


def _typed_null(reason: str) -> dict[str, str]:
    if type(reason) is not str or not reason:
        _fail("typed-null reason is empty")
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _require_typed_null(
    value: Any,
    *,
    reason: str,
    label: str,
) -> dict[str, str]:
    expected = {"kind": "NOT_APPLICABLE", "reason": reason}
    if type(value) is not dict or value != expected:
        _fail(f"{label} typed-null reason or fields changed")
    return value


def _terminal_output_null_reason(outcome: str) -> str:
    if outcome == "SESSION_OWNERSHIP_NOT_YET_COMPLETE":
        return "CHILD_DID_NOT_OWN_SESSION_FROM_OBSERVER_OPEN"
    if outcome not in _ALLOWED_TERMINAL_CODES:
        _fail("terminal output typed-null outcome is unregistered")
    return outcome


def _locks() -> dict[str, bool]:
    return {
        "source_authority_complete": False,
        "code_provenance_complete": False,
        "portable_semantic_registry_complete": False,
        "fresh_heldout_accessed": False,
        "official_execution_allowed": False,
        "production_authorizing": False,
        "scientific_endpoint_credit_allowed": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
        "private_material_serialized": False,
    }


def _require_memfd_platform() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if not hasattr(libc, "memfd_create") or not Path("/proc/self/fd").is_dir():
        _fail("sealed memfd execution is unavailable")


def _memfd_create(name: str) -> int:
    _require_memfd_platform()
    if hasattr(os, "memfd_create"):
        return os.memfd_create(
            name,
            flags=_MFD_ALLOW_SEALING | _MFD_CLOEXEC,
        )
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.memfd_create
    function.argtypes = (ctypes.c_char_p, ctypes.c_uint)
    function.restype = ctypes.c_int
    fd = function(
        name.encode("ascii", errors="strict"),
        _MFD_ALLOW_SEALING | _MFD_CLOEXEC,
    )
    if fd < 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    return fd


def _stage_sealed_bytes(raw: bytes, *, name: str, cap: int) -> int:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > cap
        or type(name) is not str
        or not name
    ):
        _fail("sealed bytes are empty, mistyped, or over cap")
    fd = _memfd_create(name)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset : offset + 1024 * 1024])
            if written <= 0:
                _fail("sealed-byte staging made no progress")
            offset += written
        fcntl.fcntl(fd, _F_ADD_SEALS, _REQUIRED_SEALS)
        _verify_sealed_fd(fd, cap=cap)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _verify_sealed_fd(fd: int, *, cap: int) -> os.stat_result:
    if type(fd) is not int or fd < 0:
        _fail("sealed descriptor is invalid")
    try:
        status = os.fstat(fd)
        seals = fcntl.fcntl(fd, _F_GET_SEALS)
    except OSError as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "sealed descriptor cannot be inspected"
        ) from error
    if (
        seals & _REQUIRED_SEALS != _REQUIRED_SEALS
        or status.st_size <= 0
        or status.st_size > cap
    ):
        _fail("descriptor is writable, unsealed, empty, or over cap")
    return status


def _read_sealed_fd(fd: int, *, cap: int) -> bytes:
    status = _verify_sealed_fd(fd, cap=cap)
    chunks: list[bytes] = []
    offset = 0
    while offset < status.st_size:
        try:
            chunk = os.pread(
                fd,
                min(1024 * 1024, status.st_size - offset),
                offset,
            )
        except OSError as error:
            raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
                "sealed descriptor cannot be read"
            ) from error
        if not chunk:
            _fail("sealed descriptor is truncated")
        chunks.append(chunk)
        offset += len(chunk)
    after = os.fstat(fd)
    if (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        _fail("sealed descriptor identity changed during read")
    return b"".join(chunks)


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _deterministic_source_archive() -> tuple[
    bytes,
    tuple[tuple[str, str, int], ...],
]:
    package_root = _source_root() / "acfqp"
    paths = tuple(
        sorted(
            path
            for path in package_root.rglob("*.py")
            if path.is_file() and not path.is_symlink()
        )
    )
    if not paths:
        _fail("signer-owning IPC source package is absent")
    entries: list[tuple[str, str, int]] = []
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_STORED,
        strict_timestamps=True,
    ) as archive:
        for path in paths:
            raw = path.read_bytes()
            relative = path.relative_to(_source_root()).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100444 << 16
            info.create_system = 3
            archive.writestr(info, raw)
            entries.append(
                (relative, hashlib.sha256(raw).hexdigest(), len(raw))
            )
    raw_archive = output.getvalue()
    if not raw_archive or len(raw_archive) > MAX_SOURCE_ARCHIVE_BYTES:
        _fail("signer-owning IPC source archive exceeds its cap")
    return raw_archive, tuple(entries)


def _archive_entries(raw: bytes) -> tuple[tuple[str, str, int], ...]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_SOURCE_ARCHIVE_BYTES:
        _fail("source archive bytes are empty, mistyped, or over cap")
    result: list[tuple[str, str, int]] = []
    seen: set[str] = set()
    try:
        with zipfile.ZipFile(io.BytesIO(raw), mode="r") as archive:
            infos = archive.infolist()
            for info in infos:
                path = PurePosixPath(info.filename)
                if (
                    info.filename in seen
                    or path.is_absolute()
                    or ".." in path.parts
                    or not info.filename.startswith("acfqp/")
                    or not info.filename.endswith(".py")
                    or info.compress_type != zipfile.ZIP_STORED
                    or info.date_time != (1980, 1, 1, 0, 0, 0)
                ):
                    _fail("source archive entry is duplicated or noncanonical")
                seen.add(info.filename)
                content = archive.read(info)
                result.append(
                    (
                        info.filename,
                        hashlib.sha256(content).hexdigest(),
                        len(content),
                    )
                )
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "source archive is unreadable"
        ) from error
    ordered = tuple(sorted(result))
    if tuple(result) != ordered or not ordered:
        _fail("source archive entry order is noncanonical")
    return ordered


def _source_payload(
    *,
    archive_sha256: str,
    archive_byte_count: int,
    entries: tuple[tuple[str, str, int], ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_signer_owning_observer_source_snapshot.v1",
        "schema_version": SCHEMA_VERSION,
        "archive_sha256": _cid(archive_sha256, "source archive"),
        "archive_byte_count": archive_byte_count,
        "archive_format": "DETERMINISTIC_ZIP_STORED",
        "entries": [
            {"path": path, "sha256": digest, "byte_count": size}
            for path, digest, size in entries
        ],
        "entry_count": len(entries),
        "live_workspace_import_allowed": False,
    }


def _runtime_payload() -> dict[str, Any]:
    executable = Path(sys.executable).resolve(strict=True)
    raw = executable.read_bytes()
    return {
        "schema": "acfqp.v075_signer_owning_observer_runtime.v1",
        "schema_version": SCHEMA_VERSION,
        "implementation": sys.implementation.name,
        "version": list(sys.version_info[:3]),
        "executable_sha256": hashlib.sha256(raw).hexdigest(),
        "executable_byte_count": len(raw),
        "required_flags": {
            "isolated": 1,
            "no_site": 1,
            "ignore_environment": 1,
            "safe_path": True if hasattr(sys.flags, "safe_path") else None,
        },
    }


def _program_payload(
    *,
    source_snapshot_id: str,
    runtime_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_signer_owning_observer_program.v1",
        "schema_version": SCHEMA_VERSION,
        "module": _MODULE_NAME,
        "child_callable": "_sealed_child_main",
        "bootstrap_sha256": _BOOTSTRAP_SHA256,
        "source_snapshot_id": source_snapshot_id,
        "runtime_id": runtime_id,
        "input_frame_count": 1,
        "output_frame_count": 1,
        "signer_constructed_in_child_only": True,
        "prior_closure_input_allowed": False,
        "prior_b3_input_allowed": False,
    }


@lru_cache(maxsize=4)
def _immutable_bytes_sha256(raw: bytes) -> str:
    """Hash immutable archive bytes once per distinct archive value."""

    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class V075SignerOwningSealedObserverServiceProfileV1:
    source_archive_sha256: str
    source_archive_byte_count: int
    source_entries: tuple[tuple[str, str, int], ...]
    runtime_document: Mapping[str, Any] = field(repr=False, compare=False)
    timeout_milliseconds: int
    _archive_bytes: bytes = field(repr=False, compare=False)
    _validated_archive_bytes: bytes = field(init=False, repr=False, compare=False)
    _source_snapshot_id: str = field(init=False, repr=False)
    _runtime_id: str = field(init=False, repr=False)
    _program_id: str = field(init=False, repr=False)
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.source_archive_sha256) is not str
            or type(self.source_archive_byte_count) is not int
            or type(self.source_entries) is not tuple
            or type(self.runtime_document) is not dict
            or type(self.timeout_milliseconds) is not int
            or self.timeout_milliseconds
            not in range(
                MIN_TIMEOUT_MILLISECONDS,
                MAX_TIMEOUT_MILLISECONDS + 1,
            )
            or type(self._archive_bytes) is not bytes
        ):
            _fail("signer-owning service profile is malformed")
        # Full ZIP structure and per-entry hashes are immutable construction
        # checks.  Replaying them on every property access made one 21 MiB
        # snapshot get decomposed and rehashed dozens of times.  Validate the
        # complete archive once here; later freshness checks still bind the
        # exact bytes by size/SHA and bind the immutable entry tuple through
        # the source-snapshot content ID.
        if (
            len(self._archive_bytes) != self.source_archive_byte_count
            or _immutable_bytes_sha256(self._archive_bytes)
            != self.source_archive_sha256
            or _archive_entries(self._archive_bytes) != self.source_entries
        ):
            _fail("signer-owning service source archive is inconsistent")
        # ``bytes`` is immutable.  Retaining the exact object that passed the
        # full ZIP/hash validation lets freshness checks reject any archive
        # replacement without re-reading and re-hashing 21+ MiB on every
        # profile property access.  This is stricter than digest-only replay:
        # even a byte-identical replacement is rejected until a new profile is
        # constructed and content-addressed.
        object.__setattr__(
            self,
            "_validated_archive_bytes",
            self._archive_bytes,
        )
        source_payload = _source_payload(
            archive_sha256=self.source_archive_sha256,
            archive_byte_count=self.source_archive_byte_count,
            entries=self.source_entries,
        )
        source_id = _hash("source_snapshot", source_payload)
        runtime_id = _hash("runtime", dict(self.runtime_document))
        program_id = _hash(
            "program",
            _program_payload(
                source_snapshot_id=source_id,
                runtime_id=runtime_id,
            ),
        )
        object.__setattr__(self, "_source_snapshot_id", source_id)
        object.__setattr__(self, "_runtime_id", runtime_id)
        object.__setattr__(self, "_program_id", program_id)
        object.__setattr__(
            self,
            "_profile_id",
            _hash("profile", self._payload()),
        )
        self._assert_current()

    def _payload(self) -> dict[str, Any]:
        source_payload = _source_payload(
            archive_sha256=self.source_archive_sha256,
            archive_byte_count=self.source_archive_byte_count,
            entries=self.source_entries,
        )
        return {
            "schema": "acfqp.v075_signer_owning_observer_service_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_snapshot": {
                **source_payload,
                "source_snapshot_id": self._source_snapshot_id,
            },
            "source_snapshot_id": self._source_snapshot_id,
            "runtime": {
                **dict(self.runtime_document),
                "runtime_id": self._runtime_id,
            },
            "runtime_id": self._runtime_id,
            "program": {
                **_program_payload(
                    source_snapshot_id=self._source_snapshot_id,
                    runtime_id=self._runtime_id,
                ),
                "program_id": self._program_id,
            },
            "program_id": self._program_id,
            "timeout_milliseconds": self.timeout_milliseconds,
            "request_byte_cap": MAX_REQUEST_BYTES,
            "child_result_byte_cap": MAX_CHILD_RESULT_BYTES,
            "private_material_byte_cap": MAX_PRIVATE_MATERIAL_BYTES,
            "observer_session_ownership_complete": False,
            "b3_issuance_allowed": False,
            **_locks(),
        }

    def _assert_current(self) -> None:
        if (
            self._archive_bytes is not self._validated_archive_bytes
            or len(self._archive_bytes) != self.source_archive_byte_count
            or _immutable_bytes_sha256(self._archive_bytes)
            != self.source_archive_sha256
            or _hash(
                "source_snapshot",
                _source_payload(
                    archive_sha256=self.source_archive_sha256,
                    archive_byte_count=self.source_archive_byte_count,
                    entries=self.source_entries,
                ),
            )
            != self._source_snapshot_id
            or _hash("runtime", dict(self.runtime_document))
            != self._runtime_id
            or _hash(
                "program",
                _program_payload(
                    source_snapshot_id=self._source_snapshot_id,
                    runtime_id=self._runtime_id,
                ),
            )
            != self._program_id
            or _hash("profile", self._payload()) != self._profile_id
        ):
            _fail("signer-owning service profile identity is stale")

    @property
    def source_snapshot_id(self) -> str:
        self._assert_current()
        return self._source_snapshot_id

    @property
    def runtime_id(self) -> str:
        self._assert_current()
        return self._runtime_id

    @property
    def program_id(self) -> str:
        self._assert_current()
        return self._program_id

    @property
    def profile_id(self) -> str:
        self._assert_current()
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return deepcopy(
            {**self._payload(), "profile_id": self._profile_id}
        )

    def __reduce__(self) -> NoReturn:
        raise TypeError("signer-owning service profiles retain source bytes")


def freeze_v075_signer_owning_sealed_observer_service_profile_v1(
    *,
    timeout_milliseconds: int = 10_000,
) -> V075SignerOwningSealedObserverServiceProfileV1:
    archive, entries = _deterministic_source_archive()
    return V075SignerOwningSealedObserverServiceProfileV1(
        hashlib.sha256(archive).hexdigest(),
        len(archive),
        entries,
        _runtime_payload(),
        timeout_milliseconds,
        archive,
    )


_REQUEST_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "profile_id",
        "service_program_id",
        "source_snapshot_id",
        "runtime_id",
        "request_nonce",
        "requested_operation",
        "session_ownership_requirement",
        "session_external_id",
        "private_material_commitment_id",
        "signer_registry",
        "signer_registry_id",
        "observer_evidence_key_id",
        "ordered_stream_ids",
        "caller_supplied_signer",
        "caller_supplied_verification",
        "caller_supplied_private_material",
        "caller_supplied_prior_closure",
        "caller_supplied_prior_b3",
        "request_id",
    }
)


def _public_key_from_document(
    value: Any,
    *,
    expected_role: str,
) -> public.V075RSAPublicVerificationKeyV1:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "key_role",
            "algorithm",
            "modulus_hex",
            "public_exponent",
            "minimum_modulus_bits",
            "private_key_serialized",
            "key_id",
        },
        label="public signer key",
    )
    if (
        item["schema"] != "acfqp.v075_rsa_public_verification_key.v1"
        or item["key_role"] != expected_role
        or item["algorithm"] != "RSASSA-PKCS1-v1_5-SHA256"
        or type(item["modulus_hex"]) is not str
        or type(item["public_exponent"]) is not int
        or item["private_key_serialized"] is not False
    ):
        _fail("public signer key fields changed")
    try:
        key = public.V075RSAPublicVerificationKeyV1(
            item["key_role"],
            int(item["modulus_hex"], 16),
            item["public_exponent"],
        )
    except (TypeError, ValueError) as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "public signer key failed exact replay"
        ) from error
    if key.to_document() != item:
        _fail("public signer key identity changed")
    return key


def _registry_from_document(
    value: Any,
) -> public.V075TrustedSignerRegistryV1:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "campaign_authority_key_id",
            "observer_evidence_key_id",
            "private_keys_serialized",
            "registry_precedes_final_preregistration",
            "final_preregistration_must_bind_registry_id",
            "registry_contains_final_preregistration_id",
            "campaign_authority_key",
            "observer_evidence_key",
            "registry_id",
        },
        label="signer registry",
    )
    campaign = _public_key_from_document(
        item["campaign_authority_key"],
        expected_role="CAMPAIGN_AUTHORITY",
    )
    observer_key = _public_key_from_document(
        item["observer_evidence_key"],
        expected_role="OBSERVER_EVIDENCE",
    )
    try:
        registry = public.V075TrustedSignerRegistryV1(
            campaign,
            observer_key,
        )
    except (TypeError, ValueError) as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "signer registry failed exact replay"
        ) from error
    if registry.to_document() != item:
        _fail("signer registry identity changed")
    return registry


def _request_payload(
    *,
    profile: V075SignerOwningSealedObserverServiceProfileV1,
    request_nonce: str,
    session_external_id: str,
    private_material_commitment_id: str,
    signer_registry: public.V075TrustedSignerRegistryV1,
    ordered_stream_ids: tuple[str, ...],
) -> dict[str, Any]:
    _cid(request_nonce, "request nonce")
    _cid(session_external_id, "session external identity")
    _cid(private_material_commitment_id, "private-material commitment")
    if (
        type(signer_registry) is not public.V075TrustedSignerRegistryV1
        or type(ordered_stream_ids) is not tuple
        or not ordered_stream_ids
        or tuple(sorted(set(ordered_stream_ids))) != ordered_stream_ids
    ):
        _fail("finalize request public registry or stream set is malformed")
    for value in ordered_stream_ids:
        _cid(value, "requested stream")
    return {
        "schema": "acfqp.v075_signer_owning_observer_finalize_request.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "profile_id": profile.profile_id,
        "service_program_id": profile.program_id,
        "source_snapshot_id": profile.source_snapshot_id,
        "runtime_id": profile.runtime_id,
        "request_nonce": request_nonce,
        "requested_operation": "FINALIZE_CHILD_OWNED_SESSION",
        "session_ownership_requirement": "CHILD_OPEN_THROUGH_FINALIZE",
        "session_external_id": session_external_id,
        "private_material_commitment_id": private_material_commitment_id,
        "signer_registry": signer_registry.to_document(),
        "signer_registry_id": signer_registry.registry_id,
        "observer_evidence_key_id": (
            signer_registry.observer_evidence_key.key_id
        ),
        "ordered_stream_ids": list(ordered_stream_ids),
        "caller_supplied_signer": False,
        "caller_supplied_verification": False,
        "caller_supplied_private_material": False,
        "caller_supplied_prior_closure": False,
        "caller_supplied_prior_b3": False,
    }


@dataclass(frozen=True, slots=True)
class V075SealedObserverFinalizeRequestV1:
    _document: Mapping[str, Any] = field(repr=False)
    _raw: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        document = _validate_request_document(dict(self._document))
        raw = _canonical(document)
        object.__setattr__(
            self,
            "_document",
            MappingProxyType(
                _load(raw, label="finalize request", cap=MAX_REQUEST_BYTES)
            ),
        )
        object.__setattr__(self, "_raw", raw)

    def _current_document(self) -> dict[str, Any]:
        document = _validate_request_document(
            _load(
                self._raw,
                label="finalize request",
                cap=MAX_REQUEST_BYTES,
            )
        )
        if _canonical(document) != self._raw:
            _fail("finalize request cached bytes changed")
        return document

    @property
    def request_id(self) -> str:
        return self._current_document()["request_id"]

    @property
    def request_nonce(self) -> str:
        return self._current_document()["request_nonce"]

    @property
    def canonical_bytes(self) -> bytes:
        self._current_document()
        return self._raw

    def to_document(self) -> dict[str, Any]:
        return self._current_document()


def freeze_v075_sealed_observer_finalize_request_v1(
    *,
    profile: V075SignerOwningSealedObserverServiceProfileV1,
    request_nonce: str,
    session_external_id: str,
    private_material_commitment_id: str,
    signer_registry: public.V075TrustedSignerRegistryV1,
    ordered_stream_ids: tuple[str, ...],
) -> V075SealedObserverFinalizeRequestV1:
    if type(profile) is not V075SignerOwningSealedObserverServiceProfileV1:
        _fail("finalize request profile is untyped")
    profile._assert_current()
    payload = _request_payload(
        profile=profile,
        request_nonce=request_nonce,
        session_external_id=session_external_id,
        private_material_commitment_id=private_material_commitment_id,
        signer_registry=signer_registry,
        ordered_stream_ids=ordered_stream_ids,
    )
    return V075SealedObserverFinalizeRequestV1(
        {**payload, "request_id": _hash("request", payload)}
    )


def _validate_request_document(document: dict[str, Any]) -> dict[str, Any]:
    item = _exact(document, _REQUEST_KEYS, label="finalize request")
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_observer_finalize_request.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["requested_operation"] != "FINALIZE_CHILD_OWNED_SESSION"
        or item["session_ownership_requirement"]
        != "CHILD_OPEN_THROUGH_FINALIZE"
        or any(
            item[key] is not False
            for key in (
                "caller_supplied_signer",
                "caller_supplied_verification",
                "caller_supplied_private_material",
                "caller_supplied_prior_closure",
                "caller_supplied_prior_b3",
            )
        )
    ):
        _fail("finalize request attempts a forbidden post-hoc input channel")
    for key in (
        "profile_id",
        "service_program_id",
        "source_snapshot_id",
        "runtime_id",
        "request_nonce",
        "session_external_id",
        "private_material_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "request_id",
    ):
        _cid(item[key], f"finalize request {key}")
    registry = _registry_from_document(item["signer_registry"])
    if (
        registry.registry_id != item["signer_registry_id"]
        or registry.observer_evidence_key.key_id
        != item["observer_evidence_key_id"]
        or type(item["ordered_stream_ids"]) is not list
        or not item["ordered_stream_ids"]
        or sorted(set(item["ordered_stream_ids"]))
        != item["ordered_stream_ids"]
    ):
        _fail("finalize request registry or stream identity is stale")
    for value in item["ordered_stream_ids"]:
        _cid(value, "finalize request stream")
    payload = {key: value for key, value in item.items() if key != "request_id"}
    if _hash("request", payload) != item["request_id"]:
        _fail("finalize request content identity changed")
    return item


def verify_v075_sealed_observer_finalize_request_bytes_v1(
    raw: bytes,
) -> V075SealedObserverFinalizeRequestV1:
    return V075SealedObserverFinalizeRequestV1(
        _load(raw, label="finalize request", cap=MAX_REQUEST_BYTES)
    )


_PRIVATE_MATERIAL_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "private_salt_hex",
        "private_environment",
        "material_commitment_id",
    }
)


def _private_material_commitment(raw: bytes) -> str:
    item = _load(
        raw,
        label="sealed private-session material",
        cap=MAX_PRIVATE_MATERIAL_BYTES,
    )
    _exact(
        item,
        _PRIVATE_MATERIAL_KEYS,
        label="sealed private-session material",
    )
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_observer_private_session_material.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or type(item["private_salt_hex"]) is not str
        or not item["private_salt_hex"]
        or len(item["private_salt_hex"]) % 2
        or any(
            character not in "0123456789abcdef"
            for character in item["private_salt_hex"]
        )
        or type(item["private_environment"]) is not list
        or not item["private_environment"]
    ):
        _fail("sealed private-session material schema is malformed")
    claimed = _cid(
        item["material_commitment_id"],
        "sealed private-session material",
    )
    payload = {
        key: value for key, value in item.items() if key != "material_commitment_id"
    }
    expected = _hash("private_material", payload)
    if claimed != expected:
        _fail("sealed private-session material content identity changed")
    return expected


def _private_material_raw_for_testing(
    *,
    private_salt_hex: str,
    private_environment: list[Any],
) -> bytes:
    """Test-support constructor; private bytes never enter an IPC request."""

    payload = {
        "schema": (
            "acfqp.v075_signer_owning_observer_private_session_material.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "private_salt_hex": private_salt_hex,
        "private_environment": private_environment,
    }
    raw = _canonical(
        {**payload, "material_commitment_id": _hash("private_material", payload)}
    )
    _private_material_commitment(raw)
    return raw


def _stage_sealed_private_material_bytes_for_testing(raw: bytes) -> int:
    """Stage private test material without exposing it in request artifacts."""

    _private_material_commitment(raw)
    return _stage_sealed_bytes(
        raw,
        name="acfqp-v075-private-session-material",
        cap=MAX_PRIVATE_MATERIAL_BYTES,
    )


def _parse_frame_header(header: bytes, *, cap: int) -> int:
    if type(header) is not bytes or len(header) != _FRAME_WIDTH:
        _fail("IPC frame header is truncated")
    try:
        text = header.decode("ascii", errors="strict")
        if any(character not in "0123456789abcdef" for character in text):
            raise ValueError("noncanonical digit")
        length = int(text, 16)
    except (UnicodeError, ValueError) as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "IPC frame header is noncanonical"
        ) from error
    if (
        header != f"{length:0{_FRAME_WIDTH}x}".encode("ascii")
        or not 0 < length <= cap
    ):
        _fail("IPC frame length is noncanonical or outside its cap")
    return length


def _frame(raw: bytes, *, cap: int) -> bytes:
    if type(raw) is not bytes or not raw or len(raw) > cap:
        _fail("IPC payload is empty, mistyped, or over cap")
    return f"{len(raw):0{_FRAME_WIDTH}x}".encode("ascii") + raw


def _decode_single_frame(raw: bytes, *, cap: int) -> bytes:
    if type(raw) is not bytes or len(raw) < _FRAME_WIDTH:
        _fail("IPC framed bytes are truncated")
    length = _parse_frame_header(raw[:_FRAME_WIDTH], cap=cap)
    if len(raw) != _FRAME_WIDTH + length:
        _fail("IPC frame is truncated or carries extra frames")
    return raw[_FRAME_WIDTH:]


def _read_child_frame(stream: Any, *, cap: int) -> bytes:
    header = stream.read(_FRAME_WIDTH)
    length = _parse_frame_header(header, cap=cap)
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = stream.read(min(1024 * 1024, remaining))
        if type(chunk) is not bytes or not chunk:
            _fail("child received a truncated request frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    if stream.read(1):
        _fail("child received a double-finalize or trailing frame")
    return b"".join(chunks)


def _write_child_frame(stream: Any, raw: bytes, *, cap: int) -> None:
    framed = _frame(raw, cap=cap)
    try:
        stream.write(framed)
        stream.flush()
    except (BrokenPipeError, OSError) as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "child result frame write failed"
        ) from error


def _child_work(
    *,
    secret_read: int,
    secret_verified: int,
    signer_load_attempts: int,
    signer_load_successes: int,
) -> dict[str, int]:
    return {
        "sealed_source_verification_checks": 2,
        "runtime_identity_checks": 1,
        "request_raw_replay_calls": 1,
        "private_material_fd_read_attempts": secret_read,
        "private_material_commitment_checks": secret_verified,
        "production_signer_load_attempts": signer_load_attempts,
        "production_signer_load_successes": signer_load_successes,
        "signer_load_challenge_signatures": signer_load_successes,
        "observer_session_open_attempts": 0,
        "observer_session_finalize_attempts": 0,
        "private_replay_calls": 0,
        "b3_sign_calls": 0,
        "prior_closure_upgrade_calls": 0,
        "prior_b3_upgrade_calls": 0,
    }


def _child_result_payload(
    *,
    request: Mapping[str, Any],
    outcome: str,
    secret_verified: bool,
    signer_loaded: bool,
    work: Mapping[str, int],
) -> dict[str, Any]:
    if outcome not in _CHILD_TERMINAL_CODES:
        _fail("child result outcome is unregistered")
    reason = _terminal_output_null_reason(outcome)
    return {
        "schema": "acfqp.v075_signer_owning_observer_child_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": outcome,
        "profile_id": request["profile_id"],
        "service_program_id": request["service_program_id"],
        "source_snapshot_id": request["source_snapshot_id"],
        "runtime_id": request["runtime_id"],
        "request_id": request["request_id"],
        "request_nonce": request["request_nonce"],
        "session_external_id": request["session_external_id"],
        "private_material_commitment_id": (
            request["private_material_commitment_id"]
        ),
        "signer_registry_id": request["signer_registry_id"],
        "observer_evidence_key_id": request["observer_evidence_key_id"],
        "ordered_stream_ids": request["ordered_stream_ids"],
        "sealed_private_material_commitment_verified": secret_verified,
        "sealed_child_signer_loader_completed": signer_loaded,
        "signer_loader_completion_is_process_attestation_not_crypto_proof": (
            True
        ),
        "observer_session_owned_from_open": False,
        "private_replay_performed": False,
        "b3_sign_performed": False,
        "observer_session_public_id": _typed_null(reason),
        "signed_batch_journal_closure": _typed_null(reason),
        "signed_batch_journal_closure_id": _typed_null(reason),
        "b3_attestation": _typed_null(reason),
        "b3_attestation_id": _typed_null(reason),
        "child_work": dict(work),
        **_locks(),
    }


def _finish_child_result(
    *,
    request: Mapping[str, Any],
    outcome: str,
    secret_verified: bool,
    signer_loaded: bool,
    work: Mapping[str, int],
) -> bytes:
    payload = _child_result_payload(
        request=request,
        outcome=outcome,
        secret_verified=secret_verified,
        signer_loaded=signer_loaded,
        work=work,
    )
    return _canonical(
        {**payload, "child_result_id": _hash("child_result", payload)}
    )


def _assert_child_runtime(
    *,
    expected_runtime_id: str,
    expected_source_snapshot_id: str,
    expected_archive_sha256: str,
    expected_archive_size: int,
    archive_fd: int,
) -> None:
    archive = _read_sealed_fd(archive_fd, cap=MAX_SOURCE_ARCHIVE_BYTES)
    entries = _archive_entries(archive)
    source_payload = _source_payload(
        archive_sha256=hashlib.sha256(archive).hexdigest(),
        archive_byte_count=len(archive),
        entries=entries,
    )
    if (
        hashlib.sha256(archive).hexdigest() != expected_archive_sha256
        or len(archive) != expected_archive_size
        or _hash("source_snapshot", source_payload)
        != expected_source_snapshot_id
    ):
        _fail("sealed child source snapshot identity changed")
    runtime_payload = _runtime_payload()
    flags = runtime_payload["required_flags"]
    actual_safe_path = (
        bool(sys.flags.safe_path) if hasattr(sys.flags, "safe_path") else None
    )
    if (
        sys.flags.isolated != flags["isolated"]
        or sys.flags.no_site != flags["no_site"]
        or sys.flags.ignore_environment != flags["ignore_environment"]
        or actual_safe_path != flags["safe_path"]
        or _hash("runtime", runtime_payload) != expected_runtime_id
    ):
        _fail("sealed child runtime identity or flags changed")
    archive_origin = f"/proc/self/fd/{archive_fd}"
    if (
        not str(Path(__file__)).startswith(archive_origin)
        and not __file__.startswith(archive_origin)
    ):
        _fail("sealed child imported IPC code from live workspace")


def _sealed_child_main(
    *,
    archive_fd: int,
    private_material_fd: int,
    expected_source_snapshot_id: str,
    expected_archive_sha256: str,
    expected_archive_size: int,
    expected_runtime_id: str,
    expected_program_id: str,
    repository_root: str,
    signer_private_root: str,
    signer_private_key_path: str,
) -> int:
    """Child-only entry.  It emits one frame and never serializes secrets."""

    request: dict[str, Any] | None = None
    secret_read = 0
    secret_verified_count = 0
    signer_attempts = 0
    signer_successes = 0
    try:
        _assert_child_runtime(
            expected_runtime_id=expected_runtime_id,
            expected_source_snapshot_id=expected_source_snapshot_id,
            expected_archive_sha256=expected_archive_sha256,
            expected_archive_size=expected_archive_size,
            archive_fd=archive_fd,
        )
        raw = _read_child_frame(sys.stdin.buffer, cap=MAX_REQUEST_BYTES)
        request = verify_v075_sealed_observer_finalize_request_bytes_v1(
            raw
        ).to_document()
        if (
            request["source_snapshot_id"] != expected_source_snapshot_id
            or request["runtime_id"] != expected_runtime_id
            or request["service_program_id"] != expected_program_id
        ):
            _fail("child request crossed source/runtime/program identities")
        secret_read = 1
        secret = _read_sealed_fd(
            private_material_fd,
            cap=MAX_PRIVATE_MATERIAL_BYTES,
        )
        try:
            commitment = _private_material_commitment(secret)
        except V075SignerOwningSealedObserverIPCV1InvariantViolation:
            commitment = ""
        if commitment != request["private_material_commitment_id"]:
            result = _finish_child_result(
                request=request,
                outcome="PRIVATE_MATERIAL_COMMITMENT_MISMATCH",
                secret_verified=False,
                signer_loaded=False,
                work=_child_work(
                    secret_read=secret_read,
                    secret_verified=secret_verified_count,
                    signer_load_attempts=signer_attempts,
                    signer_load_successes=signer_successes,
                ),
            )
            _write_child_frame(
                sys.stdout.buffer,
                result,
                cap=MAX_CHILD_RESULT_BYTES,
            )
            return 0
        secret_verified_count = 1
        signer_attempts = 1
        try:
            registry = _registry_from_document(request["signer_registry"])
            signer = (
                signer_runtime
                .load_v075_production_observer_evidence_signer_v1(
                    repository_root=Path(repository_root),
                    private_root=Path(signer_private_root),
                    private_key_path=Path(signer_private_key_path),
                    signer_registry=registry,
                )
            )
            if (
                signer.public_verification_key_v1()
                != registry.observer_evidence_key
            ):
                raise signer_runtime.V075ProductionPrivateSignerInvariantViolation(
                    "foreign signer"
                )
        except (
            OSError,
            TypeError,
            ValueError,
            signer_runtime.V075ProductionPrivateSignerInvariantViolation,
        ):
            result = _finish_child_result(
                request=request,
                outcome="SIGNER_LOAD_FAILED",
                secret_verified=True,
                signer_loaded=False,
                work=_child_work(
                    secret_read=secret_read,
                    secret_verified=secret_verified_count,
                    signer_load_attempts=signer_attempts,
                    signer_load_successes=signer_successes,
                ),
            )
            _write_child_frame(
                sys.stdout.buffer,
                result,
                cap=MAX_CHILD_RESULT_BYTES,
            )
            return 0
        signer_successes = 1
        # Fail closed: no closure/B3 input is admitted, and this Stage-A
        # service has not yet opened and retained an observer session.
        result = _finish_child_result(
            request=request,
            outcome="SESSION_OWNERSHIP_NOT_YET_COMPLETE",
            secret_verified=True,
            signer_loaded=True,
            work=_child_work(
                secret_read=secret_read,
                secret_verified=secret_verified_count,
                signer_load_attempts=signer_attempts,
                signer_load_successes=signer_successes,
            ),
        )
        _write_child_frame(
            sys.stdout.buffer,
            result,
            cap=MAX_CHILD_RESULT_BYTES,
        )
        return 0
    except BaseException:
        # An unclassified child failure is never upgraded into a self-reported
        # semantic artifact with an unverifiable work vector.  The supervisor
        # closes it as a typed transport noncertificate instead.
        return 91 if request is None else 92


_BOOTSTRAP_SOURCE = r"""
import fcntl
import hashlib
import importlib
import os
import sys

archive_fd = int(sys.argv[1])
private_fd = int(sys.argv[2])
expected_archive_sha256 = sys.argv[3]
expected_archive_size = int(sys.argv[4])
expected_source_id = sys.argv[5]
expected_runtime_id = sys.argv[6]
expected_program_id = sys.argv[7]
repository_root = sys.argv[8]
private_root = sys.argv[9]
private_key_path = sys.argv[10]
required_seals = 0x0008 | 0x0004 | 0x0002 | 0x0001
if fcntl.fcntl(archive_fd, 1034) & required_seals != required_seals:
    raise SystemExit(71)
status = os.fstat(archive_fd)
if status.st_size != expected_archive_size:
    raise SystemExit(72)
digest = hashlib.sha256()
offset = 0
while offset < status.st_size:
    chunk = os.pread(
        archive_fd,
        min(1024 * 1024, status.st_size - offset),
        offset,
    )
    if not chunk:
        raise SystemExit(73)
    digest.update(chunk)
    offset += len(chunk)
if digest.hexdigest() != expected_archive_sha256:
    raise SystemExit(74)
archive_path = "/proc/self/fd/" + str(archive_fd)
sys.path.insert(0, archive_path)
module = importlib.import_module(
    "acfqp.v075_signer_owning_sealed_observer_ipc_v1"
)
raise SystemExit(
    module._sealed_child_main(
        archive_fd=archive_fd,
        private_material_fd=private_fd,
        expected_source_snapshot_id=expected_source_id,
        expected_archive_sha256=expected_archive_sha256,
        expected_archive_size=expected_archive_size,
        expected_runtime_id=expected_runtime_id,
        expected_program_id=expected_program_id,
        repository_root=repository_root,
        signer_private_root=private_root,
        signer_private_key_path=private_key_path,
    )
)
""".strip()
_BOOTSTRAP_SHA256 = hashlib.sha256(
    _BOOTSTRAP_SOURCE.encode("utf-8")
).hexdigest()


def _child_argv(
    *,
    profile: V075SignerOwningSealedObserverServiceProfileV1,
    archive_fd: int,
    private_material_fd: int,
    repository_root: Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
) -> list[str]:
    profile._assert_current()
    return [
        sys.executable,
        "-I",
        "-S",
        "-c",
        _BOOTSTRAP_SOURCE,
        str(archive_fd),
        str(private_material_fd),
        profile.source_archive_sha256,
        str(profile.source_archive_byte_count),
        profile.source_snapshot_id,
        profile.runtime_id,
        profile.program_id,
        os.fspath(repository_root),
        os.fspath(signer_private_root),
        os.fspath(signer_private_key_path),
    ]


def _terminate(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.kill()
        except (ProcessLookupError, OSError):
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except (ProcessLookupError, OSError):
            pass


def _capture_start(process: subprocess.Popen[bytes]) -> dict[str, Any]:
    try:
        pgid = os.getpgid(process.pid)
        stat_text = Path(f"/proc/{process.pid}/stat").read_text(
            encoding="ascii"
        )
        tail = stat_text[stat_text.rfind(")") + 2 :].split()
        start_ticks = int(tail[19])
        executable = Path(os.readlink(f"/proc/{process.pid}/exe")).resolve(
            strict=True
        )
        raw = executable.read_bytes()
    except (OSError, ValueError, IndexError) as error:
        raise V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "supervisor could not capture child process identity"
        ) from error
    if pgid != process.pid:
        _fail("child is not the leader of its isolated process group")
    return {
        "pid": process.pid,
        "pgid": pgid,
        "start_ticks": start_ticks,
        "executable_sha256": hashlib.sha256(raw).hexdigest(),
        "executable_byte_count": len(raw),
    }


def _exchange(
    process: subprocess.Popen[bytes],
    *,
    request_raw: bytes,
    deadline: float,
) -> tuple[bytes | None, bytes, int | None, str | None]:
    if process.stdin is None or process.stdout is None or process.stderr is None:
        _fail("child lacks exact protocol pipes")
    outbound = _frame(request_raw, cap=MAX_REQUEST_BYTES)
    stdin_fd = process.stdin.fileno()
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    for fd in (stdin_fd, stdout_fd, stderr_fd):
        os.set_blocking(fd, False)
    outbound_offset = 0
    stdin_open = True
    readable = {stdout_fd, stderr_fd}
    stdout = bytearray()
    stderr = bytearray()
    expected_stdout: int | None = None
    failure: str | None = None
    while stdin_open or readable:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            failure = "CHILD_TIMEOUT"
            _terminate(process)
            break
        ready_read, ready_write, _ = select.select(
            list(readable),
            [stdin_fd] if stdin_open else [],
            [],
            remaining,
        )
        if not ready_read and not ready_write:
            failure = "CHILD_TIMEOUT"
            _terminate(process)
            break
        if stdin_open and stdin_fd in ready_write:
            try:
                written = os.write(
                    stdin_fd,
                    outbound[outbound_offset : outbound_offset + 64 * 1024],
                )
            except (BrokenPipeError, OSError):
                written = 0
                failure = "CHILD_CRASH"
                _terminate(process)
            outbound_offset += written
            if outbound_offset == len(outbound):
                process.stdin.close()
                process.stdin = None
                stdin_open = False
        for fd in tuple(ready_read):
            try:
                chunk = os.read(fd, 64 * 1024)
            except OSError:
                chunk = b""
            if not chunk:
                readable.discard(fd)
                continue
            if fd == stderr_fd:
                stderr.extend(chunk)
                if len(stderr) > MAX_STDERR_BYTES:
                    failure = "CHILD_STDERR_CAP_EXCEEDED"
                    _terminate(process)
                continue
            stdout.extend(chunk)
            if expected_stdout is None and len(stdout) >= _FRAME_WIDTH:
                try:
                    length = _parse_frame_header(
                        bytes(stdout[:_FRAME_WIDTH]),
                        cap=MAX_CHILD_RESULT_BYTES,
                    )
                    expected_stdout = _FRAME_WIDTH + length
                except V075SignerOwningSealedObserverIPCV1InvariantViolation:
                    failure = "CHILD_FRAME_INVALID"
                    _terminate(process)
            if (
                expected_stdout is not None
                and len(stdout) > expected_stdout
            ):
                failure = "CHILD_EXTRA_OUTPUT"
                _terminate(process)
            if len(stdout) > _FRAME_WIDTH + MAX_CHILD_RESULT_BYTES:
                failure = "CHILD_OUTPUT_CAP_EXCEEDED"
                _terminate(process)
        if process.poll() is not None and stdin_open and not readable:
            failure = failure or "CHILD_CRASH"
            _terminate(process)
            break
    if process.poll() is None:
        remaining = max(0.001, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            failure = failure or "CHILD_TIMEOUT"
            _terminate(process)
    exit_code = process.poll()
    if failure is None:
        if stderr:
            failure = "CHILD_STDERR_FORBIDDEN"
        elif exit_code != 0:
            failure = "CHILD_CRASH"
        elif expected_stdout is None or len(stdout) != expected_stdout:
            failure = "CHILD_FRAME_INVALID"
    child_raw = (
        None
        if failure is not None
        else bytes(stdout[_FRAME_WIDTH:])
    )
    return child_raw, bytes(stderr), exit_code, failure


_CHILD_RESULT_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "terminal_scope",
        "terminal_class",
        "terminal_code",
        "profile_id",
        "service_program_id",
        "source_snapshot_id",
        "runtime_id",
        "request_id",
        "request_nonce",
        "session_external_id",
        "private_material_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "ordered_stream_ids",
        "sealed_private_material_commitment_verified",
        "sealed_child_signer_loader_completed",
        "signer_loader_completion_is_process_attestation_not_crypto_proof",
        "observer_session_owned_from_open",
        "private_replay_performed",
        "b3_sign_performed",
        "observer_session_public_id",
        "signed_batch_journal_closure",
        "signed_batch_journal_closure_id",
        "b3_attestation",
        "b3_attestation_id",
        "child_work",
        "source_authority_complete",
        "code_provenance_complete",
        "portable_semantic_registry_complete",
        "fresh_heldout_accessed",
        "official_execution_allowed",
        "production_authorizing",
        "scientific_endpoint_credit_allowed",
        "plan_certificate",
        "infeasibility_certificate",
        "private_material_serialized",
        "child_result_id",
    }
)


def _validate_child_result(
    raw: bytes,
    *,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    item = _exact(
        _load(raw, label="child result", cap=MAX_CHILD_RESULT_BYTES),
        _CHILD_RESULT_KEYS,
        label="child result",
    )
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_observer_child_result.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["terminal_scope"] != TERMINAL_SCOPE
        or item["terminal_class"] != TERMINAL_CLASS
        or any(
            item[key] != request[key]
            for key in (
                "profile_id",
                "service_program_id",
                "source_snapshot_id",
                "runtime_id",
                "request_id",
                "request_nonce",
                "session_external_id",
                "private_material_commitment_id",
                "signer_registry_id",
                "observer_evidence_key_id",
                "ordered_stream_ids",
            )
        )
        or item["observer_session_owned_from_open"] is not False
        or item["private_replay_performed"] is not False
        or item["b3_sign_performed"] is not False
        or item["signer_loader_completion_is_process_attestation_not_crypto_proof"]
        is not True
        or any(item[key] is not False for key in _locks())
    ):
        _fail("child result crossed request identities or overclaims")
    for key in (
        "observer_session_public_id",
        "signed_batch_journal_closure",
        "signed_batch_journal_closure_id",
        "b3_attestation",
        "b3_attestation_id",
    ):
        _require_typed_null(
            item[key],
            reason=_terminal_output_null_reason(item["terminal_code"]),
            label=f"child result {key}",
        )
    expected_work_keys = set(
        _child_work(
            secret_read=0,
            secret_verified=0,
            signer_load_attempts=0,
            signer_load_successes=0,
        )
    )
    if (
        type(item["child_work"]) is not dict
        or set(item["child_work"]) != expected_work_keys
        or any(
            type(value) is not int or value < 0
            for value in item["child_work"].values()
        )
    ):
        _fail("child result work accounting is incomplete")
    outcome = item["terminal_code"]
    status_matrix = {
        "SESSION_OWNERSHIP_NOT_YET_COMPLETE": (True, True),
        "PRIVATE_MATERIAL_COMMITMENT_MISMATCH": (False, False),
        "SIGNER_LOAD_FAILED": (True, False),
    }
    work_matrix = {
        "SESSION_OWNERSHIP_NOT_YET_COMPLETE": _child_work(
            secret_read=1,
            secret_verified=1,
            signer_load_attempts=1,
            signer_load_successes=1,
        ),
        "PRIVATE_MATERIAL_COMMITMENT_MISMATCH": _child_work(
            secret_read=1,
            secret_verified=0,
            signer_load_attempts=0,
            signer_load_successes=0,
        ),
        "SIGNER_LOAD_FAILED": _child_work(
            secret_read=1,
            secret_verified=1,
            signer_load_attempts=1,
            signer_load_successes=0,
        ),
    }
    if (
        outcome not in status_matrix
        or (
            item["sealed_private_material_commitment_verified"],
            item["sealed_child_signer_loader_completed"],
        )
        != status_matrix[outcome]
        or item["child_work"] != work_matrix[outcome]
        or item["child_work"]["production_signer_load_successes"]
        > item["child_work"]["production_signer_load_attempts"]
        or item["child_work"]["signer_load_challenge_signatures"]
        != item["child_work"]["production_signer_load_successes"]
    ):
        _fail("child result outcome and work matrix disagree")
    payload = {
        key: value for key, value in item.items() if key != "child_result_id"
    }
    if _hash("child_result", payload) != item["child_result_id"]:
        _fail("child result content identity changed")
    return item


@dataclass(slots=True)
class _WorkRecorder:
    source_archive_stage_attempts: int = 0
    process_launch_attempts: int = 0
    process_identity_capture_attempts: int = 0
    process_launches: int = 0
    process_exit_successes: int = 0
    process_exit_failures: int = 0
    parent_to_child_frames: int = 0
    child_to_parent_frames: int = 0
    parent_to_child_payload_bytes: int = 0
    child_to_parent_payload_bytes: int = 0
    framing_bytes: int = 0
    source_archive_staged_bytes: int = 0
    source_archive_seal_checks: int = 0
    private_material_seal_checks_parent: int = 0
    process_identity_checks: int = 0
    supervisor_checks: int = 0
    request_raw_replay_calls_parent: int = 0
    child_result_raw_replay_calls_parent: int = 0
    nonce_rejections: int = 0
    source_archive_staging_failure_events: int = 0
    process_launch_failure_events: int = 0
    process_identity_capture_failure_events: int = 0
    supervisor_protocol_failure_events: int = 0
    child_result_validation_failure_events: int = 0
    timeout_events: int = 0
    crash_events: int = 0
    stderr_bytes: int = 0

    def document(self, *, profile_id: str, request_id: str) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.v075_signer_owning_observer_work.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": profile_id,
            "request_id": request_id,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
            "native_zero_required": True,
            "all_failure_path_work_retained": True,
        }
        return {**payload, "work_id": _hash("work", payload)}


def _process_document(
    *,
    start: Mapping[str, Any] | None,
    exit_code: int | None,
    launched: bool,
    reaped: bool,
) -> dict[str, Any]:
    if not launched:
        identity_reason = "NOT_LAUNCHED"
    elif start is None:
        identity_reason = "PROCESS_IDENTITY_CAPTURE_FAILED"
    else:
        identity_reason = ""
    payload = {
        "schema": "acfqp.v075_signer_owning_observer_process.v1",
        "schema_version": SCHEMA_VERSION,
        "launched": launched,
        "identity_capture_complete": launched and start is not None,
        "pid": (
            start["pid"] if start is not None else _typed_null(identity_reason)
        ),
        "pgid": (
            start["pgid"] if start is not None else _typed_null(identity_reason)
        ),
        "start_ticks": (
            start["start_ticks"]
            if start is not None
            else _typed_null(identity_reason)
        ),
        "executable_sha256": (
            start["executable_sha256"]
            if start is not None
            else _typed_null(identity_reason)
        ),
        "executable_byte_count": (
            start["executable_byte_count"]
            if start is not None
            else _typed_null(identity_reason)
        ),
        "exit_code": (
            exit_code
            if exit_code is not None
            else _typed_null("NOT_LAUNCHED")
        ),
        "leader_reaped": reaped,
    }
    return {**payload, "process_id": _hash("process", payload)}


def _invalid_child_payload_id(
    *,
    payload_sha256: str,
    payload_byte_count: int,
) -> str:
    _cid(payload_sha256, "invalid child payload digest")
    if type(payload_byte_count) is not int or payload_byte_count <= 0:
        _fail("invalid child payload byte count is malformed")
    payload = {
        "schema": (
            "acfqp.v075_signer_owning_observer_invalid_child_payload.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "payload_sha256": payload_sha256,
        "payload_byte_count": payload_byte_count,
        "raw_payload_serialized": False,
    }
    return _hash("invalid_child_payload", payload)


def _journal_from_specs(
    specs: list[tuple[str, str, str, str, int]],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    prior = hashlib.sha256(
        b"acfqp:v075-signer-owning-observer-journal-initial:v1"
    ).hexdigest()
    for index, (
        direction,
        kind,
        message_id,
        payload_sha256,
        payload_byte_count,
    ) in enumerate(specs):
        payload = {
            "schema": "acfqp.v075_signer_owning_observer_journal_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "index": index,
            "direction": direction,
            "message_kind": kind,
            "message_id": message_id,
            "payload_sha256": payload_sha256,
            "payload_byte_count": payload_byte_count,
            "prior_entry_id": prior,
        }
        entry = {
            **payload,
            "journal_entry_id": _hash("journal_entry", payload),
        }
        entries.append(entry)
        prior = entry["journal_entry_id"]
    payload = {
        "schema": "acfqp.v075_signer_owning_observer_journal.v1",
        "schema_version": SCHEMA_VERSION,
        "entries": entries,
        "entry_count": len(entries),
        "head_id": prior,
        "exact_protocol_order": True,
    }
    return {**payload, "journal_id": _hash("journal", payload)}


def _journal_document(
    *,
    request_raw: bytes,
    request_id: str,
    child_raw: bytes | None,
    child_result_id: str | None,
    sent: bool,
) -> dict[str, Any]:
    if (
        type(request_raw) is not bytes
        or not request_raw
        or type(sent) is not bool
        or (child_result_id is not None and child_raw is None)
        or (child_raw is not None and not sent)
    ):
        _fail("journal source messages are malformed")
    specs = [
        (
            "PARENT_TO_CHILD" if sent else "PARENT_VALIDATION",
            "FINALIZE_REQUEST" if sent else "REJECTED_FINALIZE_REQUEST",
            request_id,
            hashlib.sha256(request_raw).hexdigest(),
            len(request_raw),
        )
    ]
    if child_raw is not None:
        child_digest = hashlib.sha256(child_raw).hexdigest()
        child_size = len(child_raw)
        if child_result_id is not None:
            message_kind = "TYPED_NONCERTIFICATE_RESULT"
            message_id = child_result_id
        else:
            message_kind = "UNTYPED_INVALID_CHILD_RESULT"
            message_id = _invalid_child_payload_id(
                payload_sha256=child_digest,
                payload_byte_count=child_size,
            )
        specs.append(
            (
                "CHILD_TO_PARENT",
                message_kind,
                message_id,
                child_digest,
                child_size,
            )
        )
    return _journal_from_specs(specs)


def _invalid_child_journal_from_metadata(
    *,
    request_raw: bytes,
    request_id: str,
    payload_sha256: str,
    payload_byte_count: int,
) -> dict[str, Any]:
    return _journal_from_specs(
        [
            (
                "PARENT_TO_CHILD",
                "FINALIZE_REQUEST",
                request_id,
                hashlib.sha256(request_raw).hexdigest(),
                len(request_raw),
            ),
            (
                "CHILD_TO_PARENT",
                "UNTYPED_INVALID_CHILD_RESULT",
                _invalid_child_payload_id(
                    payload_sha256=payload_sha256,
                    payload_byte_count=payload_byte_count,
                ),
                payload_sha256,
                payload_byte_count,
            ),
        ]
    )


def _supervisor_document(
    *,
    profile_id: str,
    request_id: str,
    process_id: str,
    child_result_id: str | None,
    outcome: str,
    nonce: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_signer_owning_observer_supervisor.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "request_id": request_id,
        "process_id": process_id,
        "child_result_id": (
            child_result_id
            if child_result_id is not None
            else _typed_null("NO_VALID_CHILD_RESULT")
        ),
        "supervisor_nonce": nonce,
        "outcome": outcome,
        "local_process_attestation_only": True,
        "cryptographic_process_provenance": False,
        "os_sandbox_claimed": False,
    }
    return {**payload, "supervisor_id": _hash("supervisor", payload)}


def _result_document(
    *,
    profile: V075SignerOwningSealedObserverServiceProfileV1,
    request: Mapping[str, Any],
    request_raw: bytes,
    outcome: str,
    child: Mapping[str, Any] | None,
    child_raw: bytes | None,
    process: Mapping[str, Any],
    supervisor: Mapping[str, Any],
    journal: Mapping[str, Any],
    work: Mapping[str, Any],
    stderr: bytes,
) -> dict[str, Any]:
    reason = _terminal_output_null_reason(outcome)
    payload = {
        "schema": "acfqp.v075_signer_owning_sealed_observer_ipc_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": outcome,
        "profile_id": profile.profile_id,
        "service_program_id": profile.program_id,
        "source_snapshot_id": profile.source_snapshot_id,
        "runtime": {
            **deepcopy(dict(profile.runtime_document)),
            "runtime_id": profile.runtime_id,
        },
        "runtime_id": profile.runtime_id,
        "request_id": request["request_id"],
        "request_nonce": request["request_nonce"],
        "session_external_id": request["session_external_id"],
        "private_material_commitment_id": (
            request["private_material_commitment_id"]
        ),
        "signer_registry_id": request["signer_registry_id"],
        "observer_evidence_key_id": request["observer_evidence_key_id"],
        "ordered_stream_ids": request["ordered_stream_ids"],
        "request_sha256": hashlib.sha256(request_raw).hexdigest(),
        "request_byte_count": len(request_raw),
        "child_result": (
            dict(child)
            if child is not None
            else _typed_null("NO_VALID_CHILD_RESULT")
        ),
        "child_result_id": (
            child["child_result_id"]
            if child is not None
            else _typed_null("NO_VALID_CHILD_RESULT")
        ),
        "observer_session_public_id": _typed_null(reason),
        "signed_batch_journal_closure": _typed_null(reason),
        "signed_batch_journal_closure_id": _typed_null(reason),
        "b3_attestation": _typed_null(reason),
        "b3_attestation_id": _typed_null(reason),
        "observer_session_owned_from_open": False,
        "private_replay_performed": False,
        "b3_sign_performed": False,
        "process": dict(process),
        "process_id": process["process_id"],
        "supervisor": dict(supervisor),
        "supervisor_id": supervisor["supervisor_id"],
        "journal": dict(journal),
        "journal_id": journal["journal_id"],
        "work": dict(work),
        "work_id": work["work_id"],
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stderr_byte_count": len(stderr),
        **_locks(),
    }
    return {**payload, "result_id": _hash("result", payload)}


@dataclass(frozen=True, slots=True)
class V075SignerOwningSealedObserverIPCResultV1:
    _document: Mapping[str, Any] = field(repr=False)
    _raw: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        item = _validate_result_document(dict(self._document))
        raw = _canonical(item)
        object.__setattr__(
            self,
            "_document",
            MappingProxyType(
                _load(raw, label="final IPC result", cap=MAX_FINAL_RESULT_BYTES)
            ),
        )
        object.__setattr__(self, "_raw", raw)

    def _current_document(self) -> dict[str, Any]:
        item = _validate_result_document(
            _load(
                self._raw,
                label="final IPC result",
                cap=MAX_FINAL_RESULT_BYTES,
            )
        )
        if _canonical(item) != self._raw:
            _fail("final IPC result cached bytes changed")
        return item

    @property
    def result_id(self) -> str:
        return self._current_document()["result_id"]

    @property
    def terminal_code(self) -> str:
        return self._current_document()["terminal_code"]

    @property
    def canonical_bytes(self) -> bytes:
        self._current_document()
        if len(self._raw) > MAX_FINAL_RESULT_BYTES:
            _fail("final signer-owning IPC result exceeds its cap")
        return self._raw

    def to_document(self) -> dict[str, Any]:
        return self._current_document()


def _validate_hashed_document(
    value: Any,
    *,
    role: str,
    id_key: str,
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or id_key not in value:
        _fail(f"{label} is missing")
    _cid(value[id_key], f"{label} identity")
    payload = {key: child for key, child in value.items() if key != id_key}
    if _hash(role, payload) != value[id_key]:
        _fail(f"{label} content identity changed")
    return value


def _validate_runtime_document(value: Any) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "implementation",
            "version",
            "executable_sha256",
            "executable_byte_count",
            "required_flags",
            "runtime_id",
        },
        label="runtime artifact",
    )
    _validate_hashed_document(
        item,
        role="runtime",
        id_key="runtime_id",
        label="runtime artifact",
    )
    flags = _exact(
        item["required_flags"],
        {"isolated", "no_site", "ignore_environment", "safe_path"},
        label="runtime flags",
    )
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_observer_runtime.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or type(item["implementation"]) is not str
        or not item["implementation"]
        or type(item["version"]) is not list
        or len(item["version"]) != 3
        or any(type(part) is not int or part < 0 for part in item["version"])
        or _cid(item["executable_sha256"], "runtime executable")
        != item["executable_sha256"]
        or type(item["executable_byte_count"]) is not int
        or item["executable_byte_count"] <= 0
        or type(flags["isolated"]) is not int
        or flags["isolated"] != 1
        or type(flags["no_site"]) is not int
        or flags["no_site"] != 1
        or type(flags["ignore_environment"]) is not int
        or flags["ignore_environment"] != 1
        or (
            flags["safe_path"] is not True
            and flags["safe_path"] is not None
        )
    ):
        _fail("runtime artifact is malformed")
    return item


def _validate_process_document(value: Any) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "launched",
            "identity_capture_complete",
            "pid",
            "pgid",
            "start_ticks",
            "executable_sha256",
            "executable_byte_count",
            "exit_code",
            "leader_reaped",
            "process_id",
        },
        label="process artifact",
    )
    _validate_hashed_document(
        item,
        role="process",
        id_key="process_id",
        label="process artifact",
    )
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_observer_process.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or type(item["launched"]) is not bool
        or type(item["identity_capture_complete"]) is not bool
        or item["leader_reaped"] is not True
    ):
        _fail("process artifact status is malformed")
    if item["launched"] and item["identity_capture_complete"]:
        if (
            type(item["pid"]) is not int
            or item["pid"] <= 0
            or type(item["pgid"]) is not int
            or item["pgid"] != item["pid"]
            or type(item["start_ticks"]) is not int
            or item["start_ticks"] < 0
            or _cid(
                item["executable_sha256"],
                "process executable",
            )
            != item["executable_sha256"]
            or type(item["executable_byte_count"]) is not int
            or item["executable_byte_count"] <= 0
            or type(item["exit_code"]) is not int
        ):
            _fail("launched process artifact is malformed")
    elif item["launched"]:
        if type(item["exit_code"]) is not int:
            _fail("identity-capture failure lacks a reaped exit status")
        for key in (
            "pid",
            "pgid",
            "start_ticks",
            "executable_sha256",
            "executable_byte_count",
        ):
            _require_typed_null(
                item[key],
                reason="PROCESS_IDENTITY_CAPTURE_FAILED",
                label=f"uncaptured process {key}",
            )
    else:
        if item["identity_capture_complete"] is not False:
            _fail("nonlaunched process claims captured identity")
        for key in (
            "pid",
            "pgid",
            "start_ticks",
            "executable_sha256",
            "executable_byte_count",
            "exit_code",
        ):
            _require_typed_null(
                item[key],
                reason="NOT_LAUNCHED",
                label=f"nonlaunched process {key}",
            )
    return item


def _validate_supervisor_document(value: Any) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "profile_id",
            "request_id",
            "process_id",
            "child_result_id",
            "supervisor_nonce",
            "outcome",
            "local_process_attestation_only",
            "cryptographic_process_provenance",
            "os_sandbox_claimed",
            "supervisor_id",
        },
        label="supervisor artifact",
    )
    _validate_hashed_document(
        item,
        role="supervisor",
        id_key="supervisor_id",
        label="supervisor artifact",
    )
    for key in (
        "profile_id",
        "request_id",
        "process_id",
        "supervisor_nonce",
    ):
        _cid(item[key], f"supervisor {key}")
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_observer_supervisor.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["outcome"] not in _ALLOWED_TERMINAL_CODES
        or item["local_process_attestation_only"] is not True
        or item["cryptographic_process_provenance"] is not False
        or item["os_sandbox_claimed"] is not False
        or type(item["child_result_id"]) not in {str, dict}
    ):
        _fail("supervisor artifact overclaims or is malformed")
    if type(item["child_result_id"]) is str:
        _cid(item["child_result_id"], "supervisor child result")
    else:
        _require_typed_null(
            item["child_result_id"],
            reason="NO_VALID_CHILD_RESULT",
            label="supervisor child result",
        )
    return item


def _validate_journal_document(value: Any) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "entries",
            "entry_count",
            "head_id",
            "exact_protocol_order",
            "journal_id",
        },
        label="journal artifact",
    )
    _validate_hashed_document(
        item,
        role="journal",
        id_key="journal_id",
        label="journal artifact",
    )
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_observer_journal.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or type(item["entries"]) is not list
        or not item["entries"]
        or type(item["entry_count"]) is not int
        or item["entry_count"] != len(item["entries"])
        or item["entry_count"] not in {1, 2}
        or item["exact_protocol_order"] is not True
    ):
        _fail("journal artifact is malformed")
    prior = hashlib.sha256(
        b"acfqp:v075-signer-owning-observer-journal-initial:v1"
    ).hexdigest()
    for index, value in enumerate(item["entries"]):
        entry = _exact(
            value,
            {
                "schema",
                "schema_version",
                "index",
                "direction",
                "message_kind",
                "message_id",
                "payload_sha256",
                "payload_byte_count",
                "prior_entry_id",
                "journal_entry_id",
            },
            label="journal entry",
        )
        _validate_hashed_document(
            entry,
            role="journal_entry",
            id_key="journal_entry_id",
            label="journal entry",
        )
        if (
            entry["schema"]
            != "acfqp.v075_signer_owning_observer_journal_entry.v1"
            or entry["schema_version"] != SCHEMA_VERSION
            or entry["index"] != index
            or entry["direction"]
            not in {
                "PARENT_TO_CHILD",
                "PARENT_VALIDATION",
                "CHILD_TO_PARENT",
            }
            or type(entry["message_kind"]) is not str
            or not entry["message_kind"]
            or _cid(entry["message_id"], "journal message")
            != entry["message_id"]
            or _cid(entry["payload_sha256"], "journal payload")
            != entry["payload_sha256"]
            or type(entry["payload_byte_count"]) is not int
            or entry["payload_byte_count"] <= 0
            or entry["prior_entry_id"] != prior
        ):
            _fail("journal entry is malformed or out of order")
        if index == 0:
            if (
                entry["direction"],
                entry["message_kind"],
            ) not in {
                ("PARENT_TO_CHILD", "FINALIZE_REQUEST"),
                ("PARENT_VALIDATION", "REJECTED_FINALIZE_REQUEST"),
            }:
                _fail("journal request entry kind is unregistered")
        elif (
            entry["direction"] != "CHILD_TO_PARENT"
            or entry["message_kind"]
            not in {
                "TYPED_NONCERTIFICATE_RESULT",
                "UNTYPED_INVALID_CHILD_RESULT",
            }
        ):
            _fail("journal child entry kind is unregistered")
        if (
            entry["message_kind"] == "UNTYPED_INVALID_CHILD_RESULT"
            and entry["message_id"]
            != _invalid_child_payload_id(
                payload_sha256=entry["payload_sha256"],
                payload_byte_count=entry["payload_byte_count"],
            )
        ):
            _fail("invalid child journal message identity changed")
        prior = entry["journal_entry_id"]
    if item["head_id"] != prior:
        _fail("journal head differs from its exact chain")
    if (
        item["entry_count"] == 2
        and (
            item["entries"][0]["direction"] != "PARENT_TO_CHILD"
            or item["entries"][0]["message_kind"] != "FINALIZE_REQUEST"
        )
    ) or (
        item["entries"][0]["direction"] == "PARENT_VALIDATION"
        and item["entry_count"] != 1
    ):
        _fail("journal request/child entry sequence is impossible")
    return item


def _validate_work_document(value: Any) -> dict[str, Any]:
    counter_keys = set(_WorkRecorder.__dataclass_fields__)
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "profile_id",
            "request_id",
            *counter_keys,
            "native_zero_required",
            "all_failure_path_work_retained",
            "work_id",
        },
        label="work artifact",
    )
    _validate_hashed_document(
        item,
        role="work",
        id_key="work_id",
        label="work artifact",
    )
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_observer_work.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["native_zero_required"] is not True
        or item["all_failure_path_work_retained"] is not True
        or any(
            type(item[key]) is not int or item[key] < 0
            for key in counter_keys
        )
    ):
        _fail("work artifact is incomplete or malformed")
    unit_counters = {
        key
        for key in counter_keys
        if key
        not in {
            "parent_to_child_payload_bytes",
            "child_to_parent_payload_bytes",
            "framing_bytes",
            "source_archive_staged_bytes",
            "stderr_bytes",
        }
    }
    if (
        any(item[key] not in {0, 1} for key in unit_counters)
        or item["process_launches"] > item["process_launch_attempts"]
        or item["process_identity_capture_attempts"]
        > item["process_launches"]
        or item["process_identity_checks"]
        > item["process_identity_capture_attempts"]
        or item["process_exit_successes"]
        + item["process_exit_failures"]
        != item["process_launches"]
        or item["source_archive_seal_checks"]
        > item["source_archive_stage_attempts"]
        or item["parent_to_child_frames"] > item["process_launches"]
        or item["child_to_parent_frames"] > item["parent_to_child_frames"]
        or item["child_result_raw_replay_calls_parent"]
        != item["child_to_parent_frames"]
        or item["framing_bytes"]
        != _FRAME_WIDTH
        * (
            item["parent_to_child_frames"]
            + item["child_to_parent_frames"]
        )
    ):
        _fail("work artifact counters fail exact reconciliation")
    _cid(item["profile_id"], "work profile")
    _cid(item["request_id"], "work request")
    return item


def _validate_result_document(document: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "terminal_scope",
        "terminal_class",
        "terminal_code",
        "profile_id",
        "service_program_id",
        "source_snapshot_id",
        "runtime",
        "runtime_id",
        "request_id",
        "request_nonce",
        "session_external_id",
        "private_material_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "ordered_stream_ids",
        "request_sha256",
        "request_byte_count",
        "child_result",
        "child_result_id",
        "observer_session_public_id",
        "signed_batch_journal_closure",
        "signed_batch_journal_closure_id",
        "b3_attestation",
        "b3_attestation_id",
        "observer_session_owned_from_open",
        "private_replay_performed",
        "b3_sign_performed",
        "process",
        "process_id",
        "supervisor",
        "supervisor_id",
        "journal",
        "journal_id",
        "work",
        "work_id",
        "stderr_sha256",
        "stderr_byte_count",
        *set(_locks()),
        "result_id",
    }
    item = _exact(document, required, label="final signer-owning IPC result")
    if (
        item["schema"]
        != "acfqp.v075_signer_owning_sealed_observer_ipc_result.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["terminal_scope"] != TERMINAL_SCOPE
        or item["terminal_class"] != TERMINAL_CLASS
        or item["terminal_code"] not in _ALLOWED_TERMINAL_CODES
        or item["observer_session_owned_from_open"] is not False
        or item["private_replay_performed"] is not False
        or item["b3_sign_performed"] is not False
        or any(item[key] is not False for key in _locks())
        or type(item["ordered_stream_ids"]) is not list
        or not item["ordered_stream_ids"]
        or sorted(set(item["ordered_stream_ids"]))
        != item["ordered_stream_ids"]
    ):
        _fail("final signer-owning IPC result overclaims")
    for key in (
        "profile_id",
        "service_program_id",
        "source_snapshot_id",
        "runtime_id",
        "request_id",
        "request_nonce",
        "session_external_id",
        "private_material_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "request_sha256",
        "stderr_sha256",
        "result_id",
    ):
        _cid(item[key], f"final result {key}")
    for value in item["ordered_stream_ids"]:
        _cid(value, "final result stream")
    for key in (
        "observer_session_public_id",
        "signed_batch_journal_closure",
        "signed_batch_journal_closure_id",
        "b3_attestation",
        "b3_attestation_id",
    ):
        _require_typed_null(
            item[key],
            reason=_terminal_output_null_reason(item["terminal_code"]),
            label=f"final result {key}",
        )
    runtime = _validate_runtime_document(item["runtime"])
    process = _validate_process_document(item["process"])
    supervisor = _validate_supervisor_document(item["supervisor"])
    journal = _validate_journal_document(item["journal"])
    work = _validate_work_document(item["work"])
    if (
        process["process_id"] != item["process_id"]
        or supervisor["supervisor_id"] != item["supervisor_id"]
        or journal["journal_id"] != item["journal_id"]
        or work["work_id"] != item["work_id"]
        or runtime["runtime_id"] != item["runtime_id"]
        or supervisor["process_id"] != process["process_id"]
        or supervisor["request_id"] != item["request_id"]
        or supervisor["profile_id"] != item["profile_id"]
        or supervisor["outcome"] != item["terminal_code"]
        or work["profile_id"] != item["profile_id"]
        or work["request_id"] != item["request_id"]
        or work["process_launches"] != int(process["launched"])
        or work["process_identity_checks"]
        != int(process["identity_capture_complete"])
        or work["process_exit_successes"]
        != int(
            process["launched"]
            and type(process["exit_code"]) is int
            and process["exit_code"] == 0
        )
        or work["process_exit_failures"]
        != int(
            process["launched"]
            and type(process["exit_code"]) is int
            and process["exit_code"] != 0
        )
        or type(item["request_byte_count"]) is not int
        or item["request_byte_count"] <= 0
        or type(item["stderr_byte_count"]) is not int
        or item["stderr_byte_count"] < 0
    ):
        _fail("final signer-owning IPC nested identities differ")
    if (
        process["launched"]
        and process["identity_capture_complete"]
        and (
            process["executable_sha256"]
            != runtime["executable_sha256"]
            or process["executable_byte_count"]
            != runtime["executable_byte_count"]
        )
    ):
        _fail("launched process executable differs from profile runtime")
    if (
        item["terminal_code"] in _PRELAUNCH_TERMINAL_CODES
        and process["launched"]
    ) or (
        item["terminal_code"] not in _PRELAUNCH_TERMINAL_CODES
        and not process["launched"]
    ):
        _fail("final result process state disagrees with terminal outcome")
    terminal = item["terminal_code"]
    expected_stage_attempt = int(terminal != "NONCE_REPLAY_REJECTED")
    expected_launch_attempt = int(
        terminal
        not in {
            "NONCE_REPLAY_REJECTED",
            "SOURCE_ARCHIVE_STAGING_FAILED",
        }
    )
    expected_launch = int(terminal not in _PRELAUNCH_TERMINAL_CODES)
    expected_capture_attempt = expected_launch
    expected_capture_success = int(
        expected_launch
        and terminal != "PROCESS_IDENTITY_CAPTURE_FAILED"
    )
    expected_sent = int(
        expected_capture_success
        and terminal != "PROCESS_IDENTITY_CAPTURE_FAILED"
    )
    expected_child_frame = int(
        terminal in _CHILD_TERMINAL_CODES
        or terminal == "CHILD_RESULT_VALIDATION_FAILED"
    )
    expected_events = {
        "nonce_rejections": int(terminal == "NONCE_REPLAY_REJECTED"),
        "source_archive_staging_failure_events": int(
            terminal == "SOURCE_ARCHIVE_STAGING_FAILED"
        ),
        "process_launch_failure_events": int(
            terminal == "PROCESS_LAUNCH_FAILED"
        ),
        "process_identity_capture_failure_events": int(
            terminal == "PROCESS_IDENTITY_CAPTURE_FAILED"
        ),
        "supervisor_protocol_failure_events": int(
            terminal == "SUPERVISOR_PROTOCOL_FAILURE"
        ),
        "child_result_validation_failure_events": int(
            terminal == "CHILD_RESULT_VALIDATION_FAILED"
        ),
        "timeout_events": int(terminal == "CHILD_TIMEOUT"),
        "crash_events": int(
            terminal
            in {
                "CHILD_CRASH",
                "CHILD_FRAME_INVALID",
                "CHILD_EXTRA_OUTPUT",
                "CHILD_OUTPUT_CAP_EXCEEDED",
                "CHILD_STDERR_CAP_EXCEEDED",
                "CHILD_STDERR_FORBIDDEN",
            }
        ),
    }
    if (
        work["source_archive_stage_attempts"] != expected_stage_attempt
        or work["process_launch_attempts"] != expected_launch_attempt
        or work["process_launches"] != expected_launch
        or work["process_identity_capture_attempts"]
        != expected_capture_attempt
        or work["process_identity_checks"] != expected_capture_success
        or work["parent_to_child_frames"] != expected_sent
        or work["child_to_parent_frames"] != expected_child_frame
        or work["request_raw_replay_calls_parent"] != 1
        or work["private_material_seal_checks_parent"] != 1
        or work["supervisor_checks"] != 1
        or any(work[key] != value for key, value in expected_events.items())
    ):
        _fail("final result outcome and native work vector disagree")
    request_entry = journal["entries"][0]
    if (
        request_entry["message_id"] != item["request_id"]
        or request_entry["payload_sha256"] != item["request_sha256"]
        or request_entry["payload_byte_count"] != item["request_byte_count"]
        or request_entry["direction"]
        != ("PARENT_TO_CHILD" if expected_sent else "PARENT_VALIDATION")
        or request_entry["message_kind"]
        != (
            "FINALIZE_REQUEST"
            if expected_sent
            else "REJECTED_FINALIZE_REQUEST"
        )
    ):
        _fail("final result request journal entry differs")
    if expected_child_frame:
        if journal["entry_count"] != 2:
            _fail("final result omits its received child journal entry")
        child_entry = journal["entries"][1]
        expected_child_kind = (
            "UNTYPED_INVALID_CHILD_RESULT"
            if terminal == "CHILD_RESULT_VALIDATION_FAILED"
            else "TYPED_NONCERTIFICATE_RESULT"
        )
        if (
            child_entry["message_kind"] != expected_child_kind
            or child_entry["payload_byte_count"]
            != work["child_to_parent_payload_bytes"]
        ):
            _fail("final result child journal/work evidence differs")
        if terminal == "CHILD_RESULT_VALIDATION_FAILED":
            if child_entry["message_id"] != _invalid_child_payload_id(
                payload_sha256=child_entry["payload_sha256"],
                payload_byte_count=child_entry["payload_byte_count"],
            ):
                _fail("invalid child result journal evidence changed")
    elif journal["entry_count"] != 1:
        _fail("final result contains an impossible child journal entry")
    if type(item["child_result"]) is dict and "child_result_id" in item[
        "child_result"
    ]:
        request_projection = {
            key: item[key]
            for key in (
                "profile_id",
                "service_program_id",
                "source_snapshot_id",
                "runtime_id",
                "request_id",
                "request_nonce",
                "session_external_id",
                "private_material_commitment_id",
                "signer_registry_id",
                "observer_evidence_key_id",
                "ordered_stream_ids",
            )
        }
        child_raw = _canonical(item["child_result"])
        child = _validate_child_result(
            child_raw,
            request=request_projection,
        )
        child_entry = journal["entries"][1]
        if (
            child["child_result_id"] != item["child_result_id"]
            or type(supervisor["child_result_id"]) is not str
            or supervisor["child_result_id"] != child["child_result_id"]
            or supervisor["child_result_id"] != item["child_result_id"]
            or child["terminal_code"] != item["terminal_code"]
            or child_entry["message_id"] != item["child_result_id"]
            or child_entry["payload_sha256"]
            != hashlib.sha256(child_raw).hexdigest()
            or child_entry["payload_byte_count"] != len(child_raw)
        ):
            _fail("final result child identity differs")
    elif (
        item["terminal_code"] not in _NO_CHILD_TERMINAL_CODES
    ):
        _fail("final result lacks its mandatory child result")
    else:
        _require_typed_null(
            item["child_result"],
            reason="NO_VALID_CHILD_RESULT",
            label="final child result",
        )
        top_child_result_id = _require_typed_null(
            item["child_result_id"],
            reason="NO_VALID_CHILD_RESULT",
            label="final child result identity",
        )
        supervisor_child_result_id = _require_typed_null(
            supervisor["child_result_id"],
            reason="NO_VALID_CHILD_RESULT",
            label="supervisor child result identity",
        )
        if supervisor_child_result_id != top_child_result_id:
            _fail("supervisor child result identity differs from final result")
    payload = {key: value for key, value in item.items() if key != "result_id"}
    if _hash("result", payload) != item["result_id"]:
        _fail("final signer-owning IPC result identity changed")
    return item


class V075SignerOwningSealedObserverServiceV1:
    """One local nonce-consuming Stage-A supervisor."""

    __slots__ = ("profile", "_consumed_nonces", "_lock")

    def __init__(
        self,
        profile: V075SignerOwningSealedObserverServiceProfileV1,
    ) -> None:
        if type(profile) is not V075SignerOwningSealedObserverServiceProfileV1:
            _fail("signer-owning service requires one exact profile")
        profile._assert_current()
        self.profile = profile
        self._consumed_nonces: set[str] = set()
        self._lock = threading.Lock()

    def consume_nonce(self, nonce: str) -> bool:
        _cid(nonce, "service request nonce")
        with self._lock:
            if nonce in self._consumed_nonces:
                return False
            self._consumed_nonces.add(nonce)
            return True

    def __reduce__(self) -> NoReturn:
        raise TypeError("signer-owning services are process-local")


def start_v075_signer_owning_sealed_observer_service_v1(
    *,
    profile: V075SignerOwningSealedObserverServiceProfileV1,
) -> V075SignerOwningSealedObserverServiceV1:
    return V075SignerOwningSealedObserverServiceV1(profile)


def _prelaunch_nonce_result(
    *,
    profile: V075SignerOwningSealedObserverServiceProfileV1,
    request: Mapping[str, Any],
    request_raw: bytes,
) -> V075SignerOwningSealedObserverIPCResultV1:
    recorder = _WorkRecorder(
        private_material_seal_checks_parent=1,
        request_raw_replay_calls_parent=1,
        nonce_rejections=1,
        supervisor_checks=1,
    )
    process = _process_document(
        start=None,
        exit_code=None,
        launched=False,
        reaped=True,
    )
    journal = _journal_document(
        request_raw=request_raw,
        request_id=request["request_id"],
        child_raw=None,
        child_result_id=None,
        sent=False,
    )
    work = recorder.document(
        profile_id=profile.profile_id,
        request_id=request["request_id"],
    )
    supervisor = _supervisor_document(
        profile_id=profile.profile_id,
        request_id=request["request_id"],
        process_id=process["process_id"],
        child_result_id=None,
        outcome="NONCE_REPLAY_REJECTED",
        nonce=hashlib.sha256(os.urandom(32)).hexdigest(),
    )
    return V075SignerOwningSealedObserverIPCResultV1(
        _result_document(
            profile=profile,
            request=request,
            request_raw=request_raw,
            outcome="NONCE_REPLAY_REJECTED",
            child=None,
            child_raw=None,
            process=process,
            supervisor=supervisor,
            journal=journal,
            work=work,
            stderr=b"",
        )
    )


def _close_supervisor_result(
    *,
    profile: V075SignerOwningSealedObserverServiceProfileV1,
    request: Mapping[str, Any],
    request_raw: bytes,
    outcome: str,
    recorder: _WorkRecorder,
    process: subprocess.Popen[bytes] | None,
    start: Mapping[str, Any] | None,
    child: Mapping[str, Any] | None,
    child_raw: bytes | None,
    stderr: bytes,
    exit_code: int | None,
) -> V075SignerOwningSealedObserverIPCResultV1:
    launched = process is not None
    if launched and process.poll() is None:
        _terminate(process)
    if launched:
        exit_code = process.poll()
        if type(exit_code) is not int:
            _fail("launched child could not be reaped")
    process_document = _process_document(
        start=start,
        exit_code=exit_code,
        launched=launched,
        reaped=(not launched or process.poll() is not None),
    )
    sent = recorder.parent_to_child_frames == 1
    journal = _journal_document(
        request_raw=request_raw,
        request_id=request["request_id"],
        child_raw=child_raw,
        child_result_id=(
            None if child is None else child["child_result_id"]
        ),
        sent=sent,
    )
    recorder.supervisor_checks = 1
    work = recorder.document(
        profile_id=profile.profile_id,
        request_id=request["request_id"],
    )
    supervisor = _supervisor_document(
        profile_id=profile.profile_id,
        request_id=request["request_id"],
        process_id=process_document["process_id"],
        child_result_id=(
            None if child is None else child["child_result_id"]
        ),
        outcome=outcome,
        nonce=hashlib.sha256(os.urandom(32)).hexdigest(),
    )
    return V075SignerOwningSealedObserverIPCResultV1(
        _result_document(
            profile=profile,
            request=request,
            request_raw=request_raw,
            outcome=outcome,
            child=child,
            child_raw=child_raw if child is not None else None,
            process=process_document,
            supervisor=supervisor,
            journal=journal,
            work=work,
            stderr=stderr,
        )
    )


def execute_v075_signer_owning_sealed_observer_finalize_v1(
    *,
    service: V075SignerOwningSealedObserverServiceV1,
    request_bytes: bytes,
    repository_root: Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
    sealed_private_material_fd: int,
) -> V075SignerOwningSealedObserverIPCResultV1:
    """Run one child-only signer load and fail closed before post-hoc B3."""

    if type(service) is not V075SignerOwningSealedObserverServiceV1:
        _fail("signer-owning execute received a foreign service")
    profile = service.profile
    profile._assert_current()
    request_object = verify_v075_sealed_observer_finalize_request_bytes_v1(
        request_bytes
    )
    request = request_object.to_document()
    if (
        request["profile_id"] != profile.profile_id
        or request["service_program_id"] != profile.program_id
        or request["source_snapshot_id"] != profile.source_snapshot_id
        or request["runtime_id"] != profile.runtime_id
    ):
        _fail("finalize request was transplanted across service profiles")
    # Structural path and descriptor checks are non-consuming preflight.  A
    # caller may repair either input and retry the same public request nonce.
    for value, label in (
        (repository_root, "repository root"),
        (signer_private_root, "signer private root"),
        (signer_private_key_path, "signer private key path"),
    ):
        if not isinstance(value, Path) or not value.is_absolute():
            _fail(f"{label} must be one absolute pathlib.Path")
    _verify_sealed_fd(
        sealed_private_material_fd,
        cap=MAX_PRIVATE_MATERIAL_BYTES,
    )
    if not service.consume_nonce(request["request_nonce"]):
        return _prelaunch_nonce_result(
            profile=profile,
            request=request,
            request_raw=request_bytes,
        )

    recorder = _WorkRecorder(
        private_material_seal_checks_parent=1,
        request_raw_replay_calls_parent=1,
    )
    archive_fd: int | None = None
    process: subprocess.Popen[bytes] | None = None
    start: dict[str, Any] | None = None
    child_raw: bytes | None = None
    child: dict[str, Any] | None = None
    stderr = b""
    exit_code: int | None = None
    failure: str | None = None
    operation_stage = "SOURCE_ARCHIVE_STAGING"
    try:
        recorder.source_archive_stage_attempts = 1
        archive_fd = _stage_sealed_bytes(
            profile._archive_bytes,
            name=f"acfqp-v075-stage-a-{profile.source_snapshot_id[:12]}",
            cap=MAX_SOURCE_ARCHIVE_BYTES,
        )
        recorder.source_archive_staged_bytes = profile.source_archive_byte_count
        recorder.source_archive_seal_checks = 1
        operation_stage = "PROCESS_LAUNCH"
        recorder.process_launch_attempts = 1
        with tempfile.TemporaryDirectory(
            prefix="acfqp-v075-signer-owning-observer-"
        ) as sandbox:
            environment = {
                "LC_ALL": "C.UTF-8",
                "LANG": "C.UTF-8",
                "TZ": "UTC",
                "PYTHONHASHSEED": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            process = subprocess.Popen(
                _child_argv(
                    profile=profile,
                    archive_fd=archive_fd,
                    private_material_fd=sealed_private_material_fd,
                    repository_root=repository_root,
                    signer_private_root=signer_private_root,
                    signer_private_key_path=signer_private_key_path,
                ),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=sandbox,
                env=environment,
                close_fds=True,
                pass_fds=(archive_fd, sealed_private_material_fd),
                start_new_session=True,
            )
            recorder.process_launches = 1
            operation_stage = "PROCESS_IDENTITY_CAPTURE"
            recorder.process_identity_capture_attempts = 1
            start = _capture_start(process)
            recorder.process_identity_checks = 1
            operation_stage = "SUPERVISOR_PROTOCOL"
            recorder.parent_to_child_frames = 1
            recorder.parent_to_child_payload_bytes = len(request_bytes)
            recorder.framing_bytes = _FRAME_WIDTH
            child_raw, stderr, exit_code, failure = _exchange(
                process,
                request_raw=request_bytes,
                deadline=(
                    time.monotonic()
                    + profile.timeout_milliseconds / 1000
                ),
            )
            _terminate(process)
            recorder.stderr_bytes = len(stderr)
            if child_raw is not None:
                recorder.child_to_parent_frames = 1
                recorder.child_to_parent_payload_bytes = len(child_raw)
                recorder.framing_bytes += _FRAME_WIDTH
                recorder.child_result_raw_replay_calls_parent = 1
                operation_stage = "CHILD_RESULT_VALIDATION"
                child = _validate_child_result(
                    child_raw,
                    request=request,
                )
            if failure == "CHILD_TIMEOUT":
                recorder.timeout_events = 1
            elif failure is not None:
                recorder.crash_events = 1
    except BaseException:
        if process is not None:
            _terminate(process)
        failure_matrix = {
            "SOURCE_ARCHIVE_STAGING": "SOURCE_ARCHIVE_STAGING_FAILED",
            "PROCESS_LAUNCH": "PROCESS_LAUNCH_FAILED",
            "PROCESS_IDENTITY_CAPTURE": (
                "PROCESS_IDENTITY_CAPTURE_FAILED"
            ),
            "SUPERVISOR_PROTOCOL": "SUPERVISOR_PROTOCOL_FAILURE",
            "CHILD_RESULT_VALIDATION": "CHILD_RESULT_VALIDATION_FAILED",
        }
        failure = failure_matrix[operation_stage]
        if failure == "SOURCE_ARCHIVE_STAGING_FAILED":
            recorder.source_archive_staging_failure_events = 1
        elif failure == "PROCESS_LAUNCH_FAILED":
            recorder.process_launch_failure_events = 1
        elif failure == "PROCESS_IDENTITY_CAPTURE_FAILED":
            recorder.process_identity_capture_failure_events = 1
        elif failure == "CHILD_RESULT_VALIDATION_FAILED":
            recorder.child_result_validation_failure_events = 1
            child = None
        else:
            recorder.supervisor_protocol_failure_events = 1
            child = None
    finally:
        if process is not None:
            _terminate(process)
            exit_code = process.poll()
            if type(exit_code) is int and exit_code == 0:
                recorder.process_exit_successes = 1
            else:
                recorder.process_exit_failures = 1
        if archive_fd is not None:
            try:
                os.close(archive_fd)
            except OSError:
                pass

    outcome = (
        child["terminal_code"]
        if child is not None
        else failure or "CHILD_CRASH"
    )
    return _close_supervisor_result(
        profile=profile,
        request=request,
        request_raw=request_bytes,
        outcome=outcome,
        recorder=recorder,
        process=process,
        start=start,
        child=child,
        child_raw=child_raw,
        stderr=stderr,
        exit_code=exit_code,
    )


def verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
    *,
    raw: bytes,
    request_bytes: bytes,
    profile: V075SignerOwningSealedObserverServiceProfileV1,
) -> V075SignerOwningSealedObserverIPCResultV1:
    """Public raw replay of the bounded noncertificate envelope."""

    if type(profile) is not V075SignerOwningSealedObserverServiceProfileV1:
        _fail("result verifier profile is untyped")
    request = verify_v075_sealed_observer_finalize_request_bytes_v1(
        request_bytes
    ).to_document()
    result = V075SignerOwningSealedObserverIPCResultV1(
        _load(raw, label="final IPC result", cap=MAX_FINAL_RESULT_BYTES)
    )
    document = result.to_document()
    expected_runtime = {
        **deepcopy(dict(profile.runtime_document)),
        "runtime_id": profile.runtime_id,
    }
    if (
        document["profile_id"] != profile.profile_id
        or document["service_program_id"] != profile.program_id
        or document["source_snapshot_id"] != profile.source_snapshot_id
        or document["runtime_id"] != profile.runtime_id
        or document["runtime"] != expected_runtime
        or document["request_id"] != request["request_id"]
        or document["request_nonce"] != request["request_nonce"]
        or document["session_external_id"]
        != request["session_external_id"]
        or document["private_material_commitment_id"]
        != request["private_material_commitment_id"]
        or document["signer_registry_id"]
        != request["signer_registry_id"]
        or document["observer_evidence_key_id"]
        != request["observer_evidence_key_id"]
        or document["ordered_stream_ids"]
        != request["ordered_stream_ids"]
        or document["request_sha256"]
        != hashlib.sha256(request_bytes).hexdigest()
        or document["request_byte_count"] != len(request_bytes)
    ):
        _fail("final IPC result was transplanted across request or profile")
    child = document["child_result"]
    process = document["process"]
    if type(child) is dict and "child_result_id" in child:
        child_raw = _canonical(child)
        replayed_child = _validate_child_result(
            child_raw,
            request=request,
        )
        if (
            replayed_child != child
            or document["terminal_code"] != child["terminal_code"]
        ):
            _fail("final IPC child result differs from raw replay")
        expected_journal = _journal_document(
            request_raw=request_bytes,
            request_id=request["request_id"],
            child_raw=child_raw,
            child_result_id=child["child_result_id"],
            sent=True,
        )
    elif document["terminal_code"] == "CHILD_RESULT_VALIDATION_FAILED":
        invalid_entry = document["journal"]["entries"][1]
        expected_journal = _invalid_child_journal_from_metadata(
            request_raw=request_bytes,
            request_id=request["request_id"],
            payload_sha256=invalid_entry["payload_sha256"],
            payload_byte_count=invalid_entry["payload_byte_count"],
        )
    else:
        if document["terminal_code"] not in _NO_CHILD_TERMINAL_CODES:
            _fail("final IPC result lacks its required child artifact")
        expected_journal = _journal_document(
            request_raw=request_bytes,
            request_id=request["request_id"],
            child_raw=None,
            child_result_id=None,
            sent=document["work"]["parent_to_child_frames"] == 1,
        )
    if document["journal"] != expected_journal:
        _fail("final IPC journal differs from exact request/child replay")
    work = document["work"]
    launched = bool(process["launched"])
    child_present = type(child) is dict and "child_result_id" in child
    terminal = document["terminal_code"]
    stage_attempted = terminal != "NONCE_REPLAY_REJECTED"
    source_staged = terminal not in {
        "NONCE_REPLAY_REJECTED",
        "SOURCE_ARCHIVE_STAGING_FAILED",
    }
    launch_attempted = source_staged
    identity_attempted = launched
    identity_captured = bool(process["identity_capture_complete"])
    sent = identity_captured
    child_frame = child_present or terminal == "CHILD_RESULT_VALIDATION_FAILED"
    exit_code = process["exit_code"]
    exited_zero = launched and type(exit_code) is int and exit_code == 0
    expected_counts = {
        "source_archive_stage_attempts": int(stage_attempted),
        "process_launch_attempts": int(launch_attempted),
        "process_identity_capture_attempts": int(identity_attempted),
        "process_launches": int(launched),
        "process_exit_successes": int(exited_zero),
        "process_exit_failures": int(launched and not exited_zero),
        "parent_to_child_frames": int(sent),
        "child_to_parent_frames": int(child_frame),
        "parent_to_child_payload_bytes": (
            len(request_bytes) if sent else 0
        ),
        "child_to_parent_payload_bytes": (
            len(_canonical(child)) if child_present else 0
        ),
        "framing_bytes": (
            _FRAME_WIDTH * (int(sent) + int(child_frame))
        ),
        "source_archive_staged_bytes": (
            profile.source_archive_byte_count if source_staged else 0
        ),
        "source_archive_seal_checks": int(source_staged),
        "private_material_seal_checks_parent": 1,
        "process_identity_checks": int(identity_captured),
        "supervisor_checks": 1,
        "request_raw_replay_calls_parent": 1,
        "child_result_raw_replay_calls_parent": int(child_frame),
        "nonce_rejections": int(
            terminal == "NONCE_REPLAY_REJECTED"
        ),
        "source_archive_staging_failure_events": int(
            terminal == "SOURCE_ARCHIVE_STAGING_FAILED"
        ),
        "process_launch_failure_events": int(
            terminal == "PROCESS_LAUNCH_FAILED"
        ),
        "process_identity_capture_failure_events": int(
            terminal == "PROCESS_IDENTITY_CAPTURE_FAILED"
        ),
        "supervisor_protocol_failure_events": int(
            terminal == "SUPERVISOR_PROTOCOL_FAILURE"
        ),
        "child_result_validation_failure_events": int(
            terminal == "CHILD_RESULT_VALIDATION_FAILED"
        ),
        "timeout_events": int(terminal == "CHILD_TIMEOUT"),
        "crash_events": int(
            launched
            and not child_present
            and terminal
            in {
                "CHILD_CRASH",
                "CHILD_FRAME_INVALID",
                "CHILD_EXTRA_OUTPUT",
                "CHILD_OUTPUT_CAP_EXCEEDED",
                "CHILD_STDERR_CAP_EXCEEDED",
                "CHILD_STDERR_FORBIDDEN",
            }
        ),
        "stderr_bytes": document["stderr_byte_count"],
    }
    if terminal == "CHILD_RESULT_VALIDATION_FAILED":
        if work["child_to_parent_payload_bytes"] <= 0:
            _fail("invalid child result work omits received payload bytes")
        expected_counts["child_to_parent_payload_bytes"] = work[
            "child_to_parent_payload_bytes"
        ]
    if any(work[key] != value for key, value in expected_counts.items()):
        _fail("final IPC work differs from exact protocol replay")
    return result


def open_v075_signer_owning_sealed_observer_production_v1() -> NoReturn:
    raise V075SignerOwningSealedObserverProductionV1NotReady(
        "contract-1.69 Stage A owns the signer process but not yet one "
        "observer session from open through finalize; B3, production, "
        "registry, scientific, and certificate claims remain locked"
    )


__all__ = [
    "B3_ISSUANCE_ALLOWED",
    "CODE_PROVENANCE_COMPLETE",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "MAX_CHILD_RESULT_BYTES",
    "MAX_FINAL_RESULT_BYTES",
    "MAX_PRIVATE_MATERIAL_BYTES",
    "MAX_REQUEST_BYTES",
    "OBSERVER_SESSION_OWNERSHIP_COMPLETE",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "V075SealedObserverFinalizeRequestV1",
    "V075SignerOwningSealedObserverIPCV1InvariantViolation",
    "V075SignerOwningSealedObserverIPCResultV1",
    "V075SignerOwningSealedObserverProductionV1NotReady",
    "V075SignerOwningSealedObserverServiceProfileV1",
    "V075SignerOwningSealedObserverServiceV1",
    "execute_v075_signer_owning_sealed_observer_finalize_v1",
    "freeze_v075_sealed_observer_finalize_request_v1",
    "freeze_v075_signer_owning_sealed_observer_service_profile_v1",
    "open_v075_signer_owning_sealed_observer_production_v1",
    "start_v075_signer_owning_sealed_observer_service_v1",
    "verify_v075_sealed_observer_finalize_request_bytes_v1",
    "verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1",
]
