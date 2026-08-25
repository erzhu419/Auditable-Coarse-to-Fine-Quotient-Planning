from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

import pytest

from scripts import materialize_v180r12r2_ten_terminal_aggregation_prelaunch as materializer


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MATERIALIZER = ROOT / materializer.MATERIALIZER_RELATIVE_PATH
SOURCE_LAUNCHER = ROOT / materializer.SOURCE_LAUNCHER_RELATIVE_PATH
SOURCE_BOOTSTRAP = ROOT / materializer.SOURCE_BOOTSTRAP_RELATIVE_PATH
PYTHON = "/usr/bin/python3"
GIT = "/usr/bin/git"
ISOLATED_FLAGS = (
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={materializer.PYCACHE_PREFIX}",
)


@pytest.fixture
def tmp_path() -> Path:
    """Use the native Linux filesystem so POSIX mode assertions are meaningful."""

    path = Path(tempfile.mkdtemp(prefix="v180r12r2-materializer-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _git(repository: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        [GIT, "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        env={
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        },
    )
    assert completed.stderr == b""
    return completed.stdout


def _commit(repository: Path, message: str, *, allow_empty: bool = False) -> str:
    arguments = [
        "-c",
        "user.name=V180r12r2 Test",
        "-c",
        "user.email=v180r12r2@example.invalid",
        "commit",
        "-q",
    ]
    if allow_empty:
        arguments.append("--allow-empty")
    arguments.extend(["-m", message])
    subprocess.run(
        [GIT, "-C", str(repository), *arguments],
        check=True,
        env={
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
        },
    )
    return _git(repository, "rev-parse", "HEAD").decode("ascii").strip()


def _write(repository: Path, relative: str, source: str | bytes) -> None:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(source, bytes):
        path.write_bytes(source)
    else:
        path.write_text(source, encoding="utf-8")


def _wrapper_source(value: str, count: int, *, suffix: str = "") -> str:
    names = materializer.WRAPPER_REDACTED_CONSTANT_NAMES
    lines = []
    for name in names:
        if name in materializer._WRAPPER_STRING_CONSTANT_NAMES:
            lines.append(f'{name} = "{value}"')
        else:
            lines.append(f"{name} = {count}")
    return "\n".join(lines) + "\n" + suffix


def _raw_git_fact(repository: Path, commit: str, relative: str) -> dict[str, object]:
    line = _git(repository, "ls-tree", commit, "--", relative).decode("utf-8").strip()
    prefix, observed = line.split("\t", 1)
    mode, kind, object_id = prefix.split(" ")
    assert observed == relative and kind == "blob"
    raw = _git(repository, "cat-file", "blob", object_id)
    return {
        "relative_path": relative,
        "git_mode": mode,
        "git_blob_id": object_id,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _source_fixture(repository: Path) -> None:
    _write(repository, materializer.MATERIALIZER_RELATIVE_PATH, SOURCE_MATERIALIZER.read_bytes())
    _write(repository, materializer.SOURCE_LAUNCHER_RELATIVE_PATH, SOURCE_LAUNCHER.read_bytes())
    _write(
        repository,
        materializer.SOURCE_BOOTSTRAP_RELATIVE_PATH,
        SOURCE_BOOTSTRAP.read_bytes(),
    )
    _write(repository, "src/acfqp/__init__.py", "")
    _write(repository, "src/acfqp/abstraction/__init__.py", "")
    _write(repository, "src/acfqp/leaf.py", "VALUE = 7\n")
    _write(
        repository,
        materializer.AUTHORIZATION_SELF_RELATIVE_PATH,
        "AUTHORIZATION_BOUND = True\n",
    )
    _write(
        repository,
        materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
        _wrapper_source("0" * 64, 0),
    )
    module_roots = sorted(
        {
            *materializer._CONTRACT_SOURCE_ROOTS,
            *materializer._PRODUCTION_SOURCE_ROOTS,
            *materializer._VERIFICATION_SOURCE_ROOTS,
        }
    )
    for relative in module_roots:
        if relative in materializer.TARGET_RUNNER_PATHS.values():
            _write(repository, relative, "from acfqp import leaf\n")
        elif relative != materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            _write(repository, relative, "from acfqp import leaf\n")


def _third_party_fixture(tmp_path: Path) -> dict[str, str]:
    packaging_root = (tmp_path / "packaging-root").absolute()
    tomli_root = (tmp_path / "tomli-root").absolute()
    _write(packaging_root, "packaging/__init__.py", "")
    _write(
        packaging_root,
        "packaging/utils.py",
        "def canonicalize_name(value):\n    return value.lower()\n",
    )
    _write(tomli_root, "tomli/__init__.py", "def loads(value):\n    return {}\n")
    return {"packaging": str(packaging_root), "tomli": str(tomli_root)}


def _external_document(
    repository: Path,
    c_pre: str,
    c_pre_tree: str,
    third_party_roots: dict[str, str],
) -> dict[str, object]:
    return {
        "schema": materializer.EXTERNAL_ROOT_SCHEMA,
        "materialization_rule_id": materializer.MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": materializer.SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository),
        "git_directory": str(repository / ".git"),
        "c_pre_commit_id": c_pre,
        "c_pre_tree_id": c_pre_tree,
        "bootstrap_git_blob": _raw_git_fact(
            repository, c_pre, materializer.SOURCE_BOOTSTRAP_RELATIVE_PATH
        ),
        "launcher_git_blob": _raw_git_fact(
            repository, c_pre, materializer.SOURCE_LAUNCHER_RELATIVE_PATH
        ),
        "materializer_git_blob": _raw_git_fact(
            repository, c_pre, materializer.MATERIALIZER_RELATIVE_PATH
        ),
        "third_party_source_roots": third_party_roots,
        "created_before_v180r12r2_authorized_production_execution": True,
        "v180r12r2_outcome_bytes_accessed": False,
    }


def _write_external_root(repository: Path, document: dict[str, object]) -> tuple[Path, str]:
    path = repository / materializer.EXTERNAL_ROOT_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o600)
    raw = _canonical(document)
    path.write_bytes(raw)
    path.chmod(0o400)
    return path, hashlib.sha256(raw).hexdigest()


def _build_repository(
    tmp_path: Path,
    *,
    wrapper_suffix: str = "",
    later_commit: bool = False,
) -> tuple[Path, Path, str, str, dict[str, object]]:
    repository = (tmp_path / "repository").absolute()
    repository.mkdir()
    subprocess.run([GIT, "-C", str(repository), "init", "-q"], check=True)
    _source_fixture(repository)
    subprocess.run([GIT, "-C", str(repository), "add", "."], check=True)
    c_pre = _commit(repository, "C_pre")
    c_pre_tree = _git(repository, "rev-parse", f"{c_pre}^{{tree}}").decode("ascii").strip()
    external = _external_document(
        repository,
        c_pre,
        c_pre_tree,
        _third_party_fixture(tmp_path),
    )
    _commit(repository, "empty same-tree bridge", allow_empty=True)
    _write(
        repository,
        materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
        _wrapper_source("1" * 64, 1, suffix=wrapper_suffix),
    )
    subprocess.run(
        [GIT, "-C", str(repository), "add", materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH],
        check=True,
    )
    _commit(repository, "freeze wrapper literals")
    if later_commit:
        _write(repository, "UNBOUND", "later\n")
        subprocess.run([GIT, "-C", str(repository), "add", "UNBOUND"], check=True)
        _commit(repository, "forbidden later commit")
    external_path, digest = _write_external_root(repository, external)
    return repository, external_path, digest, c_pre, external


def _invoke(repository: Path, external_path: Path, digest: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            PYTHON,
            *ISOLATED_FLAGS,
            str(repository / materializer.MATERIALIZER_RELATIVE_PATH),
            str(repository),
            str(external_path),
        ],
        cwd=repository,
        env={materializer.EXTERNAL_ROOT_SHA256_ENV: digest},
        check=False,
        capture_output=True,
        text=True,
    )


