from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from fractions import Fraction
import hashlib

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.core import Outcome, QuerySpec
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
    GroundFallbackResultV1,
    _seal_trusted_ground_fallback_execution_v1,
    run_ground_fallback_search_v1,
)
from acfqp.routing_v1 import RouteDecisionContextV1, TypedNotApplicable
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationV1Error,
    semantic_verifier_spec_v1,
    verify_ground_fallback_semantics_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _State:
    name: str


class _OneStepKernel:
    horizon = 1
    registered_reward_features = ("reward",)
    registered_goals = ("default",)

    def __init__(self, *, fails: bool) -> None:
        self.fails = fails
        self.start = _State("start")
        self.end = _State("failure" if fails else "terminal")
        self.action = "advance"

    def reward_upper_bound(self, horizon, raw_weights, goal):
        return Fraction(horizon * raw_weights.get("reward", 0))

    def initial_distribution(self):
        return ((Fraction(1), self.start),)

    def actions(self, state):
        return (self.action,) if state == self.start else ()

    def step(self, state, action):
        assert state == self.start and action == self.action
        return (
            Outcome(
                Fraction(1),
                self.end,
                (("reward", Fraction(1)),),
                failure=self.fails,
                terminal=True,
            ),
        )

    def is_terminal(self, state):
        return state == self.end


def _cap(**overrides: int) -> GroundFallbackCapProfileV1:
    values = {
        "max_states_expanded": 10,
        "max_actions_evaluated": 10,
        "max_ground_steps": 10,
        "max_outcome_rows": 10,
        "max_bellman_backups": 10,
        "max_composed_candidates": 10,
        "max_cap_checks": 100,
        "max_positive_outcomes_per_step": 1,
    }
    values.update(overrides)
    return GroundFallbackCapProfileV1(**values)


def _context(label: str = "semantic-fallback") -> RouteDecisionContextV1:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    return RouteDecisionContextV1(
        _id(f"{label}:pre"),
        _id(f"{label}:protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id(f"{label}:structural"),
        _id(f"{label}:query"),
        _id(f"{label}:plan"),
        _id(f"{label}:threshold"),
        _id(f"{label}:epoch"),
        _id(f"{label}:occurrence"),
        _id(f"{label}:attempt"),
    )


def _verification_record() -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(SemanticRole.GROUND_FALLBACK)
    return CounterRecordV1.observe(
        registry,
        spec.verification_counter_path,
        1,
        recorder_id="trusted-ground-fallback-semantic-verifier-test-v1",
    )


def _raw_execution(
    *, fails: bool, cap: GroundFallbackCapProfileV1 | None = None
) -> tuple[
    GroundFallbackExecutionV1,
    GroundFallbackCapProfileV1,
    RouteDecisionContextV1,
    str,
]:
    selected_cap = cap or _cap()
    context = _context("infeasible" if fails else "feasible")
    point_id = _id("infeasible:point" if fails else "feasible:point")
    kernel = _OneStepKernel(fails=fails)
    query = QuerySpec.from_state(
        kernel.start,
        horizon=1,
        reward_weights=(("reward", Fraction(1)),),
        delta=Fraction(1, 20),
    )
    execution = run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=context.route_decision_context_id,
        decision_point_id=point_id,
        route_decision_id=_id(f"{point_id}:decision"),
        selected_upper_id=_id(f"{point_id}:upper"),
        route_attempt_id=context.route_attempt_id,
        query_id=context.query_id,
        cap_profile=selected_cap,
    )
    return execution, selected_cap, context, point_id


def _binding(context: RouteDecisionContextV1, point_id: str) -> AttestationContextV1:
    return AttestationContextV1(
        context,
        point_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        20,
    )


def _verify(
    execution: GroundFallbackExecutionV1,
    cap: GroundFallbackCapProfileV1,
    context: RouteDecisionContextV1,
    point_id: str,
):
    return verify_ground_fallback_semantics_v1(
        execution,
        cap_profile=cap,
        binding=_binding(context, point_id),
        verification_work_record=_verification_record(),
    )


@pytest.mark.parametrize(
    ("fails", "expected"),
    (
        (False, GroundFallbackOutcome.FEASIBLE_CERTIFIED),
        (True, GroundFallbackOutcome.INFEASIBLE_CERTIFIED),
    ),
)
def test_trusted_executor_authorizes_exact_complete_outcomes(
    fails: bool, expected: GroundFallbackOutcome
) -> None:
    raw, cap, context, point_id = _raw_execution(fails=fails)
    assert raw.result.outcome is expected
    sealed = _seal_trusted_ground_fallback_execution_v1(
        raw, constraint_delta=Fraction(1, 20)
    )

    verified = _verify(sealed, cap, context, point_id)

    assert verified.role is SemanticRole.GROUND_FALLBACK
    assert verified.outcome == expected.value
    assert verified.artifact == raw.result
    assert raw.work_vector.work_vector_id in verified.recomputed_evidence_ids


