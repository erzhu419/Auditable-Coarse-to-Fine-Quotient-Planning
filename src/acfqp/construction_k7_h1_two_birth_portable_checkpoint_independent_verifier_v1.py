"""Independent bytes-only verifier for the V18 two-birth journal.

The verifier consumes canonical record bytes.  It neither imports nor calls
the producer, raw runtime, probe runtime, or native role modules.  Embedded
source bytes are hashed directly and Python callable bindings are replayed by
compiling (but never executing) the corresponding frozen source.

A verified three-record journal remains a durable *observation* only.  A
verified protocol-failure closure remains a typed noncertificate.  Neither
outcome grants a continuation capability, topology authority, accounting
authority, current-access authority, or official execution authority.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import errno
import hashlib
import re
import signal
import socket
import stat
import struct
from types import CodeType, MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.construction_k7_h1_domain_registry_extension_v18 import (
    CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = (
    "construction_k7_h1_two_birth_portable_checkpoint_independent_verifier_v1"
)
PRODUCER_PROFILE_KEY = "construction_k7_h1_two_birth_portable_checkpoint_v1"
READINESS = "INDEPENDENT_DURABLE_NONAUTHORITATIVE_OBSERVATION_VERIFICATION"

SUCCESS_OUTCOME = "DURABLE_NONAUTHORITATIVE_OBSERVATION_VERIFIED"
NONCERTIFICATE_OUTCOME = "TYPED_PROTOCOL_FAILURE_NONCERTIFICATE_VERIFIED"

_SOURCE_SCHEMA = "acfqp.k7_h1_two_birth_execution_source_closure.v1"
_CREDENTIAL_SCHEMA = (
    "acfqp.k7_h1_nested_probe_credential_observation_bundle.v1"
)
_CHECKPOINT_SCHEMA = "acfqp.k7_h1_live_two_birth_prefix_checkpoint.v1"
_FAILURE_SCHEMA = "acfqp.k7_h1_two_birth_protocol_failure_closure.v1"
_LIVE_SCHEMA = "acfqp.k7_h1_two_birth_live_observation.v1"

_SOURCE_ID = "two_birth_execution_source_closure_id"
_CREDENTIAL_ID = "nested_probe_credential_observation_bundle_id"
_CHECKPOINT_ID = "live_two_birth_prefix_checkpoint_id"
_FAILURE_ID = "two_birth_protocol_failure_closure_id"

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_HEX = re.compile(r"(?:[0-9a-f]{2})*\Z")
_FRAME = struct.Struct("<QIIQ16sqiIQ")
_UCRED = struct.Struct("=iII")
_RIGHT = struct.Struct("=i")
_FRAME_MAGIC = 0x31564E5043514641
_FRAME_VERSION = 1
_FD_CLOEXEC = 1
_SOCK_SEQPACKET = getattr(socket, "SOCK_SEQPACKET", 5)
_ALLOWED_RECEIVE_FLAGS = int(getattr(socket, "MSG_EOR", 0)) | int(
    getattr(socket, "MSG_CMSG_CLOEXEC", 0)
)
_ROLE_ELF_SHA256 = "18656f1efabf4e7229c5f5a7676f557bd2d28b17bb3eaf81d37953fd21578c05"
_ROLE_ELF_BYTE_COUNT = 8272

_LOCKED_CLAIMS: Mapping[str, Any] = MappingProxyType(
    {
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
)

_SOURCE_ROLE_PATHS: tuple[tuple[str, str], ...] = (
    (
        "PORTABLE_CHECKPOINT_PRODUCER_PYTHON",
        "src/acfqp/construction_k7_h1_two_birth_portable_checkpoint_v1.py",
    ),
    (
        "V18_DOMAIN_REGISTRY_PYTHON",
        "src/acfqp/construction_k7_h1_domain_registry_extension_v18.py",
    ),
    ("CANONICAL_JSON_IDENTITY_PYTHON", "src/acfqp/phase3e_ids.py"),
    (
        "TWO_BIRTH_RUNTIME_PYTHON",
        "src/acfqp/construction_k7_h1_nested_creator_two_birth_runtime_v1.py",
    ),
    (
        "NESTED_PROBE_RUNTIME_PYTHON",
        "src/acfqp/construction_k7_h1_nested_creator_probe_native_v1.py",
    ),
    (
        "SUPERVISOR_EXEC_BIRTH_PYTHON",
        "src/acfqp/construction_k7_h1_nested_creator_supervisor_exec_birth_native_v1.py",
    ),
    (
        "SUPERVISOR_ROLE_PYTHON",
        "src/acfqp/construction_k7_h1_nested_creator_supervisor_native_v1.py",
    ),
    (
        "SUPERVISOR_EXEC_BIRTH_ASSEMBLY",
        "src/acfqp/native/h1_nested_creator_supervisor_exec_birth_x86_64_v1.S",
    ),
    (
        "SUPERVISOR_ROLE_NATIVE_SOURCE",
        "src/acfqp/native/h1_nested_creator_supervisor_x86_64_v1.c",
    ),
)

# These are verifier-side trust anchors, deliberately outside the producer's
# self-signed source closure.  Updating a source entry, all callable
# fingerprints, and every enclosing V18 content ID therefore cannot turn
# different executable bytes into the frozen V18 verifier-accepted source set.
_SOURCE_ANCHORS: Mapping[str, tuple[int, str]] = MappingProxyType(
    {
        "PORTABLE_CHECKPOINT_PRODUCER_PYTHON": (
            86558,
            "1fe3d96cbac95aeb8f229fc17d3abc9223e9b2d7a9dc5447fccc756f10d84d36",
        ),
        "V18_DOMAIN_REGISTRY_PYTHON": (
            3055,
            "b8def7a086b3e8f6d6945d5a780b75f4ffbff4142a5e8533e305b9b69d916e05",
        ),
        "CANONICAL_JSON_IDENTITY_PYTHON": (
            170660,
            "3eb435bfec4692961d61b4edf6e067cc128810509b5e35ec1d7348079288c4c2",
        ),
        "TWO_BIRTH_RUNTIME_PYTHON": (
            83943,
            "4639c2ef97fdbfc0bfd66f8a03b06ec8db8c5b43bf2736e1b19999d6e3632e1c",
        ),
        "NESTED_PROBE_RUNTIME_PYTHON": (
            74363,
            "7845775a7449a30a3f452ae53edc695c6f46534ef1a5b6725f24313bcd970266",
        ),
        "SUPERVISOR_EXEC_BIRTH_PYTHON": (
            13348,
            "434ce1618929abb0ce1534ca79f11fa8f4102b100dac68e64160f4e51490dee8",
        ),
        "SUPERVISOR_ROLE_PYTHON": (
            26520,
            "3fa2b55f635c19530d0859a83d0eb87c0dba242ead236852a6c5f07cc4178c98",
        ),
        "SUPERVISOR_EXEC_BIRTH_ASSEMBLY": (
            11340,
            "cb7b665a024d9d92821a706e5c68d5e24fcbcb3ef6d2faac401936265ba4803b",
        ),
        "SUPERVISOR_ROLE_NATIVE_SOURCE": (
            20145,
            "3461a4b7215f04cf4a2c7274a8737968f438ed1bc8270027400c00b920c52750",
        ),
    }
)

_CALLABLE_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "RUNTIME_BEGIN",
        "acfqp.construction_k7_h1_nested_creator_two_birth_runtime_v1",
        "begin_bounded_nested_creator_two_birth_live_prefix_v1",
        "TWO_BIRTH_RUNTIME_PYTHON",
    ),
    (
        "RUNTIME_SNAPSHOT",
        "acfqp.construction_k7_h1_nested_creator_two_birth_runtime_v1",
        "snapshot_bounded_nested_creator_two_birth_live_prefix_v1",
        "TWO_BIRTH_RUNTIME_PYTHON",
    ),
    (
        "RUNTIME_CLOSE",
        "acfqp.construction_k7_h1_nested_creator_two_birth_runtime_v1",
        "close_bounded_nested_creator_two_birth_live_prefix_v1",
        "TWO_BIRTH_RUNTIME_PYTHON",
    ),
    (
        "RUNTIME_ABORT",
        "acfqp.construction_k7_h1_nested_creator_two_birth_runtime_v1",
        "abort_bounded_nested_creator_two_birth_live_prefix_v1",
        "TWO_BIRTH_RUNTIME_PYTHON",
    ),
    (
        "RUNTIME_BEGIN_FAILURE_RECOVERY",
        "acfqp.construction_k7_h1_nested_creator_two_birth_runtime_v1",
        "recover_bounded_nested_creator_two_birth_begin_failure_v1",
        "TWO_BIRTH_RUNTIME_PYTHON",
    ),
    (
        "CONTROL_POPULATION_OBSERVE",
        "acfqp.construction_k7_h1_nested_creator_probe_native_v1",
        "observe_nested_creator_control_population_v1",
        "NESTED_PROBE_RUNTIME_PYTHON",
    ),
    (
        "V18_CONTENT_ID",
        "acfqp.construction_k7_h1_domain_registry_extension_v18",
        "extension_content_id_v18",
        "V18_DOMAIN_REGISTRY_PYTHON",
    ),
    (
        "CANONICAL_JSON_BYTES",
        "acfqp.phase3e_ids",
        "canonical_json_bytes",
        "CANONICAL_JSON_IDENTITY_PYTHON",
    ),
)


class TwoBirthPortableCheckpointIndependentVerificationViolation(ValueError):
    """The supplied bytes do not satisfy the frozen V18 observation contract."""


def _fail(message: str) -> NoReturn:
    raise TwoBirthPortableCheckpointIndependentVerificationViolation(message)


def _expect(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        _fail(f"{label} fields changed")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive integer")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative integer")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256 digest")
    return value


def _hex_bytes(value: Any, label: str, *, byte_count: int | None = None) -> bytes:
    if type(value) is not str or _LOWER_HEX.fullmatch(value) is None:
        _fail(f"{label} must be lowercase even-length hexadecimal")
    raw = bytes.fromhex(value)
    if byte_count is not None and len(raw) != byte_count:
        _fail(f"{label} byte count changed")
    return raw


def _claims(document: Mapping[str, Any], label: str) -> None:
    for field, expected in _LOCKED_CLAIMS.items():
        if field not in document or document[field] != expected or type(document[field]) is not type(expected):
            _fail(f"{label} changed locked claim {field}")


def _parse_record(raw: bytes, index: int) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"journal record {index} is not nonempty bytes")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise TwoBirthPortableCheckpointIndependentVerificationViolation(
            f"journal record {index} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"journal record {index} is not one canonical object")
    return document


def _content_id(
    document: Mapping[str, Any], *, domain: str, id_field: str, label: str
) -> str:
    supplied = document.get(id_field)
    _sha(supplied, f"{label} ID")
    payload = dict(document)
    del payload[id_field]
    expected = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    if supplied != expected:
        _fail(f"{label} content ID or domain changed")
    return supplied


def _find_code(root: CodeType, qualname: str) -> CodeType:
    matches: list[CodeType] = []
    stack = [root]
    while stack:
        item = stack.pop()
        # ``co_qualname`` is unavailable on the repository's Python 3.10
        # baseline.  All frozen authorities are module-level functions, so
        # their exact public qualname equals ``co_name``.
        if item.co_name == qualname:
            matches.append(item)
        stack.extend(value for value in item.co_consts if type(value) is CodeType)
    if len(matches) != 1:
        _fail(f"frozen callable {qualname} is absent or ambiguous")
    return matches[0]


def _semantic_value_document(value: Any) -> dict[str, Any]:
    """Encode one Python code constant without repr or marshal authority."""

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
        items.sort(key=canonical_json_bytes)
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
        items.sort(key=canonical_json_bytes)
        return {"kind": "DICT", "items": items}
    if type(value) is CodeType:
        return {"kind": "CODE", "value": _code_fingerprint_document(value)}
    _fail("frozen callable contains an unsupported semantic value")


def _code_fingerprint_document(code: CodeType) -> dict[str, Any]:
    """Replay the producer's recursive, address-free code semantics."""

    if type(code) is not CodeType:
        _fail("frozen callable code object changed type")
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
        "co_exceptiontable_hex": getattr(
            code, "co_exceptiontable", b""
        ).hex(),
    }


