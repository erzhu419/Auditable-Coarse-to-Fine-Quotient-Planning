from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib

import pytest

from acfqp.accounting_v1 import (
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.core import Outcome, QuerySpec
from acfqp.domains.g2048 import safe_chain_fixture
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    GroundFallbackOutcome,
    GroundFallbackProtocolError,
    GroundFallbackResultV1,
    GroundFallbackV1Error,
    SEALED_ROUTE_CAP_PROFILE_KEY,
    build_ground_fallback_cardinality_evidence_v1,
    execute_authorized_ground_fallback_v1,
    require_fallback_formula_binding_v1,
    run_ground_fallback_search_v1,
)
from acfqp.phase3e_sealed_executor_v1 import (
    OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
    RuntimeFactoryCardinalityV1,
)
from acfqp.route_upper_formula_v1 import (
    RouteUpperFormulaV1Error,
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteDecisionContextV1,
    RouteKind,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import SemanticVerificationV1Error


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _cap(**overrides: int) -> GroundFallbackCapProfileV1:
    values = {
        "max_states_expanded": 1_000,
        "max_actions_evaluated": 2_000,
        "max_ground_steps": 1_000,
        "max_outcome_rows": 6_000,
        "max_bellman_backups": 200_000,
        "max_composed_candidates": 200_000,
        "max_cap_checks": 300_000,
        "max_positive_outcomes_per_step": 6,
    }
    values.update(overrides)
    return GroundFallbackCapProfileV1(**values)


def _run(kernel: object, query: object, cap: GroundFallbackCapProfileV1):
    return run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=_id("context"),
        decision_point_id=_id("decision-point"),
        route_decision_id=_id("route-decision"),
        selected_upper_id=_id("fallback-upper"),
        route_attempt_id=_id("route-attempt"),
        query_id=_id("query"),
        cap_profile=cap,
    )


def test_safe_chain_exact_fallback_is_capped_native_and_matches_j0() -> None:
    kernel, query = safe_chain_fixture()
    execution = _run(kernel, query, _cap())

    assert execution.result.outcome is GroundFallbackOutcome.FEASIBLE_CERTIFIED
    assert execution.result.search_complete is True
    assert execution.result.selected_failure_probability == Fraction(99, 5000)
    assert execution.result.selected_expected_reward == Fraction(3, 64)
    assert execution.selected_policy is not None
    assert execution.result.semantic_authority is False
    assert execution.result.authorizes_terminal_classification is False

    work = execution.work_vector
    assert work.value("fallback.states_expanded") == 20
    assert work.value("fallback.actions_evaluated") == 48
    assert work.value("fallback.ground_steps") == 48
    assert work.value("fallback.outcome_rows") == 192
    # Candidate composition is not diagnostic-only: every candidate is
    # charged on the registered nonkernel Bellman-backup leaf.
    assert work.value("fallback.bellman_backups") == 5_696
    assert work.value("fallback.bellman_backups") == (
        execution.result.composed_candidate_count
    )
    assert work.value("control.cap_rejections") == 0
    assert all(
        value == 0
        for path, value in work.values.items()
        if path.startswith("local.") or path.startswith("rebuild.")
    )
    assert GroundFallbackResultV1.from_dict(execution.result.to_dict()) == (
        execution.result
    )
    assert GroundFallbackCapProfileV1.from_dict(_cap().to_dict()) == _cap()


def test_candidate_cap_exhaustion_discards_partial_frontier_and_is_not_infeasible() -> None:
    kernel, query = safe_chain_fixture()
    execution = _run(
        kernel,
        query,
        _cap(max_composed_candidates=1, max_bellman_backups=10),
    )

    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    assert execution.result.search_complete is False
    assert execution.result.cap_exhausted_name == "max_composed_candidates"
    assert execution.result.frontier == ()
    assert execution.selected_policy is None
    assert execution.result.selected_expected_reward is None
    assert execution.result.selected_failure_probability is None
    assert execution.work_vector.value("control.cap_rejections") == 1
    assert execution.work_vector.value("route.failures") == 1
    assert execution.work_vector.value("solver.failures") == 1


@dataclass(frozen=True)
class _FailState:
    name: str


@dataclass(frozen=True)
class _OneAction:
    name: str


class _AlwaysFailKernel:
    horizon = 1
    registered_reward_features = ("reward",)
    registered_goals = ("default",)
    start = _FailState("start")
    failed = _FailState("failed")
    action = _OneAction("fail")

    def reward_upper_bound(self, horizon, raw_weights, goal):
        return Fraction(0)

    def initial_distribution(self):
        return ((Fraction(1), self.start),)

    def actions(self, state):
        return (self.action,) if state == self.start else ()

    def step(self, state, action):
        assert state == self.start and action == self.action
        return (Outcome(Fraction(1), self.failed, failure=True, terminal=True),)

    def is_terminal(self, state):
        return state == self.failed


