from __future__ import annotations

"""Effect-free stage-0 admitted through an external sealed-source invoker.

The campaign does not claim that this user-owned source authenticates itself.
An operator-controlled external TCB must digest a stable read of these bytes,
place those same bytes in sealed memfd 3, and enter this stage with the exact
hidden arguments below.  This stage preserves that descriptor as fd 4 for the
authenticated controller, admits only the pinned stage-1 bytes into a new
sealed fd 3, and execs a fresh isolated interpreter.  It performs no project
import, journal operation, or network operation.
"""

import errno
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import sys
from typing import NoReturn


EXACT_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
}
PYTHON = "/usr/bin/python3"
PYTHON_REALPATH = "/usr/bin/python3.10"
PYTHON_REALPATH_SHA256 = (
    "7d51cd6b48b521277f5caa4610a82126e315fa2be4df069823a8b1eeb5bd4a86"
)
PYTHON_REALPATH_BYTE_COUNT = 5_917_224
BOOTSTRAP_RELATIVE = (
    "scripts/bootstrap_v42_formal_transport_successor_v42r3.py"
)
STAGE_ONE_RELATIVE = (
    "scripts/launch_v42_formal_transport_successor_v42r3.py"
)
STAGE_ONE_SHA256 = (
    "a9e68b9fee9b830e7c9286b44b9c68c8ed84f9c721889143352f1f968952d636"
)
STAGE_ONE_BYTE_COUNT = 119_165
EXTERNAL_ROOT_ARGUMENT = "--v42r3-external-repository-root"
EXTERNAL_SHA_ARGUMENT = "--v42r3-external-bootstrap-sha256"
STAGE_ONE_ROOT_ARGUMENT = "--v42r3-bootstrap-repository-root"
SEALED_STAGE_FD = 3
SEALED_STAGE_PATH = "/proc/self/fd/3"
SEALED_BOOTSTRAP_FD = 4
PINNED_PYTHON_FD = 5
MAX_SOURCE_BYTES = 8 * 1024**2


class V42FormalTransportBootstrapError(RuntimeError):
    """The externally admitted stage-0 rejected its execution boundary."""


def _fail(message: str) -> NoReturn:
    raise V42FormalTransportBootstrapError(message)


def _live_descriptors() -> list[int]:
    live: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        if not name.isdigit():
            continue
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise
            continue
        live.append(descriptor)
    return sorted(live)


def _stable_regular(
    path: Path, *, expected_size: int | None = None,
    mode: int = 0o644, uid: int | None = None, gid: int | None = None,
) -> bytes:
    named = path.lstat()
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        expected_uid = os.geteuid() if uid is None else uid
        expected_gid = os.getegid() if gid is None else gid
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_uid != expected_uid
            or before.st_gid != expected_gid
            or before.st_nlink != 1
            or not 0 < before.st_size <= MAX_SOURCE_BYTES
            or (expected_size is not None and before.st_size != expected_size)
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("V42r3 bootstrap source storage changed: " + str(path))
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("V42r3 bootstrap source ended early: " + str(path))
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("V42r3 bootstrap source grew while read: " + str(path))
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = path.lstat()
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(final, field)
        for field in fields
    ):
        _fail("V42r3 bootstrap source changed while read: " + str(path))
    return b"".join(chunks)


def _read_sealed_bootstrap() -> bytes:
    before = os.fstat(SEALED_STAGE_FD)
    expected_seals = (
        fcntl.F_SEAL_SEAL
        | fcntl.F_SEAL_SHRINK
        | fcntl.F_SEAL_GROW
        | fcntl.F_SEAL_WRITE
    )
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != os.geteuid()
        or before.st_gid != os.getegid()
        or before.st_nlink != 0
        or not 0 < before.st_size <= MAX_SOURCE_BYTES
        or fcntl.fcntl(SEALED_STAGE_FD, fcntl.F_GET_SEALS) != expected_seals
    ):
        _fail("V42r3 externally sealed bootstrap storage changed")
    chunks: list[bytes] = []
    offset = 0
    while offset < before.st_size:
        chunk = os.pread(
            SEALED_STAGE_FD,
            min(1024 * 1024, before.st_size - offset),
            offset,
        )
        if not chunk:
            _fail("V42r3 externally sealed bootstrap ended early")
        chunks.append(chunk)
        offset += len(chunk)
    after = os.fstat(SEALED_STAGE_FD)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        any(getattr(before, field) != getattr(after, field) for field in fields)
        or fcntl.fcntl(SEALED_STAGE_FD, fcntl.F_GET_SEALS) != expected_seals
    ):
        _fail("V42r3 externally sealed bootstrap changed while read")
    return b"".join(chunks)


