"""Honest V6 pre-execution upper candidate for canonical direct fallback.

The canonical H=1 identity and seven fallback cardinalities are accepted only
from the issuer-owned authorities in
``construction_k7_canonical_infeasible_fallback_acquisition_v1``.  Route-order
evidence is accepted only as a typed ``AccessEventLogV1`` and is fully replayed
under the official estimate-before-execute protocol.

The current direct-fallback runner does not yet enforce a complete nine-path
shared-resource cap profile.  Consequently this module deliberately emits a
``FINITE_ADMISSION_CAP_CANDIDATE`` rather than a tight route upper.  It cannot
authorize execution or formal ``actual <= upper`` verification.  The object
is the identity-bound construction prerequisite from which a future enforced
supervisor profile can be substituted as one new content-addressed object.

No V1 route upper is reused or relabelled.  No CounterRecord, WorkVector,
ComparisonVector, terminal, Gate, scalar, or break-even result is issued.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_canonical_infeasible_fallback_owned_runner_v2 as owned_runner_v2
from acfqp import v075_k7_broker_worker_entry_v1 as broker_worker_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as broker_ipc_v1
from acfqp import v075_k7_outer_attempt_cgroup_v1 as outer_cgroup_v1
from acfqp import v075_k7_parent_atomic_executor_v1 as parent_executor_v1
from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessOperation,
    AccessProtocolV1Error,
    AccessProtocolViolation,
    AccessRouteScope,
    PRESELECTION_READ_OPERATIONS,
    ProtocolSequenceProfileV1,
    replay_access_protocol,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    TypedNotApplicable,
)


SCHEMA_VERSION = "6.1.0"
PROFILE_KEY = "construction_k7_direct_fallback_route_upper_v6"
PROPOSED_CONTRACT_VERSION = "2.0.46"
UPPER_KIND = "FINITE_ADMISSION_CAP_CANDIDATE"
CONSTRUCTION_ONLY = True

OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

EXPECTED_OPERATIONAL_PATH_COUNT = 182
EXPECTED_STAGE_FORBIDDEN_ZERO_COUNT = 166
EXPECTED_OWNER_EXACT_COUNT = 7
EXPECTED_SHARED_RESOURCE_CAP_COUNT = 9
EXPECTED_COMPARISON_AXIS_COUNT = 8

_PREPARATION_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-route-preparation:v6"
)
_CAP_SOURCE_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-shared-cap-source:v6"
)
_CAP_PROFILE_DOMAIN = "acfqp:construction-k7-direct-fallback-route-cap:v6"
_BARRIER_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-preexecution-barrier:v6"
)
_CARDINALITY_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-cardinality-evidence:v6"
)
_FORMULA_DOMAIN = "acfqp:construction-k7-direct-fallback-route-formula:v6"
_UPPER_DOMAIN = "acfqp:construction-k7-direct-fallback-route-upper:v6"
_DECISION_DOMAIN = "acfqp:construction-k7-direct-fallback-route-decision:v6"
_BUNDLE_DOMAIN = "acfqp:construction-k7-direct-fallback-route-freeze:v6"


class ConstructionK7DirectFallbackRouteUpperV6Error(ValueError):
    """The typed source, access replay, cap source, or V6 candidate is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DirectFallbackRouteUpperV6Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackRouteUpperV6Error(
            f"{label} must be one exact content ID"
        ) from error


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _source_sha256(module: Any) -> str:
    path = getattr(module, "__file__", None)
    if type(path) is not str:
        _fail("shared-cap source module has no filesystem identity")
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as error:
        raise ConstructionK7DirectFallbackRouteUpperV6Error(
            "shared-cap source bytes are unavailable"
        ) from error


def _validated_comparison_profile(registry: Any) -> Any:
    comparison = registry_v6.official_comparison_profile_v6(registry)
    axis_names = tuple(axis.name for axis in comparison.axes)
    if (
        len(axis_names) != EXPECTED_COMPARISON_AXIS_COUNT
        or len(set(axis_names)) != EXPECTED_COMPARISON_AXIS_COUNT
    ):
        _fail(
            "official comparison profile must contain exactly eight distinct axes"
        )
    return comparison


OWNER_EXACT_UPPERS: tuple[tuple[str, int], ...] = tuple(
    sorted(
        {
            "control.cap_checks": 56,
            "control.cap_rejections": 0,
            "fallback.states_expanded": 8,
            "fallback.actions_evaluated": 16,
            "fallback.ground_steps": 16,
            "fallback.outcome_rows": 96,
            "fallback.bellman_backups": 16,
        }.items()
    )
)


class LeafUpperSourceV6(str, Enum):
    STAGE_FORBIDDEN_ZERO = "STAGE_FORBIDDEN_ZERO"
    EXACT_TYPED_H1_CARDINALITY = "EXACT_TYPED_H1_CARDINALITY"
    UNENFORCED_SHARED_ADMISSION_CAP = "UNENFORCED_SHARED_ADMISSION_CAP"


class CapEnforcementStatusV6(str, Enum):
    CURRENT_RUNNER_ENFORCED = "CURRENT_RUNNER_ENFORCED"
    EXTERNAL_PROFILE_NOT_BOUND_TO_CURRENT_RUNNER = (
        "EXTERNAL_PROFILE_NOT_BOUND_TO_CURRENT_RUNNER"
    )
    NO_COMPLETE_AGGREGATE_ENFORCEMENT = "NO_COMPLETE_AGGREGATE_ENFORCEMENT"


