from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_history_manifest_v42 as history


ROOT = Path(__file__).resolve().parents[1]
FRESH_BOARDS = (
    (2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)
FRESH_SEEDS = (
    "standard-2048-v42-fresh-terminal-00-7f3c8b19-20260827",
    "standard-2048-v42-fresh-terminal-01-92a64de5-20260827",
)


@pytest.fixture(scope="module")
def history_scan() -> dict:
    return history.scan_standard_2048_git_history_v42(ROOT)


def test_v42_history_scan_exactly_rebuilds_the_frozen_complete_closure(
    history_scan: dict,
) -> None:
    scan = history_scan
    assert history.history_scan_summary_v42(scan) == history.EXPECTED_HISTORY_SCAN_SUMMARY
    summary = history.history_scan_summary_v42(scan)
    assert summary["skipped_oversize_blob_count"] == 0
    assert summary["maximum_reachable_blob_byte_count"] <= summary[
        "maximum_scanned_blob_byte_count"
    ]
    assert summary["scanned_utf8_blob_count"] == summary["reachable_blob_count"]

    # The defect that consumed the first draft is permanently in the
    # regression corpus: this exact V6 board and its D4 orbit must be present.
    reused_v6_board = (0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    assert reused_v6_board in scan["_literal_boards"]
    assert history._d4_orbit_representative(reused_v6_board) in scan["_d4_orbits"]  # noqa: SLF001


def test_v42_replacement_boards_seeds_and_orbits_are_fresh_across_history(
    history_scan: dict,
) -> None:
    scan = history_scan
    proof = history.candidate_freshness_proof_v42(
        scan, boards=FRESH_BOARDS, seeds=FRESH_SEEDS
    )
    assert proof["all_candidates_fresh"] is True
    assert proof["candidate_board_orbits_pairwise_distinct"] is True
    assert all(
        row["exact_board_absent_from_history"]
        and row["d4_orbit_absent_from_history"]
        for row in proof["candidate_boards"]
    )
    assert all(
        row["literal_seed_absent_from_history"]
        and row["seed_bytes_absent_from_every_history_blob"]
        and row["seed_not_generated_by_historical_template"]
        for row in proof["candidate_seeds"]
    )
    manifest = history.freeze_history_manifest_v42(proof)
    assert manifest["freshness_scope"] == (
        "GIT_RETAINED_SOURCE_VISIBLE_PRE_V42_CLOSURE_ONLY"
    )
    assert manifest["unretained_external_or_deleted_history_excluded"] is True
    assert manifest["universal_never_run_claimed"] is False
