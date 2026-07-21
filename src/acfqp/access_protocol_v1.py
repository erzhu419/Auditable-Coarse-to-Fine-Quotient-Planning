"""Fail-closed Phase-3E estimate-before-execute access protocol.

This module implements the FQ13 ordering boundary without changing the
historical Phase-3B/3C/3D runners.  An access log is first frozen as an
immutable preselection prefix, a marginal route decision is then attested,
and only the selected route's execution operations become reachable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, TypeVar

from acfqp.phase3e_ids import (
    ACCESS_EVENT_LOG_DOMAIN,
    FORBIDDEN_ACCESS_VIOLATION_DOMAIN,
    PROTOCOL_SEQUENCE_PROFILE_DOMAIN,
    ROUTE_DECISION_FREEZE_ATTESTATION_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import MarginalRouteDecisionV1, RouteSelection


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "phase3e_estimate_before_execute_access_v1"
PROTOCOL_FAILURE_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PROTOCOL_FAILURE_CODE = "PROTOCOL_FAILURE"


class AccessProtocolV1Error(ValueError):
    """A typed access-protocol object or replay is invalid."""


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise AccessProtocolV1Error(str(error)) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise AccessProtocolV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


def _positive(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise AccessProtocolV1Error(f"{field} must be a positive integer")
    return value


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise AccessProtocolV1Error(f"{field} must be a nonnegative integer")
    return value


E = TypeVar("E", bound=Enum)


def _enum(value: Any, enum_type: type[E], field: str) -> E:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise AccessProtocolV1Error(f"invalid {field}: {value!r}") from error


class AccessRouteScope(str, Enum):
    COMMON = "COMMON"
    LOCAL = "LOCAL"
    FALLBACK = "FALLBACK"


class AccessOperation(str, Enum):
    READ_FROZEN_RAPM = "READ_FROZEN_RAPM"
    READ_FROZEN_BUILD_EPOCH = "READ_FROZEN_BUILD_EPOCH"
    READ_FAILED_CERTIFICATE = "READ_FAILED_CERTIFICATE"
    READ_SELECTED_PLAN = "READ_SELECTED_PLAN"
    READ_ACTION_CATALOGUE = "READ_ACTION_CATALOGUE"
    READ_FRONTIER_IDENTITIES = "READ_FRONTIER_IDENTITIES"
    READ_PROOF_CIRCUIT_METADATA = "READ_PROOF_CIRCUIT_METADATA"
    READ_PREREGISTERED_CARDINALITIES = "READ_PREREGISTERED_CARDINALITIES"
    READ_CAP_REGISTRY = "READ_CAP_REGISTRY"
    READ_FORMULA_REGISTRY = "READ_FORMULA_REGISTRY"
    READ_PROFILE_REGISTRY = "READ_PROFILE_REGISTRY"

    # These accesses are common to both selected routes, but are legal only
    # after the route-decision freeze.  They make the previously implicit
    # runtime-CAS resolution/construction boundary replayable.
    RESOLVE_RUNTIME_CAS = "RESOLVE_RUNTIME_CAS"
    OPEN_RUNTIME_PRIVATE_LEASE = "OPEN_RUNTIME_PRIVATE_LEASE"
    CONSTRUCT_SELECTED_EXECUTOR = "CONSTRUCT_SELECTED_EXECUTOR"

    KERNEL_STEP = "KERNEL_STEP"
    GROUND_OUTCOME_ENUMERATION = "GROUND_OUTCOME_ENUMERATION"
    LOCAL_SLICE_MATERIALIZATION = "LOCAL_SLICE_MATERIALIZATION"
    LOCAL_CAPABILITY_COMPILATION = "LOCAL_CAPABILITY_COMPILATION"
    LOCAL_WORKER_LAUNCH = "LOCAL_WORKER_LAUNCH"
    LOCAL_PATCH_STITCH = "LOCAL_PATCH_STITCH"
    LOCAL_POSTAUDIT = "LOCAL_POSTAUDIT"
    FALLBACK_SOLVER_INVOCATION = "FALLBACK_SOLVER_INVOCATION"
    FALLBACK_WORKER_LAUNCH = "FALLBACK_WORKER_LAUNCH"

    LOCAL_CAPABILITY_ARTIFACT = "LOCAL_CAPABILITY_ARTIFACT"
    LOCAL_WORKER_RESULT_ARTIFACT = "LOCAL_WORKER_RESULT_ARTIFACT"
    LOCAL_STITCH_ARTIFACT = "LOCAL_STITCH_ARTIFACT"
    LOCAL_POSTAUDIT_ARTIFACT = "LOCAL_POSTAUDIT_ARTIFACT"
    FALLBACK_RESULT_ARTIFACT = "FALLBACK_RESULT_ARTIFACT"


PRESELECTION_READ_OPERATIONS = tuple(
    sorted(
        (
            AccessOperation.READ_FROZEN_RAPM,
            AccessOperation.READ_FROZEN_BUILD_EPOCH,
            AccessOperation.READ_FAILED_CERTIFICATE,
            AccessOperation.READ_SELECTED_PLAN,
            AccessOperation.READ_ACTION_CATALOGUE,
            AccessOperation.READ_FRONTIER_IDENTITIES,
            AccessOperation.READ_PROOF_CIRCUIT_METADATA,
            AccessOperation.READ_PREREGISTERED_CARDINALITIES,
            AccessOperation.READ_CAP_REGISTRY,
            AccessOperation.READ_FORMULA_REGISTRY,
            AccessOperation.READ_PROFILE_REGISTRY,
        ),
        key=lambda operation: operation.value,
    )
)

ROUTE_SCOPED_OPERATIONS = tuple(
    sorted(
        (
            AccessOperation.KERNEL_STEP,
            AccessOperation.GROUND_OUTCOME_ENUMERATION,
            AccessOperation.RESOLVE_RUNTIME_CAS,
            AccessOperation.OPEN_RUNTIME_PRIVATE_LEASE,
            AccessOperation.CONSTRUCT_SELECTED_EXECUTOR,
        ),
        key=lambda operation: operation.value,
    )
)

LOCAL_ONLY_OPERATIONS = tuple(
    sorted(
        (
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessOperation.LOCAL_CAPABILITY_COMPILATION,
            AccessOperation.LOCAL_WORKER_LAUNCH,
            AccessOperation.LOCAL_PATCH_STITCH,
            AccessOperation.LOCAL_POSTAUDIT,
            AccessOperation.LOCAL_CAPABILITY_ARTIFACT,
            AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT,
            AccessOperation.LOCAL_STITCH_ARTIFACT,
            AccessOperation.LOCAL_POSTAUDIT_ARTIFACT,
        ),
        key=lambda operation: operation.value,
    )
)

FALLBACK_ONLY_OPERATIONS = tuple(
    sorted(
        (
            AccessOperation.FALLBACK_SOLVER_INVOCATION,
            AccessOperation.FALLBACK_WORKER_LAUNCH,
            AccessOperation.FALLBACK_RESULT_ARTIFACT,
        ),
        key=lambda operation: operation.value,
    )
)

ARTIFACT_OPERATIONS = frozenset(
    {
        AccessOperation.LOCAL_CAPABILITY_ARTIFACT,
        AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT,
        AccessOperation.LOCAL_STITCH_ARTIFACT,
        AccessOperation.LOCAL_POSTAUDIT_ARTIFACT,
        AccessOperation.FALLBACK_RESULT_ARTIFACT,
    }
)

# Every preselection read is identity-bearing.  Recording only the operation
# name allowed a caller to replace the frozen RAPM, plan, cap, or formula while
# preserving the same access-log hash shape.
IDENTITY_BEARING_OPERATIONS = (
    frozenset(PRESELECTION_READ_OPERATIONS)
    | ARTIFACT_OPERATIONS
    | frozenset(
        {
            AccessOperation.RESOLVE_RUNTIME_CAS,
            AccessOperation.OPEN_RUNTIME_PRIVATE_LEASE,
            AccessOperation.CONSTRUCT_SELECTED_EXECUTOR,
        }
    )
)

# Only these route-scoped events carry ground-transition stage semantics.
# Runtime-CAS operations may precede local stage 1 and must not be mistaken
# for an unscoped kernel access merely because both routes share them.
GROUND_TRANSITION_OPERATIONS = frozenset(
    {
        AccessOperation.KERNEL_STEP,
        AccessOperation.GROUND_OUTCOME_ENUMERATION,
    }
)


class AccessViolationReason(str, Enum):
    PRESELECTION_FORBIDDEN_ACCESS = "PRESELECTION_FORBIDDEN_ACCESS"
    PRESELECTION_ROUTE_SCOPE_VIOLATION = "PRESELECTION_ROUTE_SCOPE_VIOLATION"
    LOCAL_ACCESS_ON_FALLBACK_ROUTE = "LOCAL_ACCESS_ON_FALLBACK_ROUTE"
    FALLBACK_ACCESS_ON_LOCAL_ROUTE = "FALLBACK_ACCESS_ON_LOCAL_ROUTE"
    SELECTED_ROUTE_SCOPE_MISMATCH = "SELECTED_ROUTE_SCOPE_MISMATCH"
    LOCAL_STAGE_ORDER_VIOLATION = "LOCAL_STAGE_ORDER_VIOLATION"


@dataclass(frozen=True, slots=True)
class ProtocolSequenceProfileV1:
    allowed_preselection_operations: tuple[
        AccessOperation, ...
    ] = PRESELECTION_READ_OPERATIONS
    route_scoped_operations: tuple[AccessOperation, ...] = ROUTE_SCOPED_OPERATIONS
    local_only_operations: tuple[AccessOperation, ...] = LOCAL_ONLY_OPERATIONS
    fallback_only_operations: tuple[AccessOperation, ...] = FALLBACK_ONLY_OPERATIONS
    profile_key: str = PROFILE_KEY
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.profile_key != PROFILE_KEY:
            raise AccessProtocolV1Error("protocol sequence profile identity mismatch")
        if self.allowed_preselection_operations != PRESELECTION_READ_OPERATIONS:
            raise AccessProtocolV1Error("preselection read whitelist changed")
        if self.route_scoped_operations != ROUTE_SCOPED_OPERATIONS:
            raise AccessProtocolV1Error("route-scoped operation registry changed")
        if self.local_only_operations != LOCAL_ONLY_OPERATIONS:
            raise AccessProtocolV1Error("local-only operation registry changed")
        if self.fallback_only_operations != FALLBACK_ONLY_OPERATIONS:
            raise AccessProtocolV1Error("fallback-only operation registry changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.protocol_sequence_profile.v1",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "allowed_preselection_operations": [
                operation.value for operation in self.allowed_preselection_operations
            ],
            "route_scoped_operations": [
                operation.value for operation in self.route_scoped_operations
            ],
            "local_only_operations": [
                operation.value for operation in self.local_only_operations
            ],
            "fallback_only_operations": [
                operation.value for operation in self.fallback_only_operations
            ],
        }

    @property
    def protocol_sequence_profile_id(self) -> str:
        return content_id(PROTOCOL_SEQUENCE_PROFILE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ProtocolSequenceProfileV1":
        expected = {
            "schema",
            "schema_version",
            "profile_key",
            "allowed_preselection_operations",
            "route_scoped_operations",
            "local_only_operations",
            "fallback_only_operations",
            "protocol_sequence_profile_id",
        }
        _fields(document, expected, "protocol sequence profile")
        if document["schema"] != "acfqp.protocol_sequence_profile.v1":
            raise AccessProtocolV1Error("protocol sequence profile schema mismatch")

        def operations(field: str) -> tuple[AccessOperation, ...]:
            values = document[field]
            if type(values) is not list:
                raise AccessProtocolV1Error(f"{field} must be a list")
            return tuple(_enum(value, AccessOperation, field) for value in values)

        result = cls(
            operations("allowed_preselection_operations"),
            operations("route_scoped_operations"),
            operations("local_only_operations"),
            operations("fallback_only_operations"),
            document["profile_key"],
            document["schema_version"],
        )
        _cid(document["protocol_sequence_profile_id"], "profile ID")
        if (
            document["protocol_sequence_profile_id"]
            != result.protocol_sequence_profile_id
        ):
            raise AccessProtocolV1Error("protocol sequence profile content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class AccessEventV1:
    sequence_number: int
    route_attempt_id: str
    decision_point_id: str
    operation: AccessOperation
    route_scope: AccessRouteScope
    artifact_id: str | None = None

    def __post_init__(self) -> None:
        _positive(self.sequence_number, "access sequence number")
        _cid(self.route_attempt_id, "route_attempt_id")
        _cid(self.decision_point_id, "decision_point_id")
        object.__setattr__(
            self,
            "operation",
            _enum(self.operation, AccessOperation, "access operation"),
        )
        object.__setattr__(
            self,
            "route_scope",
            _enum(self.route_scope, AccessRouteScope, "access route scope"),
        )
        if self.operation in IDENTITY_BEARING_OPERATIONS:
            _cid(self.artifact_id, "artifact_id")
        elif self.artifact_id is not None:
            raise AccessProtocolV1Error(
                "only registered identity-bearing events may carry artifact_id"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_number": self.sequence_number,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "operation": self.operation.value,
            "route_scope": self.route_scope.value,
            "artifact_id": self.artifact_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "AccessEventV1":
        _fields(
            document,
            {
                "sequence_number",
                "route_attempt_id",
                "decision_point_id",
                "operation",
                "route_scope",
                "artifact_id",
            },
            "access event",
        )
        return cls(
            document["sequence_number"],
            document["route_attempt_id"],
            document["decision_point_id"],
            _enum(document["operation"], AccessOperation, "access operation"),
            _enum(document["route_scope"], AccessRouteScope, "access route scope"),
            document["artifact_id"],
        )


@dataclass(frozen=True, slots=True)
class AccessEventLogV1:
    route_attempt_id: str
    decision_point_id: str
    protocol_sequence_profile_id: str
    events: tuple[AccessEventV1, ...]
    route_decision_id: str | None = None
    route_decision_freeze_attestation_id: str | None = None
    freeze_after_sequence: int | None = None
    prefreeze_access_event_log_id: str | None = None

    def __post_init__(self) -> None:
        _cid(self.route_attempt_id, "route_attempt_id")
        _cid(self.decision_point_id, "decision_point_id")
        _cid(self.protocol_sequence_profile_id, "protocol_sequence_profile_id")
        if type(self.events) is not tuple:
            raise AccessProtocolV1Error("access events must be an immutable tuple")
        for expected_sequence, event in enumerate(self.events, start=1):
            if event.sequence_number != expected_sequence:
                raise AccessProtocolV1Error(
                    "access event sequence must be contiguous, monotonic, "
                    "and start at 1"
                )
            if (
                event.route_attempt_id != self.route_attempt_id
                or event.decision_point_id != self.decision_point_id
            ):
                raise AccessProtocolV1Error(
                    "access event is bound to another attempt or decision point"
                )
        freeze_fields = (
            self.route_decision_id,
            self.route_decision_freeze_attestation_id,
            self.freeze_after_sequence,
            self.prefreeze_access_event_log_id,
        )
        if all(value is None for value in freeze_fields):
            return
        if any(value is None for value in freeze_fields):
            raise AccessProtocolV1Error(
                "frozen access log requires the complete freeze identity chain"
            )
        _cid(self.route_decision_id, "route_decision_id")
        _cid(
            self.route_decision_freeze_attestation_id,
            "route_decision_freeze_attestation_id",
        )
        _cid(self.prefreeze_access_event_log_id, "prefreeze_access_event_log_id")
        freeze_after = _nonnegative(
            self.freeze_after_sequence,
            "freeze_after_sequence",
        )
        if freeze_after > len(self.events):
            raise AccessProtocolV1Error(
                "freeze boundary lies beyond the recorded access sequence"
            )

    @property
    def is_frozen(self) -> bool:
        return self.route_decision_id is not None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.access_event_log.v1",
            "schema_version": SCHEMA_VERSION,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
            "events": [event.to_dict() for event in self.events],
            "route_decision_id": self.route_decision_id,
            "route_decision_freeze_attestation_id": (
                self.route_decision_freeze_attestation_id
            ),
            "freeze_after_sequence": self.freeze_after_sequence,
            "prefreeze_access_event_log_id": self.prefreeze_access_event_log_id,
        }

    @property
    def access_event_log_id(self) -> str:
        return content_id(ACCESS_EVENT_LOG_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "access_event_log_id": self.access_event_log_id}

    def prefreeze_prefix(self) -> "AccessEventLogV1":
        count = len(self.events) if not self.is_frozen else self.freeze_after_sequence
        if count is None:  # guarded by is_frozen, kept for type narrowing
            raise AccessProtocolV1Error("frozen log is missing its boundary")
        return AccessEventLogV1(
            self.route_attempt_id,
            self.decision_point_id,
            self.protocol_sequence_profile_id,
            self.events[:count],
        )

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "AccessEventLogV1":
        expected = {
            "schema",
            "schema_version",
            "route_attempt_id",
            "decision_point_id",
            "protocol_sequence_profile_id",
            "events",
            "route_decision_id",
            "route_decision_freeze_attestation_id",
            "freeze_after_sequence",
            "prefreeze_access_event_log_id",
            "access_event_log_id",
        }
        _fields(document, expected, "access event log")
        if (
            document["schema"] != "acfqp.access_event_log.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise AccessProtocolV1Error("access event log schema mismatch")
        rows = document["events"]
        if type(rows) is not list:
            raise AccessProtocolV1Error("access events must be a list")
        result = cls(
            document["route_attempt_id"],
            document["decision_point_id"],
            document["protocol_sequence_profile_id"],
            tuple(AccessEventV1.from_dict(row) for row in rows),
            document["route_decision_id"],
            document["route_decision_freeze_attestation_id"],
            document["freeze_after_sequence"],
            document["prefreeze_access_event_log_id"],
        )
        _cid(document["access_event_log_id"], "access_event_log_id")
        if document["access_event_log_id"] != result.access_event_log_id:
            raise AccessProtocolV1Error("access event log content ID mismatch")
        return result


def _violation_reason(
    event: AccessEventV1,
    selected_route: RouteSelection | None,
) -> AccessViolationReason | None:
    if selected_route is None:
        if event.operation not in PRESELECTION_READ_OPERATIONS:
            return AccessViolationReason.PRESELECTION_FORBIDDEN_ACCESS
        if event.route_scope is not AccessRouteScope.COMMON:
            return AccessViolationReason.PRESELECTION_ROUTE_SCOPE_VIOLATION
        return None

    if event.operation in PRESELECTION_READ_OPERATIONS:
        if event.route_scope is AccessRouteScope.COMMON:
            return None
        return AccessViolationReason.SELECTED_ROUTE_SCOPE_MISMATCH

    if event.operation in ROUTE_SCOPED_OPERATIONS:
        expected_scope = (
            AccessRouteScope.LOCAL
            if selected_route is RouteSelection.LOCAL
            else AccessRouteScope.FALLBACK
        )
        if event.route_scope is not expected_scope:
            return AccessViolationReason.SELECTED_ROUTE_SCOPE_MISMATCH
        return None

    if event.operation in LOCAL_ONLY_OPERATIONS:
        if selected_route is RouteSelection.FALLBACK:
            return AccessViolationReason.LOCAL_ACCESS_ON_FALLBACK_ROUTE
        if event.route_scope is not AccessRouteScope.LOCAL:
            return AccessViolationReason.SELECTED_ROUTE_SCOPE_MISMATCH
        return None

    if event.operation in FALLBACK_ONLY_OPERATIONS:
        if selected_route is RouteSelection.LOCAL:
            return AccessViolationReason.FALLBACK_ACCESS_ON_LOCAL_ROUTE
        if event.route_scope is not AccessRouteScope.FALLBACK:
            return AccessViolationReason.SELECTED_ROUTE_SCOPE_MISMATCH
        return None

    return AccessViolationReason.SELECTED_ROUTE_SCOPE_MISMATCH


_LOCAL_STAGE_MARKERS: Mapping[AccessOperation, int] = {
    AccessOperation.LOCAL_SLICE_MATERIALIZATION: 1,
    AccessOperation.LOCAL_CAPABILITY_COMPILATION: 2,
    AccessOperation.LOCAL_WORKER_LAUNCH: 3,
    AccessOperation.LOCAL_PATCH_STITCH: 4,
    AccessOperation.LOCAL_POSTAUDIT: 5,
}

_LOCAL_ARTIFACT_STAGE: Mapping[AccessOperation, int] = {
    AccessOperation.LOCAL_CAPABILITY_ARTIFACT: 2,
    AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT: 3,
    AccessOperation.LOCAL_STITCH_ARTIFACT: 4,
    AccessOperation.LOCAL_POSTAUDIT_ARTIFACT: 5,
}


def local_execution_order_violation_v1(
    events: tuple[AccessEventV1, ...],
    *,
    freeze_after_sequence: int,
) -> AccessEventV1 | None:
    """Return the first local event that skips or reverses a required stage."""

    stage = 0
    for event in events:
        if event.sequence_number <= freeze_after_sequence:
            continue
        if event.route_scope is not AccessRouteScope.LOCAL:
            continue
        marker = _LOCAL_STAGE_MARKERS.get(event.operation)
        if marker is not None:
            if marker < stage or marker > stage + 1:
                return event
            stage = max(stage, marker)
            continue
        artifact_stage = _LOCAL_ARTIFACT_STAGE.get(event.operation)
        if artifact_stage is not None and artifact_stage != stage:
            return event
        if event.operation in GROUND_TRANSITION_OPERATIONS and stage not in {1, 5}:
            # Ground transitions belong to materialization or the post-audit,
            # never to estimate/compile/worker/stitch.
            return event
    return None


def local_execution_stages_v1(
    events: tuple[AccessEventV1, ...],
    *,
    freeze_after_sequence: int,
) -> tuple[int, ...]:
    """Return the distinct required local stages reached in log order."""

    reached: list[int] = []
    for event in events:
        if event.sequence_number <= freeze_after_sequence:
            continue
        stage = _LOCAL_STAGE_MARKERS.get(event.operation)
        if stage is not None and (not reached or reached[-1] != stage):
            reached.append(stage)
    return tuple(reached)


def _verified_route_decision(
    value: Any,
    *,
    route_attempt_id: str,
    decision_point_id: str,
) -> tuple[MarginalRouteDecisionV1, str]:
    """Extract a decision only from the semantic authority runtime handle."""

    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        SemanticVerificationV1Error,
        require_semantic_verification_result_v1,
    )
    try:
        result = require_semantic_verification_result_v1(
            value, SemanticRole.ROUTE_DECISION
        )
    except SemanticVerificationV1Error as error:
        raise AccessProtocolV1Error(
            "route freeze requires authority-bearing ROUTE_DECISION semantic evidence"
        ) from error
    if not isinstance(result.artifact, MarginalRouteDecisionV1):
        raise AccessProtocolV1Error(
            "verified route-decision result carries the wrong artifact type"
        )
    decision = result.artifact
    attestation = result.attestation
    if (
        attestation.artifact_id != decision.route_decision_id
        or attestation.route_attempt_id != route_attempt_id
        or attestation.decision_point_id != decision_point_id
        or decision.decision_point_id != decision_point_id
        or result.outcome != decision.selected_route.value
    ):
        raise AccessProtocolV1Error(
            "verified route-decision evidence is bound to another attempt or point"
        )
    return decision, attestation.verification_attestation_id


@dataclass(frozen=True, slots=True)
class RouteDecisionFreezeAttestationV1:
    route_attempt_id: str
    decision_point_id: str
    route_decision_id: str
    route_decision_verification_attestation_id: str
    selected_route: RouteSelection
    protocol_sequence_profile_id: str
    prefreeze_access_event_log_id: str
    last_preselection_sequence: int

    def __post_init__(self) -> None:
        _cid(self.route_attempt_id, "route_attempt_id")
        _cid(self.decision_point_id, "decision_point_id")
        _cid(self.route_decision_id, "route_decision_id")
        _cid(
            self.route_decision_verification_attestation_id,
            "route_decision_verification_attestation_id",
        )
        _cid(self.protocol_sequence_profile_id, "protocol_sequence_profile_id")
        _cid(self.prefreeze_access_event_log_id, "prefreeze_access_event_log_id")
        _nonnegative(self.last_preselection_sequence, "last_preselection_sequence")
        object.__setattr__(
            self,
            "selected_route",
            _enum(self.selected_route, RouteSelection, "selected_route"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_decision_freeze_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "route_decision_id": self.route_decision_id,
            "route_decision_verification_attestation_id": (
                self.route_decision_verification_attestation_id
            ),
            "selected_route": self.selected_route.value,
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
            "prefreeze_access_event_log_id": self.prefreeze_access_event_log_id,
            "last_preselection_sequence": self.last_preselection_sequence,
        }

    @property
    def route_decision_freeze_attestation_id(self) -> str:
        return content_id(
            ROUTE_DECISION_FREEZE_ATTESTATION_DOMAIN,
            self._payload(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "route_decision_freeze_attestation_id": (
                self.route_decision_freeze_attestation_id
            ),
        }

    @classmethod
    def freeze(
        cls,
        profile: ProtocolSequenceProfileV1,
        prefreeze_log: AccessEventLogV1,
        decision_result: Any,
    ) -> "RouteDecisionFreezeAttestationV1":
        decision, decision_attestation_id = _verified_route_decision(
            decision_result,
            route_attempt_id=prefreeze_log.route_attempt_id,
            decision_point_id=prefreeze_log.decision_point_id,
        )
        if prefreeze_log.is_frozen:
            raise AccessProtocolV1Error(
                "route decision requires an unfrozen prefix log"
            )
        if prefreeze_log.decision_point_id != decision.decision_point_id:
            raise AccessProtocolV1Error("route decision and access log point differ")
        if (
            prefreeze_log.protocol_sequence_profile_id
            != profile.protocol_sequence_profile_id
        ):
            raise AccessProtocolV1Error("access log uses another sequence profile")
        for event in prefreeze_log.events:
            reason = _violation_reason(event, None)
            if reason is not None:
                raise AccessProtocolV1Error(
                    f"cannot freeze after forbidden preselection access: {reason.value}"
                )
        return cls(
            prefreeze_log.route_attempt_id,
            prefreeze_log.decision_point_id,
            decision.route_decision_id,
            decision_attestation_id,
            decision.selected_route,
            profile.protocol_sequence_profile_id,
            prefreeze_log.access_event_log_id,
            len(prefreeze_log.events),
        )

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "RouteDecisionFreezeAttestationV1":
        expected = {
            "schema",
            "schema_version",
            "route_attempt_id",
            "decision_point_id",
            "route_decision_id",
            "route_decision_verification_attestation_id",
            "selected_route",
            "protocol_sequence_profile_id",
            "prefreeze_access_event_log_id",
            "last_preselection_sequence",
            "route_decision_freeze_attestation_id",
        }
        _fields(document, expected, "route decision freeze attestation")
        if (
            document["schema"]
            != "acfqp.route_decision_freeze_attestation.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise AccessProtocolV1Error("route decision freeze schema mismatch")
        result = cls(
            document["route_attempt_id"],
            document["decision_point_id"],
            document["route_decision_id"],
            document["route_decision_verification_attestation_id"],
            _enum(document["selected_route"], RouteSelection, "selected_route"),
            document["protocol_sequence_profile_id"],
            document["prefreeze_access_event_log_id"],
            document["last_preselection_sequence"],
        )
        _cid(
            document["route_decision_freeze_attestation_id"],
            "route_decision_freeze_attestation_id",
        )
        if (
            document["route_decision_freeze_attestation_id"]
            != result.route_decision_freeze_attestation_id
        ):
            raise AccessProtocolV1Error("route decision freeze content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class ForbiddenAccessViolationV1:
    route_attempt_id: str
    decision_point_id: str
    protocol_sequence_profile_id: str
    access_event_log_id: str
    offending_sequence_number: int
    operation: AccessOperation
    reason: AccessViolationReason
    selected_route: RouteSelection | None
    route_decision_freeze_attestation_id: str | None
    terminal_class: str = PROTOCOL_FAILURE_CLASS
    terminal_code: str = PROTOCOL_FAILURE_CODE

    def __post_init__(self) -> None:
        _cid(self.route_attempt_id, "route_attempt_id")
        _cid(self.decision_point_id, "decision_point_id")
        _cid(self.protocol_sequence_profile_id, "protocol_sequence_profile_id")
        _cid(self.access_event_log_id, "access_event_log_id")
        _positive(self.offending_sequence_number, "offending_sequence_number")
        object.__setattr__(
            self,
            "operation",
            _enum(self.operation, AccessOperation, "operation"),
        )
        object.__setattr__(
            self,
            "reason",
            _enum(self.reason, AccessViolationReason, "violation reason"),
        )
        if self.selected_route is None:
            if self.route_decision_freeze_attestation_id is not None:
                raise AccessProtocolV1Error(
                    "preselection violation cannot bind a route freeze"
                )
        else:
            object.__setattr__(
                self,
                "selected_route",
                _enum(self.selected_route, RouteSelection, "selected_route"),
            )
            _cid(
                self.route_decision_freeze_attestation_id,
                "route_decision_freeze_attestation_id",
            )
        if (
            self.terminal_class != PROTOCOL_FAILURE_CLASS
            or self.terminal_code != PROTOCOL_FAILURE_CODE
        ):
            raise AccessProtocolV1Error(
                "forbidden access must close as noncertificate PROTOCOL_FAILURE"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.forbidden_access_violation.v1",
            "schema_version": SCHEMA_VERSION,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
            "access_event_log_id": self.access_event_log_id,
            "offending_sequence_number": self.offending_sequence_number,
            "operation": self.operation.value,
            "reason": self.reason.value,
            "selected_route": (
                None if self.selected_route is None else self.selected_route.value
            ),
            "route_decision_freeze_attestation_id": (
                self.route_decision_freeze_attestation_id
            ),
            "terminal_class": self.terminal_class,
            "terminal_code": self.terminal_code,
        }

    @property
    def forbidden_access_violation_id(self) -> str:
        return content_id(FORBIDDEN_ACCESS_VIOLATION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "forbidden_access_violation_id": self.forbidden_access_violation_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ForbiddenAccessViolationV1":
        expected = {
            "schema",
            "schema_version",
            "route_attempt_id",
            "decision_point_id",
            "protocol_sequence_profile_id",
            "access_event_log_id",
            "offending_sequence_number",
            "operation",
            "reason",
            "selected_route",
            "route_decision_freeze_attestation_id",
            "terminal_class",
            "terminal_code",
            "forbidden_access_violation_id",
        }
        _fields(document, expected, "forbidden access violation")
        if (
            document["schema"] != "acfqp.forbidden_access_violation.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise AccessProtocolV1Error("forbidden access schema mismatch")
        selected = (
            None
            if document["selected_route"] is None
            else _enum(document["selected_route"], RouteSelection, "selected_route")
        )
        result = cls(
            document["route_attempt_id"],
            document["decision_point_id"],
            document["protocol_sequence_profile_id"],
            document["access_event_log_id"],
            document["offending_sequence_number"],
            _enum(document["operation"], AccessOperation, "operation"),
            _enum(document["reason"], AccessViolationReason, "reason"),
            selected,
            document["route_decision_freeze_attestation_id"],
            document["terminal_class"],
            document["terminal_code"],
        )
        _cid(
            document["forbidden_access_violation_id"],
            "forbidden_access_violation_id",
        )
        if (
            document["forbidden_access_violation_id"]
            != result.forbidden_access_violation_id
        ):
            raise AccessProtocolV1Error("forbidden access content ID mismatch")
        return result


class AccessProtocolViolation(RuntimeError):
    """Raised after the controller has closed fail-safe on a forbidden access."""

    def __init__(self, violation: ForbiddenAccessViolationV1) -> None:
        self.violation = violation
        super().__init__(
            f"{violation.terminal_code}: {violation.reason.value} at "
            f"sequence {violation.offending_sequence_number}"
        )


def _violation_artifact(
    log: AccessEventLogV1,
    event: AccessEventV1,
    reason: AccessViolationReason,
    *,
    selected_route: RouteSelection | None,
    freeze_attestation_id: str | None,
) -> ForbiddenAccessViolationV1:
    return ForbiddenAccessViolationV1(
        log.route_attempt_id,
        log.decision_point_id,
        log.protocol_sequence_profile_id,
        log.access_event_log_id,
        event.sequence_number,
        event.operation,
        reason,
        selected_route,
        freeze_attestation_id,
    )


def replay_access_protocol(
    log: AccessEventLogV1,
    profile: ProtocolSequenceProfileV1,
    *,
    decision_result: Any | None = None,
    freeze_attestation: RouteDecisionFreezeAttestationV1 | None = None,
) -> None:
    """Replay ordering, prefix identity, and selected-route access semantics."""

    if log.protocol_sequence_profile_id != profile.protocol_sequence_profile_id:
        raise AccessProtocolV1Error("access log/profile identity mismatch")
    if not log.is_frozen:
        if decision_result is not None or freeze_attestation is not None:
            raise AccessProtocolV1Error("unfrozen log cannot bind a route decision")
        for event in log.events:
            reason = _violation_reason(event, None)
            if reason is not None:
                raise AccessProtocolViolation(
                    _violation_artifact(
                        log,
                        event,
                        reason,
                        selected_route=None,
                        freeze_attestation_id=None,
                    )
                )
        return

    if decision_result is None or freeze_attestation is None:
        raise AccessProtocolV1Error(
            "frozen access log requires its route decision and freeze attestation"
        )
    decision, decision_attestation_id = _verified_route_decision(
        decision_result,
        route_attempt_id=log.route_attempt_id,
        decision_point_id=log.decision_point_id,
    )
    if (
        decision.decision_point_id != log.decision_point_id
        or decision.route_decision_id != log.route_decision_id
        or freeze_attestation.route_attempt_id != log.route_attempt_id
        or freeze_attestation.decision_point_id != log.decision_point_id
        or freeze_attestation.route_decision_id != decision.route_decision_id
        or freeze_attestation.route_decision_verification_attestation_id
        != decision_attestation_id
        or freeze_attestation.selected_route is not decision.selected_route
        or freeze_attestation.protocol_sequence_profile_id
        != profile.protocol_sequence_profile_id
        or freeze_attestation.route_decision_freeze_attestation_id
        != log.route_decision_freeze_attestation_id
        or freeze_attestation.prefreeze_access_event_log_id
        != log.prefreeze_access_event_log_id
        or freeze_attestation.last_preselection_sequence
        != log.freeze_after_sequence
    ):
        raise AccessProtocolV1Error("route decision freeze identity chain mismatch")
    prefix = log.prefreeze_prefix()
    if prefix.access_event_log_id != log.prefreeze_access_event_log_id:
        raise AccessProtocolV1Error("prefreeze access-log prefix ID mismatch")
    boundary = log.freeze_after_sequence
    if boundary is None:  # narrowed by is_frozen
        raise AccessProtocolV1Error("frozen access log lacks a boundary")
    for event in log.events:
        selected = (
            None
            if event.sequence_number <= boundary
            else decision.selected_route
        )
        reason = _violation_reason(event, selected)
        if reason is not None:
            freeze_id = (
                None
                if selected is None
                else freeze_attestation.route_decision_freeze_attestation_id
            )
            raise AccessProtocolViolation(
                _violation_artifact(
                    log,
                    event,
                    reason,
                    selected_route=selected,
                    freeze_attestation_id=freeze_id,
                )
            )
    if decision.selected_route is RouteSelection.LOCAL:
        bad_stage = local_execution_order_violation_v1(
            log.events,
            freeze_after_sequence=boundary,
        )
        if bad_stage is not None:
            raise AccessProtocolViolation(
                _violation_artifact(
                    log,
                    bad_stage,
                    AccessViolationReason.LOCAL_STAGE_ORDER_VIOLATION,
                    selected_route=decision.selected_route,
                    freeze_attestation_id=(
                        freeze_attestation.route_decision_freeze_attestation_id
                    ),
                )
            )


class FailClosedAccessController:
    """Append-only access recorder that closes on the first protocol violation."""

    def __init__(
        self,
        route_attempt_id: str,
        decision_point_id: str,
        *,
        profile: ProtocolSequenceProfileV1 | None = None,
    ) -> None:
        self.route_attempt_id = _cid(route_attempt_id, "route_attempt_id")
        self.decision_point_id = _cid(decision_point_id, "decision_point_id")
        self.profile = profile or ProtocolSequenceProfileV1()
        self._events: list[AccessEventV1] = []
        self._decision: MarginalRouteDecisionV1 | None = None
        self._decision_result: Any | None = None
        self._freeze: RouteDecisionFreezeAttestationV1 | None = None
        self._violation: ForbiddenAccessViolationV1 | None = None

    @property
    def violation(self) -> ForbiddenAccessViolationV1 | None:
        return self._violation

    @property
    def freeze_attestation(self) -> RouteDecisionFreezeAttestationV1 | None:
        return self._freeze

    def snapshot(self) -> AccessEventLogV1:
        if self._freeze is None or self._decision is None:
            return AccessEventLogV1(
                self.route_attempt_id,
                self.decision_point_id,
                self.profile.protocol_sequence_profile_id,
                tuple(self._events),
            )
        return AccessEventLogV1(
            self.route_attempt_id,
            self.decision_point_id,
            self.profile.protocol_sequence_profile_id,
            tuple(self._events),
            self._decision.route_decision_id,
            self._freeze.route_decision_freeze_attestation_id,
            self._freeze.last_preselection_sequence,
            self._freeze.prefreeze_access_event_log_id,
        )

    def record(
        self,
        operation: AccessOperation,
        route_scope: AccessRouteScope,
        *,
        artifact_id: str | None = None,
    ) -> AccessEventV1:
        if self._violation is not None:
            raise AccessProtocolViolation(self._violation)
        event = AccessEventV1(
            len(self._events) + 1,
            self.route_attempt_id,
            self.decision_point_id,
            operation,
            route_scope,
            artifact_id,
        )
        self._events.append(event)
        selected = None if self._decision is None else self._decision.selected_route
        reason = _violation_reason(event, selected)
        if reason is None and selected is RouteSelection.LOCAL:
            bad_stage = local_execution_order_violation_v1(
                tuple(self._events),
                freeze_after_sequence=(
                    0
                    if self._freeze is None
                    else self._freeze.last_preselection_sequence
                ),
            )
            if bad_stage is event:
                reason = AccessViolationReason.LOCAL_STAGE_ORDER_VIOLATION
        if reason is not None:
            log = self.snapshot()
            freeze_id = (
                None
                if self._freeze is None
                else self._freeze.route_decision_freeze_attestation_id
            )
            self._violation = _violation_artifact(
                log,
                event,
                reason,
                selected_route=selected,
                freeze_attestation_id=freeze_id,
            )
            raise AccessProtocolViolation(self._violation)
        return event

    def freeze_route_decision(
        self,
        decision_result: Any,
    ) -> RouteDecisionFreezeAttestationV1:
        if self._violation is not None:
            raise AccessProtocolViolation(self._violation)
        if self._freeze is not None:
            raise AccessProtocolV1Error("route decision was already frozen")
        prefreeze_log = self.snapshot()
        freeze = RouteDecisionFreezeAttestationV1.freeze(
            self.profile,
            prefreeze_log,
            decision_result,
        )
        decision, _ = _verified_route_decision(
            decision_result,
            route_attempt_id=self.route_attempt_id,
            decision_point_id=self.decision_point_id,
        )
        self._decision = decision
        self._decision_result = decision_result
        self._freeze = freeze
        return freeze

    def verify(self) -> None:
        replay_access_protocol(
            self.snapshot(),
            self.profile,
            decision_result=self._decision_result,
            freeze_attestation=self._freeze,
        )


T = TypeVar("T")


def decide_then_execute(
    controller: FailClosedAccessController,
    decision_result: Any,
    *,
    local_callback: Callable[[FailClosedAccessController], T],
    fallback_callback: Callable[[FailClosedAccessController], T],
) -> T:
    """Freeze the route decision, then invoke exactly its selected callback."""

    controller.freeze_route_decision(decision_result)
    decision = controller._decision
    if decision is None:  # pragma: no cover - established by freeze
        raise AccessProtocolV1Error("route decision freeze did not retain its artifact")
    if decision.selected_route is RouteSelection.LOCAL:
        result = local_callback(controller)
        controller.verify()
        freeze = controller.freeze_attestation
        if freeze is None:  # pragma: no cover - established above
            raise AccessProtocolV1Error("local execution is missing its freeze")
        stages = local_execution_stages_v1(
            controller.snapshot().events,
            freeze_after_sequence=freeze.last_preselection_sequence,
        )
        # A sound local attempt has two legitimate closures.  The isolated
        # solver can stop after materialization, compilation, and worker
        # execution when it proves SEARCH_CAP_EXHAUSTED or
        # NO_FEASIBLE_ASSIGNMENT.  Only a returned candidate proceeds through
        # stitch and post-audit.  The route runner binds these two stage
        # prefixes to the corresponding trusted semantic outcome; this layer
        # merely rejects skipped, partial, or extra stages.
        if stages not in ((1, 2, 3), (1, 2, 3, 4, 5)):
            raise AccessProtocolV1Error(
                "completed local callback omitted a required execution stage"
            )
        return result
    result = fallback_callback(controller)
    controller.verify()
    return result


__all__ = [
    "ARTIFACT_OPERATIONS",
    "AccessEventLogV1",
    "AccessEventV1",
    "AccessOperation",
    "AccessProtocolV1Error",
    "AccessProtocolViolation",
    "AccessRouteScope",
    "AccessViolationReason",
    "FALLBACK_ONLY_OPERATIONS",
    "GROUND_TRANSITION_OPERATIONS",
    "FailClosedAccessController",
    "ForbiddenAccessViolationV1",
    "LOCAL_ONLY_OPERATIONS",
    "PRESELECTION_READ_OPERATIONS",
    "PROFILE_KEY",
    "PROTOCOL_FAILURE_CLASS",
    "PROTOCOL_FAILURE_CODE",
    "ProtocolSequenceProfileV1",
    "ROUTE_SCOPED_OPERATIONS",
    "RouteDecisionFreezeAttestationV1",
    "SCHEMA_VERSION",
    "decide_then_execute",
    "local_execution_order_violation_v1",
    "local_execution_stages_v1",
    "replay_access_protocol",
]
