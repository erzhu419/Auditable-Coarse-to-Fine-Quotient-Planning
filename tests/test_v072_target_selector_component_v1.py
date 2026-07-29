from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
import inspect
from typing import Any

import pytest

from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import v072_target_selector_component_v1 as component
from tests.test_target_preauthorization_selector_v2 import (
    _fixture,
    _id,
    _prepare,
    _registry,
    _source_binding,
)


def _arm_inputs(
    arm: selector.TargetSelectionArmV2,
    *,
    variant: int = 0,
    previous: selector.PreparedTargetSelectionV2 | None = None,
):
    model, audit, threshold, registry = _registry(
        variant=variant,
        previous=previous,
    )
    source_prior = (
        _source_binding(registry)
        if arm
        in (
            selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
            selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
        )
        else None
    )
    abstention = (
        selector.OodPriorTypedAbstentionV2(
            _id(f"component-ood-prior:{variant}"),
            _id(f"component-ood-schema:{variant}"),
        )
        if arm is selector.TargetSelectionArmV2.OOD_ABSTENTION
        else None
    )
    return (
        model,
        audit,
        threshold,
        registry,
        source_prior,
        abstention,
    )


@pytest.mark.parametrize("arm", tuple(selector.TargetSelectionArmV2))
def test_all_four_arms_receive_independent_semantic_verification(
    arm: selector.TargetSelectionArmV2,
) -> None:
    model, audit, threshold, registry, source, abstention = (
        _arm_inputs(arm)
    )
    result = (
        component.prepare_and_verify_v072_target_selection_component_v1(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=arm,
            source_prior=source,
            ood_abstention=abstention,
        )
    )
    verification = result.semantic_verification
    assert verification.semantic_replay_valid
    assert verification.arm is arm
    assert verification.prepared_selection_id == (
        result.prepared_selection.prepared_selection_id
    )
    assert verification.authorization_id == (
        result.prepared_selection.authorization.authorization_id
    )
    assert verification.production_prepare_or_private_derivation_called is False
    assert verification.caller_score_or_gain_trusted is False
    assert verification.native_zero_access_verified
    assert all(
        item.base == item.gain / item.exact_draw_upper
        for item in verification.counterfactual_replays
        if item.status
        is selector.CounterfactualEvaluationStatusV2.EVALUATED
    )


def test_semantic_verifier_does_not_call_production_derivation_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared_inputs = []
    for arm in selector.TargetSelectionArmV2:
        model, audit, threshold, registry, source, abstention = (
            _arm_inputs(arm)
        )
        claimed = selector.prepare_target_selection_v2(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=arm,
            source_prior=source,
            ood_abstention=abstention,
        )
        prepared_inputs.append(
            (
                model,
                audit,
                threshold,
                registry,
                arm,
                source,
                abstention,
                claimed,
            )
        )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("production selector derivation was called")

    for name in (
        "prepare_target_selection_v2",
        "_counterfactuals",
        "_scores",
        "_schedule",
        "_one_row_zero_other_model",
        "_fixed_policy_slack",
        "_fixed_ground_policy_metrics",
        "_fixed_quotient_policy_metrics",
        "_prior_resolution",
        "_portable_feature",
    ):
        monkeypatch.setattr(selector, name, forbidden)

    for (
        model,
        audit,
        threshold,
        registry,
        arm,
        source,
        abstention,
        claimed,
    ) in prepared_inputs:
        verified = component.verify_target_selection_semantically_v1(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=arm,
            source_prior=source,
            ood_abstention=abstention,
            claimed=claimed,
        )
        assert verified.semantic_replay_valid


def test_independent_counterfactual_invariant_failure_never_becomes_infeasible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, audit, threshold, registry, source, abstention = (
        _arm_inputs(selector.TargetSelectionArmV2.NO_PRIOR)
    )
    claimed = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
    )

    def fail_closed(*_args, **_kwargs):
        raise robust.PartialSupportRobustPlannerInvariantViolation(
            "injected independent construction failure"
        )

    monkeypatch.setattr(
        component,
        "_one_row_zero_other_model",
        fail_closed,
    )
    with pytest.raises(
        component.V072TargetSelectorComponentInvariantViolation,
        match="admissible zero-OTHER replay construction failed",
    ):
        component.verify_target_selection_semantically_v1(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=selector.TargetSelectionArmV2.NO_PRIOR,
            source_prior=source,
            ood_abstention=abstention,
            claimed=claimed,
        )


def _unsafe_clone(original: Any, **changes: Any) -> Any:
    cloned = object.__new__(type(original))
    for item in fields(original):
        object.__setattr__(
            cloned,
            item.name,
            changes.get(item.name, getattr(original, item.name)),
        )
    return cloned


