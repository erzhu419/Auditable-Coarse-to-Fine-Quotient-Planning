from __future__ import annotations

from dataclasses import replace
import copy

import pytest

from acfqp import construction_accounting_registry_v3 as v3
from acfqp import construction_accounting_v2 as v2
from acfqp import v075_batch_native_statistical_backend_v1 as batch
from acfqp import v075_integrated_direct_occurrence_pipeline_v1 as direct
from acfqp import v075_learned_support_quotient_planners_v1 as planner
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as route


def _profiles():
    registry = v3.official_counter_registry_v3()
    stage = v3.official_stage_profile_v3(registry)
    comparison = v3.official_comparison_profile_v3(registry)
    actual = v3.official_actual_projection_profile_v3(
        registry, comparison
    )
    migration = v3.official_legacy_migration_profile_v3(registry)
    return registry, stage, comparison, actual, migration


def test_v2_prefix_is_exact_and_successor_cardinality_is_frozen() -> None:
    registry, stage, comparison, actual, migration = _profiles()
    base = v2.official_counter_registry_v2()
    assert len(registry.leaves) == 116
    assert len(registry.operational_leaves) == 99
    assert len(registry.required_paths) == 109
    assert registry.v2_registry_id == base.registry_id
    assert registry.leaves[:0] == ()
    assert set(base.by_path) <= set(registry.by_path)
    assert all(
        registry.by_path[row.path].to_dict() == row.to_dict()
        for row in base.leaves
    )
    assert len(stage.rules) == 10
    assert len(comparison.terms) == 99
    assert actual.terms == comparison.terms
    assert len(migration.rows) == 87


def test_v3_ids_are_frozen() -> None:
    registry, stage, comparison, actual, migration = _profiles()
    assert registry.registry_id == (
        "09e48ea7f3c666de5e58bcb024e074cd"
        "887739daff598a4bf13c2e8a1a5e552e"
    )
    assert stage.stage_profile_id == (
        "d7f04727e9742047df2baadeb721675d"
        "2b59ad9464977af457eb6472b58fd5a6"
    )
    assert comparison.comparison_profile_id == (
        "cb0cd03d6ea5b45b79a66f6f057ed278"
        "fe21431caf05fc1f4430f4cb8b2e11b2"
    )
    assert actual.actual_projection_profile_id == (
        "1b04b5f148fc8bb173a1482d7e420709"
        "7c1c7e0c54e6398c366163253f139266"
    )
    assert migration.migration_profile_id == (
        "dc8e34ec371195d60f20ee928228555b"
        "0b35164745a6bec3b5ecae3d749006ab"
    )


def test_new_operational_families_have_stage_specific_native_leaves() -> None:
    registry, _stage, _comparison, _actual, _migration = _profiles()
    groups = {
        "confidence_event_evaluations",
        "exact_likelihood_comparisons",
        "interval_lp_allocations",
        "dominance_comparisons",
        "deterministic_tie_breaks",
        "quotient_cells_compiled",
        "semantic_actions_compiled",
        "concretizer_ground_actions_compiled",
    }
    for family in groups:
        assert f"build.initial_{family}" in registry.by_path
        assert f"build.open_checkpoint_{family}" in registry.by_path
        assert f"closure.reconciliation_{family}" in registry.by_path
    for family in (
        "outcome_projections",
        "proposal_entries_bound",
        "child_catalogues_built",
    ):
        assert f"acquisition.initial_{family}" in registry.by_path
        assert f"acquisition.incremental_{family}" in registry.by_path
        assert f"closure.reconciliation_{family}" in registry.by_path
    additions = tuple(
        row
        for row in registry.leaves
        if row.path not in v2.official_counter_registry_v2().by_path
    )
    assert len(additions) == 47
    assert sum(row.lane.value == "operational" for row in additions) == 46
    assert all(row.required for row in additions)
    assert all(
        row.comparison_axis == "nonkernel_compute_events"
        for row in additions
        if row.lane.value == "operational"
        and "accepted_draws" not in row.path
    )
    assert registry.by_path[
        "acquisition.incremental_observer_accepted_draws"
    ].comparison_axis == "kernel_transition_calls"
    assert registry.by_path[
        "acquisition.incremental_observer_rejections"
    ].lane.value == "diagnostic"
    assert "audit.failed_child_catalogues_built" in registry.by_path


def test_open_stages_cannot_be_relabelled_as_initial_or_closed() -> None:
    registry, stage, _comparison, _actual, _migration = _profiles()
    initial_acquisition = set(
        stage.by_stage[
            v3.ConstructionStageKindV3.INITIAL_ACQUISITION
        ].allowed_nonzero_paths
    )
    open_acquisition = set(
        stage.by_stage[
            v3.ConstructionStageKindV3.OPEN_INCREMENTAL_ACQUISITION
        ].allowed_nonzero_paths
    )
    initial_build = set(
        stage.by_stage[
            v3.ConstructionStageKindV3.INITIAL_MODEL_BUILD
        ].allowed_nonzero_paths
    )
    open_checkpoint = set(
        stage.by_stage[
            v3.ConstructionStageKindV3.OPEN_CHECKPOINT_REPLANNING
        ].allowed_nonzero_paths
    )
    closed = set(
        stage.by_stage[
            v3.ConstructionStageKindV3
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ].allowed_nonzero_paths
    )
    failed = set(
        stage.by_stage[
            v3.ConstructionStageKindV3.FAILED_ABSTRACT_PREFIX
        ].allowed_nonzero_paths
    )
    assert (
        "acquisition.incremental_observer_accepted_draws"
        in open_acquisition
    )
    assert (
        "acquisition.incremental_observer_accepted_draws"
        not in initial_acquisition | closed
    )
    assert (
        "build.open_checkpoint_dominance_comparisons"
        in open_checkpoint
    )
    assert (
        "build.open_checkpoint_dominance_comparisons"
        not in initial_build | closed
    )
    assert "audit.failed_child_catalogues_built" in failed
    assert "audit.failed_child_catalogues_built" not in (
        initial_acquisition | open_acquisition | initial_build | closed
    )
    assert set().union(
        *(set(row.allowed_nonzero_paths) for row in stage.rules)
    ) <= set(registry.required_paths)


def test_interval_row_compatibility_path_uses_its_registered_unit() -> None:
    registry, stage, _comparison, _actual, _migration = _profiles()
    for path in (
        "build.initial_interval_row_evaluations",
        "build.open_checkpoint_interval_row_evaluations",
        "closure.reconciliation_interval_row_evaluations",
    ):
        assert registry.by_path[path].unit == "row_behavior_evaluations"
    document = stage.to_document()
    assert document[
        "interval_row_path_uses_registered_row_behavior_unit"
    ] is True
    assert document[
        "initial_build_owns_root_epoch_compile_and_plan"
    ] is True
    assert document[
        "failed_abstract_prefix_owns_verified_child_audit_only"
    ] is True


def test_legacy_partition_is_complete_disjoint_and_never_translates() -> None:
    registry, _stage, _comparison, _actual, migration = _profiles()
    catalogues = (
        route.COUNTER_PATHS,
        batch.BATCH_NATIVE_COUNTER_PATHS,
        planner.PLANNER_COUNTER_PATHS,
        worker.REGISTERED_COUNTER_PATHS,
        direct.DIRECT_PIPELINE_COUNTER_PATHS,
    )
    legacy = set().union(*(set(paths) for paths in catalogues))
    assert sum(len(paths) for paths in catalogues) == 95
    assert len(legacy) == 87
    assert {row.legacy_path for row in migration.rows} == legacy
    counts = migration.to_document()["disposition_counts"]
    assert counts == {
        "REINSTRUMENT_EXISTING_FAMILY": 7,
        "DECOMPOSE_AT_NATIVE_SITES": 18,
        "DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES": 51,
        "REGISTER_NEW_OPERATIONAL_FAMILY": 11,
    }
    assert all(
        set(row.target_paths) <= set(registry.by_path)
        for row in migration.rows
    )
    assert all(
        item["historical_summary_translation_allowed"] is False
        for item in migration.to_document()["rows"]
    )
    assert migration.to_document()[
        "operation_site_instrumentation_complete"
    ] is False
    assert migration.to_document()[
        "derived_formula_registry_complete"
    ] is False