def test_public_schemas_paths_and_rule_identities_are_frozen() -> None:
    assert materializer.EXTERNAL_ROOT_RELATIVE_PATH == (
        ".tmp/exact-freeze/"
        "v180r12r2_ten_terminal_aggregation_prelaunch_external_root.json"
    )
    assert materializer.OUTPUT_ROOT_RELATIVE_PATH == (
        ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_prelaunch"
    )
    assert materializer.BOOTSTRAP_RELATIVE_PATH.endswith("/bootstrap.py")
    assert materializer.RETAINED_LAUNCHER_RELATIVE_PATH.endswith("/launcher.py")
    assert materializer.LAUNCH_MANIFEST_RELATIVE_PATH.endswith("/launch_manifest.json")
    assert materializer.MATERIALIZATION_TERMINAL_RELATIVE_PATH.endswith(
        "/MATERIALIZATION_TERMINAL.json"
    )
    assert materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH == (
        ".tmp/exact-freeze/"
        "v180r12r2_ten_terminal_aggregation_prelaunch_failure.json"
    )
    assert materializer.SOURCE_CLOSURE_RULE_ID == hashlib.sha256(
        _canonical(materializer.SOURCE_CLOSURE_RULE_DOCUMENT)
    ).hexdigest()
    assert materializer.MATERIALIZATION_RULE_ID == hashlib.sha256(
        _canonical(materializer.MATERIALIZATION_RULE_DOCUMENT)
    ).hexdigest()
    assert materializer.SOURCE_CLOSURE_RULE_ID == (
        "fe5036863176827c036ab5aef487b8e920896455dc684e44ae7791438dbb408c"
    )
    assert materializer.MATERIALIZATION_RULE_ID == (
        "79513bd291443fa661c05bc1ff91b6c8f3b8f51dda9aac01073ffec5376abf3d"
    )


