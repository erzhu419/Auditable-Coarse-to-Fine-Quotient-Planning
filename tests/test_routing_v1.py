from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    SHARED_AXES,
    RouteKindEnum,
    explicit_records_v1,
    official_counter_registry_v1,
)
from acfqp.routing_v1 import (
    BudgetOutcome,
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    FrontierSnapshotV1,
    MarginalRouteDecisionV1,
    OFFICIAL_LOCAL_CAPS,
    RouteCapProfileV1,
    RouteComparison,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    RoutingV1Error,
    TIGHT_PREEXECUTION_UPPER,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TransactionV1,
    TrustedBudgetReplayV1,
    TypedNotApplicable,
    TypedVerificationAttestationV1,
    verify_unique_attestation_roles,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _shared_bounds(
    first: int = 0,
    second: int = 0,
) -> tuple[tuple[str, int], ...]:
    values = {
        KERNEL_TRANSITION_CALLS: first,
        NONKERNEL_COMPUTE_EVENTS: second,
    }
    return tuple((axis, values.get(axis, 0)) for axis in SHARED_AXES)


@pytest.fixture
def cap() -> RouteCapProfileV1:
    return RouteCapProfileV1()


@pytest.fixture
def context() -> RouteDecisionContextV1:
    return RouteDecisionContextV1(
        _id("preregistration"),
        _id("protocol"),
        _id("comparison-profile"),
        _id("counter-registry"),
        _id("structural"),
        _id("query"),
        _id("selected-plan"),
        _id("threshold"),
        _id("build-epoch"),
        _id("occurrence"),
        _id("attempt"),
    )


@pytest.fixture
def frontier(context: RouteDecisionContextV1) -> FrontierSnapshotV1:
    return FrontierSnapshotV1(
        context.route_decision_context_id,
        1,
        (_id("failed-obligation"),),
    )


@pytest.fixture
def causal(
    frontier: FrontierSnapshotV1, cap: RouteCapProfileV1
) -> CausalEvidenceV1:
    return CausalEvidenceV1(
        frontier.frontier_snapshot_id,
        CausalOutcome.FOUND,
        True,
        None,
        3,
        cap.route_cap_profile_id,
        (_id("failed-obligation"),),
    )


@pytest.fixture
def decision_point(
    context: RouteDecisionContextV1,
    frontier: FrontierSnapshotV1,
    causal: CausalEvidenceV1,
) -> DecisionPointV1:
    return DecisionPointV1(
        context.route_decision_context_id,
        1,
        frontier.frontier_snapshot_id,
        causal.causal_evidence_id,
        _id("common-prefix-work"),
    )


@pytest.fixture
def transaction(
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    frontier: FrontierSnapshotV1,
    cap: RouteCapProfileV1,
) -> TransactionV1:
    return TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        decision_point.decision_point_id,
        1,
        frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )


@pytest.fixture
def local_cardinality(
    context: RouteDecisionContextV1,
    frontier: FrontierSnapshotV1,
    cap: RouteCapProfileV1,
) -> CardinalityEvidenceV1:
    return CardinalityEvidenceV1(
        context.route_decision_context_id,
        RouteKind.LOCAL_ATTEMPT,
        cap.route_cap_profile_id,
        frontier.frontier_snapshot_id,
        (("authorized_actions", 2), ("slice_cells", 4)),
        tuple(sorted((_id("action-catalogue"), _id("failed-proof-graph")))),
    )


@pytest.fixture
def fallback_cardinality(
    context: RouteDecisionContextV1, cap: RouteCapProfileV1
) -> CardinalityEvidenceV1:
    return CardinalityEvidenceV1(
        context.route_decision_context_id,
        RouteKind.DIRECT_FALLBACK,
        cap.route_cap_profile_id,
        TypedNotApplicable("fallback cardinality is attempt-scoped"),
        (("fallback_actions", 8), ("fallback_states", 16)),
        (_id("fallback-action-catalogue"),),
    )


