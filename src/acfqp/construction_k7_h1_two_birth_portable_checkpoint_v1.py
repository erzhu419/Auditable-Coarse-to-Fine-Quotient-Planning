"""Durable, non-authoritative observation graph for the raw two-birth cut.

This producer deliberately does not join the E5A/B2 lease authority.  It
freezes the exact source files used by the raw runtime before birth, retains a
source descriptor and a duplicate witness for every file until the root
checkpoint has crossed both file and directory ``fsync``, and persists three
domain-separated records:

``execution source closure -> credential observation bundle -> root``.

The root records that its observation was issued while SUPERVISOR was live,
but it is returned only after the V1 protocol has normally shut that process
down.  Consequently these bytes are neither a continuation capability nor an
exact/exclusive topology certificate.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import threading
import types
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v18 as domains_v18
from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_exec_birth_native_v1 as exec_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as role_v1
from acfqp import construction_k7_h1_nested_creator_two_birth_runtime_v1 as runtime_v1
from acfqp import phase3e_ids as ids_v1


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_h1_two_birth_portable_checkpoint_v1"
READINESS = "DURABLE_NONAUTHORITATIVE_TWO_BIRTH_OBSERVATION_ONLY"

EXECUTION_SOURCE_CLOSURE_IMPLEMENTATION_PRESENT = True
NESTED_CREDENTIAL_OBSERVATION_BUNDLE_IMPLEMENTATION_PRESENT = True
PORTABLE_OBSERVATION_CHECKPOINT_IMPLEMENTATION_PRESENT = True
DURABLE_PORTABLE_OBSERVATION_GRAPH_IMPLEMENTATION_PRESENT = True

E5A_RUNTIME_LEASE_JOIN_PRESENT = False
EXACT_TWO_BIRTH_OS_TOPOLOGY_OBSERVED = False
PORTABLE_CHECKPOINT_AUTHORITY_PRESENT = False
TWO_BIRTH_PREFIX_AUTHORITY_PRESENT = False
FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
E4_V2_COMPLETION_PRESENT = False
PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
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

_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_PR_GET_CHILD_SUBREAPER = 37
_LIBC = ctypes.CDLL(None, use_errno=True)
_ISSUER = object()
_PRODUCER_LOCK = threading.RLock()
_TEST_FAULT_PHASE: str | None = None
_FINGERPRINT_JSON_DUMPS = json.dumps


class ConstructionK7H1TwoBirthPortableCheckpointV1Error(RuntimeError):
    """The non-authoritative producer or its exact cleanup failed closed."""

    def __init__(
        self,
        message: str,
        *,
        failure_closure: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.failure_closure = failure_closure


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1TwoBirthPortableCheckpointV1Error(message)


def _test_fault(phase: str) -> None:
    global _TEST_FAULT_PHASE
    if _TEST_FAULT_PHASE == phase:
        _TEST_FAULT_PHASE = None
        _fail(f"injected portable-checkpoint fault after {phase}")


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if type(value) in {list, tuple}:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


def _fingerprint_canonical_json_bytes(value: Any) -> bytes:
    """Canonical bytes for the already-tagged fingerprint value language."""

    return _FINGERPRINT_JSON_DUMPS(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def _locked_claims() -> dict[str, Any]:
    return {
        "e5a_runtime_lease_join_present": False,
        "exact_two_birth_os_topology_observed": False,
        "portable_checkpoint_authority_present": False,
        "two_birth_prefix_authority_present": False,
        "five_birth_process_authority_present": False,
        "actual_observed_e3_v2_completion_present": False,
        "e4_v2_completion_present": False,
        "production_shared_resource_receipts_present": False,
        "fq11_counter_completeness_present": False,
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


def _content_document(
    *, domain: str, id_field: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    _validate_external_authorities()
    _VALIDATE_INTERNAL_AUTHORITIES()
    document = dict(payload)
    document[id_field] = _V18_CONTENT_ID(domain, document)
    return document


def _exact_write(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        try:
            written = os.write(descriptor, raw[offset:])
        except InterruptedError:
            continue
        if written <= 0:
            _fail("portable-checkpoint record write made no progress")
        offset += written


def _read_exact_fd(descriptor: int, size: int) -> bytes:
    chunks: list[bytes] = []
    offset = 0
    while offset < size:
        chunk = os.pread(descriptor, min(1 << 20, size - offset), offset)
        if not chunk:
            _fail("portable-checkpoint source or record ended early")
        chunks.append(chunk)
        offset += len(chunk)
    if os.pread(descriptor, 1, offset):
        _fail("portable-checkpoint source or record grew")
    return b"".join(chunks)


def _fd_identity(descriptor: int) -> tuple[int, int, int, int, int, int, int]:
    status = os.fstat(descriptor)
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_nlink,
        status.st_size,
    )


@dataclass(frozen=True, slots=True)
class _ModulePathAuthorityV1:
    label: str
    module: Any
    path: Path
    device: int
    inode: int
    mode: int

    def revalidate(self) -> None:
        module_path = getattr(self.module, "__file__", None)
        module_spec = getattr(self.module, "__spec__", None)
        origin = getattr(module_spec, "origin", None)
        if (
            type(module_path) is not str
            or Path(module_path).resolve() != self.path
            or type(origin) is not str
            or Path(origin).resolve() != self.path
        ):
            _fail("portable-checkpoint module path authority changed")
        status = os.stat(self.path, follow_symlinks=False)
        if (status.st_dev, status.st_ino, status.st_mode) != (
            self.device,
            self.inode,
            self.mode,
        ):
            _fail("portable-checkpoint module inode authority changed")


def _semantic_value_document(value: Any) -> dict[str, Any]:
    """Encode code constants/defaults without repr, marshal, or addresses."""

    if value is None:
        return {"kind": "NONE"}
    if value is Ellipsis:
        return {"kind": "ELLIPSIS"}
    if value is NotImplemented:
        return {"kind": "NOT_IMPLEMENTED"}
    if type(value) is bool:
        return {"kind": "BOOL", "value": value}
    if type(value) is int:
        return {"kind": "INT", "decimal": str(value)}
    if type(value) is float:
        return {"kind": "FLOAT_HEX", "value": value.hex()}
    if type(value) is complex:
        return {
            "kind": "COMPLEX_HEX",
            "real": value.real.hex(),
            "imag": value.imag.hex(),
        }
    if type(value) is str:
        return {"kind": "STR", "value": value}
    if type(value) is bytes:
        return {"kind": "BYTES", "hex": value.hex()}
    if type(value) is tuple:
        return {
            "kind": "TUPLE",
            "items": [_semantic_value_document(item) for item in value],
        }
    if type(value) is frozenset:
        items = [_semantic_value_document(item) for item in value]
        items.sort(key=_fingerprint_canonical_json_bytes)
        return {"kind": "FROZENSET", "items": items}
    if type(value) is list:
        return {
            "kind": "LIST",
            "items": [_semantic_value_document(item) for item in value],
        }
    if type(value) is dict:
        items = [
            {
                "key": _semantic_value_document(key),
                "value": _semantic_value_document(item),
            }
            for key, item in value.items()
        ]
        items.sort(key=_fingerprint_canonical_json_bytes)
        return {"kind": "DICT", "items": items}
    if type(value) is types.CodeType:
        return {"kind": "CODE", "value": _code_fingerprint_document(value)}
    _fail("portable-checkpoint callable contains an unsupported semantic value")


def _code_fingerprint_document(code: types.CodeType) -> dict[str, Any]:
    if type(code) is not types.CodeType:
        _fail("portable-checkpoint callable code object changed type")
    return {
        "schema": "acfqp.python_code_semantics.v1",
        "co_name": code.co_name,
        "co_firstlineno": code.co_firstlineno,
        "co_argcount": code.co_argcount,
        "co_posonlyargcount": code.co_posonlyargcount,
        "co_kwonlyargcount": code.co_kwonlyargcount,
        "co_nlocals": code.co_nlocals,
        "co_stacksize": code.co_stacksize,
        "co_flags": code.co_flags,
        "co_code_hex": code.co_code.hex(),
        "co_code_sha256": hashlib.sha256(code.co_code).hexdigest(),
        "co_consts": [
            _semantic_value_document(value) for value in code.co_consts
        ],
        "co_names": list(code.co_names),
        "co_varnames": list(code.co_varnames),
        "co_freevars": list(code.co_freevars),
        "co_cellvars": list(code.co_cellvars),
        "co_exceptiontable_hex": getattr(code, "co_exceptiontable", b"").hex(),
    }


def _callable_semantic_documents(
    function: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    code = getattr(function, "__code__", None)
    if type(code) is not types.CodeType:
        _fail("portable-checkpoint external callable is not one Python function")
    code_document = _code_fingerprint_document(code)
    defaults_document = _semantic_value_document(function.__defaults__)
    kwdefaults_document = _semantic_value_document(function.__kwdefaults__)
    code_sha256 = hashlib.sha256(
        _fingerprint_canonical_json_bytes(code_document)
    ).hexdigest()
    callable_document = {
        "schema": "acfqp.python_callable_semantics.v1",
        "code_fingerprint_document": code_document,
        "defaults_fingerprint_document": defaults_document,
        "kwdefaults_fingerprint_document": kwdefaults_document,
    }
    callable_sha256 = hashlib.sha256(
        _fingerprint_canonical_json_bytes(callable_document)
    ).hexdigest()
    return (
        code_document,
        defaults_document,
        kwdefaults_document,
        code_sha256,
        callable_sha256,
    )


@dataclass(frozen=True, slots=True)
class _CallableAuthorityV1:
    label: str
    module: Any
    attribute: str
    function: Any
    code: Any
    code_fingerprint_document: Mapping[str, Any]
    defaults_fingerprint_document: Mapping[str, Any]
    kwdefaults_fingerprint_document: Mapping[str, Any]
    code_fingerprint_sha256: str
    callable_semantic_fingerprint_sha256: str
    module_path: Path

    def revalidate(self) -> None:
        current = getattr(self.module, self.attribute, None)
        (
            code_document,
            defaults_document,
            kwdefaults_document,
            code_sha256,
            callable_sha256,
        ) = _callable_semantic_documents(current)
        if (
            current is not self.function
            or getattr(current, "__code__", None) is not self.code
            or _freeze_json(code_document) != self.code_fingerprint_document
            or _freeze_json(defaults_document)
            != self.defaults_fingerprint_document
            or _freeze_json(kwdefaults_document)
            != self.kwdefaults_fingerprint_document
            or code_sha256 != self.code_fingerprint_sha256
            or callable_sha256 != self.callable_semantic_fingerprint_sha256
            or getattr(current, "__module__", None)
            != getattr(self.function, "__module__", None)
        ):
            _fail("portable-checkpoint callable authority changed")

    def document(self, repository_root: Path) -> dict[str, Any]:
        return {
            "role": self.label,
            "module": self.function.__module__,
            "qualname": self.function.__qualname__,
            "module_repository_relative_path": self.module_path.relative_to(
                repository_root
            ).as_posix(),
            "code_first_line": self.code.co_firstlineno,
            "code_fingerprint_document": _thaw_json(
                self.code_fingerprint_document
            ),
            "defaults_fingerprint_document": _thaw_json(
                self.defaults_fingerprint_document
            ),
            "kwdefaults_fingerprint_document": _thaw_json(
                self.kwdefaults_fingerprint_document
            ),
            "code_fingerprint_sha256": self.code_fingerprint_sha256,
            "callable_semantic_fingerprint_sha256": (
                self.callable_semantic_fingerprint_sha256
            ),
            "callable_object_and_code_identity_revalidated": True,
        }


def _capture_module_path(label: str, module: Any) -> _ModulePathAuthorityV1:
    raw_path = getattr(module, "__file__", None)
    if type(raw_path) is not str:
        _fail("portable-checkpoint module has no source path")
    path = Path(raw_path).resolve(strict=True)
    status = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(status.st_mode):
        _fail("portable-checkpoint module path is not regular")
    return _ModulePathAuthorityV1(
        label,
        module,
        path,
        status.st_dev,
        status.st_ino,
        status.st_mode,
    )


def _capture_callable(
    label: str,
    module: Any,
    attribute: str,
    module_path: Path,
) -> _CallableAuthorityV1:
    function = getattr(module, attribute, None)
    code = getattr(function, "__code__", None)
    if function is None or code is None:
        _fail("portable-checkpoint external callable is not one Python function")
    (
        code_document,
        defaults_document,
        kwdefaults_document,
        code_sha256,
        callable_sha256,
    ) = _callable_semantic_documents(function)
    return _CallableAuthorityV1(
        label,
        module,
        attribute,
        function,
        code,
        _freeze_json(code_document),
        _freeze_json(defaults_document),
        _freeze_json(kwdefaults_document),
        code_sha256,
        callable_sha256,
        module_path,
    )


_REPOSITORY_ROOT = Path(__file__).resolve(strict=True).parents[2]
_MODULE_PATH_AUTHORITIES = tuple(
    _capture_module_path(label, module)
    for label, module in (
        ("PORTABLE_CHECKPOINT_PRODUCER_PYTHON", sys.modules[__name__]),
        ("V18_DOMAIN_REGISTRY_PYTHON", domains_v18),
        ("CANONICAL_JSON_IDENTITY_PYTHON", ids_v1),
        ("TWO_BIRTH_RUNTIME_PYTHON", runtime_v1),
        ("NESTED_PROBE_RUNTIME_PYTHON", probe_v1),
        ("SUPERVISOR_EXEC_BIRTH_PYTHON", exec_v1),
        ("SUPERVISOR_ROLE_PYTHON", role_v1),
    )
)
_MODULE_PATH_BY_LABEL = MappingProxyType(
    {
        authority.label: authority.path
        for authority in _MODULE_PATH_AUTHORITIES
    }
)
_CALLABLE_AUTHORITIES = tuple(
    _capture_callable(label, module, attribute, module_path)
    for label, module, attribute, module_path in (
        (
            "RUNTIME_BEGIN",
            runtime_v1,
            "begin_bounded_nested_creator_two_birth_live_prefix_v1",
            _MODULE_PATH_BY_LABEL["TWO_BIRTH_RUNTIME_PYTHON"],
        ),
        (
            "RUNTIME_SNAPSHOT",
            runtime_v1,
            "snapshot_bounded_nested_creator_two_birth_live_prefix_v1",
            _MODULE_PATH_BY_LABEL["TWO_BIRTH_RUNTIME_PYTHON"],
        ),
        (
            "RUNTIME_CLOSE",
            runtime_v1,
            "close_bounded_nested_creator_two_birth_live_prefix_v1",
            _MODULE_PATH_BY_LABEL["TWO_BIRTH_RUNTIME_PYTHON"],
        ),
        (
            "RUNTIME_ABORT",
            runtime_v1,
            "abort_bounded_nested_creator_two_birth_live_prefix_v1",
            _MODULE_PATH_BY_LABEL["TWO_BIRTH_RUNTIME_PYTHON"],
        ),
        (
            "RUNTIME_BEGIN_FAILURE_RECOVERY",
            runtime_v1,
            "recover_bounded_nested_creator_two_birth_begin_failure_v1",
            _MODULE_PATH_BY_LABEL["TWO_BIRTH_RUNTIME_PYTHON"],
        ),
        (
            "CONTROL_POPULATION_OBSERVE",
            probe_v1,
            "observe_nested_creator_control_population_v1",
            _MODULE_PATH_BY_LABEL["NESTED_PROBE_RUNTIME_PYTHON"],
        ),
        (
            "V18_CONTENT_ID",
            domains_v18,
            "extension_content_id_v18",
            _MODULE_PATH_BY_LABEL["V18_DOMAIN_REGISTRY_PYTHON"],
        ),
        (
            "CANONICAL_JSON_BYTES",
            ids_v1,
            "canonical_json_bytes",
            _MODULE_PATH_BY_LABEL["CANONICAL_JSON_IDENTITY_PYTHON"],
        ),
    )
)
_CALLABLE_BY_LABEL = {
    authority.label: authority.function for authority in _CALLABLE_AUTHORITIES
}
_RUNTIME_BEGIN = _CALLABLE_BY_LABEL["RUNTIME_BEGIN"]
_RUNTIME_SNAPSHOT = _CALLABLE_BY_LABEL["RUNTIME_SNAPSHOT"]
_RUNTIME_CLOSE = _CALLABLE_BY_LABEL["RUNTIME_CLOSE"]
_RUNTIME_ABORT = _CALLABLE_BY_LABEL["RUNTIME_ABORT"]
_RUNTIME_BEGIN_FAILURE_RECOVERY = _CALLABLE_BY_LABEL[
    "RUNTIME_BEGIN_FAILURE_RECOVERY"
]
_OBSERVE_CONTROL_POPULATION = _CALLABLE_BY_LABEL[
    "CONTROL_POPULATION_OBSERVE"
]
_V18_CONTENT_ID = _CALLABLE_BY_LABEL["V18_CONTENT_ID"]
_CANONICAL_JSON_BYTES = _CALLABLE_BY_LABEL["CANONICAL_JSON_BYTES"]

_SOURCE_CLOSURE_DOMAIN = (
    domains_v18.CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN
)
_CREDENTIAL_BUNDLE_DOMAIN = (
    domains_v18.CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN
)
_LIVE_CHECKPOINT_DOMAIN = (
    domains_v18.CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN
)
_FAILURE_CLOSURE_DOMAIN = (
    domains_v18.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN
)
_DOMAIN_AUTHORITIES = (
    (
        "CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN",
        _SOURCE_CLOSURE_DOMAIN,
    ),
    (
        "CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN",
        _CREDENTIAL_BUNDLE_DOMAIN,
    ),
    (
        "CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN",
        _LIVE_CHECKPOINT_DOMAIN,
    ),
    (
        "CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN",
        _FAILURE_CLOSURE_DOMAIN,
    ),
)
_EXEC_SOURCE_PATH = exec_v1.SOURCE_PATH.resolve(strict=True)
_ROLE_SOURCE_PATH = role_v1.SOURCE_PATH.resolve(strict=True)
_EXEC_SOURCE_PATH_IDENTITY = os.stat(
    _EXEC_SOURCE_PATH, follow_symlinks=False
).st_dev, os.stat(_EXEC_SOURCE_PATH, follow_symlinks=False).st_ino
_ROLE_SOURCE_PATH_IDENTITY = os.stat(
    _ROLE_SOURCE_PATH, follow_symlinks=False
).st_dev, os.stat(_ROLE_SOURCE_PATH, follow_symlinks=False).st_ino
_RUNTIME_PROFILE_KEY = runtime_v1.PROFILE_KEY
_RUNTIME_READINESS = runtime_v1.READINESS
_PROBE_PROFILE_KEY = probe_v1.PROFILE_KEY
_PARENT_REQUIRED_SUCCESS_BITS = exec_v1.PARENT_EDGE_REQUIRED_SUCCESS_BITS
_ROLE_ELF_SHA256 = role_v1.ELF_SHA256
_ROLE_ELF_BYTE_COUNT = role_v1.ELF_BYTE_COUNT
_ROLE_OPCODES = dict(role_v1.OPCODES)
_REQUIRED_SEALS = runtime_v1.REQUIRED_SEALS
_RUNTIME_ERROR_TYPE = runtime_v1.ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error


def _validate_external_authorities() -> None:
    for authority in _MODULE_PATH_AUTHORITIES:
        authority.revalidate()
    for authority in _CALLABLE_AUTHORITIES:
        authority.revalidate()
    for attribute, expected in _DOMAIN_AUTHORITIES:
        if getattr(domains_v18, attribute, None) != expected:
            _fail("portable-checkpoint V18 domain authority changed")
    if (
        (
            _SOURCE_CLOSURE_DOMAIN,
            _CREDENTIAL_BUNDLE_DOMAIN,
            _LIVE_CHECKPOINT_DOMAIN,
            _FAILURE_CLOSURE_DOMAIN,
        )
        != tuple(expected for _, expected in _DOMAIN_AUTHORITIES)
        or _RUNTIME_BEGIN is not _CALLABLE_BY_LABEL["RUNTIME_BEGIN"]
        or _RUNTIME_SNAPSHOT is not _CALLABLE_BY_LABEL["RUNTIME_SNAPSHOT"]
        or _RUNTIME_CLOSE is not _CALLABLE_BY_LABEL["RUNTIME_CLOSE"]
        or _RUNTIME_ABORT is not _CALLABLE_BY_LABEL["RUNTIME_ABORT"]
        or _RUNTIME_BEGIN_FAILURE_RECOVERY
        is not _CALLABLE_BY_LABEL["RUNTIME_BEGIN_FAILURE_RECOVERY"]
        or _OBSERVE_CONTROL_POPULATION
        is not _CALLABLE_BY_LABEL["CONTROL_POPULATION_OBSERVE"]
        or _V18_CONTENT_ID is not _CALLABLE_BY_LABEL["V18_CONTENT_ID"]
        or _CANONICAL_JSON_BYTES
        is not _CALLABLE_BY_LABEL["CANONICAL_JSON_BYTES"]
        or
        exec_v1.SOURCE_PATH.resolve() != _EXEC_SOURCE_PATH
        or role_v1.SOURCE_PATH.resolve() != _ROLE_SOURCE_PATH
        or (
            os.stat(_EXEC_SOURCE_PATH, follow_symlinks=False).st_dev,
            os.stat(_EXEC_SOURCE_PATH, follow_symlinks=False).st_ino,
        )
        != _EXEC_SOURCE_PATH_IDENTITY
        or (
            os.stat(_ROLE_SOURCE_PATH, follow_symlinks=False).st_dev,
            os.stat(_ROLE_SOURCE_PATH, follow_symlinks=False).st_ino,
        )
        != _ROLE_SOURCE_PATH_IDENTITY
        or runtime_v1.PROFILE_KEY != _RUNTIME_PROFILE_KEY
        or runtime_v1.READINESS != _RUNTIME_READINESS
        or probe_v1.PROFILE_KEY != _PROBE_PROFILE_KEY
        or exec_v1.PARENT_EDGE_REQUIRED_SUCCESS_BITS
        != _PARENT_REQUIRED_SUCCESS_BITS
        or role_v1.ELF_SHA256 != _ROLE_ELF_SHA256
        or role_v1.ELF_BYTE_COUNT != _ROLE_ELF_BYTE_COUNT
        or dict(role_v1.OPCODES) != _ROLE_OPCODES
        or runtime_v1.REQUIRED_SEALS != _REQUIRED_SEALS
        or runtime_v1.ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error
        is not _RUNTIME_ERROR_TYPE
    ):
        _fail("portable-checkpoint runtime/source authority changed")


def _open_fd_identities(*, exclude: set[int]) -> dict[int, tuple[int, int, int]]:
    result: dict[int, tuple[int, int, int]] = {}
    for name in os.listdir("/proc/self/fd"):
        if not name.isdigit():
            continue
        descriptor = int(name)
        if descriptor in exclude:
            continue
        try:
            status = os.fstat(descriptor)
        except OSError:
            continue
        result[descriptor] = (status.st_dev, status.st_ino, status.st_mode)
    return result


def _get_subreaper() -> bool:
    value = ctypes.c_int(-1)
    if _LIBC.prctl(_PR_GET_CHILD_SUBREAPER, ctypes.byref(value), 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise ConstructionK7H1TwoBirthPortableCheckpointV1Error(
            "portable-checkpoint cannot read subreaper state"
        ) from OSError(error, os.strerror(error))
    if value.value not in {0, 1}:
        _fail("portable-checkpoint subreaper state is malformed")
    return bool(value.value)


def _direct_children() -> tuple[int, ...]:
    raw = Path(
        f"/proc/self/task/{threading.get_native_id()}/children"
    ).read_text(encoding="ascii").split()
    if any(not item.isdigit() or int(item) <= 0 for item in raw):
        _fail("portable-checkpoint direct-child inventory is malformed")
    return tuple(sorted(int(item) for item in raw))


@dataclass(slots=True)
class _SourceBindingV1:
    role: str
    relative_path: str
    path: Path
    source_fd: int
    witness_fd: int
    identity: tuple[int, int, int, int, int, int, int]
    sha256: str
    source_bytes: bytes = field(repr=False)

    @property
    def descriptors(self) -> tuple[int, int]:
        return self.source_fd, self.witness_fd

    def document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "repository_relative_path": self.relative_path,
            "device": self.identity[0],
            "inode": self.identity[1],
            "mode": self.identity[2],
            "uid": self.identity[3],
            "gid": self.identity[4],
            "link_count": self.identity[5],
            "byte_count": self.identity[6],
            "sha256": self.sha256,
            "source_bytes_hex": self.source_bytes.hex(),
            "source_and_witness_same_inode": True,
            "source_descriptor_cloexec": True,
            "witness_descriptor_cloexec": True,
            "descriptor_numbers_serialized": False,
            "absolute_path_serialized": False,
        }


class _SourceClosureLeaseV1:
    __slots__ = ("bindings", "closed", "repository_root")

    def __init__(self, repository_root: Path) -> None:
        self.bindings: list[_SourceBindingV1] = []
        self.closed = False
        self.repository_root = repository_root

    @property
    def descriptors(self) -> set[int]:
        return {
            descriptor
            for binding in self.bindings
            for descriptor in binding.descriptors
            if descriptor >= 0
        }

    def revalidate(self) -> None:
        _validate_external_authorities()
        if self.closed or not self.bindings:
            _fail("portable-checkpoint source lease is absent or closed")
        for binding in self.bindings:
            if (
                _fd_identity(binding.source_fd) != binding.identity
                or _fd_identity(binding.witness_fd) != binding.identity
                or fcntl.fcntl(binding.source_fd, fcntl.F_GETFD)
                & fcntl.FD_CLOEXEC
                == 0
                or fcntl.fcntl(binding.witness_fd, fcntl.F_GETFD)
                & fcntl.FD_CLOEXEC
                == 0
            ):
                _fail("portable-checkpoint source descriptor identity changed")
            named = os.stat(binding.path, follow_symlinks=False)
            if (named.st_dev, named.st_ino) != binding.identity[:2]:
                _fail("portable-checkpoint named source mapping changed")
            raw = _read_exact_fd(binding.source_fd, binding.identity[6])
            if hashlib.sha256(raw).hexdigest() != binding.sha256:
                _fail("portable-checkpoint source bytes changed")

    def close(self) -> None:
        if self.closed:
            return
        for binding in self.bindings:
            for descriptor in binding.descriptors:
                if descriptor < 0:
                    continue
                try:
                    os.close(descriptor)
                except OSError as error:
                    if error.errno != errno.EBADF:
                        raise
            binding.source_fd = -1
            binding.witness_fd = -1
        self.closed = True


def _source_specs() -> tuple[tuple[str, Path], ...]:
    candidates = (
        *tuple(_MODULE_PATH_BY_LABEL.items()),
        ("SUPERVISOR_EXEC_BIRTH_ASSEMBLY", _EXEC_SOURCE_PATH),
        ("SUPERVISOR_ROLE_NATIVE_SOURCE", _ROLE_SOURCE_PATH),
    )
    if len({role for role, _ in candidates}) != len(candidates):
        _fail("portable-checkpoint source roles are not unique")
    for _, path in candidates:
        try:
            path.relative_to(_REPOSITORY_ROOT)
        except ValueError:
            _fail("portable-checkpoint source escaped the repository")
    return candidates


def _freeze_source_closure() -> tuple[_SourceClosureLeaseV1, dict[str, Any]]:
    _validate_external_authorities()
    lease = _SourceClosureLeaseV1(_REPOSITORY_ROOT)
    try:
        for role, path in _source_specs():
            source_fd = os.open(path, os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW)
            witness_fd = -1
            try:
                status = os.fstat(source_fd)
                if not stat.S_ISREG(status.st_mode) or status.st_nlink < 1:
                    _fail("portable-checkpoint source is not one linked regular file")
                witness_fd = int(
                    fcntl.fcntl(source_fd, fcntl.F_DUPFD_CLOEXEC, 5)
                )
                identity = _fd_identity(source_fd)
                if _fd_identity(witness_fd) != identity:
                    _fail("portable-checkpoint source witness identity changed")
                raw = _read_exact_fd(source_fd, identity[6])
                lease.bindings.append(
                    _SourceBindingV1(
                        role=role,
                        relative_path=path.relative_to(_REPOSITORY_ROOT).as_posix(),
                        path=path,
                        source_fd=source_fd,
                        witness_fd=witness_fd,
                        identity=identity,
                        sha256=hashlib.sha256(raw).hexdigest(),
                        source_bytes=raw,
                    )
                )
                source_fd = witness_fd = -1
            finally:
                for descriptor in (source_fd, witness_fd):
                    if descriptor >= 0:
                        os.close(descriptor)
        lease.revalidate()
        payload = {
            "schema": "acfqp.k7_h1_two_birth_execution_source_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "readiness": READINESS,
            "freeze_phase": "BEFORE_RAW_TWO_BIRTH_BEGIN",
            "journal_sequence": 1,
            "previous_record_id": {
                "kind": "GENESIS",
                "reason": "PRIVATE_EMPTY_JOURNAL",
            },
            "source_entries": [binding.document() for binding in lease.bindings],
            "source_entry_count": len(lease.bindings),
            "callable_authority_bindings": [
                authority.document(_REPOSITORY_ROOT)
                for authority in _CALLABLE_AUTHORITIES
            ],
            "source_and_duplicate_witness_retained_until_root_commit": True,
            "source_descriptor_revalidation_required_after_root_commit": True,
            "source_closure_is_execution_authority": False,
            **_locked_claims(),
        }
        document = _content_document(
            domain=_SOURCE_CLOSURE_DOMAIN,
            id_field="two_birth_execution_source_closure_id",
            payload=payload,
        )
        return lease, document
    except BaseException:
        lease.close()
        raise


@dataclass(slots=True)
class _JournalRecordV1:
    sequence: int
    label: str
    record_id: str
    filename: str
    raw: bytes
    descriptor: int
    bytes_complete: bool = False
    file_fsync_complete: bool = False
    directory_fsync_complete: bool = False


class _PrivateAppendJournalV1:
    __slots__ = (
        "path",
        "directory_fd",
        "directory_identity",
        "records",
        "closed",
    )

    def __init__(self, path: Path) -> None:
        self.path = path
        self.directory_fd = -1
        self.directory_identity: tuple[int, int, int, int, int, int] | None = None
        self.records: list[_JournalRecordV1] = []
        self.closed = False
        self.directory_fd = os.open(
            path, os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW
        )
        status = os.fstat(self.directory_fd)
        named = os.stat(path, follow_symlinks=False)
        if (
            not stat.S_ISDIR(status.st_mode)
            or stat.S_IMODE(status.st_mode) != 0o700
            or status.st_uid != os.geteuid()
            or status.st_nlink < 2
            or (named.st_dev, named.st_ino) != (status.st_dev, status.st_ino)
            or os.listdir(self.directory_fd)
        ):
            self.close()
            _fail("portable-checkpoint journal must be caller-owned, private, and empty")
        # Directory extent changes on every append; only its stable inode,
        # ownership, mode, and link count belong to the pinned identity.
        self.directory_identity = _fd_identity(self.directory_fd)[:6]

    @property
    def descriptors(self) -> set[int]:
        return {
            self.directory_fd,
            *(record.descriptor for record in self.records),
        } - {-1}

    def _assert_current(self) -> None:
        if self.closed or self.directory_fd < 0 or self.directory_identity is None:
            _fail("portable-checkpoint journal is closed")
        named = os.stat(self.path, follow_symlinks=False)
        if (
            _fd_identity(self.directory_fd)[:6] != self.directory_identity
            or (named.st_dev, named.st_ino) != self.directory_identity[:2]
            or set(os.listdir(self.directory_fd))
            != {record.filename for record in self.records}
        ):
            _fail("portable-checkpoint journal mapping or inventory changed")
        for record in self.records:
            status = os.fstat(record.descriptor)
            named_record = os.stat(
                record.filename,
                dir_fd=self.directory_fd,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(status.st_mode)
                or stat.S_IMODE(status.st_mode) != 0o400
                or status.st_nlink != 1
                or (named_record.st_dev, named_record.st_ino)
                != (status.st_dev, status.st_ino)
                or (record.bytes_complete and _read_exact_fd(record.descriptor, len(record.raw)) != record.raw)
            ):
                _fail("portable-checkpoint retained journal record changed")

    def append(
        self,
        *,
        label: str,
        document: Mapping[str, Any],
        id_field: str,
        fault_after_file_fsync: str | None = None,
        fault_after_directory_fsync: str | None = None,
    ) -> _JournalRecordV1:
        _VALIDATE_INTERNAL_AUTHORITIES()
        self._assert_current()
        record_id = document.get(id_field)
        if type(record_id) is not str or len(record_id) != 64:
            _fail("portable-checkpoint journal record ID is malformed")
        sequence = len(self.records) + 1
        if document.get("journal_sequence") != sequence:
            _fail("portable-checkpoint journal sequence changed")
        previous = document.get("previous_record_id")
        if sequence == 1:
            if (
                type(previous) is not dict
                or previous.get("kind") != "GENESIS"
            ):
                _fail("portable-checkpoint journal genesis changed")
        elif previous != self.records[-1].record_id:
            _fail("portable-checkpoint journal previous-record chain changed")
        _validate_external_authorities()
        raw = _CANONICAL_JSON_BYTES(_thaw_json(document))
        filename = f"{sequence:06d}_{label}_{record_id}.json"
        descriptor = os.open(
            filename,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | _O_CLOEXEC | _O_NOFOLLOW,
            0o400,
            dir_fd=self.directory_fd,
        )
        record = _JournalRecordV1(
            sequence=sequence,
            label=label,
            record_id=record_id,
            filename=filename,
            raw=raw,
            descriptor=descriptor,
        )
        self.records.append(record)
        _exact_write(descriptor, raw)
        record.bytes_complete = True
        os.fsync(descriptor)
        record.file_fsync_complete = True
        if fault_after_file_fsync is not None:
            _test_fault(fault_after_file_fsync)
        status = os.fstat(descriptor)
        if (
            not stat.S_ISREG(status.st_mode)
            or stat.S_IMODE(status.st_mode) != 0o400
            or status.st_nlink != 1
            or status.st_size != len(raw)
            or _read_exact_fd(descriptor, len(raw)) != raw
        ):
            _fail("portable-checkpoint persisted record changed")
        os.fsync(self.directory_fd)
        record.directory_fsync_complete = True
        if fault_after_directory_fsync is not None:
            _test_fault(fault_after_directory_fsync)
        self._assert_current()
        return record

    def can_append_failure(self) -> bool:
        try:
            self._assert_current()
        except BaseException:
            return False
        return all(record.bytes_complete for record in self.records)

    def facts(self) -> list[dict[str, Any]]:
        return [
            {
                "sequence": record.sequence,
                "label": record.label,
                "record_id": record.record_id,
                "filename": record.filename,
                "byte_count": len(record.raw),
                "sha256": hashlib.sha256(record.raw).hexdigest(),
                "file_fsync_complete": record.file_fsync_complete,
                "directory_fsync_complete": record.directory_fsync_complete,
            }
            for record in self.records
        ]

    def close(self) -> None:
        if self.closed:
            return
        for record in self.records:
            if record.descriptor >= 0:
                try:
                    os.close(record.descriptor)
                except OSError as error:
                    if error.errno != errno.EBADF:
                        raise
                record.descriptor = -1
        if self.directory_fd >= 0:
            try:
                os.close(self.directory_fd)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise
            self.directory_fd = -1
        self.closed = True


_LIVE_OBSERVATION_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "readiness",
        "live_prefix_state_at_issuance",
        "guardian_identity",
        "control_cgroup_identity",
        "birth_order",
        "creator_by_role",
        "supervisor_pid",
        "supervisor_start_ticks",
        "probe_pid",
        "probe_start_ticks",
        "outer_pid_cell_value",
        "outer_parent_edge",
        "outer_nonce_hex",
        "outer_registered_expected_frames",
        "outer_receive_facts",
        "outer_pidfd_fact",
        "outer_seal_set",
        "outer_role_source_fact",
        "entry_empty_control_snapshots",
        "outer_supervisor_live_snapshots",
        "checkpoint_current_control_snapshots",
        "live_session_verification",
        "nested_probe_observed_facts_v2",
        "retained_descriptor_roles",
        "retained_live_descriptor_numbers_serialized",
        "historical_scm_rights_descriptor_number_observation_present",
        "historical_descriptor_numbers_are_not_resume_capability",
        "memory_peak_read_count",
        "supervisor_v1_only_accepts_shutdown_after_probe",
        "broker_launch_supported_by_live_process",
        "target_two_birth_creator_chain_observed",
        "exact_creator_reap_ownership_observed",
        "portable_observation_checkpoint_present",
        "durable_two_birth_artifact_graph_present",
        "portable_checkpoint_authority_present",
        "live_continuation_capability_portable",
        *tuple(_locked_claims()),
    }
)
_CGROUP_SNAPSHOT_KEYS = frozenset(
    {
        "sequence",
        "directory_device",
        "directory_inode",
        "first_cgroup_procs",
        "events",
        "pids_current",
        "second_cgroup_procs",
    }
)
_FRAME_KEYS = frozenset(
    {"opcode", "sequence", "nonce_hex", "pid", "status", "flags", "fact_a"}
)


def _require_cgroup_snapshots(
    rows: Any,
    *,
    sequences: tuple[int, int],
    expected_pids: tuple[int, ...],
    control_identity: tuple[int, int, int, int, int, int, int],
    label: str,
) -> None:
    if type(rows) is not list or len(rows) != 2:
        _fail(f"portable-checkpoint {label} inventory changed")
    expected = tuple(sorted(expected_pids))
    for row, sequence in zip(rows, sequences, strict=True):
        if (
            type(row) is not dict
            or frozenset(row) != _CGROUP_SNAPSHOT_KEYS
            or row.get("sequence") != sequence
            or row.get("directory_device") != control_identity[0]
            or row.get("directory_inode") != control_identity[1]
            or tuple(row.get("first_cgroup_procs", ())) != expected
            or tuple(row.get("second_cgroup_procs", ())) != expected
            or row.get("pids_current") != len(expected)
            or type(row.get("events")) is not dict
            or row["events"].get("populated") != int(bool(expected))
            or row["events"].get("frozen") != 0
        ):
            _fail(f"portable-checkpoint {label} join changed")


def _require_frame(
    value: Any,
    *,
    opcode: int,
    pid: int,
    nonce_hex: str,
    status: int = 0,
    flags: int = 0,
    fact_a: int = 0,
) -> None:
    if (
        type(value) is not dict
        or frozenset(value) != _FRAME_KEYS
        or value
        != {
            "opcode": opcode,
            "sequence": 1,
            "nonce_hex": nonce_hex,
            "pid": pid,
            "status": status,
            "flags": flags,
            "fact_a": fact_a,
        }
    ):
        _fail("portable-checkpoint nested frame join changed")


def _validate_live_observation(
    live_observation: Mapping[str, Any],
    *,
    control_identity: tuple[int, int, int, int, int, int, int],
) -> dict[str, Any]:
    _validate_external_authorities()
    observation = _thaw_json(live_observation)
    if type(observation) is not dict or frozenset(observation) != _LIVE_OBSERVATION_KEYS:
        _fail("portable-checkpoint live observation schema inventory changed")
    if (
        observation.get("schema")
        != "acfqp.k7_h1_two_birth_live_observation.v1"
        or observation.get("schema_version") != "1.0.0"
        or observation.get("profile_key") != _RUNTIME_PROFILE_KEY
        or observation.get("readiness") != _RUNTIME_READINESS
        or observation.get("live_prefix_state_at_issuance")
        != "PROBE_REAPED_SUPERVISOR_LIVE"
    ):
        _fail("portable-checkpoint live observation identity changed")
    for name, expected in _locked_claims().items():
        if observation.get(name) != expected:
            _fail("portable-checkpoint live observation negative lock changed")
    guardian = observation.get("guardian_identity")
    cgroup = observation.get("control_cgroup_identity")
    if (
        type(guardian) is not dict
        or frozenset(guardian)
        != {"pid", "process_start_ticks", "thread_id", "native_thread_id"}
        or guardian.get("pid") != os.getpid()
        or guardian.get("thread_id") != threading.get_ident()
        or guardian.get("native_thread_id") != threading.get_native_id()
        or type(guardian.get("process_start_ticks")) is not int
        or guardian["process_start_ticks"] <= 0
        or type(cgroup) is not dict
        or frozenset(cgroup) != {"device", "inode", "mode"}
        or cgroup
        != {
            "device": control_identity[0],
            "inode": control_identity[1],
            "mode": control_identity[2],
        }
    ):
        _fail("portable-checkpoint guardian or CONTROL identity changed")
    supervisor = observation.get("supervisor_pid")
    supervisor_start = observation.get("supervisor_start_ticks")
    probe = observation.get("probe_pid")
    probe_start = observation.get("probe_start_ticks")
    if (
        type(supervisor) is not int
        or supervisor <= 0
        or type(supervisor_start) is not int
        or supervisor_start <= 0
        or type(probe) is not int
        or probe <= 0
        or probe == supervisor
        or type(probe_start) is not int
        or probe_start <= 0
        or observation.get("birth_order") != ["SUPERVISOR", "PIDFD_PROBE"]
        or observation.get("creator_by_role")
        != {"SUPERVISOR": "GUARDIAN", "PIDFD_PROBE": "SUPERVISOR"}
        or observation.get("outer_pid_cell_value") != supervisor
    ):
        _fail("portable-checkpoint two-birth identity join changed")
    parent = observation.get("outer_parent_edge")
    pidfd = observation.get("outer_pidfd_fact")
    role_source = observation.get("outer_role_source_fact")
    if (
        type(parent) is not dict
        or parent
        != {
            "clone_result": supervisor,
            "status_bits": _PARENT_REQUIRED_SUCCESS_BITS,
            "first_cleanup_error": 0,
            "reserved_zero": 0,
        }
        or type(pidfd) is not dict
        or frozenset(pidfd) != {"pid", "nspid", "device", "inode"}
        or pidfd.get("pid") != supervisor
        or type(pidfd.get("nspid")) is not int
        or pidfd["nspid"] <= 0
        or type(role_source) is not dict
        or role_source.get("elf_sha256") != _ROLE_ELF_SHA256
        or role_source.get("elf_byte_count") != _ROLE_ELF_BYTE_COUNT
        or role_source.get("source_device") != role_source.get("witness_device")
        or role_source.get("source_inode") != role_source.get("witness_inode")
        or role_source.get("source_witness_same_identity") is not True
        or observation.get("outer_seal_set") != _REQUIRED_SEALS
    ):
        _fail("portable-checkpoint outer birth evidence join changed")
    nonce_hex = observation.get("outer_nonce_hex")
    if (
        type(nonce_hex) is not str
        or len(nonce_hex) != 32
        or any(character not in "0123456789abcdef" for character in nonce_hex)
    ):
        _fail("portable-checkpoint outer nonce changed")
    registered = observation.get("outer_registered_expected_frames")
    received = observation.get("outer_receive_facts")
    expected_frames = (
        ("CELL_WITHDRAWN", b"ACFQP:EXEC_CELL_WITHDRAWN:v1:"),
        ("GATE_READY", b"ACFQP:EXEC_GATE_READY:v1:"),
        ("RELEASE_ECHO", b"ACFQP:EXEC_RELEASE:v1:"),
    )
    if type(registered) is not list or type(received) is not list:
        _fail("portable-checkpoint outer gate inventory changed")
    if len(registered) != 3 or len(received) != 3:
        _fail("portable-checkpoint outer gate count changed")
    for expected, register, receive in zip(
        expected_frames, registered, received, strict=True
    ):
        kind, prefix = expected
        raw = prefix + nonce_hex.encode("ascii")
        digest = hashlib.sha256(raw).hexdigest()
        if (
            type(register) is not dict
            or register
            != {
                "kind": kind,
                "payload_hex": raw.hex(),
                "sha256": digest,
                "byte_count": len(raw),
            }
            or type(receive) is not dict
            or receive.get("kind") != kind
            or receive.get("sha256") != digest
            or receive.get("byte_count") != len(raw)
            or receive.get("credential_pid") != supervisor
            or receive.get("credential_uid") != os.getuid()
            or receive.get("credential_gid") != os.getgid()
            or type(receive.get("message_flags")) is not int
        ):
            _fail("portable-checkpoint outer gate credential join changed")
    _require_cgroup_snapshots(
        observation.get("entry_empty_control_snapshots"),
        sequences=(7000, 7001),
        expected_pids=(),
        control_identity=control_identity,
        label="entry CONTROL snapshots",
    )
    _require_cgroup_snapshots(
        observation.get("outer_supervisor_live_snapshots"),
        sequences=(1, 2),
        expected_pids=(supervisor,),
        control_identity=control_identity,
        label="outer live CONTROL snapshots",
    )
    _require_cgroup_snapshots(
        observation.get("checkpoint_current_control_snapshots"),
        sequences=(8000, 8001),
        expected_pids=(supervisor,),
        control_identity=control_identity,
        label="current CONTROL snapshots",
    )
    session = observation.get("live_session_verification")
    if (
        type(session) is not dict
        or session.get("profile_key") != _PROBE_PROFILE_KEY
        or session.get("session_state") != "PROBE_REAPED_SUPERVISOR_LIVE"
        or session.get("supervisor_pid") != supervisor
        or session.get("supervisor_start_ticks") != supervisor_start
        or session.get("supervisor_pidfd_fact", {}).get("pid") != supervisor
        or session.get("supervisor_pidfd_cloexec") is not True
        or session.get("owner_pid") != os.getpid()
        or session.get("owner_thread_id") != threading.get_ident()
        or session.get("active_probe_pid") != -1
        or session.get("live_session_verified") is not True
        or session.get("verification_mutated_session") is not False
        or session.get("control_socket_fact", {})
        .get("peer_credentials", {})
        .get("pid")
        != os.getpid()
        or session.get("control_socket_fact", {})
        .get("peer_credentials", {})
        .get("uid")
        != os.getuid()
        or session.get("control_socket_fact", {})
        .get("peer_credentials", {})
        .get("gid")
        != os.getgid()
    ):
        _fail("portable-checkpoint live-session join changed")
    nested = observation.get("nested_probe_observed_facts_v2")
    if (
        type(nested) is not dict
        or frozenset(nested)
        != {
            "schema",
            "schema_version",
            "profile_key",
            "raw_facts_v1",
            "supervisor_ready_observation",
            "protocol_receive_observations",
            "nested_receive_credential_observations_present",
            "nested_receive_rights_observations_present",
            "portable_checkpoint_authority_present",
            "two_birth_prefix_authority_present",
            "official_execution_allowed",
        }
        or nested.get("schema")
        != "acfqp.k7_h1_nested_creator_probe_observed_facts.v2"
        or nested.get("schema_version") != "2.0.0"
        or nested.get("profile_key")
        != "construction_k7_h1_nested_creator_probe_observed_v2"
        or nested.get("nested_receive_credential_observations_present") is not True
        or nested.get("nested_receive_rights_observations_present") is not True
        or nested.get("portable_checkpoint_authority_present") is not False
        or nested.get("two_birth_prefix_authority_present") is not False
        or nested.get("official_execution_allowed") is not False
    ):
        _fail("portable-checkpoint nested V2 identity changed")
    raw_facts = nested.get("raw_facts_v1")
    if (
        type(raw_facts) is not dict
        or raw_facts.get("schema")
        != "acfqp.k7_h1_nested_creator_probe_raw_facts.v1"
        or raw_facts.get("schema_version") != "1.0.0"
        or raw_facts.get("profile_key") != _PROBE_PROFILE_KEY
        or raw_facts.get("supervisor_pid") != supervisor
        or raw_facts.get("supervisor_start_ticks") != supervisor_start
        or raw_facts.get("probe_pid") != probe
        or raw_facts.get("probe_start_ticks") != probe_start
        or raw_facts.get("pid_cell_value") != probe
        or raw_facts.get("pidfd_fact", {}).get("pid") != probe
        or raw_facts.get("guardian_waitid_errno") != errno.ECHILD
        or raw_facts.get("actual_nested_pidfd_probe_birth_present") is not True
        or raw_facts.get("actual_non_guardian_creator_reap_present") is not True
        or raw_facts.get("guardian_independent_pid_cell_pidfd_cgroup_join_present")
        is not True
        or raw_facts.get("gated_supervisor_birth_authority_present") is not False
        or raw_facts.get("two_birth_prefix_authority_present") is not False
        or raw_facts.get("five_birth_process_authority_present") is not False
        or raw_facts.get("production_shared_resource_receipts_present") is not False
        or raw_facts.get("official_execution_allowed") is not False
    ):
        _fail("portable-checkpoint nested raw-facts join changed")
    nested_nonce = raw_facts.get("nonce_hex")
    if type(nested_nonce) is not str or len(nested_nonce) != 32:
        _fail("portable-checkpoint nested nonce changed")
    _require_frame(
        raw_facts.get("parent_return_frame"),
        opcode=_ROLE_OPCODES["PROBE_PARENT_RETURN"],
        pid=probe,
        nonce_hex=nested_nonce,
        flags=0x1F,
        fact_a=supervisor,
    )
    _require_frame(
        raw_facts.get("child_withdrawn_frame"),
        opcode=_ROLE_OPCODES["CHILD_CELL_WITHDRAWN"],
        pid=probe,
        nonce_hex=nested_nonce,
    )
    _require_frame(
        raw_facts.get("child_ready_frame"),
        opcode=_ROLE_OPCODES["CHILD_GATE_READY"],
        pid=probe,
        nonce_hex=nested_nonce,
    )
    _require_frame(
        raw_facts.get("child_release_echo_frame"),
        opcode=_ROLE_OPCODES["CHILD_RELEASE_ECHO"],
        pid=probe,
        nonce_hex=nested_nonce,
    )
    _require_frame(
        raw_facts.get("creator_reap_frame"),
        opcode=_ROLE_OPCODES["PROBE_REAP"],
        pid=probe,
        nonce_hex=nested_nonce,
        flags=1,
        fact_a=errno.ECHILD,
    )
    _require_cgroup_snapshots(
        raw_facts.get("live_cgroup_snapshots"),
        sequences=(1, 2),
        expected_pids=(supervisor, probe),
        control_identity=control_identity,
        label="nested live CONTROL snapshots",
    )
    _require_cgroup_snapshots(
        raw_facts.get("post_reap_cgroup_snapshots"),
        sequences=(3, 4),
        expected_pids=(supervisor,),
        control_identity=control_identity,
        label="nested post-reap CONTROL snapshots",
    )
    observations = nested.get("protocol_receive_observations")
    expected_opcodes = (
        _ROLE_OPCODES["PROBE_PARENT_RETURN"],
        _ROLE_OPCODES["CHILD_CELL_WITHDRAWN"],
        _ROLE_OPCODES["CHILD_GATE_READY"],
        _ROLE_OPCODES["CHILD_RELEASE_ECHO"],
        _ROLE_OPCODES["PROBE_REAP"],
    )
    expected_credentials = (supervisor, probe, probe, probe, supervisor)
    expected_rights = (1, 0, 0, 0, 0)
    if type(observations) is not list or len(observations) != 5:
        _fail("portable-checkpoint nested observation count changed")
    for index, (item, opcode, credential_pid, rights_count) in enumerate(
        zip(
            observations,
            expected_opcodes,
            expected_credentials,
            expected_rights,
            strict=True,
        )
    ):
        if type(item) is not dict:
            _fail("portable-checkpoint nested observation type changed")
        raw_payload_hex = item.get("raw_payload_hex")
        try:
            raw_payload = bytes.fromhex(raw_payload_hex)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1TwoBirthPortableCheckpointV1Error(
                "portable-checkpoint nested observation bytes changed"
            ) from error
        installed = item.get("installed_pidfd_facts")
        if (
            item.get("event_index") != index
            or item.get("opcode") != opcode
            or item.get("decoded_frame", {}).get("opcode") != opcode
            or item.get("decoded_frame", {}).get("pid") != item.get("frame_pid")
            or item.get("credentials")
            != {"pid": credential_pid, "uid": os.getuid(), "gid": os.getgid()}
            or item.get("rights_count") != rights_count
            or type(installed) is not list
            or len(installed) != rights_count
            or item.get("payload_byte_count") != len(raw_payload)
            or item.get("payload_sha256")
            != hashlib.sha256(raw_payload).hexdigest()
            or (
                rights_count == 1
                and (
                    installed[0].get("pid") != probe
                    or installed[0].get("cloexec") is not True
                )
            )
        ):
            _fail("portable-checkpoint nested credential/right join changed")
    ready = nested.get("supervisor_ready_observation")
    if (
        type(ready) is not dict
        or ready.get("opcode") != _ROLE_OPCODES["SUPERVISOR_READY"]
        or ready.get("frame_pid") != supervisor
        or ready.get("credentials")
        != {"pid": supervisor, "uid": os.getuid(), "gid": os.getgid()}
        or ready.get("rights_count") != 0
    ):
        _fail("portable-checkpoint supervisor-ready credential join changed")
    if (
        observation.get("retained_descriptor_roles")
        != ["CONTROL_CGROUP", "SUPERVISOR_CONTROL_SOCKET", "SUPERVISOR_PIDFD"]
        or observation.get("retained_live_descriptor_numbers_serialized")
        is not False
        or observation.get(
            "historical_scm_rights_descriptor_number_observation_present"
        )
        is not True
        or observation.get(
            "historical_descriptor_numbers_are_not_resume_capability"
        )
        is not True
        or observation.get("memory_peak_read_count") != 0
        or observation.get("supervisor_v1_only_accepts_shutdown_after_probe")
        is not True
        or observation.get("broker_launch_supported_by_live_process") is not False
        or observation.get("target_two_birth_creator_chain_observed") is not True
        or observation.get("exact_creator_reap_ownership_observed") is not True
        or observation.get("portable_observation_checkpoint_present") is not False
        or observation.get("durable_two_birth_artifact_graph_present") is not False
        or observation.get("live_continuation_capability_portable") is not False
    ):
        _fail("portable-checkpoint raw observation scope locks changed")
    return observation


def _verify_domain_document(
    value: Mapping[str, Any],
    *,
    domain: str,
    id_field: str,
    label: str,
) -> dict[str, Any]:
    document = _thaw_json(value)
    if type(document) is not dict:
        _fail(f"portable-checkpoint {label} is not one exact object")
    payload = dict(document)
    supplied = payload.pop(id_field, None)
    if (
        type(supplied) is not str
        or len(supplied) != 64
        or _V18_CONTENT_ID(domain, payload) != supplied
    ):
        _fail(f"portable-checkpoint {label} content ID changed")
    return document


def _validate_source_closure_document(
    source_closure: Mapping[str, Any],
) -> dict[str, Any]:
    document = _verify_domain_document(
        source_closure,
        domain=_SOURCE_CLOSURE_DOMAIN,
        id_field="two_birth_execution_source_closure_id",
        label="execution source closure",
    )
    entries = document.get("source_entries")
    if (
        frozenset(document)
        != {
            "schema",
            "schema_version",
            "profile_key",
            "readiness",
            "freeze_phase",
            "journal_sequence",
            "previous_record_id",
            "source_entries",
            "source_entry_count",
            "callable_authority_bindings",
            "source_and_duplicate_witness_retained_until_root_commit",
            "source_descriptor_revalidation_required_after_root_commit",
            "source_closure_is_execution_authority",
            "two_birth_execution_source_closure_id",
            *tuple(_locked_claims()),
        }
        or document.get("schema")
        != "acfqp.k7_h1_two_birth_execution_source_closure.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("readiness") != READINESS
        or document.get("freeze_phase") != "BEFORE_RAW_TWO_BIRTH_BEGIN"
        or document.get("journal_sequence") != 1
        or document.get("previous_record_id")
        != {"kind": "GENESIS", "reason": "PRIVATE_EMPTY_JOURNAL"}
        or type(entries) is not list
        or document.get("source_entry_count") != len(_source_specs())
        or len(entries) != len(_source_specs())
        or document.get("source_closure_is_execution_authority") is not False
    ):
        _fail("portable-checkpoint execution source closure schema changed")
    expected_roles = [role for role, _ in _source_specs()]
    if [entry.get("role") for entry in entries] != expected_roles:
        _fail("portable-checkpoint execution source role order changed")
    expected_callable_documents = [
        authority.document(_REPOSITORY_ROOT)
        for authority in _CALLABLE_AUTHORITIES
    ]
    if document.get("callable_authority_bindings") != expected_callable_documents:
        _fail("portable-checkpoint callable authority manifest changed")
    for entry, (expected_role, expected_path) in zip(
        entries, _source_specs(), strict=True
    ):
        if type(entry) is not dict:
            _fail("portable-checkpoint execution source entry changed")
        descriptor = os.open(
            expected_path, os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW
        )
        try:
            status = os.fstat(descriptor)
            current_raw = _read_exact_fd(descriptor, status.st_size)
        finally:
            os.close(descriptor)
        try:
            raw = bytes.fromhex(entry.get("source_bytes_hex"))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1TwoBirthPortableCheckpointV1Error(
                "portable-checkpoint embedded source bytes changed"
            ) from error
        if (
            entry.get("role") != expected_role
            or entry.get("repository_relative_path")
            != expected_path.relative_to(_REPOSITORY_ROOT).as_posix()
            or entry.get("device") != status.st_dev
            or entry.get("inode") != status.st_ino
            or entry.get("mode") != status.st_mode
            or entry.get("uid") != status.st_uid
            or entry.get("gid") != status.st_gid
            or entry.get("link_count") != status.st_nlink
            or raw != current_raw
            or entry.get("byte_count") != len(raw)
            or entry.get("sha256") != hashlib.sha256(raw).hexdigest()
            or entry.get("source_and_witness_same_inode") is not True
            or entry.get("source_descriptor_cloexec") is not True
            or entry.get("witness_descriptor_cloexec") is not True
            or entry.get("descriptor_numbers_serialized") is not False
            or entry.get("absolute_path_serialized") is not False
        ):
            _fail("portable-checkpoint embedded source join changed")
    for name, expected in _locked_claims().items():
        if document.get(name) != expected:
            _fail("portable-checkpoint source negative lock changed")
    return document


def _credential_bundle(
    *,
    source_closure: Mapping[str, Any],
    live_observation: Mapping[str, Any],
    control_identity: tuple[int, int, int, int, int, int, int],
) -> dict[str, Any]:
    source = _validate_source_closure_document(source_closure)
    observation = _validate_live_observation(
        live_observation, control_identity=control_identity
    )
    payload = {
        "schema": "acfqp.k7_h1_nested_probe_credential_observation_bundle.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "two_birth_execution_source_closure_id": source[
            "two_birth_execution_source_closure_id"
        ],
        "journal_sequence": 2,
        "previous_record_id": source[
            "two_birth_execution_source_closure_id"
        ],
        "guardian_identity": observation["guardian_identity"],
        "control_cgroup_identity": observation["control_cgroup_identity"],
        "supervisor_pid": observation["supervisor_pid"],
        "supervisor_start_ticks": observation["supervisor_start_ticks"],
        "probe_pid": observation["probe_pid"],
        "probe_start_ticks": observation["probe_start_ticks"],
        "outer_registered_expected_frames": observation[
            "outer_registered_expected_frames"
        ],
        "outer_receive_facts": observation["outer_receive_facts"],
        "nested_probe_observed_facts_v2": observation[
            "nested_probe_observed_facts_v2"
        ],
        "nested_receive_credential_observations_present": True,
        "nested_receive_rights_observations_present": True,
        "credential_observations_are_not_lease_authority": True,
        **_locked_claims(),
    }
    return _content_document(
        domain=_CREDENTIAL_BUNDLE_DOMAIN,
        id_field="nested_probe_credential_observation_bundle_id",
        payload=payload,
    )


def _validate_credential_bundle_document(
    credential_bundle: Mapping[str, Any],
    *,
    source_closure: Mapping[str, Any],
    live_observation: Mapping[str, Any],
    control_identity: tuple[int, int, int, int, int, int, int],
) -> dict[str, Any]:
    source = _validate_source_closure_document(source_closure)
    observation = _validate_live_observation(
        live_observation, control_identity=control_identity
    )
    document = _verify_domain_document(
        credential_bundle,
        domain=_CREDENTIAL_BUNDLE_DOMAIN,
        id_field="nested_probe_credential_observation_bundle_id",
        label="credential observation bundle",
    )
    if (
        frozenset(document)
        != {
            "schema",
            "schema_version",
            "profile_key",
            "readiness",
            "two_birth_execution_source_closure_id",
            "journal_sequence",
            "previous_record_id",
            "guardian_identity",
            "control_cgroup_identity",
            "supervisor_pid",
            "supervisor_start_ticks",
            "probe_pid",
            "probe_start_ticks",
            "outer_registered_expected_frames",
            "outer_receive_facts",
            "nested_probe_observed_facts_v2",
            "nested_receive_credential_observations_present",
            "nested_receive_rights_observations_present",
            "credential_observations_are_not_lease_authority",
            "nested_probe_credential_observation_bundle_id",
            *tuple(_locked_claims()),
        }
        or document.get("schema")
        != "acfqp.k7_h1_nested_probe_credential_observation_bundle.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("readiness") != READINESS
        or document.get("two_birth_execution_source_closure_id")
        != source["two_birth_execution_source_closure_id"]
        or document.get("journal_sequence") != 2
        or document.get("previous_record_id")
        != source["two_birth_execution_source_closure_id"]
        or document.get("guardian_identity") != observation["guardian_identity"]
        or document.get("control_cgroup_identity")
        != observation["control_cgroup_identity"]
        or document.get("supervisor_pid") != observation["supervisor_pid"]
        or document.get("supervisor_start_ticks")
        != observation["supervisor_start_ticks"]
        or document.get("probe_pid") != observation["probe_pid"]
        or document.get("probe_start_ticks") != observation["probe_start_ticks"]
        or document.get("outer_registered_expected_frames")
        != observation["outer_registered_expected_frames"]
        or document.get("outer_receive_facts")
        != observation["outer_receive_facts"]
        or document.get("nested_probe_observed_facts_v2")
        != observation["nested_probe_observed_facts_v2"]
        or document.get("nested_receive_credential_observations_present")
        is not True
        or document.get("nested_receive_rights_observations_present") is not True
        or document.get("credential_observations_are_not_lease_authority")
        is not True
    ):
        _fail("portable-checkpoint credential observation bundle join changed")
    for name, expected in _locked_claims().items():
        if document.get(name) != expected:
            _fail("portable-checkpoint credential negative lock changed")
    return document


def _root_checkpoint(
    *,
    source_closure: Mapping[str, Any],
    credential_bundle: Mapping[str, Any],
    live_observation: Mapping[str, Any],
    control_identity: tuple[int, int, int, int, int, int, int],
) -> dict[str, Any]:
    source = _validate_source_closure_document(source_closure)
    observation = _validate_live_observation(
        live_observation, control_identity=control_identity
    )
    credentials = _validate_credential_bundle_document(
        credential_bundle,
        source_closure=source,
        live_observation=observation,
        control_identity=control_identity,
    )
    if observation["live_prefix_state_at_issuance"] != "PROBE_REAPED_SUPERVISOR_LIVE":
        _fail("portable-checkpoint observation was not issued at the live cut")
    payload = {
        "schema": "acfqp.k7_h1_live_two_birth_prefix_checkpoint.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "issuance_state": "PROBE_REAPED_SUPERVISOR_LIVE",
        "runtime_state_at_root_commit": "PROBE_REAPED_SUPERVISOR_LIVE",
        "expected_success_return_runtime_state": "CLOSED",
        "producer_success_return_not_yet_observed": True,
        "producer_protocol_after_checkpoint": "V1_SHUTDOWN_ONLY",
        "journal_sequence": 3,
        "previous_record_id": credentials[
            "nested_probe_credential_observation_bundle_id"
        ],
        "checkpoint_durable_before_runtime_shutdown": True,
        "execution_source_closure": source,
        "credential_observation_bundle": credentials,
        "live_observation": observation,
        "root_embeds_complete_child_documents": True,
        "two_birth_execution_source_closure_id": source[
            "two_birth_execution_source_closure_id"
        ],
        "nested_probe_credential_observation_bundle_id": credentials[
            "nested_probe_credential_observation_bundle_id"
        ],
        "portable_observation_checkpoint_present": True,
        "durable_portable_observation_graph_present": True,
        "checkpoint_bytes_describe_historical_live_observation": True,
        "checkpoint_bytes_encode_resume_capability": False,
        "live_continuation_capability_portable": False,
        **_locked_claims(),
    }
    return _content_document(
        domain=_LIVE_CHECKPOINT_DOMAIN,
        id_field="live_two_birth_prefix_checkpoint_id",
        payload=payload,
    )


def _cleanup_raw_runtime(
    *,
    handle: runtime_v1.BoundedNestedCreatorTwoBirthLivePrefixV1 | None,
    control_cgroup_fd: int,
    baseline_ambient_fds: Mapping[int, tuple[int, int, int]],
    producer_descriptors: set[int],
    baseline_subreaper: bool,
) -> dict[str, Any]:
    terminal_method = "NO_HANDLE_RUNTIME_ALREADY_CLOSED"
    terminal_document: Mapping[str, Any] | None = None
    recovery_document: Mapping[str, Any] | None = None
    if handle is not None:
        state = handle.state
        if state == "PROBE_REAPED_SUPERVISOR_LIVE":
            _validate_external_authorities()
            terminal_document = _RUNTIME_ABORT(handle)
            terminal_method = "PUBLIC_ABORT"
        elif state == "CLOSED":
            terminal_method = "PUBLIC_NORMAL_CLOSE_ALREADY_COMMITTED"
        elif state == "ABORTED_CLOSED":
            terminal_method = "PUBLIC_ABORT_ALREADY_COMMITTED"
        else:
            _fail("portable-checkpoint raw handle entered an unclosed state")
    else:
        try:
            _validate_external_authorities()
            recovery_document = _RUNTIME_BEGIN_FAILURE_RECOVERY()
            terminal_method = "PUBLIC_BEGIN_FAILURE_RECOVERY"
        except _RUNTIME_ERROR_TYPE as error:
            if "begin failure quarantine is absent" not in str(error):
                raise
    _validate_external_authorities()
    empty_one = _OBSERVE_CONTROL_POPULATION(
        control_cgroup_fd, expected_pids=(), sequence=18001
    )
    empty_two = _OBSERVE_CONTROL_POPULATION(
        control_cgroup_fd, expected_pids=(), sequence=18002
    )
    direct_children = _direct_children()
    current_ambient = _open_fd_identities(exclude=producer_descriptors)
    subreaper = _get_subreaper()
    if (
        direct_children
        or current_ambient != dict(baseline_ambient_fds)
        or subreaper is not baseline_subreaper
    ):
        _fail("portable-checkpoint raw cleanup did not restore guardian state")
    return {
        "raw_cleanup_completely_closed": True,
        "terminal_method": terminal_method,
        "terminal_document": (
            _thaw_json(terminal_document)
            if terminal_document is not None
            else {"kind": "NOT_APPLICABLE", "reason": "NO_ABORT_RESULT"}
        ),
        "begin_failure_recovery_document": (
            _thaw_json(recovery_document)
            if recovery_document is not None
            else {"kind": "NOT_APPLICABLE", "reason": "NO_QUARANTINE"}
        ),
        "empty_control_snapshots": [dict(empty_one), dict(empty_two)],
        "direct_children_after_cleanup": [],
        "ambient_fd_inventory_restored": True,
        "subreaper_state_restored": True,
    }


def _failure_closure(
    *,
    source_closure: Mapping[str, Any] | None,
    journal: _PrivateAppendJournalV1,
    cleanup: Mapping[str, Any],
    error: BaseException,
    raw_begin_returned: bool,
) -> dict[str, Any]:
    source = (
        _thaw_json(source_closure)
        if source_closure is not None
        else {"kind": "NOT_AVAILABLE", "reason": "SOURCE_FREEZE_DID_NOT_COMPLETE"}
    )
    payload = {
        "schema": "acfqp.k7_h1_two_birth_protocol_failure_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "source_closure": source,
        "journal_sequence": len(journal.records) + 1,
        "previous_record_id": (
            journal.records[-1].record_id
            if journal.records
            else {"kind": "GENESIS", "reason": "NO_PREDECESSOR_RECORD"}
        ),
        "raw_begin_returned": raw_begin_returned,
        "failure_type": type(error).__name__,
        "failure_message": str(error),
        "cleanup": _thaw_json(cleanup),
        "journal_records_before_failure_closure": journal.facts(),
        "failure_closure_is_not_infeasibility": True,
        "failure_closure_is_not_plan_certificate": True,
        **_locked_claims(),
    }
    return _content_document(
        domain=_FAILURE_CLOSURE_DOMAIN,
        id_field="two_birth_protocol_failure_closure_id",
        payload=payload,
    )


_INTERNAL_CALLABLE_AUTHORITIES = tuple(
    (name, function, function.__code__)
    for name, function in (
        ("_fingerprint_canonical_json_bytes", _fingerprint_canonical_json_bytes),
        ("_semantic_value_document", _semantic_value_document),
        ("_code_fingerprint_document", _code_fingerprint_document),
        ("_callable_semantic_documents", _callable_semantic_documents),
        ("_validate_external_authorities", _validate_external_authorities),
        ("_content_document", _content_document),
        ("_freeze_source_closure", _freeze_source_closure),
        ("_validate_live_observation", _validate_live_observation),
        ("_credential_bundle", _credential_bundle),
        ("_root_checkpoint", _root_checkpoint),
        ("_failure_closure", _failure_closure),
        ("_PrivateAppendJournalV1.append", _PrivateAppendJournalV1.append),
    )
)


def _validate_internal_authorities() -> None:
    for name, function, code in _INTERNAL_CALLABLE_AUTHORITIES:
        if name == "_PrivateAppendJournalV1.append":
            current = _PrivateAppendJournalV1.append
        else:
            current = globals().get(name)
        if current is not function or getattr(current, "__code__", None) is not code:
            _fail("portable-checkpoint internal callable authority changed")


_VALIDATE_INTERNAL_AUTHORITIES = _validate_internal_authorities
_FROZEN_CREDENTIAL_BUNDLE = _credential_bundle
_FROZEN_ROOT_CHECKPOINT = _root_checkpoint
_FROZEN_FAILURE_CLOSURE = _failure_closure


@dataclass(frozen=True, slots=True)
class TwoBirthPortableCheckpointGraphV1:
    source_closure: Mapping[str, Any]
    credential_bundle: Mapping[str, Any]
    live_checkpoint: Mapping[str, Any]
    shutdown_result: Mapping[str, Any]
    journal_records: tuple[Mapping[str, Any], ...]
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("portable-checkpoint graph is caller-minted")
        for name in (
            "source_closure",
            "credential_bundle",
            "live_checkpoint",
            "shutdown_result",
            "journal_records",
        ):
            object.__setattr__(self, name, _freeze_json(getattr(self, name)))

    def __copy__(self) -> NoReturn:
        _fail("portable-checkpoint graph cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("portable-checkpoint graph cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("portable-checkpoint graph cannot be pickled")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_two_birth_portable_checkpoint_graph.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "readiness": READINESS,
            "source_closure": _thaw_json(self.source_closure),
            "credential_bundle": _thaw_json(self.credential_bundle),
            "live_checkpoint": _thaw_json(self.live_checkpoint),
            "shutdown_result": _thaw_json(self.shutdown_result),
            "journal_records": _thaw_json(self.journal_records),
            "issuance_state": "PROBE_REAPED_SUPERVISOR_LIVE",
            "producer_return_runtime_state": "CLOSED",
            "portable_checkpoint_authority_present": False,
            **_locked_claims(),
        }


def run_two_birth_portable_checkpoint_producer_v1(
    *,
    control_cgroup_fd: int,
    journal_directory: Path | str,
) -> TwoBirthPortableCheckpointGraphV1:
    """Persist one non-authoritative live observation, then shut down V1.

    ``control_cgroup_fd`` remains caller-owned.  The journal directory must
    already exist, be owned by the effective user, have mode ``0700``, and be
    empty.  A successful return means the root was durable before shutdown and
    that the raw runtime has since reached ``CLOSED``.
    """

    if type(control_cgroup_fd) is not int or control_cgroup_fd < 0:
        _fail("portable-checkpoint CONTROL descriptor is invalid")
    control_identity = _fd_identity(control_cgroup_fd)
    if not stat.S_ISDIR(control_identity[2]):
        _fail("portable-checkpoint CONTROL descriptor is not a directory")
    path = Path(os.path.abspath(os.fspath(journal_directory)))
    source_lease: _SourceClosureLeaseV1 | None = None
    source_closure: dict[str, Any] | None = None
    journal: _PrivateAppendJournalV1 | None = None
    handle: runtime_v1.BoundedNestedCreatorTwoBirthLivePrefixV1 | None = None
    baseline_ambient_fds: dict[int, tuple[int, int, int]] = {}
    baseline_subreaper = False
    original_error: BaseException | None = None
    failure_closure: dict[str, Any] | None = None

    with _PRODUCER_LOCK:
        try:
            _validate_external_authorities()
            _VALIDATE_INTERNAL_AUTHORITIES()
            journal = _PrivateAppendJournalV1(path)
            baseline_ambient_fds = _open_fd_identities(
                exclude=journal.descriptors
            )
            baseline_subreaper = _get_subreaper()
            if _direct_children():
                _fail("portable-checkpoint guardian already owns a direct child")
            source_lease, source_closure = _freeze_source_closure()
            _test_fault("SOURCE_CLOSURE_FROZEN")

            _validate_external_authorities()
            handle = _RUNTIME_BEGIN(
                control_cgroup_fd=control_cgroup_fd
            )
            _test_fault("RAW_BEGIN_RETURNED")
            _validate_external_authorities()
            live_observation = (
                _RUNTIME_SNAPSHOT(handle)
            )
            _test_fault("LIVE_SNAPSHOT_FROZEN")
            credentials = _FROZEN_CREDENTIAL_BUNDLE(
                source_closure=source_closure,
                live_observation=live_observation,
                control_identity=control_identity,
            )
            checkpoint = _FROZEN_ROOT_CHECKPOINT(
                source_closure=source_closure,
                credential_bundle=credentials,
                live_observation=live_observation,
                control_identity=control_identity,
            )

            source_lease.revalidate()
            journal.append(
                label="EXECUTION_SOURCE_CLOSURE",
                document=source_closure,
                id_field="two_birth_execution_source_closure_id",
                fault_after_file_fsync="SOURCE_RECORD_FILE_FSYNC",
            )
            source_lease.revalidate()
            journal.append(
                label="CREDENTIAL_OBSERVATION_BUNDLE",
                document=credentials,
                id_field="nested_probe_credential_observation_bundle_id",
                fault_after_file_fsync="CREDENTIAL_RECORD_FILE_FSYNC",
            )
            source_lease.revalidate()
            journal.append(
                label="LIVE_PREFIX_CHECKPOINT",
                document=checkpoint,
                id_field="live_two_birth_prefix_checkpoint_id",
                fault_after_file_fsync="CHECKPOINT_RECORD_FILE_FSYNC",
                fault_after_directory_fsync="CHECKPOINT_RECORD_DIRECTORY_FSYNC",
            )
            source_lease.revalidate()
            _test_fault("ROOT_DURABLE_COMMIT")
            source_lease.close()

            _validate_external_authorities()
            shutdown = _RUNTIME_CLOSE(handle)
            shutdown_document = shutdown.to_document()
            if handle.state != "CLOSED":
                _fail("portable-checkpoint producer did not reach CLOSED")
            _test_fault("RUNTIME_CLOSED")
            if _fd_identity(control_cgroup_fd) != control_identity:
                _fail("portable-checkpoint caller CONTROL descriptor changed")
            if _direct_children() or _get_subreaper() is not baseline_subreaper:
                _fail("portable-checkpoint successful shutdown was incomplete")
            current_ambient = _open_fd_identities(exclude=journal.descriptors)
            if current_ambient != baseline_ambient_fds:
                _fail("portable-checkpoint successful FD inventory changed")
            result = TwoBirthPortableCheckpointGraphV1(
                source_closure=source_closure,
                credential_bundle=credentials,
                live_checkpoint=checkpoint,
                shutdown_result=shutdown_document,
                journal_records=tuple(journal.facts()),
                _issuer=_ISSUER,
            )
            return result
        except BaseException as error:
            original_error = error
            if journal is not None:
                try:
                    producer_descriptors = journal.descriptors
                    if source_lease is not None:
                        producer_descriptors |= source_lease.descriptors
                    cleanup = _cleanup_raw_runtime(
                        handle=handle,
                        control_cgroup_fd=control_cgroup_fd,
                        baseline_ambient_fds=baseline_ambient_fds,
                        producer_descriptors=producer_descriptors,
                        baseline_subreaper=baseline_subreaper,
                    )
                    if journal.can_append_failure():
                        if source_lease is not None and not source_lease.closed:
                            source_lease.revalidate()
                        failure_closure = _FROZEN_FAILURE_CLOSURE(
                            source_closure=source_closure,
                            journal=journal,
                            cleanup=cleanup,
                            error=error,
                            raw_begin_returned=handle is not None,
                        )
                        journal.append(
                            label="PROTOCOL_FAILURE_CLOSURE",
                            document=failure_closure,
                            id_field="two_birth_protocol_failure_closure_id",
                        )
                except BaseException as cleanup_error:
                    raise ConstructionK7H1TwoBirthPortableCheckpointV1Error(
                        "portable-checkpoint failed and raw cleanup or failure closure did not complete"
                    ) from cleanup_error
            raise ConstructionK7H1TwoBirthPortableCheckpointV1Error(
                "portable-checkpoint producer closed as a typed noncertificate: "
                f"{error}",
                failure_closure=(
                    _freeze_json(failure_closure)
                    if failure_closure is not None
                    else None
                ),
            ) from original_error
        finally:
            if source_lease is not None:
                source_lease.close()
            if journal is not None:
                journal.close()


__all__ = (
    "ConstructionK7H1TwoBirthPortableCheckpointV1Error",
    "PROFILE_KEY",
    "READINESS",
    "SCHEMA_VERSION",
    "TwoBirthPortableCheckpointGraphV1",
    "run_two_birth_portable_checkpoint_producer_v1",
)
