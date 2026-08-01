from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import construction_accounting_registry_v3 as v3
from acfqp import construction_accounting_registry_v4 as v4


def _profiles():
    registry = v4.official_counter_registry_v4()
    stage = v4.official_stage_profile_v4(registry)
    comparison = v4.official_comparison_profile_v4(registry)
    actual = v4.official_actual_projection_profile_v4(
        registry, comparison
    )
    return registry, stage, comparison, actual


def test_v4_cardinalities_and_exact_v3_prefix_are_frozen() -> None:
    registry, stage, comparison, actual = _profiles()
    base = v3.official_counter_registry_v3()
    assert len(registry.leaves) == 124
    assert len(registry.operational_leaves) == 106
    assert len(registry.required_paths) == 117
    assert registry.v3_registry_id == base.registry_id
    assert set(base.by_path) <= set(registry.by_path)
    assert all(
        registry.by_path[row.path].to_dict() == row.to_dict()
        for row in base.leaves
    )
    additions = tuple(
        row for row in registry.leaves if row.path not in base.by_path
    )
    assert len(additions) == 8
    assert sum(row.lane.value == "operational" for row in additions) == 7
    assert all(row.required for row in additions)
    assert len(stage.rules) == 10
    assert len(comparison.terms) == 106
    assert actual.terms == comparison.terms


def test_v4_additions_are_exact_and_have_native_semantics() -> None:
    registry, _stage, _comparison, _actual = _profiles()
    base = v3.official_counter_registry_v3()
    assert set(registry.by_path) - set(base.by_path) == {
        "build.initial_outcome_projections",
        "build.initial_proposal_entries_bound",
        "build.open_checkpoint_outcome_projections",
        "build.open_checkpoint_proposal_entries_bound",
        "closure.reconciliation_private_replay_ground_steps",
        "closure.reconciliation_private_replay_random_word_calls",
        "closure.reconciliation_private_replay_rejections",
        "closure.reconciliation_private_replay_outcome_aggregate_rows",
    }
    assert registry.by_path[
        "closure.reconciliation_private_replay_ground_steps"
    ].comparison_axis == "kernel_transition_calls"
    assert registry.by_path[
        "closure.reconciliation_private_replay_rejections"
    ].lane.value == "diagnostic"
    for path in (
        "build.initial_outcome_projections",
        "build.initial_proposal_entries_bound",
        "build.open_checkpoint_outcome_projections",
        "build.open_checkpoint_proposal_entries_bound",
        "closure.reconciliation_private_replay_random_word_calls",
        "closure.reconciliation_private_replay_outcome_aggregate_rows",
    ):
        assert registry.by_path[path].lane.value == "operational"
        assert (
            registry.by_path[path].comparison_axis
            == "nonkernel_compute_events"
        )


def test_v4_stage_ownership_is_additive_and_exact() -> None:
    _registry, stage, _comparison, _actual = _profiles()
    base = v3.official_stage_profile_v3()
    base_by_stage = {
        row.stage_kind: set(row.allowed_nonzero_paths)
        for row in base.rules
    }
    current_by_stage = {
        row.stage_kind: set(row.allowed_nonzero_paths)
        for row in stage.rules
    }
    initial = v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD
    checkpoint = (
        v4.ConstructionStageKindV4.OPEN_CHECKPOINT_REPLANNING
    )
    closed = (
        v4.ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    )
    assert current_by_stage[initial] - base_by_stage[initial] == {
        "build.initial_outcome_projections",
        "build.initial_proposal_entries_bound",
    }
    assert current_by_stage[checkpoint] - base_by_stage[checkpoint] == {
        "build.open_checkpoint_outcome_projections",
        "build.open_checkpoint_proposal_entries_bound",
    }
    assert current_by_stage[closed] - base_by_stage[closed] == {
        "closure.reconciliation_private_replay_ground_steps",
        "closure.reconciliation_private_replay_random_word_calls",
        "closure.reconciliation_private_replay_rejections",
        "closure.reconciliation_private_replay_outcome_aggregate_rows",
    }
    for kind in v4.ConstructionStageKindV4:
        if kind not in {initial, checkpoint, closed}:
            assert current_by_stage[kind] == base_by_stage[kind]

    initial_acquisition = current_by_stage[
        v4.ConstructionStageKindV4.INITIAL_ACQUISITION
    ]
    open_acquisition = current_by_stage[
        v4.ConstructionStageKindV4.OPEN_INCREMENTAL_ACQUISITION
    ]
    assert "acquisition.initial_outcome_projections" in initial_acquisition
    assert (
        "acquisition.initial_proposal_entries_bound"
        in initial_acquisition
    )
    assert (
        "acquisition.incremental_outcome_projections"
        in open_acquisition
    )
    assert (
        "acquisition.incremental_proposal_entries_bound"
        in open_acquisition
    )


def test_v4_projection_charges_each_operational_leaf_once() -> None:
    registry, _stage, comparison, actual = _profiles()
    assert {row.source_leaf for row in comparison.terms} == {
        row.path for row in registry.operational_leaves
    }
    assert len(comparison.terms) == len(registry.operational_leaves)
    assert len({row.source_leaf for row in comparison.terms}) == 106
    assert all(row.coefficient == 1 for row in comparison.terms)
    assert (
        "closure.reconciliation_private_replay_rejections"
        not in {row.source_leaf for row in comparison.terms}
    )
    kernel = {
        row.source_leaf
        for row in comparison.terms
        if row.target_axis == "kernel_transition_calls"
    }
    assert "closure.reconciliation_private_replay_ground_steps" in kernel
    assert actual.terms == comparison.terms
    assert comparison.to_document()["scalar_cost_defined"] is False


def test_v4_profiles_reject_tampering() -> None:
    registry, stage, comparison, actual = _profiles()
    with pytest.raises(v4.ConstructionAccountingRegistryV4Error):
        replace(
            registry, leaves=registry.leaves[:-1]
        ).validate_official_catalogue()
    with pytest.raises(v4.ConstructionAccountingRegistryV4Error):
        replace(stage, rules=stage.rules[:-1])
    with pytest.raises(v4.ConstructionAccountingRegistryV4Error):
        replace(
            comparison, terms=comparison.terms[:-1]
        ).validate(registry)
    with pytest.raises(v4.ConstructionAccountingRegistryV4Error):
        replace(actual, terms=actual.terms[:-1]).validate(
            registry, comparison
        )


def test_v4_freeze_emits_profiles_only() -> None:
    frozen = v4.freeze_construction_accounting_registry_v4()
    assert set(frozen) == {
        "counter_registry",
        "stage_profile",
        "comparison_profile",
        "actual_projection_profile",
    }
    rendered = repr(frozen)
    assert "counter_record_id" not in rendered
    assert "work_vector_id" not in rendered
    assert "comparison_vector_id" not in rendered
