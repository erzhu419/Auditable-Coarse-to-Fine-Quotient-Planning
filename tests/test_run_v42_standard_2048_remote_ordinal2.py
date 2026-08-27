from __future__ import annotations

import ast
import copy
import hashlib
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace

import pytest

from acfqp import construction_k7_standard_2048_remote_execution_authority_v42r1 as authority
from acfqp import construction_k7_standard_2048_fresh_terminal_preregistration_v42 as pre
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import run_v42_standard_2048_remote_ordinal2 as runner
from scripts import supervise_v42_standard_2048_remote_ordinal2 as supervisor


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - Git object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def _host(stage: str) -> dict[str, object]:
    scope = "/user.slice/user-1000.slice/session-353701.scope"
    return authority.build_host_attestation_v42r1(
        transport_target_alias=authority.REMOTE_HOST_ALIAS,
        observed_hostname=authority.REMOTE_HOSTNAME,
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_python_invocation=authority.REMOTE_PYTHON,
        observed_python_realpath=authority.REMOTE_PYTHON_REALPATH,
        observed_python_version=authority.REMOTE_PYTHON_VERSION,
        observed_source_root=str(authority.REMOTE_SOURCE_ROOT),
        memory_total_bytes=540_433_203_200,
        memory_available_bytes=531_989_004_288,
        swap_total_bytes=8_589_930_496,
        swap_free_bytes=8_589_930_496,
        cgroup_mount_filesystem_type="cgroup2",
        cgroup_mount_root="/",
        cgroup_unified_scope_path=scope,
        cgroup_root_controllers=["cpu", "io", "memory", "pids"],
        cgroup_memory_ancestry=[
            {
                "cgroup_path": scope,
                "memory_max_mode": "MAX",
                "memory_max_bytes": None,
                "memory_current_bytes": 3_604_480,
            },
            {
                "cgroup_path": "/user.slice/user-1000.slice",
                "memory_max_mode": "MAX",
                "memory_max_bytes": None,
                "memory_current_bytes": 98_635_935_744,
            },
            {
                "cgroup_path": "/user.slice",
                "memory_max_mode": "MAX",
                "memory_max_bytes": None,
                "memory_current_bytes": 98_636_795_904,
            },
            {
                "cgroup_path": "/",
                "memory_max_mode": "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES",
                "memory_max_bytes": None,
                "memory_current_bytes": None,
            },
        ],
        filesystem_available_bytes=64 * 1024**3,
        attestation_stage=stage,
    )


