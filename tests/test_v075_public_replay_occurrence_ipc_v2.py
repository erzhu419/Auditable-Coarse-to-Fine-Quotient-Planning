from __future__ import annotations

import ast
from copy import deepcopy
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import time
from types import SimpleNamespace
import zipfile

import pytest

from acfqp import v075_public_replay_occurrence_ipc_v2 as ipc
from tests.test_v075_portable_occurrence_evidence_bundle_v2 import (
    _build_portable_closed_bundle,
)


@pytest.fixture(scope="module")
def source_snapshot() -> ipc.V075PublicReplaySourceSnapshotV2:
    return ipc._capture_source_snapshot()  # noqa: SLF001


@pytest.fixture(scope="module")
def portable_bundle_bytes() -> bytes:
    return _build_portable_closed_bundle()[2].canonical_bytes


def _profile(
    raw: bytes,
    *,
    timeout: int = 600,
) -> ipc.V075PublicReplayOccurrenceIPCProfileV2:
    return ipc.freeze_v075_public_replay_occurrence_ipc_profile_v2(
        portable_bundle_bytes=raw,
        process_timeout_seconds=timeout,
    )


@pytest.fixture(scope="module")
def honest_replay(portable_bundle_bytes):
    profile = _profile(portable_bundle_bytes)
    result = ipc.execute_v075_public_replay_occurrence_ipc_v2(
        profile=profile,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    return profile, result


def _attack_script(
    tmp_path: Path,
    *,
    body: str,
) -> Path:
    path = tmp_path / "attack_child.py"
    path.write_text(
        textwrap.dedent(
            f"""
            import sys
            import time

            WIDTH = 8

            def read_frame():
                header = sys.stdin.buffer.read(WIDTH)
                if len(header) != WIDTH:
                    raise SystemExit(91)
                size = int(header.decode("ascii"), 16)
                raw = sys.stdin.buffer.read(size)
                if len(raw) != size:
                    raise SystemExit(92)
                return raw

            def write_frame(raw):
                header = f"{{len(raw):0{{WIDTH}}x}}".encode("ascii")
                sys.stdout.buffer.write(header + raw)
                sys.stdout.buffer.flush()

            read_frame()
            read_frame()
            if sys.stdin.buffer.read(1) != b"":
                raise SystemExit(93)
            {body}
            """
        ),
        encoding="utf-8",
    )
    return path


def _replace_child(
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
) -> None:
    monkeypatch.setattr(
        ipc,
        "_child_argv",
        lambda _registration, _sealed_fd: [
            sys.executable,
            "-I",
            str(path),
        ],
    )


def _expected_child_bytes(
    raw: bytes,
    profile: ipc.V075PublicReplayOccurrenceIPCProfileV2,
) -> bytes:
    return ipc._expected_child_result(  # noqa: SLF001
        profile,
        raw,
    ).canonical_bytes


def _different(value):
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        if len(value) == 64 and all(
            character in "0123456789abcdef" for character in value
        ):
            replacement = "0" if value[0] != "0" else "1"
            return replacement + value[1:]
        return value + "_MUTATED"
    if type(value) is tuple:
        return tuple(reversed(value))
    raise AssertionError(f"unsupported mutation type: {type(value)!r}")


def _mutate_path(root, path) -> None:
    target = root
    for component in path[:-1]:
        target = (
            target[component]
            if type(component) is int
            else getattr(target, component)
        )
    field_name = path[-1]
    object.__setattr__(
        target,
        field_name,
        _different(getattr(target, field_name)),
    )


def _synthetic_profile(
    source_snapshot: ipc.V075PublicReplaySourceSnapshotV2,
    raw: bytes,
) -> ipc.V075PublicReplayOccurrenceIPCProfileV2:
    program = ipc.registered_v075_public_replay_child_program_v2(
        source_snapshot=source_snapshot,
    )
    return ipc.V075PublicReplayOccurrenceIPCProfileV2(
        ipc._PROFILE_ISSUER,  # noqa: SLF001
        "1" * 64,
        "2" * 64,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        1,
        1,
        60,
        program,
        ipc._profile_freeze_work(  # noqa: SLF001
            source_snapshot,
            program.runtime_identity,
        ),
    )


def _synthetic_claimed_result(
    profile: ipc.V075PublicReplayOccurrenceIPCProfileV2,
    raw: bytes,
) -> ipc.V075PublicReplayOccurrenceIPCResultV2:
    snapshot = profile.program_registration.source_snapshot
    runtime = profile.program_registration.runtime_identity
    child = ipc._expected_child_result(  # noqa: SLF001
        profile,
        raw,
    )
    journal = ipc._expected_journal(  # noqa: SLF001
        profile=profile,
        portable_bundle_bytes=raw,
        child=child,
    )
    launch_raw = ipc._canonical_bytes(  # noqa: SLF001
        ipc._launch_document(profile)  # noqa: SLF001
    )
    work = ipc.V075PublicReplayIPCOperationalSuccessWorkV2(
        1,
        2,
        1,
        len(launch_raw) + len(raw),
        len(child.canonical_bytes),
        3 * ipc._FRAME_WIDTH,  # noqa: SLF001
        0,
        1,
        snapshot.archive_byte_count,
        snapshot.archive_byte_count,
        1,
        2,
        2 * snapshot.to_document()["archive_entry_count"],
        1,
        2,
        2,
        2 * len(snapshot.executable_entries),
        0,
    )
    attestation = ipc.V075PublicReplayConstructionSupervisorAttestationV2(
        ipc._SUPERVISOR_ATTESTATION_ISSUER,  # noqa: SLF001
        "3" * 64,
        12345,
        12345,
        1,
        runtime.executable_sha256,
        runtime.executable_byte_count,
        runtime.runtime_identity_id,
        snapshot.source_snapshot_id,
        3,
        0,
        1,
        snapshot.archive_byte_count,
        ipc._REQUIRED_SEALS,  # noqa: SLF001
        journal.entries[0].message_id,
        profile.portable_bundle_id,
        child.child_result_id,
        0,
        True,
        True,
        True,
    )
    return ipc.V075PublicReplayOccurrenceIPCResultV2(
        profile.profile_id,
        profile.occurrence_id,
        profile.portable_bundle_id,
        snapshot.source_snapshot_id,
        child,
        journal,
        work,
        attestation,
        hashlib.sha256(b"").hexdigest(),
        0,
    )


def test_source_snapshot_archive_is_canonical_sealed_and_read_only(
    source_snapshot,
) -> None:
    assert len(source_snapshot.source_manifest.entries) == 64
    assert {
        item.distribution_name
        for item in source_snapshot.dependency_distributions
    } == (
        {"packaging", "tomli"}
        if sys.version_info < (3, 11)
        else {"packaging"}
    )
    assert len(source_snapshot.executable_entries) > 65
    assert source_snapshot.to_document()["archive_entry_count"] == (
        len(source_snapshot.executable_entries)
        + 2 * len(source_snapshot.dependency_distributions)
    )
    lock = source_snapshot.to_document()["preregistered_dependency_lock"]
    assert lock["dependency_lock_id"] == (
        source_snapshot.to_document()["preregistered_dependency_lock_id"]
    )
    assert lock["installed_record_snapshot_bound"] is True
    assert lock["independent_distribution_authority_verified"] is False
    assert lock["external_lockfile_authority_verified"] is False
    assert lock["production_dependency_lock"] is False
    ipc._verify_source_archive_bytes(  # noqa: SLF001
        source_snapshot,
        source_snapshot.archive_bytes,
    )
    program = ipc.registered_v075_public_replay_child_program_v2(
        source_snapshot=source_snapshot,
    )
    reconstructed = ipc._program_from_document(  # noqa: SLF001
        program.to_document(),
        archive_bytes=b"",
    )
    assert reconstructed.registration_id == program.registration_id
    assert reconstructed.source_snapshot.source_snapshot_id == (
        source_snapshot.source_snapshot_id
    )
    assert reconstructed.source_snapshot.archive_bytes == b""
    assert reconstructed.runtime_identity.runtime_identity_id == (
        program.runtime_identity.runtime_identity_id
    )

    sealed_fd = ipc._stage_sealed_source_snapshot(  # noqa: SLF001
        source_snapshot
    )
    try:
        seals = fcntl.fcntl(sealed_fd, ipc._F_GET_SEALS)  # noqa: SLF001
        assert seals & ipc._REQUIRED_SEALS == ipc._REQUIRED_SEALS  # noqa: SLF001
        ipc._verify_sealed_source_fd(  # noqa: SLF001
            sealed_fd,
            source_snapshot,
        )
        with pytest.raises(OSError):
            os.write(sealed_fd, b"x")
        argv = ipc._child_argv(program, sealed_fd)  # noqa: SLF001
        assert argv[:5] == [
            sys.executable,
            "-I",
            "-S",
            "-c",
            ipc._BOOTSTRAP_SOURCE,  # noqa: SLF001
        ]
        assert str(Path(ipc.__file__).resolve()) not in argv
    finally:
        os.close(sealed_fd)


def test_dependency_sources_and_metadata_are_preregistered_and_sealed(
    source_snapshot,
) -> None:
    packaging = next(
        item
        for item in source_snapshot.dependency_distributions
        if item.distribution_name == "packaging"
    )
    installed = importlib.metadata.distribution("packaging")
    expected_packaging_sources = {
        PurePath.as_posix()
        for value in installed.files or ()
        if (
            (PurePath := Path(str(value))).parts
            and PurePath.parts[0] == "packaging"
            and PurePath.suffix == ".py"
        )
    }
    assert {
        item.relative_path for item in packaging.source_entries
    } == expected_packaging_sources
    if sys.version_info < (3, 11):
        assert any(
            item.distribution_name == "tomli"
            for item in source_snapshot.dependency_distributions
        )
    with zipfile.ZipFile(
        io.BytesIO(source_snapshot.archive_bytes),
        mode="r",
    ) as archive:
        names = set(archive.namelist())
        for distribution in source_snapshot.dependency_distributions:
            assert distribution.metadata_relative_path in names
            assert distribution.record_relative_path in names
            assert distribution.metadata_relative_path not in {
                item.relative_path
                for item in source_snapshot.executable_entries
            }
            assert distribution.record_relative_path not in {
                item.relative_path
                for item in source_snapshot.executable_entries
            }
            assert hashlib.sha256(
                archive.read(distribution.metadata_relative_path)
            ).hexdigest() == distribution.metadata_sha256
            assert hashlib.sha256(
                archive.read(distribution.record_relative_path)
            ).hexdigest() == distribution.record_sha256

        captured = {
            name: archive.read(name) for name in archive.namelist()
        }
    metadata_path = packaging.metadata_relative_path
    changed_metadata = bytearray(captured[metadata_path])
    changed_metadata[len(changed_metadata) // 2] ^= 1
    captured[metadata_path] = bytes(changed_metadata)
    attacked = ipc._deterministic_source_archive(captured)  # noqa: SLF001
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="archive bytes differ",
    ):
        ipc._verify_source_archive_bytes(  # noqa: SLF001
            source_snapshot,
            attacked,
        )


def test_dependency_version_full_rehash_cannot_override_raw_metadata(
    source_snapshot,
) -> None:
    attacked = deepcopy(source_snapshot)
    distribution = attacked.dependency_distributions[0]
    object.__setattr__(distribution, "distribution_version", "999.0")
    for entry in distribution.source_entries:
        object.__setattr__(entry, "distribution_version", "999.0")
    object.__setattr__(
        distribution,
        "_distribution_id",
        ipc._hash("dependency_distribution", distribution._payload()),  # noqa: SLF001
    )
    object.__setattr__(
        attacked,
        "_source_snapshot_id",
        ipc._hash("source_snapshot", attacked._payload()),  # noqa: SLF001
    )
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="raw Name/Version",
    ):
        ipc._verify_source_archive_bytes(  # noqa: SLF001
            attacked,
            attacked.archive_bytes,
        )


