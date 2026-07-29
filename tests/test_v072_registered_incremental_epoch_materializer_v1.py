from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import (
    v072_registered_incremental_epoch_materializer_v1 as materializer,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _cold_epoch(
    *labels: str,
) -> materializer.RegistrationDisjointIncrementalEpochV1:
    return materializer.freeze_registration_disjoint_cold_epoch_v1(
        cold_acquisitions=tuple(
            materializer.RegistrationDisjointIncrementalAcquisitionV1(
                _id(f"row-{label}"),
                0,
                materializer.RegistrationDisjointAcquisitionKindV1.COLD,
            )
            for label in labels
        )
    )


def _history_ids(
    epoch: materializer.RegistrationDisjointIncrementalEpochV1,
) -> tuple[str, ...]:
    return tuple(
        item.acquisition_id for item in epoch.acquisition_history
    )


def _row(
    epoch: materializer.RegistrationDisjointIncrementalEpochV1,
    label: str,
    *,
    latest: bool = True,
) -> materializer.RegistrationDisjointIncrementalAcquisitionV1:
    candidates = tuple(
        item
        for item in epoch.acquisition_history
        if item.row_binding_id == _id(f"row-{label}")
    )
    assert candidates
    return (
        max(candidates, key=lambda item: item.round_index)
        if latest
        else min(candidates, key=lambda item: item.round_index)
    )


def _selector(
    prior: materializer.RegistrationDisjointIncrementalEpochV1,
    *,
    parent_label: str,
    new_child_labels: tuple[str, ...],
) -> materializer.RegistrationDisjointSelectorClosureV1:
    parent = _row(prior, parent_label)
    return materializer.RegistrationDisjointSelectorClosureV1(
        prior.round_index + 1,
        prior.epoch_id,
        prior.frontier_id,
        _history_ids(prior),
        parent.acquisition_id,
        parent.row_binding_id,
        tuple(sorted(_id(f"row-{label}") for label in new_child_labels)),
    )


def _round_one(
) -> tuple[
    materializer.RegistrationDisjointIncrementalEpochV1,
    materializer.RegistrationDisjointSelectorClosureV1,
    materializer.RegistrationDisjointIncrementalEpochV1,
]:
    cold = _cold_epoch("A", "B", "C")
    selected = _selector(
        cold,
        parent_label="A",
        new_child_labels=("D", "E"),
    )
    result = (
        materializer
        .materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=cold,
            selector_closure=selected,
        )
    )
    return cold, selected, result


def test_production_api_accepts_only_exact_chain_bound_inputs() -> None:
    signature = inspect.signature(
        materializer.materialize_registered_incremental_h2_model_epoch_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
        "prior_epoch",
        "selector_closure",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in signature.parameters.values()
    )
    forbidden = {
        "rows",
        "observations",
        "law",
        "seed",
        "counts",
        "status",
        "callback",
        "projection",
        "model",
        "policy",
    }
    assert forbidden.isdisjoint(signature.parameters)
    synthetic_signature = inspect.signature(
        materializer
        .materialize_registration_disjoint_incremental_epoch_v1
    )
    assert tuple(synthetic_signature.parameters) == (
        "prior_epoch",
        "selector_closure",
    )


