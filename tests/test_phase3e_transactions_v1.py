from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    SHARED_AXES,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
import acfqp.phase3e_local_semantics_v1 as local_semantics
from acfqp.phase3e_local_semantics_v1 import (
    FrozenThresholdProfileV1,
    LocalSolverOutcome,
    LocalTransactionResultV1,
    PostAuditCertificateV1,
    PostAuditOutcome,
)
from acfqp.phase3e_transactions_v1 import (
    Phase3ETransactionV1Error,
    authorize_second_transaction_v1,
    fallback_after_local_cap_exhaustion_v1,
    prepare_second_transaction_candidate_v1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    FrontierSnapshotV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteUpperBoundEnvelopeV1,
    TIGHT_PREEXECUTION_UPPER,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationV1Error,
    semantic_verifier_spec_v1,
    verify_local_transaction_result_semantics_v1,
    verify_post_audit_semantics_v1,
    verify_work_vector_semantics_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _context(plan: str, registry, profile) -> RouteDecisionContextV1:
    threshold = FrozenThresholdProfileV1(
        _id("query"), Fraction(1, 20), Fraction(1, 20)
    )
    return RouteDecisionContextV1(
        _id("pre"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id("structural"),
        _id("query"),
        _id(plan),
        threshold.threshold_profile_id,
        _id("epoch"),
        _id("occurrence"),
        _id("attempt"),
    )


def _local_work(registry, transaction: TransactionV1, *, cap_rejections: int = 0):
    values = {path: 0 for path in registry.required_paths}
    values.update(
        {
            "local.causal_candidate_evaluations": 1,
            "control.cap_checks": 1,
            "control.cap_rejections": cap_rejections,
            "route.attempts": 1,
            "route.successes": 0,
            "route.failures": 1,
            "solver.attempts": 1,
            "solver.successes": 0 if cap_rejections else 1,
            "solver.failures": 1 if cap_rejections else 0,
        }
    )
    return registry.materialize(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=explicit_records_v1(
            registry,
            values,
            recorder_id="phase3e_second_transaction_test_recorder",
        ),
    )


def _cardinality(context, route, cap_id, frontier, label):
    return CardinalityEvidenceV1(
        context.route_decision_context_id,
        route,
        cap_id,
        (
            frontier.frontier_snapshot_id
            if route is RouteKind.LOCAL_ATTEMPT
            else TypedNotApplicable("fallback is attempt-scoped")
        ),
        (("registered.bound", 1),),
        (_id(f"cardinality-source-{label}"),),
    )


def _upper(
    *,
    context,
    decision,
    cardinality,
    route,
    bound,
    transaction=None,
    causal=None,
    label,
):
    local = route is RouteKind.LOCAL_ATTEMPT
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
        decision.decision_point_id,
        transaction.transaction_id if local else TypedNotApplicable("fallback"),
        transaction.transaction_index if local else TypedNotApplicable("fallback"),
        (
            transaction.frontier_snapshot_id
            if local
            else TypedNotApplicable("fallback")
        ),
        causal.causal_evidence_id if local else TypedNotApplicable("fallback"),
        cardinality.route_cap_profile_id,
        cardinality.cardinality_evidence_id,
        _id(f"formula-{label}"),
        route,
        TIGHT_PREEXECUTION_UPPER,
        tuple((axis, bound) for axis in SHARED_AXES),
    )


def _world(*, cap_rejections: int = 0):
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    cap = RouteCapProfileV1()
    first_context = _context("first-abstract-plan", registry, profile)
    first_frontier = FrontierSnapshotV1(
        first_context.route_decision_context_id,
        1,
        (_id("first-obligation"),),
    )
    first_causal = CausalEvidenceV1(
        first_frontier.frontier_snapshot_id,
        CausalOutcome.FOUND,
        True,
        None,
        1,
        cap.route_cap_profile_id,
        (_id("first-obligation"),),
    )
    first_decision = DecisionPointV1(
        first_context.route_decision_context_id,
        1,
        first_frontier.frontier_snapshot_id,
        first_causal.causal_evidence_id,
        _id("first-common-prefix-work"),
    )
    first_transaction = TransactionV1(
        first_context.logical_occurrence_id,
        first_context.route_attempt_id,
        first_decision.decision_point_id,
        1,
        first_frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    first_work = _local_work(
        registry, first_transaction, cap_rejections=cap_rejections
    )

    first_local_upper_id = _id("first-local-upper")
    first_fallback_upper_id = _id("first-fallback-upper")
    stitched_plan_id = _id("stitched-plan-after-failed-postaudit")
    first_local_result = LocalTransactionResultV1(
        first_context.route_decision_context_id,
        first_decision.decision_point_id,
        first_transaction.transaction_id,
        first_context.route_attempt_id,
        first_context.query_id,
        first_context.selected_plan_id,
        cap.route_cap_profile_id,
        first_local_upper_id,
        first_work.work_vector_id,
        _id("first-capability"),
        _id("first-worker-result"),
        _id("first-runtime-attestation"),
        _id("first-overlay"),
        stitched_plan_id,
        LocalSolverOutcome.CANDIDATE_FOUND,
        True,
        None,
    )
    threshold = FrozenThresholdProfileV1(
        first_context.query_id, Fraction(1, 20), Fraction(1, 20)
    )
    failed_post_audit = PostAuditCertificateV1(
        first_context.route_decision_context_id,
        first_decision.decision_point_id,
        first_transaction.transaction_id,
        first_context.route_attempt_id,
        first_context.query_id,
        first_context.selected_plan_id,
        first_context.threshold_profile_id,
        first_local_result.local_transaction_result_id,
        first_work.work_vector_id,
        first_local_result.candidate_overlay_binding_id,
        stitched_plan_id,
        _id("failed-postaudit-issues"),
        PostAuditOutcome.FAILED,
        Fraction(0),
        Fraction(1, 10),
        Fraction(1, 10),
        0,
        0,
    )
    first_execution = local_semantics._seal_trusted_execution_v1(
        local_result=first_local_result,
        post_audit=failed_post_audit,
        work_vector=first_work,
        threshold_profile=threshold,
    )

    second_context = _context("stitched-plan-after-failed-postaudit", registry, profile)
    second_frontier = FrontierSnapshotV1(
        second_context.route_decision_context_id,
        2,
        (_id("second-deeper-obligation"),),
    )
    second_causal = CausalEvidenceV1(
        second_frontier.frontier_snapshot_id,
        CausalOutcome.FOUND,
        True,
        None,
        1,
        cap.route_cap_profile_id,
        (_id("second-deeper-obligation"),),
    )
    prefix_recorder = NativeCounterRecorderV1(
        subject_id=second_context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-second-common-prefix-test-v1",
    )
    prefix_recorder.add("common.abstract_audit_obligations", 1)
    second_common_prefix_work = prefix_recorder.seal()
    second_decision = DecisionPointV1(
        second_context.route_decision_context_id,
        2,
        second_frontier.frontier_snapshot_id,
        second_causal.causal_evidence_id,
        second_common_prefix_work.work_vector.work_vector_id,
    )
    second_transaction = TransactionV1(
        second_context.logical_occurrence_id,
        second_context.route_attempt_id,
        second_decision.decision_point_id,
        2,
        second_frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    local_cardinality = _cardinality(
        second_context,
        RouteKind.LOCAL_ATTEMPT,
        cap.route_cap_profile_id,
        second_frontier,
        "second-local",
    )
    fallback_cardinality = _cardinality(
        second_context,
        RouteKind.DIRECT_FALLBACK,
        _id("independent-fallback-cap"),
        second_frontier,
        "second-fallback",
    )
    local_upper = _upper(
        context=second_context,
        decision=second_decision,
        cardinality=local_cardinality,
        route=RouteKind.LOCAL_ATTEMPT,
        bound=1,
        transaction=second_transaction,
        causal=second_causal,
        label="second-local",
    )
    fallback_upper = _upper(
        context=second_context,
        decision=second_decision,
        cardinality=fallback_cardinality,
        route=RouteKind.DIRECT_FALLBACK,
        bound=2,
        label="second-fallback",
    )
    route_decision = MarginalRouteDecisionV1.select(
        second_decision,
        fallback_upper,
        causal=second_causal,
        local_upper=local_upper,
    )
    return {
        "registry": registry,
        "cap": cap,
        "first_context": first_context,
        "first_frontier": first_frontier,
        "first_causal": first_causal,
        "first_decision_point": first_decision,
        "first_transaction": first_transaction,
        "first_local_work": first_work,
        "first_local_upper_id": first_local_upper_id,
        "first_fallback_upper_id": first_fallback_upper_id,
        "first_local_result_artifact_id": (
            first_local_result.local_transaction_result_id
        ),
        "failed_post_audit_artifact_id": (
            failed_post_audit.post_audit_certificate_id
        ),
        "new_stitched_plan_binding_id": stitched_plan_id,
        "second_context": second_context,
        "second_frontier": second_frontier,
        "second_causal": second_causal,
        "second_decision_point": second_decision,
        "second_transaction": second_transaction,
        "second_local_cardinality": local_cardinality,
        "second_fallback_cardinality": fallback_cardinality,
        "second_local_upper": local_upper,
        "second_fallback_upper": fallback_upper,
        "second_route_decision": route_decision,
        "second_common_prefix_work": second_common_prefix_work,
        "first_execution": first_execution,
    }


def _prepare(world):
    arguments = dict(world)
    registry = arguments.pop("registry")
    cap = arguments.pop("cap")
    arguments.pop("first_execution", None)
    return prepare_second_transaction_candidate_v1(
        **arguments,
        cap_profile=cap,
        registry=registry,
    )


def _verification_record(role: SemanticRole, registry) -> CounterRecordV1:
    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).verification_counter_path,
        1,
        recorder_id=f"phase3e-second-transaction-{role.value.lower()}-v1",
    )


def _first_authorities(world):
    binding = AttestationContextV1(
        world["first_context"],
        world["first_decision_point"].decision_point_id,
        world["first_transaction"].transaction_id,
        30,
    )
    work = verify_work_vector_semantics_v1(
        world["first_local_work"],
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.WORK_VECTOR, world["registry"]
        ),
        registry=world["registry"],
    )
    local = verify_local_transaction_result_semantics_v1(
        world["first_execution"],
        context=world["first_context"],
        decision_point=world["first_decision_point"],
        transaction=world["first_transaction"],
        cap_profile=world["cap"],
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.LOCAL_SOLVER_RESULT, world["registry"]
        ),
        registry=world["registry"],
    )
    post = verify_post_audit_semantics_v1(
        world["first_execution"],
        local_solver_result=local,
        context=world["first_context"],
        decision_point=world["first_decision_point"],
        transaction=world["first_transaction"],
        cap_profile=world["cap"],
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.POST_AUDIT, world["registry"]
        ),
        registry=world["registry"],
    )
    return work, local, post


