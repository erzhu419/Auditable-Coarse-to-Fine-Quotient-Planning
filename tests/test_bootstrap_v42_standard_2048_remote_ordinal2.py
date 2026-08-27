from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile

import pytest

from acfqp import construction_k7_standard_2048_remote_execution_authority_v42r1 as authority
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import bootstrap_v42_standard_2048_remote_ordinal2 as bootstrap


ROOT = Path(__file__).resolve().parents[1]
_PYZ_RAW_BY_TRANSPORT_ID: dict[str, bytes] = {}


def _all_fixture_source_paths() -> tuple[str, ...]:
    return tuple(
        sorted(
            set(authority.FORMAL_REMOTE_SOURCE_ROOTS)
            | {
                str(source_relative)
                for _archive, _module, member_kind, source_relative in (
                    authority.REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS
                )
                if member_kind == "COMMITTED_GIT_BLOB"
            }
        )
    )


def _live_bootstrap_constants() -> dict[str, object]:
    return {
        name: getattr(authority, name)
        for name in bootstrap._COMMITTED_BOOTSTRAP_CONSTANT_NAMES  # noqa: SLF001
    }


@pytest.mark.parametrize("boundary", ["write_fchmod", "directory_chmod"])
def test_bootstrap_publication_birth_ignores_hostile_umask_and_restores_it(
    monkeypatch: pytest.MonkeyPatch, boundary: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"acfqp-v42-bootstrap-umask-{boundary}-", dir="/tmp") as base:
        parent = Path(base)
        target = parent / ("artifact.bin" if boundary == "write_fchmod" else "one-shot")
        original_fchmod = os.fchmod
        original_chmod = os.chmod
        interrupted = False

        def interrupt_fchmod(descriptor: int, mode: int) -> None:
            nonlocal interrupted
            opened = os.readlink(f"/proc/self/fd/{descriptor}")
            if boundary == "write_fchmod" and opened == str(target) and not interrupted:
                interrupted = True
                raise KeyboardInterrupt("fixture bootstrap write birth")
            original_fchmod(descriptor, mode)

        def interrupt_chmod(path: object, mode: int, **kwargs: object) -> None:
            nonlocal interrupted
            if boundary == "directory_chmod" and os.fspath(path) == str(target) and not interrupted:
                assert target.lstat().st_mode & 0o777 == 0o700
                interrupted = True
                raise KeyboardInterrupt("fixture bootstrap directory birth")
            original_chmod(path, mode, **kwargs)  # type: ignore[arg-type]

        prior_umask = os.umask(0o777)
        try:
            with monkeypatch.context() as interrupted_call:
                interrupted_call.setattr(os, "fchmod", interrupt_fchmod)
                interrupted_call.setattr(os, "chmod", interrupt_chmod)
                with pytest.raises(KeyboardInterrupt, match="fixture bootstrap"):
                    if boundary == "write_fchmod":
                        bootstrap._write_once(target, b"durable bytes")  # noqa: SLF001
                    else:
                        bootstrap._create_one_shot_directory(  # noqa: SLF001
                            target, expected_parent=parent
                        )
            observed_umask = os.umask(0o777)
            assert observed_umask == 0o777
            assert target.lstat().st_mode & 0o777 == (
                0o400 if boundary == "write_fchmod" else 0o700
            )
        finally:
            os.umask(prior_umask)
        assert interrupted is True


