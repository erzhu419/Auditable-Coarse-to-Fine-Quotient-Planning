"""Fail-closed two-frame IPC skeleton for the accounted V0-075 K7 child.

This module freezes only the next transport boundary.  It reuses the existing
sealed-source/process substrate and the signer-owning private-replay lifecycle,
binds the complete Phase-3E occurrence/route identity, and requires exactly two
ordered child output frames:

1. the business result together with its operational cutoff; and
2. a post-cutoff accounting suffix.

The K7 execution body, trusted live resource monitors, output-byte fixed point,
and source-byte semantic replay are deliberately not implemented here.  The
second frame therefore carries all nine shared-resource paths as typed
``NOT_AVAILABLE`` blockers.  Structural replay never emits CounterRecords or
formal vectors and cannot authorize production.

All content domains are registered centrally in ``phase3e_ids``.  The
``REQUESTED_PHASE3E_DOMAIN_CONSTANTS`` tuple remains the exact registry audit
list.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import json
from typing import Any, Mapping, NoReturn

from acfqp import campaign_v1 as campaign
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import routing_v1 as routing
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution_v1
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3
from acfqp import v075_signer_owning_complete_observer_lifecycle_ipc_v1 as lifecycle
from acfqp import v075_signer_owning_sealed_observer_ipc_v1 as sealed_transport
from acfqp.phase3e_ids import (
    V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ACCOUNTING_SUFFIX_FRAME_V1_DOMAIN,
    V075_K7_ROOT_CAP_ACCOUNTED_SEALED_BUSINESS_FRAME_V1_DOMAIN,
    V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROFILE_V1_DOMAIN,
    V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROGRAM_V1_DOMAIN,
    V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROTOCOL_REPLAY_V1_DOMAIN,
    V075_K7_ROOT_CAP_ACCOUNTED_SEALED_REQUEST_V1_DOMAIN,
    V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ROUTE_IDENTITY_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.92.0"
PROFILE_KEY = "v075_k7_root_cap_accounted_sealed_ipc_v1"
REQUESTED_OPERATION = "EXECUTE_K7_ROOT_CAP_WITH_ACCOUNTING"
REGISTERED_OUTPUT_FRAME_ROLES = (
    "BUSINESS_RESULT_AND_OPERATIONAL_CUTOFF",
    "POST_CUTOFF_ACCOUNTING_SUFFIX",
)
CURRENT_READINESS = "SKELETON_LIVE_EXECUTION_AUTHORITIES_NOT_CONNECTED"

MAX_REQUEST_BYTES = sealed_transport.MAX_REQUEST_BYTES
MAX_FRAME_BYTES = sealed_transport.MAX_CHILD_RESULT_BYTES

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROGRAM_V1_DOMAIN",
    "V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROFILE_V1_DOMAIN",
    "V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ROUTE_IDENTITY_V1_DOMAIN",
    "V075_K7_ROOT_CAP_ACCOUNTED_SEALED_REQUEST_V1_DOMAIN",
    "V075_K7_ROOT_CAP_ACCOUNTED_SEALED_BUSINESS_FRAME_V1_DOMAIN",
    "V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ACCOUNTING_SUFFIX_FRAME_V1_DOMAIN",
    "V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROTOCOL_REPLAY_V1_DOMAIN",
)

LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROGRAM_V1_DOMAIN,
        V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROFILE_V1_DOMAIN,
        V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ROUTE_IDENTITY_V1_DOMAIN,
        V075_K7_ROOT_CAP_ACCOUNTED_SEALED_REQUEST_V1_DOMAIN,
        V075_K7_ROOT_CAP_ACCOUNTED_SEALED_BUSINESS_FRAME_V1_DOMAIN,
        V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ACCOUNTING_SUFFIX_FRAME_V1_DOMAIN,
        V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROTOCOL_REPLAY_V1_DOMAIN,
    }
)

LIVE_EXECUTION_BLOCKERS = (
    "K7_SEALED_CHILD_BODY_NOT_CONNECTED",
    "TRUSTED_OUTER_RESOURCE_MONITORS_NOT_CONNECTED",
    "OUTPUT_BYTE_FIXED_POINT_NOT_CONNECTED",
    "SOURCE_BYTE_SEMANTIC_REPLAY_NOT_CONNECTED",
)

_PROFILE_ISSUER = object()
_AUTHORITY_SNAPSHOT_ISSUER = object()
_IDENTITY_ISSUER = object()
_REQUEST_ISSUER = object()
_BUSINESS_FRAME_ISSUER = object()
_SUFFIX_FRAME_ISSUER = object()
_REPLAY_ISSUER = object()


class V075K7RootCapAccountedSealedIPCV1Error(ValueError):
    """The accounted K7 profile, identity, request, or frame is invalid."""


class V075K7RootCapAccountedSealedProductionV1NotReady(RuntimeError):
    """The two-frame skeleton is not a live production execution authority."""


def _fail(message: str) -> NoReturn:
    raise V075K7RootCapAccountedSealedIPCV1Error(message)


def _canonical(value: Any, label: str) -> bytes:
    """Return strict canonical JSON bytes under this module's typed error."""

    try:
        return canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise V075K7RootCapAccountedSealedIPCV1Error(
            f"{label} is not canonical JSON"
        ) from error


def _require_same_canonical_document(
    actual: Mapping[str, Any], expected: Mapping[str, Any], label: str
) -> None:
    """Compare JSON bytes, not Python values (where ``True == 1``)."""

    if _canonical(actual, label) != _canonical(expected, f"expected {label}"):
        _fail(f"{label} failed exact canonical content replay")


