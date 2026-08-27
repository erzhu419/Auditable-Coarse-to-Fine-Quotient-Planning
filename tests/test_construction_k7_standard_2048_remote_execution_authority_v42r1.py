from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import tempfile

import pytest

from acfqp import construction_k7_standard_2048_remote_execution_authority_v42r1 as authority


ROOT = Path(__file__).resolve().parents[1]


def test_authority_publication_inode_is_0400_before_first_fchmod(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-authority-umask-", dir="/tmp") as base:
        target = Path(base) / "AUTHORITY_CONSUMPTION.json"
        original_fchmod = os.fchmod
        interrupted = False

        def interrupt_first_fchmod(descriptor: int, mode: int) -> None:
            nonlocal interrupted
            if os.readlink(f"/proc/self/fd/{descriptor}") == str(target) and not interrupted:
                interrupted = True
                raise KeyboardInterrupt("fixture authority publication birth")
            original_fchmod(descriptor, mode)

        prior_umask = os.umask(0o777)
        try:
            with monkeypatch.context() as interrupted_call:
                interrupted_call.setattr(os, "fchmod", interrupt_first_fchmod)
                with pytest.raises(KeyboardInterrupt, match="authority publication"):
                    authority._write_once(target, b"authority bytes")  # noqa: SLF001
            observed_umask = os.umask(0o777)
            assert observed_umask == 0o777
            assert target.lstat().st_mode & 0o777 == 0o400
        finally:
            os.umask(prior_umask)
        assert interrupted is True


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - Git object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def _host_attestation(**changes: object) -> dict[str, object]:
    scope = "/user.slice/user-1000.slice/session-353701.scope"
    ancestry = [
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
    ]
    arguments: dict[str, object] = {
        "transport_target_alias": authority.REMOTE_HOST_ALIAS,
        "observed_hostname": authority.REMOTE_HOSTNAME,
        "observed_user": authority.REMOTE_USER,
        "observed_uid": authority.REMOTE_UID,
        "observed_python_invocation": authority.REMOTE_PYTHON,
        "observed_python_realpath": authority.REMOTE_PYTHON_REALPATH,
        "observed_python_version": authority.REMOTE_PYTHON_VERSION,
        "observed_source_root": str(authority.REMOTE_SOURCE_ROOT),
        "memory_total_bytes": 540_433_203_200,
        "memory_available_bytes": 531_989_004_288,
        "swap_total_bytes": 8_589_930_496,
        "swap_free_bytes": 8_589_930_496,
        "cgroup_mount_filesystem_type": "cgroup2",
        "cgroup_mount_root": "/",
        "cgroup_unified_scope_path": scope,
        "cgroup_root_controllers": ["cpu", "cpuset", "io", "memory", "pids"],
        "cgroup_memory_ancestry": ancestry,
        "filesystem_available_bytes": 64 * 1024**3,
        "attestation_stage": "PREPARE",
    }
    arguments.update(changes)
    return authority.build_host_attestation_v42r1(**arguments)  # type: ignore[arg-type]


def _remote_bootstrap_pyz_artifact(
    source_facts: list[dict[str, object]],
) -> dict[str, object]:
    by_path = {str(row["relative_path"]): row for row in source_facts}
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
            fact = by_path[str(source_relative)]
            raw = f"# fixture {sorted(by_path).index(str(source_relative))}\n".encode(
                "ascii"
            )
            assert len(raw) == fact["byte_count"]
            assert hashlib.sha256(raw).hexdigest() == fact["sha256"]
            blob = fact["git_blob_oid"]
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
        pyz_sha256="a" * 64,
        pyz_byte_count=65_537,
    )


def _source_and_transport_manifests() -> tuple[dict[str, object], dict[str, object]]:
    source_facts = []
    source_paths = set(authority.FORMAL_REMOTE_SOURCE_ROOTS) | {
        str(source_relative)
        for _archive, _module, member_kind, source_relative in (
            authority.REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS
        )
        if member_kind == "COMMITTED_GIT_BLOB"
    }
    for index, relative in enumerate(sorted(source_paths)):
        raw = f"# fixture {index}\n".encode("ascii")
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
    readme = b"transport-only fixture\n"
    transport_facts = sorted(
        [
            *source_facts,
            {
                "relative_path": "README.md",
                "git_mode": "100644",
                "git_object_type": "blob",
                "git_blob_oid": _git_blob(readme),
                "byte_count": len(readme),
                "sha256": hashlib.sha256(readme).hexdigest(),
            },
        ],
        key=lambda row: row["relative_path"],
    )
    transport = authority.build_transport_manifest_v42r1(
        source_manifest=source,
        transport_facts=transport_facts,
        source_archive_sha256="3" * 64,
        source_archive_byte_count=12_345,
        remote_bootstrap_pyz_artifact=_remote_bootstrap_pyz_artifact(source_facts),
    )
    return source, transport


