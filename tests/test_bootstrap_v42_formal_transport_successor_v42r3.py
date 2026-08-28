from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = (
    ROOT / "scripts/bootstrap_v42_formal_transport_successor_v42r3.py"
)
STAGE_ONE = (
    ROOT / "scripts/launch_v42_formal_transport_successor_v42r3.py"
)
ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
}
EXTERNAL_INVOKER = r'''
import fcntl
import hashlib
import os
import stat
import sys

path, root, expected, *user = sys.argv[1:]
named = os.lstat(path)
descriptor = os.open(
    path,
    os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
)
before = os.fstat(descriptor)
if (
    not stat.S_ISREG(before.st_mode)
    or stat.S_IMODE(before.st_mode) != 0o644
    or before.st_uid != os.geteuid()
    or before.st_gid != os.getegid()
    or before.st_nlink != 1
    or not 0 < before.st_size <= 8 * 1024**2
    or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
):
    raise RuntimeError("external bootstrap storage changed")
raw = b""
while len(raw) < before.st_size:
    chunk = os.read(descriptor, before.st_size - len(raw))
    if not chunk:
        raise RuntimeError("external bootstrap ended early")
    raw += chunk
if os.read(descriptor, 1):
    raise RuntimeError("external bootstrap grew")
after = os.fstat(descriptor)
os.close(descriptor)
final = os.lstat(path)
fields = (
    "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
    "st_size", "st_mtime_ns", "st_ctime_ns",
)
if (
    hashlib.sha256(raw).hexdigest() != expected
    or any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(final, field)
        for field in fields
    )
):
    raise RuntimeError("external bootstrap digest or stable state changed")
descriptor = os.memfd_create(
    "external-acfqp-v42r3-bootstrap",
    os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
)
if descriptor != 3:
    raise RuntimeError("external bootstrap memfd number changed")
os.fchmod(descriptor, 0o400)
view = memoryview(raw)
while view:
    written = os.write(descriptor, view)
    if written <= 0:
        raise RuntimeError("external bootstrap memfd write failed")
    view = view[written:]
os.fsync(descriptor)
os.lseek(descriptor, 0, os.SEEK_SET)
seals = (
    fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK
    | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
)
fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals)
os.set_inheritable(descriptor, True)
os.execve(
    "/usr/bin/python3",
    [
        "/usr/bin/python3", "-I", "-S", "-B", "/proc/self/fd/3",
        "--v42r3-external-repository-root", root,
        "--v42r3-external-bootstrap-sha256", expected, *user,
    ],
    {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": "/usr/bin:/bin"},
)
'''


def _bootstrap_constants(path: Path = BOOTSTRAP) -> dict[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in {
            "STAGE_ONE_SHA256", "STAGE_ONE_BYTE_COUNT",
        }:
            values[target.id] = ast.literal_eval(node.value)
    return values


def _run(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "/usr/bin/python3", "-I", "-S", "-B", str(path),
            *arguments,
        ],
        cwd=path.parents[1],
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_external(
    path: Path, *arguments: str, expected_sha256: str | None = None,
) -> subprocess.CompletedProcess[str]:
    digest = (
        hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_sha256 is None else expected_sha256
    )
    return subprocess.run(
        [
            "/usr/bin/python3", "-I", "-S", "-B", "-c", EXTERNAL_INVOKER,
            str(path), str(path.parents[1]), digest, *arguments,
        ],
        cwd=path.parents[1],
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def test_bootstrap_is_stdlib_only_and_imports_no_effect_client() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert source.startswith("from __future__ import annotations\n")
    assert "/bin/sh" not in source
    assert "readlink -f" not in source
    tree = ast.parse(source)
    imported: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    assert all(
        name != "acfqp" and not name.startswith("acfqp.")
        and name != "scripts" and not name.startswith("scripts.")
        for name in imported
    )
    assert "subprocess" not in imported
    assert "socket" not in imported


def test_bootstrap_pins_exact_stage_one_bytes() -> None:
    constants = _bootstrap_constants()
    raw = STAGE_ONE.read_bytes()
    assert constants == {
        "STAGE_ONE_SHA256": hashlib.sha256(raw).hexdigest(),
        "STAGE_ONE_BYTE_COUNT": len(raw),
    }


def test_bootstrap_sealed_cross_process_handoff_reaches_help() -> None:
    result = _run_external(BOOTSTRAP, "--help")
    assert result.returncode == 0, result.stderr
    assert "native V42r3 formal transport successor launcher" in result.stdout


def test_stage_one_rejects_direct_unsealed_entry() -> None:
    result = _run(STAGE_ONE, "--help")
    assert result.returncode != 0
    assert "did not enter through pinned bootstrap" in result.stderr


def test_bootstrap_rejects_direct_unsealed_entry() -> None:
    result = _run(BOOTSTRAP, "--help")
    assert result.returncode != 0
    assert "external sealed invoker" in result.stderr


def test_bootstrap_rejects_same_size_stage_one_tamper(
    tmp_path: Path,
) -> None:
    clone = tmp_path / "repo"
    (clone / "scripts").mkdir(parents=True)
    bootstrap_copy = clone / BOOTSTRAP.relative_to(ROOT)
    stage_copy = clone / STAGE_ONE.relative_to(ROOT)
    shutil.copyfile(BOOTSTRAP, bootstrap_copy)
    shutil.copyfile(STAGE_ONE, stage_copy)
    os.chmod(bootstrap_copy, 0o644)
    os.chmod(stage_copy, 0o644)
    raw = bytearray(stage_copy.read_bytes())
    raw[-1] = 32 if raw[-1] != 32 else 10
    stage_copy.write_bytes(raw)
    os.chmod(stage_copy, 0o644)

    result = _run_external(bootstrap_copy, "--help")
    assert result.returncode != 0
    assert "stage-1 digest changed" in result.stderr


def test_external_invoker_rejects_bootstrap_digest_mismatch() -> None:
    result = _run_external(
        BOOTSTRAP, "--help", expected_sha256="0" * 64
    )
    assert result.returncode != 0
    assert "external bootstrap digest" in result.stderr