def test_success_materializes_exact_bootstrap_manifest_and_terminal_last(
    tmp_path: Path,
) -> None:
    repository, external_path, digest, c_pre, external = _build_repository(tmp_path)
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode == 0, completed.stderr
    output = repository / materializer.OUTPUT_ROOT_RELATIVE_PATH
    bootstrap = repository / materializer.BOOTSTRAP_RELATIVE_PATH
    launcher = repository / materializer.RETAINED_LAUNCHER_RELATIVE_PATH
    manifest_path = repository / materializer.LAUNCH_MANIFEST_RELATIVE_PATH
    terminal_path = repository / materializer.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    failure = repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o400
        for path in (bootstrap, launcher, manifest_path, terminal_path)
    )
    assert not failure.exists()
    assert bootstrap.read_bytes() == _git(
        repository,
        "cat-file",
        "blob",
        external["bootstrap_git_blob"]["git_blob_id"],
    )
    assert launcher.read_bytes() == _git(
        repository,
        "cat-file",
        "blob",
        external["launcher_git_blob"]["git_blob_id"],
    )

    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    assert _canonical(manifest) == manifest_raw
    assert manifest["schema"] == materializer.LAUNCH_MANIFEST_SCHEMA
    assert manifest["c_pre_commit_id"] == c_pre
    assert manifest["c_pre_root"] == str(output)
    assert manifest["manifest_relative_path"] == "launch_manifest.json"
    assert manifest["bootstrap"]["relative_path"] == "bootstrap.py"
    assert manifest["git"]["runner_process_count"] == 6
    assert manifest["git"]["runner_environment_template"][
        materializer.MANIFEST_SHA256_ENV
    ] == materializer.MANIFEST_SHA256_TEMPLATE
    wrapper_source = next(
        row
        for row in manifest["source_modules"]
        if row["module"] == materializer.AUTHORIZATION_EVIDENCE_MODULE
    )
    current_wrapper = (
        repository / materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH
    ).read_bytes()
    assert wrapper_source == {
        "module": materializer.AUTHORIZATION_EVIDENCE_MODULE,
        "is_package": False,
        **materializer._raw_fact(
            materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
            current_wrapper,
        ),
    }
    normalized = next(
        row
        for row in manifest["authorization_source_closure"]["facts"]
        if row["relative_path"] == materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH
    )
    assert normalized["binding_kind"] == materializer.NORMALIZED_WRAPPER_BINDING_KIND
    assert normalized["redacted_constant_names"] == list(
        materializer.WRAPPER_REDACTED_CONSTANT_NAMES
    )
    assert normalized["sha256"] != wrapper_source["sha256"]

    bootstrap_spec = importlib.util.spec_from_file_location(
        "synthetic_retained_bootstrap", bootstrap
    )
    assert bootstrap_spec is not None and bootstrap_spec.loader is not None
    bootstrap_module = importlib.util.module_from_spec(bootstrap_spec)
    bootstrap_spec.loader.exec_module(bootstrap_module)
    validated_manifest = bootstrap_module._validated_manifest(
        manifest, repository, output, "launch_manifest.json"
    )
    third_party_facts, wrapper_fact = (
        bootstrap_module._validate_manifest_resource_contract(validated_manifest)
    )
    bound_records = bootstrap_module._compile_bound_sources(
        validated_manifest, repository, wrapper_fact
    )
    third_party_records = bootstrap_module._compile_third_party_sources(
        third_party_facts
    )
    assert materializer.AUTHORIZATION_SELF_MODULE in bound_records
    assert materializer.AUTHORIZATION_EVIDENCE_MODULE in bound_records
    assert {"packaging", "tomli"} <= set(third_party_records)

    terminal_raw = terminal_path.read_bytes()
    terminal = json.loads(terminal_raw)
    assert _canonical(terminal) == terminal_raw
    assert terminal["schema"] == materializer.MATERIALIZATION_TERMINAL_SCHEMA
    assert terminal["launch_manifest"] == materializer._raw_fact(
        materializer.LAUNCH_MANIFEST_RELATIVE_PATH, manifest_raw
    )
    assert (
        terminal["external_root_created_before_authorized_production_execution"]
        is True
    )
    assert terminal["external_root_required_before_authorization_issuance"] is False
    assert terminal["materialization_terminal_written_last"] is True
    assert terminal["campaign_actual_measurement"] is False
    assert terminal["scientific_occurrence_executed"] is False
    assert terminal["v180r12r2_outcome_bytes_accessed"] is False
    stdout = json.loads(completed.stdout)
    assert stdout["materialization_terminal_id"] == terminal[
        "materialization_terminal_id"
    ]


