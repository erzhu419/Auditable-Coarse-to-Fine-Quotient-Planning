from __future__ import annotations

import copy
import fcntl
import hashlib
import os
from pathlib import Path
import pickle
import shutil
import socket
import subprocess
import sys

import pytest

from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as role


HELPER = Path(__file__).with_name("_nested_creator_probe_subprocess.py")


def _run_real_helper(mode: str) -> dict[str, object]:
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
            mode,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=dict(os.environ),
        timeout=30,
    )
    import json

    return json.loads(completed.stdout.splitlines()[-1])


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
    assert "verify_nested_creator_live_session_v1" in probe.__all__


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


def test_session_begin_rejects_non_cloexec_before_registration() -> None:
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    pidfd = os.pidfd_open(os.getpid(), 0)
    try:
        fcntl.fcntl(parent.fileno(), fcntl.F_SETFD, 0)
        with pytest.raises(
            probe.ConstructionK7H1NestedCreatorProbeNativeV1Error,
            match="descriptor contract changed",
        ):
            probe.begin_nested_creator_supervisor_session_v1(
                supervisor_pid=os.getpid() + 1,
                supervisor_pidfd=pidfd,
                control_fd=parent.fileno(),
            )
        assert len(probe._LIVE_SESSIONS) == 0  # noqa: SLF001
    finally:
        os.close(pidfd)
        parent.close()
        child.close()


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
    observed = object.__new__(probe.NestedCreatorProbeObservedFactsV2)
    with pytest.raises(probe.ConstructionK7H1NestedCreatorProbeNativeV1Error):
        copy.copy(observed)
    with pytest.raises(probe.ConstructionK7H1NestedCreatorProbeNativeV1Error):
        copy.deepcopy(observed)
    with pytest.raises(probe.ConstructionK7H1NestedCreatorProbeNativeV1Error):
        pickle.dumps(observed)


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
    result = _run_real_helper("SUCCESS")
    assert result["probe_pid"] > 0
    assert result["supervisor_pid"] > 0
    assert result["probe_pid"] != result["supervisor_pid"]
    assert result["guardian_waitid_errno"] == 10
    assert result["live_population"] == 2
    assert result["post_reap_population"] == 1
    assert result["creator_reap_opcode"] == role.OPCODES["PROBE_REAP"]
    assert result["supervisor_reap"] is True
    assert result["two_birth_prefix_authority_present"] is False
    assert result["ready_payload_hex_bytes"] == role.FRAME_BYTES
    assert result["ready_credential_pid"] == result["supervisor_pid"]
    assert result["receive_count"] == 5
    assert result["receive_opcodes"] == [
        role.OPCODES["PROBE_PARENT_RETURN"],
        role.OPCODES["CHILD_CELL_WITHDRAWN"],
        role.OPCODES["CHILD_GATE_READY"],
        role.OPCODES["CHILD_RELEASE_ECHO"],
        role.OPCODES["PROBE_REAP"],
    ]
    assert result["receive_credential_pids"] == [
        result["supervisor_pid"],
        result["probe_pid"],
        result["probe_pid"],
        result["probe_pid"],
        result["supervisor_pid"],
    ]
    assert result["receive_rights_counts"] == [1, 0, 0, 0, 0]
    assert result["all_payloads_exact_frame_size"] is True
    assert result["all_payload_hashes_match"] is True
    assert result["all_decoded_frames_match"] is True
    assert result["all_ancillary_semantics_match"] is True
    assert result["installed_pidfd_pid"] == result["probe_pid"]
    assert result["installed_pidfd_cloexec"] is True
    assert result["installed_pidfd_descriptor_flags"] & 1 == 1
    assert result["mutation_rejections"] == 2
    assert result["live_verifier_before_state"] == "SUPERVISOR_READY"
    assert result["live_verifier_after_state"] == "SUPERVISOR_READY"
    assert result["live_verifier_parent_pid"] > 0
    assert result["live_verifier_pidfd_pid"] == result["supervisor_pid"]
    assert result["live_verifier_control_cloexec"] is True
    assert result["live_verifier_verified"] is True
    assert result["live_verifier_mutation_rejected"] is True
    assert result["control_substitution_rejected"] is True
    assert result["control_abort_substitution_rejected"] is True
    assert result["pidfd_substitution_rejected"] is True
    assert result["pidfd_abort_substitution_rejected"] is True
    assert result["finish_pidfd_substitution_rejected"] is True
    assert result["finish_attack_victim_remained_waitable"] is True
    assert result["restored_control_device"] == result["frozen_control_device"]
    assert result["restored_control_inode"] == result["frozen_control_inode"]
    assert result["restored_pidfd_device"] == result["frozen_pidfd_device"]
    assert result["restored_pidfd_inode"] == result["frozen_pidfd_inode"]
    assert result["frozen_control_peer_pid"] > 0
    assert result["terminal_trusted_record_registry_count"] == 0
    assert result["atfork_child"] == {
        "control_fd_closed": True,
        "trusted_record_registry_count": 0,
        "pidfd_closed": True,
        "registry_count": 0,
        "session_state": "FORK_CHILD_POISONED",
        "session_control_fd": -1,
        "session_pidfd": -1,
        "verify_rejected": True,
        "supervisor_not_child": True,
    }


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_between_registration_fault_leaves_no_half_registry() -> None:
    result = _run_real_helper("AFTER_SESSION_RECORD_REGISTER")
    assert result == {
        "mode": "AFTER_SESSION_RECORD_REGISTER",
        "begin_error_type": (
            "ConstructionK7H1NestedCreatorProbeNativeV1Error"
        ),
        "trusted_record_registry_count": 0,
    }


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
@pytest.mark.parametrize(
    ("mode", "expected_state"),
    [
        ("AFTER_INNER_CONTROL_CLOSE", "SUPERVISOR_RELEASED_TO_EXIT"),
        ("AFTER_INNER_PIDFD_CLOSE", "CLOSED"),
        ("AFTER_INNER_PIDFD_CONSUME", "CLOSED"),
    ],
)
def test_terminal_inner_close_fault_finishes_forward_and_retries(
    mode: str, expected_state: str
) -> None:
    result = _run_real_helper(mode)
    assert result["first_error_type"] == (
        "ConstructionK7H1NestedCreatorProbeNativeV1Error"
    )
    assert result["partial_state"] == expected_state
    assert result["partial_fd"] == -1
    assert result["retry_idempotent"] is True
    assert result["supervisor_reaped"] is True
    assert result["trusted_record_registry_count"] == 0


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
@pytest.mark.parametrize(
    "mode",
    [
        "ABORT_AFTER_INNER_CONTROL_CLOSE",
        "ABORT_AFTER_INNER_PIDFD_CLOSE",
    ],
)
def test_abort_inner_close_fault_is_recoverable_and_idempotent(mode: str) -> None:
    result = _run_real_helper(mode)
    assert result["first_error_type"] == (
        "ConstructionK7H1NestedCreatorProbeNativeV1Error"
    )
    assert result["partial_control_fd"] == -1
    if mode.endswith("CONTROL_CLOSE"):
        assert result["partial_state"] == (
            "ABORT_CONTROL_CLOSED_CLEANUP_REQUIRED"
        )
    else:
        assert result["partial_state"] == "ABORTED_CLOSED"
        assert result["partial_pidfd"] == -1
    assert result["retry_idempotent"] is True
    assert result["trusted_record_registry_count"] == 0


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_abort_rejects_unrelated_child_without_reaping_it() -> None:
    result = _run_real_helper("ABORT_UNRELATED_CHILD")
    assert result["unrelated_rejected"] is True
    assert result["unrelated_still_live"] is True
    assert result["unrelated_reaped_by_test"] is True
    assert result["session_still_live"] is True
    assert result["abort_idempotent"] is True
    assert result["trusted_record_registry_count"] == 0


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_before_parent_return_unknown_probe_is_recovered_exactly() -> None:
    result = _run_real_helper("BEFORE_PARENT_RETURN")
    assert result["first_error_type"] == (
        "ConstructionK7H1NestedCreatorProbeNativeV1Error"
    )
    assert result["unknown_probe_pid"] > 0
    assert result["unknown_probe_pid"] in result["reaped_pids"]
    assert result["session_fds_closed"] is True
    assert result["cgroup_empty"] is True
    assert result["trusted_record_registry_count"] == 0


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_abort_rejects_fake_control_member_even_if_session_claims_it() -> None:
    result = _run_real_helper("ABORT_FAKE_CONTROL_MEMBER")
    assert result["fake_member_rejected"] is True
    assert result["fake_member_still_live"] is True
    assert result["fake_member_reaped_by_test"] is True
    assert result["abort_closed"] is True
    assert result["trusted_record_registry_count"] == 0


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_wrong_cgroup_before_command_does_not_poison_cleanup_lease() -> None:
    result = _run_real_helper("WRONG_CGROUP_BEFORE_COMMAND")
    assert result["first_error_type"] == (
        "ConstructionK7H1NestedCreatorProbeNativeV1Error"
    )
    assert result["abort_closed"] is True
    assert result["trusted_record_registry_count"] == 0


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_atfork_does_not_close_reused_already_closed_control_number() -> None:
    result = _run_real_helper("ATFORK_REUSED_CLOSED_CONTROL")
    assert result["fork_clean"] is True
    assert result["child_report"] == {
        "replacement_open": True,
        "inherited_pidfd_closed": True,
        "session_state": "FORK_CHILD_POISONED",
    }
    assert result["supervisor_reaped"] is True
    assert result["trusted_record_registry_count"] == 0
