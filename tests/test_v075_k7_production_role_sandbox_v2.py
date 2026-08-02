from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp import v075_k7_production_role_sandbox_v2 as sandbox_v2


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"


def _denied_names(role: sandbox_v2.K7ProductionSandboxRoleV2) -> set[str]:
    return {
        name for name, _number in sandbox_v2.denied_syscalls_for_role_v2(role)
    }


def _run_filter(
    rows: tuple[tuple[int, int, int, int], ...],
    *,
    syscall: int,
    arguments: tuple[int, ...] = (),
    architecture: int = sandbox_v2.AUDIT_ARCH_X86_64,
) -> int:
    values = [0] * 6
    values[: len(arguments)] = arguments

    def load(offset: int) -> int:
        if offset == 0:
            return syscall & 0xFFFFFFFF
        if offset == 4:
            return architecture & 0xFFFFFFFF
        if offset >= 16 and (offset - 16) % 4 == 0:
            argument = (offset - 16) // 8
            high = ((offset - 16) % 8) // 4
            value = values[argument] & 0xFFFFFFFFFFFFFFFF
            return (value >> (32 * high)) & 0xFFFFFFFF
        raise AssertionError(f"unexpected seccomp_data offset {offset}")

    accumulator = 0
    index = 0
    while index < len(rows):
        code, true_jump, false_jump, value = rows[index]
        if code == sandbox_v2.BPF_LD_W_ABS:
            accumulator = load(value)
            index += 1
        elif code == sandbox_v2.BPF_JMP_JEQ_K:
            index += 1 + (true_jump if accumulator == value else false_jump)
        elif code == sandbox_v2.BPF_JMP_JSET_K:
            index += 1 + (true_jump if accumulator & value else false_jump)
        elif code == sandbox_v2.BPF_RET_K:
            return value
        else:  # pragma: no cover - closed instruction grammar
            raise AssertionError(f"unexpected BPF opcode {code}")
    raise AssertionError("filter fell off its instruction array")


def test_preexec_exact_exec_edge_and_postexec_tightening_are_separate() -> None:
    denied = sandbox_v2.SECCOMP_RET_ERRNO | errno.EPERM
    executable_fd = 123
    for role in sandbox_v2.K7ProductionSandboxRoleV2:
        names = _denied_names(role)
        assert set(sandbox_v2.DESCENDANT_CREATION_SYSCALLS) <= names
        assert "execve" in names
        assert "execveat" not in names
        assert not set(sandbox_v2.EXISTING_ENDPOINT_SYSCALLS) & names
        rows = sandbox_v2.preexec_seccomp_filter_rows_for_role_v2(
            role,
            executable_fd=executable_fd,
        )
        assert _run_filter(
            rows,
            syscall=322,
            arguments=(executable_fd, 0, 0, 0, sandbox_v2.AT_EMPTY_PATH),
        ) == sandbox_v2.SECCOMP_RET_ALLOW
        assert _run_filter(
            rows,
            syscall=322,
            arguments=(executable_fd + 1, 0, 0, 0, sandbox_v2.AT_EMPTY_PATH),
        ) == denied
        assert _run_filter(
            rows,
            syscall=322,
            arguments=(executable_fd, 0, 0, 0, 0),
        ) == denied
        assert _run_filter(rows, syscall=59) == denied
        for name in sandbox_v2.DESCENDANT_CREATION_SYSCALLS:
            assert _run_filter(
                rows,
                syscall=sandbox_v2.X86_64_SYSCALL_NUMBERS[name],
            ) == denied
        assert _run_filter(rows, syscall=44) == sandbox_v2.SECCOMP_RET_ALLOW

    postexec = sandbox_v2.postexec_seccomp_filter_rows_v2()
    assert _run_filter(postexec, syscall=59) == denied
    assert _run_filter(postexec, syscall=322) == denied
    # This layer only tightens exec.  The still-stacked pre-exec layer owns
    # descendant denial.
    assert _run_filter(postexec, syscall=57) == sandbox_v2.SECCOMP_RET_ALLOW
    assert _run_filter(
        postexec,
        syscall=1,
        architecture=0,
    ) == sandbox_v2.SECCOMP_RET_KILL_PROCESS

    worker = _denied_names(sandbox_v2.K7ProductionSandboxRoleV2.WORKER)
    business = _denied_names(sandbox_v2.K7ProductionSandboxRoleV2.BUSINESS)
    assert "fchmod" not in worker and "fchmod" in business
    assert "ftruncate" in worker and "ftruncate" not in business
    assert {"renameat", "renameat2", "unlinkat"}.isdisjoint(worker)
    assert {"renameat", "renameat2", "unlinkat"} <= business

    document = (
        sandbox_v2.official_v075_k7_production_role_sandbox_profile_v2()
        .to_document()
    )
    assert document["parent_only_prepares_ruleset_and_filter"] is True
    assert document["preexec_exact_execveat_edge"] is True
    assert document["postexec_landlock_installation_forbidden"] is True
    assert document["profile_domain_registry_joined"] is True
    assert all(value is False for value in document["formal_locks"].values())