def test_remote_ordinal2_identity_and_predecessor_failure_chain_are_disjoint() -> None:
    assert authority.FORMAL_IDENTITY.endswith("REMOTE_ORDINAL_2")
    assert authority.GLOBAL_EXECUTION_ORDINAL == 2
    assert authority.FORMAL_IDENTITY != authority.PREDECESSOR_FORMAL_IDENTITY
    assert authority.REMOTE_HOST_ALIAS == "jtl110gpu2"
    assert authority.REMOTE_USER == "erzhu419"
    assert authority.REMOTE_UID == 1000
    assert authority.PREDECESSOR_RETENTION_READY is True
    assert authority.PREDECESSOR_RETENTION_MANIFEST_ID == (
        "5ab73d90b63675fe4255c0bf6cd2116444a52b5b0009cd6cf822f4fbf7b6ce66"
    )
    assert authority.PREDECESSOR_INDEPENDENT_VERIFICATION_ID == (
        "6c088a5515a096ce363c7ab9a834d9ed9c22da87a63d4ed59d1d68e78167db3b"
    )
    assert authority.PREDECESSOR_RUNNER_FAILURE_ID == (
        "c5ab25e29efef47c22d2ccbbaa5867f11b51e9fadaecab321e60fc3dc879d354"
    )
    binding = authority.verify_predecessor_retention_ready_v42r1(ROOT)
    assert binding["predecessor_campaign_absent"] is True
    assert binding["predecessor_scientific_success"] is False
    assert binding["predecessor_same_identity_rerun_forbidden"] is True


def test_transport_inventory_is_broader_than_static_python_execution_closure() -> None:
    source, transport = _source_and_transport_manifests()
    source_paths = {row["relative_path"] for row in source["source_facts"]}
    transport_paths = {row["relative_path"] for row in transport["transport_facts"]}
    assert source["source_scope"] == "COMMITTED_REPOSITORY_PYTHON_SOURCE_ONLY"
    assert transport["transport_scope"] == (
        "ALL_COMMITTED_REGULAR_FILES_IN_DETERMINISTIC_USTAR"
    )
    assert source_paths < transport_paths
    assert "README.md" in transport_paths
    authority.verify_source_manifest_v42r1(source)
    authority.verify_transport_manifest_v42r1(
        transport, source_manifest=source
    )