def test_infeasibility_requires_exhaustive_completion() -> None:
    kernel = _AlwaysFailKernel()
    query = QuerySpec.from_state(
        kernel.start,
        horizon=1,
        reward_weights=(("reward", Fraction(0)),),
        goal="default",
        delta=Fraction(1, 20),
    )
    execution = _run(kernel, query, _cap())

    assert execution.result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
    assert execution.result.search_complete is True
    assert execution.result.frontier[0].failure_probability == 1
    assert execution.result.selected_policy_signature == ()
    assert execution.work_vector.value("route.successes") == 1
    assert execution.work_vector.value("solver.successes") == 1


class _TooManyRowsKernel(_AlwaysFailKernel):
    extra = _FailState("extra")

    def step(self, state, action):
        return (
            Outcome(Fraction(1, 2), self.failed, failure=True, terminal=True),
            Outcome(Fraction(1, 2), self.extra, failure=True, terminal=True),
        )


def test_preregistered_outcome_bound_violation_is_protocol_error() -> None:
    kernel = _TooManyRowsKernel()
    query = QuerySpec.from_state(
        kernel.start,
        horizon=1,
        reward_weights=(("reward", Fraction(0)),),
        goal="default",
        delta=Fraction(1, 20),
    )
    cap = GroundFallbackCapProfileV1(10, 10, 10, 10, 10, 10, 100, 1)
    with pytest.raises(GroundFallbackProtocolError, match="per_step") as caught:
        _run(kernel, query, cap)
    partial = caught.value.partial_work_vector
    assert partial is not None
    assert partial.value("fallback.ground_steps") == 1
    assert partial.value("fallback.outcome_rows") == 2
    assert partial.value("route.failures") == 1


def _fallback_route_world(cap: GroundFallbackCapProfileV1):
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    context = RouteDecisionContextV1(
        _id("pre"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id("structural"),
        _id("query"),
        _id("plan"),
        _id("threshold"),
        _id("epoch"),
        _id("occurrence"),
        _id("attempt"),
    )
    decision = DecisionPointV1(
        context.route_decision_context_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        TypedNotApplicable("direct fallback has no frontier"),
        TypedNotApplicable("direct fallback has no causal search"),
        _id("common-prefix"),
    )
    bounds = (
        ("common.protocol_checks", 5),
        ("fallback.actions_evaluated", 48),
        ("fallback.bellman_backups", 5_696),
        ("fallback.composed_candidates", 5_696),
        ("fallback.ground_steps", 48),
        ("fallback.outcome_rows", 192),
        ("fallback.states_expanded", 20),
        ("control.cap_checks", 5_812),
    )
    bound = GroundFallbackCardinalityBoundV1(
        context.route_decision_context_id,
        decision.decision_point_id,
        cap.ground_fallback_cap_profile_id,
        bounds,
        (_id("frozen-fallback-search-bound-source"),),
    )
    return registry, profile, context, decision, bound


def test_fallback_cardinality_adapter_binds_route_specific_formula_cap() -> None:
    cap = _cap()
    registry, profile, context, decision, bound = _fallback_route_world(cap)
    bound.validate_against_cap(cap)
    assert GroundFallbackCardinalityBoundV1.from_dict(bound.to_dict()) == bound
    cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=decision,
        cap_profile=cap,
        bound=bound,
    )

    assert cardinality.route_cap_profile_id == cap.route_cap_profile_id
    assert bound.ground_fallback_cardinality_bound_id in (
        cardinality.source_artifact_ids
    )
    counts = dict(cardinality.counts)
    assert counts["fallback.bellman_backups"] == 5_696
    assert counts["common.protocol_checks"] == 5
    assert counts["local.solver_policy_assignments"] == 0
    # This profile admits the complete registered search, so a tight upper
    # cannot charge a rejection that is known not to occur.
    assert counts["control.cap_rejections"] == 0

    # Direct fallback has no implicit/local-cap default.  The formula must bind
    # this exact independent finite cap profile.
    with pytest.raises(RouteUpperFormulaV1Error, match="explicit finite"):
        official_route_upper_formula_v1(
            RouteKind.DIRECT_FALLBACK,
            registry=registry,
            profile=profile,
        )
    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=cap,
    )
    require_fallback_formula_binding_v1(formula, cap)
    assert formula.route_cap_profile_id == cap.route_cap_profile_id
    envelope, proof = derive_route_upper_v1(
        context=context,
        decision_point=decision,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=profile,
        formula=formula,
    )
    assert envelope.route_cap_profile_id == cap.route_cap_profile_id
    assert dict(proof.leaf_upper_bounds)["fallback.bellman_backups"] == 5_696
    assert dict(proof.leaf_upper_bounds)["control.cap_checks"] == 5_812


