"""Stdlib-only ingress receiver for V42 materialization activation.

The committed tiny loader verifies these bytes before compilation.  This file
never imports the project package.  It has three operations: a read-only
resource probe, one formal activation of a selected complete pre-formal
receipt, and read-only state observation after a disconnect.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import shlex
import signal
import socket
import stat
import subprocess
import sys
import time
from typing import Callable


SCHEMA_VERSION = "42.1.0"
FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2"
GLOBAL_EXECUTION_ORDINAL = 2
REMOTE_HOSTNAME = "erzhu419-Super-Server"
REMOTE_USER = "erzhu419"
REMOTE_UID = 1000
REMOTE_GID = 1000
REMOTE_PARENT = "/home/erzhu419/mine_code"
FIXED_ROOT = REMOTE_PARENT + "/.acfqp-v42-remote-ordinal2"
FIXED_LEDGER = REMOTE_PARENT + "/.acfqp-v42-remote-ordinal2-transport-ledger"

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
BOOTSTRAP_REMOTE_ATTEMPT_NAME = "MATERIALIZATION_ATTEMPT.json"
BOOTSTRAP_MATERIALIZATION_TERMINAL_NAME = (
    ".V42_REMOTE_ORDINAL2_MATERIALIZATION_TERMINAL.json"
)
BOOTSTRAP_MATERIALIZATION_FAILURE_NAME = "MATERIALIZATION_FAILURE.json"

ACTIVATION_PLAN_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_activation_plan.v42r1"
)
RESOURCE_PLAN_SCHEMA = (
    "acfqp.v42_remote_ordinal2_preactivation_resource_probe_plan.v42r1"
)
LOCAL_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_local_materialization_activation_attempt.v42r1"
)
NETWORK_START_SCHEMA = (
    "acfqp.v42_remote_ordinal2_materialization_activation_network_start.v42r1"
)
REMOTE_ATTEMPT_SCHEMA = (
    "acfqp.v42_remote_ordinal2_remote_materialization_activation_attempt.v42r1"
)

_DOMAIN = "acfqp:v42-remote-ordinal2:"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SYS_RENAMEAT2_X86_64 = 316
_RENAME_NOREPLACE = 1
_AT_FDCWD = -100
_MAXIMUM_ENVELOPE_BYTES = 4 * 1024**2
_MAXIMUM_OUTPUT_BYTES = 32 * 1024**2
_SYSTEMD_RUN_TIMEOUT_SECONDS = 30.0
_SYSTEMD_RUN_TERM_GRACE_SECONDS = 1.0


class _ActivationReceiverFailure(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise _ActivationReceiverFailure(message)


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
        raise _ActivationReceiverFailure("value is not canonical JSON") from error


def _canonical_document(raw: bytes, label: str) -> dict[str, object]:
    if type(raw) is not bytes or not raw or len(raw) > _MAXIMUM_ENVELOPE_BYTES:
        _fail(label + " byte envelope changed")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except _ActivationReceiverFailure:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise _ActivationReceiverFailure(label + " is not strict JSON") from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(label + " is not a canonical JSON object")
    return value


def _content_id(domain: str, payload: dict[str, object]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + _canonical_bytes(payload)
    ).hexdigest()


def _verify_id(
    document: object,
    *,
    schema: str,
    identity: str,
    domain: str,
    label: str,
) -> dict[str, object]:
    if type(document) is not dict:
        _fail(label + " changed type")
    if (
        document.get("schema") != schema
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != FORMAL_IDENTITY
        or document.get("global_execution_ordinal") != GLOBAL_EXECUTION_ORDINAL
    ):
        _fail(label + " authority header changed")
    observed = document.get(identity)
    if type(observed) is not str or _HEX64.fullmatch(observed) is None:
        _fail(label + " identity changed")
    payload = dict(document)
    del payload[identity]
    if observed != _content_id(domain, payload):
        _fail(label + " content identity changed")
    return dict(document)


def _stat_identity(path: str, observed: os.stat_result, node_type: str) -> dict[str, object]:
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


def _open_lexical_directory(path: str) -> int:
    parsed = Path(path)
    if not parsed.is_absolute() or ".." in parsed.parts:
        _fail("directory path is not lexical absolute")
    current = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in parsed.parts[1:]:
            observed = os.stat(component, dir_fd=current, follow_symlinks=False)
            if not stat.S_ISDIR(observed.st_mode):
                _fail("lexical directory component changed type")
            successor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=current,
            )
            opened = os.fstat(successor)
            if (observed.st_dev, observed.st_ino) != (opened.st_dev, opened.st_ino):
                os.close(successor)
                _fail("lexical directory component changed during open")
            os.close(current)
            current = successor
        return current
    except BaseException:
        os.close(current)
        raise


def _hash_regular_at(
    parent_fd: int,
    name: str,
    *,
    expected_mode: int,
    expected_uid: int,
    expected_gid: int,
    expected_count: int,
    expected_sha256: str,
    durable: bool,
) -> tuple[dict[str, object], bytes]:
    before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != expected_mode
        or before.st_uid != expected_uid
        or before.st_gid != expected_gid
        or before.st_nlink != 1
        or before.st_size != expected_count
    ):
        _fail("regular-file storage changed: " + name)
    descriptor = os.open(
        name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=parent_fd
    )
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    remaining = expected_count
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("regular-file name changed before open: " + name)
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("regular file ended early: " + name)
            digest.update(chunk)
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("regular file has trailing bytes: " + name)
        if durable:
            os.fsync(descriptor)
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
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
        getattr(before, field) != getattr(after_fd, field)
        or getattr(before, field) != getattr(after_path, field)
        for field in fields
    ):
        _fail("regular file changed while read: " + name)
    if digest.hexdigest() != expected_sha256:
        _fail("regular file hash changed: " + name)
    return _stat_identity("", before, "REGULAR_FILE"), b"".join(chunks)


def _read_selected_transport_manifest(
    plan: dict[str, object], *, durable: bool
) -> dict[str, object]:
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
        _fail("activation transport control fact changed")
    fact = candidates[0]
    count = fact.get("byte_count")
    digest = fact.get("sha256")
    if (
        type(count) is not int
        or not 0 < count <= _MAXIMUM_ENVELOPE_BYTES
        or type(digest) is not str
        or _HEX64.fullmatch(digest) is None
    ):
        _fail("activation transport control identity changed")
    roots: list[int] = []
    for key in ("preformal_scratch_root", "fixed_remote_root"):
        path = plan.get(key)
        if type(path) is not str:
            _fail("activation selected control root changed type")
        try:
            roots.append(_open_lexical_directory(path))
        except FileNotFoundError:
            continue
    if len(roots) != 1:
        for descriptor in roots:
            os.close(descriptor)
        _fail("activation selected transport root state changed")
    root_fd = roots[0]
    try:
        _identity, raw = _hash_regular_at(
            root_fd,
            "TRANSPORT_MANIFEST.json",
            expected_mode=0o400,
            expected_uid=REMOTE_UID,
            expected_gid=REMOTE_GID,
            expected_count=count,
            expected_sha256=digest,
            durable=durable,
        )
    finally:
        os.close(root_fd)
    document = _canonical_document(raw, "activation selected transport manifest")
    document = _verify_id(
        document,
        schema="acfqp.v42_remote_ordinal2_transport_manifest.v42r1",
        identity="transport_manifest_id",
        domain=_DOMAIN + "transport-manifest",
        label="activation selected transport manifest",
    )
    if document["transport_manifest_id"] != plan.get("transport_manifest_id"):
        _fail("activation selected transport manifest plan join changed")
    return document


def _verify_plan_program_transport_facts(
    plan: dict[str, object],
    *,
    artifact_keys: tuple[str, ...],
    observed_sha256: dict[str, str],
    durable: bool,
) -> None:
    transport = _read_selected_transport_manifest(plan, durable=durable)
    rows = transport.get("transport_facts")
    if type(rows) is not list:
        _fail("activation selected transport facts changed type")
    by_path = {
        row.get("relative_path"): row for row in rows if type(row) is dict
    }
    if len(by_path) != len(rows):
        _fail("activation selected transport facts contain duplicate paths")
    for key in artifact_keys:
        artifact = plan.get(key)
        if type(artifact) is not dict:
            _fail("activation program artifact changed type")
        row = by_path.get(artifact.get("relative_path"))
        if (
            type(row) is not dict
            or observed_sha256.get(key) != artifact.get("sha256")
            or row.get("sha256") != artifact.get("sha256")
            or row.get("byte_count") != artifact.get("byte_count")
            or row.get("git_blob_oid") != artifact.get("git_blob_oid")
            or row.get("git_mode") != artifact.get("git_mode")
            or row.get("git_object_type") != artifact.get("git_object_type")
            or row.get("git_mode") != "100644"
            or row.get("git_object_type") != "blob"
        ):
            _fail("activation program does not join exact transport fact")


def _observe_exact_five(
    plan: dict[str, object], *, durable: bool, require_selected_match: bool = True
) -> dict[str, object]:
    scratch_path = plan.get("preformal_scratch_root")
    parent_path = str(Path(str(scratch_path)).parent)
    if (
        type(scratch_path) is not str
        or parent_path != str(Path(str(plan.get("fixed_remote_root"))).parent)
        or parent_path != str(Path(str(plan.get("fixed_transport_ledger_root"))).parent)
    ):
        _fail("activation roots are not same-parent siblings")
    parent_fd = _open_lexical_directory(parent_path)
    try:
        scratch_name = Path(scratch_path).name
        stage_name = Path(str(plan.get("preformal_ledger_stage_root"))).name
        fixed_name = Path(str(plan.get("fixed_remote_root"))).name
        ledger_name = Path(str(plan.get("fixed_transport_ledger_root"))).name
        parent_stat = os.fstat(parent_fd)
        scratch_fd = os.open(
            scratch_name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        stage_fd = os.open(
            stage_name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        try:
            scratch_stat = os.fstat(scratch_fd)
            stage_stat = os.fstat(stage_fd)
            if (
                stat.S_IMODE(scratch_stat.st_mode) != 0o700
                or stat.S_IMODE(stage_stat.st_mode) != 0o700
                or scratch_stat.st_uid != REMOTE_UID
                or scratch_stat.st_gid != REMOTE_GID
                or stage_stat.st_uid != REMOTE_UID
                or stage_stat.st_gid != REMOTE_GID
                or sorted(os.listdir(scratch_fd)) != list(CONTROL_NAMES)
                or os.listdir(stage_fd) != []
            ):
                _fail("selected scratch or empty ledger-stage changed")
            for absent in (fixed_name, ledger_name):
                try:
                    os.stat(absent, dir_fd=parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                _fail("fixed activation target is not absent")
            facts = plan.get("control_facts")
            if type(facts) is not list:
                _fail("activation control facts changed type")
            controls: list[dict[str, object]] = []
            for fact in facts:
                if type(fact) is not dict:
                    _fail("activation control fact changed type")
                name = fact.get("name")
                if name not in CONTROL_NAMES:
                    _fail("activation control name changed")
                identity, _raw = _hash_regular_at(
                    scratch_fd,
                    str(name),
                    expected_mode=0o400,
                    expected_uid=REMOTE_UID,
                    expected_gid=REMOTE_GID,
                    expected_count=int(fact.get("byte_count")),
                    expected_sha256=str(fact.get("sha256")),
                    durable=durable,
                )
                identity["path"] = str(Path(scratch_path) / str(name))
                controls.append(
                    {
                        "name": name,
                        "identity": identity,
                        "sha256": fact["sha256"],
                        "byte_count": fact["byte_count"],
                    }
                )
            controls.sort(key=lambda row: str(row["name"]))
            if [row["name"] for row in controls] != list(CONTROL_NAMES):
                _fail("activation control inventory changed")
            if durable:
                os.fsync(scratch_fd)
                os.fsync(stage_fd)
            result = {
                "shared_parent_identity": _stat_identity(
                    parent_path, parent_stat, "DIRECTORY"
                ),
                "scratch_root_identity": _stat_identity(
                    scratch_path, scratch_stat, "DIRECTORY"
                ),
                "ledger_stage_identity": _stat_identity(
                    str(plan["preformal_ledger_stage_root"]),
                    stage_stat,
                    "DIRECTORY",
                ),
                "control_identities": controls,
                "scratch_inventory": list(CONTROL_NAMES),
                "ledger_stage_inventory": [],
                "fixed_remote_root_state": "ABSENT",
                "fixed_transport_ledger_state": "ABSENT",
                "all_paths_observed_nofollow_from_pinned_parent": True,
                "all_file_bytes_hashed_from_pinned_descriptors": True,
                "whole_tree_first_last_snapshot_equal": True,
            }
            if require_selected_match and result != plan.get("selected_remote_snapshot"):
                _fail("selected remote snapshot changed since resource probe")
            return result
        finally:
            os.close(scratch_fd)
            os.close(stage_fd)
    finally:
        os.close(parent_fd)


def _secure_write_once_at(directory_fd: int, name: str, raw: bytes) -> None:
    if "/" in name or name in {"", ".", ".."}:
        _fail("write-once name changed")
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
            _fail("write-once final storage changed")
    finally:
        os.close(descriptor)
    final = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if (final.st_dev, final.st_ino) != (observed.st_dev, observed.st_ino):
        _fail("write-once name changed after close")


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


def _verify_activation_envelope(
    envelope: dict[str, object],
    *,
    expected_plan_id: str,
    expected_local_attempt_id: str,
    verified_receiver_sha256: str,
    observed_remote_ingress_python_argv: list[str],
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object], bytes]:
    if set(envelope) != {
        "schema",
        "operation",
        "activation_plan",
        "local_activation_attempt",
        "network_start",
        "remote_activation_attempt",
        "service_source_utf8",
    } or envelope.get("schema") != "acfqp.v42_materialization_activation_ingress.v42r1":
        _fail("activation ingress envelope schema changed")
    if envelope.get("operation") != "ACTIVATE_SELECTED_COMPLETE_RECEIPT":
        _fail("activation ingress operation changed")
    plan = _verify_id(
        envelope.get("activation_plan"),
        schema=ACTIVATION_PLAN_SCHEMA,
        identity="materialization_activation_plan_id",
        domain=_DOMAIN + "materialization-activation-plan",
        label="activation plan",
    )
    local = _verify_id(
        envelope.get("local_activation_attempt"),
        schema=LOCAL_ATTEMPT_SCHEMA,
        identity="local_materialization_activation_attempt_id",
        domain=_DOMAIN + "local-materialization-activation-attempt",
        label="local activation attempt",
    )
    network = _verify_id(
        envelope.get("network_start"),
        schema=NETWORK_START_SCHEMA,
        identity="materialization_activation_network_start_id",
        domain=_DOMAIN + "materialization-activation-network-start",
        label="activation network start",
    )
    remote = _verify_id(
        envelope.get("remote_activation_attempt"),
        schema=REMOTE_ATTEMPT_SCHEMA,
        identity="remote_materialization_activation_attempt_id",
        domain=_DOMAIN + "remote-materialization-activation-attempt",
        label="remote activation attempt",
    )
    if (
        plan["materialization_activation_plan_id"] != expected_plan_id
        or local["local_materialization_activation_attempt_id"]
        != expected_local_attempt_id
        or local.get("materialization_activation_plan_id") != expected_plan_id
        or network.get("materialization_activation_plan_id") != expected_plan_id
        or network.get("local_materialization_activation_attempt_id")
        != expected_local_attempt_id
        or remote.get("materialization_activation_plan_id") != expected_plan_id
        or remote.get("local_materialization_activation_attempt_id")
        != expected_local_attempt_id
        or remote.get("materialization_activation_plan") != plan
        or remote.get("local_materialization_activation_attempt") != local
        or remote.get("materialization_activation_network_start") != network
        or remote.get("observed_remote_ingress_python_argv")
        != observed_remote_ingress_python_argv
    ):
        _fail("activation ingress document DAG changed")
    receiver = plan.get("activation_receiver_artifact")
    if type(receiver) is not dict or receiver.get("sha256") != verified_receiver_sha256:
        _fail("verified activation receiver does not join the plan")
    service_text = envelope.get("service_source_utf8")
    if type(service_text) is not str:
        _fail("activation service source changed type")
    service_raw = service_text.encode("utf-8", errors="strict")
    service = plan.get("activation_service_artifact")
    if (
        type(service) is not dict
        or service.get("byte_count") != len(service_raw)
        or service.get("sha256") != hashlib.sha256(service_raw).hexdigest()
    ):
        _fail("activation service bytes do not join the plan")
    _verify_plan_program_transport_facts(
        plan,
        artifact_keys=(
            "activation_receiver_artifact",
            "activation_service_artifact",
        ),
        observed_sha256={
            "activation_receiver_artifact": verified_receiver_sha256,
            "activation_service_artifact": hashlib.sha256(service_raw).hexdigest(),
        },
        durable=True,
    )
    return plan, local, network, remote, service_raw


def _open_verified_executable(executable_fact: dict[str, object]) -> tuple[int, os.stat_result]:
    path = executable_fact.get("path")
    if type(path) is not str or not path.startswith("/"):
        _fail("systemd executable path changed")
    before = os.lstat(path)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != executable_fact.get("mode")
        or before.st_uid != executable_fact.get("uid")
        or before.st_gid != executable_fact.get("gid")
        or before.st_nlink != executable_fact.get("st_nlink")
        or before.st_size != executable_fact.get("byte_count")
    ):
        _fail("systemd executable metadata changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("systemd executable changed before open")
        digest = hashlib.sha256()
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(descriptor, min(1024 * 1024, before.st_size - offset), offset)
            if not chunk:
                _fail("systemd executable ended early")
            digest.update(chunk)
            offset += len(chunk)
        if digest.hexdigest() != executable_fact.get("sha256"):
            _fail("systemd executable hash changed")
        after = os.fstat(descriptor)
        final = os.lstat(path)
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
            _fail("systemd executable changed while verified")
        return descriptor, before
    except BaseException:
        os.close(descriptor)
        raise


def _verify_executable_path_still_matches(
    descriptor: int, before: os.stat_result, path: str
) -> None:
    held = os.fstat(descriptor)
    final = os.lstat(path)
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
        getattr(before, field) != getattr(held, field)
        or getattr(before, field) != getattr(final, field)
        for field in fields
    ):
        _fail("systemd executable path changed around effect")


def _bounded_waitpid(pid: int, timeout_seconds: float) -> int:
    if type(pid) is not int or pid <= 1 or not 0.0 < timeout_seconds <= 300.0:
        _fail("bounded systemd child wait contract changed")
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            observed, status = os.waitpid(pid, os.WNOHANG)
        except InterruptedError:
            continue
        if observed == pid:
            return status
        if time.monotonic() >= deadline:
            break
        time.sleep(0.01)
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as error:
        if error.errno != errno.ESRCH:
            raise
    grace = time.monotonic() + _SYSTEMD_RUN_TERM_GRACE_SECONDS
    while True:
        try:
            observed, status = os.waitpid(pid, os.WNOHANG)
        except InterruptedError:
            continue
        except ChildProcessError:
            _fail("bounded systemd child disappeared before reap")
        if observed == pid:
            return status
        if time.monotonic() >= grace:
            break
        time.sleep(0.01)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError as error:
        if error.errno != errno.ESRCH:
            raise
    while True:
        try:
            _observed, status = os.waitpid(pid, 0)
            return status
        except InterruptedError:
            continue
        except ChildProcessError:
            _fail("bounded systemd child disappeared before final reap")


def _default_systemd_runner(
    argv: list[str], environment: dict[str, str], executable_fact: dict[str, object]
) -> int:
    executable_fd, executable_stat = _open_verified_executable(executable_fact)
    try:
        pid = os.fork()
        if pid == 0:
            try:
                null_fd = os.open("/dev/null", os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
                for target in (0, 1, 2):
                    os.dup2(null_fd, target, inheritable=True)
                staged = fcntl.fcntl(executable_fd, fcntl.F_DUPFD_CLOEXEC, 3)
                if staged != 3:
                    os.dup2(staged, 3, inheritable=False)
                    os.close(staged)
                for token in os.listdir("/proc/self/fd"):
                    descriptor = int(token)
                    if descriptor not in (0, 1, 2, 3):
                        try:
                            os.close(descriptor)
                        except OSError:
                            pass
                os.execve("/proc/self/fd/3", argv, environment)
            except BaseException:
                os._exit(127)
        status = _bounded_waitpid(pid, _SYSTEMD_RUN_TIMEOUT_SECONDS)
        _verify_executable_path_still_matches(
            executable_fd, executable_stat, str(executable_fact["path"])
        )
        return os.waitstatus_to_exitcode(status)
    finally:
        os.close(executable_fd)


def activate_selected_receipt_v42r1(
    *,
    envelope: dict[str, object],
    expected_plan_id: str,
    expected_local_attempt_id: str,
    verified_receiver_sha256: str,
    observed_remote_ingress_python_argv: list[str],
    systemd_runner: Callable[
        [list[str], dict[str, str], dict[str, object]], int
    ] = _default_systemd_runner,
    fault_hook: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Perform the one remote activation cut; never retry it."""

    def cut(name: str) -> None:
        if fault_hook is not None:
            fault_hook(name)

    plan, _local, _network, remote, service_raw = _verify_activation_envelope(
        envelope,
        expected_plan_id=expected_plan_id,
        expected_local_attempt_id=expected_local_attempt_id,
        verified_receiver_sha256=verified_receiver_sha256,
        observed_remote_ingress_python_argv=observed_remote_ingress_python_argv,
    )
    _observe_exact_five(plan, durable=True)
    parent_path = str(Path(str(plan["fixed_remote_root"])).parent)
    parent_fd = _open_lexical_directory(parent_path)
    stage_name = Path(str(plan["preformal_ledger_stage_root"])).name
    ledger_name = Path(str(plan["fixed_transport_ledger_root"])).name
    try:
        stage_fd = os.open(
            stage_name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        try:
            if os.listdir(stage_fd):
                _fail("ledger stage was not empty at activation cut")
            cut("BEFORE_REMOTE_ATTEMPT_WRITE")
            remote_raw = _canonical_bytes(remote)
            _secure_write_once_at(stage_fd, REMOTE_ATTEMPT_NAME, remote_raw)
            cut("AFTER_REMOTE_ATTEMPT_FSYNC")
            _secure_write_once_at(stage_fd, SERVICE_SOURCE_NAME, service_raw)
            cut("AFTER_SERVICE_SOURCE_FSYNC")
            if sorted(os.listdir(stage_fd)) != sorted(
                (REMOTE_ATTEMPT_NAME, SERVICE_SOURCE_NAME)
            ):
                _fail("ledger stage inventory changed before publish")
            os.fsync(stage_fd)
        finally:
            os.close(stage_fd)
        cut("BEFORE_LEDGER_RENAME")
        _rename_noreplace_at(parent_fd, stage_name, ledger_name)
        cut("AFTER_LEDGER_RENAME_BEFORE_PARENT_FSYNC")
        os.fsync(parent_fd)
        cut("AFTER_LEDGER_PARENT_FSYNC")
    finally:
        os.close(parent_fd)
    systemd_contract = plan.get("systemd_service_contract")
    if type(systemd_contract) is not dict:
        _fail("activation systemd contract changed type")
    argv = systemd_contract.get("authorized_systemd_run_argv_template")
    environment = systemd_contract.get("client_environment")
    if type(argv) is not list or type(environment) is not dict:
        _fail("activation systemd invocation changed type")
    argv = [
        str(item)
        .replace(
            "{acfqp_v42_materialization_activation_plan_id}", expected_plan_id
        )
        .replace(
            "{acfqp_v42_remote_materialization_activation_attempt_id}",
            str(remote["remote_materialization_activation_attempt_id"]),
        )
        for item in argv
    ]
    if {"--wait", "--pipe", "--pty", "--scope", "--collect"}.intersection(argv):
        _fail("activation systemd invocation admitted a forbidden option")
    cut("BEFORE_SYSTEMD_RUN")
    executable_fact = systemd_contract.get("systemd_run")
    if type(executable_fact) is not dict:
        _fail("systemd-run executable fact changed type")
    returncode = systemd_runner(
        argv,
        {str(k): str(v) for k, v in environment.items()},
        executable_fact,
    )
    cut("AFTER_SYSTEMD_RUN")
    # Nonzero, disconnect, or unreadable completion is ambiguous.  A caller
    # may only classify the append-only ledger; this function never retries.
    return {
        "schema": "acfqp.v42_remote_ordinal2_activation_ingress_result.v42r1",
        "materialization_activation_plan_id": expected_plan_id,
        "remote_materialization_activation_attempt_id": remote[
            "remote_materialization_activation_attempt_id"
        ],
        "systemd_run_returncode": returncode,
        "systemd_effect_may_have_occurred": True,
        "same_activation_identity_retry_forbidden": True,
        "read_only_followup_only": True,
    }


def _path_state_at(parent_fd: int, name: str) -> tuple[str, list[str]]:
    try:
        observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return "ABSENT", []
    if not stat.S_ISDIR(observed.st_mode):
        return "NONREGULAR", []
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=parent_fd,
    )
    try:
        names = sorted(os.listdir(descriptor))
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if (observed.st_dev, observed.st_ino, observed.st_mode) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
    ) or (observed.st_dev, observed.st_ino, observed.st_mode) != (
        final.st_dev,
        final.st_ino,
        final.st_mode,
    ):
        _fail("activation path changed during read-only observation")
    return "EXACT_DIRECTORY", names


