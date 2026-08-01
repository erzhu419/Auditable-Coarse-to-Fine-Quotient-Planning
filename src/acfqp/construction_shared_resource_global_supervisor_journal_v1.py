"""Structural global-supervisor lifecycle journal for shared resources.

This module supplies an issuer-owned, globally ordered event boundary without
joining it to a route, an outer-finalization result, or an operating-system
authority.  Callers submit exact typed source documents; the journal assigns
the only accepted sequence numbers internally and embeds every source
document in the resulting content-addressed transcript.

The implementation proves only schema, identity, ordering, and hash-chain
structure.  It does not prove that a process was really reaped, that a
descendant scan or cgroup read was performed, or that the typed documents came
from a trusted supervisor.  Consequently every semantic/formal issuance lock
remains false.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import re
from typing import Any, ClassVar, Mapping

from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_SCOPE_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_SOURCE_DOCUMENT_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.93.0"
PROFILE_KEY = "construction_shared_resource_global_supervisor_journal_v1"

GLOBAL_SUPERVISOR_SCOPE_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_SCOPE_V1_DOMAIN
)
GLOBAL_SUPERVISOR_SOURCE_DOCUMENT_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_SOURCE_DOCUMENT_V1_DOMAIN
)
GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN
)
GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    GLOBAL_SUPERVISOR_SCOPE_V1_DOMAIN,
    GLOBAL_SUPERVISOR_SOURCE_DOCUMENT_V1_DOMAIN,
    GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN,
    GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN,
)
LOCAL_DOMAIN_TAGS = frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS)

OS_SOURCE_PROVENANCE_VERIFIED = False
GLOBAL_SEQUENCE_MAPPED_TO_OS_ORDER_VERIFIED = False
COUNTER_RECORD_AUTHORIZED = False
WORK_VECTOR_AUTHORIZED = False
COMPARISON_VECTOR_AUTHORIZED = False
ACTUAL_PROJECTION_PROOF_AUTHORIZED = False
OFFICIAL_EXECUTION_ALLOWED = False

_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9._:/-]{0,255}$")
_TERMINAL_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ConstructionSharedResourceGlobalSupervisorJournalV1Error(ValueError):
    """The typed source, journal state, or internal sequence is invalid."""


class GlobalSupervisorEventKindV1(str, Enum):
    WINDOW_START = "WINDOW_START"
    BUSINESS_CUTOFF = "BUSINESS_CUTOFF"
    PROCESS_REAP = "PROCESS_REAP"
    DESCENDANT_SCAN = "DESCENDANT_SCAN"
    FINAL_CGROUP_PEAK = "FINAL_CGROUP_PEAK"
    PARENT_TERMINAL = "PARENT_TERMINAL"


EVENT_ORDER = (
    GlobalSupervisorEventKindV1.WINDOW_START,
    GlobalSupervisorEventKindV1.BUSINESS_CUTOFF,
    GlobalSupervisorEventKindV1.PROCESS_REAP,
    GlobalSupervisorEventKindV1.DESCENDANT_SCAN,
    GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK,
    GlobalSupervisorEventKindV1.PARENT_TERMINAL,
)


class GlobalSupervisorJournalStateV1(str, Enum):
    WINDOW_STARTED = "WINDOW_STARTED"
    BUSINESS_CUTOFF_RECORDED = "BUSINESS_CUTOFF_RECORDED"
    PROCESS_REAP_RECORDED = "PROCESS_REAP_RECORDED"
    DESCENDANT_SCAN_RECORDED = "DESCENDANT_SCAN_RECORDED"
    FINAL_CGROUP_PEAK_RECORDED = "FINAL_CGROUP_PEAK_RECORDED"
    PARENT_TERMINAL_RECORDED = "PARENT_TERMINAL_RECORDED"
    FROZEN = "FROZEN"


_PREFIX_STATES = (
    GlobalSupervisorJournalStateV1.WINDOW_STARTED,
    GlobalSupervisorJournalStateV1.BUSINESS_CUTOFF_RECORDED,
    GlobalSupervisorJournalStateV1.PROCESS_REAP_RECORDED,
    GlobalSupervisorJournalStateV1.DESCENDANT_SCAN_RECORDED,
    GlobalSupervisorJournalStateV1.FINAL_CGROUP_PEAK_RECORDED,
    GlobalSupervisorJournalStateV1.PARENT_TERMINAL_RECORDED,
)


class BusinessCutoffClaimV1(str, Enum):
    BUSINESS_PAYLOAD_COMPLETE = "BUSINESS_PAYLOAD_COMPLETE"
    BUSINESS_PAYLOAD_ABORTED = "BUSINESS_PAYLOAD_ABORTED"


class ParentTerminalClaimV1(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"


def _fail(message: str) -> None:
    raise ConstructionSharedResourceGlobalSupervisorJournalV1Error(message)


def _content_id(domain_tag: str, payload: Mapping[str, Any]) -> str:
    if domain_tag not in LOCAL_DOMAIN_TAGS:
        _fail("global-supervisor journal used an undeclared content domain")
    return content_id(domain_tag, dict(payload))


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionSharedResourceGlobalSupervisorJournalV1Error(
            f"{field_name} must be one full content ID"
        ) from error


def _key(value: Any, field_name: str) -> str:
    if type(value) is not str or _KEY.fullmatch(value) is None:
        _fail(f"{field_name} must be one canonical nonempty key")
    return value


def _exact_int(value: Any, field_name: str) -> int:
    if type(value) is not int:
        _fail(f"{field_name} must be an exact integer")
    return value


def _nonnegative(value: Any, field_name: str) -> int:
    value = _exact_int(value, field_name)
    if value < 0:
        _fail(f"{field_name} must be nonnegative")
    return value


def _exact_true(value: Any, field_name: str) -> None:
    if type(value) is not bool or value is not True:
        _fail(f"{field_name} must be exact true")


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceGlobalSupervisorJournalV1Error(
            f"unknown {field_name} {value!r}"
        ) from error


def _formal_locks() -> dict[str, bool]:
    return {
        "os_source_provenance_verified": OS_SOURCE_PROVENANCE_VERIFIED,
        "global_sequence_mapped_to_os_order_verified": (
            GLOBAL_SEQUENCE_MAPPED_TO_OS_ORDER_VERIFIED
        ),
        "counter_record_authorized": COUNTER_RECORD_AUTHORIZED,
        "work_vector_authorized": WORK_VECTOR_AUTHORIZED,
        "comparison_vector_authorized": COMPARISON_VECTOR_AUTHORIZED,
        "actual_projection_proof_authorized": (
            ACTUAL_PROJECTION_PROOF_AUTHORIZED
        ),
        "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
    }


@dataclass(frozen=True, slots=True)
class GlobalSupervisorScopeV1:
    """Typed identity shared by every source document in one journal."""

    measurement_identity_binding_id: str
    execution_profile_id: str
    window_key: str
    supervision_scope_key: str
    _scope_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _cid(
            self.measurement_identity_binding_id,
            "scope measurement identity binding",
        )
        _cid(self.execution_profile_id, "scope execution profile")
        _key(self.window_key, "scope window key")
        _key(self.supervision_scope_key, "scope supervision key")
        if self.window_key == self.supervision_scope_key:
            _fail("window and supervision scope keys must be role-distinct")
        object.__setattr__(
            self,
            "_scope_id",
            _content_id(GLOBAL_SUPERVISOR_SCOPE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_global_supervisor_scope.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "measurement_identity_binding_id": (
                self.measurement_identity_binding_id
            ),
            "execution_profile_id": self.execution_profile_id,
            "window_key": self.window_key,
            "supervision_scope_key": self.supervision_scope_key,
            "route_identity_joined": False,
            "supervisor_os_authority_bound": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def scope_id(self) -> str:
        current = _content_id(GLOBAL_SUPERVISOR_SCOPE_V1_DOMAIN, self._payload())
        if current != self._scope_id:
            _fail("global-supervisor scope changed after issuance")
        return self._scope_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "global_supervisor_scope_id": self.scope_id}


class _SourceDocumentV1:
    __slots__ = ()

    EVENT_KIND: ClassVar[GlobalSupervisorEventKindV1]
    scope: GlobalSupervisorScopeV1

    def _specific_payload(self) -> dict[str, Any]:
        raise NotImplementedError

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_global_supervisor_source_document.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "event_kind": self.EVENT_KIND.value,
            "scope": self.scope.to_document(),
            "typed_claim": self._specific_payload(),
            "caller_supplied_global_sequence": False,
            "structural_source_claim_only": True,
            "source_bytes_independently_replayed": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def source_document_id(self) -> str:
        return _content_id(
            GLOBAL_SUPERVISOR_SOURCE_DOCUMENT_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_document_id": self.source_document_id}


def _scope(value: Any) -> GlobalSupervisorScopeV1:
    if type(value) is not GlobalSupervisorScopeV1:
        _fail("source document requires one exact typed supervisor scope")
    return value


@dataclass(frozen=True, slots=True)
class WindowStartSourceDocumentV1(_SourceDocumentV1):
    EVENT_KIND: ClassVar[GlobalSupervisorEventKindV1] = (
        GlobalSupervisorEventKindV1.WINDOW_START
    )
    scope: GlobalSupervisorScopeV1
    monitor_registration_key: str

    def __post_init__(self) -> None:
        _scope(self.scope)
        _key(self.monitor_registration_key, "monitor registration key")

    def _specific_payload(self) -> dict[str, Any]:
        return {
            "monitor_registration_key": self.monitor_registration_key,
            "window_start_claimed": True,
        }


@dataclass(frozen=True, slots=True)
class BusinessCutoffSourceDocumentV1(_SourceDocumentV1):
    EVENT_KIND: ClassVar[GlobalSupervisorEventKindV1] = (
        GlobalSupervisorEventKindV1.BUSINESS_CUTOFF
    )
    scope: GlobalSupervisorScopeV1
    cutoff_claim: BusinessCutoffClaimV1
    business_frame_key: str
    cutoff_complete: bool

    def __post_init__(self) -> None:
        _scope(self.scope)
        object.__setattr__(
            self,
            "cutoff_claim",
            _enum(BusinessCutoffClaimV1, self.cutoff_claim, "cutoff claim"),
        )
        _key(self.business_frame_key, "business frame key")
        _exact_true(self.cutoff_complete, "cutoff_complete")

    def _specific_payload(self) -> dict[str, Any]:
        return {
            "cutoff_claim": self.cutoff_claim.value,
            "business_frame_key": self.business_frame_key,
            "cutoff_complete_claimed": self.cutoff_complete,
        }


@dataclass(frozen=True, slots=True)
class ProcessReapSourceDocumentV1(_SourceDocumentV1):
    EVENT_KIND: ClassVar[GlobalSupervisorEventKindV1] = (
        GlobalSupervisorEventKindV1.PROCESS_REAP
    )
    scope: GlobalSupervisorScopeV1
    process_handle_key: str
    wait_status: int
    reap_complete: bool

    def __post_init__(self) -> None:
        _scope(self.scope)
        _key(self.process_handle_key, "process handle key")
        _exact_int(self.wait_status, "wait status")
        _exact_true(self.reap_complete, "reap_complete")

    def _specific_payload(self) -> dict[str, Any]:
        return {
            "process_handle_key": self.process_handle_key,
            "wait_status": self.wait_status,
            "process_reap_claimed_complete": self.reap_complete,
        }


@dataclass(frozen=True, slots=True)
class DescendantScanSourceDocumentV1(_SourceDocumentV1):
    EVENT_KIND: ClassVar[GlobalSupervisorEventKindV1] = (
        GlobalSupervisorEventKindV1.DESCENDANT_SCAN
    )
    scope: GlobalSupervisorScopeV1
    process_handle_key: str
    descendant_count: int
    scan_complete: bool

    def __post_init__(self) -> None:
        _scope(self.scope)
        _key(self.process_handle_key, "process handle key")
        if _nonnegative(self.descendant_count, "descendant count") != 0:
            _fail("terminal descendant scan must claim exactly zero descendants")
        _exact_true(self.scan_complete, "scan_complete")

    def _specific_payload(self) -> dict[str, Any]:
        return {
            "process_handle_key": self.process_handle_key,
            "descendant_count": self.descendant_count,
            "descendant_scan_claimed_complete": self.scan_complete,
        }


@dataclass(frozen=True, slots=True)
class FinalCgroupPeakSourceDocumentV1(_SourceDocumentV1):
    EVENT_KIND: ClassVar[GlobalSupervisorEventKindV1] = (
        GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK
    )
    scope: GlobalSupervisorScopeV1
    cgroup_scope_key: str
    working_bytes_peak: int
    peak_read_complete: bool

    def __post_init__(self) -> None:
        _scope(self.scope)
        _key(self.cgroup_scope_key, "cgroup scope key")
        _nonnegative(self.working_bytes_peak, "working bytes peak")
        _exact_true(self.peak_read_complete, "peak_read_complete")

    def _specific_payload(self) -> dict[str, Any]:
        return {
            "cgroup_scope_key": self.cgroup_scope_key,
            "working_bytes_peak": self.working_bytes_peak,
            "final_cgroup_peak_read_claimed_complete": self.peak_read_complete,
        }


@dataclass(frozen=True, slots=True)
class ParentTerminalSourceDocumentV1(_SourceDocumentV1):
    EVENT_KIND: ClassVar[GlobalSupervisorEventKindV1] = (
        GlobalSupervisorEventKindV1.PARENT_TERMINAL
    )
    scope: GlobalSupervisorScopeV1
    terminal_claim: ParentTerminalClaimV1
    terminal_code: str
    terminal_complete: bool

    def __post_init__(self) -> None:
        _scope(self.scope)
        object.__setattr__(
            self,
            "terminal_claim",
            _enum(
                ParentTerminalClaimV1,
                self.terminal_claim,
                "parent terminal claim",
            ),
        )
        if (
            type(self.terminal_code) is not str
            or _TERMINAL_CODE.fullmatch(self.terminal_code) is None
        ):
            _fail("terminal code must be one canonical public code")
        _exact_true(self.terminal_complete, "terminal_complete")

    def _specific_payload(self) -> dict[str, Any]:
        return {
            "terminal_claim": self.terminal_claim.value,
            "terminal_code": self.terminal_code,
            "parent_terminal_claimed_complete": self.terminal_complete,
        }


GlobalSupervisorSourceDocumentV1 = (
    WindowStartSourceDocumentV1
    | BusinessCutoffSourceDocumentV1
    | ProcessReapSourceDocumentV1
    | DescendantScanSourceDocumentV1
    | FinalCgroupPeakSourceDocumentV1
    | ParentTerminalSourceDocumentV1
)

_SOURCE_TYPE_BY_KIND: dict[GlobalSupervisorEventKindV1, type[_SourceDocumentV1]] = {
    GlobalSupervisorEventKindV1.WINDOW_START: WindowStartSourceDocumentV1,
    GlobalSupervisorEventKindV1.BUSINESS_CUTOFF: (
        BusinessCutoffSourceDocumentV1
    ),
    GlobalSupervisorEventKindV1.PROCESS_REAP: ProcessReapSourceDocumentV1,
    GlobalSupervisorEventKindV1.DESCENDANT_SCAN: (
        DescendantScanSourceDocumentV1
    ),
    GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK: (
        FinalCgroupPeakSourceDocumentV1
    ),
    GlobalSupervisorEventKindV1.PARENT_TERMINAL: (
        ParentTerminalSourceDocumentV1
    ),
}


_EVENT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GlobalSupervisorEventV1:
    _issuer: InitVar[object]
    scope_id: str
    sequence: int
    kind: GlobalSupervisorEventKindV1
    prior_event_id: str | None
    source_document: GlobalSupervisorSourceDocumentV1
    _event_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EVENT_ISSUER:
            _fail("global-supervisor events are journal-issued only")
        _cid(self.scope_id, "event scope")
        if _exact_int(self.sequence, "event sequence") <= 0:
            _fail("event sequence must be positive")
        kind = _enum(GlobalSupervisorEventKindV1, self.kind, "event kind")
        object.__setattr__(self, "kind", kind)
        if self.sequence == 1:
            if self.prior_event_id is not None:
                _fail("first event cannot have a prior event ID")
        else:
            _cid(self.prior_event_id, "prior event")
        expected_type = _SOURCE_TYPE_BY_KIND[kind]
        if type(self.source_document) is not expected_type:
            _fail("event kind requires its exact typed source document")
        if self.source_document.scope.scope_id != self.scope_id:
            _fail("event source document crossed the journal scope")
        object.__setattr__(
            self,
            "_event_id",
            _content_id(GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_global_supervisor_event.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "global_supervisor_scope_id": self.scope_id,
            "sequence": self.sequence,
            "event_kind": self.kind.value,
            "prior_event_id": self.prior_event_id,
            "source_document_id": self.source_document.source_document_id,
            "source_document": self.source_document.to_document(),
            "sequence_assigned_internally": True,
            "caller_sequence_accepted": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def event_id(self) -> str:
        current = _content_id(GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN, self._payload())
        if current != self._event_id:
            _fail("global-supervisor event changed after issuance")
        return self._event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "global_supervisor_event_id": self.event_id}


_JOURNAL_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FrozenGlobalSupervisorEventJournalV1:
    _issuer: InitVar[object]
    scope: GlobalSupervisorScopeV1
    events: tuple[GlobalSupervisorEventV1, ...]
    _journal_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _JOURNAL_ISSUER:
            _fail("frozen global-supervisor journals are issuer-owned only")
        if type(self.scope) is not GlobalSupervisorScopeV1:
            _fail("frozen journal requires one exact typed scope")
        if type(self.events) is not tuple or len(self.events) != len(EVENT_ORDER):
            _fail("frozen journal requires the complete six-event lifecycle")
        prior: str | None = None
        source_ids: list[str] = []
        for sequence, (event, expected_kind) in enumerate(
            zip(self.events, EVENT_ORDER, strict=True),
            start=1,
        ):
            if type(event) is not GlobalSupervisorEventV1:
                _fail("frozen journal entries must be exact issued events")
            if (
                event.sequence != sequence
                or event.kind is not expected_kind
                or event.prior_event_id != prior
                or event.scope_id != self.scope.scope_id
                or event.source_document.scope != self.scope
            ):
                _fail("frozen journal lifecycle, sequence, or hash chain changed")
            source_ids.append(event.source_document.source_document_id)
            prior = event.event_id
        if len(set(source_ids)) != len(source_ids):
            _fail("each lifecycle role requires a distinct typed source document")
        reap = self.events[2].source_document
        scan = self.events[3].source_document
        assert type(reap) is ProcessReapSourceDocumentV1
        assert type(scan) is DescendantScanSourceDocumentV1
        if reap.process_handle_key != scan.process_handle_key:
            _fail("descendant scan crossed the reaped process handle")
        object.__setattr__(
            self,
            "_journal_id",
            _content_id(
                GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_global_supervisor_event_journal.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.to_document(),
            "event_count": len(self.events),
            "events": [event.to_document() for event in self.events],
            "head_event_id": self.events[-1].event_id,
            "global_sequence_origin": 1,
            "global_sequence_contiguous": True,
            "strict_lifecycle_structure_replayed": True,
            "typed_source_documents_embedded": True,
            "opaque_source_ids_accepted_without_documents": False,
            "journal_issuer_owned": True,
            "os_event_semantics_independently_replayed": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def journal_id(self) -> str:
        current = _content_id(
            GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN,
            self._payload(),
        )
        if current != self._journal_id:
            _fail("global-supervisor journal changed after freeze")
        return self._journal_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "global_supervisor_event_journal_id": self.journal_id,
        }


class GlobalSupervisorEventJournalSessionV1:
    """Mutable issuer boundary; only this object assigns event sequences."""

    __slots__ = ("_events", "_scope", "_state")

    def __init__(self, _issuer: object, start: WindowStartSourceDocumentV1):
        if _issuer is not _JOURNAL_ISSUER:
            _fail("global-supervisor journal sessions are factory-issued only")
        if type(start) is not WindowStartSourceDocumentV1:
            _fail("journal opening requires one exact WINDOW_START document")
        self._scope = start.scope
        self._events: list[GlobalSupervisorEventV1] = []
        self._state = GlobalSupervisorJournalStateV1.WINDOW_STARTED
        self._append_issued(start)

    @property
    def state(self) -> GlobalSupervisorJournalStateV1:
        return self._state

    @property
    def events(self) -> tuple[GlobalSupervisorEventV1, ...]:
        return tuple(self._events)

    def _validate_prefix(self) -> None:
        if self._state is GlobalSupervisorJournalStateV1.FROZEN:
            expected_length = len(EVENT_ORDER)
        else:
            try:
                expected_length = _PREFIX_STATES.index(self._state) + 1
            except ValueError as error:  # pragma: no cover - defensive
                raise ConstructionSharedResourceGlobalSupervisorJournalV1Error(
                    "journal entered an unknown state"
                ) from error
        if len(self._events) != expected_length:
            _fail("journal state and event-prefix length diverged")
        prior: str | None = None
        for sequence, event in enumerate(self._events, start=1):
            if type(event) is not GlobalSupervisorEventV1:
                _fail("journal prefix contains a caller-minted event")
            if (
                event.sequence != sequence
                or event.kind is not EVENT_ORDER[sequence - 1]
                or event.prior_event_id != prior
                or event.scope_id != self._scope.scope_id
            ):
                _fail("journal prefix sequence, lifecycle, or chain is invalid")
            prior = event.event_id

    def _append_issued(
        self,
        source: GlobalSupervisorSourceDocumentV1,
    ) -> GlobalSupervisorEventV1:
        sequence = len(self._events) + 1
        event = GlobalSupervisorEventV1(
            _EVENT_ISSUER,
            self._scope.scope_id,
            sequence,
            EVENT_ORDER[sequence - 1],
            self._events[-1].event_id if self._events else None,
            source,
        )
        self._events.append(event)
        return event

    def append(
        self,
        source: GlobalSupervisorSourceDocumentV1,
    ) -> GlobalSupervisorEventV1:
        """Append the one source type allowed by the current state."""

        self._validate_prefix()
        if self._state is GlobalSupervisorJournalStateV1.FROZEN:
            _fail("cannot append after journal freeze")
        if self._state is GlobalSupervisorJournalStateV1.PARENT_TERMINAL_RECORDED:
            _fail("cannot append after parent terminal")
        expected_index = len(self._events)
        expected_kind = EVENT_ORDER[expected_index]
        expected_type = _SOURCE_TYPE_BY_KIND[expected_kind]
        if type(source) is not expected_type:
            _fail(
                f"journal state requires {expected_kind.value} typed source next"
            )
        if source.scope != self._scope:
            _fail("typed source document crossed the journal scope")
        if expected_kind is GlobalSupervisorEventKindV1.DESCENDANT_SCAN:
            reap = self._events[2].source_document
            assert type(reap) is ProcessReapSourceDocumentV1
            assert type(source) is DescendantScanSourceDocumentV1
            if source.process_handle_key != reap.process_handle_key:
                _fail("descendant scan crossed the reaped process handle")
        event = self._append_issued(source)
        self._state = _PREFIX_STATES[len(self._events) - 1]
        return event

    def freeze(self) -> FrozenGlobalSupervisorEventJournalV1:
        """Freeze only after the exact six-event lifecycle has completed."""

        self._validate_prefix()
        if self._state is not GlobalSupervisorJournalStateV1.PARENT_TERMINAL_RECORDED:
            _fail("journal cannot freeze before PARENT_TERMINAL")
        frozen = FrozenGlobalSupervisorEventJournalV1(
            _JOURNAL_ISSUER,
            self._scope,
            tuple(self._events),
        )
        self._state = GlobalSupervisorJournalStateV1.FROZEN
        return frozen


def open_global_supervisor_event_journal_v1(
    start: WindowStartSourceDocumentV1,
) -> GlobalSupervisorEventJournalSessionV1:
    """Open one journal and internally assign sequence one to WINDOW_START."""

    return GlobalSupervisorEventJournalSessionV1(_JOURNAL_ISSUER, start)


__all__ = [
    "ACTUAL_PROJECTION_PROOF_AUTHORIZED",
    "BusinessCutoffClaimV1",
    "BusinessCutoffSourceDocumentV1",
    "COMPARISON_VECTOR_AUTHORIZED",
    "COUNTER_RECORD_AUTHORIZED",
    "ConstructionSharedResourceGlobalSupervisorJournalV1Error",
    "DescendantScanSourceDocumentV1",
    "EVENT_ORDER",
    "FinalCgroupPeakSourceDocumentV1",
    "FrozenGlobalSupervisorEventJournalV1",
    "GLOBAL_SEQUENCE_MAPPED_TO_OS_ORDER_VERIFIED",
    "GlobalSupervisorEventJournalSessionV1",
    "GlobalSupervisorEventKindV1",
    "GlobalSupervisorEventV1",
    "GlobalSupervisorJournalStateV1",
    "GlobalSupervisorScopeV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OS_SOURCE_PROVENANCE_VERIFIED",
    "ParentTerminalClaimV1",
    "ParentTerminalSourceDocumentV1",
    "ProcessReapSourceDocumentV1",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "WORK_VECTOR_AUTHORIZED",
    "WindowStartSourceDocumentV1",
    "open_global_supervisor_event_journal_v1",
]
