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

from acfqp import construction_k7_h1_nested_creator_leaf_roles_native_v2 as role


HELPER = Path(__file__).with_name("_nested_creator_leaf_roles_v2_subprocess.py")


def _run(role_name: str, mode: str) -> dict[str, object]:
    repository = HELPER.parent.parent
    completed = subprocess.run(
        [sys.executable, os.fspath(HELPER), role_name, mode],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.fspath(repository / "src")},
        timeout=15,
    )
    return json.loads(completed.stdout.splitlines()[-1])


def test_static_source_images_protocol_and_claim_locks() -> None:
    evidence = role.verify_nested_creator_leaf_role_images_v2()
    assert evidence["source_sha256"] == hashlib.sha256(role.SOURCE_PATH.read_bytes()).hexdigest()
    assert evidence["worker_elf_sha256"] == hashlib.sha256(role.WORKER_ELF_BYTES).hexdigest()
    assert evidence["business_elf_sha256"] == hashlib.sha256(role.BUSINESS_ELF_BYTES).hexdigest()
    assert role.WORKER_ELF_BYTES != role.BUSINESS_ELF_BYTES
    assert evidence["role_slots"] == {"WORKER": 1, "BUSINESS": 2}
    assert evidence["external_guardian_credential_check_implementation_present"] is True
    assert evidence["actual_parent_pid_binding_implementation_present"] is True
    assert evidence["pdeathsig_parent_lifetime_binding_implementation_present"] is True
    assert evidence["registered_broker_image_attestation_present"] is False
    assert evidence["direct_lifecycle_observed"] is False
    assert evidence["worker_resource_semantics_present"] is False
    assert evidence["business_resource_semantics_present"] is False
    assert evidence["worker_role_birth_by_broker_observed"] is False
    assert evidence["business_role_birth_by_broker_observed"] is False
    assert evidence["actual_observed_e3_v2_completion_present"] is False
    assert evidence["e4_v2_completion_present"] is False
    assert evidence["production_shared_resource_receipts_present"] is False
    assert evidence["formal_v7_authority_present"] is False
    assert evidence["official_execution_allowed"] is False


def test_abi_build_slot_seal_and_claim_mutations_are_rejected(monkeypatch) -> None:
    attacks = (
        ("OPCODES", {**role.OPCODES, "ROLE_READY": 99}),
        ("ROLE_SLOTS", {"WORKER": 2, "BUSINESS": 1}),
        ("BUILD_ARGV_PREFIX", (*role.BUILD_ARGV_PREFIX, "-DATTACK")),
        ("REQUIRED_SEALS", role.REQUIRED_SEALS ^ role.F_SEAL_WRITE),
        ("_FRAME", struct.Struct("<64s")),
        ("WORKER_RESOURCE_SEMANTICS_PRESENT", True),
        ("REGISTERED_BROKER_IMAGE_ATTESTATION_PRESENT", True),
        ("ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT", True),
        ("FORMAL_V7_AUTHORITY_PRESENT", True),
        ("OFFICIAL_EXECUTION_ALLOWED", True),
    )
    for attribute, value in attacks:
        with monkeypatch.context() as attack:
            attack.setattr(role, attribute, value)
            with pytest.raises(role.ConstructionK7H1NestedCreatorLeafRolesNativeV2Error):
                role.verify_nested_creator_leaf_role_images_v2()


def test_frame_abi_roundtrip_and_prefix_mutation_rejection() -> None:
    frame = role.LeafRoleFrameV2(
        role.OPCODES["ROLE_GO"], 1, bytes(range(16)), 101,
        role.ROLE_SLOTS["WORKER"], 99,
    )
    raw = frame.to_bytes()
    assert len(raw) == role.FRAME_BYTES == 64
    assert role.LeafRoleFrameV2.from_bytes(raw) == frame
    changed = bytearray(raw)
    changed[0] ^= 1
    with pytest.raises(role.ConstructionK7H1NestedCreatorLeafRolesNativeV2Error):
        role.LeafRoleFrameV2.from_bytes(bytes(changed))


@pytest.mark.parametrize("role_name", ["WORKER", "BUSINESS"])
def test_sealed_role_images_are_exact_cloexec_and_immutable(role_name: str) -> None:
    descriptor = role.create_sealed_nested_creator_leaf_role_memfd_v2(role_name)
    try:
        expected = role.WORKER_ELF_BYTES if role_name == "WORKER" else role.BUSINESS_ELF_BYTES
        assert os.pread(descriptor, role.ELF_BYTE_COUNT + 1, 0) == expected
        assert os.fstat(descriptor).st_size == role.ELF_BYTE_COUNT
        assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        assert fcntl.fcntl(descriptor, role.F_GET_SEALS) == role.REQUIRED_SEALS
        with pytest.raises(OSError):
            os.write(descriptor, b"x")
    finally:
        os.close(descriptor)