def _materialize_systemd_template(
    template: object,
    *,
    plan_id: str,
    remote_attempt_id: str | None = None,
    invocation_id: str | None = None,
    control_group: str | None = None,
) -> list[str]:
    if type(template) is not list or any(type(item) is not str for item in template):
        _fail("systemd argv template changed")
    result: list[str] = []
    for item in template:
        value = item.replace(
            "{acfqp_v42_materialization_activation_plan_id}", plan_id
        )
        if remote_attempt_id is not None:
            value = value.replace(
                "{acfqp_v42_remote_materialization_activation_attempt_id}",
                remote_attempt_id,
            )
        if invocation_id is not None:
            value = value.replace(
                "{acfqp_v42_systemd_invocation_id}", invocation_id
            )
        if control_group is not None:
            value = value.replace(
                "{acfqp_v42_systemd_control_group}", control_group
            )
        result.append(value)
    if any("{acfqp_v42_" in item for item in result):
        _fail("systemd argv replacement was incomplete")
    return result


def _run_pinned_read_only_tool(
    argv: list[str], environment: dict[str, str], executable_fact: dict[str, object]
) -> tuple[int, bytes, bytes]:
    descriptor, before = _open_verified_executable(executable_fact)
    try:
        process = subprocess.Popen(
            argv,
            executable=f"/proc/self/fd/{descriptor}",
            env=environment,
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
            label="read-only systemctl query",
        )
        _verify_executable_path_still_matches(
            descriptor, before, str(executable_fact["path"])
        )
    finally:
        os.close(descriptor)
    if len(stdout) > 256 * 1024 or len(stderr) > 64 * 1024:
        _fail("read-only systemctl query exceeded cap")
    return process.returncode, stdout, stderr


