from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import construction_accounting_registry_v5 as v5
from acfqp import construction_accounting_registry_v6 as v6
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V6_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V6_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V6_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V6_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
)


def _profiles():
    registry = v6.official_counter_registry_v6()
    stage = v6.official_stage_profile_v6(registry)
    comparison = v6.official_comparison_profile_v6(registry)
    actual = v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    return registry, stage, comparison, actual


def test_v6_is_strictly_additive_over_v5() -> None:
    registry, stage, comparison, actual = _profiles()
    base = v5.official_counter_registry_v5()
    assert len(registry.leaves) == 209
    assert len(registry.operational_leaves) == 182
    assert len(registry.required_paths) == 202
    assert len(stage.rules) == 10
    assert len(comparison.terms) == 182
    assert actual.terms == comparison.terms
    assert registry.v5_registry_id == base.registry_id
    assert all(
        registry.by_path[row.path].to_dict() == row.to_dict()
        for row in base.leaves
    )
    assert len(set(registry.by_path) - set(base.by_path)) == 58


def test_exact_v6_addition_stage_cardinalities() -> None:
    registry, stage, _comparison, _actual = _profiles()
    base_paths = set(v5.official_counter_registry_v5().by_path)
    additions = set(registry.by_path) - base_paths
    expected = {
        v6.ConstructionStageKindV6.INITIAL_ACQUISITION: 7,
        v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION: 7,
        v6.ConstructionStageKindV6.INITIAL_MODEL_BUILD: 10,
        v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING: 20,
        (
            v6.ConstructionStageKindV6
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ): 14,
    }
    for stage_kind, count in expected.items():
        owned = additions & set(
            stage.by_stage[stage_kind].allowed_nonzero_paths
        )
        assert len(owned) == count
    assert sum(expected.values()) == len(additions)


def test_engine_and_sequential_replacements_have_strict_owners() -> None:
    registry, _stage, _comparison, _actual = _profiles()
    engine_paths = {
        "acquisition.initial_engine_ground_draws",
        "acquisition.initial_engine_random_word_calls",
        "acquisition.initial_engine_rejections",
        "acquisition.initial_engine_stream_initialization_merges",
        "acquisition.incremental_engine_ground_draws",
        "closure.reconciliation_engine_ground_draws",
    }
    assert all(
        registry.by_path[path].owner == "h2_graph_transition_engine_v1"
        for path in engine_paths
    )
    for path in (
        "acquisition.initial_engine_ground_draws",
        "acquisition.initial_engine_stream_initialization_merges",
        "closure.reconciliation_engine_ground_draws",
    ):
        assert registry.by_path[path].comparison_axis == (
            "kernel_transition_calls"
        )
    for path in (
        "acquisition.initial_engine_rejections",
        "acquisition.incremental_engine_rejections",
        "closure.reconciliation_engine_rejections",
    ):
        leaf = registry.by_path[path]
        assert leaf.lane.value == "diagnostic"
        assert leaf.comparison_axis is None

    sequential_paths = {
        "build.initial_sequential_exact_likelihood_comparisons",
        "build.initial_sequential_interval_log_search_evaluations",
        "build.open_checkpoint_sequential_exact_likelihood_comparisons",
        (
            "closure.reconciliation_"
            "sequential_interval_log_search_evaluations"
        ),
    }
    assert all(
        registry.by_path[path].owner
        == "sequential_bernoulli_acquisition_v1"
        for path in sequential_paths
    )


