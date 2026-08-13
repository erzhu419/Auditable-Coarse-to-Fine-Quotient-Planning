from __future__ import annotations

from acfqp import construction_accounting_registry_v8 as v8
from acfqp import construction_accounting_registry_v9 as v9
from acfqp.accounting_v1 import (
    CounterRecordV1,
    RouteKindEnum,
    WorkVectorV1,
    derive_comparison_vector_v1,
)


def _vector(values: dict[str, int]) -> WorkVectorV1:
    registry = v9.official_counter_registry_v9()
    all_values = {path: 0 for path in registry.required_paths}
    all_values.update(values)
    return WorkVectorV1(
        registry.registry_id,
        "9" * 64,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        tuple(
            CounterRecordV1.observe(
                registry, path, all_values[path], recorder_id="v9-focused-test"
            )
            for path in sorted(all_values)
        ),
    )


def test_v9_preserves_v8_and_adds_exact_model_synthesis_inventory() -> None:
    old = v8.official_counter_registry_v8()
    new = v9.official_counter_registry_v9()
    assert new.v8_registry_id == old.registry_id
    assert tuple(row.to_dict() for row in new.leaves if row.path in old.by_path) == tuple(
        row.to_dict() for row in old.leaves
    )
    assert len(new.leaves) == 269
    assert len(new.operational_leaves) == 213
    assert len(new.evaluation_leaves) == 23
    assert len(new.required_paths) == 262


def test_model_synthesis_projects_exactly_once_but_replay_does_not() -> None:
    registry = v9.official_counter_registry_v9()
    profile = v9.official_comparison_profile_v9(registry)
    vector = _vector(
        {
            "model.target_probability_labels_acquired": 4,
            "model.structural_expression_value_evaluations": 224,
            "model.expression_candidates_materialized": 80,
            "model.exact_program_proof_rows_evaluated": 17,
            "model.world_model_freezes": 1,
            "evaluation.target_probability_labels_acquired": 999,
            "evaluation.exact_program_proof_rows_evaluated": 999,
        }
    )
    registry.validate_vector(vector)
    comparison = derive_comparison_vector_v1(vector, registry, profile)
    assert comparison.value("kernel_transition_calls") == 0
    assert comparison.value("nonkernel_compute_events") == 326
    assert all(not term.source_leaf.startswith("evaluation.") for term in profile.terms)


def test_probability_labels_are_not_relabelled_ground_transitions() -> None:
    frozen = v9.freeze_construction_accounting_registry_v9()
    document = frozen["counter_registry"]
    leaf = v9.official_counter_registry_v9().by_path[
        "model.target_probability_labels_acquired"
    ]
    assert leaf.comparison_axis == "nonkernel_compute_events"
    assert document["scalar_probability_label_query_is_ground_transition_call"] is False
    assert document["sample_label_count_remains_separately_reportable"] is True


def test_model_stage_rules_are_disjoint_and_complete_for_v9_additions() -> None:
    profile = v9.official_stage_profile_v9()
    paths = [
        path
        for rule in profile.model_synthesis_rules
        for path in rule.allowed_nonzero_paths
    ]
    additions = {
        row.path
        for row in v9.official_counter_registry_v9().leaves
        if row.semantics_id.endswith("-v9")
    }
    assert len(paths) == len(set(paths))
    assert set(paths) == additions


def test_all_v9_profile_identities_are_content_addressed_and_stable() -> None:
    frozen = v9.freeze_construction_accounting_registry_v9()
    assert frozen["counter_registry"]["counter_registry_id"] == (
        "4e7dcb1dae484c258e826c609070eb698c118d5ff2f24906c25222665d7adb34"
    )
    assert frozen["stage_profile"]["stage_profile_id"] == (
        "2f2c5669824af425e330e2fa34f71c8eaecd66188ed6cf5ead0732fcca508188"
    )
    assert frozen["comparison_profile"]["comparison_profile_id"] == (
        "a6eadec7df35749a688c5ebc721d1370a33d1efdb66bc6911dccd9d863a28e3a"
    )
    assert frozen["actual_projection_profile"]["actual_projection_profile_id"] == (
        "f1930a67cba4ba94dd9cd09696e83420d3752b718ca06b3341384aac2931c505"
    )
    assert frozen == v9.freeze_construction_accounting_registry_v9()
