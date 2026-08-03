"""Fail-closed successor production shared-resource owner scaffold (V2).

This revision freezes a distinct production schema family, nine path-embedded
owner names, and their atomic/lifecycle obligations.  It deliberately cannot
execute.  The only issuer-sealed activation state is ``V7_AUTHORITY_PENDING``;
the public engine is an exact immutable tuple capability whose mutable document
and verification state live only in the external issuer registry.  Tuple
subclasses and caller-created exact tuples are not authorities.  Every reserved
owner name is paired only with a non-callable pending sentinel, and no private
live owner kernel exists in this revision.

Receipt/event/pair domain strings below are registration candidates for the
future V7 adapter.  This module does not mint those artifacts and does not use
the central domain registry until its owner accepts the new tags.  A future
adapter must add trusted launch, output-fixed-point, descendant-reap and
same-OFD authorities.  It must not reinterpret any pending V2 object as a
formal route decision or execution token.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import hmac
from typing import Any, Callable, Mapping, NoReturn

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.49"
PROFILE_KEY = "production_shared_cap_engine_v2_preproduction_locked"
BLOCKER = "V7_AUTHORITY_PENDING"

ACTIVATION_INTERFACE_DOMAIN_CANDIDATE = (
    "acfqp:production-shared-cap-activation-interface:v2"
)
PROFILE_DOMAIN_CANDIDATE = "acfqp:production-shared-cap-profile:v2"
ENGINE_DOMAIN_CANDIDATE = "acfqp:production-shared-cap-engine:v2"
RECEIPT_DOMAIN_CANDIDATE = "acfqp:preproduction-shared-cap-receipt:v2"
SEMANTIC_EVENT_DOMAIN_CANDIDATE = (
    "acfqp:preproduction-shared-cap-semantic-event:v2"
)
ATOMIC_PAIR_DOMAIN_CANDIDATE = "acfqp:preproduction-shared-cap-atomic-pair:v2"

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    ACTIVATION_INTERFACE_DOMAIN_CANDIDATE,
    PROFILE_DOMAIN_CANDIDATE,
    ENGINE_DOMAIN_CANDIDATE,
    RECEIPT_DOMAIN_CANDIDATE,
    SEMANTIC_EVENT_DOMAIN_CANDIDATE,
    ATOMIC_PAIR_DOMAIN_CANDIDATE,
)


class ProductionSharedCapV2Error(ValueError):
    """A pending production object is malformed, foreign, stale or mutated."""


class V7AuthorityPendingV2(ProductionSharedCapV2Error):
    """No production attempt started because formal V7 authority is absent."""

    blocker = BLOCKER
    production_execution_started = False
    official_execution_allowed = False
    certificate_issued = False


class ProductionSharedCapProtocolFailureV2(ProductionSharedCapV2Error):
    """A forged or mutated capability failed before production execution."""

    terminal_scope = "ROUTE_ATTEMPT"
    terminal_class = "ATTEMPT_CLOSURE_NONCERTIFICATE"
    terminal_code = "PROTOCOL_FAILURE"
    certificate_issued = False
    infeasibility_certified = False


class ProductionSharedCapExhaustedV2(ProductionSharedCapV2Error):
    """Reserved for the future V7 adapter; cap exhaustion is not infeasibility."""

    terminal_scope = "ROUTE_ATTEMPT"
    terminal_class = "ATTEMPT_CLOSURE_NONCERTIFICATE"
    terminal_code = "FALLBACK_CAP_EXHAUSTED"
    certificate_issued = False
    infeasibility_certified = False


class ActivationStatusV2(str, Enum):
    V7_AUTHORITY_PENDING = "V7_AUTHORITY_PENDING"


class ProductionEngineStateV2(str, Enum):
    V7_AUTHORITY_PENDING = "V7_AUTHORITY_PENDING"
    CLOSED = "CLOSED"


class ReducerV2(str, Enum):
    SUM = "SUM"
    MAX = "MAX"


class SandboxIngressKindV2(str, Enum):
    COPY_INTO_EXECUTION_SANDBOX = "COPY_INTO_EXECUTION_SANDBOX"
    BIND_INTO_EXECUTION_SANDBOX = "BIND_INTO_EXECUTION_SANDBOX"


class NativeLaunchOutcomeV2(str, Enum):
    POSITIVE_NATIVE_EDGE_WITH_MATCHING_PIDFD = (
        "POSITIVE_NATIVE_EDGE_WITH_MATCHING_PIDFD"
    )
    TRUSTED_NO_CHILD = "TRUSTED_NO_CHILD"
    AMBIGUOUS_CHILD_EXISTENCE = "AMBIGUOUS_CHILD_EXISTENCE"


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


@dataclass(frozen=True, slots=True)
class OwnerSiteSpecV2:
    path: str
    site_key: str
    owner_method: str
    reducer: ReducerV2
    required_semantics: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            self.path not in SHARED_RESOURCE_PATHS
            or type(self.site_key) is not str
            or not self.site_key.startswith("shared.")
            or type(self.owner_method) is not str
            or not self.owner_method
            or type(self.required_semantics) is not tuple
            or not self.required_semantics
            or len(set(self.required_semantics)) != len(self.required_semantics)
            or any(
                type(value) is not str or not value
                for value in self.required_semantics
            )
        ):
            raise ProductionSharedCapV2Error(
                "production owner site specification is malformed"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "site_key": self.site_key,
            "owner_method": self.owner_method,
            "reducer": self.reducer.value,
            "required_semantics": list(self.required_semantics),
        }


_ATOMIC_FAILURE = (
    "ADMIT_BEFORE_CALLBACK",
    "ATOMIC_RECEIPT_EVENT_PAIR",
    "CALLBACK_OR_JOURNAL_EXCEPTION_FULL_CHARGE_PROTOCOL_FAILURE",
)

OWNER_SITE_SPECS = (
    OwnerSiteSpecV2(
        "common.hash_invocations",
        "shared.hash",
        "record_hash_invocation",
        ReducerV2.SUM,
        _ATOMIC_FAILURE,
    ),
    OwnerSiteSpecV2(
        "common.integrity_checks",
        "shared.integrity",
        "record_integrity_check",
        ReducerV2.SUM,
        _ATOMIC_FAILURE,
    ),
    OwnerSiteSpecV2(
        "common.protocol_checks",
        "shared.protocol",
        "record_protocol_check",
        ReducerV2.SUM,
        _ATOMIC_FAILURE,
    ),
    OwnerSiteSpecV2(
        "io.mounted_bytes_peak",
        "shared.mount",
        "open_mounted_payload",
        ReducerV2.MAX,
        (
            "DISTINCT_PAYLOAD_IDENTITY",
            "OPEN_BEFORE_CHILD_VISIBILITY",
            "CLOSE_ONLY_AFTER_TRUSTED_DESCENDANT_REAP",
            "CLEANUP_REMAINS_AVAILABLE_AFTER_PROTOCOL_FAILURE",
        ),
    ),
    OwnerSiteSpecV2(
        "io.output_bytes",
        "shared.output",
        "begin_route_output",
        ReducerV2.SUM,
        (
            "WHOLE_ROUTE_FIXED_POINT_RESERVE_BEFORE_FIRST_LAUNCH",
            "TRUSTED_EXACT_OUTPUT_FINALIZE",
            "OUTSTANDING_RESERVATION_BLOCKS_CLOSE",
            "CALLBACK_OR_JOURNAL_EXCEPTION_FULL_CHARGE_PROTOCOL_FAILURE",
        ),
    ),
    OwnerSiteSpecV2(
        "io.read_bytes",
        "shared.read",
        "read_registered_payload",
        ReducerV2.SUM,
        (
            "ADMIT_BEFORE_READ_OR_PREAD",
            "TRUSTED_RETURNED_BYTE_COUNT",
            "CALLBACK_OR_JOURNAL_EXCEPTION_FULL_CHARGE_PROTOCOL_FAILURE",
        ),
    ),
    OwnerSiteSpecV2(
        "io.staged_bytes",
        "shared.stage",
        "stage_registered_payload",
        ReducerV2.SUM,
        (
            "NAMED_COPY_OR_BIND_ONLY",
            "GENERIC_IPC_EXCLUDED",
            "ADMIT_BEFORE_SANDBOX_INGRESS",
            "CALLBACK_OR_JOURNAL_EXCEPTION_FULL_CHARGE_PROTOCOL_FAILURE",
        ),
    ),
    OwnerSiteSpecV2(
        "memory.working_bytes_peak",
        "shared.memory",
        "bind_working_hierarchy",
        ReducerV2.MAX,
        (
            "BIND_MEMORY_MAX_BEFORE_FIRST_LAUNCH",
            "TRUSTED_DESCENDANT_REAP",
            "RETAINED_SAME_OFD_MEMORY_PEAK",
            "MEMORY_LIMIT_IS_NOT_ACTUAL_PEAK",
        ),
    ),
    OwnerSiteSpecV2(
        "process.launches",
        "shared.launch",
        "launch_registered_role",
        ReducerV2.SUM,
        (
            "RESERVE_IMMEDIATELY_BEFORE_NATIVE_LAUNCH",
            "POSITIVE_EDGE_REQUIRES_MATCHING_PIDFD",
            "REFUND_ONLY_TRUSTED_NO_CHILD",
            "AMBIGUOUS_OR_EXCEPTION_FULL_CHARGE_PROTOCOL_FAILURE",
        ),
    ),
)

_SITES_BY_PATH = {row.path: row for row in OWNER_SITE_SPECS}


def _fail(message: str) -> NoReturn:
    raise ProductionSharedCapV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ProductionSharedCapV2Error(
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


_MINTABLE_PENDING_ID_DOMAINS = frozenset(
    {
        ACTIVATION_INTERFACE_DOMAIN_CANDIDATE,
        PROFILE_DOMAIN_CANDIDATE,
        ENGINE_DOMAIN_CANDIDATE,
    }
)


def _candidate_content_id(domain: str, value: Any) -> str:
    if type(domain) is not str:
        _fail("pending V2 identity domain must be one exact string")
    if domain not in _MINTABLE_PENDING_ID_DOMAINS:
        _fail("local domain is not mintable by the pending V2 identity authority")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(value)
    ).hexdigest()


_ACTIVATION_ISSUER = object()
_PROFILE_ISSUER = object()

_LIVE_ACTIVATIONS: dict[
    int, tuple["ProductionRouteActivationInterfaceV2", bytes]
] = {}
_LIVE_PROFILES: dict[int, tuple["ProductionSharedCapProfileV2", bytes]] = {}
_LIVE_ENGINES: dict[int, tuple[tuple[Any, ...], bytes, bytes]] = {}


@dataclass(frozen=True, slots=True)
class ProductionRouteActivationInterfaceV2:
    """Issuer-sealed interface whose only legal V2 state is pending."""

    _issuer: InitVar[object]
    route_decision_context_id: str
    decision_point_id: str
    route_attempt_id: str
    v7_authority_request_id: str
    status: ActivationStatusV2
    activation_interface_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ACTIVATION_ISSUER:
            _fail("production activation interface is issuer-owned")
        for name in (
            "route_decision_context_id",
            "decision_point_id",
            "route_attempt_id",
            "v7_authority_request_id",
        ):
            _cid(getattr(self, name), name)
        if self.status is not ActivationStatusV2.V7_AUTHORITY_PENDING:
            _fail("this revision cannot mint a formal V7 activation")
        object.__setattr__(
            self,
            "activation_interface_id",
            _candidate_content_id(
                ACTIVATION_INTERFACE_DOMAIN_CANDIDATE, self._payload()
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.production_shared_cap_activation_interface.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "route_attempt_id": self.route_attempt_id,
            "v7_authority_request_id": self.v7_authority_request_id,
            "status": self.status.value,
            "formal_v7_route_decision_authority_present": False,
            "production_execution_authorized": False,
            "production_owner_sites_wired": False,
            "source_site_manifest_semantically_verified": False,
            "formal_actual_compliance_eligible": False,
            "construction_prerequisite_accepted": False,
            "blocker": BLOCKER,
        }

    def _document_unchecked(self) -> dict[str, Any]:
        payload = self._payload()
        if not hmac.compare_digest(
            _candidate_content_id(ACTIVATION_INTERFACE_DOMAIN_CANDIDATE, payload),
            self.activation_interface_id,
        ):
            _fail("production activation interface changed after issuance")
        return {**payload, "activation_interface_id": self.activation_interface_id}

    def to_document(self) -> dict[str, Any]:
        retained = _LIVE_ACTIVATIONS.get(id(self))
        if retained is None or retained[0] is not self:
            _fail("production activation interface is not a live issuer artifact")
        try:
            document = self._document_unchecked()
        except Exception as error:
            raise ProductionSharedCapV2Error(
                "production activation interface failed identity replay"
            ) from error
        if not hmac.compare_digest(canonical_json_bytes(document), retained[1]):
            _fail("production activation interface changed after issuer sealing")
        return document


def freeze_v7_pending_activation_interface_v2(
    *,
    route_decision_context_id: str,
    decision_point_id: str,
    route_attempt_id: str,
    v7_authority_request_id: str,
) -> ProductionRouteActivationInterfaceV2:
    """Freeze a pending request; this is not a route-decision token."""

    result = ProductionRouteActivationInterfaceV2(
        _ACTIVATION_ISSUER,
        _cid(route_decision_context_id, "route_decision_context_id"),
        _cid(decision_point_id, "decision_point_id"),
        _cid(route_attempt_id, "route_attempt_id"),
        _cid(v7_authority_request_id, "v7_authority_request_id"),
        ActivationStatusV2.V7_AUTHORITY_PENDING,
    )
    _LIVE_ACTIVATIONS[id(result)] = (
        result,
        canonical_json_bytes(result._document_unchecked()),
    )
    return result


def _require_live_activation(value: Any) -> ProductionRouteActivationInterfaceV2:
    if type(value) is not ProductionRouteActivationInterfaceV2:
        _fail("production engine requires the exact V2 activation interface type")
    retained = _LIVE_ACTIVATIONS.get(id(value))
    if retained is None or retained[0] is not value:
        _fail("production activation interface is foreign or caller-minted")
    try:
        current = canonical_json_bytes(value._document_unchecked())
    except Exception as error:
        raise ProductionSharedCapV2Error(
            "production activation interface failed identity replay"
        ) from error
    if not hmac.compare_digest(current, retained[1]):
        _fail("production activation interface changed after issuer sealing")
    if value.status is not ActivationStatusV2.V7_AUTHORITY_PENDING:
        _fail("this revision accepts no non-pending activation state")
    return value


@dataclass(frozen=True, slots=True)
class ProductionSharedCapLimitV2:
    path: str
    site_key: str
    reducer: ReducerV2
    cap: int

    def __post_init__(self) -> None:
        spec = _SITES_BY_PATH.get(self.path)
        if (
            spec is None
            or self.site_key != spec.site_key
            or self.reducer is not spec.reducer
        ):
            _fail("production shared-cap limit changed its embedded owner site")
        _nonnegative(self.cap, f"{self.path} cap")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "site_key": self.site_key,
            "reducer": self.reducer.value,
            "cap": self.cap,
        }


@dataclass(frozen=True, slots=True)
class ProductionSharedCapProfileV2:
    _issuer: InitVar[object]
    activation_interface_id: str
    route_decision_context_id: str
    decision_point_id: str
    route_attempt_id: str
    limits: tuple[ProductionSharedCapLimitV2, ...]
    max_control_cap_checks: int
    profile_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("production shared-cap profile is issuer-owned")
        for name in (
            "activation_interface_id",
            "route_decision_context_id",
            "decision_point_id",
            "route_attempt_id",
        ):
            _cid(getattr(self, name), name)
        if (
            type(self.limits) is not tuple
            or len(self.limits) != 9
            or tuple(row.path for row in self.limits) != SHARED_RESOURCE_PATHS
            or any(
                type(row) is not ProductionSharedCapLimitV2 for row in self.limits
            )
        ):
            _fail("production shared-cap profile must contain the canonical nine rows")
        _positive(self.max_control_cap_checks, "max_control_cap_checks")
        object.__setattr__(
            self,
            "profile_id",
            _candidate_content_id(PROFILE_DOMAIN_CANDIDATE, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.production_shared_cap_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "activation_interface_id": self.activation_interface_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "route_attempt_id": self.route_attempt_id,
            "limits": [row.to_document() for row in self.limits],
            "max_control_cap_checks": self.max_control_cap_checks,
            "owner_site_count": 9,
            "caller_selectable_path": False,
            "formal_v7_route_decision_authority_present": False,
            "production_execution_authorized": False,
            "production_owner_sites_wired": False,
            "source_site_manifest_semantically_verified": False,
            "formal_actual_compliance_eligible": False,
            "blocker": BLOCKER,
        }

    def _document_unchecked(self) -> dict[str, Any]:
        payload = self._payload()
        if not hmac.compare_digest(
            _candidate_content_id(PROFILE_DOMAIN_CANDIDATE, payload), self.profile_id
        ):
            _fail("production shared-cap profile changed after issuance")
        return {**payload, "production_shared_cap_profile_id": self.profile_id}

    def to_document(self) -> dict[str, Any]:
        retained = _LIVE_PROFILES.get(id(self))
        if retained is None or retained[0] is not self:
            _fail("production shared-cap profile is not a live issuer artifact")
        try:
            document = self._document_unchecked()
        except Exception as error:
            raise ProductionSharedCapV2Error(
                "production shared-cap profile failed identity replay"
            ) from error
        if not hmac.compare_digest(canonical_json_bytes(document), retained[1]):
            _fail("production shared-cap profile changed after issuer sealing")
        return document


def freeze_production_shared_cap_profile_v2(
    *,
    activation: ProductionRouteActivationInterfaceV2,
    caps: Mapping[str, int],
    max_control_cap_checks: int,
) -> ProductionSharedCapProfileV2:
    activation = _require_live_activation(activation)
    if type(caps) is not dict or set(caps) != set(SHARED_RESOURCE_PATHS):
        _fail("production shared caps must cover exactly the nine embedded paths")
    limits = tuple(
        ProductionSharedCapLimitV2(
            spec.path,
            spec.site_key,
            spec.reducer,
            _nonnegative(caps[spec.path], spec.path),
        )
        for spec in OWNER_SITE_SPECS
    )
    result = ProductionSharedCapProfileV2(
        _PROFILE_ISSUER,
        activation.activation_interface_id,
        activation.route_decision_context_id,
        activation.decision_point_id,
        activation.route_attempt_id,
        limits,
        _positive(max_control_cap_checks, "max_control_cap_checks"),
    )
    _LIVE_PROFILES[id(result)] = (
        result,
        canonical_json_bytes(result._document_unchecked()),
    )
    return result


def _require_live_profile(value: Any) -> ProductionSharedCapProfileV2:
    if type(value) is not ProductionSharedCapProfileV2:
        _fail("production engine requires the exact V2 profile type")
    retained = _LIVE_PROFILES.get(id(value))
    if retained is None or retained[0] is not value:
        _fail("production shared-cap profile is foreign or caller-minted")
    try:
        current = canonical_json_bytes(value._document_unchecked())
    except Exception as error:
        raise ProductionSharedCapV2Error(
            "production shared-cap profile failed identity replay"
        ) from error
    if not hmac.compare_digest(current, retained[1]):
        _fail("production shared-cap profile changed after issuer sealing")
    return value


ProductionSharedCapEngineV2 = tuple
"""Exact immutable pending capability type; subclasses are not authorities."""

_ENGINE_RUNTIME_SCHEMA_V2 = "acfqp.production_shared_cap_engine_runtime.v2"
_ENGINE_ID_INDEX = 1
_ENGINE_STATE_INDEX = 2
_ENGINE_OWNER_SENTINELS_INDEX = 3


def _engine_payload(
    activation: ProductionRouteActivationInterfaceV2,
    profile: ProductionSharedCapProfileV2,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.production_shared_cap_engine.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "activation_interface_id": activation.activation_interface_id,
        "production_shared_cap_profile_id": profile.profile_id,
        "RouteDecisionContext_id": activation.route_decision_context_id,
        "decision_point_id": activation.decision_point_id,
        "route_attempt_id": activation.route_attempt_id,
        "state": ProductionEngineStateV2.V7_AUTHORITY_PENDING.value,
        "owner_sites": [row.to_document() for row in OWNER_SITE_SPECS],
        "owner_site_count": 9,
        "owner_surface_kind": "EXACT_IMMUTABLE_TUPLE_PENDING_SENTINELS",
        "exact_tuple_capability_required": True,
        "tuple_subclasses_authoritative": False,
        "caller_created_exact_tuple_authoritative": False,
        "reachable_mutable_backing_present": False,
        "caller_selectable_path": False,
        "callable_owner_surface_present": False,
        "paired_receipt_and_semantic_event_required": True,
        "formal_v7_route_decision_authority_present": False,
        "production_execution_authorized": False,
        "production_owner_sites_wired": False,
        "source_site_manifest_semantically_verified": False,
        "formal_actual_compliance_eligible": False,
        "construction_prerequisite_accepted": False,
        "preproduction_kernel_receipts_accepted": False,
        "official_execution_allowed": False,
        "blocker": BLOCKER,
    }


def _engine_runtime_document_v2(value: Any) -> dict[str, Any]:
    if (
        type(value) is not tuple
        or len(value) != 4
        or value[0] != _ENGINE_RUNTIME_SCHEMA_V2
        or type(value[_ENGINE_ID_INDEX]) is not str
        or type(value[_ENGINE_STATE_INDEX]) is not str
        or type(value[_ENGINE_OWNER_SENTINELS_INDEX]) is not tuple
    ):
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap engine runtime tuple is malformed"
        )
    owner_rows = value[_ENGINE_OWNER_SENTINELS_INDEX]
    if (
        len(owner_rows) != len(OWNER_SITE_SPECS)
        or any(
            type(row) is not tuple
            or len(row) != 2
            or type(row[0]) is not str
            or type(row[1]) is not str
            for row in owner_rows
        )
        or tuple(row[0] for row in owner_rows)
        != tuple(site.owner_method for site in OWNER_SITE_SPECS)
        or any(
            row[1] != ActivationStatusV2.V7_AUTHORITY_PENDING.value
            for row in owner_rows
        )
    ):
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap owner sentinel tuple is malformed"
        )
    return {
        "runtime_schema": _ENGINE_RUNTIME_SCHEMA_V2,
        "production_shared_cap_engine_id": value[_ENGINE_ID_INDEX],
        "state": value[_ENGINE_STATE_INDEX],
        "owner_sentinels": [list(row) for row in owner_rows],
    }


def _require_live_engine_v2(value: Any) -> tuple[tuple[Any, ...], bytes, bytes]:
    if type(value) is not ProductionSharedCapEngineV2:
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap engine is not one exact tuple capability"
        )
    retained = _LIVE_ENGINES.get(id(value))
    if retained is None or retained[0] is not value:
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap engine is not a live issuer object"
        )
    try:
        current_runtime = canonical_json_bytes(_engine_runtime_document_v2(value))
    except Exception as error:
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap engine runtime failed identity replay"
        ) from error
    if not hmac.compare_digest(current_runtime, retained[2]):
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap engine runtime changed after issuer sealing"
        )
    return retained


def production_shared_cap_engine_document_v2(value: Any) -> dict[str, Any]:
    """Replay the sealed document of one live immutable pending capability."""

    retained = _require_live_engine_v2(value)
    document = loads_canonical_json(retained[1])
    if type(document) is not dict:
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap engine document is malformed"
        )
    claimed_id = document.pop("production_shared_cap_engine_id", None)
    if not hmac.compare_digest(
        _candidate_content_id(ENGINE_DOMAIN_CANDIDATE, document),
        _cid(claimed_id, "production_shared_cap_engine_id"),
    ):
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap engine document failed content replay"
        )
    return {**document, "production_shared_cap_engine_id": claimed_id}


def production_shared_cap_engine_state_v2(value: Any) -> ProductionEngineStateV2:
    _require_live_engine_v2(value)
    try:
        return ProductionEngineStateV2(value[_ENGINE_STATE_INDEX])
    except (IndexError, TypeError, ValueError) as error:
        raise ProductionSharedCapProtocolFailureV2(
            "production shared-cap engine state is malformed"
        ) from error


def production_shared_cap_engine_id_v2(value: Any) -> str:
    _require_live_engine_v2(value)
    return _cid(value[_ENGINE_ID_INDEX], "engine ID")


def production_shared_cap_engine_owner_sentinel_v2(
    value: Any, owner_method: str
) -> str:
    """Return the non-callable pending sentinel for one frozen owner name."""

    _require_live_engine_v2(value)
    if type(owner_method) is not str:
        raise ProductionSharedCapProtocolFailureV2(
            "owner method lookup requires one exact string"
        )
    for method, sentinel in value[_ENGINE_OWNER_SENTINELS_INDEX]:
        if method == owner_method:
            return sentinel
    raise ProductionSharedCapProtocolFailureV2(
        "owner method is absent from the frozen nine-name surface"
    )


def prepare_production_shared_cap_engine_v2(
    *,
    activation: ProductionRouteActivationInterfaceV2,
    profile: ProductionSharedCapProfileV2,
) -> tuple[Any, ...]:
    """Return a sealed pending facade, never an executable production session."""

    activation = _require_live_activation(activation)
    profile = _require_live_profile(profile)
    expected = (
        activation.activation_interface_id,
        activation.route_decision_context_id,
        activation.decision_point_id,
        activation.route_attempt_id,
    )
    actual = (
        profile.activation_interface_id,
        profile.route_decision_context_id,
        profile.decision_point_id,
        profile.route_attempt_id,
    )
    if actual != expected:
        _fail("production shared-cap profile is foreign to the activation interface")
    payload = _engine_payload(activation, profile)
    engine_id = _candidate_content_id(ENGINE_DOMAIN_CANDIDATE, payload)
    document = {**payload, "production_shared_cap_engine_id": engine_id}
    owner_sentinels = tuple(
        (
            site.owner_method,
            ActivationStatusV2.V7_AUTHORITY_PENDING.value,
        )
        for site in OWNER_SITE_SPECS
    )
    result = (
        _ENGINE_RUNTIME_SCHEMA_V2,
        engine_id,
        ProductionEngineStateV2.V7_AUTHORITY_PENDING.value,
        owner_sentinels,
    )
    runtime_document = _engine_runtime_document_v2(result)
    _LIVE_ENGINES[id(result)] = (
        result,
        canonical_json_bytes(document),
        canonical_json_bytes(runtime_document),
    )
    return result


def _issue_preproduction_atomic_kernel_v2(
    profile: ProductionSharedCapProfileV2,
    *,
    journal_sink: Callable[[Any], None] | None = None,
) -> NoReturn:
    """Fail closed: pending profiles cannot issue a private live kernel."""

    _require_live_profile(profile)
    del journal_sink
    raise V7AuthorityPendingV2(
        "preproduction atomic kernel issuance is locked by V7_AUTHORITY_PENDING"
    )


__all__ = [
    "ActivationStatusV2",
    "NativeLaunchOutcomeV2",
    "OWNER_SITE_SPECS",
    "ProductionEngineStateV2",
    "ProductionRouteActivationInterfaceV2",
    "ProductionSharedCapEngineV2",
    "ProductionSharedCapExhaustedV2",
    "ProductionSharedCapProfileV2",
    "ProductionSharedCapProtocolFailureV2",
    "ProductionSharedCapV2Error",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SandboxIngressKindV2",
    "SHARED_RESOURCE_PATHS",
    "V7AuthorityPendingV2",
    "freeze_production_shared_cap_profile_v2",
    "freeze_v7_pending_activation_interface_v2",
    "prepare_production_shared_cap_engine_v2",
    "production_shared_cap_engine_document_v2",
    "production_shared_cap_engine_id_v2",
    "production_shared_cap_engine_owner_sentinel_v2",
    "production_shared_cap_engine_state_v2",
]