def test_unsealed_native_extension_record_full_rehash_fails_closed(
    source_snapshot,
) -> None:
    attacked = deepcopy(source_snapshot)
    distribution = attacked.dependency_distributions[0]
    with zipfile.ZipFile(
        io.BytesIO(attacked.archive_bytes),
        mode="r",
    ) as archive:
        captured = {
            name: archive.read(name) for name in archive.namelist()
        }
    record_path = distribution.record_relative_path
    captured[record_path] += b"packaging/injected_attack.so,,\\n"
    object.__setattr__(
        distribution,
        "record_sha256",
        hashlib.sha256(captured[record_path]).hexdigest(),
    )
    object.__setattr__(
        distribution,
        "record_byte_count",
        len(captured[record_path]),
    )
    object.__setattr__(
        distribution,
        "_distribution_id",
        ipc._hash("dependency_distribution", distribution._payload()),  # noqa: SLF001
    )
    attacked_archive = ipc._deterministic_source_archive(  # noqa: SLF001
        captured
    )
    object.__setattr__(attacked, "archive_bytes", attacked_archive)
    object.__setattr__(
        attacked,
        "archive_sha256",
        hashlib.sha256(attacked_archive).hexdigest(),
    )
    object.__setattr__(
        attacked,
        "archive_byte_count",
        len(attacked_archive),
    )
    object.__setattr__(
        attacked,
        "_source_snapshot_id",
        ipc._hash("source_snapshot", attacked._payload()),  # noqa: SLF001
    )
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="native extension",
    ):
        ipc._verify_source_archive_bytes(  # noqa: SLF001
            attacked,
            attacked_archive,
        )