def _upper(
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cap: RouteCapProfileV1,
    cardinality: CardinalityEvidenceV1,
    route_kind: RouteKind,
    values: tuple[tuple[str, int], ...],
    *,
    transaction: TransactionV1 | None = None,
    causal: CausalEvidenceV1 | None = None,
) -> RouteUpperBoundEnvelopeV1:
    local = route_kind is RouteKind.LOCAL_ATTEMPT
    na = TypedNotApplicable("not applicable to direct fallback")
    return RouteUpperBoundEnvelopeV1(
        context.preregistration_id,
        context.protocol_id,
        context.comparison_profile_id,
        context.counter_registry_id,
        context.structural_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        context.build_epoch_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        decision_point.decision_point_id,
        transaction.transaction_id if local and transaction else na,
        transaction.transaction_index if local and transaction else na,
        causal.frontier_snapshot_id if local and causal else na,
        causal.causal_evidence_id if local and causal else na,
        cap.route_cap_profile_id,
        cardinality.cardinality_evidence_id,
        _id(f"formula-{route_kind.value}"),
        route_kind,
        TIGHT_PREEXECUTION_UPPER,
        values,
    )


def _local_work_vector(subject_id: str, **overrides: int):
    registry = official_counter_registry_v1()
    values = {path: 0 for path in registry.required_paths}
    values.update(overrides)
    records = explicit_records_v1(
        registry,
        values,
        recorder_id="trusted-routing-cap-replay-v1",
    )
    return registry, registry.materialize(
        subject_id=subject_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=records,
    )


def test_route_cap_profile_freezes_all_twenty_budget_values(cap: RouteCapProfileV1) -> None:
    assert len(OFFICIAL_LOCAL_CAPS) == 19
    assert cap.max_local_transactions_per_logical_occurrence == 2
    assert len(cap.route_cap_profile_id) == 64
    assert RouteCapProfileV1.from_dict(cap.to_dict()) == cap

    changed = dict(OFFICIAL_LOCAL_CAPS)
    changed["max_causal_candidate_evaluations"] = 33
    with pytest.raises(RoutingV1Error, match="frozen V0 caps"):
        RouteCapProfileV1(tuple(sorted(changed.items())))


def test_context_frontier_and_causal_round_trip_with_full_ids(
    context: RouteDecisionContextV1,
    frontier: FrontierSnapshotV1,
    causal: CausalEvidenceV1,
) -> None:
    assert RouteDecisionContextV1.from_dict(context.to_dict()) == context
    assert FrontierSnapshotV1.from_dict(frontier.to_dict()) == frontier
    assert CausalEvidenceV1.from_dict(causal.to_dict()) == causal
    assert all(
        len(value) == 64
        for value in (
            context.route_decision_context_id,
            frontier.frontier_snapshot_id,
            causal.causal_evidence_id,
        )
    )


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        (CausalOutcome.CAP_EXHAUSTED, "CAP_EXHAUSTED"),
        (CausalOutcome.NO_SOUND_COVER, "NO_SOUND_COVER"),
        (CausalOutcome.LOCAL_CAP_IMPOSSIBLE, "LOCAL_CAP_IMPOSSIBLE"),
    ],
)
def test_every_negative_causal_outcome_permanently_forbids_local(
    frontier: FrontierSnapshotV1,
    cap: RouteCapProfileV1,
    outcome: CausalOutcome,
    reason: str,
) -> None:
    evidence = CausalEvidenceV1(
        frontier.frontier_snapshot_id,
        outcome,
        False,
        reason,
        32,
        cap.route_cap_profile_id,
        (_id("failed-obligation"),),
    )
    assert evidence.local_allowed is False
    with pytest.raises(RoutingV1Error, match="permanently forbid"):
        CausalEvidenceV1(
            frontier.frontier_snapshot_id,
            outcome,
            True,
            None,
            1,
            cap.route_cap_profile_id,
            (_id("failed-obligation"),),
        )


