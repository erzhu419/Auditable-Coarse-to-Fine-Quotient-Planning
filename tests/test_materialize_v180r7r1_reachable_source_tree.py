from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v180r7r1m1 as domains
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import materialize_v180r7r1_reachable_source_tree as materializer


@pytest.fixture(scope="module")
def plan() -> materializer.MaterializationPlanV180r7r1m1:
    return materializer.build_materialization_plan_v180r7r1m1()


def test_materialization_plan_consumes_only_exact_frozen_reachable_sources(
    plan: materializer.MaterializationPlanV180r7r1m1,
) -> None:
    assert plan.catalog_manifest_id == materializer.EXPECTED_CATALOG_MANIFEST_ID
    assert plan.source_boundary_commit == (
        materializer.EXPECTED_SOURCE_BOUNDARY_COMMIT
    )
    assert plan.source_inventory_preregistration_id == (
        materializer.EXPECTED_SOURCE_INVENTORY_PREREGISTRATION_ID
    )
    assert plan.source_closure_repair_id == (
        materializer.EXPECTED_SOURCE_CLOSURE_REPAIR_ID
    )
    assert len(plan.root_modules) == 151
    assert len(plan.reachable_sources) == 307
    assert plan.reachable_source_byte_count == 15_129_926
    assert [item.module_name for item in plan.reachable_sources] == sorted(
        {item.module_name for item in plan.reachable_sources}
    )
    assert hashlib.sha256(
        canonical_json_bytes(plan.reachable_source_facts)
    ).hexdigest() == materializer.EXPECTED_REACHABLE_SOURCE_FACTS_SHA256
    assert all(
        item.staged_relative_path.startswith("src/acfqp/")
        or item.staged_relative_path == "src/acfqp/__init__.py"
        for item in plan.reachable_sources
    )
    assert plan.expected_source_closure["closure_id"] == (
        materializer.EXPECTED_SOURCE_CLOSURE_ID
    )
    assert not materializer.MATERIALIZED_ROOT.exists()
    assert not materializer.OUTPUT_MANIFEST_PATH.exists()


def test_materialization_manifest_is_canonical_self_counted_and_outcome_free(
    plan: materializer.MaterializationPlanV180r7r1m1,
) -> None:
    document, raw = materializer.build_materialization_manifest_v180r7r1m1(
        plan=plan,
        materialized_source_closure=plan.expected_source_closure,
        tree_directory_count=7,
    )
    payload = dict(document)
    identity = payload.pop("materialization_manifest_id")
    assert identity == domains.extension_content_id_v180r7r1m1(
        domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_MANIFEST_V180R7R1M1_DOMAIN,
        payload,
    )
    assert canonical_json_bytes(document) == raw
    assert document["construction_work"]["materialization_manifest_write"][
        "byte_count"
    ] == len(raw)
    tree = document["materialized_source_tree"]
    tree_payload = dict(tree)
    tree_identity = tree_payload.pop("materialized_source_tree_id")
    assert tree_identity == domains.extension_content_id_v180r7r1m1(
        domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_V180R7R1M1_DOMAIN,
        tree_payload,
    )
    assert tree["materialized_source_file_count"] == 307
    assert tree["materialized_source_byte_count"] == 15_129_926
    assert document["unchanged_v2_source_closure_id"] == (
        materializer.EXPECTED_SOURCE_CLOSURE_ID
    )
    assert document["unchanged_v2_source_closure"] == (
        plan.expected_source_closure
    )
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


