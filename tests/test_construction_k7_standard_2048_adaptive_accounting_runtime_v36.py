from __future__ import annotations

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_adaptive_accounting_preregistration_v36 as pre
from acfqp import construction_k7_standard_2048_adaptive_accounting_runtime_v36 as runtime
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.phase3e_ids import content_id


def _subject(label: str) -> str:
    return content_id(pre.FUTURE_DOMAINS["measurement"], {"label": label})


def _model_counts() -> dict[str, int]:
    return {
        "model.structural_context_rows_frozen": 2400,
        "model.structural_expression_value_evaluations": 100_000,
        "model.expression_candidates_materialized": 19,
        "model.candidate_label_consistency_checks": 31,
        "model.active_query_partition_evaluations": 76_000,
        "model.target_probability_labels_acquired": 6,
        "model.exact_program_proof_rows_evaluated": 4,
        "model.world_model_freezes": 1,
    }


def test_model_native_windows_partition_without_double_charging() -> None:
    acquisition = runtime.model_stage_counter_values_v36(
        _model_counts(), stage="ACQUISITION"
    )
    proof = runtime.model_stage_counter_values_v36(
        _model_counts(), stage="PROOF_AND_OVERLAY"
    )
    for path, value in _model_counts().items():
        assert acquisition[path] + proof[path] == value
    assert acquisition["model.exact_program_proof_rows_evaluated"] == 0
    assert acquisition["model.world_model_freezes"] == 0
    assert proof["model.target_probability_labels_acquired"] == 0


def test_operational_decision_records_planning_and_one_target_transition() -> None:
    values = runtime.operational_decision_counter_values_v36(
        model={
            "factored_action_row_evaluation_count": 7,
            "factored_support_outcome_evaluation_count": 84,
            "subproof_cache_hit_count": 5,
            "subproof_cache_miss_count": 9,
            "cross_decision_subproof_cache_hit_count": 3,
        },
        target_outcome_count=28,
    )
    assert values["common.abstract_bellman_backups"] == 7
    assert values["common.abstract_support_outcome_evaluations"] == 84
    assert values["common.abstract_subproof_cache_lookups"] == 14
    assert values["target.execution_ground_steps"] == 1
    assert values["target.execution_outcome_rows"] == 28
    assert values["target.transition_observations"] == 1


def test_no_prior_control_is_evaluation_only() -> None:
    values = runtime.no_prior_control_counter_values_v36(2400)
    registry = registry_v9.official_counter_registry_v9()
    assert values["evaluation.target_probability_labels_acquired"] == 2400
    assert all(values[leaf.path] == 0 for leaf in registry.operational_leaves)


def test_complete_native_zero_vector_projects_once() -> None:
    values = runtime.model_stage_counter_values_v36(
        _model_counts(), stage="ACQUISITION"
    )
    subject = _subject("acquisition")
    chain = runtime.build_operational_accounting_chain_v36(
        subject_id=subject,
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        values=values,
        recorder_id=_subject("recorder"),
    )
    registry = registry_v9.official_counter_registry_v9()
    assert len(chain.work_vector.records) == len(registry.by_path)
    assert chain.work_vector.subject_id == subject
    assert chain.comparison_vector.value("nonkernel_compute_events") > 0
    assert chain.native_zero_attestation.work_vector_id == (
        chain.work_vector.work_vector_id
    )


def test_evaluation_vector_cannot_enter_operational_comparison() -> None:
    values = runtime.no_prior_control_counter_values_v36(2400)
    subject = _subject("control")
    vector, zero = runtime.build_evaluation_work_vector_v36(
        subject_id=subject,
        values=values,
        recorder_id=_subject("evaluation-recorder"),
    )
    assert vector.subject_id == subject
    assert vector.value("evaluation.target_probability_labels_acquired") == 2400
    assert zero.work_vector_id == vector.work_vector_id