@dataclass(frozen=True, slots=True)
class SharedAdmissionCapRowV6:
    path: str
    value: int
    source_module: str
    source_symbol: str
    source_value: int
    enforcement_status: CapEnforcementStatusV6

    def __post_init__(self) -> None:
        if not all(
            type(value) is str and value
            for value in (self.path, self.source_module, self.source_symbol)
        ):
            _fail("shared admission-cap row has an invalid source label")
        if type(self.value) is not int or self.value < 0:
            _fail("shared admission cap must be a nonnegative exact integer")
        if type(self.source_value) is not int or self.source_value < 0:
            _fail("shared admission source value must be a nonnegative exact integer")
        try:
            object.__setattr__(
                self,
                "enforcement_status",
                CapEnforcementStatusV6(self.enforcement_status),
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackRouteUpperV6Error(
                "shared admission-cap enforcement status is invalid"
            ) from error

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "value": self.value,
            "source_module": self.source_module,
            "source_symbol": self.source_symbol,
            "source_value": self.source_value,
            "enforcement_status": self.enforcement_status.value,
        }


_CAP_SOURCE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class DirectFallbackSharedResourceCapSourceV6:
    _issuer: InitVar[object]
    current_runner_module: str
    current_runner_source_sha256: str
    source_module_sha256: tuple[tuple[str, str], ...]
    rows: tuple[SharedAdmissionCapRowV6, ...]
    _source_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CAP_SOURCE_ISSUER:
            _fail("shared-resource cap source is issuer-owned")
        if not _matches_shared_cap_source(self):
            _fail("shared-resource cap source differs from live code/constants")
        object.__setattr__(self, "_source_id", _content_id(_CAP_SOURCE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_shared_cap_source.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "current_runner_module": self.current_runner_module,
            "current_runner_source_sha256": self.current_runner_source_sha256,
            "source_module_sha256": [
                {"module": module, "sha256": digest}
                for module, digest in self.source_module_sha256
            ],
            "rows": [row.to_document() for row in self.rows],
            "all_nine_paths_finite": True,
            "all_nine_paths_enforced_by_current_runner": False,
            "formal_actual_compliance_eligible": False,
            "production_join_blocker": (
                "CURRENT_DIRECT_FALLBACK_RUNNER_LACKS_COMPLETE_SHARED_CAP_ENFORCEMENT"
            ),
            "construction_only": True,
        }

    @property
    def cap_source_id(self) -> str:
        if not _matches_shared_cap_source(self):
            _fail("shared-resource cap source became stale")
        current = _content_id(_CAP_SOURCE_DOMAIN, self._payload())
        if current != self._source_id:
            _fail("shared-resource cap source changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_cap_source_id": self.cap_source_id}


def _cap_rows() -> tuple[SharedAdmissionCapRowV6, ...]:
    # The three event caps are finite construction admission candidates only;
    # the current runner has no complete shared-resource recorder/enforcer.
    no_aggregate = CapEnforcementStatusV6.NO_COMPLETE_AGGREGATE_ENFORCEMENT
    external = CapEnforcementStatusV6.EXTERNAL_PROFILE_NOT_BOUND_TO_CURRENT_RUNNER
    rows = (
        SharedAdmissionCapRowV6(
            "common.hash_invocations", 4096, __name__, "candidate_common_event_cap", 4096, no_aggregate
        ),
        SharedAdmissionCapRowV6(
            "common.integrity_checks", 4096, __name__, "candidate_common_event_cap", 4096, no_aggregate
        ),
        SharedAdmissionCapRowV6(
            "common.protocol_checks", 4096, __name__, "candidate_common_event_cap", 4096, no_aggregate
        ),
        SharedAdmissionCapRowV6(
            "io.mounted_bytes_peak",
            broker_ipc_v1.MAX_STREAM_BYTES,
            broker_ipc_v1.__name__,
            "MAX_STREAM_BYTES",
            broker_ipc_v1.MAX_STREAM_BYTES,
            external,
        ),
        SharedAdmissionCapRowV6(
            "io.output_bytes",
            broker_worker_v1.MAX_OUTPUT_BYTES,
            broker_worker_v1.__name__,
            "MAX_OUTPUT_BYTES",
            broker_worker_v1.MAX_OUTPUT_BYTES,
            external,
        ),
        SharedAdmissionCapRowV6(
            "io.read_bytes",
            broker_ipc_v1.MAX_STREAM_BYTES,
            broker_ipc_v1.__name__,
            "MAX_STREAM_BYTES",
            broker_ipc_v1.MAX_STREAM_BYTES,
            no_aggregate,
        ),
        SharedAdmissionCapRowV6(
            "io.staged_bytes",
            broker_ipc_v1.MAX_STREAM_BYTES,
            broker_ipc_v1.__name__,
            "MAX_STREAM_BYTES",
            broker_ipc_v1.MAX_STREAM_BYTES,
            no_aggregate,
        ),
        SharedAdmissionCapRowV6(
            "memory.working_bytes_peak",
            outer_cgroup_v1.FIXED_OUTER_MEMORY_MAX_BYTES,
            outer_cgroup_v1.__name__,
            "FIXED_OUTER_MEMORY_MAX_BYTES",
            outer_cgroup_v1.FIXED_OUTER_MEMORY_MAX_BYTES,
            external,
        ),
        SharedAdmissionCapRowV6(
            "process.launches",
            2,
            __name__,
            "candidate_two_role_launch_topology",
            2,
            no_aggregate,
        ),
    )
    return tuple(sorted(rows, key=lambda row: row.path))


def _shared_cap_source_values() -> tuple[Any, ...]:
    module_rows = tuple(
        sorted(
            (
                (__name__, hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
                (owned_runner_v2.__name__, _source_sha256(owned_runner_v2)),
                (broker_worker_v1.__name__, _source_sha256(broker_worker_v1)),
                (broker_ipc_v1.__name__, _source_sha256(broker_ipc_v1)),
                (outer_cgroup_v1.__name__, _source_sha256(outer_cgroup_v1)),
                (parent_executor_v1.__name__, _source_sha256(parent_executor_v1)),
            )
        )
    )
    return (
        owned_runner_v2.__name__,
        _source_sha256(owned_runner_v2),
        module_rows,
        _cap_rows(),
    )


def _matches_shared_cap_source(
    candidate: DirectFallbackSharedResourceCapSourceV6,
) -> bool:
    return _shared_cap_source_values() == (
        candidate.current_runner_module,
        candidate.current_runner_source_sha256,
        candidate.source_module_sha256,
        candidate.rows,
    )


def freeze_direct_fallback_shared_resource_cap_source_v6(
) -> DirectFallbackSharedResourceCapSourceV6:
    return DirectFallbackSharedResourceCapSourceV6(
        _CAP_SOURCE_ISSUER, *_shared_cap_source_values()
    )


@dataclass(frozen=True, slots=True)
class DirectFallbackRoutePreparationV6:
    source_preexecution: acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1 = field(
        repr=False, compare=False
    )
    durable_proof_bytes: bytes = field(repr=False, compare=False)
    current_identity: acquisition_v1.CanonicalFallbackCurrentIdentityV1 = field(
        repr=False, compare=False
    )
    route_context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    source_preexecution_candidate_id: str
    current_identity_attestation_id: str
    source_cardinality_evidence_id: str
    source_cap_profile_id: str

    def __post_init__(self) -> None:
        _validate_source_preexecution(
            self.source_preexecution,
            durable_proof_bytes=self.durable_proof_bytes,
            current_identity=self.current_identity,
        )
        for value, label in (
            (self.source_preexecution_candidate_id, "source preexecution candidate"),
            (self.current_identity_attestation_id, "current identity attestation"),
            (self.source_cardinality_evidence_id, "source cardinality evidence"),
            (self.source_cap_profile_id, "source cap profile"),
        ):
            _cid(value, label)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_route_preparation.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_context": self.route_context.to_dict(),
            "decision_point": self.decision_point.to_dict(),
            "source_preexecution_candidate_id": self.source_preexecution_candidate_id,
            "durable_proof_sha256": hashlib.sha256(
                self.durable_proof_bytes
            ).hexdigest(),
            "current_identity_attestation_id": self.current_identity_attestation_id,
            "source_cardinality_evidence_id": self.source_cardinality_evidence_id,
            "source_cap_profile_id": self.source_cap_profile_id,
            "source_v1_upper_reused": False,
            "construction_only": True,
        }

    @property
    def preparation_id(self) -> str:
        _validate_preparation(self)
        return _content_id(_PREPARATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_preparation_id": self.preparation_id}


def _validate_source_preexecution(
    value: Any,
    *,
    durable_proof_bytes: bytes,
    current_identity: acquisition_v1.CanonicalFallbackCurrentIdentityV1,
) -> acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1:
    if type(value) is not acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1:
        _fail("canonical H1 source requires the issuer-owned typed preexecution authority")
    try:
        replayed = (
            acquisition_v1.replay_canonical_direct_fallback_preexecution_candidate_v1(
                durable_proof_bytes,
                current_identity=current_identity,
                cap_profile=None,
            )
        )
        candidate_id = value.candidate_id
        current_id = value.current_identity.attestation_id
        source_counts = dict(value.cardinality.counts)
        supplied_document = value.to_document()
        replayed_document = replayed.to_document()
    except (
        AttributeError,
        TypeError,
        ValueError,
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
    ) as error:
        raise ConstructionK7DirectFallbackRouteUpperV6Error(
            "canonical H1 preexecution authority failed durable independent replay"
        ) from error
    if (
        not candidate_id
        or not current_id
        or value.current_identity is not current_identity
        or supplied_document != replayed_document
        or candidate_id != replayed.candidate_id
        or current_id != replayed.current_identity.attestation_id
        or value.decision.selected_route is not RouteSelection.FALLBACK
        or value.decision.selected_upper_id != value.upper.route_upper_bound_envelope_id
        or any(source_counts.get(path) != expected for path, expected in OWNER_EXACT_UPPERS)
    ):
        _fail(
            "typed canonical H1 authority differs from durable independent replay"
        )
    return replayed


def _expected_context_and_point(
    source: acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1,
) -> tuple[RouteDecisionContextV1, DecisionPointV1]:
    registry = registry_v6.official_counter_registry_v6()
    comparison = _validated_comparison_profile(registry)
    source_context = source.route_context
    context = RouteDecisionContextV1(
        source_context.preregistration_id,
        source_context.protocol_id,
        comparison.comparison_profile_id,
        registry.registry_id,
        source_context.structural_id,
        source_context.query_id,
        source_context.selected_plan_id,
        source_context.threshold_profile_id,
        source_context.build_epoch_id,
        source_context.logical_occurrence_id,
        source_context.route_attempt_id,
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        TypedNotApplicable("direct fallback has no local frontier"),
        TypedNotApplicable("direct fallback has no causal search"),
        source.decision_point.common_prefix_work_id,
    )
    return context, point


def _validate_preparation(value: DirectFallbackRoutePreparationV6) -> None:
    _validate_source_preexecution(
        value.source_preexecution,
        durable_proof_bytes=value.durable_proof_bytes,
        current_identity=value.current_identity,
    )
    context, point = _expected_context_and_point(value.source_preexecution)
    source = value.source_preexecution
    if (
        value.route_context != context
        or value.decision_point != point
        or value.source_preexecution_candidate_id != source.candidate_id
        or value.current_identity_attestation_id != source.current_identity.attestation_id
        or value.source_cardinality_evidence_id != source.cardinality.cardinality_evidence_id
        or value.source_cap_profile_id != source.cap_profile.ground_fallback_cap_profile_id
    ):
        _fail("V6 route preparation differs from the typed canonical H1 source")


def prepare_construction_k7_direct_fallback_route_upper_v6(
    source_preexecution: acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1,
    *,
    durable_proof_bytes: bytes,
    current_identity: acquisition_v1.CanonicalFallbackCurrentIdentityV1,
) -> DirectFallbackRoutePreparationV6:
    _validate_source_preexecution(
        source_preexecution,
        durable_proof_bytes=durable_proof_bytes,
        current_identity=current_identity,
    )
    context, point = _expected_context_and_point(source_preexecution)
    result = DirectFallbackRoutePreparationV6(
        source_preexecution,
        durable_proof_bytes,
        current_identity,
        context,
        point,
        source_preexecution.candidate_id,
        source_preexecution.current_identity.attestation_id,
        source_preexecution.cardinality.cardinality_evidence_id,
        source_preexecution.cap_profile.ground_fallback_cap_profile_id,
    )
    _validate_preparation(result)
    return result


@dataclass(frozen=True, slots=True)
class DirectFallbackPreexecutionBarrierV6:
    route_decision_context_id: str
    decision_point_id: str
    protocol_sequence_profile_id: str
    access_event_log_id: str
    access_event_count: int
    replayed_operations: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.route_decision_context_id, "route decision context"),
            (self.decision_point_id, "decision point"),
            (self.protocol_sequence_profile_id, "protocol profile"),
            (self.access_event_log_id, "access-event log"),
        ):
            _cid(value, label)
        if type(self.access_event_count) is not int or self.access_event_count < 0:
            _fail("preexecution access-event count must be nonnegative")
        allowed = {operation.value for operation in PRESELECTION_READ_OPERATIONS}
        if (
            len(self.replayed_operations) != self.access_event_count
            or any(operation not in allowed for operation in self.replayed_operations)
        ):
            _fail("preexecution barrier contains a forbidden access operation")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_preexecution_barrier.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
            "access_event_log_id": self.access_event_log_id,
            "access_event_count": self.access_event_count,
            "freeze_after_sequence": self.access_event_count,
            "replayed_operations": list(self.replayed_operations),
            "all_events_common_preselection_reads": True,
            "kernel_step_before_freeze": False,
            "local_or_fallback_execution_before_freeze": False,
            "route_zero_derived_from_access_protocol": True,
            "caller_supplied_zero_snapshot_used": False,
            "actual_hints_supplied": False,
            "construction_only": True,
        }

    @property
    def barrier_id(self) -> str:
        return _content_id(_BARRIER_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preexecution_barrier_id": self.barrier_id}


@dataclass(frozen=True, slots=True)
class DirectFallbackCapProfileV6:
    route_decision_context_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    source_preexecution_candidate_id: str
    source_ground_cap_profile_id: str
    shared_resource_cap_source_id: str
    owner_limits: tuple[tuple[str, int], ...]
    shared_resource_limits: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for name in (
            "route_decision_context_id",
            "counter_registry_id",
            "stage_profile_id",
            "comparison_profile_id",
            "source_preexecution_candidate_id",
            "source_ground_cap_profile_id",
            "shared_resource_cap_source_id",
        ):
            _cid(getattr(self, name), name)
        if self.owner_limits != OWNER_EXACT_UPPERS or len(self.shared_resource_limits) != 9:
            _fail("V6 direct-fallback cap profile changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_route_cap.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "route_kind": RouteKind.DIRECT_FALLBACK.value,
            "source_preexecution_candidate_id": self.source_preexecution_candidate_id,
            "source_ground_cap_profile_id": self.source_ground_cap_profile_id,
            "shared_resource_cap_source_id": self.shared_resource_cap_source_id,
            "owner_limits": [
                {"path": path, "value": value} for path, value in self.owner_limits
            ],
            "shared_resource_limits": [
                {"path": path, "value": value}
                for path, value in self.shared_resource_limits
            ],
            "all_limits_finite": True,
            "all_limits_current_runner_enforced": False,
            "formal_actual_compliance_eligible": False,
            "construction_only": True,
        }

    @property
    def cap_profile_id(self) -> str:
        return _content_id(_CAP_PROFILE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_cap_profile_id": self.cap_profile_id}


@dataclass(frozen=True, slots=True)
class DirectFallbackCardinalityEvidenceV6:
    route_decision_context_id: str
    decision_point_id: str
    route_cap_profile_id: str
    source_preexecution_candidate_id: str
    source_cardinality_evidence_id: str
    counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for name in (
            "route_decision_context_id",
            "decision_point_id",
            "route_cap_profile_id",
            "source_preexecution_candidate_id",
            "source_cardinality_evidence_id",
        ):
            _cid(getattr(self, name), name)
        if self.counts != OWNER_EXACT_UPPERS:
            _fail("V6 cardinalities differ from the typed exact H1 authority")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_cardinality_evidence.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "route_cap_profile_id": self.route_cap_profile_id,
            "route_kind": RouteKind.DIRECT_FALLBACK.value,
            "source_preexecution_candidate_id": self.source_preexecution_candidate_id,
            "source_cardinality_evidence_id": self.source_cardinality_evidence_id,
            "counts": [
                {"path": path, "value": value} for path, value in self.counts
            ],
            "measured_before_execution": True,
            "depends_on_actual_route_work": False,
            "construction_only": True,
        }

    @property
    def cardinality_evidence_id(self) -> str:
        return _content_id(_CARDINALITY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cardinality_evidence_id": self.cardinality_evidence_id}


@dataclass(frozen=True, slots=True)
class DirectFallbackLeafUpperTermV6:
    target_leaf: str
    source_kind: LeafUpperSourceV6
    source_name: str

    def __post_init__(self) -> None:
        if type(self.target_leaf) is not str or not self.target_leaf:
            _fail("leaf-upper target must be one nonempty path")
        try:
            object.__setattr__(self, "source_kind", LeafUpperSourceV6(self.source_kind))
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackRouteUpperV6Error(
                "leaf-upper source kind is invalid"
            ) from error
        if type(self.source_name) is not str or not self.source_name:
            _fail("leaf-upper source name must be nonempty")

    def to_document(self) -> dict[str, Any]:
        return {
            "target_leaf": self.target_leaf,
            "source_kind": self.source_kind.value,
            "source_name": self.source_name,
            "coefficient": 1,
            "addend": 0,
        }


@dataclass(frozen=True, slots=True)
class DirectFallbackRouteFormulaV6:
    route_decision_context_id: str
    decision_point_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    route_cap_profile_id: str
    cardinality_evidence_id: str
    terms: tuple[DirectFallbackLeafUpperTermV6, ...]

    @property
    def disposition_counts(self) -> dict[LeafUpperSourceV6, int]:
        return {
            kind: sum(term.source_kind is kind for term in self.terms)
            for kind in LeafUpperSourceV6
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_route_formula.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "route_cap_profile_id": self.route_cap_profile_id,
            "cardinality_evidence_id": self.cardinality_evidence_id,
            "route_kind": RouteKind.DIRECT_FALLBACK.value,
            "terms": [term.to_document() for term in self.terms],
            "caller_supplied_actual_allowed": False,
            "construction_only": True,
        }

    @property
    def formula_id(self) -> str:
        return _content_id(_FORMULA_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "formula_id": self.formula_id}


@dataclass(frozen=True, slots=True)
class DirectFallbackRouteUpperV6:
    route_context: RouteDecisionContextV1
    decision_point_id: str
    stage_profile_id: str
    route_cap_profile_id: str
    cardinality_evidence_id: str
    formula_id: str
    leaf_upper_bounds: tuple[tuple[str, int], ...]
    comparison_upper_bounds: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.decision_point_id, "decision point"),
            (self.stage_profile_id, "stage profile"),
            (self.route_cap_profile_id, "route cap profile"),
            (self.cardinality_evidence_id, "cardinality evidence"),
            (self.formula_id, "route formula"),
        ):
            _cid(value, label)
        registry = registry_v6.official_counter_registry_v6()
        comparison = _validated_comparison_profile(registry)
        expected_axis_names = tuple(axis.name for axis in comparison.axes)
        supplied_axis_names = tuple(
            axis for axis, _value in self.comparison_upper_bounds
        )
        if (
            len(self.comparison_upper_bounds) != EXPECTED_COMPARISON_AXIS_COUNT
            or supplied_axis_names != expected_axis_names
            or any(
                type(value) is not int or value < 0
                for _axis, value in self.comparison_upper_bounds
            )
        ):
            _fail(
                "V6 route upper requires exactly the eight official comparison axes"
            )

    def _payload(self) -> dict[str, Any]:
        context = self.route_context
        return {
            "schema": "acfqp.construction_k7_direct_fallback_route_upper.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_context": context.to_dict(),
            "decision_point_id": self.decision_point_id,
            "stage_profile_id": self.stage_profile_id,
            "route_cap_profile_id": self.route_cap_profile_id,
            "cardinality_evidence_id": self.cardinality_evidence_id,
            "formula_id": self.formula_id,
            "route_kind": RouteKind.DIRECT_FALLBACK.value,
            "upper_kind": UPPER_KIND,
            "leaf_upper_bounds": [
                {"path": path, "value": value} for path, value in self.leaf_upper_bounds
            ],
            "comparison_upper_bounds": [
                {"axis": axis, "value": value}
                for axis, value in self.comparison_upper_bounds
            ],
            "formal_actual_compliance_eligible": False,
            "authorizes_route_selection": False,
            "legacy_v1_route_upper_reused": False,
            "legacy_v1_route_upper_promoted_as_v6": False,
            "construction_only": True,
        }

    @property
    def route_upper_id(self) -> str:
        return _content_id(_UPPER_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_upper_candidate_id": self.route_upper_id}


@dataclass(frozen=True, slots=True)
class DirectFallbackRouteDecisionV6:
    route_decision_context_id: str
    decision_point_id: str
    preexecution_barrier_id: str
    fallback_upper_candidate_id: str
    frozen_after_access_sequence: int

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_route_decision.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "preexecution_barrier_id": self.preexecution_barrier_id,
            "fallback_upper_candidate_id": self.fallback_upper_candidate_id,
            "selected_route_candidate": RouteSelection.FALLBACK.value,
            "comparison": "MISSING_LOCAL_UPPER",
            "frozen_after_access_sequence": self.frozen_after_access_sequence,
            "execution_permitted": False,
            "formal_route_decision": False,
            "blocker": "SHARED_RESOURCE_CAP_ENFORCEMENT_INCOMPLETE",
            "construction_only": True,
        }

    @property
    def route_decision_id(self) -> str:
        return _content_id(_DECISION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_decision_candidate_id": self.route_decision_id}


_BUNDLE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ConstructionK7DirectFallbackRouteFreezeV6:
    _issuer: InitVar[object]
    preparation: DirectFallbackRoutePreparationV6
    access_log: AccessEventLogV1 = field(repr=False, compare=False)
    cap_source: DirectFallbackSharedResourceCapSourceV6
    barrier: DirectFallbackPreexecutionBarrierV6
    cap_profile: DirectFallbackCapProfileV6
    cardinality: DirectFallbackCardinalityEvidenceV6
    formula: DirectFallbackRouteFormulaV6
    upper: DirectFallbackRouteUpperV6
    decision: DirectFallbackRouteDecisionV6
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUNDLE_ISSUER:
            _fail("V6 direct-fallback route freeze is issuer-owned")
        _validate_bundle(self)
        object.__setattr__(self, "_bundle_id", _content_id(_BUNDLE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_route_freeze.v6",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "route_preparation": self.preparation.to_document(),
            "preexecution_access_log": self.access_log.to_dict(),
            "shared_resource_cap_source": self.cap_source.to_document(),
            "preexecution_barrier": self.barrier.to_document(),
            "cap_profile": self.cap_profile.to_document(),
            "cardinality_evidence": self.cardinality.to_document(),
            "route_upper_formula": self.formula.to_document(),
            "fallback_upper_candidate": self.upper.to_document(),
            "fallback_decision_candidate": self.decision.to_document(),
            "partition": {
                "operational_paths": EXPECTED_OPERATIONAL_PATH_COUNT,
                "stage_forbidden_zero": EXPECTED_STAGE_FORBIDDEN_ZERO_COUNT,
                "owner_exact_cardinality": EXPECTED_OWNER_EXACT_COUNT,
                "shared_resource_finite_cap_candidate": EXPECTED_SHARED_RESOURCE_CAP_COUNT,
            },
            "upper_kind": UPPER_KIND,
            "formal_actual_compliance_eligible": False,
            "formal_route_decision_issued": False,
            "production_join_completed": False,
            "production_join_blockers": [
                "CURRENT_DIRECT_FALLBACK_RUNNER_LACKS_COMPLETE_SHARED_CAP_ENFORCEMENT",
                "NINE_SHARED_RESOURCE_CAPS_NOT_FORMAL_ACTUAL_UPPERS",
            ],
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "terminal_artifact_issued": False,
            "legacy_v1_route_upper_reused": False,
            "construction_only": True,
            "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
            "official_scalar_cost": OFFICIAL_SCALAR_COST,
            "official_N_break_even": OFFICIAL_N_BREAK_EVEN,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
        }

    @property
    def bundle_id(self) -> str:
        _validate_bundle(self)
        current = _content_id(_BUNDLE_DOMAIN, self._payload())
        if current != self._bundle_id:
            _fail("V6 direct-fallback route freeze changed after issuance")
        return current

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_freeze_id": self.bundle_id}


def _formula_terms() -> tuple[DirectFallbackLeafUpperTermV6, ...]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    owner = dict(OWNER_EXACT_UPPERS)
    shared = {row.path: row.value for row in _cap_rows()}
    allowed = set(
        stage.by_stage[
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ].allowed_nonzero_paths
    )
    operational = {row.path for row in registry.operational_leaves}
    if (allowed & operational) != set(owner) | set(shared):
        _fail("V6 DIRECT_FALLBACK ownership differs from the 7+9 sources")
    result = []
    for leaf in registry.operational_leaves:
        if leaf.path in owner:
            kind = LeafUpperSourceV6.EXACT_TYPED_H1_CARDINALITY
            source = leaf.path
        elif leaf.path in shared:
            kind = LeafUpperSourceV6.UNENFORCED_SHARED_ADMISSION_CAP
            source = leaf.path
        else:
            kind = LeafUpperSourceV6.STAGE_FORBIDDEN_ZERO
            source = "DIRECT_FALLBACK_STAGE_PROFILE"
        result.append(DirectFallbackLeafUpperTermV6(leaf.path, kind, source))
    return tuple(result)


def _leaf_uppers(
    terms: tuple[DirectFallbackLeafUpperTermV6, ...],
) -> tuple[tuple[str, int], ...]:
    owner = dict(OWNER_EXACT_UPPERS)
    shared = {row.path: row.value for row in _cap_rows()}
    result = []
    for term in terms:
        if term.source_kind is LeafUpperSourceV6.EXACT_TYPED_H1_CARDINALITY:
            value = owner[term.source_name]
        elif term.source_kind is LeafUpperSourceV6.UNENFORCED_SHARED_ADMISSION_CAP:
            value = shared[term.source_name]
        else:
            value = 0
        result.append((term.target_leaf, value))
    return tuple(result)


def _comparison_uppers(
    leaf_uppers: tuple[tuple[str, int], ...],
) -> tuple[tuple[str, int], ...]:
    registry = registry_v6.official_counter_registry_v6()
    comparison = _validated_comparison_profile(registry)
    values = dict(leaf_uppers)
    grouped: dict[str, list[int]] = {axis.name: [] for axis in comparison.axes}
    for term in comparison.terms:
        grouped[term.target_axis].append(values[term.source_leaf])
    result = []
    for axis in comparison.axes:
        candidates = grouped[axis.name]
        if not candidates:
            _fail("V6 comparison candidate omitted one shared axis")
        result.append(
            (
                axis.name,
                sum(candidates) if axis.reducer is ReducerEnum.SUM else max(candidates),
            )
        )
    if len(result) != EXPECTED_COMPARISON_AXIS_COUNT:
        _fail("V6 comparison candidate must contain exactly eight axes")
    return tuple(result)


def _replay_preselection_log(
    preparation: DirectFallbackRoutePreparationV6,
    log: AccessEventLogV1,
) -> DirectFallbackPreexecutionBarrierV6:
    if type(log) is not AccessEventLogV1:
        _fail("preexecution ordering requires a typed AccessEventLogV1")
    try:
        parsed = AccessEventLogV1.from_dict(log.to_dict())
        profile = ProtocolSequenceProfileV1()
        replay_access_protocol(parsed, profile)
    except (AccessProtocolV1Error, AccessProtocolViolation, TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackRouteUpperV6Error(
            "preselection access protocol replay rejected the log"
        ) from error
    if (
        parsed != log
        or parsed.is_frozen
        or parsed.route_attempt_id != preparation.route_context.route_attempt_id
        or parsed.decision_point_id != preparation.decision_point.decision_point_id
        or any(
            event.operation not in PRESELECTION_READ_OPERATIONS
            or event.route_scope is not AccessRouteScope.COMMON
            for event in parsed.events
        )
    ):
        _fail("access log is stale, frozen, or contains route execution before freeze")
    return DirectFallbackPreexecutionBarrierV6(
        preparation.route_context.route_decision_context_id,
        preparation.decision_point.decision_point_id,
        profile.protocol_sequence_profile_id,
        parsed.access_event_log_id,
        len(parsed.events),
        tuple(event.operation.value for event in parsed.events),
    )


def _validate_bundle(bundle: ConstructionK7DirectFallbackRouteFreezeV6) -> None:
    _validate_preparation(bundle.preparation)
    expected_cap_source = freeze_direct_fallback_shared_resource_cap_source_v6()
    if bundle.cap_source.to_document() != expected_cap_source.to_document():
        _fail("shared-resource cap source is fake or stale")
    expected_barrier = _replay_preselection_log(bundle.preparation, bundle.access_log)
    if bundle.barrier != expected_barrier:
        _fail("preexecution barrier differs from full access-protocol replay")
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = _validated_comparison_profile(registry)
    source = bundle.preparation.source_preexecution
    shared_limits = tuple((row.path, row.value) for row in bundle.cap_source.rows)
    expected_cap = DirectFallbackCapProfileV6(
        bundle.preparation.route_context.route_decision_context_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        source.candidate_id,
        source.cap_profile.ground_fallback_cap_profile_id,
        bundle.cap_source.cap_source_id,
        OWNER_EXACT_UPPERS,
        shared_limits,
    )
    if bundle.cap_profile != expected_cap:
        _fail("V6 cap profile differs from typed owner/shared sources")
    expected_cardinality = DirectFallbackCardinalityEvidenceV6(
        bundle.preparation.route_context.route_decision_context_id,
        bundle.preparation.decision_point.decision_point_id,
        expected_cap.cap_profile_id,
        source.candidate_id,
        source.cardinality.cardinality_evidence_id,
        OWNER_EXACT_UPPERS,
    )
    if bundle.cardinality != expected_cardinality:
        _fail("V6 cardinality evidence differs from the typed H1 authority")
    terms = _formula_terms()
    expected_formula = DirectFallbackRouteFormulaV6(
        bundle.preparation.route_context.route_decision_context_id,
        bundle.preparation.decision_point.decision_point_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        expected_cap.cap_profile_id,
        expected_cardinality.cardinality_evidence_id,
        terms,
    )
    counts = expected_formula.disposition_counts
    if (
        bundle.formula != expected_formula
        or counts[LeafUpperSourceV6.STAGE_FORBIDDEN_ZERO]
        != EXPECTED_STAGE_FORBIDDEN_ZERO_COUNT
        or counts[LeafUpperSourceV6.EXACT_TYPED_H1_CARDINALITY]
        != EXPECTED_OWNER_EXACT_COUNT
        or counts[LeafUpperSourceV6.UNENFORCED_SHARED_ADMISSION_CAP]
        != EXPECTED_SHARED_RESOURCE_CAP_COUNT
    ):
        _fail("V6 formula or 166+7+9 partition changed")
    leaf = _leaf_uppers(terms)
    axes = _comparison_uppers(leaf)
    expected_upper = DirectFallbackRouteUpperV6(
        bundle.preparation.route_context,
        bundle.preparation.decision_point.decision_point_id,
        stage.stage_profile_id,
        expected_cap.cap_profile_id,
        expected_cardinality.cardinality_evidence_id,
        expected_formula.formula_id,
        leaf,
        axes,
    )
    if bundle.upper != expected_upper:
        _fail("V6 finite admission upper candidate differs from replay")
    expected_decision = DirectFallbackRouteDecisionV6(
        bundle.preparation.route_context.route_decision_context_id,
        bundle.preparation.decision_point.decision_point_id,
        expected_barrier.barrier_id,
        expected_upper.route_upper_id,
        len(bundle.access_log.events),
    )
    if bundle.decision != expected_decision:
        _fail("fallback decision candidate was not frozen at the replayed boundary")


def freeze_construction_k7_direct_fallback_route_upper_v6(
    *,
    preparation: DirectFallbackRoutePreparationV6,
    source_preexecution: acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1,
    preselection_access_log: AccessEventLogV1,
    shared_resource_cap_source: DirectFallbackSharedResourceCapSourceV6,
    actual_hints: Mapping[str, int] | None = None,
) -> ConstructionK7DirectFallbackRouteFreezeV6:
    if type(preparation) is not DirectFallbackRoutePreparationV6:
        _fail("route freeze requires its typed V6 preparation")
    _validate_preparation(preparation)
    _validate_source_preexecution(
        source_preexecution,
        durable_proof_bytes=preparation.durable_proof_bytes,
        current_identity=preparation.current_identity,
    )
    if source_preexecution is not preparation.source_preexecution:
        _fail("route freeze source differs from the prepared typed H1 authority")
    if actual_hints is not None:
        _fail("post-run actual hints cannot enter preexecution upper construction")
    if type(shared_resource_cap_source) is not DirectFallbackSharedResourceCapSourceV6:
        _fail("shared-resource caps require the issuer-owned typed source")
    if (
        shared_resource_cap_source.to_document()
        != freeze_direct_fallback_shared_resource_cap_source_v6().to_document()
    ):
        _fail("shared-resource cap source is fake or stale")
    barrier = _replay_preselection_log(preparation, preselection_access_log)
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = _validated_comparison_profile(registry)
    shared_limits = tuple(
        (row.path, row.value) for row in shared_resource_cap_source.rows
    )
    cap = DirectFallbackCapProfileV6(
        preparation.route_context.route_decision_context_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        source_preexecution.candidate_id,
        source_preexecution.cap_profile.ground_fallback_cap_profile_id,
        shared_resource_cap_source.cap_source_id,
        OWNER_EXACT_UPPERS,
        shared_limits,
    )
    cardinality = DirectFallbackCardinalityEvidenceV6(
        preparation.route_context.route_decision_context_id,
        preparation.decision_point.decision_point_id,
        cap.cap_profile_id,
        source_preexecution.candidate_id,
        source_preexecution.cardinality.cardinality_evidence_id,
        OWNER_EXACT_UPPERS,
    )
    terms = _formula_terms()
    formula = DirectFallbackRouteFormulaV6(
        preparation.route_context.route_decision_context_id,
        preparation.decision_point.decision_point_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        cap.cap_profile_id,
        cardinality.cardinality_evidence_id,
        terms,
    )
    leaf = _leaf_uppers(terms)
    axes = _comparison_uppers(leaf)
    upper = DirectFallbackRouteUpperV6(
        preparation.route_context,
        preparation.decision_point.decision_point_id,
        stage.stage_profile_id,
        cap.cap_profile_id,
        cardinality.cardinality_evidence_id,
        formula.formula_id,
        leaf,
        axes,
    )
    decision = DirectFallbackRouteDecisionV6(
        preparation.route_context.route_decision_context_id,
        preparation.decision_point.decision_point_id,
        barrier.barrier_id,
        upper.route_upper_id,
        len(preselection_access_log.events),
    )
    return ConstructionK7DirectFallbackRouteFreezeV6(
        _BUNDLE_ISSUER,
        preparation,
        preselection_access_log,
        shared_resource_cap_source,
        barrier,
        cap,
        cardinality,
        formula,
        upper,
        decision,
    )


def verify_construction_k7_direct_fallback_route_upper_v6(
    raw: bytes,
    *,
    expected_source_preexecution: acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1,
    expected_durable_proof_bytes: bytes,
    expected_current_identity: acquisition_v1.CanonicalFallbackCurrentIdentityV1,
    expected_preselection_access_log: AccessEventLogV1,
) -> ConstructionK7DirectFallbackRouteFreezeV6:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackRouteUpperV6Error(
            "route-freeze bytes are not canonical"
        ) from error
    if type(document) is not dict:
        _fail("route-freeze document must be one canonical object")
    preparation = prepare_construction_k7_direct_fallback_route_upper_v6(
        expected_source_preexecution,
        durable_proof_bytes=expected_durable_proof_bytes,
        current_identity=expected_current_identity,
    )
    result = freeze_construction_k7_direct_fallback_route_upper_v6(
        preparation=preparation,
        source_preexecution=expected_source_preexecution,
        preselection_access_log=expected_preselection_access_log,
        shared_resource_cap_source=freeze_direct_fallback_shared_resource_cap_source_v6(),
    )
    if document != result.to_document():
        _fail("route-freeze document differs from independent V6 replay")
    return result


__all__ = [
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "CapEnforcementStatusV6",
    "ConstructionK7DirectFallbackRouteFreezeV6",
    "ConstructionK7DirectFallbackRouteUpperV6Error",
    "DirectFallbackCapProfileV6",
    "DirectFallbackCardinalityEvidenceV6",
    "DirectFallbackLeafUpperTermV6",
    "DirectFallbackPreexecutionBarrierV6",
    "DirectFallbackRouteDecisionV6",
    "DirectFallbackRouteFormulaV6",
    "DirectFallbackRoutePreparationV6",
    "DirectFallbackRouteUpperV6",
    "DirectFallbackSharedResourceCapSourceV6",
    "EXPECTED_OPERATIONAL_PATH_COUNT",
    "EXPECTED_OWNER_EXACT_COUNT",
    "EXPECTED_SHARED_RESOURCE_CAP_COUNT",
    "EXPECTED_STAGE_FORBIDDEN_ZERO_COUNT",
    "LeafUpperSourceV6",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OWNER_EXACT_UPPERS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "SharedAdmissionCapRowV6",
    "UPPER_KIND",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "freeze_construction_k7_direct_fallback_route_upper_v6",
    "freeze_direct_fallback_shared_resource_cap_source_v6",
    "prepare_construction_k7_direct_fallback_route_upper_v6",
    "verify_construction_k7_direct_fallback_route_upper_v6",
]
