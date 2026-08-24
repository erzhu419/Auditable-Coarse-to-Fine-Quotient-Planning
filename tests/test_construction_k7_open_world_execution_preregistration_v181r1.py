from pathlib import Path

from acfqp import construction_k7_open_world_execution_preregistration_v181r1 as prereg


def test_execution_preregistration_freezes_runner_before_outcomes() -> None:
    document = prereg.freeze_open_world_execution_preregistration_v181r1().to_document()
    assert len(document["frozen_source_facts"]) == 9
    assert document["manifest_reveals_accessed"] is True
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False
    assert document["runner_frozen_before_target_outcome_access"] is True
    assert document["same_runner_for_both_arms"] is True
    assert document["only_arm_switch"] == "REUSABLE_SUBPROGRAM_ARCHIVE_AVAILABLE"


def test_frozen_sources_match_current_bytes() -> None:
    document = prereg.freeze_open_world_execution_preregistration_v181r1().to_document()
    base = Path(prereg.__file__).resolve().parent
    assert all((base / row["filename"]).is_file() for row in document["frozen_source_facts"])


def test_execution_preregistration_keeps_official_gates_locked() -> None:
    document = prereg.freeze_open_world_execution_preregistration_v181r1().to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_retained_execution_preregistration_bytes_are_exact() -> None:
    value = prereg.freeze_open_world_execution_preregistration_v181r1()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r1_open_world_execution_preregistration.json"
    )
    assert path.read_bytes() == value.canonical_bytes
