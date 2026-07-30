from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from acfqp import _v075_construction_source_runtime_v2 as helper
from acfqp import v075_construction_source_code_provenance_v2 as authority


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def runtime_lock() -> helper.ConstructionRuntimeDependencyLockV2:
    return helper.verify_construction_runtime_dependency_lock_v2(
        dependency_lock_bytes=(
            PROJECT_ROOT / "specs/V075_DEPENDENCY_LOCK.json"
        ).read_bytes(),
        pyproject_bytes=(PROJECT_ROOT / "pyproject.toml").read_bytes(),
        timeout_seconds=30,
    )


def _toy_sources(
    root: Path,
) -> tuple[dict[str, bytes], dict[str, Path]]:
    package = root / "acfqp"
    package.mkdir()
    sources = {
        "acfqp": b'"""isolated toy package."""\n',
        "acfqp.alpha": b"from acfqp import beta\nVALUE = beta.VALUE\n",
        "acfqp.beta": b"VALUE = 7\n",
        "acfqp.gamma": b"VALUE = 11\n",
        "acfqp.unused": b"VALUE = 13\n",
    }
    paths = {
        "acfqp": package / "__init__.py",
        "acfqp.alpha": package / "alpha.py",
        "acfqp.beta": package / "beta.py",
        "acfqp.gamma": package / "gamma.py",
        "acfqp.unused": package / "unused.py",
    }
    for module_name, path in paths.items():
        path.write_bytes(sources[module_name])
    return sources, paths


