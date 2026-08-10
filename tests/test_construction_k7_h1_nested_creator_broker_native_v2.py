from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

from acfqp import construction_k7_h1_nested_creator_broker_native_v2 as role


HELPER = Path(__file__).with_name("_nested_creator_broker_role_v2_subprocess.py")


def test_static_source_elf_creator_grammar_and_claim_locks() -> None:
    evidence = role.verify_nested_creator_broker_native_image_v2()
    assert evidence["source_sha256"] == hashlib.sha256(
        role.SOURCE_PATH.read_bytes()
    ).hexdigest()
    assert evidence["elf_sha256"] == hashlib.sha256(role.ROLE_ELF_BYTES).hexdigest()
    assert evidence["elf_byte_count"] == len(role.ROLE_ELF_BYTES)
    assert evidence["control_fd"] == 3
    assert evidence["role_slots"] == {"WORKER": 1, "BUSINESS": 2}
    assert evidence["create_role_sequences"] == {"WORKER": 2, "BUSINESS": 3}
    assert evidence["create_role_rights"] == [
        "GUARDIAN_SUPPLIED_CGROUP_V2_DIRECTORY",
        "WRITABLE_SHARED_PID_CELL_MEMFD",
        "SEALED_LINUX_X86_64_ET_EXEC_ELF_MEMFD",
        "GUARDIAN_SUPPLIED_SOCK_SEQPACKET_ENDPOINT",
    ]
    assert evidence["shutdown_sequence"] == 4
    assert evidence["general_four_right_creator_grammar_implementation_present"] is True
    assert evidence["clone3_execveat_pidfd_creator_implementation_present"] is True
    assert evidence["creator_wnowait_consuming_reap_implementation_present"] is True
    assert evidence["runtime_toolchain_invocation_present"] is False
    assert evidence["broker_created_by_supervisor_observed"] is False
    assert evidence["worker_role_birth_observed"] is False
    assert evidence["business_role_birth_observed"] is False
    assert evidence["channel_independence_authority_present"] is False
    assert evidence["role_image_slot_identity_authority_present"] is False
    assert evidence["one_shot_leaf_authority_present"] is False
    assert evidence["failure_closure_authority_present"] is False
    assert evidence["three_birth_prefix_authority_present"] is False
    assert evidence["five_birth_process_authority_present"] is False
    assert evidence["official_execution_allowed"] is False


def test_mutable_abi_build_rights_and_claim_attacks_are_rejected(
    monkeypatch,
) -> None:
    with monkeypatch.context() as attack:
        changed = dict(role.OPCODES)
        changed["BROKER_READY"], changed["BROKER_GO"] = (
            changed["BROKER_GO"],
            changed["BROKER_READY"],
        )
        attack.setattr(role, "OPCODES", changed)
        with pytest.raises(role.ConstructionK7H1NestedCreatorBrokerNativeV2Error):
            role.verify_nested_creator_broker_native_image_v2()
    with monkeypatch.context() as attack:
        attack.setattr(role, "CREATE_ROLE_RIGHTS", ("A", "B", "C", "D"))
        with pytest.raises(role.ConstructionK7H1NestedCreatorBrokerNativeV2Error):
            role.verify_nested_creator_broker_native_image_v2()
    with monkeypatch.context() as attack:
        attack.setattr(
            role, "GENERAL_FOUR_RIGHT_CREATOR_GRAMMAR_IMPLEMENTATION_PRESENT", False
        )
        with pytest.raises(role.ConstructionK7H1NestedCreatorBrokerNativeV2Error):
            role.verify_nested_creator_broker_native_image_v2()
    with monkeypatch.context() as attack:
        attack.setattr(role, "BUILD_ARGV", (*role.BUILD_ARGV, "-DATTACK"))
        with pytest.raises(role.ConstructionK7H1NestedCreatorBrokerNativeV2Error):
            role.verify_nested_creator_broker_native_image_v2()
    with monkeypatch.context() as attack:
        attack.setattr(role, "REQUIRED_SEALS", role.REQUIRED_SEALS ^ role.F_SEAL_WRITE)
        with pytest.raises(role.ConstructionK7H1NestedCreatorBrokerNativeV2Error):
            role.verify_nested_creator_broker_native_image_v2()
    with monkeypatch.context() as attack:
        attack.setattr(role, "_FRAME", struct.Struct("<64s"))
        with pytest.raises(role.ConstructionK7H1NestedCreatorBrokerNativeV2Error):
            role.verify_nested_creator_broker_native_image_v2()
    with monkeypatch.context() as attack:
        attack.setattr(role, "CHANNEL_INDEPENDENCE_AUTHORITY_PRESENT", True)
        with pytest.raises(role.ConstructionK7H1NestedCreatorBrokerNativeV2Error):
            role.verify_nested_creator_broker_native_image_v2()


