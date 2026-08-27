from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

import pytest

from acfqp import (
    construction_k7_standard_2048_fresh_terminal_failure_retention_v42r1 as retention,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = (
    ROOT / "scripts/materialize_v42_standard_2048_fresh_terminal_failure_retention.py"
)
VERIFIER = ROOT / "scripts/verify_v42_standard_2048_fresh_terminal_failure_retention.py"
INDEPENDENT_SOURCE = (
    ROOT
    / "src/acfqp/"
    "construction_k7_standard_2048_fresh_terminal_failure_retention_"
    "independent_verifier_v42r1.py"
)
EXPECTED_MANIFEST_ID = (
    "5ab73d90b63675fe4255c0bf6cd2116444a52b5b0009cd6cf822f4fbf7b6ce66"
)
EXPECTED_VERIFICATION_ID = (
    "6c088a5515a096ce363c7ab9a834d9ed9c22da87a63d4ed59d1d68e78167db3b"
)


def _invoke_materializer(target: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        (
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(MATERIALIZER),
            "--repository-root",
            str(ROOT),
            "--retention-root",
            str(target),
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )


def _invoke_verifier(
    target: Path, *, publish: bool = False
) -> subprocess.CompletedProcess[bytes]:
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(VERIFIER),
        "--repository-root",
        str(ROOT),
        "--retention-root",
        str(target),
    ]
    if publish:
        command.append("--publish")
    return subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )


def _load(path: Path) -> dict[str, object]:
    value = loads_canonical_json(path.read_bytes())
    assert type(value) is dict
    return value


def _replace_canonical(path: Path, value: dict[str, object]) -> None:
    original_mode = stat.S_IMODE(path.lstat().st_mode)
    path.chmod(0o600)
    path.write_bytes(canonical_json_bytes(value))
    path.chmod(original_mode)


def _original_fixed_inputs_available() -> bool:
    return all(
        (ROOT / spec["original_relative_path"]).is_file()
        for spec in retention.ARTIFACT_SPECS
    ) and all(
        Path(spec["original_absolute_path"]).is_file()
        for spec in retention.INVOCATION_CAPTURE_SPECS
    )


@pytest.fixture(scope="module")
def retained_bundle() -> Path:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r1-failure-retention-", dir="/tmp"
    ) as parent_name:
        target = Path(parent_name) / "bundle"
        if _original_fixed_inputs_available():
            materialized = _invoke_materializer(target)
            assert materialized.returncode == 0, materialized.stderr.decode()
            manifest = json.loads(materialized.stdout)
            assert manifest["retention_manifest_id"] == EXPECTED_MANIFEST_ID
            verified = _invoke_verifier(target, publish=True)
        else:
            committed = (
                ROOT
                / "retained_evidence/"
                "v42_standard_2048_fresh_terminal_ordinal1_failure"
            )
            assert committed.is_dir()
            shutil.copytree(committed, target)
            manifest = _load(target / "RETENTION_MANIFEST.json")
            assert manifest["retention_manifest_id"] == EXPECTED_MANIFEST_ID
            verified = _invoke_verifier(target)
        assert verified.returncode == 0, verified.stderr.decode()
        verification = json.loads(verified.stdout)
        assert verification["independent_verification_id"] == EXPECTED_VERIFICATION_ID
        yield target


@pytest.fixture
def linux_tmp_path() -> Path:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42r1-test-", dir="/tmp") as name:
        yield Path(name)


