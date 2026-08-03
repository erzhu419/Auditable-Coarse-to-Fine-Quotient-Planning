"""Sealed-source construction successor for the owned fallback segment.

V3 joins the owner ledger to live repository paths while constructing its
session.  This additive V4 slice removes that construction dependency: its
only source inputs are one canonical sealed member and one canonical V3
operation-boundary-manifest document.  It replays their exact join without a
live archive loader, ``Path(__file__)``, cwd/repository discovery, or any
ground/planner operation.

The currently sealed owner still imports the frozen V3 gateway, bind and
finish functions.  Consequently the verified V4 authority carries an
explicit blocker for production owner execution.  A construction harness
exercises the immutable positive-prefix lifecycle without pretending that its
events came from the production owner.  A future owner engine must import the
V4 gateway before the production runtime entry can be enabled.
"""

from __future__ import annotations

import ast
import builtins
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import InitVar, dataclass, field, fields, is_dataclass
import dis
from enum import Enum
from fractions import Fraction
import hashlib
import sys
import threading
from types import CodeType, MappingProxyType, ModuleType
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.domains import g2048 as canonical_g2048_v4
from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
)
from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_EVENT_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_MANIFEST_AUTHORITY_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_AUTHORITY_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_BOUNDARY_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_SOURCE_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_EVENT_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_EXECUTION_BINDING_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_G2048_TRANSITION_CLOSURE_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_KERNEL_SEMANTICS_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_POLICY_CLASS_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_QUERY_SEMANTICS_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_REWARD_SEMANTICS_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_PROFILE_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_SEMANTICS_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_START_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_STRUCTURAL_SEMANTICS_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_TERMINAL_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_THRESHOLD_SEMANTICS_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_TRANSCRIPT_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNER_BLOCKER_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_SOURCE_AUTHORITY_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_START_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TERMINAL_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TRANSCRIPT_DOMAIN,
    Phase3EIdentityError,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "4.0.0"
PROFILE_KEY = "construction_accounting_route_segment_v4"
PROPOSED_CONTRACT_VERSION = "2.0.53"
REQUIRED_CONTRACT_VERSION = "2.0.52"
CONSTRUCTION_ONLY = True
PRODUCTION_OWNER_SOURCE_INTEGRATED = False
PRODUCTION_CLOSURE_CLAIMED = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"

SOURCE_MODULE = "acfqp.phase3e_fallback_owned_v2"
SOURCE_RELATIVE_PATH = "phase3e_fallback_owned_v2.py"
LEGACY_OWNER_GATEWAY = "emit_owned_route_operation_v3"
REQUIRED_OWNER_GATEWAY = "emit_owned_route_operation_v4"
EXPECTED_SOURCE_BYTE_COUNT = 24965
EXPECTED_SOURCE_SHA256 = (
    "ed1b6f6dbc186552f33363da55f6fbeb1727f84f1b598d15939c63cbba0ce3b4"
)
EXPECTED_BOUNDARY_MANIFEST_ID = (
    "867b465489484b8fafe5acbb39675b9b14eb152729df93116e138e9ed8b23e17"
)
EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256 = (
    "20545882606e09958a7895130bb03d6a9b29f4ee956d79611a3ffbda5e4a8274"
)
EXPECTED_BOUNDARY_COUNT = 7

OWNED_ENGINE_CONTRACT_VERSION = "2.0.54"
OWNED_ENGINE_SOURCE_MODULE = "acfqp.phase3e_fallback_owned_v3"
OWNED_ENGINE_SOURCE_RELATIVE_PATH = "phase3e_fallback_owned_v3.py"
OWNED_ENGINE_SOURCE_BYTE_COUNT = 37568
OWNED_ENGINE_SOURCE_SHA256 = (
    "27a0e116ba7f1e11246590796393030991c8093d743f11d81ccff24180e2a595"
)
OWNED_ENGINE_SEARCH_AST_SHA256 = (
    "47b8d5eadca2ebebdc7095fea1ee6d53147042a1b05bca45dddd195a1b46034f"
)
OWNED_ENGINE_BIND_AST_SHA256 = (
    "f802fe7f09c4ce51e24124add55ea959c0192ca5bad31f5c8d4287692dfb878b"
)
OWNED_ENGINE_BIND_LOCATION = (478, 4, 478, 41)
OWNED_ENGINE_FINISH_AST_SHA256 = (
    "9a9bc464c23c5413d9091598d9da1c85e2e7f29e502a591e09131197abba7fbf"
)
OWNED_ENGINE_FINISH_LOCATION = (690, 4, 690, 54)

_LEGACY_ARCHIVE_DOMAIN = "acfqp:construction-k7-direct-fallback-source-archive:v3"
_LEGACY_BOUNDARY_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-boundary:v3"
)
_LEGACY_MANIFEST_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-manifest:v3"
)
_ISSUER = object()
_OWNED_GATEWAY_ISSUER_V4 = object()
_OWNED_SEARCH_BIND_ISSUER_V4 = object()
_OWNED_SEARCH_FINISH_ISSUER_V4 = object()
_OWNED_NODE_MINT_ISSUER_V4 = object()
_FROZEN_GETFRAME_V4 = sys._getframe  # noqa: SLF001
_OWNED_ENGINE_IMPORT_SEAL_LOCK_V4 = threading.RLock()


class ConstructionAccountingRouteSegmentV4Error(ValueError):
    """The sealed source, authority, operation prefix, or lifecycle is invalid."""


class OwnerRuntimeIntegrationBlockedV4(ConstructionAccountingRouteSegmentV4Error):
    """The sealed owner does not import the V4 runtime gateway."""

    def __init__(self, blocker: "OwnerRuntimeIntegrationBlockerV4") -> None:
        super().__init__(blocker.code)
        self.blocker = blocker


class RouteSegmentTerminalKindV4(str, Enum):
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class RouteOperationOriginV4(str, Enum):
    CONSTRUCTION_VERIFIED_SOURCE_REPLAY = "CONSTRUCTION_VERIFIED_SOURCE_REPLAY"
    SOURCE_OWNED_RUNTIME = "SOURCE_OWNED_RUNTIME"


class _SessionModeV4(str, Enum):
    CONSTRUCTION = "CONSTRUCTION"
    OWNED_RUNTIME = "OWNED_RUNTIME"


def _fail(message: str) -> NoReturn:
    raise ConstructionAccountingRouteSegmentV4Error(message)


def _same_frozen_runtime_value_v4(left: Any, right: Any) -> bool:
    if left is right:
        return True
    if type(left) in {type(None), bool, int, str, bytes, float, complex}:
        return type(left) is type(right) and left == right
    return False


@dataclass(frozen=True, slots=True)
class _CallableImportStateV4:
    target: Any
    code: Any
    globals_object: Any
    defaults_object: Any
    default_values: tuple[Any, ...]
    kwdefaults_object: Any
    kwdefault_values: tuple[tuple[str, Any], ...]
    closure_object: Any
    closure_values: tuple[Any, ...]


def _freeze_callable_import_state_v4(target: Any) -> _CallableImportStateV4:
    defaults = getattr(target, "__defaults__", None)
    kwdefaults = getattr(target, "__kwdefaults__", None)
    closure = getattr(target, "__closure__", None)
    return _CallableImportStateV4(
        target,
        getattr(target, "__code__", None),
        getattr(target, "__globals__", None),
        defaults,
        () if defaults is None else tuple(defaults),
        kwdefaults,
        () if kwdefaults is None else tuple(sorted(kwdefaults.items())),
        closure,
        () if closure is None else tuple(cell.cell_contents for cell in closure),
    )


def _callable_import_state_matches_v4(state: _CallableImportStateV4) -> bool:
    target = state.target
    defaults = getattr(target, "__defaults__", None)
    kwdefaults = getattr(target, "__kwdefaults__", None)
    closure = getattr(target, "__closure__", None)
    if (
        getattr(target, "__code__", None) is not state.code
        or getattr(target, "__globals__", None) is not state.globals_object
        or defaults is not state.defaults_object
        or kwdefaults is not state.kwdefaults_object
        or closure is not state.closure_object
        or (() if defaults is None else tuple(defaults)) != state.default_values
        or (() if kwdefaults is None else tuple(sorted(kwdefaults.items())))
        != state.kwdefault_values
        or (() if closure is None else tuple(cell.cell_contents for cell in closure))
        != state.closure_values
    ):
        return False
    return all(
        _same_frozen_runtime_value_v4(current, frozen)
        for current, frozen in zip(
            () if defaults is None else tuple(defaults),
            state.default_values,
        )
    ) and all(
        current_name == frozen_name
        and _same_frozen_runtime_value_v4(current, frozen)
        for (current_name, current), (frozen_name, frozen) in zip(
            () if kwdefaults is None else tuple(sorted(kwdefaults.items())),
            state.kwdefault_values,
        )
    ) and all(
        _same_frozen_runtime_value_v4(current, frozen)
        for current, frozen in zip(
            () if closure is None else tuple(cell.cell_contents for cell in closure),
            state.closure_values,
        )
    )


@dataclass(frozen=True, slots=True)
class _OwnedEngineImportSealV4:
    validator_state: _CallableImportStateV4
    owner_globals: Mapping[str, Any]
    expected_defaults: tuple[Any, ...]
    runtime_global_bindings: tuple[tuple[str, Any, Any], ...]
    runtime_builtin_bindings: tuple[tuple[str, Any, Any], ...]
    runtime_class_surfaces: tuple[tuple[Any, tuple[Any, ...]], ...]
    global_callable_states: tuple[tuple[str, _CallableImportStateV4], ...]
    builtin_callable_states: tuple[tuple[str, _CallableImportStateV4], ...]
    class_callable_states: tuple[
        tuple[Any, str, Any, tuple[_CallableImportStateV4, ...]], ...
    ]
    frozen_named_bindings: tuple[tuple[str, Any], ...]


_OWNED_ENGINE_IMPORT_SEAL_V4: _OwnedEngineImportSealV4 | None = None


def _descriptor_callables_v4(descriptor: Any) -> tuple[Any, ...]:
    if isinstance(descriptor, (classmethod, staticmethod)):
        return (descriptor.__func__,)
    if isinstance(descriptor, property):
        return tuple(
            function
            for function in (descriptor.fget, descriptor.fset, descriptor.fdel)
            if function is not None
        )
    return (descriptor,) if getattr(descriptor, "__code__", None) is not None else ()


def seal_owned_fallback_engine_import_v4(
    validator: Any,
    owner_globals: Mapping[str, Any],
    expected_defaults: tuple[Any, ...],
    runtime_global_bindings: tuple[tuple[str, Any, Any], ...],
    runtime_builtin_bindings: tuple[tuple[str, Any, Any], ...],
    runtime_class_surfaces: tuple[tuple[Any, tuple[Any, ...]], ...],
) -> None:
    """One-shot external import seal for the owned engine's live validator."""

    global _OWNED_ENGINE_IMPORT_SEAL_V4
    try:
        caller = _FROZEN_GETFRAME_V4(1)
    except (AttributeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "owned-engine import seal caller is unavailable"
        ) from error
    with _OWNED_ENGINE_IMPORT_SEAL_LOCK_V4:
        if _OWNED_ENGINE_IMPORT_SEAL_V4 is not None:
            _fail("owned-engine import seal is exact-once")
        defaults = getattr(validator, "__defaults__", None)
        if (
            caller.f_globals is not owner_globals
            or caller.f_locals is not owner_globals
            or caller.f_code.co_name != "<module>"
            or owner_globals.get("__name__") != OWNED_ENGINE_SOURCE_MODULE
            or owner_globals.get("require_frozen_owned_fallback_engine_binding_v3")
            is not validator
            or getattr(validator, "__globals__", None) is not owner_globals
            or type(defaults) is not tuple
            or len(defaults) != len(expected_defaults)
            or len(defaults) != 14
            or any(
                not _same_frozen_runtime_value_v4(current, expected)
                for current, expected in zip(defaults, expected_defaults)
            )
            or getattr(validator, "__kwdefaults__", None) is not None
            or type(runtime_global_bindings) is not tuple
            or type(runtime_builtin_bindings) is not tuple
            or type(runtime_class_surfaces) is not tuple
        ):
            _fail("owned-engine import seal input is invalid")
        global_states = tuple(
            (name, _freeze_callable_import_state_v4(target))
            for name, target, _code in runtime_global_bindings
            if getattr(target, "__code__", None) is not None
        )
        builtin_states = tuple(
            (name, _freeze_callable_import_state_v4(target))
            for name, target, _code in runtime_builtin_bindings
            if getattr(target, "__code__", None) is not None
        )
        class_states = tuple(
            (
                owner,
                name,
                descriptor,
                tuple(
                    _freeze_callable_import_state_v4(target)
                    for target in _descriptor_callables_v4(descriptor)
                ),
            )
            for owner, surfaces in runtime_class_surfaces
            for name, descriptor, _descriptor_code in surfaces
        )
        frozen_names = (
            "_FROZEN_SEARCH_ENTRY_OBJECT_V3",
            "_FROZEN_SEARCH_ENTRY_GLOBALS_V3",
            "_FROZEN_SEARCH_ENTRY_CODE_V3",
            "_FROZEN_WORK_VECTOR_HELPER_OBJECT_V3",
            "_FROZEN_WORK_VECTOR_HELPER_GLOBALS_V3",
            "_FROZEN_WORK_VECTOR_HELPER_CODE_V3",
            "_FROZEN_OWNER_BINDING_VALIDATOR_OBJECT_V3",
            "_FROZEN_OWNER_BINDING_VALIDATOR_GLOBALS_V3",
            "_FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3",
            "_FROZEN_RUNTIME_GLOBAL_BINDINGS_V3",
            "_FROZEN_RUNTIME_BUILTIN_BINDINGS_V3",
            "_FROZEN_RUNTIME_CLASS_SURFACES_V3",
            "_FROZEN_LIVE_CODE_FINGERPRINTS_V3",
            "_normalized_recursive_code_fingerprint_v3",
            "verify_owned_fallback_engine_import_seal_v4",
        )
        named = tuple((name, owner_globals.get(name)) for name in frozen_names)
        if any(value is None for _name, value in named):
            _fail("owned-engine import seal lacks a frozen named binding")
        _OWNED_ENGINE_IMPORT_SEAL_V4 = _OwnedEngineImportSealV4(
            _freeze_callable_import_state_v4(validator),
            owner_globals,
            defaults,
            runtime_global_bindings,
            runtime_builtin_bindings,
            runtime_class_surfaces,
            global_states,
            builtin_states,
            class_states,
            named,
        )


def verify_owned_fallback_engine_import_seal_v4(
    validator: Any,
    owner_globals: Mapping[str, Any],
) -> None:
    """Reject synchronized validator/default/dependency replacement."""

    with _OWNED_ENGINE_IMPORT_SEAL_LOCK_V4:
        seal = _OWNED_ENGINE_IMPORT_SEAL_V4
        if (
            seal is None
            or validator is not seal.validator_state.target
            or owner_globals is not seal.owner_globals
            or owner_globals.get("require_frozen_owned_fallback_engine_binding_v3")
            is not validator
            or not _callable_import_state_matches_v4(seal.validator_state)
            or getattr(validator, "__defaults__", None) is not seal.expected_defaults
            or owner_globals.get("_FROZEN_RUNTIME_GLOBAL_BINDINGS_V3")
            is not seal.runtime_global_bindings
            or owner_globals.get("_FROZEN_RUNTIME_BUILTIN_BINDINGS_V3")
            is not seal.runtime_builtin_bindings
            or owner_globals.get("_FROZEN_RUNTIME_CLASS_SURFACES_V3")
            is not seal.runtime_class_surfaces
            or any(owner_globals.get(name) is not value for name, value in seal.frozen_named_bindings)
        ):
            _fail("owned fallback engine import seal changed")
        for name, target, code in seal.runtime_global_bindings:
            current = owner_globals.get(name)
            if current is not target or getattr(current, "__code__", None) is not code:
                _fail(f"owned fallback runtime dependency {name!r} changed")
        for name, target, code in seal.runtime_builtin_bindings:
            current = getattr(builtins, name, None)
            if current is not target or getattr(current, "__code__", None) is not code:
                _fail(f"owned fallback builtin dependency {name!r} changed")
        if any(
            not _callable_import_state_matches_v4(state)
            for _name, state in (*seal.global_callable_states, *seal.builtin_callable_states)
        ):
            _fail("owned fallback mathematical callable state changed")
        for owner, name, descriptor, callable_states in seal.class_callable_states:
            if vars(owner).get(name) is not descriptor or any(
                not _callable_import_state_matches_v4(state)
                for state in callable_states
            ):
                _fail("owned fallback runtime class surface changed")


_FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_V4 = (
    verify_owned_fallback_engine_import_seal_v4
)
_FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_GLOBALS_V4 = (
    verify_owned_fallback_engine_import_seal_v4.__globals__
)
_FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_CODE_V4 = (
    verify_owned_fallback_engine_import_seal_v4.__code__
)
_FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_DEFAULTS_V4 = (
    verify_owned_fallback_engine_import_seal_v4.__defaults__
)
_FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_KWDEFAULTS_V4 = (
    verify_owned_fallback_engine_import_seal_v4.__kwdefaults__
)


def _require_frozen_owned_engine_import_seal_verifier_v4() -> Any:
    verifier = _FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_V4
    if (
        globals().get("verify_owned_fallback_engine_import_seal_v4") is not verifier
        or verifier.__globals__
        is not _FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_GLOBALS_V4
        or verifier.__code__ is not _FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_CODE_V4
        or verifier.__defaults__
        is not _FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_DEFAULTS_V4
        or verifier.__kwdefaults__
        is not _FROZEN_OWNED_ENGINE_IMPORT_SEAL_VERIFIER_KWDEFAULTS_V4
        or verifier.__defaults__ is not None
        or verifier.__kwdefaults__ is not None
    ):
        _fail("owned-engine import-seal verifier changed")
    return verifier


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _normalized_code_component_v4(value: Any) -> Any:
    if isinstance(value, CodeType):
        return _normalized_code_structure_v4(value)
    if value is None or type(value) in {bool, int, str, float, complex}:
        return (type(value).__name__, repr(value))
    if type(value) is bytes:
        return ("bytes", value.hex())
    if type(value) is tuple:
        return ("tuple", tuple(_normalized_code_component_v4(row) for row in value))
    if type(value) is frozenset:
        return (
            "frozenset",
            tuple(sorted(repr(_normalized_code_component_v4(row)) for row in value)),
        )
    return (type(value).__module__, type(value).__qualname__, repr(value))


def _normalized_code_structure_v4(code: CodeType) -> tuple[Any, ...]:
    return (
        "code-v1",
        code.co_name,
        code.co_argcount,
        getattr(code, "co_posonlyargcount", 0),
        code.co_kwonlyargcount,
        code.co_nlocals,
        code.co_stacksize,
        code.co_flags,
        code.co_code.hex(),
        tuple(_normalized_code_component_v4(row) for row in code.co_consts),
        tuple(code.co_names),
        tuple(code.co_varnames),
        tuple(code.co_freevars),
        tuple(code.co_cellvars),
        getattr(code, "co_exceptiontable", b"").hex(),
    )


def _normalized_recursive_code_fingerprint_v4(code: CodeType) -> str:
    return _sha256(repr(_normalized_code_structure_v4(code)).encode("utf-8"))


_CANONICAL_G2048_ROOT_SURFACES_V4 = (
    "__init__",
    "__post_init__",
    "size",
    "reward_upper_bound",
    "initial_distribution",
    "actions",
    "step",
    "is_terminal",
    "_adjacent",
    "_validate_state",
    "rank_cap",
    "horizon",
    "registered_reward_features",
    "registered_goals",
    "spawn_distribution",
    "cell_count",
)
_CANONICAL_G2048_SUPPORT_SURFACES_V4 = (
    "__new__",
    "__init__",
    "__post_init__",
    "__eq__",
    "__hash__",
)
_CANONICAL_G2048_EXPLICIT_CLASS_SURFACES_V4 = MappingProxyType(
    {
        canonical_g2048_v4.G2048State: ("board", "status"),
        canonical_g2048_v4.G2048Action: (
            "first",
            "second",
            "survivor",
        ),
        canonical_g2048_v4.G2048Status: ("ACTIVE", "FAILURE"),
        canonical_g2048_v4.Outcome: (
            "probability",
            "next_state",
            "reward_features",
            "failure",
            "terminal",
        ),
        Fraction: (
            "__add__",
            "__radd__",
            "__mul__",
            "__rmul__",
            "__truediv__",
            "__rtruediv__",
            "__eq__",
            "__lt__",
            "__le__",
            "__hash__",
            "numerator",
            "denominator",
        ),
    }
)
_CANONICAL_G2048_REGISTERED_CLASSES_V4 = (
    canonical_g2048_v4.G2048Kernel,
    *tuple(_CANONICAL_G2048_EXPLICIT_CLASS_SURFACES_V4),
)


def _walk_code_objects_v4(code: CodeType) -> tuple[CodeType, ...]:
    found = [code]
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            found.extend(_walk_code_objects_v4(constant))
    return tuple(found)


def _global_names_in_code_v4(code: CodeType) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                instruction.argval
                for instruction in dis.get_instructions(code)
                if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}
                and type(instruction.argval) is str
            }
        )
    )


def _module_attributes_in_code_v4(
    code: CodeType,
    owner_globals: Mapping[str, Any],
) -> tuple[tuple[ModuleType, str, Any], ...]:
    """Return direct ``module.attribute`` loads used by one code object."""

    instructions = tuple(dis.get_instructions(code))
    found: dict[tuple[int, str], tuple[ModuleType, str, Any]] = {}
    for index, instruction in enumerate(instructions[:-1]):
        if (
            instruction.opname not in {"LOAD_GLOBAL", "LOAD_NAME"}
            or type(instruction.argval) is not str
        ):
            continue
        module = owner_globals.get(instruction.argval)
        following = instructions[index + 1]
        if (
            not isinstance(module, ModuleType)
            or following.opname not in {"LOAD_ATTR", "LOAD_METHOD"}
            or type(following.argval) is not str
            or not hasattr(module, following.argval)
        ):
            continue
        attribute = getattr(module, following.argval)
        found[(id(module), following.argval)] = (
            module,
            following.argval,
            attribute,
        )
    return tuple(found.values())