def _init_toy_git_repository(root: Path) -> tuple[str, bytes]:
    source = root / "src/acfqp/__init__.py"
    source.parent.mkdir(parents=True)
    raw = b'"""tracked toy package."""\n'
    source.write_bytes(raw)
    environment = {
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
    }
    for arguments in (
        ("init", "-q"),
        ("config", "user.email", "test@example.invalid"),
        ("config", "user.name", "V075 test"),
        ("add", "src/acfqp/__init__.py"),
        ("commit", "-q", "-m", "fixture"),
        ("branch", "-M", "main"),
    ):
        subprocess.run(
            ("/usr/bin/git", "-C", str(root), *arguments),
            check=True,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return "src/acfqp/__init__.py", raw


def test_multiroot_closure_archive_and_exact_isolated_compile_set(
    tmp_path: Path,
    runtime_lock: helper.ConstructionRuntimeDependencyLockV2,
) -> None:
    sources, paths = _toy_sources(tmp_path)
    closure = helper.build_construction_source_closure_v2(
        root_modules=("acfqp.alpha", "acfqp.gamma"),
        module_sources=sources,
        module_paths=paths,
    )
    assert closure.module_names == (
        "acfqp",
        "acfqp.alpha",
        "acfqp.beta",
        "acfqp.gamma",
    )
    assert "acfqp.unused" not in closure.module_names

    first = helper.build_deterministic_source_archive_v2(
        closure=closure,
        module_sources=sources,
    )
    second = helper.build_deterministic_source_archive_v2(
        closure=closure,
        module_sources=sources,
    )
    assert first.archive_bytes == second.archive_bytes
    assert first.archive_id == second.archive_id

    first_compiled = helper.verify_construction_sealed_archive_compile_v2(
        closure=closure,
        archive=first,
        runtime_lock=runtime_lock,
        timeout_seconds=30,
    )
    second_compiled = helper.verify_construction_sealed_archive_compile_v2(
        closure=closure,
        archive=first,
        runtime_lock=runtime_lock,
        timeout_seconds=30,
    )
    assert first_compiled.before_acfqp_modules == ()
    assert first_compiled.after_acfqp_modules == ()
    assert (
        first_compiled.child_result_bytes
        == second_compiled.child_result_bytes
    )
    assert first_compiled.verification_id == second_compiled.verification_id
    document = first_compiled.to_document()
    assert document["child_flags"] == ["-I", "-S"]
    assert document["tested_source_execution_allowed"] is False
    assert document["loaded_source_manifest_claimed"] is False
    child = first_compiled.child_result_document
    assert child["tested_source_execution_allowed"] is False
    assert child["archive_added_to_sys_path"] is False
    assert [item["module_name"] for item in child["compiled_entries"]] == (
        list(closure.module_names)
    )


def test_source_bytes_and_symlink_paths_fail_closed(tmp_path: Path) -> None:
    sources, paths = _toy_sources(tmp_path)
    changed = dict(sources)
    changed["acfqp.alpha"] += b"# changed\n"
    with pytest.raises(
        helper.V075ConstructionSourceRuntimeV2InvariantViolation
    ):
        helper.build_construction_source_closure_v2(
            root_modules=("acfqp.alpha",),
            module_sources=changed,
            module_paths=paths,
        )

    link = tmp_path / "alpha-link.py"
    link.symlink_to(paths["acfqp.alpha"])
    linked_paths = dict(paths)
    linked_paths["acfqp.alpha"] = link
    with pytest.raises(
        helper.V075ConstructionSourceRuntimeV2InvariantViolation
    ):
        helper.build_construction_source_closure_v2(
            root_modules=("acfqp.alpha",),
            module_sources=sources,
            module_paths=linked_paths,
        )


def test_missing_static_acfqp_import_fails_closed(tmp_path: Path) -> None:
    sources, paths = _toy_sources(tmp_path)
    sources["acfqp.alpha"] = b"import acfqp.omitted\n"
    paths["acfqp.alpha"].write_bytes(sources["acfqp.alpha"])
    with pytest.raises(
        helper.V075ConstructionSourceRuntimeV2InvariantViolation,
        match="absent from supplied sources",
    ):
        helper.build_construction_source_closure_v2(
            root_modules=("acfqp.alpha",),
            module_sources=sources,
            module_paths=paths,
        )


def test_runtime_lock_binds_raw_spec_and_usr_bin_python3(
    runtime_lock: helper.ConstructionRuntimeDependencyLockV2,
) -> None:
    assert runtime_lock.requested_executable == "/usr/bin/python3"
    assert runtime_lock.resolved_executable == "/usr/bin/python3.10"
    assert runtime_lock.dependency_lock_id == (
        "777a2108e166af8a991bc953d4584e35d"
        "b210a6a59f5182f2879864b0b7b5b72"
    )
    assert runtime_lock.dependency_lock_document["project"][
        "pyproject_sha256"
    ] == runtime_lock.pyproject_sha256
    assert "dependency_import_paths" not in runtime_lock.to_document()


def test_archived_code_is_compiled_but_never_executed(
    tmp_path: Path,
    runtime_lock: helper.ConstructionRuntimeDependencyLockV2,
) -> None:
    sources, paths = _toy_sources(tmp_path)
    marker = tmp_path / "forged-child-result"
    sources["acfqp"] = (
        b"import os\n"
        + f"open({str(marker)!r}, 'wb').write(b'forged')\n".encode()
        + b"os._exit(0)\n"
    )
    paths["acfqp"].write_bytes(sources["acfqp"])
    closure = helper.build_construction_source_closure_v2(
        root_modules=tuple(sorted(sources)),
        module_sources=sources,
        module_paths=paths,
    )
    archive = helper.build_deterministic_source_archive_v2(
        closure=closure,
        module_sources=sources,
    )
    result = helper.verify_construction_sealed_archive_compile_v2(
        closure=closure,
        archive=archive,
        runtime_lock=runtime_lock,
        timeout_seconds=30,
    )
    assert result.after_acfqp_modules == ()
    assert not marker.exists()


def test_all_candidate_roots_include_literal_dynamic_target(
    tmp_path: Path,
) -> None:
    sources, paths = _toy_sources(tmp_path)
    sources["acfqp.alpha"] = (
        b"import importlib\n"
        b"NAME = 'acfqp.unused'\n"
        b"def later():\n"
        b"    return importlib.import_module(NAME)\n"
    )
    paths["acfqp.alpha"].write_bytes(sources["acfqp.alpha"])
    closure = helper.build_construction_source_closure_v2(
        root_modules=tuple(sorted(sources)),
        module_sources=sources,
        module_paths=paths,
    )
    assert closure.module_names == tuple(sorted(sources))
    assert "acfqp.unused" in closure.module_names


def test_archive_mutation_is_rejected_before_any_source_execution(
    tmp_path: Path,
    runtime_lock: helper.ConstructionRuntimeDependencyLockV2,
) -> None:
    sources, paths = _toy_sources(tmp_path)
    closure = helper.build_construction_source_closure_v2(
        root_modules=tuple(sorted(sources)),
        module_sources=sources,
        module_paths=paths,
    )
    archive = helper.build_deterministic_source_archive_v2(
        closure=closure,
        module_sources=sources,
    )
    object.__setattr__(
        archive,
        "archive_bytes",
        archive.archive_bytes[:-1] + bytes([archive.archive_bytes[-1] ^ 1]),
    )
    with pytest.raises(
        helper.V075ConstructionSourceRuntimeV2InvariantViolation
    ):
        helper.verify_construction_sealed_archive_compile_v2(
            closure=closure,
            archive=archive,
            runtime_lock=runtime_lock,
            timeout_seconds=30,
        )


def test_tracked_blob_rereads_live_worktree_after_capture(
    tmp_path: Path,
) -> None:
    relative, captured = _init_toy_git_repository(tmp_path)
    (tmp_path / relative).write_bytes(captured + b"# post-capture mutation\n")
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="worktree, index, and HEAD bytes differ",
    ):
        authority._tracked_blob(
            tmp_path,
            relative=relative,
            expected_raw=captured,
        )


