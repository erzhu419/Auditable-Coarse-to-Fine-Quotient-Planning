"""Single effect boundary for the V42 pre-formal remote upload.

The sender keeps the exact local journal snapshot pinned across durable network
marker publication and descriptor-based exec of the registered SSH binary.  A
remote completion is accepted only as exit zero plus one bounded canonical
receipt followed by EOF and a full contextual receipt verification.  Every
other observation after marker publication is conservatively ambiguous.
"""

from __future__ import annotations

import base64
import ctypes
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import os
import selectors
import signal
import stat
import sys
import time
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from scripts import publish_v42_preformal_upload_journal as journal


SENDER_CHILD_TIMEOUT_SECONDS = 900.0
KEYGEN_TIMEOUT_SECONDS = 10.0
EXEC_STATUS_TIMEOUT_SECONDS = 5.0
POST_EXIT_PIPE_DRAIN_SECONDS = 5.0
STDERR_DIAGNOSTIC_BYTE_CAP = 64 * 1024
PIPE_CHUNK_BYTES = 1024 * 1024

# The formal sender is bound to the registered Linux x86-64 hosts.  Python
# does not expose close_range(2) on every supported interpreter, and os.execve
# emits a Python audit event after the last user-space descriptor sweep.  The
# child therefore stages its executable/status descriptors at 3/4, closes the
# complete >=5 namespace in one kernel operation, and enters the pinned inode
# with execveat(AT_EMPTY_PATH).  This leaves exactly 0/1/2 at program entry.
_SYS_EXECVEAT_X86_64 = 322
_SYS_CLOSE_RANGE_X86_64 = 436
_AT_EMPTY_PATH = 0x1000
_UINT_MAX = (1 << 32) - 1
_CHILD_EXECUTABLE_FD = 3
_CHILD_EXEC_STATUS_FD = 4
_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC_SYSCALL = _LIBC.syscall
_LIBC_SYSCALL.restype = ctypes.c_long


class V42PreformalSenderError(RuntimeError):
    pass


class V42PreformalSenderClosureError(V42PreformalSenderError):
    """The effect observation was known but its durable journal close failed."""


def _fail(message: str) -> NoReturn:
    raise V42PreformalSenderError(message)


def _stable_file_state(observed: os.stat_result) -> tuple[int, ...]:
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_uid,
        observed.st_gid,
        observed.st_nlink,
        observed.st_size,
        observed.st_mtime_ns,
        observed.st_ctime_ns,
    )


def _canonical_absolute_path(path: object, label: str) -> str:
    if (
        type(path) is not str
        or not path.startswith("/")
        or "\x00" in path
        or os.path.normpath(path) != path
    ):
        _fail(f"{label} path changed")
    return path


def _hash_open_descriptor(descriptor: int) -> tuple[str, int]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    count = 0
    while True:
        chunk = os.read(descriptor, PIPE_CHUNK_BYTES)
        if not chunk:
            break
        digest.update(chunk)
        count += len(chunk)
    return digest.hexdigest(), count


@dataclass
class _PinnedLocalFile:
    path: str
    descriptor: int
    state: tuple[int, ...]
    mode: int
    uid: int
    gid: int
    nlink: int
    byte_count: int
    sha256: str | None
    label: str
    closed: bool = False

    def verify(self) -> None:
        if self.closed:
            _fail(f"{self.label} pin is closed")
        before = os.fstat(self.descriptor)
        named_before = os.lstat(self.path)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != self.mode
            or before.st_uid != self.uid
            or before.st_gid != self.gid
            or before.st_nlink != self.nlink
            or before.st_size != self.byte_count
            or _stable_file_state(before) != self.state
            or (named_before.st_dev, named_before.st_ino)
            != (before.st_dev, before.st_ino)
        ):
            _fail(f"{self.label} metadata or named identity changed")
        if self.sha256 is not None:
            digest, count = _hash_open_descriptor(self.descriptor)
            if digest != self.sha256 or count != self.byte_count:
                _fail(f"{self.label} bytes changed")
        after = os.fstat(self.descriptor)
        named_after = os.lstat(self.path)
        if (
            _stable_file_state(after) != self.state
            or (named_after.st_dev, named_after.st_ino)
            != (after.st_dev, after.st_ino)
        ):
            _fail(f"{self.label} changed during final rejoin")

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            os.close(self.descriptor)


def _open_local_file_pin(
    *,
    path: object,
    mode: object,
    uid: object,
    gid: object,
    nlink: object,
    byte_count: object,
    sha256: object | None,
    label: str,
) -> _PinnedLocalFile:
    path = _canonical_absolute_path(path, label)
    if any(type(value) is not int for value in (mode, uid, gid, nlink, byte_count)):
        _fail(f"{label} numeric contract changed")
    if nlink != 1 or byte_count <= 0:
        _fail(f"{label} link or size contract changed")
    if sha256 is not None and (
        type(sha256) is not str
        or len(sha256) != 64
        or any(character not in "0123456789abcdef" for character in sha256)
    ):
        _fail(f"{label} hash contract changed")
    if sha256 is None:
        open_flags = getattr(os, "O_PATH", 0)
        if open_flags == 0:
            _fail("local platform lacks O_PATH for private-key metadata pinning")
        open_flags |= os.O_NOFOLLOW | os.O_CLOEXEC
    else:
        open_flags = (
            os.O_RDONLY
            | os.O_NONBLOCK
            | os.O_NOCTTY
            | os.O_NOFOLLOW
            | os.O_CLOEXEC
        )
    descriptor = -1
    try:
        named_before = os.lstat(path)
        descriptor = os.open(path, open_flags)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_uid != uid
            or before.st_gid != gid
            or before.st_nlink != nlink
            or before.st_size != byte_count
            or (named_before.st_dev, named_before.st_ino)
            != (before.st_dev, before.st_ino)
        ):
            _fail(f"{label} initial file fact changed")
        if sha256 is not None:
            digest, count = _hash_open_descriptor(descriptor)
            if digest != sha256 or count != byte_count:
                _fail(f"{label} initial bytes changed")
        after = os.fstat(descriptor)
        named_after = os.lstat(path)
        if (
            _stable_file_state(after) != _stable_file_state(before)
            or (named_after.st_dev, named_after.st_ino)
            != (after.st_dev, after.st_ino)
        ):
            _fail(f"{label} changed during initial pin")
        return _PinnedLocalFile(
            path=path,
            descriptor=descriptor,
            state=_stable_file_state(after),
            mode=mode,
            uid=uid,
            gid=gid,
            nlink=nlink,
            byte_count=byte_count,
            sha256=sha256,
            label=label,
        )
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _openssh_blob_fingerprint(blob: bytes, *, expected_type: bytes) -> str:
    if type(blob) is not bytes:
        _fail("OpenSSH public blob changed type")
    offset = 0
    fields: list[bytes] = []
    for _index in range(2):
        if offset + 4 > len(blob):
            _fail("OpenSSH public blob ended before a length field")
        count = int.from_bytes(blob[offset : offset + 4], "big")
        offset += 4
        if count <= 0 or offset + count > len(blob):
            _fail("OpenSSH public blob field length changed")
        fields.append(blob[offset : offset + count])
        offset += count
    if offset != len(blob) or fields[0] != expected_type or len(fields[1]) != 32:
        _fail("OpenSSH ed25519 public blob structure changed")
    encoded = base64.b64encode(hashlib.sha256(blob).digest()).rstrip(b"=")
    return "SHA256:" + encoded.decode("ascii")