def _nested_callable_and_class_dependencies_v4(value: Any) -> tuple[Any, ...]:
    """Find executable objects retained in defaults/kwdefaults/closures."""

    found: list[Any] = []
    pending = [value]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, type) or getattr(current, "__code__", None) is not None:
            found.append(current)
        elif type(current) in (tuple, list, set, frozenset):
            pending.extend(current)
        elif type(current) is dict:
            pending.extend(current.keys())
            pending.extend(current.values())
    return tuple(found)


def _static_resolution_surface_v4(
    owner: type,
    name: str,
) -> tuple[type, Any] | None:
    for base in owner.__mro__:
        if name in vars(base):
            return base, vars(base)[name]
    return None


def _same_static_resolution_surface_v4(
    current: tuple[type, Any] | None,
    frozen: tuple[type, Any] | None,
) -> bool:
    return current is frozen or (
        current is not None
        and frozen is not None
        and current[0] is frozen[0]
        and current[1] is frozen[1]
    )


@dataclass(frozen=True, slots=True)
class _ExactClassDictionaryStateV4:
    owner: type
    metaclass: type
    mro_types: tuple[type, ...]
    base_types: tuple[type, ...]
    entries: tuple[tuple[str, Any], ...]
    instance_getattribute: tuple[type, Any] | None
    instance_getattr: tuple[type, Any] | None
    metaclass_getattribute: tuple[type, Any] | None
    metaclass_getattr: tuple[type, Any] | None
    metaclass_call: tuple[type, Any] | None


def _freeze_exact_class_dictionary_v4(owner: type) -> _ExactClassDictionaryStateV4:
    metaclass = type(owner)
    return _ExactClassDictionaryStateV4(
        owner,
        metaclass,
        tuple(owner.__mro__),
        tuple(owner.__bases__),
        tuple(vars(owner).items()),
        _static_resolution_surface_v4(owner, "__getattribute__"),
        _static_resolution_surface_v4(owner, "__getattr__"),
        _static_resolution_surface_v4(metaclass, "__getattribute__"),
        _static_resolution_surface_v4(metaclass, "__getattr__"),
        _static_resolution_surface_v4(metaclass, "__call__"),
    )


def _exact_class_dictionary_matches_v4(
    state: _ExactClassDictionaryStateV4,
) -> bool:
    owner = state.owner
    current_entries = tuple(vars(owner).items())
    return (
        type(owner) is state.metaclass
        and tuple(owner.__mro__) == state.mro_types
        and all(
            left is right for left, right in zip(owner.__mro__, state.mro_types)
        )
        and tuple(owner.__bases__) == state.base_types
        and all(
            left is right for left, right in zip(owner.__bases__, state.base_types)
        )
        and len(current_entries) == len(state.entries)
        and all(
            current_name == frozen_name and current_value is frozen_value
            for (current_name, current_value), (frozen_name, frozen_value) in zip(
                current_entries,
                state.entries,
            )
        )
        and _same_static_resolution_surface_v4(
            _static_resolution_surface_v4(owner, "__getattribute__"),
            state.instance_getattribute,
        )
        and _same_static_resolution_surface_v4(
            _static_resolution_surface_v4(owner, "__getattr__"),
            state.instance_getattr,
        )
        and _same_static_resolution_surface_v4(
            _static_resolution_surface_v4(state.metaclass, "__getattribute__"),
            state.metaclass_getattribute,
        )
        and _same_static_resolution_surface_v4(
            _static_resolution_surface_v4(state.metaclass, "__getattr__"),
            state.metaclass_getattr,
        )
        and _same_static_resolution_surface_v4(
            _static_resolution_surface_v4(state.metaclass, "__call__"),
            state.metaclass_call,
        )
    )


@dataclass(frozen=True, slots=True)
class _ExactModuleResolutionStateV4:
    module: ModuleType
    module_type: type
    module_globals: Mapping[str, Any]
    module_getattribute: tuple[type, Any] | None
    module_getattr: tuple[type, Any] | None
    direct_specials: tuple[tuple[str, bool, Any], ...]


def _freeze_exact_module_resolution_v4(
    module: ModuleType,
) -> _ExactModuleResolutionStateV4:
    module_globals = module.__dict__
    specials = tuple(
        (name, name in module_globals, module_globals.get(name))
        for name in ("__getattribute__", "__getattr__")
    )
    return _ExactModuleResolutionStateV4(
        module,
        type(module),
        module_globals,
        _static_resolution_surface_v4(type(module), "__getattribute__"),
        _static_resolution_surface_v4(type(module), "__getattr__"),
        specials,
    )


def _exact_module_resolution_matches_v4(
    state: _ExactModuleResolutionStateV4,
) -> bool:
    module = state.module
    module_globals = module.__dict__
    return (
        type(module) is state.module_type
        and module_globals is state.module_globals
        and _same_static_resolution_surface_v4(
            _static_resolution_surface_v4(type(module), "__getattribute__"),
            state.module_getattribute,
        )
        and _same_static_resolution_surface_v4(
            _static_resolution_surface_v4(type(module), "__getattr__"),
            state.module_getattr,
        )
        and all(
            (name in module_globals) is present
            and (not present or module_globals.get(name) is target)
            for name, present, target in state.direct_specials
        )
    )


@dataclass(frozen=True, slots=True)
class _CanonicalG2048TransitionSealV4:
    module_object: Any
    module_globals: Mapping[str, Any]
    kernel_class: type
    root_surfaces: tuple[tuple[str, Any, tuple[_CallableImportStateV4, ...]], ...]
    module_bindings: tuple[
        tuple[str, Mapping[str, Any], str, Any, _CallableImportStateV4 | None], ...
    ]
    module_attribute_bindings: tuple[
        tuple[ModuleType, str, Any, _CallableImportStateV4 | None], ...
    ]
    builtin_bindings: tuple[
        tuple[str, Any, _CallableImportStateV4 | None], ...
    ]
    class_surfaces: tuple[
        tuple[type, str, Any, tuple[_CallableImportStateV4, ...]], ...
    ]
    exact_class_dictionaries: tuple[_ExactClassDictionaryStateV4, ...]
    exact_module_resolutions: tuple[_ExactModuleResolutionStateV4, ...]
    document_bytes: bytes
    closure_id: str


def _build_canonical_g2048_transition_seal_v4() -> _CanonicalG2048TransitionSealV4:
    module = canonical_g2048_v4
    module_globals = module.__dict__
    kernel_class = module.G2048Kernel
    roots: list[tuple[str, Any, tuple[_CallableImportStateV4, ...]]] = []
    pending_states: list[_CallableImportStateV4] = []
    for name in _CANONICAL_G2048_ROOT_SURFACES_V4:
        descriptor = vars(kernel_class).get(name)
        if descriptor is None:
            _fail(f"canonical G2048 manifest lacks root surface {name!r}")
        states = tuple(
            _freeze_callable_import_state_v4(target)
            for target in _descriptor_callables_v4(descriptor)
        )
        if not states and not hasattr(descriptor, "__get__"):
            _fail(
                f"canonical G2048 root surface {name!r} is neither callable "
                "nor a descriptor"
            )
        roots.append((name, descriptor, states))
        pending_states.extend(states)

    dependency_records: dict[
        tuple[int, str],
        tuple[str, Mapping[str, Any], str, Any, _CallableImportStateV4 | None],
    ] = {}
    module_attribute_records: dict[
        tuple[int, str],
        tuple[ModuleType, str, Any, _CallableImportStateV4 | None],
    ] = {}
    builtin_names: set[str] = set()
    support_classes: set[type] = set()
    class_records: dict[
        tuple[int, str],
        tuple[type, str, Any, tuple[_CallableImportStateV4, ...]],
    ] = {}
    pending_classes: list[type] = []
    visited_callable_targets: set[int] = set()
    visited_classes: set[int] = set()
    while pending_states or pending_classes:
        while pending_states:
            state = pending_states.pop()
            if id(state.target) in visited_callable_targets:
                continue
            visited_callable_targets.add(id(state.target))
            if not isinstance(state.code, CodeType) or not isinstance(
                state.globals_object, Mapping
            ):
                continue
            dependency_globals = state.globals_object
            dependency_module = str(dependency_globals.get("__name__", "<unknown>"))
            retained_values = (
                *state.default_values,
                *(value for _name, value in state.kwdefault_values),
                *state.closure_values,
            )
            for retained in retained_values:
                for dependency in _nested_callable_and_class_dependencies_v4(
                    retained
                ):
                    if isinstance(dependency, type):
                        support_classes.add(dependency)
                        pending_classes.append(dependency)
                    elif getattr(dependency, "__code__", None) is not None:
                        pending_states.append(
                            _freeze_callable_import_state_v4(dependency)
                        )
            for nested in _walk_code_objects_v4(state.code):
                for (
                    dependency_module_object,
                    attribute_name,
                    target,
                ) in _module_attributes_in_code_v4(
                    nested,
                    dependency_globals,
                ):
                    callable_state = (
                        _freeze_callable_import_state_v4(target)
                        if getattr(target, "__code__", None) is not None
                        else None
                    )
                    module_attribute_records[
                        (id(dependency_module_object), attribute_name)
                    ] = (
                        dependency_module_object,
                        attribute_name,
                        target,
                        callable_state,
                    )
                    if callable_state is not None:
                        pending_states.append(callable_state)
                    if isinstance(target, type):
                        support_classes.add(target)
                        pending_classes.append(target)
                for name in _global_names_in_code_v4(nested):
                    if name in dependency_globals:
                        target = dependency_globals[name]
                        callable_state = (
                            _freeze_callable_import_state_v4(target)
                            if getattr(target, "__code__", None) is not None
                            else None
                        )
                        dependency_records[(id(dependency_globals), name)] = (
                            dependency_module,
                            dependency_globals,
                            name,
                            target,
                            callable_state,
                        )
                        if callable_state is not None:
                            pending_states.append(callable_state)
                        if isinstance(target, type):
                            support_classes.add(target)
                            pending_classes.append(target)
                    elif hasattr(builtins, name):
                        builtin_names.add(name)
        while pending_classes:
            owner = pending_classes.pop()
            if id(owner) in visited_classes:
                continue
            visited_classes.add(id(owner))
            surface_names = tuple(
                dict.fromkeys(
                    (
                        *_CANONICAL_G2048_SUPPORT_SURFACES_V4,
                        *_CANONICAL_G2048_EXPLICIT_CLASS_SURFACES_V4.get(
                            owner, ()
                        ),
                    )
                )
            )
            for name in surface_names:
                descriptor = vars(owner).get(name)
                if descriptor is None:
                    continue
                states = tuple(
                    _freeze_callable_import_state_v4(target)
                    for target in _descriptor_callables_v4(descriptor)
                )
                class_records[(id(owner), name)] = (
                    owner,
                    name,
                    descriptor,
                    states,
                )
                pending_states.extend(states)

    module_bindings = tuple(
        sorted(
            dependency_records.values(),
            key=lambda row: (
                row[0],
                row[2],
                type(row[3]).__module__,
                type(row[3]).__qualname__,
            ),
        )
    )
    builtin_bindings = tuple(
        (
            name,
            getattr(builtins, name),
            (
                _freeze_callable_import_state_v4(getattr(builtins, name))
                if getattr(getattr(builtins, name), "__code__", None) is not None
                else None
            ),
        )
        for name in sorted(builtin_names)
    )
    module_attribute_bindings = tuple(
        sorted(
            module_attribute_records.values(),
            key=lambda row: (row[0].__name__, row[1]),
        )
    )
    class_surfaces = tuple(
        sorted(
            class_records.values(),
            key=lambda row: (row[0].__module__, row[0].__qualname__, row[1]),
        )
    )
    exact_class_dictionaries = tuple(
        _freeze_exact_class_dictionary_v4(owner)
        for owner in _CANONICAL_G2048_REGISTERED_CLASSES_V4
    )
    resolution_modules: dict[int, ModuleType] = {id(module): module}
    for dependency_module, _name, _target, _state in module_attribute_bindings:
        resolution_modules[id(dependency_module)] = dependency_module
    for owner_module, owner_globals, _name, _target, _state in module_bindings:
        candidate_module = sys.modules.get(owner_module)
        if (
            isinstance(candidate_module, ModuleType)
            and candidate_module.__dict__ is owner_globals
        ):
            resolution_modules[id(candidate_module)] = candidate_module
    exact_module_resolutions = tuple(
        _freeze_exact_module_resolution_v4(dependency_module)
        for dependency_module in sorted(
            resolution_modules.values(), key=lambda row: row.__name__
        )
    )
    document = {
        "schema": "acfqp.canonical_g2048_transition_semantic_closure.v4",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "kernel_type": f"{kernel_class.__module__}.{kernel_class.__qualname__}",
        "kernel_size": 2,
        "root_surfaces": [
            {
                "name": name,
                "callable_code_sha256": [
                    (
                        None
                        if state.code is None
                        else _normalized_recursive_code_fingerprint_v4(state.code)
                    )
                    for state in states
                ],
            }
            for name, _descriptor, states in roots
        ],
        "recursive_module_bindings": [
            {
                "owner_module": owner_module,
                "name": name,
                "target_type": f"{type(target).__module__}.{type(target).__qualname__}",
                "target_qualname": getattr(target, "__qualname__", None),
                "code_sha256": (
                    None
                    if state is None or state.code is None
                    else _normalized_recursive_code_fingerprint_v4(state.code)
                ),
            }
            for owner_module, _owner_globals, name, target, state in module_bindings
        ],
        "recursive_builtin_bindings": [name for name, _target, _state in builtin_bindings],
        "recursive_module_attribute_bindings": [
            {
                "module": module.__name__,
                "name": name,
                "target_type": f"{type(target).__module__}.{type(target).__qualname__}",
                "target_qualname": getattr(target, "__qualname__", None),
                "code_sha256": (
                    None
                    if state is None or state.code is None
                    else _normalized_recursive_code_fingerprint_v4(state.code)
                ),
            }
            for module, name, target, state in module_attribute_bindings
        ],
        "support_class_surfaces": [
            {
                "owner": f"{owner.__module__}.{owner.__qualname__}",
                "name": name,
                "callable_code_sha256": [
                    (
                        None
                        if state.code is None
                        else _normalized_recursive_code_fingerprint_v4(state.code)
                    )
                    for state in states
                ],
            }
            for owner, name, _descriptor, states in class_surfaces
        ],
        "exact_registered_class_dictionaries": [
            {
                "owner": f"{state.owner.__module__}.{state.owner.__qualname__}",
                "class_dict_keys": [name for name, _target in state.entries],
                "getattribute_owner": (
                    None
                    if state.instance_getattribute is None
                    else (
                        f"{state.instance_getattribute[0].__module__}."
                        f"{state.instance_getattribute[0].__qualname__}"
                    )
                ),
                "getattr_absent": state.instance_getattr is None,
                "slots_present": "__slots__" in dict(state.entries),
            }
            for state in exact_class_dictionaries
        ],
        "exact_module_attribute_resolution": [
            {
                "module": state.module.__name__,
                "module_type": (
                    f"{state.module_type.__module__}."
                    f"{state.module_type.__qualname__}"
                ),
                "direct_getattribute_present": state.direct_specials[0][1],
                "direct_getattr_present": state.direct_specials[1][1],
            }
            for state in exact_module_resolutions
        ],
        "object_identity_revalidated_live": True,
        "source_hash_only": False,
        "construction_only": True,
    }
    document_bytes = canonical_json_bytes(document)
    return _CanonicalG2048TransitionSealV4(
        module,
        module_globals,
        kernel_class,
        tuple(roots),
        module_bindings,
        module_attribute_bindings,
        builtin_bindings,
        class_surfaces,
        exact_class_dictionaries,
        exact_module_resolutions,
        document_bytes,
        content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_G2048_TRANSITION_CLOSURE_DOMAIN,
            document,
        ),
    )


_CANONICAL_G2048_TRANSITION_SEAL_V4 = _build_canonical_g2048_transition_seal_v4()


def _verify_canonical_g2048_transition_closure_v4() -> str:
    seal = _CANONICAL_G2048_TRANSITION_SEAL_V4
    if (
        canonical_g2048_v4 is not seal.module_object
        or canonical_g2048_v4.__dict__ is not seal.module_globals
        or canonical_g2048_v4.G2048Kernel is not seal.kernel_class
    ):
        _fail("canonical G2048 transition closure root changed")
    for name, descriptor, states in seal.root_surfaces:
        if vars(seal.kernel_class).get(name) is not descriptor or any(
            not _callable_import_state_matches_v4(state) for state in states
        ):
            _fail(f"canonical G2048 transition root {name!r} changed")
    for owner_module, owner_globals, name, target, state in seal.module_bindings:
        if owner_globals.get("__name__") != owner_module or owner_globals.get(name) is not target or (
            state is not None and not _callable_import_state_matches_v4(state)
        ):
            _fail(
                "canonical G2048 recursive dependency "
                f"{owner_module}.{name} changed"
            )
    for name, target, state in seal.builtin_bindings:
        if getattr(builtins, name, None) is not target or (
            state is not None and not _callable_import_state_matches_v4(state)
        ):
            _fail(f"canonical G2048 builtin dependency {name!r} changed")
    for module, name, target, state in seal.module_attribute_bindings:
        if getattr(module, name, None) is not target or (
            state is not None and not _callable_import_state_matches_v4(state)
        ):
            _fail(
                "canonical G2048 module attribute dependency "
                f"{module.__name__}.{name} changed"
            )
    for owner, name, descriptor, states in seal.class_surfaces:
        if vars(owner).get(name) is not descriptor or any(
            not _callable_import_state_matches_v4(state) for state in states
        ):
            _fail(
                "canonical G2048 support class surface "
                f"{owner.__qualname__}.{name} changed"
            )
    for state in seal.exact_class_dictionaries:
        if not _exact_class_dictionary_matches_v4(state):
            _fail(
                "canonical G2048 exact class dictionary changed: "
                f"{state.owner.__module__}.{state.owner.__qualname__}"
            )
    for state in seal.exact_module_resolutions:
        if not _exact_module_resolution_matches_v4(state):
            _fail(
                "canonical G2048 module attribute resolution changed: "
                f"{state.module.__name__}"
            )
    if canonical_json_bytes(loads_canonical_json(seal.document_bytes)) != seal.document_bytes:
        _fail("canonical G2048 transition closure document changed")
    return seal.closure_id


def _require_canonical_g2048_transition_closure_v4(kernel: Any) -> str:
    closure_id = _verify_canonical_g2048_transition_closure_v4()
    seal = _CANONICAL_G2048_TRANSITION_SEAL_V4
    if type(kernel) is not seal.kernel_class or kernel.size != 2:
        _fail("owned engine requires the registered canonical G2048Kernel(2)")
    return closure_id


def _legacy_content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            f"{label} must be one full content ID"
        ) from error


def _require_route_node_issuance(issuer: object, key: str, node: Any) -> None:
    """Bind readable-token construction to one exact session method."""

    if issuer is not _ISSUER:
        _fail("V4 route-segment node is session-issued only")
    try:
        generated_init = _FROZEN_GETFRAME_V4(2)
        session_caller = _FROZEN_GETFRAME_V4(3)
        expected_code = _FROZEN_ROUTE_NODE_CODES_V4[key]
    except (AttributeError, KeyError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "V4 route-segment issuance ancestry is unavailable"
        ) from error
    if (
        generated_init.f_code is not type(node).__init__.__code__
        or session_caller.f_globals is not _FROZEN_ROUTE_NODE_GLOBALS_V4
        or (
            session_caller.f_code not in expected_code
            if type(expected_code) is tuple
            else session_caller.f_code is not expected_code
        )
    ):
        _fail("V4 route-segment node bypassed its exact session issuer")


@dataclass(frozen=True, slots=True)
class _SiteSpecV4:
    boundary_key: str
    dispatch_key: str
    target_path: str
    operation_source_symbol: str


_SITE_SPECS: tuple[_SiteSpecV4, ...] = (
    _SiteSpecV4(
        "direct-fallback.action-evaluated",
        "direct-fallback.action.evaluated",
        "fallback.actions_evaluated",
        "_OwnedFallbackLedgerV2.evaluate_action",
    ),
    _SiteSpecV4(
        "direct-fallback.bellman-backup",
        "direct-fallback.bellman.backup",
        "fallback.bellman_backups",
        "_OwnedFallbackLedgerV2.compose_candidate",
    ),
    _SiteSpecV4(
        "direct-fallback.cap-check",
        "direct-fallback.control.cap-check",
        "control.cap_checks",
        "_OwnedFallbackLedgerV2._guard",
    ),
    _SiteSpecV4(
        "direct-fallback.cap-rejection",
        "direct-fallback.control.cap-rejection",
        "control.cap_rejections",
        "_OwnedFallbackLedgerV2._reject",
    ),
    _SiteSpecV4(
        "direct-fallback.ground-step",
        "direct-fallback.kernel.transition",
        "fallback.ground_steps",
        "_OwnedFallbackLedgerV2.reserve_transition",
    ),
    _SiteSpecV4(
        "direct-fallback.outcome-row",
        "direct-fallback.outcome.row",
        "fallback.outcome_rows",
        "_OwnedFallbackLedgerV2.record_outcomes",
    ),
    _SiteSpecV4(
        "direct-fallback.state-expanded",
        "direct-fallback.state.expanded",
        "fallback.states_expanded",
        "_OwnedFallbackLedgerV2.expand_state",
    ),
)
_SPEC_BY_DISPATCH = MappingProxyType({row.dispatch_key: row for row in _SITE_SPECS})
_EXPECTED_PATHS = frozenset(row.target_path for row in _SITE_SPECS)
_OWNED_ENGINE_SITE_SPECS: tuple[_SiteSpecV4, ...] = tuple(
    _SiteSpecV4(
        row.boundary_key,
        row.dispatch_key,
        row.target_path,
        row.operation_source_symbol.replace(
            "_OwnedFallbackLedgerV2", "_OwnedFallbackLedgerV3"
        ),
    )
    for row in _SITE_SPECS
)
_OWNED_ENGINE_SPEC_BY_DISPATCH = MappingProxyType(
    {row.dispatch_key: row for row in _OWNED_ENGINE_SITE_SPECS}
)