def test_landlock_unexpected_errors_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sandbox_v2,
        "_raw_syscall",
        lambda _number, *_arguments: (-1, errno.EIO),
    )
    with pytest.raises(
        sandbox_v2.V075K7ProductionRoleSandboxV2Error,
        match="unexpected errno",
    ):
        sandbox_v2.probe_v075_k7_production_landlock_abi_v2()
    with pytest.raises(
        sandbox_v2.V075K7ProductionRoleSandboxV2Error,
        match="creation failed",
    ):
        sandbox_v2._create_landlock_ruleset_v2()  # noqa: SLF001
    with pytest.raises(
        sandbox_v2.V075K7ProductionRoleSandboxV2Error,
        match="PATH_BENEATH",
    ):
        sandbox_v2._add_worker_output_rule_v2(  # noqa: SLF001
            ruleset_fd=91,
            output_directory_fd=92,
        )


def test_parent_preparation_binds_executable_output_and_ruleset_fds(
    tmp_path: Path,
) -> None:
    abi = sandbox_v2.probe_v075_k7_production_landlock_abi_v2()
    if abi is None or abi < sandbox_v2.MINIMUM_LANDLOCK_ABI:
        pytest.skip("Landlock ABI 3 is unavailable")
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    executable_fd = os.open(
        sys.executable,
        os.O_RDONLY | os.O_CLOEXEC,
    )
    first_fd = os.open(first, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    second_fd = os.open(second, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    authorities: list[sandbox_v2.K7ProductionRoleSandboxAuthorityV2] = []
    try:
        authority = (
            sandbox_v2.freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
                role=sandbox_v2.K7ProductionSandboxRoleV2.WORKER,
                executable_fd=executable_fd,
                output_directory_fd=first_fd,
            )
        )
        authorities.append(authority)
        os.dup2(second_fd, first_fd, inheritable=False)
        with pytest.raises(
            sandbox_v2.V075K7ProductionRoleSandboxV2Error,
            match="output-directory FD identity changed",
        ):
            authority.assert_current()

        executable_cross = os.open(sys.executable, os.O_RDONLY | os.O_CLOEXEC)
        second_authority = (
            sandbox_v2.freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
                role=sandbox_v2.K7ProductionSandboxRoleV2.BUSINESS,
                executable_fd=executable_cross,
            )
        )
        authorities.append(second_authority)
        os.dup2(second_fd, executable_cross, inheritable=False)
        with pytest.raises(
            sandbox_v2.V075K7ProductionRoleSandboxV2Error,
            match="executable FD",
        ):
            second_authority.assert_current()
        os.close(executable_cross)

        ruleset_cross_exec = os.open(sys.executable, os.O_RDONLY | os.O_CLOEXEC)
        ruleset_authority = (
            sandbox_v2.freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
                role=sandbox_v2.K7ProductionSandboxRoleV2.BUSINESS,
                executable_fd=ruleset_cross_exec,
            )
        )
        authorities.append(ruleset_authority)
        null_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        os.dup2(
            null_fd,
            ruleset_authority.preexec_landlock_ruleset_fd,
            inheritable=False,
        )
        os.close(null_fd)
        with pytest.raises(
            sandbox_v2.V075K7ProductionRoleSandboxV2Error,
            match="ruleset FD identity changed",
        ):
            ruleset_authority.assert_current()
        os.close(ruleset_cross_exec)

        with pytest.raises(
            sandbox_v2.V075K7ProductionRoleSandboxV2Error,
            match="may not receive",
        ):
            sandbox_v2.freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
                role=sandbox_v2.K7ProductionSandboxRoleV2.BUSINESS,
                executable_fd=executable_fd,
                output_directory_fd=second_fd,
            )
    finally:
        for authority in authorities:
            authority.close()
        os.close(executable_fd)
        os.close(first_fd)
        os.close(second_fd)


