from __future__ import annotations

import copy

import pytest

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_expression_accounted_preregistration_v24 as pre


@pytest.fixture(scope="module")
def frozen() -> pre.Standard2048ExpressionAccountedPreregistrationV24:
    return pre.freeze_standard_2048_expression_accounted_preregistration_v24()


def test_accounting_preregistration_is_outcome_free_and_content_addressed(frozen) -> None:
    assert pre.verify_standard_2048_expression_accounted_preregistration_v24(frozen) is frozen
    document = frozen.to_document()
    assert frozen.preregistration_id == document["expression_accounted_preregistration_id"]
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert document["outcome_fields_present"] is False
    assert document["counter_records_issued"] is False
    assert document["work_vectors_issued"] is False
    assert document["comparison_vectors_issued"] is False


def test_measurement_replays_predecessors_without_relabelling_summaries(frozen) -> None:
    predecessors = frozen.to_document()["measurement_predecessors"]
    assert predecessors["measurement_replays_already_revealed_target"] is True
    assert predecessors["fresh_blind_scientific_confirmation_claimed"] is False
    assert predecessors["predecessor_artifacts_relabelled_as_actual_counters"] is False


def test_model_acquisition_and_evaluation_paths_bind_v9(frozen) -> None:
    document = frozen.to_document()
    protocol = document["actual_accounting_protocol"]
    registry = registry_v9.official_counter_registry_v9()
    assert protocol["counter_registry_id"] == registry.registry_id
    assert tuple(protocol["model_operational_paths"]) == pre.MODEL_OPERATIONAL_PATHS
    assert tuple(protocol["model_evaluation_paths"]) == pre.MODEL_EVALUATION_PATHS
    assert set(pre.MODEL_OPERATIONAL_PATHS).issubset(registry.by_path)
    assert set(pre.MODEL_EVALUATION_PATHS).issubset(registry.by_path)


def test_long_workload_and_nine_shared_paths_are_frozen(frozen) -> None:
    document = frozen.to_document()
    workload = document["registered_long_reuse_workload"]
    assert workload["episode_count"] == 4
    assert workload["maximum_decision_count"] == 128
    assert workload["maximum_evaluation_work_vector_count"] == 12
    assert tuple(document["actual_accounting_protocol"]["shared_resource_paths"]) == pre.SHARED_RESOURCE_PATHS
    assert len(pre.SHARED_RESOURCE_PATHS) == 9


def test_official_gates_remain_locked_and_caller_mutation_is_rejected(frozen) -> None:
    document = frozen.to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    tampered = copy.copy(frozen)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7Standard2048ExpressionAccountedPreregistrationV24Error):
        pre.verify_standard_2048_expression_accounted_preregistration_v24(tampered)
