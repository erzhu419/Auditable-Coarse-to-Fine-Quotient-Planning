"""Additive owner-bound accounting for one construction route segment.

This module is deliberately independent of the historical five-stage root-cap
runtime.  A session owns exactly one V6 construction stage, records only
positive primitive events observed at source-bound call sites, and freezes an
immutable start -> stage -> events -> completion/abort chain.  It does not
materialize absent events as zero and it does not issue CounterRecords,
WorkVectors, ComparisonVectors, terminal certificates, or production closure.
Its frame-ancestry checks defend this construction harness against Python-API
spoofing only; they are not a native-code or production security boundary.

The small ``DirectFallbackOwnedOperationSourceV2`` class at the bottom is a
future/test source binding for the first additive manifest.  It is not the
production fallback solver.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import importlib
import re
import sys
import threading
from types import MappingProxyType
from typing import Any, Iterator, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "construction_accounting_route_segment_v2"
COVERAGE_STATE = "ROUTE_SEGMENT_POSITIVE_EVENTS_ONLY"
CENTRAL_DOMAIN_REGISTRATION_PENDING = True
PRODUCTION_CLOSURE_CLAIMED = False
CONSTRUCTION_ONLY = True
PYTHON_API_SPOOF_RESISTANCE_ONLY = True
NATIVE_CODE_ADVERSARY_RESISTANCE_CLAIMED = False

_START_DOMAIN = "acfqp:construction-accounting-route-segment-start:v2"
_STAGE_START_DOMAIN = (
    "acfqp:construction-accounting-route-segment-stage-start:v2"
)
_EVENT_DOMAIN = "acfqp:construction-accounting-route-segment-event:v2"
_STAGE_COMPLETION_DOMAIN = (
    "acfqp:construction-accounting-route-segment-stage-completion:v2"
)
_COMPLETION_DOMAIN = (
    "acfqp:construction-accounting-route-segment-completion:v2"
)
_ABORT_DOMAIN = "acfqp:construction-accounting-route-segment-abort:v2"
_TRANSCRIPT_DOMAIN = (
    "acfqp:construction-accounting-route-segment-transcript:v2"
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_DISPATCH_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_ABORT_REASON = re.compile(r"^[A-Z][A-Z0-9_]*$")
_FROZEN_GETFRAME_V2 = sys._getframe  # noqa: SLF001


class ConstructionAccountingRouteSegmentV2Error(RuntimeError):
    """The route-segment binding, event, or lifecycle is invalid."""


class RouteSegmentTerminalKindV2(str, Enum):
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


_NODE_ISSUER = object()
_GATEWAY_ISSUER = object()


def _require_session_node_issuance_v2(
    issuer: object,
    node: Any,
    authorized_caller_key: str,
) -> None:
    """Require dataclass-init -> exact session-method construction ancestry."""

    if issuer is not _NODE_ISSUER:
        _fail("route-segment chain object is session-issued only")
    try:
        generated_init_frame = _FROZEN_GETFRAME_V2(2)
        session_caller_frame = _FROZEN_GETFRAME_V2(3)
        expected_code = _FROZEN_NODE_ISSUER_CODES_V2[authorized_caller_key]
    except (AttributeError, KeyError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV2Error(
            "route-segment issuance ancestry is unavailable"
        ) from error
    if (
        generated_init_frame.f_code is not type(node).__init__.__code__
        or session_caller_frame.f_globals is not _FROZEN_NODE_ISSUER_GLOBALS_V2
        or session_caller_frame.f_code is not expected_code
    ):
        _fail("route-segment chain object bypassed its exact session issuer")


def _fail(message: str) -> NoReturn:
    raise ConstructionAccountingRouteSegmentV2Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    # These domains intentionally remain local until the integration slice.
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV2Error(
            f"{label} must be one full content ID"
        ) from error


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{label} must be one canonical identifier")
    return value


def _stage(value: Any) -> registry_v6.ConstructionStageKindV6:
    try:
        return registry_v6.ConstructionStageKindV6(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV2Error(
            f"unknown V6 construction stage {value!r}"
        ) from error


def _abort_reason(value: Any) -> str:
    if type(value) is not str or _ABORT_REASON.fullmatch(value) is None:
        _fail("abort reason must be one canonical uppercase code")
    return value


def _base_payload(
    *,
    schema: str,
    route_segment_start_id: str,
    chain_sequence: int,
    predecessor_chain_id: str,
) -> dict[str, Any]:
    _cid(route_segment_start_id, "route segment start")
    _cid(predecessor_chain_id, "predecessor chain")
    if type(chain_sequence) is not int or chain_sequence <= 0:
        _fail("route-segment chain sequence must be positive")
    return {
        "schema": schema,
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "route_segment_start_id": route_segment_start_id,
        "chain_sequence": chain_sequence,
        "predecessor_chain_id": predecessor_chain_id,
        "coverage_state": COVERAGE_STATE,
        "construction_only": True,
        "python_api_spoof_resistance_only": True,
        "native_code_adversary_resistance_claimed": False,
        "central_domain_registration_pending": True,
        "production_closure_claimed": False,
    }


@dataclass(frozen=True, slots=True)
class RouteSegmentStartV2:
    _issuer: InitVar[object]
    route_segment_id: str
    occurrence_id: str
    route_attempt_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_manifest_id: str
    recorder_id: str
    stage_kind: registry_v6.ConstructionStageKindV6

    def __post_init__(self, _issuer: object) -> None:
        _require_session_node_issuance_v2(_issuer, self, "START")
        for value, label in (
            (self.route_segment_id, "route segment"),
            (self.occurrence_id, "occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.boundary_manifest_id, "boundary manifest"),
        ):
            _cid(value, label)
        _identifier(self.recorder_id, "recorder ID")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_route_segment_start.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_id": self.route_segment_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "recorder_id": self.recorder_id,
            "stage_kind": self.stage_kind.value,
            "chain_sequence": 0,
            "predecessor_chain_id": None,
            "coverage_state": COVERAGE_STATE,
            "positive_events_only": True,
            "absent_event_is_zero": False,
            "construction_only": True,
            "python_api_spoof_resistance_only": True,
            "native_code_adversary_resistance_claimed": False,
            "central_domain_registration_pending": True,
            "production_closure_claimed": False,
        }

    @property
    def start_id(self) -> str:
        return _content_id(_START_DOMAIN, self._payload())

    @property
    def chain_id(self) -> str:
        return self.start_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_start_id": self.start_id}


@dataclass(frozen=True, slots=True)
class RouteSegmentStageStartV2:
    _issuer: InitVar[object]
    route_segment_start_id: str
    stage_kind: registry_v6.ConstructionStageKindV6
    chain_sequence: int
    predecessor_chain_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_session_node_issuance_v2(_issuer, self, "STAGE_START")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        _base_payload(
            schema="acfqp.construction_accounting_route_segment_stage_start.v2",
            route_segment_start_id=self.route_segment_start_id,
            chain_sequence=self.chain_sequence,
            predecessor_chain_id=self.predecessor_chain_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            **_base_payload(
                schema="acfqp.construction_accounting_route_segment_stage_start.v2",
                route_segment_start_id=self.route_segment_start_id,
                chain_sequence=self.chain_sequence,
                predecessor_chain_id=self.predecessor_chain_id,
            ),
            "stage_kind": self.stage_kind.value,
            "stage_occurrence_index": 1,
        }

    @property
    def chain_id(self) -> str:
        return _content_id(_STAGE_START_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_start_id": self.chain_id}


@dataclass(frozen=True, slots=True)
class RouteSegmentOperationEventV2:
    _issuer: InitVar[object]
    route_segment_start_id: str
    stage_kind: registry_v6.ConstructionStageKindV6
    boundary_id: str
    dispatch_key: str
    path: str
    reducer: ReducerEnum
    amount: int
    stage_event_sequence: int
    chain_sequence: int
    predecessor_chain_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_session_node_issuance_v2(_issuer, self, "EVENT")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        _cid(self.boundary_id, "operation boundary")
        if (
            type(self.dispatch_key) is not str
            or _DISPATCH_KEY.fullmatch(self.dispatch_key) is None
        ):
            _fail("event dispatch key is noncanonical")
        _identifier(self.path, "counter path")
        try:
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRouteSegmentV2Error(
                "event reducer is invalid"
            ) from error
        if self.reducer is not ReducerEnum.SUM:
            _fail("route-segment owned events currently support SUM only")
        if type(self.amount) is not int or self.amount != 1:
            _fail("each source event must represent exactly one primitive")
        if type(self.stage_event_sequence) is not int or self.stage_event_sequence <= 0:
            _fail("stage event sequence must be positive")
        _base_payload(
            schema="acfqp.construction_accounting_route_segment_event.v2",
            route_segment_start_id=self.route_segment_start_id,
            chain_sequence=self.chain_sequence,
            predecessor_chain_id=self.predecessor_chain_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            **_base_payload(
                schema="acfqp.construction_accounting_route_segment_event.v2",
                route_segment_start_id=self.route_segment_start_id,
                chain_sequence=self.chain_sequence,
                predecessor_chain_id=self.predecessor_chain_id,
            ),
            "stage_kind": self.stage_kind.value,
            "boundary_id": self.boundary_id,
            "dispatch_key": self.dispatch_key,
            "path": self.path,
            "reducer": self.reducer.value,
            "amount": self.amount,
            "stage_event_sequence": self.stage_event_sequence,
            "caller_reported_summary_allowed": False,
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
class RouteSegmentStageCompletionV2:
    _issuer: InitVar[object]
    route_segment_start_id: str
    stage_kind: registry_v6.ConstructionStageKindV6
    event_ids: tuple[str, ...]
    chain_sequence: int
    predecessor_chain_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_session_node_issuance_v2(_issuer, self, "STAGE_COMPLETION")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        if type(self.event_ids) is not tuple:
            _fail("stage completion event IDs must be one exact tuple")
        for event_id in self.event_ids:
            _cid(event_id, "stage event")
        if len(set(self.event_ids)) != len(self.event_ids):
            _fail("stage completion repeats an event ID")
        _base_payload(
            schema=(
                "acfqp.construction_accounting_route_segment_stage_completion.v2"
            ),
            route_segment_start_id=self.route_segment_start_id,
            chain_sequence=self.chain_sequence,
            predecessor_chain_id=self.predecessor_chain_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            **_base_payload(
                schema=(
                    "acfqp.construction_accounting_route_segment_stage_completion.v2"
                ),
                route_segment_start_id=self.route_segment_start_id,
                chain_sequence=self.chain_sequence,
                predecessor_chain_id=self.predecessor_chain_id,
            ),
            "stage_kind": self.stage_kind.value,
            "stage_occurrence_index": 1,
            "event_ids": list(self.event_ids),
            "event_count": len(self.event_ids),
        }

    @property
    def chain_id(self) -> str:
        return _content_id(_STAGE_COMPLETION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_completion_id": self.chain_id}


@dataclass(frozen=True, slots=True)
class RouteSegmentCompletionV2:
    _issuer: InitVar[object]
    route_segment_start_id: str
    stage_completion_id: str
    total_event_count: int
    chain_sequence: int
    predecessor_chain_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_session_node_issuance_v2(_issuer, self, "COMPLETION")
        _cid(self.stage_completion_id, "stage completion")
        if type(self.total_event_count) is not int or self.total_event_count < 0:
            _fail("total event count must be nonnegative")
        _base_payload(
            schema="acfqp.construction_accounting_route_segment_completion.v2",
            route_segment_start_id=self.route_segment_start_id,
            chain_sequence=self.chain_sequence,
            predecessor_chain_id=self.predecessor_chain_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            **_base_payload(
                schema="acfqp.construction_accounting_route_segment_completion.v2",
                route_segment_start_id=self.route_segment_start_id,
                chain_sequence=self.chain_sequence,
                predecessor_chain_id=self.predecessor_chain_id,
            ),
            "stage_completion_id": self.stage_completion_id,
            "total_event_count": self.total_event_count,
            "terminal_kind": RouteSegmentTerminalKindV2.COMPLETED.value,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
        }

    @property
    def chain_id(self) -> str:
        return _content_id(_COMPLETION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_completion_id": self.chain_id}


@dataclass(frozen=True, slots=True)
class RouteSegmentAbortV2:
    _issuer: InitVar[object]
    route_segment_start_id: str
    reason: str
    active_stage: registry_v6.ConstructionStageKindV6 | None
    total_event_count: int
    chain_sequence: int
    predecessor_chain_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_session_node_issuance_v2(_issuer, self, "ABORT")
        object.__setattr__(self, "reason", _abort_reason(self.reason))
        if self.active_stage is not None:
            object.__setattr__(self, "active_stage", _stage(self.active_stage))
        if type(self.total_event_count) is not int or self.total_event_count < 0:
            _fail("abort event count must be nonnegative")
        _base_payload(
            schema="acfqp.construction_accounting_route_segment_abort.v2",
            route_segment_start_id=self.route_segment_start_id,
            chain_sequence=self.chain_sequence,
            predecessor_chain_id=self.predecessor_chain_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            **_base_payload(
                schema="acfqp.construction_accounting_route_segment_abort.v2",
                route_segment_start_id=self.route_segment_start_id,
                chain_sequence=self.chain_sequence,
                predecessor_chain_id=self.predecessor_chain_id,
            ),
            "reason": self.reason,
            "active_stage": (
                None if self.active_stage is None else self.active_stage.value
            ),
            "total_event_count": self.total_event_count,
            "terminal_kind": RouteSegmentTerminalKindV2.ABORTED.value,
            "positive_prefix_retained": True,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
        }

    @property
    def chain_id(self) -> str:
        return _content_id(_ABORT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_abort_id": self.chain_id}


RouteSegmentNodeV2 = (
    RouteSegmentStageStartV2
    | RouteSegmentOperationEventV2
    | RouteSegmentStageCompletionV2
    | RouteSegmentCompletionV2
    | RouteSegmentAbortV2
)


@dataclass(frozen=True, slots=True)
class RouteSegmentTranscriptV2:
    _issuer: InitVar[object]
    start: RouteSegmentStartV2
    nodes: tuple[RouteSegmentNodeV2, ...]
    _terminal_kind: RouteSegmentTerminalKindV2 = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _require_session_node_issuance_v2(_issuer, self, "TRANSCRIPT")
        if type(self.start) is not RouteSegmentStartV2 or not self.nodes:
            _fail("route-segment transcript lacks its exact start or nodes")
        predecessor = self.start.chain_id
        event_ids: list[str] = []
        stage_started = False
        stage_completed = False
        terminal_kind: RouteSegmentTerminalKindV2 | None = None
        for sequence, node in enumerate(self.nodes, start=1):
            if (
                getattr(node, "route_segment_start_id", None) != self.start.start_id
                or getattr(node, "chain_sequence", None) != sequence
                or getattr(node, "predecessor_chain_id", None) != predecessor
            ):
                _fail("route-segment transcript chain is discontinuous")
            if type(node) is RouteSegmentStageStartV2:
                if sequence != 1 or stage_started or node.stage_kind is not self.start.stage_kind:
                    _fail("route-segment stage start is misplaced")
                stage_started = True
            elif type(node) is RouteSegmentOperationEventV2:
                if not stage_started or stage_completed or node.stage_kind is not self.start.stage_kind:
                    _fail("operation event lies outside the active route stage")
                if node.stage_event_sequence != len(event_ids) + 1:
                    _fail("route-segment event sequence is discontinuous")
                event_ids.append(node.event_id)
            elif type(node) is RouteSegmentStageCompletionV2:
                if not stage_started or stage_completed or node.event_ids != tuple(event_ids):
                    _fail("route-segment stage completion changed event coverage")
                if node.stage_kind is not self.start.stage_kind:
                    _fail("route-segment stage completion changed stage")
                stage_completed = True
            elif type(node) is RouteSegmentCompletionV2:
                if (
                    not stage_completed
                    or sequence != len(self.nodes)
                    or node.total_event_count != len(event_ids)
                    or node.stage_completion_id != self.nodes[-2].chain_id
                ):
                    _fail("route-segment completion is premature or inconsistent")
                terminal_kind = RouteSegmentTerminalKindV2.COMPLETED
            elif type(node) is RouteSegmentAbortV2:
                if sequence != len(self.nodes) or node.total_event_count != len(event_ids):
                    _fail("route-segment abort is misplaced or changed event count")
                terminal_kind = RouteSegmentTerminalKindV2.ABORTED
            else:  # pragma: no cover - union guarded above
                _fail("route-segment transcript contains a foreign node")
            predecessor = node.chain_id
        if terminal_kind is None:
            _fail("route-segment transcript has no terminal node")
        object.__setattr__(self, "_terminal_kind", terminal_kind)

    @property
    def terminal_kind(self) -> RouteSegmentTerminalKindV2:
        return self._terminal_kind

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(
            node.event_id
            for node in self.nodes
            if type(node) is RouteSegmentOperationEventV2
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_route_segment_transcript.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_start": self.start.to_document(),
            "nodes": [node.to_document() for node in self.nodes],
            "terminal_kind": self.terminal_kind.value,
            "event_count": len(self.event_ids),
            "positive_prefix_retained": True,
            "absent_event_is_zero": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "python_api_spoof_resistance_only": True,
            "native_code_adversary_resistance_claimed": False,
            "central_domain_registration_pending": True,
            "production_closure_claimed": False,
        }

    @property
    def transcript_id(self) -> str:
        return _content_id(_TRANSCRIPT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_transcript_id": self.transcript_id}


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
        raise ConstructionAccountingRouteSegmentV2Error(
            "operation owner code is unavailable"
        ) from error
    return module.__dict__, code


class RouteSegmentAccountingSessionV2:
    """Thread-owned positive-event recorder for one exact V6 route stage."""

    def __init__(
        self,
        *,
        route_segment_id: str,
        occurrence_id: str,
        route_attempt_id: str,
        recorder_id: str,
        stage_kind: registry_v6.ConstructionStageKindV6,
        boundary_manifest: Any,
    ) -> None:
        self._lock = threading.RLock()
        self._owner_thread_id = threading.get_ident()
        self._registry = registry_v6.official_counter_registry_v6()
        self._stage_profile = registry_v6.official_stage_profile_v6(self._registry)
        self._boundary_manifest = boundary_manifest
        self._stage_kind = _stage(stage_kind)
        self._validate_binding()
        self._gateway_binding = (
            _FROZEN_OPERATION_GATEWAY_V2,
            _FROZEN_OPERATION_GATEWAY_V2.__globals__,
            _FROZEN_OPERATION_GATEWAY_V2.__code__,
        )
        self._start = RouteSegmentStartV2(
            _NODE_ISSUER,
            _cid(route_segment_id, "route segment"),
            _cid(occurrence_id, "occurrence"),
            _cid(route_attempt_id, "route attempt"),
            self._registry.registry_id,
            self._stage_profile.stage_profile_id,
            self.boundary_manifest_id,
            recorder_id,
            self._stage_kind,
        )
        self._nodes: list[RouteSegmentNodeV2] = []
        self._active_stage = False
        self._stage_completed = False
        self._event_count = 0
        self._terminal = False

    def _validate_binding(self) -> None:
        from acfqp import (
            construction_k7_direct_fallback_operation_boundary_manifest_v2
            as direct_manifest_v2,
        )

        self._registry.validate_official_catalogue()
        self._stage_profile.validate(self._registry)
        if type(self._boundary_manifest) is not (
            direct_manifest_v2.DirectFallbackOperationBoundaryManifestV2
        ):
            _fail("route-segment binding requires the exact direct-fallback manifest")
        replay = direct_manifest_v2.replay_direct_fallback_operation_source_archive_v2(
            direct_manifest_v2.load_direct_fallback_operation_source_archive_v2()
        )
        if (
            replay.outcome
            is not direct_manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.VERIFIED
            or replay.manifest is None
            or canonical_json_bytes(replay.manifest.to_document())
            != canonical_json_bytes(self._boundary_manifest.to_document())
        ):
            _fail("route-segment manifest differs from independent source replay")
        manifest_id = self._boundary_manifest.boundary_manifest_id
        if (
            _cid(
                getattr(self._boundary_manifest, "counter_registry_id", None),
                "manifest counter registry",
            )
            != self._registry.registry_id
            or _cid(
                getattr(self._boundary_manifest, "stage_profile_id", None),
                "manifest stage profile",
            )
            != self._stage_profile.stage_profile_id
            or _stage(getattr(self._boundary_manifest, "stage_kind", None))
            is not self._stage_kind
        ):
            _fail("route-segment manifest crossed registry, stage, or profile")
        by_dispatch = self._boundary_manifest.by_dispatch
        allowed = set(
            self._stage_profile.by_stage[self._stage_kind].allowed_nonzero_paths
        )
        owner_bindings: dict[str, tuple[Any, Any]] = {}
        for dispatch_key, boundary in by_dispatch.items():
            if (
                dispatch_key != getattr(boundary, "dispatch_key", None)
                or type(dispatch_key) is not str
                or _DISPATCH_KEY.fullmatch(dispatch_key) is None
                or _stage(getattr(boundary, "stage_kind", None)) is not self._stage_kind
            ):
                _fail("route-segment dispatch binding is malformed")
            path = getattr(boundary, "target_path", None)
            leaf = self._registry.by_path.get(path)
            if leaf is None or path not in allowed:
                _fail("route-segment boundary targets an unowned stage path")
            try:
                reducer = ReducerEnum(getattr(boundary, "reducer", None))
            except (TypeError, ValueError) as error:
                raise ConstructionAccountingRouteSegmentV2Error(
                    "route-segment boundary reducer is invalid"
                ) from error
            if reducer is not ReducerEnum.SUM or reducer is not leaf.reducer:
                _fail("route-segment boundary reducer differs from V6 registry")
            owner_bindings[dispatch_key] = _resolve_owner(
                getattr(boundary, "operation_source_module", None),
                getattr(boundary, "operation_source_symbol", None),
            )
        self.boundary_manifest_id = manifest_id
        self._by_dispatch = MappingProxyType(dict(by_dispatch))
        self._owner_bindings = MappingProxyType(owner_bindings)

    def _revalidate_live_bindings(self) -> None:
        current_gateway = globals().get("emit_route_segment_operation_v2")
        expected_gateway, expected_globals, expected_code = self._gateway_binding
        if (
            current_gateway is not expected_gateway
            or getattr(current_gateway, "__globals__", None) is not expected_globals
            or getattr(current_gateway, "__code__", None) is not expected_code
        ):
            self._violation(
                "LIVE_GATEWAY_BINDING_CHANGED",
                "route-segment operation gateway changed after session binding",
            )
        for dispatch_key, boundary in self._by_dispatch.items():
            try:
                current_globals, current_code = _resolve_owner(
                    getattr(boundary, "operation_source_module", None),
                    getattr(boundary, "operation_source_symbol", None),
                )
            except ConstructionAccountingRouteSegmentV2Error:
                self._violation(
                    "LIVE_OWNER_BINDING_CHANGED",
                    "route-segment source owner was removed or made noncallable",
                )
            expected_owner_globals, expected_owner_code = self._owner_bindings[
                dispatch_key
            ]
            if (
                current_globals is not expected_owner_globals
                or current_code is not expected_owner_code
            ):
                self._violation(
                    "LIVE_OWNER_BINDING_CHANGED",
                    "route-segment source owner changed after session binding",
                )

    @property
    def start(self) -> RouteSegmentStartV2:
        return self._start

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def transcript(self) -> RouteSegmentTranscriptV2:
        if not self._terminal:
            _fail("route-segment transcript is unavailable before terminalization")
        return RouteSegmentTranscriptV2(
            _NODE_ISSUER, self._start, tuple(self._nodes)
        )

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            self._protocol_abort("CROSS_THREAD_ACTIVE_SCOPE")
            _fail("route-segment accounting crossed its owner thread")

    def _next_predecessor(self) -> str:
        return self._nodes[-1].chain_id if self._nodes else self._start.chain_id

    def _append(self, node: RouteSegmentNodeV2) -> None:
        self._nodes.append(node)

    def _protocol_abort(self, reason: str) -> None:
        with self._lock:
            if self._terminal:
                return
            reason = _abort_reason(reason)
            self._append(
                RouteSegmentAbortV2(
                    _NODE_ISSUER,
                    self._start.start_id,
                    reason,
                    self._stage_kind if self._active_stage else None,
                    self._event_count,
                    len(self._nodes) + 1,
                    self._next_predecessor(),
                )
            )
            self._active_stage = False
            self._terminal = True

    def _violation(self, reason: str, message: str) -> NoReturn:
        self._protocol_abort(reason)
        raise ConstructionAccountingRouteSegmentV2Error(message)

    def enter_stage(self, stage_kind: Any) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal:
                _fail("route-segment session is already terminal")
            self._revalidate_live_bindings()
            stage = _stage(stage_kind)
            if stage is not self._stage_kind:
                self._violation("WRONG_ROUTE_STAGE", "entered another V6 route stage")
            if self._active_stage or self._stage_completed or self._nodes:
                self._violation("DUPLICATE_STAGE_START", "route stage entered twice")
            self._append(
                RouteSegmentStageStartV2(
                    _NODE_ISSUER,
                    self._start.start_id,
                    stage,
                    1,
                    self._start.chain_id,
                )
            )
            self._active_stage = True

    def emit_operation(self) -> NoReturn:
        """Reject direct session emission; only the frozen gateway can issue."""

        with self._lock:
            self._check_thread()
            if self._terminal:
                _fail("route-segment session is already terminal")
            self._violation(
                "DIRECT_SESSION_EMISSION_FORBIDDEN",
                "route operations must enter through the frozen gateway",
            )

    def _emit_from_gateway(
        self,
        _issuer: object,
        dispatch_key: Any,
        amount: Any = 1,
        *,
        owner_module: Any,
        owner_globals: Any,
        owner_code: Any,
    ) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal:
                _fail("route-segment session is already terminal")
            try:
                gateway_frame = _FROZEN_GETFRAME_V2(1)
            except (AttributeError, ValueError):  # pragma: no cover
                self._violation(
                    "GATEWAY_CALLER_FRAME_UNAVAILABLE",
                    "route-segment gateway caller frame is unavailable",
                )
            expected_gateway, expected_globals, expected_code = self._gateway_binding
            if (
                _issuer is not _GATEWAY_ISSUER
                or gateway_frame.f_globals is not expected_globals
                or gateway_frame.f_code is not expected_code
                or globals().get("emit_route_segment_operation_v2")
                is not expected_gateway
            ):
                self._violation(
                    "UNTRUSTED_GATEWAY_CALLER",
                    "route operation was not issued by the immediate frozen gateway",
                )
            if not self._active_stage:
                self._violation(
                    "EVENT_OUTSIDE_ACTIVE_STAGE",
                    "owned route operation has no active stage",
                )
            if (
                type(dispatch_key) is not str
                or _DISPATCH_KEY.fullmatch(dispatch_key) is None
            ):
                self._violation(
                    "MALFORMED_DISPATCH_KEY", "operation dispatch is noncanonical"
                )
            if type(amount) is not int or amount != 1:
                self._violation(
                    "PRODUCTION_AMOUNT_NOT_UNIT",
                    "each operation event must represent one primitive",
                )
            boundary = self._by_dispatch.get(dispatch_key)
            if boundary is None:
                self._violation(
                    "UNKNOWN_STAGE_DISPATCH",
                    "dispatch key has no boundary in this route stage",
                )
            expected_globals, expected_code = self._owner_bindings[dispatch_key]
            if (
                type(owner_module) is not str
                or owner_module
                != getattr(boundary, "operation_source_module", None)
                or owner_globals is not expected_globals
                or owner_code is not expected_code
            ):
                self._violation(
                    "OPERATION_OWNER_MISMATCH",
                    "dispatch caller differs from the frozen source owner",
                )
            event = RouteSegmentOperationEventV2(
                _NODE_ISSUER,
                self._start.start_id,
                self._stage_kind,
                _cid(getattr(boundary, "boundary_id", None), "boundary"),
                dispatch_key,
                getattr(boundary, "target_path"),
                getattr(boundary, "reducer"),
                amount,
                self._event_count + 1,
                len(self._nodes) + 1,
                self._next_predecessor(),
            )
            self._append(event)
            self._event_count += 1

    def exit_stage(self, stage_kind: Any | None = None) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal:
                _fail("route-segment session is already terminal")
            self._revalidate_live_bindings()
            if not self._active_stage:
                self._violation("STAGE_EXIT_WITHOUT_START", "no route stage is active")
            if stage_kind is not None and _stage(stage_kind) is not self._stage_kind:
                self._violation("STAGE_EXIT_MISMATCH", "exited another route stage")
            event_ids = tuple(
                node.event_id
                for node in self._nodes
                if type(node) is RouteSegmentOperationEventV2
            )
            self._append(
                RouteSegmentStageCompletionV2(
                    _NODE_ISSUER,
                    self._start.start_id,
                    self._stage_kind,
                    event_ids,
                    len(self._nodes) + 1,
                    self._next_predecessor(),
                )
            )
            self._active_stage = False
            self._stage_completed = True

    def complete(self) -> RouteSegmentTranscriptV2:
        with self._lock:
            self._check_thread()
            if self._terminal:
                _fail("route-segment session is already terminal")
            self._revalidate_live_bindings()
            if self._active_stage or not self._stage_completed:
                self._violation(
                    "INCOMPLETE_ROUTE_SEGMENT",
                    "route segment cannot complete before its exact stage",
                )
            stage_completion = self._nodes[-1]
            if type(stage_completion) is not RouteSegmentStageCompletionV2:
                self._violation(
                    "INVALID_COMPLETION_PREDECESSOR",
                    "route completion must follow stage completion",
                )
            self._append(
                RouteSegmentCompletionV2(
                    _NODE_ISSUER,
                    self._start.start_id,
                    stage_completion.chain_id,
                    self._event_count,
                    len(self._nodes) + 1,
                    self._next_predecessor(),
                )
            )
            self._terminal = True
            return self.transcript

    def abort(self, reason: str = "CALLER_REQUESTED_ABORT") -> RouteSegmentTranscriptV2:
        self._check_thread()
        self._protocol_abort(reason)
        return self.transcript


_FROZEN_NODE_ISSUER_GLOBALS_V2 = globals()
_FROZEN_NODE_ISSUER_CODES_V2 = MappingProxyType(
    {
        "START": RouteSegmentAccountingSessionV2.__init__.__code__,
        "STAGE_START": RouteSegmentAccountingSessionV2.enter_stage.__code__,
        "EVENT": RouteSegmentAccountingSessionV2._emit_from_gateway.__code__,
        "STAGE_COMPLETION": RouteSegmentAccountingSessionV2.exit_stage.__code__,
        "COMPLETION": RouteSegmentAccountingSessionV2.complete.__code__,
        "ABORT": RouteSegmentAccountingSessionV2._protocol_abort.__code__,
        "TRANSCRIPT": RouteSegmentAccountingSessionV2.transcript.fget.__code__,
    }
)


_ACTIVE_ROUTE_SEGMENT_RUNTIME: ContextVar[
    RouteSegmentAccountingSessionV2 | None
] = ContextVar("acfqp_route_segment_accounting_runtime_v2", default=None)


@contextmanager
def activate_route_segment_accounting_v2(
    session: RouteSegmentAccountingSessionV2,
) -> Iterator[RouteSegmentAccountingSessionV2]:
    """Activate one issuer-owned route segment; nested activation fails closed."""

    if type(session) is not RouteSegmentAccountingSessionV2:
        _fail("route-segment activation requires the exact V2 session type")
    session._check_thread()
    session._revalidate_live_bindings()
    active = _ACTIVE_ROUTE_SEGMENT_RUNTIME.get()
    if active is not None:
        active._protocol_abort("NESTED_ACTIVE_SCOPE")
        _fail("nested route-segment accounting scopes are forbidden")
    if session.is_terminal:
        _fail("terminal route-segment session cannot be reactivated")
    token: Token[Any] = _ACTIVE_ROUTE_SEGMENT_RUNTIME.set(session)
    try:
        yield session
    except BaseException as error:
        if not session.is_terminal:
            session._protocol_abort("ACTIVE_SCOPE_EXCEPTION")
        raise
    else:
        if not session.is_terminal:
            session._protocol_abort("INCOMPLETE_SCOPE_EXIT")
            _fail("active route-segment scope exited without terminalization")
    finally:
        _ACTIVE_ROUTE_SEGMENT_RUNTIME.reset(token)


def emit_route_segment_operation_v2(dispatch_key: Any, amount: Any = 1) -> None:
    """Emit from a frozen owner site, or remain an exact no-op when inactive."""

    session = _ACTIVE_ROUTE_SEGMENT_RUNTIME.get()
    if session is None:
        return
    try:
        caller = _FROZEN_GETFRAME_V2(1)
    except (AttributeError, ValueError) as error:  # pragma: no cover
        session._protocol_abort("CALLER_FRAME_UNAVAILABLE")
        raise ConstructionAccountingRouteSegmentV2Error(
            "route-segment operation caller frame is unavailable"
        ) from error
    session._emit_from_gateway(
        _GATEWAY_ISSUER,
        dispatch_key,
        amount,
        owner_module=caller.f_globals.get("__name__"),
        owner_globals=caller.f_globals,
        owner_code=caller.f_code,
    )


_FROZEN_OPERATION_GATEWAY_V2 = emit_route_segment_operation_v2


def enter_route_segment_stage_v2(stage_kind: Any) -> None:
    session = _ACTIVE_ROUTE_SEGMENT_RUNTIME.get()
    if session is not None:
        session.enter_stage(stage_kind)


def exit_route_segment_stage_v2(stage_kind: Any | None = None) -> None:
    session = _ACTIVE_ROUTE_SEGMENT_RUNTIME.get()
    if session is not None:
        session.exit_stage(stage_kind)


def complete_route_segment_v2() -> RouteSegmentTranscriptV2 | None:
    session = _ACTIVE_ROUTE_SEGMENT_RUNTIME.get()
    return None if session is None else session.complete()


class DirectFallbackOwnedOperationSourceV2:
    """Future/test-only owner sites; not a production fallback implementation."""

    @staticmethod
    def cap_check_v2() -> None:
        emit_route_segment_operation_v2("direct-fallback.control.cap-check", 1)

    @staticmethod
    def cap_rejection_v2() -> None:
        emit_route_segment_operation_v2(
            "direct-fallback.control.cap-rejection", 1
        )

    @staticmethod
    def state_expanded_v2() -> None:
        emit_route_segment_operation_v2("direct-fallback.state.expanded", 1)

    @staticmethod
    def action_evaluated_v2() -> None:
        emit_route_segment_operation_v2("direct-fallback.action.evaluated", 1)

    @staticmethod
    def ground_step_v2() -> None:
        emit_route_segment_operation_v2("direct-fallback.kernel.transition", 1)

    @staticmethod
    def outcome_row_v2() -> None:
        emit_route_segment_operation_v2("direct-fallback.outcome.row", 1)

    @staticmethod
    def bellman_backup_v2() -> None:
        emit_route_segment_operation_v2("direct-fallback.bellman.backup", 1)


__all__ = (
    "CENTRAL_DOMAIN_REGISTRATION_PENDING",
    "COVERAGE_STATE",
    "ConstructionAccountingRouteSegmentV2Error",
    "DirectFallbackOwnedOperationSourceV2",
    "PRODUCTION_CLOSURE_CLAIMED",
    "PROFILE_KEY",
    "RouteSegmentAbortV2",
    "RouteSegmentAccountingSessionV2",
    "RouteSegmentCompletionV2",
    "RouteSegmentOperationEventV2",
    "RouteSegmentStageCompletionV2",
    "RouteSegmentStageStartV2",
    "RouteSegmentStartV2",
    "RouteSegmentTerminalKindV2",
    "RouteSegmentTranscriptV2",
    "SCHEMA_VERSION",
    "activate_route_segment_accounting_v2",
    "complete_route_segment_v2",
    "emit_route_segment_operation_v2",
    "enter_route_segment_stage_v2",
    "exit_route_segment_stage_v2",
)