def _require_same_json_atom(actual: Any, expected: Any, label: str) -> None:
    """Require both JSON scalar value and type for duplicated authority fields."""

    if type(actual) is not type(expected) or actual != expected:
        _fail(f"{label} is stale or has the wrong JSON scalar type")


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("accounted sealed IPC used an unregistered local domain")
    return content_id(domain, dict(payload))


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075K7RootCapAccountedSealedIPCV1Error(
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


def _fields(document: Mapping[str, Any], expected: set[str], label: str) -> None:
    try:
        require_exact_fields(document, expected, context=label)
    except ValueError as error:
        raise V075K7RootCapAccountedSealedIPCV1Error(str(error)) from error


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        _fail(f"{label} must be one exact JSON object")
    return value


def _typed_unavailable(reason: str) -> dict[str, str]:
    return {"kind": "NOT_AVAILABLE", "reason": reason}


def _program_payload(
    *,
    source_snapshot_id: str,
    runtime_id: str,
    sealed_transport_program_id: str,
    private_replay_program_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_k7_root_cap_accounted_sealed_program.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "module": "acfqp.v075_k7_root_cap_accounted_sealed_ipc_v1",
        "child_callable": "_accounted_k7_child_main",
        "source_snapshot_id": source_snapshot_id,
        "runtime_id": runtime_id,
        "sealed_transport_program_id": sealed_transport_program_id,
        "signer_owning_private_replay_program_id": private_replay_program_id,
        "input_frame_count": 1,
        "output_frame_count": 2,
        "ordered_output_frame_roles": list(REGISTERED_OUTPUT_FRAME_ROLES),
        "business_frame_precedes_accounting_suffix": True,
        "business_work_forbidden_after_cutoff": True,
        "private_material_allowed_in_public_request": False,
        "caller_supplied_signer_allowed": False,
        "caller_supplied_private_replay_allowed": False,
        "live_child_body_connected": False,
    }


@dataclass(frozen=True, slots=True)
class _V075K7AccountedAuthoritySnapshotV1:
    """One construction-time validation of the exact K7 authorities.

    The official V6 factories recursively validate the entire V1--V6
    catalogue.  That is necessary when this snapshot is constructed, but it
    is neither a freshness check nor useful work to repeat for every profile
    property.  The snapshot retains the exact frozen authority objects and
    their content IDs.  Subsequent checks recompute only those IDs and reject
    replacement of either this snapshot or any nested authority object.
    """

    _issuer: InitVar[object]
    registry: registry_v6.CounterRegistryV6 = field(repr=False, compare=False)
    stage: registry_v6.StageProfileV6 = field(repr=False, compare=False)
    comparison: registry_v6.ComparisonProfileV6 = field(
        repr=False, compare=False
    )
    projection: registry_v6.ActualProjectionProfileV6 = field(
        repr=False, compare=False
    )
    boundary: boundary_v3.K7RootCapOperationBoundaryManifestV3 = field(
        repr=False, compare=False
    )
    execution: execution_v1.V075K7RootCapExecutionIdentityProfileV1 = field(
        repr=False, compare=False
    )
    _validated_refs: tuple[object, ...] = field(init=False, repr=False)
    _validated_ids: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _AUTHORITY_SNAPSHOT_ISSUER:
            _fail("accounted sealed authority snapshot is caller-minted")
        expected_types = (
            registry_v6.CounterRegistryV6,
            registry_v6.StageProfileV6,
            registry_v6.ComparisonProfileV6,
            registry_v6.ActualProjectionProfileV6,
            boundary_v3.K7RootCapOperationBoundaryManifestV3,
            execution_v1.V075K7RootCapExecutionIdentityProfileV1,
        )
        refs = (
            self.registry,
            self.stage,
            self.comparison,
            self.projection,
            self.boundary,
            self.execution,
        )
        if any(
            type(value) is not expected
            for value, expected in zip(refs, expected_types)
        ):
            _fail("accounted sealed authority snapshot has a foreign type")
        ids = self._current_ids()
        self._assert_joins(ids)
        object.__setattr__(self, "_validated_refs", refs)
        object.__setattr__(self, "_validated_ids", ids)
        self._assert_current()

    def _current_ids(self) -> tuple[str, ...]:
        return (
            self.registry.registry_id,
            self.stage.stage_profile_id,
            self.comparison.comparison_profile_id,
            self.projection.actual_projection_profile_id,
            self.boundary.manifest_id,
            self.execution.profile_id,
        )

    def _assert_joins(self, ids: tuple[str, ...]) -> None:
        registry_id, stage_id, comparison_id, projection_id, boundary_id, _ = ids
        if (
            self.stage.counter_registry_id != registry_id
            or self.comparison.counter_registry_id != registry_id
            or self.projection.counter_registry_id != registry_id
            or self.projection.comparison_profile_id != comparison_id
            or self.boundary.counter_registry_id != registry_id
            or self.boundary.stage_profile_id != stage_id
            or self.boundary.comparison_profile_id != comparison_id
            or self.boundary.actual_projection_profile_id != projection_id
            or self.execution.boundary_manifest_id != boundary_id
        ):
            _fail("accounted sealed authority snapshot does not join exactly")

    def _assert_current(self) -> None:
        current_refs = (
            self.registry,
            self.stage,
            self.comparison,
            self.projection,
            self.boundary,
            self.execution,
        )
        if any(
            current is not validated
            for current, validated in zip(current_refs, self._validated_refs)
        ):
            _fail("accounted sealed authority object was replaced")
        current_ids = self._current_ids()
        self._assert_joins(current_ids)
        if current_ids != self._validated_ids:
            _fail("accounted sealed authority content identity is stale")

    @property
    def ids(self) -> tuple[str, ...]:
        self._assert_current()
        return self._validated_ids


@dataclass(frozen=True, slots=True)
class V075K7RootCapAccountedSealedIPCProfileV1:
    """Exact substrate/profile binding for the future accounted K7 child."""

    _issuer: InitVar[object]
    transport_profile: sealed_transport.V075SignerOwningSealedObserverServiceProfileV1 = field(
        repr=False, compare=False
    )
    private_replay_profile: lifecycle.V075CompleteObserverLifecycleProfileV1 = field(
        repr=False, compare=False
    )
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundary_manifest_id: str
    execution_profile_id: str
    _authority_snapshot: _V075K7AccountedAuthoritySnapshotV1 = field(
        repr=False, compare=False
    )
    _validated_authority_snapshot: _V075K7AccountedAuthoritySnapshotV1 = field(
        init=False, repr=False, compare=False
    )
    _source_snapshot_id: str = field(init=False, repr=False)
    _runtime_id: str = field(init=False, repr=False)
    _transport_profile_id: str = field(init=False, repr=False)
    _transport_program_id: str = field(init=False, repr=False)
    _private_replay_profile_id: str = field(init=False, repr=False)
    _private_replay_program_id: str = field(init=False, repr=False)
    _program_id: str = field(init=False, repr=False)
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("accounted sealed IPC profile is caller-minted")
        if type(self._authority_snapshot) is not _V075K7AccountedAuthoritySnapshotV1:
            _fail("accounted sealed IPC profile lacks its authority snapshot")
        object.__setattr__(
            self,
            "_validated_authority_snapshot",
            self._authority_snapshot,
        )
        self._assert_authority_chain()
        # The substrate objects are frozen.  Capture their verified IDs once;
        # repeatedly re-reading and re-hashing the sealed source archive would
        # turn every schema property access into an archive replay.
        object.__setattr__(
            self, "_source_snapshot_id", self.transport_profile._source_snapshot_id  # noqa: SLF001
        )
        object.__setattr__(self, "_runtime_id", self.transport_profile._runtime_id)  # noqa: SLF001
        object.__setattr__(
            self, "_transport_profile_id", self.transport_profile._profile_id  # noqa: SLF001
        )
        object.__setattr__(
            self, "_transport_program_id", self.transport_profile._program_id  # noqa: SLF001
        )
        object.__setattr__(
            self, "_private_replay_profile_id", self.private_replay_profile._profile_id  # noqa: SLF001
        )
        object.__setattr__(
            self, "_private_replay_program_id", self.private_replay_profile._program_id  # noqa: SLF001
        )
        program_id = _hash(
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROGRAM_V1_DOMAIN,
            _program_payload(
                source_snapshot_id=self._source_snapshot_id,
                runtime_id=self._runtime_id,
                sealed_transport_program_id=self._transport_program_id,
                private_replay_program_id=self._private_replay_program_id,
            ),
        )
        object.__setattr__(self, "_program_id", program_id)
        object.__setattr__(
            self,
            "_profile_id",
            _hash(V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROFILE_V1_DOMAIN, self._payload()),
        )
        self._assert_current()

    def _assert_authority_chain(self) -> None:
        if (
            type(self.transport_profile)
            is not sealed_transport.V075SignerOwningSealedObserverServiceProfileV1
            or type(self.private_replay_profile)
            is not lifecycle.V075CompleteObserverLifecycleProfileV1
            or self.private_replay_profile.transport_profile is not self.transport_profile
        ):
            _fail("sealed transport and signer-owning replay must share one substrate")
        self.transport_profile._assert_current()  # noqa: SLF001
        self.private_replay_profile._assert_current()  # noqa: SLF001
        if self._authority_snapshot is not self._validated_authority_snapshot:
            _fail("accounted sealed IPC authority snapshot was replaced")
        self._authority_snapshot._assert_current()
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
            (self.boundary_manifest_id, "boundary manifest"),
            (self.execution_profile_id, "execution profile"),
        ):
            _cid(value, label)
        if (
            (
                self.counter_registry_id,
                self.stage_profile_id,
                self.comparison_profile_id,
                self.actual_projection_profile_id,
                self.boundary_manifest_id,
                self.execution_profile_id,
            )
            != self._authority_snapshot.ids
            or not any(
                path == "acfqp/v075_k7_root_cap_accounted_sealed_ipc_v1.py"
                for path, _digest, _size in self.transport_profile.source_entries
            )
        ):
            _fail("accounted sealed IPC authority chain is stale")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_accounted_sealed_ipc_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_snapshot_id": self._source_snapshot_id,
            "runtime_id": self._runtime_id,
            "sealed_transport_profile_id": self._transport_profile_id,
            "sealed_transport_program_id": self._transport_program_id,
            "signer_owning_private_replay_profile_id": self._private_replay_profile_id,
            "signer_owning_private_replay_program_id": self._private_replay_program_id,
            "program_id": self._program_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "execution_profile_id": self.execution_profile_id,
            "output_frame_count": 2,
            "ordered_output_frame_roles": list(REGISTERED_OUTPUT_FRAME_ROLES),
            "current_readiness": CURRENT_READINESS,
            "live_execution_blockers": list(LIVE_EXECUTION_BLOCKERS),
            "shared_resource_semantics_verified": False,
            "output_byte_fixed_point_verified": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    def _assert_current(self) -> None:
        self._assert_authority_chain()
        expected_program = _hash(
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROGRAM_V1_DOMAIN,
            _program_payload(
                source_snapshot_id=self._source_snapshot_id,
                runtime_id=self._runtime_id,
                sealed_transport_program_id=self._transport_program_id,
                private_replay_program_id=self._private_replay_program_id,
            ),
        )
        if (
            type(self.transport_profile)
            is not sealed_transport.V075SignerOwningSealedObserverServiceProfileV1
            or type(self.private_replay_profile)
            is not lifecycle.V075CompleteObserverLifecycleProfileV1
            or self.private_replay_profile.transport_profile is not self.transport_profile
            or self.transport_profile._source_snapshot_id != self._source_snapshot_id  # noqa: SLF001
            or self.transport_profile._runtime_id != self._runtime_id  # noqa: SLF001
            or self.transport_profile._profile_id != self._transport_profile_id  # noqa: SLF001
            or self.transport_profile._program_id != self._transport_program_id  # noqa: SLF001
            or self.private_replay_profile._profile_id != self._private_replay_profile_id  # noqa: SLF001
            or self.private_replay_profile._program_id != self._private_replay_program_id  # noqa: SLF001
            or expected_program != self._program_id
            or _hash(V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROFILE_V1_DOMAIN, self._payload())
            != self._profile_id
        ):
            _fail("accounted sealed IPC profile identity is stale")

    @property
    def program_id(self) -> str:
        self._assert_current()
        return self._program_id

    @property
    def profile_id(self) -> str:
        self._assert_current()
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "profile_id": self._profile_id}


def freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
    *, timeout_milliseconds: int = 10_000
) -> V075K7RootCapAccountedSealedIPCProfileV1:
    transport = sealed_transport.freeze_v075_signer_owning_sealed_observer_service_profile_v1(
        timeout_milliseconds=timeout_milliseconds
    )
    private_replay = lifecycle.V075CompleteObserverLifecycleProfileV1(transport)
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    boundary = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    execution = execution_v1.official_v075_k7_root_cap_execution_identity_profile_v1()
    authorities = _V075K7AccountedAuthoritySnapshotV1(
        _AUTHORITY_SNAPSHOT_ISSUER,
        registry,
        stage,
        comparison,
        projection,
        boundary,
        execution,
    )
    return V075K7RootCapAccountedSealedIPCProfileV1(
        _PROFILE_ISSUER,
        transport,
        private_replay,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        projection.actual_projection_profile_id,
        boundary.manifest_id,
        execution.profile_id,
        authorities,
    )


@dataclass(frozen=True, slots=True)
class V075K7RootCapAccountedSealedRouteIdentityV1:
    """The complete typed occurrence/attempt/decision/transaction identity."""

    _issuer: InitVar[object]
    profile: V075K7RootCapAccountedSealedIPCProfileV1 = field(repr=False, compare=False)
    logical_occurrence: campaign.LogicalOccurrenceV1 = field(repr=False)
    route_attempt: campaign.RouteAttemptV1 = field(repr=False)
    route_context: routing.RouteDecisionContextV1 = field(repr=False)
    decision_point: routing.DecisionPointV1 = field(repr=False)
    transaction: routing.TransactionV1 = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _IDENTITY_ISSUER:
            _fail("accounted sealed route identity is caller-minted")
        self._assert_current()

    def _assert_current(self) -> None:
        if type(self.profile) is not V075K7RootCapAccountedSealedIPCProfileV1:
            _fail("route identity lacks the exact accounted child profile")
        self.profile._assert_current()
        if (
            type(self.logical_occurrence) is not campaign.LogicalOccurrenceV1
            or type(self.route_attempt) is not campaign.RouteAttemptV1
            or type(self.route_context) is not routing.RouteDecisionContextV1
            or type(self.decision_point) is not routing.DecisionPointV1
            or type(self.transaction) is not routing.TransactionV1
        ):
            _fail("route identity requires exact Phase-3E typed authorities")
        occurrence = self.logical_occurrence
        attempt = self.route_attempt
        context = self.route_context
        decision = self.decision_point
        transaction = self.transaction
        frontier = decision.frontier_snapshot_id
        causal = decision.causal_evidence_id
        if (
            not isinstance(frontier, str)
            or not isinstance(causal, str)
            or type(decision.transaction_index) is not int
            or occurrence.logical_occurrence_id != attempt.logical_occurrence_id
            or occurrence.logical_occurrence_id != context.logical_occurrence_id
            or attempt.route_attempt_id != context.route_attempt_id
            or attempt.build_epoch_id != context.build_epoch_id
            or occurrence.protocol_id != context.protocol_id
            or occurrence.structural_id != context.structural_id
            or occurrence.query_id != context.query_id
            or occurrence.selected_plan_id != context.selected_plan_id
            or occurrence.threshold_profile_id != context.threshold_profile_id
            or context.counter_registry_id != self.profile.counter_registry_id
            or context.comparison_profile_id != self.profile.comparison_profile_id
            or decision.route_decision_context_id != context.route_decision_context_id
            or transaction.logical_occurrence_id != occurrence.logical_occurrence_id
            or transaction.route_attempt_id != attempt.route_attempt_id
            or transaction.decision_point_id != decision.decision_point_id
            or transaction.transaction_index != decision.transaction_index
            or transaction.frontier_snapshot_id != frontier
            or (attempt.route_attempt_index == 1 and attempt.build_epoch_id != occurrence.initial_build_epoch_id)
        ):
            _fail("route/occurrence identity graph does not join exactly")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_accounted_sealed_route_identity.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "profile_id": self.profile.profile_id,
            "logical_occurrence": self.logical_occurrence.to_dict(),
            "route_attempt": self.route_attempt.to_dict(),
            "route_decision_context": self.route_context.to_dict(),
            "decision_point": self.decision_point.to_dict(),
            "transaction": self.transaction.to_dict(),
            "logical_occurrence_id": self.logical_occurrence.logical_occurrence_id,
            "route_attempt_id": self.route_attempt.route_attempt_id,
            "RouteDecisionContext_id": self.route_context.route_decision_context_id,
            "decision_point_id": self.decision_point.decision_point_id,
            "transaction_id": self.transaction.transaction_id,
            "transaction_index": self.transaction.transaction_index,
            "frontier_snapshot_id": self.transaction.frontier_snapshot_id,
            "route_cap_profile_id": self.transaction.route_cap_profile_id,
            "execution_profile_id": self.profile.execution_profile_id,
            "route_kind": execution_v1.REGISTERED_ROUTE,
            "arm": execution_v1.REGISTERED_ARM,
        }

    @property
    def route_identity_id(self) -> str:
        self._assert_current()
        return _hash(
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ROUTE_IDENTITY_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_identity_id": self.route_identity_id}

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        *,
        profile: V075K7RootCapAccountedSealedIPCProfileV1,
    ) -> "V075K7RootCapAccountedSealedRouteIdentityV1":
        expected = {
            "schema", "schema_version", "profile_key", "profile_id",
            "logical_occurrence", "route_attempt", "route_decision_context",
            "decision_point", "transaction", "logical_occurrence_id",
            "route_attempt_id", "RouteDecisionContext_id", "decision_point_id",
            "transaction_id", "transaction_index", "frontier_snapshot_id",
            "route_cap_profile_id", "execution_profile_id", "route_kind", "arm",
            "route_identity_id",
        }
        _fields(document, expected, "accounted sealed route identity")
        if (
            document["schema"]
            != "acfqp.v075_k7_root_cap_accounted_sealed_route_identity.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or document["profile_key"] != PROFILE_KEY
            or document["profile_id"] != profile.profile_id
        ):
            _fail("accounted sealed route identity schema/profile mismatch")
        try:
            result = cls(
                _IDENTITY_ISSUER,
                profile,
                campaign.LogicalOccurrenceV1.from_dict(
                    _mapping(document["logical_occurrence"], "logical occurrence")
                ),
                campaign.RouteAttemptV1.from_dict(
                    _mapping(document["route_attempt"], "route attempt")
                ),
                routing.RouteDecisionContextV1.from_dict(
                    _mapping(document["route_decision_context"], "route context")
                ),
                routing.DecisionPointV1.from_dict(
                    _mapping(document["decision_point"], "decision point")
                ),
                routing.TransactionV1.from_dict(
                    _mapping(document["transaction"], "transaction")
                ),
            )
        except (campaign.CampaignV1Error, routing.RoutingV1Error) as error:
            raise V075K7RootCapAccountedSealedIPCV1Error(
                "nested route/occurrence authority failed replay"
            ) from error
        payload = result._payload()
        nonduplicate_fields = {
            "schema",
            "schema_version",
            "profile_key",
            "profile_id",
            "logical_occurrence",
            "route_attempt",
            "route_decision_context",
            "decision_point",
            "transaction",
            "route_identity_id",
        }
        for name in expected - nonduplicate_fields:
            _require_same_json_atom(
                document[name], payload[name], f"route identity duplicate field {name}"
            )
        if document["route_identity_id"] != result.route_identity_id:
            _fail("route identity content ID mismatch")
        _require_same_canonical_document(
            document, result.to_document(), "accounted sealed route identity"
        )
        return result


def freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
    *,
    profile: V075K7RootCapAccountedSealedIPCProfileV1,
    logical_occurrence: campaign.LogicalOccurrenceV1,
    route_attempt: campaign.RouteAttemptV1,
    route_context: routing.RouteDecisionContextV1,
    decision_point: routing.DecisionPointV1,
    transaction: routing.TransactionV1,
) -> V075K7RootCapAccountedSealedRouteIdentityV1:
    return V075K7RootCapAccountedSealedRouteIdentityV1(
        _IDENTITY_ISSUER,
        profile,
        logical_occurrence,
        route_attempt,
        route_context,
        decision_point,
        transaction,
    )


def _identity_refs(identity: V075K7RootCapAccountedSealedRouteIdentityV1) -> dict[str, Any]:
    return {
        "route_identity_id": identity.route_identity_id,
        "logical_occurrence_id": identity.logical_occurrence.logical_occurrence_id,
        "route_attempt_id": identity.route_attempt.route_attempt_id,
        "RouteDecisionContext_id": identity.route_context.route_decision_context_id,
        "decision_point_id": identity.decision_point.decision_point_id,
        "transaction_id": identity.transaction.transaction_id,
        "transaction_index": identity.transaction.transaction_index,
    }


@dataclass(frozen=True, slots=True)
class V075K7RootCapAccountedSealedRequestV1:
    _issuer: InitVar[object]
    profile: V075K7RootCapAccountedSealedIPCProfileV1 = field(repr=False, compare=False)
    route_identity: V075K7RootCapAccountedSealedRouteIdentityV1 = field(repr=False)
    request_nonce: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REQUEST_ISSUER:
            _fail("accounted sealed request is caller-minted")
        self.profile._assert_current()
        self.route_identity._assert_current()
        _cid(self.request_nonce, "request nonce")
        if self.route_identity.profile.profile_id != self.profile.profile_id:
            _fail("request crosses accounted child profiles")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_accounted_sealed_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "profile_id": self.profile.profile_id,
            "program_id": self.profile.program_id,
            "request_nonce": self.request_nonce,
            "requested_operation": REQUESTED_OPERATION,
            "route_identity": self.route_identity.to_document(),
            **_identity_refs(self.route_identity),
            "caller_supplied_private_material": False,
            "caller_supplied_signer": False,
            "caller_supplied_private_replay": False,
            "expected_output_frame_count": 2,
            "expected_output_frame_roles": list(REGISTERED_OUTPUT_FRAME_ROLES),
        }

    @property
    def request_id(self) -> str:
        return _hash(V075_K7_ROOT_CAP_ACCOUNTED_SEALED_REQUEST_V1_DOMAIN, self._payload())

    @property
    def canonical_bytes(self) -> bytes:
        raw = _canonical(self.to_document(), "accounted sealed request")
        if len(raw) > MAX_REQUEST_BYTES:
            _fail("accounted sealed request exceeds its transport cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


def freeze_v075_k7_root_cap_accounted_sealed_request_v1(
    *, profile: V075K7RootCapAccountedSealedIPCProfileV1,
    route_identity: V075K7RootCapAccountedSealedRouteIdentityV1,
    request_nonce: str,
) -> V075K7RootCapAccountedSealedRequestV1:
    return V075K7RootCapAccountedSealedRequestV1(
        _REQUEST_ISSUER, profile, route_identity, request_nonce
    )


_REQUEST_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "profile_id", "program_id", "request_nonce", "requested_operation",
    "route_identity", "route_identity_id", "logical_occurrence_id",
    "route_attempt_id", "RouteDecisionContext_id", "decision_point_id",
    "transaction_id", "transaction_index", "caller_supplied_private_material",
    "caller_supplied_signer", "caller_supplied_private_replay",
    "expected_output_frame_count", "expected_output_frame_roles", "request_id",
}