@dataclass(frozen=True, slots=True)
class SealedSourceMemberAuthorityV4:
    _issuer: InitVar[object]
    source_module: str
    source_sha256: str
    source_byte_count: int
    legacy_source_archive_id: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("sealed source authority is verifier-issued only")
        if (
            self.source_module != SOURCE_MODULE
            or self.source_sha256 != EXPECTED_SOURCE_SHA256
            or self.source_byte_count != EXPECTED_SOURCE_BYTE_COUNT
        ):
            _fail("sealed source authority changed the exact member")
        _cid(self.legacy_source_archive_id, "legacy source archive")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sealed_route_segment_source_authority.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_module": self.source_module,
            "source_relative_path": SOURCE_RELATIVE_PATH,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "legacy_source_archive_id": self.legacy_source_archive_id,
            "input_form": "CALLER_SUPPLIED_CANONICAL_SEALED_MEMBER_BYTES",
            "live_archive_loader_called": False,
            "filesystem_locator_used": False,
            "construction_only": True,
        }

    @property
    def source_authority_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_SOURCE_AUTHORITY_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_authority_id": self.source_authority_id}


@dataclass(frozen=True, slots=True)
class VerifiedOperationBoundaryV4:
    _issuer: InitVar[object]
    boundary_id: str
    boundary_key: str
    dispatch_key: str
    target_path: str
    owner: str
    operation_source_module: str
    operation_source_symbol: str
    source_gateway_symbol: str
    symbol_ast_sha256: str
    call_ast_sha256: str
    call_location: tuple[int, int, int, int]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("verified operation boundary is verifier-issued only")
        _cid(self.boundary_id, "operation boundary")
        spec = _SPEC_BY_DISPATCH.get(self.dispatch_key)
        if (
            spec is None
            or self.boundary_key != spec.boundary_key
            or self.target_path != spec.target_path
            or self.operation_source_module != SOURCE_MODULE
            or self.operation_source_symbol != spec.operation_source_symbol
            or self.source_gateway_symbol != LEGACY_OWNER_GATEWAY
            or type(self.call_location) is not tuple
            or len(self.call_location) != 4
            or any(type(value) is not int or value < 0 for value in self.call_location)
        ):
            _fail("verified operation boundary changed the seven-site inventory")
        for value in (self.owner, self.symbol_ast_sha256, self.call_ast_sha256):
            if type(value) is not str or not value:
                _fail("verified operation boundary text is invalid")

    def to_document(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "target_path": self.target_path,
            "owner": self.owner,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "source_gateway_symbol": self.source_gateway_symbol,
            "symbol_ast_sha256": self.symbol_ast_sha256,
            "call_ast_sha256": self.call_ast_sha256,
            "call_location": list(self.call_location),
            "reducer": ReducerEnum.SUM.value,
            "unit_amount": True,
        }


@dataclass(frozen=True, slots=True)
class OwnerRuntimeIntegrationBlockerV4:
    _issuer: InitVar[object]
    observed_gateway_symbol: str
    required_gateway_symbol: str
    observed_bind_finish_contract: str
    required_successor: str
    code: str = "SUCCESSOR_OWNED_ENGINE_IMPORTING_V4_GATEWAYS_REQUIRED"

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("owner integration blocker is verifier-issued only")
        if (
            self.observed_gateway_symbol != LEGACY_OWNER_GATEWAY
            or self.required_gateway_symbol != REQUIRED_OWNER_GATEWAY
            or self.observed_bind_finish_contract != "FROZEN_V3_AUTHORIZER"
            or self.required_successor != "SEALED_SOURCE_OWNED_ENGINE_V4"
        ):
            _fail("owner integration blocker changed its exact dependency")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_segment_owner_integration_blocker.v4",
            "schema_version": SCHEMA_VERSION,
            "code": self.code,
            "observed_gateway_symbol": self.observed_gateway_symbol,
            "required_gateway_symbol": self.required_gateway_symbol,
            "observed_bind_finish_contract": self.observed_bind_finish_contract,
            "required_successor": self.required_successor,
            "v3_authorizer_bypass_allowed": False,
            "production_owner_source_integrated": False,
            "construction_only": True,
        }

    @property
    def blocker_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNER_BLOCKER_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "blocker_id": self.blocker_id}


@dataclass(frozen=True, slots=True)
class VerifiedOperationBoundaryManifestAuthorityV4:
    _issuer: InitVar[object]
    source_authority: SealedSourceMemberAuthorityV4
    legacy_boundary_manifest_id: str
    manifest_document_sha256: str
    manifest_document_byte_count: int
    counter_registry_id: str
    stage_profile_id: str
    boundaries: tuple[VerifiedOperationBoundaryV4, ...]
    owner_integration_blocker: OwnerRuntimeIntegrationBlockerV4

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("operation-boundary manifest authority is verifier-issued only")
        if (
            type(self.source_authority) is not SealedSourceMemberAuthorityV4
            or type(self.boundaries) is not tuple
            or len(self.boundaries) != EXPECTED_BOUNDARY_COUNT
            or tuple(sorted(self.boundaries, key=lambda row: row.boundary_key))
            != self.boundaries
            or {row.dispatch_key for row in self.boundaries}
            != set(_SPEC_BY_DISPATCH)
            or type(self.owner_integration_blocker)
            is not OwnerRuntimeIntegrationBlockerV4
            or self.legacy_boundary_manifest_id != EXPECTED_BOUNDARY_MANIFEST_ID
            or self.manifest_document_sha256
            != EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256
            or type(self.manifest_document_byte_count) is not int
            or self.manifest_document_byte_count <= 0
        ):
            _fail("operation-boundary manifest authority is inconsistent")
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
        ):
            _cid(value, label)

    @property
    def by_dispatch(self) -> Mapping[str, VerifiedOperationBoundaryV4]:
        return MappingProxyType({row.dispatch_key: row for row in self.boundaries})

    @property
    def runtime_gateway_compatible(self) -> bool:
        return False

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_operation_boundary_manifest_authority.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "required_contract_version": REQUIRED_CONTRACT_VERSION,
            "source_authority_id": self.source_authority.source_authority_id,
            "legacy_boundary_manifest_id": self.legacy_boundary_manifest_id,
            "manifest_document_sha256": self.manifest_document_sha256,
            "manifest_document_byte_count": self.manifest_document_byte_count,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "stage_kind": registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value,
            "boundaries": [row.to_document() for row in self.boundaries],
            "boundary_count": len(self.boundaries),
            "owner_integration_blocker_id": self.owner_integration_blocker.blocker_id,
            "runtime_gateway_compatible": False,
            "ground_or_planner_work_performed_during_construction": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "production_owner_source_integrated": False,
            "production_closure_claimed": False,
        }

    @property
    def manifest_authority_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_MANIFEST_AUTHORITY_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_authority": self.source_authority.to_document(),
            "owner_integration_blocker": self.owner_integration_blocker.to_document(),
            "manifest_authority_id": self.manifest_authority_id,
        }


_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "counter_registry_id",
        "stage_profile_id",
        "stage_kind",
        "parent_v2_manifest_id",
        "parent_v2_manifest_document_sha256",
        "source_archive_id",
        "live_owner_binding_id",
        "source_members",
        "boundaries",
        "boundary_count",
        "production_source_integrated",
        "runtime_evidence_issued",
        "counter_records_issued",
        "work_vectors_issued",
        "comparison_vectors_issued",
        "construction_only",
        "production_closure_claimed",
        "boundary_manifest_id",
    }
)
_BOUNDARY_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "boundary_key",
        "dispatch_key",
        "stage_kind",
        "target_path",
        "owner",
        "reducer",
        "operation_source_module",
        "operation_source_symbol",
        "source_sha256",
        "source_byte_count",
        "symbol_ast_sha256",
        "call_ast_sha256",
        "call_location",
        "literal_dispatch",
        "unit_amount",
        "real_ledger_primitive_site",
        "construction_only",
        "boundary_id",
    }
)


def _qualified_functions(tree: ast.AST) -> dict[str, ast.FunctionDef]:
    found: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_OwnedFallbackLedgerV2":
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    found[f"{node.name}.{child.name}"] = child
    return found


def _literal_gateway_call(call: ast.Call) -> tuple[str, str] | None:
    if not isinstance(call.func, ast.Name):
        return None
    if call.func.id not in {LEGACY_OWNER_GATEWAY, REQUIRED_OWNER_GATEWAY}:
        return None
    if len(call.args) != 2 or call.keywords:
        return None
    dispatch, amount = call.args
    if (
        not isinstance(dispatch, ast.Constant)
        or type(dispatch.value) is not str
        or not isinstance(amount, ast.Constant)
        or type(amount.value) is not int
        or amount.value != 1
    ):
        return None
    return call.func.id, dispatch.value


def verify_sealed_operation_boundary_authority_v4(
    source_member_bytes: bytes,
    boundary_manifest_document_bytes: bytes,
) -> VerifiedOperationBoundaryManifestAuthorityV4:
    """Replay the exact V3 source/manifest join from caller-supplied bytes only."""

    if type(source_member_bytes) is not bytes:
        _fail("sealed source member must be exact bytes")
    if (
        len(source_member_bytes) != EXPECTED_SOURCE_BYTE_COUNT
        or _sha256(source_member_bytes) != EXPECTED_SOURCE_SHA256
    ):
        _fail("sealed source member differs from the frozen V3 owner source")
    if type(boundary_manifest_document_bytes) is not bytes:
        _fail("operation-boundary manifest document must be canonical bytes")
    if (
        _sha256(boundary_manifest_document_bytes)
        != EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256
    ):
        _fail("operation-boundary manifest document digest changed")
    try:
        document = loads_canonical_json(boundary_manifest_document_bytes)
        require_exact_fields(
            document,
            _MANIFEST_FIELDS,
            context="V3 operation-boundary manifest",
        )
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "operation-boundary manifest document is not canonical"
        ) from error
    if type(document) is not dict:
        _fail("operation-boundary manifest document must be an object")
    manifest_payload = dict(document)
    manifest_id = manifest_payload.pop("boundary_manifest_id")
    if (
        manifest_id != EXPECTED_BOUNDARY_MANIFEST_ID
        or _legacy_content_id(_LEGACY_MANIFEST_DOMAIN, manifest_payload)
        != manifest_id
        or document["schema"]
        != "acfqp.direct_fallback_operation_boundary_manifest.v3"
        or document["schema_version"] != "3.0.0"
        or document["stage_kind"]
        != registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value
        or document["boundary_count"] != EXPECTED_BOUNDARY_COUNT
        or document["runtime_evidence_issued"] is not False
        or document["counter_records_issued"] != 0
        or document["work_vectors_issued"] != 0
        or document["comparison_vectors_issued"] != 0
        or document["construction_only"] is not True
        or document["production_closure_claimed"] is not False
    ):
        _fail("operation-boundary manifest document changed its exact contract")

    legacy_archive_id = _legacy_content_id(
        _LEGACY_ARCHIVE_DOMAIN,
        {
            "schema": "acfqp.direct_fallback_source_archive.v3",
            "schema_version": "3.0.0",
            "members": [
                {
                    "module_name": SOURCE_MODULE,
                    "source_sha256": EXPECTED_SOURCE_SHA256,
                    "source_byte_count": EXPECTED_SOURCE_BYTE_COUNT,
                }
            ],
        },
    )
    expected_member = {
        "module_name": SOURCE_MODULE,
        "relative_path": SOURCE_RELATIVE_PATH,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_byte_count": EXPECTED_SOURCE_BYTE_COUNT,
    }
    if (
        document["source_archive_id"] != legacy_archive_id
        or document["source_members"] != [expected_member]
    ):
        _fail("operation-boundary manifest crossed its sealed source member")

    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    registry.validate_official_catalogue()
    stage_profile.validate(registry)
    if (
        document["counter_registry_id"] != registry.registry_id
        or document["stage_profile_id"] != stage_profile.stage_profile_id
    ):
        _fail("operation-boundary manifest crossed the V6 registry or stage profile")
    allowed = set(
        stage_profile.by_stage[
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ].allowed_nonzero_paths
    )

    try:
        tree = ast.parse(source_member_bytes, filename="<sealed-source-member-v4>")
    except (SyntaxError, TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "sealed source member is not valid Python"
        ) from error
    functions = _qualified_functions(tree)
    all_gateway_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {LEGACY_OWNER_GATEWAY, REQUIRED_OWNER_GATEWAY}
    ]
    literal_calls = [_literal_gateway_call(call) for call in all_gateway_calls]
    if (
        len(all_gateway_calls) != EXPECTED_BOUNDARY_COUNT
        or any(row is None for row in literal_calls)
        or {row[1] for row in literal_calls if row is not None}
        != set(_SPEC_BY_DISPATCH)
        or {row[0] for row in literal_calls if row is not None}
        != {LEGACY_OWNER_GATEWAY}
    ):
        _fail("sealed source changed the exact seven legacy owner gateways")

    raw_boundaries = document["boundaries"]
    if type(raw_boundaries) is not list or len(raw_boundaries) != EXPECTED_BOUNDARY_COUNT:
        _fail("operation-boundary manifest lacks seven boundaries")
    verified_boundaries: list[VerifiedOperationBoundaryV4] = []
    for row in raw_boundaries:
        try:
            require_exact_fields(row, _BOUNDARY_FIELDS, context="V3 operation boundary")
        except Phase3EIdentityError as error:
            raise ConstructionAccountingRouteSegmentV4Error(
                "operation-boundary row fields changed"
            ) from error
        if type(row) is not dict:
            _fail("operation-boundary row must be an object")
        boundary_payload = dict(row)
        boundary_id = boundary_payload.pop("boundary_id")
        spec = _SPEC_BY_DISPATCH.get(row["dispatch_key"])
        leaf = registry.by_path.get(row["target_path"])
        if (
            spec is None
            or row["boundary_key"] != spec.boundary_key
            or row["target_path"] != spec.target_path
            or row["operation_source_symbol"] != spec.operation_source_symbol
            or row["operation_source_module"] != SOURCE_MODULE
            or row["source_sha256"] != EXPECTED_SOURCE_SHA256
            or row["source_byte_count"] != EXPECTED_SOURCE_BYTE_COUNT
            or row["reducer"] != ReducerEnum.SUM.value
            or row["stage_kind"]
            != registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value
            or row["literal_dispatch"] is not True
            or row["unit_amount"] is not True
            or row["real_ledger_primitive_site"] is not True
            or row["construction_only"] is not True
            or _legacy_content_id(_LEGACY_BOUNDARY_DOMAIN, boundary_payload)
            != boundary_id
            or leaf is None
            or row["target_path"] not in allowed
            or leaf.reducer is not ReducerEnum.SUM
            or row["owner"] != leaf.owner
        ):
            _fail("operation-boundary row changed its source or V6 ownership")
        symbol = functions.get(spec.operation_source_symbol)
        if symbol is None:
            _fail("sealed source lost an owned ledger method")
        matching = [
            call
            for call in ast.walk(symbol)
            if isinstance(call, ast.Call)
            and _literal_gateway_call(call)
            == (LEGACY_OWNER_GATEWAY, spec.dispatch_key)
        ]
        if len(matching) != 1:
            _fail("sealed source lost an exact owned gateway call")
        call = matching[0]
        symbol_hash = _sha256(
            ast.dump(symbol, include_attributes=False).encode("utf-8")
        )
        call_hash = _sha256(ast.dump(call, include_attributes=False).encode("utf-8"))
        location = (
            call.lineno,
            call.col_offset,
            call.end_lineno,
            call.end_col_offset,
        )
        if (
            row["symbol_ast_sha256"] != symbol_hash
            or row["call_ast_sha256"] != call_hash
            or row["call_location"] != list(location)
        ):
            _fail("sealed source AST differs from its boundary manifest")
        verified_boundaries.append(
            VerifiedOperationBoundaryV4(
                _ISSUER,
                boundary_id,
                spec.boundary_key,
                spec.dispatch_key,
                spec.target_path,
                leaf.owner,
                SOURCE_MODULE,
                spec.operation_source_symbol,
                LEGACY_OWNER_GATEWAY,
                symbol_hash,
                call_hash,
                location,
            )
        )

    source_authority = SealedSourceMemberAuthorityV4(
        _ISSUER,
        SOURCE_MODULE,
        EXPECTED_SOURCE_SHA256,
        EXPECTED_SOURCE_BYTE_COUNT,
        legacy_archive_id,
    )
    blocker = OwnerRuntimeIntegrationBlockerV4(
        _ISSUER,
        LEGACY_OWNER_GATEWAY,
        REQUIRED_OWNER_GATEWAY,
        "FROZEN_V3_AUTHORIZER",
        "SEALED_SOURCE_OWNED_ENGINE_V4",
    )
    return VerifiedOperationBoundaryManifestAuthorityV4(
        _ISSUER,
        source_authority,
        manifest_id,
        EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256,
        len(boundary_manifest_document_bytes),
        registry.registry_id,
        stage_profile.stage_profile_id,
        tuple(sorted(verified_boundaries, key=lambda item: item.boundary_key)),
        blocker,
    )


@dataclass(frozen=True, slots=True)
class VerifiedOwnedEngineBoundaryV4:
    """One exact V4 gateway site in the sealed successor engine."""

    _issuer: InitVar[object]
    dispatch_key: str
    target_path: str
    operation_source_symbol: str
    symbol_ast_sha256: str
    call_ast_sha256: str
    call_location: tuple[int, int, int, int]

    def __post_init__(self, _issuer: object) -> None:
        spec = _OWNED_ENGINE_SPEC_BY_DISPATCH.get(self.dispatch_key)
        if (
            _issuer is not _ISSUER
            or spec is None
            or self.target_path != spec.target_path
            or self.operation_source_symbol != spec.operation_source_symbol
            or type(self.symbol_ast_sha256) is not str
            or type(self.call_ast_sha256) is not str
            or type(self.call_location) is not tuple
            or len(self.call_location) != 4
            or any(type(value) is not int or value < 0 for value in self.call_location)
        ):
            _fail("sealed owned-engine boundary is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sealed_owned_engine_boundary.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_engine_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "dispatch_key": self.dispatch_key,
            "target_path": self.target_path,
            "operation_source_module": OWNED_ENGINE_SOURCE_MODULE,
            "operation_source_symbol": self.operation_source_symbol,
            "source_gateway_symbol": REQUIRED_OWNER_GATEWAY,
            "symbol_ast_sha256": self.symbol_ast_sha256,
            "call_ast_sha256": self.call_ast_sha256,
            "call_location": list(self.call_location),
            "reducer": ReducerEnum.SUM.value,
            "unit_amount": True,
        }

    @property
    def boundary_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_BOUNDARY_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owned_engine_boundary_id": self.boundary_id}


@dataclass(frozen=True, slots=True)
class VerifiedOwnedEngineAuthorityV4:
    """Sealed-source authority for ``phase3e_fallback_owned_v3`` only."""

    _issuer: InitVar[object]
    source_sha256: str
    source_byte_count: int
    counter_registry_id: str
    stage_profile_id: str
    boundaries: tuple[VerifiedOwnedEngineBoundaryV4, ...]
    search_entry_symbol_ast_sha256: str
    bind_call_ast_sha256: str
    bind_call_location: tuple[int, int, int, int]
    finish_call_ast_sha256: str
    finish_call_location: tuple[int, int, int, int]
    compiled_code_fingerprints: tuple[tuple[str, str], ...]

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or self.source_sha256 != OWNED_ENGINE_SOURCE_SHA256
            or self.source_byte_count != OWNED_ENGINE_SOURCE_BYTE_COUNT
            or type(self.boundaries) is not tuple
            or len(self.boundaries) != EXPECTED_BOUNDARY_COUNT
            or tuple(sorted(self.boundaries, key=lambda row: row.dispatch_key))
            != self.boundaries
            or {row.dispatch_key for row in self.boundaries}
            != set(_OWNED_ENGINE_SPEC_BY_DISPATCH)
            or any(
                type(value) is not str or not value
                for value in (
                    self.search_entry_symbol_ast_sha256,
                    self.bind_call_ast_sha256,
                    self.finish_call_ast_sha256,
                )
            )
            or any(
                type(location) is not tuple
                or len(location) != 4
                or any(type(value) is not int or value < 0 for value in location)
                for location in (
                    self.bind_call_location,
                    self.finish_call_location,
                )
            )
            or type(self.compiled_code_fingerprints) is not tuple
            or tuple(sorted(self.compiled_code_fingerprints))
            != self.compiled_code_fingerprints
            or len(self.compiled_code_fingerprints) != 12
            or len({name for name, _digest in self.compiled_code_fingerprints})
            != len(self.compiled_code_fingerprints)
            or any(
                type(name) is not str
                or not name
                or type(digest) is not str
                or len(digest) != 64
                for name, digest in self.compiled_code_fingerprints
            )
        ):
            _fail("sealed owned-engine authority is inconsistent")
        _cid(self.counter_registry_id, "owned-engine counter registry")
        _cid(self.stage_profile_id, "owned-engine stage profile")

    @property
    def by_dispatch(self) -> Mapping[str, VerifiedOwnedEngineBoundaryV4]:
        return MappingProxyType({row.dispatch_key: row for row in self.boundaries})

    def _source_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sealed_owned_engine_source.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_engine_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "source_module": OWNED_ENGINE_SOURCE_MODULE,
            "source_relative_path": OWNED_ENGINE_SOURCE_RELATIVE_PATH,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "caller_supplied_sealed_member_bytes": True,
            "live_path_loader_called": False,
        }

    @property
    def source_authority_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_SOURCE_DOMAIN,
            self._source_payload(),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_owned_engine_authority.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "proposed_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "source_authority_id": self.source_authority_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "stage_kind": registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value,
            "boundaries": [row.to_document() for row in self.boundaries],
            "boundary_count": len(self.boundaries),
            "required_gateway": REQUIRED_OWNER_GATEWAY,
            "required_bind": "bind_owned_fallback_search_v4",
            "required_finish": "finish_owned_fallback_search_v4",
            "search_entry_symbol": "run_owned_ground_fallback_search_v3",
            "search_entry_symbol_ast_sha256": (
                self.search_entry_symbol_ast_sha256
            ),
            "bind_call_ast_sha256": self.bind_call_ast_sha256,
            "bind_call_location": list(self.bind_call_location),
            "finish_call_ast_sha256": self.finish_call_ast_sha256,
            "finish_call_location": list(self.finish_call_location),
            "compiled_code_fingerprints": [
                {"qualified_name": name, "sha256": digest}
                for name, digest in self.compiled_code_fingerprints
            ],
            "compiled_code_fingerprints_authoritative": True,
            "ast_digests_authoritative": True,
            "ast_digests_role": "INDEPENDENTLY_FROZEN_TOPOLOGY_PINS",
            "bind_directly_precedes_query_validation": True,
            "finish_directly_precedes_execution_return": True,
            "runtime_gateway_compatible": True,
            "old_v3_runner_authorizer_used": False,
            "live_path_loader_called": False,
            "production_owner_source_integrated": True,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
            "construction_only": True,
        }

    @property
    def authority_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_AUTHORITY_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_authority": self._source_payload(),
            "owned_engine_authority_id": self.authority_id,
        }