def test_git_inspection_ignores_fake_path_and_git_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _relative, _captured = _init_toy_git_repository(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    marker = tmp_path / "fake-git-ran"
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/bin/sh\n"
        f"/usr/bin/touch {marker}\n"
        "exit 99\n"
    )
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin))
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "foreign.git"))
    monkeypatch.setenv("GIT_WORK_TREE", "/")
    head = authority._git(tmp_path, "rev-parse", "HEAD")
    assert len(head) == 40
    assert not marker.exists()


def test_rehashed_or_duplicate_dependency_lock_is_rejected() -> None:
    raw = (PROJECT_ROOT / "specs/V075_DEPENDENCY_LOCK.json").read_bytes()
    document = json.loads(raw)
    document["interpreter"]["cache_tag"] = "foreign-cache-tag"
    attacked = json.dumps(document).encode("utf-8")
    with pytest.raises(
        helper.V075ConstructionSourceRuntimeV2InvariantViolation
    ):
        helper.verify_construction_runtime_dependency_lock_v2(
            dependency_lock_bytes=attacked,
            pyproject_bytes=(PROJECT_ROOT / "pyproject.toml").read_bytes(),
            timeout_seconds=30,
        )

    duplicate = b'{"schema":"x","schema":"y"}'
    with pytest.raises(
        helper.V075ConstructionSourceRuntimeV2InvariantViolation,
        match="duplicate JSON key",
    ):
        helper.verify_construction_runtime_dependency_lock_v2(
            dependency_lock_bytes=duplicate,
            pyproject_bytes=(PROJECT_ROOT / "pyproject.toml").read_bytes(),
            timeout_seconds=30,
        )


def test_public_surface_has_no_execution_gate() -> None:
    assert set(helper.__all__) == {
        "ARCHIVE_FORMAT",
        "ConstructionSealedArchiveCompileVerificationV2",
        "ConstructionRuntimeDependencyLockV2",
        "ConstructionSourceArchiveV2",
        "ConstructionSourceClosureV2",
        "ConstructionSourceModuleV2",
        "DEFAULT_TIMEOUT_SECONDS",
        "MAX_TIMEOUT_SECONDS",
        "PROFILE_KEY",
        "PYTHON_EXECUTABLE",
        "SCHEMA_VERSION",
        "STATIC_CLOSURE_RULE",
        "V075ConstructionSourceRuntimeV2InvariantViolation",
        "build_construction_source_closure_v2",
        "build_deterministic_source_archive_v2",
        "verify_construction_sealed_archive_compile_v2",
        "verify_construction_runtime_dependency_lock_v2",
    }
