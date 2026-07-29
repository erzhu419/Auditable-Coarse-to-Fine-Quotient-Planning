from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import copy
from unittest.mock import patch

import pytest

import acfqp.observation_support_exact_evaluation_v1 as exact
import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.partial_support_confidence_v1 as confidence
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _ExactEventInterval:
    event_key: str
    event_interval_id: str
    lower_probability: Fraction
    upper_probability: Fraction


@dataclass(frozen=True)
class _ExactAuthority:
    authority_id: str
    event_intervals: tuple[_ExactEventInterval, ...]


@dataclass(frozen=True)
class _ExactSupportEpoch:
    support_epoch_id: str


@dataclass(frozen=True)
class _ExactPartialRow:
    binding: acquisition.GraphObservationRowBindingV1
    support_descriptors: tuple[
        acquisition.GraphObservedOutcomeDescriptorV1, ...
    ]
    confidence_authority: _ExactAuthority
    support_epoch: _ExactSupportEpoch
    other_interval: _ExactEventInterval
    partial_row_id: str


def _tiny_audit_template() -> robust.RobustPlanAuditV1:
    context_id = _id("tiny-context")
    root_state = _id("tiny-root")
    child_state = _id("tiny-child")
    root_action = _id("tiny-root-action")
    child_action = _id("tiny-child-action")
    active = _id("tiny-active")
    success = _id("tiny-success")
    other = _id("tiny-other")
    catalogues = (
        robust.StateActionCatalogueV1(
            root_state,
            root_state,
            (robust.CatalogueActionV1(root_action, root_action),),
        ),
        robust.StateActionCatalogueV1(
            child_state,
            child_state,
            (robust.CatalogueActionV1(child_action, child_action),),
        ),
    )
    destinations = (
        robust.RegisteredDestinationV1(
            active,
            robust.DestinationCategory.ACTIVE_STATE,
            child_state,
        ),
        robust.RegisteredDestinationV1(
            success,
            robust.DestinationCategory.SUCCESS_TERMINAL,
        ),
        robust.RegisteredDestinationV1(
            other,
            robust.DestinationCategory.OTHER,
        ),
    )
    rows = (
        robust.IntervalSimplexRowV1(
            root_state,
            2,
            root_action,
            Fraction(1, 64),
            Fraction(1, 64),
            other,
            tuple(
                sorted(
                    (
                        robust.IntervalDestinationMassV1(
                            active,
                            Fraction(1),
                            Fraction(1),
                        ),
                        robust.IntervalDestinationMassV1(
                            other,
                            Fraction(0),
                            Fraction(0),
                        ),
                    ),
                    key=lambda item: item.destination_id,
                )
            ),
        ),
        robust.IntervalSimplexRowV1(
            child_state,
            1,
            child_action,
            Fraction(1, 32),
            Fraction(1, 32),
            other,
            tuple(
                sorted(
                    (
                        robust.IntervalDestinationMassV1(
                            success,
                            Fraction(1),
                            Fraction(1),
                        ),
                        robust.IntervalDestinationMassV1(
                            other,
                            Fraction(0),
                            Fraction(0),
                        ),
                    ),
                    key=lambda item: item.destination_id,
                )
            ),
        ),
    )
    model = robust.build_partial_support_model_v1(
        context_id=context_id,
        root_state_id=root_state,
        catalogues=catalogues,
        destinations=destinations,
        rows=rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        context_id,
        Fraction(1, 20),
        Fraction(3, 64),
    )
    return robust.solve_ground_direct_robust_h2_v1(model, threshold)


