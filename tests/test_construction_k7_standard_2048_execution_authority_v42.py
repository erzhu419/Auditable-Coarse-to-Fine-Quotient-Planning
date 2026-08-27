from copy import deepcopy
import importlib
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp import construction_k7_standard_2048_execution_authority_v42 as authority


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


@pytest.fixture()
def transitive_source_repo(tmp_path: Path) -> tuple[Path, str, tuple[str, ...]]:
    root = tmp_path / "source-repo"
    package = root / "src" / "acfqp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("\n", encoding="utf-8")
    (package / "fixture_root.py").write_text(
        "from acfqp import fixture_dependency\n"
        "from acfqp.fixture_package import child\n"
        "VALUE = fixture_dependency.VALUE + child.VALUE\n",
        encoding="utf-8",
    )
    (package / "fixture_dependency.py").write_text("VALUE = 7\n", encoding="utf-8")
    fixture_package = package / "fixture_package"
    fixture_package.mkdir()
    (fixture_package / "__init__.py").write_text("\n", encoding="utf-8")
    (fixture_package / "child.py").write_text("VALUE = 11\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "v42-fixture@example.invalid")
    _git(root, "config", "user.name", "V42 Fixture")
    _git(root, "add", "src")
    _git(root, "commit", "-q", "-m", "fixture source closure")
    return root, _git(root, "rev-parse", "HEAD"), (
        "src/acfqp/fixture_root.py",
    )


def test_v42_source_manifest_rebuilds_transitive_commit_blobs_and_rejects_dirty_dependency(
    transitive_source_repo: tuple[Path, str, tuple[str, ...]],
) -> None:
    root, commit, roots = transitive_source_repo
    manifest = authority.build_source_manifest_from_commit_v42(
        root, source_commit=commit, source_roots=roots
    )
    paths = {row["relative_path"] for row in manifest["source_facts"]}
    assert paths == {
        "src/acfqp/__init__.py",
        "src/acfqp/fixture_root.py",
        "src/acfqp/fixture_dependency.py",
        "src/acfqp/fixture_package/__init__.py",
        "src/acfqp/fixture_package/child.py",
    }
    assert manifest["source_closure_scope"] == authority.SOURCE_CLOSURE_SCOPE
    assert manifest["stdlib_and_interpreter_sources_excluded"] is True
    assert manifest["external_python_distributions_excluded"] is True
    assert manifest["non_python_resources_excluded"] is True
    assert {row["git_mode"] for row in manifest["source_facts"]} == {"100644"}
    assert {row["git_object_type"] for row in manifest["source_facts"]} == {"blob"}
    authority.verify_source_manifest_document_v42(
        manifest,
        root=root,
        recompute_from_commit=True,
        source_roots=roots,
        enforce_frozen_semantic_sources=False,
    )
    (root / "src/acfqp/fixture_dependency.py").write_text(
        "VALUE = 8\n", encoding="utf-8"
    )
    with pytest.raises(
        authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
        match="transitive source closure",
    ):
        authority.verify_live_source_matches_manifest_v42(
            root,
            manifest,
            source_roots=roots,
            enforce_frozen_semantic_sources=False,
        )


def test_v42_source_manifest_extra_field_and_resigned_tamper_fail_closed(
    transitive_source_repo: tuple[Path, str, tuple[str, ...]],
) -> None:
    root, commit, roots = transitive_source_repo
    manifest = authority.build_source_manifest_from_commit_v42(
        root, source_commit=commit, source_roots=roots
    )
    extra = {**manifest, "unregistered_extra_claim": True}
    with pytest.raises(
        authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
        match="schema is not exact",
    ):
        authority.verify_source_manifest_document_v42(
            extra,
            source_roots=roots,
            enforce_frozen_semantic_sources=False,
        )

    tampered = deepcopy(manifest)
    tampered["source_facts"][0]["sha256"] = "0" * 64
    payload = {key: value for key, value in tampered.items() if key != "source_manifest_id"}
    tampered["source_manifest_id"] = domains.extension_content_id_v42(
        domains.CONSTRUCTION_K7_SOURCE_MANIFEST_V42_DOMAIN, payload
    )
    with pytest.raises(
        authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
        match="commit-tree replay",
    ):
        authority.verify_source_manifest_document_v42(
            tampered,
            root=root,
            recompute_from_commit=True,
            source_roots=roots,
            enforce_frozen_semantic_sources=False,
        )


def test_v42_source_binding_rejects_resigned_extra_field_instead_of_self_proving() -> None:
    receipt = {
        "prepare_receipt_id": "1" * 64,
        "source_commit": "2" * 40,
        "source_tree": "3" * 40,
        "source_manifest_id": "4" * 64,
    }
    attempt = {"runner_attempt_id": "5" * 64}
    worker_start = {"worker_start_id": "c" * 64}
    consumption = {"authority_consumption_id": "d" * 64}
    expected = authority.build_campaign_source_binding_v42(
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_start=worker_start,
        authority_consumption=consumption,
        fresh_terminal_preregistration_id="6" * 64,
        target_kernel_id="7" * 64,
        adaptive_expression_overlay_id="8" * 64,
        adaptive_expression_proof_id="9" * 64,
        adaptive_expression_model_id="a" * 64,
        planner_id="b" * 64,
    )
    forged_payload = {
        key: value for key, value in expected.items() if key != "source_binding_id"
    }
    forged_payload["unregistered_extra_claim"] = "FORGED"
    forged = {
        **forged_payload,
        "source_binding_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_SOURCE_BINDING_V42_DOMAIN, forged_payload
        ),
    }
    with pytest.raises(
        authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
        match="schema is not exact",
    ):
        authority.verify_campaign_source_binding_v42(forged, expected=expected)


