"""Owner-bound accounting for the production-native fallback construction slice.

This V3 runtime records the seven positive ``DIRECT_FALLBACK`` primitive
families from :mod:`acfqp.phase3e_fallback_owned_v2`.  It deliberately stops
before CounterRecord/WorkVector/ComparisonVector materialization and before
FQ9 terminal classification.  The runtime is inactive by default and an
active session is bound to an independently replayed V3 source manifest.

The frame and live-code checks are a Python construction control.  They are
not a process-isolation or native-code adversary boundary.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import InitVar, dataclass
from enum import Enum
import hashlib
import importlib
import sys
import threading
from types import MappingProxyType
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "3.0.0"
PROFILE_KEY = "construction_accounting_route_segment_v3"
CONSTRUCTION_ONLY = True
PRODUCTION_OWNER_SOURCE_INTEGRATED = True
PRODUCTION_CLOSURE_CLAIMED = False
PYTHON_API_SPOOF_RESISTANCE_ONLY = True

_START_DOMAIN = "acfqp:construction-accounting-route-segment-start:v3"
_EVENT_DOMAIN = "acfqp:construction-accounting-route-segment-event:v3"
_TERMINAL_DOMAIN = "acfqp:construction-accounting-route-segment-terminal:v3"
_TRANSCRIPT_DOMAIN = "acfqp:construction-accounting-route-segment-transcript:v3"
_FROZEN_GETFRAME_V3 = sys._getframe  # noqa: SLF001
_NODE_ISSUER = object()
OWNED_ROUTE_EVENT_ACK_V3 = object()
_SEARCH_BIND_ISSUER_V3 = object()
_SEARCH_FINISH_ISSUER_V3 = object()


class ConstructionAccountingRouteSegmentV3Error(RuntimeError):
    """The V3 manifest binding, operation stream, or lifecycle is invalid."""


class RouteSegmentTerminalKindV3(str, Enum):
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


def _fail(message: str) -> NoReturn:
    raise ConstructionAccountingRouteSegmentV3Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV3Error(
            f"{label} must be one full content ID"
        ) from error


def _resolve_owner(module_name: Any, symbol_qualname: Any) -> tuple[Any, Any]:
    if type(module_name) is not str or not module_name.startswith("acfqp."):
        _fail("operation owner module is invalid")
    if type(symbol_qualname) is not str or not symbol_qualname:
        _fail("operation owner symbol is invalid")
    try:
        module = importlib.import_module(module_name)
        value: Any = module
        for component in symbol_qualname.split("."):
            value = getattr(value, component)
        code = value.__code__
    except (AttributeError, ImportError, TypeError) as error:
        raise ConstructionAccountingRouteSegmentV3Error(
            "operation owner code is unavailable"
        ) from error
    return module.__dict__, code


def _require_node_issuance(issuer: object, key: str, node: Any) -> None:
    if issuer is not _NODE_ISSUER:
        _fail("owned route-segment node is session-issued only")
    try:
        generated_init = _FROZEN_GETFRAME_V3(2)
        session_caller = _FROZEN_GETFRAME_V3(3)
        expected_code = _FROZEN_NODE_CODES_V3[key]
    except (AttributeError, KeyError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV3Error(
            "owned route-segment issuance ancestry is unavailable"
        ) from error
    if (
        generated_init.f_code is not type(node).__init__.__code__
        or session_caller.f_globals is not _FROZEN_NODE_GLOBALS_V3
        or (
            session_caller.f_code not in expected_code
            if type(expected_code) is tuple
            else session_caller.f_code is not expected_code
        )
    ):
        _fail("owned route-segment node bypassed its exact session issuer")


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentStartV3:
    _issuer: InitVar[object]
    route_segment_id: str
    occurrence_id: str
    route_attempt_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_manifest_id: str
    recorder_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_node_issuance(_issuer, "START", self)
        for value, label in (
            (self.route_segment_id, "route segment"),
            (self.occurrence_id, "occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.boundary_manifest_id, "boundary manifest"),
        ):
            _cid(value, label)
        if type(self.recorder_id) is not str or not self.recorder_id:
            _fail("recorder ID must be nonempty")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_start.v3",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_id": self.route_segment_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "recorder_id": self.recorder_id,
            "stage_kind": registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value,
            "construction_only": True,
            "production_owner_source_integrated": True,
            "production_closure_claimed": False,
        }

    @property
    def start_id(self) -> str:
        return _content_id(_START_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_start_id": self.start_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteOperationEventV3:
    _issuer: InitVar[object]
    route_segment_start_id: str
    boundary_id: str
    dispatch_key: str
    path: str
    amount: int
    event_sequence: int
    predecessor_chain_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_node_issuance(_issuer, "EVENT", self)
        _cid(self.route_segment_start_id, "route segment start")
        _cid(self.boundary_id, "operation boundary")
        _cid(self.predecessor_chain_id, "predecessor chain")
        if not all(
            type(value) is str and value
            for value in (self.dispatch_key, self.path)
        ):
            _fail("operation dispatch/path is invalid")
        if type(self.amount) is not int or self.amount != 1:
            _fail("each owned event must represent one primitive")
        if type(self.event_sequence) is not int or self.event_sequence <= 0:
            _fail("event sequence must be positive")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_operation_event.v3",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_start_id": self.route_segment_start_id,
            "stage_kind": registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value,
            "boundary_id": self.boundary_id,
            "dispatch_key": self.dispatch_key,
            "path": self.path,
            "reducer": ReducerEnum.SUM.value,
            "amount": self.amount,
            "event_sequence": self.event_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "caller_reported_summary_allowed": False,
            "construction_only": True,
        }

    @property
    def event_id(self) -> str:
        return _content_id(_EVENT_DOMAIN, self._payload())

    @property
    def chain_id(self) -> str:
        return self.event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operation_event_id": self.event_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentTerminalV3:
    _issuer: InitVar[object]
    route_segment_start_id: str
    terminal_kind: RouteSegmentTerminalKindV3
    event_count: int
    event_ids: tuple[str, ...]
    predecessor_chain_id: str
    abort_reason: str | None

    def __post_init__(self, _issuer: object) -> None:
        _require_node_issuance(_issuer, "TERMINAL", self)
        _cid(self.route_segment_start_id, "route segment start")
        _cid(self.predecessor_chain_id, "predecessor chain")
        try:
            object.__setattr__(
                self, "terminal_kind", RouteSegmentTerminalKindV3(self.terminal_kind)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRouteSegmentV3Error(
                "route segment terminal kind is invalid"
            ) from error
        if (
            type(self.event_count) is not int
            or self.event_count < 0
            or type(self.event_ids) is not tuple
            or self.event_count != len(self.event_ids)
            or len(set(self.event_ids)) != len(self.event_ids)
        ):
            _fail("route segment terminal changed event coverage")
        for event_id in self.event_ids:
            _cid(event_id, "operation event")
        if self.terminal_kind is RouteSegmentTerminalKindV3.COMPLETED:
            if self.abort_reason is not None:
                _fail("completed segment cannot carry an abort reason")
        elif type(self.abort_reason) is not str or not self.abort_reason:
            _fail("aborted segment requires a reason")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_terminal.v3",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_start_id": self.route_segment_start_id,
            "terminal_kind": self.terminal_kind.value,
            "event_count": self.event_count,
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
        return _content_id(_TERMINAL_DOMAIN, self._payload())

    @property
    def chain_id(self) -> str:
        return self.terminal_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_terminal_id": self.terminal_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentTranscriptV3:
    _issuer: InitVar[object]
    start: OwnedRouteSegmentStartV3
    events: tuple[OwnedRouteOperationEventV3, ...]
    terminal: OwnedRouteSegmentTerminalV3

    def __post_init__(self, _issuer: object) -> None:
        _require_node_issuance(_issuer, "TRANSCRIPT", self)
        if (
            type(self.start) is not OwnedRouteSegmentStartV3
            or type(self.events) is not tuple
            or type(self.terminal) is not OwnedRouteSegmentTerminalV3
        ):
            _fail("route segment transcript uses foreign objects")
        predecessor = self.start.start_id
        for sequence, event in enumerate(self.events, start=1):
            if (
                type(event) is not OwnedRouteOperationEventV3
                or event.route_segment_start_id != self.start.start_id
                or event.event_sequence != sequence
                or event.predecessor_chain_id != predecessor
            ):
                _fail("route segment transcript event chain is discontinuous")
            predecessor = event.chain_id
        if (
            self.terminal.route_segment_start_id != self.start.start_id
            or self.terminal.predecessor_chain_id != predecessor
            or self.terminal.event_ids != tuple(row.event_id for row in self.events)
        ):
            _fail("route segment transcript terminal changed its positive prefix")

    @property
    def values(self) -> Mapping[str, int]:
        values: dict[str, int] = {}
        for event in self.events:
            values[event.path] = values.get(event.path, 0) + event.amount
        return MappingProxyType(values)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_transcript.v3",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "start": self.start.to_document(),
            "events": [row.to_document() for row in self.events],
            "terminal": self.terminal.to_document(),
            "event_count": len(self.events),
            "positive_prefix_retained": True,
            "absent_event_is_zero": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "production_owner_source_integrated": True,
            "production_closure_claimed": False,
        }

    @property
    def transcript_id(self) -> str:
        return _content_id(_TRANSCRIPT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_transcript_id": self.transcript_id}


_GATEWAY_ISSUER = object()


class OwnedFallbackRouteSegmentSessionV3:
    """Thread-owned recorder bound to the exact production-owner manifest."""

    def __init__(
        self,
        *,
        route_segment_id: str,
        occurrence_id: str,
        route_attempt_id: str,
        recorder_id: str,
        boundary_manifest: Any,
    ) -> None:
        from acfqp import (
            construction_k7_direct_fallback_operation_boundary_manifest_v3
            as manifest_v3,
        )

        registry = registry_v6.official_counter_registry_v6()
        stage_profile = registry_v6.official_stage_profile_v6(registry)
        registry.validate_official_catalogue()
        stage_profile.validate(registry)
        if (
            globals().get("emit_owned_route_operation_v3")
            is not _FROZEN_OPERATION_GATEWAY_V3
            or _FROZEN_OPERATION_GATEWAY_V3.__globals__
            is not _FROZEN_OPERATION_GATEWAY_GLOBALS_V3
            or _FROZEN_OPERATION_GATEWAY_V3.__code__
            is not _FROZEN_OPERATION_GATEWAY_CODE_V3
        ):
            _fail("owned route gateway differs from its module import binding")
        if type(boundary_manifest) is not manifest_v3.DirectFallbackOperationBoundaryManifestV3:
            _fail("owned fallback session requires the exact V3 manifest")
        if (
            manifest_v3.require_frozen_live_owner_binding_v3
            is not manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_OBJECT_V3
            or manifest_v3.require_frozen_live_owner_binding_v3.__globals__
            is not manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_GLOBALS_V3
            or manifest_v3.require_frozen_live_owner_binding_v3.__code__
            is not manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_CODE_V3
        ):
            _fail("owned fallback live-binding validator changed")
        try:
            live_binding = manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_OBJECT_V3(
                boundary_manifest
            )
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRouteSegmentV3Error(
                "owned fallback import-time live source binding changed"
            ) from error
        replay = manifest_v3.replay_direct_fallback_operation_source_archive_v3(
            manifest_v3.load_direct_fallback_operation_source_archive_v3()
        )
        if (
            replay.manifest is None
            or replay.blockers
            or replay.manifest.to_document() != boundary_manifest.to_document()
        ):
            _fail("owned fallback manifest differs from independent source replay")
        if (
            boundary_manifest.counter_registry_id != registry.registry_id
            or boundary_manifest.stage_profile_id != stage_profile.stage_profile_id
            or boundary_manifest.stage_kind
            is not registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ):
            _fail("owned fallback manifest crossed registry or stage")
        allowed = set(
            stage_profile.by_stage[
                registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
            ].allowed_nonzero_paths
        )
        owner_bindings: dict[str, tuple[Any, Any]] = {}
        frozen_methods = {
            name: (function, code)
            for name, function, code in live_binding.method_bindings
        }
        for dispatch_key, boundary in boundary_manifest.by_dispatch.items():
            leaf = registry.by_path.get(boundary.target_path)
            if (
                leaf is None
                or boundary.target_path not in allowed
                or boundary.reducer is not ReducerEnum.SUM
                or leaf.reducer is not ReducerEnum.SUM
            ):
                _fail("owned fallback boundary targets an invalid V6 leaf")
            owner_globals, owner_code = _resolve_owner(
                boundary.operation_source_module,
                boundary.operation_source_symbol,
            )
            method_name = boundary.operation_source_symbol.rsplit(".", 1)[-1]
            frozen_method = frozen_methods.get(method_name)
            if frozen_method is None:
                _fail("owned fallback manifest names an unfrozen ledger method")
            frozen_function, frozen_code = frozen_method
            if (
                owner_globals is not live_binding.owner_globals
                or owner_code is not frozen_code
                or getattr(live_binding.owner_class, method_name, None)
                is not frozen_function
                or owner_globals.get("_OwnedFallbackLedgerV2")
                is not live_binding.owner_class
                or owner_globals.get("emit_owned_route_operation_v3")
                is not live_binding.gateway
                or live_binding.gateway is not _FROZEN_OPERATION_GATEWAY_V3
            ):
                _fail("owned fallback source differs from import-time identities")
            owner_bindings[dispatch_key] = (owner_globals, frozen_code)
        self._lock = threading.RLock()
        self._owner_thread_id = threading.get_ident()
        self._manifest = boundary_manifest
        self._by_dispatch = MappingProxyType(dict(boundary_manifest.by_dispatch))
        self._owner_bindings = MappingProxyType(owner_bindings)
        self._live_binding = live_binding
        self._live_binding_validator = (
            manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_OBJECT_V3,
            manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_GLOBALS_V3,
            manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_CODE_V3,
        )
        self._gateway_binding = (
            _FROZEN_OPERATION_GATEWAY_V3,
            _FROZEN_OPERATION_GATEWAY_GLOBALS_V3,
            _FROZEN_OPERATION_GATEWAY_CODE_V3,
        )
        self._start = OwnedRouteSegmentStartV3(
            _NODE_ISSUER,
            _cid(route_segment_id, "route segment"),
            _cid(occurrence_id, "occurrence"),
            _cid(route_attempt_id, "route attempt"),
            registry.registry_id,
            stage_profile.stage_profile_id,
            boundary_manifest.boundary_manifest_id,
            recorder_id,
        )
        self._events: list[OwnedRouteOperationEventV3] = []
        self._active = False
        self._terminal: OwnedRouteSegmentTerminalV3 | None = None
        self._bound_ledger: Any | None = None
        self._search_frame: Any | None = None
        self._search_finished = False
        self._finished_values: Mapping[str, int] | None = None

    @property
    def start(self) -> OwnedRouteSegmentStartV3:
        return self._start

    @property
    def is_terminal(self) -> bool:
        return self._terminal is not None

    @property
    def transcript(self) -> OwnedRouteSegmentTranscriptV3:
        if self._terminal is None:
            _fail("owned fallback transcript is unavailable before terminalization")
        return OwnedRouteSegmentTranscriptV3(
            _NODE_ISSUER, self._start, tuple(self._events), self._terminal
        )

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            self._abort("CROSS_THREAD_ACTIVE_SCOPE")
            _fail("owned fallback accounting crossed its owner thread")

    def _predecessor(self) -> str:
        return self._events[-1].chain_id if self._events else self._start.start_id

    @staticmethod
    def _ledger_values(ledger: Any) -> Mapping[str, int]:
        return MappingProxyType(
            {
                "fallback.states_expanded": ledger.states_expanded,
                "fallback.actions_evaluated": ledger.actions_evaluated,
                "fallback.ground_steps": ledger.ground_steps,
                "fallback.outcome_rows": ledger.outcome_rows,
                "fallback.bellman_backups": ledger.bellman_backups,
                "control.cap_checks": ledger.cap_checks,
                "control.cap_rejections": ledger.cap_rejections,
            }
        )

    @staticmethod
    def _frame_descends_from(frame: Any, ancestor: Any) -> bool:
        current = frame
        while current is not None:
            if current is ancestor:
                return True
            current = current.f_back
        return False

    def _bind_search_from_owner(
        self,
        issuer: object,
        ledger: Any,
        search_frame: Any,
    ) -> None:
        with self._lock:
            self._check_thread()
            try:
                wrapper_frame = _FROZEN_GETFRAME_V3(1)
            except (AttributeError, ValueError) as error:
                self._abort("SEARCH_BIND_WRAPPER_UNAVAILABLE")
                raise ConstructionAccountingRouteSegmentV3Error(
                    "owned fallback search-bind wrapper is unavailable"
                ) from error
            if (
                wrapper_frame.f_globals
                is not _FROZEN_SEARCH_BIND_WRAPPER_GLOBALS_V3
                or wrapper_frame.f_code
                is not _FROZEN_SEARCH_BIND_WRAPPER_CODE_V3
                or globals().get("bind_owned_fallback_search_v3")
                is not _FROZEN_SEARCH_BIND_WRAPPER_OBJECT_V3
                or _FROZEN_SEARCH_BIND_WRAPPER_OBJECT_V3.__globals__
                is not _FROZEN_SEARCH_BIND_WRAPPER_GLOBALS_V3
                or _FROZEN_SEARCH_BIND_WRAPPER_OBJECT_V3.__code__
                is not _FROZEN_SEARCH_BIND_WRAPPER_CODE_V3
                or search_frame is not wrapper_frame.f_back
            ):
                self._abort("SEARCH_BIND_WRAPPER_BYPASSED")
                _fail("owned fallback search binding bypassed its frozen wrapper")
            current_authorizer = globals().get(
                "_require_authorized_owned_search_frame_v3"
            )
            if (
                current_authorizer
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3
                or getattr(current_authorizer, "__globals__", None)
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_GLOBALS_V3
                or getattr(current_authorizer, "__code__", None)
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_CODE_V3
                or _FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3.__globals__
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_GLOBALS_V3
                or _FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3.__code__
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_CODE_V3
            ):
                self._abort("SEARCH_FRAME_AUTHORIZER_CHANGED")
                _fail("owned fallback search-frame authorizer changed")
            try:
                _FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3(search_frame)
            except ConstructionAccountingRouteSegmentV3Error:
                self._abort("UNAUTHORIZED_SEARCH_CALLER")
                raise
            if (
                issuer is not _SEARCH_BIND_ISSUER_V3
                or self._terminal is not None
                or not self._active
                or self._bound_ledger is not None
                or self._search_frame is not None
                or self._search_finished
            ):
                self._abort("INVALID_SEARCH_BINDING")
                _fail("owned fallback search binding is invalid")
            self._revalidate()
            if type(ledger) is not self._live_binding.owner_class:
                self._abort("FOREIGN_LEDGER_INSTANCE")
                _fail("owned fallback search used a foreign ledger instance")
            self._bound_ledger = ledger
            self._search_frame = search_frame

    def _finish_search_from_owner(
        self,
        issuer: object,
        ledger: Any,
        search_frame: Any,
    ) -> None:
        with self._lock:
            self._check_thread()
            try:
                wrapper_frame = _FROZEN_GETFRAME_V3(1)
            except (AttributeError, ValueError) as error:
                self._abort("SEARCH_FINISH_WRAPPER_UNAVAILABLE")
                raise ConstructionAccountingRouteSegmentV3Error(
                    "owned fallback search-finish wrapper is unavailable"
                ) from error
            if (
                wrapper_frame.f_globals
                is not _FROZEN_SEARCH_FINISH_WRAPPER_GLOBALS_V3
                or wrapper_frame.f_code
                is not _FROZEN_SEARCH_FINISH_WRAPPER_CODE_V3
                or globals().get("finish_owned_fallback_search_v3")
                is not _FROZEN_SEARCH_FINISH_WRAPPER_OBJECT_V3
                or _FROZEN_SEARCH_FINISH_WRAPPER_OBJECT_V3.__globals__
                is not _FROZEN_SEARCH_FINISH_WRAPPER_GLOBALS_V3
                or _FROZEN_SEARCH_FINISH_WRAPPER_OBJECT_V3.__code__
                is not _FROZEN_SEARCH_FINISH_WRAPPER_CODE_V3
                or search_frame is not wrapper_frame.f_back
            ):
                self._abort("SEARCH_FINISH_WRAPPER_BYPASSED")
                _fail("owned fallback search finish bypassed its frozen wrapper")
            current_authorizer = globals().get(
                "_require_authorized_owned_search_frame_v3"
            )
            if (
                current_authorizer
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3
                or getattr(current_authorizer, "__globals__", None)
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_GLOBALS_V3
                or getattr(current_authorizer, "__code__", None)
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_CODE_V3
                or _FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3.__globals__
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_GLOBALS_V3
                or _FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3.__code__
                is not _FROZEN_SEARCH_FRAME_AUTHORIZER_CODE_V3
            ):
                self._abort("SEARCH_FRAME_AUTHORIZER_CHANGED")
                _fail("owned fallback search-frame authorizer changed")
            try:
                _FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3(search_frame)
            except ConstructionAccountingRouteSegmentV3Error:
                self._abort("UNAUTHORIZED_SEARCH_CALLER")
                raise
            if (
                issuer is not _SEARCH_FINISH_ISSUER_V3
                or self._terminal is not None
                or not self._active
                or ledger is not self._bound_ledger
                or search_frame is not self._search_frame
                or self._search_finished
            ):
                self._abort("INVALID_SEARCH_FINISH")
                _fail("owned fallback search finish is invalid")
            self._revalidate()
            values = self._ledger_values(ledger)
            positive = {path: value for path, value in values.items() if value > 0}
            if (
                dict(self.transcript_values_before_terminal) != positive
                or len(self._events) != sum(positive.values())
            ):
                self._abort("LEDGER_TRANSCRIPT_DIVERGENCE")
                _fail("owned fallback ledger and event transcript diverged")
            self._finished_values = values
            self._search_finished = True

    @property
    def transcript_values_before_terminal(self) -> Mapping[str, int]:
        values: dict[str, int] = {}
        for event in self._events:
            values[event.path] = values.get(event.path, 0) + event.amount
        return MappingProxyType(values)

    def _revalidate(self) -> None:
        current_gateway = globals().get("emit_owned_route_operation_v3")
        expected, expected_globals, expected_code = self._gateway_binding
        if (
            current_gateway is not expected
            or getattr(current_gateway, "__globals__", None) is not expected_globals
            or getattr(current_gateway, "__code__", None) is not expected_code
        ):
            self._abort("LIVE_GATEWAY_BINDING_CHANGED")
            _fail("owned fallback gateway changed after session binding")
        from acfqp import (
            construction_k7_direct_fallback_operation_boundary_manifest_v3
            as manifest_v3,
        )

        validator, validator_globals, validator_code = self._live_binding_validator
        current_validator = getattr(
            manifest_v3, "require_frozen_live_owner_binding_v3", None
        )
        if (
            current_validator is not validator
            or getattr(current_validator, "__globals__", None) is not validator_globals
            or getattr(current_validator, "__code__", None) is not validator_code
            or validator
            is not manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_OBJECT_V3
            or validator_globals
            is not manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_GLOBALS_V3
            or validator_code is not manifest_v3._FROZEN_LIVE_OWNER_VALIDATOR_CODE_V3
        ):
            self._abort("LIVE_BINDING_VALIDATOR_CHANGED")
            _fail("owned fallback live-binding validator changed")
        try:
            current_binding = validator(self._manifest)
        except (TypeError, ValueError):
            self._abort("LIVE_OWNER_BINDING_CHANGED")
            _fail("owned fallback import-time owner binding changed")
        if (
            current_binding.owner_class is not self._live_binding.owner_class
            or current_binding.owner_globals is not self._live_binding.owner_globals
            or current_binding.gateway is not self._live_binding.gateway
            or len(current_binding.method_bindings)
            != len(self._live_binding.method_bindings)
            or any(
                left_name != right_name
                or left_function is not right_function
                or left_code is not right_code
                for (
                    left_name,
                    left_function,
                    left_code,
                ), (
                    right_name,
                    right_function,
                    right_code,
                ) in zip(
                    current_binding.method_bindings,
                    self._live_binding.method_bindings,
                )
            )
        ):
            self._abort("LIVE_OWNER_BINDING_CHANGED")
            _fail("owned fallback import-time owner binding changed")
        for dispatch_key, boundary in self._by_dispatch.items():
            try:
                current_globals, current_code = _resolve_owner(
                    boundary.operation_source_module,
                    boundary.operation_source_symbol,
                )
            except ConstructionAccountingRouteSegmentV3Error:
                self._abort("LIVE_OWNER_BINDING_CHANGED")
                _fail("owned fallback owner changed after session binding")
            expected_globals, expected_code = self._owner_bindings[dispatch_key]
            if (
                current_globals is not expected_globals
                or current_code is not expected_code
                or current_globals.get("emit_owned_route_operation_v3")
                is not _FROZEN_OPERATION_GATEWAY_V3
            ):
                self._abort("LIVE_OWNER_BINDING_CHANGED")
                _fail("owned fallback owner changed after session binding")

    def enter(self) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or self._active:
                _fail("owned fallback stage entered in an invalid state")
            self._revalidate()
            self._active = True

    def _emit_from_gateway(
        self,
        issuer: object,
        dispatch_key: Any,
        amount: Any,
        *,
        owner_module: Any,
        owner_globals: Any,
        owner_code: Any,
        owner_instance: Any,
        owner_frame: Any,
    ) -> object:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or not self._active:
                self._abort("EVENT_OUTSIDE_ACTIVE_STAGE")
                _fail("owned fallback event lies outside its active stage")
            # Recheck the archived-source/live-code join at the event boundary,
            # before constructing or appending the next immutable node.  A
            # mutation after ``enter()`` must not be retained as if it were a
            # legitimate positive prefix and discovered only at completion.
            self._revalidate()
            if (
                self._bound_ledger is None
                or owner_instance is not self._bound_ledger
                or self._search_frame is None
                or not self._frame_descends_from(owner_frame, self._search_frame)
                or self._search_finished
            ):
                self._abort("UNBOUND_LEDGER_OR_SEARCH")
                _fail("owned fallback event is outside its bound search invocation")
            try:
                gateway_frame = _FROZEN_GETFRAME_V3(1)
            except (AttributeError, ValueError) as error:
                self._abort("GATEWAY_FRAME_UNAVAILABLE")
                raise ConstructionAccountingRouteSegmentV3Error(
                    "owned fallback gateway frame is unavailable"
                ) from error
            expected_gateway, expected_globals, expected_code = self._gateway_binding
            if (
                issuer is not _GATEWAY_ISSUER
                or gateway_frame.f_globals is not expected_globals
                or gateway_frame.f_code is not expected_code
                or globals().get("emit_owned_route_operation_v3")
                is not expected_gateway
            ):
                self._abort("UNTRUSTED_GATEWAY_CALLER")
                _fail("owned fallback event bypassed the frozen gateway")
            if type(dispatch_key) is not str or type(amount) is not int or amount != 1:
                self._abort("MALFORMED_OPERATION")
                _fail("owned fallback event is not one literal unit primitive")
            boundary = self._by_dispatch.get(dispatch_key)
            if boundary is None:
                self._abort("UNKNOWN_DISPATCH")
                _fail("owned fallback dispatch is absent from the V3 manifest")
            expected_owner_globals, expected_owner_code = self._owner_bindings[dispatch_key]
            if (
                owner_module != boundary.operation_source_module
                or owner_globals is not expected_owner_globals
                or owner_code is not expected_owner_code
            ):
                self._abort("OWNER_MISMATCH")
                _fail("owned fallback dispatch caller differs from its source site")
            self._events.append(
                OwnedRouteOperationEventV3(
                    _NODE_ISSUER,
                    self._start.start_id,
                    boundary.boundary_id,
                    dispatch_key,
                    boundary.target_path,
                    amount,
                    len(self._events) + 1,
                    self._predecessor(),
                )
            )
            return OWNED_ROUTE_EVENT_ACK_V3

    def complete(self) -> OwnedRouteSegmentTranscriptV3:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or not self._active:
                _fail("owned fallback segment cannot complete in its current state")
            self._revalidate()
            if (
                not self._search_finished
                or self._bound_ledger is None
                or self._finished_values is None
                or self._ledger_values(self._bound_ledger) != self._finished_values
                or dict(self.transcript_values_before_terminal)
                != {
                    path: value
                    for path, value in self._finished_values.items()
                    if value > 0
                }
            ):
                self._abort("UNVERIFIED_SEARCH_COMPLETION")
                _fail("owned fallback segment lacks an exact finished search")
            self._active = False
            event_ids = tuple(row.event_id for row in self._events)
            self._terminal = OwnedRouteSegmentTerminalV3(
                _NODE_ISSUER,
                self._start.start_id,
                RouteSegmentTerminalKindV3.COMPLETED,
                len(event_ids),
                event_ids,
                self._predecessor(),
                None,
            )
            return self.transcript

    def _abort(self, reason: str) -> None:
        with self._lock:
            if self._terminal is not None:
                return
            self._active = False
            event_ids = tuple(row.event_id for row in self._events)
            self._terminal = OwnedRouteSegmentTerminalV3(
                _NODE_ISSUER,
                self._start.start_id,
                RouteSegmentTerminalKindV3.ABORTED,
                len(event_ids),
                event_ids,
                self._predecessor(),
                reason,
            )

    def abort(self, reason: str = "CALLER_REQUESTED_ABORT") -> OwnedRouteSegmentTranscriptV3:
        self._check_thread()
        self._abort(reason)
        return self.transcript


_FROZEN_NODE_GLOBALS_V3 = globals()
_FROZEN_NODE_CODES_V3 = MappingProxyType(
    {
        "START": OwnedFallbackRouteSegmentSessionV3.__init__.__code__,
        "EVENT": OwnedFallbackRouteSegmentSessionV3._emit_from_gateway.__code__,
        "TERMINAL": (
            OwnedFallbackRouteSegmentSessionV3.complete.__code__,
            OwnedFallbackRouteSegmentSessionV3._abort.__code__,
        ),
        "TRANSCRIPT": OwnedFallbackRouteSegmentSessionV3.transcript.fget.__code__,
    }
)


_ACTIVE_OWNED_ROUTE_RUNTIME_V3: ContextVar[
    OwnedFallbackRouteSegmentSessionV3 | None
] = ContextVar("acfqp_owned_fallback_route_runtime_v3", default=None)


@contextmanager
def activate_owned_route_segment_v3(
    session: OwnedFallbackRouteSegmentSessionV3,
) -> Iterator[OwnedFallbackRouteSegmentSessionV3]:
    if type(session) is not OwnedFallbackRouteSegmentSessionV3:
        _fail("owned route activation requires the exact V3 session")
    session._check_thread()
    incumbent = _ACTIVE_OWNED_ROUTE_RUNTIME_V3.get()
    if incumbent is not None:
        incumbent._abort("NESTED_ACTIVE_SCOPE")
        _fail("nested owned route segments are forbidden")
    token: Token[Any] = _ACTIVE_OWNED_ROUTE_RUNTIME_V3.set(session)
    try:
        yield session
    except BaseException:
        if not session.is_terminal:
            session._abort("ACTIVE_SCOPE_EXCEPTION")
        raise
    else:
        if not session.is_terminal:
            session._abort("INCOMPLETE_SCOPE_EXIT")
            _fail("owned route scope exited without terminalization")
    finally:
        _ACTIVE_OWNED_ROUTE_RUNTIME_V3.reset(token)


def emit_owned_route_operation_v3(
    dispatch_key: Any,
    amount: Any = 1,
) -> object | None:
    """Emit from a V3-bound owner site, or remain a no-op when inactive."""

    session = _ACTIVE_OWNED_ROUTE_RUNTIME_V3.get()
    if session is None:
        return None
    try:
        caller = _FROZEN_GETFRAME_V3(1)
    except (AttributeError, ValueError) as error:
        session._abort("CALLER_FRAME_UNAVAILABLE")
        raise ConstructionAccountingRouteSegmentV3Error(
            "owned fallback caller frame is unavailable"
        ) from error
    return session._emit_from_gateway(
        _GATEWAY_ISSUER,
        dispatch_key,
        amount,
        owner_module=caller.f_globals.get("__name__"),
        owner_globals=caller.f_globals,
        owner_code=caller.f_code,
        owner_instance=caller.f_locals.get("self"),
        owner_frame=caller,
    )


_FROZEN_OPERATION_GATEWAY_V3 = emit_owned_route_operation_v3
_FROZEN_OPERATION_GATEWAY_GLOBALS_V3 = emit_owned_route_operation_v3.__globals__
_FROZEN_OPERATION_GATEWAY_CODE_V3 = emit_owned_route_operation_v3.__code__


def _require_authorized_owned_search_frame_v3(search_frame: Any) -> None:
    from acfqp import (
        construction_k7_canonical_infeasible_fallback_owned_runner_v2
        as runner_v2,
    )

    caller = search_frame.f_back
    if (
        search_frame.f_globals is not runner_v2._EXPECTED_OWNED_SEARCH_GLOBALS
        or search_frame.f_code is not runner_v2._EXPECTED_OWNED_SEARCH_CODE
        or caller is None
        or caller.f_globals
        is not runner_v2._FROZEN_AUTHORIZED_SEARCH_CALLER_GLOBALS_V2
        or caller.f_code is not runner_v2._FROZEN_AUTHORIZED_SEARCH_CALLER_CODE_V2
        or runner_v2._execute_authorized_owned_search_segment_v2
        is not runner_v2._FROZEN_AUTHORIZED_SEARCH_CALLER_OBJECT_V2
        or runner_v2._FROZEN_AUTHORIZED_SEARCH_CALLER_OBJECT_V2.__globals__
        is not runner_v2._FROZEN_AUTHORIZED_SEARCH_CALLER_GLOBALS_V2
        or runner_v2._FROZEN_AUTHORIZED_SEARCH_CALLER_OBJECT_V2.__code__
        is not runner_v2._FROZEN_AUTHORIZED_SEARCH_CALLER_CODE_V2
    ):
        _fail("owned fallback search lacks its frozen authorized caller")


_FROZEN_SEARCH_FRAME_AUTHORIZER_OBJECT_V3 = (
    _require_authorized_owned_search_frame_v3
)
_FROZEN_SEARCH_FRAME_AUTHORIZER_GLOBALS_V3 = (
    _require_authorized_owned_search_frame_v3.__globals__
)
_FROZEN_SEARCH_FRAME_AUTHORIZER_CODE_V3 = (
    _require_authorized_owned_search_frame_v3.__code__
)


def bind_owned_fallback_search_v3(ledger: Any) -> None:
    session = _ACTIVE_OWNED_ROUTE_RUNTIME_V3.get()
    if session is None:
        _fail("owned fallback search requires an active route segment")
    try:
        search_frame = _FROZEN_GETFRAME_V3(1)
    except (AttributeError, ValueError) as error:
        session._abort("SEARCH_FRAME_UNAVAILABLE")
        raise ConstructionAccountingRouteSegmentV3Error(
            "owned fallback search frame is unavailable"
        ) from error
    try:
        _require_authorized_owned_search_frame_v3(search_frame)
    except ConstructionAccountingRouteSegmentV3Error:
        session._abort("UNAUTHORIZED_SEARCH_CALLER")
        raise
    session._bind_search_from_owner(_SEARCH_BIND_ISSUER_V3, ledger, search_frame)


def finish_owned_fallback_search_v3(ledger: Any) -> None:
    session = _ACTIVE_OWNED_ROUTE_RUNTIME_V3.get()
    if session is None:
        _fail("owned fallback search finish requires an active route segment")
    try:
        search_frame = _FROZEN_GETFRAME_V3(1)
    except (AttributeError, ValueError) as error:
        session._abort("SEARCH_FRAME_UNAVAILABLE")
        raise ConstructionAccountingRouteSegmentV3Error(
            "owned fallback search frame is unavailable"
        ) from error
    try:
        _require_authorized_owned_search_frame_v3(search_frame)
    except ConstructionAccountingRouteSegmentV3Error:
        session._abort("UNAUTHORIZED_SEARCH_CALLER")
        raise
    session._finish_search_from_owner(
        _SEARCH_FINISH_ISSUER_V3,
        ledger,
        search_frame,
    )


_FROZEN_SEARCH_BIND_WRAPPER_OBJECT_V3 = bind_owned_fallback_search_v3
_FROZEN_SEARCH_BIND_WRAPPER_GLOBALS_V3 = bind_owned_fallback_search_v3.__globals__
_FROZEN_SEARCH_BIND_WRAPPER_CODE_V3 = bind_owned_fallback_search_v3.__code__
_FROZEN_SEARCH_FINISH_WRAPPER_OBJECT_V3 = finish_owned_fallback_search_v3
_FROZEN_SEARCH_FINISH_WRAPPER_GLOBALS_V3 = (
    finish_owned_fallback_search_v3.__globals__
)
_FROZEN_SEARCH_FINISH_WRAPPER_CODE_V3 = finish_owned_fallback_search_v3.__code__


__all__ = (
    "CONSTRUCTION_ONLY",
    "ConstructionAccountingRouteSegmentV3Error",
    "OwnedFallbackRouteSegmentSessionV3",
    "OwnedRouteOperationEventV3",
    "OwnedRouteSegmentStartV3",
    "OwnedRouteSegmentTerminalV3",
    "OwnedRouteSegmentTranscriptV3",
    "OWNED_ROUTE_EVENT_ACK_V3",
    "PRODUCTION_CLOSURE_CLAIMED",
    "PRODUCTION_OWNER_SOURCE_INTEGRATED",
    "PROFILE_KEY",
    "PYTHON_API_SPOOF_RESISTANCE_ONLY",
    "RouteSegmentTerminalKindV3",
    "SCHEMA_VERSION",
    "activate_owned_route_segment_v3",
    "bind_owned_fallback_search_v3",
    "emit_owned_route_operation_v3",
    "finish_owned_fallback_search_v3",
)
