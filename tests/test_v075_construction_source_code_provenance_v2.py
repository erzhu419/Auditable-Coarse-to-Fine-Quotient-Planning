from __future__ import annotations

import ast
from dataclasses import fields
import hashlib
import inspect
from pathlib import Path
import pickle
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_construction_source_code_provenance_v2 as authority
from acfqp import (
    v075_construction_source_code_provenance_independent_verifier_v2
    as independent,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), *args),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _small_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    package = root / "src" / "acfqp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "root.py").write_text(
        "from acfqp import support\nVALUE = support.VALUE\n",
        encoding="utf-8",
    )
    (package / "support.py").write_text("VALUE = 7\n", encoding="utf-8")
    (root / "specs").mkdir()
    (root / "specs" / "V075_DEPENDENCY_LOCK.json").write_bytes(
        canonical_json_bytes(
            {
                "schema": "test",
                "runtime_dependency_lock_id": _id("lock"),
            }
        )
    )
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "fixture")
    return root


def _entry(name: str) -> authority.V075ConstructionGitSourceEntryV2:
    relative = (
        "src/acfqp/__init__.py"
        if name == "acfqp"
        else "src/" + name.replace(".", "/") + ".py"
    )
    return authority.V075ConstructionGitSourceEntryV2(
        name,
        relative,
        "100644",
        "a" * 40,
        _id(f"source:{name}"),
        100 + len(name),
        _id(f"runtime:{name}"),
    )


def test_raw_entry_and_currentness_signatures_are_exact() -> None:
    raw = (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )
    assert tuple(
        inspect.signature(
            authority.replay_v075_construction_source_code_provenance_v2
        ).parameters
    ) == raw
    assert tuple(
        inspect.signature(
            authority.V075ConstructionSourceCodeProvenanceClosureV2
            .assert_current
        ).parameters
    ) == ("self", *raw)
    assert tuple(
        inspect.signature(
            independent
            .verify_v075_construction_source_code_provenance_bytes_v2
        ).parameters
    ) == ("closure_bytes", *raw)
    assert authority.ROOT_MODULES == tuple(
        sorted(
            (
                authority.UPSTREAM_ROOT_MODULE,
                authority.AUTHORITY_ROOT_MODULE,
                authority.INDEPENDENT_VERIFIER_ROOT_MODULE,
            )
        )
    )


def test_raw_182_is_first_and_only_work_when_it_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def raw(**_kwargs):
        calls.append("1.82")
        raise RuntimeError("private marker")

    def forbidden(**_kwargs):
        calls.append("forbidden")
        raise AssertionError("post-1.82 work ran early")

    monkeypatch.setattr(
        authority.terminal,
        "replay_v075_portable_semantic_terminal_closure_v2",
        raw,
    )
    monkeypatch.setattr(authority, "_freeze_after_raw_182", forbidden)
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation
    ) as captured:
        authority.replay_v075_construction_source_code_provenance_v2(
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["1.82"]
    assert str(captured.value) == authority._REPLAY_MISMATCH  # noqa: SLF001
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    assert "private marker" not in str(captured.value)


def test_independent_verifier_does_not_read_claim_before_raw_182(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def raw(**_kwargs):
        calls.append("1.82")
        raise RuntimeError("private marker")

    def forbidden(_raw):
        calls.append("claim")
        raise AssertionError("claim was read before raw replay")

    monkeypatch.setattr(
        independent.terminal,
        "replay_v075_portable_semantic_terminal_closure_v2",
        raw,
    )
    monkeypatch.setattr(independent, "_strict_document", forbidden)
    with pytest.raises(
        independent
        .V075ConstructionSourceCodeProvenanceIndependentV2Violation
    ) as captured:
        independent.verify_v075_construction_source_code_provenance_bytes_v2(
            closure_bytes=b"claimed",
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["1.82"]
    assert str(captured.value) == independent._REPLAY_MISMATCH  # noqa: SLF001
    assert captured.value.__cause__ is None


def test_independent_verifier_ast_forbids_producer_replay_and_freezer() -> None:
    source = inspect.getsource(independent)
    assert "_freeze_after_raw_182" not in source
    assert "verify_construction_loaded_modules_isolated_v2" not in source
    assert '"loaded_source_verification"' not in source
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "acfqp":
            assert all(
                alias.name
                != "v075_construction_source_code_provenance_v2"
                for alias in node.names
            )
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Attribute):
                assert function.attr not in {
                    "_freeze_after_raw_182",
                    "replay_v075_construction_source_code_provenance_v2",
                }
            elif isinstance(function, ast.Name):
                assert function.id not in {
                    "_freeze_after_raw_182",
                    "replay_v075_construction_source_code_provenance_v2",
                }


def test_independent_git_ignores_path_and_git_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _small_repo(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    marker = tmp_path / "fake-git-ran"
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/bin/sh\n"
        f"/usr/bin/touch {marker}\n"
        "exit 99\n",
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin))
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "foreign.git"))
    monkeypatch.setenv("GIT_WORK_TREE", "/")
    assert len(independent._git(root, "rev-parse", "HEAD")) == 40  # noqa: SLF001
    assert not marker.exists()