def _require_entry() -> tuple[Path, bytes, list[str]]:
    if (
        len(sys.argv) < 5
        or sys.argv[0] != SEALED_STAGE_PATH
        or sys.argv[1] != EXTERNAL_ROOT_ARGUMENT
        or not os.path.isabs(sys.argv[2])
        or os.path.realpath(sys.argv[2]) != sys.argv[2]
        or not os.path.isdir(sys.argv[2])
        or sys.argv[3] != EXTERNAL_SHA_ARGUMENT
        or len(sys.argv[4]) != 64
        or any(character not in "0123456789abcdef" for character in sys.argv[4])
    ):
        _fail("V42r3 bootstrap did not enter through external sealed invoker")
    root = Path(sys.argv[2])
    expected_sha256 = sys.argv[4]
    user_arguments = list(sys.argv[5:])
    if (
        __file__ != SEALED_STAGE_PATH
        or sys.executable != PYTHON
        or os.path.realpath(sys.executable) != PYTHON_REALPATH
        or tuple(sys.version_info[:3]) != (3, 10, 12)
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
        or sys.gettrace() is not None
        or sys.getprofile() is not None
        or sys.orig_argv
        != [
            PYTHON, "-I", "-S", "-B", SEALED_STAGE_PATH,
            EXTERNAL_ROOT_ARGUMENT, str(root),
            EXTERNAL_SHA_ARGUMENT, expected_sha256, *user_arguments,
        ]
        or sys.path
        != [
            "/usr/lib/python310.zip",
            "/usr/lib/python3.10",
            "/usr/lib/python3.10/lib-dynload",
        ]
        or dict(os.environ) != EXACT_ENVIRONMENT
        or Path.cwd() != root
        or getattr(getattr(os, "__spec__", None), "origin", None)
        != "/usr/lib/python3.10/os.py"
        or _live_descriptors() != [0, 1, 2, SEALED_STAGE_FD]
    ):
        _fail("V42r3 bootstrap isolated sealed entry changed")
    raw = _read_sealed_bootstrap()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        _fail("V42r3 external bootstrap digest assertion changed")
    if _stable_regular(root / BOOTSTRAP_RELATIVE) != raw:
        _fail("V42r3 sealed bootstrap differs from selected repository")
    stage_one = _stable_regular(
        root / STAGE_ONE_RELATIVE, expected_size=STAGE_ONE_BYTE_COUNT
    )
    if hashlib.sha256(stage_one).hexdigest() != STAGE_ONE_SHA256:
        _fail("V42r3 bootstrap stage-1 digest changed")
    if _live_descriptors() != [0, 1, 2, SEALED_STAGE_FD]:
        _fail("V42r3 bootstrap verification leaked a descriptor")
    return root, stage_one, user_arguments


def _open_pinned_python() -> int:
    path = Path(PYTHON_REALPATH)
    named = path.lstat()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        current = os.stat("/proc/self/exe")
        if (
            descriptor != PINNED_PYTHON_FD
            or not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o755
            or before.st_uid != 0
            or before.st_gid != 0
            or before.st_nlink != 1
            or before.st_size != PYTHON_REALPATH_BYTE_COUNT
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
            or (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino)
        ):
            _fail("V42r3 bootstrap Python executable identity changed")
        digest = hashlib.sha256()
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(
                descriptor, min(1024 * 1024, before.st_size - offset), offset
            )
            if not chunk:
                _fail("V42r3 bootstrap Python executable ended early")
            digest.update(chunk)
            offset += len(chunk)
        after = os.fstat(descriptor)
        final = path.lstat()
        fields = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
        if (
            digest.hexdigest() != PYTHON_REALPATH_SHA256
            or any(
                getattr(before, field) != getattr(after, field)
                or getattr(after, field) != getattr(final, field)
                for field in fields
            )
            or os.get_inheritable(descriptor)
        ):
            _fail("V42r3 bootstrap Python executable changed while pinned")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _preserve_bootstrap_and_seal_stage_one(raw: bytes) -> None:
    os.dup2(SEALED_STAGE_FD, SEALED_BOOTSTRAP_FD, inheritable=True)
    os.close(SEALED_STAGE_FD)
    descriptor = os.memfd_create(
        "acfqp-v42r3-formal-launcher",
        os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
    )
    if descriptor != SEALED_STAGE_FD:
        os.close(descriptor)
        _fail("V42r3 bootstrap stage-1 memfd number changed")
    os.fchmod(descriptor, 0o400)
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            _fail("V42r3 bootstrap stage-1 memfd write made no progress")
        view = view[written:]
    os.fsync(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)
    expected_seals = (
        fcntl.F_SEAL_SEAL
        | fcntl.F_SEAL_SHRINK
        | fcntl.F_SEAL_GROW
        | fcntl.F_SEAL_WRITE
    )
    fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, expected_seals)
    os.set_inheritable(descriptor, True)
    observed = os.fstat(descriptor)
    if (
        not stat.S_ISREG(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o400
        or observed.st_uid != os.geteuid()
        or observed.st_gid != os.getegid()
        or observed.st_nlink != 0
        or observed.st_size != len(raw)
        or fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != expected_seals
        or not os.get_inheritable(descriptor)
        or not os.get_inheritable(SEALED_BOOTSTRAP_FD)
        or _live_descriptors()
        != [0, 1, 2, SEALED_STAGE_FD, SEALED_BOOTSTRAP_FD]
    ):
        _fail("V42r3 bootstrap sealed source handoff changed")


def main() -> NoReturn:
    root, raw, user_arguments = _require_entry()
    _preserve_bootstrap_and_seal_stage_one(raw)
    python_fd = _open_pinned_python()
    arguments = [
        PYTHON,
        "-I",
        "-S",
        "-B",
        SEALED_STAGE_PATH,
        STAGE_ONE_ROOT_ARGUMENT,
        str(root),
        *user_arguments,
    ]
    try:
        os.execve(
            "/proc/self/fd/" + str(python_fd), arguments, EXACT_ENVIRONMENT
        )
    except BaseException:
        os.close(python_fd)
        raise
    _fail("V42r3 bootstrap isolated exec returned")


if __name__ == "__main__":
    main()