def _coherently_forge_gain_and_score(
    prepared: selector.PreparedTargetSelectionV2,
) -> selector.PreparedTargetSelectionV2:
    original_counterfactual = prepared.counterfactuals[0]
    assert original_counterfactual.counterfactual_slack is not None
    increment = Fraction(1, 10_000)
    forged_gain = original_counterfactual.gain + increment
    forged_counterfactual = replace(
        original_counterfactual,
        counterfactual_slack=(
            original_counterfactual.counterfactual_slack + increment
        ),
        gain=forged_gain,
        base=forged_gain / original_counterfactual.exact_draw_upper,
    )
    counterfactuals = tuple(
        sorted(
            (
                forged_counterfactual
                if item.candidate_id
                == original_counterfactual.candidate_id
                else item
                for item in prepared.counterfactuals
            ),
            key=lambda item: item.counterfactual_id,
        )
    )

    original_score = next(
        item
        for item in prepared.scores
        if item.candidate_id == original_counterfactual.candidate_id
    )
    forged_score = replace(
        original_score,
        counterfactual_id=forged_counterfactual.counterfactual_id,
        base=forged_counterfactual.base,
        score=forged_counterfactual.base * original_score.multiplier,
        gain=forged_counterfactual.gain,
        gain_eligible=True,
    )
    scores = tuple(
        sorted(
            (
                forged_score
                if item.candidate_id == original_score.candidate_id
                else item
                for item in prepared.scores
            ),
            key=lambda item: item.score_id,
        )
    )
    candidate_by_id = {
        item.candidate_id: item for item in prepared.registry.candidates
    }
    entries = tuple(
        sorted(
            (
                selector.TargetSelectionScheduleEntryV2(
                    score.counterfactual_id,
                    score.candidate_id,
                    score.score,
                    score.gain,
                    score.exact_draw_upper,
                    score.gain_eligible,
                    (
                        prepared.registry
                        .cumulative_new_child_actions_before_round
                        + candidate_by_id[
                            score.candidate_id
                        ].n_new_child_actions
                        <= selector.MAX_NEW_CHILD_ACTIONS_TOTAL
                        and prepared.registry
                        .cumulative_draw_upper_before_round
                        + score.exact_draw_upper
                        <= selector.MAX_TWO_ROUND_DRAW_UPPER
                    ),
                )
                for score in scores
            ),
            key=lambda item: (
                -item.score,
                -item.gain,
                item.exact_draw_upper,
                item.candidate_id,
            ),
        )
    )
    selected_entry = next(
        item
        for item in entries
        if item.gain_eligible and item.cap_eligible
    )
    schedule = selector.TargetSelectionScheduleCoreV2(
        prepared.registry.registry_id,
        prepared.registry.round_index,
        entries,
        selected_entry.candidate_id,
    )
    selected = candidate_by_id[selected_entry.candidate_id]
    authorization = replace(
        prepared.authorization,
        schedule_core_id=schedule.schedule_core_id,
        selected_candidate_id=selected.candidate_id,
        selected_planner_row_id=selected.planner_row_id,
        selected_exact_draw_upper=selected.exact_draw_upper,
        cumulative_new_child_actions_after_selection=(
            prepared.registry.cumulative_new_child_actions_before_round
            + selected.n_new_child_actions
        ),
        cumulative_draw_upper_after_selection=(
            prepared.registry.cumulative_draw_upper_before_round
            + selected.exact_draw_upper
        ),
    )
    return selector.PreparedTargetSelectionV2(
        prepared.registry,
        counterfactuals,
        scores,
        schedule,
        prepared.access_log,
        authorization,
        prepared.source_prior_binding,
        prepared.ood_abstention,
    )


def test_coherently_resigned_caller_gain_and_score_are_rejected() -> None:
    model, audit, threshold, registry, source, abstention = (
        _arm_inputs(selector.TargetSelectionArmV2.NO_PRIOR)
    )
    prepared = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
    )
    forged = _coherently_forge_gain_and_score(prepared)
    assert forged.prepared_selection_id != prepared.prepared_selection_id
    with pytest.raises(
        component.V072TargetSelectorComponentInvariantViolation,
        match="claimed gains",
    ):
        component.verify_target_selection_semantically_v1(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=selector.TargetSelectionArmV2.NO_PRIOR,
            source_prior=source,
            ood_abstention=abstention,
            claimed=forged,
        )
    for function in (
        component.verify_target_selection_semantically_v1,
        component.prepare_and_verify_v072_target_selection_component_v1,
    ):
        parameters = inspect.signature(function).parameters
        assert "score" not in parameters
        assert "gain" not in parameters
        assert "ranking" not in parameters