def test_independent_rejects_claimed_loaded_source_true(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _small_repo(tmp_path)
    expected = {
        "schema": "test.expected.construction.provenance",
        "construction_sealed_source_compile_manifest_complete": True,
        "construction_loaded_source_manifest_complete": False,
        "future_target_worker_loaded_code_attested": False,
        "closure_id": _id("expected-closure"),
    }
    attacked = {
        **expected,
        "construction_loaded_source_manifest_complete": True,
    }
    monkeypatch.setattr(
        independent.terminal,
        "replay_v075_portable_semantic_terminal_closure_v2",
        lambda **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        independent,
        "_reconstruct_document",
        lambda **_kwargs: expected,
    )
    with pytest.raises(
        independent
        .V075ConstructionSourceCodeProvenanceIndependentV2Violation
    ):
        independent.verify_v075_construction_source_code_provenance_bytes_v2(
            closure_bytes=canonical_json_bytes(attacked),
            repository_root=root,
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )


def test_real_all_tracked_helper_archive_and_isolated_compile_set() -> None:
    root = Path(__file__).resolve().parents[1]
    sources, paths, _relatives = authority._candidate_sources(  # noqa: SLF001
        root
    )
    helper = independent.source_runtime
    closure = helper.build_construction_source_closure_v2(
        root_modules=tuple(sorted(sources)),
        module_sources=sources,
        module_paths=paths,
    )
    runtime_lock = helper.verify_construction_runtime_dependency_lock_v2(
        dependency_lock_bytes=(
            root / authority.DEPENDENCY_LOCK_PATH
        ).read_bytes(),
        pyproject_bytes=(root / authority.PYPROJECT_PATH).read_bytes(),
        timeout_seconds=30,
    )
    archive = helper.build_deterministic_source_archive_v2(
        closure=closure,
        module_sources=sources,
    )
    compiled = helper.verify_construction_sealed_archive_compile_v2(
        closure=closure,
        archive=archive,
        runtime_lock=runtime_lock,
        timeout_seconds=30,
    )
    assert set(authority.ROOT_MODULES) <= set(closure.module_names)
    assert closure.root_modules == tuple(sorted(sources))
    assert compiled.before_acfqp_modules == ()
    assert compiled.after_acfqp_modules == ()
    assert compiled.source_archive_id == archive.archive_id
    assert (
        compiled.child_result_document["tested_source_execution_allowed"]
        is False
    )
    assert archive.archive_byte_count == len(archive.archive_bytes)


def test_independent_reconstruction_matches_producer_in_committed_clone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = Path(__file__).resolve().parents[1]
    root = tmp_path / "committed-construction"
    shutil.copytree(source_root / "src", root / "src")
    (root / "specs").mkdir()
    shutil.copy2(
        source_root / authority.DEPENDENCY_LOCK_PATH,
        root / authority.DEPENDENCY_LOCK_PATH,
    )
    shutil.copy2(source_root / authority.PYPROJECT_PATH, root / "pyproject.toml")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "construction fixture")

    sources, paths, _relatives = authority._candidate_sources(  # noqa: SLF001
        root
    )
    runtime_closure = (
        independent.source_runtime.build_construction_source_closure_v2(
            root_modules=authority.ROOT_MODULES,
            module_sources=sources,
            module_paths=paths,
        )
    )
    old_entries = tuple(
        SimpleNamespace(
            module_name=item.module_name,
            relative_path=item.relative_path,
            source_sha256=item.source_sha256,
            source_byte_count=item.source_byte_count,
        )
        for item in runtime_closure.modules[
            : authority.EXPECTED_OCCURRENCE_SOURCE_ENTRY_COUNT
        ]
    )
    manifest_raw = canonical_json_bytes(
        {
            "entries": [
                {
                    "module_name": item.module_name,
                    "relative_path": item.relative_path,
                    "source_sha256": item.source_sha256,
                    "source_byte_count": item.source_byte_count,
                }
                for item in old_entries
            ]
        }
    )
    manifest = SimpleNamespace(
        entries=old_entries,
        manifest_id=_id("committed-manifest"),
        canonical_bytes=manifest_raw,
    )
    upstream = SimpleNamespace(
        terminal_closure_id=_id("terminal"),
        portable_bundle_id=_id("bundle"),
        occurrence_id=_id("occurrence"),
        public_context_closure_id=_id("context"),
        source_manifest_id=manifest.manifest_id,
        source_manifest=manifest,
    )
    monkeypatch.setattr(
        authority.terminal,
        "V075PortableSemanticTerminalClosureV2",
        SimpleNamespace,
    )
    portable = b"portable"
    produced = authority._freeze_after_raw_182(  # noqa: SLF001
        repository_root=root,
        upstream=upstream,
        portable_bundle_bytes=portable,
    )
    independently_reconstructed = independent._reconstruct_document(  # noqa: SLF001
        root=root.resolve(strict=True),
        upstream=upstream,
        portable_bundle_bytes=portable,
    )
    assert produced.to_document() == independently_reconstructed
    assert produced.canonical_bytes == canonical_json_bytes(
        independently_reconstructed
    )


