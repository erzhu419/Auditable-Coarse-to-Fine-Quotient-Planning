"""Construction semantic closure and exact-current Owner-tail attestation.

The 59D prefix checker was deliberately synchronous: it proved a dispatch
prefix against one observed Owner tail but issued no artifact whose identity
bound that tail.  This module freezes the Python verifier semantics used for
that check and issues a content-addressed attestation for one caller-pinned
current tail.  Any later Owner append invalidates exact-current verification;
future extensions must issue a new attestation.

The closure is runtime-retained and source-byte bound.  It is not a generic
cross-process source authority, and the attestation does not authorize cleanup,
normal execution, accounting, route choice, or terminal classification.
"""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from dataclasses import InitVar, dataclass, field
import dis
from enum import Enum, EnumMeta
import hashlib
import hmac
import inspect
from pathlib import Path
import re
import sys
from types import FunctionType, MappingProxyType, ModuleType
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_domain_registry_extension_v1 as domains_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp import phase3e_ids as ids_v1
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-A"
PROFILE_KEY = "construction_k7_h1_tail_bound_prefix_attestation_v1"

SEMANTIC_CLOSURE_DOMAIN = (
    domains_v1.CONSTRUCTION_K7_H1_PREFIX_VERIFIER_SEMANTIC_CLOSURE_V1_DOMAIN
)
TAIL_ATTESTATION_DOMAIN = (
    domains_v1.CONSTRUCTION_K7_H1_TAIL_BOUND_PREFIX_ATTESTATION_V1_DOMAIN
)

PREFIX_VERIFIER_SEMANTIC_CLOSURE_PRESENT = True
EXACT_CURRENT_TAIL_ATTESTATION_PRESENT = True
CROSS_PROCESS_SOURCE_AUTHORITY_PRESENT = False
FUTURE_APPEND_VALIDITY = False
NO_EVENT_RECOVERY_COMPLETE = False
CLEANUP_EXECUTION_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORD_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

_CLOSURE_ISSUER = object()
_ATTESTATION_ISSUER = object()


