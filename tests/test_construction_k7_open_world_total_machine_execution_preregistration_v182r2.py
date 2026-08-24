from pathlib import Path

from acfqp import construction_k7_open_world_total_machine_execution_preregistration_v182r2 as registration


ROOT = Path(__file__).resolve().parents[1]


def test_v182r2_execution_is_fresh_outcome_free_and_source_closed() -> None:
    document = registration.freeze_open_world_total_machine_execution_preregistration_v182r2().to_document()
    assert document["execution_preregistration_id"] == registration.EXPECTED_PREREGISTRATION_ID
    assert document["failed_predecessor_failure_id"] == registration.FAILED_PREDECESSOR_FAILURE_ID
    assert document["failed_predecessor_output_must_remain_preserved"] is True
    assert document["source_and_target_outcome_execution_started"] is False
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["actual_worker_process_count"] == 0
    assert document["two_worker_cap"] == 2
    assert document["candidate_admission_requires_full_finite_carrier_totality"] is True
    assert document["official_execution_allowed"] is False
    for fact in document["source_facts"]:
        path = ROOT / fact["relative_path"]
        assert path.is_file()
        assert len(path.read_bytes()) == fact["byte_count"]


def test_v182r2_output_root_is_absent_before_execution() -> None:
    document = registration.freeze_open_world_total_machine_execution_preregistration_v182r2().to_document()
    root = ROOT / document["output_root_relative_path"]
    assert root.exists() is False
