import hashlib
import os
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_ten_terminal_aggregation_stale_predecessor_freeze_v180r12r2
    as stale,
)


def test_v180r12r2_preserves_r12_and_freezes_r12r1_stale_unexecuted() -> None:
    frozen = stale.freeze_ten_terminal_aggregation_stale_predecessor_v180r12r2()
    document = frozen.to_document()
    assert len(frozen.stale_predecessor_id) == 64
    assert document["preserved_v180r12_protocol_id"] == (
        stale.PRESERVED_V180R12_PROTOCOL_ID
    )
    assert document["preserved_v180r12_failure_id"] == (
        stale.PRESERVED_V180R12_FAILURE_ID
    )
    assert document["preserved_v180r12r1_protocol_id"] == (
        stale.PRESERVED_V180R12R1_PROTOCOL_ID
    )
    assert document["preserved_v180r12r1_authorization_id"] == (
        stale.PRESERVED_V180R12R1_AUTHORIZATION_ID
    )
    assert document["v180r12r1_status"] == "STALE_UNEXECUTED"
    assert document["v180r12r1_authorization_execution_count"] == 0
    assert document["v180r12r1_same_authorization_execution_forbidden"] is True
    assert document["v180r12r1_same_logical_occurrence_reuse_forbidden"] is True
    assert document["v180r12r2_outcome_accessed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
    if stale.EXPECTED_STALE_PREDECESSOR_ID != "0" * 64:
        assert frozen.stale_predecessor_id == stale.EXPECTED_STALE_PREDECESSOR_ID
        assert len(frozen.canonical_bytes) == stale.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
            stale.EXPECTED_CANONICAL_SHA256
        )


def test_v180r12r2_stale_record_binds_all_four_predecessor_canonical_facts() -> None:
    document = stale.build_ten_terminal_aggregation_stale_predecessor_v180r12r2()
    facts = document["preserved_canonical_facts"]
    assert set(facts) == {
        "v180r12_protocol",
        "v180r12_failure",
        "v180r12r1_protocol",
        "v180r12r1_authorization",
    }
    assert facts["v180r12r1_authorization"] == {
        "content_id": stale.PRESERVED_V180R12R1_AUTHORIZATION_ID,
        "byte_count": 6_041,
        "sha256": (
            "11f89eb57dfdb7e3e480fae93cf195f5ef7a30ec43b1751e59bfc7d3e38b2f83"
        ),
    }


def test_v180r12r2_stale_absence_check_rejects_dangling_leaf(
    tmp_path: Path,
) -> None:
    (tmp_path / "safe").mkdir()
    os.symlink("missing-target", tmp_path / "safe" / "stale-output")
    with pytest.raises(
        stale.TenTerminalAggregationStalePredecessorV180R12R2Error,
        match="progress or a linked leaf",
    ):
        stale._require_absent_symlink_free_target(  # noqa: SLF001
            tmp_path,
            "safe/stale-output",
        )


def test_v180r12r2_stale_absence_check_rejects_symlink_ancestor(
    tmp_path: Path,
) -> None:
    (tmp_path / "real").mkdir()
    os.symlink("real", tmp_path / "linked")
    with pytest.raises(
        stale.TenTerminalAggregationStalePredecessorV180R12R2Error,
        match="ancestor is linked",
    ):
        stale._require_absent_symlink_free_target(  # noqa: SLF001
            tmp_path,
            "linked/stale-output",
        )
