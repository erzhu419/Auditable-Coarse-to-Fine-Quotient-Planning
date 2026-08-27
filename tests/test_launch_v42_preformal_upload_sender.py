from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import os
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from scripts import launch_v42_preformal_upload_sender as launcher
from scripts import publish_v42_preformal_upload_journal as journal
from scripts import run_v42_preformal_upload_sender as sender
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _context,
    _fixture,
    _token,
)


def _write_control_capsule(root: Path, controls: dict[str, bytes]) -> None:
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    for name in launcher.CONTROL_NAMES:
        path = root / name
        path.write_bytes(controls[name])
        os.chmod(path, 0o400)


def _small_controls() -> dict[str, bytes]:
    return {
        name: (name + "\n").encode("ascii") for name in launcher.CONTROL_NAMES
    }


def _exact_fake_sys(token: str) -> SimpleNamespace:
    argv = [str(launcher.SCRIPT_PATH), "--upload-token", token]
    return SimpleNamespace(
        executable=launcher.LOCAL_PYTHON,
        version_info=launcher.LOCAL_PYTHON_VERSION,
        flags=SimpleNamespace(isolated=1, no_site=1),
        dont_write_bytecode=True,
        argv=argv,
        orig_argv=[
            launcher.LOCAL_PYTHON,
            "-I",
            "-S",
            "-B",
            *argv,
        ],
    )


def test_exact_cli_entry_accepts_only_isolated_ordered_lower_hex64(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token("strict-launcher-entry")
    monkeypatch.setattr(launcher, "sys", _exact_fake_sys(token))
    assert launcher._verify_exact_cli_entry_v42r1() == token  # noqa: SLF001

    crossed = _exact_fake_sys(token)
    crossed.orig_argv[1:4] = ["-S", "-I", "-B"]
    monkeypatch.setattr(launcher, "sys", crossed)
    with pytest.raises(
        launcher.V42PreformalSenderLauncherError,
        match="original Python argv changed",
    ):
        launcher._verify_exact_cli_entry_v42r1()  # noqa: SLF001

    malformed = _exact_fake_sys(token.upper())
    monkeypatch.setattr(launcher, "sys", malformed)
    with pytest.raises(
        launcher.V42PreformalSenderLauncherError,
        match="fresh lowercase hex64 syntax",
    ):
        launcher._verify_exact_cli_entry_v42r1()  # noqa: SLF001


def test_five_controls_are_exact_mode0400_owned_single_link_stable_readbacks(
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-launcher-controls-", dir="/tmp"
    ) as base:
        root = Path(base) / "capsule"
        controls = _small_controls()
        _write_control_capsule(root, controls)

        assert launcher._read_control_capsule_v42r1(root) == controls  # noqa: SLF001

        os.chmod(root / launcher.SOURCE_MANIFEST_NAME, 0o600)
        with pytest.raises(
            launcher.V42PreformalSenderLauncherError, match="metadata changed"
        ):
            launcher._read_control_capsule_v42r1(root)  # noqa: SLF001


@pytest.mark.parametrize("attack", ["extra", "symlink", "hardlink", "fifo"])
def test_five_control_namespace_attacks_fail_closed_without_fifo_block(
    attack: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-launcher-attack-", dir="/tmp"
    ) as base:
        base_path = Path(base)
        root = base_path / ("capsule-" + attack)
        controls = _small_controls()
        _write_control_capsule(root, controls)
        target = root / launcher.SOURCE_MANIFEST_NAME
        if attack == "extra":
            (root / "UNREGISTERED").write_bytes(b"x")
        elif attack == "symlink":
            target.unlink()
            target.symlink_to(root / launcher.TRANSPORT_MANIFEST_NAME)
        elif attack == "hardlink":
            os.link(target, base_path / "second-name")
        else:
            target.unlink()
            os.mkfifo(target, mode=0o400)

        with pytest.raises(launcher.V42PreformalSenderLauncherError):
            launcher._read_control_capsule_v42r1(root)  # noqa: SLF001


def test_stable_readback_detects_named_replacement_between_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-launcher-replace-", dir="/tmp"
    ) as base:
        root = Path(base) / "capsule-replace"
        controls = _small_controls()
        _write_control_capsule(root, controls)
        target = root / launcher.SOURCE_MANIFEST_NAME
        target_identity = (target.stat().st_dev, target.stat().st_ino)
        original_read_stream = launcher._read_stream  # noqa: SLF001
        replaced = False

        def replace_after_first_pass(
            descriptor: int, maximum: int, *, retain: bool
        ) -> tuple[bytes, str, int]:
            nonlocal replaced
            result = original_read_stream(descriptor, maximum, retain=retain)
            observed = os.fstat(descriptor)
            if (
                retain
                and not replaced
                and (observed.st_dev, observed.st_ino) == target_identity
            ):
                replacement = root / ".replacement"
                replacement.write_bytes(controls[launcher.SOURCE_MANIFEST_NAME])
                os.chmod(replacement, 0o400)
                os.replace(replacement, target)
                replaced = True
            return result

        monkeypatch.setattr(launcher, "_read_stream", replace_after_first_pass)
        with pytest.raises(
            launcher.V42PreformalSenderLauncherError,
            match="changed during stable readback",
        ):
            launcher._read_control_capsule_v42r1(root)  # noqa: SLF001
        assert replaced is True