def _function_has_no_defaults(
    source_raw: bytes, *, path: str, qualname: str
) -> bool:
    """Establish the frozen NONE defaults without executing source bytes."""

    try:
        tree = ast.parse(source_raw, filename=path, mode="exec")
    except (SyntaxError, ValueError, TypeError) as error:
        raise TwoBirthPortableCheckpointIndependentVerificationViolation(
            f"embedded Python source cannot parse defaults for {qualname}"
        ) from error
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == qualname
    ]
    if len(matches) != 1:
        _fail(f"frozen callable AST {qualname} is absent or ambiguous")
    arguments = matches[0].args
    return not arguments.defaults and all(
        default is None for default in arguments.kw_defaults
    )


def _callable_semantic_documents_from_source(
    source_raw: bytes,
    *,
    path: str,
    qualname: str,
    compiled_root: CodeType,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str, CodeType]:
    """Recompute a binding from bytes, never importing or executing it."""

    code = _find_code(compiled_root, qualname)
    if not _function_has_no_defaults(source_raw, path=path, qualname=qualname):
        _fail(
            f"frozen callable {qualname} acquired defaults that cannot be "
            "verified without execution"
        )
    code_document = _code_fingerprint_document(code)
    defaults_document = {"kind": "NONE"}
    kwdefaults_document = {"kind": "NONE"}
    code_sha256 = hashlib.sha256(
        canonical_json_bytes(code_document)
    ).hexdigest()
    callable_document = {
        "schema": "acfqp.python_callable_semantics.v1",
        "code_fingerprint_document": code_document,
        "defaults_fingerprint_document": defaults_document,
        "kwdefaults_fingerprint_document": kwdefaults_document,
    }
    callable_sha256 = hashlib.sha256(
        canonical_json_bytes(callable_document)
    ).hexdigest()
    return (
        code_document,
        defaults_document,
        kwdefaults_document,
        code_sha256,
        callable_sha256,
        code,
    )


def _verify_source_closure(document: dict[str, Any]) -> str:
    expected_keys = {
        "schema", "schema_version", "profile_key", "readiness",
        "freeze_phase", "journal_sequence", "previous_record_id",
        "source_entries", "source_entry_count", "callable_authority_bindings",
        "source_and_duplicate_witness_retained_until_root_commit",
        "source_descriptor_revalidation_required_after_root_commit",
        "source_closure_is_execution_authority", _SOURCE_ID,
        *_LOCKED_CLAIMS,
    }
    _exact_keys(document, expected_keys, "source closure")
    _expect(document["schema"] == _SOURCE_SCHEMA, "source schema changed")
    _expect(document["schema_version"] == SCHEMA_VERSION, "source schema version changed")
    _expect(document["profile_key"] == PRODUCER_PROFILE_KEY, "source profile changed")
    _expect(document["readiness"] == "DURABLE_NONAUTHORITATIVE_TWO_BIRTH_OBSERVATION_ONLY", "source readiness changed")
    _expect(document["freeze_phase"] == "BEFORE_RAW_TWO_BIRTH_BEGIN", "source freeze phase changed")
    _expect(document["journal_sequence"] == 1, "source sequence changed")
    _expect(document["previous_record_id"] == {"kind": "GENESIS", "reason": "PRIVATE_EMPTY_JOURNAL"}, "source genesis marker changed")
    _expect(document["source_entry_count"] == len(_SOURCE_ROLE_PATHS), "source entry count changed")
    _expect(document["source_and_duplicate_witness_retained_until_root_commit"] is True, "source witness retention changed")
    _expect(document["source_descriptor_revalidation_required_after_root_commit"] is True, "source revalidation changed")
    _expect(document["source_closure_is_execution_authority"] is False, "source closure claimed authority")
    _claims(document, "source closure")

    entries = document["source_entries"]
    if type(entries) is not list or len(entries) != len(_SOURCE_ROLE_PATHS):
        _fail("source entry inventory changed")
    by_role: dict[str, tuple[dict[str, Any], bytes]] = {}
    entry_keys = {
        "role", "repository_relative_path", "device", "inode", "mode",
        "uid", "gid", "link_count", "byte_count", "sha256",
        "source_bytes_hex", "source_and_witness_same_inode",
        "source_descriptor_cloexec", "witness_descriptor_cloexec",
        "descriptor_numbers_serialized", "absolute_path_serialized",
    }
    for entry, (expected_role, expected_path) in zip(entries, _SOURCE_ROLE_PATHS, strict=True):
        entry = _exact_keys(entry, entry_keys, f"source entry {expected_role}")
        _expect(entry["role"] == expected_role, "source role order changed")
        _expect(entry["repository_relative_path"] == expected_path, f"source path changed for {expected_role}")
        _nonnegative(entry["device"], f"{expected_role} device")
        _positive(entry["inode"], f"{expected_role} inode")
        mode = _positive(entry["mode"], f"{expected_role} mode")
        _expect(stat.S_ISREG(mode), f"{expected_role} is not a regular source")
        _nonnegative(entry["uid"], f"{expected_role} uid")
        _nonnegative(entry["gid"], f"{expected_role} gid")
        _positive(entry["link_count"], f"{expected_role} link count")
        byte_count = _nonnegative(entry["byte_count"], f"{expected_role} byte count")
        raw = _hex_bytes(entry["source_bytes_hex"], f"{expected_role} source bytes", byte_count=byte_count)
        embedded_sha256 = _sha(entry["sha256"], f"{expected_role} source hash")
        _expect(hashlib.sha256(raw).hexdigest() == embedded_sha256, f"{expected_role} embedded source hash changed")
        _expect(
            (byte_count, embedded_sha256) == _SOURCE_ANCHORS[expected_role],
            f"external source anchor changed for {expected_role}",
        )
        for field in ("source_and_witness_same_inode", "source_descriptor_cloexec", "witness_descriptor_cloexec"):
            _expect(entry[field] is True, f"{expected_role} {field} changed")
        for field in ("descriptor_numbers_serialized", "absolute_path_serialized"):
            _expect(entry[field] is False, f"{expected_role} {field} changed")
        by_role[expected_role] = (entry, raw)

    bindings = document["callable_authority_bindings"]
    if type(bindings) is not list or len(bindings) != len(_CALLABLE_SPECS):
        _fail("callable authority inventory changed")
    compiled: dict[str, CodeType] = {}
    binding_keys = {
        "role", "module", "qualname", "module_repository_relative_path",
        "code_first_line", "code_fingerprint_document",
        "defaults_fingerprint_document", "kwdefaults_fingerprint_document",
        "code_fingerprint_sha256", "callable_semantic_fingerprint_sha256",
        "callable_object_and_code_identity_revalidated",
    }
    for binding, (role, module, qualname, source_role) in zip(bindings, _CALLABLE_SPECS, strict=True):
        binding = _exact_keys(binding, binding_keys, f"callable binding {role}")
        source_entry, source_raw = by_role[source_role]
        expected_path = source_entry["repository_relative_path"]
        _expect(binding["role"] == role, "callable role order changed")
        _expect(binding["module"] == module, f"callable module changed for {role}")
        _expect(binding["qualname"] == qualname, f"callable qualname changed for {role}")
        _expect(binding["module_repository_relative_path"] == expected_path, f"callable path join changed for {role}")
        _expect(binding["callable_object_and_code_identity_revalidated"] is True, f"callable revalidation changed for {role}")
        if source_role not in compiled:
            try:
                compiled[source_role] = compile(source_raw, expected_path, "exec", dont_inherit=True)
            except (SyntaxError, ValueError, TypeError) as error:
                raise TwoBirthPortableCheckpointIndependentVerificationViolation(
                    f"embedded Python source cannot replay {role}"
                ) from error
        (
            code_document,
            defaults_document,
            kwdefaults_document,
            code_sha256,
            callable_sha256,
            code,
        ) = _callable_semantic_documents_from_source(
            source_raw,
            path=expected_path,
            qualname=qualname,
            compiled_root=compiled[source_role],
        )
        _expect(binding["code_first_line"] == code.co_firstlineno, f"callable line join changed for {role}")
        _expect(
            binding["code_fingerprint_document"] == code_document,
            f"callable recursive code fingerprint changed for {role}",
        )
        _expect(
            binding["defaults_fingerprint_document"] == defaults_document
            and binding["kwdefaults_fingerprint_document"]
            == kwdefaults_document,
            f"callable default fingerprint changed for {role}",
        )
        _expect(
            binding["code_fingerprint_sha256"] == code_sha256,
            f"callable code fingerprint hash changed for {role}",
        )
        _expect(
            binding["callable_semantic_fingerprint_sha256"]
            == callable_sha256,
            f"callable semantic fingerprint hash changed for {role}",
        )

    return _content_id(
        document,
        domain=CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
        id_field=_SOURCE_ID,
        label="source closure",
    )


