from __future__ import annotations

from acfqp.accounting_v1 import (
    CounterRecordV1,
    RouteKindEnum,
    WorkVectorV1,
    derive_comparison_vector_v1,
)
from acfqp import construction_accounting_registry_v7 as v7
from acfqp import construction_accounting_registry_v8 as v8


def _vector(values: dict[str, int]) -> WorkVectorV1:
    registry = v8.official_counter_registry_v8()
    all_values = {path: 0 for path in registry.required_paths}
    all_values.update(values)
    records = tuple(
        CounterRecordV1.observe(
            registry, path, all_values[path], recorder_id="v8-focused-test"
        )
        for path in sorted(all_values)
    )
    return WorkVectorV1(
        registry.registry_id,
        "f" * 64,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        records,
    )


def test_v8_preserves_v7_and_adds_exact_lane_inventory() -> None:
    old = v7.official_counter_registry_v7()
    new = v8.official_counter_registry_v8()
    assert new.v7_registry_id == old.registry_id
    assert tuple(row.to_dict() for row in new.leaves if row.path in old.by_path) == tuple(
        row.to_dict() for row in old.leaves
    )
    assert len(new.leaves) == 253
    assert len(new.operational_leaves) == 205
    assert len(new.evaluation_leaves) == 15
    assert len(new.required_paths) == 246


def test_target_execution_projects_but_evaluation_replay_does_not() -> None:
    registry = v8.official_counter_registry_v8()
    profile = v8.official_comparison_profile_v8(registry)
    vector = _vector(
        {
            "target.execution_ground_steps": 1,
            "target.execution_outcome_rows": 28,
            "target.transition_observations": 1,
            "evaluation.exact_ground_steps": 999,
            "evaluation.exact_outcome_rows": 9999,
            "route.attempts": 1,
            "route.successes": 1,
        }
    )
    registry.validate_vector(vector)
    comparison = derive_comparison_vector_v1(vector, registry, profile)
    assert comparison.value("kernel_transition_calls") == 1
    assert comparison.value("nonkernel_compute_events") == 29
    assert all(
        not term.source_leaf.startswith("evaluation.") for term in profile.terms
    )


def test_cache_lookups_are_costed_and_hits_are_diagnostic() -> None:
    registry = v8.official_counter_registry_v8()
    profile = v8.official_comparison_profile_v8(registry)
    vector = _vector(
        {
            "common.abstract_subproof_cache_lookups": 100,
            "common.abstract_support_outcome_evaluations": 500,
            "common.abstract_subproof_cache_hits": 90,
            "common.abstract_subproof_cache_misses": 10,
        }
    )
    comparison = derive_comparison_vector_v1(vector, registry, profile)
    assert comparison.value("nonkernel_compute_events") == 600
    assert registry.by_path["common.abstract_subproof_cache_hits"].comparison_axis is None
    assert registry.by_path["common.abstract_subproof_cache_misses"].comparison_axis is None


def test_frozen_v8_profile_ids_are_stable() -> None:
    frozen = v8.freeze_construction_accounting_registry_v8()
    assert frozen["counter_registry"]["counter_registry_id"] == (
        "c85bc3bc127f2c64ae6010db7eb44f9f79a5b37843da1b641e0f06f2f3c9a519"
    )
    assert frozen["comparison_profile"]["comparison_profile_id"] == (
        "3ed1f6367dcfdbab2f5d9a893b505cd17e109e9d758ba188d1b5a547d8f1ad6b"
    )
    assert frozen["actual_projection_profile"]["actual_projection_profile_id"] == (
        "bed3454cd28806e222b0e2c7bba5dccbac0af4cf313c094d7196d8400b9f7d76"
    )
    assert frozen["stage_profile"]["stage_profile_id"] == (
        "3a5628c312c0c81a2f9f62e6536da5e51055e93244f69aaa928b94d42dfe56f9"
    )
