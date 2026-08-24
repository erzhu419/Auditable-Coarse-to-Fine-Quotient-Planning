from acfqp import construction_k7_open_world_failure_v181r5 as failure


def test_v181r5_premature_oracle_access_is_frozen_as_failure() -> None:
    document = failure.freeze_open_world_failure_v181r5().to_document()
    assert document["failure_code"] == "PREMATURE_TARGET_ORACLE_ACCESS"
    assert document["target_oracle_query_call_count"] == 80
    assert document["unique_raw_observation_count"] == 48
    assert document["target_outcomes_accessed"] is True
    assert document["execution_preregistration_frozen"] is False
    assert document["campaign_executed"] is False
    assert document["same_v181r5_identity_scientific_rerun_forbidden"] is True
    assert document["failure_reclassified_as_success"] is False


def test_v181r5_failure_keeps_formal_gates_locked() -> None:
    document = failure.freeze_open_world_failure_v181r5().to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