def test_preimport_manifest_join_replays_real_transport_fixture() -> None:
    controls, _loader, _receiver = _fixture("launcher-preimport")
    source, manifest, local = launcher._preimport_manifests_v42r1(  # noqa: SLF001
        controls
    )
    assert manifest["source_commit"] == source["source_commit"]
    assert manifest["source_tree"] == source["source_tree"]
    assert local["source_manifest_id"] == source["source_manifest_id"]
    assert local["transport_manifest_id"] == manifest["transport_manifest_id"]


def _live_tcb_manifest() -> tuple[dict[str, Any], dict[str, tuple[str, str, str]]]:
    rows: list[dict[str, Any]] = []
    selected: dict[str, tuple[str, str, str]] = {}
    for relative in launcher.LOCAL_EFFECTFUL_TCB_PATHS:
        raw = (launcher.ROOT / relative).read_bytes()
        oid = launcher._git_blob_oid(raw)  # noqa: SLF001
        rows.append(
            {
                "relative_path": relative,
                "git_mode": "100644",
                "git_object_type": "blob",
                "git_blob_oid": oid,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        selected[relative] = ("100644", "blob", oid)
    return {"transport_facts": rows}, selected


def test_effectful_tcb_bytes_match_selected_git_and_transport_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, selected = _live_tcb_manifest()
    monkeypatch.setattr(
        launcher,
        "_selected_git_inventory_v42r1",
        lambda **_kwargs: dict(selected),
    )
    observed = launcher._read_and_verify_effectful_tcb_v42r1(  # noqa: SLF001
        manifest=manifest,
        source_commit="1" * 40,
        source_tree="2" * 40,
    )
    assert tuple(sorted(observed)) == launcher.LOCAL_EFFECTFUL_TCB_PATHS
    assert observed[launcher.LAUNCHER_SOURCE_RELATIVE] == (
        launcher.ROOT / launcher.LAUNCHER_SOURCE_RELATIVE
    ).read_bytes()


def test_effectful_tcb_live_drift_and_selected_tree_splice_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, selected = _live_tcb_manifest()
    monkeypatch.setattr(
        launcher,
        "_selected_git_inventory_v42r1",
        lambda **_kwargs: dict(selected),
    )
    original = launcher._read_relative_tcb_file_v42r1  # noqa: SLF001

    def drift(root_fd: int, relative: str) -> bytes:
        raw = original(root_fd, relative)
        if relative == launcher.SENDER_SOURCE_RELATIVE:
            return raw + b"# crossed\n"
        return raw

    monkeypatch.setattr(launcher, "_read_relative_tcb_file_v42r1", drift)
    with pytest.raises(
        launcher.V42PreformalSenderLauncherError,
        match="live local TCB bytes differ",
    ):
        launcher._read_and_verify_effectful_tcb_v42r1(  # noqa: SLF001
            manifest=manifest,
            source_commit="1" * 40,
            source_tree="2" * 40,
        )

    monkeypatch.setattr(launcher, "_read_relative_tcb_file_v42r1", original)
    crossed = dict(selected)
    crossed[launcher.JOURNAL_SOURCE_RELATIVE] = (
        "100644",
        "blob",
        "3" * 40,
    )
    monkeypatch.setattr(
        launcher,
        "_selected_git_inventory_v42r1",
        lambda **_kwargs: crossed,
    )
    with pytest.raises(
        launcher.V42PreformalSenderLauncherError,
        match="selected Git TCB fact differs",
    ):
        launcher._read_and_verify_effectful_tcb_v42r1(  # noqa: SLF001
            manifest=manifest,
            source_commit="1" * 40,
            source_tree="2" * 40,
        )


def test_verified_bytes_loader_ignores_valid_unchecked_malicious_pyc() -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-malicious-pyc-", dir="/tmp"
    ) as base:
        root = Path(base)
        package = root / "verified_probe"
        package.mkdir(mode=0o700)
        init_path = package / "__init__.py"
        payload_path = package / "payload.py"
        init_raw = b"PACKAGE_VALUE = 1\n"
        verified_raw = b"VALUE = 1\n"
        init_path.write_bytes(init_raw)
        payload_path.write_bytes(b"VALUE = 2\n")
        malicious_pyc = Path(
            py_compile.compile(
                str(payload_path),
                doraise=True,
                invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
            )
        )
        payload_path.write_bytes(verified_raw)
        assert malicious_pyc.is_file()

        module_paths = {
            "verified_probe": "verified_probe/__init__.py",
            "verified_probe.payload": "verified_probe/payload.py",
        }
        finder = launcher._VerifiedTcbMetaFinderV42r1(  # noqa: SLF001
            root=root,
            module_paths=module_paths,
            raw_by_path={
                "verified_probe/__init__.py": init_raw,
                "verified_probe/payload.py": verified_raw,
            },
        )
        sys.meta_path.insert(0, finder)
        try:
            imported = importlib.import_module("verified_probe.payload")
            assert imported.VALUE == 1
            assert imported.__cached__ is None
            assert imported.__file__ == str(payload_path)
            assert imported.__spec__.origin == str(payload_path)
            assert imported.__spec__.cached is None
            assert imported.__spec__.loader is finder.loaders[
                "verified_probe.payload"
            ]
            with pytest.raises(ImportError, match="unregistered local TCB"):
                importlib.import_module("verified_probe.unregistered")
        finally:
            sys.meta_path.remove(finder)
            sys.modules.pop("verified_probe.payload", None)
            sys.modules.pop("verified_probe", None)

        # Establish that the unchecked pyc is valid and malicious: the normal
        # path importer executes VALUE=2 from it even though source says 1.
        sys.path.insert(0, str(root))
        try:
            imported_from_path = importlib.import_module("verified_probe.payload")
            assert imported_from_path.VALUE == 2
            assert imported_from_path.__cached__ == str(malicious_pyc)
        finally:
            sys.path.remove(str(root))
            sys.modules.pop("verified_probe.payload", None)
            sys.modules.pop("verified_probe", None)


def test_production_module_closure_compiles_only_initial_verified_bytes() -> None:
    root = launcher.ROOT
    source = r'''
import ast
from pathlib import Path
import sys
import types

path = Path(sys.argv[1])
tree = ast.parse(path.read_bytes(), filename=str(path))
assert isinstance(tree.body[-1], ast.If)
tree.body.pop()
ast.fix_missing_locations(tree)
module = types.ModuleType("__main__")
module.__file__ = str(path)
module.__spec__ = None
sys.modules["__main__"] = module
exec(compile(tree, str(path), "exec"), module.__dict__, module.__dict__)
initial = {
    relative: (module.ROOT / relative).read_bytes()
    for relative in module.LOCAL_EFFECTFUL_TCB_PATHS
}
loaded = module._load_effectful_modules_v42r1(initial)
module._verify_effectful_surfaces_v42r1(loaded)
module._verify_loaded_module_inventory_v42r1(
    modules=loaded, direct_entry=True
)
assert all(
    loader.raw is loaded.tcb_raw_by_path[loader.relative_path]
    for loader in loaded.finder.loaders.values()
)
print("VERIFIED_BYTES_ONLY")
'''
    completed = subprocess.run(
        (
            launcher.LOCAL_PYTHON,
            "-I",
            "-S",
            "-B",
            "-c",
            source,
            str(launcher.SCRIPT_PATH),
        ),
        cwd=root,
        env={"LC_ALL": "C", "LANG": "C"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20.0,
    )
    assert completed.returncode == 0, completed.stderr.decode(
        "utf-8", errors="replace"
    )
    assert completed.stdout == b"VERIFIED_BYTES_ONLY\n"
    assert completed.stderr == b""


def test_pinned_execveat_uses_open_inode_across_path_swap_and_restore(
) -> None:
    source = r'''
import os
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(sys.argv[1])
sys.path[:0] = [str(root), str(root / "src")]
from scripts import launch_v42_preformal_upload_sender as launcher

before = len(os.listdir("/proc/self/fd"))
with tempfile.TemporaryDirectory(
    prefix="acfqp-v42-git-inode-swap-", dir="/tmp"
) as base:
    base_path = Path(base)
    live_path = base_path / "git"
    held_path = base_path / "git-held"
    shutil.copyfile(launcher.GIT_EXECUTABLE, live_path)
    os.chmod(live_path, 0o755)
    descriptor = os.open(
        live_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        os.replace(live_path, held_path)
        shutil.copyfile("/usr/bin/false", live_path)
        os.chmod(live_path, 0o755)
        observation = launcher._run_pinned_executable_v42r1(
            executable_fd=descriptor,
            argv=(str(live_path), "--version"),
            environment=dict(launcher._GIT_ENVIRONMENT),
            stdout_cap=4096,
            stderr_cap=4096,
            timeout_seconds=5.0,
        )
        assert observation.exec_succeeded is True
        assert observation.returncode == 0
        assert observation.stdout_raw == launcher.GIT_VERSION_STDOUT
        assert observation.stderr_raw == b""
        assert observation.stdout_eof is True
        assert observation.stderr_eof is True
    finally:
        os.close(descriptor)
        os.replace(held_path, live_path)
assert len(os.listdir("/proc/self/fd")) == before
print("PINNED_INODE_EXECUTED")
'''
    completed = subprocess.run(
        (
            launcher.LOCAL_PYTHON,
            "-I",
            "-S",
            "-B",
            "-c",
            source,
            str(launcher.ROOT),
        ),
        cwd=launcher.ROOT,
        env={"LC_ALL": "C", "LANG": "C"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20.0,
    )
    assert completed.returncode == 0, completed.stderr.decode(
        "utf-8", errors="replace"
    )
    assert completed.stdout == b"PINNED_INODE_EXECUTED\n"
    assert completed.stderr == b""


def test_pinned_exec_failure_timeout_overflow_close_fds_and_reap() -> None:
    source = r'''
import os
from pathlib import Path
import signal
import sys

root = Path(sys.argv[1])
sys.path[:0] = [str(root), str(root / "src")]
from scripts import launch_v42_preformal_upload_sender as launcher

before = len(os.listdir("/proc/self/fd"))
descriptor = os.open(
    launcher.LOCAL_PYTHON_REALPATH,
    os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
)
code = (
    "import os,time;"
    "os.write(1,b'o'*200000);"
    "os.write(2,b'e'*200000);"
    "time.sleep(30)"
)
try:
    observation = launcher._run_pinned_executable_v42r1(
        executable_fd=descriptor,
        argv=(
            launcher.LOCAL_PYTHON,
            "-I",
            "-S",
            "-B",
            "-c",
            code,
        ),
        environment={"LC_ALL": "C"},
        stdout_cap=1024,
        stderr_cap=1024,
        timeout_seconds=0.25,
    )
finally:
    os.close(descriptor)
assert observation.exec_succeeded is True
assert observation.timed_out is True
assert observation.returncode == -signal.SIGKILL
assert observation.stdout_overflow is True
assert observation.stderr_overflow is True
assert observation.stdout_eof is True
assert observation.stderr_eof is True
assert len(os.listdir("/proc/self/fd")) == before
print("TIMEOUT_REAP_FD_CLOSURE_OK")
'''
    completed = subprocess.run(
        (
            launcher.LOCAL_PYTHON,
            "-I",
            "-S",
            "-B",
            "-c",
            source,
            str(launcher.ROOT),
        ),
        cwd=launcher.ROOT,
        env={"LC_ALL": "C", "LANG": "C"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20.0,
    )
    assert completed.returncode == 0, completed.stderr.decode(
        "utf-8", errors="replace"
    )
    assert completed.stdout == b"TIMEOUT_REAP_FD_CLOSURE_OK\n"
    assert completed.stderr == b""


def test_fixed_git_rejects_nonempty_stderr_and_closes_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor, state = launcher._pin_fixed_git_v42r1()  # noqa: SLF001
    monkeypatch.setattr(
        launcher,
        "_pin_fixed_git_v42r1",
        lambda: (descriptor, state),
    )
    monkeypatch.setattr(
        launcher,
        "_run_pinned_executable_v42r1",
        lambda **_kwargs: launcher._PinnedProcessObservationV42r1(  # noqa: SLF001
            exec_succeeded=True,
            returncode=0,
            timed_out=False,
            stdout_raw=launcher.GIT_VERSION_STDOUT,
            stdout_total_byte_count=len(launcher.GIT_VERSION_STDOUT),
            stdout_overflow=False,
            stdout_eof=True,
            stderr_raw=b"warning\n",
            stderr_total_byte_count=8,
            stderr_overflow=False,
            stderr_eof=True,
        ),
    )
    with pytest.raises(
        launcher.V42PreformalSenderLauncherError,
        match="exact output contract",
    ):
        launcher._run_fixed_git_v42r1("--version")  # noqa: SLF001
    with pytest.raises(OSError):
        os.fstat(descriptor)


@dataclass(frozen=True)
class _FakeSenderResult:
    network_start: dict[str, Any] | None
    receipt: dict[str, Any] | None
    outcome: dict[str, Any]
    diagnostic_code: str
    child_returncode: int | None
    stdout_byte_count: int
    stdout_sha256: str | None
    stderr_byte_count: int
    stderr_sha256: str | None


def _fake_modules(
    *, diagnostic: str = "LOCAL_PRE_NETWORK_FAILURE"
) -> tuple[launcher._LoadedEffectfulModules, list[dict[str, Any]]]:  # noqa: SLF001
    calls: list[dict[str, Any]] = []

    def execute(**kwargs: Any) -> _FakeSenderResult:
        calls.append(kwargs)
        plan = kwargs["plan"]
        attempt = kwargs["attempt"]
        outcome = transport.build_preformal_upload_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome_class=transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE,
            abandonment_reason_code=transport.PREFORMAL_ABANDONMENT_REASON_LOCAL,
            control_raw_by_name=kwargs["control_raw_by_name"],
            loader_source_raw=kwargs["loader_source_raw"],
            receiver_source_raw=kwargs["receiver_source_raw"],
            predecessor_chain=kwargs["predecessor_chain"],
        )
        return _FakeSenderResult(
            network_start=None,
            receipt=None,
            outcome=outcome,
            diagnostic_code=diagnostic,
            child_returncode=None,
            stdout_byte_count=0,
            stdout_sha256=None,
            stderr_byte_count=0,
            stderr_sha256=None,
        )

    fake_sender = SimpleNamespace(
        V42PreformalSenderResult=_FakeSenderResult,
        execute_preformal_upload_v42r1=execute,
    )
    modules = launcher._LoadedEffectfulModules(  # noqa: SLF001
        transport=transport,
        journal=journal,
        sender=fake_sender,  # type: ignore[arg-type]
    )
    return modules, calls


def test_execute_helper_calls_sender_exactly_once_with_literal_empty_chain() -> None:
    controls, loader_raw, receiver_raw = _fixture("launcher-execute-once")
    token = _token("launcher-execute-token")
    modules, calls = _fake_modules()

    document = launcher._execute_once_v42r1(  # noqa: SLF001
        modules=modules,
        controls=controls,
        loader_raw=loader_raw,
        receiver_raw=receiver_raw,
        upload_token=token,
        preexisting_journal_state="ABSENT",
    )

    assert len(calls) == 1
    assert calls[0]["predecessor_chain"] == []
    assert calls[0]["plan"]["preformal_upload_ordinal"] == 1
    assert calls[0]["plan"]["upload_token_history"] == [token]
    assert document["predecessor_chain_length"] == 0
    raw = launcher._canonical_json_bytes(document)  # noqa: SLF001
    assert launcher._canonical_json_object(raw, "result") == document  # noqa: SLF001


@pytest.mark.parametrize(
    ("state", "diagnostic"),
    [
        ("POSTNETWORK_UNRESOLVED", "RECOVERED_POSTNETWORK_AS_AMBIGUOUS"),
        ("COMPLETE_RECEIPT_PENDING_OUTCOME", "RECOVERED_COMPLETE_RECEIPT"),
        ("TERMINAL", "RECOVERED_TERMINAL_JOURNAL"),
    ],
)
def test_posteffect_reentry_requires_exact_recovery_diagnostic(
    state: str, diagnostic: str
) -> None:
    controls, loader_raw, receiver_raw = _fixture("launcher-recovery-" + state)
    modules, calls = _fake_modules(diagnostic=diagnostic)
    document = launcher._execute_once_v42r1(  # noqa: SLF001
        modules=modules,
        controls=controls,
        loader_raw=loader_raw,
        receiver_raw=receiver_raw,
        upload_token=_token("launcher-recovery-token-" + state),
        preexisting_journal_state=state,
    )
    assert len(calls) == 1
    assert document["diagnostic_code"] == diagnostic

    crossed, crossed_calls = _fake_modules(diagnostic="COMPLETE_EXACT_RECEIPT")
    with pytest.raises(
        launcher.V42PreformalSenderLauncherError,
        match="reentry did not remain recovery-only",
    ):
        launcher._execute_once_v42r1(  # noqa: SLF001
            modules=crossed,
            controls=controls,
            loader_raw=loader_raw,
            receiver_raw=receiver_raw,
            upload_token=_token("launcher-recovery-token-" + state),
            preexisting_journal_state=state,
        )
    assert len(crossed_calls) == 1


def test_journal_inspection_accepts_only_the_five_registered_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controls, loader_raw, receiver_raw = _fixture("launcher-inspection")
    token = _token("launcher-inspection-token")
    plan = transport.build_preformal_upload_plan_v42r1(
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        upload_token=token,
        predecessor_chain=[],
    )
    attempt = transport.build_preformal_upload_attempt_v42r1(
        plan=plan,
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        predecessor_chain=[],
    )
    modules = launcher._LoadedEffectfulModules(  # noqa: SLF001
        transport=transport, journal=journal, sender=sender
    )

    monkeypatch.setattr(launcher, "_path_node_kind", lambda _path: "ABSENT")
    assert launcher._inspect_existing_journal_v42r1(  # noqa: SLF001
        modules=modules,
        plan=plan,
        attempt=attempt,
        controls=controls,
        loader_raw=loader_raw,
        receiver_raw=receiver_raw,
    ) == "ABSENT"

    monkeypatch.setattr(launcher, "_path_node_kind", lambda _path: "DIRECTORY")
    for state in (
        "PRE_NETWORK_PREFIX",
        "PRE_NETWORK_BASE",
        "POSTNETWORK_UNRESOLVED",
        "COMPLETE_RECEIPT_PENDING_OUTCOME",
        "TERMINAL",
    ):
        monkeypatch.setattr(
            journal,
            "inspect_preformal_upload_journal_v42r1",
            lambda **_kwargs: SimpleNamespace(state=state),
        )
        assert launcher._inspect_existing_journal_v42r1(  # noqa: SLF001
            modules=modules,
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_raw=loader_raw,
            receiver_raw=receiver_raw,
        ) == state

    monkeypatch.setattr(
        journal,
        "inspect_preformal_upload_journal_v42r1",
        lambda **_kwargs: SimpleNamespace(state="UNREGISTERED"),
    )
    with pytest.raises(
        launcher.V42PreformalSenderLauncherError, match="unknown state"
    ):
        launcher._inspect_existing_journal_v42r1(  # noqa: SLF001
            modules=modules,
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_raw=loader_raw,
            receiver_raw=receiver_raw,
        )


def test_real_terminal_same_token_reentry_never_prepares_an_ssh_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-launcher-terminal-", dir="/tmp"
    ) as base:
        transport_parent = Path(base)
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", transport_parent)
        controls, loader_raw, receiver_raw = _fixture("launcher-real-terminal")
        token = _token("launcher-real-terminal-token")
        context = {
            "control_raw_by_name": controls,
            "loader_source_raw": loader_raw,
            "receiver_source_raw": receiver_raw,
            "predecessor_chain": [],
        }
        plan = transport.build_preformal_upload_plan_v42r1(
            **context, upload_token=token
        )
        attempt = transport.build_preformal_upload_attempt_v42r1(
            **context, plan=plan
        )
        journal.publish_pre_network_journal_v42r1(
            **context, plan=plan, attempt=attempt
        )
        outcome = transport.build_preformal_upload_outcome_v42r1(
            **context,
            plan=plan,
            attempt=attempt,
            outcome_class=transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE,
            abandonment_reason_code=transport.PREFORMAL_ABANDONMENT_REASON_LOCAL,
        )
        journal.publish_outcome_v42r1(
            **context,
            plan=plan,
            attempt=attempt,
            outcome=outcome,
            receipt=None,
        )
        modules = launcher._LoadedEffectfulModules(  # noqa: SLF001
            transport=transport, journal=journal, sender=sender
        )
        state = launcher._inspect_existing_journal_v42r1(  # noqa: SLF001
            modules=modules,
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_raw=loader_raw,
            receiver_raw=receiver_raw,
        )
        assert state == "TERMINAL"

        def forbidden_child(*_args: Any, **_kwargs: Any) -> Any:
            raise AssertionError("terminal reentry attempted to prepare an SSH child")

        monkeypatch.setattr(sender, "_prepare_pinned_child", forbidden_child)
        document = launcher._execute_once_v42r1(  # noqa: SLF001
            modules=modules,
            controls=controls,
            loader_raw=loader_raw,
            receiver_raw=receiver_raw,
            upload_token=token,
            preexisting_journal_state=state,
        )
        assert document["diagnostic_code"] == "RECOVERED_TERMINAL_JOURNAL"
        assert document["outcome"] == outcome