def verify_v075_k7_root_cap_accounted_sealed_request_bytes_v1(
    *,
    raw: bytes,
    profile: V075K7RootCapAccountedSealedIPCProfileV1,
) -> V075K7RootCapAccountedSealedRequestV1:
    if type(raw) is not bytes or not raw or len(raw) > MAX_REQUEST_BYTES:
        _fail("accounted sealed request bytes are empty, mistyped, or over cap")
    if type(profile) is not V075K7RootCapAccountedSealedIPCProfileV1:
        _fail("request replay requires one exact accounted child profile")
    profile._assert_current()
    document = _load_canonical(raw, "accounted sealed request")
    _fields(document, _REQUEST_KEYS, "accounted sealed request")
    if (
        document["schema"] != "acfqp.v075_k7_root_cap_accounted_sealed_request.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["profile_id"] != profile.profile_id
        or document["program_id"] != profile.program_id
        or document["requested_operation"] != REQUESTED_OPERATION
        or document["caller_supplied_private_material"] is not False
        or document["caller_supplied_signer"] is not False
        or document["caller_supplied_private_replay"] is not False
        or type(document["expected_output_frame_count"]) is not int
        or document["expected_output_frame_count"] != 2
        or document["expected_output_frame_roles"]
        != list(REGISTERED_OUTPUT_FRAME_ROLES)
    ):
        _fail("accounted sealed request schema or fixed semantics changed")
    identity = V075K7RootCapAccountedSealedRouteIdentityV1.from_document(
        _mapping(document["route_identity"], "route identity"), profile=profile
    )
    for name, value in _identity_refs(identity).items():
        _require_same_json_atom(
            document[name], value, f"request route identity field {name}"
        )
    result = V075K7RootCapAccountedSealedRequestV1(
        _REQUEST_ISSUER, profile, identity, document["request_nonce"]
    )
    _require_same_canonical_document(
        document, result.to_document(), "accounted sealed request"
    )
    return result


