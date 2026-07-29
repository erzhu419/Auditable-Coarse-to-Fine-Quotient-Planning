from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import verified_source_acquisition_archive_v2 as source_v2


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _mass(
    destination_id: str,
    lower: Fraction,
    upper: Fraction,
) -> robust.IntervalDestinationMassV1:
    return robust.IntervalDestinationMassV1(
        destination_id,
        lower,
        upper,
    )


def _fixture(
    *,
    variant: int = 0,
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    robust.RobustPlanAuditV1,
    robust.RobustThresholdProfileV1,
    selector.PublicFrontierActionCatalogueMetadataV2,
]:
    context_id = _id("selector-context")
    root_state = _id("selector-root-state")
    child_state = _id("selector-child-state")
    extra_state = _id("selector-extra-public-child-state")
    root_cell = _id("selector-root-cell")
    child_cell = _id("selector-child-cell")
    extra_cell = _id("selector-extra-cell")
    root_action = _id("selector-root-ground-action")
    child_action = _id("selector-child-ground-action")
    extra_action_1 = _id("selector-extra-action-1")
    extra_action_2 = _id("selector-extra-action-2")
    root_semantic = _id("selector-root-semantic-action")
    child_semantic = _id("selector-child-semantic-action")
    extra_semantic_1 = _id("selector-extra-semantic-1")
    extra_semantic_2 = _id("selector-extra-semantic-2")

    active_destination = _id("selector-active-destination")
    failure_destination = _id("selector-failure-destination")
    success_destination = _id("selector-success-destination")
    other_destination = _id("selector-other-destination")
    destinations = tuple(
        sorted(
            (
                robust.RegisteredDestinationV1(
                    active_destination,
                    robust.DestinationCategory.ACTIVE_STATE,
                    child_state,
                ),
                robust.RegisteredDestinationV1(
                    failure_destination,
                    robust.DestinationCategory.FAILURE,
                ),
                robust.RegisteredDestinationV1(
                    success_destination,
                    robust.DestinationCategory.SUCCESS_TERMINAL,
                ),
                robust.RegisteredDestinationV1(
                    other_destination,
                    robust.DestinationCategory.OTHER,
                ),
            ),
            key=lambda item: item.destination_id,
        )
    )
    catalogues = tuple(
        sorted(
            (
                robust.StateActionCatalogueV1(
                    root_state,
                    root_cell,
                    (
                        robust.CatalogueActionV1(
                            root_action,
                            root_semantic,
                        ),
                    ),
                ),
                robust.StateActionCatalogueV1(
                    child_state,
                    child_cell,
                    (
                        robust.CatalogueActionV1(
                            child_action,
                            child_semantic,
                        ),
                    ),
                ),
                robust.StateActionCatalogueV1(
                    extra_state,
                    extra_cell,
                    tuple(
                        sorted(
                            (
                                robust.CatalogueActionV1(
                                    extra_action_1,
                                    extra_semantic_1,
                                ),
                                robust.CatalogueActionV1(
                                    extra_action_2,
                                    extra_semantic_2,
                                ),
                            ),
                            key=lambda item: item.action_id,
                        )
                    ),
                ),
            ),
            key=lambda item: item.state_id,
        )
    )
    concretizers = tuple(
        sorted(
            (
                robust.DistinctActionConcretizerEntryV1(
                    root_cell,
                    root_state,
                    root_semantic,
                    (root_action,),
                ),
                robust.DistinctActionConcretizerEntryV1(
                    child_cell,
                    child_state,
                    child_semantic,
                    (child_action,),
                ),
            ),
            key=lambda item: item.concretizer_entry_id,
        )
    )
    shift = Fraction(variant, 200)
    child_masses = tuple(
        sorted(
            (
                _mass(
                    failure_destination,
                    Fraction(1, 10) - shift,
                    Fraction(1, 4) - shift,
                ),
                _mass(
                    other_destination,
                    Fraction(0),
                    Fraction(1, 5) - shift,
                ),
                _mass(
                    success_destination,
                    Fraction(11, 20) + shift,
                    Fraction(9, 10),
                ),
            ),
            key=lambda item: item.destination_id,
        )
    )
    root_masses = tuple(
        sorted(
            (
                _mass(
                    active_destination,
                    Fraction(3, 4) + shift,
                    Fraction(9, 10),
                ),
                _mass(
                    failure_destination,
                    Fraction(0),
                    Fraction(1, 10) - shift,
                ),
                _mass(
                    other_destination,
                    Fraction(0),
                    Fraction(3, 20) - shift,
                ),
            ),
            key=lambda item: item.destination_id,
        )
    )
    rows = (
        robust.IntervalSimplexRowV1(
            child_state,
            1,
            child_action,
            Fraction(1, 5),
            Fraction(1, 5),
            other_destination,
            child_masses,
        ),
        robust.IntervalSimplexRowV1(
            root_state,
            2,
            root_action,
            Fraction(3, 10),
            Fraction(3, 10),
            other_destination,
            root_masses,
        ),
    )
    model = robust.build_partial_support_model_v1(
        context_id=context_id,
        root_state_id=root_state,
        catalogues=catalogues,
        destinations=destinations,
        rows=rows,
        concretizer_entries=concretizers,
    )
    threshold = robust.RobustThresholdProfileV1(
        context_id,
        Fraction(1, 5),
        Fraction(1),
    )
    audit = robust.solve_quotient_robust_h2_v1(model, threshold)
    assert not audit.certified
    assert audit.failed_frontier is not None
    extra_catalogue = next(
        item for item in catalogues if item.state_id == extra_state
    )
    new_catalogues = {
        row_id: (
            (extra_catalogue,)
            if next(
                item for item in model.rows if item.row_id == row_id
            ).remaining_horizon
            == 2
            else ()
        )
        for row_id in audit.failed_frontier.selected_row_ids
    }
    metadata = selector.freeze_public_frontier_action_metadata_v2(
        model=model,
        audit=audit,
        support_epoch_id=_id(f"selector-support-epoch:{variant}"),
        newly_reachable_child_catalogues_by_row=new_catalogues,
    )
    return model, audit, threshold, metadata