def test_typed_null_is_not_missing_and_cannot_replace_local_fields(
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cap: RouteCapProfileV1,
    local_cardinality: CardinalityEvidenceV1,
) -> None:
    typed = TypedNotApplicable("fallback has no frontier")
    assert TypedNotApplicable.from_dict(typed.to_dict()) == typed
    with pytest.raises(RoutingV1Error, match="cannot be NOT_APPLICABLE"):
        _upper(
            context,
            decision_point,
            cap,
            local_cardinality,
            RouteKind.LOCAL_ATTEMPT,
            _shared_bounds(first=1),
        )


def test_cardinality_evidence_is_preexecution_and_route_typed(
    local_cardinality: CardinalityEvidenceV1,
    fallback_cardinality: CardinalityEvidenceV1,
) -> None:
    assert CardinalityEvidenceV1.from_dict(local_cardinality.to_dict()) == local_cardinality
    assert CardinalityEvidenceV1.from_dict(fallback_cardinality.to_dict()) == fallback_cardinality
    with pytest.raises(RoutingV1Error, match="cannot be NOT_APPLICABLE"):
        CardinalityEvidenceV1(
            local_cardinality.route_decision_context_id,
            RouteKind.LOCAL_ATTEMPT,
            local_cardinality.route_cap_profile_id,
            TypedNotApplicable("invalid local frontier"),
            local_cardinality.counts,
            local_cardinality.source_artifact_ids,
        )


def test_route_upper_binds_every_context_and_rejects_stale_identity(
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cap: RouteCapProfileV1,
    local_cardinality: CardinalityEvidenceV1,
    transaction: TransactionV1,
    causal: CausalEvidenceV1,
) -> None:
    upper = _upper(
        context,
        decision_point,
        cap,
        local_cardinality,
        RouteKind.LOCAL_ATTEMPT,
        _shared_bounds(1, 4),
        transaction=transaction,
        causal=causal,
    )
    upper.validate_bindings(
        context,
        decision_point,
        local_cardinality,
        transaction=transaction,
        causal=causal,
    )
    assert RouteUpperBoundEnvelopeV1.from_dict(upper.to_dict()) == upper

    tampered = upper.to_dict()
    tampered["selected_plan_id"] = _id("other-plan")
    with pytest.raises(RoutingV1Error, match="content ID mismatch"):
        RouteUpperBoundEnvelopeV1.from_dict(tampered)


@pytest.mark.parametrize(
    "bad_bounds",
    [
        _shared_bounds()[:-1],
        _shared_bounds() + (("unexpected_axis", 0),),
        tuple(reversed(_shared_bounds())),
        _shared_bounds()[:1] + _shared_bounds(),
    ],
    ids=("missing", "extra", "noncanonical-order", "duplicate"),
)
def test_route_upper_requires_exact_canonical_shared_axis_coverage(
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cap: RouteCapProfileV1,
    fallback_cardinality: CardinalityEvidenceV1,
    bad_bounds: tuple[tuple[str, int], ...],
) -> None:
    with pytest.raises(RoutingV1Error, match="exact eight shared axes"):
        _upper(
            context,
            decision_point,
            cap,
            fallback_cardinality,
            RouteKind.DIRECT_FALLBACK,
            bad_bounds,
        )


@pytest.mark.parametrize(
    ("local_values", "fallback_values", "selection", "comparison"),
    [
        ((1, 2), (2, 2), RouteSelection.LOCAL, RouteComparison.LOCAL_STRICTLY_DOMINATES),
        ((2, 2), (2, 2), RouteSelection.FALLBACK, RouteComparison.EQUAL),
        ((3, 2), (2, 2), RouteSelection.FALLBACK, RouteComparison.FALLBACK_DOMINATES),
        ((1, 3), (2, 2), RouteSelection.FALLBACK, RouteComparison.INCOMPARABLE),
    ],
)
def test_marginal_selection_requires_strict_componentwise_local_dominance(
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cap: RouteCapProfileV1,
    local_cardinality: CardinalityEvidenceV1,
    fallback_cardinality: CardinalityEvidenceV1,
    transaction: TransactionV1,
    causal: CausalEvidenceV1,
    local_values: tuple[int, int],
    fallback_values: tuple[int, int],
    selection: RouteSelection,
    comparison: RouteComparison,
) -> None:
    local = _upper(
        context,
        decision_point,
        cap,
        local_cardinality,
        RouteKind.LOCAL_ATTEMPT,
        _shared_bounds(*local_values),
        transaction=transaction,
        causal=causal,
    )
    fallback = _upper(
        context,
        decision_point,
        cap,
        fallback_cardinality,
        RouteKind.DIRECT_FALLBACK,
        _shared_bounds(*fallback_values),
    )
    result = MarginalRouteDecisionV1.select(
        decision_point, fallback, causal=causal, local_upper=local
    )
    assert result.selected_route is selection
    assert result.comparison is comparison
    assert len(result.route_decision_id) == 64


