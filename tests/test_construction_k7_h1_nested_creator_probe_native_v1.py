from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import pickle
import shutil
import subprocess
import sys

import pytest

from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as role


HELPER = Path(__file__).with_name("_nested_creator_probe_subprocess.py")


def test_registered_native_role_replays_exact_static_elf_and_locked_claims() -> None:
    evidence = role.verify_nested_creator_supervisor_native_image_v1()
    assert evidence["source_sha256"] == hashlib.sha256(
        role.SOURCE_PATH.read_bytes()
    ).hexdigest()
    assert evidence["elf_sha256"] == hashlib.sha256(role.ROLE_ELF_BYTES).hexdigest()
    assert evidence["elf_byte_count"] == len(role.ROLE_ELF_BYTES)
    assert evidence["single_nested_pidfd_probe_only"] is True
    assert evidence["creator_wnowait_and_consuming_reap"] is True
    assert evidence["third_wait_requires_echild"] is True
    assert evidence["runtime_toolchain_invocation_present"] is False
    assert evidence["actual_process_birth_present"] is False
    assert evidence["five_birth_process_authority_present"] is False
    assert evidence["official_execution_allowed"] is False


def test_registered_role_memfd_is_exact_cloexec_and_immutable() -> None:
    descriptor = role.create_sealed_nested_creator_supervisor_memfd_v1()
    try:
        assert os.pread(descriptor, role.ELF_BYTE_COUNT + 1, 0) == role.ROLE_ELF_BYTES
        assert os.fstat(descriptor).st_size == role.ELF_BYTE_COUNT
        assert os.get_inheritable(descriptor) is False
        with pytest.raises(OSError):
            os.write(descriptor, b"x")
    finally:
        os.close(descriptor)


def test_frame_abi_is_exact_and_rejects_mutation() -> None:
    frame = probe.NativeProtocolFrameV1(
        role.OPCODES["PROBE_COMMAND"], 1, bytes(range(16)), 73, -5, 9, 11
    )
    assert len(frame.to_bytes()) == role.FRAME_BYTES == 64
    assert probe.NativeProtocolFrameV1.from_bytes(frame.to_bytes()) == frame
    changed = bytearray(frame.to_bytes())
    changed[0] ^= 1
    with pytest.raises(probe.ConstructionK7H1NestedCreatorProbeNativeV1Error):
        probe.NativeProtocolFrameV1.from_bytes(bytes(changed))


def test_runtime_authority_types_are_not_caller_mintable_or_copyable() -> None:
    with pytest.raises(probe.ConstructionK7H1NestedCreatorProbeNativeV1Error):
        probe.NestedCreatorProbeLiveSessionV1(
            supervisor_pid=1,
            supervisor_start_ticks=1,
            supervisor_pidfd=1,
            control_fd=1,
            guardian_pid=1,
            guardian_uid=1,
            guardian_gid=1,
            owner_pid=1,
            owner_thread_id=1,
            state="SUPERVISOR_READY",
        )
    facts = object.__new__(probe.NestedCreatorProbeRawFactsV1)
    with pytest.raises(probe.ConstructionK7H1NestedCreatorProbeNativeV1Error):
        copy.copy(facts)
    with pytest.raises(probe.ConstructionK7H1NestedCreatorProbeNativeV1Error):
        copy.deepcopy(facts)
    with pytest.raises(probe.ConstructionK7H1NestedCreatorProbeNativeV1Error):
        pickle.dumps(facts)


def test_import_and_verification_do_not_invoke_toolchain(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("production verifier invoked a toolchain")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    role.verify_nested_creator_supervisor_native_image_v1()


def test_registered_toolchain_rebuilds_exact_static_elf(tmp_path: Path) -> None:
    compiler = shutil.which("gcc")
    linker = shutil.which("ld")
    if compiler is None or linker is None:
        pytest.skip("registered native build toolchain is unavailable")
    compiler_version = subprocess.run(
        [compiler, "-dumpfullversion", "-dumpversion"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    linker_version = subprocess.run(
        [linker, "--version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    if compiler_version != "11.4.0" or linker_version != role.BUILD_TOOLCHAIN["ld"]:
        pytest.skip("host toolchain differs from the registered audit toolchain")
    output = tmp_path / "nested-creator-supervisor"
    subprocess.run(
        [
            compiler,
            *role.BUILD_ARGV[1:],
            "-o",
            os.fspath(output),
            os.fspath(role.SOURCE_PATH),
        ],
        check=True,
    )
    assert output.read_bytes() == role.ROLE_ELF_BYTES


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_non_guardian_creator_birth_and_reap() -> None:
    repository = HELPER.parent.parent
    completed = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--scope",
            "--collect",
            "-p",
            "Delegate=yes",
            "-p",
            "TasksMax=infinity",
            f"--working-directory={repository}",
            "env",
            f"PYTHONPATH={repository / 'src'}",
            sys.executable,
            os.fspath(HELPER),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=dict(os.environ),
        timeout=30,
    )
    import json

    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["probe_pid"] > 0
    assert result["supervisor_pid"] > 0
    assert result["probe_pid"] != result["supervisor_pid"]
    assert result["guardian_waitid_errno"] == 10
    assert result["live_population"] == 2
    assert result["post_reap_population"] == 1
    assert result["creator_reap_opcode"] == role.OPCODES["PROBE_REAP"]
    assert result["supervisor_reap"] is True
    assert result["two_birth_prefix_authority_present"] is False