def _strict_public_key_line(raw: bytes, *, byte_cap: int) -> tuple[str, bytes]:
    if not 0 < len(raw) <= byte_cap or not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        _fail("ssh-keygen output is not one bounded newline-terminated line")
    parts = raw[:-1].split(b" ", 2)
    if len(parts) not in {2, 3} or parts[0] != b"ssh-ed25519" or not parts[1]:
        _fail("ssh-keygen output type or field count changed")
    if len(parts) == 3:
        comment = parts[2]
        try:
            comment.decode("utf-8", errors="strict")
        except UnicodeError as error:
            raise V42PreformalSenderError(
                "ssh-keygen trailing comment is not UTF-8"
            ) from error
        if (
            not comment
            or comment.startswith(b" ")
            or comment.endswith(b" ")
            or any(byte < 0x20 or byte == 0x7F for byte in comment)
        ):
            _fail("ssh-keygen trailing comment changed form")
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except ValueError as error:
        raise V42PreformalSenderError("ssh-keygen public blob is not base64") from error
    return "ssh-ed25519", blob


def _verify_known_hosts_fingerprint(contract: dict[str, Any]) -> None:
    raw = transport.PINNED_KNOWN_HOSTS_BYTES
    if (
        hashlib.sha256(raw).hexdigest() != contract["known_hosts_sha256"]
        or len(raw) != contract["known_hosts_byte_count"]
        or not raw.endswith(b"\n")
        or raw.count(b"\n") != 1
    ):
        _fail("pinned known-hosts bytes changed")
    fields = raw[:-1].split(b" ")
    endpoint = f"[{contract['endpoint_host']}]:{contract['endpoint_port']}".encode(
        "ascii"
    )
    if len(fields) != 3 or fields[0] != endpoint or fields[1] != b"ssh-ed25519":
        _fail("pinned known-hosts line changed")
    try:
        blob = base64.b64decode(fields[2], validate=True)
    except ValueError as error:
        raise V42PreformalSenderError("known-host public blob is not base64") from error
    observed = _openssh_blob_fingerprint(blob, expected_type=b"ssh-ed25519")
    if observed != contract["pinned_host_key_fingerprint"]:
        _fail("known-host fingerprint changed")


@dataclass
class _LocalDispatchPins:
    ssh: _PinnedLocalFile
    ssh_keygen: _PinnedLocalFile
    identity: _PinnedLocalFile

    def verify(self) -> None:
        self.ssh.verify()
        self.ssh_keygen.verify()
        self.identity.verify()

    def close(self) -> None:
        for pin in (self.identity, self.ssh_keygen, self.ssh):
            try:
                pin.close()
            except OSError:
                pass


def _open_local_dispatch_pins_v42r1(plan: dict[str, Any]) -> _LocalDispatchPins:
    contract = plan.get("ssh_client_contract")
    if type(contract) is not dict:
        _fail("SSH client contract changed type")
    if (
        contract.get("dispatch_environment") != transport.LOCAL_DISPATCH_ENVIRONMENT
        or contract.get("ssh_child_exact_file_descriptors") != [0, 1, 2]
        or contract.get("ssh_child_stdin_stdout_stderr_must_not_be_tty") is not True
        or contract.get("ssh_child_close_fds_required") is not True
        or contract.get("sender_child_exec_platform") != "LINUX_X86_64"
        or contract.get("sender_child_descriptor_staging")
        != {
            "executable_fd": _CHILD_EXECUTABLE_FD,
            "exec_status_fd": _CHILD_EXEC_STATUS_FD,
            "close_range_first_fd": 5,
        }
        or contract.get("sender_child_direct_syscalls_x86_64")
        != {
            "execveat": _SYS_EXECVEAT_X86_64,
            "close_range": _SYS_CLOSE_RANGE_X86_64,
            "execveat_flags": ["AT_EMPTY_PATH"],
        }
        or contract.get(
            "sender_parent_sigpipe_ignored_from_last_pre_marker_gate_through_reap"
        )
        is not True
        or contract.get(
            "sender_blockable_signals_masked_across_fork_and_child_handlers_reset_before_exec"
        )
        is not True
        or contract.get(
            "sender_python_trace_and_profile_hooks_forbidden_at_every_pre_fork_gate"
        )
        is not True
        or contract.get(
            "sender_child_clears_inherited_trace_and_profile_hooks_before_close_range"
        )
        is not True
        or contract.get(
            "sender_python_ctypes_libc_and_kernel_are_external_local_tcb"
        )
        is not True
        or contract.get("private_key_bytes_or_hash_persisted") is not False
        or contract.get("same_uid_identity_path_replacement_excluded_from_claim")
        is not True
        or contract.get("same_uid_known_hosts_path_replacement_excluded_from_claim")
        is not True
        or contract.get(
            "ssh_dynamic_loader_shared_libraries_nss_and_dns_are_external_host_tcb"
        )
        is not True
    ):
        _fail("SSH dispatch or claim-boundary contract changed")
    _verify_known_hosts_fingerprint(contract)
    ssh: _PinnedLocalFile | None = None
    keygen: _PinnedLocalFile | None = None
    identity: _PinnedLocalFile | None = None
    try:
        ssh = _open_local_file_pin(
            path=contract["ssh_executable"],
            mode=contract["ssh_executable_mode"],
            uid=contract["ssh_executable_uid"],
            gid=contract["ssh_executable_gid"],
            nlink=contract["ssh_executable_nlink"],
            byte_count=contract["ssh_executable_byte_count"],
            sha256=contract["ssh_executable_sha256"],
            label="local SSH executable",
        )
        keygen = _open_local_file_pin(
            path=contract["ssh_keygen_executable"],
            mode=contract["ssh_keygen_mode"],
            uid=contract["ssh_keygen_uid"],
            gid=contract["ssh_keygen_gid"],
            nlink=contract["ssh_keygen_nlink"],
            byte_count=contract["ssh_keygen_byte_count"],
            sha256=contract["ssh_keygen_sha256"],
            label="local ssh-keygen executable",
        )
        identity = _open_local_file_pin(
            path=contract["identity_file"],
            mode=contract["identity_mode"],
            uid=contract["identity_uid"],
            gid=contract["identity_gid"],
            nlink=contract["identity_nlink"],
            byte_count=contract["identity_byte_count"],
            sha256=None,
            label="local SSH private-key metadata",
        )
        pins = _LocalDispatchPins(ssh=ssh, ssh_keygen=keygen, identity=identity)
        pins.verify()
        return pins
    except BaseException:
        for pin in (identity, keygen, ssh):
            if pin is not None:
                pin.close()
        raise