def _terminate_child_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        _fail("bounded child could not be reaped")


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
        or not 0 < stdout_cap <= _MAXIMUM_OUTPUT_BYTES
        or not 0 < stderr_cap <= _MAXIMUM_OUTPUT_BYTES
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
            events = selector.select(min(remaining, 0.1))
            for key, _mask in events:
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


def _parse_systemctl_show(raw: bytes) -> dict[str, str]:
    if not raw.endswith(b"\n") or b"\0" in raw:
        _fail("systemctl show output changed framing")
    try:
        lines = raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as error:
        raise _ActivationReceiverFailure("systemctl show is not UTF-8") from error
    result: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            _fail("systemctl show line changed")
        key, value = line.split("=", 1)
        if key in result:
            _fail("systemctl show duplicated a property")
        result[key] = value
    expected = {
        "Id", "LoadState", "ActiveState", "SubState", "FragmentPath",
        "MainPID", "InvocationID", "ControlGroup", "Type", "StandardInput",
        "StandardOutput", "StandardError", "Restart", "UMask", "KillMode",
        "RuntimeMaxUSec", "WorkingDirectory", "Slice",
    }
    if set(result) != expected:
        _fail("systemctl show property keyset changed")
    return result


def _remote_attempt_id_read_only(plan: dict[str, object]) -> str | None:
    try:
        ledger_fd = _open_lexical_directory(str(plan["fixed_transport_ledger_root"]))
    except (FileNotFoundError, OSError, _ActivationReceiverFailure):
        return None
    try:
        before = os.stat(REMOTE_ATTEMPT_NAME, dir_fd=ledger_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o400
            or before.st_uid != REMOTE_UID
            or before.st_gid != REMOTE_GID
            or before.st_nlink != 1
            or not 0 < before.st_size <= _MAXIMUM_ENVELOPE_BYTES
        ):
            return None
        descriptor = os.open(
            REMOTE_ATTEMPT_NAME,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=ledger_fd,
        )
        try:
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                return None
            raw = b""
            while len(raw) < before.st_size:
                chunk = os.read(descriptor, before.st_size - len(raw))
                if not chunk:
                    return None
                raw += chunk
            after_fd = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after_path = os.stat(
            REMOTE_ATTEMPT_NAME, dir_fd=ledger_fd, follow_symlinks=False
        )
        fields = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
        if any(
            getattr(before, field) != getattr(after_fd, field)
            or getattr(before, field) != getattr(after_path, field)
            for field in fields
        ):
            return None
        document = _canonical_document(raw, "remote activation attempt")
        verified = _verify_id(
            document,
            schema=REMOTE_ATTEMPT_SCHEMA,
            identity="remote_materialization_activation_attempt_id",
            domain=_DOMAIN + "remote-materialization-activation-attempt",
            label="remote activation attempt",
        )
        if verified.get("materialization_activation_plan_id") != plan.get(
            "materialization_activation_plan_id"
        ):
            return None
        return str(verified["remote_materialization_activation_attempt_id"])
    except (FileNotFoundError, OSError, _ActivationReceiverFailure):
        return None
    finally:
        os.close(ledger_fd)


