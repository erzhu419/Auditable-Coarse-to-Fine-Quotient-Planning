from acfqp import construction_k7_open_world_execution_preregistration_v181r4 as prereg


def test_v181r4_execution_freeze_precedes_target_queries() -> None:
    document = prereg.freeze_open_world_execution_preregistration_v181r4().to_document()
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False
    assert document["runner_frozen_before_target_outcome_access"] is True
    assert len(document["frozen_source_facts"]) == 11
    assert len({row["filename"] for row in document["frozen_source_facts"]}) == 11


def test_v181r4_rank_rule_is_preregistered_without_cap_increase() -> None:
    document = prereg.freeze_open_world_execution_preregistration_v181r4().to_document()
    assert document["execution_recompile_requires_actual_model_mismatch"] is True
    assert document["rank_decreasing_certificate_required"] is True
    assert document["selected_action_requires_strict_rank_decrease_for_every_successor"] is True
    assert document["reset_horizon_procrastination_forbidden"] is True
    assert document["resource_cap_increased_relative_to_v181r3"] is False
    assert document["target_episode_denominator"] == 72


def test_v181r4_execution_claims_remain_nonofficial() -> None:
    document = prereg.freeze_open_world_execution_preregistration_v181r4().to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
