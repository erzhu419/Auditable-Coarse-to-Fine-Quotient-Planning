#!/usr/bin/env python3
"""Standalone read-only receiver for the frozen V42r3r3 launch occurrence.

The source bytes are intended to be supplied directly to
``/usr/bin/python3 -I -S -B -c``.  The receiver has one mode and performs only
bounded reads plus two ``systemctl show`` observations.  In particular, this
module has no journal creation/publication, systemd lifecycle operation, or
scientific-runner execution path.

The observation is deliberately weaker than a historical non-execution
proof: an absent journal and an absent unit are current-state observations.
They cannot prove that the retained V42r3r3 launch occurrence never started.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import selectors
import signal
import socket
import stat
import subprocess
import sys
import time
from typing import Any, Mapping, NoReturn, Sequence
import uuid


SCHEMA_VERSION = "42.3.4"
MODE = "--inspect-retained-launch-v42r3r4"
RECOVERY_OPERATION = "READ_ONLY_LAUNCH_RECOVERY"
RECOVERY_INSPECTION_ORDINAL = 1
INGRESS_SCHEMA = "acfqp.v42r3r4_formal_launch_recovery_ingress"
REMOTE_INSPECTION_SCHEMA = (
    "acfqp.v42r3r4_formal_launch_recovery_remote_inspection"
)
REMOTE_INSPECTION_DOMAIN = (
    b"acfqp:v42r3r4-formal-launch-recovery:remote-inspection"
)
RETAINED_PLAN_DOMAIN = b"acfqp:v42-formal-transport-successor:plan:v42r3"
RETAINED_CONTROLLER_MANIFEST_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:controller-source-manifest:v42r3"
)
RETAINED_LAUNCH_TRANSPORT_ATTEMPT_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:launch-transport-attempt:v42r3"
)
RETAINED_LAUNCH_ADMISSION_RECEIPT_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:launch-admission-receipt:v42r3"
)
RETAINED_SERVICE_WRAPPER_ATTESTATION_DOMAIN = (
    b"acfqp:v42-formal-transport-successor:service-wrapper-attestation:v42r3"
)
RETAINED_PLAN_SCHEMA = "acfqp.v42_formal_transport_successor_plan.v42r3"
RETAINED_PLAN_VERSION = "42.3.0"
FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2"
GLOBAL_EXECUTION_ORDINAL = 2

REMOTE_HOSTNAME = "erzhu419-Super-Server"
REMOTE_USER = "erzhu419"
REMOTE_UID = 1000
REMOTE_GID = 1000
REMOTE_PYTHON_PATH = "/usr/bin/python3"
REMOTE_PYTHON_REALPATH = "/usr/bin/python3.12"
REMOTE_PYTHON_VERSION = (3, 12, 3)
SYSTEMCTL_PATH = "/usr/bin/systemctl"
SYSTEMD_CLIENT_ENVIRONMENT = {
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "LC_ALL": "C.UTF-8",
    "XDG_RUNTIME_DIR": "/run/user/1000",
}
FIXED_REMOTE_ROOT = "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2"
FIXED_SOURCE_ROOT = FIXED_REMOTE_ROOT + "/source"
RETAINED_REMOTE_JOURNAL_ROOT = (
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-remote-ordinal2-formal-transport-v42r3r3"
)
SYSTEMD_UNIT_PREFIX = "acfqp-v42r3r3-remote-ordinal2-"

REMOTE_CONTROLLER_NAME = "CONTROLLER_SOURCE_MANIFEST.json"
REMOTE_LOADER_NAME = "FORMAL_TRANSPORT_LOADER.py"
REMOTE_AUTHORITY_NAME = "FORMAL_TRANSPORT_AUTHORITY.py"
REMOTE_RECEIVER_NAME = "FORMAL_TRANSPORT_RECEIVER.py"
REMOTE_PLAN_NAME = "FORMAL_TRANSPORT_PLAN.json"
REMOTE_TRANSPORT_ATTEMPT_NAME = "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json"
REMOTE_ADMISSION_NAME = "FORMAL_LAUNCH_ADMISSION_RECEIPT.json"
REMOTE_WRAPPER_ATTESTATION_NAME = "FORMAL_SERVICE_WRAPPER_ATTESTATION.json"
REMOTE_INITIAL_INVENTORY = frozenset(
    {
        REMOTE_CONTROLLER_NAME,
        REMOTE_LOADER_NAME,
        REMOTE_AUTHORITY_NAME,
        REMOTE_RECEIVER_NAME,
        REMOTE_PLAN_NAME,
        REMOTE_TRANSPORT_ATTEMPT_NAME,
    }
)
REMOTE_ALLOWED_INVENTORY = REMOTE_INITIAL_INVENTORY | {
    REMOTE_ADMISSION_NAME,
    REMOTE_WRAPPER_ATTESTATION_NAME,
}
RECOVERED_ARTIFACT_NAMES = {
    "launch_transport_attempt": REMOTE_TRANSPORT_ATTEMPT_NAME,
    "launch_admission_receipt": REMOTE_ADMISSION_NAME,
    "service_wrapper_attestation": REMOTE_WRAPPER_ATTESTATION_NAME,
}

MANAGER_SHOW_FIELDS = (
    "InvocationID",
    "MainPID",
    "ControlGroup",
    "LoadState",
    "ActiveState",
    "SubState",
)
UNIT_SHOW_FIELDS = (
    "Id",
    "LoadState",
    "ActiveState",
    "SubState",
    "Result",
    "InvocationID",
    "MainPID",
    "ControlGroup",
    "Type",
    "Restart",
    "RemainAfterExit",
    "SuccessExitStatus",
    "UMask",
    "KillMode",
    "TimeoutStopUSec",
    "RuntimeMaxUSec",
    "StandardInput",
    "StandardOutput",
    "StandardError",
    "WorkingDirectory",
    "Slice",
    "FragmentPath",
    "ExecStart",
    "Environment",
)

INGRESS_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "recovery_plan_id",
        "retained_launch_occurrence_id",
        "retained_formal_transport_plan",
        "retained_formal_transport_plan_id",
        "retained_local_launch_attempt_id",
        "retained_remote_journal_root",
        "retained_systemd_unit_name",
        "expected_remote_hostname",
        "expected_remote_uid",
        "expected_remote_gid",
        "recovery_inspection_ordinal",
    }
)
RUNTIME_FIELDS = frozenset(
    {
        "hostname",
        "user",
        "uid",
        "gid",
        "python_invocation",
        "python_realpath",
        "python_version",
        "python_isolated_flag",
        "python_no_site_flag",
        "python_dont_write_bytecode",
    }
)
TOOL_FACT_FIELDS = frozenset(
    {"path", "sha256", "byte_count", "mode", "uid", "gid", "st_nlink"}
)
REMOTE_TOOL_PATHS = {
    "env": "/usr/bin/env",
    "python": REMOTE_PYTHON_REALPATH,
    "systemctl": SYSTEMCTL_PATH,
    "systemd_run": "/usr/bin/systemd" + "-run",
}
MAX_INGRESS_BYTES = 8 * 1024**2
MAX_JOURNAL_ARTIFACT_BYTES = 8 * 1024**2
MAX_SYSTEMCTL_STDOUT = 256 * 1024
MAX_SYSTEMCTL_STDERR = 64 * 1024
COMMAND_TIMEOUT_SECONDS = 30.0
_HEX64 = re.compile(r"[0-9a-f]{64}")
_INVOCATION32 = re.compile(r"[0-9a-f]{32}")
_CGROUP = re.compile(r"/(?:[A-Za-z0-9_.:@\\-]+/?)*")


class V42R3R4RecoveryReceiverError(RuntimeError):
    """The authenticated read-only recovery receiver rejected its input."""


def _fail(message: str) -> NoReturn:
    raise V42R3R4RecoveryReceiverError(message)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_INGRESS_BYTES:
        _fail(label + " changed emptiness or cap")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, ValueError, TypeError) as error:
        raise V42R3R4RecoveryReceiverError(label + " is not canonical JSON") from error
    if type(value) is not dict or _canonical_bytes(value) != raw:
        _fail(label + " canonical bytes changed")
    return value


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + b"\0" + _canonical_bytes(dict(payload))).hexdigest()


def _claimed_id(
    document: Mapping[str, Any], *, field: str, domain: bytes, label: str,
) -> str:
    claimed = document.get(field)
    if type(claimed) is not str or _HEX64.fullmatch(claimed) is None:
        _fail(label + " ID changed")
    payload = {key: value for key, value in document.items() if key != field}
    if _content_id(domain, payload) != claimed:
        _fail(label + " content ID changed")
    return claimed


def _verify_ingress(raw: bytes, expected_recovery_plan_id: str) -> dict[str, Any]:
    document = _canonical_document(raw, "formal recovery ingress")
    if (
        set(document) != INGRESS_FIELDS
        or document.get("schema") != INGRESS_SCHEMA
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("recovery_plan_id") != expected_recovery_plan_id
        or _HEX64.fullmatch(expected_recovery_plan_id) is None
    ):
        _fail("formal recovery ingress schema, version, or plan ID changed")
    for field in (
        "retained_launch_occurrence_id",
        "retained_formal_transport_plan_id",
        "retained_local_launch_attempt_id",
    ):
        value = document[field]
        if type(value) is not str or _HEX64.fullmatch(value) is None:
            _fail("formal recovery retained ID changed: " + field)
    if (
        document["retained_remote_journal_root"] != RETAINED_REMOTE_JOURNAL_ROOT
        or document["expected_remote_hostname"] != REMOTE_HOSTNAME
        or document["expected_remote_uid"] != REMOTE_UID
        or document["expected_remote_gid"] != REMOTE_GID
        or document["recovery_inspection_ordinal"]
        != RECOVERY_INSPECTION_ORDINAL
    ):
        _fail("formal recovery fixed host, root, or ordinal changed")
    attempt_id = document["retained_local_launch_attempt_id"]
    expected_unit = SYSTEMD_UNIT_PREFIX + attempt_id + ".service"
    if document["retained_systemd_unit_name"] != expected_unit:
        _fail("formal recovery retained systemd unit changed")
    plan = document["retained_formal_transport_plan"]
    if type(plan) is not dict:
        _fail("formal recovery retained plan changed type")
    plan_id = _claimed_id(
        plan,
        field="formal_transport_plan_id",
        domain=RETAINED_PLAN_DOMAIN,
        label="retained formal transport plan",
    )
    if (
        plan_id != document["retained_formal_transport_plan_id"]
        or plan.get("schema") != RETAINED_PLAN_SCHEMA
        or plan.get("schema_version") != RETAINED_PLAN_VERSION
        or plan.get("formal_identity") != FORMAL_IDENTITY
        or plan.get("global_execution_ordinal") != GLOBAL_EXECUTION_ORDINAL
        or plan.get("fixed_remote_root") != FIXED_REMOTE_ROOT
        or plan.get("fixed_source_root") != FIXED_SOURCE_ROOT
        or plan.get("remote_journal_root") != RETAINED_REMOTE_JOURNAL_ROOT
        or plan.get("expected_remote_hostname") != REMOTE_HOSTNAME
        or plan.get("observed_remote_hostname") != REMOTE_HOSTNAME
        or plan.get("observed_remote_user") != REMOTE_USER
        or plan.get("observed_remote_uid") != REMOTE_UID
        or plan.get("observed_remote_gid") != REMOTE_GID
        or plan.get("controller_same_effect_dispatch_replay_forbidden_after_marker")
        is not True
        or plan.get("unit_absence_never_proves_service_never_started") is not True
    ):
        _fail("formal recovery retained plan binding changed")
    _retained_execution_tcb(plan)
    return document


def _retained_tool_fact(
    value: Any, *, expected_path: str, label: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != TOOL_FACT_FIELDS:
        _fail("retained " + label + " tool fact field set changed")
    fact = dict(value)
    if (
        fact["path"] != expected_path
        or type(fact["path"]) is not str
        or type(fact["sha256"]) is not str
        or _HEX64.fullmatch(fact["sha256"]) is None
        or type(fact["byte_count"]) is not int
        or not 0 < fact["byte_count"] <= 64 * 1024**2
        or type(fact["mode"]) is not int
        or fact["mode"] != 0o755
        or type(fact["uid"]) is not int
        or fact["uid"] != 0
        or type(fact["gid"]) is not int
        or fact["gid"] != 0
        or type(fact["st_nlink"]) is not int
        or fact["st_nlink"] != 1
    ):
        _fail("retained " + label + " tool fact changed")
    return fact


def _retained_execution_tcb(
    plan: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    receipt = plan.get("host_epoch_receipt")
    if type(receipt) is not dict:
        _fail("retained host epoch receipt changed type")
    runtime = receipt.get("observed_runtime")
    if type(runtime) is not dict or set(runtime) != RUNTIME_FIELDS:
        _fail("retained Python runtime field set changed")
    expected_runtime = {
        "hostname": REMOTE_HOSTNAME,
        "user": REMOTE_USER,
        "uid": REMOTE_UID,
        "gid": REMOTE_GID,
        "python_invocation": REMOTE_PYTHON_PATH,
        "python_realpath": REMOTE_PYTHON_REALPATH,
        "python_version": list(REMOTE_PYTHON_VERSION),
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
    }
    if runtime != expected_runtime:
        _fail("retained Python runtime evidence changed")
    plan_tools = plan.get("remote_tool_facts")
    receipt_tools = receipt.get("remote_tool_facts")
    if (
        type(plan_tools) is not dict
        or type(receipt_tools) is not dict
        or set(plan_tools) != set(REMOTE_TOOL_PATHS)
        or set(receipt_tools) != set(REMOTE_TOOL_PATHS)
        or plan_tools != receipt_tools
    ):
        _fail("retained remote tool fact inventory or receipt join changed")
    tools = {
        name: _retained_tool_fact(
            plan_tools[name], expected_path=path, label=name
        )
        for name, path in REMOTE_TOOL_PATHS.items()
    }
    return dict(runtime), tools


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


def _directory_identity(observed: os.stat_result) -> tuple[int, int]:
    return observed.st_dev, observed.st_ino


def _stable_virtual_regular(path: str, cap: int) -> bytes:
    named = os.lstat(path)
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("unsafe virtual read-only artifact: " + path)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > cap:
                _fail("virtual read-only artifact exceeded cap: " + path)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.lstat(path)
    if (
        _stable_state(before) != _stable_state(after)
        or _stable_state(after) != _stable_state(final)
    ):
        _fail("virtual read-only artifact changed during observation: " + path)
    return b"".join(chunks)


class _ExecutablePin:
    def __init__(self, expected_fact: Mapping[str, Any], *, label: str) -> None:
        path = expected_fact.get("path")
        if type(path) is not str:
            _fail(label + " executable path changed")
        fact = _retained_tool_fact(
            expected_fact, expected_path=path, label=label
        )
        self.path = path
        self.label = label
        self.byte_count = fact["byte_count"]
        self.sha256 = fact["sha256"]
        self.descriptor = -1
        named = os.lstat(path)
        self.descriptor = os.open(
            path, os.O_RDONLY | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        observed = os.fstat(self.descriptor)
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != fact["mode"]
            or observed.st_uid != fact["uid"]
            or observed.st_gid != fact["gid"]
            or observed.st_nlink != fact["st_nlink"]
            or observed.st_size != self.byte_count
            or _stable_state(observed) != _stable_state(named)
        ):
            self.close()
            _fail(label + " executable identity changed")
        self.state = _stable_state(observed)
        try:
            self.verify()
        except BaseException:
            self.close()
            raise

    def _digest(self) -> str:
        digest = hashlib.sha256()
        offset = 0
        while offset < self.byte_count:
            chunk = os.pread(
                self.descriptor,
                min(1024 * 1024, self.byte_count - offset),
                offset,
            )
            if not chunk:
                _fail(self.label + " executable ended early while hashed")
            digest.update(chunk)
            offset += len(chunk)
        if os.pread(self.descriptor, 1, self.byte_count):
            _fail(self.label + " executable grew while hashed")
        return digest.hexdigest()

    def verify(self) -> None:
        if self.descriptor < 0:
            _fail(self.label + " executable pin is closed")
        if (
            _stable_state(os.fstat(self.descriptor)) != self.state
            or _stable_state(os.lstat(self.path)) != self.state
            or self._digest() != self.sha256
        ):
            _fail(self.label + " executable changed while pinned")

    def close(self) -> None:
        descriptor = self.descriptor
        self.descriptor = -1
        if descriptor >= 0:
            os.close(descriptor)


def _verify_current_python_runtime(
    runtime: Mapping[str, Any], python_pin: _ExecutablePin,
) -> None:
    python_pin.verify()
    pinned = os.fstat(python_pin.descriptor)
    live_executable = os.stat("/proc/self/exe")
    if (
        sys.executable != runtime["python_invocation"]
        or os.path.realpath(sys.executable) != runtime["python_realpath"]
        or python_pin.path != runtime["python_realpath"]
        or list(sys.version_info[:3]) != runtime["python_version"]
        or sys.flags.isolated != runtime["python_isolated_flag"]
        or sys.flags.no_site != runtime["python_no_site_flag"]
        or sys.dont_write_bytecode is not runtime["python_dont_write_bytecode"]
        or (live_executable.st_dev, live_executable.st_ino)
        != (pinned.st_dev, pinned.st_ino)
    ):
        _fail("current Python runtime differs from retained exact evidence")


def _kill_reap(process: subprocess.Popen[bytes]) -> None:
    """Collect only the receiver's read-only systemctl child on failure."""

    try:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except BaseException:
                process.kill()
        process.wait(timeout=10)
    except BaseException:
        pass