class ConstructionK7H1TailBoundPrefixAttestationV1Error(ValueError):
    """The semantic closure, dispatch prefix, or exact Owner tail changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1TailBoundPrefixAttestationV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1TailBoundPrefixAttestationV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _stable_code_value(value: Any) -> Any:
    if type(value) is type(_stable_code_value.__code__):
        return _stable_code_document(value)
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is bytes:
        return {"kind": "BYTES", "hex": value.hex()}
    if type(value) is tuple:
        return {"kind": "TUPLE", "items": [_stable_code_value(v) for v in value]}
    if type(value) is frozenset:
        return {
            "kind": "FROZENSET",
            "items": _sort_projected(
                [_stable_code_value(item) for item in value]
            ),
        }
    if type(value) is float:
        return {"kind": "FLOAT", "hex": value.hex()}
    return {
        "kind": "CODE_CONSTANT",
        "type": f"{type(value).__module__}.{type(value).__qualname__}",
        "repr": repr(value),
    }


def _stable_code_document(code: Any) -> dict[str, Any]:
    return {
        "argcount": code.co_argcount,
        "posonlyargcount": code.co_posonlyargcount,
        "kwonlyargcount": code.co_kwonlyargcount,
        "nlocals": code.co_nlocals,
        "stacksize": code.co_stacksize,
        "flags": code.co_flags,
        "code_hex": code.co_code.hex(),
        "exception_table_hex": getattr(code, "co_exceptiontable", b"").hex(),
        "constants": [_stable_code_value(value) for value in code.co_consts],
        "names": list(code.co_names),
        "varnames": list(code.co_varnames),
        "freevars": list(code.co_freevars),
        "cellvars": list(code.co_cellvars),
    }


def _sort_projected(values: list[Any]) -> list[Any]:
    return sorted(values, key=canonical_json_bytes)


def _project_semantic_value(value: Any) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is bytes:
        return {"kind": "BYTES", "hex": value.hex()}
    if type(value) is float:
        return {"kind": "FLOAT", "hex": value.hex()}
    if type(value) is tuple:
        return {
            "kind": "TUPLE",
            "items": [_project_semantic_value(item) for item in value],
        }
    if type(value) is list:
        return {
            "kind": "LIST",
            "items": [_project_semantic_value(item) for item in value],
        }
    if type(value) in {set, frozenset}:
        return {
            "kind": type(value).__name__.upper(),
            "items": _sort_projected(
                [_project_semantic_value(item) for item in value]
            ),
        }
    if type(value) in {dict, MappingProxyType}:
        rows = [
            {
                "key": _project_semantic_value(key),
                "value": _project_semantic_value(child),
            }
            for key, child in value.items()
        ]
        return {
            "kind": "MAPPING",
            "items": sorted(rows, key=lambda row: canonical_json_bytes(row["key"])),
        }
    if isinstance(value, re.Pattern):
        return {
            "kind": "REGEX",
            "pattern": value.pattern,
            "flags": value.flags,
        }
    if isinstance(value, EnumMeta):
        return {
            "kind": "ENUM_TYPE",
            "type": f"{value.__module__}.{value.__qualname__}",
            "members": [
                {"name": name, "value": _project_semantic_value(member.value)}
                for name, member in value.__members__.items()
            ],
        }
    if isinstance(value, Enum):
        return {
            "kind": "ENUM_MEMBER",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "name": value.name,
            "value": _project_semantic_value(value.value),
        }
    if isinstance(value, ContextVar):
        return {"kind": "CONTEXT_VAR", "name": value.name}
    if isinstance(value, ModuleType):
        return {"kind": "MODULE_REFERENCE", "name": value.__name__}
    if isinstance(value, type):
        return {
            "kind": "TYPE_REFERENCE",
            "module": value.__module__,
            "qualname": value.__qualname__,
        }
    if type(value) is object:
        return {
            "kind": "OPAQUE_RUNTIME_IDENTITY_SENTINEL",
            "type": "builtins.object",
            "cross_process_value_present": False,
        }
    if isinstance(value, (classmethod, staticmethod)):
        function = value.__func__
        return {
            "kind": type(value).__name__.upper(),
            "function": {
                "module": function.__module__,
                "qualname": function.__qualname__,
            },
        }
    if isinstance(value, property):
        return {
            "kind": "PROPERTY",
            "getter": _project_semantic_value(value.fget),
            "setter": _project_semantic_value(value.fset),
            "deleter": _project_semantic_value(value.fdel),
        }
    if inspect.ismethoddescriptor(value) or inspect.isdatadescriptor(value):
        owner = getattr(value, "__objclass__", None)
        return {
            "kind": "DESCRIPTOR_REFERENCE",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "name": getattr(value, "__name__", None),
            "owner": (
                f"{owner.__module__}.{owner.__qualname__}"
                if isinstance(owner, type)
                else None
            ),
        }
    if type(value) is FunctionType:
        return {
            "kind": "PYTHON_FUNCTION_SEMANTIC_REFERENCE",
            "function": _function_row(value),
            "transitive_globals_bound_here": False,
        }
    if callable(value):
        return {
            "kind": "CALLABLE_REFERENCE",
            "module": getattr(value, "__module__", type(value).__module__),
            "qualname": getattr(value, "__qualname__", type(value).__qualname__),
        }
    return {
        "kind": "OPAQUE_RUNTIME_OBJECT",
        "type": f"{type(value).__module__}.{type(value).__qualname__}",
        "repr": repr(value),
        "runtime_identity_required": True,
        "cross_process_value_present": False,
    }


def _function_row(function: Callable[..., Any]) -> dict[str, Any]:
    if type(function) is not FunctionType:
        _fail("prefix semantic closure expected one Python function")
    document = {
        "module": function.__module__,
        "qualname": function.__qualname__,
        "code": _stable_code_document(function.__code__),
        "defaults": _project_semantic_value(function.__defaults__),
        "kwdefaults": _project_semantic_value(function.__kwdefaults__),
        "closure_cells": [
            _project_semantic_value(cell.cell_contents)
            for cell in (function.__closure__ or ())
        ],
    }
    return {
        **document,
        "function_semantic_id": hashlib.sha256(
            b"acfqp:k7-h1-prefix-function-semantic:v1\x00"
            + canonical_json_bytes(document)
        ).hexdigest(),
    }


def _module_row(module: ModuleType) -> dict[str, Any]:
    path = Path(module.__file__).resolve(strict=True)
    raw = path.read_bytes()
    if not raw:
        _fail("prefix semantic closure module source is empty")
    return {
        "module": module.__name__,
        "loaded_realpath": str(path),
        "source_byte_count": len(raw),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _same_module_function_closure(
    module: ModuleType,
    roots: tuple[str, ...],
) -> dict[str, FunctionType]:
    namespace = vars(module)
    pending = list(roots)
    result: dict[str, FunctionType] = {}
    while pending:
        name = pending.pop()
        if name in result:
            continue
        function = namespace.get(name)
        if type(function) is not FunctionType or function.__module__ != module.__name__:
            _fail(f"prefix semantic root/dependency changed: {module.__name__}.{name}")
        result[name] = function
        for dependency_name in function.__code__.co_names:
            dependency = namespace.get(dependency_name)
            if (
                type(dependency) is FunctionType
                and dependency.__module__ == module.__name__
                and dependency_name not in result
            ):
                pending.append(dependency_name)
    return dict(sorted(result.items()))


_MODULES = (
    sys.modules[__name__],
    owner_v3,
    owner_v4,
    dispatch_v1,
    rejection_v1,
    ids_v1,
    domains_v1,
)
_ROOTS = {
    sys.modules[__name__]: (
        "issue_h1_tail_bound_prefix_attestation_v1",
        "extend_h1_tail_bound_prefix_attestation_v1",
        "verify_h1_tail_bound_prefix_attestation_exact_current_bytes_v1",
        "verify_h1_tail_bound_prefix_attestation_extension_observed_current_bytes_v1",
    ),
    owner_v3: ("inspect_h1_shared_cap_owner_v3_record_prefix",),
    owner_v4: ("replay_h1_shared_cap_owner_v4_wal",),
    dispatch_v1: ("verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1",),
}
_EXTERNAL_FUNCTIONS = (
    rejection_v1.acknowledge_h1_attempt_rejection_v1,
    rejection_v1.commit_h1_attempt_rejection_with_admission_lease_v1,
    rejection_v1.hold_h1_attempt_gate_open_for_admission_v1,
    rejection_v1.hold_h1_attempt_gate_open_for_side_effect_v1,
    rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1,
    rejection_v1.open_h1_attempt_rejection_gate_v1,
    ids_v1.canonical_json_bytes,
    ids_v1.content_id,
    ids_v1.loads_canonical_json,
    ids_v1.parse_content_id,
    domains_v1.extension_content_id_v1,
)
_EXTERNAL_PROTOCOL_TYPES = (contextlib._GeneratorContextManager,)
_IMPLICIT_PROTOCOL_ATTRIBUTES = frozenset(
    {
        "__bool__",
        "__call__",
        "__contains__",
        "__enter__",
        "__eq__",
        "__exit__",
        "__ge__",
        "__getitem__",
        "__gt__",
        "__hash__",
        "__init__",
        "__iter__",
        "__le__",
        "__len__",
        "__lt__",
        "__new__",
        "__next__",
        "__post_init__",
    }
)


def _derive_semantic_payload_and_refs() -> tuple[
    dict[str, Any],
    dict[str, FunctionType],
    dict[str, Any],
    dict[str, ModuleType],
]:
    functions: dict[str, FunctionType] = {}
    globals_by_key: dict[str, Any] = {}
    allowed_module_names = {module.__name__ for module in _MODULES}
    pending: list[FunctionType] = []
    function_ordinals: dict[int, int] = {}

    def register_binding(key: str, value: Any) -> None:
        if key in globals_by_key and globals_by_key[key] is not value:
            _fail(f"prefix semantic binding changed identity: {key}")
        globals_by_key[key] = value

    def enqueue(function: Any, binding_key: str) -> None:
        if type(function) is not FunctionType:
            _fail(f"prefix semantic Python dependency changed: {binding_key}")
        if function.__module__ not in allowed_module_names:
            _fail(
                "prefix semantic closure reached an unregistered Python module: "
                f"{function.__module__}"
            )
        register_binding(binding_key, function)
        function_ordinals.setdefault(id(function), len(function_ordinals))
        pending.append(function)

    def register_nested_identity(
        parent_key: str,
        value: Any,
        seen: set[int] | None = None,
    ) -> None:
        visited = set() if seen is None else seen
        if type(value) in {dict, MappingProxyType}:
            if id(value) in visited:
                _fail("prefix semantic nested mapping contains a cycle")
            visited.add(id(value))
            rows = sorted(
                value.items(),
                key=lambda item: canonical_json_bytes(
                    _project_semantic_value(item[0])
                ),
            )
            for index, (key, child) in enumerate(rows):
                register_nested_identity(
                    f"{parent_key}:mapping-key:{index}", key, visited
                )
                register_nested_identity(
                    f"{parent_key}:mapping-value:{index}", child, visited
                )
            visited.remove(id(value))
            return
        if type(value) in {tuple, list, set, frozenset}:
            if id(value) in visited:
                _fail("prefix semantic nested collection contains a cycle")
            visited.add(id(value))
            children = list(value)
            if type(value) in {set, frozenset}:
                children = sorted(
                    children,
                    key=lambda child: canonical_json_bytes(
                        _project_semantic_value(child)
                    ),
                )
            for index, child in enumerate(children):
                register_nested_identity(
                    f"{parent_key}:item:{index}", child, visited
                )
            visited.remove(id(value))
            return
        if value is None or type(value) in {bool, int, str, bytes, float}:
            return
        nested_key = f"nested-identity:{parent_key}"
        register_binding(nested_key, value)
        if type(value) is FunctionType and value.__module__ in allowed_module_names:
            enqueue(value, nested_key)

    for module, roots in _ROOTS.items():
        namespace = vars(module)
        for name in roots:
            enqueue(namespace.get(name), f"root:{module.__name__}:{name}")
    for function in _EXTERNAL_FUNCTIONS:
        enqueue(
            function,
            f"root:external:{function.__module__}:{function.__qualname__}",
        )

    def enqueue_descriptor_functions(value: Any, binding_key: str) -> None:
        candidates: tuple[Any, ...]
        if type(value) is FunctionType:
            candidates = (value,)
        elif isinstance(value, (classmethod, staticmethod)):
            candidates = (value.__func__,)
        elif isinstance(value, property):
            candidates = tuple(
                function
                for function in (value.fget, value.fset, value.fdel)
                if function is not None
            )
        else:
            candidates = ()
        for index, function in enumerate(candidates):
            if (
                type(function) is FunctionType
                and function.__module__ in allowed_module_names
            ):
                enqueue(function, f"{binding_key}:callable:{index}")

    def drain_pending_functions() -> None:
        while pending:
            function = pending.pop()
            semantic_id = _function_row(function)["function_semantic_id"]
            function_ordinal = function_ordinals[id(function)]
            function_key = (
                f"function:{function.__module__}:{function.__qualname__}:"
                f"{semantic_id}:{function_ordinal}"
            )
            existing = functions.get(function_key)
            if existing is not None:
                if existing is not function:
                    _fail(
                        f"prefix semantic function identity collided: {function_key}"
                    )
                continue
            functions[function_key] = function
            namespace = function.__globals__
            for global_name in function.__code__.co_names:
                if global_name not in namespace:
                    continue
                value = namespace[global_name]
                binding_key = f"dependency:{function_key}:{global_name}"
                register_binding(binding_key, value)
                register_nested_identity(binding_key, value)
                if (
                    type(value) is FunctionType
                    and value.__module__ in allowed_module_names
                ):
                    enqueue(value, binding_key)
                if isinstance(value, type):
                    for attribute_name in function.__code__.co_names:
                        try:
                            attribute_value = inspect.getattr_static(
                                value, attribute_name
                            )
                        except AttributeError:
                            continue
                        attribute_key = (
                            f"type-attribute:{function_key}:{global_name}:"
                            f"{attribute_name}"
                        )
                        register_binding(attribute_key, attribute_value)
                        register_nested_identity(attribute_key, attribute_value)
                        enqueue_descriptor_functions(attribute_value, attribute_key)
            instructions = tuple(dis.get_instructions(function))
            for instruction_index, instruction in enumerate(instructions):
                if instruction.opname not in {"LOAD_GLOBAL", "LOAD_NAME"}:
                    continue
                global_name = instruction.argval
                if global_name not in namespace:
                    continue
                current = namespace[global_name]
                for attribute_instruction in instructions[instruction_index + 1 :]:
                    if attribute_instruction.opname not in {
                        "LOAD_ATTR",
                        "LOAD_METHOD",
                    }:
                        break
                    attribute_name = attribute_instruction.argval
                    try:
                        if isinstance(current, ModuleType):
                            attribute_value = vars(current)[attribute_name]
                        else:
                            attribute_value = inspect.getattr_static(
                                current, attribute_name
                            )
                    except (KeyError, AttributeError):
                        break
                    attribute_key = (
                        f"attribute:{function_key}:{global_name}:"
                        f"{attribute_name}"
                    )
                    register_binding(attribute_key, attribute_value)
                    register_nested_identity(attribute_key, attribute_value)
                    enqueue_descriptor_functions(attribute_value, attribute_key)
                    current = attribute_value
            for index, cell in enumerate(function.__closure__ or ()):
                try:
                    cell_value = cell.cell_contents
                except ValueError as error:
                    raise ConstructionK7H1TailBoundPrefixAttestationV1Error(
                        "prefix semantic closure contains an empty cell"
                    ) from error
                closure_key = f"closure:{function_key}:{index}"
                register_binding(closure_key, cell_value)
                register_nested_identity(closure_key, cell_value)

    # A receiver's class can be loaded in one verifier function while a
    # property or method is read in another.  Binding only same-function
    # ``global type + co_names`` pairs therefore misses runtime replacement of
    # that descriptor.  Close the set to a fixed point over every referenced
    # project type and every attribute name read anywhere in the function
    # closure.  Descriptor callables discovered here are themselves enqueued,
    # so their registered-module dependencies are transitively closed too.
    processed_receiver_attributes: set[tuple[str, str]] = set()
    while True:
        drain_pending_functions()
        attribute_names = {
            instruction.argval
            for function in functions.values()
            for instruction in dis.get_instructions(function)
            if instruction.opname in {"LOAD_ATTR", "LOAD_METHOD"}
            and type(instruction.argval) is str
        }
        referenced_behavior_types: dict[str, type] = {}

        def register_behavior_type(value: type, *, external: bool = False) -> None:
            if not external and value.__module__ not in allowed_module_names:
                return
            type_key = (
                f"{value.__module__}:{value.__qualname__}:runtime-{id(value):x}"
            )
            referenced_behavior_types[type_key] = value
            for base in value.__mro__[1:]:
                if base.__module__ in allowed_module_names:
                    register_behavior_type(base)

        for value in globals_by_key.values():
            if isinstance(value, type):
                register_behavior_type(value)
        for value in _EXTERNAL_PROTOCOL_TYPES:
            register_behavior_type(value, external=True)
            for base in value.__mro__[1:]:
                if base is not object:
                    register_behavior_type(base, external=True)
        discovered = False
        for type_key, receiver_type in sorted(referenced_behavior_types.items()):
            behavior_namespace = {
                name: value
                for name, value in vars(receiver_type).items()
                if (
                    type(value) is FunctionType
                    or isinstance(value, (classmethod, staticmethod, property))
                    or inspect.ismethoddescriptor(value)
                    or inspect.isdatadescriptor(value)
                    or callable(value)
                )
            }
            for attribute_name, attribute_value in sorted(
                behavior_namespace.items()
            ):
                pair = (type_key, attribute_name)
                if pair in processed_receiver_attributes:
                    continue
                processed_receiver_attributes.add(pair)
                attribute_key = (
                    f"behavior-type-attribute:{type_key}:{attribute_name}"
                )
                register_binding(attribute_key, attribute_value)
                register_nested_identity(attribute_key, attribute_value)
                if (
                    attribute_name in attribute_names
                    or attribute_name in _IMPLICIT_PROTOCOL_ATTRIBUTES
                ):
                    enqueue_descriptor_functions(attribute_value, attribute_key)
                discovered = True
        if not pending and not discovered:
            break

    modules = {module.__name__: module for module in _MODULES}
    function_rows = [
        {"binding_key": key, **_function_row(function)}
        for key, function in sorted(functions.items())
    ]
    global_rows = [
        {
            "binding_key": key,
            "semantic_value": _project_semantic_value(value),
        }
        for key, value in sorted(globals_by_key.items())
    ]
    payload = {
        "schema": "acfqp.k7_h1_prefix_verifier_semantic_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "module_rows": [_module_row(module) for module in _MODULES],
        "function_rows": function_rows,
        "semantic_global_rows": global_rows,
        "module_count": len(_MODULES),
        "function_count": len(function_rows),
        "classified_global_name_count": len(global_rows),
        "unclassified_global_names": [],
        "function_code_defaults_kwdefaults_bound": True,
        "mutable_semantic_globals_deep_projected": True,
        "opaque_runtime_objects_identity_bound": True,
        "external_dependency_entrypoints_bound": True,
        "closure_complete_for_registered_python_dependencies": True,
        "registered_closure_cell_dependencies_transitively_bound": True,
        "unregistered_python_entrypoint_code_bound_nontransitively": True,
        "dynamic_type_method_identity_bound": True,
        "cross_function_project_type_attribute_identity_bound": True,
        "project_type_behavior_namespace_identity_bound": True,
        "registered_contextmanager_protocol_identity_bound": True,
        "hostile_stdlib_or_interpreter_monkeypatch_complete": False,
        "runtime_object_identity_retained": True,
        "cross_process_source_authority_present": False,
        "external_expected_closure_binding_present": False,
        "production_execution_authority_present": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return payload, functions, globals_by_key, modules


@dataclass(frozen=True, slots=True)
class H1PrefixVerifierSemanticClosureV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    function_refs: tuple[tuple[str, FunctionType], ...] = field(repr=False)
    global_refs: tuple[tuple[str, Any], ...] = field(repr=False)
    module_refs: tuple[tuple[str, ModuleType], ...] = field(repr=False)
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CLOSURE_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("prefix semantic closure is caller-minted")
        payload = loads_canonical_json(self.payload_bytes)
        if type(payload) is not dict or canonical_json_bytes(payload) != self.payload_bytes:
            _fail("prefix semantic closure payload is not canonical")
        object.__setattr__(
            self,
            "_closure_id",
            domains_v1.extension_content_id_v1(SEMANTIC_CLOSURE_DOMAIN, payload),
        )

    @property
    def closure_id(self) -> str:
        return self._closure_id

    @property
    def payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self.payload_bytes)
        if type(value) is not dict:  # pragma: no cover - issuer invariant
            _fail("prefix semantic closure changed type")
        return value

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self.payload,
            "h1_prefix_verifier_semantic_closure_id": self.closure_id,
        }


def inspect_h1_prefix_verifier_semantic_closure_candidate_v1(
) -> H1PrefixVerifierSemanticClosureV1:
    payload, functions, globals_by_key, modules = _derive_semantic_payload_and_refs()
    return H1PrefixVerifierSemanticClosureV1(
        _CLOSURE_ISSUER,
        canonical_json_bytes(payload),
        tuple(sorted(functions.items())),
        tuple(sorted(globals_by_key.items())),
        tuple(sorted(modules.items())),
    )


def freeze_h1_prefix_verifier_semantic_closure_v1(
    *,
    expected_closure_id: str,
) -> H1PrefixVerifierSemanticClosureV1:
    expected = _cid(expected_closure_id, "expected prefix semantic closure")
    value = inspect_h1_prefix_verifier_semantic_closure_candidate_v1()
    if not hmac.compare_digest(value.closure_id, expected):
        _fail("caller-pinned prefix semantic closure ID differs from current semantics")
    return value


def _require_live_semantic_closure(
    value: H1PrefixVerifierSemanticClosureV1,
) -> H1PrefixVerifierSemanticClosureV1:
    if type(value) is not H1PrefixVerifierSemanticClosureV1:
        _fail("tail attestation requires one exact semantic closure")
    payload, functions, globals_by_key, modules = _derive_semantic_payload_and_refs()
    if (
        not hmac.compare_digest(canonical_json_bytes(payload), value.payload_bytes)
        or tuple(sorted(functions)) != tuple(key for key, _ in value.function_refs)
        or tuple(sorted(globals_by_key))
        != tuple(key for key, _ in value.global_refs)
        or tuple(sorted(modules)) != tuple(key for key, _ in value.module_refs)
        or any(functions[key] is not original for key, original in value.function_refs)
        or any(globals_by_key[key] is not original for key, original in value.global_refs)
        or any(modules[key] is not original for key, original in value.module_refs)
    ):
        _fail("prefix verifier semantics changed after closure issuance")
    return value


def verify_h1_prefix_verifier_semantic_closure_bytes_v1(
    raw: bytes,
    *,
    expected_closure_id: str,
) -> H1PrefixVerifierSemanticClosureV1:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1TailBoundPrefixAttestationV1Error(
            "prefix semantic closure bytes are not canonical"
        ) from error
    if type(document) is not dict:
        _fail("prefix semantic closure document must be one object")
    claimed = _cid(
        document.pop("h1_prefix_verifier_semantic_closure_id", None),
        "prefix semantic closure",
    )
    expected = freeze_h1_prefix_verifier_semantic_closure_v1(
        expected_closure_id=expected_closure_id
    )
    if (
        claimed != expected.closure_id
        or domains_v1.extension_content_id_v1(SEMANTIC_CLOSURE_DOMAIN, document)
        != claimed
        or canonical_json_bytes(document) != expected.payload_bytes
    ):
        _fail("prefix semantic closure differs from exact reconstruction")
    return expected


@dataclass(frozen=True, slots=True)
class H1TailBoundPrefixAttestationV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("tail-bound prefix attestation is caller-minted")
        payload = loads_canonical_json(self.payload_bytes)
        if type(payload) is not dict or canonical_json_bytes(payload) != self.payload_bytes:
            _fail("tail-bound prefix attestation payload is not canonical")
        object.__setattr__(
            self,
            "_attestation_id",
            domains_v1.extension_content_id_v1(TAIL_ATTESTATION_DOMAIN, payload),
        )

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    @property
    def payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self.payload_bytes)
        if type(value) is not dict:  # pragma: no cover
            _fail("tail-bound prefix attestation changed type")
        return value

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self.payload,
            "h1_tail_bound_prefix_attestation_id": self.attestation_id,
        }


def _ordered_owner_records(index: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = [
        dict(record)
        for rows in index["records_by_role"].values()
        for record in rows
    ]
    by_sequence = sorted(records, key=lambda row: row["sequence"])
    if (
        len(by_sequence) != index["journal_sequence"]
        or [row["sequence"] for row in by_sequence]
        != list(range(1, len(by_sequence) + 1))
    ):
        _fail("Owner index does not expose one exact ordered record tail")
    return by_sequence


def _record_ids(records: list[dict[str, Any]]) -> list[str]:
    return [owner_v3._record_id(record) for record in records]


def _issue_tail_attestation(
    trace_bytes: bytes,
    *,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    profile: dispatch_v1.H1LifecycleDispatchProfileV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    semantic_closure: H1PrefixVerifierSemanticClosureV1,
    expected_tail_sequence: int,
    expected_tail_head_id: Any,
    predecessor_attestation_id: Any,
) -> H1TailBoundPrefixAttestationV1:
    closure = _require_live_semantic_closure(semantic_closure)
    if (
        type(trace_bytes) is not bytes
        or type(owner) is not owner_v4.H1SharedCapOwnerV4WalHandle
        or type(expected_tail_sequence) is not int
        or expected_tail_sequence < 0
    ):
        _fail("tail attestation operands are mistyped")
    expected_head: Any = (
        _typed_null("JOURNAL_GENESIS")
        if expected_tail_sequence == 0
        else _cid(expected_tail_head_id, "expected Owner tail head")
    )
    if expected_tail_sequence == 0 and expected_tail_head_id != expected_head:
        _fail("expected genesis tail head must be one typed null")
    before_closure_id = closure.closure_id
    trace = dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
        trace_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner.owner,
    )
    replay_before = owner_v4.replay_h1_shared_cap_owner_v4_wal(owner)
    index = owner_v3.inspect_h1_shared_cap_owner_v3_record_index(owner.owner)
    replay_after = owner_v4.replay_h1_shared_cap_owner_v4_wal(owner)
    _require_live_semantic_closure(closure)
    if (
        replay_before != replay_after
        or replay_after["recovery_required"] is not False
        or replay_after["journal_replay_complete"] is not True
        or replay_after["journal_sequence"] != expected_tail_sequence
        or replay_after["journal_head_id"] != expected_head
        or index["journal_sequence"] != expected_tail_sequence
        or index["journal_head_id"] != expected_head
        or index["charged_values"] != replay_after["charged_values"]
        or index["outstanding_values"] != replay_after["outstanding_values"]
        or index["observed_overrun_count"]
        != replay_after["observed_overrun_count"]
        or index["gate_owner_join_status"]
        != replay_after["gate_owner_join_status"]
    ):
        _fail(
            "Owner current tail differs or gate/Owner observation changed "
            "during issuance"
        )
    trace_document = trace.to_document()
    records = _ordered_owner_records(index)
    ordered_ids = _record_ids(records)
    cutoff_sequence = trace_document["owner_journal_sequence_at_snapshot"]
    cutoff_head = trace_document["owner_journal_head_id_at_snapshot"]
    if cutoff_sequence > expected_tail_sequence:
        _fail("dispatch cutoff exceeds the attested current tail")
    tail_extension = ordered_ids[cutoff_sequence:]
    state_payload = {
        "charged_values": index["charged_values"],
        "outstanding_values": index["outstanding_values"],
        "record_ids_by_role": index["record_ids_by_role"],
    }
    consumed_events = trace_document["consumed_events"]
    prefix_last_event_id: Any = (
        consumed_events[-1]["h1_lifecycle_dispatch_event_id"]
        if consumed_events
        else _typed_null("DISPATCH_PREFIX_HAS_NO_EVENTS")
    )
    payload = {
        "schema": "acfqp.k7_h1_tail_bound_prefix_attestation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_prefix_verifier_semantic_closure_id": before_closure_id,
        "predecessor_h1_tail_bound_prefix_attestation_id": predecessor_attestation_id,
        "h1_lifecycle_dispatch_trace_id": trace_document[
            "h1_lifecycle_dispatch_trace_id"
        ],
        "dispatch_trace_byte_count": len(trace_bytes),
        "dispatch_trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "h1_anchored_lifecycle_program_id": bundle.program.anchored_program_id,
        "h1_anchored_lifecycle_handler_registry_id": bundle.registry.registry_id,
        "h1_production_lifecycle_source_manifest_id": bundle.program.source_manifest_id,
        "h1_execution_topology_profile_id": bundle.program.execution_topology_profile_id,
        "h1_production_output_branch_dag_id": bundle.program.output_branch_dag_id,
        "h1_lifecycle_dispatch_profile_id": profile.profile_id,
        "h1_shared_cap_profile_core_v3_id": owner.profile.profile_id,
        "h1_shared_cap_owner_v3_runtime_id": owner.runtime_id,
        "h1_shared_cap_owner_v4_wal_binding_id": owner.binding_id,
        "h1_attempt_rejection_gate_id": Path(owner.gate_directory).name,
        "logical_occurrence_id": profile.logical_occurrence_id,
        "route_attempt_id": profile.route_attempt_id,
        "decision_point_id": profile.decision_point_id,
        "transaction_id": profile.transaction_id,
        "prefix_event_count": trace_document["consumed_event_count"],
        "prefix_last_event_id": prefix_last_event_id,
        "prefix_first_failure_event_id": trace_document[
            "first_failure_event_id"
        ],
        "prefix_next_site_key": trace_document["next_site_key"],
        "prefix_owner_sequence": cutoff_sequence,
        "prefix_owner_head_id": cutoff_head,
        "prefix_owner_record_ids_by_role": trace_document[
            "owner_record_ids_at_snapshot"
        ],
        "prefix_gate_join_status": trace_document[
            "owner_gate_join_status_at_snapshot"
        ],
        "prefix_gate_rejection_commit_id": trace_document[
            "owner_rejection_commit_id_at_snapshot"
        ],
        "prefix_gate_rejection_ack_id": trace_document[
            "owner_rejection_ack_id_at_snapshot"
        ],
        "current_tail_sequence": expected_tail_sequence,
        "current_tail_head_id": expected_head,
        "current_tail_ordered_record_ids": ordered_ids,
        "current_tail_extension_after_prefix_ids": tail_extension,
        "current_tail_extension_count": len(tail_extension),
        "current_tail_state_digest": hashlib.sha256(
            b"acfqp:k7-h1-owner-tail-state:v1\x00"
            + canonical_json_bytes(state_payload)
        ).hexdigest(),
        "current_tail_record_ids_by_role": index["record_ids_by_role"],
        "current_gate_state": replay_after["gate_state"],
        "current_gate_join_status": replay_after["gate_owner_join_status"],
        "current_gate_rejection_commit_id": index["rejection_commit_id"],
        "current_gate_rejection_ack_id": index["rejection_ack_id"],
        "no_pending_cursor_at_issuance": True,
        "no_incomplete_semantic_pair_at_issuance": True,
        "no_gate_recovery_required_at_issuance": True,
        "double_collected_gate_owner_observation_equal": True,
        "verification_scope": "EXACT_TAIL_OBSERVED_DURING_ISSUANCE",
        "atomic_future_consumer_lease_present": False,
        "exact_current_use_authority_present": False,
        "future_append_validity": False,
        "prefix_verification_attestation_issued": True,
        "runtime_object_identity_retained": True,
        "cross_process_source_authority_present": False,
        "no_event_recovery_complete": False,
        "cleanup_execution_authority_present": False,
        "production_execution_authority_present": False,
        "formal_counter_record_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "official_execution_allowed": False,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
        "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
    }
    return H1TailBoundPrefixAttestationV1(
        _ATTESTATION_ISSUER,
        canonical_json_bytes(payload),
    )


def issue_h1_tail_bound_prefix_attestation_v1(
    trace_bytes: bytes,
    *,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    profile: dispatch_v1.H1LifecycleDispatchProfileV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    semantic_closure: H1PrefixVerifierSemanticClosureV1,
    expected_tail_sequence: int,
    expected_tail_head_id: Any,
) -> H1TailBoundPrefixAttestationV1:
    return _issue_tail_attestation(
        trace_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=semantic_closure,
        expected_tail_sequence=expected_tail_sequence,
        expected_tail_head_id=expected_tail_head_id,
        predecessor_attestation_id=_typed_null("FIRST_EXACT_CURRENT_TAIL_ATTESTATION"),
    )


def extend_h1_tail_bound_prefix_attestation_v1(
    predecessor: H1TailBoundPrefixAttestationV1,
    trace_bytes: bytes,
    *,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    profile: dispatch_v1.H1LifecycleDispatchProfileV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    semantic_closure: H1PrefixVerifierSemanticClosureV1,
    expected_tail_sequence: int,
    expected_tail_head_id: Any,
) -> H1TailBoundPrefixAttestationV1:
    """Issue a new observation whose record chain extends one retained predecessor."""

    if type(predecessor) is not H1TailBoundPrefixAttestationV1:
        _fail("tail attestation extension requires one issuer-retained predecessor")
    previous = predecessor.payload
    try:
        trace_document = loads_canonical_json(trace_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1TailBoundPrefixAttestationV1Error(
            "tail attestation extension trace is not canonical"
        ) from error
    if type(trace_document) is not dict:
        _fail("tail attestation extension trace must be one object")
    required_identity = {
        "h1_prefix_verifier_semantic_closure_id": semantic_closure.closure_id,
        "h1_lifecycle_dispatch_trace_id": _cid(
            trace_document.get("h1_lifecycle_dispatch_trace_id"),
            "extension dispatch trace",
        ),
        "h1_anchored_lifecycle_program_id": bundle.program.anchored_program_id,
        "h1_lifecycle_dispatch_profile_id": profile.profile_id,
        "h1_shared_cap_owner_v3_runtime_id": owner.runtime_id,
        "h1_shared_cap_owner_v4_wal_binding_id": owner.binding_id,
    }
    if any(previous.get(key) != value for key, value in required_identity.items()):
        _fail("tail attestation predecessor crossed its semantic context")
    if expected_tail_sequence <= previous["current_tail_sequence"]:
        _fail("tail attestation extension must advance the Owner sequence")
    extended = _issue_tail_attestation(
        trace_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=semantic_closure,
        expected_tail_sequence=expected_tail_sequence,
        expected_tail_head_id=expected_tail_head_id,
        predecessor_attestation_id=predecessor.attestation_id,
    )
    current = extended.payload
    prior_ids = previous["current_tail_ordered_record_ids"]
    if (
        current["current_tail_ordered_record_ids"][: len(prior_ids)]
        != prior_ids
        or current["prefix_owner_sequence"]
        != previous["prefix_owner_sequence"]
        or current["prefix_owner_head_id"]
        != previous["prefix_owner_head_id"]
    ):
        _fail("tail attestation extension is not one append-only continuation")
    return extended


def verify_h1_tail_bound_prefix_attestation_exact_current_bytes_v1(
    raw: bytes,
    trace_bytes: bytes,
    *,
    expected_attestation_id: str,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    profile: dispatch_v1.H1LifecycleDispatchProfileV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    semantic_closure: H1PrefixVerifierSemanticClosureV1,
    expected_tail_sequence: int,
    expected_tail_head_id: Any,
) -> H1TailBoundPrefixAttestationV1:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1TailBoundPrefixAttestationV1Error(
            "tail-bound prefix attestation bytes are not canonical"
        ) from error
    if type(document) is not dict:
        _fail("tail-bound prefix attestation must be one object")
    claimed = _cid(
        document.pop("h1_tail_bound_prefix_attestation_id", None),
        "tail-bound prefix attestation",
    )
    expected_id = _cid(expected_attestation_id, "expected tail attestation")
    reconstructed = issue_h1_tail_bound_prefix_attestation_v1(
        trace_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=semantic_closure,
        expected_tail_sequence=expected_tail_sequence,
        expected_tail_head_id=expected_tail_head_id,
    )
    if (
        claimed != expected_id
        or claimed != reconstructed.attestation_id
        or domains_v1.extension_content_id_v1(TAIL_ATTESTATION_DOMAIN, document)
        != claimed
        or canonical_json_bytes(document) != reconstructed.payload_bytes
    ):
        _fail("tail-bound prefix attestation differs from exact-current replay")
    return reconstructed


def verify_h1_tail_bound_prefix_attestation_extension_observed_current_bytes_v1(
    raw: bytes,
    predecessor: H1TailBoundPrefixAttestationV1,
    trace_bytes: bytes,
    *,
    expected_attestation_id: str,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    profile: dispatch_v1.H1LifecycleDispatchProfileV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    semantic_closure: H1PrefixVerifierSemanticClosureV1,
    expected_tail_sequence: int,
    expected_tail_head_id: Any,
) -> H1TailBoundPrefixAttestationV1:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1TailBoundPrefixAttestationV1Error(
            "tail-bound prefix extension bytes are not canonical"
        ) from error
    if type(document) is not dict:
        _fail("tail-bound prefix extension must be one object")
    claimed = _cid(
        document.pop("h1_tail_bound_prefix_attestation_id", None),
        "tail-bound prefix extension",
    )
    reconstructed = extend_h1_tail_bound_prefix_attestation_v1(
        predecessor,
        trace_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
        semantic_closure=semantic_closure,
        expected_tail_sequence=expected_tail_sequence,
        expected_tail_head_id=expected_tail_head_id,
    )
    if (
        claimed != _cid(expected_attestation_id, "expected tail extension")
        or claimed != reconstructed.attestation_id
        or domains_v1.extension_content_id_v1(TAIL_ATTESTATION_DOMAIN, document)
        != claimed
        or canonical_json_bytes(document) != reconstructed.payload_bytes
    ):
        _fail("tail-bound prefix extension differs from observed-current replay")
    return reconstructed


__all__ = (
    "ConstructionK7H1TailBoundPrefixAttestationV1Error",
    "H1PrefixVerifierSemanticClosureV1",
    "H1TailBoundPrefixAttestationV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "freeze_h1_prefix_verifier_semantic_closure_v1",
    "extend_h1_tail_bound_prefix_attestation_v1",
    "inspect_h1_prefix_verifier_semantic_closure_candidate_v1",
    "issue_h1_tail_bound_prefix_attestation_v1",
    "verify_h1_prefix_verifier_semantic_closure_bytes_v1",
    "verify_h1_tail_bound_prefix_attestation_exact_current_bytes_v1",
    "verify_h1_tail_bound_prefix_attestation_extension_observed_current_bytes_v1",
)
