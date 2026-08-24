from __future__ import annotations

from pathlib import Path

import pytest

from acfqp.construction_k7_open_world_campaign_v181r2 import (
    DurableProgressV181R2,
    OpenWorldCampaignV181R2Error,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


def test_durable_progress_records_exact_manifest_arm_and_block(tmp_path: Path) -> None:
    progress = DurableProgressV181R2(tmp_path, "a" * 64)
    first = progress.append(
        stage="ACQUISITION_BLOCK_RETAINED_BEFORE_MINIMUM",
        manifest_index=2,
        arm="REUSED_SUBPROGRAM_PRIOR",
        block_index=0,
    )
    second = progress.append(
        stage="DISTRIBUTION_COMPLETE",
        manifest_index=2,
        arm=None,
        block_index=None,
        row_ids=("b" * 64,),
    )
    assert first["manifest_index"] == 2
    assert first["arm"] == "REUSED_SUBPROGRAM_PRIOR"
    assert first["block_index"] == 0
    assert second["previous_checkpoint_id"] == first["progress_checkpoint_id"]
    assert progress.last_checkpoint_id == second["progress_checkpoint_id"]
    assert progress.checkpoint_ids == (
        first["progress_checkpoint_id"],
        second["progress_checkpoint_id"],
    )
    for index, expected in enumerate((first, second)):
        raw = (tmp_path / f"checkpoint-{index:04d}.json").read_bytes()
        assert raw == canonical_json_bytes(expected)
        assert loads_canonical_json(raw) == expected


def test_progress_directory_must_begin_fresh(tmp_path: Path) -> None:
    (tmp_path / "checkpoint-0000.json").write_text("occupied")
    with pytest.raises(OpenWorldCampaignV181R2Error, match="begin fresh"):
        DurableProgressV181R2(tmp_path, "a" * 64)


def test_progress_claims_remain_nonofficial(tmp_path: Path) -> None:
    document = DurableProgressV181R2(tmp_path, "a" * 64).append(
        stage="ACQUISITION_BLOCK_COMPILE_FAILED",
        manifest_index=0,
        arm="EMPTY_ARCHIVE_NO_PRIOR",
        block_index=1,
        failure=ValueError("bounded failure"),
    )
    assert document["failure_type"] == "ValueError"
    assert document["target_outcome_progress_not_success_claim"] is True
    assert document["official_execution_allowed"] is False
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
