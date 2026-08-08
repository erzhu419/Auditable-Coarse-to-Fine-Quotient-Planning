"""H1-specific predecision shared-cap profile and live owner kernel (V2).

Contract 2.0.58 closes the missing owner *mechanics* for the nine shared
resource paths.  The cap profile is deliberately earlier than, and therefore
contains none of, ``DecisionPoint``, route-upper, route-decision, selected-route
or decision-freeze identities.  A production owner prepared by this module is
locked until a later exact operand/formal-route join activates it.

The implementation is not a sentinel: one issuer-retained kernel implements
reserve-before-callback admission, atomic receipt/event pairs, SUM and MAX
settlement, mount/output lifecycles, the complete BROKER+WORKER+BUSINESS memory
formula, and the exact WORKER-then-BUSINESS launch topology.  A domain-separated
construction exercise uses the same kernel so these mechanics can be tested
without issuing production execution authority or accounting evidence.

The construction domains used here are centrally registered and use the
normative ``SHA256(domain || 0x00 || canonical-json)`` rule.  That registration
does not activate production execution: the exact operand/formal-route join,
broker-owned native observations, cross-process persistent single-consumption
authority, and native ambiguity resolution remain explicit downstream
blockers.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import wraps
import copy
import hmac
import threading
from typing import Any, Callable, Mapping, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_SHARED_CAP_EVENT_V2_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_MEMORY_BINDING_V2_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_MOUNT_TOKEN_V2_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OUTPUT_TOKEN_V2_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_PROFILE_V2_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_RECEIPT_V2_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_RUNTIME_V2_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_SOURCE_MANIFEST_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.58"
PROFILE_KEY = "construction_k7_h1_shared_cap_owner_v2"

OFFICIAL_EXECUTION_ALLOWED = False
FORMAL_OPERAND_AUTHORITY_JOIN_PRESENT = False
FORMAL_ROUTE_AUTHORITY_JOIN_PRESENT = False
FORMAL_ACTUAL_COMPLIANCE_ELIGIBLE = False
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

PROFILE_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_PROFILE_V2_DOMAIN
SOURCE_MANIFEST_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_SOURCE_MANIFEST_V2_DOMAIN
RUNTIME_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_RUNTIME_V2_DOMAIN
RECEIPT_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_RECEIPT_V2_DOMAIN
EVENT_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_EVENT_V2_DOMAIN
MOUNT_TOKEN_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_MOUNT_TOKEN_V2_DOMAIN
OUTPUT_TOKEN_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_OUTPUT_TOKEN_V2_DOMAIN
MEMORY_BINDING_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_MEMORY_BINDING_V2_DOMAIN

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    PROFILE_DOMAIN,
    SOURCE_MANIFEST_DOMAIN,
    RUNTIME_DOMAIN,
    RECEIPT_DOMAIN,
    EVENT_DOMAIN,
    MOUNT_TOKEN_DOMAIN,
    OUTPUT_TOKEN_DOMAIN,
    MEMORY_BINDING_DOMAIN,
)
if len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS):
    raise RuntimeError("H1 shared-cap V2 domains are not role-separated")
if not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("H1 shared-cap V2 domains are not centrally registered")


SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)

EXACT_CHILD_LAUNCH_ORDER = ("WORKER", "BUSINESS")
EXACT_PROCESS_LAUNCH_UPPER = 2
EXACT_CONTROL_CAP_REJECTIONS_UPPER = 1

_FORBIDDEN_PROFILE_FIELDS = frozenset(
    {
        "decision_point_id",
        "DecisionPoint_id",
        "route_upper_id",
        "route_upper_bound_envelope_id",
        "route_decision_id",
        "marginal_route_decision_id",
        "selected_route",
        "route_decision_freeze_id",
        "route_decision_freeze_sequence",
    }
)


class ConstructionK7H1SharedCapOwnerV2Error(ValueError):
    """An H1 shared-cap profile, owner, reservation or lifecycle failed."""


class H1SharedCapExecutionLockedV2(ConstructionK7H1SharedCapOwnerV2Error):
    """Production side effects are forbidden before both formal joins."""

    failure_kind = "EXECUTION_LOCKED"
    terminal_classification_issued = False
    certificate_issued = False
    official_execution_allowed = False


class H1SharedCapProtocolFailureV2(ConstructionK7H1SharedCapOwnerV2Error):
    """An admitted callback or lifecycle violated the frozen protocol."""

    failure_kind = "SHARED_OWNER_PROTOCOL_FAILURE"
    terminal_classification_issued = False
    certificate_issued = False
    infeasibility_certified = False


class H1SharedCapExhaustedV2(ConstructionK7H1SharedCapOwnerV2Error):
    """One shared hard cap rejected work before its side effect."""

    failure_kind = "SHARED_CAP_EXHAUSTED"
    terminal_classification_issued = False
    certificate_issued = False
    infeasibility_certified = False


class H1SharedReducerV2(str, Enum):
    SUM = "SUM"
    MAX = "MAX"


class H1SharedOwnerModeV2(str, Enum):
    AWAITING_OPERAND_FORMAL_JOIN = "AWAITING_OPERAND_FORMAL_JOIN"
    CONSTRUCTION_EXERCISE_ONLY = "CONSTRUCTION_EXERCISE_ONLY"
    ACTIVE_AFTER_OPERAND_FORMAL_JOIN = "ACTIVE_AFTER_OPERAND_FORMAL_JOIN"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    CLOSED = "CLOSED"


class H1SharedIngressKindV2(str, Enum):
    COPY_INTO_EXECUTION_SANDBOX = "COPY_INTO_EXECUTION_SANDBOX"
    BIND_INTO_EXECUTION_SANDBOX = "BIND_INTO_EXECUTION_SANDBOX"


class H1SharedSettlementV2(str, Enum):
    EXACT_SUCCESS = "EXACT_SUCCESS"
    FULL_RESERVATION_ON_CALLBACK_FAILURE = "FULL_RESERVATION_ON_CALLBACK_FAILURE"
    LIFECYCLE_OPEN = "LIFECYCLE_OPEN"
    LIFECYCLE_CLOSE = "LIFECYCLE_CLOSE"
    PRELAUNCH_BINDING = "PRELAUNCH_BINDING"
    EXACT_FINALIZATION = "EXACT_FINALIZATION"
    OBSERVED_UPPER_BOUND_VIOLATION = "OBSERVED_UPPER_BOUND_VIOLATION"
    CAP_REJECTED_BEFORE_SIDE_EFFECT = "CAP_REJECTED_BEFORE_SIDE_EFFECT"


class H1SharedLifecycleTerminalV2(str, Enum):
    """Exact status of one reservation-backed terminal observation."""

    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    EXACT_SUCCESS = "EXACT_SUCCESS"
    FAILED_UPPER_ONLY = "FAILED_UPPER_ONLY"
    OBSERVED_UPPER_BOUND_VIOLATION = "OBSERVED_UPPER_BOUND_VIOLATION"


_SETTLED_LIFECYCLE_TERMINALS = frozenset(
    {
        H1SharedLifecycleTerminalV2.EXACT_SUCCESS,
        H1SharedLifecycleTerminalV2.FAILED_UPPER_ONLY,
        H1SharedLifecycleTerminalV2.OBSERVED_UPPER_BOUND_VIOLATION,
    }
)


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1SharedCapOwnerV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1SharedCapOwnerV2Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _content_id(domain: str, payload: Any) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("H1 shared-cap content domain is not declared")
    return content_id(domain, payload)


@dataclass(frozen=True, slots=True)
class H1SharedOwnerSiteV2:
    path: str
    family_key: str
    owner_role: str
    owner_method: str
    source_symbol: str
    reducer: H1SharedReducerV2
    lifecycle: str

    def __post_init__(self) -> None:
        if (
            self.path not in SHARED_RESOURCE_PATHS
            or type(self.family_key) is not str
            or not self.family_key.startswith("h1.shared.")
            or self.owner_role != "BROKER"
            or type(self.owner_method) is not str
            or not self.owner_method
            or type(self.source_symbol) is not str
            or not self.source_symbol.startswith(
                "acfqp.construction_k7_h1_shared_cap_owner_v2."
            )
            or type(self.lifecycle) is not str
            or not self.lifecycle
        ):
            _fail("H1 shared owner site is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "family_key": self.family_key,
            "owner_role": self.owner_role,
            "owner_method": self.owner_method,
            "source_symbol": self.source_symbol,
            "reducer": self.reducer.value,
            "lifecycle": self.lifecycle,
        }


def _owner_sites() -> tuple[H1SharedOwnerSiteV2, ...]:
    module = "acfqp.construction_k7_h1_shared_cap_owner_v2"
    S = H1SharedReducerV2.SUM
    M = H1SharedReducerV2.MAX
    rows = (
        ("common.hash_invocations", "hash", "record_hash_invocation", S,
         "ATOMIC_RESERVE_CALLBACK_SETTLE"),
        ("common.integrity_checks", "integrity", "record_integrity_check", S,
         "ATOMIC_RESERVE_CALLBACK_SETTLE"),
        ("common.protocol_checks", "protocol", "record_protocol_check", S,
         "ATOMIC_RESERVE_CALLBACK_SETTLE"),
        ("io.mounted_bytes_peak", "mount", "open_mounted_payload", M,
         "OPEN_BEFORE_VISIBILITY_CLOSE_AFTER_DESCENDANT_REAP"),
        ("io.output_bytes", "output", "begin_route_output", S,
         "WHOLE_ROUTE_RESERVE_BEFORE_FIRST_LAUNCH_EXACT_FINALIZE"),
        ("io.read_bytes", "read", "read_registered_payload", S,
         "RESERVE_BEFORE_READ_EXACT_RETURNED_BYTES"),
        ("io.staged_bytes", "stage", "stage_registered_payload", S,
         "RESERVE_BEFORE_NAMED_COPY_OR_BIND"),
        ("memory.working_bytes_peak", "memory", "bind_working_hierarchy", M,
         "BIND_ALL_THREE_ROLES_BEFORE_FIRST_POSTDECISION_SIDE_EFFECT"),
        ("process.launches", "launch", "launch_registered_role", S,
         "RESERVE_IMMEDIATELY_BEFORE_WORKER_THEN_BUSINESS_LAUNCH"),
    )
    return tuple(
        H1SharedOwnerSiteV2(
            path,
            f"h1.shared.{family}",
            "BROKER",
            method,
            f"{module}.H1SharedCapOwnerV2.{method}",
            reducer,
            lifecycle,
        )
        for path, family, method, reducer, lifecycle in rows
    )


OWNER_SITE_SPECS = _owner_sites()
_SITE_BY_PATH = {row.path: row for row in OWNER_SITE_SPECS}
LIFECYCLE_SOURCE_SYMBOLS = (
    "H1SharedCapOwnerV2.finalize_route_output",
    "H1SharedCapOwnerV2.close_mounted_payload",
    "H1SharedCapOwnerV2.mark_trusted_descendants_reaped",
    "H1SharedCapOwnerV2.read_working_bytes_peak",
    "H1SharedCapOwnerV2.close",
    "H1SharedCapOwnerV2.close_failed_cleanup",
)


_PROFILE_ISSUER = object()
_SOURCE_ISSUER = object()
_OWNER_ISSUER = object()
_TOKEN_ISSUER = object()

_LIVE_PROFILES: dict[int, tuple[object, bytes]] = {}
_LIVE_MANIFESTS: dict[int, tuple[object, bytes]] = {}
_LIVE_OWNERS: dict[int, tuple[object, "_OwnerStateV2", bytes]] = {}
_LIVE_MOUNT_TOKENS: dict[int, tuple[object, int, str, bytes]] = {}
_LIVE_OUTPUT_TOKENS: dict[int, tuple[object, int, bytes]] = {}
_LIVE_MEMORY_BINDINGS: dict[int, tuple[object, int, bytes]] = {}
_LIVE_PRODUCTION_RUNTIME_IDS: set[str] = set()
_LOCK = threading.RLock()


@dataclass(frozen=True, slots=True)
class H1SharedCapLimitV2:
    path: str
    reducer: H1SharedReducerV2
    hard_cap: int

    def __post_init__(self) -> None:
        site = _SITE_BY_PATH.get(self.path)
        if site is None or self.reducer is not site.reducer:
            _fail("H1 shared cap changed its registered path/reducer")
        _nonnegative(self.hard_cap, f"{self.path} hard cap")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "reducer": self.reducer.value,
            "hard_cap": self.hard_cap,
        }


@dataclass(frozen=True, slots=True)
class H1SharedCapProfileV2:
    _issuer: InitVar[object]
    predecision_context_id: str
    current_access_authority_id: str
    route_attempt_id: str
    execution_topology_profile_id: str
    source_archive_id: str
    limits: tuple[H1SharedCapLimitV2, ...]
    max_control_cap_checks: int
    control_cap_rejections_upper: int
    outer_hierarchy_cap: int
    broker_parent_cap: int
    worker_role_cap: int
    business_role_cap: int
    retained_memory_peak_ofd_plan_id: str
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("H1 shared-cap profile is caller-minted")
        for value, label in (
            (self.predecision_context_id, "predecision context"),
            (self.current_access_authority_id, "current-access authority"),
            (self.route_attempt_id, "route attempt"),
            (self.execution_topology_profile_id, "execution topology profile"),
            (self.source_archive_id, "source archive"),
            (self.retained_memory_peak_ofd_plan_id, "memory peak OFD plan"),
        ):
            _cid(value, label)
        if (
            type(self.limits) is not tuple
            or len(self.limits) != 9
            or tuple(row.path for row in self.limits) != SHARED_RESOURCE_PATHS
            or any(type(row) is not H1SharedCapLimitV2 for row in self.limits)
        ):
            _fail("H1 shared-cap profile requires the ordered nine limits")
        _positive(self.max_control_cap_checks, "max control cap checks")
        if self.control_cap_rejections_upper != EXACT_CONTROL_CAP_REJECTIONS_UPPER:
            _fail("H1 shared cap must reserve exactly one control rejection")
        for value, label in (
            (self.outer_hierarchy_cap, "outer hierarchy cap"),
            (self.broker_parent_cap, "broker parent cap"),
            (self.worker_role_cap, "worker role cap"),
            (self.business_role_cap, "business role cap"),
        ):
            _positive(value, label)
        if self.limit_for("process.launches").hard_cap != EXACT_PROCESS_LAUNCH_UPPER:
            _fail("H1 process launch hard cap must equal WORKER+BUSINESS=2")
        if self.memory_formula_upper <= 0:
            _fail("H1 complete-topology memory formula must be positive")
        object.__setattr__(
            self, "_profile_id", _content_id(PROFILE_DOMAIN, self._payload())
        )

    def limit_for(self, path: str) -> H1SharedCapLimitV2:
        if type(path) is not str or path not in _SITE_BY_PATH:
            _fail("unknown H1 shared path")
        return self.limits[SHARED_RESOURCE_PATHS.index(path)]

    @property
    def memory_formula_upper(self) -> int:
        return min(
            self.limit_for("memory.working_bytes_peak").hard_cap,
            self.outer_hierarchy_cap,
            self.broker_parent_cap + self.worker_role_cap + self.business_role_cap,
        )

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.construction_k7_h1_shared_cap_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "predecision_context_id": self.predecision_context_id,
            "production_current_access_authority_id": (
                self.current_access_authority_id
            ),
            "route_attempt_id": self.route_attempt_id,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "source_archive_id": self.source_archive_id,
            "limits": [row.to_document() for row in self.limits],
            "max_control_cap_checks": self.max_control_cap_checks,
            "control_cap_rejections_upper": self.control_cap_rejections_upper,
            "memory_topology": {
                "outer_hierarchy_cap": self.outer_hierarchy_cap,
                "broker_parent_cap": self.broker_parent_cap,
                "worker_role_cap": self.worker_role_cap,
                "business_role_cap": self.business_role_cap,
                "roles_covered": ["BROKER", "WORKER", "BUSINESS"],
                "formula": "MIN(HARD_CAP,OUTER,BROKER_PARENT+WORKER+BUSINESS)",
                "formula_upper": self.memory_formula_upper,
                "retained_same_ofd_memory_peak_plan_id": (
                    self.retained_memory_peak_ofd_plan_id
                ),
            },
            "child_launch_order": list(EXACT_CHILD_LAUNCH_ORDER),
            "process_launches_upper": EXACT_PROCESS_LAUNCH_UPPER,
            "profile_frozen_predecision": True,
            "formal_operand_authority_join_present": False,
            "formal_route_authority_join_present": False,
            "production_execution_authorized": False,
            "formal_actual_compliance_eligible": False,
            "official_execution_allowed": False,
        }
        if set(payload) & _FORBIDDEN_PROFILE_FIELDS:
            _fail("H1 shared-cap profile contains a future decision field")
        return payload

    @property
    def profile_id(self) -> str:
        _require_profile(self)
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_shared_cap_profile_id": self._profile_id}


def freeze_h1_shared_cap_profile_v2(
    *,
    predecision_context_id: str,
    current_access_authority_id: str,
    route_attempt_id: str,
    execution_topology_profile_id: str,
    source_archive_id: str,
    hard_caps: Mapping[str, int],
    max_control_cap_checks: int,
    outer_hierarchy_cap: int,
    broker_parent_cap: int,
    worker_role_cap: int,
    business_role_cap: int,
    retained_memory_peak_ofd_plan_id: str,
) -> H1SharedCapProfileV2:
    if type(hard_caps) is not dict or set(hard_caps) != set(SHARED_RESOURCE_PATHS):
        _fail("H1 shared hard caps must cover exactly the nine paths")
    limits = tuple(
        H1SharedCapLimitV2(
            site.path,
            site.reducer,
            _nonnegative(hard_caps[site.path], f"{site.path} hard cap"),
        )
        for site in OWNER_SITE_SPECS
    )
    value = H1SharedCapProfileV2(
        _PROFILE_ISSUER,
        _cid(predecision_context_id, "predecision context"),
        _cid(current_access_authority_id, "current-access authority"),
        _cid(route_attempt_id, "route attempt"),
        _cid(execution_topology_profile_id, "execution topology profile"),
        _cid(source_archive_id, "source archive"),
        limits,
        _positive(max_control_cap_checks, "max control cap checks"),
        EXACT_CONTROL_CAP_REJECTIONS_UPPER,
        _positive(outer_hierarchy_cap, "outer hierarchy cap"),
        _positive(broker_parent_cap, "broker parent cap"),
        _positive(worker_role_cap, "worker role cap"),
        _positive(business_role_cap, "business role cap"),
        _cid(retained_memory_peak_ofd_plan_id, "memory peak OFD plan"),
    )
    raw = canonical_json_bytes(value.to_document())
    with _LOCK:
        _LIVE_PROFILES[id(value)] = (value, raw)
    return value


def _require_profile(value: Any) -> H1SharedCapProfileV2:
    if type(value) is not H1SharedCapProfileV2:
        _fail("H1 shared-cap profile has a foreign type")
    with _LOCK:
        retained = _LIVE_PROFILES.get(id(value))
    if retained is None or retained[0] is not value:
        _fail("H1 shared-cap profile is not issuer retained")
    current = canonical_json_bytes(value.to_document())
    if not hmac.compare_digest(current, retained[1]):
        _fail("H1 shared-cap profile changed after issuance")
    if set(value.to_document()) & _FORBIDDEN_PROFILE_FIELDS:
        _fail("H1 shared-cap profile acquired a future decision field")
    return value


@dataclass(frozen=True, slots=True)
class H1SharedCapSourceManifestV2:
    _issuer: InitVar[object]
    source_archive_id: str
    execution_topology_profile_id: str
    sites: tuple[H1SharedOwnerSiteV2, ...]
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SOURCE_ISSUER
            or self.sites != OWNER_SITE_SPECS
        ):
            _fail("H1 shared-cap source manifest is issuer-owned and exact")
        _cid(self.source_archive_id, "source archive")
        _cid(self.execution_topology_profile_id, "execution topology profile")
        object.__setattr__(
            self,
            "_manifest_id",
            _content_id(SOURCE_MANIFEST_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_shared_cap_source_manifest.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_archive_id": self.source_archive_id,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "sites": [row.to_document() for row in self.sites],
            "lifecycle_source_symbols": [
                f"acfqp.construction_k7_h1_shared_cap_owner_v2.{symbol}"
                for symbol in LIFECYCLE_SOURCE_SYMBOLS
            ],
            "site_count": 9,
            "manifest_role": "STRUCTURAL_OWNER_SITE_MANIFEST",
            "source_bytes_bound": False,
            "normalized_ast_bound": False,
            "loaded_symbol_semantics_verified": False,
            "symbol_rows_are_structural_declarations": True,
            "production_source_authority_present": False,
            "owner_role": "BROKER",
            "issuer_retained_owner_kernel_required": True,
            "reserve_before_side_effect_required": True,
            "caller_selectable_path_allowed": False,
            "sentinel_owner_allowed": False,
            "production_execution_authorized": False,
        }

    @property
    def manifest_id(self) -> str:
        _require_manifest(self)
        return self._manifest_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_shared_cap_source_manifest_id": self._manifest_id}


def freeze_h1_shared_cap_source_manifest_v2(
    *, source_archive_id: str, execution_topology_profile_id: str
) -> H1SharedCapSourceManifestV2:
    value = H1SharedCapSourceManifestV2(
        _SOURCE_ISSUER,
        _cid(source_archive_id, "source archive"),
        _cid(execution_topology_profile_id, "execution topology profile"),
        OWNER_SITE_SPECS,
    )
    with _LOCK:
        _LIVE_MANIFESTS[id(value)] = (
            value,
            canonical_json_bytes(value.to_document()),
        )
    return value


def _require_manifest(value: Any) -> H1SharedCapSourceManifestV2:
    if type(value) is not H1SharedCapSourceManifestV2:
        _fail("H1 shared-cap source manifest has a foreign type")
    with _LOCK:
        retained = _LIVE_MANIFESTS.get(id(value))
    if retained is None or retained[0] is not value:
        _fail("H1 shared-cap source manifest is not issuer retained")
    current = canonical_json_bytes(value.to_document())
    if not hmac.compare_digest(current, retained[1]):
        _fail("H1 shared-cap source manifest changed after issuance")
    return value


@dataclass(frozen=True, slots=True)
class H1SharedMountTokenV2:
    _issuer: InitVar[object]
    owner_runtime_id: str
    payload_identity_id: str
    extent: int
    open_sequence: int
    token_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TOKEN_ISSUER:
            _fail("H1 shared mount token is caller-minted")
        _cid(self.owner_runtime_id, "owner runtime")
        _cid(self.payload_identity_id, "payload identity")
        _positive(self.extent, "mounted extent")
        _positive(self.open_sequence, "mount open sequence")
        object.__setattr__(
            self,
            "token_id",
            _content_id(MOUNT_TOKEN_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_shared_mount_token.v2",
            "owner_runtime_id": self.owner_runtime_id,
            "payload_identity_id": self.payload_identity_id,
            "extent": self.extent,
            "open_sequence": self.open_sequence,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "mount_token_id": self.token_id}


@dataclass(frozen=True, slots=True)
class H1SharedOutputTokenV2:
    _issuer: InitVar[object]
    owner_runtime_id: str
    reserved_fixed_point_bytes: int
    token_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TOKEN_ISSUER:
            _fail("H1 shared output token is caller-minted")
        _cid(self.owner_runtime_id, "owner runtime")
        _nonnegative(self.reserved_fixed_point_bytes, "output fixed point")
        object.__setattr__(
            self,
            "token_id",
            _content_id(OUTPUT_TOKEN_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_shared_output_token.v2",
            "owner_runtime_id": self.owner_runtime_id,
            "reserved_fixed_point_bytes": self.reserved_fixed_point_bytes,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_token_id": self.token_id}


@dataclass(frozen=True, slots=True)
class H1SharedMemoryBindingV2:
    _issuer: InitVar[object]
    owner_runtime_id: str
    retained_memory_peak_ofd_plan_id: str
    formula_upper: int
    binding_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TOKEN_ISSUER:
            _fail("H1 shared memory binding is caller-minted")
        _cid(self.owner_runtime_id, "owner runtime")
        _cid(self.retained_memory_peak_ofd_plan_id, "memory peak OFD plan")
        _positive(self.formula_upper, "memory formula upper")
        object.__setattr__(
            self,
            "binding_id",
            _content_id(MEMORY_BINDING_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_shared_memory_binding.v2",
            "owner_runtime_id": self.owner_runtime_id,
            "retained_same_ofd_memory_peak_plan_id": (
                self.retained_memory_peak_ofd_plan_id
            ),
            "formula": "MIN(HARD_CAP,OUTER,BROKER_PARENT+WORKER+BUSINESS)",
            "roles_covered": ["BROKER", "WORKER", "BUSINESS"],
            "formula_upper": self.formula_upper,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "memory_binding_id": self.binding_id}


@dataclass(slots=True)
class _OwnerStateV2:
    mode: H1SharedOwnerModeV2
    sequence: int
    actual: dict[str, int]
    outstanding: dict[str, int]
    cap_checks: int
    cap_rejections: int
    receipts: list[dict[str, Any]]
    events: list[dict[str, Any]]
    active_mounts: dict[str, tuple[int, int]]
    active_mount_tokens: set[int]
    ambiguous_mount_opens: dict[str, int]
    mounted_current: int
    output_reserved: int | None
    output_finalized: bool
    output_terminal: H1SharedLifecycleTerminalV2
    memory_bound: bool
    memory_observed: bool
    memory_peak_terminal: H1SharedLifecycleTerminalV2
    descendants_reaped: bool
    reap_pidfd_observation_ids: dict[str, str]
    launch_order: list[str]
    formal_operand_authority_id: str | None
    formal_route_authority_id: str | None
    operation_in_flight: bool
    mutation_violation_count: int
    cleanup_closed: bool
    operation_start_mode: H1SharedOwnerModeV2 | None
    operation_start_violation_count: int
    ambiguous_memory_binding: bool
    ambiguous_launch_role: str | None
    failure_cause_chain: list[dict[str, Any]]
    operation_start_failure_count: int


@dataclass(frozen=True, slots=True)
class H1SharedCapOwnerV2:
    """Opaque issuer-owned handle whose methods delegate to one retained kernel."""

    _issuer: InitVar[object]
    profile_id: str
    source_manifest_id: str
    runtime_id: str
    construction_exercise: bool

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OWNER_ISSUER:
            _fail("H1 shared-cap owner handle is caller-minted")
        _cid(self.profile_id, "shared-cap profile")
        _cid(self.source_manifest_id, "shared-cap source manifest")
        _cid(self.runtime_id, "shared-cap runtime")
        if type(self.construction_exercise) is not bool:
            _fail("H1 shared-cap owner mode is malformed")

    def record_hash_invocation(self, callback: Callable[[], Any]) -> Any:
        return _run_unit_sum(self, "common.hash_invocations", callback)

    def record_integrity_check(self, callback: Callable[[], Any]) -> Any:
        return _run_unit_sum(self, "common.integrity_checks", callback)

    def record_protocol_check(self, callback: Callable[[], Any]) -> Any:
        return _run_unit_sum(self, "common.protocol_checks", callback)

    def read_registered_payload(
        self, reserved_bytes: int, callback: Callable[[], bytes]
    ) -> bytes:
        reserved = _nonnegative(reserved_bytes, "read reservation")
        return _run_sum_bytes(self, "io.read_bytes", reserved, callback)

    def stage_registered_payload(
        self,
        reserved_bytes: int,
        ingress_kind: H1SharedIngressKindV2,
        callback: Callable[[], int],
    ) -> int:
        try:
            kind = H1SharedIngressKindV2(ingress_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1SharedCapOwnerV2Error(
                "H1 staged ingress kind is invalid"
            ) from error
        return _run_sum_int(
            self,
            "io.staged_bytes",
            _nonnegative(reserved_bytes, "stage reservation"),
            callback,
            detail={"ingress_kind": kind.value},
        )

    def bind_working_hierarchy(
        self, callback: Callable[[H1SharedMemoryBindingV2], Any]
    ) -> H1SharedMemoryBindingV2:
        return _bind_memory(self, callback)

    def begin_route_output(self) -> H1SharedOutputTokenV2:
        return _begin_output(self)

    def finalize_route_output(
        self,
        token: H1SharedOutputTokenV2,
        actual_output_bytes: int,
        callback: Callable[[], Any],
    ) -> Any:
        return _finalize_output(self, token, actual_output_bytes, callback)

    def open_mounted_payload(
        self,
        payload_identity_id: str,
        extent: int,
        callback: Callable[[], Any],
    ) -> H1SharedMountTokenV2:
        return _open_mount(self, payload_identity_id, extent, callback)

    def close_mounted_payload(
        self, token: H1SharedMountTokenV2, callback: Callable[[], Any]
    ) -> Any:
        return _close_mount(self, token, callback)

    def launch_registered_role(
        self, role: str, callback: Callable[[], Any]
    ) -> Any:
        return _launch_role(self, role, callback)

    def mark_trusted_descendants_reaped(
        self,
        *,
        worker_pidfd_observation_id: str | None,
        business_pidfd_observation_id: str | None,
        retained_memory_peak_ofd_plan_id: str,
    ) -> None:
        _mark_reaped(
            self,
            worker_pidfd_observation_id,
            business_pidfd_observation_id,
            retained_memory_peak_ofd_plan_id,
        )

    def read_working_bytes_peak(self, callback: Callable[[], int]) -> int:
        return _read_memory_peak(self, callback)

    def close(self) -> None:
        _close_owner(self)

    def close_failed_cleanup(self) -> None:
        _close_failed_owner(self)

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_shared_cap_owner_handle.v2",
            "schema_version": SCHEMA_VERSION,
            "h1_shared_cap_profile_id": self.profile_id,
            "h1_shared_cap_source_manifest_id": self.source_manifest_id,
            "h1_shared_cap_runtime_id": self.runtime_id,
            "construction_exercise": self.construction_exercise,
        }


def _owner_runtime_payload(
    profile: H1SharedCapProfileV2,
    manifest: H1SharedCapSourceManifestV2,
    *,
    construction_exercise: bool,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_k7_h1_shared_cap_runtime.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "h1_shared_cap_profile_id": profile.profile_id,
        "h1_shared_cap_source_manifest_id": manifest.manifest_id,
        "predecision_context_id": profile.predecision_context_id,
        "production_current_access_authority_id": profile.current_access_authority_id,
        "route_attempt_id": profile.route_attempt_id,
        "construction_exercise": construction_exercise,
        "initial_mode": (
            H1SharedOwnerModeV2.CONSTRUCTION_EXERCISE_ONLY.value
            if construction_exercise
            else H1SharedOwnerModeV2.AWAITING_OPERAND_FORMAL_JOIN.value
        ),
        "real_owner_kernel_present": True,
        "sentinel_owner": False,
        "production_execution_authorized": False,
        "formal_operand_authority_join_present": False,
        "formal_route_authority_join_present": False,
        "official_execution_allowed": False,
    }


def _prepare_owner(
    profile: H1SharedCapProfileV2,
    source_manifest: H1SharedCapSourceManifestV2,
    *,
    construction_exercise: bool,
) -> H1SharedCapOwnerV2:
    profile = _require_profile(profile)
    source_manifest = _require_manifest(source_manifest)
    if (
        profile.source_archive_id != source_manifest.source_archive_id
        or profile.execution_topology_profile_id
        != source_manifest.execution_topology_profile_id
    ):
        _fail("H1 shared-cap profile/source manifest identity mismatch")
    runtime_id = _content_id(
        RUNTIME_DOMAIN,
        _owner_runtime_payload(
            profile, source_manifest, construction_exercise=construction_exercise
        ),
    )
    value = H1SharedCapOwnerV2(
        _OWNER_ISSUER,
        profile.profile_id,
        source_manifest.manifest_id,
        runtime_id,
        construction_exercise,
    )
    state = _OwnerStateV2(
        mode=(
            H1SharedOwnerModeV2.CONSTRUCTION_EXERCISE_ONLY
            if construction_exercise
            else H1SharedOwnerModeV2.AWAITING_OPERAND_FORMAL_JOIN
        ),
        sequence=0,
        actual={path: 0 for path in SHARED_RESOURCE_PATHS},
        outstanding={path: 0 for path in SHARED_RESOURCE_PATHS},
        cap_checks=0,
        cap_rejections=0,
        receipts=[],
        events=[],
        active_mounts={},
        active_mount_tokens=set(),
        ambiguous_mount_opens={},
        mounted_current=0,
        output_reserved=None,
        output_finalized=False,
        output_terminal=H1SharedLifecycleTerminalV2.NOT_STARTED,
        memory_bound=False,
        memory_observed=False,
        memory_peak_terminal=H1SharedLifecycleTerminalV2.NOT_STARTED,
        descendants_reaped=False,
        reap_pidfd_observation_ids={},
        launch_order=[],
        formal_operand_authority_id=None,
        formal_route_authority_id=None,
        operation_in_flight=False,
        mutation_violation_count=0,
        cleanup_closed=False,
        operation_start_mode=None,
        operation_start_violation_count=0,
        ambiguous_memory_binding=False,
        ambiguous_launch_role=None,
        failure_cause_chain=[],
        operation_start_failure_count=0,
    )
    with _LOCK:
        if not construction_exercise and runtime_id in _LIVE_PRODUCTION_RUNTIME_IDS:
            _fail("one H1 production shared-cap runtime may be prepared only once")
        _LIVE_OWNERS[id(value)] = (
            value,
            state,
            canonical_json_bytes(value.to_document()),
        )
        if not construction_exercise:
            _LIVE_PRODUCTION_RUNTIME_IDS.add(runtime_id)
    return value


def prepare_h1_shared_cap_owner_v2(
    *,
    profile: H1SharedCapProfileV2,
    source_manifest: H1SharedCapSourceManifestV2,
) -> H1SharedCapOwnerV2:
    """Prepare a real, but production-locked, owner awaiting both joins."""

    return _prepare_owner(profile, source_manifest, construction_exercise=False)


def prepare_h1_shared_cap_owner_construction_exercise_v2(
    *,
    profile: H1SharedCapProfileV2,
    source_manifest: H1SharedCapSourceManifestV2,
) -> H1SharedCapOwnerV2:
    """Exercise the exact kernel without minting production evidence."""

    return _prepare_owner(profile, source_manifest, construction_exercise=True)


def _require_owner(
    value: Any, *, operable: bool = False
) -> tuple[H1SharedCapOwnerV2, _OwnerStateV2, H1SharedCapProfileV2]:
    if type(value) is not H1SharedCapOwnerV2:
        _fail("H1 shared-cap owner has a foreign type")
    with _LOCK:
        retained = _LIVE_OWNERS.get(id(value))
    if retained is None or retained[0] is not value:
        _fail("H1 shared-cap owner is not issuer retained")
    if not hmac.compare_digest(canonical_json_bytes(value.to_document()), retained[2]):
        _fail("H1 shared-cap owner handle changed after issuance")
    with _LOCK:
        profile_retained = next(
            (
                row
                for row in _LIVE_PROFILES.values()
                if row[0].profile_id == value.profile_id
            ),
            None,
        )
    if profile_retained is None:
        _fail("H1 shared-cap owner lost its retained profile")
    profile = _require_profile(profile_retained[0])
    state = retained[1]
    if operable:
        if state.mode is H1SharedOwnerModeV2.AWAITING_OPERAND_FORMAL_JOIN:
            raise H1SharedCapExecutionLockedV2(
                "shared owner awaits exact operand and formal-route joins"
            )
        if state.mode is H1SharedOwnerModeV2.CAP_EXHAUSTED:
            raise H1SharedCapExhaustedV2("H1 shared owner is cap exhausted")
        if state.mode in {
            H1SharedOwnerModeV2.PROTOCOL_FAILURE,
            H1SharedOwnerModeV2.CLOSED,
        }:
            raise H1SharedCapProtocolFailureV2(
                f"H1 shared owner is not operable: {state.mode.value}"
            )
    return value, state, profile


_FAILURE_MODES = frozenset(
    {
        H1SharedOwnerModeV2.CAP_EXHAUSTED,
        H1SharedOwnerModeV2.PROTOCOL_FAILURE,
    }
)


def _append_failure_cause(
    state: _OwnerStateV2,
    *,
    observed_mode: H1SharedOwnerModeV2,
    cleanup_phase: bool,
    operation: str,
    exception_type: str,
    message: str,
) -> None:
    """Append one ordered cause while preserving the first terminal mode."""

    if observed_mode not in _FAILURE_MODES:
        observed_mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
    ordinal = len(state.failure_cause_chain) + 1
    if ordinal == 1:
        primary_mode = observed_mode
        kind = "PRIMARY"
    else:
        primary_mode = H1SharedOwnerModeV2(
            state.failure_cause_chain[0]["observed_mode"]
        )
        kind = "SECONDARY"
    state.failure_cause_chain.append(
        {
            "ordinal": ordinal,
            "kind": kind,
            "cleanup_phase": cleanup_phase,
            "observed_mode": observed_mode.value,
            "preserved_primary_mode": primary_mode.value,
            "operation": operation,
            "exception_type": exception_type,
            "message": message,
        }
    )
    state.mode = primary_mode


def _validate_failure_cause_chain(state: _OwnerStateV2) -> None:
    chain = state.failure_cause_chain
    if not chain:
        if state.mode in _FAILURE_MODES:
            _fail("failed H1 shared owner lacks its primary failure cause")
        return
    primary_mode = chain[0].get("observed_mode")
    if primary_mode not in {
        H1SharedOwnerModeV2.CAP_EXHAUSTED.value,
        H1SharedOwnerModeV2.PROTOCOL_FAILURE.value,
    }:
        _fail("H1 shared owner primary failure mode is invalid")
    for ordinal, cause in enumerate(chain, start=1):
        if (
            type(cause) is not dict
            or cause.get("ordinal") != ordinal
            or cause.get("kind")
            != ("PRIMARY" if ordinal == 1 else "SECONDARY")
            or type(cause.get("cleanup_phase")) is not bool
            or cause.get("preserved_primary_mode") != primary_mode
            or cause.get("observed_mode")
            not in {
                H1SharedOwnerModeV2.CAP_EXHAUSTED.value,
                H1SharedOwnerModeV2.PROTOCOL_FAILURE.value,
            }
            or type(cause.get("operation")) is not str
            or not cause["operation"]
            or type(cause.get("exception_type")) is not str
            or not cause["exception_type"]
            or type(cause.get("message")) is not str
            or not cause["message"]
        ):
            _fail("H1 shared owner failure cause chain is malformed")
    if state.mode in _FAILURE_MODES and state.mode.value != primary_mode:
        _fail("H1 shared owner did not preserve its primary failure mode")


def _serialized_operation_wrapper(
    function: Callable[..., Any], *, allow_failure_cleanup: bool
) -> Callable[..., Any]:
    """Serialize one mutation and reject callback reentrancy before effects."""

    @wraps(function)
    def wrapped(
        owner: H1SharedCapOwnerV2, *args: Any, **kwargs: Any
    ) -> Any:
        # The construction RLock deliberately stays held across the callback.
        # A read-only snapshot in the same thread remains possible; a
        # same-owner mutation in that callback is rejected by the in-flight
        # bit.  This does not claim cross-owner non-reentrancy or broker-native
        # cross-thread liveness.
        with _LOCK:
            _, state, _ = _require_owner(owner)
            if state.operation_in_flight:
                state.mutation_violation_count += 1
                _append_failure_cause(
                    state,
                    observed_mode=H1SharedOwnerModeV2.PROTOCOL_FAILURE,
                    cleanup_phase=allow_failure_cleanup,
                    operation=function.__name__,
                    exception_type=H1SharedCapProtocolFailureV2.__name__,
                    message="same-owner callback reentrancy is forbidden",
                )
                raise H1SharedCapProtocolFailureV2(
                    "same-owner callback reentrancy is forbidden"
                )
            if state.cleanup_closed or state.mode is H1SharedOwnerModeV2.CLOSED:
                raise H1SharedCapProtocolFailureV2(
                    "shared owner is already closed"
                )
            if (
                state.output_terminal in _SETTLED_LIFECYCLE_TERMINALS
                and function.__name__ not in {
                    "_close_owner",
                    "_close_failed_owner",
                }
            ):
                _append_failure_cause(
                    state,
                    observed_mode=H1SharedOwnerModeV2.PROTOCOL_FAILURE,
                    cleanup_phase=allow_failure_cleanup,
                    operation=function.__name__,
                    exception_type=H1SharedCapProtocolFailureV2.__name__,
                    message=(
                        "no resource mutation is allowed after terminal output "
                        "settlement"
                    ),
                )
                raise H1SharedCapProtocolFailureV2(
                    "no resource mutation is allowed after terminal output settlement"
                )
            if state.mode is H1SharedOwnerModeV2.AWAITING_OPERAND_FORMAL_JOIN:
                raise H1SharedCapExecutionLockedV2(
                    "shared owner awaits exact operand and formal-route joins"
                )
            failed = state.mode in {
                H1SharedOwnerModeV2.CAP_EXHAUSTED,
                H1SharedOwnerModeV2.PROTOCOL_FAILURE,
            }
            if failed and not allow_failure_cleanup:
                if state.mode is H1SharedOwnerModeV2.CAP_EXHAUSTED:
                    raise H1SharedCapExhaustedV2(
                        "H1 shared owner is cap exhausted"
                    )
                raise H1SharedCapProtocolFailureV2(
                    "H1 shared owner is in protocol failure"
                )
            starting_mode = state.mode
            starting_violations = state.mutation_violation_count
            state.operation_in_flight = True
            state.operation_start_mode = starting_mode
            state.operation_start_violation_count = starting_violations
            state.operation_start_failure_count = len(state.failure_cause_chain)
            try:
                result = function(owner, *args, **kwargs)
                if state.mutation_violation_count != starting_violations:
                    raise H1SharedCapProtocolFailureV2(
                        "shared-owner callback concealed a failed nested mutation"
                    )
                if (
                    not allow_failure_cleanup
                    and state.mode
                    in {
                        H1SharedOwnerModeV2.CAP_EXHAUSTED,
                        H1SharedOwnerModeV2.PROTOCOL_FAILURE,
                    }
                ):
                    raise H1SharedCapProtocolFailureV2(
                        "shared-owner callback concealed a failed nested mutation"
                    )
                if failed and state.mode is not starting_mode:
                    raise H1SharedCapProtocolFailureV2(
                        "failure cleanup changed the preserved terminal cause"
                    )
                return result
            except BaseException as error:
                if failed:
                    _append_failure_cause(
                        state,
                        # The original terminal mode is carried separately as
                        # preserved_primary_mode.  A newly failed cleanup is a
                        # protocol observation unless it itself raised a real
                        # cap-exhaustion exception.
                        observed_mode=(
                            H1SharedOwnerModeV2.CAP_EXHAUSTED
                            if isinstance(error, H1SharedCapExhaustedV2)
                            else H1SharedOwnerModeV2.PROTOCOL_FAILURE
                        ),
                        cleanup_phase=allow_failure_cleanup,
                        operation=function.__name__,
                        exception_type=type(error).__name__,
                        message=str(error) or "failure cleanup raised without a message",
                    )
                elif (
                    state.mode in _FAILURE_MODES
                    and len(state.failure_cause_chain)
                    == state.operation_start_failure_count
                ):
                    _append_failure_cause(
                        state,
                        observed_mode=state.mode,
                        cleanup_phase=allow_failure_cleanup,
                        operation=function.__name__,
                        exception_type=type(error).__name__,
                        message=str(error) or "shared-owner operation failed",
                    )
                raise
            finally:
                state.operation_in_flight = False
                state.operation_start_mode = None
                state.operation_start_violation_count = 0
                state.operation_start_failure_count = 0

    return wrapped


def _serialized_owner_operation(function: Callable[..., Any]) -> Callable[..., Any]:
    return _serialized_operation_wrapper(function, allow_failure_cleanup=False)


def _serialized_cleanup_operation(function: Callable[..., Any]) -> Callable[..., Any]:
    return _serialized_operation_wrapper(function, allow_failure_cleanup=True)


def _record_pair(
    owner: H1SharedCapOwnerV2,
    state: _OwnerStateV2,
    *,
    path: str,
    reservation: int,
    actual: int,
    settlement: H1SharedSettlementV2,
    detail: Mapping[str, Any] | None = None,
) -> None:
    state.sequence += 1
    base = {
        "schema_version": SCHEMA_VERSION,
        "h1_shared_cap_runtime_id": owner.runtime_id,
        "sequence": state.sequence,
        "path": path,
        "reducer": _SITE_BY_PATH[path].reducer.value,
        "reservation": reservation,
        "actual": actual,
        "settlement": settlement.value,
        "detail": dict(detail or {}),
        "construction_exercise": owner.construction_exercise,
        "formal_accounting_eligible": False,
        "control_cap_checks_after_event": state.cap_checks,
        "control_cap_rejections_after_event": state.cap_rejections,
        "pair_content_id_hash_lane": "PROVENANCE",
        "pair_content_id_hash_charged_as_operational": False,
    }
    receipt_payload = {
        **base,
        "schema": "acfqp.h1_shared_cap_receipt.v2",
        "atomic_pair_sequence": state.sequence,
    }
    event_payload = {
        **base,
        "schema": "acfqp.h1_shared_cap_semantic_event.v2",
        "atomic_pair_sequence": state.sequence,
    }
    state.receipts.append(
        {
            **receipt_payload,
            "receipt_id": _content_id(RECEIPT_DOMAIN, receipt_payload),
        }
    )
    state.events.append(
        {**event_payload, "event_id": _content_id(EVENT_DOMAIN, event_payload)}
    )


def _reject(
    owner: H1SharedCapOwnerV2,
    state: _OwnerStateV2,
    *,
    path: str,
    reservation: int,
    candidate: int | None,
    hard_cap: int,
    message: str,
) -> NoReturn:
    if state.cap_rejections >= EXACT_CONTROL_CAP_REJECTIONS_UPPER:
        _append_failure_cause(
            state,
            observed_mode=H1SharedOwnerModeV2.PROTOCOL_FAILURE,
            cleanup_phase=False,
            operation="_reject",
            exception_type=H1SharedCapProtocolFailureV2.__name__,
            message="a second cap rejection exceeded the registered upper",
        )
        raise H1SharedCapProtocolFailureV2(
            "a second cap rejection exceeded the registered upper"
        )
    state.cap_rejections += 1
    _record_pair(
        owner,
        state,
        path=path,
        reservation=reservation,
        actual=0,
        settlement=H1SharedSettlementV2.CAP_REJECTED_BEFORE_SIDE_EFFECT,
        detail={
            "candidate": candidate,
            "hard_cap": hard_cap,
            "side_effect_started": False,
        },
    )
    _append_failure_cause(
        state,
        observed_mode=H1SharedOwnerModeV2.CAP_EXHAUSTED,
        cleanup_phase=False,
        operation="_reject",
        exception_type=H1SharedCapExhaustedV2.__name__,
        message=message,
    )
    raise H1SharedCapExhaustedV2(message)


def _reserve(
    owner: H1SharedCapOwnerV2,
    state: _OwnerStateV2,
    profile: H1SharedCapProfileV2,
    path: str,
    amount: int,
    *,
    max_candidate: int | None = None,
) -> None:
    amount = _nonnegative(amount, "shared reservation")
    if state.cap_checks >= profile.max_control_cap_checks:
        _reject(
            owner,
            state,
            path=path,
            reservation=amount,
            candidate=None,
            hard_cap=profile.max_control_cap_checks,
            message="control.cap_checks hard cap rejected the operation",
        )
    state.cap_checks += 1
    reducer = _SITE_BY_PATH[path].reducer
    hard_cap = profile.limit_for(path).hard_cap
    candidate = (
        state.actual[path] + state.outstanding[path] + amount
        if reducer is H1SharedReducerV2.SUM
        else _nonnegative(max_candidate, "MAX admission candidate")
    )
    if candidate > hard_cap:
        _reject(
            owner,
            state,
            path=path,
            reservation=amount,
            candidate=candidate,
            hard_cap=hard_cap,
            message=f"{path} hard cap rejected the operation",
        )
    state.outstanding[path] += amount


def _settle_sum(
    state: _OwnerStateV2, path: str, reservation: int, actual: int
) -> None:
    actual = _nonnegative(actual, "SUM actual")
    if actual > reservation or state.outstanding[path] < reservation:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            f"{path} actual exceeded or lost its reservation"
        )
    state.outstanding[path] -= reservation
    state.actual[path] += actual


def _settle_max(
    state: _OwnerStateV2, path: str, reservation: int, actual: int
) -> None:
    actual = _nonnegative(actual, "MAX actual")
    if actual > reservation or state.outstanding[path] < reservation:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            f"{path} actual exceeded or lost its reservation"
        )
    state.outstanding[path] -= reservation
    state.actual[path] = max(state.actual[path], actual)


def _record_observed_upper_violation(
    owner: H1SharedCapOwnerV2,
    state: _OwnerStateV2,
    *,
    path: str,
    reservation: int,
    observed_actual: int,
    detail: Mapping[str, Any] | None = None,
) -> NoReturn:
    actual = _nonnegative(observed_actual, "observed upper-bound violation")
    if actual <= reservation or state.outstanding[path] < reservation:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            f"{path} observed-overrun state is inconsistent"
        )
    state.outstanding[path] -= reservation
    if _SITE_BY_PATH[path].reducer is H1SharedReducerV2.SUM:
        state.actual[path] += actual
    else:
        state.actual[path] = max(state.actual[path], actual)
    _record_pair(
        owner,
        state,
        path=path,
        reservation=reservation,
        actual=actual,
        settlement=H1SharedSettlementV2.OBSERVED_UPPER_BOUND_VIOLATION,
        detail=detail,
    )
    state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
    raise H1SharedCapProtocolFailureV2(
        f"{path} observed actual exceeded its admitted upper"
    )


def _ensure_callback(callback: Any) -> Callable[..., Any]:
    if not callable(callback):
        _fail("shared owner callback must be callable")
    return callback


def _require_callback_did_not_conceal_failure(state: _OwnerStateV2) -> None:
    starting_mode = state.operation_start_mode
    started_failed = starting_mode in {
        H1SharedOwnerModeV2.CAP_EXHAUSTED,
        H1SharedOwnerModeV2.PROTOCOL_FAILURE,
    }
    now_failed = state.mode in {
        H1SharedOwnerModeV2.CAP_EXHAUSTED,
        H1SharedOwnerModeV2.PROTOCOL_FAILURE,
    }
    if (
        state.mutation_violation_count
        != state.operation_start_violation_count
        or (not started_failed and now_failed)
    ):
        raise H1SharedCapProtocolFailureV2(
            "shared-owner callback concealed a failed nested mutation"
        )


def _require_memory_binding(
    owner: H1SharedCapOwnerV2, binding: Any
) -> H1SharedMemoryBindingV2:
    if type(binding) is not H1SharedMemoryBindingV2:
        _fail("H1 memory binding has a foreign type")
    with _LOCK:
        retained = _LIVE_MEMORY_BINDINGS.get(id(binding))
    if (
        retained is None
        or retained[0] is not binding
        or retained[1] != id(owner)
        or binding.owner_runtime_id != owner.runtime_id
        or not hmac.compare_digest(
            canonical_json_bytes(binding.to_document()), retained[2]
        )
    ):
        _fail("H1 memory binding is foreign, stale or mutated")
    return binding


def _ensure_memory_first(state: _OwnerStateV2, path: str) -> None:
    if path != "memory.working_bytes_peak" and not state.memory_bound:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "working hierarchy must bind before the first postdecision side effect"
        )


@_serialized_owner_operation
def _run_unit_sum(
    owner: H1SharedCapOwnerV2, path: str, callback: Callable[[], Any]
) -> Any:
    _, state, profile = _require_owner(owner, operable=True)
    _ensure_memory_first(state, path)
    callback = _ensure_callback(callback)
    _reserve(owner, state, profile, path, 1)
    try:
        result = callback()
        _require_callback_did_not_conceal_failure(state)
    except BaseException as error:
        _settle_sum(state, path, 1, 1)
        _record_pair(
            owner,
            state,
            path=path,
            reservation=1,
            actual=1,
            settlement=H1SharedSettlementV2.FULL_RESERVATION_ON_CALLBACK_FAILURE,
        )
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            f"{path} callback failed after admission"
        ) from error
    _settle_sum(state, path, 1, 1)
    _record_pair(
        owner,
        state,
        path=path,
        reservation=1,
        actual=1,
        settlement=H1SharedSettlementV2.EXACT_SUCCESS,
    )
    return result


@_serialized_owner_operation
def _run_sum_bytes(
    owner: H1SharedCapOwnerV2,
    path: str,
    reservation: int,
    callback: Callable[[], bytes],
) -> bytes:
    _, state, profile = _require_owner(owner, operable=True)
    _ensure_memory_first(state, path)
    callback = _ensure_callback(callback)
    _reserve(owner, state, profile, path, reservation)
    try:
        result = callback()
        _require_callback_did_not_conceal_failure(state)
        if type(result) is not bytes:
            raise TypeError("read callback did not return exact bytes")
    except BaseException as error:
        if state.outstanding[path] >= reservation:
            _settle_sum(state, path, reservation, reservation)
        _record_pair(
            owner,
            state,
            path=path,
            reservation=reservation,
            actual=reservation,
            settlement=H1SharedSettlementV2.FULL_RESERVATION_ON_CALLBACK_FAILURE,
        )
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            f"{path} callback/settlement failed after admission"
        ) from error
    actual = len(result)
    if actual > reservation:
        _record_observed_upper_violation(
            owner,
            state,
            path=path,
            reservation=reservation,
            observed_actual=actual,
        )
    _settle_sum(state, path, reservation, actual)
    _record_pair(
        owner,
        state,
        path=path,
        reservation=reservation,
        actual=actual,
        settlement=H1SharedSettlementV2.EXACT_SUCCESS,
    )
    return result


@_serialized_owner_operation
def _run_sum_int(
    owner: H1SharedCapOwnerV2,
    path: str,
    reservation: int,
    callback: Callable[[], int],
    *,
    detail: Mapping[str, Any] | None = None,
) -> int:
    _, state, profile = _require_owner(owner, operable=True)
    _ensure_memory_first(state, path)
    callback = _ensure_callback(callback)
    _reserve(owner, state, profile, path, reservation)
    try:
        result = callback()
        _require_callback_did_not_conceal_failure(state)
        actual = _nonnegative(result, f"{path} callback result")
    except BaseException as error:
        if state.outstanding[path] >= reservation:
            _settle_sum(state, path, reservation, reservation)
        _record_pair(
            owner,
            state,
            path=path,
            reservation=reservation,
            actual=reservation,
            settlement=H1SharedSettlementV2.FULL_RESERVATION_ON_CALLBACK_FAILURE,
            detail=detail,
        )
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            f"{path} callback/settlement failed after admission"
        ) from error
    if actual > reservation:
        _record_observed_upper_violation(
            owner,
            state,
            path=path,
            reservation=reservation,
            observed_actual=actual,
            detail=detail,
        )
    _settle_sum(state, path, reservation, actual)
    _record_pair(
        owner,
        state,
        path=path,
        reservation=reservation,
        actual=actual,
        settlement=H1SharedSettlementV2.EXACT_SUCCESS,
        detail=detail,
    )
    return result


@_serialized_owner_operation
def _bind_memory(
    owner: H1SharedCapOwnerV2,
    callback: Callable[[H1SharedMemoryBindingV2], Any],
) -> H1SharedMemoryBindingV2:
    _, state, profile = _require_owner(owner, operable=True)
    callback = _ensure_callback(callback)
    if state.sequence != 0 or state.memory_bound:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "working hierarchy binding must be the first owner operation"
        )
    upper = profile.memory_formula_upper
    _reserve(
        owner,
        state,
        profile,
        "memory.working_bytes_peak",
        upper,
        max_candidate=upper,
    )
    binding = H1SharedMemoryBindingV2(
        _TOKEN_ISSUER,
        owner.runtime_id,
        profile.retained_memory_peak_ofd_plan_id,
        upper,
    )
    with _LOCK:
        _LIVE_MEMORY_BINDINGS[id(binding)] = (
            binding,
            id(owner),
            canonical_json_bytes(binding.to_document()),
        )
    try:
        callback(binding)
        _require_memory_binding(owner, binding)
        _require_callback_did_not_conceal_failure(state)
    except BaseException as error:
        _settle_max(state, "memory.working_bytes_peak", upper, upper)
        _record_pair(
            owner,
            state,
            path="memory.working_bytes_peak",
            reservation=upper,
            actual=upper,
            settlement=H1SharedSettlementV2.FULL_RESERVATION_ON_CALLBACK_FAILURE,
            detail={"binding_id": binding.binding_id},
        )
        # The callback may have created the native hierarchy before failing.
        # A later native-resolution contract must prove whether cleanup is
        # required; the construction owner may not silently treat it as absent.
        state.ambiguous_memory_binding = True
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "working hierarchy callback failed after admission"
        ) from error
    # Keep the one aggregate reservation live until the retained-OFD peak is
    # read after both descendants are reaped.  The read is settlement of this
    # pre-side-effect admission, not a second admission/check.
    state.memory_bound = True
    state.memory_peak_terminal = H1SharedLifecycleTerminalV2.PENDING
    _record_pair(
        owner,
        state,
        path="memory.working_bytes_peak",
        reservation=upper,
        actual=0,
        settlement=H1SharedSettlementV2.PRELAUNCH_BINDING,
        detail={"binding_id": binding.binding_id},
    )
    return binding


@_serialized_owner_operation
def _begin_output(owner: H1SharedCapOwnerV2) -> H1SharedOutputTokenV2:
    _, state, profile = _require_owner(owner, operable=True)
    _ensure_memory_first(state, "io.output_bytes")
    if state.output_reserved is not None or state.launch_order:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "whole-route output must reserve exactly once before first launch"
        )
    reservation = profile.limit_for("io.output_bytes").hard_cap
    _reserve(owner, state, profile, "io.output_bytes", reservation)
    state.output_reserved = reservation
    state.output_terminal = H1SharedLifecycleTerminalV2.PENDING
    token = H1SharedOutputTokenV2(_TOKEN_ISSUER, owner.runtime_id, reservation)
    with _LOCK:
        _LIVE_OUTPUT_TOKENS[id(token)] = (
            token,
            id(owner),
            canonical_json_bytes(token.to_document()),
        )
    _record_pair(
        owner,
        state,
        path="io.output_bytes",
        reservation=reservation,
        actual=0,
        settlement=H1SharedSettlementV2.PRELAUNCH_BINDING,
        detail={"output_token_id": token.token_id},
    )
    return token


def _require_output_token(
    owner: H1SharedCapOwnerV2, token: Any
) -> H1SharedOutputTokenV2:
    if type(token) is not H1SharedOutputTokenV2:
        _fail("H1 output token has a foreign type")
    with _LOCK:
        retained = _LIVE_OUTPUT_TOKENS.get(id(token))
    if (
        retained is None
        or retained[0] is not token
        or retained[1] != id(owner)
        or not hmac.compare_digest(
            canonical_json_bytes(token.to_document()), retained[2]
        )
    ):
        _fail("H1 output token is foreign or belongs to another owner")
    if token.owner_runtime_id != owner.runtime_id:
        _fail("H1 output token crossed its runtime")
    return token


@_serialized_cleanup_operation
def _finalize_output(
    owner: H1SharedCapOwnerV2,
    token: H1SharedOutputTokenV2,
    actual_output_bytes: int,
    callback: Callable[[], Any],
) -> Any:
    _, state, _ = _require_owner(owner)
    token = _require_output_token(owner, token)
    callback = _ensure_callback(callback)
    actual = _nonnegative(actual_output_bytes, "actual output bytes")
    if (
        state.output_terminal is not H1SharedLifecycleTerminalV2.PENDING
        or state.output_reserved != token.reserved_fixed_point_bytes
        or state.outstanding["io.output_bytes"]
        != token.reserved_fixed_point_bytes
    ):
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "H1 output reservation is stale or already terminal"
        )
    failed_cleanup = state.mode in {
        H1SharedOwnerModeV2.CAP_EXHAUSTED,
        H1SharedOwnerModeV2.PROTOCOL_FAILURE,
    }
    memory_peak_settled = (
        state.memory_peak_terminal in _SETTLED_LIFECYCLE_TERMINALS
    )
    if (
        not state.descendants_reaped
        or not memory_peak_settled
        or (
            not failed_cleanup
            and state.memory_peak_terminal
            is not H1SharedLifecycleTerminalV2.EXACT_SUCCESS
        )
        or state.active_mount_tokens
        or state.active_mounts
        or state.ambiguous_mount_opens
        or state.ambiguous_memory_binding
        or state.ambiguous_launch_role is not None
        or (
            not failed_cleanup
            and tuple(state.launch_order) != EXACT_CHILD_LAUNCH_ORDER
        )
        or (
            failed_cleanup
            and tuple(state.launch_order)
            != EXACT_CHILD_LAUNCH_ORDER[: len(state.launch_order)]
        )
    ):
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "route output may finalize only after the known launch prefix, "
            "trusted reap, memory settlement and mount cleanup"
        )
    try:
        result = callback()
        _require_callback_did_not_conceal_failure(state)
    except BaseException as error:
        if actual > token.reserved_fixed_point_bytes:
            state.output_terminal = (
                H1SharedLifecycleTerminalV2.OBSERVED_UPPER_BOUND_VIOLATION
            )
            try:
                _record_observed_upper_violation(
                    owner,
                    state,
                    path="io.output_bytes",
                    reservation=token.reserved_fixed_point_bytes,
                    observed_actual=actual,
                    detail={
                        "output_token_id": token.token_id,
                        "finalization_callback_failed": True,
                    },
                )
            except H1SharedCapProtocolFailureV2 as violation:
                raise violation from error
        if state.outstanding["io.output_bytes"] >= token.reserved_fixed_point_bytes:
            _settle_sum(
                state,
                "io.output_bytes",
                token.reserved_fixed_point_bytes,
                token.reserved_fixed_point_bytes,
            )
        _record_pair(
            owner,
            state,
            path="io.output_bytes",
            reservation=token.reserved_fixed_point_bytes,
            actual=token.reserved_fixed_point_bytes,
            settlement=H1SharedSettlementV2.FULL_RESERVATION_ON_CALLBACK_FAILURE,
            detail={"output_token_id": token.token_id},
        )
        state.output_terminal = H1SharedLifecycleTerminalV2.FAILED_UPPER_ONLY
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "H1 output finalization failed after route-wide reservation"
        ) from error
    if actual > token.reserved_fixed_point_bytes:
        state.output_terminal = (
            H1SharedLifecycleTerminalV2.OBSERVED_UPPER_BOUND_VIOLATION
        )
        _record_observed_upper_violation(
            owner,
            state,
            path="io.output_bytes",
            reservation=token.reserved_fixed_point_bytes,
            observed_actual=actual,
            detail={"output_token_id": token.token_id},
        )
    _settle_sum(
        state,
        "io.output_bytes",
        token.reserved_fixed_point_bytes,
        actual,
    )
    state.output_finalized = True
    state.output_terminal = H1SharedLifecycleTerminalV2.EXACT_SUCCESS
    _record_pair(
        owner,
        state,
        path="io.output_bytes",
        reservation=token.reserved_fixed_point_bytes,
        actual=actual,
        settlement=H1SharedSettlementV2.EXACT_FINALIZATION,
        detail={"output_token_id": token.token_id},
    )
    return result


@_serialized_owner_operation
def _open_mount(
    owner: H1SharedCapOwnerV2,
    payload_identity_id: str,
    extent: int,
    callback: Callable[[], Any],
) -> H1SharedMountTokenV2:
    _, state, profile = _require_owner(owner, operable=True)
    _ensure_memory_first(state, "io.mounted_bytes_peak")
    if state.launch_order:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "mounted payload must open before first child visibility"
        )
    payload_id = _cid(payload_identity_id, "mounted payload identity")
    extent = _positive(extent, "mounted payload extent")
    callback = _ensure_callback(callback)
    existing = state.active_mounts.get(payload_id)
    if existing is not None and existing[0] != extent:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "one physical payload identity changed extent while visible"
        )
    prospective = state.mounted_current + (0 if existing else extent)
    reservation = prospective
    _reserve(
        owner,
        state,
        profile,
        "io.mounted_bytes_peak",
        reservation,
        max_candidate=prospective,
    )
    try:
        callback()
        _require_callback_did_not_conceal_failure(state)
    except BaseException as error:
        _settle_max(state, "io.mounted_bytes_peak", reservation, prospective)
        _record_pair(
            owner,
            state,
            path="io.mounted_bytes_peak",
            reservation=reservation,
            actual=prospective,
            settlement=H1SharedSettlementV2.FULL_RESERVATION_ON_CALLBACK_FAILURE,
            detail={"payload_identity_id": payload_id, "extent": extent},
        )
        # The callback may have made the mount visible before failing.  Do not
        # erase that native-existence ambiguity by omitting an active token.
        state.ambiguous_mount_opens[payload_id] = extent
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "mount callback failed after admission"
        ) from error
    _settle_max(state, "io.mounted_bytes_peak", reservation, prospective)
    state.active_mounts[payload_id] = (
        extent,
        1 if existing is None else existing[1] + 1,
    )
    if existing is None:
        state.mounted_current += extent
    token = H1SharedMountTokenV2(
        _TOKEN_ISSUER,
        owner.runtime_id,
        payload_id,
        extent,
        state.sequence + 1,
    )
    with _LOCK:
        _LIVE_MOUNT_TOKENS[id(token)] = (
            token,
            id(owner),
            payload_id,
            canonical_json_bytes(token.to_document()),
        )
    state.active_mount_tokens.add(id(token))
    _record_pair(
        owner,
        state,
        path="io.mounted_bytes_peak",
        reservation=reservation,
        actual=prospective,
        settlement=H1SharedSettlementV2.LIFECYCLE_OPEN,
        detail={"payload_identity_id": payload_id, "mount_token_id": token.token_id},
    )
    return token


@_serialized_cleanup_operation
def _close_mount(
    owner: H1SharedCapOwnerV2,
    token: H1SharedMountTokenV2,
    callback: Callable[[], Any],
) -> Any:
    _, state, _ = _require_owner(owner)
    callback = _ensure_callback(callback)
    if not state.descendants_reaped:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "mounted payload cannot close before trusted descendant reap"
        )
    if type(token) is not H1SharedMountTokenV2:
        _fail("H1 mount token has a foreign type")
    with _LOCK:
        retained = _LIVE_MOUNT_TOKENS.get(id(token))
    if (
        retained is None
        or retained[0] is not token
        or retained[1] != id(owner)
        or retained[2] != token.payload_identity_id
        or not hmac.compare_digest(
            canonical_json_bytes(token.to_document()), retained[3]
        )
        or id(token) not in state.active_mount_tokens
    ):
        _fail("H1 mount token is stale, foreign or already closed")
    try:
        result = callback()
        _require_callback_did_not_conceal_failure(state)
    except BaseException as error:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "mount close failed; cleanup obligation remains live"
        ) from error
    extent, refs = state.active_mounts[token.payload_identity_id]
    if refs == 1:
        del state.active_mounts[token.payload_identity_id]
        state.mounted_current -= extent
    else:
        state.active_mounts[token.payload_identity_id] = (extent, refs - 1)
    state.active_mount_tokens.remove(id(token))
    with _LOCK:
        _LIVE_MOUNT_TOKENS.pop(id(token), None)
    _record_pair(
        owner,
        state,
        path="io.mounted_bytes_peak",
        reservation=0,
        actual=state.actual["io.mounted_bytes_peak"],
        settlement=H1SharedSettlementV2.LIFECYCLE_CLOSE,
        detail={
            "payload_identity_id": token.payload_identity_id,
            "mount_token_id": token.token_id,
        },
    )
    return result


@_serialized_owner_operation
def _launch_role(
    owner: H1SharedCapOwnerV2, role: str, callback: Callable[[], Any]
) -> Any:
    _, state, profile = _require_owner(owner, operable=True)
    _ensure_memory_first(state, "process.launches")
    callback = _ensure_callback(callback)
    if state.output_reserved is None:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "whole-route output reservation must precede the first launch"
        )
    if state.output_finalized:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "a child launch cannot occur after route output finalization"
        )
    if type(role) is not str or len(state.launch_order) >= 2:
        _fail("H1 child launch role is invalid or duplicated")
    expected = EXACT_CHILD_LAUNCH_ORDER[len(state.launch_order)]
    if role != expected:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            f"H1 child launch order requires {expected}"
        )
    _reserve(owner, state, profile, "process.launches", 1)
    try:
        result = callback()
        _require_callback_did_not_conceal_failure(state)
    except BaseException as error:
        _settle_sum(state, "process.launches", 1, 1)
        _record_pair(
            owner,
            state,
            path="process.launches",
            reservation=1,
            actual=1,
            settlement=H1SharedSettlementV2.FULL_RESERVATION_ON_CALLBACK_FAILURE,
            detail={"role": role, "child_existence": "AMBIGUOUS"},
        )
        state.ambiguous_launch_role = role
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "native launch callback failed after reservation; child existence ambiguous"
        ) from error
    _settle_sum(state, "process.launches", 1, 1)
    state.launch_order.append(role)
    _record_pair(
        owner,
        state,
        path="process.launches",
        reservation=1,
        actual=1,
        settlement=H1SharedSettlementV2.EXACT_SUCCESS,
        detail={"role": role, "positive_native_edge": True},
    )
    return result


@_serialized_cleanup_operation
def _mark_reaped(
    owner: H1SharedCapOwnerV2,
    worker_pidfd_observation_id: str | None,
    business_pidfd_observation_id: str | None,
    retained_memory_peak_ofd_plan_id: str,
) -> None:
    _, state, profile = _require_owner(owner)
    if state.descendants_reaped:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "trusted descendant reap may be recorded exactly once"
        )
    launched = tuple(state.launch_order)
    failed_cleanup = state.mode in {
        H1SharedOwnerModeV2.CAP_EXHAUSTED,
        H1SharedOwnerModeV2.PROTOCOL_FAILURE,
    }
    if (
        state.ambiguous_launch_role is not None
        or (
            launched != EXACT_CHILD_LAUNCH_ORDER
            and not (
                failed_cleanup
                and launched == EXACT_CHILD_LAUNCH_ORDER[: len(launched)]
            )
        )
    ):
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "trusted reap requires an exact known launched-role prefix"
        )
    supplied_observations = {
        "WORKER": worker_pidfd_observation_id,
        "BUSINESS": business_pidfd_observation_id,
    }
    retained_observations: dict[str, str] = {}
    for role, observation in supplied_observations.items():
        if role in launched:
            retained_observations[role] = _cid(
                observation, f"{role.lower()} pidfd reap observation"
            )
        elif observation is not None:
            state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
            raise H1SharedCapProtocolFailureV2(
                f"{role} reap observation is forbidden when that role was not launched"
            )
    if (
        _cid(retained_memory_peak_ofd_plan_id, "memory peak OFD plan")
        != profile.retained_memory_peak_ofd_plan_id
    ):
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "trusted reap did not retain the frozen memory.peak OFD plan"
        )
    state.reap_pidfd_observation_ids = retained_observations
    state.descendants_reaped = True


@_serialized_cleanup_operation
def _read_memory_peak(
    owner: H1SharedCapOwnerV2, callback: Callable[[], int]
) -> int:
    _, state, profile = _require_owner(owner)
    callback = _ensure_callback(callback)
    if (
        not state.memory_bound
        or not state.descendants_reaped
        or state.memory_peak_terminal is not H1SharedLifecycleTerminalV2.PENDING
    ):
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "memory peak requires one pending post-reap read from the retained OFD"
        )
    reservation = profile.memory_formula_upper
    if state.outstanding["memory.working_bytes_peak"] != reservation:
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "memory peak lost its one aggregate prelaunch reservation"
        )
    try:
        result = callback()
        _require_callback_did_not_conceal_failure(state)
        actual = _nonnegative(result, "observed working-byte peak")
    except BaseException as error:
        if state.outstanding["memory.working_bytes_peak"] >= reservation:
            _settle_max(
                state, "memory.working_bytes_peak", reservation, reservation
            )
        _record_pair(
            owner,
            state,
            path="memory.working_bytes_peak",
            reservation=reservation,
            actual=reservation,
            settlement=H1SharedSettlementV2.FULL_RESERVATION_ON_CALLBACK_FAILURE,
        )
        state.memory_peak_terminal = (
            H1SharedLifecycleTerminalV2.FAILED_UPPER_ONLY
        )
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "memory peak read failed after admission"
        ) from error
    if actual > reservation:
        state.memory_peak_terminal = (
            H1SharedLifecycleTerminalV2.OBSERVED_UPPER_BOUND_VIOLATION
        )
        _record_observed_upper_violation(
            owner,
            state,
            path="memory.working_bytes_peak",
            reservation=reservation,
            observed_actual=actual,
        )
    _settle_max(state, "memory.working_bytes_peak", reservation, actual)
    state.memory_observed = True
    state.memory_peak_terminal = H1SharedLifecycleTerminalV2.EXACT_SUCCESS
    _record_pair(
        owner,
        state,
        path="memory.working_bytes_peak",
        reservation=reservation,
        actual=actual,
        settlement=H1SharedSettlementV2.EXACT_SUCCESS,
        detail={
            "retained_same_ofd_memory_peak_plan_id": (
                profile.retained_memory_peak_ofd_plan_id
            )
        },
    )
    return result


@_serialized_owner_operation
def _close_owner(owner: H1SharedCapOwnerV2) -> None:
    _, state, _ = _require_owner(owner, operable=True)
    if (
        tuple(state.launch_order) != EXACT_CHILD_LAUNCH_ORDER
        or not state.descendants_reaped
        or not state.memory_observed
        or state.memory_peak_terminal
        is not H1SharedLifecycleTerminalV2.EXACT_SUCCESS
        or not state.output_finalized
        or state.output_terminal
        is not H1SharedLifecycleTerminalV2.EXACT_SUCCESS
        or state.active_mount_tokens
        or state.active_mounts
        or any(state.outstanding.values())
    ):
        state.mode = H1SharedOwnerModeV2.PROTOCOL_FAILURE
        raise H1SharedCapProtocolFailureV2(
            "H1 shared owner cannot close with an incomplete route lifecycle"
        )
    state.mode = H1SharedOwnerModeV2.CLOSED


@_serialized_cleanup_operation
def _close_failed_owner(owner: H1SharedCapOwnerV2) -> None:
    _, state, _ = _require_owner(owner)
    if state.mode not in {
        H1SharedOwnerModeV2.CAP_EXHAUSTED,
        H1SharedOwnerModeV2.PROTOCOL_FAILURE,
    }:
        raise H1SharedCapProtocolFailureV2(
            "failure cleanup close requires a preserved failure cause"
        )
    if (
        state.ambiguous_memory_binding
        or state.ambiguous_launch_role is not None
        or state.ambiguous_mount_opens
        or (bool(state.launch_order) and not state.descendants_reaped)
        or (
            state.memory_bound
            and state.memory_peak_terminal not in _SETTLED_LIFECYCLE_TERMINALS
        )
        or (
            state.output_reserved is not None
            and state.output_terminal not in _SETTLED_LIFECYCLE_TERMINALS
        )
        or state.active_mount_tokens
        or state.active_mounts
        or any(state.outstanding.values())
    ):
        raise H1SharedCapProtocolFailureV2(
            "failure cleanup cannot close with unresolved resources"
        )
    state.cleanup_closed = True


def h1_shared_cap_owner_snapshot_v2(owner: H1SharedCapOwnerV2) -> dict[str, Any]:
    with _LOCK:
        owner, state, profile = _require_owner(owner)
        _validate_failure_cause_chain(state)
        return {
            "schema": "acfqp.construction_k7_h1_shared_cap_owner_snapshot.v2",
            "schema_version": SCHEMA_VERSION,
            "h1_shared_cap_runtime_id": owner.runtime_id,
            "h1_shared_cap_profile_id": owner.profile_id,
            "h1_shared_cap_source_manifest_id": owner.source_manifest_id,
            "mode": state.mode.value,
            "construction_exercise": owner.construction_exercise,
            "production_execution_authorized": (
                state.mode is H1SharedOwnerModeV2.ACTIVE_AFTER_OPERAND_FORMAL_JOIN
            ),
            "formal_operand_authority_join_present": (
                state.formal_operand_authority_id is not None
            ),
            "formal_route_authority_join_present": (
                state.formal_route_authority_id is not None
            ),
            "formal_actual_compliance_eligible": False,
            "official_execution_allowed": False,
            "sequence": state.sequence,
            "operation_in_flight": state.operation_in_flight,
            "mutation_violation_count": state.mutation_violation_count,
            "cleanup_closed": state.cleanup_closed,
            "ambiguous_memory_binding": state.ambiguous_memory_binding,
            "ambiguous_launch_role": state.ambiguous_launch_role,
            "ambiguous_mount_opens": dict(state.ambiguous_mount_opens),
            "actual": dict(state.actual),
            "outstanding": dict(state.outstanding),
            "control": {
                "cap_checks": state.cap_checks,
                "cap_rejections": state.cap_rejections,
                "cap_rejections_upper": profile.control_cap_rejections_upper,
            },
            "memory_formula_upper": profile.memory_formula_upper,
            "memory_bound": state.memory_bound,
            "memory_observed": state.memory_observed,
            "memory_peak_terminal": state.memory_peak_terminal.value,
            "memory_peak_terminal_settled": (
                state.memory_peak_terminal in _SETTLED_LIFECYCLE_TERMINALS
            ),
            "descendants_reaped": state.descendants_reaped,
            "reap_exact_once": True,
            "reap_transition_count": 1 if state.descendants_reaped else 0,
            "reap_observations_native_verified": False,
            "reap_observations_role_bound": False,
            "reap_pidfd_observation_ids": dict(
                state.reap_pidfd_observation_ids
            ),
            "launch_order": list(state.launch_order),
            "process_launches_exact": state.actual["process.launches"],
            "mounted_current": state.mounted_current,
            "active_mount_count": len(state.active_mount_tokens),
            "output_reserved": state.output_reserved,
            "output_finalized": state.output_finalized,
            "output_terminal": state.output_terminal.value,
            "output_terminal_settled": (
                state.output_terminal in _SETTLED_LIFECYCLE_TERMINALS
            ),
            "receipts": copy.deepcopy(state.receipts),
            "semantic_events": copy.deepcopy(state.events),
            "atomic_pair_count": len(state.receipts),
            "failure_cause_chain": copy.deepcopy(state.failure_cause_chain),
            "primary_failure": (
                copy.deepcopy(state.failure_cause_chain[0])
                if state.failure_cause_chain
                else None
            ),
            "secondary_failures": copy.deepcopy(
                state.failure_cause_chain[1:]
            ),
            "primary_failure_mode_preserved": (
                not state.failure_cause_chain
                or state.mode.value
                == state.failure_cause_chain[0]["preserved_primary_mode"]
            ),
            "failure_cause_chain_verified": True,
        }


def verify_h1_shared_cap_failure_cause_chain_v2(
    owner: H1SharedCapOwnerV2,
) -> bool:
    """Verify the issuer-retained ordered primary/secondary failure chain."""

    with _LOCK:
        _, state, _ = _require_owner(owner)
        _validate_failure_cause_chain(state)
        return True


def require_h1_shared_cap_owner_v2(
    owner: H1SharedCapOwnerV2,
) -> H1SharedCapOwnerV2:
    return _require_owner(owner)[0]


__all__ = (
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7H1SharedCapOwnerV2Error",
    "EVENT_DOMAIN",
    "EXACT_CHILD_LAUNCH_ORDER",
    "EXACT_CONTROL_CAP_REJECTIONS_UPPER",
    "EXACT_PROCESS_LAUNCH_UPPER",
    "FORMAL_ACTUAL_COMPLIANCE_ELIGIBLE",
    "FORMAL_OPERAND_AUTHORITY_JOIN_PRESENT",
    "FORMAL_ROUTE_AUTHORITY_JOIN_PRESENT",
    "H1SharedCapExecutionLockedV2",
    "H1SharedCapExhaustedV2",
    "H1SharedCapLimitV2",
    "H1SharedCapOwnerV2",
    "H1SharedCapProfileV2",
    "H1SharedCapProtocolFailureV2",
    "H1SharedCapSourceManifestV2",
    "H1SharedIngressKindV2",
    "H1SharedLifecycleTerminalV2",
    "H1SharedMemoryBindingV2",
    "H1SharedMountTokenV2",
    "H1SharedOutputTokenV2",
    "H1SharedOwnerModeV2",
    "H1SharedOwnerSiteV2",
    "H1SharedReducerV2",
    "H1SharedSettlementV2",
    "LIFECYCLE_SOURCE_SYMBOLS",
    "MEMORY_BINDING_DOMAIN",
    "MOUNT_TOKEN_DOMAIN",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OUTPUT_TOKEN_DOMAIN",
    "OWNER_SITE_SPECS",
    "PROFILE_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RECEIPT_DOMAIN",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "RUNTIME_DOMAIN",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "SHARED_RESOURCE_PATHS",
    "SOURCE_MANIFEST_DOMAIN",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "freeze_h1_shared_cap_profile_v2",
    "freeze_h1_shared_cap_source_manifest_v2",
    "h1_shared_cap_owner_snapshot_v2",
    "prepare_h1_shared_cap_owner_construction_exercise_v2",
    "prepare_h1_shared_cap_owner_v2",
    "require_h1_shared_cap_owner_v2",
    "verify_h1_shared_cap_failure_cause_chain_v2",
)