def _stable_process_argv(pid: int) -> list[str] | None:
    if type(pid) is not int or pid <= 1:
        return None
    path = f"/proc/{pid}/cmdline"
    try:
        before = os.lstat(path)
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            raw = b""
            while len(raw) <= 2 * 1024 * 1024:
                chunk = os.read(descriptor, 64 * 1024)
                if not chunk:
                    break
                raw += chunk
            after_fd = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after_path = os.lstat(path)
    except (FileNotFoundError, ProcessLookupError, OSError):
        return None
    if (
        len(raw) > 2 * 1024 * 1024
        or not raw.endswith(b"\0")
        or (before.st_dev, before.st_ino) != (after_fd.st_dev, after_fd.st_ino)
        or (before.st_dev, before.st_ino) != (after_path.st_dev, after_path.st_ino)
    ):
        return None
    try:
        return [part.decode("utf-8", errors="strict") for part in raw[:-1].split(b"\0")]
    except UnicodeError:
        return None


def _observe_unit_read_only(plan: dict[str, object]) -> tuple[str, bool]:
    contract = plan.get("systemd_service_contract")
    if type(contract) is not dict:
        return "UNOBSERVABLE", False
    plan_id = str(plan.get("materialization_activation_plan_id"))
    unit = "acfqp-v42-o2-activation-" + plan_id + ".service"
    try:
        argv = _materialize_systemd_template(
            contract.get("authorized_systemctl_show_argv_template"),
            plan_id=plan_id,
        )
        returncode, stdout, stderr = _run_pinned_read_only_tool(
            argv,
            {str(key): str(value) for key, value in contract["client_environment"].items()},
            contract["systemctl"],
        )
        if stderr:
            return "UNOBSERVABLE", False
        properties = _parse_systemctl_show(stdout)
    except (OSError, _ActivationReceiverFailure, KeyError, TypeError):
        return "UNOBSERVABLE", False
    if properties["LoadState"] == "not-found":
        return "NOT_FOUND", False
    if returncode != 0:
        return "UNOBSERVABLE", False
    if properties["ActiveState"] == "failed" or properties["SubState"] == "failed":
        state = "FAILED"
    elif properties["ActiveState"] == "activating":
        state = "ACTIVATING"
    elif properties["ActiveState"] == "active":
        state = "ACTIVE"
    elif properties["ActiveState"] == "inactive":
        state = "INACTIVE"
    else:
        state = "UNOBSERVABLE"
    try:
        main_pid = int(properties["MainPID"])
    except ValueError:
        return state, False
    remote_attempt_id = _remote_attempt_id_read_only(plan)
    expected_clean: list[str] | None = None
    if remote_attempt_id is not None:
        expected_clean = _materialize_systemd_template(
            contract.get("authorized_service_worker_argv_template"),
            plan_id=plan_id,
            remote_attempt_id=remote_attempt_id,
            invocation_id=properties["InvocationID"],
            control_group=properties["ControlGroup"],
        )
    exact = (
        properties["Id"] == unit
        and properties["LoadState"] == "loaded"
        and properties["Type"] == "exec"
        and properties["Restart"] == "no"
        and properties["UMask"] == "0077"
        and properties["KillMode"] == "control-group"
        and properties["RuntimeMaxUSec"] == "1w"
        and properties["StandardInput"] == "null"
        and properties["StandardOutput"] == "null"
        and properties["StandardError"] == "null"
        and properties["WorkingDirectory"]
        == str(Path(str(plan["fixed_remote_root"])).parent)
        and properties["Slice"] == "app.slice"
        and properties["FragmentPath"]
        == f"/run/user/{REMOTE_UID}/systemd/transient/{unit}"
        and main_pid > 1
        and _HEX64.fullmatch(plan_id) is not None
        and re.fullmatch(r"[0-9a-f]{32}", properties["InvocationID"]) is not None
        and properties["ControlGroup"].endswith("/app.slice/" + unit)
        and expected_clean is not None
        and _stable_process_argv(main_pid) == expected_clean
    )
    return state, exact


