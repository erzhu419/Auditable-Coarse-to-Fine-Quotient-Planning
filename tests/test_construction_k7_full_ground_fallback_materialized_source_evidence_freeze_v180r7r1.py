from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_full_ground_fallback_materialized_source_evidence_freeze_v180r7r1
    as frozen,
)
from acfqp.phase3e_ids import canonical_json_bytes


@pytest.fixture(scope="module")
def evidence() -> frozen.FrozenFullGroundFallbackMaterializedSourceV180r7r1:
    return frozen.load_frozen_full_ground_fallback_materialized_source_v180r7r1()


def test_materialized_source_manifest_and_tree_are_exactly_frozen(
    evidence: frozen.FrozenFullGroundFallbackMaterializedSourceV180r7r1,
) -> None:
    document = evidence.to_document()
    assert evidence.materialization_manifest_id == (
        "1480c3e0a5bcfe7e88f9cbd6a346efd500c17a1826ca656aa527567a0c8ae7f3"
    )
    assert evidence.materialized_source_tree_id == (
        "5cc30a0a9eea4caa239953af930c8382d3194b2f2ad82847eb9c0ba79b7a2993"
    )
    assert evidence.source_closure_id == (
        "ac3f10ef4eea5c0ecc740d9cecc1991e851a65af198e6696f32bde1965feeb4b"
    )
    assert len(evidence.canonical_bytes) == 340_182
    assert hashlib.sha256(evidence.canonical_bytes).hexdigest() == (
        "790a2dbc89828bc23938e4b09d2d7e0c292e8b7c3b5f92ee0738d540d20e380c"
    )
    assert canonical_json_bytes(document) == evidence.canonical_bytes
    expected_root = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v180r7r1_materialized_source"
    )
    assert evidence.source_root == expected_root
    assert (evidence.source_root / "src" / "acfqp").is_dir()
    assert not frozen._FAILURE_PATH.exists()


def test_all_307_staged_files_and_unchanged_v2_closure_are_replayed(
    evidence: frozen.FrozenFullGroundFallbackMaterializedSourceV180r7r1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = evidence.to_document()
    tree = document["materialized_source_tree"]
    facts = tree["reachable_source_facts"]
    assert len(facts) == 307
    assert sum(row["source_byte_count"] for row in facts) == 15_129_926
    assert hashlib.sha256(canonical_json_bytes(facts)).hexdigest() == (
        "a087ecfac3bcd6132a2242a670b9c38273de3e7bd823b5687e8223a73069772d"
    )
    directories, files = frozen._inventory_tree(evidence.source_root)
    assert len(directories) == 6
    assert len(files) == 307

    calls = 0
    original = frozen.source_runtime_v2.build_construction_source_closure_v2

    def replay_spy(**arguments: object) -> object:
        nonlocal calls
        calls += 1
        return original(**arguments)

    monkeypatch.setattr(
        frozen.source_runtime_v2,
        "build_construction_source_closure_v2",
        replay_spy,
    )
    replayed = (
        frozen.load_frozen_full_ground_fallback_materialized_source_v180r7r1()
    )
    assert calls == 1
    assert replayed.source_closure_id == evidence.source_closure_id
    assert replayed.to_document()["unchanged_v2_source_closure"] == document[
        "unchanged_v2_source_closure"
    ]


def test_construction_work_is_exact_and_all_outcome_gates_remain_locked(
    evidence: frozen.FrozenFullGroundFallbackMaterializedSourceV180r7r1,
) -> None:
    document = evidence.to_document()
    work = document["construction_work"]
    assert work == frozen._CONSTRUCTION_WORK
    assert work["semantic_file_read_count"] == 632
    assert work["semantic_file_read_byte_count"] == 34_073_507
    assert work["durable_file_write_count"] == 308
    assert work["durable_file_write_byte_count"] == 15_470_108
    assert work["occurrence_counter_record_count"] == 0
    assert work["occurrence_route_work_vector_count"] == 0
    assert work["occurrence_comparison_vector_count"] == 0
    assert work["construction_work_excluded_from_occurrence_route_vectors"] is True
    assert document["fresh_execution_authorization_issued"] is False
    assert document["fallback_occurrence_started"] is False
    assert document["scientific_occurrence_executed"] is False
    assert document["production_outcome_accessed"] is False
    assert document["counter_records_issued"] is False
    assert document["route_work_vectors_issued"] is False
    assert document["comparison_vectors_issued"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert document["construction_only"] is True


def test_independent_tree_reader_rejects_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "materialized"
    package = root / "src" / "acfqp"
    package.mkdir(parents=True)
    target = tmp_path / "target.py"
    target.write_bytes(b"value = 1\n")
    linked = package / "linked.py"
    try:
        linked.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    with pytest.raises(
        frozen.FullGroundFallbackMaterializedSourceEvidenceFreezeV180r7r1Error,
        match="symlink",
    ):
        frozen._inventory_tree(root)
