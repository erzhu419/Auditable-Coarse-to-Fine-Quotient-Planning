"""Anchored construction dispatcher for the frozen 62-site H1 lifecycle.

This module turns the caller-pinned Git-object snapshot from Contract 2.0.59-A
into a typed construction handler registry and an ordered in-memory dispatch
trace.  Resource handlers use the durable Owner-V3 reserve/guard/settle
protocol introduced by Contract 2.0.59-B.  The old Owner-V2 method strings in
the snapshot are checked as migration annotations only and are never resolved
with ``getattr``.

The boundary is deliberately narrow.  Callback return values are construction
assertions, dispatch events are not durable exactly-once records, and neither
the loaded Python bytes nor live production hooks are externally anchored.
Consequently this module issues no source, native-evidence, route, accounting,
terminal, or official-execution authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import hmac
from pathlib import Path
import subprocess
from types import FunctionType
from typing import Any, Callable, Mapping, NoReturn

from acfqp import (
    construction_k7_h1_lifecycle_local_main_anchor_independent_verifier_v1
    as anchor_v1,
)
from acfqp import construction_k7_h1_production_lifecycle_source_candidate_v1 as candidate_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_ANCHORED_LIFECYCLE_HANDLER_REGISTRY_V1_DOMAIN,
    CONSTRUCTION_K7_H1_ANCHORED_LIFECYCLE_PROGRAM_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_TRACE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-C"
PROFILE_KEY = "construction_k7_h1_anchored_lifecycle_dispatch_v1"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_EXECUTION_AUTHORIZED = False
SOURCE_AUTHORITY_PRESENT = False
NATIVE_EVIDENCE_AUTHORITY_PRESENT = False
PRODUCTION_LIVE_HOOKS_COMPLETE = False
CLEANUP_CONTINUATION_COMPLETE = False
OUTPUT_LEAF_JOIN_BOUND = False
CURRENT_ACCESS_ATOMIC_BRIDGE_PRESENT = False
JOINT_OUTPUT_READ_FIXED_POINT_PRESENT = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
PREFIX_VERIFICATION_ATTESTATION_ISSUED = False

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION = (
    "ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION"
)

HANDLER_REGISTRY_DOMAIN = (
    CONSTRUCTION_K7_H1_ANCHORED_LIFECYCLE_HANDLER_REGISTRY_V1_DOMAIN
)
ANCHORED_PROGRAM_DOMAIN = CONSTRUCTION_K7_H1_ANCHORED_LIFECYCLE_PROGRAM_V1_DOMAIN
DISPATCH_PROFILE_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_PROFILE_V1_DOMAIN
DISPATCH_EVENT_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_EVENT_V1_DOMAIN
DISPATCH_TRACE_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_TRACE_V1_DOMAIN
SNAPSHOT_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1_DOMAIN
PROGRAM_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    HANDLER_REGISTRY_DOMAIN,
    ANCHORED_PROGRAM_DOMAIN,
    DISPATCH_PROFILE_DOMAIN,
    DISPATCH_EVENT_DOMAIN,
    DISPATCH_TRACE_DOMAIN,
    SNAPSHOT_DOMAIN,
    PROGRAM_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover - central registry invariant
    raise RuntimeError("anchored lifecycle dispatcher domains are not registered")


SHARED_RESOURCE_PATHS = owner_v3.SHARED_RESOURCE_PATHS
PATH_REDUCERS = owner_v3.PATH_REDUCERS
PROGRAM_SNAPSHOT_REPOSITORY_PATH = anchor_v1.PROGRAM_SNAPSHOT_REPOSITORY_PATH
LIFECYCLE_CANDIDATE_REPOSITORY_PATH = (
    "src/acfqp/construction_k7_h1_production_lifecycle_source_candidate_v1.py"
)

_CID_PATTERN_LENGTH = 64
_TYPED_NULL_KEYS = frozenset({"kind", "reason"})
_TRANSITION_FIELDS = frozenset(
    {
        "ordinal",
        "site_key",
        "phase",
        "operation",
        "resource_path",
        "owner_role",
        "intended_owner_method_string",
        "owner_method_semantic_identity_bound",
        "from_state",
        "success_state",
        "reservation_edge",
        "ambiguity_role",
        "failure_edges",
    }
)
_FAILURE_EDGE_FIELDS = frozenset(
    {
        "outcome",
        "current_site_admitted",
        "side_effect_may_have_started",
        "native_existence",
        "provisional_primary_cause_class",
        "provisional_primary_cause_code",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "certificate_issued",
        "infeasibility_certified",
    }
)
_EXPECTED_OPERATION_COUNTS = {
    "MEMORY_BIND": 1,
    "COMMON_HASH": 1,
    "COMMON_INTEGRITY": 1,
    "COMMON_PROTOCOL": 1,
    "OUTPUT_RESERVE": 1,
    "STAGE_INPUT": 10,
    "MOUNT_OPEN": 10,
    "LAUNCH_CHILD": 2,
    "READ_INPUT": 10,
    "READ_BUSINESS_RESULT": 3,
    "DESCENDANT_REAP": 1,
    "SAME_OFD_PEAK_READ": 1,
    "MOUNT_CLOSE": 10,
    "OUTPUT_ROLE_READBACK": 8,
    "OUTPUT_FINALIZE": 1,
    "OUTPUT_CLOSE": 1,
}
_UNIT_OPERATIONS = frozenset(
    {"COMMON_HASH", "COMMON_INTEGRITY", "COMMON_PROTOCOL", "LAUNCH_CHILD"}
)
_MAGNITUDE_OPERATIONS = frozenset(
    {
        "STAGE_INPUT",
        "MOUNT_OPEN",
        "READ_INPUT",
        "READ_BUSINESS_RESULT",
        "OUTPUT_ROLE_READBACK",
    }
)
_NO_CHARGE_OPERATIONS = frozenset(
    {"DESCENDANT_REAP", "MOUNT_CLOSE", "OUTPUT_CLOSE"}
)
_DEFERRED_ORIGINS = {
    "memory:bind-working-hierarchy": "memory:read-retained-same-ofd-peak",
    "output:reserve-route-wide": "output:finalize-route-wide",
}
_DEFERRED_COMPLETIONS = {value: key for key, value in _DEFERRED_ORIGINS.items()}


class ConstructionK7H1AnchoredLifecycleDispatchV1Error(ValueError):
    """The anchored program, registry, profile, event, or trace failed closed."""


class H1LifecycleDispatchProtocolFailureV1(
    ConstructionK7H1AnchoredLifecycleDispatchV1Error
):
    failure_kind = "PROTOCOL_FAILURE"
    certificate_issued = False
    infeasibility_certified = False


class H1LifecycleHandlerModeV1(str, Enum):
    IMMEDIATE_UNIT = "IMMEDIATE_UNIT_SETTLEMENT"
    IMMEDIATE_MAGNITUDE = "IMMEDIATE_MAGNITUDE_SETTLEMENT"
    DEFERRED_ORIGIN = "DEFERRED_ORIGIN_ADMISSION_ONLY"
    DEFERRED_COMPLETION = "DEFERRED_COMPLETION"
    NO_CHARGE_CONTROL = "NO_CHARGE_LIFECYCLE_CONTROL"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1AnchoredLifecycleDispatchV1Error(message)


def _protocol(message: str) -> NoReturn:
    raise H1LifecycleDispatchProtocolFailureV1(message)


def _cid(value: Any, label: str) -> str:
    try:
        parsed = parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AnchoredLifecycleDispatchV1Error(
            f"{label} is not a canonical content ID"
        ) from error
    return parsed


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be one nonempty exact string")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _is_typed_null(value: Any) -> bool:
    return (
        type(value) is dict
        and frozenset(value) == _TYPED_NULL_KEYS
        and value.get("kind") == "NOT_APPLICABLE"
        and type(value.get("reason")) is str
        and bool(value["reason"])
    )


def _frozen_json(value: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(dict(value))


def _thaw(raw: bytes) -> dict[str, Any]:
    value = loads_canonical_json(raw)
    if type(value) is not dict:
        _fail("frozen dispatcher row is not one object")
    return value


def _git_blob(root: Path, commit_id: str, repository_path: str) -> bytes:
    environment = {
        "GIT_NO_REPLACE_OBJECTS": "1",
        "HOME": str(root),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "TZ": "UTC",
    }
    try:
        tree = subprocess.run(
            (
                "/usr/bin/git",
                "--no-replace-objects",
                "-C",
                str(root),
                "ls-tree",
                commit_id,
                "--",
                repository_path,
            ),
            check=True,
            capture_output=True,
            env=environment,
        ).stdout.decode("ascii", errors="strict").strip()
        fields = tree.split(None, 3)
        if (
            len(fields) != 4
            or fields[0] != "100644"
            or fields[1] != "blob"
            or fields[3] != repository_path
        ):
            _fail("anchored lifecycle snapshot Git tree row is malformed")
        raw = subprocess.run(
            (
                "/usr/bin/git",
                "--no-replace-objects",
                "-C",
                str(root),
                "cat-file",
                "blob",
                fields[2],
            ),
            check=True,
            capture_output=True,
            env=environment,
        ).stdout
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as error:
        raise ConstructionK7H1AnchoredLifecycleDispatchV1Error(
            "anchored lifecycle snapshot Git-object read failed"
        ) from error
    if not raw:
        _fail("anchored lifecycle snapshot Git blob is empty")
    return bytes(raw)


def _stable_code_value(value: Any) -> Any:
    if type(value) is type(_stable_code_value.__code__):
        return _stable_code_document(value)
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is bytes:
        return {"bytes_hex": value.hex()}
    if type(value) is tuple:
        return [_stable_code_value(child) for child in value]
    return {"type": type(value).__qualname__, "repr": repr(value)}


def _stable_code_document(code: Any) -> dict[str, Any]:
    return {
        "argcount": code.co_argcount,
        "posonlyargcount": code.co_posonlyargcount,
        "kwonlyargcount": code.co_kwonlyargcount,
        "nlocals": code.co_nlocals,
        "stacksize": code.co_stacksize,
        "flags": code.co_flags,
        "code_hex": code.co_code.hex(),
        "constants": [_stable_code_value(value) for value in code.co_consts],
        "names": list(code.co_names),
        "varnames": list(code.co_varnames),
        "freevars": list(code.co_freevars),
        "cellvars": list(code.co_cellvars),
    }


def _callable_code_id(function: Callable[..., Any]) -> str:
    if type(function) is not FunctionType:
        _fail("Owner-V3 dispatch entrypoint is not one Python function")
    payload = canonical_json_bytes(
        {
            "module": function.__module__,
            "qualname": function.__qualname__,
            "code": _stable_code_document(function.__code__),
        }
    )
    return hashlib.sha256(b"acfqp:k7-h1-dispatch-callable:v1\x00" + payload).hexdigest()


_OWNER_ENTRYPOINTS: dict[str, Callable[..., Any]] = {
    "reserve": owner_v3.reserve_h1_shared_cap_owner_v3,
    "hold": owner_v3.hold_h1_shared_cap_owner_v3_side_effect,
    "settle": owner_v3.settle_h1_shared_cap_owner_v3,
    "replay": owner_v3.replay_h1_shared_cap_owner_v3,
    "index": owner_v3.inspect_h1_shared_cap_owner_v3_record_index,
}
_OWNER_ENTRYPOINT_CODE_IDS = {
    name: _callable_code_id(function) for name, function in _OWNER_ENTRYPOINTS.items()
}
_OWNER_PREFIX_INDEX_ENTRYPOINT = (
    owner_v3.inspect_h1_shared_cap_owner_v3_record_prefix
)


def _owner_function_dependency_closure(
    root_name: str,
) -> dict[str, Callable[..., Any]]:
    pending = [root_name]
    closure: dict[str, Callable[..., Any]] = {}
    namespace = vars(owner_v3)
    while pending:
        name = pending.pop()
        if name in closure:
            continue
        function = namespace.get(name)
        if (
            type(function) is not FunctionType
            or function.__module__ != owner_v3.__name__
        ):
            _protocol("Owner-V3 prefix dependency closure changed")
        closure[name] = function
        for dependency_name in function.__code__.co_names:
            dependency = namespace.get(dependency_name)
            if (
                type(dependency) is FunctionType
                and dependency.__module__ == owner_v3.__name__
                and dependency_name not in closure
            ):
                pending.append(dependency_name)
    return dict(sorted(closure.items()))


_OWNER_PREFIX_DEPENDENCY_FUNCTIONS = _owner_function_dependency_closure(
    "inspect_h1_shared_cap_owner_v3_record_prefix"
)
_OWNER_PREFIX_DEPENDENCY_CODE_IDS = {
    name: _callable_code_id(function)
    for name, function in _OWNER_PREFIX_DEPENDENCY_FUNCTIONS.items()
}


def _verify_owner_entrypoints() -> None:
    current = {
        "reserve": owner_v3.reserve_h1_shared_cap_owner_v3,
        "hold": owner_v3.hold_h1_shared_cap_owner_v3_side_effect,
        "settle": owner_v3.settle_h1_shared_cap_owner_v3,
        "replay": owner_v3.replay_h1_shared_cap_owner_v3,
        "index": owner_v3.inspect_h1_shared_cap_owner_v3_record_index,
    }
    for name, frozen in _OWNER_ENTRYPOINTS.items():
        if current[name] is not frozen or not hmac.compare_digest(
            _callable_code_id(frozen), _OWNER_ENTRYPOINT_CODE_IDS[name]
        ):
            _protocol("Owner-V3 dispatch entrypoint changed before native work")


def _verify_owner_prefix_index_entrypoint() -> None:
    current = _owner_function_dependency_closure(
        "inspect_h1_shared_cap_owner_v3_record_prefix"
    )
    if set(current) != set(_OWNER_PREFIX_DEPENDENCY_FUNCTIONS):
        _protocol("Owner-V3 prefix dependency set changed before verification")
    for name, frozen in _OWNER_PREFIX_DEPENDENCY_FUNCTIONS.items():
        if current[name] is not frozen or not hmac.compare_digest(
            _callable_code_id(current[name]),
            _OWNER_PREFIX_DEPENDENCY_CODE_IDS[name],
        ):
            _protocol("Owner-V3 prefix dependency changed before verification")


def _operation_id(profile_id: str, ordinal: int, site_key: str) -> str:
    payload = canonical_json_bytes(
        {
            "dispatch_profile_id": profile_id,
            "ordinal": ordinal,
            "site_key": site_key,
        }
    )
    return hashlib.sha256(
        b"acfqp:k7-h1-dispatch-operation:v1\x00" + payload
    ).hexdigest()


def _owner_reservation_operation_id(
    profile_id: str,
    row: Mapping[str, Any],
) -> str | None:
    site_key = row["site_key"]
    if site_key in _DEFERRED_COMPLETIONS:
        origin = _DEFERRED_COMPLETIONS[site_key]
        return _operation_id(profile_id, 1 if origin.startswith("memory:") else 5, origin)
    if row["reservation_edge"] is True:
        return _operation_id(profile_id, row["ordinal"], site_key)
    return None


def _evidence_source_id(profile_id: str, ordinal: int, site_key: str) -> str:
    payload = canonical_json_bytes(
        {
            "dispatch_profile_id": profile_id,
            "ordinal": ordinal,
            "site_key": site_key,
            "authority": "CALLER_CONSTRUCTION_CALLBACK_ONLY",
        }
    )
    return hashlib.sha256(
        b"acfqp:k7-h1-dispatch-construction-evidence:v1\x00" + payload
    ).hexdigest()


def _resource_path(row: Mapping[str, Any]) -> str | None:
    value = row["resource_path"]
    if _is_typed_null(value):
        return None
    if type(value) is not str or value not in SHARED_RESOURCE_PATHS:
        _fail("anchored transition contains an invalid shared path")
    return value


def _handler_mode(row: Mapping[str, Any]) -> H1LifecycleHandlerModeV1:
    operation = row["operation"]
    site_key = row["site_key"]
    if operation in _UNIT_OPERATIONS:
        return H1LifecycleHandlerModeV1.IMMEDIATE_UNIT
    if operation in _MAGNITUDE_OPERATIONS:
        return H1LifecycleHandlerModeV1.IMMEDIATE_MAGNITUDE
    if site_key in _DEFERRED_ORIGINS:
        return H1LifecycleHandlerModeV1.DEFERRED_ORIGIN
    if site_key in _DEFERRED_COMPLETIONS:
        return H1LifecycleHandlerModeV1.DEFERRED_COMPLETION
    if operation in _NO_CHARGE_OPERATIONS:
        return H1LifecycleHandlerModeV1.NO_CHARGE_CONTROL
    _fail("anchored lifecycle operation has no typed Owner-V3 handler")


def _failure_outcomes(row: Mapping[str, Any]) -> tuple[str, ...]:
    edges = row["failure_edges"]
    if type(edges) is not list or not edges:
        _fail("anchored transition failure edges are malformed")
    outcomes: list[str] = []
    for edge in edges:
        if type(edge) is not dict or frozenset(edge) != _FAILURE_EDGE_FIELDS:
            _fail("anchored transition failure-edge fields are not exact")
        outcome = _nonempty(edge["outcome"], "anchored failure outcome")
        if outcome == "SUCCESS" or outcome in outcomes:
            _fail("anchored transition failure outcomes are invalid")
        outcomes.append(outcome)
    return tuple(outcomes)


def _pair_site(row: Mapping[str, Any]) -> str | None:
    site_key = row["site_key"]
    if site_key in _DEFERRED_ORIGINS:
        return _DEFERRED_ORIGINS[site_key]
    if site_key in _DEFERRED_COMPLETIONS:
        return _DEFERRED_COMPLETIONS[site_key]
    if row["operation"] == "MOUNT_OPEN":
        return site_key.replace("mount-open:", "mount-close:", 1)
    if row["operation"] == "MOUNT_CLOSE":
        return site_key.replace("mount-close:", "mount-open:", 1)
    return None


def _owner_protocol(mode: H1LifecycleHandlerModeV1, site_key: str) -> list[str]:
    if mode in {
        H1LifecycleHandlerModeV1.IMMEDIATE_UNIT,
        H1LifecycleHandlerModeV1.IMMEDIATE_MAGNITUDE,
    }:
        return ["reserve", "hold", "construction_callback", "settle"]
    if mode is H1LifecycleHandlerModeV1.DEFERRED_ORIGIN:
        # Owner V3 intentionally blocks unrelated appends while a native cell
        # is started but unsettled.  The two long-lived origins are therefore
        # admission-only in this construction boundary; their real native
        # starts remain a live-hook obligation for the later activation stage.
        return ["reserve"]
    if mode is H1LifecycleHandlerModeV1.DEFERRED_COMPLETION:
        return ["reuse_reservation", "hold", "construction_callback", "settle"]
    return ["construction_callback"]


def _handler_row(row: Mapping[str, Any]) -> dict[str, Any]:
    mode = _handler_mode(row)
    path = _resource_path(row)
    charged_path = (
        None if mode is H1LifecycleHandlerModeV1.NO_CHARGE_CONTROL else path
    )
    pair_site = _pair_site(row)
    return {
        "ordinal": row["ordinal"],
        "site_key": row["site_key"],
        "phase": row["phase"],
        "operation": row["operation"],
        "owner_role": row["owner_role"],
        "resource_path": (
            charged_path
            if charged_path is not None
            else _typed_null("NO_SHARED_COST_LEAF")
        ),
        "contextual_resource_path": (
            path if path is not None else _typed_null("NO_CONTEXTUAL_RESOURCE_PATH")
        ),
        "reducer": (
            PATH_REDUCERS[charged_path]
            if charged_path is not None
            else _typed_null("NO_REDUCER")
        ),
        "handler_mode": mode.value,
        "owner_v3_protocol": _owner_protocol(mode, row["site_key"]),
        "owner_v3_callable_code_ids": {
            name: _OWNER_ENTRYPOINT_CODE_IDS[name]
            for name in ("reserve", "hold", "settle")
            if name in _owner_protocol(mode, row["site_key"])
        },
        "reservation_edge": row["reservation_edge"],
        "paired_site_key": (
            pair_site if pair_site is not None else _typed_null("NO_PAIRED_SITE")
        ),
        "legacy_owner_v2_method_annotation": row[
            "intended_owner_method_string"
        ],
        "legacy_owner_v2_method_semantic_identity_bound": row[
            "owner_method_semantic_identity_bound"
        ],
        "legacy_method_used_for_dispatch": False,
        "failure_outcomes": list(_failure_outcomes(row)),
        "callback_required": row["operation"]
        not in {"MEMORY_BIND", "OUTPUT_RESERVE"},
        "callback_value_kind": (
            "UNIT_EVENT"
            if mode is H1LifecycleHandlerModeV1.IMMEDIATE_UNIT
            else "NONNEGATIVE_MAGNITUDE"
            if mode is H1LifecycleHandlerModeV1.IMMEDIATE_MAGNITUDE
            or mode is H1LifecycleHandlerModeV1.DEFERRED_COMPLETION
            else "CONTROL_ONLY"
            if row["operation"] not in {"MEMORY_BIND", "OUTPUT_RESERVE"}
            else "NONE"
        ),
        "native_evidence_authority_present": False,
        "production_hook_bound": False,
    }


def _verify_snapshot(
    raw: bytes,
    *,
    repository_root: Path,
    parent_commit_id: str,
    expected_snapshot_id: str,
    expected_program_id: str,
    expected_analysis_id: str,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    try:
        snapshot = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AnchoredLifecycleDispatchV1Error(
            "anchored lifecycle snapshot is not canonical JSON"
        ) from error
    if type(snapshot) is not dict:
        _fail("anchored lifecycle snapshot is not one object")
    snapshot_payload = dict(snapshot)
    claimed_snapshot_id = _cid(
        snapshot_payload.pop("h1_lifecycle_program_snapshot_id", None),
        "anchored lifecycle snapshot",
    )
    if (
        content_id(SNAPSHOT_DOMAIN, snapshot_payload) != claimed_snapshot_id
        or claimed_snapshot_id != expected_snapshot_id
    ):
        _fail("anchored lifecycle snapshot identity changed")
    program = snapshot.get("program")
    if type(program) is not dict:
        _fail("anchored lifecycle snapshot contains no program object")
    program_payload = dict(program)
    claimed_program_id = _cid(
        program_payload.pop("h1_production_lifecycle_program_id", None),
        "anchored lifecycle program",
    )
    if (
        content_id(PROGRAM_DOMAIN, program_payload) != claimed_program_id
        or claimed_program_id != expected_program_id
        or snapshot.get("branch_analysis_id") != expected_analysis_id
    ):
        _fail("anchored lifecycle program or branch-analysis identity changed")
    rows = program.get("transitions")
    if type(rows) is not list or len(rows) != 62:
        _fail("anchored lifecycle program must contain exactly 62 sites")
    counts: dict[str, int] = {}
    sites: set[str] = set()
    failure_edge_count = 0
    previous_state = "STATE_INITIAL"
    paths: set[str] = set()
    frozen_rows: list[dict[str, Any]] = []
    for ordinal, original in enumerate(rows, start=1):
        if type(original) is not dict or frozenset(original) != _TRANSITION_FIELDS:
            _fail("anchored lifecycle transition fields are not exact")
        row = dict(original)
        if row["ordinal"] != ordinal or row["from_state"] != previous_state:
            _fail("anchored lifecycle transition order or state chain changed")
        site = _nonempty(row["site_key"], "anchored lifecycle site")
        if site in sites or row["success_state"] != f"STATE_AFTER_{site}":
            _fail("anchored lifecycle site is duplicated or has a wrong successor")
        sites.add(site)
        previous_state = row["success_state"]
        operation = _nonempty(row["operation"], "anchored lifecycle operation")
        counts[operation] = counts.get(operation, 0) + 1
        path = _resource_path(row)
        if path is not None:
            paths.add(path)
        outcomes = _failure_outcomes(row)
        failure_edge_count += len(outcomes)
        frozen_rows.append(row)
    if (
        counts != _EXPECTED_OPERATION_COUNTS
        or paths != set(SHARED_RESOURCE_PATHS)
        or failure_edge_count != 143
        or snapshot.get("branch_count") != 144
        or program.get("transition_count") != 62
        or rows[0]["operation"] != "MEMORY_BIND"
        or rows[-1]["operation"] != "OUTPUT_CLOSE"
    ):
        _fail("anchored lifecycle program cardinalities or boundary order changed")
    expected_candidate_path = (
        repository_root / LIFECYCLE_CANDIDATE_REPOSITORY_PATH
    ).resolve(strict=True)
    loaded_candidate_path = Path(candidate_v1.__file__).resolve(strict=True)
    pinned_candidate_source = _git_blob(
        repository_root,
        parent_commit_id,
        LIFECYCLE_CANDIDATE_REPOSITORY_PATH,
    )
    if (
        loaded_candidate_path != expected_candidate_path
        or expected_candidate_path.read_bytes() != pinned_candidate_source
    ):
        _fail("loaded lifecycle candidate source differs from the anchored Git blob")
    candidate_document = dict(
        candidate_v1.registered_h1_production_lifecycle_program_candidate_v1().to_document()
    )
    # Exact source bytes were checked above.  ``ast.dump`` is not byte-stable
    # across supported Python minor versions, so the same bytes can produce a
    # different source-manifest ID and therefore a different program ID.  Only
    # those two derived identities are normalized for the secondary structural
    # comparison; every program field remains exact.
    candidate_document["h1_production_lifecycle_source_manifest_id"] = program[
        "h1_production_lifecycle_source_manifest_id"
    ]
    candidate_document["h1_production_lifecycle_program_id"] = program[
        "h1_production_lifecycle_program_id"
    ]
    if not hmac.compare_digest(
        canonical_json_bytes(program), canonical_json_bytes(candidate_document)
    ):
        _fail("loaded candidate cross-check differs from the anchored Git program")
    return dict(program), tuple(frozen_rows)


_REGISTRY_ISSUER = object()
_PROGRAM_ISSUER = object()
_BUNDLE_ISSUER = object()
_PROFILE_ISSUER = object()
_EVENT_ISSUER = object()
_TRACE_ISSUER = object()
_SESSION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1AnchoredLifecycleHandlerRegistryV1:
    _issuer: InitVar[object]
    provenance_id: str
    snapshot_id: str
    program_id: str
    _handler_rows: tuple[bytes, ...] = field(repr=False)
    _registry_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REGISTRY_ISSUER:
            _fail("anchored lifecycle handler registry is verifier-issued only")
        for value in (self.provenance_id, self.snapshot_id, self.program_id):
            _cid(value, "handler-registry identity")
        if len(self._handler_rows) != 62:
            _fail("handler registry must contain exactly 62 frozen rows")
        object.__setattr__(
            self, "_registry_id", content_id(HANDLER_REGISTRY_DOMAIN, self._payload())
        )

    @property
    def handlers(self) -> tuple[dict[str, Any], ...]:
        return tuple(_thaw(raw) for raw in self._handler_rows)

    def _payload(self) -> dict[str, Any]:
        handlers = [dict(row) for row in self.handlers]
        mode_counts: dict[str, int] = {}
        for row in handlers:
            mode_counts[row["handler_mode"]] = mode_counts.get(row["handler_mode"], 0) + 1
        return {
            "schema": "acfqp.k7_h1_anchored_lifecycle_handler_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_caller_pinned_lifecycle_provenance_id": self.provenance_id,
            "lifecycle_program_snapshot_id": self.snapshot_id,
            "lifecycle_program_id": self.program_id,
            "handler_count": len(handlers),
            "handler_mode_counts": mode_counts,
            "reservation_site_count": sum(
                1 for row in handlers if row["reservation_edge"] is True
            ),
            "immediate_settlement_site_count": sum(
                1
                for row in handlers
                if row["handler_mode"]
                in {
                    H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value,
                    H1LifecycleHandlerModeV1.IMMEDIATE_MAGNITUDE.value,
                }
            ),
            "deferred_origin_site_count": sum(
                1
                for row in handlers
                if row["handler_mode"]
                == H1LifecycleHandlerModeV1.DEFERRED_ORIGIN.value
            ),
            "deferred_completion_site_count": sum(
                1
                for row in handlers
                if row["handler_mode"]
                == H1LifecycleHandlerModeV1.DEFERRED_COMPLETION.value
            ),
            "no_charge_control_site_count": sum(
                1
                for row in handlers
                if row["handler_mode"]
                == H1LifecycleHandlerModeV1.NO_CHARGE_CONTROL.value
            ),
            "handlers": handlers,
            "legacy_owner_v2_strings_are_annotations_only": True,
            "dynamic_getattr_dispatch_forbidden": True,
            "owner_v3_callable_binding_is_construction_local": True,
            "loaded_execution_bytes_verified": False,
            "source_authority_present": False,
            "native_evidence_authority_present": False,
            "production_live_hooks_complete": False,
        }

    @property
    def registry_id(self) -> str:
        current = content_id(HANDLER_REGISTRY_DOMAIN, self._payload())
        if not hmac.compare_digest(current, self._registry_id):
            _fail("anchored lifecycle handler registry changed")
        return self._registry_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_anchored_lifecycle_handler_registry_id": self.registry_id,
        }


@dataclass(frozen=True, slots=True)
class H1AnchoredLifecycleProgramV1:
    _issuer: InitVar[object]
    anchor_id: str
    provenance_id: str
    snapshot_id: str
    program_id: str
    branch_analysis_id: str
    source_manifest_id: str
    execution_topology_profile_id: str
    output_branch_dag_id: str
    handler_registry_id: str
    _transition_rows: tuple[bytes, ...] = field(repr=False)
    _anchored_program_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROGRAM_ISSUER:
            _fail("anchored lifecycle program is verifier-issued only")
        for value in (
            self.anchor_id,
            self.provenance_id,
            self.snapshot_id,
            self.program_id,
            self.branch_analysis_id,
            self.source_manifest_id,
            self.execution_topology_profile_id,
            self.output_branch_dag_id,
            self.handler_registry_id,
        ):
            _cid(value, "anchored-program identity")
        if len(self._transition_rows) != 62:
            _fail("anchored lifecycle program lost one of its 62 sites")
        object.__setattr__(
            self,
            "_anchored_program_id",
            content_id(ANCHORED_PROGRAM_DOMAIN, self._payload()),
        )

    @property
    def transitions(self) -> tuple[dict[str, Any], ...]:
        return tuple(_thaw(raw) for raw in self._transition_rows)

    def _payload(self) -> dict[str, Any]:
        rows = [dict(row) for row in self.transitions]
        return {
            "schema": "acfqp.k7_h1_anchored_lifecycle_program.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_lifecycle_local_main_anchor_id": self.anchor_id,
            "h1_caller_pinned_lifecycle_provenance_id": self.provenance_id,
            "lifecycle_program_snapshot_id": self.snapshot_id,
            "lifecycle_program_id": self.program_id,
            "lifecycle_branch_analysis_id": self.branch_analysis_id,
            "h1_production_lifecycle_source_manifest_id": self.source_manifest_id,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "h1_production_output_branch_dag_id": self.output_branch_dag_id,
            "h1_anchored_lifecycle_handler_registry_id": self.handler_registry_id,
            "transition_count": len(rows),
            "operation_family_count": len(_EXPECTED_OPERATION_COUNTS),
            "declared_failure_edge_count": sum(
                len(row["failure_edges"]) for row in rows
            ),
            "declared_branch_count": 144,
            "transitions": rows,
            "snapshot_loaded_from_verified_git_blob": True,
            "snapshot_rows_drive_dispatch_order": True,
            "candidate_module_used_only_as_equality_cross_check": True,
            "source_authority_present": False,
            "loaded_execution_bytes_verified": False,
            "toctou_exclusion_present": False,
            "cleanup_continuation_complete": False,
            "output_leaf_join_bound": False,
            "production_live_hooks_complete": False,
        }

    @property
    def anchored_program_id(self) -> str:
        current = content_id(ANCHORED_PROGRAM_DOMAIN, self._payload())
        if not hmac.compare_digest(current, self._anchored_program_id):
            _fail("anchored lifecycle program changed")
        return self._anchored_program_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_anchored_lifecycle_program_id": self.anchored_program_id,
        }


@dataclass(frozen=True, slots=True)
class H1AnchoredLifecycleDispatchBundleV1:
    _issuer: InitVar[object]
    registry: H1AnchoredLifecycleHandlerRegistryV1
    program: H1AnchoredLifecycleProgramV1

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BUNDLE_ISSUER
            or type(self.registry) is not H1AnchoredLifecycleHandlerRegistryV1
            or type(self.program) is not H1AnchoredLifecycleProgramV1
            or self.program.handler_registry_id != self.registry.registry_id
            or self.program.program_id != self.registry.program_id
            or self.program.snapshot_id != self.registry.snapshot_id
            or self.program.provenance_id != self.registry.provenance_id
        ):
            _fail("anchored lifecycle dispatch bundle is caller-minted or crossed")


def freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
    repository_root: str | Path,
    *,
    expected_anchor_id: str,
) -> H1AnchoredLifecycleDispatchBundleV1:
    """Rebuild the dispatch grammar from the caller-pinned Git-object snapshot."""

    expected = _cid(expected_anchor_id, "expected lifecycle anchor")
    root = Path(repository_root).resolve(strict=True)
    anchor = anchor_v1.verify_h1_lifecycle_local_main_anchor_v1(root)
    if not hmac.compare_digest(anchor.anchor_id, expected):
        _fail("verified lifecycle anchor differs from the caller-pinned ID")
    provenance = anchor_v1.inspect_h1_caller_pinned_lifecycle_provenance_v1(
        root,
        expected_anchor_id=expected,
    )
    snapshot_raw = _git_blob(
        root,
        anchor.parent_commit_id,
        PROGRAM_SNAPSHOT_REPOSITORY_PATH,
    )
    _program_document, transitions = _verify_snapshot(
        snapshot_raw,
        repository_root=root,
        parent_commit_id=anchor.parent_commit_id,
        expected_snapshot_id=provenance.program_snapshot_id,
        expected_program_id=provenance.program_id,
        expected_analysis_id=provenance.branch_analysis_id,
    )
    handler_documents = tuple(_handler_row(row) for row in transitions)
    registry = H1AnchoredLifecycleHandlerRegistryV1(
        _REGISTRY_ISSUER,
        provenance.provenance_id,
        provenance.program_snapshot_id,
        provenance.program_id,
        tuple(_frozen_json(row) for row in handler_documents),
    )
    registry_document = registry.to_document()
    if (
        registry_document["handler_mode_counts"]
        != {
            H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value: 5,
            H1LifecycleHandlerModeV1.IMMEDIATE_MAGNITUDE.value: 41,
            H1LifecycleHandlerModeV1.DEFERRED_ORIGIN.value: 2,
            H1LifecycleHandlerModeV1.DEFERRED_COMPLETION.value: 2,
            H1LifecycleHandlerModeV1.NO_CHARGE_CONTROL.value: 12,
        }
        or registry_document["reservation_site_count"] != 48
        or registry_document["immediate_settlement_site_count"] != 46
    ):
        _fail("anchored lifecycle handler partition changed")
    program = H1AnchoredLifecycleProgramV1(
        _PROGRAM_ISSUER,
        anchor.anchor_id,
        provenance.provenance_id,
        provenance.program_snapshot_id,
        provenance.program_id,
        provenance.branch_analysis_id,
        _program_document["h1_production_lifecycle_source_manifest_id"],
        _program_document["h1_execution_topology_profile_id"],
        _program_document["h1_production_output_branch_dag_id"],
        registry.registry_id,
        tuple(_frozen_json(row) for row in transitions),
    )
    return H1AnchoredLifecycleDispatchBundleV1(_BUNDLE_ISSUER, registry, program)


@dataclass(frozen=True, slots=True)
class H1LifecycleDispatchProfileV1:
    _issuer: InitVar[object]
    anchored_program_id: str
    handler_registry_id: str
    owner_profile_id: str
    owner_runtime_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: str
    _site_operands: tuple[tuple[str, int], ...]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("lifecycle dispatch profile is issuer-created only")
        for value in (
            self.anchored_program_id,
            self.handler_registry_id,
            self.owner_profile_id,
            self.owner_runtime_id,
            self.logical_occurrence_id,
            self.route_attempt_id,
            self.decision_point_id,
            self.transaction_id,
        ):
            _cid(value, "dispatch-profile identity")
        if len(self._site_operands) != 48:
            _fail("dispatch profile must freeze exactly 48 reservation operands")
        object.__setattr__(
            self, "_profile_id", content_id(DISPATCH_PROFILE_DOMAIN, self._payload())
        )

    @property
    def site_operands(self) -> dict[str, int]:
        return dict(self._site_operands)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_lifecycle_dispatch_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_anchored_lifecycle_program_id": self.anchored_program_id,
            "h1_anchored_lifecycle_handler_registry_id": self.handler_registry_id,
            "h1_shared_cap_profile_core_v3_id": self.owner_profile_id,
            "h1_shared_cap_owner_v3_runtime_id": self.owner_runtime_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "site_reservation_uppers": [
                {"site_key": site, "reservation_upper": upper}
                for site, upper in self._site_operands
            ],
            "site_operand_count": len(self._site_operands),
            "site_operands_frozen_before_dispatch": True,
            "site_operands_are_construction_assertions": True,
            "numeric_operand_authority_present": False,
            "native_evidence_authority_present": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def profile_id(self) -> str:
        current = content_id(DISPATCH_PROFILE_DOMAIN, self._payload())
        if not hmac.compare_digest(current, self._profile_id):
            _fail("lifecycle dispatch profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_lifecycle_dispatch_profile_id": self.profile_id,
        }


def bind_h1_lifecycle_dispatch_profile_v1(
    bundle: H1AnchoredLifecycleDispatchBundleV1,
    owner: owner_v3.H1SharedCapOwnerV3Handle,
    *,
    site_reservation_uppers: Mapping[str, int],
) -> H1LifecycleDispatchProfileV1:
    """Freeze all 48 construction operands before the first dispatch callback."""

    if (
        type(bundle) is not H1AnchoredLifecycleDispatchBundleV1
        or type(owner) is not owner_v3.H1SharedCapOwnerV3Handle
        or type(site_reservation_uppers) is not dict
    ):
        _fail("dispatch profile requires exact bundle, Owner-V3 handle, and dict")
    program = bundle.program
    registry = bundle.registry
    owner_profile = owner.profile
    if (
        owner_profile.caller_pinned_lifecycle_provenance_id != program.provenance_id
        or owner_profile.lifecycle_program_snapshot_id != program.snapshot_id
        or owner_profile.lifecycle_program_id != program.program_id
        or owner_profile.lifecycle_branch_analysis_id != program.branch_analysis_id
        or owner.source_manifest.caller_pinned_lifecycle_provenance_id
        != program.provenance_id
        or owner.source_manifest.lifecycle_program_snapshot_id != program.snapshot_id
        or owner.source_manifest.lifecycle_program_id != program.program_id
        or owner.source_manifest.lifecycle_branch_analysis_id != program.branch_analysis_id
    ):
        _fail("Owner-V3 identities do not match the anchored lifecycle program")
    handlers = registry.handlers
    reservation_handlers = [row for row in handlers if row["reservation_edge"] is True]
    expected_sites = {row["site_key"] for row in reservation_handlers}
    if set(site_reservation_uppers) != expected_sites:
        _fail("dispatch operands do not cover exactly 48 reservation sites")
    ordered: list[tuple[str, int]] = []
    for row in reservation_handlers:
        site = row["site_key"]
        upper = _nonnegative(site_reservation_uppers[site], "site reservation upper")
        path = row["resource_path"]
        if row["handler_mode"] == H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value:
            if upper != 1:
                _fail("unit-event dispatch operand must equal one")
        limit = owner_profile.limits[SHARED_RESOURCE_PATHS.index(path)]
        if upper > limit.hard_cap:
            _fail("one frozen site operand exceeds its Owner-V3 hard cap")
        ordered.append((site, upper))
    _verify_owner_entrypoints()
    return H1LifecycleDispatchProfileV1(
        _PROFILE_ISSUER,
        program.anchored_program_id,
        registry.registry_id,
        owner_profile.profile_id,
        owner.runtime_id,
        owner_profile.logical_occurrence_id,
        owner_profile.route_attempt_id,
        owner_profile.decision_point_id,
        owner_profile.transaction_id,
        tuple(ordered),
    )


_OWNER_REF_KEYS = (
    "reservation_id",
    "rejection_admission_id",
    "native_cell_id",
    "native_evidence_id",
    "settlement_id",
    "receipt_id",
    "owner_event_id",
    "owner_snapshot_id",
    "rejection_commit_id",
    "rejection_ack_id",
)
_EVENT_DOCUMENT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_lifecycle_dispatch_profile_id",
        "h1_anchored_lifecycle_program_id",
        "h1_anchored_lifecycle_handler_registry_id",
        "h1_shared_cap_profile_core_v3_id",
        "h1_shared_cap_owner_v3_runtime_id",
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
        "previous_dispatch_event_id",
        "outcome",
        "reservation_upper",
        "native_observed_value",
        "value_basis",
        "callback_invocation_count",
        "callback_exception_type",
        "owner_record_refs",
        "owner_journal_sequence_before_event",
        "owner_journal_head_id_before_event",
        "owner_journal_sequence_after_event",
        "owner_journal_head_id_after_event",
        "declared_first_failure",
        "anchored_transition_semantics_present",
        "supplemental_protocol_abort",
        "first_failure_is_provisional_prefix_only",
        "normal_forward_dispatch_allowed_after_event",
        "construction_callback_value_only",
        "native_evidence_authority_present",
        "event_durable_exactly_once",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "certificate_issued",
        "infeasibility_certified",
        "h1_lifecycle_dispatch_event_id",
    }
)
_TRACE_DOCUMENT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_lifecycle_dispatch_profile_id",
        "h1_anchored_lifecycle_program_id",
        "h1_anchored_lifecycle_handler_registry_id",
        "h1_shared_cap_profile_core_v3_id",
        "h1_shared_cap_owner_v3_runtime_id",
        "consumed_event_count",
        "consumed_events",
        "first_failure_event_id",
        "full_declared_success_reached",
        "next_site_key",
        "deferred_reservation_ids",
        "active_mount_open_sites",
        "ambiguous_native_sites",
        "post_admission_protocol_abort_sites",
        "owner_journal_sequence_at_snapshot",
        "owner_journal_head_id_at_snapshot",
        "owner_charged_values_at_snapshot",
        "owner_outstanding_values_at_snapshot",
        "owner_record_ids_at_snapshot",
        "owner_gate_join_status_at_snapshot",
        "owner_rejection_commit_id_at_snapshot",
        "owner_rejection_ack_id_at_snapshot",
        "owner_new_work_allowed_at_snapshot",
        "declared_prefix_replay_complete",
        "declared_first_failure_replay_complete",
        "first_failure_is_provisional_prefix_only",
        "normal_dispatch_closed",
        "event_trace_durable_exactly_once",
        "source_authority_present",
        "loaded_execution_bytes_verified",
        "toctou_exclusion_present",
        "production_live_hooks_complete",
        "cleanup_continuation_complete",
        "output_leaf_join_bound",
        "current_access_atomic_bridge_present",
        "joint_output_read_fixed_point_present",
        "native_evidence_authority_present",
        "formal_v7_route_authority_present",
        "counter_records_issued",
        "work_vector_issued",
        "comparison_vector_issued",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "official_execution_allowed",
        "official_scalar_cost",
        "official_N_break_even",
        "counter_completeness_gate_status",
        "workload_economics_gate_status",
        "sample_efficiency_gate_status",
        "h1_lifecycle_dispatch_trace_id",
    }
)


def _empty_owner_refs() -> dict[str, Any]:
    return {key: _typed_null(f"NO_{key.upper()}") for key in _OWNER_REF_KEYS}


def _settlement_refs(result: owner_v3.H1SharedSettlementResultV3) -> dict[str, Any]:
    return {
        "reservation_id": result.reservation.reservation_id,
        "rejection_admission_id": _typed_null("NO_REJECTION_ADMISSION_ID"),
        "native_cell_id": result.native_cell_document[
            "h1_shared_cap_owner_v3_native_cell_id"
        ],
        "native_evidence_id": result.evidence_document[
            "h1_shared_cap_owner_v3_native_evidence_id"
        ],
        "settlement_id": result.settlement_document[
            "h1_shared_cap_owner_v3_settlement_id"
        ],
        "receipt_id": result.receipt_document[
            "h1_shared_cap_owner_v3_receipt_id"
        ],
        "owner_event_id": result.event_document[
            "h1_shared_cap_owner_v3_event_id"
        ],
        "owner_snapshot_id": result.snapshot_document[
            "h1_shared_cap_owner_v3_snapshot_id"
        ],
        "rejection_commit_id": _typed_null("NO_REJECTION_COMMIT_ID"),
        "rejection_ack_id": _typed_null("NO_REJECTION_ACK_ID"),
    }


def _rejection_refs(
    result: owner_v3.H1SharedCapRejectionResultV3,
    owner_index: Mapping[str, Any],
) -> dict[str, Any]:
    admissions = [
        row
        for row in owner_index["records_by_role"]["rejection_admission"]
        if row["rejection_request_id"] == result.rejection_commit.rejection_request_id
    ]
    if len(admissions) != 1:
        _protocol("cap rejection lacks one exact Owner-V3 admission record")
    return {
        "reservation_id": _typed_null("CAP_REJECTED_BEFORE_RESERVATION"),
        "rejection_admission_id": admissions[0][
            "h1_shared_cap_owner_v3_reservation_id"
        ],
        "native_cell_id": _typed_null("CAP_REJECTED_BEFORE_NATIVE_CELL"),
        "native_evidence_id": _typed_null("CAP_REJECTED_BEFORE_NATIVE_EVIDENCE"),
        "settlement_id": _typed_null("CAP_REJECTED_BEFORE_SETTLEMENT"),
        "receipt_id": result.receipt_document[
            "h1_shared_cap_owner_v3_receipt_id"
        ],
        "owner_event_id": result.event_document[
            "h1_shared_cap_owner_v3_event_id"
        ],
        "owner_snapshot_id": result.snapshot_document[
            "h1_shared_cap_owner_v3_snapshot_id"
        ],
        "rejection_commit_id": result.rejection_commit.commit_id,
        "rejection_ack_id": result.acknowledgement.ack_id,
    }


def _verify_owner_refs_against_index(
    refs: Mapping[str, Any],
    owner_index: Mapping[str, Any],
) -> None:
    role_for_ref = {
        "reservation_id": "reservation",
        "rejection_admission_id": "rejection_admission",
        "native_cell_id": "native_cell",
        "native_evidence_id": "native_evidence",
        "settlement_id": "settlement",
        "receipt_id": "receipt",
        "owner_event_id": "event",
        "owner_snapshot_id": "snapshot",
    }
    ids_by_role = owner_index["record_ids_by_role"]
    for key in _OWNER_REF_KEYS:
        value = refs[key]
        if _is_typed_null(value):
            continue
        parsed = _cid(value, f"dispatch Owner-V3 {key}")
        role = role_for_ref.get(key)
        if role is not None and parsed not in ids_by_role[role]:
            _protocol("dispatch event names an Owner-V3 record absent from replay")
    rejection_commit = refs["rejection_commit_id"]
    if not _is_typed_null(rejection_commit) and (
        rejection_commit != owner_index["rejection_commit_id"]
    ):
        _protocol("dispatch event rejection commit differs from Owner-V3 replay")
    rejection_ack = refs["rejection_ack_id"]
    if not _is_typed_null(rejection_ack) and (
        rejection_ack != owner_index["rejection_ack_id"]
    ):
        _protocol("dispatch event rejection acknowledgement differs from gate replay")


@dataclass(frozen=True, slots=True)
class H1LifecycleDispatchEventV1:
    _issuer: InitVar[object]
    _event_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EVENT_ISSUER:
            _fail("lifecycle dispatch event is dispatcher-issued only")
        document = _thaw(self._event_bytes)
        if frozenset(document) != _EVENT_DOCUMENT_FIELDS:
            _fail("lifecycle dispatch event fields are not exact")
        claimed = _cid(
            document.pop("h1_lifecycle_dispatch_event_id", None),
            "lifecycle dispatch event",
        )
        if content_id(DISPATCH_EVENT_DOMAIN, document) != claimed:
            _fail("lifecycle dispatch event identity is invalid")

    @property
    def document(self) -> dict[str, Any]:
        return _thaw(self._event_bytes)

    @property
    def event_id(self) -> str:
        return _cid(self.document["h1_lifecycle_dispatch_event_id"], "dispatch event")

    @property
    def outcome(self) -> str:
        return self.document["outcome"]

    @property
    def site_key(self) -> str:
        return self.document["site_key"]

    @property
    def canonical_bytes(self) -> bytes:
        return bytes(self._event_bytes)


def _issue_event(
    session: "H1LifecycleConstructionDispatcherV1",
    row: Mapping[str, Any],
    handler: Mapping[str, Any],
    *,
    outcome: str,
    operation_id: str,
    reservation_upper: int | None,
    native_observed_value: int | None,
    value_basis: str | None,
    callback_invocation_count: int,
    callback_exception_type: str | None,
    owner_refs: Mapping[str, Any],
    expected_owner_sequence_delta: int,
) -> H1LifecycleDispatchEventV1:
    previous = session._events[-1].event_id if session._events else None
    _verify_owner_entrypoints()
    owner_index = _OWNER_ENTRYPOINTS["index"](session.owner)
    if (
        owner_index["journal_sequence"]
        != session._owner_journal_sequence + expected_owner_sequence_delta
    ):
        _protocol("Owner-V3 journal changed outside the selected lifecycle handler")
    _verify_owner_refs_against_index(owner_refs, owner_index)
    owner_reservation_operation_id = _owner_reservation_operation_id(
        session.profile.profile_id, row
    )
    payload = {
        "schema": "acfqp.k7_h1_lifecycle_dispatch_event.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_lifecycle_dispatch_profile_id": session.profile.profile_id,
        "h1_anchored_lifecycle_program_id": session.bundle.program.anchored_program_id,
        "h1_anchored_lifecycle_handler_registry_id": session.bundle.registry.registry_id,
        "h1_shared_cap_profile_core_v3_id": session.profile.owner_profile_id,
        "h1_shared_cap_owner_v3_runtime_id": session.profile.owner_runtime_id,
        "logical_occurrence_id": session.profile.logical_occurrence_id,
        "route_attempt_id": session.profile.route_attempt_id,
        "decision_point_id": session.profile.decision_point_id,
        "transaction_id": session.profile.transaction_id,
        "ordinal": row["ordinal"],
        "site_key": row["site_key"],
        "phase": row["phase"],
        "operation": row["operation"],
        "from_state": row["from_state"],
        "success_state": row["success_state"],
        "handler_mode": handler["handler_mode"],
        "resource_path": handler["resource_path"],
        "reducer": handler["reducer"],
        "deterministic_dispatch_operation_id": operation_id,
        "owner_reservation_operation_id": (
            owner_reservation_operation_id
            if owner_reservation_operation_id is not None
            else _typed_null("NO_OWNER_RESERVATION_OPERATION")
        ),
        "previous_dispatch_event_id": (
            previous if previous is not None else _typed_null("DISPATCH_GENESIS")
        ),
        "outcome": outcome,
        "reservation_upper": (
            reservation_upper
            if reservation_upper is not None
            else _typed_null("NO_RESERVATION_AT_THIS_SITE")
        ),
        "native_observed_value": (
            native_observed_value
            if native_observed_value is not None
            else _typed_null("NO_EXACT_NATIVE_VALUE")
        ),
        "value_basis": (
            value_basis if value_basis is not None else _typed_null("NO_VALUE_BASIS")
        ),
        "callback_invocation_count": callback_invocation_count,
        "callback_exception_type": (
            callback_exception_type
            if callback_exception_type is not None
            else _typed_null("NO_CALLBACK_EXCEPTION")
        ),
        "owner_record_refs": dict(owner_refs),
        "owner_journal_sequence_before_event": session._owner_journal_sequence,
        "owner_journal_head_id_before_event": session._owner_journal_head_id,
        "owner_journal_sequence_after_event": owner_index["journal_sequence"],
        "owner_journal_head_id_after_event": owner_index["journal_head_id"],
        "declared_first_failure": (
            outcome != "SUCCESS" and outcome in _failure_outcomes(row)
        ),
        "anchored_transition_semantics_present": (
            outcome == "SUCCESS" or outcome in _failure_outcomes(row)
        ),
        "supplemental_protocol_abort": (
            outcome == ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
        ),
        "first_failure_is_provisional_prefix_only": outcome != "SUCCESS",
        "normal_forward_dispatch_allowed_after_event": (
            outcome == "SUCCESS" and row["ordinal"] < 62
        ),
        "construction_callback_value_only": True,
        "native_evidence_authority_present": False,
        "event_durable_exactly_once": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "certificate_issued": False,
        "infeasibility_certified": False,
    }
    document = {
        **payload,
        "h1_lifecycle_dispatch_event_id": content_id(DISPATCH_EVENT_DOMAIN, payload),
    }
    return H1LifecycleDispatchEventV1(_EVENT_ISSUER, canonical_json_bytes(document))


@dataclass(frozen=True, slots=True)
class H1LifecycleDispatchTraceV1:
    _issuer: InitVar[object]
    _trace_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TRACE_ISSUER:
            _fail("lifecycle dispatch trace is dispatcher-issued only")
        document = _thaw(self._trace_bytes)
        if frozenset(document) != _TRACE_DOCUMENT_FIELDS:
            _fail("lifecycle dispatch trace fields are not exact")
        claimed = _cid(
            document.pop("h1_lifecycle_dispatch_trace_id", None),
            "lifecycle dispatch trace",
        )
        if content_id(DISPATCH_TRACE_DOMAIN, document) != claimed:
            _fail("lifecycle dispatch trace identity is invalid")

    @property
    def trace_id(self) -> str:
        return _cid(
            self.to_document()["h1_lifecycle_dispatch_trace_id"],
            "lifecycle dispatch trace",
        )

    def to_document(self) -> dict[str, Any]:
        return _thaw(self._trace_bytes)

    @property
    def canonical_bytes(self) -> bytes:
        return bytes(self._trace_bytes)


@dataclass(slots=True)
class H1LifecycleConstructionDispatcherV1:
    _issuer: InitVar[object]
    bundle: H1AnchoredLifecycleDispatchBundleV1
    profile: H1LifecycleDispatchProfileV1
    owner: owner_v3.H1SharedCapOwnerV3Handle
    _events: tuple[H1LifecycleDispatchEventV1, ...] = ()
    _deferred: dict[str, owner_v3.H1SharedReservationV3] = field(default_factory=dict)
    _active_mount_sites: list[str] = field(default_factory=list)
    _ambiguous_native_sites: list[str] = field(default_factory=list)
    _post_admission_protocol_abort_sites: list[str] = field(default_factory=list)
    _owner_journal_sequence: int = 0
    _owner_journal_head_id: Any = field(
        default_factory=lambda: _typed_null("JOURNAL_GENESIS")
    )
    _normal_closed: bool = False
    _in_callback: bool = False
    _violation_count: int = 0
    _session_binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SESSION_ISSUER
            or type(self.bundle) is not H1AnchoredLifecycleDispatchBundleV1
            or type(self.profile) is not H1LifecycleDispatchProfileV1
            or type(self.owner) is not owner_v3.H1SharedCapOwnerV3Handle
        ):
            _fail("lifecycle construction dispatcher is issuer-created only")
        object.__setattr__(
            self,
            "_session_binding_id",
            hashlib.sha256(
                b"acfqp:k7-h1-dispatch-session:v1\x00"
                + canonical_json_bytes(
                    {
                        "program_id": self.bundle.program.anchored_program_id,
                        "profile_id": self.profile.profile_id,
                        "owner_runtime_id": self.owner.runtime_id,
                    }
                )
            ).hexdigest(),
        )

    @property
    def events(self) -> tuple[H1LifecycleDispatchEventV1, ...]:
        return tuple(self._events)


def start_h1_lifecycle_construction_dispatch_v1(
    bundle: H1AnchoredLifecycleDispatchBundleV1,
    profile: H1LifecycleDispatchProfileV1,
    owner: owner_v3.H1SharedCapOwnerV3Handle,
) -> H1LifecycleConstructionDispatcherV1:
    if (
        type(bundle) is not H1AnchoredLifecycleDispatchBundleV1
        or type(profile) is not H1LifecycleDispatchProfileV1
        or type(owner) is not owner_v3.H1SharedCapOwnerV3Handle
        or profile.anchored_program_id != bundle.program.anchored_program_id
        or profile.handler_registry_id != bundle.registry.registry_id
        or profile.owner_profile_id != owner.profile.profile_id
        or profile.owner_runtime_id != owner.runtime_id
    ):
        _fail("dispatch session identities are crossed")
    _verify_owner_entrypoints()
    replay = _OWNER_ENTRYPOINTS["index"](owner)
    if (
        replay["journal_sequence"] != 0
        or replay["reservation_count"] != 0
        or replay["settlement_count"] != 0
        or replay["new_work_allowed"] is not True
    ):
        _fail("dispatch session requires one fresh, open Owner-V3 journal")
    session = H1LifecycleConstructionDispatcherV1(
        _SESSION_ISSUER,
        bundle,
        profile,
        owner,
    )
    session._owner_journal_sequence = replay["journal_sequence"]
    session._owner_journal_head_id = replay["journal_head_id"]
    return session


def _validate_session(session: H1LifecycleConstructionDispatcherV1) -> None:
    if type(session) is not H1LifecycleConstructionDispatcherV1:
        _fail("dispatch requires one exact construction session")
    expected = hashlib.sha256(
        b"acfqp:k7-h1-dispatch-session:v1\x00"
        + canonical_json_bytes(
            {
                "program_id": session.bundle.program.anchored_program_id,
                "profile_id": session.profile.profile_id,
                "owner_runtime_id": session.owner.runtime_id,
            }
        )
    ).hexdigest()
    if not hmac.compare_digest(expected, session._session_binding_id):
        _protocol("dispatch session binding changed")
    if len(session._events) > 62:
        _protocol("dispatch session contains too many events")
    _verify_owner_entrypoints()
    owner_index = _OWNER_ENTRYPOINTS["index"](session.owner)
    if (
        owner_index["journal_sequence"] != session._owner_journal_sequence
        or owner_index["journal_head_id"] != session._owner_journal_head_id
    ):
        _protocol("Owner-V3 journal changed outside the dispatch event chain")
    last_failure = (
        session._events[-1]
        if session._events and session._events[-1].outcome != "SUCCESS"
        else None
    )
    if last_failure is not None and last_failure.outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT":
        refs = last_failure.document["owner_record_refs"]
        if (
            owner_index["gate_owner_join_status"] != "LOCAL_ACK_VERIFIED"
            or owner_index["new_work_allowed"] is not False
            or owner_index["rejection_commit_id"] != refs["rejection_commit_id"]
            or owner_index["rejection_ack_id"] != refs["rejection_ack_id"]
        ):
            _protocol("local cap-rejection dispatch differs from attempt-gate replay")
    else:
        expected_new_work = not (
            last_failure is not None
            and last_failure.outcome
            in {
                "OBSERVED_UPPER_BOUND_VIOLATION",
                ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION,
            }
        )
        if (
            owner_index["gate_owner_join_status"] != "OPEN_NO_REJECTION"
            or not _is_typed_null(owner_index["rejection_commit_id"])
            or not _is_typed_null(owner_index["rejection_ack_id"])
            or owner_index["new_work_allowed"] is not expected_new_work
        ):
            _protocol("attempt gate changed outside the dispatch event chain")
    previous: str | None = None
    for ordinal, event in enumerate(session._events, start=1):
        document = event.document
        transition = session.bundle.program.transitions[ordinal - 1]
        if (
            document["ordinal"] != ordinal
            or document["site_key"] != transition["site_key"]
            or document["previous_dispatch_event_id"]
            != (previous if previous is not None else _typed_null("DISPATCH_GENESIS"))
        ):
            _protocol("dispatch session event chain changed")
        previous = event.event_id
    if any(event.outcome != "SUCCESS" for event in session._events[:-1]):
        _protocol("dispatch session continued after its first failure")
    if session._events and session._events[-1].outcome != "SUCCESS":
        if not session._normal_closed:
            _protocol("failed dispatch session is not closed")


def _invoke_callback(
    session: H1LifecycleConstructionDispatcherV1,
    callback: Callable[[], Any],
) -> tuple[bool, Any, str | None]:
    if not callable(callback):
        _fail("the next lifecycle site requires one callback")
    if session._in_callback:
        session._violation_count += 1
        _protocol("lifecycle dispatcher callback reentry is forbidden")
    starting_violations = session._violation_count
    starting_local_state = canonical_json_bytes(
        {
            "events": [event.event_id for event in session._events],
            "deferred": {
                site: reservation.reservation_id
                for site, reservation in sorted(session._deferred.items())
            },
            "active_mount_sites": list(session._active_mount_sites),
            "ambiguous_native_sites": list(session._ambiguous_native_sites),
            "post_admission_protocol_abort_sites": list(
                session._post_admission_protocol_abort_sites
            ),
            "normal_closed": session._normal_closed,
            "owner_sequence": session._owner_journal_sequence,
            "owner_head": session._owner_journal_head_id,
        }
    )
    session._in_callback = True
    try:
        try:
            result = callback()
        except BaseException as error:
            return False, None, type(error).__name__
        ending_local_state = canonical_json_bytes(
            {
                "events": [event.event_id for event in session._events],
                "deferred": {
                    site: reservation.reservation_id
                    for site, reservation in sorted(session._deferred.items())
                },
                "active_mount_sites": list(session._active_mount_sites),
                "ambiguous_native_sites": list(session._ambiguous_native_sites),
                "post_admission_protocol_abort_sites": list(
                    session._post_admission_protocol_abort_sites
                ),
                "normal_closed": session._normal_closed,
                "owner_sequence": session._owner_journal_sequence,
                "owner_head": session._owner_journal_head_id,
            }
        )
        if (
            session._violation_count != starting_violations
            or not hmac.compare_digest(starting_local_state, ending_local_state)
        ):
            return False, None, "H1LifecycleDispatchReentryViolation"
        return True, result, None
    finally:
        session._in_callback = False


def _callback_failure_outcome(row: Mapping[str, Any]) -> str:
    allowed = set(_failure_outcomes(row))
    preferred = (
        "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
        if row["operation"] in {"MEMORY_BIND", "MOUNT_OPEN", "LAUNCH_CHILD"}
        else "CLEANUP_FAILED"
        if row["operation"] == "MOUNT_CLOSE"
        else "PROTOCOL_FAILED"
        if row["operation"] in {"DESCENDANT_REAP", "OUTPUT_CLOSE"}
        else "CALLBACK_FAILED_AFTER_ADMISSION"
    )
    if preferred not in allowed:
        _protocol("anchored transition lacks its typed callback-failure edge")
    return preferred


def _validated_magnitude(value: Any) -> tuple[bool, int | None, str | None]:
    if type(value) is not int or value < 0:
        return False, None, "InvalidNonnegativeMagnitudeResult"
    return True, value, None


def _append_event(
    session: H1LifecycleConstructionDispatcherV1,
    event: H1LifecycleDispatchEventV1,
) -> H1LifecycleDispatchEventV1:
    session._events = (*session._events, event)
    session._owner_journal_sequence = event.document[
        "owner_journal_sequence_after_event"
    ]
    session._owner_journal_head_id = event.document[
        "owner_journal_head_id_after_event"
    ]
    if event.outcome != "SUCCESS" or len(session._events) == 62:
        session._normal_closed = True
    return event


def _settle(
    session: H1LifecycleConstructionDispatcherV1,
    reservation: owner_v3.H1SharedReservationV3,
    *,
    basis: owner_v3.H1SharedValueBasisV3,
    native_value: int | None,
    evidence_source_id: str,
) -> tuple[owner_v3.H1SharedSettlementResultV3, bool]:
    try:
        result = _OWNER_ENTRYPOINTS["settle"](
            session.owner,
            reservation,
            value_basis=basis,
            native_observed_value=native_value,
            evidence_source_id=evidence_source_id,
        )
    except owner_v3.H1SharedCapOwnerV3ObservedOverrun as error:
        return error.result, True
    return result, False


def dispatch_next_h1_lifecycle_site_v1(
    session: H1LifecycleConstructionDispatcherV1,
    *,
    callback: Callable[[], Any] | None = None,
) -> H1LifecycleDispatchEventV1:
    """Execute only the next frozen site and append one construction event.

    Reservation uppers and operation IDs come from the frozen dispatch profile;
    callers cannot select a site, path, reducer, upper, or operation identity at
    execution time.
    """

    if type(session) is not H1LifecycleConstructionDispatcherV1:
        _fail("dispatch requires one exact construction session")
    if session._in_callback:
        session._violation_count += 1
        _protocol("lifecycle dispatcher cannot recurse from a callback")
    _validate_session(session)
    if session._normal_closed:
        _protocol("normal lifecycle dispatch is already closed")
    _verify_owner_entrypoints()
    index = len(session._events)
    row = session.bundle.program.transitions[index]
    handler = session.bundle.registry.handlers[index]
    mode = H1LifecycleHandlerModeV1(handler["handler_mode"])
    callback_required = handler["callback_required"]
    if callback_required is True and not callable(callback):
        _fail("the next lifecycle site requires one callback before admission")
    if callback_required is False and callback is not None:
        _fail("the next lifecycle site forbids a callback before admission")
    operation_id = _operation_id(session.profile.profile_id, row["ordinal"], row["site_key"])
    evidence_id = _evidence_source_id(
        session.profile.profile_id, row["ordinal"], row["site_key"]
    )
    operands = session.profile.site_operands
    upper = operands.get(row["site_key"])
    path = _resource_path(row)
    refs = _empty_owner_refs()

    if mode is H1LifecycleHandlerModeV1.NO_CHARGE_CONTROL:
        if row["operation"] == "MOUNT_CLOSE":
            expected_open = _pair_site(row)
            if not session._active_mount_sites or session._active_mount_sites[-1] != expected_open:
                _protocol("mount-close order differs from the frozen reverse stack")
        if row["operation"] == "OUTPUT_CLOSE" and (
            session._deferred or session._active_mount_sites
        ):
            _protocol("output close reached with unresolved lifecycle resources")
        ok, _result, error_type = _invoke_callback(session, callback)  # type: ignore[arg-type]
        outcome = "SUCCESS" if ok else _callback_failure_outcome(row)
        event = _issue_event(
            session,
            row,
            handler,
            outcome=outcome,
            operation_id=operation_id,
            reservation_upper=None,
            native_observed_value=None,
            value_basis=None,
            callback_invocation_count=1,
            callback_exception_type=error_type,
            owner_refs=refs,
            expected_owner_sequence_delta=0,
        )
        if outcome == "SUCCESS" and row["operation"] == "MOUNT_CLOSE":
            session._active_mount_sites.pop()
        return _append_event(session, event)

    if mode is H1LifecycleHandlerModeV1.DEFERRED_COMPLETION:
        origin = _DEFERRED_COMPLETIONS[row["site_key"]]
        reservation = session._deferred.get(origin)
        if reservation is None:
            _protocol("deferred completion lost its origin reservation")
        upper = operands[origin]
        with _OWNER_ENTRYPOINTS["hold"](session.owner, reservation):
            ok, result, error_type = _invoke_callback(session, callback)  # type: ignore[arg-type]
        if not ok:
            settlement, _overrun = _settle(
                session,
                reservation,
                basis=owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER,
                native_value=None,
                evidence_source_id=evidence_id,
            )
            refs = _settlement_refs(settlement)
            outcome = _callback_failure_outcome(row)
            value_basis = owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER.value
            native = None
        else:
            valid_native, native, invalid_type = _validated_magnitude(result)
            if not valid_native:
                settlement, _overrun = _settle(
                    session,
                    reservation,
                    basis=owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER,
                    native_value=None,
                    evidence_source_id=evidence_id,
                )
                refs = _settlement_refs(settlement)
                outcome = _callback_failure_outcome(row)
                value_basis = (
                    owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER.value
                )
                error_type = invalid_type
            else:
                assert native is not None
                basis = (
                    owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN
                    if native > upper
                    else owner_v3.H1SharedValueBasisV3.EXACT_NATIVE
                )
                settlement, overrun = _settle(
                    session,
                    reservation,
                    basis=basis,
                    native_value=native,
                    evidence_source_id=evidence_id,
                )
                refs = _settlement_refs(settlement)
                outcome = "OBSERVED_UPPER_BOUND_VIOLATION" if overrun else "SUCCESS"
                value_basis = basis.value
                error_type = None
        del session._deferred[origin]
        event = _issue_event(
            session,
            row,
            handler,
            outcome=outcome,
            operation_id=operation_id,
            reservation_upper=upper,
            native_observed_value=native,
            value_basis=value_basis,
            callback_invocation_count=1,
            callback_exception_type=error_type,
            owner_refs=refs,
            expected_owner_sequence_delta=6,
        )
        return _append_event(session, event)

    if upper is None or path is None:
        _protocol("reservation handler lost its frozen path or operand")
    try:
        reservation = _OWNER_ENTRYPOINTS["reserve"](
            session.owner,
            operation_id=operation_id,
            site_key=row["site_key"],
            path=path,
            reservation_upper=upper,
        )
    except owner_v3.H1SharedCapOwnerV3Rejected as error:
        if error.result is None:
            _protocol("Owner-V3 cap rejection lost its durable pair")
        refs = _rejection_refs(
            error.result,
            _OWNER_ENTRYPOINTS["index"](session.owner),
        )
        event = _issue_event(
            session,
            row,
            handler,
            outcome="CAP_REJECTED_BEFORE_SIDE_EFFECT",
            operation_id=operation_id,
            reservation_upper=upper,
            native_observed_value=None,
            value_basis=None,
            callback_invocation_count=0,
            callback_exception_type=None,
            owner_refs=refs,
            expected_owner_sequence_delta=4,
        )
        return _append_event(session, event)

    if mode is H1LifecycleHandlerModeV1.DEFERRED_ORIGIN:
        refs["reservation_id"] = reservation.reservation_id
        session._deferred[row["site_key"]] = reservation
        event = _issue_event(
            session,
            row,
            handler,
            outcome="SUCCESS",
            operation_id=operation_id,
            reservation_upper=upper,
            native_observed_value=None,
            value_basis=None,
            callback_invocation_count=0,
            callback_exception_type=None,
            owner_refs=refs,
            expected_owner_sequence_delta=1,
        )
        return _append_event(session, event)

    with _OWNER_ENTRYPOINTS["hold"](session.owner, reservation):
        ok, result, error_type = _invoke_callback(session, callback)  # type: ignore[arg-type]
    if not ok:
        settlement, _overrun = _settle(
            session,
            reservation,
            basis=owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER,
            native_value=None,
            evidence_source_id=evidence_id,
        )
        refs = _settlement_refs(settlement)
        failure_outcome = _callback_failure_outcome(row)
        if failure_outcome == "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION":
            session._ambiguous_native_sites.append(row["site_key"])
        event = _issue_event(
            session,
            row,
            handler,
            outcome=failure_outcome,
            operation_id=operation_id,
            reservation_upper=upper,
            native_observed_value=None,
            value_basis=owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER.value,
            callback_invocation_count=1,
            callback_exception_type=error_type,
            owner_refs=refs,
            expected_owner_sequence_delta=7,
        )
        return _append_event(session, event)
    if mode is H1LifecycleHandlerModeV1.IMMEDIATE_UNIT:
        native = 1
        basis = owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT
    else:
        valid_native, native, invalid_type = _validated_magnitude(result)
        if not valid_native:
            settlement, _overrun = _settle(
                session,
                reservation,
                basis=owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER,
                native_value=None,
                evidence_source_id=evidence_id,
            )
            refs = _settlement_refs(settlement)
            failure_outcome = _callback_failure_outcome(row)
            if failure_outcome == "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION":
                session._ambiguous_native_sites.append(row["site_key"])
            event = _issue_event(
                session,
                row,
                handler,
                outcome=failure_outcome,
                operation_id=operation_id,
                reservation_upper=upper,
                native_observed_value=None,
                value_basis=(
                    owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER.value
                ),
                callback_invocation_count=1,
                callback_exception_type=invalid_type,
                owner_refs=refs,
                expected_owner_sequence_delta=7,
            )
            return _append_event(session, event)
        assert native is not None
        basis = (
            owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN
            if native > upper
            else owner_v3.H1SharedValueBasisV3.EXACT_NATIVE
        )
    settlement, overrun = _settle(
        session,
        reservation,
        basis=basis,
        native_value=native,
        evidence_source_id=evidence_id,
    )
    refs = _settlement_refs(settlement)
    outcome = "OBSERVED_UPPER_BOUND_VIOLATION" if overrun else "SUCCESS"
    if overrun and outcome not in _failure_outcomes(row):
        outcome = ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
        session._post_admission_protocol_abort_sites.append(row["site_key"])
    if (
        outcome in {"SUCCESS", ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION}
        and row["operation"] == "MOUNT_OPEN"
    ):
        session._active_mount_sites.append(row["site_key"])
    event = _issue_event(
        session,
        row,
        handler,
        outcome=outcome,
        operation_id=operation_id,
        reservation_upper=upper,
        native_observed_value=native,
        value_basis=basis.value,
        callback_invocation_count=1,
        callback_exception_type=None,
        owner_refs=refs,
        expected_owner_sequence_delta=7,
    )
    return _append_event(session, event)


def snapshot_h1_lifecycle_dispatch_trace_v1(
    session: H1LifecycleConstructionDispatcherV1,
) -> H1LifecycleDispatchTraceV1:
    _validate_session(session)
    events = [event.document for event in session._events]
    first_failure = next(
        (event for event in session._events if event.outcome != "SUCCESS"), None
    )
    next_site = (
        session.bundle.program.transitions[len(events)]["site_key"]
        if first_failure is None and len(events) < 62
        else None
    )
    _verify_owner_entrypoints()
    owner_replay = _OWNER_ENTRYPOINTS["index"](session.owner)
    payload = {
        "schema": "acfqp.k7_h1_lifecycle_dispatch_trace.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_lifecycle_dispatch_profile_id": session.profile.profile_id,
        "h1_anchored_lifecycle_program_id": session.bundle.program.anchored_program_id,
        "h1_anchored_lifecycle_handler_registry_id": session.bundle.registry.registry_id,
        "h1_shared_cap_profile_core_v3_id": session.profile.owner_profile_id,
        "h1_shared_cap_owner_v3_runtime_id": session.profile.owner_runtime_id,
        "consumed_event_count": len(events),
        "consumed_events": events,
        "first_failure_event_id": (
            first_failure.event_id
            if first_failure is not None
            else _typed_null("NO_FIRST_FAILURE_EVENT")
        ),
        "full_declared_success_reached": len(events) == 62 and first_failure is None,
        "next_site_key": (
            next_site if next_site is not None else _typed_null("NO_NEXT_NORMAL_SITE")
        ),
        "deferred_reservation_ids": {
            site: reservation.reservation_id
            for site, reservation in sorted(session._deferred.items())
        },
        "active_mount_open_sites": list(session._active_mount_sites),
        "ambiguous_native_sites": list(session._ambiguous_native_sites),
        "post_admission_protocol_abort_sites": list(
            session._post_admission_protocol_abort_sites
        ),
        "owner_journal_sequence_at_snapshot": owner_replay["journal_sequence"],
        "owner_journal_head_id_at_snapshot": owner_replay["journal_head_id"],
        "owner_charged_values_at_snapshot": owner_replay["charged_values"],
        "owner_outstanding_values_at_snapshot": owner_replay["outstanding_values"],
        "owner_record_ids_at_snapshot": owner_replay["record_ids_by_role"],
        "owner_gate_join_status_at_snapshot": owner_replay[
            "gate_owner_join_status"
        ],
        "owner_rejection_commit_id_at_snapshot": owner_replay[
            "rejection_commit_id"
        ],
        "owner_rejection_ack_id_at_snapshot": owner_replay["rejection_ack_id"],
        "owner_new_work_allowed_at_snapshot": owner_replay["new_work_allowed"],
        "declared_prefix_replay_complete": True,
        "declared_first_failure_replay_complete": (
            first_failure is not None
            and first_failure.document["declared_first_failure"] is True
        ),
        "first_failure_is_provisional_prefix_only": first_failure is not None,
        "normal_dispatch_closed": session._normal_closed,
        "event_trace_durable_exactly_once": False,
        "source_authority_present": False,
        "loaded_execution_bytes_verified": False,
        "toctou_exclusion_present": False,
        "production_live_hooks_complete": False,
        "cleanup_continuation_complete": False,
        "output_leaf_join_bound": False,
        "current_access_atomic_bridge_present": False,
        "joint_output_read_fixed_point_present": False,
        "native_evidence_authority_present": False,
        "formal_v7_route_authority_present": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
        "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
    }
    document = {
        **payload,
        "h1_lifecycle_dispatch_trace_id": content_id(DISPATCH_TRACE_DOMAIN, payload),
    }
    return H1LifecycleDispatchTraceV1(_TRACE_ISSUER, canonical_json_bytes(document))


def _verify_h1_lifecycle_dispatch_trace_against_owner_index_v1(
    data: bytes,
    *,
    bundle: H1AnchoredLifecycleDispatchBundleV1,
    profile: H1LifecycleDispatchProfileV1,
    owner: owner_v3.H1SharedCapOwnerV3Handle,
    owner_index: Mapping[str, Any],
) -> H1LifecycleDispatchTraceV1:
    """Replay one construction trace against one already-verified Owner view."""

    if (
        type(data) is not bytes
        or type(bundle) is not H1AnchoredLifecycleDispatchBundleV1
        or type(profile) is not H1LifecycleDispatchProfileV1
        or type(owner) is not owner_v3.H1SharedCapOwnerV3Handle
        or type(owner_index) is not dict
    ):
        _fail(
            "trace verification requires exact bytes, bundle, profile, owner, "
            "and Owner view"
        )
    try:
        document = loads_canonical_json(data)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AnchoredLifecycleDispatchV1Error(
            "dispatch trace is not canonical JSON"
        ) from error
    if type(document) is not dict or frozenset(document) != _TRACE_DOCUMENT_FIELDS:
        _fail("dispatch trace document is not one object")
    payload = dict(document)
    claimed = _cid(
        payload.pop("h1_lifecycle_dispatch_trace_id", None),
        "dispatch trace",
    )
    if content_id(DISPATCH_TRACE_DOMAIN, payload) != claimed:
        _fail("dispatch trace content ID is invalid")
    if (
        document.get("h1_lifecycle_dispatch_profile_id") != profile.profile_id
        or document.get("h1_anchored_lifecycle_program_id")
        != bundle.program.anchored_program_id
        or document.get("h1_anchored_lifecycle_handler_registry_id")
        != bundle.registry.registry_id
        or document.get("h1_shared_cap_profile_core_v3_id")
        != profile.owner_profile_id
        or document.get("h1_shared_cap_owner_v3_runtime_id")
        != profile.owner_runtime_id
        or profile.owner_profile_id != owner.profile.profile_id
        or profile.owner_runtime_id != owner.runtime_id
    ):
        _fail("dispatch trace crossed its program, registry, profile, or runtime")
    records_by_role = owner_index["records_by_role"]
    record_ids_by_role = owner_index["record_ids_by_role"]
    id_fields = {
        "reservation": "h1_shared_cap_owner_v3_reservation_id",
        "rejection_admission": "h1_shared_cap_owner_v3_reservation_id",
        "native_cell": "h1_shared_cap_owner_v3_native_cell_id",
        "native_evidence": "h1_shared_cap_owner_v3_native_evidence_id",
        "settlement": "h1_shared_cap_owner_v3_settlement_id",
        "receipt": "h1_shared_cap_owner_v3_receipt_id",
        "event": "h1_shared_cap_owner_v3_event_id",
        "snapshot": "h1_shared_cap_owner_v3_snapshot_id",
    }
    owner_maps = {
        role: {row[id_fields[role]]: row for row in records_by_role[role]}
        for role in id_fields
    }
    referenced_owner_ids = {role: set() for role in id_fields}
    events = document.get("consumed_events")
    if type(events) is not list or document.get("consumed_event_count") != len(events):
        _fail("dispatch trace event count is malformed")
    if len(events) > 62:
        _fail("dispatch trace contains more than 62 events")
    transitions = bundle.program.transitions
    handlers = bundle.registry.handlers
    previous: str | None = None
    failure_id: str | None = None
    operation_ids: set[str] = set()
    deferred: dict[str, str] = {}
    active_mounts: list[str] = []
    ambiguous_sites: list[str] = []
    protocol_abort_sites: list[str] = []
    previous_owner_sequence = 0
    previous_owner_head: Any = _typed_null("JOURNAL_GENESIS")
    for index, event in enumerate(events):
        if type(event) is not dict or frozenset(event) != _EVENT_DOCUMENT_FIELDS:
            _fail("dispatch trace contains a non-object event")
        event_payload = dict(event)
        event_id = _cid(
            event_payload.pop("h1_lifecycle_dispatch_event_id", None),
            "dispatch event",
        )
        if content_id(DISPATCH_EVENT_DOMAIN, event_payload) != event_id:
            _fail("dispatch trace contains an invalid event ID")
        row = transitions[index]
        handler = handlers[index]
        expected_operation_id = _operation_id(profile.profile_id, index + 1, row["site_key"])
        expected_owner_operation_id = _owner_reservation_operation_id(
            profile.profile_id, row
        )
        context_matches = all(
            event.get(key) == value
            for key, value in {
                "schema": "acfqp.k7_h1_lifecycle_dispatch_event.v1",
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "h1_lifecycle_dispatch_profile_id": profile.profile_id,
                "h1_anchored_lifecycle_program_id": bundle.program.anchored_program_id,
                "h1_anchored_lifecycle_handler_registry_id": bundle.registry.registry_id,
                "h1_shared_cap_profile_core_v3_id": profile.owner_profile_id,
                "h1_shared_cap_owner_v3_runtime_id": profile.owner_runtime_id,
                "logical_occurrence_id": profile.logical_occurrence_id,
                "route_attempt_id": profile.route_attempt_id,
                "decision_point_id": profile.decision_point_id,
                "transaction_id": profile.transaction_id,
            }.items()
        )
        if (
            not context_matches
            or event.get("ordinal") != index + 1
            or event.get("site_key") != row["site_key"]
            or event.get("phase") != row["phase"]
            or event.get("operation") != row["operation"]
            or event.get("from_state") != row["from_state"]
            or event.get("success_state") != row["success_state"]
            or event.get("handler_mode") != handler["handler_mode"]
            or event.get("resource_path") != handler["resource_path"]
            or event.get("reducer") != handler["reducer"]
            or event.get("deterministic_dispatch_operation_id")
            != expected_operation_id
            or event.get("owner_reservation_operation_id")
            != (
                expected_owner_operation_id
                if expected_owner_operation_id is not None
                else _typed_null("NO_OWNER_RESERVATION_OPERATION")
            )
            or event.get("previous_dispatch_event_id")
            != (previous if previous is not None else _typed_null("DISPATCH_GENESIS"))
        ):
            _fail("dispatch trace skipped, reordered, or rebound one site")
        if expected_operation_id in operation_ids:
            _fail("dispatch trace reused one deterministic operation ID")
        operation_ids.add(expected_operation_id)
        outcome = event.get("outcome")
        supplemental_abort = (
            outcome == ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
            and row["operation"] == "MOUNT_OPEN"
            and "OBSERVED_UPPER_BOUND_VIOLATION" not in _failure_outcomes(row)
        )
        if (
            outcome != "SUCCESS"
            and outcome not in _failure_outcomes(row)
            and not supplemental_abort
        ):
            _fail("dispatch trace used an outcome absent from the anchored edge set")
        if failure_id is not None:
            _fail("dispatch trace continued after its first failure")
        if outcome != "SUCCESS":
            failure_id = event_id
        callback_count = event.get("callback_invocation_count")
        if outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT":
            if callback_count != 0:
                _fail("cap-rejected dispatch event claims a callback")
        elif row["operation"] in {"MEMORY_BIND", "OUTPUT_RESERVE"}:
            if callback_count != 0:
                _fail("deferred-origin admission event claims a native callback")
        elif callback_count != 1:
            _fail("dispatched lifecycle site must invoke exactly one callback")
        refs = event.get("owner_record_refs")
        if type(refs) is not dict or frozenset(refs) != frozenset(_OWNER_REF_KEYS):
            _fail("dispatch event Owner-V3 reference fields are not exact")
        mode = H1LifecycleHandlerModeV1(handler["handler_mode"])
        upper = (
            profile.site_operands[_DEFERRED_COMPLETIONS[row["site_key"]]]
            if row["site_key"] in _DEFERRED_COMPLETIONS
            else profile.site_operands.get(row["site_key"])
        )
        expected_present: set[str]
        if outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT":
            expected_present = {
                "rejection_admission_id",
                "receipt_id",
                "owner_event_id",
                "owner_snapshot_id",
                "rejection_commit_id",
                "rejection_ack_id",
            }
            expected_delta = 4
        elif mode is H1LifecycleHandlerModeV1.DEFERRED_ORIGIN:
            expected_present = {"reservation_id"}
            expected_delta = 1
        elif mode is H1LifecycleHandlerModeV1.NO_CHARGE_CONTROL:
            expected_present = set()
            expected_delta = 0
        else:
            expected_present = {
                "reservation_id",
                "native_cell_id",
                "native_evidence_id",
                "settlement_id",
                "receipt_id",
                "owner_event_id",
                "owner_snapshot_id",
            }
            expected_delta = (
                6
                if mode is H1LifecycleHandlerModeV1.DEFERRED_COMPLETION
                else 7
            )
        actual_present = {key for key, value in refs.items() if not _is_typed_null(value)}
        if actual_present != expected_present:
            _fail("dispatch event Owner-V3 reference roles are inconsistent")
        for key in actual_present:
            _cid(refs[key], f"dispatch Owner-V3 {key}")
        if event.get("owner_journal_sequence_before_event") != previous_owner_sequence:
            _fail("dispatch event Owner-V3 sequence prefix changed")
        if event.get("owner_journal_head_id_before_event") != previous_owner_head:
            _fail("dispatch event Owner-V3 head prefix changed")
        after_sequence = event.get("owner_journal_sequence_after_event")
        if after_sequence != previous_owner_sequence + expected_delta:
            _fail("dispatch event Owner-V3 sequence delta changed")

        resource_event = mode is not H1LifecycleHandlerModeV1.NO_CHARGE_CONTROL
        expected_upper: Any = upper if resource_event else _typed_null(
            "NO_RESERVATION_AT_THIS_SITE"
        )
        if event.get("reservation_upper") != expected_upper:
            _fail("dispatch event changed its frozen reservation operand")
        native_value = event.get("native_observed_value")
        value_basis = event.get("value_basis")
        callback_exception = event.get("callback_exception_type")
        if outcome == "SUCCESS":
            if mode is H1LifecycleHandlerModeV1.IMMEDIATE_UNIT:
                if (
                    native_value != 1
                    or value_basis
                    != owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT.value
                ):
                    _fail("unit dispatch success changed its exact value semantics")
            elif mode in {
                H1LifecycleHandlerModeV1.IMMEDIATE_MAGNITUDE,
                H1LifecycleHandlerModeV1.DEFERRED_COMPLETION,
            }:
                if (
                    type(native_value) is not int
                    or native_value < 0
                    or native_value > upper
                    or value_basis != owner_v3.H1SharedValueBasisV3.EXACT_NATIVE.value
                ):
                    _fail("magnitude dispatch success changed its exact semantics")
            elif not _is_typed_null(native_value) or not _is_typed_null(value_basis):
                _fail("nonsettling dispatch success claims a native value")
            if not _is_typed_null(callback_exception):
                _fail("successful dispatch event claims a callback exception")
        elif outcome in {
            "OBSERVED_UPPER_BOUND_VIOLATION",
            ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION,
        }:
            if (
                type(native_value) is not int
                or type(upper) is not int
                or native_value <= upper
                or value_basis != owner_v3.H1SharedValueBasisV3.OBSERVED_OVERRUN.value
                or not _is_typed_null(callback_exception)
            ):
                _fail("dispatch overrun changed or clipped its observed value")
        elif outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT":
            if (
                not _is_typed_null(native_value)
                or not _is_typed_null(value_basis)
                or not _is_typed_null(callback_exception)
            ):
                _fail("cap-rejected event claims native execution")
        elif mode is H1LifecycleHandlerModeV1.NO_CHARGE_CONTROL:
            if (
                not _is_typed_null(native_value)
                or not _is_typed_null(value_basis)
                or type(callback_exception) is not str
            ):
                _fail("failed control event changed its no-charge semantics")
        elif (
            not _is_typed_null(native_value)
            or value_basis
            != owner_v3.H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER.value
            or type(callback_exception) is not str
        ):
            _fail("failed admitted callback is not conservatively settled")

        if (
            event.get("declared_first_failure")
            is not (outcome != "SUCCESS" and not supplemental_abort)
            or event.get("anchored_transition_semantics_present")
            is not (not supplemental_abort)
            or event.get("supplemental_protocol_abort") is not supplemental_abort
            or event.get("first_failure_is_provisional_prefix_only")
            is not (outcome != "SUCCESS")
            or event.get("normal_forward_dispatch_allowed_after_event")
            is not (outcome == "SUCCESS" and index + 1 < 62)
            or event.get("construction_callback_value_only") is not True
            or event.get("native_evidence_authority_present") is not False
            or event.get("event_durable_exactly_once") is not False
            or event.get("attempt_closure_issued") is not False
            or event.get("terminal_classification_issued") is not False
            or event.get("certificate_issued") is not False
            or event.get("infeasibility_certified") is not False
        ):
            _fail("dispatch event crossed its construction claim boundary")

        if mode is H1LifecycleHandlerModeV1.DEFERRED_ORIGIN and outcome == "SUCCESS":
            deferred[row["site_key"]] = refs["reservation_id"]
        elif mode is H1LifecycleHandlerModeV1.DEFERRED_COMPLETION:
            origin = _DEFERRED_COMPLETIONS[row["site_key"]]
            if deferred.get(origin) != refs["reservation_id"]:
                _fail("deferred completion changed its origin reservation")
            deferred.pop(origin)
        if row["operation"] == "MOUNT_OPEN" and outcome in {
            "SUCCESS",
            ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION,
        }:
            active_mounts.append(row["site_key"])
        elif row["operation"] == "MOUNT_CLOSE" and outcome == "SUCCESS":
            expected_open = _pair_site(row)
            if not active_mounts or active_mounts[-1] != expected_open:
                _fail("dispatch trace changed reverse mount-close order")
            active_mounts.pop()
        if outcome == "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION":
            ambiguous_sites.append(row["site_key"])
        if supplemental_abort:
            protocol_abort_sites.append(row["site_key"])

        role_for_ref = {
            "reservation_id": "reservation",
            "rejection_admission_id": "rejection_admission",
            "native_cell_id": "native_cell",
            "native_evidence_id": "native_evidence",
            "settlement_id": "settlement",
            "receipt_id": "receipt",
            "owner_event_id": "event",
            "owner_snapshot_id": "snapshot",
        }
        for ref_key, role in role_for_ref.items():
            if ref_key in expected_present:
                if refs[ref_key] not in owner_maps[role]:
                    _fail("dispatch event references an absent Owner-V3 record")
                referenced_owner_ids[role].add(refs[ref_key])
        if "reservation_id" in expected_present:
            reservation = owner_maps["reservation"][refs["reservation_id"]]
            expected_reservation_site = (
                _DEFERRED_COMPLETIONS[row["site_key"]]
                if row["site_key"] in _DEFERRED_COMPLETIONS
                else row["site_key"]
            )
            if (
                reservation["operation_id"] != expected_owner_operation_id
                or reservation["site_key"] != expected_reservation_site
                or reservation["path"] != _resource_path(row)
                or reservation["reservation_upper"] != upper
            ):
                _fail("dispatch event crossed its exact Owner-V3 reservation")
        if "rejection_admission_id" in expected_present:
            admission = owner_maps["rejection_admission"][
                refs["rejection_admission_id"]
            ]
            if (
                admission["record_kind"] != "REJECTION_ADMISSION_DURABLE"
                or admission["admission_outcome"]
                != "REJECTED_BEFORE_SIDE_EFFECT"
                or admission["operation_id"] != expected_owner_operation_id
                or admission["site_key"] != row["site_key"]
                or admission["path"] != _resource_path(row)
                or admission["reservation_upper"] != upper
            ):
                _fail("dispatch cap rejection crossed its Owner-V3 admission")
        if "settlement_id" in expected_present:
            cell = owner_maps["native_cell"][refs["native_cell_id"]]
            evidence = owner_maps["native_evidence"][refs["native_evidence_id"]]
            settlement = owner_maps["settlement"][refs["settlement_id"]]
            if (
                cell["h1_shared_cap_owner_v3_reservation_id"] != refs["reservation_id"]
                or cell["operation_id"] != expected_owner_operation_id
                or evidence["h1_shared_cap_owner_v3_reservation_id"]
                != refs["reservation_id"]
                or evidence["h1_shared_cap_owner_v3_native_cell_id"]
                != refs["native_cell_id"]
                or evidence["value_basis"] != value_basis
                or settlement["h1_shared_cap_owner_v3_reservation_id"]
                != refs["reservation_id"]
                or settlement["h1_shared_cap_owner_v3_native_evidence_id"]
                != refs["native_evidence_id"]
                or settlement["operation_id"] != expected_owner_operation_id
                or settlement["value_basis"] != value_basis
                or settlement["reservation_upper"] != upper
            ):
                _fail("dispatch event changed its Owner-V3 settlement chain")
            if type(native_value) is int and (
                evidence["native_observed_value"] != native_value
                or settlement["native_observed_value"] != native_value
            ):
                _fail("dispatch event native value differs from Owner-V3 evidence")
        if "receipt_id" in expected_present:
            receipt = owner_maps["receipt"][refs["receipt_id"]]
            owner_event = owner_maps["event"][refs["owner_event_id"]]
            snapshot = owner_maps["snapshot"][refs["owner_snapshot_id"]]
            expected_subject_kind = (
                "CAP_REJECTION"
                if outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
                else "SETTLEMENT"
            )
            expected_subject_id = (
                refs["rejection_commit_id"]
                if outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
                else refs["settlement_id"]
            )
            if (
                receipt["subject_kind"] != expected_subject_kind
                or receipt["subject_id"] != expected_subject_id
                or owner_event["subject_kind"] != expected_subject_kind
                or owner_event["subject_id"] != expected_subject_id
                or owner_event["h1_shared_cap_owner_v3_receipt_id"]
                != refs["receipt_id"]
                or snapshot["h1_shared_cap_owner_v3_receipt_id"]
                != refs["receipt_id"]
                or snapshot["h1_shared_cap_owner_v3_event_id"]
                != refs["owner_event_id"]
            ):
                _fail("dispatch event changed its Owner-V3 receipt/event/snapshot chain")
        expected_after_head = (
            previous_owner_head
            if expected_delta == 0
            else refs["reservation_id"]
            if expected_delta == 1
            else refs["owner_snapshot_id"]
        )
        if event.get("owner_journal_head_id_after_event") != expected_after_head:
            _fail("dispatch event Owner-V3 head transition changed")
        previous_owner_sequence = after_sequence
        previous_owner_head = expected_after_head
        previous = event_id
    encoded_failure = document.get("first_failure_event_id")
    if encoded_failure != (
        failure_id if failure_id is not None else _typed_null("NO_FIRST_FAILURE_EVENT")
    ):
        _fail("dispatch trace first-failure identity is inconsistent")
    full_success = len(events) == 62 and failure_id is None
    if document.get("full_declared_success_reached") is not full_success:
        _fail("dispatch trace full-success marker is inconsistent")
    expected_next = (
        transitions[len(events)]["site_key"]
        if failure_id is None and len(events) < 62
        else _typed_null("NO_NEXT_NORMAL_SITE")
    )
    if document.get("next_site_key") != expected_next:
        _fail("dispatch trace next-site marker is inconsistent")
    if document.get("deferred_reservation_ids") != deferred:
        _fail("dispatch trace deferred-reservation frontier is inconsistent")
    if document.get("active_mount_open_sites") != active_mounts:
        _fail("dispatch trace active-mount frontier is inconsistent")
    if document.get("ambiguous_native_sites") != ambiguous_sites:
        _fail("dispatch trace ambiguous-native frontier is inconsistent")
    if document.get("post_admission_protocol_abort_sites") != protocol_abort_sites:
        _fail("dispatch trace supplemental protocol-abort frontier is inconsistent")
    if (
        document.get("owner_journal_sequence_at_snapshot")
        != owner_index["journal_sequence"]
        or document.get("owner_journal_head_id_at_snapshot")
        != owner_index["journal_head_id"]
        or document.get("owner_charged_values_at_snapshot")
        != owner_index["charged_values"]
        or document.get("owner_outstanding_values_at_snapshot")
        != owner_index["outstanding_values"]
        or document.get("owner_record_ids_at_snapshot")
        != owner_index["record_ids_by_role"]
        or document.get("owner_gate_join_status_at_snapshot")
        != owner_index["gate_owner_join_status"]
        or document.get("owner_rejection_commit_id_at_snapshot")
        != owner_index["rejection_commit_id"]
        or document.get("owner_rejection_ack_id_at_snapshot")
        != owner_index["rejection_ack_id"]
        or document.get("owner_new_work_allowed_at_snapshot")
        is not owner_index["new_work_allowed"]
        or previous_owner_sequence != owner_index["journal_sequence"]
        or previous_owner_head != owner_index["journal_head_id"]
    ):
        _fail("dispatch trace Owner-V3 terminal snapshot is inconsistent")
    if failure_id is not None:
        failure_event = next(
            event
            for event in events
            if event["h1_lifecycle_dispatch_event_id"] == failure_id
        )
        failure_refs = failure_event["owner_record_refs"]
        if failure_event["outcome"] == "CAP_REJECTED_BEFORE_SIDE_EFFECT":
            if (
                failure_refs["rejection_commit_id"]
                != owner_index["rejection_commit_id"]
                or failure_refs["rejection_ack_id"]
                != owner_index["rejection_ack_id"]
            ):
                _fail("dispatch cap rejection differs from gate replay")
        elif (
            owner_index["gate_owner_join_status"] != "OPEN_NO_REJECTION"
            or not _is_typed_null(owner_index["rejection_commit_id"])
            or not _is_typed_null(owner_index["rejection_ack_id"])
            or owner_index["new_work_allowed"]
            is not (
                failure_event["outcome"]
                not in {
                    "OBSERVED_UPPER_BOUND_VIOLATION",
                    ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION,
                }
            )
        ):
            _fail("attempt gate changed outside the dispatch trace")
    elif (
        owner_index["gate_owner_join_status"] != "OPEN_NO_REJECTION"
        or not _is_typed_null(owner_index["rejection_commit_id"])
        or not _is_typed_null(owner_index["rejection_ack_id"])
        or owner_index["new_work_allowed"] is not True
    ):
        _fail("attempt gate changed outside the dispatch trace")
    for role in id_fields:
        if referenced_owner_ids[role] != set(record_ids_by_role[role]):
            _fail("dispatch trace does not exactly cover its Owner-V3 record set")
    expected_closed = failure_id is not None or full_success
    declared_first_failure_replayed = (
        failure_id is not None and failure_event["declared_first_failure"] is True
    )
    if (
        document.get("declared_prefix_replay_complete") is not True
        or document.get("declared_first_failure_replay_complete")
        is not declared_first_failure_replayed
        or document.get("first_failure_is_provisional_prefix_only")
        is not (failure_id is not None)
        or document.get("normal_dispatch_closed") is not expected_closed
    ):
        _fail("dispatch trace derived closure state is inconsistent")
    if (
        document.get("source_authority_present") is not False
        or document.get("loaded_execution_bytes_verified") is not False
        or document.get("toctou_exclusion_present") is not False
        or document.get("production_live_hooks_complete") is not False
        or document.get("native_evidence_authority_present") is not False
        or document.get("cleanup_continuation_complete") is not False
        or document.get("output_leaf_join_bound") is not False
        or document.get("formal_v7_route_authority_present") is not False
        or document.get("counter_records_issued") is not False
        or document.get("work_vector_issued") is not False
        or document.get("comparison_vector_issued") is not False
        or document.get("attempt_closure_issued") is not False
        or document.get("terminal_classification_issued") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("counter_completeness_gate_status")
        != COUNTER_COMPLETENESS_GATE_STATUS
        or document.get("workload_economics_gate_status")
        != WORKLOAD_ECONOMICS_GATE_STATUS
        or document.get("sample_efficiency_gate_status")
        != SAMPLE_EFFICIENCY_GATE_STATUS
    ):
        _fail("dispatch trace crossed a locked authority or Gate boundary")
    return H1LifecycleDispatchTraceV1(_TRACE_ISSUER, canonical_json_bytes(document))


def verify_h1_lifecycle_dispatch_trace_bytes_v1(
    data: bytes,
    *,
    bundle: H1AnchoredLifecycleDispatchBundleV1,
    profile: H1LifecycleDispatchProfileV1,
    owner: owner_v3.H1SharedCapOwnerV3Handle,
) -> H1LifecycleDispatchTraceV1:
    """Replay the trace against the exact current durable Owner-V3 journal."""

    if (
        type(data) is not bytes
        or type(bundle) is not H1AnchoredLifecycleDispatchBundleV1
        or type(profile) is not H1LifecycleDispatchProfileV1
        or type(owner) is not owner_v3.H1SharedCapOwnerV3Handle
    ):
        _fail("trace verification requires exact bytes, bundle, profile, and owner")
    _verify_owner_entrypoints()
    owner_index = _OWNER_ENTRYPOINTS["index"](owner)
    return _verify_h1_lifecycle_dispatch_trace_against_owner_index_v1(
        data,
        bundle=bundle,
        profile=profile,
        owner=owner,
        owner_index=owner_index,
    )


def verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
    data: bytes,
    *,
    bundle: H1AnchoredLifecycleDispatchBundleV1,
    profile: H1LifecycleDispatchProfileV1,
    owner: owner_v3.H1SharedCapOwnerV3Handle,
) -> H1LifecycleDispatchTraceV1:
    """Verify the trace at its cutoff and admit only an append-only Owner tail.

    Unlike the exact verifier, this entrypoint permits later durable Owner-V3
    records.  It still replays the complete current journal and reconstructs
    the exact prefix named by the trace's sequence/head snapshot.  The normal
    semantic verifier then uses only that prefix, so later cleanup records
    cannot satisfy, replace, or alter any dispatch obligation at the cutoff.
    """

    if (
        type(data) is not bytes
        or type(bundle) is not H1AnchoredLifecycleDispatchBundleV1
        or type(profile) is not H1LifecycleDispatchProfileV1
        or type(owner) is not owner_v3.H1SharedCapOwnerV3Handle
    ):
        _fail(
            "trace prefix verification requires exact bytes, bundle, profile, "
            "and owner"
        )
    try:
        preliminary = loads_canonical_json(data)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AnchoredLifecycleDispatchV1Error(
            "dispatch trace is not canonical JSON"
        ) from error
    if type(preliminary) is not dict:
        _fail("dispatch trace document is not one object")
    _verify_owner_entrypoints()
    _verify_owner_prefix_index_entrypoint()
    owner_index = _OWNER_PREFIX_INDEX_ENTRYPOINT(
        owner,
        journal_sequence=preliminary.get("owner_journal_sequence_at_snapshot"),
        journal_head_id=preliminary.get("owner_journal_head_id_at_snapshot"),
    )
    return _verify_h1_lifecycle_dispatch_trace_against_owner_index_v1(
        data,
        bundle=bundle,
        profile=profile,
        owner=owner,
        owner_index=owner_index,
    )


__all__ = (
    "ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION",
    "ANCHORED_PROGRAM_DOMAIN",
    "CLEANUP_CONTINUATION_COMPLETE",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "CURRENT_ACCESS_ATOMIC_BRIDGE_PRESENT",
    "ConstructionK7H1AnchoredLifecycleDispatchV1Error",
    "DISPATCH_EVENT_DOMAIN",
    "DISPATCH_PROFILE_DOMAIN",
    "DISPATCH_TRACE_DOMAIN",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1AnchoredLifecycleDispatchBundleV1",
    "H1AnchoredLifecycleHandlerRegistryV1",
    "H1AnchoredLifecycleProgramV1",
    "H1LifecycleConstructionDispatcherV1",
    "H1LifecycleDispatchEventV1",
    "H1LifecycleDispatchProfileV1",
    "H1LifecycleDispatchProtocolFailureV1",
    "H1LifecycleDispatchTraceV1",
    "H1LifecycleHandlerModeV1",
    "HANDLER_REGISTRY_DOMAIN",
    "JOINT_OUTPUT_READ_FIXED_POINT_PRESENT",
    "NATIVE_EVIDENCE_AUTHORITY_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OUTPUT_LEAF_JOIN_BOUND",
    "PREFIX_VERIFICATION_ATTESTATION_ISSUED",
    "PRODUCTION_EXECUTION_AUTHORIZED",
    "PRODUCTION_LIVE_HOOKS_COMPLETE",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SOURCE_AUTHORITY_PRESENT",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "bind_h1_lifecycle_dispatch_profile_v1",
    "dispatch_next_h1_lifecycle_site_v1",
    "freeze_h1_anchored_lifecycle_dispatch_bundle_v1",
    "snapshot_h1_lifecycle_dispatch_trace_v1",
    "start_h1_lifecycle_construction_dispatch_v1",
    "verify_h1_lifecycle_dispatch_trace_bytes_v1",
    "verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1",
)
