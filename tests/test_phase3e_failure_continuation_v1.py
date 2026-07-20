from __future__ import annotations

from dataclasses import replace
import hashlib
from types import SimpleNamespace

import pytest

from acfqp.accounting_v1 import (
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
from acfqp.phase3e_failure_continuation_v1 import (
    AuthorizedFallbackAfterLocalFailureV1,
    LocalFailureKind,
    Phase3EFailureContinuationV1Error,
    authorize_fallback_after_local_failure_v1,
    prepare_fallback_after_local_failure_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    build_ground_fallback_cardinality_evidence_v1,
)
from acfqp.phase3e_transactions_v1 import (
    Phase3ETransactionV1Error,
    fallback_after_local_cap_exhaustion_v1,
    fallback_after_second_post_audit_failure_v1,
)
from acfqp.route_upper_formula_v1 import (
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    BudgetOutcome,
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import SemanticVerificationV1Error


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _local_work(registry, transaction: TransactionV1, *, rejected: bool = False):
    values = {path: 0 for path in registry.required_paths}
    values.update(
        {
            "local.causal_candidate_evaluations": 1,
            "control.cap_checks": 1,
            "control.cap_rejections": 1 if rejected else 0,
            "route.attempts": 1,
            "route.successes": 0 if rejected else 1,
            "route.failures": 1 if rejected else 0,
            "solver.attempts": 1,
            "solver.successes": 0 if rejected else 1,
            "solver.failures": 1 if rejected else 0,
        }
    )
    return registry.materialize(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=explicit_records_v1(
            registry,
            values,
            recorder_id="phase3e-fresh-fallback-local-work-test-v1",
        ),
    )


def _world(*, transaction_count: int = 2, rejected_last: bool = False):
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    local_cap = RouteCapProfileV1()
    context = RouteDecisionContextV1(
        _id("pre"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id("structural"),
        _id("query"),
        _id("failed-stitched-plan"),
        _id("threshold"),
        _id("epoch"),
        _id("occurrence"),
        _id("attempt"),
    )
    transactions = tuple(
        TransactionV1(
            context.logical_occurrence_id,
            context.route_attempt_id,
            _id(f"local-decision-{index}"),
            index,
            _id(f"local-frontier-{index}"),
            local_cap.route_cap_profile_id,
        )
        for index in range(1, transaction_count + 1)
    )
    work = tuple(
        _local_work(
            registry,
            transaction,
            rejected=rejected_last and index == transaction_count,
        )
        for index, transaction in enumerate(transactions, start=1)
    )

    prefix_recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
    )
    prefix_recorder.add("common.protocol_checks", 3)
    prefix = prefix_recorder.seal()
    fallback_point = DecisionPointV1(
        context.route_decision_context_id,
        TypedNotApplicable("failed local transaction is already closed"),
        TypedNotApplicable("direct fallback has no local frontier"),
        TypedNotApplicable("local is forbidden after this failure"),
        prefix.work_vector.work_vector_id,
    )
    fallback_cap = GroundFallbackCapProfileV1(
        100,
        100,
        100,
        400,
        100,
        100,
        1_000,
        4,
    )
    bound = GroundFallbackCardinalityBoundV1(
        context.route_decision_context_id,
        fallback_point.decision_point_id,
        fallback_cap.ground_fallback_cap_profile_id,
        (
            ("common.protocol_checks", 5),
            ("fallback.actions_evaluated", 2),
            ("fallback.bellman_backups", 4),
            ("fallback.composed_candidates", 4),
            ("fallback.ground_steps", 2),
            ("fallback.outcome_rows", 4),
            ("fallback.states_expanded", 2),
            ("control.cap_checks", 10),
        ),
        (_id("fresh-fallback-cardinality-parent"),),
    )
    cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=fallback_point,
        cap_profile=fallback_cap,
        bound=bound,
    )
    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=fallback_cap,
    )
    upper, _ = derive_route_upper_v1(
        context=context,
        decision_point=fallback_point,
        cardinality=cardinality,
        cap_profile=fallback_cap,
        registry=registry,
        profile=profile,
        formula=formula,
    )
    decision = MarginalRouteDecisionV1.select(
        fallback_point,
        upper,
        causal=None,
        local_upper=None,
    )
    arguments = {
        "context": context,
        "failure_kind": (
            LocalFailureKind.LOCAL_SEARCH_CAP_EXHAUSTED
            if rejected_last
            else LocalFailureKind.POST_AUDIT_FAILED
        ),
        "failure_artifact_id": _id("local-failure-artifact"),
        "transactions": transactions,
        "prior_local_work_vectors": work,
        "local_cap_profile": local_cap,
        "prior_route_upper_ids": tuple(
            _id(f"old-route-upper-{index}")
            for index in range(1, transaction_count + 2)
        ),
        "fallback_common_prefix_work": prefix,
        "fallback_decision_point": fallback_point,
        "fallback_cap_profile": fallback_cap,
        "fallback_cardinality_bound": bound,
        "fallback_cardinality": cardinality,
        "fallback_upper": upper,
        "fallback_route_decision": decision,
        "prior_fallback_cardinality_bound_ids": (
            _id("old-fallback-bound"),
        ),
        "registry": registry,
        "comparison_profile": profile,
    }
    return arguments