def test_exact_completed_materialization_cannot_be_rerun(tmp_path: Path) -> None:
    repository, external_path, digest, _, _ = _build_repository(tmp_path)
    first = _invoke(repository, external_path, digest)
    assert first.returncode == 0, first.stderr
    terminal = (
        repository / materializer.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    ).read_bytes()
    second = _invoke(repository, external_path, digest)
    assert second.returncode != 0
    assert "terminal already exists; rerun forbidden" in second.stderr
    assert (
        repository / materializer.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    ).read_bytes() == terminal
    assert not (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).exists()


def test_wrong_external_digest_freezes_typed_failure_without_output(
    tmp_path: Path,
) -> None:
    repository, external_path, _, _, _ = _build_repository(tmp_path)
    completed = _invoke(repository, external_path, "0" * 64)
    assert completed.returncode != 0
    assert not (repository / materializer.OUTPUT_ROOT_RELATIVE_PATH).exists()
    failure_path = repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH
    failure_raw = failure_path.read_bytes()
    failure = json.loads(failure_raw)
    assert _canonical(failure) == failure_raw
    assert failure["schema"] == materializer.MATERIALIZATION_FAILURE_SCHEMA
    assert failure["failed_phase"] == "EXTERNAL_ROOT_VALIDATION"
    assert failure["same_materialization_identity_rerun_forbidden"] is True
    assert failure["campaign_actual_measurement"] is False
    assert stat.S_IMODE(failure_path.stat().st_mode) == 0o400
    again = _invoke(repository, external_path, "0" * 64)
    assert again.returncode != 0
    assert "failure already exists; rerun forbidden" in again.stderr
    assert failure_path.read_bytes() == failure_raw


