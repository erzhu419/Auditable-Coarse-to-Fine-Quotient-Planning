"""Stdlib-only durable service for V42 materialization activation.

The verified systemd bootstrap loader normalizes the environment, proves that
0/1/2 are the exact ``/dev/null`` inode, verifies this source from the fixed
ledger, and only then compiles it.  This service writes the service receipt,
performs the second resource gate, publishes READY, atomically renames the
selected exact-five scratch root, writes the transport terminal, and finally
executes the unchanged trusted bootstrap outer argv.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid
from typing import Callable


SCHEMA_VERSION = "42.1.0"
FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2"
GLOBAL_EXECUTION_ORDINAL = 2
REMOTE_HOSTNAME = "erzhu419-Super-Server"
REMOTE_USER = "erzhu419"
REMOTE_UID = 1000
REMOTE_GID = 1000
CONTROL_NAMES = (
    "EXECUTION_SOURCE_MANIFEST.json",
    "LOCAL_MATERIALIZATION_ATTEMPT.json",
    "REMOTE_BOOTSTRAP.pyz",
    "SOURCE_CAPSULE.tar",
    "TRANSPORT_MANIFEST.json",
)
REMOTE_ATTEMPT_NAME = "REMOTE_MATERIALIZATION_ACTIVATION_ATTEMPT.json"
SERVICE_SOURCE_NAME = "MATERIALIZATION_ACTIVATION_SERVICE.py"
SERVICE_RECEIPT_NAME = "REMOTE_ACTIVATION_SERVICE_RECEIPT.json"
READY_NAME = "REMOTE_ACTIVATION_PUBLISH_READY.json"
TERMINAL_NAME = "REMOTE_MATERIALIZATION_TRANSPORT_TERMINAL.json"
FAILURE_NAME = "REMOTE_MATERIALIZATION_ACTIVATION_FAILURE.json"
REMOTE_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_materialization_activation_attempt.v42r1"
)
SERVICE_RECEIPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_activation_service_receipt.v42r1"
)
READY_SCHEMA = "acfqp.v42_remote_ordinal2_activation_publish_ready.v42r1"
TERMINAL_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_transport_terminal.v42r1"
)
FAILURE_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_activation_failure.v42r1"
)
MINIMUM_MEMORY_TOTAL_BYTES = 128 * 1024**3
MINIMUM_MEMORY_AVAILABLE_BYTES = 96 * 1024**3
MINIMUM_SWAP_FREE_BYTES = 8 * 1024**3 - 4096
MINIMUM_FILESYSTEM_AVAILABLE_BYTES = 16 * 1024**3
SERVICE_ENVIRONMENT = {"LC_ALL": "C.UTF-8"}
SYSTEMD_UNIT_PREFIX = "acfqp-v42-o2-activation-"
SYSTEMCTL = "/usr/bin/systemctl"
SYSTEMD_CLIENT_ENVIRONMENT = {
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "LC_ALL": "C.UTF-8",
    "XDG_RUNTIME_DIR": "/run/user/1000",
}
_DOMAIN = "acfqp:v42-remote-ordinal2:"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_HEX32 = re.compile(r"[0-9a-f]{32}")
_SYS_RENAMEAT2_X86_64 = 316
_RENAME_NOREPLACE = 1


class _ActivationServiceFailure(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise _ActivationServiceFailure(message)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate JSON object key")
        result[key] = value
    return result


def _reject_number(token: str) -> None:
    _fail("non-integer JSON number is forbidden: " + token)


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as error:
        raise _ActivationServiceFailure("value is not canonical JSON") from error


def _canonical_document(raw: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except _ActivationServiceFailure:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise _ActivationServiceFailure(label + " is not strict JSON") from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(label + " is not canonical JSON")
    return value


def _content_id(domain: str, payload: dict[str, object]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + _canonical_bytes(payload)
    ).hexdigest()


def _verify_id(
    document: dict[str, object], *, schema: str, identity: str, domain: str
) -> None:
    observed = document.get(identity)
    if (
        document.get("schema") != schema
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != FORMAL_IDENTITY
        or document.get("global_execution_ordinal") != GLOBAL_EXECUTION_ORDINAL
        or type(observed) is not str
        or _HEX64.fullmatch(observed) is None
    ):
        _fail(identity + " authority header changed")
    payload = dict(document)
    del payload[identity]
    if observed != _content_id(domain, payload):
        _fail(identity + " content identity changed")


def _base(schema: str) -> dict[str, object]:
    return {
        "schema": schema,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
    }


def _stable_state(observed: os.stat_result) -> tuple[int, ...]:
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


def _live_descriptors() -> tuple[int, ...]:
    scanner = os.open(
        "/proc/self/fd",
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        names = {int(name) for name in os.listdir(scanner)}
        allowed = {0, 1, 2, scanner, scanner + 1}
        if names != allowed:
            _fail("service inherited descriptor inventory changed")
        try:
            os.fstat(scanner + 1)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise
        else:
            _fail("service descriptor iterator remained live")
    finally:
        os.close(scanner)
    return (0, 1, 2)


def _require_exact_devnull_stdio() -> None:
    if _live_descriptors() != (0, 1, 2):
        _fail("service descriptor allowlist changed")
    null_stat = os.stat("/dev/null", follow_symlinks=False)
    if not stat.S_ISCHR(null_stat.st_mode):
        _fail("/dev/null changed type")
    for descriptor in (0, 1, 2):
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISCHR(observed.st_mode)
            or (observed.st_dev, observed.st_ino, observed.st_rdev)
            != (null_stat.st_dev, null_stat.st_ino, null_stat.st_rdev)
        ):
            _fail("service stdio is not exact /dev/null")


def _process_unified_cgroup(process_id: int) -> str:
    if type(process_id) is not int or process_id <= 1:
        _fail("service cgroup process id changed")
    descriptor = os.open(
        f"/proc/{process_id}/cgroup",
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(4097 - total, 4096))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > 4096:
                _fail("service cgroup record exceeded cap")
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    if (
        not raw.startswith(b"0::/")
        or raw.count(b"\n") != 1
        or not raw.endswith(b"\n")
    ):
        _fail("service cgroup record changed")
    value = raw[3:-1].decode("ascii", errors="strict")
    if not value.startswith("/") or ".." in value.split("/"):
        _fail("service cgroup path changed")
    return value


def _current_unified_cgroup() -> str:
    return _process_unified_cgroup(os.getpid())


def _require_current_unified_cgroup(expected: str) -> None:
    if type(expected) is not str or _current_unified_cgroup() != expected:
        _fail("clean service cgroup changed across normalization exec")


def _hash_descriptor(descriptor: int, expected_count: int) -> tuple[str, int]:
    if type(expected_count) is not int or not 0 < expected_count <= 16 * 1024**2:
        _fail("executable byte count changed")
    digest = hashlib.sha256()
    offset = 0
    while offset < expected_count:
        chunk = os.pread(
            descriptor, min(1024 * 1024, expected_count - offset), offset
        )
        if not chunk:
            _fail("executable ended before its exact byte count")
        digest.update(chunk)
        offset += len(chunk)
    if os.pread(descriptor, 1, expected_count):
        _fail("executable exceeded its exact byte count")
    return digest.hexdigest(), offset


def _open_verified_executable(fact: dict[str, object], label: str) -> tuple[int, tuple[int, ...]]:
    keys = {"path", "sha256", "byte_count", "mode", "uid", "gid", "st_nlink"}
    if type(fact) is not dict or set(fact) != keys:
        _fail(label + " executable fact schema changed")
    path = fact["path"]
    if type(path) is not str or not path.startswith("/") or ".." in path.split("/"):
        _fail(label + " executable path changed")
    before = os.lstat(path)
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NOCTTY,
    )
    try:
        opened = os.fstat(descriptor)
        digest, count = _hash_descriptor(descriptor, fact.get("byte_count"))
        after = os.fstat(descriptor)
        final = os.lstat(path)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != fact["mode"]
            or opened.st_uid != fact["uid"]
            or opened.st_gid != fact["gid"]
            or opened.st_nlink != fact["st_nlink"]
            or count != fact["byte_count"]
            or digest != fact["sha256"]
            or _stable_state(before) != _stable_state(opened)
            or _stable_state(before) != _stable_state(after)
            or _stable_state(before) != _stable_state(final)
        ):
            _fail(label + " executable changed")
        return descriptor, _stable_state(after)
    except BaseException:
        os.close(descriptor)
        raise


def _verify_executable_path(descriptor: int, path: str, state: tuple[int, ...], label: str) -> None:
    if _stable_state(os.fstat(descriptor)) != state or _stable_state(os.lstat(path)) != state:
        _fail(label + " executable changed after use")


def _open_lexical_directory(path: str) -> int:
    parsed = Path(path)
    if not parsed.is_absolute() or ".." in parsed.parts:
        _fail("directory path is not lexical absolute")
    current = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in parsed.parts[1:]:
            observed = os.stat(component, dir_fd=current, follow_symlinks=False)
            if not stat.S_ISDIR(observed.st_mode):
                _fail("directory component changed type")
            successor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=current,
            )
            opened = os.fstat(successor)
            if (observed.st_dev, observed.st_ino) != (opened.st_dev, opened.st_ino):
                os.close(successor)
                _fail("directory component changed while opened")
            os.close(current)
            current = successor
        return current
    except BaseException:
        os.close(current)
        raise


def _write_once_at(directory_fd: int, name: str, raw: bytes) -> None:
    previous_umask = os.umask(0o077)
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
            | os.O_NOFOLLOW,
            0o400,
            dir_fd=directory_fd,
        )
    finally:
        os.umask(previous_umask)
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset : offset + 1024 * 1024])
            if written <= 0:
                _fail("write-once write made no progress")
            offset += written
        os.fsync(descriptor)
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o400
            or observed.st_uid != os.geteuid()
            or observed.st_gid != os.getegid()
            or observed.st_nlink != 1
            or observed.st_size != len(raw)
        ):
            _fail("write-once storage changed")
    finally:
        os.close(descriptor)
    final = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if (final.st_dev, final.st_ino) != (observed.st_dev, observed.st_ino):
        _fail("write-once path changed after close")


def _read_file_at(directory_fd: int, name: str, maximum: int) -> bytes:
    before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != REMOTE_UID
        or before.st_gid != REMOTE_GID
        or before.st_nlink != 1
        or not 0 < before.st_size <= maximum
    ):
        _fail("ledger file storage changed: " + name)
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=directory_fd,
    )
    chunks: list[bytes] = []
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("ledger file changed before open")
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("ledger file ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_uid",
        "st_gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(before, field) != getattr(final, field)
        for field in fields
    ):
        _fail("ledger file changed while read")
    return b"".join(chunks)


def _verify_service_transport_fact(
    plan: dict[str, object], service_raw: bytes
) -> None:
    facts = plan.get("control_facts")
    candidates = (
        [
            fact
            for fact in facts
            if type(fact) is dict
            and fact.get("name") == "TRANSPORT_MANIFEST.json"
        ]
        if type(facts) is list
        else []
    )
    if len(candidates) != 1:
        _fail("service transport control fact changed")
    control_fact = candidates[0]
    count = control_fact.get("byte_count")
    digest = control_fact.get("sha256")
    if (
        type(count) is not int
        or not 0 < count <= 16 * 1024**2
        or type(digest) is not str
        or _HEX64.fullmatch(digest) is None
    ):
        _fail("service transport control identity changed")
    roots: list[int] = []
    for key in ("preformal_scratch_root", "fixed_remote_root"):
        path = plan.get(key)
        if type(path) is not str:
            _fail("service selected control root changed type")
        try:
            roots.append(_open_lexical_directory(path))
        except FileNotFoundError:
            continue
    if len(roots) != 1:
        for descriptor in roots:
            os.close(descriptor)
        _fail("service selected transport root state changed")
    root_fd = roots[0]
    try:
        raw = _read_file_at(root_fd, "TRANSPORT_MANIFEST.json", 16 * 1024**2)
    finally:
        os.close(root_fd)
    if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
        _fail("service transport manifest bytes changed")
    transport = _canonical_document(raw, "service selected transport manifest")
    _verify_id(
        transport,
        schema="acfqp.v42_remote_ordinal2_transport_manifest.v42r1",
        identity="transport_manifest_id",
        domain=_DOMAIN + "transport-manifest",
    )
    if transport["transport_manifest_id"] != plan.get("transport_manifest_id"):
        _fail("service transport manifest plan join changed")
    artifact = plan.get("activation_service_artifact")
    rows = transport.get("transport_facts")
    if type(artifact) is not dict or type(rows) is not list:
        _fail("service artifact or transport facts changed type")
    matches = [
        row
        for row in rows
        if type(row) is dict
        and row.get("relative_path") == artifact.get("relative_path")
    ]
    actual_sha = hashlib.sha256(service_raw).hexdigest()
    actual_oid = hashlib.sha1(  # noqa: S324 - Git object identity
        f"blob {len(service_raw)}\0".encode("ascii") + service_raw
    ).hexdigest()
    if (
        len(matches) != 1
        or artifact.get("byte_count") != len(service_raw)
        or artifact.get("sha256") != actual_sha
        or artifact.get("git_blob_oid") != actual_oid
        or artifact.get("git_mode") != "100644"
        or artifact.get("git_object_type") != "blob"
        or matches[0].get("byte_count") != len(service_raw)
        or matches[0].get("sha256") != actual_sha
        or matches[0].get("git_blob_oid") != actual_oid
        or matches[0].get("git_mode") != "100644"
        or matches[0].get("git_object_type") != "blob"
    ):
        _fail("activation service does not join exact transport fact")


def _rename_noreplace_at(parent_fd: int, old_name: str, new_name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.syscall(
        ctypes.c_long(_SYS_RENAMEAT2_X86_64),
        ctypes.c_int(parent_fd),
        ctypes.c_char_p(old_name.encode("utf-8")),
        ctypes.c_int(parent_fd),
        ctypes.c_char_p(new_name.encode("utf-8")),
        ctypes.c_uint(_RENAME_NOREPLACE),
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), old_name + " -> " + new_name)


def _resource_checks(values: dict[str, object]) -> dict[str, bool]:
    ancestry = values.get("cgroup_memory_ancestry")
    if type(ancestry) is not list:
        _fail("service cgroup ancestry changed type")
    finite = [row for row in ancestry if row.get("memory_max_mode") == "FINITE"]
    return {
        "memory_total_gate": values["memory_total_bytes"] >= MINIMUM_MEMORY_TOTAL_BYTES,
        "memory_available_gate": values["memory_available_bytes"]
        >= MINIMUM_MEMORY_AVAILABLE_BYTES,
        "memory_observation_consistent": values["memory_available_bytes"]
        <= values["memory_total_bytes"],
        "swap_gate": values["swap_total_bytes"] == 0
        or values["swap_free_bytes"] >= MINIMUM_SWAP_FREE_BYTES,
        "swap_observation_consistent": values["swap_free_bytes"]
        <= values["swap_total_bytes"]
        and (values["swap_total_bytes"] != 0 or values["swap_free_bytes"] == 0),
        "filesystem_available_gate": values["filesystem_available_bytes"]
        >= MINIMUM_FILESYSTEM_AVAILABLE_BYTES,
        "cgroup_memory_gate": bool(finite)
        and all(
            row["memory_max_bytes"] >= MINIMUM_MEMORY_TOTAL_BYTES
            and row["memory_max_bytes"] - row["memory_current_bytes"]
            >= MINIMUM_MEMORY_AVAILABLE_BYTES
            for row in finite
        ),
        "cgroup_ancestry_reaches_root": bool(ancestry)
        and ancestry[-1].get("cgroup_path") == "/",
    }


def _default_resource_observer(parent_path: str) -> dict[str, object]:
    values: dict[str, int] = {}
    with open("/proc/meminfo", "rt", encoding="ascii") as stream:
        for line in stream:
            fields = line.split()
            if len(fields) == 3 and fields[2] == "kB" and fields[0].endswith(":"):
                values[fields[0][:-1]] = int(fields[1]) * 1024
    filesystem = os.statvfs(parent_path)
    with open("/proc/self/cgroup", "rt", encoding="ascii") as stream:
        line = stream.read(4096)
    if not line.startswith("0::") or line.count("\n") != 1:
        _fail("service cgroup record changed")
    current = Path(line[3:-1])
    ancestry: list[dict[str, object]] = []
    while True:
        directory = Path("/sys/fs/cgroup") / str(current).lstrip("/")
        maximum = directory / "memory.max"
        usage = directory / "memory.current"
        if maximum.exists() and usage.exists():
            maximum_raw = maximum.read_text(encoding="ascii")
            ancestry.append(
                {
                    "cgroup_path": str(current),
                    "memory_max_mode": "MAX" if maximum_raw == "max\n" else "FINITE",
                    "memory_max_bytes": None if maximum_raw == "max\n" else int(maximum_raw),
                    "memory_current_bytes": int(usage.read_text(encoding="ascii")),
                }
            )
        elif current == Path("/"):
            ancestry.append(
                {
                    "cgroup_path": "/",
                    "memory_max_mode": "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES",
                    "memory_max_bytes": None,
                    "memory_current_bytes": None,
                }
            )
        else:
            _fail("service cgroup ancestry omitted a non-root limit")
        if current == Path("/"):
            break
        current = current.parent
    return {
        "memory_total_bytes": values["MemTotal"],
        "memory_available_bytes": values["MemAvailable"],
        "swap_total_bytes": values["SwapTotal"],
        "swap_free_bytes": values["SwapFree"],
        "filesystem_available_bytes": filesystem.f_bavail * filesystem.f_frsize,
        "cgroup_memory_ancestry": ancestry,
    }


def _resource_gate(
    *, plan_id: str, stage: str, values: dict[str, object]
) -> dict[str, object]:
    checks = _resource_checks(values)
    return {
        "stage": stage,
        "materialization_activation_plan_id": plan_id,
        "memory_total_bytes": values["memory_total_bytes"],
        "memory_available_bytes": values["memory_available_bytes"],
        "swap_total_bytes": values["swap_total_bytes"],
        "swap_free_bytes": values["swap_free_bytes"],
        "filesystem_available_bytes": values["filesystem_available_bytes"],
        "cgroup_memory_ancestry": values["cgroup_memory_ancestry"],
        "resource_gate_checks": checks,
        "all_resource_gates_passed": all(checks.values()),
        "observation_was_read_only": True,
    }


def _replace_template(template: object, replacements: dict[str, str], label: str) -> list[str]:
    if type(template) is not list or any(type(item) is not str for item in template):
        _fail(label + " template changed")
    result: list[str] = []
    for item in template:
        value = item
        for sentinel, replacement in replacements.items():
            value = value.replace(sentinel, replacement)
        result.append(value)
    if any("{acfqp_v42_" in item for item in result):
        _fail(label + " template replacement was incomplete")
    return result


def _expected_service_argv(
    plan: dict[str, object], remote_attempt_id: str, invocation_id: str, control_group: str
) -> list[str]:
    contract = plan.get("systemd_service_contract")
    if type(contract) is not dict:
        _fail("systemd service contract changed")
    return _replace_template(
        contract.get("authorized_service_worker_argv_template"),
        {
            "{acfqp_v42_remote_materialization_activation_attempt_id}": remote_attempt_id,
            "{acfqp_v42_systemd_invocation_id}": invocation_id,
            "{acfqp_v42_systemd_control_group}": control_group,
        },
        "systemd service worker argv",
    )


def _expected_bootstrap_argv(plan: dict[str, object], remote_attempt_id: str) -> list[str]:
    contract = plan.get("systemd_service_contract")
    if type(contract) is not dict:
        _fail("systemd service contract changed")
    return _replace_template(
        contract.get("authorized_service_bootstrap_argv_template"),
        {
            "{acfqp_v42_remote_materialization_activation_attempt_id}": remote_attempt_id,
        },
        "systemd service bootstrap argv",
    )


def _expected_systemctl_argv(plan: dict[str, object]) -> list[str]:
    contract = plan.get("systemd_service_contract")
    if type(contract) is not dict:
        _fail("systemd service contract changed")
    return _replace_template(
        contract.get("authorized_systemctl_show_argv_template"),
        {
            "{acfqp_v42_materialization_activation_plan_id}": str(
                plan["materialization_activation_plan_id"]
            )
        },
        "systemctl show argv",
    )


def _parse_systemctl_properties(raw: bytes) -> dict[str, str]:
    if not raw.endswith(b"\n") or b"\0" in raw:
        _fail("systemctl properties changed framing")
    try:
        lines = raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as error:
        raise _ActivationServiceFailure("systemctl properties are not UTF-8") from error
    result: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            _fail("systemctl property line changed")
        key, value = line.split("=", 1)
        if key in result:
            _fail("systemctl property was duplicated")
        result[key] = value
    expected = {
        "Id", "LoadState", "ActiveState", "SubState", "FragmentPath",
        "MainPID", "InvocationID", "ControlGroup", "Type",
        "StandardInput", "StandardOutput", "StandardError", "Restart",
        "UMask", "KillMode", "RuntimeMaxUSec", "WorkingDirectory", "Slice",
    }
    if set(result) != expected:
        _fail("systemctl property keyset changed")
    return result


def _run_pinned_systemctl(plan: dict[str, object]) -> dict[str, str]:
    contract = plan.get("systemd_service_contract")
    if type(contract) is not dict:
        _fail("systemd service contract changed")
    fact = contract.get("systemctl")
    descriptor, state = _open_verified_executable(fact, "systemctl")
    argv = _expected_systemctl_argv(plan)
    try:
        process = subprocess.Popen(
            argv,
            executable=f"/proc/self/fd/{descriptor}",
            env=dict(SYSTEMD_CLIENT_ENVIRONMENT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            pass_fds=(descriptor,),
            start_new_session=True,
        )
        stdout, stderr = _bounded_child_output(
            process,
            stdout_cap=256 * 1024,
            stderr_cap=64 * 1024,
            timeout_seconds=10.0,
            label="systemctl read-only observation",
        )
        _verify_executable_path(descriptor, str(fact["path"]), state, "systemctl")
    except BaseException:
        if "process" in locals():
            _terminate_child_group(process)
        raise
    finally:
        os.close(descriptor)
    if process.returncode != 0 or stderr or len(stdout) > 256 * 1024:
        _fail("systemctl read-only observation did not close exactly")
    return _parse_systemctl_properties(stdout)


def _terminate_child_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        _fail("bounded systemctl child could not be reaped")


def _bounded_child_output(
    process: subprocess.Popen[bytes],
    *,
    stdout_cap: int,
    stderr_cap: int,
    timeout_seconds: float,
    label: str,
) -> tuple[bytes, bytes]:
    if (
        process.stdout is None
        or process.stderr is None
        or type(stdout_cap) is not int
        or type(stderr_cap) is not int
        or not 0 < stdout_cap <= 4 * 1024**2
        or not 0 < stderr_cap <= 4 * 1024**2
        or not 0.0 < timeout_seconds <= 60.0
    ):
        _terminate_child_group(process)
        _fail(label + " bounded output contract changed")
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    streams = {
        stdout_fd: (process.stdout, stdout_cap, bytearray()),
        stderr_fd: (process.stderr, stderr_cap, bytearray()),
    }
    selector = selectors.DefaultSelector()
    deadline = time.monotonic() + timeout_seconds
    try:
        for descriptor, (stream, _cap, _buffer) in streams.items():
            os.set_blocking(descriptor, False)
            selector.register(stream, selectors.EVENT_READ, descriptor)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate_child_group(process)
                _fail(label + " timed out")
            for key, _mask in selector.select(min(remaining, 0.1)):
                descriptor = int(key.data)
                stream, cap, buffer = streams[descriptor]
                try:
                    chunk = os.read(descriptor, min(65536, cap + 1 - len(buffer)))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                buffer.extend(chunk)
                if len(buffer) > cap:
                    _terminate_child_group(process)
                    _fail(label + " exceeded cap")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_child_group(process)
            _fail(label + " timed out")
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _terminate_child_group(process)
            _fail(label + " timed out")
        return bytes(streams[stdout_fd][2]), bytes(streams[stderr_fd][2])
    except BaseException:
        _terminate_child_group(process)
        raise
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            if not stream.closed:
                stream.close()


def _normalize_unit_properties(
    *,
    plan: dict[str, object],
    remote_attempt_id: str,
    invocation_id: str,
    control_group: str,
    service_pid: int,
    raw_properties: dict[str, str],
    invocation_symlink_verified: bool,
) -> dict[str, object]:
    unit = SYSTEMD_UNIT_PREFIX + str(plan["materialization_activation_plan_id"]) + ".service"
    try:
        main_pid = int(raw_properties["MainPID"])
    except (KeyError, ValueError) as error:
        raise _ActivationServiceFailure("systemd MainPID changed") from error
    normalized: dict[str, object] = {
        key: raw_properties[key]
        for key in (
            "Id", "LoadState", "ActiveState", "SubState", "FragmentPath",
            "InvocationID", "ControlGroup", "Type", "StandardInput",
            "StandardOutput", "StandardError", "Restart", "UMask", "KillMode",
            "RuntimeMaxUSec", "WorkingDirectory", "Slice",
        )
    }
    normalized["MainPID"] = main_pid
    normalized["bootstrap_argv_verified_by_tiny_loader_before_clean_exec"] = True
    normalized["invocation_symlink_verified"] = invocation_symlink_verified
    normalized["observed_via_pinned_systemctl_executable"] = True
    normalized["systemctl_argv"] = _expected_systemctl_argv(plan)
    expected = {
        "Id": unit,
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "running",
        "FragmentPath": f"/run/user/{REMOTE_UID}/systemd/transient/{unit}",
        "MainPID": service_pid,
        "InvocationID": invocation_id,
        "ControlGroup": control_group,
        "Type": "exec",
        "bootstrap_argv_verified_by_tiny_loader_before_clean_exec": True,
        "StandardInput": "null",
        "StandardOutput": "null",
        "StandardError": "null",
        "Restart": "no",
        "UMask": "0077",
        "KillMode": "control-group",
        "RuntimeMaxUSec": "1w",
        "WorkingDirectory": str(Path(str(plan["fixed_remote_root"])).parent),
        "Slice": "app.slice",
        "invocation_symlink_verified": True,
        "observed_via_pinned_systemctl_executable": True,
        "systemctl_argv": _expected_systemctl_argv(plan),
    }
    if normalized != expected:
        _fail("live systemd unit properties changed")
    return normalized


def _default_unit_observer(
    plan: dict[str, object],
    remote_attempt_id: str,
    invocation_id: str,
    control_group: str,
    service_pid: int,
) -> dict[str, object]:
    unit = SYSTEMD_UNIT_PREFIX + str(plan["materialization_activation_plan_id"]) + ".service"
    if not control_group.endswith("/app.slice/" + unit):
        _fail("service cgroup does not end in its exact unit")
    if (
        service_pid != os.getpid()
        or _process_unified_cgroup(service_pid) != control_group
    ):
        _fail("live service PID cgroup does not join the clean runtime")
    invocation_path = Path(
        f"/run/user/{REMOTE_UID}/systemd/units/invocation:" + unit
    )
    before = os.lstat(invocation_path)
    if not stat.S_ISLNK(before.st_mode):
        _fail("service invocation symlink is absent")
    target = os.readlink(invocation_path)
    try:
        target_hex = uuid.UUID(target).hex
    except ValueError as error:
        raise _ActivationServiceFailure("service invocation symlink changed") from error
    after = os.lstat(invocation_path)
    if _stable_state(before) != _stable_state(after) or target_hex != invocation_id:
        _fail("service invocation symlink/systemd ID join changed")
    return _normalize_unit_properties(
        plan=plan,
        remote_attempt_id=remote_attempt_id,
        invocation_id=invocation_id,
        control_group=control_group,
        service_pid=service_pid,
        raw_properties=_run_pinned_systemctl(plan),
        invocation_symlink_verified=True,
    )


def _identity(path: str, observed: os.stat_result, node_type: str) -> dict[str, object]:
    return {
        "path": path,
        "node_type": node_type,
        "st_dev": observed.st_dev,
        "st_ino": observed.st_ino,
        "mode": stat.S_IMODE(observed.st_mode),
        "uid": observed.st_uid,
        "gid": observed.st_gid,
        "st_nlink": observed.st_nlink,
        "st_size": observed.st_size,
        "st_mtime_ns": observed.st_mtime_ns,
        "st_ctime_ns": observed.st_ctime_ns,
    }


def _exact_five_snapshot(
    *, root_path: str, control_facts: list[dict[str, object]], durable: bool
) -> dict[str, object]:
    root_fd = _open_lexical_directory(root_path)
    try:
        root_stat = os.fstat(root_fd)
        if (
            stat.S_IMODE(root_stat.st_mode) != 0o700
            or root_stat.st_uid != REMOTE_UID
            or root_stat.st_gid != REMOTE_GID
            or sorted(os.listdir(root_fd)) != list(CONTROL_NAMES)
        ):
            _fail("exact-five root storage changed")
        facts_by_name = {str(row["name"]): row for row in control_facts}
        controls: list[dict[str, object]] = []
        for name in CONTROL_NAMES:
            fact = facts_by_name[name]
            before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != REMOTE_UID
                or before.st_gid != REMOTE_GID
                or before.st_nlink != 1
                or before.st_size != fact["byte_count"]
            ):
                _fail("exact-five control storage changed")
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=root_fd,
            )
            digest = hashlib.sha256()
            try:
                offset = 0
                while offset < before.st_size:
                    chunk = os.pread(
                        descriptor, min(1024 * 1024, before.st_size - offset), offset
                    )
                    if not chunk:
                        _fail("exact-five control ended early")
                    digest.update(chunk)
                    offset += len(chunk)
                if durable:
                    os.fsync(descriptor)
                after = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            final = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            fields = (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_uid",
                "st_gid",
                "st_nlink",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
            if (
                digest.hexdigest() != fact["sha256"]
                or any(
                    getattr(before, field) != getattr(after, field)
                    or getattr(before, field) != getattr(final, field)
                    for field in fields
                )
            ):
                _fail("exact-five control changed while verified")
            controls.append(
                {
                    "name": name,
                    "path": str(Path(root_path) / name),
                    "sha256": fact["sha256"],
                    "byte_count": fact["byte_count"],
                    "mode": 0o400,
                    "uid": REMOTE_UID,
                    "gid": REMOTE_GID,
                    "identity": _identity(
                        str(Path(root_path) / name), before, "REGULAR_FILE"
                    ),
                }
            )
        if durable:
            os.fsync(root_fd)
        return {
            "root_path": root_path,
            "root_identity": _identity(root_path, root_stat, "DIRECTORY"),
            "control_facts": controls,
            "exact_inventory": list(CONTROL_NAMES),
            "every_file_hashed_and_fsynced_through_one_pinned_descriptor": True,
            "root_directory_fsynced": True,
            "whole_tree_first_last_snapshot_equal": True,
            "no_symlink_hardlink_or_special_node": True,
        }
    finally:
        os.close(root_fd)


def _same_inode_before_publish(
    before: dict[str, object], after: dict[str, object]
) -> bool:
    fields = (
        "node_type",
        "st_dev",
        "st_ino",
        "mode",
        "uid",
        "gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    return all(before[field] == after[field] for field in fields)


def _same_inode_after_rename(
    before: dict[str, object], after: dict[str, object]
) -> bool:
    fields = (
        "node_type",
        "st_dev",
        "st_ino",
        "mode",
        "uid",
        "gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
    )
    return all(before[field] == after[field] for field in fields)


def _service_receipt(
    *,
    plan: dict[str, object],
    remote: dict[str, object],
    invocation_id: str,
    control_group: str,
    gate: dict[str, object],
    observed_argv: list[str],
    service_pid: int,
    live_unit_properties: dict[str, object],
) -> dict[str, object]:
    plan_id = str(plan["materialization_activation_plan_id"])
    payload = {
        **_base(SERVICE_RECEIPT_SCHEMA),
        "materialization_activation_plan_id": plan_id,
        "remote_materialization_activation_attempt_id": remote[
            "remote_materialization_activation_attempt_id"
        ],
        "preformal_upload_receipt_id": plan["preformal_upload_receipt_id"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "systemd_unit_name": SYSTEMD_UNIT_PREFIX + plan_id + ".service",
        "systemd_invocation_id": invocation_id,
        "systemd_control_group": control_group,
        "systemd_main_pid": service_pid,
        "live_systemd_unit_properties": live_unit_properties,
        "systemd_unit_properties_exact": True,
        "observed_service_argv": observed_argv,
        "observed_environment": dict(SERVICE_ENVIRONMENT),
        "exact_live_file_descriptors": [0, 1, 2],
        "stdin_stdout_stderr_are_systemd_null_devices": True,
        "first_service_resource_gate": gate,
        "fixed_remote_root_state": "ABSENT",
        "scratch_state": "EXACT_DIRECTORY",
        "published_as_first_systemd_service_mutation": True,
        "published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ledger_and_parent_fsynced_before_staging_or_fixed_root_effect": True,
        "published_before_publish_ready_or_fixed_root_rename": True,
        "same_service_identity_retry_forbidden": True,
    }
    return {
        **payload,
        "remote_activation_service_receipt_id": _content_id(
            _DOMAIN + "remote-activation-service-receipt", payload
        ),
    }


def _ready(
    *,
    plan: dict[str, object],
    remote: dict[str, object],
    receipt: dict[str, object],
    gate: dict[str, object],
    scratch_snapshot: dict[str, object],
) -> dict[str, object]:
    payload = {
        **_base(READY_SCHEMA),
        "materialization_activation_plan_id": plan[
            "materialization_activation_plan_id"
        ],
        "remote_materialization_activation_attempt_id": remote[
            "remote_materialization_activation_attempt_id"
        ],
        "remote_activation_service_receipt_id": receipt[
            "remote_activation_service_receipt_id"
        ],
        "preformal_upload_receipt_id": plan["preformal_upload_receipt_id"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "second_service_resource_gate": gate,
        "live_scratch_snapshot": scratch_snapshot,
        "fixed_remote_root_state": "ABSENT",
        "scratch_and_fixed_root_share_one_pinned_parent": True,
        "all_scratch_files_hashed_and_fsynced_through_pinned_descriptors": True,
        "scratch_root_and_shared_parent_fsynced_before_ready": True,
        "ready_published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ledger_and_shared_parent_fsynced_after_ready": True,
        "root_rename_noreplace_not_started_before_ready_durable": True,
        "failure_publication_forbidden_after_ready": True,
        "same_activation_identity_retry_forbidden": True,
    }
    return {
        **payload,
        "remote_activation_publish_ready_id": _content_id(
            _DOMAIN + "remote-activation-publish-ready", payload
        ),
    }


def _terminal(
    *,
    plan: dict[str, object],
    remote: dict[str, object],
    receipt: dict[str, object],
    ready: dict[str, object],
    fixed_snapshot: dict[str, object],
) -> dict[str, object]:
    payload = {
        **_base(TERMINAL_SCHEMA),
        "materialization_activation_plan_id": plan[
            "materialization_activation_plan_id"
        ],
        "remote_materialization_activation_attempt_id": remote[
            "remote_materialization_activation_attempt_id"
        ],
        "remote_activation_service_receipt_id": receipt[
            "remote_activation_service_receipt_id"
        ],
        "remote_activation_publish_ready_id": ready[
            "remote_activation_publish_ready_id"
        ],
        "preformal_upload_receipt_id": plan["preformal_upload_receipt_id"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "local_materialization_attempt_id": plan["local_materialization_attempt_id"],
        "fixed_root_snapshot": fixed_snapshot,
        "scratch_root_state": "ABSENT",
        "fixed_remote_root_state": "EXACT_DIRECTORY",
        "fixed_root_publish_method": "RENAMEAT2_NOREPLACE_SAME_PARENT",
        "root_rename_noreplace_completed": True,
        "shared_parent_fsync_completed_after_rename": True,
        "fixed_root_postpublish_pinned_whole_tree_reverify_completed": True,
        "terminal_published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ledger_and_shared_parent_fsynced_after_terminal": True,
        "trusted_bootstrap_outer_command": plan["trusted_bootstrap_outer_command"],
        "terminal_verified_by_service_before_exact_outer_exec": True,
        "terminal_id_and_canonical_bytes_reverified_by_same_service_context_before_exec": True,
        "trusted_bootstrap_outer_exec_started_at_terminal_publication": False,
        "durable_terminal_authorizes_same_service_context_next_step_exact_outer_exec": True,
        "downstream_launcher_evidence_terminal_id_join_is_defense_in_depth": True,
        "downstream_launcher_evidence_terminal_id_join_implemented": False,
        "formal_outer_exec_enabled_after_service_successor_join": True,
        "transport_classification": "COMPLETE_TRANSPORT_SUCCESS",
        "same_activation_identity_retry_forbidden": True,
    }
    return {
        **payload,
        "remote_materialization_transport_terminal_id": _content_id(
            _DOMAIN + "remote-materialization-transport-terminal", payload
        ),
    }


def _typed_resource_failure(
    *,
    plan: dict[str, object],
    remote: dict[str, object],
    receipt: dict[str, object] | None,
    message: str,
) -> dict[str, object]:
    stage = (
        "SYSTEMD_ADMISSION_BEFORE_SERVICE_RECEIPT"
        if receipt is None
        else "SERVICE_AFTER_RECEIPT_BEFORE_READY"
    )
    payload = {
        **_base(FAILURE_SCHEMA),
        "materialization_activation_plan_id": plan[
            "materialization_activation_plan_id"
        ],
        "remote_materialization_activation_attempt_id": remote[
            "remote_materialization_activation_attempt_id"
        ],
        "remote_activation_service_receipt_id": (
            None if receipt is None else receipt["remote_activation_service_receipt_id"]
        ),
        "preformal_upload_receipt_id": plan["preformal_upload_receipt_id"],
        "source_manifest_id": plan["source_manifest_id"],
        "transport_manifest_id": plan["transport_manifest_id"],
        "failure_stage": stage,
        "failure_classification": "RESOURCE_GATE_FAILED",
        "failure_message": message,
        "publish_ready_state": "ABSENT",
        "fixed_remote_root_state": "ABSENT",
        "fixed_root_publish_started": False,
        "root_rename_noreplace_called": False,
        "trusted_bootstrap_outer_exec_started": False,
        "failure_published_o_excl_nofollow_mode_0400_and_fsynced": True,
        "ledger_and_shared_parent_fsynced_after_failure": True,
        "same_activation_identity_retry_forbidden": True,
        "read_only_followup_only": True,
    }
    return {
        **payload,
        "remote_materialization_activation_failure_id": _content_id(
            _DOMAIN + "remote-materialization-activation-failure", payload
        ),
    }


def _default_outer_exec(argv: list[str], plan: dict[str, object]) -> None:
    startup = plan.get("remote_startup_tcb_contract")
    if type(startup) is not dict:
        _fail("trusted bootstrap Python TCB changed")
    invocation_path = startup.get("python_invocation_path")
    real_path = startup.get("python_realpath")
    if (
        argv != plan.get("trusted_bootstrap_outer_command")
        or not argv
        or argv[0] != invocation_path
        or sys.executable != invocation_path
        or os.path.realpath(sys.executable) != real_path
    ):
        _fail("trusted bootstrap outer command or live Python changed")
    link = os.lstat(str(invocation_path))
    if (
        not stat.S_ISLNK(link.st_mode)
        or os.readlink(str(invocation_path))
        != startup.get("python_invocation_link_target")
        or stat.S_IMODE(link.st_mode) != startup.get("python_invocation_mode")
        or link.st_uid != startup.get("python_invocation_uid")
        or link.st_gid != startup.get("python_invocation_gid")
        or link.st_nlink != startup.get("python_invocation_nlink")
    ):
        _fail("trusted bootstrap Python invocation changed")
    fact = {
        "path": real_path,
        "sha256": startup.get("python_realpath_sha256"),
        "byte_count": startup.get("python_realpath_byte_count"),
        "mode": startup.get("python_realpath_mode"),
        "uid": startup.get("python_realpath_uid"),
        "gid": startup.get("python_realpath_gid"),
        "st_nlink": startup.get("python_realpath_nlink"),
    }
    descriptor, state = _open_verified_executable(fact, "trusted bootstrap Python")
    try:
        _verify_executable_path(
            descriptor, str(real_path), state, "trusted bootstrap Python"
        )
        os.execve(f"/proc/self/fd/{descriptor}", argv, {})
    finally:
        os.close(descriptor)
    _fail("trusted bootstrap outer exec returned")


def run_service_v42r1(
    *,
    remote_activation_attempt_id: str,
    systemd_invocation_id: str,
    systemd_control_group: str,
    observed_service_argv: list[str],
    resource_observer: Callable[[str], dict[str, object]] = _default_resource_observer,
    unit_observer: Callable[
        [dict[str, object], str, str, str, int], dict[str, object]
    ] = _default_unit_observer,
    outer_exec: Callable[[list[str], dict[str, object]], None] = _default_outer_exec,
    fault_hook: Callable[[str], None] | None = None,
    fixed_ledger_override_for_offline_fixture: str | None = None,
    formal_runtime_checks: bool = True,
) -> dict[str, object]:
    def cut(name: str) -> None:
        if fault_hook is not None:
            fault_hook(name)

    if (
        _HEX64.fullmatch(remote_activation_attempt_id) is None
        or _HEX32.fullmatch(systemd_invocation_id) is None
        or not systemd_control_group.startswith("/")
    ):
        _fail("clean service runtime changed")
    if formal_runtime_checks:
        if os.environ != SERVICE_ENVIRONMENT:
            _fail("clean service environment changed")
        if socket.gethostname() != REMOTE_HOSTNAME or pwd.getpwuid(os.geteuid()).pw_name != REMOTE_USER:
            _fail("service host identity changed")
        _require_exact_devnull_stdio()
        _require_current_unified_cgroup(systemd_control_group)
    # The fixed ledger path is recoverable from the remote attempt only after
    # opening the one registered fixed name.  Formal mode never accepts an
    # alternate path.
    fixed_ledger = (
        "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2-transport-ledger"
        if fixed_ledger_override_for_offline_fixture is None
        else fixed_ledger_override_for_offline_fixture
    )
    ledger_fd = _open_lexical_directory(fixed_ledger)
    try:
        attempt_raw = _read_file_at(ledger_fd, REMOTE_ATTEMPT_NAME, 4 * 1024**2)
        remote = _canonical_document(attempt_raw, "remote activation attempt")
        _verify_id(
            remote,
            schema=REMOTE_ATTEMPT_SCHEMA,
            identity="remote_materialization_activation_attempt_id",
            domain=_DOMAIN + "remote-materialization-activation-attempt",
        )
        if remote["remote_materialization_activation_attempt_id"] != remote_activation_attempt_id:
            _fail("service selected a different remote attempt")
        plan = remote.get("materialization_activation_plan")
        if type(plan) is not dict or plan.get("materialization_activation_plan_id") != remote.get(
            "materialization_activation_plan_id"
        ):
            _fail("service remote attempt omitted its activation plan")
        if str(plan.get("fixed_transport_ledger_root")) != fixed_ledger:
            _fail("service fixed ledger path changed")
        service_raw = _read_file_at(ledger_fd, SERVICE_SOURCE_NAME, 4 * 1024**2)
        _verify_service_transport_fact(plan, service_raw)
        expected_unit = SYSTEMD_UNIT_PREFIX + str(
            plan["materialization_activation_plan_id"]
        ) + ".service"
        if (
            not systemd_control_group.endswith("/app.slice/" + expected_unit)
            or observed_service_argv
            != _expected_service_argv(
                plan,
                remote_activation_attempt_id,
                systemd_invocation_id,
                systemd_control_group,
            )
        ):
            _fail("service argv, unit, or cgroup changed before first effect")
        expected_names = sorted((REMOTE_ATTEMPT_NAME, SERVICE_SOURCE_NAME))
        if sorted(os.listdir(ledger_fd)) != expected_names:
            _fail("service initial ledger inventory changed")
        service_pid = os.getpid()
        live_unit = unit_observer(
            plan,
            remote_activation_attempt_id,
            systemd_invocation_id,
            systemd_control_group,
            service_pid,
        )
        parent_path = str(Path(str(plan["fixed_remote_root"])).parent)
        first_values = resource_observer(parent_path)
        first_gate = _resource_gate(
            plan_id=str(plan["materialization_activation_plan_id"]),
            stage="SYSTEMD_SERVICE_RECEIPT_GATE",
            values=first_values,
        )
        if first_gate["all_resource_gates_passed"] is not True:
            failure = _typed_resource_failure(
                plan=plan,
                remote=remote,
                receipt=None,
                message="first service resource gate failed",
            )
            _write_once_at(ledger_fd, FAILURE_NAME, _canonical_bytes(failure))
            os.fsync(ledger_fd)
            return failure
        receipt = _service_receipt(
            plan=plan,
            remote=remote,
            invocation_id=systemd_invocation_id,
            control_group=systemd_control_group,
            gate=first_gate,
            observed_argv=observed_service_argv,
            service_pid=service_pid,
            live_unit_properties=live_unit,
        )
        cut("BEFORE_SERVICE_RECEIPT_WRITE")
        _write_once_at(ledger_fd, SERVICE_RECEIPT_NAME, _canonical_bytes(receipt))
        os.fsync(ledger_fd)
        cut("AFTER_SERVICE_RECEIPT_FSYNC")
        second_values = resource_observer(parent_path)
        second_gate = _resource_gate(
            plan_id=str(plan["materialization_activation_plan_id"]),
            stage="SYSTEMD_SERVICE_PUBLISH_GATE",
            values=second_values,
        )
        if second_gate["all_resource_gates_passed"] is not True:
            failure = _typed_resource_failure(
                plan=plan,
                remote=remote,
                receipt=receipt,
                message="second service resource gate failed",
            )
            _write_once_at(ledger_fd, FAILURE_NAME, _canonical_bytes(failure))
            os.fsync(ledger_fd)
            return failure
        scratch = _exact_five_snapshot(
            root_path=str(plan["preformal_scratch_root"]),
            control_facts=list(plan["control_facts"]),
            durable=True,
        )
        selected = plan["selected_remote_snapshot"]
        if not _same_inode_before_publish(
            selected["scratch_root_identity"], scratch["root_identity"]
        ):
            _fail("service scratch root changed after resource probe")
        for before, after in zip(
            selected["control_identities"], scratch["control_facts"], strict=True
        ):
            if (
                before["name"] != after["name"]
                or before["sha256"] != after["sha256"]
                or before["byte_count"] != after["byte_count"]
                or not _same_inode_before_publish(before["identity"], after["identity"])
            ):
                _fail("service scratch control changed after resource probe")
        ready = _ready(
            plan=plan,
            remote=remote,
            receipt=receipt,
            gate=second_gate,
            scratch_snapshot=scratch,
        )
        cut("BEFORE_READY_WRITE")
        _write_once_at(ledger_fd, READY_NAME, _canonical_bytes(ready))
        os.fsync(ledger_fd)
        cut("AFTER_READY_FSYNC")
        parent_fd = _open_lexical_directory(parent_path)
        try:
            scratch_name = Path(str(plan["preformal_scratch_root"])).name
            fixed_name = Path(str(plan["fixed_remote_root"])).name
            cut("BEFORE_FIXED_ROOT_RENAME")
            _rename_noreplace_at(parent_fd, scratch_name, fixed_name)
            cut("AFTER_FIXED_ROOT_RENAME_BEFORE_PARENT_FSYNC")
            os.fsync(parent_fd)
            cut("AFTER_FIXED_ROOT_PARENT_FSYNC")
        finally:
            os.close(parent_fd)
        fixed = _exact_five_snapshot(
            root_path=str(plan["fixed_remote_root"]),
            control_facts=list(plan["control_facts"]),
            durable=True,
        )
        if not _same_inode_after_rename(
            scratch["root_identity"], fixed["root_identity"]
        ):
            _fail("fixed root is not the selected scratch inode")
        for before, after in zip(scratch["control_facts"], fixed["control_facts"], strict=True):
            if before["name"] != after["name"] or not _same_inode_before_publish(
                before["identity"], after["identity"]
            ):
                _fail("fixed control is not the selected scratch inode")
        terminal = _terminal(
            plan=plan,
            remote=remote,
            receipt=receipt,
            ready=ready,
            fixed_snapshot=fixed,
        )
        cut("BEFORE_TERMINAL_WRITE")
        terminal_raw = _canonical_bytes(terminal)
        _write_once_at(ledger_fd, TERMINAL_NAME, terminal_raw)
        os.fsync(ledger_fd)
        parent_fd = _open_lexical_directory(parent_path)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        cut("AFTER_TERMINAL_FSYNC")
        readback = _read_file_at(ledger_fd, TERMINAL_NAME, 4 * 1024**2)
        if readback != terminal_raw:
            _fail("durable terminal readback changed")
        cut("BEFORE_TRUSTED_OUTER_EXEC")
        argv = list(plan["trusted_bootstrap_outer_command"])
    finally:
        os.close(ledger_fd)
    outer_exec(argv, plan)
    return terminal


def main_v42r1(
    *,
    remote_activation_attempt_id: str,
    systemd_invocation_id: str,
    systemd_control_group: str,
) -> int:
    run_service_v42r1(
        remote_activation_attempt_id=remote_activation_attempt_id,
        systemd_invocation_id=systemd_invocation_id,
        systemd_control_group=systemd_control_group,
        observed_service_argv=list(sys.orig_argv),
    )
    return 0
