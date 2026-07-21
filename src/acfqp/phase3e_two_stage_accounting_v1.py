"""Cycle-free two-stage accounting for Phase 3E verification work.

The accounting boundary in this module is deliberately ordered::

    sealed core
      -> frozen verification-charge plan
      -> authoritative semantic verification results
      -> operational verification suffix
      -> reducer-aware core+suffix aggregate
      -> exact charge manifest and receipt

The charge plan fixes the complete set of semantic obligations before their
work is admitted.  The manifest then binds every authoritative attestation to
its exact source ``CounterRecordV1`` and to the destination suffix/aggregate
artifacts.  Consequently an omitted, padded, duplicated, substituted, or
cross-context charge cannot be made self-consistent merely by re-hashing a
claimed total.

The manifest and receipt do not charge their own verification.  They are
deterministic closure artifacts over already incurred operational records;
this is the seal boundary that prevents a self-referential accounting cycle.
No scalar cost or official-economics claim is introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from acfqp.accounting_v1 import (
    AccountingV1Error,
    ComparisonProfileV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    NativeZeroAttestationV1,
    ReconciliationProofV1,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    WorkVectorV1,
    explicit_records_v1,
)
from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    ProtocolSequenceProfileV1,
    RouteDecisionFreezeAttestationV1,
    replay_access_protocol,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProfileV1,
    ActualProjectionProofV1,
    ActualWorkScope,
    derive_actual_projection_v1,
    verify_actual_projection_v1,
)
from acfqp.native_recorder_v1 import RecordedWorkV1
from acfqp.marginal_accounting_v1 import (
    AGGREGATION_RECORDER_ID,
    AggregatedMarginalWorkV1,
    derive_marginal_work_aggregate_v1,
)
from acfqp.phase3e_ids import (
    ACCOUNTING_CORE_SEAL_DOMAIN,
    NONSEMANTIC_VERIFICATION_ATTESTATION_DOMAIN,
    TWO_STAGE_WORK_AGGREGATE_DOMAIN,
    VERIFICATION_CHARGE_ENTRY_DOMAIN,
    VERIFICATION_CHARGE_MANIFEST_DOMAIN,
    VERIFICATION_CHARGE_PLAN_DOMAIN,
    VERIFICATION_CHARGE_RECEIPT_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import (
    RouteKind,
    RouteDecisionContextV1,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationResultV1,
    semantic_verifier_spec_v1,
)


SCHEMA_VERSION = "1.0.0"
TWO_STAGE_SUFFIX_RECORDER_ID = "phase3e-two-stage-verification-suffix-v1"
TWO_STAGE_AGGREGATE_RECORDER_ID = "phase3e-two-stage-work-aggregate-v1"


class TwoStageAccountingV1Error(ValueError):
    """A core, charge plan, suffix, aggregate, manifest, or receipt is invalid."""


class AccountingCoreStage(str, Enum):
    COMMON_PREFIX = "COMMON_PREFIX"
    ROUTE_EXECUTION = "ROUTE_EXECUTION"


class NonsemanticVerificationCheckKind(str, Enum):
    ACCESS_TRACE_RECONCILIATION = "ACCESS_TRACE_RECONCILIATION"
    EXECUTION_VECTOR_INTEGRITY = "EXECUTION_VECTOR_INTEGRITY"
    NATIVE_AGGREGATION = "NATIVE_AGGREGATION"
    AGGREGATE_UPPER_COMPLIANCE = "AGGREGATE_UPPER_COMPLIANCE"
    CONTINUATION_WORK_VECTOR_AUTHORITY = (
        "CONTINUATION_WORK_VECTOR_AUTHORITY"
    )


@dataclass(frozen=True, slots=True)
class AccessTraceReconciliationEvidenceV1:
    """Typed inputs for registered access-order/native-counter replay."""

    access_log: AccessEventLogV1
    freeze_attestation: RouteDecisionFreezeAttestationV1
    protocol_profile: ProtocolSequenceProfileV1
    decision_result: object
    selected_route: RouteSelection
    execution: object
    execution_work: RecordedWorkV1


@dataclass(frozen=True, slots=True)
class ExecutionVectorIntegrityEvidenceV1:
    """The exact execution vector whose sealed core is being verified."""

    execution_work: RecordedWorkV1


@dataclass(frozen=True, slots=True)
class NativeAggregationEvidenceV1:
    """An independently derived native marginal aggregation."""

    independent_aggregate: AggregatedMarginalWorkV1 | None = None


@dataclass(frozen=True, slots=True)
class AggregateUpperComplianceEvidenceV1:
    """The authoritative selected upper checked against the aggregate."""

    selected_upper: RouteUpperBoundEnvelopeV1


@dataclass(frozen=True, slots=True)
class ContinuationWorkVectorEvidenceV1:
    """A prior-run authority and the new context in which it is replayed."""

    authority: object
    current_context: RouteDecisionContextV1


NonsemanticVerificationEvidenceV1 = (
    AccessTraceReconciliationEvidenceV1
    | ExecutionVectorIntegrityEvidenceV1
    | NativeAggregationEvidenceV1
    | AggregateUpperComplianceEvidenceV1
    | ContinuationWorkVectorEvidenceV1
)


def _route_kind_for_selection_v1(
    selected: RouteSelection,
) -> RouteKindEnum:
    """Translate decision vocabulary to native accounting vocabulary."""

    selection = RouteSelection(selected)
    return (
        RouteKindEnum.LOCAL_ATTEMPT
        if selection is RouteSelection.LOCAL
        else RouteKindEnum.DIRECT_FALLBACK
    )


ContentRef = str | TypedNotApplicable


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise TwoStageAccountingV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise TwoStageAccountingV1Error(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _positive(value: Any, field: str) -> int:
    value = _nonnegative(value, field)
    if value == 0:
        raise TwoStageAccountingV1Error(f"{field} must be positive")
    return value


def _token(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise TwoStageAccountingV1Error(f"{field} must be a nonempty string")
    return value


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise TwoStageAccountingV1Error(str(error)) from error


def _enum(value: Any, enum_type: type[Enum], field: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise TwoStageAccountingV1Error(f"invalid {field}: {value!r}") from error


def _content_ref(value: Any, field: str) -> ContentRef:
    if isinstance(value, TypedNotApplicable):
        return value
    return _cid(value, field)


def _parse_content_ref(value: Any, field: str) -> ContentRef:
    if isinstance(value, Mapping):
        try:
            return TypedNotApplicable.from_dict(value)
        except ValueError as error:
            raise TwoStageAccountingV1Error(str(error)) from error
    return _content_ref(value, field)


def _ref_dict(value: ContentRef) -> Any:
    return value.to_dict() if isinstance(value, TypedNotApplicable) else value


def _same_ref(left: ContentRef, right: ContentRef) -> bool:
    # ``TypedNotApplicable.reason`` is part of the canonical typed-null payload
    # and therefore part of the frozen identity.  Treating every typed null as
    # interchangeable would let a semantic result minted for one explicit
    # not-applicable binding satisfy a differently content-addressed charge
    # obligation.
    return left == right


def _load_context(value: RouteDecisionContextV1 | Mapping[str, Any]) -> RouteDecisionContextV1:
    try:
        return RouteDecisionContextV1.from_dict(
            value.to_dict() if isinstance(value, RouteDecisionContextV1) else value
        )
    except ValueError as error:
        raise TwoStageAccountingV1Error(
            f"invalid RouteDecisionContextV1: {error}"
        ) from error


def _verify_profiles(
    context: RouteDecisionContextV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> None:
    try:
        registry.validate_official_catalogue()
        comparison_profile.validate(registry)
        actual_profile.validate(registry, comparison_profile)
    except ValueError as error:
        raise TwoStageAccountingV1Error(str(error)) from error
    if context.counter_registry_id != registry.registry_id:
        raise TwoStageAccountingV1Error("route context uses another counter registry")
    if context.comparison_profile_id != comparison_profile.comparison_profile_id:
        raise TwoStageAccountingV1Error("route context uses another comparison profile")


def _verify_recorded_work(
    recorded: RecordedWorkV1,
    *,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> None:
    if not isinstance(recorded, RecordedWorkV1):
        raise TwoStageAccountingV1Error("work must be an exact RecordedWorkV1")
    try:
        registry.validate_vector(recorded.work_vector)
        if recorded.native_zero_attestation != NativeZeroAttestationV1.derive(
            recorded.work_vector, registry
        ):
            raise TwoStageAccountingV1Error("native-zero attestation mismatch")
        if recorded.reconciliation_proof != ReconciliationProofV1.derive(
            recorded.work_vector, registry
        ):
            raise TwoStageAccountingV1Error("reconciliation proof mismatch")
        verify_actual_projection_v1(
            recorded.actual_projection_proof,
            recorded.work_vector,
            recorded.comparison_vector,
            registry,
            comparison_profile,
            actual_profile,
        )
    except (AccountingV1Error, ValueError) as error:
        if isinstance(error, TwoStageAccountingV1Error):
            raise
        raise TwoStageAccountingV1Error(str(error)) from error


@dataclass(frozen=True, slots=True)
class SealedAccountingCoreV1:
    route_decision_context_id: str
    decision_point_id: ContentRef
    transaction_id: ContentRef
    core_stage: AccountingCoreStage
    route_kind: RouteKindEnum
    subject_id: str
    work_scope: ActualWorkScope
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    core_work_vector_id: str
    core_comparison_vector_id: str
    core_projection_proof_id: str
    core_counter_record_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in (
            "route_decision_context_id",
            "subject_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "core_work_vector_id",
            "core_comparison_vector_id",
            "core_projection_proof_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self, "decision_point_id", _content_ref(self.decision_point_id, "decision_point_id")
        )
        object.__setattr__(
            self, "transaction_id", _content_ref(self.transaction_id, "transaction_id")
        )
        object.__setattr__(
            self, "core_stage", _enum(self.core_stage, AccountingCoreStage, "core_stage")
        )
        object.__setattr__(
            self, "route_kind", _enum(self.route_kind, RouteKindEnum, "route_kind")
        )
        object.__setattr__(
            self, "work_scope", _enum(self.work_scope, ActualWorkScope, "work_scope")
        )
        if not self.core_counter_record_ids:
            raise TwoStageAccountingV1Error("sealed core must bind counter records")
        for record_id in self.core_counter_record_ids:
            _cid(record_id, "core_counter_record_id")
        if len(set(self.core_counter_record_ids)) != len(self.core_counter_record_ids):
            raise TwoStageAccountingV1Error("sealed core repeats a counter record ID")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.accounting_core_seal.v1",
            "schema_version": SCHEMA_VERSION,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": _ref_dict(self.decision_point_id),
            "transaction_id": _ref_dict(self.transaction_id),
            "core_stage": self.core_stage.value,
            "route_kind": self.route_kind.value,
            "subject_id": self.subject_id,
            "work_scope": self.work_scope.value,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "core_work_vector_id": self.core_work_vector_id,
            "core_comparison_vector_id": self.core_comparison_vector_id,
            "core_projection_proof_id": self.core_projection_proof_id,
            "core_counter_record_ids": list(self.core_counter_record_ids),
        }

    @property
    def accounting_core_seal_id(self) -> str:
        return content_id(ACCOUNTING_CORE_SEAL_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_core_seal_id": self.accounting_core_seal_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "SealedAccountingCoreV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "transaction_id",
            "core_stage",
            "route_kind",
            "subject_id",
            "work_scope",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "core_work_vector_id",
            "core_comparison_vector_id",
            "core_projection_proof_id",
            "core_counter_record_ids",
            "accounting_core_seal_id",
        }
        _fields(document, expected, "accounting core seal")
        if (
            document["schema"] != "acfqp.accounting_core_seal.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["core_counter_record_ids"]) is not list
        ):
            raise TwoStageAccountingV1Error("accounting-core-seal schema mismatch")
        result = cls(
            document["RouteDecisionContext_id"],
            _parse_content_ref(document["decision_point_id"], "decision_point_id"),
            _parse_content_ref(document["transaction_id"], "transaction_id"),
            document["core_stage"],
            document["route_kind"],
            document["subject_id"],
            document["work_scope"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["actual_projection_profile_id"],
            document["core_work_vector_id"],
            document["core_comparison_vector_id"],
            document["core_projection_proof_id"],
            tuple(document["core_counter_record_ids"]),
        )
        if document["accounting_core_seal_id"] != result.accounting_core_seal_id:
            raise TwoStageAccountingV1Error("accounting-core-seal content ID mismatch")
        return result


def seal_accounting_core_v1(
    *,
    recorded_work: RecordedWorkV1,
    binding: AttestationContextV1,
    core_stage: AccountingCoreStage | str,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> SealedAccountingCoreV1:
    if not isinstance(binding, AttestationContextV1):
        raise TwoStageAccountingV1Error("core requires an AttestationContextV1")
    context = _load_context(binding.route_context)
    _verify_profiles(context, registry, comparison_profile, actual_profile)
    _verify_recorded_work(
        recorded_work,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    stage = _enum(core_stage, AccountingCoreStage, "core_stage")
    vector = recorded_work.work_vector
    proof = recorded_work.actual_projection_proof
    transaction_na = isinstance(binding.transaction_id, TypedNotApplicable)
    decision_na = isinstance(binding.decision_point_id, TypedNotApplicable)
    if stage is AccountingCoreStage.COMMON_PREFIX:
        if (
            vector.route_kind not in {
                RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
                RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            }
            or proof.work_scope is not ActualWorkScope.COMMON_PREFIX
            or vector.subject_id != context.route_attempt_id
            or not transaction_na
        ):
            raise TwoStageAccountingV1Error(
                "common-prefix core route/scope/subject/transaction mismatch"
            )
    else:
        if proof.work_scope is not ActualWorkScope.MARGINAL_ROUTE_EXECUTION:
            raise TwoStageAccountingV1Error("route core must be marginal execution work")
        if vector.route_kind is RouteKindEnum.LOCAL_ATTEMPT:
            if decision_na or transaction_na or vector.subject_id != binding.transaction_id:
                raise TwoStageAccountingV1Error("local core context/subject mismatch")
        elif vector.route_kind is RouteKindEnum.DIRECT_FALLBACK:
            if decision_na or not transaction_na or vector.subject_id != context.route_attempt_id:
                raise TwoStageAccountingV1Error("fallback core context/subject mismatch")
        else:
            raise TwoStageAccountingV1Error(
                "route core must be LOCAL_ATTEMPT or DIRECT_FALLBACK"
            )
    return SealedAccountingCoreV1(
        context.route_decision_context_id,
        binding.decision_point_id,
        binding.transaction_id,
        stage,
        vector.route_kind,
        vector.subject_id,
        proof.work_scope,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        actual_profile.actual_projection_profile_id,
        vector.work_vector_id,
        recorded_work.comparison_vector.comparison_vector_id,
        proof.actual_projection_proof_id,
        tuple(row.record_id for row in vector.records),
    )


@dataclass(frozen=True, slots=True)
class VerificationChargeObligationV1:
    ordinal: int
    artifact_id: str
    artifact_schema_id: str
    artifact_role: str
    semantic_verifier_id: str
    verification_profile_id: str
    verification_counter_path: str
    verification_lane: LaneEnum
    source_counter_record_id: str
    expected_result: str
    verified_at_protocol_step: int
    decision_point_id: ContentRef | None = None
    transaction_id: ContentRef | None = None

    def __post_init__(self) -> None:
        _nonnegative(self.ordinal, "obligation ordinal")
        _cid(self.artifact_id, "obligation artifact_id")
        _token(self.artifact_schema_id, "artifact_schema_id")
        _token(self.artifact_role, "artifact_role")
        _cid(self.semantic_verifier_id, "semantic_verifier_id")
        _cid(self.verification_profile_id, "verification_profile_id")
        _token(self.verification_counter_path, "verification_counter_path")
        object.__setattr__(
            self,
            "verification_lane",
            _enum(self.verification_lane, LaneEnum, "verification_lane"),
        )
        if self.verification_lane is not LaneEnum.OPERATIONAL:
            raise TwoStageAccountingV1Error(
                "two-stage operational suffix rejects evaluation-lane verification"
            )
        _cid(self.source_counter_record_id, "source_counter_record_id")
        _token(self.expected_result, "expected_result")
        _nonnegative(self.verified_at_protocol_step, "verified_at_protocol_step")
        if self.decision_point_id is not None:
            object.__setattr__(
                self,
                "decision_point_id",
                _content_ref(self.decision_point_id, "decision_point_id"),
            )
        if self.transaction_id is not None:
            object.__setattr__(
                self,
                "transaction_id",
                _content_ref(self.transaction_id, "transaction_id"),
            )
        try:
            spec = semantic_verifier_spec_v1(SemanticRole(self.artifact_role))
        except (TypeError, ValueError) as error:
            raise TwoStageAccountingV1Error(
                f"unknown semantic role {self.artifact_role!r}"
            ) from error
        expected = (
            spec.artifact_schema_id,
            spec.semantic_verifier_id,
            spec.verification_profile_id,
            spec.counter_path_for_lane(self.verification_lane),
        )
        actual = (
            self.artifact_schema_id,
            self.semantic_verifier_id,
            self.verification_profile_id,
            self.verification_counter_path,
        )
        if actual != expected:
            raise TwoStageAccountingV1Error(
                "verification obligation drifts from the semantic verifier registry"
            )
        if self.expected_result not in spec.outcomes or self.expected_result == "INVALID":
            raise TwoStageAccountingV1Error(
                "verification obligation must freeze a non-INVALID registered result"
            )

    @classmethod
    def for_role(
        cls,
        *,
        ordinal: int,
        artifact_id: str,
        role: SemanticRole | str,
        expected_result: str,
        verified_at_protocol_step: int,
        verification_work_record: CounterRecordV1,
        binding: AttestationContextV1 | None = None,
    ) -> "VerificationChargeObligationV1":
        semantic_role = _enum(role, SemanticRole, "semantic role")
        spec = semantic_verifier_spec_v1(semantic_role)
        if (
            not isinstance(verification_work_record, CounterRecordV1)
            or verification_work_record.path != spec.verification_counter_path
            or verification_work_record.lane is not LaneEnum.OPERATIONAL
            or verification_work_record.value < 1
        ):
            raise TwoStageAccountingV1Error(
                "semantic obligation requires its exact positive operational CounterRecord"
            )
        return cls(
            ordinal,
            artifact_id,
            spec.artifact_schema_id,
            semantic_role.value,
            spec.semantic_verifier_id,
            spec.verification_profile_id,
            spec.verification_counter_path,
            LaneEnum.OPERATIONAL,
            verification_work_record.record_id,
            expected_result,
            verified_at_protocol_step,
            None if binding is None else binding.decision_point_id,
            None if binding is None else binding.transaction_id,
        )

    def to_dict(self) -> dict[str, Any]:
        if self.decision_point_id is None or self.transaction_id is None:
            raise TwoStageAccountingV1Error(
                "unresolved verification obligation cannot be serialized"
            )
        return {
            "ordinal": self.ordinal,
            "artifact_id": self.artifact_id,
            "artifact_schema_id": self.artifact_schema_id,
            "artifact_role": self.artifact_role,
            "semantic_verifier_id": self.semantic_verifier_id,
            "verification_profile_id": self.verification_profile_id,
            "verification_counter_path": self.verification_counter_path,
            "verification_lane": self.verification_lane.value,
            "source_counter_record_id": self.source_counter_record_id,
            "expected_result": self.expected_result,
            "verified_at_protocol_step": self.verified_at_protocol_step,
            "decision_point_id": _ref_dict(self.decision_point_id),
            "transaction_id": _ref_dict(self.transaction_id),
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "VerificationChargeObligationV1":
        expected = {
            "ordinal",
            "artifact_id",
            "artifact_schema_id",
            "artifact_role",
            "semantic_verifier_id",
            "verification_profile_id",
            "verification_counter_path",
            "verification_lane",
            "source_counter_record_id",
            "expected_result",
            "verified_at_protocol_step",
            "decision_point_id",
            "transaction_id",
        }
        _fields(document, expected, "verification charge obligation")
        return cls(
            document["ordinal"],
            document["artifact_id"],
            document["artifact_schema_id"],
            document["artifact_role"],
            document["semantic_verifier_id"],
            document["verification_profile_id"],
            document["verification_counter_path"],
            document["verification_lane"],
            document["source_counter_record_id"],
            document["expected_result"],
            document["verified_at_protocol_step"],
            _parse_content_ref(document["decision_point_id"], "decision_point_id"),
            _parse_content_ref(document["transaction_id"], "transaction_id"),
        )


@dataclass(frozen=True, slots=True)
class FrozenNonsemanticVerificationObligationV1:
    """A prepaid runner check whose result is attested after aggregation.

    The exact source record is frozen before the check.  Its later attestation
    is manifest evidence only and never becomes an input to the vector that it
    certifies, which is the non-self-referential boundary.
    """

    ordinal: int
    check_kind: NonsemanticVerificationCheckKind
    source_counter_record_id: str
    verification_counter_path: str
    verified_at_protocol_step: int

    def __post_init__(self) -> None:
        _nonnegative(self.ordinal, "nonsemantic obligation ordinal")
        object.__setattr__(
            self,
            "check_kind",
            _enum(
                self.check_kind,
                NonsemanticVerificationCheckKind,
                "nonsemantic check kind",
            ),
        )
        _cid(self.source_counter_record_id, "source_counter_record_id")
        _token(self.verification_counter_path, "verification_counter_path")
        _nonnegative(self.verified_at_protocol_step, "verified_at_protocol_step")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "check_kind": self.check_kind.value,
            "source_counter_record_id": self.source_counter_record_id,
            "verification_counter_path": self.verification_counter_path,
            "verified_at_protocol_step": self.verified_at_protocol_step,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "FrozenNonsemanticVerificationObligationV1":
        expected = {
            "ordinal",
            "check_kind",
            "source_counter_record_id",
            "verification_counter_path",
            "verified_at_protocol_step",
        }
        _fields(document, expected, "nonsemantic verification obligation")
        return cls(**document)


@dataclass(frozen=True, slots=True)
class NonsemanticVerificationAttestationV1:
    route_decision_context_id: str
    decision_point_id: ContentRef
    transaction_id: ContentRef
    accounting_core_seal_id: str
    verification_charge_plan_id: str
    obligation_ordinal: int
    check_kind: NonsemanticVerificationCheckKind
    source_counter_record_id: str
    verified_evidence_ids: tuple[str, ...]
    verified_at_protocol_step: int
    verification_result: str = "VALID"

    def __post_init__(self) -> None:
        for field in (
            "route_decision_context_id",
            "accounting_core_seal_id",
            "verification_charge_plan_id",
            "source_counter_record_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self,
            "decision_point_id",
            _content_ref(self.decision_point_id, "decision_point_id"),
        )
        object.__setattr__(
            self,
            "transaction_id",
            _content_ref(self.transaction_id, "transaction_id"),
        )
        _nonnegative(self.obligation_ordinal, "obligation_ordinal")
        object.__setattr__(
            self,
            "check_kind",
            _enum(
                self.check_kind,
                NonsemanticVerificationCheckKind,
                "nonsemantic check kind",
            ),
        )
        if not self.verified_evidence_ids:
            raise TwoStageAccountingV1Error(
                "nonsemantic attestation must bind checked evidence"
            )
        for evidence_id in self.verified_evidence_ids:
            _cid(evidence_id, "verified_evidence_id")
        if (
            tuple(sorted(self.verified_evidence_ids))
            != self.verified_evidence_ids
            or len(set(self.verified_evidence_ids))
            != len(self.verified_evidence_ids)
        ):
            raise TwoStageAccountingV1Error(
                "verified evidence IDs must be unique and sorted"
            )
        _nonnegative(self.verified_at_protocol_step, "verified_at_protocol_step")
        if self.verification_result != "VALID":
            raise TwoStageAccountingV1Error(
                "nonsemantic verification attestation must be VALID"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.nonsemantic_verification_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": _ref_dict(self.decision_point_id),
            "transaction_id": _ref_dict(self.transaction_id),
            "accounting_core_seal_id": self.accounting_core_seal_id,
            "verification_charge_plan_id": self.verification_charge_plan_id,
            "obligation_ordinal": self.obligation_ordinal,
            "check_kind": self.check_kind.value,
            "source_counter_record_id": self.source_counter_record_id,
            "verified_evidence_ids": list(self.verified_evidence_ids),
            "verified_at_protocol_step": self.verified_at_protocol_step,
            "verification_result": self.verification_result,
        }

    @property
    def nonsemantic_verification_attestation_id(self) -> str:
        return content_id(
            NONSEMANTIC_VERIFICATION_ATTESTATION_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "nonsemantic_verification_attestation_id": (
                self.nonsemantic_verification_attestation_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "NonsemanticVerificationAttestationV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "transaction_id",
            "accounting_core_seal_id",
            "verification_charge_plan_id",
            "obligation_ordinal",
            "check_kind",
            "source_counter_record_id",
            "verified_evidence_ids",
            "verified_at_protocol_step",
            "verification_result",
            "nonsemantic_verification_attestation_id",
        }
        _fields(document, expected, "nonsemantic verification attestation")
        if (
            document["schema"]
            != "acfqp.nonsemantic_verification_attestation.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["verified_evidence_ids"]) is not list
        ):
            raise TwoStageAccountingV1Error(
                "nonsemantic-verification-attestation schema mismatch"
            )
        result = cls(
            document["RouteDecisionContext_id"],
            _parse_content_ref(document["decision_point_id"], "decision_point_id"),
            _parse_content_ref(document["transaction_id"], "transaction_id"),
            document["accounting_core_seal_id"],
            document["verification_charge_plan_id"],
            document["obligation_ordinal"],
            document["check_kind"],
            document["source_counter_record_id"],
            tuple(document["verified_evidence_ids"]),
            document["verified_at_protocol_step"],
            document["verification_result"],
        )
        if (
            document["nonsemantic_verification_attestation_id"]
            != result.nonsemantic_verification_attestation_id
        ):
            raise TwoStageAccountingV1Error(
                "nonsemantic-verification-attestation content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class VerificationChargePlanV1:
    route_decision_context_id: str
    decision_point_id: ContentRef
    transaction_id: ContentRef
    accounting_core_seal_id: str
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    route_kind: RouteKindEnum
    subject_id: str
    core_stage: AccountingCoreStage
    plan_frozen_at_protocol_step: int
    obligations: tuple[VerificationChargeObligationV1, ...]
    nonsemantic_obligations: tuple[
        FrozenNonsemanticVerificationObligationV1, ...
    ] = ()

    def __post_init__(self) -> None:
        for field in (
            "route_decision_context_id",
            "accounting_core_seal_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "subject_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self, "decision_point_id", _content_ref(self.decision_point_id, "decision_point_id")
        )
        object.__setattr__(
            self, "transaction_id", _content_ref(self.transaction_id, "transaction_id")
        )
        object.__setattr__(
            self, "route_kind", _enum(self.route_kind, RouteKindEnum, "route_kind")
        )
        object.__setattr__(
            self, "core_stage", _enum(self.core_stage, AccountingCoreStage, "core_stage")
        )
        object.__setattr__(
            self,
            "obligations",
            tuple(
                replace(
                    row,
                    decision_point_id=(
                        self.decision_point_id
                        if row.decision_point_id is None
                        else row.decision_point_id
                    ),
                    transaction_id=(
                        self.transaction_id
                        if row.transaction_id is None
                        else row.transaction_id
                    ),
                )
                for row in self.obligations
            ),
        )
        _nonnegative(self.plan_frozen_at_protocol_step, "plan_frozen_at_protocol_step")
        if not self.obligations:
            raise TwoStageAccountingV1Error("verification charge plan cannot be empty")
        if tuple(row.ordinal for row in self.obligations) != tuple(
            range(len(self.obligations))
        ):
            raise TwoStageAccountingV1Error(
                "verification obligations must use contiguous canonical ordinals"
            )
        keys = tuple((row.artifact_id, row.artifact_role) for row in self.obligations)
        if len(set(keys)) != len(keys):
            raise TwoStageAccountingV1Error(
                "verification plan repeats an artifact-role obligation"
            )
        semantic_source_ids = tuple(
            row.source_counter_record_id for row in self.obligations
        )
        if len(set(semantic_source_ids)) != len(semantic_source_ids):
            raise TwoStageAccountingV1Error(
                "verification plan repeats a semantic source CounterRecord"
            )
        if any(
            row.verified_at_protocol_step <= self.plan_frozen_at_protocol_step
            for row in self.obligations
        ):
            raise TwoStageAccountingV1Error(
                "verification must occur strictly after the charge plan is frozen"
            )
        expected_nonsemantic_ordinals = tuple(
            range(
                len(self.obligations),
                len(self.obligations) + len(self.nonsemantic_obligations),
            )
        )
        if tuple(
            row.ordinal for row in self.nonsemantic_obligations
        ) != expected_nonsemantic_ordinals:
            raise TwoStageAccountingV1Error(
                "nonsemantic obligations must continue canonical plan ordinals"
            )
        source_ids = tuple(
            row.source_counter_record_id for row in self.nonsemantic_obligations
        )
        if len(set(source_ids)) != len(source_ids):
            raise TwoStageAccountingV1Error(
                "nonsemantic obligations repeat a source CounterRecord"
            )
        if set(source_ids) & set(semantic_source_ids):
            raise TwoStageAccountingV1Error(
                "semantic and nonsemantic obligations reuse one CounterRecord"
            )
        if any(
            row.verified_at_protocol_step <= self.plan_frozen_at_protocol_step
            for row in self.nonsemantic_obligations
        ):
            raise TwoStageAccountingV1Error(
                "nonsemantic checks must follow charge-plan freeze"
            )

    @classmethod
    def for_core(
        cls,
        core: SealedAccountingCoreV1,
        *,
        plan_frozen_at_protocol_step: int,
        obligations: Sequence[VerificationChargeObligationV1],
        nonsemantic_obligations: Sequence[
            FrozenNonsemanticVerificationObligationV1
        ] = (),
    ) -> "VerificationChargePlanV1":
        result = cls(
            core.route_decision_context_id,
            core.decision_point_id,
            core.transaction_id,
            core.accounting_core_seal_id,
            core.counter_registry_id,
            core.comparison_profile_id,
            core.actual_projection_profile_id,
            core.route_kind,
            core.subject_id,
            core.core_stage,
            plan_frozen_at_protocol_step,
            tuple(obligations),
            tuple(nonsemantic_obligations),
        )
        _validate_plan_core(result, core)
        return result

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verification_charge_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": _ref_dict(self.decision_point_id),
            "transaction_id": _ref_dict(self.transaction_id),
            "accounting_core_seal_id": self.accounting_core_seal_id,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "route_kind": self.route_kind.value,
            "subject_id": self.subject_id,
            "core_stage": self.core_stage.value,
            "plan_frozen_at_protocol_step": self.plan_frozen_at_protocol_step,
            "obligations": [row.to_dict() for row in self.obligations],
            "nonsemantic_obligations": [
                row.to_dict() for row in self.nonsemantic_obligations
            ],
        }

    @property
    def verification_charge_plan_id(self) -> str:
        return content_id(VERIFICATION_CHARGE_PLAN_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "verification_charge_plan_id": self.verification_charge_plan_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "VerificationChargePlanV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "transaction_id",
            "accounting_core_seal_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "route_kind",
            "subject_id",
            "core_stage",
            "plan_frozen_at_protocol_step",
            "obligations",
            "nonsemantic_obligations",
            "verification_charge_plan_id",
        }
        _fields(document, expected, "verification charge plan")
        if (
            document["schema"] != "acfqp.verification_charge_plan.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["obligations"]) is not list
            or type(document["nonsemantic_obligations"]) is not list
        ):
            raise TwoStageAccountingV1Error("verification-charge-plan schema mismatch")
        result = cls(
            document["RouteDecisionContext_id"],
            _parse_content_ref(document["decision_point_id"], "decision_point_id"),
            _parse_content_ref(document["transaction_id"], "transaction_id"),
            document["accounting_core_seal_id"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["actual_projection_profile_id"],
            document["route_kind"],
            document["subject_id"],
            document["core_stage"],
            document["plan_frozen_at_protocol_step"],
            tuple(VerificationChargeObligationV1.from_dict(row) for row in document["obligations"]),
            tuple(
                FrozenNonsemanticVerificationObligationV1.from_dict(row)
                for row in document["nonsemantic_obligations"]
            ),
        )
        if document["verification_charge_plan_id"] != result.verification_charge_plan_id:
            raise TwoStageAccountingV1Error("verification-charge-plan content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class VerificationChargeEntryV1:
    obligation_ordinal: int
    artifact_id: str
    artifact_role: str
    source_counter_record_id: str
    semantic_attestation_id: str

    def __post_init__(self) -> None:
        _nonnegative(self.obligation_ordinal, "obligation_ordinal")
        _cid(self.artifact_id, "artifact_id")
        _token(self.artifact_role, "artifact_role")
        _cid(self.source_counter_record_id, "source_counter_record_id")
        _cid(self.semantic_attestation_id, "semantic_attestation_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verification_charge_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "obligation_ordinal": self.obligation_ordinal,
            "artifact_id": self.artifact_id,
            "artifact_role": self.artifact_role,
            "source_counter_record_id": self.source_counter_record_id,
            "semantic_attestation_id": self.semantic_attestation_id,
        }

    @property
    def verification_charge_entry_id(self) -> str:
        return content_id(VERIFICATION_CHARGE_ENTRY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "verification_charge_entry_id": self.verification_charge_entry_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "VerificationChargeEntryV1":
        expected = {
            "schema",
            "schema_version",
            "obligation_ordinal",
            "artifact_id",
            "artifact_role",
            "source_counter_record_id",
            "semantic_attestation_id",
            "verification_charge_entry_id",
        }
        _fields(document, expected, "verification charge entry")
        if (
            document["schema"] != "acfqp.verification_charge_entry.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise TwoStageAccountingV1Error("verification-charge-entry schema mismatch")
        result = cls(
            document["obligation_ordinal"],
            document["artifact_id"],
            document["artifact_role"],
            document["source_counter_record_id"],
            document["semantic_attestation_id"],
        )
        if document["verification_charge_entry_id"] != result.verification_charge_entry_id:
            raise TwoStageAccountingV1Error("verification-charge-entry content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class NonsemanticVerificationChargeEntryV1:
    obligation_ordinal: int
    check_kind: NonsemanticVerificationCheckKind
    source_counter_record_id: str
    nonsemantic_attestation_id: str

    def __post_init__(self) -> None:
        _nonnegative(self.obligation_ordinal, "obligation_ordinal")
        object.__setattr__(
            self,
            "check_kind",
            _enum(
                self.check_kind,
                NonsemanticVerificationCheckKind,
                "nonsemantic check kind",
            ),
        )
        _cid(self.source_counter_record_id, "source_counter_record_id")
        _cid(self.nonsemantic_attestation_id, "nonsemantic_attestation_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.nonsemantic_verification_charge_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "obligation_ordinal": self.obligation_ordinal,
            "check_kind": self.check_kind.value,
            "source_counter_record_id": self.source_counter_record_id,
            "nonsemantic_attestation_id": self.nonsemantic_attestation_id,
        }

    @property
    def verification_charge_entry_id(self) -> str:
        return content_id(VERIFICATION_CHARGE_ENTRY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_charge_entry_id": self.verification_charge_entry_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "NonsemanticVerificationChargeEntryV1":
        expected = {
            "schema",
            "schema_version",
            "obligation_ordinal",
            "check_kind",
            "source_counter_record_id",
            "nonsemantic_attestation_id",
            "verification_charge_entry_id",
        }
        _fields(document, expected, "nonsemantic verification charge entry")
        if (
            document["schema"]
            != "acfqp.nonsemantic_verification_charge_entry.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise TwoStageAccountingV1Error(
                "nonsemantic-verification-charge-entry schema mismatch"
            )
        result = cls(
            document["obligation_ordinal"],
            document["check_kind"],
            document["source_counter_record_id"],
            document["nonsemantic_attestation_id"],
        )
        if document["verification_charge_entry_id"] != result.verification_charge_entry_id:
            raise TwoStageAccountingV1Error(
                "nonsemantic-verification-charge-entry content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class TwoStageWorkAggregateV1:
    route_decision_context_id: str
    decision_point_id: ContentRef
    transaction_id: ContentRef
    accounting_core_seal_id: str
    verification_charge_plan_id: str
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    route_kind: RouteKindEnum
    subject_id: str
    core_work_vector_id: str
    core_comparison_vector_id: str
    core_projection_proof_id: str
    verification_suffix_work_vector_id: str
    verification_suffix_comparison_vector_id: str
    verification_suffix_projection_proof_id: str
    aggregate_work_vector_id: str
    aggregate_comparison_vector_id: str
    aggregate_projection_proof_id: str

    def __post_init__(self) -> None:
        for field in (
            "route_decision_context_id",
            "accounting_core_seal_id",
            "verification_charge_plan_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "route_kind",
            "subject_id",
            "core_work_vector_id",
            "core_comparison_vector_id",
            "core_projection_proof_id",
            "verification_suffix_work_vector_id",
            "verification_suffix_comparison_vector_id",
            "verification_suffix_projection_proof_id",
            "aggregate_work_vector_id",
            "aggregate_comparison_vector_id",
            "aggregate_projection_proof_id",
        ):
            if field == "route_kind":
                continue
            _cid(getattr(self, field), field)
        object.__setattr__(
            self, "decision_point_id", _content_ref(self.decision_point_id, "decision_point_id")
        )
        object.__setattr__(
            self, "transaction_id", _content_ref(self.transaction_id, "transaction_id")
        )
        object.__setattr__(
            self, "route_kind", _enum(self.route_kind, RouteKindEnum, "route_kind")
        )
        works = (
            self.core_work_vector_id,
            self.verification_suffix_work_vector_id,
            self.aggregate_work_vector_id,
        )
        if len(set(works)) != len(works):
            raise TwoStageAccountingV1Error("two-stage aggregate aliases work stages")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.two_stage_work_aggregate.v1",
            "schema_version": SCHEMA_VERSION,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": _ref_dict(self.decision_point_id),
            "transaction_id": _ref_dict(self.transaction_id),
            "accounting_core_seal_id": self.accounting_core_seal_id,
            "verification_charge_plan_id": self.verification_charge_plan_id,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "route_kind": self.route_kind.value,
            "subject_id": self.subject_id,
            "core_work_vector_id": self.core_work_vector_id,
            "core_comparison_vector_id": self.core_comparison_vector_id,
            "core_projection_proof_id": self.core_projection_proof_id,
            "verification_suffix_work_vector_id": self.verification_suffix_work_vector_id,
            "verification_suffix_comparison_vector_id": self.verification_suffix_comparison_vector_id,
            "verification_suffix_projection_proof_id": self.verification_suffix_projection_proof_id,
            "aggregate_work_vector_id": self.aggregate_work_vector_id,
            "aggregate_comparison_vector_id": self.aggregate_comparison_vector_id,
            "aggregate_projection_proof_id": self.aggregate_projection_proof_id,
        }

    @property
    def two_stage_work_aggregate_id(self) -> str:
        return content_id(TWO_STAGE_WORK_AGGREGATE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "two_stage_work_aggregate_id": self.two_stage_work_aggregate_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "TwoStageWorkAggregateV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "transaction_id",
            "accounting_core_seal_id",
            "verification_charge_plan_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "route_kind",
            "subject_id",
            "core_work_vector_id",
            "core_comparison_vector_id",
            "core_projection_proof_id",
            "verification_suffix_work_vector_id",
            "verification_suffix_comparison_vector_id",
            "verification_suffix_projection_proof_id",
            "aggregate_work_vector_id",
            "aggregate_comparison_vector_id",
            "aggregate_projection_proof_id",
            "two_stage_work_aggregate_id",
        }
        _fields(document, expected, "two-stage work aggregate")
        if (
            document["schema"] != "acfqp.two_stage_work_aggregate.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise TwoStageAccountingV1Error("two-stage-work-aggregate schema mismatch")
        result = cls(
            document["RouteDecisionContext_id"],
            _parse_content_ref(document["decision_point_id"], "decision_point_id"),
            _parse_content_ref(document["transaction_id"], "transaction_id"),
            document["accounting_core_seal_id"],
            document["verification_charge_plan_id"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["actual_projection_profile_id"],
            document["route_kind"],
            document["subject_id"],
            document["core_work_vector_id"],
            document["core_comparison_vector_id"],
            document["core_projection_proof_id"],
            document["verification_suffix_work_vector_id"],
            document["verification_suffix_comparison_vector_id"],
            document["verification_suffix_projection_proof_id"],
            document["aggregate_work_vector_id"],
            document["aggregate_comparison_vector_id"],
            document["aggregate_projection_proof_id"],
        )
        if document["two_stage_work_aggregate_id"] != result.two_stage_work_aggregate_id:
            raise TwoStageAccountingV1Error("two-stage-work-aggregate content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class VerificationChargeManifestV1:
    route_decision_context_id: str
    decision_point_id: ContentRef
    transaction_id: ContentRef
    accounting_core_seal_id: str
    verification_charge_plan_id: str
    entries: tuple[VerificationChargeEntryV1, ...]
    nonsemantic_entries: tuple[NonsemanticVerificationChargeEntryV1, ...]
    verification_suffix_work_vector_id: str
    verification_suffix_comparison_vector_id: str
    verification_suffix_projection_proof_id: str
    aggregate_work_vector_id: str
    aggregate_comparison_vector_id: str
    aggregate_projection_proof_id: str
    two_stage_work_aggregate_id: str

    def __post_init__(self) -> None:
        for field in (
            "route_decision_context_id",
            "accounting_core_seal_id",
            "verification_charge_plan_id",
            "verification_suffix_work_vector_id",
            "verification_suffix_comparison_vector_id",
            "verification_suffix_projection_proof_id",
            "aggregate_work_vector_id",
            "aggregate_comparison_vector_id",
            "aggregate_projection_proof_id",
            "two_stage_work_aggregate_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self, "decision_point_id", _content_ref(self.decision_point_id, "decision_point_id")
        )
        object.__setattr__(
            self, "transaction_id", _content_ref(self.transaction_id, "transaction_id")
        )
        if tuple(row.obligation_ordinal for row in self.entries) != tuple(
            range(len(self.entries))
        ):
            raise TwoStageAccountingV1Error(
                "semantic manifest entries must use contiguous obligation ordinals"
            )
        if tuple(
            row.obligation_ordinal for row in self.nonsemantic_entries
        ) != tuple(
            range(
                len(self.entries),
                len(self.entries) + len(self.nonsemantic_entries),
            )
        ):
            raise TwoStageAccountingV1Error(
                "nonsemantic manifest entries must continue obligation ordinals"
            )
        if not self.entries and not self.nonsemantic_entries:
            raise TwoStageAccountingV1Error("verification manifest cannot be empty")
        for field, values in (
            ("source CounterRecord", tuple(row.source_counter_record_id for row in self.entries)),
            ("semantic attestation", tuple(row.semantic_attestation_id for row in self.entries)),
            ("artifact-role", tuple((row.artifact_id, row.artifact_role) for row in self.entries)),
        ):
            if len(set(values)) != len(values):
                raise TwoStageAccountingV1Error(f"manifest repeats a {field}")
        nonsemantic_source_ids = tuple(
            row.source_counter_record_id for row in self.nonsemantic_entries
        )
        nonsemantic_attestation_ids = tuple(
            row.nonsemantic_attestation_id for row in self.nonsemantic_entries
        )
        if len(set(nonsemantic_source_ids)) != len(nonsemantic_source_ids):
            raise TwoStageAccountingV1Error(
                "manifest repeats a nonsemantic source CounterRecord"
            )
        if len(set(nonsemantic_attestation_ids)) != len(
            nonsemantic_attestation_ids
        ):
            raise TwoStageAccountingV1Error(
                "manifest repeats a nonsemantic attestation"
            )
        if set(nonsemantic_source_ids) & {
            row.source_counter_record_id for row in self.entries
        }:
            raise TwoStageAccountingV1Error(
                "semantic and nonsemantic charges reuse one CounterRecord"
            )

    @property
    def source_counter_record_ids(self) -> tuple[str, ...]:
        return tuple(row.source_counter_record_id for row in self.entries) + tuple(
            row.source_counter_record_id for row in self.nonsemantic_entries
        )

    @property
    def semantic_attestation_ids(self) -> tuple[str, ...]:
        return tuple(row.semantic_attestation_id for row in self.entries)

    @property
    def nonsemantic_attestation_ids(self) -> tuple[str, ...]:
        return tuple(
            row.nonsemantic_attestation_id for row in self.nonsemantic_entries
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verification_charge_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": _ref_dict(self.decision_point_id),
            "transaction_id": _ref_dict(self.transaction_id),
            "accounting_core_seal_id": self.accounting_core_seal_id,
            "verification_charge_plan_id": self.verification_charge_plan_id,
            "verification_charge_entry_ids": [
                row.verification_charge_entry_id for row in self.entries
            ],
            "nonsemantic_verification_charge_entry_ids": [
                row.verification_charge_entry_id
                for row in self.nonsemantic_entries
            ],
            "verification_suffix_work_vector_id": self.verification_suffix_work_vector_id,
            "verification_suffix_comparison_vector_id": self.verification_suffix_comparison_vector_id,
            "verification_suffix_projection_proof_id": self.verification_suffix_projection_proof_id,
            "aggregate_work_vector_id": self.aggregate_work_vector_id,
            "aggregate_comparison_vector_id": self.aggregate_comparison_vector_id,
            "aggregate_projection_proof_id": self.aggregate_projection_proof_id,
            "two_stage_work_aggregate_id": self.two_stage_work_aggregate_id,
        }

    @property
    def verification_charge_manifest_id(self) -> str:
        return content_id(VERIFICATION_CHARGE_MANIFEST_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [row.to_dict() for row in self.entries],
            "nonsemantic_entries": [
                row.to_dict() for row in self.nonsemantic_entries
            ],
            "verification_charge_manifest_id": self.verification_charge_manifest_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "VerificationChargeManifestV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "transaction_id",
            "accounting_core_seal_id",
            "verification_charge_plan_id",
            "verification_charge_entry_ids",
            "nonsemantic_verification_charge_entry_ids",
            "entries",
            "nonsemantic_entries",
            "verification_suffix_work_vector_id",
            "verification_suffix_comparison_vector_id",
            "verification_suffix_projection_proof_id",
            "aggregate_work_vector_id",
            "aggregate_comparison_vector_id",
            "aggregate_projection_proof_id",
            "two_stage_work_aggregate_id",
            "verification_charge_manifest_id",
        }
        _fields(document, expected, "verification charge manifest")
        if (
            document["schema"] != "acfqp.verification_charge_manifest.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["verification_charge_entry_ids"]) is not list
            or type(document["nonsemantic_verification_charge_entry_ids"])
            is not list
            or type(document["entries"]) is not list
            or type(document["nonsemantic_entries"]) is not list
        ):
            raise TwoStageAccountingV1Error("verification-charge-manifest schema mismatch")
        entries = tuple(VerificationChargeEntryV1.from_dict(row) for row in document["entries"])
        nonsemantic_entries = tuple(
            NonsemanticVerificationChargeEntryV1.from_dict(row)
            for row in document["nonsemantic_entries"]
        )
        if document["verification_charge_entry_ids"] != [
            row.verification_charge_entry_id for row in entries
        ]:
            raise TwoStageAccountingV1Error("manifest entry ID list mismatch")
        if document["nonsemantic_verification_charge_entry_ids"] != [
            row.verification_charge_entry_id for row in nonsemantic_entries
        ]:
            raise TwoStageAccountingV1Error(
                "manifest nonsemantic entry ID list mismatch"
            )
        result = cls(
            document["RouteDecisionContext_id"],
            _parse_content_ref(document["decision_point_id"], "decision_point_id"),
            _parse_content_ref(document["transaction_id"], "transaction_id"),
            document["accounting_core_seal_id"],
            document["verification_charge_plan_id"],
            entries,
            nonsemantic_entries,
            document["verification_suffix_work_vector_id"],
            document["verification_suffix_comparison_vector_id"],
            document["verification_suffix_projection_proof_id"],
            document["aggregate_work_vector_id"],
            document["aggregate_comparison_vector_id"],
            document["aggregate_projection_proof_id"],
            document["two_stage_work_aggregate_id"],
        )
        if document["verification_charge_manifest_id"] != result.verification_charge_manifest_id:
            raise TwoStageAccountingV1Error("verification-charge-manifest content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class VerificationChargeReceiptV1:
    verification_charge_manifest_id: str
    verification_charge_plan_id: str
    accounting_core_seal_id: str
    two_stage_work_aggregate_id: str
    replayed_source_counter_record_ids: tuple[str, ...]
    replayed_semantic_attestation_ids: tuple[str, ...]
    replayed_nonsemantic_attestation_ids: tuple[str, ...]
    destination_suffix_work_vector_id: str
    destination_aggregate_work_vector_id: str
    verification_result: str = "VALID"

    def __post_init__(self) -> None:
        for field in (
            "verification_charge_manifest_id",
            "verification_charge_plan_id",
            "accounting_core_seal_id",
            "two_stage_work_aggregate_id",
            "destination_suffix_work_vector_id",
            "destination_aggregate_work_vector_id",
        ):
            _cid(getattr(self, field), field)
        for name, values in (
            ("source CounterRecord", self.replayed_source_counter_record_ids),
        ):
            if not values:
                raise TwoStageAccountingV1Error(f"receipt has no replayed {name} IDs")
            for value in values:
                _cid(value, name)
            if len(set(values)) != len(values):
                raise TwoStageAccountingV1Error(f"receipt repeats a {name} ID")
        all_attestations = (
            self.replayed_semantic_attestation_ids
            + self.replayed_nonsemantic_attestation_ids
        )
        if not all_attestations:
            raise TwoStageAccountingV1Error(
                "receipt has no replayed verification attestations"
            )
        for value in all_attestations:
            _cid(value, "verification attestation")
        if len(set(all_attestations)) != len(all_attestations):
            raise TwoStageAccountingV1Error(
                "receipt repeats a verification attestation ID"
            )
        if self.verification_result != "VALID":
            raise TwoStageAccountingV1Error("verification receipt result must be VALID")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verification_charge_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "verification_charge_manifest_id": self.verification_charge_manifest_id,
            "verification_charge_plan_id": self.verification_charge_plan_id,
            "accounting_core_seal_id": self.accounting_core_seal_id,
            "two_stage_work_aggregate_id": self.two_stage_work_aggregate_id,
            "replayed_source_counter_record_ids": list(self.replayed_source_counter_record_ids),
            "replayed_semantic_attestation_ids": list(self.replayed_semantic_attestation_ids),
            "replayed_nonsemantic_attestation_ids": list(
                self.replayed_nonsemantic_attestation_ids
            ),
            "destination_suffix_work_vector_id": self.destination_suffix_work_vector_id,
            "destination_aggregate_work_vector_id": self.destination_aggregate_work_vector_id,
            "verification_result": self.verification_result,
        }

    @property
    def verification_charge_receipt_id(self) -> str:
        return content_id(VERIFICATION_CHARGE_RECEIPT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "verification_charge_receipt_id": self.verification_charge_receipt_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "VerificationChargeReceiptV1":
        expected = {
            "schema",
            "schema_version",
            "verification_charge_manifest_id",
            "verification_charge_plan_id",
            "accounting_core_seal_id",
            "two_stage_work_aggregate_id",
            "replayed_source_counter_record_ids",
            "replayed_semantic_attestation_ids",
            "replayed_nonsemantic_attestation_ids",
            "destination_suffix_work_vector_id",
            "destination_aggregate_work_vector_id",
            "verification_result",
            "verification_charge_receipt_id",
        }
        _fields(document, expected, "verification charge receipt")
        if (
            document["schema"] != "acfqp.verification_charge_receipt.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["replayed_source_counter_record_ids"]) is not list
            or type(document["replayed_semantic_attestation_ids"]) is not list
            or type(document["replayed_nonsemantic_attestation_ids"])
            is not list
        ):
            raise TwoStageAccountingV1Error("verification-charge-receipt schema mismatch")
        result = cls(
            document["verification_charge_manifest_id"],
            document["verification_charge_plan_id"],
            document["accounting_core_seal_id"],
            document["two_stage_work_aggregate_id"],
            tuple(document["replayed_source_counter_record_ids"]),
            tuple(document["replayed_semantic_attestation_ids"]),
            tuple(document["replayed_nonsemantic_attestation_ids"]),
            document["destination_suffix_work_vector_id"],
            document["destination_aggregate_work_vector_id"],
            document["verification_result"],
        )
        if document["verification_charge_receipt_id"] != result.verification_charge_receipt_id:
            raise TwoStageAccountingV1Error("verification-charge-receipt content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class TwoStageAccountingClosureV1:
    core: SealedAccountingCoreV1
    plan: VerificationChargePlanV1
    nonsemantic_evidence: tuple[NonsemanticVerificationEvidenceV1, ...]
    nonsemantic_attestations: tuple[NonsemanticVerificationAttestationV1, ...]
    verification_suffix: RecordedWorkV1
    aggregate_work: RecordedWorkV1
    aggregate: TwoStageWorkAggregateV1
    manifest: VerificationChargeManifestV1
    receipt: VerificationChargeReceiptV1


def _materialize_values(
    *,
    values: Mapping[str, int],
    subject_id: str,
    route_kind: RouteKindEnum,
    work_scope: ActualWorkScope,
    recorder_id: str,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> RecordedWorkV1:
    try:
        records = explicit_records_v1(
            registry, values, recorder_id=recorder_id
        )
        vector = registry.materialize(
            subject_id=subject_id,
            route_kind=route_kind,
            records=records,
        )
        comparison, proof = derive_actual_projection_v1(
            vector,
            registry,
            comparison_profile,
            actual_profile,
            source_lane=LaneEnum.OPERATIONAL,
            work_scope=work_scope,
        )
        return RecordedWorkV1(
            vector,
            NativeZeroAttestationV1.derive(vector, registry),
            ReconciliationProofV1.derive(vector, registry),
            comparison,
            proof,
        )
    except ValueError as error:
        raise TwoStageAccountingV1Error(str(error)) from error


def _merge_value(
    values: dict[str, int], record: CounterRecordV1, registry: CounterRegistryV1
) -> None:
    try:
        leaf = registry.by_path[record.path]
        if record.counter_registry_id != registry.registry_id:
            raise TwoStageAccountingV1Error(
                "verification source record uses another counter registry"
            )
        record.verify_against(leaf)
    except (KeyError, ValueError) as error:
        if isinstance(error, TwoStageAccountingV1Error):
            raise
        raise TwoStageAccountingV1Error(
            f"invalid verification source CounterRecordV1: {error}"
        ) from error
    if leaf.lane is not LaneEnum.OPERATIONAL:
        raise TwoStageAccountingV1Error(
            "only operational semantic-verification work enters the suffix"
        )
    _positive(record.value, "semantic verification work")
    if leaf.reducer is ReducerEnum.SUM:
        values[record.path] += record.value
    else:
        values[record.path] = max(values[record.path], record.value)


def _validate_plan_core(plan: VerificationChargePlanV1, core: SealedAccountingCoreV1) -> None:
    expected = (
        core.route_decision_context_id,
        core.decision_point_id,
        core.transaction_id,
        core.accounting_core_seal_id,
        core.counter_registry_id,
        core.comparison_profile_id,
        core.actual_projection_profile_id,
        core.route_kind,
        core.subject_id,
        core.core_stage,
    )
    actual = (
        plan.route_decision_context_id,
        plan.decision_point_id,
        plan.transaction_id,
        plan.accounting_core_seal_id,
        plan.counter_registry_id,
        plan.comparison_profile_id,
        plan.actual_projection_profile_id,
        plan.route_kind,
        plan.subject_id,
        plan.core_stage,
    )
    if actual != expected:
        raise TwoStageAccountingV1Error("verification plan is stale for the sealed core")
    source_ids = {
        row.source_counter_record_id
        for row in (*plan.obligations, *plan.nonsemantic_obligations)
    }
    overlap = source_ids & set(core.core_counter_record_ids)
    if overlap:
        raise TwoStageAccountingV1Error(
            "verification plan reuses a sealed-core CounterRecord"
        )


def _result_entries(
    *,
    plan: VerificationChargePlanV1,
    results: Sequence[SemanticVerificationResultV1],
    registry: CounterRegistryV1,
) -> tuple[tuple[VerificationChargeEntryV1, ...], tuple[CounterRecordV1, ...]]:
    if len(results) != len(plan.obligations):
        raise TwoStageAccountingV1Error(
            "semantic result set does not exactly cover the frozen obligations"
        )
    by_key: dict[tuple[str, str], SemanticVerificationResultV1] = {}
    for result in results:
        if not isinstance(result, SemanticVerificationResultV1):
            raise TwoStageAccountingV1Error(
                "verification charges require authority-bearing semantic results"
            )
        key = (result.attestation.artifact_id, result.attestation.artifact_role)
        if key in by_key:
            raise TwoStageAccountingV1Error("semantic result set repeats an artifact-role")
        by_key[key] = result

    entries: list[VerificationChargeEntryV1] = []
    records: list[CounterRecordV1] = []
    for obligation in plan.obligations:
        key = (obligation.artifact_id, obligation.artifact_role)
        try:
            result = by_key.pop(key)
        except KeyError as error:
            raise TwoStageAccountingV1Error(
                "semantic result substituted or omitted a frozen obligation"
            ) from error
        attestation = result.attestation
        record = result.verification_work_record
        binding = result.binding
        if (
            binding.route_context.route_decision_context_id
            != plan.route_decision_context_id
            or attestation.route_decision_context_id
            != plan.route_decision_context_id
            or obligation.decision_point_id is None
            or obligation.transaction_id is None
            or not _same_ref(
                binding.decision_point_id, obligation.decision_point_id
            )
            or not _same_ref(
                attestation.decision_point_id, obligation.decision_point_id
            )
            or not _same_ref(binding.transaction_id, obligation.transaction_id)
            or not _same_ref(
                attestation.transaction_id, obligation.transaction_id
            )
        ):
            raise TwoStageAccountingV1Error(
                "semantic verification result was reused across accounting contexts"
            )
        expected_metadata = (
            obligation.artifact_schema_id,
            obligation.semantic_verifier_id,
            obligation.verification_profile_id,
            obligation.expected_result,
            obligation.verified_at_protocol_step,
            obligation.verification_counter_path,
            obligation.verification_lane,
            obligation.source_counter_record_id,
        )
        actual_metadata = (
            attestation.artifact_schema_id,
            attestation.semantic_verifier_id,
            attestation.verification_profile_id,
            attestation.verification_result,
            attestation.verified_at_protocol_step,
            record.path,
            attestation.verification_lane,
            record.record_id,
        )
        if actual_metadata != expected_metadata:
            raise TwoStageAccountingV1Error(
                "semantic result does not match its frozen verification obligation"
            )
        if result.binding.verification_lane is not obligation.verification_lane:
            raise TwoStageAccountingV1Error(
                "semantic result invocation lane differs from the frozen obligation"
            )
        if attestation.verification_work_counter_record_id != record.record_id:
            raise TwoStageAccountingV1Error(
                "semantic attestation substituted its source CounterRecord"
            )
        _merge_value(
            {path: 0 for path in registry.required_paths}, record, registry
        )
        entries.append(
            VerificationChargeEntryV1(
                obligation.ordinal,
                obligation.artifact_id,
                obligation.artifact_role,
                record.record_id,
                attestation.verification_attestation_id,
            )
        )
        records.append(record)
    if by_key:
        raise TwoStageAccountingV1Error("semantic result set contains padding")
    if len({row.record_id for row in records}) != len(records):
        raise TwoStageAccountingV1Error(
            "one source CounterRecord cannot pay for multiple semantic attestations"
        )
    if len({row.semantic_attestation_id for row in entries}) != len(entries):
        raise TwoStageAccountingV1Error("semantic attestation was duplicated")
    return tuple(entries), tuple(records)


def _registered_nonsemantic_evidence_ids_v1(
    *,
    core: SealedAccountingCoreV1,
    core_work: RecordedWorkV1,
    obligation: FrozenNonsemanticVerificationObligationV1,
    evidence: NonsemanticVerificationEvidenceV1,
    aggregate: TwoStageWorkAggregateV1,
    suffix: RecordedWorkV1,
    aggregate_work: RecordedWorkV1,
    route_context: RouteDecisionContextV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> tuple[str, ...]:
    """Replay one closed-registry nonsemantic check from typed evidence.

    Returning caller-selected content IDs is intentionally impossible.  Each
    branch recomputes the check from the concrete objects registered for that
    ``check_kind`` and only then derives the canonical evidence-ID tuple.
    """

    kind = obligation.check_kind
    try:
        if kind is NonsemanticVerificationCheckKind.ACCESS_TRACE_RECONCILIATION:
            if type(evidence) is not AccessTraceReconciliationEvidenceV1:
                raise TwoStageAccountingV1Error(
                    "access reconciliation requires typed access evidence"
                )
            if (
                type(evidence.access_log) is not AccessEventLogV1
                or type(evidence.freeze_attestation)
                is not RouteDecisionFreezeAttestationV1
                or type(evidence.protocol_profile)
                is not ProtocolSequenceProfileV1
                or type(evidence.execution_work) is not RecordedWorkV1
                or evidence.execution_work != core_work
            ):
                raise TwoStageAccountingV1Error(
                    "access reconciliation evidence is stale or substituted"
                )
            selected = RouteSelection(evidence.selected_route)
            expected_route_kind = _route_kind_for_selection_v1(selected)
            if (
                evidence.access_log.route_attempt_id
                != route_context.route_attempt_id
                or evidence.access_log.decision_point_id
                != core.decision_point_id
                or evidence.freeze_attestation.selected_route is not selected
                or core.route_kind is not expected_route_kind
            ):
                raise TwoStageAccountingV1Error(
                    "access reconciliation evidence uses another route binding"
                )
            replay_access_protocol(
                evidence.access_log,
                evidence.protocol_profile,
                decision_result=evidence.decision_result,
                freeze_attestation=evidence.freeze_attestation,
            )
            # These route-semantic checks live in the runner to avoid moving
            # executor-domain types into the accounting layer.  They are
            # imported only at verification time, after that module is fully
            # initialized, and receive the typed evidence rather than IDs.
            from acfqp.phase3e_runner_v1 import (
                Phase3ERouteExecutionV1,
                _reconcile_access_and_native_counters,
                _require_selected_access_trace,
            )

            if type(evidence.execution) is not Phase3ERouteExecutionV1:
                raise TwoStageAccountingV1Error(
                    "access reconciliation lacks typed route execution"
                )
            boundary = evidence.freeze_attestation.last_preselection_sequence
            _require_selected_access_trace(
                selected=selected,
                execution=evidence.execution,
                log=evidence.access_log,
                freeze_after_sequence=boundary,
            )
            _reconcile_access_and_native_counters(
                selected=selected,
                log=evidence.access_log,
                work=evidence.execution_work,
            )
            return tuple(
                sorted(
                    (
                        evidence.access_log.access_event_log_id,
                        evidence.freeze_attestation.route_decision_freeze_attestation_id,
                    )
                )
            )

        if kind is NonsemanticVerificationCheckKind.EXECUTION_VECTOR_INTEGRITY:
            if (
                type(evidence) is not ExecutionVectorIntegrityEvidenceV1
                or type(evidence.execution_work) is not RecordedWorkV1
                or evidence.execution_work != core_work
            ):
                raise TwoStageAccountingV1Error(
                    "execution-integrity evidence is stale or substituted"
                )
            _verify_recorded_work(
                evidence.execution_work,
                registry=registry,
                comparison_profile=comparison_profile,
                actual_profile=actual_profile,
            )
            return tuple(
                sorted(
                    (
                        core.core_work_vector_id,
                        core.core_projection_proof_id,
                    )
                )
            )

        if kind is NonsemanticVerificationCheckKind.NATIVE_AGGREGATION:
            if type(evidence) is not NativeAggregationEvidenceV1:
                raise TwoStageAccountingV1Error(
                    "native aggregation requires typed aggregation evidence"
                )
            expected_values: dict[str, int] = {}
            for path in registry.required_paths:
                leaf = registry.by_path[path]
                left = core_work.work_vector.value(path)
                right = suffix.work_vector.value(path)
                expected_values[path] = (
                    left + right
                    if leaf.reducer is ReducerEnum.SUM
                    else max(left, right)
                )
            if aggregate_work.work_vector.values != expected_values:
                raise TwoStageAccountingV1Error(
                    "native aggregate values differ from core/suffix replay"
                )
            expected_binding = (
                core.core_work_vector_id,
                core.core_comparison_vector_id,
                core.core_projection_proof_id,
                suffix.work_vector.work_vector_id,
                suffix.comparison_vector.comparison_vector_id,
                suffix.actual_projection_proof.actual_projection_proof_id,
                aggregate_work.work_vector.work_vector_id,
                aggregate_work.comparison_vector.comparison_vector_id,
                aggregate_work.actual_projection_proof.actual_projection_proof_id,
            )
            actual_binding = (
                aggregate.core_work_vector_id,
                aggregate.core_comparison_vector_id,
                aggregate.core_projection_proof_id,
                aggregate.verification_suffix_work_vector_id,
                aggregate.verification_suffix_comparison_vector_id,
                aggregate.verification_suffix_projection_proof_id,
                aggregate.aggregate_work_vector_id,
                aggregate.aggregate_comparison_vector_id,
                aggregate.aggregate_projection_proof_id,
            )
            if actual_binding != expected_binding:
                raise TwoStageAccountingV1Error(
                    "two-stage aggregate substituted a native source or result"
                )
            if core.core_stage is AccountingCoreStage.ROUTE_EXECUTION:
                if type(evidence.independent_aggregate) is not AggregatedMarginalWorkV1:
                    raise TwoStageAccountingV1Error(
                        "route aggregation lacks an independent marginal replay"
                    )
                replayed = derive_marginal_work_aggregate_v1(
                    subject_id=core.subject_id,
                    route_kind=core.route_kind,
                    execution=(
                        core_work.work_vector,
                        core_work.comparison_vector,
                        core_work.actual_projection_proof,
                    ),
                    verification_suffix=(
                        suffix.work_vector,
                        suffix.comparison_vector,
                        suffix.actual_projection_proof,
                    ),
                    registry=registry,
                    comparison_profile=comparison_profile,
                    actual_profile=actual_profile,
                )
                if (
                    evidence.independent_aggregate != replayed
                    or replayed.aggregate_work_vector != aggregate_work.work_vector
                    or replayed.aggregate_comparison_vector
                    != aggregate_work.comparison_vector
                    or replayed.aggregate_projection_proof
                    != aggregate_work.actual_projection_proof
                ):
                    raise TwoStageAccountingV1Error(
                        "independent native aggregation does not replay"
                    )
                return tuple(
                    sorted(
                        (
                            aggregate.two_stage_work_aggregate_id,
                            replayed.aggregation_proof.marginal_work_aggregation_proof_id,
                        )
                    )
                )
            if evidence.independent_aggregate is not None:
                raise TwoStageAccountingV1Error(
                    "common-prefix aggregation cannot claim a marginal replay"
                )
            return tuple(
                sorted(
                    (
                        aggregate.two_stage_work_aggregate_id,
                        suffix.work_vector.work_vector_id,
                        aggregate_work.work_vector.work_vector_id,
                    )
                )
            )

        if kind is NonsemanticVerificationCheckKind.AGGREGATE_UPPER_COMPLIANCE:
            if (
                type(evidence) is not AggregateUpperComplianceEvidenceV1
                or type(evidence.selected_upper) is not RouteUpperBoundEnvelopeV1
            ):
                raise TwoStageAccountingV1Error(
                    "upper compliance requires a typed selected upper"
                )
            upper = evidence.selected_upper
            expected_route = RouteKind(core.route_kind.value)
            if (
                upper.route_attempt_id != route_context.route_attempt_id
                or upper.decision_point_id != core.decision_point_id
                or not _same_ref(upper.transaction_id, core.transaction_id)
                or upper.counter_registry_id != core.counter_registry_id
                or upper.comparison_profile_id != core.comparison_profile_id
                or upper.route_kind is not expected_route
            ):
                raise TwoStageAccountingV1Error(
                    "selected upper is stale for the aggregate binding"
                )
            upper_values = dict(upper.upper_bounds)
            if tuple(sorted(upper_values)) != SHARED_AXES:
                raise TwoStageAccountingV1Error(
                    "selected upper lacks the exact shared axes"
                )
            exceeded = tuple(
                axis
                for axis in SHARED_AXES
                if aggregate_work.comparison_vector.value(axis)
                > upper_values[axis]
            )
            if exceeded:
                raise TwoStageAccountingV1Error(
                    "aggregate exceeds selected upper on " + ", ".join(exceeded)
                )
            return tuple(
                sorted(
                    (
                        aggregate_work.comparison_vector.comparison_vector_id,
                        upper.route_upper_bound_envelope_id,
                    )
                )
            )

        if kind is NonsemanticVerificationCheckKind.CONTINUATION_WORK_VECTOR_AUTHORITY:
            if (
                type(evidence) is not ContinuationWorkVectorEvidenceV1
                or evidence.current_context != route_context
            ):
                raise TwoStageAccountingV1Error(
                    "continuation check requires typed current-context evidence"
                )
            from acfqp.phase3e_runner_v1 import (
                ContinuationWorkVectorAuthorityV1,
                _verify_continuation_work_vector_authority_v1,
            )

            if type(evidence.authority) is not ContinuationWorkVectorAuthorityV1:
                raise TwoStageAccountingV1Error(
                    "continuation check lacks typed prior-run authority"
                )
            prior_ids = _verify_continuation_work_vector_authority_v1(
                evidence.authority,
                current_context=route_context,
            )
            return tuple(
                sorted(
                    (
                        *prior_ids,
                        aggregate.two_stage_work_aggregate_id,
                        suffix.work_vector.work_vector_id,
                        aggregate_work.work_vector.work_vector_id,
                    )
                )
            )
    except TwoStageAccountingV1Error:
        raise
    except (TypeError, ValueError) as error:
        raise TwoStageAccountingV1Error(
            f"registered {kind.value} verification failed: {error}"
        ) from error
    raise TwoStageAccountingV1Error(
        f"unregistered nonsemantic check kind: {kind.value}"
    )


def attest_nonsemantic_verification_v1(
    *,
    core: SealedAccountingCoreV1,
    core_work: RecordedWorkV1,
    plan: VerificationChargePlanV1,
    obligation: FrozenNonsemanticVerificationObligationV1,
    evidence: NonsemanticVerificationEvidenceV1,
    aggregate: TwoStageWorkAggregateV1,
    suffix: RecordedWorkV1,
    aggregate_work: RecordedWorkV1,
    route_context: RouteDecisionContextV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> NonsemanticVerificationAttestationV1:
    if obligation not in plan.nonsemantic_obligations:
        raise TwoStageAccountingV1Error(
            "nonsemantic attestation obligation is absent from the frozen plan"
    )
    _validate_plan_core(plan, core)
    verified_evidence_ids = _registered_nonsemantic_evidence_ids_v1(
        core=core,
        core_work=core_work,
        obligation=obligation,
        evidence=evidence,
        aggregate=aggregate,
        suffix=suffix,
        aggregate_work=aggregate_work,
        route_context=route_context,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    return NonsemanticVerificationAttestationV1(
        core.route_decision_context_id,
        core.decision_point_id,
        core.transaction_id,
        core.accounting_core_seal_id,
        plan.verification_charge_plan_id,
        obligation.ordinal,
        obligation.check_kind,
        obligation.source_counter_record_id,
        verified_evidence_ids,
        obligation.verified_at_protocol_step,
    )


def _nonsemantic_entries(
    *,
    core: SealedAccountingCoreV1,
    plan: VerificationChargePlanV1,
    attestations: Sequence[NonsemanticVerificationAttestationV1],
) -> tuple[NonsemanticVerificationChargeEntryV1, ...]:
    if len(attestations) != len(plan.nonsemantic_obligations):
        raise TwoStageAccountingV1Error(
            "nonsemantic attestations do not exactly cover frozen obligations"
        )
    by_ordinal: dict[int, NonsemanticVerificationAttestationV1] = {}
    for attestation in attestations:
        if not isinstance(attestation, NonsemanticVerificationAttestationV1):
            raise TwoStageAccountingV1Error(
                "nonsemantic check lacks its typed attestation"
            )
        if attestation.obligation_ordinal in by_ordinal:
            raise TwoStageAccountingV1Error(
                "nonsemantic attestation repeats an obligation"
            )
        by_ordinal[attestation.obligation_ordinal] = attestation
    entries: list[NonsemanticVerificationChargeEntryV1] = []
    for obligation in plan.nonsemantic_obligations:
        try:
            attestation = by_ordinal.pop(obligation.ordinal)
        except KeyError as error:
            raise TwoStageAccountingV1Error(
                "nonsemantic attestation omitted or substituted an obligation"
            ) from error
        expected = (
            core.route_decision_context_id,
            core.decision_point_id,
            core.transaction_id,
            core.accounting_core_seal_id,
            plan.verification_charge_plan_id,
            obligation.check_kind,
            obligation.source_counter_record_id,
            obligation.verified_at_protocol_step,
        )
        actual = (
            attestation.route_decision_context_id,
            attestation.decision_point_id,
            attestation.transaction_id,
            attestation.accounting_core_seal_id,
            attestation.verification_charge_plan_id,
            attestation.check_kind,
            attestation.source_counter_record_id,
            attestation.verified_at_protocol_step,
        )
        if actual != expected:
            raise TwoStageAccountingV1Error(
                "nonsemantic attestation is stale or foreign"
            )
        entries.append(
            NonsemanticVerificationChargeEntryV1(
                obligation.ordinal,
                obligation.check_kind,
                obligation.source_counter_record_id,
                attestation.nonsemantic_verification_attestation_id,
            )
        )
    if by_ordinal:
        raise TwoStageAccountingV1Error(
            "nonsemantic attestation tuple contains padding"
        )
    return tuple(entries)


def derive_two_stage_accounting_v1(
    *,
    core: SealedAccountingCoreV1,
    core_work: RecordedWorkV1,
    plan: VerificationChargePlanV1,
    semantic_results: Sequence[SemanticVerificationResultV1],
    nonsemantic_records: Sequence[CounterRecordV1] = (),
    nonsemantic_evidence_factory: Callable[
        [TwoStageWorkAggregateV1, RecordedWorkV1, RecordedWorkV1],
        Sequence[NonsemanticVerificationEvidenceV1],
    ]
    | None = None,
    route_context: RouteDecisionContextV1 | Mapping[str, Any],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> TwoStageAccountingClosureV1:
    context = _load_context(route_context)
    _verify_profiles(context, registry, comparison_profile, actual_profile)
    _verify_recorded_work(
        core_work,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    if context.route_decision_context_id != core.route_decision_context_id:
        raise TwoStageAccountingV1Error("sealed core uses another route context")
    expected_core = SealedAccountingCoreV1(
        core.route_decision_context_id,
        core.decision_point_id,
        core.transaction_id,
        core.core_stage,
        core_work.work_vector.route_kind,
        core_work.work_vector.subject_id,
        core_work.actual_projection_proof.work_scope,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        actual_profile.actual_projection_profile_id,
        core_work.work_vector.work_vector_id,
        core_work.comparison_vector.comparison_vector_id,
        core_work.actual_projection_proof.actual_projection_proof_id,
        tuple(row.record_id for row in core_work.work_vector.records),
    )
    if core != expected_core:
        raise TwoStageAccountingV1Error("sealed core does not match exact recorded work")
    _validate_plan_core(plan, core)
    entries, source_records = _result_entries(
        plan=plan, results=semantic_results, registry=registry
    )

    records_by_id: dict[str, CounterRecordV1] = {}
    for record in nonsemantic_records:
        if not isinstance(record, CounterRecordV1):
            raise TwoStageAccountingV1Error(
                "nonsemantic verification charge is not a CounterRecordV1"
            )
        if record.record_id in records_by_id:
            raise TwoStageAccountingV1Error(
                "nonsemantic verification records contain a duplicate"
            )
        records_by_id[record.record_id] = record
    if len(records_by_id) != len(plan.nonsemantic_obligations):
        raise TwoStageAccountingV1Error(
            "nonsemantic records do not exactly cover frozen obligations"
        )
    ordered_nonsemantic_records: list[CounterRecordV1] = []
    for obligation in plan.nonsemantic_obligations:
        try:
            record = records_by_id.pop(obligation.source_counter_record_id)
        except KeyError as error:
            raise TwoStageAccountingV1Error(
                "nonsemantic source CounterRecord was omitted or substituted"
            ) from error
        if record.path != obligation.verification_counter_path:
            raise TwoStageAccountingV1Error(
                "nonsemantic source CounterRecord path differs from frozen obligation"
            )
        _merge_value(
            {path: 0 for path in registry.required_paths}, record, registry
        )
        ordered_nonsemantic_records.append(record)
    if records_by_id:
        raise TwoStageAccountingV1Error(
            "nonsemantic source CounterRecord tuple contains padding"
        )
    if {row.record_id for row in source_records} & {
        row.record_id for row in ordered_nonsemantic_records
    }:
        raise TwoStageAccountingV1Error(
            "semantic and nonsemantic obligations reuse one CounterRecord"
        )

    suffix_values = {path: 0 for path in registry.required_paths}
    for record in source_records:
        _merge_value(suffix_values, record, registry)
    for record in ordered_nonsemantic_records:
        _merge_value(suffix_values, record, registry)
    suffix_scope = (
        ActualWorkScope.COMMON_PREFIX
        if core.core_stage is AccountingCoreStage.COMMON_PREFIX
        else ActualWorkScope.MARGINAL_ROUTE_VERIFICATION
    )
    suffix = _materialize_values(
        values=suffix_values,
        subject_id=core.subject_id,
        route_kind=core.route_kind,
        work_scope=suffix_scope,
        recorder_id=TWO_STAGE_SUFFIX_RECORDER_ID,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )

    aggregate_values: dict[str, int] = {}
    core_values = core_work.work_vector.values
    suffix_native = suffix.work_vector.values
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        aggregate_values[path] = (
            core_values[path] + suffix_native[path]
            if leaf.reducer is ReducerEnum.SUM
            else max(core_values[path], suffix_native[path])
        )
    aggregate_scope = (
        ActualWorkScope.COMMON_PREFIX
        if core.core_stage is AccountingCoreStage.COMMON_PREFIX
        else ActualWorkScope.MARGINAL_ROUTE_AGGREGATE
    )
    aggregate_work = _materialize_values(
        values=aggregate_values,
        subject_id=core.subject_id,
        route_kind=core.route_kind,
        work_scope=aggregate_scope,
        recorder_id=(
            TWO_STAGE_AGGREGATE_RECORDER_ID
            if core.core_stage is AccountingCoreStage.COMMON_PREFIX
            else AGGREGATION_RECORDER_ID
        ),
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    aggregate = TwoStageWorkAggregateV1(
        core.route_decision_context_id,
        core.decision_point_id,
        core.transaction_id,
        core.accounting_core_seal_id,
        plan.verification_charge_plan_id,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        actual_profile.actual_projection_profile_id,
        core.route_kind,
        core.subject_id,
        core.core_work_vector_id,
        core.core_comparison_vector_id,
        core.core_projection_proof_id,
        suffix.work_vector.work_vector_id,
        suffix.comparison_vector.comparison_vector_id,
        suffix.actual_projection_proof.actual_projection_proof_id,
        aggregate_work.work_vector.work_vector_id,
        aggregate_work.comparison_vector.comparison_vector_id,
        aggregate_work.actual_projection_proof.actual_projection_proof_id,
    )
    if plan.nonsemantic_obligations:
        if nonsemantic_evidence_factory is None:
            raise TwoStageAccountingV1Error(
                "nonsemantic obligations require typed post-aggregate evidence"
            )
        nonsemantic_evidence = tuple(
            nonsemantic_evidence_factory(aggregate, suffix, aggregate_work)
        )
        if len(nonsemantic_evidence) != len(plan.nonsemantic_obligations):
            raise TwoStageAccountingV1Error(
                "nonsemantic evidence does not exactly cover frozen obligations"
            )
        nonsemantic_attestations = tuple(
            attest_nonsemantic_verification_v1(
                core=core,
                core_work=core_work,
                plan=plan,
                obligation=obligation,
                evidence=evidence,
                aggregate=aggregate,
                suffix=suffix,
                aggregate_work=aggregate_work,
                route_context=context,
                registry=registry,
                comparison_profile=comparison_profile,
                actual_profile=actual_profile,
            )
            for obligation, evidence in zip(
                plan.nonsemantic_obligations,
                nonsemantic_evidence,
                strict=True,
            )
        )
    else:
        if nonsemantic_evidence_factory is not None:
            supplied = tuple(
                nonsemantic_evidence_factory(aggregate, suffix, aggregate_work)
            )
            if supplied:
                raise TwoStageAccountingV1Error(
                    "nonsemantic evidence factory padded an empty plan"
                )
        nonsemantic_evidence = ()
        nonsemantic_attestations = ()
    nonsemantic_entries = _nonsemantic_entries(
        core=core,
        plan=plan,
        attestations=nonsemantic_attestations,
    )
    manifest = VerificationChargeManifestV1(
        core.route_decision_context_id,
        core.decision_point_id,
        core.transaction_id,
        core.accounting_core_seal_id,
        plan.verification_charge_plan_id,
        entries,
        nonsemantic_entries,
        suffix.work_vector.work_vector_id,
        suffix.comparison_vector.comparison_vector_id,
        suffix.actual_projection_proof.actual_projection_proof_id,
        aggregate_work.work_vector.work_vector_id,
        aggregate_work.comparison_vector.comparison_vector_id,
        aggregate_work.actual_projection_proof.actual_projection_proof_id,
        aggregate.two_stage_work_aggregate_id,
    )
    receipt = VerificationChargeReceiptV1(
        manifest.verification_charge_manifest_id,
        plan.verification_charge_plan_id,
        core.accounting_core_seal_id,
        aggregate.two_stage_work_aggregate_id,
        manifest.source_counter_record_ids,
        manifest.semantic_attestation_ids,
        manifest.nonsemantic_attestation_ids,
        suffix.work_vector.work_vector_id,
        aggregate_work.work_vector.work_vector_id,
    )
    return TwoStageAccountingClosureV1(
        core,
        plan,
        nonsemantic_evidence,
        nonsemantic_attestations,
        suffix,
        aggregate_work,
        aggregate,
        manifest,
        receipt,
    )


def verify_two_stage_accounting_v1(
    claimed: TwoStageAccountingClosureV1,
    *,
    core_work: RecordedWorkV1,
    semantic_results: Sequence[SemanticVerificationResultV1],
    nonsemantic_records: Sequence[CounterRecordV1] = (),
    route_context: RouteDecisionContextV1 | Mapping[str, Any],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> VerificationChargeReceiptV1:
    if not isinstance(claimed, TwoStageAccountingClosureV1):
        raise TwoStageAccountingV1Error(
            "claimed closure must be a TwoStageAccountingClosureV1"
        )
    recomputed = derive_two_stage_accounting_v1(
        core=claimed.core,
        core_work=core_work,
        plan=claimed.plan,
        semantic_results=semantic_results,
        nonsemantic_records=nonsemantic_records,
        nonsemantic_evidence_factory=(
            (lambda _aggregate, _suffix, _work: claimed.nonsemantic_evidence)
            if claimed.plan.nonsemantic_obligations
            else None
        ),
        route_context=route_context,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    if claimed != recomputed:
        raise TwoStageAccountingV1Error(
            "claimed two-stage accounting closure differs from exact replay"
        )
    return recomputed.receipt


__all__ = [
    "AccessTraceReconciliationEvidenceV1",
    "AccountingCoreStage",
    "AggregateUpperComplianceEvidenceV1",
    "ContinuationWorkVectorEvidenceV1",
    "ExecutionVectorIntegrityEvidenceV1",
    "FrozenNonsemanticVerificationObligationV1",
    "NativeAggregationEvidenceV1",
    "NonsemanticVerificationAttestationV1",
    "NonsemanticVerificationChargeEntryV1",
    "NonsemanticVerificationCheckKind",
    "NonsemanticVerificationEvidenceV1",
    "SCHEMA_VERSION",
    "SealedAccountingCoreV1",
    "TwoStageAccountingClosureV1",
    "TwoStageAccountingV1Error",
    "TwoStageWorkAggregateV1",
    "TWO_STAGE_AGGREGATE_RECORDER_ID",
    "TWO_STAGE_SUFFIX_RECORDER_ID",
    "VerificationChargeEntryV1",
    "VerificationChargeManifestV1",
    "VerificationChargeObligationV1",
    "VerificationChargePlanV1",
    "VerificationChargeReceiptV1",
    "attest_nonsemantic_verification_v1",
    "derive_two_stage_accounting_v1",
    "seal_accounting_core_v1",
    "verify_two_stage_accounting_v1",
]
