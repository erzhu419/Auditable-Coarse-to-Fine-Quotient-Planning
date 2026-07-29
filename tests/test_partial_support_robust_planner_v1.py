from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.partial_support_robust_planner_v1 as robust_module
from acfqp.partial_support_robust_planner_v1 import (
    CONTRACT_VERSION,
    PROFILE_KEY,
    CatalogueActionV1,
    CounterfactualStatus,
    DestinationCategory,
    DistinctActionConcretizerEntryV1,
    IntervalDestinationMassV1,
    IntervalSimplexRowV1,
    PartialSupportRobustPlannerInvariantViolation,
    RegisteredDestinationV1,
    RobustAuditStatus,
    RobustThresholdProfileV1,
    StateActionCatalogueV1,
    build_partial_support_model_v1,
    solve_ground_direct_robust_h2_v1,
    solve_quotient_robust_h2_v1,
    verify_robust_plan_audit_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _masses(
    *items: tuple[str, Fraction, Fraction],
) -> tuple[IntervalDestinationMassV1, ...]:
    return tuple(
        sorted(
            (
                IntervalDestinationMassV1(
                    destination_id,
                    lower,
                    upper,
                )
                for destination_id, lower, upper in items
            ),
            key=lambda item: item.destination_id,
        )
    )


def _catalogue(
    state_id: str,
    state_coordinate_key: str,
    action_id: str,
    action_coordinate_key: str,
):
    return StateActionCatalogueV1(
        state_id,
        state_coordinate_key,
        (CatalogueActionV1(action_id, action_coordinate_key),),
    )


def _safe_model(
    *,
    child_lower: Fraction = Fraction(99, 100),
    child_upper: Fraction = Fraction(1),
    other_lower: Fraction = Fraction(0),
    other_upper: Fraction = Fraction(1, 100),
):
    context = _id("context")
    root_state = _id("root-state")
    child_state = _id("child-state")
    root_cell = _id("root-cell")
    child_cell = _id("child-cell")
    root_action = _id("root-action")
    child_action = _id("child-action")
    root_abstract_action = _id("root-abstract-action")
    child_abstract_action = _id("child-abstract-action")
    child_destination = _id("child-destination")
    success_destination = _id("success-destination")
    failure_destination = _id("failure-destination")
    other_destination = _id("other-destination")

    catalogues = (
        _catalogue(
            root_state,
            root_cell,
            root_action,
            root_abstract_action,
        ),
        _catalogue(
            child_state,
            child_cell,
            child_action,
            child_abstract_action,
        ),
    )
    destinations = (
        RegisteredDestinationV1(
            child_destination,
            DestinationCategory.ACTIVE_STATE,
            child_state,
        ),
        RegisteredDestinationV1(
            success_destination,
            DestinationCategory.SUCCESS_TERMINAL,
        ),
        RegisteredDestinationV1(
            failure_destination,
            DestinationCategory.FAILURE,
        ),
        RegisteredDestinationV1(
            other_destination,
            DestinationCategory.OTHER,
        ),
    )
    rows = (
        IntervalSimplexRowV1(
            root_state,
            2,
            root_action,
            Fraction(0),
            Fraction(0),
            other_destination,
            _masses(
                (child_destination, child_lower, child_upper),
                (other_destination, other_lower, other_upper),
            ),
        ),
        IntervalSimplexRowV1(
            child_state,
            1,
            child_action,
            Fraction(1),
            Fraction(1),
            other_destination,
            _masses(
                (success_destination, Fraction(1), Fraction(1)),
                (other_destination, Fraction(0), Fraction(0)),
            ),
        ),
    )
    concretizers = (
        DistinctActionConcretizerEntryV1(
            root_cell,
            root_state,
            root_abstract_action,
            (root_action,),
        ),
        DistinctActionConcretizerEntryV1(
            child_cell,
            child_state,
            child_abstract_action,
            (child_action,),
        ),
    )
    model = build_partial_support_model_v1(
        context_id=context,
        root_state_id=root_state,
        catalogues=catalogues,
        destinations=destinations,
        rows=rows,
        concretizer_entries=concretizers,
    )
    threshold = RobustThresholdProfileV1(
        context,
        Fraction(1, 50),
        Fraction(1),
    )
    return model, threshold


def _branching_factorization_model(child_count: int):
    """Build a ground-large/quotient-small exact H=2 regression model."""

    context = _id(f"factorization-context-{child_count}")
    root_state = _id(f"factorization-root-{child_count}")
    root_cell = _id(f"factorization-root-cell-{child_count}")
    child_cell = _id(f"factorization-child-cell-{child_count}")
    root_semantic = _id(f"factorization-root-semantic-{child_count}")
    child_semantic = _id(f"factorization-child-semantic-{child_count}")
    other_destination = _id(f"factorization-other-{child_count}")
    success_destination = _id(f"factorization-success-{child_count}")
    child_states = tuple(
        sorted(
            _id(f"factorization-child-{child_count}-{index}")
            for index in range(child_count)
        )
    )
    root_actions = tuple(
        sorted(
            (
                CatalogueActionV1(
                    _id(f"factorization-root-action-{child_count}-{index}"),
                    root_semantic,
                )
                for index in range(2)
            ),
            key=lambda item: item.action_id,
        )
    )
    child_actions = {
        state_id: tuple(
            sorted(
                (
                    CatalogueActionV1(
                        _id(
                            f"factorization-child-action-{child_count}-"
                            f"{state_id}-{index}"
                        ),
                        child_semantic,
                    )
                    for index in range(2)
                ),
                key=lambda item: item.action_id,
            )
        )
        for state_id in child_states
    }
    catalogues = (
        StateActionCatalogueV1(root_state, root_cell, root_actions),
        *(
            StateActionCatalogueV1(
                state_id,
                child_cell,
                child_actions[state_id],
            )
            for state_id in child_states
        ),
    )
    active_destinations = tuple(
        RegisteredDestinationV1(
            _id(f"factorization-active-{child_count}-{state_id}"),
            DestinationCategory.ACTIVE_STATE,
            state_id,
        )
        for state_id in child_states
    )
    destinations = (
        *active_destinations,
        RegisteredDestinationV1(
            success_destination,
            DestinationCategory.SUCCESS_TERMINAL,
        ),
        RegisteredDestinationV1(
            other_destination,
            DestinationCategory.OTHER,
        ),
    )
    root_mass_lower = Fraction(1, 2 * child_count)
    rows = [
        IntervalSimplexRowV1(
            root_state,
            2,
            action.action_id,
            Fraction(0),
            Fraction(0),
            other_destination,
            _masses(
                *(
                    (
                        destination.destination_id,
                        root_mass_lower,
                        Fraction(1),
                    )
                    for destination in active_destinations
                ),
                (other_destination, Fraction(0), Fraction(0)),
            ),
        )
        for action in root_actions
    ]
    for state_index, state_id in enumerate(child_states):
        for action_index, action in enumerate(child_actions[state_id]):
            reward = Fraction(2 + ((state_index + action_index) % 7), 10)
            rows.append(
                IntervalSimplexRowV1(
                    state_id,
                    1,
                    action.action_id,
                    reward,
                    reward,
                    other_destination,
                    _masses(
                        (
                            success_destination,
                            Fraction(1),
                            Fraction(1),
                        ),
                        (other_destination, Fraction(0), Fraction(0)),
                    ),
                )
            )
    concretizers = (
        DistinctActionConcretizerEntryV1(
            root_cell,
            root_state,
            root_semantic,
            tuple(action.action_id for action in root_actions),
        ),
        *(
            DistinctActionConcretizerEntryV1(
                child_cell,
                state_id,
                child_semantic,
                tuple(
                    action.action_id for action in child_actions[state_id]
                ),
            )
            for state_id in child_states
        ),
    )
    return (
        build_partial_support_model_v1(
            context_id=context,
            root_state_id=root_state,
            catalogues=catalogues,
            destinations=destinations,
            rows=rows,
            concretizer_entries=concretizers,
        ),
        RobustThresholdProfileV1(
            context,
            Fraction(1, 10),
            Fraction(1),
        ),
    )


def test_nonzero_other_mass_can_receive_sound_h2_certificate() -> None:
    model, threshold = _safe_model()

    audit = solve_ground_direct_robust_h2_v1(model, threshold)

    assert CONTRACT_VERSION == "1.32.0"
    assert PROFILE_KEY == "partial_support_interval_simplex_robust_h2_v0"
    assert audit.status is RobustAuditStatus.CERTIFIED
    assert audit.root_failure_upper == Fraction(1, 100)
    assert audit.root_reward_lower == Fraction(99, 100)
    assert audit.normalized_regret_upper == Fraction(1, 100)
    assert audit.kernel_calls == 0
    assert audit.complete_reachable_policy
    assert len(audit.assignments) == 2
    assert any(
        item.other_mass_upper == Fraction(1, 100)
        and item.failure_charge_count == 1
        for item in audit.other_mass_upper_on_selected_policy
    )
    assert (
        audit.counterfactual.status
        is CounterfactualStatus.ORIGINAL_ALREADY_CERTIFIED
    )
    assert audit.counterfactual.zero_other_certified is None
    assert verify_robust_plan_audit_v1(
        model,
        threshold,
        audit,
    ).valid


def test_risk_bound_equal_to_delta_is_feasible_by_query_contract() -> None:
    model, threshold = _safe_model(
        child_lower=Fraction(49, 50),
        other_upper=Fraction(1, 50),
    )

    audit = solve_ground_direct_robust_h2_v1(model, threshold)

    assert audit.root_failure_upper == threshold.risk_tolerance
    assert audit.status is RobustAuditStatus.CERTIFIED


def test_joint_simplex_prevents_marginal_upper_double_charge_attack() -> None:
    model, threshold = _safe_model()
    root_row = next(row for row in model.rows if row.remaining_horizon == 2)
    child_destination = next(
        item.destination_id
        for item in model.destinations
        if item.category is DestinationCategory.ACTIVE_STATE
    )
    other_destination = model.other_destination.destination_id
    failure_one = _id("failure-one")
    failure_two = _id("failure-two")
    destinations = tuple(
        item
        for item in model.destinations
        if item.category is not DestinationCategory.FAILURE
    ) + (
        RegisteredDestinationV1(
            failure_one,
            DestinationCategory.FAILURE,
        ),
        RegisteredDestinationV1(
            failure_two,
            DestinationCategory.FAILURE,
        ),
    )
    attacked_row = replace(
        root_row,
        masses=_masses(
            (child_destination, Fraction(99, 100), Fraction(1)),
            (failure_one, Fraction(0), Fraction(1, 100)),
            (failure_two, Fraction(0), Fraction(1, 100)),
            (other_destination, Fraction(0), Fraction(1, 100)),
        ),
    )
    attacked_model = build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=destinations,
        rows=(
            attacked_row,
            *(row for row in model.rows if row.remaining_horizon == 1),
        ),
        concretizer_entries=model.concretizer_entries,
    )

    audit = solve_ground_direct_robust_h2_v1(
        attacked_model,
        threshold,
    )

    # The three 0.01 marginal upper bounds share one residual 0.01 mass.
    assert audit.root_failure_upper == Fraction(1, 100)
    assert audit.status is RobustAuditStatus.CERTIFIED
    forged = replace(audit, root_failure_upper=Fraction(3, 100))
    with pytest.raises(
        PartialSupportRobustPlannerInvariantViolation,
        match="semantic replay",
    ):
        verify_robust_plan_audit_v1(
            attacked_model,
            threshold,
            forged,
        )


