from pathlib import Path

import pytest

from acfqp import construction_k7_ten_terminal_aggregation_finalizer_v180r12r1 as finalizer


def test_v180r12r1_finalizer_rejects_an_incomplete_source_denominator(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R1Error,
        match="V180r11 terminal is absent",
    ):
        finalizer.materialize_ten_terminal_aggregation_v180r12r1(tmp_path)


def test_v180r12r1_finalizer_has_exact_nine_path_orchestration_boundary() -> None:
    assert len(finalizer.SHARED_RESOURCE_PATHS) == 9
    assert finalizer.WORKING_BYTES_HARD_CAP == 4 * 1024 * 1024 * 1024