def _registry(
    *,
    variant: int = 0,
    previous: selector.PreparedTargetSelectionV2 | None = None,
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    robust.RobustPlanAuditV1,
    robust.RobustThresholdProfileV1,
    selector.TargetCandidateRegistryV2,
]:
    model, audit, threshold, metadata = _fixture(variant=variant)
    registry = selector.freeze_target_candidate_registry_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        public_metadata=metadata,
        round_index=1 if previous is None else 2,
        previous_selection=previous,
    )
    return model, audit, threshold, registry


def _optimistic_resolution_registry() -> tuple[
    robust.PartialSupportIntervalModelV1,
    robust.RobustPlanAuditV1,
    robust.RobustThresholdProfileV1,
    selector.TargetCandidateRegistryV2,
]:
    base, _audit, threshold, _metadata = _fixture()
    destination_by_id = {
        item.destination_id: item for item in base.destinations
    }
    target = next(
        item for item in base.rows if item.remaining_horizon == 2
    )
    replacement_masses = []
    for mass in target.masses:
        category = destination_by_id[mass.destination_id].category
        if category is robust.DestinationCategory.ACTIVE_STATE:
            replacement_masses.append(
                _mass(mass.destination_id, Fraction(3, 5), Fraction(7, 10))
            )
        elif category is robust.DestinationCategory.OTHER:
            replacement_masses.append(
                _mass(mass.destination_id, Fraction(0), Fraction(3, 10))
            )
        else:
            replacement_masses.append(mass)
    replacement = replace(
        target,
        masses=tuple(
            sorted(
                replacement_masses,
                key=lambda item: item.destination_id,
            )
        ),
    )
    model = robust.build_partial_support_model_v1(
        context_id=base.context_id,
        root_state_id=base.root_state_id,
        catalogues=base.catalogues,
        destinations=base.destinations,
        rows=tuple(
            replacement if item.row_id == target.row_id else item
            for item in base.rows
        ),
        concretizer_entries=base.concretizer_entries,
    )
    audit = robust.solve_quotient_robust_h2_v1(model, threshold)
    assert audit.failed_frontier is not None
    row_state_ids = {item.state_id for item in model.rows}
    extra_catalogue = next(
        item
        for item in model.catalogues
        if item.state_id not in row_state_ids
    )
    row_by_id = {item.row_id: item for item in model.rows}
    metadata = selector.freeze_public_frontier_action_metadata_v2(
        model=model,
        audit=audit,
        support_epoch_id=_id("optimistic-resolution-support-epoch"),
        newly_reachable_child_catalogues_by_row={
            row_id: (
                (extra_catalogue,)
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
        public_metadata=metadata,
        round_index=1,
    )
    return model, audit, threshold, registry


def _consensus(
    feature_key: str,
    q: Fraction,
    label: str,
) -> source_v2.NonrectangularFeatureConsensusV2:
    contexts = tuple(sorted((_id(f"{label}:c1"), _id(f"{label}:c2"))))
    aggregates = tuple(sorted((_id(f"{label}:a1"), _id(f"{label}:a2"))))
    worst = max(Fraction(0), q - Fraction(1, 10))
    return source_v2.NonrectangularFeatureConsensusV2(
        feature_key,
        contexts,
        aggregates,
        Fraction(1, 10),
        q,
        worst,
        q - worst,
        False,
        source_v2.FeatureConsensusDispositionV2.APPLIED,
        Fraction(1, 2) + Fraction(3, 2) * q,
    )


def _source_binding(
    registry: selector.TargetCandidateRegistryV2,
) -> selector.VerifiedSourcePriorBindingV2:
    features = tuple(
        sorted(
            {item.feature.feature_key for item in registry.candidates}
        )
    )
    consensus = tuple(
        sorted(
            (
                _consensus(
                    feature,
                    Fraction(index + 1, len(features) + 1),
                    f"source-consensus:{index}",
                )
                for index, feature in enumerate(features)
            ),
            key=lambda item: item.consensus_id,
        )
    )
    return selector.VerifiedSourcePriorBindingV2(
        _id("verified-source-archive"),
        source_v2.FEATURE_SCHEMA_ID,
        consensus,
    )


def _prepare(
    arm: selector.TargetSelectionArmV2,
    *,
    variant: int = 0,
    previous: selector.PreparedTargetSelectionV2 | None = None,
) -> selector.PreparedTargetSelectionV2:
    model, audit, threshold, registry = _registry(
        variant=variant,
        previous=previous,
    )
    source = (
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
            _id("ood-rejected-prior"),
            _id("ood-feature-schema"),
        )
        if arm is selector.TargetSelectionArmV2.OOD_ABSTENTION
        else None
    )
    return selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=arm,
        source_prior=source,
        ood_abstention=abstention,
    )