@dataclass(frozen=True)
class _ChildObservation:
    exec_succeeded: bool
    returncode: int | None
    timed_out: bool
    stdin_expected_byte_count: int
    stdin_sent_byte_count: int
    stdin_complete: bool
    stdout_raw: bytes
    stdout_total_byte_count: int
    stdout_sha256: str
    stdout_overflow: bool
    stdout_eof: bool
    stderr_prefix: bytes
    stderr_total_byte_count: int
    stderr_sha256: str
    stderr_overflow: bool
    stderr_eof: bool


def _live_file_descriptors() -> list[int]:
    try:
        names = os.listdir("/proc/self/fd")
    except OSError as error:
        raise V42PreformalSenderError("sender cannot enumerate live descriptors") from error
    result: list[int] = []
    for name in names:
        try:
            descriptor = int(name)
        except ValueError:
            _fail("sender descriptor name changed")
        try:
            fcntl.fcntl(descriptor, fcntl.F_GETFD)
        except OSError as error:
            if error.errno == errno.EBADF:
                continue
            raise
        result.append(descriptor)
    return sorted(result)


def _assert_single_threaded() -> None:
    try:
        tasks = sorted(name for name in os.listdir("/proc/self/task") if name.isdigit())
    except OSError as error:
        raise V42PreformalSenderError("sender cannot enumerate process threads") from error
    if len(tasks) != 1:
        _fail("effectful sender requires an exact single-threaded process")


def _assert_no_python_trace_or_profile_hooks() -> None:
    if sys.gettrace() is not None or sys.getprofile() is not None:
        _fail("effectful sender forbids Python trace and profile hooks")


def _assert_direct_child_exec_platform() -> None:
    if (
        os.name != "posix"
        or os.uname().sysname != "Linux"
        or os.uname().machine not in {"x86_64", "amd64"}
        or not hasattr(fcntl, "F_DUPFD_CLOEXEC")
        or not hasattr(signal, "pthread_sigmask")
        or not hasattr(signal, "valid_signals")
    ):
        _fail("sender direct child-exec platform changed")

    # These probes are effect-free for the calling descriptor namespace.  They
    # distinguish a missing syscall from a later, post-marker child failure.
    ctypes.set_errno(0)
    close_result = _LIBC_SYSCALL(
        _SYS_CLOSE_RANGE_X86_64,
        ctypes.c_uint(_UINT_MAX),
        ctypes.c_uint(_UINT_MAX),
        ctypes.c_uint(0),
    )
    if close_result != 0:
        _fail("sender kernel lacks the required close_range syscall")
    empty_vector = (ctypes.c_char_p * 1)(None)
    ctypes.set_errno(0)
    exec_result = _LIBC_SYSCALL(
        _SYS_EXECVEAT_X86_64,
        ctypes.c_int(-1),
        ctypes.c_char_p(b""),
        empty_vector,
        empty_vector,
        ctypes.c_int(_AT_EMPTY_PATH),
    )
    if exec_result != -1 or ctypes.get_errno() == errno.ENOSYS:
        _fail("sender kernel lacks the required execveat syscall")


def _blockable_signals() -> set[signal.Signals]:
    return {
        signum
        for signum in signal.valid_signals()
        if signum not in {signal.SIGKILL, signal.SIGSTOP}
    }


def _encoded_exec_vectors(
    argv: tuple[str, ...], environment: dict[str, str]
) -> tuple[
    tuple[bytes, ...],
    tuple[bytes, ...],
    Any,
    Any,
]:
    argv_raw = tuple(os.fsencode(value) for value in argv)
    environment_raw = tuple(
        os.fsencode(f"{key}={value}") for key, value in environment.items()
    )
    argv_vector = (ctypes.c_char_p * (len(argv_raw) + 1))(*argv_raw, None)
    environment_vector = (ctypes.c_char_p * (len(environment_raw) + 1))(
        *environment_raw, None
    )
    return argv_raw, environment_raw, argv_vector, environment_vector


@dataclass
class _SigpipeIgnoreGuard:
    previous: Any
    active: bool = True

    @classmethod
    def acquire(cls) -> "_SigpipeIgnoreGuard":
        _assert_single_threaded()
        previous = signal.getsignal(signal.SIGPIPE)
        try:
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            guard = cls(previous=previous)
            guard.verify()
            return guard
        except BaseException:
            try:
                signal.signal(signal.SIGPIPE, previous)
            except BaseException:
                pass
            raise

    def verify(self) -> None:
        if not self.active or signal.getsignal(signal.SIGPIPE) is not signal.SIG_IGN:
            _fail("sender parent SIGPIPE disposition changed")

    def close(self) -> None:
        if self.active:
            try:
                signal.signal(signal.SIGPIPE, self.previous)
                if signal.getsignal(signal.SIGPIPE) != self.previous:
                    _fail("sender parent SIGPIPE disposition was not restored")
            except BaseException:
                # A Python-level asynchronous exception can be delivered at
                # signal.signal's return boundary.  Retry once so the caller
                # can conservatively classify the error without silently
                # leaving its process-wide disposition altered.
                try:
                    signal.signal(signal.SIGPIPE, self.previous)
                except BaseException:
                    pass
                raise
            self.active = False


def _pipe_cloexec() -> tuple[int, int]:
    if not hasattr(os, "pipe2"):
        _fail("local platform lacks atomic CLOEXEC pipes")
    return os.pipe2(os.O_CLOEXEC)


def _returncode_from_wait_status(status: int) -> int:
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    _fail("child wait status is neither exited nor signaled")


def _close_noexcept(descriptor: int) -> None:
    if descriptor >= 0:
        try:
            os.close(descriptor)
        except OSError:
            pass