def test_nonzero_preaccess_counter_attack_is_rejected_even_if_id_is_hidden() -> None:
    model, audit, threshold, registry, source, abstention = (
        _arm_inputs(selector.TargetSelectionArmV2.NO_PRIOR)
    )
    prepared = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
    )
    original_counter = prepared.access_log.native_zero_counters[0]
    nonzero_counter = _unsafe_clone(original_counter, value=1)
    assert nonzero_counter.counter_id == original_counter.counter_id
    forged_access = _unsafe_clone(
        prepared.access_log,
        native_zero_counters=(
            nonzero_counter,
            *prepared.access_log.native_zero_counters[1:],
        ),
    )
    assert forged_access.access_log_id == prepared.access_log.access_log_id
    forged = _unsafe_clone(prepared, access_log=forged_access)
    with pytest.raises(
        component.V072TargetSelectorComponentInvariantViolation,
        match="claimed gains",
    ):
        component.verify_target_selection_semantically_v1(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=selector.TargetSelectionArmV2.NO_PRIOR,
            source_prior=source,
            ood_abstention=abstention,
            claimed=forged,
        )


def test_round_two_fresh_chain_passes_but_stale_or_transplanted_registry_fails() -> None:
    first = _prepare(selector.TargetSelectionArmV2.NO_PRIOR)
    (
        model2,
        audit2,
        threshold2,
        registry2,
        source2,
        abstention2,
    ) = _arm_inputs(
        selector.TargetSelectionArmV2.NO_PRIOR,
        variant=1,
        previous=first,
    )
    second = selector.prepare_target_selection_v2(
        model=model2,
        audit=audit2,
        threshold=threshold2,
        registry=registry2,
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
    )
    assert component.verify_target_selection_semantically_v1(
        model=model2,
        audit=audit2,
        threshold=threshold2,
        registry=registry2,
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
        previous_selection=first,
        source_prior=source2,
        ood_abstention=abstention2,
        claimed=second,
    ).semantic_replay_valid

    with pytest.raises(
        component.V072TargetSelectorComponentInvariantViolation,
        match="stale",
    ):
        component.verify_target_selection_semantically_v1(
            model=model2,
            audit=audit2,
            threshold=threshold2,
            registry=first.registry,
            arm=selector.TargetSelectionArmV2.NO_PRIOR,
            previous_selection=first,
            claimed=second,
        )

    transplanted = _unsafe_clone(
        registry2,
        candidates=first.registry.candidates,
    )
    with pytest.raises(
        component.V072TargetSelectorComponentInvariantViolation,
    ):
        component.verify_target_selection_semantically_v1(
            model=model2,
            audit=audit2,
            threshold=threshold2,
            registry=transplanted,
            arm=selector.TargetSelectionArmV2.NO_PRIOR,
            previous_selection=first,
            claimed=second,
        )

    wrong_previous = _prepare(
        selector.TargetSelectionArmV2.NO_PRIOR,
        variant=2,
    )
    with pytest.raises(
        component.V072TargetSelectorComponentInvariantViolation,
        match="predecessor",
    ):
        component.verify_target_selection_semantically_v1(
            model=model2,
            audit=audit2,
            threshold=threshold2,
            registry=registry2,
            arm=selector.TargetSelectionArmV2.NO_PRIOR,
            previous_selection=wrong_previous,
            claimed=second,
        )


def test_ground_direct_selected_policy_is_semantically_replayed() -> None:
    model, _quotient_audit, threshold, _metadata = _fixture()
    audit = robust.solve_ground_direct_robust_h2_v1(model, threshold)
    assert audit.failed_frontier is not None
    reachable = set(robust._reachable_child_states(model))
    extra_catalogues = tuple(
        item
        for item in model.catalogues
        if item.state_id not in reachable
        and item.state_id != model.root_state_id
    )
    row_by_id = {item.row_id: item for item in model.rows}
    public = selector.freeze_public_frontier_action_metadata_v2(
        model=model,
        audit=audit,
        support_epoch_id=_id("ground-component-support-epoch"),
        newly_reachable_child_catalogues_by_row={
            row_id: (
                extra_catalogues
                if row_by_id[row_id].remaining_horizon == 2
                else ()
            )
            for row_id in audit.failed_frontier.selected_row_ids
        },
    )
    registry = selector.freeze_target_candidate_registry_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        public_metadata=public,
        round_index=1,
    )
    result = (
        component.prepare_and_verify_v072_target_selection_component_v1(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=selector.TargetSelectionArmV2.NO_PRIOR,
        )
    )
    assert result.semantic_verification.semantic_replay_valid
    assert audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT
