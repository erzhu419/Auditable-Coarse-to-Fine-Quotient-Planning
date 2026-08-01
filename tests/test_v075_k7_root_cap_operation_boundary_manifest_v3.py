from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import construction_accounting_registry_v4 as registry_v4
from acfqp import construction_accounting_registry_v5 as registry_v5
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ROOT_CAP_OPERATION_BOUNDARY_MANIFEST_V3_DOMAIN,
    V075_K7_ROOT_CAP_OPERATION_BOUNDARY_V3_DOMAIN,
)
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as manifest
from acfqp.v075_k7_root_cap_operation_site_manifest_v2 import (
    OperationSiteClassificationV2,
    official_k7_root_cap_operation_site_manifest_v2,
)


def _frozen() -> manifest.K7RootCapOperationBoundaryManifestV3:
    return manifest.official_k7_root_cap_operation_boundary_manifest_v3()


def test_v3_binds_v2_and_v6_profiles_without_runtime_claims() -> None:
    frozen = _frozen()
    document = frozen.to_document()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    assert frozen.v2_manifest_id == (
        official_k7_root_cap_operation_site_manifest_v2().manifest_id
    )
    assert frozen.counter_registry_id == registry.registry_id
    assert frozen.stage_profile_id == stage.stage_profile_id
    assert frozen.comparison_profile_id == comparison.comparison_profile_id
    assert frozen.actual_projection_profile_id == (
        actual.actual_projection_profile_id
    )
    assert len(frozen.boundaries) == 150
    assert document["classification_counts"] == {
        "V6_NATIVE_BOUNDARY_SCHEMA_ONLY": 27,
        "V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY": 6,
        "V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY": 43,
        "V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY": 13,
        "OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO": 43,
        "LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN": 16,
        "LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN": 2,
    }
    assert document["runtime_emitters_installed"] is False
    assert document["live_operation_event_count"] == 0
    assert document["all_site_completeness_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["counter_completeness_gate_passed"] is False
    assert document["workload_economics_gate_passed"] is False


def test_every_v5_and_v6_addition_has_an_exact_boundary() -> None:
    frozen = _frozen()
    v4_paths = set(registry_v4.official_counter_registry_v4().by_path)
    v5_paths = set(registry_v5.official_counter_registry_v5().by_path)
    v6_paths = set(registry_v6.official_counter_registry_v6().by_path)
    v5_additions = v5_paths - v4_paths
    v6_additions = v6_paths - v5_paths
    assert len(v5_additions) == 27
    assert len(v6_additions) == 58
    assert v5_additions <= set(frozen.by_path)
    assert v6_additions <= set(frozen.by_path)
    assert all(
        row.operation_source_module and row.operation_source_symbol
        for path in (*sorted(v5_additions), *sorted(v6_additions))
        for row in frozen.by_path[path]
    )
    assert all(
        row.registered_owner
        == row.operation_source_module.rsplit(".", 1)[-1]
        for path in (*sorted(v5_additions), *sorted(v6_additions))
        for row in frozen.by_path[path]
    )


def test_all_24_root_v4_owner_matched_paths_and_open_analogues_are_bound() -> None:
    frozen = _frozen()
    v2 = official_k7_root_cap_operation_site_manifest_v2()
    direct = {
        path
        for site in v2.sites
        if site.classification
        is OperationSiteClassificationV2.DIRECT_VALID_OWNER_MATCHED
        for path in site.target_paths
    }
    assert len(direct) == 24
    assert direct <= set(frozen.by_path)
    assert len(manifest._ROOT_ACTIVE_V4_OWNER_MATCHED_PATHS) == 13
    assert len(manifest._OPEN_V4_OWNER_MATCHED_PATHS) == 7
    assert (
        direct - set(manifest._LEGACY_REPLACEMENTS)
        == manifest._ROOT_ACTIVE_V4_OWNER_MATCHED_PATHS
    )
    registry = registry_v6.official_counter_registry_v6()
    for path in manifest._ROOT_ACTIVE_V4_OWNER_MATCHED_PATHS:
        rows = frozen.by_path[path]
        assert len(rows) == 1
        row = rows[0]
        assert row.classification is (
            manifest.OperationBoundaryClassificationV3
            .V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY
        )
        assert row.registered_owner == registry.by_path[path].owner
        assert row.registered_owner == (
            row.operation_source_module.rsplit(".", 1)[-1]
        )
    for path in manifest._OPEN_V4_OWNER_MATCHED_PATHS:
        row = frozen.by_path[path][0]
        assert row.classification is (
            manifest.OperationBoundaryClassificationV3
            .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
        )

    analogue_groups = (
        (
            "acquisition.initial_outcome_aggregate_rows",
            "acquisition.incremental_outcome_aggregate_rows",
            "closure.reconciliation_private_replay_outcome_aggregate_rows",
        ),
        (
            "acquisition.initial_support_freezes",
            "acquisition.incremental_support_freezes",
        ),
        (
            "build.initial_confidence_event_evaluations",
            "build.open_checkpoint_confidence_event_evaluations",
            "closure.reconciliation_confidence_event_evaluations",
        ),
        (
            "build.initial_interval_row_evaluations",
            "build.open_checkpoint_interval_row_evaluations",
            "closure.reconciliation_interval_row_evaluations",
        ),
        (
            "build.initial_policy_assignments_evaluated",
            "build.open_checkpoint_policy_assignments_evaluated",
            "closure.reconciliation_policy_assignments_evaluated",
        ),
    )
    for paths in analogue_groups:
        assert len(
            {frozen.by_path[path][0].dispatch_key for path in paths}
        ) == 1


def test_new_v4_boundaries_count_semantic_primitives_not_artifact_totals() -> None:
    frozen = _frozen()
    expected_fragments = {
        "acquisition.initial_outcome_aggregate_rows": (
            "each V075BatchOutcomeAggregateV2 construction",
            "per successfully materialized aggregate row",
        ),
        "acquisition.initial_support_freezes": (
            "both appended",
            "per successfully committed complete support freeze",
        ),
        "build.initial_confidence_event_evaluations": (
            "at function entry",
            "per invoked confidence-event evaluation",
        ),
        "build.initial_interval_row_evaluations": (
            "V075EventIntervalV2 construction",
            "per successfully constructed interval row",
        ),
        "build.initial_model_rows_built": (
            "exact numerical-row replay",
            "per successfully compiled changed live-model row",
        ),
        "build.initial_source_units_compiled": (
            "_CollectedRow source unit is appended",
            "per successfully compiled live row-source unit",
        ),
        "build.initial_policy_assignments_evaluated": (
            "under-cap combination",
            "per successfully evaluated policy assignment",
        ),
        "audit.failed_child_catalogues_built": (
            "accepted as the current child catalogue",
            "per accepted complete child catalogue",
        ),
        "closure.reconciliation_outcome_projections": (
            "one validated batch outcome aggregate",
            "per completed closed aggregate-outcome projection",
        ),
    }
    for path, (boundary_fragment, count_fragment) in expected_fragments.items():
        row = frozen.by_path[path][0]
        assert boundary_fragment in row.operation_boundary
        assert count_fragment in row.count_rule
        assert row.to_document()["artifact_cardinality_backfill_allowed"] is False


def test_every_unmapped_required_v4_path_has_exact_nonemittable_reason() -> None:
    frozen = _frozen()
    document = frozen.to_document()
    report = document["unmapped_v4_required_paths_by_reason"]
    assert {key: len(value) for key, value in report.items()} == {
        "COMMON_SUM_PENDING_HOOK": 7,
        "CAPACITY_PEAK_PENDING_HOOK": 2,
        "DERIVED_ONLY_RECONCILIATION": 8,
        "NATIVE_ZERO_NOT_EXECUTED_OR_OUTSIDE_ROOT_CAP": 62,
    }
    flattened = [path for paths in report.values() for path in paths]
    assert len(flattened) == len(set(flattened))
    v4 = registry_v4.official_counter_registry_v4()
    assert set(flattened) == (
        set(v4.required_paths) - set(frozen.by_path)
    )
    assert "common.hash_invocations" in report["COMMON_SUM_PENDING_HOOK"]
    assert "io.mounted_bytes_peak" in report["CAPACITY_PEAK_PENDING_HOOK"]
    assert "route.attempts" in report["DERIVED_ONLY_RECONCILIATION"]
    assert "acquisition.incremental_child_catalogues_built" in report[
        "NATIVE_ZERO_NOT_EXECUTED_OR_OUTSIDE_ROOT_CAP"
    ]


def test_typed_replay_greedy_and_policy_multisite_boundaries_are_complete() -> None:
    frozen = _frozen()
    expected_replay_helpers = {
        "_replay_support_descriptor",
        "_replay_event_interval",
        "_replay_numerical_row",
        "_replay_numerical_model",
        "_replay_row_evidence_binding",
        "_replay_construction_planning_input",
        "_replay_construction_lineage",
    }
    for prefix in (
        "build.initial",
        "build.open_checkpoint",
        "closure.reconciliation",
    ):
        replay = frozen.by_path[f"{prefix}_batch_v2_typed_record_replays"]
        assert len(replay) == 7
        assert {row.operation_source_symbol for row in replay} == (
            expected_replay_helpers
        )

        greedy = frozen.by_path[
            f"{prefix}_batch_v2_interval_greedy_allocation_steps"
        ]
        assert len(greedy) == 2
        assert {row.operation_source_symbol for row in greedy} == {
            "_extreme",
            "_extreme_bounds",
        }
        assert all(
            "zero addition" in row.operation_boundary
            and "completed for-index allocation update" in row.count_rule
            for row in greedy
        )

        policy = frozen.by_path[
            f"{prefix}_batch_v2_policy_order_comparisons"
        ]
        assert len(policy) == 2
        assert all(
            row.operation_source_symbol
            == "plan_v075_construction_numerical_model_v2"
            for row in policy
        )
        assert any("diagnostic" in row.operation_boundary for row in policy)
        assert any("feasible-candidate" in row.operation_boundary for row in policy)


def test_stage_neutral_dispatch_is_unique_per_active_stage_and_site() -> None:
    frozen = _frozen()
    emittable = tuple(
        row
        for row in frozen.boundaries
        if row.to_document()["emittable_in_this_fixture"]
    )
    native_zero = tuple(
        row
        for row in frozen.boundaries
        if not row.to_document()["emittable_in_this_fixture"]
    )
    active_pairs = [(row.stage, row.dispatch_key) for row in emittable]
    zero_pairs = {(row.stage, row.dispatch_key) for row in native_zero}
    assert len(active_pairs) == len(set(active_pairs))
    assert not set(active_pairs) & zero_pairs

    for paths in (
        (
            "acquisition.initial_engine_ground_draws",
            "acquisition.incremental_engine_ground_draws",
            "closure.reconciliation_engine_ground_draws",
        ),
        (
            "build.initial_sequential_exact_likelihood_comparisons",
            "build.open_checkpoint_sequential_exact_likelihood_comparisons",
            (
                "closure.reconciliation_"
                "sequential_exact_likelihood_comparisons"
            ),
        ),
        (
            "build.initial_batch_v2_option_metric_evaluations",
            "build.open_checkpoint_batch_v2_option_metric_evaluations",
            "closure.reconciliation_batch_v2_option_metric_evaluations",
        ),
    ):
        assert len(
            {
                frozen.by_path[path][0].dispatch_key
                for path in paths
            }
        ) == 1

    for prefix in (
        "build.initial",
        "build.open_checkpoint",
        "closure.reconciliation",
    ):
        replay = frozen.by_path[f"{prefix}_batch_v2_typed_record_replays"]
        greedy = frozen.by_path[
            f"{prefix}_batch_v2_interval_greedy_allocation_steps"
        ]
        policy = frozen.by_path[
            f"{prefix}_batch_v2_policy_order_comparisons"
        ]
        assert len({row.dispatch_key for row in replay}) == 7
        assert len({row.dispatch_key for row in greedy}) == 2
        assert len({row.dispatch_key for row in policy}) == 2

    document = frozen.to_document()
    assert document["runtime_dispatch_selector"] == [
        "trusted_active_construction_stage_contextvar",
        "dispatch_key",
    ]
    assert document["caller_supplied_stage_dispatch_allowed"] is False
    assert document["stage_dispatch_context_must_be_active"] is True


def test_exact_log_and_cache_boundaries_do_not_charge_cached_summaries() -> None:
    frozen = _frozen()
    for prefix in (
        "build.initial",
        "build.open_checkpoint",
        "closure.reconciliation",
    ):
        exact = frozen.by_path[
            f"{prefix}_sequential_exact_likelihood_comparisons"
        ]
        assert len(exact) == 1
        assert exact[0].operation_source_symbol == (
            "_ExactGridRejectionV1.rejects"
        )
        assert exact[0].cache_semantics is (
            manifest.CacheSemanticsV3.MISS_COMPUTATION_ONLY
        )

        logarithmic = frozen.by_path[
            f"{prefix}_sequential_interval_log_search_evaluations"
        ]
        assert len(logarithmic) == 2
        assert {row.operation_source_symbol for row in logarithmic} == {
            "_last_rejected_lower_grid_index",
            "_first_rejected_upper_grid_index",
        }
        assert all(
            row.cache_semantics
            is manifest.CacheSemanticsV3.MISS_COMPUTATION_ONLY
            for row in logarithmic
        )

        lookup = frozen.by_path[f"{prefix}_confidence_cache_lookups"]
        hit = frozen.by_path[f"{prefix}_confidence_cache_hits"]
        miss = frozen.by_path[f"{prefix}_confidence_cache_misses"]
        assert lookup[0].cache_semantics is (
            manifest.CacheSemanticsV3.LOOKUP_ATTEMPT
        )
        assert hit[0].cache_semantics is (
            manifest.CacheSemanticsV3.HIT_CLASSIFICATION_ONLY
        )
        assert miss[0].cache_semantics is (
            manifest.CacheSemanticsV3.MISS_CLASSIFICATION_ONLY
        )
        assert {
            lookup[0].operation_source_symbol,
            hit[0].operation_source_symbol,
            miss[0].operation_source_symbol,
        } == {"_outer_confidence_bounds_accounted_v2"}
        assert "cache-info before/after" in hit[0].operation_boundary
        assert "cache-info before/after" in miss[0].operation_boundary
    document = frozen.to_document()
    assert document["returned_summary_charging_allowed"] is False
    assert document["artifact_cardinality_backfill_allowed"] is False
    assert document["cache_hit_exact_or_log_computation_charged"] is False
    assert document["confidence_cache_info_before_after_required"] is True
    assert document["confidence_cache_body_entry_marker_required"] is True
    assert document["official_cache_lifecycle"] == (
        "ISOLATED_COLD_CACHE_EPOCH_PER_OCCURRENCE_OR_REPLAY"
    )
    assert document["process_global_warm_cache_reuse_allowed"] is False
    assert document["beta_binomial_cache_accounting"] == (
        "INTERNAL_TO_ONE_REGISTERED_EXACT_COMPARISON_EVENT_"
        "NO_SEPARATE_V6_CHARGE"
    )
    assert document[
        "beta_binomial_cache_requires_same_cold_isolated_epoch"
    ] is True


def test_engine_observer_live_dynamic_and_closed_boundaries_are_owner_local() -> None:
    frozen = _frozen()
    engine = frozen.by_path["acquisition.initial_engine_ground_draws"][0]
    assert engine.operation_source_module == (
        "acfqp.h2_graph_transition_engine_v1"
    )
    assert engine.operation_source_symbol == "DeterministicH2GraphStreamV1.draw"
    accumulator = frozen.by_path[
        "acquisition.initial_observer_accumulator_updates"
    ][0]
    assert accumulator.operation_source_symbol == (
        "_StreamingBatchAccumulatorV2.append"
    )
    row_source = frozen.by_path[
        "build.initial_live_model_row_source_bindings_built"
    ][0]
    assert row_source.operation_source_symbol == "_row_source_binding"
    for path in (
        "audit.dynamic_root_rows_scanned",
        "audit.dynamic_support_descriptors_scanned",
        "audit.dynamic_causal_edges_built",
        "audit.dynamic_child_action_rows_built",
        "audit.dynamic_row_cap_checks",
        "audit.dynamic_child_closure_attestations",
        "closure.reconciliation_batch_v2_model_rows_built",
        "closure.reconciliation_batch_v2_row_evidence_bindings_built",
        "closure.reconciliation_batch_v2_support_descriptors_compiled",
    ):
        assert path in frozen.by_path
        assert frozen.by_path[path]
    child_row = frozen.by_path["audit.dynamic_child_action_rows_built"][0]
    assert child_row.operation_source_symbol == "_derive_child_states"
    assert "accepted into the dynamic child row collection" in (
        child_row.operation_boundary
    )
    assert "dynamic-owner child-row bind" in child_row.count_rule


def test_open_multiround_boundaries_are_supported_but_native_zero_in_fixture() -> None:
    frozen = _frozen()
    outside = {
        row.target_path
        for row in frozen.boundaries
        if row.classification
        is manifest.OperationBoundaryClassificationV3
        .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
    }
    assert "acquisition.incremental_engine_ground_draws" in outside
    assert "build.open_checkpoint_batch_v2_typed_record_replays" in outside
    assert set(manifest.FORBIDDEN_UNUSED_STAGES) == {
        registry_v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION,
        registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING,
        registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT,
        registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
        registry_v6.ConstructionStageKindV6.REBUILD,
    }
    assert frozen.to_document()["open_stages_supported_by_v6_registry"] is True
    assert frozen.to_document()["open_stages_executed_by_this_fixture"] is False


def test_all_legacy_mismatches_are_native_zero_with_owner_correct_replacements() -> None:
    frozen = _frozen()
    registry = registry_v6.official_counter_registry_v6()
    legacy = tuple(
        row
        for row in frozen.boundaries
        if row.classification
        in {
            manifest.OperationBoundaryClassificationV3
            .LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN,
            manifest.OperationBoundaryClassificationV3
            .LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN,
        }
    )
    assert len(legacy) == 18
    assert len({row.target_path for row in legacy}) == 18
    for row in legacy:
        source_owner = row.operation_source_module.rsplit(".", 1)[-1]
        assert row.replacement_paths
        assert all(
            registry.by_path[path].owner == source_owner
            for path in row.replacement_paths
        )
        if row.classification is (
            manifest.OperationBoundaryClassificationV3
            .LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN
        ):
            assert row.registered_owner != source_owner
        else:
            assert row.registered_owner == source_owner
            assert row.target_path.endswith("signed_batches")
            assert len(row.replacement_paths) == 2


def test_v3_ids_are_domain_separated_and_manifest_is_tamper_evident() -> None:
    frozen = _frozen()
    assert V075_K7_ROOT_CAP_OPERATION_BOUNDARY_V3_DOMAIN in PHASE3E_DOMAIN_TAGS
    assert (
        V075_K7_ROOT_CAP_OPERATION_BOUNDARY_MANIFEST_V3_DOMAIN
        in PHASE3E_DOMAIN_TAGS
    )
    assert all(len(row.boundary_id) == 64 for row in frozen.boundaries)
    assert len({row.boundary_id for row in frozen.boundaries}) == len(
        frozen.boundaries
    )
    first = frozen.boundaries[0]
    changed = replace(
        first,
        operation_boundary=first.operation_boundary + " changed",
    )
    altered = replace(
        frozen,
        boundaries=tuple(
            sorted(
                (changed, *frozen.boundaries[1:]),
                key=lambda row: row.boundary_key,
            )
        ),
    )
    assert changed.boundary_id != first.boundary_id
    assert altered.manifest_id != frozen.manifest_id
    with pytest.raises(
        manifest.V075K7RootCapOperationBoundaryManifestV3Error,
        match="official K7 root-cap V3",
    ):
        altered.validate_official()
