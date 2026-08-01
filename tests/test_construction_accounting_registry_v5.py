from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import construction_accounting_registry_v4 as v4
from acfqp import construction_accounting_registry_v5 as v5
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V5_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
)


def _profiles():
    registry = v5.official_counter_registry_v5()
    stage = v5.official_stage_profile_v5(registry)
    comparison = v5.official_comparison_profile_v5(registry)
    actual = v5.official_actual_projection_profile_v5(
        registry, comparison
    )
    return registry, stage, comparison, actual


def test_v5_preserves_v4_and_has_exact_cardinalities() -> None:
    registry, stage, comparison, actual = _profiles()
    base = v4.official_counter_registry_v4()
    assert len(registry.leaves) == 151
    assert len(registry.operational_leaves) == 133
    assert len(registry.required_paths) == 144
    assert len(stage.rules) == 10
    assert len(comparison.terms) == 133
    assert actual.terms == comparison.terms
    assert registry.v4_registry_id == base.registry_id
    assert all(
        registry.by_path[row.path].to_dict() == row.to_dict()
        for row in base.leaves
    )
    assert len(set(registry.by_path) - set(base.by_path)) == 27


def test_exact_owner_specific_additions_and_stage_ownership() -> None:
    registry, stage, _comparison, _actual = _profiles()
    initial = stage.by_stage[v5.ConstructionStageKindV5.INITIAL_MODEL_BUILD]
    failed = stage.by_stage[v5.ConstructionStageKindV5.FAILED_ABSTRACT_PREFIX]
    closed = stage.by_stage[
        v5.ConstructionStageKindV5
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ]
    assertions = {
        "build.initial_live_model_support_descriptors_compiled": (
            "v075_live_incremental_model_authority_v2",
            "support_descriptors",
            initial,
        ),
        "build.initial_batch_v2_interval_greedy_allocation_steps": (
            "v075_batch_native_planning_backend_v2",
            "greedy_allocation_steps",
            initial,
        ),
        "closure.reconciliation_batch_v2_support_descriptors_compiled": (
            "v075_batch_native_planning_backend_v2",
            "support_descriptors",
            closed,
        ),
        "build.initial_live_model_outcome_projections": (
            "v075_live_incremental_model_authority_v2",
            "outcome_projections",
            initial,
        ),
        "closure.reconciliation_batch_v2_model_rows_built": (
            "v075_batch_native_planning_backend_v2",
            "model_rows",
            closed,
        ),
        "closure.reconciliation_batch_v2_row_evidence_bindings_built": (
            "v075_batch_native_planning_backend_v2",
            "row_evidence_bindings",
            closed,
        ),
        "audit.dynamic_child_action_rows_built": (
            "v075_live_dynamic_acquisition_authority_v2",
            "child_action_rows",
            failed,
        ),
    }
    for path, (owner, unit, rule) in assertions.items():
        leaf = registry.by_path[path]
        assert leaf.owner == owner
        assert leaf.unit == unit
        assert leaf.lane.value == "operational"
        assert leaf.reducer.value == "sum"
        assert leaf.comparison_axis == "nonkernel_compute_events"
        assert leaf.required is True
        assert path in rule.allowed_nonzero_paths
        assert sum(
            path in item.allowed_nonzero_paths for item in stage.rules
        ) == 1


def test_batch_families_are_nine_per_stage_and_dynamic_is_six() -> None:
    registry, _stage, _comparison, _actual = _profiles()
    added = set(registry.by_path) - set(
        v4.official_counter_registry_v4().by_path
    )
    initial = {
        path
        for path in added
        if path.startswith("build.initial_batch_v2_")
        or path == "build.initial_live_model_support_descriptors_compiled"
    }
    closed = {
        path
        for path in added
        if path.startswith("closure.reconciliation_batch_v2_")
        and path
        not in {
            "closure.reconciliation_batch_v2_model_rows_built",
            (
                "closure.reconciliation_batch_v2_"
                "row_evidence_bindings_built"
            ),
        }
    }
    dynamic = {path for path in added if path.startswith("audit.dynamic_")}
    corrections = added - initial - closed - dynamic
    assert len(initial) == 9
    assert len(closed) == 9
    assert len(dynamic) == 6
    assert len(corrections) == 3
    assert not any("extreme_evaluation" in path for path in added)
    assert not any("interval_lp_allocations" in path for path in added)
    assert {
        "build.initial_batch_v2_interval_greedy_allocation_steps",
        (
            "closure.reconciliation_batch_v2_"
            "interval_greedy_allocation_steps"
        ),
    } <= added


def test_v5_owner_stage_and_greedy_claims_remain_schema_only() -> None:
    registry, stage, _comparison, _actual = _profiles()
    registry_document = registry.to_document()
    stage_document = stage.to_document()
    assert registry_document[
        "greedy_allocation_event_boundary_schema_frozen"
    ] is True
    assert registry_document["runtime_greedy_allocation_instrumented"] is False
    assert registry_document["runtime_owner_match_verified"] is False
    assert registry_document["runtime_stage_attribution_verified"] is False
    assert registry_document[
        "operation_event_boundary_profile_complete"
    ] is False
    assert stage_document[
        "batch_v2_initial_and_closed_stage_assignment_schema_frozen"
    ] is True
    assert stage_document[
        "dynamic_child_failed_prefix_assignment_schema_frozen"
    ] is True
    assert stage_document[
        "owner_correction_stage_assignment_schema_frozen"
    ] is True
    assert stage_document["runtime_owner_match_verified"] is False
    assert stage_document["runtime_stage_attribution_verified"] is False


def test_every_v5_operational_leaf_projects_once() -> None:
    registry, _stage, comparison, actual = _profiles()
    sources = [row.source_leaf for row in comparison.terms]
    assert sources == [row.path for row in registry.operational_leaves]
    assert len(sources) == len(set(sources)) == 133
    assert all(row.coefficient == 1 for row in comparison.terms)
    assert actual.terms == comparison.terms


def test_cardinality_guard_and_catalogue_mutation_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(v5, "EXPECTED_V5_OPERATIONAL_LEAF_COUNT", 132)
    with pytest.raises(
        v5.ConstructionAccountingRegistryV5Error,
        match="cardinality",
    ):
        v5.official_counter_registry_v5()

    monkeypatch.undo()
    registry = v5.official_counter_registry_v5()
    forged = replace(
        registry,
        leaves=registry.leaves[:-1],
    )
    with pytest.raises(v5.ConstructionAccountingRegistryV5Error):
        forged.validate_official_catalogue()


def test_v5_domains_are_registered_and_separated() -> None:
    expected = {
        CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN,
        CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN,
        CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN,
        CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V5_DOMAIN,
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