def test_materialized_nested_directories_and_member_are_safe_at_birth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-member-umask-", dir="/tmp") as base:
        target = Path(base) / "source"
        first_relative = transport["transport_facts"][0]["relative_path"]  # type: ignore[index]
        first_path = target / str(first_relative)
        original_fchmod = os.fchmod
        interrupted = False

        def interrupt_first_member(descriptor: int, mode: int) -> None:
            nonlocal interrupted
            opened = os.readlink(f"/proc/self/fd/{descriptor}")
            if opened == str(first_path) and not interrupted:
                interrupted = True
                raise KeyboardInterrupt("fixture first materialized member birth")
            original_fchmod(descriptor, mode)

        prior_umask = os.umask(0o777)
        try:
            with monkeypatch.context() as interrupted_call:
                interrupted_call.setattr(os, "fchmod", interrupt_first_member)
                with pytest.raises(KeyboardInterrupt, match="materialized member"):
                    bootstrap.materialize_capsule_v42r1(
                        archive_raw=archive_raw,
                        source_manifest_raw=canonical_json_bytes(source),
                        transport_manifest_raw=canonical_json_bytes(transport),
                        target_root=target,
                        require_fixed_target=False,
                    )
            observed_umask = os.umask(0o777)
            assert observed_umask == 0o777
            assert first_path.lstat().st_mode & 0o777 == 0o400
            for directory in (target, *first_path.parents):
                if directory == Path(base).parent:
                    break
                if directory == Path(base):
                    continue
                assert directory.lstat().st_mode & 0o777 == 0o700
        finally:
            os.umask(prior_umask)
        assert interrupted is True


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - Git object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def _capsule_fixture(
    *, live_pyz_members: bool = False,
) -> tuple[bytes, dict[str, object], dict[str, object]]:
    entries: list[dict[str, str]] = []
    blobs: dict[str, bytes] = {}
    source_facts: list[dict[str, object]] = []
    for index, relative in enumerate(_all_fixture_source_paths()):
        if live_pyz_members and relative in {
            str(source_relative)
            for _archive, _module, member_kind, source_relative in (
                authority.REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS
            )
            if member_kind == "COMMITTED_GIT_BLOB"
        }:
            raw = (ROOT / relative).read_bytes()
        else:
            raw = f"# capsule fixture {index}\n".encode("ascii")
        oid = _git_blob(raw)
        entry = {
            "relative_path": relative,
            "git_mode": "100644",
            "git_object_type": "blob",
            "git_blob_oid": oid,
        }
        entries.append(entry)
        blobs[oid] = raw
        source_facts.append(
            {
                **entry,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    for relative, extra_raw in (
        ("TRANSPORT_ONLY.txt", b"transport inventory is intentionally broader\n"),
        (
            ".tmp/exact-freeze/v41-committed-transport-fixture.json",
            b'{"committed_tmp_member":true}\n',
        ),
    ):
        extra_oid = _git_blob(extra_raw)
        entries.append(
            {
                "relative_path": relative,
                "git_mode": "100644",
                "git_object_type": "blob",
                "git_blob_oid": extra_oid,
            }
        )
        blobs[extra_oid] = extra_raw
    entries.sort(key=lambda row: row["relative_path"])
    archive_raw, transport_facts = bootstrap._deterministic_ustar_bytes(  # noqa: SLF001
        entries, blobs
    )
    committed_constants = _live_bootstrap_constants()
    pyz_raw, pyz_artifact = bootstrap._deterministic_remote_bootstrap_pyz_bytes(  # noqa: SLF001
        entries,
        blobs,
        committed_bootstrap_constants=committed_constants,
    )
    source = authority.build_source_manifest_v42r1(
        source_commit="1" * 40,
        source_tree="2" * 40,
        source_facts=source_facts,
        source_roots=list(authority.FORMAL_REMOTE_SOURCE_ROOTS),
        dynamic_import_sites=[],
    )
    transport = authority.build_transport_manifest_v42r1(
        source_manifest=source,
        transport_facts=transport_facts,
        source_archive_sha256=hashlib.sha256(archive_raw).hexdigest(),
        source_archive_byte_count=len(archive_raw),
        remote_bootstrap_pyz_artifact=pyz_artifact,
    )
    _PYZ_RAW_BY_TRANSPORT_ID[str(transport["transport_manifest_id"])] = pyz_raw
    return archive_raw, source, transport


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _install_five_control_bytes(
    remote_root: Path,
    archive_raw: bytes,
    source: dict[str, object],
    transport: dict[str, object],
) -> dict[str, object]:
    remote_root.mkdir(mode=0o700)
    remote_root.chmod(0o700)
    local_attempt = authority.build_local_materialization_attempt_v42r1(
        source_manifest=source,  # type: ignore[arg-type]
        transport_manifest=transport,  # type: ignore[arg-type]
    )
    controls = (
        (
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            canonical_json_bytes(local_attempt),
        ),
        (authority.SOURCE_CAPSULE_NAME, archive_raw),
        (authority.SOURCE_MANIFEST_NAME, canonical_json_bytes(source)),
        (authority.TRANSPORT_MANIFEST_NAME, canonical_json_bytes(transport)),
        (
            authority.REMOTE_BOOTSTRAP_PYZ_NAME,
            _PYZ_RAW_BY_TRANSPORT_ID[str(transport["transport_manifest_id"])],
        ),
    )
    for name, raw in controls:
        bootstrap._write_once(remote_root / name, raw)  # noqa: SLF001
    return local_attempt


def _install_formal_controls(
    remote_root: Path,
    archive_raw: bytes,
    source: dict[str, object],
    transport: dict[str, object],
) -> dict[str, object]:
    local_attempt = _install_five_control_bytes(
        remote_root, archive_raw, source, transport
    )
    (*_documents, snapshot) = bootstrap._read_formal_controls(  # noqa: SLF001
        remote_root
    )
    launcher_evidence = authority.build_remote_bootstrap_launcher_evidence_v42r1(
        source_manifest=source,  # type: ignore[arg-type]
        transport_manifest=transport,  # type: ignore[arg-type]
        local_materialization_attempt=local_attempt,
        observed_outer_python_command=local_attempt["remote_bootstrap_outer_command"],
        authorized_inner_python_command=local_attempt["remote_bootstrap_inner_command"],
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
        outer_lexical_chain=bootstrap._snapshot_full_lexical_chain_nofollow(  # noqa: SLF001
            remote_root
        ),
        outer_root_identity=snapshot["root_identity"],
        outer_root_inventory=snapshot["root_inventory"],
        outer_five_control_identities=snapshot["control_identities"],
        runtime_pyz_memfd=authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_FD,
        runtime_evidence_memfd=authority.REMOTE_BOOTSTRAP_RUNTIME_EVIDENCE_FD,
        required_memfd_seals=authority.REMOTE_BOOTSTRAP_REQUIRED_MEMFD_SEALS,
        required_memfd_mode=authority.REMOTE_BOOTSTRAP_PYZ_FILE_MODE,
        runtime_memfd_uid=authority.REMOTE_UID,
        runtime_memfd_gid=authority.REMOTE_GID,
        runtime_memfds_inheritable_for_inner_exec=True,
        fixed_identity_effect_started=False,
    )
    pyz = transport["remote_bootstrap_pyz_artifact"]
    loaded_origins = [
        {
            **row,
            "observed_origin": authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH
            + "/"
            + row["archive_path"],
        }
        for row in pyz["application_module_origins"]  # type: ignore[index]
    ]
    runtime_binding = authority.build_remote_bootstrap_runtime_binding_v42r1(
        transport,  # type: ignore[arg-type]
        source_manifest=source,  # type: ignore[arg-type]
        local_materialization_attempt=local_attempt,
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
        observed_inner_python_command=local_attempt["remote_bootstrap_inner_command"],
        observed_remote_bootstrap_pyz_fixed_path=str(
            remote_root / authority.REMOTE_BOOTSTRAP_PYZ_NAME
        ),
        observed_remote_bootstrap_pyz_runtime_path=(
            authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH
        ),
        observed_remote_bootstrap_pyz_sha256=pyz["pyz_sha256"],  # type: ignore[index]
        observed_remote_bootstrap_pyz_byte_count=pyz["pyz_byte_count"],  # type: ignore[index]
        observed_member_manifest_id=pyz["member_manifest_id"],  # type: ignore[index]
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
        loaded_application_module_origins=loaded_origins,
    )
    bootstrap._REMOTE_BOOTSTRAP_RUNTIME_BINDING = runtime_binding  # noqa: SLF001
    bootstrap._REMOTE_BOOTSTRAP_RUNTIME_BINDING_INSTALLATION_CLOSED = False  # noqa: SLF001
    return local_attempt


def _trusted_launcher_selftest_command(
    remote_root: Path, transport: dict[str, object],
) -> list[str]:
    pyz = transport["remote_bootstrap_pyz_artifact"]
    return [
        authority.REMOTE_PYTHON,
        "-I",
        "-S",
        "-B",
        "-c",
        authority.REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES.decode("utf-8"),
        str(remote_root),
        "--self-test-bootstrap-runtime",
        str(transport["transport_manifest_id"]),
        str(pyz["pyz_sha256"]),  # type: ignore[index]
        str(pyz["pyz_byte_count"]),  # type: ignore[index]
    ]


def _trusted_launcher_wrapper_source(
    remote_root: Path,
    transport: dict[str, object],
    *,
    preopened_targets: tuple[int, ...],
    capture_execve: bool,
) -> str:
    launcher = authority.REMOTE_BOOTSTRAP_TRUSTED_LAUNCHER_BYTES.decode("utf-8")
    pyz = transport["remote_bootstrap_pyz_artifact"]
    arguments = [
        str(remote_root),
        "--self-test-bootstrap-runtime",
        str(transport["transport_manifest_id"]),
        str(pyz["pyz_sha256"]),  # type: ignore[index]
        str(pyz["pyz_byte_count"]),  # type: ignore[index]
    ]
    expected_orig_argv = [
        authority.REMOTE_PYTHON,
        "-I",
        "-S",
        "-B",
        "-c",
        launcher,
        *arguments,
    ]
    capture = ""
    if capture_execve:
        capture = """
def captured_execve(executable, argv, environment):
    sys.stdout.write(json.dumps({"executable": executable, "argv": argv, "env": environment}, sort_keys=True))
    raise SystemExit(0)
os.execve = captured_execve
"""
    return f"""
import json
import os
import sys
launcher = {launcher!r}
targets = {preopened_targets!r}
source_fd = os.open('/dev/null', os.O_RDONLY)
try:
    for target in targets:
        os.dup2(source_fd, target, inheritable=True)
finally:
    if source_fd not in targets:
        os.close(source_fd)
sys.argv = {['-c', *arguments]!r}
sys.orig_argv = {expected_orig_argv!r}
{capture}
exec(compile(launcher, '<trusted-launcher>', 'exec'), {{}})
"""


def _tree_snapshot(root: Path) -> dict[str, tuple[str, int, bytes]]:
    result: dict[str, tuple[str, int, bytes]] = {}
    for path in sorted(root.rglob("*")):
        observed = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISREG(observed.st_mode):
            result[relative] = ("FILE", stat.S_IMODE(observed.st_mode), path.read_bytes())
        elif stat.S_ISDIR(observed.st_mode):
            result[relative] = ("DIRECTORY", stat.S_IMODE(observed.st_mode), b"")
        else:
            result[relative] = ("OTHER", stat.S_IMODE(observed.st_mode), b"")
    return result


def test_trusted_launcher_clean_host_runs_only_verified_sealed_pyz(
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-clean-host-", dir="/tmp") as base:
        base_path = Path(base)
        archive_raw, source, transport = _capsule_fixture(live_pyz_members=True)
        remote_root = base_path / "five-controls"
        _install_five_control_bytes(remote_root, archive_raw, source, transport)
        unrelated = base_path / "clean-cwd"
        unrelated.mkdir()
        completed = subprocess.run(
            _trusted_launcher_selftest_command(remote_root, transport),
            cwd=unrelated,
            env={},
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stderr.decode(
            "utf-8", errors="replace"
        )
        result = authority.loads_canonical_json(completed.stdout.rstrip(b"\n"))
        assert result["trusted_outer_launcher_verified"] is True
        assert result["sealed_memfd_runtime_verified"] is True
        assert result["remote_materialization_attempt_published"] is False
        assert [
            row["archive_path"] for row in result["loaded_application_module_origins"]
        ] == [row[0] for row in authority.REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS]
        assert not (
            remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME
        ).exists()


@pytest.mark.parametrize(
    "preopened_targets",
    [(), (37,), (38,), (37, 38)],
)
def test_trusted_launcher_handles_hostile_fd37_fd38_layouts(
    preopened_targets: tuple[int, ...],
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-hostile-fd-", dir="/tmp") as base:
        remote_root = Path(base) / "five-controls"
        archive_raw, source, transport = _capsule_fixture(live_pyz_members=True)
        _install_five_control_bytes(remote_root, archive_raw, source, transport)
        wrapper = _trusted_launcher_wrapper_source(
            remote_root,
            transport,
            preopened_targets=preopened_targets,
            capture_execve=False,
        )
        completed = subprocess.run(
            [authority.REMOTE_PYTHON, "-I", "-S", "-B", "-c", wrapper],
            cwd=base,
            env={},
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stderr.decode(
            "utf-8", errors="replace"
        )
        result = authority.loads_canonical_json(completed.stdout.rstrip(b"\n"))
        assert result["sealed_memfd_runtime_verified"] is True
        assert result["loaded_application_module_origins"]


def test_inner_pread_hash_preserves_pyz_offset_and_zipimport_reachability() -> None:
    generated = authority.REMOTE_BOOTSTRAP_GENERATED_MAIN_BYTES.decode("utf-8")
    assert "os.pread(" in generated
    assert "os.lseek(descriptor" not in generated
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-pread-pyz-", dir="/tmp") as base:
        remote_root = Path(base) / "five-controls"
        archive_raw, source, transport = _capsule_fixture(live_pyz_members=True)
        _install_five_control_bytes(remote_root, archive_raw, source, transport)
        wrapper = _trusted_launcher_wrapper_source(
            remote_root,
            transport,
            preopened_targets=(37, 38),
            capture_execve=False,
        )
        completed = subprocess.run(
            [authority.REMOTE_PYTHON, "-I", "-S", "-B", "-c", wrapper],
            cwd=base,
            env={},
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stderr.decode(
            "utf-8", errors="replace"
        )
        result = authority.loads_canonical_json(completed.stdout.rstrip(b"\n"))
        assert result["loaded_application_module_origins"]


def test_trusted_launcher_execve_uses_exact_inner_argv_and_empty_environment() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-execve-", dir="/tmp") as base:
        remote_root = Path(base) / "five-controls"
        archive_raw, source, transport = _capsule_fixture(live_pyz_members=True)
        _install_five_control_bytes(remote_root, archive_raw, source, transport)
        wrapper = _trusted_launcher_wrapper_source(
            remote_root,
            transport,
            preopened_targets=(37, 38),
            capture_execve=True,
        )
        completed = subprocess.run(
            [authority.REMOTE_PYTHON, "-I", "-S", "-B", "-c", wrapper],
            cwd=base,
            env={},
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stderr.decode(
            "utf-8", errors="replace"
        )
        captured = json.loads(completed.stdout.decode("utf-8"))
        pyz = transport["remote_bootstrap_pyz_artifact"]
        assert captured == {
            "executable": authority.REMOTE_PYTHON,
            "argv": [
                authority.REMOTE_PYTHON,
                "-I",
                "-S",
                "-B",
                authority.REMOTE_BOOTSTRAP_RUNTIME_PYZ_PATH,
                "--self-test-bootstrap-runtime",
                transport["transport_manifest_id"],
                pyz["pyz_sha256"],  # type: ignore[index]
                str(pyz["pyz_byte_count"]),  # type: ignore[index]
            ],
            "env": {},
        }


@pytest.mark.parametrize("attack", ["missing", "corrupt"])
def test_trusted_launcher_missing_or_corrupt_pyz_fails_before_remote_attempt(
    attack: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f"acfqp-v42-pyz-{attack}-", dir="/tmp"
    ) as base:
        base_path = Path(base)
        archive_raw, source, transport = _capsule_fixture(live_pyz_members=True)
        remote_root = base_path / f"five-controls-{attack}"
        _install_five_control_bytes(remote_root, archive_raw, source, transport)
        pyz_path = remote_root / authority.REMOTE_BOOTSTRAP_PYZ_NAME
        if attack == "missing":
            pyz_path.unlink()
        else:
            attacked = bytearray(pyz_path.read_bytes())
            attacked[len(attacked) // 2] ^= 1
            pyz_path.chmod(0o600)
            pyz_path.write_bytes(bytes(attacked))
            pyz_path.chmod(0o400)
        completed = subprocess.run(
            _trusted_launcher_selftest_command(remote_root, transport),
            cwd=base_path,
            env={},
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode != 0
        assert not (
            remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME
        ).exists()


@pytest.mark.parametrize(
    "attack",
    ["same_content_new_inode", "root_inventory", "ancestor_mode"],
)
def test_outer_evidence_rejects_control_or_ancestor_drift_before_inner_effect(
    monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f"acfqp-v42-evidence-{attack}-", dir="/tmp"
    ) as base:
        remote_root = Path(base) / "remote"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", remote_root / "source")
        archive_raw, source, transport = _capsule_fixture()
        _install_formal_controls(remote_root, archive_raw, source, transport)
        binding = bootstrap._REMOTE_BOOTSTRAP_RUNTIME_BINDING  # noqa: SLF001
        assert binding is not None
        evidence = binding["trusted_launcher_evidence"]
        parent_mode = stat.S_IMODE(remote_root.parent.lstat().st_mode)
        if attack == "same_content_new_inode":
            path = remote_root / authority.REMOTE_BOOTSTRAP_PYZ_NAME
            retained = path.read_bytes()
            old_inode = path.lstat().st_ino
            old_path = remote_root / "old-pyz-inode"
            path.rename(old_path)
            bootstrap._write_once(path, retained)  # noqa: SLF001
            assert path.lstat().st_ino != old_inode
            old_path.unlink()
        elif attack == "root_inventory":
            bootstrap._write_once(  # noqa: SLF001
                remote_root / "UNRECOGNIZED", b"attack"
            )
        else:
            remote_root.parent.chmod(0o777)
        try:
            with pytest.raises(
                bootstrap.V42RemoteOrdinal2BootstrapError,
                match="five controls|snapshot changed|ancestor",
            ):
                bootstrap.read_verified_remote_bootstrap_controls_for_runtime_v42r1(
                    evidence
                )
        finally:
            remote_root.parent.chmod(parent_mode)
        assert not (
            remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME
        ).exists()


def test_deterministic_ustar_materializes_exact_regular_read_only_inventory() -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-capsule-", dir="/tmp") as base:
        target = Path(base) / "materialized"
        observed_source, observed_transport = bootstrap.materialize_capsule_v42r1(
            archive_raw=archive_raw,
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=target,
            require_fixed_target=False,
        )
        assert observed_source == source
        assert observed_transport == transport
        observed_files = {
            path.relative_to(target).as_posix()
            for path in target.rglob("*")
            if path.is_file()
        }
        assert observed_files == {
            row["relative_path"] for row in transport["transport_facts"]
        }
        assert all(
            stat.S_IMODE(path.lstat().st_mode) == 0o444
            for path in target.rglob("*")
            if path.is_file()
        )
        with pytest.raises(
            bootstrap.V42RemoteOrdinal2BootstrapError,
            match="retry is forbidden",
        ):
            bootstrap.materialize_capsule_v42r1(
                archive_raw=archive_raw,
                source_manifest_raw=canonical_json_bytes(source),
                transport_manifest_raw=canonical_json_bytes(transport),
                target_root=target,
                require_fixed_target=False,
            )


def test_live_transport_walk_verifies_committed_tmp_and_only_exact_mutable_roots(
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-tmp-walk-", dir="/tmp"
    ) as base:
        base_path = Path(base)
        target = base_path / "materialized"
        bootstrap.materialize_capsule_v42r1(
            archive_raw=archive_raw,
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=target,
            require_fixed_target=False,
        )
        committed_tmp = (
            target / ".tmp/exact-freeze/v41-committed-transport-fixture.json"
        )
        assert committed_tmp.is_file()

        authority_root = target / authority.AUTHORITY_ROOT_RELATIVE
        evidence_root = target / authority.EVIDENCE_ROOT_RELATIVE
        authority_root.mkdir(mode=0o700)
        evidence_root.mkdir(mode=0o700)
        bootstrap._write_once(  # noqa: SLF001
            authority_root / authority.PREPARE_RECEIPT_NAME, b"fixture receipt"
        )
        bootstrap._write_once(  # noqa: SLF001
            evidence_root / authority.ATTEMPT_NAME, b"fixture attempt"
        )
        authority.verify_live_transport_inventory_v42r1(
            target, transport, source, require_fixed_root=False
        )

        bootstrap._write_once(  # noqa: SLF001
            authority_root / "UNRECOGNIZED", b"attack"
        )
        with pytest.raises(
            authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
            match="unrecognized entry",
        ):
            authority.verify_live_transport_inventory_v42r1(
                target, transport, source, require_fixed_root=False
            )

        attacked = base_path / "sibling-attack"
        bootstrap.materialize_capsule_v42r1(
            archive_raw=archive_raw,
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=attacked,
            require_fixed_target=False,
        )
        sibling = (
            attacked
            / ".tmp/exact-freeze/v42-standard-2048-remote-ordinal2-authority-sibling"
        )
        sibling.mkdir(mode=0o700)
        with pytest.raises(
            authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
            match="unmanifested or unsafe",
        ):
            authority.verify_live_transport_inventory_v42r1(
                attacked, transport, source, require_fixed_root=False
            )

        redirected = base_path / "reserved-root-redirect"
        bootstrap.materialize_capsule_v42r1(
            archive_raw=archive_raw,
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=redirected,
            require_fixed_target=False,
        )
        outside = base_path / "outside-mutable-root"
        outside.mkdir()
        (redirected / authority.AUTHORITY_ROOT_RELATIVE).symlink_to(
            outside, target_is_directory=True
        )
        with pytest.raises(
            authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
            match="redirected|unsafe",
        ):
            authority.verify_live_transport_inventory_v42r1(
                redirected, transport, source, require_fixed_root=False
            )


def _assert_actual_tmp_materialization(
    capsule_root: Path,
    source: dict[str, object],
    transport: dict[str, object],
    actual_tmp_paths: tuple[str, ...],
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-actual-tmp-", dir="/tmp"
    ) as base:
        materialized = Path(base) / "materialized"
        bootstrap.materialize_capsule_v42r1(
            archive_raw=(capsule_root / authority.SOURCE_CAPSULE_NAME).read_bytes(),
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=materialized,
            require_fixed_target=False,
        )
        authority.verify_live_transport_inventory_v42r1(
            materialized,
            transport,  # type: ignore[arg-type]
            source,  # type: ignore[arg-type]
            require_fixed_root=False,
        )
        assert {
            path.relative_to(materialized).as_posix()
            for path in (materialized / ".tmp").rglob("*")
            if path.is_file()
        } == set(actual_tmp_paths)


def test_capsule_hash_tamper_fails_before_target_creation(tmp_path: Path) -> None:
    archive_raw, source, transport = _capsule_fixture()
    attacked = bytearray(archive_raw)
    attacked[513] ^= 1
    target = tmp_path / "must-stay-absent"
    with pytest.raises(
        bootstrap.V42RemoteOrdinal2BootstrapError,
        match="transported capsule bytes changed",
    ):
        bootstrap.materialize_capsule_v42r1(
            archive_raw=bytes(attacked),
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=target,
            require_fixed_target=False,
        )
    assert not target.exists()


@pytest.mark.parametrize("attack", ["symlink", "traversal", "extra", "mode"])
def test_capsule_rejects_nonregular_traversal_extra_and_mode_attacks(
    tmp_path: Path, attack: str
) -> None:
    original_archive, source, original_transport = _capsule_fixture()
    expected = original_transport["transport_facts"]
    payload_by_name: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(original_archive), mode="r:") as original:
        for member in original:
            extracted = original.extractfile(member)
            assert extracted is not None
            payload_by_name[member.name] = extracted.read()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for index, fact in enumerate(expected):
            name = fact["relative_path"]
            member = tarfile.TarInfo(name)
            member.size = fact["byte_count"]
            member.mode = 0o444
            member.uid = member.gid = 0
            member.uname = member.gname = ""
            member.mtime = 0
            raw = payload_by_name[name]
            if index == 0 and attack == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                member.size = 0
                archive.addfile(member)
                continue
            if index == 0 and attack == "traversal":
                member.name = "../escape"
            if index == 0 and attack == "mode":
                member.mode = 0o777
            archive.addfile(member, io.BytesIO(raw))
        if attack == "extra":
            extra = tarfile.TarInfo("EXTRA")
            extra.size = 0
            extra.mode = 0o444
            extra.uid = extra.gid = 0
            extra.uname = extra.gname = ""
            extra.mtime = 0
            archive.addfile(extra, io.BytesIO(b""))
    attacked_archive = stream.getvalue()
    transport = authority.build_transport_manifest_v42r1(
        source_manifest=source,
        transport_facts=expected,
        source_archive_sha256=hashlib.sha256(attacked_archive).hexdigest(),
        source_archive_byte_count=len(attacked_archive),
        remote_bootstrap_pyz_artifact=original_transport[
            "remote_bootstrap_pyz_artifact"
        ],
    )
    target = tmp_path / f"target-{attack}"
    with pytest.raises(bootstrap.V42RemoteOrdinal2BootstrapError):
        bootstrap.materialize_capsule_v42r1(
            archive_raw=attacked_archive,
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=target,
            require_fixed_target=False,
        )
    assert not target.exists()


def test_materializer_rejects_redirected_target_parent(tmp_path: Path) -> None:
    archive_raw, source, transport = _capsule_fixture()
    real = tmp_path / "real"
    real.mkdir()
    redirected = tmp_path / "redirected"
    redirected.symlink_to(real)
    with pytest.raises(
        bootstrap.V42RemoteOrdinal2BootstrapError,
        match="redirected",
    ):
        bootstrap.materialize_capsule_v42r1(
            archive_raw=archive_raw,
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=redirected / "source",
            require_fixed_target=False,
        )


def test_committed_capsule_builder_is_deterministic_and_uses_full_transport_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    for index, relative in enumerate(_all_fixture_source_paths()):
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# committed root {index}\n", encoding="utf-8")
    (repository / "TRANSPORT_ONLY.txt").write_text("full tree\n", encoding="utf-8")
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
    _git(repository, "add", ".")
    _git(repository, "commit", "-q", "-m", "capsule fixture")
    commit = _git(repository, "rev-parse", "HEAD")
    monkeypatch.setattr(
        authority,
        "verify_predecessor_retention_ready_v42r1",
        lambda root: {"fixture": str(root)},
    )
    monkeypatch.setattr(
        bootstrap,
        "_verify_live_build_tcb_matches_commit_v42r1",
        lambda *args, **kwargs: _live_bootstrap_constants(),
    )
    first_root = tmp_path / "capsule-one"
    second_root = tmp_path / "capsule-two"
    first_source, first_transport = bootstrap.build_capsule_from_commit_v42r1(
        repository, source_commit=commit, capsule_root=first_root
    )
    second_source, second_transport = bootstrap.build_capsule_from_commit_v42r1(
        repository, source_commit=commit, capsule_root=second_root
    )
    assert first_source == second_source
    assert first_transport == second_transport
    for name in (
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        authority.SOURCE_CAPSULE_NAME,
        authority.SOURCE_MANIFEST_NAME,
        authority.TRANSPORT_MANIFEST_NAME,
        authority.REMOTE_BOOTSTRAP_PYZ_NAME,
    ):
        assert (first_root / name).read_bytes() == (second_root / name).read_bytes()
    local_attempt = authority.verify_local_materialization_attempt_v42r1(
        (first_root / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME).read_bytes(),
        source_manifest=first_source,
        transport_manifest=first_transport,
    )
    assert (
        local_attempt["published_before_any_fixed_identity_transport_effect"]
        is True
    )
    assert local_attempt["fixed_identity_transport_effect_started"] is False
    assert local_attempt[
        "same_fixed_identity_transport_retry_forbidden_after_publication"
    ] is True
    assert "TRANSPORT_ONLY.txt" not in {
        row["relative_path"] for row in first_source["source_facts"]
    }
    assert "TRANSPORT_ONLY.txt" in {
        row["relative_path"] for row in first_transport["transport_facts"]
    }


def test_hermetic_git_ignores_hostile_environment_and_uses_fixed_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        observed.update({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 0, stdout=b"ok\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("PATH", "/attacker/bin")
    monkeypatch.setenv("GIT_DIR", "/attacker/repository")
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "/attacker/objects")
    completed = bootstrap._run_hermetic_git_v42r1(  # noqa: SLF001
        Path("/tmp"), "rev-parse", "HEAD"
    )
    assert completed.stdout == b"ok\n"
    assert observed["command"][:2] == (
        bootstrap.GIT_EXECUTABLE,
        "--no-replace-objects",
    )
    assert observed["env"] == bootstrap._HERMETIC_GIT_ENV  # noqa: SLF001
    assert "PATH" not in observed["env"]  # type: ignore[operator]
    assert "GIT_DIR" not in observed["env"]  # type: ignore[operator]
    assert "GIT_OBJECT_DIRECTORY" not in observed["env"]  # type: ignore[operator]


@pytest.mark.parametrize("attack", ["bytes", "version"])
def test_fixed_git_byte_or_version_drift_is_rejected(
    monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    fixture_raw = b"fixture fixed git bytes"
    monkeypatch.setattr(
        bootstrap, "GIT_EXECUTABLE_BYTE_COUNT", len(fixture_raw)
    )
    monkeypatch.setattr(
        bootstrap,
        "GIT_EXECUTABLE_SHA256",
        (
            "0" * 64
            if attack == "bytes"
            else hashlib.sha256(fixture_raw).hexdigest()
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "_read_regular_nofollow_capped",
        lambda path, maximum: fixture_raw,
    )
    monkeypatch.setattr(
        bootstrap,
        "_run_hermetic_git_v42r1",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, stdout=b"git version ATTACK\n", stderr=b""
        ),
    )
    with pytest.raises(
        bootstrap.V42RemoteOrdinal2BootstrapError,
        match="bytes changed" if attack == "bytes" else "version changed",
    ):
        bootstrap._verify_fixed_git_executable_v42r1()  # noqa: SLF001


def test_local_build_gates_fixed_git_and_common_dir_before_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    monkeypatch.setattr(
        bootstrap,
        "_require_isolated_local_build_runtime_v42r1",
        lambda: events.append("isolated-python"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_verify_fixed_git_executable_v42r1",
        lambda: events.append("fixed-git") or (1,),
    )
    monkeypatch.setattr(
        bootstrap,
        "_verify_git_common_directory_v42r1",
        lambda root: events.append("common-dir") or (2,),
    )
    monkeypatch.setattr(
        authority,
        "verify_predecessor_retention_ready_v42r1",
        lambda root: events.append("predecessor") or {},
    )

    def stop_at_head(root: Path, *arguments: str, **kwargs: object) -> bytes:
        del root, kwargs
        events.append("git:" + " ".join(arguments))
        raise RuntimeError("fixture stop after gate ordering")

    monkeypatch.setattr(bootstrap, "_git", stop_at_head)
    with pytest.raises(RuntimeError, match="fixture stop"):
        bootstrap._build_local()  # noqa: SLF001
    assert events == [
        "isolated-python",
        "fixed-git",
        "common-dir",
        "predecessor",
        "git:rev-parse --verify HEAD^{commit}",
    ]


def test_git_common_directory_redirect_is_rejected_before_capsule_effect(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / ".git/commondir").write_text("../foreign-common\n", encoding="ascii")
    capsule_root = tmp_path / "must-stay-absent"
    with pytest.raises(
        bootstrap.V42RemoteOrdinal2BootstrapError,
        match="common-directory redirect",
    ):
        bootstrap._verify_git_common_directory_v42r1(repository)  # noqa: SLF001
    assert not capsule_root.exists()


@pytest.mark.parametrize(
    "raw",
    [
        b"100644 b\0" + b"b" * 20 + b"100644 a\0" + b"a" * 20,
        b"100644 bad\x01name\0" + b"a" * 20,
        b"100644 bad\xffname\0" + b"a" * 20,
        b"120000 symlink\0" + b"a" * 20,
        b"100644 truncated\0" + b"a" * 19,
    ],
)
def test_raw_git_tree_parser_rejects_noncanonical_or_unsafe_records(
    raw: bytes,
) -> None:
    with pytest.raises(bootstrap.V42RemoteOrdinal2BootstrapError):
        bootstrap._parse_raw_git_tree_v42r1(raw)  # noqa: SLF001


def test_recursive_git_tree_rehash_rejects_claimed_child_oid_with_other_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_commit = "1" * 40
    source_tree = "2" * 40
    claimed_child = "3" * 40
    root_raw = b"40000 child\0" + bytes.fromhex(claimed_child)
    wrong_child_raw = b"100644 member.py\0" + b"4" * 20

    def fake_git(root: Path, *arguments: str, **kwargs: object) -> bytes:
        del root, kwargs
        if arguments == ("rev-parse", "--verify", f"{source_commit}^{{commit}}"):
            return (source_commit + "\n").encode("ascii")
        if arguments == ("rev-parse", f"{source_commit}^{{tree}}"):
            return (source_tree + "\n").encode("ascii")
        if arguments == ("cat-file", "tree", source_tree):
            return root_raw
        if arguments == ("cat-file", "tree", claimed_child):
            return wrong_child_raw
        raise AssertionError(arguments)

    monkeypatch.setattr(bootstrap, "_git", fake_git)
    with pytest.raises(
        bootstrap.V42RemoteOrdinal2BootstrapError,
        match="child Git tree bytes changed object identity",
    ):
        bootstrap._committed_inventory(Path("/unused"), source_commit)  # noqa: SLF001


def test_actual_head_tmp_path_inventory_roundtrips_without_wholesale_pruning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.run(
        ("git", "ls-tree", "-r", "-z", "--name-only", "HEAD", "--", ".tmp"),
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    actual_tmp_paths = tuple(
        raw.decode("utf-8") for raw in completed.stdout.split(b"\0") if raw
    )
    # Bind this regression to the retained predecessor tree that exposed the
    # bug, while using tiny per-path fixture bytes so the test does not copy
    # roughly 470 MiB of historical evidence on every run.
    assert len(actual_tmp_paths) == 540
    assert all(relative.startswith(".tmp/") for relative in actual_tmp_paths)
    reserved_prefixes = (
        authority.AUTHORITY_ROOT_RELATIVE,
        authority.EVIDENCE_ROOT_RELATIVE,
    )
    assert not any(
        relative == reserved
        or relative.startswith(reserved + "/")
        for relative in actual_tmp_paths
        for reserved in reserved_prefixes
    )

    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-actual-tmp-repository-", dir="/tmp"
    ) as base:
        base_path = Path(base)
        repository = base_path / "repository"
        repository.mkdir()
        for index, relative in enumerate(_all_fixture_source_paths()):
            path = repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# committed execution root {index}\n", encoding="utf-8")
        for index, relative in enumerate(actual_tmp_paths):
            path = repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"actual HEAD path fixture {index}: {relative}\n".encode())
        _git(repository, "init", "-q")
        _git(repository, "config", "user.email", "fixture@example.invalid")
        _git(repository, "config", "user.name", "Fixture")
        _git(repository, "add", ".")
        _git(repository, "commit", "-q", "-m", "actual HEAD tmp path fixture")
        commit = _git(repository, "rev-parse", "HEAD")
        monkeypatch.setattr(
            authority,
            "verify_predecessor_retention_ready_v42r1",
            lambda root: {"fixture": str(root)},
        )
        monkeypatch.setattr(
            bootstrap,
            "_verify_live_build_tcb_matches_commit_v42r1",
            lambda *args, **kwargs: _live_bootstrap_constants(),
        )
        capsule_root = base_path / "capsule"
        source, transport = bootstrap.build_capsule_from_commit_v42r1(
            repository, source_commit=commit, capsule_root=capsule_root
        )
        manifested_tmp_paths = {
            row["relative_path"]
            for row in transport["transport_facts"]
            if row["relative_path"].startswith(".tmp/")
        }
        assert manifested_tmp_paths == set(actual_tmp_paths)

        _assert_actual_tmp_materialization(
            capsule_root, source, transport, actual_tmp_paths
        )


def test_formal_materialization_attempt_precedes_effect_and_failure_is_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-materialize-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        archive_raw, source, transport = _capsule_fixture()
        _install_formal_controls(remote_root, archive_raw, source, transport)

        class InjectedExtractionFailure(RuntimeError):
            pass

        monkeypatch.setattr(
            bootstrap,
            "materialize_capsule_v42r1",
            lambda **kwargs: (_ for _ in ()).throw(InjectedExtractionFailure("fixture")),
        )
        with pytest.raises(InjectedExtractionFailure):
            bootstrap.materialize_fixed_remote_capsule_once_v42r1(
                remote_root=remote_root,
                source_root=source_root,
                require_fixed_paths=True,
            )
        assert (remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME).is_file()
        failure_raw = (
            remote_root / authority.MATERIALIZATION_FAILURE_NAME
        ).read_bytes()
        local_attempt = authority.verify_local_materialization_attempt_v42r1(
            (remote_root / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME).read_bytes(),
            source_manifest=source,
            transport_manifest=transport,
        )
        remote_attempt = authority.verify_remote_materialization_attempt_v42r1(
            (remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME).read_bytes(),
            local_materialization_attempt=local_attempt,
            source_manifest=source,
            transport_manifest=transport,
        )
        failure = authority.verify_materialization_failure_v42r1(
            failure_raw,
            local_materialization_attempt=local_attempt,
            remote_materialization_attempt=remote_attempt,
            source_manifest=source,
            transport_manifest=transport,
        )
        assert failure["failure_stage"] == "STAGING_EXTRACTION"
        assert failure["retry_authorized"] is False
        assert not source_root.exists()
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "COMPLETE_FAILURE"
        assert classification["remote_path_mutated_by_classifier"] is False
        with pytest.raises(Exception, match="extra|prior-attempt|retry|binding is absent"):
            bootstrap.materialize_fixed_remote_capsule_once_v42r1(
                remote_root=remote_root,
                source_root=source_root,
                require_fixed_paths=True,
            )


def test_remote_attempt_is_first_materialization_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-first-effect-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        archive_raw, source, transport = _capsule_fixture()
        _install_formal_controls(remote_root, archive_raw, source, transport)
        writes: list[Path] = []

        class StopAtFirstWrite(RuntimeError):
            pass

        def stop(path: Path, raw: bytes, **kwargs: object) -> None:
            del raw, kwargs
            writes.append(path)
            raise StopAtFirstWrite

        monkeypatch.setattr(bootstrap.processio, "write_once", stop)
        with pytest.raises(StopAtFirstWrite):
            bootstrap.materialize_fixed_remote_capsule_once_v42r1(
                remote_root=remote_root,
                source_root=source_root,
                require_fixed_paths=True,
            )
        assert writes == [remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME]
        assert not source_root.exists()


def test_atomic_noreplace_publish_carries_embedded_terminal_and_classifier_is_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-atomic-publish-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        archive_raw, source, transport = _capsule_fixture()
        local_attempt = _install_formal_controls(
            remote_root, archive_raw, source, transport
        )
        original_rename = bootstrap.processio.rename_noreplace
        rename_observations: list[tuple[str, str]] = []

        def observed_rename(parent: Path, old_name: str, new_name: str) -> None:
            assert parent == remote_root
            assert not (parent / new_name).exists()
            assert (
                parent / old_name / authority.MATERIALIZATION_TERMINAL_NAME
            ).is_file()
            rename_observations.append((old_name, new_name))
            original_rename(parent, old_name, new_name)

        monkeypatch.setattr(bootstrap.processio, "rename_noreplace", observed_rename)
        terminal = bootstrap.materialize_fixed_remote_capsule_once_v42r1(
            remote_root=remote_root,
            source_root=source_root,
            require_fixed_paths=True,
        )
        assert rename_observations == [
            (
                authority.materialization_staging_name_v42r1(
                    local_attempt["local_materialization_attempt_id"]
                ),
                "source",
            )
        ]
        assert (
            source_root / authority.MATERIALIZATION_TERMINAL_NAME
        ).read_bytes() == canonical_json_bytes(terminal)
        phase = authority.verify_remote_control_phase_inventory_v42r1(
            "POST_MATERIALIZATION_PREPARE"
        )
        assert phase["source_manifest"] == source
        assert phase["transport_manifest"] == transport
        assert phase["materialization_terminal_id"] == terminal[
            "materialization_terminal_id"
        ]
        assert authority.MATERIALIZATION_TERMINAL_NAME not in {
            row["relative_path"] for row in source["source_facts"]
        }
        assert authority.MATERIALIZATION_TERMINAL_NAME not in {
            row["relative_path"] for row in transport["transport_facts"]
        }
        before = _tree_snapshot(remote_root)
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "COMPLETE_SUCCESS"
        assert classification["same_identity_transport_or_materialization_retry_authorized"] is False
        assert _tree_snapshot(remote_root) == before
        with monkeypatch.context() as no_resolve:
            no_resolve.setattr(
                Path,
                "resolve",
                lambda *args, **kwargs: (_ for _ in ()).throw(
                    AssertionError("successful classifier escaped its pinned descriptor")
                ),
            )
            pinned_classification = (
                bootstrap.classify_materialization_read_only_v42r1(
                    remote_root=remote_root,
                    expected_local_attempt_raw=canonical_json_bytes(local_attempt),
                    expected_archive_raw=archive_raw,
                    expected_source_manifest_raw=canonical_json_bytes(source),
                    expected_transport_manifest_raw=canonical_json_bytes(transport),
                    require_fixed_paths=True,
                )
            )
        assert pinned_classification["classification"] == "COMPLETE_SUCCESS"
        for attacked_path, attacked_mode, restored_mode in (
            (remote_root / authority.SOURCE_MANIFEST_NAME, 0o644, 0o400),
            (
                source_root / authority.MATERIALIZATION_TERMINAL_NAME,
                0o644,
                0o400,
            ),
            (source_root, 0o755, 0o700),
        ):
            attacked_path.chmod(attacked_mode)
            attacked_before = _tree_snapshot(remote_root)
            attacked_classification = (
                bootstrap.classify_materialization_read_only_v42r1(
                    remote_root=remote_root,
                    expected_local_attempt_raw=canonical_json_bytes(local_attempt),
                    expected_archive_raw=archive_raw,
                    expected_source_manifest_raw=canonical_json_bytes(source),
                    expected_transport_manifest_raw=canonical_json_bytes(transport),
                    require_fixed_paths=True,
                )
            )
            assert attacked_classification["classification"] == (
                "AMBIGUOUS_PERMANENTLY_CLOSED"
            )
            assert _tree_snapshot(remote_root) == attacked_before
            attacked_path.chmod(restored_mode)
        extra = remote_root / "UNRECOGNIZED"
        bootstrap._write_once(extra, b"unexpected")  # noqa: SLF001
        changed_before = _tree_snapshot(remote_root)
        changed = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert changed["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert changed["extra_remote_entry_names"] == ["UNRECOGNIZED"]
        assert _tree_snapshot(remote_root) == changed_before
        with pytest.raises(Exception, match="extra|prior-attempt|retry|binding is absent"):
            bootstrap.materialize_fixed_remote_capsule_once_v42r1(
                remote_root=remote_root,
                source_root=source_root,
                require_fixed_paths=True,
            )


def test_ambiguous_partial_transport_is_permanently_closed_and_not_mutated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-partial-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        remote_root.mkdir(mode=0o700)
        remote_root.chmod(0o700)
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        archive_raw, source, transport = _capsule_fixture()
        local_attempt = authority.build_local_materialization_attempt_v42r1(
            source_manifest=source,
            transport_manifest=transport,
        )
        bootstrap._write_once(  # noqa: SLF001
            remote_root / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            canonical_json_bytes(local_attempt),
        )
        before = _tree_snapshot(remote_root)
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["same_identity_transport_or_materialization_retry_authorized"] is False
        assert set(classification["changed_or_absent_remote_control_names"]) == {
            authority.SOURCE_CAPSULE_NAME,
            authority.SOURCE_MANIFEST_NAME,
            authority.TRANSPORT_MANIFEST_NAME,
            authority.REMOTE_BOOTSTRAP_PYZ_NAME,
        }
        assert _tree_snapshot(remote_root) == before


def test_classifier_types_symlinked_remote_attempt_as_ambiguous_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-attempt-symlink-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        archive_raw, source, transport = _capsule_fixture()
        local_attempt = _install_formal_controls(
            remote_root, archive_raw, source, transport
        )
        outside = Path(base) / "outside"
        outside.write_bytes(b"not an attempt")
        (remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME).symlink_to(
            outside
        )
        before = _tree_snapshot(remote_root)
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["classification_reason"] == (
            "REMOTE_ATTEMPT_INVALID_OR_UNREADABLE"
        )
        assert _tree_snapshot(remote_root) == before


def test_preexisting_source_is_never_overwritten_or_attempted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-preexisting-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        archive_raw, source, transport = _capsule_fixture()
        _install_formal_controls(remote_root, archive_raw, source, transport)
        source_root.mkdir()
        sentinel = source_root / "sentinel"
        sentinel.write_bytes(b"never overwrite")
        before = _tree_snapshot(remote_root)
        with pytest.raises(Exception, match="extra|prior-attempt|retry|binding is absent"):
            bootstrap.materialize_fixed_remote_capsule_once_v42r1(
                remote_root=remote_root,
                source_root=source_root,
                require_fixed_paths=True,
            )
        assert _tree_snapshot(remote_root) == before
        assert not (
            remote_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME
        ).exists()


def test_atomic_publish_race_uses_noreplace_and_preserves_competing_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-noreplace-race-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        archive_raw, source, transport = _capsule_fixture()
        local_attempt = _install_formal_controls(
            remote_root, archive_raw, source, transport
        )
        original_rename = bootstrap.processio.rename_noreplace

        def race(parent: Path, old_name: str, new_name: str) -> None:
            competing = parent / new_name
            competing.mkdir()
            (competing / "sentinel").write_bytes(b"competing target")
            original_rename(parent, old_name, new_name)

        monkeypatch.setattr(bootstrap.processio, "rename_noreplace", race)
        with pytest.raises(OSError):
            bootstrap.materialize_fixed_remote_capsule_once_v42r1(
                remote_root=remote_root,
                source_root=source_root,
                require_fixed_paths=True,
            )
        assert (source_root / "sentinel").read_bytes() == b"competing target"
        assert not (remote_root / authority.MATERIALIZATION_FAILURE_NAME).exists()
        staging = remote_root / authority.materialization_staging_name_v42r1(
            local_attempt["local_materialization_attempt_id"]
        )
        assert (staging / authority.MATERIALIZATION_TERMINAL_NAME).is_file()
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["same_identity_transport_or_materialization_retry_authorized"] is False


@pytest.mark.parametrize("attack", ["delete_recreate", "in_place_mutate"])
def test_live_transport_inventory_rejects_cross_scan_nested_file_splice(
    monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-tree-race-", dir="/tmp") as base:
        target = Path(base) / "materialized"
        bootstrap.materialize_capsule_v42r1(
            archive_raw=archive_raw,
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=target,
            require_fixed_target=False,
        )
        attacked = (
            target / ".tmp/exact-freeze/v41-committed-transport-fixture.json"
        )
        trigger = target / "TRANSPORT_ONLY.txt"
        original_read = authority._read_regular_nofollow_stable  # noqa: SLF001
        injected = False

        def read_then_attack(
            path: Path, maximum: int = 1024 * 1024 * 1024,
        ) -> tuple[bytes, os.stat_result]:
            nonlocal injected
            raw, observed = original_read(path, maximum)
            if path == trigger and not injected:
                retained = attacked.read_bytes()
                if attack == "delete_recreate":
                    attacked.unlink()
                    attacked.write_bytes(retained)
                    attacked.chmod(0o444)
                else:
                    attacked.chmod(0o644)
                    changed = bytearray(retained)
                    changed[0] ^= 1
                    attacked.write_bytes(bytes(changed))
                    attacked.chmod(0o444)
                injected = True
            return raw, observed

        monkeypatch.setattr(
            authority, "_read_regular_nofollow_stable", read_then_attack
        )
        with pytest.raises(
            authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
            match="changed across full inventory",
        ):
            authority.verify_live_transport_inventory_v42r1(
                target, transport, source, require_fixed_root=False
            )


def test_materialization_classifier_types_absent_fixed_root_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-root-absent-", dir="/tmp") as base:
        remote_root = Path(base) / "remote-absent"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", remote_root / "source")
        local_attempt = authority.build_local_materialization_attempt_v42r1(
            source_manifest=source,
            transport_manifest=transport,
        )
        parent_before = _tree_snapshot(Path(base))
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["remote_root_state"] == "ABSENT"
        assert classification["classification_reason"] == (
            "FIXED_REMOTE_ROOT_ABSENT_AFTER_LOCAL_MATERIALIZATION_ATTEMPT"
        )
        assert classification[
            "same_identity_transport_or_materialization_retry_authorized"
        ] is False
        assert _tree_snapshot(Path(base)) == parent_before
        assert not remote_root.exists()


@pytest.mark.parametrize(
    ("attack", "expected_state"),
    [
        ("symlink", "SYMLINK"),
        ("regular", "REGULAR_FILE"),
        ("nonregular", "NONREGULAR"),
        ("mode", "DIRECTORY_UNSAFE_MODE"),
        ("uid", "DIRECTORY_UNEXPECTED_UID"),
    ],
)
def test_materialization_classifier_types_unsafe_fixed_root_without_following(
    monkeypatch: pytest.MonkeyPatch, attack: str, expected_state: str,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-root-unsafe-", dir="/tmp") as base:
        base_path = Path(base)
        remote_root = base_path / "remote"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", remote_root / "source")
        if attack == "uid":
            monkeypatch.setattr(authority, "REMOTE_UID", os.geteuid() + 1)
        local_attempt = authority.build_local_materialization_attempt_v42r1(
            source_manifest=source,
            transport_manifest=transport,
        )
        if attack == "symlink":
            target = base_path / "symlink-target"
            target.mkdir(mode=0o700)
            remote_root.symlink_to(target, target_is_directory=True)
        elif attack == "regular":
            remote_root.write_bytes(b"not a directory\n")
        elif attack == "nonregular":
            os.mkfifo(remote_root, 0o600)
        else:
            remote_root.mkdir(mode=0o700)
            if attack == "mode":
                remote_root.chmod(0o777)
        before = _tree_snapshot(base_path)
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["remote_root_state"] == expected_state
        assert classification[
            "same_identity_transport_or_materialization_retry_authorized"
        ] is False
        assert _tree_snapshot(base_path) == before


def test_materialization_classifier_rejects_symlinked_ancestor_without_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-root-ancestor-", dir="/tmp") as base:
        base_path = Path(base)
        real_parent = base_path / "real-parent"
        real_parent.mkdir(mode=0o700)
        (real_parent / "remote").mkdir(mode=0o700)
        linked_parent = base_path / "linked-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        remote_root = linked_parent / "remote"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", remote_root / "source")
        local_attempt = authority.build_local_materialization_attempt_v42r1(
            source_manifest=source,
            transport_manifest=transport,
        )
        monkeypatch.setattr(
            Path,
            "resolve",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("classifier followed a lexical ancestor")
            ),
        )
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["remote_root_state"] == "REDIRECTED_ANCESTOR"


def test_materialization_classification_schema_and_content_id_are_exact() -> None:
    document = bootstrap._materialization_classification_document(  # noqa: SLF001
        local_materialization_attempt_id="1" * 64,
        remote_materialization_attempt_id=None,
        materialization_terminal_id=None,
        materialization_failure_id=None,
        classification="AMBIGUOUS_PERMANENTLY_CLOSED",
        classification_reason="FIXTURE",
        changed_or_absent_remote_control_names=["A"],
        extra_remote_entry_names=["B"],
        remote_root_state="SYMLINK",
    )
    assert set(document) == {
        "schema", "schema_version", "formal_identity", "global_execution_ordinal",
        "local_materialization_attempt_id", "remote_materialization_attempt_id",
        "materialization_terminal_id", "materialization_failure_id",
        "classification", "classification_reason",
        "changed_or_absent_remote_control_names", "extra_remote_entry_names",
        "remote_root_state", "remote_path_mutated_by_classifier",
        "process_started_by_classifier",
        "same_identity_transport_or_materialization_retry_authorized",
        "only_read_only_followup_allowed", "materialization_classification_id",
    }
    payload = {
        key: value
        for key, value in document.items()
        if key != "materialization_classification_id"
    }
    assert document["materialization_classification_id"] == hashlib.sha256(
        b"acfqp:v42-remote-ordinal2:materialization-classification\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


def test_classifier_observation_race_is_typed_and_closes_pinned_fd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-root-race-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", remote_root / "source")
        local_attempt = _install_formal_controls(
            remote_root, archive_raw, source, transport
        )
        attacked = remote_root / authority.SOURCE_MANIFEST_NAME
        original_read = bootstrap._read_regular_nofollow_capped  # noqa: SLF001
        injected = False

        def read_then_delete(path: Path, maximum: int) -> bytes:
            nonlocal injected
            raw = original_read(path, maximum)
            if path.name == attacked.name and not injected:
                attacked.unlink()
                injected = True
            return raw

        monkeypatch.setattr(
            bootstrap, "_read_regular_nofollow_capped", read_then_delete
        )
        descriptor_count_before = len(os.listdir("/proc/self/fd"))
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        descriptor_count_after = len(os.listdir("/proc/self/fd"))
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["classification_reason"] == (
            "REMOTE_OBSERVATION_RACE_OR_IO_FAILURE_DURING_CLASSIFICATION"
        )
        assert descriptor_count_after == descriptor_count_before


def test_classifier_rejects_ancestor_mode_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-ancestor-mode-", dir="/tmp") as base:
        base_path = Path(base)
        remote_root = base_path / "remote"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", remote_root / "source")
        local_attempt = _install_formal_controls(
            remote_root, archive_raw, source, transport
        )
        original_snapshot = authority._snapshot_transport_tree_metadata_v42r1  # noqa: SLF001
        injected = False

        def snapshot_then_chmod(root: Path) -> dict[str, tuple[int, ...]]:
            nonlocal injected
            snapshot = original_snapshot(root)
            if not injected:
                base_path.chmod(0o755)
                injected = True
            return snapshot

        monkeypatch.setattr(
            authority,
            "_snapshot_transport_tree_metadata_v42r1",
            snapshot_then_chmod,
        )
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["classification_reason"] == (
            "REMOTE_ROOT_OR_ANCESTOR_CHANGED_DURING_CLASSIFICATION"
        )


def test_pinned_classifier_handles_mutable_root_without_resolve_and_rejects_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-mutable-pinned-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        local_attempt = _install_formal_controls(
            remote_root, archive_raw, source, transport
        )
        bootstrap.materialize_fixed_remote_capsule_once_v42r1(
            remote_root=remote_root,
            source_root=source_root,
            require_fixed_paths=True,
        )
        mutable_root = source_root / authority.AUTHORITY_ROOT_RELATIVE
        mutable_root.mkdir(mode=0o700)
        mutable_root.chmod(0o700)
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "COMPLETE_SUCCESS"

        mutable_root.rmdir()
        outside = Path(base) / "outside-mutable"
        outside.mkdir(mode=0o700)
        mutable_root.symlink_to(outside, target_is_directory=True)
        attacked = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert attacked["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"


def test_nested_materialization_directory_links_are_parent_fsynced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_raw, source, transport = _capsule_fixture()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-fsync-chain-", dir="/tmp") as base:
        target = Path(base) / "materialized"
        original_fsync = bootstrap.os.fsync
        fsynced_paths: list[Path] = []

        def observed_fsync(descriptor: int) -> None:
            try:
                fsynced_paths.append(
                    Path(os.readlink(f"/proc/self/fd/{descriptor}"))
                )
            except OSError:
                pass
            original_fsync(descriptor)

        monkeypatch.setattr(bootstrap.os, "fsync", observed_fsync)
        bootstrap.materialize_capsule_v42r1(
            archive_raw=archive_raw,
            source_manifest_raw=canonical_json_bytes(source),
            transport_manifest_raw=canonical_json_bytes(transport),
            target_root=target,
            require_fixed_target=False,
        )
        assert target in fsynced_paths
        assert target / ".tmp" in fsynced_paths
        assert target / ".tmp/exact-freeze" in fsynced_paths


def test_classifier_closes_transport_to_source_cross_verifier_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-cross-verifier-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        archive_raw, source, transport = _capsule_fixture()
        local_attempt = _install_formal_controls(
            remote_root, archive_raw, source, transport
        )
        bootstrap.materialize_fixed_remote_capsule_once_v42r1(
            remote_root=remote_root,
            source_root=source_root,
            require_fixed_paths=True,
        )
        attacked = (
            source_root
            / ".tmp/exact-freeze/v41-committed-transport-fixture.json"
        )
        original_source_verifier = authority.verify_live_source_matches_manifest_v42
        injected = False

        def mutate_between_verifiers(
            root: Path, manifest: dict[str, object], *, require_fixed_root: bool = True,
            pinned_root_descriptor: int | None = None,
        ) -> None:
            nonlocal injected
            if not injected:
                retained = attacked.read_bytes()
                attacked.unlink()
                attacked.write_bytes(retained)
                attacked.chmod(0o444)
                injected = True
            original_source_verifier(
                root,
                manifest,
                require_fixed_root=require_fixed_root,
                pinned_root_descriptor=pinned_root_descriptor,
            )

        monkeypatch.setattr(
            authority,
            "verify_live_source_matches_manifest_v42",
            mutate_between_verifiers,
        )
        classification = bootstrap.classify_materialization_read_only_v42r1(
            remote_root=remote_root,
            expected_local_attempt_raw=canonical_json_bytes(local_attempt),
            expected_archive_raw=archive_raw,
            expected_source_manifest_raw=canonical_json_bytes(source),
            expected_transport_manifest_raw=canonical_json_bytes(transport),
            require_fixed_paths=True,
        )
        assert classification["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
        assert classification["classification_reason"] == (
            "REMOTE_TREE_CHANGED_DURING_READ_ONLY_CLASSIFICATION"
        )