def test_unsealed_and_partially_sealed_writable_fds_fail_closed(
    source_snapshot,
) -> None:
    unsealed_fd = ipc._memfd_create("acfqp-v075-unsealed-test")  # noqa: SLF001
    try:
        os.write(unsealed_fd, source_snapshot.archive_bytes)
        with pytest.raises(
            ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
            match="writable or unsealed",
        ):
            ipc._verify_sealed_source_fd(  # noqa: SLF001
                unsealed_fd,
                source_snapshot,
            )
        assert os.write(unsealed_fd, b"x") == 1
    finally:
        os.close(unsealed_fd)

    writable_fd = ipc._memfd_create("acfqp-v075-writable-test")  # noqa: SLF001
    try:
        os.write(writable_fd, source_snapshot.archive_bytes)
        fcntl.fcntl(
            writable_fd,
            ipc._F_ADD_SEALS,  # noqa: SLF001
            ipc._F_SEAL_GROW | ipc._F_SEAL_SHRINK,  # noqa: SLF001
        )
        with pytest.raises(
            ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
            match="writable or unsealed",
        ):
            ipc._verify_sealed_source_fd(  # noqa: SLF001
                writable_fd,
                source_snapshot,
            )
        os.lseek(writable_fd, 0, os.SEEK_SET)
        assert os.write(writable_fd, b"x") == 1
    finally:
        os.close(writable_fd)


def test_sealed_snapshot_zip_imports_exact_registered_module_origins(
    source_snapshot,
    tmp_path,
) -> None:
    sealed_fd = ipc._stage_sealed_source_snapshot(  # noqa: SLF001
        source_snapshot
    )
    expected = {
        entry.module_name: entry.relative_path
        for entry in source_snapshot.entries
    }
    script = textwrap.dedent(
        """
        import importlib
        import json
        import sys

        fd = int(sys.argv[1])
        expected = json.loads(sys.argv[2])
        archive_path = "/proc/self/fd/" + str(fd)
        sys.path.insert(0, archive_path)
        for name in sorted(expected):
            importlib.import_module(name)
        roots = {"acfqp", "packaging", "tomli"}
        actual = {
            name
            for name in sys.modules
            if any(name == root or name.startswith(root + ".") for root in roots)
        }
        if actual != set(expected):
            raise SystemExit(81)
        for name, relative_path in expected.items():
            origin = sys.modules[name].__spec__.origin
            if origin != archive_path + "/" + relative_path:
                raise SystemExit(82)
        print("OK")
        """
    )
    poison = tmp_path / "poison"
    (poison / "packaging").mkdir(parents=True)
    (poison / "packaging" / "__init__.py").write_text(
        "raise RuntimeError('site poison executed')\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(poison)
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                script,
                str(sealed_fd),
                json.dumps(expected, sort_keys=True),
            ],
            check=False,
            capture_output=True,
            env=environment,
            pass_fds=(sealed_fd,),
            timeout=60,
        )
    finally:
        os.close(sealed_fd)
    assert completed.returncode == 0, completed.stderr.decode(
        "utf-8",
        errors="replace",
    )
    assert completed.stdout == b"OK\n"
    assert completed.stderr == b""


def test_loaded_source_origin_and_archive_byte_mutations_fail_closed(
    source_snapshot,
    monkeypatch,
) -> None:
    entry = source_snapshot.entries[0]
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="loaded public replay source entry",
    ):
        ipc.V075PublicReplayLoadedSourceEntryV2(
            entry.module_name,
            entry.relative_path,
            entry.source_sha256,
            entry.source_byte_count,
            f"/live/workspace/{entry.relative_path}",
        )

    raw = b"x"
    profile = _synthetic_profile(source_snapshot, raw)
    attacked = deepcopy(profile)
    archive = bytearray(
        attacked.program_registration.source_snapshot.archive_bytes
    )
    archive[len(archive) // 2] ^= 1
    object.__setattr__(
        attacked.program_registration.source_snapshot,
        "archive_bytes",
        bytes(archive),
    )
    launched = False

    def forbidden_launch(_registration, _sealed_fd):
        nonlocal launched
        launched = True
        raise AssertionError("mutated source archive must fail before launch")

    monkeypatch.setattr(ipc, "_child_argv", forbidden_launch)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="source archive bytes differ",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=attacked,
            portable_bundle_bytes=raw,
        )
    assert launched is False