def test_v42_source_manifest_rejects_symlink_and_executable_git_modes(
    transitive_source_repo: tuple[Path, str, tuple[str, ...]],
) -> None:
    root, _, roots = transitive_source_repo
    dependency = root / "src/acfqp/fixture_dependency.py"
    dependency.unlink()
    dependency.symlink_to("fixture_root.py")
    _git(root, "add", "src/acfqp/fixture_dependency.py")
    _git(root, "commit", "-q", "-m", "symlink attack")
    with pytest.raises(
        authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
        match="allowed regular Python blob",
    ):
        authority.build_source_manifest_from_commit_v42(
            root, source_commit=_git(root, "rev-parse", "HEAD"), source_roots=roots
        )

    dependency.unlink()
    dependency.write_text("VALUE = 7\n", encoding="utf-8")
    _git(root, "add", "src/acfqp/fixture_dependency.py")
    _git(root, "update-index", "--chmod=+x", "src/acfqp/fixture_dependency.py")
    _git(root, "commit", "-q", "-m", "executable attack")
    with pytest.raises(
        authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
        match="allowed regular Python blob",
    ):
        authority.build_source_manifest_from_commit_v42(
            root, source_commit=_git(root, "rev-parse", "HEAD"), source_roots=roots
        )


def test_v42_live_source_reader_uses_nofollow_and_runtime_gate_rejects_extra_module(
    transitive_source_repo: tuple[Path, str, tuple[str, ...]],
) -> None:
    root, commit, roots = transitive_source_repo
    manifest = authority.build_source_manifest_from_commit_v42(
        root, source_commit=commit, source_roots=roots
    )
    dependency = root / "src/acfqp/fixture_dependency.py"
    target = root / "same-bytes.py"
    target.write_bytes(dependency.read_bytes())
    dependency.unlink()
    dependency.symlink_to(target)
    with pytest.raises(
        authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
        match="not a regular file",
    ):
        authority._read_regular_nofollow_stable(dependency)  # noqa: SLF001

    extra_module = ModuleType("acfqp.v42_unmanifested_fixture")
    extra_module.__file__ = str(root / "src/acfqp/unmanifested_fixture.py")
    Path(extra_module.__file__).write_text("VALUE = 1\n", encoding="utf-8")
    sys.modules[extra_module.__name__] = extra_module
    try:
        with pytest.raises(
            authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
            match="unmanifested repository module",
        ):
            authority.verify_runtime_repository_modules_in_manifest_v42(
                root,
                manifest,
                source_roots=roots,
                enforce_frozen_semantic_sources=False,
            )
    finally:
        sys.modules.pop(extra_module.__name__, None)
    guard = authority.install_runtime_repository_import_guard_v42(
        root,
        manifest,
        source_roots=roots,
        enforce_frozen_semantic_sources=False,
    )
    try:
        with pytest.raises(
            authority.ConstructionK7Standard2048ExecutionAuthorityV42Error,
            match="import guard rejected",
        ):
            importlib.import_module("acfqp.unmanifested_fixture")
    finally:
        sys.meta_path.remove(guard)