def test_import_and_verifier_do_not_invoke_toolchain(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("leaf V2 verifier invoked a toolchain")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    role.verify_nested_creator_leaf_role_images_v2()


@pytest.mark.parametrize("role_name,slot,image", [
    ("WORKER", 1, role.WORKER_ELF_BYTES),
    ("BUSINESS", 2, role.BUSINESS_ELF_BYTES),
])
def test_registered_toolchain_rebuilds_both_exact_images(
    tmp_path: Path, role_name: str, slot: int, image: bytes,
) -> None:
    compiler = shutil.which("gcc")
    linker = shutil.which("ld")
    if compiler is None or linker is None:
        pytest.skip("registered native build toolchain is unavailable")
    compiler_version = subprocess.run(
        [compiler, "-dumpfullversion", "-dumpversion"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    linker_version = subprocess.run(
        [linker, "--version"], check=True, capture_output=True, text=True,
    ).stdout.splitlines()[0]
    if compiler_version != "11.4.0" or linker_version != role.BUILD_TOOLCHAIN["ld"]:
        pytest.skip("host toolchain differs from the registered audit toolchain")
    output = tmp_path / role_name.lower()
    subprocess.run(
        [compiler, *role.BUILD_ARGV_PREFIX[1:], f"-DACFQP_LEAF_ROLE_SLOT={slot}",
         "-o", output, role.SOURCE_PATH],
        check=True,
    )
    assert output.read_bytes() == image


@pytest.mark.parametrize("role_name", ["WORKER", "BUSINESS"])
def test_real_direct_lifecycle_has_distinct_guardian_and_actual_parent_surrogate(
    role_name: str,
) -> None:
    result = _run(role_name, "SUCCESS")
    assert result["role"] == role_name
    assert len({
        result["guardian_pid"], result["parent_surrogate_pid"], result["leaf_pid"],
    }) == 3
    assert result["ready_parent_pid"] == result["parent_surrogate_pid"]
    assert result["ready_role_slot"] == role.ROLE_SLOTS[role_name]
    assert result["sequences"] == [0, 1, 2]
    assert result["credential_pids"] == [result["leaf_pid"]] * 3
    assert result["parent_surrogate_exit_status"] == 0
    assert role.CONTROL_FD in result["leaf_open_fds_after_ready"]
    assert not any(descriptor >= 4 for descriptor in result["leaf_open_fds_after_ready"])
    assert result["direct_lifecycle_observed"] is True
    assert result["external_guardian_distinct_from_actual_parent"] is True
    assert result["registered_broker_image_attestation_present"] is False
    assert result["worker_resource_semantics_present"] is False
    assert result["business_resource_semantics_present"] is False
    assert result["actual_observed_e3_v2_completion_present"] is False
    assert result["e4_v2_completion_present"] is False
    assert result["formal_v7_authority_present"] is False
    assert result["official_execution_allowed"] is False


@pytest.mark.parametrize("role_name", ["WORKER", "BUSINESS"])
def test_real_sibling_guardian_credential_attack_is_rejected(role_name: str) -> None:
    result = _run(role_name, "WRONG_CREDENTIAL")
    assert len({
        result["guardian_pid"], result["parent_surrogate_pid"],
        result["leaf_pid"], result["sibling_pid"],
    }) == 4
    assert result["failure_opcode"] == role.OPCODES["PROTOCOL_FAILURE"]
    assert result["failure_sequence"] == 1
    assert result["failure_status"] < 0
    assert result["failure_credential_pid"] == result["leaf_pid"]
    assert result["parent_surrogate_exit_status"] != 0
    assert result["wrong_credential_rejected"] is True


@pytest.mark.parametrize("role_name", ["WORKER", "BUSINESS"])
def test_real_wrong_role_slot_command_is_rejected(role_name: str) -> None:
    result = _run(role_name, "WRONG_SLOT")
    assert result["wrong_slot"] != role.ROLE_SLOTS[role_name]
    assert result["failure_opcode"] == role.OPCODES["PROTOCOL_FAILURE"]
    assert result["failure_sequence"] == 1
    assert result["failure_status"] < 0
    assert result["failure_credential_pid"] == result["leaf_pid"]
    assert result["parent_surrogate_exit_status"] != 0
    assert result["wrong_slot_rejected"] is True


@pytest.mark.parametrize("role_name", ["WORKER", "BUSINESS"])
def test_real_collapsed_guardian_parent_identity_is_rejected(role_name: str) -> None:
    result = _run(role_name, "COLLAPSED_IDENTITY")
    assert result["guardian_pid"] != result["leaf_pid"]
    assert result["received_bytes"] == 0
    assert result["leaf_exit_status"] == 117
    assert result["collapsed_guardian_parent_identity_rejected"] is True


@pytest.mark.parametrize("role_name", ["WORKER", "BUSINESS"])
def test_real_actual_parent_death_sigkills_blocked_leaf(role_name: str) -> None:
    result = _run(role_name, "PARENT_DEATH")
    assert result["parent_surrogate_pid"] != result["leaf_pid"]
    assert result["parent_surrogate_exit_status"] == 0
    assert result["leaf_pidfd_readable_after_parent_exit"] is True
    assert result["leaf_waited_pid"] == result["leaf_pid"]
    assert result["leaf_was_signaled"] is True
    assert result["leaf_term_signal"] == 9
    assert result["pdeathsig_parent_lifetime_binding_observed"] is True


@pytest.mark.parametrize("role_name", ["WORKER", "BUSINESS"])
@pytest.mark.parametrize("mode,rights_count", [
    ("SCM_RIGHTS", 1),
    ("ANCILLARY_TRUNCATION", 32),
])
def test_real_extra_or_truncated_rights_ancillary_is_rejected_without_continuation(
    role_name: str, mode: str, rights_count: int,
) -> None:
    result = _run(role_name, mode)
    assert result["attack_mode"] == mode
    assert result["sent_rights_count"] == rights_count
    assert result["failure_opcode"] == role.OPCODES["PROTOCOL_FAILURE"]
    assert result["failure_sequence"] == 1
    assert result["failure_status"] < 0
    assert result["failure_credential_pid"] == result["leaf_pid"]
    assert result["parent_surrogate_exit_status"] != 0
    assert result["ancillary_rejected"] is True