def observe_activation_state_read_only_v42r1(plan: dict[str, object]) -> dict[str, object]:
    parent_path = str(Path(str(plan.get("fixed_remote_root"))).parent)
    parent_fd = _open_lexical_directory(parent_path)
    try:
        scratch_state, _scratch_names = _path_state_at(
            parent_fd, Path(str(plan["preformal_scratch_root"])).name
        )
        stage_state, _stage_names = _path_state_at(
            parent_fd, Path(str(plan["preformal_ledger_stage_root"])).name
        )
        root_state, _root_names = _path_state_at(
            parent_fd, Path(str(plan["fixed_remote_root"])).name
        )
        ledger_state, ledger_names = _path_state_at(
            parent_fd, Path(str(plan["fixed_transport_ledger_root"])).name
        )
    finally:
        os.close(parent_fd)
    unit_state, unit_exact = _observe_unit_read_only(plan)
    return {
        "fixed_remote_root_state": root_state,
        "preformal_scratch_root_state": scratch_state,
        "preformal_ledger_stage_state": stage_state,
        "fixed_transport_ledger_state": ledger_state,
        "fixed_transport_ledger_inventory": ledger_names,
        "systemd_unit_state": unit_state,
        "systemd_unit_properties_exact": unit_exact,
        "all_paths_observed_nofollow": True,
        "whole_tree_first_last_snapshot_equal": True,
    }