def _owned_engine_qualified_functions(tree: ast.AST) -> dict[str, ast.FunctionDef]:
    found: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_OwnedFallbackLedgerV3":
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    found[f"{node.name}.{child.name}"] = child
    return found


def _compiled_owned_engine_codes_v4(source_member_bytes: bytes) -> Mapping[str, CodeType]:
    """Compile, but never execute, the exact member and locate owner code objects."""

    try:
        module_code = compile(
            source_member_bytes,
            "<sealed-owned-engine-compiled-v4>",
            "exec",
            dont_inherit=True,
            optimize=0,
        )
    except (SyntaxError, TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "sealed owned-engine source cannot be compiled"
        ) from error
    top_level = {
        row.co_name: row
        for row in module_code.co_consts
        if isinstance(row, CodeType)
    }
    ledger_class = top_level.get("_OwnedFallbackLedgerV3")
    if ledger_class is None:
        _fail("sealed owned-engine compiled source lost its ledger class")
    ledger_methods = {
        row.co_name: row
        for row in ledger_class.co_consts
        if isinstance(row, CodeType)
    }
    required = {
        *(f"_OwnedFallbackLedgerV3.{name}" for name in (
            "__init__",
            "_guard",
            "_reject",
            "expand_state",
            "evaluate_action",
            "reserve_transition",
            "record_outcomes",
            "compose_candidate",
        )),
        "_legacy_work_vector_v3",
        "run_owned_ground_fallback_search_v3",
        "require_frozen_owned_fallback_source_binding_v3",
        "require_frozen_owned_fallback_engine_binding_v3",
    }
    found: dict[str, CodeType] = {
        f"_OwnedFallbackLedgerV3.{name}": code
        for name, code in ledger_methods.items()
        if f"_OwnedFallbackLedgerV3.{name}" in required
    }
    found.update(
        {
            name: top_level[name]
            for name in required
            if not name.startswith("_OwnedFallbackLedgerV3.") and name in top_level
        }
    )
    if set(found) != required:
        _fail("sealed owned-engine compiled code inventory changed")
    return MappingProxyType(found)


def _live_owned_engine_code_fingerprints_v4(binding: Any) -> tuple[tuple[str, str], ...]:
    """Independently hash actual live code; never trust module-supplied digests."""

    rows: list[tuple[str, str]] = []
    try:
        for name, _function, code in binding.source_binding.method_bindings:
            rows.append(
                (
                    f"_OwnedFallbackLedgerV3.{name}",
                    _normalized_recursive_code_fingerprint_v4(code),
                )
            )
        rows.extend(
            (
                (
                    "_legacy_work_vector_v3",
                    _normalized_recursive_code_fingerprint_v4(
                        binding.work_vector_helper_code
                    ),
                ),
                (
                    "run_owned_ground_fallback_search_v3",
                    _normalized_recursive_code_fingerprint_v4(
                        binding.search_entry_code
                    ),
                ),
                (
                    "require_frozen_owned_fallback_source_binding_v3",
                    _normalized_recursive_code_fingerprint_v4(
                        binding.source_validator_code
                    ),
                ),
                (
                    "require_frozen_owned_fallback_engine_binding_v3",
                    _normalized_recursive_code_fingerprint_v4(
                        binding.engine_validator.__code__
                    ),
                ),
            )
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "owned-engine live code inventory is unavailable"
        ) from error
    result = tuple(sorted(rows))
    if len(result) != 12 or len({name for name, _digest in result}) != 12:
        _fail("owned-engine live code inventory changed")
    return result


def _verify_sealed_owned_engine_authority_impl_v4(
    source_member_bytes: bytes,
    _frozen_pins: tuple[Any, ...] = (
        OWNED_ENGINE_SOURCE_BYTE_COUNT,
        OWNED_ENGINE_SOURCE_SHA256,
        OWNED_ENGINE_SEARCH_AST_SHA256,
        OWNED_ENGINE_BIND_AST_SHA256,
        OWNED_ENGINE_BIND_LOCATION,
        OWNED_ENGINE_FINISH_AST_SHA256,
        OWNED_ENGINE_FINISH_LOCATION,
    ),
) -> VerifiedOwnedEngineAuthorityV4:
    """Verify the exact successor engine without repository/path discovery."""

    (
        frozen_source_byte_count,
        frozen_source_sha256,
        frozen_search_ast_sha256,
        frozen_bind_ast_sha256,
        frozen_bind_location,
        frozen_finish_ast_sha256,
        frozen_finish_location,
    ) = _frozen_pins

    if (
        type(source_member_bytes) is not bytes
        or len(source_member_bytes) != frozen_source_byte_count
        or _sha256(source_member_bytes) != frozen_source_sha256
    ):
        _fail("sealed owned-engine source differs from Contract 2.0.54")
    try:
        tree = ast.parse(source_member_bytes, filename="<sealed-owned-engine-v4>")
    except (SyntaxError, TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "sealed owned-engine source is not valid Python"
        ) from error

    imported: set[str] = set()
    forbidden_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "acfqp.construction_accounting_route_segment_v4":
                imported.update(alias.name for alias in node.names)
            if node.module and (
                "construction_accounting_route_segment_v3" in node.module
                or "canonical_infeasible_fallback_owned_runner" in node.module
                or "direct_fallback_operation_boundary_manifest" in node.module
            ):
                forbidden_imports.add(node.module)
        elif isinstance(node, ast.Import):
            forbidden_imports.update(
                alias.name
                for alias in node.names
                if "construction_accounting_route_segment_v3" in alias.name
                or "canonical_infeasible_fallback_owned_runner" in alias.name
                or "direct_fallback_operation_boundary_manifest" in alias.name
            )
    required_imports = {
        "OWNED_ROUTE_EVENT_ACK_V4",
        "bind_owned_fallback_search_v4",
        "emit_owned_route_operation_v4",
        "finish_owned_fallback_search_v4",
        "seal_owned_fallback_engine_import_v4",
        "verify_owned_fallback_engine_import_seal_v4",
    }
    if imported != required_imports or forbidden_imports:
        _fail("sealed owned engine changed its exact V4 runtime imports")

    functions = _owned_engine_qualified_functions(tree)
    gateway_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == REQUIRED_OWNER_GATEWAY
    ]
    bind_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "bind_owned_fallback_search_v4"
    ]
    finish_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "finish_owned_fallback_search_v4"
    ]
    search_entries = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_owned_ground_fallback_search_v3"
    ]
    literal_calls = [_literal_gateway_call(call) for call in gateway_calls]
    if (
        len(gateway_calls) != EXPECTED_BOUNDARY_COUNT
        or any(row is None for row in literal_calls)
        or {row[0] for row in literal_calls if row is not None}
        != {REQUIRED_OWNER_GATEWAY}
        or {row[1] for row in literal_calls if row is not None}
        != set(_OWNED_ENGINE_SPEC_BY_DISPATCH)
        or len(bind_calls) != 1
        or len(finish_calls) != 1
        or len(search_entries) != 1
    ):
        _fail("sealed owned engine changed its seven-site/bind/finish topology")

    search_entry = search_entries[0]
    bind_call = bind_calls[0]
    finish_call = finish_calls[0]
    direct_call_indices: dict[str, int] = {}
    for index, statement in enumerate(search_entry.body):
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Name)
            and statement.value.func.id
            in {"bind_owned_fallback_search_v4", "finish_owned_fallback_search_v4"}
        ):
            direct_call_indices[statement.value.func.id] = index
    bind_index = direct_call_indices.get("bind_owned_fallback_search_v4")
    finish_index = direct_call_indices.get("finish_owned_fallback_search_v4")
    if (
        bind_index is None
        or finish_index is None
        or search_entry.body[bind_index].value is not bind_call
        or search_entry.body[finish_index].value is not finish_call
        or len(bind_call.args) != 1
        or not isinstance(bind_call.args[0], ast.Name)
        or bind_call.args[0].id != "ledger"
        or bind_call.keywords
        or len(finish_call.args) != 2
        or not isinstance(finish_call.args[0], ast.Name)
        or finish_call.args[0].id != "ledger"
        or not isinstance(finish_call.args[1], ast.Name)
        or finish_call.args[1].id != "execution"
        or finish_call.keywords
        or bind_index <= 0
        or bind_index + 1 >= len(search_entry.body)
        or finish_index <= 0
        or finish_index + 1 >= len(search_entry.body)
    ):
        _fail("sealed owned engine moved bind/finish outside the exact search caller")
    ledger_statement = search_entry.body[bind_index - 1]
    validation_statement = search_entry.body[bind_index + 1]
    execution_statement = search_entry.body[finish_index - 1]
    return_statement = search_entry.body[finish_index + 1]
    if (
        not isinstance(ledger_statement, ast.Assign)
        or len(ledger_statement.targets) != 1
        or not isinstance(ledger_statement.targets[0], ast.Name)
        or ledger_statement.targets[0].id != "ledger"
        or not isinstance(ledger_statement.value, ast.Call)
        or not isinstance(ledger_statement.value.func, ast.Name)
        or ledger_statement.value.func.id != "_OwnedFallbackLedgerV3"
        or not isinstance(validation_statement, ast.Expr)
        or not isinstance(validation_statement.value, ast.Call)
        or not isinstance(validation_statement.value.func, ast.Name)
        or validation_statement.value.func.id != "validate_query"
        or not isinstance(execution_statement, ast.Assign)
        or len(execution_statement.targets) != 1
        or not isinstance(execution_statement.targets[0], ast.Name)
        or execution_statement.targets[0].id != "execution"
        or not isinstance(return_statement, ast.Return)
        or not isinstance(return_statement.value, ast.Name)
        or return_statement.value.id != "execution"
    ):
        _fail("sealed owned engine changed bind-before-ground or finish-before-return")

    search_ast_sha256 = _sha256(
        ast.dump(search_entry, include_attributes=False).encode("utf-8")
    )
    bind_ast_sha256 = _sha256(
        ast.dump(bind_call, include_attributes=False).encode("utf-8")
    )
    bind_location = (
        bind_call.lineno,
        bind_call.col_offset,
        bind_call.end_lineno,
        bind_call.end_col_offset,
    )
    finish_ast_sha256 = _sha256(
        ast.dump(finish_call, include_attributes=False).encode("utf-8")
    )
    finish_location = (
        finish_call.lineno,
        finish_call.col_offset,
        finish_call.end_lineno,
        finish_call.end_col_offset,
    )
    if (
        search_ast_sha256 != frozen_search_ast_sha256
        or bind_ast_sha256 != frozen_bind_ast_sha256
        or bind_location != frozen_bind_location
        or finish_ast_sha256 != frozen_finish_ast_sha256
        or finish_location != frozen_finish_location
    ):
        _fail("sealed owned engine changed its independently frozen AST pins")

    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    registry.validate_official_catalogue()
    stage.validate(registry)
    allowed = set(
        stage.by_stage[
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ].allowed_nonzero_paths
    )
    boundaries: list[VerifiedOwnedEngineBoundaryV4] = []
    for spec in _OWNED_ENGINE_SITE_SPECS:
        symbol = functions.get(spec.operation_source_symbol)
        if symbol is None or spec.target_path not in allowed:
            _fail("sealed owned engine lost an exact ledger owner")
        matching = [
            call
            for call in ast.walk(symbol)
            if isinstance(call, ast.Call)
            and _literal_gateway_call(call)
            == (REQUIRED_OWNER_GATEWAY, spec.dispatch_key)
        ]
        if len(matching) != 1:
            _fail("sealed owned engine lost an exact V4 gateway call")
        call = matching[0]
        boundaries.append(
            VerifiedOwnedEngineBoundaryV4(
                _ISSUER,
                spec.dispatch_key,
                spec.target_path,
                spec.operation_source_symbol,
                _sha256(ast.dump(symbol, include_attributes=False).encode("utf-8")),
                _sha256(ast.dump(call, include_attributes=False).encode("utf-8")),
                (call.lineno, call.col_offset, call.end_lineno, call.end_col_offset),
            )
        )
    compiled_codes = _compiled_owned_engine_codes_v4(source_member_bytes)
    compiled_fingerprints = tuple(
        sorted(
            (
                name,
                _normalized_recursive_code_fingerprint_v4(code),
            )
            for name, code in compiled_codes.items()
        )
    )
    return VerifiedOwnedEngineAuthorityV4(
        _ISSUER,
        OWNED_ENGINE_SOURCE_SHA256,
        OWNED_ENGINE_SOURCE_BYTE_COUNT,
        registry.registry_id,
        stage.stage_profile_id,
        tuple(sorted(boundaries, key=lambda row: row.dispatch_key)),
        search_ast_sha256,
        bind_ast_sha256,
        bind_location,
        finish_ast_sha256,
        finish_location,
        compiled_fingerprints,
    )


_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_V4 = (
    _verify_sealed_owned_engine_authority_impl_v4
)
_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_GLOBALS_V4 = (
    _verify_sealed_owned_engine_authority_impl_v4.__globals__
)
_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_CODE_V4 = (
    _verify_sealed_owned_engine_authority_impl_v4.__code__
)
_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_DEFAULTS_V4 = (
    _verify_sealed_owned_engine_authority_impl_v4.__defaults__
)
_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_KWDEFAULTS_V4 = (
    _verify_sealed_owned_engine_authority_impl_v4.__kwdefaults__
)


def verify_sealed_owned_engine_authority_v4(
    source_member_bytes: bytes,
) -> VerifiedOwnedEngineAuthorityV4:
    """Verify only the one frozen Contract-2.0.54 member."""

    verifier = _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_V4
    if (
        globals().get("_verify_sealed_owned_engine_authority_impl_v4")
        is not verifier
        or verifier.__globals__
        is not _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_GLOBALS_V4
        or verifier.__code__ is not _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_CODE_V4
        or verifier.__defaults__
        is not _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_DEFAULTS_V4
        or verifier.__kwdefaults__
        is not _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_KWDEFAULTS_V4
        or verifier.__kwdefaults__ is not None
    ):
        _fail("sealed owned-engine verifier implementation changed")
    return verifier(source_member_bytes)


_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_V4 = verify_sealed_owned_engine_authority_v4
_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_GLOBALS_V4 = (
    verify_sealed_owned_engine_authority_v4.__globals__
)
_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_CODE_V4 = (
    verify_sealed_owned_engine_authority_v4.__code__
)
_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_DEFAULTS_V4 = (
    verify_sealed_owned_engine_authority_v4.__defaults__
)
_FROZEN_SEALED_OWNED_ENGINE_VERIFIER_KWDEFAULTS_V4 = (
    verify_sealed_owned_engine_authority_v4.__kwdefaults__
)


def _require_frozen_sealed_owned_engine_verifier_v4() -> Any:
    verifier = _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_V4
    if (
        globals().get("verify_sealed_owned_engine_authority_v4") is not verifier
        or verifier.__globals__ is not _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_GLOBALS_V4
        or verifier.__code__ is not _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_CODE_V4
        or verifier.__defaults__ is not _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_DEFAULTS_V4
        or verifier.__kwdefaults__
        is not _FROZEN_SEALED_OWNED_ENGINE_VERIFIER_KWDEFAULTS_V4
        or verifier.__defaults__ is not None
        or verifier.__kwdefaults__ is not None
    ):
        _fail("sealed owned-engine verifier entry changed")
    return verifier


def _owned_semantic_value_v4(value: Any) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, Enum):
        return {
            "enum_type": f"{type(value).__module__}.{type(value).__qualname__}",
            "value": _owned_semantic_value_v4(value.value),
        }
    if type(value) in {tuple, list}:
        return [_owned_semantic_value_v4(row) for row in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            _fail("owned search semantics require string mapping keys")
        return {
            key: _owned_semantic_value_v4(value[key])
            for key in sorted(value)
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "dataclass_type": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": {
                row.name: _owned_semantic_value_v4(getattr(value, row.name))
                for row in fields(value)
                if not row.name.startswith("_")
            },
        }
    _fail(
        "owned search semantics cannot canonically encode "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def _owned_kernel_method_fingerprints_v4(kernel: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name in ("actions", "step", "is_terminal", "reward_upper_bound"):
        target = getattr(kernel, name, None)
        target = getattr(target, "__func__", target)
        if isinstance(target, (classmethod, staticmethod)):
            target = target.__func__
        code = getattr(target, "__code__", None)
        if not isinstance(code, CodeType):
            _fail(f"owned kernel lacks exact semantic method {name!r}")
        rows.append(
            {
                "method": name,
                "recursive_code_sha256": _normalized_recursive_code_fingerprint_v4(
                    code
                ),
            }
        )
    return rows


@dataclass(frozen=True, slots=True)
class OwnedEngineSearchSemanticsV4:
    """Ground-free exact semantics expected before an owned search binds."""

    _issuer: InitVar[object]
    structural_id: str
    kernel_id: str
    derived_query_id: str
    threshold_profile_id: str
    reward_profile_id: str
    policy_class_id: str
    complete_search_profile_id: str
    semantic_documents_bytes: bytes

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER or type(self.semantic_documents_bytes) is not bytes:
            _fail("owned search semantics are issuer-owned")
        for value, label in (
            (self.structural_id, "owned structural semantics"),
            (self.kernel_id, "owned kernel semantics"),
            (self.derived_query_id, "owned query semantics"),
            (self.threshold_profile_id, "owned threshold semantics"),
            (self.reward_profile_id, "owned reward semantics"),
            (self.policy_class_id, "owned policy class"),
            (self.complete_search_profile_id, "owned search profile"),
        ):
            _cid(value, label)
        documents = loads_canonical_json(self.semantic_documents_bytes)
        expected_keys = {
            "structural",
            "kernel",
            "query",
            "threshold",
            "reward",
            "policy_class",
            "search_profile",
        }
        if type(documents) is not dict or set(documents) != expected_keys:
            _fail("owned search semantic document set changed")
        if canonical_json_bytes(documents) != self.semantic_documents_bytes:
            _fail("owned search semantic documents are not canonical bytes")
        expected_ids = (
            content_id(
                CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_STRUCTURAL_SEMANTICS_DOMAIN,
                documents["structural"],
            ),
            content_id(
                CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_KERNEL_SEMANTICS_DOMAIN,
                documents["kernel"],
            ),
            content_id(
                CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_QUERY_SEMANTICS_DOMAIN,
                documents["query"],
            ),
            content_id(
                CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_THRESHOLD_SEMANTICS_DOMAIN,
                documents["threshold"],
            ),
            content_id(
                CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_REWARD_SEMANTICS_DOMAIN,
                documents["reward"],
            ),
            content_id(
                CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_POLICY_CLASS_DOMAIN,
                documents["policy_class"],
            ),
            content_id(
                CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_PROFILE_DOMAIN,
                documents["search_profile"],
            ),
        )
        if expected_ids != (
            self.structural_id,
            self.kernel_id,
            self.derived_query_id,
            self.threshold_profile_id,
            self.reward_profile_id,
            self.policy_class_id,
            self.complete_search_profile_id,
        ):
            _fail("owned search semantic IDs differ from their exact documents")

    @property
    def semantics_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_SEMANTICS_DOMAIN,
            self._payload(),
        )

    @property
    def transition_semantic_closure_id(self) -> str:
        documents = loads_canonical_json(self.semantic_documents_bytes)
        value = documents["kernel"].get("transition_semantic_closure_id")
        return _cid(value, "owned G2048 transition closure")

    def _payload(self) -> dict[str, Any]:
        documents = loads_canonical_json(self.semantic_documents_bytes)
        return {
            "schema": "acfqp.owned_engine_search_semantics.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_engine_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "structural_id": self.structural_id,
            "kernel_id": self.kernel_id,
            "derived_query_id": self.derived_query_id,
            "threshold_profile_id": self.threshold_profile_id,
            "reward_profile_id": self.reward_profile_id,
            "policy_class_id": self.policy_class_id,
            "complete_search_profile_id": self.complete_search_profile_id,
            "transition_semantic_closure_id": self.transition_semantic_closure_id,
            "semantic_documents": documents,
            "ground_transition_calls": 0,
            "caller_query_label_is_not_semantic_authority": True,
            "construction_only": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owned_engine_search_semantics_id": self.semantics_id}


def derive_owned_engine_search_semantics_v4(
    kernel: Any,
    query: Any,
) -> OwnedEngineSearchSemanticsV4:
    """Derive exact identities from runtime kernel/query without stepping."""

    transition_semantic_closure_id = (
        _require_canonical_g2048_transition_closure_v4(kernel)
    )
    kernel_type_name = f"{type(kernel).__module__}.{type(kernel).__qualname__}"
    kernel_config = _owned_semantic_value_v4(kernel)
    structural_key_function = getattr(kernel, "structural_key", None)
    structural_key = (
        None
        if structural_key_function is None
        else _owned_semantic_value_v4(structural_key_function())
    )
    public_structure = {
        name: _owned_semantic_value_v4(getattr(kernel, name))
        for name in (
            "rank_cap",
            "horizon",
            "spawn_distribution",
            "registered_reward_features",
            "registered_goals",
            "cell_count",
        )
        if hasattr(kernel, name)
    }
    structural = {
        "schema": "acfqp.owned_engine_structural_semantics.v4",
        "kernel_type": kernel_type_name,
        "kernel_config": kernel_config,
        "structural_key": structural_key,
        "public_structure": public_structure,
        "transition_semantic_closure_id": transition_semantic_closure_id,
    }
    structural_id = content_id(
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_STRUCTURAL_SEMANTICS_DOMAIN,
        structural,
    )
    kernel_document = {
        "schema": "acfqp.owned_engine_kernel_semantics.v4",
        "structural_id": structural_id,
        "kernel_type": kernel_type_name,
        "semantic_method_fingerprints": _owned_kernel_method_fingerprints_v4(kernel),
        "transition_semantic_closure_id": transition_semantic_closure_id,
    }
    kernel_id = content_id(
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_KERNEL_SEMANTICS_DOMAIN,
        kernel_document,
    )
    initial_rows = [
        {
            "probability": _owned_semantic_value_v4(probability),
            "state": _owned_semantic_value_v4(state),
        }
        for probability, state in query.initial_distribution
    ]
    initial_rows.sort(key=canonical_json_bytes)
    threshold = {
        "schema": "acfqp.owned_engine_threshold_semantics.v4",
        "delta": _owned_semantic_value_v4(query.delta),
    }
    threshold_id = content_id(
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_THRESHOLD_SEMANTICS_DOMAIN,
        threshold,
    )
    reward = {
        "schema": "acfqp.owned_engine_reward_semantics.v4",
        "reward_weights": _owned_semantic_value_v4(query.reward_weights),
        "normalizer": _owned_semantic_value_v4(query.normalizer),
        "normalizer_proof_id": query.normalizer_proof_id,
    }
    reward_id = content_id(
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_REWARD_SEMANTICS_DOMAIN,
        reward,
    )
    policy_class = {
        "schema": "acfqp.owned_engine_policy_class.v4",
        "policy_class": "deterministic_finite_horizon_markov",
        "randomized_policy": False,
        "policy_mixture": False,
    }
    policy_class_id = content_id(
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_POLICY_CLASS_DOMAIN,
        policy_class,
    )
    query_document = {
        "schema": "acfqp.owned_engine_query_semantics.v4",
        "kernel_id": kernel_id,
        "initial_distribution": initial_rows,
        "horizon": query.horizon,
        "goal": query.goal,
        "threshold_profile_id": threshold_id,
        "reward_profile_id": reward_id,
    }
    derived_query_id = content_id(
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_QUERY_SEMANTICS_DOMAIN,
        query_document,
    )
    search_profile = {
        "schema": "acfqp.owned_engine_search_profile.v4",
        "algorithm": "complete_finite_horizon_deterministic_markov_pareto_dp",
        "query_id": derived_query_id,
        "policy_class_id": policy_class_id,
        "horizon": query.horizon,
        "exact_rational": True,
        "ground_transition_calls_derived_at_execution": True,
    }
    search_profile_id = content_id(
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_PROFILE_DOMAIN,
        search_profile,
    )
    documents = {
        "structural": structural,
        "kernel": kernel_document,
        "query": query_document,
        "threshold": threshold,
        "reward": reward,
        "policy_class": policy_class,
        "search_profile": search_profile,
    }
    return OwnedEngineSearchSemanticsV4(
        _ISSUER,
        structural_id,
        kernel_id,
        derived_query_id,
        threshold_id,
        reward_id,
        policy_class_id,
        search_profile_id,
        canonical_json_bytes(documents),
    )


_FROZEN_SEARCH_SEMANTICS_DERIVER_V4 = derive_owned_engine_search_semantics_v4
_FROZEN_SEARCH_SEMANTICS_DERIVER_GLOBALS_V4 = (
    derive_owned_engine_search_semantics_v4.__globals__
)
_FROZEN_SEARCH_SEMANTICS_DERIVER_CODE_V4 = (
    derive_owned_engine_search_semantics_v4.__code__
)
_FROZEN_SEARCH_SEMANTICS_DERIVER_DEFAULTS_V4 = (
    derive_owned_engine_search_semantics_v4.__defaults__
)
_FROZEN_SEARCH_SEMANTICS_DERIVER_KWDEFAULTS_V4 = (
    derive_owned_engine_search_semantics_v4.__kwdefaults__
)
_SEARCH_SEMANTICS_HELPER_NAMES_V4 = (
    "_owned_semantic_value_v4",
    "_owned_kernel_method_fingerprints_v4",
    "_require_canonical_g2048_transition_closure_v4",
    "_verify_canonical_g2048_transition_closure_v4",
    "_callable_import_state_matches_v4",
    "_same_frozen_runtime_value_v4",
    "_normalized_recursive_code_fingerprint_v4",
    "_normalized_code_structure_v4",
    "_normalized_code_component_v4",
    "_sha256",
    "content_id",
    "canonical_json_bytes",
    "loads_canonical_json",
    "fields",
    "is_dataclass",
)
_FROZEN_SEARCH_SEMANTICS_HELPERS_V4 = tuple(
    (
        name,
        globals()[name],
        (
            _freeze_callable_import_state_v4(globals()[name])
            if getattr(globals()[name], "__code__", None) is not None
            else None
        ),
    )
    for name in _SEARCH_SEMANTICS_HELPER_NAMES_V4
)
_FROZEN_SEARCH_SEMANTICS_VALUES_V4 = (
    ("canonical_g2048_v4", canonical_g2048_v4),
    ("_CANONICAL_G2048_TRANSITION_SEAL_V4", _CANONICAL_G2048_TRANSITION_SEAL_V4),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_STRUCTURAL_SEMANTICS_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_STRUCTURAL_SEMANTICS_DOMAIN,
    ),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_KERNEL_SEMANTICS_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_KERNEL_SEMANTICS_DOMAIN,
    ),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_QUERY_SEMANTICS_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_QUERY_SEMANTICS_DOMAIN,
    ),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_THRESHOLD_SEMANTICS_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_THRESHOLD_SEMANTICS_DOMAIN,
    ),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_REWARD_SEMANTICS_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_REWARD_SEMANTICS_DOMAIN,
    ),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_POLICY_CLASS_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_POLICY_CLASS_DOMAIN,
    ),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_PROFILE_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_PROFILE_DOMAIN,
    ),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_SEMANTICS_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_SEMANTICS_DOMAIN,
    ),
    (
        "CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_G2048_TRANSITION_CLOSURE_DOMAIN",
        CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_G2048_TRANSITION_CLOSURE_DOMAIN,
    ),
)
_FROZEN_SEARCH_SEMANTICS_CLASS_SURFACES_V4 = tuple(
    (
        name,
        vars(OwnedEngineSearchSemanticsV4).get(name),
        tuple(
            _freeze_callable_import_state_v4(target)
            for target in _descriptor_callables_v4(
                vars(OwnedEngineSearchSemanticsV4).get(name)
            )
        ),
    )
    for name in (
        "__init__",
        "__post_init__",
        "semantics_id",
        "transition_semantic_closure_id",
        "_payload",
        "to_document",
    )
)


