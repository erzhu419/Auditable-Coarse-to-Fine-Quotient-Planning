"""Attempt-wide raw process-launch supervision for the V0-075 K7 route.

The mutable session opens before successor-request replay, binds the replayed
request/route identity before execution, owns the context-local launch sink,
and closes to an immutable raw journal on both success and failure paths.  The
journal is attempt-wide process evidence only.  It deliberately issues no
CounterRecord, WorkVector, ComparisonVector, projection proof, terminal, or
certificate.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
import hashlib
import itertools
import os
from pathlib import Path
import sys
from threading import Lock, get_ident
import time
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_attempt_process_sink_v1 as sink_v1
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ATTEMPT_PROCESS_EXECUTION_V1_DOMAIN,
    V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN,
    V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN,
    V075_K7_ATTEMPT_PROCESS_SESSION_START_V1_DOMAIN,
    V075_K7_ATTEMPT_PROCESS_SUPERVISOR_PROFILE_V1_DOMAIN,
    V075_K7_ATTEMPT_PROCESS_VERIFICATION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.2"
PROFILE_KEY = "v075_k7_attempt_process_supervisor_v1"
COUNTER_PATH = "process.launches"
REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_ATTEMPT_PROCESS_SUPERVISOR_PROFILE_V1_DOMAIN",
    "V075_K7_ATTEMPT_PROCESS_SESSION_START_V1_DOMAIN",
    "V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN",
    "V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN",
    "V075_K7_ATTEMPT_PROCESS_EXECUTION_V1_DOMAIN",
    "V075_K7_ATTEMPT_PROCESS_VERIFICATION_V1_DOMAIN",
)
LOCAL_DOMAINS = frozenset(
    {
        V075_K7_ATTEMPT_PROCESS_SUPERVISOR_PROFILE_V1_DOMAIN,
        V075_K7_ATTEMPT_PROCESS_SESSION_START_V1_DOMAIN,
        V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN,
        V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN,
        V075_K7_ATTEMPT_PROCESS_EXECUTION_V1_DOMAIN,
        V075_K7_ATTEMPT_PROCESS_VERIFICATION_V1_DOMAIN,
    }
)
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("attempt-process supervisor domains are unregistered")

_PROFILE_ISSUER = object()
_EXECUTION_ISSUER = object()
_EVENT_ISSUER = object()
_JOURNAL_ISSUER = object()
_VERIFICATION_ISSUER = object()
_EXECUTOR_PIN_ISSUER = object()
_TEST_AUTHORITY_ISSUER = object()
_SESSION_ORDINALS = itertools.count(1)
_SESSION_ORDINAL_LOCK = Lock()
_EXECUTOR_CALLSITE_LOCK = Lock()


class V075K7AttemptProcessSupervisorV1Error(ValueError):
    """The attempt process window, identity, or raw journal is invalid."""


class AttemptProcessCloseKindV1(str, Enum):
    IDENTITY_BIND_FAILURE = "IDENTITY_BIND_FAILURE"
    PRELAUNCH_FAILURE = "PRELAUNCH_FAILURE"
    POSTLAUNCH_FAILURE = "POSTLAUNCH_FAILURE"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    SUCCESS = "SUCCESS"


class AttemptProcessSessionStateV1(str, Enum):
    STARTED_BEFORE_REQUEST_REPLAY = "STARTED_BEFORE_REQUEST_REPLAY"
    REQUEST_BOUND = "REQUEST_BOUND"
    LAUNCH_OBSERVED = "LAUNCH_OBSERVED"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class _PinnedExecutorCallsiteV1:
    _issuer: InitVar[object]
    function: Any
    code: Any
    globals_mapping: dict[str, Any]
    module_name: str
    function_name: str
    source_path: str
    source_sha256: str
    source_byte_count: int

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EXECUTOR_PIN_ISSUER
            or not callable(self.function)
            or self.code is not self.function.__code__
            or self.globals_mapping is not self.function.__globals__
            or self.module_name != "acfqp.v075_k7_attempt_process_executor_v1"
            or self.function_name != "execute_v075_k7_attempt_scoped_parent_v1"
            or self.function.__module__ != self.module_name
            or self.function.__name__ != self.function_name
            or type(self.source_path) is not str
            or not self.source_path
            or type(self.source_sha256) is not str
            or len(self.source_sha256) != 64
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
        ):
            _fail("attempt-process executor callsite pin is malformed")


@dataclass(frozen=True, slots=True)
class _AttemptProcessTestAuthorityV1:
    _issuer: InitVar[object]
    owner_process_id: int
    owner_thread_id: int

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _TEST_AUTHORITY_ISSUER
            or self.owner_process_id != os.getpid()
            or self.owner_thread_id != get_ident()
        ):
            _fail("attempt-process test authority is caller-minted or crossed")

    def _assert_current(self) -> None:
        if (
            os.getpid() != self.owner_process_id
            or get_ident() != self.owner_thread_id
        ):
            _fail("attempt-process test authority crossed process or thread")


_PINNED_EXECUTOR_CALLSITE: _PinnedExecutorCallsiteV1 | None = None


def _fail(message: str) -> NoReturn:
    raise V075K7AttemptProcessSupervisorV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("attempt-process supervisor used an undeclared content domain")
    return content_id(domain, dict(payload))


def _register_v075_k7_attempt_process_executor_callsite_v1(
    function: Any,
) -> None:
    """Pin the original executor function exactly once at module finalization."""

    global _PINNED_EXECUTOR_CALLSITE
    if (
        not callable(function)
        or getattr(function, "__module__", None)
        != "acfqp.v075_k7_attempt_process_executor_v1"
        or getattr(function, "__name__", None)
        != "execute_v075_k7_attempt_scoped_parent_v1"
    ):
        _fail("foreign function cannot register as the attempt executor")
    globals_mapping = function.__globals__
    if (
        globals_mapping.get("__name__") != function.__module__
        or globals_mapping.get("execute_v075_k7_attempt_scoped_parent_v1")
        is not function
    ):
        _fail("executor registration is not module-finalization exact")
    source_path_value = globals_mapping.get("__file__")
    if type(source_path_value) is not str or not source_path_value:
        _fail("attempt executor registration lacks a source path")
    source_path = Path(source_path_value).resolve()
    try:
        raw = source_path.read_bytes()
    except OSError as error:
        raise V075K7AttemptProcessSupervisorV1Error(
            "attempt executor source snapshot is unreadable"
        ) from error
    candidate = _PinnedExecutorCallsiteV1(
        _EXECUTOR_PIN_ISSUER,
        function,
        function.__code__,
        globals_mapping,
        function.__module__,
        function.__name__,
        str(source_path),
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )
    with _EXECUTOR_CALLSITE_LOCK:
        if _PINNED_EXECUTOR_CALLSITE is not None:
            _fail("attempt executor callsite was already pinned")
        _PINNED_EXECUTOR_CALLSITE = candidate


def _issue_v075_k7_attempt_process_test_authority_v1(
) -> _AttemptProcessTestAuthorityV1:
    """Issue an explicit private injection authority only inside pytest."""

    caller_name = sys._getframe(1).f_globals.get("__name__")  # noqa: SLF001
    if (
        "PYTEST_CURRENT_TEST" not in os.environ
        or type(caller_name) is not str
        or not (
            caller_name.startswith("test_")
            or ".test_" in caller_name
            or caller_name.startswith("tests.")
        )
    ):
        _fail("attempt-process test authority is unavailable outside pytest")
    return _AttemptProcessTestAuthorityV1(
        _TEST_AUTHORITY_ISSUER, os.getpid(), get_ident()
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7AttemptProcessSupervisorV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _enum(enum_type: type[Enum], value: Any, label: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise V075K7AttemptProcessSupervisorV1Error(
            f"unknown {label} {value!r}"
        ) from error


def _document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} snapshot is empty or mistyped")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7AttemptProcessSupervisorV1Error(
            f"{label} snapshot is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} snapshot must be one JSON object")
    return value


def _locks() -> dict[str, bool]:
    return {
        "attempt_wide_raw_process_evidence": False,
        "complete_attempt_wide_raw_process_evidence": False,
        "registered_prebind_through_parent_payload_raw_prefix": True,
        "semantic_source_evidence_verified": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "actual_projection_proof_issued": False,
        "formal_vector_authorized": False,
        "attempt_terminal_issued": False,
        "plan_certificate_issued": False,
        "infeasibility_certificate_issued": False,
        "official_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class K7AttemptProcessSupervisorProfileV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    counter_semantics: Mapping[str, Any] = field(repr=False, compare=False)
    _counter_semantics_bytes: bytes = field(init=False, repr=False)
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("attempt-process supervisor profile is caller-minted")
        registry = registry_v6.official_counter_registry_v6()
        registry.validate_official_catalogue()
        leaf = registry.by_path[COUNTER_PATH]
        semantics = leaf.to_dict()
        if (
            self.counter_registry_id != registry.registry_id
            or dict(self.counter_semantics) != semantics
            or semantics.get("semantics_id") != "process-launch-v1"
            or semantics.get("owner") != "process_supervisor"
            or semantics.get("unit") != "launches"
            or semantics.get("scope") != "attempt"
            or semantics.get("reducer") != "sum"
        ):
            _fail("attempt-process profile differs from V6 process ownership")
        snapshot = canonical_json_bytes(semantics)
        object.__setattr__(self, "_counter_semantics_bytes", snapshot)
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_ATTEMPT_PROCESS_SUPERVISOR_PROFILE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_attempt_process_supervisor_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "counter_semantics": _document(
                self._counter_semantics_bytes, "counter semantics"
            ),
            "target_counter_path": COUNTER_PATH,
            "runtime_source_module": (
                "acfqp.v075_k7_atomic_pidfd_runtime_v1"
            ),
            "runtime_source_symbol": (
                "run_v075_k7_atomic_pidfd_runtime_v1"
            ),
            "sink_source_module": (
                "acfqp.v075_k7_attempt_process_sink_v1"
            ),
            "sink_source_symbol": (
                "record_v075_k7_attempt_process_launch_v1"
            ),
            "fixed_runtime_code_object_required": True,
            "caller_supplied_count_accepted": False,
            "expected_launch_events_on_success": 1,
            "hard_raw_launch_event_cap": 16,
            **_locks(),
        }

    def _assert_current(self) -> None:
        registry = registry_v6.official_counter_registry_v6()
        if (
            self.counter_registry_id != registry.registry_id
            or canonical_json_bytes(self.counter_semantics)
            != self._counter_semantics_bytes
            or _hash(
                V075_K7_ATTEMPT_PROCESS_SUPERVISOR_PROFILE_V1_DOMAIN,
                self._payload(),
            )
            != self._profile_id
        ):
            _fail("attempt-process supervisor profile changed after freeze")

    @property
    def profile_id(self) -> str:
        self._assert_current()
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "supervisor_profile_id": self.profile_id}


@lru_cache(maxsize=1)
def official_v075_k7_attempt_process_supervisor_profile_v1(
) -> K7AttemptProcessSupervisorProfileV1:
    registry = registry_v6.official_counter_registry_v6()
    return K7AttemptProcessSupervisorProfileV1(
        _PROFILE_ISSUER,
        registry.registry_id,
        registry.by_path[COUNTER_PATH].to_dict(),
    )


@dataclass(frozen=True, slots=True)
class K7AttemptProcessExecutionV1:
    _issuer: InitVar[object]
    supervisor_profile_id: str
    session_key: str
    owner_process_id: int
    owner_thread_id: int
    start_monotonic_ns: int
    start_ordinal: int
    request_id: str
    route_identity_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    route_decision_context_id: str
    decision_point_id: str
    transaction_id: str
    transaction_index: int
    _execution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EXECUTION_ISSUER:
            _fail("attempt-process execution identity is caller-minted")
        for value, label in (
            (self.supervisor_profile_id, "supervisor profile"),
            (self.session_key, "session key"),
            (self.request_id, "successor request"),
            (self.route_identity_id, "route identity"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.route_decision_context_id, "route decision context"),
            (self.decision_point_id, "decision point"),
            (self.transaction_id, "transaction"),
        ):
            _cid(value, label)
        if (
            type(self.owner_process_id) is not int
            or self.owner_process_id <= 0
            or type(self.owner_thread_id) is not int
            or self.owner_thread_id <= 0
            or type(self.start_monotonic_ns) is not int
            or self.start_monotonic_ns <= 0
            or type(self.start_ordinal) is not int
            or self.start_ordinal <= 0
            or type(self.transaction_index) is not int
            or self.transaction_index <= 0
        ):
            _fail("attempt-process execution scalar is invalid")
        object.__setattr__(
            self,
            "_execution_id",
            _hash(V075_K7_ATTEMPT_PROCESS_EXECUTION_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_attempt_process_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "supervisor_profile_id": self.supervisor_profile_id,
            "session_key": self.session_key,
            "owner_process_id": self.owner_process_id,
            "owner_thread_id": self.owner_thread_id,
            "start_monotonic_ns": self.start_monotonic_ns,
            "start_ordinal": self.start_ordinal,
            "request_id": self.request_id,
            "route_identity_id": self.route_identity_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "transaction_index": self.transaction_index,
            "session_started_before_request_replay": True,
            "request_bound_before_launch": True,
        }

    @property
    def execution_id(self) -> str:
        current = _hash(
            V075_K7_ATTEMPT_PROCESS_EXECUTION_V1_DOMAIN, self._payload()
        )
        if current != self._execution_id:
            _fail("attempt-process execution identity changed after freeze")
        return self._execution_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "process_execution_id": self.execution_id}


@dataclass(frozen=True, slots=True)
class K7AttemptProcessLaunchEventV1:
    _issuer: InitVar[object]
    process_execution_id: str
    session_key: str
    sequence: int
    observed_monotonic_ns: int
    observer_process_id: int
    observer_thread_id: int
    runtime_source_module: str
    runtime_source_symbol: str
    runtime_source_path: str | None
    runtime_source_sha256: str | None
    runtime_source_byte_count: int | None
    runtime_code_object_pinned: bool
    runtime_globals_mapping_pinned: bool
    test_only_injection: bool
    _event_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EVENT_ISSUER:
            _fail("attempt-process launch event is caller-minted")
        _cid(self.process_execution_id, "process execution")
        _cid(self.session_key, "session key")
        if (
            type(self.sequence) is not int
            or not (1 <= self.sequence <= 16)
            or type(self.observed_monotonic_ns) is not int
            or self.observed_monotonic_ns <= 0
            or type(self.observer_process_id) is not int
            or self.observer_process_id <= 0
            or type(self.observer_thread_id) is not int
            or self.observer_thread_id <= 0
        ):
            _fail("attempt-process launch event scalar is invalid")
        if self.test_only_injection:
            provenance_valid = (
                self.runtime_source_module == "TEST_ONLY_PRIVATE_AUTHORITY"
                and self.runtime_source_symbol == "TEST_ONLY_EVENT_INJECTION"
                and self.runtime_source_path is None
                and self.runtime_source_sha256 is None
                and self.runtime_source_byte_count is None
                and self.runtime_code_object_pinned is False
                and self.runtime_globals_mapping_pinned is False
            )
        else:
            provenance_valid = (
                self.runtime_source_module
                == "acfqp.v075_k7_atomic_pidfd_runtime_v1"
                and self.runtime_source_symbol
                == "run_v075_k7_atomic_pidfd_runtime_v1"
                and type(self.runtime_source_path) is str
                and bool(self.runtime_source_path)
                and type(self.runtime_source_sha256) is str
                and len(self.runtime_source_sha256) == 64
                and type(self.runtime_source_byte_count) is int
                and self.runtime_source_byte_count > 0
                and self.runtime_code_object_pinned is True
                and self.runtime_globals_mapping_pinned is True
            )
        if type(self.test_only_injection) is not bool or not provenance_valid:
            _fail("attempt-process launch provenance is invalid")
        object.__setattr__(
            self,
            "_event_id",
            _hash(
                V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_attempt_process_launch_event.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "process_execution_id": self.process_execution_id,
            "session_key": self.session_key,
            "sequence": self.sequence,
            "observed_monotonic_ns": self.observed_monotonic_ns,
            "observer_process_id": self.observer_process_id,
            "observer_thread_id": self.observer_thread_id,
            "runtime_source_module": self.runtime_source_module,
            "runtime_source_symbol": self.runtime_source_symbol,
            "runtime_source_path": self.runtime_source_path,
            "runtime_source_sha256": self.runtime_source_sha256,
            "runtime_source_byte_count": self.runtime_source_byte_count,
            "runtime_code_object_pinned": self.runtime_code_object_pinned,
            "runtime_globals_mapping_pinned": (
                self.runtime_globals_mapping_pinned
            ),
            "test_only_injection": self.test_only_injection,
            "counter_path": COUNTER_PATH,
            "event_kind": "PROCESS_LAUNCH",
            "source_kind": "PROCESS_SUPERVISOR_LAUNCH",
            "observed_value": 1,
            "charged": True,
            "caller_supplied_value": False,
        }

    @property
    def event_id(self) -> str:
        current = _hash(
            V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN,
            self._payload(),
        )
        if current != self._event_id:
            _fail("attempt-process launch event changed after freeze")
        return self._event_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "launch_event_id": self.event_id}


@dataclass(frozen=True, slots=True)
class K7AttemptProcessRawJournalV1:
    _issuer: InitVar[object]
    supervisor_profile_id: str
    session_key: str
    owner_process_id: int
    owner_thread_id: int
    start_monotonic_ns: int
    start_ordinal: int
    close_kind: AttemptProcessCloseKindV1
    close_monotonic_ns: int
    protocol_failure_reason: str | None
    launch_edge_entered_count: int
    launch_edge_lower_bound: int
    launch_event_materialization_in_progress: bool
    _start_authority_bytes: bytes = field(repr=False, compare=False)
    _execution_bytes: bytes | None = field(repr=False, compare=False)
    _event_bytes: tuple[bytes, ...] = field(repr=False, compare=False)
    _raw_journal_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _JOURNAL_ISSUER:
            _fail("attempt-process raw journal is caller-minted")
        _cid(self.supervisor_profile_id, "supervisor profile")
        _cid(self.session_key, "session key")
        close_kind = _enum(
            AttemptProcessCloseKindV1, self.close_kind, "process close kind"
        )
        object.__setattr__(self, "close_kind", close_kind)
        if (
            type(self.owner_process_id) is not int
            or self.owner_process_id <= 0
            or type(self.owner_thread_id) is not int
            or self.owner_thread_id <= 0
            or type(self.start_monotonic_ns) is not int
            or self.start_monotonic_ns <= 0
            or type(self.start_ordinal) is not int
            or self.start_ordinal <= 0
            or type(self.close_monotonic_ns) is not int
            or self.close_monotonic_ns < self.start_monotonic_ns
            or type(self._event_bytes) is not tuple
        ):
            _fail("attempt-process journal scalar or event container is invalid")
        if (
            type(self.launch_edge_entered_count) is not int
            or self.launch_edge_entered_count < 0
            or type(self.launch_edge_lower_bound) is not int
            or self.launch_edge_lower_bound != self.launch_edge_entered_count
            or type(self.launch_event_materialization_in_progress) is not bool
        ):
            _fail("attempt-process launch-edge write-ahead state is invalid")
        execution = (
            None
            if self._execution_bytes is None
            else _document(self._execution_bytes, "process execution")
        )
        start_authority = _document(
            self._start_authority_bytes, "session start authority"
        )
        if start_authority.get("authority_kind") not in {
            "PINNED_PRODUCTION_EXECUTOR",
            "TEST_ONLY_PRIVATE_AUTHORITY",
        }:
            _fail("attempt-process journal start authority is invalid")
        events = tuple(
            _document(raw, "process launch event") for raw in self._event_bytes
        )
        if len(events) > 16:
            _fail("attempt-process journal exceeds its raw launch-event cap")
        if self.launch_edge_entered_count < len(events):
            _fail("materialized launches exceed the launch-edge lower bound")
        if close_kind is AttemptProcessCloseKindV1.IDENTITY_BIND_FAILURE:
            valid = (
                execution is None
                and not events
                and self.launch_edge_entered_count == 0
                and not self.launch_event_materialization_in_progress
            )
        elif close_kind is AttemptProcessCloseKindV1.PRELAUNCH_FAILURE:
            valid = (
                execution is not None
                and not events
                and self.launch_edge_entered_count == 0
                and not self.launch_event_materialization_in_progress
            )
        elif close_kind is AttemptProcessCloseKindV1.PROTOCOL_FAILURE:
            valid = type(self.protocol_failure_reason) is str and bool(
                self.protocol_failure_reason
            )
        else:
            valid = (
                execution is not None
                and len(events) == 1
                and self.launch_edge_entered_count == 1
                and not self.launch_event_materialization_in_progress
            )
        if not valid:
            _fail("attempt-process journal launch prefix disagrees with close kind")
        if (
            close_kind is not AttemptProcessCloseKindV1.PROTOCOL_FAILURE
            and self.protocol_failure_reason is not None
        ):
            _fail("nonprotocol process journal carries a protocol-failure reason")
        if (
            self.launch_event_materialization_in_progress
            and (
                close_kind is not AttemptProcessCloseKindV1.PROTOCOL_FAILURE
                or self.launch_edge_entered_count <= len(events)
            )
        ):
            _fail("incomplete launch materialization lacks its protocol prefix")
        if execution is not None:
            if (
                execution.get("session_key") != self.session_key
                or execution.get("supervisor_profile_id")
                != self.supervisor_profile_id
            ):
                _fail("attempt-process journal crosses an execution identity")
            execution_id = execution.get("process_execution_id")
            _cid(execution_id, "embedded process execution")
        else:
            execution_id = None
        for index, event in enumerate(events, start=1):
            if (
                event.get("sequence") != index
                or event.get("session_key") != self.session_key
                or event.get("process_execution_id") != execution_id
                or event.get("observed_value") != 1
                or event.get("caller_supplied_value") is not False
            ):
                _fail("attempt-process journal contains a crossed launch event")
        object.__setattr__(
            self,
            "_raw_journal_id",
            _hash(
                V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN,
                self._payload(),
            ),
        )

    @property
    def execution_document(self) -> dict[str, Any] | None:
        if self._execution_bytes is None:
            return None
        return _document(self._execution_bytes, "process execution")

    @property
    def launch_event_documents(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            _document(raw, "process launch event") for raw in self._event_bytes
        )

    @property
    def observed_launch_count(self) -> int:
        return len(self._event_bytes)

    def _payload(self) -> dict[str, Any]:
        execution = self.execution_document
        events = self.launch_event_documents
        return {
            "schema": "acfqp.v075_k7_attempt_process_raw_journal.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "supervisor_profile_id": self.supervisor_profile_id,
            "session_key": self.session_key,
            "owner_process_id": self.owner_process_id,
            "owner_thread_id": self.owner_thread_id,
            "start_monotonic_ns": self.start_monotonic_ns,
            "start_ordinal": self.start_ordinal,
            "close_kind": self.close_kind.value,
            "close_monotonic_ns": self.close_monotonic_ns,
            "protocol_failure_reason": self.protocol_failure_reason,
            "session_start_authority": _document(
                self._start_authority_bytes, "session start authority"
            ),
            "launch_edge_entered_count": self.launch_edge_entered_count,
            "launch_edge_lower_bound": self.launch_edge_lower_bound,
            "materialized_launch_event_count": len(events),
            "launch_event_materialization_in_progress": (
                self.launch_event_materialization_in_progress
            ),
            "process_execution": execution,
            "process_execution_id": (
                None if execution is None else execution["process_execution_id"]
            ),
            "launch_events": list(events),
            "launch_event_ids": [row["launch_event_id"] for row in events],
            "observed_launch_count": len(events),
            "test_only_event_injection_present": any(
                row["test_only_injection"] for row in events
            ),
            "raw_launch_event_list_empty": not events,
            "attempt_window_started_before_request_replay": True,
            "attempt_window_closed_on_failure_prefix": (
                self.close_kind is not AttemptProcessCloseKindV1.SUCCESS
            ),
            "immutable_raw_event_journal": True,
            **_locks(),
        }

    @property
    def raw_journal_id(self) -> str:
        current = _hash(
            V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN, self._payload()
        )
        if current != self._raw_journal_id:
            _fail("attempt-process raw journal changed after freeze")
        return self._raw_journal_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "raw_journal_id": self.raw_journal_id}


@dataclass(frozen=True, slots=True)
class K7AttemptProcessVerificationV1:
    _issuer: InitVar[object]
    supervisor_profile_id: str
    raw_journal_id: str
    close_kind: AttemptProcessCloseKindV1
    observed_launch_count: int
    launch_edge_lower_bound: int
    launch_event_materialization_in_progress: bool

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _VERIFICATION_ISSUER:
            _fail("attempt-process verification is caller-minted")
        _cid(self.supervisor_profile_id, "supervisor profile")
        _cid(self.raw_journal_id, "raw process journal")
        object.__setattr__(
            self,
            "close_kind",
            _enum(
                AttemptProcessCloseKindV1,
                self.close_kind,
                "process close kind",
            ),
        )
        if type(self.observed_launch_count) is not int or not (
            0 <= self.observed_launch_count <= 16
        ):
            _fail("attempt-process verification count is invalid")
        if (
            type(self.launch_edge_lower_bound) is not int
            or self.launch_edge_lower_bound < self.observed_launch_count
            or type(self.launch_event_materialization_in_progress) is not bool
        ):
            _fail("attempt-process verification lower bound is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_attempt_process_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "supervisor_profile_id": self.supervisor_profile_id,
            "raw_journal_id": self.raw_journal_id,
            "close_kind": self.close_kind.value,
            "observed_launch_count": self.observed_launch_count,
            "launch_edge_lower_bound": self.launch_edge_lower_bound,
            "launch_event_materialization_in_progress": (
                self.launch_event_materialization_in_progress
            ),
            "canonical_snapshot_replayed": True,
            "attempt_window_prefix_consistent": True,
            "formal_counter_record_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return _hash(
            V075_K7_ATTEMPT_PROCESS_VERIFICATION_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


class V075K7AttemptProcessSupervisorSessionV1:
    """Mutable, process/thread-bound owner of one attempt launch journal."""

    def __init__(
        self,
        profile: K7AttemptProcessSupervisorProfileV1,
        *,
        _issuer: object,
        _executor_callsite: _PinnedExecutorCallsiteV1 | None = None,
        _test_authority: _AttemptProcessTestAuthorityV1 | None = None,
    ) -> None:
        if _issuer is not _SESSION_ISSUER:
            _fail("attempt-process supervisor session is caller-minted")
        if type(profile) is not K7AttemptProcessSupervisorProfileV1:
            _fail("attempt-process session requires the exact profile")
        if (_executor_callsite is None) == (_test_authority is None):
            _fail("attempt-process session requires one start authority")
        if _test_authority is not None:
            if type(_test_authority) is not _AttemptProcessTestAuthorityV1:
                _fail("attempt-process test start authority is mistyped")
            _test_authority._assert_current()
            start_authority = {
                "authority_kind": "TEST_ONLY_PRIVATE_AUTHORITY",
                "executor_source_module": "TEST_ONLY_PRIVATE_AUTHORITY",
                "executor_source_symbol": "TEST_ONLY_SESSION_START",
                "executor_source_path": None,
                "executor_source_sha256": None,
                "executor_source_byte_count": None,
                "executor_code_object_pinned": False,
                "executor_globals_mapping_pinned": False,
                "production_session": False,
            }
        else:
            assert _executor_callsite is not None
            if type(_executor_callsite) is not _PinnedExecutorCallsiteV1:
                _fail("attempt-process executor start pin is mistyped")
            start_authority = {
                "authority_kind": "PINNED_PRODUCTION_EXECUTOR",
                "executor_source_module": _executor_callsite.module_name,
                "executor_source_symbol": _executor_callsite.function_name,
                "executor_source_path": _executor_callsite.source_path,
                "executor_source_sha256": _executor_callsite.source_sha256,
                "executor_source_byte_count": (
                    _executor_callsite.source_byte_count
                ),
                "executor_code_object_pinned": True,
                "executor_globals_mapping_pinned": True,
                "production_session": True,
            }
        profile._assert_current()
        with _SESSION_ORDINAL_LOCK:
            ordinal = next(_SESSION_ORDINALS)
        self._profile = profile
        self._owner_process_id = os.getpid()
        self._owner_thread_id = get_ident()
        self._start_monotonic_ns = time.monotonic_ns()
        self._start_ordinal = ordinal
        self._start_authority_bytes = canonical_json_bytes(start_authority)
        self._test_authority = _test_authority
        self._session_key = _hash(
            V075_K7_ATTEMPT_PROCESS_SESSION_START_V1_DOMAIN,
            {
                "schema": "acfqp.v075_k7_attempt_process_session_start.v1",
                "schema_version": SCHEMA_VERSION,
                "supervisor_profile_id": profile.profile_id,
                "owner_process_id": self._owner_process_id,
                "owner_thread_id": self._owner_thread_id,
                "start_monotonic_ns": self._start_monotonic_ns,
                "start_ordinal": ordinal,
                "start_authority": start_authority,
            },
        )
        self._state = (
            AttemptProcessSessionStateV1.STARTED_BEFORE_REQUEST_REPLAY
        )
        self._request: (
            successor_v1.V075K7ParentOwnedSuccessorRequestV1 | None
        ) = None
        self._request_bytes: bytes | None = None
        self._execution: K7AttemptProcessExecutionV1 | None = None
        self._execution_bytes: bytes | None = None
        self._event_bytes: list[bytes] = []
        self._launch_edge_entered_count = 0
        self._launch_event_materialization_in_progress = False
        self._protocol_failure_reason: str | None = None
        self._journal: K7AttemptProcessRawJournalV1 | None = None
        self._sink_binding = (
            sink_v1._register_v075_k7_attempt_process_receiver_v1(self)
        )

    def __reduce__(self) -> NoReturn:
        raise TypeError("attempt-process supervisor session is unpickleable")

    def _assert_owner(self) -> None:
        if os.getpid() != self._owner_process_id:
            _fail("attempt-process session crossed a process boundary")
        if get_ident() != self._owner_thread_id:
            _fail("attempt-process session crossed a thread boundary")

    def _assert_open(self) -> None:
        self._assert_owner()
        if self._state is AttemptProcessSessionStateV1.CLOSED:
            _fail("attempt-process session is already closed")

    @property
    def state(self) -> AttemptProcessSessionStateV1:
        self._assert_owner()
        return self._state

    @property
    def session_key(self) -> str:
        self._assert_owner()
        return self._session_key

    @property
    def execution(self) -> K7AttemptProcessExecutionV1 | None:
        self._assert_owner()
        return self._execution

    @property
    def launch_edge_entered_count(self) -> int:
        self._assert_owner()
        return self._launch_edge_entered_count

    @property
    def journal(self) -> K7AttemptProcessRawJournalV1:
        self._assert_owner()
        if self._journal is None:
            _fail("attempt-process journal is unavailable before close")
        return self._journal

    def bind_request(
        self,
        request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    ) -> K7AttemptProcessExecutionV1:
        self._assert_open()
        if (
            self._state
            is not AttemptProcessSessionStateV1.STARTED_BEFORE_REQUEST_REPLAY
            or self._request is not None
        ):
            _fail("attempt-process request may be bound exactly once")
        if type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1:
            _fail("attempt-process request binding requires exact authority")
        try:
            request._assert_current()  # noqa: SLF001
            request_bytes = request.canonical_bytes
            route = request.route_identity
            route._assert_current()  # noqa: SLF001
            execution = K7AttemptProcessExecutionV1(
                _EXECUTION_ISSUER,
                self._profile.profile_id,
                self._session_key,
                self._owner_process_id,
                self._owner_thread_id,
                self._start_monotonic_ns,
                self._start_ordinal,
                request.request_id,
                route.route_identity_id,
                route.logical_occurrence.logical_occurrence_id,
                route.route_attempt.route_attempt_id,
                route.route_context.route_decision_context_id,
                route.decision_point.decision_point_id,
                route.transaction.transaction_id,
                route.transaction.transaction_index,
            )
        except Exception as error:
            if isinstance(error, V075K7AttemptProcessSupervisorV1Error):
                raise
            raise V075K7AttemptProcessSupervisorV1Error(
                "attempt-process request failed complete identity replay"
            ) from error
        self._request = request
        self._request_bytes = request_bytes
        self._execution = execution
        self._execution_bytes = execution.canonical_bytes
        self._state = AttemptProcessSessionStateV1.REQUEST_BOUND
        return execution

    def activate_process_sink(self) -> AbstractContextManager[None]:
        self._assert_open()
        return sink_v1.activate_v075_k7_attempt_process_sink_v1(
            self._sink_binding
        )

    def _materialize_launch_edge_v1(
        self,
        *,
        provenance: Mapping[str, Any] | None,
        runtime_callsite: object | None,
        test_only_injection: bool,
    ) -> None:
        # Write-ahead facts come first.  Once the fixed launch edge reaches the
        # receiver, no later timestamp, hash, allocation, or serialization
        # failure may turn it back into a prelaunch zero.
        self._launch_edge_entered_count += 1
        self._launch_event_materialization_in_progress = True
        try:
            self._assert_open()
            if self._execution is None or self._state not in {
                AttemptProcessSessionStateV1.REQUEST_BOUND,
                AttemptProcessSessionStateV1.LAUNCH_OBSERVED,
            }:
                self._protocol_failure_reason = (
                    "LAUNCH_EDGE_ENTERED_OUTSIDE_BOUND_EXECUTION"
                )
                _fail(
                    "attempt-process launch arrived outside a bound execution"
                )
            if runtime_callsite is not None:
                provenance = runtime_callsite.provenance()
            if provenance is None:
                self._protocol_failure_reason = (
                    "LAUNCH_EVENT_PROVENANCE_UNAVAILABLE"
                )
                _fail("attempt-process launch provenance is unavailable")
            if len(self._event_bytes) >= 16:
                self._protocol_failure_reason = (
                    "RAW_LAUNCH_EVENT_CAP_EXCEEDED"
                )
                _fail("attempt-process raw launch-event cap was exceeded")
            event = K7AttemptProcessLaunchEventV1(
                _EVENT_ISSUER,
                self._execution.execution_id,  # type: ignore[union-attr]
                self._session_key,
                len(self._event_bytes) + 1,
                time.monotonic_ns(),
                os.getpid(),
                get_ident(),
                provenance["runtime_source_module"],
                provenance["runtime_source_symbol"],
                provenance["runtime_source_path"],
                provenance["runtime_source_sha256"],
                provenance["runtime_source_byte_count"],
                provenance["runtime_code_object_pinned"],
                provenance["runtime_globals_mapping_pinned"],
                test_only_injection,
            )
            event_bytes = event.canonical_bytes
            self._event_bytes.append(event_bytes)
            self._launch_event_materialization_in_progress = False
            self._state = AttemptProcessSessionStateV1.LAUNCH_OBSERVED
        except BaseException as error:
            if self._protocol_failure_reason is None:
                self._protocol_failure_reason = (
                    "LAUNCH_EVENT_MATERIALIZATION_FAILED_"
                    + type(error).__name__.upper()
                )
            raise
        if len(self._event_bytes) != 1:
            self._protocol_failure_reason = (
                "UNEXPECTED_ADDITIONAL_PROCESS_LAUNCH"
            )
            _fail("unexpected additional process launch was journaled")

    def _record_process_launch_from_sink_v1(
        self,
        issuer: object,
        runtime_callsite: object,
    ) -> None:
        if (
            issuer is not sink_v1._EVENT_ISSUER  # noqa: SLF001
            or type(runtime_callsite)
            is not sink_v1._PinnedRuntimeCallsiteV1  # noqa: SLF001
            or runtime_callsite
            is not sink_v1._PINNED_RUNTIME_CALLSITE  # noqa: SLF001
        ):
            _fail("attempt-process launch event bypassed the fixed sink")
        self._materialize_launch_edge_v1(
            provenance=None,
            runtime_callsite=runtime_callsite,
            test_only_injection=False,
        )

    def _record_process_launch_for_testing_v1(
        self,
        authority: _AttemptProcessTestAuthorityV1,
    ) -> None:
        self._assert_open()
        if (
            type(authority) is not _AttemptProcessTestAuthorityV1
            or authority is not self._test_authority
        ):
            _fail("test launch injection lacks its session authority")
        authority._assert_current()
        if self._execution is None or self._state not in {
            AttemptProcessSessionStateV1.REQUEST_BOUND,
            AttemptProcessSessionStateV1.LAUNCH_OBSERVED,
        }:
            _fail("test launch injection is outside a bound execution")
        self._materialize_launch_edge_v1(
            provenance={
                "runtime_source_module": "TEST_ONLY_PRIVATE_AUTHORITY",
                "runtime_source_symbol": "TEST_ONLY_EVENT_INJECTION",
                "runtime_source_path": None,
                "runtime_source_sha256": None,
                "runtime_source_byte_count": None,
                "runtime_code_object_pinned": False,
                "runtime_globals_mapping_pinned": False,
            },
            runtime_callsite=None,
            test_only_injection=True,
        )

    def close(
        self, close_kind: AttemptProcessCloseKindV1
    ) -> K7AttemptProcessRawJournalV1:
        self._assert_open()
        close_kind = _enum(
            AttemptProcessCloseKindV1, close_kind, "process close kind"
        )
        execution = self._execution
        count = len(self._event_bytes)
        if self._request is not None:
            try:
                self._request._assert_current()  # noqa: SLF001
                current_request_bytes = self._request.canonical_bytes
            except Exception as error:
                del error
                current_request_bytes = None
            if current_request_bytes != self._request_bytes:
                self._protocol_failure_reason = (
                    "BOUND_REQUEST_SNAPSHOT_CHANGED_BEFORE_CLOSE"
                )
        if self._protocol_failure_reason is not None:
            close_kind = AttemptProcessCloseKindV1.PROTOCOL_FAILURE
        elif close_kind is AttemptProcessCloseKindV1.IDENTITY_BIND_FAILURE:
            valid = (
                execution is None
                and count == 0
                and self._launch_edge_entered_count == 0
            )
        elif close_kind is AttemptProcessCloseKindV1.PRELAUNCH_FAILURE:
            valid = (
                execution is not None
                and count == 0
                and self._launch_edge_entered_count == 0
            )
        elif close_kind is AttemptProcessCloseKindV1.PROTOCOL_FAILURE:
            self._protocol_failure_reason = "CALLER_REPORTED_PROTOCOL_FAILURE"
            valid = True
        else:
            valid = (
                execution is not None
                and count == 1
                and self._launch_edge_entered_count == 1
                and not self._launch_event_materialization_in_progress
            )
        if self._protocol_failure_reason is None and not valid:
            self._protocol_failure_reason = "CLOSE_KIND_PREFIX_MISMATCH"
            close_kind = AttemptProcessCloseKindV1.PROTOCOL_FAILURE
        try:
            journal = K7AttemptProcessRawJournalV1(
                _JOURNAL_ISSUER,
                self._profile.profile_id,
                self._session_key,
                self._owner_process_id,
                self._owner_thread_id,
                self._start_monotonic_ns,
                self._start_ordinal,
                close_kind,
                time.monotonic_ns(),
                self._protocol_failure_reason,
                self._launch_edge_entered_count,
                self._launch_edge_entered_count,
                self._launch_event_materialization_in_progress,
                self._start_authority_bytes,
                self._execution_bytes,
                tuple(self._event_bytes),
            )
            self._journal = journal
            return journal
        except BaseException as error:
            if self._protocol_failure_reason is None:
                self._protocol_failure_reason = (
                    "RAW_JOURNAL_MATERIALIZATION_FAILED_"
                    + type(error).__name__.upper()
                )
            raise
        finally:
            sink_v1._unregister_v075_k7_attempt_process_receiver_v1(  # noqa: SLF001
                self._sink_binding
            )
            self._state = AttemptProcessSessionStateV1.CLOSED

    def emergency_prefix_bytes_v1(self) -> bytes:
        """Freeze a nonformal prefix after ordinary journal close failed."""

        self._assert_owner()
        if self._journal is not None:
            _fail("emergency prefix is forbidden after a journal was issued")
        locks = _locks()
        locks["registered_prebind_through_parent_payload_raw_prefix"] = False
        return canonical_json_bytes(
            {
                "schema": (
                    "acfqp.v075_k7_attempt_process_emergency_prefix.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "supervisor_profile_id": self._profile._profile_id,  # noqa: SLF001
                "session_key": self._session_key,
                "session_state": self._state.value,
                "start_authority": _document(
                    self._start_authority_bytes, "session start authority"
                ),
                "process_execution": (
                    None
                    if self._execution_bytes is None
                    else _document(
                        self._execution_bytes, "process execution"
                    )
                ),
                "launch_events": [
                    _document(raw, "process launch event")
                    for raw in self._event_bytes
                ],
                "launch_edge_entered_count": (
                    self._launch_edge_entered_count
                ),
                "launch_edge_lower_bound": self._launch_edge_entered_count,
                "materialized_launch_event_count": len(self._event_bytes),
                "launch_event_materialization_in_progress": (
                    self._launch_event_materialization_in_progress
                ),
                "protocol_failure_reason": self._protocol_failure_reason,
                "raw_journal_issued": False,
                "closure_incomplete": True,
                "emergency_nonformal_prefix": True,
                **locks,
            }
        )

    def emergency_prefix_snapshot_v1(self) -> tuple[Any, ...]:
        """Retain raw fields even if canonical emergency encoding fails."""

        self._assert_owner()
        return (
            "acfqp.v075_k7_attempt_process_emergency_prefix_snapshot.v1",
            self._profile._profile_id,  # noqa: SLF001
            self._session_key,
            self._state.value,
            self._start_authority_bytes,
            self._execution_bytes,
            tuple(self._event_bytes),
            self._launch_edge_entered_count,
            self._launch_event_materialization_in_progress,
            self._protocol_failure_reason,
            self._journal is not None,
            False,
        )


_SESSION_ISSUER = object()


def start_v075_k7_attempt_process_supervisor_session_v1(
    *,
    profile: K7AttemptProcessSupervisorProfileV1 | None = None,
) -> V075K7AttemptProcessSupervisorSessionV1:
    """Start a window only from the fixed attempt-scoped parent executor."""

    caller = sys._getframe(1)  # noqa: SLF001 - fixed caller authority
    with _EXECUTOR_CALLSITE_LOCK:
        executor_callsite = _PINNED_EXECUTOR_CALLSITE
    if (
        executor_callsite is None
        or caller.f_code is not executor_callsite.code
        or caller.f_globals is not executor_callsite.globals_mapping
        or caller.f_globals.get("__name__") != executor_callsite.module_name
    ):
        _fail("attempt-process session start came from a foreign call site")

    selected = (
        official_v075_k7_attempt_process_supervisor_profile_v1()
        if profile is None
        else profile
    )
    return V075K7AttemptProcessSupervisorSessionV1(
        selected,
        _issuer=_SESSION_ISSUER,
        _executor_callsite=executor_callsite,
    )


def _start_v075_k7_attempt_process_supervisor_session_for_testing_v1(
    authority: _AttemptProcessTestAuthorityV1,
    *,
    profile: K7AttemptProcessSupervisorProfileV1 | None = None,
) -> V075K7AttemptProcessSupervisorSessionV1:
    if type(authority) is not _AttemptProcessTestAuthorityV1:
        _fail("test session start requires its private authority")
    authority._assert_current()
    selected = (
        official_v075_k7_attempt_process_supervisor_profile_v1()
        if profile is None
        else profile
    )
    return V075K7AttemptProcessSupervisorSessionV1(
        selected,
        _issuer=_SESSION_ISSUER,
        _test_authority=authority,
    )


def _inject_v075_k7_attempt_process_launch_for_testing_v1(
    *,
    session: V075K7AttemptProcessSupervisorSessionV1,
    authority: _AttemptProcessTestAuthorityV1,
) -> None:
    if type(session) is not V075K7AttemptProcessSupervisorSessionV1:
        _fail("test launch injection requires the exact session")
    session._record_process_launch_for_testing_v1(authority)  # noqa: SLF001


def verify_v075_k7_attempt_process_raw_journal_bytes_v1(
    *,
    raw: bytes,
    expected: K7AttemptProcessRawJournalV1,
) -> K7AttemptProcessVerificationV1:
    """Replay the exact immutable raw snapshot without upgrading its claim."""

    if type(expected) is not K7AttemptProcessRawJournalV1:
        _fail("raw process replay requires the exact expected journal")
    document = _document(raw, "raw process journal")
    if canonical_json_bytes(document) != expected.canonical_bytes:
        _fail("raw process journal bytes differ from the frozen snapshot")
    profile = official_v075_k7_attempt_process_supervisor_profile_v1()
    if document.get("supervisor_profile_id") != profile.profile_id:
        _fail("raw process journal uses a stale supervisor profile")
    if document.get("raw_journal_id") != expected.raw_journal_id:
        _fail("raw process journal content ID changed")
    return K7AttemptProcessVerificationV1(
        _VERIFICATION_ISSUER,
        profile.profile_id,
        expected.raw_journal_id,
        expected.close_kind,
        expected.observed_launch_count,
        expected.launch_edge_lower_bound,
        expected.launch_event_materialization_in_progress,
    )


__all__ = (
    "AttemptProcessCloseKindV1",
    "AttemptProcessSessionStateV1",
    "COUNTER_PATH",
    "K7AttemptProcessExecutionV1",
    "K7AttemptProcessLaunchEventV1",
    "K7AttemptProcessRawJournalV1",
    "K7AttemptProcessSupervisorProfileV1",
    "K7AttemptProcessVerificationV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7AttemptProcessSupervisorSessionV1",
    "V075K7AttemptProcessSupervisorV1Error",
    "official_v075_k7_attempt_process_supervisor_profile_v1",
    "start_v075_k7_attempt_process_supervisor_session_v1",
    "verify_v075_k7_attempt_process_raw_journal_bytes_v1",
)