def _read_meminfo() -> dict[str, int]:
    with open("/proc/meminfo", "rb", buffering=0) as stream:
        raw = stream.read(1024 * 1024)
    values: dict[str, int] = {}
    for line in raw.decode("ascii").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] == "kB" and fields[0].endswith(":"):
            values[fields[0][:-1]] = int(fields[1]) * 1024
    if any(name not in values for name in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree")):
        _fail("resource probe meminfo changed")
    return values


def observe_resources_read_only_v42r1(parent_path: str) -> dict[str, object]:
    """Read only host resources; does not create a plan or consume identity."""

    parent_fd = _open_lexical_directory(parent_path)
    try:
        filesystem = os.fstatvfs(parent_fd)
    finally:
        os.close(parent_fd)
    meminfo = _read_meminfo()
    # The precise cgroup ancestry is independently verified by the pure
    # authority.  The stdlib ingress returns an exact raw projection; on hosts
    # whose root view omits memory files, use the registered delegated-root row.
    with open("/proc/self/cgroup", "rb", buffering=0) as stream:
        cgroup_raw = stream.read(4096)
    if not cgroup_raw.startswith(b"0::") or not cgroup_raw.endswith(b"\n"):
        _fail("resource probe cgroup scope changed")
    scope = cgroup_raw[3:-1].decode("ascii")
    rows: list[dict[str, object]] = []
    current = Path(scope)
    while True:
        relative = str(current).lstrip("/")
        directory = Path("/sys/fs/cgroup") / relative
        maximum = directory / "memory.max"
        usage = directory / "memory.current"
        if maximum.exists() and usage.exists():
            maximum_raw = maximum.read_bytes()
            usage_raw = usage.read_bytes()
            rows.append(
                {
                    "cgroup_path": str(current),
                    "memory_max_mode": "MAX" if maximum_raw == b"max\n" else "FINITE",
                    "memory_max_bytes": (
                        None if maximum_raw == b"max\n" else int(maximum_raw)
                    ),
                    "memory_current_bytes": int(usage_raw),
                }
            )
        elif current == Path("/"):
            rows.append(
                {
                    "cgroup_path": "/",
                    "memory_max_mode": "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES",
                    "memory_max_bytes": None,
                    "memory_current_bytes": None,
                }
            )
        else:
            _fail("resource probe cgroup ancestry is incomplete")
        if current == Path("/"):
            break
        current = current.parent
    return {
        "observed_hostname": socket.gethostname(),
        "observed_user": pwd.getpwuid(os.geteuid()).pw_name,
        "observed_uid": os.geteuid(),
        "observed_gid": os.getegid(),
        "memory_total_bytes": meminfo["MemTotal"],
        "memory_available_bytes": meminfo["MemAvailable"],
        "swap_total_bytes": meminfo["SwapTotal"],
        "swap_free_bytes": meminfo["SwapFree"],
        "filesystem_available_bytes": filesystem.f_bavail * filesystem.f_frsize,
        "cgroup_memory_ancestry": rows,
        "remote_mutation_performed": False,
        "only_current_ssh_ingress_process_started": True,
        "additional_or_durable_remote_process_started": False,
    }


def _observe_python_projection(resource_plan: dict[str, object]) -> dict[str, object]:
    contract = resource_plan.get("remote_startup_tcb_contract")
    if type(contract) is not dict:
        _fail("resource probe startup TCB changed type")
    fields = (
        "python_invocation_path",
        "python_invocation_node_type",
        "python_invocation_link_target",
        "python_invocation_mode",
        "python_invocation_uid",
        "python_invocation_gid",
        "python_invocation_nlink",
        "python_realpath",
        "python_realpath_node_type",
        "python_realpath_mode",
        "python_realpath_uid",
        "python_realpath_gid",
        "python_realpath_nlink",
        "python_realpath_sha256",
        "python_realpath_byte_count",
        "python_version",
        "python_isolated_flag",
        "python_no_site_flag",
        "python_dont_write_bytecode",
    )
    if any(field not in contract for field in fields):
        _fail("resource probe Python contract omitted a field")
    expected = {field: contract[field] for field in fields}
    invocation_path = str(expected["python_invocation_path"])
    invocation = os.lstat(invocation_path)
    if (
        not stat.S_ISLNK(invocation.st_mode)
        or os.readlink(invocation_path) != expected["python_invocation_link_target"]
        or stat.S_IMODE(invocation.st_mode) != expected["python_invocation_mode"]
        or invocation.st_uid != expected["python_invocation_uid"]
        or invocation.st_gid != expected["python_invocation_gid"]
        or invocation.st_nlink != expected["python_invocation_nlink"]
    ):
        _fail("resource probe Python invocation changed")
    real_fact = {
        "path": expected["python_realpath"],
        "mode": expected["python_realpath_mode"],
        "uid": expected["python_realpath_uid"],
        "gid": expected["python_realpath_gid"],
        "st_nlink": expected["python_realpath_nlink"],
        "byte_count": expected["python_realpath_byte_count"],
        "sha256": expected["python_realpath_sha256"],
    }
    descriptor, before = _open_verified_executable(real_fact)
    try:
        _verify_executable_path_still_matches(
            descriptor, before, str(real_fact["path"])
        )
    finally:
        os.close(descriptor)
    if (
        sys.executable != invocation_path
        or os.path.realpath(sys.executable) != expected["python_realpath"]
        or list(sys.version_info[:3]) != expected["python_version"]
        or sys.flags.isolated != expected["python_isolated_flag"]
        or sys.flags.no_site != expected["python_no_site_flag"]
        or sys.dont_write_bytecode is not expected["python_dont_write_bytecode"]
    ):
        _fail("resource probe live Python runtime changed")
    return expected


def _verify_resource_probe_envelope(
    envelope: dict[str, object],
    *,
    expected_plan_id: str,
    expected_receipt_id: str,
    verified_receiver_sha256: str,
    observed_remote_ingress_python_argv: list[str],
) -> tuple[dict[str, object], dict[str, object]]:
    if set(envelope) != {
        "schema",
        "operation",
        "resource_plan",
        "preformal_receipt",
    } or envelope.get("schema") != "acfqp.v42_preactivation_resource_probe_ingress.v42r1":
        _fail("resource probe ingress envelope schema changed")
    if envelope.get("operation") != "READ_ONLY_PREACTIVATION_RESOURCE_PROBE":
        _fail("resource probe operation changed")
    plan = _verify_id(
        envelope.get("resource_plan"),
        schema=RESOURCE_PLAN_SCHEMA,
        identity="preactivation_resource_probe_plan_id",
        domain=_DOMAIN + "preactivation-resource-probe-plan",
        label="resource probe plan",
    )
    receipt = envelope.get("preformal_receipt")
    if type(receipt) is not dict:
        _fail("resource probe receipt changed type")
    if (
        plan["preactivation_resource_probe_plan_id"] != expected_plan_id
        or plan.get("preformal_upload_receipt_id") != expected_receipt_id
        or receipt.get("preformal_upload_receipt_id") != expected_receipt_id
        or plan.get("activation_receiver_artifact", {}).get("sha256")
        != verified_receiver_sha256
    ):
        _fail("resource probe plan/receipt/receiver join changed")
    _verify_plan_program_transport_facts(
        plan,
        artifact_keys=("activation_receiver_artifact",),
        observed_sha256={"activation_receiver_artifact": verified_receiver_sha256},
        durable=False,
    )
    template = plan.get("authorized_resource_probe_remote_python_argv_template")
    if type(template) is not list:
        _fail("resource probe remote argv template changed")
    expected_argv = [
        str(item).replace(
            "{acfqp_v42_preactivation_resource_probe_plan_id}", expected_plan_id
        )
        for item in template
    ]
    if observed_remote_ingress_python_argv != expected_argv:
        _fail("resource probe remote Python argv changed")
    return plan, dict(receipt)


def run_resource_probe_v42r1(
    *,
    envelope: dict[str, object],
    expected_plan_id: str,
    expected_receipt_id: str,
    verified_receiver_sha256: str,
    observed_remote_ingress_python_argv: list[str],
) -> dict[str, object]:
    plan, _receipt = _verify_resource_probe_envelope(
        envelope,
        expected_plan_id=expected_plan_id,
        expected_receipt_id=expected_receipt_id,
        verified_receiver_sha256=verified_receiver_sha256,
        observed_remote_ingress_python_argv=observed_remote_ingress_python_argv,
    )
    snapshot = _observe_exact_five(
        plan, durable=False, require_selected_match=False
    )
    resources = observe_resources_read_only_v42r1(
        str(Path(str(plan["fixed_remote_root"])).parent)
    )
    return {
        "schema": "acfqp.v42_remote_ordinal2_preactivation_resource_probe_observation.v42r1",
        "preactivation_resource_probe_plan_id": expected_plan_id,
        "preformal_upload_receipt_id": expected_receipt_id,
        **resources,
        "observed_python": _observe_python_projection(plan),
        "selected_remote_snapshot": snapshot,
        "resource_observation_stage": "READ_ONLY_PREACTIVATION_PROBE",
        "exact_live_file_descriptors": [0, 1, 2],
        "stdin_stdout_stderr_not_tty": True,
        "remote_mutation_performed": False,
        "fixed_root_effect_performed": False,
        "systemd_effect_performed": False,
        "trusted_bootstrap_effect_performed": False,
        "only_current_ssh_ingress_process_started": True,
        "additional_or_durable_remote_process_started": False,
        "read_only_observation_completed": True,
    }


def _verify_classification_envelope(
    envelope: dict[str, object],
    *,
    expected_plan_id: str,
    expected_local_attempt_id: str,
    verified_receiver_sha256: str,
    observed_remote_ingress_python_argv: list[str],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    if set(envelope) != {
        "schema", "operation", "activation_plan", "local_activation_attempt",
        "network_start",
    } or envelope.get("schema") != "acfqp.v42_materialization_activation_classify_ingress.v42r1":
        _fail("activation classifier ingress schema changed")
    if envelope.get("operation") != "READ_ONLY_CLASSIFY_ACTIVATION":
        _fail("activation classifier operation changed")
    plan = _verify_id(
        envelope.get("activation_plan"),
        schema=ACTIVATION_PLAN_SCHEMA,
        identity="materialization_activation_plan_id",
        domain=_DOMAIN + "materialization-activation-plan",
        label="activation plan",
    )
    local = _verify_id(
        envelope.get("local_activation_attempt"),
        schema=LOCAL_ATTEMPT_SCHEMA,
        identity="local_materialization_activation_attempt_id",
        domain=_DOMAIN + "local-materialization-activation-attempt",
        label="local activation attempt",
    )
    network = _verify_id(
        envelope.get("network_start"),
        schema=NETWORK_START_SCHEMA,
        identity="materialization_activation_network_start_id",
        domain=_DOMAIN + "materialization-activation-network-start",
        label="activation network start",
    )
    receiver = plan.get("activation_receiver_artifact")
    template = plan.get("authorized_read_only_classifier_remote_python_argv_template")
    if type(template) is not list:
        _fail("activation classifier argv template changed")
    expected_argv = [
        str(item)
        .replace("{acfqp_v42_materialization_activation_plan_id}", expected_plan_id)
        .replace(
            "{acfqp_v42_local_materialization_activation_attempt_id}",
            expected_local_attempt_id,
        )
        for item in template
    ]
    if (
        plan["materialization_activation_plan_id"] != expected_plan_id
        or local["local_materialization_activation_attempt_id"]
        != expected_local_attempt_id
        or local.get("materialization_activation_plan_id") != expected_plan_id
        or network.get("materialization_activation_plan_id") != expected_plan_id
        or network.get("local_materialization_activation_attempt_id")
        != expected_local_attempt_id
        or type(receiver) is not dict
        or receiver.get("sha256") != verified_receiver_sha256
        or observed_remote_ingress_python_argv != expected_argv
    ):
        _fail("activation classifier DAG or argv changed")
    _verify_plan_program_transport_facts(
        plan,
        artifact_keys=("activation_receiver_artifact",),
        observed_sha256={"activation_receiver_artifact": verified_receiver_sha256},
        durable=False,
    )
    return plan, local, network


def _read_optional_ledger_documents(
    plan: dict[str, object], observation: dict[str, object]
) -> dict[str, object | None]:
    result: dict[str, object | None] = {
        "remote_attempt": None,
        "service_receipt": None,
        "publish_ready": None,
        "terminal": None,
        "failure": None,
    }
    if observation["fixed_transport_ledger_state"] != "EXACT_DIRECTORY":
        return result
    known = {
        REMOTE_ATTEMPT_NAME: "remote_attempt",
        SERVICE_RECEIPT_NAME: "service_receipt",
        READY_NAME: "publish_ready",
        TERMINAL_NAME: "terminal",
        FAILURE_NAME: "failure",
    }
    names = observation["fixed_transport_ledger_inventory"]
    if any(name not in {*known, SERVICE_SOURCE_NAME} for name in names):
        return result
    ledger_fd = _open_lexical_directory(str(plan["fixed_transport_ledger_root"]))
    try:
        before_names = sorted(os.listdir(ledger_fd))
        for name, key in known.items():
            if name not in before_names:
                continue
            before = os.stat(name, dir_fd=ledger_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != REMOTE_UID
                or before.st_gid != REMOTE_GID
                or before.st_nlink != 1
                or not 0 < before.st_size <= _MAXIMUM_ENVELOPE_BYTES
            ):
                _fail("activation classifier ledger file storage changed")
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=ledger_fd,
            )
            try:
                opened = os.fstat(descriptor)
                if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                    _fail("activation classifier ledger file changed before open")
                chunks: list[bytes] = []
                remaining = before.st_size
                while remaining:
                    chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                    if not chunk:
                        _fail("activation classifier ledger file ended early")
                    chunks.append(chunk)
                    remaining -= len(chunk)
                after_fd = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            after_path = os.stat(name, dir_fd=ledger_fd, follow_symlinks=False)
            fields = (
                "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
                "st_size", "st_mtime_ns", "st_ctime_ns",
            )
            if any(
                getattr(before, field) != getattr(after_fd, field)
                or getattr(before, field) != getattr(after_path, field)
                for field in fields
            ):
                _fail("activation classifier ledger file changed while read")
            result[key] = _canonical_document(b"".join(chunks), name)
        if sorted(os.listdir(ledger_fd)) != before_names:
            _fail("activation classifier ledger inventory changed while read")
    finally:
        os.close(ledger_fd)
    return result


def _read_optional_fixed_root_documents(
    plan: dict[str, object], observation: dict[str, object]
) -> dict[str, object]:
    known = (
        "EXECUTION_SOURCE_MANIFEST.json",
        "LOCAL_MATERIALIZATION_ATTEMPT.json",
        "TRANSPORT_MANIFEST.json",
        BOOTSTRAP_REMOTE_ATTEMPT_NAME,
        BOOTSTRAP_MATERIALIZATION_TERMINAL_NAME,
        BOOTSTRAP_MATERIALIZATION_FAILURE_NAME,
    )
    if observation["fixed_remote_root_state"] != "EXACT_DIRECTORY":
        return {
            "inventory_before": [],
            "inventory_after": [],
            "documents": {},
            "collected_subset_only_not_whole_tree": True,
        }
    root_fd = _open_lexical_directory(str(plan["fixed_remote_root"]))
    try:
        before_root = os.fstat(root_fd)
        before_names = sorted(os.listdir(root_fd))
        documents: dict[str, object] = {}
        for name in known:
            if name not in before_names:
                continue
            before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != REMOTE_UID
                or before.st_gid != REMOTE_GID
                or before.st_nlink != 1
                or not 0 < before.st_size <= _MAXIMUM_ENVELOPE_BYTES
            ):
                _fail("fixed-root evidence document storage changed")
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=root_fd,
            )
            try:
                opened = os.fstat(descriptor)
                if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                    _fail("fixed-root evidence document changed before open")
                chunks: list[bytes] = []
                remaining = before.st_size
                while remaining:
                    chunk = os.read(descriptor, min(1024 * 1024, remaining))
                    if not chunk:
                        _fail("fixed-root evidence document ended early")
                    chunks.append(chunk)
                    remaining -= len(chunk)
                if os.read(descriptor, 1):
                    _fail("fixed-root evidence document grew while read")
                after_fd = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            after_path = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            fields = (
                "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
                "st_size", "st_mtime_ns", "st_ctime_ns",
            )
            if any(
                getattr(before, field) != getattr(after_fd, field)
                or getattr(before, field) != getattr(after_path, field)
                for field in fields
            ):
                _fail("fixed-root evidence document changed while read")
            documents[name] = _canonical_document(b"".join(chunks), name)
        after_names = sorted(os.listdir(root_fd))
        after_root = os.fstat(root_fd)
    finally:
        os.close(root_fd)
    root_fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        before_names != after_names
        or not stat.S_ISDIR(after_root.st_mode)
        or any(
            getattr(before_root, field) != getattr(after_root, field)
            for field in root_fields
        )
    ):
        _fail("fixed-root inventory changed during evidence read")
    return {
        "inventory_before": before_names,
        "inventory_after": after_names,
        "documents": documents,
        "collected_subset_only_not_whole_tree": True,
    }