def test_native_material_is_one_shot_and_keeps_program_storage(
    tmp_path: Path,
) -> None:
    abi = sandbox_v2.probe_v075_k7_production_landlock_abi_v2()
    if abi is None or abi < sandbox_v2.MINIMUM_LANDLOCK_ABI:
        pytest.skip("Landlock ABI 3 is unavailable")
    executable_fd = os.open(sys.executable, os.O_RDONLY | os.O_CLOEXEC)
    try:
        authority = (
            sandbox_v2.freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
                role=sandbox_v2.K7ProductionSandboxRoleV2.BUSINESS,
                executable_fd=executable_fd,
            )
        )
        material = (
            sandbox_v2.consume_v075_k7_production_role_preexec_sandbox_v2(
                authority
            )
        )
        try:
            assert material.executable_fd == executable_fd
            assert material.preexec_landlock_ruleset_fd >= 3
            assert material.preexec_seccomp_program_address > 0
            assert len(material.preexec_seccomp_filter_sha256) == 64
            material.assert_current()
            with pytest.raises(
                sandbox_v2.V075K7ProductionRoleSandboxV2Error,
                match="already consumed",
            ):
                sandbox_v2.consume_v075_k7_production_role_preexec_sandbox_v2(
                    authority
                )
        finally:
            material.close()
        with pytest.raises(
            sandbox_v2.V075K7ProductionRoleSandboxV2Error,
            match="closed",
        ):
            material.assert_current()
    finally:
        os.close(executable_fd)


_SUBPROCESS_SOURCE = r'''
import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import socket
import sys

sys.path.insert(0, sys.argv[1])
from acfqp import v075_k7_production_role_sandbox_v2 as sandbox

role = sandbox.K7ProductionSandboxRoleV2(sys.argv[2])
output = Path(sys.argv[3])
outside = Path(sys.argv[4])
output.mkdir(mode=0o700, parents=True)
outside.mkdir(mode=0o700, parents=True)
existing = outside / "existing.txt"
existing.write_bytes(b"before-sandbox")
executable_fd = os.open(sys.executable, os.O_RDONLY | os.O_CLOEXEC)
output_fd = None
if role is sandbox.K7ProductionSandboxRoleV2.WORKER:
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
memfd = os.memfd_create(
    "acfqp-sandbox-behavior",
    os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
)
abi = sandbox.probe_v075_k7_production_landlock_abi_v2()
if abi is None or abi < sandbox.MINIMUM_LANDLOCK_ABI:
    raise SystemExit(77)
authority = sandbox.freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
    role=role,
    executable_fd=executable_fd,
    output_directory_fd=output_fd,
)
material = sandbox.consume_v075_k7_production_role_preexec_sandbox_v2(authority)
program_address = material.preexec_seccomp_program_address
ruleset_fd = material.preexec_landlock_ruleset_fd

# This is the native trampoline's irreversible order, exercised in an
# isolated test process without attempting to claim a Python launch path.
ctypes.set_errno(0)
if sandbox._LIBC.prctl(sandbox.PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
    raise SystemExit(78)
result, error = sandbox._raw_syscall(
    sandbox.LANDLOCK_RESTRICT_SELF,
    ruleset_fd,
    0,
)
if result != 0:
    raise SystemExit(79)
result, error = sandbox._raw_syscall(
    sandbox.SECCOMP_SYSCALL_X86_64,
    sandbox.SECCOMP_SET_MODE_FILTER,
    0,
    ctypes.c_void_p(program_address),
)
if result != 0:
    raise SystemExit(80)
material.close()

# The exact execveat gate reaches the kernel (EFAULT from the deliberately bad
# pathname pointer). Crossed FD/flags and plain exec are rejected by seccomp.
result, exact_exec_errno = sandbox._raw_syscall(
    sandbox.X86_64_SYSCALL_NUMBERS["execveat"],
    executable_fd,
    ctypes.c_void_p(1),
    ctypes.c_void_p(0),
    ctypes.c_void_p(0),
    sandbox.AT_EMPTY_PATH,
)
if result != -1 or exact_exec_errno != errno.EFAULT:
    raise SystemExit(81)
result, crossed_exec_errno = sandbox._raw_syscall(
    sandbox.X86_64_SYSCALL_NUMBERS["execveat"],
    memfd,
    ctypes.c_void_p(1),
    ctypes.c_void_p(0),
    ctypes.c_void_p(0),
    sandbox.AT_EMPTY_PATH,
)
if result != -1 or crossed_exec_errno != errno.EPERM:
    raise SystemExit(82)
result, crossed_flag_errno = sandbox._raw_syscall(
    sandbox.X86_64_SYSCALL_NUMBERS["execveat"],
    executable_fd,
    ctypes.c_void_p(1),
    ctypes.c_void_p(0),
    ctypes.c_void_p(0),
    0,
)
if result != -1 or crossed_flag_errno != errno.EPERM:
    raise SystemExit(83)
result, plain_exec_errno = sandbox._raw_syscall(
    sandbox.X86_64_SYSCALL_NUMBERS["execve"],
    ctypes.c_void_p(1),
    ctypes.c_void_p(0),
    ctypes.c_void_p(0),
)
if result != -1 or plain_exec_errno != errno.EPERM:
    raise SystemExit(84)

left.send(b"allowed-endpoint")
if right.recv(64) != b"allowed-endpoint":
    raise SystemExit(85)
os.write(memfd, b"memfd")
os.fsync(memfd)
if role is sandbox.K7ProductionSandboxRoleV2.BUSINESS:
    os.ftruncate(memfd, 0)
else:
    inside_fd = os.open(
        "inside.tmp",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
        dir_fd=output_fd,
    )
    os.fchmod(inside_fd, 0o600)
    os.write(inside_fd, b"worker-output")
    os.fsync(inside_fd)
    os.close(inside_fd)
    os.rename(
        "inside.tmp",
        "inside.json",
        src_dir_fd=output_fd,
        dst_dir_fd=output_fd,
    )
fcntl.fcntl(memfd, getattr(fcntl, "F_ADD_SEALS", 1033), 0x000F)

try:
    blocked_fd = os.open(existing, os.O_WRONLY | os.O_TRUNC | os.O_CLOEXEC)
except OSError as error:
    path_errno = error.errno
else:
    os.close(blocked_fd)
    raise SystemExit(86)
if path_errno not in {errno.EACCES, errno.EPERM}:
    raise SystemExit(87)

try:
    child_pid = os.fork()
except OSError as error:
    fork_errno = error.errno
else:
    if child_pid == 0:
        os._exit(88)
    os.waitpid(child_pid, 0)
    raise SystemExit(89)
if fork_errno != errno.EPERM:
    raise SystemExit(90)

tightening = sandbox.install_v075_k7_production_role_postexec_tightening_v2(
    role=role
)
result, post_execveat_errno = sandbox._raw_syscall(
    sandbox.X86_64_SYSCALL_NUMBERS["execveat"],
    executable_fd,
    ctypes.c_void_p(1),
    ctypes.c_void_p(0),
    ctypes.c_void_p(0),
    sandbox.AT_EMPTY_PATH,
)
if result != -1 or post_execveat_errno != errno.EPERM:
    raise SystemExit(91)
result, post_execve_errno = sandbox._raw_syscall(
    sandbox.X86_64_SYSCALL_NUMBERS["execve"],
    ctypes.c_void_p(1),
    ctypes.c_void_p(0),
    ctypes.c_void_p(0),
)
if result != -1 or post_execve_errno != errno.EPERM:
    raise SystemExit(92)

document = tightening.to_document()
sys.stdout.write(json.dumps({
    "role": role.value,
    "exact_exec_errno": exact_exec_errno,
    "crossed_exec_errno": crossed_exec_errno,
    "path_errno": path_errno,
    "fork_errno": fork_errno,
    "post_execve_errno": post_execve_errno,
    "post_execveat_errno": post_execveat_errno,
    "inside_exists": (output / "inside.json").exists(),
    "landlock_from_birth_required": document["landlock_from_birth_required"],
    "landlock_installed_by_this_stage": document["landlock_installed_by_this_stage"],
    "formal_locks": document["formal_locks"],
}, sort_keys=True))
'''