def test_exact_selector_derives_gain_cost_order_and_native_zero_access() -> None:
    prepared = _prepare(selector.TargetSelectionArmV2.NO_PRIOR)
    assert prepared.sample_efficiency_gate_status == "NOT_RUN"
    assert prepared.authorization.frozen_before_target_access
    assert prepared.authorization.selected_candidate_id == (
        prepared.schedule.selected_candidate_id
    )
    assert {
        item.path: (item.value, item.observed)
        for item in prepared.access_log.native_zero_counters
    } == {
        path: (0, True) for path in selector.REQUIRED_NATIVE_ZERO_PATHS
    }
    by_candidate = {
        item.candidate_id: item
        for item in prepared.registry.candidates
    }
    for counterfactual in prepared.counterfactuals:
        candidate = by_candidate[counterfactual.candidate_id]
        assert counterfactual.base == (
            counterfactual.gain / candidate.exact_draw_upper
        )
        assert candidate.exact_draw_upper == (
            2_048
            + candidate.n_new_child_actions * (64 + 8_192)
        )
        assert counterfactual.to_document()["source_prior_inputs"] == []
    assert prepared.schedule.entries == tuple(
        sorted(prepared.schedule.entries, key=selector._ranking_key)
    )


def test_optimistic_resolution_is_one_row_mass_preserving_and_proposal_only() -> None:
    model, audit, threshold, registry = _optimistic_resolution_registry()
    prepared = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
    )
    counterfactual = next(
        item
        for item in prepared.counterfactuals
        if item.status
        is selector.CounterfactualEvaluationStatusV2
        .MASS_PRESERVING_OPTIMISTIC_RESOLUTION
    )
    source = next(
        item
        for item in model.rows
        if item.row_id == counterfactual.planner_row_id
    )
    resolved, destination_id, resolution_id = (
        selector._mass_preserving_optimistic_resolution_model(
            model,
            source.row_id,
        )
    )
    assert counterfactual.zero_other_model_id is None
    assert counterfactual.resolution_model_id == resolved.model_id
    assert counterfactual.resolution_destination_id == destination_id
    assert counterfactual.optimistic_resolution_id == resolution_id
    assert len(resolved.destinations) == len(model.destinations) + 1
    assert {
        item.destination_id: item for item in resolved.destinations
        if item.destination_id != destination_id
    } == {
        item.destination_id: item for item in model.destinations
    }
    new_destination = next(
        item
        for item in resolved.destinations
        if item.destination_id == destination_id
    )
    assert (
        new_destination.category
        is robust.DestinationCategory.SUCCESS_TERMINAL
    )
    row_key = lambda row: (
        row.state_id,
        row.remaining_horizon,
        row.action_id,
    )
    resolved_by_key = {row_key(item): item for item in resolved.rows}
    source_by_key = {row_key(item): item for item in model.rows}
    target_key = row_key(source)
    assert {
        key: value
        for key, value in resolved_by_key.items()
        if key != target_key
    } == {
        key: value
        for key, value in source_by_key.items()
        if key != target_key
    }
    resolved_target = resolved_by_key[target_key]
    source_masses = {
        item.destination_id: item for item in source.masses
    }
    resolved_masses = {
        item.destination_id: item for item in resolved_target.masses
    }
    source_other = source_masses[source.other_destination_id]
    assert resolved_masses[source.other_destination_id] == _mass(
        source.other_destination_id,
        Fraction(0),
        Fraction(0),
    )
    assert resolved_masses[destination_id] == _mass(
        destination_id,
        source_other.lower,
        source_other.upper,
    )
    assert {
        key: value
        for key, value in resolved_masses.items()
        if key not in (source.other_destination_id, destination_id)
    } == {
        key: value
        for key, value in source_masses.items()
        if key != source.other_destination_id
    }
    non_other_upper = sum(
        (
            item.upper
            for item in source.masses
            if item.destination_id != source.other_destination_id
        ),
        Fraction(0),
    )
    assert non_other_upper < 1
    semantics = counterfactual.to_document()["resolution_semantics"]
    assert semantics["proposal_only"] is True
    assert semantics["certificate_authority"] is False
    assert prepared.proposal_only is True
    assert (
        prepared.authorization.to_document()["certificate_authority"]
        is False
    )
    assert prepared.authorization.model_id == model.model_id
    assert prepared.authorization.model_id != resolved.model_id