def run_read_only_classification_v42r1(
    *,
    envelope: dict[str, object],
    expected_plan_id: str,
    expected_local_attempt_id: str,
    verified_receiver_sha256: str,
    observed_remote_ingress_python_argv: list[str],
) -> dict[str, object]:
    plan, _local, _network = _verify_classification_envelope(
        envelope,
        expected_plan_id=expected_plan_id,
        expected_local_attempt_id=expected_local_attempt_id,
        verified_receiver_sha256=verified_receiver_sha256,
        observed_remote_ingress_python_argv=observed_remote_ingress_python_argv,
    )
    before = observe_activation_state_read_only_v42r1(plan)
    documents = _read_optional_ledger_documents(plan, before)
    fixed_root_evidence = _read_optional_fixed_root_documents(plan, before)
    after = observe_activation_state_read_only_v42r1(plan)
    return {
        "schema": "acfqp.v42_remote_ordinal2_materialization_activation_read_only_observation.v42r1",
        "materialization_activation_plan_id": expected_plan_id,
        "local_materialization_activation_attempt_id": expected_local_attempt_id,
        "observation_before": before,
        "observation_after": after,
        "remote_documents": documents,
        "fixed_root_evidence": fixed_root_evidence,
        "remote_mutation_performed": False,
        "only_read_only_ssh_ingress_and_systemctl_query_processes_started": True,
        "additional_durable_or_mutating_remote_process_started": False,
        "activation_retry_authorized": False,
    }


