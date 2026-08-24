from __future__ import annotations

from pathlib import Path

import pytest

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import (
    construction_k7_recovery_eligible_source_closure_successor_v180r7r1
    as successor,
)
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


def _repository_catalogue() -> tuple[dict[str, bytes], dict[str, str]]:
    sources: dict[str, bytes] = {}
    paths: dict[str, str] = {}
    package = ROOT / "src" / "acfqp"
    for path in sorted(package.rglob("*.py")):
        relative = path.relative_to(ROOT / "src")
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        module_name = ".".join(parts)
        sources[module_name] = path.read_bytes()
        paths[module_name] = str(path)
    return sources, paths


def _synthetic_path(root: Path, module_name: str, *, package: bool = False) -> Path:
    relative = Path(*module_name.split("."))
    return (
        root / relative / "__init__.py"
        if package
        else (root / relative).with_suffix(".py")
    )


def _synthetic_catalogue(
    root: Path,
    *,
    unrelated_count: int = 0,
    dynamic_root_count: int = 1,
) -> tuple[dict[str, bytes], dict[str, str], dict[str, bytes]]:
    sources: dict[str, bytes] = {}
    paths: dict[str, str] = {}
    raw_by_path: dict[str, bytes] = {}

    def add(module_name: str, raw: bytes, *, package: bool = False) -> None:
        path = _synthetic_path(root, module_name, package=package)
        sources[module_name] = raw
        paths[module_name] = str(path)
        raw_by_path[str(path)] = raw

    add("acfqp", b"# package\n", package=True)
    add(
        "acfqp.construction_k7_recovery_eligible_accounted_runtime_v1",
        b"from acfqp import reachable_dependency\n",
    )
    add("acfqp.reachable_dependency", b"VALUE = 1\n")
    for index in range(dynamic_root_count):
        add(
            f"acfqp.v075_synthetic_root_{index:04d}",
            b"from acfqp import reachable_dependency\n",
        )
    for index in range(unrelated_count):
        add(f"acfqp.unrelated_{index:04d}", b"UNUSED = True\n")
    return sources, paths, raw_by_path


def _install_synthetic_reader(
    monkeypatch: pytest.MonkeyPatch,
    raw_by_path: dict[str, bytes],
) -> None:
    def read(path: str | Path) -> bytes:
        return raw_by_path[str(path)]

    monkeypatch.setattr(
        successor.source_runtime_v2,
        "_read_regular_symlink_free",
        read,
    )


def test_full_repository_catalogue_over_v2_cap_selects_bounded_exact_closure() -> None:
    sources, paths = _repository_catalogue()
    assert len(sources) > source_runtime_v2.MAX_MODULES

    result = successor.build_recovery_eligible_source_closure_successor_v180r7r1(
        module_sources=sources,
        module_paths=paths,
    )
    document = result.to_document()

    assert len(result.catalog_module_names) == len(sources)
    assert len(result.source_closure.root_modules) == 151
    assert len(result.reachable_module_names) == len(result.source_closure.modules) == 307
    assert result.reachable_source_byte_count == 15_129_926
    assert len(result.reachable_module_names) <= source_runtime_v2.MAX_MODULES
    assert len(result.reachable_module_names) <= successor.MAX_RECOVERY_RUNTIME_FILES
    assert (
        result.reachable_source_byte_count
        <= successor.MAX_RECOVERY_RUNTIME_SOURCE_BYTES
    )
    assert set(result.reachable_module_names) < set(result.catalog_module_names)
    assert document["candidate_catalog"]["module_count"] == len(sources)
    assert (
        document["candidate_catalog"]["source_facts_sha256"]
        == result.catalog_source_facts_sha256
    )
    assert document["reachable_runtime"]["module_count"] == len(
        result.reachable_module_names
    )
    assert document["unchanged_v2_source_runtime"]["max_modules"] == 1_024
    assert document["unchanged_v2_source_runtime"]["v2_constants_mutated"] is False
    assert document["scientific_occurrence_executed"] is False
    assert document["target_outcomes_accessed"] is False
    assert canonical_json_bytes(document) == result.canonical_bytes


