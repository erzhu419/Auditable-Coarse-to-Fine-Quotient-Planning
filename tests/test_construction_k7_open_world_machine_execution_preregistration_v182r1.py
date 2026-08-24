from __future__ import annotations

from acfqp import construction_k7_open_world_machine_execution_preregistration_v182r1 as preregistration


def test_v182r1_execution_is_fresh_outcome_free_and_zero_worker() -> None:
    frozen = preregistration.freeze_open_world_machine_execution_preregistration_v182r1()
    document = frozen.to_document()
    assert document["execution_preregistration_id"] == (
        frozen.execution_preregistration_id
    )
    assert len(document["source_facts"]) == 11
    assert document["output_root_must_be_absent"] is True
    assert document["same_identity_rerun_after_any_progress_forbidden"] is True
    assert document["source_and_target_outcome_execution_started"] is False
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["two_worker_cap"] == 2
    assert document["actual_worker_process_count"] == 0
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
