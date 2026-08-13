from __future__ import annotations

from acfqp.accounting_v1 import LaneEnum, RouteKindEnum
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp import construction_accounting_registry_v8 as registry_v8
from acfqp import construction_k7_standard_2048_instrumented_runtime_v12 as runtime
from acfqp import construction_k7_standard_2048_long_episode_independent_verifier_v11 as replay
from acfqp import construction_k7_standard_2048_meta_prior_route_preregistration_v10 as dense
from acfqp.domains.standard_2048 import state_from_board_v1


def test_fallback_decision_preserves_common_and_route_work_separately() -> None:
    draft = runtime.smoke_first_registered_decision_v12()
    assert draft.route == "COLD_EXACT_DIRECT_GROUND_FALLBACK"
    assert draft.fallback_counter_values is not None
    assert draft.evaluation_counter_values is None
    common = draft.common_counter_values
    fallback = draft.fallback_counter_values
    assert common["common.abstract_bellman_backups"] > 0
    assert common["common.abstract_support_outcome_evaluations"] > 0
    assert common["common.hash_invocations"] > 0
    assert common["common.protocol_checks"] > 0
    assert common["fallback.ground_steps"] == 0
    assert common["target.execution_ground_steps"] == 0
    assert fallback["fallback.ground_steps"] > 0
    assert fallback["common.hash_invocations"] > 0
    assert fallback["common.integrity_checks"] > 0
    assert fallback["common.protocol_checks"] > 0
    assert fallback["target.execution_ground_steps"] == 1
    assert fallback["target.transition_observations"] == 1
    common_chain = runtime.build_operational_accounting_chain_v12(
        subject_id="a" * 64,
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        values=common,
        recorder_id="standard-2048-v12-common",
    )
    fallback_chain = runtime.build_operational_accounting_chain_v12(
        subject_id="b" * 64,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
        values=fallback,
        recorder_id="standard-2048-v12-fallback",
    )
    assert common_chain.work_vector.work_vector_id != fallback_chain.work_vector.work_vector_id
    assert common_chain.comparison_vector.value("kernel_transition_calls") == 0
    assert fallback_chain.comparison_vector.value("kernel_transition_calls") > 0


def test_abstract_decision_keeps_exact_replay_in_evaluation_lane() -> None:
    binding, bounds, lower, upper = replay._operator_binding()
    common = runtime.NativeCounterSetV12()
    rows = runtime.InstrumentedLazyRowsV12(
        bounds, binding["long_operator_binding_id"], common
    )
    bellman = runtime.InstrumentedPersistentBellmanV12(lower, upper, common)
    draft = runtime.execute_instrumented_decision_v12(
        state=state_from_board_v1(dense.PREREGISTERED_INITIAL_BOARDS[0]),
        decision_index=0,
        seed=dense.PREREGISTERED_EPISODE_SEEDS[0],
        operator_id=binding["long_operator_binding_id"],
        rows=rows,
        bellman=bellman,
        common_counters=common,
    )
    assert draft.route == "ABSTRACT_CERTIFIED"
    assert draft.fallback_counter_values is None
    assert draft.evaluation_counter_values is not None
    assert draft.common_counter_values["target.execution_ground_steps"] == 1
    assert draft.evaluation_counter_values["evaluation.exact_ground_steps"] > 0
    assert draft.evaluation_counter_values["evaluation.hash_invocations"] > 0
    assert all(
        draft.evaluation_counter_values[path] == 0
        for path in (
            "common.abstract_bellman_backups",
            "fallback.ground_steps",
            "target.execution_ground_steps",
        )
    )
    operational = runtime.build_operational_accounting_chain_v12(
        subject_id="c" * 64,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
        values=draft.common_counter_values,
        recorder_id="standard-2048-v12-abstract",
    )
    evaluation = runtime.build_evaluation_work_vector_v12(
        subject_id="d" * 64,
        values=draft.evaluation_counter_values,
        recorder_id="standard-2048-v12-evaluation",
    )
    assert operational.comparison_vector.value("kernel_transition_calls") == 1
    registry = registry_v8.official_counter_registry_v8()
    assert any(
        row.lane is LaneEnum.EVALUATION and row.value > 0
        for row in evaluation.records
    )
    assert all(
        evaluation.value(leaf.path) == 0 for leaf in registry.operational_leaves
    )


def test_cache_and_support_reconciliation_is_exact() -> None:
    draft = runtime.smoke_first_registered_decision_v12()
    common = draft.common_counter_values
    assert common["common.abstract_subproof_cache_lookups"] == (
        common["common.abstract_subproof_cache_hits"]
        + common["common.abstract_subproof_cache_misses"]
    )
    fallback = draft.fallback_counter_values
    assert fallback is not None
    assert fallback["fallback.subproof_cache_lookups"] == (
        fallback["fallback.subproof_cache_hits"]
        + fallback["fallback.subproof_cache_misses"]
    )
    assert fallback["fallback.actions_evaluated"] == fallback["fallback.ground_steps"]
    assert fallback["fallback.actions_evaluated"] == fallback["fallback.bellman_backups"]