def test_child_runtime_identity_is_independently_recomputed(
    source_snapshot,
) -> None:
    runtime = ipc._capture_runtime_identity()  # noqa: SLF001
    program = ipc.registered_v075_public_replay_child_program_v2(
        source_snapshot=source_snapshot,
        runtime_identity=runtime,
    )
    sealed_fd = ipc._stage_sealed_source_snapshot(  # noqa: SLF001
        source_snapshot
    )
    try:
        argv = ipc._child_argv(program, sealed_fd)  # noqa: SLF001
        argv[-1] = "0" * 64
        if runtime.runtime_identity_id == argv[-1]:
            argv[-1] = "1" * 64
        completed = subprocess.run(
            argv,
            input=b"",
            check=False,
            capture_output=True,
            pass_fds=(sealed_fd,),
            timeout=30,
        )
    finally:
        os.close(sealed_fd)
    assert completed.returncode == 74
    assert completed.stderr == (
        b"V075PublicReplayOccurrenceIPCV2InvariantViolation\n"
    )
    assert completed.stdout == b""


def test_process_none_launch_failure_closes_sealed_fd_without_masking(
    source_snapshot,
    monkeypatch,
) -> None:
    raw = b"x"
    profile = _synthetic_profile(source_snapshot, raw)
    staged_fds: list[int] = []
    real_stage = ipc._stage_sealed_source_snapshot  # noqa: SLF001

    def recording_stage(snapshot, **kwargs):
        fd = real_stage(snapshot, **kwargs)
        staged_fds.append(fd)
        return fd

    def fail_before_popen(_registration, _sealed_fd):
        raise RuntimeError("synthetic argv failure")

    monkeypatch.setattr(ipc, "_stage_sealed_source_snapshot", recording_stage)
    monkeypatch.setattr(ipc, "_child_argv", fail_before_popen)
    with pytest.raises(RuntimeError, match="synthetic argv failure"):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=raw,
        )
    assert len(staged_fds) == 1
    with pytest.raises(OSError):
        os.fstat(staged_fds[0])


def test_supervisor_attestation_and_success_work_are_separate_and_nonofficial(
    source_snapshot,
    monkeypatch,
    tmp_path,
) -> None:
    raw = b"x"
    profile = _synthetic_profile(source_snapshot, raw)
    expected_hex = _expected_child_bytes(raw, profile).hex()
    child = _attack_script(
        tmp_path,
        body=f"write_frame(bytes.fromhex({expected_hex!r}))",
    )
    _replace_child(monkeypatch, child)
    result = ipc.execute_v075_public_replay_occurrence_ipc_v2(
        profile=profile,
        portable_bundle_bytes=raw,
    )
    attestation = result.supervisor_attestation
    work = result.operational_success_work
    assert attestation.child_pid == attestation.child_pgid
    assert attestation.runtime_identity_id == (
        profile.program_registration.runtime_identity.runtime_identity_id
    )
    assert attestation.source_snapshot_id == source_snapshot.source_snapshot_id
    assert attestation.sealed_fd_seals == ipc._REQUIRED_SEALS  # noqa: SLF001
    assert attestation.leader_reaped is True
    assert attestation.process_group_absent_after_cleanup is True
    attestation_document = attestation.to_document()
    assert attestation_document["cryptographic_or_os_provenance"] is False
    assert attestation_document["persistent_process_provenance_proof"] is False
    assert attestation_document["parent_execution_source_attested"] is False
    assert attestation_document["child_loaded_source_os_attested"] is False

    assert work.source_archive_validation_passes_parent_execution == 2
    assert work.source_archive_entry_checks_parent_execution == (
        2 * source_snapshot.to_document()["archive_entry_count"]
    )
    assert work.raw_bundle_verifier_calls_parent_execution == 0
    assert work.raw_bundle_verifier_calls_child == 1
    assert work.loaded_source_entry_checks_child == (
        2 * len(source_snapshot.executable_entries)
    )
    work_document = work.to_document()
    assert work_document["failure_path_accounting_complete"] is False
    assert work_document["official_or_economics_cost_eligible"] is False
    assert work_document["parent_execution_source_attested"] is False
    assert work_document["child_internal_counter_observed"] is False
    assert work_document["independently_verified_actual_work"] is False
    assert (
        work_document["accounting_blocker"]
        == "TYPED_FAILURE_WORK_ARTIFACT_NOT_IMPLEMENTED"
    )
    assert profile.profile_freeze_work.raw_bundle_verifier_calls == 1
    assert profile.profile_freeze_work.process_launches == 0


def test_raw_verifier_is_followed_by_second_exact_loaded_source_check(
    source_snapshot,
    monkeypatch,
) -> None:
    before = ipc._expected_loaded_source_manifest(  # noqa: SLF001
        source_snapshot
    )
    events: list[str] = []
    sentinel = object()

    def verify(raw):
        assert raw == b"x"
        events.append("verify")
        return sentinel

    def exact_loaded(*, snapshot, archive_path):
        assert snapshot is source_snapshot
        assert archive_path == "/proc/self/fd/99"
        events.append("loaded")
        return before

    monkeypatch.setattr(ipc, "_verify_bundle", verify)
    monkeypatch.setattr(ipc, "_actual_loaded_source_manifest", exact_loaded)
    bundle, after = ipc._verify_bundle_with_loaded_source_recheck(  # noqa: SLF001
        raw=b"x",
        snapshot=source_snapshot,
        archive_path="/proc/self/fd/99",
        before=before,
    )
    assert bundle is sentinel
    assert after is before
    assert events == ["verify", "loaded"]

    first = before.entries[0]
    changed_digest = (
        ("0" if first.source_sha256[0] != "0" else "1")
        + first.source_sha256[1:]
    )
    changed_first = ipc.V075PublicReplayLoadedSourceEntryV2(
        first.module_name,
        first.relative_path,
        changed_digest,
        first.source_byte_count,
        first.normalized_origin,
    )
    changed = ipc.V075PublicReplayLoadedSourceManifestV2(
        before.source_snapshot_id,
        (changed_first, *before.entries[1:]),
    )
    monkeypatch.setattr(
        ipc,
        "_actual_loaded_source_manifest",
        lambda **_kwargs: changed,
    )
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="source set changed",
    ):
        ipc._verify_bundle_with_loaded_source_recheck(  # noqa: SLF001
            raw=b"x",
            snapshot=source_snapshot,
            archive_path="/proc/self/fd/99",
            before=before,
        )