def test_invalid_production_gate_has_zero_registered_target_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("TARGET_ACCESS")
        raise AssertionError("invalid materializer gate touched target")

    for module, name in (
        (observer, "_environment_law"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (observer, "evaluation_only_exact_atoms_v2"),
        (observer.AnchorGatedHeldoutTransitionStreamV2, "draw"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    with pytest.raises(
        materializer.RegisteredIncrementalEpochMaterializerLockedV1
    ) as captured:
        materializer.materialize_registered_incremental_h2_model_epoch_v1(
            authority_chain=object(),  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            occurrence_plan=object(),  # type: ignore[arg-type]
            context=object(),  # type: ignore[arg-type]
            prior_epoch=object(),  # type: ignore[arg-type]
            selector_closure=object(),  # type: ignore[arg-type]
        )
    assert captured.value.access_audit == materializer.ZERO_ACCESS_AUDIT
    assert captured.value.access_audit.target_access_started is False
    assert calls == []


def test_round_one_materializes_promotion_and_every_complete_new_child() -> None:
    cold, selected, result = _round_one()
    cold_snapshot = (
        cold.epoch_id,
        cold.acquisition_history,
        cold.active_acquisition_ids,
    )
    old_a = _row(cold, "A")
    new_rows = {
        _id("row-D"),
        _id("row-E"),
    }
    new_values = tuple(
        item
        for item in result.acquisition_history
        if item.acquisition_id in result.new_acquisition_ids
    )
    promotions = tuple(
        item
        for item in new_values
        if item.kind
        is materializer.RegistrationDisjointAcquisitionKindV1.PROMOTION
    )
    children = tuple(
        item
        for item in new_values
        if item.kind
        is materializer.RegistrationDisjointAcquisitionKindV1.NEW_CHILD
    )

    assert result.round_index == 1
    assert result.predecessor_epoch_id == cold.epoch_id
    assert result.predecessor_frontier_id is None
    assert result.frontier_id == selected.frontier_id
    assert len(result.acquisition_history) == 6
    assert len(result.active_acquisition_ids) == 5
    assert len(promotions) == 1
    assert promotions[0].parent_acquisition_id == old_a.acquisition_id
    assert promotions[0].row_binding_id == old_a.row_binding_id
    assert {item.row_binding_id for item in children} == new_rows
    assert set(selected.new_child_row_binding_ids) == new_rows
    assert old_a.acquisition_id in _history_ids(result)
    assert old_a.acquisition_id not in result.active_acquisition_ids
    assert promotions[0].acquisition_id in result.active_acquisition_ids
    assert len(result.closure_id) == 64
    assert len(result.closure_verification_id) == 64
    assert len(result.model_pair_id) == 64
    assert len(result.model_verification_id) == 64

    expected_producer = (
        prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
        + 2
        * (
            prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
            + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
        )
    )
    assert result.work is not None
    assert result.work.acquisition_calls == 3
    assert result.work.independent_replay_calls == 3
    assert result.work.producer_draws == expected_producer
    assert result.work.independent_replay_draws == expected_producer
    assert result.work.total_observer_draws == 2 * expected_producer
    assert result.work.historical_acquisition_count == 6
    assert result.work.active_physical_row_count == 5
    assert result.work.superseded_historical_version_count == 1
    assert result.work.registered_target_accesses == 0
    assert (
        cold.epoch_id,
        cold.acquisition_history,
        cold.active_acquisition_ids,
    ) == cold_snapshot


def test_round_two_requires_and_retains_strict_dependent_lineage() -> None:
    _cold, first_selector, first = _round_one()
    second_selector = _selector(
        first,
        parent_label="D",
        new_child_labels=("F",),
    )
    parent = _row(first, "D")
    second = (
        materializer
        .materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=first,
            selector_closure=second_selector,
        )
    )

    assert second.round_index == 2
    assert second.predecessor_epoch_id == first.epoch_id
    assert second.predecessor_frontier_id == first.frontier_id
    assert second.frontier_id == second_selector.frontier_id
    assert set(first_selector.supporting_acquisition_ids) < set(
        second_selector.supporting_acquisition_ids
    )
    assert second_selector.supporting_acquisition_ids == _history_ids(first)
    assert set(_history_ids(first)).issubset(_history_ids(second))
    assert len(second.acquisition_history) == 8
    assert len(second.active_acquisition_ids) == 6
    assert parent.acquisition_id in _history_ids(second)
    assert parent.acquisition_id not in second.active_acquisition_ids
    promotion = next(
        item
        for item in second.acquisition_history
        if item.acquisition_id in second.new_acquisition_ids
        and item.kind
        is materializer.RegistrationDisjointAcquisitionKindV1.PROMOTION
    )
    assert promotion.parent_acquisition_id == parent.acquisition_id
    assert promotion.row_binding_id == parent.row_binding_id
    assert promotion.acquisition_id in second.active_acquisition_ids
    assert second.work is not None
    expected_producer = (
        prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
        + prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
        + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
    )
    assert second.work.producer_draws == expected_producer
    assert second.work.total_observer_draws == 2 * expected_producer
    assert second.work.superseded_historical_version_count == 2


def test_round_two_rejects_fresh_frontier_or_incomplete_inventory() -> None:
    _cold, _first_selector, first = _round_one()
    valid = _selector(
        first,
        parent_label="D",
        new_child_labels=("F",),
    )
    wrong_predecessor = replace(
        valid,
        predecessor_frontier_id=_id("fresh-unrelated-frontier"),
    )
    with pytest.raises(
        materializer.V072RegisteredIncrementalEpochMaterializerViolation,
        match="strict extension",
    ):
        materializer.materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=first,
            selector_closure=wrong_predecessor,
        )

    incomplete_support = tuple(
        item
        for item in valid.supporting_acquisition_ids
        if item != valid.promotion_parent_acquisition_id
    )
    replacement_parent = incomplete_support[0]
    attacked = materializer.RegistrationDisjointSelectorClosureV1(
        2,
        first.epoch_id,
        first.frontier_id,
        incomplete_support,
        replacement_parent,
        next(
            item.row_binding_id
            for item in first.acquisition_history
            if item.acquisition_id == replacement_parent
        ),
        valid.new_child_row_binding_ids,
    )
    with pytest.raises(
        materializer.V072RegisteredIncrementalEpochMaterializerViolation,
        match="strict extension",
    ):
        materializer.materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=first,
            selector_closure=attacked,
        )


def test_new_child_cannot_replace_an_active_physical_row() -> None:
    cold = _cold_epoch("A", "B", "C")
    parent = _row(cold, "A")
    attacked = materializer.RegistrationDisjointSelectorClosureV1(
        1,
        cold.epoch_id,
        None,
        _history_ids(cold),
        parent.acquisition_id,
        parent.row_binding_id,
        (_id("row-B"),),
    )
    with pytest.raises(
        materializer.V072RegisteredIncrementalEpochMaterializerViolation,
        match="replaces an active row",
    ):
        materializer.materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=cold,
            selector_closure=attacked,
        )


def test_round_two_cannot_promote_a_stale_historical_version() -> None:
    _cold, _first_selector, first = _round_one()
    stale = _row(first, "A", latest=False)
    attacked = materializer.RegistrationDisjointSelectorClosureV1(
        2,
        first.epoch_id,
        first.frontier_id,
        _history_ids(first),
        stale.acquisition_id,
        stale.row_binding_id,
        (_id("row-F"),),
    )
    with pytest.raises(
        materializer.V072RegisteredIncrementalEpochMaterializerViolation,
        match="latest physical row",
    ):
        materializer.materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=first,
            selector_closure=attacked,
        )


def test_synthetic_documents_cannot_claim_registered_target_access() -> None:
    _cold, _selected, result = _round_one()
    assert result.work is not None
    assert result.work.registered_target_accesses == 0
    assert result.work.caller_rows_status_counts_callbacks == 0
    assert all(
        item.replay_id != item.acquisition_id
        for item in result.acquisition_history
    )
    assert result.epoch_id not in {
        result.closure_id,
        result.closure_verification_id,
        result.model_pair_id,
        result.model_verification_id,
    }