def _kill_noexcept(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError as error:
        if error.errno != errno.ESRCH:
            raise


def _terminate_and_reap_noexcept(pid: int) -> None:
    try:
        observed_pid, _status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return
    except InterruptedError:
        observed_pid = 0
    if observed_pid == pid:
        return
    _kill_noexcept(pid)
    while True:
        try:
            os.waitpid(pid, 0)
            return
        except InterruptedError:
            continue
        except ChildProcessError:
            return


@dataclass
class _PreparedPinnedChild:
    executable_fd: int
    argv: tuple[str, ...]
    environment: dict[str, str]
    segments: tuple[bytes, ...]
    stdout_cap: int
    stderr_cap: int
    timeout_seconds: float
    stdin_read: int
    stdin_write: int
    stdout_read: int
    stdout_write: int
    stderr_read: int
    stderr_write: int
    exec_status_read: int
    exec_status_write: int
    spawned: bool = False
    closed: bool = False

    def _all_pipe_fds(self) -> tuple[int, ...]:
        return (
            self.stdin_read,
            self.stdin_write,
            self.stdout_read,
            self.stdout_write,
            self.stderr_read,
            self.stderr_write,
            self.exec_status_read,
            self.exec_status_write,
        )

    def verify_prepared(self) -> None:
        if self.closed or self.spawned:
            _fail("prepared child is not at its single-use boundary")
        _assert_single_threaded()
        _assert_no_python_trace_or_profile_hooks()
        _assert_direct_child_exec_platform()
        live = set(_live_file_descriptors())
        required_descriptors = {
            0,
            1,
            2,
            self.executable_fd,
            *self._all_pipe_fds(),
        }
        if (
            not {0, 1, 2}.issubset(live)
            or len(required_descriptors) != 12
            or any(descriptor < 3 for descriptor in required_descriptors - {0, 1, 2})
        ):
            _fail("prepared child descriptor identities changed")
        for descriptor in self._all_pipe_fds():
            if descriptor not in live:
                _fail("prepared child pipe descriptor disappeared")
            if not fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
                _fail("prepared child pipe lost CLOEXEC")
        if self.executable_fd not in live:
            _fail("prepared executable descriptor disappeared")
        if any(
            os.isatty(descriptor)
            for descriptor in (self.stdin_read, self.stdout_write, self.stderr_write)
        ):
            _fail("prepared child stdio unexpectedly uses a tty")
        if (
            not self.argv
            or self.argv[0].startswith("/") is False
            or any(type(value) is not str or "\x00" in value for value in self.argv)
            or self.environment != transport.LOCAL_DISPATCH_ENVIRONMENT
            or any(
                type(key) is not str
                or type(value) is not str
                or "\x00" in key
                or "\x00" in value
                for key, value in self.environment.items()
            )
        ):
            _fail("prepared child argv or environment changed")

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            for descriptor in self._all_pipe_fds():
                _close_noexcept(descriptor)

    def spawn_and_pump(self) -> _ChildObservation:
        self.verify_prepared()
        started = time.monotonic()
        deadline = started + self.timeout_seconds
        try:
            (
                argv_raw,
                environment_raw,
                argv_vector,
                environment_vector,
            ) = _encoded_exec_vectors(self.argv, self.environment)
            # Keep the encoded byte owners alive through fork and the direct
            # child syscall; ctypes pointer arrays do not own separate copies.
            if not argv_raw or len(environment_raw) != len(self.environment):
                _fail("prepared child exec vectors changed")
            sigpipe_guard = _SigpipeIgnoreGuard.acquire()
        except BaseException:
            self.close()
            raise
        self.spawned = True
        previous_mask: set[signal.Signals] | None = None
        pid: int | None = None
        try:
            previous_mask = signal.pthread_sigmask(
                signal.SIG_BLOCK, _blockable_signals()
            )
            pid = os.fork()
        except BaseException:
            self.close()
            if previous_mask is not None:
                try:
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                except BaseException:
                    pass
            try:
                sigpipe_guard.close()
            except BaseException:
                pass
            raise
        if pid == 0:
            status_descriptor = self.exec_status_write
            try:
                # A hook installed by the os.fork audit event is inherited by
                # the child.  Clear both tracing mechanisms while signals are
                # still blocked and before the final descriptor sweep.
                sys.settrace(None)
                sys.setprofile(None)
                staged_executable = fcntl.fcntl(
                    self.executable_fd, fcntl.F_DUPFD_CLOEXEC, 5
                )
                staged_status = fcntl.fcntl(
                    self.exec_status_write, fcntl.F_DUPFD_CLOEXEC, 5
                )
                os.dup2(self.stdin_read, 0, inheritable=True)
                os.dup2(self.stdout_write, 1, inheritable=True)
                os.dup2(self.stderr_write, 2, inheritable=True)
                os.dup2(
                    staged_executable, _CHILD_EXECUTABLE_FD, inheritable=False
                )
                os.dup2(staged_status, _CHILD_EXEC_STATUS_FD, inheritable=False)
                status_descriptor = _CHILD_EXEC_STATUS_FD
                # Signals remain blocked from before fork while inherited
                # Python handlers are removed.  Thus no handler can create a
                # descriptor between the final close_range and execveat.
                for signum in sorted(_blockable_signals(), key=int):
                    signal.signal(signum, signal.SIG_DFL)
                close_result = _LIBC_SYSCALL(
                    _SYS_CLOSE_RANGE_X86_64,
                    ctypes.c_uint(5),
                    ctypes.c_uint(_UINT_MAX),
                    ctypes.c_uint(0),
                )
                if close_result != 0:
                    raise OSError("child close_range failed")
                signal.pthread_sigmask(signal.SIG_SETMASK, set())
                _LIBC_SYSCALL(
                    _SYS_EXECVEAT_X86_64,
                    ctypes.c_int(_CHILD_EXECUTABLE_FD),
                    ctypes.c_char_p(b""),
                    argv_vector,
                    environment_vector,
                    ctypes.c_int(_AT_EMPTY_PATH),
                )
                raise OSError("child execveat failed")
            except BaseException:
                try:
                    os.write(status_descriptor, b"E")
                except BaseException:
                    pass
                os._exit(127)
        try:
            # From this first parent-side instruction onward every exception
            # owns and reaps pid.  All catchable signals remain blocked until
            # that ownership and the parent endpoint state are established.
            for descriptor in (
                self.stdin_read,
                self.stdout_write,
                self.stderr_write,
                self.exec_status_write,
            ):
                _close_noexcept(descriptor)
            self.stdin_read = -1
            self.stdout_write = -1
            self.stderr_write = -1
            self.exec_status_write = -1
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            previous_mask = None
            sigpipe_guard.verify()

            exec_succeeded = False
            exec_timed_out = False
            try:
                os.set_blocking(self.exec_status_read, False)
                exec_deadline = min(
                    deadline, time.monotonic() + EXEC_STATUS_TIMEOUT_SECONDS
                )
                exec_bytes = bytearray()
                while True:
                    try:
                        chunk = os.read(self.exec_status_read, 16)
                    except BlockingIOError:
                        chunk = None
                    except InterruptedError:
                        continue
                    if chunk == b"":
                        exec_succeeded = not exec_bytes
                        break
                    if chunk:
                        exec_bytes.extend(chunk)
                        if len(exec_bytes) > 1:
                            break
                    remaining = exec_deadline - time.monotonic()
                    if remaining <= 0:
                        exec_timed_out = True
                        break
                    selector = selectors.DefaultSelector()
                    try:
                        selector.register(self.exec_status_read, selectors.EVENT_READ)
                        selector.select(min(remaining, 0.25))
                    finally:
                        selector.close()
            finally:
                _close_noexcept(self.exec_status_read)
                self.exec_status_read = -1
            if exec_timed_out:
                _kill_noexcept(pid)
            observation = _pump_child_process(
                pid=pid,
                stdin_fd=self.stdin_write,
                stdout_fd=self.stdout_read,
                stderr_fd=self.stderr_read,
                segments=self.segments if exec_succeeded else (),
                expected_input_byte_count=sum(len(segment) for segment in self.segments),
                stdout_cap=self.stdout_cap,
                stderr_cap=self.stderr_cap,
                deadline=deadline,
                exec_succeeded=exec_succeeded,
                already_timed_out=exec_timed_out,
            )
            self.stdin_write = -1
            self.stdout_read = -1
            self.stderr_read = -1
            self.closed = True
            sigpipe_guard.close()
            return observation
        except BaseException:
            self.close()
            _terminate_and_reap_noexcept(pid)
            if previous_mask is not None:
                try:
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                except BaseException:
                    pass
            try:
                sigpipe_guard.close()
            except BaseException:
                pass
            raise


def _prepare_pinned_child(
    *,
    executable_fd: int,
    argv: tuple[str, ...],
    environment: dict[str, str],
    segments: tuple[bytes, ...],
    stdout_cap: int,
    stderr_cap: int,
    timeout_seconds: float,
) -> _PreparedPinnedChild:
    if (
        type(executable_fd) is not int
        or executable_fd < 0
        or type(argv) is not tuple
        or type(environment) is not dict
        or type(segments) is not tuple
        or any(type(segment) is not bytes for segment in segments)
        or type(stdout_cap) is not int
        or not 0 < stdout_cap <= 1024 * 1024
        or type(stderr_cap) is not int
        or not 0 < stderr_cap <= 1024 * 1024
        or type(timeout_seconds) is not float
        or not 0.0 < timeout_seconds <= SENDER_CHILD_TIMEOUT_SECONDS
    ):
        _fail("prepared child resource contract changed")
    descriptors: list[int] = []
    try:
        stdin_read, stdin_write = _pipe_cloexec()
        descriptors.extend((stdin_read, stdin_write))
        stdout_read, stdout_write = _pipe_cloexec()
        descriptors.extend((stdout_read, stdout_write))
        stderr_read, stderr_write = _pipe_cloexec()
        descriptors.extend((stderr_read, stderr_write))
        exec_status_read, exec_status_write = _pipe_cloexec()
        descriptors.extend((exec_status_read, exec_status_write))
        prepared = _PreparedPinnedChild(
            executable_fd=executable_fd,
            argv=argv,
            environment=dict(environment),
            segments=segments,
            stdout_cap=stdout_cap,
            stderr_cap=stderr_cap,
            timeout_seconds=timeout_seconds,
            stdin_read=stdin_read,
            stdin_write=stdin_write,
            stdout_read=stdout_read,
            stdout_write=stdout_write,
            stderr_read=stderr_read,
            stderr_write=stderr_write,
            exec_status_read=exec_status_read,
            exec_status_write=exec_status_write,
        )
        prepared.verify_prepared()
        return prepared
    except BaseException:
        for descriptor in descriptors:
            _close_noexcept(descriptor)
        raise


def _pump_child_process(
    *,
    pid: int,
    stdin_fd: int,
    stdout_fd: int,
    stderr_fd: int,
    segments: tuple[bytes, ...],
    expected_input_byte_count: int,
    stdout_cap: int,
    stderr_cap: int,
    deadline: float,
    exec_succeeded: bool,
    already_timed_out: bool,
) -> _ChildObservation:
    for descriptor in (stdin_fd, stdout_fd, stderr_fd):
        os.set_blocking(descriptor, False)
    selector = selectors.DefaultSelector()
    stdout_digest = hashlib.sha256()
    stderr_digest = hashlib.sha256()
    stdout_prefix = bytearray()
    stderr_prefix = bytearray()
    stdout_total = 0
    stderr_total = 0
    stdout_eof = False
    stderr_eof = False
    sent = 0
    segment_index = 0
    segment_offset = 0
    stdin_complete = expected_input_byte_count == 0 and exec_succeeded
    timed_out = already_timed_out
    killed = already_timed_out
    status: int | None = None
    post_exit_deadline: float | None = None

    def close_registered(descriptor: int) -> None:
        try:
            selector.unregister(descriptor)
        except (KeyError, ValueError):
            pass
        _close_noexcept(descriptor)

    try:
        selector.register(stdout_fd, selectors.EVENT_READ, "stdout")
        selector.register(stderr_fd, selectors.EVENT_READ, "stderr")
        if exec_succeeded and segments:
            selector.register(stdin_fd, selectors.EVENT_WRITE, "stdin")
        else:
            _close_noexcept(stdin_fd)
            stdin_fd = -1
        while selector.get_map() or status is None:
            now = time.monotonic()
            if status is None:
                try:
                    observed_pid, observed_status = os.waitpid(pid, os.WNOHANG)
                except InterruptedError:
                    observed_pid = 0
                    observed_status = 0
                if observed_pid == pid:
                    status = observed_status
                    post_exit_deadline = now + POST_EXIT_PIPE_DRAIN_SECONDS
            if status is None and now >= deadline and not killed:
                timed_out = True
                killed = True
                _kill_noexcept(pid)
                if stdin_fd >= 0:
                    close_registered(stdin_fd)
                    stdin_fd = -1
                post_exit_deadline = now + POST_EXIT_PIPE_DRAIN_SECONDS
            if post_exit_deadline is not None and now >= post_exit_deadline:
                for key in list(selector.get_map().values()):
                    close_registered(key.fd)
                break
            if killed and status is None and not selector.get_map():
                while True:
                    try:
                        _observed_pid, status = os.waitpid(pid, 0)
                        break
                    except InterruptedError:
                        continue
                break
            timeout = 0.25
            if killed:
                timeout = min(timeout, 0.01)
            if status is None:
                timeout = min(timeout, max(0.0, deadline - now))
            if post_exit_deadline is not None:
                timeout = min(timeout, max(0.0, post_exit_deadline - now))
            events = selector.select(timeout)
            for key, _mask in events:
                descriptor = key.fd
                role = key.data
                if role == "stdin":
                    if segment_index >= len(segments):
                        stdin_complete = sent == expected_input_byte_count
                        close_registered(descriptor)
                        stdin_fd = -1
                        continue
                    segment = segments[segment_index]
                    view = memoryview(segment)[
                        segment_offset : segment_offset + PIPE_CHUNK_BYTES
                    ]
                    try:
                        written = os.write(descriptor, view)
                    except (BlockingIOError, InterruptedError):
                        continue
                    except BrokenPipeError:
                        close_registered(descriptor)
                        stdin_fd = -1
                        continue
                    if written <= 0:
                        close_registered(descriptor)
                        stdin_fd = -1
                        continue
                    sent += written
                    segment_offset += written
                    if segment_offset == len(segment):
                        segment_index += 1
                        segment_offset = 0
                        if segment_index == len(segments):
                            stdin_complete = sent == expected_input_byte_count
                            close_registered(descriptor)
                            stdin_fd = -1
                else:
                    # Exactly one bounded read per ready descriptor per
                    # selector round.  Continuous output can therefore neither
                    # starve stdin/stderr nor postpone the next deadline check.
                    try:
                        chunk = os.read(descriptor, PIPE_CHUNK_BYTES)
                    except (BlockingIOError, InterruptedError):
                        continue
                    if not chunk:
                        close_registered(descriptor)
                        if role == "stdout":
                            stdout_eof = True
                            stdout_fd = -1
                        else:
                            stderr_eof = True
                            stderr_fd = -1
                        continue
                    if role == "stdout":
                        stdout_digest.update(chunk)
                        stdout_total += len(chunk)
                        remaining = stdout_cap + 1 - len(stdout_prefix)
                        if remaining > 0:
                            stdout_prefix.extend(chunk[:remaining])
                    else:
                        stderr_digest.update(chunk)
                        stderr_total += len(chunk)
                        remaining = stderr_cap - len(stderr_prefix)
                        if remaining > 0:
                            stderr_prefix.extend(chunk[:remaining])
        if status is None:
            _kill_noexcept(pid)
            while True:
                try:
                    _observed_pid, status = os.waitpid(pid, 0)
                    break
                except InterruptedError:
                    continue
        return _ChildObservation(
            exec_succeeded=exec_succeeded,
            returncode=_returncode_from_wait_status(status),
            timed_out=timed_out,
            stdin_expected_byte_count=expected_input_byte_count,
            stdin_sent_byte_count=sent,
            stdin_complete=stdin_complete,
            stdout_raw=bytes(stdout_prefix),
            stdout_total_byte_count=stdout_total,
            stdout_sha256=stdout_digest.hexdigest(),
            stdout_overflow=stdout_total > stdout_cap,
            stdout_eof=stdout_eof,
            stderr_prefix=bytes(stderr_prefix),
            stderr_total_byte_count=stderr_total,
            stderr_sha256=stderr_digest.hexdigest(),
            stderr_overflow=stderr_total > stderr_cap,
            stderr_eof=stderr_eof,
        )
    finally:
        selector.close()
        for descriptor in (stdin_fd, stdout_fd, stderr_fd):
            _close_noexcept(descriptor)
        if status is None:
            try:
                _kill_noexcept(pid)
            finally:
                while True:
                    try:
                        os.waitpid(pid, 0)
                        break
                    except InterruptedError:
                        continue
                    except ChildProcessError:
                        break


def _derive_identity_fingerprint_v42r1(
    *, plan: dict[str, Any], pins: _LocalDispatchPins
) -> str:
    contract = plan["ssh_client_contract"]
    argv = tuple(contract["identity_public_derivation_argv"])
    if argv != (
        contract["ssh_keygen_executable"],
        "-y",
        "-f",
        contract["identity_file"],
    ):
        _fail("ssh-keygen derivation argv changed")
    pins.verify()
    prepared = _prepare_pinned_child(
        executable_fd=pins.ssh_keygen.descriptor,
        argv=argv,
        environment=dict(transport.LOCAL_DISPATCH_ENVIRONMENT),
        segments=(),
        stdout_cap=contract["identity_public_output_byte_cap"],
        stderr_cap=STDERR_DIAGNOSTIC_BYTE_CAP,
        timeout_seconds=float(KEYGEN_TIMEOUT_SECONDS),
    )
    try:
        observation = prepared.spawn_and_pump()
    finally:
        prepared.close()
    if (
        not observation.exec_succeeded
        or observation.returncode != 0
        or observation.timed_out
        or observation.stdout_overflow
        or not observation.stdout_eof
        or observation.stderr_total_byte_count != 0
        or not observation.stderr_eof
    ):
        _fail("ssh-keygen public derivation did not close exactly")
    key_type, blob = _strict_public_key_line(
        observation.stdout_raw,
        byte_cap=contract["identity_public_output_byte_cap"],
    )
    if (
        key_type != contract["identity_public_key_type"]
        or len(blob) != contract["identity_public_blob_byte_count"]
        or contract.get("identity_public_trailing_comment_is_non_authoritative")
        is not True
    ):
        _fail("derived SSH public blob changed")
    fingerprint = _openssh_blob_fingerprint(
        blob, expected_type=contract["identity_public_key_type"].encode("ascii")
    )
    if fingerprint != contract["identity_public_fingerprint"]:
        _fail("derived SSH identity fingerprint changed")
    pins.verify()
    return fingerprint


def _normalized_sender_inputs(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, bytes],
    bytes,
    bytes,
    list[dict[str, dict[str, Any]]],
]:
    if type(control_raw_by_name) is not dict or any(
        type(name) is not str or type(raw) is not bytes
        for name, raw in control_raw_by_name.items()
    ):
        _fail("sender controls must be an exact bytes mapping")
    if type(loader_source_raw) is not bytes or type(receiver_source_raw) is not bytes:
        _fail("sender program artifacts must be immutable bytes")
    controls = dict(control_raw_by_name)
    loader = loader_source_raw
    receiver = receiver_source_raw
    caller_chain = [] if predecessor_chain is None else predecessor_chain
    chain = loads_canonical_json(canonical_json_bytes(caller_chain))
    if type(chain) is not list:
        _fail("sender predecessor chain changed type")
    normalized_plan = transport.verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=controls,
        loader_source_raw=loader,
        receiver_source_raw=receiver,
        predecessor_chain=chain,
    )
    normalized_attempt = transport.verify_preformal_upload_attempt_against_controls_v42r1(
        attempt,
        plan=normalized_plan,
        control_raw_by_name=controls,
        loader_source_raw=loader,
        receiver_source_raw=receiver,
        predecessor_chain=chain,
    )
    header = transport.build_preformal_upload_stream_header_v42r1(
        plan=normalized_plan,
        attempt=normalized_attempt,
        control_raw_by_name=controls,
        loader_source_raw=loader,
        receiver_source_raw=receiver,
        predecessor_chain=chain,
    )
    return (
        normalized_plan,
        normalized_attempt,
        header,
        controls,
        loader,
        receiver,
        chain,
    )