def test_git_source_requires_regular_committed_head_index_worktree(
    tmp_path: Path,
) -> None:
    root = _small_repo(tmp_path)
    relative = "src/acfqp/root.py"
    raw = (root / relative).read_bytes()
    mode, blob = authority._tracked_blob(  # noqa: SLF001
        root,
        relative=relative,
        expected_raw=raw,
    )
    assert mode == "100644"
    assert blob == _git(root, "rev-parse", f"HEAD:{relative}")

    (root / relative).write_text("VALUE = 8\n", encoding="utf-8")
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="worktree, index, and HEAD",
    ):
        authority._tracked_blob(  # noqa: SLF001
            root,
            relative=relative,
            expected_raw=(root / relative).read_bytes(),
        )
    _git(root, "restore", "--source=HEAD", "--staged", "--worktree", relative)

    (root / relative).write_text("VALUE = 9\n", encoding="utf-8")
    _git(root, "add", relative)
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="worktree, index, and HEAD",
    ):
        authority._tracked_blob(  # noqa: SLF001
            root,
            relative=relative,
            expected_raw=(root / relative).read_bytes(),
        )


def test_symlink_and_untracked_source_are_rejected(tmp_path: Path) -> None:
    root = _small_repo(tmp_path)
    target = root / "src" / "acfqp" / "support.py"
    link = root / "src" / "acfqp" / "link.py"
    link.symlink_to(target)
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="symlink",
    ):
        authority._regular_no_symlink(  # noqa: SLF001
            root, "src/acfqp/link.py"
        )
    untracked = root / "src" / "acfqp" / "untracked.py"
    untracked.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="stage-zero",
    ):
        authority._tracked_blob(  # noqa: SLF001
            root,
            relative="src/acfqp/untracked.py",
            expected_raw=untracked.read_bytes(),
        )


def test_head_must_equal_local_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _small_repo(tmp_path)
    _git(root, "switch", "-c", "other")
    (root / "src" / "acfqp" / "support.py").write_text(
        "VALUE = 10\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "other")
    runtime_closure = SimpleNamespace(
        modules=(),
        source_closure_id=_id("runtime-closure"),
    )
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="HEAD and local main differ",
    ):
        authority._freeze_repository_closure(  # noqa: SLF001
            root=root,
            runtime_closure=runtime_closure,
            module_sources={},
            module_paths={},
            relative_paths={},
        )