def _pyz_artifact(
    source_facts: list[dict[str, object]],
    raw_by_path: dict[str, bytes],
    pyz_raw: bytes,
) -> dict[str, object]:
    facts = {str(row["relative_path"]): row for row in source_facts}
    members: list[dict[str, object]] = []
    for archive_path, module_name, member_kind, source_relative in (
        authority.REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS
    ):
        if member_kind == "GENERATED_STDLIB_MAIN":
            raw = authority.REMOTE_BOOTSTRAP_GENERATED_MAIN_BYTES
            blob = None
        elif member_kind == "GENERATED_EMPTY_PACKAGE_SHIM":
            raw = authority.REMOTE_BOOTSTRAP_GENERATED_EMPTY_PACKAGE_SHIM_BYTES
            blob = None
        else:
            raw = raw_by_path[str(source_relative)]
            blob = facts[str(source_relative)]["git_blob_oid"]
        members.append(
            {
                "archive_path": archive_path,
                "module_name": module_name,
                "member_kind": member_kind,
                "source_relative_path": source_relative,
                "git_blob_oid": blob,
                "member_mode": authority.REMOTE_BOOTSTRAP_PYZ_MEMBER_MODE,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return authority.build_remote_bootstrap_pyz_artifact_v42r1(
        members=members,
        pyz_sha256=hashlib.sha256(pyz_raw).hexdigest(),
        pyz_byte_count=len(pyz_raw),
    )


def _authority_documents() -> dict[str, dict[str, object]]:
    source_facts: list[dict[str, object]] = []
    raw_by_path: dict[str, bytes] = {}
    for index, relative in enumerate(sorted(authority.FORMAL_REMOTE_SOURCE_ROOTS)):
        raw = f"# runner fixture {index}\n".encode("ascii")
        raw_by_path[relative] = raw
        source_facts.append(
            {
                "relative_path": relative,
                "git_mode": "100644",
                "git_object_type": "blob",
                "git_blob_oid": _git_blob(raw),
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    source = authority.build_source_manifest_v42r1(
        source_commit="1" * 40,
        source_tree="2" * 40,
        source_facts=source_facts,
        source_roots=list(authority.FORMAL_REMOTE_SOURCE_ROOTS),
        dynamic_import_sites=[],
    )
    capsule_raw = b"runner fixture source capsule\n"
    pyz_raw = b"runner fixture remote bootstrap pyz\n"
    pyz_artifact = _pyz_artifact(source_facts, raw_by_path, pyz_raw)
    transport = authority.build_transport_manifest_v42r1(
        source_manifest=source,
        transport_facts=source_facts,
        source_archive_sha256=hashlib.sha256(capsule_raw).hexdigest(),
        source_archive_byte_count=len(capsule_raw),
        remote_bootstrap_pyz_artifact=pyz_artifact,
    )
    materialization_local = authority.build_local_materialization_attempt_v42r1(
        source_manifest=source, transport_manifest=transport
    )
    chain_paths = ["/"]
    current = ""
    for component in authority.REMOTE_ROOT.parts[1:]:
        current += "/" + component
        chain_paths.append(current)
    identity = [1, 2, stat.S_IFDIR | 0o700, authority.REMOTE_UID,
                authority.REMOTE_GID, 1, 0, 3, 4]
    control_identity = [1, 5, stat.S_IFREG | 0o400, authority.REMOTE_UID,
                        authority.REMOTE_GID, 1, 1, 3, 4]
    launcher_evidence = authority.build_remote_bootstrap_launcher_evidence_v42r1(
        source_manifest=source,
        transport_manifest=transport,
        local_materialization_attempt=materialization_local,
        observed_outer_python_command=materialization_local[
            "remote_bootstrap_outer_command"
        ],
        authorized_inner_python_command=materialization_local[
            "remote_bootstrap_inner_command"
        ],
        observed_outer_hostname=authority.REMOTE_HOSTNAME,
        observed_outer_user=authority.REMOTE_USER,
        observed_outer_uid=authority.REMOTE_UID,
        observed_outer_gid=authority.REMOTE_GID,
        observed_outer_python_invocation=authority.REMOTE_PYTHON,
        observed_outer_python_realpath=authority.REMOTE_PYTHON_REALPATH,
        observed_outer_python_version=authority.REMOTE_PYTHON_VERSION,
        outer_python_isolated_flag=1,
        outer_python_no_site_flag=1,
        outer_python_dont_write_bytecode=True,
        outer_five_control_verification_completed=True,
        outer_pyz_nofollow_stable_hash_completed=True,
        outer_lexical_chain=[
            {"absolute_path": path, "identity": list(identity[:5])}
            for path in chain_paths
        ],
        outer_root_identity=list(identity),
        outer_root_inventory=sorted(
            {
                authority.SOURCE_MANIFEST_NAME,
                authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
                authority.REMOTE_BOOTSTRAP_PYZ_NAME,
                authority.SOURCE_CAPSULE_NAME,
                authority.TRANSPORT_MANIFEST_NAME,
            }
        ),
        outer_five_control_identities={
            name: list(control_identity)
            for name in {
                authority.SOURCE_MANIFEST_NAME,
                authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
                authority.REMOTE_BOOTSTRAP_PYZ_NAME,
                authority.SOURCE_CAPSULE_NAME,
                authority.TRANSPORT_MANIFEST_NAME,
            }
        },
        runtime_pyz_memfd=authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_FD,
        runtime_evidence_memfd=authority.REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_FD,
        required_memfd_seals=authority.REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS,
        required_memfd_mode=authority.REMOTE_BOOTSTRAP_PYZ_FILE_MODE,
        runtime_memfd_uid=authority.REMOTE_UID,
        runtime_memfd_gid=authority.REMOTE_GID,
        runtime_memfds_inheritable_for_inner_exec=True,
        fixed_identity_effect_started=False,
    )
    runtime_binding = authority.build_remote_bootstrap_runtime_binding_v42r1(
        transport,
        source_manifest=source,
        local_materialization_attempt=materialization_local,
        trusted_launcher_evidence=launcher_evidence,
        observed_hostname=authority.REMOTE_HOSTNAME,
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_python_invocation=authority.REMOTE_PYTHON,
        observed_python_realpath=authority.REMOTE_PYTHON_REALPATH,
        observed_python_version=authority.REMOTE_PYTHON_VERSION,
        python_isolated_flag=1,
        python_no_site_flag=1,
        python_dont_write_bytecode=True,
        observed_inner_python_command=materialization_local[
            "remote_bootstrap_inner_command"
        ],
        observed_remote_bootstrap_pyz_fixed_path=str(
            authority.REMOTE_ROOT / authority.REMOTE_BOOTSTRAP_PYZ_NAME
        ),
        observed_remote_bootstrap_pyz_runtime_path=(
            authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH
        ),
        observed_remote_bootstrap_pyz_sha256=pyz_artifact["pyz_sha256"],
        observed_remote_bootstrap_pyz_byte_count=pyz_artifact["pyz_byte_count"],
        observed_member_manifest_id=pyz_artifact["member_manifest_id"],
        runtime_pyz_memfd_seals=authority.REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS,
        runtime_evidence_memfd_seals=authority.REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS,
        runtime_pyz_memfd_mode=authority.REMOTE_BOOTSTRAP_PYZ_FILE_MODE,
        runtime_evidence_memfd_mode=authority.REMOTE_BOOTSTRAP_PYZ_FILE_MODE,
        runtime_pyz_memfd_uid=authority.REMOTE_UID,
        runtime_pyz_memfd_gid=authority.REMOTE_GID,
        runtime_evidence_memfd_uid=authority.REMOTE_UID,
        runtime_evidence_memfd_gid=authority.REMOTE_GID,
        runtime_memfds_inheritable=True,
        observed_stdlib_module_origins=list(
            authority.REMOTE_BOOTSTRAP_STDLIB_MODULE_ORIGINS
        ),
        loaded_application_module_origins=[
            {
                **row,
                "observed_origin": authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH
                + "/"
                + row["archive_path"],
            }
            for row in pyz_artifact["application_module_origins"]
        ],
    )
    materialization_remote = authority.build_remote_materialization_attempt_v42r1(
        local_materialization_attempt=materialization_local,
        source_manifest=source,
        transport_manifest=transport,
        remote_bootstrap_runtime_binding=runtime_binding,
    )
    materialization_terminal = authority.build_materialization_terminal_v42r1(
        local_materialization_attempt=materialization_local,
        remote_materialization_attempt=materialization_remote,
        source_manifest=source,
        transport_manifest=transport,
    )
    predecessor = authority.build_predecessor_retention_binding_v42r1(
        retention_manifest_sha256=authority.PREDECESSOR_RETENTION_MANIFEST_SHA256,
        retention_manifest_byte_count=authority.PREDECESSOR_RETENTION_MANIFEST_BYTE_COUNT,
        independent_verification_sha256=(
            authority.PREDECESSOR_INDEPENDENT_VERIFICATION_SHA256
        ),
        independent_verification_byte_count=(
            authority.PREDECESSOR_INDEPENDENT_VERIFICATION_BYTE_COUNT
        ),
    )
    prepare_host = _host("PREPARE")
    receipt = authority.build_remote_prepare_receipt_v42r1(
        source_manifest=source,
        transport_manifest=transport,
        predecessor_retention_binding=predecessor,
        prepare_host_attestation=prepare_host,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
        remote_bootstrap_sha256=next(
            fact["sha256"]
            for fact in source["source_facts"]
            if fact["relative_path"]
            == "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py"
        ),
        remote_bootstrap_runtime_binding=runtime_binding,
    )
    local_attempt = runner.build_local_launch_attempt_v42r1(
        prepare_receipt=receipt,
        transport_target_alias=authority.REMOTE_HOST_ALIAS,
    )
    launch_host = _host("LAUNCH")
    attempt = authority.build_runner_attempt_v42(
        receipt,
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
        launch_host_attestation=launch_host,
        local_launch_attempt_id=local_attempt["local_launch_attempt_id"],
    )
    prepare_journal = runner._journal(  # noqa: SLF001
        schema="acfqp.v42_remote_ordinal2_prepare_attempt_journal.v42r1",
        domain="acfqp:v42-remote-ordinal2:prepare-journal",
        id_key="prepare_attempt_journal_id",
        fields={
            "formal_identity": authority.FORMAL_IDENTITY,
            "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "source_commit": receipt["source_commit"],
            "source_tree": receipt["source_tree"],
            "source_manifest_id": receipt["source_manifest_id"],
            "transport_manifest_id": receipt["transport_manifest_id"],
            "remote_host_alias": authority.REMOTE_HOST_ALIAS,
            "remote_hostname": authority.REMOTE_HOSTNAME,
            "prepare_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "outcome_or_tape_materialized": False,
            "formal_execution_performed": False,
            "same_identity_prepare_retry_forbidden": True,
        },
    )
    launch_journal = runner._journal(  # noqa: SLF001
        schema="acfqp.v42_remote_ordinal2_launch_attempt_journal.v42r1",
        domain="acfqp:v42-remote-ordinal2:launch-journal",
        id_key="launch_attempt_journal_id",
        fields={
            "formal_identity": authority.FORMAL_IDENTITY,
            "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "prepare_receipt_id": receipt["prepare_receipt_id"],
            "runner_attempt_id": attempt["runner_attempt_id"],
            "source_commit": receipt["source_commit"],
            "source_tree": receipt["source_tree"],
            "source_manifest_id": receipt["source_manifest_id"],
            "transport_manifest_id": receipt["transport_manifest_id"],
            "predecessor_binding_id": receipt["predecessor_binding_id"],
            "launch_host_attestation_id": launch_host["host_attestation_id"],
            "local_launch_attempt_id": local_attempt["local_launch_attempt_id"],
            "launch_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "formal_execution_performed": False,
            "outcome_fields_present": False,
            "same_identity_launch_retry_forbidden": True,
        },
    )
    stdout = b"partial supervisor output"
    stderr = b"typed supervisor failure"
    failure_payload = {
        "schema": "acfqp.v42_remote_ordinal2_runner_failure.v42r1",
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "prepare_receipt_id": receipt["prepare_receipt_id"],
        "runner_attempt_id": attempt["runner_attempt_id"],
        "launch_attempt_journal_id": launch_journal["launch_attempt_journal_id"],
        "local_launch_attempt_id": local_attempt["local_launch_attempt_id"],
        "failure_stage": "SUPERVISOR_INVOCATION",
        "failure_type": "V42RemoteOrdinal2ChildError",
        "failure_message": "fixture",
        "supervisor_failure_classification": "SUPERVISOR_TIMEOUT",
        "supervisor_returncode": -9,
        "supervisor_group_teardown": (
            "TERM_THEN_KILL_GROUP_CONFIRMED_DIRECT_WAIT_AND_PIPE_EOF"
        ),
        "supervisor_stdout": runner._stream_fact(  # noqa: SLF001
            stdout, runner.MAX_SUPERVISOR_STDOUT_BYTES
        ),
        "supervisor_stderr": runner._stream_fact(  # noqa: SLF001
            stderr, runner.MAX_SUPERVISOR_STDERR_BYTES
        ),
        "evidence_root_state": "DIRECTORY",
        "scientific_success": False,
        "same_identity_rerun_forbidden": True,
        "transport_disconnect_retry_authorized": False,
        "official_execution_allowed": False,
    }
    failure = {
        **failure_payload,
        "runner_failure_id": runner._content_id(  # noqa: SLF001
            "acfqp:v42-remote-ordinal2:runner-failure", failure_payload
        ),
    }
    return {
        "source": source,
        "transport": transport,
        "capsule": {"raw": capsule_raw},
        "pyz": {"raw": pyz_raw},
        "launcher_evidence": launcher_evidence,
        "runtime_binding": runtime_binding,
        "materialization_local": materialization_local,
        "materialization_remote": materialization_remote,
        "materialization_terminal": materialization_terminal,
        "prepare_host": prepare_host,
        "receipt": receipt,
        "local_attempt": local_attempt,
        "launch_host": launch_host,
        "attempt": attempt,
        "prepare_journal": prepare_journal,
        "launch_journal": launch_journal,
        "failure": failure,
        "stdout": {"raw": stdout},
        "stderr": {"raw": stderr},
    }


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _populate_transport_source_fixture(source: Path) -> None:
    for index, relative in enumerate(sorted(authority.FORMAL_REMOTE_SOURCE_ROOTS)):
        _write(source / relative, f"# runner fixture {index}\n".encode("ascii"))


def _secure_fixture_directories(root: Path) -> None:
    root.chmod(0o700)
    for path in root.rglob("*"):
        if path.is_dir():
            path.chmod(0o700)


def _complete_failure_mirror(
    base: Path,
) -> tuple[Path, Path, Path, dict[str, dict[str, object]]]:
    documents = _authority_documents()
    local_parent = base / "local"
    local_parent.mkdir()
    local_control = local_parent / "control"
    receipt_raw = canonical_json_bytes(documents["receipt"])
    runner.issue_local_launch_attempt_once_v42r1(
        local_control_root=local_control, prepare_receipt_raw=receipt_raw
    )
    mirror = base / "mirror"
    source = mirror / "source"
    source.mkdir(parents=True)
    _populate_failure_mirror(source, mirror, documents)
    return source, mirror, local_control, documents


def _populate_failure_mirror(
    source: Path,
    mirror: Path,
    documents: dict[str, dict[str, object]],
) -> None:
    _populate_transport_source_fixture(source)
    authority_root = source / authority.AUTHORITY_ROOT_RELATIVE
    evidence_root = source / authority.EVIDENCE_ROOT_RELATIVE
    receipt_raw = canonical_json_bytes(documents["receipt"])
    _write(
        mirror / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        canonical_json_bytes(documents["materialization_local"]),
    )
    _write(mirror / authority.SOURCE_CAPSULE_NAME, documents["capsule"]["raw"])
    _write(mirror / authority.SOURCE_MANIFEST_NAME, canonical_json_bytes(documents["source"]))
    _write(mirror / authority.TRANSPORT_MANIFEST_NAME, canonical_json_bytes(documents["transport"]))
    _write(mirror / authority.REMOTE_BOOTSTRAP_PYZ_NAME, documents["pyz"]["raw"])
    _write(
        mirror / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
        canonical_json_bytes(documents["materialization_remote"]),
    )
    _write(
        source / authority.MATERIALIZATION_TERMINAL_NAME,
        canonical_json_bytes(documents["materialization_terminal"]),
    )
    _write(mirror / authority.LOCAL_LAUNCH_ATTEMPT_NAME, canonical_json_bytes(documents["local_attempt"]))
    _write(mirror / authority.PREPARE_HOST_ATTESTATION_NAME, canonical_json_bytes(documents["prepare_host"]))
    _write(mirror / authority.LAUNCH_HOST_ATTESTATION_NAME, canonical_json_bytes(documents["launch_host"]))
    _write(source / authority.PREPARE_ATTEMPT_JOURNAL_NAME, canonical_json_bytes(documents["prepare_journal"]))
    _write(authority_root / authority.PREPARE_RECEIPT_NAME, receipt_raw)
    _write(source / authority.LAUNCH_ATTEMPT_JOURNAL_NAME, canonical_json_bytes(documents["launch_journal"]))
    _write(source / authority.LAUNCH_FAILURE_JOURNAL_NAME, canonical_json_bytes(documents["failure"]))
    _write(evidence_root / authority.ATTEMPT_NAME, canonical_json_bytes(documents["attempt"]))
    _write(evidence_root / authority.SUPERVISOR_STDOUT_NAME, documents["stdout"]["raw"])
    _write(evidence_root / authority.SUPERVISOR_STDERR_NAME, documents["stderr"]["raw"])
    _write(evidence_root / authority.FAILURE_NAME, canonical_json_bytes(documents["failure"]))
    _secure_fixture_directories(mirror)


def _remote_snapshot(root: Path) -> dict[str, tuple[int, int, int, str]]:
    return {
        path.relative_to(root).as_posix(): (
            path.lstat().st_mode,
            path.lstat().st_size,
            path.lstat().st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in root.rglob("*")
        if path.is_file()
    }


def _install_no_remote_access_guard(
    monkeypatch: pytest.MonkeyPatch, mirror_root: Path,
) -> None:
    """Make same-ordinal recovery prove that it never opens the mirror tree."""

    original_lstat = Path.lstat
    original_resolve = Path.resolve
    original_path_open = Path.open
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text
    original_open = os.open
    original_stat = os.stat
    original_listdir = os.listdir
    original_scandir = os.scandir
    original_readlink = os.readlink
    mirror_text = os.fspath(mirror_root)

    def descriptor_is_remote(descriptor: int | None) -> bool:
        if descriptor is None:
            return False
        try:
            target = original_readlink(f"/proc/self/fd/{descriptor}")
        except OSError:
            return False
        return target == mirror_text or target.startswith(mirror_text + "/")

    def path_is_remote(value: object, *, dir_fd: int | None = None) -> bool:
        if descriptor_is_remote(dir_fd):
            return True
        if isinstance(value, int):
            return descriptor_is_remote(value)
        try:
            text = os.fsdecode(os.fspath(value))  # type: ignore[arg-type]
        except TypeError:
            return False
        return text == mirror_text or text.startswith(mirror_text + "/")

    def blocked(operation: str, value: object) -> None:
        pytest.fail(f"same-ordinal recovery used remote {operation}: {value}")

    def guarded_lstat(path: Path):  # type: ignore[no-untyped-def]
        if path_is_remote(path):
            blocked("Path.lstat", path)
        return original_lstat(path)

    def guarded_resolve(path: Path, *args: object, **kwargs: object) -> Path:
        if path_is_remote(path):
            blocked("Path.resolve", path)
        return original_resolve(path, *args, **kwargs)

    def guarded_path_open(path: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if path_is_remote(path):
            blocked("Path.open", path)
        return original_path_open(path, *args, **kwargs)

    def guarded_read_bytes(path: Path) -> bytes:
        if path_is_remote(path):
            blocked("Path.read_bytes", path)
        return original_read_bytes(path)

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path_is_remote(path):
            blocked("Path.read_text", path)
        return original_read_text(path, *args, **kwargs)

    def guarded_open(
        path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None,
    ) -> int:
        if path_is_remote(path, dir_fd=dir_fd):
            blocked("os.open", path)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    def guarded_stat(
        path: object, *, dir_fd: int | None = None, follow_symlinks: bool = True,
    ):  # type: ignore[no-untyped-def]
        if path_is_remote(path, dir_fd=dir_fd):
            blocked("os.stat", path)
        return original_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    def guarded_listdir(path: object = ".") -> list[str]:
        if path_is_remote(path):
            blocked("os.listdir", path)
        return original_listdir(path)  # type: ignore[arg-type]

    def guarded_scandir(path: object = "."):  # type: ignore[no-untyped-def]
        if path_is_remote(path):
            blocked("os.scandir", path)
        return original_scandir(path)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "lstat", guarded_lstat)
    monkeypatch.setattr(Path, "resolve", guarded_resolve)
    monkeypatch.setattr(Path, "open", guarded_path_open)
    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(os, "open", guarded_open)
    monkeypatch.setattr(os, "stat", guarded_stat)
    monkeypatch.setattr(os, "listdir", guarded_listdir)
    monkeypatch.setattr(os, "scandir", guarded_scandir)
    monkeypatch.setattr(
        authority,
        "_snapshot_transport_tree_metadata_v42r1",
        lambda *args, **kwargs: blocked("authority tree scanner", (args, kwargs)),
    )


def _create_partial_collection_state(
    control: Path, documents: dict[str, dict[str, object]],
) -> tuple[Path, Path, Path]:
    attempts = runner._ensure_local_append_container(  # noqa: SLF001
        control, runner.LOCAL_COLLECTION_ATTEMPTS_NAME
    )
    snapshots = runner._ensure_local_append_container(  # noqa: SLF001
        control, runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
    )
    attempt = runner._build_expected_collection_attempt(  # noqa: SLF001
        collection_ordinal=1,
        local_launch_attempt_id=documents["local_attempt"]["local_launch_attempt_id"],
        previous_manifest=None,
    )
    attempt_path = attempts / "000001.json"
    runner.processio.write_once(attempt_path, canonical_json_bytes(attempt))
    ordinal = snapshots / "000001"
    runner.processio.create_one_shot_root(ordinal, expected_parent=snapshots)
    pending = ordinal / "PENDING"
    runner.processio.create_one_shot_root(pending, expected_parent=ordinal)
    artifacts = pending / "artifacts"
    runner.processio.create_one_shot_root(artifacts, expected_parent=pending)
    residual = artifacts / "partial.bin"
    runner.processio.write_once(residual, b"retained partial bytes")
    return attempt_path, pending, residual


def test_runner_contains_no_network_transport_implementation() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "subprocess" not in imported
    assert "socket" not in imported
    assert runner._supervisor_command()[:4] == (  # noqa: SLF001
        authority.REMOTE_PYTHON, "-I", "-S", "-B"
    )
    assert runner.LOCAL_LAUNCH_ATTEMPT_NAME == authority.LOCAL_LAUNCH_ATTEMPT_NAME


def test_local_launch_attempt_is_o_excl_and_retry_forbidden_after_publication() -> None:
    documents = _authority_documents()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-local-", dir="/tmp") as base:
        parent = Path(base) / "parent"
        parent.mkdir()
        control = parent / "control"
        receipt_raw = canonical_json_bytes(documents["receipt"])
        attempt = runner.issue_local_launch_attempt_once_v42r1(
            local_control_root=control, prepare_receipt_raw=receipt_raw
        )
        assert attempt["published_before_any_launch_transport_effect"] is True
        assert attempt["transport_effect_started"] is False
        assert attempt["same_identity_retry_forbidden_after_publication"] is True
        assert (control / runner.LOCAL_LAUNCH_ATTEMPT_NAME).is_file()
        with pytest.raises(Exception, match="durable publication|already exists|File exists"):
            runner.issue_local_launch_attempt_once_v42r1(
                local_control_root=control, prepare_receipt_raw=receipt_raw
            )


def test_prepare_receipt_bootstrap_hash_must_join_its_source_manifest_fact() -> None:
    documents = _authority_documents()
    receipt = documents["receipt"]
    with pytest.raises(Exception, match="bootstrap hash differs"):
        authority.build_remote_prepare_receipt_v42r1(
            source_manifest=documents["source"],
            transport_manifest=documents["transport"],
            predecessor_retention_binding=receipt["predecessor_retention_binding"],
            prepare_host_attestation=documents["prepare_host"],
            fresh_terminal_preregistration_id=receipt[
                "fresh_terminal_preregistration_id"
            ],
            history_freshness_manifest_id=receipt[
                "history_freshness_manifest_id"
                ],
                remote_bootstrap_sha256="0" * 64,
                remote_bootstrap_runtime_binding=documents["runtime_binding"],
            )


def test_remote_launch_requires_transported_local_attempt_before_first_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    documents = _authority_documents()
    monkeypatch.setattr(runner.processio, "require_isolated_python", lambda: None)
    mirror = tmp_path / "remote"
    source = mirror / "source"
    source.mkdir(parents=True)
    authority_root = source / authority.AUTHORITY_ROOT_RELATIVE
    _write(
        authority_root / authority.PREPARE_RECEIPT_NAME,
        canonical_json_bytes(documents["receipt"]),
    )
    monkeypatch.setattr(runner, "ROOT", source)
    monkeypatch.setattr(authority, "REMOTE_ROOT", mirror)
    monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source)
    monkeypatch.setattr(
        authority, "verify_prepare_receipt_v42", lambda *args, **kwargs: documents["receipt"]
    )
    def verify_phase(*args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        local_path = mirror / authority.LOCAL_LAUNCH_ATTEMPT_NAME
        if not local_path.exists():
            raise FileNotFoundError(local_path)
        return {
            "local_launch_attempt_raw": local_path.read_bytes(),
            "local_launch_attempt": documents["local_attempt"],
        }

    monkeypatch.setattr(
        authority, "verify_remote_control_phase_inventory_v42r1", verify_phase
    )
    writes: list[Path] = []
    monkeypatch.setattr(
        runner.processio,
        "write_once",
        lambda path, raw, **kwargs: writes.append(path),
    )
    with pytest.raises(FileNotFoundError):
        runner._launch_remote()  # noqa: SLF001
    assert writes == []

    _write(
        mirror / authority.LOCAL_LAUNCH_ATTEMPT_NAME,
        canonical_json_bytes(documents["local_attempt"]),
    )
    monkeypatch.setattr(
        authority,
        "observe_host_attestation_v42r1",
        lambda *args, **kwargs: {"host_attestation_id": "a" * 64},
    )
    monkeypatch.setattr(
        authority,
        "build_runner_attempt_v42",
        lambda *args, **kwargs: {
            "runner_attempt_id": "b" * 64,
            "launch_host_attestation_id": "a" * 64,
            "local_launch_attempt_id": documents["local_attempt"][
                "local_launch_attempt_id"
            ],
        },
    )

    class StopAfterWrite(RuntimeError):
        pass

    def stop_write(path: Path, raw: bytes, **kwargs: object) -> None:
        del raw, kwargs
        writes.append(path)
        raise StopAfterWrite

    writes.clear()
    monkeypatch.setattr(runner.processio, "write_once", stop_write)
    monkeypatch.setattr(
        runner.processio,
        "run_capped_child",
        lambda **kwargs: pytest.fail(f"supervisor ran before journal: {kwargs}"),
    )
    with pytest.raises(StopAfterWrite):
        runner._launch_remote()  # noqa: SLF001
    assert writes[0] == source / authority.LAUNCH_ATTEMPT_JOURNAL_NAME


def test_terminal_publication_is_irreversible_before_stdout_broken_pipe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    documents = _authority_documents()
    monkeypatch.setattr(runner.processio, "require_isolated_python", lambda: None)
    receipt = documents["receipt"]
    attempt = documents["attempt"]
    worker_start = authority.build_worker_start_v42(
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_authorization_secret_sha256="d" * 64,
    )
    consumption = authority.build_authority_consumption_v42(
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_start=worker_start,
    )
    campaign_payload = {"all_registered_episodes_terminal": True}
    campaign = {
        **campaign_payload,
        "fresh_terminal_campaign_id": runner.domains.extension_content_id_v42(
            runner.domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN,
            campaign_payload,
        ),
    }
    verification_payload = {
        "fresh_terminal_campaign_id": campaign["fresh_terminal_campaign_id"],
        "prepare_receipt_id": receipt["prepare_receipt_id"],
        "runner_attempt_id": attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "authority_consumption_id": consumption["authority_consumption_id"],
        "producer_or_runner_module_imported": False,
    }
    verification = {
        **verification_payload,
        "fresh_terminal_verification_id": runner.domains.extension_content_id_v42(
            runner.domains.CONSTRUCTION_K7_VERIFICATION_V42_DOMAIN,
            verification_payload,
        ),
    }
    envelope = supervisor._build_supervisor_envelope(  # noqa: SLF001
        receipt=receipt,
        attempt=attempt,
        worker_start=worker_start,
        consumption=consumption,
        campaign_document=campaign,
        verification_document=verification,
        all_terminal=True,
    )

    with tempfile.TemporaryDirectory(prefix="acfqp-v42-terminal-cut-", dir="/tmp") as base:
        base_path = Path(base)
        mirror = base_path / "mirror"
        source = mirror / "source"
        source.mkdir(parents=True)
        _populate_transport_source_fixture(source)
        authority_root = source / authority.AUTHORITY_ROOT_RELATIVE
        receipt_raw = canonical_json_bytes(receipt)
        _write(
            mirror / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            canonical_json_bytes(documents["materialization_local"]),
        )
        _write(mirror / authority.SOURCE_CAPSULE_NAME, documents["capsule"]["raw"])
        _write(
            mirror / authority.SOURCE_MANIFEST_NAME,
            canonical_json_bytes(documents["source"]),
        )
        _write(
            mirror / authority.TRANSPORT_MANIFEST_NAME,
            canonical_json_bytes(documents["transport"]),
        )
        _write(
            mirror / authority.REMOTE_BOOTSTRAP_PYZ_NAME,
            documents["pyz"]["raw"],
        )
        _write(
            mirror / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
            canonical_json_bytes(documents["materialization_remote"]),
        )
        _write(
            source / authority.MATERIALIZATION_TERMINAL_NAME,
            canonical_json_bytes(documents["materialization_terminal"]),
        )
        _write(
            mirror / authority.LOCAL_LAUNCH_ATTEMPT_NAME,
            canonical_json_bytes(documents["local_attempt"]),
        )
        _write(
            mirror / authority.PREPARE_HOST_ATTESTATION_NAME,
            canonical_json_bytes(documents["prepare_host"]),
        )
        _write(
            source / authority.PREPARE_ATTEMPT_JOURNAL_NAME,
            canonical_json_bytes(documents["prepare_journal"]),
        )
        _write(authority_root / authority.PREPARE_RECEIPT_NAME, receipt_raw)
        _secure_fixture_directories(mirror)

        original_remote_root = authority.REMOTE_ROOT
        original_remote_source = authority.REMOTE_SOURCE_ROOT
        original_stdout = runner.sys.stdout
        original_verify_prepare = authority.verify_prepare_receipt_v42
        original_build_runner = authority.build_runner_attempt_v42
        monkeypatch.setattr(runner, "ROOT", source)
        monkeypatch.setattr(authority, "REMOTE_ROOT", mirror)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source)
        monkeypatch.setattr(
            authority, "verify_prepare_receipt_v42", lambda *args, **kwargs: receipt
        )

        def verify_phase(phase: str, **kwargs: object) -> dict[str, object]:
            del kwargs
            result: dict[str, object] = {
                "local_launch_attempt_raw": canonical_json_bytes(
                    documents["local_attempt"]
                ),
                "local_launch_attempt": documents["local_attempt"],
            }
            if phase == "POST_LAUNCH":
                result["launch_host_attestation"] = documents["launch_host"]
            return result

        monkeypatch.setattr(
            authority, "verify_remote_control_phase_inventory_v42r1", verify_phase
        )
        monkeypatch.setattr(
            authority,
            "observe_host_attestation_v42r1",
            lambda *args, **kwargs: documents["launch_host"],
        )
        monkeypatch.setattr(
            authority,
            "build_runner_attempt_v42",
            lambda *args, **kwargs: attempt,
        )

        def completed_supervisor(**kwargs: object) -> SimpleNamespace:
            del kwargs
            evidence_root = source / authority.EVIDENCE_ROOT_RELATIVE
            runner.processio.write_once(
                evidence_root / authority.WORKER_START_NAME,
                canonical_json_bytes(worker_start),
            )
            runner.processio.write_once(
                evidence_root / authority.AUTHORITY_CONSUMPTION_NAME,
                canonical_json_bytes(consumption),
            )
            return SimpleNamespace(
                returncode=0,
                stdout=canonical_json_bytes(envelope) + b"\n",
                stderr=b"",
            )

        monkeypatch.setattr(
            runner.processio, "run_capped_child", completed_supervisor
        )

        class BrokenWriter:
            def write(self, raw: bytes) -> int:
                del raw
                raise BrokenPipeError("fixture downstream pipe closed")

        monkeypatch.setattr(
            runner.sys, "stdout", SimpleNamespace(buffer=BrokenWriter())
        )
        with pytest.raises(BrokenPipeError, match="downstream pipe closed"):
            runner._launch_remote()  # noqa: SLF001
        evidence_root = source / authority.EVIDENCE_ROOT_RELATIVE
        assert (evidence_root / authority.TERMINAL_NAME).is_file()
        assert not (source / authority.LAUNCH_FAILURE_JOURNAL_NAME).exists()
        assert not (evidence_root / authority.FAILURE_NAME).exists()

        monkeypatch.setattr(runner.sys, "stdout", original_stdout)
        monkeypatch.setattr(authority, "REMOTE_ROOT", original_remote_root)
        monkeypatch.setattr(
            authority, "REMOTE_SOURCE_ROOT", original_remote_source
        )
        monkeypatch.setattr(
            authority, "verify_prepare_receipt_v42", original_verify_prepare
        )
        monkeypatch.setattr(
            authority, "build_runner_attempt_v42", original_build_runner
        )
        local_parent = base_path / "local"
        local_parent.mkdir()
        local_control = local_parent / "control"
        runner.issue_local_launch_attempt_once_v42r1(
            local_control_root=local_control,
            prepare_receipt_raw=receipt_raw,
        )
        terminal_snapshot = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=local_control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        assert terminal_snapshot["collection_status"] == "COMPLETE_TERMINAL"


def test_ambiguous_disconnect_forbids_retry_and_allows_only_read_only_collection() -> None:
    documents = _authority_documents()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-ambiguous-", dir="/tmp") as base:
        base_path = Path(base)
        local_parent = base_path / "local"
        local_parent.mkdir()
        control = local_parent / "control"
        receipt_raw = canonical_json_bytes(documents["receipt"])
        runner.issue_local_launch_attempt_once_v42r1(
            local_control_root=control, prepare_receipt_raw=receipt_raw
        )
        ambiguity = runner.record_transport_ambiguity_once_v42r1(
            local_control_root=control,
            classification="SSH_DISCONNECT_AFTER_LAUNCH_EFFECT_POSSIBLE",
            transport_stdout=b"transport stdout",
            transport_stderr=b"connection lost",
        )
        assert ambiguity["retry_authorized"] is False
        assert ambiguity["only_read_only_collection_allowed"] is True
        with pytest.raises(Exception):
            runner.record_transport_ambiguity_once_v42r1(
                local_control_root=control,
                classification="SSH_DISCONNECT_AFTER_LAUNCH_EFFECT_POSSIBLE",
                transport_stdout=b"transport stdout",
                transport_stderr=b"connection lost",
            )
        mirror = base_path / "mirror"
        source = mirror / "source"
        source.mkdir(parents=True)
        _secure_fixture_directories(mirror)
        manifest = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        assert manifest["collection_status"] == (
            "AMBIGUOUS_INCOMPLETE_READ_ONLY_SNAPSHOT"
        )
        assert manifest["transport_ambiguity_present"] is True
        assert manifest["transport_ambiguity_id"] == ambiguity["transport_ambiguity_id"]
        assert manifest["same_identity_retry_authorized"] is False
        assert manifest["further_action_if_incomplete"] == "NEXT_COLLECTION_ORDINAL_ONLY"
        assert manifest["collection_ordinal"] == 1
        assert manifest["previous_collection_manifest_id"] is None


def test_typed_failure_collector_is_remote_read_only_and_retrieves_exact_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-collector-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        before = _remote_snapshot(mirror)
        monkeypatch.setattr(
            runner.processio,
            "run_capped_child",
            lambda **kwargs: pytest.fail(f"collector spawned a process: {kwargs}"),
        )
        manifest = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        after = _remote_snapshot(mirror)
        assert after == before
        assert manifest["collection_status"] == "COMPLETE_FAILURE"
        assert manifest["remote_process_started_by_collector"] is False
        assert manifest["remote_path_mutated_by_collector"] is False
        assert manifest["collection_is_read_only"] is True
        assert manifest["collection_input_provenance"] == "LOCAL_READ_ONLY_MIRROR"
        retained = {
            row["role"]: row
            for row in manifest["artifact_inventory"]
            if row["state"] == "EXACT_RETAINED"
        }
        assert retained["LAUNCH_FAILURE"]["sha256"] == hashlib.sha256(
            canonical_json_bytes(documents["failure"])
        ).hexdigest()
        assert retained["FAILURE"]["sha256"] == retained["LAUNCH_FAILURE"]["sha256"]


def test_collector_retains_exact_remote_bootstrap_pyz_fifth_control() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-pyz-retained-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        manifest = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        by_role = {row["role"]: row for row in manifest["artifact_inventory"]}
        pyz = by_role["REMOTE_BOOTSTRAP_PYZ"]
        pyz_raw = documents["pyz"]["raw"]
        assert pyz["state"] == "EXACT_RETAINED"
        assert pyz["remote_path"] == str(
            mirror / authority.REMOTE_BOOTSTRAP_PYZ_NAME
        )
        assert pyz["byte_count"] == len(pyz_raw)
        assert pyz["sha256"] == hashlib.sha256(pyz_raw).hexdigest()
        assert pyz["sha256"] == documents["transport"][
            "remote_bootstrap_pyz_artifact"
        ]["pyz_sha256"]


@pytest.mark.parametrize("attack", ["missing", "corrupt"])
def test_collector_never_completes_with_missing_or_corrupt_bootstrap_pyz(
    attack: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f"acfqp-v42-pyz-{attack}-", dir="/tmp"
    ) as base:
        source, mirror, control, _documents = _complete_failure_mirror(Path(base))
        pyz_path = mirror / authority.REMOTE_BOOTSTRAP_PYZ_NAME
        if attack == "missing":
            pyz_path.unlink()
        else:
            attacked = bytearray(pyz_path.read_bytes())
            attacked[0] ^= 1
            pyz_path.write_bytes(bytes(attacked))
        remote_before = _remote_snapshot(mirror)
        with pytest.raises(Exception, match="pyz|materialization|missing|inventory"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert _remote_snapshot(mirror) == remote_before
        ordinal_root = control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME / "000001"
        content_root = next(ordinal_root.iterdir())
        failure_manifest = runner._canonical_document(  # noqa: SLF001
            (content_root / "COLLECTION_MANIFEST.json").read_bytes(),
            "test fifth-control failure closure",
        )
        assert failure_manifest["collection_status"] == runner.COLLECTION_FAILURE_STATUS


def test_collector_rejects_self_consistent_bootstrap_pyz_transport_id_splice() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-pyz-id-splice-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        attacked_pyz_raw = documents["pyz"]["raw"] + b"spliced"
        original_artifact = documents["transport"]["remote_bootstrap_pyz_artifact"]
        attacked_artifact = authority.build_remote_bootstrap_pyz_artifact_v42r1(
            members=copy.deepcopy(original_artifact["members"]),
            pyz_sha256=hashlib.sha256(attacked_pyz_raw).hexdigest(),
            pyz_byte_count=len(attacked_pyz_raw),
        )
        original_transport = documents["transport"]
        attacked_transport = authority.build_transport_manifest_v42r1(
            source_manifest=documents["source"],
            transport_facts=copy.deepcopy(original_transport["transport_facts"]),
            source_archive_sha256=original_transport["source_archive_sha256"],
            source_archive_byte_count=original_transport["source_archive_byte_count"],
            remote_bootstrap_pyz_artifact=attacked_artifact,
        )
        (mirror / authority.REMOTE_BOOTSTRAP_PYZ_NAME).write_bytes(attacked_pyz_raw)
        (mirror / authority.TRANSPORT_MANIFEST_NAME).write_bytes(
            canonical_json_bytes(attacked_transport)
        )
        with pytest.raises(Exception, match="transport manifest differs"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )


def test_collection_chain_rejects_remote_bootstrap_pyz_path_splice() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-pyz-path-splice-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        manifest = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        attempt = runner._canonical_document(  # noqa: SLF001
            (
                control
                / runner.LOCAL_COLLECTION_ATTEMPTS_NAME
                / "000001.json"
            ).read_bytes(),
            "test fifth-control path splice attempt",
        )
        attacked = copy.deepcopy(manifest)
        row = next(
            item
            for item in attacked["artifact_inventory"]
            if item["role"] == "REMOTE_BOOTSTRAP_PYZ"
        )
        row["remote_path"] = str(mirror / "unrelated-bootstrap.pyz")
        payload = {
            key: value
            for key, value in attacked.items()
            if key != "collection_manifest_id"
        }
        attacked["collection_manifest_id"] = runner._content_id(  # noqa: SLF001
            "acfqp:v42-remote-ordinal2:collection-manifest", payload
        )
        with pytest.raises(Exception, match="remote role paths changed"):
            runner._verify_collection_chain_link(  # noqa: SLF001
                attempt=attempt,
                manifest=attacked,
                ordinal=1,
                content_directory_name=attacked["collection_manifest_id"],
                local_launch_attempt_id=documents["local_attempt"][
                    "local_launch_attempt_id"
                ],
                previous_manifest=None,
                expected_prepare_receipt_id=documents["receipt"][
                    "prepare_receipt_id"
                ],
                expected_collection_input_provenance="LOCAL_READ_ONLY_MIRROR",
                expected_remote_paths=runner._collection_remote_path_map(  # noqa: SLF001
                    source, mirror
                ),
            )


def test_cross_ordinal_bootstrap_pyz_rollback_preserves_old_snapshot_bytes() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-pyz-rollback-", dir="/tmp") as base:
        source, mirror, control, _documents = _complete_failure_mirror(Path(base))
        first = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        first_root = (
            control
            / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
            / "000001"
            / first["collection_manifest_id"]
        )
        first_bytes = {
            path.relative_to(first_root).as_posix(): path.read_bytes()
            for path in first_root.rglob("*")
            if path.is_file()
        }
        pyz_path = mirror / authority.REMOTE_BOOTSTRAP_PYZ_NAME
        attacked = bytearray(pyz_path.read_bytes())
        attacked[-1] ^= 1
        pyz_path.write_bytes(bytes(attacked))
        with pytest.raises(Exception, match="rolled back|changed an exact artifact|pyz"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )
        assert {
            path.relative_to(first_root).as_posix(): path.read_bytes()
            for path in first_root.rglob("*")
            if path.is_file()
        } == first_bytes


def test_collector_rejects_changed_transported_local_attempt() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-collector-attack-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        attacked = mirror / authority.LOCAL_LAUNCH_ATTEMPT_NAME
        document = bytearray(attacked.read_bytes())
        document[-1] ^= 1
        attacked.write_bytes(bytes(document))
        with pytest.raises(Exception, match="local launch attempt|canonical"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("supervisor_failure_classification", ["not", "typed"]),
        ("supervisor_returncode", True),
        ("supervisor_group_teardown", ""),
        ("evidence_root_state", "UNKNOWN"),
        ("failure_message", "x" * (runner.processio.MAX_EXCEPTION_MESSAGE_BYTES + 1)),
    ],
)
def test_collector_rejects_rehashed_semantically_untyped_launch_failure(
    field: str, value: object,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-failure-type-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        changed = dict(documents["failure"])
        changed[field] = value
        payload = {
            key: item for key, item in changed.items() if key != "runner_failure_id"
        }
        changed["runner_failure_id"] = runner._content_id(  # noqa: SLF001
            "acfqp:v42-remote-ordinal2:runner-failure", payload
        )
        changed_raw = canonical_json_bytes(changed)
        (source / authority.LAUNCH_FAILURE_JOURNAL_NAME).write_bytes(changed_raw)
        (
            source / authority.EVIDENCE_ROOT_RELATIVE / authority.FAILURE_NAME
        ).write_bytes(changed_raw)
        with pytest.raises(Exception, match="retry boundary|typed|semantics"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )


def test_collector_accepts_typed_failure_when_evidence_root_is_regular_file() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-evidence-file-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        evidence_root = source / authority.EVIDENCE_ROOT_RELATIVE
        for child in evidence_root.iterdir():
            child.unlink()
        evidence_root.rmdir()
        evidence_root.write_bytes(b"pre-existing evidence-root blocker\n")

        failure = dict(documents["failure"])
        failure.update(
            {
                "failure_stage": "EVIDENCE_ROOT_CREATION",
                "failure_message": "identity already exists",
                "supervisor_failure_classification": None,
                "supervisor_returncode": None,
                "supervisor_group_teardown": "NOT_REQUESTED",
                "supervisor_stdout": runner._stream_fact(  # noqa: SLF001
                    b"", runner.MAX_SUPERVISOR_STDOUT_BYTES
                ),
                "supervisor_stderr": runner._stream_fact(  # noqa: SLF001
                    b"", runner.MAX_SUPERVISOR_STDERR_BYTES
                ),
                "evidence_root_state": "REGULAR_FILE",
            }
        )
        payload = {
            key: value for key, value in failure.items() if key != "runner_failure_id"
        }
        failure["runner_failure_id"] = runner._content_id(  # noqa: SLF001
            "acfqp:v42-remote-ordinal2:runner-failure", payload
        )
        (source / authority.LAUNCH_FAILURE_JOURNAL_NAME).write_bytes(
            canonical_json_bytes(failure)
        )

        manifest = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        assert manifest["collection_status"] == "COMPLETE_FAILURE"
        by_role = {row["role"]: row for row in manifest["artifact_inventory"]}
        assert by_role["LAUNCH_FAILURE"]["state"] == "EXACT_RETAINED"
        assert by_role["ATTEMPT"]["state"] == "ABSENT"
        assert by_role["FAILURE"]["state"] == "ABSENT"


def test_collection_snapshots_are_append_only_and_later_terminal_state_is_collectible() -> None:
    documents = _authority_documents()
    temporary = tempfile.TemporaryDirectory(prefix="acfqp-v42-chain-", dir="/tmp")
    base = Path(temporary.name)
    local_parent = base / "local"
    local_parent.mkdir()
    control = local_parent / "control"
    runner.issue_local_launch_attempt_once_v42r1(
        local_control_root=control,
        prepare_receipt_raw=canonical_json_bytes(documents["receipt"]),
    )
    mirror = base / "mirror"
    source = mirror / "source"
    source.mkdir(parents=True)
    _secure_fixture_directories(mirror)

    first = runner.collect_remote_result_read_only_v42r1(
        remote_source_root=source,
        remote_control_root=mirror,
        local_control_root=control,
        collection_ordinal=1,
        require_fixed_remote_paths=False,
    )
    assert first["collection_status"] == "AMBIGUOUS_INCOMPLETE_READ_ONLY_SNAPSHOT"
    first_root = (
        control
        / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
        / "000001"
        / first["collection_manifest_id"]
    )
    first_bytes = {
        path.relative_to(first_root).as_posix(): path.read_bytes()
        for path in first_root.rglob("*")
        if path.is_file()
    }

    _populate_failure_mirror(source, mirror, documents)
    second = runner.collect_remote_result_read_only_v42r1(
        remote_source_root=source,
        remote_control_root=mirror,
        local_control_root=control,
        collection_ordinal=2,
        require_fixed_remote_paths=False,
    )
    assert second["collection_status"] == "COMPLETE_FAILURE"
    assert second["previous_collection_ordinal"] == 1
    assert second["previous_collection_manifest_id"] == first["collection_manifest_id"]
    assert second["previous_collection_status"] == first["collection_status"]
    assert {
        path.relative_to(first_root).as_posix(): path.read_bytes()
        for path in first_root.rglob("*")
        if path.is_file()
    } == first_bytes

    remote_before_reverify = _remote_snapshot(mirror)
    same_ordinal_readback = runner.collect_remote_result_read_only_v42r1(
        remote_source_root=source,
        remote_control_root=mirror,
        local_control_root=control,
        collection_ordinal=2,
        require_fixed_remote_paths=False,
    )
    assert same_ordinal_readback == second
    assert _remote_snapshot(mirror) == remote_before_reverify
    with pytest.raises(Exception, match="branch|gap|rollback|extra"):
        runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=4,
            require_fixed_remote_paths=False,
        )
    temporary.cleanup()


def test_attempt_only_interruption_is_locally_closed_then_next_ordinal_collects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-recover-attempt-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        attempts_root = runner._ensure_local_append_container(  # noqa: SLF001
            control, runner.LOCAL_COLLECTION_ATTEMPTS_NAME
        )
        runner._ensure_local_append_container(  # noqa: SLF001
            control, runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
        )
        expected_attempt = runner._build_expected_collection_attempt(  # noqa: SLF001
            collection_ordinal=1,
            local_launch_attempt_id=documents["local_attempt"][
                "local_launch_attempt_id"
            ],
            previous_manifest=None,
        )
        runner.processio.write_once(
            attempts_root / "000001.json",
            canonical_json_bytes(expected_attempt),
        )
        with monkeypatch.context() as no_remote:
            _install_no_remote_access_guard(no_remote, mirror)
            recovered = runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert recovered["schema"] == runner.COLLECTION_RECOVERY_MANIFEST_SCHEMA
        assert recovered["collection_status"] == runner.COLLECTION_FAILURE_STATUS
        assert recovered["remote_read_performed_for_snapshot"] is False
        assert recovered["collection_attempt_storage"]["state"] == "EXACT_CANONICAL"
        second = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=2,
            require_fixed_remote_paths=False,
        )
        assert second["collection_status"] == "COMPLETE_FAILURE"
        assert second["previous_collection_manifest_id"] == recovered[
            "collection_manifest_id"
        ]


def test_collection_container_pair_interruption_is_safe_to_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-container-pair-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        original = runner._ensure_local_append_container  # noqa: SLF001
        interrupted = False

        def create_first_then_interrupt(parent: Path, name: str) -> Path:
            nonlocal interrupted
            result = original(parent, name)
            if name == runner.LOCAL_COLLECTION_ATTEMPTS_NAME and not interrupted:
                interrupted = True
                raise KeyboardInterrupt("fixture interruption between collection roots")
            return result

        with monkeypatch.context() as first:
            first.setattr(
                runner, "_ensure_local_append_container", create_first_then_interrupt
            )
            with pytest.raises(KeyboardInterrupt, match="between collection roots"):
                runner.collect_remote_result_read_only_v42r1(
                    remote_source_root=source,
                    remote_control_root=mirror,
                    local_control_root=control,
                    collection_ordinal=1,
                    require_fixed_remote_paths=False,
                )
        assert {
            entry.name
            for entry in control.iterdir()
            if entry.name.startswith("COLLECTION_")
        } == {runner.LOCAL_COLLECTION_ATTEMPTS_NAME}
        completed = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        assert completed["collection_status"] == "COMPLETE_FAILURE"


@pytest.mark.parametrize("boundary", ["attempt_fchmod", "ordinal_chmod"])
def test_hostile_umask_publication_birth_is_recoverable(
    monkeypatch: pytest.MonkeyPatch, boundary: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"acfqp-v42-umask-{boundary}-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        attempt_path = (
            control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME / "000001.json"
        )
        ordinal_path = (
            control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME / "000001"
        )
        original_fchmod = os.fchmod
        original_chmod = os.chmod
        interrupted = False

        def interrupt_fchmod(descriptor: int, mode: int) -> None:
            nonlocal interrupted
            try:
                target = os.readlink(f"/proc/self/fd/{descriptor}")
            except OSError:
                target = ""
            if boundary == "attempt_fchmod" and target == str(attempt_path) and not interrupted:
                interrupted = True
                raise KeyboardInterrupt("fixture after O_EXCL before first fchmod")
            original_fchmod(descriptor, mode)

        def interrupt_chmod(path: object, mode: int, **kwargs: object) -> None:
            nonlocal interrupted
            if boundary == "ordinal_chmod" and os.fspath(path) == str(ordinal_path) and not interrupted:
                assert ordinal_path.lstat().st_mode & 0o777 == 0o700
                interrupted = True
                raise KeyboardInterrupt("fixture after mkdir before chmod")
            original_chmod(path, mode, **kwargs)  # type: ignore[arg-type]

        prior_umask = os.umask(0o777)
        try:
            with monkeypatch.context() as interrupted_call:
                interrupted_call.setattr(os, "fchmod", interrupt_fchmod)
                interrupted_call.setattr(os, "chmod", interrupt_chmod)
                with pytest.raises(KeyboardInterrupt, match="fixture"):
                    runner.collect_remote_result_read_only_v42r1(
                        remote_source_root=source,
                        remote_control_root=mirror,
                        local_control_root=control,
                        collection_ordinal=1,
                        require_fixed_remote_paths=False,
                    )
            observed_umask = os.umask(0o777)
            assert observed_umask == 0o777
            if boundary == "attempt_fchmod":
                assert attempt_path.lstat().st_mode & 0o777 == 0o400
                assert attempt_path.stat().st_size == 0
            else:
                assert ordinal_path.lstat().st_mode & 0o777 == 0o700
            with monkeypatch.context() as recovery:
                _install_no_remote_access_guard(recovery, mirror)
                manifest = runner.collect_remote_result_read_only_v42r1(
                    remote_source_root=source,
                    remote_control_root=mirror,
                    local_control_root=control,
                    collection_ordinal=1,
                    require_fixed_remote_paths=False,
                )
            assert manifest["schema"] == runner.COLLECTION_RECOVERY_MANIFEST_SCHEMA
        finally:
            os.umask(prior_umask)
        assert interrupted is True


def test_append_container_birth_survives_chmod_interruption_and_restores_umask(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-append-umask-", dir="/tmp") as base:
        _, _, control, _ = _complete_failure_mirror(Path(base))
        target = control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME
        original_chmod = os.chmod
        interrupted = False

        def interrupt_target(path: object, mode: int, **kwargs: object) -> None:
            nonlocal interrupted
            if os.fspath(path) == str(target) and not interrupted:
                assert target.lstat().st_mode & 0o777 == 0o700
                interrupted = True
                raise KeyboardInterrupt("fixture append container after mkdir")
            original_chmod(path, mode, **kwargs)  # type: ignore[arg-type]

        prior_umask = os.umask(0o777)
        try:
            with monkeypatch.context() as first:
                first.setattr(os, "chmod", interrupt_target)
                with pytest.raises(KeyboardInterrupt, match="append container"):
                    runner._ensure_local_append_container(  # noqa: SLF001
                        control, runner.LOCAL_COLLECTION_ATTEMPTS_NAME
                    )
            observed_umask = os.umask(0o777)
            assert observed_umask == 0o777
            assert target.lstat().st_mode & 0o777 == 0o700
            assert runner._ensure_local_append_container(  # noqa: SLF001
                control, runner.LOCAL_COLLECTION_ATTEMPTS_NAME
            ) == target
        finally:
            os.umask(prior_umask)
        assert interrupted is True


@pytest.mark.parametrize("failed_leaf", ["attempt", "residual"])
def test_recovery_leaf_fsync_failure_reenters_without_remote_access(
    monkeypatch: pytest.MonkeyPatch, failed_leaf: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"acfqp-v42-fsync-{failed_leaf}-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        attempt_path, _, residual = _create_partial_collection_state(control, documents)
        target = attempt_path if failed_leaf == "attempt" else residual
        original_fsync = os.fsync
        interrupted = False

        def interrupt_target(descriptor: int) -> None:
            nonlocal interrupted
            try:
                opened_path = os.readlink(f"/proc/self/fd/{descriptor}")
            except OSError:
                opened_path = ""
            if opened_path == str(target) and not interrupted:
                interrupted = True
                raise OSError(f"fixture {failed_leaf} fsync interruption")
            original_fsync(descriptor)

        with monkeypatch.context() as first:
            _install_no_remote_access_guard(first, mirror)
            first.setattr(os, "fsync", interrupt_target)
            with pytest.raises(OSError, match="fixture"):
                runner.collect_remote_result_read_only_v42r1(
                    remote_source_root=source,
                    remote_control_root=mirror,
                    local_control_root=control,
                    collection_ordinal=1,
                    require_fixed_remote_paths=False,
                )
        assert interrupted is True
        with monkeypatch.context() as second:
            _install_no_remote_access_guard(second, mirror)
            manifest = runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert manifest["schema"] == runner.COLLECTION_RECOVERY_MANIFEST_SCHEMA


def test_recovery_flushes_all_retained_leaves_and_ancestors_before_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-fsync-order-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        attempt_path, pending, residual = _create_partial_collection_state(control, documents)
        attempts = control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME
        snapshots = control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
        ordinal = snapshots / "000001"
        artifacts = pending / "artifacts"
        required = {
            str(attempt_path), str(attempts), str(residual), str(artifacts),
            str(pending), str(ordinal), str(snapshots), str(control),
        }
        flushed: list[str] = []
        original_fsync = os.fsync
        original_write_once = runner.processio.write_once

        def record_fsync(descriptor: int) -> None:
            try:
                flushed.append(os.readlink(f"/proc/self/fd/{descriptor}"))
            except OSError:
                flushed.append("<unobservable>")
            original_fsync(descriptor)

        def assert_flush_before_recovery_manifest(
            path: Path, raw: bytes, **kwargs: object,
        ) -> object:
            if path.name.startswith(runner.COLLECTION_RECOVERY_MANIFEST_PREFIX):
                missing = required - set(flushed)
                assert not missing, f"recovery manifest preceded durable refs: {missing}"
                last = lambda value: max(  # noqa: E731
                    index for index, observed in enumerate(flushed) if observed == value
                )
                assert flushed.index(str(attempt_path)) < last(str(attempts))
                assert flushed.index(str(residual)) < last(str(artifacts))
                assert last(str(artifacts)) < last(str(pending))
                assert last(str(pending)) < last(str(ordinal))
                assert last(str(ordinal)) < last(str(snapshots))
                assert last(str(snapshots)) < last(str(control))
            return original_write_once(path, raw, **kwargs)

        with monkeypatch.context() as recovery:
            _install_no_remote_access_guard(recovery, mirror)
            recovery.setattr(os, "fsync", record_fsync)
            recovery.setattr(
                runner.processio, "write_once", assert_flush_before_recovery_manifest
            )
            manifest = runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert manifest["schema"] == runner.COLLECTION_RECOVERY_MANIFEST_SCHEMA


def test_rename_effect_before_internal_fsync_is_durably_recovered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-rename-fsync-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        ordinal = control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME / "000001"
        original_fsync = os.fsync
        injected = False

        def interrupt_rename_parent_fsync(descriptor: int) -> None:
            nonlocal injected
            try:
                opened_path = os.readlink(f"/proc/self/fd/{descriptor}")
            except OSError:
                opened_path = ""
            published = (
                ordinal.is_dir()
                and not (ordinal / "PENDING").exists()
                and any(
                    len(entry.name) == 64 and entry.is_dir()
                    for entry in ordinal.iterdir()
                )
            )
            if opened_path == str(ordinal) and published and not injected:
                injected = True
                raise OSError("fixture renameat2 effect before parent fsync")
            original_fsync(descriptor)

        with monkeypatch.context() as first:
            first.setattr(os, "fsync", interrupt_rename_parent_fsync)
            with pytest.raises(OSError, match="renameat2 effect"):
                runner.collect_remote_result_read_only_v42r1(
                    remote_source_root=source,
                    remote_control_root=mirror,
                    local_control_root=control,
                    collection_ordinal=1,
                    require_fixed_remote_paths=False,
                )
        assert injected is True
        assert not (ordinal / "PENDING").exists()
        assert len(list(ordinal.iterdir())) == 1

        flushed: list[str] = []

        def record_fsync(descriptor: int) -> None:
            try:
                flushed.append(os.readlink(f"/proc/self/fd/{descriptor}"))
            except OSError:
                pass
            original_fsync(descriptor)

        with monkeypatch.context() as second:
            _install_no_remote_access_guard(second, mirror)
            second.setattr(os, "fsync", record_fsync)
            manifest = runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert manifest["schema"] == runner.COLLECTION_MANIFEST_SCHEMA
        assert str(ordinal) in flushed


def test_recovery_content_identity_excludes_inode_time_and_directory_size() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-portable-recovery-", dir="/tmp") as base:
        base_path = Path(base)
        roots = [base_path / "copy-a", base_path / "copy-b"]
        for index, root in enumerate(roots):
            root.mkdir(mode=0o700)
            nested = root / "nested"
            nested.mkdir(mode=0o700)
            if index == 1:
                # Grow and empty the second directory so its physical inode and
                # implementation-specific directory size/history differ.
                for ordinal in range(32):
                    transient = nested / f"discard-{ordinal:02d}"
                    transient.write_bytes(b"discard")
                    transient.unlink()
            retained = nested / "retained.bin"
            retained.write_bytes(b"portable residual bytes")
            retained.chmod(0o400)
            os.utime(root, ns=(1_000_000_000 + index, 2_000_000_000 + index))
            os.utime(nested, ns=(3_000_000_000 + index, 4_000_000_000 + index))
            os.utime(retained, ns=(5_000_000_000 + index, 6_000_000_000 + index))
        facts = [
            runner._snapshot_collection_recovery_residual(  # noqa: SLF001
                root, excluded_top_level_name=None
            )
            for root in roots
        ]
        assert facts[0] == facts[1]
        root_fact, inventory = facts[0]
        assert set(root_fact) == {"entry_type", "st_mode", "st_uid", "st_gid"}
        directory_row = next(row for row in inventory if row["entry_type"] == "DIRECTORY")
        assert directory_row["st_size"] is None
        assert directory_row["sha256"] is None


@pytest.mark.parametrize("linked_role", ["attempt", "manifest", "artifact"])
def test_collection_chain_rejects_external_hardlink_alias(linked_role: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f"acfqp-v42-hardlink-{linked_role}-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        first = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        content_root = (
            control
            / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
            / "000001"
            / first["collection_manifest_id"]
        )
        candidates = {
            "attempt": control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME / "000001.json",
            "manifest": content_root / "COLLECTION_MANIFEST.json",
            "artifact": next((content_root / "artifacts").iterdir()),
        }
        attacked = candidates[linked_role]
        alias = Path(base) / f"external-{linked_role}.alias"
        os.link(attacked, alias)
        assert attacked.lstat().st_nlink == 2
        with pytest.raises(Exception, match="linked|unsafe|nonregular"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )
        attempts = control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME
        assert {entry.name for entry in attempts.iterdir()} == {"000001.json"}


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("prepare_receipt_id", "f" * 64),
        ("transport_target_alias", "jtl110gpu"),
        ("remote_process_started_by_collector", True),
        ("collection_input_provenance", "FIXED_REMOTE_PATHS"),
        ("artifact_remote_path", "/unrelated/spliced-snapshot"),
    ],
)
def test_collection_chain_rejects_rehashed_semantic_splice(
    field: str, replacement: object,
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"acfqp-v42-chain-semantic-{field}-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        first = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        ordinal_root = control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME / "000001"
        content_root = ordinal_root / first["collection_manifest_id"]
        manifest_path = content_root / "COLLECTION_MANIFEST.json"
        changed = copy.deepcopy(first)
        if field == "artifact_remote_path":
            changed["artifact_inventory"][0]["remote_path"] = replacement
        else:
            changed[field] = replacement
        payload = {
            key: value for key, value in changed.items() if key != "collection_manifest_id"
        }
        changed_id = runner._content_id(  # noqa: SLF001
            "acfqp:v42-remote-ordinal2:collection-manifest", payload
        )
        changed["collection_manifest_id"] = changed_id
        manifest_path.chmod(0o600)
        manifest_path.write_bytes(canonical_json_bytes(changed))
        manifest_path.chmod(0o400)
        content_root.rename(ordinal_root / changed_id)
        with pytest.raises(Exception, match="identity|role paths"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )
        attempts = control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME
        assert {entry.name for entry in attempts.iterdir()} == {"000001.json"}


@pytest.mark.parametrize(
    "boundary",
    [
        "attempt_write",
        "ordinal_mkdir",
        "pending_mkdir",
        "artifact_mkdir",
        "artifact_write",
        "ordinary_manifest_write",
        "rename_before",
        "rename_after",
        "snapshot_fsync_after_rename",
        "readback_after_rename",
    ],
)
def test_collection_interruption_matrix_recovers_without_remote_reread(
    monkeypatch: pytest.MonkeyPatch, boundary: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"acfqp-v42-recovery-{boundary}-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        original_write = runner.processio.write_once
        original_create = runner.processio.create_one_shot_root
        original_rename = runner.processio.rename_noreplace
        original_fsync_directory = runner.processio.fsync_directory
        original_verify_chain = runner._verify_previous_collection_chain  # noqa: SLF001
        injected = False
        renamed = False

        def partial_write(path: Path, raw: bytes) -> None:
            previous_umask = os.umask(0o077)
            try:
                descriptor = os.open(
                    path,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | os.O_NOFOLLOW
                    | os.O_CLOEXEC,
                    0o400,
                )
            finally:
                os.umask(previous_umask)
            try:
                os.fchmod(descriptor, 0o400)
                os.write(descriptor, raw[: max(1, len(raw) // 2)])
            finally:
                os.close(descriptor)

        def injected_write(path: Path, raw: bytes, **kwargs: object) -> object:
            nonlocal injected
            target = (
                boundary == "attempt_write"
                and path.parent.name == runner.LOCAL_COLLECTION_ATTEMPTS_NAME
                or boundary == "artifact_write"
                and path.parent.name == "artifacts"
                or boundary == "ordinary_manifest_write"
                and path.name == "COLLECTION_MANIFEST.json"
            )
            if target and not injected:
                injected = True
                partial_write(path, raw)
                raise KeyboardInterrupt(f"fixture interruption at {boundary}")
            return original_write(path, raw, **kwargs)

        def injected_create(
            path: Path, *, expected_parent: Path,
        ) -> None:
            nonlocal injected
            target = (
                boundary == "ordinal_mkdir"
                and path.name == "000001"
                or boundary == "pending_mkdir"
                and path.name == "PENDING"
                or boundary == "artifact_mkdir"
                and path.name == "artifacts"
            )
            original_create(path, expected_parent=expected_parent)
            if target and not injected:
                injected = True
                raise KeyboardInterrupt(f"fixture interruption at {boundary}")

        def injected_rename(parent: Path, old_name: str, new_name: str) -> None:
            nonlocal injected, renamed
            if boundary == "rename_before" and not injected:
                injected = True
                raise KeyboardInterrupt("fixture interruption before rename")
            original_rename(parent, old_name, new_name)
            renamed = True
            if boundary == "rename_after" and not injected:
                injected = True
                raise KeyboardInterrupt("fixture interruption after rename")

        def injected_fsync(path: Path) -> None:
            nonlocal injected
            if (
                boundary == "snapshot_fsync_after_rename"
                and renamed
                and path.name == runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
                and not injected
            ):
                injected = True
                raise OSError("fixture snapshot fsync interruption")
            original_fsync_directory(path)

        def injected_verify_chain(**kwargs: object) -> object:
            nonlocal injected
            if (
                boundary == "readback_after_rename"
                and renamed
                and kwargs.get("expected_count") == 1
                and not injected
            ):
                injected = True
                raise OSError("fixture readback interruption")
            return original_verify_chain(**kwargs)

        with monkeypatch.context() as first_call:
            first_call.setattr(runner.processio, "write_once", injected_write)
            first_call.setattr(
                runner.processio, "create_one_shot_root", injected_create
            )
            first_call.setattr(runner.processio, "rename_noreplace", injected_rename)
            first_call.setattr(runner.processio, "fsync_directory", injected_fsync)
            first_call.setattr(
                runner, "_verify_previous_collection_chain", injected_verify_chain
            )
            with pytest.raises(BaseException, match="fixture"):
                runner.collect_remote_result_read_only_v42r1(
                    remote_source_root=source,
                    remote_control_root=mirror,
                    local_control_root=control,
                    collection_ordinal=1,
                    require_fixed_remote_paths=False,
                )
        assert injected is True

        with monkeypatch.context() as second_call:
            _install_no_remote_access_guard(second_call, mirror)
            recovered = runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert recovered["collection_ordinal"] == 1
        assert recovered["collection_status"] in {
            "COMPLETE_FAILURE", runner.COLLECTION_FAILURE_STATUS
        }
        if boundary in {
            "rename_after", "snapshot_fsync_after_rename", "readback_after_rename"
        }:
            assert recovered["schema"] == runner.COLLECTION_MANIFEST_SCHEMA
        third = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=2,
            require_fixed_remote_paths=False,
        )
        assert third["collection_status"] == "COMPLETE_FAILURE"
        assert third["previous_collection_manifest_id"] == recovered[
            "collection_manifest_id"
        ]


def test_partial_recovery_manifest_is_retained_in_next_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-recovery-generation-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        attempts_root = runner._ensure_local_append_container(  # noqa: SLF001
            control, runner.LOCAL_COLLECTION_ATTEMPTS_NAME
        )
        runner._ensure_local_append_container(  # noqa: SLF001
            control, runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
        )
        expected_attempt = runner._build_expected_collection_attempt(  # noqa: SLF001
            collection_ordinal=1,
            local_launch_attempt_id=documents["local_attempt"][
                "local_launch_attempt_id"
            ],
            previous_manifest=None,
        )
        runner.processio.write_once(
            attempts_root / "000001.json", canonical_json_bytes(expected_attempt)
        )
        original_write = runner.processio.write_once
        partial_path: Path | None = None

        def interrupt_recovery_manifest(
            path: Path, raw: bytes, **kwargs: object,
        ) -> object:
            nonlocal partial_path
            if (
                path.name.startswith(runner.COLLECTION_RECOVERY_MANIFEST_PREFIX)
                and partial_path is None
            ):
                partial_path = path
                previous_umask = os.umask(0o077)
                try:
                    descriptor = os.open(
                        path,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | os.O_NOFOLLOW
                        | os.O_CLOEXEC,
                        0o400,
                    )
                finally:
                    os.umask(previous_umask)
                try:
                    os.fchmod(descriptor, 0o400)
                    os.write(descriptor, raw[: max(1, len(raw) // 3)])
                finally:
                    os.close(descriptor)
                raise KeyboardInterrupt("fixture partial recovery manifest")
            return original_write(path, raw, **kwargs)

        with monkeypatch.context() as interrupted:
            interrupted.setattr(
                runner.processio, "write_once", interrupt_recovery_manifest
            )
            with pytest.raises(KeyboardInterrupt, match="partial recovery"):
                runner.collect_remote_result_read_only_v42r1(
                    remote_source_root=source,
                    remote_control_root=mirror,
                    local_control_root=control,
                    collection_ordinal=1,
                    require_fixed_remote_paths=False,
                )
        assert partial_path is not None
        partial_raw = partial_path.read_bytes()
        partial_name = partial_path.name
        partial_sha = hashlib.sha256(partial_raw).hexdigest()

        with monkeypatch.context() as recovery:
            _install_no_remote_access_guard(recovery, mirror)
            manifest = runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert manifest["schema"] == runner.COLLECTION_RECOVERY_MANIFEST_SCHEMA
        assert manifest["recovery_generation"] == 2
        retained_partial = next(
            row
            for row in manifest["residual_inventory"]
            if row["relative_path"] == partial_name
        )
        assert retained_partial["sha256"] == partial_sha
        content_root = (
            control
            / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
            / "000001"
            / manifest["collection_manifest_id"]
        )
        assert (content_root / partial_name).read_bytes() == partial_raw


def test_collection_chain_rejects_branch_and_rollback() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-chain-attack-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        first = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        ordinal_root = control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME / "000001"
        (ordinal_root / ("f" * 64)).mkdir()
        with pytest.raises(Exception, match="uniquely content-addressed"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )
        (ordinal_root / ("f" * 64)).rmdir()
        (ordinal_root / first["collection_manifest_id"] / "COLLECTION_MANIFEST.json").unlink()
        with pytest.raises(Exception):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )


def test_collection_chain_rejects_old_artifact_byte_or_mode_change() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-chain-bytes-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        first = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        content_root = (
            control
            / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
            / "000001"
            / first["collection_manifest_id"]
        )
        artifact = next((content_root / "artifacts").iterdir())
        original = artifact.read_bytes()
        artifact.chmod(0o600)
        artifact.write_bytes(original + b"tamper")
        artifact.chmod(0o400)
        with pytest.raises(Exception, match="bytes changed"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )


def test_collection_chain_rejects_old_snapshot_changed_after_its_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-old-snapshot-race-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        first = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        content_root = (
            control
            / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
            / "000001"
            / first["collection_manifest_id"]
        )
        attacked = next((content_root / "artifacts").iterdir())
        original_verify = runner._verify_collection_snapshot_storage  # noqa: SLF001
        injected = False

        def verify_then_touch(
            root: Path, manifest: dict[str, object],
        ) -> None:
            nonlocal injected
            original_verify(root, manifest)  # type: ignore[arg-type]
            if not injected:
                retained = attacked.read_bytes()
                attacked.chmod(0o600)
                attacked.write_bytes(retained)
                attacked.chmod(0o400)
                injected = True

        monkeypatch.setattr(
            runner, "_verify_collection_snapshot_storage", verify_then_touch
        )
        with pytest.raises(Exception, match="whole-chain verification"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )
        assert {
            entry.name
            for entry in (control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME).iterdir()
        } == {"000001.json"}


def test_collection_rollback_closes_failed_ordinal_and_later_exact_state_is_collectible(
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-monotonic-", dir="/tmp") as base:
        source, mirror, control, documents = _complete_failure_mirror(Path(base))
        first = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        assert first["collection_status"] == "COMPLETE_FAILURE"
        first_root = (
            control
            / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME
            / "000001"
            / first["collection_manifest_id"]
        )
        first_bytes = {
            path.relative_to(first_root).as_posix(): path.read_bytes()
            for path in first_root.rglob("*")
            if path.is_file()
        }

        (source / authority.LAUNCH_FAILURE_JOURNAL_NAME).unlink()
        (source / authority.EVIDENCE_ROOT_RELATIVE / authority.FAILURE_NAME).unlink()
        with pytest.raises(Exception, match="rolled back|changed an exact artifact"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )
        second_ordinal_root = (
            control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME / "000002"
        )
        second_content = list(second_ordinal_root.iterdir())
        assert len(second_content) == 1
        second = runner._canonical_document(  # noqa: SLF001
            (second_content[0] / "COLLECTION_MANIFEST.json").read_bytes(),
            "test collection closure",
        )
        assert second["collection_status"] == runner.COLLECTION_FAILURE_STATUS
        assert second["previous_collection_status"] == "COMPLETE_FAILURE"
        assert second["collection_failure"]["failure_stage"].startswith("REMOTE_")
        assert all(
            row["state"] == runner.COLLECTION_UNOBSERVED_STATE
            for row in second["artifact_inventory"]
        )
        assert list((second_content[0] / "artifacts").iterdir()) == []

        failure_raw = canonical_json_bytes(documents["failure"])
        _write(source / authority.LAUNCH_FAILURE_JOURNAL_NAME, failure_raw)
        _write(
            source / authority.EVIDENCE_ROOT_RELATIVE / authority.FAILURE_NAME,
            failure_raw,
        )
        third = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=3,
            require_fixed_remote_paths=False,
        )
        assert third["collection_status"] == "COMPLETE_FAILURE"
        assert third["previous_collection_status"] == runner.COLLECTION_FAILURE_STATUS
        assert {
            path.relative_to(first_root).as_posix(): path.read_bytes()
            for path in first_root.rglob("*")
            if path.is_file()
        } == first_bytes


def test_transport_ambiguity_cannot_disappear_or_be_added_after_collection() -> None:
    documents = _authority_documents()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-ambiguity-chain-", dir="/tmp") as base:
        base_path = Path(base)
        local_parent = base_path / "local"
        local_parent.mkdir()
        control = local_parent / "control"
        runner.issue_local_launch_attempt_once_v42r1(
            local_control_root=control,
            prepare_receipt_raw=canonical_json_bytes(documents["receipt"]),
        )
        ambiguity = runner.record_transport_ambiguity_once_v42r1(
            local_control_root=control,
            classification="SSH_DISCONNECT_AFTER_LAUNCH_EFFECT_POSSIBLE",
            transport_stdout=b"",
            transport_stderr=b"disconnect",
        )
        mirror = base_path / "mirror"
        source = mirror / "source"
        source.mkdir(parents=True)
        _secure_fixture_directories(mirror)
        first = runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        assert first["transport_ambiguity_id"] == ambiguity["transport_ambiguity_id"]
        (control / runner.LOCAL_TRANSPORT_AMBIGUITY_NAME).unlink()
        with pytest.raises(Exception, match="ambiguity appeared, disappeared, or changed"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=2,
                require_fixed_remote_paths=False,
            )
        assert {
            path.name
            for path in (control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME).iterdir()
        } == {"000001.json"}

        second_parent = base_path / "second-local"
        second_parent.mkdir()
        second_control = second_parent / "control"
        runner.issue_local_launch_attempt_once_v42r1(
            local_control_root=second_control,
            prepare_receipt_raw=canonical_json_bytes(documents["receipt"]),
        )
        runner.collect_remote_result_read_only_v42r1(
            remote_source_root=source,
            remote_control_root=mirror,
            local_control_root=second_control,
            collection_ordinal=1,
            require_fixed_remote_paths=False,
        )
        with pytest.raises(Exception, match="extra|partial|collection"):
            runner.record_transport_ambiguity_once_v42r1(
                local_control_root=second_control,
                classification="SSH_DISCONNECT_AFTER_LAUNCH_EFFECT_POSSIBLE",
                transport_stdout=b"",
                transport_stderr=b"late",
            )


def test_collector_rejects_path_splice_and_unsafe_local_controls_before_attempt(
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-splice-", dir="/tmp") as base:
        base_path = Path(base)
        _, mirror, control, _ = _complete_failure_mirror(base_path)
        unrelated = base_path / "unrelated" / "not-source"
        unrelated.mkdir(parents=True)
        with pytest.raises(Exception, match="one lexical snapshot"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=unrelated,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert not (control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME).exists()

        receipt_path = control / runner.LOCAL_PREPARE_RECEIPT_NAME
        receipt_path.chmod(0o600)
        with pytest.raises(Exception, match="unsafe mode|nonregular|misowned"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=mirror / "source",
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert not (control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME).exists()
        receipt_path.chmod(0o400)
        attempt_path = control / runner.LOCAL_LAUNCH_ATTEMPT_NAME
        attempt_path.chmod(0o600)
        with pytest.raises(Exception, match="unsafe mode|nonregular|misowned"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=mirror / "source",
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        assert not (control / runner.LOCAL_COLLECTION_ATTEMPTS_NAME).exists()


def test_collector_rejects_unsafe_manifested_ancestor_directory_mode() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-dir-mode-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        (source / "scripts").chmod(0o777)
        with pytest.raises(Exception, match="unrecognized directory"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )


@pytest.mark.parametrize("attack", ["delete_recreate", "in_place_mutate"])
def test_collector_rejects_cross_scan_file_splice_and_closes_ordinal(
    monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-parent-race-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        attacked = mirror / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME
        trigger = source / authority.PREPARE_ATTEMPT_JOURNAL_NAME
        original_read = runner.processio.read_fixed_artifact
        injected = False

        def read_then_attack(path: Path, maximum: int) -> bytes:
            nonlocal injected
            raw = original_read(path, maximum)
            if path == trigger and not injected:
                retained = attacked.read_bytes()
                if attack == "delete_recreate":
                    attacked.unlink()
                    attacked.write_bytes(retained)
                else:
                    changed = bytearray(retained)
                    changed[0] ^= 1
                    with attacked.open("r+b") as stream:
                        stream.write(changed)
                        stream.flush()
                        os.fsync(stream.fileno())
                injected = True
            return raw

        monkeypatch.setattr(
            runner.processio, "read_fixed_artifact", read_then_attack
        )
        with pytest.raises(Exception, match="file changed across observation"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        ordinal_root = control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME / "000001"
        content_root = next(ordinal_root.iterdir())
        manifest = runner._canonical_document(  # noqa: SLF001
            (content_root / "COLLECTION_MANIFEST.json").read_bytes(),
            "test parent-race closure",
        )
        assert manifest["collection_status"] == runner.COLLECTION_FAILURE_STATUS
        assert manifest["collection_failure"]["failure_stage"] == (
            "REMOTE_FILE_STABILITY_VALIDATION"
        )


def test_collector_whole_tree_boundary_rejects_late_nested_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-tree-race-", dir="/tmp") as base:
        source, mirror, control, _ = _complete_failure_mirror(Path(base))
        original = runner._verify_remote_collection_known_inventory  # noqa: SLF001

        def verify_then_mutate(**kwargs: object) -> None:
            original(**kwargs)
            (source / "scripts" / "late-unmanifested.py").write_bytes(b"late\n")

        monkeypatch.setattr(
            runner, "_verify_remote_collection_known_inventory", verify_then_mutate
        )
        with pytest.raises(Exception, match="remote tree changed"):
            runner.collect_remote_result_read_only_v42r1(
                remote_source_root=source,
                remote_control_root=mirror,
                local_control_root=control,
                collection_ordinal=1,
                require_fixed_remote_paths=False,
            )
        ordinal_root = control / runner.LOCAL_COLLECTION_SNAPSHOTS_NAME / "000001"
        content_root = next(ordinal_root.iterdir())
        manifest = runner._canonical_document(  # noqa: SLF001
            (content_root / "COLLECTION_MANIFEST.json").read_bytes(),
            "test whole-tree closure",
        )
        assert manifest["collection_status"] == runner.COLLECTION_FAILURE_STATUS
        assert manifest["collection_failure"]["failure_stage"] == (
            "REMOTE_TREE_FINAL_SNAPSHOT"
        )