def test_transaction_two_failure_prepares_only_a_fresh_fallback_chain() -> None:
    arguments = _world(transaction_count=2)
    candidate = prepare_fallback_after_local_failure_v1(**arguments)

    assert candidate.execution_authorized is False
    assert candidate.infeasibility_certified is False
    assert candidate.budget_replay.trusted_outcome is BudgetOutcome.BUDGET_EXHAUSTED
    assert candidate.fallback_route_decision.selected_route is RouteSelection.FALLBACK
    assert candidate.fallback_decision_point.decision_point_id not in {
        row.decision_point_id for row in candidate.transactions
    }
    assert candidate.fallback_upper.route_upper_bound_envelope_id not in set(
        candidate.prior_route_upper_ids
    )
    assert candidate.fallback_cardinality_bound.ground_fallback_cardinality_bound_id not in set(
        candidate.prior_fallback_cardinality_bound_ids
    )
    assert candidate.preserved_local_work_vector_ids == tuple(
        row.work_vector_id for row in arguments["prior_local_work_vectors"]
    )


def test_stale_route_upper_is_rejected_even_when_all_numbers_match() -> None:
    arguments = _world(transaction_count=2)
    fresh_upper_id = arguments["fallback_upper"].route_upper_bound_envelope_id
    arguments["prior_route_upper_ids"] = (
        *arguments["prior_route_upper_ids"],
        fresh_upper_id,
    )
    with pytest.raises(
        Phase3EFailureContinuationV1Error, match="stale route upper"
    ):
        prepare_fallback_after_local_failure_v1(**arguments)


def test_stale_cardinality_bound_is_rejected_for_new_decision() -> None:
    arguments = _world(transaction_count=1)
    fresh_bound_id = (
        arguments[
            "fallback_cardinality_bound"
        ].ground_fallback_cardinality_bound_id
    )
    arguments["prior_fallback_cardinality_bound_ids"] = (fresh_bound_id,)
    with pytest.raises(
        Phase3EFailureContinuationV1Error, match="old cardinality-bound"
    ):
        prepare_fallback_after_local_failure_v1(**arguments)


def test_cap_exhaustion_prepares_fallback_but_never_infeasibility() -> None:
    arguments = _world(transaction_count=1, rejected_last=True)
    candidate = prepare_fallback_after_local_failure_v1(**arguments)

    assert candidate.failure_kind is LocalFailureKind.LOCAL_SEARCH_CAP_EXHAUSTED
    assert candidate.budget_replay.trusted_outcome is BudgetOutcome.BUDGET_REMAINS
    assert candidate.fallback_route_decision.selected_route is RouteSelection.FALLBACK
    assert candidate.infeasibility_certified is False
    assert candidate.execution_authorized is False


