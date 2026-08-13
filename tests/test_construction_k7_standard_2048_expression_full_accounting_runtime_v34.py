from __future__ import annotations

from acfqp import construction_k7_standard_2048_commit_reveal_target_kernel_v22 as target
from acfqp import construction_k7_standard_2048_expression_full_accounting_runtime_v34 as runtime
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.domains.standard_2048 import state_from_board_v1


def test_native_counter_set_emits_every_v9_path_including_zero() -> None:
    counters = runtime.NativeCounterSetV34()
    frozen = counters.freeze()
    assert len(frozen) == 269
    assert all(value == 0 for value in frozen.values())


def test_operational_model_events_project_to_shared_nonkernel_axis() -> None:
    counters = runtime.NativeCounterSetV34()
    counters.add("model.target_probability_labels_acquired", 4)
    counters.add("model.structural_expression_value_evaluations", 224)
    counters.add("model.expression_candidates_materialized", 80)
    counters.add("model.exact_program_proof_rows_evaluated", 17)
    counters.add("model.world_model_freezes")
    chain = runtime.build_operational_accounting_chain_v34(
        subject_id="a" * 64,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        values=counters.freeze(),
        recorder_id="b" * 64,
    )
    assert chain.comparison_vector.value("kernel_transition_calls") == 0
    assert chain.comparison_vector.value("nonkernel_compute_events") == 326
    assert chain.projection_proof.comparison_vector_id == chain.comparison_vector.comparison_vector_id


def test_exact_evaluation_replay_matches_ground_planner() -> None:
    state = state_from_board_v1(
        (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    )
    actual, counters = runtime.evaluate_ground_root_with_native_counters_v34(
        state, outcome_provider=target.target_outcomes_v22, horizon=2
    )
    expected = planner.evaluate_ground_root_v1(
        state, outcome_provider=target.target_outcomes_v22, horizon=2
    )
    assert actual["root_action_exact_values"] == expected["root_action_exact_values"]
    assert actual["selected_action"] == expected["selected_action"]
    assert counters["evaluation.exact_ground_steps"] == actual["ground_state_action_row_count"]
    assert counters["evaluation.exact_outcome_rows"] == actual["ground_outcome_count"]
    assert counters["evaluation.exact_subproof_cache_hits"] == actual[
        "subproof_cache_hit_count"
    ]
    assert counters["evaluation.exact_subproof_cache_misses"] == actual[
        "subproof_cache_miss_count"
    ]
    assert counters["evaluation.exact_states_expanded"] > 0


def test_evaluation_vector_has_no_operational_projection_source() -> None:
    counters = runtime.NativeCounterSetV34()
    counters.add("evaluation.target_probability_labels_acquired", 4)
    counters.add("evaluation.exact_program_proof_rows_evaluated", 17)
    vector, zero = runtime.build_evaluation_work_vector_v34(
        subject_id="c" * 64,
        values=counters.freeze(),
        recorder_id="d" * 64,
    )
    assert vector.value("model.target_probability_labels_acquired") == 0
    assert vector.value("evaluation.target_probability_labels_acquired") == 4
    assert vector.work_vector_id == zero.work_vector_id
