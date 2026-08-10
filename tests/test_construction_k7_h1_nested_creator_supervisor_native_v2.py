from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v2 as v2


HELPER = Path(__file__).with_name(
    "_nested_creator_supervisor_v2_prefix_subprocess.py"
)


def test_v2_source_image_additive_abi_and_negative_claim_locks() -> None:
    evidence = v2.verify_nested_creator_supervisor_native_image_v2()
    assert evidence["source_sha256"] == hashlib.sha256(
        v2.SOURCE_PATH.read_bytes()
    ).hexdigest()
    assert evidence["v1_source_dependency_sha256"] == hashlib.sha256(
        v2.V1_SOURCE_PATH.read_bytes()
    ).hexdigest()
    assert evidence["elf_sha256"] == hashlib.sha256(v2.ROLE_ELF_BYTES).hexdigest()
    assert evidence["elf_byte_count"] == len(v2.ROLE_ELF_BYTES)
    assert tuple(v2.OPCODES.items())[:12] == tuple(v1.OPCODES.items())
    assert tuple(v2.OPCODES.values()) == tuple(range(1, 18))
    assert evidence["broker_command_sequence"] == 2
    assert evidence["broker_shutdown_sequence"] == 3
    assert evidence["direct_shutdown_sequence"] == 2
    assert evidence["broker_command_descriptor_roles"] == [
        "CONTROL_O_PATH_LEAF_GRANT",
        "PRISTINE_PID_CELL_MEMFD",
        "SEALED_BROKER_ELF_MEMFD",
        "BROKER_CHILD_SOCK_SEQPACKET_ENDPOINT",
    ]
    assert evidence["broker_parent_return_rights"] == ["CREATOR_PIDFD"]
    assert evidence["broker_elf_byte_count"] == 12720
    assert evidence["broker_elf_required_seals"] == 15
    assert evidence["broker_reap_semantics"] == "WNOWAIT_THEN_CONSUME_THEN_ECHILD"
    assert (
        evidence["broker_failure_semantics"]
        == (
            "PIDFD_KILL_OR_IMMEDIATE_DIRECT_CHILD_FALLBACK_THEN_CONSUME_"
            "THEN_ECHILD_THEN_CLOSE"
        )
    )
    assert [row["name"] for row in evidence["broker_frame_grammar"]] == [
        "BROKER_COMMAND",
        "BROKER_PARENT_RETURN",
        "BROKER_ACK",
        "BROKER_ACK_ECHO",
        "BROKER_REAP",
    ]
    assert [row["scm_rights_count"] for row in evidence["broker_frame_grammar"]] == [
        4,
        1,
        0,
        0,
        0,
    ]
    assert evidence["broker_clone_exec_reap_branch_implementation_present"] is True
    assert evidence["broker_descriptor_validation_implementation_present"] is True
    assert evidence["broker_cgroup_o_path_validation_implementation_present"] is True
    assert evidence["broker_controller_peercred_validation_implementation_present"] is True
    assert evidence["broker_failure_pidfd_convergence_implementation_present"] is True
    assert evidence["runtime_toolchain_invocation_present"] is False
    assert evidence["actual_supervisor_exec_observed"] is False
    assert evidence["actual_nested_pidfd_probe_birth_observed"] is False
    assert evidence["actual_broker_birth_observed"] is False
    assert evidence["three_birth_prefix_authority_present"] is False
    assert evidence["five_birth_process_authority_present"] is False
    assert evidence["official_execution_allowed"] is False
    assert evidence["official_scalar_cost"] is None
    assert evidence["official_N_break_even"] is None
    assert evidence["counter_completeness_gate"] == "NOT_RUN"
    assert evidence["workload_economics_gate"] == "NOT_RUN"


def test_v2_sealed_memfd_is_exact_cloexec_and_immutable() -> None:
    descriptor = v2.create_sealed_nested_creator_supervisor_memfd_v2()
    try:
        assert os.pread(descriptor, v2.ELF_BYTE_COUNT + 1, 0) == v2.ROLE_ELF_BYTES
        assert os.fstat(descriptor).st_size == v2.ELF_BYTE_COUNT
        assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        assert fcntl.fcntl(descriptor, v2.F_GET_SEALS) == v2.REQUIRED_SEALS
        with pytest.raises(OSError):
            os.write(descriptor, b"x")
    finally:
        os.close(descriptor)