def test_only_reachable_subset_is_passed_to_unchanged_v2_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources, paths, raw_by_path = _synthetic_catalogue(
        tmp_path,
        unrelated_count=source_runtime_v2.MAX_MODULES + 8,
    )
    _install_synthetic_reader(monkeypatch, raw_by_path)
    original = successor.source_runtime_v2.build_construction_source_closure_v2
    observed: dict[str, object] = {}

    def capture(**kwargs: object) -> source_runtime_v2.ConstructionSourceClosureV2:
        observed.update(kwargs)
        return original(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        successor.source_runtime_v2,
        "build_construction_source_closure_v2",
        capture,
    )
    result = successor.build_recovery_eligible_source_closure_successor_v180r7r1(
        module_sources=sources,
        module_paths=paths,
    )

    selected_sources = observed["module_sources"]
    selected_paths = observed["module_paths"]
    assert isinstance(selected_sources, dict)
    assert isinstance(selected_paths, dict)
    assert len(sources) > source_runtime_v2.MAX_MODULES
    assert tuple(sorted(selected_sources)) == result.reachable_module_names
    assert tuple(sorted(selected_paths)) == result.reachable_module_names
    assert len(selected_sources) == 4
    assert "acfqp.reachable_dependency" in selected_sources
    assert not any(name.startswith("acfqp.unrelated_") for name in selected_sources)


def test_repair_replay_fails_closed_on_catalogue_or_reachable_byte_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources, paths, raw_by_path = _synthetic_catalogue(
        tmp_path,
        unrelated_count=1,
    )
    _install_synthetic_reader(monkeypatch, raw_by_path)
    frozen = successor.build_recovery_eligible_source_closure_successor_v180r7r1(
        module_sources=sources,
        module_paths=paths,
    )
    replayed = successor.require_recovery_eligible_source_closure_successor_v180r7r1(
        module_sources=sources,
        module_paths=paths,
        expected_repair_id=frozen.repair_id,
    )
    assert replayed.repair_id == frozen.repair_id

    added_name = "acfqp.unrelated_added_after_freeze"
    added_path = _synthetic_path(tmp_path, added_name)
    sources_with_added_name = {**sources, added_name: b"UNUSED = True\n"}
    paths_with_added_name = {**paths, added_name: str(added_path)}
    raw_by_path[str(added_path)] = sources_with_added_name[added_name]
    with pytest.raises(
        successor.ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error,
        match="drifted from its frozen identity",
    ):
        successor.require_recovery_eligible_source_closure_successor_v180r7r1(
            module_sources=sources_with_added_name,
            module_paths=paths_with_added_name,
            expected_repair_id=frozen.repair_id,
        )

    unreachable_name = "acfqp.unrelated_0000"
    original_unreachable_raw = sources[unreachable_name]
    changed_unreachable_sources = dict(sources)
    changed_unreachable_sources[unreachable_name] = b"UNUSED = None\n"
    assert len(changed_unreachable_sources[unreachable_name]) == len(
        original_unreachable_raw
    )
    raw_by_path[paths[unreachable_name]] = changed_unreachable_sources[
        unreachable_name
    ]
    with pytest.raises(
        successor.ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error,
        match="drifted from its frozen identity",
    ):
        successor.require_recovery_eligible_source_closure_successor_v180r7r1(
            module_sources=changed_unreachable_sources,
            module_paths=paths,
            expected_repair_id=frozen.repair_id,
        )
    raw_by_path[paths[unreachable_name]] = original_unreachable_raw

    changed_sources = dict(sources)
    changed_sources["acfqp.reachable_dependency"] = b"VALUE = 2\n"
    raw_by_path[paths["acfqp.reachable_dependency"]] = changed_sources[
        "acfqp.reachable_dependency"
    ]
    with pytest.raises(
        successor.ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error,
        match="drifted from its frozen identity",
    ):
        successor.require_recovery_eligible_source_closure_successor_v180r7r1(
            module_sources=changed_sources,
            module_paths=paths,
            expected_repair_id=frozen.repair_id,
        )