def test_original_failure_is_frozen_without_oom_reclassification() -> None:
    if _original_fixed_inputs_available():
        manifest, raw_by_role = retention.audit_original_v42_ordinal1_failure(ROOT)
    else:
        retained = (
            ROOT
            / "retained_evidence/"
            "v42_standard_2048_fresh_terminal_ordinal1_failure"
        )
        manifest = _load(retained / "RETENTION_MANIFEST.json")
        raw_by_role = {
            "EVIDENCE_ROOT_FAILURE": (
                retained / "artifacts/06_FAILURE_EVIDENCE_ROOT.json"
            ).read_bytes(),
            "FIXED_PARENT_FAILURE": (
                retained / "artifacts/07_FAILURE_FIXED_PARENT.json"
            ).read_bytes(),
            "PREPARE_RECEIPT": (
                retained / "artifacts/01_PREPARE_RECEIPT.json"
            ).read_bytes(),
            "PREPARE_INVOCATION_STDOUT": (
                retained / "invocation_captures/00_PREPARE_STDOUT.bin"
            ).read_bytes(),
        }
    assert manifest["retention_manifest_id"] == EXPECTED_MANIFEST_ID
    assert manifest["formal_worker_failure_classification"] == "PRODUCER_EXCEPTION"
    assert manifest["operator_observation_is_not_formal_oom_proof"] is True
    observation = manifest["operator_observation"]
    assert observation["retention_document_constructed_after_formal_failure"] is True
    assert observation["resource_observations_and_signal_preceded_failure_publication"] is True
    assert observation["formal_oom_event_receipt_present"] is False
    assert observation["formal_cgroup_oom_proof_present"] is False
    assert observation["formal_kernel_oom_kill_proof_present"] is False
    assert observation["outer_runner_natural_exit_code_observed"] == 1
    assert raw_by_role["EVIDENCE_ROOT_FAILURE"] == raw_by_role["FIXED_PARENT_FAILURE"]
    assert raw_by_role["PREPARE_INVOCATION_STDOUT"] == (
        raw_by_role["PREPARE_RECEIPT"] + b"\n"
    )


def test_materialized_retention_and_fresh_verification_are_exact(
    retained_bundle: Path,
) -> None:
    manifest = _load(retained_bundle / "RETENTION_MANIFEST.json")
    verification = _load(retained_bundle / "INDEPENDENT_VERIFICATION.json")
    assert manifest["formal_artifact_count"] == 8
    assert manifest["non_formal_invocation_capture_count"] == 4
    assert manifest["retained_file_count_excluding_manifest_and_verification"] == 12
    assert manifest["retention_mode_profiles"] == {
        "MATERIALIZED_PRIVATE_MODE_POLICY": {
            "directory_mode_octal": "0700",
            "file_mode_octal": "0400",
        },
        "GIT_RETAINED_REGULAR_MODE": {
            "directory_mode_octal": "0755",
            "file_mode_octal": "0644",
        },
    }
    assert manifest["retained_bundle_fresh_clone_self_sufficient"] is True
    assert manifest["live_original_paths_required_for_independent_reverification"] is False
    assert manifest["invocation_captures_are_not_fixed_formal_evidence"] is True
    assert manifest["invocation_captures_are_not_formal_worker_streams"] is True
    assert manifest["formal_campaign_artifact_present"] is False
    assert manifest["formal_verification_artifact_present"] is False
    assert manifest["formal_terminal_artifact_present"] is False
    assert (
        manifest["formal_worker_stdout_or_stderr_capture_bytes_retained_separately"]
        is False
    )
    assert manifest["same_identity_rerun_forbidden"] is True
    assert manifest["ordinal2_authority_constructed"] is False
    assert manifest["ordinal2_execution_performed"] is False
    assert manifest["scientific_success"] is False
    assert manifest["scientific_claim_issued"] is False
    assert verification["retention_manifest_id"] == EXPECTED_MANIFEST_ID
    assert verification["producer_or_v42_formal_module_imported"] is False
    assert verification["fresh_python_isolated_flag"] is True
    assert verification["fresh_python_no_site_flag"] is True
    assert verification["fresh_python_no_bytecode_flag"] is True
    root_mode = stat.S_IMODE(retained_bundle.lstat().st_mode)
    assert root_mode in {0o700, 0o755}
    file_mode = 0o400 if root_mode == 0o700 else 0o644
    for path in retained_bundle.rglob("*"):
        expected = root_mode if path.is_dir() else file_mode
        assert stat.S_IMODE(path.lstat().st_mode) == expected