def test_second_transaction_candidate_requires_fresh_deeper_identity_chain() -> None:
    world = _world()
    candidate = _prepare(world)

    assert candidate.execution_authorized is False
    assert candidate.second_transaction.transaction_index == 2
    assert candidate.second_frontier.frontier_stage == 2
    assert candidate.first_frontier.frontier_stage == 1
    assert candidate.budget_replay.next_transaction_index == 2
    assert candidate.preserved_first_local_work_id == (
        world["first_local_work"].work_vector_id
    )
    assert candidate.second_route_decision.selected_route.value == "LOCAL"

    with pytest.raises(Phase3ETransactionV1Error, match="structural replay"):
        replace(candidate, _validation_authority=None)


def test_same_or_shallower_frontier_is_rejected() -> None:
    world = _world()
    shallow = FrontierSnapshotV1(
        world["second_context"].route_decision_context_id,
        1,
        (_id("different-but-not-deeper"),),
    )
    world["second_frontier"] = shallow
    with pytest.raises(Phase3ETransactionV1Error, match="strictly deeper"):
        _prepare(world)


def test_reused_old_upper_identity_is_rejected() -> None:
    world = _world()
    world["first_local_upper_id"] = (
        world["second_local_upper"].route_upper_bound_envelope_id
    )
    with pytest.raises(Phase3ETransactionV1Error, match="reused"):
        _prepare(world)