def test_occurrence_manifest_is_exact_64_entry_subset() -> None:
    occurrence_names = tuple(
        f"acfqp.occurrence_{index:02d}"
        for index in range(
            authority.EXPECTED_OCCURRENCE_SOURCE_ENTRY_COUNT
        )
    )
    all_names = tuple(
        sorted(
            {
                *occurrence_names,
                *authority.ROOT_MODULES,
                "acfqp.semantic_extra",
            }
        )
    )
    entries = tuple(_entry(name) for name in all_names)
    repository = authority.V075ConstructionLocalRepositoryClosureV2(
        "a" * 40,
        "b" * 40,
        authority.REGISTERED_LOCAL_BRANCH_REF,
        authority.REGISTERED_GIT_EXECUTABLE,
        _id("git executable"),
        1024,
        authority.ROOT_MODULES,
        _id("runtime-closure"),
        entries,
    )
    by_name = {item.module_name: item for item in entries}
    old_entries = tuple(
        SimpleNamespace(
            module_name=name,
            relative_path=by_name[name].relative_path.removeprefix("src/"),
            source_sha256=by_name[name].source_sha256,
            source_byte_count=by_name[name].source_byte_count,
        )
        for name in occurrence_names
    )
    raw = canonical_json_bytes(
        {"entries": [vars(item) for item in old_entries]}
    )
    manifest = SimpleNamespace(
        entries=old_entries,
        manifest_id=_id("manifest"),
        canonical_bytes=raw,
    )
    upstream = SimpleNamespace(
        source_manifest=manifest,
        source_manifest_id=manifest.manifest_id,
    )
    lane = authority._freeze_occurrence_lane(  # noqa: SLF001
        upstream=upstream,
        repository=repository,
    )
    assert len(lane.entry_bindings) == 64
    changed = list(old_entries)
    changed[0] = SimpleNamespace(
        **{
            **vars(changed[0]),
            "source_sha256": _id("transplanted"),
        }
    )
    manifest.entries = tuple(changed)
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="exact local semantic-source subset",
    ):
        authority._freeze_occurrence_lane(  # noqa: SLF001
            upstream=upstream,
            repository=repository,
        )


def test_semantic_lane_keeps_shared_and_new_entries_separate() -> None:
    shared = tuple(_id(f"shared:{index}") for index in range(3))
    extra = tuple(_id(f"extra:{index}") for index in range(2))
    lane = authority.V075ConstructionSemanticCodeLaneV2(
        _id("repository"),
        _id("runtime"),
        authority.ROOT_MODULES,
        (*shared, *extra),
        shared,
        extra,
    )
    assert set(lane.entry_ids) == set(shared) | set(extra)
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="semantic replay code lane",
    ):
        authority.V075ConstructionSemanticCodeLaneV2(
            _id("repository"),
            _id("runtime"),
            authority.ROOT_MODULES,
            (*shared, *extra),
            shared,
            (shared[0], *extra),
        )


def test_dag_rejects_forward_dependency_and_preserves_two_lanes() -> None:
    first = authority.V075ConstructionSourceProvenanceDAGNodeV2(
        0, "RAW", _id("raw"), ()
    )
    second = authority.V075ConstructionSourceProvenanceDAGNodeV2(
        1, "OCCURRENCE_BUNDLE_SOURCE_LANE", _id("occurrence"), (first.node_id,)
    )
    third = authority.V075ConstructionSourceProvenanceDAGNodeV2(
        2, "SEMANTIC_REPLAY_CODE_LANE", _id("semantic"), (second.node_id,)
    )
    dag = authority.V075ConstructionSourceProvenanceDAGV2(
        (first, second, third)
    )
    assert dag.nodes[1].role == "OCCURRENCE_BUNDLE_SOURCE_LANE"
    assert dag.nodes[2].role == "SEMANTIC_REPLAY_CODE_LANE"
    forward = authority.V075ConstructionSourceProvenanceDAGNodeV2(
        0, "BAD", _id("bad"), (_id("future-node"),)
    )
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="cyclic or non-topological",
    ):
        authority.V075ConstructionSourceProvenanceDAGV2((forward,))


