"""Reducer-aware accounting for a complete Phase-3E logical occurrence.

The historical :class:`~acfqp.actual_accounting_v1.OccurrenceWorkSumV1`
intentionally models one common prefix, one failed local attempt, and one
fallback.  Phase 3E permits two local transactions and requires a fresh
decision point before a fallback that follows either failure.  This module
adds that more general accounting object without changing the historical
schema.

An occurrence is represented as an ordered sequence of decision pairs::

    COMMON_PREFIX, (LOCAL_TRANSACTION | DIRECT_FALLBACK)

There may be at most two local pairs and at most one fallback pair.  A
fallback, when present, is final.  A fallback decision may either be a fresh
fallback-only point (typed-null local fields) or a marginal local/fallback
point whose selector chose fallback before the candidate local transaction
executed.  In the latter case its decision point retains the candidate index,
frontier, and causal identities, while the fallback component itself retains
a typed-null transaction: estimating transaction 2 must never fabricate or
charge an executed transaction 2.  Each component accepts only native
``RecordedWorkV1`` evidence, or a runner marginal aggregate accompanied by
both native source bundles from which its ``MarginalWorkAggregationProofV1``
was derived.  A route component must include an ordered execution and
verification pair, or that complete replayable aggregate; execution-only work
is never a complete occurrence charge.  It retains every WorkVector,
ComparisonVector,
ActualProjectionProof, native-zero, reconciliation, and marginal-aggregation
identity.  Reducers are replayed twice: first within a component (for an
execution plus its verification suffix), then across the occurrence.
Additive resources use ``sum`` and capacity resources use ``max``.

The serialized aggregate is not self-authoritative.  Verification requires
the original typed runtime evidence and reconstructs every component
reference and total.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence, TypeAlias

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    ComparisonVectorV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProfileV1,
    ActualProjectionProofV1,
    ActualWorkScope,
)
from acfqp.marginal_accounting_v1 import (
    AggregatedMarginalWorkV1,
    MarginalAccountingV1Error,
    MarginalWorkAggregationProofV1,
    verify_marginal_work_aggregate_v1,
)
from acfqp.native_recorder_v1 import RecordedWorkV1, verify_recorded_work_v1
from acfqp.phase3e_two_stage_accounting_v1 import (
    TwoStageAccountingClosureV1,
    TwoStageAccountingV1Error,
    _materialize_values,
    verify_two_stage_accounting_v1,
)
from acfqp.semantic_verification_v1 import (
    SemanticVerificationResultV1,
    require_semantic_verification_result_v1,
)
from acfqp.phase3e_ids import (
    OCCURRENCE_PARTIAL_COMMON_ACCOUNTING_DOMAIN,
    OCCURRENCE_WORK_AGGREGATE_DOMAIN,
    OCCURRENCE_WORK_COMPONENT_REF_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteDecisionContextV1,
    TransactionV1,
    TypedNotApplicable,
)


SCHEMA_VERSION = "1.0.0"
MAX_LOCAL_TRANSACTIONS = 2


class Phase3EOccurrenceAccountingV1Error(ValueError):
    """An occurrence component, identity chain, or reducer replay is invalid."""


class OccurrenceWorkComponentKind(str, Enum):
    COMMON_PREFIX = "COMMON_PREFIX"
    LOCAL_TRANSACTION = "LOCAL_TRANSACTION"
    DIRECT_FALLBACK = "DIRECT_FALLBACK"


class OccurrenceRawEvidenceKind(str, Enum):
    RECORDED_WORK = "RECORDED_WORK"
    AGGREGATED_MARGINAL_WORK = "AGGREGATED_MARGINAL_WORK"
    TWO_STAGE_ACCOUNTED_COMMON = "TWO_STAGE_ACCOUNTED_COMMON"
    PARTIAL_ACCOUNTED_COMMON = "PARTIAL_ACCOUNTED_COMMON"


@dataclass(frozen=True, slots=True)
class RunnerMarginalWorkEvidenceV1:
    """A runner aggregate plus both native bundles that authorize it."""

    aggregate: AggregatedMarginalWorkV1
    execution: RecordedWorkV1
    verification_suffix: RecordedWorkV1

    def __post_init__(self) -> None:
        if not isinstance(self.aggregate, AggregatedMarginalWorkV1):
            raise Phase3EOccurrenceAccountingV1Error(
                "runner marginal evidence has the wrong aggregate type"
            )
        if not isinstance(
            self.aggregate.aggregation_proof, MarginalWorkAggregationProofV1
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "runner marginal evidence lacks MarginalWorkAggregationProofV1"
            )
        if not isinstance(self.execution, RecordedWorkV1) or not isinstance(
            self.verification_suffix, RecordedWorkV1
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "runner marginal evidence requires both native source bundles"
            )


@dataclass(frozen=True, slots=True)
class RunnerCommonAccountingEvidenceV1:
    """A common core plus the exact two-stage verification closure it paid."""

    core: RecordedWorkV1
    closure: TwoStageAccountingClosureV1
    semantic_results: tuple[SemanticVerificationResultV1, ...]
    nonsemantic_records: tuple[CounterRecordV1, ...]
    route_context: RouteDecisionContextV1

    def __post_init__(self) -> None:
        if not isinstance(self.core, RecordedWorkV1) or not isinstance(
            self.closure, TwoStageAccountingClosureV1
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "common accounting evidence requires typed core and closure"
            )
        if type(self.semantic_results) is not tuple or not all(
            isinstance(row, SemanticVerificationResultV1)
            for row in self.semantic_results
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "common semantic replay inputs must be an immutable typed tuple"
            )
        if type(self.nonsemantic_records) is not tuple or not all(
            isinstance(row, CounterRecordV1)
            for row in self.nonsemantic_records
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "common nonsemantic replay inputs must be an immutable typed tuple"
            )
        if not isinstance(self.route_context, RouteDecisionContextV1):
            raise Phase3EOccurrenceAccountingV1Error(
                "common accounting evidence requires a typed route context"
            )


@dataclass(frozen=True, slots=True)
class RunnerPartialCommonAccountingEvidenceV1:
    """Fail-closed common core plus every already observed verifier charge.

    This is not a successful two-stage receipt.  It exists only so a rejected
    continuation package cannot make operational verifier work disappear.
    Replay revalidates the exact authority contexts and CounterRecords, then
    deterministically reconstructs both the suffix and reducer-aware sum.
    """

    core: RecordedWorkV1
    semantic_results: tuple[SemanticVerificationResultV1, ...]
    nonsemantic_records: tuple[CounterRecordV1, ...]
    route_context: RouteDecisionContextV1
    decision_point_id: str
    verification_suffix: RecordedWorkV1
    aggregate_work: RecordedWorkV1

    def __post_init__(self) -> None:
        if type(self.core) is not RecordedWorkV1:
            raise Phase3EOccurrenceAccountingV1Error(
                "partial common accounting requires an exact RecordedWorkV1 core"
            )
        if type(self.semantic_results) is not tuple or not all(
            type(row) is SemanticVerificationResultV1
            for row in self.semantic_results
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "partial common semantic inputs must be exact immutable results"
            )
        if type(self.nonsemantic_records) is not tuple or not all(
            type(row) is CounterRecordV1 for row in self.nonsemantic_records
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "partial common nonsemantic inputs must be exact immutable records"
            )
        if type(self.route_context) is not RouteDecisionContextV1:
            raise Phase3EOccurrenceAccountingV1Error(
                "partial common accounting requires an exact route context"
            )
        _cid(self.decision_point_id, "decision_point_id")
        if type(self.verification_suffix) is not RecordedWorkV1 or type(
            self.aggregate_work
        ) is not RecordedWorkV1:
            raise Phase3EOccurrenceAccountingV1Error(
                "partial common accounting lacks its exact derived work"
            )

    @property
    def partial_common_accounting_id(self) -> str:
        return content_id(
            OCCURRENCE_PARTIAL_COMMON_ACCOUNTING_DOMAIN,
            {
                "schema": "acfqp.occurrence_partial_common_accounting.v1",
                "RouteDecisionContext_id": (
                    self.route_context.route_decision_context_id
                ),
                "decision_point_id": self.decision_point_id,
                "core_work_vector_id": self.core.work_vector.work_vector_id,
                "semantic_attestation_ids": [
                    row.attestation.verification_attestation_id
                    for row in self.semantic_results
                ],
                "nonsemantic_counter_record_ids": [
                    row.record_id for row in self.nonsemantic_records
                ],
                "verification_suffix_work_vector_id": (
                    self.verification_suffix.work_vector.work_vector_id
                ),
                "aggregate_work_vector_id": (
                    self.aggregate_work.work_vector.work_vector_id
                ),
            },
        )


def derive_runner_partial_common_accounting_v1(
    *,
    core: RecordedWorkV1,
    semantic_results: tuple[SemanticVerificationResultV1, ...],
    nonsemantic_records: tuple[CounterRecordV1, ...],
    route_context: RouteDecisionContextV1,
    decision_point_id: str,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> RunnerPartialCommonAccountingEvidenceV1:
    """Charge only exact, already observed operational continuation records."""

    try:
        verify_recorded_work_v1(
            core,
            expected_scope=ActualWorkScope.COMMON_PREFIX,
            registry=registry,
            comparison_profile=comparison_profile,
        )
        parse_content_id(decision_point_id)
    except ValueError as error:
        raise Phase3EOccurrenceAccountingV1Error(
            f"partial common core is invalid: {error}"
        ) from error
    if (
        type(route_context) is not RouteDecisionContextV1
        or route_context.counter_registry_id != registry.registry_id
        or route_context.comparison_profile_id
        != comparison_profile.comparison_profile_id
        or core.work_vector.subject_id != route_context.route_attempt_id
        or core.work_vector.route_kind
        is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        or core.actual_projection_proof.actual_projection_profile_id
        != actual_profile.actual_projection_profile_id
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "partial common core/context/profile chain is stale"
        )
    records: list[CounterRecordV1] = []
    if type(semantic_results) is not tuple:
        raise Phase3EOccurrenceAccountingV1Error(
            "partial semantic results must be an immutable tuple"
        )
    for result in semantic_results:
        if type(result) is not SemanticVerificationResultV1:
            raise Phase3EOccurrenceAccountingV1Error(
                "partial semantic charge lacks exact replay authority"
            )
        try:
            verified = require_semantic_verification_result_v1(
                result, result.role
            )
        except ValueError as error:
            raise Phase3EOccurrenceAccountingV1Error(
                f"partial semantic charge is unauthoritative: {error}"
            ) from error
        if (
            verified.binding.route_context != route_context
            or verified.binding.decision_point_id != decision_point_id
            or verified.binding.verification_lane is not LaneEnum.OPERATIONAL
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "partial semantic charge uses another context, point, or lane"
            )
        records.append(verified.verification_work_record)
    if type(nonsemantic_records) is not tuple or not all(
        type(row) is CounterRecordV1 for row in nonsemantic_records
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "partial nonsemantic charges must be exact CounterRecords"
        )
    records.extend(nonsemantic_records)
    if not records:
        raise Phase3EOccurrenceAccountingV1Error(
            "partial common accounting requires observed verifier work"
        )
    if len({row.record_id for row in records}) != len(records):
        raise Phase3EOccurrenceAccountingV1Error(
            "partial common accounting repeats a CounterRecord"
        )
    if {row.record_id for row in records} & {
        row.record_id for row in core.work_vector.records
    }:
        raise Phase3EOccurrenceAccountingV1Error(
            "partial common accounting recharges a core CounterRecord"
        )
    suffix_values = {path: 0 for path in registry.required_paths}
    for record in records:
        if record.counter_registry_id != registry.registry_id or (
            record.lane is not LaneEnum.OPERATIONAL
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "partial common record uses another registry or lane"
            )
        leaf = registry.by_path.get(record.path)
        if leaf is None:
            raise Phase3EOccurrenceAccountingV1Error(
                "partial common record uses an unknown path"
            )
        try:
            record.verify_against(leaf)
        except ValueError as error:
            raise Phase3EOccurrenceAccountingV1Error(
                f"partial common record is invalid: {error}"
            ) from error
        suffix_values[record.path] = (
            suffix_values[record.path] + record.value
            if leaf.reducer is ReducerEnum.SUM
            else max(suffix_values[record.path], record.value)
        )
    suffix = _materialize_values(
        values=suffix_values,
        subject_id=route_context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        recorder_id="phase3e-occurrence-partial-common-suffix-v1",
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    aggregate_values: dict[str, int] = {}
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        core_value = core.work_vector.value(path)
        suffix_value = suffix.work_vector.value(path)
        aggregate_values[path] = (
            core_value + suffix_value
            if leaf.reducer is ReducerEnum.SUM
            else max(core_value, suffix_value)
        )
    aggregate = _materialize_values(
        values=aggregate_values,
        subject_id=route_context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        recorder_id="phase3e-occurrence-partial-common-aggregate-v1",
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    return RunnerPartialCommonAccountingEvidenceV1(
        core,
        semantic_results,
        nonsemantic_records,
        route_context,
        decision_point_id,
        suffix,
        aggregate,
    )


OccurrenceRawEvidenceV1: TypeAlias = (
    RecordedWorkV1
    | RunnerMarginalWorkEvidenceV1
    | RunnerCommonAccountingEvidenceV1
    | RunnerPartialCommonAccountingEvidenceV1
)
ContentRefV1: TypeAlias = str | TypedNotApplicable
IndexRefV1: TypeAlias = int | TypedNotApplicable


_NO_TRANSACTION = "component is not transaction-owned"
_NO_TRANSACTION_INDEX = "component has no local transaction index"
_NO_NATIVE_ZERO = "derived aggregate has no direct native-zero proof"
_NO_RECONCILIATION = "derived aggregate has no direct reconciliation proof"
_NO_MARGINAL_AGGREGATION = "native work is not a marginal aggregate"


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3EOccurrenceAccountingV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise Phase3EOccurrenceAccountingV1Error(str(error)) from error


def _enum(value: Any, enum_type: type[Enum], field: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise Phase3EOccurrenceAccountingV1Error(
            f"invalid {field}: {value!r}"
        ) from error


def _typed_content_ref(value: Any, field: str) -> ContentRefV1:
    if isinstance(value, TypedNotApplicable):
        return value
    return _cid(value, field)


def _typed_index_ref(value: Any, field: str) -> IndexRefV1:
    if isinstance(value, TypedNotApplicable):
        return value
    if type(value) is not int or value not in {1, 2}:
        raise Phase3EOccurrenceAccountingV1Error(
            f"{field} must be transaction index 1 or 2"
        )
    return value


def _parse_content_ref(value: Any, field: str) -> ContentRefV1:
    if isinstance(value, Mapping):
        try:
            return TypedNotApplicable.from_dict(value)
        except ValueError as error:
            raise Phase3EOccurrenceAccountingV1Error(str(error)) from error
    return _typed_content_ref(value, field)


def _parse_index_ref(value: Any, field: str) -> IndexRefV1:
    if isinstance(value, Mapping):
        try:
            return TypedNotApplicable.from_dict(value)
        except ValueError as error:
            raise Phase3EOccurrenceAccountingV1Error(str(error)) from error
    return _typed_index_ref(value, field)


def _ref_payload(value: ContentRefV1 | IndexRefV1) -> Any:
    return value.to_dict() if isinstance(value, TypedNotApplicable) else value


def _axis_values(
    values: Sequence[tuple[str, int]], context: str
) -> tuple[tuple[str, int], ...]:
    result = tuple(values)
    if (
        tuple(sorted(result)) != result
        or len(dict(result)) != len(result)
        or tuple(axis for axis, _ in result) != SHARED_AXES
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            f"{context} must contain the exact sorted shared-axis set"
        )
    for axis, value in result:
        if type(value) is not int or value < 0:
            raise Phase3EOccurrenceAccountingV1Error(
                f"{context}.{axis} must be a nonnegative exact integer"
            )
    return result


def _axis_rows(values: Sequence[tuple[str, int]]) -> list[dict[str, Any]]:
    return [{"axis": axis, "value": value} for axis, value in values]


def _parse_axis_rows(value: Any, context: str) -> tuple[tuple[str, int], ...]:
    if type(value) is not list:
        raise Phase3EOccurrenceAccountingV1Error(f"{context} must be a list")
    rows: list[tuple[str, int]] = []
    for row in value:
        _fields(row, {"axis", "value"}, f"{context} row")
        rows.append((row["axis"], row["value"]))
    return _axis_values(rows, context)


def _reduce_axis_values(
    vectors: Sequence[Sequence[tuple[str, int]]],
    profile: ComparisonProfileV1,
) -> tuple[tuple[str, int], ...]:
    if not vectors:
        raise Phase3EOccurrenceAccountingV1Error(
            "reducer replay needs at least one comparison vector"
        )
    reducers = {axis.name: axis.reducer for axis in profile.axes}
    totals = {axis: 0 for axis in SHARED_AXES}
    for values in vectors:
        canonical = _axis_values(values, "comparison values")
        for axis, value in canonical:
            if reducers[axis] is ReducerEnum.SUM:
                totals[axis] += value
            else:
                totals[axis] = max(totals[axis], value)
    return tuple(sorted(totals.items()))


@dataclass(frozen=True, slots=True)
class OccurrenceNativeSourceRefV1:
    """Complete native provenance for one marginal-aggregate source."""

    work_scope: ActualWorkScope
    route_kind: RouteKindEnum
    subject_id: str
    work_vector_id: str
    comparison_vector_id: str
    actual_projection_proof_id: str
    native_zero_attestation_id: str
    reconciliation_proof_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "work_scope",
            _enum(self.work_scope, ActualWorkScope, "source work_scope"),
        )
        object.__setattr__(
            self,
            "route_kind",
            _enum(self.route_kind, RouteKindEnum, "source route_kind"),
        )
        if self.work_scope not in {
            ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
            ActualWorkScope.COMMON_PREFIX,
        }:
            raise Phase3EOccurrenceAccountingV1Error(
                "aggregate source must be common, execution, or verification work"
            )
        allowed_route_kinds = (
            {RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE}
            if self.work_scope is ActualWorkScope.COMMON_PREFIX
            else {RouteKindEnum.LOCAL_ATTEMPT, RouteKindEnum.DIRECT_FALLBACK}
        )
        if self.route_kind not in allowed_route_kinds:
            raise Phase3EOccurrenceAccountingV1Error(
                "aggregate source route kind differs from its work scope"
            )
        for field in (
            "subject_id",
            "work_vector_id",
            "comparison_vector_id",
            "actual_projection_proof_id",
            "native_zero_attestation_id",
            "reconciliation_proof_id",
        ):
            _cid(getattr(self, field), field)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_scope": self.work_scope.value,
            "route_kind": self.route_kind.value,
            "subject_id": self.subject_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "actual_projection_proof_id": self.actual_projection_proof_id,
            "native_zero_attestation_id": self.native_zero_attestation_id,
            "reconciliation_proof_id": self.reconciliation_proof_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "OccurrenceNativeSourceRefV1":
        expected = {
            "work_scope",
            "route_kind",
            "subject_id",
            "work_vector_id",
            "comparison_vector_id",
            "actual_projection_proof_id",
            "native_zero_attestation_id",
            "reconciliation_proof_id",
        }
        _fields(document, expected, "occurrence aggregate source reference")
        return cls(
            document["work_scope"],
            document["route_kind"],
            document["subject_id"],
            document["work_vector_id"],
            document["comparison_vector_id"],
            document["actual_projection_proof_id"],
            document["native_zero_attestation_id"],
            document["reconciliation_proof_id"],
        )


@dataclass(frozen=True, slots=True)
class OccurrenceRawWorkRefV1:
    """All immutable identities retained for one native accounting input."""

    evidence_kind: OccurrenceRawEvidenceKind
    work_scope: ActualWorkScope
    route_kind: RouteKindEnum
    subject_id: str
    work_vector_id: str
    comparison_vector_id: str
    actual_projection_proof_id: str
    native_zero_attestation_id: ContentRefV1
    reconciliation_proof_id: ContentRefV1
    marginal_work_aggregation_proof_id: ContentRefV1
    aggregation_source_refs: tuple[OccurrenceNativeSourceRefV1, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_kind",
            _enum(self.evidence_kind, OccurrenceRawEvidenceKind, "evidence_kind"),
        )
        object.__setattr__(
            self,
            "work_scope",
            _enum(self.work_scope, ActualWorkScope, "work_scope"),
        )
        object.__setattr__(
            self,
            "route_kind",
            _enum(self.route_kind, RouteKindEnum, "route_kind"),
        )
        for field in (
            "subject_id",
            "work_vector_id",
            "comparison_vector_id",
            "actual_projection_proof_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self,
            "native_zero_attestation_id",
            _typed_content_ref(
                self.native_zero_attestation_id, "native_zero_attestation_id"
            ),
        )
        object.__setattr__(
            self,
            "reconciliation_proof_id",
            _typed_content_ref(
                self.reconciliation_proof_id, "reconciliation_proof_id"
            ),
        )
        object.__setattr__(
            self,
            "marginal_work_aggregation_proof_id",
            _typed_content_ref(
                self.marginal_work_aggregation_proof_id,
                "marginal_work_aggregation_proof_id",
            ),
        )
        if type(self.aggregation_source_refs) is not tuple or not all(
            isinstance(row, OccurrenceNativeSourceRefV1)
            for row in self.aggregation_source_refs
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "aggregate source references must be an immutable typed tuple"
            )
        native_na = isinstance(self.native_zero_attestation_id, TypedNotApplicable)
        reconciliation_na = isinstance(
            self.reconciliation_proof_id, TypedNotApplicable
        )
        aggregate_na = isinstance(
            self.marginal_work_aggregation_proof_id, TypedNotApplicable
        )
        if self.evidence_kind is OccurrenceRawEvidenceKind.RECORDED_WORK:
            if native_na or reconciliation_na or not aggregate_na:
                raise Phase3EOccurrenceAccountingV1Error(
                    "RecordedWorkV1 references must retain both native proofs "
                    "and cannot claim a marginal aggregation proof"
                )
            if self.aggregation_source_refs:
                raise Phase3EOccurrenceAccountingV1Error(
                    "RecordedWorkV1 cannot claim aggregate source references"
                )
            if self.work_scope is ActualWorkScope.MARGINAL_ROUTE_AGGREGATE:
                raise Phase3EOccurrenceAccountingV1Error(
                    "MARGINAL_ROUTE_AGGREGATE requires complete source refs"
                )
        elif self.evidence_kind is OccurrenceRawEvidenceKind.AGGREGATED_MARGINAL_WORK:
            if not (native_na and reconciliation_na) or aggregate_na:
                raise Phase3EOccurrenceAccountingV1Error(
                    "derived aggregate must carry only its aggregation proof"
                )
            if self.work_scope is not ActualWorkScope.MARGINAL_ROUTE_AGGREGATE:
                raise Phase3EOccurrenceAccountingV1Error(
                    "aggregated marginal evidence has the wrong work scope"
                )
            if tuple(
                row.work_scope for row in self.aggregation_source_refs
            ) != (
                ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
                ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
            ):
                raise Phase3EOccurrenceAccountingV1Error(
                    "marginal aggregate must retain ordered execution and "
                    "verification source refs"
                )
            if any(
                row.route_kind is not self.route_kind
                or row.subject_id != self.subject_id
                for row in self.aggregation_source_refs
            ):
                raise Phase3EOccurrenceAccountingV1Error(
                    "marginal aggregate source context is stale or spliced"
                )
            for field in (
                "work_vector_id",
                "comparison_vector_id",
                "actual_projection_proof_id",
                "native_zero_attestation_id",
                "reconciliation_proof_id",
            ):
                if len(
                    {getattr(row, field) for row in self.aggregation_source_refs}
                ) != 2:
                    raise Phase3EOccurrenceAccountingV1Error(
                        f"marginal aggregate repeats source {field}"
                    )
        else:
            if not (native_na and reconciliation_na) or aggregate_na:
                raise Phase3EOccurrenceAccountingV1Error(
                    "two-stage common aggregate must retain its receipt only"
                )
            if self.work_scope is not ActualWorkScope.COMMON_PREFIX:
                raise Phase3EOccurrenceAccountingV1Error(
                    "two-stage common aggregate has the wrong work scope"
                )
            if tuple(
                row.work_scope for row in self.aggregation_source_refs
            ) != (
                ActualWorkScope.COMMON_PREFIX,
                ActualWorkScope.COMMON_PREFIX,
            ):
                raise Phase3EOccurrenceAccountingV1Error(
                    "two-stage common must retain ordered core and suffix refs"
                )
            if any(
                row.route_kind is not self.route_kind
                or row.subject_id != self.subject_id
                for row in self.aggregation_source_refs
            ):
                raise Phase3EOccurrenceAccountingV1Error(
                    "two-stage common source context is stale or spliced"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_kind": self.evidence_kind.value,
            "work_scope": self.work_scope.value,
            "route_kind": self.route_kind.value,
            "subject_id": self.subject_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "actual_projection_proof_id": self.actual_projection_proof_id,
            "native_zero_attestation_id": _ref_payload(
                self.native_zero_attestation_id
            ),
            "reconciliation_proof_id": _ref_payload(
                self.reconciliation_proof_id
            ),
            "marginal_work_aggregation_proof_id": _ref_payload(
                self.marginal_work_aggregation_proof_id
            ),
            "aggregation_source_refs": [
                row.to_dict() for row in self.aggregation_source_refs
            ],
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "OccurrenceRawWorkRefV1":
        expected = {
            "evidence_kind",
            "work_scope",
            "route_kind",
            "subject_id",
            "work_vector_id",
            "comparison_vector_id",
            "actual_projection_proof_id",
            "native_zero_attestation_id",
            "reconciliation_proof_id",
            "marginal_work_aggregation_proof_id",
            "aggregation_source_refs",
        }
        _fields(document, expected, "occurrence raw-work reference")
        if type(document["aggregation_source_refs"]) is not list:
            raise Phase3EOccurrenceAccountingV1Error(
                "aggregation_source_refs must be a list"
            )
        return cls(
            document["evidence_kind"],
            document["work_scope"],
            document["route_kind"],
            document["subject_id"],
            document["work_vector_id"],
            document["comparison_vector_id"],
            document["actual_projection_proof_id"],
            _parse_content_ref(
                document["native_zero_attestation_id"],
                "native_zero_attestation_id",
            ),
            _parse_content_ref(
                document["reconciliation_proof_id"],
                "reconciliation_proof_id",
            ),
            _parse_content_ref(
                document["marginal_work_aggregation_proof_id"],
                "marginal_work_aggregation_proof_id",
            ),
            tuple(
                OccurrenceNativeSourceRefV1.from_dict(row)
                for row in document["aggregation_source_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class OccurrenceWorkComponentRefV1:
    """Content-addressed identity and work provenance for one component."""

    sequence_index: int
    component_kind: OccurrenceWorkComponentKind
    logical_occurrence_id: str
    route_attempt_id: str
    route_decision_context_id: str
    decision_point_id: str
    transaction_id: ContentRefV1
    transaction_index: IndexRefV1
    raw_work_refs: tuple[OccurrenceRawWorkRefV1, ...]
    component_values: tuple[tuple[str, int], ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.sequence_index) is not int or self.sequence_index <= 0:
            raise Phase3EOccurrenceAccountingV1Error(
                "component sequence index must be positive"
            )
        object.__setattr__(
            self,
            "component_kind",
            _enum(
                self.component_kind,
                OccurrenceWorkComponentKind,
                "component_kind",
            ),
        )
        for field in (
            "logical_occurrence_id",
            "route_attempt_id",
            "route_decision_context_id",
            "decision_point_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self,
            "transaction_id",
            _typed_content_ref(self.transaction_id, "transaction_id"),
        )
        object.__setattr__(
            self,
            "transaction_index",
            _typed_index_ref(self.transaction_index, "transaction_index"),
        )
        if not self.raw_work_refs or not all(
            isinstance(row, OccurrenceRawWorkRefV1) for row in self.raw_work_refs
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "component must retain typed raw-work references"
            )
        if len({row.work_vector_id for row in self.raw_work_refs}) != len(
            self.raw_work_refs
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "component repeats a raw WorkVector"
            )
        object.__setattr__(
            self,
            "component_values",
            _axis_values(self.component_values, "component values"),
        )
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3EOccurrenceAccountingV1Error(
                "occurrence component schema version mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.occurrence_work_component_ref.v1",
            "schema_version": self.schema_version,
            "sequence_index": self.sequence_index,
            "component_kind": self.component_kind.value,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": _ref_payload(self.transaction_id),
            "transaction_index": _ref_payload(self.transaction_index),
            "raw_work_refs": [row.to_dict() for row in self.raw_work_refs],
            "component_values": _axis_rows(self.component_values),
        }

    @property
    def occurrence_work_component_ref_id(self) -> str:
        return content_id(OCCURRENCE_WORK_COMPONENT_REF_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_work_component_ref_id": (
                self.occurrence_work_component_ref_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "OccurrenceWorkComponentRefV1":
        expected = {
            "schema",
            "schema_version",
            "sequence_index",
            "component_kind",
            "logical_occurrence_id",
            "route_attempt_id",
            "RouteDecisionContext_id",
            "decision_point_id",
            "transaction_id",
            "transaction_index",
            "raw_work_refs",
            "component_values",
            "occurrence_work_component_ref_id",
        }
        _fields(document, expected, "occurrence work component reference")
        if (
            document["schema"] != "acfqp.occurrence_work_component_ref.v1"
            or type(document["raw_work_refs"]) is not list
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "occurrence component reference schema mismatch"
            )
        result = cls(
            document["sequence_index"],
            document["component_kind"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            document["RouteDecisionContext_id"],
            document["decision_point_id"],
            _parse_content_ref(document["transaction_id"], "transaction_id"),
            _parse_index_ref(document["transaction_index"], "transaction_index"),
            tuple(
                OccurrenceRawWorkRefV1.from_dict(row)
                for row in document["raw_work_refs"]
            ),
            _parse_axis_rows(document["component_values"], "component values"),
            document["schema_version"],
        )
        if (
            document["occurrence_work_component_ref_id"]
            != result.occurrence_work_component_ref_id
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "occurrence component reference content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class OccurrenceWorkComponentEvidenceV1:
    """Runtime evidence used to derive one serialized component reference."""

    component_kind: OccurrenceWorkComponentKind
    route_context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    transaction: TransactionV1 | None
    raw_work: tuple[OccurrenceRawEvidenceV1, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "component_kind",
            _enum(
                self.component_kind,
                OccurrenceWorkComponentKind,
                "component_kind",
            ),
        )
        if not isinstance(self.route_context, RouteDecisionContextV1):
            raise Phase3EOccurrenceAccountingV1Error(
                "component route context has the wrong runtime type"
            )
        if not isinstance(self.decision_point, DecisionPointV1):
            raise Phase3EOccurrenceAccountingV1Error(
                "component decision point has the wrong runtime type"
            )
        if self.transaction is not None and not isinstance(
            self.transaction, TransactionV1
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "component transaction has the wrong runtime type"
            )
        if type(self.raw_work) is not tuple or not self.raw_work:
            raise Phase3EOccurrenceAccountingV1Error(
                "component raw work must be a nonempty immutable tuple"
            )


def _work_evidence_parts(
    evidence: OccurrenceRawEvidenceV1,
    *,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> tuple[
    WorkVectorV1,
    ComparisonVectorV1,
    ActualProjectionProofV1,
    OccurrenceRawWorkRefV1,
]:
    if isinstance(evidence, RecordedWorkV1):
        proof = evidence.actual_projection_proof
        if proof.work_scope is ActualWorkScope.MARGINAL_ROUTE_AGGREGATE:
            raise Phase3EOccurrenceAccountingV1Error(
                "an aggregate WorkVector without source refs is forbidden"
            )
        try:
            verify_recorded_work_v1(
                evidence,
                expected_scope=proof.work_scope,
                registry=registry,
                comparison_profile=comparison_profile,
            )
        except ValueError as error:
            raise Phase3EOccurrenceAccountingV1Error(
                f"RecordedWorkV1 replay failed: {error}"
            ) from error
        work = evidence.work_vector
        comparison = evidence.comparison_vector
        raw_ref = OccurrenceRawWorkRefV1(
            OccurrenceRawEvidenceKind.RECORDED_WORK,
            proof.work_scope,
            work.route_kind,
            work.subject_id,
            work.work_vector_id,
            comparison.comparison_vector_id,
            proof.actual_projection_proof_id,
            evidence.native_zero_attestation.native_zero_attestation_id,
            evidence.reconciliation_proof.reconciliation_proof_id,
            TypedNotApplicable(_NO_MARGINAL_AGGREGATION),
            (),
        )
        return work, comparison, proof, raw_ref

    if isinstance(evidence, RunnerCommonAccountingEvidenceV1):
        core = evidence.core
        closure = evidence.closure
        try:
            verify_two_stage_accounting_v1(
                closure,
                core_work=core,
                semantic_results=evidence.semantic_results,
                nonsemantic_records=evidence.nonsemantic_records,
                route_context=evidence.route_context,
                registry=registry,
                comparison_profile=comparison_profile,
                actual_profile=actual_profile,
            )
        except (TwoStageAccountingV1Error, ValueError) as error:
            raise Phase3EOccurrenceAccountingV1Error(
                f"runner common two-stage replay failed: {error}"
            ) from error
        aggregate = closure.aggregate_work
        suffix = closure.verification_suffix
        work = aggregate.work_vector
        comparison = aggregate.comparison_vector
        proof = aggregate.actual_projection_proof

        def common_source_ref(
            recorded: RecordedWorkV1,
        ) -> OccurrenceNativeSourceRefV1:
            source_proof = recorded.actual_projection_proof
            return OccurrenceNativeSourceRefV1(
                source_proof.work_scope,
                recorded.work_vector.route_kind,
                recorded.work_vector.subject_id,
                recorded.work_vector.work_vector_id,
                recorded.comparison_vector.comparison_vector_id,
                source_proof.actual_projection_proof_id,
                recorded.native_zero_attestation.native_zero_attestation_id,
                recorded.reconciliation_proof.reconciliation_proof_id,
            )

        raw_ref = OccurrenceRawWorkRefV1(
            OccurrenceRawEvidenceKind.TWO_STAGE_ACCOUNTED_COMMON,
            proof.work_scope,
            work.route_kind,
            work.subject_id,
            work.work_vector_id,
            comparison.comparison_vector_id,
            proof.actual_projection_proof_id,
            TypedNotApplicable(_NO_NATIVE_ZERO),
            TypedNotApplicable(_NO_RECONCILIATION),
            closure.receipt.verification_charge_receipt_id,
            (common_source_ref(core), common_source_ref(suffix)),
        )
        return work, comparison, proof, raw_ref

    if type(evidence) is RunnerPartialCommonAccountingEvidenceV1:
        replayed_partial = derive_runner_partial_common_accounting_v1(
            core=evidence.core,
            semantic_results=evidence.semantic_results,
            nonsemantic_records=evidence.nonsemantic_records,
            route_context=evidence.route_context,
            decision_point_id=evidence.decision_point_id,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )
        if replayed_partial != evidence:
            raise Phase3EOccurrenceAccountingV1Error(
                "partial common accounting differs from exact record replay"
            )
        work = evidence.aggregate_work.work_vector
        comparison = evidence.aggregate_work.comparison_vector
        proof = evidence.aggregate_work.actual_projection_proof

        def partial_source_ref(
            recorded: RecordedWorkV1,
        ) -> OccurrenceNativeSourceRefV1:
            source_proof = recorded.actual_projection_proof
            return OccurrenceNativeSourceRefV1(
                source_proof.work_scope,
                recorded.work_vector.route_kind,
                recorded.work_vector.subject_id,
                recorded.work_vector.work_vector_id,
                recorded.comparison_vector.comparison_vector_id,
                source_proof.actual_projection_proof_id,
                recorded.native_zero_attestation.native_zero_attestation_id,
                recorded.reconciliation_proof.reconciliation_proof_id,
            )

        raw_ref = OccurrenceRawWorkRefV1(
            OccurrenceRawEvidenceKind.PARTIAL_ACCOUNTED_COMMON,
            proof.work_scope,
            work.route_kind,
            work.subject_id,
            work.work_vector_id,
            comparison.comparison_vector_id,
            proof.actual_projection_proof_id,
            TypedNotApplicable(_NO_NATIVE_ZERO),
            TypedNotApplicable(_NO_RECONCILIATION),
            evidence.partial_common_accounting_id,
            (
                partial_source_ref(evidence.core),
                partial_source_ref(evidence.verification_suffix),
            ),
        )
        return work, comparison, proof, raw_ref

    if not isinstance(evidence, RunnerMarginalWorkEvidenceV1):
        raise Phase3EOccurrenceAccountingV1Error(
            "raw work must be RecordedWorkV1 or complete runner marginal evidence "
            "or common accounting evidence"
        )

    execution = evidence.execution
    verification = evidence.verification_suffix
    try:
        verify_recorded_work_v1(
            execution,
            expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=registry,
            comparison_profile=comparison_profile,
        )
        verify_recorded_work_v1(
            verification,
            expected_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
            registry=registry,
            comparison_profile=comparison_profile,
        )
        work = evidence.aggregate.aggregate_work_vector
        comparison = evidence.aggregate.aggregate_comparison_vector
        proof = evidence.aggregate.aggregate_projection_proof
        verify_marginal_work_aggregate_v1(
            evidence.aggregate,
            subject_id=work.subject_id,
            route_kind=work.route_kind,
            execution=(
                execution.work_vector,
                execution.comparison_vector,
                execution.actual_projection_proof,
            ),
            verification_suffix=(
                verification.work_vector,
                verification.comparison_vector,
                verification.actual_projection_proof,
            ),
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )
    except (MarginalAccountingV1Error, ValueError) as error:
        raise Phase3EOccurrenceAccountingV1Error(
            f"runner marginal aggregate replay failed: {error}"
        ) from error

    def source_ref(recorded: RecordedWorkV1) -> OccurrenceNativeSourceRefV1:
        source_proof = recorded.actual_projection_proof
        return OccurrenceNativeSourceRefV1(
            source_proof.work_scope,
            recorded.work_vector.route_kind,
            recorded.work_vector.subject_id,
            recorded.work_vector.work_vector_id,
            recorded.comparison_vector.comparison_vector_id,
            source_proof.actual_projection_proof_id,
            recorded.native_zero_attestation.native_zero_attestation_id,
            recorded.reconciliation_proof.reconciliation_proof_id,
        )

    raw_ref = OccurrenceRawWorkRefV1(
        OccurrenceRawEvidenceKind.AGGREGATED_MARGINAL_WORK,
        proof.work_scope,
        work.route_kind,
        work.subject_id,
        work.work_vector_id,
        comparison.comparison_vector_id,
        proof.actual_projection_proof_id,
        TypedNotApplicable(_NO_NATIVE_ZERO),
        TypedNotApplicable(_NO_RECONCILIATION),
        evidence.aggregate.aggregation_proof.marginal_work_aggregation_proof_id,
        (source_ref(execution), source_ref(verification)),
    )
    return work, comparison, proof, raw_ref


def _expected_raw_scopes(
    kind: OccurrenceWorkComponentKind,
    refs: Sequence[OccurrenceRawWorkRefV1],
) -> None:
    scopes = tuple(row.work_scope for row in refs)
    if kind is OccurrenceWorkComponentKind.COMMON_PREFIX:
        if scopes != (ActualWorkScope.COMMON_PREFIX,):
            raise Phase3EOccurrenceAccountingV1Error(
                "common-prefix component must contain one COMMON_PREFIX input"
            )
        return
    allowed = {
        (ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,),
        (
            ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        ),
    }
    if scopes not in allowed:
        raise Phase3EOccurrenceAccountingV1Error(
            "route component must retain MARGINAL_ROUTE_VERIFICATION via a "
            "replayable aggregate or ordered execution-plus-verification work"
        )


def _derive_component_ref(
    evidence: OccurrenceWorkComponentEvidenceV1,
    *,
    sequence_index: int,
    logical_occurrence_id: str,
    route_attempt_id: str,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> OccurrenceWorkComponentRefV1:
    context = evidence.route_context
    decision_point = evidence.decision_point
    kind = evidence.component_kind
    if (
        context.logical_occurrence_id != logical_occurrence_id
        or context.route_attempt_id != route_attempt_id
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "component splices another occurrence or route attempt"
        )
    if (
        context.counter_registry_id != registry.registry_id
        or context.comparison_profile_id
        != comparison_profile.comparison_profile_id
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "component route context uses stale accounting profiles"
        )
    if (
        decision_point.route_decision_context_id
        != context.route_decision_context_id
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "component decision point/context identity mismatch"
        )

    replayed = tuple(
        _work_evidence_parts(
            row,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )
        for row in evidence.raw_work
    )
    raw_refs = tuple(row[3] for row in replayed)
    _expected_raw_scopes(kind, raw_refs)
    comparisons = tuple(row[1].values for row in replayed)

    if kind is OccurrenceWorkComponentKind.COMMON_PREFIX:
        if evidence.transaction is not None:
            raise Phase3EOccurrenceAccountingV1Error(
                "common-prefix component cannot own a transaction"
            )
        work = replayed[0][0]
        bound_core_id = (
            evidence.raw_work[0].core.work_vector.work_vector_id
            if isinstance(
                evidence.raw_work[0],
                (
                    RunnerCommonAccountingEvidenceV1,
                    RunnerPartialCommonAccountingEvidenceV1,
                ),
            )
            else work.work_vector_id
        )
        if (
            work.route_kind is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
            or work.subject_id != route_attempt_id
            or decision_point.common_prefix_work_id != bound_core_id
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "common-prefix WorkVector is stale for its decision point"
            )
        transaction_id: ContentRefV1 = TypedNotApplicable(_NO_TRANSACTION)
        transaction_index: IndexRefV1 = TypedNotApplicable(
            _NO_TRANSACTION_INDEX
        )
    elif kind is OccurrenceWorkComponentKind.LOCAL_TRANSACTION:
        transaction = evidence.transaction
        if transaction is None:
            raise Phase3EOccurrenceAccountingV1Error(
                "local component requires its exact transaction"
            )
        if isinstance(decision_point.transaction_index, TypedNotApplicable):
            raise Phase3EOccurrenceAccountingV1Error(
                "local decision point has no transaction index"
            )
        if isinstance(decision_point.frontier_snapshot_id, TypedNotApplicable):
            raise Phase3EOccurrenceAccountingV1Error(
                "local decision point has no frontier"
            )
        expected_transaction = (
            logical_occurrence_id,
            route_attempt_id,
            decision_point.decision_point_id,
            decision_point.transaction_index,
            decision_point.frontier_snapshot_id,
        )
        actual_transaction = (
            transaction.logical_occurrence_id,
            transaction.route_attempt_id,
            transaction.decision_point_id,
            transaction.transaction_index,
            transaction.frontier_snapshot_id,
        )
        if actual_transaction != expected_transaction:
            raise Phase3EOccurrenceAccountingV1Error(
                "local component transaction identity chain is stale or spliced"
            )
        if any(
            row[0].route_kind is not RouteKindEnum.LOCAL_ATTEMPT
            or row[0].subject_id != transaction.transaction_id
            for row in replayed
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "local raw WorkVector does not bind its transaction subject"
            )
        transaction_id = transaction.transaction_id
        transaction_index = transaction.transaction_index
    else:
        if evidence.transaction is not None:
            raise Phase3EOccurrenceAccountingV1Error(
                "direct fallback cannot own a local transaction"
            )
        fallback_only = (
            isinstance(decision_point.transaction_index, TypedNotApplicable)
            and isinstance(
                decision_point.frontier_snapshot_id, TypedNotApplicable
            )
            and isinstance(decision_point.causal_evidence_id, TypedNotApplicable)
        )
        marginal_fallback = (
            type(decision_point.transaction_index) is int
            and decision_point.transaction_index in {1, 2}
            and isinstance(decision_point.frontier_snapshot_id, str)
            and isinstance(decision_point.causal_evidence_id, str)
        )
        if not (fallback_only or marginal_fallback):
            raise Phase3EOccurrenceAccountingV1Error(
                "direct fallback requires either a fallback-only point or a "
                "complete marginal local/fallback decision point"
            )
        if any(
            row[0].route_kind is not RouteKindEnum.DIRECT_FALLBACK
            or row[0].subject_id != route_attempt_id
            for row in replayed
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "fallback raw WorkVector does not bind its route-attempt subject"
            )
        transaction_id = TypedNotApplicable(_NO_TRANSACTION)
        transaction_index = TypedNotApplicable(_NO_TRANSACTION_INDEX)

    return OccurrenceWorkComponentRefV1(
        sequence_index,
        kind,
        logical_occurrence_id,
        route_attempt_id,
        context.route_decision_context_id,
        decision_point.decision_point_id,
        transaction_id,
        transaction_index,
        raw_refs,
        _reduce_axis_values(comparisons, comparison_profile),
    )


_STABLE_CONTEXT_FIELDS = (
    "preregistration_id",
    "protocol_id",
    "comparison_profile_id",
    "counter_registry_id",
    "structural_id",
    "query_id",
    "threshold_profile_id",
    "build_epoch_id",
    "logical_occurrence_id",
    "route_attempt_id",
)


def _validate_runtime_sequence(
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
) -> None:
    if not components:
        raise Phase3EOccurrenceAccountingV1Error(
            "occurrence work must contain at least one charged component"
        )
    partial_common_positions = tuple(
        index
        for index, component in enumerate(components)
        if any(
            type(raw) is RunnerPartialCommonAccountingEvidenceV1
            for raw in component.raw_work
        )
    )
    # PARTIAL_ACCOUNTED_COMMON is rejection-only evidence.  It can preserve a
    # verifier suffix after package validation aborts, but it must never be
    # laundered into an earlier or route-paired successful decision prefix.
    if partial_common_positions and (
        partial_common_positions != (len(components) - 1,)
        or len(components) % 2 != 1
        or components[-1].component_kind
        is not OccurrenceWorkComponentKind.COMMON_PREFIX
        or len(components[-1].raw_work) != 1
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "PARTIAL_ACCOUNTED_COMMON is allowed only as the final unpaired "
            "rejected-package common prefix"
        )

    # A control-plane failure may occur after a next decision's common-prefix
    # work has been sealed but before its route decision is frozen.  That final
    # prefix is real work and must remain chargeable; inventing a zero-valued
    # route partner would violate FQ13.  Every earlier prefix must still have
    # exactly one route component.
    has_unpaired_terminal_prefix = len(components) % 2 == 1
    paired = components[:-1] if has_unpaired_terminal_prefix else components
    if has_unpaired_terminal_prefix and (
        components[-1].component_kind
        is not OccurrenceWorkComponentKind.COMMON_PREFIX
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "only a final pre-freeze common prefix may be unpaired"
        )
    route_components = paired[1::2]
    prefix_components = paired[0::2]
    if any(
        row.component_kind is not OccurrenceWorkComponentKind.COMMON_PREFIX
        for row in prefix_components
    ) or any(
        row.component_kind is OccurrenceWorkComponentKind.COMMON_PREFIX
        for row in route_components
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "occurrence components are not ordered prefix/route pairs"
        )
    local_components = tuple(
        row
        for row in route_components
        if row.component_kind is OccurrenceWorkComponentKind.LOCAL_TRANSACTION
    )
    fallback_components = tuple(
        row
        for row in route_components
        if row.component_kind is OccurrenceWorkComponentKind.DIRECT_FALLBACK
    )
    if len(local_components) > MAX_LOCAL_TRANSACTIONS:
        raise Phase3EOccurrenceAccountingV1Error(
            "occurrence exceeds the two-local-transaction budget"
        )
    if len(fallback_components) > 1:
        raise Phase3EOccurrenceAccountingV1Error(
            "occurrence repeats direct fallback"
        )
    if fallback_components and route_components[-1] is not fallback_components[0]:
        raise Phase3EOccurrenceAccountingV1Error(
            "direct fallback must be the final route component"
        )
    for prefix, route in zip(prefix_components, route_components, strict=True):
        if (
            prefix.route_context.route_decision_context_id
            != route.route_context.route_decision_context_id
            or prefix.decision_point.decision_point_id
            != route.decision_point.decision_point_id
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "a route component is spliced from another common-prefix decision"
            )


def _validate_cross_component_chain(
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    refs: tuple[OccurrenceWorkComponentRefV1, ...],
) -> None:
    first_context = components[0].route_context
    for component in components[1:]:
        context = component.route_context
        for field in _STABLE_CONTEXT_FIELDS:
            if getattr(context, field) != getattr(first_context, field):
                raise Phase3EOccurrenceAccountingV1Error(
                    f"occurrence component changed stable context field {field}"
                )

    raw_refs = tuple(
        raw for component in refs for raw in component.raw_work_refs
    )
    source_refs = tuple(
        source for raw in raw_refs for source in raw.aggregation_source_refs
    )
    work_ids = [raw.work_vector_id for raw in raw_refs] + [
        source.work_vector_id for source in source_refs
    ]
    comparison_ids = [raw.comparison_vector_id for raw in raw_refs] + [
        source.comparison_vector_id for source in source_refs
    ]
    projection_ids = [raw.actual_projection_proof_id for raw in raw_refs] + [
        source.actual_projection_proof_id for source in source_refs
    ]
    for values, label in (
        (work_ids, "WorkVector"),
        (comparison_ids, "ComparisonVector"),
        (projection_ids, "ActualProjectionProof"),
    ):
        if len(set(values)) != len(values):
            raise Phase3EOccurrenceAccountingV1Error(
                f"occurrence repeats a raw {label} identity"
            )

    paired = components[:-1] if len(components) % 2 else components
    route_pairs = tuple(zip(paired[0::2], paired[1::2], strict=True))
    decision_ids = [
        prefix.decision_point.decision_point_id
        for prefix in components[0::2]
    ]
    if len(set(decision_ids)) != len(decision_ids):
        raise Phase3EOccurrenceAccountingV1Error(
            "occurrence reuses a stale decision point"
        )
    prefix_work_ids = [
        ref.raw_work_refs[0].work_vector_id
        for ref in refs
        if ref.component_kind is OccurrenceWorkComponentKind.COMMON_PREFIX
    ]
    if len(set(prefix_work_ids)) != len(prefix_work_ids):
        raise Phase3EOccurrenceAccountingV1Error(
            "occurrence reuses stale common-prefix work"
        )

    local_pairs = tuple(
        pair
        for pair in route_pairs
        if pair[1].component_kind
        is OccurrenceWorkComponentKind.LOCAL_TRANSACTION
    )
    local_transactions = tuple(pair[1].transaction for pair in local_pairs)
    if tuple(row.transaction_index for row in local_transactions if row is not None) != tuple(
        range(1, len(local_transactions) + 1)
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "local transaction indices must be continuous from 1"
        )
    local_transaction_ids = tuple(
        row.transaction_id for row in local_transactions if row is not None
    )
    if len(set(local_transaction_ids)) != len(local_transaction_ids):
        raise Phase3EOccurrenceAccountingV1Error(
            "occurrence repeats a local transaction identity"
        )
    if len(local_pairs) == 2:
        first_local_context = local_pairs[0][1].route_context
        second_local_context = local_pairs[1][1].route_context
        if (
            first_local_context.route_decision_context_id
            == second_local_context.route_decision_context_id
            or first_local_context.selected_plan_id
            == second_local_context.selected_plan_id
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "transaction 2 must use a fresh selected-plan context"
            )
        first_transaction = local_pairs[0][1].transaction
        second_transaction = local_pairs[1][1].transaction
        assert first_transaction is not None and second_transaction is not None
        if first_transaction.frontier_snapshot_id == second_transaction.frontier_snapshot_id:
            raise Phase3EOccurrenceAccountingV1Error(
                "transaction 2 reuses the stale transaction-1 frontier"
            )

    fallback_pairs = tuple(
        pair
        for pair in route_pairs
        if pair[1].component_kind
        is OccurrenceWorkComponentKind.DIRECT_FALLBACK
    )
    if fallback_pairs:
        fallback_route = fallback_pairs[0][1]
        fallback_context = fallback_route.route_context
        fallback_point = fallback_route.decision_point
        marginal_fallback = not isinstance(
            fallback_point.transaction_index, TypedNotApplicable
        )
        if marginal_fallback:
            expected_candidate_index = len(local_pairs) + 1
            if fallback_point.transaction_index != expected_candidate_index:
                raise Phase3EOccurrenceAccountingV1Error(
                    "marginal fallback candidate index does not follow the "
                    "executed local transaction history"
                )
            if expected_candidate_index > MAX_LOCAL_TRANSACTIONS:
                raise Phase3EOccurrenceAccountingV1Error(
                    "marginal fallback exceeds the local transaction budget"
                )
            if local_pairs:
                latest_local = local_pairs[-1][1]
                latest_transaction = latest_local.transaction
                assert latest_transaction is not None
                if (
                    fallback_context.route_decision_context_id
                    == latest_local.route_context.route_decision_context_id
                    or fallback_context.selected_plan_id
                    == latest_local.route_context.selected_plan_id
                ):
                    raise Phase3EOccurrenceAccountingV1Error(
                        "post-local marginal fallback must retain the fresh "
                        "stitched-plan decision context"
                    )
                if (
                    fallback_point.frontier_snapshot_id
                    == latest_transaction.frontier_snapshot_id
                ):
                    raise Phase3EOccurrenceAccountingV1Error(
                        "post-local marginal fallback reused the stale frontier"
                    )
        elif local_pairs:
            latest_local_context = local_pairs[-1][1].route_context
            if (
                fallback_context.route_decision_context_id
                != latest_local_context.route_decision_context_id
            ):
                raise Phase3EOccurrenceAccountingV1Error(
                    "post-local fallback uses a stale route-decision context"
                )


@dataclass(frozen=True, slots=True)
class Phase3EOccurrenceWorkAggregateV1:
    """Content-addressed non-scalar total retaining all component references."""

    logical_occurrence_id: str
    route_attempt_id: str
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    component_refs: tuple[OccurrenceWorkComponentRefV1, ...]
    aggregate_values: tuple[tuple[str, int], ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "logical_occurrence_id",
            "route_attempt_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
        ):
            _cid(getattr(self, field), field)
        if not self.component_refs or not all(
            isinstance(row, OccurrenceWorkComponentRefV1)
            for row in self.component_refs
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "occurrence aggregate requires typed component references"
            )
        if tuple(row.sequence_index for row in self.component_refs) != tuple(
            range(1, len(self.component_refs) + 1)
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "occurrence component sequence must be continuous from 1"
            )
        if len(
            {row.occurrence_work_component_ref_id for row in self.component_refs}
        ) != len(self.component_refs):
            raise Phase3EOccurrenceAccountingV1Error(
                "occurrence aggregate repeats a component reference"
            )
        if any(
            row.logical_occurrence_id != self.logical_occurrence_id
            or row.route_attempt_id != self.route_attempt_id
            for row in self.component_refs
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "occurrence component reference has a stale occurrence or attempt"
            )
        partial_common_positions = tuple(
            index
            for index, component in enumerate(self.component_refs)
            if any(
                raw.evidence_kind
                is OccurrenceRawEvidenceKind.PARTIAL_ACCOUNTED_COMMON
                for raw in component.raw_work_refs
            )
        )
        if partial_common_positions and (
            partial_common_positions != (len(self.component_refs) - 1,)
            or len(self.component_refs) % 2 != 1
            or self.component_refs[-1].component_kind
            is not OccurrenceWorkComponentKind.COMMON_PREFIX
            or len(self.component_refs[-1].raw_work_refs) != 1
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "PARTIAL_ACCOUNTED_COMMON is allowed only as the final unpaired "
                "rejected-package common prefix"
            )
        object.__setattr__(
            self,
            "aggregate_values",
            _axis_values(self.aggregate_values, "occurrence aggregate values"),
        )
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3EOccurrenceAccountingV1Error(
                "occurrence aggregate schema version mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_occurrence_work_aggregate.v1",
            "schema_version": self.schema_version,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "component_refs": [row.to_dict() for row in self.component_refs],
            "aggregate_values": _axis_rows(self.aggregate_values),
        }

    @property
    def phase3e_occurrence_work_aggregate_id(self) -> str:
        return content_id(OCCURRENCE_WORK_AGGREGATE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "phase3e_occurrence_work_aggregate_id": (
                self.phase3e_occurrence_work_aggregate_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "Phase3EOccurrenceWorkAggregateV1":
        expected = {
            "schema",
            "schema_version",
            "logical_occurrence_id",
            "route_attempt_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "component_refs",
            "aggregate_values",
            "phase3e_occurrence_work_aggregate_id",
        }
        _fields(document, expected, "Phase-3E occurrence work aggregate")
        if (
            document["schema"]
            != "acfqp.phase3e_occurrence_work_aggregate.v1"
            or type(document["component_refs"]) is not list
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "Phase-3E occurrence aggregate schema mismatch"
            )
        result = cls(
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["actual_projection_profile_id"],
            tuple(
                OccurrenceWorkComponentRefV1.from_dict(row)
                for row in document["component_refs"]
            ),
            _parse_axis_rows(
                document["aggregate_values"], "occurrence aggregate values"
            ),
            document["schema_version"],
        )
        if (
            document["phase3e_occurrence_work_aggregate_id"]
            != result.phase3e_occurrence_work_aggregate_id
        ):
            raise Phase3EOccurrenceAccountingV1Error(
                "Phase-3E occurrence aggregate content ID mismatch"
            )
        return result


def derive_phase3e_occurrence_work_aggregate_v1(
    *,
    logical_occurrence_id: str,
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> Phase3EOccurrenceWorkAggregateV1:
    """Replay a complete ordered occurrence and derive its exact vector total."""

    occurrence_id = _cid(logical_occurrence_id, "logical_occurrence_id")
    if type(components) is not tuple or not all(
        isinstance(row, OccurrenceWorkComponentEvidenceV1) for row in components
    ):
        raise Phase3EOccurrenceAccountingV1Error(
            "components must be an immutable typed tuple"
        )
    try:
        registry.validate_official_catalogue()
        comparison_profile.validate(registry)
        actual_profile.validate(registry, comparison_profile)
    except ValueError as error:
        raise Phase3EOccurrenceAccountingV1Error(str(error)) from error
    _validate_runtime_sequence(components)
    route_attempt_id = components[0].route_context.route_attempt_id
    refs = tuple(
        _derive_component_ref(
            component,
            sequence_index=index,
            logical_occurrence_id=occurrence_id,
            route_attempt_id=route_attempt_id,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )
        for index, component in enumerate(components, start=1)
    )
    _validate_cross_component_chain(components, refs)
    return Phase3EOccurrenceWorkAggregateV1(
        occurrence_id,
        route_attempt_id,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        actual_profile.actual_projection_profile_id,
        refs,
        _reduce_axis_values(
            tuple(row.component_values for row in refs), comparison_profile
        ),
    )


def verify_phase3e_occurrence_work_aggregate_v1(
    claimed: Phase3EOccurrenceWorkAggregateV1,
    *,
    logical_occurrence_id: str,
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> Phase3EOccurrenceWorkAggregateV1:
    """Reconstruct a claimed occurrence aggregate from all raw evidence."""

    if not isinstance(claimed, Phase3EOccurrenceWorkAggregateV1):
        raise Phase3EOccurrenceAccountingV1Error(
            "claimed occurrence aggregate has the wrong runtime type"
        )
    replayed = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=logical_occurrence_id,
        components=components,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    if claimed != replayed:
        raise Phase3EOccurrenceAccountingV1Error(
            "claimed occurrence aggregate differs from reducer-aware evidence replay"
        )
    return replayed


__all__ = [
    "MAX_LOCAL_TRANSACTIONS",
    "OccurrenceNativeSourceRefV1",
    "OccurrenceRawEvidenceKind",
    "OccurrenceRawWorkRefV1",
    "OccurrenceWorkComponentEvidenceV1",
    "OccurrenceWorkComponentKind",
    "OccurrenceWorkComponentRefV1",
    "Phase3EOccurrenceAccountingV1Error",
    "Phase3EOccurrenceWorkAggregateV1",
    "RunnerMarginalWorkEvidenceV1",
    "RunnerCommonAccountingEvidenceV1",
    "RunnerPartialCommonAccountingEvidenceV1",
    "derive_runner_partial_common_accounting_v1",
    "derive_phase3e_occurrence_work_aggregate_v1",
    "verify_phase3e_occurrence_work_aggregate_v1",
]