def test_terminate_process_kills_descendants_after_leader_exit(
    tmp_path,
) -> None:
    descendant_pid_path = tmp_path / "descendant.pid"
    script = textwrap.dedent(
        """
        import os
        from pathlib import Path
        import sys
        import time

        child = os.fork()
        if child == 0:
            Path(sys.argv[1]).write_text(str(os.getpid()), encoding="ascii")
            while True:
                time.sleep(1)
        raise SystemExit(0)
        """
    )
    process = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", script, str(descendant_pid_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        assert process.wait(timeout=10) == 0
        deadline = time.monotonic() + 5
        while not descendant_pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        descendant_pid = int(
            descendant_pid_path.read_text(encoding="ascii")
        )

        def descendant_is_running() -> bool:
            try:
                state = Path(f"/proc/{descendant_pid}/stat").read_text(
                    encoding="ascii"
                ).split()[2]
            except (FileNotFoundError, ProcessLookupError):
                return False
            return state != "Z"

        assert descendant_is_running()
        ipc._terminate_process(process)  # noqa: SLF001
        deadline = time.monotonic() + 5
        while descendant_is_running() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert descendant_is_running() is False
    finally:
        ipc._terminate_process(process)  # noqa: SLF001


def test_uppercase_frame_headers_fail_at_both_protocol_endpoints() -> None:
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="noncanonical",
    ):
        ipc._read_frame_child(  # noqa: SLF001
            io.BytesIO(b"0000000A" + b"x" * 10),
            byte_cap=100,
        )

    attack = textwrap.dedent(
        """
        import sys

        for _ in range(2):
            header = sys.stdin.buffer.read(8)
            length = int(header.decode("ascii"), 16)
            remaining = length
            while remaining:
                raw = sys.stdin.buffer.read(remaining)
                if not raw:
                    raise SystemExit(91)
                remaining -= len(raw)
        sys.stdout.buffer.write(b"0000000A" + b"x" * 10)
        sys.stdout.buffer.flush()
        """
    )
    process = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", attack],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        with pytest.raises(
            ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
            match="noncanonical",
        ):
            ipc._supervised_exchange(  # noqa: SLF001
                process,
                parent_frames=((b"x", 100), (b"y", 100)),
                deadline=time.monotonic() + 10,
            )
    finally:
        ipc._terminate_process(process)  # noqa: SLF001


def test_public_semantic_evaluation_replays_raw_bundle_in_own_lane(
    source_snapshot,
    monkeypatch,
) -> None:
    raw = b"x"
    profile = _synthetic_profile(source_snapshot, raw)
    claimed = _synthetic_claimed_result(profile, raw)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="raw-byte replay failed",
    ):
        ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
            claimed=claimed,
            profile=profile,
            portable_bundle_bytes=raw,
        )

    calls: list[bytes] = []
    verified_bundle = SimpleNamespace(
        occurrence_id=profile.occurrence_id,
        bundle_id=profile.portable_bundle_id,
        records=(object(),),
        root_bindings=(object(),),
    )

    def replay(value):
        calls.append(value)
        return verified_bundle

    monkeypatch.setattr(ipc, "_verify_bundle", replay)
    evaluation = ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
        claimed=claimed,
        profile=profile,
        portable_bundle_bytes=raw,
    )
    assert calls == [raw]
    assert isinstance(
        evaluation,
        ipc.V075PublicReplaySemanticEvaluationV2,
    )
    assert evaluation.evaluation_work.raw_bundle_verifier_calls == 1
    assert evaluation.evaluation_work.process_launches == 0
    assert evaluation.to_document()["process_provenance_verified"] is False
    assert evaluation.to_document()["operational_work_verified"] is False


def test_child_pid_full_ancestor_rehash_is_reconstructed_and_rejected(
    source_snapshot,
    monkeypatch,
) -> None:
    raw = b"x"
    profile = _synthetic_profile(source_snapshot, raw)
    attacked = _synthetic_claimed_result(profile, raw)
    verified_bundle = SimpleNamespace(
        occurrence_id=profile.occurrence_id,
        bundle_id=profile.portable_bundle_id,
        records=(object(),),
        root_bindings=(object(),),
    )
    monkeypatch.setattr(ipc, "_verify_bundle", lambda _raw: verified_bundle)

    attestation = attacked.supervisor_attestation
    object.__setattr__(attestation, "child_pid", attestation.child_pid + 1)
    object.__setattr__(
        attestation,
        "_attestation_id",
        ipc._hash(  # noqa: SLF001
            "supervisor_attestation",
            attestation._payload(),  # noqa: SLF001
        ),
    )
    object.__setattr__(
        attacked,
        "_result_id",
        ipc._hash("result", attacked._payload()),  # noqa: SLF001
    )
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="semantic result or internal binding",
    ):
        ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
            claimed=attacked,
            profile=profile,
            portable_bundle_bytes=raw,
        )