def test_materialization_manifest_accounts_construction_not_route_work(
    plan: materializer.MaterializationPlanV180r7r1m1,
) -> None:
    document, raw = materializer.build_materialization_manifest_v180r7r1m1(
        plan=plan,
        materialized_source_closure=plan.expected_source_closure,
        tree_directory_count=7,
    )
    work = document["construction_work"]
    producer_bytes = sum(
        row["byte_count"] for row in plan.producer_source_facts
    )
    assert work["retained_identity_validation_reads"] == {
        "file_count": 16,
        "byte_count": 3_765_861,
        "sha256_file_identity_checks": 16,
    }
    assert work["live_reachable_source_reads"] == {
        "file_count": 307,
        "byte_count": 15_129_926,
        "sha256_source_fact_checks": 307,
    }
    assert work["materialized_source_writes"] == {
        "file_count": 307,
        "byte_count": 15_129_926,
        "file_fsync_count": 307,
    }
    assert work["unchanged_v2_materialized_source_replay_reads"] == {
        "file_count": 307,
        "byte_count": 15_129_926,
        "caller_supplied_byte_equality_checks": 307,
        "source_digest_constructions": 307,
    }
    assert work["semantic_file_read_count"] == 632
    assert work["semantic_file_read_byte_count"] == (
        3_765_861 + producer_bytes + 2 * 15_129_926
    )
    assert work["durable_file_write_count"] == 308
    assert work["durable_file_write_byte_count"] == 15_129_926 + len(raw)
    assert work["file_fsync_count"] == 308
    assert work["directory_fsync_count"] == 9
    assert work["occurrence_counter_record_count"] == 0
    assert work["occurrence_route_work_vector_count"] == 0
    assert work["occurrence_comparison_vector_count"] == 0
    assert work["construction_work_excluded_from_occurrence_route_vectors"] is True


