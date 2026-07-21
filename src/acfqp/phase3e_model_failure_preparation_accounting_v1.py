"""Native accounting for the non-hash portion of model-failure preparation.

The H2 consumer performs route-estimation work after its failed abstract prefix
and through raw marginal-route decision construction, before semantic route
verification.  This module records that work as an ordered event trace and
reducer-aware post-core WorkVector.

The decision point must continue to bind the already-observed failed-prefix
core.  Several preparation evidence IDs do not exist until after that point is
constructed, so backfilling their aggregate ID into ``DecisionPointV1`` would
create an identity cycle (or require unobserved, predeclared counts).  This V1
therefore retains the replayed preparation as a separate post-decision-point,
pre-semantic-verification component.  It is not silently passed off as the
runner's decision-point-bound common core.

Content-ID/hash work and accounting materialization are deliberately outside
the trace.  Charging either while its own trace/WorkVector identity is being
constructed is self-referential unless the project adopts a separate scoped
hash observer with a precommitted closure rule.  The exclusion is explicit,
immutable, and tested; the global hash/accounting blocker therefore remains.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRegistryV1,
    ReducerEnum,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    RecordedWorkV1,
    derive_recorded_work_v1,
    verify_recorded_work_v1,
)
from acfqp.phase3e_ids import (
    MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN,
    MODEL_FAILURE_PREPARATION_TRACE_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)


PREPARATION_RECORDER_ID = "phase3e-model-failure-preparation-v1"
PREPARATION_AGGREGATE_RECORDER_ID = (
    "phase3e-model-failure-preparation-aggregate-v1"
)
PREPARATION_OCCURRENCE_CHARGE_STATUS = (
    "RETAINED_POST_CORE_NOT_YET_OCCURRENCE_CHARGED"
)
PREPARATION_EXCLUSIONS = (
    "ABSTRACT_AUDIT_REPLAY_ACCOUNTED_ONLY_BY_PRIOR_TWO_STAGE_SUFFIX",
    "ACCOUNTING_MATERIALIZATION_AND_SEALING_SELF_REFERENCE",
    "CONTENT_ID_HASH_INVOCATIONS_REQUIRE_SCOPED_OBSERVER",
    "GROUND_HANDOFF_CONSTRUCTION_OUTSIDE_PREPARATION_SCOPE",
)


class Phase3EModelFailurePreparationAccountingV1Error(ValueError):
    """Preparation events, native work, or reducer replay are inconsistent."""


class PreparationEventKind(str, Enum):
    CAUSAL_CANDIDATE_EVALUATION = "CAUSAL_CANDIDATE_EVALUATION"
    PROTOCOL_CHECK = "PROTOCOL_CHECK"
    INTEGRITY_CHECK = "INTEGRITY_CHECK"
    CAP_CHECK = "CAP_CHECK"


_COUNTER_BY_KIND = {
    PreparationEventKind.CAUSAL_CANDIDATE_EVALUATION: (
        "local.causal_candidate_evaluations"
    ),
    PreparationEventKind.PROTOCOL_CHECK: "common.protocol_checks",
    PreparationEventKind.INTEGRITY_CHECK: "common.integrity_checks",
    PreparationEventKind.CAP_CHECK: "control.cap_checks",
}


# This is the exact order of the boundary-level operations performed by
# ``prepare_phase3e_from_model_failure_v1``.  A helper invocation is one
# registered operation; we do not pretend that every private assertion inside
# that helper is a separately observable native event.  Causal candidate
# evaluations are the sole variable-length block and are emitted individually.
_PRE_CAUSAL_SIGNATURE: tuple[tuple[PreparationEventKind, str], ...] = (
    (PreparationEventKind.PROTOCOL_CHECK, "official-accounting-profiles-validated"),
    (PreparationEventKind.PROTOCOL_CHECK, "failed-prefix-authority-validated"),
    (PreparationEventKind.PROTOCOL_CHECK, "ground-binding-authority-validated"),
    (PreparationEventKind.PROTOCOL_CHECK, "runtime-input-types-validated"),
    (PreparationEventKind.INTEGRITY_CHECK, "runtime-manifest-roundtrip-validated"),
    (PreparationEventKind.INTEGRITY_CHECK, "runtime-cardinality-roundtrip-validated"),
    (
        PreparationEventKind.INTEGRITY_CHECK,
        "runtime-manifest-cardinality-binding-validated",
    ),
    (PreparationEventKind.PROTOCOL_CHECK, "failed-query-chain-validated"),
    (
        PreparationEventKind.PROTOCOL_CHECK,
        "prepared-estimate-derived-from-failed-authority",
    ),
    (
        PreparationEventKind.PROTOCOL_CHECK,
        "verified-model-estimate-binding-replayed",
    ),
    (PreparationEventKind.PROTOCOL_CHECK, "route-cap-profile-types-validated"),
    (PreparationEventKind.PROTOCOL_CHECK, "protocol-step-order-validated"),
    (PreparationEventKind.PROTOCOL_CHECK, "causal-frontier-derived"),
)

_POST_CAUSAL_SIGNATURE: tuple[tuple[PreparationEventKind, str], ...] = (
    (PreparationEventKind.CAP_CHECK, "causal-evaluation-cap-checked"),
    (PreparationEventKind.PROTOCOL_CHECK, "decision-point-transaction-bound"),
    (PreparationEventKind.PROTOCOL_CHECK, "local-cardinality-source-derived"),
    (PreparationEventKind.CAP_CHECK, "local-cardinality-bound-cap-checked"),
    (PreparationEventKind.CAP_CHECK, "local-cardinality-evidence-cap-checked"),
    (PreparationEventKind.PROTOCOL_CHECK, "local-upper-formula-bound"),
    (PreparationEventKind.PROTOCOL_CHECK, "local-upper-derived"),
    (PreparationEventKind.PROTOCOL_CHECK, "fallback-cardinality-source-derived"),
    (PreparationEventKind.CAP_CHECK, "fallback-cardinality-bound-cap-checked"),
    (
        PreparationEventKind.CAP_CHECK,
        "fallback-cardinality-evidence-cap-checked",
    ),
    (PreparationEventKind.PROTOCOL_CHECK, "fallback-upper-formula-bound"),
    (PreparationEventKind.PROTOCOL_CHECK, "fallback-upper-derived"),
    (PreparationEventKind.PROTOCOL_CHECK, "marginal-route-decision-derived"),
)


def expected_preparation_event_signature_v1(
    causal_candidate_count: int,
) -> tuple[tuple[PreparationEventKind, str], ...]:
    """Return the immutable event contract for one H2 preparation."""

    if type(causal_candidate_count) is not int or causal_candidate_count < 0:
        raise Phase3EModelFailurePreparationAccountingV1Error(
            "causal candidate count must be nonnegative"
        )
    causal = tuple(
        (
            PreparationEventKind.CAUSAL_CANDIDATE_EVALUATION,
            f"causal-candidate-{index:04d}",
        )
        for index in range(1, causal_candidate_count + 1)
    )
    return _PRE_CAUSAL_SIGNATURE + causal + _POST_CAUSAL_SIGNATURE


@dataclass(frozen=True, slots=True)
class ModelFailurePreparationEventV1:
    sequence_number: int
    event_kind: PreparationEventKind
    operation_id: str
    evidence_id: str

    def __post_init__(self) -> None:
        if type(self.sequence_number) is not int or self.sequence_number <= 0:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation event sequence must be positive"
            )
        try:
            object.__setattr__(
                self, "event_kind", PreparationEventKind(self.event_kind)
            )
            parse_content_id(self.evidence_id)
        except (TypeError, ValueError) as error:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation event kind/evidence is invalid"
            ) from error
        if type(self.operation_id) is not str or not self.operation_id:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation operation_id must be nonempty"
            )

    @property
    def counter_path(self) -> str:
        return _COUNTER_BY_KIND[self.event_kind]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_number": self.sequence_number,
            "event_kind": self.event_kind.value,
            "operation_id": self.operation_id,
            "evidence_id": self.evidence_id,
            "counter_path": self.counter_path,
        }

    @classmethod
    def from_dict(
        cls, document: dict[str, Any]
    ) -> "ModelFailurePreparationEventV1":
        require_exact_fields(
            document,
            {
                "sequence_number",
                "event_kind",
                "operation_id",
                "evidence_id",
                "counter_path",
            },
            context="model-failure preparation event",
        )
        result = cls(
            document["sequence_number"],
            document["event_kind"],
            document["operation_id"],
            document["evidence_id"],
        )
        if document["counter_path"] != result.counter_path:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation event counter path differs from its event kind"
            )
        return result


@dataclass(frozen=True, slots=True)
class ModelFailurePreparationTraceV1:
    route_decision_context_id: str
    route_attempt_id: str
    source_prefix_work_vector_id: str
    events: tuple[ModelFailurePreparationEventV1, ...]
    causal_evidence_id: str
    causal_candidate_count: int
    excluded_work: tuple[str, ...] = PREPARATION_EXCLUSIONS
    post_decision_point_component: bool = True
    trace_sealed_before_semantic_route_verification: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.route_decision_context_id,
            self.route_attempt_id,
            self.source_prefix_work_vector_id,
            self.causal_evidence_id,
        ):
            try:
                parse_content_id(value)
            except ValueError as error:
                raise Phase3EModelFailurePreparationAccountingV1Error(
                    "preparation trace identity is invalid"
                ) from error
        if type(self.events) is not tuple or not self.events:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation trace requires immutable events"
            )
        if not all(type(row) is ModelFailurePreparationEventV1 for row in self.events):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation trace contains an untyped event"
            )
        if tuple(row.sequence_number for row in self.events) != tuple(
            range(1, len(self.events) + 1)
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation event sequence is missing, duplicated, or reordered"
            )
        if len({row.operation_id for row in self.events}) != len(self.events):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation operation IDs must be unique"
            )
        signature = tuple(
            (row.event_kind, row.operation_id) for row in self.events
        )
        if signature != expected_preparation_event_signature_v1(
            self.causal_candidate_count
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation event contract is missing, duplicated, or reordered"
            )
        causal = tuple(
            row
            for row in self.events
            if row.event_kind
            is PreparationEventKind.CAUSAL_CANDIDATE_EVALUATION
        )
        if (
            type(self.causal_candidate_count) is not int
            or self.causal_candidate_count < 0
            or len(causal) != self.causal_candidate_count
            or any(row.evidence_id != self.causal_evidence_id for row in causal)
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation causal events differ from frozen causal evidence"
            )
        if (
            self.excluded_work != PREPARATION_EXCLUSIONS
            or self.post_decision_point_component is not True
            or self.trace_sealed_before_semantic_route_verification is not True
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation trace cannot hide exclusions or move its freeze boundary"
            )
        if any(
            row.counter_path == "common.hash_invocations" for row in self.events
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "self-referential content-ID hashes cannot enter this trace"
            )

    def count(self, path: str) -> int:
        if path not in set(_COUNTER_BY_KIND.values()):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation trace queried an unregistered path"
            )
        return sum(row.counter_path == path for row in self.events)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.model_failure_preparation_trace.v1",
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_attempt_id": self.route_attempt_id,
            "source_prefix_work_vector_id": self.source_prefix_work_vector_id,
            "events": [row.to_dict() for row in self.events],
            "causal_evidence_id": self.causal_evidence_id,
            "causal_candidate_count": self.causal_candidate_count,
            "excluded_work": list(self.excluded_work),
            "post_decision_point_component": True,
            "trace_sealed_before_semantic_route_verification": True,
        }

    @property
    def model_failure_preparation_trace_id(self) -> str:
        return content_id(MODEL_FAILURE_PREPARATION_TRACE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "model_failure_preparation_trace_id": (
                self.model_failure_preparation_trace_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: dict[str, Any]
    ) -> "ModelFailurePreparationTraceV1":
        require_exact_fields(
            document,
            {
                "schema",
                "RouteDecisionContext_id",
                "route_attempt_id",
                "source_prefix_work_vector_id",
                "events",
                "causal_evidence_id",
                "causal_candidate_count",
                "excluded_work",
                "post_decision_point_component",
                "trace_sealed_before_semantic_route_verification",
                "model_failure_preparation_trace_id",
            },
            context="model-failure preparation trace",
        )
        if (
            document["schema"] != "acfqp.model_failure_preparation_trace.v1"
            or type(document["events"]) is not list
            or type(document["excluded_work"]) is not list
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation trace transport schema mismatch"
            )
        result = cls(
            document["RouteDecisionContext_id"],
            document["route_attempt_id"],
            document["source_prefix_work_vector_id"],
            tuple(
                ModelFailurePreparationEventV1.from_dict(row)
                for row in document["events"]
            ),
            document["causal_evidence_id"],
            document["causal_candidate_count"],
            tuple(document["excluded_work"]),
            document["post_decision_point_component"],
            document["trace_sealed_before_semantic_route_verification"],
        )
        if (
            document["model_failure_preparation_trace_id"]
            != result.model_failure_preparation_trace_id
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation trace content ID mismatch"
            )
        return result


class ModelFailurePreparationEventRecorderV1:
    """Append-only stage recorder used directly at preparation operations."""

    def __init__(
        self,
        *,
        route_decision_context_id: str,
        route_attempt_id: str,
        source_prefix_work_vector_id: str,
    ) -> None:
        for value in (
            route_decision_context_id,
            route_attempt_id,
            source_prefix_work_vector_id,
        ):
            parse_content_id(value)
        self.route_decision_context_id = route_decision_context_id
        self.route_attempt_id = route_attempt_id
        self.source_prefix_work_vector_id = source_prefix_work_vector_id
        self._events: list[ModelFailurePreparationEventV1] = []
        self._sealed = False

    def observe(
        self,
        kind: PreparationEventKind,
        operation_id: str,
        evidence_id: str,
    ) -> None:
        if self._sealed:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation recorder is already sealed"
            )
        event = ModelFailurePreparationEventV1(
            len(self._events) + 1, kind, operation_id, evidence_id
        )
        if any(row.operation_id == event.operation_id for row in self._events):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation recorder observed a duplicate operation"
            )
        self._events.append(event)

    def observe_causal_candidates(
        self,
        *,
        causal_evidence_id: str,
        evaluated_candidate_count: int,
    ) -> None:
        if type(evaluated_candidate_count) is not int or evaluated_candidate_count < 0:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "causal candidate count must be nonnegative"
            )
        for index in range(1, evaluated_candidate_count + 1):
            self.observe(
                PreparationEventKind.CAUSAL_CANDIDATE_EVALUATION,
                f"causal-candidate-{index:04d}",
                causal_evidence_id,
            )

    def seal(
        self,
        *,
        causal_evidence_id: str,
        causal_candidate_count: int,
    ) -> ModelFailurePreparationTraceV1:
        if self._sealed:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation recorder is already sealed"
            )
        self._sealed = True
        return ModelFailurePreparationTraceV1(
            self.route_decision_context_id,
            self.route_attempt_id,
            self.source_prefix_work_vector_id,
            tuple(self._events),
            causal_evidence_id,
            causal_candidate_count,
        )


def _profiles_v1(
    registry: CounterRegistryV1 | None,
    profile: ComparisonProfileV1 | None,
) -> tuple[CounterRegistryV1, ComparisonProfileV1]:
    trusted_registry = registry or official_counter_registry_v1()
    trusted_profile = profile or official_comparison_profile_v1(
        trusted_registry
    )
    trusted_registry.validate_official_catalogue()
    trusted_profile.validate(trusted_registry)
    if (
        trusted_registry != official_counter_registry_v1()
        or trusted_profile != official_comparison_profile_v1(trusted_registry)
    ):
        raise Phase3EModelFailurePreparationAccountingV1Error(
            "preparation accounting requires exact official profiles"
        )
    return trusted_registry, trusted_profile


def _record_trace_v1(
    trace: ModelFailurePreparationTraceV1,
    *,
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
) -> RecordedWorkV1:
    recorder = NativeCounterRecorderV1(
        subject_id=trace.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id=PREPARATION_RECORDER_ID,
    )
    for event in trace.events:
        recorder.add(event.counter_path)
    work = recorder.seal()
    for path in _COUNTER_BY_KIND.values():
        if work.work_vector.value(path) != trace.count(path):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation native work differs from its event trace"
            )
    if work.work_vector.value("common.hash_invocations") != 0:
        raise Phase3EModelFailurePreparationAccountingV1Error(
            "preparation work violated the hash exclusion boundary"
        )
    return work


def _aggregate_prefix_v1(
    source_prefix: RecordedWorkV1,
    preparation_work: RecordedWorkV1,
    *,
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
) -> RecordedWorkV1:
    try:
        verify_recorded_work_v1(
            source_prefix,
            expected_scope=ActualWorkScope.COMMON_PREFIX,
            registry=registry,
            comparison_profile=profile,
        )
        verify_recorded_work_v1(
            preparation_work,
            expected_scope=ActualWorkScope.COMMON_PREFIX,
            registry=registry,
            comparison_profile=profile,
        )
    except ValueError as error:
        raise Phase3EModelFailurePreparationAccountingV1Error(
            f"preparation source work does not replay: {error}"
        ) from error
    left = source_prefix.work_vector
    right = preparation_work.work_vector
    if (
        left.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or right.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or left.subject_id != right.subject_id
    ):
        raise Phase3EModelFailurePreparationAccountingV1Error(
            "preparation aggregation requires one failed-prefix subject"
        )
    values: dict[str, int] = {}
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        values[path] = (
            left.value(path) + right.value(path)
            if leaf.reducer is ReducerEnum.SUM
            else max(left.value(path), right.value(path))
        )
    vector = registry.materialize(
        subject_id=left.subject_id,
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        records=explicit_records_v1(
            registry,
            values,
            recorder_id=PREPARATION_AGGREGATE_RECORDER_ID,
        ),
    )
    return derive_recorded_work_v1(
        vector,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
    )


@dataclass(frozen=True, slots=True)
class ModelFailurePreparationAccountingV1:
    trace: ModelFailurePreparationTraceV1
    source_prefix: RecordedWorkV1
    preparation_work: RecordedWorkV1
    aggregate_work: RecordedWorkV1
    occurrence_charge_status: str = PREPARATION_OCCURRENCE_CHARGE_STATUS

    def __post_init__(self) -> None:
        if (
            type(self.trace) is not ModelFailurePreparationTraceV1
            or type(self.source_prefix) is not RecordedWorkV1
            or type(self.preparation_work) is not RecordedWorkV1
            or type(self.aggregate_work) is not RecordedWorkV1
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation accounting contains an untyped member"
            )
        if (
            self.trace.source_prefix_work_vector_id
            != self.source_prefix.work_vector.work_vector_id
            or self.trace.route_attempt_id
            != self.source_prefix.work_vector.subject_id
        ):
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation trace differs from its source prefix"
            )
        if self.occurrence_charge_status != PREPARATION_OCCURRENCE_CHARGE_STATUS:
            raise Phase3EModelFailurePreparationAccountingV1Error(
                "preparation accounting cannot claim occurrence charging"
            )

    @property
    def incremental_work(self) -> RecordedWorkV1:
        """Return only newly observed work, safe to add without prefix duplication."""

        return self.preparation_work

    @property
    def model_failure_preparation_accounting_id(self) -> str:
        return content_id(
            MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN,
            {
                "schema": "acfqp.model_failure_preparation_accounting.v1",
                "trace_id": self.trace.model_failure_preparation_trace_id,
                "source_prefix_work_vector_id": (
                    self.source_prefix.work_vector.work_vector_id
                ),
                "preparation_work_vector_id": (
                    self.preparation_work.work_vector.work_vector_id
                ),
                "aggregate_work_vector_id": (
                    self.aggregate_work.work_vector.work_vector_id
                ),
                "excluded_work": list(self.trace.excluded_work),
                "occurrence_charge_status": self.occurrence_charge_status,
            },
        )

    def metadata(self) -> dict[str, Any]:
        """Serialize only identities; native WorkVectors remain separate roles."""

        payload = {
            "schema": "acfqp.model_failure_preparation_accounting.v1",
            "trace_id": self.trace.model_failure_preparation_trace_id,
            "source_prefix_work_vector_id": (
                self.source_prefix.work_vector.work_vector_id
            ),
            "preparation_work_vector_id": (
                self.preparation_work.work_vector.work_vector_id
            ),
            "aggregate_work_vector_id": (
                self.aggregate_work.work_vector.work_vector_id
            ),
            "excluded_work": list(self.trace.excluded_work),
            "occurrence_charge_status": self.occurrence_charge_status,
        }
        return {
            **payload,
            "model_failure_preparation_accounting_id": content_id(
                MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN, payload
            ),
        }


def derive_model_failure_preparation_accounting_v1(
    *,
    trace: ModelFailurePreparationTraceV1,
    source_prefix: RecordedWorkV1,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> ModelFailurePreparationAccountingV1:
    trusted_registry, trusted_profile = _profiles_v1(
        registry, comparison_profile
    )
    preparation = _record_trace_v1(
        trace, registry=trusted_registry, profile=trusted_profile
    )
    aggregate = _aggregate_prefix_v1(
        source_prefix,
        preparation,
        registry=trusted_registry,
        profile=trusted_profile,
    )
    result = ModelFailurePreparationAccountingV1(
        trace, source_prefix, preparation, aggregate
    )
    replayed_preparation = _record_trace_v1(
        trace, registry=trusted_registry, profile=trusted_profile
    )
    replayed_aggregate = _aggregate_prefix_v1(
        source_prefix,
        replayed_preparation,
        registry=trusted_registry,
        profile=trusted_profile,
    )
    if (
        replayed_preparation != result.preparation_work
        or replayed_aggregate != result.aggregate_work
    ):
        raise Phase3EModelFailurePreparationAccountingV1Error(
            "preparation accounting differs from deterministic replay"
        )
    return result


def verify_model_failure_preparation_accounting_v1(
    accounting: ModelFailurePreparationAccountingV1,
    *,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> ModelFailurePreparationAccountingV1:
    if type(accounting) is not ModelFailurePreparationAccountingV1:
        raise Phase3EModelFailurePreparationAccountingV1Error(
            "preparation verification requires exact typed accounting"
        )
    replayed = derive_model_failure_preparation_accounting_v1(
        trace=accounting.trace,
        source_prefix=accounting.source_prefix,
        registry=registry,
        comparison_profile=comparison_profile,
    )
    if replayed != accounting:
        raise Phase3EModelFailurePreparationAccountingV1Error(
            "preparation accounting differs from exact trace replay"
        )
    return accounting


__all__ = [
    "MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN",
    "MODEL_FAILURE_PREPARATION_TRACE_DOMAIN",
    "ModelFailurePreparationAccountingV1",
    "ModelFailurePreparationEventRecorderV1",
    "ModelFailurePreparationEventV1",
    "ModelFailurePreparationTraceV1",
    "PREPARATION_EXCLUSIONS",
    "PREPARATION_OCCURRENCE_CHARGE_STATUS",
    "Phase3EModelFailurePreparationAccountingV1Error",
    "PreparationEventKind",
    "derive_model_failure_preparation_accounting_v1",
    "expected_preparation_event_signature_v1",
    "verify_model_failure_preparation_accounting_v1",
]