@dataclass(frozen=True, slots=True)
class V075K7RootCapAccountedSealedBusinessFrameV1:
    _issuer: InitVar[object]
    request: V075K7RootCapAccountedSealedRequestV1 = field(repr=False, compare=False)
    business_result_id: str
    partial_native_transcript_id: str
    terminal_artifact_id: str
    private_replay_attestation_id: str
    cutoff_marker_id: str
    cutoff_sequence: int

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUSINESS_FRAME_ISSUER:
            _fail("business/cutoff frame is caller-minted")
        if type(self.request) is not V075K7RootCapAccountedSealedRequestV1:
            _fail("business/cutoff frame lacks one exact request")
        for value, label in (
            (self.business_result_id, "business result"),
            (self.partial_native_transcript_id, "partial native transcript"),
            (self.terminal_artifact_id, "terminal artifact"),
            (self.private_replay_attestation_id, "private replay attestation"),
            (self.cutoff_marker_id, "cutoff marker"),
        ):
            _cid(value, label)
        _positive(self.cutoff_sequence, "cutoff sequence")

    def _payload(self) -> dict[str, Any]:
        identity = self.request.route_identity
        return {
            "schema": "acfqp.v075_k7_root_cap_accounted_sealed_business_frame.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "frame_index": 1,
            "frame_role": REGISTERED_OUTPUT_FRAME_ROLES[0],
            "profile_id": self.request.profile.profile_id,
            "program_id": self.request.profile.program_id,
            "request_id": self.request.request_id,
            **_identity_refs(identity),
            "business_result_id": self.business_result_id,
            "partial_native_transcript_id": self.partial_native_transcript_id,
            "terminal_artifact_id": self.terminal_artifact_id,
            "terminal_status": execution_v1.REGISTERED_TERMINAL_STATUS,
            "signer_owning_private_replay_attestation_id": self.private_replay_attestation_id,
            "operational_cutoff_marker_id": self.cutoff_marker_id,
            "operational_cutoff_sequence": self.cutoff_sequence,
            "business_result_frozen_before_suffix": True,
            "formal_vector_embedded": False,
        }

    @property
    def frame_id(self) -> str:
        return _hash(V075_K7_ROOT_CAP_ACCOUNTED_SEALED_BUSINESS_FRAME_V1_DOMAIN, self._payload())

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical(self.to_document(), "accounted sealed business frame")

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "business_frame_id": self.frame_id}


def freeze_v075_k7_root_cap_accounted_sealed_business_frame_v1(
    *, request: V075K7RootCapAccountedSealedRequestV1,
    business_result_id: str,
    partial_native_transcript_id: str,
    terminal_artifact_id: str,
    private_replay_attestation_id: str,
    cutoff_marker_id: str,
    cutoff_sequence: int,
) -> V075K7RootCapAccountedSealedBusinessFrameV1:
    return V075K7RootCapAccountedSealedBusinessFrameV1(
        _BUSINESS_FRAME_ISSUER,
        request,
        business_result_id,
        partial_native_transcript_id,
        terminal_artifact_id,
        private_replay_attestation_id,
        cutoff_marker_id,
        cutoff_sequence,
    )


def _shared_blockers() -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "path": path,
            "measurement": _typed_unavailable(
                "LIVE_TRUSTED_SHARED_RESOURCE_MONITOR_NOT_CONNECTED"
            ),
            "semantic_authority_present": False,
        }
        for path in receipts_v1.SHARED_RESOURCE_PATHS
    )


@dataclass(frozen=True, slots=True)
class V075K7RootCapAccountedSealedAccountingSuffixFrameV1:
    _issuer: InitVar[object]
    business_frame: V075K7RootCapAccountedSealedBusinessFrameV1 = field(
        repr=False, compare=False
    )
    suffix_start_sequence: int
    suffix_end_sequence: int

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SUFFIX_FRAME_ISSUER:
            _fail("accounting suffix frame is caller-minted")
        if type(self.business_frame) is not V075K7RootCapAccountedSealedBusinessFrameV1:
            _fail("accounting suffix lacks one exact business frame")
        _positive(self.suffix_start_sequence, "suffix start sequence")
        _positive(self.suffix_end_sequence, "suffix end sequence")
        if (
            self.suffix_start_sequence != self.business_frame.cutoff_sequence + 1
            or self.suffix_end_sequence < self.suffix_start_sequence
        ):
            _fail("accounting suffix does not begin strictly after the cutoff")

    def _payload(self) -> dict[str, Any]:
        request = self.business_frame.request
        identity = request.route_identity
        return {
            "schema": "acfqp.v075_k7_root_cap_accounted_sealed_accounting_suffix_frame.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "frame_index": 2,
            "frame_role": REGISTERED_OUTPUT_FRAME_ROLES[1],
            "profile_id": request.profile.profile_id,
            "program_id": request.profile.program_id,
            "request_id": request.request_id,
            **_identity_refs(identity),
            "business_frame_id": self.business_frame.frame_id,
            "operational_cutoff_marker_id": self.business_frame.cutoff_marker_id,
            "operational_cutoff_sequence": self.business_frame.cutoff_sequence,
            "suffix_start_sequence": self.suffix_start_sequence,
            "suffix_end_sequence": self.suffix_end_sequence,
            "shared_resource_paths": [
                dict(row) for row in _shared_blockers()
            ],
            "shared_resource_path_count": len(receipts_v1.SHARED_RESOURCE_PATHS),
            "owner_complete_closure_set": _typed_unavailable(
                "OWNER_COMPLETE_CLOSURE_SET_NOT_CONNECTED"
            ),
            "profile_native_zero_attestation_set": _typed_unavailable(
                "PROFILE_NATIVE_ZERO_ATTESTATION_SET_NOT_CONNECTED"
            ),
            "derived_reconciliation_proof_set": _typed_unavailable(
                "DERIVED_RECONCILIATION_PROOF_SET_NOT_CONNECTED"
            ),
            "output_byte_receipt": _typed_unavailable(
                "OUTPUT_BYTE_FIXED_POINT_NOT_CONNECTED"
            ),
            "accounting_suffix_bytes_are_chargeable_output": True,
            "accounting_content_id_hashes_are_provenance_only": True,
            "shared_resource_semantics_verified": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
        }

    @property
    def frame_id(self) -> str:
        return _hash(
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ACCOUNTING_SUFFIX_FRAME_V1_DOMAIN,
            self._payload(),
        )

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical(self.to_document(), "accounted sealed accounting suffix frame")

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_suffix_frame_id": self.frame_id}


def freeze_v075_k7_root_cap_accounted_sealed_accounting_suffix_frame_v1(
    *,
    business_frame: V075K7RootCapAccountedSealedBusinessFrameV1,
    suffix_start_sequence: int,
    suffix_end_sequence: int,
) -> V075K7RootCapAccountedSealedAccountingSuffixFrameV1:
    return V075K7RootCapAccountedSealedAccountingSuffixFrameV1(
        _SUFFIX_FRAME_ISSUER,
        business_frame,
        suffix_start_sequence,
        suffix_end_sequence,
    )