def test_raw_result_raw_json_and_unsealed_search_have_no_authority() -> None:
    raw, cap, context, point_id = _raw_execution(fails=False)
    with pytest.raises(SemanticVerificationV1Error, match="trusted runtime provenance"):
        _verify(raw, cap, context, point_id)
    with pytest.raises(SemanticVerificationV1Error, match="raw result JSON"):
        verify_ground_fallback_semantics_v1(
            raw.result.to_dict(),
            cap_profile=cap,
            binding=_binding(context, point_id),
            verification_work_record=_verification_record(),
        )


def test_runtime_seal_rejects_replaced_result_and_work() -> None:
    raw, cap, context, point_id = _raw_execution(fails=False)
    sealed = _seal_trusted_ground_fallback_execution_v1(
        raw, constraint_delta=Fraction(1, 20)
    )
    changed_result = dataclasses.replace(
        sealed.result, selected_upper_id=_id("substituted-upper")
    )
    result_attack = GroundFallbackExecutionV1(
        changed_result,
        sealed.work_vector,
        sealed.selected_policy,
        sealed.trusted_provenance,
    )
    with pytest.raises(SemanticVerificationV1Error, match="does not bind"):
        _verify(result_attack, cap, context, point_id)

    registry = official_counter_registry_v1()
    changed_values = sealed.work_vector.values
    changed_values["io.output_bytes"] += 1
    changed_work = registry.materialize(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        records=explicit_records_v1(
            registry,
            changed_values,
            recorder_id="fallback-work-replacement-attack-v1",
        ),
    )
    work_bound_result = dataclasses.replace(
        sealed.result, work_vector_id=changed_work.work_vector_id
    )
    work_attack = GroundFallbackExecutionV1(
        work_bound_result,
        changed_work,
        sealed.selected_policy,
        sealed.trusted_provenance,
    )
    with pytest.raises(SemanticVerificationV1Error, match="does not bind"):
        _verify(work_attack, cap, context, point_id)


def test_wrong_context_and_cap_cannot_reuse_trusted_execution() -> None:
    raw, cap, context, point_id = _raw_execution(fails=False)
    sealed = _seal_trusted_ground_fallback_execution_v1(
        raw, constraint_delta=Fraction(1, 20)
    )
    other_context = _context("other-context")
    with pytest.raises(
        SemanticVerificationV1Error,
        match="does not match|another route/query",
    ):
        _verify(sealed, cap, other_context, point_id)
    with pytest.raises(SemanticVerificationV1Error, match="another finite cap"):
        _verify(
            sealed,
            _cap(max_states_expanded=11),
            context,
            point_id,
        )


def test_cap_exhausted_is_authorized_only_as_noncertificate_outcome() -> None:
    raw, cap, context, point_id = _raw_execution(
        fails=False, cap=_cap(max_cap_checks=1)
    )
    assert raw.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    sealed = _seal_trusted_ground_fallback_execution_v1(
        raw, constraint_delta=Fraction(1, 20)
    )
    assert _verify(sealed, cap, context, point_id).outcome == "CAP_EXHAUSTED"

    # Even a defect inside the trusted executor that relabelled the exhausted
    # bytes cannot turn them into an infeasibility certificate: semantic replay
    # independently checks frontier completeness and native terminal counters.
    false_infeasible = GroundFallbackResultV1(
        raw.result.route_decision_context_id,
        raw.result.decision_point_id,
        raw.result.route_decision_id,
        raw.result.selected_upper_id,
        raw.result.route_attempt_id,
        raw.result.query_id,
        raw.result.ground_fallback_cap_profile_id,
        raw.result.work_vector_id,
        GroundFallbackOutcome.INFEASIBLE_CERTIFIED,
        True,
        (),
        (),
        None,
        None,
        None,
        raw.result.composed_candidate_count,
    )
    mislabeled = _seal_trusted_ground_fallback_execution_v1(
        GroundFallbackExecutionV1(false_infeasible, raw.work_vector, None),
        constraint_delta=Fraction(1, 20),
    )
    with pytest.raises(SemanticVerificationV1Error, match="complete nonempty frontier"):
        _verify(mislabeled, cap, context, point_id)