def test_four_right_labels_do_not_claim_unproved_semantics() -> None:
    evidence = role.verify_nested_creator_broker_native_image_v2()
    serialized = "\n".join(evidence["create_role_rights"])
    assert "LEAF" not in serialized
    assert "ONE_SHOT" not in serialized
    assert "STATIC" not in serialized
    assert "INDEPENDENT" not in serialized
    assert evidence["same_endpoint_inode_alias_rejection_present"] is True
    assert evidence["channel_independence_authority_present"] is False
    assert evidence["role_image_slot_identity_authority_present"] is False


def test_frame_abi_round_trip_and_mutation_rejection() -> None:
    frame = role.BrokerRoleFrameV2(
        role.OPCODES["CREATE_ROLE"],
        role.CREATE_ROLE_SEQUENCES["WORKER"],
        bytes(range(16)),
        101,
        fact_a=role.ROLE_SLOTS["WORKER"],
    )
    raw = frame.to_bytes()
    assert len(raw) == role.FRAME_BYTES == 64
    assert role.BrokerRoleFrameV2.from_bytes(raw) == frame
    changed = bytearray(raw)
    changed[0] ^= 1
    with pytest.raises(role.ConstructionK7H1NestedCreatorBrokerNativeV2Error):
        role.BrokerRoleFrameV2.from_bytes(bytes(changed))


def test_sealed_role_image_is_exact_cloexec_and_immutable() -> None:
    descriptor = role.create_sealed_nested_creator_broker_memfd_v2()
    try:
        assert os.pread(descriptor, role.ELF_BYTE_COUNT + 1, 0) == role.ROLE_ELF_BYTES
        assert os.fstat(descriptor).st_size == role.ELF_BYTE_COUNT
        assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        assert fcntl.fcntl(descriptor, role.F_GET_SEALS) == role.REQUIRED_SEALS
        with pytest.raises(OSError):
            os.write(descriptor, b"x")
    finally:
        os.close(descriptor)


def test_import_and_verifier_do_not_invoke_toolchain(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("BROKER V2 verifier invoked a toolchain")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    role.verify_nested_creator_broker_native_image_v2()


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
    output = tmp_path / "nested-creator-broker-v2"
    subprocess.run(
        [compiler, *role.BUILD_ARGV[1:], "-o", output, role.SOURCE_PATH],
        check=True,
    )
    assert output.read_bytes() == role.ROLE_ELF_BYTES


def test_real_direct_exec_ready_go_shutdown_lifecycle() -> None:
    repository = HELPER.parent.parent
    completed = subprocess.run(
        [sys.executable, os.fspath(HELPER), "SUCCESS"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.fspath(repository / "src")},
        timeout=15,
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["broker_pid"] > 0
    assert result["guardian_pid"] > 0
    assert result["broker_pid"] != result["guardian_pid"]
    assert result["ready_opcode"] == role.OPCODES["BROKER_READY"]
    assert result["go_echo_opcode"] == role.OPCODES["BROKER_GO_ECHO"]
    assert result["bye_opcode"] == role.OPCODES["BROKER_BYE"]
    assert result["sequences"] == [0, 1, 4]
    assert result["credential_pids"] == [result["broker_pid"]] * 3
    assert result["exit_status"] == 0
    assert result["direct_exec_ready_go_shutdown_observed"] is True
    assert result["create_role_branch_exercised"] is False
    assert result["broker_created_by_supervisor_observed"] is False
    assert result["channel_independence_authority_present"] is False
    assert result["role_image_slot_identity_authority_present"] is False
    assert result["one_shot_leaf_authority_present"] is False
    assert result["failure_closure_authority_present"] is False
    assert result["three_birth_prefix_authority_present"] is False
    assert result["five_birth_process_authority_present"] is False


def test_real_sibling_sender_credentials_are_rejected() -> None:
    repository = HELPER.parent.parent
    completed = subprocess.run(
        [sys.executable, os.fspath(HELPER), "WRONG_CREDENTIAL"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.fspath(repository / "src")},
        timeout=15,
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["broker_pid"] > 0
    assert result["guardian_pid"] > 0
    assert result["sibling_pid"] > 0
    assert len(
        {result["broker_pid"], result["guardian_pid"], result["sibling_pid"]}
    ) == 3
    assert result["failure_opcode"] == role.OPCODES["PROTOCOL_FAILURE"]
    assert result["failure_sequence"] == 1
    assert result["failure_status"] < 0
    assert result["broker_exit_status"] != 0
    assert result["wrong_credential_rejected"] is True