def _exact_row(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> _ExactPartialRow:
    atoms = observer.evaluation_exact_atoms_v1(
        context,
        catalogue,
        action,
    )
    descriptor_by_id: dict[
        str,
        acquisition.GraphObservedOutcomeDescriptorV1,
    ] = {}
    mass_by_id: dict[str, Fraction] = {}
    for atom in atoms:
        descriptor = acquisition.GraphObservedOutcomeDescriptorV1(
            atom.next_state,
            atom.realized_row_reward,
            atom.failure,
            atom.terminal,
        )
        descriptor_by_id[descriptor.outcome_id] = descriptor
        mass_by_id[descriptor.outcome_id] = (
            mass_by_id.get(descriptor.outcome_id, Fraction(0))
            + atom.probability
        )
    descriptors = tuple(
        descriptor_by_id[item] for item in sorted(descriptor_by_id)
    )
    binding = acquisition.GraphObservationRowBindingV1(
        context.context_id,
        catalogue.catalogue_id,
        catalogue.state.state_id,
        action,
        catalogue.remaining_horizon,
    )
    events = tuple(
        _ExactEventInterval(
            item.outcome_id,
            _id(f"{binding.row_id}:{item.outcome_id}:event"),
            mass_by_id[item.outcome_id],
            mass_by_id[item.outcome_id],
        )
        for item in descriptors
    )
    other = _ExactEventInterval(
        confidence.OTHER_EVENT_KEY,
        _id(f"{binding.row_id}:other:event"),
        Fraction(0),
        Fraction(0),
    )
    authority = _ExactAuthority(
        _id(f"{binding.row_id}:authority"),
        (*events, other),
    )
    return _ExactPartialRow(
        binding,
        descriptors,
        authority,
        _ExactSupportEpoch(_id(f"{binding.row_id}:epoch")),
        other,
        _id(f"{binding.row_id}:partial-row"),
    )


@pytest.fixture(scope="module")
def exact_fixture():
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    root = observer.legal_action_catalogue_v1(
        context,
        observer.root_state_v1(context),
        2,
    )
    child_by_state: dict[str, observer.SymbolicGraphStateV1] = {}
    for action in root.actions:
        for atom in observer.evaluation_exact_atoms_v1(
            context,
            root,
            action,
        ):
            if not atom.failure:
                child_by_state[atom.next_state.state_id] = atom.next_state
    children = tuple(
        observer.legal_action_catalogue_v1(context, state, 1)
        for _, state in sorted(child_by_state.items())
    )
    catalogues = (root, *children)
    rows = tuple(
        _exact_row(context, catalogue, action)
        for catalogue in catalogues
        for action in catalogue.actions
    )
    with (
        patch.object(
            acquisition,
            "GraphPartialSupportRowV1",
            _ExactPartialRow,
        ),
        patch.object(
            graph_model.confidence,
            "verify_partial_support_confidence_v1",
            lambda _authority: None,
        ),
    ):
        bridge = graph_model.build_observation_support_graph_models_v1(
            context=context,
            root_catalogue=root,
            catalogues=catalogues,
            partial_rows=rows,
        )
    canonical_bridge = bridge
    identity_concretizers = tuple(
        robust.DistinctActionConcretizerEntryV1(
            catalogue.state_id,
            catalogue.state_id,
            action.action_id,
            (action.action_id,),
        )
        for catalogue in bridge.direct_model.catalogues
        for action in catalogue.actions
    )
    identity_quotient_model = robust.build_partial_support_model_v1(
        context_id=bridge.context_id,
        root_state_id=bridge.direct_model.root_state_id,
        catalogues=bridge.direct_model.catalogues,
        destinations=bridge.direct_model.destinations,
        rows=bridge.direct_model.rows,
        concretizer_entries=identity_concretizers,
    )
    bridge = copy.copy(canonical_bridge)
    object.__setattr__(
        bridge,
        "quotient_model",
        identity_quotient_model,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        bridge.reward_ceiling,
        context.normalized_regret_tolerance,
    )
    comparator = observer.evaluation_exact_ground_search_v1(context)
    binding_by_public_action = {
        (
            item.state_id,
            item.remaining_horizon,
            item.action,
        ): item
        for item in bridge.action_bindings
    }
    direct_assignments = tuple(
        sorted(
            (
                robust.RobustPolicyAssignmentV1(
                    robust.PolicyScope.GROUND_STATE,
                    assignment.state.state_id,
                    assignment.remaining_horizon,
                    binding_by_public_action[
                        (
                            assignment.state.state_id,
                            assignment.remaining_horizon,
                            assignment.action,
                        )
                    ].action_id,
                )
                for assignment in comparator.policy_assignments
            ),
            key=lambda item: item.assignment_id,
        )
    )
    quotient_assignments = tuple(
        sorted(
            (
                robust.RobustPolicyAssignmentV1(
                    robust.PolicyScope.QUOTIENT_CELL,
                    item.scope_key,
                    item.remaining_horizon,
                    item.selected_action_key,
                )
                for item in direct_assignments
            ),
            key=lambda item: item.assignment_id,
        )
    )
    template = _tiny_audit_template()
    direct = replace(
        template,
        solver_kind=robust.RobustSolverKind.GROUND_DIRECT,
        model_id=bridge.direct_model.model_id,
        threshold_profile_id=threshold.threshold_profile_id,
        assignments=direct_assignments,
        root_reward_lower=Fraction(0),
        unrestricted_reward_upper=context.reward_ceiling,
        root_failure_upper=Fraction(1, 25),
        normalized_regret_upper=context.normalized_regret_tolerance,
    )
    quotient = replace(
        template,
        solver_kind=robust.RobustSolverKind.QUOTIENT,
        model_id=bridge.quotient_model.model_id,
        threshold_profile_id=threshold.threshold_profile_id,
        assignments=quotient_assignments,
        root_reward_lower=Fraction(0),
        unrestricted_reward_upper=context.reward_ceiling,
        root_failure_upper=Fraction(1, 25),
        normalized_regret_upper=context.normalized_regret_tolerance,
    )
    return context, canonical_bridge, bridge, direct, quotient


def test_direct_exact_lift_is_bound_and_evaluation_only(exact_fixture) -> None:
    context, bridge, _, direct, _ = exact_fixture

    with patch.object(
        exact.robust,
        "verify_robust_plan_audit_v1",
        lambda _model, _threshold, claimed: (
            None
            if claimed.audit_id == direct.audit_id
            else (_ for _ in ()).throw(
                robust.PartialSupportRobustPlannerInvariantViolation(
                    "semantic replay"
                )
            )
        ),
    ):
        result = exact.evaluate_observation_support_exact_lift_v1(
            context,
            bridge,
            direct,
        )

    assert exact.CONTRACT_VERSION == "1.32.0"
    assert result.solver_kind is robust.RobustSolverKind.GROUND_DIRECT
    assert result.exact_failure_probability == Fraction(99, 5000)
    assert result.exact_normalized_reward == Fraction(3, 64)
    assert result.exact_normalized_regret == 0
    assert result.audit_bounds_cover_exact_lift
    assert result.public_risk_check_passed
    assert result.public_regret_check_passed
    assert result.audit_frozen_before_first_exact_call
    assert not result.may_influence_operational_certificate
    assert not result.repairs_conditional_prng_certificate
    assert (
        result.unseen_outcome_policy_semantics
        == exact.UNSEEN_OUTCOME_POLICY_SEMANTICS
    )
    assert result.execution_lane == exact.EVALUATION_ONLY
    assert result.counters.operational_exact_atom_calls == 0
    assert all(
        len(item.ground_action_ids) == 1
        and item.policy_scope is robust.PolicyScope.GROUND_STATE
        for item in result.decisions
    )
    with patch.object(
        exact.robust,
        "verify_robust_plan_audit_v1",
        lambda *_args: None,
    ):
        verification = exact.verify_observation_support_exact_lift_v1(
            context,
            bridge,
            direct,
            result,
        )
    assert verification.valid
    assert verification.replayed_evaluation_id == result.evaluation_id


def test_quotient_lift_uses_uniform_distinct_action_concretizer(
    exact_fixture,
) -> None:
    context, _, bridge, _, quotient = exact_fixture

    with patch.object(
        exact.robust,
        "verify_robust_plan_audit_v1",
        lambda *_args: None,
    ):
        result = exact.evaluate_observation_support_exact_lift_v1(
            context,
            bridge,
            quotient,
        )

    assert result.solver_kind is robust.RobustSolverKind.QUOTIENT
    assert result.exact_failure_probability == Fraction(99, 5000)
    assert result.exact_normalized_reward == Fraction(3, 64)
    assert all(
        item.policy_scope is robust.PolicyScope.QUOTIENT_CELL
        for item in result.decisions
    )
    assert all(
        item.uniform_ground_action_weight
        == Fraction(1, len(item.ground_action_ids))
        for item in result.decisions
    )


def test_exact_lift_rejects_tampered_audit_and_wrong_context(
    exact_fixture,
) -> None:
    context, bridge, _, direct, _ = exact_fixture
    other = observer.public_context_by_key_v1("opaque_graph_k6_v0")

    with patch.object(
        exact.robust,
        "verify_robust_plan_audit_v1",
        lambda *_args: None,
    ):
        with pytest.raises(
            exact.ObservationSupportExactEvaluationInvariantViolation,
            match="identities",
        ):
            exact.evaluate_observation_support_exact_lift_v1(
                other,
                bridge,
                direct,
            )

    forged = replace(
        direct,
        root_failure_upper=direct.root_failure_upper + Fraction(1, 100),
    )
    def _verify(_model, _threshold, claimed):
        if claimed.audit_id != direct.audit_id:
            raise robust.PartialSupportRobustPlannerInvariantViolation(
                "semantic replay"
            )

    with patch.object(
        exact.robust,
        "verify_robust_plan_audit_v1",
        _verify,
    ):
        with pytest.raises(
            exact.ObservationSupportExactEvaluationInvariantViolation,
            match="semantic replay",
        ):
            exact.evaluate_observation_support_exact_lift_v1(
                context,
                bridge,
                forged,
            )


def test_exact_evaluation_artifact_tampering_fails_replay(
    exact_fixture,
) -> None:
    context, bridge, _, direct, _ = exact_fixture
    with patch.object(
        exact.robust,
        "verify_robust_plan_audit_v1",
        lambda *_args: None,
    ):
        result = exact.evaluate_observation_support_exact_lift_v1(
            context,
            bridge,
            direct,
        )
    forged = replace(
        result,
        audit_failure_bound=result.audit_failure_bound + Fraction(1, 100),
    )

    with patch.object(
        exact.robust,
        "verify_robust_plan_audit_v1",
        lambda *_args: None,
    ):
        with pytest.raises(
            exact.ObservationSupportExactEvaluationInvariantViolation,
            match="differs from exact replay",
        ):
            exact.verify_observation_support_exact_lift_v1(
                context,
                bridge,
                direct,
                forged,
            )


def test_exact_fallback_has_separate_lane_and_cap_is_not_infeasible() -> None:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")

    feasible = exact.run_observation_support_exact_fallback_v1(context)
    assert (
        feasible.outcome
        is exact.ExactFallbackOutcome.FEASIBLE_PLAN_CERTIFIED
    )
    assert feasible.feasible_plan_certified
    assert not feasible.infeasibility_certified
    assert not feasible.interruptible_hard_cap_claimed
    assert feasible.cap_semantics == exact.FALLBACK_CAP_SEMANTICS
    assert feasible.logical_lane == exact.FALLBACK_EXACT
    assert feasible.counters.complete_exact_ground_search_calls == 1
    assert (
        feasible.counters.inferred_exact_atom_calls
        == feasible.search.evaluated_state_action_rows
    )
    assert feasible.counters.acquisition_transition_calls == 0

    exhausted = exact.run_observation_support_exact_fallback_v1(
        context,
        max_exact_state_action_rows=1,
    )
    assert exhausted.cap_exhausted
    assert (
        exhausted.outcome
        is exact.ExactFallbackOutcome.CAP_EXHAUSTED_NONCERTIFICATE
    )
    assert not exhausted.feasible_plan_certified
    assert not exhausted.infeasibility_certified
    assert not exhausted.interruptible_hard_cap_claimed
    assert exhausted.counters.cap_rejections == 1


def test_fallback_rejects_wrong_context_and_tampered_classification() -> None:
    with pytest.raises(
        exact.ObservationSupportExactEvaluationInvariantViolation,
        match="registered",
    ):
        exact.run_observation_support_exact_fallback_v1(object())  # type: ignore[arg-type]

    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    result = exact.run_observation_support_exact_fallback_v1(
        context,
        max_exact_state_action_rows=1,
    )
    with pytest.raises(
        exact.ObservationSupportExactEvaluationInvariantViolation,
        match="classification",
    ):
        replace(result, infeasibility_certified=True)
