"""Fail-closed orchestration for one complete Phase-3E logical occurrence.

``phase3e_runner_v1.run_phase3e`` intentionally owns exactly one frozen route
decision.  This module composes those one-decision runs without weakening that
boundary.  A failed local transaction is retained as charged native work; a
second local transaction can run only after the full fresh-frontier authority
chain in :mod:`acfqp.phase3e_transactions_v1` succeeds.  That fresh marginal
decision may instead select and execute direct fallback without fabricating a
second local transaction.  Failures that do not reach such a fresh decision
use the separate fallback-only chain in
:mod:`acfqp.phase3e_failure_continuation_v1`.

The runner never creates semantic verification authority.  Callers must
provide the exact runtime verification results emitted by the registered
semantic verifiers.  Structural artifacts, hashes, status strings, or a
locally reconstructed object are insufficient.

This is still a non-official vertical slice.  In particular, the scalar and
counter-completeness gates remain locked exactly as in the one-decision
runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Mapping, Protocol

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProfileV1,
    official_actual_projection_profile_v1,
)
from acfqp.phase3e_failure_continuation_v1 import (
    AuthorizedFallbackAfterLocalFailureV1,
    FallbackAfterLocalFailureCandidateV1,
    LocalFailureKind,
    authorize_fallback_after_local_failure_v1,
    prepare_fallback_after_local_failure_v1,
    require_authorized_fallback_after_local_failure_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
    require_trusted_ground_fallback_execution_authority_v1,
)
from acfqp.phase3e_ids import (
    OCCURRENCE_CONTROL_FAILURE_DOMAIN,
    OCCURRENCE_TERMINAL_ARTIFACT_DOMAIN,
    OCCURRENCE_FAILURE_EVIDENCE_BINDING_DOMAIN,
    OCCURRENCE_FAILURE_TERMINAL_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_local_semantics_v1 import (
    LocalSolverOutcome,
    PostAuditOutcome,
    TrustedLocalExecutionV1,
    require_trusted_local_execution_authority_v1,
)
from acfqp.native_recorder_v1 import RecordedWorkV1
from acfqp.phase3e_occurrence_accounting_v1 import (
    OccurrenceWorkComponentEvidenceV1,
    OccurrenceWorkComponentKind,
    Phase3EOccurrenceWorkAggregateV1,
    RunnerCommonAccountingEvidenceV1,
    RunnerMarginalWorkEvidenceV1,
    RunnerPartialCommonAccountingEvidenceV1,
    derive_runner_partial_common_accounting_v1,
    derive_phase3e_occurrence_work_aggregate_v1,
    verify_phase3e_occurrence_work_aggregate_v1,
)
from acfqp.phase3e_runner_v1 import (
    COUNTER_COMPLETENESS_GATE_STATUS,
    OFFICIAL_EXECUTION_ALLOWED,
    OFFICIAL_N_BREAK_EVEN,
    OFFICIAL_SCALAR_COST,
    UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS,
    WORKLOAD_ECONOMICS_GATE_STATUS,
    Phase3EDecisionAuthorizationV1,
    Phase3EFailedRouteEvidenceV1,
    Phase3EPreselectionReadV1,
    Phase3ERouteExecutionFailedV1,
    Phase3ERouteExecutorV1,
    Phase3ERunResultV1,
    PreparedPhase3ERunV1,
    run_phase3e,
    verify_failed_route_evidence_v1,
)
from acfqp.phase3e_transactions_v1 import (
    LocalContinuationDirectiveV1,
    LocalContinuationRoute,
    SecondTransactionCandidateV1,
    authorize_second_transaction_v1,
    prepare_second_transaction_candidate_v1,
    require_local_continuation_directive_authority_v1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    DecisionPointV1,
    FrontierSnapshotV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TerminalClass,
    TerminalCode,
    TerminalArtifactV1,
    TransactionV1,
    TypedNotApplicable,
)


class Phase3EOccurrenceRunnerV1Error(ValueError):
    """An occurrence transition is unauthorized, stale, or unaccounted."""


class OccurrenceClosureCodeV1(str, Enum):
    LOCAL_GROUND_RECOVERY = "LOCAL_GROUND_RECOVERY"
    FULL_GROUND_FALLBACK = "FULL_GROUND_FALLBACK"
    FULL_GROUND_EXACT_INFEASIBLE = "FULL_GROUND_EXACT_INFEASIBLE"
    FALLBACK_CAP_EXHAUSTED = "FALLBACK_CAP_EXHAUSTED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"


_OCCURRENCE_FAILURE_TERMINAL_AUTHORITY = object()
_PARTIAL_COMMON_REJECTION_STAGES = frozenset(
    {
        "SECOND_TRANSACTION_AUTHORITY_REJECTED",
        "FRESH_FALLBACK_AUTHORITY_REJECTED",
    }
)


@dataclass(frozen=True, slots=True)
class Phase3EOccurrenceControlFailureV1:
    """Content-addressed evidence for a pre-freeze continuation failure."""

    route_decision_context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str | TypedNotApplicable
    failure_stage: str
    error_type: str
    error_message: str
    completed_decision_run_count: int
    accounted_common_work_id: str | TypedNotApplicable

    def __post_init__(self) -> None:
        for name in (
            "route_decision_context_id",
            "logical_occurrence_id",
            "route_attempt_id",
        ):
            try:
                parse_content_id(getattr(self, name))
            except ValueError as error:
                raise Phase3EOccurrenceRunnerV1Error(
                    f"{name} must be a content ID"
                ) from error
        object.__setattr__(
            self, "decision_point_id", _parse_ref(self.decision_point_id, "decision_point_id")
        )
        object.__setattr__(
            self,
            "accounted_common_work_id",
            _parse_ref(self.accounted_common_work_id, "accounted_common_work_id"),
        )
        if type(self.failure_stage) is not str or not self.failure_stage:
            raise Phase3EOccurrenceRunnerV1Error(
                "control failure stage must be nonempty"
            )
        if type(self.error_type) is not str or not self.error_type or type(
            self.error_message
        ) is not str:
            raise Phase3EOccurrenceRunnerV1Error(
                "control failure must retain error type and message"
            )
        if (
            type(self.completed_decision_run_count) is not int
            or self.completed_decision_run_count < 1
            or self.completed_decision_run_count > 2
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "control failure completed-run count is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_occurrence_control_failure.v1",
            "schema_version": "1.0.0",
            "RouteDecisionContext_id": self.route_decision_context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": _ref_payload(self.decision_point_id),
            "failure_stage": self.failure_stage,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "completed_decision_run_count": self.completed_decision_run_count,
            "accounted_common_work_id": _ref_payload(
                self.accounted_common_work_id
            ),
        }

    @property
    def occurrence_control_failure_id(self) -> str:
        return content_id(OCCURRENCE_CONTROL_FAILURE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_control_failure_id": self.occurrence_control_failure_id,
        }


@dataclass(frozen=True, slots=True)
class Phase3EOccurrenceTerminalArtifactV1:
    """Typed denominator and provenance artifact for one occurrence closure.

    The dedicated FQ9 occurrence authority binds the ordered component list,
    denominator counts, and every sealed executor identity actually used.
    """

    route_decision_context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str | TypedNotApplicable
    transaction_id: str | TypedNotApplicable
    occurrence_work_aggregate_id: str
    component_ref_ids: tuple[str, ...]
    terminal_code: TerminalCode
    decision_run_count: int
    transaction_count: int
    work_component_count: int
    detail_id: str
    runtime_tree_ids: tuple[str, ...] = ()
    executor_recipe_ids: tuple[str, ...] = ()
    closure_denominator_included: bool = True
    certification_denominator_included: bool = True
    economics_denominator_included: bool = True
    plan_certificate_count: int = 0
    infeasibility_certificate_count: int = 0
    noncertificate_count: int = 1
    terminal_scope: str = "LOGICAL_OCCURRENCE"
    terminal_class: TerminalClass = TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        for name in (
            "route_decision_context_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "occurrence_work_aggregate_id",
            "detail_id",
        ):
            try:
                parse_content_id(getattr(self, name))
            except ValueError as error:
                raise Phase3EOccurrenceRunnerV1Error(
                    f"{name} must be a content ID"
                ) from error
        object.__setattr__(
            self, "decision_point_id", _parse_ref(self.decision_point_id, "decision_point_id")
        )
        object.__setattr__(
            self, "transaction_id", _parse_ref(self.transaction_id, "transaction_id")
        )
        if type(self.component_ref_ids) is not tuple or not self.component_ref_ids:
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence closure requires an ordered component-ref tuple"
            )
        for value in self.component_ref_ids + self.runtime_tree_ids + self.executor_recipe_ids:
            try:
                parse_content_id(value)
            except ValueError as error:
                raise Phase3EOccurrenceRunnerV1Error(
                    "occurrence closure provenance contains a non-content ID"
                ) from error
        if len(set(self.component_ref_ids)) != len(self.component_ref_ids):
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence closure repeats a work component"
            )
        if len(self.runtime_tree_ids) != len(self.executor_recipe_ids):
            raise Phase3EOccurrenceRunnerV1Error(
                "runtime-tree and executor-recipe provenance lengths differ"
            )
        object.__setattr__(self, "terminal_code", TerminalCode(self.terminal_code))
        object.__setattr__(self, "terminal_class", TerminalClass(self.terminal_class))
        if (
            self.terminal_scope != "LOGICAL_OCCURRENCE"
            or self.terminal_class
            is not TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence terminal must be a logical-occurrence noncertificate"
            )
        if self.terminal_code not in {
            TerminalCode.PROTOCOL_FAILURE,
            TerminalCode.FALLBACK_CAP_EXHAUSTED,
        }:
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence closure evidence currently authorizes only noncertificates"
            )
        if (
            type(self.decision_run_count) is not int
            or self.decision_run_count < 1
            or self.decision_run_count > 3
            or type(self.transaction_count) is not int
            or self.transaction_count < 0
            or self.transaction_count > 2
            or self.work_component_count != len(self.component_ref_ids)
            or self.work_component_count not in {
                2 * self.decision_run_count,
                2 * self.decision_run_count - 1,
            }
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence closure decision/transaction/component counts are invalid"
            )
        if not all(
            value is True
            for value in (
                self.closure_denominator_included,
                self.certification_denominator_included,
                self.economics_denominator_included,
            )
        ) or (
            self.plan_certificate_count,
            self.infeasibility_certificate_count,
            self.noncertificate_count,
        ) != (0, 0, 1):
            raise Phase3EOccurrenceRunnerV1Error(
                "noncertificate occurrence must remain in all denominators exactly once"
            )
        if self.schema_version != "1.0.0":
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence closure evidence schema mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_occurrence_terminal_artifact.v1",
            "schema_version": self.schema_version,
            "terminal_scope": self.terminal_scope,
            "terminal_class": self.terminal_class.value,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": _ref_payload(self.decision_point_id),
            "transaction_id": _ref_payload(self.transaction_id),
            "occurrence_work_aggregate_id": self.occurrence_work_aggregate_id,
            "component_ref_ids": list(self.component_ref_ids),
            "terminal_code": self.terminal_code.value,
            "decision_run_count": self.decision_run_count,
            "transaction_count": self.transaction_count,
            "work_component_count": self.work_component_count,
            "detail_id": self.detail_id,
            "runtime_tree_ids": list(self.runtime_tree_ids),
            "executor_recipe_ids": list(self.executor_recipe_ids),
            "closure_denominator_included": True,
            "certification_denominator_included": True,
            "economics_denominator_included": True,
            "plan_certificate_count": 0,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 1,
        }

    @property
    def occurrence_terminal_artifact_id(self) -> str:
        return content_id(OCCURRENCE_TERMINAL_ARTIFACT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_terminal_artifact_id": self.occurrence_terminal_artifact_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "Phase3EOccurrenceTerminalArtifactV1":
        expected = {
            "schema", "schema_version", "terminal_scope", "terminal_class",
            "RouteDecisionContext_id", "logical_occurrence_id",
            "route_attempt_id", "decision_point_id", "transaction_id",
            "occurrence_work_aggregate_id", "component_ref_ids",
            "terminal_code", "decision_run_count", "transaction_count",
            "work_component_count", "detail_id", "runtime_tree_ids",
            "executor_recipe_ids", "closure_denominator_included",
            "certification_denominator_included",
            "economics_denominator_included", "plan_certificate_count",
            "infeasibility_certificate_count", "noncertificate_count",
            "occurrence_terminal_artifact_id",
        }
        try:
            require_exact_fields(document, expected, context="occurrence closure evidence")
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(str(error)) from error
        if (
            document["schema"]
            != "acfqp.phase3e_occurrence_terminal_artifact.v1"
            or type(document["component_ref_ids"]) is not list
            or type(document["runtime_tree_ids"]) is not list
            or type(document["executor_recipe_ids"]) is not list
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence closure evidence schema mismatch"
            )
        result = cls(
            document["RouteDecisionContext_id"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            _parse_ref(document["decision_point_id"], "decision_point_id"),
            _parse_ref(document["transaction_id"], "transaction_id"),
            document["occurrence_work_aggregate_id"],
            tuple(document["component_ref_ids"]),
            document["terminal_code"],
            document["decision_run_count"],
            document["transaction_count"],
            document["work_component_count"],
            document["detail_id"],
            tuple(document["runtime_tree_ids"]),
            tuple(document["executor_recipe_ids"]),
            document["closure_denominator_included"],
            document["certification_denominator_included"],
            document["economics_denominator_included"],
            document["plan_certificate_count"],
            document["infeasibility_certificate_count"],
            document["noncertificate_count"],
            document["terminal_scope"],
            document["terminal_class"],
            document["schema_version"],
        )
        if document["occurrence_terminal_artifact_id"] != result.occurrence_terminal_artifact_id:
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence terminal artifact content ID mismatch"
            )
        return result


def _ref_payload(value: str | TypedNotApplicable) -> Any:
    return value.to_dict() if isinstance(value, TypedNotApplicable) else value


def _parse_ref(value: Any, field: str) -> str | TypedNotApplicable:
    if isinstance(value, TypedNotApplicable):
        try:
            return TypedNotApplicable.from_dict(value.to_dict())
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(str(error)) from error
    if isinstance(value, Mapping):
        try:
            return TypedNotApplicable.from_dict(value)
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(str(error)) from error
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            f"{field} must be a content ID or typed NOT_APPLICABLE"
        ) from error


def failed_route_evidence_binding_id_v1(
    evidence: Phase3EFailedRouteEvidenceV1,
) -> str:
    """Content-bind every retained identity and failure classification."""

    if not isinstance(evidence, Phase3EFailedRouteEvidenceV1):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence failure binding requires typed route evidence"
        )
    decision_attestation = getattr(
        getattr(evidence.decision_result, "attestation", None),
        "verification_attestation_id",
        None,
    )
    try:
        parse_content_id(decision_attestation)
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            "failed route lacks its decision verification attestation"
        ) from error
    violation = evidence.forbidden_access_violation
    sealed_failure = evidence.sealed_executor_failure_evidence
    return content_id(
        OCCURRENCE_FAILURE_EVIDENCE_BINDING_DOMAIN,
        {
            "schema": "acfqp.phase3e_occurrence_failure_evidence_binding.v1",
            "RouteDecisionContext_id": (
                evidence.context.route_decision_context_id
            ),
            "logical_occurrence_id": evidence.context.logical_occurrence_id,
            "route_attempt_id": evidence.context.route_attempt_id,
            "decision_point_id": evidence.decision_point.decision_point_id,
            "route_decision_id": evidence.decision.route_decision_id,
            "decision_verification_attestation_id": decision_attestation,
            "selected_upper_id": (
                evidence.selected_upper.route_upper_bound_envelope_id
            ),
            "selected_route": evidence.selected_route.value,
            "accounted_common_work_vector_id": (
                evidence.accounted_common_work.work_vector.work_vector_id
            ),
            "common_two_stage_receipt_id": (
                None
                if evidence.common_two_stage_accounting is None
                else evidence.common_two_stage_accounting.receipt
                .verification_charge_receipt_id
            ),
            "partial_route_work_vector_id": (
                evidence.partial_route_work.work_vector.work_vector_id
            ),
            "partial_verification_work_vector_id": (
                evidence.partial_verification_work.work_vector.work_vector_id
            ),
            "partial_marginal_work_vector_id": (
                evidence.partial_marginal_work.aggregate_work_vector.work_vector_id
            ),
            "partial_marginal_aggregation_proof_id": (
                evidence.partial_marginal_work.aggregation_proof
                .marginal_work_aggregation_proof_id
            ),
            "access_event_log_id": evidence.access_log.access_event_log_id,
            "route_decision_freeze_attestation_id": (
                evidence.freeze_attestation
                .route_decision_freeze_attestation_id
            ),
            "original_error_classification": (
                evidence.original_error_classification.value
            ),
            "original_error_type": evidence.original_error_type,
            "original_error_message": evidence.original_error_message,
            "access_native_reconciliation_status": (
                evidence.access_native_reconciliation_status.value
            ),
            "access_native_reconciliation_error": (
                evidence.access_native_reconciliation_error
            ),
            "forbidden_access_violation_id": (
                None
                if violation is None
                else violation.forbidden_access_violation_id
            ),
            "sealed_executor_failure_evidence_id": (
                None
                if sealed_failure is None
                else sealed_failure.sealed_executor_failure_evidence_id
            ),
            "closure_class": evidence.closure_class,
            "closure_code": evidence.closure_code,
        },
    )


@dataclass(frozen=True, slots=True)
class Phase3EOccurrenceFailureTerminalV1:
    """Content-addressed logical-occurrence noncertificate closure."""

    route_decision_context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: str | TypedNotApplicable
    selected_route: RouteSelection
    occurrence_work_aggregate_id: str
    failed_route_evidence_binding_id: str
    partial_route_work_vector_id: str
    partial_verification_work_vector_id: str
    partial_marginal_work_vector_id: str
    partial_marginal_aggregation_proof_id: str
    route_decision_freeze_attestation_id: str
    access_event_log_id: str
    successful_decision_run_count: int
    failed_decision_ordinal: int
    transaction_count: int
    work_component_count: int
    closure_denominator_included: bool = True
    certification_denominator_included: bool = True
    economics_denominator_included: bool = True
    plan_certificate_count: int = 0
    infeasibility_certificate_count: int = 0
    noncertificate_count: int = 1
    terminal_scope: str = "LOGICAL_OCCURRENCE"
    terminal_class: TerminalClass = (
        TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
    )
    terminal_code: TerminalCode = TerminalCode.PROTOCOL_FAILURE
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        for field_name in (
            "route_decision_context_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "occurrence_work_aggregate_id",
            "failed_route_evidence_binding_id",
            "partial_route_work_vector_id",
            "partial_verification_work_vector_id",
            "partial_marginal_work_vector_id",
            "partial_marginal_aggregation_proof_id",
            "route_decision_freeze_attestation_id",
            "access_event_log_id",
        ):
            try:
                parse_content_id(getattr(self, field_name))
            except ValueError as error:
                raise Phase3EOccurrenceRunnerV1Error(
                    f"{field_name} must be a full content ID"
                ) from error
        object.__setattr__(
            self, "transaction_id", _parse_ref(self.transaction_id, "transaction_id")
        )
        object.__setattr__(
            self, "selected_route", RouteSelection(self.selected_route)
        )
        object.__setattr__(
            self, "terminal_class", TerminalClass(self.terminal_class)
        )
        object.__setattr__(self, "terminal_code", TerminalCode(self.terminal_code))
        if (
            self.terminal_scope != "LOGICAL_OCCURRENCE"
            or self.terminal_class
            is not TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
            or self.terminal_code is not TerminalCode.PROTOCOL_FAILURE
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "failed occurrence may close only as logical-occurrence "
                "noncertificate PROTOCOL_FAILURE"
            )
        if (
            type(self.successful_decision_run_count) is not int
            or self.successful_decision_run_count < 0
            or self.successful_decision_run_count > 2
            or self.failed_decision_ordinal
            != self.successful_decision_run_count + 1
            or self.failed_decision_ordinal not in {1, 2, 3}
            or type(self.transaction_count) is not int
            or self.transaction_count < 0
            or self.transaction_count > 2
            or self.work_component_count != 2 * self.failed_decision_ordinal
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "failed occurrence decision/component cardinalities are invalid"
            )
        if not all(
            value is True
            for value in (
                self.closure_denominator_included,
                self.certification_denominator_included,
                self.economics_denominator_included,
            )
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "failed logical occurrence cannot be removed from a denominator"
            )
        if (
            self.plan_certificate_count,
            self.infeasibility_certificate_count,
            self.noncertificate_count,
        ) != (0, 0, 1):
            raise Phase3EOccurrenceRunnerV1Error(
                "protocol failure must count exactly one noncertificate and no certificate"
            )
        if self.schema_version != "1.0.0":
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence failure terminal schema version mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_occurrence_failure_terminal.v1",
            "schema_version": self.schema_version,
            "terminal_scope": self.terminal_scope,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": _ref_payload(self.transaction_id),
            "selected_route": self.selected_route.value,
            "occurrence_work_aggregate_id": self.occurrence_work_aggregate_id,
            "failed_route_evidence_binding_id": (
                self.failed_route_evidence_binding_id
            ),
            "partial_route_work_vector_id": self.partial_route_work_vector_id,
            "partial_verification_work_vector_id": (
                self.partial_verification_work_vector_id
            ),
            "partial_marginal_work_vector_id": (
                self.partial_marginal_work_vector_id
            ),
            "partial_marginal_aggregation_proof_id": (
                self.partial_marginal_aggregation_proof_id
            ),
            "route_decision_freeze_attestation_id": (
                self.route_decision_freeze_attestation_id
            ),
            "access_event_log_id": self.access_event_log_id,
            "successful_decision_run_count": self.successful_decision_run_count,
            "failed_decision_ordinal": self.failed_decision_ordinal,
            "transaction_count": self.transaction_count,
            "work_component_count": self.work_component_count,
            "closure_denominator_included": True,
            "certification_denominator_included": True,
            "economics_denominator_included": True,
            "plan_certificate_count": 0,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 1,
        }

    @property
    def occurrence_failure_terminal_id(self) -> str:
        return content_id(OCCURRENCE_FAILURE_TERMINAL_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_failure_terminal_id": self.occurrence_failure_terminal_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "Phase3EOccurrenceFailureTerminalV1":
        expected = {
            "schema",
            "schema_version",
            "terminal_scope",
            "terminal_class",
            "terminal_code",
            "RouteDecisionContext_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transaction_id",
            "selected_route",
            "occurrence_work_aggregate_id",
            "failed_route_evidence_binding_id",
            "partial_route_work_vector_id",
            "partial_verification_work_vector_id",
            "partial_marginal_work_vector_id",
            "partial_marginal_aggregation_proof_id",
            "route_decision_freeze_attestation_id",
            "access_event_log_id",
            "successful_decision_run_count",
            "failed_decision_ordinal",
            "transaction_count",
            "work_component_count",
            "closure_denominator_included",
            "certification_denominator_included",
            "economics_denominator_included",
            "plan_certificate_count",
            "infeasibility_certificate_count",
            "noncertificate_count",
            "occurrence_failure_terminal_id",
        }
        try:
            require_exact_fields(
                document, expected, context="occurrence failure terminal"
            )
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(str(error)) from error
        if document["schema"] != "acfqp.phase3e_occurrence_failure_terminal.v1":
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence failure terminal schema mismatch"
            )
        result = cls(
            document["RouteDecisionContext_id"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            document["decision_point_id"],
            _parse_ref(document["transaction_id"], "transaction_id"),
            document["selected_route"],
            document["occurrence_work_aggregate_id"],
            document["failed_route_evidence_binding_id"],
            document["partial_route_work_vector_id"],
            document["partial_verification_work_vector_id"],
            document["partial_marginal_work_vector_id"],
            document["partial_marginal_aggregation_proof_id"],
            document["route_decision_freeze_attestation_id"],
            document["access_event_log_id"],
            document["successful_decision_run_count"],
            document["failed_decision_ordinal"],
            document["transaction_count"],
            document["work_component_count"],
            document["closure_denominator_included"],
            document["certification_denominator_included"],
            document["economics_denominator_included"],
            document["plan_certificate_count"],
            document["infeasibility_certificate_count"],
            document["noncertificate_count"],
            document["terminal_scope"],
            document["terminal_class"],
            document["terminal_code"],
            document["schema_version"],
        )
        if document["occurrence_failure_terminal_id"] != (
            result.occurrence_failure_terminal_id
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence failure terminal content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class Phase3EOccurrenceFailureTerminalAuthorityV1:
    """Opaque authority emitted only after full failure/occurrence replay."""

    terminal: Phase3EOccurrenceFailureTerminalV1
    occurrence_work: Phase3EOccurrenceWorkAggregateV1
    failed_route_evidence: Phase3EFailedRouteEvidenceV1 = field(
        repr=False, compare=False
    )
    _authority: object = field(default=None, repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _OCCURRENCE_FAILURE_TERMINAL_AUTHORITY:
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence failure terminal authority requires semantic replay"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_OCCURRENCE_FAILURE_TERMINAL_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise Phase3EOccurrenceRunnerV1Error(
                    "occurrence failure terminal is a copied or modified authority"
                ) from error


def require_phase3e_occurrence_failure_terminal_authority_v1(
    authority: object,
) -> Phase3EOccurrenceFailureTerminalAuthorityV1:
    """Require the exact full-replay occurrence-failure authority instance."""

    if type(authority) is not Phase3EOccurrenceFailureTerminalAuthorityV1:
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence failure terminal lacks semantic replay authority"
        )
    try:
        require_runtime_authority_v1(
            authority,
            issuer=_OCCURRENCE_FAILURE_TERMINAL_AUTHORITY,
        )
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence failure terminal is not the retained replay instance"
        ) from error
    return authority


@dataclass(frozen=True, slots=True)
class LocalFailureObservationV1:
    """Typed, immutable state handed to a continuation planner."""

    context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    transaction: TransactionV1
    run_result: Phase3ERunResultV1
    failure_kind: LocalFailureKind
    failure_artifact_id: str
    completed_transactions: tuple[TransactionV1, ...]
    completed_local_runs: tuple[Phase3ERunResultV1, ...]

    def __post_init__(self) -> None:
        if self.run_result.selected_route is not RouteSelection.LOCAL:
            raise Phase3EOccurrenceRunnerV1Error(
                "local failure observation carries a non-local run"
            )
        if type(self.completed_transactions) is not tuple or type(
            self.completed_local_runs
        ) is not tuple:
            raise Phase3EOccurrenceRunnerV1Error(
                "completed local history must be immutable"
            )
        if len(self.completed_transactions) != len(self.completed_local_runs):
            raise Phase3EOccurrenceRunnerV1Error(
                "local transaction/run history lengths differ"
            )
        if not self.completed_transactions or (
            self.completed_transactions[-1] != self.transaction
            or self.completed_local_runs[-1] is not self.run_result
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "failure observation does not end at the current transaction"
            )
        try:
            parse_content_id(self.failure_artifact_id)
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(
                "local failure artifact ID is invalid"
            ) from error


@dataclass(frozen=True, slots=True)
class SecondTransactionAuthorityPackageV1:
    """Planner-owned next-step inputs; prior WorkVector authority is excluded.

    The completed transaction's WorkVector result is intentionally absent: it
    comes only from ``LocalFailureObservationV1.run_result`` at authorization
    time, so the planner cannot substitute historical execution evidence.
    """

    first_frontier: FrontierSnapshotV1
    first_causal: CausalEvidenceV1
    first_transaction: TransactionV1
    first_fallback_upper_id: str
    second_context: RouteDecisionContextV1
    second_frontier: FrontierSnapshotV1
    second_causal: CausalEvidenceV1
    second_decision_point: DecisionPointV1
    second_transaction: TransactionV1
    second_local_cardinality: CardinalityEvidenceV1
    second_fallback_cardinality: CardinalityEvidenceV1
    second_local_upper: RouteUpperBoundEnvelopeV1
    second_fallback_upper: RouteUpperBoundEnvelopeV1
    second_route_decision: MarginalRouteDecisionV1
    second_common_prefix_work: RecordedWorkV1
    cap_profile: RouteCapProfileV1
    causal_result: object = field(repr=False, compare=False)
    local_cardinality_result: object = field(repr=False, compare=False)
    fallback_cardinality_result: object = field(repr=False, compare=False)
    local_upper_result: object = field(repr=False, compare=False)
    fallback_upper_result: object = field(repr=False, compare=False)
    route_decision_result: object = field(repr=False, compare=False)
    reusable_rapm_id: str
    failed_certificate_id: str
    action_catalogue_id: str
    preselection_reads: tuple[Phase3EPreselectionReadV1, ...]
    local_executor: Phase3ERouteExecutorV1 = field(repr=False, compare=False)
    fallback_executor: Phase3ERouteExecutorV1 = field(repr=False, compare=False)
    two_stage_accounting_profile: bool = field(default=False, kw_only=True)
    common_accounting_core: object | None = field(
        default=None, kw_only=True, repr=False, compare=False
    )
    common_verification_charge_plan: object | None = field(
        default=None, kw_only=True, repr=False, compare=False
    )
    common_nonsemantic_records: tuple[CounterRecordV1, ...] = field(
        default=(), kw_only=True, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        try:
            parse_content_id(self.first_fallback_upper_id)
            parse_content_id(self.reusable_rapm_id)
            parse_content_id(self.failed_certificate_id)
            parse_content_id(self.action_catalogue_id)
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(str(error)) from error
        if type(self.preselection_reads) is not tuple:
            raise Phase3EOccurrenceRunnerV1Error(
                "transaction-2 preselection reads must be immutable"
            )
        if type(self.two_stage_accounting_profile) is not bool:
            raise Phase3EOccurrenceRunnerV1Error(
                "transaction-2 accounting profile flag must be boolean"
            )
        if type(self.common_nonsemantic_records) is not tuple or not all(
            isinstance(row, CounterRecordV1)
            for row in self.common_nonsemantic_records
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "transaction-2 nonsemantic records must be an immutable typed tuple"
            )
        if not self.two_stage_accounting_profile and (
            self.common_accounting_core is not None
            or self.common_verification_charge_plan is not None
            or self.common_nonsemantic_records
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "historical transaction-2 package cannot claim accounting artifacts"
            )


@dataclass(frozen=True, slots=True)
class FreshFallbackAuthorityPackageV1:
    """Fresh fallback-only inputs excluding prior execution authority.

    ``prior_work_results`` is deliberately not a planner field.  The occurrence
    runner derives that tuple from its immutable completed-run history.
    """

    context: RouteDecisionContextV1
    failure_kind: LocalFailureKind
    local_cap_profile: RouteCapProfileV1
    prior_route_upper_ids: tuple[str, ...]
    prior_fallback_cardinality_bound_ids: tuple[str, ...]
    fallback_common_prefix_work: RecordedWorkV1
    fallback_decision_point: DecisionPointV1
    fallback_cap_profile: GroundFallbackCapProfileV1
    fallback_cardinality_bound: GroundFallbackCardinalityBoundV1
    fallback_cardinality: CardinalityEvidenceV1
    fallback_upper: RouteUpperBoundEnvelopeV1
    fallback_route_decision: MarginalRouteDecisionV1
    common_prefix_work_result: object = field(repr=False, compare=False)
    cardinality_result: object = field(repr=False, compare=False)
    fallback_upper_result: object = field(repr=False, compare=False)
    route_decision_result: object = field(repr=False, compare=False)
    reusable_rapm_id: str
    failed_certificate_id: str
    action_catalogue_id: str
    preselection_reads: tuple[Phase3EPreselectionReadV1, ...]
    fallback_executor: Phase3ERouteExecutorV1 = field(repr=False, compare=False)
    two_stage_accounting_profile: bool = field(default=False, kw_only=True)
    common_accounting_core: object | None = field(
        default=None, kw_only=True, repr=False, compare=False
    )
    common_verification_charge_plan: object | None = field(
        default=None, kw_only=True, repr=False, compare=False
    )
    common_nonsemantic_records: tuple[CounterRecordV1, ...] = field(
        default=(), kw_only=True, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        try:
            parse_content_id(self.reusable_rapm_id)
            parse_content_id(self.failed_certificate_id)
            parse_content_id(self.action_catalogue_id)
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(str(error)) from error
        if type(self.prior_route_upper_ids) is not tuple or type(
            self.prior_fallback_cardinality_bound_ids
        ) is not tuple:
            raise Phase3EOccurrenceRunnerV1Error(
                "prior fallback identity history must be immutable"
            )
        if type(self.preselection_reads) is not tuple:
            raise Phase3EOccurrenceRunnerV1Error(
                "fallback preselection reads must be immutable"
            )
        if type(self.two_stage_accounting_profile) is not bool:
            raise Phase3EOccurrenceRunnerV1Error(
                "fresh-fallback accounting profile flag must be boolean"
            )
        if type(self.common_nonsemantic_records) is not tuple or not all(
            isinstance(row, CounterRecordV1)
            for row in self.common_nonsemantic_records
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "fallback nonsemantic records must be an immutable typed tuple"
            )
        if not self.two_stage_accounting_profile and (
            self.common_accounting_core is not None
            or self.common_verification_charge_plan is not None
            or self.common_nonsemantic_records
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "historical fallback package cannot claim accounting artifacts"
            )


class SecondTransactionPlannerV1(Protocol):
    def __call__(
        self, observation: LocalFailureObservationV1
    ) -> SecondTransactionAuthorityPackageV1: ...


class FreshFallbackPlannerV1(Protocol):
    def __call__(
        self, observation: LocalFailureObservationV1
    ) -> FreshFallbackAuthorityPackageV1: ...


def _continuation_executor_profile_kwargs_v1(
    observation: LocalFailureObservationV1,
    executor: Phase3ERouteExecutorV1,
    expected_route: RouteSelection,
) -> dict[str, object]:
    """Preserve a sealed profile across every decision in one occurrence.

    Historical runs remain historical.  A sealed first/previous decision,
    however, may never silently fall back to an arbitrary preconstructed
    callable for transaction 2 or the fresh fallback decision.
    """

    sealed = observation.run_result.sealed_executor_profile
    if sealed is not True:
        if sealed is not False:
            raise Phase3EOccurrenceRunnerV1Error(
                "completed run has an invalid sealed-executor profile flag"
            )
        return {}
    from acfqp.phase3e_sealed_executor_v1 import (
        Phase3ESealedExecutorV1Error,
        require_sealed_executor_factory_v1,
    )

    try:
        factory = require_sealed_executor_factory_v1(executor)
    except Phase3ESealedExecutorV1Error as error:
        raise Phase3EOccurrenceRunnerV1Error(
            "sealed occurrence continuation rejected a legacy executor"
        ) from error
    if factory.recipe.selected_route is not expected_route:
        raise Phase3EOccurrenceRunnerV1Error(
            "sealed continuation recipe differs from the selected route"
        )
    return {
        "runtime_tree_id": factory.recipe.runtime_tree_id,
        "executor_recipe_id": factory.recipe.executor_recipe_id,
        "sealed_executor_profile": True,
    }


def _runner_route_semantic_result_v1(
    run: Phase3ERunResultV1,
    role: object,
) -> object:
    """Select one exact authority emitted by the completed route runner."""

    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        SemanticVerificationV1Error,
        require_semantic_verification_result_v1,
    )

    semantic_role = SemanticRole(role)
    matches: list[object] = []
    for result in run.route_execution.semantic_verification_results:
        try:
            verified = require_semantic_verification_result_v1(
                result, semantic_role
            )
        except SemanticVerificationV1Error:
            continue
        matches.append(verified)
    if len(matches) != 1:
        raise Phase3EOccurrenceRunnerV1Error(
            f"completed runner route must carry exactly one {semantic_role.value} authority"
        )
    return matches[0]


def _continuation_accounting_profile_kwargs_v1(
    observation: LocalFailureObservationV1,
    package: object,
) -> dict[str, object]:
    """Require an exact next-prefix charge plan after an accounted run."""

    previous = observation.run_result.two_stage_accounting_profile
    claimed = getattr(package, "two_stage_accounting_profile", False)
    core = getattr(package, "common_accounting_core", None)
    plan = getattr(package, "common_verification_charge_plan", None)
    if previous is True:
        from acfqp.phase3e_two_stage_accounting_v1 import (
            SealedAccountingCoreV1,
            VerificationChargePlanV1,
        )

        if claimed is not True or not isinstance(
            core, SealedAccountingCoreV1
        ) or not isinstance(plan, VerificationChargePlanV1):
            raise Phase3EOccurrenceRunnerV1Error(
                "accounted occurrence continuation lacks its frozen next-prefix charge plan"
            )
        records = getattr(package, "common_nonsemantic_records", None)
        if type(records) is not tuple or not all(
            isinstance(row, CounterRecordV1) for row in records
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "accounted continuation lacks its frozen nonsemantic records"
            )
        from acfqp.phase3e_runner_v1 import (
            continuation_work_vector_authority_v1,
        )
        return {
            "two_stage_accounting_profile": True,
            "common_accounting_core": core,
            "common_verification_charge_plan": plan,
            "additional_common_verification_results": (
                (package.common_prefix_work_result,)
                if isinstance(package, FreshFallbackAuthorityPackageV1)
                else ()
            ),
            "common_nonsemantic_records": records,
            "continuation_work_vector_authorities": tuple(
                continuation_work_vector_authority_v1(row)
                for row in observation.completed_local_runs
            ),
        }
    if previous is not False:
        raise Phase3EOccurrenceRunnerV1Error(
            "completed run has an invalid two-stage accounting profile flag"
        )
    if (
        claimed is not False
        or core is not None
        or plan is not None
        or getattr(package, "common_nonsemantic_records", ())
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "historical occurrence cannot claim a continuation accounting plan"
        )
    return {}


@dataclass(frozen=True, slots=True)
class Phase3EOccurrenceRunResultV1:
    closure_code: OccurrenceClosureCodeV1
    decision_runs: tuple[Phase3ERunResultV1, ...]
    transactions: tuple[TransactionV1, ...]
    work_components: tuple[OccurrenceWorkComponentEvidenceV1, ...]
    occurrence_work: Phase3EOccurrenceWorkAggregateV1
    continuation_authorities: tuple[object, ...] = field(
        default=(), repr=False, compare=False
    )
    failed_route_evidence: Phase3EFailedRouteEvidenceV1 | None = field(
        default=None, repr=False, compare=False
    )
    occurrence_failure_terminal: (
        Phase3EOccurrenceFailureTerminalV1 | None
    ) = None
    occurrence_failure_terminal_authority: (
        Phase3EOccurrenceFailureTerminalAuthorityV1 | None
    ) = field(default=None, repr=False, compare=False)
    occurrence_terminal: Phase3EOccurrenceTerminalArtifactV1 | None = None
    occurrence_terminal_result: object | None = field(
        default=None, repr=False, compare=False
    )
    control_failure_evidence: Phase3EOccurrenceControlFailureV1 | None = None
    infeasibility_certified: bool = False
    official_execution_allowed: bool = OFFICIAL_EXECUTION_ALLOWED
    official_scalar_cost: None = OFFICIAL_SCALAR_COST
    official_N_break_even: None = OFFICIAL_N_BREAK_EVEN
    workload_economics_gate_status: str = WORKLOAD_ECONOMICS_GATE_STATUS
    counter_completeness_gate_status: str = COUNTER_COMPLETENESS_GATE_STATUS
    unresolved_official_execution_obligations: tuple[str, ...] = (
        UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "closure_code", OccurrenceClosureCodeV1(self.closure_code)
        )
        if type(self.decision_runs) is not tuple or type(
            self.transactions
        ) is not tuple or type(self.work_components) is not tuple:
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence result histories must be immutable"
            )
        _verify_occurrence_result_history_v1(self)
        partial_common_positions = tuple(
            index
            for index, component in enumerate(self.work_components)
            if any(
                type(raw) is RunnerPartialCommonAccountingEvidenceV1
                for raw in component.raw_work
            )
        )
        if partial_common_positions and (
            partial_common_positions != (len(self.work_components) - 1,)
            or len(self.work_components) != 2 * len(self.decision_runs) + 1
            or self.work_components[-1].component_kind
            is not OccurrenceWorkComponentKind.COMMON_PREFIX
            or len(self.work_components[-1].raw_work) != 1
            or self.closure_code is not OccurrenceClosureCodeV1.PROTOCOL_FAILURE
            or type(self.control_failure_evidence)
            is not Phase3EOccurrenceControlFailureV1
            or self.control_failure_evidence.failure_stage
            not in _PARTIAL_COMMON_REJECTION_STAGES
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "PARTIAL_ACCOUNTED_COMMON is allowed only as the final unpaired "
                "authority-rejected package prefix"
            )
        noncertificate = self.closure_code in {
            OccurrenceClosureCodeV1.PROTOCOL_FAILURE,
            OccurrenceClosureCodeV1.FALLBACK_CAP_EXHAUSTED,
        }
        if noncertificate:
            if not isinstance(
                self.occurrence_terminal, Phase3EOccurrenceTerminalArtifactV1
            ):
                raise Phase3EOccurrenceRunnerV1Error(
                    "noncertificate occurrence lacks its typed terminal artifact"
                )
            from acfqp.semantic_verification_v1 import (
                SemanticRole,
                SemanticVerificationV1Error,
                require_semantic_verification_result_v1,
            )
            try:
                terminal_result = require_semantic_verification_result_v1(
                    self.occurrence_terminal_result,
                    SemanticRole.OCCURRENCE_TERMINAL,
                )
            except SemanticVerificationV1Error as error:
                raise Phase3EOccurrenceRunnerV1Error(
                    "noncertificate occurrence lacks semantic terminal authority"
                ) from error
            if (
                terminal_result.artifact != self.occurrence_terminal
                or terminal_result.attestation.artifact_id
                != self.occurrence_terminal.occurrence_terminal_artifact_id
                or terminal_result.binding.verification_lane is not LaneEnum.EVALUATION
            ):
                raise Phase3EOccurrenceRunnerV1Error(
                    "occurrence terminal authority is stale or not evaluation-only"
                )
            component_ids = tuple(
                row.occurrence_work_component_ref_id
                for row in self.occurrence_work.component_refs
            )
            binding = terminal_result.binding
            terminal_context = self.work_components[-1].route_context
            if (
                self.occurrence_terminal.occurrence_work_aggregate_id
                != self.occurrence_work.phase3e_occurrence_work_aggregate_id
                or self.occurrence_terminal.component_ref_ids != component_ids
                or self.occurrence_terminal.work_component_count
                != len(self.work_components)
                or self.occurrence_terminal.route_decision_context_id
                != terminal_context.route_decision_context_id
                or self.occurrence_terminal.logical_occurrence_id
                != terminal_context.logical_occurrence_id
                or self.occurrence_terminal.route_attempt_id
                != terminal_context.route_attempt_id
                or binding.route_context != terminal_context
                or binding.decision_point_id
                != self.occurrence_terminal.decision_point_id
                or binding.transaction_id
                != self.occurrence_terminal.transaction_id
                or terminal_result.recomputed_evidence_ids
                != tuple(
                    sorted(
                        (
                            self.occurrence_terminal.detail_id,
                            *self.occurrence_terminal.component_ref_ids,
                            *self.occurrence_terminal.runtime_tree_ids,
                            *self.occurrence_terminal.executor_recipe_ids,
                        )
                    )
                )
            ):
                raise Phase3EOccurrenceRunnerV1Error(
                    "occurrence terminal authority is spliced from another result history"
                )
            expected_code = (
                TerminalCode.PROTOCOL_FAILURE
                if self.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
                else TerminalCode.FALLBACK_CAP_EXHAUSTED
            )
            if self.occurrence_terminal.terminal_code is not expected_code:
                raise Phase3EOccurrenceRunnerV1Error(
                    "occurrence closure and typed terminal code disagree"
                )
        elif self.occurrence_terminal is not None or self.occurrence_terminal_result is not None:
            raise Phase3EOccurrenceRunnerV1Error(
                "certificate closure cannot carry a noncertificate terminal"
            )
        failed = self.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
        if failed:
            if len(self.decision_runs) > 2 or len(self.work_components) not in {
                2 * len(self.decision_runs),
                2 * len(self.decision_runs) + 1,
                2 * (len(self.decision_runs) + 1),
            }:
                raise Phase3EOccurrenceRunnerV1Error(
                    "failed occurrence work is not an exact completed-run plus "
                    "optional pre-freeze prefix/failed-route sequence"
                )
            authority = self.occurrence_failure_terminal_authority
            route_failure = self.failed_route_evidence is not None
            control_failure = self.control_failure_evidence is not None
            if route_failure == control_failure:
                raise Phase3EOccurrenceRunnerV1Error(
                    "protocol failure needs exactly one route or control detail"
                )
            if route_failure:
                authority = (
                    require_phase3e_occurrence_failure_terminal_authority_v1(
                        authority
                    )
                )
            if route_failure and (
                not isinstance(
                    self.occurrence_failure_terminal,
                    Phase3EOccurrenceFailureTerminalV1,
                )
                or not isinstance(
                    authority,
                    Phase3EOccurrenceFailureTerminalAuthorityV1,
                )
                or authority.terminal != self.occurrence_failure_terminal
                or authority.occurrence_work != self.occurrence_work
                or authority.failed_route_evidence is not self.failed_route_evidence
            ):
                raise Phase3EOccurrenceRunnerV1Error(
                    "route-failed occurrence lacks exact detailed authority"
                )
            if route_failure:
                registry = official_counter_registry_v1()
                profile = official_comparison_profile_v1(registry)
                actual_profile = official_actual_projection_profile_v1(
                    registry, profile
                )
                replayed_authority = (
                    verify_phase3e_occurrence_failure_terminal_v1(
                        self.occurrence_failure_terminal,
                        failure_evidence=self.failed_route_evidence,
                        successful_runs=self.decision_runs,
                        transactions=self.transactions,
                        components=self.work_components,
                        registry=registry,
                        comparison_profile=profile,
                        actual_profile=actual_profile,
                    )
                )
                if (
                    replayed_authority.terminal
                    != self.occurrence_failure_terminal
                    or replayed_authority.occurrence_work
                    != self.occurrence_work
                    or replayed_authority.failed_route_evidence
                    is not self.failed_route_evidence
                ):
                    raise Phase3EOccurrenceRunnerV1Error(
                        "route-failed occurrence authority differs from exact replay"
                    )
            if control_failure and any(
                row is not None
                for row in (
                    self.failed_route_evidence,
                    self.occurrence_failure_terminal,
                    self.occurrence_failure_terminal_authority,
                )
            ):
                raise Phase3EOccurrenceRunnerV1Error(
                    "control failure cannot claim failed-route evidence"
                )
        else:
            if not self.decision_runs or len(self.decision_runs) > 3:
                raise Phase3EOccurrenceRunnerV1Error(
                    "a successful occurrence needs one to three one-decision runs"
                )
            if len(self.work_components) != 2 * len(self.decision_runs):
                raise Phase3EOccurrenceRunnerV1Error(
                    "each decision run must retain its prefix and marginal work"
                )
            if any(
                row is not None
                for row in (
                    self.failed_route_evidence,
                    self.occurrence_failure_terminal,
                    self.occurrence_failure_terminal_authority,
                    self.control_failure_evidence,
                )
            ):
                raise Phase3EOccurrenceRunnerV1Error(
                    "certificate/cap closure cannot carry protocol-failure authority"
                )
        if tuple(row.transaction_index for row in self.transactions) != tuple(
            range(1, len(self.transactions) + 1)
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence local transaction indices are not continuous"
            )
        expected_infeasible = (
            self.closure_code
            is OccurrenceClosureCodeV1.FULL_GROUND_EXACT_INFEASIBLE
        )
        if self.infeasibility_certified is not expected_infeasible:
            raise Phase3EOccurrenceRunnerV1Error(
                "infeasibility flag disagrees with exact fallback closure"
            )
        if (
            self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate_status
            != WORKLOAD_ECONOMICS_GATE_STATUS
            or self.counter_completeness_gate_status
            != COUNTER_COMPLETENESS_GATE_STATUS
            or self.unresolved_official_execution_obligations
            != UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "official Phase-3E locks were relaxed"
            )


def _forbidden_local_executor(*_args: object, **_kwargs: object) -> Any:
    raise Phase3EOccurrenceRunnerV1Error(
        "fresh fallback-only decision attempted local execution"
    )


def _transaction_from_run(
    prepared: PreparedPhase3ERunV1,
    result: Phase3ERunResultV1,
) -> TransactionV1 | None:
    if result.selected_route is RouteSelection.FALLBACK:
        return None
    upper = result.selected_upper
    point = prepared.decision_point
    if (
        isinstance(upper.transaction_id, TypedNotApplicable)
        or isinstance(upper.transaction_index, TypedNotApplicable)
        or isinstance(upper.frontier_snapshot_id, TypedNotApplicable)
        or isinstance(point.transaction_index, TypedNotApplicable)
        or isinstance(point.frontier_snapshot_id, TypedNotApplicable)
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "selected local run lacks a complete transaction identity"
        )
    transaction = TransactionV1(
        prepared.context.logical_occurrence_id,
        prepared.context.route_attempt_id,
        point.decision_point_id,
        point.transaction_index,
        point.frontier_snapshot_id,
        upper.route_cap_profile_id,
    )
    if (
        transaction.transaction_id != upper.transaction_id
        or transaction.transaction_index != upper.transaction_index
        or transaction.frontier_snapshot_id != upper.frontier_snapshot_id
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "selected local upper does not bind the reconstructed transaction"
        )
    return transaction


def _components_for_run(
    prepared: PreparedPhase3ERunV1,
    result: Phase3ERunResultV1,
    transaction: TransactionV1 | None,
) -> tuple[OccurrenceWorkComponentEvidenceV1, ...]:
    accounted_common: object = result.common_prefix_work
    if result.two_stage_accounting_profile is True:
        accounted_common = RunnerCommonAccountingEvidenceV1(
            result.common_prefix_work,
            result.common_two_stage_accounting,
            result.common_verification_results,
            result.common_nonsemantic_records,
            prepared.context,
        )
    kind = (
        OccurrenceWorkComponentKind.LOCAL_TRANSACTION
        if result.selected_route is RouteSelection.LOCAL
        else OccurrenceWorkComponentKind.DIRECT_FALLBACK
    )
    return (
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.COMMON_PREFIX,
            prepared.context,
            prepared.decision_point,
            None,
            (accounted_common,),
        ),
        OccurrenceWorkComponentEvidenceV1(
            kind,
            prepared.context,
            prepared.decision_point,
            transaction,
            (
                RunnerMarginalWorkEvidenceV1(
                    result.aggregate_marginal_work,
                    result.selected_route_work,
                    result.verification_suffix_work,
                ),
            ),
        ),
    )


def _transaction_from_failed_route(
    prepared: PreparedPhase3ERunV1,
    evidence: Phase3EFailedRouteEvidenceV1,
) -> TransactionV1 | None:
    if evidence.selected_route is RouteSelection.FALLBACK:
        return None
    upper = evidence.selected_upper
    point = prepared.decision_point
    if (
        isinstance(upper.transaction_id, TypedNotApplicable)
        or isinstance(upper.transaction_index, TypedNotApplicable)
        or isinstance(upper.frontier_snapshot_id, TypedNotApplicable)
        or isinstance(point.transaction_index, TypedNotApplicable)
        or isinstance(point.frontier_snapshot_id, TypedNotApplicable)
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "failed local route lacks a complete transaction identity"
        )
    transaction = TransactionV1(
        prepared.context.logical_occurrence_id,
        prepared.context.route_attempt_id,
        point.decision_point_id,
        point.transaction_index,
        point.frontier_snapshot_id,
        upper.route_cap_profile_id,
    )
    if (
        transaction.transaction_id != upper.transaction_id
        or transaction.transaction_index != upper.transaction_index
        or transaction.frontier_snapshot_id != upper.frontier_snapshot_id
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "failed local route transaction differs from its selected upper"
        )
    return transaction


def _components_for_failed_route(
    prepared: PreparedPhase3ERunV1,
    evidence: Phase3EFailedRouteEvidenceV1,
    transaction: TransactionV1 | None,
) -> tuple[OccurrenceWorkComponentEvidenceV1, ...]:
    kind = (
        OccurrenceWorkComponentKind.LOCAL_TRANSACTION
        if evidence.selected_route is RouteSelection.LOCAL
        else OccurrenceWorkComponentKind.DIRECT_FALLBACK
    )
    accounted_common: object = evidence.common_prefix_work
    if evidence.common_two_stage_accounting is not None:
        accounted_common = RunnerCommonAccountingEvidenceV1(
            evidence.common_prefix_work,
            evidence.common_two_stage_accounting,
            evidence.common_verification_results,
            evidence.common_nonsemantic_records,
            evidence.context,
        )
    return (
        OccurrenceWorkComponentEvidenceV1(
            OccurrenceWorkComponentKind.COMMON_PREFIX,
            prepared.context,
            prepared.decision_point,
            None,
            (accounted_common,),
        ),
        OccurrenceWorkComponentEvidenceV1(
            kind,
            prepared.context,
            prepared.decision_point,
            transaction,
            (
                RunnerMarginalWorkEvidenceV1(
                    evidence.partial_marginal_work,
                    evidence.partial_route_work,
                    evidence.partial_verification_work,
                ),
            ),
        ),
    )


def _run_component_matches_v1(
    prefix: OccurrenceWorkComponentEvidenceV1,
    route: OccurrenceWorkComponentEvidenceV1,
    run: Phase3ERunResultV1,
) -> bool:
    if (
        prefix.component_kind
        is not OccurrenceWorkComponentKind.COMMON_PREFIX
        or prefix.transaction is not None
        or prefix.route_context != route.route_context
        or prefix.decision_point != route.decision_point
    ):
        return False
    binding = getattr(run.selected_work_result, "binding", None)
    run_context = getattr(binding, "route_context", None)
    if (
        run_context is None
        or prefix.route_context != run_context
        or prefix.decision_point.decision_point_id
        != run.decision.decision_point_id
        or run.selected_upper.decision_point_id
        != run.decision.decision_point_id
        or run.selected_upper.route_attempt_id != run_context.route_attempt_id
    ):
        return False
    if run.selected_route is RouteSelection.LOCAL:
        if (
            route.transaction is None
            or isinstance(run.selected_upper.transaction_id, TypedNotApplicable)
            or route.transaction.transaction_id
            != run.selected_upper.transaction_id
            or route.transaction.logical_occurrence_id
            != run_context.logical_occurrence_id
            or route.transaction.route_attempt_id
            != run_context.route_attempt_id
            or route.transaction.decision_point_id
            != run.decision.decision_point_id
        ):
            return False
    elif (
        run.selected_route is RouteSelection.FALLBACK
        and (
            route.transaction is not None
            or not isinstance(
                run.selected_upper.transaction_id, TypedNotApplicable
            )
        )
    ):
        return False
    accounted_common: object = run.common_prefix_work
    if run.two_stage_accounting_profile is True:
        accounted_common = RunnerCommonAccountingEvidenceV1(
            run.common_prefix_work,
            run.common_two_stage_accounting,
            run.common_verification_results,
            run.common_nonsemantic_records,
            run.selected_work_result.binding.route_context,
        )
    if prefix.raw_work != (accounted_common,) or len(route.raw_work) != 1:
        return False
    raw = route.raw_work[0]
    return (
        isinstance(raw, RunnerMarginalWorkEvidenceV1)
        and raw.aggregate == run.aggregate_marginal_work
        and raw.execution == run.selected_route_work
        and raw.verification_suffix == run.verification_suffix_work
        and route.component_kind
        is (
            OccurrenceWorkComponentKind.LOCAL_TRANSACTION
            if run.selected_route is RouteSelection.LOCAL
            else OccurrenceWorkComponentKind.DIRECT_FALLBACK
        )
    )


def _verify_occurrence_result_history_v1(
    result: Phase3EOccurrenceRunResultV1,
) -> None:
    """Replay the ordered result history before trusting closure metadata.

    The runtime result intentionally retains richer evidence than its
    serialized component references.  This boundary therefore reconstructs
    the aggregate from that evidence and binds every completed run and local
    transaction back to the exact ordered component sequence.
    """

    components = result.work_components
    runs = result.decision_runs
    if not components or not all(
        type(row) is OccurrenceWorkComponentEvidenceV1 for row in components
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence result requires an immutable typed work history"
        )
    if not all(type(row) is Phase3ERunResultV1 for row in runs):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence result requires an immutable typed decision history"
        )
    if not all(type(row) is TransactionV1 for row in result.transactions):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence result requires an immutable typed transaction history"
        )

    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(registry, profile)
    try:
        verify_phase3e_occurrence_work_aggregate_v1(
            result.occurrence_work,
            logical_occurrence_id=(
                components[0].route_context.logical_occurrence_id
            ),
            components=components,
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual_profile,
        )
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            f"occurrence result work history does not replay: {error}"
        ) from error

    if len(components) < 2 * len(runs):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence result omits work for a completed decision run"
        )
    for index, run in enumerate(runs):
        if not _run_component_matches_v1(
            components[2 * index], components[2 * index + 1], run
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence result splices or reorders a completed run"
            )

    component_transactions = tuple(
        component.transaction
        for component in components
        if component.component_kind
        is OccurrenceWorkComponentKind.LOCAL_TRANSACTION
    )
    if any(transaction is None for transaction in component_transactions) or (
        component_transactions != result.transactions
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence transaction history differs from local work components"
        )

    # PROTOCOL_FAILURE has a separate route/control terminal replay below.
    # Every other closure must be the semantic outcome of the final completed
    # run; a caller may not relabel a valid history with ``dataclasses.replace``.
    if result.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE:
        return
    if not runs:
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence closure lacks a completed decision run"
        )
    final_run = runs[-1]
    semantic_execution = final_run.route_execution.semantic_execution
    if result.closure_code is OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY:
        try:
            semantic_execution = require_trusted_local_execution_authority_v1(
                semantic_execution
            )
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(
                "local-recovery closure lacks its exact runtime authority"
            ) from error
        if (
            final_run.selected_route is not RouteSelection.LOCAL
            or type(semantic_execution) is not TrustedLocalExecutionV1
            or semantic_execution.post_audit is None
            or semantic_execution.post_audit.outcome
            is not PostAuditOutcome.CERTIFIED
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "local-recovery closure differs from the final run outcome"
            )
        return
    if (
        final_run.selected_route is not RouteSelection.FALLBACK
        or type(semantic_execution) is not GroundFallbackExecutionV1
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "fallback closure differs from the final run route"
        )
    try:
        semantic_execution = (
            require_trusted_ground_fallback_execution_authority_v1(
                semantic_execution
            )
        )
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            "fallback closure lacks its exact runtime authority"
        ) from error
    expected_fallback_closure = {
        GroundFallbackOutcome.FEASIBLE_CERTIFIED: (
            OccurrenceClosureCodeV1.FULL_GROUND_FALLBACK
        ),
        GroundFallbackOutcome.INFEASIBLE_CERTIFIED: (
            OccurrenceClosureCodeV1.FULL_GROUND_EXACT_INFEASIBLE
        ),
        GroundFallbackOutcome.CAP_EXHAUSTED: (
            OccurrenceClosureCodeV1.FALLBACK_CAP_EXHAUSTED
        ),
    }[semantic_execution.result.outcome]
    if result.closure_code is not expected_fallback_closure:
        raise Phase3EOccurrenceRunnerV1Error(
            "fallback closure differs from the final ground outcome"
        )


def verify_phase3e_occurrence_failure_terminal_v1(
    claimed: Phase3EOccurrenceFailureTerminalV1 | Mapping[str, Any],
    *,
    failure_evidence: Phase3EFailedRouteEvidenceV1,
    successful_runs: tuple[Phase3ERunResultV1, ...],
    transactions: tuple[TransactionV1, ...],
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> Phase3EOccurrenceFailureTerminalAuthorityV1:
    """Replay an occurrence-level protocol closure from all retained work."""

    terminal = (
        claimed
        if isinstance(claimed, Phase3EOccurrenceFailureTerminalV1)
        else Phase3EOccurrenceFailureTerminalV1.from_dict(claimed)
    )
    if type(successful_runs) is not tuple or not all(
        type(row) is Phase3ERunResultV1 for row in successful_runs
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "successful decision history must be an immutable typed tuple"
        )
    if type(transactions) is not tuple or not all(
        isinstance(row, TransactionV1) for row in transactions
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "transaction history must be an immutable typed tuple"
        )
    evidence = verify_failed_route_evidence_v1(
        failure_evidence,
        registry=registry,
        comparison_profile=comparison_profile,
    )
    if len(components) != 2 * (len(successful_runs) + 1):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence failure replay omits or adds a decision work pair"
        )
    if any(
        type(raw) is RunnerPartialCommonAccountingEvidenceV1
        for component in components
        for raw in component.raw_work
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "a failed-route terminal cannot pair PARTIAL_ACCOUNTED_COMMON "
            "with marginal work"
        )
    for index, run in enumerate(successful_runs):
        if not _run_component_matches_v1(
            components[2 * index], components[2 * index + 1], run
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence failure work splices or omits a successful run"
            )
    failure_prefix, failure_route = components[-2:]
    if (
        failure_prefix.route_context != evidence.context
        or failure_prefix.decision_point != evidence.decision_point
        or failure_prefix.component_kind
        is not OccurrenceWorkComponentKind.COMMON_PREFIX
        or len(failure_route.raw_work) != 1
        or failure_route.route_context != evidence.context
        or failure_route.decision_point != evidence.decision_point
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence failure pair uses another route context or decision"
        )
    failure_raw = failure_route.raw_work[0]
    if (
        not isinstance(failure_raw, RunnerMarginalWorkEvidenceV1)
        or failure_raw.execution != evidence.partial_route_work
        or failure_raw.verification_suffix != evidence.partial_verification_work
        or failure_raw.aggregate != evidence.partial_marginal_work
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence failure pair omits or splices exact partial marginal work"
        )
    local_transactions = tuple(
        row.transaction
        for row in components[1::2]
        if row.component_kind is OccurrenceWorkComponentKind.LOCAL_TRANSACTION
    )
    if local_transactions != transactions:
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence failure transaction history differs from charged work"
        )
    occurrence_work = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=evidence.context.logical_occurrence_id,
        components=components,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    verify_phase3e_occurrence_work_aggregate_v1(
        occurrence_work,
        logical_occurrence_id=evidence.context.logical_occurrence_id,
        components=components,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    expected_transaction: str | TypedNotApplicable
    if evidence.selected_route is RouteSelection.LOCAL:
        if not transactions or failure_route.transaction != transactions[-1]:
            raise Phase3EOccurrenceRunnerV1Error(
                "failed local terminal omits its transaction"
            )
        expected_transaction = transactions[-1].transaction_id
    else:
        if failure_route.transaction is not None:
            raise Phase3EOccurrenceRunnerV1Error(
                "failed fallback terminal fabricated a local transaction"
            )
        expected_transaction = TypedNotApplicable(
            "failed direct fallback has no local transaction"
        )
    proof = evidence.partial_marginal_work.aggregation_proof
    expected = Phase3EOccurrenceFailureTerminalV1(
        evidence.context.route_decision_context_id,
        evidence.context.logical_occurrence_id,
        evidence.context.route_attempt_id,
        evidence.decision_point.decision_point_id,
        expected_transaction,
        evidence.selected_route,
        occurrence_work.phase3e_occurrence_work_aggregate_id,
        failed_route_evidence_binding_id_v1(evidence),
        evidence.partial_route_work.work_vector.work_vector_id,
        evidence.partial_verification_work.work_vector.work_vector_id,
        evidence.partial_marginal_work.aggregate_work_vector.work_vector_id,
        proof.marginal_work_aggregation_proof_id,
        evidence.freeze_attestation.route_decision_freeze_attestation_id,
        evidence.access_log.access_event_log_id,
        len(successful_runs),
        len(successful_runs) + 1,
        len(transactions),
        len(components),
    )
    if terminal != expected:
        raise Phase3EOccurrenceRunnerV1Error(
            "claimed occurrence failure terminal differs from full evidence replay"
        )
    authority = Phase3EOccurrenceFailureTerminalAuthorityV1(
        expected,
        occurrence_work,
        evidence,
        _authority=_OCCURRENCE_FAILURE_TERMINAL_AUTHORITY,
    )
    return bind_runtime_authority_v1(
        authority,
        issuer=_OCCURRENCE_FAILURE_TERMINAL_AUTHORITY,
    )


def _observe_local_failure(
    *,
    prepared: PreparedPhase3ERunV1,
    result: Phase3ERunResultV1,
    transaction: TransactionV1,
    transactions: tuple[TransactionV1, ...],
    local_runs: tuple[Phase3ERunResultV1, ...],
) -> LocalFailureObservationV1 | None:
    execution = result.route_execution.semantic_execution
    try:
        execution = require_trusted_local_execution_authority_v1(execution)
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            "selected LOCAL run lacks trusted local semantic execution"
        ) from error
    # A sealed executor returns a merged selected-route WorkVector that also
    # contains construction/hash/I/O work.  The trusted local semantic result
    # intentionally binds the delegate WorkVector produced by the route
    # adapter, and the sealed execution merge proof binds that delegate to the
    # merged runner vector.  Comparing the local result directly with the
    # merged vector rejects every valid sealed occurrence (including a
    # certified first transaction) and would encourage relabelling the local
    # semantic artifact with accounting work it did not produce.
    semantic_route_work = (
        result.route_execution.delegate_execution_work
        if result.route_execution.delegate_execution_work is not None
        else result.selected_route_work
    )
    if (
        execution.local_result.selected_upper_id
        != result.selected_upper.route_upper_bound_envelope_id
        or execution.local_result.transaction_id != transaction.transaction_id
        or execution.local_result.work_vector_id
        != semantic_route_work.work_vector.work_vector_id
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "trusted local result does not bind the executed upper, transaction, "
            "and native WorkVector"
        )
    if execution.post_audit is not None:
        if execution.post_audit.outcome is PostAuditOutcome.CERTIFIED:
            return None
        if execution.post_audit.outcome is not PostAuditOutcome.FAILED:
            raise Phase3EOccurrenceRunnerV1Error(
                "local post-audit has an unregistered outcome"
            )
        return LocalFailureObservationV1(
            prepared.context,
            prepared.decision_point,
            transaction,
            result,
            LocalFailureKind.POST_AUDIT_FAILED,
            execution.post_audit.post_audit_certificate_id,
            transactions,
            local_runs,
        )
    if execution.local_result.outcome is LocalSolverOutcome.SEARCH_CAP_EXHAUSTED:
        failure_kind = LocalFailureKind.LOCAL_SEARCH_CAP_EXHAUSTED
    elif execution.local_result.outcome is LocalSolverOutcome.NO_FEASIBLE_ASSIGNMENT:
        failure_kind = LocalFailureKind.LOCAL_NO_FEASIBLE_ASSIGNMENT
    else:
        raise Phase3EOccurrenceRunnerV1Error(
            "a local candidate cannot close without a sound post-audit"
        )
    return LocalFailureObservationV1(
        prepared.context,
        prepared.decision_point,
        transaction,
        result,
        failure_kind,
        execution.local_result.local_transaction_result_id,
        transactions,
        local_runs,
    )


def _prepare_second_run(
    observation: LocalFailureObservationV1,
    package: SecondTransactionAuthorityPackageV1,
) -> tuple[
    PreparedPhase3ERunV1,
    SecondTransactionCandidateV1,
    LocalContinuationDirectiveV1,
]:
    if observation.failure_kind is not LocalFailureKind.POST_AUDIT_FAILED:
        raise Phase3EOccurrenceRunnerV1Error(
            "only a failed sound post-audit can request transaction 2"
        )
    local_execution = observation.run_result.route_execution.semantic_execution
    if type(local_execution) is not TrustedLocalExecutionV1 or (
        local_execution.post_audit is None
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "transaction-2 request lacks the failed trusted local execution"
        )
    from acfqp.semantic_verification_v1 import SemanticRole

    first_local_solver_result = _runner_route_semantic_result_v1(
        observation.run_result,
        SemanticRole.LOCAL_SOLVER_RESULT,
    )
    post_audit_failure_result = _runner_route_semantic_result_v1(
        observation.run_result,
        SemanticRole.POST_AUDIT,
    )
    try:
        candidate = prepare_second_transaction_candidate_v1(
            first_context=observation.context,
            first_decision_point=observation.decision_point,
            first_frontier=package.first_frontier,
            first_causal=package.first_causal,
            first_transaction=package.first_transaction,
            first_local_work=observation.run_result.selected_route_work.work_vector,
            first_local_upper_id=(
                observation.run_result.selected_upper.route_upper_bound_envelope_id
            ),
            first_fallback_upper_id=package.first_fallback_upper_id,
            first_local_result_artifact_id=(
                local_execution.local_result.local_transaction_result_id
            ),
            failed_post_audit_artifact_id=observation.failure_artifact_id,
            new_stitched_plan_binding_id=(
                local_execution.local_result.stitched_plan_binding_id
            ),
            second_context=package.second_context,
            second_frontier=package.second_frontier,
            second_causal=package.second_causal,
            second_decision_point=package.second_decision_point,
            second_transaction=package.second_transaction,
            second_local_cardinality=package.second_local_cardinality,
            second_fallback_cardinality=package.second_fallback_cardinality,
            second_local_upper=package.second_local_upper,
            second_fallback_upper=package.second_fallback_upper,
            second_route_decision=package.second_route_decision,
            second_common_prefix_work=package.second_common_prefix_work,
            cap_profile=package.cap_profile,
        )
        directive = authorize_second_transaction_v1(
            candidate,
            # The planner may describe the next structural candidate, but it
            # may not manufacture authority for work already executed.  That
            # authority is minted and charged by the preceding runner result.
            first_local_work_result=observation.run_result.selected_work_result,
            first_local_solver_result=first_local_solver_result,
            post_audit_failure_result=post_audit_failure_result,
            causal_result=package.causal_result,
            local_cardinality_result=package.local_cardinality_result,
            fallback_cardinality_result=package.fallback_cardinality_result,
            local_upper_result=package.local_upper_result,
            fallback_upper_result=package.fallback_upper_result,
            route_decision_result=package.route_decision_result,
        )
        directive = require_local_continuation_directive_authority_v1(
            directive
        )
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            f"transaction-2 authority failed closed: {error}"
        ) from error
    selected = package.second_route_decision.selected_route
    expected_route = (
        LocalContinuationRoute.SECOND_LOCAL_TRANSACTION
        if selected is RouteSelection.LOCAL
        else LocalContinuationRoute.DIRECT_FALLBACK
    )
    if directive.next_route is not expected_route:
        raise Phase3EOccurrenceRunnerV1Error(
            "transaction-2 directive disagrees with its authoritative route "
            "decision"
        )
    if selected is RouteSelection.LOCAL:
        if directive.second_transaction != package.second_transaction:
            raise Phase3EOccurrenceRunnerV1Error(
                "transaction-2 directive does not bind the authorized local "
                "transaction"
            )
        selected_upper_result = package.local_upper_result
    else:
        if directive.second_transaction is not None:
            raise Phase3EOccurrenceRunnerV1Error(
                "fallback continuation fabricated a local transaction"
            )
        selected_upper_result = package.fallback_upper_result
    authorization = Phase3EDecisionAuthorizationV1(
        package.route_decision_result,
        selected_upper_result,
        (
            package.causal_result,
            package.local_cardinality_result,
            package.fallback_cardinality_result,
            package.local_upper_result,
            package.fallback_upper_result,
            package.route_decision_result,
        ),
    )
    selected_executor = (
        package.local_executor
        if selected is RouteSelection.LOCAL
        else package.fallback_executor
    )
    executor_profile = _continuation_executor_profile_kwargs_v1(
        observation,
        selected_executor,
        selected,
    )
    accounting_profile = _continuation_accounting_profile_kwargs_v1(
        observation,
        package,
    )
    prepared = PreparedPhase3ERunV1(
        package.second_context,
        package.second_decision_point,
        package.reusable_rapm_id,
        package.failed_certificate_id,
        package.action_catalogue_id,
        package.preselection_reads,
        package.second_common_prefix_work,
        authorization,
        **executor_profile,
        **accounting_profile,
    )
    return prepared, candidate, directive


def _prepare_fallback_run(
    observation: LocalFailureObservationV1,
    package: FreshFallbackAuthorityPackageV1,
) -> tuple[
    PreparedPhase3ERunV1,
    FallbackAfterLocalFailureCandidateV1,
    AuthorizedFallbackAfterLocalFailureV1,
]:
    if package.context != observation.context or package.failure_kind is not (
        observation.failure_kind
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "fresh fallback package is bound to another failure context"
        )
    selected_local_upper_ids = {
        row.selected_upper.route_upper_bound_envelope_id
        for row in observation.completed_local_runs
    }
    if not selected_local_upper_ids <= set(package.prior_route_upper_ids):
        raise Phase3EOccurrenceRunnerV1Error(
            "fresh fallback history omitted a selected local upper"
        )
    from acfqp.semantic_verification_v1 import SemanticRole

    failure_role = (
        SemanticRole.POST_AUDIT
        if observation.failure_kind is LocalFailureKind.POST_AUDIT_FAILED
        else SemanticRole.LOCAL_SOLVER_RESULT
    )
    failure_result = _runner_route_semantic_result_v1(
        observation.run_result,
        failure_role,
    )
    try:
        candidate = prepare_fallback_after_local_failure_v1(
            context=package.context,
            failure_kind=package.failure_kind,
            failure_artifact_id=observation.failure_artifact_id,
            transactions=observation.completed_transactions,
            prior_local_work_vectors=tuple(
                row.selected_route_work.work_vector
                for row in observation.completed_local_runs
            ),
            local_cap_profile=package.local_cap_profile,
            prior_route_upper_ids=package.prior_route_upper_ids,
            fallback_common_prefix_work=package.fallback_common_prefix_work,
            fallback_decision_point=package.fallback_decision_point,
            fallback_cap_profile=package.fallback_cap_profile,
            fallback_cardinality_bound=package.fallback_cardinality_bound,
            fallback_cardinality=package.fallback_cardinality,
            fallback_upper=package.fallback_upper,
            fallback_route_decision=package.fallback_route_decision,
            prior_fallback_cardinality_bound_ids=(
                package.prior_fallback_cardinality_bound_ids
            ),
        )
        authorized = authorize_fallback_after_local_failure_v1(
            candidate,
            failure_result=failure_result,
            # Preserve the exact runner-owned authorities.  In particular, a
            # fresh-fallback planner has no seam through which it can replace
            # an expensive local WorkVector by a cheaper same-shaped vector.
            prior_work_results=tuple(
                row.selected_work_result
                for row in observation.completed_local_runs
            ),
            common_prefix_work_result=package.common_prefix_work_result,
            cardinality_result=package.cardinality_result,
            fallback_upper_result=package.fallback_upper_result,
            route_decision_result=package.route_decision_result,
        )
        authorized = require_authorized_fallback_after_local_failure_v1(
            authorized
        )
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            f"fresh fallback authority failed closed: {error}"
        ) from error
    authorization = Phase3EDecisionAuthorizationV1(
        package.route_decision_result,
        package.fallback_upper_result,
        (
            package.cardinality_result,
            package.fallback_upper_result,
            package.route_decision_result,
        ),
    )
    executor_profile = _continuation_executor_profile_kwargs_v1(
        observation,
        package.fallback_executor,
        RouteSelection.FALLBACK,
    )
    accounting_profile = _continuation_accounting_profile_kwargs_v1(
        observation,
        package,
    )
    prepared = PreparedPhase3ERunV1(
        package.context,
        package.fallback_decision_point,
        package.reusable_rapm_id,
        package.failed_certificate_id,
        package.action_catalogue_id,
        package.preselection_reads,
        package.fallback_common_prefix_work,
        authorization,
        **executor_profile,
        **accounting_profile,
    )
    return prepared, candidate, authorized


def _fallback_closure(result: Phase3ERunResultV1) -> OccurrenceClosureCodeV1:
    execution = result.route_execution.semantic_execution
    try:
        execution = require_trusted_ground_fallback_execution_authority_v1(
            execution
        )
    except ValueError as error:
        raise Phase3EOccurrenceRunnerV1Error(
            "selected FALLBACK run lacks trusted ground-fallback execution"
        ) from error
    outcome = execution.result.outcome
    if outcome is GroundFallbackOutcome.FEASIBLE_CERTIFIED:
        return OccurrenceClosureCodeV1.FULL_GROUND_FALLBACK
    if outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED:
        return OccurrenceClosureCodeV1.FULL_GROUND_EXACT_INFEASIBLE
    if outcome is GroundFallbackOutcome.CAP_EXHAUSTED:
        return OccurrenceClosureCodeV1.FALLBACK_CAP_EXHAUSTED
    raise Phase3EOccurrenceRunnerV1Error(
        "ground fallback produced an unregistered terminal outcome"
    )


def _finish(
    *,
    closure: OccurrenceClosureCodeV1,
    runs: tuple[Phase3ERunResultV1, ...],
    transactions: tuple[TransactionV1, ...],
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    continuation_authorities: tuple[object, ...],
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> Phase3EOccurrenceRunResultV1:
    aggregate = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=(
            components[0].route_context.logical_occurrence_id
        ),
        components=components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )
    verify_phase3e_occurrence_work_aggregate_v1(
        aggregate,
        logical_occurrence_id=(
            components[0].route_context.logical_occurrence_id
        ),
        components=components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )
    terminal: Phase3EOccurrenceTerminalArtifactV1 | None = None
    terminal_result: object | None = None
    if closure is OccurrenceClosureCodeV1.FALLBACK_CAP_EXHAUSTED:
        last_run = runs[-1]
        semantic_execution = last_run.route_execution.semantic_execution
        if type(semantic_execution) is not GroundFallbackExecutionV1:
            raise Phase3EOccurrenceRunnerV1Error(
                "fallback-cap occurrence lacks ground fallback evidence"
            )
        terminal, terminal_result = _make_occurrence_terminal_v1(
            code=TerminalCode.FALLBACK_CAP_EXHAUSTED,
            aggregate=aggregate,
            components=components,
            runs=runs,
            transactions=transactions,
            context=components[-1].route_context,
            decision_point_id=components[-1].decision_point.decision_point_id,
            transaction_id=TypedNotApplicable(
                "fallback-cap occurrence terminal has no local transaction"
            ),
            detail_id=(
                semantic_execution.result.ground_fallback_result_id
            ),
            detail_evidence=semantic_execution,
            registry=registry,
        )
    return Phase3EOccurrenceRunResultV1(
        closure_code=closure,
        decision_runs=runs,
        transactions=transactions,
        work_components=components,
        occurrence_work=aggregate,
        continuation_authorities=continuation_authorities,
        occurrence_terminal=terminal,
        occurrence_terminal_result=terminal_result,
        infeasibility_certified=(
            closure is OccurrenceClosureCodeV1.FULL_GROUND_EXACT_INFEASIBLE
        ),
    )


def _sealed_runtime_provenance_v1(
    runs: tuple[Phase3ERunResultV1, ...],
    extra_prepared: PreparedPhase3ERunV1 | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    trees: list[str] = []
    recipes: list[str] = []
    for run in runs:
        if run.sealed_executor_profile:
            assert run.runtime_tree_id is not None
            assert run.executor_recipe_id is not None
            trees.append(run.runtime_tree_id)
            recipes.append(run.executor_recipe_id)
    if extra_prepared is not None and extra_prepared.sealed_executor_profile:
        assert extra_prepared.runtime_tree_id is not None
        assert extra_prepared.executor_recipe_id is not None
        trees.append(extra_prepared.runtime_tree_id)
        recipes.append(extra_prepared.executor_recipe_id)
    return tuple(trees), tuple(recipes)


def _make_occurrence_terminal_v1(
    *,
    code: TerminalCode,
    aggregate: Phase3EOccurrenceWorkAggregateV1,
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    runs: tuple[Phase3ERunResultV1, ...],
    transactions: tuple[TransactionV1, ...],
    context: RouteDecisionContextV1,
    decision_point_id: str | TypedNotApplicable,
    transaction_id: str | TypedNotApplicable,
    detail_id: str,
    detail_evidence: object,
    registry: CounterRegistryV1,
    extra_prepared: PreparedPhase3ERunV1 | None = None,
) -> tuple[Phase3EOccurrenceTerminalArtifactV1, object]:
    """Create and independently attest one aggregate noncertificate."""

    trees, recipes = _sealed_runtime_provenance_v1(runs, extra_prepared)
    artifact = Phase3EOccurrenceTerminalArtifactV1(
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        decision_point_id,
        transaction_id,
        aggregate.phase3e_occurrence_work_aggregate_id,
        tuple(
            row.occurrence_work_component_ref_id
            for row in aggregate.component_refs
        ),
        code,
        sum(
            row.component_kind is OccurrenceWorkComponentKind.COMMON_PREFIX
            for row in components
        ),
        sum(
            row.component_kind is OccurrenceWorkComponentKind.LOCAL_TRANSACTION
            for row in components
        ),
        len(components),
        detail_id,
        trees,
        recipes,
    )
    from acfqp.semantic_verification_v1 import (
        AttestationContextV1,
        SemanticRole,
        semantic_verifier_spec_v1,
        verify_occurrence_terminal_semantics_v1,
    )

    spec = semantic_verifier_spec_v1(SemanticRole.OCCURRENCE_TERMINAL)
    verification_record = CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(LaneEnum.EVALUATION),
        1,
        recorder_id="phase3e-occurrence-terminal-evaluation-v1",
    )
    result = verify_occurrence_terminal_semantics_v1(
        artifact,
        occurrence_work=aggregate,
        components=components,
        decision_runs=runs,
        detail_evidence=detail_evidence,
        binding=AttestationContextV1(
            context,
            decision_point_id,
            transaction_id,
            0,
            LaneEnum.EVALUATION,
        ),
        verification_work_record=verification_record,
        extra_prepared=extra_prepared,
        registry=registry,
    )
    return artifact, result


def _verified_control_prefix_v1(
    *,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    common_work: RecordedWorkV1,
    semantic_results: tuple[object, ...] = (),
    nonsemantic_records: tuple[CounterRecordV1, ...] = (),
    existing: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> OccurrenceWorkComponentEvidenceV1 | None:
    """Return a real pre-freeze prefix only when native replay accepts it."""

    from acfqp.semantic_verification_v1 import SemanticVerificationResultV1

    exact_results = tuple(
        row
        for row in semantic_results
        if type(row) is SemanticVerificationResultV1
    )
    raw_evidence: object = common_work
    if exact_results or nonsemantic_records:
        raw_evidence = derive_runner_partial_common_accounting_v1(
            core=common_work,
            semantic_results=exact_results,
            nonsemantic_records=nonsemantic_records,
            route_context=context,
            decision_point_id=decision_point.decision_point_id,
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual_profile,
        )
    candidate = OccurrenceWorkComponentEvidenceV1(
        OccurrenceWorkComponentKind.COMMON_PREFIX,
        context,
        decision_point,
        None,
        (raw_evidence,),
    )
    try:
        derive_phase3e_occurrence_work_aggregate_v1(
            logical_occurrence_id=context.logical_occurrence_id,
            components=existing + (candidate,),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual_profile,
        )
    except ValueError:
        return None
    return candidate


def _finish_control_failure(
    *,
    stage: str,
    error: Exception,
    runs: tuple[Phase3ERunResultV1, ...],
    transactions: tuple[TransactionV1, ...],
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    continuation_authorities: tuple[object, ...],
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
    prepared: PreparedPhase3ERunV1 | None = None,
    pending_context: RouteDecisionContextV1 | None = None,
    pending_point: DecisionPointV1 | None = None,
    pending_common_work: RecordedWorkV1 | None = None,
    pending_semantic_results: tuple[object, ...] = (),
    pending_nonsemantic_records: tuple[CounterRecordV1, ...] = (),
) -> Phase3EOccurrenceRunResultV1:
    """Close a continuation/control failure without discarding prior work."""

    if not runs:
        raise Phase3EOccurrenceRunnerV1Error(
            "control failure closure requires at least one completed route"
        ) from error
    final_components = components
    context = pending_context
    point = pending_point
    common = pending_common_work
    if prepared is not None:
        context = prepared.context
        point = prepared.decision_point
        common = prepared.common_prefix_work
    if context is not None and point is not None and common is not None:
        prefix = _verified_control_prefix_v1(
            context=context,
            decision_point=point,
            common_work=common,
            semantic_results=pending_semantic_results,
            nonsemantic_records=pending_nonsemantic_records,
            existing=components,
            registry=registry,
            profile=profile,
            actual_profile=actual_profile,
        )
        if prefix is not None:
            final_components += (prefix,)
    if not final_components:
        raise Phase3EOccurrenceRunnerV1Error(
            "control failure has no retained occurrence work"
        ) from error
    terminal_component = final_components[-1]
    context = terminal_component.route_context
    point = terminal_component.decision_point
    aggregate = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=context.logical_occurrence_id,
        components=final_components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )
    accounted_common: str | TypedNotApplicable = (
        aggregate.component_refs[-1].raw_work_refs[0].work_vector_id
        if terminal_component.component_kind
        is OccurrenceWorkComponentKind.COMMON_PREFIX
        else TypedNotApplicable(
            "control failure occurred before another verifiable common core"
        )
    )
    detail = Phase3EOccurrenceControlFailureV1(
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        stage,
        type(error).__name__,
        str(error),
        len(runs),
        accounted_common,
    )
    occurrence_terminal, terminal_result = _make_occurrence_terminal_v1(
        code=TerminalCode.PROTOCOL_FAILURE,
        aggregate=aggregate,
        components=final_components,
        runs=runs,
        transactions=transactions,
        context=context,
        decision_point_id=point.decision_point_id,
        transaction_id=TypedNotApplicable(
            "control failure occurred before a selected route completed"
        ),
        detail_id=detail.occurrence_control_failure_id,
        detail_evidence=detail,
        registry=registry,
        extra_prepared=prepared,
    )
    return Phase3EOccurrenceRunResultV1(
        closure_code=OccurrenceClosureCodeV1.PROTOCOL_FAILURE,
        decision_runs=runs,
        transactions=transactions,
        work_components=final_components,
        occurrence_work=aggregate,
        continuation_authorities=continuation_authorities,
        occurrence_terminal=occurrence_terminal,
        occurrence_terminal_result=terminal_result,
        control_failure_evidence=detail,
        infeasibility_certified=False,
    )


def _finish_failure(
    *,
    failure: Phase3ERouteExecutionFailedV1,
    runs: tuple[Phase3ERunResultV1, ...],
    transactions: tuple[TransactionV1, ...],
    components: tuple[OccurrenceWorkComponentEvidenceV1, ...],
    continuation_authorities: tuple[object, ...],
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
    prepared: PreparedPhase3ERunV1,
) -> Phase3EOccurrenceRunResultV1:
    evidence = verify_failed_route_evidence_v1(
        failure.evidence,
        registry=registry,
        comparison_profile=profile,
    )
    sealed_failure = evidence.sealed_executor_failure_evidence
    if sealed_failure is not None and (
        prepared.sealed_executor_profile is not True
        or prepared.runtime_tree_id != sealed_failure.runtime_tree_id
        or prepared.executor_recipe_id != sealed_failure.executor_recipe_id
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "sealed failure evidence is spliced from another prepared runtime"
        )
    if prepared.sealed_executor_profile is True and sealed_failure is None:
        raise Phase3EOccurrenceRunnerV1Error(
            "sealed failed route omits its constructor failure evidence"
        )
    occurrence_work = derive_phase3e_occurrence_work_aggregate_v1(
        logical_occurrence_id=evidence.context.logical_occurrence_id,
        components=components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )
    transaction_ref: str | TypedNotApplicable = (
        transactions[-1].transaction_id
        if evidence.selected_route is RouteSelection.LOCAL
        else TypedNotApplicable("failed direct fallback has no local transaction")
    )
    proof = evidence.partial_marginal_work.aggregation_proof
    terminal = Phase3EOccurrenceFailureTerminalV1(
        evidence.context.route_decision_context_id,
        evidence.context.logical_occurrence_id,
        evidence.context.route_attempt_id,
        evidence.decision_point.decision_point_id,
        transaction_ref,
        evidence.selected_route,
        occurrence_work.phase3e_occurrence_work_aggregate_id,
        failed_route_evidence_binding_id_v1(evidence),
        evidence.partial_route_work.work_vector.work_vector_id,
        evidence.partial_verification_work.work_vector.work_vector_id,
        evidence.partial_marginal_work.aggregate_work_vector.work_vector_id,
        proof.marginal_work_aggregation_proof_id,
        evidence.freeze_attestation.route_decision_freeze_attestation_id,
        evidence.access_log.access_event_log_id,
        len(runs),
        len(runs) + 1,
        len(transactions),
        len(components),
    )
    authority = verify_phase3e_occurrence_failure_terminal_v1(
        terminal,
        failure_evidence=evidence,
        successful_runs=runs,
        transactions=transactions,
        components=components,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )
    if authority.occurrence_work != occurrence_work:
        raise Phase3EOccurrenceRunnerV1Error(
            "occurrence failure authority reconstructed another work aggregate"
        )
    occurrence_terminal, occurrence_terminal_result = (
        _make_occurrence_terminal_v1(
            code=TerminalCode.PROTOCOL_FAILURE,
            aggregate=occurrence_work,
            components=components,
            runs=runs,
            transactions=transactions,
            context=evidence.context,
            decision_point_id=evidence.decision_point.decision_point_id,
            transaction_id=transaction_ref,
            detail_id=terminal.occurrence_failure_terminal_id,
            detail_evidence=authority,
            registry=registry,
            extra_prepared=prepared,
        )
    )
    return Phase3EOccurrenceRunResultV1(
        closure_code=OccurrenceClosureCodeV1.PROTOCOL_FAILURE,
        decision_runs=runs,
        transactions=transactions,
        work_components=components,
        occurrence_work=occurrence_work,
        continuation_authorities=continuation_authorities,
        failed_route_evidence=evidence,
        occurrence_failure_terminal=terminal,
        occurrence_failure_terminal_authority=authority,
        occurrence_terminal=occurrence_terminal,
        occurrence_terminal_result=occurrence_terminal_result,
        infeasibility_certified=False,
    )


def run_phase3e_occurrence_v1(
    initial_prepared: PreparedPhase3ERunV1,
    *,
    local_executor: Phase3ERouteExecutorV1,
    fallback_executor: Phase3ERouteExecutorV1,
    second_transaction_planner: SecondTransactionPlannerV1 | None = None,
    fresh_fallback_planner: FreshFallbackPlannerV1 | None = None,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> Phase3EOccurrenceRunResultV1:
    """Execute and account one logical occurrence, with at most two locals.

    The first decision and every subsequent decision still pass independently
    through :func:`run_phase3e`.  No continuation callback is invoked until the
    preceding selected route is complete and its native work is sealed.
    """

    trusted_registry = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(
        trusted_registry
    )
    actual_profile = official_actual_projection_profile_v1(
        trusted_registry, profile
    )
    runs: list[Phase3ERunResultV1] = []
    transactions: list[TransactionV1] = []
    components: list[OccurrenceWorkComponentEvidenceV1] = []
    continuation_authorities: list[object] = []

    def execute(
        prepared: PreparedPhase3ERunV1,
        local: Phase3ERouteExecutorV1,
        fallback: Phase3ERouteExecutorV1,
    ) -> tuple[
        Phase3ERunResultV1 | None,
        TransactionV1 | None,
        Phase3ERouteExecutionFailedV1 | None,
    ]:
        try:
            result = run_phase3e(
                prepared,
                local_executor=local,
                fallback_executor=fallback,
                registry=trusted_registry,
                comparison_profile=profile,
            )
        except Phase3ERouteExecutionFailedV1 as failure:
            evidence = verify_failed_route_evidence_v1(
                failure.evidence,
                registry=trusted_registry,
                comparison_profile=profile,
            )
            if (
                evidence.context != prepared.context
                or evidence.decision_point != prepared.decision_point
            ):
                raise Phase3EOccurrenceRunnerV1Error(
                    "failed route evidence uses another prepared decision"
                ) from failure
            transaction = _transaction_from_failed_route(prepared, evidence)
            if transaction is not None:
                transactions.append(transaction)
            components.extend(
                _components_for_failed_route(prepared, evidence, transaction)
            )
            return None, transaction, failure
        if type(result) is not Phase3ERunResultV1:
            raise Phase3EOccurrenceRunnerV1Error(
                "one-decision runner returned an untyped result"
            )
        try:
            replace(result)
        except ValueError as error:
            raise Phase3EOccurrenceRunnerV1Error(
                f"one-decision runner returned an invalid typed result: {error}"
            ) from error
        transaction = _transaction_from_run(prepared, result)
        runs.append(result)
        if transaction is not None:
            transactions.append(transaction)
        components.extend(_components_for_run(prepared, result, transaction))
        return result, transaction, None

    result, transaction, failure = execute(
        initial_prepared, local_executor, fallback_executor
    )
    if failure is not None:
        return _finish_failure(
            failure=failure,
            runs=tuple(runs),
            transactions=tuple(transactions),
            components=tuple(components),
            continuation_authorities=tuple(continuation_authorities),
            registry=trusted_registry,
            profile=profile,
            actual_profile=actual_profile,
            prepared=initial_prepared,
        )
    assert result is not None
    if result.selected_route is RouteSelection.FALLBACK:
        return _finish(
            closure=_fallback_closure(result),
            runs=tuple(runs),
            transactions=tuple(transactions),
            components=tuple(components),
            continuation_authorities=tuple(continuation_authorities),
            registry=trusted_registry,
            profile=profile,
            actual_profile=actual_profile,
        )
    assert transaction is not None
    observation = _observe_local_failure(
        prepared=initial_prepared,
        result=result,
        transaction=transaction,
        transactions=tuple(transactions),
        local_runs=tuple(runs),
    )
    if observation is None:
        return _finish(
            closure=OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY,
            runs=tuple(runs),
            transactions=tuple(transactions),
            components=tuple(components),
            continuation_authorities=tuple(continuation_authorities),
            registry=trusted_registry,
            profile=profile,
            actual_profile=actual_profile,
        )

    # A failed post-audit gets one fresh, strictly deeper decision point.  Its
    # marginal selector may authorize transaction 2 or direct fallback.
    # Cap/no-assignment closures skip directly to a new fallback-only decision.
    if observation.failure_kind is LocalFailureKind.POST_AUDIT_FAILED:
        if second_transaction_planner is None:
            return _finish_control_failure(
                stage="MISSING_SECOND_TRANSACTION_PLANNER",
                error=Phase3EOccurrenceRunnerV1Error(
                    "failed transaction 1 lacks a transaction-2 authority planner"
                ),
                runs=tuple(runs),
                transactions=tuple(transactions),
                components=tuple(components),
                continuation_authorities=tuple(continuation_authorities),
                registry=trusted_registry,
                profile=profile,
                actual_profile=actual_profile,
            )
        try:
            package = second_transaction_planner(observation)
        except Exception as error:
            return _finish_control_failure(
                stage="SECOND_TRANSACTION_PLANNER_FAILED",
                error=error,
                runs=tuple(runs),
                transactions=tuple(transactions),
                components=tuple(components),
                continuation_authorities=tuple(continuation_authorities),
                registry=trusted_registry,
                profile=profile,
                actual_profile=actual_profile,
            )
        if type(package) is not SecondTransactionAuthorityPackageV1:
            return _finish_control_failure(
                stage="UNTYPED_SECOND_TRANSACTION_PACKAGE",
                error=Phase3EOccurrenceRunnerV1Error(
                    "transaction-2 planner returned an untyped package"
                ),
                runs=tuple(runs),
                transactions=tuple(transactions),
                components=tuple(components),
                continuation_authorities=tuple(continuation_authorities),
                registry=trusted_registry,
                profile=profile,
                actual_profile=actual_profile,
            )
        try:
            second_prepared, candidate, directive = _prepare_second_run(
                observation, package
            )
        except Exception as error:
            return _finish_control_failure(
                stage="SECOND_TRANSACTION_AUTHORITY_REJECTED",
                error=error,
                runs=tuple(runs),
                transactions=tuple(transactions),
                components=tuple(components),
                continuation_authorities=tuple(continuation_authorities),
                registry=trusted_registry,
                profile=profile,
                actual_profile=actual_profile,
                pending_context=package.second_context,
                pending_point=package.second_decision_point,
                pending_common_work=package.second_common_prefix_work,
                pending_semantic_results=(
                    package.causal_result,
                    package.local_cardinality_result,
                    package.fallback_cardinality_result,
                    package.local_upper_result,
                    package.fallback_upper_result,
                    package.route_decision_result,
                ),
                pending_nonsemantic_records=(
                    package.common_nonsemantic_records
                ),
            )
        continuation_authorities.extend((candidate, directive))
        second_result, second_transaction, failure = execute(
            second_prepared,
            (
                package.local_executor
                if directive.next_route
                is LocalContinuationRoute.SECOND_LOCAL_TRANSACTION
                else _forbidden_local_executor
            ),
            package.fallback_executor,
        )
        if failure is not None:
            return _finish_failure(
                failure=failure,
                runs=tuple(runs),
                transactions=tuple(transactions),
                components=tuple(components),
                continuation_authorities=tuple(continuation_authorities),
                registry=trusted_registry,
                profile=profile,
                actual_profile=actual_profile,
                prepared=second_prepared,
            )
        assert second_result is not None
        if directive.next_route is LocalContinuationRoute.DIRECT_FALLBACK:
            if second_result.selected_route is not RouteSelection.FALLBACK or (
                second_transaction is not None
            ):
                raise Phase3EOccurrenceRunnerV1Error(
                    "authorized second-decision fallback executed another route"
                )
            return _finish(
                closure=_fallback_closure(second_result),
                runs=tuple(runs),
                transactions=tuple(transactions),
                components=tuple(components),
                continuation_authorities=tuple(continuation_authorities),
                registry=trusted_registry,
                profile=profile,
                actual_profile=actual_profile,
            )
        if second_result.selected_route is not RouteSelection.LOCAL or (
            second_transaction is None
        ):
            raise Phase3EOccurrenceRunnerV1Error(
                "authorized transaction 2 executed another route"
            )
        if second_transaction != package.second_transaction:
            raise Phase3EOccurrenceRunnerV1Error(
                "executed transaction 2 differs from its authority package"
            )
        observation = _observe_local_failure(
            prepared=second_prepared,
            result=second_result,
            transaction=second_transaction,
            transactions=tuple(transactions),
            local_runs=tuple(runs),
        )
        if observation is None:
            return _finish(
                closure=OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY,
                runs=tuple(runs),
                transactions=tuple(transactions),
                components=tuple(components),
                continuation_authorities=tuple(continuation_authorities),
                registry=trusted_registry,
                profile=profile,
                actual_profile=actual_profile,
            )

    if fresh_fallback_planner is None:
        return _finish_control_failure(
            stage="MISSING_FRESH_FALLBACK_PLANNER",
            error=Phase3EOccurrenceRunnerV1Error(
                "local failure lacks a fresh fallback-only authority planner"
            ),
            runs=tuple(runs),
            transactions=tuple(transactions),
            components=tuple(components),
            continuation_authorities=tuple(continuation_authorities),
            registry=trusted_registry,
            profile=profile,
            actual_profile=actual_profile,
        )
    try:
        fallback_package = fresh_fallback_planner(observation)
    except Exception as error:
        return _finish_control_failure(
            stage="FRESH_FALLBACK_PLANNER_FAILED",
            error=error,
            runs=tuple(runs),
            transactions=tuple(transactions),
            components=tuple(components),
            continuation_authorities=tuple(continuation_authorities),
            registry=trusted_registry,
            profile=profile,
            actual_profile=actual_profile,
        )
    if type(fallback_package) is not FreshFallbackAuthorityPackageV1:
        return _finish_control_failure(
            stage="UNTYPED_FRESH_FALLBACK_PACKAGE",
            error=Phase3EOccurrenceRunnerV1Error(
                "fallback planner returned an untyped authority package"
            ),
            runs=tuple(runs),
            transactions=tuple(transactions),
            components=tuple(components),
            continuation_authorities=tuple(continuation_authorities),
            registry=trusted_registry,
            profile=profile,
            actual_profile=actual_profile,
        )
    try:
        fallback_prepared, fallback_candidate, fallback_authority = (
            _prepare_fallback_run(observation, fallback_package)
        )
    except Exception as error:
        return _finish_control_failure(
            stage="FRESH_FALLBACK_AUTHORITY_REJECTED",
            error=error,
            runs=tuple(runs),
            transactions=tuple(transactions),
            components=tuple(components),
            continuation_authorities=tuple(continuation_authorities),
            registry=trusted_registry,
            profile=profile,
            actual_profile=actual_profile,
            pending_context=fallback_package.context,
            pending_point=fallback_package.fallback_decision_point,
            pending_common_work=fallback_package.fallback_common_prefix_work,
            pending_semantic_results=(
                fallback_package.common_prefix_work_result,
                fallback_package.cardinality_result,
                fallback_package.fallback_upper_result,
                fallback_package.route_decision_result,
            ),
            pending_nonsemantic_records=(
                fallback_package.common_nonsemantic_records
            ),
        )
    continuation_authorities.extend(
        (fallback_candidate, fallback_authority)
    )
    fallback_result, fallback_transaction, failure = execute(
        fallback_prepared,
        _forbidden_local_executor,
        fallback_package.fallback_executor,
    )
    if failure is not None:
        return _finish_failure(
            failure=failure,
            runs=tuple(runs),
            transactions=tuple(transactions),
            components=tuple(components),
            continuation_authorities=tuple(continuation_authorities),
            registry=trusted_registry,
            profile=profile,
            actual_profile=actual_profile,
            prepared=fallback_prepared,
        )
    assert fallback_result is not None
    if fallback_result.selected_route is not RouteSelection.FALLBACK or (
        fallback_transaction is not None
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "fresh fallback-only decision executed another route"
        )
    return _finish(
        closure=_fallback_closure(fallback_result),
        runs=tuple(runs),
        transactions=tuple(transactions),
        components=tuple(components),
        continuation_authorities=tuple(continuation_authorities),
        registry=trusted_registry,
        profile=profile,
        actual_profile=actual_profile,
    )


__all__ = [
    "FreshFallbackAuthorityPackageV1",
    "FreshFallbackPlannerV1",
    "LocalFailureObservationV1",
    "OccurrenceClosureCodeV1",
    "Phase3EOccurrenceFailureTerminalAuthorityV1",
    "Phase3EOccurrenceFailureTerminalV1",
    "Phase3EOccurrenceControlFailureV1",
    "Phase3EOccurrenceRunResultV1",
    "Phase3EOccurrenceRunnerV1Error",
    "Phase3EOccurrenceTerminalArtifactV1",
    "SecondTransactionAuthorityPackageV1",
    "SecondTransactionPlannerV1",
    "failed_route_evidence_binding_id_v1",
    "run_phase3e_occurrence_v1",
    "require_phase3e_occurrence_failure_terminal_authority_v1",
    "verify_phase3e_occurrence_failure_terminal_v1",
]