def test_negative_causal_evidence_cannot_be_reopened_by_a_cheap_local_upper(
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cap: RouteCapProfileV1,
    local_cardinality: CardinalityEvidenceV1,
    fallback_cardinality: CardinalityEvidenceV1,
    transaction: TransactionV1,
    frontier: FrontierSnapshotV1,
) -> None:
    forbidden = CausalEvidenceV1(
        frontier.frontier_snapshot_id,
        CausalOutcome.NO_SOUND_COVER,
        False,
        "NO_SOUND_COVER",
        4,
        cap.route_cap_profile_id,
        (_id("failed-obligation"),),
    )
    local = _upper(
        context,
        decision_point,
        cap,
        local_cardinality,
        RouteKind.LOCAL_ATTEMPT,
        _shared_bounds(),
        transaction=transaction,
        causal=forbidden,
    )
    fallback = _upper(
        context,
        decision_point,
        cap,
        fallback_cardinality,
        RouteKind.DIRECT_FALLBACK,
        _shared_bounds(100, 100),
    )
    result = MarginalRouteDecisionV1.select(
        decision_point, fallback, causal=forbidden, local_upper=local
    )
    assert result.selected_route is RouteSelection.FALLBACK
    assert result.comparison is RouteComparison.LOCAL_FORBIDDEN


def test_trusted_budget_replay_ignores_worker_claim_and_enforces_continuity(
    context: RouteDecisionContextV1,
    transaction: TransactionV1,
    cap: RouteCapProfileV1,
    frontier: FrontierSnapshotV1,
) -> None:
    registry, first_work = _local_work_vector(transaction.transaction_id)
    one = TrustedBudgetReplayV1.replay_work_vectors(
        (transaction,),
        (first_work,),
        cap,
        registry=registry,
        worker_claim="BUDGET_EXHAUSTED",
    )
    assert one.trusted_outcome is BudgetOutcome.BUDGET_REMAINS
    assert one.next_transaction_index == 2

    second = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        _id("decision-two"),
        2,
        _id("deeper-frontier"),
        cap.route_cap_profile_id,
    )
    _, second_work = _local_work_vector(second.transaction_id)
    two = TrustedBudgetReplayV1.replay_work_vectors(
        (transaction, second),
        (first_work, second_work),
        cap,
        registry=registry,
        worker_claim="BUDGET_REMAINS",
    )
    assert two.trusted_outcome is BudgetOutcome.BUDGET_EXHAUSTED
    assert isinstance(two.next_transaction_index, TypedNotApplicable)

    with pytest.raises(RoutingV1Error, match="start at 1"):
        TrustedBudgetReplayV1.replay_work_vectors(
            (second,),
            (second_work,),
            cap,
            registry=registry,
            worker_claim="BUDGET_REMAINS",
        )

    with pytest.raises(RoutingV1Error, match="ID-only"):
        TrustedBudgetReplayV1.replay(
            (transaction,),
            (first_work.work_vector_id,),
            cap,
            worker_claim="BUDGET_REMAINS",
        )