def test_isolated_public_replay_round_trip_is_typed_and_non_authorizing(
    portable_bundle_bytes,
    honest_replay,
) -> None:
    profile, result = honest_replay
    evaluation = ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
        claimed=result,
        profile=profile,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    document = result.to_document()
    child = result.child_verification.to_document()

    assert evaluation.result_id == result.result_id
    assert evaluation.evaluation_work.raw_bundle_verifier_calls == 1
    assert evaluation.to_document()["process_provenance_verified"] is False
    assert result.profile_id == profile.profile_id
    assert result.portable_bundle_id == profile.portable_bundle_id
    assert child["terminal_code"] == (
        "PORTABLE_GRAPH_REPLAYED_CONSTRUCTION_ONLY"
    )
    assert child["raw_bundle_bytes_verified"] is True
    assert child["semantic_registry_replay_complete"] is False
    assert document["terminal_scope"] == "CONSTRUCTION_PUBLIC_REPLAY_ONLY"
    assert document["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["official_execution_allowed"] is False
    assert document["production_authorizing"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert len(result.journal.entries) == 3
    work = result.operational_success_work
    assert work.process_launches == 1
    assert work.parent_to_child_frames == 2
    assert work.child_to_parent_frames == 1
    assert work.staged_bytes == (
        profile.program_registration.source_snapshot.archive_byte_count
    )
    assert work.source_snapshot_bytes == work.staged_bytes
    assert work.sealed_memfd_count == 1
    assert work.source_archive_validation_passes_parent_execution == 2
    assert work.seal_verification_checks_parent_execution == 1
    assert work.seal_verification_checks_child == 2
    assert result.supervisor_attestation.leader_reaped is True
    assert (
        result.supervisor_attestation.to_document()[
            "cryptographic_or_os_provenance"
        ]
        is False
    )
    assert result.source_snapshot_id == (
        profile.program_registration.source_snapshot.source_snapshot_id
    )
    assert len(
        result.child_verification.loaded_source_manifest.entries
    ) == len(profile.program_registration.source_snapshot.executable_entries)
    assert all(
        item.normalized_origin.startswith("sealed-memfd://snapshot/")
        for item in result.child_verification.loaded_source_manifest.entries
    )
    assert result.stderr_byte_count == 0
    program = profile.program_registration
    manifest_modules = {
        item.module_name for item in program.source_manifest.entries
    }
    assert {
        "acfqp.phase3e_ids",
        "acfqp.v075_public_graph_semantics_v1",
        "acfqp.v075_observer_signed_batch_control_authority_v2",
        "acfqp.v075_live_incremental_model_authority_v2",
        "acfqp.v075_live_dynamic_acquisition_authority_v2",
        "acfqp.v075_observer_signed_multiround_occurrence_runner_v2",
        "acfqp.v075_private_observer_boundary_v2",
    } <= manifest_modules
    assert program.interpreter_implementation == sys.implementation.name
    assert program.interpreter_cache_tag == sys.implementation.cache_tag
    assert program.interpreter_executable_byte_count > 0
    assert result.result_id == hashlib.sha256(
        ipc._DOMAINS["result"].encode("utf-8")  # noqa: SLF001
        + b"\x00"
        + ipc._canonical_bytes(result._payload())  # noqa: SLF001
    ).hexdigest()


def test_child_source_has_only_the_registered_public_bundle_boundary() -> None:
    path = Path(ipc.__file__).resolve()
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden_source_tokens = (
        "private_salt",
        "private_environment",
        "observer_signer",
        "secret_laws",
        "target_tape_namespace",
        "v075_private_observer_boundary",
        "v075_live_dynamic_acquisition_authority",
        "v075_live_incremental_model_authority",
        "v075_observer_signed_batch_control_authority",
        "v075_observer_signed_multiround_occurrence_runner",
    )
    assert not any(token in source for token in forbidden_source_tokens)
    assert not any(
        name.endswith(
            (
                "v075_private_observer_boundary_v2",
                "v075_live_dynamic_acquisition_authority_v2",
                "v075_live_incremental_model_authority_v2",
                "v075_observer_signed_batch_control_authority_v2",
                "v075_observer_signed_multiround_occurrence_runner_v2",
            )
        )
        for name in imports
    )
    assert ipc._VERIFIER_MODULE_NAME in source  # noqa: SLF001
    assert ipc._VERIFIER_CALLABLE in source  # noqa: SLF001


def test_parent_rejects_mutated_bundle_before_process_launch(
    portable_bundle_bytes,
    monkeypatch,
) -> None:
    profile = _profile(portable_bundle_bytes)
    attacked = bytearray(portable_bundle_bytes)
    attacked[-2] = ord("0") if attacked[-2] != ord("0") else ord("1")
    launched = False

    def forbidden_launch(_registration, _sealed_fd):
        nonlocal launched
        launched = True
        raise AssertionError("mutated bytes must fail before process launch")

    monkeypatch.setattr(ipc, "_child_argv", forbidden_launch)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="raw-byte replay failed|frozen replay profile",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=bytes(attacked),
        )
    assert launched is False


def test_stale_program_digest_is_rejected_before_process_launch(
    portable_bundle_bytes,
    monkeypatch,
) -> None:
    profile = _profile(portable_bundle_bytes)
    object.__setattr__(
        profile.program_registration,
        "ipc_module_sha256",
        "0" * 64,
    )
    launched = False

    def forbidden_launch(_registration, _sealed_fd):
        nonlocal launched
        launched = True
        raise AssertionError("stale program must fail before process launch")

    monkeypatch.setattr(ipc, "_child_argv", forbidden_launch)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="stale",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )
    assert launched is False