def _run_systemctl_show(
    pin: _ExecutablePin, *, user: bool, unit: str, fields: Sequence[str],
) -> bytes:
    pin.verify()
    argv = [pin.path]
    if user:
        argv.append("--user")
    argv.extend(("--no-pager", "show"))
    argv.extend("--property=" + field for field in fields)
    argv.append(unit)
    process = subprocess.Popen(
        tuple(argv),
        executable="/proc/self/fd/" + str(pin.descriptor),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/",
        env=dict(SYSTEMD_CLIENT_ENVIRONMENT),
        close_fds=True,
        pass_fds=(pin.descriptor,),
        start_new_session=True,
    )
    selector: selectors.BaseSelector | None = None
    try:
        if process.stdout is None or process.stderr is None:
            _fail("read-only systemctl pipes were not created")
        selector = selectors.DefaultSelector()
        streams = {"stdout": bytearray(), "stderr": bytearray()}
        caps = {"stdout": MAX_SYSTEMCTL_STDOUT, "stderr": MAX_SYSTEMCTL_STDERR}
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic() + COMMAND_TIMEOUT_SECONDS
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail("read-only systemctl show timed out")
            for key, _mask in selector.select(min(remaining, 0.25)):
                try:
                    chunk = os.read(key.fd, 64 * 1024)
                except (BlockingIOError, InterruptedError):
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                streams[key.data].extend(chunk)
                if len(streams[key.data]) > caps[key.data]:
                    _fail("read-only systemctl stream exceeded cap")
        returncode = process.wait(
            timeout=max(0.1, deadline - time.monotonic())
        )
        pin.verify()
        if returncode != 0 or streams["stderr"]:
            _fail("read-only systemctl show did not close exactly")
        return bytes(streams["stdout"])
    except BaseException:
        _kill_reap(process)
        raise
    finally:
        if selector is not None:
            selector.close()
        for stream in (process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()


def _property_records(raw: bytes) -> dict[str, str]:
    if not raw.endswith(b"\n") or b"\0" in raw:
        _fail("systemctl properties are not canonical newline text")
    try:
        lines = raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as error:
        raise V42R3R4RecoveryReceiverError("systemctl output is not UTF-8") from error
    result: dict[str, str] = {}
    for line in lines:
        if not line or "=" not in line:
            _fail("systemctl property record changed")
        key, value = line.split("=", 1)
        if key in result:
            _fail("systemctl property was duplicated")
        result[key] = value
    return result


def _parse_manager_properties(raw: bytes) -> dict[str, str]:
    properties = _property_records(raw)
    if set(properties) != set(MANAGER_SHOW_FIELDS):
        _fail("systemctl manager property inventory changed")
    return properties


def _parse_unit_properties(raw: bytes) -> tuple[dict[str, str], str]:
    """Parse exact unit properties, allowing systemd's one absent-unit omission."""

    properties = _property_records(raw)
    expected = set(UNIT_SHOW_FIELDS)
    observed = set(properties)
    if observed == expected:
        exec_state = (
            "PRESENT_EMPTY" if properties["ExecStart"] == "" else "PRESENT_NONEMPTY"
        )
    elif (
        observed == expected - {"ExecStart"}
        and properties.get("LoadState") == "not-found"
        and properties.get("FragmentPath") == ""
    ):
        exec_state = "OMITTED_ONLY_FOR_NOT_FOUND_UNIT"
    else:
        _fail("systemctl unit property inventory changed")
    properties.pop("ExecStart", None)
    return properties, exec_state


def _manager_binding(systemctl_pin: _ExecutablePin) -> dict[str, Any]:
    boot_raw = _stable_virtual_regular("/proc/sys/kernel/random/boot_id", 128)
    try:
        boot = boot_raw.decode("ascii", errors="strict").strip()
    except UnicodeError as error:
        raise V42R3R4RecoveryReceiverError("kernel boot ID is not ASCII") from error
    if str(uuid.UUID(boot)) != boot or boot_raw != (boot + "\n").encode("ascii"):
        _fail("kernel boot ID encoding changed")
    linger = "/var/lib/systemd/linger/" + REMOTE_USER
    linger_raw = _stable_virtual_regular(linger, 1)
    linger_state = os.lstat(linger)
    if (
        linger_raw != b""
        or stat.S_IMODE(linger_state.st_mode) != 0o644
        or linger_state.st_uid != 0
        or linger_state.st_gid != 0
        or linger_state.st_nlink != 1
    ):
        _fail("systemd linger authority changed")
    properties = _parse_manager_properties(
        _run_systemctl_show(
            systemctl_pin,
            user=False,
            unit="user@1000.service",
            fields=MANAGER_SHOW_FIELDS,
        )
    )
    if (
        properties["LoadState"] != "loaded"
        or properties["ActiveState"] != "active"
        or properties["SubState"] != "running"
        or not properties["MainPID"].isdigit()
        or int(properties["MainPID"]) <= 1
        or _INVOCATION32.fullmatch(properties["InvocationID"]) is None
        or _CGROUP.fullmatch(properties["ControlGroup"]) is None
        or not properties["ControlGroup"].startswith("/user.slice/")
    ):
        _fail("user systemd manager epoch changed")
    return {
        "kernel_boot_id": boot,
        "linger_enabled": True,
        "linger_path": linger,
        "user_manager_invocation_id": str(uuid.UUID(properties["InvocationID"])),
        "user_manager_main_pid": int(properties["MainPID"]),
        "user_manager_control_group": properties["ControlGroup"],
    }


def _unit_observation(
    systemctl_pin: _ExecutablePin, *, attempt_id: str, expected_unit: str,
) -> dict[str, Any]:
    properties, exec_state = _parse_unit_properties(
        _run_systemctl_show(
            systemctl_pin,
            user=True,
            unit=expected_unit,
            fields=UNIT_SHOW_FIELDS,
        )
    )
    result: dict[str, Any] = dict(properties)
    try:
        result["MainPID"] = int(properties["MainPID"])
    except ValueError as error:
        raise V42R3R4RecoveryReceiverError("unit MainPID is not decimal") from error
    if result["MainPID"] < 0:
        _fail("unit MainPID changed range")
    if properties["InvocationID"]:
        if _INVOCATION32.fullmatch(properties["InvocationID"]) is None:
            _fail("unit InvocationID changed")
        result["InvocationID"] = str(uuid.UUID(properties["InvocationID"]))
    if properties["Id"] != expected_unit:
        _fail("observed systemd unit identity changed")
    result["ExecStartPropertyState"] = exec_state
    if result["LoadState"] == "loaded":
        if (
            result["Type"] != "exec"
            or result["Restart"] != "no"
            or result["RemainAfterExit"] != "yes"
            or result["SuccessExitStatus"] != "2"
            or result["UMask"] != "0077"
            or result["KillMode"] != "mixed"
            or result["TimeoutStopUSec"] != "30s"
            or result["RuntimeMaxUSec"] != "1w 25min"
            or result["StandardInput"] != "null"
            or result["StandardOutput"] != "null"
            or result["StandardError"] != "null"
            or result["WorkingDirectory"] != FIXED_SOURCE_ROOT
            or result["Slice"] != "app.slice"
            or result["FragmentPath"]
            != "/run/user/1000/systemd/transient/" + expected_unit
            or result["Environment"] != ""
        ):
            _fail("loaded retained systemd service contract changed")
        if result["MainPID"] > 1:
            pid = str(result["MainPID"])
            cmdline = _stable_virtual_regular("/proc/" + pid + "/cmdline", 1024**2)
            if not cmdline or not cmdline.endswith(b"\0") or b"\0\0" in cmdline:
                _fail("retained unit MainPID cmdline changed encoding")
            try:
                result["LiveMainPIDArgv"] = [
                    item.decode("utf-8", errors="strict")
                    for item in cmdline[:-1].split(b"\0")
                ]
            except UnicodeError as error:
                raise V42R3R4RecoveryReceiverError(
                    "retained unit MainPID argv is not UTF-8"
                ) from error
            cgroup = _stable_virtual_regular("/proc/" + pid + "/cgroup", 64 * 1024)
            if cgroup != ("0::" + result["ControlGroup"] + "\n").encode("ascii"):
                _fail("retained unit MainPID cgroup/systemctl join changed")
            result["LiveMainPIDArgvSource"] = "PROC_MAINPID_CMDLINE"
        else:
            result["LiveMainPIDArgv"] = []
            result["LiveMainPIDArgvSource"] = "UNAVAILABLE_NO_MAINPID"
    else:
        if result["FragmentPath"] != "" or result["MainPID"] != 0:
            _fail("non-loaded retained unit invented fragment or MainPID")
        result["LiveMainPIDArgv"] = []
        result["LiveMainPIDArgvSource"] = "ABSENT_UNIT"
    return result


class _ReadOnlyDirectoryPin:
    """No-follow read-only capability for the retained journal directory."""

    def __init__(self, path: str, chain: list[tuple[int, str | None, tuple[int, int]]]):
        self.path = path
        self.chain = chain

    @property
    def descriptor(self) -> int:
        if not self.chain:
            _fail("retained journal pin is closed")
        return self.chain[-1][0]

    @classmethod
    def open_optional(cls, path: str) -> "_ReadOnlyDirectoryPin | None":
        pure = PurePosixPath(path)
        if not pure.is_absolute() or ".." in pure.parts or pure == PurePosixPath("/"):
            _fail("retained journal path changed")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open("/", flags)
        chain: list[tuple[int, str | None, tuple[int, int]]] = [
            (descriptor, None, _directory_identity(os.fstat(descriptor)))
        ]
        try:
            for component in pure.parent.parts[1:]:
                named = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                if not stat.S_ISDIR(named.st_mode):
                    _fail("retained journal ancestry is not a directory")
                child = os.open(component, flags, dir_fd=descriptor)
                opened = os.fstat(child)
                if _directory_identity(named) != _directory_identity(opened):
                    os.close(child)
                    _fail("retained journal ancestry changed while opening")
                chain.append((child, component, _directory_identity(opened)))
                descriptor = child
            try:
                named = os.stat(pure.name, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                for _ordinal in range(2):
                    cls._verify_chain(chain)
                    try:
                        os.stat(pure.name, dir_fd=descriptor, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        _fail("retained journal appeared during absence observation")
                cls._close_chain(chain)
                return None
            if not stat.S_ISDIR(named.st_mode):
                _fail("retained journal is not a directory")
            child = os.open(pure.name, flags, dir_fd=descriptor)
            opened = os.fstat(child)
            if _directory_identity(named) != _directory_identity(opened):
                os.close(child)
                _fail("retained journal changed while opening")
            chain.append((child, pure.name, _directory_identity(opened)))
            result = cls(path, chain)
            result.verify()
            return result
        except BaseException:
            cls._close_chain(chain)
            raise

    @staticmethod
    def _verify_chain(chain: list[tuple[int, str | None, tuple[int, int]]]) -> None:
        for index, (descriptor, name, identity) in enumerate(chain):
            if _directory_identity(os.fstat(descriptor)) != identity:
                _fail("held retained journal ancestry changed")
            if index:
                assert name is not None
                named = os.stat(name, dir_fd=chain[index - 1][0], follow_symlinks=False)
                if _directory_identity(named) != identity:
                    _fail("named retained journal ancestry changed")

    @staticmethod
    def _close_chain(chain: list[tuple[int, str | None, tuple[int, int]]]) -> None:
        while chain:
            descriptor, _name, _identity = chain.pop()
            try:
                os.close(descriptor)
            except OSError:
                pass

    def verify(self) -> None:
        self._verify_chain(self.chain)
        root = os.fstat(self.descriptor)
        if (
            not stat.S_ISDIR(root.st_mode)
            or stat.S_IMODE(root.st_mode) != 0o700
            or root.st_uid != REMOTE_UID
            or root.st_gid != REMOTE_GID
            or root.st_nlink != 2
        ):
            _fail("retained journal root authority changed")

    def inventory(self) -> frozenset[str]:
        self.verify()
        before = frozenset(os.listdir(self.descriptor))
        self.verify()
        after = frozenset(os.listdir(self.descriptor))
        if (
            before != after
            or not REMOTE_INITIAL_INVENTORY <= before
            or not before <= REMOTE_ALLOWED_INVENTORY
            or REMOTE_WRAPPER_ATTESTATION_NAME in before
            and REMOTE_ADMISSION_NAME not in before
        ):
            _fail("retained journal inventory changed")
        return before

    def read(self, name: str) -> bytes:
        if name not in REMOTE_ALLOWED_INVENTORY:
            _fail("retained journal artifact name changed")
        self.verify()
        named = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=self.descriptor,
        )
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != REMOTE_UID
                or before.st_gid != REMOTE_GID
                or before.st_nlink != 1
                or before.st_size < 0
                or before.st_size > MAX_JOURNAL_ARTIFACT_BYTES
                or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
            ):
                _fail("retained journal artifact authority changed: " + name)
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    _fail("retained journal artifact ended early: " + name)
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _fail("retained journal artifact grew during read: " + name)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        self.verify()
        final = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        if (
            _stable_state(before) != _stable_state(after)
            or _stable_state(after) != _stable_state(final)
        ):
            _fail("retained journal artifact changed during read: " + name)
        return b"".join(chunks)

    def close(self) -> None:
        self._close_chain(self.chain)

    def __enter__(self) -> "_ReadOnlyDirectoryPin":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _verify_raw_fact(raw: bytes, fact: object, label: str) -> None:
    if (
        type(fact) is not dict
        or type(fact.get("byte_count")) is not int
        or type(fact.get("sha256")) is not str
        or len(raw) != fact["byte_count"]
        or hashlib.sha256(raw).hexdigest() != fact["sha256"]
    ):
        _fail("retained " + label + " artifact fact changed")


def _verify_recovered_documents(
    recovered: dict[str, dict[str, Any]], *, plan_id: str, attempt_id: str,
    expected_unit: str,
) -> None:
    attempt = recovered.get("launch_transport_attempt")
    if attempt is not None:
        _claimed_id(
            attempt,
            field="formal_launch_transport_attempt_id",
            domain=RETAINED_LAUNCH_TRANSPORT_ATTEMPT_DOMAIN,
            label="retained launch transport attempt",
        )
        if (
            attempt.get("schema")
            != "acfqp.v42_formal_transport_successor_launch_transport_attempt.v42r3"
            or attempt.get("schema_version") != RETAINED_PLAN_VERSION
            or attempt.get("formal_transport_plan_id") != plan_id
            or attempt.get("local_launch_attempt_id") != attempt_id
            or attempt.get("unit_name") != expected_unit
            or attempt.get("operation") != "LAUNCH"
            or attempt.get("network_effect_started") is not False
            or attempt.get("systemd_admission_effect_started") is not False
            or attempt.get("formal_execution_performed") is not False
            or attempt.get(
                "controller_same_effect_dispatch_replay_forbidden_after_network_marker"
            )
            is not True
        ):
            _fail("retained launch transport attempt changed")
    admission = recovered.get("launch_admission_receipt")
    if admission is not None:
        _claimed_id(
            admission,
            field="formal_launch_admission_receipt_id",
            domain=RETAINED_LAUNCH_ADMISSION_RECEIPT_DOMAIN,
            label="retained launch admission receipt",
        )
        if (
            attempt is None
            or admission.get("schema")
            != "acfqp.v42_formal_transport_successor_launch_admission_receipt.v42r3"
            or admission.get("schema_version") != RETAINED_PLAN_VERSION
            or admission.get("formal_transport_plan_id") != plan_id
            or admission.get("local_launch_attempt_id") != attempt_id
            or admission.get("unit_name") != expected_unit
            or admission.get("formal_launch_transport_attempt_id")
            != attempt.get("formal_launch_transport_attempt_id")
        ):
            _fail("retained launch admission receipt changed")
    wrapper = recovered.get("service_wrapper_attestation")
    if wrapper is not None:
        _claimed_id(
            wrapper,
            field="formal_service_wrapper_attestation_id",
            domain=RETAINED_SERVICE_WRAPPER_ATTESTATION_DOMAIN,
            label="retained service wrapper attestation",
        )
        if (
            admission is None
            or wrapper.get("schema")
            != "acfqp.v42_formal_transport_successor_service_wrapper_attestation.v42r3"
            or wrapper.get("schema_version") != RETAINED_PLAN_VERSION
            or wrapper.get("formal_transport_plan_id") != plan_id
            or wrapper.get("local_launch_attempt_id") != attempt_id
            or wrapper.get("formal_launch_transport_attempt_id")
            != attempt.get("formal_launch_transport_attempt_id")
            or wrapper.get("formal_launch_admission_receipt_id")
            != admission.get("formal_launch_admission_receipt_id")
        ):
            _fail("retained service wrapper attestation changed")


def _journal_observation(
    *, retained_plan: Mapping[str, Any], plan_id: str, attempt_id: str,
    expected_unit: str,
) -> tuple[str, list[str], dict[str, str], dict[str, dict[str, Any]]]:
    pin = _ReadOnlyDirectoryPin.open_optional(RETAINED_REMOTE_JOURNAL_ROOT)
    if pin is None:
        return (
            "ABSENT",
            [],
            {key: "ABSENT" for key in RECOVERED_ARTIFACT_NAMES},
            {},
        )
    with pin:
        inventory = pin.inventory()
        plan_raw = pin.read(REMOTE_PLAN_NAME)
        if plan_raw != _canonical_bytes(dict(retained_plan)):
            _fail("retained journal plan differs from recovery ingress")
        controller = _canonical_document(
            pin.read(REMOTE_CONTROLLER_NAME), "retained controller source manifest"
        )
        controller_id = _claimed_id(
            controller,
            field="controller_source_manifest_id",
            domain=RETAINED_CONTROLLER_MANIFEST_DOMAIN,
            label="retained controller source manifest",
        )
        if controller_id != retained_plan.get("controller_source_manifest_id"):
            _fail("retained controller manifest identity changed")
        _verify_raw_fact(
            pin.read(REMOTE_LOADER_NAME),
            retained_plan.get("probe_loader_artifact"),
            "loader",
        )
        _verify_raw_fact(
            pin.read(REMOTE_AUTHORITY_NAME),
            retained_plan.get("formal_authority_artifact"),
            "authority",
        )
        _verify_raw_fact(
            pin.read(REMOTE_RECEIVER_NAME),
            retained_plan.get("probe_receiver_artifact"),
            "receiver",
        )
        recovered: dict[str, dict[str, Any]] = {}
        states: dict[str, str] = {}
        for key, name in RECOVERED_ARTIFACT_NAMES.items():
            if name in inventory:
                recovered[key] = _canonical_document(
                    pin.read(name), "retained " + key.replace("_", " ")
                )
                states[key] = "REGULAR_FILE"
            else:
                states[key] = "ABSENT"
        _verify_recovered_documents(
            recovered,
            plan_id=plan_id,
            attempt_id=attempt_id,
            expected_unit=expected_unit,
        )
        if pin.inventory() != inventory:
            _fail("retained journal changed during read-only recovery")
        return "DIRECTORY", sorted(inventory), states, recovered


def build_remote_inspection(
    *, ingress_raw: bytes, expected_recovery_plan_id: str,
) -> dict[str, Any]:
    """Authenticate one ingress and build one current-state-only inspection."""

    ingress = _verify_ingress(ingress_raw, expected_recovery_plan_id)
    retained_plan = ingress["retained_formal_transport_plan"]
    runtime, tools = _retained_execution_tcb(retained_plan)
    python_pin = _ExecutablePin(tools["python"], label="Python")
    systemctl_pin: _ExecutablePin | None = None
    try:
        _verify_current_python_runtime(runtime, python_pin)
        if (
            socket.gethostname() != runtime["hostname"]
            or os.getuid() != runtime["uid"]
            or os.getgid() != runtime["gid"]
        ):
            _fail("formal recovery live host identity changed")
        systemctl_pin = _ExecutablePin(tools["systemctl"], label="systemctl")
        manager = _manager_binding(systemctl_pin)
        unit = _unit_observation(
            systemctl_pin,
            attempt_id=ingress["retained_local_launch_attempt_id"],
            expected_unit=ingress["retained_systemd_unit_name"],
        )
        state, inventory, artifact_states, recovered = _journal_observation(
            retained_plan=retained_plan,
            plan_id=ingress["retained_formal_transport_plan_id"],
            attempt_id=ingress["retained_local_launch_attempt_id"],
            expected_unit=ingress["retained_systemd_unit_name"],
        )
        systemctl_pin.verify()
        _verify_current_python_runtime(runtime, python_pin)
        payload = {
            "schema": REMOTE_INSPECTION_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "formal_identity": FORMAL_IDENTITY,
            "global_execution_ordinal": GLOBAL_EXECUTION_ORDINAL,
            "recovery_operation": RECOVERY_OPERATION,
            "recovery_plan_id": ingress["recovery_plan_id"],
            "retained_launch_occurrence_id": ingress[
                "retained_launch_occurrence_id"
            ],
            "retained_formal_transport_plan_id": ingress[
                "retained_formal_transport_plan_id"
            ],
            "retained_local_launch_attempt_id": ingress[
                "retained_local_launch_attempt_id"
            ],
            "recovery_inspection_ordinal": ingress["recovery_inspection_ordinal"],
            "retained_remote_journal_root": ingress[
                "retained_remote_journal_root"
            ],
            "retained_systemd_unit_name": ingress["retained_systemd_unit_name"],
            "observed_remote_hostname": REMOTE_HOSTNAME,
            "observed_remote_uid": REMOTE_UID,
            "observed_remote_gid": REMOTE_GID,
            "manager_binding": manager,
            "unit_observation": unit,
            "retained_remote_journal_state": state,
            "retained_remote_journal_inventory": inventory,
            "artifact_states": artifact_states,
            "recovered_documents": recovered,
            "authenticated_body_remote_filesystem_mutation_performed": False,
            "systemd_lifecycle_mutation_performed": False,
            "same_effect_reissued": False,
            "end_to_end_absence_claimed": False,
        }
        return {
            **payload,
            "remote_inspection_id": _content_id(REMOTE_INSPECTION_DOMAIN, payload),
        }
    finally:
        if systemctl_pin is not None:
            systemctl_pin.close()
        python_pin.close()


def _read_exact_stdin(expected_count: int) -> bytes:
    if not 0 < expected_count <= MAX_INGRESS_BYTES:
        _fail("formal recovery ingress byte count changed")
    chunks: list[bytes] = []
    remaining = expected_count
    while remaining:
        chunk = os.read(0, min(remaining, 1024 * 1024))
        if not chunk:
            _fail("formal recovery ingress ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(0, 1):
        _fail("formal recovery ingress included trailing bytes")
    return b"".join(chunks)


def _runtime_source() -> str:
    if len(sys.orig_argv) < 6 or sys.orig_argv[1:5] != ["-I", "-S", "-B", "-c"]:
        _fail("formal recovery Python invocation changed")
    source = sys.orig_argv[5]
    if (
        type(source) is not str
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or not sys.dont_write_bytecode
    ):
        _fail("formal recovery isolated Python flags changed")
    return source


def main() -> int:
    if len(sys.argv) != 7 or sys.argv[0] != "-c" or sys.argv[1] != MODE:
        _fail("formal recovery receiver mode or argv arity changed")
    source_raw = _runtime_source().encode("utf-8", errors="strict")
    try:
        source_count = int(sys.argv[3])
        ingress_count = int(sys.argv[5])
    except ValueError as error:
        raise V42R3R4RecoveryReceiverError("formal recovery byte count changed") from error
    if (
        str(source_count) != sys.argv[3]
        or str(ingress_count) != sys.argv[5]
        or _HEX64.fullmatch(sys.argv[2]) is None
        or _HEX64.fullmatch(sys.argv[4]) is None
        or _HEX64.fullmatch(sys.argv[6]) is None
        or len(source_raw) != source_count
        or hashlib.sha256(source_raw).hexdigest() != sys.argv[2]
    ):
        _fail("formal recovery receiver source or ingress fact changed")
    ingress_raw = _read_exact_stdin(ingress_count)
    if hashlib.sha256(ingress_raw).hexdigest() != sys.argv[4]:
        _fail("formal recovery ingress SHA256 changed")
    inspection = build_remote_inspection(
        ingress_raw=ingress_raw,
        expected_recovery_plan_id=sys.argv[6],
    )
    output = _canonical_bytes(inspection) + b"\n"
    written = 0
    while written < len(output):
        count = os.write(1, output[written:])
        if count <= 0:
            _fail("formal recovery stdout ended early")
        written += count
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "V42R3R4RecoveryReceiverError",
    "build_remote_inspection",
    "main",
]
