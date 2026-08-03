"""Pre-registered fail-closed admission authority for nine shared resources.

This module is the first Contract-2.0.47 execution slice.  It supplies one
generic supervisor-owned cap profile and mutable admission session, but does
not claim that any production owner currently calls the session.  Formal
actual-compliance and official-execution eligibility therefore remain false.
The session can be activated only for construction tests by a replayed clean
prefreeze prefix and an issuer-owned FALLBACK *candidate*.  That prerequisite
is explicitly not a formal V6/V7 route-decision authority and cannot authorize
production execution.

Budget sessions are one-shot issuer capabilities keyed by profile and route
attempt, so identical same-ID sessions cannot fork a budget.  A callback
exception never proves that no work occurred: absent a successful exact
result (for example returned read bytes), the full reservation is charged and
the construction session becomes a noncertificate protocol failure.

Every accepted or target-cap-rejected admission is exactly one atomic,
nonrecursive ``control.cap_checks`` event.  The small meta comparison which
admits that event does not recursively create another event.  Reservation
settlement and mount close events are evidence-only suffixes and have zero
``control.cap_checks`` delta.

``io.staged_bytes`` is deliberately exposed only through :meth:`stage_ingress`:
it means a named copy or bind into the execution sandbox.  Generic IPC is not
staging and has no API in this authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hmac
import threading
from typing import Any, Callable, Mapping, NoReturn, TypeVar

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    ProtocolSequenceProfileV1,
    replay_access_protocol,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_CAP_FALLBACK_DECISION_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_SHARED_CAP_FALLBACK_DECISION_PREREQUISITE_V1_DOMAIN,
    CONSTRUCTION_SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN,
    CONSTRUCTION_SHARED_CAP_PROFILE_V1_DOMAIN,
    CONSTRUCTION_SHARED_CAP_RECEIPT_V1_DOMAIN,
    CONSTRUCTION_SHARED_CAP_RESERVATION_V1_DOMAIN,
    CONSTRUCTION_SHARED_CAP_SESSION_V1_DOMAIN,
    CONSTRUCTION_SHARED_CAP_SNAPSHOT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp.routing_v1 import (
    RouteDecisionContextV1,
    RouteSelection,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.47"
PROFILE_KEY = "construction_shared_cap_authority_v1"

SHARED_CAP_PROFILE_V1_DOMAIN = CONSTRUCTION_SHARED_CAP_PROFILE_V1_DOMAIN
FALLBACK_DECISION_CANDIDATE_V1_DOMAIN = (
    CONSTRUCTION_SHARED_CAP_FALLBACK_DECISION_CANDIDATE_V1_DOMAIN
)
FALLBACK_DECISION_PREREQUISITE_V1_DOMAIN = (
    CONSTRUCTION_SHARED_CAP_FALLBACK_DECISION_PREREQUISITE_V1_DOMAIN
)
SHARED_CAP_SESSION_V1_DOMAIN = CONSTRUCTION_SHARED_CAP_SESSION_V1_DOMAIN
SHARED_CAP_RESERVATION_V1_DOMAIN = CONSTRUCTION_SHARED_CAP_RESERVATION_V1_DOMAIN
SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN = CONSTRUCTION_SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN
SHARED_CAP_RECEIPT_V1_DOMAIN = CONSTRUCTION_SHARED_CAP_RECEIPT_V1_DOMAIN
SHARED_CAP_SNAPSHOT_V1_DOMAIN = CONSTRUCTION_SHARED_CAP_SNAPSHOT_V1_DOMAIN

SHARED_RESOURCE_PATHS = shared_v1.SHARED_RESOURCE_PATHS
SUM_SHARED_RESOURCE_PATHS = shared_v1.SUM_SHARED_RESOURCE_PATHS
MAX_SHARED_RESOURCE_PATHS = shared_v1.MAX_SHARED_RESOURCE_PATHS
CONTROL_CAP_CHECKS_PATH = "control.cap_checks"
MOUNTED_BYTES_PATH = "io.mounted_bytes_peak"
WORKING_BYTES_PATH = "memory.working_bytes_peak"
READ_BYTES_PATH = "io.read_bytes"
STAGED_BYTES_PATH = "io.staged_bytes"

_PROFILE_ISSUER = object()
_DECISION_CANDIDATE_ISSUER = object()
_DECISION_PREREQUISITE_ISSUER = object()
_SESSION_ISSUER = object()
_RESERVATION_ISSUER = object()
_MOUNT_TOKEN_ISSUER = object()
_RECEIPT_ISSUER = object()
_SNAPSHOT_ISSUER = object()

# These are live runtime capabilities, not serialized proof substitutes.  The
# retained canonical bytes make ``object.__new__`` and post-issuance mutation
# fail even when an attacker also recomputes a plausible content ID.
_LIVE_PROFILES: dict[
    int, tuple["DirectFallbackSharedCapProfileV1", bytes]
] = {}
_LIVE_DECISION_CANDIDATES: dict[
    int, tuple["ConstructionFallbackDecisionCandidateV1", bytes]
] = {}
_LIVE_DECISION_PREREQUISITES: dict[
    int, tuple["ConstructionFallbackDecisionPrerequisiteV1", bytes]
] = {}
_LIVE_SESSIONS: dict[int, "_SessionIssuerSealV1"] = {}
_ISSUED_SESSION_KEYS: dict[
    tuple[str, str], "DirectFallbackSharedCapSessionV1"
] = {}
_LIVE_RESERVATIONS: dict[int, "_ReservationSealV1"] = {}
_LIVE_MOUNT_TOKENS: dict[int, "_MountTokenSealV1"] = {}
_LIVE_RECEIPTS: dict[int, tuple["SharedCapAdmissionReceiptV1", bytes]] = {}
_LIVE_SNAPSHOTS: dict[
    int, tuple["SharedCapSessionSnapshotV1", bytes]
] = {}
_SESSION_ISSUANCE_LOCK = threading.RLock()

T = TypeVar("T")


class ConstructionSharedCapAuthorityV1Error(ValueError):
    """A cap object was malformed, stale, foreign, or used out of order."""


class SharedCapSessionStateV1(str, Enum):
    PREPARED = "PREPARED"
    CONSTRUCTION_ACTIVE = "CONSTRUCTION_ACTIVE"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"
    PROTOCOL_FAILED = "PROTOCOL_FAILED"
    CLOSED = "CLOSED"


class SharedCapReceiptKindV1(str, Enum):
    SUM_RESERVED = "SUM_RESERVED"
    SUM_COMMITTED = "SUM_COMMITTED"
    SUM_REFUNDED = "SUM_REFUNDED"
    SUM_CALLBACK_FAILED = "SUM_CALLBACK_FAILED"
    SUM_PROTOCOL_OVERRETURN = "SUM_PROTOCOL_OVERRETURN"
    SUM_PROTOCOL_CAPABILITY_REJECTED = "SUM_PROTOCOL_CAPABILITY_REJECTED"
    SUM_REJECTED_CAP_EXHAUSTED = "SUM_REJECTED_CAP_EXHAUSTED"
    MAX_ADMITTED = "MAX_ADMITTED"
    MAX_REJECTED_CAP_EXHAUSTED = "MAX_REJECTED_CAP_EXHAUSTED"
    MOUNT_OPENED = "MOUNT_OPENED"
    MOUNT_CLOSED = "MOUNT_CLOSED"
    MOUNT_PROTOCOL_CAPABILITY_REJECTED = "MOUNT_PROTOCOL_CAPABILITY_REJECTED"
    MOUNT_REJECTED_CAP_EXHAUSTED = "MOUNT_REJECTED_CAP_EXHAUSTED"


class SandboxIngressKindV1(str, Enum):
    COPY_INTO_EXECUTION_SANDBOX = "COPY_INTO_EXECUTION_SANDBOX"
    BIND_INTO_EXECUTION_SANDBOX = "BIND_INTO_EXECUTION_SANDBOX"


class SharedCapProtocolFailureV1(ConstructionSharedCapAuthorityV1Error):
    """A protocol error; always a noncertificate ``PROTOCOL_FAILURE``."""

    terminal_scope = "ROUTE_ATTEMPT"
    terminal_class = "ATTEMPT_CLOSURE_NONCERTIFICATE"
    terminal_code = "PROTOCOL_FAILURE"
    certificate_issued = False
    infeasibility_certified = False


class SharedCapExhaustedV1(ConstructionSharedCapAuthorityV1Error):
    """A selected fallback exhausted a preregistered shared-resource cap."""

    terminal_scope = "ROUTE_ATTEMPT"
    terminal_class = "ATTEMPT_CLOSURE_NONCERTIFICATE"
    terminal_code = "FALLBACK_CAP_EXHAUSTED"
    certificate_issued = False
    infeasibility_certified = False

    def __init__(
        self,
        message: str,
        *,
        path: str,
        cap: int,
        current: int,
        requested: int,
        receipt_id: str | None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.cap = cap
        self.current = current
        self.requested = requested
        self.receipt_id = receipt_id


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedCapAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedCapAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _require_live_profile(
    value: Any,
) -> tuple["DirectFallbackSharedCapProfileV1", bytes]:
    if type(value) is not DirectFallbackSharedCapProfileV1:
        _fail("shared-cap profile has a foreign type")
    retained = _LIVE_PROFILES.get(id(value))
    if retained is None or retained[0] is not value:
        _fail("shared-cap profile is not a live issuer authority")
    try:
        current = canonical_json_bytes(value.to_document())
    except Exception as error:
        raise ConstructionSharedCapAuthorityV1Error(
            "shared-cap profile failed live identity replay"
        ) from error
    if not hmac.compare_digest(current, retained[1]):
        _fail("shared-cap profile differs from its issued canonical bytes")
    return retained


def _require_live_decision_candidate(
    value: Any,
) -> tuple["ConstructionFallbackDecisionCandidateV1", bytes]:
    if type(value) is not ConstructionFallbackDecisionCandidateV1:
        _fail("construction fallback decision candidate has a foreign type")
    retained = _LIVE_DECISION_CANDIDATES.get(id(value))
    if retained is None or retained[0] is not value:
        _fail("construction fallback decision candidate is not a live issuer authority")
    try:
        current = canonical_json_bytes(value.to_document())
    except Exception as error:
        raise ConstructionSharedCapAuthorityV1Error(
            "construction fallback decision candidate failed live identity replay"
        ) from error
    if not hmac.compare_digest(current, retained[1]):
        _fail("construction fallback decision candidate changed after issuance")
    return retained


def _require_live_decision_prerequisite(
    value: Any,
) -> tuple["ConstructionFallbackDecisionPrerequisiteV1", bytes]:
    if type(value) is not ConstructionFallbackDecisionPrerequisiteV1:
        _fail("construction fallback decision prerequisite has a foreign type")
    retained = _LIVE_DECISION_PREREQUISITES.get(id(value))
    if retained is None or retained[0] is not value:
        _fail("construction fallback prerequisite is not a live issuer authority")
    try:
        current = canonical_json_bytes(value.to_document())
    except Exception as error:
        raise ConstructionSharedCapAuthorityV1Error(
            "construction fallback prerequisite failed live identity replay"
        ) from error
    if not hmac.compare_digest(current, retained[1]):
        _fail("construction fallback prerequisite changed after issuance")
    return retained


@dataclass(frozen=True, slots=True)
class SharedCapLimitV1:
    path: str
    reducer: ReducerEnum
    unit: str
    cap: int
    source_site_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        if self.path not in SHARED_RESOURCE_PATHS or leaf is None:
            _fail("shared-cap row names an unknown shared-resource path")
        if self.reducer is not leaf.reducer or self.unit != leaf.unit:
            _fail("shared-cap row changed the V6 reducer or unit")
        _nonnegative(self.cap, f"{self.path} cap")
        if (
            type(self.source_site_ids) is not tuple
            or not self.source_site_ids
            or tuple(sorted(self.source_site_ids)) != self.source_site_ids
            or len(set(self.source_site_ids)) != len(self.source_site_ids)
        ):
            _fail("each shared-cap row requires sorted unique source-site IDs")
        for site_id in self.source_site_ids:
            _cid(site_id, f"{self.path} source-site ID")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "reducer": self.reducer.value,
            "unit": self.unit,
            "cap": self.cap,
            "source_site_ids": list(self.source_site_ids),
        }


def _official_v6_identities() -> tuple[Any, Any, Any]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    return registry, stage, comparison


def _require_official_v6_context(route_context: Any) -> RouteDecisionContextV1:
    if type(route_context) is not RouteDecisionContextV1:
        _fail("shared-cap construction requires one exact route context")
    registry = registry_v6.official_counter_registry_v6()
    comparison = registry_v6.official_comparison_profile_v6(registry)
    if (
        route_context.counter_registry_id != registry.registry_id
        or route_context.comparison_profile_id != comparison.comparison_profile_id
    ):
        _fail("shared-cap route context is not bound to official V6 identities")
    return route_context


@dataclass(frozen=True, slots=True)
class ConstructionFallbackDecisionCandidateV1:
    """Construction-only FALLBACK candidate; never a formal route authority."""

    _issuer: InitVar[object]
    route_decision_context_id: str
    decision_point_id: str
    route_attempt_id: str
    fallback_upper_candidate_id: str
    preexecution_barrier_id: str
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DECISION_CANDIDATE_ISSUER:
            _fail("construction fallback decision candidate is issuer-owned")
        for name in (
            "route_decision_context_id",
            "decision_point_id",
            "route_attempt_id",
            "fallback_upper_candidate_id",
            "preexecution_barrier_id",
        ):
            _cid(getattr(self, name), name)
        object.__setattr__(
            self,
            "_candidate_id",
            content_id(FALLBACK_DECISION_CANDIDATE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_cap_fallback_decision_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "route_attempt_id": self.route_attempt_id,
            "fallback_upper_candidate_id": self.fallback_upper_candidate_id,
            "preexecution_barrier_id": self.preexecution_barrier_id,
            "selected_route_candidate": RouteSelection.FALLBACK.value,
            "formal_route_decision": False,
            "execution_permitted": False,
            "construction_only": True,
            "blocker": "V7_FORMAL_ROUTE_DECISION_AUTHORITY_MISSING",
        }

    @property
    def candidate_id(self) -> str:
        return self._candidate_id

    def to_document(self) -> dict[str, Any]:
        payload = self._payload()
        if not hmac.compare_digest(
            content_id(FALLBACK_DECISION_CANDIDATE_V1_DOMAIN, payload),
            self._candidate_id,
        ):
            _fail("construction fallback decision candidate changed after issuance")
        return {**payload, "fallback_decision_candidate_id": self.candidate_id}


def freeze_construction_fallback_decision_candidate_v1(
    *,
    route_context: RouteDecisionContextV1,
    decision_point_id: str,
    fallback_upper_candidate_id: str,
    preexecution_barrier_id: str,
) -> ConstructionFallbackDecisionCandidateV1:
    route_context = _require_official_v6_context(route_context)
    result = ConstructionFallbackDecisionCandidateV1(
        _DECISION_CANDIDATE_ISSUER,
        route_context.route_decision_context_id,
        _cid(decision_point_id, "decision_point_id"),
        route_context.route_attempt_id,
        _cid(fallback_upper_candidate_id, "fallback_upper_candidate_id"),
        _cid(preexecution_barrier_id, "preexecution_barrier_id"),
    )
    _LIVE_DECISION_CANDIDATES[id(result)] = (
        result,
        canonical_json_bytes(result.to_document()),
    )
    return result


@dataclass(frozen=True, slots=True)
class DirectFallbackSharedCapProfileV1:
    """Issuer-owned official-V6 cap profile with no formal route authority."""

    _issuer: InitVar[object]
    route_decision_context_id: str
    route_decision_candidate_id: str
    decision_point_id: str
    route_attempt_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    source_site_manifest_id: str
    limits: tuple[SharedCapLimitV1, ...]
    max_control_cap_checks: int
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("shared-cap profile is issuer-owned")
        for name in (
            "route_decision_context_id",
            "route_decision_candidate_id",
            "decision_point_id",
            "route_attempt_id",
            "counter_registry_id",
            "stage_profile_id",
            "comparison_profile_id",
            "source_site_manifest_id",
        ):
            _cid(getattr(self, name), name)
        if (
            type(self.limits) is not tuple
            or len(self.limits) != 9
            or any(type(row) is not SharedCapLimitV1 for row in self.limits)
            or tuple(row.path for row in self.limits) != SHARED_RESOURCE_PATHS
        ):
            _fail("shared-cap profile must contain the canonical nine rows")
        _positive(self.max_control_cap_checks, "max_control_cap_checks")
        object.__setattr__(
            self,
            "_profile_id",
            content_id(SHARED_CAP_PROFILE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_cap_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_decision_candidate_id": self.route_decision_candidate_id,
            "decision_point_id": self.decision_point_id,
            "route_attempt_id": self.route_attempt_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "source_site_manifest_id": self.source_site_manifest_id,
            "source_site_manifest_semantically_verified": False,
            "source_site_registration_status": (
                "PREREGISTERED_CONSTRUCTION_ONLY_UNVERIFIED"
            ),
            "selected_route_candidate": RouteSelection.FALLBACK.value,
            "formal_v6_route_decision_authority_present": False,
            "construction_prerequisite_only": True,
            "limits": [row.to_document() for row in self.limits],
            "max_control_cap_checks": self.max_control_cap_checks,
            "admission_control_semantics": (
                "ONE_ATOMIC_NONRECURSIVE_CONTROL_CAP_CHECK_PER_ADMISSION"
            ),
            "control_cap_check_self_accounting": True,
            "control_cap_check_recursive_event_count": 0,
            "io_staged_bytes_semantics": (
                "NAMED_COPY_OR_BIND_INGRESS_INTO_EXECUTION_SANDBOX_ONLY"
            ),
            "generic_ipc_is_staged_bytes": False,
            "production_owner_sites_wired": False,
            "formal_actual_compliance_eligible": False,
            "official_execution_allowed": False,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    @property
    def by_path(self) -> dict[str, SharedCapLimitV1]:
        return {row.path: row for row in self.limits}

    def to_document(self) -> dict[str, Any]:
        payload = self._payload()
        if not hmac.compare_digest(
            content_id(SHARED_CAP_PROFILE_V1_DOMAIN, payload), self._profile_id
        ):
            _fail("shared-cap profile changed after issuance")
        return {**payload, "shared_cap_profile_id": self._profile_id}


def freeze_direct_fallback_shared_cap_profile_v1(
    *,
    route_context: RouteDecisionContextV1,
    route_decision_candidate: ConstructionFallbackDecisionCandidateV1,
    stage_profile_id: str,
    source_site_manifest_id: str,
    caps: Mapping[str, int],
    source_site_ids: Mapping[str, tuple[str, ...]],
    max_control_cap_checks: int,
) -> DirectFallbackSharedCapProfileV1:
    """Freeze the exact nine-row profile without authorizing execution."""

    route_context = _require_official_v6_context(route_context)
    _require_live_decision_candidate(route_decision_candidate)
    if (
        route_decision_candidate.route_decision_context_id
        != route_context.route_decision_context_id
        or route_decision_candidate.route_attempt_id != route_context.route_attempt_id
    ):
        _fail("construction fallback decision candidate is foreign to route context")
    if type(caps) is not dict or set(caps) != set(SHARED_RESOURCE_PATHS):
        _fail("shared-cap values must cover exactly the nine canonical paths")
    if (
        type(source_site_ids) is not dict
        or set(source_site_ids) != set(SHARED_RESOURCE_PATHS)
    ):
        _fail("source-site map must cover exactly the nine canonical paths")
    registry, stage, comparison = _official_v6_identities()
    if _cid(stage_profile_id, "stage_profile_id") != stage.stage_profile_id:
        _fail("shared-cap profile requires the official V6 stage profile")
    limits = tuple(
        SharedCapLimitV1(
            path,
            registry.by_path[path].reducer,
            registry.by_path[path].unit,
            _nonnegative(caps[path], f"{path} cap"),
            tuple(sorted(source_site_ids[path])),
        )
        for path in SHARED_RESOURCE_PATHS
    )
    result = DirectFallbackSharedCapProfileV1(
        _PROFILE_ISSUER,
        route_context.route_decision_context_id,
        route_decision_candidate.candidate_id,
        route_decision_candidate.decision_point_id,
        route_context.route_attempt_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        _cid(source_site_manifest_id, "source_site_manifest_id"),
        limits,
        _positive(max_control_cap_checks, "max_control_cap_checks"),
    )
    _LIVE_PROFILES[id(result)] = (
        result,
        canonical_json_bytes(result.to_document()),
    )
    return result


@dataclass(frozen=True, slots=True)
class ConstructionFallbackDecisionPrerequisiteV1:
    """Replayed construction prefix, explicitly short of V7 route authority."""

    _issuer: InitVar[object]
    shared_cap_profile_id: str
    route_decision_context_id: str
    route_decision_candidate_id: str
    decision_point_id: str
    route_attempt_id: str
    protocol_sequence_profile_id: str
    prefreeze_access_event_log_id: str
    _prerequisite_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DECISION_PREREQUISITE_ISSUER:
            _fail("construction fallback decision prerequisite is issuer-owned")
        for name in (
            "shared_cap_profile_id",
            "route_decision_context_id",
            "route_decision_candidate_id",
            "decision_point_id",
            "route_attempt_id",
            "protocol_sequence_profile_id",
            "prefreeze_access_event_log_id",
        ):
            _cid(getattr(self, name), name)
        object.__setattr__(
            self,
            "_prerequisite_id",
            content_id(FALLBACK_DECISION_PREREQUISITE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_shared_cap_fallback_decision_prerequisite.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "shared_cap_profile_id": self.shared_cap_profile_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_decision_candidate_id": self.route_decision_candidate_id,
            "decision_point_id": self.decision_point_id,
            "route_attempt_id": self.route_attempt_id,
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
            "prefreeze_access_event_log_id": self.prefreeze_access_event_log_id,
            "selected_route_candidate": RouteSelection.FALLBACK.value,
            "prefreeze_access_log_replayed": True,
            "formal_v6_route_decision_authority_present": False,
            "authorizes_production_route_execution": False,
            "construction_cap_mechanics_only": True,
            "blocker": "V7_FORMAL_ROUTE_DECISION_AUTHORITY_MISSING",
        }

    @property
    def prerequisite_id(self) -> str:
        return self._prerequisite_id

    def to_document(self) -> dict[str, Any]:
        payload = self._payload()
        if not hmac.compare_digest(
            content_id(FALLBACK_DECISION_PREREQUISITE_V1_DOMAIN, payload),
            self._prerequisite_id,
        ):
            _fail("construction fallback prerequisite changed after issuance")
        return {
            **payload,
            "fallback_decision_prerequisite_id": self.prerequisite_id,
        }


def freeze_construction_fallback_decision_prerequisite_v1(
    *,
    profile: DirectFallbackSharedCapProfileV1,
    route_decision_candidate: ConstructionFallbackDecisionCandidateV1,
    protocol_profile: ProtocolSequenceProfileV1,
    prefreeze_log: AccessEventLogV1,
) -> ConstructionFallbackDecisionPrerequisiteV1:
    """Replay a clean prefreeze prefix without minting formal route authority."""

    _require_live_profile(profile)
    _require_live_decision_candidate(route_decision_candidate)
    if type(protocol_profile) is not ProtocolSequenceProfileV1:
        _fail("construction fallback prerequisite requires exact protocol profile")
    if type(prefreeze_log) is not AccessEventLogV1:
        _fail("construction fallback prerequisite requires exact prefreeze log")
    try:
        replay_access_protocol(prefreeze_log, protocol_profile)
    except Exception as error:
        raise ConstructionSharedCapAuthorityV1Error(
            "construction fallback prerequisite failed access-prefix replay"
        ) from error
    if (
        prefreeze_log.is_frozen
        or prefreeze_log.route_attempt_id != profile.route_attempt_id
        or prefreeze_log.decision_point_id != profile.decision_point_id
        or prefreeze_log.protocol_sequence_profile_id
        != protocol_profile.protocol_sequence_profile_id
        or route_decision_candidate.candidate_id
        != profile.route_decision_candidate_id
        or route_decision_candidate.route_decision_context_id
        != profile.route_decision_context_id
        or route_decision_candidate.decision_point_id != profile.decision_point_id
        or route_decision_candidate.route_attempt_id != profile.route_attempt_id
    ):
        _fail("construction fallback candidate/prefix is stale or foreign")
    result = ConstructionFallbackDecisionPrerequisiteV1(
        _DECISION_PREREQUISITE_ISSUER,
        profile.profile_id,
        profile.route_decision_context_id,
        profile.route_decision_candidate_id,
        profile.decision_point_id,
        profile.route_attempt_id,
        protocol_profile.protocol_sequence_profile_id,
        prefreeze_log.access_event_log_id,
    )
    _LIVE_DECISION_PREREQUISITES[id(result)] = (
        result,
        canonical_json_bytes(result.to_document()),
    )
    return result


@dataclass(frozen=True, slots=True)
class SharedCapReservationV1:
    _issuer: InitVar[object]
    session_id: str
    profile_id: str
    path: str
    site_id: str
    amount: int
    reservation_sequence: int
    _reservation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESERVATION_ISSUER:
            _fail("shared-cap reservation is issuer-owned")
        _cid(self.session_id, "session_id")
        _cid(self.profile_id, "profile_id")
        _cid(self.site_id, "site_id")
        if self.path not in SUM_SHARED_RESOURCE_PATHS:
            _fail("reservation path is not one shared SUM path")
        _nonnegative(self.amount, "reservation amount")
        _positive(self.reservation_sequence, "reservation sequence")
        object.__setattr__(
            self,
            "_reservation_id",
            content_id(SHARED_CAP_RESERVATION_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_cap_reservation.v1",
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "shared_cap_profile_id": self.profile_id,
            "path": self.path,
            "site_id": self.site_id,
            "amount": self.amount,
            "reservation_sequence": self.reservation_sequence,
        }

    @property
    def reservation_id(self) -> str:
        if not hmac.compare_digest(
            content_id(SHARED_CAP_RESERVATION_V1_DOMAIN, self._payload()),
            self._reservation_id,
        ):
            _fail("shared-cap reservation changed after issuance")
        return self._reservation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_cap_reservation_id": self.reservation_id}


@dataclass(frozen=True, slots=True)
class SharedCapMountTokenV1:
    _issuer: InitVar[object]
    session_id: str
    profile_id: str
    site_id: str
    payload_id: str
    payload_bytes: int
    open_sequence: int
    _token_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _MOUNT_TOKEN_ISSUER:
            _fail("mount-visibility token is issuer-owned")
        for name in ("session_id", "profile_id", "site_id", "payload_id"):
            _cid(getattr(self, name), name)
        _nonnegative(self.payload_bytes, "mounted payload bytes")
        _positive(self.open_sequence, "mount open sequence")
        object.__setattr__(
            self,
            "_token_id",
            content_id(SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_cap_mount_token.v1",
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "shared_cap_profile_id": self.profile_id,
            "site_id": self.site_id,
            "payload_id": self.payload_id,
            "payload_bytes": self.payload_bytes,
            "open_sequence": self.open_sequence,
        }

    @property
    def token_id(self) -> str:
        if not hmac.compare_digest(
            content_id(SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN, self._payload()),
            self._token_id,
        ):
            _fail("mount-visibility token changed after issuance")
        return self._token_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_cap_mount_token_id": self.token_id}


@dataclass(frozen=True, slots=True)
class _ReservationSealV1:
    capability: SharedCapReservationV1
    canonical_bytes: bytes
    reservation_id: str
    session_id: str
    profile_id: str
    path: str
    site_id: str
    amount: int


@dataclass(frozen=True, slots=True)
class _MountTokenSealV1:
    capability: SharedCapMountTokenV1
    canonical_bytes: bytes
    token_id: str
    session_id: str
    profile_id: str
    site_id: str
    payload_id: str
    payload_bytes: int


@dataclass(frozen=True, slots=True)
class SharedCapAdmissionReceiptV1:
    _issuer: InitVar[object]
    session_id: str
    profile_id: str
    decision_prerequisite_id: str
    sequence: int
    kind: SharedCapReceiptKindV1
    path: str
    site_id: str
    reducer: ReducerEnum
    requested: int
    committed: int
    refunded: int
    value_before: int
    value_after: int
    retained_peak: int
    control_cap_checks_before: int
    control_cap_checks_after: int
    control_cap_checks_delta: int
    accepted: bool
    terminal_code: str | None
    _receipt_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RECEIPT_ISSUER:
            _fail("shared-cap admission receipt is issuer-owned")
        for name in (
            "session_id",
            "profile_id",
            "decision_prerequisite_id",
            "site_id",
        ):
            _cid(getattr(self, name), name)
        _positive(self.sequence, "receipt sequence")
        if self.path not in set(SHARED_RESOURCE_PATHS) | {CONTROL_CAP_CHECKS_PATH}:
            _fail("shared-cap receipt names an unknown path")
        for name in (
            "requested",
            "committed",
            "refunded",
            "value_before",
            "value_after",
            "retained_peak",
            "control_cap_checks_before",
            "control_cap_checks_after",
            "control_cap_checks_delta",
        ):
            _nonnegative(getattr(self, name), name)
        if self.control_cap_checks_delta not in (0, 1):
            _fail("receipt control-cap delta must be exactly zero or one")
        if (
            self.control_cap_checks_after
            != self.control_cap_checks_before + self.control_cap_checks_delta
        ):
            _fail("receipt control-cap arithmetic is inconsistent")
        if self.terminal_code not in (None, "FALLBACK_CAP_EXHAUSTED", "PROTOCOL_FAILURE"):
            _fail("receipt terminal code is invalid")
        object.__setattr__(
            self,
            "_receipt_id",
            content_id(SHARED_CAP_RECEIPT_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_cap_admission_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "shared_cap_profile_id": self.profile_id,
            "fallback_decision_prerequisite_id": self.decision_prerequisite_id,
            "sequence": self.sequence,
            "kind": self.kind.value,
            "path": self.path,
            "site_id": self.site_id,
            "reducer": self.reducer.value,
            "requested": self.requested,
            "committed": self.committed,
            "refunded": self.refunded,
            "value_before": self.value_before,
            "value_after": self.value_after,
            "retained_peak": self.retained_peak,
            "control_cap_checks_before": self.control_cap_checks_before,
            "control_cap_checks_after": self.control_cap_checks_after,
            "control_cap_checks_delta": self.control_cap_checks_delta,
            "accepted": self.accepted,
            "terminal_class": (
                None if self.terminal_code is None else "ATTEMPT_CLOSURE_NONCERTIFICATE"
            ),
            "terminal_code": self.terminal_code,
            "certificate_issued": False,
            "infeasibility_certified": False,
            "accounting_identity_hash_excluded_from_business_hash_meter": True,
        }

    @property
    def receipt_id(self) -> str:
        if not hmac.compare_digest(
            content_id(SHARED_CAP_RECEIPT_V1_DOMAIN, self._payload()),
            self._receipt_id,
        ):
            _fail("shared-cap receipt changed after issuance")
        return self._receipt_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_cap_receipt_id": self.receipt_id}


@dataclass(frozen=True, slots=True)
class SharedCapSessionSnapshotV1:
    _issuer: InitVar[object]
    session_id: str
    profile_id: str
    decision_prerequisite_id: str | None
    state: SharedCapSessionStateV1
    terminal_code: str | None
    shared_values: tuple[tuple[str, int], ...]
    outstanding_reserved_values: tuple[tuple[str, int], ...]
    mounted_current_bytes: int
    control_cap_checks: int
    receipt_ids: tuple[str, ...]
    _snapshot_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SNAPSHOT_ISSUER:
            _fail("shared-cap snapshot is issuer-owned")
        _cid(self.session_id, "session_id")
        _cid(self.profile_id, "profile_id")
        if self.decision_prerequisite_id is not None:
            _cid(self.decision_prerequisite_id, "decision_prerequisite_id")
        if tuple(path for path, _ in self.shared_values) != SHARED_RESOURCE_PATHS:
            _fail("snapshot does not contain the canonical nine values")
        if tuple(path for path, _ in self.outstanding_reserved_values) != tuple(
            path for path in SHARED_RESOURCE_PATHS if path in SUM_SHARED_RESOURCE_PATHS
        ):
            _fail("snapshot does not contain the canonical SUM reservations")
        for _, value in self.shared_values + self.outstanding_reserved_values:
            _nonnegative(value, "snapshot value")
        _nonnegative(self.mounted_current_bytes, "mounted current bytes")
        _nonnegative(self.control_cap_checks, "control cap checks")
        for receipt_id in self.receipt_ids:
            _cid(receipt_id, "receipt ID")
        object.__setattr__(
            self,
            "_snapshot_id",
            content_id(SHARED_CAP_SNAPSHOT_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_cap_session_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "shared_cap_profile_id": self.profile_id,
            "fallback_decision_prerequisite_id": self.decision_prerequisite_id,
            "state": self.state.value,
            "terminal_scope": None if self.terminal_code is None else "ROUTE_ATTEMPT",
            "terminal_class": (
                None if self.terminal_code is None else "ATTEMPT_CLOSURE_NONCERTIFICATE"
            ),
            "terminal_code": self.terminal_code,
            "shared_values": [
                {"path": path, "value": value} for path, value in self.shared_values
            ],
            "outstanding_reserved_values": [
                {"path": path, "value": value}
                for path, value in self.outstanding_reserved_values
            ],
            "mounted_current_bytes": self.mounted_current_bytes,
            "control_cap_checks": self.control_cap_checks,
            "receipt_ids": list(self.receipt_ids),
            "certificate_issued": False,
            "infeasibility_certified": False,
            "production_owner_sites_wired": False,
            "source_site_manifest_semantically_verified": False,
            "formal_actual_compliance_eligible": False,
        }

    @property
    def snapshot_id(self) -> str:
        retained = _LIVE_SNAPSHOTS.get(id(self))
        if retained is None or retained[0] is not self:
            raise SharedCapProtocolFailureV1(
                "shared-cap snapshot is not a live issuer artifact"
            )
        try:
            payload = self._payload()
            current_id = content_id(SHARED_CAP_SNAPSHOT_V1_DOMAIN, payload)
            current_document = {
                **payload,
                "shared_cap_snapshot_id": self._snapshot_id,
            }
            current_bytes = canonical_json_bytes(current_document)
        except Exception as error:
            raise SharedCapProtocolFailureV1(
                "shared-cap snapshot failed canonical identity replay"
            ) from error
        if (
            not hmac.compare_digest(current_id, self._snapshot_id)
            or not hmac.compare_digest(current_bytes, retained[1])
        ):
            raise SharedCapProtocolFailureV1(
                "shared-cap snapshot changed after issuance"
            )
        return self._snapshot_id

    def to_document(self) -> dict[str, Any]:
        snapshot_id = self.snapshot_id
        return {**self._payload(), "shared_cap_snapshot_id": snapshot_id}


@dataclass(frozen=True, slots=True)
class _SessionRuntimeSealV1:
    state: SharedCapSessionStateV1
    decision_prerequisite: ConstructionFallbackDecisionPrerequisiteV1 | None
    terminal_code: str | None
    sum_committed: tuple[tuple[str, int], ...]
    sum_reserved: tuple[tuple[str, int], ...]
    max_values: tuple[tuple[str, int], ...]
    control_cap_checks: int
    receipts: tuple[SharedCapAdmissionReceiptV1, ...]
    active_reservations: tuple[tuple[str, SharedCapReservationV1], ...]
    settled_reservations: frozenset[str]
    mount_entries: tuple[tuple[str, tuple[int, int]], ...]
    mount_tokens: tuple[tuple[str, SharedCapMountTokenV1], ...]
    closed_mount_tokens: frozenset[str]
    mounted_current_bytes: int
    canonical_bytes: bytes


@dataclass(frozen=True, slots=True)
class _SessionIssuerSealV1:
    capability: "DirectFallbackSharedCapSessionV1"
    lock: threading.RLock
    profile: DirectFallbackSharedCapProfileV1
    profile_id: str
    profile_bytes: bytes
    session_id: str
    identity_bytes: bytes
    runtime: _SessionRuntimeSealV1


class DirectFallbackSharedCapSessionV1:
    """Mutable, atomic admission authority for one selected fallback attempt."""

    __slots__ = (
        "_profile",
        "_profile_id",
        "_profile_bytes",
        "_session_id",
        "_state",
        "_decision_prerequisite",
        "_terminal_code",
        "_sum_committed",
        "_sum_reserved",
        "_max_values",
        "_control_cap_checks",
        "_receipts",
        "_active_reservations",
        "_settled_reservations",
        "_mount_entries",
        "_mount_tokens",
        "_closed_mount_tokens",
        "_mounted_current_bytes",
        "_lock",
    )

    def __getattribute__(self, name: str) -> Any:
        # Public surface access is itself capability use.  Looking up a method
        # on an ``object.__new__`` forgery must therefore fail with the typed
        # protocol outcome before Python can leak a missing-field AttributeError.
        if not name.startswith("_"):
            seal = _LIVE_SESSIONS.get(id(self))
            if seal is None or seal.capability is not self:
                raise SharedCapProtocolFailureV1(
                    "shared-cap session is not a live issuer authority"
                )
            with seal.lock:
                object.__getattribute__(self, "_assert_live_session")()
        return object.__getattribute__(self, name)

    def __init__(
        self,
        profile: DirectFallbackSharedCapProfileV1,
        *,
        _issuer: object | None = None,
    ) -> None:
        if _issuer is not _SESSION_ISSUER:
            raise SharedCapProtocolFailureV1(
                "shared-cap sessions are issued only by the one-shot factory"
            )
        _, issued_profile_bytes = _require_live_profile(profile)
        self._profile = profile
        self._profile_id = profile.profile_id
        self._profile_bytes = issued_profile_bytes
        self._session_id = content_id(
            SHARED_CAP_SESSION_V1_DOMAIN,
            {
                "schema": "acfqp.construction_shared_cap_session.v1",
                "schema_version": SCHEMA_VERSION,
                "shared_cap_profile_id": profile.profile_id,
                "RouteDecisionContext_id": profile.route_decision_context_id,
                "route_decision_candidate_id": profile.route_decision_candidate_id,
                "decision_point_id": profile.decision_point_id,
                "route_attempt_id": profile.route_attempt_id,
            },
        )
        self._state = SharedCapSessionStateV1.PREPARED
        self._decision_prerequisite: (
            ConstructionFallbackDecisionPrerequisiteV1 | None
        ) = None
        self._terminal_code: str | None = None
        self._sum_committed = {path: 0 for path in SUM_SHARED_RESOURCE_PATHS}
        self._sum_reserved = {path: 0 for path in SUM_SHARED_RESOURCE_PATHS}
        self._max_values = {path: 0 for path in MAX_SHARED_RESOURCE_PATHS}
        self._control_cap_checks = 0
        self._receipts: list[SharedCapAdmissionReceiptV1] = []
        self._active_reservations: dict[str, SharedCapReservationV1] = {}
        self._settled_reservations: set[str] = set()
        self._mount_entries: dict[str, tuple[int, int]] = {}
        self._mount_tokens: dict[str, SharedCapMountTokenV1] = {}
        self._closed_mount_tokens: set[str] = set()
        self._mounted_current_bytes = 0
        self._lock = threading.RLock()

    def __copy__(self) -> NoReturn:
        raise SharedCapProtocolFailureV1("shared-cap session cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]) -> NoReturn:
        raise SharedCapProtocolFailureV1(
            "shared-cap session cannot be deep-copied"
        )

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        raise SharedCapProtocolFailureV1(
            "shared-cap session cannot be serialized"
        )

    def _identity_document_unchecked(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_cap_session.v1",
            "schema_version": SCHEMA_VERSION,
            "shared_cap_profile_id": object.__getattribute__(self, "_profile_id"),
            "session_id": object.__getattribute__(self, "_session_id"),
            "profile_object_identity": id(
                object.__getattribute__(self, "_profile")
            ),
            "lock_object_identity": id(object.__getattribute__(self, "_lock")),
            "profile_bytes": object.__getattribute__(self, "_profile_bytes").hex(),
        }

    def _runtime_document_unchecked(self) -> dict[str, Any]:
        state = object.__getattribute__(self, "_state")
        prerequisite = object.__getattribute__(self, "_decision_prerequisite")
        terminal_code = object.__getattribute__(self, "_terminal_code")
        sum_committed = object.__getattribute__(self, "_sum_committed")
        sum_reserved = object.__getattribute__(self, "_sum_reserved")
        max_values = object.__getattribute__(self, "_max_values")
        control = object.__getattribute__(self, "_control_cap_checks")
        receipts = object.__getattribute__(self, "_receipts")
        active = object.__getattribute__(self, "_active_reservations")
        settled = object.__getattribute__(self, "_settled_reservations")
        mount_entries = object.__getattribute__(self, "_mount_entries")
        mount_tokens = object.__getattribute__(self, "_mount_tokens")
        closed_mount_tokens = object.__getattribute__(self, "_closed_mount_tokens")
        mounted_current = object.__getattribute__(self, "_mounted_current_bytes")
        if type(state) is not SharedCapSessionStateV1:
            raise SharedCapProtocolFailureV1("shared-cap state has a foreign value")
        if prerequisite is not None and type(prerequisite) is not ConstructionFallbackDecisionPrerequisiteV1:
            raise SharedCapProtocolFailureV1(
                "shared-cap prerequisite state has a foreign value"
            )
        if terminal_code not in (
            None,
            SharedCapProtocolFailureV1.terminal_code,
            SharedCapExhaustedV1.terminal_code,
        ):
            raise SharedCapProtocolFailureV1(
                "shared-cap terminal state has a foreign value"
            )
        expected_sum = set(SUM_SHARED_RESOURCE_PATHS)
        expected_max = set(MAX_SHARED_RESOURCE_PATHS)
        if (
            type(sum_committed) is not dict
            or set(sum_committed) != expected_sum
            or type(sum_reserved) is not dict
            or set(sum_reserved) != expected_sum
            or type(max_values) is not dict
            or set(max_values) != expected_max
        ):
            raise SharedCapProtocolFailureV1(
                "shared-cap accounting maps are malformed"
            )
        for value in tuple(sum_committed.values()) + tuple(sum_reserved.values()) + tuple(max_values.values()):
            if type(value) is not int or value < 0:
                raise SharedCapProtocolFailureV1(
                    "shared-cap accounting value is not a nonnegative exact integer"
                )
        if type(control) is not int or control < 0:
            raise SharedCapProtocolFailureV1(
                "shared-cap control count is not a nonnegative exact integer"
            )
        if (
            type(receipts) is not list
            or type(active) is not dict
            or type(settled) is not set
            or type(mount_entries) is not dict
            or type(mount_tokens) is not dict
            or type(closed_mount_tokens) is not set
            or type(mounted_current) is not int
            or mounted_current < 0
        ):
            raise SharedCapProtocolFailureV1(
                "shared-cap runtime containers are malformed"
            )
        return {
            "state": state.value,
            "decision_prerequisite_object_identity": (
                None if prerequisite is None else id(prerequisite)
            ),
            "terminal_code": terminal_code,
            "sum_committed": [[path, sum_committed[path]] for path in SUM_SHARED_RESOURCE_PATHS],
            "sum_reserved": [[path, sum_reserved[path]] for path in SUM_SHARED_RESOURCE_PATHS],
            "max_values": [[path, max_values[path]] for path in MAX_SHARED_RESOURCE_PATHS],
            "control_cap_checks": control,
            "receipt_object_identities": [id(value) for value in receipts],
            "active_reservations": [
                [key, id(value)] for key, value in sorted(active.items())
            ],
            "settled_reservations": sorted(settled),
            "mount_entries": [
                [key, list(value)] for key, value in sorted(mount_entries.items())
            ],
            "mount_tokens": [
                [key, id(value)] for key, value in sorted(mount_tokens.items())
            ],
            "closed_mount_tokens": sorted(closed_mount_tokens),
            "mounted_current_bytes": mounted_current,
        }

    def _capture_runtime_seal_unchecked(self) -> _SessionRuntimeSealV1:
        document = self._runtime_document_unchecked()
        return _SessionRuntimeSealV1(
            object.__getattribute__(self, "_state"),
            object.__getattribute__(self, "_decision_prerequisite"),
            object.__getattribute__(self, "_terminal_code"),
            tuple(object.__getattribute__(self, "_sum_committed").items()),
            tuple(object.__getattribute__(self, "_sum_reserved").items()),
            tuple(object.__getattribute__(self, "_max_values").items()),
            object.__getattribute__(self, "_control_cap_checks"),
            tuple(object.__getattribute__(self, "_receipts")),
            tuple(object.__getattribute__(self, "_active_reservations").items()),
            frozenset(object.__getattribute__(self, "_settled_reservations")),
            tuple(object.__getattribute__(self, "_mount_entries").items()),
            tuple(object.__getattribute__(self, "_mount_tokens").items()),
            frozenset(object.__getattribute__(self, "_closed_mount_tokens")),
            object.__getattribute__(self, "_mounted_current_bytes"),
            canonical_json_bytes(document),
        )

    def _initial_issuer_seal_unchecked(self) -> _SessionIssuerSealV1:
        identity = canonical_json_bytes(self._identity_document_unchecked())
        return _SessionIssuerSealV1(
            self,
            object.__getattribute__(self, "_lock"),
            object.__getattribute__(self, "_profile"),
            object.__getattribute__(self, "_profile_id"),
            object.__getattribute__(self, "_profile_bytes"),
            object.__getattribute__(self, "_session_id"),
            identity,
            self._capture_runtime_seal_unchecked(),
        )

    def _refresh_session_seal_unchecked(self) -> None:
        retained = _LIVE_SESSIONS.get(id(self))
        if retained is None or retained.capability is not self:
            raise SharedCapProtocolFailureV1(
                "shared-cap session is not a live issuer authority"
            )
        _LIVE_SESSIONS[id(self)] = _SessionIssuerSealV1(
            self,
            retained.lock,
            retained.profile,
            retained.profile_id,
            retained.profile_bytes,
            retained.session_id,
            retained.identity_bytes,
            self._capture_runtime_seal_unchecked(),
        )

    def _restore_from_issuer_seal_unchecked(
        self, seal: _SessionIssuerSealV1
    ) -> None:
        runtime = seal.runtime
        object.__setattr__(self, "_profile", seal.profile)
        object.__setattr__(self, "_profile_id", seal.profile_id)
        object.__setattr__(self, "_profile_bytes", seal.profile_bytes)
        object.__setattr__(self, "_session_id", seal.session_id)
        object.__setattr__(self, "_lock", seal.lock)
        object.__setattr__(self, "_state", runtime.state)
        object.__setattr__(self, "_decision_prerequisite", runtime.decision_prerequisite)
        object.__setattr__(self, "_terminal_code", runtime.terminal_code)
        object.__setattr__(self, "_sum_committed", dict(runtime.sum_committed))
        object.__setattr__(self, "_sum_reserved", dict(runtime.sum_reserved))
        object.__setattr__(self, "_max_values", dict(runtime.max_values))
        object.__setattr__(self, "_control_cap_checks", runtime.control_cap_checks)
        object.__setattr__(self, "_receipts", list(runtime.receipts))
        object.__setattr__(self, "_active_reservations", dict(runtime.active_reservations))
        object.__setattr__(self, "_settled_reservations", set(runtime.settled_reservations))
        object.__setattr__(self, "_mount_entries", dict(runtime.mount_entries))
        object.__setattr__(self, "_mount_tokens", dict(runtime.mount_tokens))
        object.__setattr__(self, "_closed_mount_tokens", set(runtime.closed_mount_tokens))
        object.__setattr__(self, "_mounted_current_bytes", runtime.mounted_current_bytes)

    def _assert_live_session(self) -> None:
        retained = _LIVE_SESSIONS.get(id(self))
        if retained is None or retained.capability is not self:
            raise SharedCapProtocolFailureV1(
                "shared-cap session is not the one-shot live issuer authority"
            )
        try:
            identity = canonical_json_bytes(self._identity_document_unchecked())
            runtime = canonical_json_bytes(self._runtime_document_unchecked())
            profile, profile_bytes = _require_live_profile(retained.profile)
            if object.__getattribute__(self, "_decision_prerequisite") is not None:
                _require_live_decision_prerequisite(
                    object.__getattribute__(self, "_decision_prerequisite")
                )
            valid = (
                profile is retained.profile
                and object.__getattribute__(self, "_lock") is retained.lock
                and object.__getattribute__(self, "_profile") is retained.profile
                and object.__getattribute__(self, "_profile_id") == retained.profile_id
                and object.__getattribute__(self, "_profile_bytes") == retained.profile_bytes
                and object.__getattribute__(self, "_session_id") == retained.session_id
                and hmac.compare_digest(identity, retained.identity_bytes)
                and hmac.compare_digest(profile_bytes, retained.profile_bytes)
                and hmac.compare_digest(runtime, retained.runtime.canonical_bytes)
            )
        except Exception as error:
            self._restore_from_issuer_seal_unchecked(retained)
            self._protocol_fail(
                "shared-cap session fixed identity or runtime seal is invalid",
                error if isinstance(error, Exception) else None,
            )
        if not valid:
            self._restore_from_issuer_seal_unchecked(retained)
            self._protocol_fail(
                "shared-cap session changed after issuer sealing"
            )

    def _public_lock_unchecked(self) -> threading.RLock:
        retained = _LIVE_SESSIONS.get(id(self))
        if retained is None or retained.capability is not self:
            raise SharedCapProtocolFailureV1(
                "shared-cap session is not a live issuer authority"
            )
        return retained.lock

    @property
    def session_id(self) -> str:
        with self._public_lock_unchecked():
            self._assert_live_session()
            return self._session_id

    @property
    def state(self) -> SharedCapSessionStateV1:
        with self._public_lock_unchecked():
            self._assert_live_session()
            return self._state

    @property
    def receipts(self) -> tuple[SharedCapAdmissionReceiptV1, ...]:
        with self._public_lock_unchecked():
            self._assert_live_session()
            self._assert_receipts_current()
            return tuple(self._receipts)

    @property
    def control_cap_checks(self) -> int:
        with self._public_lock_unchecked():
            self._assert_live_session()
            return self._control_cap_checks

    def _assert_profile_current(self) -> None:
        self._assert_live_session()
        try:
            retained_profile, retained_bytes = _require_live_profile(self._profile)
            current = canonical_json_bytes(retained_profile.to_document())
        except Exception as error:
            self._protocol_fail("shared-cap profile became invalid or stale", error)
        if (
            self._profile.profile_id != self._profile_id
            or not hmac.compare_digest(retained_bytes, self._profile_bytes)
            or not hmac.compare_digest(current, self._profile_bytes)
        ):
            self._protocol_fail("shared-cap profile changed after session creation")

    def _assert_receipts_current(self) -> None:
        for receipt in self._receipts:
            retained = _LIVE_RECEIPTS.get(id(receipt))
            try:
                current = canonical_json_bytes(receipt.to_document())
            except Exception as error:
                self._protocol_fail("shared-cap receipt failed identity replay", error)
            if (
                retained is None
                or retained[0] is not receipt
                or not hmac.compare_digest(current, retained[1])
            ):
                self._protocol_fail(
                    "shared-cap receipt is foreign or changed after issuance"
                )

    def _settle_all_outstanding_reservations_unchecked(self) -> None:
        """Charge every admitted-but-unsettled SUM upper exactly once.

        A protocol transition cannot infer how much of any side effect already
        happened.  The retained issuer seals are therefore the only trusted
        settlement source, and every still-live reservation is fully charged.
        """

        active = list(object.__getattribute__(self, "_active_reservations").values())
        for reservation in active:
            seal = _LIVE_RESERVATIONS.get(id(reservation))
            if seal is None or seal.capability is not reservation:
                # Runtime topology is issuer-sealed.  A missing external
                # capability seal is itself unrecoverable protocol corruption.
                continue
            self._conservatively_settle_reservation(
                seal,
                receipt_kind=SharedCapReceiptKindV1.SUM_PROTOCOL_CAPABILITY_REJECTED,
            )

    def _transition_protocol_failed_unchecked(self) -> None:
        # This is the one protocol transition authority.  In particular, a
        # callback may invoke another session method, catch its typed failure,
        # and return normally; the outer reservation is still found here and
        # conservatively charged before the callback can appear successful.
        self._settle_all_outstanding_reservations_unchecked()
        object.__setattr__(self, "_state", SharedCapSessionStateV1.PROTOCOL_FAILED)
        object.__setattr__(
            self, "_terminal_code", SharedCapProtocolFailureV1.terminal_code
        )
        if _LIVE_SESSIONS.get(id(self)) is not None:
            self._refresh_session_seal_unchecked()

    def _protocol_fail(self, message: str, cause: Exception | None = None) -> NoReturn:
        self._transition_protocol_failed_unchecked()
        error = SharedCapProtocolFailureV1(message)
        if cause is None:
            raise error
        raise error from cause

    def _runtime_nonnegative(self, value: Any, label: str) -> int:
        try:
            return _nonnegative(value, label)
        except ConstructionSharedCapAuthorityV1Error as error:
            self._protocol_fail(f"invalid runtime {label}", error)

    def _runtime_cid(self, value: Any, label: str) -> str:
        try:
            return _cid(value, label)
        except ConstructionSharedCapAuthorityV1Error as error:
            self._protocol_fail(f"invalid runtime {label}", error)

    def activate_construction(
        self, prerequisite: ConstructionFallbackDecisionPrerequisiteV1
    ) -> None:
        """Activate synthetic cap mechanics without production authority."""

        with self._public_lock_unchecked():
            self._assert_profile_current()
            if self._state is not SharedCapSessionStateV1.PREPARED:
                self._protocol_fail("shared-cap session activation is out of order")
            if type(prerequisite) is not ConstructionFallbackDecisionPrerequisiteV1:
                self._protocol_fail(
                    "shared-cap session requires construction decision prerequisite"
                )
            try:
                _require_live_decision_prerequisite(prerequisite)
            except ConstructionSharedCapAuthorityV1Error as error:
                self._protocol_fail(
                    "shared-cap session requires a live construction prerequisite",
                    error,
                )
            expected = (
                self._profile_id,
                self._profile.route_decision_context_id,
                self._profile.route_decision_candidate_id,
                self._profile.decision_point_id,
                self._profile.route_attempt_id,
            )
            actual = (
                prerequisite.shared_cap_profile_id,
                prerequisite.route_decision_context_id,
                prerequisite.route_decision_candidate_id,
                prerequisite.decision_point_id,
                prerequisite.route_attempt_id,
            )
            if actual != expected:
                self._protocol_fail(
                    "construction fallback prerequisite is foreign to this session"
                )
            self._decision_prerequisite = prerequisite
            self._state = SharedCapSessionStateV1.CONSTRUCTION_ACTIVE
            self._refresh_session_seal_unchecked()

    def _ensure_active(self) -> ConstructionFallbackDecisionPrerequisiteV1:
        self._assert_profile_current()
        self._assert_receipts_current()
        if (
            self._state is not SharedCapSessionStateV1.CONSTRUCTION_ACTIVE
            or self._decision_prerequisite is None
        ):
            self._protocol_fail(
                "shared-cap admission occurred outside construction-active FALLBACK"
            )
        return self._decision_prerequisite

    def _row_and_site(
        self, path: str, site_id: str, reducer: ReducerEnum
    ) -> SharedCapLimitV1:
        authority = self._ensure_active()
        del authority
        row = self._profile.by_path.get(path)
        if row is None or row.reducer is not reducer:
            self._protocol_fail("shared-cap path/reducer is unknown or mismatched")
        try:
            parsed_site = _cid(site_id, "source-site ID")
        except ConstructionSharedCapAuthorityV1Error as error:
            self._protocol_fail("shared-cap admission used an invalid source-site ID", error)
        if parsed_site not in row.source_site_ids:
            self._protocol_fail("shared-cap admission bypassed its frozen source-site manifest")
        return row

    def _begin_admission(
        self, path: str, site_id: str, reducer: ReducerEnum
    ) -> tuple[SharedCapLimitV1, int]:
        row = self._row_and_site(path, site_id, reducer)
        before = self._control_cap_checks
        if before + 1 > self._profile.max_control_cap_checks:
            self._state = SharedCapSessionStateV1.CAP_EXHAUSTED
            self._terminal_code = SharedCapExhaustedV1.terminal_code
            self._refresh_session_seal_unchecked()
            raise SharedCapExhaustedV1(
                "nonrecursive control.cap_checks admission cap exhausted",
                path=CONTROL_CAP_CHECKS_PATH,
                cap=self._profile.max_control_cap_checks,
                current=before,
                requested=1,
                receipt_id=None,
            )
        # This increment is the admission check itself.  It does not call this
        # method recursively and therefore creates exactly one registered event.
        self._control_cap_checks = before + 1
        return row, before

    def _append_receipt(
        self,
        *,
        kind: SharedCapReceiptKindV1,
        path: str,
        site_id: str,
        reducer: ReducerEnum,
        requested: int,
        committed: int,
        refunded: int,
        value_before: int,
        value_after: int,
        retained_peak: int,
        control_before: int,
        control_delta: int,
        accepted: bool,
        terminal_code: str | None = None,
    ) -> SharedCapAdmissionReceiptV1:
        prerequisite = self._decision_prerequisite
        if prerequisite is None:
            self._protocol_fail(
                "receipt creation requires construction decision prerequisite"
            )
        receipt = SharedCapAdmissionReceiptV1(
            _RECEIPT_ISSUER,
            self._session_id,
            self._profile_id,
            prerequisite.prerequisite_id,
            len(self._receipts) + 1,
            kind,
            path,
            site_id,
            reducer,
            requested,
            committed,
            refunded,
            value_before,
            value_after,
            retained_peak,
            control_before,
            control_before + control_delta,
            control_delta,
            accepted,
            terminal_code,
        )
        _LIVE_RECEIPTS[id(receipt)] = (
            receipt,
            canonical_json_bytes(receipt.to_document()),
        )
        self._receipts.append(receipt)
        self._refresh_session_seal_unchecked()
        return receipt

    def _reject_cap(
        self,
        *,
        kind: SharedCapReceiptKindV1,
        row: SharedCapLimitV1,
        site_id: str,
        requested: int,
        current: int,
        control_before: int,
        retained_peak: int,
    ) -> NoReturn:
        receipt = self._append_receipt(
            kind=kind,
            path=row.path,
            site_id=site_id,
            reducer=row.reducer,
            requested=requested,
            committed=0,
            refunded=0,
            value_before=current,
            value_after=current,
            retained_peak=retained_peak,
            control_before=control_before,
            control_delta=1,
            accepted=False,
            terminal_code=SharedCapExhaustedV1.terminal_code,
        )
        self._state = SharedCapSessionStateV1.CAP_EXHAUSTED
        self._terminal_code = SharedCapExhaustedV1.terminal_code
        self._refresh_session_seal_unchecked()
        raise SharedCapExhaustedV1(
            f"{row.path} preregistered cap exhausted",
            path=row.path,
            cap=row.cap,
            current=current,
            requested=requested,
            receipt_id=receipt.receipt_id,
        )

    def _reserve_sum(
        self, path: str, amount: int, *, site_id: str
    ) -> SharedCapReservationV1:
        with self._lock:
            amount = self._runtime_nonnegative(amount, "SUM reservation amount")
            row, control_before = self._begin_admission(
                path, site_id, ReducerEnum.SUM
            )
            current = self._sum_committed[path] + self._sum_reserved[path]
            if current + amount > row.cap:
                self._reject_cap(
                    kind=SharedCapReceiptKindV1.SUM_REJECTED_CAP_EXHAUSTED,
                    row=row,
                    site_id=site_id,
                    requested=amount,
                    current=current,
                    control_before=control_before,
                    retained_peak=current,
                )
            reservation = SharedCapReservationV1(
                _RESERVATION_ISSUER,
                self._session_id,
                self._profile_id,
                path,
                site_id,
                amount,
                len(self._receipts) + 1,
            )
            reservation_id = reservation.reservation_id
            _LIVE_RESERVATIONS[id(reservation)] = _ReservationSealV1(
                reservation,
                canonical_json_bytes(reservation.to_document()),
                reservation_id,
                self._session_id,
                self._profile_id,
                path,
                site_id,
                amount,
            )
            self._sum_reserved[path] += amount
            self._active_reservations[reservation_id] = reservation
            self._append_receipt(
                kind=SharedCapReceiptKindV1.SUM_RESERVED,
                path=path,
                site_id=site_id,
                reducer=ReducerEnum.SUM,
                requested=amount,
                committed=0,
                refunded=0,
                value_before=current,
                value_after=current + amount,
                retained_peak=current + amount,
                control_before=control_before,
                control_delta=1,
                accepted=True,
            )
            return reservation

    def reserve_sum(
        self, path: str, amount: int, *, site_id: str
    ) -> SharedCapReservationV1:
        """Reserve a SUM charge before the corresponding side effect.

        Staging is intentionally excluded from this generic entry point so a
        caller cannot relabel ordinary IPC as sandbox ingress.
        """

        with self._public_lock_unchecked():
            self._assert_live_session()
            if path == STAGED_BYTES_PATH:
                self._protocol_fail(
                    "io.staged_bytes is admitted only by stage_ingress"
                )
        return self._reserve_sum(path, amount, site_id=site_id)

    def _conservatively_settle_reservation(
        self,
        seal: _ReservationSealV1,
        *,
        receipt_kind: SharedCapReceiptKindV1,
    ) -> None:
        current = self._active_reservations.get(seal.reservation_id)
        if current is not seal.capability:
            return
        before = self._sum_committed[seal.path] + self._sum_reserved[seal.path]
        if self._sum_reserved[seal.path] < seal.amount:
            self._protocol_fail("reservation bookkeeping would become negative")
        self._sum_reserved[seal.path] -= seal.amount
        self._sum_committed[seal.path] += seal.amount
        self._active_reservations.pop(seal.reservation_id)
        self._settled_reservations.add(seal.reservation_id)
        self._append_receipt(
            kind=receipt_kind,
            path=seal.path,
            site_id=seal.site_id,
            reducer=ReducerEnum.SUM,
            requested=seal.amount,
            committed=seal.amount,
            refunded=0,
            value_before=before,
            value_after=before,
            retained_peak=before,
            control_before=self._control_cap_checks,
            control_delta=0,
            accepted=False,
            terminal_code=SharedCapProtocolFailureV1.terminal_code,
        )

    def _reservation(self, value: Any) -> _ReservationSealV1:
        if type(value) is not SharedCapReservationV1:
            self._protocol_fail("reservation settlement used a foreign capability")
        seal = _LIVE_RESERVATIONS.get(id(value))
        if seal is None or seal.capability is not value:
            self._protocol_fail("reservation is not a live issuer capability")
        try:
            current_bytes = canonical_json_bytes(value.to_document())
        except Exception as error:
            self._conservatively_settle_reservation(
                seal,
                receipt_kind=(
                    SharedCapReceiptKindV1.SUM_PROTOCOL_CAPABILITY_REJECTED
                ),
            )
            self._protocol_fail("reservation failed post-issuance identity replay", error)
        if not hmac.compare_digest(current_bytes, seal.canonical_bytes):
            self._conservatively_settle_reservation(
                seal,
                receipt_kind=(
                    SharedCapReceiptKindV1.SUM_PROTOCOL_CAPABILITY_REJECTED
                ),
            )
            self._protocol_fail("reservation changed after issuance")
        current = self._active_reservations.get(seal.reservation_id)
        if (
            seal.session_id != self._session_id
            or seal.profile_id != self._profile_id
            or current is not value
        ):
            self._protocol_fail("reservation is foreign, stale, or already settled")
        return seal

    def commit_sum(
        self, reservation: SharedCapReservationV1, *, actual_amount: int | None = None
    ) -> SharedCapAdmissionReceiptV1:
        """Commit actual bytes/events and atomically refund unused reservation."""

        with self._public_lock_unchecked():
            self._assert_live_session()
            if self._state not in (
                SharedCapSessionStateV1.CONSTRUCTION_ACTIVE,
                SharedCapSessionStateV1.CAP_EXHAUSTED,
            ):
                self._protocol_fail("reservation settlement is out of order")
            seal = self._reservation(reservation)
            if actual_amount is None:
                actual = seal.amount
            else:
                try:
                    actual = _nonnegative(actual_amount, "actual SUM amount")
                except ConstructionSharedCapAuthorityV1Error as error:
                    self._conservatively_settle_reservation(
                        seal,
                        receipt_kind=(
                            SharedCapReceiptKindV1.SUM_PROTOCOL_CAPABILITY_REJECTED
                        ),
                    )
                    self._protocol_fail("invalid runtime actual SUM amount", error)
            if actual > seal.amount:
                self._conservatively_settle_reservation(
                    seal,
                    receipt_kind=(
                        SharedCapReceiptKindV1.SUM_PROTOCOL_CAPABILITY_REJECTED
                    ),
                )
                self._protocol_fail("actual SUM amount exceeds its prior reservation")
            path = seal.path
            before = self._sum_committed[path] + self._sum_reserved[path]
            self._sum_reserved[path] -= seal.amount
            self._sum_committed[path] += actual
            after = self._sum_committed[path] + self._sum_reserved[path]
            self._active_reservations.pop(seal.reservation_id)
            self._settled_reservations.add(seal.reservation_id)
            refund = seal.amount - actual
            return self._append_receipt(
                kind=(
                    SharedCapReceiptKindV1.SUM_REFUNDED
                    if actual == 0
                    else SharedCapReceiptKindV1.SUM_COMMITTED
                ),
                path=path,
                site_id=seal.site_id,
                reducer=ReducerEnum.SUM,
                requested=seal.amount,
                committed=actual,
                refunded=refund,
                value_before=before,
                value_after=after,
                retained_peak=max(before, after),
                control_before=self._control_cap_checks,
                control_delta=0,
                accepted=True,
            )

    def refund_sum(
        self, reservation: SharedCapReservationV1
    ) -> SharedCapAdmissionReceiptV1:
        with self._public_lock_unchecked():
            self._assert_live_session()
        return self.commit_sum(reservation, actual_amount=0)

    def _settle_callback_failure(
        self,
        reservation: SharedCapReservationV1,
        callback_error: BaseException,
    ) -> None:
        """Conservatively charge the full reserve for an exception outcome."""

        # Never trust ``self._lock`` or mutable accounting containers after an
        # arbitrary callback ran.  The retained issuer lock and runtime seal
        # are the authority.  If replay detects corruption, _assert_live_session
        # restores the last trusted runtime and its protocol transition fully
        # settles every outstanding reservation; do not attempt a second
        # settlement in that branch.
        with self._public_lock_unchecked():
            try:
                self._assert_live_session()
                self._assert_receipts_current()
            except SharedCapProtocolFailureV1:
                raise SharedCapProtocolFailureV1(
                    "shared-cap callback corrupted its admission session"
                ) from callback_error
            if self._state is not SharedCapSessionStateV1.CONSTRUCTION_ACTIVE:
                try:
                    self._protocol_fail(
                        "shared-cap callback terminated its admission session"
                    )
                except SharedCapProtocolFailureV1:
                    raise SharedCapProtocolFailureV1(
                        "shared-cap callback terminated its admission session"
                    ) from callback_error
            try:
                seal = self._reservation(reservation)
            except SharedCapProtocolFailureV1:
                # _reservation has already used the retained capability seal
                # to commit the full reservation and transitioned the session.
                # Preserve the callback exception as the public causal root
                # without attempting a second settlement.
                raise SharedCapProtocolFailureV1(
                    "shared-cap callback corrupted its active reservation"
                ) from callback_error
            # An exception carries no independently replayable byte/event
            # result.  Charge the entire admitted upper; exact partial reads
            # are represented only by a successful returned ``bytes`` value.
            actual = seal.amount
            before = self._sum_committed[seal.path] + self._sum_reserved[seal.path]
            self._sum_reserved[seal.path] -= seal.amount
            self._sum_committed[seal.path] += actual
            after = self._sum_committed[seal.path] + self._sum_reserved[seal.path]
            self._active_reservations.pop(seal.reservation_id)
            self._settled_reservations.add(seal.reservation_id)
            self._append_receipt(
                kind=SharedCapReceiptKindV1.SUM_CALLBACK_FAILED,
                path=seal.path,
                site_id=seal.site_id,
                reducer=ReducerEnum.SUM,
                requested=seal.amount,
                committed=actual,
                refunded=seal.amount - actual,
                value_before=before,
                value_after=after,
                retained_peak=max(before, after),
                control_before=self._control_cap_checks,
                control_delta=0,
                accepted=False,
                terminal_code=SharedCapProtocolFailureV1.terminal_code,
            )
            self._transition_protocol_failed_unchecked()

    def _require_active_after_callback(self) -> None:
        with object.__getattribute__(self, "_lock"):
            self._assert_live_session()
            if self._state is not SharedCapSessionStateV1.CONSTRUCTION_ACTIVE:
                self._protocol_fail(
                    "shared-cap callback changed or terminated its admission session"
                )

    def run_sum_operation(
        self,
        path: str,
        amount: int,
        *,
        site_id: str,
        operation: Callable[[], T],
    ) -> T:
        with self._public_lock_unchecked():
            self._assert_live_session()
        reservation = self.reserve_sum(path, amount, site_id=site_id)
        try:
            result = operation()
        except BaseException as error:
            self._settle_callback_failure(reservation, error)
            raise
        self._require_active_after_callback()
        self.commit_sum(reservation)
        return result

    def bounded_read(
        self,
        maximum_bytes: int,
        *,
        site_id: str,
        reader: Callable[[int], bytes],
    ) -> bytes:
        """Reserve before read, cap the request, and refund unread bytes."""

        with self._public_lock_unchecked():
            self._assert_live_session()
        reservation = self.reserve_sum(
            READ_BYTES_PATH, maximum_bytes, site_id=site_id
        )
        try:
            result = reader(maximum_bytes)
        except BaseException as error:
            self._settle_callback_failure(reservation, error)
            raise
        self._require_active_after_callback()
        if type(result) is not bytes:
            error = SharedCapProtocolFailureV1(
                "bounded reader returned a non-bytes object"
            )
            self._settle_callback_failure(reservation, error)
            raise error
        if len(result) > maximum_bytes:
            with self._lock:
                seal = self._reservation(reservation)
                path = seal.path
                before = self._sum_committed[path] + self._sum_reserved[path]
                self._sum_reserved[path] -= seal.amount
                self._sum_committed[path] += len(result)
                after = self._sum_committed[path] + self._sum_reserved[path]
                self._active_reservations.pop(seal.reservation_id)
                self._settled_reservations.add(seal.reservation_id)
                self._append_receipt(
                    kind=SharedCapReceiptKindV1.SUM_PROTOCOL_OVERRETURN,
                    path=path,
                    site_id=seal.site_id,
                    reducer=ReducerEnum.SUM,
                    requested=seal.amount,
                    committed=len(result),
                    refunded=0,
                    value_before=before,
                    value_after=after,
                    retained_peak=max(before, after),
                    control_before=self._control_cap_checks,
                    control_delta=0,
                    accepted=False,
                    terminal_code=SharedCapProtocolFailureV1.terminal_code,
                )
                self._protocol_fail("bounded reader exceeded its admitted request")
        self.commit_sum(reservation, actual_amount=len(result))
        return result

    def stage_ingress(
        self,
        payload_bytes: int,
        *,
        site_id: str,
        ingress_kind: SandboxIngressKindV1,
        operation: Callable[[], T],
    ) -> T:
        """Charge only a named sandbox copy/bind; generic IPC is invalid."""

        with self._public_lock_unchecked():
            self._assert_live_session()
            if type(ingress_kind) is not SandboxIngressKindV1:
                self._protocol_fail(
                    "io.staged_bytes requires named sandbox COPY or BIND ingress"
                )
        reservation = self._reserve_sum(
            STAGED_BYTES_PATH, payload_bytes, site_id=site_id
        )
        try:
            result = operation()
        except BaseException as error:
            self._settle_callback_failure(reservation, error)
            raise
        self._require_active_after_callback()
        self.commit_sum(reservation)
        return result

    def admit_max(self, path: str, value: int, *, site_id: str) -> None:
        """Admit one retained MAX measurement (currently working bytes)."""

        with self._public_lock_unchecked():
            self._assert_live_session()
            value = self._runtime_nonnegative(value, "MAX observation")
            if path == MOUNTED_BYTES_PATH:
                self._protocol_fail(
                    "mounted bytes require unique-payload visibility admission"
                )
            row, control_before = self._begin_admission(
                path, site_id, ReducerEnum.MAX
            )
            before = self._max_values[path]
            if value > row.cap:
                self._reject_cap(
                    kind=SharedCapReceiptKindV1.MAX_REJECTED_CAP_EXHAUSTED,
                    row=row,
                    site_id=site_id,
                    requested=value,
                    current=before,
                    control_before=control_before,
                    retained_peak=before,
                )
            after = max(before, value)
            self._max_values[path] = after
            self._append_receipt(
                kind=SharedCapReceiptKindV1.MAX_ADMITTED,
                path=path,
                site_id=site_id,
                reducer=ReducerEnum.MAX,
                requested=value,
                committed=value,
                refunded=0,
                value_before=before,
                value_after=after,
                retained_peak=after,
                control_before=control_before,
                control_delta=1,
                accepted=True,
            )

    def open_mount_visibility(
        self, payload_id: str, payload_bytes: int, *, site_id: str
    ) -> SharedCapMountTokenV1:
        """Admit visibility using simultaneous distinct-payload MAX semantics."""

        with self._public_lock_unchecked():
            self._assert_live_session()
            payload_id = self._runtime_cid(payload_id, "mounted payload ID")
            payload_bytes = self._runtime_nonnegative(
                payload_bytes, "mounted payload bytes"
            )
            existing = self._mount_entries.get(payload_id)
            if existing is not None and existing[0] != payload_bytes:
                self._protocol_fail(
                    "one mounted payload identity was reused with different bytes"
                )
            row, control_before = self._begin_admission(
                MOUNTED_BYTES_PATH, site_id, ReducerEnum.MAX
            )
            proposed = (
                self._mounted_current_bytes
                if existing is not None
                else self._mounted_current_bytes + payload_bytes
            )
            if proposed > row.cap:
                self._reject_cap(
                    kind=SharedCapReceiptKindV1.MOUNT_REJECTED_CAP_EXHAUSTED,
                    row=row,
                    site_id=site_id,
                    requested=payload_bytes,
                    current=self._mounted_current_bytes,
                    control_before=control_before,
                    retained_peak=self._max_values[MOUNTED_BYTES_PATH],
                )
            token = SharedCapMountTokenV1(
                _MOUNT_TOKEN_ISSUER,
                self._session_id,
                self._profile_id,
                site_id,
                payload_id,
                payload_bytes,
                len(self._receipts) + 1,
            )
            token_id = token.token_id
            _LIVE_MOUNT_TOKENS[id(token)] = _MountTokenSealV1(
                token,
                canonical_json_bytes(token.to_document()),
                token_id,
                self._session_id,
                self._profile_id,
                site_id,
                payload_id,
                payload_bytes,
            )
            if existing is None:
                self._mount_entries[payload_id] = (payload_bytes, 1)
                self._mounted_current_bytes = proposed
            else:
                self._mount_entries[payload_id] = (payload_bytes, existing[1] + 1)
            before_peak = self._max_values[MOUNTED_BYTES_PATH]
            after_peak = max(before_peak, self._mounted_current_bytes)
            self._max_values[MOUNTED_BYTES_PATH] = after_peak
            self._mount_tokens[token_id] = token
            self._append_receipt(
                kind=SharedCapReceiptKindV1.MOUNT_OPENED,
                path=MOUNTED_BYTES_PATH,
                site_id=site_id,
                reducer=ReducerEnum.MAX,
                requested=payload_bytes,
                committed=payload_bytes if existing is None else 0,
                refunded=0,
                value_before=(
                    self._mounted_current_bytes - payload_bytes
                    if existing is None
                    else self._mounted_current_bytes
                ),
                value_after=self._mounted_current_bytes,
                retained_peak=after_peak,
                control_before=control_before,
                control_delta=1,
                accepted=True,
            )
            return token

    def _close_mount_seal(
        self,
        seal: _MountTokenSealV1,
        *,
        kind: SharedCapReceiptKindV1,
        accepted: bool,
        terminal_code: str | None,
    ) -> SharedCapAdmissionReceiptV1 | None:
        current = self._mount_tokens.get(seal.token_id)
        if current is not seal.capability:
            return None
        entry = self._mount_entries.get(seal.payload_id)
        if entry is None or entry[0] != seal.payload_bytes or entry[1] <= 0:
            self._protocol_fail("mount bookkeeping is missing or inconsistent")
        before = self._mounted_current_bytes
        payload_bytes, references = entry
        if references == 1:
            self._mount_entries.pop(seal.payload_id)
            self._mounted_current_bytes -= payload_bytes
        else:
            self._mount_entries[seal.payload_id] = (payload_bytes, references - 1)
        if self._mounted_current_bytes < 0:
            self._protocol_fail("mounted current bytes became negative")
        self._mount_tokens.pop(seal.token_id)
        self._closed_mount_tokens.add(seal.token_id)
        return self._append_receipt(
            kind=kind,
            path=MOUNTED_BYTES_PATH,
            site_id=seal.site_id,
            reducer=ReducerEnum.MAX,
            requested=seal.payload_bytes,
            committed=0,
            refunded=(payload_bytes if references == 1 else 0),
            value_before=before,
            value_after=self._mounted_current_bytes,
            retained_peak=self._max_values[MOUNTED_BYTES_PATH],
            control_before=self._control_cap_checks,
            control_delta=0,
            accepted=accepted,
            terminal_code=terminal_code,
        )

    def _mount_token_seal(self, value: Any) -> _MountTokenSealV1:
        if type(value) is not SharedCapMountTokenV1:
            self._protocol_fail("mount close used a foreign capability")
        seal = _LIVE_MOUNT_TOKENS.get(id(value))
        if seal is None or seal.capability is not value:
            self._protocol_fail("mount token is not a live issuer capability")
        if seal.session_id != self._session_id or seal.profile_id != self._profile_id:
            self._protocol_fail("mount token belongs to another cap session")
        try:
            current_bytes = canonical_json_bytes(value.to_document())
        except Exception as error:
            self._close_mount_seal(
                seal,
                kind=SharedCapReceiptKindV1.MOUNT_PROTOCOL_CAPABILITY_REJECTED,
                accepted=False,
                terminal_code=SharedCapProtocolFailureV1.terminal_code,
            )
            self._protocol_fail("mount token failed post-issuance identity replay", error)
        if not hmac.compare_digest(current_bytes, seal.canonical_bytes):
            self._close_mount_seal(
                seal,
                kind=SharedCapReceiptKindV1.MOUNT_PROTOCOL_CAPABILITY_REJECTED,
                accepted=False,
                terminal_code=SharedCapProtocolFailureV1.terminal_code,
            )
            self._protocol_fail("mount token changed after issuance")
        if self._mount_tokens.get(seal.token_id) is not value:
            self._protocol_fail("mount token is stale or already closed")
        return seal

    def close_mount_visibility(
        self, token: SharedCapMountTokenV1
    ) -> SharedCapAdmissionReceiptV1:
        with self._public_lock_unchecked():
            self._assert_live_session()
            if self._state not in (
                SharedCapSessionStateV1.CONSTRUCTION_ACTIVE,
                SharedCapSessionStateV1.CAP_EXHAUSTED,
                SharedCapSessionStateV1.PROTOCOL_FAILED,
            ):
                self._protocol_fail("mount close is out of order")
            seal = self._mount_token_seal(token)
            receipt = self._close_mount_seal(
                seal,
                kind=SharedCapReceiptKindV1.MOUNT_CLOSED,
                accepted=True,
                terminal_code=(
                    SharedCapProtocolFailureV1.terminal_code
                    if self._state is SharedCapSessionStateV1.PROTOCOL_FAILED
                    else None
                ),
            )
            if receipt is None:
                self._protocol_fail("mount token became stale during close")
            return receipt

    def snapshot(self) -> SharedCapSessionSnapshotV1:
        with self._public_lock_unchecked():
            self._assert_live_session()
            self._assert_receipts_current()
            shared_values = []
            for path in SHARED_RESOURCE_PATHS:
                if path in SUM_SHARED_RESOURCE_PATHS:
                    value = self._sum_committed[path]
                else:
                    value = self._max_values[path]
                shared_values.append((path, value))
            reservations = tuple(
                (path, self._sum_reserved[path])
                for path in SHARED_RESOURCE_PATHS
                if path in SUM_SHARED_RESOURCE_PATHS
            )
            result = SharedCapSessionSnapshotV1(
                _SNAPSHOT_ISSUER,
                self._session_id,
                self._profile_id,
                (
                    None
                    if self._decision_prerequisite is None
                    else self._decision_prerequisite.prerequisite_id
                ),
                self._state,
                self._terminal_code,
                tuple(shared_values),
                reservations,
                self._mounted_current_bytes,
                self._control_cap_checks,
                tuple(row.receipt_id for row in self._receipts),
            )
            snapshot_document = {
                **result._payload(),
                "shared_cap_snapshot_id": object.__getattribute__(
                    result, "_snapshot_id"
                ),
            }
            _LIVE_SNAPSHOTS[id(result)] = (
                result,
                canonical_json_bytes(snapshot_document),
            )
            return result

    def close(self) -> SharedCapSessionSnapshotV1:
        with self._public_lock_unchecked():
            self._assert_live_session()
            if self._state not in (
                SharedCapSessionStateV1.CONSTRUCTION_ACTIVE,
                SharedCapSessionStateV1.CAP_EXHAUSTED,
            ):
                self._protocol_fail("shared-cap session close is out of order")
            if self._active_reservations or self._mount_tokens:
                self._protocol_fail(
                    "shared-cap session cannot close with outstanding capabilities"
                )
            self._state = SharedCapSessionStateV1.CLOSED
            self._refresh_session_seal_unchecked()
            return self.snapshot()


def issue_construction_shared_cap_session_v1(
    profile: DirectFallbackSharedCapProfileV1,
) -> DirectFallbackSharedCapSessionV1:
    """Issue exactly one live budget session for one profile/route attempt."""

    _require_live_profile(profile)
    key = (profile.profile_id, profile.route_attempt_id)
    with _SESSION_ISSUANCE_LOCK:
        if key in _ISSUED_SESSION_KEYS:
            raise SharedCapProtocolFailureV1(
                "shared-cap budget session was already issued for this profile/attempt"
            )
        result = DirectFallbackSharedCapSessionV1(
            profile,
            _issuer=_SESSION_ISSUER,
        )
        _LIVE_SESSIONS[id(result)] = result._initial_issuer_seal_unchecked()
        _ISSUED_SESSION_KEYS[key] = result
        return result


__all__ = [
    "CONTROL_CAP_CHECKS_PATH",
    "ConstructionFallbackDecisionCandidateV1",
    "ConstructionFallbackDecisionPrerequisiteV1",
    "ConstructionSharedCapAuthorityV1Error",
    "DirectFallbackSharedCapProfileV1",
    "DirectFallbackSharedCapSessionV1",
    "MAX_SHARED_RESOURCE_PATHS",
    "PROPOSED_CONTRACT_VERSION",
    "PROFILE_KEY",
    "READ_BYTES_PATH",
    "SHARED_RESOURCE_PATHS",
    "STAGED_BYTES_PATH",
    "SUM_SHARED_RESOURCE_PATHS",
    "SandboxIngressKindV1",
    "SharedCapAdmissionReceiptV1",
    "SharedCapExhaustedV1",
    "SharedCapLimitV1",
    "SharedCapMountTokenV1",
    "SharedCapProtocolFailureV1",
    "SharedCapReceiptKindV1",
    "SharedCapReservationV1",
    "SharedCapSessionSnapshotV1",
    "SharedCapSessionStateV1",
    "freeze_construction_fallback_decision_candidate_v1",
    "freeze_construction_fallback_decision_prerequisite_v1",
    "freeze_direct_fallback_shared_cap_profile_v1",
    "issue_construction_shared_cap_session_v1",
]