def test_fallback_cap_exhaustion_is_never_an_infeasibility_certificate(
    context: RouteDecisionContextV1,
) -> None:
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
        TerminalCode.FALLBACK_CAP_EXHAUSTED,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        TypedNotApplicable("failure occurred before a decision point"),
        TypedNotApplicable("no local transaction"),
        _id("actual-work"),
        (_id("fallback-cap-attestation"),),
    )
    assert terminal.terminal_class is TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
    assert len(terminal.terminal_artifact_id) == 64
    with pytest.raises(RoutingV1Error, match="class/code mismatch"):
        TerminalArtifactV1(
            "ROUTE_ATTEMPT",
            TerminalClass.INFEASIBILITY_CERTIFICATE,
            TerminalCode.FALLBACK_CAP_EXHAUSTED,
            context.route_decision_context_id,
            context.logical_occurrence_id,
            context.route_attempt_id,
            TypedNotApplicable("none"),
            TypedNotApplicable("none"),
            _id("actual-work"),
            (_id("fallback-cap-attestation"),),
        )


def _attestation(
    context: RouteDecisionContextV1,
    *,
    artifact_id: str,
    role: str,
    schema: str,
    result: str,
) -> TypedVerificationAttestationV1:
    na = TypedNotApplicable("attestation is attempt-scoped")
    return TypedVerificationAttestationV1(
        artifact_id,
        schema,
        role,
        context.route_decision_context_id,
        context.structural_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        context.build_epoch_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        na,
        na,
        _id(f"verifier-{role}"),
        _id("verification-profile"),
        result,
        _id(f"verification-work-{role}"),
        7,
    )


def test_typed_verification_attestation_binds_role_schema_outcome_and_work(
    context: RouteDecisionContextV1,
) -> None:
    artifact_id = _id("route-upper")
    upper = _attestation(
        context,
        artifact_id=artifact_id,
        role="ROUTE_UPPER",
        schema="RouteUpperBoundEnvelopeV1",
        result="VALID",
    )
    assert len(upper.verification_attestation_id) == 64
    with pytest.raises(RoutingV1Error, match="role/schema"):
        _attestation(
            context,
            artifact_id=artifact_id,
            role="ROUTE_UPPER",
            schema="WorkVectorV1",
            result="VALID",
        )
    other_role = _attestation(
        context,
        artifact_id=artifact_id,
        role="WORK_VECTOR",
        schema="WorkVectorV1",
        result="VALID",
    )
    with pytest.raises(RoutingV1Error, match="incompatible roles"):
        verify_unique_attestation_roles((upper, other_role))


def test_remaining_typed_artifacts_have_strict_canonical_round_trips(
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cap: RouteCapProfileV1,
    local_cardinality: CardinalityEvidenceV1,
    fallback_cardinality: CardinalityEvidenceV1,
    transaction: TransactionV1,
    causal: CausalEvidenceV1,
) -> None:
    local = _upper(
        context,
        decision_point,
        cap,
        local_cardinality,
        RouteKind.LOCAL_ATTEMPT,
        _shared_bounds(1, 1),
        transaction=transaction,
        causal=causal,
    )
    fallback = _upper(
        context,
        decision_point,
        cap,
        fallback_cardinality,
        RouteKind.DIRECT_FALLBACK,
        _shared_bounds(2, 1),
    )
    route_decision = MarginalRouteDecisionV1.select(
        decision_point,
        fallback,
        causal=causal,
        local_upper=local,
    )
    registry, budget_work = _local_work_vector(transaction.transaction_id)
    budget = TrustedBudgetReplayV1.replay_work_vectors(
        (transaction,),
        (budget_work,),
        cap,
        registry=registry,
        worker_claim="BUDGET_EXHAUSTED",
    )
    terminal = TerminalArtifactV1(
        "LOGICAL_OCCURRENCE",
        TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.LOCAL_GROUND_RECOVERY,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        decision_point.decision_point_id,
        transaction.transaction_id,
        _id("verified-work"),
        (_id("postaudit-attestation"),),
    )
    attestation = _attestation(
        context,
        artifact_id=local.route_upper_bound_envelope_id,
        role="ROUTE_UPPER",
        schema="RouteUpperBoundEnvelopeV1",
        result="VALID",
    )
    cases = (
        (route_decision, MarginalRouteDecisionV1.from_dict, "route_decision_id"),
        (terminal, TerminalArtifactV1.from_dict, "terminal_artifact_id"),
        (
            attestation,
            TypedVerificationAttestationV1.from_dict,
            "verification_attestation_id",
        ),
    )
    for artifact, loader, id_field in cases:
        canonical = artifact.to_dict()
        assert loader(copy.deepcopy(canonical)).to_dict() == canonical

        missing = copy.deepcopy(canonical)
        missing.pop("schema_version")
        with pytest.raises(RoutingV1Error, match="field set mismatch"):
            loader(missing)

        extra = copy.deepcopy(canonical)
        extra["undeclared"] = 1
        with pytest.raises(RoutingV1Error, match="field set mismatch"):
            loader(extra)

        tampered = copy.deepcopy(canonical)
        tampered[id_field] = "0" * 64
        with pytest.raises(RoutingV1Error, match="content ID mismatch"):
            loader(tampered)

    assert TrustedBudgetReplayV1.from_dict(
        copy.deepcopy(budget.to_dict()),
        transactions=(transaction,),
        work_vectors=(budget_work,),
        cap_profile=cap,
        registry=registry,
    ) == budget
    with pytest.raises(RoutingV1Error, match="ID-only budget document"):
        TrustedBudgetReplayV1.from_dict(copy.deepcopy(budget.to_dict()))


