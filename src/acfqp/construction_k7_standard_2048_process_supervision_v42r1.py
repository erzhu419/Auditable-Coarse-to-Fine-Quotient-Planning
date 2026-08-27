"""Small source-auditable process and durable-file helpers for V42 ordinal-2."""

from __future__ import annotations

import ctypes
import hashlib
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import time
from typing import NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MAX_EXCEPTION_MESSAGE_BYTES = 4096
MAX_CHILD_STDERR_BYTES = 1024 * 1024
RENAME_NOREPLACE = 1


class V42RemoteOrdinal2ProcessError(RuntimeError):
    """One isolated role, bounded stream, or durable publication failed."""


class V42RemoteOrdinal2ChildError(V42RemoteOrdinal2ProcessError):
    def __init__(
        self,
        message: str,
        *,
        role: str,
        returncode: int | None,
        stdout: bytes,
        stderr: bytes,
        classification: str,
        group_teardown: str = "NOT_REQUESTED",
    ) -> None:
        super().__init__(bounded_message(message))
        self.role = role
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.classification = classification
        self.group_teardown = group_teardown


def fail(message: str) -> NoReturn:
    raise V42RemoteOrdinal2ProcessError(bounded_message(message))


def bounded_message(value: object) -> str:
    raw = str(value).encode("utf-8", errors="replace")
    if len(raw) <= MAX_EXCEPTION_MESSAGE_BYTES:
        return raw.decode("utf-8")
    # ``raw`` is valid UTF-8 before truncation, so ``ignore`` can discard only
    # the incomplete trailing code point.  In particular, it cannot introduce
    # a replacement character whose UTF-8 encoding would exceed the byte cap.
    return raw[:MAX_EXCEPTION_MESSAGE_BYTES].decode("utf-8", errors="ignore")