def test_cache_and_missing_operation_families_are_typed() -> None:
    registry, _stage, _comparison, _actual = _profiles()
    for prefix in (
        "build.initial",
        "build.open_checkpoint",
        "closure.reconciliation",
    ):
        lookup = registry.by_path[f"{prefix}_confidence_cache_lookups"]
        hit = registry.by_path[f"{prefix}_confidence_cache_hits"]
        miss = registry.by_path[f"{prefix}_confidence_cache_misses"]
        assert lookup.lane.value == "operational"
        assert lookup.comparison_axis == "nonkernel_compute_events"
        assert hit.lane.value == miss.lane.value == "diagnostic"
        assert hit.comparison_axis is miss.comparison_axis is None

    required = {
        "acquisition.initial_observer_accumulator_updates",
        "acquisition.initial_signed_batches_materialized",
        "acquisition.initial_signed_batches_committed",
        "build.initial_live_model_row_source_bindings_built",
        "build.initial_batch_v2_replay_checkpoint_evaluations",
        "build.initial_batch_v2_replay_interval_reconstructions",
        "build.initial_batch_v2_option_metric_evaluations",
        "build.initial_batch_v2_policy_assignment_cap_checks",
        "build.open_checkpoint_live_model_outcome_projections",
        "build.open_checkpoint_live_model_support_descriptors_compiled",
    }
    assert required <= set(registry.by_path)


def test_open_multiround_successors_are_routed_not_globally_forbidden() -> None:
    registry, stage, _comparison, _actual = _profiles()
    open_acquisition = stage.by_stage[
        v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION
    ]
    open_checkpoint = stage.by_stage[
        v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING
    ]
    assert "acquisition.incremental_engine_ground_draws" in (
        open_acquisition.allowed_nonzero_paths
    )
    assert "acquisition.incremental_signed_batches_committed" in (
        open_acquisition.allowed_nonzero_paths
    )
    assert "build.open_checkpoint_batch_v2_row_behaviors_compiled" in (
        open_checkpoint.allowed_nonzero_paths
    )
    assert "build.open_checkpoint_live_model_outcome_projections" in (
        open_checkpoint.allowed_nonzero_paths
    )
    for path in (
        "acquisition.initial_observer_accepted_draws",
        "build.initial_exact_likelihood_comparisons",
        "closure.reconciliation_private_replay_ground_steps",
    ):
        assert registry.by_path[path].to_dict() == (
            v5.official_counter_registry_v5().by_path[path].to_dict()
        )


def test_every_v6_operational_leaf_projects_once() -> None:
    registry, _stage, comparison, actual = _profiles()
    sources = [row.source_leaf for row in comparison.terms]
    assert sources == [row.path for row in registry.operational_leaves]
    assert len(sources) == len(set(sources)) == 182
    assert all(row.coefficient == 1 for row in comparison.terms)
    assert actual.terms == comparison.terms


def test_v6_remains_schema_only_and_gate_locked() -> None:
    registry, stage, _comparison, _actual = _profiles()
    document = registry.to_document()
    assert document["runtime_operation_emitters_installed"] is False
    assert document["runtime_owner_match_verified"] is False
    assert document["runtime_stage_attribution_verified"] is False
    assert document["operation_family_completeness_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["counter_completeness_gate_passed"] is False
    assert document["workload_economics_gate_passed"] is False
    assert stage.to_document()[
        "open_incremental_owner_corrections_routed"
    ] is True
    assert stage.to_document()[
        "open_checkpoint_owner_corrections_routed"
    ] is True


def test_v6_domains_and_tamper_guards() -> None:
    expected = {
        CONSTRUCTION_COUNTER_REGISTRY_V6_DOMAIN,
        CONSTRUCTION_STAGE_PROFILE_V6_DOMAIN,
        CONSTRUCTION_COMPARISON_PROFILE_V6_DOMAIN,
        CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V6_DOMAIN,
    }
    assert expected <= PHASE3E_DOMAIN_TAGS
    registry, stage, comparison, actual = _profiles()
    assert len(
        {
            registry.registry_id,
            stage.stage_profile_id,
            comparison.comparison_profile_id,
            actual.actual_projection_profile_id,
        }
    ) == 4
    forged = replace(registry, leaves=registry.leaves[:-1])
    with pytest.raises(v6.ConstructionAccountingRegistryV6Error):
        forged.validate_official_catalogue()