def test_missing_reachable_policy_assignment_is_rejected_by_replay() -> None:
    model, threshold = _safe_model()
    audit = solve_ground_direct_robust_h2_v1(model, threshold)
    root_only = tuple(
        item for item in audit.assignments if item.remaining_horizon == 2
    )
    forged = replace(audit, assignments=root_only)

    with pytest.raises(
        PartialSupportRobustPlannerInvariantViolation,
        match="semantic replay",
    ):
        verify_robust_plan_audit_v1(model, threshold, forged)


def test_interval_row_rejects_infeasible_unit_simplex() -> None:
    other_destination = _id("infeasible-other")
    with pytest.raises(
        PartialSupportRobustPlannerInvariantViolation,
        match="unit simplex",
    ):
        IntervalSimplexRowV1(
            _id("infeasible-state"),
            2,
            _id("infeasible-action"),
            Fraction(0),
            Fraction(0),
            other_destination,
            _masses(
                (_id("known-destination"), Fraction(0), Fraction(2, 5)),
                (other_destination, Fraction(0), Fraction(2, 5)),
            ),
        )


def test_model_rejects_out_of_registry_destination_in_active_row() -> None:
    model, _ = _safe_model()
    root_row = next(row for row in model.rows if row.remaining_horizon == 2)
    other_destination = model.other_destination.destination_id
    unknown_active_destination = _id("unregistered-active-destination")
    forged_root = replace(
        root_row,
        masses=_masses(
            (unknown_active_destination, Fraction(1), Fraction(1)),
            (other_destination, Fraction(0), Fraction(0)),
        ),
    )

    with pytest.raises(
        PartialSupportRobustPlannerInvariantViolation,
        match="out-of-registry destination",
    ):
        build_partial_support_model_v1(
            context_id=model.context_id,
            root_state_id=model.root_state_id,
            catalogues=model.catalogues,
            destinations=model.destinations,
            rows=(
                forged_root,
                *(row for row in model.rows if row.remaining_horizon == 1),
            ),
            concretizer_entries=model.concretizer_entries,
        )


