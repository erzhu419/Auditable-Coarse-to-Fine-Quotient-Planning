"""Construction-only E3-bound output continuation for ordinals 53..62.

The module intentionally emits witness schemas.  No durable byte produced
here is a formal CounterRecord, WorkVector, ComparisonVector, projection proof
or terminal certificate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_h1_domain_registry_extension_v11 as domains_v11
from acfqp import construction_k7_h1_exclusive_native_resource_broker_v1 as e3_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E4"
PROFILE_KEY = "construction_k7_h1_e3_bound_output_ordinal_continuation_v1"

ROLE_ORDER: tuple[str, ...] = (
    "BUSINESS_RESULT",
    "OPERATIONAL_TRACE",
    "TERMINAL_ARTIFACT",
    "COUNTER_RECORD_SET",
    "WORK_VECTOR",
    "COMPARISON_VECTOR",
    "ACTUAL_PROJECTION_PROOF",
    "OUTPUT_MANIFEST",
)
ROLE_ORDINALS = MappingProxyType(
    {role: 53 + index for index, role in enumerate(ROLE_ORDER)}
)
ROLE_FILE_NAMES = MappingProxyType(
    {
        "BUSINESS_RESULT": "53-business-result.json",
        "OPERATIONAL_TRACE": "54-operational-trace.json",
        "TERMINAL_ARTIFACT": "55-terminal-artifact.json",
        "COUNTER_RECORD_SET": "56-counter-record-set.json",
        "WORK_VECTOR": "57-work-vector.json",
        "COMPARISON_VECTOR": "58-comparison-vector.json",
        "ACTUAL_PROJECTION_PROOF": "59-actual-projection-proof.json",
        "OUTPUT_MANIFEST": "60-output-manifest.json",
    }
)
ROLE_SCHEMAS = MappingProxyType(
    {
        role: (
            "acfqp.k7_h1_e4."
            + role.lower()
            + ".construction_witness.v1"
        )
        for role in ROLE_ORDER
    }
)

MAX_FIXED_POINT_ITERATIONS = 32
MAX_ROLE_BYTES = 256 * 1024
MAX_TOTAL_OUTPUT_BYTES = 2 * 1024 * 1024
SERIALIZER_BUFFER_EXTENT_CAP_BYTES = 2 * MAX_TOTAL_OUTPUT_BYTES
_ID = re.compile(r"^[0-9a-f]{64}$")
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_RESULT_ISSUER = object()
_PROFILE_ISSUER = object()
_CONTEXT_ISSUER = object()
_FIXED_POINT_ISSUER = object()

E3_BOUND_OUTPUT_CONTINUATION_PRESENT = True
CONSTRUCTION_OUTPUT_ORDINAL_53_TO_62_WITNESS_PRESENT = True
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
ROUTE_WIDE_PEAK_AUTHORITY_PRESENT = False
PEAK_SCOPE_STATUS = "PEAK_SCOPE_UNRESOLVED"
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"


class ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error(ValueError):
    """An E4 identity, fixed point, writer or ordinal invariant crossed."""


class H1E4FaultInjectionV1(str, Enum):
    """Construction-only attack points; every non-NONE value must fail."""

    NONE = "NONE"
    EXTRA_FILE = "EXTRA_FILE"
    SYMLINK = "SYMLINK"
    HARDLINK = "HARDLINK"
    REPLACE_ROLE = "REPLACE_ROLE"
    REORDER_EVENTS = "REORDER_EVENTS"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    CRASH_AFTER_ORDINAL_55 = "CRASH_AFTER_ORDINAL_55"
    ERROR_BEFORE_FINALIZE_61 = "ERROR_BEFORE_FINALIZE_61"
    ERROR_AFTER_FINALIZE_61 = "ERROR_AFTER_FINALIZE_61"
    DIRECTORY_RENAME = "DIRECTORY_RENAME"
    DIRECTORY_UNLINK = "DIRECTORY_UNLINK"
    DIRECTORY_CHMOD = "DIRECTORY_CHMOD"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error(
            f"{label} is not one content ID"
        ) from error


def _domain_id(domain: str, payload: Any) -> str:
    return domains_v11.extension_content_id_v11(domain, payload)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be an exact nonnegative integer")
    return value


def _canonical_mapping(value: Any, label: str) -> tuple[dict[str, Any], bytes]:
    if type(value) is not dict:
        _fail(f"{label} must be one exact dict")
    try:
        raw = canonical_json_bytes(value)
        replay = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(replay) is not dict or canonical_json_bytes(replay) != raw:
        _fail(f"{label} canonical replay changed")
    return dict(replay), raw


def _with_id(payload: Mapping[str, Any], *, domain: str, id_field: str) -> dict[str, Any]:
    document = dict(payload)
    document[id_field] = _domain_id(domain, payload)
    return document


def _verify_content_object(
    row: Any,
    *,
    domain: str,
    id_field: str,
    label: str,
) -> dict[str, Any]:
    if type(row) is not dict:
        _fail(f"{label} is not one exact object")
    payload = dict(row)
    supplied = _cid(payload.pop(id_field, None), label)
    if _domain_id(domain, payload) != supplied:
        _fail(f"{label} content ID changed")
    return payload


def _locked_claims() -> dict[str, Any]:
    return {
        "production_output_leaf_authority_present": False,
        "route_wide_peak_authority_present": False,
        "peak_scope_status": PEAK_SCOPE_STATUS,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_actual_projection_proof_issued": False,
        "current_access_authority_present": False,
        "formal_v7_authority_present": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }


@dataclass(frozen=True, slots=True)
class H1E3BoundOutputContinuationProfileV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    profile_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("E4 profile is caller-minted")
        document = loads_canonical_json(self.payload_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.payload_bytes:
            _fail("E4 profile bytes are not canonical")
        object.__setattr__(
            self,
            "profile_id",
            _domain_id(
                domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_CONTINUATION_PROFILE_V1_DOMAIN,
                document,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.payload_bytes)
        return {**document, "h1_e3_bound_output_continuation_profile_id": self.profile_id}


def _profile_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_e3_bound_output_continuation_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "accepted_upstream_type": "H1ExclusiveBrokerCompletionV1",
        "accepted_upstream_disposition": "BROKER_EXCLUSIVE_PRESENT",
        "accepted_upstream_profile_key": e3_v1.PROFILE_KEY,
        "prebound_context_required": True,
        "typed_null_prebinding_accepted": False,
        "role_ordinal_file_map": [
            {
                "role": role,
                "normal_ordinal": ROLE_ORDINALS[role],
                "file_name": ROLE_FILE_NAMES[role],
            }
            for role in ROLE_ORDER
        ],
        "fixed_point_iteration_cap": MAX_FIXED_POINT_ITERATIONS,
        "role_byte_cap": MAX_ROLE_BYTES,
        "total_output_byte_cap": MAX_TOTAL_OUTPUT_BYTES,
        "serializer_buffer_extent_cap_bytes": SERIALIZER_BUFFER_EXTENT_CAP_BYTES,
        "serializer_buffer_extent_is_not_peak_working_memory": True,
        "maximum_simultaneous_render_sets": 2,
        "durable_role_count": 8,
        "ninth_durable_wrapper_forbidden": True,
        "construction_witness_schemas_only": True,
        "joint_output_read_fixed_point_required": True,
        "two_terminal_identical_replays_required": True,
        "exactly_once_inode_pinned_readback_required": True,
        "pinned_parent_directory_fd_required": True,
        "parent_entry_fsync_after_mkdir_required": True,
        "parent_name_to_child_inode_replay_before_ordinals_61_and_62": True,
        "output_directory_initially_empty_and_inode_pinned": True,
        "unified_owned_fd_registry_required": True,
        "fork_covers_precontext_and_runtime_role_fds": True,
        "persistent_close_failure_quarantined_and_retryable": True,
        "authoritative_full_completion_reconstruction_required": True,
        **_locked_claims(),
    }


_PROFILE = H1E3BoundOutputContinuationProfileV1(
    _PROFILE_ISSUER, canonical_json_bytes(_profile_payload())
)


def official_h1_e3_bound_output_continuation_profile_v1(
) -> H1E3BoundOutputContinuationProfileV1:
    return _PROFILE


@dataclass(frozen=True, slots=True, eq=False)
class H1E3BoundOutputContinuationContextV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _owner_key: str = field(repr=False)
    _parent_fd: int = field(repr=False)
    _directory_fd: int = field(repr=False)
    _parent_path: Path = field(repr=False)
    _directory_path: Path = field(repr=False)
    _directory_basename: str = field(repr=False)
    context_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CONTEXT_ISSUER:
            _fail("E4 context is caller-minted")
        document = loads_canonical_json(self.payload_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.payload_bytes:
            _fail("E4 context bytes are not canonical")
        object.__setattr__(
            self,
            "context_id",
            _domain_id(
                domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_CONTINUATION_CONTEXT_V1_DOMAIN,
                document,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.payload_bytes)
        return {**document, "h1_e3_bound_output_continuation_context_id": self.context_id}

    def __copy__(self) -> NoReturn:
        _fail("E4 context cannot be copied")

    def __deepcopy__(self, _memo: Any) -> NoReturn:
        _fail("E4 context cannot be deep-copied")


@dataclass(frozen=True, slots=True)
class H1E3BoundOutputJointFixedPointV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    role_bytes: tuple[tuple[str, bytes], ...] = field(repr=False)
    fixed_point_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _FIXED_POINT_ISSUER:
            _fail("E4 joint fixed point is caller-minted")
        document = loads_canonical_json(self.payload_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.payload_bytes:
            _fail("E4 fixed-point bytes are not canonical")
        if tuple(role for role, _raw in self.role_bytes) != ROLE_ORDER:
            _fail("E4 fixed point changed the eight-role order")
        object.__setattr__(
            self,
            "fixed_point_id",
            _domain_id(
                domains_v11.CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN,
                document,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.payload_bytes)
        return {**document, "h1_joint_output_read_fixed_point_id": self.fixed_point_id}


@dataclass(frozen=True, slots=True)
class H1E3BoundOutputCompletionV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    completion_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("E4 completion is caller-minted")
        document = loads_canonical_json(self.payload_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.payload_bytes:
            _fail("E4 completion bytes are not canonical")
        payload = dict(document)
        supplied = _cid(payload.pop("h1_e3_bound_output_completion_id", None), "E4 completion")
        expected = _domain_id(
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_COMPLETION_V1_DOMAIN,
            payload,
        )
        if supplied != expected:
            _fail("E4 completion content ID changed")
        _verify_completion_document(document)
        object.__setattr__(self, "completion_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return dict(loads_canonical_json(self.payload_bytes))


@dataclass(frozen=True, slots=True)
class H1E3BoundOutputPartialNoncertificateV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    partial_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("E4 partial noncertificate is caller-minted")
        document = loads_canonical_json(self.payload_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.payload_bytes:
            _fail("E4 partial bytes are not canonical")
        object.__setattr__(
            self,
            "partial_id",
            _domain_id(
                domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_PARTIAL_NONCERTIFICATE_V1_DOMAIN,
                document,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.payload_bytes)
        return {**document, "h1_e3_bound_output_partial_noncertificate_id": self.partial_id}


_OWNERSHIP_LOCK = threading.RLock()
_LIVE_CONTEXTS: dict[int, tuple[H1E3BoundOutputContinuationContextV1, bytes]] = {}
_QUARANTINED_CONTEXTS: dict[
    int, tuple[H1E3BoundOutputContinuationContextV1, bytes]
] = {}
_CONSUMED_CONTEXTS: dict[int, tuple[H1E3BoundOutputContinuationContextV1, bytes]] = {}
_CONSUMED_CONTEXT_IDS: set[str] = set()
_OWNED_FDS: dict[str, dict[int, dict[str, Any]]] = {}


def _fd_record(descriptor: int, label: str) -> dict[str, Any]:
    metadata = os.fstat(descriptor)
    return {
        "label": label,
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "file_type": stat.S_IFMT(metadata.st_mode),
    }


def _register_owned_fd(owner_key: str, descriptor: int, label: str) -> None:
    """Register an already-open FD while the ownership lock is held."""

    if _ID.fullmatch(owner_key) is None or type(descriptor) is not int or descriptor < 0:
        _fail("E4 owned FD registration is malformed")
    if any(descriptor in rows for rows in _OWNED_FDS.values()):
        _fail("E4 owned FD number is already registered")
    _OWNED_FDS.setdefault(owner_key, {})[descriptor] = _fd_record(descriptor, label)


def _open_owned_fd(
    owner_key: str,
    label: str,
    path: str | os.PathLike[str],
    flags: int,
    mode: int = 0o777,
    *,
    dir_fd: int | None = None,
) -> int:
    """Open and publish one owned FD atomically against fork preparation."""

    with _OWNERSHIP_LOCK:
        descriptor = os.open(path, flags, mode, dir_fd=dir_fd)
        try:
            _register_owned_fd(owner_key, descriptor, label)
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor


def _owned_fd_rows(owner_key: str) -> dict[int, dict[str, Any]]:
    with _OWNERSHIP_LOCK:
        return {
            descriptor: dict(row)
            for descriptor, row in _OWNED_FDS.get(owner_key, {}).items()
        }


def _same_registered_fd(descriptor: int, row: Mapping[str, Any]) -> bool:
    try:
        metadata = os.fstat(descriptor)
    except OSError as error:
        if error.errno == errno.EBADF:
            return False
        raise
    return (
        metadata.st_dev == row.get("device")
        and metadata.st_ino == row.get("inode")
        and stat.S_IFMT(metadata.st_mode) == row.get("file_type")
    )


def _close_owned_fd(owner_key: str, descriptor: int) -> bool:
    """Drop registry ownership only after the original kernel FD is gone."""

    with _OWNERSHIP_LOCK:
        rows = _OWNED_FDS.get(owner_key)
        row = None if rows is None else rows.get(descriptor)
        if row is None:
            return True
        try:
            os.close(descriptor)
            closed = True
        except OSError as error:
            try:
                still_same = _same_registered_fd(descriptor, row)
            except BaseException:
                still_same = True
            closed = error.errno == errno.EBADF or not still_same
        if closed:
            rows.pop(descriptor, None)
            if not rows:
                _OWNED_FDS.pop(owner_key, None)
        return closed


def _close_all_owned_fds(owner_key: str) -> bool:
    for descriptor in tuple(sorted(_owned_fd_rows(owner_key))):
        _close_owned_fd(owner_key, descriptor)
    return not _owned_fd_rows(owner_key)


def _before_fork() -> None:
    _OWNERSHIP_LOCK.acquire()


def _after_fork_in_parent() -> None:
    _OWNERSHIP_LOCK.release()


def _after_fork_in_child() -> None:
    """Close or quarantine every child copy of every process-local lease FD."""

    global _OWNERSHIP_LOCK
    live_contexts = tuple(_LIVE_CONTEXTS.values()) + tuple(
        _QUARANTINED_CONTEXTS.values()
    )
    for owner_key in tuple(_OWNED_FDS):
        _close_all_owned_fds(owner_key)
    survivors = set(_OWNED_FDS)
    _LIVE_CONTEXTS.clear()
    _QUARANTINED_CONTEXTS.clear()
    for context, raw in live_contexts:
        if context._owner_key in survivors:
            _QUARANTINED_CONTEXTS[id(context)] = (context, raw)
    _CONSUMED_CONTEXTS.clear()
    _CONSUMED_CONTEXT_IDS.clear()
    _OWNERSHIP_LOCK = threading.RLock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=_before_fork,
        after_in_parent=_after_fork_in_parent,
        after_in_child=_after_fork_in_child,
    )


def _directory_identity(descriptor: int) -> dict[str, int]:
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        _fail("E4 pinned output descriptor is not a directory")
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": stat.S_IMODE(metadata.st_mode),
    }


def _directory_names(descriptor: int) -> tuple[str, ...]:
    try:
        names = os.listdir(descriptor)
    except (OSError, TypeError) as error:
        raise ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error(
            "E4 could not inventory the pinned output directory"
        ) from error
    if any(type(name) is not str or name in {".", ".."} for name in names):
        _fail("E4 output directory returned a malformed name")
    return tuple(sorted(names))


def _wrap_nonformal_lifecycle(
    *,
    kind: str,
    caller_payload: Mapping[str, Any],
    caller_binding_id: str,
    logical_occurrence_id: str,
    route_attempt_id: str,
) -> tuple[dict[str, Any], str]:
    source, source_raw = _canonical_mapping(caller_payload, f"caller {kind}")
    if any(
        source.get(name) is True
        for name in (
            "formal_authority_present",
            "official_execution_allowed",
            "formal_v7_authority_present",
        )
    ):
        _fail(f"caller {kind} cannot claim formal authority inside E4")
    snapshot = kind == "lifecycle_snapshot"
    payload = {
        "schema": (
            "acfqp.k7_h1_e3_bound_output_lifecycle_snapshot.nonformal.v1"
            if snapshot
            else "acfqp.k7_h1_e3_bound_output_lifecycle_program.nonformal.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "caller_binding_id": caller_binding_id,
        "logical_occurrence_id": logical_occurrence_id,
        "route_attempt_id": route_attempt_id,
        "caller_payload": source,
        "caller_payload_sha256": _sha(source_raw),
        "formal_authority_present": False,
        "construction_witness_only": True,
    }
    domain = (
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_LIFECYCLE_SNAPSHOT_V1_DOMAIN
        if snapshot
        else domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_LIFECYCLE_PROGRAM_V1_DOMAIN
    )
    return payload, _domain_id(domain, payload)


def prepare_h1_e3_bound_output_continuation_context_v1(
    *,
    output_parent_directory: str | os.PathLike[str],
    caller_binding_id: str,
    lifecycle_snapshot: Mapping[str, Any],
    lifecycle_program: Mapping[str, Any],
    logical_occurrence_id: str,
    route_attempt_id: str,
    read_bytes_base: int = 0,
) -> H1E3BoundOutputContinuationContextV1:
    """Create and retain one fresh directory-pinned pre-E3 context."""

    caller_binding_id = _cid(caller_binding_id, "caller binding")
    logical_occurrence_id = _cid(logical_occurrence_id, "logical occurrence")
    route_attempt_id = _cid(route_attempt_id, "route attempt")
    _nonnegative(read_bytes_base, "read-bytes base")
    snapshot, snapshot_id = _wrap_nonformal_lifecycle(
        kind="lifecycle_snapshot",
        caller_payload=lifecycle_snapshot,
        caller_binding_id=caller_binding_id,
        logical_occurrence_id=logical_occurrence_id,
        route_attempt_id=route_attempt_id,
    )
    program, program_id = _wrap_nonformal_lifecycle(
        kind="lifecycle_program",
        caller_payload=lifecycle_program,
        caller_binding_id=caller_binding_id,
        logical_occurrence_id=logical_occurrence_id,
        route_attempt_id=route_attempt_id,
    )
    parent = Path(output_parent_directory).resolve(strict=True)
    nonce = os.urandom(32).hex()
    if _ID.fullmatch(nonce) is None:  # pragma: no cover - OS invariant
        _fail("E4 cryptographic nonce is malformed")
    owner_key = nonce
    parent_fd = _open_owned_fd(
        owner_key,
        "OUTPUT_PARENT_DIRECTORY",
        parent,
        os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW,
    )
    directory_fd = -1
    child: Path | None = None
    retained = False
    try:
        if not stat.S_ISDIR(os.fstat(parent_fd).st_mode):
            _fail("E4 output parent is not one pinned directory")
        parent_identity = _directory_identity(parent_fd)
        basename = f"acfqp-e4-output-{nonce}"
        os.mkdir(basename, mode=0o700, dir_fd=parent_fd)
        child = parent / basename
        directory_fd = _open_owned_fd(
            owner_key,
            "OUTPUT_DIRECTORY",
            basename,
            os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        identity = _directory_identity(directory_fd)
        if identity["mode"] != 0o700 or _directory_names(directory_fd):
            _fail("E4 output directory was not freshly created empty mode 0700")
        os.fsync(parent_fd)
        e3_profile_id = e3_v1.official_h1_exclusive_broker_profile_v1().profile_id
        e3_source_id = e3_v1.official_h1_exclusive_broker_source_manifest_v1().manifest_id
        payload = {
            "schema": "acfqp.k7_h1_e3_bound_output_continuation_context.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_e3_bound_output_continuation_profile_id": _PROFILE.profile_id,
            "context_nonce": nonce,
            "preparer_pid": os.getpid(),
            "preparer_thread_id": threading.get_ident(),
            "process_local_writer_lease": True,
            "atfork_child_copy_closed_and_registry_cleared": True,
            "unified_owned_fd_registry": True,
            "persistent_close_failure_quarantine": True,
            "caller_binding_id": caller_binding_id,
            "logical_occurrence_id": logical_occurrence_id,
            "route_attempt_id": route_attempt_id,
            "nonformal_lifecycle_snapshot": snapshot,
            "nonformal_lifecycle_snapshot_id": snapshot_id,
            "nonformal_lifecycle_program": program,
            "nonformal_lifecycle_program_id": program_id,
            "h1_exclusive_broker_profile_id": e3_profile_id,
            "h1_exclusive_broker_source_manifest_id": e3_source_id,
            "output_directory": {
                **identity,
                "basename": basename,
                "parent_device": parent_identity["device"],
                "parent_inode": parent_identity["inode"],
                "parent_mode": parent_identity["mode"],
                "pinned_parent_directory_fd_retained": True,
                "parent_entry_fsync_complete": True,
                "fresh_empty_at_preparation": True,
                "pinned_directory_fd_retained": True,
            },
            "role_ordinal_file_map": [
                {
                    "role": role,
                    "normal_ordinal": ROLE_ORDINALS[role],
                    "file_name": ROLE_FILE_NAMES[role],
                }
                for role in ROLE_ORDER
            ],
            "read_bytes_base": read_bytes_base,
            "fixed_point_iteration_cap": MAX_FIXED_POINT_ITERATIONS,
            "role_byte_cap": MAX_ROLE_BYTES,
            "total_output_byte_cap": MAX_TOTAL_OUTPUT_BYTES,
            "serializer_buffer_extent_cap_bytes": SERIALIZER_BUFFER_EXTENT_CAP_BYTES,
            "prepared_before_e3_echo_required": True,
            "typed_null_prebinding_accepted": False,
            "construction_witness_only": True,
            **_locked_claims(),
        }
        context = H1E3BoundOutputContinuationContextV1(
            _CONTEXT_ISSUER,
            canonical_json_bytes(payload),
            owner_key,
            parent_fd,
            directory_fd,
            parent,
            child,
            basename,
        )
        with _OWNERSHIP_LOCK:
            _LIVE_CONTEXTS[id(context)] = (context, context.payload_bytes)
        retained = True
        return context
    except BaseException:
        _close_all_owned_fds(owner_key)
        if child is not None:
            try:
                child.rmdir()
            except OSError:
                pass
        raise
    finally:
        if not retained:
            _close_all_owned_fds(owner_key)


def _verify_bound_output_directory_entry(
    context: H1E3BoundOutputContinuationContextV1,
    document: Mapping[str, Any],
    *,
    require_empty: bool,
) -> None:
    recorded = document.get("output_directory")
    if type(recorded) is not dict:
        _fail("E4 output-directory binding is absent")
    owned = _owned_fd_rows(context._owner_key)
    if (
        owned.get(context._parent_fd, {}).get("label") != "OUTPUT_PARENT_DIRECTORY"
        or owned.get(context._directory_fd, {}).get("label") != "OUTPUT_DIRECTORY"
    ):
        _fail("E4 parent/directory FD ownership crossed")
    try:
        parent_identity = _directory_identity(context._parent_fd)
        descriptor_identity = _directory_identity(context._directory_fd)
        parent_path_stat = os.stat(context._parent_path, follow_symlinks=False)
        child_path_stat = os.stat(context._directory_path, follow_symlinks=False)
        parent_entry_stat = os.stat(
            context._directory_basename,
            dir_fd=context._parent_fd,
            follow_symlinks=False,
        )
    except OSError as error:
        raise ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error(
            "E4 pinned output parent/child path is unavailable"
        ) from error
    recorded_parent = {
        "device": recorded.get("parent_device"),
        "inode": recorded.get("parent_inode"),
        "mode": recorded.get("parent_mode"),
    }
    recorded_child = {
        "device": recorded.get("device"),
        "inode": recorded.get("inode"),
        "mode": recorded.get("mode"),
    }
    parent_path_identity = {
        "device": parent_path_stat.st_dev,
        "inode": parent_path_stat.st_ino,
        "mode": stat.S_IMODE(parent_path_stat.st_mode),
    }
    child_path_identity = {
        "device": child_path_stat.st_dev,
        "inode": child_path_stat.st_ino,
        "mode": stat.S_IMODE(child_path_stat.st_mode),
    }
    parent_entry_identity = {
        "device": parent_entry_stat.st_dev,
        "inode": parent_entry_stat.st_ino,
        "mode": stat.S_IMODE(parent_entry_stat.st_mode),
    }
    if (
        context._owner_key != document.get("context_nonce")
        or context._directory_basename != recorded.get("basename")
        or context._directory_path.name != context._directory_basename
        or context._directory_path.parent != context._parent_path
        or recorded.get("pinned_parent_directory_fd_retained") is not True
        or recorded.get("parent_entry_fsync_complete") is not True
        or recorded.get("pinned_directory_fd_retained") is not True
        or parent_identity != recorded_parent
        or parent_path_identity != parent_identity
        or descriptor_identity != recorded_child
        or child_path_identity != descriptor_identity
        or parent_entry_identity != descriptor_identity
        or not stat.S_ISDIR(parent_path_stat.st_mode)
        or not stat.S_ISDIR(child_path_stat.st_mode)
        or not stat.S_ISDIR(parent_entry_stat.st_mode)
    ):
        _fail("E4 output directory crossed its pinned parent/name/device/inode/path")
    if require_empty and _directory_names(context._directory_fd):
        _fail("E4 output directory is no longer the prebound empty directory")


def _verify_live_context(
    context: H1E3BoundOutputContinuationContextV1,
    *,
    require_empty: bool,
) -> dict[str, Any]:
    if type(context) is not H1E3BoundOutputContinuationContextV1:
        _fail("E4 requires one issuer-owned retained context")
    with _OWNERSHIP_LOCK:
        retained = _LIVE_CONTEXTS.get(id(context))
        if (
            retained is None
            or retained[0] is not context
            or retained[1] != context.payload_bytes
            or context.context_id in _CONSUMED_CONTEXT_IDS
        ):
            _fail("E4 context is not the exact live retained object")
    document = context.to_document()
    expected_id = _domain_id(
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_CONTINUATION_CONTEXT_V1_DOMAIN,
        {key: value for key, value in document.items() if key != "h1_e3_bound_output_continuation_context_id"},
    )
    if expected_id != context.context_id:
        _fail("E4 retained context identity changed")
    if (
        document.get("schema")
        != "acfqp.k7_h1_e3_bound_output_continuation_context.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("h1_e3_bound_output_continuation_profile_id")
        != _PROFILE.profile_id
        or document.get("role_ordinal_file_map")
        != [
            {
                "role": role,
                "normal_ordinal": ROLE_ORDINALS[role],
                "file_name": ROLE_FILE_NAMES[role],
            }
            for role in ROLE_ORDER
        ]
        or document.get("fixed_point_iteration_cap") != MAX_FIXED_POINT_ITERATIONS
        or document.get("role_byte_cap") != MAX_ROLE_BYTES
        or document.get("total_output_byte_cap") != MAX_TOTAL_OUTPUT_BYTES
        or document.get("serializer_buffer_extent_cap_bytes")
        != SERIALIZER_BUFFER_EXTENT_CAP_BYTES
        or document.get("prepared_before_e3_echo_required") is not True
        or document.get("typed_null_prebinding_accepted") is not False
        or document.get("construction_witness_only") is not True
        or document.get("preparer_pid") != os.getpid()
        or document.get("preparer_thread_id") != threading.get_ident()
        or document.get("process_local_writer_lease") is not True
        or document.get("atfork_child_copy_closed_and_registry_cleared") is not True
        or document.get("unified_owned_fd_registry") is not True
        or document.get("persistent_close_failure_quarantine") is not True
        or any(document.get(key) != value for key, value in _locked_claims().items())
    ):
        _fail("E4 retained context contract fields changed")
    for label, key, domain in (
        (
            "nonformal lifecycle snapshot",
            "nonformal_lifecycle_snapshot",
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_LIFECYCLE_SNAPSHOT_V1_DOMAIN,
        ),
        (
            "nonformal lifecycle program",
            "nonformal_lifecycle_program",
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_LIFECYCLE_PROGRAM_V1_DOMAIN,
        ),
    ):
        nested = document.get(key)
        if type(nested) is not dict:
            _fail(f"E4 {label} is absent")
        expected_nested_id = _domain_id(domain, nested)
        if document.get(key + "_id") != expected_nested_id:
            _fail(f"E4 {label} identity changed")
        if (
            nested.get("formal_authority_present") is not False
            or nested.get("construction_witness_only") is not True
            or nested.get("caller_binding_id") != document.get("caller_binding_id")
            or nested.get("logical_occurrence_id") != document.get("logical_occurrence_id")
            or nested.get("route_attempt_id") != document.get("route_attempt_id")
        ):
            _fail(f"E4 {label} binding changed")
    _verify_bound_output_directory_entry(
        context, document, require_empty=require_empty
    )
    return document


def _authorize_exact_e3_completion(
    context: H1E3BoundOutputContinuationContextV1,
    e3_completion: e3_v1.H1ExclusiveBrokerCompletionV1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    context_document = _verify_live_context(context, require_empty=True)
    completion = _verify_exact_e3_completion_against_context(
        context_document=context_document,
        context_id=context.context_id,
        e3_completion=e3_completion,
    )
    return context_document, completion


def _verify_exact_e3_completion_against_context(
    *,
    context_document: Mapping[str, Any],
    context_id: str,
    e3_completion: e3_v1.H1ExclusiveBrokerCompletionV1,
) -> dict[str, Any]:
    if type(e3_completion) is not e3_v1.H1ExclusiveBrokerCompletionV1:
        _fail("E4 accepts only exact issuer-owned E3 completion success")
    try:
        completion = e3_completion.to_document()
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error(
            "E4 exact E3 completion replay failed"
        ) from error
    barrier = completion.get("native_cleanup_barrier")
    genesis = completion.get("broker_session_genesis")
    session_nonce = completion.get("session_nonce")
    if (
        completion.get("schema") != "acfqp.k7_h1_exclusive_broker_completion.v1"
        or completion.get("profile_key") != e3_v1.PROFILE_KEY
        or completion.get("proposed_contract_version") != e3_v1.PROPOSED_CONTRACT_VERSION
        or completion.get("authority_disposition") != "BROKER_EXCLUSIVE_PRESENT"
        or completion.get("broker_exclusive_present") is not True
        or completion.get("h1_exclusive_broker_profile_id")
        != context_document["h1_exclusive_broker_profile_id"]
        or completion.get("h1_exclusive_broker_source_manifest_id")
        != context_document["h1_exclusive_broker_source_manifest_id"]
        or completion.get("prebound_output_continuation_context_id")
        != context_id
        or type(barrier) is not dict
        or type(genesis) is not dict
        or barrier.get("prebound_output_continuation_context_id")
        != context_id
        or genesis.get("prebound_output_continuation_context_id")
        != context_id
        or barrier.get("session_nonce") != session_nonce
        or genesis.get("session_nonce") != session_nonce
        or barrier.get("completed_normal_ordinals") != list(range(41, 53))
        or barrier.get("native_cleanup_complete") is not True
        or barrier.get("output_ordinal_53_prerequisite_satisfied") is not True
        or barrier.get("output_ordinals_53_to_62_authorized") is not False
        or completion.get("output_ordinals_53_to_62_authorized") is not False
        or completion.get("production_output_leaf_authority_present") is not False
        or _ID.fullmatch(str(session_nonce)) is None
        or session_nonce == context_document.get("context_nonce")
    ):
        _fail("E4 exact E3 completion/context/barrier binding changed")
    return dict(completion)


def _binding_fields(
    context_document: Mapping[str, Any],
    *,
    e3_completion_id: str,
    e3_session_nonce: str,
    e3_completion_verified: bool,
) -> dict[str, Any]:
    return {
        "h1_e3_bound_output_continuation_context_id": context_document[
            "h1_e3_bound_output_continuation_context_id"
        ],
        "h1_exclusive_broker_completion_id": e3_completion_id,
        "e3_session_nonce": e3_session_nonce,
        "e3_completion_verified": e3_completion_verified,
        "caller_binding_id": context_document["caller_binding_id"],
        "logical_occurrence_id": context_document["logical_occurrence_id"],
        "route_attempt_id": context_document["route_attempt_id"],
    }


def _base_role_document(
    *,
    role: str,
    candidate_output_bytes: int,
    candidate_read_bytes: int,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    ordinal = ROLE_ORDINALS[role]
    return {
        "schema": ROLE_SCHEMAS[role],
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "role": role,
        "normal_ordinal": ordinal,
        "file_name": ROLE_FILE_NAMES[role],
        **binding,
        "candidate_output_bytes": candidate_output_bytes,
        "candidate_output_read_bytes": candidate_read_bytes,
        "construction_witness_only": True,
        "formal_schema": False,
        **_locked_claims(),
    }


def _render_role_set(
    *,
    context_document: Mapping[str, Any],
    e3_completion_id: str,
    e3_session_nonce: str,
    e3_completion_verified: bool,
    candidate_output_bytes: int,
    candidate_read_bytes: int,
) -> tuple[tuple[str, bytes], ...]:
    _nonnegative(candidate_output_bytes, "candidate output bytes")
    _nonnegative(candidate_read_bytes, "candidate read bytes")
    binding = _binding_fields(
        context_document,
        e3_completion_id=e3_completion_id,
        e3_session_nonce=e3_session_nonce,
        e3_completion_verified=e3_completion_verified,
    )
    rendered: list[tuple[str, bytes]] = []
    prior_rows: list[dict[str, Any]] = []
    for role in ROLE_ORDER[:-1]:
        document = _base_role_document(
            role=role,
            candidate_output_bytes=candidate_output_bytes,
            candidate_read_bytes=candidate_read_bytes,
            binding=binding,
        )
        document["witness_semantics"] = {
            "kind": role,
            "production_semantics_verified": False,
            "formal_parser_must_reject": True,
        }
        raw = canonical_json_bytes(document)
        role_id = _domain_id(
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN,
            document,
        )
        prior_rows.append(
            {
                "role": role,
                "normal_ordinal": ROLE_ORDINALS[role],
                "file_name": ROLE_FILE_NAMES[role],
                "construction_role_witness_id": role_id,
                "sha256": _sha(raw),
                "byte_count": len(raw),
            }
        )
        rendered.append((role, raw))
    manifest = _base_role_document(
        role="OUTPUT_MANIFEST",
        candidate_output_bytes=candidate_output_bytes,
        candidate_read_bytes=candidate_read_bytes,
        binding=binding,
    )
    manifest.update(
        {
            "ordered_nonmanifest_roles": prior_rows,
            "manifest_self_identity_present": False,
            "manifest_self_hash_present": False,
            "manifest_self_extent_present": False,
            "ninth_durable_wrapper_present": False,
            "formal_parser_must_reject": True,
        }
    )
    rendered.append(("OUTPUT_MANIFEST", canonical_json_bytes(manifest)))
    result = tuple(rendered)
    if tuple(role for role, _raw in result) != ROLE_ORDER:
        _fail("E4 renderer changed the exact eight-role order")
    for role, raw in result:
        if not 0 < len(raw) <= MAX_ROLE_BYTES:
            _fail(f"E4 {role} exceeded its exact role-byte cap")
        document = loads_canonical_json(raw)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != raw
            or document.get("schema") != ROLE_SCHEMAS[role]
            or document.get("construction_witness_only") is not True
            or document.get("formal_schema") is not False
        ):
            _fail(f"E4 {role} renderer emitted a non-witness schema")
    total = sum(len(raw) for _role, raw in result)
    if total > MAX_TOTAL_OUTPUT_BYTES:
        _fail("E4 role set exceeded its exact total-output cap")
    return result


def _role_metadata(role_bytes: Sequence[tuple[str, bytes]]) -> list[dict[str, Any]]:
    return [
        {
            "role": role,
            "normal_ordinal": ROLE_ORDINALS[role],
            "file_name": ROLE_FILE_NAMES[role],
            "construction_role_witness_id": _domain_id(
                domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN,
                loads_canonical_json(raw),
            ),
            "sha256": _sha(raw),
            "byte_count": len(raw),
        }
        for role, raw in role_bytes
    ]


def _solve_joint_fixed_point(
    *,
    context_document: Mapping[str, Any],
    e3_completion_id: str,
    e3_session_nonce: str,
    e3_completion_verified: bool,
) -> H1E3BoundOutputJointFixedPointV1:
    e3_completion_id = _cid(e3_completion_id, "E3 completion")
    if type(e3_session_nonce) is not str or _ID.fullmatch(e3_session_nonce) is None:
        _fail("E4 joint fixed point received a malformed E3 session nonce")
    read_base = _nonnegative(context_document.get("read_bytes_base"), "read-bytes base")
    candidate = (0, read_base)
    seen: set[tuple[int, int]] = set()
    iterations: list[dict[str, Any]] = []
    terminal: tuple[tuple[str, bytes], ...] | None = None
    live_render_sets = 0
    maximum_live_render_sets = 0
    for index in range(1, MAX_FIXED_POINT_ITERATIONS + 1):
        if live_render_sets != 0:
            _fail("E4 retained a nonterminal render set across iterations")
        if candidate in seen:
            _fail("E4 joint output/read recurrence cycled")
        seen.add(candidate)
        first = _render_role_set(
            context_document=context_document,
            e3_completion_id=e3_completion_id,
            e3_session_nonce=e3_session_nonce,
            e3_completion_verified=e3_completion_verified,
            candidate_output_bytes=candidate[0],
            candidate_read_bytes=candidate[1],
        )
        live_render_sets += 1
        maximum_live_render_sets = max(maximum_live_render_sets, live_render_sets)
        second = _render_role_set(
            context_document=context_document,
            e3_completion_id=e3_completion_id,
            e3_session_nonce=e3_session_nonce,
            e3_completion_verified=e3_completion_verified,
            candidate_output_bytes=candidate[0],
            candidate_read_bytes=candidate[1],
        )
        live_render_sets += 1
        maximum_live_render_sets = max(maximum_live_render_sets, live_render_sets)
        if first != second:
            _fail("E4 joint fixed-point render is nondeterministic")
        two_render_extent = 2 * sum(len(raw) for _role, raw in first)
        if two_render_extent > SERIALIZER_BUFFER_EXTENT_CAP_BYTES:
            _fail("E4 two-render serializer byte envelope exceeded its cap")
        observed_output = sum(len(raw) for _role, raw in first)
        observed_read = read_base + sum(len(raw) for _role, raw in first)
        observed = (observed_output, observed_read)
        if observed[0] < candidate[0] or observed[1] < candidate[1]:
            _fail("E4 joint output/read recurrence decreased")
        iteration_payload = {
            "schema": "acfqp.k7_h1_joint_output_read_iteration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **_binding_fields(
                context_document,
                e3_completion_id=e3_completion_id,
                e3_session_nonce=e3_session_nonce,
                e3_completion_verified=e3_completion_verified,
            ),
            "iteration_index": index,
            "candidate_output_bytes": candidate[0],
            "candidate_output_read_bytes": candidate[1],
            "observed_output_bytes": observed[0],
            "observed_output_read_bytes": observed[1],
            "read_bytes_base": read_base,
            "role_extents": [
                {"role": role, "byte_count": len(raw)} for role, raw in first
            ],
            "double_render_identical": True,
            "two_render_serializer_extent_bytes": two_render_extent,
            "serializer_extent_is_not_peak_working_memory": True,
            "converged": observed == candidate,
            "construction_witness_only": True,
        }
        iteration = _with_id(
            iteration_payload,
            domain=domains_v11.CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN,
            id_field="h1_joint_output_read_iteration_id",
        )
        iterations.append(iteration)
        if observed == candidate:
            terminal = first
            del first
            del second
            live_render_sets -= 1
            break
        candidate = observed
        del first
        del second
        live_render_sets -= 2
    if terminal is None:
        _fail("E4 joint output/read fixed point did not converge within 32 iterations")
    replay_one = _render_role_set(
        context_document=context_document,
        e3_completion_id=e3_completion_id,
        e3_session_nonce=e3_session_nonce,
        e3_completion_verified=e3_completion_verified,
        candidate_output_bytes=candidate[0],
        candidate_read_bytes=candidate[1],
    )
    live_render_sets += 1
    maximum_live_render_sets = max(maximum_live_render_sets, live_render_sets)
    if terminal != replay_one:
        _fail("E4 first terminal fixed-point replay changed bytes")
    del replay_one
    live_render_sets -= 1
    replay_two = _render_role_set(
        context_document=context_document,
        e3_completion_id=e3_completion_id,
        e3_session_nonce=e3_session_nonce,
        e3_completion_verified=e3_completion_verified,
        candidate_output_bytes=candidate[0],
        candidate_read_bytes=candidate[1],
    )
    live_render_sets += 1
    maximum_live_render_sets = max(maximum_live_render_sets, live_render_sets)
    if terminal != replay_two:
        _fail("E4 second terminal fixed-point replay changed bytes")
    del replay_two
    live_render_sets -= 1
    if live_render_sets != 1 or maximum_live_render_sets > 2:
        _fail("E4 exceeded its two-render live-set envelope")
    metadata = _role_metadata(terminal)
    payload = {
        "schema": "acfqp.k7_h1_joint_output_read_fixed_point.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        **_binding_fields(
            context_document,
            e3_completion_id=e3_completion_id,
            e3_session_nonce=e3_session_nonce,
            e3_completion_verified=e3_completion_verified,
        ),
        "read_bytes_base": read_base,
        "fixed_output_bytes": candidate[0],
        "fixed_output_read_bytes": candidate[1],
        "role_artifacts": metadata,
        "iteration_ids": [row["h1_joint_output_read_iteration_id"] for row in iterations],
        "iterations": iterations,
        "exact_componentwise_fixed_point": True,
        "readback_extent_equals_exact_role_extent": True,
        "terminal_replay_count": 2,
        "terminal_replays_identical": True,
        "maximum_simultaneous_render_sets": maximum_live_render_sets,
        "two_render_live_set_bound_verified": True,
        "terminal_role_set_sha256": _sha(
            canonical_json_bytes(
                [{"role": role, "sha256": _sha(raw)} for role, raw in terminal]
            )
        ),
        "serializer_buffer_extent_cap_bytes": SERIALIZER_BUFFER_EXTENT_CAP_BYTES,
        "serializer_extent_is_not_peak_working_memory": True,
        "construction_witness_only": True,
        **_locked_claims(),
    }
    return H1E3BoundOutputJointFixedPointV1(
        _FIXED_POINT_ISSUER,
        canonical_json_bytes(payload),
        terminal,
    )


def solve_h1_e3_bound_output_joint_fixed_point_for_construction_v1(
    *,
    context: H1E3BoundOutputContinuationContextV1,
    upstream_completion_id: str,
    upstream_session_nonce: str,
) -> H1E3BoundOutputJointFixedPointV1:
    """Pure construction replay; it deliberately does not verify/authorize E3."""

    context_document = _verify_live_context(context, require_empty=True)
    return _solve_joint_fixed_point(
        context_document=context_document,
        e3_completion_id=upstream_completion_id,
        e3_session_nonce=upstream_session_nonce,
        e3_completion_verified=False,
    )


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.pwrite(descriptor, raw[offset:], offset)
        if written <= 0:
            raise OSError("E4 output write made no progress")
        offset += written
    if os.ftruncate(descriptor, len(raw)) is not None:  # pragma: no cover
        raise OSError("E4 ftruncate returned an unexpected value")


def _pread_exact(descriptor: int, extent: int) -> bytes:
    chunks: list[bytes] = []
    offset = 0
    while offset < extent:
        chunk = os.pread(descriptor, min(1024 * 1024, extent - offset), offset)
        if not chunk:
            raise OSError("E4 inode-pinned readback ended early")
        chunks.append(chunk)
        offset += len(chunk)
    if os.pread(descriptor, 1, extent):
        raise OSError("E4 inode-pinned readback has trailing bytes")
    return b"".join(chunks)


def _path_identity(directory_fd: int, file_name: str) -> dict[str, int]:
    metadata = os.stat(file_name, dir_fd=directory_fd, follow_symlinks=False)
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": stat.S_IMODE(metadata.st_mode),
        "nlink": metadata.st_nlink,
        "size": metadata.st_size,
        "is_regular": stat.S_ISREG(metadata.st_mode),
    }


def _fd_identity(descriptor: int) -> dict[str, int]:
    metadata = os.fstat(descriptor)
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": stat.S_IMODE(metadata.st_mode),
        "nlink": metadata.st_nlink,
        "size": metadata.st_size,
        "is_regular": stat.S_ISREG(metadata.st_mode),
    }


def _verify_exact_output_inventory(
    directory_fd: int,
    handles: Mapping[str, int],
    role_bytes: Mapping[str, bytes],
) -> list[dict[str, Any]]:
    if _directory_names(directory_fd) != tuple(sorted(ROLE_FILE_NAMES.values())):
        _fail("E4 pinned directory contains an omitted, extra or renamed entry")
    rows: list[dict[str, Any]] = []
    identities: list[tuple[int, int]] = []
    for role in ROLE_ORDER:
        descriptor = handles.get(role)
        if type(descriptor) is not int or descriptor < 0:
            _fail("E4 output inventory lacks one retained inode handle")
        path_row = _path_identity(directory_fd, ROLE_FILE_NAMES[role])
        fd_row = _fd_identity(descriptor)
        raw = role_bytes[role]
        if (
            path_row != fd_row
            or path_row["is_regular"] is not True
            or path_row["mode"] != 0o400
            or path_row["nlink"] != 1
            or path_row["size"] != len(raw)
        ):
            _fail("E4 path identity, inode handle, mode, link count or extent changed")
        identities.append((path_row["device"], path_row["inode"]))
        rows.append(
            {
                "role": role,
                "normal_ordinal": ROLE_ORDINALS[role],
                "file_name": ROLE_FILE_NAMES[role],
                "device": path_row["device"],
                "inode": path_row["inode"],
                "mode": path_row["mode"],
                "nlink": path_row["nlink"],
                "byte_count": path_row["size"],
            }
        )
    if len(set(identities)) != len(ROLE_ORDER):
        _fail("E4 durable roles do not occupy eight distinct inodes")
    return rows


def _reconstruct_complete_output_document(
    *,
    context_document: Mapping[str, Any],
    e3_completion: Mapping[str, Any],
    fixed_point: H1E3BoundOutputJointFixedPointV1,
    inventory: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Rebuild every success object from authoritative inputs and inode facts."""

    if len(inventory) != len(ROLE_ORDER):
        _fail("E4 complete reconstruction requires eight inode rows")
    fixed_document = fixed_point.to_document()
    role_pairs = tuple(fixed_point.role_bytes)
    role_documents = [loads_canonical_json(raw) for _role, raw in role_pairs]
    context_id = context_document["h1_e3_bound_output_continuation_context_id"]
    e3_completion_id = e3_completion["h1_exclusive_broker_completion_id"]
    session_nonce = e3_completion["session_nonce"]
    allocation_payload = {
        "schema": "acfqp.k7_h1_e3_bound_output_writer_allocation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_e3_bound_output_continuation_context_id": context_id,
        "h1_exclusive_broker_completion_id": e3_completion_id,
        "e3_session_nonce": session_nonce,
        "output_directory": context_document["output_directory"],
        "expected_file_names": [ROLE_FILE_NAMES[role] for role in ROLE_ORDER],
        "directory_empty_before_first_create": True,
        "pinned_parent_directory_fd_is_path_lease": True,
        "parent_entry_fsync_complete": True,
        "pinned_directory_fd_is_writer_lease": True,
        "writer_lease_one_shot": True,
        "construction_witness_only": True,
    }
    allocation = _with_id(
        allocation_payload,
        domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_ALLOCATION_V1_DOMAIN,
        id_field="h1_e3_bound_output_writer_allocation_id",
    )
    allocation_id = allocation["h1_e3_bound_output_writer_allocation_id"]
    commits: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    canonical_inventory: list[dict[str, Any]] = []
    for role, (_pair_role, raw), role_document, raw_inventory in zip(
        ROLE_ORDER, role_pairs, role_documents, inventory
    ):
        row = dict(raw_inventory)
        expected_inventory = {
            "role": role,
            "normal_ordinal": ROLE_ORDINALS[role],
            "file_name": ROLE_FILE_NAMES[role],
            "device": row.get("device"),
            "inode": row.get("inode"),
            "mode": row.get("mode"),
            "nlink": row.get("nlink"),
            "byte_count": row.get("byte_count"),
        }
        if (
            _pair_role != role
            or type(expected_inventory["device"]) is not int
            or type(expected_inventory["inode"]) is not int
            or expected_inventory["mode"] != 0o400
            or expected_inventory["nlink"] != 1
            or expected_inventory["byte_count"] != len(raw)
        ):
            _fail("E4 complete reconstruction received changed inode facts")
        canonical_inventory.append(expected_inventory)
        role_id = _domain_id(
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN,
            role_document,
        )
        commit_payload = {
            "schema": "acfqp.k7_h1_e3_bound_output_role_commit.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_e3_bound_output_continuation_context_id": context_id,
            "h1_e3_bound_output_writer_allocation_id": allocation_id,
            "h1_joint_output_read_fixed_point_id": fixed_point.fixed_point_id,
            "role": role,
            "normal_ordinal": ROLE_ORDINALS[role],
            "file_name": ROLE_FILE_NAMES[role],
            "construction_role_witness_id": role_id,
            "sha256": _sha(raw),
            "byte_count": len(raw),
            "device": expected_inventory["device"],
            "inode": expected_inventory["inode"],
            "requested_create_mode": "0600",
            "read_only_committed_mode": "0400",
            "file_fsync_before_and_after_fchmod": True,
            "o_excl": True,
            "o_nofollow": True,
            "nlink": 1,
            "construction_witness_only": True,
        }
        commits.append(
            _with_id(
                commit_payload,
                domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_COMMIT_V1_DOMAIN,
                id_field="h1_e3_bound_output_role_commit_id",
            )
        )
        event_payload = {
            "schema": "acfqp.k7_h1_e3_bound_output_ordinal_event.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_e3_bound_output_continuation_context_id": context_id,
            "h1_e3_bound_output_writer_allocation_id": allocation_id,
            "h1_joint_output_read_fixed_point_id": fixed_point.fixed_point_id,
            "normal_ordinal": ROLE_ORDINALS[role],
            "effect": "INODE_PINNED_EXACT_OUTPUT_READBACK",
            "role": role,
            "file_name": ROLE_FILE_NAMES[role],
            "device": expected_inventory["device"],
            "inode": expected_inventory["inode"],
            "byte_count": len(raw),
            "sha256": _sha(raw),
            "semantic_readback_count_for_role": 1,
            "exact_once": True,
            "success": True,
            "construction_witness_only": True,
        }
        events.append(
            _with_id(
                event_payload,
                domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ORDINAL_EVENT_V1_DOMAIN,
                id_field="h1_e3_bound_output_ordinal_event_id",
            )
        )
    finalization_payload = {
        "schema": "acfqp.k7_h1_e3_bound_output_finalization.v1",
        "schema_version": SCHEMA_VERSION,
        "h1_e3_bound_output_continuation_context_id": context_id,
        "h1_e3_bound_output_writer_allocation_id": allocation_id,
        "h1_joint_output_read_fixed_point_id": fixed_point.fixed_point_id,
        "normal_ordinal": 61,
        "effect": "EIGHT_ROLE_OUTPUT_DIRECTORY_FINALIZED",
        "role_commit_ids": [
            row["h1_e3_bound_output_role_commit_id"] for row in commits
        ],
        "ordinal_53_to_60_event_ids": [
            row["h1_e3_bound_output_ordinal_event_id"] for row in events
        ],
        "directory_fsync_complete": True,
        "parent_name_to_pinned_inode_reverified": True,
        "exact_directory_inventory": canonical_inventory,
        "fixed_output_bytes": fixed_document["fixed_output_bytes"],
        "fixed_output_read_bytes": fixed_document["fixed_output_read_bytes"],
        "joint_fixed_point_equality_replayed": True,
        "success": True,
        "construction_witness_only": True,
    }
    finalization = _with_id(
        finalization_payload,
        domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_FINALIZATION_V1_DOMAIN,
        id_field="h1_e3_bound_output_finalization_id",
    )
    close_payload = {
        "schema": "acfqp.k7_h1_e3_bound_output_writer_close.v1",
        "schema_version": SCHEMA_VERSION,
        "h1_e3_bound_output_continuation_context_id": context_id,
        "h1_e3_bound_output_writer_allocation_id": allocation_id,
        "h1_e3_bound_output_finalization_id": finalization[
            "h1_e3_bound_output_finalization_id"
        ],
        "normal_ordinal": 62,
        "effect": "WRITER_LEASE_CONSUMED_AND_CLOSED",
        "ordinal_61_predecessor_verified": True,
        "retained_role_handle_count_closed": 8,
        "pinned_directory_fd_closed": True,
        "pinned_parent_directory_fd_closed": True,
        "context_consumed": True,
        "success": True,
        "construction_witness_only": True,
    }
    close_event = _with_id(
        close_payload,
        domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_CLOSE_V1_DOMAIN,
        id_field="h1_e3_bound_output_writer_close_id",
    )
    completion_payload = {
        "schema": "acfqp.k7_h1_e3_bound_output_completion.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_e3_bound_output_continuation_profile_id": _PROFILE.profile_id,
        "h1_e3_bound_output_continuation_context_id": context_id,
        "h1_exclusive_broker_completion_id": e3_completion_id,
        "e3_session_nonce": session_nonce,
        "upstream_authority_disposition": "BROKER_EXCLUSIVE_PRESENT",
        "joint_fixed_point": fixed_document,
        "writer_allocation": allocation,
        "durable_role_commits": commits,
        "durable_role_documents": role_documents,
        "output_ordinal_events_53_to_60": events,
        "ordinal_61_finalization": finalization,
        "ordinal_62_writer_close": close_event,
        "completed_output_ordinals": list(range(53, 63)),
        "output_ordinals_53_to_62_success_events_issued": True,
        "construction_output_completion_present": True,
        "durable_role_count": 8,
        "ninth_durable_wrapper_present": False,
        "construction_witness_only": True,
        **_locked_claims(),
    }
    return _with_id(
        completion_payload,
        domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_COMPLETION_V1_DOMAIN,
        id_field="h1_e3_bound_output_completion_id",
    )