@dataclass(frozen=True, slots=True)
class _SearchSemanticsDependencySealV4:
    root_states: tuple[_CallableImportStateV4, ...]
    module_bindings: tuple[
        tuple[str, Mapping[str, Any], str, Any, _CallableImportStateV4 | None], ...
    ]
    module_attribute_bindings: tuple[
        tuple[ModuleType, str, Any, _CallableImportStateV4 | None], ...
    ]
    builtin_bindings: tuple[
        tuple[str, Any, _CallableImportStateV4 | None], ...
    ]
    exact_module_resolutions: tuple[_ExactModuleResolutionStateV4, ...]


def _build_search_semantics_dependency_seal_v4(
) -> _SearchSemanticsDependencySealV4:
    roots = [
        _freeze_callable_import_state_v4(_FROZEN_SEARCH_SEMANTICS_DERIVER_V4),
        *(
            state
            for _name, _target, state in _FROZEN_SEARCH_SEMANTICS_HELPERS_V4
            if state is not None
        ),
        *(
            state
            for _name, _descriptor, states in (
                _FROZEN_SEARCH_SEMANTICS_CLASS_SURFACES_V4
            )
            for state in states
        ),
        _freeze_callable_import_state_v4(
            _require_frozen_search_semantics_deriver_v4
        ),
    ]
    pending = list(roots)
    module_records: dict[
        tuple[int, str],
        tuple[str, Mapping[str, Any], str, Any, _CallableImportStateV4 | None],
    ] = {}
    module_attribute_records: dict[
        tuple[int, str],
        tuple[ModuleType, str, Any, _CallableImportStateV4 | None],
    ] = {}
    builtin_names: set[str] = set()
    visited: set[int] = set()
    while pending:
        state = pending.pop()
        if id(state.target) in visited:
            continue
        visited.add(id(state.target))
        if not isinstance(state.code, CodeType) or not isinstance(
            state.globals_object, Mapping
        ):
            continue
        owner_globals = state.globals_object
        owner_module = str(owner_globals.get("__name__", "<unknown>"))
        retained_values = (
            *state.default_values,
            *(value for _name, value in state.kwdefault_values),
            *state.closure_values,
        )
        for retained in retained_values:
            for dependency in _nested_callable_and_class_dependencies_v4(
                retained
            ):
                if getattr(dependency, "__code__", None) is not None:
                    pending.append(_freeze_callable_import_state_v4(dependency))
        for nested in _walk_code_objects_v4(state.code):
            for module, attribute_name, target in _module_attributes_in_code_v4(
                nested,
                owner_globals,
            ):
                callable_state = (
                    _freeze_callable_import_state_v4(target)
                    if getattr(target, "__code__", None) is not None
                    else None
                )
                module_attribute_records[(id(module), attribute_name)] = (
                    module,
                    attribute_name,
                    target,
                    callable_state,
                )
                if callable_state is not None:
                    pending.append(callable_state)
            for name in _global_names_in_code_v4(nested):
                if name in owner_globals:
                    target = owner_globals[name]
                    callable_state = (
                        _freeze_callable_import_state_v4(target)
                        if getattr(target, "__code__", None) is not None
                        else None
                    )
                    module_records[(id(owner_globals), name)] = (
                        owner_module,
                        owner_globals,
                        name,
                        target,
                        callable_state,
                    )
                    if callable_state is not None:
                        pending.append(callable_state)
                elif hasattr(builtins, name):
                    builtin_names.add(name)
    module_bindings = tuple(
        sorted(
            module_records.values(),
            key=lambda row: (
                row[0],
                row[2],
                type(row[3]).__module__,
                type(row[3]).__qualname__,
            ),
        )
    )
    module_attribute_bindings = tuple(
        sorted(
            module_attribute_records.values(),
            key=lambda row: (row[0].__name__, row[1]),
        )
    )
    builtin_bindings = tuple(
        (
            name,
            getattr(builtins, name),
            (
                _freeze_callable_import_state_v4(getattr(builtins, name))
                if getattr(getattr(builtins, name), "__code__", None) is not None
                else None
            ),
        )
        for name in sorted(builtin_names)
    )
    resolution_modules: dict[int, ModuleType] = {}
    for dependency_module, _name, _target, _state in module_attribute_bindings:
        resolution_modules[id(dependency_module)] = dependency_module
    for owner_module, owner_globals, _name, _target, _state in module_bindings:
        candidate_module = sys.modules.get(owner_module)
        if (
            isinstance(candidate_module, ModuleType)
            and candidate_module.__dict__ is owner_globals
        ):
            resolution_modules[id(candidate_module)] = candidate_module
    exact_module_resolutions = tuple(
        _freeze_exact_module_resolution_v4(dependency_module)
        for dependency_module in sorted(
            resolution_modules.values(), key=lambda row: row.__name__
        )
    )
    return _SearchSemanticsDependencySealV4(
        tuple(roots),
        module_bindings,
        module_attribute_bindings,
        builtin_bindings,
        exact_module_resolutions,
    )


def _require_frozen_search_semantics_deriver_v4() -> Any:
    deriver = _FROZEN_SEARCH_SEMANTICS_DERIVER_V4
    if (
        globals().get("derive_owned_engine_search_semantics_v4") is not deriver
        or deriver.__globals__ is not _FROZEN_SEARCH_SEMANTICS_DERIVER_GLOBALS_V4
        or deriver.__code__ is not _FROZEN_SEARCH_SEMANTICS_DERIVER_CODE_V4
        or deriver.__defaults__ is not _FROZEN_SEARCH_SEMANTICS_DERIVER_DEFAULTS_V4
        or deriver.__kwdefaults__
        is not _FROZEN_SEARCH_SEMANTICS_DERIVER_KWDEFAULTS_V4
        or deriver.__defaults__ is not None
        or deriver.__kwdefaults__ is not None
    ):
        _fail("owned search-semantics deriver changed")
    for name, target, state in _FROZEN_SEARCH_SEMANTICS_HELPERS_V4:
        if globals().get(name) is not target or (
            state is not None and not _callable_import_state_matches_v4(state)
        ):
            _fail(f"owned search-semantics helper {name!r} changed")
    for name, target in _FROZEN_SEARCH_SEMANTICS_VALUES_V4:
        current = globals().get(name)
        if not _same_frozen_runtime_value_v4(current, target):
            _fail(f"owned search-semantics value {name!r} changed")
    for name, descriptor, states in _FROZEN_SEARCH_SEMANTICS_CLASS_SURFACES_V4:
        if vars(OwnedEngineSearchSemanticsV4).get(name) is not descriptor or any(
            not _callable_import_state_matches_v4(state) for state in states
        ):
            _fail(f"owned search-semantics class surface {name!r} changed")
    seal = _SEARCH_SEMANTICS_DEPENDENCY_SEAL_V4
    if seal is not _FROZEN_SEARCH_SEMANTICS_DEPENDENCY_SEAL_V4:
        _fail("owned search-semantics dependency seal changed")
    if any(
        not _callable_import_state_matches_v4(state)
        for state in seal.root_states
    ):
        _fail("owned search-semantics root callable state changed")
    for owner_module, owner_globals, name, target, state in seal.module_bindings:
        if (
            owner_globals.get("__name__") != owner_module
            or owner_globals.get(name) is not target
            or (
                state is not None
                and not _callable_import_state_matches_v4(state)
            )
        ):
            _fail(
                "owned search-semantics recursive dependency "
                f"{owner_module}.{name} changed"
            )
    for module, name, target, state in seal.module_attribute_bindings:
        if getattr(module, name, None) is not target or (
            state is not None and not _callable_import_state_matches_v4(state)
        ):
            _fail(
                "owned search-semantics module attribute dependency "
                f"{module.__name__}.{name} changed"
            )
    for name, target, state in seal.builtin_bindings:
        if getattr(builtins, name, None) is not target or (
            state is not None and not _callable_import_state_matches_v4(state)
        ):
            _fail(f"owned search-semantics builtin {name!r} changed")
    for state in seal.exact_module_resolutions:
        if not _exact_module_resolution_matches_v4(state):
            _fail(
                "owned search-semantics module resolution changed: "
                f"{state.module.__name__}"
            )
    return deriver


_SEARCH_SEMANTICS_DEPENDENCY_SEAL_V4 = (
    _build_search_semantics_dependency_seal_v4()
)
_FROZEN_SEARCH_SEMANTICS_DEPENDENCY_SEAL_V4 = (
    _SEARCH_SEMANTICS_DEPENDENCY_SEAL_V4
)


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentStartV4:
    _issuer: InitVar[object]
    route_segment_id: str
    occurrence_id: str
    route_attempt_id: str
    recorder_id: str
    manifest_authority_id: str
    owner_integration_blocker_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "START", self)
        for value, label in (
            (self.route_segment_id, "route segment"),
            (self.occurrence_id, "occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.manifest_authority_id, "manifest authority"),
            (self.owner_integration_blocker_id, "owner integration blocker"),
        ):
            _cid(value, label)
        if type(self.recorder_id) is not str or not self.recorder_id:
            _fail("recorder ID must be nonempty")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_start.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_id": self.route_segment_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "recorder_id": self.recorder_id,
            "manifest_authority_id": self.manifest_authority_id,
            "owner_integration_blocker_id": self.owner_integration_blocker_id,
            "construction_only": True,
            "production_owner_source_integrated": False,
        }

    @property
    def start_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_START_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_start_id": self.start_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteOperationEventV4:
    _issuer: InitVar[object]
    route_segment_start_id: str
    boundary_id: str
    dispatch_key: str
    path: str
    operation_source_symbol: str
    origin: RouteOperationOriginV4
    amount: int
    event_sequence: int
    predecessor_chain_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "EVENT", self)
        _cid(self.route_segment_start_id, "route segment start")
        _cid(self.boundary_id, "operation boundary")
        _cid(self.predecessor_chain_id, "predecessor chain")
        try:
            object.__setattr__(self, "origin", RouteOperationOriginV4(self.origin))
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRouteSegmentV4Error(
                "route operation origin is invalid"
            ) from error
        if (
            type(self.dispatch_key) is not str
            or not self.dispatch_key
            or type(self.path) is not str
            or not self.path
            or type(self.operation_source_symbol) is not str
            or not self.operation_source_symbol
            or type(self.amount) is not int
            or self.amount != 1
            or type(self.event_sequence) is not int
            or self.event_sequence <= 0
        ):
            _fail("route operation event is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_operation_event.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_start_id": self.route_segment_start_id,
            "boundary_id": self.boundary_id,
            "dispatch_key": self.dispatch_key,
            "path": self.path,
            "operation_source_symbol": self.operation_source_symbol,
            "origin": self.origin.value,
            "source_owned_runtime_event": (
                self.origin is RouteOperationOriginV4.SOURCE_OWNED_RUNTIME
            ),
            "reducer": ReducerEnum.SUM.value,
            "amount": self.amount,
            "event_sequence": self.event_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "construction_only": True,
        }

    @property
    def event_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_EVENT_DOMAIN,
            self._payload(),
        )

    @property
    def chain_id(self) -> str:
        return self.event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operation_event_id": self.event_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentTerminalV4:
    _issuer: InitVar[object]
    route_segment_start_id: str
    terminal_kind: RouteSegmentTerminalKindV4
    event_ids: tuple[str, ...]
    predecessor_chain_id: str
    abort_reason: str | None

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "TERMINAL", self)
        _cid(self.route_segment_start_id, "route segment start")
        _cid(self.predecessor_chain_id, "predecessor chain")
        try:
            object.__setattr__(
                self, "terminal_kind", RouteSegmentTerminalKindV4(self.terminal_kind)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRouteSegmentV4Error(
                "route terminal kind is invalid"
            ) from error
        if type(self.event_ids) is not tuple or len(set(self.event_ids)) != len(
            self.event_ids
        ):
            _fail("route terminal changed event coverage")
        for event_id in self.event_ids:
            _cid(event_id, "operation event")
        if self.terminal_kind is RouteSegmentTerminalKindV4.COMPLETED:
            if self.abort_reason is not None:
                _fail("completed route segment cannot carry an abort reason")
        elif type(self.abort_reason) is not str or not self.abort_reason:
            _fail("aborted route segment requires a reason")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_terminal.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_start_id": self.route_segment_start_id,
            "terminal_kind": self.terminal_kind.value,
            "event_count": len(self.event_ids),
            "event_ids": list(self.event_ids),
            "predecessor_chain_id": self.predecessor_chain_id,
            "abort_reason": self.abort_reason,
            "positive_prefix_retained": True,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "production_closure_claimed": False,
        }

    @property
    def terminal_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TERMINAL_DOMAIN,
            self._payload(),
        )

    @property
    def chain_id(self) -> str:
        return self.terminal_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_terminal_id": self.terminal_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentTranscriptV4:
    _issuer: InitVar[object]
    start: OwnedRouteSegmentStartV4
    events: tuple[OwnedRouteOperationEventV4, ...]
    terminal: OwnedRouteSegmentTerminalV4

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "TRANSCRIPT", self)
        if (
            type(self.start) is not OwnedRouteSegmentStartV4
            or type(self.events) is not tuple
            or type(self.terminal) is not OwnedRouteSegmentTerminalV4
        ):
            _fail("route transcript uses foreign objects")
        predecessor = self.start.start_id
        for sequence, event in enumerate(self.events, start=1):
            if (
                type(event) is not OwnedRouteOperationEventV4
                or event.route_segment_start_id != self.start.start_id
                or event.event_sequence != sequence
                or event.predecessor_chain_id != predecessor
            ):
                _fail("route transcript event chain is discontinuous")
            predecessor = event.chain_id
        if (
            self.terminal.route_segment_start_id != self.start.start_id
            or self.terminal.predecessor_chain_id != predecessor
            or self.terminal.event_ids != tuple(row.event_id for row in self.events)
        ):
            _fail("route transcript terminal changed its positive prefix")

    @property
    def values(self) -> Mapping[str, int]:
        values: dict[str, int] = {}
        for event in self.events:
            values[event.path] = values.get(event.path, 0) + event.amount
        return MappingProxyType(values)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_transcript.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "start": self.start.to_document(),
            "events": [row.to_document() for row in self.events],
            "terminal": self.terminal.to_document(),
            "event_count": len(self.events),
            "positive_prefix_retained": True,
            "absent_event_is_zero": False,
            "event_origins": sorted({row.origin.value for row in self.events}),
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "production_owner_source_integrated": False,
            "production_closure_claimed": False,
        }

    @property
    def transcript_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TRANSCRIPT_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_transcript_id": self.transcript_id}