def test_trusted_budget_replay_consumes_actual_work_vectors_and_checks_every_mapped_cap(
    context: RouteDecisionContextV1,
    transaction: TransactionV1,
    cap: RouteCapProfileV1,
) -> None:
    registry, vector = _local_work_vector(
        transaction.transaction_id,
        **{
            "local.causal_candidate_evaluations": 32,
            "local.compiler_domain_assignments": 65536,
            "local.compiler_expanded_forms": 65536,
            "local.compiler_input_records": 262144,
            "local.materialization_ground_steps": 16,
            "local.materialization_outcome_rows": 64,
            "local.postaudit_ground_steps": 8,
            "local.postaudit_outcome_rows": 32,
            "local.solver_affine_term_evaluations": 65536,
            "local.solver_dominance_comparisons": 65536,
            "local.solver_frontier_points": 128,
            "local.solver_policy_assignments": 1024,
            "local.solver_subset_evaluations": 16,
        },
    )
    replay = TrustedBudgetReplayV1.replay_work_vectors(
        (transaction,),
        (vector,),
        cap,
        registry=registry,
        worker_claim="BUDGET_EXHAUSTED",
    )
    assert replay.verified_work_vector_ids == (vector.work_vector_id,)
    assert replay.trusted_outcome is BudgetOutcome.BUDGET_REMAINS

    _, over_cap = _local_work_vector(
        transaction.transaction_id,
        **{"local.causal_candidate_evaluations": 33},
    )
    with pytest.raises(RoutingV1Error, match="exceeds max_causal_candidate_evaluations"):
        TrustedBudgetReplayV1.replay_work_vectors(
            (transaction,),
            (over_cap,),
            cap,
            registry=registry,
            worker_claim="BUDGET_REMAINS",
        )


def test_work_vector_replay_rejects_transaction_order_substitution(
    context: RouteDecisionContextV1,
    transaction: TransactionV1,
    cap: RouteCapProfileV1,
) -> None:
    second = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        _id("decision-two-for-vector-replay"),
        2,
        _id("deeper-frontier-for-vector-replay"),
        cap.route_cap_profile_id,
    )
    registry, first_vector = _local_work_vector(transaction.transaction_id)
    _, second_vector = _local_work_vector(second.transaction_id)
    with pytest.raises(RoutingV1Error, match="order or subject binding"):
        TrustedBudgetReplayV1.replay_work_vectors(
            (transaction, second),
            (second_vector, first_vector),
            cap,
            registry=registry,
            worker_claim="BUDGET_REMAINS",
        )