def main_v42r1(
    *,
    expected_plan_id: str,
    expected_local_attempt_id: str,
    verified_envelope_raw: bytes,
    verified_receiver_sha256: str,
    observed_remote_ingress_python_argv: list[str],
    loader_mode: str,
) -> int:
    envelope = _canonical_document(verified_envelope_raw, "activation ingress envelope")
    if loader_mode == "--activation-resource-probe":
        result = run_resource_probe_v42r1(
            envelope=envelope,
            expected_plan_id=expected_plan_id,
            expected_receipt_id=expected_local_attempt_id,
            verified_receiver_sha256=verified_receiver_sha256,
            observed_remote_ingress_python_argv=observed_remote_ingress_python_argv,
        )
    elif loader_mode == "--activation-ingress":
        result = activate_selected_receipt_v42r1(
            envelope=envelope,
            expected_plan_id=expected_plan_id,
            expected_local_attempt_id=expected_local_attempt_id,
            verified_receiver_sha256=verified_receiver_sha256,
            observed_remote_ingress_python_argv=observed_remote_ingress_python_argv,
        )
    elif loader_mode == "--activation-classify":
        result = run_read_only_classification_v42r1(
            envelope=envelope,
            expected_plan_id=expected_plan_id,
            expected_local_attempt_id=expected_local_attempt_id,
            verified_receiver_sha256=verified_receiver_sha256,
            observed_remote_ingress_python_argv=observed_remote_ingress_python_argv,
        )
    else:
        _fail("activation receiver loader mode changed")
    raw = _canonical_bytes(result) + b"\n"
    if len(raw) > _MAXIMUM_OUTPUT_BYTES:
        _fail("activation ingress result exceeded cap")
    os.write(1, raw)
    return 0