class OwnedFallbackRouteSegmentSessionV4:
    """Sealed-byte session; current production owner runtime remains blocked."""

    def __init__(
        self,
        *,
        route_segment_id: str,
        occurrence_id: str,
        route_attempt_id: str,
        recorder_id: str,
        source_member_bytes: bytes,
        boundary_manifest_document_bytes: bytes,
        manifest_authority: VerifiedOperationBoundaryManifestAuthorityV4,
    ) -> None:
        replayed = verify_sealed_operation_boundary_authority_v4(
            source_member_bytes,
            boundary_manifest_document_bytes,
        )
        if (
            type(manifest_authority)
            is not VerifiedOperationBoundaryManifestAuthorityV4
            or canonical_json_bytes(manifest_authority.to_document())
            != canonical_json_bytes(replayed.to_document())
        ):
            _fail("route segment requires the exact replayed sealed authority")
        self._lock = threading.RLock()
        self._owner_thread_id = threading.get_ident()
        self._authority = replayed
        self._by_dispatch = replayed.by_dispatch
        self._start = OwnedRouteSegmentStartV4(
            _ISSUER,
            _cid(route_segment_id, "route segment"),
            _cid(occurrence_id, "occurrence"),
            _cid(route_attempt_id, "route attempt"),
            recorder_id,
            replayed.manifest_authority_id,
            replayed.owner_integration_blocker.blocker_id,
        )
        self._events: list[OwnedRouteOperationEventV4] = []
        self._mode: _SessionModeV4 | None = None
        self._terminal: OwnedRouteSegmentTerminalV4 | None = None
        self._finished_values: Mapping[str, int] | None = None

    @property
    def authority(self) -> VerifiedOperationBoundaryManifestAuthorityV4:
        return self._authority

    @property
    def start(self) -> OwnedRouteSegmentStartV4:
        return self._start

    @property
    def is_terminal(self) -> bool:
        return self._terminal is not None

    @property
    def owner_integration_blocker(self) -> OwnerRuntimeIntegrationBlockerV4:
        return self._authority.owner_integration_blocker

    @property
    def transcript(self) -> OwnedRouteSegmentTranscriptV4:
        if self._terminal is None:
            _fail("V4 transcript is unavailable before terminalization")
        return OwnedRouteSegmentTranscriptV4(
            _ISSUER, self._start, tuple(self._events), self._terminal
        )

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            self._abort("CROSS_THREAD_ACTIVE_SCOPE")
            _fail("V4 route segment crossed its owner thread")

    def _predecessor(self) -> str:
        return self._events[-1].chain_id if self._events else self._start.start_id

    def enter_construction_harness(self) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or self._mode is not None:
                _fail("V4 construction harness entered in an invalid state")
            self._mode = _SessionModeV4.CONSTRUCTION

    def enter_owned_runtime(self) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or self._mode is not None:
                _fail("V4 owned runtime entered in an invalid state")
            if not self._authority.runtime_gateway_compatible:
                raise OwnerRuntimeIntegrationBlockedV4(
                    self._authority.owner_integration_blocker
                )
            self._mode = _SessionModeV4.OWNED_RUNTIME

    def _record(
        self,
        dispatch_key: Any,
        amount: Any,
        *,
        origin: RouteOperationOriginV4,
        caller_module: str | None = None,
        caller_qualname: str | None = None,
    ) -> object:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or self._mode is None:
                self._abort("EVENT_OUTSIDE_ACTIVE_STAGE")
                _fail("V4 operation lies outside its active stage")
            if type(dispatch_key) is not str or type(amount) is not int or amount != 1:
                self._abort("MALFORMED_OPERATION")
                _fail("V4 operation must be one literal unit primitive")
            boundary = self._by_dispatch.get(dispatch_key)
            if boundary is None:
                self._abort("UNKNOWN_DISPATCH")
                _fail("V4 dispatch is absent from the verified seven-site manifest")
            if origin is RouteOperationOriginV4.CONSTRUCTION_VERIFIED_SOURCE_REPLAY:
                if self._mode is not _SessionModeV4.CONSTRUCTION:
                    self._abort("CONSTRUCTION_ORIGIN_OUTSIDE_HARNESS")
                    _fail("construction replay event crossed into owned runtime")
            else:
                if self._mode is not _SessionModeV4.OWNED_RUNTIME:
                    self._abort("RUNTIME_ORIGIN_OUTSIDE_OWNER")
                    _fail("source-owned event crossed into construction replay")
                if (
                    caller_module != boundary.operation_source_module
                    or caller_qualname != boundary.operation_source_symbol
                ):
                    self._abort("OWNER_MISMATCH")
                    _fail("V4 source-owned caller differs from its sealed boundary")
            self._events.append(
                OwnedRouteOperationEventV4(
                    _ISSUER,
                    self._start.start_id,
                    boundary.boundary_id,
                    boundary.dispatch_key,
                    boundary.target_path,
                    boundary.operation_source_symbol,
                    origin,
                    1,
                    len(self._events) + 1,
                    self._predecessor(),
                )
            )
            return OWNED_ROUTE_EVENT_ACK_V4

    def finish_construction_harness(
        self, exact_ledger_values: Mapping[str, int]
    ) -> None:
        with self._lock:
            self._check_thread()
            if (
                self._terminal is not None
                or self._mode is not _SessionModeV4.CONSTRUCTION
                or self._finished_values is not None
                or not isinstance(exact_ledger_values, Mapping)
                or set(exact_ledger_values) != _EXPECTED_PATHS
                or any(
                    type(value) is not int or value < 0
                    for value in exact_ledger_values.values()
                )
            ):
                self._abort("INVALID_CONSTRUCTION_FINISH")
                _fail("V4 construction finish lacks the exact seven ledger values")
            positive = {
                path: value for path, value in exact_ledger_values.items() if value > 0
            }
            if (
                dict(self._current_values()) != positive
                or len(self._events) != sum(positive.values())
            ):
                self._abort("LEDGER_TRANSCRIPT_DIVERGENCE")
                _fail("V4 exact ledger values diverge from the positive prefix")
            self._finished_values = MappingProxyType(dict(exact_ledger_values))

    def _current_values(self) -> Mapping[str, int]:
        values: dict[str, int] = {}
        for event in self._events:
            values[event.path] = values.get(event.path, 0) + event.amount
        return MappingProxyType(values)

    def complete(self) -> OwnedRouteSegmentTranscriptV4:
        with self._lock:
            self._check_thread()
            if (
                self._terminal is not None
                or self._mode is not _SessionModeV4.CONSTRUCTION
                or self._finished_values is None
                or dict(self._current_values())
                != {
                    path: value
                    for path, value in self._finished_values.items()
                    if value > 0
                }
            ):
                self._abort("UNVERIFIED_CONSTRUCTION_COMPLETION")
                _fail("V4 segment lacks an exact finished construction replay")
            self._mode = None
            event_ids = tuple(row.event_id for row in self._events)
            self._terminal = OwnedRouteSegmentTerminalV4(
                _ISSUER,
                self._start.start_id,
                RouteSegmentTerminalKindV4.COMPLETED,
                event_ids,
                self._predecessor(),
                None,
            )
            return self.transcript

    def _abort(self, reason: str) -> None:
        with self._lock:
            if self._terminal is not None:
                return
            self._mode = None
            event_ids = tuple(row.event_id for row in self._events)
            self._terminal = OwnedRouteSegmentTerminalV4(
                _ISSUER,
                self._start.start_id,
                RouteSegmentTerminalKindV4.ABORTED,
                event_ids,
                self._predecessor(),
                reason,
            )

    def abort(
        self, reason: str = "CALLER_REQUESTED_ABORT"
    ) -> OwnedRouteSegmentTranscriptV4:
        self._check_thread()
        if type(reason) is not str or not reason:
            _fail("abort reason must be nonempty")
        self._abort(reason)
        return self.transcript


def _mint_owned_route_node_v4(node: Any) -> Any:
    return bind_runtime_authority_v1(
        node,
        issuer=_OWNED_NODE_MINT_ISSUER_V4,
    )


def _require_owned_route_node_v4(node: Any) -> None:
    try:
        require_runtime_authority_v1(
            node,
            issuer=_OWNED_NODE_MINT_ISSUER_V4,
        )
    except ValueError as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "owned-engine node lacks its retained owner mint"
        ) from error


@dataclass(frozen=True, slots=True)
class OwnedEngineRouteSegmentStartV4:
    """Start node for the separate Contract 2.0.54 source-owned engine."""

    _issuer: InitVar[object]
    route_segment_id: str
    occurrence_id: str
    route_attempt_id: str
    recorder_id: str
    owned_engine_authority_id: str
    counter_registry_id: str
    stage_profile_id: str
    route_decision_context_id: str
    decision_point_id: str
    route_decision_id: str
    selected_upper_id: str
    query_id: str
    ground_fallback_cap_profile_id: str
    search_counter_registry_id: str
    search_semantics: OwnedEngineSearchSemanticsV4
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "OWNED_START", self)
        for value, label in (
            (self.route_segment_id, "owned route segment"),
            (self.occurrence_id, "owned occurrence"),
            (self.route_attempt_id, "owned route attempt"),
            (self.owned_engine_authority_id, "owned-engine authority"),
            (self.counter_registry_id, "owned-engine counter registry"),
            (self.stage_profile_id, "owned-engine stage profile"),
            (self.route_decision_context_id, "owned route decision context"),
            (self.decision_point_id, "owned decision point"),
            (self.route_decision_id, "owned route decision"),
            (self.selected_upper_id, "owned selected upper"),
            (self.query_id, "owned query"),
            (self.ground_fallback_cap_profile_id, "owned fallback cap profile"),
            (self.search_counter_registry_id, "owned search counter registry"),
        ):
            _cid(value, label)
        if (
            type(self.recorder_id) is not str
            or not self.recorder_id
            or type(self.search_semantics) is not OwnedEngineSearchSemanticsV4
        ):
            _fail("owned-engine recorder ID must be nonempty")

    def _payload(self) -> dict[str, Any]:
        _require_owned_route_node_v4(self)
        return {
            "schema": "acfqp.owned_engine_route_segment_start.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_engine_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "route_segment_id": self.route_segment_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "recorder_id": self.recorder_id,
            "owned_engine_authority_id": self.owned_engine_authority_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "route_decision_id": self.route_decision_id,
            "selected_upper_id": self.selected_upper_id,
            "query_id": self.query_id,
            "ground_fallback_cap_profile_id": self.ground_fallback_cap_profile_id,
            "search_counter_registry_id": self.search_counter_registry_id,
            "search_semantics": self.search_semantics.to_document(),
            "search_semantics_id": self.search_semantics.semantics_id,
            "transition_semantic_closure_id": (
                self.search_semantics.transition_semantic_closure_id
            ),
            "structural_id": self.search_semantics.structural_id,
            "kernel_id": self.search_semantics.kernel_id,
            "derived_query_id": self.search_semantics.derived_query_id,
            "threshold_profile_id": self.search_semantics.threshold_profile_id,
            "reward_profile_id": self.search_semantics.reward_profile_id,
            "policy_class_id": self.search_semantics.policy_class_id,
            "complete_search_profile_id": (
                self.search_semantics.complete_search_profile_id
            ),
            "stage_kind": registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value,
            "production_owner_source_integrated": True,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
            "construction_only": True,
        }

    @property
    def start_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_START_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owned_engine_route_segment_start_id": self.start_id}


@dataclass(frozen=True, slots=True)
class OwnedEngineRouteOperationEventV4:
    """One unit event issued from an exact bound V3 ledger method."""

    _issuer: InitVar[object]
    route_segment_start_id: str
    boundary_id: str
    dispatch_key: str
    path: str
    operation_source_symbol: str
    amount: int
    event_sequence: int
    predecessor_chain_id: str
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "OWNED_EVENT", self)
        _cid(self.route_segment_start_id, "owned route segment start")
        _cid(self.boundary_id, "owned-engine boundary")
        _cid(self.predecessor_chain_id, "owned event predecessor")
        spec = _OWNED_ENGINE_SPEC_BY_DISPATCH.get(self.dispatch_key)
        if (
            spec is None
            or self.path != spec.target_path
            or self.operation_source_symbol != spec.operation_source_symbol
            or type(self.amount) is not int
            or self.amount != 1
            or type(self.event_sequence) is not int
            or self.event_sequence <= 0
        ):
            _fail("owned-engine operation event is invalid")

    def _payload(self) -> dict[str, Any]:
        _require_owned_route_node_v4(self)
        return {
            "schema": "acfqp.owned_engine_route_operation_event.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_engine_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "route_segment_start_id": self.route_segment_start_id,
            "boundary_id": self.boundary_id,
            "dispatch_key": self.dispatch_key,
            "path": self.path,
            "operation_source_module": OWNED_ENGINE_SOURCE_MODULE,
            "operation_source_symbol": self.operation_source_symbol,
            "origin": RouteOperationOriginV4.SOURCE_OWNED_RUNTIME.value,
            "amount": self.amount,
            "event_sequence": self.event_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "reducer": ReducerEnum.SUM.value,
            "counter_record_issued": False,
            "construction_only": True,
        }

    @property
    def origin(self) -> RouteOperationOriginV4:
        return RouteOperationOriginV4.SOURCE_OWNED_RUNTIME

    @property
    def event_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_EVENT_DOMAIN,
            self._payload(),
        )

    @property
    def chain_id(self) -> str:
        return self.event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owned_engine_operation_event_id": self.event_id}


def _finished_execution_material_v4(
    execution: Any,
    policy_signature_function: Any,
) -> dict[str, Any]:
    result = execution.result
    work = execution.work_vector
    result_document = result.to_dict()
    work_document = work.to_dict()
    result_bytes = canonical_json_bytes(result_document)
    work_bytes = canonical_json_bytes(work_document)
    frontier_bytes = canonical_json_bytes(result_document["frontier"])
    actual_policy_signature = (
        ()
        if execution.selected_policy is None
        else policy_signature_function(execution.selected_policy)
    )
    selected_fields = {
        "selected_policy_object_present": execution.selected_policy is not None,
        "selected_policy_signature": [
            {"remaining": remaining, "state": state, "action": action}
            for remaining, state, action in actual_policy_signature
        ],
        "selected_expected_reward": result.selected_expected_reward,
        "selected_failure_probability": result.selected_failure_probability,
    }
    selected_fields_bytes = canonical_json_bytes(selected_fields)
    return {
        "ground_fallback_result_id": result.ground_fallback_result_id,
        "result_document_sha256": _sha256(result_bytes),
        "result_document_byte_count": len(result_bytes),
        "work_vector_id": work.work_vector_id,
        "work_vector_document_sha256": _sha256(work_bytes),
        "work_vector_document_byte_count": len(work_bytes),
        "work_vector_values": tuple(sorted(work.values.items())),
        "outcome": result.outcome.value,
        "cap_exhausted_name": result.cap_exhausted_name,
        "frontier_sha256": _sha256(frontier_bytes),
        "frontier_byte_count": len(frontier_bytes),
        "frontier_count": len(result.frontier),
        "selected_fields_sha256": _sha256(selected_fields_bytes),
        "selected_fields_byte_count": len(selected_fields_bytes),
        "selected_policy_object_present": execution.selected_policy is not None,
        "selected_policy_signature": actual_policy_signature,
        "selected_expected_reward": result.selected_expected_reward,
        "selected_failure_probability": result.selected_failure_probability,
        "composed_candidate_count": result.composed_candidate_count,
        "trusted_provenance_kind": (
            "NONE_RAW_OWNED_SEARCH"
            if execution.trusted_provenance is None
            else "PRESENT"
        ),
    }


_FROZEN_FINISHED_EXECUTION_MATERIAL_OBJECT_V4 = _finished_execution_material_v4
_FROZEN_FINISHED_EXECUTION_MATERIAL_GLOBALS_V4 = (
    _finished_execution_material_v4.__globals__
)
_FROZEN_FINISHED_EXECUTION_MATERIAL_CODE_V4 = (
    _finished_execution_material_v4.__code__
)
_FROZEN_FINISHED_EXECUTION_MATERIAL_DEFAULTS_V4 = (
    _finished_execution_material_v4.__defaults__
)
_FROZEN_FINISHED_EXECUTION_MATERIAL_KWDEFAULTS_V4 = (
    _finished_execution_material_v4.__kwdefaults__
)
_FROZEN_FINISHED_EXECUTION_CANONICAL_JSON_V4 = canonical_json_bytes
_FROZEN_FINISHED_EXECUTION_SHA256_V4 = _sha256


def _require_frozen_finished_execution_material_v4() -> Any:
    helper = _FROZEN_FINISHED_EXECUTION_MATERIAL_OBJECT_V4
    if (
        globals().get("_finished_execution_material_v4") is not helper
        or helper.__globals__ is not _FROZEN_FINISHED_EXECUTION_MATERIAL_GLOBALS_V4
        or helper.__code__ is not _FROZEN_FINISHED_EXECUTION_MATERIAL_CODE_V4
        or helper.__defaults__ is not _FROZEN_FINISHED_EXECUTION_MATERIAL_DEFAULTS_V4
        or helper.__kwdefaults__
        is not _FROZEN_FINISHED_EXECUTION_MATERIAL_KWDEFAULTS_V4
        or helper.__defaults__ is not None
        or helper.__kwdefaults__ is not None
        or globals().get("canonical_json_bytes")
        is not _FROZEN_FINISHED_EXECUTION_CANONICAL_JSON_V4
        or globals().get("_sha256") is not _FROZEN_FINISHED_EXECUTION_SHA256_V4
    ):
        _fail("finished-execution material helper or dependency changed")
    return helper


@dataclass(frozen=True, slots=True)
class OwnedEngineFinishedExecutionBindingV4:
    """Canonical immutable binding of the exact execution accepted at finish."""

    _issuer: InitVar[object]
    route_segment_start_id: str
    ground_fallback_result_id: str
    result_document_sha256: str
    result_document_byte_count: int
    work_vector_id: str
    work_vector_document_sha256: str
    work_vector_document_byte_count: int
    work_vector_values: tuple[tuple[str, int], ...]
    outcome: str
    cap_exhausted_name: str | None
    frontier_sha256: str
    frontier_byte_count: int
    frontier_count: int
    selected_fields_sha256: str
    selected_fields_byte_count: int
    selected_policy_object_present: bool
    selected_policy_signature: tuple[tuple[int, str, str], ...]
    selected_expected_reward: Any
    selected_failure_probability: Any
    composed_candidate_count: int
    trusted_provenance_kind: str
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "OWNED_EXECUTION_BINDING", self)
        _cid(self.route_segment_start_id, "finished execution route segment start")
        _cid(self.ground_fallback_result_id, "finished ground fallback result")
        _cid(self.work_vector_id, "finished WorkVector")
        for digest, label in (
            (self.result_document_sha256, "finished result document SHA-256"),
            (self.work_vector_document_sha256, "finished WorkVector SHA-256"),
            (self.frontier_sha256, "finished frontier SHA-256"),
            (self.selected_fields_sha256, "finished selected-fields SHA-256"),
        ):
            if (
                type(digest) is not str
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                _fail(f"{label} is invalid")
        for value, label in (
            (self.result_document_byte_count, "finished result byte count"),
            (self.work_vector_document_byte_count, "finished WorkVector byte count"),
            (self.frontier_byte_count, "finished frontier byte count"),
            (self.selected_fields_byte_count, "finished selected-fields byte count"),
        ):
            if type(value) is not int or value <= 0:
                _fail(f"{label} must be positive")
        if (
            type(self.frontier_count) is not int
            or self.frontier_count < 0
            or type(self.composed_candidate_count) is not int
            or self.composed_candidate_count < 0
            or type(self.selected_policy_object_present) is not bool
            or type(self.work_vector_values) is not tuple
            or tuple(sorted(self.work_vector_values)) != self.work_vector_values
            or len({path for path, _value in self.work_vector_values})
            != len(self.work_vector_values)
            or any(
                type(path) is not str
                or not path
                or type(value) is not int
                or value < 0
                for path, value in self.work_vector_values
            )
            or type(self.selected_policy_signature) is not tuple
            or any(
                type(row) is not tuple
                or len(row) != 3
                or type(row[0]) is not int
                or row[0] <= 0
                or type(row[1]) is not str
                or type(row[2]) is not str
                for row in self.selected_policy_signature
            )
            or type(self.outcome) is not str
            or not self.outcome
            or self.trusted_provenance_kind != "NONE_RAW_OWNED_SEARCH"
            or (
                self.cap_exhausted_name is not None
                and (type(self.cap_exhausted_name) is not str or not self.cap_exhausted_name)
            )
        ):
            _fail("finished owned execution binding is invalid")
        if (
            not self.selected_policy_object_present
            and self.selected_policy_signature
        ):
            _fail("finished selected policy presence/signature changed")

    def _payload(self) -> dict[str, Any]:
        _require_owned_route_node_v4(self)
        return {
            "schema": "acfqp.owned_engine_finished_execution_binding.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_engine_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "route_segment_start_id": self.route_segment_start_id,
            "ground_fallback_result_id": self.ground_fallback_result_id,
            "result_document_sha256": self.result_document_sha256,
            "result_document_byte_count": self.result_document_byte_count,
            "work_vector_id": self.work_vector_id,
            "work_vector_document_sha256": self.work_vector_document_sha256,
            "work_vector_document_byte_count": self.work_vector_document_byte_count,
            "work_vector_values": [
                {"path": path, "value": value}
                for path, value in self.work_vector_values
            ],
            "outcome": self.outcome,
            "cap_exhausted_name": self.cap_exhausted_name,
            "frontier_sha256": self.frontier_sha256,
            "frontier_byte_count": self.frontier_byte_count,
            "frontier_count": self.frontier_count,
            "selected_fields_sha256": self.selected_fields_sha256,
            "selected_fields_byte_count": self.selected_fields_byte_count,
            "selected_policy_object_present": self.selected_policy_object_present,
            "selected_policy_signature": [
                {"remaining": remaining, "state": state, "action": action}
                for remaining, state, action in self.selected_policy_signature
            ],
            "selected_expected_reward": self.selected_expected_reward,
            "selected_failure_probability": self.selected_failure_probability,
            "composed_candidate_count": self.composed_candidate_count,
            "trusted_provenance_kind": self.trusted_provenance_kind,
            "exact_result_and_work_bound": True,
            "construction_only": True,
        }

    @property
    def binding_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_EXECUTION_BINDING_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "owned_engine_finished_execution_binding_id": self.binding_id,
        }


def verify_owned_engine_finished_execution_binding_v4(
    binding: OwnedEngineFinishedExecutionBindingV4,
    execution: Any,
) -> OwnedEngineFinishedExecutionBindingV4:
    """Recompute the complete binding without performing ground/planner work."""

    if type(binding) is not OwnedEngineFinishedExecutionBindingV4:
        _fail("finished execution verifier requires its exact binding type")
    _require_owned_route_node_v4(binding)
    from acfqp import phase3e_fallback_owned_v3 as owned_v3

    try:
        validator = owned_v3.require_frozen_owned_fallback_engine_binding_v3
        _require_frozen_owned_engine_import_seal_verifier_v4()(
            validator,
            owned_v3.__dict__,
        )
        engine_binding = owned_v3.require_frozen_owned_fallback_engine_binding_v3()
    except Exception as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "finished execution verifier lost the owned-engine live binding"
        ) from error
    if type(execution) is not owned_v3.GroundFallbackExecutionV1:
        _fail("finished execution verifier received a foreign execution")
    runtime_globals = {
        name: runtime_object
        for name, runtime_object, _code in engine_binding.runtime_global_bindings
    }
    policy_signature_function = runtime_globals.get("_policy_content_signature")
    if not callable(policy_signature_function):
        _fail("finished execution verifier lacks its policy-signature dependency")
    expected = _require_frozen_finished_execution_material_v4()(
        execution,
        policy_signature_function,
    )
    observed = {
        key: getattr(binding, key)
        for key in expected
    }
    if observed != expected:
        _fail("finished execution differs from the transcript binding")
    return binding