def encode_v075_k7_root_cap_accounted_sealed_two_frame_output_v1(
    *,
    business_frame: V075K7RootCapAccountedSealedBusinessFrameV1,
    accounting_suffix_frame: V075K7RootCapAccountedSealedAccountingSuffixFrameV1,
) -> bytes:
    if (
        type(business_frame) is not V075K7RootCapAccountedSealedBusinessFrameV1
        or type(accounting_suffix_frame)
        is not V075K7RootCapAccountedSealedAccountingSuffixFrameV1
        or accounting_suffix_frame.business_frame.frame_id != business_frame.frame_id
    ):
        _fail("the two output frames do not belong to one protocol execution")
    try:
        return sealed_transport._frame(  # noqa: SLF001
            business_frame.canonical_bytes, cap=MAX_FRAME_BYTES
        ) + sealed_transport._frame(  # noqa: SLF001
            accounting_suffix_frame.canonical_bytes, cap=MAX_FRAME_BYTES
        )
    except sealed_transport.V075SignerOwningSealedObserverIPCV1InvariantViolation as error:
        raise V075K7RootCapAccountedSealedIPCV1Error(
            "two-frame output exceeds the reused transport boundary"
        ) from error


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("two-frame protocol JSON contains a duplicate key")
        result[key] = value
    return result