def test_post_profile_live_workspace_replacement_does_not_affect_sealed_child(
    portable_bundle_bytes,
    honest_replay,
    monkeypatch,
) -> None:
    profile, _original = honest_replay

    def forbidden_live_access(*_args, **_kwargs):
        raise AssertionError("execution accessed the replaced live workspace")

    monkeypatch.setattr(ipc, "_local_module_path", forbidden_live_access)
    monkeypatch.setattr(ipc, "_verifier_module_path", forbidden_live_access)
    monkeypatch.setattr(ipc, "_load_portable_verifier", forbidden_live_access)
    monkeypatch.setattr(ipc, "_source_identity", forbidden_live_access)
    replayed = ipc.execute_v075_public_replay_occurrence_ipc_v2(
        profile=profile,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    assert replayed.source_snapshot_id == (
        profile.program_registration.source_snapshot.source_snapshot_id
    )


def test_status_only_child_output_is_rejected(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    profile = _profile(portable_bundle_bytes)
    child = _attack_script(
        tmp_path,
        body=(
            "write_frame("
            "b'{\"status\":\"PORTABLE_GRAPH_REPLAYED_CONSTRUCTION_ONLY\"}'"
            ")"
        ),
    )
    _replace_child(monkeypatch, child)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="independent host reconstruction",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_extra_child_frame_is_rejected(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    profile = _profile(portable_bundle_bytes)
    expected_hex = _expected_child_bytes(
        portable_bundle_bytes,
        profile,
    ).hex()
    child = _attack_script(
        tmp_path,
        body=(
            f"raw = bytes.fromhex({expected_hex!r}); "
            "write_frame(raw); write_frame(raw)"
        ),
    )
    _replace_child(monkeypatch, child)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="extra stdout",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_stderr_is_rejected_even_with_exact_typed_result(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    profile = _profile(portable_bundle_bytes)
    expected_hex = _expected_child_bytes(
        portable_bundle_bytes,
        profile,
    ).hex()
    child = _attack_script(
        tmp_path,
        body=(
            f"write_frame(bytes.fromhex({expected_hex!r})); "
            "sys.stderr.buffer.write(b'x'); sys.stderr.buffer.flush()"
        ),
    )
    _replace_child(monkeypatch, child)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="stderr",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_timeout_is_enforced_and_process_group_is_terminated(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    profile = _profile(portable_bundle_bytes, timeout=1)
    child = _attack_script(tmp_path, body="time.sleep(5)")
    _replace_child(monkeypatch, child)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="timeout",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_large_bundle_write_shares_deadline_with_stalled_reader(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    assert len(portable_bundle_bytes) > 1024 * 1024
    profile = _profile(portable_bundle_bytes, timeout=1)
    exact_profile = ipc._require_exact_profile(  # noqa: SLF001
        profile,
        require_archive_bytes=True,
    )
    monkeypatch.setattr(
        ipc,
        "_require_exact_profile",
        lambda claimed, **_kwargs: exact_profile
        if claimed is profile
        else (_ for _ in ()).throw(AssertionError("unexpected profile")),
    )
    child = tmp_path / "stalled_reader.py"
    child.write_text(
        "import time\ntime.sleep(5)\n",
        encoding="utf-8",
    )
    _replace_child(monkeypatch, child)
    started = time.monotonic()
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="timeout",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )
    assert time.monotonic() - started < 3


def test_result_and_journal_transplants_fail_independent_verification(
    portable_bundle_bytes,
    honest_replay,
) -> None:
    profile, result = honest_replay
    copied = deepcopy(result)
    object.__setattr__(
        copied.operational_success_work,
        "parent_to_child_payload_bytes",
        copied.operational_success_work.parent_to_child_payload_bytes + 1,
    )
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="semantic result or internal binding",
    ):
        ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
            claimed=copied,
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_every_result_identity_journal_and_work_field_is_reconstructed(
    portable_bundle_bytes,
    honest_replay,
) -> None:
    profile, result = honest_replay
    paths = [
        ("profile_id",),
        ("occurrence_id",),
        ("portable_bundle_id",),
        ("source_snapshot_id",),
        ("stderr_sha256",),
        ("stderr_byte_count",),
        ("_result_id",),
        ("child_verification", "profile_id"),
        ("child_verification", "program_registration_id"),
        ("child_verification", "occurrence_id"),
        ("child_verification", "portable_bundle_id"),
        ("child_verification", "portable_bundle_sha256"),
        ("child_verification", "portable_bundle_byte_count"),
        ("child_verification", "artifact_count"),
        ("child_verification", "root_binding_count"),
        ("child_verification", "source_snapshot_id"),
        ("child_verification", "loaded_source_manifest", "entries"),
        (
            "child_verification",
            "loaded_source_manifest",
            "_loaded_manifest_id",
        ),
        (
            "child_verification",
            "loaded_source_manifest",
            "entries",
            0,
            "module_name",
        ),
        (
            "child_verification",
            "loaded_source_manifest",
            "entries",
            0,
            "relative_path",
        ),
        (
            "child_verification",
            "loaded_source_manifest",
            "entries",
            0,
            "source_sha256",
        ),
        (
            "child_verification",
            "loaded_source_manifest",
            "entries",
            0,
            "source_byte_count",
        ),
        (
            "child_verification",
            "loaded_source_manifest",
            "entries",
            0,
            "normalized_origin",
        ),
        ("child_verification", "_child_result_id"),
        ("journal", "entries"),
        ("journal", "_journal_id"),
        ("operational_success_work", "process_launches"),
        ("operational_success_work", "parent_to_child_frames"),
        ("operational_success_work", "child_to_parent_frames"),
        ("operational_success_work", "parent_to_child_payload_bytes"),
        ("operational_success_work", "child_to_parent_payload_bytes"),
        ("operational_success_work", "framing_bytes"),
        (
            "operational_success_work",
            "raw_bundle_verifier_calls_parent_execution",
        ),
        (
            "operational_success_work",
            "raw_bundle_verifier_calls_child",
        ),
        ("operational_success_work", "staged_bytes"),
        ("operational_success_work", "source_snapshot_bytes"),
        ("operational_success_work", "sealed_memfd_count"),
        (
            "operational_success_work",
            "source_archive_validation_passes_parent_execution",
        ),
        (
            "operational_success_work",
            "source_archive_entry_checks_parent_execution",
        ),
        (
            "operational_success_work",
            "seal_verification_checks_parent_execution",
        ),
        (
            "operational_success_work",
            "seal_verification_checks_child",
        ),
        ("operational_success_work", "loaded_source_checks_child"),
        (
            "operational_success_work",
            "loaded_source_entry_checks_child",
        ),
        ("operational_success_work", "process_exit_code"),
        ("operational_success_work", "_work_id"),
        ("supervisor_attestation", "supervisor_nonce"),
        ("supervisor_attestation", "child_pid"),
        ("supervisor_attestation", "child_pgid"),
        ("supervisor_attestation", "child_proc_start_ticks"),
        ("supervisor_attestation", "child_executable_sha256"),
        ("supervisor_attestation", "child_executable_byte_count"),
        ("supervisor_attestation", "runtime_identity_id"),
        ("supervisor_attestation", "source_snapshot_id"),
        ("supervisor_attestation", "sealed_fd_number"),
        ("supervisor_attestation", "sealed_fd_device"),
        ("supervisor_attestation", "sealed_fd_inode"),
        ("supervisor_attestation", "sealed_fd_size"),
        ("supervisor_attestation", "sealed_fd_seals"),
        ("supervisor_attestation", "launch_id"),
        ("supervisor_attestation", "portable_bundle_id"),
        ("supervisor_attestation", "child_result_id"),
        ("supervisor_attestation", "child_exit_code"),
        ("supervisor_attestation", "leader_reaped"),
        (
            "supervisor_attestation",
            "process_group_cleanup_attempted",
        ),
        (
            "supervisor_attestation",
            "process_group_absent_after_cleanup",
        ),
        ("supervisor_attestation", "_attestation_id"),
    ]
    entry_fields = (
        "sequence_number",
        "direction",
        "message_kind",
        "message_id",
        "message_byte_count",
        "message_sha256",
        "previous_entry_id",
        "_entry_id",
    )
    paths.extend(
        ("journal", "entries", index, field_name)
        for index in range(3)
        for field_name in entry_fields
    )
    for path in paths:
        attacked = deepcopy(result)
        _mutate_path(attacked, path)
        with pytest.raises(
            ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
            match="semantic result or internal binding",
        ):
            ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
                claimed=attacked,
                profile=profile,
                portable_bundle_bytes=portable_bundle_bytes,
            )


def test_profile_program_manifest_and_cached_ids_are_reconstructed(
    portable_bundle_bytes,
    honest_replay,
) -> None:
    profile, result = honest_replay
    paths = (
        ("occurrence_id",),
        ("portable_bundle_id",),
        ("portable_bundle_sha256",),
        ("portable_bundle_byte_count",),
        ("portable_artifact_count",),
        ("portable_root_binding_count",),
        ("process_timeout_seconds",),
        ("_profile_id",),
        ("profile_freeze_work", "source_snapshot_captures"),
        (
            "profile_freeze_work",
            "source_archive_validation_passes",
        ),
        ("profile_freeze_work", "source_archive_entries_checked"),
        ("profile_freeze_work", "runtime_identity_captures"),
        ("profile_freeze_work", "stdlib_entries_hashed"),
        ("profile_freeze_work", "raw_bundle_verifier_calls"),
        ("profile_freeze_work", "process_launches"),
        ("profile_freeze_work", "_profile_freeze_work_id"),
        ("program_registration", "ipc_module_sha256"),
        ("program_registration", "verifier_module_sha256"),
        ("program_registration", "interpreter_implementation"),
        ("program_registration", "interpreter_version"),
        ("program_registration", "interpreter_cache_tag"),
        ("program_registration", "interpreter_executable_sha256"),
        ("program_registration", "interpreter_executable_byte_count"),
        ("program_registration", "_registration_id"),
        (
            "program_registration",
            "runtime_identity",
            "_runtime_identity_id",
        ),
        (
            "program_registration",
            "runtime_identity",
            "executable_sha256",
        ),
        (
            "program_registration",
            "runtime_identity",
            "shared_library_sha256",
        ),
        (
            "program_registration",
            "runtime_identity",
            "stdlib_tree_digest",
        ),
        (
            "program_registration",
            "runtime_identity",
            "soabi",
        ),
        (
            "program_registration",
            "source_snapshot",
            "_source_snapshot_id",
        ),
        (
            "program_registration",
            "source_snapshot",
            "archive_sha256",
        ),
        (
            "program_registration",
            "source_snapshot",
            "archive_byte_count",
        ),
        (
            "program_registration",
            "source_snapshot",
            "bootstrap_sha256",
        ),
        (
            "program_registration",
            "source_snapshot",
            "source_manifest",
            "_manifest_id",
        ),
        (
            "program_registration",
            "source_snapshot",
            "source_manifest",
            "entries",
            0,
            "source_sha256",
        ),
        (
            "program_registration",
            "source_snapshot",
            "source_manifest",
            "entries",
            0,
            "source_byte_count",
        ),
        (
            "program_registration",
            "source_snapshot",
            "dependency_distributions",
            0,
            "_distribution_id",
        ),
        (
            "program_registration",
            "source_snapshot",
            "dependency_distributions",
            0,
            "metadata_sha256",
        ),
        (
            "program_registration",
            "source_snapshot",
            "dependency_distributions",
            0,
            "source_entries",
            0,
            "source_sha256",
        ),
    )
    for path in paths:
        attacked_profile = deepcopy(profile)
        _mutate_path(attacked_profile, path)
        with pytest.raises(
            ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation
        ):
            ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
                claimed=result,
                profile=attacked_profile,
                portable_bundle_bytes=portable_bundle_bytes,
            )


def test_production_entrypoint_and_all_module_locks_remain_closed() -> None:
    assert ipc.PROPOSED_CONTRACT_VERSION == "1.62.0"
    assert ipc.OFFICIAL_EXECUTION_ALLOWED is False
    assert ipc.PRODUCTION_AUTHORIZING is False
    assert ipc.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert ipc.SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED is False
    assert ipc.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert ipc.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert ipc.SEMANTIC_REGISTRY_REPLAY_COMPLETE is False
    with pytest.raises(ipc.V075PublicReplayProductionV2NotReady):
        ipc.open_v075_production_public_replay_occurrence_ipc_v2()