def test_v2_verification_does_not_invoke_toolchain(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("production V2 verifier invoked a toolchain")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    v2.verify_nested_creator_supervisor_native_image_v2()


def test_v2_verifier_rejects_abi_and_claim_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(v2.OPCODES, "BROKER_REAP", 99)
    with pytest.raises(v2.ConstructionK7H1NestedCreatorSupervisorNativeV2Error):
        v2.verify_nested_creator_supervisor_native_image_v2()
    monkeypatch.setitem(v2.OPCODES, "BROKER_REAP", 17)
    monkeypatch.setattr(v2, "ACTUAL_BROKER_BIRTH_OBSERVED", True)
    with pytest.raises(
        v2.ConstructionK7H1NestedCreatorSupervisorNativeV2Error,
        match="claim locks changed",
    ):
        v2.verify_nested_creator_supervisor_native_image_v2()


@pytest.mark.parametrize(
    ("name", "mutated"),
    [
        ("FRAME_MAGIC", 0),
        ("FRAME_VERSION", 99),
        ("FRAME_BYTES", 63),
        ("REQUIRED_CLONE_FLAGS", 0),
        ("BROKER_ELF_BYTE_COUNT", 1),
        ("BROKER_ELF_REQUIRED_SEALS", 0),
        ("BROKER_PARENT_RETURN_RIGHTS", ("NOT_A_PIDFD",)),
        ("BROKER_ACK_DIRECTION", "WRONG"),
        ("BROKER_ACK_ECHO_DIRECTION", "WRONG"),
        ("BROKER_REAP_SEMANTICS", "WRONG"),
        ("BROKER_FAILURE_SEMANTICS", "WRONG"),
        ("BROKER_DESCRIPTOR_VALIDATION_IMPLEMENTATION_PRESENT", False),
        ("BROKER_CGROUP_O_PATH_VALIDATION_IMPLEMENTATION_PRESENT", False),
        ("BROKER_CONTROLLER_PEERCRED_VALIDATION_IMPLEMENTATION_PRESENT", False),
        ("BROKER_FAILURE_PIDFD_CONVERGENCE_IMPLEMENTATION_PRESENT", False),
    ],
)
def test_v2_verifier_rejects_each_registered_abi_mutation(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    mutated: object,
) -> None:
    monkeypatch.setattr(v2, name, mutated)
    with pytest.raises(v2.ConstructionK7H1NestedCreatorSupervisorNativeV2Error):
        v2.verify_nested_creator_supervisor_native_image_v2()


def test_registered_toolchain_rebuilds_exact_v2_static_elf(tmp_path: Path) -> None:
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
    if compiler_version != "11.4.0" or linker_version != v2.BUILD_TOOLCHAIN["ld"]:
        pytest.skip("host toolchain differs from the registered audit toolchain")
    output = tmp_path / "nested-creator-supervisor-v2"
    subprocess.run(
        [
            compiler,
            *v2.BUILD_ARGV[1:],
            "-o",
            os.fspath(output),
            os.fspath(v2.SOURCE_PATH),
        ],
        check=True,
    )
    assert output.read_bytes() == v2.ROLE_ELF_BYTES


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_v2_image_preserves_probe_reaped_direct_shutdown_raw_prefix() -> None:
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
        timeout=30,
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["birth_order"] == ["SUPERVISOR", "PIDFD_PROBE"]
    assert result["creator_by_slot"] == {
        "SUPERVISOR": "EXTERNAL_GUARDIAN",
        "PIDFD_PROBE": "SUPERVISOR",
    }
    assert result["maximum_observed_control_population"] == 2
    assert result["final_population"] == 0
    assert result["fd_count_restored"] is True
    assert result["subreaper_restored"] is True
    assert result["direct_children"] == ""
    assert result["live_session_count"] == 0
    assert result["target_two_birth_creator_chain_observed"] is True
    assert result["exact_two_birth_os_topology_observed"] is False
    assert result["exclusive_two_birth_topology_authority_present"] is False
    assert result["two_birth_prefix_authority_present"] is False


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_v2_supervisor_creates_controls_and_reaps_broker_raw_branch() -> None:
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
            "BROKER",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["birth_order"] == ["SUPERVISOR", "PIDFD_PROBE", "BROKER"]
    assert result["creator_by_slot"] == {
        "SUPERVISOR": "EXTERNAL_GUARDIAN",
        "PIDFD_PROBE": "SUPERVISOR",
        "BROKER": "SUPERVISOR",
    }
    assert result["supervisor_pid"] > 0
    assert result["broker_pid"] > 0
    assert result["broker_observed_parent_pid"] == result["supervisor_pid"]
    assert result["broker_pidfd_pid"] == result["broker_pid"]
    assert result["broker_pid_cell_value"] == result["broker_pid"]
    assert result["pre_broker_population"] == 1
    assert result["maximum_observed_control_population"] == 2
    assert result["post_broker_population"] == 1
    assert result["final_population"] == 0
    assert result["broker_reap_status"] == 0
    assert result["broker_reap_code"] == 1
    assert result["broker_reap_echild"] == 10
    assert result["guardian_echild_while_live"] == 10
    assert result["guardian_echild_after_reap"] == 10
    assert result["ack_echo_before_broker_shutdown"] is True
    assert result["abort_state"] == "ABORTED_CLOSED"
    assert result["fd_count_restored"] is True
    assert result["subreaper_restored"] is True
    assert result["direct_children"] == ""
    assert result["raw_broker_branch_observed"] is True
    assert result["three_birth_prefix_authority_present"] is False


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_v2_bad_broker_ack_kills_consumes_proves_and_closes() -> None:
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
            "BROKER_BAD_ACK",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["failure_sequence"] == 2
    assert result["failure_status"] == -33
    assert result["broker_pidfd_pid"] == result["broker_pid_cell_value"]
    assert result["pre_failure_population"] == 2
    assert result["guardian_echild_while_live"] == 10
    assert result["guardian_echild_after_failure"] == 10
    assert result["final_population"] == 0
    assert result["abort_state"] == "ABORTED_CLOSED"
    assert result["fd_count_restored"] is True
    assert result["subreaper_restored"] is True
    assert result["direct_children"] == ""
    assert result["clone_failure_cleanup_observed"] is True
    assert result["three_birth_prefix_authority_present"] is False


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_v2_unsealed_broker_image_is_rejected_before_clone() -> None:
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
            "BROKER_UNSEALED_EXEC",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["failure_sequence"] == 2
    assert result["failure_status"] == -47
    assert result["pre_command_population"] == 1
    assert result["pid_cell_untouched"] is True
    assert result["descriptor_rejected_before_clone"] is True
    assert result["final_population"] == 0
    assert result["abort_state"] == "ABORTED_CLOSED"
    assert result["fd_count_restored"] is True
    assert result["subreaper_restored"] is True
    assert result["direct_children"] == ""
    assert result["three_birth_prefix_authority_present"] is False