def test_production_counterfactual_invariant_failure_never_becomes_infeasible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, audit, threshold, registry = _registry()

    def fail_closed(*_args, **_kwargs):
        raise robust.PartialSupportRobustPlannerInvariantViolation(
            "injected construction failure"
        )

    monkeypatch.setattr(
        selector,
        "_one_row_zero_other_model",
        fail_closed,
    )
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation,
        match="admissible zero-OTHER model construction failed",
    ):
        selector._counterfactuals(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
        )


def test_selector_api_rejects_caller_score_gain_and_forged_values() -> None:
    parameters = inspect.signature(
        selector.prepare_target_selection_v2
    ).parameters
    assert "gain" not in parameters
    assert "score" not in parameters
    assert "ranking" not in parameters
    prepared = _prepare(selector.TargetSelectionArmV2.NO_PRIOR)
    claim = prepared.counterfactuals[0]
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation
    ):
        replace(claim, gain=claim.gain + 1)
    score = prepared.scores[0]
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation
    ):
        replace(score, score=score.score + 1)


def test_zero_gain_is_ineligible_for_every_arm() -> None:
    prepared = _prepare(selector.TargetSelectionArmV2.NO_PRIOR)
    original = prepared.counterfactuals[0]
    zero = selector.OneRowCounterfactualGainV2(
        original.registry_id,
        original.candidate_id,
        original.model_id,
        original.audit_id,
        original.frontier_id,
        original.threshold_profile_id,
        original.support_epoch_id,
        original.planner_row_id,
        original.exact_draw_upper,
        selector.CounterfactualEvaluationStatusV2.EVALUATED,
        _id("zero-gain-counterfactual-model"),
        Fraction(-1, 10),
        Fraction(-1, 10),
        Fraction(0),
        Fraction(0),
    )
    assert not zero.eligible
    for arm, disposition in (
        (selector.TargetSelectionArmV2.NO_PRIOR, "NO_PRIOR"),
        (selector.TargetSelectionArmV2.OOD_ABSTENTION, "SCHEMA_MISMATCH"),
    ):
        score = selector.TargetArmRankingScoreV2(
            zero.counterfactual_id,
            zero.candidate_id,
            prepared.registry.candidates[0].feature.feature_key,
            arm,
            None,
            None,
            disposition,
            None,
            Fraction(0),
            Fraction(1),
            Fraction(0),
            Fraction(0),
            zero.exact_draw_upper,
            False,
        )
        assert not score.gain_eligible
        assert score.score == 0