def _verify_cgroup_snapshot(
    value: Any,
    *,
    sequence: int,
    expected_pids: list[int],
    control_identity: Mapping[str, Any],
    label: str,
) -> None:
    value = _exact_keys(
        value,
        {"sequence", "directory_device", "directory_inode", "first_cgroup_procs", "events", "pids_current", "second_cgroup_procs"},
        label,
    )
    _expect(value["sequence"] == sequence, f"{label} sequence changed")
    _expect(value["directory_device"] == control_identity["device"] and value["directory_inode"] == control_identity["inode"], f"{label} cgroup identity join changed")
    _expect(value["first_cgroup_procs"] == expected_pids and value["second_cgroup_procs"] == expected_pids, f"{label} PID inventory changed")
    events = value["events"]
    _expect(type(events) is dict and events.get("populated") == int(bool(expected_pids)) and events.get("frozen") == 0 and all(type(k) is str and type(v) is int and v >= 0 for k, v in events.items()), f"{label} events changed")
    _expect(value["pids_current"] == len(expected_pids), f"{label} pids.current changed")


def _verify_pidfd_fact(value: Any, *, pid: int, label: str) -> None:
    value = _exact_keys(value, {"pid", "nspid", "device", "inode"}, label)
    _expect(value["pid"] == pid, f"{label} PID join changed")
    _positive(value["nspid"], f"{label} namespace PID")
    _nonnegative(value["device"], f"{label} device")
    _positive(value["inode"], f"{label} inode")


def _frame_from_raw(raw: bytes, label: str) -> dict[str, Any]:
    if len(raw) != _FRAME.size:
        _fail(f"{label} native frame byte count changed")
    magic, version, opcode, sequence, nonce, pid, status, flags, fact_a = _FRAME.unpack(raw)
    _expect(magic == _FRAME_MAGIC and version == _FRAME_VERSION, f"{label} frame identity changed")
    return {
        "opcode": opcode,
        "sequence": sequence,
        "nonce_hex": nonce.hex(),
        "pid": pid,
        "status": status,
        "flags": flags,
        "fact_a": fact_a,
    }


def _verify_unix_address(value: Any, label: str) -> None:
    """Verify one replayable Unix-socket address observation.

    Linux ``socketpair`` observations can report no source address or the
    connected empty pathname.  ``SO_PASSCRED`` auto-binding can instead
    report an abstract address: NUL followed by five lowercase ASCII hex
    digits.  These are three real kernel encodings, not interchangeable
    placeholders invented by the verifier.
    """

    if value == {"kind": "NONE"}:
        return
    if type(value) is not dict:
        _fail(f"{label} socket address changed")
    if value.get("kind") == "TEXT" and set(value) == {"kind", "value"}:
        _expect(value["value"] == "", f"{label} Unix pathname changed")
        return
    if value.get("kind") == "BYTES_HEX" and set(value) == {"kind", "value"}:
        raw = _hex_bytes(value["value"], f"{label} abstract Unix address")
        _expect(
            len(raw) == 6
            and raw[:1] == b"\x00"
            and all(byte in b"0123456789abcdef" for byte in raw[1:]),
            f"{label} abstract Unix address grammar changed",
        )
        return
    _fail(f"{label} socket address changed")


def _verify_native_observation(
    value: Any,
    *,
    event_index: int,
    expected_frame: Mapping[str, Any],
    credential_pid: int,
    credential_uid: int,
    credential_gid: int,
    rights_count: int,
    installed_pid: int | None,
    label: str,
) -> None:
    keys = {
        "event_index", "opcode", "sequence", "frame_pid", "payload_sha256",
        "payload_byte_count", "raw_payload_hex", "decoded_frame", "credentials",
        "rights_count", "installed_pidfd_facts", "recv_flags", "address",
        "connected_peer_address", "ancillary",
    }
    value = _exact_keys(value, keys, label)
    _expect(value["event_index"] == event_index, f"{label} event index changed")
    raw = _hex_bytes(value["raw_payload_hex"], f"{label} raw payload")
    decoded = _frame_from_raw(raw, label)
    _expect(decoded == expected_frame and value["decoded_frame"] == decoded, f"{label} decoded frame join changed")
    _expect(value["opcode"] == decoded["opcode"] and value["sequence"] == decoded["sequence"] and value["frame_pid"] == decoded["pid"], f"{label} frame summary changed")
    _expect(value["payload_byte_count"] == len(raw) and value["payload_sha256"] == hashlib.sha256(raw).hexdigest(), f"{label} payload hash changed")
    credentials = {"pid": credential_pid, "uid": credential_uid, "gid": credential_gid}
    _expect(value["credentials"] == credentials, f"{label} credentials changed")
    _expect(value["rights_count"] == rights_count, f"{label} rights count changed")
    installed = value["installed_pidfd_facts"]
    _expect(type(installed) is list and len(installed) == rights_count, f"{label} installed-right inventory changed")
    if rights_count == 1:
        fact = _exact_keys(installed[0], {"pid", "nspid", "device", "inode", "descriptor_flags", "cloexec"}, f"{label} installed pidfd")
        _expect(installed_pid is not None and fact["pid"] == installed_pid, f"{label} installed pidfd PID changed")
        _positive(fact["nspid"], f"{label} installed namespace PID")
        _nonnegative(fact["device"], f"{label} installed pidfd device")
        _positive(fact["inode"], f"{label} installed pidfd inode")
        _expect(type(fact["descriptor_flags"]) is int and fact["descriptor_flags"] & _FD_CLOEXEC and fact["cloexec"] is True, f"{label} installed pidfd lost CLOEXEC")
    _expect(type(value["recv_flags"]) is int and value["recv_flags"] >= 0 and value["recv_flags"] & (socket.MSG_TRUNC | socket.MSG_CTRUNC) == 0 and value["recv_flags"] & ~_ALLOWED_RECEIVE_FLAGS == 0, f"{label} receive flags changed")
    _verify_unix_address(value["address"], f"{label} source")
    _verify_unix_address(value["connected_peer_address"], f"{label} peer")
    ancillary = value["ancillary"]
    _expect(type(ancillary) is list and len(ancillary) == 1 + int(rights_count > 0), f"{label} ancillary inventory changed")
    credential_rows = [row for row in ancillary if type(row) is dict and row.get("level") == socket.SOL_SOCKET and row.get("kind") == socket.SCM_CREDENTIALS]
    rights_rows = [row for row in ancillary if type(row) is dict and row.get("level") == socket.SOL_SOCKET and row.get("kind") == socket.SCM_RIGHTS]
    _expect(len(credential_rows) == 1 and len(rights_rows) == int(rights_count > 0), f"{label} ancillary roles changed")
    _exact_keys(credential_rows[0], {"level", "kind", "byte_count", "data_hex"}, f"{label} SCM credentials row")
    credential_raw = _hex_bytes(credential_rows[0].get("data_hex"), f"{label} SCM credentials", byte_count=_UCRED.size)
    _expect(credential_rows[0].get("byte_count") == _UCRED.size and _UCRED.unpack(credential_raw) == (credential_pid, credential_uid, credential_gid), f"{label} SCM credentials bytes changed")
    if rights_rows:
        _exact_keys(rights_rows[0], {"level", "kind", "byte_count", "data_hex"}, f"{label} SCM rights row")
        right_raw = _hex_bytes(rights_rows[0].get("data_hex"), f"{label} SCM right", byte_count=_RIGHT.size)
        _expect(rights_rows[0].get("byte_count") == _RIGHT.size and _RIGHT.unpack(right_raw)[0] >= 0, f"{label} SCM right bytes changed")


def _frame_document(*, opcode: int, nonce: str, pid: int, status: int = 0, flags: int = 0, fact_a: int = 0, sequence: int = 1) -> dict[str, Any]:
    return {"opcode": opcode, "sequence": sequence, "nonce_hex": nonce, "pid": pid, "status": status, "flags": flags, "fact_a": fact_a}