def test_duplicate_legacy_views_do_not_become_duplicate_native_charges() -> None:
    _registry, _stage, _comparison, _actual, migration = _profiles()
    rows = {row.legacy_path: row for row in migration.rows}
    for path in (
        "adaptive.route_attempts",
        "direct.route_attempts",
        "common.confidence_event_evaluations",
        "common.exact_likelihood_comparisons",
        "common.log_search_evaluations",
        "common.per_draw_capabilities_materialized",
        "common.request_reconstructions",
        "common.statistical_rows_built",
    ):
        assert len(rows[path].source_catalogues) == 2
    assert rows[
        "common.confidence_event_evaluations"
    ].disposition is (
        v3.LegacyMigrationDispositionV3
        .REGISTER_NEW_OPERATIONAL_FAMILY
    )
    assert rows[
        "adaptive.route_attempts"
    ].disposition is (
        v3.LegacyMigrationDispositionV3
        .DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES
    )


def test_comparison_projects_each_operational_leaf_once_without_scalar() -> None:
    registry, _stage, comparison, actual, _migration = _profiles()
    assert tuple(row.name for row in comparison.axes) == (
        "kernel_transition_calls",
        "nonkernel_compute_events",
        "output_bytes",
        "peak_mounted_bytes",
        "peak_working_bytes",
        "process_launches",
        "read_bytes",
        "staged_bytes",
    )
    assert {row.source_leaf for row in comparison.terms} == {
        row.path for row in registry.operational_leaves
    }
    assert len(comparison.terms) == len(registry.operational_leaves)
    assert all(row.coefficient == 1 for row in comparison.terms)
    assert actual.terms == comparison.terms
    assert comparison.to_document()["scalar_cost_defined"] is False


def test_registry_profile_tampering_fails() -> None:
    registry, stage, comparison, actual, migration = _profiles()
    leaf = registry.leaves[-1]
    forged_leaf = replace(leaf, unit="forged_units")
    forged_registry = replace(
        registry,
        leaves=tuple(sorted(
            (*registry.leaves[:-1], forged_leaf),
            key=lambda row: row.path,
        )),
    )
    with pytest.raises(v3.ConstructionAccountingRegistryV3Error):
        forged_registry.validate_official_catalogue()
    with pytest.raises(v3.ConstructionAccountingRegistryV3Error):
        replace(
            stage,
            rules=stage.rules[:-1],
        )
    with pytest.raises(v3.ConstructionAccountingRegistryV3Error):
        replace(
            comparison,
            terms=comparison.terms[:-1],
        ).validate(registry)
    with pytest.raises(v3.ConstructionAccountingRegistryV3Error):
        replace(
            actual,
            terms=actual.terms[:-1],
        ).validate(registry, comparison)
    attacked_rows = list(migration.rows)
    attacked_rows[0] = replace(
        attacked_rows[0],
        target_paths=("common.protocol_checks",),
    )
    with pytest.raises(v3.ConstructionAccountingRegistryV3Error):
        replace(
            migration, rows=tuple(attacked_rows)
        ).validate(registry)


def test_frozen_documents_are_fresh_and_do_not_issue_work() -> None:
    first = v3.freeze_construction_accounting_registry_successor_v3()
    attacked = copy.deepcopy(first)
    attacked["counter_registry"]["leaves"][0]["unit"] = "forged"
    second = v3.freeze_construction_accounting_registry_successor_v3()
    assert second["counter_registry"]["leaves"][0]["unit"] != "forged"
    assert set(second) == {
        "counter_registry",
        "stage_profile",
        "comparison_profile",
        "actual_projection_profile",
        "legacy_migration_profile",
    }
    combined = repr(second)
    assert "counter_record_id" not in combined
    assert "work_vector_id" not in combined
    assert "comparison_vector_id" not in combined