def test_external_root_c_pre_is_not_substituted_from_head(tmp_path: Path) -> None:
    repository, external_path, _, _, external = _build_repository(tmp_path)
    head = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    head_tree = _git(repository, "rev-parse", "HEAD^{tree}").decode("ascii").strip()
    external["c_pre_commit_id"] = head
    external["c_pre_tree_id"] = head_tree
    external["bootstrap_git_blob"] = _raw_git_fact(
        repository, head, materializer.SOURCE_BOOTSTRAP_RELATIVE_PATH
    )
    external["materializer_git_blob"] = _raw_git_fact(
        repository, head, materializer.MATERIALIZER_RELATIVE_PATH
    )
    external["launcher_git_blob"] = _raw_git_fact(
        repository, head, materializer.SOURCE_LAUNCHER_RELATIVE_PATH
    )
    external_path, digest = _write_external_root(repository, external)
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "exactly C_pre -> bridge -> literal HEAD" in completed.stderr
    failure = json.loads(
        (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["failed_phase"] == "GIT_TOPOLOGY_VALIDATION"


def test_later_commit_after_literal_head_is_rejected(tmp_path: Path) -> None:
    repository, external_path, digest, _, _ = _build_repository(
        tmp_path, later_commit=True
    )
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "exactly C_pre -> bridge -> literal HEAD" in completed.stderr
    assert not (repository / materializer.OUTPUT_ROOT_RELATIVE_PATH).exists()


def test_wrapper_change_outside_eight_literals_is_rejected(tmp_path: Path) -> None:
    repository, external_path, digest, _, _ = _build_repository(
        tmp_path, wrapper_suffix="EXTRA_WRAPPER_LOGIC = True\n"
    )
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "outside the eight literals" in completed.stderr
    failure = json.loads(
        (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["failed_phase"] == "C_PRE_SOURCE_CLOSURE"


def test_symlinked_external_root_is_rejected_and_preserved(tmp_path: Path) -> None:
    repository, external_path, digest, _, external = _build_repository(tmp_path)
    external_path.chmod(0o600)
    external_path.unlink()
    target = tmp_path / "external-target.json"
    target.write_bytes(_canonical(external))
    target.chmod(0o400)
    external_path.symlink_to(target)
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "unavailable or symlinked" in completed.stderr
    assert external_path.is_symlink()
    assert (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).exists()


def test_preexisting_partial_output_is_frozen_without_mutation(tmp_path: Path) -> None:
    repository, external_path, digest, _, _ = _build_repository(tmp_path)
    output = repository / materializer.OUTPUT_ROOT_RELATIVE_PATH
    output.mkdir(mode=0o700)
    partial = output / "bootstrap.py"
    partial.write_bytes(b"partial")
    partial.chmod(0o400)
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "partial output exists; rerun forbidden" in completed.stderr
    assert partial.read_bytes() == b"partial"
    failure = json.loads(
        (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["failed_phase"] == "PREEXISTING_PROGRESS_CHECK"
    assert failure["partial_artifact_observations"]["bootstrap"]["sha256"] == hashlib.sha256(
        b"partial"
    ).hexdigest()


def test_materializer_is_stdlib_only_and_never_executes_campaign_code() -> None:
    source = SOURCE_MATERIALIZER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.add((node.module or "").split(".", 1)[0])
    assert imported == {
        "ast",
        "hashlib",
        "io",
        "json",
        "os",
        "pathlib",
        "re",
        "stat",
        "subprocess",
        "sys",
        "sysconfig",
        "tarfile",
        "tokenize",
        "typing",
    }
    assert "from acfqp" not in source
    assert "CounterRecord" not in source
    assert "WorkVector" not in source
    assert "ComparisonVector" not in source
    assert "os.O_EXCL" in source
    assert "os.O_NOFOLLOW" in source
    assert "os.O_CLOEXEC" in source
    assert "os.fsync" in source
    assert not (ROOT / materializer.OUTPUT_ROOT_RELATIVE_PATH).exists()
    assert not (ROOT / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).exists()
