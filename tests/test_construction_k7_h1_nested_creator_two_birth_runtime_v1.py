from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import pickle
import shutil
import subprocess
import sys

import pytest

from acfqp import construction_k7_h1_nested_creator_supervisor_exec_birth_native_v1 as native
from acfqp import construction_k7_h1_nested_creator_two_birth_runtime_v1 as runtime


HELPER = Path(__file__).with_name("_nested_creator_two_birth_runtime_subprocess.py")


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
        timeout=30,
    )
    return json.loads(completed.stdout.splitlines()[-1])


def test_exec_birth_native_source_text_abi_and_claim_locks() -> None:
    evidence = native.verify_nested_creator_supervisor_exec_birth_native_image_v1()
    assert evidence["text_byte_count"] == len(native.X86_64_TEXT_BYTES)
    assert evidence["clone_args_size"] == 88
    assert evidence["launch_args_size"] == 128
    assert evidence["parent_edge_size"] == 32
    assert evidence["parent_required_success_bits"] == 123
    assert evidence["role_elf_sha256"]
    assert evidence["runtime_toolchain_invocation_present"] is False
    assert evidence["actual_process_birth_present"] is False
    assert evidence["two_birth_prefix_authority_present"] is False
    assert "load_nested_creator_supervisor_exec_birth_entry_v1" in native.__all__


def test_registered_assembler_rebuilds_exact_exec_birth_text(tmp_path: Path) -> None:
    assembler = shutil.which("as")
    objcopy = shutil.which("objcopy")
    if assembler is None or objcopy is None:
        pytest.skip("registered GNU assembler toolchain is unavailable")
    version = subprocess.run(
        [assembler, "--version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    if "GNU assembler" not in version or "2.38" not in version:
        pytest.skip("host assembler differs from the registered audit toolchain")
    object_path = tmp_path / "edge.o"
    text_path = tmp_path / "edge.text"
    subprocess.run(
        [assembler, "--64", "-o", object_path, native.SOURCE_PATH], check=True
    )
    subprocess.run(
        [objcopy, "-O", "binary", "--only-section=.text", object_path, text_path],
        check=True,
    )
    assert text_path.read_bytes() == native.X86_64_TEXT_BYTES


def test_raw_two_birth_result_is_not_caller_mintable_or_copyable() -> None:
    result = object.__new__(runtime.BoundedNestedCreatorTwoBirthRawResultV1)
    with pytest.raises(runtime.ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error):
        copy.copy(result)
    with pytest.raises(runtime.ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error):
        copy.deepcopy(result)
    with pytest.raises(runtime.ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error):
        pickle.dumps(result)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_gated_two_birth_topology_and_creator_reaps() -> None:
    result = _run_real_helper("SUCCESS")
    assert result["birth_order"] == ["SUPERVISOR", "PIDFD_PROBE"]
    assert result["creator_by_slot"] == {
        "SUPERVISOR": "EXTERNAL_GUARDIAN",
        "PIDFD_PROBE": "SUPERVISOR",
    }
    assert result["supervisor_pid"] > 0
    assert result["probe_pid"] > 0
    assert result["supervisor_pid"] != result["probe_pid"]
    assert result["maximum_observed_control_population"] == 2
    assert result["final_population"] == 0
    assert result["memory_peak_read_count"] == 0
    assert result["outer_gate_fact_count"] == 3
    assert len(result["outer_nonce_hex"]) == 32
    assert result["outer_seal_set"] == 15
    assert result["outer_pidfd_pid"] == result["supervisor_pid"]
    assert result["outer_role_witness_same_identity"] is True
    assert result["mutation_rejections"] == 3
    assert result["fd_count_restored"] is True
    assert result["subreaper_restored"] is True
    assert result["direct_children"] == ""
    assert result["live_session_count"] == 0
    assert result["target_two_birth_creator_chain_observed"] is True
    assert result["exact_two_birth_os_topology_observed"] is False
    assert result["exclusive_two_birth_topology_authority_present"] is False
    assert result["two_birth_prefix_authority_present"] is False


@pytest.mark.parametrize("mode", ("NATIVE_RETURN_TAKEOVER", "PROBE_PARENT_RETURN"))
@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_failure_cleanup_restores_process_fd_cgroup_and_subreaper(
    mode: str,
) -> None:
    result = _run_real_helper(mode)
    assert result["mode"] == mode
    assert result["error_type"]
    assert result["final_population"] == 0
    assert result["fd_count_restored"] is True
    assert result["subreaper_restored"] is True
    assert result["direct_children"] == ""
    assert result["live_session_count"] == 0