def _verify_nested_v2(
    value: Any,
    *,
    guardian_pid: int,
    supervisor_pid: int,
    supervisor_start_ticks: int,
    probe_pid: int,
    probe_start_ticks: int,
    control_identity: Mapping[str, Any],
) -> tuple[int, int]:
    value = _exact_keys(
        value,
        {"schema", "schema_version", "profile_key", "raw_facts_v1", "supervisor_ready_observation", "protocol_receive_observations", "nested_receive_credential_observations_present", "nested_receive_rights_observations_present", "portable_checkpoint_authority_present", "two_birth_prefix_authority_present", "official_execution_allowed"},
        "nested V2 facts",
    )
    _expect(value["schema"] == "acfqp.k7_h1_nested_creator_probe_observed_facts.v2" and value["schema_version"] == "2.0.0" and value["profile_key"] == "construction_k7_h1_nested_creator_probe_observed_v2", "nested V2 identity changed")
    for field in ("nested_receive_credential_observations_present", "nested_receive_rights_observations_present"):
        _expect(value[field] is True, f"nested V2 {field} changed")
    for field in ("portable_checkpoint_authority_present", "two_birth_prefix_authority_present", "official_execution_allowed"):
        _expect(value[field] is False, f"nested V2 {field} changed")

    raw_facts = _exact_keys(
        value["raw_facts_v1"],
        {"schema", "schema_version", "profile_key", "supervisor_pid", "supervisor_start_ticks", "probe_pid", "probe_start_ticks", "nonce_hex", "parent_return_frame", "child_withdrawn_frame", "child_ready_frame", "child_release_echo_frame", "creator_reap_frame", "pid_cell_value", "pidfd_fact", "live_cgroup_snapshots", "post_reap_cgroup_snapshots", "guardian_waitid_errno", "actual_nested_pidfd_probe_birth_present", "actual_non_guardian_creator_reap_present", "guardian_independent_pid_cell_pidfd_cgroup_join_present", "gated_supervisor_birth_authority_present", "two_birth_prefix_authority_present", "five_birth_process_authority_present", "production_shared_resource_receipts_present", "official_execution_allowed"},
        "nested raw facts",
    )
    _expect(raw_facts["schema"] == "acfqp.k7_h1_nested_creator_probe_raw_facts.v1" and raw_facts["schema_version"] == SCHEMA_VERSION and raw_facts["profile_key"] == "construction_k7_h1_nested_creator_probe_native_v1", "nested raw identity changed")
    _expect((raw_facts["supervisor_pid"], raw_facts["supervisor_start_ticks"], raw_facts["probe_pid"], raw_facts["probe_start_ticks"]) == (supervisor_pid, supervisor_start_ticks, probe_pid, probe_start_ticks), "nested raw process join changed")
    nonce = raw_facts["nonce_hex"]
    _hex_bytes(nonce, "nested nonce", byte_count=16)
    frames = (
        ("parent_return_frame", _frame_document(opcode=3, nonce=nonce, pid=probe_pid, flags=0x1F, fact_a=supervisor_pid)),
        ("child_withdrawn_frame", _frame_document(opcode=9, nonce=nonce, pid=probe_pid)),
        ("child_ready_frame", _frame_document(opcode=10, nonce=nonce, pid=probe_pid)),
        ("child_release_echo_frame", _frame_document(opcode=12, nonce=nonce, pid=probe_pid)),
        ("creator_reap_frame", _frame_document(opcode=5, nonce=nonce, pid=probe_pid, flags=1, fact_a=errno.ECHILD)),
    )
    for field, expected in frames:
        _expect(raw_facts[field] == expected, f"nested raw {field} semantics changed")
    _expect(raw_facts["pid_cell_value"] == probe_pid and raw_facts["guardian_waitid_errno"] == errno.ECHILD, "nested PID-cell or reap ownership changed")
    _verify_pidfd_fact(raw_facts["pidfd_fact"], pid=probe_pid, label="nested probe pidfd")
    live = raw_facts["live_cgroup_snapshots"]
    post = raw_facts["post_reap_cgroup_snapshots"]
    _expect(type(live) is list and len(live) == 2 and type(post) is list and len(post) == 2, "nested cgroup snapshot inventory changed")
    for item, seq in zip(live, (1, 2), strict=True):
        _verify_cgroup_snapshot(item, sequence=seq, expected_pids=[supervisor_pid, probe_pid], control_identity=control_identity, label=f"nested live cgroup {seq}")
    for item, seq in zip(post, (3, 4), strict=True):
        _verify_cgroup_snapshot(item, sequence=seq, expected_pids=[supervisor_pid], control_identity=control_identity, label=f"nested post-reap cgroup {seq}")
    for field in ("actual_nested_pidfd_probe_birth_present", "actual_non_guardian_creator_reap_present", "guardian_independent_pid_cell_pidfd_cgroup_join_present"):
        _expect(raw_facts[field] is True, f"nested raw {field} changed")
    for field in ("gated_supervisor_birth_authority_present", "two_birth_prefix_authority_present", "five_birth_process_authority_present", "production_shared_resource_receipts_present", "official_execution_allowed"):
        _expect(raw_facts[field] is False, f"nested raw {field} changed")

    ready = value["supervisor_ready_observation"]
    credentials = ready.get("credentials") if type(ready) is dict else None
    if type(credentials) is not dict:
        _fail("supervisor-ready credentials are absent")
    uid = _nonnegative(credentials.get("uid"), "nested guardian uid")
    gid = _nonnegative(credentials.get("gid"), "nested guardian gid")
    ready_frame = _frame_document(opcode=1, nonce="00" * 16, pid=supervisor_pid, fact_a=guardian_pid, sequence=0)
    _verify_native_observation(ready, event_index=0, expected_frame=ready_frame, credential_pid=supervisor_pid, credential_uid=uid, credential_gid=gid, rights_count=0, installed_pid=None, label="supervisor-ready observation")
    observations = value["protocol_receive_observations"]
    if type(observations) is not list or len(observations) != 5:
        _fail("nested receive observation inventory changed")
    expected_rows = (
        (frames[0][1], supervisor_pid, 1, probe_pid),
        (frames[1][1], probe_pid, 0, None),
        (frames[2][1], probe_pid, 0, None),
        (frames[3][1], probe_pid, 0, None),
        (frames[4][1], supervisor_pid, 0, None),
    )
    for index, (item, (frame, credential_pid, right_count, installed_pid)) in enumerate(zip(observations, expected_rows, strict=True)):
        _verify_native_observation(item, event_index=index, expected_frame=frame, credential_pid=credential_pid, credential_uid=uid, credential_gid=gid, rights_count=right_count, installed_pid=installed_pid, label=f"nested receive {index}")
    installed_probe_pidfd = observations[0]["installed_pidfd_facts"][0]
    _expect(
        {
            field: installed_probe_pidfd[field]
            for field in ("pid", "nspid", "device", "inode")
        }
        == raw_facts["pidfd_fact"],
        "nested installed/raw pidfd identity join changed",
    )
    return uid, gid