def _close_definitively(descriptor: int) -> bool:
    """Close one owned FD and distinguish a live failure from EBADF."""

    try:
        os.close(descriptor)
        return True
    except OSError as error:
        try:
            fcntl.fcntl(descriptor, fcntl.F_GETFD)
        except OSError as probe_error:
            if probe_error.errno == errno.EBADF:
                return True
        if error.errno == errno.EBADF:
            return True
        return False


def _retire_context(context: H1E3BoundOutputContinuationContextV1) -> bool:
    closed = _close_all_owned_fds(context._owner_key)
    with _OWNERSHIP_LOCK:
        retained = _LIVE_CONTEXTS.get(id(context)) or _QUARANTINED_CONTEXTS.get(
            id(context)
        )
        if retained is None:
            return closed and id(context) in _CONSUMED_CONTEXTS
        if closed:
            _LIVE_CONTEXTS.pop(id(context), None)
            _QUARANTINED_CONTEXTS.pop(id(context), None)
            _CONSUMED_CONTEXTS[id(context)] = retained
            _CONSUMED_CONTEXT_IDS.add(context.context_id)
        else:
            _LIVE_CONTEXTS.pop(id(context), None)
            _QUARANTINED_CONTEXTS[id(context)] = retained
    return closed


def _record_context_consumed_after_definitive_close(
    context: H1E3BoundOutputContinuationContextV1,
) -> None:
    with _OWNERSHIP_LOCK:
        if _owned_fd_rows(context._owner_key):
            _fail("E4 context still owns an FD at writer consumption")
        retained = _LIVE_CONTEXTS.get(id(context)) or _QUARANTINED_CONTEXTS.get(
            id(context)
        )
        if retained is None or retained[0] is not context:
            _fail("E4 context disappeared before definitive writer close")
        _LIVE_CONTEXTS.pop(id(context), None)
        _QUARANTINED_CONTEXTS.pop(id(context), None)
        _CONSUMED_CONTEXTS[id(context)] = retained
        _CONSUMED_CONTEXT_IDS.add(context.context_id)


