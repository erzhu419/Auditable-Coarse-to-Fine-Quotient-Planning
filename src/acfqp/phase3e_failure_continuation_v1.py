"""Fresh fallback decision preparation after a failed local transaction.

FQ2 closes a local transaction before fallback is considered.  Consequently a
fallback route may not reuse the decision point or the fallback upper that
preceded the failed local attempt.  This module makes that boundary explicit:

* :func:`prepare_fallback_after_local_failure_v1` validates a newly built,
  fallback-only decision chain but grants no execution authority;
* :func:`authorize_fallback_after_local_failure_v1` accepts that chain only
  after the local failure, cardinality, upper, and route decision have each
  been semantically replayed.

The partial semantic profile implements ``POST_AUDIT`` and
``LOCAL_SOLVER_RESULT`` only for opaque Phase-3D safe-chain runtime provenance.
Raw or structurally plausible artifacts remain inert, and the integrated
production adapter that mints those runtime seals is still a separate gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRegistryV1,
    RouteKindEnum,
    WorkVectorV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import RecordedWorkV1, verify_recorded_work_v1
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
)
from acfqp.phase3e_ids import parse_content_id
from acfqp.routing_v1 import (
    BudgetOutcome,
    CardinalityEvidenceV1,
    DecisionPointV1,
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


class Phase3EFailureContinuationV1Error(ValueError):
    """A post-local fallback chain is stale, incomplete, or unauthorized."""


class LocalFailureKind(str, Enum):
    POST_AUDIT_FAILED = "POST_AUDIT_FAILED"
    LOCAL_SEARCH_CAP_EXHAUSTED = "LOCAL_SEARCH_CAP_EXHAUSTED"
    LOCAL_NO_FEASIBLE_ASSIGNMENT = "LOCAL_NO_FEASIBLE_ASSIGNMENT"


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3EFailureContinuationV1Error(
            f"{field_name} must be a full Phase-3E content ID"
        ) from error


def _typed_na(value: object) -> bool:
    return isinstance(value, TypedNotApplicable)


@dataclass(frozen=True, slots=True)
class FallbackAfterLocalFailureCandidateV1:
    """Complete structural input for a fresh fallback-only decision.

    ``execution_authorized`` is permanently false.  In particular, retaining
    a route-decision-shaped object here does not make its raw hash executable.
    """

    context: RouteDecisionContextV1
    failure_kind: LocalFailureKind
    failure_artifact_id: str
    transactions: tuple[TransactionV1, ...]
    prior_local_work_vectors: tuple[WorkVectorV1, ...]
    prior_route_upper_ids: tuple[str, ...]
    prior_fallback_cardinality_bound_ids: tuple[str, ...]
    fallback_common_prefix_work: RecordedWorkV1
    fallback_decision_point: DecisionPointV1
    fallback_cap_profile: GroundFallbackCapProfileV1
    fallback_cardinality_bound: GroundFallbackCardinalityBoundV1
    fallback_cardinality: CardinalityEvidenceV1
    fallback_upper: RouteUpperBoundEnvelopeV1
    fallback_route_decision: MarginalRouteDecisionV1
    budget_replay: TrustedBudgetReplayV1
    execution_authorized: bool = False
    infeasibility_certified: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "failure_kind", LocalFailureKind(self.failure_kind))
        _cid(self.failure_artifact_id, "failure_artifact_id")
        if self.execution_authorized is not False:
            raise Phase3EFailureContinuationV1Error(
                "a structural fallback candidate cannot authorize execution"
            )
        if self.infeasibility_certified is not False:
            raise Phase3EFailureContinuationV1Error(
                "local failure or cap exhaustion cannot certify infeasibility"
            )

    @property
    def preserved_local_work_vector_ids(self) -> tuple[str, ...]:
        return tuple(vector.work_vector_id for vector in self.prior_local_work_vectors)


_FRESH_FALLBACK_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class AuthorizedFallbackAfterLocalFailureV1:
    """Runtime-only authority handle for the newly selected fallback route."""

    candidate: FallbackAfterLocalFailureCandidateV1
    failure_result: object = field(repr=False, compare=False)
    prior_work_results: tuple[object, ...] = field(repr=False, compare=False)
    common_prefix_work_result: object = field(repr=False, compare=False)
    cardinality_result: object = field(repr=False, compare=False)
    fallback_upper_result: object = field(repr=False, compare=False)
    route_decision_result: object = field(repr=False, compare=False)
    infeasibility_certified: bool = False
    _authority: object = field(default=None, repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _FRESH_FALLBACK_AUTHORITY:
            raise Phase3EFailureContinuationV1Error(
                "fresh fallback continuation lacks semantic authority"
            )
        if self.infeasibility_certified is not False:
            raise Phase3EFailureContinuationV1Error(
                "local failure or cap exhaustion is never infeasibility evidence"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_FRESH_FALLBACK_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise Phase3EFailureContinuationV1Error(
                    "fresh fallback continuation is a copied or modified authority"
                ) from error

    @property
    def selected_route(self) -> RouteSelection:
        return RouteSelection.FALLBACK

    @property
    def preserved_local_work_vector_ids(self) -> tuple[str, ...]:
        return self.candidate.preserved_local_work_vector_ids


def require_authorized_fallback_after_local_failure_v1(
    authority: object,
) -> AuthorizedFallbackAfterLocalFailureV1:
    """Require the exact semantic-replay fallback continuation instance."""

    if type(authority) is not AuthorizedFallbackAfterLocalFailureV1:
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback continuation lacks semantic authority"
        )
    try:
        require_runtime_authority_v1(
            authority,
            issuer=_FRESH_FALLBACK_AUTHORITY,
        )
    except ValueError as error:
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback continuation is not the retained minted instance"
        ) from error
    return authority


def prepare_fallback_after_local_failure_v1(
    *,
    context: RouteDecisionContextV1,
    failure_kind: LocalFailureKind | str,
    failure_artifact_id: str,
    transactions: tuple[TransactionV1, ...],
    prior_local_work_vectors: tuple[WorkVectorV1, ...],
    local_cap_profile: RouteCapProfileV1,
    prior_route_upper_ids: tuple[str, ...],
    fallback_common_prefix_work: RecordedWorkV1,
    fallback_decision_point: DecisionPointV1,
    fallback_cap_profile: GroundFallbackCapProfileV1,
    fallback_cardinality_bound: GroundFallbackCardinalityBoundV1,
    fallback_cardinality: CardinalityEvidenceV1,
    fallback_upper: RouteUpperBoundEnvelopeV1,
    fallback_route_decision: MarginalRouteDecisionV1,
    prior_fallback_cardinality_bound_ids: tuple[str, ...] = (),
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> FallbackAfterLocalFailureCandidateV1:
    """Validate a fresh fallback decision without granting execution rights."""

    if not isinstance(context, RouteDecisionContextV1):
        raise Phase3EFailureContinuationV1Error(
            "fallback continuation requires RouteDecisionContextV1"
        )
    try:
        kind = LocalFailureKind(failure_kind)
    except (TypeError, ValueError) as error:
        raise Phase3EFailureContinuationV1Error(
            "unknown local failure kind"
        ) from error
    failure_id = _cid(failure_artifact_id, "failure_artifact_id")
    trusted_registry = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(trusted_registry)
    try:
        trusted_registry.validate_official_catalogue()
        profile.validate(trusted_registry)
        RouteCapProfileV1.from_dict(local_cap_profile.to_dict())
        GroundFallbackCapProfileV1.from_dict(fallback_cap_profile.to_dict())
    except ValueError as error:
        raise Phase3EFailureContinuationV1Error(str(error)) from error
    if (
        context.counter_registry_id != trusted_registry.registry_id
        or context.comparison_profile_id != profile.comparison_profile_id
    ):
        raise Phase3EFailureContinuationV1Error(
            "fallback context uses another accounting profile"
        )

    transaction_rows = tuple(transactions)
    work_rows = tuple(prior_local_work_vectors)
    if len(transaction_rows) not in {1, 2} or len(work_rows) != len(
        transaction_rows
    ):
        raise Phase3EFailureContinuationV1Error(
            "fallback continuation requires one or two completed local transactions"
        )
    for expected_index, (transaction, vector) in enumerate(
        zip(transaction_rows, work_rows, strict=True), start=1
    ):
        if transaction.transaction_index != expected_index:
            raise Phase3EFailureContinuationV1Error(
                "completed transaction indices must be continuous from 1"
            )
        if (
            transaction.logical_occurrence_id != context.logical_occurrence_id
            or transaction.route_attempt_id != context.route_attempt_id
        ):
            raise Phase3EFailureContinuationV1Error(
                "fallback continuation mixes occurrence or route-attempt identities"
            )
        if vector.route_kind is not RouteKindEnum.LOCAL_ATTEMPT:
            raise Phase3EFailureContinuationV1Error(
                "preserved work is not a local-attempt WorkVector"
            )
        if vector.subject_id != transaction.transaction_id:
            raise Phase3EFailureContinuationV1Error(
                "preserved WorkVector does not bind its transaction"
            )
    try:
        budget_replay = TrustedBudgetReplayV1.replay_work_vectors(
            transaction_rows,
            work_rows,
            local_cap_profile,
            worker_claim=TypedNotApplicable(
                "trusted replay, not a worker claim, controls continuation"
            ),
            registry=trusted_registry,
        )
    except ValueError as error:
        raise Phase3EFailureContinuationV1Error(
            f"local transaction budget replay failed: {error}"
        ) from error
    if len(transaction_rows) == 2 and (
        budget_replay.trusted_outcome is not BudgetOutcome.BUDGET_EXHAUSTED
    ):
        raise Phase3EFailureContinuationV1Error(
            "two local transactions must exhaust the V0 transaction budget"
        )

    try:
        verified_prefix = verify_recorded_work_v1(
            fallback_common_prefix_work,
            expected_scope=ActualWorkScope.COMMON_PREFIX,
            registry=trusted_registry,
            comparison_profile=profile,
        )
    except ValueError as error:
        raise Phase3EFailureContinuationV1Error(
            f"fresh fallback common-prefix work does not replay: {error}"
        ) from error
    prefix_vector = verified_prefix.work_vector
    if (
        prefix_vector.route_kind not in {
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        }
        or prefix_vector.subject_id != context.route_attempt_id
        or fallback_decision_point.common_prefix_work_id
        != prefix_vector.work_vector_id
    ):
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback decision point does not bind its common-prefix WorkVector"
        )
    if prefix_vector.work_vector_id in {
        vector.work_vector_id for vector in work_rows
    }:
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback prefix reused prior local work"
        )
    if (
        fallback_decision_point.route_decision_context_id
        != context.route_decision_context_id
        or not _typed_na(fallback_decision_point.transaction_index)
        or not _typed_na(fallback_decision_point.frontier_snapshot_id)
        or not _typed_na(fallback_decision_point.causal_evidence_id)
    ):
        raise Phase3EFailureContinuationV1Error(
            "post-local fallback requires a fallback-only fresh decision point"
        )
    if fallback_decision_point.decision_point_id in {
        transaction.decision_point_id for transaction in transaction_rows
    }:
        raise Phase3EFailureContinuationV1Error(
            "post-local fallback reused the failed local decision point"
        )

    old_upper_ids = tuple(
        _cid(value, "prior_route_upper_id") for value in prior_route_upper_ids
    )
    if not old_upper_ids or len(set(old_upper_ids)) != len(old_upper_ids):
        raise Phase3EFailureContinuationV1Error(
            "prior route-upper identities must be nonempty and unique"
        )
    old_bound_ids = tuple(
        _cid(value, "prior_fallback_cardinality_bound_id")
        for value in prior_fallback_cardinality_bound_ids
    )
    if len(set(old_bound_ids)) != len(old_bound_ids):
        raise Phase3EFailureContinuationV1Error(
            "prior fallback cardinality-bound identities repeat"
        )

    fallback_cardinality_bound.validate_against_cap(fallback_cap_profile)
    if (
        fallback_cardinality_bound.route_decision_context_id
        != context.route_decision_context_id
        or fallback_cardinality_bound.decision_point_id
        != fallback_decision_point.decision_point_id
        or fallback_cardinality_bound.ground_fallback_cap_profile_id
        != fallback_cap_profile.ground_fallback_cap_profile_id
    ):
        raise Phase3EFailureContinuationV1Error(
            "fallback cardinality bound is stale for the fresh decision point"
        )
    if (
        fallback_cardinality_bound.ground_fallback_cardinality_bound_id
        in set(old_bound_ids)
    ):
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback reused an old cardinality-bound identity"
        )
    if (
        fallback_cardinality.route_decision_context_id
        != context.route_decision_context_id
        or fallback_cardinality.route_kind is not RouteKind.DIRECT_FALLBACK
        or fallback_cardinality.route_cap_profile_id
        != fallback_cap_profile.ground_fallback_cap_profile_id
        or not _typed_na(fallback_cardinality.frontier_snapshot_id)
        or fallback_cardinality_bound.ground_fallback_cardinality_bound_id
        not in fallback_cardinality.source_artifact_ids
        or fallback_cardinality.counts
        != fallback_cardinality_bound.operational_count_values(trusted_registry)
    ):
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback cardinality evidence does not project its bound source"
        )

    try:
        fallback_upper.validate_bindings(
            context,
            fallback_decision_point,
            fallback_cardinality,
        )
    except ValueError as error:
        raise Phase3EFailureContinuationV1Error(
            f"fresh fallback upper binding failed: {error}"
        ) from error
    if (
        fallback_upper.route_kind is not RouteKind.DIRECT_FALLBACK
        or fallback_upper.route_cap_profile_id
        != fallback_cap_profile.ground_fallback_cap_profile_id
    ):
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback upper uses another route or cap profile"
        )
    if fallback_upper.route_upper_bound_envelope_id in set(old_upper_ids):
        raise Phase3EFailureContinuationV1Error(
            "post-local fallback reused a stale route upper"
        )
    expected_decision = MarginalRouteDecisionV1.select(
        fallback_decision_point,
        fallback_upper,
        causal=None,
        local_upper=None,
    )
    if fallback_route_decision != expected_decision:
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback route decision differs from selector replay"
        )
    if (
        fallback_route_decision.selected_route is not RouteSelection.FALLBACK
        or fallback_route_decision.selected_upper_id
        != fallback_upper.route_upper_bound_envelope_id
    ):
        raise Phase3EFailureContinuationV1Error(
            "post-local continuation did not select the fresh fallback upper"
        )

    return FallbackAfterLocalFailureCandidateV1(
        context,
        kind,
        failure_id,
        transaction_rows,
        work_rows,
        old_upper_ids,
        old_bound_ids,
        verified_prefix,
        fallback_decision_point,
        fallback_cap_profile,
        fallback_cardinality_bound,
        fallback_cardinality,
        fallback_upper,
        fallback_route_decision,
        budget_replay,
    )


def _require_new_binding(
    result: Any,
    candidate: FallbackAfterLocalFailureCandidateV1,
) -> None:
    binding = result.binding
    if (
        binding.route_context != candidate.context
        or binding.decision_point_id
        != candidate.fallback_decision_point.decision_point_id
        or not _typed_na(binding.transaction_id)
    ):
        raise Phase3EFailureContinuationV1Error(
            "fallback authority belongs to another context or decision point"
        )


def authorize_fallback_after_local_failure_v1(
    candidate: FallbackAfterLocalFailureCandidateV1,
    *,
    failure_result: Any,
    prior_work_results: tuple[Any, ...],
    common_prefix_work_result: Any,
    cardinality_result: Any,
    fallback_upper_result: Any,
    route_decision_result: Any,
) -> AuthorizedFallbackAfterLocalFailureV1:
    """Authorize only the fresh post-failure fallback decision chain."""

    if not isinstance(candidate, FallbackAfterLocalFailureCandidateV1):
        raise Phase3EFailureContinuationV1Error(
            "fallback authorization requires its structural candidate"
        )
    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        require_semantic_verification_result_v1,
    )

    failure_role, failure_outcome = {
        LocalFailureKind.POST_AUDIT_FAILED: (
            SemanticRole.POST_AUDIT,
            "FAILED",
        ),
        LocalFailureKind.LOCAL_SEARCH_CAP_EXHAUSTED: (
            SemanticRole.LOCAL_SOLVER_RESULT,
            "SEARCH_CAP_EXHAUSTED",
        ),
        LocalFailureKind.LOCAL_NO_FEASIBLE_ASSIGNMENT: (
            SemanticRole.LOCAL_SOLVER_RESULT,
            "NO_FEASIBLE_ASSIGNMENT",
        ),
    }[candidate.failure_kind]
    verified_failure = require_semantic_verification_result_v1(
        failure_result, failure_role
    )
    if type(prior_work_results) is not tuple or len(prior_work_results) != len(
        candidate.transactions
    ):
        raise Phase3EFailureContinuationV1Error(
            "each preserved local WorkVector requires semantic authority"
        )
    verified_prior_work = tuple(
        require_semantic_verification_result_v1(result, SemanticRole.WORK_VECTOR)
        for result in prior_work_results
    )
    verified_prefix_work = require_semantic_verification_result_v1(
        common_prefix_work_result, SemanticRole.WORK_VECTOR
    )
    verified_cardinality = require_semantic_verification_result_v1(
        cardinality_result, SemanticRole.CARDINALITY_EVIDENCE
    )
    verified_upper = require_semantic_verification_result_v1(
        fallback_upper_result, SemanticRole.ROUTE_UPPER
    )
    verified_decision = require_semantic_verification_result_v1(
        route_decision_result, SemanticRole.ROUTE_DECISION
    )

    last_transaction = candidate.transactions[-1]
    if (
        verified_failure.outcome != failure_outcome
        or verified_failure.attestation.artifact_id
        != candidate.failure_artifact_id
        or verified_failure.binding.route_context != candidate.context
        or verified_failure.binding.decision_point_id
        != last_transaction.decision_point_id
        or verified_failure.binding.transaction_id
        != last_transaction.transaction_id
    ):
        raise Phase3EFailureContinuationV1Error(
            "local-failure authority does not bind the completed transaction"
        )
    stable_fields = (
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
    for transaction, vector, result in zip(
        candidate.transactions,
        candidate.prior_local_work_vectors,
        verified_prior_work,
        strict=True,
    ):
        if (
            result.outcome != "VALID"
            or result.artifact != vector
            or result.attestation.artifact_id != vector.work_vector_id
            or result.binding.transaction_id != transaction.transaction_id
            or result.binding.decision_point_id != transaction.decision_point_id
            or any(
                getattr(result.binding.route_context, name)
                != getattr(candidate.context, name)
                for name in stable_fields
            )
        ):
            raise Phase3EFailureContinuationV1Error(
                "preserved local WorkVector lacks matching semantic authority"
            )
    prefix_vector = candidate.fallback_common_prefix_work.work_vector
    if (
        verified_prefix_work.outcome != "VALID"
        or verified_prefix_work.artifact != prefix_vector
        or verified_prefix_work.attestation.artifact_id
        != prefix_vector.work_vector_id
        or verified_prefix_work.binding.route_context != candidate.context
        or verified_prefix_work.binding.decision_point_id
        != candidate.fallback_decision_point.decision_point_id
        or not _typed_na(verified_prefix_work.binding.transaction_id)
    ):
        raise Phase3EFailureContinuationV1Error(
            "fresh fallback common-prefix WorkVector lacks semantic authority"
        )
    expected = (
        (
            verified_cardinality,
            "VALID",
            candidate.fallback_cardinality,
            candidate.fallback_cardinality.cardinality_evidence_id,
        ),
        (
            verified_upper,
            "VALID",
            candidate.fallback_upper,
            candidate.fallback_upper.route_upper_bound_envelope_id,
        ),
        (
            verified_decision,
            RouteSelection.FALLBACK.value,
            candidate.fallback_route_decision,
            candidate.fallback_route_decision.route_decision_id,
        ),
    )
    for result, outcome, artifact, artifact_id in expected:
        if (
            result.outcome != outcome
            or result.artifact != artifact
            or result.attestation.artifact_id != artifact_id
        ):
            raise Phase3EFailureContinuationV1Error(
                "fresh fallback semantic authority carries another artifact or outcome"
            )
        _require_new_binding(result, candidate)

    authority = AuthorizedFallbackAfterLocalFailureV1(
        candidate,
        verified_failure,
        verified_prior_work,
        verified_prefix_work,
        verified_cardinality,
        verified_upper,
        verified_decision,
        False,
        _FRESH_FALLBACK_AUTHORITY,
    )
    return bind_runtime_authority_v1(
        authority,
        issuer=_FRESH_FALLBACK_AUTHORITY,
    )


__all__ = [
    "AuthorizedFallbackAfterLocalFailureV1",
    "FallbackAfterLocalFailureCandidateV1",
    "LocalFailureKind",
    "Phase3EFailureContinuationV1Error",
    "authorize_fallback_after_local_failure_v1",
    "prepare_fallback_after_local_failure_v1",
    "require_authorized_fallback_after_local_failure_v1",
]