def _outbound_segments_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    header: dict[str, Any],
    controls: dict[str, bytes],
    receiver_source_raw: bytes,
) -> tuple[bytes, ...]:
    header_raw = canonical_json_bytes(header)
    body_by_name = {
        transport.PREFORMAL_PLAN_NAME: canonical_json_bytes(plan),
        transport.PREFORMAL_ATTEMPT_NAME: canonical_json_bytes(attempt),
        **controls,
    }
    frames = header["frames"]
    if [frame["name"] for frame in frames] != list(
        transport.PREFORMAL_STREAM_FRAME_ORDER
    ):
        _fail("sender stream frame order changed")
    bodies: list[bytes] = []
    for frame in frames:
        raw = body_by_name[frame["name"]]
        if (
            len(raw) != frame["byte_count"]
            or hashlib.sha256(raw).hexdigest() != frame["sha256"]
        ):
            _fail("sender stream body differs from its frame header")
        bodies.append(raw)
    return (
        receiver_source_raw,
        transport.PREFORMAL_STREAM_MAGIC.encode("ascii") + b"\0",
        len(header_raw).to_bytes(8, "big"),
        header_raw,
        *bodies,
    )


def _complete_receipt_from_observation(
    *,
    observation: _ChildObservation,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    controls: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    if (
        not observation.exec_succeeded
        or observation.returncode != 0
        or observation.timed_out
        or not observation.stdin_complete
        or observation.stdin_sent_byte_count
        != observation.stdin_expected_byte_count
        or observation.stdout_overflow
        or not observation.stdout_eof
        or observation.stdout_total_byte_count != len(observation.stdout_raw)
        or not observation.stderr_eof
    ):
        return None
    try:
        parsed = loads_canonical_json(observation.stdout_raw)
        if type(parsed) is not dict:
            return None
        return transport.verify_preformal_upload_receipt_against_controls_v42r1(
            parsed,
            plan=plan,
            attempt=attempt,
            control_raw_by_name=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=predecessor_chain,
        )
    except BaseException:
        return None


@dataclass(frozen=True)
class V42PreformalSenderResult:
    network_start: dict[str, Any] | None
    receipt: dict[str, Any] | None
    outcome: dict[str, Any]
    diagnostic_code: str
    child_returncode: int | None
    stdout_byte_count: int
    stdout_sha256: str | None
    stderr_byte_count: int
    stderr_sha256: str | None


def _build_and_publish_outcome(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    controls: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]],
    outcome_class: str,
    abandonment_reason_code: str | None,
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    outcome = transport.build_preformal_upload_outcome_v42r1(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=controls,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        outcome_class=outcome_class,
        receipt=receipt,
        abandonment_reason_code=abandonment_reason_code,
        predecessor_chain=predecessor_chain,
    )
    return journal.publish_outcome_v42r1(
        plan=plan,
        attempt=attempt,
        outcome=outcome,
        control_raw_by_name=controls,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        receipt=receipt,
        predecessor_chain=predecessor_chain,
    )