@pytest.mark.parametrize(
    "relative",
    [
        authority.MATERIALIZATION_TERMINAL_NAME,
        authority.PREPARE_ATTEMPT_JOURNAL_NAME,
        authority.PREPARE_FAILURE_JOURNAL_NAME,
        authority.LAUNCH_ATTEMPT_JOURNAL_NAME,
        authority.LAUNCH_FAILURE_JOURNAL_NAME,
        authority.AUTHORITY_ROOT_RELATIVE,
        authority.AUTHORITY_ROOT_RELATIVE + "/PREPARE_RECEIPT.json",
        authority.EVIDENCE_ROOT_RELATIVE + "/ATTEMPT.json",
    ],
)
def test_transport_manifest_rejects_exact_mutable_state_collisions(
    relative: str,
) -> None:
    source, transport = _source_and_transport_manifests()
    raw = b"reserved collision fixture\n"
    facts = [
        *transport["transport_facts"],
        {
            "relative_path": relative,
            "git_mode": "100644",
            "git_object_type": "blob",
            "git_blob_oid": _git_blob(raw),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    ]
    facts.sort(key=lambda row: row["relative_path"])
    with pytest.raises(
        authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
        match="reserved mutable state",
    ):
        authority.build_transport_manifest_v42r1(
            source_manifest=source,
            transport_facts=facts,
            source_archive_sha256="4" * 64,
            source_archive_byte_count=12_346,
            remote_bootstrap_pyz_artifact=transport[
                "remote_bootstrap_pyz_artifact"
            ],
        )


def test_fixed_host_swap_boundary_is_exact_and_one_byte_less_fails() -> None:
    assert authority.MINIMUM_SWAP_FREE_BYTES == 8 * 1024**3 - 4096
    passed = _host_attestation(
        swap_total_bytes=authority.MINIMUM_SWAP_FREE_BYTES,
        swap_free_bytes=authority.MINIMUM_SWAP_FREE_BYTES,
    )
    assert passed["checks"]["swap_gate"] is True
    authority.verify_host_attestation_v42r1(
        passed, expected_stage="PREPARE", require_pass=True
    )
    failed = _host_attestation(
        swap_total_bytes=authority.MINIMUM_SWAP_FREE_BYTES,
        swap_free_bytes=authority.MINIMUM_SWAP_FREE_BYTES - 1,
    )
    assert failed["checks"]["swap_gate"] is False
    with pytest.raises(
        authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
        match="resource gate",
    ):
        authority.verify_host_attestation_v42r1(
            failed, expected_stage="PREPARE", require_pass=True
        )


def test_finite_cgroup_ancestor_requires_total_and_headroom_boundaries() -> None:
    base = _host_attestation()
    chain = deepcopy(base["cgroup_memory_ancestry"])
    maximum = (
        authority.MINIMUM_MEMORY_TOTAL_BYTES
        + authority.MINIMUM_MEMORY_AVAILABLE_BYTES
    )
    chain[1] = {
        "cgroup_path": "/user.slice/user-1000.slice",
        "memory_max_mode": "FINITE",
        "memory_max_bytes": maximum,
        "memory_current_bytes": maximum
        - authority.MINIMUM_MEMORY_AVAILABLE_BYTES,
    }
    passed = _host_attestation(cgroup_memory_ancestry=chain)
    assert passed["checks"]["cgroup_memory_gate"] is True
    attacked = deepcopy(chain)
    attacked[1]["memory_current_bytes"] += 1
    failed = _host_attestation(cgroup_memory_ancestry=attacked)
    assert failed["checks"]["cgroup_memory_gate"] is False


def _fake_cgroup_tree(tmp_path: Path) -> tuple[Path, Path]:
    proc = tmp_path / "self.cgroup"
    proc.write_bytes(b"0::/user.slice/user-1000.slice/session.scope\n")
    root = tmp_path / "cgroup"
    root.mkdir()
    (root / "cgroup.controllers").write_bytes(b"cpu io memory pids\n")
    current = root
    for part in ("user.slice", "user-1000.slice", "session.scope"):
        current = current / part
        current.mkdir()
        (current / "memory.max").write_bytes(b"max\n")
        (current / "memory.current").write_bytes(b"123456\n")
    return proc, root


def test_cgroup_v2_scope_to_root_chain_accepts_only_exact_root_delegated_absence(
    tmp_path: Path,
) -> None:
    proc, root = _fake_cgroup_tree(tmp_path)
    scope, controllers, chain = authority._read_cgroup_memory_observation(  # noqa: SLF001
        proc_self_cgroup=proc, cgroup_root=root
    )
    assert scope == "/user.slice/user-1000.slice/session.scope"
    assert controllers == ["cpu", "io", "memory", "pids"]
    assert [row["cgroup_path"] for row in chain] == [
        "/user.slice/user-1000.slice/session.scope",
        "/user.slice/user-1000.slice",
        "/user.slice",
        "/",
    ]
    assert chain[-1]["memory_max_mode"] == (
        "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES"
    )

    (root / "user.slice/memory.current").unlink()
    with pytest.raises(
        authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
        match="non-root cgroup omitted|partially present",
    ):
        authority._read_cgroup_memory_observation(  # noqa: SLF001
            proc_self_cgroup=proc, cgroup_root=root
        )


@pytest.mark.parametrize(
    "raw",
    [
        b"0::/safe\n0::/duplicate\n",
        b"0::/safe\n1:name:/legacy\n",
        b"0::/safe/../escape\n",
        b"0::/safe//noncanonical\n",
        b"0::/safe\r\n",
        b"0::/safe\tchild\n",
        b"0::/safe\x7fchild\n",
        b"1:name=/not-unified\n",
        b"0::/" + b"a" * 4093 + b"\n",
    ],
)
def test_cgroup_v2_scope_parser_rejects_ambiguous_or_unsafe_paths(
    tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "self.cgroup"
    path.write_bytes(raw)
    with pytest.raises(
        authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error
    ):
        authority._read_exact_cgroup_scope(path)  # noqa: SLF001


def test_cgroup_v2_ancestry_rejects_symlink_redirect(tmp_path: Path) -> None:
    proc, root = _fake_cgroup_tree(tmp_path)
    target = root / "real-session"
    target.mkdir()
    (target / "memory.max").write_bytes(b"max\n")
    (target / "memory.current").write_bytes(b"1\n")
    redirected = root / "user.slice/user-1000.slice/session.scope"
    for child in redirected.iterdir():
        child.unlink()
    redirected.rmdir()
    redirected.symlink_to(target)
    with pytest.raises(
        authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
        match="redirect",
    ):
        authority._read_cgroup_memory_observation(  # noqa: SLF001
            proc_self_cgroup=proc, cgroup_root=root
        )


def test_cgroup_mountinfo_requires_one_exact_cgroup2_root(tmp_path: Path) -> None:
    mountinfo = tmp_path / "mountinfo"
    exact = b"36 25 0:32 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n"
    mountinfo.write_bytes(exact)
    filesystem, root, raw = authority._read_cgroup2_mount_observation(  # noqa: SLF001
        mountinfo
    )
    assert (filesystem, root, raw) == ("cgroup2", "/", exact)
    mountinfo.write_bytes(exact + exact)
    with pytest.raises(
        authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
        match="ambiguous",
    ):
        authority._read_cgroup2_mount_observation(mountinfo)  # noqa: SLF001
    mountinfo.write_bytes(
        b"36 25 0:32 / /sys/fs/cgroup rw - cgroup cgroup rw\n"
    )
    with pytest.raises(
        authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
        match="not the exact unified",
    ):
        authority._read_cgroup2_mount_observation(mountinfo)  # noqa: SLF001


def test_remote_phase_whole_tree_rejects_nested_same_bytes_new_inode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-phase-tree-", dir="/tmp") as base:
        remote_root = Path(base) / "remote"
        source_root = remote_root / "source"
        remote_root.mkdir(mode=0o700)
        source_root.mkdir(mode=0o700)
        for name in (
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            authority.SOURCE_CAPSULE_NAME,
            authority.SOURCE_MANIFEST_NAME,
            authority.TRANSPORT_MANIFEST_NAME,
            authority.REMOTE_BOOTSTRAP_PYZ_NAME,
            authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
        ):
            path = remote_root / name
            path.write_bytes(b"phase fixture\n")
            path.chmod(0o400)
        nested = source_root / "nested-transport-member.bin"
        nested.write_bytes(b"same retained bytes\n")
        nested.chmod(0o444)
        original_inode = nested.lstat().st_ino

        monkeypatch.setattr(authority, "REMOTE_ROOT", remote_root)
        monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
        monkeypatch.setattr(
            authority,
            "verify_fixed_transport_controls_v42r1",
            lambda: {
                "source_manifest": {"source_manifest_id": "fixture-source"},
                "transport_manifest": {"transport_manifest_id": "fixture-transport"},
            },
        )

        def mutate_after_first_phase_snapshot(
            root: Path,
            transport_manifest: dict[str, object],
            source_manifest: dict[str, object],
        ) -> dict[str, object]:
            del root, transport_manifest, source_manifest
            retained = nested.read_bytes()
            old_path = source_root / "old-nested-inode"
            nested.rename(old_path)
            nested.write_bytes(retained)
            nested.chmod(0o444)
            assert nested.lstat().st_ino != original_inode
            old_path.unlink()
            return {}

        monkeypatch.setattr(
            authority,
            "verify_fixed_materialization_success_v42r1",
            mutate_after_first_phase_snapshot,
        )
        with pytest.raises(
            authority.ConstructionK7Standard2048RemoteExecutionAuthorityV42r1Error,
            match="phase or ancestor tree changed",
        ):
            authority.verify_remote_control_phase_inventory_v42r1(
                "POST_MATERIALIZATION_PREPARE"
            )