def require_isolated_python() -> None:
    if not (
        sys.flags.isolated == 1
        and sys.flags.no_site == 1
        and sys.dont_write_bytecode is True
    ):
        fail("formal V42 remote ordinal-2 role requires python -I -S -B")


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_once(path: Path, raw: bytes, *, mode: int = 0o400) -> dict[str, object]:
    if type(raw) is not bytes:
        fail("V42 remote ordinal-2 publication bytes changed type")
    parent = path.parent
    parent_observed = parent.lstat()
    if (
        not path.is_absolute()
        or not stat.S_ISDIR(parent_observed.st_mode)
        or parent.resolve(strict=True) != parent
    ):
        fail("V42 remote ordinal-2 publication parent is redirected")
    # This formal CLI is single-threaded at every durable publication point.
    # Mask only group/other bits while creating the O_EXCL inode so an
    # adversarial caller umask cannot erase owner-read permission in the tiny
    # open-to-first-fchmod interruption window.
    previous_umask = os.umask(0o077)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            mode,
        )
    finally:
        os.umask(previous_umask)
    try:
        # Freeze the visible partial inode's mode before its first data byte.
        # A process interruption can therefore be retained and hashed by the
        # append-only recovery journal without inheriting a caller umask mode.
        os.fchmod(descriptor, mode)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V42 remote ordinal-2 publication short write")
            view = view[written:]
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    retained = read_fixed_artifact(path, len(raw))
    observed = path.lstat()
    if retained != raw or stat.S_IMODE(observed.st_mode) != mode:
        fail("V42 remote ordinal-2 durable publication readback changed")
    fsync_directory(path.parent)
    return {
        "relative_name": path.name,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def create_one_shot_root(path: Path, *, expected_parent: Path) -> None:
    if not path.is_absolute() or path.parent != expected_parent or path == Path(path.anchor):
        fail("V42 remote ordinal-2 one-shot root changed")
    observed_parent = expected_parent.lstat()
    if (
        not stat.S_ISDIR(observed_parent.st_mode)
        or expected_parent.resolve(strict=True) != expected_parent
    ):
        fail("V42 remote ordinal-2 one-shot parent is redirected or non-directory")
    previous_umask = os.umask(0o077)
    try:
        try:
            os.mkdir(path, 0o700)
        except FileExistsError as error:
            raise V42RemoteOrdinal2ProcessError(
                "V42 remote ordinal-2 identity already exists; retry is forbidden"
            ) from error
    finally:
        os.umask(previous_umask)
    os.chmod(path, 0o700)
    if path.resolve(strict=True) != path:
        fail("V42 remote ordinal-2 one-shot root was redirected")
    fsync_directory(expected_parent)
    fsync_directory(path)


def rename_noreplace(parent: Path, old_name: str, new_name: str) -> None:
    """Atomically publish one child without permitting replacement.

    The fixed Linux target exposes ``renameat2``.  Refusing to fall back to
    ``rename`` keeps a pre-existing destination from ever being overwritten,
    including under a concurrent local filesystem race.
    """

    if (
        not parent.is_absolute()
        or parent == Path(parent.anchor)
        or type(old_name) is not str
        or type(new_name) is not str
        or not old_name
        or not new_name
        or old_name in {".", ".."}
        or new_name in {".", ".."}
        or "/" in old_name
        or "/" in new_name
        or "\x00" in old_name
        or "\x00" in new_name
    ):
        fail("V42 remote ordinal-2 no-replace rename contract changed")
    observed_parent = parent.lstat()
    if (
        not stat.S_ISDIR(observed_parent.st_mode)
        or parent.resolve(strict=True) != parent
    ):
        fail("V42 remote ordinal-2 no-replace rename parent is redirected")
    directory_fd = os.open(
        parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            fail("V42 remote ordinal-2 requires renameat2(RENAME_NOREPLACE)")
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
        result = renameat2(
            directory_fd,
            old_name.encode("utf-8"),
            directory_fd,
            new_name.encode("utf-8"),
            RENAME_NOREPLACE,
        )
        if result != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def read_fd_capped(descriptor: int, maximum: int, label: str) -> bytes:
    if type(maximum) is not int or maximum < 0:
        fail("V42 remote ordinal-2 stream cap changed")
    chunks: list[bytes] = []
    byte_count = 0
    while True:
        remaining = maximum + 1 - byte_count
        if remaining <= 0:
            fail(f"V42 remote ordinal-2 {label} exceeds its byte cap")
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        byte_count += len(chunk)
        if byte_count > maximum:
            fail(f"V42 remote ordinal-2 {label} exceeds its byte cap")
    return b"".join(chunks)


def read_fixed_artifact(path: Path, maximum: int) -> bytes:
    parent = path.parent
    parent_observed = parent.lstat()
    if (
        not path.is_absolute()
        or not stat.S_ISDIR(parent_observed.st_mode)
        or parent.resolve(strict=True) != parent
    ):
        fail("V42 remote ordinal-2 artifact parent is redirected")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISREG(observed.st_mode)
            or observed.st_nlink != 1
            or observed.st_size > maximum
        ):
            fail(f"V42 remote ordinal-2 artifact is nonregular or exceeds cap: {path.name}")
        raw = read_fd_capped(descriptor, maximum, path.name)
        after = os.fstat(descriptor)
        if (
            observed.st_dev,
            observed.st_ino,
            observed.st_mode,
            observed.st_nlink,
            observed.st_size,
            observed.st_mtime_ns,
            observed.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            fail(f"V42 remote ordinal-2 artifact changed during read: {path.name}")
        return raw
    finally:
        os.close(descriptor)


def memfd_from_bytes(label: str, raw: bytes) -> int:
    if type(raw) is not bytes:
        fail("V42 remote ordinal-2 child input changed type")
    descriptor = os.memfd_create(label, flags=os.MFD_CLOEXEC)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V42 remote ordinal-2 memfd short write")
            view = view[written:]
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def child_classification(role: str, returncode: int) -> str:
    if returncode < 0:
        number = -returncode
        try:
            name = signal.Signals(number).name
        except ValueError:
            name = "UNKNOWN"
        return f"{role}_SIGNAL_{name}_{number}"
    if returncode in (9, 137):
        return f"{role}_OOM_OR_SIGKILL_STYLE_EXIT"
    return f"{role}_NONZERO_EXIT"


def typed_failure_classification(raw: bytes, fallback: str) -> str:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        return fallback
    try:
        document = loads_canonical_json(raw[:-1])
    except (TypeError, ValueError):
        return fallback
    if (
        type(document) is dict
        and document.get("schema")
        == "acfqp.v42_remote_ordinal2_isolated_process_failure.v42r1"
        and type(document.get("failure_classification")) is str
    ):
        return document["failure_classification"]
    return fallback


def run_capped_child(
    *,
    role: str,
    command: tuple[str, ...],
    stdout_cap: int,
    stderr_cap: int = MAX_CHILD_STDERR_BYTES,
    timeout_seconds: int,
    cwd: Path,
    inherited_descriptor: int | None = None,
    start_new_session: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    if (
        type(role) is not str
        or not role
        or type(command) is not tuple
        or not command
        or any(type(argument) is not str or not argument for argument in command)
        or type(stdout_cap) is not int
        or stdout_cap < 0
        or type(stderr_cap) is not int
        or stderr_cap < 0
        or type(timeout_seconds) is not int
        or timeout_seconds <= 0
        or not isinstance(cwd, Path)
        or not cwd.is_absolute()
        or type(start_new_session) is not bool
        or (
            inherited_descriptor is not None
            and (type(inherited_descriptor) is not int or inherited_descriptor < 0)
        )
    ):
        fail("V42 remote ordinal-2 child process contract changed")
    environment = {"PATH": os.defpath, "LC_ALL": "C.UTF-8"}
    pass_fds = () if inherited_descriptor is None else (inherited_descriptor,)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        pass_fds=pass_fds,
        start_new_session=start_new_session,
    )
    process_group = process.pid

    def signal_child_process_group(signal_number: int) -> bool:
        if not start_new_session:
            try:
                process.send_signal(signal_number)
            except ProcessLookupError:
                return False
            return True
        # A fresh session makes the exact child PID the leader of a new process
        # group containing its descendants, never the caller's group.
        try:
            os.killpg(process_group, signal_number)
        except ProcessLookupError:
            return False
        return True

    def child_process_group_exists() -> bool:
        if not start_new_session:
            return process.poll() is None
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            return False
        return True

    if process.stdout is None or process.stderr is None:
        signal_child_process_group(signal.SIGKILL)
        fail("V42 remote ordinal-2 child pipes are unavailable")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, ("stdout", stdout_cap))
    selector.register(process.stderr, selectors.EVENT_READ, ("stderr", stderr_cap))
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout_seconds
    classification: str | None = None
    returncode: int | None = None
    group_teardown = "NOT_REQUESTED"

    def drain_ready(timeout: float) -> bool:
        events = selector.select(timeout=max(0.0, timeout))
        for key, _ in events:
            stream_name, cap = key.data
            chunk = os.read(key.fd, 64 * 1024)
            if not chunk:
                selector.unregister(key.fileobj)
                key.fileobj.close()
                continue
            # Retain at most cap+1 so cap evidence stays bounded even during
            # group teardown and inherited-pipe drainage.
            remaining = cap + 1 - len(buffers[stream_name])
            if remaining > 0:
                buffers[stream_name].extend(chunk[:remaining])
        return bool(events)

    def terminate_and_drain_group() -> str:
        term_sent = signal_child_process_group(signal.SIGTERM)
        term_deadline = time.monotonic() + 1.0
        while time.monotonic() < term_deadline and (
            child_process_group_exists() or selector.get_map()
        ):
            drain_ready(min(0.05, term_deadline - time.monotonic()))
            process.poll()
        kill_sent = False
        if child_process_group_exists():
            kill_sent = signal_child_process_group(signal.SIGKILL)
        if not start_new_session:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return "DIRECT_CHILD_TERM_KILL_INCOMPLETE_ENCLOSING_GROUP_REQUIRED"
            return (
                "DIRECT_CHILD_TERM_THEN_KILL_REAPED_ENCLOSING_GROUP_OWNS_DESCENDANTS"
                if kill_sent
                else "DIRECT_CHILD_TERM_REAPED_ENCLOSING_GROUP_OWNS_DESCENDANTS"
                if term_sent
                else "DIRECT_CHILD_ALREADY_ABSENT_ENCLOSING_GROUP_OWNS_DESCENDANTS"
            )
        kill_deadline = time.monotonic() + 5.0
        while time.monotonic() < kill_deadline and (
            child_process_group_exists() or selector.get_map()
        ):
            drain_ready(min(0.05, kill_deadline - time.monotonic()))
            process.poll()
        process.poll()
        group_gone = not child_process_group_exists()
        pipes_at_eof = not selector.get_map()
        prefix = (
            "TERM_THEN_KILL_GROUP"
            if kill_sent
            else "TERM_GROUP"
            if term_sent
            else "GROUP_ALREADY_ABSENT"
        )
        return (
            f"{prefix}_CONFIRMED_DIRECT_WAIT_AND_PIPE_EOF"
            if group_gone and pipes_at_eof
            else f"{prefix}_INCOMPLETE_GROUP_OR_PIPE_DRAIN"
        )
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                classification = f"{role}_TIMEOUT"
                group_teardown = terminate_and_drain_group()
                break
            for key, _ in selector.select(timeout=min(remaining, 1.0)):
                stream_name, cap = key.data
                chunk = os.read(key.fd, 64 * 1024)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                buffers[stream_name].extend(chunk)
                if len(buffers[stream_name]) > cap:
                    classification = f"{role}_{stream_name.upper()}_CAP_EXCEEDED"
                    group_teardown = terminate_and_drain_group()
                    break
            if classification is not None:
                break
            if process.poll() is not None and selector.get_map():
                # Give ordinary EOF one bounded chance to become observable.
                drain_ready(0.1)
                if selector.get_map():
                    classification = f"{role}_DIRECT_EXIT_WITH_INHERITED_PIPE_OPEN"
                    group_teardown = terminate_and_drain_group()
                    break
        try:
            returncode = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            classification = classification or f"{role}_GROUP_TEARDOWN_TIMEOUT"
            group_teardown = terminate_and_drain_group()
            returncode = process.wait(timeout=30)
        if (
            classification is None
            and start_new_session
            and child_process_group_exists()
        ):
            classification = f"{role}_DESCENDANT_PROCESS_GROUP_LEAK"
            group_teardown = terminate_and_drain_group()
    except BaseException:
        try:
            terminate_and_drain_group()
        except BaseException:
            signal_child_process_group(signal.SIGKILL)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        raise
    finally:
        selector.close()
        for pipe in (process.stdout, process.stderr):
            if not pipe.closed:
                pipe.close()
    stdout = bytes(buffers["stdout"][:stdout_cap])
    stderr = bytes(buffers["stderr"][:stderr_cap])
    if classification is not None:
        raise V42RemoteOrdinal2ChildError(
            f"V42 remote ordinal-2 {role} child failed: {classification}",
            role=role,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            classification=classification,
            group_teardown=group_teardown,
        )
    if returncode is None:
        fail("V42 remote ordinal-2 child return code is unavailable")
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def one_canonical_stdout(completed: subprocess.CompletedProcess[bytes], label: str) -> bytes:
    if not completed.stdout.endswith(b"\n") or completed.stdout.endswith(b"\n\n"):
        fail(f"V42 remote ordinal-2 {label} stdout has noncanonical trailing bytes")
    raw = completed.stdout[:-1]
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V42RemoteOrdinal2ProcessError(
            f"V42 remote ordinal-2 {label} stdout is not canonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        fail(f"V42 remote ordinal-2 {label} stdout canonical bytes changed")
    return raw


__all__ = (
    "MAX_CHILD_STDERR_BYTES",
    "MAX_EXCEPTION_MESSAGE_BYTES",
    "RENAME_NOREPLACE",
    "V42RemoteOrdinal2ChildError",
    "V42RemoteOrdinal2ProcessError",
    "bounded_message",
    "child_classification",
    "create_one_shot_root",
    "fail",
    "fsync_directory",
    "memfd_from_bytes",
    "one_canonical_stdout",
    "read_fd_capped",
    "read_fixed_artifact",
    "rename_noreplace",
    "require_isolated_python",
    "run_capped_child",
    "typed_failure_classification",
    "write_once",
)