@dataclass(frozen=True, slots=True)
class OwnedEngineRouteSegmentTerminalV4:
    _issuer: InitVar[object]
    route_segment_start_id: str
    terminal_kind: RouteSegmentTerminalKindV4
    event_ids: tuple[str, ...]
    predecessor_chain_id: str
    abort_reason: str | None
    exact_search_finished: bool
    finished_execution_binding: OwnedEngineFinishedExecutionBindingV4 | None
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "OWNED_TERMINAL", self)
        _cid(self.route_segment_start_id, "owned route segment start")
        _cid(self.predecessor_chain_id, "owned terminal predecessor")
        try:
            object.__setattr__(
                self, "terminal_kind", RouteSegmentTerminalKindV4(self.terminal_kind)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRouteSegmentV4Error(
                "owned-engine terminal kind is invalid"
            ) from error
        if (
            type(self.event_ids) is not tuple
            or len(set(self.event_ids)) != len(self.event_ids)
            or type(self.exact_search_finished) is not bool
            or (
                self.exact_search_finished
                and type(self.finished_execution_binding)
                is not OwnedEngineFinishedExecutionBindingV4
            )
            or (
                not self.exact_search_finished
                and self.finished_execution_binding is not None
            )
        ):
            _fail("owned-engine terminal changed event/search coverage")
        for event_id in self.event_ids:
            _cid(event_id, "owned operation event")
        if (
            self.finished_execution_binding is not None
            and self.finished_execution_binding.route_segment_start_id
            != self.route_segment_start_id
        ):
            _fail("finished execution binding crossed its route segment")
        if self.terminal_kind is RouteSegmentTerminalKindV4.COMPLETED:
            if self.abort_reason is not None or not self.exact_search_finished:
                _fail("completed owned-engine terminal lacks exact search finish")
        elif type(self.abort_reason) is not str or not self.abort_reason:
            _fail("aborted owned-engine terminal requires a reason")

    def _payload(self) -> dict[str, Any]:
        _require_owned_route_node_v4(self)
        return {
            "schema": "acfqp.owned_engine_route_segment_terminal.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_engine_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "route_segment_start_id": self.route_segment_start_id,
            "terminal_kind": self.terminal_kind.value,
            "event_count": len(self.event_ids),
            "event_ids": list(self.event_ids),
            "predecessor_chain_id": self.predecessor_chain_id,
            "abort_reason": self.abort_reason,
            "exact_search_finished": self.exact_search_finished,
            "finished_execution_binding": (
                None
                if self.finished_execution_binding is None
                else self.finished_execution_binding.to_document()
            ),
            "finished_execution_binding_id": (
                None
                if self.finished_execution_binding is None
                else self.finished_execution_binding.binding_id
            ),
            "positive_prefix_retained": True,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "production_closure_claimed": False,
        }

    @property
    def terminal_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_TERMINAL_DOMAIN,
            self._payload(),
        )

    @property
    def chain_id(self) -> str:
        return self.terminal_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "owned_engine_route_segment_terminal_id": self.terminal_id,
        }


@dataclass(frozen=True, slots=True)
class OwnedEngineRouteSegmentTranscriptV4:
    _issuer: InitVar[object]
    start: OwnedEngineRouteSegmentStartV4
    events: tuple[OwnedEngineRouteOperationEventV4, ...]
    terminal: OwnedEngineRouteSegmentTerminalV4
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "OWNED_TRANSCRIPT", self)
        if (
            type(self.start) is not OwnedEngineRouteSegmentStartV4
            or type(self.events) is not tuple
            or type(self.terminal) is not OwnedEngineRouteSegmentTerminalV4
        ):
            _fail("owned-engine transcript uses foreign objects")
        predecessor = self.start.start_id
        for sequence, event in enumerate(self.events, start=1):
            if (
                type(event) is not OwnedEngineRouteOperationEventV4
                or event.route_segment_start_id != self.start.start_id
                or event.event_sequence != sequence
                or event.predecessor_chain_id != predecessor
            ):
                _fail("owned-engine transcript event chain is discontinuous")
            predecessor = event.chain_id
        if (
            self.terminal.route_segment_start_id != self.start.start_id
            or self.terminal.predecessor_chain_id != predecessor
            or self.terminal.event_ids != tuple(row.event_id for row in self.events)
        ):
            _fail("owned-engine terminal changed its positive prefix")
        if self.terminal.finished_execution_binding is not None:
            _require_owned_route_node_v4(
                self.terminal.finished_execution_binding
            )

    @property
    def values(self) -> Mapping[str, int]:
        _require_owned_route_node_v4(self)
        values: dict[str, int] = {}
        for event in self.events:
            values[event.path] = values.get(event.path, 0) + event.amount
        return MappingProxyType(values)

    def _payload(self) -> dict[str, Any]:
        _require_owned_route_node_v4(self)
        return {
            "schema": "acfqp.owned_engine_route_segment_transcript.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_engine_contract_version": OWNED_ENGINE_CONTRACT_VERSION,
            "start": self.start.to_document(),
            "events": [row.to_document() for row in self.events],
            "terminal": self.terminal.to_document(),
            "finished_execution_binding_id": (
                None
                if self.terminal.finished_execution_binding is None
                else self.terminal.finished_execution_binding.binding_id
            ),
            "event_count": len(self.events),
            "positive_prefix_retained": True,
            "absent_event_is_zero": False,
            "event_origins": [RouteOperationOriginV4.SOURCE_OWNED_RUNTIME.value]
            if self.events
            else [],
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "production_owner_source_integrated": True,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
            "construction_only": True,
            "production_closure_claimed": False,
        }

    @property
    def transcript_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_TRANSCRIPT_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "owned_engine_route_segment_transcript_id": self.transcript_id,
        }