def test_reachable_source_reader_rejects_symlinks(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    package = source_root / "acfqp"
    package.mkdir(parents=True)
    target = tmp_path / "target.py"
    target.write_bytes(b"value = 1\n")
    linked = package / "linked.py"
    try:
        linked.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    raw = target.read_bytes()
    fact = {
        "module_name": "acfqp.linked",
        "relative_path": "acfqp/linked.py",
        "source_byte_count": len(raw),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
    }
    with pytest.raises(
        materializer.V180r7r1MaterializedSourceTreeError,
        match="linked",
    ):
        materializer._read_exact_source(fact, source_root=source_root)


def test_write_once_helpers_use_o_excl_and_fsync_file_and_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "source.py"
    fsync_descriptors: list[int] = []
    monkeypatch.setattr(materializer.os, "fsync", fsync_descriptors.append)
    materializer._write_file_once(target, b"value = 1\n")
    assert target.read_bytes() == b"value = 1\n"
    assert len(fsync_descriptors) == 1
    with pytest.raises(FileExistsError):
        materializer._write_file_once(target, b"value = 2\n")

    manifest_target = tmp_path / "manifest.json"
    materializer._write_manifest_once(manifest_target, b"{}")
    assert manifest_target.read_bytes() == b"{}"
    assert len(fsync_descriptors) == 3
    with pytest.raises(FileExistsError):
        materializer._write_manifest_once(manifest_target, b"{}")


def test_preexisting_progress_is_frozen_as_typed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materialized_root = tmp_path / "materialized"
    source_root = materialized_root / "src" / "acfqp"
    source_root.mkdir(parents=True)
    partial = source_root / "partial.py"
    partial.write_bytes(b"partial = True\n")
    output_path = tmp_path / "materialization.json"
    failure_path = tmp_path / "failure.json"
    monkeypatch.setattr(materializer, "MATERIALIZED_ROOT", materialized_root)
    monkeypatch.setattr(materializer, "OUTPUT_MANIFEST_PATH", output_path)
    monkeypatch.setattr(materializer, "FAILURE_PATH", failure_path)

    with pytest.raises(
        materializer.V180r7r1MaterializedSourceTreeError,
        match="already exists",
    ):
        materializer.main()
    raw = failure_path.read_bytes()
    document = materializer.loads_canonical_json(raw)
    assert canonical_json_bytes(document) == raw
    payload = dict(document)
    identity = payload.pop("materialized_source_tree_failure_id")
    assert identity == domains.extension_content_id_v180r7r1m1(
        domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_FAILURE_V180R7R1M1_DOMAIN,
        payload,
    )
    progress = document["materialized_progress_inventory"]
    assert progress["materialized_root"]["presence"] == "DIRECTORY"
    assert progress["regular_file_count"] == 1
    assert progress["regular_file_byte_count"] == len(b"partial = True\n")
    assert progress["entry_count"] == 3
    assert document["failed_phase"] == "PREEXISTING_PROGRESS_CHECK"
    assert document["same_materialization_identity_rerun_forbidden"] is True
    assert document["scientific_occurrence_executed"] is False
    assert document["success_claimed"] is False
    with pytest.raises(
        materializer.V180r7r1MaterializedSourceTreeError,
        match="failure evidence already exists",
    ):
        materializer.main()


def test_failure_write_or_fsync_error_leaves_o_excl_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "failure.json"
    raw = b'{"failure":true}'

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr(materializer.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="injected fsync failure"):
        materializer._write_failure_once(target, raw)
    assert target.read_bytes() == raw
    with pytest.raises(FileExistsError):
        materializer._write_failure_once(target, raw)


def test_exact_completed_tree_and_manifest_reject_replay_without_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materialized_root = tmp_path / "materialized"
    materialized_root.mkdir()
    output_path = tmp_path / "materialization.json"
    output_path.write_bytes(b"exact terminal placeholder")
    failure_path = tmp_path / "failure.json"
    monkeypatch.setattr(materializer, "MATERIALIZED_ROOT", materialized_root)
    monkeypatch.setattr(materializer, "OUTPUT_MANIFEST_PATH", output_path)
    monkeypatch.setattr(materializer, "FAILURE_PATH", failure_path)
    monkeypatch.setattr(
        materializer,
        "_exact_completed_materialization_present",
        lambda: True,
    )
    with pytest.raises(
        materializer.V180r7r1MaterializedSourceTreeError,
        match="already completed; replay forbidden",
    ):
        materializer.main()
    assert not failure_path.exists()


def test_lone_or_tampered_success_manifest_is_typed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materialized_root = tmp_path / "absent-materialized"
    output_path = tmp_path / "materialization.json"
    output_path.write_bytes(b"tampered")
    failure_path = tmp_path / "failure.json"
    monkeypatch.setattr(materializer, "MATERIALIZED_ROOT", materialized_root)
    monkeypatch.setattr(materializer, "OUTPUT_MANIFEST_PATH", output_path)
    monkeypatch.setattr(materializer, "FAILURE_PATH", failure_path)
    with pytest.raises(
        materializer.V180r7r1MaterializedSourceTreeError,
        match="manifest already exists",
    ):
        materializer.main()
    document = materializer.loads_canonical_json(failure_path.read_bytes())
    assert document["materialized_progress_inventory"]["materialized_root"][
        "presence"
    ] == "ABSENT"
    assert document["materialization_manifest_state"] == {
        "presence": "REGULAR_FILE",
        "byte_count": len(b"tampered"),
        "sha256": hashlib.sha256(b"tampered").hexdigest(),
    }
    assert document["same_materialization_identity_rerun_forbidden"] is True
    assert document["success_claimed"] is False


def test_one_shot_entrypoint_is_fixed_and_does_not_authorize_an_occurrence() -> None:
    source = Path(materializer.__file__).read_text(encoding="utf-8")
    assert "v180r7r1_materialized_source/src/acfqp" not in source
    assert '"v180r7r1_materialized_source"' in source
    assert '"v180r7r1_materialized_source_manifest.json"' in source
    assert '"v180r7r1_materialized_source_failure.json"' in source
    assert "source_runtime_v2.build_construction_source_closure_v2(" in source
    assert "closure.closure_id == EXPECTED_SOURCE_CLOSURE_ID" in source
    assert "os.O_EXCL" in source
    assert "os.fsync(descriptor)" in source
    assert "_fsync_directory(path.parent)" in source
    assert "if os.path.lexists(MATERIALIZED_ROOT)" in source
    assert "if os.path.lexists(OUTPUT_MANIFEST_PATH)" in source
    assert "_exact_completed_materialization_present()" in source
    assert "except BaseException as error:" in source
    assert "_write_failure_once(FAILURE_PATH, failure_raw)" in source
    assert "fallback_execution_authorization_v180r7r1" not in source
    assert "CounterRecord" not in source
    assert "WorkVector" not in source
    assert "ComparisonVector" not in source
    assert not materializer.MATERIALIZED_ROOT.exists()
    assert not materializer.OUTPUT_MANIFEST_PATH.exists()
    assert not materializer.FAILURE_PATH.exists()