@pytest.mark.parametrize(
    "role",
    tuple(sandbox_v2.K7ProductionSandboxRoleV2),
)
def test_live_two_stage_subprocess_boundary(
    tmp_path: Path,
    role: sandbox_v2.K7ProductionSandboxRoleV2,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            _SUBPROCESS_SOURCE,
            os.fspath(SOURCE_ROOT),
            role.value,
            os.fspath(tmp_path / role.value.lower() / "output"),
            os.fspath(tmp_path / role.value.lower() / "outside"),
        ],
        check=False,
        capture_output=True,
        env={"LANG": "C", "LC_ALL": "C", "TZ": "UTC"},
        text=True,
        timeout=30,
    )
    if completed.returncode == 77:
        pytest.skip("Landlock ABI 3 is unavailable in the subprocess")
    assert completed.returncode == 0, (
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )
    assert completed.stderr == ""
    document = json.loads(completed.stdout)
    assert document["role"] == role.value
    assert document["exact_exec_errno"] == errno.EFAULT
    assert document["crossed_exec_errno"] == errno.EPERM
    assert document["path_errno"] in {errno.EACCES, errno.EPERM}
    assert document["fork_errno"] == errno.EPERM
    assert document["post_execve_errno"] == errno.EPERM
    assert document["post_execveat_errno"] == errno.EPERM
    assert document["inside_exists"] is (
        role is sandbox_v2.K7ProductionSandboxRoleV2.WORKER
    )
    assert document["landlock_from_birth_required"] is True
    assert document["landlock_installed_by_this_stage"] is False
    assert all(value is False for value in document["formal_locks"].values())
