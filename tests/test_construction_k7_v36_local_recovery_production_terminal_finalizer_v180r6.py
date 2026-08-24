from pathlib import Path

import pytest

from acfqp import construction_k7_v36_local_recovery_production_terminal_finalizer_v180r6 as finalizer


def test_v36_adapter_refuses_a_preexisting_output_tree(tmp_path: Path) -> None:
    root = tmp_path / "already-present"
    root.mkdir()
    with pytest.raises(
        finalizer.ConstructionK7V36ProductionTerminalFinalizerV180r6Error,
        match="new absent Path",
    ):
        finalizer.run_v36_local_ground_recovery_production_occurrence_v180r6(root)


def test_absent_platform_path_reaches_v35_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "absent-output"

    def reached() -> None:
        raise RuntimeError("V35 boundary reached")

    monkeypatch.setattr(
        finalizer.v35_campaign,
        "run_standard_2048_adaptive_expression_campaign_v35",
        reached,
    )
    with pytest.raises(RuntimeError, match="V35 boundary reached"):
        finalizer.run_v36_local_ground_recovery_production_occurrence_v180r6(root)


def test_local_recovery_adapter_uses_no_historical_summary_input() -> None:
    assert finalizer.EXPECTED_OPERATIONAL_WORK_VECTOR_COUNT == 15
    assert "historical" not in (
        finalizer.run_v36_local_ground_recovery_production_occurrence_v180r6.__annotations__
    )
