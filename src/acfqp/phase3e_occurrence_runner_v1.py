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

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRegistryV1,
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
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
)
from acfqp.phase3e_ids import parse_content_id
from acfqp.phase3e_local_semantics_v1 import (
    LocalSolverOutcome,
    PostAuditOutcome,
    TrustedLocalExecutionV1,
)
from acfqp.native_recorder_v1 import RecordedWorkV1
from acfqp.phase3e_occurrence_accounting_v1 import (
    OccurrenceWorkComponentEvidenceV1,
    OccurrenceWorkComponentKind,
    Phase3EOccurrenceWorkAggregateV1,
    RunnerMarginalWorkEvidenceV1,
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
    Phase3EPreselectionReadV1,
    Phase3ERouteExecutorV1,
    Phase3ERunResultV1,
    PreparedPhase3ERunV1,
    run_phase3e,
)
from acfqp.phase3e_transactions_v1 import (
    LocalContinuationDirectiveV1,
    LocalContinuationRoute,
    SecondTransactionCandidateV1,
    authorize_second_transaction_v1,
    prepare_second_transaction_candidate_v1,
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
    """All structural and semantic inputs needed to authorize transaction 2."""

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
    first_local_work_result: object = field(repr=False, compare=False)
    first_local_solver_result: object = field(repr=False, compare=False)
    post_audit_failure_result: object = field(repr=False, compare=False)
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


@dataclass(frozen=True, slots=True)
class FreshFallbackAuthorityPackageV1:
    """Fresh fallback-only decision and all semantic authority for it."""

    context: RouteDecisionContextV1
    failure_kind: LocalFailureKind
    failure_result: object = field(repr=False, compare=False)
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
    prior_work_results: tuple[object, ...] = field(repr=False, compare=False)
    common_prefix_work_result: object = field(repr=False, compare=False)
    cardinality_result: object = field(repr=False, compare=False)
    fallback_upper_result: object = field(repr=False, compare=False)
    route_decision_result: object = field(repr=False, compare=False)
    reusable_rapm_id: str
    failed_certificate_id: str
    action_catalogue_id: str
    preselection_reads: tuple[Phase3EPreselectionReadV1, ...]
    fallback_executor: Phase3ERouteExecutorV1 = field(repr=False, compare=False)

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


class SecondTransactionPlannerV1(Protocol):
    def __call__(
        self, observation: LocalFailureObservationV1
    ) -> SecondTransactionAuthorityPackageV1: ...


class FreshFallbackPlannerV1(Protocol):
    def __call__(
        self, observation: LocalFailureObservationV1
    ) -> FreshFallbackAuthorityPackageV1: ...


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
        if not self.decision_runs or len(self.decision_runs) > 3:
            raise Phase3EOccurrenceRunnerV1Error(
                "an occurrence needs one to three one-decision runs"
            )
        if type(self.decision_runs) is not tuple or type(
            self.transactions
        ) is not tuple or type(self.work_components) is not tuple:
            raise Phase3EOccurrenceRunnerV1Error(
                "occurrence result histories must be immutable"
            )
        if len(self.work_components) != 2 * len(self.decision_runs):
            raise Phase3EOccurrenceRunnerV1Error(
                "each decision run must retain its prefix and marginal work"
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
            (result.common_prefix_work,),
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


def _observe_local_failure(
    *,
    prepared: PreparedPhase3ERunV1,
    result: Phase3ERunResultV1,
    transaction: TransactionV1,
    transactions: tuple[TransactionV1, ...],
    local_runs: tuple[Phase3ERunResultV1, ...],
) -> LocalFailureObservationV1 | None:
    execution = result.route_execution.semantic_execution
    if not isinstance(execution, TrustedLocalExecutionV1):
        raise Phase3EOccurrenceRunnerV1Error(
            "selected LOCAL run lacks trusted local semantic execution"
        )
    if (
        execution.local_result.selected_upper_id
        != result.selected_upper.route_upper_bound_envelope_id
        or execution.local_result.transaction_id != transaction.transaction_id
        or execution.local_result.work_vector_id
        != result.selected_route_work.work_vector.work_vector_id
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
    if not isinstance(local_execution, TrustedLocalExecutionV1) or (
        local_execution.post_audit is None
    ):
        raise Phase3EOccurrenceRunnerV1Error(
            "transaction-2 request lacks the failed trusted local execution"
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
            first_local_work_result=package.first_local_work_result,
            first_local_solver_result=package.first_local_solver_result,
            post_audit_failure_result=package.post_audit_failure_result,
            causal_result=package.causal_result,
            local_cardinality_result=package.local_cardinality_result,
            fallback_cardinality_result=package.fallback_cardinality_result,
            local_upper_result=package.local_upper_result,
            fallback_upper_result=package.fallback_upper_result,
            route_decision_result=package.route_decision_result,
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
    prepared = PreparedPhase3ERunV1(
        package.second_context,
        package.second_decision_point,
        package.reusable_rapm_id,
        package.failed_certificate_id,
        package.action_catalogue_id,
        package.preselection_reads,
        package.second_common_prefix_work,
        authorization,
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
            failure_result=package.failure_result,
            prior_work_results=package.prior_work_results,
            common_prefix_work_result=package.common_prefix_work_result,
            cardinality_result=package.cardinality_result,
            fallback_upper_result=package.fallback_upper_result,
            route_decision_result=package.route_decision_result,
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
    prepared = PreparedPhase3ERunV1(
        package.context,
        package.fallback_decision_point,
        package.reusable_rapm_id,
        package.failed_certificate_id,
        package.action_catalogue_id,
        package.preselection_reads,
        package.fallback_common_prefix_work,
        authorization,
    )
    return prepared, candidate, authorized


def _fallback_closure(result: Phase3ERunResultV1) -> OccurrenceClosureCodeV1:
    execution = result.route_execution.semantic_execution
    if not isinstance(execution, GroundFallbackExecutionV1):
        raise Phase3EOccurrenceRunnerV1Error(
            "selected FALLBACK run lacks trusted ground-fallback execution"
        )
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
    return Phase3EOccurrenceRunResultV1(
        closure,
        runs,
        transactions,
        components,
        aggregate,
        continuation_authorities,
        closure is OccurrenceClosureCodeV1.FULL_GROUND_EXACT_INFEASIBLE,
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
    ) -> tuple[Phase3ERunResultV1, TransactionV1 | None]:
        result = run_phase3e(
            prepared,
            local_executor=local,
            fallback_executor=fallback,
            registry=trusted_registry,
            comparison_profile=profile,
        )
        if not isinstance(result, Phase3ERunResultV1):
            raise Phase3EOccurrenceRunnerV1Error(
                "one-decision runner returned an untyped result"
            )
        transaction = _transaction_from_run(prepared, result)
        runs.append(result)
        if transaction is not None:
            transactions.append(transaction)
        components.extend(_components_for_run(prepared, result, transaction))
        return result, transaction

    result, transaction = execute(
        initial_prepared, local_executor, fallback_executor
    )
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
            raise Phase3EOccurrenceRunnerV1Error(
                "failed transaction 1 lacks a transaction-2 authority planner"
            )
        package = second_transaction_planner(observation)
        if not isinstance(package, SecondTransactionAuthorityPackageV1):
            raise Phase3EOccurrenceRunnerV1Error(
                "transaction-2 planner returned an untyped package"
            )
        second_prepared, candidate, directive = _prepare_second_run(
            observation, package
        )
        continuation_authorities.extend((candidate, directive))
        second_result, second_transaction = execute(
            second_prepared,
            (
                package.local_executor
                if directive.next_route
                is LocalContinuationRoute.SECOND_LOCAL_TRANSACTION
                else _forbidden_local_executor
            ),
            package.fallback_executor,
        )
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
        raise Phase3EOccurrenceRunnerV1Error(
            "local failure lacks a fresh fallback-only authority planner"
        )
    fallback_package = fresh_fallback_planner(observation)
    if not isinstance(fallback_package, FreshFallbackAuthorityPackageV1):
        raise Phase3EOccurrenceRunnerV1Error(
            "fallback planner returned an untyped authority package"
        )
    fallback_prepared, fallback_candidate, fallback_authority = (
        _prepare_fallback_run(observation, fallback_package)
    )
    continuation_authorities.extend(
        (fallback_candidate, fallback_authority)
    )
    fallback_result, fallback_transaction = execute(
        fallback_prepared,
        _forbidden_local_executor,
        fallback_package.fallback_executor,
    )
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
    "Phase3EOccurrenceRunResultV1",
    "Phase3EOccurrenceRunnerV1Error",
    "SecondTransactionAuthorityPackageV1",
    "SecondTransactionPlannerV1",
    "run_phase3e_occurrence_v1",
]
