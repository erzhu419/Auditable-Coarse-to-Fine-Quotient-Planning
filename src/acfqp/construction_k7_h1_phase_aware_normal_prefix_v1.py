"""Durable phase-aware execution of H1 lifecycle sites 1 through 40.

The historical lifecycle dispatcher is intentionally not called here: its
Owner entry points reacquire the attempt rejection gate and its events are
in-memory.  This successor owns one composite PHASE -> GATE -> JOURNAL ->
OWNER lease, records an intent before admission, records a callback result
before settlement, and commits one immutable event after settlement.  A
dangling native-start cell is conservatively closed and the callback is never
executed again.

This module stops at the successful normal prefix.  It does not execute site
41 or later, transition the attempt to cleanup-only, issue formal accounting
objects, or authorize official execution.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import dataclasses
from dataclasses import InitVar, dataclass, field
import dis
from enum import Enum
import fcntl
import hashlib
import hmac
import inspect
import os
from pathlib import Path
import re
import secrets
import stat
import threading
from types import FunctionType, MappingProxyType, ModuleType
from typing import Any, Callable, Iterator, Mapping, NoReturn

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_domain_registry_extension_v3 as domains_v3
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


_SOURCE_MODULES = MappingProxyType(
    {
        "dispatch_v1": dispatch_v1,
        "phase_v1": phase_v1,
        "rejection_v1": rejection_v1,
        "owner_v3": owner_v3,
        "owner_v4": owner_v4,
        "domains_v3": domains_v3,
    }
)


def _freeze_dependency_value(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_dependency_value(child) for key, child in value.items()}
        )
    if type(value) is list:
        return tuple(_freeze_dependency_value(child) for child in value)
    if type(value) is set:
        return frozenset(_freeze_dependency_value(child) for child in value)
    if type(value) is tuple:
        return tuple(_freeze_dependency_value(child) for child in value)
    return value


class _FrozenDependencyModuleView:
    __slots__ = ("_values",)

    def __init__(self, module: Any, *, deep_freeze: frozenset[str] = frozenset()) -> None:
        values = {
            name: (
                _freeze_dependency_value(value)
                if name in deep_freeze
                else value
            )
            for name, value in vars(module).items()
        }
        object.__setattr__(self, "_values", MappingProxyType(values))

    def __getattr__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, "_values")[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __setattr__(self, name: str, value: Any) -> NoReturn:
        raise RuntimeError("frozen dependency module view cannot be mutated")


# All execution below resolves through import-captured objects.  The source
# modules remain separately available only for drift detection.
dispatch_v1 = _FrozenDependencyModuleView(_SOURCE_MODULES["dispatch_v1"])
phase_v1 = _FrozenDependencyModuleView(_SOURCE_MODULES["phase_v1"])
rejection_v1 = _FrozenDependencyModuleView(_SOURCE_MODULES["rejection_v1"])
owner_v3 = _FrozenDependencyModuleView(
    _SOURCE_MODULES["owner_v3"], deep_freeze=frozenset({"_EXTRA_FIELDS"})
)
owner_v4 = _FrozenDependencyModuleView(_SOURCE_MODULES["owner_v4"])
domains_v3 = _FrozenDependencyModuleView(
    _SOURCE_MODULES["domains_v3"],
    deep_freeze=frozenset({"K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V3"}),
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-A"
PROFILE_KEY = "construction_k7_h1_phase_aware_normal_prefix_pretransition_v1"
PREFIX_END_ORDINAL = 40

AUTHORITY_STAGE = "PRETRANSITION_ONLY"
PHASE_AWARE_NORMAL_PREFIX_PRETRANSITION_1_40_PRESENT = True
NORMAL_PREFIX_1_40_DURABLE_HAPPY_PATH_PRESENT = True
NORMAL_PREFIX_1_40_PRETRANSITION_EVENT_RECOVERY_PRESENT = False
PHASE_AWARE_CAP_REJECTION_PAIR_ACK_EVENT_PRETRANSITION_RECOVERY_PRESENT = False
PHASE_AWARE_NORMAL_PREFIX_1_40_PRESENT = False
NORMAL_PREFIX_1_40_NO_EVENT_RECOVERY_COMPLETE = False
PHASE_AWARE_CAP_REJECTION_RECOVERY_PRESENT = False
PHASE_AWARE_FAILURE_TO_CLEANUP_TRANSITION_PRESENT = False
NO_EVENT_RECOVERY_COMPLETE = False
CLEANUP_EXECUTION_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
_LOCAL_AUTHORITY_POISONED = False

SPEC_DOMAIN = domains_v3.CONSTRUCTION_K7_H1_NORMAL_PREFIX_SPEC_V1_DOMAIN
ALLOCATION_DOMAIN = domains_v3.CONSTRUCTION_K7_H1_NORMAL_PREFIX_ALLOCATION_V1_DOMAIN
INTENT_DOMAIN = domains_v3.CONSTRUCTION_K7_H1_NORMAL_SITE_INTENT_V1_DOMAIN
CALLBACK_DOMAIN = domains_v3.CONSTRUCTION_K7_H1_NORMAL_SITE_CALLBACK_RESULT_V1_DOMAIN
EVENT_DOMAIN = domains_v3.CONSTRUCTION_K7_H1_NORMAL_SITE_EVENT_COMMIT_V1_DOMAIN
CURSOR_DOMAIN = domains_v3.CONSTRUCTION_K7_H1_NORMAL_PREFIX_CURSOR_RECORD_V1_DOMAIN
SNAPSHOT_DOMAIN = domains_v3.CONSTRUCTION_K7_H1_NORMAL_PREFIX_SNAPSHOT_V1_DOMAIN
SEMANTIC_CLOSURE_DOMAIN = (
    domains_v3.CONSTRUCTION_K7_H1_NORMAL_PREFIX_SEMANTIC_CLOSURE_V1_DOMAIN
)

_DEPENDENCY_SYMBOL_NAMES = MappingProxyType(
    {
        "dispatch_v1": frozenset(
            {
                "ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION",
                "H1AnchoredLifecycleDispatchBundleV1",
                "H1LifecycleDispatchProfileV1",
                "H1LifecycleHandlerModeV1",
                "_evidence_source_id",
                "_failure_outcomes",
                "_operation_id",
                "_owner_reservation_operation_id",
                "_resource_path",
            }
        ),
        "phase_v1": frozenset(
            {
                "H1AttemptExecutionPhaseOwnerV1Handle",
                "H1AttemptExecutionPhaseV1",
                "_ACTIVE_PHASE_LEASES",
                "_activate_lease_context",
                "_close_fork_inherited_locked",
                "_recover_locked",
                "_release_locked",
                "_require_handle_locked",
            }
        ),
        "rejection_v1": frozenset(
            {
                "H1AttemptRejectionAckV1",
                "H1AttemptRejectionCommitV1",
                "H1AttemptRejectionCrashPointV1",
                "H1AttemptRejectionGateHandleV1",
                "H1AttemptRejectionGateStateV1",
                "H1RejectionLimitKindV1",
                "H1RejectionSourceKindV1",
                "_ACK_FILE",
                "_ACK_ISSUER",
                "_activate_gate_context",
                "_active_gate_modes",
                "_append_cursor_state_locked",
                "_commit_rejection_locked",
                "_observe_gate_locked",
                "_publish_new",
                "_read_file",
                "_release_retained_gate_context",
                "_replay_gate_locked",
                "_require_handle",
            }
        ),
        "owner_v3": frozenset(
            {
                "H1SharedCapOwnerV3Handle",
                "H1SharedCapRejectionResultV3",
                "H1SharedNativeStateV3",
                "H1SharedReducerV3",
                "H1SharedReservationV3",
                "H1SharedSettlementResultV3",
                "H1SharedValueBasisV3",
                "_EXTRA_FIELDS",
                "_ReplayState",
                "_append_receipt_event_snapshot",
                "_append_record",
                "_append_rejection_pair_locked",
                "_find_pair_for_subject",
                "_limit",
                "_native_semantics",
                "_pair_extra",
                "_parse_document",
                "_read_file",
                "_record_id",
                "_record_names",
                "_replay_records_fd",
                "_require_durable_reservation",
                "_require_handle_locked",
                "_require_owner_open_join",
                "_require_pair_frontier",
                "_require_rejection_context",
                "_require_value_basis_path",
                "_reservation_document_for_request",
                "_verify_record_identity",
            }
        ),
        "owner_v4": frozenset(
            {
                "H1SharedCapOwnerV4WalHandle",
                "replay_h1_shared_cap_owner_v4_wal",
            }
        ),
        "domains_v3": frozenset(
            {
                "CONSTRUCTION_K7_H1_NORMAL_PREFIX_ALLOCATION_V1_DOMAIN",
                "CONSTRUCTION_K7_H1_NORMAL_PREFIX_CURSOR_RECORD_V1_DOMAIN",
                "CONSTRUCTION_K7_H1_NORMAL_PREFIX_SEMANTIC_CLOSURE_V1_DOMAIN",
                "CONSTRUCTION_K7_H1_NORMAL_PREFIX_SNAPSHOT_V1_DOMAIN",
                "CONSTRUCTION_K7_H1_NORMAL_PREFIX_SPEC_V1_DOMAIN",
                "CONSTRUCTION_K7_H1_NORMAL_SITE_CALLBACK_RESULT_V1_DOMAIN",
                "CONSTRUCTION_K7_H1_NORMAL_SITE_EVENT_COMMIT_V1_DOMAIN",
                "CONSTRUCTION_K7_H1_NORMAL_SITE_INTENT_V1_DOMAIN",
                "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V3",
                "extension_content_id_v3",
            }
        ),
    }
)

_ROOT_NAME = ".acfqp-k7-h1-normal-prefix-v1"
_ROOT_LOCK = ".allocation.lock"
_SPEC_FILE = "normal-prefix-spec.json"
_LOCK_FILE = "normal-prefix.lock"
_CURSOR_FILE = "normal-prefix.cursor"
_ALLOCATION_PREFIX = "allocation-"
_SEAL_PREFIX = "record-seal-"
_HIGH_WATER_TOKEN_PREFIX = "cursor-token-"
_HIGH_WATER_STATE_PREFIX = "cursor-state-"
_TEMP_PREFIX = ".tmp-"
_RECORD_PATTERN = re.compile(
    r"^(?P<ordinal>[0-9]{4})-(?P<kind>intent|callback|event)-"
    r"(?P<record>[0-9a-f]{64})\.json$"
)
_SEAL_PATTERN = re.compile(
    r"^record-seal-(?P<attempt>[0-9a-f]{64})-(?P<ordinal>[0-9]{4})-"
    r"(?P<kind>intent|callback|event)-(?P<record>[0-9a-f]{64})\.json$"
)
_HIGH_WATER_STATE_PATTERN = re.compile(
    r"^cursor-state-(?P<attempt>[0-9a-f]{64})-(?P<sequence>[0-9]{4})-"
    r"(?P<cursor>[0-9a-f]{64})$"
)

_SPEC_ISSUER = object()
_HANDLE_ISSUER = object()
_LEASE_ISSUER = object()
_INTENT_ISSUER = object()
_CALLBACK_ISSUER = object()
_EVENT_ISSUER = object()
_SNAPSHOT_ISSUER = object()
_ACTIVE_EXECUTIONS: ContextVar[tuple[str, ...]] = ContextVar(
    "acfqp_k7_h1_phase_aware_normal_prefix", default=()
)
_GATE_CONTEXT_MODE = "PHASE_AWARE_NORMAL_PREFIX_EXCLUSIVE"

_INTENT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_normal_prefix_spec_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "ordinal",
        "site_key",
        "phase",
        "operation",
        "from_state",
        "success_state",
        "handler_mode",
        "resource_path",
        "reducer",
        "callback_required",
        "failure_outcomes",
        "deterministic_dispatch_operation_id",
        "owner_reservation_operation_id",
        "native_evidence_source_id",
        "reservation_upper",
        "admission_candidate",
        "hard_cap",
        "expected_admission_outcome",
        "rejection_request_id",
        "previous_normal_site_event_commit_id",
        "owner_journal_sequence_before_site",
        "owner_journal_head_id_before_site",
        "durable_before_owner_admission",
        "callback_retry_forbidden_after_native_cell",
        "site_authority_single_use_per_lease",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "certificate_issued",
        "official_execution_allowed",
        "h1_normal_site_intent_id",
    }
)
_CALLBACK_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_normal_prefix_spec_id",
        "route_attempt_id",
        "ordinal",
        "site_key",
        "h1_normal_site_intent_id",
        "callback_result_kind",
        "native_observed_value",
        "callback_invocation_count",
        "callback_invocation_may_have_occurred",
        "callback_exception_type",
        "durable_before_owner_settlement",
        "native_evidence_authority_present",
        "official_execution_allowed",
        "h1_normal_site_callback_result_id",
    }
)
_EVENT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_normal_prefix_spec_id",
        "h1_lifecycle_dispatch_profile_id",
        "h1_anchored_lifecycle_program_id",
        "h1_anchored_lifecycle_handler_registry_id",
        "h1_shared_cap_owner_v3_runtime_id",
        "h1_shared_cap_owner_v4_wal_binding_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "ordinal",
        "site_key",
        "phase",
        "operation",
        "from_state",
        "success_state",
        "handler_mode",
        "resource_path",
        "reducer",
        "deterministic_dispatch_operation_id",
        "owner_reservation_operation_id",
        "h1_normal_site_intent_id",
        "h1_normal_site_callback_result_id",
        "previous_normal_site_event_commit_id",
        "outcome",
        "reservation_upper",
        "native_observed_value",
        "value_basis",
        "callback_invocation_count",
        "callback_exception_type",
        "owner_record_refs",
        "owner_journal_sequence_before_site",
        "owner_journal_head_id_before_site",
        "owner_journal_sequence_after_site",
        "owner_journal_head_id_after_site",
        "owner_appended_records",
        "declared_first_failure",
        "anchored_transition_semantics_present",
        "supplemental_protocol_abort",
        "normal_forward_dispatch_allowed_after_event",
        "event_durable_exactly_once",
        "callback_result_durable_before_settlement",
        "callback_invocation_may_have_occurred",
        "first_failure_is_provisional_prefix_only",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "certificate_issued",
        "infeasibility_certified",
        "formal_counter_records_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "formal_v7_route_authority_present",
        "official_execution_allowed",
        "h1_normal_site_event_commit_id",
    }
)
_ALLOCATION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_normal_prefix_spec_id",
        "route_attempt_id",
        "normal_prefix_root_realpath",
        "normal_prefix_root_device",
        "normal_prefix_root_inode",
        "root_allocation_lock_device",
        "root_allocation_lock_inode",
        "high_water_token_device",
        "high_water_token_inode",
        "normal_prefix_journal_realpath",
        "normal_prefix_journal_device",
        "normal_prefix_journal_inode",
        "normal_prefix_lock_device",
        "normal_prefix_lock_inode",
        "normal_prefix_cursor_device",
        "normal_prefix_cursor_inode",
        "single_attempt_allocation",
        "root_record_seals_required",
        "official_execution_allowed",
        "h1_normal_prefix_allocation_id",
    }
)


class ConstructionK7H1PhaseAwareNormalPrefixV1Error(ValueError):
    pass


class H1NormalPrefixProtocolFailureV1(ConstructionK7H1PhaseAwareNormalPrefixV1Error):
    pass


class H1NormalPrefixInjectedCrashV1(RuntimeError):
    pass


class H1NormalPrefixForkedCallbackContinuationV1(RuntimeError):
    pass


class H1NormalPrefixCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_INTENT_FSYNC = "AFTER_INTENT_FSYNC"
    AFTER_RESERVATION_FSYNC = "AFTER_RESERVATION_FSYNC"
    AFTER_NATIVE_CELL_FSYNC = "AFTER_NATIVE_CELL_FSYNC"
    AFTER_CALLBACK_RESULT_FSYNC = "AFTER_CALLBACK_RESULT_FSYNC"
    AFTER_SETTLEMENT_FSYNC = "AFTER_SETTLEMENT_FSYNC"
    AFTER_EVENT_FSYNC = "AFTER_EVENT_FSYNC"


class H1NormalPrefixStatusV1(str, Enum):
    READY = "READY"
    CALLBACK_REQUIRED_TO_RESUME_SAFE_PRESTART = (
        "CALLBACK_REQUIRED_TO_RESUME_SAFE_PRESTART"
    )
    NORMAL_PREFIX_COMPLETE_AWAITING_POST_CHILD_CLEANUP = (
        "NORMAL_PREFIX_COMPLETE_AWAITING_POST_CHILD_CLEANUP"
    )
    FAILURE_POISONED_AWAITING_PHASE_TRANSITION = (
        "FAILURE_POISONED_AWAITING_PHASE_TRANSITION"
    )


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1PhaseAwareNormalPrefixV1Error(message)


def _protocol(message: str) -> NoReturn:
    raise H1NormalPrefixProtocolFailureV1(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1PhaseAwareNormalPrefixV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be one nonempty string")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative integer")
    return value


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _content_id(domain: str, payload: Any) -> str:
    return domains_v3.extension_content_id_v3(domain, payload)


def _parse_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise H1NormalPrefixProtocolFailureV1(f"{label} is not canonical JSON") from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _protocol(f"{label} is not one exact canonical object")
    return value


def _stable_dependency_value(value: Any) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is bytes:
        return {"bytes_hex": value.hex()}
    if type(value) is float:
        return {"float_hex": value.hex()}
    if isinstance(value, Enum):
        return {
            "enum_type": f"{type(value).__module__}.{type(value).__qualname__}",
            "name": value.name,
            "value": _stable_dependency_value(value.value),
        }
    if isinstance(value, Mapping):
        rows = [
            {
                "key": _stable_dependency_value(key),
                "value": _stable_dependency_value(child),
            }
            for key, child in value.items()
        ]
        return {
            "kind": "MAPPING",
            "items": sorted(rows, key=lambda row: canonical_json_bytes(row["key"])),
        }
    if type(value) in {tuple, list}:
        return [_stable_dependency_value(child) for child in value]
    if type(value) in {set, frozenset}:
        children = [_stable_dependency_value(child) for child in value]
        return sorted(children, key=canonical_json_bytes)
    if type(value) is FunctionType:
        return _dependency_callable_document(value)
    if isinstance(value, re.Pattern):
        return {"kind": "REGEX", "pattern": value.pattern, "flags": value.flags}
    if isinstance(value, ContextVar):
        return {"kind": "CONTEXT_VAR", "name": value.name}
    if isinstance(value, ModuleType):
        return {"kind": "MODULE_REFERENCE", "name": value.__name__}
    if isinstance(value, (classmethod, staticmethod)):
        return {
            "kind": type(value).__name__.upper(),
            "function": _stable_dependency_value(value.__func__),
        }
    if isinstance(value, property):
        return {
            "kind": "PROPERTY",
            "getter": _stable_dependency_value(value.fget),
            "setter": _stable_dependency_value(value.fset),
            "deleter": _stable_dependency_value(value.fdel),
        }
    if isinstance(value, dataclasses.Field):
        def field_value(child: Any) -> Any:
            if child is dataclasses.MISSING:
                return {"kind": "DATACLASSES_MISSING"}
            return _stable_dependency_value(child)

        return {
            "kind": "DATACLASS_FIELD",
            "name": value.name,
            "type": _stable_dependency_value(value.type),
            "default": field_value(value.default),
            "default_factory": field_value(value.default_factory),
            "repr": value.repr,
            "hash": value.hash,
            "init": value.init,
            "compare": value.compare,
            "metadata": _stable_dependency_value(value.metadata),
            "kw_only": value.kw_only,
            "field_type": repr(getattr(value, "_field_type", None)),
        }
    if type(value).__module__ == "dataclasses" and type(value).__qualname__ == "_DataclassParams":
        return {
            "kind": "DATACLASS_PARAMS",
            "parameters": {
                key: getattr(value, key, None)
                for key in (
                    "init",
                    "repr",
                    "eq",
                    "order",
                    "unsafe_hash",
                    "frozen",
                    "match_args",
                    "kw_only",
                    "slots",
                    "weakref_slot",
                )
            },
        }
    if isinstance(value, type):
        payload: dict[str, Any] = {
            "kind": "TYPE",
            "module": value.__module__,
            "qualname": value.__qualname__,
        }
        if issubclass(value, Enum):
            payload["members"] = {
                name: _stable_dependency_value(member.value)
                for name, member in value.__members__.items()
            }
        return payload
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
    if callable(value):
        return {
            "kind": "CALLABLE_REFERENCE",
            "module": getattr(value, "__module__", type(value).__module__),
            "qualname": getattr(value, "__qualname__", type(value).__qualname__),
        }
    return {
        "kind": "OPAQUE_ROLE_OBJECT",
        "type_module": type(value).__module__,
        "type_qualname": type(value).__qualname__,
    }


def _stable_code_value(value: Any) -> Any:
    if hasattr(value, "co_code") and hasattr(value, "co_consts"):
        return _stable_code_document(value)
    return _stable_dependency_value(value)


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


def _dependency_callable_document(function: FunctionType) -> dict[str, Any]:
    return {
        "kind": "PYTHON_FUNCTION",
        "module": function.__module__,
        "qualname": function.__qualname__,
        "code": _stable_code_document(function.__code__),
        "defaults": _stable_dependency_value(function.__defaults__),
        "kwdefaults": _stable_dependency_value(function.__kwdefaults__),
    }


def _dependency_descriptor(value: Any) -> dict[str, Any]:
    stable = _stable_dependency_value(value)
    raw = canonical_json_bytes(stable)
    return {
        "semantic_sha256": hashlib.sha256(
            b"acfqp:k7-h1-normal-prefix-dependency-symbol:v1\x00" + raw
        ).hexdigest(),
        "semantic_projection": stable,
    }


_IMPORT_DEPENDENCY_OBJECTS = MappingProxyType(
    {
        f"{module_name}.{symbol_name}": getattr(module, symbol_name)
        for module_name, module in _SOURCE_MODULES.items()
        for symbol_name in _DEPENDENCY_SYMBOL_NAMES[module_name]
    }
)
_IMPORT_DEPENDENCY_DESCRIPTOR_BYTES = MappingProxyType(
    {
        role: canonical_json_bytes(_dependency_descriptor(value))
        for role, value in _IMPORT_DEPENDENCY_OBJECTS.items()
    }
)


def _derive_transitive_dependency_semantics() -> tuple[dict[str, Any], dict[str, Any]]:
    refs: dict[str, Any] = {}
    functions: dict[str, FunctionType] = {}
    function_ordinals: dict[int, int] = {}
    pending_functions: list[FunctionType] = []
    pending_types: list[type] = []
    processed_types: set[int] = set()
    module_rows: dict[str, dict[str, Any]] = {}

    def register(key: str, value: Any) -> None:
        previous = refs.get(key)
        if previous is not None and previous is not value:
            _fail(f"normal-prefix transitive dependency identity collided: {key}")
        refs[key] = value

    def register_module(module: ModuleType) -> None:
        if not module.__name__.startswith("acfqp"):
            return
        path = Path(module.__file__).resolve(strict=True)
        raw = path.read_bytes()
        if not raw:
            _fail("normal-prefix transitive dependency source is empty")
        module_rows[module.__name__] = {
            "module": module.__name__,
            "loaded_realpath": str(path),
            "source_byte_count": len(raw),
            "source_sha256": hashlib.sha256(raw).hexdigest(),
        }

    def enqueue_function(value: Any, key: str) -> None:
        if type(value) is not FunctionType:
            return
        register(key, value)
        if value.__module__.startswith("acfqp"):
            function_ordinals.setdefault(id(value), len(function_ordinals))
            pending_functions.append(value)

    def enqueue_descriptor(value: Any, key: str) -> None:
        if type(value) is FunctionType:
            enqueue_function(value, key)
        elif isinstance(value, (classmethod, staticmethod)):
            enqueue_function(value.__func__, f"{key}:function")
        elif isinstance(value, property):
            for role, function in (
                ("get", value.fget),
                ("set", value.fset),
                ("delete", value.fdel),
            ):
                if function is not None:
                    enqueue_function(function, f"{key}:{role}")

    for role, value in sorted(_IMPORT_DEPENDENCY_OBJECTS.items()):
        register(f"direct:{role}", value)
        if type(value) is FunctionType:
            enqueue_function(value, f"direct-function:{role}")
        elif isinstance(value, type):
            pending_types.append(value)

    while pending_functions or pending_types:
        while pending_functions:
            function = pending_functions.pop()
            function_key = (
                f"{function.__module__}:{function.__qualname__}:"
                f"{function_ordinals[id(function)]:06d}"
            )
            existing = functions.get(function_key)
            if existing is not None:
                if existing is not function:
                    _fail(
                        "normal-prefix transitive function qualname changed identity"
                    )
                continue
            functions[function_key] = function
            module = inspect.getmodule(function)
            if isinstance(module, ModuleType):
                register_module(module)
            namespace = function.__globals__
            for global_name in function.__code__.co_names:
                if global_name not in namespace:
                    continue
                value = namespace[global_name]
                binding = f"global:{function_key}:{global_name}"
                register(binding, value)
                if type(value) is FunctionType:
                    enqueue_function(value, f"{binding}:function")
                elif isinstance(value, type):
                    pending_types.append(value)
                elif isinstance(value, ModuleType):
                    register_module(value)
            instructions = tuple(dis.get_instructions(function))
            for index, instruction in enumerate(instructions):
                if instruction.opname not in {"LOAD_GLOBAL", "LOAD_NAME"}:
                    continue
                global_name = instruction.argval
                if global_name not in namespace:
                    continue
                current = namespace[global_name]
                for attribute_instruction in instructions[index + 1 :]:
                    if attribute_instruction.opname not in {"LOAD_ATTR", "LOAD_METHOD"}:
                        break
                    attribute_name = attribute_instruction.argval
                    try:
                        current = (
                            vars(current)[attribute_name]
                            if isinstance(current, ModuleType)
                            else inspect.getattr_static(current, attribute_name)
                        )
                    except (KeyError, AttributeError):
                        break
                    binding = (
                        f"attribute:{function_key}:{global_name}:{attribute_name}"
                    )
                    register(binding, current)
                    enqueue_descriptor(current, binding)
                    if isinstance(current, type):
                        pending_types.append(current)
            for index, cell in enumerate(function.__closure__ or ()):
                try:
                    value = cell.cell_contents
                except ValueError as error:
                    raise ConstructionK7H1PhaseAwareNormalPrefixV1Error(
                        "normal-prefix transitive dependency has an empty closure cell"
                    ) from error
                binding = f"closure:{function_key}:{index}"
                register(binding, value)
                enqueue_descriptor(value, binding)
                if isinstance(value, type):
                    pending_types.append(value)

        while pending_types:
            value = pending_types.pop()
            if id(value) in processed_types or not value.__module__.startswith("acfqp"):
                continue
            processed_types.add(id(value))
            module = inspect.getmodule(value)
            if isinstance(module, ModuleType):
                register_module(module)
            type_key = (
                f"{value.__module__}:{value.__qualname__}:"
                f"{len(processed_types):06d}"
            )
            register(f"behavior-type:{type_key}", value)
            if issubclass(value, Enum):
                for attribute_name in (
                    "_member_names_",
                    "_member_map_",
                    "_value2member_map_",
                ):
                    register(
                        f"enum-state:{type_key}:{attribute_name}",
                        vars(value)[attribute_name],
                    )
            if dataclasses.is_dataclass(value):
                for attribute_name in (
                    "__dataclass_fields__",
                    "__dataclass_params__",
                ):
                    register(
                        f"dataclass-state:{type_key}:{attribute_name}",
                        vars(value)[attribute_name],
                    )
            for attribute_name, attribute in sorted(vars(value).items()):
                if not (
                    type(attribute) is FunctionType
                    or isinstance(attribute, (classmethod, staticmethod, property))
                    or inspect.ismethoddescriptor(attribute)
                    or inspect.isdatadescriptor(attribute)
                    or callable(attribute)
                ):
                    continue
                binding = f"behavior-attribute:{type_key}:{attribute_name}"
                register(binding, attribute)
                enqueue_descriptor(attribute, binding)
            for base in value.__mro__[1:]:
                if base.__module__.startswith("acfqp"):
                    pending_types.append(base)

    function_rows = [
        {
            "function_key": key,
            "semantic_projection": _stable_dependency_value(function),
        }
        for key, function in sorted(functions.items())
    ]
    binding_rows = [
        {
            "binding_key": key,
            "semantic_projection": _stable_dependency_value(value),
        }
        for key, value in sorted(refs.items())
    ]
    payload = {
        "module_rows": [module_rows[key] for key in sorted(module_rows)],
        "function_rows": function_rows,
        "binding_rows": binding_rows,
        "module_count": len(module_rows),
        "function_count": len(function_rows),
        "binding_count": len(binding_rows),
        "transitive_project_functions_closed": True,
        "project_type_behavior_bound": True,
        "closure_cells_bound": True,
        "hostile_stdlib_or_interpreter_monkeypatch_complete": False,
        "cross_process_runtime_identity_authority_present": False,
    }
    return payload, refs


(
    _IMPORT_TRANSITIVE_DEPENDENCY_SEMANTICS_MUTABLE,
    _IMPORT_TRANSITIVE_DEPENDENCY_REFS_MUTABLE,
) = _derive_transitive_dependency_semantics()
_IMPORT_TRANSITIVE_DEPENDENCY_SEMANTICS_BYTES = canonical_json_bytes(
    _IMPORT_TRANSITIVE_DEPENDENCY_SEMANTICS_MUTABLE
)
del _IMPORT_TRANSITIVE_DEPENDENCY_SEMANTICS_MUTABLE
_IMPORT_TRANSITIVE_DEPENDENCY_REFS = MappingProxyType(
    dict(_IMPORT_TRANSITIVE_DEPENDENCY_REFS_MUTABLE)
)
del _IMPORT_TRANSITIVE_DEPENDENCY_REFS_MUTABLE


def _require_dependency_namespace_unchanged(*, full: bool = False) -> None:
    for role, original in _IMPORT_DEPENDENCY_OBJECTS.items():
        module_name, symbol_name = role.split(".", 1)
        current = getattr(_SOURCE_MODULES[module_name], symbol_name, None)
        if (
            current is not original
            or canonical_json_bytes(_dependency_descriptor(current))
            != _IMPORT_DEPENDENCY_DESCRIPTOR_BYTES[role]
        ):
            _fail(f"normal-prefix dependency drifted after import: {role}")
    if not full:
        return
    current_semantics, current_refs = _derive_transitive_dependency_semantics()
    if canonical_json_bytes(current_semantics) != (
        _IMPORT_TRANSITIVE_DEPENDENCY_SEMANTICS_BYTES
    ):
        _fail("normal-prefix transitive dependency semantics drifted after import")
    if frozenset(current_refs) != frozenset(_IMPORT_TRANSITIVE_DEPENDENCY_REFS):
        _fail("normal-prefix transitive dependency bindings changed shape")
    for key, original in _IMPORT_TRANSITIVE_DEPENDENCY_REFS.items():
        current = current_refs[key]
        if type(original) not in {type(None), bool, int, str, bytes, float}:
            if current is not original:
                _fail(
                    "normal-prefix transitive dependency changed identity: " + key
                )


def _capture_local_authority_state() -> tuple[tuple[Any, ...], ...]:
    rows: list[tuple[Any, ...]] = []
    namespace = globals()
    post_capture_names = frozenset(
        {
            "_IMPORT_LOCAL_AUTHORITY_STATE",
            "_IMPORT_LOCAL_AUTHORITY_GUARD",
            "_IMPORT_LOCAL_AUTHORITY_GUARD_CODE",
            "_IMPORT_DEPENDENCY_GUARD",
            "_IMPORT_DEPENDENCY_GUARD_CODE",
        }
    )
    rows.append(
        (
            "NAMESPACE_NAMES",
            frozenset(
                name for name in namespace if not name.startswith("__")
            )
            | post_capture_names,
        )
    )
    pending_nested_functions: list[tuple[str, FunctionType]] = []
    seen_function_ids: set[int] = set()

    def append_function_row(
        kind: str,
        binding: str,
        function: FunctionType,
    ) -> None:
        if id(function) in seen_function_ids:
            return
        seen_function_ids.add(id(function))
        closure_values = tuple(
            cell.cell_contents for cell in (function.__closure__ or ())
        )
        rows.append(
            (
                kind,
                binding,
                function,
                function.__code__,
                function.__defaults__,
                function.__kwdefaults__,
                repr(function.__defaults__),
                repr(function.__kwdefaults__),
                (
                    dict(function.__kwdefaults__)
                    if type(function.__kwdefaults__) is dict
                    else None
                ),
                closure_values,
                tuple(repr(value) for value in closure_values),
            )
        )
        for index, value in enumerate(closure_values):
            if type(value) is FunctionType:
                pending_nested_functions.append(
                    (f"{binding}.__closure__[{index}]", value)
                )

    for name, value in sorted(namespace.items()):
        if name.startswith("__"):
            continue
        rows.append(("GLOBAL_BINDING", name, value))
        if isinstance(value, _FrozenDependencyModuleView):
            frozen_values = object.__getattribute__(value, "_values")
            rows.append(
                (
                    "FROZEN_DEPENDENCY_VIEW",
                    name,
                    value,
                    frozen_values,
                    tuple(
                        (
                            key,
                            child,
                            canonical_json_bytes(_stable_dependency_value(child)),
                        )
                        for key, child in sorted(frozen_values.items())
                    ),
                )
            )
        if type(value) is FunctionType:
            append_function_row("FUNCTION", name, value)
        elif isinstance(value, type) and value.__module__ == __name__:
            rows.append(("TYPE", name, value, frozenset(vars(value))))
            for attribute_name, attribute in sorted(vars(value).items()):
                rows.append(
                    (
                        "TYPE_MEMBER",
                        name,
                        value,
                        attribute_name,
                        attribute,
                        repr(attribute),
                        (
                            ("DICT", dict(attribute))
                            if type(attribute) is dict
                            else ("LIST", list(attribute))
                            if type(attribute) is list
                            else ("SET", set(attribute))
                            if type(attribute) is set
                            else None
                        ),
                    )
                )
                functions: tuple[FunctionType, ...]
                if type(attribute) is FunctionType:
                    functions = (attribute,)
                elif isinstance(attribute, (classmethod, staticmethod)):
                    functions = (attribute.__func__,)
                elif isinstance(attribute, property):
                    functions = tuple(
                        function
                        for function in (attribute.fget, attribute.fset, attribute.fdel)
                        if function is not None
                    )
                else:
                    functions = ()
                if functions:
                    rows.append(
                        (
                            "TYPE_ATTRIBUTE",
                            name,
                            value,
                            attribute_name,
                            attribute,
                            tuple(
                                (
                                    function,
                                    function.__code__,
                                    function.__defaults__,
                                    function.__kwdefaults__,
                                    repr(function.__defaults__),
                                    repr(function.__kwdefaults__),
                                )
                                for function in functions
                            ),
                        )
                    )
                    for index, function in enumerate(functions):
                        append_function_row(
                            "NESTED_FUNCTION",
                            f"{name}.{attribute_name}[{index}]",
                            function,
                        )
    while pending_nested_functions:
        binding, function = pending_nested_functions.pop()
        append_function_row("NESTED_FUNCTION", binding, function)
    return tuple(rows)


def _require_local_authority_namespace_unchanged(
    state: tuple[tuple[Any, ...], ...],
) -> None:
    namespace = globals()
    for row in state:
        kind = row[0]
        if kind == "NAMESPACE_NAMES":
            _, expected_names = row
            current_names = frozenset(
                name for name in namespace if not name.startswith("__")
            )
            if current_names != expected_names:
                raise RuntimeError(
                    "normal-prefix local authority namespace shape drifted"
                )
        elif kind == "GLOBAL_BINDING":
            _, name, original = row
            if namespace.get(name) is not original:
                raise RuntimeError(
                    "normal-prefix local authority binding drifted: " + name
                )
        elif kind == "FROZEN_DEPENDENCY_VIEW":
            _, name, original, original_values, values = row
            current_values = object.__getattribute__(original, "_values")
            if current_values is not original_values or frozenset(
                current_values
            ) != frozenset(key for key, _, _ in values):
                raise RuntimeError(
                    "normal-prefix frozen dependency view drifted: " + name
                )
            for key, child, semantic_bytes in values:
                current = current_values.get(key)
                if (
                    current is not child
                    or canonical_json_bytes(_stable_dependency_value(current))
                    != semantic_bytes
                ):
                    raise RuntimeError(
                        "normal-prefix frozen dependency value drifted: "
                        + name
                        + "."
                        + key
                    )
        elif kind in {"FUNCTION", "NESTED_FUNCTION"}:
            (
                _,
                name,
                original,
                code,
                defaults,
                kwdefaults,
                defaults_repr,
                kwdefaults_repr,
                kwdefaults_snapshot,
                closure_values,
                closure_reprs,
            ) = row
            current = namespace.get(name) if kind == "FUNCTION" else original
            if (
                current is not original
                or current.__code__ is not code
                or current.__defaults__ is not defaults
                or current.__kwdefaults__ is not kwdefaults
                or repr(current.__defaults__) != defaults_repr
                or repr(current.__kwdefaults__) != kwdefaults_repr
                or (
                    kwdefaults_snapshot is not None
                    and dict(current.__kwdefaults__ or {}) != kwdefaults_snapshot
                )
                or len(current.__closure__ or ()) != len(closure_values)
                or any(
                    cell.cell_contents is not expected
                    for cell, expected in zip(
                        current.__closure__ or (), closure_values
                    )
                )
                or tuple(
                    repr(cell.cell_contents)
                    for cell in (current.__closure__ or ())
                )
                != closure_reprs
            ):
                raise RuntimeError(
                    "normal-prefix local authority function drifted: " + name
                )
        elif kind == "TYPE":
            _, name, original, attribute_names = row
            if (
                namespace.get(name) is not original
                or frozenset(vars(original)) != attribute_names
            ):
                raise RuntimeError(
                    "normal-prefix local authority type drifted: " + name
                )
        elif kind == "TYPE_MEMBER":
            (
                _,
                name,
                original_type,
                attribute_name,
                original,
                original_repr,
                _mutable_snapshot,
            ) = row
            current = vars(original_type).get(attribute_name)
            if current is not original or repr(current) != original_repr:
                raise RuntimeError(
                    "normal-prefix local type state drifted: "
                    + name
                    + "."
                    + attribute_name
                )
        elif kind == "TYPE_ATTRIBUTE":
            _, name, original_type, attribute_name, original, functions = row
            current = vars(original_type).get(attribute_name)
            if current is not original:
                raise RuntimeError(
                    "normal-prefix local type behavior drifted: "
                    + name
                    + "."
                    + attribute_name
                )
            for (
                function,
                code,
                defaults,
                kwdefaults,
                defaults_repr,
                kwdefaults_repr,
            ) in functions:
                if (
                    function.__code__ is not code
                    or function.__defaults__ is not defaults
                    or function.__kwdefaults__ is not kwdefaults
                    or repr(function.__defaults__) != defaults_repr
                    or repr(function.__kwdefaults__) != kwdefaults_repr
                ):
                    raise RuntimeError(
                        "normal-prefix local type callable drifted: "
                        + name
                        + "."
                        + attribute_name
                    )
        else:
            raise RuntimeError(
                "unknown normal-prefix local authority state row: " + str(kind)
            )


def _restore_local_authority_state_after_callback(
    state: tuple[tuple[Any, ...], ...],
    namespace: dict[str, Any],
) -> None:
    expected_names: frozenset[str] | None = None
    for row in state:
        kind = row[0]
        if kind == "NAMESPACE_NAMES":
            expected_names = row[1]
        elif kind == "GLOBAL_BINDING":
            namespace[row[1]] = row[2]
        elif kind == "FROZEN_DEPENDENCY_VIEW":
            object.__setattr__(row[2], "_values", row[3])

    for row in state:
        kind = row[0]
        if kind in {"FUNCTION", "NESTED_FUNCTION"}:
            (
                _,
                _name,
                function,
                code,
                defaults,
                kwdefaults,
                _defaults_repr,
                _kwdefaults_repr,
                kwdefaults_snapshot,
                _closure_values,
                _closure_reprs,
            ) = row
            function.__code__ = code
            function.__defaults__ = defaults
            function.__kwdefaults__ = kwdefaults
            if type(kwdefaults) is dict and kwdefaults_snapshot is not None:
                kwdefaults.clear()
                kwdefaults.update(kwdefaults_snapshot)
        elif kind == "TYPE":
            _, _name, original_type, expected_attributes = row
            for attribute_name in tuple(vars(original_type)):
                if attribute_name not in expected_attributes:
                    type.__delattr__(original_type, attribute_name)
        elif kind == "TYPE_MEMBER":
            (
                _,
                _name,
                original_type,
                attribute_name,
                original,
                _original_repr,
                mutable_snapshot,
            ) = row
            if vars(original_type).get(attribute_name) is not original:
                type.__setattr__(original_type, attribute_name, original)
            if mutable_snapshot is not None:
                container_kind, snapshot = mutable_snapshot
                if container_kind == "DICT":
                    original.clear()
                    original.update(snapshot)
                elif container_kind == "LIST":
                    original[:] = snapshot
                elif container_kind == "SET":
                    original.clear()
                    original.update(snapshot)
                else:  # pragma: no cover - issuer-owned exhaustive snapshot
                    raise RuntimeError(
                        "normal-prefix local mutable snapshot kind is invalid"
                    )
        elif kind == "TYPE_ATTRIBUTE":
            _, _name, _original_type, _attribute_name, _original, functions = row
            for (
                function,
                code,
                defaults,
                kwdefaults,
                _defaults_repr,
                _kwdefaults_repr,
            ) in functions:
                function.__code__ = code
                function.__defaults__ = defaults
                function.__kwdefaults__ = kwdefaults

    if expected_names is None:  # pragma: no cover - import-time invariant
        raise RuntimeError("normal-prefix local authority namespace row is absent")
    for name in tuple(namespace):
        if not name.startswith("__") and name not in expected_names:
            del namespace[name]


def _open_directory(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1PhaseAwareNormalPrefixV1Error(
            "normal-prefix directory cannot be opened"
        ) from error


def _open_directory_at(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise ConstructionK7H1PhaseAwareNormalPrefixV1Error(
            "normal-prefix child directory cannot be opened"
        ) from error


def _open_regular_at(
    directory_fd: int,
    name: str,
    *,
    flags: int,
    mode: int = 0o600,
) -> int:
    effective = flags | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        effective |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, effective, mode, dir_fd=directory_fd)
    except OSError as error:
        raise ConstructionK7H1PhaseAwareNormalPrefixV1Error(
            f"normal-prefix regular file {name!r} cannot be opened"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        _fail("normal-prefix regular file was replaced")
    return descriptor


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:  # pragma: no cover - kernel contract
            _fail("normal-prefix durable write made no progress")
        view = view[written:]


def _read_file(directory_fd: int, name: str) -> bytes | None:
    try:
        descriptor = _open_regular_at(directory_fd, name, flags=os.O_RDONLY)
    except ConstructionK7H1PhaseAwareNormalPrefixV1Error:
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        raise
    try:
        metadata = os.fstat(descriptor)
        if stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}:
            _protocol("normal-prefix record has a noncanonical mode")
        chunks: list[bytes] = []
        while True:
            block = os.read(descriptor, 65536)
            if not block:
                break
            chunks.append(block)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _publish_new(
    directory_fd: int,
    name: str,
    raw: bytes,
    *,
    mode: int = 0o400,
) -> bool:
    temporary = f"{_TEMP_PREFIX}{os.getpid()}-{secrets.token_hex(16)}"
    descriptor = _open_regular_at(
        directory_fd,
        temporary,
        flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode=0o600,
    )
    try:
        _write_all(descriptor, raw)
        os.fsync(descriptor)
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    published = False
    try:
        try:
            os.link(
                temporary,
                name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
            os.fsync(directory_fd)
            published = True
        except FileExistsError:
            published = False
    finally:
        try:
            os.unlink(temporary, dir_fd=directory_fd)
            os.fsync(directory_fd)
        except FileNotFoundError:  # pragma: no cover
            pass
    return published


def _cleanup_temps(directory_fd: int) -> None:
    changed = False
    for name in os.listdir(directory_fd):
        if not name.startswith(_TEMP_PREFIX):
            continue
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            _protocol("normal-prefix orphan temp is not private and regular")
        os.unlink(name, dir_fd=directory_fd)
        changed = True
    if changed:
        os.fsync(directory_fd)


def _require_mode(metadata: os.stat_result, mode: int, label: str) -> None:
    if not stat.S_ISREG(metadata.st_mode) and label not in {
        "normal-prefix root",
        "normal-prefix attempt directory",
    }:
        _protocol(f"{label} is not regular")
    if stat.S_IMODE(metadata.st_mode) != mode:
        _protocol(f"{label} mode changed")


@dataclass(frozen=True, slots=True)
class H1NormalPrefixSpecV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SPEC_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("normal-prefix spec is caller-minted")
        payload = _parse_document(self.payload_bytes, "normal-prefix spec")
        object.__setattr__(self, "_spec_id", _content_id(SPEC_DOMAIN, payload))

    @property
    def spec_id(self) -> str:
        return self._spec_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse_document(self.payload_bytes, "normal-prefix spec")

    def to_document(self) -> dict[str, Any]:
        return {**self.payload, "h1_normal_prefix_spec_id": self.spec_id}


@dataclass(frozen=True, slots=True)
class H1NormalPrefixHandleV1:
    _issuer: InitVar[object]
    spec: H1NormalPrefixSpecV1
    allocation_id: str
    root_directory: str
    root_device: int
    root_inode: int
    root_lock_device: int
    root_lock_inode: int
    high_water_token_device: int
    high_water_token_inode: int
    journal_directory: str
    journal_device: int
    journal_inode: int
    lock_device: int
    lock_inode: int
    cursor_device: int
    cursor_inode: int

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _HANDLE_ISSUER or type(self.spec) is not H1NormalPrefixSpecV1:
            _fail("normal-prefix handle is caller-minted")
        _cid(self.allocation_id, "normal-prefix allocation")
        _nonempty(self.root_directory, "normal-prefix root directory")
        _nonempty(self.journal_directory, "normal-prefix journal directory")
        for label, value in (
            ("root device", self.root_device),
            ("root inode", self.root_inode),
            ("root-lock device", self.root_lock_device),
            ("root-lock inode", self.root_lock_inode),
            ("high-water-token device", self.high_water_token_device),
            ("high-water-token inode", self.high_water_token_inode),
            ("journal device", self.journal_device),
            ("journal inode", self.journal_inode),
            ("journal-lock device", self.lock_device),
            ("journal-lock inode", self.lock_inode),
            ("cursor device", self.cursor_device),
            ("cursor inode", self.cursor_inode),
        ):
            _nonnegative(value, "normal-prefix " + label)

    @property
    def route_attempt_id(self) -> str:
        return self.spec.payload["route_attempt_id"]

    def __reduce__(self) -> NoReturn:
        _fail("normal-prefix handle is not serializable")


@dataclass(frozen=True, slots=True)
class H1NormalSiteIntentV1:
    _issuer: InitVar[object]
    _document_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _INTENT_ISSUER or type(self._document_bytes) is not bytes:
            _fail("normal-site intent is caller-minted")
        document = _parse_document(self._document_bytes, "normal-site intent")
        kind, _key, _record_id = _record_identity(document)
        if kind != "intent":
            _fail("normal-site intent bytes have the wrong schema")

    @property
    def document(self) -> dict[str, Any]:
        return _parse_document(self._document_bytes, "normal-site intent")

    @property
    def intent_id(self) -> str:
        return _cid(self.document["h1_normal_site_intent_id"], "normal-site intent")

    @property
    def canonical_bytes(self) -> bytes:
        return bytes(self._document_bytes)


@dataclass(frozen=True, slots=True)
class H1NormalSiteCallbackResultV1:
    _issuer: InitVar[object]
    _document_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CALLBACK_ISSUER or type(self._document_bytes) is not bytes:
            _fail("normal-site callback result is caller-minted")
        document = _parse_document(
            self._document_bytes, "normal-site callback result"
        )
        kind, _key, _record_id = _record_identity(document)
        if kind != "callback":
            _fail("normal-site callback-result bytes have the wrong schema")

    @property
    def document(self) -> dict[str, Any]:
        return _parse_document(
            self._document_bytes, "normal-site callback result"
        )

    @property
    def callback_result_id(self) -> str:
        return _cid(
            self.document["h1_normal_site_callback_result_id"],
            "normal-site callback result",
        )

    @property
    def canonical_bytes(self) -> bytes:
        return bytes(self._document_bytes)


@dataclass(frozen=True, slots=True)
class H1NormalSiteEventCommitV1:
    _issuer: InitVar[object]
    _document_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EVENT_ISSUER or type(self._document_bytes) is not bytes:
            _fail("normal-site event is caller-minted")
        document = _parse_document(self._document_bytes, "normal-site event")
        kind, _key, _record_id = _record_identity(document)
        if kind != "event":
            _fail("normal-site event bytes have the wrong schema")

    @property
    def document(self) -> dict[str, Any]:
        return _parse_document(self._document_bytes, "normal-site event")

    @property
    def event_id(self) -> str:
        return _cid(self.document["h1_normal_site_event_commit_id"], "normal-site event")

    @property
    def outcome(self) -> str:
        return _nonempty(self.document["outcome"], "normal-site outcome")

    @property
    def ordinal(self) -> int:
        return _nonnegative(self.document["ordinal"], "normal-site ordinal")

    @property
    def canonical_bytes(self) -> bytes:
        return bytes(self._document_bytes)


@dataclass(frozen=True, slots=True)
class H1NormalPrefixSnapshotV1:
    _issuer: InitVar[object]
    _document_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SNAPSHOT_ISSUER or type(self._document_bytes) is not bytes:
            _fail("normal-prefix snapshot is caller-minted")
        document = _parse_document(self._document_bytes, "normal-prefix snapshot")
        claimed = _cid(
            document.pop("h1_normal_prefix_snapshot_id", None),
            "normal-prefix snapshot",
        )
        if _content_id(SNAPSHOT_DOMAIN, document) != claimed:
            _fail("normal-prefix snapshot identity is invalid")

    @property
    def document(self) -> dict[str, Any]:
        return _parse_document(self._document_bytes, "normal-prefix snapshot")

    @property
    def snapshot_id(self) -> str:
        return _cid(self.document["h1_normal_prefix_snapshot_id"], "normal-prefix snapshot")

    @property
    def status(self) -> H1NormalPrefixStatusV1:
        return H1NormalPrefixStatusV1(self.document["status"])

    @property
    def canonical_bytes(self) -> bytes:
        return bytes(self._document_bytes)


@dataclass(slots=True)
class H1PhaseAwareNormalPrefixLeaseV1:
    _issuer: InitVar[object]
    handle: H1NormalPrefixHandleV1
    phase_handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1
    owner: owner_v4.H1SharedCapOwnerV4WalHandle
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1
    dispatch_profile: dispatch_v1.H1LifecycleDispatchProfileV1
    _phase_root_fd: int = field(repr=False)
    _phase_directory_fd: int = field(repr=False)
    _phase_lock_fd: int = field(repr=False)
    _phase_cursor_fd: int = field(repr=False)
    _gate_directory_fd: int = field(repr=False)
    _gate_lock_fd: int = field(repr=False)
    _journal_root_fd: int = field(repr=False)
    _journal_directory_fd: int = field(repr=False)
    _journal_lock_fd: int = field(repr=False)
    _journal_cursor_fd: int = field(repr=False)
    _owner_pid: int = field(repr=False)
    _owner_thread_id: int = field(repr=False)
    _active: bool = field(default=True, repr=False)
    _site_consumed: bool = field(default=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _LEASE_ISSUER:
            _fail("phase-aware normal-prefix lease is caller-minted")
        for descriptor in (
            self._phase_root_fd,
            self._phase_directory_fd,
            self._phase_lock_fd,
            self._phase_cursor_fd,
            self._gate_directory_fd,
            self._gate_lock_fd,
            self._journal_root_fd,
            self._journal_directory_fd,
            self._journal_lock_fd,
            self._journal_cursor_fd,
        ):
            if os.get_inheritable(descriptor):
                _fail("phase-aware lease descriptor is inheritable")

    def __reduce__(self) -> NoReturn:
        _fail("phase-aware normal-prefix lease is not serializable")


@dataclass(slots=True)
class _JournalState:
    intents: list[dict[str, Any]]
    callbacks: dict[int, dict[str, Any]]
    events: list[dict[str, Any]]
    expected_records: list[tuple[str, dict[str, Any], str]]

    @property
    def next_ordinal(self) -> int:
        return len(self.events) + 1

    @property
    def failed(self) -> bool:
        return bool(self.events and self.events[-1]["outcome"] != "SUCCESS")

    @property
    def dangling_intent(self) -> dict[str, Any] | None:
        if len(self.intents) == len(self.events) + 1:
            return self.intents[-1]
        return None


def inspect_h1_normal_prefix_semantic_closure_candidate_v1() -> dict[str, Any]:
    _require_dependency_namespace_unchanged(full=True)
    self_path = Path(__file__).resolve(strict=True)
    sources = [
        {
            "module": __name__,
            "source_sha256": hashlib.sha256(self_path.read_bytes()).hexdigest(),
        }
    ]
    for module in _SOURCE_MODULES.values():
        path = Path(module.__file__).resolve(strict=True)
        sources.append(
            {
                "module": module.__name__,
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    payload = {
        "schema": "acfqp.k7_h1_normal_prefix_semantic_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "authority_stage": AUTHORITY_STAGE,
        "source_components": sources,
        "dependency_symbol_descriptors": {
            role: loads_canonical_json(descriptor_bytes)
            for role, descriptor_bytes in sorted(
                _IMPORT_DEPENDENCY_DESCRIPTOR_BYTES.items()
            )
        },
        "transitive_dependency_semantics": (
            loads_canonical_json(_IMPORT_TRANSITIVE_DEPENDENCY_SEMANTICS_BYTES)
        ),
        "domain_registry": dict(domains_v3.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V3),
        "dependency_namespace_rechecked_before_every_lease": True,
        "execution_uses_import_captured_dependency_view": True,
        "historical_public_dispatcher_not_called": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "h1_normal_prefix_semantic_closure_id": _content_id(
            SEMANTIC_CLOSURE_DOMAIN, payload
        ),
    }


def freeze_h1_normal_prefix_spec_v1(
    base_directory: str | Path,
    *,
    phase_handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    dispatch_profile: dispatch_v1.H1LifecycleDispatchProfileV1,
) -> H1NormalPrefixSpecV1:
    if (
        type(phase_handle) is not phase_v1.H1AttemptExecutionPhaseOwnerV1Handle
        or type(rejection_gate) is not rejection_v1.H1AttemptRejectionGateHandleV1
        or type(owner) is not owner_v4.H1SharedCapOwnerV4WalHandle
        or type(bundle) is not dispatch_v1.H1AnchoredLifecycleDispatchBundleV1
        or type(dispatch_profile) is not dispatch_v1.H1LifecycleDispatchProfileV1
    ):
        _fail("normal-prefix spec requires exact issuer-owned inputs")
    phase_payload = phase_handle.spec.payload
    if (
        phase_payload["h1_attempt_rejection_gate_id"] != rejection_gate.spec.gate_id
        or phase_payload["logical_occurrence_id"] != dispatch_profile.logical_occurrence_id
        or phase_payload["route_attempt_id"] != dispatch_profile.route_attempt_id
        or phase_payload["h1_anchored_lifecycle_program_id"]
        != bundle.program.anchored_program_id
        or phase_payload["h1_anchored_lifecycle_handler_registry_id"]
        != bundle.registry.registry_id
        or dispatch_profile.owner_runtime_id != owner.runtime_id
        or dispatch_profile.owner_profile_id != owner.profile.profile_id
        or dispatch_profile.anchored_program_id != bundle.program.anchored_program_id
        or dispatch_profile.handler_registry_id != bundle.registry.registry_id
        or owner.profile.route_attempt_id != dispatch_profile.route_attempt_id
    ):
        _fail("normal-prefix spec inputs cross identity boundaries")
    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(owner)
    if (
        replay["pending_cursor"]["kind"] != "NOT_APPLICABLE"
        or replay["journal_sequence"] != 7
        or replay["reservation_count"] != 1
        or replay["settlement_count"] != 1
        or any(replay["charged_values"].values())
        or any(replay["outstanding_values"].values())
        or replay["conservative_settlement_count"] != 0
        or replay["observed_overrun_count"] != 0
        or replay["gate_owner_join_status"] != "OPEN_NO_REJECTION"
        or replay["new_work_allowed"] is not True
    ):
        _fail("normal-prefix spec requires a fresh V4-activated Owner journal")
    base = Path(base_directory).resolve(strict=True)
    metadata = base.stat()
    if not stat.S_ISDIR(metadata.st_mode):
        _fail("normal-prefix base is not a directory")
    if str(base) != phase_payload["phase_base_realpath"]:
        _fail("normal-prefix and attempt-phase authorities require one physical base")
    semantic_closure = inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    normal_prefix_sites = []
    for row, handler in zip(
        bundle.program.transitions[:PREFIX_END_ORDINAL],
        bundle.registry.handlers[:PREFIX_END_ORDINAL],
    ):
        normal_prefix_sites.append(
            {
                "ordinal": row["ordinal"],
                "site_key": row["site_key"],
                "phase": row["phase"],
                "operation": row["operation"],
                "from_state": row["from_state"],
                "success_state": row["success_state"],
                "handler_mode": handler["handler_mode"],
                "resource_path": dispatch_v1._resource_path(row),
                "reducer": handler["reducer"],
                "callback_required": handler["callback_required"],
                "failure_outcomes": list(dispatch_v1._failure_outcomes(row)),
                "deterministic_dispatch_operation_id": dispatch_v1._operation_id(
                    dispatch_profile.profile_id,
                    row["ordinal"],
                    row["site_key"],
                ),
                "owner_reservation_operation_id": (
                    dispatch_v1._owner_reservation_operation_id(
                        dispatch_profile.profile_id, row
                    )
                ),
                "native_evidence_source_id": dispatch_v1._evidence_source_id(
                    dispatch_profile.profile_id,
                    row["ordinal"],
                    row["site_key"],
                ),
                "reservation_upper": dispatch_profile.site_operands[row["site_key"]],
            }
        )
    payload = {
        "schema": "acfqp.k7_h1_normal_prefix_spec.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "authority_stage": AUTHORITY_STAGE,
        "logical_occurrence_id": dispatch_profile.logical_occurrence_id,
        "route_attempt_id": dispatch_profile.route_attempt_id,
        "decision_point_id": dispatch_profile.decision_point_id,
        "transaction_id": dispatch_profile.transaction_id,
        "h1_attempt_execution_phase_spec_id": phase_handle.spec.spec_id,
        "h1_attempt_phase_allocation_id": phase_handle.allocation_id,
        "h1_attempt_rejection_gate_id": rejection_gate.spec.gate_id,
        "h1_shared_cap_profile_core_v3_id": owner.profile.profile_id,
        "h1_shared_cap_owner_v3_runtime_id": owner.runtime_id,
        "h1_shared_cap_owner_v4_wal_binding_id": owner.binding_id,
        "h1_lifecycle_dispatch_profile_id": dispatch_profile.profile_id,
        "h1_anchored_lifecycle_program_id": bundle.program.anchored_program_id,
        "h1_anchored_lifecycle_handler_registry_id": bundle.registry.registry_id,
        "h1_normal_prefix_semantic_closure_id": semantic_closure[
            "h1_normal_prefix_semantic_closure_id"
        ],
        "normal_prefix_first_ordinal": 1,
        "normal_prefix_last_ordinal": PREFIX_END_ORDINAL,
        "normal_prefix_site_contracts": normal_prefix_sites,
        "owner_baseline_journal_sequence": replay["journal_sequence"],
        "owner_baseline_journal_head_id": replay["journal_head_id"],
        "normal_prefix_base_realpath": str(base),
        "normal_prefix_base_device": metadata.st_dev,
        "normal_prefix_base_inode": metadata.st_ino,
        "lock_order": "PHASE_EX_THEN_GATE_EX_THEN_JOURNAL_EX_THEN_OWNER_EX_THEN_NATIVE",
        "v4_wal_activated_before_first_site": True,
        "historical_dispatcher_reentry_forbidden": True,
        "callback_result_durable_before_settlement": True,
        "dangling_native_cell_never_reexecutes_callback": True,
        "success_is_prefix_only": True,
        "cleanup_execution_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1NormalPrefixSpecV1(_SPEC_ISSUER, canonical_json_bytes(payload))


def _allocation_name(route_attempt_id: str) -> str:
    return f"{_ALLOCATION_PREFIX}{route_attempt_id}.json"


def _allocation_document(
    spec: H1NormalPrefixSpecV1,
    *,
    root_path: Path,
    root_metadata: os.stat_result,
    root_lock_metadata: os.stat_result,
    high_water_token_metadata: os.stat_result,
    journal_path: Path,
    journal_metadata: os.stat_result,
    lock_metadata: os.stat_result,
    cursor_metadata: os.stat_result,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_normal_prefix_allocation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_normal_prefix_spec_id": spec.spec_id,
        "route_attempt_id": spec.payload["route_attempt_id"],
        "normal_prefix_root_realpath": str(root_path),
        "normal_prefix_root_device": root_metadata.st_dev,
        "normal_prefix_root_inode": root_metadata.st_ino,
        "root_allocation_lock_device": root_lock_metadata.st_dev,
        "root_allocation_lock_inode": root_lock_metadata.st_ino,
        "high_water_token_device": high_water_token_metadata.st_dev,
        "high_water_token_inode": high_water_token_metadata.st_ino,
        "normal_prefix_journal_realpath": str(journal_path),
        "normal_prefix_journal_device": journal_metadata.st_dev,
        "normal_prefix_journal_inode": journal_metadata.st_ino,
        "normal_prefix_lock_device": lock_metadata.st_dev,
        "normal_prefix_lock_inode": lock_metadata.st_ino,
        "normal_prefix_cursor_device": cursor_metadata.st_dev,
        "normal_prefix_cursor_inode": cursor_metadata.st_ino,
        "single_attempt_allocation": True,
        "root_record_seals_required": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "h1_normal_prefix_allocation_id": _content_id(ALLOCATION_DOMAIN, payload),
    }


def _parse_allocation_document(
    raw: bytes,
    spec: H1NormalPrefixSpecV1,
) -> tuple[dict[str, Any], str]:
    document = _parse_document(raw, "normal-prefix allocation")
    if frozenset(document) != _ALLOCATION_FIELDS:
        _protocol("normal-prefix allocation fields are not exact")
    payload = dict(document)
    claimed = _cid(
        payload.pop("h1_normal_prefix_allocation_id", None),
        "normal-prefix allocation",
    )
    expected_root = (
        Path(spec.payload["normal_prefix_base_realpath"]) / _ROOT_NAME
    ).resolve(strict=True)
    expected_journal = (expected_root / spec.payload["route_attempt_id"]).resolve(
        strict=True
    )
    for key in (
        "normal_prefix_root_device",
        "normal_prefix_root_inode",
        "root_allocation_lock_device",
        "root_allocation_lock_inode",
        "high_water_token_device",
        "high_water_token_inode",
        "normal_prefix_journal_device",
        "normal_prefix_journal_inode",
        "normal_prefix_lock_device",
        "normal_prefix_lock_inode",
        "normal_prefix_cursor_device",
        "normal_prefix_cursor_inode",
    ):
        _nonnegative(document[key], "normal-prefix allocation " + key)
    if (
        _content_id(ALLOCATION_DOMAIN, payload) != claimed
        or document["schema"] != "acfqp.k7_h1_normal_prefix_allocation.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["h1_normal_prefix_spec_id"] != spec.spec_id
        or document["route_attempt_id"] != spec.payload["route_attempt_id"]
        or document["normal_prefix_root_realpath"] != str(expected_root)
        or document["normal_prefix_journal_realpath"] != str(expected_journal)
        or document["single_attempt_allocation"] is not True
        or document["root_record_seals_required"] is not True
        or document["official_execution_allowed"] is not False
    ):
        _protocol("normal-prefix allocation semantics changed")
    return document, claimed


def _cursor_payload(
    spec_id: str,
    *,
    sequence: int,
    previous_id: str | None,
    ordinal: int,
    record_kind: str,
    record_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_normal_prefix_cursor_record.v1",
        "schema_version": SCHEMA_VERSION,
        "h1_normal_prefix_spec_id": spec_id,
        "sequence": sequence,
        "previous_normal_prefix_cursor_record_id": (
            previous_id if previous_id is not None else _typed_null("CURSOR_GENESIS")
        ),
        "ordinal": ordinal,
        "record_kind": record_kind,
        "record_id": record_id if record_id is not None else _typed_null("NO_SITE_RECORD"),
    }
    return {
        **payload,
        "h1_normal_prefix_cursor_record_id": _content_id(CURSOR_DOMAIN, payload),
    }


def _cursor_genesis(spec_id: str) -> dict[str, Any]:
    return _cursor_payload(
        spec_id,
        sequence=0,
        previous_id=None,
        ordinal=0,
        record_kind="GENESIS",
        record_id=None,
    )


def _high_water_token_name(attempt: str) -> str:
    return f"{_HIGH_WATER_TOKEN_PREFIX}{attempt}"


def _high_water_token_bytes(spec_id: str, attempt: str) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "acfqp.k7_h1_normal_prefix_high_water_token.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_normal_prefix_spec_id": spec_id,
            "route_attempt_id": attempt,
            "purpose": "INODE_BOUND_MONOTONIC_NORMAL_PREFIX_HIGH_WATER",
        }
    )


def _high_water_state_name(attempt: str, sequence: int, cursor_id: str) -> str:
    return (
        f"{_HIGH_WATER_STATE_PREFIX}{attempt}-{sequence:04d}-"
        f"{_cid(cursor_id, 'normal-prefix high-water cursor')}"
    )


def _link_high_water_state(
    root_fd: int,
    *,
    attempt: str,
    sequence: int,
    cursor_id: str,
) -> str:
    name = _high_water_state_name(attempt, sequence, cursor_id)
    try:
        os.link(
            _high_water_token_name(attempt),
            name,
            src_dir_fd=root_fd,
            dst_dir_fd=root_fd,
            follow_symlinks=False,
        )
        os.fsync(root_fd)
    except FileExistsError:
        pass
    token_metadata = os.stat(
        _high_water_token_name(attempt), dir_fd=root_fd, follow_symlinks=False
    )
    state_metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(state_metadata.st_mode)
        or stat.S_IMODE(state_metadata.st_mode) != 0o600
        or (token_metadata.st_dev, token_metadata.st_ino)
        != (state_metadata.st_dev, state_metadata.st_ino)
    ):
        _protocol("normal-prefix high-water state is not the exact token hard link")
    return name


def _unlink_high_water_state(root_fd: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=root_fd)
        os.fsync(root_fd)
    except FileNotFoundError:
        pass


def _high_water_states(
    root_fd: int,
    handle: H1NormalPrefixHandleV1,
) -> list[tuple[int, str, str]]:
    token_name = _high_water_token_name(handle.route_attempt_id)
    state_prefix = f"{_HIGH_WATER_STATE_PREFIX}{handle.route_attempt_id}-"
    states: list[tuple[int, str, str]] = []
    observed_links = 0
    for name in os.listdir(root_fd):
        if name != token_name and not name.startswith(state_prefix):
            continue
        metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if (metadata.st_dev, metadata.st_ino) != (
            handle.high_water_token_device,
            handle.high_water_token_inode,
        ):
            _protocol("normal-prefix high-water namespace crossed an inode")
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            _protocol("normal-prefix high-water link is not private and regular")
        observed_links += 1
        if name == token_name:
            continue
        match = _HIGH_WATER_STATE_PATTERN.fullmatch(name)
        if match is None or match.group("attempt") != handle.route_attempt_id:
            _protocol("normal-prefix high-water state name is malformed")
        states.append(
            (
                int(match.group("sequence")),
                _cid(match.group("cursor"), "normal-prefix high-water cursor"),
                name,
            )
        )
    token_fd = _open_regular_at(root_fd, token_name, flags=os.O_RDONLY)
    try:
        metadata = os.fstat(token_fd)
        raw = os.pread(token_fd, 4096, 0)
        if (
            (metadata.st_dev, metadata.st_ino)
            != (handle.high_water_token_device, handle.high_water_token_inode)
            or not hmac.compare_digest(
                raw,
                _high_water_token_bytes(
                    handle.spec.spec_id, handle.route_attempt_id
                ),
            )
            or metadata.st_nlink != observed_links
        ):
            _protocol("normal-prefix high-water token changed")
    finally:
        os.close(token_fd)
    states.sort()
    if not states or len(states) > 2:
        _protocol("normal-prefix high-water frontier is absent or nonlocal")
    if len(states) == 2 and states[1][0] != states[0][0] + 1:
        _protocol("normal-prefix high-water frontier has a sequence gap")
    return states


def initialize_h1_normal_prefix_journal_v1(
    spec: H1NormalPrefixSpecV1,
) -> H1NormalPrefixHandleV1:
    if type(spec) is not H1NormalPrefixSpecV1:
        _fail("normal-prefix initialization requires one exact spec")
    payload = spec.payload
    base = Path(payload["normal_prefix_base_realpath"])
    base_fd = _open_directory(base)
    root_fd = root_lock_fd = high_water_token_fd = journal_fd = lock_fd = cursor_fd = -1
    root_lock_held = journal_lock_held = False
    try:
        base_metadata = os.fstat(base_fd)
        if (base_metadata.st_dev, base_metadata.st_ino) != (
            payload["normal_prefix_base_device"],
            payload["normal_prefix_base_inode"],
        ):
            _fail("normal-prefix base inode changed")
        try:
            os.mkdir(_ROOT_NAME, 0o700, dir_fd=base_fd)
            os.fsync(base_fd)
        except FileExistsError:
            pass
        root_fd = _open_directory_at(base_fd, _ROOT_NAME)
        root_metadata = os.fstat(root_fd)
        if not stat.S_ISDIR(root_metadata.st_mode) or stat.S_IMODE(root_metadata.st_mode) != 0o700:
            _fail("normal-prefix root is not one private directory")
        try:
            root_lock_fd = _open_regular_at(
                root_fd,
                _ROOT_LOCK,
                flags=os.O_RDWR | os.O_CREAT | os.O_EXCL,
                mode=0o600,
            )
            os.fsync(root_fd)
        except ConstructionK7H1PhaseAwareNormalPrefixV1Error:
            root_lock_fd = _open_regular_at(root_fd, _ROOT_LOCK, flags=os.O_RDWR)
        _require_mode(os.fstat(root_lock_fd), 0o600, "normal-prefix root lock")
        fcntl.flock(root_lock_fd, fcntl.LOCK_EX)
        root_lock_held = True
        _cleanup_temps(root_fd)
        attempt = payload["route_attempt_id"]
        token_name = _high_water_token_name(attempt)
        token_raw = _high_water_token_bytes(spec.spec_id, attempt)
        existing_token = _read_file(root_fd, token_name)
        if existing_token is None:
            if not _publish_new(root_fd, token_name, token_raw, mode=0o600):
                _fail("normal-prefix high-water token publication conflicted")
        elif not hmac.compare_digest(existing_token, token_raw):
            _fail("normal-prefix high-water token changed")
        high_water_token_fd = _open_regular_at(root_fd, token_name, flags=os.O_RDONLY)
        _require_mode(
            os.fstat(high_water_token_fd), 0o600, "normal-prefix high-water token"
        )
        genesis = _cursor_genesis(spec.spec_id)
        try:
            os.mkdir(attempt, 0o700, dir_fd=root_fd)
            os.fsync(root_fd)
        except FileExistsError:
            pass
        journal_fd = _open_directory_at(root_fd, attempt)
        journal_metadata = os.fstat(journal_fd)
        if not stat.S_ISDIR(journal_metadata.st_mode) or stat.S_IMODE(journal_metadata.st_mode) != 0o700:
            _fail("normal-prefix attempt directory is not private")
        try:
            lock_fd = _open_regular_at(
                journal_fd,
                _LOCK_FILE,
                flags=os.O_RDWR | os.O_CREAT | os.O_EXCL,
                mode=0o600,
            )
            os.fsync(journal_fd)
        except ConstructionK7H1PhaseAwareNormalPrefixV1Error:
            lock_fd = _open_regular_at(journal_fd, _LOCK_FILE, flags=os.O_RDWR)
        _require_mode(os.fstat(lock_fd), 0o600, "normal-prefix lock")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        journal_lock_held = True
        _cleanup_temps(journal_fd)
        spec_raw = canonical_json_bytes(spec.to_document())
        existing = _read_file(journal_fd, _SPEC_FILE)
        if existing is None:
            if not _publish_new(journal_fd, _SPEC_FILE, spec_raw):
                _fail("normal-prefix spec publication conflicted")
        elif not hmac.compare_digest(existing, spec_raw):
            _fail("route attempt already has a different normal-prefix spec")
        cursor_raw = _read_file(journal_fd, _CURSOR_FILE)
        if cursor_raw is None:
            genesis_raw = canonical_json_bytes(genesis) + b"\n"
            if not _publish_new(journal_fd, _CURSOR_FILE, genesis_raw, mode=0o600):
                _fail("normal-prefix cursor genesis publication conflicted")
        cursor_fd = _open_regular_at(journal_fd, _CURSOR_FILE, flags=os.O_RDWR)
        _require_mode(os.fstat(cursor_fd), 0o600, "normal-prefix cursor")
        state_prefix = f"{_HIGH_WATER_STATE_PREFIX}{attempt}-"
        state_names = [
            name for name in os.listdir(root_fd) if name.startswith(state_prefix)
        ]
        existing_allocation_before_bootstrap = _read_file(
            root_fd, _allocation_name(attempt)
        )
        cursor_rows, tail, _complete_length = _read_cursor_locked(
            cursor_fd, spec.spec_id
        )
        pristine_bootstrap = (
            not tail
            and cursor_rows == [genesis]
            and not _record_files(journal_fd)
            and not _root_seals_for_attempt(root_fd, attempt)
        )
        expected_genesis_state = _high_water_state_name(
            attempt, 0, genesis["h1_normal_prefix_cursor_record_id"]
        )
        if existing_allocation_before_bootstrap is None:
            if not pristine_bootstrap or tuple(sorted(state_names)) not in {
                (),
                (expected_genesis_state,),
            }:
                _fail("normal-prefix allocation disappeared after journal progress")
            _link_high_water_state(
                root_fd,
                attempt=attempt,
                sequence=0,
                cursor_id=genesis["h1_normal_prefix_cursor_record_id"],
            )
        elif not state_names:
            _fail("normal-prefix high-water state disappeared after allocation")
        root_path = (base / _ROOT_NAME).resolve(strict=True)
        journal_path = (root_path / attempt).resolve(strict=True)
        allocation = _allocation_document(
            spec,
            root_path=root_path,
            root_metadata=root_metadata,
            root_lock_metadata=os.fstat(root_lock_fd),
            high_water_token_metadata=os.fstat(high_water_token_fd),
            journal_path=journal_path,
            journal_metadata=journal_metadata,
            lock_metadata=os.fstat(lock_fd),
            cursor_metadata=os.fstat(cursor_fd),
        )
        allocation_raw = canonical_json_bytes(allocation)
        allocation_name = _allocation_name(attempt)
        existing_allocation = existing_allocation_before_bootstrap
        if existing_allocation is None:
            if not _publish_new(root_fd, allocation_name, allocation_raw):
                _fail("normal-prefix allocation publication conflicted")
        elif not hmac.compare_digest(existing_allocation, allocation_raw):
            _fail("normal-prefix allocation split-brain detected")
        handle = H1NormalPrefixHandleV1(
            _HANDLE_ISSUER,
            spec,
            allocation["h1_normal_prefix_allocation_id"],
            str(root_path),
            root_metadata.st_dev,
            root_metadata.st_ino,
            os.fstat(root_lock_fd).st_dev,
            os.fstat(root_lock_fd).st_ino,
            os.fstat(high_water_token_fd).st_dev,
            os.fstat(high_water_token_fd).st_ino,
            str(journal_path),
            journal_metadata.st_dev,
            journal_metadata.st_ino,
            os.fstat(lock_fd).st_dev,
            os.fstat(lock_fd).st_ino,
            os.fstat(cursor_fd).st_dev,
            os.fstat(cursor_fd).st_ino,
        )
    finally:
        if cursor_fd >= 0:
            os.close(cursor_fd)
        if lock_fd >= 0:
            if journal_lock_held:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        if journal_fd >= 0:
            os.close(journal_fd)
        if root_lock_fd >= 0:
            if root_lock_held:
                fcntl.flock(root_lock_fd, fcntl.LOCK_UN)
            os.close(root_lock_fd)
        if high_water_token_fd >= 0:
            os.close(high_water_token_fd)
        if root_fd >= 0:
            os.close(root_fd)
        os.close(base_fd)
    replay_h1_normal_prefix_journal_v1(handle)
    return handle


def open_h1_normal_prefix_journal_v1(
    spec: H1NormalPrefixSpecV1,
) -> H1NormalPrefixHandleV1:
    if type(spec) is not H1NormalPrefixSpecV1:
        _fail("normal-prefix open requires one exact spec")
    payload = spec.payload
    root = Path(payload["normal_prefix_base_realpath"]) / _ROOT_NAME
    root_fd = _open_directory(root.resolve(strict=True))
    root_lock_fd = high_water_token_fd = journal_fd = lock_fd = cursor_fd = -1
    try:
        root_metadata = os.fstat(root_fd)
        root_lock_fd = _open_regular_at(root_fd, _ROOT_LOCK, flags=os.O_RDWR)
        fcntl.flock(root_lock_fd, fcntl.LOCK_SH)
        attempt = payload["route_attempt_id"]
        high_water_token_fd = _open_regular_at(
            root_fd, _high_water_token_name(attempt), flags=os.O_RDONLY
        )
        journal_fd = _open_directory_at(root_fd, attempt)
        journal_metadata = os.fstat(journal_fd)
        lock_fd = _open_regular_at(journal_fd, _LOCK_FILE, flags=os.O_RDWR)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        cursor_fd = _open_regular_at(journal_fd, _CURSOR_FILE, flags=os.O_RDWR)
        allocation_raw = _read_file(root_fd, _allocation_name(attempt))
        spec_raw = _read_file(journal_fd, _SPEC_FILE)
        if allocation_raw is None or spec_raw != canonical_json_bytes(spec.to_document()):
            _fail("normal-prefix allocation or spec is absent")
        allocation, claimed = _parse_allocation_document(allocation_raw, spec)
        if (
            allocation["h1_normal_prefix_spec_id"] != spec.spec_id
            or allocation["normal_prefix_root_device"] != root_metadata.st_dev
            or allocation["normal_prefix_root_inode"] != root_metadata.st_ino
            or allocation["root_allocation_lock_device"]
            != os.fstat(root_lock_fd).st_dev
            or allocation["root_allocation_lock_inode"]
            != os.fstat(root_lock_fd).st_ino
            or allocation["high_water_token_device"]
            != os.fstat(high_water_token_fd).st_dev
            or allocation["high_water_token_inode"]
            != os.fstat(high_water_token_fd).st_ino
            or allocation["normal_prefix_journal_device"] != journal_metadata.st_dev
            or allocation["normal_prefix_journal_inode"] != journal_metadata.st_ino
            or allocation["normal_prefix_lock_device"] != os.fstat(lock_fd).st_dev
            or allocation["normal_prefix_lock_inode"] != os.fstat(lock_fd).st_ino
            or allocation["normal_prefix_cursor_device"] != os.fstat(cursor_fd).st_dev
            or allocation["normal_prefix_cursor_inode"] != os.fstat(cursor_fd).st_ino
        ):
            _fail("normal-prefix physical allocation changed")
        handle = H1NormalPrefixHandleV1(
            _HANDLE_ISSUER,
            spec,
            claimed,
            str(root.resolve(strict=True)),
            root_metadata.st_dev,
            root_metadata.st_ino,
            os.fstat(root_lock_fd).st_dev,
            os.fstat(root_lock_fd).st_ino,
            os.fstat(high_water_token_fd).st_dev,
            os.fstat(high_water_token_fd).st_ino,
            str((root / attempt).resolve(strict=True)),
            journal_metadata.st_dev,
            journal_metadata.st_ino,
            os.fstat(lock_fd).st_dev,
            os.fstat(lock_fd).st_ino,
            os.fstat(cursor_fd).st_dev,
            os.fstat(cursor_fd).st_ino,
        )
    finally:
        if cursor_fd >= 0:
            os.close(cursor_fd)
        if lock_fd >= 0:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        if journal_fd >= 0:
            os.close(journal_fd)
        if high_water_token_fd >= 0:
            os.close(high_water_token_fd)
        if root_lock_fd >= 0:
            fcntl.flock(root_lock_fd, fcntl.LOCK_UN)
            os.close(root_lock_fd)
        os.close(root_fd)
    replay_h1_normal_prefix_journal_v1(handle)
    return handle


def _record_identity(document: dict[str, Any]) -> tuple[str, str, str]:
    schema = document.get("schema")
    if schema == "acfqp.k7_h1_normal_site_intent.v1":
        domain, key, kind, fields = (
            INTENT_DOMAIN,
            "h1_normal_site_intent_id",
            "intent",
            _INTENT_FIELDS,
        )
    elif schema == "acfqp.k7_h1_normal_site_callback_result.v1":
        domain, key, kind, fields = (
            CALLBACK_DOMAIN,
            "h1_normal_site_callback_result_id",
            "callback",
            _CALLBACK_FIELDS,
        )
    elif schema == "acfqp.k7_h1_normal_site_event_commit.v1":
        domain, key, kind, fields = (
            EVENT_DOMAIN,
            "h1_normal_site_event_commit_id",
            "event",
            _EVENT_FIELDS,
        )
    else:
        _protocol("normal-prefix journal contains an unknown record schema")
    if (
        frozenset(document) != fields
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != PROFILE_KEY
    ):
        _protocol("normal-prefix journal record fields or contract changed")
    if kind == "intent" and (
        document["durable_before_owner_admission"] is not True
        or document["callback_retry_forbidden_after_native_cell"] is not True
        or document["site_authority_single_use_per_lease"] is not True
        or document["attempt_closure_issued"] is not False
        or document["terminal_classification_issued"] is not False
        or document["certificate_issued"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _protocol("normal-site intent changed a locked claim field")
    if kind == "callback" and (
        document["durable_before_owner_settlement"] is not True
        or document["native_evidence_authority_present"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _protocol("normal-site callback result changed a locked claim field")
    if kind == "event" and (
        document["event_durable_exactly_once"] is not True
        or document["attempt_closure_issued"] is not False
        or document["terminal_classification_issued"] is not False
        or document["certificate_issued"] is not False
        or document["infeasibility_certified"] is not False
        or document["formal_counter_records_issued"] is not False
        or document["formal_work_vector_issued"] is not False
        or document["formal_comparison_vector_issued"] is not False
        or document["formal_v7_route_authority_present"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _protocol("normal-site event changed a locked claim field")
    claimed = _cid(document.get(key), f"normal-prefix {kind} record")
    payload = dict(document)
    del payload[key]
    if _content_id(domain, payload) != claimed:
        _protocol("normal-prefix journal record identity is invalid")
    return kind, key, claimed


def _verify_callback_replay_shape(
    intent: Mapping[str, Any], callback: Mapping[str, Any]
) -> None:
    kind = callback["callback_result_kind"]
    native = callback["native_observed_value"]
    exception = callback["callback_exception_type"]
    count = callback["callback_invocation_count"]
    may = callback["callback_invocation_may_have_occurred"]
    no_native = _typed_null("NO_EXACT_NATIVE_VALUE")
    no_exception = _typed_null("NO_CALLBACK_EXCEPTION")
    valid = False
    if kind == "UNIT_CALLBACK_RETURNED":
        valid = (
            intent["handler_mode"]
            == dispatch_v1.H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value
            and native == no_native
            and exception == no_exception
            and count == 1
            and may is False
        )
    elif kind == "MAGNITUDE_RETURNED":
        valid = (
            intent["handler_mode"]
            == dispatch_v1.H1LifecycleHandlerModeV1.IMMEDIATE_MAGNITUDE.value
            and type(native) is int
            and native >= 0
            and exception == no_exception
            and count == 1
            and may is False
        )
    elif kind in {"CALLBACK_EXCEPTION", "INVALID_NONNEGATIVE_MAGNITUDE"}:
        valid = (
            native == no_native
            and type(exception) is str
            and bool(exception)
            and count == 1
            and may is False
        )
    elif kind == "NATIVE_CELL_WITHOUT_DURABLE_CALLBACK_RESULT":
        valid = (
            native == no_native
            and exception == "DurableCallbackResultMissingAfterNativeCell"
            and count == 0
            and may is True
        )
    if not valid:
        _protocol("normal-prefix callback result has an invalid typed shape")


def _verify_event_replay_shape(
    intent: Mapping[str, Any],
    callback: Mapping[str, Any] | None,
    event: Mapping[str, Any],
) -> None:
    inherited = {
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "ordinal",
        "site_key",
        "phase",
        "operation",
        "from_state",
        "success_state",
        "handler_mode",
        "resource_path",
        "reducer",
        "deterministic_dispatch_operation_id",
        "owner_reservation_operation_id",
        "reservation_upper",
        "owner_journal_sequence_before_site",
        "owner_journal_head_id_before_site",
    }
    if any(event[key] != intent[key] for key in inherited):
        _protocol("normal-site event changed an intent-bound semantic field")
    if callback is None:
        if event["callback_invocation_count"] != 0:
            _protocol("callback-free normal-site event charged an invocation")
        if event["outcome"] == "CAP_REJECTED_BEFORE_SIDE_EFFECT":
            if intent["expected_admission_outcome"] != "REJECTED_BEFORE_SIDE_EFFECT":
                _protocol("normal-site cap event contradicts its admission intent")
        elif not (
            intent["handler_mode"]
            == dispatch_v1.H1LifecycleHandlerModeV1.DEFERRED_ORIGIN.value
            and event["outcome"] == "SUCCESS"
        ):
            _protocol("callback-free normal-site event has invalid semantics")
        return
    _verify_callback_replay_shape(intent, callback)
    if (
        event["callback_invocation_count"] != callback["callback_invocation_count"]
        or event["callback_exception_type"] != callback["callback_exception_type"]
        or event["callback_invocation_may_have_occurred"]
        != callback["callback_invocation_may_have_occurred"]
    ):
        _protocol("normal-site event changed its callback-result semantics")
    basis, native, nominal, value_basis = _settlement_semantics_from_callback(
        intent, callback
    )
    del basis
    expected_outcome = nominal
    if callback["callback_result_kind"] == "MAGNITUDE_RETURNED" and (
        native is not None and native > intent["reservation_upper"]
    ):
        expected_outcome = "OBSERVED_UPPER_BOUND_VIOLATION"
        if expected_outcome not in intent["failure_outcomes"]:
            expected_outcome = dispatch_v1.ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
    if (
        event["outcome"] != expected_outcome
        or event["native_observed_value"]
        != (native if native is not None else _typed_null("NO_EXACT_NATIVE_VALUE"))
        or event["value_basis"] != value_basis
    ):
        _protocol("normal-site event contradicts its durable callback result")


def _record_name(ordinal: int, kind: str, record_id: str) -> str:
    return f"{ordinal:04d}-{kind}-{record_id}.json"


def _seal_name(attempt: str, ordinal: int, kind: str, record_id: str) -> str:
    return f"{_SEAL_PREFIX}{attempt}-{ordinal:04d}-{kind}-{record_id}.json"


def _verify_or_create_seal(
    root_fd: int,
    journal_fd: int,
    *,
    attempt: str,
    ordinal: int,
    kind: str,
    record_id: str,
    allow_create: bool,
) -> None:
    record_name = _record_name(ordinal, kind, record_id)
    seal_name = _seal_name(attempt, ordinal, kind, record_id)
    record_stat = os.stat(record_name, dir_fd=journal_fd, follow_symlinks=False)
    if not stat.S_ISREG(record_stat.st_mode) or stat.S_IMODE(record_stat.st_mode) != 0o400:
        _protocol("normal-prefix record is not immutable and regular")
    try:
        seal_stat = os.stat(seal_name, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        if not allow_create:
            _protocol("normal-prefix record lost its root seal")
        try:
            os.link(
                record_name,
                seal_name,
                src_dir_fd=journal_fd,
                dst_dir_fd=root_fd,
                follow_symlinks=False,
            )
            os.fsync(root_fd)
        except FileExistsError:
            pass
        seal_stat = os.stat(seal_name, dir_fd=root_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(seal_stat.st_mode)
        or stat.S_IMODE(seal_stat.st_mode) != 0o400
        or (record_stat.st_dev, record_stat.st_ino)
        != (seal_stat.st_dev, seal_stat.st_ino)
    ):
        _protocol("normal-prefix record seal is not its exact hard link")


def _publish_record_locked(
    handle: H1NormalPrefixHandleV1,
    root_fd: int,
    journal_fd: int,
    document: dict[str, Any],
) -> tuple[str, str]:
    kind, _key, record_id = _record_identity(document)
    ordinal = _nonnegative(document.get("ordinal"), "normal-prefix record ordinal")
    name = _record_name(ordinal, kind, record_id)
    raw = canonical_json_bytes(document)
    if not _publish_new(journal_fd, name, raw):
        existing = _read_file(journal_fd, name)
        if existing is None or not hmac.compare_digest(existing, raw):
            _protocol("normal-prefix record publication conflicted")
    _verify_or_create_seal(
        root_fd,
        journal_fd,
        attempt=handle.route_attempt_id,
        ordinal=ordinal,
        kind=kind,
        record_id=record_id,
        allow_create=True,
    )
    return kind, record_id


def _read_cursor_locked(
    cursor_fd: int,
    spec_id: str,
) -> tuple[list[dict[str, Any]], bytes, int]:
    os.lseek(cursor_fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        block = os.read(cursor_fd, 65536)
        if not block:
            break
        chunks.append(block)
    raw = b"".join(chunks)
    complete_length = raw.rfind(b"\n") + 1
    complete = raw[:complete_length]
    tail = raw[complete_length:]
    rows: list[dict[str, Any]] = []
    for sequence, line in enumerate(complete.splitlines(), start=0):
        row = _parse_document(line, "normal-prefix cursor row")
        claimed = _cid(
            row.get("h1_normal_prefix_cursor_record_id"),
            "normal-prefix cursor row",
        )
        payload = dict(row)
        del payload["h1_normal_prefix_cursor_record_id"]
        if (
            _content_id(CURSOR_DOMAIN, payload) != claimed
            or row.get("schema") != "acfqp.k7_h1_normal_prefix_cursor_record.v1"
            or row.get("schema_version") != SCHEMA_VERSION
            or row.get("h1_normal_prefix_spec_id") != spec_id
            or row.get("sequence") != sequence
            or row.get("previous_normal_prefix_cursor_record_id")
            != (
                rows[-1]["h1_normal_prefix_cursor_record_id"]
                if rows
                else _typed_null("CURSOR_GENESIS")
            )
        ):
            _protocol("normal-prefix cursor chain is invalid")
        rows.append(row)
    if not rows or rows[0] != _cursor_genesis(spec_id):
        _protocol("normal-prefix cursor genesis changed")
    return rows, tail, complete_length


def _append_cursor_locked(
    handle: H1NormalPrefixHandleV1,
    root_fd: int,
    cursor_fd: int,
    rows: list[dict[str, Any]],
    *,
    ordinal: int,
    kind: str,
    record_id: str,
) -> dict[str, Any]:
    row = _cursor_payload(
        handle.spec.spec_id,
        sequence=len(rows),
        previous_id=rows[-1]["h1_normal_prefix_cursor_record_id"],
        ordinal=ordinal,
        record_kind=kind.upper(),
        record_id=record_id,
    )
    current_sequence = len(rows) - 1
    current_id = rows[-1]["h1_normal_prefix_cursor_record_id"]
    next_sequence = len(rows)
    next_id = row["h1_normal_prefix_cursor_record_id"]
    states = _high_water_states(root_fd, handle)
    observed = tuple(
        (sequence, cursor_id) for sequence, cursor_id, _name in states
    )
    allowed_before = [
        (current_sequence, current_id),
    ]
    allowed_during = [
        (current_sequence, current_id),
        (next_sequence, next_id),
    ]
    if observed not in {tuple(allowed_before), tuple(allowed_during)}:
        _protocol("normal-prefix high-water is not at the exact cursor append edge")
    next_state_name = _link_high_water_state(
        root_fd,
        attempt=handle.route_attempt_id,
        sequence=next_sequence,
        cursor_id=next_id,
    )
    os.lseek(cursor_fd, 0, os.SEEK_END)
    _write_all(cursor_fd, canonical_json_bytes(row) + b"\n")
    os.fsync(cursor_fd)
    for _sequence, _cursor_id, name in _high_water_states(root_fd, handle):
        if name != next_state_name:
            _unlink_high_water_state(root_fd, name)
    rows.append(row)
    return row


def _record_files(journal_fd: int) -> list[tuple[int, str, str, str]]:
    result: list[tuple[int, str, str, str]] = []
    allowed_static = {_SPEC_FILE, _LOCK_FILE, _CURSOR_FILE}
    for name in os.listdir(journal_fd):
        if name in allowed_static or name.startswith(_TEMP_PREFIX):
            continue
        match = _RECORD_PATTERN.fullmatch(name)
        if match is None:
            _protocol("normal-prefix journal contains an unknown entry")
        result.append(
            (
                int(match.group("ordinal")),
                match.group("kind"),
                match.group("record"),
                name,
            )
        )
    rank = {"intent": 0, "callback": 1, "event": 2}
    result.sort(key=lambda row: (row[0], rank[row[1]]))
    return result


def _root_seals_for_attempt(root_fd: int, attempt: str) -> list[tuple[int, str, str, str]]:
    rows: list[tuple[int, str, str, str]] = []
    for name in os.listdir(root_fd):
        if name == _ROOT_LOCK or name.startswith(_TEMP_PREFIX):
            continue
        if re.fullmatch(r"[0-9a-f]{64}", name):
            metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
                _protocol("normal-prefix root attempt entry is not private directory")
            continue
        if name.startswith(_ALLOCATION_PREFIX):
            if re.fullmatch(r"allocation-[0-9a-f]{64}\.json", name) is None:
                _protocol("normal-prefix root contains a malformed allocation entry")
            metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o400:
                _protocol("normal-prefix allocation entry is not immutable")
            continue
        if name.startswith(_HIGH_WATER_TOKEN_PREFIX):
            if re.fullmatch(r"cursor-token-[0-9a-f]{64}", name) is None:
                _protocol("normal-prefix root contains a malformed high-water token")
            metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
                _protocol("normal-prefix high-water token is not private and regular")
            continue
        if name.startswith(_HIGH_WATER_STATE_PREFIX):
            if _HIGH_WATER_STATE_PATTERN.fullmatch(name) is None:
                _protocol("normal-prefix root contains a malformed high-water state")
            metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
                _protocol("normal-prefix high-water state is not private and regular")
            continue
        match = _SEAL_PATTERN.fullmatch(name)
        if match is None:
            _protocol("normal-prefix root contains an unknown entry")
        if match.group("attempt") == attempt:
            rows.append(
                (
                    int(match.group("ordinal")),
                    match.group("kind"),
                    match.group("record"),
                    name,
                )
            )
    rank = {"intent": 0, "callback": 1, "event": 2}
    rows.sort(key=lambda row: (row[0], rank[row[1]]))
    return rows


def _restore_sealed_records_locked(
    handle: H1NormalPrefixHandleV1,
    root_fd: int,
    journal_fd: int,
) -> None:
    files = {(o, k, r) for o, k, r, _ in _record_files(journal_fd)}
    for ordinal, kind, record_id, seal_name in _root_seals_for_attempt(
        root_fd, handle.route_attempt_id
    ):
        key = (ordinal, kind, record_id)
        if key in files:
            continue
        name = _record_name(ordinal, kind, record_id)
        try:
            os.link(
                seal_name,
                name,
                src_dir_fd=root_fd,
                dst_dir_fd=journal_fd,
                follow_symlinks=False,
            )
            os.fsync(journal_fd)
        except FileExistsError:
            pass


def _replay_journal_locked(
    handle: H1NormalPrefixHandleV1,
    root_fd: int,
    journal_fd: int,
    cursor_fd: int,
    *,
    repair: bool,
) -> _JournalState:
    if repair:
        _cleanup_temps(journal_fd)
    elif any(name.startswith(_TEMP_PREFIX) for name in os.listdir(journal_fd)):
        _protocol("normal-prefix read-only replay refuses an orphan temp")
    cursor_rows, tail, complete_length = _read_cursor_locked(
        cursor_fd, handle.spec.spec_id
    )
    committed_record_count = len(cursor_rows) - 1
    if repair:
        _restore_sealed_records_locked(handle, root_fd, journal_fd)
    else:
        present = {(o, k, r) for o, k, r, _ in _record_files(journal_fd)}
        sealed = {
            (o, k, r)
            for o, k, r, _ in _root_seals_for_attempt(
                root_fd, handle.route_attempt_id
            )
        }
        if not sealed.issubset(present):
            _protocol(
                "normal-prefix read-only replay refuses sealed-record restoration"
            )
    files = _record_files(journal_fd)
    intents: list[dict[str, Any]] = []
    callbacks: dict[int, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    expected: list[tuple[str, dict[str, Any], str]] = []
    previous_event: str | None = None
    by_ordinal: dict[int, list[tuple[str, str, str]]] = {}
    for ordinal, kind, record_id, name in files:
        by_ordinal.setdefault(ordinal, []).append((kind, record_id, name))
    if by_ordinal and sorted(by_ordinal) != list(range(1, max(by_ordinal) + 1)):
        _protocol("normal-prefix journal has an ordinal gap")
    for ordinal in sorted(by_ordinal):
        if ordinal > PREFIX_END_ORDINAL:
            _protocol("normal-prefix journal contains an out-of-scope ordinal")
        rows = by_ordinal[ordinal]
        kinds = [row[0] for row in rows]
        if not kinds or kinds[0] != "intent" or kinds.count("intent") != 1:
            _protocol("normal-prefix site lacks one leading intent")
        if kinds.count("callback") > 1 or kinds.count("event") > 1:
            _protocol("normal-prefix site duplicated a durable record")
        if "event" in kinds and kinds[-1] != "event":
            _protocol("normal-prefix site continued after its event")
        if ordinal < max(by_ordinal) and "event" not in kinds:
            _protocol("normal-prefix journal continued past a dangling site")
        for kind, filename_id, name in rows:
            raw = _read_file(journal_fd, name)
            if raw is None:  # pragma: no cover - retained lock
                _protocol("normal-prefix record disappeared during replay")
            document = _parse_document(raw, "normal-prefix site record")
            parsed_kind, _key, record_id = _record_identity(document)
            if (
                parsed_kind != kind
                or record_id != filename_id
                or document.get("ordinal") != ordinal
                or document.get("h1_normal_prefix_spec_id") != handle.spec.spec_id
                or document.get("route_attempt_id") != handle.route_attempt_id
            ):
                _protocol("normal-prefix record filename or context differs")
            _verify_or_create_seal(
                root_fd,
                journal_fd,
                attempt=handle.route_attempt_id,
                ordinal=ordinal,
                kind=kind,
                record_id=record_id,
                allow_create=(repair and len(expected) + 1 > committed_record_count),
            )
            if kind == "intent":
                contract = handle.spec.payload["normal_prefix_site_contracts"][
                    ordinal - 1
                ]
                if (
                    document.get("previous_normal_site_event_commit_id")
                    != (
                        previous_event
                        if previous_event is not None
                        else _typed_null("NORMAL_PREFIX_GENESIS")
                    )
                    or any(document.get(key) != value for key, value in contract.items())
                ):
                    _protocol("normal-prefix intent chain changed")
                intents.append(document)
            elif kind == "callback":
                if (
                    not intents
                    or document.get("h1_normal_site_intent_id")
                    != intents[-1]["h1_normal_site_intent_id"]
                    or handle.spec.payload["normal_prefix_site_contracts"][
                        ordinal - 1
                    ]["callback_required"]
                    is not True
                ):
                    _protocol("normal-prefix callback result crossed its intent")
                callbacks[ordinal] = document
            else:
                allowed_outcomes = {
                    "SUCCESS",
                    *handle.spec.payload["normal_prefix_site_contracts"][ordinal - 1][
                        "failure_outcomes"
                    ],
                    dispatch_v1.ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION,
                }
                if (
                    not intents
                    or document.get("h1_normal_site_intent_id")
                    != intents[-1]["h1_normal_site_intent_id"]
                    or document.get("h1_normal_site_callback_result_id")
                    != (
                        callbacks[ordinal]["h1_normal_site_callback_result_id"]
                        if ordinal in callbacks
                        else _typed_null("SITE_HAS_NO_CALLBACK_RESULT")
                    )
                    or document.get("previous_normal_site_event_commit_id")
                    != (
                        previous_event
                        if previous_event is not None
                        else _typed_null("NORMAL_PREFIX_GENESIS")
                    )
                    or document.get("outcome") not in allowed_outcomes
                ):
                    _protocol("normal-prefix event chain changed")
                _verify_event_replay_shape(
                    intents[-1], callbacks.get(ordinal), document
                )
                previous_event = record_id
                events.append(document)
            expected.append((kind, document, record_id))
    if len(intents) not in {len(events), len(events) + 1}:
        _protocol("normal-prefix journal has more than one dangling intent")
    if any(event["outcome"] != "SUCCESS" for event in events[:-1]):
        _protocol("normal-prefix journal continued after its first failure")

    if len(cursor_rows) - 1 > len(expected):
        _protocol("normal-prefix durable records fell below cursor high-water")
    expected_cursor_rows: list[dict[str, Any]] = [_cursor_genesis(handle.spec.spec_id)]
    for kind, document, record_id in expected:
        expected_cursor_rows.append(
            _cursor_payload(
                handle.spec.spec_id,
                sequence=len(expected_cursor_rows),
                previous_id=expected_cursor_rows[-1]["h1_normal_prefix_cursor_record_id"],
                ordinal=document["ordinal"],
                record_kind=kind.upper(),
                record_id=record_id,
            )
        )
    if cursor_rows != expected_cursor_rows[: len(cursor_rows)]:
        _protocol("normal-prefix cursor differs from immutable records")
    high_water_states = _high_water_states(root_fd, handle)
    high_water = tuple(
        (sequence, cursor_id)
        for sequence, cursor_id, _name in high_water_states
    )
    for sequence, cursor_id in high_water:
        if (
            sequence >= len(expected_cursor_rows)
            or expected_cursor_rows[sequence][
                "h1_normal_prefix_cursor_record_id"
            ]
            != cursor_id
        ):
            _protocol("normal-prefix immutable records fell below high-water state")
    cursor_sequence = len(cursor_rows) - 1
    high_sequence = high_water[-1][0]
    if high_sequence < cursor_sequence or high_sequence > cursor_sequence + 1:
        _protocol("normal-prefix cursor and high-water state cannot be reconciled")
    cursor_state = (
        cursor_sequence,
        cursor_rows[-1]["h1_normal_prefix_cursor_record_id"],
    )
    if len(high_water) == 1:
        if high_water[0] != cursor_state:
            _protocol("normal-prefix high-water differs from stable cursor")
    elif high_water[0] == cursor_state:
        if high_sequence != cursor_sequence + 1:
            _protocol("normal-prefix high-water append edge is not adjacent")
    elif high_water[-1] != cursor_state:
        _protocol("normal-prefix high-water transition does not contain cursor")
    if len(expected_cursor_rows) - 1 > high_sequence + 1:
        _protocol("normal-prefix records exceeded high-water by more than one append")
    if len(high_water) == 2 and len(expected_cursor_rows) - 1 > high_sequence:
        _protocol("normal-prefix records advanced during a high-water transition")
    next_raw = (
        canonical_json_bytes(expected_cursor_rows[len(cursor_rows)]) + b"\n"
        if len(cursor_rows) < len(expected_cursor_rows)
        else None
    )
    if tail:
        if not repair or next_raw is None or not next_raw.startswith(tail):
            _protocol("normal-prefix cursor has a nonrepairable torn tail")
        os.ftruncate(cursor_fd, complete_length)
        os.fsync(cursor_fd)
    if repair:
        while len(cursor_rows) < len(expected_cursor_rows):
            kind, document, record_id = expected[len(cursor_rows) - 1]
            _append_cursor_locked(
                handle,
                root_fd,
                cursor_fd,
                cursor_rows,
                ordinal=document["ordinal"],
                kind=kind,
                record_id=record_id,
            )
    elif len(cursor_rows) != len(expected_cursor_rows):
        _protocol("normal-prefix cursor is behind immutable records")
    stable_states = _high_water_states(root_fd, handle)
    expected_stable = (
        len(cursor_rows) - 1,
        cursor_rows[-1]["h1_normal_prefix_cursor_record_id"],
    )
    if len(stable_states) == 2:
        if (stable_states[-1][0], stable_states[-1][1]) != expected_stable:
            _protocol("normal-prefix high-water transition did not reach cursor")
        if not repair:
            _protocol(
                "normal-prefix read-only replay refuses adjacent high-water cleanup"
            )
        _unlink_high_water_state(root_fd, stable_states[0][2])
        stable_states = _high_water_states(root_fd, handle)
    if (
        len(stable_states) != 1
        or (stable_states[0][0], stable_states[0][1]) != expected_stable
    ):
        _protocol("normal-prefix high-water did not stabilize at cursor")
    return _JournalState(intents, callbacks, events, expected)


def _require_journal_locked(
    handle: H1NormalPrefixHandleV1,
) -> tuple[int, int, int, int, _JournalState]:
    if type(handle) is not H1NormalPrefixHandleV1:
        _fail("normal-prefix operation requires one exact handle")
    root_fd = _open_directory(Path(handle.root_directory))
    journal_fd = lock_fd = cursor_fd = -1
    lock_held = False
    try:
        root_metadata = os.fstat(root_fd)
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or stat.S_IMODE(root_metadata.st_mode) != 0o700
            or (root_metadata.st_dev, root_metadata.st_ino)
            != (handle.root_device, handle.root_inode)
        ):
            _protocol("normal-prefix root allocation changed")
        root_lock_fd = _open_regular_at(root_fd, _ROOT_LOCK, flags=os.O_RDONLY)
        try:
            root_lock_metadata = os.fstat(root_lock_fd)
            if (
                stat.S_IMODE(root_lock_metadata.st_mode) != 0o600
                or (root_lock_metadata.st_dev, root_lock_metadata.st_ino)
                != (handle.root_lock_device, handle.root_lock_inode)
            ):
                _protocol("normal-prefix root lock changed")
        finally:
            os.close(root_lock_fd)
        allocation_raw = _read_file(root_fd, _allocation_name(handle.route_attempt_id))
        if allocation_raw is None:
            _protocol("normal-prefix allocation disappeared")
        allocation, claimed = _parse_allocation_document(
            allocation_raw, handle.spec
        )
        if claimed != handle.allocation_id:
            _protocol("normal-prefix allocation identity changed")
        if (
            allocation.get("h1_normal_prefix_spec_id") != handle.spec.spec_id
            or allocation.get("route_attempt_id") != handle.route_attempt_id
            or allocation.get("normal_prefix_root_device") != handle.root_device
            or allocation.get("normal_prefix_root_inode") != handle.root_inode
            or allocation.get("root_allocation_lock_device")
            != handle.root_lock_device
            or allocation.get("root_allocation_lock_inode")
            != handle.root_lock_inode
            or allocation.get("high_water_token_device")
            != handle.high_water_token_device
            or allocation.get("high_water_token_inode")
            != handle.high_water_token_inode
            or allocation.get("normal_prefix_journal_device")
            != handle.journal_device
            or allocation.get("normal_prefix_journal_inode")
            != handle.journal_inode
            or allocation.get("normal_prefix_lock_device") != handle.lock_device
            or allocation.get("normal_prefix_lock_inode") != handle.lock_inode
            or allocation.get("normal_prefix_cursor_device") != handle.cursor_device
            or allocation.get("normal_prefix_cursor_inode") != handle.cursor_inode
        ):
            _protocol("normal-prefix allocation no longer matches its handle")
        journal_fd = _open_directory_at(root_fd, handle.route_attempt_id)
        journal_metadata = os.fstat(journal_fd)
        if (
            not stat.S_ISDIR(journal_metadata.st_mode)
            or stat.S_IMODE(journal_metadata.st_mode) != 0o700
            or (journal_metadata.st_dev, journal_metadata.st_ino)
            != (handle.journal_device, handle.journal_inode)
        ):
            _protocol("normal-prefix attempt directory changed")
        lock_fd = _open_regular_at(journal_fd, _LOCK_FILE, flags=os.O_RDWR)
        lock_metadata = os.fstat(lock_fd)
        if (
            stat.S_IMODE(lock_metadata.st_mode) != 0o600
            or (lock_metadata.st_dev, lock_metadata.st_ino)
            != (handle.lock_device, handle.lock_inode)
        ):
            _protocol("normal-prefix coordination lock changed")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        lock_held = True
        spec_raw = _read_file(journal_fd, _SPEC_FILE)
        if spec_raw != canonical_json_bytes(handle.spec.to_document()):
            _protocol("normal-prefix spec bytes changed")
        cursor_fd = _open_regular_at(journal_fd, _CURSOR_FILE, flags=os.O_RDWR)
        cursor_metadata = os.fstat(cursor_fd)
        if (
            stat.S_IMODE(cursor_metadata.st_mode) != 0o600
            or (cursor_metadata.st_dev, cursor_metadata.st_ino)
            != (handle.cursor_device, handle.cursor_inode)
        ):
            _protocol("normal-prefix cursor changed")
        state = _replay_journal_locked(
            handle,
            root_fd,
            journal_fd,
            cursor_fd,
            repair=True,
        )
        return root_fd, journal_fd, lock_fd, cursor_fd, state
    except BaseException:
        if cursor_fd >= 0:
            os.close(cursor_fd)
        if lock_fd >= 0:
            if lock_held:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        if journal_fd >= 0:
            os.close(journal_fd)
        os.close(root_fd)
        raise


def _release_journal_locked(root_fd: int, journal_fd: int, lock_fd: int, cursor_fd: int) -> None:
    os.close(cursor_fd)
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    os.close(lock_fd)
    os.close(journal_fd)
    os.close(root_fd)


def _close_fork_inherited_journal_locked(
    root_fd: int, journal_fd: int, lock_fd: int, cursor_fd: int
) -> None:
    os.close(cursor_fd)
    os.close(lock_fd)
    os.close(journal_fd)
    os.close(root_fd)


def _snapshot_from_state(
    handle: H1NormalPrefixHandleV1,
    state: _JournalState,
    *,
    callback_required_to_resume: bool = False,
    owner_tail_verified_under_composite_lease: bool = False,
) -> H1NormalPrefixSnapshotV1:
    if state.failed:
        status = H1NormalPrefixStatusV1.FAILURE_POISONED_AWAITING_PHASE_TRANSITION
    elif len(state.events) == PREFIX_END_ORDINAL:
        status = (
            H1NormalPrefixStatusV1.NORMAL_PREFIX_COMPLETE_AWAITING_POST_CHILD_CLEANUP
        )
    elif callback_required_to_resume:
        status = H1NormalPrefixStatusV1.CALLBACK_REQUIRED_TO_RESUME_SAFE_PRESTART
    else:
        status = H1NormalPrefixStatusV1.READY
    last_event = state.events[-1] if state.events else None
    payload = {
        "schema": "acfqp.k7_h1_normal_prefix_snapshot.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "authority_stage": AUTHORITY_STAGE,
        "h1_normal_prefix_spec_id": handle.spec.spec_id,
        "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
        "route_attempt_id": handle.route_attempt_id,
        "completed_event_count": len(state.events),
        "next_ordinal": (
            len(state.events) + 1 if len(state.events) < PREFIX_END_ORDINAL else 41
        ),
        "dangling_intent_id": (
            state.dangling_intent["h1_normal_site_intent_id"]
            if state.dangling_intent is not None
            else _typed_null("NO_DANGLING_INTENT")
        ),
        "last_event_id": (
            last_event["h1_normal_site_event_commit_id"]
            if last_event is not None
            else _typed_null("NORMAL_PREFIX_GENESIS")
        ),
        "first_failure_outcome": (
            last_event["outcome"] if state.failed else _typed_null("NO_FAILURE")
        ),
        "status": status.value,
        "normal_forward_dispatch_allowed": (
            status is H1NormalPrefixStatusV1.READY
            and owner_tail_verified_under_composite_lease
        ),
        "site_41_or_later_authorized": False,
        "owner_tail_verified_under_composite_lease": (
            owner_tail_verified_under_composite_lease
        ),
        "cleanup_execution_authority_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "certificate_issued": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "h1_normal_prefix_snapshot_id": _content_id(SNAPSHOT_DOMAIN, payload),
    }
    return H1NormalPrefixSnapshotV1(
        _SNAPSHOT_ISSUER, canonical_json_bytes(document)
    )


def replay_h1_normal_prefix_journal_v1(
    handle: H1NormalPrefixHandleV1,
) -> H1NormalPrefixSnapshotV1:
    root_fd, journal_fd, lock_fd, cursor_fd, state = _require_journal_locked(handle)
    try:
        return _snapshot_from_state(handle, state)
    finally:
        _release_journal_locked(root_fd, journal_fd, lock_fd, cursor_fd)


def _validate_execution_bindings(
    handle: H1NormalPrefixHandleV1,
    phase_handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    dispatch_profile: dispatch_v1.H1LifecycleDispatchProfileV1,
) -> None:
    if _LOCAL_AUTHORITY_POISONED is not False:
        _fail("normal-prefix local authority process is poisoned")
    payload = handle.spec.payload
    current_semantic_closure = inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    if (
        type(phase_handle) is not phase_v1.H1AttemptExecutionPhaseOwnerV1Handle
        or type(rejection_gate) is not rejection_v1.H1AttemptRejectionGateHandleV1
        or type(owner) is not owner_v4.H1SharedCapOwnerV4WalHandle
        or type(bundle) is not dispatch_v1.H1AnchoredLifecycleDispatchBundleV1
        or type(dispatch_profile) is not dispatch_v1.H1LifecycleDispatchProfileV1
        or payload["h1_attempt_execution_phase_spec_id"] != phase_handle.spec.spec_id
        or payload["h1_attempt_phase_allocation_id"] != phase_handle.allocation_id
        or payload["h1_attempt_rejection_gate_id"] != rejection_gate.spec.gate_id
        or payload["h1_shared_cap_profile_core_v3_id"] != owner.profile.profile_id
        or payload["h1_shared_cap_owner_v3_runtime_id"] != owner.runtime_id
        or payload["h1_shared_cap_owner_v4_wal_binding_id"] != owner.binding_id
        or payload["h1_lifecycle_dispatch_profile_id"] != dispatch_profile.profile_id
        or payload["h1_anchored_lifecycle_program_id"]
        != bundle.program.anchored_program_id
        or payload["h1_anchored_lifecycle_handler_registry_id"]
        != bundle.registry.registry_id
        or payload["h1_normal_prefix_semantic_closure_id"]
        != current_semantic_closure["h1_normal_prefix_semantic_closure_id"]
    ):
        _fail("phase-aware normal-prefix execution crossed a frozen binding")


def _require_live_lease(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
) -> H1PhaseAwareNormalPrefixLeaseV1:
    if (
        type(lease) is not H1PhaseAwareNormalPrefixLeaseV1
        or _LOCAL_AUTHORITY_POISONED is not False
        or not lease._active
        or lease._owner_pid != os.getpid()
        or lease._owner_thread_id != threading.get_ident()
        or _ACTIVE_EXECUTIONS.get() != (lease.handle.spec.spec_id,)
        or phase_v1._ACTIVE_PHASE_LEASES.get() != (lease.phase_handle.spec.spec_id,)
        or rejection_v1._active_gate_modes(lease.rejection_gate.spec.gate_id)
        != (_GATE_CONTEXT_MODE,)
    ):
        _fail("phase-aware normal-prefix lease is stale, forked, or crossed")
    _require_dependency_namespace_unchanged()
    for descriptor, device, inode, label in (
        (
            lease._phase_lock_fd,
            lease.phase_handle.lock_device,
            lease.phase_handle.lock_inode,
            "phase lock",
        ),
        (
            lease._gate_lock_fd,
            lease.rejection_gate.gate_lock_device,
            lease.rejection_gate.gate_lock_inode,
            "gate lock",
        ),
        (
            lease._journal_lock_fd,
            lease.handle.lock_device,
            lease.handle.lock_inode,
            "journal lock",
        ),
    ):
        metadata = os.fstat(descriptor)
        if (metadata.st_dev, metadata.st_ino) != (device, inode):
            _fail(f"phase-aware normal-prefix {label} changed")
    return lease


@contextmanager
def hold_h1_phase_aware_normal_prefix_lease_v1(
    handle: H1NormalPrefixHandleV1,
    *,
    phase_handle: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    dispatch_profile: dispatch_v1.H1LifecycleDispatchProfileV1,
) -> Iterator[H1PhaseAwareNormalPrefixLeaseV1]:
    _validate_execution_bindings(
        handle,
        phase_handle,
        rejection_gate,
        owner,
        bundle,
        dispatch_profile,
    )
    if _ACTIVE_EXECUTIONS.get():
        _fail("phase-aware normal-prefix leases cannot nest")
    owner_pid = os.getpid()
    owner_thread_id = threading.get_ident()
    execution_token: Any | None = None
    phase_token: Any | None = None
    phase_root_fd = phase_directory_fd = phase_lock_fd = phase_cursor_fd = -1
    gate_directory_fd = gate_lock_fd = -1
    journal_root_fd = journal_directory_fd = journal_lock_fd = journal_cursor_fd = -1
    gate_token: Any | None = None
    lease: H1PhaseAwareNormalPrefixLeaseV1 | None = None
    try:
        execution_token = _ACTIVE_EXECUTIONS.set((handle.spec.spec_id,))
        phase_token = phase_v1._activate_lease_context(phase_handle)
        (
            phase_root_fd,
            phase_directory_fd,
            phase_lock_fd,
            phase_cursor_fd,
        ) = phase_v1._require_handle_locked(phase_handle)
        phase_state, transition = phase_v1._recover_locked(
            phase_root_fd,
            phase_directory_fd,
            phase_cursor_fd,
            phase_handle,
        )
        if phase_state is not phase_v1.H1AttemptExecutionPhaseV1.NORMAL or transition is not None:
            _fail("normal-prefix execution is forbidden outside NORMAL phase")
        _, gate_directory_fd, gate_lock_fd = rejection_v1._require_handle(
            rejection_gate, fcntl.LOCK_EX
        )
        rejection_v1._replay_gate_locked(rejection_gate, gate_directory_fd)
        gate_token = rejection_v1._activate_gate_context(
            rejection_gate.spec.gate_id, _GATE_CONTEXT_MODE
        )
        (
            journal_root_fd,
            journal_directory_fd,
            journal_lock_fd,
            journal_cursor_fd,
            _journal_state,
        ) = _require_journal_locked(handle)
        lease = H1PhaseAwareNormalPrefixLeaseV1(
            _LEASE_ISSUER,
            handle,
            phase_handle,
            rejection_gate,
            owner,
            bundle,
            dispatch_profile,
            phase_root_fd,
            phase_directory_fd,
            phase_lock_fd,
            phase_cursor_fd,
            gate_directory_fd,
            gate_lock_fd,
            journal_root_fd,
            journal_directory_fd,
            journal_lock_fd,
            journal_cursor_fd,
            owner_pid,
            owner_thread_id,
        )
        yield lease
    finally:
        current_pid = os.getpid()
        current_thread_id = threading.get_ident()
        if current_pid == owner_pid and current_thread_id == owner_thread_id:
            if lease is not None:
                lease._active = False
            if journal_root_fd >= 0:
                _release_journal_locked(
                    journal_root_fd,
                    journal_directory_fd,
                    journal_lock_fd,
                    journal_cursor_fd,
                )
            if gate_directory_fd >= 0:
                rejection_v1._release_retained_gate_context(
                    gate_id=rejection_gate.spec.gate_id,
                    mode=_GATE_CONTEXT_MODE,
                    directory_fd=gate_directory_fd,
                    lock_fd=gate_lock_fd,
                    context_token=gate_token,
                    owner_pid=owner_pid,
                    owner_thread_id=owner_thread_id,
                )
            if phase_root_fd >= 0:
                phase_v1._release_locked(
                    phase_root_fd,
                    phase_directory_fd,
                    phase_lock_fd,
                    phase_cursor_fd,
                )
            if phase_token is not None:
                phase_v1._ACTIVE_PHASE_LEASES.reset(phase_token)
            if execution_token is not None:
                _ACTIVE_EXECUTIONS.reset(execution_token)
        elif current_pid != owner_pid:
            if lease is not None:
                lease._active = False
            if journal_root_fd >= 0:
                _close_fork_inherited_journal_locked(
                    journal_root_fd,
                    journal_directory_fd,
                    journal_lock_fd,
                    journal_cursor_fd,
                )
            if gate_directory_fd >= 0:
                rejection_v1._release_retained_gate_context(
                    gate_id=rejection_gate.spec.gate_id,
                    mode=_GATE_CONTEXT_MODE,
                    directory_fd=gate_directory_fd,
                    lock_fd=gate_lock_fd,
                    context_token=gate_token,
                    owner_pid=owner_pid,
                    owner_thread_id=owner_thread_id,
                )
            if phase_root_fd >= 0:
                phase_v1._close_fork_inherited_locked(
                    phase_root_fd,
                    phase_directory_fd,
                    phase_lock_fd,
                    phase_cursor_fd,
                )
            phase_v1._ACTIVE_PHASE_LEASES.set(())
            _ACTIVE_EXECUTIONS.set(())
        else:
            _fail("phase-aware normal-prefix lease crossed its owning thread")


def _owner_tail_records(
    directory_fd: int,
) -> tuple[int, Any, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    head: Any = _typed_null("JOURNAL_GENESIS")
    for expected, (sequence, filename_id, name) in enumerate(
        owner_v3._record_names(directory_fd), start=1
    ):
        if sequence != expected:
            _protocol("Owner journal changed while phase-aware lease was retained")
        raw = owner_v3._read_file(directory_fd, name)
        if raw is None:  # pragma: no cover - Owner lock retained
            _protocol("Owner record disappeared during phase-aware replay")
        document = owner_v3._parse_document(raw, "phase-aware Owner record")
        record_id = owner_v3._verify_record_identity(document)
        if record_id != filename_id:
            _protocol("Owner record filename changed during phase-aware replay")
        rows.append(document)
        head = record_id
    return len(rows), head, rows


def _owner_delta(
    rows: list[dict[str, Any]],
    before_sequence: int,
) -> list[dict[str, Any]]:
    if before_sequence > len(rows):
        _protocol("Owner journal rolled back below a normal-site intent")
    return [
        {
            "sequence": row["sequence"],
            "schema": row["schema"],
            "record_kind": row["record_kind"],
            "record_id": owner_v3._verify_record_identity(dict(row)),
        }
        for row in rows[before_sequence:]
    ]


def _direct_ack_locked(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    commit: rejection_v1.H1AttemptRejectionCommitV1,
    pair: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> rejection_v1.H1AttemptRejectionAckV1:
    receipt, event, snapshot = pair
    desired = rejection_v1.H1AttemptRejectionAckV1(
        rejection_v1._ACK_ISSUER,
        lease.rejection_gate.spec.gate_id,
        commit.commit_id,
        owner_v3._record_id(receipt),
        owner_v3._record_id(event),
        owner_v3._record_id(snapshot),
    )
    raw = desired.canonical_bytes
    if not rejection_v1._publish_new(
        lease._gate_directory_fd,
        rejection_v1._ACK_FILE,
        raw,
    ):
        existing = rejection_v1._read_file(
            lease._gate_directory_fd, rejection_v1._ACK_FILE
        )
        if existing is None or not hmac.compare_digest(existing, raw):
            _protocol("phase-aware cap rejection ACK conflicted")
    rejection_v1._append_cursor_state_locked(
        lease.rejection_gate,
        lease._gate_directory_fd,
        state=rejection_v1.H1AttemptRejectionGateStateV1.ACKNOWLEDGED,
        commit_id=commit.commit_id,
        ack_id=desired.ack_id,
    )
    return desired


def _reserve_locked(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    root_fd: int,
    directory_fd: int,
    state: owner_v3._ReplayState,
    *,
    operation_id: str,
    site_key: str,
    path: str,
    reservation_upper: int,
) -> tuple[
    owner_v3.H1SharedReservationV3 | None,
    owner_v3.H1SharedCapRejectionResultV3 | None,
    owner_v3._ReplayState,
]:
    existing_id = state.reservation_by_operation.get(operation_id)
    if existing_id is not None:
        existing = state.reservations[existing_id]
        if (
            existing["site_key"] != site_key
            or existing["path"] != path
            or existing["reservation_upper"] != reservation_upper
        ):
            _protocol("normal-site operation ID was reused with different semantics")
        return owner_v3.H1SharedReservationV3(existing), None, state
    owner_v3._require_owner_open_join(state)
    if state.observed_overrun_count:
        _protocol("normal-prefix Owner is poisoned by an observed overrun")
    owner_v3._require_pair_frontier(state, allowed_subject_id=None)
    document, candidate = owner_v3._reservation_document_for_request(
        lease.owner.owner,
        state,
        operation_id=operation_id,
        site_key=site_key,
        path=path,
        reservation_upper=reservation_upper,
    )
    limit = owner_v3._limit(lease.owner.profile, path)
    if state.pending_cursor is not None:
        _protocol("V4 WAL reconciliation left an unresolved Owner cursor")
    if candidate <= limit.hard_cap:
        appended = owner_v3._append_record(
            root_fd,
            directory_fd,
            lease.owner.owner,
            state,
            schema="acfqp.k7_h1_shared_cap_reservation.v3",
            kind="RESERVATION_DURABLE",
            extra={
                key: value
                for key, value in document.items()
                if key
                in owner_v3._EXTRA_FIELDS[
                    "acfqp.k7_h1_shared_cap_reservation.v3"
                ]
            },
        )
        state = owner_v3._replay_records_fd(directory_fd, lease.owner.owner)
        return owner_v3.H1SharedReservationV3(appended), None, state

    request_id = _cid(document["rejection_request_id"], "normal-site rejection request")
    commit = rejection_v1._commit_rejection_locked(
        lease.rejection_gate,
        lease._gate_directory_fd,
        decision_point_id=lease.owner.profile.decision_point_id,
        transaction_id=lease.owner.profile.transaction_id,
        shared_owner_profile_core_id=lease.owner.profile.profile_id,
        rejection_request_id=request_id,
        source_kind=rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER,
        site_key=site_key,
        path=path,
        limit_kind=rejection_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=reservation_upper,
        candidate=candidate,
        hard_cap=limit.hard_cap,
        reason_code="SHARED_CAP_EXHAUSTED",
        fault=rejection_v1.H1AttemptRejectionCrashPointV1.NONE,
    )
    owner_v3._append_record(
        root_fd,
        directory_fd,
        lease.owner.owner,
        state,
        schema="acfqp.k7_h1_shared_cap_reservation.v3",
        kind="REJECTION_ADMISSION_DURABLE",
        extra={
            key: value
            for key, value in document.items()
            if key in owner_v3._EXTRA_FIELDS["acfqp.k7_h1_shared_cap_reservation.v3"]
        },
    )
    state = owner_v3._replay_records_fd(directory_fd, lease.owner.owner)
    pair = owner_v3._append_rejection_pair_locked(
        root_fd,
        directory_fd,
        lease.owner.owner,
        state,
        commit,
    )
    acknowledgement = _direct_ack_locked(lease, commit, pair)
    state = owner_v3._replay_records_fd(directory_fd, lease.owner.owner)
    return (
        None,
        owner_v3.H1SharedCapRejectionResultV3(
            commit,
            pair[0],
            pair[1],
            pair[2],
            acknowledgement,
        ),
        state,
    )


def _start_cell_locked(
    owner: owner_v3.H1SharedCapOwnerV3Handle,
    root_fd: int,
    directory_fd: int,
    state: owner_v3._ReplayState,
    reservation: owner_v3.H1SharedReservationV3,
) -> tuple[dict[str, Any], owner_v3._ReplayState]:
    reservation_id, durable = owner_v3._require_durable_reservation(
        owner, state, reservation
    )
    existing = state.cells.get(reservation_id)
    if existing is not None:
        return existing, state
    if reservation_id in state.settlements:
        _protocol("settled normal-site reservation lacks its native cell")
    owner_v3._require_pair_frontier(state, allowed_subject_id=reservation_id)
    cell = owner_v3._append_record(
        root_fd,
        directory_fd,
        owner,
        state,
        schema="acfqp.k7_h1_shared_cap_native_cell.v3",
        kind="NATIVE_CELL_DURABLE",
        extra={
            "h1_shared_cap_owner_v3_reservation_id": reservation_id,
            "operation_id": durable["operation_id"],
            "path": durable["path"],
            "lifecycle_state": owner_v3.H1SharedNativeStateV3.SIDE_EFFECT_STARTED.value,
            "durable_before_native_effect": True,
        },
    )
    return cell, owner_v3._replay_records_fd(directory_fd, owner)


def _settle_locked(
    owner: owner_v3.H1SharedCapOwnerV3Handle,
    root_fd: int,
    directory_fd: int,
    state: owner_v3._ReplayState,
    reservation: owner_v3.H1SharedReservationV3,
    *,
    basis: owner_v3.H1SharedValueBasisV3,
    native_observed_value: int | None,
    evidence_source_id: str,
) -> tuple[owner_v3.H1SharedSettlementResultV3, bool, owner_v3._ReplayState]:
    evidence_source = _cid(evidence_source_id, "normal-site evidence source")
    reservation_id, durable = owner_v3._require_durable_reservation(
        owner, state, reservation
    )
    owner_v3._require_value_basis_path(basis, durable["path"])
    semantics = owner_v3._native_semantics(
        basis,
        reservation_upper=durable["reservation_upper"],
        native_observed_value=native_observed_value,
    )
    native_state, encoded_native, charged, exact, conservative, overrun = semantics
    lifecycle_state = (
        owner_v3.H1SharedNativeStateV3.KNOWN_NOT_STARTED
        if basis is owner_v3.H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO
        else owner_v3.H1SharedNativeStateV3.SIDE_EFFECT_STARTED
    )
    cell_extra = {
        "h1_shared_cap_owner_v3_reservation_id": reservation_id,
        "operation_id": durable["operation_id"],
        "path": durable["path"],
        "lifecycle_state": lifecycle_state.value,
        "durable_before_native_effect": True,
    }
    cell = state.cells.get(reservation_id)
    if cell is None:
        if lifecycle_state is owner_v3.H1SharedNativeStateV3.SIDE_EFFECT_STARTED:
            _protocol("normal-site observed settlement lacks durable native start")
        cell = owner_v3._append_record(
            root_fd,
            directory_fd,
            owner,
            state,
            schema="acfqp.k7_h1_shared_cap_native_cell.v3",
            kind="NATIVE_CELL_DURABLE",
            extra=cell_extra,
        )
        state = owner_v3._replay_records_fd(directory_fd, owner)
    elif any(cell[key] != value for key, value in cell_extra.items()):
        _protocol("normal-site native-cell semantics changed at settlement")

    evidence_extra = {
        "h1_shared_cap_owner_v3_reservation_id": reservation_id,
        "h1_shared_cap_owner_v3_native_cell_id": owner_v3._record_id(cell),
        "operation_id": durable["operation_id"],
        "path": durable["path"],
        "value_basis": basis.value,
        "native_observed_value": encoded_native,
        "charged_value": charged,
        "construction_exact_value_assertion": exact,
        "native_authority_verified": False,
        "evidence_source_authority_verified": False,
        "conservative_charge": conservative,
        "upper_bound_violation": overrun,
        "evidence_source_id": evidence_source,
    }
    evidence = state.evidence.get(reservation_id)
    if evidence is None:
        evidence = owner_v3._append_record(
            root_fd,
            directory_fd,
            owner,
            state,
            schema="acfqp.k7_h1_shared_cap_native_evidence.v3",
            kind="NATIVE_EVIDENCE_DURABLE",
            extra=evidence_extra,
        )
        state = owner_v3._replay_records_fd(directory_fd, owner)
    elif any(evidence[key] != value for key, value in evidence_extra.items()):
        _protocol("normal-site native evidence retry changed")

    settlement = state.settlements.get(reservation_id)
    if settlement is None:
        limit = owner_v3._limit(owner.profile, durable["path"])
        charged_before = state.charged[durable["path"]]
        charged_after = (
            charged_before + charged
            if limit.reducer is owner_v3.H1SharedReducerV3.SUM
            else max(charged_before, charged)
        )
        outstanding_before = state.outstanding[durable["path"]]
        settlement = owner_v3._append_record(
            root_fd,
            directory_fd,
            owner,
            state,
            schema="acfqp.k7_h1_shared_cap_settlement.v3",
            kind="SETTLEMENT_DURABLE",
            extra={
                "h1_shared_cap_owner_v3_reservation_id": reservation_id,
                "h1_shared_cap_owner_v3_native_evidence_id": owner_v3._record_id(evidence),
                "operation_id": durable["operation_id"],
                "path": durable["path"],
                "reducer": limit.reducer.value,
                "value_basis": basis.value,
                "native_observed_value": encoded_native,
                "charged_value": charged,
                "reservation_upper": durable["reservation_upper"],
                "charged_before": charged_before,
                "charged_after": charged_after,
                "outstanding_before": outstanding_before,
                "outstanding_after": outstanding_before - durable["reservation_upper"],
                "single_spend": True,
            },
        )
        state = owner_v3._replay_records_fd(directory_fd, owner)
    elif (
        settlement["h1_shared_cap_owner_v3_native_evidence_id"]
        != owner_v3._record_id(evidence)
        or settlement["value_basis"] != basis.value
        or settlement["native_observed_value"] != encoded_native
        or settlement["charged_value"] != charged
    ):
        _protocol("normal-site settlement retry semantics changed")

    pair = owner_v3._find_pair_for_subject(state, owner_v3._record_id(settlement))
    if pair is None:
        pair = owner_v3._append_receipt_event_snapshot(
            root_fd,
            directory_fd,
            owner,
            state,
            pair_extra=owner_v3._pair_extra(
                subject_kind="SETTLEMENT",
                subject_id=owner_v3._record_id(settlement),
                path=settlement["path"],
                reducer=settlement["reducer"],
                reservation_upper=settlement["reservation_upper"],
                native_observed_value=settlement["native_observed_value"],
                charged_value=settlement["charged_value"],
                value_basis=settlement["value_basis"],
                construction_exact_value_assertion=evidence[
                    "construction_exact_value_assertion"
                ],
                conservative_charge=evidence["conservative_charge"],
                upper_bound_violation=evidence["upper_bound_violation"],
                control_cap_rejections=0 if state.rejection_commit_id is None else 1,
            ),
        )
    state = owner_v3._replay_records_fd(directory_fd, owner)
    result = owner_v3.H1SharedSettlementResultV3(
        owner_v3.H1SharedReservationV3(durable),
        cell,
        evidence,
        settlement,
        pair[0],
        pair[1],
        pair[2],
    )
    return result, overrun, state


def _settlement_refs(result: owner_v3.H1SharedSettlementResultV3) -> dict[str, Any]:
    return {
        "reservation_id": result.reservation.reservation_id,
        "native_cell_id": owner_v3._record_id(result.native_cell_document),
        "native_evidence_id": owner_v3._record_id(result.evidence_document),
        "settlement_id": owner_v3._record_id(result.settlement_document),
        "receipt_id": owner_v3._record_id(result.receipt_document),
        "event_id": owner_v3._record_id(result.event_document),
        "snapshot_id": owner_v3._record_id(result.snapshot_document),
        "rejection_commit_id": _typed_null("NO_CAP_REJECTION"),
        "rejection_ack_id": _typed_null("NO_CAP_REJECTION"),
    }


def _rejection_refs(result: owner_v3.H1SharedCapRejectionResultV3) -> dict[str, Any]:
    return {
        "reservation_id": _typed_null("RESERVATION_REJECTED"),
        "native_cell_id": _typed_null("SIDE_EFFECT_NOT_STARTED"),
        "native_evidence_id": _typed_null("SIDE_EFFECT_NOT_STARTED"),
        "settlement_id": _typed_null("SIDE_EFFECT_NOT_STARTED"),
        "receipt_id": owner_v3._record_id(result.receipt_document),
        "event_id": owner_v3._record_id(result.event_document),
        "snapshot_id": owner_v3._record_id(result.snapshot_document),
        "rejection_commit_id": result.rejection_commit.commit_id,
        "rejection_ack_id": result.acknowledgement.ack_id,
    }


def _reservation_only_refs(reservation: owner_v3.H1SharedReservationV3) -> dict[str, Any]:
    return {
        "reservation_id": reservation.reservation_id,
        "native_cell_id": _typed_null("DEFERRED_NATIVE_START"),
        "native_evidence_id": _typed_null("DEFERRED_SETTLEMENT"),
        "settlement_id": _typed_null("DEFERRED_SETTLEMENT"),
        "receipt_id": _typed_null("DEFERRED_SETTLEMENT"),
        "event_id": _typed_null("DEFERRED_SETTLEMENT"),
        "snapshot_id": _typed_null("DEFERRED_SETTLEMENT"),
        "rejection_commit_id": _typed_null("NO_CAP_REJECTION"),
        "rejection_ack_id": _typed_null("NO_CAP_REJECTION"),
    }


def _next_site(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    state: _JournalState,
) -> tuple[dict[str, Any], dict[str, Any]]:
    ordinal = state.next_ordinal
    if ordinal > PREFIX_END_ORDINAL:
        _fail("Contract 59E-C does not authorize lifecycle site 41 or later")
    row = lease.bundle.program.transitions[ordinal - 1]
    handler = lease.bundle.registry.handlers[ordinal - 1]
    if row["ordinal"] != ordinal or handler["site_key"] != row["site_key"]:
        _protocol("normal-prefix frozen program and handler registry diverged")
    if handler["handler_mode"] not in {
        dispatch_v1.H1LifecycleHandlerModeV1.DEFERRED_ORIGIN.value,
        dispatch_v1.H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value,
        dispatch_v1.H1LifecycleHandlerModeV1.IMMEDIATE_MAGNITUDE.value,
    }:
        _protocol("normal-prefix reached an out-of-scope handler mode")
    return row, handler


def _build_intent(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    journal_state: _JournalState,
    owner_state: owner_v3._ReplayState,
    row: Mapping[str, Any],
    handler: Mapping[str, Any],
) -> H1NormalSiteIntentV1:
    ordinal = row["ordinal"]
    operation_id = dispatch_v1._operation_id(
        lease.dispatch_profile.profile_id, ordinal, row["site_key"]
    )
    evidence_id = dispatch_v1._evidence_source_id(
        lease.dispatch_profile.profile_id, ordinal, row["site_key"]
    )
    path = dispatch_v1._resource_path(row)
    upper = lease.dispatch_profile.site_operands.get(row["site_key"])
    if path is None or upper is None:
        _protocol("normal-prefix reservation site lost its frozen operand")
    reservation_document, candidate = owner_v3._reservation_document_for_request(
        lease.owner.owner,
        owner_state,
        operation_id=operation_id,
        site_key=row["site_key"],
        path=path,
        reservation_upper=upper,
    )
    limit = owner_v3._limit(lease.owner.profile, path)
    previous_event = journal_state.events[-1] if journal_state.events else None
    payload = {
        "schema": "acfqp.k7_h1_normal_site_intent.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_normal_prefix_spec_id": lease.handle.spec.spec_id,
        "logical_occurrence_id": lease.owner.profile.logical_occurrence_id,
        "route_attempt_id": lease.owner.profile.route_attempt_id,
        "decision_point_id": lease.owner.profile.decision_point_id,
        "transaction_id": lease.owner.profile.transaction_id,
        "ordinal": ordinal,
        "site_key": row["site_key"],
        "phase": row["phase"],
        "operation": row["operation"],
        "from_state": row["from_state"],
        "success_state": row["success_state"],
        "handler_mode": handler["handler_mode"],
        "resource_path": path,
        "reducer": handler["reducer"],
        "callback_required": handler["callback_required"],
        "failure_outcomes": list(dispatch_v1._failure_outcomes(row)),
        "deterministic_dispatch_operation_id": operation_id,
        "owner_reservation_operation_id": dispatch_v1._owner_reservation_operation_id(
            lease.dispatch_profile.profile_id, row
        ),
        "native_evidence_source_id": evidence_id,
        "reservation_upper": upper,
        "admission_candidate": candidate,
        "hard_cap": limit.hard_cap,
        "expected_admission_outcome": (
            "REJECTED_BEFORE_SIDE_EFFECT"
            if candidate > limit.hard_cap
            else "ADMITTED"
        ),
        "rejection_request_id": reservation_document["rejection_request_id"],
        "previous_normal_site_event_commit_id": (
            previous_event["h1_normal_site_event_commit_id"]
            if previous_event is not None
            else _typed_null("NORMAL_PREFIX_GENESIS")
        ),
        "owner_journal_sequence_before_site": owner_state.sequence,
        "owner_journal_head_id_before_site": owner_state.head_id,
        "durable_before_owner_admission": True,
        "callback_retry_forbidden_after_native_cell": True,
        "site_authority_single_use_per_lease": True,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "certificate_issued": False,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "h1_normal_site_intent_id": _content_id(INTENT_DOMAIN, payload),
    }
    return H1NormalSiteIntentV1(_INTENT_ISSUER, canonical_json_bytes(document))


def _callback_document(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    intent: Mapping[str, Any],
    *,
    result_kind: str,
    native_value: int | None,
    exception_type: str | None,
    callback_invocation_count: int = 1,
    callback_invocation_may_have_occurred: bool = False,
) -> H1NormalSiteCallbackResultV1:
    payload = {
        "schema": "acfqp.k7_h1_normal_site_callback_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_normal_prefix_spec_id": lease.handle.spec.spec_id,
        "route_attempt_id": lease.handle.route_attempt_id,
        "ordinal": intent["ordinal"],
        "site_key": intent["site_key"],
        "h1_normal_site_intent_id": intent["h1_normal_site_intent_id"],
        "callback_result_kind": result_kind,
        "native_observed_value": (
            native_value if native_value is not None else _typed_null("NO_EXACT_NATIVE_VALUE")
        ),
        "callback_invocation_count": callback_invocation_count,
        "callback_invocation_may_have_occurred": (
            callback_invocation_may_have_occurred
        ),
        "callback_exception_type": (
            exception_type
            if exception_type is not None
            else _typed_null("NO_CALLBACK_EXCEPTION")
        ),
        "durable_before_owner_settlement": True,
        "native_evidence_authority_present": False,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "h1_normal_site_callback_result_id": _content_id(CALLBACK_DOMAIN, payload),
    }
    return H1NormalSiteCallbackResultV1(
        _CALLBACK_ISSUER, canonical_json_bytes(document)
    )


def _event_document(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    journal_state: _JournalState,
    intent: Mapping[str, Any],
    callback_result: Mapping[str, Any] | None,
    *,
    outcome: str,
    native_value: int | None,
    value_basis: str | None,
    owner_refs: Mapping[str, Any],
    owner_sequence_after: int,
    owner_head_after: Any,
    owner_delta: list[dict[str, Any]],
) -> H1NormalSiteEventCommitV1:
    callback_count = (
        callback_result["callback_invocation_count"]
        if callback_result is not None
        else 0
    )
    callback_exception = (
        callback_result["callback_exception_type"]
        if callback_result is not None
        else _typed_null("NO_CALLBACK_EXCEPTION")
    )
    previous_event = journal_state.events[-1] if journal_state.events else None
    payload = {
        "schema": "acfqp.k7_h1_normal_site_event_commit.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_normal_prefix_spec_id": lease.handle.spec.spec_id,
        "h1_lifecycle_dispatch_profile_id": lease.dispatch_profile.profile_id,
        "h1_anchored_lifecycle_program_id": lease.bundle.program.anchored_program_id,
        "h1_anchored_lifecycle_handler_registry_id": lease.bundle.registry.registry_id,
        "h1_shared_cap_owner_v3_runtime_id": lease.owner.runtime_id,
        "h1_shared_cap_owner_v4_wal_binding_id": lease.owner.binding_id,
        "logical_occurrence_id": lease.owner.profile.logical_occurrence_id,
        "route_attempt_id": lease.owner.profile.route_attempt_id,
        "decision_point_id": lease.owner.profile.decision_point_id,
        "transaction_id": lease.owner.profile.transaction_id,
        "ordinal": intent["ordinal"],
        "site_key": intent["site_key"],
        "phase": intent["phase"],
        "operation": intent["operation"],
        "from_state": intent["from_state"],
        "success_state": intent["success_state"],
        "handler_mode": intent["handler_mode"],
        "resource_path": intent["resource_path"],
        "reducer": intent["reducer"],
        "deterministic_dispatch_operation_id": intent[
            "deterministic_dispatch_operation_id"
        ],
        "owner_reservation_operation_id": intent["owner_reservation_operation_id"],
        "h1_normal_site_intent_id": intent["h1_normal_site_intent_id"],
        "h1_normal_site_callback_result_id": (
            callback_result["h1_normal_site_callback_result_id"]
            if callback_result is not None
            else _typed_null("SITE_HAS_NO_CALLBACK_RESULT")
        ),
        "previous_normal_site_event_commit_id": (
            previous_event["h1_normal_site_event_commit_id"]
            if previous_event is not None
            else _typed_null("NORMAL_PREFIX_GENESIS")
        ),
        "outcome": outcome,
        "reservation_upper": intent["reservation_upper"],
        "native_observed_value": (
            native_value if native_value is not None else _typed_null("NO_EXACT_NATIVE_VALUE")
        ),
        "value_basis": value_basis if value_basis is not None else _typed_null("NO_VALUE_BASIS"),
        "callback_invocation_count": callback_count,
        "callback_exception_type": callback_exception,
        "owner_record_refs": dict(owner_refs),
        "owner_journal_sequence_before_site": intent[
            "owner_journal_sequence_before_site"
        ],
        "owner_journal_head_id_before_site": intent["owner_journal_head_id_before_site"],
        "owner_journal_sequence_after_site": owner_sequence_after,
        "owner_journal_head_id_after_site": owner_head_after,
        "owner_appended_records": owner_delta,
        "declared_first_failure": outcome != "SUCCESS",
        "anchored_transition_semantics_present": (
            outcome == "SUCCESS" or outcome in intent["failure_outcomes"]
        ),
        "supplemental_protocol_abort": (
            outcome == dispatch_v1.ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
        ),
        "normal_forward_dispatch_allowed_after_event": (
            outcome == "SUCCESS" and intent["ordinal"] < PREFIX_END_ORDINAL
        ),
        "event_durable_exactly_once": True,
        "callback_result_durable_before_settlement": callback_result is not None,
        "callback_invocation_may_have_occurred": (
            callback_result["callback_invocation_may_have_occurred"]
            if callback_result is not None
            else False
        ),
        "first_failure_is_provisional_prefix_only": outcome != "SUCCESS",
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "certificate_issued": False,
        "infeasibility_certified": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "h1_normal_site_event_commit_id": _content_id(EVENT_DOMAIN, payload),
    }
    return H1NormalSiteEventCommitV1(
        _EVENT_ISSUER, canonical_json_bytes(document)
    )


def _recover_cap_rejection_locked(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    intent: Mapping[str, Any],
    root_fd: int,
    directory_fd: int,
    state: owner_v3._ReplayState,
) -> tuple[owner_v3.H1SharedCapRejectionResultV3, owner_v3._ReplayState]:
    gate_state, commit, acknowledgement = rejection_v1._observe_gate_locked(
        lease.rejection_gate,
        lease._gate_directory_fd,
        advance_cursor=True,
    )
    if commit is None or gate_state is rejection_v1.H1AttemptRejectionGateStateV1.OPEN:
        _protocol("expected local cap rejection is absent")
    if (
        commit.shared_owner_profile_core_id != lease.owner.profile.profile_id
        or commit.source_kind is not rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER
        or commit.rejection_request_id != intent["rejection_request_id"]
        or commit.site_key != intent["site_key"]
        or commit.path != intent["resource_path"]
        or commit.reservation_upper != intent["reservation_upper"]
        or commit.candidate != intent["admission_candidate"]
        or commit.hard_cap != intent["hard_cap"]
        or commit.decision_point_id != lease.owner.profile.decision_point_id
        or commit.transaction_id != lease.owner.profile.transaction_id
    ):
        _protocol("attempt-wide rejection is not the dangling normal-site rejection")
    admission = state.rejection_admissions.get(commit.rejection_request_id)
    if admission is None:
        if state.rejection_admissions or state.rejection_commit_id is not None:
            _protocol("Owner journal contains a different rejection frontier")
        document, candidate = owner_v3._reservation_document_for_request(
            lease.owner.owner,
            state,
            operation_id=intent["deterministic_dispatch_operation_id"],
            site_key=intent["site_key"],
            path=intent["resource_path"],
            reservation_upper=intent["reservation_upper"],
        )
        if (
            candidate != intent["admission_candidate"]
            or document["rejection_request_id"] != commit.rejection_request_id
            or document["record_kind"] != "REJECTION_ADMISSION_DURABLE"
        ):
            _protocol("recovered rejection no longer matches its Owner prestate")
        owner_v3._append_record(
            root_fd,
            directory_fd,
            lease.owner.owner,
            state,
            schema="acfqp.k7_h1_shared_cap_reservation.v3",
            kind="REJECTION_ADMISSION_DURABLE",
            extra={
                key: value
                for key, value in document.items()
                if key
                in owner_v3._EXTRA_FIELDS[
                    "acfqp.k7_h1_shared_cap_reservation.v3"
                ]
            },
        )
        state = owner_v3._replay_records_fd(directory_fd, lease.owner.owner)
    else:
        owner_v3._require_rejection_context(lease.owner.owner, state, commit)
    pair = owner_v3._find_pair_for_subject(state, commit.commit_id)
    if pair is None:
        pair = owner_v3._append_rejection_pair_locked(
            root_fd,
            directory_fd,
            lease.owner.owner,
            state,
            commit,
        )
        state = owner_v3._replay_records_fd(directory_fd, lease.owner.owner)
    if acknowledgement is None:
        acknowledgement = _direct_ack_locked(lease, commit, pair)
    elif (
        acknowledgement.receipt_id != owner_v3._record_id(pair[0])
        or acknowledgement.event_id != owner_v3._record_id(pair[1])
        or acknowledgement.snapshot_id != owner_v3._record_id(pair[2])
    ):
        _protocol("recovered gate ACK differs from the Owner rejection pair")
    rejection_v1._observe_gate_locked(
        lease.rejection_gate,
        lease._gate_directory_fd,
        advance_cursor=True,
    )
    state = owner_v3._replay_records_fd(directory_fd, lease.owner.owner)
    return (
        owner_v3.H1SharedCapRejectionResultV3(
            commit,
            pair[0],
            pair[1],
            pair[2],
            acknowledgement,
        ),
        state,
    )


def _commit_event_locked(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    journal_state: _JournalState,
    event: H1NormalSiteEventCommitV1,
) -> H1NormalSiteEventCommitV1:
    _publish_record_locked(
        lease.handle,
        lease._journal_root_fd,
        lease._journal_directory_fd,
        dict(event.document),
    )
    replayed = _replay_journal_locked(
        lease.handle,
        lease._journal_root_fd,
        lease._journal_directory_fd,
        lease._journal_cursor_fd,
        repair=True,
    )
    if (
        not replayed.events
        or replayed.events[-1]["h1_normal_site_event_commit_id"] != event.event_id
    ):
        _protocol("normal-site event did not become the unique durable tail")
    return event


def _callback_failure_outcome(intent: Mapping[str, Any]) -> str:
    preferred = (
        "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
        if intent["operation"] in {"MEMORY_BIND", "MOUNT_OPEN", "LAUNCH_CHILD"}
        else "CALLBACK_FAILED_AFTER_ADMISSION"
    )
    if preferred not in intent["failure_outcomes"]:
        _protocol("normal-prefix transition lacks its callback-failure edge")
    return preferred


def _event_after_owner_change(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    journal_state: _JournalState,
    intent: Mapping[str, Any],
    callback_result: Mapping[str, Any] | None,
    *,
    outcome: str,
    native_value: int | None,
    value_basis: str | None,
    owner_refs: Mapping[str, Any],
    owner_rows: list[dict[str, Any]],
) -> H1NormalSiteEventCommitV1:
    sequence = len(owner_rows)
    head: Any = (
        owner_v3._verify_record_identity(dict(owner_rows[-1]))
        if owner_rows
        else _typed_null("JOURNAL_GENESIS")
    )
    before = intent["owner_journal_sequence_before_site"]
    event = _event_document(
        lease,
        journal_state,
        intent,
        callback_result,
        outcome=outcome,
        native_value=native_value,
        value_basis=value_basis,
        owner_refs=owner_refs,
        owner_sequence_after=sequence,
        owner_head_after=head,
        owner_delta=_owner_delta(owner_rows, before),
    )
    return _commit_event_locked(lease, journal_state, event)


def _expected_owner_tail(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    journal_state: _JournalState,
) -> tuple[int, Any]:
    if journal_state.events:
        last = journal_state.events[-1]
        return (
            last["owner_journal_sequence_after_site"],
            last["owner_journal_head_id_after_site"],
        )
    return (
        lease.handle.spec.payload["owner_baseline_journal_sequence"],
        lease.handle.spec.payload["owner_baseline_journal_head_id"],
    )


def _verify_durable_event_owner_deltas(
    journal_state: _JournalState,
    owner_rows: list[dict[str, Any]],
) -> None:
    for event in journal_state.events:
        before = event["owner_journal_sequence_before_site"]
        after = event["owner_journal_sequence_after_site"]
        if not (0 <= before <= after <= len(owner_rows)):
            _protocol("normal-site event names an impossible Owner sequence interval")
        before_head: Any = (
            owner_v3._verify_record_identity(dict(owner_rows[before - 1]))
            if before
            else _typed_null("JOURNAL_GENESIS")
        )
        after_head: Any = (
            owner_v3._verify_record_identity(dict(owner_rows[after - 1]))
            if after
            else _typed_null("JOURNAL_GENESIS")
        )
        expected_delta = _owner_delta(owner_rows[:after], before)
        if (
            event["owner_journal_head_id_before_site"] != before_head
            or event["owner_journal_head_id_after_site"] != after_head
            or event["owner_appended_records"] != expected_delta
        ):
            _protocol("normal-site event differs from its exact Owner record interval")


def _verify_owner_prefix_for_intent(
    intent: Mapping[str, Any],
    owner_rows: list[dict[str, Any]],
    gate_commit: rejection_v1.H1AttemptRejectionCommitV1 | None,
) -> None:
    before = intent["owner_journal_sequence_before_site"]
    if before > len(owner_rows):
        _protocol("Owner journal rolled back below the durable normal-site intent")
    head: Any = (
        owner_v3._verify_record_identity(dict(owner_rows[before - 1]))
        if before
        else _typed_null("JOURNAL_GENESIS")
    )
    if head != intent["owner_journal_head_id_before_site"]:
        _protocol("Owner prefix at durable normal-site intent changed")
    suffix = owner_rows[before:]
    if not suffix:
        return

    expected_rejection = (
        intent["expected_admission_outcome"] == "REJECTED_BEFORE_SIDE_EFFECT"
    )
    first = suffix[0]
    if (
        first.get("schema") != "acfqp.k7_h1_shared_cap_reservation.v3"
        or first.get("operation_id")
        != intent["deterministic_dispatch_operation_id"]
        or first.get("site_key") != intent["site_key"]
        or first.get("path") != intent["resource_path"]
        or first.get("reducer") != intent["reducer"]
        or first.get("reservation_upper") != intent["reservation_upper"]
        or first.get("admission_candidate") != intent["admission_candidate"]
    ):
        _protocol("Owner suffix after durable intent belongs to another site")

    if expected_rejection:
        if (
            len(suffix) > 4
            or first.get("record_kind") != "REJECTION_ADMISSION_DURABLE"
            or first.get("admission_outcome")
            != "REJECTED_BEFORE_SIDE_EFFECT"
            or first.get("rejection_request_id") != intent["rejection_request_id"]
            or gate_commit is None
            or gate_commit.rejection_request_id != intent["rejection_request_id"]
        ):
            _protocol("Owner rejection suffix differs from its durable intent")
        if len(suffix) >= 2:
            receipt = suffix[1]
            if (
                receipt.get("schema")
                != "acfqp.k7_h1_shared_cap_receipt.v3"
                or receipt.get("record_kind") != "RECEIPT_DURABLE"
                or receipt.get("subject_kind") != "CAP_REJECTION"
                or receipt.get("subject_id") != gate_commit.commit_id
            ):
                _protocol("Owner rejection receipt crossed its durable intent")
        if len(suffix) >= 3:
            event = suffix[2]
            if (
                event.get("schema") != "acfqp.k7_h1_shared_cap_event.v3"
                or event.get("record_kind") != "EVENT_DURABLE"
                or event.get("h1_shared_cap_owner_v3_receipt_id")
                != owner_v3._record_id(suffix[1])
                or event.get("subject_kind") != "CAP_REJECTION"
                or event.get("subject_id") != gate_commit.commit_id
            ):
                _protocol("Owner rejection event crossed its durable intent")
        if len(suffix) == 4:
            snapshot = suffix[3]
            if (
                snapshot.get("schema") != "acfqp.k7_h1_shared_cap_snapshot.v3"
                or snapshot.get("record_kind") != "SNAPSHOT_DURABLE"
                or snapshot.get("h1_shared_cap_owner_v3_receipt_id")
                != owner_v3._record_id(suffix[1])
                or snapshot.get("h1_shared_cap_owner_v3_event_id")
                != owner_v3._record_id(suffix[2])
            ):
                _protocol("Owner rejection snapshot crossed its durable intent")
        return

    if (
        len(suffix) > 7
        or first.get("record_kind") != "RESERVATION_DURABLE"
        or first.get("admission_outcome") != "ADMITTED"
        or first.get("rejection_request_id") != _typed_null("CAP_NOT_EXCEEDED")
    ):
        _protocol("Owner admitted suffix differs from its durable intent")
    reservation_id = owner_v3._record_id(first)
    if intent["handler_mode"] == dispatch_v1.H1LifecycleHandlerModeV1.DEFERRED_ORIGIN.value:
        if len(suffix) != 1:
            _protocol("deferred-origin Owner suffix continued before its event")
        return
    if len(suffix) >= 2:
        cell = suffix[1]
        if (
            cell.get("schema") != "acfqp.k7_h1_shared_cap_native_cell.v3"
            or cell.get("record_kind") != "NATIVE_CELL_DURABLE"
            or cell.get("h1_shared_cap_owner_v3_reservation_id") != reservation_id
            or cell.get("operation_id")
            != intent["deterministic_dispatch_operation_id"]
            or cell.get("path") != intent["resource_path"]
        ):
            _protocol("Owner native-cell suffix crossed its durable intent")
    if len(suffix) >= 3:
        evidence = suffix[2]
        if (
            evidence.get("schema")
            != "acfqp.k7_h1_shared_cap_native_evidence.v3"
            or evidence.get("record_kind") != "NATIVE_EVIDENCE_DURABLE"
            or evidence.get("h1_shared_cap_owner_v3_reservation_id")
            != reservation_id
            or evidence.get("h1_shared_cap_owner_v3_native_cell_id")
            != owner_v3._record_id(suffix[1])
            or evidence.get("operation_id")
            != intent["deterministic_dispatch_operation_id"]
            or evidence.get("path") != intent["resource_path"]
            or evidence.get("evidence_source_id")
            != intent["native_evidence_source_id"]
        ):
            _protocol("Owner native-evidence suffix crossed its durable intent")
    if len(suffix) >= 4:
        settlement = suffix[3]
        if (
            settlement.get("schema")
            != "acfqp.k7_h1_shared_cap_settlement.v3"
            or settlement.get("record_kind") != "SETTLEMENT_DURABLE"
            or settlement.get("h1_shared_cap_owner_v3_reservation_id")
            != reservation_id
            or settlement.get("h1_shared_cap_owner_v3_native_evidence_id")
            != owner_v3._record_id(suffix[2])
            or settlement.get("operation_id")
            != intent["deterministic_dispatch_operation_id"]
            or settlement.get("path") != intent["resource_path"]
        ):
            _protocol("Owner settlement suffix crossed its durable intent")
    if len(suffix) >= 5:
        receipt = suffix[4]
        settlement_id = owner_v3._record_id(suffix[3])
        if (
            receipt.get("schema") != "acfqp.k7_h1_shared_cap_receipt.v3"
            or receipt.get("record_kind") != "RECEIPT_DURABLE"
            or receipt.get("subject_kind") != "SETTLEMENT"
            or receipt.get("subject_id") != settlement_id
        ):
            _protocol("Owner settlement receipt crossed its durable intent")
    if len(suffix) >= 6:
        event = suffix[5]
        if (
            event.get("schema") != "acfqp.k7_h1_shared_cap_event.v3"
            or event.get("record_kind") != "EVENT_DURABLE"
            or event.get("h1_shared_cap_owner_v3_receipt_id")
            != owner_v3._record_id(suffix[4])
            or event.get("subject_kind") != "SETTLEMENT"
            or event.get("subject_id") != owner_v3._record_id(suffix[3])
        ):
            _protocol("Owner settlement event crossed its durable intent")
    if len(suffix) == 7:
        snapshot = suffix[6]
        if (
            snapshot.get("schema") != "acfqp.k7_h1_shared_cap_snapshot.v3"
            or snapshot.get("record_kind") != "SNAPSHOT_DURABLE"
            or snapshot.get("h1_shared_cap_owner_v3_receipt_id")
            != owner_v3._record_id(suffix[4])
            or snapshot.get("h1_shared_cap_owner_v3_event_id")
            != owner_v3._record_id(suffix[5])
        ):
            _protocol("Owner settlement snapshot crossed its durable intent")


def _verify_intent_owner_semantics(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    directory_fd: int,
    intent: Mapping[str, Any],
) -> None:
    prestate = owner_v3._replay_records_fd(
        directory_fd,
        lease.owner.owner,
        stop_after_sequence=intent["owner_journal_sequence_before_site"],
    )
    document, candidate = owner_v3._reservation_document_for_request(
        lease.owner.owner,
        prestate,
        operation_id=intent["deterministic_dispatch_operation_id"],
        site_key=intent["site_key"],
        path=intent["resource_path"],
        reservation_upper=intent["reservation_upper"],
    )
    limit = owner_v3._limit(lease.owner.profile, intent["resource_path"])
    if (
        candidate != intent["admission_candidate"]
        or limit.hard_cap != intent["hard_cap"]
        or document["rejection_request_id"] != intent["rejection_request_id"]
        or document["admission_outcome"] != intent["expected_admission_outcome"]
    ):
        _protocol("durable normal-site intent differs from its exact Owner prestate")


def _capture_callback_lease_authority(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
) -> tuple[tuple[Any, ...], ...]:
    rows: list[tuple[Any, ...]] = []
    pending: list[tuple[str, Any]] = [("lease", lease)]
    seen: set[int] = set()
    while pending:
        path, current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if not dataclasses.is_dataclass(current) or isinstance(current, type):
            continue
        fields = tuple(dataclasses.fields(current))
        rows.append(
            (
                "DATACLASS_OBJECT",
                path,
                current,
                type(current),
                tuple(field.name for field in fields),
            )
        )
        for dataclass_field in fields:
            value = getattr(current, dataclass_field.name)
            rows.append(
                (
                    "DATACLASS_FIELD",
                    path,
                    current,
                    dataclass_field.name,
                    value,
                    repr(value),
                )
            )
            if dataclasses.is_dataclass(value) and not isinstance(value, type):
                pending.append((f"{path}.{dataclass_field.name}", value))
    return tuple(rows)


def _require_callback_lease_authority_unchanged(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    state: tuple[tuple[Any, ...], ...],
) -> None:
    if lease._site_consumed is not True:
        lease._site_consumed = True
        lease._active = False
        _fail("normal-prefix callback changed consumed lease authority")
    for row in state:
        kind = row[0]
        if kind == "DATACLASS_OBJECT":
            _, path, original, original_type, field_names = row
            if (
                type(original) is not original_type
                or tuple(field.name for field in dataclasses.fields(original))
                != field_names
            ):
                lease._site_consumed = True
                lease._active = False
                _fail("normal-prefix callback changed authority object: " + path)
        elif kind == "DATACLASS_FIELD":
            _, path, original, field_name, expected, expected_repr = row
            current = getattr(original, field_name)
            if current is not expected or repr(current) != expected_repr:
                lease._site_consumed = True
                lease._active = False
                _fail(
                    "normal-prefix callback changed authority field: "
                    + path
                    + "."
                    + field_name
                )
        else:  # pragma: no cover - issuer-owned exhaustive rows
            _fail("normal-prefix callback authority snapshot is malformed")


def _invoke_callback(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    intent: Mapping[str, Any],
    callback: Callable[[], Any],
) -> H1NormalSiteCallbackResultV1:
    module_namespace = globals()
    getpid = os.getpid
    get_ident = threading.get_ident
    callback_pid = getpid()
    callback_thread_id = get_ident()
    local_guard = _IMPORT_LOCAL_AUTHORITY_GUARD
    local_guard_code = _IMPORT_LOCAL_AUTHORITY_GUARD_CODE
    local_state = _IMPORT_LOCAL_AUTHORITY_STATE
    dependency_guard = _IMPORT_DEPENDENCY_GUARD
    dependency_guard_code = _IMPORT_DEPENDENCY_GUARD_CODE
    import_authority_bindings = (
        ("_IMPORT_LOCAL_AUTHORITY_STATE", local_state),
        ("_IMPORT_LOCAL_AUTHORITY_GUARD", local_guard),
        ("_IMPORT_LOCAL_AUTHORITY_GUARD_CODE", local_guard_code),
        ("_IMPORT_DEPENDENCY_GUARD", dependency_guard),
        ("_IMPORT_DEPENDENCY_GUARD_CODE", dependency_guard_code),
    )
    restore_guard = _restore_local_authority_state_after_callback
    restore_guard_code = restore_guard.__code__
    lease_guard = _require_callback_lease_authority_unchanged
    lease_guard_code = lease_guard.__code__
    lease_state = _capture_callback_lease_authority(lease)
    canonicalizer = canonical_json_bytes
    intent_bytes = canonicalizer(intent)
    authority_error = ConstructionK7H1PhaseAwareNormalPrefixV1Error
    returned: Any = None
    callback_error: BaseException | None = None
    try:
        returned = callback()
    except BaseException as error:
        callback_error = error
    try:
        if getpid() != callback_pid or get_ident() != callback_thread_id:
            raise H1NormalPrefixForkedCallbackContinuationV1(
                "fork child cannot publish parent callback authority"
            )
        if (
            local_guard.__code__ is not local_guard_code
            or dependency_guard.__code__ is not dependency_guard_code
            or lease_guard.__code__ is not lease_guard_code
            or restore_guard.__code__ is not restore_guard_code
            or globals().get("_require_local_authority_namespace_unchanged")
            is not local_guard
            or globals().get("_require_dependency_namespace_unchanged")
            is not dependency_guard
            or globals().get("_require_callback_lease_authority_unchanged")
            is not lease_guard
            or globals().get("_restore_local_authority_state_after_callback")
            is not restore_guard
            or any(
                globals().get(name) is not expected
                for name, expected in import_authority_bindings
            )
        ):
            raise authority_error(
                "normal-prefix callback mutated its authority guards"
            )
        local_guard(local_state)
        dependency_guard(full=True)
        lease_guard(lease, lease_state)
        if canonicalizer(intent) != intent_bytes:
            raise authority_error(
                "normal-prefix callback changed its durable intent input"
            )
        _require_live_lease(lease)
    except BaseException:
        try:
            for name, expected in import_authority_bindings:
                module_namespace[name] = expected
            restore_guard(local_state, module_namespace)
            local_guard(local_state)
            dependency_guard(full=True)
        except BaseException:
            module_namespace["_LOCAL_AUTHORITY_POISONED"] = True
        lease._site_consumed = True
        lease._active = False
        raise
    if callback_error is not None:
        return _callback_document(
            lease,
            intent,
            result_kind="CALLBACK_EXCEPTION",
            native_value=None,
            exception_type=type(callback_error).__name__,
        )
    if intent["handler_mode"] == dispatch_v1.H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value:
        return _callback_document(
            lease,
            intent,
            result_kind="UNIT_CALLBACK_RETURNED",
            native_value=None,
            exception_type=None,
        )
    if type(returned) is not int or returned < 0:
        return _callback_document(
            lease,
            intent,
            result_kind="INVALID_NONNEGATIVE_MAGNITUDE",
            native_value=None,
            exception_type="InvalidNonnegativeMagnitudeResult",
        )
    return _callback_document(
        lease,
        intent,
        result_kind="MAGNITUDE_RETURNED",
        native_value=returned,
        exception_type=None,
    )


def _settlement_semantics_from_callback(
    intent: Mapping[str, Any],
    callback_result: Mapping[str, Any],
) -> tuple[owner_v3.H1SharedValueBasisV3, int | None, str, str | None]:
    kind = callback_result["callback_result_kind"]
    if kind == "UNIT_CALLBACK_RETURNED":
        return (
            owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT,
            1,
            "SUCCESS",
            owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT.value,
        )
    if kind == "MAGNITUDE_RETURNED":
        native = callback_result["native_observed_value"]
        if type(native) is not int or native < 0:
            _protocol("durable magnitude callback result changed type")
        basis = (
            owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN
            if native > intent["reservation_upper"]
            else owner_v3.H1SharedValueBasisV3.EXACT_NATIVE
        )
        return basis, native, "SUCCESS", basis.value
    if kind in {
        "CALLBACK_EXCEPTION",
        "INVALID_NONNEGATIVE_MAGNITUDE",
        "NATIVE_CELL_WITHOUT_DURABLE_CALLBACK_RESULT",
    }:
        basis = owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER
        return basis, None, _callback_failure_outcome(intent), basis.value
    _protocol("normal-prefix callback result kind is unknown")


def execute_next_h1_phase_aware_normal_site_v1(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
    *,
    callback: Callable[[], Any] | None = None,
    crash_point: H1NormalPrefixCrashPointV1 = H1NormalPrefixCrashPointV1.NONE,
) -> H1NormalSiteEventCommitV1 | H1NormalPrefixSnapshotV1:
    lease = _require_live_lease(lease)
    if lease._site_consumed:
        _fail("one phase-aware lease can consume at most one normal-site authority")
    try:
        fault = H1NormalPrefixCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1PhaseAwareNormalPrefixV1Error(
            "normal-prefix crash point is invalid"
        ) from error
    journal_state = _replay_journal_locked(
        lease.handle,
        lease._journal_root_fd,
        lease._journal_directory_fd,
        lease._journal_cursor_fd,
        repair=True,
    )
    closed_prefix = journal_state.failed or len(journal_state.events) == PREFIX_END_ORDINAL
    row: dict[str, Any] | None = None
    handler: dict[str, Any] | None = None
    dangling = journal_state.dangling_intent
    if not closed_prefix:
        row, handler = _next_site(lease, journal_state)
        if dangling is None:
            if handler["callback_required"] is True and not callable(callback):
                _fail("the next normal-prefix site requires a callback before intent")
            if handler["callback_required"] is False and callback is not None:
                _fail("the next normal-prefix site forbids a callback")
        elif (
            dangling["ordinal"] != row["ordinal"]
            or dangling["site_key"] != row["site_key"]
            or dangling["handler_mode"] != handler["handler_mode"]
            or dangling["callback_required"] != handler["callback_required"]
        ):
            _protocol("dangling normal-site intent differs from the frozen next site")

    gate_state, gate_commit, _gate_ack = rejection_v1._observe_gate_locked(
        lease.rejection_gate,
        lease._gate_directory_fd,
        advance_cursor=True,
    )
    owner_root_fd = owner_directory_fd = -1
    try:
        owner_root_fd, owner_directory_fd, owner_state = owner_v3._require_handle_locked(
            lease.owner.owner
        )
        owner_sequence, owner_head, owner_rows = _owner_tail_records(owner_directory_fd)
        _verify_durable_event_owner_deltas(journal_state, owner_rows)
        expected_sequence, expected_head = _expected_owner_tail(lease, journal_state)
        if closed_prefix:
            if owner_sequence != expected_sequence or owner_head != expected_head:
                _protocol("Owner tail changed after the durable normal-prefix event")
            return _snapshot_from_state(
                lease.handle,
                journal_state,
                owner_tail_verified_under_composite_lease=True,
            )
        assert row is not None and handler is not None
        if dangling is None:
            if gate_state is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN:
                _protocol("attempt gate closed before the next normal-site intent")
            if owner_sequence != expected_sequence or owner_head != expected_head:
                _protocol("Owner journal changed outside the durable normal-prefix chain")
            owner_v3._require_owner_open_join(owner_state)
            intent_object = _build_intent(
                lease, journal_state, owner_state, row, handler
            )
            lease._site_consumed = True
            _publish_record_locked(
                lease.handle,
                lease._journal_root_fd,
                lease._journal_directory_fd,
                dict(intent_object.document),
            )
            journal_state = _replay_journal_locked(
                lease.handle,
                lease._journal_root_fd,
                lease._journal_directory_fd,
                lease._journal_cursor_fd,
                repair=True,
            )
            dangling = journal_state.dangling_intent
            if dangling is None:
                _protocol("normal-site intent did not become the unique durable tail")
            if fault is H1NormalPrefixCrashPointV1.AFTER_INTENT_FSYNC:
                raise H1NormalPrefixInjectedCrashV1("crash after durable normal-site intent")
        else:
            lease._site_consumed = True
            _verify_owner_prefix_for_intent(dangling, owner_rows, gate_commit)

        intent = dangling
        assert intent is not None
        _verify_intent_owner_semantics(lease, owner_directory_fd, intent)
        expected_rejection = intent["expected_admission_outcome"] == "REJECTED_BEFORE_SIDE_EFFECT"
        if gate_state is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN:
            if not expected_rejection or gate_commit is None:
                _protocol("foreign attempt rejection crossed a normal-site intent")
            rejection_result, owner_state = _recover_cap_rejection_locked(
                lease,
                intent,
                owner_root_fd,
                owner_directory_fd,
                owner_state,
            )
            _, _, owner_rows = _owner_tail_records(owner_directory_fd)
            event = _event_after_owner_change(
                lease,
                journal_state,
                intent,
                None,
                outcome="CAP_REJECTED_BEFORE_SIDE_EFFECT",
                native_value=None,
                value_basis=None,
                owner_refs=_rejection_refs(rejection_result),
                owner_rows=owner_rows,
            )
            if fault is H1NormalPrefixCrashPointV1.AFTER_EVENT_FSYNC:
                raise H1NormalPrefixInjectedCrashV1("crash after durable normal-site event")
            return event

        operation_id = intent["deterministic_dispatch_operation_id"]
        reservation_id = owner_state.reservation_by_operation.get(operation_id)
        reservation: owner_v3.H1SharedReservationV3 | None = (
            owner_v3.H1SharedReservationV3(owner_state.reservations[reservation_id])
            if reservation_id is not None
            else None
        )
        if reservation is None:
            reservation, rejection_result, owner_state = _reserve_locked(
                lease,
                owner_root_fd,
                owner_directory_fd,
                owner_state,
                operation_id=operation_id,
                site_key=intent["site_key"],
                path=intent["resource_path"],
                reservation_upper=intent["reservation_upper"],
            )
            if rejection_result is not None:
                _, _, owner_rows = _owner_tail_records(owner_directory_fd)
                event = _event_after_owner_change(
                    lease,
                    journal_state,
                    intent,
                    None,
                    outcome="CAP_REJECTED_BEFORE_SIDE_EFFECT",
                    native_value=None,
                    value_basis=None,
                    owner_refs=_rejection_refs(rejection_result),
                    owner_rows=owner_rows,
                )
                if fault is H1NormalPrefixCrashPointV1.AFTER_EVENT_FSYNC:
                    raise H1NormalPrefixInjectedCrashV1(
                        "crash after durable cap-rejection event"
                    )
                return event
            if fault is H1NormalPrefixCrashPointV1.AFTER_RESERVATION_FSYNC:
                raise H1NormalPrefixInjectedCrashV1("crash after durable reservation")
        if reservation is None:  # pragma: no cover - exhaustive above
            _protocol("normal-site admission lost its reservation")

        if intent["handler_mode"] == dispatch_v1.H1LifecycleHandlerModeV1.DEFERRED_ORIGIN.value:
            _, _, owner_rows = _owner_tail_records(owner_directory_fd)
            event = _event_after_owner_change(
                lease,
                journal_state,
                intent,
                None,
                outcome="SUCCESS",
                native_value=None,
                value_basis=None,
                owner_refs=_reservation_only_refs(reservation),
                owner_rows=owner_rows,
            )
            if fault is H1NormalPrefixCrashPointV1.AFTER_EVENT_FSYNC:
                raise H1NormalPrefixInjectedCrashV1("crash after durable deferred-origin event")
            return event

        callback_document = journal_state.callbacks.get(intent["ordinal"])
        reservation_id = reservation.reservation_id
        cell = owner_state.cells.get(reservation_id)
        if callback_document is None:
            if cell is None:
                if not callable(callback):
                    return _snapshot_from_state(
                        lease.handle,
                        journal_state,
                        callback_required_to_resume=True,
                        owner_tail_verified_under_composite_lease=True,
                    )
                _cell, owner_state = _start_cell_locked(
                    lease.owner.owner,
                    owner_root_fd,
                    owner_directory_fd,
                    owner_state,
                    reservation,
                )
                if fault is H1NormalPrefixCrashPointV1.AFTER_NATIVE_CELL_FSYNC:
                    raise H1NormalPrefixInjectedCrashV1("crash after durable native cell")
                callback_object = _invoke_callback(lease, intent, callback)
            else:
                callback_object = _callback_document(
                    lease,
                    intent,
                    result_kind="NATIVE_CELL_WITHOUT_DURABLE_CALLBACK_RESULT",
                    native_value=None,
                    exception_type="DurableCallbackResultMissingAfterNativeCell",
                    callback_invocation_count=0,
                    callback_invocation_may_have_occurred=True,
                )
            _require_live_lease(lease)
            _publish_record_locked(
                lease.handle,
                lease._journal_root_fd,
                lease._journal_directory_fd,
                dict(callback_object.document),
            )
            journal_state = _replay_journal_locked(
                lease.handle,
                lease._journal_root_fd,
                lease._journal_directory_fd,
                lease._journal_cursor_fd,
                repair=True,
            )
            callback_document = journal_state.callbacks[intent["ordinal"]]
            if fault is H1NormalPrefixCrashPointV1.AFTER_CALLBACK_RESULT_FSYNC:
                raise H1NormalPrefixInjectedCrashV1(
                    "crash after durable callback-result record"
                )

        _require_live_lease(lease)
        basis, native_value, nominal_outcome, value_basis = (
            _settlement_semantics_from_callback(intent, callback_document)
        )
        settlement, overrun, owner_state = _settle_locked(
            lease.owner.owner,
            owner_root_fd,
            owner_directory_fd,
            owner_state,
            reservation,
            basis=basis,
            native_observed_value=native_value,
            evidence_source_id=intent["native_evidence_source_id"],
        )
        if fault is H1NormalPrefixCrashPointV1.AFTER_SETTLEMENT_FSYNC:
            raise H1NormalPrefixInjectedCrashV1("crash after durable settlement")
        outcome = nominal_outcome
        if overrun:
            outcome = "OBSERVED_UPPER_BOUND_VIOLATION"
            if outcome not in intent["failure_outcomes"]:
                outcome = dispatch_v1.ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
        _, _, owner_rows = _owner_tail_records(owner_directory_fd)
        event = _event_after_owner_change(
            lease,
            journal_state,
            intent,
            callback_document,
            outcome=outcome,
            native_value=native_value,
            value_basis=value_basis,
            owner_refs=_settlement_refs(settlement),
            owner_rows=owner_rows,
        )
        if fault is H1NormalPrefixCrashPointV1.AFTER_EVENT_FSYNC:
            raise H1NormalPrefixInjectedCrashV1("crash after durable normal-site event")
        return event
    finally:
        if owner_directory_fd >= 0:
            os.close(owner_directory_fd)
        if owner_root_fd >= 0:
            os.close(owner_root_fd)


def recover_pending_h1_phase_aware_normal_site_v1(
    lease: H1PhaseAwareNormalPrefixLeaseV1,
) -> H1NormalSiteEventCommitV1 | H1NormalPrefixSnapshotV1:
    """Recover without accepting a callback and therefore never reexecute one."""

    lease = _require_live_lease(lease)
    state = _replay_journal_locked(
        lease.handle,
        lease._journal_root_fd,
        lease._journal_directory_fd,
        lease._journal_cursor_fd,
        repair=True,
    )
    if state.dangling_intent is None:
        return _snapshot_from_state(lease.handle, state)
    return execute_next_h1_phase_aware_normal_site_v1(lease, callback=None)


_IMPORT_LOCAL_AUTHORITY_STATE = _capture_local_authority_state()
_IMPORT_LOCAL_AUTHORITY_GUARD = _require_local_authority_namespace_unchanged
_IMPORT_LOCAL_AUTHORITY_GUARD_CODE = (
    _require_local_authority_namespace_unchanged.__code__
)
_IMPORT_DEPENDENCY_GUARD = _require_dependency_namespace_unchanged
_IMPORT_DEPENDENCY_GUARD_CODE = _require_dependency_namespace_unchanged.__code__


__all__ = (
    "ConstructionK7H1PhaseAwareNormalPrefixV1Error",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "CLEANUP_EXECUTION_AUTHORITY_PRESENT",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1NormalPrefixForkedCallbackContinuationV1",
    "H1NormalPrefixCrashPointV1",
    "H1NormalPrefixHandleV1",
    "H1NormalPrefixInjectedCrashV1",
    "H1NormalPrefixProtocolFailureV1",
    "H1NormalPrefixSnapshotV1",
    "H1NormalPrefixSpecV1",
    "H1NormalPrefixStatusV1",
    "H1NormalSiteCallbackResultV1",
    "H1NormalSiteEventCommitV1",
    "H1NormalSiteIntentV1",
    "H1PhaseAwareNormalPrefixLeaseV1",
    "NO_EVENT_RECOVERY_COMPLETE",
    "NORMAL_PREFIX_1_40_DURABLE_HAPPY_PATH_PRESENT",
    "NORMAL_PREFIX_1_40_PRETRANSITION_EVENT_RECOVERY_PRESENT",
    "NORMAL_PREFIX_1_40_NO_EVENT_RECOVERY_COMPLETE",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PHASE_AWARE_CAP_REJECTION_RECOVERY_PRESENT",
    "PHASE_AWARE_CAP_REJECTION_PAIR_ACK_EVENT_PRETRANSITION_RECOVERY_PRESENT",
    "PHASE_AWARE_FAILURE_TO_CLEANUP_TRANSITION_PRESENT",
    "PHASE_AWARE_NORMAL_PREFIX_1_40_PRESENT",
    "PHASE_AWARE_NORMAL_PREFIX_PRETRANSITION_1_40_PRESENT",
    "PREFIX_END_ORDINAL",
    "PRODUCTION_EXECUTION_AUTHORITY_PRESENT",
    "PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "execute_next_h1_phase_aware_normal_site_v1",
    "freeze_h1_normal_prefix_spec_v1",
    "hold_h1_phase_aware_normal_prefix_lease_v1",
    "initialize_h1_normal_prefix_journal_v1",
    "inspect_h1_normal_prefix_semantic_closure_candidate_v1",
    "open_h1_normal_prefix_journal_v1",
    "recover_pending_h1_phase_aware_normal_site_v1",
    "replay_h1_normal_prefix_journal_v1",
)