def test_second_common_prefix_must_be_replayable_recorded_work() -> None:
    world = _world()
    world["second_common_prefix_work"] = object()
    with pytest.raises(Phase3ETransactionV1Error, match="RecordedWork"):
        _prepare(world)

    world = _world()
    world["second_decision_point"] = replace(
        world["second_decision_point"],
        common_prefix_work_id=_id("uncharged-second-prefix-claim"),
    )
    with pytest.raises(Phase3ETransactionV1Error, match="common-prefix work"):
        _prepare(world)


def test_second_context_must_bind_explicit_new_stitched_plan() -> None:
    world = _world()
    world["new_stitched_plan_binding_id"] = _id("unrelated-stitched-plan")
    with pytest.raises(Phase3ETransactionV1Error, match="explicitly supplied"):
        _prepare(world)


def test_cap_exhausted_first_local_cannot_open_second_transaction() -> None:
    world = _world(cap_rejections=1)
    with pytest.raises(Phase3ETransactionV1Error, match="route directly to fallback"):
        _prepare(world)


def test_third_transaction_shape_is_rejected_by_first_index_rule() -> None:
    world = _world()
    world["first_transaction"] = replace(
        world["first_transaction"], transaction_index=2
    )
    with pytest.raises(Phase3ETransactionV1Error, match="transaction 1"):
        _prepare(world)