def test_private_inputs_are_not_fields_or_direct_hash_arguments() -> None:
    for cls in (
        authority.V075ConstructionGitSourceEntryV2,
        authority.V075ConstructionLocalRepositoryClosureV2,
        authority.V075ConstructionOccurrenceSourceLaneV2,
        authority.V075ConstructionSemanticCodeLaneV2,
        authority.V075ConstructionDependencyLockBindingV2,
        authority.V075ConstructionSourceArchiveBindingV2,
        authority.V075ConstructionSourceCodeProvenanceClosureV2,
    ):
        names = {item.name for item in fields(cls)}
        assert "private_generation_seed" not in names
        assert "private_salt" not in names
    tree = ast.parse(inspect.getsource(authority))
    for call in (
        item for item in ast.walk(tree) if isinstance(item, ast.Call)
    ):
        if (
            isinstance(call.func, ast.Attribute)
            and call.func.attr in {"sha256", "digest", "hexdigest"}
        ) or (
            isinstance(call.func, ast.Name) and call.func.id == "_hash"
        ):
            rendered = " ".join(
                ast.unparse(argument) for argument in call.args
            )
            assert "private_generation_seed" not in rendered
            assert "private_salt" not in rendered


def test_all_production_science_certificate_and_accounting_locks_closed() -> None:
    assert authority.CONSTRUCTION_SOURCE_ARCHIVE_REPLAY_COMPLETE is True
    assert authority.CONSTRUCTION_LOCAL_GIT_CODE_CLOSURE_COMPLETE is True
    assert (
        authority.CONSTRUCTION_ALL_TRACKED_ACFQP_SOURCE_CANDIDATES_COMPLETE
        is True
    )
    assert (
        authority.CONSTRUCTION_SEALED_SOURCE_COMPILE_MANIFEST_COMPLETE
        is True
    )
    assert authority.CONSTRUCTION_LOADED_SOURCE_MANIFEST_COMPLETE is False
    assert authority.CONSTRUCTION_TWO_LANE_PROVENANCE_DAG_COMPLETE is True
    for name in (
        "OFFICIAL_EXECUTION_ALLOWED",
        "PRODUCTION_AUTHORIZING",
        "SOURCE_AUTHORITY_COMPLETE",
        "CODE_PROVENANCE_COMPLETE",
        "FRESH_HELDOUT_ACCESS_ALLOWED",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
        "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
        "ACCOUNTING_GATE_PASSED",
        "TARGET_ACCESS_ALLOWED",
        "OBSERVER_OPEN_ALLOWED",
        "KERNEL_ACCESS_ALLOWED",
        "J0_ACCESS_ALLOWED",
        "PLANNER_WORKER_LAUNCH_ALLOWED",
        "OPERATIONAL_REGISTRIES_ALLOWED",
        "PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED",
    ):
        assert getattr(authority, name) is False
    for name in (
        "OFFICIAL_EXECUTION_ALLOWED",
        "PRODUCTION_AUTHORIZING",
        "SOURCE_AUTHORITY_COMPLETE",
        "CODE_PROVENANCE_COMPLETE",
        "FRESH_HELDOUT_ACCESS_ALLOWED",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
        "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
        "ACCOUNTING_GATE_PASSED",
        "TARGET_ACCESS_ALLOWED",
        "OBSERVER_OPEN_ALLOWED",
    ):
        assert getattr(independent, name) is False


def test_closure_pickle_and_production_gate_are_closed() -> None:
    assert "__reduce__" in (
        authority.V075ConstructionSourceCodeProvenanceClosureV2.__dict__
    )
    fake = object.__new__(
        authority.V075ConstructionSourceCodeProvenanceClosureV2
    )
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(fake)
    with pytest.raises(
        authority.V075ConstructionSourceCodeProvenanceV2InvariantViolation,
        match="duck types",
    ):
        (
            authority
            .assert_v075_construction_source_code_provenance_production_gate_v2(
                SimpleNamespace()
            )
        )