def _same_owned_source_binding_v4(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    scalar_objects = (
        "owner_class",
        "owner_globals",
        "gateway",
        "gateway_globals",
        "gateway_code",
        "event_ack",
        "search_bind",
        "search_bind_globals",
        "search_bind_code",
        "search_finish",
        "search_finish_globals",
        "search_finish_code",
    )
    if any(getattr(left, name) is not getattr(right, name) for name in scalar_objects):
        return False
    if len(left.method_bindings) != len(right.method_bindings):
        return False
    return all(
        left_name == right_name
        and left_function is right_function
        and left_code is right_code
        for (left_name, left_function, left_code), (
            right_name,
            right_function,
            right_code,
        ) in zip(left.method_bindings, right.method_bindings)
    )


def _same_owned_engine_binding_v4(left: Any, right: Any) -> bool:
    if type(left) is not type(right) or not _same_owned_source_binding_v4(
        left.source_binding, right.source_binding
    ):
        return False
    return all(
        getattr(left, name) is getattr(right, name)
        for name in (
            "search_entry",
            "search_entry_globals",
            "search_entry_code",
            "work_vector_helper",
            "work_vector_helper_globals",
            "work_vector_helper_code",
            "source_validator",
            "source_validator_globals",
            "source_validator_code",
            "runtime_global_bindings",
            "runtime_builtin_bindings",
            "runtime_class_surfaces",
            "engine_validator",
        )
    ) and left.live_code_fingerprints == right.live_code_fingerprints


class OwnedEngineFallbackRouteSegmentSessionV4:
    """Exact-once recorder for the sealed ``phase3e_fallback_owned_v3`` engine."""

    def __init__(
        self,
        *,
        route_segment_id: str,
        occurrence_id: str,
        route_attempt_id: str,
        recorder_id: str,
        route_decision_context_id: str,
        decision_point_id: str,
        route_decision_id: str,
        selected_upper_id: str,
        query_id: str,
        ground_fallback_cap_profile_id: str,
        search_counter_registry_id: str,
        expected_search_semantics: OwnedEngineSearchSemanticsV4,
        source_member_bytes: bytes,
        engine_authority: VerifiedOwnedEngineAuthorityV4,
        engine_binding: Any,
    ) -> None:
        replayed = _require_frozen_sealed_owned_engine_verifier_v4()(
            source_member_bytes
        )
        if (
            type(engine_authority) is not VerifiedOwnedEngineAuthorityV4
            or canonical_json_bytes(engine_authority.to_document())
            != canonical_json_bytes(replayed.to_document())
        ):
            _fail("owned-engine session requires its exact replayed authority")
        if type(expected_search_semantics) is not OwnedEngineSearchSemanticsV4:
            _fail("owned-engine session requires exact expected search semantics")
        _require_frozen_search_semantics_deriver_v4()
        live_transition_closure_id = (
            _verify_canonical_g2048_transition_closure_v4()
        )
        expected_semantic_documents = loads_canonical_json(
            expected_search_semantics.semantic_documents_bytes
        )
        if (
            expected_semantic_documents["kernel"].get(
                "transition_semantic_closure_id"
            )
            != live_transition_closure_id
            or expected_semantic_documents["structural"].get(
                "transition_semantic_closure_id"
            )
            != live_transition_closure_id
        ):
            _fail("owned-engine start lost the live G2048 transition closure")
        from acfqp import phase3e_fallback_owned_v3 as owned_v3

        validator = getattr(
            owned_v3, "require_frozen_owned_fallback_engine_binding_v3", None
        )
        if not callable(validator):
            _fail("owned-engine live-binding validator is unavailable")
        try:
            _require_frozen_owned_engine_import_seal_verifier_v4()(
                validator,
                owned_v3.__dict__,
            )
            current_binding = validator()
        except Exception as error:
            raise ConstructionAccountingRouteSegmentV4Error(
                "owned-engine import-time live binding changed"
            ) from error
        live_code_fingerprints = _live_owned_engine_code_fingerprints_v4(
            current_binding
        )
        if (
            type(engine_binding) is not type(current_binding)
            or not _same_owned_engine_binding_v4(engine_binding, current_binding)
            or current_binding.engine_validator is not validator
            or current_binding.search_entry_globals is not owned_v3.__dict__
            or current_binding.source_binding.owner_globals is not owned_v3.__dict__
            or current_binding.live_code_fingerprints
            != live_code_fingerprints
            or live_code_fingerprints != replayed.compiled_code_fingerprints
        ):
            _fail("owned-engine session received a foreign or unsealed live binding")

        methods = {
            name: (function, code)
            for name, function, code in current_binding.source_binding.method_bindings
        }
        owner_bindings: dict[str, tuple[Any, Any]] = {}
        for dispatch_key, boundary in replayed.by_dispatch.items():
            method_name = boundary.operation_source_symbol.rsplit(".", 1)[-1]
            method = methods.get(method_name)
            if method is None:
                _fail("owned-engine authority names an unfrozen ledger method")
            owner_bindings[dispatch_key] = method
        runtime_globals = {
            name: runtime_object
            for name, runtime_object, _code in current_binding.runtime_global_bindings
        }
        policy_signature_function = runtime_globals.get("_policy_content_signature")
        if not callable(policy_signature_function):
            _fail("owned-engine policy-signature dependency is unavailable")

        self._lock = threading.RLock()
        self._owner_thread_id = threading.get_ident()
        self._authority = replayed
        self._by_dispatch = replayed.by_dispatch
        self._engine_module = owned_v3
        self._engine_binding = current_binding
        self._engine_validator = validator
        self._engine_validator_globals = getattr(validator, "__globals__", None)
        self._engine_validator_code = getattr(validator, "__code__", None)
        self._owner_bindings = MappingProxyType(owner_bindings)
        self._policy_signature_function = policy_signature_function
        self._start = _mint_owned_route_node_v4(
            OwnedEngineRouteSegmentStartV4(
                _ISSUER,
                _cid(route_segment_id, "owned route segment"),
                _cid(occurrence_id, "owned occurrence"),
                _cid(route_attempt_id, "owned route attempt"),
                recorder_id,
                replayed.authority_id,
                replayed.counter_registry_id,
                replayed.stage_profile_id,
                _cid(route_decision_context_id, "owned route decision context"),
                _cid(decision_point_id, "owned decision point"),
                _cid(route_decision_id, "owned route decision"),
                _cid(selected_upper_id, "owned selected upper"),
                _cid(query_id, "owned query"),
                _cid(
                    ground_fallback_cap_profile_id,
                    "owned fallback cap profile",
                ),
                _cid(search_counter_registry_id, "owned search counter registry"),
                expected_search_semantics,
            )
        )
        self._events: list[OwnedEngineRouteOperationEventV4] = []
        self._active = False
        self._terminal: OwnedEngineRouteSegmentTerminalV4 | None = None
        self._bound_ledger: Any | None = None
        self._bound_registry: Any | None = None
        self._bound_search_semantics: OwnedEngineSearchSemanticsV4 | None = None
        self._search_frame: Any | None = None
        self._search_finished = False
        self._finished_values: Mapping[str, int] | None = None
        self._finished_composed_candidates: int | None = None
        self._finished_execution: Any | None = None
        self._finished_execution_binding: (
            OwnedEngineFinishedExecutionBindingV4 | None
        ) = None

    @property
    def authority(self) -> VerifiedOwnedEngineAuthorityV4:
        return self._authority

    @property
    def start(self) -> OwnedEngineRouteSegmentStartV4:
        _require_owned_route_node_v4(self._start)
        return self._start

    @property
    def is_terminal(self) -> bool:
        return self._terminal is not None

    @property
    def transcript(self) -> OwnedEngineRouteSegmentTranscriptV4:
        if self._terminal is None:
            _fail("owned-engine transcript is unavailable before terminalization")
        _require_owned_route_node_v4(self._start)
        for event in self._events:
            _require_owned_route_node_v4(event)
        if self._finished_execution_binding is not None:
            _require_owned_route_node_v4(self._finished_execution_binding)
        _require_owned_route_node_v4(self._terminal)
        return _mint_owned_route_node_v4(
            OwnedEngineRouteSegmentTranscriptV4(
                _ISSUER, self._start, tuple(self._events), self._terminal
            )
        )

    @property
    def transcript_values_before_terminal(self) -> Mapping[str, int]:
        values: dict[str, int] = {}
        for event in self._events:
            values[event.path] = values.get(event.path, 0) + event.amount
        return MappingProxyType(values)

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            self._abort("CROSS_THREAD_ACTIVE_SCOPE")
            _fail("owned-engine accounting crossed its owner thread")

    def _predecessor(self) -> str:
        return self._events[-1].chain_id if self._events else self._start.start_id

    @staticmethod
    def _ledger_values(ledger: Any) -> Mapping[str, int]:
        values = {
            "fallback.states_expanded": ledger.states_expanded,
            "fallback.actions_evaluated": ledger.actions_evaluated,
            "fallback.ground_steps": ledger.ground_steps,
            "fallback.outcome_rows": ledger.outcome_rows,
            "fallback.bellman_backups": ledger.bellman_backups,
            "control.cap_checks": ledger.cap_checks,
            "control.cap_rejections": ledger.cap_rejections,
        }
        if (
            any(type(value) is not int or value < 0 for value in values.values())
            or type(ledger.composed_candidates) is not int
            or ledger.composed_candidates < 0
            or ledger.composed_candidates != ledger.bellman_backups
        ):
            _fail("owned-engine ledger values or candidate/backup equality changed")
        return MappingProxyType(values)

    def _require_minted_prefix(self) -> None:
        _require_owned_route_node_v4(self._start)
        for event in self._events:
            _require_owned_route_node_v4(event)
        if self._finished_execution_binding is not None:
            _require_owned_route_node_v4(self._finished_execution_binding)
        if self._terminal is not None:
            _require_owned_route_node_v4(self._terminal)

    def _validate_search_identity_at_bind(self, ledger: Any, search_frame: Any) -> Any:
        local = search_frame.f_locals
        start = self._start
        expected = {
            "route_decision_context_id": start.route_decision_context_id,
            "decision_point_id": start.decision_point_id,
            "route_decision_id": start.route_decision_id,
            "selected_upper_id": start.selected_upper_id,
            "route_attempt_id": start.route_attempt_id,
            "query_id": start.query_id,
            "recorder_id": start.recorder_id,
        }
        if any(local.get(name) != value for name, value in expected.items()):
            self._abort("SEARCH_IDENTITY_MISMATCH")
            _fail("owned-engine search identities differ from its start")
        cap_profile = local.get("cap_profile")
        registry = local.get("trusted_registry")
        try:
            actual_semantics = _require_frozen_search_semantics_deriver_v4()(
                local.get("kernel"),
                local.get("query"),
            )
        except Exception as error:
            self._abort("SEARCH_SEMANTICS_DERIVATION_INVALID")
            raise ConstructionAccountingRouteSegmentV4Error(
                "owned-engine actual search semantics are unavailable"
            ) from error
        if canonical_json_bytes(actual_semantics.to_document()) != canonical_json_bytes(
            start.search_semantics.to_document()
        ):
            self._abort("SEARCH_SEMANTICS_MISMATCH")
            _fail("owned-engine actual kernel/query semantics differ from its start")
        try:
            cap_profile_id = cap_profile.ground_fallback_cap_profile_id
            registry_id = registry.registry_id
        except Exception as error:
            self._abort("SEARCH_PROFILE_BINDING_INVALID")
            raise ConstructionAccountingRouteSegmentV4Error(
                "owned-engine search profiles are unavailable at bind"
            ) from error
        if (
            ledger is not local.get("ledger")
            or ledger.cap is not cap_profile
            or cap_profile_id != start.ground_fallback_cap_profile_id
            or registry_id != start.search_counter_registry_id
            or any(self._ledger_values(ledger).values())
            or ledger.composed_candidates != 0
        ):
            self._abort("SEARCH_PROFILE_BINDING_MISMATCH")
            _fail("owned-engine search cap/registry/zero-ledger binding changed")
        self._bound_search_semantics = actual_semantics
        return registry

    def _validate_finished_execution(self, execution: Any) -> None:
        start = self._start
        ledger = self._bound_ledger
        registry = self._bound_registry
        if ledger is None or registry is None:
            _fail("owned-engine finished execution lacks its bound ledger/registry")
        execution_type = self._engine_module.GroundFallbackExecutionV1
        result_type = self._engine_module.GroundFallbackResultV1
        if type(execution) is not execution_type or type(execution.result) is not result_type:
            _fail("owned-engine finish received a foreign execution/result")
        if execution.trusted_provenance is not None:
            _fail("raw owned-engine search cannot carry trusted provenance")
        result = execution.result
        work = execution.work_vector
        expected_result_ids = (
            (result.route_decision_context_id, start.route_decision_context_id),
            (result.decision_point_id, start.decision_point_id),
            (result.route_decision_id, start.route_decision_id),
            (result.selected_upper_id, start.selected_upper_id),
            (result.route_attempt_id, start.route_attempt_id),
            (result.query_id, start.query_id),
            (
                result.ground_fallback_cap_profile_id,
                start.ground_fallback_cap_profile_id,
            ),
            (result.work_vector_id, work.work_vector_id),
            (work.subject_id, start.route_attempt_id),
            (work.counter_registry_id, start.search_counter_registry_id),
            (registry.registry_id, start.search_counter_registry_id),
            (
                ledger.cap.ground_fallback_cap_profile_id,
                start.ground_fallback_cap_profile_id,
            ),
        )
        if any(actual != expected for actual, expected in expected_result_ids):
            _fail("owned-engine result/work identities differ from its start")
        values = self._ledger_values(ledger)
        work_values = work.values
        if any(work_values.get(path) != value for path, value in values.items()):
            _fail("owned-engine WorkVector differs from its ledger")
        if (
            result.composed_candidate_count != ledger.composed_candidates
            or ledger.composed_candidates != ledger.bellman_backups
        ):
            _fail("owned-engine result candidate count differs from Bellman work")
        is_cap = result.outcome.value == "CAP_EXHAUSTED"
        success = 0 if is_cap else 1
        if (
            work_values.get("route.attempts") != 1
            or work_values.get("route.successes") != success
            or work_values.get("route.failures") != 1 - success
            or work_values.get("solver.attempts") != 1
            or work_values.get("solver.successes") != success
            or work_values.get("solver.failures") != 1 - success
            or (is_cap and ledger.cap_rejections != 1)
            or (not is_cap and ledger.cap_rejections != 0)
        ):
            _fail("owned-engine result outcome differs from route/solver work")

    def _freeze_finished_execution_binding(
        self, execution: Any
    ) -> OwnedEngineFinishedExecutionBindingV4:
        material = _require_frozen_finished_execution_material_v4()(
            execution,
            self._policy_signature_function,
        )
        return _mint_owned_route_node_v4(
            OwnedEngineFinishedExecutionBindingV4(
                _ISSUER,
                self._start.start_id,
                material["ground_fallback_result_id"],
                material["result_document_sha256"],
                material["result_document_byte_count"],
                material["work_vector_id"],
                material["work_vector_document_sha256"],
                material["work_vector_document_byte_count"],
                material["work_vector_values"],
                material["outcome"],
                material["cap_exhausted_name"],
                material["frontier_sha256"],
                material["frontier_byte_count"],
                material["frontier_count"],
                material["selected_fields_sha256"],
                material["selected_fields_byte_count"],
                material["selected_policy_object_present"],
                material["selected_policy_signature"],
                material["selected_expected_reward"],
                material["selected_failure_probability"],
                material["composed_candidate_count"],
                material["trusted_provenance_kind"],
            )
        )

    @staticmethod
    def _frame_descends_from(frame: Any, ancestor: Any) -> bool:
        current = frame
        while current is not None:
            if current is ancestor:
                return True
            current = current.f_back
        return False

    def _revalidate(self) -> None:
        self._require_minted_prefix()
        try:
            _require_frozen_search_semantics_deriver_v4()
            live_transition_closure_id = (
                _verify_canonical_g2048_transition_closure_v4()
            )
            start_semantic_documents = loads_canonical_json(
                self._start.search_semantics.semantic_documents_bytes
            )
            if (
                start_semantic_documents["kernel"].get(
                    "transition_semantic_closure_id"
                )
                != live_transition_closure_id
                or start_semantic_documents["structural"].get(
                    "transition_semantic_closure_id"
                )
                != live_transition_closure_id
            ):
                raise ConstructionAccountingRouteSegmentV4Error(
                    "owned-engine start transition closure changed"
                )
        except Exception:
            self._abort("LIVE_G2048_TRANSITION_CLOSURE_CHANGED")
            _fail("owned-engine live G2048 transition closure changed")
        current_validator = getattr(
            self._engine_module,
            "require_frozen_owned_fallback_engine_binding_v3",
            None,
        )
        if (
            current_validator is not self._engine_validator
            or getattr(current_validator, "__globals__", None)
            is not self._engine_validator_globals
            or getattr(current_validator, "__code__", None)
            is not self._engine_validator_code
        ):
            self._abort("LIVE_ENGINE_VALIDATOR_CHANGED")
            _fail("owned-engine live-binding validator changed")
        try:
            _require_frozen_owned_engine_import_seal_verifier_v4()(
                current_validator,
                self._engine_module.__dict__,
            )
            current = self._engine_validator()
        except Exception:
            self._abort("LIVE_ENGINE_BINDING_CHANGED")
            _fail("owned-engine live binding changed after session creation")
        if not _same_owned_engine_binding_v4(current, self._engine_binding):
            self._abort("LIVE_ENGINE_BINDING_CHANGED")
            _fail("owned-engine live binding changed after session creation")
        current_runtime_globals = {
            name: runtime_object
            for name, runtime_object, _code in current.runtime_global_bindings
        }
        if (
            current_runtime_globals.get("_policy_content_signature")
            is not self._policy_signature_function
        ):
            self._abort("LIVE_POLICY_SIGNATURE_DEPENDENCY_CHANGED")
            _fail("owned-engine policy-signature dependency changed")
        live_code_fingerprints = _live_owned_engine_code_fingerprints_v4(current)
        if (
            current.live_code_fingerprints != live_code_fingerprints
            or live_code_fingerprints != self._authority.compiled_code_fingerprints
        ):
            self._abort("LIVE_ENGINE_CODE_CROSS_BINDING_CHANGED")
            _fail("owned-engine live code differs from its sealed compiled source")

    def enter_owned_runtime(self) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or self._active:
                _fail("owned-engine stage entered in an invalid state")
            self._revalidate()
            self._active = True

    def _bind_search_from_owner(
        self, issuer: object, ledger: Any, search_frame: Any
    ) -> None:
        with self._lock:
            self._check_thread()
            try:
                wrapper_frame = _FROZEN_GETFRAME_V4(1)
            except (AttributeError, ValueError) as error:
                self._abort("SEARCH_BIND_WRAPPER_UNAVAILABLE")
                raise ConstructionAccountingRouteSegmentV4Error(
                    "owned-engine search-bind wrapper is unavailable"
                ) from error
            if (
                issuer is not _OWNED_SEARCH_BIND_ISSUER_V4
                or wrapper_frame.f_globals is not _FROZEN_SEARCH_BIND_GLOBALS_V4
                or wrapper_frame.f_code is not _FROZEN_SEARCH_BIND_CODE_V4
                or globals().get("bind_owned_fallback_search_v4")
                is not _FROZEN_SEARCH_BIND_OBJECT_V4
                or search_frame is not wrapper_frame.f_back
                or self._terminal is not None
                or not self._active
                or self._bound_ledger is not None
                or self._search_frame is not None
                or self._search_finished
            ):
                self._abort("INVALID_SEARCH_BINDING")
                _fail("owned-engine search binding is invalid")
            self._revalidate()
            binding = self._engine_binding
            if (
                type(ledger) is not binding.source_binding.owner_class
                or search_frame.f_globals is not binding.search_entry_globals
                or search_frame.f_code is not binding.search_entry_code
                or search_frame.f_globals.get("run_owned_ground_fallback_search_v3")
                is not binding.search_entry
            ):
                self._abort("FOREIGN_LEDGER_OR_SEARCH")
                _fail("owned-engine binding used a foreign ledger or search")
            registry = self._validate_search_identity_at_bind(ledger, search_frame)
            self._bound_ledger = ledger
            self._bound_registry = registry
            self._search_frame = search_frame

    def _record_from_owner(
        self,
        issuer: object,
        dispatch_key: Any,
        amount: Any,
        *,
        owner_globals: Any,
        owner_code: Any,
        owner_instance: Any,
        owner_frame: Any,
    ) -> object:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or not self._active:
                self._abort("EVENT_OUTSIDE_ACTIVE_STAGE")
                _fail("owned-engine event lies outside its active stage")
            self._revalidate()
            try:
                gateway_frame = _FROZEN_GETFRAME_V4(1)
            except (AttributeError, ValueError) as error:
                self._abort("GATEWAY_FRAME_UNAVAILABLE")
                raise ConstructionAccountingRouteSegmentV4Error(
                    "owned-engine gateway frame is unavailable"
                ) from error
            if (
                issuer is not _OWNED_GATEWAY_ISSUER_V4
                or gateway_frame.f_globals is not _FROZEN_OPERATION_GATEWAY_GLOBALS_V4
                or gateway_frame.f_code is not _FROZEN_OPERATION_GATEWAY_CODE_V4
                or globals().get("emit_owned_route_operation_v4")
                is not _FROZEN_OPERATION_GATEWAY_OBJECT_V4
            ):
                self._abort("UNTRUSTED_GATEWAY_CALLER")
                _fail("owned-engine event bypassed the frozen gateway")
            if (
                self._bound_ledger is None
                or owner_instance is not self._bound_ledger
                or self._search_frame is None
                or not self._frame_descends_from(owner_frame, self._search_frame)
                or self._search_finished
            ):
                self._abort("UNBOUND_LEDGER_OR_SEARCH")
                _fail("owned-engine event is outside its exact bound search")
            if type(dispatch_key) is not str or type(amount) is not int or amount != 1:
                self._abort("MALFORMED_OPERATION")
                _fail("owned-engine event must be one literal unit primitive")
            boundary = self._by_dispatch.get(dispatch_key)
            expected_owner = self._owner_bindings.get(dispatch_key)
            if boundary is None or expected_owner is None:
                self._abort("UNKNOWN_DISPATCH")
                _fail("owned-engine dispatch is absent from its sealed authority")
            expected_function, expected_code = expected_owner
            method_name = boundary.operation_source_symbol.rsplit(".", 1)[-1]
            if (
                owner_globals is not self._engine_binding.source_binding.owner_globals
                or owner_code is not expected_code
                or getattr(self._engine_binding.source_binding.owner_class, method_name, None)
                is not expected_function
            ):
                self._abort("OWNER_MISMATCH")
                _fail("owned-engine dispatch caller differs from its sealed site")
            self._events.append(
                _mint_owned_route_node_v4(OwnedEngineRouteOperationEventV4(
                    _ISSUER,
                    self._start.start_id,
                    boundary.boundary_id,
                    dispatch_key,
                    boundary.target_path,
                    boundary.operation_source_symbol,
                    1,
                    len(self._events) + 1,
                    self._predecessor(),
                ))
            )
            return OWNED_ROUTE_EVENT_ACK_V4

    def _finish_search_from_owner(
        self, issuer: object, ledger: Any, execution: Any, search_frame: Any
    ) -> None:
        with self._lock:
            self._check_thread()
            try:
                wrapper_frame = _FROZEN_GETFRAME_V4(1)
            except (AttributeError, ValueError) as error:
                self._abort("SEARCH_FINISH_WRAPPER_UNAVAILABLE")
                raise ConstructionAccountingRouteSegmentV4Error(
                    "owned-engine search-finish wrapper is unavailable"
                ) from error
            if (
                issuer is not _OWNED_SEARCH_FINISH_ISSUER_V4
                or wrapper_frame.f_globals is not _FROZEN_SEARCH_FINISH_GLOBALS_V4
                or wrapper_frame.f_code is not _FROZEN_SEARCH_FINISH_CODE_V4
                or globals().get("finish_owned_fallback_search_v4")
                is not _FROZEN_SEARCH_FINISH_OBJECT_V4
                or search_frame is not wrapper_frame.f_back
                or self._terminal is not None
                or not self._active
                or ledger is not self._bound_ledger
                or search_frame is not self._search_frame
                or execution is not search_frame.f_locals.get("execution")
                or execution.result is not search_frame.f_locals.get("result")
                or execution.work_vector
                is not search_frame.f_locals.get("work_vector")
                or self._search_finished
            ):
                self._abort("INVALID_SEARCH_FINISH")
                _fail("owned-engine search finish is invalid")
            self._revalidate()
            values = self._ledger_values(ledger)
            positive = {path: value for path, value in values.items() if value > 0}
            if (
                dict(self.transcript_values_before_terminal) != positive
                or len(self._events) != sum(positive.values())
            ):
                self._abort("LEDGER_TRANSCRIPT_DIVERGENCE")
                _fail("owned-engine ledger and event transcript diverged")
            try:
                self._validate_finished_execution(execution)
            except ConstructionAccountingRouteSegmentV4Error:
                self._abort("RESULT_WORK_BINDING_MISMATCH")
                raise
            finished_execution_binding = self._freeze_finished_execution_binding(
                execution
            )
            verify_owned_engine_finished_execution_binding_v4(
                finished_execution_binding,
                execution,
            )
            self._finished_values = values
            self._finished_composed_candidates = ledger.composed_candidates
            self._finished_execution = execution
            self._finished_execution_binding = finished_execution_binding
            self._search_finished = True

    def complete(self) -> OwnedEngineRouteSegmentTranscriptV4:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or not self._active:
                _fail("owned-engine segment cannot complete in its current state")
            self._revalidate()
            if (
                not self._search_finished
                or self._bound_ledger is None
                or self._finished_values is None
                or self._finished_composed_candidates is None
                or self._finished_execution is None
                or self._finished_execution_binding is None
                or self._ledger_values(self._bound_ledger) != self._finished_values
                or self._bound_ledger.composed_candidates
                != self._finished_composed_candidates
                or dict(self.transcript_values_before_terminal)
                != {
                    path: value
                    for path, value in self._finished_values.items()
                    if value > 0
                }
            ):
                self._abort("UNVERIFIED_SEARCH_COMPLETION")
                _fail("owned-engine segment lacks an exact finished search")
            try:
                self._validate_finished_execution(self._finished_execution)
                verify_owned_engine_finished_execution_binding_v4(
                    self._finished_execution_binding,
                    self._finished_execution,
                )
            except ConstructionAccountingRouteSegmentV4Error:
                self._abort("RESULT_WORK_BINDING_MISMATCH")
                raise
            self._active = False
            event_ids = tuple(row.event_id for row in self._events)
            self._terminal = _mint_owned_route_node_v4(
                OwnedEngineRouteSegmentTerminalV4(
                    _ISSUER,
                    self._start.start_id,
                    RouteSegmentTerminalKindV4.COMPLETED,
                    event_ids,
                    self._predecessor(),
                    None,
                    True,
                    self._finished_execution_binding,
                )
            )
            return self.transcript

    def _abort(self, reason: str) -> None:
        with self._lock:
            if self._terminal is not None:
                return
            self._active = False
            if self._bound_ledger is not None:
                try:
                    values = self._ledger_values(self._bound_ledger)
                    positive = {
                        path: value for path, value in values.items() if value > 0
                    }
                    reconciled = (
                        dict(self.transcript_values_before_terminal) == positive
                        and len(self._events) == sum(positive.values())
                    )
                except ConstructionAccountingRouteSegmentV4Error:
                    reconciled = False
                if not reconciled and reason != "LEDGER_TRANSCRIPT_DIVERGENCE":
                    reason = "ABORT_LEDGER_TRANSCRIPT_DIVERGENCE"
            event_ids = tuple(row.event_id for row in self._events)
            self._terminal = _mint_owned_route_node_v4(
                OwnedEngineRouteSegmentTerminalV4(
                    _ISSUER,
                    self._start.start_id,
                    RouteSegmentTerminalKindV4.ABORTED,
                    event_ids,
                    self._predecessor(),
                    reason,
                    self._search_finished,
                    (
                        self._finished_execution_binding
                        if self._search_finished
                        else None
                    ),
                )
            )

    def abort(
        self, reason: str = "CALLER_REQUESTED_ABORT"
    ) -> OwnedEngineRouteSegmentTranscriptV4:
        self._check_thread()
        if type(reason) is not str or not reason:
            _fail("owned-engine abort reason must be nonempty")
        self._abort(reason)
        return self.transcript


_FROZEN_ROUTE_NODE_GLOBALS_V4 = globals()
_FROZEN_ROUTE_NODE_CODES_V4 = MappingProxyType(
    {
        "START": OwnedFallbackRouteSegmentSessionV4.__init__.__code__,
        "EVENT": OwnedFallbackRouteSegmentSessionV4._record.__code__,
        "TERMINAL": (
            OwnedFallbackRouteSegmentSessionV4.complete.__code__,
            OwnedFallbackRouteSegmentSessionV4._abort.__code__,
        ),
        "TRANSCRIPT": OwnedFallbackRouteSegmentSessionV4.transcript.fget.__code__,
        "OWNED_START": OwnedEngineFallbackRouteSegmentSessionV4.__init__.__code__,
        "OWNED_EVENT": OwnedEngineFallbackRouteSegmentSessionV4._record_from_owner.__code__,
        "OWNED_EXECUTION_BINDING": (
            OwnedEngineFallbackRouteSegmentSessionV4._freeze_finished_execution_binding.__code__
        ),
        "OWNED_TERMINAL": (
            OwnedEngineFallbackRouteSegmentSessionV4.complete.__code__,
            OwnedEngineFallbackRouteSegmentSessionV4._abort.__code__,
        ),
        "OWNED_TRANSCRIPT": (
            OwnedEngineFallbackRouteSegmentSessionV4.transcript.fget.__code__
        ),
    }
)


OWNED_ROUTE_EVENT_ACK_V4 = object()
_ACTIVE_ROUTE_SEGMENT_V4: ContextVar[Any | None] = ContextVar(
    "acfqp_owned_fallback_route_runtime_v4", default=None
)


@contextmanager
def activate_construction_route_segment_v4(
    session: OwnedFallbackRouteSegmentSessionV4,
) -> Iterator[OwnedFallbackRouteSegmentSessionV4]:
    if type(session) is not OwnedFallbackRouteSegmentSessionV4:
        _fail("V4 construction activation requires the exact session")
    session._check_thread()
    if _ACTIVE_ROUTE_SEGMENT_V4.get() is not None:
        _fail("nested V4 route segments are forbidden")
    session.enter_construction_harness()
    token: Token[Any] = _ACTIVE_ROUTE_SEGMENT_V4.set(session)
    try:
        yield session
    except BaseException:
        if not session.is_terminal:
            session._abort("ACTIVE_SCOPE_EXCEPTION")
        raise
    else:
        if not session.is_terminal:
            session._abort("INCOMPLETE_SCOPE_EXIT")
            _fail("V4 construction scope exited without terminalization")
    finally:
        _ACTIVE_ROUTE_SEGMENT_V4.reset(token)


@contextmanager
def activate_owned_route_segment_v4(
    session: OwnedFallbackRouteSegmentSessionV4
    | OwnedEngineFallbackRouteSegmentSessionV4,
) -> Iterator[
    OwnedFallbackRouteSegmentSessionV4 | OwnedEngineFallbackRouteSegmentSessionV4
]:
    """Enter either the legacy blocker or the separate sealed owned engine."""

    if type(session) not in (
        OwnedFallbackRouteSegmentSessionV4,
        OwnedEngineFallbackRouteSegmentSessionV4,
    ):
        _fail("V4 owned activation requires the exact session")
    session._check_thread()
    if _ACTIVE_ROUTE_SEGMENT_V4.get() is not None:
        _fail("nested V4 route segments are forbidden")
    session.enter_owned_runtime()
    token: Token[Any] = _ACTIVE_ROUTE_SEGMENT_V4.set(session)
    try:
        yield session
    except BaseException:
        if not session.is_terminal:
            session._abort("ACTIVE_SCOPE_EXCEPTION")
        raise
    else:
        if not session.is_terminal:
            session._abort("INCOMPLETE_SCOPE_EXIT")
            _fail("V4 owned route scope exited without terminalization")
    finally:
        _ACTIVE_ROUTE_SEGMENT_V4.reset(token)


def emit_verified_construction_operation_v4(
    dispatch_key: Any, amount: Any = 1
) -> object:
    session = _ACTIVE_ROUTE_SEGMENT_V4.get()
    if session is None:
        _fail("V4 construction event requires an active harness")
    return session._record(
        dispatch_key,
        amount,
        origin=RouteOperationOriginV4.CONSTRUCTION_VERIFIED_SOURCE_REPLAY,
    )


def emit_owned_route_operation_v4(dispatch_key: Any, amount: Any = 1) -> object:
    """Issue one operation from the exact bound successor-engine method."""

    session = _ACTIVE_ROUTE_SEGMENT_V4.get()
    if session is None:
        _fail("V4 source-owned event requires an active owned runtime")
    try:
        caller = _FROZEN_GETFRAME_V4(1)
    except (AttributeError, ValueError) as error:
        session._abort("CALLER_FRAME_UNAVAILABLE")
        raise ConstructionAccountingRouteSegmentV4Error(
            "V4 source-owner frame is unavailable"
        ) from error
    if type(session) is OwnedEngineFallbackRouteSegmentSessionV4:
        return session._record_from_owner(
            _OWNED_GATEWAY_ISSUER_V4,
            dispatch_key,
            amount,
            owner_globals=caller.f_globals,
            owner_code=caller.f_code,
            owner_instance=caller.f_locals.get("self"),
            owner_frame=caller,
        )
    if type(session) is OwnedFallbackRouteSegmentSessionV4:
        return session._record(
            dispatch_key,
            amount,
            origin=RouteOperationOriginV4.SOURCE_OWNED_RUNTIME,
            caller_module=caller.f_globals.get("__name__"),
            caller_qualname=getattr(caller.f_code, "co_qualname", caller.f_code.co_name),
        )
    _fail("V4 source-owned event found a foreign active session")


def bind_owned_fallback_search_v4(ledger: Any) -> None:
    """Bind exactly one V3 search invocation before any owned operation."""

    session = _ACTIVE_ROUTE_SEGMENT_V4.get()
    if type(session) is not OwnedEngineFallbackRouteSegmentSessionV4:
        _fail("owned-engine search requires its exact active V4 session")
    try:
        search_frame = _FROZEN_GETFRAME_V4(1)
    except (AttributeError, ValueError) as error:
        session._abort("SEARCH_FRAME_UNAVAILABLE")
        raise ConstructionAccountingRouteSegmentV4Error(
            "owned-engine search frame is unavailable"
        ) from error
    session._bind_search_from_owner(
        _OWNED_SEARCH_BIND_ISSUER_V4,
        ledger,
        search_frame,
    )


def finish_owned_fallback_search_v4(ledger: Any, execution: Any) -> None:
    """Seal the bound ledger only after the same V3 search returns its result."""

    session = _ACTIVE_ROUTE_SEGMENT_V4.get()
    if type(session) is not OwnedEngineFallbackRouteSegmentSessionV4:
        _fail("owned-engine search finish requires its exact active V4 session")
    try:
        search_frame = _FROZEN_GETFRAME_V4(1)
    except (AttributeError, ValueError) as error:
        session._abort("SEARCH_FRAME_UNAVAILABLE")
        raise ConstructionAccountingRouteSegmentV4Error(
            "owned-engine search finish frame is unavailable"
        ) from error
    session._finish_search_from_owner(
        _OWNED_SEARCH_FINISH_ISSUER_V4,
        ledger,
        execution,
        search_frame,
    )


_FROZEN_OPERATION_GATEWAY_OBJECT_V4 = emit_owned_route_operation_v4
_FROZEN_OPERATION_GATEWAY_GLOBALS_V4 = emit_owned_route_operation_v4.__globals__
_FROZEN_OPERATION_GATEWAY_CODE_V4 = emit_owned_route_operation_v4.__code__
_FROZEN_SEARCH_BIND_OBJECT_V4 = bind_owned_fallback_search_v4
_FROZEN_SEARCH_BIND_GLOBALS_V4 = bind_owned_fallback_search_v4.__globals__
_FROZEN_SEARCH_BIND_CODE_V4 = bind_owned_fallback_search_v4.__code__
_FROZEN_SEARCH_FINISH_OBJECT_V4 = finish_owned_fallback_search_v4
_FROZEN_SEARCH_FINISH_GLOBALS_V4 = finish_owned_fallback_search_v4.__globals__
_FROZEN_SEARCH_FINISH_CODE_V4 = finish_owned_fallback_search_v4.__code__


__all__ = (
    "CONSTRUCTION_ONLY",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionAccountingRouteSegmentV4Error",
    "EXPECTED_BOUNDARY_COUNT",
    "EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256",
    "EXPECTED_BOUNDARY_MANIFEST_ID",
    "EXPECTED_SOURCE_BYTE_COUNT",
    "EXPECTED_SOURCE_SHA256",
    "LEGACY_OWNER_GATEWAY",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OWNED_ENGINE_CONTRACT_VERSION",
    "OWNED_ENGINE_SOURCE_BYTE_COUNT",
    "OWNED_ENGINE_SOURCE_MODULE",
    "OWNED_ENGINE_SOURCE_RELATIVE_PATH",
    "OWNED_ENGINE_SOURCE_SHA256",
    "OWNED_ROUTE_EVENT_ACK_V4",
    "OwnedEngineFinishedExecutionBindingV4",
    "OwnedEngineFallbackRouteSegmentSessionV4",
    "OwnedEngineSearchSemanticsV4",
    "OwnedEngineRouteOperationEventV4",
    "OwnedEngineRouteSegmentStartV4",
    "OwnedEngineRouteSegmentTerminalV4",
    "OwnedEngineRouteSegmentTranscriptV4",
    "OwnedFallbackRouteSegmentSessionV4",
    "OwnedRouteOperationEventV4",
    "OwnedRouteSegmentStartV4",
    "OwnedRouteSegmentTerminalV4",
    "OwnedRouteSegmentTranscriptV4",
    "OwnerRuntimeIntegrationBlockedV4",
    "OwnerRuntimeIntegrationBlockerV4",
    "PRODUCTION_CLOSURE_CLAIMED",
    "PRODUCTION_OWNER_SOURCE_INTEGRATED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUIRED_CONTRACT_VERSION",
    "REQUIRED_OWNER_GATEWAY",
    "RouteOperationOriginV4",
    "RouteSegmentTerminalKindV4",
    "SCHEMA_VERSION",
    "SOURCE_MODULE",
    "SOURCE_RELATIVE_PATH",
    "SealedSourceMemberAuthorityV4",
    "VerifiedOwnedEngineAuthorityV4",
    "VerifiedOwnedEngineBoundaryV4",
    "VerifiedOperationBoundaryManifestAuthorityV4",
    "VerifiedOperationBoundaryV4",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "activate_construction_route_segment_v4",
    "activate_owned_route_segment_v4",
    "bind_owned_fallback_search_v4",
    "derive_owned_engine_search_semantics_v4",
    "emit_owned_route_operation_v4",
    "emit_verified_construction_operation_v4",
    "finish_owned_fallback_search_v4",
    "seal_owned_fallback_engine_import_v4",
    "verify_sealed_owned_engine_authority_v4",
    "verify_owned_engine_finished_execution_binding_v4",
    "verify_owned_fallback_engine_import_seal_v4",
    "verify_sealed_operation_boundary_authority_v4",
)