def test_singleton_quotient_and_direct_robust_bellman_agree() -> None:
    model, threshold = _safe_model()

    direct = solve_ground_direct_robust_h2_v1(model, threshold)
    quotient = solve_quotient_robust_h2_v1(model, threshold)

    assert quotient.status is direct.status
    assert quotient.root_reward_lower == direct.root_reward_lower
    assert (
        quotient.unrestricted_reward_upper
        == direct.unrestricted_reward_upper
    )
    assert quotient.root_failure_upper == direct.root_failure_upper
    assert (
        quotient.normalized_regret_upper
        == direct.normalized_regret_upper
    )
    assert verify_robust_plan_audit_v1(
        model,
        threshold,
        quotient,
    ).valid


def test_factorized_unrestricted_h2_upper_is_byte_exact_to_full_enumeration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, threshold = _safe_model()
    enumerated_upper = max(
        item.reward_upper
        for item in robust_module._direct_policy_evaluations(
            model,
            threshold,
        )
    )
    factorized_upper = robust_module._unrestricted_ground_reward_upper_h2(
        model,
        threshold,
    )
    assert factorized_upper == enumerated_upper

    factorized_audit = solve_quotient_robust_h2_v1(model, threshold)
    monkeypatch.setattr(
        robust_module,
        "_unrestricted_ground_reward_upper_h2",
        lambda _model, _threshold: enumerated_upper,
    )
    enumerated_audit = solve_quotient_robust_h2_v1(model, threshold)
    assert factorized_audit.audit_id == enumerated_audit.audit_id
    assert factorized_audit.to_document() == enumerated_audit.to_document()