def test_real_git_archive_and_clean_clone_use_portable_retained_modes(
    retained_bundle: Path, linux_tmp_path: Path
) -> None:
    staging = linux_tmp_path / "staging"
    clean = linux_tmp_path / "clean"
    subprocess.run(
        ("git", "clone", "--shared", "--quiet", str(ROOT), str(staging)),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    successor_paths = (
        "src/acfqp/construction_k7_standard_2048_fresh_terminal_failure_retention_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_fresh_terminal_failure_retention_independent_verifier_v42r1.py",
        "scripts/materialize_v42_standard_2048_fresh_terminal_failure_retention.py",
        "scripts/verify_v42_standard_2048_fresh_terminal_failure_retention.py",
        "tests/test_construction_k7_standard_2048_fresh_terminal_failure_retention_v42r1.py",
    )
    for relative in successor_paths:
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    retained_relative = (
        "retained_evidence/v42_standard_2048_fresh_terminal_ordinal1_failure"
    )
    staging_retention = staging / retained_relative
    if staging_retention.exists():
        assert _load(staging_retention / "RETENTION_MANIFEST.json")[
            "retention_manifest_id"
        ] == EXPECTED_MANIFEST_ID
    else:
        shutil.copytree(retained_bundle, staging_retention)
    subprocess.run(
        ("git", "add", "--", *successor_paths, retained_relative),
        cwd=staging,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    commit_environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "V42r1 portability fixture",
        "GIT_AUTHOR_EMAIL": "v42r1-fixture.invalid@example.invalid",
        "GIT_COMMITTER_NAME": "V42r1 portability fixture",
        "GIT_COMMITTER_EMAIL": "v42r1-fixture.invalid@example.invalid",
    }
    staged = subprocess.run(
        ("git", "diff", "--cached", "--quiet"),
        cwd=staging,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert staged.returncode in {0, 1}, staged.stderr.decode()
    if staged.returncode == 1:
        subprocess.run(
            (
                "git",
                "-c",
                "commit.gpgSign=false",
                "commit",
                "--quiet",
                "-m",
                "temporary V42r1 portability fixture",
            ),
            cwd=staging,
            env=commit_environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

    archive_path = linux_tmp_path / "retention.tar"
    subprocess.run(
        (
            "git",
            "-c",
            "tar.umask=0022",
            "archive",
            "--format=tar",
            "-o",
            str(archive_path),
            "HEAD",
            "--",
            retained_relative,
        ),
        cwd=staging,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    with tarfile.open(archive_path, mode="r:") as archive:
        retained_members = [
            member
            for member in archive.getmembers()
            if member.name.startswith(retained_relative)
        ]
    assert retained_members
    assert all(
        member.mode == (0o755 if member.isdir() else 0o644)
        for member in retained_members
    )

    previous_umask = os.umask(0o022)
    try:
        subprocess.run(
            ("git", "clone", "--shared", "--quiet", str(staging), str(clean)),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
    finally:
        os.umask(previous_umask)
    clean_retention = clean / retained_relative
    assert stat.S_IMODE(clean_retention.lstat().st_mode) == 0o755
    assert all(
        stat.S_IMODE(path.lstat().st_mode) == (0o755 if path.is_dir() else 0o644)
        for path in clean_retention.rglob("*")
    )
    verified = subprocess.run(
        (
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(
                clean
                / "scripts/verify_v42_standard_2048_fresh_terminal_failure_retention.py"
            ),
            "--repository-root",
            str(clean),
            "--retention-root",
            str(clean_retention),
        ),
        cwd=clean,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert verified.returncode == 0, verified.stderr.decode()
    assert json.loads(verified.stdout)["independent_verification_id"] == (
        EXPECTED_VERIFICATION_ID
    )


def test_independent_verifier_source_is_producer_free() -> None:
    tree = ast.parse(INDEPENDENT_SOURCE.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)
    forbidden = {
        "acfqp.construction_k7_standard_2048_execution_authority_v42",
        "acfqp.construction_k7_standard_2048_fresh_terminal_campaign_v42",
        "acfqp.construction_k7_standard_2048_fresh_terminal_independent_verifier_v42",
        "acfqp.construction_k7_standard_2048_fresh_terminal_failure_retention_v42r1",
        "scripts.run_v42_standard_2048_fresh_terminal_campaign",
        "scripts.supervise_v42_standard_2048_fresh_terminal_campaign",
    }
    assert imports.isdisjoint(forbidden)


def test_same_retention_root_cannot_be_materialized_twice(
    retained_bundle: Path,
) -> None:
    before = (retained_bundle / "RETENTION_MANIFEST.json").read_bytes()
    repeated = _invoke_materializer(retained_bundle)
    assert repeated.returncode != 0
    assert (retained_bundle / "RETENTION_MANIFEST.json").read_bytes() == before


def test_rehashed_manifest_cannot_promote_operator_observation_to_oom(
    retained_bundle: Path, linux_tmp_path: Path
) -> None:
    target = linux_tmp_path / "reclassified"
    shutil.copytree(retained_bundle, target)
    path = target / "RETENTION_MANIFEST.json"
    manifest = _load(path)
    manifest["operator_observation"]["formal_oom_event_receipt_present"] = True
    manifest["formal_classification_rewritten_as_oom"] = True
    payload = dict(manifest)
    payload.pop("retention_manifest_id")
    manifest["retention_manifest_id"] = hashlib.sha256(
        retention.RETENTION_DOMAIN.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    _replace_canonical(path, manifest)
    rejected = _invoke_verifier(target)
    assert rejected.returncode != 0
    assert b"manifest changed or self-rebound" in rejected.stderr


def test_different_failure_copies_are_rejected(
    retained_bundle: Path, linux_tmp_path: Path
) -> None:
    target = linux_tmp_path / "different-failures"
    shutil.copytree(retained_bundle, target)
    path = target / "artifacts/07_FAILURE_FIXED_PARENT.json"
    original_mode = stat.S_IMODE(path.lstat().st_mode)
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + b"\n")
    path.chmod(original_mode)
    rejected = _invoke_verifier(target)
    assert rejected.returncode != 0
    assert b"FIXED_PARENT_FAILURE" in rejected.stderr


def test_partial_or_extra_retention_is_rejected(
    retained_bundle: Path, linux_tmp_path: Path
) -> None:
    partial = linux_tmp_path / "partial"
    shutil.copytree(retained_bundle, partial)
    (partial / "artifacts/04_WORKER_START.json").unlink()
    rejected_partial = _invoke_verifier(partial)
    assert rejected_partial.returncode != 0
    assert b"artifact inventory changed" in rejected_partial.stderr

    extra = linux_tmp_path / "extra"
    shutil.copytree(retained_bundle, extra)
    extra_path = extra / "artifacts/CAMPAIGN.json"
    extra_path.write_bytes(b"{}")
    extra_path.chmod(
        0o400 if stat.S_IMODE(extra.lstat().st_mode) == 0o700 else 0o644
    )
    rejected_extra = _invoke_verifier(extra)
    assert rejected_extra.returncode != 0
    assert b"artifact inventory changed" in rejected_extra.stderr


def test_non_formal_invocation_capture_tamper_is_rejected(
    retained_bundle: Path, linux_tmp_path: Path
) -> None:
    target = linux_tmp_path / "capture-tamper"
    shutil.copytree(retained_bundle, target)
    path = target / "invocation_captures/03_LAUNCH_STDERR.bin"
    original_mode = stat.S_IMODE(path.lstat().st_mode)
    path.chmod(0o600)
    raw = path.read_bytes()
    path.write_bytes(b"X" + raw[1:])
    path.chmod(original_mode)
    rejected = _invoke_verifier(target)
    assert rejected.returncode != 0
    assert b"invocation capture changed" in rejected.stderr