def _network_start_document(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    controls: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    return transport.build_preformal_network_start_v42r1(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=controls,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )


def _recover_after_pre_network_publication_error(
    *,
    original_error: BaseException,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    controls: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]],
) -> V42PreformalSenderResult | None:
    try:
        inspection = journal.inspect_preformal_upload_journal_v42r1(
            plan=plan,
            attempt=attempt,
            control_raw_by_name=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=predecessor_chain,
        )
    except BaseException as inspection_error:
        raise original_error from inspection_error
    if inspection.state in {"PRE_NETWORK_PREFIX", "PRE_NETWORK_BASE"}:
        return None
    if inspection.state == "TERMINAL":
        if inspection.outcome is None:
            _fail("terminal journal inspection omitted its outcome")
        local_failure = inspection.outcome["outcome_class"] == (
            transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE
        )
        return V42PreformalSenderResult(
            network_start=(
                None
                if local_failure
                else _network_start_document(
                    plan=plan,
                    attempt=attempt,
                    controls=controls,
                    loader_source_raw=loader_source_raw,
                    receiver_source_raw=receiver_source_raw,
                    predecessor_chain=predecessor_chain,
                )
            ),
            receipt=inspection.receipt,
            outcome=inspection.outcome,
            diagnostic_code="RECOVERED_TERMINAL_JOURNAL",
            child_returncode=None,
            stdout_byte_count=0,
            stdout_sha256=None,
            stderr_byte_count=0,
            stderr_sha256=None,
        )
    if inspection.state == "POSTNETWORK_UNRESOLVED":
        receipt = None
        outcome_class = transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS
        reason = transport.PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS
        diagnostic = "RECOVERED_POSTNETWORK_AS_AMBIGUOUS"
    elif inspection.state == "COMPLETE_RECEIPT_PENDING_OUTCOME":
        if inspection.receipt is None:
            _fail("complete receipt recovery omitted its receipt")
        receipt = inspection.receipt
        outcome_class = transport.PREFORMAL_OUTCOME_COMPLETE
        reason = None
        diagnostic = "RECOVERED_COMPLETE_RECEIPT"
    else:
        _fail("journal inspection returned an unknown sender state")
    try:
        outcome = _build_and_publish_outcome(
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=predecessor_chain,
            outcome_class=outcome_class,
            abandonment_reason_code=reason,
            receipt=receipt,
        )
    except BaseException as close_error:
        raise V42PreformalSenderClosureError(
            "existing pre-formal journal state could not be durably closed"
        ) from close_error
    return V42PreformalSenderResult(
        network_start=_network_start_document(
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=predecessor_chain,
        ),
        receipt=receipt,
        outcome=outcome,
        diagnostic_code=diagnostic,
        child_returncode=None,
        stdout_byte_count=0,
        stdout_sha256=None,
        stderr_byte_count=0,
        stderr_sha256=None,
    )