def test_forbidden_pre_authorization_access_cannot_be_hidden() -> None:
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation
    ):
        selector.NativeZeroPreauthorizationCounterV2(
            "target_observer.calls",
            value=1,
        )
    prepared = _prepare(selector.TargetSelectionArmV2.NO_PRIOR)
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation
    ):
        replace(
            prepared.access_log,
            native_zero_counters=prepared.access_log.native_zero_counters[:-1],
        )


def test_wrong_arm_reverses_same_source_q_without_second_archive() -> None:
    model, audit, threshold, registry = _registry()
    source = _source_binding(registry)
    correct = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
        source_prior=source,
    )
    wrong = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
        source_prior=source,
    )
    assert correct.source_prior_binding == wrong.source_prior_binding
    correct_by_candidate = {
        item.candidate_id: item for item in correct.scores
    }
    wrong_by_candidate = {
        item.candidate_id: item for item in wrong.scores
    }
    for candidate_id, score in correct_by_candidate.items():
        reverse = wrong_by_candidate[candidate_id]
        assert score.source_feature_disposition == "APPLIED"
        assert reverse.source_feature_disposition == "APPLIED"
        assert score.source_midrank_q == reverse.source_midrank_q
        q = score.source_midrank_q
        assert q is not None
        assert score.multiplier == Fraction(1, 2) + Fraction(3, 2) * q
        assert reverse.multiplier == (
            Fraction(1, 2) + Fraction(3, 2) * (1 - q)
        )


