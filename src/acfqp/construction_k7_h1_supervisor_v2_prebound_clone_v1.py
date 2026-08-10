"""Source-closed preparation for one future SUPERVISOR-V2 native birth edge.

This additive V20 slice freezes the exact relocation-free x86-64 native text,
the SUPERVISOR-V2 ELF, one pristine shared PID cell, one empty credentialled
SEQPACKET endpoint, the three protocol frames, and the complete clone ABI
except for the one-shot cgroup grant.  It deliberately has no activation-
successor issuer.  Consequently its sole public execute entry always fails
closed before invoking native text.

The capsule is an owner-thread-bound opaque registry key.  It exposes no file
descriptor, mapping, ctypes object, function pointer, or raw grant accessor.
The PID cell, both ends of the pristine credentialled socketpair, and the role
ELF are borrowed.  This module owns four F_DUPFD_CLOEXEC copies with the same
kernel identities while the caller retains its originals.  Cancellation leaves
a reused descriptor open when its kernel identity differs.  Descriptor-number
reuse with the same open-file description is intentionally outside this local
model because Linux exposes no descriptor-generation identity within one file
descriptor table.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import errno
import fcntl
import hashlib
import mmap
import os
from pathlib import Path
import platform
import signal
import socket
import stat
import struct
import sys
import threading
from types import FunctionType, MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v20 as domains_v20
from acfqp import construction_k7_h1_nested_creator_supervisor_exec_birth_native_v1 as native_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v2 as supervisor_v2
from acfqp import phase3e_ids as ids_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.64-E-C-E5B-B2-D-V20-PREBOUND-CLONE"
PROFILE_KEY = "construction_k7_h1_supervisor_v2_prebound_clone_v1"
READINESS = (
    "BUILD_LOCAL_SOURCE_CLOSED_PREBOUND_NATIVE_EDGE_NO_ACTIVATION_NO_CLONE"
)

EXACT_NATIVE_TEXT_FROZEN = True
EXACT_SUPERVISOR_V2_ELF_REQUIRED = True
EXACT_CLONE_ABI_FROZEN = True
OWNER_THREAD_AND_FORK_BOUND_CAPSULE_PRESENT = True
PUBLIC_FAIL_CLOSED_EXECUTE_ENTRY_PRESENT = True
DIFFERENT_KERNEL_IDENTITY_REUSE_LEFT_OPEN = True
SAME_OPEN_FILE_DESCRIPTION_FD_GENERATION_REUSE_DETECTABLE = False
SAME_PROCESS_PRIVATE_FD_TABLE_MUTATION_IN_SCOPE = False

ACTIVATION_SUCCESSOR_ISSUER_PRESENT = False
GUARDIAN_TAKEOVER_CONSUMED = False
PERMIT_CONSUMPTION_PATH_PRESENT = False
NATIVE_ENTRY_INVOKED = False
CLONE_SYSCALL_PERFORMED = False
ACTUAL_PROCESS_BIRTH_PRESENT = False
PIDFD_ISSUED = False
THREE_BIRTH_PREFIX_AUTHORITY_PRESENT = False
FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT = False
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

PID_CELL_BYTES = 4096
MAX_FRAME_BYTES = native_v1.MAX_RELEASE_FRAME_BYTES
REQUIRED_CLONE_FLAGS = native_v1.REQUIRED_CLONE_FLAGS
REQUIRED_ROLE_SEALS = supervisor_v2.REQUIRED_SEALS
CLONE_ARGS_SIZE = native_v1.CLONE_ARGS_SIZE
CHILD_GATE_SOURCE_FD_MINIMUM = native_v1.CHILD_GATE_SOURCE_FD_MINIMUM
CHILD_GATE_PEER_SOURCE_FD_MINIMUM = CHILD_GATE_SOURCE_FD_MINIMUM + 1
EXECUTABLE_SOURCE_FD_MINIMUM = native_v1.EXECUTABLE_SOURCE_FD_MINIMUM

_RAW_OS_CLOSE = os.close
_RAW_OS_FSTAT = os.fstat
_RAW_OS_PREAD = os.pread
_RAW_OS_READLINK = os.readlink
_RAW_FCNTL = fcntl.fcntl
_RAW_SOCKET_CLASS = socket.socket
_RAW_SHA256 = hashlib.sha256
_RAW_SYS_GETTRACE = sys.gettrace
_RAW_SYS_SETTRACE = sys.settrace
_RAW_SYS_GETPROFILE = sys.getprofile
_RAW_SYS_SETPROFILE = sys.setprofile
_RAW_PTHREAD_SIGMASK = signal.pthread_sigmask
_CANONICAL_JSON_BYTES = ids_v1.canonical_json_bytes
_LOADS_CANONICAL_JSON = ids_v1.loads_canonical_json
_V20_DOMAINS = frozenset(domains_v20.K7_H1_DOMAIN_TAG_EXTENSION_V20)
_CLONE_ARGS_TYPE = native_v1.CloneArgsV1
_PARENT_EDGE_TYPE = native_v1.NativeParentEdgeV1
_LAUNCH_ARGS_TYPE = native_v1.NativeExecLaunchArgsV1
_NATIVE_TEXT_BYTES = bytes(native_v1.X86_64_TEXT_BYTES)
_NATIVE_TEXT_SHA256 = native_v1.X86_64_TEXT_SHA256
_NATIVE_TEXT_BYTE_COUNT = native_v1.X86_64_TEXT_BYTE_COUNT
_SUPERVISOR_V2_ELF_BYTES = bytes(supervisor_v2.ROLE_ELF_BYTES)
_SUPERVISOR_V2_ELF_SHA256 = supervisor_v2.ELF_SHA256
_SUPERVISOR_V2_ELF_BYTE_COUNT = supervisor_v2.ELF_BYTE_COUNT
_BLOCKABLE_SIGNALS = frozenset(signal.valid_signals()) - {
    signal.SIGKILL,
    signal.SIGSTOP,
}

_ARGV0_BYTES = b"acfqp-h1-supervisor-v2\x00"
_PAIR_PROBE_CHILD_TO_PEER = b"ACFQP:V20:PAIR:C2P"
_PAIR_PROBE_PEER_TO_CHILD = b"ACFQP:V20:PAIR:P2C"
_CANONICALIZER_PROBE = {
    "a": [1, 2],
    "b": {"kind": "BUILD_LOCAL_PROBE", "value": True},
}
_CANONICALIZER_PROBE_BYTES = _CANONICAL_JSON_BYTES(_CANONICALIZER_PROBE)
SELF_SOURCE_EXPECTATION_KIND = "BUILD_LOCAL_IMPORT_FACT_NOT_EXTERNAL_AUTHORITY"
EXTERNAL_EXPECTED_SELF_SOURCE_DIGEST_PRESENT = False
BUILD_LOCAL_SELF_SOURCE_MUTATION_DETECTION_PRESENT = True

_ISSUER = object()
_LOCK = threading.RLock()
_LIVE: dict["H1SupervisorV2PreboundNativeCloneV1", "_LiveCapsuleRecordV1"] = {}
_PRECOMMIT: dict[object, "_PendingResourcesV1"] = {}
_CLOSING: dict[
    "H1SupervisorV2PreboundNativeCloneV1", "_CleanupProgressV1"
] = {}
_TERMINAL: dict[
    "H1SupervisorV2PreboundNativeCloneV1", "_TerminalCancellationRecordV1"
] = {}
_LOCAL_CALLABLES: Mapping[str, tuple[Any, Any, Any, Any]] = MappingProxyType({})

_SELF_PATH = Path(__file__).resolve(strict=True)
_SOURCE_PATHS = MappingProxyType(
    {
        "prebound_clone_v1": _SELF_PATH,
        "domain_registry_v20": Path(domains_v20.__file__).resolve(strict=True),
        "native_exec_binding_v1": Path(native_v1.__file__).resolve(strict=True),
        "native_exec_text_v1": native_v1.SOURCE_PATH,
        "supervisor_role_v2": Path(supervisor_v2.__file__).resolve(strict=True),
        "supervisor_role_source_v2": supervisor_v2.SOURCE_PATH,
        "supervisor_role_source_v1": supervisor_v2.V1_SOURCE_PATH,
        "phase3e_ids": Path(ids_v1.__file__).resolve(strict=True),
    }
)
_EXPECTED_SOURCE_SHA256 = MappingProxyType(
    {
        "domain_registry_v20": "297197069dc88353d986d22bc0c3e4a4755f7c18055f5c5ae4412f51f7085a61",
        "native_exec_binding_v1": "434ce1618929abb0ce1534ca79f11fa8f4102b100dac68e64160f4e51490dee8",
        "native_exec_text_v1": "cb7b665a024d9d92821a706e5c68d5e24fcbcb3ef6d2faac401936265ba4803b",
        "supervisor_role_v2": "093600d4c33df993e851525e28a686318780de593a9c2bbbb3a3ebc639440d8e",
        "supervisor_role_source_v2": "a06c90bd9137b3b59171f0137400aa5964560ba7411833591446bb39205fc252",
        "supervisor_role_source_v1": "3461a4b7215f04cf4a2c7274a8737968f438ed1bc8270027400c00b920c52750",
        "phase3e_ids": "3eb435bfec4692961d61b4edf6e067cc128810509b5e35ec1d7348079288c4c2",
    }
)


def _source_fact(path: Path) -> tuple[int, int, int, int, str]:
    status = path.stat()
    raw = path.read_bytes()
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        _RAW_SHA256(raw).hexdigest(),
    )


_IMPORT_SOURCE_FACTS = MappingProxyType(
    {label: _source_fact(path) for label, path in _SOURCE_PATHS.items()}
)
for _label, _digest in _EXPECTED_SOURCE_SHA256.items():
    if _IMPORT_SOURCE_FACTS[_label][-1] != _digest:  # pragma: no cover
        raise RuntimeError(f"V20 prebound clone dependency changed: {_label}")

_EXPECTED_DOMAIN_GLOBALS = MappingProxyType(
    {
        name: getattr(domains_v20, name)
        for name in dir(domains_v20)
        if name.endswith("_DOMAIN")
        or name
        in {
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V20",
            "K7_H1_DOMAIN_TAG_EXTENSION_V20",
        }
    }
    | {
        "canonical_json_bytes": domains_v20.canonical_json_bytes,
        "extension_content_id_v20": domains_v20.extension_content_id_v20,
    }
)
_UPSTREAM_CALLABLES = MappingProxyType(
    {
        (module_name, name): (
            value,
            value.__code__,
            value.__defaults__,
            dict(value.__kwdefaults__) if value.__kwdefaults__ else None,
        )
        for module_name, module in (
            ("domains", domains_v20),
            ("native", native_v1),
            ("supervisor", supervisor_v2),
            ("ids", ids_v1),
        )
        for name, value in vars(module).items()
        if type(value) is FunctionType and value.__globals__ is module.__dict__
    }
)
_UPSTREAM_MODULES = MappingProxyType(
    {
        "domains": domains_v20,
        "native": native_v1,
        "supervisor": supervisor_v2,
        "ids": ids_v1,
    }
)
_STATIC_GLOBALS = MappingProxyType(
    {
        "domains_v20": domains_v20,
        "native_v1": native_v1,
        "supervisor_v2": supervisor_v2,
        "ids_v1": ids_v1,
        "sys": sys,
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "PROPOSED_CONTRACT_VERSION": PROPOSED_CONTRACT_VERSION,
        "PROFILE_KEY": PROFILE_KEY,
        "READINESS": READINESS,
        "EXACT_NATIVE_TEXT_FROZEN": EXACT_NATIVE_TEXT_FROZEN,
        "EXACT_SUPERVISOR_V2_ELF_REQUIRED": EXACT_SUPERVISOR_V2_ELF_REQUIRED,
        "EXACT_CLONE_ABI_FROZEN": EXACT_CLONE_ABI_FROZEN,
        "OWNER_THREAD_AND_FORK_BOUND_CAPSULE_PRESENT": (
            OWNER_THREAD_AND_FORK_BOUND_CAPSULE_PRESENT
        ),
        "PUBLIC_FAIL_CLOSED_EXECUTE_ENTRY_PRESENT": (
            PUBLIC_FAIL_CLOSED_EXECUTE_ENTRY_PRESENT
        ),
        "DIFFERENT_KERNEL_IDENTITY_REUSE_LEFT_OPEN": (
            DIFFERENT_KERNEL_IDENTITY_REUSE_LEFT_OPEN
        ),
        "SAME_OPEN_FILE_DESCRIPTION_FD_GENERATION_REUSE_DETECTABLE": (
            SAME_OPEN_FILE_DESCRIPTION_FD_GENERATION_REUSE_DETECTABLE
        ),
        "SAME_PROCESS_PRIVATE_FD_TABLE_MUTATION_IN_SCOPE": (
            SAME_PROCESS_PRIVATE_FD_TABLE_MUTATION_IN_SCOPE
        ),
        "ACTIVATION_SUCCESSOR_ISSUER_PRESENT": ACTIVATION_SUCCESSOR_ISSUER_PRESENT,
        "GUARDIAN_TAKEOVER_CONSUMED": GUARDIAN_TAKEOVER_CONSUMED,
        "PERMIT_CONSUMPTION_PATH_PRESENT": PERMIT_CONSUMPTION_PATH_PRESENT,
        "NATIVE_ENTRY_INVOKED": NATIVE_ENTRY_INVOKED,
        "CLONE_SYSCALL_PERFORMED": CLONE_SYSCALL_PERFORMED,
        "ACTUAL_PROCESS_BIRTH_PRESENT": ACTUAL_PROCESS_BIRTH_PRESENT,
        "PIDFD_ISSUED": PIDFD_ISSUED,
        "THREE_BIRTH_PREFIX_AUTHORITY_PRESENT": THREE_BIRTH_PREFIX_AUTHORITY_PRESENT,
        "FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT": FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT,
        "PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT": (
            PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT
        ),
        "FQ11_COUNTER_COMPLETENESS_PRESENT": FQ11_COUNTER_COMPLETENESS_PRESENT,
        "FORMAL_COUNTER_RECORDS_ISSUED": FORMAL_COUNTER_RECORDS_ISSUED,
        "FORMAL_WORK_VECTOR_ISSUED": FORMAL_WORK_VECTOR_ISSUED,
        "FORMAL_COMPARISON_VECTOR_ISSUED": FORMAL_COMPARISON_VECTOR_ISSUED,
        "FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED": (
            FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED
        ),
        "CURRENT_ACCESS_AUTHORITY_PRESENT": CURRENT_ACCESS_AUTHORITY_PRESENT,
        "FORMAL_V7_AUTHORITY_PRESENT": FORMAL_V7_AUTHORITY_PRESENT,
        "OFFICIAL_EXECUTION_ALLOWED": OFFICIAL_EXECUTION_ALLOWED,
        "OFFICIAL_SCALAR_COST": OFFICIAL_SCALAR_COST,
        "OFFICIAL_N_BREAK_EVEN": OFFICIAL_N_BREAK_EVEN,
        "COUNTER_COMPLETENESS_GATE": COUNTER_COMPLETENESS_GATE,
        "WORKLOAD_ECONOMICS_GATE": WORKLOAD_ECONOMICS_GATE,
        "PID_CELL_BYTES": PID_CELL_BYTES,
        "MAX_FRAME_BYTES": MAX_FRAME_BYTES,
        "REQUIRED_CLONE_FLAGS": REQUIRED_CLONE_FLAGS,
        "REQUIRED_ROLE_SEALS": REQUIRED_ROLE_SEALS,
        "CLONE_ARGS_SIZE": CLONE_ARGS_SIZE,
        "CHILD_GATE_SOURCE_FD_MINIMUM": CHILD_GATE_SOURCE_FD_MINIMUM,
        "CHILD_GATE_PEER_SOURCE_FD_MINIMUM": CHILD_GATE_PEER_SOURCE_FD_MINIMUM,
        "EXECUTABLE_SOURCE_FD_MINIMUM": EXECUTABLE_SOURCE_FD_MINIMUM,
        "_RAW_OS_CLOSE": _RAW_OS_CLOSE,
        "_RAW_OS_FSTAT": _RAW_OS_FSTAT,
        "_RAW_OS_PREAD": _RAW_OS_PREAD,
        "_RAW_OS_READLINK": _RAW_OS_READLINK,
        "_RAW_FCNTL": _RAW_FCNTL,
        "_RAW_SOCKET_CLASS": _RAW_SOCKET_CLASS,
        "_RAW_SHA256": _RAW_SHA256,
        "_RAW_SYS_GETTRACE": _RAW_SYS_GETTRACE,
        "_RAW_SYS_SETTRACE": _RAW_SYS_SETTRACE,
        "_RAW_SYS_GETPROFILE": _RAW_SYS_GETPROFILE,
        "_RAW_SYS_SETPROFILE": _RAW_SYS_SETPROFILE,
        "_RAW_PTHREAD_SIGMASK": _RAW_PTHREAD_SIGMASK,
        "_CANONICAL_JSON_BYTES": _CANONICAL_JSON_BYTES,
        "_LOADS_CANONICAL_JSON": _LOADS_CANONICAL_JSON,
        "_V20_DOMAINS": _V20_DOMAINS,
        "_CANONICALIZER_PROBE": _CANONICALIZER_PROBE,
        "_CANONICALIZER_PROBE_BYTES": _CANONICALIZER_PROBE_BYTES,
        "_CLONE_ARGS_TYPE": _CLONE_ARGS_TYPE,
        "_PARENT_EDGE_TYPE": _PARENT_EDGE_TYPE,
        "_LAUNCH_ARGS_TYPE": _LAUNCH_ARGS_TYPE,
        "_NATIVE_TEXT_BYTES": _NATIVE_TEXT_BYTES,
        "_NATIVE_TEXT_SHA256": _NATIVE_TEXT_SHA256,
        "_NATIVE_TEXT_BYTE_COUNT": _NATIVE_TEXT_BYTE_COUNT,
        "_SUPERVISOR_V2_ELF_BYTES": _SUPERVISOR_V2_ELF_BYTES,
        "_SUPERVISOR_V2_ELF_SHA256": _SUPERVISOR_V2_ELF_SHA256,
        "_SUPERVISOR_V2_ELF_BYTE_COUNT": _SUPERVISOR_V2_ELF_BYTE_COUNT,
        "_BLOCKABLE_SIGNALS": _BLOCKABLE_SIGNALS,
        "_ARGV0_BYTES": _ARGV0_BYTES,
        "_PAIR_PROBE_CHILD_TO_PEER": _PAIR_PROBE_CHILD_TO_PEER,
        "_PAIR_PROBE_PEER_TO_CHILD": _PAIR_PROBE_PEER_TO_CHILD,
        "SELF_SOURCE_EXPECTATION_KIND": SELF_SOURCE_EXPECTATION_KIND,
        "EXTERNAL_EXPECTED_SELF_SOURCE_DIGEST_PRESENT": (
            EXTERNAL_EXPECTED_SELF_SOURCE_DIGEST_PRESENT
        ),
        "BUILD_LOCAL_SELF_SOURCE_MUTATION_DETECTION_PRESENT": (
            BUILD_LOCAL_SELF_SOURCE_MUTATION_DETECTION_PRESENT
        ),
        "_SOURCE_PATHS": _SOURCE_PATHS,
        "_EXPECTED_SOURCE_SHA256": _EXPECTED_SOURCE_SHA256,
        "_IMPORT_SOURCE_FACTS": _IMPORT_SOURCE_FACTS,
        "_EXPECTED_DOMAIN_GLOBALS": _EXPECTED_DOMAIN_GLOBALS,
        "_UPSTREAM_CALLABLES": _UPSTREAM_CALLABLES,
        "_UPSTREAM_MODULES": _UPSTREAM_MODULES,
        "_ISSUER": _ISSUER,
        "_LOCK": _LOCK,
        "_LIVE": _LIVE,
        "_PRECOMMIT": _PRECOMMIT,
        "_CLOSING": _CLOSING,
        "_TERMINAL": _TERMINAL,
    }
)


class ConstructionK7H1SupervisorV2PreboundCloneV1Error(RuntimeError):
    """The V20 source, capsule, native image, FD, owner, or state crossed."""

    def __init__(
        self,
        message: str,
        *,
        cleanup_document: Mapping[str, Any] | None = None,
        primary_error: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.cleanup_document = (
            _deep_copy(cleanup_document) if cleanup_document is not None else None
        )
        self.primary_error = primary_error


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1SupervisorV2PreboundCloneV1Error(message)


def _claims() -> dict[str, Any]:
    return {
        "activation_successor_issuer_present": False,
        "guardian_takeover_consumed": False,
        "permit_consumption_path_present": False,
        "native_entry_invoked": False,
        "clone_syscall_performed": False,
        "actual_process_birth_present": False,
        "pidfd_issued": False,
        "three_birth_prefix_authority_present": False,
        "five_birth_process_authority_present": False,
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
        "external_expected_self_source_digest_present": False,
        "build_local_self_source_mutation_detection_present": True,
        "self_source_expectation_kind": SELF_SOURCE_EXPECTATION_KIND,
        "different_kernel_identity_reuse_left_open": True,
        "same_open_file_description_fd_generation_reuse_detectable": False,
        "same_process_private_fd_table_mutation_in_scope": False,
    }


def _deep_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = _LOADS_CANONICAL_JSON(_CANONICAL_JSON_BYTES(value))
    if type(copied) is not dict:
        _fail("V20 canonical copy changed exact type")
    return copied


def _document_bytes(value: Mapping[str, Any]) -> bytes:
    raw = _CANONICAL_JSON_BYTES(value)
    if _CANONICAL_JSON_BYTES(_LOADS_CANONICAL_JSON(raw)) != raw:
        _fail("V20 canonical document replay changed")
    return raw


def _document_from_bytes(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} canonical bytes changed type")
    value = _LOADS_CANONICAL_JSON(raw)
    if type(value) is not dict or _CANONICAL_JSON_BYTES(value) != raw:
        _fail(f"{label} canonical bytes changed")
    return value


def _local_domain_id(domain_tag: str, payload: Mapping[str, Any]) -> str:
    if type(domain_tag) is not str or domain_tag not in _V20_DOMAINS:
        _fail("V20 local content-ID domain changed")
    return _RAW_SHA256(
        domain_tag.encode("utf-8") + b"\x00" + _CANONICAL_JSON_BYTES(payload)
    ).hexdigest()


def _with_id(
    payload: Mapping[str, Any], *, domain: str, id_field: str
) -> dict[str, Any]:
    result = dict(payload)
    result[id_field] = _local_domain_id(domain, payload)
    return result


def _verify_id(
    document: Mapping[str, Any], *, domain: str, id_field: str, label: str
) -> str:
    if type(document) is not dict:
        _fail(f"{label} is not one exact object")
    payload = dict(document)
    supplied = payload.pop(id_field, None)
    if type(supplied) is not str or _local_domain_id(domain, payload) != supplied:
        _fail(f"{label} content ID changed")
    return supplied


def _source_closure_document(
    source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return _with_id(
        {
            "schema": "acfqp.k7_h1_supervisor_v2_prebound_native_edge_source_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_rows": source_rows,
            "native_text_sha256": _NATIVE_TEXT_SHA256,
            "native_text_byte_count": _NATIVE_TEXT_BYTE_COUNT,
            "supervisor_v2_elf_sha256": _SUPERVISOR_V2_ELF_SHA256,
            "supervisor_v2_elf_byte_count": _SUPERVISOR_V2_ELF_BYTE_COUNT,
            "runtime_toolchain_invocation_present": False,
            "self_source_expectation_scope": (
                "BUILD_LOCAL_IMPORT_FACT_WITH_POST_IMPORT_MUTATION_REPLAY"
            ),
            **_claims(),
        },
        domain=(
            domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_SOURCE_CLOSURE_V1_DOMAIN
        ),
        id_field="prebound_native_edge_source_closure_id",
    )


def _capsule_document(
    *,
    source_closure_id: str,
    owner_pid: int,
    owner_process_start_ticks: int,
    owner_thread_id: int,
    owner_native_thread_id: int,
    fd_facts: list[dict[str, Any]],
    source_fd_facts: list[dict[str, Any]],
    frame_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    return _with_id(
        {
            "schema": "acfqp.k7_h1_supervisor_v2_prebound_native_edge_capsule.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "prebound_native_edge_source_closure_id": source_closure_id,
            "state": "PREBOUND_NO_ACTIVATION",
            "owner_identity": {
                "pid": owner_pid,
                "process_start_ticks": owner_process_start_ticks,
                "thread_id": owner_thread_id,
                "native_thread_id": owner_native_thread_id,
            },
            "fd_facts": fd_facts,
            "source_fd_facts": source_fd_facts,
            "input_ownership": {
                "caller_retains_original_descriptors": 4,
                "capsule_owns_f_dupfd_cloexec_duplicates": True,
                "duplicates_preserve_kernel_identity": True,
            },
            "frame_facts": frame_facts,
            "clone_args_template": {
                "flags": REQUIRED_CLONE_FLAGS,
                "exit_signal": int(signal.SIGCHLD),
                "cgroup": {
                    "kind": "NOT_BOUND",
                    "reason": "GUARDIAN_ACTIVATION_SUCCESSOR_REQUIRED",
                },
            },
            "single_thread_process_required_at_future_native_entry": True,
            "native_text_sha256": _NATIVE_TEXT_SHA256,
            "native_entry_state": "ABSENT_UNTIL_GUARDIAN_ACTIVATION_SUCCESSOR",
            "executable_native_mapping_present": False,
            "capsule_owned_executable_native_mapping_present": False,
            "upstream_native_trampoline_unmapped": True,
            "supervisor_v2_elf_sha256": _SUPERVISOR_V2_ELF_SHA256,
            "raw_descriptor_accessor_present": False,
            "raw_native_callable_accessor_present": False,
            **_claims(),
        },
        domain=(
            domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_CAPSULE_V1_DOMAIN
        ),
        id_field="prebound_native_edge_capsule_id",
    )


def _callable_fact(function: Any) -> tuple[Any, Any, Any, Any]:
    return (
        function,
        function.__code__,
        function.__defaults__,
        dict(function.__kwdefaults__) if function.__kwdefaults__ else None,
    )


def _expectation_literal_fingerprint(
    source_builder: Any,
    capsule_builder: Any,
    _sha256: Any = _RAW_SHA256,
) -> str:
    chunks: list[bytes] = []
    for label, function in (
        ("source", source_builder),
        ("capsule", capsule_builder),
    ):
        code = function.__code__
        chunks.extend(
            (
                label.encode("ascii"),
                code.co_code,
                repr(code.co_consts).encode("utf-8"),
                repr(code.co_names).encode("utf-8"),
            )
        )
    return _sha256(b"\x00".join(chunks)).hexdigest()


def _make_import_time_expectation_anchor(
    *,
    source_builder: Any,
    capsule_builder: Any,
    static_registry: Mapping[str, Any],
    literal_fingerprint_builder: Any,
    error_type: type[Exception],
) -> tuple[Any, Any]:
    """Capture expectations in closure cells that global rebinding cannot rebase."""

    module_globals = source_builder.__globals__
    expected_literal_fingerprint = literal_fingerprint_builder(
        source_builder,
        capsule_builder,
    )
    expected_fingerprint_callable = _callable_fact(literal_fingerprint_builder)
    sealed_callable_registry: Mapping[str, tuple[Any, Any, Any, Any]] | None = None

    def seal_callable_registry(
        registry: Mapping[str, tuple[Any, Any, Any, Any]],
    ) -> None:
        nonlocal sealed_callable_registry
        if sealed_callable_registry is not None:
            raise error_type("V20 import-time expectation anchor was resealed")
        sealed_callable_registry = registry

    def verify_expectation_anchor() -> tuple[Any, Any]:
        registry = sealed_callable_registry
        if (
            registry is None
            or module_globals.get("_LOCAL_CALLABLES") is not registry
            or module_globals.get("_STATIC_GLOBALS") is not static_registry
        ):
            raise error_type("V20 import-time expectation registry changed")
        for name, expected in registry.items():
            live = module_globals.get(name)
            if (
                live is not expected[0]
                or getattr(live, "__code__", None) is not expected[1]
                or getattr(live, "__defaults__", None) != expected[2]
                or getattr(live, "__kwdefaults__", None) != expected[3]
                or getattr(live, "__globals__", None) is not module_globals
            ):
                raise error_type(
                    f"V20 local callable changed at import-time anchor: {name}"
                )
        for name, expected in static_registry.items():
            if module_globals.get(name) is not expected:
                raise error_type(
                    f"V20 static global identity changed at import-time anchor: {name}"
                )
        if (
            module_globals.get("_source_closure_document") is not source_builder
            or module_globals.get("_capsule_document") is not capsule_builder
            or module_globals.get("_expectation_literal_fingerprint")
            is not literal_fingerprint_builder
            or _callable_fact(literal_fingerprint_builder)
            != expected_fingerprint_callable
            or literal_fingerprint_builder(source_builder, capsule_builder)
            != expected_literal_fingerprint
        ):
            raise error_type("V20 import-time expectation literal fingerprint changed")
        return source_builder, capsule_builder

    return seal_callable_registry, verify_expectation_anchor


(
    _SEAL_IMPORT_TIME_EXPECTATION_ANCHOR,
    _VERIFY_IMPORT_TIME_EXPECTATION_ANCHOR,
) = _make_import_time_expectation_anchor(
    source_builder=_source_closure_document,
    capsule_builder=_capsule_document,
    static_registry=_STATIC_GLOBALS,
    literal_fingerprint_builder=_expectation_literal_fingerprint,
    error_type=ConstructionK7H1SupervisorV2PreboundCloneV1Error,
)


def _validate_source_and_code_closure(
    _expectation_anchor: Any = _VERIFY_IMPORT_TIME_EXPECTATION_ANCHOR,
) -> list[dict[str, Any]]:
    _expectation_anchor()
    rows: list[dict[str, Any]] = []
    for label, path in sorted(_SOURCE_PATHS.items()):
        observed = _source_fact(path)
        if observed != _IMPORT_SOURCE_FACTS[label]:
            _fail(f"V20 prebound clone source changed after import: {label}")
        rows.append(
            {
                "label": label,
                "sha256": observed[-1],
                "byte_count": observed[3],
            }
        )
    for (module_name, name), expected in _UPSTREAM_CALLABLES.items():
        live = getattr(_UPSTREAM_MODULES[module_name], name, None)
        if (
            live is not expected[0]
            or getattr(live, "__code__", None) is not expected[1]
            or getattr(live, "__defaults__", None) != expected[2]
            or getattr(live, "__kwdefaults__", None) != expected[3]
            or getattr(live, "__globals__", None)
            is not _UPSTREAM_MODULES[module_name].__dict__
        ):
            _fail(f"V20 upstream callable changed: {module_name}.{name}")
    module_globals = globals()
    for name, expected in _LOCAL_CALLABLES.items():
        live = module_globals.get(name)
        if (
            live is not expected[0]
            or getattr(live, "__code__", None) is not expected[1]
            or getattr(live, "__defaults__", None) != expected[2]
            or getattr(live, "__kwdefaults__", None) != expected[3]
            or getattr(live, "__globals__", None) is not module_globals
        ):
            _fail(f"V20 local callable changed: {name}")
    for name, expected in _STATIC_GLOBALS.items():
        if module_globals.get(name) is not expected:
            _fail(f"V20 static global identity changed: {name}")
    for name, expected in _EXPECTED_DOMAIN_GLOBALS.items():
        if getattr(domains_v20, name, None) is not expected:
            _fail(f"V20 domain global identity changed: {name}")
    if (
        hashlib.sha256 is not _RAW_SHA256
        or _CANONICAL_JSON_BYTES(_CANONICALIZER_PROBE)
        != _CANONICALIZER_PROBE_BYTES
        or domains_v20.canonical_json_bytes is not _CANONICAL_JSON_BYTES
        or frozenset(domains_v20.K7_H1_DOMAIN_TAG_EXTENSION_V20)
        != _V20_DOMAINS
        or
        native_v1.CloneArgsV1 is not _CLONE_ARGS_TYPE
        or native_v1.NativeParentEdgeV1 is not _PARENT_EDGE_TYPE
        or native_v1.NativeExecLaunchArgsV1 is not _LAUNCH_ARGS_TYPE
        or native_v1.REQUIRED_CLONE_FLAGS != REQUIRED_CLONE_FLAGS
        or bytes(native_v1.X86_64_TEXT_BYTES) != _NATIVE_TEXT_BYTES
        or supervisor_v2.ROLE_ELF_BYTES != _SUPERVISOR_V2_ELF_BYTES
        or supervisor_v2.ELF_SHA256 != _SUPERVISOR_V2_ELF_SHA256
        or supervisor_v2.ELF_BYTE_COUNT != _SUPERVISOR_V2_ELF_BYTE_COUNT
    ):
        _fail("V20 hash primitive, native, or SUPERVISOR-V2 public global changed")
    if (
        getattr(native_v1, "_TRAMPOLINE_MEMORY", None) is not None
        or getattr(native_v1, "_TRAMPOLINE_FUNCTION", None) is not None
    ):
        _fail("V20 upstream native trampoline was mapped before activation")
    return rows


def _verify_native_abi_and_images() -> None:
    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        _fail("V20 prebound clone is registered only for Linux x86-64")
    if (
        len(_NATIVE_TEXT_BYTES) != _NATIVE_TEXT_BYTE_COUNT
        or _RAW_SHA256(_NATIVE_TEXT_BYTES).hexdigest() != _NATIVE_TEXT_SHA256
        or len(_SUPERVISOR_V2_ELF_BYTES) != _SUPERVISOR_V2_ELF_BYTE_COUNT
        or _RAW_SHA256(_SUPERVISOR_V2_ELF_BYTES).hexdigest()
        != _SUPERVISOR_V2_ELF_SHA256
        or _SUPERVISOR_V2_ELF_BYTES[:16] != b"\x7fELF\x02\x01\x01" + bytes(9)
        or ctypes.sizeof(_CLONE_ARGS_TYPE) != CLONE_ARGS_SIZE
        or ctypes.sizeof(_PARENT_EDGE_TYPE) != 32
        or ctypes.sizeof(_LAUNCH_ARGS_TYPE) != 128
    ):
        _fail("V20 native text, role ELF, or ABI changed")
    offsets = {
        name: getattr(_LAUNCH_ARGS_TYPE, name).offset
        for name, _ctype in _LAUNCH_ARGS_TYPE._fields_
    }
    if offsets != {
        "clone_args": 0,
        "creator_pid_cell_mapping": 8,
        "pid_cell_mapping_bytes": 16,
        "creator_pid_cell_fd": 24,
        "one_shot_cgroup_grant_fd": 32,
        "child_gate_fd": 40,
        "parent_edge": 48,
        "cell_withdrawn_frame": 56,
        "cell_withdrawn_frame_bytes": 64,
        "gate_ready_frame": 72,
        "gate_ready_frame_bytes": 80,
        "release_frame": 88,
        "release_frame_bytes": 96,
        "supervisor_executable_fd": 104,
        "supervisor_argv": 112,
        "supervisor_envp": 120,
    }:
        _fail("V20 native launch ABI offsets changed")


def _owner_thread_identity() -> tuple[int, threading.Thread, int, int]:
    # Preparation is inert and may run under a test/runner supervisor thread.
    # The later fused native-entry boundary must separately prove an exact
    # single-thread process immediately before clone3.
    return (
        os.getpid(),
        threading.current_thread(),
        threading.get_ident(),
        threading.get_native_id(),
    )


def _process_start_ticks(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    close = raw.rfind(")")
    if close < 0:
        _fail("V20 owner process stat grammar changed")
    fields = raw[close + 2 :].split()
    if len(fields) < 20 or not fields[19].isdigit():
        _fail("V20 owner process start time is absent")
    return int(fields[19])


def _fd_common(descriptor: int, *, role: str) -> dict[str, Any]:
    if type(descriptor) is not int or descriptor < 0:
        _fail(f"V20 {role} descriptor is invalid")
    status = _RAW_OS_FSTAT(descriptor)
    flags = _RAW_FCNTL(descriptor, fcntl.F_GETFD)
    if flags & fcntl.FD_CLOEXEC == 0:
        _fail(f"V20 {role} descriptor lost CLOEXEC")
    return {
        "role": role,
        "device": status.st_dev,
        "inode": status.st_ino,
        "mode": status.st_mode,
        "size": status.st_size,
        "cloexec": True,
    }


def _owned_socket_inspection_duplicate(descriptor: int) -> socket.socket:
    """Wrap only a module-owned duplicate of one borrowed socket descriptor."""

    duplicate_fd = -1
    endpoint: socket.socket | None = None
    committed = False
    prior_trace = _RAW_SYS_GETTRACE()
    prior_profile = _RAW_SYS_GETPROFILE()
    prior_signal_mask: set[signal.Signals] | None = None
    try:
        # No Python trace/profile callback or catchable signal can cut between
        # the kernel FD allocation and socket-object adoption.  All three are
        # restored below after the duplicate is either wrapped or closed.
        _RAW_SYS_SETTRACE(None)
        _RAW_SYS_SETPROFILE(None)
        prior_signal_mask = _RAW_PTHREAD_SIGMASK(
            signal.SIG_BLOCK,
            _BLOCKABLE_SIGNALS,
        )
        duplicate_fd = int(_RAW_FCNTL(descriptor, fcntl.F_DUPFD_CLOEXEC, 3))
        endpoint = _RAW_SOCKET_CLASS(fileno=duplicate_fd)
        committed = True
        return endpoint
    finally:
        try:
            if not committed:
                if endpoint is not None:
                    endpoint.close()
                elif duplicate_fd >= 0:
                    try:
                        _RAW_OS_CLOSE(duplicate_fd)
                    except OSError:
                        pass
        finally:
            try:
                if prior_signal_mask is not None:
                    _RAW_PTHREAD_SIGMASK(signal.SIG_SETMASK, prior_signal_mask)
            finally:
                _RAW_SYS_SETPROFILE(prior_profile)
                _RAW_SYS_SETTRACE(prior_trace)


def _socket_queue_is_empty(descriptor: int) -> bool:
    endpoint: socket.socket | None = None
    try:
        endpoint = _owned_socket_inspection_duplicate(descriptor)
        try:
            endpoint.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
        except BlockingIOError:
            return True
        return False
    finally:
        if endpoint is not None:
            endpoint.close()


def _socket_credentials(ancillary: list[tuple[int, int, bytes]]) -> tuple[int, int, int]:
    values = [
        struct.unpack("3i", raw[:12])
        for level, kind, raw in ancillary
        if level == socket.SOL_SOCKET
        and kind == getattr(socket, "SCM_CREDENTIALS", 2)
        and len(raw) >= 12
    ]
    if len(values) != 1:
        _fail("V20 child gate pair did not carry exactly one credential record")
    return tuple(int(value) for value in values[0])


def _drain_interrupted_pair_probe(
    receiver: socket.socket,
    *,
    payload: bytes,
) -> None:
    """Remove our sole probe record when a round trip is interrupted."""

    try:
        raw, _ancillary, message_flags, _address = receiver.recvmsg(
            len(payload) + 1,
            socket.CMSG_SPACE(12),
            socket.MSG_DONTWAIT,
        )
    except BlockingIOError:
        # The send did not commit, or the matching receive already consumed it.
        return
    if (
        raw != payload
        or message_flags
        & (getattr(socket, "MSG_TRUNC", 0) | getattr(socket, "MSG_CTRUNC", 0))
    ):
        _fail("V20 interrupted pair-probe rollback observed an alien record")


def _round_trip_pair_probe(
    sender: socket.socket,
    receiver: socket.socket,
    *,
    payload: bytes,
) -> tuple[bytes, list[tuple[int, int, bytes]], int]:
    """Send and consume one probe, rolling back a committed send on failure."""

    probe_may_be_queued = True
    send_completed = False
    receive_completed = False
    try:
        count = sender.send(
            payload,
            socket.MSG_DONTWAIT | getattr(socket, "MSG_NOSIGNAL", 0),
        )
        send_completed = True
        if count != len(payload):
            _fail("V20 child gate pair probe was partial")
        raw, ancillary, message_flags, _address = receiver.recvmsg(
            len(payload) + 1,
            socket.CMSG_SPACE(12),
            socket.MSG_DONTWAIT,
        )
        receive_completed = True
        probe_may_be_queued = False
        return raw, ancillary, message_flags
    finally:
        # Setting the phase flags on separate bytecode/line boundaries makes
        # every trace/signal cut conservative: an empty nonblocking receive is
        # harmless, while a committed probe is removed before failure escapes.
        if probe_may_be_queued or (send_completed and not receive_completed):
            _drain_interrupted_pair_probe(receiver, payload=payload)


def _socket_pair_facts(
    child_gate_fd: int,
    child_gate_peer_fd: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    child: socket.socket | None = None
    peer: socket.socket | None = None
    try:
        child = _owned_socket_inspection_duplicate(child_gate_fd)
        peer = _owned_socket_inspection_duplicate(child_gate_peer_fd)
        endpoints = (
            ("child_gate_fd", child_gate_fd, child),
            ("child_gate_peer_fd", child_gate_peer_fd, peer),
        )
        facts: list[dict[str, Any]] = []
        for role, descriptor, endpoint in endpoints:
            common = _fd_common(descriptor, role=role)
            status_flags = _RAW_FCNTL(descriptor, fcntl.F_GETFL)
            receive_timeout = endpoint.getsockopt(
                socket.SOL_SOCKET, socket.SO_RCVTIMEO, 16
            )
            send_timeout = endpoint.getsockopt(
                socket.SOL_SOCKET, socket.SO_SNDTIMEO, 16
            )
            if (
                endpoint.family != socket.AF_UNIX
                or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
                != socket.SOCK_SEQPACKET
                or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != 1
                or status_flags & os.O_NONBLOCK
                or receive_timeout != bytes(len(receive_timeout))
                or send_timeout != bytes(len(send_timeout))
                or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR) != 0
            ):
                _fail("V20 child gate pair flags, timeout, or credentials changed")
            peer_name = endpoint.getpeername()
            peer_credentials_raw = endpoint.getsockopt(
                socket.SOL_SOCKET, getattr(socket, "SO_PEERCRED", 17), 12
            )
            if len(peer_credentials_raw) != 12:
                _fail("V20 child gate peer credentials changed width")
            peer_credentials = tuple(
                int(value) for value in struct.unpack("3i", peer_credentials_raw)
            )
            cookie: int | None = None
            if hasattr(socket, "SO_COOKIE"):
                cookie_raw = endpoint.getsockopt(
                    socket.SOL_SOCKET, socket.SO_COOKIE, 8
                )
                cookie = int.from_bytes(cookie_raw, "little", signed=False)
            common.update(
                {
                    "fd_kind": "BLOCKING_CONNECTED_AF_UNIX_SOCK_SEQPACKET_ENDPOINT",
                    "socket_domain": int(socket.AF_UNIX),
                    "socket_type": int(socket.SOCK_SEQPACKET),
                    "passcred": 1,
                    "nonblocking": False,
                    "receive_timeout_zero": True,
                    "send_timeout_zero": True,
                    "peer_name_repr": repr(peer_name),
                    "peer_credentials": {
                        "pid": peer_credentials[0],
                        "uid": peer_credentials[1],
                        "gid": peer_credentials[2],
                    },
                    "socket_cookie": cookie,
                }
            )
            facts.append(common)

        if not _socket_queue_is_empty(child_gate_fd) or not _socket_queue_is_empty(
            child_gate_peer_fd
        ):
            _fail("V20 child gate pair contains pre-activation data")

        raw, ancillary, message_flags = _round_trip_pair_probe(
            child,
            peer,
            payload=_PAIR_PROBE_CHILD_TO_PEER,
        )
        if (
            raw != _PAIR_PROBE_CHILD_TO_PEER
            or message_flags
            & (getattr(socket, "MSG_TRUNC", 0) | getattr(socket, "MSG_CTRUNC", 0))
            or _socket_credentials(ancillary) != (os.getpid(), os.getuid(), os.getgid())
        ):
            _fail("V20 child gate pair forward identity probe changed")

        raw, ancillary, message_flags = _round_trip_pair_probe(
            peer,
            child,
            payload=_PAIR_PROBE_PEER_TO_CHILD,
        )
        if (
            raw != _PAIR_PROBE_PEER_TO_CHILD
            or message_flags
            & (getattr(socket, "MSG_TRUNC", 0) | getattr(socket, "MSG_CTRUNC", 0))
            or _socket_credentials(ancillary) != (os.getpid(), os.getuid(), os.getgid())
            or not _socket_queue_is_empty(child_gate_fd)
            or not _socket_queue_is_empty(child_gate_peer_fd)
        ):
            _fail("V20 child gate pair reverse identity probe changed")
        pair_proof = _RAW_SHA256(
            _PAIR_PROBE_CHILD_TO_PEER + b"\x00" + _PAIR_PROBE_PEER_TO_CHILD
        ).hexdigest()
        for fact, endpoint in zip(facts, (child, peer), strict=True):
            # Linux may autobind an unnamed AF_UNIX endpoint on the first
            # credentialled send.  Freeze the stable post-probe name.
            fact["peer_name_repr"] = repr(endpoint.getpeername())
            fact["bidirectional_pair_probe_sha256"] = pair_proof
            fact["queues_empty_after_pair_probe"] = True
        return facts[0], facts[1]
    except OSError as error:
        raise ConstructionK7H1SupervisorV2PreboundCloneV1Error(
            "V20 child gate descriptors are not one live bidirectional socketpair"
        ) from error
    finally:
        if peer is not None:
            peer.close()
        if child is not None:
            child.close()


def _descriptor_facts(
    creator_pid_cell_fd: int,
    child_gate_fd: int,
    child_gate_peer_fd: int,
    supervisor_executable_fd: int,
) -> list[dict[str, Any]]:
    descriptors = (
        creator_pid_cell_fd,
        child_gate_fd,
        child_gate_peer_fd,
        supervisor_executable_fd,
    )
    if len(set(descriptors)) != 4:
        _fail("V20 prebound descriptor numbers overlap")

    pid_fact = _fd_common(creator_pid_cell_fd, role="creator_pid_cell_fd")
    pid_status = _RAW_OS_FSTAT(creator_pid_cell_fd)
    pid_access = _RAW_FCNTL(creator_pid_cell_fd, fcntl.F_GETFL) & os.O_ACCMODE
    try:
        pid_seals = _RAW_FCNTL(creator_pid_cell_fd, fcntl.F_GET_SEALS)
    except OSError as error:
        raise ConstructionK7H1SupervisorV2PreboundCloneV1Error(
            "V20 creator PID cell is not a sealable memfd"
        ) from error
    if (
        not stat.S_ISREG(pid_status.st_mode)
        or pid_status.st_size != PID_CELL_BYTES
        or pid_access != os.O_RDWR
        or pid_seals != 0
        or _RAW_OS_PREAD(creator_pid_cell_fd, PID_CELL_BYTES + 1, 0)
        != bytes(PID_CELL_BYTES)
        or not _RAW_OS_READLINK(f"/proc/self/fd/{creator_pid_cell_fd}").startswith(
            "/memfd:"
        )
    ):
        _fail("V20 creator PID cell is not one pristine writable unsealed page")
    pid_fact.update(
        {
            "fd_kind": "PRISTINE_WRITABLE_PID_CELL_MEMFD",
            "access_mode": "O_RDWR",
            "seals": 0,
            "sha256": _RAW_SHA256(bytes(PID_CELL_BYTES)).hexdigest(),
        }
    )

    gate_fact, gate_peer_fact = _socket_pair_facts(
        child_gate_fd, child_gate_peer_fd
    )

    role_fact = _fd_common(
        supervisor_executable_fd, role="supervisor_executable_fd"
    )
    role_status = _RAW_OS_FSTAT(supervisor_executable_fd)
    try:
        role_seals = _RAW_FCNTL(supervisor_executable_fd, fcntl.F_GET_SEALS)
    except OSError as error:
        raise ConstructionK7H1SupervisorV2PreboundCloneV1Error(
            "V20 SUPERVISOR-V2 executable is not a sealed memfd"
        ) from error
    role_raw = _RAW_OS_PREAD(
        supervisor_executable_fd, _SUPERVISOR_V2_ELF_BYTE_COUNT + 1, 0
    )
    if (
        not stat.S_ISREG(role_status.st_mode)
        or role_status.st_size != _SUPERVISOR_V2_ELF_BYTE_COUNT
        or role_seals != REQUIRED_ROLE_SEALS
        or role_raw != _SUPERVISOR_V2_ELF_BYTES
        or _RAW_SHA256(role_raw).hexdigest() != _SUPERVISOR_V2_ELF_SHA256
    ):
        _fail("V20 SUPERVISOR-V2 executable identity changed")
    role_fact.update(
        {
            "fd_kind": "SEALED_EXACT_SUPERVISOR_V2_ELF_MEMFD",
            "seals": role_seals,
            "sha256": _SUPERVISOR_V2_ELF_SHA256,
        }
    )

    identities = {
        (row["device"], row["inode"])
        for row in (pid_fact, gate_fact, gate_peer_fact, role_fact)
    }
    if len(identities) != 4:
        _fail("V20 prebound descriptor kernel identities overlap")
    return [pid_fact, gate_fact, gate_peer_fact, role_fact]


def _owned_fd_identity(
    role: str, descriptor: int
) -> tuple[str, int, int, int, int]:
    status = _RAW_OS_FSTAT(descriptor)
    return (role, descriptor, status.st_dev, status.st_ino, status.st_mode)


def _duplicate_into_pending(
    pending: _PendingResourcesV1,
    *,
    role: str,
    source_fd: int,
    minimum: int,
) -> int:
    descriptor = -1
    try:
        descriptor = int(_RAW_FCNTL(source_fd, fcntl.F_DUPFD_CLOEXEC, minimum))
        identity = _owned_fd_identity(role, descriptor)
        pending.owned_fds.append(identity)
        return descriptor
    except BaseException:
        if descriptor >= 0:
            try:
                _RAW_OS_CLOSE(descriptor)
            except OSError:
                pass
        raise


def _identity_safe_close_row(
    identity: tuple[str, int, int, int, int]
) -> dict[str, Any]:
    role, descriptor, expected_device, expected_inode, expected_mode = identity
    try:
        status = _RAW_OS_FSTAT(descriptor)
    except OSError as error:
        if error.errno != errno.EBADF:
            return {
                "role": role,
                "capsule_owned_resource_closed_or_absent": False,
                "descriptor_closed_by_module": False,
                "errno": error.errno,
            }
        return {
            "role": role,
            "capsule_owned_resource_closed_or_absent": True,
            "descriptor_closed_by_module": False,
            "already_absent": True,
        }
    if (
        status.st_dev,
        status.st_ino,
        status.st_mode,
    ) != (expected_device, expected_inode, expected_mode):
        return {
            "role": role,
            "capsule_owned_resource_closed_or_absent": True,
            "descriptor_closed_by_module": False,
            "different_kernel_identity_reuse_detected": True,
            "replacement_descriptor_left_open": True,
        }
    try:
        _RAW_OS_CLOSE(descriptor)
    except OSError as error:
        return {
            "role": role,
            "capsule_owned_resource_closed_or_absent": error.errno == errno.EBADF,
            "descriptor_closed_by_module": False,
            "errno": error.errno,
        }
    return {
        "role": role,
        "capsule_owned_resource_closed_or_absent": True,
        "descriptor_closed_by_module": True,
    }


def _close_pending_resources(pending: _PendingResourcesV1) -> list[dict[str, Any]]:
    mapping = pending.creator_mapping
    if mapping is not None:
        role = "creator_pid_cell_mapping"
        if role not in pending.close_rows or not pending.close_rows[role].get(
            "capsule_owned_resource_closed_or_absent", False
        ):
            if mapping.closed:
                pending.close_rows[role] = {
                    "role": role,
                    "capsule_owned_resource_closed_or_absent": True,
                    "descriptor_closed_by_module": False,
                    "already_absent": True,
                }
            else:
                try:
                    mapping.close()
                except BaseException as error:
                    pending.close_rows[role] = {
                        "role": role,
                        "capsule_owned_resource_closed_or_absent": False,
                        "descriptor_closed_by_module": False,
                        "error_type": type(error).__name__,
                    }
                else:
                    pending.close_rows[role] = {
                        "role": role,
                        "capsule_owned_resource_closed_or_absent": True,
                        "descriptor_closed_by_module": True,
                    }
    for identity in tuple(pending.owned_fds):
        role = identity[0]
        if role not in pending.close_rows or not pending.close_rows[role].get(
            "capsule_owned_resource_closed_or_absent", False
        ):
            pending.close_rows[role] = _identity_safe_close_row(identity)
    ordered_roles = (
        *(("creator_pid_cell_mapping",) if mapping is not None else ()),
        *(identity[0] for identity in pending.owned_fds),
    )
    return [_deep_copy(pending.close_rows[role]) for role in ordered_roles]


def _pending_resources_closed(pending: _PendingResourcesV1) -> bool:
    required_roles = {identity[0] for identity in pending.owned_fds}
    if pending.creator_mapping is not None:
        required_roles.add("creator_pid_cell_mapping")
    return set(pending.close_rows) >= required_roles and all(
        pending.close_rows[role].get(
            "capsule_owned_resource_closed_or_absent", False
        )
        is True
        for role in required_roles
    )


def _recover_precommit_resources() -> None:
    """Finish forward every anonymous failed preparation before new work."""

    for token, pending in tuple(_PRECOMMIT.items()):
        if pending.live_handle is not None:
            _LIVE.pop(pending.live_handle, None)
            _CLOSING.pop(pending.live_handle, None)
        _close_pending_resources(pending)
        if not _pending_resources_closed(pending):
            _fail("V20 prior precommit cleanup remains incomplete")
        _PRECOMMIT.pop(token, None)


def _frame_fact(raw: bytes, *, role: str) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_FRAME_BYTES:
        _fail(f"V20 {role} frame is absent or exceeds the native cap")
    return {
        "role": role,
        "byte_count": len(raw),
        "sha256": _RAW_SHA256(raw).hexdigest(),
    }


class H1SupervisorV2PreboundNativeCloneV1:
    """Opaque exact-identity capsule; it contains no public capability field."""

    __slots__ = ()

    def __new__(cls, issuer: object = None) -> "H1SupervisorV2PreboundNativeCloneV1":
        if cls is not H1SupervisorV2PreboundNativeCloneV1 or issuer is not _ISSUER:
            _fail("V20 prebound capsule construction is issuer-only")
        return super().__new__(cls)

    def __copy__(self) -> NoReturn:
        _fail("V20 prebound capsule cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("V20 prebound capsule cannot be deep-copied")

    def __reduce__(self) -> NoReturn:
        _fail("V20 prebound capsule cannot be serialized")

    def __reduce_ex__(self, _protocol: int) -> NoReturn:
        _fail("V20 prebound capsule cannot be serialized")


@dataclass(slots=True)
class _PendingResourcesV1:
    owned_fds: list[tuple[str, int, int, int, int]]
    creator_mapping: mmap.mmap | None = field(default=None, repr=False)
    close_rows: dict[str, dict[str, Any]] = field(default_factory=dict)
    live_handle: Any = field(default=None, repr=False)


@dataclass(slots=True)
class _CleanupProgressV1:
    rows: dict[str, dict[str, Any]]


@dataclass(frozen=True, slots=True)
class _LiveCapsuleRecordV1:
    handle: H1SupervisorV2PreboundNativeCloneV1 = field(repr=False)
    owner_pid: int
    owner_process_start_ticks: int
    owner_thread: threading.Thread = field(repr=False)
    owner_thread_id: int
    owner_native_thread_id: int
    creator_pid_cell_fd: int
    child_gate_fd: int
    child_gate_peer_fd: int
    supervisor_executable_fd: int
    creator_mapping: mmap.mmap = field(repr=False)
    creator_mapping_address: int
    pidfd_cell: Any = field(repr=False)
    clone_args: Any = field(repr=False)
    parent_edge: Any = field(repr=False)
    cell_buffer: Any = field(repr=False)
    gate_buffer: Any = field(repr=False)
    release_buffer: Any = field(repr=False)
    argv0_buffer: Any = field(repr=False)
    argv: Any = field(repr=False)
    envp: Any = field(repr=False)
    launch_args: Any = field(repr=False)
    launch_args_pointer: Any = field(repr=False)
    frames: tuple[bytes, bytes, bytes] = field(repr=False)
    fd_facts_bytes: bytes = field(repr=False)
    owned_fd_identities: tuple[tuple[str, int, int, int, int], ...]
    source_document_bytes: bytes = field(repr=False)
    source_document_sha256: str
    source_closure_id: str
    capsule_document_bytes: bytes = field(repr=False)
    capsule_document_sha256: str
    capsule_id: str


@dataclass(frozen=True, slots=True)
class _CloseOutcomeV1:
    role: str
    outcome: str
    errno_value: int | None = None


@dataclass(frozen=True, slots=True)
class _TerminalCancellationRecordV1:
    """Trusted replay state retaining the exact closed live-record identity."""

    issuer: object = field(repr=False)
    handle: H1SupervisorV2PreboundNativeCloneV1 = field(repr=False)
    live_record: _LiveCapsuleRecordV1 = field(repr=False)
    owner: tuple[int, int, threading.Thread, int, int] = field(repr=False)
    document_bytes: bytes = field(repr=False)
    document_sha256: str
    cancellation_id: str
    parent_capsule_id: str
    close_outcomes: tuple[_CloseOutcomeV1, ...]
    input_integrity_valid_before_cleanup: bool
    historical_input_integrity_valid: bool


def _make_terminal_replay_anchor_store(
    *,
    handle_type: type[H1SupervisorV2PreboundNativeCloneV1],
    error_type: type[Exception],
    errno_ebadf: int,
) -> tuple[Any, Any, Any, Any, Any]:
    """Keep terminal history in a closure-private, append-only per-handle map."""

    missing = object()
    ordered_roles = (
        "creator_pid_cell_mapping",
        "creator_pid_cell_fd",
        "child_gate_fd",
        "child_gate_peer_fd",
        "supervisor_executable_fd",
    )
    anchors: dict[
        H1SupervisorV2PreboundNativeCloneV1,
        tuple[
            str,
            bool | None,
            tuple[tuple[str, str, int | None], ...] | None,
        ],
    ] = {}

    def bind_issuance_parent(
        handle: H1SupervisorV2PreboundNativeCloneV1,
        parent_capsule_id: str,
    ) -> None:
        if (
            type(handle) is not handle_type
            or type(parent_capsule_id) is not str
            or len(parent_capsule_id) != 64
        ):
            raise error_type("V20 issuance parent anchor input changed")
        existing = anchors.get(handle, missing)
        if existing is missing:
            anchors[handle] = (parent_capsule_id, None, None)
        elif existing != (parent_capsule_id, None, None):
            raise error_type("V20 issuance parent anchor changed")

    def bind_history(
        handle: H1SupervisorV2PreboundNativeCloneV1,
        parent_capsule_id: str,
        input_integrity_valid: bool,
    ) -> tuple[str, bool]:
        if (
            type(handle) is not handle_type
            or type(parent_capsule_id) is not str
            or len(parent_capsule_id) != 64
            or type(input_integrity_valid) is not bool
        ):
            raise error_type("V20 terminal history anchor input changed")
        existing = anchors.get(handle, missing)
        if existing is missing:
            raise error_type("V20 issuance parent anchor is absent")
        if existing[1] is None:
            anchors[handle] = (existing[0], input_integrity_valid, existing[2])
            return existing[0], input_integrity_valid
        # A retry after cleanup began must retain the first pre-cleanup result,
        # even though its now-closed descriptors cannot pass live verification.
        return existing[0], existing[1]

    def bind_close_outcomes(
        handle: H1SupervisorV2PreboundNativeCloneV1,
        values: tuple[tuple[str, str, int | None], ...],
    ) -> tuple[tuple[str, str, int | None], ...]:
        if (
            type(handle) is not handle_type
            or type(values) is not tuple
            or len(values) != len(ordered_roles)
        ):
            raise error_type("V20 terminal close-outcome anchor input changed")
        normalized: list[tuple[str, str, int | None]] = []
        for role, value in zip(ordered_roles, values, strict=True):
            if type(value) is not tuple or len(value) != 3 or value[0] != role:
                raise error_type("V20 terminal close-outcome anchor schema changed")
            outcome = value[1]
            errno_value = value[2]
            if type(outcome) is not str or (
                errno_value is not None and type(errno_value) is not int
            ):
                raise error_type("V20 terminal close-outcome anchor type changed")
            if (
                (outcome in {"CLOSED_BY_MODULE", "ALREADY_ABSENT"} and errno_value is None)
                or (
                    role != "creator_pid_cell_mapping"
                    and outcome == "DIFFERENT_KERNEL_IDENTITY_LEFT_OPEN"
                    and errno_value is None
                )
                or (
                    role != "creator_pid_cell_mapping"
                    and outcome == "CLOSE_REPORTED_EBADF"
                    and errno_value == errno_ebadf
                )
            ):
                normalized.append((role, outcome, errno_value))
            else:
                raise error_type("V20 terminal close-outcome anchor value changed")
        if len(normalized) != len(ordered_roles):
            raise error_type("V20 terminal close-outcome anchor inventory changed")
        frozen_values = tuple(normalized)
        existing = anchors.get(handle, missing)
        if existing is missing or existing[1] is None:
            raise error_type("V20 terminal history anchor is absent")
        if existing[2] is None:
            anchors[handle] = (existing[0], existing[1], frozen_values)
            return frozen_values
        if existing[2] != frozen_values:
            raise error_type("V20 terminal close-outcome history changed")
        return existing[2]

    def require_anchor(
        handle: H1SupervisorV2PreboundNativeCloneV1,
    ) -> tuple[str, bool, tuple[tuple[str, str, int | None], ...]]:
        existing = anchors.get(handle, missing)
        if existing is missing or type(existing[1]) is not bool or existing[2] is None:
            raise error_type("V20 terminal replay anchor is absent")
        return existing[0], existing[1], existing[2]

    def clear_anchors_after_fork() -> None:
        anchors.clear()

    return (
        bind_issuance_parent,
        bind_history,
        bind_close_outcomes,
        require_anchor,
        clear_anchors_after_fork,
    )


(
    _BIND_TERMINAL_ISSUANCE_PARENT_ANCHOR,
    _BIND_TERMINAL_HISTORY_ANCHOR,
    _BIND_TERMINAL_CLOSE_OUTCOMES_ANCHOR,
    _REQUIRE_TERMINAL_REPLAY_ANCHOR,
    _CLEAR_TERMINAL_REPLAY_ANCHORS_AFTER_FORK,
) = _make_terminal_replay_anchor_store(
    handle_type=H1SupervisorV2PreboundNativeCloneV1,
    error_type=ConstructionK7H1SupervisorV2PreboundCloneV1Error,
    errno_ebadf=errno.EBADF,
)


def _require(
    handle: H1SupervisorV2PreboundNativeCloneV1,
) -> _LiveCapsuleRecordV1:
    if type(handle) is not H1SupervisorV2PreboundNativeCloneV1:
        _fail("V20 operation requires the exact capsule type")
    record = _LIVE.get(handle)
    if record is None or record.handle is not handle:
        _fail("V20 prebound capsule is not live in trusted ownership")
    capsule_document = _document_from_bytes(
        record.capsule_document_bytes, label="V20 prebound capsule"
    )
    expected_owner = {
        "pid": record.owner_pid,
        "process_start_ticks": record.owner_process_start_ticks,
        "thread_id": record.owner_thread_id,
        "native_thread_id": record.owner_native_thread_id,
    }
    if (
        record.owner_pid != os.getpid()
        or record.owner_process_start_ticks != _process_start_ticks(os.getpid())
        or record.owner_thread is not threading.current_thread()
        or record.owner_thread_id != threading.get_ident()
        or record.owner_native_thread_id != threading.get_native_id()
        or capsule_document.get("owner_identity") != expected_owner
    ):
        _fail("V20 prebound capsule crossed owner process or thread")
    return record


def _verify_record(
    record: _LiveCapsuleRecordV1,
    _expectation_anchor: Any = _VERIFY_IMPORT_TIME_EXPECTATION_ANCHOR,
) -> dict[str, Any]:
    source_document_builder, capsule_document_builder = _expectation_anchor()
    source_rows = _validate_source_and_code_closure()
    _verify_native_abi_and_images()
    fd_facts = _descriptor_facts(
        record.creator_pid_cell_fd,
        record.child_gate_fd,
        record.child_gate_peer_fd,
        record.supervisor_executable_fd,
    )
    frozen_fd_facts = _LOADS_CANONICAL_JSON(record.fd_facts_bytes)
    if (
        type(frozen_fd_facts) is not list
        or _CANONICAL_JSON_BYTES(frozen_fd_facts) != record.fd_facts_bytes
        or fd_facts != frozen_fd_facts
    ):
        _fail("V20 prebound descriptor identity changed")
    role_to_fd = {
        "creator_pid_cell_fd": record.creator_pid_cell_fd,
        "child_gate_fd": record.child_gate_fd,
        "child_gate_peer_fd": record.child_gate_peer_fd,
        "supervisor_executable_fd": record.supervisor_executable_fd,
    }
    observed_owned_identities = tuple(
        (
            row["role"],
            role_to_fd[row["role"]],
            row["device"],
            row["inode"],
            row["mode"],
        )
        for row in fd_facts
    )
    if observed_owned_identities != record.owned_fd_identities:
        _fail("V20 prebound owned descriptor authority changed")
    if (
        int(record.pidfd_cell.value) != -1
        or int(record.clone_args.flags) != REQUIRED_CLONE_FLAGS
        or int(record.clone_args.pidfd) != ctypes.addressof(record.pidfd_cell)
        or int(record.clone_args.child_tid) != 0
        or int(record.clone_args.parent_tid) != record.creator_mapping_address
        or int(record.clone_args.exit_signal) != int(signal.SIGCHLD)
        or int(record.clone_args.stack) != 0
        or int(record.clone_args.stack_size) != 0
        or int(record.clone_args.tls) != 0
        or int(record.clone_args.set_tid) != 0
        or int(record.clone_args.set_tid_size) != 0
        or int(record.clone_args.cgroup) != 0
        or tuple(
            int(getattr(record.parent_edge, name))
            for name in (
                "clone_result",
                "status_bits",
                "first_cleanup_error",
                "reserved_zero",
            )
        )
        != (0, 0, 0, 0)
    ):
        _fail("V20 prebound clone template changed before activation")
    cell, gate, release = record.frames
    observed_frames = (
        bytes(record.cell_buffer),
        bytes(record.gate_buffer),
        bytes(record.release_buffer),
    )
    observed_frame_facts = [
        _frame_fact(raw, role=role)
        for raw, role in zip(
            observed_frames,
            ("cell_withdrawn_frame", "gate_ready_frame", "release_frame"),
            strict=True,
        )
    ]
    argv_values = ctypes.cast(
        record.argv, ctypes.POINTER(ctypes.c_void_p)
    )
    envp_values = ctypes.cast(
        record.envp, ctypes.POINTER(ctypes.c_void_p)
    )
    if (
        observed_frames != (cell, gate, release)
        or bytes(record.argv0_buffer) != _ARGV0_BYTES
        or int(argv_values[0] or 0) != ctypes.addressof(record.argv0_buffer)
        or int(argv_values[1] or 0) != 0
        or int(envp_values[0] or 0) != 0
        or ctypes.addressof(record.launch_args_pointer.contents)
        != ctypes.addressof(record.launch_args)
        or ctypes.addressof(ctypes.c_char.from_buffer(record.creator_mapping))
        != record.creator_mapping_address
        or int(record.launch_args.clone_args) != ctypes.addressof(record.clone_args)
        or int(record.launch_args.creator_pid_cell_mapping)
        != record.creator_mapping_address
        or int(record.launch_args.pid_cell_mapping_bytes) != PID_CELL_BYTES
        or int(record.launch_args.creator_pid_cell_fd)
        != record.creator_pid_cell_fd
        or int(record.launch_args.one_shot_cgroup_grant_fd) != -1
        or int(record.launch_args.child_gate_fd) != record.child_gate_fd
        or int(record.launch_args.parent_edge) != ctypes.addressof(record.parent_edge)
        or int(record.launch_args.cell_withdrawn_frame)
        != ctypes.addressof(record.cell_buffer)
        or int(record.launch_args.cell_withdrawn_frame_bytes) != len(cell)
        or int(record.launch_args.gate_ready_frame)
        != ctypes.addressof(record.gate_buffer)
        or int(record.launch_args.gate_ready_frame_bytes) != len(gate)
        or int(record.launch_args.release_frame)
        != ctypes.addressof(record.release_buffer)
        or int(record.launch_args.release_frame_bytes) != len(release)
        or int(record.launch_args.supervisor_executable_fd)
        != record.supervisor_executable_fd
        or int(record.launch_args.supervisor_argv) != ctypes.addressof(record.argv)
        or int(record.launch_args.supervisor_envp) != ctypes.addressof(record.envp)
    ):
        _fail("V20 native launch pointer graph changed")
    if (
        type(record.source_document_sha256) is not str
        or type(record.capsule_document_sha256) is not str
        or type(record.source_closure_id) is not str
        or len(record.source_closure_id) != 64
        or type(record.capsule_id) is not str
        or len(record.capsule_id) != 64
        or _RAW_SHA256(record.source_document_bytes).hexdigest()
        != record.source_document_sha256
        or _RAW_SHA256(record.capsule_document_bytes).hexdigest()
        != record.capsule_document_sha256
    ):
        _fail("V20 prebound authoritative document bytes changed")
    source_document = _document_from_bytes(
        record.source_document_bytes, label="V20 prebound source closure"
    )
    capsule_document = _document_from_bytes(
        record.capsule_document_bytes, label="V20 prebound capsule"
    )
    source_id = _verify_id(
        source_document,
        domain=(
            domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_SOURCE_CLOSURE_V1_DOMAIN
        ),
        id_field="prebound_native_edge_source_closure_id",
        label="V20 prebound source closure",
    )
    capsule_id = _verify_id(
        capsule_document,
        domain=(
            domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_CAPSULE_V1_DOMAIN
        ),
        id_field="prebound_native_edge_capsule_id",
        label="V20 prebound capsule",
    )
    expected_source_document = source_document_builder(source_rows)
    expected_capsule_document = capsule_document_builder(
        source_closure_id=expected_source_document[
            "prebound_native_edge_source_closure_id"
        ],
        owner_pid=record.owner_pid,
        owner_process_start_ticks=record.owner_process_start_ticks,
        owner_thread_id=record.owner_thread_id,
        owner_native_thread_id=record.owner_native_thread_id,
        fd_facts=fd_facts,
        source_fd_facts=fd_facts,
        frame_facts=observed_frame_facts,
    )
    if (
        source_id != record.source_closure_id
        or capsule_id != record.capsule_id
        or source_document != expected_source_document
        or capsule_document != expected_capsule_document
        or record.source_document_bytes
        != _CANONICAL_JSON_BYTES(expected_source_document)
        or record.capsule_document_bytes
        != _CANONICAL_JSON_BYTES(expected_capsule_document)
    ):
        _fail("V20 exact regenerated prebound document changed")
    return _deep_copy(capsule_document)


def prepare_h1_supervisor_v2_prebound_native_clone_v1(
    *,
    creator_pid_cell_fd: int,
    child_gate_fd: int,
    child_gate_peer_fd: int,
    supervisor_executable_fd: int,
    cell_withdrawn_frame: bytes,
    gate_ready_frame: bytes,
    release_frame: bytes,
) -> H1SupervisorV2PreboundNativeCloneV1:
    """Borrow four FDs, own exact duplicates, and freeze non-grant inputs."""

    token = object()
    pending = _PendingResourcesV1(owned_fds=[])
    handle: H1SupervisorV2PreboundNativeCloneV1 | None = None
    with _LOCK:
        _recover_precommit_resources()
        if _LIVE or _CLOSING or _PRECOMMIT:
            _fail("V20 permits only one live or precommitting native edge")
        _PRECOMMIT[token] = pending
        try:
            source_rows = _validate_source_and_code_closure()
            _verify_native_abi_and_images()
            owner_pid, owner_thread, owner_thread_id, owner_native_thread_id = (
                _owner_thread_identity()
            )
            owner_start = _process_start_ticks(owner_pid)
            input_fd_facts = _descriptor_facts(
                creator_pid_cell_fd,
                child_gate_fd,
                child_gate_peer_fd,
                supervisor_executable_fd,
            )
            frame_facts = [
                _frame_fact(cell_withdrawn_frame, role="cell_withdrawn_frame"),
                _frame_fact(gate_ready_frame, role="gate_ready_frame"),
                _frame_fact(release_frame, role="release_frame"),
            ]
            if len({row["sha256"] for row in frame_facts}) != 3:
                _fail("V20 protocol frames are not three distinct bindings")

            owned_pid_cell_fd = _duplicate_into_pending(
                pending,
                role="creator_pid_cell_fd",
                source_fd=creator_pid_cell_fd,
                minimum=5,
            )
            owned_child_gate_fd = _duplicate_into_pending(
                pending,
                role="child_gate_fd",
                source_fd=child_gate_fd,
                minimum=CHILD_GATE_SOURCE_FD_MINIMUM,
            )
            owned_child_gate_peer_fd = _duplicate_into_pending(
                pending,
                role="child_gate_peer_fd",
                source_fd=child_gate_peer_fd,
                minimum=CHILD_GATE_PEER_SOURCE_FD_MINIMUM,
            )
            owned_role_fd = _duplicate_into_pending(
                pending,
                role="supervisor_executable_fd",
                source_fd=supervisor_executable_fd,
                minimum=EXECUTABLE_SOURCE_FD_MINIMUM,
            )
            fd_facts = _descriptor_facts(
                owned_pid_cell_fd,
                owned_child_gate_fd,
                owned_child_gate_peer_fd,
                owned_role_fd,
            )
            if fd_facts != input_fd_facts:
                _fail("V20 private duplicates changed input kernel identities")
            pending.creator_mapping = mmap.mmap(
                owned_pid_cell_fd,
                PID_CELL_BYTES,
                flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
            )
            creator_mapping = pending.creator_mapping
            creator_mapping_address = ctypes.addressof(
                ctypes.c_char.from_buffer(creator_mapping)
            )
            pidfd_cell = ctypes.c_int(-1)
            clone_args = _CLONE_ARGS_TYPE(
                flags=REQUIRED_CLONE_FLAGS,
                pidfd=ctypes.addressof(pidfd_cell),
                child_tid=0,
                parent_tid=creator_mapping_address,
                exit_signal=int(signal.SIGCHLD),
                stack=0,
                stack_size=0,
                tls=0,
                set_tid=0,
                set_tid_size=0,
                cgroup=0,
            )
            parent_edge = _PARENT_EDGE_TYPE(0, 0, 0, 0)
            cell_buffer = ctypes.create_string_buffer(
                cell_withdrawn_frame, len(cell_withdrawn_frame)
            )
            gate_buffer = ctypes.create_string_buffer(
                gate_ready_frame, len(gate_ready_frame)
            )
            release_buffer = ctypes.create_string_buffer(
                release_frame, len(release_frame)
            )
            argv0_buffer = ctypes.create_string_buffer(
                _ARGV0_BYTES, len(_ARGV0_BYTES)
            )
            argv = (ctypes.c_char_p * 2)(
                ctypes.cast(argv0_buffer, ctypes.c_char_p), None
            )
            envp = (ctypes.c_char_p * 1)(None)
            launch_args = _LAUNCH_ARGS_TYPE(
                clone_args=ctypes.addressof(clone_args),
                creator_pid_cell_mapping=creator_mapping_address,
                pid_cell_mapping_bytes=PID_CELL_BYTES,
                creator_pid_cell_fd=owned_pid_cell_fd,
                one_shot_cgroup_grant_fd=-1,
                child_gate_fd=owned_child_gate_fd,
                parent_edge=ctypes.addressof(parent_edge),
                cell_withdrawn_frame=ctypes.addressof(cell_buffer),
                cell_withdrawn_frame_bytes=len(cell_withdrawn_frame),
                gate_ready_frame=ctypes.addressof(gate_buffer),
                gate_ready_frame_bytes=len(gate_ready_frame),
                release_frame=ctypes.addressof(release_buffer),
                release_frame_bytes=len(release_frame),
                supervisor_executable_fd=owned_role_fd,
                supervisor_argv=ctypes.addressof(argv),
                supervisor_envp=ctypes.addressof(envp),
            )
            source_document = _source_closure_document(source_rows)
            capsule_document = _capsule_document(
                source_closure_id=source_document[
                    "prebound_native_edge_source_closure_id"
                ],
                owner_pid=owner_pid,
                owner_process_start_ticks=owner_start,
                owner_thread_id=owner_thread_id,
                owner_native_thread_id=owner_native_thread_id,
                fd_facts=fd_facts,
                source_fd_facts=input_fd_facts,
                frame_facts=frame_facts,
            )
            source_document_bytes = _document_bytes(source_document)
            capsule_document_bytes = _document_bytes(capsule_document)
            handle = H1SupervisorV2PreboundNativeCloneV1(_ISSUER)
            record = _LiveCapsuleRecordV1(
                handle=handle,
                owner_pid=owner_pid,
                owner_process_start_ticks=owner_start,
                owner_thread=owner_thread,
                owner_thread_id=owner_thread_id,
                owner_native_thread_id=owner_native_thread_id,
                creator_pid_cell_fd=owned_pid_cell_fd,
                child_gate_fd=owned_child_gate_fd,
                child_gate_peer_fd=owned_child_gate_peer_fd,
                supervisor_executable_fd=owned_role_fd,
                creator_mapping=creator_mapping,
                creator_mapping_address=creator_mapping_address,
                pidfd_cell=pidfd_cell,
                clone_args=clone_args,
                parent_edge=parent_edge,
                cell_buffer=cell_buffer,
                gate_buffer=gate_buffer,
                release_buffer=release_buffer,
                argv0_buffer=argv0_buffer,
                argv=argv,
                envp=envp,
                launch_args=launch_args,
                launch_args_pointer=ctypes.pointer(launch_args),
                frames=(cell_withdrawn_frame, gate_ready_frame, release_frame),
                fd_facts_bytes=_CANONICAL_JSON_BYTES(fd_facts),
                owned_fd_identities=tuple(pending.owned_fds),
                source_document_bytes=source_document_bytes,
                source_document_sha256=_RAW_SHA256(
                    source_document_bytes
                ).hexdigest(),
                source_closure_id=source_document[
                    "prebound_native_edge_source_closure_id"
                ],
                capsule_document_bytes=capsule_document_bytes,
                capsule_document_sha256=_RAW_SHA256(
                    capsule_document_bytes
                ).hexdigest(),
                capsule_id=capsule_document["prebound_native_edge_capsule_id"],
            )
            _verify_record(record)
            _BIND_TERMINAL_ISSUANCE_PARENT_ANCHOR(
                handle,
                record.capsule_id,
            )
            pending.live_handle = handle
            _LIVE[handle] = record
            _PRECOMMIT.pop(token, None)
            return handle
        except BaseException:
            _PRECOMMIT[token] = pending
            if handle is not None:
                pending.live_handle = handle
                _LIVE.pop(handle, None)
                _CLOSING.pop(handle, None)
            _close_pending_resources(pending)
            if _pending_resources_closed(pending):
                _PRECOMMIT.pop(token, None)
            raise


def verify_h1_supervisor_v2_prebound_native_clone_v1(
    handle: H1SupervisorV2PreboundNativeCloneV1,
) -> dict[str, Any]:
    """Replay source, ABI, W^X, owner, FD, pointer graph, and content IDs."""

    with _LOCK:
        return _verify_record(_require(handle))


def execute_h1_supervisor_v2_prebound_native_clone_v1(
    handle: H1SupervisorV2PreboundNativeCloneV1,
    *,
    activation_successor: object,
) -> NoReturn:
    """Fail before native entry until an additive trusted successor exists."""

    raise ConstructionK7H1SupervisorV2PreboundCloneV1Error(
        "V20 Guardian activation successor issuer is absent; native entry was not invoked"
    )


def _record_owner_tuple(
    record: _LiveCapsuleRecordV1,
) -> tuple[int, int, threading.Thread, int, int]:
    return (
        record.owner_pid,
        record.owner_process_start_ticks,
        record.owner_thread,
        record.owner_thread_id,
        record.owner_native_thread_id,
    )


def _require_owner_tuple(
    owner: tuple[int, int, threading.Thread, int, int],
) -> None:
    if (
        owner[0] != os.getpid()
        or owner[1] != _process_start_ticks(os.getpid())
        or owner[2] is not threading.current_thread()
        or owner[3] != threading.get_ident()
        or owner[4] != threading.get_native_id()
    ):
        _fail("V20 terminal capsule crossed owner process or thread")


def _close_record_resources(
    record: _LiveCapsuleRecordV1,
    progress: _CleanupProgressV1,
) -> list[dict[str, Any]]:
    mapping_role = "creator_pid_cell_mapping"
    if (
        mapping_role not in progress.rows
        or not progress.rows[mapping_role].get(
            "capsule_owned_resource_closed_or_absent", False
        )
    ):
        if record.creator_mapping.closed:
            progress.rows[mapping_role] = {
                "role": mapping_role,
                "capsule_owned_resource_closed_or_absent": True,
                "descriptor_closed_by_module": False,
                "already_absent": True,
            }
        else:
            try:
                record.creator_mapping.close()
            except BaseException as error:  # pragma: no cover - platform edge
                progress.rows[mapping_role] = {
                    "role": mapping_role,
                    "capsule_owned_resource_closed_or_absent": False,
                    "descriptor_closed_by_module": False,
                    "error_type": type(error).__name__,
                }
            else:
                progress.rows[mapping_role] = {
                    "role": mapping_role,
                    "capsule_owned_resource_closed_or_absent": True,
                    "descriptor_closed_by_module": True,
                }
    for identity in record.owned_fd_identities:
        role = identity[0]
        if role not in progress.rows or not progress.rows[role].get(
            "capsule_owned_resource_closed_or_absent", False
        ):
            progress.rows[role] = _identity_safe_close_row(identity)
    ordered_roles = (
        mapping_role,
        "creator_pid_cell_fd",
        "child_gate_fd",
        "child_gate_peer_fd",
        "supervisor_executable_fd",
    )
    rows = [_deep_copy(progress.rows[role]) for role in ordered_roles]
    for row in rows:
        row["closed"] = row["capsule_owned_resource_closed_or_absent"]
    return rows


def _close_outcomes_from_rows(
    close_rows: list[dict[str, Any]],
) -> tuple[_CloseOutcomeV1, ...]:
    ordered_roles = (
        "creator_pid_cell_mapping",
        "creator_pid_cell_fd",
        "child_gate_fd",
        "child_gate_peer_fd",
        "supervisor_executable_fd",
    )
    if type(close_rows) is not list or len(close_rows) != len(ordered_roles):
        _fail("V20 terminal close-row inventory changed")
    outcomes: list[_CloseOutcomeV1] = []
    for role, row in zip(ordered_roles, close_rows, strict=True):
        common = {
            "role": role,
            "capsule_owned_resource_closed_or_absent": True,
            "closed": True,
        }
        closed_by_module = {**common, "descriptor_closed_by_module": True}
        already_absent = {
            **common,
            "descriptor_closed_by_module": False,
            "already_absent": True,
        }
        different_identity = {
            **common,
            "descriptor_closed_by_module": False,
            "different_kernel_identity_reuse_detected": True,
            "replacement_descriptor_left_open": True,
        }
        close_reported_ebadf = {
            **common,
            "descriptor_closed_by_module": False,
            "errno": errno.EBADF,
        }
        if row == closed_by_module:
            outcome = _CloseOutcomeV1(role, "CLOSED_BY_MODULE")
        elif row == already_absent:
            outcome = _CloseOutcomeV1(role, "ALREADY_ABSENT")
        elif role != "creator_pid_cell_mapping" and row == different_identity:
            outcome = _CloseOutcomeV1(role, "DIFFERENT_KERNEL_IDENTITY_LEFT_OPEN")
        elif role != "creator_pid_cell_mapping" and row == close_reported_ebadf:
            outcome = _CloseOutcomeV1(
                role,
                "CLOSE_REPORTED_EBADF",
                errno.EBADF,
            )
        else:
            _fail(f"V20 terminal close-row schema changed: {role}")
        outcomes.append(outcome)
    return tuple(outcomes)


def _close_outcome_anchor_values(
    outcomes: tuple[_CloseOutcomeV1, ...],
) -> tuple[tuple[str, str, int | None], ...]:
    if type(outcomes) is not tuple or any(
        type(outcome) is not _CloseOutcomeV1 for outcome in outcomes
    ):
        _fail("V20 terminal close-outcome typed record changed")
    return tuple(
        (outcome.role, outcome.outcome, outcome.errno_value)
        for outcome in outcomes
    )


def _close_rows_from_outcomes(
    outcomes: tuple[_CloseOutcomeV1, ...],
) -> list[dict[str, Any]]:
    ordered_roles = (
        "creator_pid_cell_mapping",
        "creator_pid_cell_fd",
        "child_gate_fd",
        "child_gate_peer_fd",
        "supervisor_executable_fd",
    )
    if (
        type(outcomes) is not tuple
        or len(outcomes) != len(ordered_roles)
        or any(type(outcome) is not _CloseOutcomeV1 for outcome in outcomes)
    ):
        _fail("V20 trusted terminal close outcomes changed type")
    rows: list[dict[str, Any]] = []
    for role, outcome in zip(ordered_roles, outcomes, strict=True):
        if outcome.role != role:
            _fail("V20 trusted terminal close-outcome order changed")
        row: dict[str, Any] = {
            "role": role,
            "capsule_owned_resource_closed_or_absent": True,
            "descriptor_closed_by_module": outcome.outcome == "CLOSED_BY_MODULE",
            "closed": True,
        }
        if outcome.outcome == "CLOSED_BY_MODULE" and outcome.errno_value is None:
            pass
        elif outcome.outcome == "ALREADY_ABSENT" and outcome.errno_value is None:
            row["already_absent"] = True
        elif (
            role != "creator_pid_cell_mapping"
            and outcome.outcome == "DIFFERENT_KERNEL_IDENTITY_LEFT_OPEN"
            and outcome.errno_value is None
        ):
            row["different_kernel_identity_reuse_detected"] = True
            row["replacement_descriptor_left_open"] = True
        elif (
            role != "creator_pid_cell_mapping"
            and outcome.outcome == "CLOSE_REPORTED_EBADF"
            and outcome.errno_value == errno.EBADF
        ):
            row["errno"] = errno.EBADF
        else:
            _fail(f"V20 trusted terminal close outcome changed: {role}")
        rows.append(row)
    return rows


def _cancellation_document(
    parent_capsule_id: str,
    *,
    close_rows: list[dict[str, Any]],
    input_integrity_valid_before_cleanup: bool,
) -> dict[str, Any]:
    if type(parent_capsule_id) is not str or len(parent_capsule_id) != 64:
        _fail("V20 trusted prebound capsule identity changed")
    return _with_id(
        {
            "schema": "acfqp.k7_h1_supervisor_v2_prebound_native_edge_cancellation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "prebound_native_edge_capsule_id": parent_capsule_id,
            "state_before": "PREBOUND_NO_ACTIVATION",
            "state_after": "CANCELLED_UNACTIVATED",
            "close_rows": close_rows,
            "all_capsule_owned_resources_closed": all(
                row.get("capsule_owned_resource_closed_or_absent") is True
                for row in close_rows
            ),
            "different_kernel_identity_reused_descriptors_left_open": any(
                row.get("replacement_descriptor_left_open") is True
                for row in close_rows
            ),
            "terminal_replay_is_idempotent": True,
            "input_integrity_valid_before_cleanup": (
                input_integrity_valid_before_cleanup
            ),
            "activation_successor_present": False,
            "permit_consumed": False,
            "native_entry_invoked": False,
            "clone_syscall_performed": False,
            "actual_process_birth_present": False,
            **_claims(),
        },
        domain=(
            domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_CANCELLATION_V1_DOMAIN
        ),
        id_field="prebound_native_edge_cancellation_id",
    )


def _terminal_resources_are_closed(
    record: _LiveCapsuleRecordV1,
    close_rows: Any,
) -> bool:
    if type(close_rows) is not list or len(close_rows) != 5:
        return False
    rows: dict[str, dict[str, Any]] = {}
    for row in close_rows:
        if type(row) is not dict or type(row.get("role")) is not str:
            return False
        role = row["role"]
        if role in rows:
            return False
        if (
            row.get("capsule_owned_resource_closed_or_absent") is not True
            or row.get("closed") is not True
            or type(row.get("descriptor_closed_by_module")) is not bool
        ):
            return False
        rows[role] = row
    expected_roles = {
        "creator_pid_cell_mapping",
        "creator_pid_cell_fd",
        "child_gate_fd",
        "child_gate_peer_fd",
        "supervisor_executable_fd",
    }
    if set(rows) != expected_roles or not record.creator_mapping.closed:
        return False
    for role, descriptor, device, inode, mode in record.owned_fd_identities:
        if role not in rows:
            return False
        try:
            status = _RAW_OS_FSTAT(descriptor)
        except OSError as error:
            if error.errno != errno.EBADF:
                return False
        else:
            # A same-identity descriptor means the capsule-owned open-file
            # reference survived.  A different identity is a later fd-number
            # reuse and must be left untouched by terminal replay.
            if (status.st_dev, status.st_ino, status.st_mode) == (
                device,
                inode,
                mode,
            ):
                return False
    return True


def _verify_terminal_cancellation_record(
    handle: H1SupervisorV2PreboundNativeCloneV1,
    terminal: Any,
    _anchor_reader: Any = _REQUIRE_TERMINAL_REPLAY_ANCHOR,
    _close_outcome_type: Any = _CloseOutcomeV1,
) -> dict[str, Any]:
    if (
        type(terminal) is not _TerminalCancellationRecordV1
        or terminal.issuer is not _ISSUER
        or terminal.handle is not handle
        or terminal.live_record.handle is not handle
    ):
        _fail("V20 terminal cancellation record identity changed")
    _require_owner_tuple(terminal.owner)
    if terminal.owner != _record_owner_tuple(terminal.live_record):
        _fail("V20 terminal cancellation owner binding changed")
    _validate_source_and_code_closure()
    (
        anchored_parent_capsule_id,
        anchored_input_integrity,
        anchored_close_outcome_values,
    ) = _anchor_reader(handle)
    if (
        type(terminal.parent_capsule_id) is not str
        or len(terminal.parent_capsule_id) != 64
        or terminal.parent_capsule_id != anchored_parent_capsule_id
        or (
            anchored_input_integrity
            and terminal.live_record.capsule_id != anchored_parent_capsule_id
        )
    ):
        _fail("V20 terminal parent capsule anchor changed")
    if (
        type(terminal.document_sha256) is not str
        or type(terminal.cancellation_id) is not str
        or len(terminal.cancellation_id) != 64
        or _RAW_SHA256(terminal.document_bytes).hexdigest()
        != terminal.document_sha256
    ):
        _fail("V20 terminal authoritative document bytes changed")
    document = _document_from_bytes(
        terminal.document_bytes, label="V20 terminal cancellation"
    )
    cancellation_id = _verify_id(
        document,
        domain=(
            domains_v20.CONSTRUCTION_K7_H1_SUPERVISOR_V2_PREBOUND_NATIVE_EDGE_CANCELLATION_V1_DOMAIN
        ),
        id_field="prebound_native_edge_cancellation_id",
        label="V20 terminal cancellation",
    )
    if (
        type(terminal.input_integrity_valid_before_cleanup) is not bool
        or type(terminal.historical_input_integrity_valid) is not bool
        or terminal.input_integrity_valid_before_cleanup
        is not anchored_input_integrity
        or terminal.historical_input_integrity_valid is not anchored_input_integrity
        or _close_outcome_anchor_values(terminal.close_outcomes)
        != anchored_close_outcome_values
    ):
        _fail("V20 terminal historical input-integrity anchor changed")
    anchored_close_outcomes = tuple(
        _close_outcome_type(*value) for value in anchored_close_outcome_values
    )
    close_rows = _close_rows_from_outcomes(anchored_close_outcomes)
    if (
        document.get("close_rows") != close_rows
        or not _terminal_resources_are_closed(terminal.live_record, close_rows)
    ):
        _fail("V20 terminal cancellation replay found a live capsule resource")
    expected = _cancellation_document(
        anchored_parent_capsule_id,
        close_rows=close_rows,
        input_integrity_valid_before_cleanup=anchored_input_integrity,
    )
    if (
        cancellation_id != terminal.cancellation_id
        or document.get("prebound_native_edge_capsule_id")
        != anchored_parent_capsule_id
        or expected != document
        or terminal.document_bytes != _CANONICAL_JSON_BYTES(expected)
        or document.get("all_capsule_owned_resources_closed") is not True
    ):
        _fail("V20 terminal cancellation semantics changed")
    return document


def _replay_terminal_cancellation(
    handle: H1SupervisorV2PreboundNativeCloneV1,
) -> dict[str, Any] | None:
    terminal = _TERMINAL.get(handle)
    if terminal is None:
        return None
    document = _verify_terminal_cancellation_record(handle, terminal)
    _LIVE.pop(handle, None)
    _CLOSING.pop(handle, None)
    return _deep_copy(document)


def cancel_h1_supervisor_v2_prebound_native_clone_v1(
    handle: H1SupervisorV2PreboundNativeCloneV1,
) -> dict[str, Any]:
    """Cancel the capsule and close only its private duplicate FDs."""

    primary: BaseException | None = None
    with _LOCK:
        replay = _replay_terminal_cancellation(handle)
        if replay is not None:
            return replay
        record = _require(handle)
        parent_capsule_id = record.capsule_id
        try:
            verified_capsule = _verify_record(record)
            parent_capsule_id = verified_capsule["prebound_native_edge_capsule_id"]
        except BaseException as error:
            primary = error
        (
            anchored_parent_capsule_id,
            anchored_input_integrity,
        ) = _BIND_TERMINAL_HISTORY_ANCHOR(
            handle,
            parent_capsule_id,
            primary is None,
        )
        progress = _CLOSING.setdefault(handle, _CleanupProgressV1(rows={}))
        close_rows = _close_record_resources(record, progress)
        document = _cancellation_document(
            anchored_parent_capsule_id,
            close_rows=close_rows,
            input_integrity_valid_before_cleanup=anchored_input_integrity,
        )
        terminal_bytes = _document_bytes(document)
        if document["all_capsule_owned_resources_closed"] is not True:
            raise ConstructionK7H1SupervisorV2PreboundCloneV1Error(
                "V20 capsule cleanup remains incomplete and retryable",
                cleanup_document=document,
                primary_error=primary,
            ) from primary
        close_outcomes = _close_outcomes_from_rows(close_rows)
        if _close_rows_from_outcomes(close_outcomes) != close_rows:
            _fail("V20 terminal close rows did not round-trip exactly")
        anchored_close_outcome_values = (
            _BIND_TERMINAL_CLOSE_OUTCOMES_ANCHOR(
                handle,
                _close_outcome_anchor_values(close_outcomes),
            )
        )
        if anchored_close_outcome_values != _close_outcome_anchor_values(
            close_outcomes
        ):
            _fail("V20 terminal close-outcome anchor changed")
        terminal = _TerminalCancellationRecordV1(
            issuer=_ISSUER,
            handle=handle,
            live_record=record,
            owner=_record_owner_tuple(record),
            document_bytes=terminal_bytes,
            document_sha256=_RAW_SHA256(terminal_bytes).hexdigest(),
            cancellation_id=document["prebound_native_edge_cancellation_id"],
            parent_capsule_id=anchored_parent_capsule_id,
            close_outcomes=close_outcomes,
            input_integrity_valid_before_cleanup=anchored_input_integrity,
            historical_input_integrity_valid=anchored_input_integrity,
        )
        _verify_terminal_cancellation_record(handle, terminal)
        _TERMINAL[handle] = terminal
        _LIVE.pop(handle, None)
        _CLOSING.pop(handle, None)
    if primary is not None:
        raise ConstructionK7H1SupervisorV2PreboundCloneV1Error(
            "V20 crossed capsule was closed without activation",
            cleanup_document=document,
            primary_error=primary,
        ) from primary
    return _document_from_bytes(
        terminal_bytes, label="V20 terminal cancellation"
    )


def _before_fork() -> None:
    _LOCK.acquire()


def _after_fork_parent() -> None:
    _LOCK.release()


def _after_fork_child(
    _clear_terminal_anchors: Any = _CLEAR_TERMINAL_REPLAY_ANCHORS_AFTER_FORK,
) -> None:
    try:
        records = tuple(_LIVE.values())
        pending_records = tuple(_PRECOMMIT.values())
        _LIVE.clear()
        _PRECOMMIT.clear()
        _CLOSING.clear()
        _TERMINAL.clear()
        _clear_terminal_anchors()
        for record in records:
            _close_pending_resources(
                _PendingResourcesV1(
                    owned_fds=list(record.owned_fd_identities),
                    creator_mapping=record.creator_mapping,
                )
            )
        for pending in pending_records:
            _close_pending_resources(pending)
    finally:
        reinit = getattr(_LOCK, "_at_fork_reinit", None)
        if callable(reinit):
            reinit()


def _freeze_local_callable_closure() -> None:
    global _LOCAL_CALLABLES
    module_globals = globals()
    captured = {
        name: _callable_fact(value)
        for name, value in tuple(module_globals.items())
        if type(value) is FunctionType
        and value.__globals__ is module_globals
        and name not in {"_callable_fact", "_freeze_local_callable_closure"}
    }
    captured["_callable_fact"] = _callable_fact(_callable_fact)
    captured["_freeze_local_callable_closure"] = _callable_fact(
        _freeze_local_callable_closure
    )
    _LOCAL_CALLABLES = MappingProxyType(captured)


_freeze_local_callable_closure()
_SEAL_IMPORT_TIME_EXPECTATION_ANCHOR(_LOCAL_CALLABLES)
os.register_at_fork(
    before=_before_fork,
    after_in_parent=_after_fork_parent,
    after_in_child=_after_fork_child,
)


__all__ = (
    "ACTIVATION_SUCCESSOR_ISSUER_PRESENT",
    "CLONE_SYSCALL_PERFORMED",
    "ConstructionK7H1SupervisorV2PreboundCloneV1Error",
    "H1SupervisorV2PreboundNativeCloneV1",
    "NATIVE_ENTRY_INVOKED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PUBLIC_FAIL_CLOSED_EXECUTE_ENTRY_PRESENT",
    "READINESS",
    "REQUIRED_CLONE_FLAGS",
    "SCHEMA_VERSION",
    "cancel_h1_supervisor_v2_prebound_native_clone_v1",
    "execute_h1_supervisor_v2_prebound_native_clone_v1",
    "prepare_h1_supervisor_v2_prebound_native_clone_v1",
    "verify_h1_supervisor_v2_prebound_native_clone_v1",
)