def _load_canonical(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: _fail(
                f"{label} contains non-finite {token}"
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        if isinstance(error, V075K7RootCapAccountedSealedIPCV1Error):
            raise
        raise V075K7RootCapAccountedSealedIPCV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or _canonical(value, label) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _split_two_frames(raw: bytes) -> tuple[bytes, bytes]:
    if type(raw) is not bytes:
        _fail("two-frame output must be bytes")
    parts: list[bytes] = []
    offset = 0
    try:
        for _index in range(2):
            header_end = offset + sealed_transport._FRAME_WIDTH  # noqa: SLF001
            if header_end > len(raw):
                _fail("two-frame output is truncated")
            length = sealed_transport._parse_frame_header(  # noqa: SLF001
                raw[offset:header_end], cap=MAX_FRAME_BYTES
            )
            payload_end = header_end + length
            if payload_end > len(raw):
                _fail("two-frame output payload is truncated")
            parts.append(raw[header_end:payload_end])
            offset = payload_end
    except sealed_transport.V075SignerOwningSealedObserverIPCV1InvariantViolation as error:
        raise V075K7RootCapAccountedSealedIPCV1Error(
            "two-frame output uses invalid transport framing"
        ) from error
    if offset != len(raw):
        _fail("two-frame output contains an extra frame or trailing bytes")
    return parts[0], parts[1]


_BUSINESS_KEYS = {
    "schema", "schema_version", "profile_key", "frame_index", "frame_role",
    "profile_id", "program_id", "request_id", "route_identity_id",
    "logical_occurrence_id", "route_attempt_id", "RouteDecisionContext_id",
    "decision_point_id", "transaction_id", "transaction_index",
    "business_result_id", "partial_native_transcript_id", "terminal_artifact_id",
    "terminal_status", "signer_owning_private_replay_attestation_id",
    "operational_cutoff_marker_id", "operational_cutoff_sequence",
    "business_result_frozen_before_suffix", "formal_vector_embedded",
    "business_frame_id",
}

_SUFFIX_KEYS = {
    "schema", "schema_version", "profile_key", "frame_index", "frame_role",
    "profile_id", "program_id", "request_id", "route_identity_id",
    "logical_occurrence_id", "route_attempt_id", "RouteDecisionContext_id",
    "decision_point_id", "transaction_id", "transaction_index",
    "business_frame_id", "operational_cutoff_marker_id",
    "operational_cutoff_sequence", "suffix_start_sequence", "suffix_end_sequence",
    "shared_resource_paths", "shared_resource_path_count",
    "owner_complete_closure_set", "profile_native_zero_attestation_set",
    "derived_reconciliation_proof_set", "output_byte_receipt",
    "accounting_suffix_bytes_are_chargeable_output",
    "accounting_content_id_hashes_are_provenance_only",
    "shared_resource_semantics_verified", "counter_records_issued",
    "work_vector_issued", "comparison_vector_issued", "formal_vector_authorized",
    "accounting_suffix_frame_id",
}


def _verify_business_document(
    document: Mapping[str, Any], request: V075K7RootCapAccountedSealedRequestV1
) -> V075K7RootCapAccountedSealedBusinessFrameV1:
    _fields(document, _BUSINESS_KEYS, "accounted sealed business frame")
    expected_refs = _identity_refs(request.route_identity)
    for name, value in expected_refs.items():
        _require_same_json_atom(
            document[name], value, f"business frame route identity field {name}"
        )
    if (
        document["schema"] != "acfqp.v075_k7_root_cap_accounted_sealed_business_frame.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["profile_key"] != PROFILE_KEY
        or type(document["frame_index"]) is not int
        or document["frame_index"] != 1
        or document["frame_role"] != REGISTERED_OUTPUT_FRAME_ROLES[0]
        or document["profile_id"] != request.profile.profile_id
        or document["program_id"] != request.profile.program_id
        or document["request_id"] != request.request_id
        or document["terminal_status"] != execution_v1.REGISTERED_TERMINAL_STATUS
        or document["business_result_frozen_before_suffix"] is not True
        or document["formal_vector_embedded"] is not False
    ):
        _fail("business/cutoff frame schema or fixed semantics changed")
    result = V075K7RootCapAccountedSealedBusinessFrameV1(
        _BUSINESS_FRAME_ISSUER,
        request,
        document["business_result_id"],
        document["partial_native_transcript_id"],
        document["terminal_artifact_id"],
        document["signer_owning_private_replay_attestation_id"],
        document["operational_cutoff_marker_id"],
        document["operational_cutoff_sequence"],
    )
    _require_same_canonical_document(
        document, result.to_document(), "business/cutoff frame"
    )
    return result


def _verify_unavailable(value: Any, reason: str, label: str) -> None:
    if value != _typed_unavailable(reason):
        _fail(f"{label} must remain one exact typed-unavailable blocker")


def _verify_suffix_document(
    document: Mapping[str, Any],
    business: V075K7RootCapAccountedSealedBusinessFrameV1,
) -> V075K7RootCapAccountedSealedAccountingSuffixFrameV1:
    _fields(document, _SUFFIX_KEYS, "accounted sealed accounting suffix frame")
    request = business.request
    expected_refs = _identity_refs(request.route_identity)
    for name, value in expected_refs.items():
        _require_same_json_atom(
            document[name], value, f"accounting suffix route identity field {name}"
        )
    if (
        document["schema"]
        != "acfqp.v075_k7_root_cap_accounted_sealed_accounting_suffix_frame.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["profile_key"] != PROFILE_KEY
        or type(document["frame_index"]) is not int
        or document["frame_index"] != 2
        or document["frame_role"] != REGISTERED_OUTPUT_FRAME_ROLES[1]
        or document["profile_id"] != request.profile.profile_id
        or document["program_id"] != request.profile.program_id
        or document["request_id"] != request.request_id
        or document["business_frame_id"] != business.frame_id
        or document["operational_cutoff_marker_id"] != business.cutoff_marker_id
        or type(document["operational_cutoff_sequence"]) is not int
        or document["operational_cutoff_sequence"] != business.cutoff_sequence
        or type(document["shared_resource_path_count"]) is not int
        or document["shared_resource_path_count"] != len(receipts_v1.SHARED_RESOURCE_PATHS)
        or document["shared_resource_paths"] != [dict(row) for row in _shared_blockers()]
        or document["accounting_suffix_bytes_are_chargeable_output"] is not True
        or document["accounting_content_id_hashes_are_provenance_only"] is not True
        or document["shared_resource_semantics_verified"] is not False
        or any(
            document[name] is not False
            for name in (
                "counter_records_issued", "work_vector_issued",
                "comparison_vector_issued", "formal_vector_authorized",
            )
        )
    ):
        _fail("accounting suffix schema, blockers, or locked claims changed")
    _verify_unavailable(
        document["owner_complete_closure_set"],
        "OWNER_COMPLETE_CLOSURE_SET_NOT_CONNECTED",
        "owner closure set",
    )
    _verify_unavailable(
        document["profile_native_zero_attestation_set"],
        "PROFILE_NATIVE_ZERO_ATTESTATION_SET_NOT_CONNECTED",
        "native-zero set",
    )
    _verify_unavailable(
        document["derived_reconciliation_proof_set"],
        "DERIVED_RECONCILIATION_PROOF_SET_NOT_CONNECTED",
        "derived proof set",
    )
    _verify_unavailable(
        document["output_byte_receipt"],
        "OUTPUT_BYTE_FIXED_POINT_NOT_CONNECTED",
        "output-byte receipt",
    )
    result = V075K7RootCapAccountedSealedAccountingSuffixFrameV1(
        _SUFFIX_FRAME_ISSUER,
        business,
        document["suffix_start_sequence"],
        document["suffix_end_sequence"],
    )
    _require_same_canonical_document(
        document, result.to_document(), "accounting suffix"
    )
    return result


@dataclass(frozen=True, slots=True)
class V075K7RootCapAccountedSealedProtocolReplayV1:
    _issuer: InitVar[object]
    request_id: str
    route_identity_id: str
    business_frame_id: str
    accounting_suffix_frame_id: str
    framed_byte_count: int

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            _fail("accounted sealed protocol replay is caller-minted")
        for value, label in (
            (self.request_id, "request"),
            (self.route_identity_id, "route identity"),
            (self.business_frame_id, "business frame"),
            (self.accounting_suffix_frame_id, "accounting suffix frame"),
        ):
            _cid(value, label)
        _positive(self.framed_byte_count, "framed byte count")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_accounted_sealed_protocol_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "route_identity_id": self.route_identity_id,
            "business_frame_id": self.business_frame_id,
            "accounting_suffix_frame_id": self.accounting_suffix_frame_id,
            "framed_byte_count": self.framed_byte_count,
            "decoded_frame_count": 2,
            "decoded_frame_roles": list(REGISTERED_OUTPUT_FRAME_ROLES),
            "structural_protocol_replay_passed": True,
            "semantic_source_evidence_verified": False,
            "shared_resource_semantics_verified": False,
            "output_byte_fixed_point_verified": False,
            "formal_vector_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return _hash(
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROTOCOL_REPLAY_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_replay_id": self.replay_id}


def verify_v075_k7_root_cap_accounted_sealed_two_frame_output_v1(
    *,
    raw: bytes,
    request: V075K7RootCapAccountedSealedRequestV1,
) -> V075K7RootCapAccountedSealedProtocolReplayV1:
    if type(request) is not V075K7RootCapAccountedSealedRequestV1:
        _fail("two-frame replay requires one exact request")
    request.profile._assert_current()
    first_raw, second_raw = _split_two_frames(raw)
    business = _verify_business_document(
        _load_canonical(first_raw, "business/cutoff frame"), request
    )
    suffix = _verify_suffix_document(
        _load_canonical(second_raw, "accounting suffix frame"), business
    )
    return V075K7RootCapAccountedSealedProtocolReplayV1(
        _REPLAY_ISSUER,
        request.request_id,
        request.route_identity.route_identity_id,
        business.frame_id,
        suffix.frame_id,
        len(raw),
    )


def _accounted_k7_child_main(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Reserved sealed-child entrypoint; fail closed until live hooks exist."""

    raise V075K7RootCapAccountedSealedProductionV1NotReady(
        "the two-frame K7 schema is frozen, but the live K7 body, trusted "
        "shared-resource monitors, output-byte fixed point, and independent "
        "source-byte replay are not connected"
    )


def open_v075_k7_root_cap_accounted_sealed_production_v1() -> NoReturn:
    _accounted_k7_child_main()


__all__ = [
    "CURRENT_READINESS",
    "LIVE_EXECUTION_BLOCKERS",
    "LOCAL_DOMAIN_TAGS",
    "MAX_FRAME_BYTES",
    "MAX_REQUEST_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_OUTPUT_FRAME_ROLES",
    "REQUESTED_OPERATION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7RootCapAccountedSealedAccountingSuffixFrameV1",
    "V075K7RootCapAccountedSealedBusinessFrameV1",
    "V075K7RootCapAccountedSealedIPCProfileV1",
    "V075K7RootCapAccountedSealedIPCV1Error",
    "V075K7RootCapAccountedSealedProductionV1NotReady",
    "V075K7RootCapAccountedSealedProtocolReplayV1",
    "V075K7RootCapAccountedSealedRequestV1",
    "V075K7RootCapAccountedSealedRouteIdentityV1",
    "encode_v075_k7_root_cap_accounted_sealed_two_frame_output_v1",
    "freeze_v075_k7_root_cap_accounted_sealed_accounting_suffix_frame_v1",
    "freeze_v075_k7_root_cap_accounted_sealed_business_frame_v1",
    "freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1",
    "freeze_v075_k7_root_cap_accounted_sealed_request_v1",
    "freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1",
    "open_v075_k7_root_cap_accounted_sealed_production_v1",
    "verify_v075_k7_root_cap_accounted_sealed_request_bytes_v1",
    "verify_v075_k7_root_cap_accounted_sealed_two_frame_output_v1",
]
