#!/usr/bin/env python3
"""Strict one-entry launcher for the V42 pre-formal upload sender.

The launcher is deliberately stdlib-only until it has read the exact local
five-control capsule and bound every local effectful source file to both the
capsule transport manifest and the selected committed HEAD.  It accepts one
fresh lowercase hexadecimal upload token.  The first-attempt predecessor chain
is always the literal empty list; same-token re-entry is delegated once to the
audited sender, whose journal recovery states prevent a second network start.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import sys
import time
from types import MappingProxyType, ModuleType
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
SCRIPT_PATH = ROOT / "scripts/launch_v42_preformal_upload_sender.py"
FIXED_LOCAL_CAPSULE_ROOT = (
    ROOT / ".tmp/exact-freeze/v42-standard-2048-remote-ordinal2-capsule"
)

LOCAL_PYTHON = "/usr/bin/python3"
LOCAL_PYTHON_REALPATH = "/usr/bin/python3.10"
LOCAL_PYTHON_VERSION = (3, 10, 12)
GIT_EXECUTABLE = "/usr/bin/git"
GIT_EXECUTABLE_REALPATH = "/usr/bin/git"
GIT_EXECUTABLE_SHA256 = (
    "587ef21868c948b883993e23209b86a72a6ddc06aab1545c697ffc31075acd4a"
)
GIT_EXECUTABLE_BYTE_COUNT = 3_710_360
GIT_EXECUTABLE_MODE = 0o755
GIT_EXECUTABLE_UID = 0
GIT_EXECUTABLE_GID = 0
GIT_EXECUTABLE_NLINK = 1
GIT_VERSION_STDOUT = b"git version 2.34.1\n"
GIT_QUERY_TIMEOUT_SECONDS = 30.0
GIT_STDOUT_BYTE_CAP = 4 * 1024**2
GIT_STDERR_BYTE_CAP = 64 * 1024
GIT_POST_EXIT_DRAIN_SECONDS = 2.0
GIT_EXEC_STATUS_TIMEOUT_SECONDS = 5.0

_SYS_EXECVEAT_X86_64 = 322
_SYS_CLOSE_RANGE_X86_64 = 436
_AT_EMPTY_PATH = 0x1000
_UINT_MAX = (1 << 32) - 1
_CHILD_EXECUTABLE_FD = 3
_CHILD_EXEC_STATUS_FD = 4
_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC_SYSCALL = _LIBC.syscall
_LIBC_SYSCALL.restype = ctypes.c_long

SOURCE_MANIFEST_NAME = "EXECUTION_SOURCE_MANIFEST.json"
LOCAL_MATERIALIZATION_ATTEMPT_NAME = "LOCAL_MATERIALIZATION_ATTEMPT.json"
REMOTE_BOOTSTRAP_PYZ_NAME = "REMOTE_BOOTSTRAP.pyz"
SOURCE_CAPSULE_NAME = "SOURCE_CAPSULE.tar"
TRANSPORT_MANIFEST_NAME = "TRANSPORT_MANIFEST.json"
CONTROL_NAMES = tuple(
    sorted(
        (
            SOURCE_MANIFEST_NAME,
            LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            REMOTE_BOOTSTRAP_PYZ_NAME,
            SOURCE_CAPSULE_NAME,
            TRANSPORT_MANIFEST_NAME,
        )
    )
)
MAXIMUM_CONTROL_BYTES = {
    SOURCE_MANIFEST_NAME: 64 * 1024**2,
    LOCAL_MATERIALIZATION_ATTEMPT_NAME: 4 * 1024**2,
    REMOTE_BOOTSTRAP_PYZ_NAME: 64 * 1024**2,
    SOURCE_CAPSULE_NAME: 2 * 1024**3,
    TRANSPORT_MANIFEST_NAME: 64 * 1024**2,
}
MAXIMUM_TCB_SOURCE_BYTES = 8 * 1024**2
READ_CHUNK_BYTES = 1024 * 1024

LOADER_SOURCE_RELATIVE = "scripts/v42_preformal_upload_loader.py"
RECEIVER_SOURCE_RELATIVE = "scripts/v42_preformal_upload_receiver.py"
LAUNCHER_SOURCE_RELATIVE = "scripts/launch_v42_preformal_upload_sender.py"
SENDER_SOURCE_RELATIVE = "scripts/run_v42_preformal_upload_sender.py"
JOURNAL_SOURCE_RELATIVE = "scripts/publish_v42_preformal_upload_journal.py"
TRANSPORT_SOURCE_RELATIVE = (
    "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py"
)

# This is the exact repository-local Python closure that can influence the
# call into execute_preformal_upload_v42r1.  Loader and receiver are verified
# even though they are transported as bytes rather than imported locally.
LOCAL_EFFECTFUL_TCB_PATHS = tuple(
    sorted(
        (
            "scripts/__init__.py",
            LAUNCHER_SOURCE_RELATIVE,
            SENDER_SOURCE_RELATIVE,
            JOURNAL_SOURCE_RELATIVE,
            LOADER_SOURCE_RELATIVE,
            RECEIVER_SOURCE_RELATIVE,
            "src/acfqp/__init__.py",
            "src/acfqp/artifacts.py",
            "src/acfqp/build_coverage.py",
            "src/acfqp/construction_k7_domain_registry_extension_v42.py",
            "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
            TRANSPORT_SOURCE_RELATIVE,
            "src/acfqp/core.py",
            "src/acfqp/enumeration.py",
            "src/acfqp/phase3e_ids.py",
        )
    )
)

EXPECTED_IMPORTED_REPOSITORY_MODULES = {
    "acfqp": "src/acfqp/__init__.py",
    "acfqp.artifacts": "src/acfqp/artifacts.py",
    "acfqp.build_coverage": "src/acfqp/build_coverage.py",
    "acfqp.construction_k7_domain_registry_extension_v42": (
        "src/acfqp/construction_k7_domain_registry_extension_v42.py"
    ),
    "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1": (
        "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py"
    ),
    "acfqp.construction_k7_standard_2048_materialization_transport_v42r1": (
        TRANSPORT_SOURCE_RELATIVE
    ),
    "acfqp.core": "src/acfqp/core.py",
    "acfqp.enumeration": "src/acfqp/enumeration.py",
    "acfqp.phase3e_ids": "src/acfqp/phase3e_ids.py",
    "scripts": "scripts/__init__.py",
    "scripts.publish_v42_preformal_upload_journal": JOURNAL_SOURCE_RELATIVE,
    "scripts.run_v42_preformal_upload_sender": SENDER_SOURCE_RELATIVE,
}

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_GIT_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
}


class V42PreformalSenderLauncherError(RuntimeError):
    """The local capsule, selected commit, entry, or recovery state changed."""


def _fail(message: str) -> NoReturn:
    raise V42PreformalSenderLauncherError(message)


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42PreformalSenderLauncherError(
            "launcher result is not canonical JSON"
        ) from error


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("control JSON contains a duplicate object key")
        result[key] = value
    return result


def _canonical_json_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _token: _fail(
                f"{label} contains a nonfinite JSON number"
            ),
        )
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42PreformalSenderLauncherError(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or _canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _content_id(domain: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\x00" + _canonical_json_bytes(payload)
    ).hexdigest()


def _verify_document_id(
    document: dict[str, Any], *, key: str, domain: str, label: str
) -> None:
    observed = document.get(key)
    if type(observed) is not str or _HEX64.fullmatch(observed) is None:
        _fail(f"{label} identity changed")
    payload = dict(document)
    payload.pop(key)
    if _content_id(domain, payload) != observed:
        _fail(f"{label} content identity changed")


def _git_blob_oid(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - exact Git SHA-1 object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


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


def _stable_directory_state(observed: os.stat_result) -> tuple[int, ...]:
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_uid,
        observed.st_gid,
        observed.st_nlink,
        observed.st_mtime_ns,
        observed.st_ctime_ns,
    )


@dataclass
class _DirectoryChain:
    descriptors: list[int]
    states: list[tuple[int, ...]]

    @property
    def descriptor(self) -> int:
        return self.descriptors[-1]

    def verify(self) -> None:
        for descriptor, expected in zip(
            self.descriptors, self.states, strict=True
        ):
            if _stable_directory_state(os.fstat(descriptor)) != expected:
                _fail("opened directory chain changed")

    def close(self) -> None:
        while self.descriptors:
            os.close(self.descriptors.pop())
        self.states.clear()


def _open_absolute_directory_chain(path: Path, *, label: str) -> _DirectoryChain:
    if (
        not path.is_absolute()
        or path == Path(path.anchor)
        or path.as_posix() != str(path)
        or any(part in {"", ".", ".."} for part in path.parts[1:])
    ):
        _fail(f"{label} path changed")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptors = [os.open("/", flags)]
    states = [_stable_directory_state(os.fstat(descriptors[0]))]
    try:
        for component in path.parts[1:]:
            before = os.stat(
                component,
                dir_fd=descriptors[-1],
                follow_symlinks=False,
            )
            if not stat.S_ISDIR(before.st_mode):
                _fail(f"{label} ancestor is not a directory")
            child = os.open(component, flags, dir_fd=descriptors[-1])
            opened = os.fstat(child)
            if _stable_directory_state(before) != _stable_directory_state(opened):
                os.close(child)
                _fail(f"{label} ancestor changed while opening")
            descriptors.append(child)
            states.append(_stable_directory_state(opened))
        chain = _DirectoryChain(descriptors=descriptors, states=states)
        chain.verify()
        return chain
    except BaseException:
        while descriptors:
            os.close(descriptors.pop())
        raise


def _read_stream(descriptor: int, maximum: int, *, retain: bool) -> tuple[bytes, str, int]:
    chunks: list[bytes] = []
    digest = hashlib.sha256()
    count = 0
    while True:
        remaining = maximum + 1 - count
        if remaining <= 0:
            _fail("bounded regular file exceeded its byte cap")
        chunk = os.read(descriptor, min(READ_CHUNK_BYTES, remaining))
        if not chunk:
            break
        digest.update(chunk)
        count += len(chunk)
        if retain:
            chunks.append(chunk)
        if count > maximum:
            _fail("bounded regular file exceeded its byte cap")
    return (b"".join(chunks) if retain else b"", digest.hexdigest(), count)


def _read_regular_at_v42r1(
    parent_fd: int,
    name: str,
    *,
    maximum: int,
    expected_mode: int,
    expected_uid: int,
    expected_gid: int,
    expected_nlink: int,
    label: str,
) -> bytes:
    if (
        type(name) is not str
        or not name
        or name in {".", ".."}
        or "/" in name
        or "\x00" in name
    ):
        _fail(f"{label} basename changed")
    descriptor = -1
    try:
        named_before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        descriptor = os.open(
            name,
            os.O_RDONLY
            | os.O_NONBLOCK
            | os.O_NOCTTY
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != expected_mode
            or before.st_uid != expected_uid
            or before.st_gid != expected_gid
            or before.st_nlink != expected_nlink
            or before.st_size <= 0
            or before.st_size > maximum
            or (named_before.st_dev, named_before.st_ino)
            != (before.st_dev, before.st_ino)
        ):
            _fail(f"{label} metadata changed")
        raw, digest, count = _read_stream(descriptor, maximum, retain=True)
        middle = os.fstat(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        _discarded, readback_digest, readback_count = _read_stream(
            descriptor, maximum, retain=False
        )
        after = os.fstat(descriptor)
        named_after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            count != before.st_size
            or readback_count != count
            or readback_digest != digest
            or hashlib.sha256(raw).hexdigest() != digest
            or _stable_file_state(before) != _stable_file_state(middle)
            or _stable_file_state(before) != _stable_file_state(after)
            or _stable_file_state(before) != _stable_file_state(named_after)
        ):
            _fail(f"{label} changed during stable readback")
        return raw
    except OSError as error:
        raise V42PreformalSenderLauncherError(
            f"{label} could not be read through the no-follow boundary"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_relative_tcb_file_v42r1(root_fd: int, relative: str) -> bytes:
    parsed = PurePosixPath(relative)
    if (
        parsed.is_absolute()
        or parsed.as_posix() != relative
        or len(parsed.parts) < 2
        or any(part in {"", ".", ".."} for part in parsed.parts)
    ):
        _fail("local effectful TCB relative path changed")
    current = os.dup(root_fd)
    try:
        for component in parsed.parts[:-1]:
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=current,
            )
            observed = os.fstat(child)
            named = os.stat(component, dir_fd=current, follow_symlinks=False)
            if (
                not stat.S_ISDIR(observed.st_mode)
                or _stable_directory_state(observed)
                != _stable_directory_state(named)
            ):
                os.close(child)
                _fail("local effectful TCB directory changed")
            os.close(current)
            current = child
        name = parsed.parts[-1]
        named = os.stat(name, dir_fd=current, follow_symlinks=False)
        mode = stat.S_IMODE(named.st_mode)
        if mode not in {0o444, 0o644}:
            _fail("local effectful TCB source mode changed")
        return _read_regular_at_v42r1(
            current,
            name,
            maximum=MAXIMUM_TCB_SOURCE_BYTES,
            expected_mode=mode,
            expected_uid=os.geteuid(),
            expected_gid=os.getegid(),
            expected_nlink=1,
            label="local effectful TCB " + relative,
        )
    finally:
        os.close(current)


def _read_control_capsule_v42r1(
    capsule_root: Path = FIXED_LOCAL_CAPSULE_ROOT,
) -> dict[str, bytes]:
    chain = _open_absolute_directory_chain(capsule_root, label="local capsule root")
    try:
        observed_root = os.fstat(chain.descriptor)
        if (
            stat.S_IMODE(observed_root.st_mode) != 0o700
            or observed_root.st_uid != os.geteuid()
            or observed_root.st_gid != os.getegid()
        ):
            _fail("local capsule root mode or ownership changed")
        if tuple(sorted(os.listdir(chain.descriptor))) != CONTROL_NAMES:
            _fail("local capsule five-control inventory changed")
        controls = {
            name: _read_regular_at_v42r1(
                chain.descriptor,
                name,
                maximum=MAXIMUM_CONTROL_BYTES[name],
                expected_mode=0o400,
                expected_uid=os.geteuid(),
                expected_gid=os.getegid(),
                expected_nlink=1,
                label="local capsule control " + name,
            )
            for name in CONTROL_NAMES
        }
        if tuple(sorted(os.listdir(chain.descriptor))) != CONTROL_NAMES:
            _fail("local capsule inventory changed across stable readback")
        chain.verify()
        return controls
    finally:
        chain.close()


def _preimport_manifests_v42r1(
    controls: dict[str, bytes],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if type(controls) is not dict or tuple(sorted(controls)) != CONTROL_NAMES:
        _fail("detached five-control inventory changed")
    source = _canonical_json_object(
        controls[SOURCE_MANIFEST_NAME], "execution source manifest"
    )
    local = _canonical_json_object(
        controls[LOCAL_MATERIALIZATION_ATTEMPT_NAME],
        "local materialization attempt",
    )
    manifest = _canonical_json_object(
        controls[TRANSPORT_MANIFEST_NAME], "transport manifest"
    )
    _verify_document_id(
        source,
        key="source_manifest_id",
        domain="acfqp:v42-remote-ordinal2:source-manifest",
        label="execution source manifest",
    )
    _verify_document_id(
        manifest,
        key="transport_manifest_id",
        domain="acfqp:v42-remote-ordinal2:transport-manifest",
        label="transport manifest",
    )
    _verify_document_id(
        local,
        key="local_materialization_attempt_id",
        domain="acfqp:v42-remote-ordinal2:local-materialization-attempt",
        label="local materialization attempt",
    )
    source_commit = source.get("source_commit")
    source_tree = source.get("source_tree")
    if (
        type(source_commit) is not str
        or _HEX40.fullmatch(source_commit) is None
        or type(source_tree) is not str
        or _HEX40.fullmatch(source_tree) is None
        or manifest.get("source_commit") != source_commit
        or manifest.get("source_tree") != source_tree
        or manifest.get("execution_source_manifest_id")
        != source["source_manifest_id"]
        or local.get("source_manifest_id") != source["source_manifest_id"]
        or local.get("transport_manifest_id")
        != manifest["transport_manifest_id"]
    ):
        _fail("five-control source, transport, or local lineage changed")
    if (
        manifest.get("source_archive_sha256")
        != hashlib.sha256(controls[SOURCE_CAPSULE_NAME]).hexdigest()
        or manifest.get("source_archive_byte_count")
        != len(controls[SOURCE_CAPSULE_NAME])
    ):
        _fail("source archive bytes differ from the transport manifest")
    pyz = manifest.get("remote_bootstrap_pyz_artifact")
    if (
        type(pyz) is not dict
        or pyz.get("pyz_sha256")
        != hashlib.sha256(controls[REMOTE_BOOTSTRAP_PYZ_NAME]).hexdigest()
        or pyz.get("pyz_byte_count") != len(controls[REMOTE_BOOTSTRAP_PYZ_NAME])
    ):
        _fail("remote bootstrap pyz bytes differ from the transport manifest")
    return source, manifest, local


def _transport_facts_by_path_v42r1(
    manifest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows = manifest.get("transport_facts")
    if type(rows) is not list or not rows:
        _fail("transport fact inventory changed type or emptiness")
    result: dict[str, dict[str, Any]] = {}
    previous = ""
    for row in rows:
        if type(row) is not dict or set(row) != {
            "relative_path",
            "git_mode",
            "git_object_type",
            "git_blob_oid",
            "byte_count",
            "sha256",
        }:
            _fail("transport fact schema changed")
        relative = row.get("relative_path")
        if (
            type(relative) is not str
            or relative <= previous
            or PurePosixPath(relative).is_absolute()
            or PurePosixPath(relative).as_posix() != relative
            or any(
                part in {"", ".", ".."}
                for part in PurePosixPath(relative).parts
            )
            or row.get("git_mode") != "100644"
            or row.get("git_object_type") != "blob"
            or type(row.get("git_blob_oid")) is not str
            or _HEX40.fullmatch(row["git_blob_oid"]) is None
            or type(row.get("byte_count")) is not int
            or row["byte_count"] < 0
            or type(row.get("sha256")) is not str
            or _HEX64.fullmatch(row["sha256"]) is None
        ):
            _fail("transport fact semantics or ordering changed")
        previous = relative
        result[relative] = dict(row)
    if set(LOCAL_EFFECTFUL_TCB_PATHS) - set(result):
        _fail("selected transport omitted a local effectful TCB source")
    return result


def _pin_fixed_git_v42r1() -> tuple[int, tuple[int, ...]]:
    descriptor = os.open(
        GIT_EXECUTABLE,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        observed = os.fstat(descriptor)
        raw, digest, count = _read_stream(
            descriptor, GIT_EXECUTABLE_BYTE_COUNT, retain=False
        )
        del raw
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != GIT_EXECUTABLE_MODE
            or observed.st_uid != GIT_EXECUTABLE_UID
            or observed.st_gid != GIT_EXECUTABLE_GID
            or observed.st_nlink != GIT_EXECUTABLE_NLINK
            or count != GIT_EXECUTABLE_BYTE_COUNT
            or digest != GIT_EXECUTABLE_SHA256
            or os.path.realpath(GIT_EXECUTABLE) != GIT_EXECUTABLE_REALPATH
            or _stable_file_state(os.fstat(descriptor))
            != _stable_file_state(observed)
        ):
            _fail("fixed Git executable changed")
        return descriptor, _stable_file_state(observed)
    except BaseException:
        os.close(descriptor)
        raise


@dataclass(frozen=True)
class _PinnedProcessObservationV42r1:
    exec_succeeded: bool
    returncode: int | None
    timed_out: bool
    stdout_raw: bytes
    stdout_total_byte_count: int
    stdout_overflow: bool
    stdout_eof: bool
    stderr_raw: bytes
    stderr_total_byte_count: int
    stderr_overflow: bool
    stderr_eof: bool


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


def _returncode_from_wait_status(status: int) -> int:
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    _fail("pinned child wait status changed")


def _blockable_signals() -> set[signal.Signals]:
    return {
        signum
        for signum in signal.valid_signals()
        if signum not in {signal.SIGKILL, signal.SIGSTOP}
    }


def _assert_direct_exec_platform_v42r1() -> None:
    if (
        os.name != "posix"
        or os.uname().sysname != "Linux"
        or os.uname().machine not in {"x86_64", "amd64"}
        or not hasattr(os, "pipe2")
        or not hasattr(fcntl, "F_DUPFD_CLOEXEC")
        or not hasattr(signal, "pthread_sigmask")
        or not hasattr(signal, "valid_signals")
    ):
        _fail("pinned direct-exec platform changed")
    tasks = sorted(name for name in os.listdir("/proc/self/task") if name.isdigit())
    if len(tasks) != 1:
        _fail("pinned direct exec requires an exact single-threaded process")
    if sys.gettrace() is not None or sys.getprofile() is not None:
        _fail("pinned direct exec forbids Python trace and profile hooks")
    ctypes.set_errno(0)
    close_result = _LIBC_SYSCALL(
        _SYS_CLOSE_RANGE_X86_64,
        ctypes.c_uint(_UINT_MAX),
        ctypes.c_uint(_UINT_MAX),
        ctypes.c_uint(0),
    )
    if close_result != 0:
        _fail("kernel lacks the required close_range syscall")
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
        _fail("kernel lacks the required execveat syscall")


def _encoded_exec_vectors_v42r1(
    argv: tuple[str, ...], environment: dict[str, str]
) -> tuple[tuple[bytes, ...], tuple[bytes, ...], Any, Any]:
    argv_raw = tuple(os.fsencode(value) for value in argv)
    environment_raw = tuple(
        os.fsencode(f"{key}={value}") for key, value in environment.items()
    )
    argv_vector = (ctypes.c_char_p * (len(argv_raw) + 1))(*argv_raw, None)
    environment_vector = (ctypes.c_char_p * (len(environment_raw) + 1))(
        *environment_raw, None
    )
    return argv_raw, environment_raw, argv_vector, environment_vector


def _read_exec_status_v42r1(
    descriptor: int, *, deadline: float
) -> tuple[bool, bool]:
    os.set_blocking(descriptor, False)
    observed = bytearray()
    selector = selectors.DefaultSelector()
    try:
        selector.register(descriptor, selectors.EVENT_READ)
        while True:
            try:
                chunk = os.read(descriptor, 16)
            except (BlockingIOError, InterruptedError):
                chunk = None
            if chunk == b"":
                return not observed, False
            if chunk:
                observed.extend(chunk)
                if len(observed) > 1:
                    return False, False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False, True
            selector.select(min(remaining, 0.25))
    finally:
        selector.close()


def _pump_pinned_child_v42r1(
    *,
    pid: int,
    stdout_fd: int,
    stderr_fd: int,
    stdout_cap: int,
    stderr_cap: int,
    deadline: float,
    exec_succeeded: bool,
    already_timed_out: bool,
) -> _PinnedProcessObservationV42r1:
    for descriptor in (stdout_fd, stderr_fd):
        os.set_blocking(descriptor, False)
    selector = selectors.DefaultSelector()
    stdout_raw = bytearray()
    stderr_raw = bytearray()
    stdout_total = 0
    stderr_total = 0
    stdout_eof = False
    stderr_eof = False
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
                    post_exit_deadline = now + GIT_POST_EXIT_DRAIN_SECONDS
            if status is None and now >= deadline and not killed:
                timed_out = True
                killed = True
                _kill_noexcept(pid)
                post_exit_deadline = now + GIT_POST_EXIT_DRAIN_SECONDS
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
            for key, _mask in selector.select(timeout):
                descriptor = key.fd
                try:
                    chunk = os.read(descriptor, READ_CHUNK_BYTES)
                except (BlockingIOError, InterruptedError):
                    continue
                if not chunk:
                    close_registered(descriptor)
                    if key.data == "stdout":
                        stdout_eof = True
                        stdout_fd = -1
                    else:
                        stderr_eof = True
                        stderr_fd = -1
                    continue
                if key.data == "stdout":
                    stdout_total += len(chunk)
                    remaining = stdout_cap + 1 - len(stdout_raw)
                    if remaining > 0:
                        stdout_raw.extend(chunk[:remaining])
                else:
                    stderr_total += len(chunk)
                    remaining = stderr_cap + 1 - len(stderr_raw)
                    if remaining > 0:
                        stderr_raw.extend(chunk[:remaining])
        if status is None:
            _kill_noexcept(pid)
            while True:
                try:
                    _observed_pid, status = os.waitpid(pid, 0)
                    break
                except InterruptedError:
                    continue
        return _PinnedProcessObservationV42r1(
            exec_succeeded=exec_succeeded,
            returncode=_returncode_from_wait_status(status),
            timed_out=timed_out,
            stdout_raw=bytes(stdout_raw),
            stdout_total_byte_count=stdout_total,
            stdout_overflow=stdout_total > stdout_cap,
            stdout_eof=stdout_eof,
            stderr_raw=bytes(stderr_raw),
            stderr_total_byte_count=stderr_total,
            stderr_overflow=stderr_total > stderr_cap,
            stderr_eof=stderr_eof,
        )
    finally:
        selector.close()
        _close_noexcept(stdout_fd)
        _close_noexcept(stderr_fd)
        if status is None:
            _terminate_and_reap_noexcept(pid)


def _run_pinned_executable_v42r1(
    *,
    executable_fd: int,
    argv: tuple[str, ...],
    environment: dict[str, str],
    stdout_cap: int,
    stderr_cap: int,
    timeout_seconds: float,
) -> _PinnedProcessObservationV42r1:
    if (
        type(executable_fd) is not int
        or executable_fd < 3
        or type(argv) is not tuple
        or not argv
        or any(type(value) is not str or "\x00" in value for value in argv)
        or type(environment) is not dict
        or any(
            type(key) is not str
            or type(value) is not str
            or "\x00" in key
            or "\x00" in value
            for key, value in environment.items()
        )
        or type(stdout_cap) is not int
        or not 0 < stdout_cap <= 4 * 1024**2
        or type(stderr_cap) is not int
        or not 0 < stderr_cap <= 1024 * 1024
        or type(timeout_seconds) is not float
        or not 0.0 < timeout_seconds <= 60.0
    ):
        _fail("pinned executable resource contract changed")
    _assert_direct_exec_platform_v42r1()
    (
        argv_raw,
        environment_raw,
        argv_vector,
        environment_vector,
    ) = _encoded_exec_vectors_v42r1(argv, environment)
    if not argv_raw or len(environment_raw) != len(environment):
        _fail("pinned executable vectors changed")
    descriptors: list[int] = []
    pid: int | None = None
    previous_mask: set[signal.Signals] | None = None
    started = time.monotonic()
    deadline = started + timeout_seconds
    try:
        stdin_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        descriptors.append(stdin_fd)
        if not stat.S_ISCHR(os.fstat(stdin_fd).st_mode):
            _fail("pinned executable stdin is not the exact null-device kind")
        stdout_read, stdout_write = os.pipe2(os.O_CLOEXEC)
        descriptors.extend((stdout_read, stdout_write))
        stderr_read, stderr_write = os.pipe2(os.O_CLOEXEC)
        descriptors.extend((stderr_read, stderr_write))
        exec_status_read, exec_status_write = os.pipe2(os.O_CLOEXEC)
        descriptors.extend((exec_status_read, exec_status_write))
        previous_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK, _blockable_signals()
        )
        pid = os.fork()
        if pid == 0:
            status_descriptor = exec_status_write
            try:
                sys.settrace(None)
                sys.setprofile(None)
                staged_executable = fcntl.fcntl(
                    executable_fd, fcntl.F_DUPFD_CLOEXEC, 5
                )
                staged_status = fcntl.fcntl(
                    exec_status_write, fcntl.F_DUPFD_CLOEXEC, 5
                )
                os.dup2(stdin_fd, 0, inheritable=True)
                os.dup2(stdout_write, 1, inheritable=True)
                os.dup2(stderr_write, 2, inheritable=True)
                os.dup2(
                    staged_executable, _CHILD_EXECUTABLE_FD, inheritable=False
                )
                os.dup2(
                    staged_status, _CHILD_EXEC_STATUS_FD, inheritable=False
                )
                status_descriptor = _CHILD_EXEC_STATUS_FD
                os.chdir("/")
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
        for descriptor in (stdin_fd, stdout_write, stderr_write, exec_status_write):
            _close_noexcept(descriptor)
            descriptors.remove(descriptor)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        previous_mask = None
        exec_deadline = min(
            deadline, time.monotonic() + GIT_EXEC_STATUS_TIMEOUT_SECONDS
        )
        exec_succeeded, exec_timed_out = _read_exec_status_v42r1(
            exec_status_read, deadline=exec_deadline
        )
        _close_noexcept(exec_status_read)
        descriptors.remove(exec_status_read)
        if exec_timed_out:
            _kill_noexcept(pid)
        descriptors.remove(stdout_read)
        descriptors.remove(stderr_read)
        observation = _pump_pinned_child_v42r1(
            pid=pid,
            stdout_fd=stdout_read,
            stderr_fd=stderr_read,
            stdout_cap=stdout_cap,
            stderr_cap=stderr_cap,
            deadline=deadline,
            exec_succeeded=exec_succeeded,
            already_timed_out=exec_timed_out,
        )
        pid = None
        return observation
    except BaseException:
        if pid is not None and pid > 0:
            _terminate_and_reap_noexcept(pid)
        raise
    finally:
        if previous_mask is not None:
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            except BaseException:
                pass
        for descriptor in descriptors:
            _close_noexcept(descriptor)


def _run_fixed_git_v42r1(*arguments: str) -> bytes:
    descriptor, state = _pin_fixed_git_v42r1()
    try:
        observation = _run_pinned_executable_v42r1(
            executable_fd=descriptor,
            argv=(GIT_EXECUTABLE, "--no-replace-objects", *arguments),
            environment=dict(_GIT_ENVIRONMENT),
            stdout_cap=GIT_STDOUT_BYTE_CAP,
            stderr_cap=GIT_STDERR_BYTE_CAP,
            timeout_seconds=float(GIT_QUERY_TIMEOUT_SECONDS),
        )
        if (
            not observation.exec_succeeded
            or observation.returncode != 0
            or observation.timed_out
            or observation.stdout_overflow
            or not observation.stdout_eof
            or observation.stdout_total_byte_count
            != len(observation.stdout_raw)
            or observation.stderr_overflow
            or not observation.stderr_eof
            or observation.stderr_total_byte_count != 0
            or observation.stderr_raw != b""
        ):
            _fail("fixed Git descriptor query failed its exact output contract")
        named = os.stat(GIT_EXECUTABLE, follow_symlinks=False)
        if (
            _stable_file_state(os.fstat(descriptor)) != state
            or _stable_file_state(named) != state
        ):
            _fail("fixed Git executable changed across read-only query")
        return observation.stdout_raw
    finally:
        os.close(descriptor)


def _selected_git_inventory_v42r1(
    *, source_commit: str, source_tree: str
) -> dict[str, tuple[str, str, str]]:
    if _run_fixed_git_v42r1("--version") != GIT_VERSION_STDOUT:
        _fail("fixed Git version output changed")
    anchors = _run_fixed_git_v42r1(
        "-C",
        str(ROOT),
        "rev-parse",
        "--verify",
        "HEAD^{commit}",
        "HEAD^{tree}",
    ).splitlines()
    if anchors != [source_commit.encode("ascii"), source_tree.encode("ascii")]:
        _fail("selected committed HEAD or tree differs from the capsule")
    raw = _run_fixed_git_v42r1(
        "-C",
        str(ROOT),
        "ls-tree",
        "-rz",
        "--full-tree",
        source_commit,
        "--",
        *LOCAL_EFFECTFUL_TCB_PATHS,
    )
    records = raw.split(b"\x00")
    if not records or records[-1] != b"":
        _fail("selected Git TCB inventory framing changed")
    result: dict[str, tuple[str, str, str]] = {}
    for record in records[:-1]:
        try:
            header, relative_raw = record.split(b"\t", 1)
            mode_raw, kind_raw, oid_raw = header.split(b" ")
            relative = relative_raw.decode("utf-8", errors="strict")
            values = (
                mode_raw.decode("ascii"),
                kind_raw.decode("ascii"),
                oid_raw.decode("ascii"),
            )
        except (UnicodeError, ValueError) as error:
            raise V42PreformalSenderLauncherError(
                "selected Git TCB inventory is malformed"
            ) from error
        if relative in result:
            _fail("selected Git TCB inventory contains a duplicate")
        result[relative] = values
    if set(result) != set(LOCAL_EFFECTFUL_TCB_PATHS):
        _fail("selected Git commit omitted an exact local TCB source")
    return result


def _read_and_verify_effectful_tcb_v42r1(
    *, manifest: dict[str, Any], source_commit: str, source_tree: str
) -> dict[str, bytes]:
    facts = _transport_facts_by_path_v42r1(manifest)
    selected = _selected_git_inventory_v42r1(
        source_commit=source_commit, source_tree=source_tree
    )
    root_chain = _open_absolute_directory_chain(ROOT, label="repository root")
    try:
        result: dict[str, bytes] = {}
        for relative in LOCAL_EFFECTFUL_TCB_PATHS:
            fact = facts[relative]
            if selected[relative] != (
                fact["git_mode"],
                fact["git_object_type"],
                fact["git_blob_oid"],
            ):
                _fail("selected Git TCB fact differs from the transport manifest")
            raw = _read_relative_tcb_file_v42r1(root_chain.descriptor, relative)
            if (
                len(raw) != fact["byte_count"]
                or hashlib.sha256(raw).hexdigest() != fact["sha256"]
                or _git_blob_oid(raw) != fact["git_blob_oid"]
            ):
                _fail("live local TCB bytes differ from selected committed HEAD")
            result[relative] = raw
        root_chain.verify()
        return result
    finally:
        root_chain.close()


@dataclass(frozen=True)
class _LoadedEffectfulModules:
    transport: ModuleType
    journal: ModuleType
    sender: ModuleType
    finder: "_VerifiedTcbMetaFinderV42r1 | None" = None
    tcb_raw_by_path: object | None = None


class _VerifiedTcbBytesLoaderV42r1(importlib.abc.Loader):
    """Compile one selected immutable source byte string without path reads."""

    def __init__(
        self,
        *,
        finder: "_VerifiedTcbMetaFinderV42r1",
        fullname: str,
        relative_path: str,
        raw: bytes,
        is_package: bool,
    ) -> None:
        self.finder = finder
        self.fullname = fullname
        self.relative_path = relative_path
        self.absolute_path = str(finder.root / relative_path)
        self.raw = raw
        self.is_package = is_package
        self.exec_count = 0

    def create_module(self, _spec: object) -> None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        if (
            self.exec_count != 0
            or module.__name__ != self.fullname
            or module.__spec__ is None
            or module.__spec__.loader is not self
            or module.__spec__.origin != self.absolute_path
            or module.__spec__.cached is not None
        ):
            _fail("verified TCB byte loader entry changed")
        self.exec_count = 1
        module.__file__ = self.absolute_path
        module.__cached__ = None
        module.__loader__ = self
        module.__package__ = (
            self.fullname if self.is_package else self.fullname.rpartition(".")[0]
        )
        code = compile(
            self.raw,
            self.absolute_path,
            "exec",
            flags=0,
            dont_inherit=True,
            optimize=0,
        )
        exec(code, module.__dict__, module.__dict__)


class _VerifiedTcbMetaFinderV42r1(importlib.abc.MetaPathFinder):
    """Admit only registered acfqp/scripts modules from verified bytes."""

    def __init__(
        self,
        *,
        root: Path,
        module_paths: dict[str, str],
        raw_by_path: object,
    ) -> None:
        if type(module_paths) is not dict or not module_paths:
            _fail("verified TCB module map changed")
        supplied = dict(raw_by_path)  # type: ignore[arg-type]
        if set(module_paths.values()) - set(supplied):
            _fail("verified TCB bytes omitted an imported module")
        self.root = root
        self.module_paths = MappingProxyType(dict(module_paths))
        self.raw_by_path = MappingProxyType(
            {relative: supplied[relative] for relative in module_paths.values()}
        )
        self.protected_roots = frozenset(
            name.partition(".")[0] for name in module_paths
        )
        loaders: dict[str, _VerifiedTcbBytesLoaderV42r1] = {}
        for fullname, relative in module_paths.items():
            raw = self.raw_by_path[relative]
            if type(raw) is not bytes:
                _fail("verified TCB source changed immutable byte type")
            loaders[fullname] = _VerifiedTcbBytesLoaderV42r1(
                finder=self,
                fullname=fullname,
                relative_path=relative,
                raw=raw,
                is_package=fullname in self.protected_roots,
            )
        self.loaders = MappingProxyType(loaders)

    def find_spec(
        self,
        fullname: str,
        _path: object = None,
        _target: object = None,
    ) -> object:
        root_name = fullname.partition(".")[0]
        if root_name not in self.protected_roots:
            return None
        loader = self.loaders.get(fullname)
        if loader is None:
            raise ImportError("unregistered local TCB module rejected: " + fullname)
        spec = importlib.util.spec_from_loader(
            fullname,
            loader,
            origin=loader.absolute_path,
            is_package=loader.is_package,
        )
        if spec is None:
            _fail("verified TCB module spec construction failed")
        spec.cached = None
        if loader.is_package:
            spec.submodule_search_locations = []
        return spec


def _load_effectful_modules_v42r1(
    initial_tcb: dict[str, bytes],
) -> _LoadedEffectfulModules:
    if str(ROOT) in sys.path or str(SOURCE_ROOT) in sys.path:
        _fail("repository import roots were present before TCB verification")
    if any(
        name == root or name.startswith(root + ".")
        for name in sys.modules
        for root in ("acfqp", "scripts")
    ):
        _fail("a protected repository module was loaded before byte binding")
    snapshot = MappingProxyType(dict(initial_tcb))
    finder = _VerifiedTcbMetaFinderV42r1(
        root=ROOT,
        module_paths=dict(EXPECTED_IMPORTED_REPOSITORY_MODULES),
        raw_by_path=snapshot,
    )
    sys.meta_path.insert(0, finder)
    transport = importlib.import_module(
        "acfqp.construction_k7_standard_2048_materialization_transport_v42r1"
    )
    journal = importlib.import_module("scripts.publish_v42_preformal_upload_journal")
    sender = importlib.import_module("scripts.run_v42_preformal_upload_sender")
    return _LoadedEffectfulModules(
        transport=transport,
        journal=journal,
        sender=sender,
        finder=finder,
        tcb_raw_by_path=snapshot,
    )


def _verify_loaded_module_inventory_v42r1(
    *, modules: _LoadedEffectfulModules, direct_entry: bool
) -> None:
    finder = modules.finder
    if (
        type(finder) is not _VerifiedTcbMetaFinderV42r1
        or finder.root != ROOT
        or dict(finder.module_paths) != EXPECTED_IMPORTED_REPOSITORY_MODULES
        or set(finder.raw_by_path) != set(EXPECTED_IMPORTED_REPOSITORY_MODULES.values())
        or set(finder.loaders) != set(EXPECTED_IMPORTED_REPOSITORY_MODULES)
        or finder.protected_roots != frozenset({"acfqp", "scripts"})
        or not isinstance(finder.module_paths, MappingProxyType)
        or not isinstance(finder.raw_by_path, MappingProxyType)
        or not isinstance(finder.loaders, MappingProxyType)
        or not sys.meta_path
        or sys.meta_path[0] is not finder
        or sum(
            type(candidate) is _VerifiedTcbMetaFinderV42r1
            for candidate in sys.meta_path
        )
        != 1
        or not isinstance(modules.tcb_raw_by_path, MappingProxyType)
        or str(ROOT) in sys.path
        or str(SOURCE_ROOT) in sys.path
    ):
        _fail("verified TCB meta finder identity changed")
    observed: dict[str, str] = {}
    for name, module in tuple(sys.modules.items()):
        file_name = getattr(module, "__file__", None)
        if type(file_name) is not str:
            continue
        try:
            relative = Path(file_name).relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if file_name.endswith((".pyc", ".pyo")):
            _fail("effectful launcher loaded repository bytecode")
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        if direct_entry and name == "__main__" and relative == LAUNCHER_SOURCE_RELATIVE:
            if (
                origin is not None
                or file_name != str(SCRIPT_PATH)
                or getattr(module, "__cached__", None) is not None
            ):
                _fail("direct launcher module origin changed")
            continue
        if origin != file_name:
            _fail("loaded repository module origin and __file__ differ")
        loader = getattr(module, "__loader__", None)
        if (
            type(loader) is not _VerifiedTcbBytesLoaderV42r1
            or finder.loaders.get(name) is not loader
            or loader.finder is not finder
            or loader.fullname != name
            or loader.relative_path != relative
            or loader.absolute_path != file_name
            or loader.exec_count != 1
            or loader.raw is not finder.raw_by_path[relative]
            or loader.raw is not modules.tcb_raw_by_path[relative]  # type: ignore[index]
            or module.__spec__ is None
            or module.__spec__.loader is not loader
            or module.__spec__.origin != file_name
            or module.__spec__.cached is not None
            or getattr(module, "__cached__", None) is not None
            or module.__package__
            != (
                name
                if name in finder.protected_roots
                else name.rpartition(".")[0]
            )
        ):
            _fail("loaded repository module did not use its exact verified bytes")
        if name in finder.protected_roots:
            if (
                getattr(module, "__path__", None) != []
                or module.__spec__.submodule_search_locations != []
            ):
                _fail("verified TCB package search locations changed")
        elif hasattr(module, "__path__"):
            _fail("verified TCB nonpackage acquired package search locations")
        observed[name] = relative
    if observed != EXPECTED_IMPORTED_REPOSITORY_MODULES:
        _fail("loaded effectful repository module inventory changed")


def _verify_effectful_surfaces_v42r1(modules: _LoadedEffectfulModules) -> None:
    transport = modules.transport
    sender = modules.sender
    journal = modules.journal
    if (
        tuple(transport.CONTROL_NAMES) != CONTROL_NAMES
        or dict(transport.MAXIMUM_CONTROL_BYTES) != MAXIMUM_CONTROL_BYTES
        or transport.PREFORMAL_LOADER_SOURCE_RELATIVE != LOADER_SOURCE_RELATIVE
        or transport.PREFORMAL_RECEIVER_SOURCE_RELATIVE
        != RECEIVER_SOURCE_RELATIVE
        or not callable(sender.execute_preformal_upload_v42r1)
        or sender.execute_preformal_upload_v42r1.__module__
        != "scripts.run_v42_preformal_upload_sender"
        or not callable(journal.inspect_preformal_upload_journal_v42r1)
        or journal.inspect_preformal_upload_journal_v42r1.__module__
        != "scripts.publish_v42_preformal_upload_journal"
    ):
        _fail("effectful sender, journal, or transport surface changed")


def _path_node_kind(path: Path) -> str:
    try:
        observed = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        return "ABSENT"
    if stat.S_ISDIR(observed.st_mode):
        return "DIRECTORY"
    return "OTHER"


def _inspect_existing_journal_v42r1(
    *,
    modules: _LoadedEffectfulModules,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    controls: dict[str, bytes],
    loader_raw: bytes,
    receiver_raw: bytes,
) -> str:
    chain_kind = _path_node_kind(Path(plan["local_chain_root"]))
    slot_kind = _path_node_kind(Path(plan["local_ordinal_slot"]))
    if chain_kind == "ABSENT" and slot_kind == "ABSENT":
        return "ABSENT"
    if chain_kind == "DIRECTORY" and slot_kind == "ABSENT":
        return "PRE_NETWORK_NO_SLOT"
    if chain_kind != "DIRECTORY" or slot_kind != "DIRECTORY":
        _fail("pre-formal journal root or ordinal slot changed node type")
    inspection = modules.journal.inspect_preformal_upload_journal_v42r1(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        predecessor_chain=[],
    )
    if inspection.state not in {
        "PRE_NETWORK_PREFIX",
        "PRE_NETWORK_BASE",
        "POSTNETWORK_UNRESOLVED",
        "COMPLETE_RECEIPT_PENDING_OUTCOME",
        "TERMINAL",
    }:
        _fail("journal inspection returned an unknown state")
    return inspection.state


def _sender_result_document_v42r1(
    *,
    modules: _LoadedEffectfulModules,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    upload_token: str,
    preexisting_journal_state: str,
    result: object,
) -> dict[str, Any]:
    if type(result) is not modules.sender.V42PreformalSenderResult:
        _fail("sender returned a noncanonical result type")
    recovery_diagnostics = {
        "POSTNETWORK_UNRESOLVED": "RECOVERED_POSTNETWORK_AS_AMBIGUOUS",
        "COMPLETE_RECEIPT_PENDING_OUTCOME": "RECOVERED_COMPLETE_RECEIPT",
        "TERMINAL": "RECOVERED_TERMINAL_JOURNAL",
    }
    expected_recovery = recovery_diagnostics.get(preexisting_journal_state)
    if expected_recovery is not None and result.diagnostic_code != expected_recovery:
        _fail("same-token post-effect reentry did not remain recovery-only")
    payload = {
        "schema": "acfqp.v42_preformal_upload_sender_launcher_result.v42r1",
        "source_commit": plan["source_commit"],
        "source_tree": plan["source_tree"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "local_materialization_attempt_id": plan[
            "local_materialization_attempt_id"
        ],
        "preformal_upload_plan_id": plan["preformal_upload_plan_id"],
        "preformal_upload_attempt_id": attempt["preformal_upload_attempt_id"],
        "preformal_upload_ordinal": plan["preformal_upload_ordinal"],
        "upload_token": upload_token,
        "predecessor_chain_length": 0,
        "preexisting_journal_state": preexisting_journal_state,
        "same_token_posteffect_reentry_is_recovery_only": True,
        "network_start": result.network_start,
        "receipt": result.receipt,
        "outcome": result.outcome,
        "diagnostic_code": result.diagnostic_code,
        "child_returncode": result.child_returncode,
        "stdout_byte_count": result.stdout_byte_count,
        "stdout_sha256": result.stdout_sha256,
        "stderr_byte_count": result.stderr_byte_count,
        "stderr_sha256": result.stderr_sha256,
    }
    return {
        **payload,
        "launcher_result_id": _content_id(
            "acfqp:v42-remote-ordinal2:preformal-sender-launcher-result",
            payload,
        ),
    }


def _execute_once_v42r1(
    *,
    modules: _LoadedEffectfulModules,
    controls: dict[str, bytes],
    loader_raw: bytes,
    receiver_raw: bytes,
    upload_token: str,
    preexisting_journal_state: str,
) -> dict[str, Any]:
    chain: list[dict[str, dict[str, Any]]] = []
    plan = modules.transport.build_preformal_upload_plan_v42r1(
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        upload_token=upload_token,
        predecessor_chain=chain,
    )
    attempt = modules.transport.build_preformal_upload_attempt_v42r1(
        plan=plan,
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        predecessor_chain=chain,
    )
    if (
        plan["preformal_upload_ordinal"] != 1
        or plan["previous_preformal_upload_outcome"] is not None
        or plan["previous_preformal_upload_outcome_id"] is not None
        or plan["upload_token"] != upload_token
        or plan["upload_token_history"] != [upload_token]
    ):
        _fail("first pre-formal upload plan acquired a predecessor")
    result = modules.sender.execute_preformal_upload_v42r1(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        predecessor_chain=chain,
    )
    return _sender_result_document_v42r1(
        modules=modules,
        plan=plan,
        attempt=attempt,
        upload_token=upload_token,
        preexisting_journal_state=preexisting_journal_state,
        result=result,
    )


def _verify_exact_cli_entry_v42r1() -> str:
    if (
        Path(__file__) != SCRIPT_PATH
        or not Path(__file__).is_absolute()
        or Path(__file__).resolve(strict=True) != SCRIPT_PATH
        or sys.executable != LOCAL_PYTHON
        or os.path.realpath(sys.executable) != LOCAL_PYTHON_REALPATH
        or tuple(sys.version_info[:3]) != LOCAL_PYTHON_VERSION
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
        or len(sys.argv) != 3
        or sys.argv[0] != str(SCRIPT_PATH)
        or sys.argv[1] != "--upload-token"
    ):
        _fail("launcher requires its exact isolated Python entry")
    token = sys.argv[2]
    expected = [
        LOCAL_PYTHON,
        "-I",
        "-S",
        "-B",
        str(SCRIPT_PATH),
        "--upload-token",
        token,
    ]
    if list(sys.orig_argv) != expected:
        _fail("launcher original Python argv changed")
    if _HEX64.fullmatch(token) is None:
        _fail("upload token is not fresh lowercase hex64 syntax")
    return token


def _write_all_stdout(raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(1, view)
        if written <= 0:
            _fail("canonical launcher result short write")
        view = view[written:]


def main() -> int:
    upload_token = _verify_exact_cli_entry_v42r1()
    controls = _read_control_capsule_v42r1()
    source, manifest, _local = _preimport_manifests_v42r1(controls)
    initial_tcb = _read_and_verify_effectful_tcb_v42r1(
        manifest=manifest,
        source_commit=source["source_commit"],
        source_tree=source["source_tree"],
    )
    modules = _load_effectful_modules_v42r1(initial_tcb)
    _verify_effectful_surfaces_v42r1(modules)
    _verify_loaded_module_inventory_v42r1(modules=modules, direct_entry=True)

    loader_raw = initial_tcb[LOADER_SOURCE_RELATIVE]
    receiver_raw = initial_tcb[RECEIVER_SOURCE_RELATIVE]
    chain: list[dict[str, dict[str, Any]]] = []
    plan = modules.transport.build_preformal_upload_plan_v42r1(
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        upload_token=upload_token,
        predecessor_chain=chain,
    )
    attempt = modules.transport.build_preformal_upload_attempt_v42r1(
        plan=plan,
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        predecessor_chain=chain,
    )
    preexisting_state = _inspect_existing_journal_v42r1(
        modules=modules,
        plan=plan,
        attempt=attempt,
        controls=controls,
        loader_raw=loader_raw,
        receiver_raw=receiver_raw,
    )

    # Last pre-effect gate: the fixed capsule, selected HEAD/tree, every local
    # effectful source, and the actual loaded module inventory must still be the
    # exact values observed above.  No sender function has been called yet.
    if _read_control_capsule_v42r1() != controls:
        _fail("local capsule changed before the sender effect boundary")
    final_tcb = _read_and_verify_effectful_tcb_v42r1(
        manifest=manifest,
        source_commit=source["source_commit"],
        source_tree=source["source_tree"],
    )
    if final_tcb != initial_tcb:
        _fail("local effectful TCB changed before the sender effect boundary")
    _verify_loaded_module_inventory_v42r1(modules=modules, direct_entry=True)
    _verify_effectful_surfaces_v42r1(modules)

    # There is exactly one call site for the effectful sender.  Rebuild inside
    # the helper from the same detached bytes and literal empty predecessor
    # chain so mutable plan objects from the journal inspection cannot cross
    # the effect boundary.
    document = _execute_once_v42r1(
        modules=modules,
        controls=controls,
        loader_raw=loader_raw,
        receiver_raw=receiver_raw,
        upload_token=upload_token,
        preexisting_journal_state=preexisting_state,
    )
    raw = _canonical_json_bytes(document)
    if _canonical_json_object(raw, "launcher result") != document:
        _fail("launcher result canonical replay changed")
    _write_all_stdout(raw)
    return 0


if __name__ == "__main__":
    try:
        _status = main()
    except BaseException:
        os.write(2, b"acfqp v42 preformal sender launcher rejected; inspect durable journal\n")
        os._exit(72)
    else:
        os._exit(_status)