def test_catalogue_module_cap_fails_before_any_path_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources, paths, _raw_by_path = _synthetic_catalogue(
        tmp_path,
        unrelated_count=successor.MAX_CANDIDATE_CATALOG_MODULES,
    )

    def forbidden_read(_path: str | Path) -> bytes:
        pytest.fail("over-cap catalogue crossed the shape guard")

    monkeypatch.setattr(
        successor.source_runtime_v2,
        "_read_regular_symlink_free",
        forbidden_read,
    )
    with pytest.raises(
        successor.ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error,
        match="shape is malformed or over its module cap",
    ):
        successor.build_recovery_eligible_source_closure_successor_v180r7r1(
            module_sources=sources,
            module_paths=paths,
        )


def test_catalogue_source_byte_cap_fails_before_any_path_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources, paths, _raw_by_path = _synthetic_catalogue(tmp_path)
    monkeypatch.setattr(successor, "MAX_CANDIDATE_CATALOG_SOURCE_BYTES", 8)

    def forbidden_read(_path: str | Path) -> bytes:
        pytest.fail("over-byte-cap catalogue crossed the aggregate guard")

    monkeypatch.setattr(
        successor.source_runtime_v2,
        "_read_regular_symlink_free",
        forbidden_read,
    )
    with pytest.raises(
        successor.ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error,
        match="aggregate source-byte cap",
    ):
        successor.build_recovery_eligible_source_closure_successor_v180r7r1(
            module_sources=sources,
            module_paths=paths,
        )


def test_catalogue_rejects_a_real_symlinked_source(
    tmp_path: Path,
) -> None:
    sources, paths, raw_by_path = _synthetic_catalogue(tmp_path)
    for path_text, raw in raw_by_path.items():
        path = Path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    victim = Path(paths["acfqp.reachable_dependency"])
    target = tmp_path / "reachable-target.py"
    target.write_bytes(sources["acfqp.reachable_dependency"])
    victim.unlink()
    victim.symlink_to(target)

    with pytest.raises(
        successor.ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error,
        match="regular symlink-free file",
    ):
        successor.build_recovery_eligible_source_closure_successor_v180r7r1(
            module_sources=sources,
            module_paths=paths,
        )


def test_v2_and_recovery_runtime_file_caps_are_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources, paths, raw_by_path = _synthetic_catalogue(
        tmp_path,
        dynamic_root_count=successor.MAX_RECOVERY_RUNTIME_FILES,
    )
    _install_synthetic_reader(monkeypatch, raw_by_path)
    with pytest.raises(
        successor.ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error,
        match="reachable recovery runtime exceeds its file cap",
    ):
        successor.build_recovery_eligible_source_closure_successor_v180r7r1(
            module_sources=sources,
            module_paths=paths,
        )

    v2_sources, v2_paths, v2_raw_by_path = _synthetic_catalogue(
        tmp_path / "v2",
        dynamic_root_count=successor.V2_MAX_REACHABLE_MODULES,
    )
    _install_synthetic_reader(monkeypatch, v2_raw_by_path)
    with pytest.raises(
        successor.ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error,
        match="roots are absent, duplicated, or over the V2 cap",
    ):
        successor.build_recovery_eligible_source_closure_successor_v180r7r1(
            module_sources=v2_sources,
            module_paths=v2_paths,
        )


def test_public_surface_exposes_build_and_strict_replay_only() -> None:
    assert successor.V2_MAX_REACHABLE_MODULES == source_runtime_v2.MAX_MODULES == 1_024
    assert successor.MAX_RECOVERY_RUNTIME_FILES == 512
    assert successor.MAX_RECOVERY_RUNTIME_SOURCE_BYTES == 16 * 1024 * 1024
    assert {
        "RecoveryEligibleSourceClosureRepairV180r7r1",
        "build_recovery_eligible_source_closure_successor_v180r7r1",
        "require_recovery_eligible_source_closure_successor_v180r7r1",
    } <= set(successor.__all__)