def execute_preformal_upload_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> V42PreformalSenderResult:
    (
        plan,
        attempt,
        header,
        controls,
        loader_source_raw,
        receiver_source_raw,
        chain,
    ) = _normalized_sender_inputs(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    segments = _outbound_segments_v42r1(
        plan=plan,
        attempt=attempt,
        header=header,
        controls=controls,
        receiver_source_raw=receiver_source_raw,
    )
    argv = tuple(
        transport.materialize_preformal_upload_ssh_argv_v42r1(
            plan=plan,
            attempt=attempt,
            control_raw_by_name=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
        )
    )
    try:
        journal.publish_pre_network_journal_v42r1(
            plan=plan,
            attempt=attempt,
            control_raw_by_name=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
        )
    except BaseException as pre_network_error:
        recovered = _recover_after_pre_network_publication_error(
            original_error=pre_network_error,
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
        )
        if recovered is not None:
            return recovered
        journal.publish_pre_network_journal_v42r1(
            plan=plan,
            attempt=attempt,
            control_raw_by_name=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
        )

    boundary: journal.HeldNetworkStartBoundaryV42r1 | None = None
    pins: _LocalDispatchPins | None = None
    prepared: _PreparedPinnedChild | None = None
    dispatch_sigpipe_guard: _SigpipeIgnoreGuard | None = None
    network_start: dict[str, Any] | None = None
    observation: _ChildObservation | None = None
    failure: BaseException | None = None
    marker_may_have_started = False
    try:
        boundary = journal.hold_network_start_boundary_v42r1(
            plan=plan,
            attempt=attempt,
            control_raw_by_name=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
        )
        pins = _open_local_dispatch_pins_v42r1(plan)
        prepared = _prepare_pinned_child(
            executable_fd=pins.ssh.descriptor,
            argv=argv,
            environment=dict(transport.LOCAL_DISPATCH_ENVIRONMENT),
            segments=segments,
            stdout_cap=transport.MAXIMUM_RECEIPT_STDOUT_BYTES,
            stderr_cap=STDERR_DIAGNOSTIC_BYTE_CAP,
            timeout_seconds=float(SENDER_CHILD_TIMEOUT_SECONDS),
        )
        fingerprint = _derive_identity_fingerprint_v42r1(plan=plan, pins=pins)
        if fingerprint != plan["ssh_client_contract"]["identity_public_fingerprint"]:
            _fail("last pre-marker identity fingerprint changed")
        # Install the parent EPIPE semantics before the irreversible marker and
        # retain them until the child is reaped and all pipe observations close.
        dispatch_sigpipe_guard = _SigpipeIgnoreGuard.acquire()
        prepared.verify_prepared()
        pins.verify()
        dispatch_sigpipe_guard.verify()
        boundary.verify_exact(durable=True)
        network_start = boundary.publish_once()
        marker_may_have_started = boundary.marker_effect_may_have_started
        prepared.verify_prepared()
        pins.verify()
        dispatch_sigpipe_guard.verify()
        boundary.verify_exact()
        observation = prepared.spawn_and_pump()
        dispatch_sigpipe_guard.verify()
        pins.verify()
        boundary.verify_exact(durable=True)
    except BaseException as error:
        failure = error
        if boundary is not None:
            marker_may_have_started = boundary.marker_effect_may_have_started
    finally:
        if prepared is not None:
            prepared.close()
        if pins is not None:
            pins.close()
        if boundary is not None:
            boundary.close()
        if dispatch_sigpipe_guard is not None:
            try:
                dispatch_sigpipe_guard.close()
            except BaseException as restore_error:
                if failure is None:
                    failure = restore_error

    if not marker_may_have_started:
        try:
            outcome = _build_and_publish_outcome(
                plan=plan,
                attempt=attempt,
                controls=controls,
                loader_source_raw=loader_source_raw,
                receiver_source_raw=receiver_source_raw,
                predecessor_chain=chain,
                outcome_class=transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE,
                abandonment_reason_code=transport.PREFORMAL_ABANDONMENT_REASON_LOCAL,
                receipt=None,
            )
        except BaseException as close_error:
            raise V42PreformalSenderClosureError(
                "pre-network sender failure could not be durably closed"
            ) from close_error
        return V42PreformalSenderResult(
            network_start=None,
            receipt=None,
            outcome=outcome,
            diagnostic_code="LOCAL_PRE_NETWORK_FAILURE",
            child_returncode=None,
            stdout_byte_count=0,
            stdout_sha256=None,
            stderr_byte_count=0,
            stderr_sha256=None,
        )

    if network_start is None:
        network_start = _network_start_document(
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
        )
    receipt = None
    if failure is None and observation is not None:
        receipt = _complete_receipt_from_observation(
            observation=observation,
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
        )
    if receipt is not None:
        outcome_class = transport.PREFORMAL_OUTCOME_COMPLETE
        reason = None
        diagnostic = "COMPLETE_EXACT_RECEIPT"
    else:
        outcome_class = transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS
        reason = transport.PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS
        diagnostic = "POSTNETWORK_WITHOUT_EXACT_COMPLETE_RECEIPT"
    try:
        outcome = _build_and_publish_outcome(
            plan=plan,
            attempt=attempt,
            controls=controls,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
            outcome_class=outcome_class,
            abandonment_reason_code=reason,
            receipt=receipt,
        )
    except BaseException as close_error:
        raise V42PreformalSenderClosureError(
            "post-network sender observation could not be durably closed"
        ) from close_error
    return V42PreformalSenderResult(
        network_start=network_start,
        receipt=receipt,
        outcome=outcome,
        diagnostic_code=diagnostic,
        child_returncode=None if observation is None else observation.returncode,
        stdout_byte_count=(
            0 if observation is None else observation.stdout_total_byte_count
        ),
        stdout_sha256=None if observation is None else observation.stdout_sha256,
        stderr_byte_count=(
            0 if observation is None else observation.stderr_total_byte_count
        ),
        stderr_sha256=None if observation is None else observation.stderr_sha256,
    )


__all__ = [
    "V42PreformalSenderClosureError",
    "V42PreformalSenderError",
    "V42PreformalSenderResult",
    "execute_preformal_upload_v42r1",
]