def test_missing_postaudit_and_route_authority_fails_closed() -> None:
    world = _world()
    candidate = _prepare(world)
    with pytest.raises(SemanticVerificationV1Error, match="semantic replay"):
        authorize_second_transaction_v1(
            candidate,
            first_local_work_result=object(),
            first_local_solver_result=object(),
            post_audit_failure_result=object(),
            causal_result=object(),
            local_cardinality_result=object(),
            fallback_cardinality_result=object(),
            local_upper_result=object(),
            fallback_upper_result=object(),
            route_decision_result=object(),
        )


def test_first_plan_work_and_failed_postaudit_authorities_bind_transaction_one() -> None:
    world = _world()
    candidate = _prepare(world)
    work, local, post = _first_authorities(world)

    # Correct first-context evidence passes the strengthened transaction-one
    # gate and then fails closed at the deliberately absent transaction-two
    # causal authority.
    with pytest.raises(SemanticVerificationV1Error, match="semantic replay"):
        authorize_second_transaction_v1(
            candidate,
            first_local_work_result=work,
            first_local_solver_result=local,
            post_audit_failure_result=post,
            causal_result=object(),
            local_cardinality_result=object(),
            fallback_cardinality_result=object(),
            local_upper_result=object(),
            fallback_upper_result=object(),
            route_decision_result=object(),
        )


def test_first_work_authority_must_name_exact_postaudit_work_vector() -> None:
    world = _world()
    candidate = _prepare(world)
    _work, local, post = _first_authorities(world)
    values = dict(world["first_local_work"].values)
    values["local.causal_candidate_evaluations"] += 1
    other_vector = world["registry"].materialize(
        subject_id=world["first_transaction"].transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=explicit_records_v1(
            world["registry"],
            values,
            recorder_id="phase3e-wrong-first-work-authority-v1",
        ),
    )
    binding = AttestationContextV1(
        world["first_context"],
        world["first_decision_point"].decision_point_id,
        world["first_transaction"].transaction_id,
        31,
    )
    wrong_work = verify_work_vector_semantics_v1(
        other_vector,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.WORK_VECTOR, world["registry"]
        ),
        registry=world["registry"],
    )
    with pytest.raises(Phase3ETransactionV1Error, match="exact WORK_VECTOR"):
        authorize_second_transaction_v1(
            candidate,
            first_local_work_result=wrong_work,
            first_local_solver_result=local,
            post_audit_failure_result=post,
            causal_result=object(),
            local_cardinality_result=object(),
            fallback_cardinality_result=object(),
            local_upper_result=object(),
            fallback_upper_result=object(),
            route_decision_result=object(),
        )


def test_cap_exhaustion_string_without_semantic_authority_cannot_route() -> None:
    world = _world(cap_rejections=1)
    with pytest.raises(SemanticVerificationV1Error, match="semantic replay"):
        fallback_after_local_cap_exhaustion_v1(
            transaction=world["first_transaction"],
            local_work=world["first_local_work"],
            cap_profile=world["cap"],
            local_solver_result="SEARCH_CAP_EXHAUSTED",
            registry=world["registry"],
        )