def test_sealed_fallback_runtime_cap_checks_are_in_exact_cardinality_chain() -> None:
    cap = replace(
        _cap(max_cap_checks=5_815),
        reserved_route_cap_checks=3,
        profile_key=SEALED_ROUTE_CAP_PROFILE_KEY,
    )
    registry, profile, context, decision, historical_bound = (
        _fallback_route_world(cap)
    )
    runtime = RuntimeFactoryCardinalityV1(
        _id("sealed-runtime-tree"),
        OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE.runtime_manifest_cap_profile_id,
        file_count=2,
        total_bytes=123,
        manifest_document_bytes=456,
    )
    sealed_bound = replace(
        historical_bound,
        source_artifact_ids=tuple(
            sorted(
                historical_bound.source_artifact_ids
                + (runtime.runtime_factory_cardinality_id,)
            )
        ),
        runtime_factory_cardinality=runtime,
    )

    historical_counts = dict(
        historical_bound.operational_count_values(registry)
    )
    sealed_counts = dict(sealed_bound.operational_count_values(registry))
    sealed_uppers = dict(sealed_bound.operational_upper_values(cap, registry))
    assert dict(runtime.upper_values())["control.cap_checks"] == 3
    assert sealed_counts["control.cap_checks"] == (
        historical_counts["control.cap_checks"] + 3
    )
    # The cap formula consumes the same exact cardinality; the factory checks
    # must not be appended a second time at the upper-envelope layer.
    assert sealed_uppers["control.cap_checks"] == sealed_counts[
        "control.cap_checks"
    ]

    cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=decision,
        cap_profile=cap,
        bound=sealed_bound,
    )
    assert dict(cardinality.counts)["control.cap_checks"] == 5_815
    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=cap,
    )
    _, proof = derive_route_upper_v1(
        context=context,
        decision_point=decision,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=profile,
        formula=formula,
    )
    assert dict(proof.leaf_upper_bounds)["control.cap_checks"] == 5_815

    # A route-wide cap of 5,812 reserves the same three factory checks and
    # leaves only 5,809 for the solver.  The complete 5,812-check solver is
    # therefore preregistered to close CAP_EXHAUSTED; it cannot be presented
    # as a successful 5,815-check execution within a 5,812 upper.
    tight_cap = replace(cap, max_cap_checks=5_812)
    tight_bound = replace(
        sealed_bound,
        ground_fallback_cap_profile_id=(
            tight_cap.ground_fallback_cap_profile_id
        ),
    )
    assert tight_cap.max_solver_cap_checks == 5_809
    assert tight_bound.cap_rejection_upper(tight_cap) == 1
    tight_cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=decision,
        cap_profile=tight_cap,
        bound=tight_bound,
    )
    assert dict(tight_cardinality.counts)["control.cap_checks"] == 5_815
    assert dict(tight_cardinality.counts)["control.cap_rejections"] == 1
    tight_formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=tight_cap,
    )
    _, tight_proof = derive_route_upper_v1(
        context=context,
        decision_point=decision,
        cardinality=tight_cardinality,
        cap_profile=tight_cap,
        registry=registry,
        profile=profile,
        formula=tight_formula,
    )
    assert dict(tight_proof.leaf_upper_bounds)["control.cap_checks"] == 5_812


def test_unsealed_fallback_cap_payload_and_identity_remain_legacy_v1() -> None:
    cap = _cap(max_cap_checks=5_812)
    document = cap.to_dict()
    assert document["schema"] == "acfqp.ground_fallback_cap_profile.v1"
    assert "reserved_route_cap_checks" not in document
    assert "max_solver_cap_checks" not in document
    assert GroundFallbackCapProfileV1.from_dict(document) == cap


def test_candidate_upper_cannot_disappear_below_registered_backup_upper() -> None:
    cap = _cap()
    _, _, context, decision, bound = _fallback_route_world(cap)
    bad_values = dict(bound.bounds)
    bad_values["fallback.bellman_backups"] = 5_695
    bad = GroundFallbackCardinalityBoundV1(
        context.route_decision_context_id,
        decision.decision_point_id,
        cap.ground_fallback_cap_profile_id,
        tuple((name, bad_values[name]) for name, _ in bound.bounds),
        bound.source_artifact_ids,
    )
    with pytest.raises(GroundFallbackV1Error, match="composed candidate"):
        bad.validate_against_cap(cap)


class _StepCountingKernel:
    def __init__(self, inner):
        self.inner = inner
        self.step_calls = 0

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def step(self, state, action):
        self.step_calls += 1
        return self.inner.step(state, action)


def test_production_executor_rejects_missing_semantic_authority_before_kernel_access() -> None:
    raw_kernel, query = safe_chain_fixture()
    kernel = _StepCountingKernel(raw_kernel)
    with pytest.raises(SemanticVerificationV1Error, match="semantic replay"):
        execute_authorized_ground_fallback_v1(
            kernel,
            query,
            context=object(),
            decision_point=object(),
            fallback_upper=object(),
            cardinality=object(),
            cardinality_bound=object(),
            cap_profile=_cap(),
            route_decision_result=object(),
            fallback_upper_result=object(),
            cardinality_result=object(),
        )
    assert kernel.step_calls == 0