def test_factorized_unrestricted_upper_matches_multistate_policy_product() -> None:
    model, threshold = _branching_factorization_model(3)

    enumerated_upper = max(
        item.reward_upper
        for item in robust_module._direct_policy_evaluations(
            model,
            threshold,
        )
    )
    factorized_upper = robust_module._unrestricted_ground_reward_upper_h2(
        model,
        threshold,
    )

    assert len(robust_module._direct_policy_evaluations(model, threshold)) == 16
    assert factorized_upper == enumerated_upper


def test_factorization_preserves_direct_cap_for_ground_large_quotient() -> None:
    model, threshold = _branching_factorization_model(17)

    with pytest.raises(
        PartialSupportRobustPlannerInvariantViolation,
        match="ground robust policy enumeration exceeds the frozen cap",
    ):
        solve_ground_direct_robust_h2_v1(model, threshold)

    quotient = solve_quotient_robust_h2_v1(model, threshold)
    assert quotient.unrestricted_reward_upper == (
        robust_module._unrestricted_ground_reward_upper_h2(model, threshold)
    )
    assert len(quotient.assignments) == 2


def test_atomic_destinations_may_share_active_state_and_terminal_category() -> None:
    model, _ = _safe_model()
    active = next(
        item
        for item in model.destinations
        if item.category is DestinationCategory.ACTIVE_STATE
    )
    success = next(
        item
        for item in model.destinations
        if item.category is DestinationCategory.SUCCESS_TERMINAL
    )
    active_two = RegisteredDestinationV1(
        _id("second-active-atom"),
        DestinationCategory.ACTIVE_STATE,
        active.state_id,
    )
    success_two = RegisteredDestinationV1(
        _id("second-success-atom"),
        DestinationCategory.SUCCESS_TERMINAL,
    )
    other_destination = model.other_destination.destination_id
    root_row = next(row for row in model.rows if row.remaining_horizon == 2)
    child_row = next(row for row in model.rows if row.remaining_horizon == 1)
    root_row = replace(
        root_row,
        masses=_masses(
            (active.destination_id, Fraction(49, 100), Fraction(1, 2)),
            (active_two.destination_id, Fraction(49, 100), Fraction(1, 2)),
            (other_destination, Fraction(0), Fraction(1, 50)),
        ),
    )
    child_row = replace(
        child_row,
        masses=_masses(
            (success.destination_id, Fraction(1, 2), Fraction(1, 2)),
            (success_two.destination_id, Fraction(1, 2), Fraction(1, 2)),
            (other_destination, Fraction(0), Fraction(0)),
        ),
    )
    expanded = build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=(
            *model.destinations,
            active_two,
            success_two,
        ),
        rows=(root_row, child_row),
        concretizer_entries=model.concretizer_entries,
    )
    threshold = RobustThresholdProfileV1(
        model.context_id,
        Fraction(3, 100),
        Fraction(1),
    )

    audit = solve_ground_direct_robust_h2_v1(expanded, threshold)

    assert audit.status is RobustAuditStatus.CERTIFIED
    assert audit.root_failure_upper == Fraction(1, 50)
    assert audit.root_reward_lower == Fraction(49, 50)