def test_ood_and_no_prior_have_identical_arm_free_schedule_bytes() -> None:
    model, audit, threshold, registry = _registry()
    no_prior = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
    )
    ood = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.OOD_ABSTENTION,
        ood_abstention=selector.OodPriorTypedAbstentionV2(
            _id("ood-prior"),
            _id("different-feature-schema"),
        ),
    )
    assert no_prior.schedule.to_document() == ood.schedule.to_document()
    assert no_prior.schedule.schedule_core_id == ood.schedule.schedule_core_id
    assert no_prior.authorization.authorization_id != (
        ood.authorization.authorization_id
    )
    assert all(item.source_midrank_q is None for item in ood.scores)
    assert ood.ood_abstention is not None
    assert (
        ood.ood_abstention.to_document()["source_numerical_inputs"]
        == []
    )


def test_source_prior_cannot_enter_counterfactual_certificate_inputs() -> None:
    model, audit, threshold, registry = _registry()
    source = _source_binding(registry)
    source_run = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
        source_prior=source,
    )
    neutral_run = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
    )
    assert tuple(
        item.to_document() for item in source_run.counterfactuals
    ) == tuple(
        item.to_document() for item in neutral_run.counterfactuals
    )
    encoded = repr(
        [item.to_document() for item in source_run.counterfactuals]
    )
    assert source.source_prior_binding_id not in encoded
    assert source.archive_id not in encoded


def test_round_two_requires_fresh_model_audit_frontier_epoch_registry() -> None:
    first = _prepare(selector.TargetSelectionArmV2.NO_PRIOR)
    model2, audit2, threshold2, registry2 = _registry(
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
    assert second.registry.round_index == 2
    assert second.registry.registry_id != first.registry.registry_id
    assert second.registry.model_id != first.registry.model_id
    assert second.registry.audit_id != first.registry.audit_id
    assert second.registry.frontier_id != first.registry.frontier_id
    assert second.registry.support_epoch_id != (
        first.registry.support_epoch_id
    )
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation
    ):
        selector.prepare_target_selection_v2(
            model=model2,
            audit=audit2,
            threshold=threshold2,
            registry=first.registry,
            arm=selector.TargetSelectionArmV2.NO_PRIOR,
        )
    model1, audit1, threshold1, metadata1 = _fixture()
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation
    ):
        selector.freeze_target_candidate_registry_v2(
            model=model1,
            audit=audit1,
            threshold=threshold1,
            public_metadata=metadata1,
            round_index=2,
            previous_selection=first,
        )


def test_public_cardinality_and_total_caps_are_exact() -> None:
    assert selector.exact_preexecution_draw_upper_v2(0) == 2_048
    assert selector.exact_preexecution_draw_upper_v2(19) == 158_912
    assert selector.MAX_TWO_ROUND_DRAW_UPPER == 160_960
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation
    ):
        selector.exact_preexecution_draw_upper_v2(20)
    model, audit, _, _ = _fixture()
    frontier = audit.failed_frontier
    assert frontier is not None
    root_row = next(
        item
        for item in model.rows
        if item.remaining_horizon == 2
        and item.row_id in frontier.selected_row_ids
    )
    child_catalogue = next(
        item
        for item in model.catalogues
        if item.state_id != model.root_state_id
        and len(item.actions) == 1
    )
    with pytest.raises(
        selector.TargetPreauthorizationSelectorV2InvariantViolation
    ):
        selector.FrontierRowPublicActionMetadataV2(
            root_row.row_id,
            root_row.state_id,
            root_row.action_id,
            1,
            (child_catalogue,),
        )


def test_target_consumes_exact_preregistered_source_dispositions() -> None:
    prepared = _prepare(
        selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR
    )
    assert all(
        item.source_feature_disposition
        in selector.TARGET_FEATURE_DISPOSITIONS
        for item in prepared.scores
    )
    assert {
        item.source_feature_disposition for item in prepared.scores
    } == {"APPLIED"}