def _verify_live_observation(value: Any) -> None:
    keys = {
        "schema", "schema_version", "profile_key", "readiness",
        "live_prefix_state_at_issuance", "guardian_identity",
        "control_cgroup_identity", "birth_order", "creator_by_role",
        "supervisor_pid", "supervisor_start_ticks", "probe_pid",
        "probe_start_ticks", "outer_pid_cell_value", "outer_parent_edge",
        "outer_nonce_hex", "outer_registered_expected_frames",
        "outer_receive_facts", "outer_pidfd_fact", "outer_seal_set",
        "outer_role_source_fact", "entry_empty_control_snapshots",
        "outer_supervisor_live_snapshots", "checkpoint_current_control_snapshots",
        "live_session_verification", "nested_probe_observed_facts_v2",
        "retained_descriptor_roles",
        "retained_live_descriptor_numbers_serialized",
        "historical_scm_rights_descriptor_number_observation_present",
        "historical_descriptor_numbers_are_not_resume_capability",
        "memory_peak_read_count", "supervisor_v1_only_accepts_shutdown_after_probe",
        "broker_launch_supported_by_live_process", "target_two_birth_creator_chain_observed",
        "exact_creator_reap_ownership_observed", "portable_observation_checkpoint_present",
        "durable_two_birth_artifact_graph_present", "portable_checkpoint_authority_present",
        "live_continuation_capability_portable", *_LOCKED_CLAIMS,
    }
    value = _exact_keys(value, keys, "live observation")
    _expect(value["schema"] == _LIVE_SCHEMA and value["schema_version"] == SCHEMA_VERSION, "live observation schema changed")
    _expect(value["profile_key"] == "construction_k7_h1_nested_creator_two_birth_runtime_v1" and value["readiness"] == "ACTUAL_TWO_BIRTH_RAW_RUNTIME_ONLY", "live observation profile changed")
    _expect(value["live_prefix_state_at_issuance"] == "PROBE_REAPED_SUPERVISOR_LIVE", "live issuance state changed")
    guardian = _exact_keys(value["guardian_identity"], {"pid", "process_start_ticks", "thread_id", "native_thread_id"}, "guardian identity")
    guardian_pid = _positive(guardian["pid"], "guardian PID")
    for field in ("process_start_ticks", "thread_id", "native_thread_id"):
        _positive(guardian[field], f"guardian {field}")
    control = _exact_keys(value["control_cgroup_identity"], {"device", "inode", "mode"}, "CONTROL identity")
    _nonnegative(control["device"], "CONTROL device")
    _positive(control["inode"], "CONTROL inode")
    _expect(type(control["mode"]) is int and stat.S_ISDIR(control["mode"]), "CONTROL mode changed")
    _expect(value["birth_order"] == ["SUPERVISOR", "PIDFD_PROBE"] and value["creator_by_role"] == {"SUPERVISOR": "GUARDIAN", "PIDFD_PROBE": "SUPERVISOR"}, "two-birth creator chain changed")
    supervisor_pid = _positive(value["supervisor_pid"], "supervisor PID")
    supervisor_ticks = _positive(value["supervisor_start_ticks"], "supervisor start ticks")
    probe_pid = _positive(value["probe_pid"], "probe PID")
    probe_ticks = _positive(value["probe_start_ticks"], "probe start ticks")
    _expect(len({guardian_pid, supervisor_pid, probe_pid}) == 3, "process identities overlap")
    _expect(value["outer_pid_cell_value"] == supervisor_pid, "outer PID-cell join changed")
    _expect(value["outer_parent_edge"] == {"clone_result": supervisor_pid, "status_bits": 123, "first_cleanup_error": 0, "reserved_zero": 0}, "outer parent-edge semantics changed")
    outer_nonce = value["outer_nonce_hex"]
    _hex_bytes(outer_nonce, "outer nonce", byte_count=16)
    expected_payloads = (
        ("CELL_WITHDRAWN", b"ACFQP:EXEC_CELL_WITHDRAWN:v1:" + outer_nonce.encode("ascii")),
        ("GATE_READY", b"ACFQP:EXEC_GATE_READY:v1:" + outer_nonce.encode("ascii")),
        ("RELEASE_ECHO", b"ACFQP:EXEC_RELEASE:v1:" + outer_nonce.encode("ascii")),
    )
    registered = value["outer_registered_expected_frames"]
    received = value["outer_receive_facts"]
    _expect(type(registered) is list and len(registered) == 3 and type(received) is list and len(received) == 3, "outer gate inventory changed")
    outer_uid: int | None = None
    outer_gid: int | None = None
    for registered_row, received_row, (kind, payload) in zip(registered, received, expected_payloads, strict=True):
        registered_row = _exact_keys(registered_row, {"kind", "payload_hex", "sha256", "byte_count"}, f"outer registered {kind}")
        expected_hash = hashlib.sha256(payload).hexdigest()
        _expect(registered_row == {"kind": kind, "payload_hex": payload.hex(), "sha256": expected_hash, "byte_count": len(payload)}, f"outer registered {kind} changed")
        received_row = _exact_keys(received_row, {"kind", "sha256", "byte_count", "credential_pid", "credential_uid", "credential_gid", "message_flags"}, f"outer receive {kind}")
        _expect(received_row["kind"] == kind and received_row["sha256"] == expected_hash and received_row["byte_count"] == len(payload), f"outer receive {kind} payload join changed")
        _expect(received_row["credential_pid"] == supervisor_pid, f"outer receive {kind} PID credential changed")
        uid = _nonnegative(received_row["credential_uid"], f"outer receive {kind} uid")
        gid = _nonnegative(received_row["credential_gid"], f"outer receive {kind} gid")
        _expect(type(received_row["message_flags"]) is int and received_row["message_flags"] >= 0 and received_row["message_flags"] & (socket.MSG_TRUNC | socket.MSG_CTRUNC) == 0 and received_row["message_flags"] & ~_ALLOWED_RECEIVE_FLAGS == 0, f"outer receive {kind} flags changed")
        outer_uid = uid if outer_uid is None else outer_uid
        outer_gid = gid if outer_gid is None else outer_gid
        _expect((uid, gid) == (outer_uid, outer_gid), "outer credential identity changed between frames")
    _verify_pidfd_fact(value["outer_pidfd_fact"], pid=supervisor_pid, label="outer supervisor pidfd")
    _expect(value["outer_seal_set"] == 15, "outer PID-cell seals changed")
    role_source = _exact_keys(value["outer_role_source_fact"], {"elf_sha256", "elf_byte_count", "source_device", "source_inode", "witness_device", "witness_inode", "source_witness_same_identity"}, "outer role source fact")
    _expect(role_source["elf_sha256"] == _ROLE_ELF_SHA256 and role_source["elf_byte_count"] == _ROLE_ELF_BYTE_COUNT, "outer role ELF identity changed")
    _expect(role_source["source_device"] == role_source["witness_device"] and role_source["source_inode"] == role_source["witness_inode"] and role_source["source_witness_same_identity"] is True, "outer role source witness join changed")
    for field in ("source_device", "witness_device"):
        _nonnegative(role_source[field], f"outer role {field}")
    for field in ("source_inode", "witness_inode"):
        _positive(role_source[field], f"outer role {field}")
    snapshot_groups = (
        ("entry_empty_control_snapshots", (7000, 7001), []),
        ("outer_supervisor_live_snapshots", (1, 2), [supervisor_pid]),
        ("checkpoint_current_control_snapshots", (8000, 8001), [supervisor_pid]),
    )
    for field, sequences, expected_pids in snapshot_groups:
        rows = value[field]
        _expect(type(rows) is list and len(rows) == 2, f"{field} inventory changed")
        for row, sequence in zip(rows, sequences, strict=True):
            _verify_cgroup_snapshot(row, sequence=sequence, expected_pids=expected_pids, control_identity=control, label=f"{field} {sequence}")
    nested_uid, nested_gid = _verify_nested_v2(value["nested_probe_observed_facts_v2"], guardian_pid=guardian_pid, supervisor_pid=supervisor_pid, supervisor_start_ticks=supervisor_ticks, probe_pid=probe_pid, probe_start_ticks=probe_ticks, control_identity=control)
    _expect((nested_uid, nested_gid) == (outer_uid, outer_gid), "outer and nested credential identities diverged")
    session = _exact_keys(value["live_session_verification"], {"profile_key", "session_state", "supervisor_pid", "supervisor_start_ticks", "supervisor_pidfd_fact", "supervisor_pidfd_cloexec", "control_socket_fact", "owner_pid", "owner_thread_id", "active_probe_pid", "live_session_verified", "verification_mutated_session"}, "live session verification")
    _expect(session["profile_key"] == "construction_k7_h1_nested_creator_probe_native_v1" and session["session_state"] == "PROBE_REAPED_SUPERVISOR_LIVE", "live session identity changed")
    _expect((session["supervisor_pid"], session["supervisor_start_ticks"]) == (supervisor_pid, supervisor_ticks) and session["owner_pid"] == guardian_pid and session["owner_thread_id"] == guardian["thread_id"] and session["active_probe_pid"] == -1, "live session process join changed")
    _expect(session["supervisor_pidfd_fact"] == value["outer_pidfd_fact"] and session["supervisor_pidfd_cloexec"] is True, "live session pidfd join changed")
    control_socket = _exact_keys(session["control_socket_fact"], {"device", "inode", "socket_type", "passcred", "descriptor_flags", "cloexec", "connected_peer_address", "peer_credentials"}, "live control socket")
    _nonnegative(control_socket["device"], "live control socket device")
    _positive(control_socket["inode"], "live control socket inode")
    _expect(control_socket["socket_type"] == _SOCK_SEQPACKET and control_socket["passcred"] == 1 and control_socket["cloexec"] is True and type(control_socket["descriptor_flags"]) is int and control_socket["descriptor_flags"] & _FD_CLOEXEC, "live control socket flags changed")
    _verify_unix_address(
        control_socket["connected_peer_address"], "live control peer"
    )
    _expect(control_socket["peer_credentials"] == {"pid": guardian_pid, "uid": outer_uid, "gid": outer_gid}, "live control peer join changed")
    _expect(session["live_session_verified"] is True and session["verification_mutated_session"] is False, "live session verification semantics changed")
    _expect(value["retained_descriptor_roles"] == ["CONTROL_CGROUP", "SUPERVISOR_CONTROL_SOCKET", "SUPERVISOR_PIDFD"], "retained descriptor roles changed")
    true_fields = (
        "supervisor_v1_only_accepts_shutdown_after_probe",
        "target_two_birth_creator_chain_observed",
        "exact_creator_reap_ownership_observed",
        "historical_scm_rights_descriptor_number_observation_present",
        "historical_descriptor_numbers_are_not_resume_capability",
    )
    false_fields = (
        "retained_live_descriptor_numbers_serialized",
        "broker_launch_supported_by_live_process",
        "portable_observation_checkpoint_present",
        "durable_two_birth_artifact_graph_present",
        "portable_checkpoint_authority_present",
        "live_continuation_capability_portable",
    )
    for field in true_fields:
        _expect(value[field] is True, f"live observation {field} changed")
    for field in false_fields:
        _expect(value[field] is False, f"live observation {field} changed")
    _expect(value["memory_peak_read_count"] == 0, "live observation performed a peak read")
    _claims(value, "live observation")


def _credential_expected_keys() -> set[str]:
    return {
        "schema", "schema_version", "profile_key", "readiness", _SOURCE_ID,
        "journal_sequence", "previous_record_id", "guardian_identity",
        "control_cgroup_identity", "supervisor_pid", "supervisor_start_ticks",
        "probe_pid", "probe_start_ticks", "outer_registered_expected_frames",
        "outer_receive_facts", "nested_probe_observed_facts_v2",
        "nested_receive_credential_observations_present",
        "nested_receive_rights_observations_present",
        "credential_observations_are_not_lease_authority", _CREDENTIAL_ID,
        *_LOCKED_CLAIMS,
    }


def _verify_credential_evidence(document: Mapping[str, Any]) -> None:
    """Verify the credential/V2 evidence even when no root row exists yet."""

    guardian = _exact_keys(
        document["guardian_identity"],
        {"pid", "process_start_ticks", "thread_id", "native_thread_id"},
        "credential guardian identity",
    )
    guardian_pid = _positive(guardian["pid"], "credential guardian PID")
    for field in ("process_start_ticks", "thread_id", "native_thread_id"):
        _positive(guardian[field], f"credential guardian {field}")
    control = _exact_keys(
        document["control_cgroup_identity"],
        {"device", "inode", "mode"},
        "credential CONTROL identity",
    )
    _nonnegative(control["device"], "credential CONTROL device")
    _positive(control["inode"], "credential CONTROL inode")
    _expect(
        type(control["mode"]) is int and stat.S_ISDIR(control["mode"]),
        "credential CONTROL mode changed",
    )
    supervisor_pid = _positive(document["supervisor_pid"], "credential supervisor PID")
    supervisor_ticks = _positive(
        document["supervisor_start_ticks"], "credential supervisor start ticks"
    )
    probe_pid = _positive(document["probe_pid"], "credential probe PID")
    probe_ticks = _positive(
        document["probe_start_ticks"], "credential probe start ticks"
    )
    _expect(
        len({guardian_pid, supervisor_pid, probe_pid}) == 3,
        "credential process identities overlap",
    )

    registered = document["outer_registered_expected_frames"]
    received = document["outer_receive_facts"]
    _expect(
        type(registered) is list
        and len(registered) == 3
        and type(received) is list
        and len(received) == 3,
        "credential outer gate inventory changed",
    )
    frame_prefixes = (
        ("CELL_WITHDRAWN", b"ACFQP:EXEC_CELL_WITHDRAWN:v1:"),
        ("GATE_READY", b"ACFQP:EXEC_GATE_READY:v1:"),
        ("RELEASE_ECHO", b"ACFQP:EXEC_RELEASE:v1:"),
    )
    outer_nonce: bytes | None = None
    outer_uid: int | None = None
    outer_gid: int | None = None
    for registered_row, received_row, (kind, prefix) in zip(
        registered, received, frame_prefixes, strict=True
    ):
        registered_row = _exact_keys(
            registered_row,
            {"kind", "payload_hex", "sha256", "byte_count"},
            f"credential registered {kind}",
        )
        payload = _hex_bytes(
            registered_row["payload_hex"],
            f"credential registered {kind} payload",
        )
        _expect(
            payload.startswith(prefix) and len(payload) == len(prefix) + 32,
            f"credential registered {kind} grammar changed",
        )
        nonce = payload[len(prefix) :]
        _expect(
            all(byte in b"0123456789abcdef" for byte in nonce),
            f"credential registered {kind} nonce changed",
        )
        outer_nonce = nonce if outer_nonce is None else outer_nonce
        _expect(nonce == outer_nonce, "credential outer nonces diverged")
        expected_hash = hashlib.sha256(payload).hexdigest()
        _expect(
            registered_row["kind"] == kind
            and registered_row["sha256"] == expected_hash
            and registered_row["byte_count"] == len(payload),
            f"credential registered {kind} hash join changed",
        )

        received_row = _exact_keys(
            received_row,
            {
                "kind", "sha256", "byte_count", "credential_pid",
                "credential_uid", "credential_gid", "message_flags",
            },
            f"credential receive {kind}",
        )
        _expect(
            received_row["kind"] == kind
            and received_row["sha256"] == expected_hash
            and received_row["byte_count"] == len(payload)
            and received_row["credential_pid"] == supervisor_pid,
            f"credential receive {kind} payload or PID join changed",
        )
        uid = _nonnegative(
            received_row["credential_uid"], f"credential receive {kind} uid"
        )
        gid = _nonnegative(
            received_row["credential_gid"], f"credential receive {kind} gid"
        )
        outer_uid = uid if outer_uid is None else outer_uid
        outer_gid = gid if outer_gid is None else outer_gid
        _expect(
            (uid, gid) == (outer_uid, outer_gid),
            "credential outer UID/GID observations diverged",
        )
        flags = received_row["message_flags"]
        _expect(
            type(flags) is int
            and flags >= 0
            and flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) == 0
            and flags & ~_ALLOWED_RECEIVE_FLAGS == 0,
            f"credential receive {kind} flags changed",
        )

    nested_uid, nested_gid = _verify_nested_v2(
        document["nested_probe_observed_facts_v2"],
        guardian_pid=guardian_pid,
        supervisor_pid=supervisor_pid,
        supervisor_start_ticks=supervisor_ticks,
        probe_pid=probe_pid,
        probe_start_ticks=probe_ticks,
        control_identity=control,
    )
    _expect(
        (nested_uid, nested_gid) == (outer_uid, outer_gid),
        "credential outer and nested UID/GID observations diverged",
    )


def _verify_credential_bundle(document: dict[str, Any], *, source_id: str, live: Mapping[str, Any] | None = None) -> str:
    _exact_keys(document, _credential_expected_keys(), "credential bundle")
    _expect(document["schema"] == _CREDENTIAL_SCHEMA and document["schema_version"] == SCHEMA_VERSION and document["profile_key"] == PRODUCER_PROFILE_KEY, "credential bundle identity changed")
    _expect(document["readiness"] == "DURABLE_NONAUTHORITATIVE_TWO_BIRTH_OBSERVATION_ONLY", "credential readiness changed")
    _expect(document[_SOURCE_ID] == source_id and document["previous_record_id"] == source_id and document["journal_sequence"] == 2, "credential source chain changed")
    for field in ("nested_receive_credential_observations_present", "nested_receive_rights_observations_present", "credential_observations_are_not_lease_authority"):
        _expect(document[field] is True, f"credential {field} changed")
    _claims(document, "credential bundle")
    _verify_credential_evidence(document)
    if live is not None:
        for field in ("guardian_identity", "control_cgroup_identity", "supervisor_pid", "supervisor_start_ticks", "probe_pid", "probe_start_ticks", "outer_registered_expected_frames", "outer_receive_facts", "nested_probe_observed_facts_v2"):
            _expect(document[field] == live[field], f"credential/live join changed for {field}")
    return _content_id(document, domain=CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN, id_field=_CREDENTIAL_ID, label="credential bundle")


def _verify_checkpoint(document: dict[str, Any], *, source: dict[str, Any], credentials: dict[str, Any], source_id: str, credential_id: str) -> str:
    keys = {
        "schema", "schema_version", "profile_key", "readiness", "issuance_state",
        "runtime_state_at_root_commit", "expected_success_return_runtime_state",
        "producer_success_return_not_yet_observed", "producer_protocol_after_checkpoint",
        "journal_sequence", "previous_record_id", "checkpoint_durable_before_runtime_shutdown",
        "execution_source_closure", "credential_observation_bundle", "live_observation",
        "root_embeds_complete_child_documents", _SOURCE_ID, _CREDENTIAL_ID,
        "portable_observation_checkpoint_present", "durable_portable_observation_graph_present",
        "checkpoint_bytes_describe_historical_live_observation",
        "checkpoint_bytes_encode_resume_capability", "live_continuation_capability_portable",
        _CHECKPOINT_ID, *_LOCKED_CLAIMS,
    }
    _exact_keys(document, keys, "live checkpoint")
    _expect(document["schema"] == _CHECKPOINT_SCHEMA and document["schema_version"] == SCHEMA_VERSION and document["profile_key"] == PRODUCER_PROFILE_KEY, "checkpoint identity changed")
    _expect(document["readiness"] == "DURABLE_NONAUTHORITATIVE_TWO_BIRTH_OBSERVATION_ONLY", "checkpoint readiness changed")
    _expect(document["issuance_state"] == "PROBE_REAPED_SUPERVISOR_LIVE" and document["runtime_state_at_root_commit"] == "PROBE_REAPED_SUPERVISOR_LIVE", "checkpoint live state changed")
    _expect(document["expected_success_return_runtime_state"] == "CLOSED" and document["producer_success_return_not_yet_observed"] is True and document["producer_protocol_after_checkpoint"] == "V1_SHUTDOWN_ONLY", "checkpoint future shutdown semantics changed")
    _expect(document["journal_sequence"] == 3 and document["previous_record_id"] == credential_id, "checkpoint journal chain changed")
    _expect(document["execution_source_closure"] == source and document["credential_observation_bundle"] == credentials and document[_SOURCE_ID] == source_id and document[_CREDENTIAL_ID] == credential_id, "checkpoint embedded-child join changed")
    _expect(document["root_embeds_complete_child_documents"] is True and document["checkpoint_durable_before_runtime_shutdown"] is True and document["portable_observation_checkpoint_present"] is True and document["durable_portable_observation_graph_present"] is True and document["checkpoint_bytes_describe_historical_live_observation"] is True, "checkpoint positive observation semantics changed")
    _expect(document["checkpoint_bytes_encode_resume_capability"] is False and document["live_continuation_capability_portable"] is False, "checkpoint claimed a resume capability")
    _verify_live_observation(document["live_observation"])
    _verify_credential_bundle(credentials, source_id=source_id, live=document["live_observation"])
    _claims(document, "live checkpoint")
    return _content_id(document, domain=CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN, id_field=_CHECKPOINT_ID, label="live checkpoint")


def _record_id(document: Mapping[str, Any]) -> str:
    schema = document.get("schema")
    field = {_SOURCE_SCHEMA: _SOURCE_ID, _CREDENTIAL_SCHEMA: _CREDENTIAL_ID, _CHECKPOINT_SCHEMA: _CHECKPOINT_ID}.get(schema)
    if field is None:
        _fail("failure prefix contains an unknown record schema")
    return _sha(document.get(field), "failure-prefix record ID")


_NOT_APPLICABLE_ABORT = {
    "kind": "NOT_APPLICABLE",
    "reason": "NO_ABORT_RESULT",
}
_NOT_APPLICABLE_QUARANTINE = {
    "kind": "NOT_APPLICABLE",
    "reason": "NO_QUARANTINE",
}


def _verify_wait_rows(value: Any, *, allowed_pids: set[int], label: str) -> None:
    if type(value) is not list:
        _fail(f"{label} wait inventory changed")
    seen: set[int] = set()
    for index, row in enumerate(value):
        row = _exact_keys(
            row,
            {"si_pid", "si_uid", "si_signo", "si_status", "si_code"},
            f"{label} wait row {index}",
        )
        pid = _positive(row["si_pid"], f"{label} wait PID")
        _expect(pid in allowed_pids and pid not in seen, f"{label} reaped an unregistered or duplicate PID")
        seen.add(pid)
        _nonnegative(row["si_uid"], f"{label} wait uid")
        _expect(
            row["si_signo"] == int(signal.SIGCHLD),
            f"{label} wait signal changed",
        )
        _nonnegative(row["si_status"], f"{label} wait status")
        _positive(row["si_code"], f"{label} wait code")


def _verify_abort_control_result(
    value: Any,
    *,
    control_identity: Mapping[str, Any],
    sequences: tuple[int, int],
    label: str,
) -> None:
    value = _exact_keys(value, {"reaped", "empty_snapshots"}, label)
    reaped = value["reaped"]
    if type(reaped) is not list:
        _fail(f"{label} reaped inventory changed")
    allowed = {
        row.get("si_pid")
        for row in reaped
        if type(row) is dict and type(row.get("si_pid")) is int
    }
    _verify_wait_rows(reaped, allowed_pids=allowed, label=label)
    rows = value["empty_snapshots"]
    _expect(type(rows) is list and len(rows) == 2, f"{label} empty snapshots changed")
    for row, sequence in zip(rows, sequences, strict=True):
        _verify_cgroup_snapshot(
            row,
            sequence=sequence,
            expected_pids=[],
            control_identity=control_identity,
            label=f"{label} empty snapshot {sequence}",
        )


def _verify_inner_abort(
    value: Any,
    *,
    supervisor_pid: int,
    control_identity: Mapping[str, Any],
    strict_live_child: bool = False,
) -> None:
    value = _exact_keys(
        value,
        {
            "active_probe_pid",
            "children_before",
            "empty_snapshots",
            "reaped",
            "state",
            "supervisor_pid",
        },
        "inner abort",
    )
    _expect(
        value["active_probe_pid"] == -1
        and value["state"] == "ABORTED_CLOSED"
        and value["supervisor_pid"] == supervisor_pid,
        "inner abort state changed",
    )
    children = value["children_before"]
    if strict_live_child:
        _expect(
            children == [supervisor_pid],
            "live PUBLIC_ABORT child inventory changed",
        )
    else:
        _expect(
            type(children) is list and children in ([supervisor_pid], []),
            "inner abort child inventory changed",
        )
    _verify_wait_rows(
        value["reaped"],
        allowed_pids={supervisor_pid},
        label="inner abort",
    )
    if strict_live_child:
        _expect(
            type(value["reaped"]) is list
            and len(value["reaped"]) == 1
            and value["reaped"][0]["si_pid"] == supervisor_pid,
            "live PUBLIC_ABORT reap inventory changed",
        )
    elif children == [supervisor_pid]:
        _expect(
            any(row["si_pid"] == supervisor_pid for row in value["reaped"]),
            "inner abort did not reap the registered supervisor",
        )
    rows = value["empty_snapshots"]
    _expect(type(rows) is list and len(rows) == 2, "inner abort empty snapshots changed")
    for row, sequence in zip(rows, (9001, 9002), strict=True):
        _verify_cgroup_snapshot(
            row,
            sequence=sequence,
            expected_pids=[],
            control_identity=control_identity,
            label=f"inner abort empty snapshot {sequence}",
        )


def _verify_outer_abort_document(
    value: Any,
    *,
    control_identity: Mapping[str, Any],
    expected_supervisor_pid: int | None = None,
    expected_probe_pid: int | None = None,
    strict_live_child: bool = False,
) -> None:
    value = _exact_keys(
        value,
        {"empty_snapshots", "inner_abort", "probe_pid", "state", "supervisor_pid"},
        "outer abort document",
    )
    supervisor_pid = _positive(value["supervisor_pid"], "outer abort supervisor PID")
    probe_pid = _positive(value["probe_pid"], "outer abort probe PID")
    if expected_supervisor_pid is not None or expected_probe_pid is not None:
        _expect(
            (supervisor_pid, probe_pid)
            == (expected_supervisor_pid, expected_probe_pid),
            "failure cleanup/credential process identity join changed",
        )
    _expect(probe_pid != supervisor_pid and value["state"] == "ABORTED_CLOSED", "outer abort process state changed")
    _verify_inner_abort(
        value["inner_abort"],
        supervisor_pid=supervisor_pid,
        control_identity=control_identity,
        strict_live_child=strict_live_child,
    )
    rows = value["empty_snapshots"]
    _expect(type(rows) is list and len(rows) == 2, "outer abort empty snapshots changed")
    for row, sequence in zip(rows, (9996, 9997), strict=True):
        _verify_cgroup_snapshot(
            row,
            sequence=sequence,
            expected_pids=[],
            control_identity=control_identity,
            label=f"outer abort empty snapshot {sequence}",
        )


def _verify_begin_recovery_document(
    value: Any, *, control_identity: Mapping[str, Any]
) -> None:
    if type(value) is dict and value.get("state") == "ABORTED_CLOSED":
        _verify_outer_abort_document(value, control_identity=control_identity)
        return
    value = _exact_keys(value, {"state", "cleanup"}, "begin recovery document")
    _expect(value["state"] == "BEGIN_FAILURE_RECOVERED_CLOSED", "begin recovery state changed")
    cleanup = value["cleanup"]
    if type(cleanup) is dict and set(cleanup) == {"reaped", "empty_snapshots"}:
        _verify_abort_control_result(
            cleanup,
            control_identity=control_identity,
            sequences=(9901, 9902),
            label="begin recovery CONTROL abort",
        )
        return
    if type(cleanup) is dict and set(cleanup) == {
        "active_probe_pid",
        "children_before",
        "empty_snapshots",
        "reaped",
        "state",
        "supervisor_pid",
    }:
        supervisor_pid = _positive(
            cleanup.get("supervisor_pid"), "begin recovery supervisor PID"
        )
        _verify_inner_abort(
            cleanup,
            supervisor_pid=supervisor_pid,
            control_identity=control_identity,
        )
        return
    _fail("begin recovery cleanup schema changed")


def _verify_failure_cleanup(
    value: Any,
    *,
    raw_begin_returned: bool,
    expected_control_identity: Mapping[str, Any] | None,
    expected_supervisor_pid: int | None,
    expected_probe_pid: int | None,
) -> None:
    value = _exact_keys(
        value,
        {
            "raw_cleanup_completely_closed",
            "terminal_method",
            "terminal_document",
            "begin_failure_recovery_document",
            "empty_control_snapshots",
            "direct_children_after_cleanup",
            "ambient_fd_inventory_restored",
            "subreaper_state_restored",
        },
        "failure cleanup",
    )
    _expect(
        value["raw_cleanup_completely_closed"] is True
        and value["direct_children_after_cleanup"] == []
        and value["ambient_fd_inventory_restored"] is True
        and value["subreaper_state_restored"] is True,
        "failure cleanup is not completely closed",
    )
    snapshots = value["empty_control_snapshots"]
    _expect(type(snapshots) is list and len(snapshots) == 2, "failure cleanup empty snapshot inventory changed")
    first = snapshots[0]
    if type(first) is not dict:
        _fail("failure cleanup CONTROL identity is absent")
    control_identity = {
        "device": first.get("directory_device"),
        "inode": first.get("directory_inode"),
    }
    _nonnegative(control_identity["device"], "failure cleanup CONTROL device")
    _positive(control_identity["inode"], "failure cleanup CONTROL inode")
    if expected_control_identity is not None:
        _expect(
            control_identity
            == {
                "device": expected_control_identity.get("device"),
                "inode": expected_control_identity.get("inode"),
            },
            "failure cleanup/credential CONTROL identity join changed",
        )
    for row, sequence in zip(snapshots, (18001, 18002), strict=True):
        _verify_cgroup_snapshot(
            row,
            sequence=sequence,
            expected_pids=[],
            control_identity=control_identity,
            label=f"failure cleanup empty snapshot {sequence}",
        )

    method = value["terminal_method"]
    terminal = value["terminal_document"]
    recovery = value["begin_failure_recovery_document"]
    if method == "PUBLIC_ABORT":
        _expect(raw_begin_returned, "PUBLIC_ABORT lacks a returned raw handle")
        _verify_outer_abort_document(
            terminal,
            control_identity=control_identity,
            expected_supervisor_pid=expected_supervisor_pid,
            expected_probe_pid=expected_probe_pid,
            strict_live_child=True,
        )
        _expect(recovery == _NOT_APPLICABLE_QUARANTINE, "PUBLIC_ABORT fabricated begin recovery")
    elif method == "PUBLIC_BEGIN_FAILURE_RECOVERY":
        _expect(not raw_begin_returned, "begin recovery followed a returned raw handle")
        _expect(terminal == _NOT_APPLICABLE_ABORT, "begin recovery fabricated terminal document")
        _verify_begin_recovery_document(recovery, control_identity=control_identity)
    elif method == "NO_HANDLE_RUNTIME_ALREADY_CLOSED":
        _expect(not raw_begin_returned, "no-handle cleanup claims a returned raw handle")
        _expect(terminal == _NOT_APPLICABLE_ABORT and recovery == _NOT_APPLICABLE_QUARANTINE, "no-handle cleanup fabricated a terminal result")
    elif method in {
        "PUBLIC_NORMAL_CLOSE_ALREADY_COMMITTED",
        "PUBLIC_ABORT_ALREADY_COMMITTED",
    }:
        _expect(raw_begin_returned, "committed terminal cleanup lacks a returned handle")
        _expect(terminal == _NOT_APPLICABLE_ABORT and recovery == _NOT_APPLICABLE_QUARANTINE, "committed terminal cleanup fabricated a result")
    else:
        _fail("failure cleanup terminal method changed")


def _verify_failure_closure(document: dict[str, Any], *, prefix: tuple[dict[str, Any], ...], prefix_raw: tuple[bytes, ...]) -> str:
    keys = {
        "schema", "schema_version", "profile_key", "readiness", "terminal_class",
        "terminal_code", "source_closure", "journal_sequence", "previous_record_id",
        "raw_begin_returned", "failure_type", "failure_message", "cleanup",
        "journal_records_before_failure_closure", "failure_closure_is_not_infeasibility",
        "failure_closure_is_not_plan_certificate", _FAILURE_ID, *_LOCKED_CLAIMS,
    }
    _exact_keys(document, keys, "failure closure")
    _expect(document["schema"] == _FAILURE_SCHEMA and document["schema_version"] == SCHEMA_VERSION and document["profile_key"] == PRODUCER_PROFILE_KEY, "failure closure identity changed")
    _expect(document["readiness"] == "ATTEMPT_CLOSURE_NONCERTIFICATE" and document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE" and document["terminal_code"] == "PROTOCOL_FAILURE", "failure terminal classification changed")
    _expect(document["journal_sequence"] == len(prefix) + 1, "failure sequence changed")
    _expect(
        type(document["raw_begin_returned"]) is bool,
        "failure raw-begin outcome changed type",
    )
    if prefix:
        _expect(
            document["raw_begin_returned"] is True,
            "failure persisted a canonical prefix before raw begin returned",
        )
    expected_previous: Any = _record_id(prefix[-1]) if prefix else {"kind": "GENESIS", "reason": "NO_PREDECESSOR_RECORD"}
    _expect(document["previous_record_id"] == expected_previous, "failure predecessor changed")
    _expect(type(document["failure_type"]) is str and bool(document["failure_type"]) and type(document["failure_message"]) is str, "failure diagnostics changed type")
    expected_control_identity = (
        prefix[1].get("control_cgroup_identity") if len(prefix) >= 2 else None
    )
    _verify_failure_cleanup(
        document["cleanup"],
        raw_begin_returned=document["raw_begin_returned"],
        expected_control_identity=expected_control_identity,
        expected_supervisor_pid=(
            prefix[1].get("supervisor_pid") if len(prefix) >= 2 else None
        ),
        expected_probe_pid=(
            prefix[1].get("probe_pid") if len(prefix) >= 2 else None
        ),
    )
    _expect(document["failure_closure_is_not_infeasibility"] is True and document["failure_closure_is_not_plan_certificate"] is True, "failure closure claimed a certificate")
    _claims(document, "failure closure")
    source = document["source_closure"]
    if source == {"kind": "NOT_AVAILABLE", "reason": "SOURCE_FREEZE_DID_NOT_COMPLETE"}:
        _expect(document["raw_begin_returned"] is False, "failure omitted source bytes after raw begin")
        _expect(not prefix or prefix[0].get("schema") != _SOURCE_SCHEMA, "failure omitted an available source closure")
    else:
        if type(source) is not dict:
            _fail("failure source closure is neither full bytes nor typed absence")
        source_id = _verify_source_closure(source)
        if prefix and prefix[0].get("schema") == _SOURCE_SCHEMA:
            _expect(source == prefix[0] and source_id == _record_id(prefix[0]), "failure embedded source diverged from prefix")
    facts = document["journal_records_before_failure_closure"]
    _expect(type(facts) is list and len(facts) == len(prefix), "failure journal-fact inventory changed")
    labels = { _SOURCE_SCHEMA: "EXECUTION_SOURCE_CLOSURE", _CREDENTIAL_SCHEMA: "CREDENTIAL_OBSERVATION_BUNDLE", _CHECKPOINT_SCHEMA: "LIVE_PREFIX_CHECKPOINT" }
    for index, (fact, prior, raw) in enumerate(zip(facts, prefix, prefix_raw, strict=True), start=1):
        fact = _exact_keys(fact, {"sequence", "label", "record_id", "filename", "byte_count", "sha256", "file_fsync_complete", "directory_fsync_complete"}, f"failure journal fact {index}")
        record_id = _record_id(prior)
        _expect(fact["sequence"] == index and fact["label"] == labels[prior["schema"]] and fact["record_id"] == record_id, f"failure journal fact {index} identity changed")
        _expect(fact["filename"] == f"{index:06d}_{fact['label']}_{record_id}.json", f"failure journal fact {index} filename changed")
        _expect(fact["byte_count"] == len(raw) and fact["sha256"] == hashlib.sha256(raw).hexdigest(), f"failure journal fact {index} bytes changed")
        _expect(type(fact["file_fsync_complete"]) is bool and type(fact["directory_fsync_complete"]) is bool, f"failure journal fact {index} durability type changed")
    return _content_id(document, domain=CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN, id_field=_FAILURE_ID, label="failure closure")


@dataclass(frozen=True, slots=True)
class TwoBirthPortableCheckpointIndependentVerificationV1:
    outcome: str
    success_observation_verified: bool
    typed_noncertificate_verified: bool
    journal_record_count: int
    source_closure_id: str | None
    credential_bundle_id: str | None
    live_checkpoint_id: str | None
    failure_closure_id: str | None
    portable_checkpoint_authority_present: bool = False
    two_birth_prefix_authority_present: bool = False
    official_execution_allowed: bool = False

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_two_birth_portable_checkpoint_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "readiness": READINESS,
            "outcome": self.outcome,
            "success_observation_verified": self.success_observation_verified,
            "typed_noncertificate_verified": self.typed_noncertificate_verified,
            "journal_record_count": self.journal_record_count,
            "source_closure_id": self.source_closure_id,
            "credential_bundle_id": self.credential_bundle_id,
            "live_checkpoint_id": self.live_checkpoint_id,
            "failure_closure_id": self.failure_closure_id,
            "portable_checkpoint_authority_present": False,
            "two_birth_prefix_authority_present": False,
            "official_execution_allowed": False,
        }


def verify_two_birth_portable_checkpoint_journal_bytes_v1(
    record_bytes: tuple[bytes, ...],
) -> TwoBirthPortableCheckpointIndependentVerificationV1:
    """Verify one complete V18 success journal or typed failure journal.

    The tuple order is the append order.  A successful observation requires
    exactly source, credentials, and root.  Any terminal failure-closure row
    selects the noncertificate branch even when all three earlier rows exist.
    """

    if type(record_bytes) is not tuple or not record_bytes or len(record_bytes) > 4:
        _fail("journal bytes must be one nonempty tuple of at most four records")
    records = tuple(_parse_record(raw, index) for index, raw in enumerate(record_bytes, start=1))
    schemas = tuple(record.get("schema") for record in records)
    if schemas == (_SOURCE_SCHEMA, _CREDENTIAL_SCHEMA, _CHECKPOINT_SCHEMA):
        source, credentials, checkpoint = records
        source_id = _verify_source_closure(source)
        credential_id = _verify_credential_bundle(credentials, source_id=source_id)
        checkpoint_id = _verify_checkpoint(checkpoint, source=source, credentials=credentials, source_id=source_id, credential_id=credential_id)
        return TwoBirthPortableCheckpointIndependentVerificationV1(
            SUCCESS_OUTCOME, True, False, 3,
            source_id, credential_id, checkpoint_id, None,
        )
    if schemas[-1:] == (_FAILURE_SCHEMA,):
        prefix = records[:-1]
        allowed_prefix = (_SOURCE_SCHEMA, _CREDENTIAL_SCHEMA, _CHECKPOINT_SCHEMA)[: len(prefix)]
        if tuple(item.get("schema") for item in prefix) != allowed_prefix:
            _fail("failure journal prefix is not the canonical source/credential/root prefix")
        source_id: str | None = None
        credential_id: str | None = None
        checkpoint_id: str | None = None
        if len(prefix) >= 1:
            source_id = _verify_source_closure(prefix[0])
        if len(prefix) >= 2:
            assert source_id is not None
            credential_id = _verify_credential_bundle(prefix[1], source_id=source_id)
        if len(prefix) == 3:
            assert source_id is not None and credential_id is not None
            checkpoint_id = _verify_checkpoint(prefix[2], source=prefix[0], credentials=prefix[1], source_id=source_id, credential_id=credential_id)
        failure_id = _verify_failure_closure(records[-1], prefix=prefix, prefix_raw=record_bytes[:-1])
        return TwoBirthPortableCheckpointIndependentVerificationV1(
            NONCERTIFICATE_OUTCOME, False, True, len(records),
            source_id, credential_id, checkpoint_id, failure_id,
        )
    _fail("journal inventory is neither the exact success graph nor a typed failure closure")


__all__ = (
    "NONCERTIFICATE_OUTCOME",
    "PROFILE_KEY",
    "READINESS",
    "SCHEMA_VERSION",
    "SUCCESS_OUTCOME",
    "TwoBirthPortableCheckpointIndependentVerificationV1",
    "TwoBirthPortableCheckpointIndependentVerificationViolation",
    "verify_two_birth_portable_checkpoint_journal_bytes_v1",
)
