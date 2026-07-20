"""Executable, non-official Phase-3E estimate-before-execute consumer.

``run_phase3e`` consumes a reusable-RAPM preparation and authority-bearing
route decision.  It freezes that decision through the FQ13 access controller,
executes exactly one selected route, emits separate common-prefix and marginal
native work vectors, and checks the marginal actual vector componentwise
against the selected, semantically verified upper.

The runner cannot mint cardinality, route-upper, or route-decision authority.
Those objects enter through :class:`Phase3EDecisionAuthorizationV1` and are
accepted only as non-serializable ``SemanticVerificationResultV1`` handles.
This keeps the orchestration executable while failing closed when an
authority is unavailable.

This vertical slice intentionally preserves every official lock.  Producing a
successful runtime result here is not the workload-economics or counter-
completeness Gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessOperation,
    AccessProtocolV1Error,
    AccessProtocolViolation,
    AccessRouteScope,
    FailClosedAccessController,
    ForbiddenAccessViolationV1,
    PRESELECTION_READ_OPERATIONS,
    ProtocolSequenceProfileV1,
    RouteDecisionFreezeAttestationV1,
    decide_then_execute,
    local_execution_stages_v1,
    replay_access_protocol,
)
from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRegistryV1,
    RouteKindEnum,
    SHARED_AXES,
    WorkVectorV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    UpperBoundViolationError,
    WITHIN_SELECTED_UPPER,
    official_actual_projection_profile_v1,
)
from acfqp.marginal_accounting_v1 import (
    AggregatedMarginalWorkV1,
    derive_marginal_work_aggregate_v1,
)
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    NativeRecorderV1Error,
    RecordedWorkV1,
    derive_failed_recorded_work_v1,
    derive_recorded_work_v1,
    verify_recorded_work_v1,
)
from acfqp.phase3e_ids import (
    PRESELECTION_NOT_APPLICABLE_BINDING_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TypedNotApplicable,
)


PROFILE_KEY = "phase3e_accounted_dynamic_routing_v0"
VERTICAL_SLICE_STATUS = "PHASE3E_ACCOUNTED_VERTICAL_SLICE_EXECUTED"
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
UNASSIGNED_POSTFREEZE_OPERATIONAL_LEAVES = (
    "common.hash_invocations",
)
UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS = (
    "NON_SELF_REFERENTIAL_TERMINAL_VERIFICATION_ACCOUNTING",
    "CONTINUATION_WORK_VECTOR_VERIFICATION_ACCOUNTING",
    "SEALED_POSTFREEZE_EXECUTOR_AND_RUNTIME_TREE",
    "OCCURRENCE_LEVEL_NONCERTIFICATE_AND_AGGREGATE_TERMINAL",
)


class Phase3ERunnerV1Error(ValueError):
    """The prepared authority chain or selected execution is inadmissible."""


def _preselection_reference_id_v1(
    operation: AccessOperation,
    value: str | TypedNotApplicable,
) -> str:
    if isinstance(value, TypedNotApplicable):
        return content_id(
            PRESELECTION_NOT_APPLICABLE_BINDING_DOMAIN,
            {
                "schema": "acfqp.preselection_not_applicable_binding.v1",
                "operation": operation.value,
                "typed_null": value.to_dict(),
            },
        )
    return parse_content_id(value)


class FailedRouteErrorClassV1(str, Enum):
    """Stable coarse classification of the original selected-route error."""

    ACCESS_PROTOCOL_FAILURE = "ACCESS_PROTOCOL_FAILURE"
    NATIVE_ACCOUNTING_FAILURE = "NATIVE_ACCOUNTING_FAILURE"
    UPPER_BOUND_VIOLATION = "UPPER_BOUND_VIOLATION"
    RUNNER_PROTOCOL_FAILURE = "RUNNER_PROTOCOL_FAILURE"
    SELECTED_ROUTE_EXECUTOR_FAILURE = "SELECTED_ROUTE_EXECUTOR_FAILURE"


class AccessNativeReconciliationStatusV1(str, Enum):
    """Whether the retained access events exactly match retained counters."""

    RECONCILED = "RECONCILED"
    MISMATCH = "MISMATCH"


@dataclass(frozen=True, slots=True)
class Phase3EFailedRouteEvidenceV1:
    """Runtime evidence for one selected route that closed noncertificate.

    This object is deliberately not a plan, infeasibility, or terminal
    certificate.  It retains the frozen authority chain and exact native work
    solely so failed work remains visible and chargeable.
    """

    context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    decision: MarginalRouteDecisionV1
    selected_upper: RouteUpperBoundEnvelopeV1
    selected_route: RouteSelection
    partial_route_work: RecordedWorkV1
    partial_verification_work: RecordedWorkV1
    partial_marginal_work: AggregatedMarginalWorkV1
    access_log: AccessEventLogV1
    freeze_attestation: RouteDecisionFreezeAttestationV1
    decision_result: object = field(repr=False, compare=False)
    protocol_profile: ProtocolSequenceProfileV1
    original_error_classification: FailedRouteErrorClassV1
    original_error_type: str
    original_error_message: str
    access_native_reconciliation_status: AccessNativeReconciliationStatusV1
    access_native_reconciliation_error: str | None
    forbidden_access_violation: ForbiddenAccessViolationV1 | None = None
    closure_class: str = "ATTEMPT_CLOSURE_NONCERTIFICATE"
    closure_code: str = "PROTOCOL_FAILURE"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "selected_route",
            RouteSelection(self.selected_route),
        )
        object.__setattr__(
            self,
            "original_error_classification",
            FailedRouteErrorClassV1(self.original_error_classification),
        )
        object.__setattr__(
            self,
            "access_native_reconciliation_status",
            AccessNativeReconciliationStatusV1(
                self.access_native_reconciliation_status
            ),
        )
        if type(self.original_error_type) is not str or not self.original_error_type:
            raise Phase3ERunnerV1Error("failed-route error type must be nonempty")
        if type(self.original_error_message) is not str:
            raise Phase3ERunnerV1Error("failed-route error message must be a string")
        if (
            self.closure_class != "ATTEMPT_CLOSURE_NONCERTIFICATE"
            or self.closure_code != "PROTOCOL_FAILURE"
        ):
            raise Phase3ERunnerV1Error(
                "failed selected route may close only as noncertificate PROTOCOL_FAILURE"
            )
        if not isinstance(self.protocol_profile, ProtocolSequenceProfileV1):
            raise Phase3ERunnerV1Error(
                "failed route requires its typed protocol sequence profile"
            )
        if (
            self.access_native_reconciliation_status
            is AccessNativeReconciliationStatusV1.RECONCILED
        ) != (self.access_native_reconciliation_error is None):
            raise Phase3ERunnerV1Error(
                "access/native reconciliation status and error disagree"
            )


class Phase3ERouteExecutionFailedV1(Phase3ERunnerV1Error):
    """Fail-closed exception carrying all observable partial route evidence."""

    def __init__(
        self,
        evidence: Phase3EFailedRouteEvidenceV1,
        *,
        original_error: Exception,
    ) -> None:
        if not isinstance(evidence, Phase3EFailedRouteEvidenceV1):
            raise Phase3ERunnerV1Error(
                "route failure exception requires typed partial evidence"
            )
        self.evidence = evidence
        self.original_error = original_error
        super().__init__(
            f"{evidence.closure_code}: "
            f"{evidence.original_error_classification.value}: "
            f"{evidence.original_error_message}"
        )


@dataclass(frozen=True, slots=True)
class Phase3EPreselectionReadV1:
    """Identity-bearing read made from frozen data before route selection."""

    operation: AccessOperation
    artifact_id: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "operation", AccessOperation(self.operation))
            parse_content_id(self.artifact_id)
        except (TypeError, ValueError) as error:
            raise Phase3ERunnerV1Error(str(error)) from error
        if self.operation not in PRESELECTION_READ_OPERATIONS:
            raise Phase3ERunnerV1Error(
                f"{self.operation.value} is not an allowed preselection read"
            )


@dataclass(frozen=True, slots=True)
class Phase3EDecisionAuthorizationV1:
    """Runtime-only semantic authority required to cross the decision freeze."""

    decision_result: object
    selected_upper_result: object
    charged_verification_results: tuple[object, ...]

    def validate(
        self,
        *,
        context: RouteDecisionContextV1,
        decision_point: DecisionPointV1,
    ) -> tuple[MarginalRouteDecisionV1, RouteUpperBoundEnvelopeV1]:
        from acfqp.semantic_verification_v1 import (
            SemanticRole,
            SemanticVerificationResultV1,
            SemanticVerificationV1Error,
            require_semantic_verification_result_v1,
        )

        try:
            decision_result = require_semantic_verification_result_v1(
                self.decision_result, SemanticRole.ROUTE_DECISION
            )
            upper_result = require_semantic_verification_result_v1(
                self.selected_upper_result, SemanticRole.ROUTE_UPPER
            )
        except SemanticVerificationV1Error as error:
            raise Phase3ERunnerV1Error(
                "run_phase3e requires semantic route-decision and selected-upper "
                "authority"
            ) from error
        decision = decision_result.artifact
        upper = upper_result.artifact
        if not isinstance(decision, MarginalRouteDecisionV1):
            raise Phase3ERunnerV1Error(
                "route-decision authority carries the wrong artifact type"
            )
        if not isinstance(upper, RouteUpperBoundEnvelopeV1):
            raise Phase3ERunnerV1Error(
                "route-upper authority carries the wrong artifact type"
            )
        if (
            decision.decision_point_id != decision_point.decision_point_id
            or decision_point.route_decision_context_id
            != context.route_decision_context_id
            or decision.selected_upper_id
            != upper.route_upper_bound_envelope_id
        ):
            raise Phase3ERunnerV1Error(
                "decision, selected upper, point, and route context do not bind"
            )
        for field in (
            "preregistration_id",
            "protocol_id",
            "comparison_profile_id",
            "counter_registry_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "build_epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
        ):
            if getattr(upper, field) != getattr(context, field):
                raise Phase3ERunnerV1Error(
                    f"selected upper/context mismatch at {field}"
                )
        expected_kind = (
            RouteKind.LOCAL_ATTEMPT
            if decision.selected_route is RouteSelection.LOCAL
            else RouteKind.DIRECT_FALLBACK
        )
        if upper.route_kind is not expected_kind:
            raise Phase3ERunnerV1Error(
                "selected upper route kind differs from the decision"
            )

        if type(self.charged_verification_results) is not tuple:
            raise Phase3ERunnerV1Error(
                "charged verification results must be an immutable tuple"
            )
        record_ids: set[str] = set()
        results_by_attestation: dict[str, SemanticVerificationResultV1] = {}
        for result in self.charged_verification_results:
            if not isinstance(result, SemanticVerificationResultV1):
                raise Phase3ERunnerV1Error(
                    "charged verification work lacks semantic runtime authority"
                )
            try:
                verified = require_semantic_verification_result_v1(
                    result, result.role
                )
            except SemanticVerificationV1Error as error:
                raise Phase3ERunnerV1Error(
                    "charged verification result is not authoritative"
                ) from error
            record_id = verified.verification_work_record.record_id
            if record_id in record_ids:
                raise Phase3ERunnerV1Error(
                    "one verification work record was charged more than once"
                )
            record_ids.add(record_id)
            if (
                verified.binding.route_context != context
                or verified.binding.decision_point_id
                != decision_point.decision_point_id
            ):
                raise Phase3ERunnerV1Error(
                    "charged semantic verification belongs to another decision context"
                )
            attestation_id = (
                verified.attestation.verification_attestation_id
            )
            if attestation_id in results_by_attestation:
                raise Phase3ERunnerV1Error(
                    "one semantic verification attestation was charged more than once"
                )
            results_by_attestation[attestation_id] = verified

        decision_attestation_id = (
            decision_result.attestation.verification_attestation_id
        )
        selected_upper_attestation_id = (
            upper_result.attestation.verification_attestation_id
        )
        if (
            decision_attestation_id not in results_by_attestation
            or selected_upper_attestation_id not in results_by_attestation
        ):
            raise Phase3ERunnerV1Error(
                "decision or selected-upper semantic verification work is uncharged"
            )

        # Charge the complete semantic dependency closure, rather than merely
        # the two handles consumed directly by this runner.  A route decision
        # is replayed from causal and both route-upper attestations; every
        # route upper is replayed from exactly one cardinality attestation.
        # Formula/proof IDs in an upper's evidence list are content artifacts,
        # not semantic-verifier results, so they remain outside this closure.
        required_attestations = {decision_attestation_id}
        pending = [decision_result]
        while pending:
            verified = pending.pop()
            dependencies: list[SemanticVerificationResultV1] = []
            if verified.role is SemanticRole.ROUTE_DECISION:
                for dependency_id in verified.recomputed_evidence_ids:
                    dependency = results_by_attestation.get(dependency_id)
                    if dependency is None:
                        raise Phase3ERunnerV1Error(
                            "route-decision semantic dependency work is uncharged"
                        )
                    if dependency.role not in {
                        SemanticRole.CAUSAL_SEARCH,
                        SemanticRole.ROUTE_UPPER,
                    }:
                        raise Phase3ERunnerV1Error(
                            "route decision cites an invalid semantic dependency role"
                        )
                    dependencies.append(dependency)
            elif verified.role is SemanticRole.ROUTE_UPPER:
                semantic_dependencies = tuple(
                    results_by_attestation[evidence_id]
                    for evidence_id in verified.recomputed_evidence_ids
                    if evidence_id in results_by_attestation
                )
                if (
                    len(semantic_dependencies) != 1
                    or semantic_dependencies[0].role
                    is not SemanticRole.CARDINALITY_EVIDENCE
                ):
                    raise Phase3ERunnerV1Error(
                        "route-upper cardinality verification work is uncharged"
                    )
                dependencies.extend(semantic_dependencies)
            for dependency in dependencies:
                dependency_id = (
                    dependency.attestation.verification_attestation_id
                )
                if dependency_id not in required_attestations:
                    required_attestations.add(dependency_id)
                    pending.append(dependency)

        if set(results_by_attestation) != required_attestations:
            raise Phase3ERunnerV1Error(
                "charged semantic verification tuple differs from the exact "
                "route-decision dependency closure"
            )
        return decision, upper


@dataclass(frozen=True, slots=True)
class PreparedPhase3ERunV1:
    """Frozen RAPM-first input consumed without ground route execution."""

    context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    reusable_rapm_id: str
    failed_certificate_id: str
    action_catalogue_id: str
    preselection_reads: tuple[Phase3EPreselectionReadV1, ...]
    common_prefix_work: RecordedWorkV1
    authorization: Phase3EDecisionAuthorizationV1

    def validate(
        self,
        registry: CounterRegistryV1,
        profile: ComparisonProfileV1,
    ) -> tuple[MarginalRouteDecisionV1, RouteUpperBoundEnvelopeV1]:
        try:
            parse_content_id(self.reusable_rapm_id)
            parse_content_id(self.failed_certificate_id)
            parse_content_id(self.action_catalogue_id)
        except ValueError as error:
            raise Phase3ERunnerV1Error(
                "prepared RAPM/certificate/action-catalogue references must be "
                "full content IDs"
            ) from error
        if (
            self.context.counter_registry_id != registry.registry_id
            or self.context.comparison_profile_id != profile.comparison_profile_id
        ):
            raise Phase3ERunnerV1Error(
                "prepared context does not bind the official accounting profiles"
            )
        if type(self.preselection_reads) is not tuple or not all(
            isinstance(row, Phase3EPreselectionReadV1)
            for row in self.preselection_reads
        ):
            raise Phase3ERunnerV1Error(
                "preselection reads must be an immutable typed tuple"
            )
        if (
            self.decision_point.route_decision_context_id
            != self.context.route_decision_context_id
        ):
            raise Phase3ERunnerV1Error(
                "prepared decision point uses another route context"
            )
        operations = tuple(row.operation for row in self.preselection_reads)
        if (
            len(set(operations)) != len(operations)
            or set(operations) != set(PRESELECTION_READ_OPERATIONS)
        ):
            raise Phase3ERunnerV1Error(
                "prepared input must identify every allowed preselection read "
                "exactly once"
            )
        common = self.common_prefix_work
        verify_recorded_work_v1(
            common,
            expected_scope=ActualWorkScope.COMMON_PREFIX,
            registry=registry,
            comparison_profile=profile,
        )
        if (
            common.work_vector.route_kind
            is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
            or common.actual_projection_proof.work_scope
            is not ActualWorkScope.COMMON_PREFIX
            or common.work_vector.subject_id != self.context.route_attempt_id
            or common.work_vector.work_vector_id
            != self.decision_point.common_prefix_work_id
            or common.comparison_vector.work_vector_id
            != common.work_vector.work_vector_id
            or common.comparison_vector.comparison_profile_id
            != profile.comparison_profile_id
        ):
            raise Phase3ERunnerV1Error(
                "common-prefix native work is not bound to this decision point"
            )

        # Verify every binding that is available from the frozen preparation
        # before consuming route-decision authority.  This makes a foreign
        # failed certificate or action catalogue fail at the preselection
        # boundary rather than being masked by a later authority error.
        reads_by_operation = {
            row.operation: row.artifact_id for row in self.preselection_reads
        }
        fixed_bindings: dict[AccessOperation, str] = {
            AccessOperation.READ_FROZEN_RAPM: self.reusable_rapm_id,
            AccessOperation.READ_FROZEN_BUILD_EPOCH: self.context.build_epoch_id,
            AccessOperation.READ_FAILED_CERTIFICATE: self.failed_certificate_id,
            AccessOperation.READ_SELECTED_PLAN: self.context.selected_plan_id,
            AccessOperation.READ_ACTION_CATALOGUE: self.action_catalogue_id,
            AccessOperation.READ_FRONTIER_IDENTITIES: (
                _preselection_reference_id_v1(
                    AccessOperation.READ_FRONTIER_IDENTITIES,
                    self.decision_point.frontier_snapshot_id,
                )
            ),
            AccessOperation.READ_PROOF_CIRCUIT_METADATA: (
                _preselection_reference_id_v1(
                    AccessOperation.READ_PROOF_CIRCUIT_METADATA,
                    self.decision_point.causal_evidence_id,
                )
            ),
            AccessOperation.READ_PROFILE_REGISTRY: (
                self.context.comparison_profile_id
            ),
        }
        for operation, expected_id in fixed_bindings.items():
            if reads_by_operation[operation] != expected_id:
                raise Phase3ERunnerV1Error(
                    f"preselection read {operation.value} is not bound to the "
                    "prepared decision context"
                )

        decision, upper = self.authorization.validate(
            context=self.context,
            decision_point=self.decision_point,
        )

        expected_bindings: dict[AccessOperation, str] = {
            AccessOperation.READ_PREREGISTERED_CARDINALITIES: (
                upper.cardinality_evidence_id
            ),
            AccessOperation.READ_CAP_REGISTRY: upper.route_cap_profile_id,
            AccessOperation.READ_FORMULA_REGISTRY: upper.formula_id,
        }
        for operation, expected_id in expected_bindings.items():
            if reads_by_operation[operation] != expected_id:
                raise Phase3ERunnerV1Error(
                    f"preselection read {operation.value} is not bound to the "
                    "prepared decision context"
                )

        # The authoritative semantic work is part of the already frozen common
        # prefix.  Aggregate by native path so two different attestations using
        # the same verifier counter cannot disappear behind one row.
        charged: dict[str, int] = {}
        for result in self.authorization.charged_verification_results:
            record = result.verification_work_record
            charged[record.path] = charged.get(record.path, 0) + record.value
        for path, required_value in charged.items():
            if common.work_vector.value(path) < required_value:
                raise Phase3ERunnerV1Error(
                    f"common-prefix WorkVector does not charge semantic work {path!r}"
                )
        return decision, upper


@dataclass(frozen=True, slots=True)
class Phase3ERouteExecutionV1:
    """Opaque selected-route completion returned by a real executor adapter.

    ``semantic_execution`` is a runtime-only seam.  V0 accepts the sealed
    in-process ground fallback or the scoped Phase-3D isolated-local execution;
    neither seal is serialized into the runner result artifact and neither by
    itself classifies a terminal or relaxes an official gate.
    """

    artifact_id: str
    completed: bool
    requires_next_transaction: bool = False
    native_execution_work: RecordedWorkV1 | None = None
    semantic_execution: object | None = field(
        default=None, compare=False, repr=False
    )
    semantic_outcome: str | None = None
    semantic_verification_results: tuple[object, ...] = field(
        default=(), compare=False, repr=False
    )

    def __post_init__(self) -> None:
        try:
            parse_content_id(self.artifact_id)
        except ValueError as error:
            raise Phase3ERunnerV1Error(
                "route execution artifact must have a full content ID"
            ) from error
        if type(self.completed) is not bool or type(
            self.requires_next_transaction
        ) is not bool:
            raise Phase3ERunnerV1Error(
                "route completion flags must be boolean"
            )
        if self.native_execution_work is not None and not isinstance(
            self.native_execution_work, RecordedWorkV1
        ):
            raise Phase3ERunnerV1Error(
                "native_execution_work must be an exact RecordedWorkV1"
            )
        if type(self.semantic_verification_results) is not tuple:
            raise Phase3ERunnerV1Error(
                "route semantic verification results must be an immutable tuple"
            )
        if self.semantic_execution is None:
            raise Phase3ERunnerV1Error(
                "selected route completion requires route-specific trusted semantic authority"
            )

        # Import lazily because both selected-route adapters import this runner
        # module.  The opaque handle is checked here but semantically attested
        # only by the route-specific verifier downstream.
        from acfqp.phase3e_local_semantics_v1 import (
            LocalSolverOutcome,
            PostAuditOutcome,
            TrustedLocalExecutionV1,
            verify_trusted_local_runtime_provenance_v1,
            verify_trusted_postaudit_runtime_provenance_v1,
        )
        if isinstance(self.semantic_execution, TrustedLocalExecutionV1):
            local_execution = self.semantic_execution
            try:
                verify_trusted_local_runtime_provenance_v1(local_execution)
                if local_execution.post_audit is not None:
                    verify_trusted_postaudit_runtime_provenance_v1(local_execution)
            except ValueError as error:
                raise Phase3ERunnerV1Error(
                    f"runtime local execution lacks trusted provenance: {error}"
                ) from error
            if self.native_execution_work is None or (
                self.native_execution_work.work_vector.work_vector_id
                != local_execution.work_vector.work_vector_id
            ):
                raise Phase3ERunnerV1Error(
                    "runtime local execution does not bind its native WorkVector"
                )
            if local_execution.post_audit is None:
                if local_execution.local_result.outcome is LocalSolverOutcome.CANDIDATE_FOUND:
                    raise Phase3ERunnerV1Error(
                        "a local candidate cannot bypass the sound post-audit"
                    )
                expected_artifact = (
                    local_execution.local_result.local_transaction_result_id
                )
                expected_outcome = local_execution.local_result.outcome.value
                expected_completed = False
                expected_next = False
            else:
                expected_artifact = (
                    local_execution.post_audit.post_audit_certificate_id
                )
                expected_outcome = local_execution.post_audit.outcome.value
                expected_completed = (
                    local_execution.post_audit.outcome is PostAuditOutcome.CERTIFIED
                )
                expected_next = (
                    local_execution.post_audit.outcome is PostAuditOutcome.FAILED
                )
            if (
                self.artifact_id != expected_artifact
                or self.semantic_outcome != expected_outcome
                or self.completed is not expected_completed
                or self.requires_next_transaction is not expected_next
            ):
                raise Phase3ERunnerV1Error(
                    "runtime local result/post-audit disagrees with route closure"
                )
            from acfqp.semantic_verification_v1 import (
                SemanticRole,
                require_semantic_verification_result_v1,
            )
            expected_roles = (
                (SemanticRole.LOCAL_SOLVER_RESULT, SemanticRole.POST_AUDIT)
                if local_execution.post_audit is not None
                else (SemanticRole.LOCAL_SOLVER_RESULT,)
            )
            if tuple(
                getattr(row, "role", None)
                for row in self.semantic_verification_results
            ) != expected_roles:
                raise Phase3ERunnerV1Error(
                    "local route completion carries an incomplete or extraneous "
                    "semantic verifier chain"
                )
            required = [
                require_semantic_verification_result_v1(
                    row, SemanticRole.LOCAL_SOLVER_RESULT
                )
                for row in self.semantic_verification_results
                if getattr(row, "role", None) is SemanticRole.LOCAL_SOLVER_RESULT
            ]
            post_results = [
                require_semantic_verification_result_v1(row, SemanticRole.POST_AUDIT)
                for row in self.semantic_verification_results
                if getattr(row, "role", None) is SemanticRole.POST_AUDIT
            ]
            if len(required) != 1 or (
                (local_execution.post_audit is not None and len(post_results) != 1)
                or (local_execution.post_audit is None and post_results)
            ):
                raise Phase3ERunnerV1Error(
                    "local route completion lacks its exact semantic verifier chain"
                )
            if required[0].artifact != local_execution.local_result or (
                post_results and post_results[0].artifact != local_execution.post_audit
            ):
                raise Phase3ERunnerV1Error(
                    "local semantic verifier result carries another execution"
                )
            return

        from acfqp.phase3e_fallback_v1 import (
            GroundFallbackExecutionV1,
            GroundFallbackOutcome,
            GroundFallbackV1Error,
            verify_trusted_ground_fallback_execution_provenance_v1,
        )

        if not isinstance(self.semantic_execution, GroundFallbackExecutionV1):
            raise Phase3ERunnerV1Error(
                "V0 runtime semantic execution has an unregistered route type"
            )
        try:
            verify_trusted_ground_fallback_execution_provenance_v1(
                self.semantic_execution
            )
        except GroundFallbackV1Error as error:
            raise Phase3ERunnerV1Error(
                f"runtime semantic execution lacks trusted provenance: {error}"
            ) from error
        fallback_result = self.semantic_execution.result
        if (
            self.artifact_id != fallback_result.ground_fallback_result_id
            or self.semantic_outcome != fallback_result.outcome.value
        ):
            raise Phase3ERunnerV1Error(
                "runtime semantic execution/result/outcome identity mismatch"
            )
        if self.native_execution_work is None or (
            self.native_execution_work.work_vector.work_vector_id
            != self.semantic_execution.work_vector.work_vector_id
        ):
            raise Phase3ERunnerV1Error(
                "runtime semantic execution does not bind its native WorkVector"
            )
        expected_completed = (
            fallback_result.outcome is not GroundFallbackOutcome.CAP_EXHAUSTED
        )
        if self.completed is not expected_completed or self.requires_next_transaction:
            raise Phase3ERunnerV1Error(
                "runtime semantic fallback outcome disagrees with route closure"
            )
        from acfqp.semantic_verification_v1 import (
            SemanticRole,
            require_semantic_verification_result_v1,
        )
        fallback_results = tuple(
            require_semantic_verification_result_v1(
                row, SemanticRole.GROUND_FALLBACK
            )
            for row in self.semantic_verification_results
        )
        if (
            len(fallback_results) != 1
            or fallback_results[0].artifact != fallback_result
            or fallback_results[0].outcome != fallback_result.outcome.value
        ):
            raise Phase3ERunnerV1Error(
                "fallback route completion lacks exact ground semantic verification"
            )


def _require_route_semantic_context_v1(
    *,
    prepared: PreparedPhase3ERunV1,
    selected_upper: RouteUpperBoundEnvelopeV1,
    execution: Phase3ERouteExecutionV1,
    selected: RouteSelection,
    freeze_after_sequence: int,
    final_access_sequence: int,
) -> None:
    """Reject a genuine route result replayed under another decision context."""

    expected_transaction = selected_upper.transaction_id
    for result in execution.semantic_verification_results:
        binding = result.binding
        if (
            binding.route_context != prepared.context
            or binding.decision_point_id
            != prepared.decision_point.decision_point_id
        ):
            raise Phase3ERunnerV1Error(
                "route semantic verifier result is bound to another context or decision"
            )
        if isinstance(expected_transaction, TypedNotApplicable):
            transaction_matches = isinstance(
                binding.transaction_id, TypedNotApplicable
            )
        else:
            transaction_matches = binding.transaction_id == expected_transaction
        if not transaction_matches:
            raise Phase3ERunnerV1Error(
                "route semantic verifier result is bound to another transaction"
            )
        if not (
            freeze_after_sequence
            < binding.verified_at_protocol_step
            <= final_access_sequence + 1
        ):
            raise Phase3ERunnerV1Error(
                "route semantic verification was not performed after decision freeze"
            )


class Phase3ERouteExecutorV1(Protocol):
    def __call__(
        self,
        prepared: PreparedPhase3ERunV1,
        controller: FailClosedAccessController,
        recorder: NativeCounterRecorderV1,
    ) -> Phase3ERouteExecutionV1: ...


@dataclass(frozen=True, slots=True)
class Phase3ERunResultV1:
    status: str
    selected_route: RouteSelection
    decision: MarginalRouteDecisionV1
    selected_upper: RouteUpperBoundEnvelopeV1
    route_execution: Phase3ERouteExecutionV1
    common_prefix_work: RecordedWorkV1
    selected_route_work: RecordedWorkV1
    verification_suffix_work: RecordedWorkV1
    aggregate_marginal_work: AggregatedMarginalWorkV1
    reusable_rapm_id: str
    preselection_reads: tuple[Phase3EPreselectionReadV1, ...]
    upper_compliance: str
    access_log: AccessEventLogV1
    freeze_attestation: RouteDecisionFreezeAttestationV1
    official_execution_allowed: bool = OFFICIAL_EXECUTION_ALLOWED
    official_scalar_cost: None = OFFICIAL_SCALAR_COST
    official_N_break_even: None = OFFICIAL_N_BREAK_EVEN
    workload_economics_gate_status: str = WORKLOAD_ECONOMICS_GATE_STATUS
    counter_completeness_gate_status: str = COUNTER_COMPLETENESS_GATE_STATUS
    postfreeze_accounting_complete: bool = False
    unassigned_postfreeze_operational_leaves: tuple[str, ...] = (
        UNASSIGNED_POSTFREEZE_OPERATIONAL_LEAVES
    )
    unresolved_official_execution_obligations: tuple[str, ...] = (
        UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS
    )

    def __post_init__(self) -> None:
        try:
            parse_content_id(self.reusable_rapm_id)
        except ValueError as error:
            raise Phase3ERunnerV1Error(
                "result reusable RAPM reference is invalid"
            ) from error
        if type(self.preselection_reads) is not tuple:
            raise Phase3ERunnerV1Error(
                "result preselection reads must remain immutable"
            )
        if self.status != VERTICAL_SLICE_STATUS:
            raise Phase3ERunnerV1Error("invalid Phase-3E vertical-slice status")
        if (
            self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate_status
            != WORKLOAD_ECONOMICS_GATE_STATUS
            or self.counter_completeness_gate_status
            != COUNTER_COMPLETENESS_GATE_STATUS
            or self.postfreeze_accounting_complete is not False
            or self.unassigned_postfreeze_operational_leaves
            != UNASSIGNED_POSTFREEZE_OPERATIONAL_LEAVES
            or self.unresolved_official_execution_obligations
            != UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS
        ):
            raise Phase3ERunnerV1Error("official Phase-3E locks were relaxed")


def _require_selected_access_trace(
    *,
    selected: RouteSelection,
    execution: Phase3ERouteExecutionV1,
    log: AccessEventLogV1,
    freeze_after_sequence: int,
) -> None:
    operations = tuple(event.operation for event in log.events)
    if selected is RouteSelection.LOCAL:
        from acfqp.phase3e_local_semantics_v1 import TrustedLocalExecutionV1

        semantic = execution.semantic_execution
        if not isinstance(semantic, TrustedLocalExecutionV1):
            raise Phase3ERunnerV1Error(
                "local access trace lacks its trusted semantic execution"
            )
        capability_results = tuple(
            event
            for event in log.events
            if event.operation is AccessOperation.LOCAL_CAPABILITY_ARTIFACT
        )
        if (
            len(capability_results) != 1
            or capability_results[0].artifact_id
            != semantic.local_result.capability_binding_id
        ):
            raise Phase3ERunnerV1Error(
                "local execution must bind exactly one compiled capability"
            )
        worker_results = tuple(
            event
            for event in log.events
            if event.operation is AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT
        )
        if (
            len(worker_results) != 1
            or worker_results[0].artifact_id
            != semantic.local_result.worker_result_binding_id
        ):
            raise Phase3ERunnerV1Error(
                "local execution must bind exactly one isolated worker result"
            )
        post_results = tuple(
            event
            for event in log.events
            if event.operation is AccessOperation.LOCAL_POSTAUDIT_ARTIFACT
        )
        stitch_results = tuple(
            event
            for event in log.events
            if event.operation is AccessOperation.LOCAL_STITCH_ARTIFACT
        )
        stages = local_execution_stages_v1(
            log.events,
            freeze_after_sequence=freeze_after_sequence,
        )
        if semantic.post_audit is None:
            if stitch_results or post_results or stages != (1, 2, 3):
                raise Phase3ERunnerV1Error(
                    "local no-candidate closure must stop after the worker result"
                )
        elif (
            stages != (1, 2, 3, 4, 5)
            or len(stitch_results) != 1
            or stitch_results[0].artifact_id
            != semantic.local_result.stitched_plan_binding_id
            or len(post_results) != 1
            or post_results[0].artifact_id != execution.artifact_id
        ):
            raise Phase3ERunnerV1Error(
                "local execution must bind exactly one post-audit artifact"
            )
    else:
        invocations = operations.count(
            AccessOperation.FALLBACK_SOLVER_INVOCATION
        )
        launches = operations.count(AccessOperation.FALLBACK_WORKER_LAUNCH)
        results = tuple(
            event
            for event in log.events
            if event.operation is AccessOperation.FALLBACK_RESULT_ARTIFACT
        )
        if invocations + launches != 1 or len(results) != 1:
            raise Phase3ERunnerV1Error(
                "fallback execution must have one solver invocation/launch and one result"
            )
        if results[0].artifact_id != execution.artifact_id:
            raise Phase3ERunnerV1Error(
                "fallback access trace binds another result artifact"
            )
        if execution.requires_next_transaction:
            raise Phase3ERunnerV1Error(
                "direct fallback cannot request a local transaction"
            )


def _reconcile_access_and_native_counters(
    *,
    selected: RouteSelection,
    log: AccessEventLogV1,
    work: RecordedWorkV1,
) -> None:
    """Bind route access events to the exact native counter leaves."""

    operations = tuple(event.operation for event in log.events)
    observed_process_launches = (
        operations.count(AccessOperation.LOCAL_WORKER_LAUNCH)
        + operations.count(AccessOperation.FALLBACK_WORKER_LAUNCH)
    )
    if work.work_vector.value("process.launches") != observed_process_launches:
        raise Phase3ERunnerV1Error(
            "access worker-launch events and process.launches disagree"
        )
    observed_steps = operations.count(AccessOperation.KERNEL_STEP)
    expected_steps = (
        work.work_vector.value("local.materialization_ground_steps")
        + work.work_vector.value("local.postaudit_ground_steps")
        if selected is RouteSelection.LOCAL
        else work.work_vector.value("fallback.ground_steps")
    )
    if observed_steps != expected_steps:
        raise Phase3ERunnerV1Error(
            "access kernel-step events and native ground-step counters disagree"
        )
    if (
        operations.count(AccessOperation.GROUND_OUTCOME_ENUMERATION)
        != expected_steps
    ):
        raise Phase3ERunnerV1Error(
            "access outcome-enumeration events and native ground steps disagree"
        )


def _classify_failed_route_error_v1(
    error: Exception,
) -> FailedRouteErrorClassV1:
    if isinstance(error, (AccessProtocolViolation, AccessProtocolV1Error)):
        return FailedRouteErrorClassV1.ACCESS_PROTOCOL_FAILURE
    if isinstance(error, UpperBoundViolationError):
        return FailedRouteErrorClassV1.UPPER_BOUND_VIOLATION
    if isinstance(error, NativeRecorderV1Error):
        return FailedRouteErrorClassV1.NATIVE_ACCOUNTING_FAILURE
    if isinstance(error, Phase3ERunnerV1Error):
        return FailedRouteErrorClassV1.RUNNER_PROTOCOL_FAILURE
    return FailedRouteErrorClassV1.SELECTED_ROUTE_EXECUTOR_FAILURE


def _exception_owned_partial_work_v1(
    error: Exception,
    execution: Phase3ERouteExecutionV1 | None,
    *,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
) -> RecordedWorkV1 | None:
    """Extract only explicitly owned native evidence from a failed adapter."""

    candidates: list[object] = []
    for field_name in (
        "partial_recorded_work",
        "partial_native_execution_work",
        "partial_work_vector",
    ):
        candidate = getattr(error, field_name, None)
        if candidate is not None:
            candidates.append(candidate)
    if execution is not None and execution.native_execution_work is not None:
        candidates.append(execution.native_execution_work)
    if not candidates:
        return None
    if len(candidates) > 1:
        identities = {
            (
                candidate.work_vector.work_vector_id
                if isinstance(candidate, RecordedWorkV1)
                else candidate.work_vector_id
                if isinstance(candidate, WorkVectorV1)
                else None
            )
            for candidate in candidates
        }
        if None in identities or len(identities) != 1:
            raise NativeRecorderV1Error(
                "failed adapter exposed conflicting owned partial WorkVectors"
            )
    candidate = candidates[0]
    if isinstance(candidate, WorkVectorV1):
        candidate = derive_recorded_work_v1(
            candidate,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=registry,
            comparison_profile=comparison_profile,
        )
    if not isinstance(candidate, RecordedWorkV1):
        raise NativeRecorderV1Error(
            "failed adapter partial work has an unregistered runtime type"
        )
    return derive_failed_recorded_work_v1(
        candidate,
        registry=registry,
        comparison_profile=comparison_profile,
    )


def verify_failed_route_evidence_v1(
    evidence: Phase3EFailedRouteEvidenceV1,
    *,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> Phase3EFailedRouteEvidenceV1:
    """Replay the exact failure binding without classifying a certificate."""

    if not isinstance(evidence, Phase3EFailedRouteEvidenceV1):
        raise Phase3ERunnerV1Error("failed-route evidence has the wrong type")
    registry = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(registry)
    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        SemanticVerificationV1Error,
        require_semantic_verification_result_v1,
    )

    try:
        decision_result = require_semantic_verification_result_v1(
            evidence.decision_result, SemanticRole.ROUTE_DECISION
        )
    except SemanticVerificationV1Error as error:
        raise Phase3ERunnerV1Error(
            "failed-route evidence lacks route-decision semantic authority"
        ) from error
    if (
        decision_result.artifact != evidence.decision
        or decision_result.binding.route_context != evidence.context
        or decision_result.binding.decision_point_id
        != evidence.decision_point.decision_point_id
    ):
        raise Phase3ERunnerV1Error(
            "failed-route decision authority belongs to another context"
        )
    verify_recorded_work_v1(
        evidence.partial_route_work,
        expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )
    verify_recorded_work_v1(
        evidence.partial_verification_work,
        expected_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        registry=registry,
        comparison_profile=profile,
    )
    expected_kind = (
        RouteKindEnum.LOCAL_ATTEMPT
        if evidence.selected_route is RouteSelection.LOCAL
        else RouteKindEnum.DIRECT_FALLBACK
    )
    expected_subject = (
        evidence.selected_upper.transaction_id
        if evidence.selected_route is RouteSelection.LOCAL
        else evidence.context.route_attempt_id
    )
    if isinstance(expected_subject, TypedNotApplicable):
        raise Phase3ERunnerV1Error(
            "failed local route lacks its transaction subject"
        )
    route_vector = evidence.partial_route_work.work_vector
    verification_vector = evidence.partial_verification_work.work_vector
    if (
        route_vector.subject_id != expected_subject
        or verification_vector.subject_id != expected_subject
        or route_vector.route_kind is not expected_kind
        or verification_vector.route_kind is not expected_kind
    ):
        raise Phase3ERunnerV1Error(
            "failed-route native work uses another route or subject"
        )
    actual_profile = official_actual_projection_profile_v1(registry, profile)
    replayed_marginal = derive_marginal_work_aggregate_v1(
        subject_id=expected_subject,
        route_kind=expected_kind,
        execution=(
            evidence.partial_route_work.work_vector,
            evidence.partial_route_work.comparison_vector,
            evidence.partial_route_work.actual_projection_proof,
        ),
        verification_suffix=(
            evidence.partial_verification_work.work_vector,
            evidence.partial_verification_work.comparison_vector,
            evidence.partial_verification_work.actual_projection_proof,
        ),
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )
    if evidence.partial_marginal_work != replayed_marginal:
        raise Phase3ERunnerV1Error(
            "failed-route marginal work does not replay from its two native sources"
        )
    if (
        route_vector.value("route.attempts"),
        route_vector.value("route.successes"),
        route_vector.value("route.failures"),
    ) != (1, 0, 1):
        raise Phase3ERunnerV1Error(
            "failed-route work must close exactly one failed attempt"
        )
    if (
        evidence.decision_point.route_decision_context_id
        != evidence.context.route_decision_context_id
        or evidence.decision.decision_point_id
        != evidence.decision_point.decision_point_id
        or evidence.decision.selected_route is not evidence.selected_route
        or evidence.decision.selected_upper_id
        != evidence.selected_upper.route_upper_bound_envelope_id
        or evidence.access_log.route_attempt_id != evidence.context.route_attempt_id
        or evidence.access_log.decision_point_id
        != evidence.decision_point.decision_point_id
    ):
        raise Phase3ERunnerV1Error(
            "failed-route authority, access, and decision identities differ"
        )
    for field_name in (
        "preregistration_id",
        "protocol_id",
        "comparison_profile_id",
        "counter_registry_id",
        "structural_id",
        "query_id",
        "selected_plan_id",
        "threshold_profile_id",
        "build_epoch_id",
        "logical_occurrence_id",
        "route_attempt_id",
    ):
        if getattr(evidence.selected_upper, field_name) != getattr(
            evidence.context, field_name
        ):
            raise Phase3ERunnerV1Error(
                f"failed-route selected upper/context mismatch at {field_name}"
            )
    expected_upper_kind = (
        RouteKind.LOCAL_ATTEMPT
        if evidence.selected_route is RouteSelection.LOCAL
        else RouteKind.DIRECT_FALLBACK
    )
    if (
        evidence.selected_upper.decision_point_id
        != evidence.decision_point.decision_point_id
        or evidence.selected_upper.route_kind is not expected_upper_kind
    ):
        raise Phase3ERunnerV1Error(
            "failed-route selected upper uses another point or route kind"
        )
    freeze = evidence.freeze_attestation
    if (
        freeze.route_attempt_id != evidence.context.route_attempt_id
        or freeze.decision_point_id != evidence.decision_point.decision_point_id
        or freeze.route_decision_id != evidence.decision.route_decision_id
        or freeze.selected_route is not evidence.selected_route
        or evidence.access_log.route_decision_freeze_attestation_id
        != freeze.route_decision_freeze_attestation_id
    ):
        raise Phase3ERunnerV1Error(
            "failed-route freeze attestation does not bind the retained log"
        )
    if (
        evidence.protocol_profile.protocol_sequence_profile_id
        != freeze.protocol_sequence_profile_id
        or evidence.access_log.protocol_sequence_profile_id
        != evidence.protocol_profile.protocol_sequence_profile_id
    ):
        raise Phase3ERunnerV1Error(
            "failed-route protocol profile does not bind its freeze and log"
        )
    replayed_violation: ForbiddenAccessViolationV1 | None = None
    try:
        replay_access_protocol(
            evidence.access_log,
            evidence.protocol_profile,
            decision_result=decision_result,
            freeze_attestation=freeze,
        )
    except AccessProtocolViolation as error:
        replayed_violation = error.violation
    except AccessProtocolV1Error as error:
        raise Phase3ERunnerV1Error(
            f"failed-route access protocol replay failed: {error}"
        ) from error
    reconciliation_error: str | None = None
    try:
        _reconcile_access_and_native_counters(
            selected=evidence.selected_route,
            log=evidence.access_log,
            work=evidence.partial_route_work,
        )
    except Phase3ERunnerV1Error as error:
        reconciliation_error = str(error)
    expected_status = (
        AccessNativeReconciliationStatusV1.RECONCILED
        if reconciliation_error is None
        else AccessNativeReconciliationStatusV1.MISMATCH
    )
    if (
        evidence.access_native_reconciliation_status is not expected_status
        or evidence.access_native_reconciliation_error != reconciliation_error
    ):
        raise Phase3ERunnerV1Error(
            "failed-route access/native reconciliation claim does not replay"
        )
    violation = evidence.forbidden_access_violation
    if violation != replayed_violation:
        raise Phase3ERunnerV1Error(
            "failed-route forbidden-access claim differs from protocol replay"
        )
    if violation is not None and evidence.original_error_classification is not (
        FailedRouteErrorClassV1.ACCESS_PROTOCOL_FAILURE
    ):
        raise Phase3ERunnerV1Error(
            "forbidden-access evidence requires ACCESS_PROTOCOL_FAILURE classification"
        )
    if violation is not None and (
        violation.route_attempt_id != evidence.context.route_attempt_id
        or violation.decision_point_id != evidence.decision_point.decision_point_id
        or violation.access_event_log_id != evidence.access_log.access_event_log_id
        or violation.route_decision_freeze_attestation_id
        != freeze.route_decision_freeze_attestation_id
        or violation.selected_route is not evidence.selected_route
    ):
        raise Phase3ERunnerV1Error(
            "failed-route forbidden-access artifact does not bind retained evidence"
        )
    return evidence


def _build_failed_route_evidence_v1(
    *,
    error: Exception,
    prepared: PreparedPhase3ERunV1,
    decision: MarginalRouteDecisionV1,
    selected_upper: RouteUpperBoundEnvelopeV1,
    execution: Phase3ERouteExecutionV1 | None,
    controller: FailClosedAccessController,
    route_recorder: NativeCounterRecorderV1,
    verification_recorder: NativeCounterRecorderV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
) -> Phase3EFailedRouteEvidenceV1:
    freeze = controller.freeze_attestation
    if freeze is None:
        raise Phase3ERunnerV1Error(
            "no selected-route failure evidence exists before decision freeze"
        )
    owned = _exception_owned_partial_work_v1(
        error,
        execution,
        registry=registry,
        comparison_profile=comparison_profile,
    )
    recorder_has_work = any(route_recorder.values.values())
    if owned is not None and recorder_has_work:
        raise Phase3ERunnerV1Error(
            "failed executor mixed runner counters with separately owned work; "
            "no double-count-free aggregate exists"
        )
    partial_route = owned or route_recorder.seal_route_failure()
    if owned is not None:
        verify_recorded_work_v1(
            partial_route,
            expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=registry,
            comparison_profile=comparison_profile,
        )
    partial_verification = verification_recorder.seal_partial()
    actual_profile = official_actual_projection_profile_v1(
        registry, comparison_profile
    )
    partial_marginal = derive_marginal_work_aggregate_v1(
        subject_id=partial_route.work_vector.subject_id,
        route_kind=partial_route.work_vector.route_kind,
        execution=(
            partial_route.work_vector,
            partial_route.comparison_vector,
            partial_route.actual_projection_proof,
        ),
        verification_suffix=(
            partial_verification.work_vector,
            partial_verification.comparison_vector,
            partial_verification.actual_projection_proof,
        ),
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    access_log = controller.snapshot()
    reconciliation_error: str | None = None
    try:
        _reconcile_access_and_native_counters(
            selected=decision.selected_route,
            log=access_log,
            work=partial_route,
        )
    except Phase3ERunnerV1Error as reconciliation_failure:
        reconciliation_error = str(reconciliation_failure)
    classification = _classify_failed_route_error_v1(error)
    violation = (
        error.violation
        if isinstance(error, AccessProtocolViolation)
        else controller.violation
    )
    evidence = Phase3EFailedRouteEvidenceV1(
        prepared.context,
        prepared.decision_point,
        decision,
        selected_upper,
        decision.selected_route,
        partial_route,
        partial_verification,
        partial_marginal,
        access_log,
        freeze,
        prepared.authorization.decision_result,
        controller.profile,
        classification,
        f"{type(error).__module__}.{type(error).__qualname__}",
        str(error),
        (
            AccessNativeReconciliationStatusV1.RECONCILED
            if reconciliation_error is None
            else AccessNativeReconciliationStatusV1.MISMATCH
        ),
        reconciliation_error,
        violation,
    )
    return verify_failed_route_evidence_v1(
        evidence,
        registry=registry,
        comparison_profile=comparison_profile,
    )


def _check_authoritative_upper(
    actual: AggregatedMarginalWorkV1,
    upper: RouteUpperBoundEnvelopeV1,
) -> str:
    upper_values = dict(upper.upper_bounds)
    if tuple(sorted(upper_values)) != SHARED_AXES:
        raise Phase3ERunnerV1Error(
            "selected authoritative upper lacks the exact shared axes"
        )
    exceeded = tuple(
        axis
        for axis in SHARED_AXES
        if actual.aggregate_comparison_vector.value(axis) > upper_values[axis]
    )
    if exceeded:
        raise UpperBoundViolationError(
            "actual selected-route work exceeds its authoritative upper on "
            + ", ".join(exceeded),
            violated_axes=exceeded,
        )
    return WITHIN_SELECTED_UPPER


def run_phase3e(
    prepared: PreparedPhase3ERunV1,
    *,
    local_executor: Phase3ERouteExecutorV1,
    fallback_executor: Phase3ERouteExecutorV1,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> Phase3ERunResultV1:
    """Freeze one authoritative decision and execute only its selected route.

    The two executors are injected so a caller can attach the Phase-3D local
    path and the complete ground fallback without giving either one access
    before route selection.  ``decide_then_execute`` invokes exactly one.
    """

    registry = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(registry)
    try:
        registry.validate_official_catalogue()
        profile.validate(registry)
        decision, selected_upper = prepared.validate(registry, profile)
    except (ValueError, NativeRecorderV1Error) as error:
        if isinstance(error, Phase3ERunnerV1Error):
            raise
        raise Phase3ERunnerV1Error(str(error)) from error

    controller = FailClosedAccessController(
        prepared.context.route_attempt_id,
        prepared.decision_point.decision_point_id,
    )
    # Replay the complete frozen-read prefix.  No route-scoped operation is
    # reachable until the semantic decision result crosses the freeze below.
    for read in prepared.preselection_reads:
        controller.record(
            read.operation,
            AccessRouteScope.COMMON,
            artifact_id=read.artifact_id,
        )

    route_kind = (
        RouteKindEnum.LOCAL_ATTEMPT
        if decision.selected_route is RouteSelection.LOCAL
        else RouteKindEnum.DIRECT_FALLBACK
    )
    subject_id: str
    if decision.selected_route is RouteSelection.LOCAL:
        if isinstance(selected_upper.transaction_id, TypedNotApplicable):
            raise Phase3ERunnerV1Error(
                "selected local upper lacks a transaction subject"
            )
        subject_id = selected_upper.transaction_id
    else:
        subject_id = prepared.context.route_attempt_id
    route_recorder = NativeCounterRecorderV1(
        subject_id=subject_id,
        route_kind=route_kind,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )
    verification_recorder = NativeCounterRecorderV1(
        subject_id=subject_id,
        route_kind=route_kind,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        registry=registry,
        comparison_profile=profile,
    )

    def local_callback(
        access: FailClosedAccessController,
    ) -> Phase3ERouteExecutionV1:
        result = local_executor(prepared, access, route_recorder)
        if not isinstance(result, Phase3ERouteExecutionV1):
            raise Phase3ERunnerV1Error(
                "local executor returned an untyped result"
            )
        return result

    def fallback_callback(
        access: FailClosedAccessController,
    ) -> Phase3ERouteExecutionV1:
        result = fallback_executor(prepared, access, route_recorder)
        if not isinstance(result, Phase3ERouteExecutionV1):
            raise Phase3ERunnerV1Error(
                "fallback executor returned an untyped result"
            )
        return result

    execution: Phase3ERouteExecutionV1 | None = None
    try:
        execution = decide_then_execute(
            controller,
            prepared.authorization.decision_result,
            local_callback=local_callback,
            fallback_callback=fallback_callback,
        )
        route_freeze = controller.freeze_attestation
        if route_freeze is None:  # pragma: no cover - freeze precedes callback
            raise Phase3ERunnerV1Error(
                "route semantic verification occurred without a decision freeze"
            )
        _require_selected_access_trace(
            selected=decision.selected_route,
            execution=execution,
            log=controller.snapshot(),
            freeze_after_sequence=route_freeze.last_preselection_sequence,
        )
        _require_route_semantic_context_v1(
            prepared=prepared,
            selected_upper=selected_upper,
            execution=execution,
            selected=decision.selected_route,
            freeze_after_sequence=route_freeze.last_preselection_sequence,
            final_access_sequence=len(controller.snapshot().events),
        )
        if execution.native_execution_work is None:
            route_recorder.record_route_completion(success=execution.completed)
            selected_work = route_recorder.seal()
        else:
            selected_work = execution.native_execution_work
            verify_recorded_work_v1(
                selected_work,
                expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
                registry=registry,
                comparison_profile=profile,
            )
            if any(route_recorder.values.values()):
                raise Phase3ERunnerV1Error(
                    "executor mixed recorder writes with an owned native WorkVector"
                )
            if (
                selected_work.work_vector.subject_id != subject_id
                or selected_work.work_vector.route_kind is not route_kind
                or selected_work.actual_projection_proof.work_scope
                is not ActualWorkScope.MARGINAL_ROUTE_EXECUTION
            ):
                raise Phase3ERunnerV1Error(
                    "executor-owned native work uses another route, subject, or scope"
                )
            expected_success = 1 if execution.completed else 0
            if (
                selected_work.work_vector.value("route.attempts") != 1
                or selected_work.work_vector.value("route.successes")
                != expected_success
                or selected_work.work_vector.value("route.failures")
                != 1 - expected_success
            ):
                raise Phase3ERunnerV1Error(
                    "executor completion disagrees with its native route closure"
                )

        _reconcile_access_and_native_counters(
            selected=decision.selected_route,
            log=controller.snapshot(),
            work=selected_work,
        )

        # Four runner-level checks are charged here: access/trace reconciliation,
        # execution-vector integrity/projection, native aggregation, and
        # aggregate/upper compliance.  Route-specific semantic verifiers
        # contribute their own exact CounterRecords (one for fallback; local
        # solver plus post-audit for a candidate).  Hash-layer invocations
        # remain the explicit completeness blocker reported by the result.
        verification_recorder.add("common.protocol_checks", 4)
        for semantic_result in execution.semantic_verification_results:
            verification_recorder.charge_verified_record(
                semantic_result.verification_work_record
            )
        verification_work = verification_recorder.seal()
        actual_profile = official_actual_projection_profile_v1(
            registry, profile
        )
        aggregate = derive_marginal_work_aggregate_v1(
            subject_id=subject_id,
            route_kind=route_kind,
            execution=(
                selected_work.work_vector,
                selected_work.comparison_vector,
                selected_work.actual_projection_proof,
            ),
            verification_suffix=(
                verification_work.work_vector,
                verification_work.comparison_vector,
                verification_work.actual_projection_proof,
            ),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual_profile,
        )
        compliance = _check_authoritative_upper(aggregate, selected_upper)
    except Exception as error:
        # Once a semantic decision has frozen, every observable selected-route
        # failure must retain its native work and access prefix.  This is a
        # noncertificate closure only; it never becomes a plan or
        # infeasibility result.
        try:
            failure_evidence = _build_failed_route_evidence_v1(
                error=error,
                prepared=prepared,
                decision=decision,
                selected_upper=selected_upper,
                execution=execution,
                controller=controller,
                route_recorder=route_recorder,
                verification_recorder=verification_recorder,
                registry=registry,
                comparison_profile=profile,
            )
        except Exception as preservation_error:
            raise Phase3ERunnerV1Error(
                "selected route failed and its observable partial evidence could "
                "not be sealed without ambiguity; original="
                f"{type(error).__module__}.{type(error).__qualname__}: {error}; "
                f"preservation={preservation_error}"
            ) from error
        raise Phase3ERouteExecutionFailedV1(
            failure_evidence,
            original_error=error,
        ) from error

    freeze = controller.freeze_attestation
    if freeze is None:  # pragma: no cover - established by decide_then_execute
        raise Phase3ERunnerV1Error("selected route executed without a freeze")
    return Phase3ERunResultV1(
        VERTICAL_SLICE_STATUS,
        decision.selected_route,
        decision,
        selected_upper,
        execution,
        prepared.common_prefix_work,
        selected_work,
        verification_work,
        aggregate,
        prepared.reusable_rapm_id,
        prepared.preselection_reads,
        compliance,
        controller.snapshot(),
        freeze,
    )


__all__ = [
    "AccessNativeReconciliationStatusV1",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "FailedRouteErrorClassV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PROFILE_KEY",
    "Phase3EDecisionAuthorizationV1",
    "Phase3EFailedRouteEvidenceV1",
    "Phase3EPreselectionReadV1",
    "Phase3ERouteExecutionV1",
    "Phase3ERouteExecutionFailedV1",
    "Phase3ERouteExecutorV1",
    "Phase3ERunResultV1",
    "Phase3ERunnerV1Error",
    "PreparedPhase3ERunV1",
    "VERTICAL_SLICE_STATUS",
    "UNASSIGNED_POSTFREEZE_OPERATIONAL_LEAVES",
    "UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "run_phase3e",
    "verify_failed_route_evidence_v1",
]
