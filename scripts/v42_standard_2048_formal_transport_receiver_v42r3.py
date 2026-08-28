#!/usr/bin/env python3
"""Remote receiver for the native V42r3 formal transport successor.

The source-only loader authenticates and compiles these bytes in memory.  In
the authenticated receiver body, the only effectful modes are one-shot prepare
and launch admission; recovery modes are read-only and cannot replay an effect
whose durable marker exists.  The earlier sshd/PAM/login-shell startup path is
an external ingress TCB.  Noninterference by concurrent actors that can write
the campaign parents is also an explicit external premise; both are outside
the authenticated-body claims.
"""

from __future__ import annotations

import hashlib
import errno
import fcntl
import os
from pathlib import Path, PurePosixPath
import pwd
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

from acfqp import (
    construction_k7_standard_2048_formal_transport_successor_v42r3 as formal,
)
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as legacy,
)
from acfqp import (
    construction_k7_standard_2048_fresh_terminal_preregistration_v42 as prereg,
)
from acfqp import (
    construction_k7_standard_2048_process_supervision_v42r1 as processio,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42.3.0"
PROBE_MODE = "--probe-host-epoch-v42r3"
PREPARE_MODE = "--prepare-once-v42r3"
INSPECT_PREPARE_MODE = "--inspect-prepare-v42r3"
ADMIT_MODE = "--admit-launch-v42r3"
INSPECT_LAUNCH_MODE = "--inspect-launch-v42r3"
SERVICE_BOOTSTRAP_MODE = "--formal-launch-service-bootstrap-v42r3"
SERVICE_WRAPPER_MODE = "--formal-launch-service-wrapper-v42r3"
ALL_MODES = frozenset(
    {
        PROBE_MODE,
        PREPARE_MODE,
        INSPECT_PREPARE_MODE,
        ADMIT_MODE,
        INSPECT_LAUNCH_MODE,
        SERVICE_BOOTSTRAP_MODE,
        SERVICE_WRAPPER_MODE,
    }
)
INGRESS_SCHEMAS = {
    PREPARE_MODE: "acfqp.v42_formal_transport_prepare_ingress.v42r3",
    INSPECT_PREPARE_MODE: (
        "acfqp.v42_formal_transport_inspect_prepare_ingress.v42r3"
    ),
    ADMIT_MODE: "acfqp.v42_formal_transport_admit_launch_ingress.v42r3",
    INSPECT_LAUNCH_MODE: (
        "acfqp.v42_formal_transport_inspect_launch_ingress.v42r3"
    ),
}
FIXED_REMOTE_ROOT = Path("/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2")
FIXED_SOURCE_ROOT = FIXED_REMOTE_ROOT / "source"
REMOTE_V42R3_JOURNAL_ROOT = Path(
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-remote-ordinal2-formal-transport-v42r3r2"
)
REMOTE_CONTROLLER_NAME = "CONTROLLER_SOURCE_MANIFEST.json"
REMOTE_LOADER_NAME = "FORMAL_TRANSPORT_LOADER.py"
REMOTE_AUTHORITY_NAME = "FORMAL_TRANSPORT_AUTHORITY.py"
REMOTE_RECEIVER_NAME = "FORMAL_TRANSPORT_RECEIVER.py"
REMOTE_PLAN_NAME = "FORMAL_TRANSPORT_PLAN.json"
REMOTE_TRANSPORT_ATTEMPT_NAME = "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json"
REMOTE_ADMISSION_NAME = "FORMAL_LAUNCH_ADMISSION_RECEIPT.json"
REMOTE_WRAPPER_ATTESTATION_NAME = "FORMAL_SERVICE_WRAPPER_ATTESTATION.json"
REMOTE_JOURNAL_INITIAL_INVENTORY = (
    REMOTE_PLAN_NAME,
    REMOTE_CONTROLLER_NAME,
    REMOTE_LOADER_NAME,
    REMOTE_AUTHORITY_NAME,
    REMOTE_RECEIVER_NAME,
    REMOTE_TRANSPORT_ATTEMPT_NAME,
)
SYSTEMD_UNIT_PREFIX = "acfqp-v42r3r2-remote-ordinal2-"
REMOTE_HOST_ALIAS = "jtl110gpu2"
REMOTE_HOSTNAME = "erzhu419-Super-Server"
REMOTE_USER = "erzhu419"
REMOTE_UID = 1000
REMOTE_GID = 1000
REMOTE_PYTHON = "/usr/bin/python3"
REMOTE_PYTHON_REALPATH = "/usr/bin/python3.12"
REMOTE_PYTHON_VERSION = (3, 12, 3)
TOOL_PATHS = {
    "env": "/usr/bin/env",
    "python": REMOTE_PYTHON_REALPATH,
    "systemctl": "/usr/bin/systemctl",
    "systemd_run": "/usr/bin/systemd-run",
}
SYSTEMD_CLIENT_ENVIRONMENT = {
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "LC_ALL": "C.UTF-8",
    "XDG_RUNTIME_DIR": "/run/user/1000",
}
FORMAL_SERVICE_ENVIRONMENT = {
    "HOME": "/home/erzhu419",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "LOGNAME": REMOTE_USER,
    "PATH": "/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONCOERCECLOCALE": "0",
    "USER": REMOTE_USER,
}
FORBIDDEN_SYSTEMD_OPTIONS = frozenset(
    {"--wait", "--pipe", "--pty", "--scope", "--collect", "--binds-to"}
)
UNIT_SHOW_FIELDS = (
    "Id", "LoadState", "ActiveState", "SubState", "Result", "InvocationID",
    "MainPID", "ControlGroup", "Type", "Restart", "RemainAfterExit",
    "SuccessExitStatus", "UMask", "KillMode", "TimeoutStopUSec",
    "RuntimeMaxUSec", "StandardInput", "StandardOutput", "StandardError",
    "WorkingDirectory", "Slice", "FragmentPath", "ExecStart", "Environment",
)
MANAGER_SHOW_FIELDS = (
    "InvocationID", "MainPID", "ControlGroup", "LoadState", "ActiveState",
    "SubState",
)
MAX_SYSTEMCTL_STDOUT = 256 * 1024
MAX_SYSTEMCTL_STDERR = 64 * 1024
COMMAND_TIMEOUT_SECONDS = 30.0
ADMISSION_HANDSHAKE_TIMEOUT_SECONDS = 60.0
CLEAN_WRAPPER_TRANSITION_TIMEOUT_SECONDS = 30.0
MAX_SYSTEMD_RUN_STREAM = 64 * 1024
MAX_JOURNAL_ARTIFACT_BYTES = 8 * 1024**2
_INVOCATION32 = re.compile(r"[0-9a-f]{32}")
_CGROUP = re.compile(r"/(?:[A-Za-z0-9_.:@\\-]+/?)*")


class V42FormalProbeReceiverError(RuntimeError):
    """The read-only host probe rejected its plan or observation."""


def _fail(message: str) -> NoReturn:
    raise V42FormalProbeReceiverError(message)


def _canonical(raw: bytes, label: str) -> dict[str, Any]:
    try:
        result = loads_canonical_json(raw)
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42FormalProbeReceiverError(label + " is not canonical JSON") from error
    if type(result) is not dict or canonical_json_bytes(result) != raw:
        _fail(label + " canonical bytes changed")
    return result


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


def _directory_identity(observed: os.stat_result) -> tuple[int, ...]:
    """Return the immutable identity of a held directory inode."""

    return (observed.st_dev, observed.st_ino)


def _stable_regular(path: Path, cap: int) -> tuple[bytes, os.stat_result]:
    named = path.lstat()
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 0
            or before.st_size > cap
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("unsafe or oversized read-only artifact: " + str(path))
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("read-only artifact ended early: " + str(path))
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("read-only artifact grew during read: " + str(path))
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = path.lstat()
    if _stable_state(before) != _stable_state(after) or _stable_state(after) != _stable_state(final):
        _fail("read-only artifact changed during observation: " + str(path))
    return b"".join(chunks), after


def _stable_virtual_regular(
    path: Path, cap: int,
) -> tuple[bytes, os.stat_result]:
    """Read one bounded procfs/sysfs value whose reported st_size is zero."""

    lexical = str(path)
    if (
        not path.is_absolute()
        or ".." in path.parts
        or not (
            lexical.startswith("/proc/")
            or lexical.startswith("/sys/fs/cgroup/")
        )
        or type(cap) is not int
        or not 0 < cap <= 1024**2
    ):
        _fail("virtual read-only artifact path or cap changed")
    named = path.lstat()
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != 0
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("unsafe virtual read-only artifact: " + lexical)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > cap:
                _fail("virtual read-only artifact exceeded cap: " + lexical)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = path.lstat()
    if (
        _stable_state(before) != _stable_state(after)
        or _stable_state(after) != _stable_state(final)
    ):
        _fail("virtual read-only artifact changed during observation: " + lexical)
    return b"".join(chunks), after


class _ExecutablePin:
    def __init__(self, path: str) -> None:
        self.path = path
        self.descriptor = -1
        try:
            named = os.lstat(path)
            self.descriptor = os.open(
                path, os.O_RDONLY | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            observed = os.fstat(self.descriptor)
            if (
                not stat.S_ISREG(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o755
                or observed.st_uid != 0
                or observed.st_gid != 0
                or observed.st_nlink != 1
                or observed.st_size <= 0
                or observed.st_size > 64 * 1024**2
                or (observed.st_dev, observed.st_ino)
                != (named.st_dev, named.st_ino)
            ):
                _fail("remote executable identity changed: " + path)
            self.state = _stable_state(observed)
            digest = hashlib.sha256()
            count = 0
            while count < observed.st_size:
                chunk = os.read(
                    self.descriptor,
                    min(1024 * 1024, observed.st_size - count),
                )
                if not chunk:
                    _fail("remote executable ended early: " + path)
                digest.update(chunk)
                count += len(chunk)
            if os.read(self.descriptor, 1):
                _fail("remote executable grew during read: " + path)
            self.fact = {
                "path": path,
                "sha256": digest.hexdigest(),
                "byte_count": count,
                "mode": 0o755,
                "uid": 0,
                "gid": 0,
                "st_nlink": 1,
            }
            self.verify()
        except BaseException:
            try:
                self.close()
            except BaseException:
                pass
            raise

    def verify(self) -> None:
        if self.descriptor < 0:
            _fail("remote executable pin is closed")
        opened = os.fstat(self.descriptor)
        named = os.lstat(self.path)
        if (
            _stable_state(opened) != self.state
            or _stable_state(named) != self.state
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("remote executable changed while pinned: " + self.path)

    def close(self) -> None:
        descriptor = getattr(self, "descriptor", -1)
        self.descriptor = -1
        if descriptor >= 0:
            os.close(descriptor)


def _observe_tool_facts() -> tuple[dict[str, dict[str, Any]], _ExecutablePin]:
    result: dict[str, dict[str, Any]] = {}
    systemctl_pin: _ExecutablePin | None = None
    pins: list[_ExecutablePin] = []
    try:
        for name, path in TOOL_PATHS.items():
            pin = _ExecutablePin(path)
            pins.append(pin)
            result[name] = dict(pin.fact)
            if name == "systemctl":
                systemctl_pin = pin
        if systemctl_pin is None:
            _fail("systemctl executable pin was not observed")
        for pin in pins:
            pin.verify()
        pins.remove(systemctl_pin)
        return result, systemctl_pin
    finally:
        primary_active = sys.exc_info()[0] is not None
        cleanup_errors: list[BaseException] = []
        for pin in reversed(pins):
            try:
                pin.close()
            except BaseException as error:
                cleanup_errors.append(error)
        if cleanup_errors and not primary_active:
            if systemctl_pin is not None and systemctl_pin not in pins:
                try:
                    systemctl_pin.close()
                except BaseException:
                    pass
            raise cleanup_errors[0]


def _kill_reap(process: subprocess.Popen[bytes]) -> None:
    """Best-effort process-group termination and collection; never raise."""

    try:
        alive = process.poll() is None
    except BaseException:
        alive = True
    if alive:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except BaseException:
            try:
                process.kill()
            except BaseException:
                pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except BaseException:
            pass
        try:
            process.wait(timeout=10)
        except BaseException:
            pass
    except BaseException:
        pass


def _close_subprocess_observers(
    selector: selectors.BaseSelector | None,
    process: subprocess.Popen[bytes],
) -> list[BaseException]:
    errors: list[BaseException] = []
    resources: list[Any] = [selector]
    for attribute in ("stdout", "stderr"):
        try:
            resources.append(getattr(process, attribute))
        except BaseException as error:
            errors.append(error)
    for resource in resources:
        if resource is None:
            continue
        try:
            if resource is selector or not resource.closed:
                resource.close()
        except BaseException as error:
            errors.append(error)
    return errors


def _run_systemctl_show(
    pin: _ExecutablePin, *, user: bool = False,
    unit: str = "user@1000.service",
    fields: Sequence[str] = MANAGER_SHOW_FIELDS,
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
        cwd=FIXED_SOURCE_ROOT,
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
        for name, stream in (
            ("stdout", process.stdout), ("stderr", process.stderr)
        ):
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
        try:
            returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            _fail("read-only systemctl exit was not observed")
        pin.verify()
        if returncode != 0 or streams["stderr"]:
            _fail("read-only systemctl show did not close exactly")
        return bytes(streams["stdout"])
    except BaseException:
        _kill_reap(process)
        raise
    finally:
        cleanup_errors = _close_subprocess_observers(selector, process)
        if cleanup_errors and sys.exc_info()[0] is None:
            raise cleanup_errors[0]


def _parse_properties(
    raw: bytes, fields: Sequence[str] = MANAGER_SHOW_FIELDS,
) -> dict[str, str]:
    if not raw.endswith(b"\n") or b"\0" in raw:
        _fail("systemctl properties are not canonical newline text")
    try:
        lines = raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as error:
        raise V42FormalProbeReceiverError("systemctl output is not UTF-8") from error
    result: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            _fail("systemctl property record changed")
        key, value = line.split("=", 1)
        if key in result:
            _fail("systemctl property was duplicated")
        result[key] = value
    if set(result) != set(fields):
        _fail("systemctl property inventory changed")
    return result


def _manager_binding(systemctl_pin: _ExecutablePin) -> dict[str, Any]:
    boot_raw, _ = _stable_virtual_regular(
        Path("/proc/sys/kernel/random/boot_id"), 128
    )
    try:
        boot = boot_raw.decode("ascii", errors="strict").strip()
    except UnicodeError as error:
        raise V42FormalProbeReceiverError("kernel boot ID is not ASCII") from error
    if str(uuid.UUID(boot)) != boot or boot_raw != (boot + "\n").encode("ascii"):
        _fail("kernel boot ID encoding changed")
    linger = Path("/var/lib/systemd/linger/erzhu419")
    linger_raw, linger_state = _stable_regular(linger, 1)
    if (
        linger_raw != b""
        or stat.S_IMODE(linger_state.st_mode) != 0o644
        or linger_state.st_uid != 0
        or linger_state.st_gid != 0
    ):
        _fail("systemd linger authority changed")
    properties = _parse_properties(_run_systemctl_show(systemctl_pin))
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
        "linger_path": str(linger),
        "user_manager_invocation_id": str(uuid.UUID(properties["InvocationID"])),
        "user_manager_main_pid": int(properties["MainPID"]),
        "user_manager_control_group": properties["ControlGroup"],
    }


def _manager_memory_ancestry(control_group: str) -> list[dict[str, Any]]:
    current = PurePosixPath(control_group)
    rows: list[dict[str, Any]] = []
    while True:
        path = str(current)
        directory = Path("/sys/fs/cgroup") / path.lstrip("/")
        maximum_path = directory / "memory.max"
        current_path = directory / "memory.current"
        try:
            maximum_raw, _ = _stable_virtual_regular(maximum_path, 128)
        except FileNotFoundError:
            try:
                current_path.lstat()
            except FileNotFoundError:
                if path != "/":
                    _fail("non-root manager cgroup omitted memory files")
                rows.append(
                    {
                        "cgroup_path": "/",
                        "memory_max_mode": "ROOT_DELEGATED_VIEW_NO_LOCAL_MEMORY_FILES",
                        "memory_max_bytes": None,
                        "memory_current_bytes": None,
                    }
                )
                break
            _fail("manager cgroup memory files are partially present")
        current_raw, _ = _stable_virtual_regular(current_path, 128)
        if maximum_raw == b"max\n":
            mode, maximum = "MAX", None
        else:
            token = maximum_raw[:-1] if maximum_raw.endswith(b"\n") else b""
            if not token.isdigit() or token != str(int(token)).encode("ascii"):
                _fail("manager cgroup memory.max encoding changed")
            mode, maximum = "FINITE", int(token)
        current_token = current_raw[:-1] if current_raw.endswith(b"\n") else b""
        if not current_token.isdigit() or current_token != str(int(current_token)).encode("ascii"):
            _fail("manager cgroup memory.current encoding changed")
        rows.append(
            {
                "cgroup_path": path,
                "memory_max_mode": mode,
                "memory_max_bytes": maximum,
                "memory_current_bytes": int(current_token),
            }
        )
        if path == "/":
            break
        current = current.parent
    return rows


def _resource_observation(manager: Mapping[str, Any]) -> dict[str, Any]:
    # The retained v42r1 observer is itself loaded from the fixed execution
    # source manifest and performs stable no-follow reads of meminfo, cgroup2
    # topology, and the fixed source root.  We project its read-only values but
    # bind limits to the user-manager cgroup that will own the future service.
    attestation = legacy.observe_host_attestation_v42r1(
        FIXED_SOURCE_ROOT,
        transport_target_alias=REMOTE_HOST_ALIAS,
        attestation_stage="PREPARE",
    )
    return {
        "memory_total_bytes": attestation["memory_total_bytes"],
        "memory_available_bytes": attestation["memory_available_bytes"],
        "swap_total_bytes": attestation["swap_total_bytes"],
        "swap_free_bytes": attestation["swap_free_bytes"],
        "filesystem_available_bytes": attestation["filesystem_available_bytes"],
        "cgroup_mount_point": attestation["cgroup_mount_point"],
        "cgroup_mount_filesystem_type": attestation[
            "cgroup_mount_filesystem_type"
        ],
        "cgroup_mount_root": attestation["cgroup_mount_root"],
        "cgroup_controllers": attestation["cgroup_root_controllers"],
        "memory_limit_ancestry": _manager_memory_ancestry(
            str(manager["user_manager_control_group"])
        ),
    }


def _runtime_observation() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "user": pwd.getpwuid(os.geteuid()).pw_name,
        "uid": os.geteuid(),
        "gid": os.getegid(),
        "python_invocation": sys.executable,
        "python_realpath": os.path.realpath(sys.executable),
        "python_version": list(sys.version_info[:3]),
        "python_isolated_flag": sys.flags.isolated,
        "python_no_site_flag": sys.flags.no_site,
        "python_dont_write_bytecode": sys.dont_write_bytecode,
    }


def _verify_fixed_materialization(plan: Mapping[str, Any]) -> None:
    phase = legacy.verify_remote_control_phase_inventory_v42r1(
        "POST_MATERIALIZATION_PREPARE"
    )
    binding = plan.get("native_activation_binding")
    if type(binding) is not dict:
        _fail("native activation binding changed type")
    expected = {
        "source_manifest_id": phase["source_manifest"]["source_manifest_id"],
        "transport_manifest_id": phase["transport_manifest"][
            "transport_manifest_id"
        ],
        "source_commit": phase["source_manifest"]["source_commit"],
        "source_tree": phase["source_manifest"]["source_tree"],
        "local_materialization_attempt_id": phase[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": phase[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": phase["materialization_terminal_id"],
    }
    for field, value in expected.items():
        if binding.get(field) != value:
            _fail("fixed materialization/native binding join changed: " + field)
    if (
        binding.get("fixed_remote_root") != str(FIXED_REMOTE_ROOT)
        or binding.get("fixed_source_root") != str(FIXED_SOURCE_ROOT)
        or binding.get("remote_target_alias") != REMOTE_HOST_ALIAS
    ):
        _fail("fixed materialization path or target binding changed")


def _verify_probe_plan_adapter(
    ingress_raw: bytes, expected_probe_plan_id: str,
) -> dict[str, Any]:
    verifier = getattr(formal, "verify_formal_host_epoch_probe_plan_v42r3", None)
    if not callable(verifier):
        _fail("successor probe plan verifier changed")
    plan = verifier(ingress_raw)
    if (
        type(plan) is not dict
        or plan.get("schema_version") != SCHEMA_VERSION
        or plan.get("formal_host_epoch_probe_plan_id") != expected_probe_plan_id
    ):
        _fail("successor probe plan identity or version changed")
    return plan


def _build_receipt_adapter(
    *, plan: Mapping[str, Any], observed_runtime: Mapping[str, Any],
    manager_binding: Mapping[str, Any], resource_observation: Mapping[str, Any],
    remote_tool_facts: Mapping[str, Any],
    formal_successor_journal_state: str,
) -> dict[str, Any]:
    builder = getattr(formal, "build_formal_host_epoch_receipt_v42r3", None)
    if not callable(builder):
        _fail("successor host epoch receipt builder changed")
    receipt = builder(
        probe_plan=plan,
        observed_runtime=observed_runtime,
        manager_binding=manager_binding,
        resource_observation=resource_observation,
        remote_tool_facts=remote_tool_facts,
        formal_successor_journal_state=formal_successor_journal_state,
    )
    if type(receipt) is not dict:
        _fail("successor host epoch receipt changed type")
    return receipt


def _authority_api(name: str) -> Any:
    value = getattr(formal, name, None)
    if not callable(value):
        _fail("successor authority API is absent: " + name)
    return value


def _verify_transport_plan_adapter(
    value: Mapping[str, Any], expected_plan_id: str,
) -> dict[str, Any]:
    verifier = _authority_api("verify_formal_transport_plan_v42r3")
    plan = verifier(dict(value))
    if (
        type(plan) is not dict
        or plan.get("schema_version") != SCHEMA_VERSION
        or plan.get("formal_transport_plan_id") != expected_plan_id
    ):
        _fail("formal transport plan identity or version changed")
    return plan


def _effect_ingress(
    raw: bytes, *, mode: str, expected_fields: set[str], expected_plan_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    document = _canonical(raw, "formal transport ingress")
    if (
        mode not in INGRESS_SCHEMAS
        or set(document) != {"schema", "schema_version", *expected_fields}
        or document.get("schema") != INGRESS_SCHEMAS[mode]
        or document.get("schema_version") != SCHEMA_VERSION
    ):
        _fail("formal transport ingress schema or version changed")
    plan_value = document.get("formal_transport_plan")
    if type(plan_value) is not dict:
        _fail("formal transport ingress plan changed type")
    return document, _verify_transport_plan_adapter(plan_value, expected_plan_id)


def _join_controller_sources(
    *, plan: Mapping[str, Any], controller_manifest: Mapping[str, Any],
    loader_artifact: Mapping[str, Any], authority_artifact: Mapping[str, Any],
    receiver_artifact: Mapping[str, Any],
) -> None:
    local_stage0_verifier = _authority_api(
        "verify_external_local_stage0_assumption_v42r3"
    )
    ssh_ingress_verifier = _authority_api(
        "verify_external_ssh_ingress_assumption_v42r3"
    )
    local_stage0 = local_stage0_verifier(
        plan.get("external_local_stage0_assumption"),
        controller_source_manifest=dict(controller_manifest),
    )
    ssh_ingress = ssh_ingress_verifier(
        plan.get("external_ssh_ingress_assumption")
    )
    if (
        plan.get("controller_source_manifest_id")
        != controller_manifest.get("controller_source_manifest_id")
        or plan.get("probe_loader_artifact") != loader_artifact
        or plan.get("formal_authority_artifact") != authority_artifact
        or plan.get("probe_receiver_artifact") != receiver_artifact
        or type(local_stage0) is not dict
        or plan.get("external_local_stage0_assumption_id")
        != local_stage0.get("external_local_stage0_assumption_id")
        or type(ssh_ingress) is not dict
        or plan.get("external_ssh_ingress_assumption_id")
        != ssh_ingress.get("external_ssh_ingress_assumption_id")
    ):
        _fail("formal plan/controller source binding changed")


def _cross_version_gate(
    *, plan: Mapping[str, Any], operation: str, legacy_phase: Mapping[str, Any],
    effect_authorized: bool,
) -> dict[str, Any]:
    verifier = _authority_api("verify_cross_version_scientific_state_gate_v42r3")
    gate = verifier(
        formal_transport_plan=dict(plan),
        operation=operation,
        legacy_scientific_phase=dict(legacy_phase),
        effect_authorized=effect_authorized,
    )
    if (
        type(gate) is not dict
        or gate.get("schema_version") != SCHEMA_VERSION
        or gate.get("cross_version_scientific_state_gate_passed") is not True
        or gate.get("effect_authorized") is not effect_authorized
    ):
        _fail("cross-version scientific-state gate did not pass exactly")
    return gate


def _prepare_receipt() -> tuple[dict[str, Any], bytes]:
    history = prereg._freshness()  # noqa: SLF001
    path = legacy.fixed_authority_root_v42(FIXED_SOURCE_ROOT) / legacy.PREPARE_RECEIPT_NAME
    raw, observed = _stable_regular(path, 64 * 1024**2)
    if stat.S_IMODE(observed.st_mode) != 0o400 or observed.st_uid != REMOTE_UID:
        _fail("legacy scientific prepare receipt storage changed")
    receipt = legacy.verify_prepare_receipt_v42(
        raw,
        fresh_terminal_preregistration_id=prereg.PREREGISTRATION_ID,
        history_freshness_manifest_id=history["history_freshness_manifest_id"],
        root=FIXED_SOURCE_ROOT,
        require_live_source=True,
    )
    return receipt, raw


def _expected_tool_facts(plan: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = (
        plan.get("remote_tool_facts"),
        plan.get("host_epoch_receipt", {}).get("remote_tool_facts")
        if type(plan.get("host_epoch_receipt")) is dict
        else None,
        plan.get("native_activation_binding", {}).get("remote_tool_facts")
        if type(plan.get("native_activation_binding")) is dict
        else None,
        plan.get("activation_binding", {}).get("remote_tool_facts")
        if type(plan.get("activation_binding")) is dict
        else None,
    )
    matches = [value for value in candidates if type(value) is dict]
    if (
        not matches
        or any(value != matches[0] for value in matches[1:])
        or set(matches[0]) != set(TOOL_PATHS)
    ):
        _fail("formal plan remote tool facts changed")
    return {key: dict(value) for key, value in matches[0].items()}


def _require_live_host_epoch(
    plan: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Observe the probed boot, user manager, and tool TCB at one boundary.

    This observer is intentionally called at each effect boundary.  A valid
    transport plan proves only what the earlier probe observed; it is not
    evidence that the same boot or user-manager process is still alive now.
    Paired pre/post observations detect drift but do not claim an atomic epoch
    lock across an external exec or systemd operation.
    """

    expected_tools = _expected_tool_facts(plan)
    observed_tools, systemctl_pin = _observe_tool_facts()
    try:
        manager = _manager_binding(systemctl_pin)
    finally:
        systemctl_pin.close()
    expected_receipt = plan.get("host_epoch_receipt")
    expected_manager = (
        expected_receipt.get("manager_binding")
        if type(expected_receipt) is dict
        else None
    )
    if observed_tools != expected_tools or manager != expected_manager:
        _fail("formal effect host epoch or live tool facts changed")
    return observed_tools, manager


class _SourcePin:
    def __init__(self, path: Path, fact: Mapping[str, Any]) -> None:
        self.path = path
        self.descriptor = -1
        try:
            self.descriptor = os.open(
                path, os.O_RDONLY | os.O_NOCTTY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            observed = os.fstat(self.descriptor)
            named = path.lstat()
            if (
                not stat.S_ISREG(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o444
                or observed.st_uid != REMOTE_UID
                or observed.st_gid != REMOTE_GID
                or observed.st_nlink != 1
                or (observed.st_dev, observed.st_ino)
                != (named.st_dev, named.st_ino)
                or observed.st_size != fact.get("byte_count")
            ):
                _fail("manifested scientific runner source identity changed")
            self.state = _stable_state(observed)
            self.byte_count = observed.st_size
            self.sha256 = str(fact.get("sha256"))
            digest = hashlib.sha256()
            remaining = observed.st_size
            while remaining:
                chunk = os.read(self.descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    _fail("manifested scientific runner source ended early")
                digest.update(chunk)
                remaining -= len(chunk)
            if os.read(self.descriptor, 1) or digest.hexdigest() != self.sha256:
                _fail("manifested scientific runner source bytes changed")
            self.verify()
        except BaseException:
            try:
                self.close()
            except BaseException:
                pass
            raise

    def verify(self) -> None:
        if self.descriptor < 0:
            _fail("scientific runner source pin is closed")
        opened = os.fstat(self.descriptor)
        named = self.path.lstat()
        if _stable_state(opened) != self.state or _stable_state(named) != self.state:
            _fail("scientific runner source changed while pinned")

    def close(self) -> None:
        descriptor = getattr(self, "descriptor", -1)
        self.descriptor = -1
        if descriptor >= 0:
            os.close(descriptor)


def _scientific_runner_fact(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    matches = [
        row
        for row in source_manifest.get("source_facts", [])
        if type(row) is dict
        and row.get("relative_path")
        == "scripts/run_v42_standard_2048_remote_ordinal2.py"
    ]
    if len(matches) != 1:
        _fail("scientific runner source fact is absent or ambiguous")
    return dict(matches[0])


def _exec_scientific_runner(
    *, plan: Mapping[str, Any], source_manifest: Mapping[str, Any],
    loader_source_raw: bytes, runner_role: str,
    cross_version_gate: Mapping[str, Any],
    live_tool_facts: Mapping[str, Mapping[str, Any]],
) -> NoReturn:
    if runner_role not in {"PREPARE_SSH", "LAUNCH_SERVICE"}:
        _fail("scientific runner stdio role changed")
    legacy.verify_live_source_matches_manifest_v42(FIXED_SOURCE_ROOT, dict(source_manifest))
    runner_path = FIXED_SOURCE_ROOT / "scripts/run_v42_standard_2048_remote_ordinal2.py"
    runner_pin = _SourcePin(runner_path, _scientific_runner_fact(source_manifest))
    python_pin: _ExecutablePin | None = None
    try:
        python_pin = _ExecutablePin(REMOTE_PYTHON_REALPATH)
        runner_pin.verify()
        python_pin.verify()
        expected_tools = _expected_tool_facts(plan)
        if (
            dict(live_tool_facts) != expected_tools
            or python_pin.fact != live_tool_facts.get("python")
        ):
            _fail("scientific exec Python differs from the live epoch gate pin")
        flags = fcntl.fcntl(runner_pin.descriptor, fcntl.F_GETFD)
        fcntl.fcntl(
            runner_pin.descriptor,
            fcntl.F_SETFD,
            flags & ~fcntl.FD_CLOEXEC,
        )
        targets = tuple(
            os.readlink("/proc/self/fd/" + str(descriptor))
            for descriptor in (0, 1, 2)
        )
        stdout = os.fstat(1)
        loader_sha = hashlib.sha256(loader_source_raw).hexdigest()
        loader_mode = (
            "--scientific-prepare-fd-v42r3"
            if runner_role == "PREPARE_SSH"
            else "--scientific-launch-fd-v42r3"
        )
        gate_ids = [
            value
            for key, value in cross_version_gate.items()
            if key.endswith("_gate_id")
            and type(value) is str
            and re.fullmatch(r"[0-9a-f]{64}", value) is not None
        ]
        if len(gate_ids) != 1:
            _fail("cross-version scientific-state gate identity changed")
        argv = (
            REMOTE_PYTHON,
            "-I", "-S", "-B", "-c", loader_source_raw.decode("utf-8", errors="strict"),
            loader_mode,
            loader_sha,
            str(len(loader_source_raw)),
            str(runner_pin.descriptor),
            runner_pin.sha256,
            str(runner_pin.byte_count),
            str(plan["legacy_execution_source_manifest_id"]),
            *targets,
            str(stdout.st_dev),
            str(stdout.st_ino),
            str(stdout.st_mode),
            str(stdout.st_rdev),
            gate_ids[0],
        )
        environment = (
            {"LC_CTYPE": "C.UTF-8"}
            if runner_role == "PREPARE_SSH"
            else dict(FORMAL_SERVICE_ENVIRONMENT)
        )
        latest_tools, _latest_manager = _require_live_host_epoch(plan)
        runner_pin.verify()
        python_pin.verify()
        if (
            latest_tools != dict(live_tool_facts)
            or python_pin.fact != latest_tools["python"]
        ):
            _fail("scientific exec epoch changed after source preparation")
        os.execve("/proc/self/fd/" + str(python_pin.descriptor), argv, environment)
        _fail("scientific runner FD exec returned")
    except BaseException:
        for pin in (python_pin, runner_pin):
            if pin is not None:
                try:
                    pin.close()
                except BaseException:
                    pass
        raise


def _write_stdout(document: Mapping[str, Any]) -> int:
    sys.stdout.buffer.write(canonical_json_bytes(dict(document)) + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _run_pinned_command(
    *, pin: _ExecutablePin, argv: Sequence[str], environment: Mapping[str, str],
    stdout_cap: int, stderr_cap: int, timeout_seconds: float,
) -> tuple[int, bytes, bytes]:
    pin.verify()
    process = subprocess.Popen(
        tuple(argv),
        executable="/proc/self/fd/" + str(pin.descriptor),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=FIXED_SOURCE_ROOT,
        env=dict(environment),
        close_fds=True,
        pass_fds=(pin.descriptor,),
        start_new_session=True,
    )
    selector: selectors.BaseSelector | None = None
    try:
        if process.stdout is None or process.stderr is None:
            _fail("bounded formal transport pipes were not created")
        selector = selectors.DefaultSelector()
        streams = {"stdout": bytearray(), "stderr": bytearray()}
        caps = {"stdout": stdout_cap, "stderr": stderr_cap}
        for name, stream in (
            ("stdout", process.stdout), ("stderr", process.stderr)
        ):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic() + timeout_seconds
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail("bounded formal transport command timed out")
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
                    _fail("bounded formal transport stream exceeded cap")
        try:
            returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            _fail("bounded formal transport command exit was not observed")
        pin.verify()
        return returncode, bytes(streams["stdout"]), bytes(streams["stderr"])
    except BaseException:
        _kill_reap(process)
        raise
    finally:
        cleanup_errors = _close_subprocess_observers(selector, process)
        if cleanup_errors and sys.exc_info()[0] is None:
            raise cleanup_errors[0]


def _unit_name(attempt_id: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", attempt_id) is None:
        _fail("formal launch attempt ID changed")
    return SYSTEMD_UNIT_PREFIX + attempt_id + ".service"


def _verify_loaded_service_contract(
    unit: Mapping[str, Any], attempt_id: str,
) -> None:
    expected_name = _unit_name(attempt_id)
    if (
        unit.get("Id") != expected_name
        or unit.get("Type") != "exec"
        or unit.get("Restart") != "no"
        or unit.get("RemainAfterExit") != "yes"
        or unit.get("SuccessExitStatus") != "2"
        or unit.get("UMask") != "0077"
        or unit.get("KillMode") != "mixed"
        or unit.get("StandardInput") != "null"
        or unit.get("StandardOutput") != "null"
        or unit.get("StandardError") != "null"
        or unit.get("WorkingDirectory") != str(FIXED_SOURCE_ROOT)
        or unit.get("FragmentPath")
        != "/run/user/1000/systemd/transient/" + expected_name
        or unit.get("Environment") != ""
        or type(unit.get("Slice")) is not str
        or re.fullmatch(r"[A-Za-z0-9_.@\-]+\.slice", unit["Slice"]) is None
    ):
        _fail("loaded formal successor service contract changed")


def _unit_observation(
    systemctl_pin: _ExecutablePin, attempt_id: str,
) -> dict[str, Any]:
    unit_name = _unit_name(attempt_id)
    properties = _parse_properties(
        _run_systemctl_show(
            systemctl_pin, user=True, unit=unit_name, fields=UNIT_SHOW_FIELDS
        ),
        UNIT_SHOW_FIELDS,
    )
    result: dict[str, Any] = dict(properties)
    try:
        result["MainPID"] = int(properties["MainPID"])
    except ValueError as error:
        raise V42FormalProbeReceiverError("unit MainPID is not decimal") from error
    if properties["InvocationID"]:
        if _INVOCATION32.fullmatch(properties["InvocationID"]) is None:
            _fail("unit InvocationID changed")
        result["InvocationID"] = str(uuid.UUID(properties["InvocationID"]))
    result.pop("ExecStart")
    if result["LoadState"] == "loaded" and result["MainPID"] > 1:
        pid = result["MainPID"]
        cmdline, _ = _stable_virtual_regular(
            Path("/proc") / str(pid) / "cmdline", 1024**2
        )
        if not cmdline or not cmdline.endswith(b"\0") or b"\0\0" in cmdline:
            _fail("formal unit MainPID cmdline changed encoding")
        result["LiveMainPIDArgv"] = [
            item.decode("utf-8", errors="strict")
            for item in cmdline[:-1].split(b"\0")
        ]
        cgroup_raw, _ = _stable_virtual_regular(
            Path("/proc") / str(pid) / "cgroup", 64 * 1024
        )
        if cgroup_raw != ("0::" + result["ControlGroup"] + "\n").encode("ascii"):
            _fail("formal unit MainPID cgroup/systemctl join changed")
        result["LiveMainPIDArgvSource"] = "PROC_MAINPID_CMDLINE"
    else:
        result["LiveMainPIDArgv"] = []
        result["LiveMainPIDArgvSource"] = (
            "UNAVAILABLE_NO_MAINPID"
            if result["LoadState"] == "loaded"
            else "ABSENT_UNIT"
        )
    if result["LoadState"] == "loaded":
        _verify_loaded_service_contract(result, attempt_id)
    return result


def _service_loader_argv(
    *, mode: str, plan: Mapping[str, Any], controller_raw: bytes,
    loader_raw: bytes, authority_raw: bytes, receiver_raw: bytes,
    plan_raw: bytes, attempt_id: str, runtime_invocation_id: str | None = None,
    runtime_control_group: str | None = None,
) -> tuple[str, ...]:
    if mode not in {SERVICE_BOOTSTRAP_MODE, SERVICE_WRAPPER_MODE}:
        _fail("formal service loader mode changed")
    result = (
        REMOTE_PYTHON,
        "-I", "-S", "-B", "-c", loader_raw.decode("utf-8", errors="strict"),
        mode,
        hashlib.sha256(loader_raw).hexdigest(), str(len(loader_raw)),
        hashlib.sha256(controller_raw).hexdigest(), str(len(controller_raw)),
        hashlib.sha256(authority_raw).hexdigest(), str(len(authority_raw)),
        hashlib.sha256(receiver_raw).hexdigest(), str(len(receiver_raw)),
        hashlib.sha256(plan_raw).hexdigest(), str(len(plan_raw)),
        str(plan["formal_transport_plan_id"]),
        str(plan["legacy_execution_source_manifest_id"]),
        attempt_id,
    )
    if mode == SERVICE_BOOTSTRAP_MODE:
        if runtime_invocation_id is not None or runtime_control_group is not None:
            _fail("formal bootstrap unexpectedly received runtime identity")
        return result
    if (
        type(runtime_invocation_id) is not str
        or str(uuid.UUID(runtime_invocation_id)) != runtime_invocation_id
        or type(runtime_control_group) is not str
        or _CGROUP.fullmatch(runtime_control_group) is None
    ):
        _fail("formal clean wrapper runtime identity changed")
    return (*result, runtime_invocation_id, runtime_control_group)


def _verify_systemd_run_argv(
    argv: object, attempt_id: str, service_bootstrap_argv: Sequence[str],
) -> tuple[str, ...]:
    if (
        type(argv) not in {list, tuple}
        or not argv
        or any(type(value) is not str or not value for value in argv)
    ):
        _fail("formal systemd-run argv changed type")
    result = tuple(argv)
    try:
        separator = result.index("--")
    except ValueError:
        _fail("formal systemd-run command separator is absent")
    options = result[1:separator]
    expected_bootstrap = tuple(service_bootstrap_argv)
    fixed_options = {
        "--user",
        "--quiet",
        "--no-ask-password",
        "--service-type=exec",
        "--property=Restart=no",
        "--property=RemainAfterExit=yes",
        "--property=SuccessExitStatus=2",
        "--property=UMask=0077",
        "--property=KillMode=mixed",
        "--property=StandardInput=null",
        "--property=StandardOutput=null",
        "--property=StandardError=null",
    }
    variable_patterns = (
        re.compile(r"--unit=" + re.escape(_unit_name(attempt_id))),
        re.compile(r"--slice=[A-Za-z0-9_.@\\-]+\.slice"),
        re.compile(r"--property=TimeoutStopSec=[1-9][0-9]*s"),
        re.compile(r"--property=RuntimeMaxSec=[1-9][0-9]*s"),
        re.compile(r"--working-directory=" + re.escape(str(FIXED_SOURCE_ROOT))),
    )
    option_inventory_exact = (
        len(options) == len(fixed_options) + len(variable_patterns)
        and len(set(options)) == len(options)
        and fixed_options <= set(options)
        and all(
            sum(pattern.fullmatch(option) is not None for option in options) == 1
            for pattern in variable_patterns
        )
    )
    forbidden = {
        option
        for option in result
        if option in FORBIDDEN_SYSTEMD_OPTIONS
        or any(option.startswith(prefix + "=") for prefix in FORBIDDEN_SYSTEMD_OPTIONS)
        or "bindsto" in option.lower().replace("-", "")
    }
    if (
        result[0] != TOOL_PATHS["systemd_run"]
        or "--user" not in result
        or "--service-type=exec" not in result
        or "--unit=" + _unit_name(attempt_id) not in result
        or forbidden
        or result.count("--") != 1
        or not option_inventory_exact
        or result[separator + 1 :] != expected_bootstrap
        or not {
            "--property=StandardInput=null",
            "--property=StandardOutput=null",
            "--property=StandardError=null",
            "--property=Restart=no",
        } <= set(result)
    ):
        _fail("formal systemd-run safety contract changed")
    return result


def _live_descriptors() -> list[int]:
    result: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        if not name.isdigit():
            _fail("formal service descriptor name changed")
        descriptor = int(name)
        try:
            fcntl.fcntl(descriptor, fcntl.F_GETFD)
        except OSError as error:
            if error.errno == errno.EBADF:
                continue
            raise
        result.append(descriptor)
    return sorted(result)


def _null_stdio_facts() -> list[dict[str, Any]]:
    null = os.stat("/dev/null", follow_symlinks=False)
    result: list[dict[str, Any]] = []
    for descriptor in (0, 1, 2):
        observed = os.fstat(descriptor)
        target = os.readlink("/proc/self/fd/" + str(descriptor))
        if (
            not stat.S_ISCHR(observed.st_mode)
            or observed.st_rdev != null.st_rdev
            or target != "/dev/null"
            or os.isatty(descriptor)
        ):
            _fail("formal service stdio is not exact /dev/null")
        result.append(
            {
                "descriptor": descriptor,
                "target": target,
                "node_type": "CHARACTER_DEVICE",
                "isatty": False,
            }
        )
    return result


def _self_cgroup() -> str:
    raw, _ = _stable_virtual_regular(Path("/proc/self/cgroup"), 64 * 1024)
    if not raw.startswith(b"0::") or raw.count(b"\n") != 1 or not raw.endswith(b"\n"):
        _fail("formal service cgroup membership changed")
    return raw[3:-1].decode("ascii", errors="strict")


def _prepare_once(
    *, ingress_raw: bytes, expected_plan_id: str,
    controller_manifest: Mapping[str, Any], loader_artifact: Mapping[str, Any],
    authority_artifact: Mapping[str, Any], receiver_artifact: Mapping[str, Any],
    loader_source_raw: bytes,
) -> int:
    document, plan = _effect_ingress(
        ingress_raw,
        mode=PREPARE_MODE,
        expected_fields={"formal_transport_plan", "formal_prepare_attempt"},
        expected_plan_id=expected_plan_id,
    )
    _join_controller_sources(
        plan=plan,
        controller_manifest=controller_manifest,
        loader_artifact=loader_artifact,
        authority_artifact=authority_artifact,
        receiver_artifact=receiver_artifact,
    )
    _authority_api("verify_formal_prepare_attempt_v42r3")(
        document["formal_prepare_attempt"], formal_transport_plan=plan
    )
    _verify_fixed_materialization(plan)
    phase = legacy.verify_remote_control_phase_inventory_v42r1(
        "POST_MATERIALIZATION_PREPARE"
    )
    gate = _cross_version_gate(
        plan=plan, operation="PREPARE", legacy_phase=phase,
        effect_authorized=True,
    )
    try:
        REMOTE_V42R3_JOURNAL_ROOT.lstat()
    except FileNotFoundError:
        pass
    else:
        _fail("formal successor state already exists; inspect without replay")
    if any(os.isatty(descriptor) for descriptor in (0, 1, 2)):
        _fail("formal prepare stdio is not a non-TTY SSH channel")
    if os.readlink("/proc/self/fd/1") == "/dev/null":
        _fail("formal prepare stdout was not preserved")
    # Last read-only gate before replacing this process with the scientific
    # prepare runner.  A stale probe receipt can never authorize this exec.
    live_tools, _manager = _require_live_host_epoch(plan)
    _exec_scientific_runner(
        plan=plan,
        source_manifest=phase["source_manifest"],
        loader_source_raw=loader_source_raw,
        runner_role="PREPARE_SSH",
        cross_version_gate=gate,
        live_tool_facts=live_tools,
    )


def _path_state(path: Path) -> str:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    if stat.S_ISREG(observed.st_mode):
        return "REGULAR_FILE"
    if stat.S_ISDIR(observed.st_mode):
        return "DIRECTORY"
    return "NONREGULAR"


class _FormalJournalPin:
    """A no-follow capability for one journal inode and its complete ancestry.

    Every component is opened relative to its already-held parent.  Reads and
    inventory observations then use only the journal descriptor.  ``verify``
    proves that every parent still resolves the component name to the same
    held inode, detecting rename/replacement at both ends of each operation
    after the capability is acquired.  Because mkdirat cannot atomically
    return a directory FD, noninterference during the creation-to-open edge is
    an explicit external remote-path premise rather than a local proof.
    """

    def __init__(
        self,
        path: Path,
        chain: list[tuple[int, str | None, tuple[int, ...]]],
    ) -> None:
        self.path = path
        self.chain = chain

    @classmethod
    def create(cls) -> "_FormalJournalPin":
        """Create and immediately pin the one-shot journal via its parent FD."""

        path = Path(REMOTE_V42R3_JOURNAL_ROOT)
        if (
            not path.is_absolute()
            or ".." in path.parts
            or "\x00" in os.fspath(path)
            or path == Path("/")
        ):
            _fail("formal successor journal root path changed")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open("/", flags)
        chain: list[tuple[int, str | None, tuple[int, ...]]] = []
        created = False
        try:
            chain.append(
                (descriptor, None, _directory_identity(os.fstat(descriptor)))
            )
            for component in path.parent.parts[1:]:
                named = os.stat(
                    component, dir_fd=descriptor, follow_symlinks=False
                )
                if not stat.S_ISDIR(named.st_mode):
                    _fail("formal successor journal parent is not a directory")
                child = os.open(component, flags, dir_fd=descriptor)
                try:
                    opened = os.fstat(child)
                except BaseException:
                    try:
                        os.close(child)
                    except BaseException:
                        pass
                    raise
                if _directory_identity(named) != _directory_identity(opened):
                    try:
                        os.close(child)
                    except BaseException:
                        pass
                    _fail("formal successor journal parent changed while opening")
                chain.append((child, component, _directory_identity(opened)))
                descriptor = child
            try:
                processio.create_one_shot_root_at(descriptor, path.name)
                created = True
            except processio.V42RemoteOrdinal2ProcessError as error:
                raise V42FormalProbeReceiverError(
                    "formal successor journal already exists or cannot be created"
                ) from error
            named = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
            child = os.open(path.name, flags, dir_fd=descriptor)
            try:
                opened = os.fstat(child)
            except BaseException:
                try:
                    os.close(child)
                except BaseException:
                    pass
                raise
            identity = _directory_identity(opened)
            if (
                _directory_identity(named) != identity
                or not stat.S_ISDIR(opened.st_mode)
                or stat.S_IMODE(opened.st_mode) != 0o700
                or opened.st_uid != REMOTE_UID
                or opened.st_gid != REMOTE_GID
                or opened.st_nlink != 2
            ):
                try:
                    os.close(child)
                except BaseException:
                    pass
                _fail("created formal successor journal authority changed")
            chain.append((child, path.name, identity))
            os.fsync(child)
            os.fsync(descriptor)
            result = cls(path, chain)
            result.verify()
            return result
        except BaseException as error:
            for opened, _name, _identity in reversed(chain):
                try:
                    os.close(opened)
                except BaseException:
                    pass
            if isinstance(error, V42FormalProbeReceiverError):
                raise
            message = (
                "formal successor journal creation failed after its durable marker"
                if created
                else "formal successor journal root cannot be created"
            )
            raise V42FormalProbeReceiverError(message) from error

    @classmethod
    def open(cls) -> "_FormalJournalPin":
        path = Path(REMOTE_V42R3_JOURNAL_ROOT)
        if (
            not path.is_absolute()
            or ".." in path.parts
            or "\x00" in os.fspath(path)
            or path == Path("/")
        ):
            _fail("formal successor journal root path changed")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open("/", flags)
        try:
            root_identity = _directory_identity(os.fstat(descriptor))
        except BaseException:
            try:
                os.close(descriptor)
            except BaseException:
                pass
            raise
        chain = [(descriptor, None, root_identity)]
        try:
            for component in path.parts[1:]:
                named = os.stat(
                    component, dir_fd=descriptor, follow_symlinks=False
                )
                if not stat.S_ISDIR(named.st_mode):
                    _fail("formal successor journal ancestry is not a directory")
                child = os.open(component, flags, dir_fd=descriptor)
                try:
                    opened = os.fstat(child)
                except BaseException:
                    try:
                        os.close(child)
                    except BaseException:
                        pass
                    raise
                if _directory_identity(named) != _directory_identity(opened):
                    try:
                        os.close(child)
                    except BaseException:
                        pass
                    _fail("formal successor journal ancestry changed while opening")
                chain.append(
                    (child, component, _directory_identity(opened))
                )
                descriptor = child
            root = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(root.st_mode)
                or stat.S_IMODE(root.st_mode) != 0o700
                or root.st_uid != REMOTE_UID
                or root.st_gid != REMOTE_GID
                or root.st_nlink != 2
            ):
                _fail("formal successor journal root authority changed")
            result = cls(path, chain)
            result.verify()
            return result
        except BaseException:
            for opened, _name, _identity in reversed(chain):
                try:
                    os.close(opened)
                except BaseException:
                    pass
            raise

    @classmethod
    def open_optional(cls) -> "_FormalJournalPin | None":
        try:
            return cls.open()
        except FileNotFoundError:
            cls._verify_stable_absence()
            return None
        except OSError as error:
            raise V42FormalProbeReceiverError(
                "formal successor journal root cannot be pinned"
            ) from error

    @classmethod
    def _verify_stable_absence(cls) -> None:
        """Bracket an absent final name with a pinned no-follow parent chain."""

        path = Path(REMOTE_V42R3_JOURNAL_ROOT)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open("/", flags)
        chain: list[tuple[int, str | None, tuple[int, ...]]] = []
        try:
            chain.append(
                (descriptor, None, _directory_identity(os.fstat(descriptor)))
            )
            for component in path.parent.parts[1:]:
                named = os.stat(
                    component, dir_fd=descriptor, follow_symlinks=False
                )
                if not stat.S_ISDIR(named.st_mode):
                    _fail("formal successor journal parent is not a directory")
                child = os.open(component, flags, dir_fd=descriptor)
                try:
                    opened = os.fstat(child)
                except BaseException:
                    try:
                        os.close(child)
                    except BaseException:
                        pass
                    raise
                if _directory_identity(named) != _directory_identity(opened):
                    try:
                        os.close(child)
                    except BaseException:
                        pass
                    _fail("formal successor journal parent changed while opening")
                chain.append((child, component, _directory_identity(opened)))
                descriptor = child

            def verify_parent_chain() -> None:
                for index, (opened_fd, name, identity) in enumerate(chain):
                    if _directory_identity(os.fstat(opened_fd)) != identity:
                        _fail("held formal successor journal parent changed")
                    if index:
                        if name is None:
                            _fail("formal successor journal parent name changed")
                        named = os.stat(
                            name,
                            dir_fd=chain[index - 1][0],
                            follow_symlinks=False,
                        )
                        if _directory_identity(named) != identity:
                            _fail("named formal successor journal parent changed")

            for _observation in range(2):
                verify_parent_chain()
                try:
                    os.stat(
                        path.name,
                        dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    pass
                else:
                    _fail("formal successor journal appeared during observation")
                verify_parent_chain()
        except OSError as error:
            raise V42FormalProbeReceiverError(
                "formal successor journal absence cannot be pinned"
            ) from error
        finally:
            for opened, _name, _identity in reversed(chain):
                try:
                    os.close(opened)
                except BaseException:
                    pass
            if not chain:
                try:
                    os.close(descriptor)
                except BaseException:
                    pass

    @classmethod
    def open_required(cls) -> "_FormalJournalPin":
        result = cls.open_optional()
        if result is None:
            _fail("formal successor journal is absent")
        return result

    @property
    def descriptor(self) -> int:
        if not self.chain:
            _fail("formal successor journal pin is closed")
        return self.chain[-1][0]

    def verify(self) -> None:
        if not self.chain:
            _fail("formal successor journal pin is closed")
        for index, (descriptor, name, identity) in enumerate(self.chain):
            try:
                opened = os.fstat(descriptor)
            except OSError as error:
                raise V42FormalProbeReceiverError(
                    "held formal successor journal ancestry is unavailable"
                ) from error
            if _directory_identity(opened) != identity:
                _fail("held formal successor journal ancestry changed")
            if index == len(self.chain) - 1 and (
                not stat.S_ISDIR(opened.st_mode)
                or stat.S_IMODE(opened.st_mode) != 0o700
                or opened.st_uid != REMOTE_UID
                or opened.st_gid != REMOTE_GID
                or opened.st_nlink != 2
            ):
                _fail("held formal successor journal authority changed")
            if index:
                if name is None:
                    _fail("formal successor journal ancestry name changed")
                try:
                    named = os.stat(
                        name,
                        dir_fd=self.chain[index - 1][0],
                        follow_symlinks=False,
                    )
                except OSError as error:
                    raise V42FormalProbeReceiverError(
                        "named formal successor journal ancestry changed"
                    ) from error
                if _directory_identity(named) != identity:
                    _fail("named formal successor journal ancestry changed")

    @staticmethod
    def _validate_name(name: str) -> None:
        if (
            type(name) is not str
            or not name
            or name in {".", ".."}
            or "/" in name
            or "\x00" in name
        ):
            _fail("formal successor journal artifact name changed")

    def inventory(self) -> frozenset[str]:
        self.verify()
        before = frozenset(os.listdir(self.descriptor))
        self.verify()
        after = frozenset(os.listdir(self.descriptor))
        self.verify()
        initial = frozenset(REMOTE_JOURNAL_INITIAL_INVENTORY)
        allowed = initial | {
            REMOTE_ADMISSION_NAME,
            REMOTE_WRAPPER_ATTESTATION_NAME,
        }
        if (
            before != after
            or not initial <= before
            or not before <= allowed
            or REMOTE_WRAPPER_ATTESTATION_NAME in before
            and REMOTE_ADMISSION_NAME not in before
        ):
            _fail("formal successor journal inventory changed")
        return before

    def read(self, name: str) -> bytes:
        self._validate_name(name)
        self.verify()
        named = os.stat(
            name, dir_fd=self.descriptor, follow_symlinks=False
        )
        descriptor = os.open(
            name,
            os.O_RDONLY
            | os.O_NONBLOCK
            | os.O_NOCTTY
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
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
                or (before.st_dev, before.st_ino)
                != (named.st_dev, named.st_ino)
            ):
                _fail(
                    "formal successor journal artifact authority changed: "
                    + name
                )
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    _fail(
                        "formal successor journal artifact ended early: " + name
                    )
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _fail("formal successor journal artifact grew: " + name)
            after = os.fstat(descriptor)
        except BaseException:
            try:
                os.close(descriptor)
            except BaseException:
                pass
            raise
        os.close(descriptor)
        final = os.stat(
            name, dir_fd=self.descriptor, follow_symlinks=False
        )
        if (
            _stable_state(before) != _stable_state(after)
            or _stable_state(after) != _stable_state(final)
        ):
            _fail("formal successor journal artifact changed: " + name)
        self.verify()
        return b"".join(chunks)

    def entry_state(self, name: str) -> str:
        self._validate_name(name)
        self.verify()
        try:
            observed = os.stat(
                name, dir_fd=self.descriptor, follow_symlinks=False
            )
        except FileNotFoundError:
            self.verify()
            return "ABSENT"
        self.verify()
        if stat.S_ISREG(observed.st_mode):
            return "REGULAR_FILE"
        if stat.S_ISDIR(observed.st_mode):
            return "DIRECTORY"
        return "NONREGULAR"

    def write_once(self, name: str, raw: bytes) -> None:
        self._validate_name(name)
        if type(raw) is not bytes:
            _fail("formal successor journal publication bytes changed")
        self.verify()
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o400,
            dir_fd=self.descriptor,
        )
        try:
            os.fchmod(descriptor, 0o400)
            written = 0
            while written < len(raw):
                count = os.write(descriptor, raw[written:])
                if count <= 0:
                    _fail("formal successor journal publication ended early")
                written += count
            os.fsync(descriptor)
            observed = os.fstat(descriptor)
            if (
                not stat.S_ISREG(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o400
                or observed.st_uid != REMOTE_UID
                or observed.st_gid != REMOTE_GID
                or observed.st_nlink != 1
                or observed.st_size != len(raw)
            ):
                _fail("formal successor journal publication authority changed")
        except BaseException:
            try:
                os.close(descriptor)
            except BaseException:
                pass
            raise
        os.close(descriptor)
        named = os.stat(
            name, dir_fd=self.descriptor, follow_symlinks=False
        )
        if _stable_state(named) != _stable_state(observed):
            _fail("formal successor journal publication identity changed")
        os.fsync(self.descriptor)
        self.verify()

    def close(self) -> None:
        chain = self.chain
        self.chain = []
        errors: list[BaseException] = []
        for descriptor, _name, _identity in reversed(chain):
            try:
                os.close(descriptor)
            except BaseException as error:
                errors.append(error)
        if errors:
            raise errors[0]

    def __enter__(self) -> "_FormalJournalPin":
        return self

    def __exit__(self, exception_type: object, _value: object, _traceback: object) -> bool:
        try:
            self.close()
        except BaseException:
            if exception_type is None:
                raise
        return False


def _formal_successor_journal_state() -> str:
    """Observe the journal root as absent or an exact pinned directory."""

    pin = _FormalJournalPin.open_optional()
    if pin is None:
        return "ABSENT"
    with pin:
        pin.verify()
    return "DIRECTORY"


def _stable_formal_journal_artifact(
    name: str, journal_pin: _FormalJournalPin | None = None,
) -> bytes:
    if journal_pin is not None:
        return journal_pin.read(name)
    with _FormalJournalPin.open_required() as owned_pin:
        return owned_pin.read(name)


def _stable_verified_formal_journal_source(
    name: str,
    fact: Mapping[str, Any],
    label: str,
    journal_pin: _FormalJournalPin | None = None,
) -> bytes:
    raw = _stable_formal_journal_artifact(name, journal_pin)
    _verify_transported_source(raw, fact, "persisted " + label)
    return raw


def _formal_successor_journal_inventory(
    journal_pin: _FormalJournalPin | None = None,
) -> frozenset[str]:
    if journal_pin is not None:
        return journal_pin.inventory()
    with _FormalJournalPin.open_required() as owned_pin:
        return owned_pin.inventory()


def _current_legacy_scientific_phase(
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Verify exactly the furthest durable legacy scientific phase.

    Inspect modes may be called after prepare, after local launch admission, or
    after the scientific service has begun.  Phase selection is based only on
    no-follow lexical observations; the selected legacy verifier then requires
    the complete exact inventory.  A present-but-invalid document therefore
    fails closed instead of being misreported as absent.
    """

    receipt_path = (
        legacy.fixed_authority_root_v42(FIXED_SOURCE_ROOT)
        / legacy.PREPARE_RECEIPT_NAME
    )
    receipt_state = _path_state(receipt_path)
    if receipt_state == "ABSENT":
        return None, legacy.verify_remote_control_phase_inventory_v42r1(
            "POST_MATERIALIZATION_PREPARE"
        )
    if receipt_state != "REGULAR_FILE":
        _fail("legacy scientific prepare receipt is nonregular")
    receipt, _raw = _prepare_receipt()
    local_state = _path_state(FIXED_REMOTE_ROOT / legacy.LOCAL_LAUNCH_ATTEMPT_NAME)
    launch_host_state = _path_state(
        FIXED_REMOTE_ROOT / legacy.LAUNCH_HOST_ATTESTATION_NAME
    )
    if launch_host_state == "REGULAR_FILE":
        phase_name = "POST_LAUNCH"
    elif launch_host_state != "ABSENT":
        _fail("legacy scientific launch host attestation is nonregular")
    elif local_state == "REGULAR_FILE":
        phase_name = "POST_PREPARE_PRELAUNCH"
    elif local_state != "ABSENT":
        _fail("legacy scientific local launch attempt is nonregular")
    else:
        phase_name = "POST_PREPARE_AWAITING_LOCAL_LAUNCH"
    phase = legacy.verify_remote_control_phase_inventory_v42r1(
        phase_name, prepare_receipt=receipt
    )
    return receipt, phase


def _inspect_prepare(
    *, ingress_raw: bytes, expected_plan_id: str,
    controller_manifest: Mapping[str, Any], loader_artifact: Mapping[str, Any],
    authority_artifact: Mapping[str, Any], receiver_artifact: Mapping[str, Any],
) -> int:
    document, plan = _effect_ingress(
        ingress_raw,
        mode=INSPECT_PREPARE_MODE,
        expected_fields={
            "formal_transport_plan", "formal_prepare_attempt_id",
            "inspection_ordinal",
        },
        expected_plan_id=expected_plan_id,
    )
    _join_controller_sources(
        plan=plan,
        controller_manifest=controller_manifest,
        loader_artifact=loader_artifact,
        authority_artifact=authority_artifact,
        receiver_artifact=receiver_artifact,
    )
    attempt_id = document["formal_prepare_attempt_id"]
    if type(attempt_id) is not str or re.fullmatch(r"[0-9a-f]{64}", attempt_id) is None:
        _fail("formal prepare inspection attempt ID changed")
    recovered: dict[str, Any] = {}
    receipt, phase = _current_legacy_scientific_phase()
    if receipt is not None:
        recovered["scientific_prepare_receipt"] = receipt
    _cross_version_gate(
        plan=plan, operation="INSPECT_PREPARE", legacy_phase=phase,
        effect_authorized=False,
    )
    systemctl_pin = _ExecutablePin(TOOL_PATHS["systemctl"])
    try:
        manager = _manager_binding(systemctl_pin)
    finally:
        systemctl_pin.close()
    states = {
        "scientific_prepare_receipt": (
            "REGULAR_FILE" if receipt is not None else "ABSENT"
        ),
        "scientific_prepare_attempt": _path_state(
            FIXED_SOURCE_ROOT / legacy.PREPARE_ATTEMPT_JOURNAL_NAME
        ),
        "scientific_prepare_failure": _path_state(
            FIXED_SOURCE_ROOT / legacy.PREPARE_FAILURE_JOURNAL_NAME
        ),
        "formal_successor_journal": _formal_successor_journal_state(),
    }
    inspection = _authority_api("build_read_only_inspection_v42r3")(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
        inspection_ordinal=document["inspection_ordinal"],
        manager_binding=manager,
        unit_observation=None,
        artifact_states=states,
        recovered_documents=recovered,
    )
    return _write_stdout(inspection)


def _publish_initial_journal(
    *, plan: Mapping[str, Any], controller_manifest: Mapping[str, Any],
    loader_raw: bytes, authority_raw: bytes, receiver_raw: bytes,
    transport_attempt: Mapping[str, Any],
) -> _FormalJournalPin:
    journal_pin = _FormalJournalPin.create()
    publications = (
        (REMOTE_PLAN_NAME, canonical_json_bytes(dict(plan))),
        (REMOTE_CONTROLLER_NAME, canonical_json_bytes(dict(controller_manifest))),
        (REMOTE_LOADER_NAME, loader_raw),
        (REMOTE_AUTHORITY_NAME, authority_raw),
        (REMOTE_RECEIVER_NAME, receiver_raw),
        (REMOTE_TRANSPORT_ATTEMPT_NAME, canonical_json_bytes(dict(transport_attempt))),
    )
    try:
        for name, raw in publications:
            journal_pin.write_once(name, raw)
        if journal_pin.inventory() != frozenset(
            REMOTE_JOURNAL_INITIAL_INVENTORY
        ):
            _fail("formal successor initial journal inventory changed")
        journal_pin.verify()
        return journal_pin
    except BaseException:
        try:
            journal_pin.close()
        except BaseException:
            pass
        raise


def _persisted_service_sources(
    journal_pin: _FormalJournalPin | None = None,
) -> tuple[bytes, bytes, bytes, bytes, bytes]:
    if journal_pin is None:
        with _FormalJournalPin.open_required() as owned_pin:
            return _persisted_service_sources(owned_pin)
    return tuple(
        journal_pin.read(name)
        for name in (
            REMOTE_CONTROLLER_NAME,
            REMOTE_LOADER_NAME,
            REMOTE_AUTHORITY_NAME,
            REMOTE_RECEIVER_NAME,
            REMOTE_PLAN_NAME,
        )
    )  # type: ignore[return-value]


def _await_clean_wrapper(
    *, systemctl_pin: _ExecutablePin, attempt_id: str,
    bootstrap_argv: Sequence[str], wrapper_argv_builder: Any,
) -> dict[str, Any]:
    deadline = time.monotonic() + CLEAN_WRAPPER_TRANSITION_TIMEOUT_SECONDS
    locked: dict[str, Any] | None = None
    while True:
        unit = _unit_observation(systemctl_pin, attempt_id)
        if (
            unit["LoadState"] != "loaded"
            or unit["ActiveState"] not in {"active", "activating"}
            or unit["SubState"] not in {"start", "running"}
            or not unit["InvocationID"]
            or unit["MainPID"] <= 1
            or not unit["ControlGroup"]
        ):
            _fail("formal successor service exited before clean wrapper")
        identity = {
            key: unit[key]
            for key in (
                "Id", "InvocationID", "MainPID", "ControlGroup", "FragmentPath",
                "Type", "Restart", "RemainAfterExit", "SuccessExitStatus", "UMask",
                "KillMode", "TimeoutStopUSec", "RuntimeMaxUSec", "StandardInput",
                "StandardOutput", "StandardError", "WorkingDirectory", "Slice",
                "Environment",
            )
        }
        if locked is None:
            locked = identity
        elif locked != identity:
            _fail("formal successor service identity drifted during clean exec")
        wrapper_argv = list(
            wrapper_argv_builder(unit["InvocationID"], unit["ControlGroup"])
        )
        if unit["LiveMainPIDArgv"] == wrapper_argv:
            return unit
        if unit["LiveMainPIDArgv"] != list(bootstrap_argv):
            _fail("formal successor service entered unauthorized argv")
        if time.monotonic() >= deadline:
            _fail("formal successor service did not reach clean wrapper")
        time.sleep(0.02)


def _admit_launch(
    *, ingress_raw: bytes, expected_plan_id: str,
    controller_manifest: Mapping[str, Any], loader_artifact: Mapping[str, Any],
    authority_artifact: Mapping[str, Any], receiver_artifact: Mapping[str, Any],
    loader_source_raw: bytes, authority_source_raw: bytes,
    receiver_source_raw: bytes,
) -> int:
    document, plan = _effect_ingress(
        ingress_raw,
        mode=ADMIT_MODE,
        expected_fields={
            "formal_transport_plan", "prepare_receipt", "local_launch_attempt",
            "formal_launch_transport_attempt",
        },
        expected_plan_id=expected_plan_id,
    )
    _join_controller_sources(
        plan=plan,
        controller_manifest=controller_manifest,
        loader_artifact=loader_artifact,
        authority_artifact=authority_artifact,
        receiver_artifact=receiver_artifact,
    )
    receipt, receipt_raw = _prepare_receipt()
    if canonical_json_bytes(document["prepare_receipt"]) != receipt_raw:
        _fail("supplied prepare receipt differs from fixed scientific receipt")
    local = legacy.verify_local_launch_attempt_v42r1(
        document["local_launch_attempt"], prepare_receipt=receipt
    )
    attempt = _authority_api("verify_formal_launch_transport_attempt_v42r3")(
        document["formal_launch_transport_attempt"],
        formal_transport_plan=plan,
        prepare_receipt=receipt,
        local_launch_attempt=local,
    )
    if type(attempt) is not dict:
        _fail("formal launch transport attempt changed type")
    attempt_id = local["local_launch_attempt_id"]
    phase = legacy.verify_remote_control_phase_inventory_v42r1(
        "POST_PREPARE_AWAITING_LOCAL_LAUNCH", prepare_receipt=receipt
    )
    _cross_version_gate(
        plan=plan, operation="ADMIT_LAUNCH", legacy_phase=phase,
        effect_authorized=True,
    )
    # The journal is the first durable launch effect.  Detect stale boot,
    # manager, or tool bytes immediately before publication.
    _live_tools, manager = _require_live_host_epoch(plan)
    journal_pin = _publish_initial_journal(
        plan=plan,
        controller_manifest=controller_manifest,
        loader_raw=loader_source_raw,
        authority_raw=authority_source_raw,
        receiver_raw=receiver_source_raw,
        transport_attempt=attempt,
    )
    try:
        # The six V42r3 journal artifacts above are durable before the legacy
        # scientific state machine receives its prelaunch attempt.  Keep the
        # journal capability live through service admission so later durable
        # publications cannot silently target a replacement directory.
        processio.write_once(
            FIXED_REMOTE_ROOT / legacy.LOCAL_LAUNCH_ATTEMPT_NAME,
            canonical_json_bytes(local),
            mode=0o400,
        )
        journal_pin.verify()
        prelaunch_phase = legacy.verify_remote_control_phase_inventory_v42r1(
            "POST_PREPARE_PRELAUNCH", prepare_receipt=receipt
        )
        _cross_version_gate(
            plan=plan, operation="SYSTEMD_ADMISSION",
            legacy_phase=prelaunch_phase, effect_authorized=True,
        )
        controller_raw = canonical_json_bytes(dict(controller_manifest))
        plan_raw = canonical_json_bytes(plan)
        bootstrap_argv = _service_loader_argv(
            mode=SERVICE_BOOTSTRAP_MODE,
            plan=plan,
            controller_raw=controller_raw,
            loader_raw=loader_source_raw,
            authority_raw=authority_source_raw,
            receiver_raw=receiver_source_raw,
            plan_raw=plan_raw,
            attempt_id=attempt_id,
        )
        systemd_argv = _verify_systemd_run_argv(
            _authority_api("build_systemd_run_argv_v42r3")(
                formal_transport_plan=plan,
                local_launch_attempt=local,
                service_bootstrap_argv=bootstrap_argv,
            ),
            attempt_id,
            bootstrap_argv,
        )
        # Publication and service admission are separate irreversible
        # boundaries; a manager restart between them must stop before
        # systemd-run.
        live_tools_before_spawn, manager = _require_live_host_epoch(plan)
        journal_pin.verify()
        systemd_pin = _ExecutablePin(TOOL_PATHS["systemd_run"])
        try:
            if systemd_pin.fact != live_tools_before_spawn["systemd_run"]:
                _fail("formal systemd-run executable differs from plan")
            returncode, stdout, stderr = _run_pinned_command(
                pin=systemd_pin,
                argv=systemd_argv,
                environment=SYSTEMD_CLIENT_ENVIRONMENT,
                stdout_cap=MAX_SYSTEMD_RUN_STREAM,
                stderr_cap=MAX_SYSTEMD_RUN_STREAM,
                timeout_seconds=COMMAND_TIMEOUT_SECONDS,
            )
        finally:
            systemd_pin.close()
        journal_pin.verify()
        if returncode != 0 or stdout or stderr:
            _fail("formal systemd-run admission was not exact quiet success")
        systemctl_pin = _ExecutablePin(TOOL_PATHS["systemctl"])
        try:
            unit = _await_clean_wrapper(
                systemctl_pin=systemctl_pin,
                attempt_id=attempt_id,
                bootstrap_argv=bootstrap_argv,
                wrapper_argv_builder=lambda invocation, cgroup: _service_loader_argv(
                    mode=SERVICE_WRAPPER_MODE,
                    plan=plan,
                    controller_raw=controller_raw,
                    loader_raw=loader_source_raw,
                    authority_raw=authority_source_raw,
                    receiver_raw=receiver_source_raw,
                    plan_raw=plan_raw,
                    attempt_id=attempt_id,
                    runtime_invocation_id=invocation,
                    runtime_control_group=cgroup,
                ),
            )
        finally:
            systemctl_pin.close()
        journal_pin.verify()
        post_spawn_tools, post_spawn_manager = _require_live_host_epoch(plan)
        if (
            post_spawn_tools != live_tools_before_spawn
            or post_spawn_manager != manager
        ):
            _fail("formal launch epoch changed across systemd admission")
        admission = _authority_api("build_launch_admission_receipt_v42r3")(
            formal_transport_plan=plan,
            launch_transport_attempt=attempt,
            manager_binding=manager,
            unit_observation=unit,
            systemd_run_argv=systemd_argv,
        )
        journal_pin.write_once(
            REMOTE_ADMISSION_NAME,
            canonical_json_bytes(admission),
        )
        journal_pin.inventory()
    except BaseException:
        try:
            journal_pin.close()
        except BaseException:
            pass
        raise
    else:
        journal_pin.close()
    return _write_stdout(admission)


def _inspect_launch(
    *, ingress_raw: bytes, expected_plan_id: str,
    controller_manifest: Mapping[str, Any], loader_artifact: Mapping[str, Any],
    authority_artifact: Mapping[str, Any], receiver_artifact: Mapping[str, Any],
) -> int:
    document, plan = _effect_ingress(
        ingress_raw,
        mode=INSPECT_LAUNCH_MODE,
        expected_fields={
            "formal_transport_plan", "local_launch_attempt_id",
            "inspection_ordinal",
        },
        expected_plan_id=expected_plan_id,
    )
    _join_controller_sources(
        plan=plan,
        controller_manifest=controller_manifest,
        loader_artifact=loader_artifact,
        authority_artifact=authority_artifact,
        receiver_artifact=receiver_artifact,
    )
    attempt_id = document["local_launch_attempt_id"]
    if type(attempt_id) is not str or re.fullmatch(r"[0-9a-f]{64}", attempt_id) is None:
        _fail("formal launch inspection attempt ID changed")
    receipt, phase = _current_legacy_scientific_phase()
    _cross_version_gate(
        plan=plan, operation="INSPECT_LAUNCH", legacy_phase=phase,
        effect_authorized=False,
    )
    systemctl_pin = _ExecutablePin(TOOL_PATHS["systemctl"])
    try:
        manager = _manager_binding(systemctl_pin)
        unit = _unit_observation(systemctl_pin, attempt_id)
    finally:
        systemctl_pin.close()
    recovered: dict[str, Any] = {}
    journal_pin = _FormalJournalPin.open_optional()
    if journal_pin is None:
        journal_state = "ABSENT"
        inventory = frozenset()
    else:
        journal_state = "DIRECTORY"
        with journal_pin:
            inventory = journal_pin.inventory()
            persisted_plan_raw = journal_pin.read(REMOTE_PLAN_NAME)
            persisted_controller_raw = journal_pin.read(REMOTE_CONTROLLER_NAME)
            _stable_verified_formal_journal_source(
                REMOTE_LOADER_NAME, loader_artifact, "loader", journal_pin
            )
            _stable_verified_formal_journal_source(
                REMOTE_AUTHORITY_NAME, authority_artifact, "authority", journal_pin
            )
            _stable_verified_formal_journal_source(
                REMOTE_RECEIVER_NAME, receiver_artifact, "receiver", journal_pin
            )
            if (
                persisted_plan_raw != canonical_json_bytes(plan)
                or persisted_controller_raw
                != canonical_json_bytes(dict(controller_manifest))
            ):
                _fail("formal successor persisted plan or controller changed")
            if receipt is None:
                _fail(
                    "formal launch journal exists without scientific prepare authority"
                )
            local_raw, local_observed = _stable_regular(
                FIXED_REMOTE_ROOT / legacy.LOCAL_LAUNCH_ATTEMPT_NAME,
                MAX_JOURNAL_ARTIFACT_BYTES,
            )
            if (
                stat.S_IMODE(local_observed.st_mode) != 0o400
                or local_observed.st_uid != REMOTE_UID
                or local_observed.st_gid != REMOTE_GID
                or local_observed.st_nlink != 1
            ):
                _fail("scientific local launch attempt storage changed")
            local = legacy.verify_local_launch_attempt_v42r1(
                local_raw, prepare_receipt=receipt
            )
            if local.get("local_launch_attempt_id") != attempt_id:
                _fail("inspected launch attempt differs from scientific authority")
            attempt_raw = journal_pin.read(REMOTE_TRANSPORT_ATTEMPT_NAME)
            attempt = _authority_api(
                "verify_formal_launch_transport_attempt_v42r3"
            )(
                attempt_raw,
                formal_transport_plan=plan,
                prepare_receipt=receipt,
                local_launch_attempt=local,
            )
            recovered["launch_transport_attempt"] = attempt
            if REMOTE_ADMISSION_NAME in inventory:
                admission_raw = journal_pin.read(REMOTE_ADMISSION_NAME)
                admission = _authority_api(
                    "verify_launch_admission_receipt_v42r3"
                )(
                    admission_raw,
                    formal_transport_plan=plan,
                    launch_transport_attempt=attempt,
                )
                recovered["launch_admission_receipt"] = admission
            else:
                admission = None
            if REMOTE_WRAPPER_ATTESTATION_NAME in inventory:
                if admission is None:
                    _fail("formal wrapper exists without admission authority")
                wrapper_gate = _cross_version_gate(
                    plan=plan,
                    operation="SERVICE_WRAPPER",
                    legacy_phase={"phase": "POST_PREPARE_PRELAUNCH"},
                    effect_authorized=True,
                )
                wrapper_raw = journal_pin.read(
                    REMOTE_WRAPPER_ATTESTATION_NAME
                )
                recovered["service_wrapper_attestation"] = _authority_api(
                    "verify_service_wrapper_attestation_v42r3"
                )(
                    wrapper_raw,
                    formal_transport_plan=plan,
                    launch_transport_attempt=attempt,
                    launch_admission_receipt=admission,
                    cross_version_scientific_state_gate=wrapper_gate,
                )
            if journal_pin.inventory() != inventory:
                _fail("formal successor journal changed during recovery")
            journal_pin.verify()
    states = {
        "formal_successor_journal": journal_state,
        "launch_transport_attempt": (
            "REGULAR_FILE"
            if REMOTE_TRANSPORT_ATTEMPT_NAME in inventory
            else "ABSENT"
        ),
        "launch_admission_receipt": (
            "REGULAR_FILE" if REMOTE_ADMISSION_NAME in inventory else "ABSENT"
        ),
        "service_wrapper_attestation": (
            "REGULAR_FILE"
            if REMOTE_WRAPPER_ATTESTATION_NAME in inventory
            else "ABSENT"
        ),
        "scientific_launch_attempt": _path_state(
            FIXED_SOURCE_ROOT / legacy.LAUNCH_ATTEMPT_JOURNAL_NAME
        ),
        "scientific_launch_failure": _path_state(
            FIXED_SOURCE_ROOT / legacy.LAUNCH_FAILURE_JOURNAL_NAME
        ),
        "scientific_terminal": _path_state(
            legacy.fixed_evidence_root_v42(FIXED_SOURCE_ROOT) / legacy.TERMINAL_NAME
        ),
    }
    inspection = _authority_api("build_read_only_inspection_v42r3")(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=attempt_id,
        inspection_ordinal=document["inspection_ordinal"],
        manager_binding=manager,
        unit_observation=unit,
        artifact_states=states,
        recovered_documents=recovered,
    )
    return _write_stdout(inspection)


def _service_context(
    *, ingress_raw: bytes, expected_plan_id: str, attempt_id: str,
    controller_manifest: Mapping[str, Any], loader_artifact: Mapping[str, Any],
    authority_artifact: Mapping[str, Any], receiver_artifact: Mapping[str, Any],
    journal_pin: _FormalJournalPin,
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    plan_value = _canonical(ingress_raw, "persisted formal transport plan")
    plan = _verify_transport_plan_adapter(plan_value, expected_plan_id)
    _join_controller_sources(
        plan=plan,
        controller_manifest=controller_manifest,
        loader_artifact=loader_artifact,
        authority_artifact=authority_artifact,
        receiver_artifact=receiver_artifact,
    )
    journal_pin.inventory()
    (
        persisted_controller_raw,
        persisted_loader_raw,
        persisted_authority_raw,
        persisted_receiver_raw,
        persisted_plan_raw,
    ) = _persisted_service_sources(journal_pin)
    if (
        persisted_controller_raw
        != canonical_json_bytes(dict(controller_manifest))
        or persisted_plan_raw != ingress_raw
    ):
        _fail("formal service persisted plan or controller changed")
    _verify_transported_source(
        persisted_loader_raw, loader_artifact, "persisted service loader"
    )
    _verify_transported_source(
        persisted_authority_raw,
        authority_artifact,
        "persisted service authority",
    )
    _verify_transported_source(
        persisted_receiver_raw,
        receiver_artifact,
        "persisted service receiver",
    )
    receipt, _receipt_raw = _prepare_receipt()
    local_raw, local_observed = _stable_regular(
        FIXED_REMOTE_ROOT / legacy.LOCAL_LAUNCH_ATTEMPT_NAME,
        MAX_JOURNAL_ARTIFACT_BYTES,
    )
    if stat.S_IMODE(local_observed.st_mode) != 0o400:
        _fail("scientific local launch attempt storage changed")
    local = legacy.verify_local_launch_attempt_v42r1(
        local_raw, prepare_receipt=receipt
    )
    if local.get("local_launch_attempt_id") != attempt_id:
        _fail("formal service/scientific launch attempt join changed")
    attempt_raw = journal_pin.read(REMOTE_TRANSPORT_ATTEMPT_NAME)
    attempt = _authority_api("verify_formal_launch_transport_attempt_v42r3")(
        attempt_raw,
        formal_transport_plan=plan,
        prepare_receipt=receipt,
        local_launch_attempt=local,
    )
    phase = legacy.verify_remote_control_phase_inventory_v42r1(
        "POST_PREPARE_PRELAUNCH", prepare_receipt=receipt
    )
    journal_pin.verify()
    return plan, receipt, local, attempt, phase


def _service_bootstrap(
    *, ingress_raw: bytes, expected_plan_id: str, attempt_id: str,
    controller_manifest: Mapping[str, Any], loader_artifact: Mapping[str, Any],
    authority_artifact: Mapping[str, Any], receiver_artifact: Mapping[str, Any],
    loader_source_raw: bytes, authority_source_raw: bytes,
    receiver_source_raw: bytes,
) -> NoReturn:
    if _live_descriptors() != [0, 1, 2]:
        _fail("formal bootstrap inherited a non-stdio descriptor")
    _null_stdio_facts()
    with _FormalJournalPin.open_required() as journal_pin:
        plan, _receipt, _local, _attempt, phase = _service_context(
            ingress_raw=ingress_raw,
            expected_plan_id=expected_plan_id,
            attempt_id=attempt_id,
            controller_manifest=controller_manifest,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
            journal_pin=journal_pin,
        )
        journal_pin.verify()
    _cross_version_gate(
        plan=plan, operation="SERVICE_BOOTSTRAP", legacy_phase=phase,
        effect_authorized=True,
    )
    invocation_raw = os.environ.get("INVOCATION_ID")
    if type(invocation_raw) is not str or _INVOCATION32.fullmatch(invocation_raw) is None:
        _fail("formal bootstrap INVOCATION_ID changed")
    invocation = str(uuid.UUID(invocation_raw))
    service_cgroup = _self_cgroup()
    controller_raw = canonical_json_bytes(dict(controller_manifest))
    plan_raw = canonical_json_bytes(plan)
    bootstrap_argv = _service_loader_argv(
        mode=SERVICE_BOOTSTRAP_MODE,
        plan=plan,
        controller_raw=controller_raw,
        loader_raw=loader_source_raw,
        authority_raw=authority_source_raw,
        receiver_raw=receiver_source_raw,
        plan_raw=plan_raw,
        attempt_id=attempt_id,
    )
    systemctl_pin = _ExecutablePin(TOOL_PATHS["systemctl"])
    try:
        unit = _unit_observation(systemctl_pin, attempt_id)
    finally:
        systemctl_pin.close()
    if (
        unit["LoadState"] != "loaded"
        or unit["ActiveState"] != "active"
        or unit["SubState"] not in {"start", "running"}
        or unit["MainPID"] != os.getpid()
        or unit["InvocationID"] != invocation
        or unit["ControlGroup"] != service_cgroup
        or unit["LiveMainPIDArgv"] != list(bootstrap_argv)
    ):
        _fail("formal bootstrap/systemd live identity changed")
    invocation_path = Path(
        "/run/user/1000/systemd/units/invocation:" + _unit_name(attempt_id)
    )
    if not invocation_path.is_symlink() or os.readlink(invocation_path) != invocation_raw:
        _fail("formal bootstrap invocation symlink changed")
    wrapper_argv = _service_loader_argv(
        mode=SERVICE_WRAPPER_MODE,
        plan=plan,
        controller_raw=controller_raw,
        loader_raw=loader_source_raw,
        authority_raw=authority_source_raw,
        receiver_raw=receiver_source_raw,
        plan_raw=plan_raw,
        attempt_id=attempt_id,
        runtime_invocation_id=invocation,
        runtime_control_group=service_cgroup,
    )
    # Clean-wrapper exec is a fresh effect boundary even though systemd
    # created this process.  Recheck the probed epoch immediately beforehand.
    bootstrap_tools, _bootstrap_manager = _require_live_host_epoch(plan)
    python_pin = _ExecutablePin(REMOTE_PYTHON_REALPATH)
    try:
        python_pin.verify()
        if python_pin.fact != bootstrap_tools["python"]:
            _fail("formal clean-wrapper Python differs from the epoch gate pin")
        os.execve(
            "/proc/self/fd/" + str(python_pin.descriptor),
            wrapper_argv,
            dict(FORMAL_SERVICE_ENVIRONMENT),
        )
    except BaseException:
        python_pin.close()
        raise
    raise AssertionError("formal clean-wrapper exec returned")


def _service_wrapper(
    *, ingress_raw: bytes, expected_plan_id: str, attempt_id: str,
    runtime_invocation_id: str, runtime_control_group: str,
    controller_manifest: Mapping[str, Any], loader_artifact: Mapping[str, Any],
    authority_artifact: Mapping[str, Any], receiver_artifact: Mapping[str, Any],
    loader_source_raw: bytes,
) -> int:
    inherited = _live_descriptors()
    if inherited != [0, 1, 2]:
        _fail("formal clean wrapper inherited a non-stdio descriptor")
    stdio = _null_stdio_facts()

    def run_with_journal_pin(journal_pin: _FormalJournalPin) -> int:
        plan, receipt, _local, attempt, phase = _service_context(
            ingress_raw=ingress_raw,
            expected_plan_id=expected_plan_id,
            attempt_id=attempt_id,
            controller_manifest=controller_manifest,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
            journal_pin=journal_pin,
        )
        gate = _cross_version_gate(
            plan=plan, operation="SERVICE_WRAPPER", legacy_phase=phase,
            effect_authorized=True,
        )
        live_tools, manager = _require_live_host_epoch(plan)
        systemctl_pin = _ExecutablePin(TOOL_PATHS["systemctl"])
        try:
            unit = _unit_observation(systemctl_pin, attempt_id)
        finally:
            systemctl_pin.close()
        service_pid = os.getpid()
        service_cgroup = _self_cgroup()
        invocation_path = Path(
            "/run/user/1000/systemd/units/invocation:" + _unit_name(attempt_id)
        )
        if not invocation_path.is_symlink():
            _fail("formal service invocation symlink is absent")
        invocation_raw = os.readlink(invocation_path)
        if _INVOCATION32.fullmatch(invocation_raw) is None:
            _fail("formal service invocation symlink changed")
        invocation = str(uuid.UUID(invocation_raw))
        if (
            unit["MainPID"] != service_pid
            or unit["ControlGroup"] != service_cgroup
            or unit["InvocationID"] != invocation
            or runtime_invocation_id != invocation
            or runtime_control_group != service_cgroup
        ):
            _fail("formal clean wrapper live identity changed")
        deadline = time.monotonic() + ADMISSION_HANDSHAKE_TIMEOUT_SECONDS
        admission: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            try:
                admission_raw = journal_pin.read(REMOTE_ADMISSION_NAME)
            except FileNotFoundError:
                time.sleep(0.05)
                continue
            admission = _authority_api(
                "verify_launch_admission_receipt_v42r3"
            )(
                admission_raw,
                formal_transport_plan=plan,
                launch_transport_attempt=attempt,
            )
            break
        if admission is None:
            _fail("formal clean wrapper timed out awaiting durable admission")
        if (
            admission.get("unit_invocation_id") != invocation
            or admission.get("unit_main_pid") != service_pid
            or admission.get("unit_control_group") != service_cgroup
        ):
            _fail("formal admission receipt/live wrapper join changed")
        # The admission wait may span a manager restart.  Refresh both the manager
        # epoch and the unit observation before publishing wrapper authority.
        live_tools, manager = _require_live_host_epoch(plan)
        systemctl_pin = _ExecutablePin(TOOL_PATHS["systemctl"])
        try:
            unit = _unit_observation(systemctl_pin, attempt_id)
        finally:
            systemctl_pin.close()
        if (
            unit["MainPID"] != service_pid
            or unit["ControlGroup"] != service_cgroup
            or unit["InvocationID"] != invocation
        ):
            _fail("formal clean wrapper identity changed before publication")
        if journal_pin.entry_state(REMOTE_WRAPPER_ATTESTATION_NAME) != "ABSENT":
            _fail(
                "formal wrapper attestation already exists; replay is forbidden"
            )
        attestation = _authority_api("build_service_wrapper_attestation_v42r3")(
            formal_transport_plan=plan,
            launch_transport_attempt=attempt,
            launch_admission_receipt=admission,
            cross_version_scientific_state_gate=gate,
            manager_binding=manager,
            unit_observation=unit,
            service_pid=service_pid,
            service_cgroup=service_cgroup,
            service_environment=dict(os.environ),
            stdio_facts=stdio,
            live_file_descriptors=inherited,
            live_tool_facts=live_tools,
        )
        journal_pin.write_once(
            REMOTE_WRAPPER_ATTESTATION_NAME,
            canonical_json_bytes(attestation),
        )
        journal_pin.inventory()
        # The wrapper attestation is retained if the epoch changes here;
        # scientific execution still fails closed and is never inferred from
        # that file alone.
        exec_tools, exec_manager = _require_live_host_epoch(plan)
        if exec_manager != manager:
            _fail("formal service epoch changed after wrapper publication")
        journal_pin.verify()
        _exec_scientific_runner(
            plan=plan,
            source_manifest=receipt["source_manifest"],
            loader_source_raw=loader_source_raw,
            runner_role="LAUNCH_SERVICE",
            cross_version_gate=gate,
            live_tool_facts=exec_tools,
        )

    with _FormalJournalPin.open_required() as journal_pin:
        return run_with_journal_pin(journal_pin)


def _host_probe(
    *, ingress_raw: bytes, controller_manifest: Mapping[str, Any],
    expected_plan_id: str, loader_artifact: Mapping[str, Any],
    authority_artifact: Mapping[str, Any], receiver_artifact: Mapping[str, Any],
) -> int:
    # Parse independently before invoking the pure authority.  This ensures a
    # schema/version mutation cannot reach any live observer.
    ingress = _canonical(ingress_raw, "formal host epoch probe plan")
    if (
        ingress.get("schema_version") != SCHEMA_VERSION
        or ingress.get("formal_host_epoch_probe_plan_id")
        != expected_plan_id
    ):
        _fail("formal host epoch probe ingress version or identity changed")
    plan = _verify_probe_plan_adapter(ingress_raw, expected_plan_id)
    controller_id = controller_manifest.get("controller_source_manifest_id")
    local_stage0 = _authority_api(
        "verify_external_local_stage0_assumption_v42r3"
    )(
        plan.get("external_local_stage0_assumption"),
        controller_source_manifest=dict(controller_manifest),
    )
    ssh_ingress = _authority_api(
        "verify_external_ssh_ingress_assumption_v42r3"
    )(plan.get("external_ssh_ingress_assumption"))
    if (
        plan.get("controller_source_manifest_id") != controller_id
        or plan.get("probe_loader_artifact") != loader_artifact
        or plan.get("formal_authority_artifact") != authority_artifact
        or plan.get("probe_receiver_artifact") != receiver_artifact
        or type(local_stage0) is not dict
        or plan.get("external_local_stage0_assumption_id")
        != local_stage0.get("external_local_stage0_assumption_id")
        or type(ssh_ingress) is not dict
        or plan.get("external_ssh_ingress_assumption_id")
        != ssh_ingress.get("external_ssh_ingress_assumption_id")
    ):
        _fail("probe plan/controller source binding changed")
    _verify_fixed_materialization(plan)
    probe_phase = legacy.verify_remote_control_phase_inventory_v42r1(
        "POST_MATERIALIZATION_PREPARE"
    )
    _cross_version_gate(
        plan=plan, operation="PROBE_HOST_EPOCH", legacy_phase=probe_phase,
        effect_authorized=False,
    )
    tools, systemctl_pin = _observe_tool_facts()
    try:
        manager = _manager_binding(systemctl_pin)
    finally:
        systemctl_pin.close()
    runtime = _runtime_observation()
    if runtime != {
        "hostname": REMOTE_HOSTNAME,
        "user": REMOTE_USER,
        "uid": REMOTE_UID,
        "gid": REMOTE_GID,
        "python_invocation": REMOTE_PYTHON,
        "python_realpath": REMOTE_PYTHON_REALPATH,
        "python_version": list(REMOTE_PYTHON_VERSION),
        "python_isolated_flag": 1,
        "python_no_site_flag": 1,
        "python_dont_write_bytecode": True,
    }:
        _fail("formal host probe runtime observation changed")
    resources = _resource_observation(manager)
    receipt = _build_receipt_adapter(
        plan=plan,
        observed_runtime=runtime,
        manager_binding=manager,
        resource_observation=resources,
        remote_tool_facts=tools,
        formal_successor_journal_state=_formal_successor_journal_state(),
    )
    raw = canonical_json_bytes(receipt)
    sys.stdout.buffer.write(raw + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _verify_transported_source(
    raw: bytes, fact: Mapping[str, Any], label: str,
) -> None:
    if (
        type(raw) is not bytes
        or type(fact) is not dict
        or len(raw) != fact.get("byte_count")
        or hashlib.sha256(raw).hexdigest() != fact.get("sha256")
    ):
        _fail("transported " + label + " source changed")


def main_v42r3(
    *, mode: str, ingress_raw: bytes, loader_source_raw: bytes,
    authority_source_raw: bytes, receiver_source_raw: bytes,
    controller_manifest: Mapping[str, Any], expected_plan_id: str,
    loader_artifact: Mapping[str, Any], authority_artifact: Mapping[str, Any],
    receiver_artifact: Mapping[str, Any], attempt_id: str | None,
    runtime_invocation_id: str | None, runtime_control_group: str | None,
) -> int:
    """Dispatch one exact 42.3.0 role after loader authentication."""

    if (
        mode not in ALL_MODES
        or type(ingress_raw) is not bytes
        or type(controller_manifest) is not dict
        or type(expected_plan_id) is not str
        or any(
            type(value) is not dict
            for value in (loader_artifact, authority_artifact, receiver_artifact)
        )
    ):
        _fail("formal transport receiver call contract changed")
    processio.require_isolated_python()
    _verify_transported_source(loader_source_raw, loader_artifact, "loader")
    _verify_transported_source(authority_source_raw, authority_artifact, "authority")
    _verify_transported_source(receiver_source_raw, receiver_artifact, "receiver")
    if mode in {
        PROBE_MODE, PREPARE_MODE, INSPECT_PREPARE_MODE, ADMIT_MODE,
        INSPECT_LAUNCH_MODE,
    }:
        if any(
            value is not None
            for value in (attempt_id, runtime_invocation_id, runtime_control_group)
        ):
            _fail("SSH formal transport role received service identity")
    elif (
        type(attempt_id) is not str
        or re.fullmatch(r"[0-9a-f]{64}", attempt_id) is None
    ):
        _fail("formal service role omitted its launch attempt ID")
    if mode != SERVICE_WRAPPER_MODE and (
        runtime_invocation_id is not None or runtime_control_group is not None
    ):
        _fail("non-wrapper role received wrapper runtime identity")
    if mode == PROBE_MODE:
        return _host_probe(
            ingress_raw=ingress_raw,
            controller_manifest=controller_manifest,
            expected_plan_id=expected_plan_id,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
        )
    if mode == PREPARE_MODE:
        return _prepare_once(
            ingress_raw=ingress_raw,
            expected_plan_id=expected_plan_id,
            controller_manifest=controller_manifest,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
            loader_source_raw=loader_source_raw,
        )
    if mode == INSPECT_PREPARE_MODE:
        return _inspect_prepare(
            ingress_raw=ingress_raw,
            expected_plan_id=expected_plan_id,
            controller_manifest=controller_manifest,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
        )
    if mode == ADMIT_MODE:
        return _admit_launch(
            ingress_raw=ingress_raw,
            expected_plan_id=expected_plan_id,
            controller_manifest=controller_manifest,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
            loader_source_raw=loader_source_raw,
            authority_source_raw=authority_source_raw,
            receiver_source_raw=receiver_source_raw,
        )
    if mode == INSPECT_LAUNCH_MODE:
        return _inspect_launch(
            ingress_raw=ingress_raw,
            expected_plan_id=expected_plan_id,
            controller_manifest=controller_manifest,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
        )
    assert attempt_id is not None
    if mode == SERVICE_BOOTSTRAP_MODE:
        _service_bootstrap(
            ingress_raw=ingress_raw,
            expected_plan_id=expected_plan_id,
            attempt_id=attempt_id,
            controller_manifest=controller_manifest,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
            loader_source_raw=loader_source_raw,
            authority_source_raw=authority_source_raw,
            receiver_source_raw=receiver_source_raw,
        )
    if mode == SERVICE_WRAPPER_MODE:
        if type(runtime_invocation_id) is not str or type(runtime_control_group) is not str:
            _fail("formal clean wrapper runtime identity changed type")
        return _service_wrapper(
            ingress_raw=ingress_raw,
            expected_plan_id=expected_plan_id,
            attempt_id=attempt_id,
            runtime_invocation_id=runtime_invocation_id,
            runtime_control_group=runtime_control_group,
            controller_manifest=controller_manifest,
            loader_artifact=loader_artifact,
            authority_artifact=authority_artifact,
            receiver_artifact=receiver_artifact,
            loader_source_raw=loader_source_raw,
        )
    raise AssertionError("unreachable formal transport mode")


__all__ = [
    "V42FormalProbeReceiverError",
    "main_v42r3",
]
