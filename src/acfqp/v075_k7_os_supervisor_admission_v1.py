"""Fail-closed host admission for the future K7 OS supervisor.

The probe performs bounded, read-only inspection only.  It never launches a
child, creates a cgroup, writes a controller file, or turns host primitives
into execution authority. Raw source bytes exist only on the probe stack; the
artifact retains bounded byte counts and digests. A delegated-parent directory
descriptor is a mandatory input to the future lease constructor; this revision
deliberately does not implement that mutating lease validation. Consequently
every issued result is ``NOT_AVAILABLE`` and every formal lock remains false.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_OS_SUPERVISOR_ADMISSION_PROBE_V1_DOMAIN,
    V075_K7_OS_SUPERVISOR_ADMISSION_PROFILE_V1_DOMAIN,
    V075_K7_OS_SUPERVISOR_ADMISSION_RESULT_V1_DOMAIN,
    V075_K7_OS_SUPERVISOR_READ_EVIDENCE_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.94.0"
PROFILE_KEY = "v075_k7_os_supervisor_admission_v1"
MAX_SOURCE_BYTES = 1024 * 1024
REQUIRED_CONTROLLERS = ("memory", "pids")
REQUIRED_LEAF_FILES = (
    "cgroup.events",
    "cgroup.procs",
    "cgroup.threads",
    "cgroup.type",
    "cgroup.max.depth",
    "cgroup.max.descendants",
    "memory.peak",
    "pids.current",
    "pids.max",
)

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_OS_SUPERVISOR_READ_EVIDENCE_V1_DOMAIN",
    "V075_K7_OS_SUPERVISOR_ADMISSION_PROFILE_V1_DOMAIN",
    "V075_K7_OS_SUPERVISOR_ADMISSION_PROBE_V1_DOMAIN",
    "V075_K7_OS_SUPERVISOR_ADMISSION_RESULT_V1_DOMAIN",
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_OS_SUPERVISOR_READ_EVIDENCE_V1_DOMAIN,
        V075_K7_OS_SUPERVISOR_ADMISSION_PROFILE_V1_DOMAIN,
        V075_K7_OS_SUPERVISOR_ADMISSION_PROBE_V1_DOMAIN,
        V075_K7_OS_SUPERVISOR_ADMISSION_RESULT_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("K7 OS-supervisor admission domains are unregistered")

OS_SOURCE_PROVENANCE_VERIFIED = False
DELEGATED_CGROUP_LEASE_VERIFIED = False
PIDFD_LIFECYCLE_VERIFIED = False
CHILD_LAUNCH_ALLOWED = False
COUNTER_RECORD_AUTHORIZED = False
WORK_VECTOR_AUTHORIZED = False
COMPARISON_VECTOR_AUTHORIZED = False
ACTUAL_PROJECTION_PROOF_AUTHORIZED = False
OFFICIAL_EXECUTION_ALLOWED = False

_PROFILE_ISSUER = object()
_READ_ISSUER = object()
_PROBE_ISSUER = object()
_RESULT_ISSUER = object()
_OCTAL_ESCAPE = re.compile(r"\\([0-7]{3})")


class V075K7OSSupervisorAdmissionV1Error(ValueError):
    """A probe input, bounded read, or issued object was invalid."""


class K7OSSupervisorAdmissionStatusV1(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"


class K7OSSupervisorBlockerV1(str, Enum):
    NOT_POSIX = "NOT_POSIX"
    NOT_LINUX = "NOT_LINUX"
    PIDFD_OPEN_UNAVAILABLE = "PIDFD_OPEN_UNAVAILABLE"
    PIDFD_WAIT_UNAVAILABLE = "PIDFD_WAIT_UNAVAILABLE"
    PROC_SELF_CGROUP_UNREADABLE = "PROC_SELF_CGROUP_UNREADABLE"
    PROC_SELF_CGROUP_INVALID = "PROC_SELF_CGROUP_INVALID"
    PROC_SELF_MOUNTINFO_UNREADABLE = "PROC_SELF_MOUNTINFO_UNREADABLE"
    CGROUP2_MOUNT_UNRESOLVED = "CGROUP2_MOUNT_UNRESOLVED"
    CURRENT_CGROUP_UNRESOLVED = "CURRENT_CGROUP_UNRESOLVED"
    CURRENT_CGROUP_CONTROLLERS_UNREADABLE = (
        "CURRENT_CGROUP_CONTROLLERS_UNREADABLE"
    )
    REQUIRED_CONTROLLER_MISSING = "REQUIRED_CONTROLLER_MISSING"
    CURRENT_CGROUP_REQUIRED_FILE_MISSING = (
        "CURRENT_CGROUP_REQUIRED_FILE_MISSING"
    )
    CURRENT_CGROUP_FACT_UNOBSERVED = "CURRENT_CGROUP_FACT_UNOBSERVED"
    CURRENT_CGROUP_REQUIRED_FILE_UNOBSERVED = (
        "CURRENT_CGROUP_REQUIRED_FILE_UNOBSERVED"
    )
    CURRENT_CGROUP_NOT_WRITABLE = "CURRENT_CGROUP_NOT_WRITABLE"
    DELEGATED_CGROUP_PARENT_FD_NOT_SUPPLIED = (
        "DELEGATED_CGROUP_PARENT_FD_NOT_SUPPLIED"
    )
    DELEGATED_CGROUP_PARENT_FD_INVALID = (
        "DELEGATED_CGROUP_PARENT_FD_INVALID"
    )
    DELEGATED_PARENT_RUNTIME_LEASE_VALIDATION_NOT_IMPLEMENTED = (
        "DELEGATED_PARENT_RUNTIME_LEASE_VALIDATION_NOT_IMPLEMENTED"
    )


class K7OSSupervisorReadRoleV1(str, Enum):
    PROC_SELF_CGROUP = "PROC_SELF_CGROUP"
    PROC_SELF_MOUNTINFO = "PROC_SELF_MOUNTINFO"
    CURRENT_CGROUP_CONTROLLERS = "CURRENT_CGROUP_CONTROLLERS"
    CURRENT_CGROUP_SUBTREE_CONTROL = "CURRENT_CGROUP_SUBTREE_CONTROL"


def _fail(message: str) -> NoReturn:
    raise V075K7OSSupervisorAdmissionV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("K7 OS-supervisor admission used an undeclared domain")
    return content_id(domain, dict(payload))


def _locks() -> dict[str, bool]:
    return {
        "os_source_provenance_verified": OS_SOURCE_PROVENANCE_VERIFIED,
        "delegated_cgroup_lease_verified": DELEGATED_CGROUP_LEASE_VERIFIED,
        "pidfd_lifecycle_verified": PIDFD_LIFECYCLE_VERIFIED,
        "child_launch_allowed": CHILD_LAUNCH_ALLOWED,
        "counter_record_authorized": COUNTER_RECORD_AUTHORIZED,
        "work_vector_authorized": WORK_VECTOR_AUTHORIZED,
        "comparison_vector_authorized": COMPARISON_VECTOR_AUTHORIZED,
        "actual_projection_proof_authorized": (
            ACTUAL_PROJECTION_PROOF_AUTHORIZED
        ),
        "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
    }


def _read_bounded(path: Path, role: K7OSSupervisorReadRoleV1) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(os.fspath(path), flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"{role.value} source is not a regular pseudo-file")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, MAX_SOURCE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_SOURCE_BYTES:
                _fail(f"{role.value} source exceeds its byte cap")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            _fail(f"{role.value} source identity changed during read")
        return b"".join(chunks)
    except V075K7OSSupervisorAdmissionV1Error:
        raise
    except OSError as error:
        raise V075K7OSSupervisorAdmissionV1Error(
            f"{role.value} source is unavailable"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


@dataclass(frozen=True, slots=True)
class K7OSSupervisorAdmissionProfileV1:
    _issuer: InitVar[object]
    required_controllers: tuple[str, ...]
    required_leaf_files: tuple[str, ...]
    maximum_source_bytes: int
    _profile_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PROFILE_ISSUER
            or self.required_controllers != REQUIRED_CONTROLLERS
            or self.required_leaf_files != REQUIRED_LEAF_FILES
            or type(self.maximum_source_bytes) is not int
            or self.maximum_source_bytes != MAX_SOURCE_BYTES
        ):
            _fail("K7 OS-supervisor admission profile changed")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_OS_SUPERVISOR_ADMISSION_PROFILE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_os_supervisor_admission_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "required_controllers": list(self.required_controllers),
            "required_leaf_files": list(self.required_leaf_files),
            "maximum_source_bytes": self.maximum_source_bytes,
            "exclusive_attempt_leaf_required": True,
            "pids_max_required": 1,
            "cgroup_max_depth_required": 0,
            "cgroup_max_descendants_required": 0,
            "clone_into_cgroup_and_pidfd_required": True,
            "read_only_probe_only": True,
            "runtime_lease_validation_implemented": False,
            "formal_locks": _locks(),
        }

    @property
    def profile_id(self) -> str:
        current = _hash(
            V075_K7_OS_SUPERVISOR_ADMISSION_PROFILE_V1_DOMAIN,
            self._payload(),
        )
        if current != self._profile_id:
            _fail("K7 OS-supervisor admission profile changed after freeze")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "admission_profile_id": self.profile_id}


@lru_cache(maxsize=1)
def official_v075_k7_os_supervisor_admission_profile_v1(
) -> K7OSSupervisorAdmissionProfileV1:
    return K7OSSupervisorAdmissionProfileV1(
        _PROFILE_ISSUER,
        REQUIRED_CONTROLLERS,
        REQUIRED_LEAF_FILES,
        MAX_SOURCE_BYTES,
    )


@dataclass(frozen=True, slots=True)
class K7OSSupervisorReadEvidenceV1:
    _issuer: InitVar[object]
    role: K7OSSupervisorReadRoleV1
    source_path: str
    byte_count: int
    sha256: str
    _evidence_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _READ_ISSUER:
            _fail("OS-supervisor read evidence is issuer-owned")
        try:
            role = K7OSSupervisorReadRoleV1(self.role)
        except (TypeError, ValueError) as error:
            raise V075K7OSSupervisorAdmissionV1Error(
                "OS-supervisor read role is unknown"
            ) from error
        object.__setattr__(self, "role", role)
        if (
            type(self.source_path) is not str
            or not self.source_path.startswith("/")
            or len(self.source_path.encode("utf-8")) > 4096
            or "\x00" in self.source_path
            or os.path.normpath(self.source_path) != self.source_path
        ):
            _fail("OS-supervisor read path must be bounded and canonical")
        if (
            type(self.byte_count) is not int
            or not 0 <= self.byte_count <= MAX_SOURCE_BYTES
            or type(self.sha256) is not str
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
        ):
            _fail("OS-supervisor read digest or byte count is invalid")
        object.__setattr__(
            self,
            "_evidence_id",
            _hash(V075_K7_OS_SUPERVISOR_READ_EVIDENCE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_os_supervisor_read_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "read_role": self.role.value,
            "source_path": self.source_path,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "read_was_bounded": True,
            "source_bytes_retained": False,
            "source_semantics_verified": False,
            "formal_locks": _locks(),
        }

    @property
    def evidence_id(self) -> str:
        current = _hash(
            V075_K7_OS_SUPERVISOR_READ_EVIDENCE_V1_DOMAIN, self._payload()
        )
        if current != self._evidence_id:
            _fail("OS-supervisor read evidence changed after issuance")
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "read_evidence_id": self.evidence_id}


def _read_evidence(
    path: Path, role: K7OSSupervisorReadRoleV1
) -> tuple[K7OSSupervisorReadEvidenceV1, bytes]:
    raw = _read_bounded(path, role)
    return (
        K7OSSupervisorReadEvidenceV1(
            _READ_ISSUER,
            role,
            os.fspath(path),
            len(raw),
            hashlib.sha256(raw).hexdigest(),
        ),
        raw,
    )


def _decode(raw: bytes, role: K7OSSupervisorReadRoleV1) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeError as error:
        raise V075K7OSSupervisorAdmissionV1Error(
            f"{role.value} is not UTF-8"
        ) from error


def _unescape_mount(value: str) -> str:
    return _OCTAL_ESCAPE.sub(lambda match: chr(int(match.group(1), 8)), value)


def _self_cgroup_path(text: str) -> str:
    matches = [line[3:] for line in text.splitlines() if line.startswith("0::")]
    if len(matches) != 1:
        _fail("/proc/self/cgroup lacks one unified-v2 membership")
    value = matches[0]
    if not value.startswith("/") or "\x00" in value or ".." in value.split("/"):
        _fail("unified-v2 cgroup membership path is invalid")
    return value


def _cgroup2_mount(text: str, membership: str) -> tuple[str, str]:
    mounts: list[tuple[str, str]] = []
    for line in text.splitlines():
        fields = line.split(" ")
        try:
            separator = fields.index("-")
        except ValueError:
            continue
        if separator + 1 < len(fields) and fields[separator + 1] == "cgroup2":
            if len(fields) <= 4:
                continue
            root = _unescape_mount(fields[3])
            mountpoint = _unescape_mount(fields[4])
            if root.startswith("/") and mountpoint.startswith("/"):
                mounts.append((root, mountpoint))
    eligible = [
        item
        for item in mounts
        if item[0] == "/"
        or membership == item[0]
        or membership.startswith(item[0].rstrip("/") + "/")
    ]
    if not eligible:
        _fail("mountinfo has no cgroup2 mount covering current membership")
    longest = max(len(root.rstrip("/")) for root, _mountpoint in eligible)
    winners = sorted(
        set(
            item
            for item in eligible
            if len(item[0].rstrip("/")) == longest
        )
    )
    if len(winners) != 1:
        _fail("mountinfo has ambiguous cgroup2 mounts for current membership")
    return winners[0]


def _current_cgroup_directory(
    *, membership: str, mount_root: str, mountpoint: str
) -> Path:
    if mount_root == "/":
        relative = membership.lstrip("/")
    elif membership == mount_root:
        relative = ""
    else:
        relative = membership[len(mount_root.rstrip("/")) + 1 :]
    candidate = Path(mountpoint) / relative
    if ".." in candidate.parts:
        _fail("current cgroup directory escapes its mount")
    return candidate


@dataclass(frozen=True, slots=True)
class K7OSSupervisorPathFactV1:
    """Bounded stat/access fact; it grants no source semantics."""

    _issuer: InitVar[object]
    role: str
    path_sha256: str
    stat_observed: bool
    exists: bool
    device: int | None
    inode: int | None
    mode: int | None
    owner_uid: int | None
    owner_gid: int | None
    is_directory: bool
    is_regular: bool
    readable: bool
    writable: bool

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROBE_ISSUER:
            _fail("OS-supervisor path facts are probe-issued")
        if (
            type(self.role) is not str
            or not self.role
            or len(self.role) > 128
            or type(self.path_sha256) is not str
            or len(self.path_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.path_sha256
            )
        ):
            _fail("OS-supervisor path fact identity is invalid")
        for value in (
            self.stat_observed,
            self.exists,
            self.is_directory,
            self.is_regular,
            self.readable,
            self.writable,
        ):
            if type(value) is not bool:
                _fail("OS-supervisor path fact boolean is mistyped")
        stat_values = (
            self.device,
            self.inode,
            self.mode,
            self.owner_uid,
            self.owner_gid,
        )
        if not self.stat_observed:
            if self.exists or any(value is not None for value in stat_values) or any(
                (self.is_directory, self.is_regular, self.readable, self.writable)
            ):
                _fail("unobserved OS-supervisor path fact carries metadata")
        elif self.exists:
            if any(type(value) is not int or value < 0 for value in stat_values):
                _fail("existing OS-supervisor path fact lacks exact stat values")
        elif any(value is not None for value in stat_values) or any(
            (self.is_directory, self.is_regular, self.readable, self.writable)
        ):
            _fail("missing OS-supervisor path fact carries positive metadata")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "path_sha256": self.path_sha256,
            "stat_observed": self.stat_observed,
            "exists": self.exists,
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
            "owner_uid": self.owner_uid,
            "owner_gid": self.owner_gid,
            "is_directory": self.is_directory,
            "is_regular": self.is_regular,
            "readable": self.readable,
            "writable": self.writable,
            "source_semantics_verified": False,
        }


def _path_fact(path: Path, role: str) -> K7OSSupervisorPathFactV1:
    encoded = os.fspath(path).encode("utf-8")
    if len(encoded) > 4096:
        _fail("OS-supervisor fact path exceeds its cap")
    digest = hashlib.sha256(encoded).hexdigest()
    try:
        status = path.stat(follow_symlinks=False)
    except (FileNotFoundError, NotADirectoryError):
        return K7OSSupervisorPathFactV1(
            _PROBE_ISSUER,
            role,
            digest,
            True,
            False,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
        )
    except OSError:
        return K7OSSupervisorPathFactV1(
            _PROBE_ISSUER,
            role,
            digest,
            False,
            False,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
        )
    directory = stat.S_ISDIR(status.st_mode)
    return K7OSSupervisorPathFactV1(
        _PROBE_ISSUER,
        role,
        digest,
        True,
        True,
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
        directory,
        stat.S_ISREG(status.st_mode),
        os.access(path, os.R_OK | (os.X_OK if directory else 0)),
        os.access(path, os.W_OK | (os.X_OK if directory else 0)),
    )


def _descriptor_fact(descriptor: int | None) -> K7OSSupervisorPathFactV1:
    role = "DELEGATED_PARENT_DESCRIPTOR"
    if descriptor is None:
        return K7OSSupervisorPathFactV1(
            _PROBE_ISSUER,
            role,
            hashlib.sha256(b"NOT_SUPPLIED").hexdigest(),
            False,
            False,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
        )
    try:
        status = os.fstat(descriptor)
        target = os.readlink(f"/proc/self/fd/{descriptor}")
    except OSError:
        return K7OSSupervisorPathFactV1(
            _PROBE_ISSUER,
            role,
            hashlib.sha256(b"INVALID_DESCRIPTOR").hexdigest(),
            False,
            False,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
        )
    target_bytes = target.encode("utf-8")
    if len(target_bytes) > 4096:
        _fail("delegated descriptor target exceeds its cap")
    return K7OSSupervisorPathFactV1(
        _PROBE_ISSUER,
        role,
        hashlib.sha256(target_bytes).hexdigest(),
        True,
        True,
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
        stat.S_ISDIR(status.st_mode),
        stat.S_ISREG(status.st_mode),
        True,
        bool(
            stat.S_ISDIR(status.st_mode)
            and os.access(f"/proc/self/fd/{descriptor}", os.W_OK | os.X_OK)
        ),
    )


@dataclass(frozen=True, slots=True)
class K7OSSupervisorAdmissionProbeV1:
    _issuer: InitVar[object]
    profile_id: str
    read_evidence: tuple[K7OSSupervisorReadEvidenceV1, ...]
    posix_present: bool
    linux_present: bool
    pidfd_open_present: bool
    pidfd_wait_present: bool
    current_cgroup_path: str | None
    cgroup2_mount_root: str | None
    cgroup2_mount_path: str | None
    current_delegatable_controllers: tuple[str, ...]
    current_cgroup_directory_fact: K7OSSupervisorPathFactV1
    current_required_file_facts: tuple[K7OSSupervisorPathFactV1, ...]
    delegated_parent_fd_supplied: bool
    delegated_parent_fact: K7OSSupervisorPathFactV1
    blockers: tuple[K7OSSupervisorBlockerV1, ...]
    _probe_id: str = field(init=False, repr=False, compare=False)
    _validated_read_ids: tuple[str, ...] = field(
        init=False, repr=False, compare=False
    )
    _validated_fact_documents: tuple[dict[str, Any], ...] = field(
        init=False, repr=False, compare=False
    )
    _validated_blocker_values: tuple[str, ...] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROBE_ISSUER:
            _fail("OS-supervisor admission probes are issuer-owned")
        parse_content_id(self.profile_id)
        if type(self.read_evidence) is not tuple or any(
            type(item) is not K7OSSupervisorReadEvidenceV1
            for item in self.read_evidence
        ):
            _fail("OS-supervisor probe read evidence is not exact")
        if len({item.role for item in self.read_evidence}) != len(self.read_evidence):
            _fail("OS-supervisor probe duplicated a read role")
        for value in (
            self.posix_present,
            self.linux_present,
            self.pidfd_open_present,
            self.pidfd_wait_present,
            self.delegated_parent_fd_supplied,
        ):
            if type(value) is not bool:
                _fail("OS-supervisor probe boolean was mistyped")
        for value, label in (
            (self.current_cgroup_path, "current cgroup path"),
            (self.cgroup2_mount_root, "cgroup2 mount root"),
            (self.cgroup2_mount_path, "cgroup2 mount path"),
        ):
            if value is not None and (type(value) is not str or not value.startswith("/")):
                _fail(f"{label} must be absolute or null")
        if (
            type(self.current_delegatable_controllers) is not tuple
            or self.current_delegatable_controllers
            != tuple(sorted(set(self.current_delegatable_controllers)))
            or type(self.current_cgroup_directory_fact)
            is not K7OSSupervisorPathFactV1
            or type(self.current_required_file_facts) is not tuple
            or len(self.current_required_file_facts) != len(REQUIRED_LEAF_FILES)
            or any(
                type(item) is not K7OSSupervisorPathFactV1
                for item in self.current_required_file_facts
            )
            or type(self.delegated_parent_fact)
            is not K7OSSupervisorPathFactV1
        ):
            _fail("OS-supervisor probe collections are not canonical")
        try:
            blockers = tuple(K7OSSupervisorBlockerV1(value) for value in self.blockers)
        except (TypeError, ValueError) as error:
            raise V075K7OSSupervisorAdmissionV1Error(
                "OS-supervisor probe blocker is unknown"
            ) from error
        if blockers != tuple(sorted(set(blockers), key=lambda item: item.value)):
            _fail("OS-supervisor blockers are duplicated or unordered")
        object.__setattr__(self, "blockers", blockers)
        if not blockers:
            _fail("read-only admission probe cannot be execution-ready")
        read_ids = tuple(item.evidence_id for item in self.read_evidence)
        fact_documents = tuple(
            item.to_document()
            for item in (
                self.current_cgroup_directory_fact,
                *self.current_required_file_facts,
                self.delegated_parent_fact,
            )
        )
        blocker_values = tuple(item.value for item in blockers)
        object.__setattr__(self, "_validated_read_ids", read_ids)
        object.__setattr__(self, "_validated_fact_documents", fact_documents)
        object.__setattr__(self, "_validated_blocker_values", blocker_values)
        object.__setattr__(
            self,
            "_probe_id",
            _hash(V075_K7_OS_SUPERVISOR_ADMISSION_PROBE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_os_supervisor_admission_probe.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "admission_profile_id": self.profile_id,
            "read_evidence": [item.to_document() for item in self.read_evidence],
            "posix_present": self.posix_present,
            "linux_present": self.linux_present,
            "pidfd_open_present": self.pidfd_open_present,
            "pidfd_wait_present": self.pidfd_wait_present,
            "current_cgroup_path": self.current_cgroup_path,
            "cgroup2_mount_root": self.cgroup2_mount_root,
            "cgroup2_mount_path": self.cgroup2_mount_path,
            "current_delegatable_controllers": list(
                self.current_delegatable_controllers
            ),
            "current_cgroup_directory_fact": (
                self.current_cgroup_directory_fact.to_document()
            ),
            "current_required_file_facts": [
                item.to_document() for item in self.current_required_file_facts
            ],
            "delegated_parent_fd_supplied": self.delegated_parent_fd_supplied,
            "delegated_parent_fact": self.delegated_parent_fact.to_document(),
            "blockers": [item.value for item in self.blockers],
            "child_launch_attempted": False,
            "cgroup_created": False,
            "cgroup_controller_write_attempted": False,
            "runtime_lease_validation_performed": False,
            "formal_locks": _locks(),
        }

    @property
    def probe_id(self) -> str:
        if (
            any(
                type(item) is not K7OSSupervisorReadEvidenceV1
                for item in self.read_evidence
            )
            or tuple(item.evidence_id for item in self.read_evidence)
            != self._validated_read_ids
            or any(
                type(item) is not K7OSSupervisorPathFactV1
                for item in (
                    self.current_cgroup_directory_fact,
                    *self.current_required_file_facts,
                    self.delegated_parent_fact,
                )
            )
            or tuple(
                item.to_document()
                for item in (
                    self.current_cgroup_directory_fact,
                    *self.current_required_file_facts,
                    self.delegated_parent_fact,
                )
            )
            != self._validated_fact_documents
            or any(
                type(item) is not K7OSSupervisorBlockerV1
                for item in self.blockers
            )
            or tuple(item.value for item in self.blockers)
            != self._validated_blocker_values
        ):
            _fail("OS-supervisor admission probe changed after issuance")
        current = _hash(
            V075_K7_OS_SUPERVISOR_ADMISSION_PROBE_V1_DOMAIN, self._payload()
        )
        if current != self._probe_id:
            _fail("OS-supervisor admission probe changed after issuance")
        return self._probe_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "admission_probe_id": self.probe_id}


@dataclass(frozen=True, slots=True)
class K7OSSupervisorAdmissionResultV1:
    _issuer: InitVar[object]
    profile: K7OSSupervisorAdmissionProfileV1 = field(repr=False, compare=False)
    probe: K7OSSupervisorAdmissionProbeV1 = field(repr=False, compare=False)
    status: K7OSSupervisorAdmissionStatusV1
    _validated_refs: tuple[object, object] = field(
        init=False, repr=False, compare=False
    )
    _validated_ids: tuple[str, str] = field(init=False, repr=False)
    _result_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.profile) is not K7OSSupervisorAdmissionProfileV1
            or type(self.probe) is not K7OSSupervisorAdmissionProbeV1
            or self.probe.profile_id != self.profile.profile_id
        ):
            _fail("OS-supervisor admission result crossed its authorities")
        try:
            status = K7OSSupervisorAdmissionStatusV1(self.status)
        except (TypeError, ValueError) as error:
            raise V075K7OSSupervisorAdmissionV1Error(
                "OS-supervisor admission status is unknown"
            ) from error
        object.__setattr__(self, "status", status)
        expected = K7OSSupervisorAdmissionStatusV1.NOT_AVAILABLE
        if status is not expected:
            _fail("OS-supervisor admission status disagrees with the probe")
        object.__setattr__(self, "_validated_refs", (self.profile, self.probe))
        object.__setattr__(
            self, "_validated_ids", (self.profile.profile_id, self.probe.probe_id)
        )
        object.__setattr__(
            self,
            "_result_id",
            _hash(V075_K7_OS_SUPERVISOR_ADMISSION_RESULT_V1_DOMAIN, self._payload()),
        )

    def _assert_current(self) -> None:
        if (
            (self.profile, self.probe) != self._validated_refs
            or self.profile is not self._validated_refs[0]
            or self.probe is not self._validated_refs[1]
            or (self.profile.profile_id, self.probe.probe_id) != self._validated_ids
        ):
            _fail("OS-supervisor admission authority changed after issuance")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_os_supervisor_admission_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "admission_profile_id": self.profile.profile_id,
            "admission_probe_id": self.probe.probe_id,
            "status": self.status.value,
            "blockers": [item.value for item in self.probe.blockers],
            "admission_scope": "PRELAUNCH_CAPABILITY_ONLY",
            "attempt_identity_bound": False,
            "attempt_terminal_issued": False,
            "noncertificate_closure_issued": False,
            "child_launch_attempted": False,
            "nine_shared_resource_paths_semantically_closed": False,
            "formal_locks": _locks(),
        }

    @property
    def result_id(self) -> str:
        self._assert_current()
        current = _hash(
            V075_K7_OS_SUPERVISOR_ADMISSION_RESULT_V1_DOMAIN, self._payload()
        )
        if current != self._result_id:
            _fail("OS-supervisor admission result changed after issuance")
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "admission_result_id": self.result_id}


def probe_v075_k7_os_supervisor_admission_v1(
    *, delegated_parent_fd: int | None = None
) -> K7OSSupervisorAdmissionResultV1:
    """Perform the bounded prelaunch probe; never launch or mutate cgroups."""

    if delegated_parent_fd is not None and (
        type(delegated_parent_fd) is not int or delegated_parent_fd < 0
    ):
        _fail("delegated parent descriptor must be a nonnegative exact integer")
    profile = official_v075_k7_os_supervisor_admission_profile_v1()
    blockers: set[K7OSSupervisorBlockerV1] = set()
    evidence: list[K7OSSupervisorReadEvidenceV1] = []
    posix_present = os.name == "posix"
    linux_present = sys.platform.startswith("linux")
    pidfd_open_present = callable(getattr(os, "pidfd_open", None))
    pidfd_wait_present = callable(getattr(os, "waitid", None)) and hasattr(
        os, "P_PIDFD"
    )
    if not posix_present:
        blockers.add(K7OSSupervisorBlockerV1.NOT_POSIX)
    if not linux_present:
        blockers.add(K7OSSupervisorBlockerV1.NOT_LINUX)
    if not pidfd_open_present:
        blockers.add(K7OSSupervisorBlockerV1.PIDFD_OPEN_UNAVAILABLE)
    if not pidfd_wait_present:
        blockers.add(K7OSSupervisorBlockerV1.PIDFD_WAIT_UNAVAILABLE)

    cgroup_path: str | None = None
    mount_root: str | None = None
    mount_path: str | None = None
    try:
        row, raw = _read_evidence(
            Path("/proc/self/cgroup"),
            K7OSSupervisorReadRoleV1.PROC_SELF_CGROUP,
        )
        evidence.append(row)
    except V075K7OSSupervisorAdmissionV1Error:
        blockers.add(K7OSSupervisorBlockerV1.PROC_SELF_CGROUP_UNREADABLE)
    else:
        try:
            cgroup_path = _self_cgroup_path(
                _decode(raw, K7OSSupervisorReadRoleV1.PROC_SELF_CGROUP)
            )
        except V075K7OSSupervisorAdmissionV1Error:
            blockers.add(K7OSSupervisorBlockerV1.PROC_SELF_CGROUP_INVALID)
    try:
        row, raw = _read_evidence(
            Path("/proc/self/mountinfo"),
            K7OSSupervisorReadRoleV1.PROC_SELF_MOUNTINFO,
        )
        evidence.append(row)
    except V075K7OSSupervisorAdmissionV1Error:
        blockers.add(K7OSSupervisorBlockerV1.PROC_SELF_MOUNTINFO_UNREADABLE)
    else:
        if cgroup_path is not None:
            try:
                mount_root, mount_path = _cgroup2_mount(
                    _decode(raw, K7OSSupervisorReadRoleV1.PROC_SELF_MOUNTINFO),
                    cgroup_path,
                )
            except V075K7OSSupervisorAdmissionV1Error:
                blockers.add(K7OSSupervisorBlockerV1.CGROUP2_MOUNT_UNRESOLVED)
        else:
            blockers.add(K7OSSupervisorBlockerV1.CGROUP2_MOUNT_UNRESOLVED)

    controllers: tuple[str, ...] = ()
    current_directory: Path | None = None
    if cgroup_path is not None and mount_root is not None and mount_path is not None:
        current_directory = _current_cgroup_directory(
            membership=cgroup_path,
            mount_root=mount_root,
            mountpoint=mount_path,
        )
        try:
            row, raw = _read_evidence(
                current_directory / "cgroup.controllers",
                K7OSSupervisorReadRoleV1.CURRENT_CGROUP_CONTROLLERS,
            )
            evidence.append(row)
            controllers = tuple(
                sorted(
                    set(
                        _decode(
                            raw,
                            K7OSSupervisorReadRoleV1.CURRENT_CGROUP_CONTROLLERS,
                        ).split()
                    )
                )
            )
        except V075K7OSSupervisorAdmissionV1Error:
            blockers.add(
                K7OSSupervisorBlockerV1.CURRENT_CGROUP_CONTROLLERS_UNREADABLE
            )
        subtree = current_directory / "cgroup.subtree_control"
        if subtree.exists():
            try:
                row, _raw = _read_evidence(
                    subtree,
                    K7OSSupervisorReadRoleV1.CURRENT_CGROUP_SUBTREE_CONTROL,
                )
                evidence.append(row)
            except V075K7OSSupervisorAdmissionV1Error:
                pass
        directory_fact = _path_fact(
            current_directory, "CURRENT_CGROUP_DIRECTORY"
        )
        required_facts = tuple(
            _path_fact(current_directory / name, f"CURRENT_REQUIRED_FILE:{name}")
            for name in REQUIRED_LEAF_FILES
        )
        if not set(REQUIRED_CONTROLLERS) <= set(controllers):
            blockers.add(K7OSSupervisorBlockerV1.REQUIRED_CONTROLLER_MISSING)
        if not directory_fact.stat_observed:
            blockers.add(K7OSSupervisorBlockerV1.CURRENT_CGROUP_FACT_UNOBSERVED)
        if any(not item.stat_observed for item in required_facts):
            blockers.add(
                K7OSSupervisorBlockerV1.CURRENT_CGROUP_REQUIRED_FILE_UNOBSERVED
            )
        if any(item.stat_observed and not item.exists for item in required_facts):
            blockers.add(
                K7OSSupervisorBlockerV1.CURRENT_CGROUP_REQUIRED_FILE_MISSING
            )
        if not directory_fact.writable:
            blockers.add(K7OSSupervisorBlockerV1.CURRENT_CGROUP_NOT_WRITABLE)
    else:
        blockers.add(K7OSSupervisorBlockerV1.CURRENT_CGROUP_UNRESOLVED)
        directory_fact = _path_fact(
            Path("/unresolved/acfqp-current-cgroup"),
            "CURRENT_CGROUP_DIRECTORY",
        )
        required_facts = tuple(
            _path_fact(
                Path("/unresolved/acfqp-current-cgroup") / name,
                f"CURRENT_REQUIRED_FILE:{name}",
            )
            for name in REQUIRED_LEAF_FILES
        )

    supplied = delegated_parent_fd is not None
    delegated_fact = _descriptor_fact(delegated_parent_fd)
    if delegated_parent_fd is None:
        blockers.add(
            K7OSSupervisorBlockerV1.DELEGATED_CGROUP_PARENT_FD_NOT_SUPPLIED
        )
    else:
        if not delegated_fact.exists or not delegated_fact.is_directory:
            blockers.add(
                K7OSSupervisorBlockerV1.DELEGATED_CGROUP_PARENT_FD_INVALID
            )
        blockers.add(
            K7OSSupervisorBlockerV1.DELEGATED_PARENT_RUNTIME_LEASE_VALIDATION_NOT_IMPLEMENTED
        )

    probe = K7OSSupervisorAdmissionProbeV1(
        _PROBE_ISSUER,
        profile.profile_id,
        tuple(evidence),
        posix_present,
        linux_present,
        pidfd_open_present,
        pidfd_wait_present,
        cgroup_path,
        mount_root,
        mount_path,
        controllers,
        directory_fact,
        required_facts,
        supplied,
        delegated_fact,
        tuple(sorted(blockers, key=lambda item: item.value)),
    )
    status = K7OSSupervisorAdmissionStatusV1.NOT_AVAILABLE
    return K7OSSupervisorAdmissionResultV1(
        _RESULT_ISSUER, profile, probe, status
    )


def verify_v075_k7_os_supervisor_admission_v1(
    result: K7OSSupervisorAdmissionResultV1,
) -> K7OSSupervisorAdmissionResultV1:
    if type(result) is not K7OSSupervisorAdmissionResultV1:
        _fail("OS-supervisor admission verifier requires the exact result")
    result._assert_current()
    return result


__all__ = [
    "ACTUAL_PROJECTION_PROOF_AUTHORIZED",
    "CHILD_LAUNCH_ALLOWED",
    "COMPARISON_VECTOR_AUTHORIZED",
    "COUNTER_RECORD_AUTHORIZED",
    "DELEGATED_CGROUP_LEASE_VERIFIED",
    "K7OSSupervisorAdmissionProfileV1",
    "K7OSSupervisorAdmissionProbeV1",
    "K7OSSupervisorAdmissionResultV1",
    "K7OSSupervisorAdmissionStatusV1",
    "K7OSSupervisorBlockerV1",
    "K7OSSupervisorPathFactV1",
    "K7OSSupervisorReadEvidenceV1",
    "K7OSSupervisorReadRoleV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OS_SOURCE_PROVENANCE_VERIFIED",
    "PIDFD_LIFECYCLE_VERIFIED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "V075K7OSSupervisorAdmissionV1Error",
    "WORK_VECTOR_AUTHORIZED",
    "official_v075_k7_os_supervisor_admission_profile_v1",
    "probe_v075_k7_os_supervisor_admission_v1",
    "verify_v075_k7_os_supervisor_admission_v1",
]