def close_unconsumed_h1_e3_bound_output_context_v1(
    context: H1E3BoundOutputContinuationContextV1,
) -> None:
    """Explicitly abandon a prepared context without creating E4 evidence."""

    _verify_live_context(context, require_empty=False)
    if not _retire_context(context):
        _fail("E4 could not definitively close the abandoned writer lease")


def retry_h1_e3_bound_output_fd_quarantine_v1(
    context: H1E3BoundOutputContinuationContextV1,
) -> None:
    """Retry cleanup without making a quarantined context reusable."""

    if type(context) is not H1E3BoundOutputContinuationContextV1:
        _fail("E4 cleanup retry requires one exact context")
    with _OWNERSHIP_LOCK:
        retained = _QUARANTINED_CONTEXTS.get(id(context))
        if (
            retained is None
            or retained[0] is not context
            or retained[1] != context.payload_bytes
            or not _owned_fd_rows(context._owner_key)
        ):
            _fail("E4 context has no retryable FD quarantine")
    if not _retire_context(context):
        _fail("E4 FD quarantine remains live after cleanup retry")


def _inject_filesystem_fault(
    fault: H1E4FaultInjectionV1,
    *,
    context: H1E3BoundOutputContinuationContextV1,
) -> None:
    directory_fd = context._directory_fd
    if fault is H1E4FaultInjectionV1.EXTRA_FILE:
        descriptor = os.open(
            "attacker-extra",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_CLOEXEC | _O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        os.close(descriptor)
    elif fault is H1E4FaultInjectionV1.SYMLINK:
        os.symlink("missing-target", "attacker-symlink", dir_fd=directory_fd)
    elif fault is H1E4FaultInjectionV1.HARDLINK:
        os.link(
            ROLE_FILE_NAMES[ROLE_ORDER[0]],
            "attacker-hardlink",
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
    elif fault is H1E4FaultInjectionV1.REPLACE_ROLE:
        file_name = ROLE_FILE_NAMES[ROLE_ORDER[2]]
        os.unlink(file_name, dir_fd=directory_fd)
        descriptor = os.open(
            file_name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | _O_CLOEXEC | _O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        try:
            _write_all(descriptor, b"replacement")
            os.fchmod(descriptor, 0o400)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    elif fault is H1E4FaultInjectionV1.DIRECTORY_RENAME:
        os.rename(
            context._directory_basename,
            f"attacker-moved-{context._owner_key}",
            src_dir_fd=context._parent_fd,
            dst_dir_fd=context._parent_fd,
        )
    elif fault is H1E4FaultInjectionV1.DIRECTORY_UNLINK:
        for role in ROLE_ORDER:
            os.unlink(ROLE_FILE_NAMES[role], dir_fd=directory_fd)
        os.rmdir(context._directory_basename, dir_fd=context._parent_fd)
    elif fault is H1E4FaultInjectionV1.DIRECTORY_CHMOD:
        os.fchmod(directory_fd, 0o755)


def _make_partial(
    *,
    context_document: Mapping[str, Any],
    e3_completion: Mapping[str, Any],
    fixed_point: H1E3BoundOutputJointFixedPointV1 | None,
    writer_allocation: Mapping[str, Any] | None,
    role_commits: Sequence[Mapping[str, Any]],
    role_documents: Sequence[Mapping[str, Any]],
    ordinal_events: Sequence[Mapping[str, Any]],
    finalization: Mapping[str, Any] | None,
    failure_stage: str,
    error: BaseException,
    writer_handles_closed: bool,
    context_consumed: bool,
    outstanding_owned_fd_labels: Sequence[str],
    fault: H1E4FaultInjectionV1,
) -> H1E3BoundOutputPartialNoncertificateV1:
    payload = {
        "schema": "acfqp.k7_h1_e3_bound_output_partial_noncertificate.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_e3_bound_output_continuation_profile_id": _PROFILE.profile_id,
        "h1_e3_bound_output_continuation_context_id": context_document[
            "h1_e3_bound_output_continuation_context_id"
        ],
        "h1_exclusive_broker_completion_id": e3_completion[
            "h1_exclusive_broker_completion_id"
        ],
        "e3_session_nonce": e3_completion["session_nonce"],
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "failure_stage": failure_stage,
        "failure_type": type(error).__name__,
        "failure_message": str(error)[:512],
        "fault_injection": fault.value,
        "joint_fixed_point": None if fixed_point is None else fixed_point.to_document(),
        "writer_allocation": None if writer_allocation is None else dict(writer_allocation),
        "durable_role_commits": [dict(row) for row in role_commits],
        "durable_role_documents": [dict(row) for row in role_documents],
        "observed_output_ordinal_events": [dict(row) for row in ordinal_events],
        "observed_output_ordinal_sequence": [
            row.get("normal_ordinal") for row in ordinal_events
        ],
        "ordinal_61_finalization": None if finalization is None else dict(finalization),
        "ordinal_62_writer_close": None,
        "writer_handles_closed_without_success_ordinal": writer_handles_closed,
        "context_consumed": context_consumed,
        "cleanup_quarantine_present": not writer_handles_closed,
        "outstanding_owned_fd_labels": list(outstanding_owned_fd_labels),
        "output_ordinals_53_to_62_success_events_issued": False,
        "construction_output_completion_present": False,
        "construction_witness_only": True,
        **_locked_claims(),
    }
    return H1E3BoundOutputPartialNoncertificateV1(
        _RESULT_ISSUER, canonical_json_bytes(payload)
    )


def _run_admitted_output_program(
    *,
    context: H1E3BoundOutputContinuationContextV1,
    context_document: Mapping[str, Any],
    e3_completion: Mapping[str, Any],
    fault: H1E4FaultInjectionV1,
) -> H1E3BoundOutputCompletionV1 | H1E3BoundOutputPartialNoncertificateV1:
    handles: dict[str, int] = {}
    fixed_point: H1E3BoundOutputJointFixedPointV1 | None = None
    writer_allocation: dict[str, Any] | None = None
    role_commits: list[dict[str, Any]] = []
    role_documents: list[dict[str, Any]] = []
    ordinal_events: list[dict[str, Any]] = []
    finalization: dict[str, Any] | None = None
    failure_stage = "FIXED_POINT"
    try:
        fixed_point = _solve_joint_fixed_point(
            context_document=context_document,
            e3_completion_id=e3_completion["h1_exclusive_broker_completion_id"],
            e3_session_nonce=e3_completion["session_nonce"],
            e3_completion_verified=True,
        )
        fixed_document = fixed_point.to_document()
        role_bytes = dict(fixed_point.role_bytes)
        failure_stage = "WRITER_ALLOCATION"
        _verify_live_context(context, require_empty=True)
        allocation_payload = {
            "schema": "acfqp.k7_h1_e3_bound_output_writer_allocation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_e3_bound_output_continuation_context_id": context.context_id,
            "h1_exclusive_broker_completion_id": e3_completion[
                "h1_exclusive_broker_completion_id"
            ],
            "e3_session_nonce": e3_completion["session_nonce"],
            "output_directory": context_document["output_directory"],
            "expected_file_names": [ROLE_FILE_NAMES[role] for role in ROLE_ORDER],
            "directory_empty_before_first_create": True,
            "pinned_parent_directory_fd_is_path_lease": True,
            "parent_entry_fsync_complete": True,
            "pinned_directory_fd_is_writer_lease": True,
            "writer_lease_one_shot": True,
            "construction_witness_only": True,
        }
        writer_allocation = _with_id(
            allocation_payload,
            domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_ALLOCATION_V1_DOMAIN,
            id_field="h1_e3_bound_output_writer_allocation_id",
        )
        failure_stage = "ROLE_COMMIT"
        for role in ROLE_ORDER:
            raw = role_bytes[role]
            file_name = ROLE_FILE_NAMES[role]
            descriptor = _open_owned_fd(
                context._owner_key,
                f"ROLE:{role}",
                file_name,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | _O_CLOEXEC | _O_NOFOLLOW,
                0o600,
                dir_fd=context._directory_fd,
            )
            handles[role] = descriptor
            os.fchmod(descriptor, 0o600)
            if stat.S_IMODE(os.fstat(descriptor).st_mode) != 0o600:
                raise OSError("E4 role was not mode 0600 before bytes")
            _write_all(descriptor, raw)
            os.fsync(descriptor)
            os.fchmod(descriptor, 0o400)
            os.fsync(descriptor)
            identity = _fd_identity(descriptor)
            if (
                identity["is_regular"] is not True
                or identity["mode"] != 0o400
                or identity["nlink"] != 1
                or identity["size"] != len(raw)
            ):
                raise OSError("E4 role inode metadata changed during commit")
            role_document = loads_canonical_json(raw)
            if type(role_document) is not dict:
                _fail("E4 durable role is not one canonical document")
            role_documents.append(dict(role_document))
            commit_payload = {
                "schema": "acfqp.k7_h1_e3_bound_output_role_commit.v1",
                "schema_version": SCHEMA_VERSION,
                "h1_e3_bound_output_continuation_context_id": context.context_id,
                "h1_e3_bound_output_writer_allocation_id": writer_allocation[
                    "h1_e3_bound_output_writer_allocation_id"
                ],
                "h1_joint_output_read_fixed_point_id": fixed_point.fixed_point_id,
                "role": role,
                "normal_ordinal": ROLE_ORDINALS[role],
                "file_name": file_name,
                "construction_role_witness_id": _domain_id(
                    domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN,
                    role_document,
                ),
                "sha256": _sha(raw),
                "byte_count": len(raw),
                "device": identity["device"],
                "inode": identity["inode"],
                "requested_create_mode": "0600",
                "read_only_committed_mode": "0400",
                "file_fsync_before_and_after_fchmod": True,
                "o_excl": True,
                "o_nofollow": True,
                "nlink": 1,
                "construction_witness_only": True,
            }
            role_commits.append(
                _with_id(
                    commit_payload,
                    domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_COMMIT_V1_DOMAIN,
                    id_field="h1_e3_bound_output_role_commit_id",
                )
            )
        os.fsync(context._directory_fd)
        _inject_filesystem_fault(fault, context=context)
        inventory = _verify_exact_output_inventory(
            context._directory_fd, handles, role_bytes
        )
        failure_stage = "ORDINAL_READBACK"
        for role in ROLE_ORDER:
            raw = role_bytes[role]
            observed = _pread_exact(handles[role], len(raw))
            if observed != raw:
                _fail("E4 inode-pinned readback bytes changed")
            identity = _fd_identity(handles[role])
            event_payload = {
                "schema": "acfqp.k7_h1_e3_bound_output_ordinal_event.v1",
                "schema_version": SCHEMA_VERSION,
                "h1_e3_bound_output_continuation_context_id": context.context_id,
                "h1_e3_bound_output_writer_allocation_id": writer_allocation[
                    "h1_e3_bound_output_writer_allocation_id"
                ],
                "h1_joint_output_read_fixed_point_id": fixed_point.fixed_point_id,
                "normal_ordinal": ROLE_ORDINALS[role],
                "effect": "INODE_PINNED_EXACT_OUTPUT_READBACK",
                "role": role,
                "file_name": ROLE_FILE_NAMES[role],
                "device": identity["device"],
                "inode": identity["inode"],
                "byte_count": len(observed),
                "sha256": _sha(observed),
                "semantic_readback_count_for_role": 1,
                "exact_once": True,
                "success": True,
                "construction_witness_only": True,
            }
            ordinal_events.append(
                _with_id(
                    event_payload,
                    domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ORDINAL_EVENT_V1_DOMAIN,
                    id_field="h1_e3_bound_output_ordinal_event_id",
                )
            )
            if (
                fault is H1E4FaultInjectionV1.CRASH_AFTER_ORDINAL_55
                and ROLE_ORDINALS[role] == 55
            ):
                raise RuntimeError("injected crash after ordinal 55")
        if fault is H1E4FaultInjectionV1.REORDER_EVENTS:
            ordinal_events[0], ordinal_events[1] = ordinal_events[1], ordinal_events[0]
        elif fault is H1E4FaultInjectionV1.DUPLICATE_EVENT:
            ordinal_events.insert(1, dict(ordinal_events[0]))
        if [row.get("normal_ordinal") for row in ordinal_events] != list(range(53, 61)):
            _fail("E4 output readback events were reordered or duplicated")
        if fault is H1E4FaultInjectionV1.ERROR_BEFORE_FINALIZE_61:
            raise RuntimeError("injected error before ordinal 61")
        inventory_after = _verify_exact_output_inventory(
            context._directory_fd, handles, role_bytes
        )
        if inventory_after != inventory:
            _fail("E4 output inventory changed across exact readback")
        os.fsync(context._directory_fd)
        _verify_bound_output_directory_entry(
            context, context_document, require_empty=False
        )
        if (
            sum(row["byte_count"] for row in inventory_after)
            != fixed_document["fixed_output_bytes"]
            or context_document["read_bytes_base"]
            + sum(row["byte_count"] for row in ordinal_events)
            != fixed_document["fixed_output_read_bytes"]
        ):
            _fail("E4 durable output/readback totals differ from the joint fixed point")
        failure_stage = "FINALIZE_61"
        finalization_payload = {
            "schema": "acfqp.k7_h1_e3_bound_output_finalization.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_e3_bound_output_continuation_context_id": context.context_id,
            "h1_e3_bound_output_writer_allocation_id": writer_allocation[
                "h1_e3_bound_output_writer_allocation_id"
            ],
            "h1_joint_output_read_fixed_point_id": fixed_point.fixed_point_id,
            "normal_ordinal": 61,
            "effect": "EIGHT_ROLE_OUTPUT_DIRECTORY_FINALIZED",
            "role_commit_ids": [
                row["h1_e3_bound_output_role_commit_id"] for row in role_commits
            ],
            "ordinal_53_to_60_event_ids": [
                row["h1_e3_bound_output_ordinal_event_id"] for row in ordinal_events
            ],
            "directory_fsync_complete": True,
            "parent_name_to_pinned_inode_reverified": True,
            "exact_directory_inventory": inventory_after,
            "fixed_output_bytes": fixed_document["fixed_output_bytes"],
            "fixed_output_read_bytes": fixed_document["fixed_output_read_bytes"],
            "joint_fixed_point_equality_replayed": True,
            "success": True,
            "construction_witness_only": True,
        }
        finalization = _with_id(
            finalization_payload,
            domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_FINALIZATION_V1_DOMAIN,
            id_field="h1_e3_bound_output_finalization_id",
        )
        if fault is H1E4FaultInjectionV1.ERROR_AFTER_FINALIZE_61:
            raise RuntimeError("injected error after ordinal 61")
        failure_stage = "CLOSE_62"
        _verify_bound_output_directory_entry(
            context, context_document, require_empty=False
        )
        for role in ROLE_ORDER:
            descriptor = handles[role]
            if not _close_owned_fd(context._owner_key, descriptor):
                raise OSError(f"E4 could not definitively close {role} handle")
            del handles[role]
        if not _close_owned_fd(context._owner_key, context._directory_fd):
            raise OSError("E4 could not definitively close writer directory handle")
        if not _close_owned_fd(context._owner_key, context._parent_fd):
            raise OSError("E4 could not definitively close writer parent handle")
        close_payload = {
            "schema": "acfqp.k7_h1_e3_bound_output_writer_close.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_e3_bound_output_continuation_context_id": context.context_id,
            "h1_e3_bound_output_writer_allocation_id": writer_allocation[
                "h1_e3_bound_output_writer_allocation_id"
            ],
            "h1_e3_bound_output_finalization_id": finalization[
                "h1_e3_bound_output_finalization_id"
            ],
            "normal_ordinal": 62,
            "effect": "WRITER_LEASE_CONSUMED_AND_CLOSED",
            "ordinal_61_predecessor_verified": True,
            "retained_role_handle_count_closed": 8,
            "pinned_directory_fd_closed": True,
            "pinned_parent_directory_fd_closed": True,
            "context_consumed": True,
            "success": True,
            "construction_witness_only": True,
        }
        close_event = _with_id(
            close_payload,
            domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_CLOSE_V1_DOMAIN,
            id_field="h1_e3_bound_output_writer_close_id",
        )
        _record_context_consumed_after_definitive_close(context)
        completion_document = _reconstruct_complete_output_document(
            context_document=context_document,
            e3_completion=e3_completion,
            fixed_point=fixed_point,
            inventory=inventory_after,
        )
        if (
            completion_document["writer_allocation"] != writer_allocation
            or completion_document["durable_role_commits"] != role_commits
            or completion_document["durable_role_documents"] != role_documents
            or completion_document["output_ordinal_events_53_to_60"]
            != ordinal_events
            or completion_document["ordinal_61_finalization"] != finalization
            or completion_document["ordinal_62_writer_close"] != close_event
        ):
            _fail("E4 runtime evidence differs from full authoritative reconstruction")
        return H1E3BoundOutputCompletionV1(
            _RESULT_ISSUER, canonical_json_bytes(completion_document)
        )
    except BaseException as error:
        failure_stage_at_error = failure_stage
        context_consumed = _retire_context(context)
        outstanding_rows = _owned_fd_rows(context._owner_key)
        handles.clear()
        return _make_partial(
            context_document=context_document,
            e3_completion=e3_completion,
            fixed_point=fixed_point,
            writer_allocation=writer_allocation,
            role_commits=role_commits,
            role_documents=role_documents,
            ordinal_events=ordinal_events,
            finalization=finalization,
            failure_stage=failure_stage_at_error,
            error=error,
            writer_handles_closed=not outstanding_rows,
            context_consumed=context_consumed,
            outstanding_owned_fd_labels=tuple(
                sorted(row["label"] for row in outstanding_rows.values())
            ),
            fault=fault,
        )


def continue_h1_e3_bound_output_ordinals_v1(
    *,
    context: H1E3BoundOutputContinuationContextV1,
    e3_completion: e3_v1.H1ExclusiveBrokerCompletionV1,
    fault_injection: H1E4FaultInjectionV1 = H1E4FaultInjectionV1.NONE,
) -> H1E3BoundOutputCompletionV1 | H1E3BoundOutputPartialNoncertificateV1:
    """Continue one exact prebound E3 success through output ordinals 53..62."""

    if type(fault_injection) is not H1E4FaultInjectionV1:
        _fail("E4 fault injection must be one exact registered enum")
    context_document, completion_document = _authorize_exact_e3_completion(
        context, e3_completion
    )
    return _run_admitted_output_program(
        context=context,
        context_document=context_document,
        e3_completion=completion_document,
        fault=fault_injection,
    )


def _verify_completion_document(document: Mapping[str, Any]) -> None:
    if (
        type(document) is not dict
        or document.get("schema") != "acfqp.k7_h1_e3_bound_output_completion.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("h1_e3_bound_output_continuation_profile_id")
        != _PROFILE.profile_id
        or document.get("upstream_authority_disposition")
        != "BROKER_EXCLUSIVE_PRESENT"
        or document.get("completed_output_ordinals") != list(range(53, 63))
        or document.get("output_ordinals_53_to_62_success_events_issued") is not True
        or document.get("construction_output_completion_present") is not True
        or document.get("durable_role_count") != 8
        or document.get("ninth_durable_wrapper_present") is not False
        or document.get("construction_witness_only") is not True
        or any(document.get(key) != value for key, value in _locked_claims().items())
    ):
        _fail("E4 completion authority or locked claims changed")
    context_id = _cid(
        document.get("h1_e3_bound_output_continuation_context_id"),
        "E4 completion context",
    )
    e3_completion_id = _cid(
        document.get("h1_exclusive_broker_completion_id"),
        "E4 upstream completion",
    )
    session_nonce = document.get("e3_session_nonce")
    if type(session_nonce) is not str or _ID.fullmatch(session_nonce) is None:
        _fail("E4 completion session nonce changed")
    fixed = document.get("joint_fixed_point")
    fixed_payload = _verify_content_object(
        fixed,
        domain=domains_v11.CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN,
        id_field="h1_joint_output_read_fixed_point_id",
        label="E4 joint fixed point",
    )
    fixed_id = fixed["h1_joint_output_read_fixed_point_id"]
    iterations = fixed_payload.get("iterations")
    if (
        fixed_payload.get("h1_e3_bound_output_continuation_context_id") != context_id
        or fixed_payload.get("h1_exclusive_broker_completion_id") != e3_completion_id
        or fixed_payload.get("e3_session_nonce") != session_nonce
        or fixed_payload.get("e3_completion_verified") is not True
        or fixed_payload.get("exact_componentwise_fixed_point") is not True
        or fixed_payload.get("terminal_replay_count") != 2
        or fixed_payload.get("terminal_replays_identical") is not True
        or fixed_payload.get("maximum_simultaneous_render_sets") != 2
        or fixed_payload.get("two_render_live_set_bound_verified") is not True
        or fixed_payload.get("serializer_extent_is_not_peak_working_memory") is not True
        or type(iterations) is not list
        or not 1 <= len(iterations) <= MAX_FIXED_POINT_ITERATIONS
    ):
        _fail("E4 completion fixed-point binding changed")
    previous: tuple[int, int] | None = None
    iteration_ids: list[str] = []
    for index, row in enumerate(iterations, start=1):
        payload = _verify_content_object(
            row,
            domain=domains_v11.CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN,
            id_field="h1_joint_output_read_iteration_id",
            label="E4 joint fixed-point iteration",
        )
        candidate = (
            payload.get("candidate_output_bytes"),
            payload.get("candidate_output_read_bytes"),
        )
        observed = (
            payload.get("observed_output_bytes"),
            payload.get("observed_output_read_bytes"),
        )
        if (
            payload.get("iteration_index") != index
            or any(type(value) is not int or value < 0 for value in (*candidate, *observed))
            or (previous is not None and candidate != previous)
            or observed[0] < candidate[0]
            or observed[1] < candidate[1]
            or payload.get("double_render_identical") is not True
            or payload.get("construction_witness_only") is not True
            or payload.get("converged") is not (candidate == observed)
            or (index < len(iterations) and candidate == observed)
            or (index == len(iterations) and candidate != observed)
        ):
            _fail("E4 joint fixed-point iteration trace changed")
        previous = observed
        iteration_ids.append(row["h1_joint_output_read_iteration_id"])
    if (
        fixed_payload.get("iteration_ids") != iteration_ids
        or previous
        != (
            fixed_payload.get("fixed_output_bytes"),
            fixed_payload.get("fixed_output_read_bytes"),
        )
    ):
        _fail("E4 fixed-point terminal equality changed")
    allocation = document.get("writer_allocation")
    allocation_payload = _verify_content_object(
        allocation,
        domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_ALLOCATION_V1_DOMAIN,
        id_field="h1_e3_bound_output_writer_allocation_id",
        label="E4 writer allocation",
    )
    allocation_id = allocation["h1_e3_bound_output_writer_allocation_id"]
    if (
        allocation_payload.get("h1_e3_bound_output_continuation_context_id") != context_id
        or allocation_payload.get("h1_exclusive_broker_completion_id") != e3_completion_id
        or allocation_payload.get("e3_session_nonce") != session_nonce
        or allocation_payload.get("expected_file_names")
        != [ROLE_FILE_NAMES[role] for role in ROLE_ORDER]
        or allocation_payload.get("directory_empty_before_first_create") is not True
        or allocation_payload.get("pinned_parent_directory_fd_is_path_lease")
        is not True
        or allocation_payload.get("parent_entry_fsync_complete") is not True
        or allocation_payload.get("pinned_directory_fd_is_writer_lease") is not True
        or allocation_payload.get("writer_lease_one_shot") is not True
    ):
        _fail("E4 writer-allocation binding changed")
    role_documents = document.get("durable_role_documents")
    commits = document.get("durable_role_commits")
    events = document.get("output_ordinal_events_53_to_60")
    if (
        type(role_documents) is not list
        or type(commits) is not list
        or type(events) is not list
        or len(role_documents) != 8
        or len(commits) != 8
        or len(events) != 8
    ):
        _fail("E4 completion does not contain the exact eight-role evidence")
    rendered_rows: list[dict[str, Any]] = []
    for index, (role, role_document, commit, event) in enumerate(
        zip(ROLE_ORDER, role_documents, commits, events)
    ):
        if type(role_document) is not dict:
            _fail("E4 completion durable role document is malformed")
        raw = canonical_json_bytes(role_document)
        role_id = _domain_id(
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN,
            role_document,
        )
        commit_payload = _verify_content_object(
            commit,
            domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_COMMIT_V1_DOMAIN,
            id_field="h1_e3_bound_output_role_commit_id",
            label="E4 role commit",
        )
        event_payload = _verify_content_object(
            event,
            domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ORDINAL_EVENT_V1_DOMAIN,
            id_field="h1_e3_bound_output_ordinal_event_id",
            label="E4 ordinal event",
        )
        expected_ordinal = 53 + index
        if (
            role_document.get("schema") != ROLE_SCHEMAS[role]
            or role_document.get("role") != role
            or role_document.get("normal_ordinal") != expected_ordinal
            or role_document.get("file_name") != ROLE_FILE_NAMES[role]
            or role_document.get("construction_witness_only") is not True
            or role_document.get("formal_schema") is not False
            or commit_payload.get("role") != role
            or commit_payload.get("normal_ordinal") != expected_ordinal
            or commit_payload.get("file_name") != ROLE_FILE_NAMES[role]
            or commit_payload.get("construction_role_witness_id") != role_id
            or commit_payload.get("sha256") != _sha(raw)
            or commit_payload.get("byte_count") != len(raw)
            or commit_payload.get("nlink") != 1
            or commit_payload.get("read_only_committed_mode") != "0400"
            or event_payload.get("role") != role
            or event_payload.get("normal_ordinal") != expected_ordinal
            or event_payload.get("effect") != "INODE_PINNED_EXACT_OUTPUT_READBACK"
            or event_payload.get("sha256") != _sha(raw)
            or event_payload.get("byte_count") != len(raw)
            or event_payload.get("semantic_readback_count_for_role") != 1
            or event_payload.get("exact_once") is not True
            or event_payload.get("success") is not True
            or event_payload.get("device") != commit_payload.get("device")
            or event_payload.get("inode") != commit_payload.get("inode")
            or commit_payload.get("h1_joint_output_read_fixed_point_id") != fixed_id
            or event_payload.get("h1_joint_output_read_fixed_point_id") != fixed_id
            or commit_payload.get("h1_e3_bound_output_writer_allocation_id") != allocation_id
            or event_payload.get("h1_e3_bound_output_writer_allocation_id") != allocation_id
        ):
            _fail("E4 durable role, commit or readback evidence changed")
        rendered_rows.append(
            {
                "role": role,
                "normal_ordinal": expected_ordinal,
                "file_name": ROLE_FILE_NAMES[role],
                "construction_role_witness_id": role_id,
                "sha256": _sha(raw),
                "byte_count": len(raw),
            }
        )
    manifest = role_documents[-1]
    if (
        manifest.get("ordered_nonmanifest_roles") != rendered_rows[:-1]
        or manifest.get("manifest_self_identity_present") is not False
        or manifest.get("manifest_self_hash_present") is not False
        or manifest.get("manifest_self_extent_present") is not False
        or manifest.get("ninth_durable_wrapper_present") is not False
        or any(
            key in manifest
            for key in (
                "construction_role_witness_id",
                "sha256",
                "byte_count",
                "manifest_id",
            )
        )
    ):
        _fail("E4 output manifest gained a self-reference or ninth wrapper")
    if (
        fixed_payload.get("role_artifacts") != rendered_rows
        or fixed_payload.get("fixed_output_bytes")
        != sum(row["byte_count"] for row in rendered_rows)
        or fixed_payload.get("fixed_output_read_bytes")
        != fixed_payload.get("read_bytes_base")
        + sum(row["byte_count"] for row in rendered_rows)
    ):
        _fail("E4 fixed point differs from the exact durable role set")
    finalization = document.get("ordinal_61_finalization")
    final_payload = _verify_content_object(
        finalization,
        domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_FINALIZATION_V1_DOMAIN,
        id_field="h1_e3_bound_output_finalization_id",
        label="E4 ordinal-61 finalization",
    )
    finalization_id = finalization["h1_e3_bound_output_finalization_id"]
    if (
        final_payload.get("normal_ordinal") != 61
        or final_payload.get("effect") != "EIGHT_ROLE_OUTPUT_DIRECTORY_FINALIZED"
        or final_payload.get("role_commit_ids")
        != [row["h1_e3_bound_output_role_commit_id"] for row in commits]
        or final_payload.get("ordinal_53_to_60_event_ids")
        != [row["h1_e3_bound_output_ordinal_event_id"] for row in events]
        or final_payload.get("directory_fsync_complete") is not True
        or final_payload.get("parent_name_to_pinned_inode_reverified") is not True
        or final_payload.get("joint_fixed_point_equality_replayed") is not True
        or final_payload.get("success") is not True
        or final_payload.get("h1_joint_output_read_fixed_point_id") != fixed_id
    ):
        _fail("E4 ordinal-61 finalization changed")
    close_event = document.get("ordinal_62_writer_close")
    close_payload = _verify_content_object(
        close_event,
        domain=domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_CLOSE_V1_DOMAIN,
        id_field="h1_e3_bound_output_writer_close_id",
        label="E4 ordinal-62 writer close",
    )
    if (
        close_payload.get("normal_ordinal") != 62
        or close_payload.get("effect") != "WRITER_LEASE_CONSUMED_AND_CLOSED"
        or close_payload.get("h1_e3_bound_output_finalization_id") != finalization_id
        or close_payload.get("ordinal_61_predecessor_verified") is not True
        or close_payload.get("retained_role_handle_count_closed") != 8
        or close_payload.get("pinned_directory_fd_closed") is not True
        or close_payload.get("pinned_parent_directory_fd_closed") is not True
        or close_payload.get("context_consumed") is not True
        or close_payload.get("success") is not True
    ):
        _fail("E4 ordinal-62 close changed")


def verify_h1_e3_bound_output_completion_structure_v1(
    value: H1E3BoundOutputCompletionV1 | Mapping[str, Any],
) -> bool:
    """Nonauthoritative shape/ID replay; coherent re-signing is out of scope."""

    document = value.to_document() if type(value) is H1E3BoundOutputCompletionV1 else value
    if type(document) is not dict:
        _fail("E4 completion verifier received a foreign type")
    payload = dict(document)
    supplied = _cid(payload.pop("h1_e3_bound_output_completion_id", None), "E4 completion")
    if (
        _domain_id(
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_COMPLETION_V1_DOMAIN,
            payload,
        )
        != supplied
    ):
        _fail("E4 completion verifier observed a changed content ID")
    _verify_completion_document(dict(document))
    return True


def _verify_retained_context_for_authoritative_replay(
    context: H1E3BoundOutputContinuationContextV1,
) -> dict[str, Any]:
    if type(context) is not H1E3BoundOutputContinuationContextV1:
        _fail("E4 authoritative replay requires the exact issued context")
    with _OWNERSHIP_LOCK:
        retained = _LIVE_CONTEXTS.get(id(context)) or _CONSUMED_CONTEXTS.get(
            id(context)
        )
        if (
            retained is None
            or retained[0] is not context
            or retained[1] != context.payload_bytes
        ):
            _fail("E4 authoritative replay context is not issuer retained")
    document = context.to_document()
    payload = dict(document)
    supplied = _cid(
        payload.pop("h1_e3_bound_output_continuation_context_id", None),
        "E4 authoritative context",
    )
    if (
        _domain_id(
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_CONTINUATION_CONTEXT_V1_DOMAIN,
            payload,
        )
        != supplied
        or supplied != context.context_id
        or document.get("profile_key") != PROFILE_KEY
        or document.get("h1_e3_bound_output_continuation_profile_id")
        != _PROFILE.profile_id
        or document.get("preparer_pid") != os.getpid()
        or document.get("preparer_thread_id") != threading.get_ident()
        or document.get("process_local_writer_lease") is not True
        or document.get("atfork_child_copy_closed_and_registry_cleared") is not True
        or document.get("unified_owned_fd_registry") is not True
        or document.get("persistent_close_failure_quarantine") is not True
        or any(document.get(key) != value for key, value in _locked_claims().items())
    ):
        _fail("E4 authoritative replay context payload changed")
    return document


def _read_authoritative_persisted_inventory(
    *,
    context_document: Mapping[str, Any],
    role_bytes: Sequence[tuple[str, bytes]],
    output_directory: str | os.PathLike[str],
) -> list[dict[str, Any]]:
    """Read inode facts and bytes without trusting completion-supplied rows."""

    directory = Path(output_directory).resolve(strict=True)
    parent_stat = os.stat(directory.parent, follow_symlinks=False)
    recorded = context_document.get("output_directory")
    if type(recorded) is not dict:
        _fail("E4 authoritative replay lacks the context directory binding")
    if (
        directory.name != recorded.get("basename")
        or parent_stat.st_dev != recorded.get("parent_device")
        or parent_stat.st_ino != recorded.get("parent_inode")
        or stat.S_IMODE(parent_stat.st_mode) != recorded.get("parent_mode")
    ):
        _fail("E4 authoritative replay crossed the pinned parent/name")
    directory_fd = os.open(
        directory, os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW
    )
    try:
        identity = _directory_identity(directory_fd)
        if identity != {
            "device": recorded.get("device"),
            "inode": recorded.get("inode"),
            "mode": recorded.get("mode"),
        }:
            _fail("E4 authoritative replay crossed the output directory")
        if _directory_names(directory_fd) != tuple(sorted(ROLE_FILE_NAMES.values())):
            _fail("E4 authoritative replay found a changed output file set")
        rows: list[dict[str, Any]] = []
        identities: set[tuple[int, int]] = set()
        for expected_role, (role, expected_raw) in zip(ROLE_ORDER, role_bytes):
            if role != expected_role:
                _fail("E4 authoritative replay role order changed")
            descriptor = os.open(
                ROLE_FILE_NAMES[role],
                os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            try:
                before = _fd_identity(descriptor)
                path_before = _path_identity(directory_fd, ROLE_FILE_NAMES[role])
                observed = _pread_exact(descriptor, before["size"])
                after = _fd_identity(descriptor)
                path_after = _path_identity(directory_fd, ROLE_FILE_NAMES[role])
            finally:
                if not _close_definitively(descriptor):
                    _fail("E4 authoritative replay could not close a role handle")
            inode_key = (before["device"], before["inode"])
            if (
                before != after
                or before != path_before
                or after != path_after
                or before["is_regular"] is not True
                or before["mode"] != 0o400
                or before["nlink"] != 1
                or inode_key in identities
                or observed != expected_raw
            ):
                _fail("E4 authoritative replay found changed durable output")
            identities.add(inode_key)
            rows.append(
                {
                    "role": role,
                    "normal_ordinal": ROLE_ORDINALS[role],
                    "file_name": ROLE_FILE_NAMES[role],
                    "device": before["device"],
                    "inode": before["inode"],
                    "mode": before["mode"],
                    "nlink": before["nlink"],
                    "byte_count": before["size"],
                }
            )
        return rows
    finally:
        if not _close_definitively(directory_fd):
            _fail("E4 authoritative replay could not close its directory handle")


def _verify_rederived_completion_semantics(
    *,
    completion_document: Mapping[str, Any],
    context_document: Mapping[str, Any],
    exact_e3_completion_document: Mapping[str, Any],
    authoritative_output_directory: str | os.PathLike[str] | None = None,
) -> None:
    """Rebuild the full completion; no supplied nested semantic is trusted."""

    derived = _solve_joint_fixed_point(
        context_document=context_document,
        e3_completion_id=exact_e3_completion_document[
            "h1_exclusive_broker_completion_id"
        ],
        e3_session_nonce=exact_e3_completion_document["session_nonce"],
        e3_completion_verified=True,
    )
    if authoritative_output_directory is None:
        finalization = completion_document.get("ordinal_61_finalization")
        if type(finalization) is not dict or type(
            finalization.get("exact_directory_inventory")
        ) is not list:
            _fail("E4 reconstruction lacks one inode inventory")
        inventory = finalization["exact_directory_inventory"]
    else:
        inventory = _read_authoritative_persisted_inventory(
            context_document=context_document,
            role_bytes=derived.role_bytes,
            output_directory=authoritative_output_directory,
        )
    expected = _reconstruct_complete_output_document(
        context_document=context_document,
        e3_completion=exact_e3_completion_document,
        fixed_point=derived,
        inventory=inventory,
    )
    if dict(completion_document) != expected:
        _fail("E4 authoritative replay differs from full reconstructed completion")


def verify_h1_e3_bound_output_completion_v1(
    *,
    completion: H1E3BoundOutputCompletionV1,
    context: H1E3BoundOutputContinuationContextV1,
    e3_completion: e3_v1.H1ExclusiveBrokerCompletionV1,
) -> bool:
    """Authoritative E4 replay from exact retained context and exact E3 success."""

    if type(completion) is not H1E3BoundOutputCompletionV1:
        _fail("E4 authoritative verifier requires one exact E4 completion")
    context_document = _verify_retained_context_for_authoritative_replay(context)
    exact_e3_document = _verify_exact_e3_completion_against_context(
        context_document=context_document,
        context_id=context.context_id,
        e3_completion=e3_completion,
    )
    completion_document = completion.to_document()
    verify_h1_e3_bound_output_completion_structure_v1(completion_document)
    _verify_rederived_completion_semantics(
        completion_document=completion_document,
        context_document=context_document,
        exact_e3_completion_document=exact_e3_document,
        authoritative_output_directory=context._directory_path,
    )
    return True


def verify_persisted_h1_e3_bound_output_files_for_evaluation_v1(
    *,
    completion: H1E3BoundOutputCompletionV1,
    output_directory: str | os.PathLike[str],
) -> bool:
    """Standalone evaluation-only byte replay; not operational route work."""

    if type(completion) is not H1E3BoundOutputCompletionV1:
        _fail("E4 persisted-file verifier requires one exact completion")
    verify_h1_e3_bound_output_completion_structure_v1(completion)
    document = completion.to_document()
    directory = Path(output_directory).resolve(strict=True)
    parent_stat = os.stat(directory.parent, follow_symlinks=False)
    directory_fd = os.open(
        directory, os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW
    )
    try:
        recorded_directory = document["writer_allocation"]["output_directory"]
        identity = _directory_identity(directory_fd)
        if (
            directory.name != recorded_directory["basename"]
            or parent_stat.st_dev != recorded_directory["parent_device"]
            or parent_stat.st_ino != recorded_directory["parent_inode"]
            or stat.S_IMODE(parent_stat.st_mode) != recorded_directory["parent_mode"]
            or identity
            != {
                "device": recorded_directory["device"],
                "inode": recorded_directory["inode"],
                "mode": recorded_directory["mode"],
            }
        ):
            _fail("E4 evaluation verifier crossed the output directory")
        if _directory_names(directory_fd) != tuple(sorted(ROLE_FILE_NAMES.values())):
            _fail("E4 evaluation verifier found a changed output file set")
        identities: set[tuple[int, int]] = set()
        for role, role_document, commit in zip(
            ROLE_ORDER,
            document["durable_role_documents"],
            document["durable_role_commits"],
        ):
            descriptor = os.open(
                ROLE_FILE_NAMES[role],
                os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            try:
                metadata = _fd_identity(descriptor)
                raw = _pread_exact(descriptor, metadata["size"])
            finally:
                if not _close_definitively(descriptor):
                    _fail("E4 evaluation verifier could not close a role handle")
            if (
                metadata["is_regular"] is not True
                or metadata["mode"] != 0o400
                or metadata["nlink"] != 1
                or (metadata["device"], metadata["inode"]) in identities
                or metadata["device"] != commit["device"]
                or metadata["inode"] != commit["inode"]
                or raw != canonical_json_bytes(role_document)
                or _sha(raw) != commit["sha256"]
                or len(raw) != commit["byte_count"]
            ):
                _fail("E4 evaluation verifier found changed durable output bytes")
            identities.add((metadata["device"], metadata["inode"]))
        return True
    finally:
        if not _close_definitively(directory_fd):
            _fail("E4 evaluation verifier could not close its directory handle")


__all__ = (
    "CONSTRUCTION_OUTPUT_ORDINAL_53_TO_62_WITNESS_PRESENT",
    "COUNTER_COMPLETENESS_GATE",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error",
    "E3_BOUND_OUTPUT_CONTINUATION_PRESENT",
    "FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1E3BoundOutputCompletionV1",
    "H1E3BoundOutputContinuationContextV1",
    "H1E3BoundOutputContinuationProfileV1",
    "H1E3BoundOutputJointFixedPointV1",
    "H1E3BoundOutputPartialNoncertificateV1",
    "H1E4FaultInjectionV1",
    "MAX_FIXED_POINT_ITERATIONS",
    "MAX_ROLE_BYTES",
    "MAX_TOTAL_OUTPUT_BYTES",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PEAK_SCOPE_STATUS",
    "PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_FILE_NAMES",
    "ROLE_ORDER",
    "ROLE_ORDINALS",
    "ROLE_SCHEMAS",
    "ROUTE_WIDE_PEAK_AUTHORITY_PRESENT",
    "SCHEMA_VERSION",
    "SERIALIZER_BUFFER_EXTENT_CAP_BYTES",
    "WORKLOAD_ECONOMICS_GATE",
    "close_unconsumed_h1_e3_bound_output_context_v1",
    "continue_h1_e3_bound_output_ordinals_v1",
    "official_h1_e3_bound_output_continuation_profile_v1",
    "prepare_h1_e3_bound_output_continuation_context_v1",
    "retry_h1_e3_bound_output_fd_quarantine_v1",
    "solve_h1_e3_bound_output_joint_fixed_point_for_construction_v1",
    "verify_h1_e3_bound_output_completion_v1",
    "verify_h1_e3_bound_output_completion_structure_v1",
    "verify_persisted_h1_e3_bound_output_files_for_evaluation_v1",
)