def test_missing_failure_and_route_authority_cannot_cross_execution_boundary() -> None:
    candidate = prepare_fallback_after_local_failure_v1(
        **_world(transaction_count=2)
    )
    with pytest.raises(SemanticVerificationV1Error, match="semantic replay"):
        authorize_fallback_after_local_failure_v1(
            candidate,
            failure_result=object(),
            prior_work_results=(object(), object()),
            common_prefix_work_result=object(),
            cardinality_result=object(),
            fallback_upper_result=object(),
            route_decision_result=object(),
        )
    with pytest.raises(
        Phase3EFailureContinuationV1Error, match="lacks semantic authority"
    ):
        AuthorizedFallbackAfterLocalFailureV1(
            candidate,
            object(),
            (object(), object()),
            object(),
            object(),
            object(),
            object(),
        )


def test_third_local_transaction_cannot_be_smuggled_into_fallback_preparation() -> None:
    arguments = _world(transaction_count=2)
    # TransactionV1 itself rejects index 3.  Repeating a shape here exercises
    # the continuation boundary's independent cardinality check as well.
    third = arguments["transactions"][-1]
    arguments["transactions"] = (*arguments["transactions"], third)
    arguments["prior_local_work_vectors"] = (
        *arguments["prior_local_work_vectors"],
        arguments["prior_local_work_vectors"][-1],
    )
    with pytest.raises(
        Phase3EFailureContinuationV1Error, match="one or two completed"
    ):
        prepare_fallback_after_local_failure_v1(**arguments)


def test_replacing_fresh_common_prefix_invalidates_the_decision_binding() -> None:
    arguments = _world(transaction_count=1)
    foreign = replace(
        arguments["fallback_decision_point"],
        common_prefix_work_id=_id("foreign-common-prefix"),
    )
    arguments["fallback_decision_point"] = foreign
    with pytest.raises(
        Phase3EFailureContinuationV1Error, match="common-prefix WorkVector"
    ):
        prepare_fallback_after_local_failure_v1(**arguments)


def test_legacy_cap_exhaustion_helper_cannot_skip_the_fresh_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = _world(transaction_count=1, rejected_last=True)
    semantic_result = SimpleNamespace(
        outcome="SEARCH_CAP_EXHAUSTED",
        binding=SimpleNamespace(
            transaction_id=arguments["transactions"][0].transaction_id
        ),
    )
    monkeypatch.setattr(
        "acfqp.semantic_verification_v1.require_semantic_verification_result_v1",
        lambda result, _role: result,
    )
    with pytest.raises(
        Phase3ETransactionV1Error, match="fresh fallback decision point"
    ):
        fallback_after_local_cap_exhaustion_v1(
            transaction=arguments["transactions"][0],
            local_work=arguments["prior_local_work_vectors"][0],
            cap_profile=arguments["local_cap_profile"],
            local_solver_result=semantic_result,
            registry=arguments["registry"],
        )


def test_legacy_transaction_two_failure_helper_cannot_reuse_old_upper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = _world(transaction_count=2)
    semantic_result = SimpleNamespace(
        outcome="FAILED",
        binding=SimpleNamespace(
            transaction_id=arguments["transactions"][1].transaction_id
        ),
    )
    monkeypatch.setattr(
        "acfqp.semantic_verification_v1.require_semantic_verification_result_v1",
        lambda result, _role: result,
    )
    with pytest.raises(
        Phase3ETransactionV1Error, match="fresh fallback decision point"
    ):
        fallback_after_second_post_audit_failure_v1(
            transactions=arguments["transactions"],
            local_work_vectors=arguments["prior_local_work_vectors"],
            cap_profile=arguments["local_cap_profile"],
            post_audit_failure_result=semantic_result,
            registry=arguments["registry"],
        )