def test_other_only_counterfactual_identifies_failed_to_certified_frontier() -> None:
    model, _ = _safe_model(
        child_lower=Fraction(47, 50),
        child_upper=Fraction(1),
        other_upper=Fraction(3, 50),
    )
    threshold = RobustThresholdProfileV1(
        model.context_id,
        Fraction(1, 20),
        Fraction(1),
    )

    audit = solve_ground_direct_robust_h2_v1(model, threshold)

    assert audit.status is RobustAuditStatus.FAILED_PROOF_FRONTIER
    assert audit.root_failure_upper == Fraction(3, 50)
    assert audit.counterfactual.status is CounterfactualStatus.ZERO_OTHER_CERTIFIED
    assert audit.counterfactual.changes_failed_to_certified
    assert not audit.counterfactual.acquisition_authorized
    assert audit.failed_frontier is not None
    assert audit.failed_frontier.other_only_counterfactual_changes


def test_zero_other_counterfactual_reports_infeasible_simplex_without_authority() -> None:
    model, _ = _safe_model(
        child_lower=Fraction(47, 50),
        child_upper=Fraction(47, 50),
        other_lower=Fraction(3, 50),
        other_upper=Fraction(3, 50),
    )
    threshold = RobustThresholdProfileV1(
        model.context_id,
        Fraction(1, 20),
        Fraction(1),
    )

    audit = solve_ground_direct_robust_h2_v1(model, threshold)

    assert audit.status is RobustAuditStatus.FAILED_PROOF_FRONTIER
    assert (
        audit.counterfactual.status
        is CounterfactualStatus.ZERO_OTHER_INFEASIBLE_SIMPLEX
    )
    assert not audit.counterfactual.changes_failed_to_certified
    assert audit.counterfactual.zero_other_certified is None
    assert audit.counterfactual.zero_other_model_id is None
    assert not audit.counterfactual.acquisition_authorized
