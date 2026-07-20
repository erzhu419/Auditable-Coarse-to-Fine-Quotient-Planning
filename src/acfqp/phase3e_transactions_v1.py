"""Fail-closed orchestration for the optional second local transaction.

This module does not decide that a post-audit failed by reading a status
string.  Structural preparation is intentionally non-authoritative; the
execution directive is emitted only after the relevant FQ7 semantic replay
handles are supplied.  The post-audit role now has a scoped safe-chain runtime
verifier, while causal search and local-cardinality authority remain explicit
fail-closed prerequisites for a positive second-local directive.

The helper preserves the first transaction's native ``WorkVectorV1`` and uses
``TrustedBudgetReplayV1`` to derive the remaining budget.  A second local
attempt requires a strictly deeper frontier, a new selected-plan context, a
new decision point/common prefix, transaction index 2, and fresh local and
fallback upper identities.  Cap exhaustion and exhausted transaction budget
always route to direct fallback and never become infeasibility evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, NoReturn

from acfqp.accounting_v1 import (
    CounterRegistryV1,
    RouteKindEnum,
    WorkVectorV1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import (
    NativeRecorderV1Error,
    RecordedWorkV1,
    verify_recorded_work_v1,
)
from acfqp.phase3e_ids import parse_content_id
from acfqp.routing_v1 import (
    BudgetOutcome,
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    FrontierSnapshotV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TransactionV1,
    TrustedBudgetReplayV1,
    TypedNotApplicable,
)


class Phase3ETransactionV1Error(ValueError):
    """A transaction continuation is stale, unauthorised, or over budget."""


class LocalContinuationRoute(str, Enum):
    SECOND_LOCAL_TRANSACTION = "SECOND_LOCAL_TRANSACTION"
    DIRECT_FALLBACK = "DIRECT_FALLBACK"


class LocalContinuationReason(str, Enum):
    POST_AUDIT_FAILED_DEEPER_FRONTIER = "POST_AUDIT_FAILED_DEEPER_FRONTIER"
    ROUTE_SELECTOR_CHOSE_FALLBACK = "ROUTE_SELECTOR_CHOSE_FALLBACK"
    LOCAL_CAP_EXHAUSTED = "LOCAL_CAP_EXHAUSTED"
    SECOND_TRANSACTION_FAILED = "SECOND_TRANSACTION_FAILED"
    TRANSACTION_BUDGET_EXHAUSTED = "TRANSACTION_BUDGET_EXHAUSTED"


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3ETransactionV1Error(
            f"{field_name} must be a full Phase-3E content ID"
        ) from error


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


_CANDIDATE_VALIDATION_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class SecondTransactionCandidateV1:
    """Structurally complete but non-authoritative second-transaction input."""

    first_context: RouteDecisionContextV1
    first_decision_point: DecisionPointV1
    first_frontier: FrontierSnapshotV1
    first_causal: CausalEvidenceV1
    first_transaction: TransactionV1
    first_local_work: WorkVectorV1
    first_local_upper_id: str
    first_fallback_upper_id: str
    first_local_result_artifact_id: str
    failed_post_audit_artifact_id: str
    new_stitched_plan_binding_id: str
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
    budget_replay: TrustedBudgetReplayV1
    execution_authorized: bool = False
    _validation_authority: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _cid(self.first_local_upper_id, "first_local_upper_id")
        _cid(self.first_fallback_upper_id, "first_fallback_upper_id")
        _cid(
            self.first_local_result_artifact_id,
            "first_local_result_artifact_id",
        )
        _cid(self.failed_post_audit_artifact_id, "failed_post_audit_artifact_id")
        _cid(self.new_stitched_plan_binding_id, "new_stitched_plan_binding_id")
        if not isinstance(self.second_common_prefix_work, RecordedWorkV1):
            raise Phase3ETransactionV1Error(
                "second common-prefix work must be an actual RecordedWorkV1"
            )
        if self._validation_authority is not _CANDIDATE_VALIDATION_AUTHORITY:
            raise Phase3ETransactionV1Error(
                "second-transaction candidate was not emitted by structural replay"
            )
        if self.execution_authorized is not False:
            raise Phase3ETransactionV1Error(
                "a structural candidate cannot self-authorize execution"
            )

    @property
    def preserved_first_local_work_id(self) -> str:
        return self.first_local_work.work_vector_id


_DIRECTIVE_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class LocalContinuationDirectiveV1:
    """Non-serializable authority handle for the next route."""

    next_route: LocalContinuationRoute
    reason: LocalContinuationReason
    preserved_local_work_vector_ids: tuple[str, ...]
    second_transaction: TransactionV1 | None
    budget_replay: TrustedBudgetReplayV1
    infeasibility_certified: bool = False
    _authority: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._authority is not _DIRECTIVE_AUTHORITY:
            raise Phase3ETransactionV1Error(
                "local continuation directive lacks semantic authority"
            )
        object.__setattr__(self, "next_route", LocalContinuationRoute(self.next_route))
        object.__setattr__(self, "reason", LocalContinuationReason(self.reason))
        if (
            not self.preserved_local_work_vector_ids
            or len(set(self.preserved_local_work_vector_ids))
            != len(self.preserved_local_work_vector_ids)
        ):
            raise Phase3ETransactionV1Error(
                "continuation must preserve unique prior local WorkVectors"
            )
        for work_id in self.preserved_local_work_vector_ids:
            _cid(work_id, "preserved_local_work_vector_id")
        if self.infeasibility_certified is not False:
            raise Phase3ETransactionV1Error(
                "local continuation/cap outcomes are never infeasibility certificates"
            )
        if self.next_route is LocalContinuationRoute.SECOND_LOCAL_TRANSACTION:
            if self.second_transaction is None or self.second_transaction.transaction_index != 2:
                raise Phase3ETransactionV1Error(
                    "second-local directive requires transaction index 2"
                )
            if self.budget_replay.trusted_outcome is not BudgetOutcome.BUDGET_REMAINS:
                raise Phase3ETransactionV1Error(
                    "second-local directive requires remaining transaction budget"
                )
        elif self.second_transaction is not None:
            raise Phase3ETransactionV1Error(
                "direct-fallback directive cannot authorize a local transaction"
            )


def _validate_first_transaction_chain(
    *,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    frontier: FrontierSnapshotV1,
    causal: CausalEvidenceV1,
    transaction: TransactionV1,
    work: WorkVectorV1,
    cap_profile: RouteCapProfileV1,
    registry: CounterRegistryV1,
) -> TrustedBudgetReplayV1:
    if transaction.transaction_index != 1:
        raise Phase3ETransactionV1Error(
            "only transaction 1 can be followed by a second local transaction"
        )
    if decision_point.route_decision_context_id != context.route_decision_context_id:
        raise Phase3ETransactionV1Error("first decision point/context mismatch")
    if frontier.route_decision_context_id != context.route_decision_context_id:
        raise Phase3ETransactionV1Error("first frontier/context mismatch")
    if decision_point.transaction_index != 1:
        raise Phase3ETransactionV1Error("first decision point index is not 1")
    if decision_point.frontier_snapshot_id != frontier.frontier_snapshot_id:
        raise Phase3ETransactionV1Error("first decision point/frontier mismatch")
    if decision_point.causal_evidence_id != causal.causal_evidence_id:
        raise Phase3ETransactionV1Error("first decision point/causal mismatch")
    if causal.frontier_snapshot_id != frontier.frontier_snapshot_id:
        raise Phase3ETransactionV1Error("first causal/frontier mismatch")
    if causal.outcome is not CausalOutcome.FOUND or causal.local_allowed is not True:
        raise Phase3ETransactionV1Error(
            "a post-audited first local transaction requires FOUND causal evidence"
        )
    if causal.cap_id != cap_profile.route_cap_profile_id:
        raise Phase3ETransactionV1Error("first causal/cap mismatch")
    expected_transaction = (
        context.logical_occurrence_id,
        context.route_attempt_id,
        decision_point.decision_point_id,
        frontier.frontier_snapshot_id,
        cap_profile.route_cap_profile_id,
    )
    actual_transaction = (
        transaction.logical_occurrence_id,
        transaction.route_attempt_id,
        transaction.decision_point_id,
        transaction.frontier_snapshot_id,
        transaction.route_cap_profile_id,
    )
    if actual_transaction != expected_transaction:
        raise Phase3ETransactionV1Error("first transaction identity chain mismatch")
    if work.route_kind is not RouteKindEnum.LOCAL_ATTEMPT:
        raise Phase3ETransactionV1Error("first work is not a local-attempt WorkVector")
    try:
        replay = TrustedBudgetReplayV1.replay_work_vectors(
            (transaction,),
            (work,),
            cap_profile,
            worker_claim=TypedNotApplicable(
                "worker budget claims are not trusted continuation evidence"
            ),
            registry=registry,
        )
    except ValueError as error:
        raise Phase3ETransactionV1Error(
            f"first transaction budget replay failed: {error}"
        ) from error
    if (
        replay.trusted_outcome is not BudgetOutcome.BUDGET_REMAINS
        or replay.next_transaction_index != 2
    ):
        raise Phase3ETransactionV1Error("trusted replay does not admit transaction 2")
    return replay


def prepare_second_transaction_candidate_v1(
    *,
    first_context: RouteDecisionContextV1,
    first_decision_point: DecisionPointV1,
    first_frontier: FrontierSnapshotV1,
    first_causal: CausalEvidenceV1,
    first_transaction: TransactionV1,
    first_local_work: WorkVectorV1,
    first_local_upper_id: str,
    first_fallback_upper_id: str,
    first_local_result_artifact_id: str,
    failed_post_audit_artifact_id: str,
    new_stitched_plan_binding_id: str,
    second_context: RouteDecisionContextV1,
    second_frontier: FrontierSnapshotV1,
    second_causal: CausalEvidenceV1,
    second_decision_point: DecisionPointV1,
    second_transaction: TransactionV1,
    second_local_cardinality: CardinalityEvidenceV1,
    second_fallback_cardinality: CardinalityEvidenceV1,
    second_local_upper: RouteUpperBoundEnvelopeV1,
    second_fallback_upper: RouteUpperBoundEnvelopeV1,
    second_route_decision: MarginalRouteDecisionV1,
    second_common_prefix_work: RecordedWorkV1,
    cap_profile: RouteCapProfileV1,
    registry: CounterRegistryV1 | None = None,
) -> SecondTransactionCandidateV1:
    """Validate a fresh second-decision chain without authorizing execution."""

    trusted_registry = registry or official_counter_registry_v1()
    trusted_registry.validate_official_catalogue()
    budget_replay = _validate_first_transaction_chain(
        context=first_context,
        decision_point=first_decision_point,
        frontier=first_frontier,
        causal=first_causal,
        transaction=first_transaction,
        work=first_local_work,
        cap_profile=cap_profile,
        registry=trusted_registry,
    )
    if first_local_work.value("control.cap_rejections") != 0:
        raise Phase3ETransactionV1Error(
            "a cap-exhausted first transaction must route directly to fallback"
        )
    for field_name in _STABLE_CONTEXT_FIELDS:
        if getattr(first_context, field_name) != getattr(second_context, field_name):
            raise Phase3ETransactionV1Error(
                f"second transaction changed stable context field {field_name}"
            )
    if second_context.selected_plan_id == first_context.selected_plan_id:
        raise Phase3ETransactionV1Error(
            "post-audit failure must bind a new stitched selected-plan identity"
        )
    if second_context.selected_plan_id != _cid(
        new_stitched_plan_binding_id, "new_stitched_plan_binding_id"
    ):
        raise Phase3ETransactionV1Error(
            "second context does not bind the explicitly supplied stitched plan"
        )
    if second_context.route_decision_context_id == first_context.route_decision_context_id:
        raise Phase3ETransactionV1Error("second route context identity was reused")
    if second_frontier.route_decision_context_id != second_context.route_decision_context_id:
        raise Phase3ETransactionV1Error("second frontier/context mismatch")
    if second_frontier.frontier_snapshot_id == first_frontier.frontier_snapshot_id:
        raise Phase3ETransactionV1Error("second transaction reused the old frontier")
    if second_frontier.frontier_stage <= first_frontier.frontier_stage:
        raise Phase3ETransactionV1Error(
            "second frontier must be strictly deeper than the first frontier"
        )
    if second_decision_point.route_decision_context_id != (
        second_context.route_decision_context_id
    ):
        raise Phase3ETransactionV1Error("second decision point/context mismatch")
    if second_decision_point.transaction_index != 2:
        raise Phase3ETransactionV1Error("second decision point index must be 2")
    if second_decision_point.decision_point_id == first_decision_point.decision_point_id:
        raise Phase3ETransactionV1Error("second decision point identity was reused")
    if second_decision_point.common_prefix_work_id == (
        first_decision_point.common_prefix_work_id
    ):
        raise Phase3ETransactionV1Error(
            "second decision point must bind newly charged preparation work"
        )
    try:
        verified_second_prefix = verify_recorded_work_v1(
            second_common_prefix_work,
            expected_scope=ActualWorkScope.COMMON_PREFIX,
            registry=trusted_registry,
        )
    except (NativeRecorderV1Error, TypeError, ValueError) as error:
        raise Phase3ETransactionV1Error(
            f"second common-prefix RecordedWork replay failed: {error}"
        ) from error
    if (
        verified_second_prefix.work_vector.route_kind
        is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        or verified_second_prefix.work_vector.subject_id
        != second_context.route_attempt_id
        or verified_second_prefix.work_vector.work_vector_id
        != second_decision_point.common_prefix_work_id
    ):
        raise Phase3ETransactionV1Error(
            "second common-prefix work does not bind this route attempt/decision"
        )
    if second_decision_point.frontier_snapshot_id != second_frontier.frontier_snapshot_id:
        raise Phase3ETransactionV1Error("second decision point/frontier mismatch")
    if second_decision_point.causal_evidence_id != second_causal.causal_evidence_id:
        raise Phase3ETransactionV1Error("second decision point/causal mismatch")
    if (
        second_causal.frontier_snapshot_id != second_frontier.frontier_snapshot_id
        or second_causal.outcome is not CausalOutcome.FOUND
        or second_causal.local_allowed is not True
        or second_causal.cap_id != cap_profile.route_cap_profile_id
    ):
        raise Phase3ETransactionV1Error(
            "second local attempt requires fresh FOUND causal evidence under current cap"
        )
    expected_second_transaction = (
        second_context.logical_occurrence_id,
        second_context.route_attempt_id,
        second_decision_point.decision_point_id,
        2,
        second_frontier.frontier_snapshot_id,
        cap_profile.route_cap_profile_id,
    )
    actual_second_transaction = (
        second_transaction.logical_occurrence_id,
        second_transaction.route_attempt_id,
        second_transaction.decision_point_id,
        second_transaction.transaction_index,
        second_transaction.frontier_snapshot_id,
        second_transaction.route_cap_profile_id,
    )
    if actual_second_transaction != expected_second_transaction:
        raise Phase3ETransactionV1Error("second transaction identity chain mismatch")

    second_local_upper.validate_bindings(
        second_context,
        second_decision_point,
        second_local_cardinality,
        transaction=second_transaction,
        causal=second_causal,
    )
    second_fallback_upper.validate_bindings(
        second_context,
        second_decision_point,
        second_fallback_cardinality,
    )
    if second_local_upper.route_kind is not RouteKind.LOCAL_ATTEMPT:
        raise Phase3ETransactionV1Error("second local upper has the wrong route kind")
    if second_fallback_upper.route_kind is not RouteKind.DIRECT_FALLBACK:
        raise Phase3ETransactionV1Error("second fallback upper has the wrong route kind")
    old_upper_ids = {
        _cid(first_local_upper_id, "first_local_upper_id"),
        _cid(first_fallback_upper_id, "first_fallback_upper_id"),
    }
    new_upper_ids = {
        second_local_upper.route_upper_bound_envelope_id,
        second_fallback_upper.route_upper_bound_envelope_id,
    }
    if len(old_upper_ids) != 2 or len(new_upper_ids) != 2:
        raise Phase3ETransactionV1Error("local/fallback upper identities collide")
    if old_upper_ids & new_upper_ids:
        raise Phase3ETransactionV1Error(
            "second decision point reused a first-transaction route upper"
        )
    if second_local_upper.route_upper_bound_envelope_id in {
        second_fallback_upper.route_upper_bound_envelope_id,
    }:
        raise Phase3ETransactionV1Error("second route upper identities collide")
    recomputed_decision = MarginalRouteDecisionV1.select(
        second_decision_point,
        second_fallback_upper,
        causal=second_causal,
        local_upper=second_local_upper,
    )
    if second_route_decision != recomputed_decision:
        raise Phase3ETransactionV1Error(
            "second route decision differs from structural selector replay"
        )
    return SecondTransactionCandidateV1(
        first_context,
        first_decision_point,
        first_frontier,
        first_causal,
        first_transaction,
        first_local_work,
        first_local_upper_id,
        first_fallback_upper_id,
        first_local_result_artifact_id,
        failed_post_audit_artifact_id,
        new_stitched_plan_binding_id,
        second_context,
        second_frontier,
        second_causal,
        second_decision_point,
        second_transaction,
        second_local_cardinality,
        second_fallback_cardinality,
        second_local_upper,
        second_fallback_upper,
        second_route_decision,
        verified_second_prefix,
        budget_replay,
        False,
        _CANDIDATE_VALIDATION_AUTHORITY,
    )


def authorize_second_transaction_v1(
    candidate: SecondTransactionCandidateV1,
    *,
    first_local_work_result: Any,
    first_local_solver_result: Any,
    post_audit_failure_result: Any,
    causal_result: Any,
    local_cardinality_result: Any,
    fallback_cardinality_result: Any,
    local_upper_result: Any,
    fallback_upper_result: Any,
    route_decision_result: Any,
) -> LocalContinuationDirectiveV1:
    """Authorize transaction 2 or fallback from complete semantic replay."""

    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        require_semantic_verification_result_v1,
    )
    from acfqp.phase3e_local_semantics_v1 import (
        LocalSolverOutcome,
        LocalTransactionResultV1,
        PostAuditCertificateV1,
    )

    first_work = require_semantic_verification_result_v1(
        first_local_work_result, SemanticRole.WORK_VECTOR
    )
    first_local = require_semantic_verification_result_v1(
        first_local_solver_result, SemanticRole.LOCAL_SOLVER_RESULT
    )
    post = require_semantic_verification_result_v1(
        post_audit_failure_result, SemanticRole.POST_AUDIT
    )

    first_binding = (
        candidate.first_context,
        candidate.first_decision_point.decision_point_id,
        candidate.first_transaction.transaction_id,
    )
    for result, label in (
        (first_work, "first WorkVector"),
        (first_local, "first local result"),
        (post, "failed post-audit"),
    ):
        actual_binding = (
            result.binding.route_context,
            result.binding.decision_point_id,
            result.binding.transaction_id,
        )
        if actual_binding != first_binding:
            raise Phase3ETransactionV1Error(
                f"{label} does not bind the completed first context/transaction"
            )
    if (
        first_work.outcome != "VALID"
        or first_work.attestation.artifact_id
        != candidate.first_local_work.work_vector_id
        or first_work.artifact != candidate.first_local_work
    ):
        raise Phase3ETransactionV1Error(
            "first local WorkVector lacks exact WORK_VECTOR semantic authority"
        )
    if (
        first_local.outcome != LocalSolverOutcome.CANDIDATE_FOUND.value
        or first_local.attestation.artifact_id
        != candidate.first_local_result_artifact_id
        or not isinstance(first_local.artifact, LocalTransactionResultV1)
    ):
        raise Phase3ETransactionV1Error(
            "first local transaction lacks exact CANDIDATE_FOUND authority"
        )
    local_artifact = first_local.artifact
    if (
        local_artifact.work_vector_id != candidate.first_local_work.work_vector_id
        or local_artifact.selected_plan_id != candidate.first_context.selected_plan_id
        or local_artifact.stitched_plan_binding_id
        != candidate.new_stitched_plan_binding_id
    ):
        raise Phase3ETransactionV1Error(
            "first local result does not bind its plan, WorkVector, and stitched plan"
        )
    if (
        post.outcome != "FAILED"
        or post.attestation.artifact_id
        != candidate.failed_post_audit_artifact_id
        or not isinstance(post.artifact, PostAuditCertificateV1)
    ):
        raise Phase3ETransactionV1Error(
            "failed post-audit semantic artifact mismatch"
        )
    post_artifact = post.artifact
    if (
        post_artifact.local_transaction_result_id
        != candidate.first_local_result_artifact_id
        or post_artifact.work_vector_id
        != candidate.first_local_work.work_vector_id
        or post_artifact.selected_plan_id
        != candidate.first_context.selected_plan_id
        or post_artifact.stitched_plan_binding_id
        != candidate.new_stitched_plan_binding_id
        or post_artifact.threshold_profile_id
        != candidate.first_context.threshold_profile_id
        or candidate.second_context.selected_plan_id
        != candidate.new_stitched_plan_binding_id
    ):
        raise Phase3ETransactionV1Error(
            "failed post-audit does not bind the first plan/work and explicit "
            "stitched-plan continuation"
        )

    causal = require_semantic_verification_result_v1(
        causal_result, SemanticRole.CAUSAL_SEARCH
    )
    local_cardinality = require_semantic_verification_result_v1(
        local_cardinality_result, SemanticRole.CARDINALITY_EVIDENCE
    )
    fallback_cardinality = require_semantic_verification_result_v1(
        fallback_cardinality_result, SemanticRole.CARDINALITY_EVIDENCE
    )
    local_upper = require_semantic_verification_result_v1(
        local_upper_result, SemanticRole.ROUTE_UPPER
    )
    fallback_upper = require_semantic_verification_result_v1(
        fallback_upper_result, SemanticRole.ROUTE_UPPER
    )
    route_decision = require_semantic_verification_result_v1(
        route_decision_result, SemanticRole.ROUTE_DECISION
    )
    expected = (
        (causal, CausalOutcome.FOUND.value, candidate.second_causal.causal_evidence_id),
        (
            local_cardinality,
            "VALID",
            candidate.second_local_cardinality.cardinality_evidence_id,
        ),
        (
            fallback_cardinality,
            "VALID",
            candidate.second_fallback_cardinality.cardinality_evidence_id,
        ),
        (
            local_upper,
            "VALID",
            candidate.second_local_upper.route_upper_bound_envelope_id,
        ),
        (
            fallback_upper,
            "VALID",
            candidate.second_fallback_upper.route_upper_bound_envelope_id,
        ),
        (
            route_decision,
            candidate.second_route_decision.selected_route.value,
            candidate.second_route_decision.route_decision_id,
        ),
    )
    for result, outcome, artifact_id in expected:
        if result.outcome != outcome or result.attestation.artifact_id != artifact_id:
            raise Phase3ETransactionV1Error(
                "semantic continuation evidence outcome/artifact mismatch"
            )
    selected = candidate.second_route_decision.selected_route
    return LocalContinuationDirectiveV1(
        (
            LocalContinuationRoute.SECOND_LOCAL_TRANSACTION
            if selected is RouteSelection.LOCAL
            else LocalContinuationRoute.DIRECT_FALLBACK
        ),
        (
            LocalContinuationReason.POST_AUDIT_FAILED_DEEPER_FRONTIER
            if selected is RouteSelection.LOCAL
            else LocalContinuationReason.ROUTE_SELECTOR_CHOSE_FALLBACK
        ),
        (candidate.first_local_work.work_vector_id,),
        candidate.second_transaction if selected is RouteSelection.LOCAL else None,
        candidate.budget_replay,
        False,
        _DIRECTIVE_AUTHORITY,
    )


def fallback_after_local_cap_exhaustion_v1(
    *,
    transaction: TransactionV1,
    local_work: WorkVectorV1,
    cap_profile: RouteCapProfileV1,
    local_solver_result: Any,
    registry: CounterRegistryV1 | None = None,
) -> NoReturn:
    """Validate cap exhaustion, then fail closed before fallback selection.

    FQ2 requires a new decision point and freshly verified fallback upper after
    the local transaction closes.  This legacy entry point intentionally no
    longer returns a direct-route authority.  Call
    ``prepare_fallback_after_local_failure_v1`` and its semantic authorization
    boundary with the preserved work instead.
    """

    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        require_semantic_verification_result_v1,
    )

    verified = require_semantic_verification_result_v1(
        local_solver_result, SemanticRole.LOCAL_SOLVER_RESULT
    )
    if verified.outcome != "SEARCH_CAP_EXHAUSTED":
        raise Phase3ETransactionV1Error(
            "local solver evidence is not SEARCH_CAP_EXHAUSTED"
        )
    if verified.binding.transaction_id != transaction.transaction_id:
        raise Phase3ETransactionV1Error(
            "local cap-exhaustion evidence binds another transaction"
        )
    trusted_registry = registry or official_counter_registry_v1()
    replay = TrustedBudgetReplayV1.replay_work_vectors(
        (transaction,),
        (local_work,),
        cap_profile,
        worker_claim=TypedNotApplicable(
            "semantic local result replaces the worker budget claim"
        ),
        registry=trusted_registry,
    )
    del replay
    raise Phase3ETransactionV1Error(
        "local cap exhaustion requires a fresh fallback decision point and "
        "fresh fallback upper; use prepare_fallback_after_local_failure_v1"
    )


def fallback_after_second_post_audit_failure_v1(
    *,
    transactions: tuple[TransactionV1, TransactionV1],
    local_work_vectors: tuple[WorkVectorV1, WorkVectorV1],
    cap_profile: RouteCapProfileV1,
    post_audit_failure_result: Any,
    registry: CounterRegistryV1 | None = None,
) -> NoReturn:
    """Forbid transaction 3, then fail closed pending a fresh fallback decision.

    Exhausting the local transaction budget is not itself a fallback route
    decision and is never infeasibility evidence.
    """

    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        require_semantic_verification_result_v1,
    )

    verified = require_semantic_verification_result_v1(
        post_audit_failure_result, SemanticRole.POST_AUDIT
    )
    if verified.outcome != "FAILED":
        raise Phase3ETransactionV1Error("second post-audit evidence is not FAILED")
    if verified.binding.transaction_id != transactions[1].transaction_id:
        raise Phase3ETransactionV1Error(
            "second post-audit failure binds another transaction"
        )
    trusted_registry = registry or official_counter_registry_v1()
    replay = TrustedBudgetReplayV1.replay_work_vectors(
        transactions,
        local_work_vectors,
        cap_profile,
        worker_claim=TypedNotApplicable(
            "trusted replay derives the exhausted transaction budget"
        ),
        registry=trusted_registry,
    )
    if replay.trusted_outcome is not BudgetOutcome.BUDGET_EXHAUSTED:
        raise Phase3ETransactionV1Error(
            "two completed transactions did not exhaust the frozen budget"
        )
    raise Phase3ETransactionV1Error(
        "transaction-2 failure requires a fresh fallback decision point and "
        "fresh fallback upper; use prepare_fallback_after_local_failure_v1"
    )


__all__ = [
    "LocalContinuationDirectiveV1",
    "LocalContinuationReason",
    "LocalContinuationRoute",
    "Phase3ETransactionV1Error",
    "SecondTransactionCandidateV1",
    "authorize_second_transaction_v1",
    "fallback_after_local_cap_exhaustion_v1",
    "fallback_after_second_post_audit_failure_v1",
    "prepare_second_transaction_candidate_v1",
]
