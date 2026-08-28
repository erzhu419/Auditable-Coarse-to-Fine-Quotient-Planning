from __future__ import annotations

"""Authenticated stage-1 launcher for the native V42r3 formal successor.

An external operator-controlled invoker admits the exact bootstrap bytes in a
sealed memfd.  That stage preserves its sealed source in fd 4, copies these
exact pinned bytes into sealed fd 3, and starts a fresh isolated interpreter.
This stage validates both handoff descriptors and then authenticates the
selected controller commit/tree and every member of the exact controller TCB
before it rebuilds the retained V42r2 native activation evidence.  Each
controller-authorized PREPARE or LAUNCH dispatch is preceded by its durable
one-shot cut; the no-cut host probe and every SSH login prelude remain within
the explicitly external ingress TCB.  Noninterference by actors that can write
the remote campaign parents is a separate unattested external premise.  The
failed V42r1 formal prefix is always opened read-only and never reused.
"""

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import importlib
import importlib.machinery
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys
import types
from typing import Any, NoReturn


LAUNCHER_RELATIVE = "scripts/launch_v42_formal_transport_successor_v42r3.py"
BOOTSTRAP_RELATIVE = (
    "scripts/bootstrap_v42_formal_transport_successor_v42r3.py"
)
BOOTSTRAP_ROOT_ARGUMENT = "--v42r3-bootstrap-repository-root"
SEALED_STAGE_FD = 3
SEALED_STAGE_PATH = "/proc/self/fd/3"
SEALED_BOOTSTRAP_FD = 4
_BOOTSTRAP_REPOSITORY_ROOT: str | None = None
if __name__ == "__main__":
    if (
        len(sys.argv) < 3
        or sys.argv[0] != SEALED_STAGE_PATH
        or sys.argv[1] != BOOTSTRAP_ROOT_ARGUMENT
        or not os.path.isabs(sys.argv[2])
        or os.path.realpath(sys.argv[2]) != sys.argv[2]
        or not os.path.isdir(sys.argv[2])
    ):
        raise RuntimeError("V42r3 launcher did not enter through pinned bootstrap")
    _BOOTSTRAP_REPOSITORY_ROOT = sys.argv[2]
    del sys.argv[1:3]
    ROOT = Path(_BOOTSTRAP_REPOSITORY_ROOT)
else:
    ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
SCRIPT_PATH = ROOT / LAUNCHER_RELATIVE
EXACT_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
}
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
GIT = "/usr/bin/git"
GIT_SHA256 = (
    "587ef21868c948b883993e23209b86a72a6ddc06aab1545c697ffc31075acd4a"
)
GIT_BYTE_COUNT = 3_710_360
_AUTHENTICATED_STAGE_SELF_RAW: bytes | None = None
_AUTHENTICATED_BOOTSTRAP_RAW: bytes | None = None
_EARLY_SEALED_MATERIALS_VERIFIED = False


def _live_descriptors() -> list[int]:
    live: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        if name.isdigit():
            descriptor = int(name)
            try:
                os.fstat(descriptor)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise
                continue
            live.append(descriptor)
    return sorted(live)


def _read_sealed_source(descriptor: int, label: str) -> bytes:
    before = os.fstat(descriptor)
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
        or not 0 < before.st_size <= 8 * 1024**2
        or fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != expected_seals
    ):
        raise RuntimeError("V42r3 sealed " + label + " storage changed")
    chunks: list[bytes] = []
    offset = 0
    while offset < before.st_size:
        chunk = os.pread(
            descriptor, min(1024 * 1024, before.st_size - offset), offset
        )
        if not chunk:
            raise RuntimeError("V42r3 sealed " + label + " ended early")
        chunks.append(chunk)
        offset += len(chunk)
    after = os.fstat(descriptor)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        any(getattr(before, field) != getattr(after, field) for field in fields)
        or fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != expected_seals
    ):
        raise RuntimeError("V42r3 sealed " + label + " changed while read")
    return b"".join(chunks)


def _require_early_isolated_runtime() -> None:
    global _AUTHENTICATED_BOOTSTRAP_RAW, _AUTHENTICATED_STAGE_SELF_RAW
    global _EARLY_SEALED_MATERIALS_VERIFIED
    expected_user_arguments = list(sys.argv[1:])
    if (
        __name__ != "__main__"
        or _BOOTSTRAP_REPOSITORY_ROOT is None
        or __file__ != SEALED_STAGE_PATH
        or sys.argv[0] != SEALED_STAGE_PATH
        or sys.executable != "/usr/bin/python3"
        or os.path.realpath(sys.executable) != "/usr/bin/python3.10"
        or tuple(sys.version_info[:3]) != (3, 10, 12)
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.dont_write_bytecode is not True
        or sys.gettrace() is not None
        or sys.getprofile() is not None
        or sys.orig_argv
        != [
            "/usr/bin/python3", "-I", "-S", "-B", SEALED_STAGE_PATH,
            BOOTSTRAP_ROOT_ARGUMENT, _BOOTSTRAP_REPOSITORY_ROOT,
            *expected_user_arguments,
        ]
        or sys.path
        != [
            "/usr/lib/python310.zip", "/usr/lib/python3.10",
            "/usr/lib/python3.10/lib-dynload",
        ]
        or dict(os.environ) != EXACT_ENVIRONMENT
        or Path.cwd() != ROOT
        or getattr(getattr(os, "__spec__", None), "origin", None)
        != "/usr/lib/python3.10/os.py"
    ):
        raise RuntimeError("V42r3 launcher isolated Python entry changed")
    if _live_descriptors() != [
        0, 1, 2, SEALED_STAGE_FD, SEALED_BOOTSTRAP_FD,
    ]:
        raise RuntimeError("V42r3 launcher inherited unexpected descriptors")
    _AUTHENTICATED_STAGE_SELF_RAW = _read_sealed_source(
        SEALED_STAGE_FD, "stage-1 launcher"
    )
    _AUTHENTICATED_BOOTSTRAP_RAW = _read_sealed_source(
        SEALED_BOOTSTRAP_FD, "stage-0 bootstrap"
    )
    os.close(SEALED_BOOTSTRAP_FD)
    os.close(SEALED_STAGE_FD)
    if _live_descriptors() != [0, 1, 2]:
        raise RuntimeError("V42r3 launcher retained a bootstrap descriptor")
    _EARLY_SEALED_MATERIALS_VERIFIED = True


if __name__ == "__main__":
    _require_early_isolated_runtime()


NEW_TCB_PATHS = (
    BOOTSTRAP_RELATIVE,
    LAUNCHER_RELATIVE,
    "scripts/run_v42_standard_2048_formal_transport_native_successor_driver.py",
    "scripts/v42_standard_2048_formal_transport_loader_v42r3.py",
    "scripts/v42_standard_2048_formal_transport_receiver_v42r3.py",
    (
        "src/acfqp/"
        "construction_k7_standard_2048_formal_transport_successor_v42r3.py"
    ),
)
PREDECESSOR_TCB_PATHS = (
    "scripts/__init__.py",
    "scripts/launch_v42_activation_successor_or_formal.py",
    "scripts/launch_v42_preformal_upload_sender.py",
    "scripts/publish_v42_preformal_upload_journal.py",
    "scripts/run_v42_activation_successor_finalizer.py",
    "scripts/run_v42_materialization_activation.py",
    "scripts/run_v42_preformal_upload_sender.py",
    "scripts/run_v42_standard_2048_formal_transport_driver.py",
    "scripts/run_v42_standard_2048_formal_transport_successor_driver.py",
    "scripts/run_v42_standard_2048_remote_ordinal2.py",
    "scripts/v42_activation_successor_loader.py",
    "scripts/v42_activation_successor_receiver.py",
    "src/acfqp/__init__.py",
    "src/acfqp/artifacts.py",
    "src/acfqp/build_coverage.py",
    "src/acfqp/construction_k7_domain_registry_extension_v42.py",
    "src/acfqp/construction_k7_standard_2048_activation_successor_v42r2.py",
    "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
    "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
    "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
    "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
    "src/acfqp/core.py",
    "src/acfqp/enumeration.py",
    "src/acfqp/phase3e_ids.py",
)
CONTROLLER_TCB_PATHS = tuple(
    sorted((*PREDECESSOR_TCB_PATHS, *NEW_TCB_PATHS))
)
if (
    len(CONTROLLER_TCB_PATHS) != 33
    or len(set(CONTROLLER_TCB_PATHS)) != len(CONTROLLER_TCB_PATHS)
):
    raise RuntimeError("V42r3 controller TCB inventory changed")

LOCAL_JOURNAL_ROOT = Path(
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-local-formal-transport-ordinal2-v42r3r1"
)
REMOTE_JOURNAL_ROOT = (
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-remote-ordinal2-formal-transport-v42r3r1"
)
KNOWN_HOSTS_NAME = "PINNED_KNOWN_HOSTS"
CONTROLLER_MANIFEST_NAME = "CONTROLLER_SOURCE_MANIFEST.json"
NATIVE_BINDING_NAME = "NATIVE_ACTIVATION_BINDING.json"
HOST_PROBE_PLAN_NAME = "FORMAL_HOST_EPOCH_PROBE_PLAN.json"
HOST_PROBE_ATTEMPT_NAME = "FORMAL_HOST_EPOCH_PROBE_ATTEMPT.json"
HOST_PROBE_OBSERVATION_NAME = "FORMAL_HOST_EPOCH_TRANSPORT_OBSERVATION.json"
HOST_PROBE_FAILURE_NAME = "FORMAL_HOST_EPOCH_DISPATCH_FAILURE.json"
HOST_RECEIPT_NAME = "FORMAL_HOST_EPOCH_RECEIPT.json"
LOCAL_PLAN_NAME = "FORMAL_TRANSPORT_PLAN.json"
LOCAL_PREPARE_ATTEMPT_NAME = "FORMAL_PREPARE_ATTEMPT.json"
LOCAL_PREPARE_NETWORK_START_NAME = "FORMAL_PREPARE_NETWORK_START.json"
LOCAL_PREPARE_RECEIPT_NAME = "FORMAL_PREPARE_RECEIPT.json"
LOCAL_LAUNCH_ATTEMPT_NAME = "LOCAL_LAUNCH_ATTEMPT.json"
LOCAL_LAUNCH_TRANSPORT_ATTEMPT_NAME = "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json"
LOCAL_LAUNCH_NETWORK_START_NAME = "FORMAL_LAUNCH_NETWORK_START.json"
LOCAL_LAUNCH_ADMISSION_NAME = "FORMAL_LAUNCH_ADMISSION_RECEIPT.json"
LOCAL_LAUNCH_CONTROL_NAME = "EXISTING_RUNNER_LAUNCH_CONTROL"
PREPARE_OUTCOME_NAME = "FORMAL_PREPARE_OPERATION_OUTCOME.json"
LAUNCH_OUTCOME_NAME = "FORMAL_LAUNCH_OPERATION_OUTCOME.json"
PRE_NETWORK_FAILURE_PREFIX = {
    "PREPARE": "FORMAL_PREPARE_PRE_NETWORK_FAILURE",
    "LAUNCH": "FORMAL_LAUNCH_PRE_NETWORK_FAILURE",
}
INSPECTION_PREFIX = "FORMAL_READ_ONLY_INSPECTION."
CLASSIFICATION_PREFIX = "FORMAL_CLASSIFICATION."
MAX_LOCAL_ARTIFACT_BYTES = 64 * 1024**2
MAX_STDERR_BYTES = 1024**2
READ_ONLY_TIMEOUT_SECONDS = 120.0
PREPARE_TIMEOUT_SECONDS = 900.0
ADMISSION_TIMEOUT_SECONDS = 120.0
MAXIMUM_REMOTE_COMMAND_BYTES = 96 * 1024
LOADER_RELATIVE = "scripts/v42_standard_2048_formal_transport_loader_v42r3.py"
RECEIVER_RELATIVE = "scripts/v42_standard_2048_formal_transport_receiver_v42r3.py"
AUTHORITY_RELATIVE = (
    "src/acfqp/"
    "construction_k7_standard_2048_formal_transport_successor_v42r3.py"
)
AUTHORITY_MODULE = (
    "acfqp.construction_k7_standard_2048_formal_transport_successor_v42r3"
)
NATIVE_DRIVER_MODULE = (
    "scripts.run_v42_standard_2048_formal_transport_native_successor_driver"
)
PREFORMAL_MODULE = (
    "acfqp.construction_k7_standard_2048_materialization_transport_v42r1"
)
SENDER_MODULE = "scripts.run_v42_preformal_upload_sender"
LOADER_MODULE = "scripts.v42_standard_2048_formal_transport_loader_v42r3"
LEGACY_AUTHORITY_MODULE = (
    "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1"
)
PREREGISTRATION_MODULE = (
    "acfqp.construction_k7_standard_2048_fresh_terminal_preregistration_v42"
)
SCIENTIFIC_RUNNER_MODULE = "scripts.run_v42_standard_2048_remote_ordinal2"
PROBE_MODE = "--probe-host-epoch-v42r3"
INSPECT_PREPARE_MODE = "--inspect-prepare-v42r3"
INSPECT_LAUNCH_MODE = "--inspect-launch-v42r3"
READ_ONLY_SSH_MODES = frozenset(
    {PROBE_MODE, INSPECT_PREPARE_MODE, INSPECT_LAUNCH_MODE}
)
SSH_MODES = frozenset(
    {
        PROBE_MODE,
        "--prepare-once-v42r3",
        INSPECT_PREPARE_MODE,
        "--admit-launch-v42r3",
        INSPECT_LAUNCH_MODE,
    }
)
SUCCESSOR_FINAL_FILE = "ACTIVATION_SUCCESSOR_FINAL_EVIDENCE_INDEX.json"
LOCAL_SSH_EXECUTABLE = "/usr/bin/ssh"
LOCAL_IDENTITY_FILE = "/home/erzhu419/.ssh/id_ed25519"
REMOTE_ENDPOINT_HOST = "tf290q6n.zjz-service.cn"
REMOTE_ENDPOINT_PORT = 23035
REMOTE_USER = "erzhu419"


class V42FormalTransportSuccessorLauncherError(RuntimeError):
    """The native formal successor launcher rejected its evidence boundary."""


def _fail(message: str) -> NoReturn:
    raise V42FormalTransportSuccessorLauncherError(message)


def _require_sealed_stage_materials() -> None:
    if (
        _EARLY_SEALED_MATERIALS_VERIFIED is not True
        or type(_AUTHENTICATED_STAGE_SELF_RAW) is not bytes
        or not _AUTHENTICATED_STAGE_SELF_RAW
        or type(_AUTHENTICATED_BOOTSTRAP_RAW) is not bytes
        or not _AUTHENTICATED_BOOTSTRAP_RAW
    ):
        _fail("V42r3 effect-capable launcher lacks verified sealed materials")


def _absolute(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or not path.name:
        _fail(label + " path changed")
    return path


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")


def _read_live_source(relative: str, cap: int = 8 * 1024**2) -> bytes:
    if relative not in CONTROLLER_TCB_PATHS:
        _fail("controller source path escaped the exact TCB")
    parsed = PurePosixPath(relative)
    if (
        parsed.is_absolute()
        or parsed.as_posix() != relative
        or any(part in {"", ".", ".."} for part in parsed.parts)
    ):
        _fail("controller source relative path changed")
    path = ROOT.joinpath(*parsed.parts)
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
            or stat.S_IMODE(before.st_mode) != 0o644
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_nlink != 1
            or not 0 < before.st_size <= cap
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("controller source storage changed: " + relative)
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("controller source ended early: " + relative)
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("controller source grew while read: " + relative)
        after = os.fstat(descriptor)
    finally:
        cleanup_error = _close_descriptors_collect([descriptor])
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error
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
        _fail("controller source changed while read: " + relative)
    return b"".join(chunks)


def _run_git(*arguments: str) -> bytes:
    named = os.lstat(GIT)
    descriptor = os.open(GIT, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o755
            or before.st_uid != 0
            or before.st_gid != 0
            or before.st_nlink != 1
            or before.st_size != GIT_BYTE_COUNT
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("fixed Git executable storage changed")
        digest = hashlib.sha256()
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(
                descriptor, min(1024 * 1024, before.st_size - offset), offset
            )
            if not chunk:
                _fail("fixed Git executable ended early")
            digest.update(chunk)
            offset += len(chunk)
        if digest.hexdigest() != GIT_SHA256:
            _fail("fixed Git executable bytes changed")
        completed = subprocess.run(
            [GIT, "--no-replace-objects", *arguments],
            executable="/proc/self/fd/" + str(descriptor),
            pass_fds=(descriptor,),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_TERMINAL_PROMPT": "0",
            },
            cwd="/",
            check=False,
            timeout=60.0,
        )
        after = os.fstat(descriptor)
    finally:
        cleanup_error = _close_descriptors_collect([descriptor])
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error
    final = os.lstat(GIT)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        any(
            getattr(before, field) != getattr(after, field)
            or getattr(after, field) != getattr(final, field)
            for field in fields
        )
        or completed.returncode != 0
        or completed.stderr
    ):
        _fail("fixed Git query did not close exactly")
    return completed.stdout


def _git_anchor(revision: str) -> str:
    raw = _run_git("-C", str(ROOT), "rev-parse", "--verify", revision)
    if len(raw) != 41 or not raw.endswith(b"\n"):
        _fail("V42r3 Git anchor output changed")
    value = raw[:-1].decode("ascii", errors="strict")
    if _HEX40.fullmatch(value) is None:
        _fail("V42r3 Git anchor is not lowercase 40-hex")
    return value


def _coherent_git_anchors(expected_commit: str) -> tuple[str, str]:
    """Observe HEAD and that exact commit's tree in one fixed Git process."""

    if _HEX40.fullmatch(expected_commit) is None:
        _fail("expected V42r3 commit anchor changed")
    raw = _run_git(
        "-C", str(ROOT), "rev-parse",
        "HEAD^{commit}", expected_commit + "^{tree}",
    )
    if len(raw) != 82 or raw.count(b"\n") != 2 or not raw.endswith(b"\n"):
        _fail("V42r3 coherent Git anchor output changed")
    head_raw, tree_raw, terminal = raw.split(b"\n")
    if terminal != b"":
        _fail("V42r3 coherent Git anchor framing changed")
    try:
        head = head_raw.decode("ascii", errors="strict")
        tree = tree_raw.decode("ascii", errors="strict")
    except UnicodeError as error:
        raise V42FormalTransportSuccessorLauncherError(
            "V42r3 coherent Git anchors are not ASCII"
        ) from error
    if _HEX40.fullmatch(head) is None or _HEX40.fullmatch(tree) is None:
        _fail("V42r3 coherent Git anchors are not lowercase 40-hex")
    return head, tree


def _git_inventory(commit: str) -> dict[str, tuple[str, str, str]]:
    listing = _run_git(
        "-C", str(ROOT), "ls-tree", "-rz", "--full-tree", commit,
        "--", *CONTROLLER_TCB_PATHS,
    )
    records = listing.split(b"\0")
    if not records or records[-1] != b"":
        _fail("V42r3 Git inventory framing changed")
    result: dict[str, tuple[str, str, str]] = {}
    for record in records[:-1]:
        try:
            header, relative_raw = record.split(b"\t", 1)
            mode_raw, kind_raw, oid_raw = header.split(b" ")
            relative = relative_raw.decode("utf-8", errors="strict")
            value = (
                mode_raw.decode("ascii"), kind_raw.decode("ascii"),
                oid_raw.decode("ascii"),
            )
        except (UnicodeError, ValueError) as error:
            raise V42FormalTransportSuccessorLauncherError(
                "V42r3 Git inventory malformed"
            ) from error
        if relative in result:
            _fail("V42r3 Git inventory contains a duplicate")
        result[relative] = value
    if set(result) != set(CONTROLLER_TCB_PATHS):
        _fail("selected commit omitted an exact V42r3 TCB source")
    return result


class _VerifiedSourceLoader:
    def __init__(
        self, *, fullname: str, relative: str, raw: bytes, package: bool,
    ) -> None:
        self.fullname = fullname
        self.relative = relative
        self.raw = raw
        self.package = package
        self.origin = str(ROOT.joinpath(*PurePosixPath(relative).parts))
        self.exec_count = 0

    def create_module(self, spec: object) -> None:
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        if self.exec_count != 0:
            _fail("verified controller module executed more than once")
        self.exec_count = 1
        namespace = vars(module)
        namespace["__file__"] = self.origin
        namespace["__cached__"] = None
        exec(
            compile(
                self.raw, self.origin, "exec", flags=0,
                dont_inherit=True, optimize=0,
            ),
            namespace,
            namespace,
        )


class _VerifiedSourceFinder:
    def __init__(
        self, raws: Mapping[str, bytes], *, enforce_runtime_boundary: bool = False,
        allowed_sys_path: Sequence[str] | None = None,
    ) -> None:
        self.raws = dict(raws)
        self.enforce_runtime_boundary = enforce_runtime_boundary
        self.allowed_sys_path = (
            None if allowed_sys_path is None else tuple(allowed_sys_path)
        )
        self.created: dict[str, _VerifiedSourceLoader] = {}
        self.module_paths: dict[str, tuple[str, bool]] = {}
        for relative in self.raws:
            if relative == "scripts/__init__.py":
                self.module_paths["scripts"] = (relative, True)
            elif relative.startswith("scripts/") and relative.endswith(".py"):
                self.module_paths[relative[:-3].replace("/", ".")] = (
                    relative, False,
                )
            elif relative == "src/acfqp/__init__.py":
                self.module_paths["acfqp"] = (relative, True)
            elif relative.startswith("src/acfqp/") and relative.endswith(".py"):
                self.module_paths[relative[4:-3].replace("/", ".")] = (
                    relative, False,
                )

    def find_spec(
        self, fullname: str, path: object = None, target: object = None,
    ) -> importlib.machinery.ModuleSpec | None:
        del path, target
        if self.enforce_runtime_boundary:
            _scrub_repository_import_paths()
            if tuple(sys.path) != self.allowed_sys_path:
                _fail("verified V42r3 sys.path authority changed")
        selected = self.module_paths.get(fullname)
        if selected is None:
            if (
                fullname == "scripts" or fullname.startswith("scripts.")
                or fullname == "acfqp" or fullname.startswith("acfqp.")
            ):
                raise ImportError("unmanifested V42r3 controller module: " + fullname)
            return None
        if fullname in self.created:
            raise ImportError("verified V42r3 controller loader repeated: " + fullname)
        relative, package = selected
        loader = _VerifiedSourceLoader(
            fullname=fullname,
            relative=relative,
            raw=self.raws[relative],
            package=package,
        )
        self.created[fullname] = loader
        spec = importlib.machinery.ModuleSpec(
            fullname, loader, origin=loader.origin, is_package=package
        )
        if package:
            # The verified finder supplies every repository child module.
            # A live package search path would expose unmanifested siblings.
            spec.submodule_search_locations = []
        return spec

    def verify_loaded(self) -> None:
        if self.enforce_runtime_boundary:
            _scrub_repository_import_paths()
            if (
                tuple(sys.path) != self.allowed_sys_path
                or not sys.meta_path
                or sys.meta_path[0] is not self
            ):
                _fail("verified V42r3 finder lost first import authority")
            extras = [
                name for name in sys.modules
                if (
                    name == "scripts" or name.startswith("scripts.")
                    or name == "acfqp" or name.startswith("acfqp.")
                ) and name not in self.created
            ]
            if extras:
                _fail("unverified repository module entered sys.modules")
        for name, loader in self.created.items():
            module = sys.modules.get(name)
            spec = getattr(module, "__spec__", None)
            expected_package = name if loader.package else name.rpartition(".")[0]
            if (
                module is None
                or getattr(module, "__loader__", None) is not loader
                or getattr(module, "__file__", None) != loader.origin
                or getattr(module, "__package__", None) != expected_package
                or getattr(spec, "origin", None) != loader.origin
                or getattr(spec, "loader", None) is not loader
                or (
                    list(getattr(spec, "submodule_search_locations", []) or [])
                    != []
                    if loader.package
                    else getattr(spec, "submodule_search_locations", None)
                    is not None
                )
                or (
                    list(getattr(module, "__path__", [])) != []
                    if loader.package
                    else hasattr(module, "__path__")
                )
                or getattr(module, "__cached__", None) is not None
                or loader.exec_count != 1
            ):
                _fail("verified controller module escaped source bytes: " + name)


_VERIFIED_RAWS: dict[str, bytes] | None = None
_VERIFIED_FINDER: _VerifiedSourceFinder | None = None
_AUTHENTICATED_CONTROLLER_MANIFEST_RAW: bytes | None = None


def _scrub_repository_import_paths() -> None:
    forbidden = {str(ROOT), str(SOURCE_ROOT)}
    sys.path[:] = [entry for entry in sys.path if entry not in forbidden]


def _install_verified_importer(raws: Mapping[str, bytes]) -> None:
    global _VERIFIED_RAWS, _VERIFIED_FINDER
    if _VERIFIED_RAWS is not None or _VERIFIED_FINDER is not None:
        _fail("V42r3 verified importer installation repeated")
    forbidden = [
        name for name in sys.modules
        if name == "scripts" or name.startswith("scripts.")
        or name == "acfqp" or name.startswith("acfqp.")
    ]
    if forbidden:
        _fail("repository module loaded before V42r3 source authentication")
    _VERIFIED_RAWS = dict(raws)
    _scrub_repository_import_paths()
    allowed_sys_path = tuple(sys.path)
    if __name__ == "__main__" and allowed_sys_path != (
        "/usr/lib/python310.zip",
        "/usr/lib/python3.10",
        "/usr/lib/python3.10/lib-dynload",
    ):
        _fail("authenticated V42r3 isolated sys.path changed")
    _VERIFIED_FINDER = _VerifiedSourceFinder(
        raws,
        enforce_runtime_boundary=True,
        allowed_sys_path=allowed_sys_path,
    )
    sys.meta_path.insert(0, _VERIFIED_FINDER)


def _verified_module(name: str) -> types.ModuleType:
    if _VERIFIED_FINDER is None or _VERIFIED_RAWS is None:
        _fail("V42r3 verified importer is absent")
    module = importlib.import_module(name)
    _VERIFIED_FINDER.verify_loaded()
    return module


def _verified_source_raw(relative: str) -> bytes:
    if _VERIFIED_RAWS is None or relative not in _VERIFIED_RAWS:
        _fail("V42r3 verified source cache is absent")
    raw = _VERIFIED_RAWS[relative]
    if _read_live_source(relative, max(len(raw), 1)) != raw:
        _fail("live V42r3 source differs from authenticated bytes: " + relative)
    return raw


def _authority() -> Any:
    return _verified_module(AUTHORITY_MODULE)


def build_live_controller_source_manifest_v42r3(
    *, expected_commit: str, expected_tree: str,
) -> dict[str, Any]:
    """Bind the exact 33-file V42r3 controller TCB to HEAD and live bytes."""

    _require_sealed_stage_materials()
    if (
        _HEX40.fullmatch(expected_commit) is None
        or _HEX40.fullmatch(expected_tree) is None
    ):
        _fail("expected V42r3 Git anchors changed")
    if _coherent_git_anchors(expected_commit) != (
        expected_commit, expected_tree
    ):
        _fail("selected coherent HEAD/commit tree differs from caller anchor")
    selected = _git_inventory(expected_commit)
    facts: list[dict[str, Any]] = []
    raws: dict[str, bytes] = {}
    for relative in CONTROLLER_TCB_PATHS:
        raw = _read_live_source(relative)
        raws[relative] = raw
        mode, kind, oid = selected[relative]
        observed_oid = hashlib.sha1(  # noqa: S324 - Git blob identity
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest()
        if (mode, kind, oid) != ("100644", "blob", observed_oid):
            _fail("live V42r3 source differs from selected Git blob: " + relative)
        facts.append(
            {
                "relative_path": relative,
                "git_mode": mode,
                "git_object_type": kind,
                "git_blob_oid": oid,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if raws[LAUNCHER_RELATIVE] != _AUTHENTICATED_STAGE_SELF_RAW:
        _fail("executing launcher bytes differ from authenticated source")
    if raws[BOOTSTRAP_RELATIVE] != _AUTHENTICATED_BOOTSTRAP_RAW:
        _fail("executing bootstrap bytes differ from authenticated source")
    if _coherent_git_anchors(expected_commit) != (
        expected_commit, expected_tree
    ):
        _fail("V42r3 coherent Git anchors changed across source verification")
    _install_verified_importer(raws)
    formal = _authority()
    manifest = formal.build_controller_source_manifest_v42r3(
        source_commit=expected_commit,
        source_tree=expected_tree,
        source_facts=facts,
    )
    verified = formal.verify_controller_source_manifest_v42r3(manifest)
    if verified != manifest:
        _fail("V42r3 authority changed its controller manifest")
    global _AUTHENTICATED_CONTROLLER_MANIFEST_RAW
    manifest_raw = _canonical_json_bytes(manifest)
    if (
        _AUTHENTICATED_CONTROLLER_MANIFEST_RAW is not None
        and _AUTHENTICATED_CONTROLLER_MANIFEST_RAW != manifest_raw
    ):
        _fail("authenticated V42r3 controller manifest changed")
    _AUTHENTICATED_CONTROLLER_MANIFEST_RAW = manifest_raw
    if any(_verified_source_raw(relative) != raws[relative] for relative in raws):
        _fail("V42r3 source changed after verified importer installation")
    return manifest


def verify_controller_and_native_inputs_v42r3(
    *, predecessor_activation_evidence_root: Path,
    successor_evidence_root: Path,
    expected_successor_final_evidence_index_id: str,
    expected_controller_commit: str,
    expected_controller_tree: str,
) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    """Perform the complete no-network controller/native input verification."""

    manifest = build_live_controller_source_manifest_v42r3(
        expected_commit=expected_controller_commit,
        expected_tree=expected_controller_tree,
    )
    native_module = _verified_module(NATIVE_DRIVER_MODULE)
    verified = native_module.verify_native_formal_inputs_v42r3(
        predecessor_activation_evidence_root=predecessor_activation_evidence_root,
        successor_evidence_root=successor_evidence_root,
        expected_successor_final_evidence_index_id=(
            expected_successor_final_evidence_index_id
        ),
    )
    formal = _authority()
    binding = formal.build_native_activation_binding_v42r3(
        native_activation_inputs=dict(verified.native_activation_inputs)
    )
    checked = formal.verify_native_activation_binding_v42r3(binding)
    if checked != binding:
        _fail("V42r3 authority changed its native activation binding")
    if native_module.verify_failed_v42r1_formal_prefix_read_only() != (
        verified.predecessor_formal_prefix
    ):
        _fail("failed V42r1 formal prefix changed across controller verification")
    return manifest, verified, binding


def _stable_state(value: os.stat_result) -> tuple[int, ...]:
    return tuple(
        getattr(value, field)
        for field in (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
    )


def _directory_identity(value: os.stat_result) -> tuple[int, ...]:
    return tuple(
        getattr(value, field)
        for field in ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid")
    )


def _close_descriptors_collect(
    descriptors: Sequence[int],
) -> BaseException | None:
    first: BaseException | None = None
    for descriptor in descriptors:
        if type(descriptor) is not int or descriptor < 0:
            continue
        try:
            os.close(descriptor)
        except BaseException as error:
            if first is None:
                first = error
    return first


def _close_resources_collect(resources: Sequence[Any]) -> BaseException | None:
    first: BaseException | None = None
    for resource in resources:
        if resource is None:
            continue
        try:
            resource.close()
        except BaseException as error:
            if first is None:
                first = error
    return first


def _journal_root_identity(value: os.stat_result) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42_formal_successor_local_journal_root_identity.v42r3",
        "schema_version": "42.3.0",
        "path": str(LOCAL_JOURNAL_ROOT),
        "st_dev": value.st_dev,
        "st_ino": value.st_ino,
        "mode": stat.S_IMODE(value.st_mode),
        "uid": value.st_uid,
        "gid": value.st_gid,
    }


def _anchor_name(suffix: str) -> str:
    if not suffix or "/" in suffix or suffix in {".", ".."}:
        _fail("V42r3 journal anchor suffix changed")
    return "." + LOCAL_JOURNAL_ROOT.name + "." + suffix


def _open_directory_chain(
    path: Path,
) -> list[tuple[int, str | None, tuple[int, ...]]]:
    if not path.is_absolute() or ".." in path.parts:
        _fail("V42r3 journal directory chain changed")
    descriptor = os.open(
        "/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    result: list[tuple[int, str | None, tuple[int, ...]]] = [
        (descriptor, None, _directory_identity(os.fstat(descriptor)))
    ]
    try:
        for component in path.parts[1:]:
            named = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            successor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
            opened = os.fstat(successor)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or _directory_identity(named) != _directory_identity(opened)
            ):
                _close_descriptors_collect([successor])
                _fail("V42r3 journal directory component changed")
            result.append(
                (successor, component, _directory_identity(opened))
            )
            descriptor = successor
        return result
    except BaseException:
        _close_descriptors_collect(
            [opened for opened, _, _ in reversed(result)]
        )
        raise


def _verify_directory_chain(
    chain: Sequence[tuple[int, str | None, tuple[int, ...]]],
) -> None:
    for index, (descriptor, name, identity) in enumerate(chain):
        if _directory_identity(os.fstat(descriptor)) != identity:
            _fail("V42r3 held directory component changed")
        if index:
            assert name is not None
            named = os.stat(
                name, dir_fd=chain[index - 1][0], follow_symlinks=False
            )
            if _directory_identity(named) != identity:
                _fail("V42r3 named directory component changed")


def _read_regular_at(
    directory_fd: int, name: str, cap: int, *, mode: int,
) -> bytes:
    if (
        not name
        or "/" in name
        or type(cap) is not int
        or not 0 < cap <= MAX_LOCAL_ARTIFACT_BYTES
    ):
        _fail("V42r3 journal read contract changed")
    named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
        dir_fd=directory_fd,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_nlink != 1
            or not 0 < before.st_size <= cap
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("V42r3 journal artifact identity changed")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("V42r3 journal artifact ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("V42r3 journal artifact grew while read")
        after = os.fstat(descriptor)
    finally:
        cleanup_error = _close_descriptors_collect([descriptor])
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error
    final = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if _stable_state(before) != _stable_state(after) or _stable_state(after) != _stable_state(final):
        _fail("V42r3 journal artifact changed while read")
    return b"".join(chunks)


@dataclass
class _JournalPin:
    descriptor: int
    parent_descriptor: int
    directory_chain: list[tuple[int, str | None, tuple[int, ...]]]
    root_state: tuple[int, ...]
    root_identity: dict[str, Any]
    closed: bool = False

    @classmethod
    def open(cls) -> "_JournalPin":
        chain = _open_directory_chain(LOCAL_JOURNAL_ROOT.parent)
        parent_descriptor = chain[-1][0]
        descriptor = -1
        try:
            descriptor = os.open(
                LOCAL_JOURNAL_ROOT.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_descriptor,
            )
            observed = os.fstat(descriptor)
            named = os.stat(
                LOCAL_JOURNAL_ROOT.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISDIR(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o700
                or observed.st_uid != os.geteuid()
                or observed.st_gid != os.getegid()
                or (observed.st_dev, observed.st_ino)
                != (named.st_dev, named.st_ino)
                or LOCAL_JOURNAL_ROOT.resolve(strict=True) != LOCAL_JOURNAL_ROOT
            ):
                _fail("V42r3 journal root pin changed")
            identity = _journal_root_identity(observed)
            retained = _read_regular_at(
                parent_descriptor,
                _anchor_name("ROOT_IDENTITY.json"),
                4096,
                mode=0o400,
            )
            if retained != _canonical_json_bytes(identity):
                _fail("V42r3 journal root identity anchor changed")
            result = cls(
                descriptor=descriptor,
                parent_descriptor=parent_descriptor,
                directory_chain=chain,
                root_state=_directory_identity(observed),
                root_identity=identity,
            )
            result.verify_root()
            return result
        except BaseException:
            _close_descriptors_collect(
                [descriptor, *[opened for opened, _, _ in reversed(chain)]]
            )
            raise

    def verify_root(self) -> None:
        if self.closed:
            _fail("V42r3 journal pin is closed")
        _verify_directory_chain(self.directory_chain)
        observed = os.fstat(self.descriptor)
        named = os.stat(
            LOCAL_JOURNAL_ROOT.name,
            dir_fd=self.parent_descriptor,
            follow_symlinks=False,
        )
        if (
            _directory_identity(observed) != self.root_state
            or (observed.st_dev, observed.st_ino)
            != (named.st_dev, named.st_ino)
            or _journal_root_identity(observed) != self.root_identity
        ):
            _fail("V42r3 journal root changed while pinned")
        if _read_regular_at(
            self.parent_descriptor,
            _anchor_name("ROOT_IDENTITY.json"),
            4096,
            mode=0o400,
        ) != _canonical_json_bytes(self.root_identity):
            _fail("V42r3 journal root anchor changed while pinned")

    def exists(self, name: str) -> bool:
        self.verify_root()
        try:
            observed = os.stat(
                name, dir_fd=self.descriptor, follow_symlinks=False
            )
        except FileNotFoundError:
            return False
        if not stat.S_ISREG(observed.st_mode):
            _fail("V42r3 journal fixed name is nonregular")
        return True

    def parent_anchor_exists(self, name: str) -> bool:
        self.verify_root()
        try:
            observed = os.stat(
                name, dir_fd=self.parent_descriptor, follow_symlinks=False
            )
        except FileNotFoundError:
            return False
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o400
            or observed.st_uid != os.geteuid()
            or observed.st_gid != os.getegid()
            or observed.st_nlink != 1
        ):
            _fail("V42r3 journal parent cut changed")
        return True

    def publish(self, name: str, raw: bytes) -> tuple[int, ...]:
        if (
            not name
            or "/" in name
            or type(raw) is not bytes
            or not 0 < len(raw) <= MAX_LOCAL_ARTIFACT_BYTES
        ):
            _fail("V42r3 journal publication contract changed")
        self.verify_root()
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o400,
            dir_fd=self.descriptor,
        )
        try:
            os.fchmod(descriptor, 0o400)
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    _fail("V42r3 journal publication made no progress")
                view = view[written:]
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
                _fail("V42r3 journal published inode changed")
            state = _stable_state(observed)
        finally:
            cleanup_error = _close_descriptors_collect([descriptor])
            if cleanup_error is not None and sys.exc_info()[0] is None:
                raise cleanup_error
        os.fsync(self.descriptor)
        named = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        if _stable_state(named) != state:
            _fail("V42r3 journal named inode differs after publication")
        self.verify_root()
        return state

    def publish_parent_anchor(self, name: str, raw: bytes) -> tuple[int, ...]:
        prefix = "." + LOCAL_JOURNAL_ROOT.name + "."
        suffix = name[len(prefix):] if name.startswith(prefix) else ""
        if (
            name != _anchor_name(suffix)
            or "/" in name
            or type(raw) is not bytes
            or not 0 < len(raw) <= MAX_LOCAL_ARTIFACT_BYTES
        ):
            _fail("V42r3 parent cut escaped the fixed prefix")
        self.verify_root()
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o400,
            dir_fd=self.parent_descriptor,
        )
        try:
            os.fchmod(descriptor, 0o400)
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    _fail("V42r3 parent cut write made no progress")
                view = view[written:]
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
                _fail("V42r3 parent cut inode changed")
            state = _stable_state(observed)
        finally:
            cleanup_error = _close_descriptors_collect([descriptor])
            if cleanup_error is not None and sys.exc_info()[0] is None:
                raise cleanup_error
        os.fsync(self.parent_descriptor)
        if _stable_state(os.stat(
            name, dir_fd=self.parent_descriptor, follow_symlinks=False
        )) != state:
            _fail("V42r3 named parent cut changed after publication")
        self.verify_root()
        return state

    def verify_artifact(self, name: str, state: tuple[int, ...]) -> None:
        self.verify_root()
        if _stable_state(os.stat(
            name, dir_fd=self.descriptor, follow_symlinks=False
        )) != state:
            _fail("V42r3 journal marker changed while effect was pending")

    def verify_parent_anchor(self, name: str, state: tuple[int, ...]) -> None:
        self.verify_root()
        if _stable_state(os.stat(
            name, dir_fd=self.parent_descriptor, follow_symlinks=False
        )) != state:
            _fail("V42r3 parent cut changed while effect was pending")

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            error = _close_descriptors_collect(
                [
                    self.descriptor,
                    *[
                        opened for opened, _, _
                        in reversed(self.directory_chain)
                    ],
                ]
            )
            if error is not None:
                raise error


@dataclass
class _KnownHostsPin:
    descriptor: int
    raw: bytes
    seals: int
    closed: bool = False

    @classmethod
    def open(cls, journal: _JournalPin) -> "_KnownHostsPin":
        journal.verify_root()
        preformal_module = _verified_module(PREFORMAL_MODULE)
        expected = preformal_module.PINNED_KNOWN_HOSTS_BYTES
        raw = _read_regular_at(
            journal.descriptor, KNOWN_HOSTS_NAME,
            MAX_LOCAL_ARTIFACT_BYTES, mode=0o400,
        )
        if (
            type(expected) is not bytes
            or raw != expected
            or not raw.endswith(b"\n")
            or raw.count(b"\n") != 1
        ):
            _fail("V42r3 live known-hosts bytes changed")
        descriptor = os.memfd_create(
            "acfqp-v42r3-known-hosts",
            flags=os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        try:
            os.fchmod(descriptor, 0o400)
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    _fail("V42r3 sealed known-hosts write made no progress")
                view = view[written:]
            os.fsync(descriptor)
            seals = (
                fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW
                | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
            )
            fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals)
            result = cls(descriptor=descriptor, raw=raw, seals=seals)
            result.verify()
            journal.verify_root()
            return result
        except BaseException:
            _close_descriptors_collect([descriptor])
            raise

    @property
    def proc_path(self) -> str:
        return "/proc/" + str(os.getpid()) + "/fd/" + str(self.descriptor)

    def verify(self) -> None:
        if self.closed:
            _fail("V42r3 known-hosts pin is closed")
        observed = os.fstat(self.descriptor)
        proc_observed = os.stat(self.proc_path, follow_symlinks=True)
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o400
            or observed.st_size != len(self.raw)
            or (observed.st_dev, observed.st_ino)
            != (proc_observed.st_dev, proc_observed.st_ino)
            or fcntl.fcntl(self.descriptor, fcntl.F_GET_SEALS) != self.seals
            or os.pread(self.descriptor, len(self.raw) + 1, 0) != self.raw
        ):
            _fail("V42r3 sealed known-hosts pin changed")

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            error = _close_descriptors_collect([self.descriptor])
            if error is not None:
                raise error


def _ensure_journal_root() -> None:
    parent = LOCAL_JOURNAL_ROOT.parent
    chain = _open_directory_chain(parent)
    parent_fd = chain[-1][0]
    root_fd = -1
    try:
        _verify_directory_chain(chain)
        observed_parent = os.fstat(parent_fd)
        if (
            not stat.S_ISDIR(observed_parent.st_mode)
            or observed_parent.st_uid != os.geteuid()
            or parent.resolve(strict=True) != parent
        ):
            _fail("V42r3 journal parent changed")
        created = False
        try:
            previous = os.umask(0o077)
            try:
                os.mkdir(LOCAL_JOURNAL_ROOT.name, 0o700, dir_fd=parent_fd)
                created = True
            finally:
                os.umask(previous)
            os.fsync(parent_fd)
        except FileExistsError:
            pass
        root_fd = os.open(
            LOCAL_JOURNAL_ROOT.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        observed = os.fstat(root_fd)
        named = os.stat(
            LOCAL_JOURNAL_ROOT.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISDIR(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o700
            or observed.st_uid != os.geteuid()
            or observed.st_gid != os.getegid()
            or (observed.st_dev, observed.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("V42r3 journal root changed")
        raw = _canonical_json_bytes(_journal_root_identity(observed))
        if created:
            anchor_name = _anchor_name("ROOT_IDENTITY.json")
            descriptor = os.open(
                anchor_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                0o400,
                dir_fd=parent_fd,
            )
            try:
                os.fchmod(descriptor, 0o400)
                view = memoryview(raw)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        _fail("V42r3 root anchor write made no progress")
                    view = view[written:]
                os.fsync(descriptor)
                anchor_state = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(anchor_state.st_mode)
                    or stat.S_IMODE(anchor_state.st_mode) != 0o400
                    or anchor_state.st_uid != os.geteuid()
                    or anchor_state.st_gid != os.getegid()
                    or anchor_state.st_nlink != 1
                    or anchor_state.st_size != len(raw)
                ):
                    _fail("V42r3 root anchor inode changed")
            finally:
                cleanup_error = _close_descriptors_collect([descriptor])
                if cleanup_error is not None and sys.exc_info()[0] is None:
                    raise cleanup_error
            os.fsync(parent_fd)
        _verify_directory_chain(chain)
        if _read_regular_at(
            parent_fd,
            _anchor_name("ROOT_IDENTITY.json"),
            4096,
            mode=0o400,
        ) != raw:
            _fail("V42r3 root anchor differs from held root")
    finally:
        cleanup_error = _close_descriptors_collect(
            [root_fd, *[descriptor for descriptor, _, _ in reversed(chain)]]
        )
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error
    pin = _JournalPin.open()
    try:
        pin.verify_root()
    finally:
        cleanup_error = _close_resources_collect((pin,))
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error


def _publish_once(name: str, raw: bytes) -> None:
    pin = _JournalPin.open()
    try:
        pin.publish(name, raw)
    finally:
        cleanup_error = _close_resources_collect((pin,))
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error


def _publish_or_verify(name: str, raw: bytes) -> None:
    try:
        _publish_once(name, raw)
    except FileExistsError:
        pin = _JournalPin.open()
        try:
            retained = _read_regular_at(
                pin.descriptor, name, max(len(raw), 1), mode=0o400
            )
        finally:
            cleanup_error = _close_resources_collect((pin,))
            if cleanup_error is not None and sys.exc_info()[0] is None:
                raise cleanup_error
        if retained != raw:
            _fail("retained V42r3 journal artifact changed: " + name)


def _manifest_fact(
    controller_manifest: Mapping[str, Any], relative: str,
) -> dict[str, Any]:
    rows = controller_manifest.get("source_facts")
    if type(rows) is not list:
        _fail("V42r3 controller source facts changed type")
    matches = [
        row for row in rows
        if type(row) is dict and row.get("relative_path") == relative
    ]
    if len(matches) != 1:
        _fail("V42r3 controller source fact is absent or ambiguous: " + relative)
    return dict(matches[0])


def _loader_remote_command_v42r3(
    *, mode: str, loader_raw: bytes, controller_raw: bytes,
    authority_raw: bytes, receiver_raw: bytes, ingress_raw: bytes,
    expected_plan_id: str, legacy_execution_source_manifest_id: str,
) -> str:
    """Build the exact post-login-shell command.

    OpenSSH's daemon, PAM path, selected login shell, and its startup hooks run
    before this command and are an explicitly external transport TCB.  The
    authenticated controller boundary begins only when these loader bytes run;
    this function does not claim pre-loader effect freedom or a root-owned
    forced-command entry.
    """
    if mode not in SSH_MODES:
        _fail("V42r3 remote SSH mode changed")
    if (
        _HEX64.fullmatch(expected_plan_id) is None
        or _HEX64.fullmatch(legacy_execution_source_manifest_id) is None
    ):
        _fail("V42r3 remote command identity changed")
    raws = (
        loader_raw, controller_raw, authority_raw, receiver_raw, ingress_raw
    )
    if any(type(raw) is not bytes or not raw for raw in raws):
        _fail("V42r3 remote command source changed type")
    try:
        loader_source = loader_raw.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise V42FormalTransportSuccessorLauncherError(
            "V42r3 loader is not strict UTF-8"
        ) from error
    arguments = [
        "/usr/bin/python3", "-I", "-S", "-B", "-c", loader_source, mode,
    ]
    for raw in raws:
        arguments.extend((hashlib.sha256(raw).hexdigest(), str(len(raw))))
    arguments.extend(
        (expected_plan_id, legacy_execution_source_manifest_id)
    )
    command = "builtin exec -c " + " ".join(
        shlex.quote(part) for part in arguments
    )
    if len(command.encode("utf-8", errors="strict")) > (
        MAXIMUM_REMOTE_COMMAND_BYTES
    ):
        _fail("V42r3 remote command exceeded the fixed single-argv cap")
    return command


def _ssh_argv_v42r3(*, known_hosts_path: str, remote_command: str) -> tuple[str, ...]:
    expected_known_hosts = str(LOCAL_JOURNAL_ROOT / KNOWN_HOSTS_NAME)
    if known_hosts_path != expected_known_hosts or not remote_command.startswith(
        "builtin exec -c "
    ):
        _fail("V42r3 SSH materialization inputs changed")
    return (
        LOCAL_SSH_EXECUTABLE,
        "-T", "-F", "/dev/null",
        "-oBatchMode=yes",
        "-oPreferredAuthentications=publickey",
        "-oPasswordAuthentication=no",
        "-oKbdInteractiveAuthentication=no",
        "-oGSSAPIAuthentication=no",
        "-oHostbasedAuthentication=no",
        "-oIdentitiesOnly=yes",
        "-oIdentityAgent=none",
        "-oCertificateFile=none",
        "-oStrictHostKeyChecking=yes",
        "-oCheckHostIP=no",
        "-oCanonicalizeHostname=no",
        "-oHostKeyAlgorithms=ssh-ed25519",
        "-oUpdateHostKeys=no",
        "-oVerifyHostKeyDNS=no",
        "-oUserKnownHostsFile=" + known_hosts_path,
        "-oGlobalKnownHostsFile=/dev/null",
        "-oKnownHostsCommand=none",
        "-oControlMaster=no",
        "-oControlPath=none",
        "-oControlPersist=no",
        "-oProxyCommand=none",
        "-oProxyJump=none",
        "-oClearAllForwardings=yes",
        "-oForwardAgent=no",
        "-oForwardX11=no",
        "-oPermitLocalCommand=no",
        "-oRequestTTY=no",
        "-oConnectionAttempts=1",
        "-oNumberOfPasswordPrompts=0",
        "-oSendEnv=-*",
        "-oStdinNull=no",
        "-i", LOCAL_IDENTITY_FILE,
        "-p", str(REMOTE_ENDPOINT_PORT),
        "-l", REMOTE_USER,
        "--", REMOTE_ENDPOINT_HOST,
        remote_command,
    )


def _ssh_execution_argv_v42r3(
    *, transport: "_TransportMaterialization", known_hosts: _KnownHostsPin,
) -> tuple[str, ...]:
    known_hosts.verify()
    fixed = "-oUserKnownHostsFile=" + str(
        LOCAL_JOURNAL_ROOT / KNOWN_HOSTS_NAME
    )
    dynamic = "-oUserKnownHostsFile=" + known_hosts.proc_path
    if transport.argv.count(fixed) != 1 or any(
        argument.startswith("-oUserKnownHostsFile=") and argument != fixed
        for argument in transport.argv
    ):
        _fail("V42r3 fixed known-hosts SSH argument changed")
    argv = tuple(dynamic if argument == fixed else argument for argument in transport.argv)
    if argv.count(dynamic) != 1 or argv[-1] != transport.argv[-1]:
        _fail("V42r3 sealed known-hosts SSH materialization changed")
    return argv


def _prepare_pinned_child(
    *, executable_fd: int, argv: tuple[str, ...], segments: tuple[bytes, ...],
    stdout_cap: int, timeout_seconds: float,
) -> Any:
    sender = _verified_module(SENDER_MODULE)
    preformal_module = _verified_module(PREFORMAL_MODULE)
    if (
        type(stdout_cap) is not int
        or not 0 < stdout_cap <= MAX_LOCAL_ARTIFACT_BYTES
        or type(timeout_seconds) is not float
        or not 0.0 < timeout_seconds <= sender.SENDER_CHILD_TIMEOUT_SECONDS
    ):
        _fail("V42r3 pinned child bounded-resource contract changed")
    descriptors: list[int] = []
    try:
        stdin_read, stdin_write = sender._pipe_cloexec()  # noqa: SLF001
        descriptors.extend((stdin_read, stdin_write))
        stdout_read, stdout_write = sender._pipe_cloexec()  # noqa: SLF001
        descriptors.extend((stdout_read, stdout_write))
        stderr_read, stderr_write = sender._pipe_cloexec()  # noqa: SLF001
        descriptors.extend((stderr_read, stderr_write))
        status_read, status_write = sender._pipe_cloexec()  # noqa: SLF001
        descriptors.extend((status_read, status_write))
        prepared = sender._PreparedPinnedChild(  # noqa: SLF001
            executable_fd=executable_fd,
            argv=argv,
            environment=dict(preformal_module.LOCAL_DISPATCH_ENVIRONMENT),
            segments=segments,
            stdout_cap=stdout_cap,
            stderr_cap=MAX_STDERR_BYTES,
            timeout_seconds=timeout_seconds,
            stdin_read=stdin_read,
            stdin_write=stdin_write,
            stdout_read=stdout_read,
            stdout_write=stdout_write,
            stderr_read=stderr_read,
            stderr_write=stderr_write,
            exec_status_read=status_read,
            exec_status_write=status_write,
        )
        prepared.verify_prepared()
        return prepared
    except BaseException:
        for descriptor in descriptors:
            sender._close_noexcept(descriptor)  # noqa: SLF001
        raise


def _ssh_pin_plan() -> dict[str, Any]:
    preformal_module = _verified_module(PREFORMAL_MODULE)
    return {
        "ssh_client_contract": preformal_module._ssh_client_contract(  # noqa: SLF001
            str(LOCAL_JOURNAL_ROOT / KNOWN_HOSTS_NAME)
        )
    }


@dataclass(frozen=True)
class _TransportMaterialization:
    mode: str
    argv: tuple[str, ...]
    frame: bytes
    remote_command_sha256: str
    expected_plan_id: str
    legacy_execution_source_manifest_id: str


def _verify_transport_ingress_v42r3(
    *, mode: str, controller_manifest: Mapping[str, Any],
    ingress: Mapping[str, Any],
) -> tuple[str, str]:
    formal = _authority()
    controller = formal.verify_controller_source_manifest_v42r3(
        controller_manifest
    )
    controller_raw = _canonical_json_bytes(controller)
    if (
        _AUTHENTICATED_CONTROLLER_MANIFEST_RAW is None
        or controller_raw != _AUTHENTICATED_CONTROLLER_MANIFEST_RAW
    ):
        _fail("transport controller differs from authenticated manifest")
    if not isinstance(ingress, Mapping):
        _fail("V42r3 transport ingress changed type")
    document = json.loads(
        _canonical_json_bytes(dict(ingress)).decode("utf-8", errors="strict")
    )
    if mode == PROBE_MODE:
        plan = formal.verify_formal_host_epoch_probe_plan_v42r3(document)
        if plan["controller_source_manifest_id"] != controller[
            "controller_source_manifest_id"
        ]:
            _fail("host probe ingress/controller join changed")
        return (
            plan["formal_host_epoch_probe_plan_id"],
            plan["legacy_execution_source_manifest_id"],
        )
    expected_schema = {
        "--prepare-once-v42r3": (
            "acfqp.v42_formal_transport_prepare_ingress.v42r3",
            {"schema", "schema_version", "formal_transport_plan",
             "formal_prepare_attempt"},
        ),
        INSPECT_PREPARE_MODE: (
            "acfqp.v42_formal_transport_inspect_prepare_ingress.v42r3",
            {"schema", "schema_version", "formal_transport_plan",
             "formal_prepare_attempt_id", "inspection_ordinal"},
        ),
        "--admit-launch-v42r3": (
            "acfqp.v42_formal_transport_admit_launch_ingress.v42r3",
            {"schema", "schema_version", "formal_transport_plan",
             "prepare_receipt", "local_launch_attempt",
             "formal_launch_transport_attempt"},
        ),
        INSPECT_LAUNCH_MODE: (
            "acfqp.v42_formal_transport_inspect_launch_ingress.v42r3",
            {"schema", "schema_version", "formal_transport_plan",
             "local_launch_attempt_id", "inspection_ordinal"},
        ),
    }.get(mode)
    if (
        expected_schema is None
        or set(document) != expected_schema[1]
        or document.get("schema") != expected_schema[0]
        or document.get("schema_version") != "42.3.0"
    ):
        _fail("V42r3 effect/inspection ingress schema changed")
    plan = formal.verify_formal_transport_plan_v42r3(
        document["formal_transport_plan"]
    )
    if plan["controller_source_manifest_id"] != controller[
        "controller_source_manifest_id"
    ]:
        _fail("transport ingress plan/controller join changed")
    if mode == "--prepare-once-v42r3":
        formal.verify_formal_prepare_attempt_v42r3(
            document["formal_prepare_attempt"], formal_transport_plan=plan
        )
    elif mode in {INSPECT_PREPARE_MODE, INSPECT_LAUNCH_MODE}:
        attempt_field = (
            "formal_prepare_attempt_id"
            if mode == INSPECT_PREPARE_MODE else "local_launch_attempt_id"
        )
        if (
            type(document[attempt_field]) is not str
            or _HEX64.fullmatch(document[attempt_field]) is None
            or type(document["inspection_ordinal"]) is not int
            or not 1 <= document["inspection_ordinal"] <= 4096
        ):
            _fail("V42r3 inspection ingress identity changed")
    else:
        receipt = _verify_scientific_prepare_receipt(
            _canonical_json_bytes(document["prepare_receipt"])
        )
        legacy = _verified_module(LEGACY_AUTHORITY_MODULE)
        local = legacy.verify_local_launch_attempt_v42r1(
            document["local_launch_attempt"], prepare_receipt=receipt
        )
        formal.verify_formal_launch_transport_attempt_v42r3(
            document["formal_launch_transport_attempt"],
            formal_transport_plan=plan,
            prepare_receipt=receipt,
            local_launch_attempt=local,
        )
    return (
        plan["formal_transport_plan_id"],
        plan["legacy_execution_source_manifest_id"],
    )


def _verify_transport_materialization(
    transport: _TransportMaterialization, *,
    controller_manifest: Mapping[str, Any], ingress: Mapping[str, Any],
) -> None:
    if (
        type(transport) is not _TransportMaterialization
        or transport.mode not in SSH_MODES
        or type(transport.argv) is not tuple
        or not transport.argv
        or type(transport.frame) is not bytes
        or not transport.frame
        or _HEX64.fullmatch(transport.expected_plan_id) is None
        or _HEX64.fullmatch(transport.legacy_execution_source_manifest_id)
        is None
        or hashlib.sha256(
            transport.argv[-1].encode("utf-8", errors="strict")
        ).hexdigest() != transport.remote_command_sha256
    ):
        _fail("V42r3 transport authorization changed")
    expected_plan_id, expected_legacy_id = _verify_transport_ingress_v42r3(
        mode=transport.mode,
        controller_manifest=controller_manifest,
        ingress=ingress,
    )
    if (
        transport.expected_plan_id != expected_plan_id
        or transport.legacy_execution_source_manifest_id != expected_legacy_id
    ):
        _fail("V42r3 transport identity differs from verified ingress")
    expected_ssh = _ssh_argv_v42r3(
        known_hosts_path=str(LOCAL_JOURNAL_ROOT / KNOWN_HOSTS_NAME),
        remote_command=transport.argv[-1],
    )
    if transport.argv != expected_ssh:
        _fail("V42r3 transport SSH argv changed")
    prefix = "builtin exec -c "
    if not transport.argv[-1].startswith(prefix):
        _fail("V42r3 remote command framing changed")
    remote_arguments = shlex.split(transport.argv[-1][len(prefix):])
    if (
        len(remote_arguments) != 19
        or remote_arguments[:5] != [
            "/usr/bin/python3", "-I", "-S", "-B", "-c"
        ]
        or remote_arguments[6] != transport.mode
        or remote_arguments[-2] != transport.expected_plan_id
        or remote_arguments[-1]
        != transport.legacy_execution_source_manifest_id
    ):
        _fail("V42r3 transport loader argv changed")
    loader_module = _verified_module(LOADER_MODULE)
    sections = loader_module._decode_probe_frame_bytes(  # noqa: SLF001
        transport.frame
    )
    raws = (remote_arguments[5].encode("utf-8", errors="strict"), *sections)
    cursor = 7
    for raw in raws:
        if remote_arguments[cursor:cursor + 2] != [
            hashlib.sha256(raw).hexdigest(), str(len(raw))
        ]:
            _fail("V42r3 transport command/frame fact changed")
        cursor += 2
    expected = _transport_materialization_v42r3(
        mode=transport.mode,
        controller_manifest=controller_manifest,
        ingress=ingress,
        expected_plan_id=expected_plan_id,
        legacy_execution_source_manifest_id=expected_legacy_id,
    )
    if transport != expected:
        _fail("V42r3 transport differs from exact authenticated reconstruction")


def _dispatch_read_only_v42r3(
    *, transport: _TransportMaterialization,
    controller_manifest: Mapping[str, Any] | None = None,
    ingress: Mapping[str, Any] | None = None,
    stdout_cap: int,
    timeout_seconds: float = READ_ONLY_TIMEOUT_SECONDS,
) -> Any:
    _require_sealed_stage_materials()
    if type(transport) is not _TransportMaterialization or (
        transport.mode not in READ_ONLY_SSH_MODES
    ):
        _fail("V42r3 read-only dispatch authorization changed")
    if controller_manifest is None or ingress is None:
        _fail("V42r3 read-only dispatch omitted authenticated context")
    _verify_transport_materialization(
        transport, controller_manifest=controller_manifest, ingress=ingress
    )
    journal = None
    known_hosts = None
    pins = None
    prepared = None
    try:
        journal = _JournalPin.open()
        known_hosts = _KnownHostsPin.open(journal)
        sender = _verified_module(SENDER_MODULE)
        plan = _ssh_pin_plan()
        pins = sender._open_local_dispatch_pins_v42r1(plan)  # noqa: SLF001
        fingerprint = sender._derive_identity_fingerprint_v42r1(  # noqa: SLF001
            plan=plan, pins=pins
        )
        if fingerprint != plan["ssh_client_contract"][
            "identity_public_fingerprint"
        ]:
            _fail("V42r3 read-only SSH identity fingerprint changed")
        prepared = _prepare_pinned_child(
            executable_fd=pins.ssh.descriptor,
            argv=_ssh_execution_argv_v42r3(
                transport=transport, known_hosts=known_hosts
            ),
            segments=(transport.frame,),
            stdout_cap=stdout_cap,
            timeout_seconds=float(timeout_seconds),
        )
        journal.verify_root()
        known_hosts.verify()
        pins.verify()
        observation = prepared.spawn_and_pump()
        known_hosts.verify()
        journal.verify_root()
        pins.verify()
        return observation
    finally:
        cleanup_error = _close_resources_collect(
            (prepared, pins, known_hosts, journal)
        )
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error


def _dispatch_effect_once_v42r3(
    *, operation: str, attempt_id: str,
    transport: _TransportMaterialization,
    controller_manifest: Mapping[str, Any] | None = None,
    ingress: Mapping[str, Any] | None = None,
    formal_transport_plan: Mapping[str, Any] | None = None,
    marker_name: str, marker_raw: bytes,
    expected_predecessor_formal_prefix: Mapping[str, Any],
    stdout_cap: int, timeout_seconds: float,
) -> tuple[Any | None, bool, BaseException | None]:
    _require_sealed_stage_materials()
    expected_mode = {
        "PREPARE": "--prepare-once-v42r3",
        "LAUNCH": "--admit-launch-v42r3",
    }.get(operation)
    expected_marker = {
        "PREPARE": LOCAL_PREPARE_NETWORK_START_NAME,
        "LAUNCH": LOCAL_LAUNCH_NETWORK_START_NAME,
    }.get(operation)
    if (
        expected_mode is None
        or transport.mode != expected_mode
        or marker_name != expected_marker
        or _HEX64.fullmatch(attempt_id) is None
        or type(marker_raw) is not bytes
        or not 0 < len(marker_raw) <= MAX_LOCAL_ARTIFACT_BYTES
    ):
        _fail("V42r3 effect dispatch authorization changed")
    if (
        controller_manifest is None
        or ingress is None
        or formal_transport_plan is None
    ):
        _fail("V42r3 effect dispatch omitted authenticated context")
    _verify_transport_materialization(
        transport, controller_manifest=controller_manifest, ingress=ingress
    )
    formal = _authority()
    plan_document = formal.verify_formal_transport_plan_v42r3(
        formal_transport_plan
    )
    marker_document = formal.verify_network_start_v42r3(
        marker_raw, formal_transport_plan=plan_document
    )
    if (
        _canonical_json_bytes(marker_document) != marker_raw
        or marker_document["operation"] != operation
        or marker_document["attempt_id"] != attempt_id
        or marker_document["formal_transport_plan_id"]
        != transport.expected_plan_id
    ):
        _fail("V42r3 network-start marker/transport join changed")
    ingress_attempt_id = (
        ingress.get("formal_prepare_attempt", {}).get(
            "formal_prepare_attempt_id"
        )
        if operation == "PREPARE"
        else ingress.get("local_launch_attempt", {}).get(
            "local_launch_attempt_id"
        )
    )
    if ingress_attempt_id != attempt_id:
        _fail("V42r3 effect ingress/marker attempt join changed")
    native_module = _verified_module(NATIVE_DRIVER_MODULE)
    if native_module.verify_failed_v42r1_formal_prefix_read_only() != dict(
        expected_predecessor_formal_prefix
    ):
        _fail("failed V42r1 formal prefix changed before effect cut")
    cut_name = _anchor_name(
        "NETWORK_START." + operation + "." + attempt_id + ".json"
    )
    journal = _JournalPin.open()
    try:
        cut_exists = (
            journal.exists(marker_name)
            or journal.parent_anchor_exists(cut_name)
        )
    except BaseException:
        _close_resources_collect((journal,))
        raise
    if cut_exists:
        cleanup_error = _close_resources_collect((journal,))
        if cleanup_error is not None:
            raise cleanup_error
        _fail("V42r3 effect cut exists; same identity replay is forbidden")
    known_hosts = None
    pins = None
    prepared = None
    sigpipe = None
    marker_may_have_started = False
    observation = None
    failure: BaseException | None = None
    marker_state: tuple[int, ...] | None = None
    cut_state: tuple[int, ...] | None = None
    try:
        known_hosts = _KnownHostsPin.open(journal)
        sender = _verified_module(SENDER_MODULE)
        ssh_plan = _ssh_pin_plan()
        pins = sender._open_local_dispatch_pins_v42r1(  # noqa: SLF001
            ssh_plan
        )
        fingerprint = sender._derive_identity_fingerprint_v42r1(  # noqa: SLF001
            plan=ssh_plan, pins=pins
        )
        if fingerprint != ssh_plan["ssh_client_contract"][
            "identity_public_fingerprint"
        ]:
            _fail("V42r3 effect SSH identity fingerprint changed")
        prepared = _prepare_pinned_child(
            executable_fd=pins.ssh.descriptor,
            argv=_ssh_execution_argv_v42r3(
                transport=transport, known_hosts=known_hosts
            ),
            segments=(transport.frame,),
            stdout_cap=stdout_cap,
            timeout_seconds=float(timeout_seconds),
        )
        sigpipe = sender._SigpipeIgnoreGuard.acquire()  # noqa: SLF001
        prepared.verify_prepared()
        known_hosts.verify()
        pins.verify()
        sigpipe.verify()
        journal.verify_root()
        if native_module.verify_failed_v42r1_formal_prefix_read_only() != dict(
            expected_predecessor_formal_prefix
        ):
            _fail("failed V42r1 formal prefix changed at effect cut")
        _verify_transport_materialization(
            transport,
            controller_manifest=controller_manifest,
            ingress=ingress,
        )
        if formal.verify_network_start_v42r3(
            marker_raw, formal_transport_plan=plan_document
        ) != marker_document:
            _fail("V42r3 network-start marker changed at effect cut")
        marker_may_have_started = True
        cut_state = journal.publish_parent_anchor(cut_name, marker_raw)
        marker_state = journal.publish(marker_name, marker_raw)
        prepared.verify_prepared()
        known_hosts.verify()
        pins.verify()
        sigpipe.verify()
        journal.verify_parent_anchor(cut_name, cut_state)
        journal.verify_artifact(marker_name, marker_state)
        observation = prepared.spawn_and_pump()
        sigpipe.verify()
        known_hosts.verify()
        pins.verify()
        journal.verify_parent_anchor(cut_name, cut_state)
        journal.verify_artifact(marker_name, marker_state)
    except BaseException as error:
        failure = error
        if not marker_may_have_started:
            try:
                marker_may_have_started = (
                    journal is not None
                    and (
                        journal.exists(marker_name)
                        or journal.parent_anchor_exists(cut_name)
                    )
                )
            except BaseException:
                marker_may_have_started = True
    finally:
        cleanup_error = _close_resources_collect(
            (prepared, pins, sigpipe, known_hosts, journal)
        )
        if failure is None and cleanup_error is not None:
            failure = cleanup_error
    return observation, marker_may_have_started, failure


def _observation_closed_exactly(observation: Any) -> bool:
    return bool(
        observation is not None
        and observation.exec_succeeded
        and observation.returncode == 0
        and not observation.timed_out
        and observation.stdin_complete
        and observation.stdin_sent_byte_count
        == observation.stdin_expected_byte_count
        and not observation.stdout_overflow
        and observation.stdout_eof
        and observation.stdout_total_byte_count == len(observation.stdout_raw)
        and observation.stderr_total_byte_count == 0
        and observation.stderr_eof
    )


def _host_probe_child_observation_fact(observation: Any) -> dict[str, Any]:
    if (
        observation is None
        or type(observation.stdout_raw) is not bytes
        or type(observation.stderr_prefix) is not bytes
    ):
        _fail("V42r3r1 host probe child observation bytes changed")
    prefix_cap = 4096
    stdout_prefix = observation.stdout_raw[:prefix_cap]
    stderr_prefix = observation.stderr_prefix[:prefix_cap]
    return {
        "exec_succeeded": observation.exec_succeeded,
        "returncode": observation.returncode,
        "timed_out": observation.timed_out,
        "stdin_expected_byte_count": observation.stdin_expected_byte_count,
        "stdin_sent_byte_count": observation.stdin_sent_byte_count,
        "stdin_complete": observation.stdin_complete,
        "stdout_retained_byte_count": len(observation.stdout_raw),
        "stdout_retained_sha256": hashlib.sha256(
            observation.stdout_raw
        ).hexdigest(),
        "stdout_prefix_byte_count": len(stdout_prefix),
        "stdout_prefix_hex": stdout_prefix.hex(),
        "stdout_total_byte_count": observation.stdout_total_byte_count,
        "stdout_sha256": observation.stdout_sha256,
        "stdout_overflow": observation.stdout_overflow,
        "stdout_eof": observation.stdout_eof,
        "stderr_prefix_byte_count": len(stderr_prefix),
        "stderr_prefix_hex": stderr_prefix.hex(),
        "stderr_total_byte_count": observation.stderr_total_byte_count,
        "stderr_sha256": observation.stderr_sha256,
        "stderr_overflow": observation.stderr_overflow,
        "stderr_eof": observation.stderr_eof,
    }


def _host_probe_failure_fact(error: BaseException) -> dict[str, Any]:
    failure_type = type(error).__module__ + "." + type(error).__qualname__
    message_raw = str(error).encode("utf-8", errors="backslashreplace")
    prefix = message_raw[:4096]
    return {
        "failure_type": failure_type,
        "message_byte_count": len(message_raw),
        "message_sha256": hashlib.sha256(message_raw).hexdigest(),
        "message_prefix_byte_count": len(prefix),
        "message_prefix_hex": prefix.hex(),
    }


def _strip_canonical_stdout(raw: bytes, label: str) -> bytes:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail(label + " stdout is not one canonical document plus newline")
    return raw[:-1]


def _transport_materialization_v42r3(
    *, mode: str, controller_manifest: Mapping[str, Any], ingress: Mapping[str, Any],
    expected_plan_id: str, legacy_execution_source_manifest_id: str,
) -> _TransportMaterialization:
    controller_raw = _canonical_json_bytes(dict(controller_manifest))
    ingress_raw = _canonical_json_bytes(dict(ingress))
    loader_raw = _verified_source_raw(LOADER_RELATIVE)
    authority_raw = _verified_source_raw(AUTHORITY_RELATIVE)
    receiver_raw = _verified_source_raw(RECEIVER_RELATIVE)
    for relative, raw in (
        (LOADER_RELATIVE, loader_raw),
        (AUTHORITY_RELATIVE, authority_raw),
        (RECEIVER_RELATIVE, receiver_raw),
    ):
        fact = _manifest_fact(controller_manifest, relative)
        if (
            fact.get("byte_count") != len(raw)
            or fact.get("sha256") != hashlib.sha256(raw).hexdigest()
        ):
            _fail("V42r3 transported source differs from controller: " + relative)
    command = _loader_remote_command_v42r3(
        mode=mode,
        loader_raw=loader_raw,
        controller_raw=controller_raw,
        authority_raw=authority_raw,
        receiver_raw=receiver_raw,
        ingress_raw=ingress_raw,
        expected_plan_id=expected_plan_id,
        legacy_execution_source_manifest_id=(
            legacy_execution_source_manifest_id
        ),
    )
    argv = _ssh_argv_v42r3(
        known_hosts_path=str(LOCAL_JOURNAL_ROOT / KNOWN_HOSTS_NAME),
        remote_command=command,
    )
    loader_module = _verified_module(LOADER_MODULE)
    frame = loader_module.build_probe_frame_v42r3(
        controller_manifest_raw=controller_raw,
        authority_raw=authority_raw,
        receiver_raw=receiver_raw,
        ingress_raw=ingress_raw,
    )
    return _TransportMaterialization(
        mode=mode,
        argv=argv,
        frame=frame,
        remote_command_sha256=hashlib.sha256(
            command.encode("utf-8", errors="strict")
        ).hexdigest(),
        expected_plan_id=expected_plan_id,
        legacy_execution_source_manifest_id=(
            legacy_execution_source_manifest_id
        ),
    )


def _read_journal_artifact(name: str, cap: int) -> bytes:
    pin = _JournalPin.open()
    try:
        return _read_regular_at(pin.descriptor, name, cap, mode=0o400)
    finally:
        cleanup_error = _close_resources_collect((pin,))
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error


def _read_optional_journal_artifact(name: str, cap: int) -> bytes | None:
    try:
        return _read_journal_artifact(name, cap)
    except FileNotFoundError:
        return None


def _initialize_probe_journal_v42r3(
    *, controller_manifest: Mapping[str, Any],
    native_activation_binding: Mapping[str, Any],
    probe_plan: Mapping[str, Any],
) -> None:
    _ensure_journal_root()
    preformal_module = _verified_module(PREFORMAL_MODULE)
    known_hosts_raw = preformal_module.PINNED_KNOWN_HOSTS_BYTES
    if (
        type(known_hosts_raw) is not bytes
        or not known_hosts_raw.endswith(b"\n")
        or known_hosts_raw.count(b"\n") != 1
    ):
        _fail("V42r3 pinned known-hosts bytes changed")
    for name, raw in (
        (KNOWN_HOSTS_NAME, known_hosts_raw),
        (CONTROLLER_MANIFEST_NAME, _canonical_json_bytes(dict(controller_manifest))),
        (NATIVE_BINDING_NAME, _canonical_json_bytes(dict(native_activation_binding))),
        (HOST_PROBE_PLAN_NAME, _canonical_json_bytes(dict(probe_plan))),
    ):
        _publish_or_verify(name, raw)


def _probe_host_epoch_v42r3(
    *, controller_manifest: Mapping[str, Any],
    verified_native_inputs: Any,
    native_activation_binding: Mapping[str, Any],
) -> dict[str, Any]:
    formal = _authority()
    legacy_id = native_activation_binding.get("source_manifest_id")
    if type(legacy_id) is not str or _HEX64.fullmatch(legacy_id) is None:
        _fail("V42r3 legacy execution source manifest ID changed")
    probe_plan = formal.build_formal_host_epoch_probe_plan_v42r3(
        controller_source_manifest=dict(controller_manifest),
        native_activation_binding=dict(native_activation_binding),
        legacy_execution_source_manifest_id=legacy_id,
    )
    if formal.verify_formal_host_epoch_probe_plan_v42r3(probe_plan) != probe_plan:
        _fail("V42r3 authority changed the probe plan")
    if verified_native_inputs.predecessor_formal_prefix != (
        _verified_module(NATIVE_DRIVER_MODULE)
        .verify_failed_v42r1_formal_prefix_read_only()
    ):
        _fail("failed V42r1 formal prefix changed before host probe")
    _initialize_probe_journal_v42r3(
        controller_manifest=controller_manifest,
        native_activation_binding=native_activation_binding,
        probe_plan=probe_plan,
    )
    retained_attempt_raw = _read_optional_journal_artifact(
        HOST_PROBE_ATTEMPT_NAME, MAX_LOCAL_ARTIFACT_BYTES
    )
    retained_observation_raw = _read_optional_journal_artifact(
        HOST_PROBE_OBSERVATION_NAME, MAX_LOCAL_ARTIFACT_BYTES
    )
    retained_failure_raw = _read_optional_journal_artifact(
        HOST_PROBE_FAILURE_NAME, MAX_LOCAL_ARTIFACT_BYTES
    )
    retained_raw = _read_optional_journal_artifact(
        HOST_RECEIPT_NAME, MAX_LOCAL_ARTIFACT_BYTES
    )
    if retained_raw is None:
        if retained_attempt_raw is not None:
            attempt = formal.verify_formal_host_epoch_probe_attempt_v42r3r1(
                retained_attempt_raw, probe_plan=probe_plan
            )
            if (
                retained_observation_raw is not None
                and retained_failure_raw is not None
            ):
                _fail("V42r3r1 host probe retained incompatible terminal records")
            if retained_observation_raw is not None:
                formal.verify_formal_host_epoch_transport_observation_v42r3r1(
                    retained_observation_raw,
                    probe_plan=probe_plan,
                    probe_attempt=attempt,
                )
            if retained_failure_raw is not None:
                formal.verify_formal_host_epoch_dispatch_failure_v42r3r1(
                    retained_failure_raw,
                    probe_plan=probe_plan,
                    probe_attempt=attempt,
                )
            _fail(
                "retained V42r3r1 host probe attempt has no authenticated "
                "receipt; controller replay is forbidden"
            )
        if retained_observation_raw is not None or retained_failure_raw is not None:
            _fail("V42r3r1 host probe terminal record lacks its attempt cut")
        transport = _transport_materialization_v42r3(
            mode=PROBE_MODE,
            controller_manifest=controller_manifest,
            ingress=probe_plan,
            expected_plan_id=probe_plan["formal_host_epoch_probe_plan_id"],
            legacy_execution_source_manifest_id=legacy_id,
        )
        attempt = formal.build_formal_host_epoch_probe_attempt_v42r3r1(
            probe_plan=probe_plan
        )
        if formal.verify_formal_host_epoch_probe_attempt_v42r3r1(
            attempt, probe_plan=probe_plan
        ) != attempt:
            _fail("V42r3r1 authority changed the host probe attempt")
        _publish_once(
            HOST_PROBE_ATTEMPT_NAME, _canonical_json_bytes(attempt)
        )
        try:
            observation = _dispatch_read_only_v42r3(
                transport=transport,
                controller_manifest=controller_manifest,
                ingress=probe_plan,
                stdout_cap=MAX_LOCAL_ARTIFACT_BYTES,
            )
        except BaseException as error:
            failure = formal.build_formal_host_epoch_dispatch_failure_v42r3r1(
                probe_plan=probe_plan,
                probe_attempt=attempt,
                failure_fact=_host_probe_failure_fact(error),
            )
            if formal.verify_formal_host_epoch_dispatch_failure_v42r3r1(
                failure,
                probe_plan=probe_plan,
                probe_attempt=attempt,
            ) != failure:
                _fail("V42r3r1 authority changed the host dispatch failure")
            _publish_once(
                HOST_PROBE_FAILURE_NAME, _canonical_json_bytes(failure)
            )
            raise
        transport_observation = (
            formal.build_formal_host_epoch_transport_observation_v42r3r1(
                probe_plan=probe_plan,
                probe_attempt=attempt,
                child_observation=_host_probe_child_observation_fact(
                    observation
                ),
            )
        )
        if formal.verify_formal_host_epoch_transport_observation_v42r3r1(
            transport_observation,
            probe_plan=probe_plan,
            probe_attempt=attempt,
        ) != transport_observation:
            _fail("V42r3r1 authority changed the host transport observation")
        _publish_once(
            HOST_PROBE_OBSERVATION_NAME,
            _canonical_json_bytes(transport_observation),
        )
        if not transport_observation["process_closed_exactly"]:
            _fail(
                "V42r3r1 read-only host probe did not close exactly; "
                "observation retained and controller replay forbidden"
            )
        retained_raw = _strip_canonical_stdout(
            observation.stdout_raw, "V42r3r1 host probe"
        )
        receipt = formal.verify_formal_host_epoch_transport_receipt_join_v42r3r1(
            transport_observation=transport_observation,
            probe_plan=probe_plan,
            probe_attempt=attempt,
            receipt_raw=retained_raw,
        )
        if receipt.get("formal_host_epoch_probe_plan_id") != probe_plan[
            "formal_host_epoch_probe_plan_id"
        ]:
            _fail("V42r3r1 host receipt/probe plan join changed")
        _publish_once(HOST_RECEIPT_NAME, retained_raw)
    else:
        if (
            retained_attempt_raw is None
            or retained_observation_raw is None
            or retained_failure_raw is not None
        ):
            _fail("retained V42r3r1 host receipt lacks its local one-shot chain")
        attempt = formal.verify_formal_host_epoch_probe_attempt_v42r3r1(
            retained_attempt_raw, probe_plan=probe_plan
        )
        transport_observation = (
            formal.verify_formal_host_epoch_transport_observation_v42r3r1(
                retained_observation_raw,
                probe_plan=probe_plan,
                probe_attempt=attempt,
            )
        )
        if not transport_observation["process_closed_exactly"]:
            _fail("retained V42r3r1 host receipt follows a nonexact transport")
        receipt = formal.verify_formal_host_epoch_transport_receipt_join_v42r3r1(
            transport_observation=transport_observation,
            probe_plan=probe_plan,
            probe_attempt=attempt,
            receipt_raw=retained_raw,
        )
        if receipt.get("formal_host_epoch_probe_plan_id") != probe_plan[
            "formal_host_epoch_probe_plan_id"
        ]:
            _fail("retained V42r3r1 host receipt/probe plan join changed")
    if verified_native_inputs.predecessor_formal_prefix != (
        _verified_module(NATIVE_DRIVER_MODULE)
        .verify_failed_v42r1_formal_prefix_read_only()
    ):
        _fail("failed V42r1 formal prefix changed across host probe")
    return receipt


def _verify_scientific_prepare_receipt(raw: bytes) -> dict[str, Any]:
    legacy = _verified_module(LEGACY_AUTHORITY_MODULE)
    prereg = _verified_module(PREREGISTRATION_MODULE)
    receipt = legacy.verify_prepare_receipt_v42(
        raw,
        fresh_terminal_preregistration_id=prereg.PREREGISTRATION_ID,
        history_freshness_manifest_id=prereg._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
        require_live_source=False,
    )
    if type(receipt) is not dict:
        _fail("scientific prepare receipt changed type")
    return receipt


def _build_retained_formal_context_v42r3(
    *, controller_manifest: Mapping[str, Any],
    native_activation_binding: Mapping[str, Any],
    allow_plan_publication: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    formal = _authority()
    legacy_id = native_activation_binding.get("source_manifest_id")
    probe_plan = formal.build_formal_host_epoch_probe_plan_v42r3(
        controller_source_manifest=dict(controller_manifest),
        native_activation_binding=dict(native_activation_binding),
        legacy_execution_source_manifest_id=legacy_id,
    )
    retained_probe_raw = _read_journal_artifact(
        HOST_PROBE_PLAN_NAME, MAX_LOCAL_ARTIFACT_BYTES
    )
    if retained_probe_raw != _canonical_json_bytes(probe_plan):
        _fail("retained V42r3 probe plan changed")
    if _read_optional_journal_artifact(
        HOST_PROBE_FAILURE_NAME, MAX_LOCAL_ARTIFACT_BYTES
    ) is not None:
        _fail("retained V42r3r1 host probe has a dispatch failure record")
    probe_attempt = formal.verify_formal_host_epoch_probe_attempt_v42r3r1(
        _read_journal_artifact(
            HOST_PROBE_ATTEMPT_NAME, MAX_LOCAL_ARTIFACT_BYTES
        ),
        probe_plan=probe_plan,
    )
    probe_transport_observation = (
        formal.verify_formal_host_epoch_transport_observation_v42r3r1(
            _read_journal_artifact(
                HOST_PROBE_OBSERVATION_NAME, MAX_LOCAL_ARTIFACT_BYTES
            ),
            probe_plan=probe_plan,
            probe_attempt=probe_attempt,
        )
    )
    if not probe_transport_observation["process_closed_exactly"]:
        _fail("retained V42r3r1 host probe transport did not close exactly")
    host_receipt_raw = _read_journal_artifact(
        HOST_RECEIPT_NAME, MAX_LOCAL_ARTIFACT_BYTES
    )
    host_receipt = (
        formal.verify_formal_host_epoch_transport_receipt_join_v42r3r1(
            transport_observation=probe_transport_observation,
            probe_plan=probe_plan,
            probe_attempt=probe_attempt,
            receipt_raw=host_receipt_raw,
        )
    )
    if host_receipt.get("formal_host_epoch_probe_plan_id") != probe_plan[
        "formal_host_epoch_probe_plan_id"
    ]:
        _fail("retained V42r3 host receipt/probe plan join changed")
    plan = formal.build_formal_transport_plan_v42r3(
        controller_source_manifest=dict(controller_manifest),
        native_activation_binding=dict(native_activation_binding),
        host_epoch_probe_plan=probe_plan,
        host_epoch_receipt=host_receipt,
        legacy_execution_source_manifest_id=legacy_id,
        known_hosts_path=str(LOCAL_JOURNAL_ROOT / KNOWN_HOSTS_NAME),
        local_journal_root=str(LOCAL_JOURNAL_ROOT),
        remote_journal_root=REMOTE_JOURNAL_ROOT,
    )
    if formal.verify_formal_transport_plan_v42r3(plan) != plan:
        _fail("V42r3 authority changed the formal transport plan")
    plan_raw = _canonical_json_bytes(plan)
    if allow_plan_publication:
        _publish_or_verify(LOCAL_PLAN_NAME, plan_raw)
    elif _read_journal_artifact(
        LOCAL_PLAN_NAME, MAX_LOCAL_ARTIFACT_BYTES
    ) != plan_raw:
        _fail("retained V42r3 formal plan changed before inspection")
    return probe_plan, host_receipt, plan


def _prepare_ingress_v42r3(
    plan: Mapping[str, Any], attempt: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42_formal_transport_prepare_ingress.v42r3",
        "schema_version": "42.3.0",
        "formal_transport_plan": dict(plan),
        "formal_prepare_attempt": dict(attempt),
    }


def _launch_ingress_v42r3(
    plan: Mapping[str, Any], prepare_receipt: Mapping[str, Any],
    local_launch_attempt: Mapping[str, Any],
    transport_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42_formal_transport_admit_launch_ingress.v42r3",
        "schema_version": "42.3.0",
        "formal_transport_plan": dict(plan),
        "prepare_receipt": dict(prepare_receipt),
        "local_launch_attempt": dict(local_launch_attempt),
        "formal_launch_transport_attempt": dict(transport_attempt),
    }


def _inspection_ingress_v42r3(
    *, plan: Mapping[str, Any], operation: str, attempt_id: str,
    inspection_ordinal: int,
) -> dict[str, Any]:
    if (
        operation not in {"PREPARE", "LAUNCH"}
        or _HEX64.fullmatch(attempt_id) is None
        or type(inspection_ordinal) is not int
        or not 1 <= inspection_ordinal <= 4096
    ):
        _fail("V42r3 inspection ingress authorization changed")
    if operation == "PREPARE":
        schema = "acfqp.v42_formal_transport_inspect_prepare_ingress.v42r3"
        attempt_field = "formal_prepare_attempt_id"
    else:
        schema = "acfqp.v42_formal_transport_inspect_launch_ingress.v42r3"
        attempt_field = "local_launch_attempt_id"
    return {
        "schema": schema,
        "schema_version": "42.3.0",
        "formal_transport_plan": dict(plan),
        attempt_field: attempt_id,
        "inspection_ordinal": inspection_ordinal,
    }


def _effect_cut_present_v42r3(
    *, formal_transport_plan: Mapping[str, Any],
    operation: str, attempt_id: str,
) -> bool:
    formal = _authority()
    plan = formal.verify_formal_transport_plan_v42r3(formal_transport_plan)
    marker_name = {
        "PREPARE": LOCAL_PREPARE_NETWORK_START_NAME,
        "LAUNCH": LOCAL_LAUNCH_NETWORK_START_NAME,
    }.get(operation)
    if marker_name is None or _HEX64.fullmatch(attempt_id) is None:
        _fail("V42r3 effect-cut query changed")
    cut_name = _anchor_name(
        "NETWORK_START." + operation + "." + attempt_id + ".json"
    )
    expected = formal.build_network_start_v42r3(
        formal_transport_plan=plan,
        operation=operation,
        attempt_id=attempt_id,
    )
    expected_raw = _canonical_json_bytes(expected)
    journal = _JournalPin.open()
    try:
        inner = journal.exists(marker_name)
        outer = journal.parent_anchor_exists(cut_name)
        if inner and _read_regular_at(
            journal.descriptor, marker_name,
            MAX_LOCAL_ARTIFACT_BYTES, mode=0o400,
        ) != expected_raw:
            _fail("V42r3 retained inner network cut changed")
        if outer and _read_regular_at(
            journal.parent_descriptor, cut_name,
            MAX_LOCAL_ARTIFACT_BYTES, mode=0o400,
        ) != expected_raw:
            _fail("V42r3 retained parent network cut changed")
        return inner or outer
    finally:
        cleanup_error = _close_resources_collect((journal,))
        if cleanup_error is not None and sys.exc_info()[0] is None:
            raise cleanup_error


def _publish_outcome_v42r3(
    *, formal_transport_plan: Mapping[str, Any], operation: str,
    attempt_id: str, outcome_class: str, receipt_raw: bytes | None,
) -> dict[str, Any]:
    formal = _authority()
    outcome = formal.build_operation_outcome_v42r3(
        formal_transport_plan=formal_transport_plan,
        operation=operation,
        attempt_id=attempt_id,
        outcome_class=outcome_class,
        receipt_raw=receipt_raw,
    )
    if formal.verify_operation_outcome_v42r3(
        outcome,
        formal_transport_plan=formal_transport_plan,
        operation=operation,
        attempt_id=attempt_id,
        receipt_raw=receipt_raw,
    ) != outcome:
        _fail("V42r3 operation outcome authority changed")
    raw = _canonical_json_bytes(outcome)
    if outcome_class == formal.OUTCOME_PRE_NETWORK_FAILURE:
        prefix = PRE_NETWORK_FAILURE_PREFIX[operation]
        journal = _JournalPin.open()
        try:
            for ordinal in range(1, 4097):
                name = prefix + f".{ordinal:08d}.json"
                if journal.exists(name):
                    continue
                try:
                    journal.publish(name, raw)
                except FileExistsError:
                    continue
                break
            else:
                _fail("V42r3 pre-network failure journal exhausted")
        finally:
            cleanup_error = _close_resources_collect((journal,))
            if cleanup_error is not None and sys.exc_info()[0] is None:
                raise cleanup_error
    else:
        name = (
            PREPARE_OUTCOME_NAME
            if operation == "PREPARE" else LAUNCH_OUTCOME_NAME
        )
        _publish_or_verify(name, raw)
    return outcome


def _retained_terminal_outcome_v42r3(
    *, formal_transport_plan: Mapping[str, Any], operation: str,
    attempt_id: str,
) -> dict[str, Any] | None:
    formal = _authority()
    name = (
        PREPARE_OUTCOME_NAME
        if operation == "PREPARE" else LAUNCH_OUTCOME_NAME
    )
    try:
        raw = _read_journal_artifact(name, MAX_LOCAL_ARTIFACT_BYTES)
    except FileNotFoundError:
        return None
    value = json.loads(raw.decode("utf-8", errors="strict"))
    receipt_raw = None
    if value.get("outcome_class") == formal.OUTCOME_COMPLETE_EXACT_RECEIPT:
        receipt_name = (
            LOCAL_PREPARE_RECEIPT_NAME
            if operation == "PREPARE" else LOCAL_LAUNCH_ADMISSION_NAME
        )
        receipt_raw = _read_journal_artifact(
            receipt_name, MAX_LOCAL_ARTIFACT_BYTES
        )
    outcome = formal.verify_operation_outcome_v42r3(
        raw,
        formal_transport_plan=formal_transport_plan,
        operation=operation,
        attempt_id=attempt_id,
        receipt_raw=receipt_raw,
    )
    if (
        outcome["controller_same_effect_dispatch_replay_allowed"] is not False
        or outcome["network_start_marker_present"] is not True
    ):
        _fail("retained V42r3 terminal outcome changed replay semantics")
    return outcome


def _retained_prepare_v42r3(
    formal_transport_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    raw = _read_journal_artifact(
        LOCAL_PREPARE_RECEIPT_NAME, MAX_LOCAL_ARTIFACT_BYTES
    )
    receipt = _verify_scientific_prepare_receipt(raw)
    if any(
        receipt[field] != formal_transport_plan[field]
        for field in (
            "source_commit", "source_tree", "source_manifest_id",
            "transport_manifest_id",
        )
    ):
        _fail("retained scientific prepare receipt differs from V42r3 plan")
    return receipt, raw


def _load_or_issue_local_launch_attempt_v42r3(
    *, formal_transport_plan: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any], prepare_receipt_raw: bytes,
) -> dict[str, Any]:
    runner = _verified_module(SCIENTIFIC_RUNNER_MODULE)
    legacy = _verified_module(LEGACY_AUTHORITY_MODULE)
    try:
        retained_raw = _read_journal_artifact(
            LOCAL_LAUNCH_ATTEMPT_NAME, MAX_LOCAL_ARTIFACT_BYTES
        )
    except FileNotFoundError:
        retained_raw = None
    control_root = LOCAL_JOURNAL_ROOT / LOCAL_LAUNCH_CONTROL_NAME
    if retained_raw is None:
        try:
            control_raw = runner._read_exact_local_control(  # noqa: SLF001
                control_root / runner.LOCAL_LAUNCH_ATTEMPT_NAME,
                MAX_LOCAL_ARTIFACT_BYTES,
            )
        except FileNotFoundError:
            local = runner.issue_local_launch_attempt_once_v42r1(
                local_control_root=control_root,
                prepare_receipt_raw=prepare_receipt_raw,
            )
            retained_raw = _canonical_json_bytes(local)
        else:
            runner._verify_local_control_inventory(  # noqa: SLF001
                control_root,
                allow_ambiguity=False,
                allow_collection_roots=False,
            )
            retained_raw = control_raw
        _publish_once(LOCAL_LAUNCH_ATTEMPT_NAME, retained_raw)
    local = legacy.verify_local_launch_attempt_v42r1(
        retained_raw, prepare_receipt=prepare_receipt
    )
    if (
        local.get("transport_target_alias")
        != formal_transport_plan["remote_target_alias"]
    ):
        _fail("V42r3 local launch attempt target changed")
    runner._verify_local_control_inventory(  # noqa: SLF001
        control_root,
        allow_ambiguity=False,
        allow_collection_roots=False,
    )
    control_raw = runner._read_exact_local_control(  # noqa: SLF001
        control_root / runner.LOCAL_LAUNCH_ATTEMPT_NAME,
        MAX_LOCAL_ARTIFACT_BYTES,
    )
    if control_raw != retained_raw:
        _fail("V42r3 launch-control and formal-journal attempts differ")
    return local


def _retained_launch_context_v42r3(
    formal_transport_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
    formal = _authority()
    receipt, receipt_raw = _retained_prepare_v42r3(formal_transport_plan)
    legacy = _verified_module(LEGACY_AUTHORITY_MODULE)
    local_raw = _read_journal_artifact(
        LOCAL_LAUNCH_ATTEMPT_NAME, MAX_LOCAL_ARTIFACT_BYTES
    )
    local = legacy.verify_local_launch_attempt_v42r1(
        local_raw, prepare_receipt=receipt
    )
    runner = _verified_module(SCIENTIFIC_RUNNER_MODULE)
    runner._verify_local_control_inventory(  # noqa: SLF001
        LOCAL_JOURNAL_ROOT / LOCAL_LAUNCH_CONTROL_NAME,
        allow_ambiguity=False,
        allow_collection_roots=False,
    )
    control_raw = runner._read_exact_local_control(  # noqa: SLF001
        LOCAL_JOURNAL_ROOT / LOCAL_LAUNCH_CONTROL_NAME
        / runner.LOCAL_LAUNCH_ATTEMPT_NAME,
        MAX_LOCAL_ARTIFACT_BYTES,
    )
    if control_raw != local_raw:
        _fail("retained launch-control attempt differs from formal journal")
    raw = _read_journal_artifact(
        LOCAL_LAUNCH_TRANSPORT_ATTEMPT_NAME,
        MAX_LOCAL_ARTIFACT_BYTES,
    )
    attempt = formal.verify_formal_launch_transport_attempt_v42r3(
        raw,
        formal_transport_plan=formal_transport_plan,
        prepare_receipt=receipt,
        local_launch_attempt=local,
    )
    return receipt, receipt_raw, local, attempt


def _execute_prepare_once_v42r3(
    *, controller_manifest: Mapping[str, Any],
    formal_transport_plan: Mapping[str, Any],
    expected_predecessor_formal_prefix: Mapping[str, Any],
) -> dict[str, Any]:
    formal = _authority()
    plan = formal.verify_formal_transport_plan_v42r3(formal_transport_plan)
    attempt = formal.build_formal_prepare_attempt_v42r3(
        formal_transport_plan=plan
    )
    formal.verify_formal_prepare_attempt_v42r3(
        attempt, formal_transport_plan=plan
    )
    _publish_or_verify(
        LOCAL_PREPARE_ATTEMPT_NAME, _canonical_json_bytes(attempt)
    )
    attempt_id = attempt["formal_prepare_attempt_id"]
    retained = _retained_terminal_outcome_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
    )
    if retained is not None:
        if retained["outcome_class"] == (
            formal.OUTCOME_COMPLETE_EXACT_RECEIPT
        ):
            _retained_prepare_v42r3(plan)
        return retained
    if _effect_cut_present_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
    ):
        return _publish_outcome_v42r3(
            formal_transport_plan=plan,
            operation="PREPARE",
            attempt_id=attempt_id,
            outcome_class=formal.OUTCOME_POST_MARKER_AMBIGUOUS,
            receipt_raw=None,
        )
    ingress = _prepare_ingress_v42r3(plan, attempt)
    transport = _transport_materialization_v42r3(
        mode="--prepare-once-v42r3",
        controller_manifest=controller_manifest,
        ingress=ingress,
        expected_plan_id=plan["formal_transport_plan_id"],
        legacy_execution_source_manifest_id=plan[
            "legacy_execution_source_manifest_id"
        ],
    )
    marker_raw = _canonical_json_bytes(
        formal.build_network_start_v42r3(
            formal_transport_plan=plan,
            operation="PREPARE",
            attempt_id=attempt_id,
        )
    )
    observation, marker, failure = _dispatch_effect_once_v42r3(
        operation="PREPARE",
        attempt_id=attempt_id,
        transport=transport,
        controller_manifest=controller_manifest,
        ingress=ingress,
        formal_transport_plan=plan,
        marker_name=LOCAL_PREPARE_NETWORK_START_NAME,
        marker_raw=marker_raw,
        expected_predecessor_formal_prefix=expected_predecessor_formal_prefix,
        stdout_cap=MAX_LOCAL_ARTIFACT_BYTES,
        timeout_seconds=PREPARE_TIMEOUT_SECONDS,
    )
    receipt = None
    receipt_raw = None
    if failure is None and marker and _observation_closed_exactly(observation):
        assert observation is not None
        try:
            receipt_raw = _strip_canonical_stdout(
                observation.stdout_raw, "V42r3 prepare"
            )
            receipt = _verify_scientific_prepare_receipt(receipt_raw)
            if any(
                receipt[field] != plan[field]
                for field in (
                    "source_commit", "source_tree", "source_manifest_id",
                    "transport_manifest_id",
                )
            ):
                _fail("V42r3 prepare receipt differs from formal plan")
        except BaseException:
            receipt = None
            receipt_raw = None
    if receipt is not None and receipt_raw is not None:
        _publish_or_verify(LOCAL_PREPARE_RECEIPT_NAME, receipt_raw)
        outcome_class = formal.OUTCOME_COMPLETE_EXACT_RECEIPT
    elif marker:
        outcome_class = formal.OUTCOME_POST_MARKER_AMBIGUOUS
    else:
        outcome_class = formal.OUTCOME_PRE_NETWORK_FAILURE
    return _publish_outcome_v42r3(
        formal_transport_plan=plan,
        operation="PREPARE",
        attempt_id=attempt_id,
        outcome_class=outcome_class,
        receipt_raw=receipt_raw,
    )


def _execute_launch_once_v42r3(
    *, controller_manifest: Mapping[str, Any],
    formal_transport_plan: Mapping[str, Any],
    expected_predecessor_formal_prefix: Mapping[str, Any],
) -> dict[str, Any]:
    formal = _authority()
    plan = formal.verify_formal_transport_plan_v42r3(formal_transport_plan)
    receipt, receipt_raw = _retained_prepare_v42r3(plan)
    local = _load_or_issue_local_launch_attempt_v42r3(
        formal_transport_plan=plan,
        prepare_receipt=receipt,
        prepare_receipt_raw=receipt_raw,
    )
    transport_attempt = formal.build_formal_launch_transport_attempt_v42r3(
        formal_transport_plan=plan,
        prepare_receipt=receipt,
        local_launch_attempt=local,
    )
    formal.verify_formal_launch_transport_attempt_v42r3(
        transport_attempt,
        formal_transport_plan=plan,
        prepare_receipt=receipt,
        local_launch_attempt=local,
    )
    _publish_or_verify(
        LOCAL_LAUNCH_TRANSPORT_ATTEMPT_NAME,
        _canonical_json_bytes(transport_attempt),
    )
    attempt_id = local["local_launch_attempt_id"]
    retained = _retained_terminal_outcome_v42r3(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=attempt_id,
    )
    if retained is not None:
        if retained["outcome_class"] == (
            formal.OUTCOME_COMPLETE_EXACT_RECEIPT
        ):
            admission_raw = _read_journal_artifact(
                LOCAL_LAUNCH_ADMISSION_NAME, MAX_LOCAL_ARTIFACT_BYTES
            )
            formal.verify_launch_admission_receipt_v42r3(
                admission_raw,
                formal_transport_plan=plan,
                launch_transport_attempt=transport_attempt,
            )
        return retained
    if _effect_cut_present_v42r3(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=attempt_id,
    ):
        return _publish_outcome_v42r3(
            formal_transport_plan=plan,
            operation="LAUNCH",
            attempt_id=attempt_id,
            outcome_class=formal.OUTCOME_POST_MARKER_AMBIGUOUS,
            receipt_raw=None,
        )
    ingress = _launch_ingress_v42r3(
        plan, receipt, local, transport_attempt
    )
    transport = _transport_materialization_v42r3(
        mode="--admit-launch-v42r3",
        controller_manifest=controller_manifest,
        ingress=ingress,
        expected_plan_id=plan["formal_transport_plan_id"],
        legacy_execution_source_manifest_id=plan[
            "legacy_execution_source_manifest_id"
        ],
    )
    marker_raw = _canonical_json_bytes(
        formal.build_network_start_v42r3(
            formal_transport_plan=plan,
            operation="LAUNCH",
            attempt_id=attempt_id,
        )
    )
    observation, marker, failure = _dispatch_effect_once_v42r3(
        operation="LAUNCH",
        attempt_id=attempt_id,
        transport=transport,
        controller_manifest=controller_manifest,
        ingress=ingress,
        formal_transport_plan=plan,
        marker_name=LOCAL_LAUNCH_NETWORK_START_NAME,
        marker_raw=marker_raw,
        expected_predecessor_formal_prefix=expected_predecessor_formal_prefix,
        stdout_cap=MAX_LOCAL_ARTIFACT_BYTES,
        timeout_seconds=ADMISSION_TIMEOUT_SECONDS,
    )
    admission = None
    admission_raw = None
    if failure is None and marker and _observation_closed_exactly(observation):
        assert observation is not None
        try:
            admission_raw = _strip_canonical_stdout(
                observation.stdout_raw, "V42r3 launch admission"
            )
            admission = formal.verify_launch_admission_receipt_v42r3(
                admission_raw,
                formal_transport_plan=plan,
                launch_transport_attempt=transport_attempt,
            )
        except BaseException:
            admission = None
            admission_raw = None
    if admission is not None and admission_raw is not None:
        _publish_or_verify(LOCAL_LAUNCH_ADMISSION_NAME, admission_raw)
        outcome_class = formal.OUTCOME_COMPLETE_EXACT_RECEIPT
    elif marker:
        outcome_class = formal.OUTCOME_POST_MARKER_AMBIGUOUS
    else:
        outcome_class = formal.OUTCOME_PRE_NETWORK_FAILURE
    return _publish_outcome_v42r3(
        formal_transport_plan=plan,
        operation="LAUNCH",
        attempt_id=attempt_id,
        outcome_class=outcome_class,
        receipt_raw=admission_raw,
    )


def _inspect_and_classify_v42r3(
    *, controller_manifest: Mapping[str, Any],
    formal_transport_plan: Mapping[str, Any],
    operation: str, inspection_ordinal: int,
) -> dict[str, Any]:
    formal = _authority()
    plan = formal.verify_formal_transport_plan_v42r3(formal_transport_plan)
    if operation == "PREPARE":
        attempt = formal.build_formal_prepare_attempt_v42r3(
            formal_transport_plan=plan
        )
        if _read_journal_artifact(
            LOCAL_PREPARE_ATTEMPT_NAME, MAX_LOCAL_ARTIFACT_BYTES
        ) != _canonical_json_bytes(attempt):
            _fail("retained V42r3 prepare attempt changed")
        attempt_id = attempt["formal_prepare_attempt_id"]
        mode = INSPECT_PREPARE_MODE
    elif operation == "LAUNCH":
        _receipt, _raw, local, _transport_attempt = (
            _retained_launch_context_v42r3(plan)
        )
        attempt_id = local["local_launch_attempt_id"]
        mode = INSPECT_LAUNCH_MODE
    else:
        _fail("V42r3 inspection operation changed")
    if not _effect_cut_present_v42r3(
        formal_transport_plan=plan,
        operation=operation,
        attempt_id=attempt_id,
    ):
        _fail("V42r3 read-only inspection requires a retained effect cut")
    ingress = _inspection_ingress_v42r3(
        plan=plan,
        operation=operation,
        attempt_id=attempt_id,
        inspection_ordinal=inspection_ordinal,
    )
    transport = _transport_materialization_v42r3(
        mode=mode,
        controller_manifest=controller_manifest,
        ingress=ingress,
        expected_plan_id=plan["formal_transport_plan_id"],
        legacy_execution_source_manifest_id=plan[
            "legacy_execution_source_manifest_id"
        ],
    )
    observation = _dispatch_read_only_v42r3(
        transport=transport,
        controller_manifest=controller_manifest,
        ingress=ingress,
        stdout_cap=MAX_LOCAL_ARTIFACT_BYTES,
    )
    if not _observation_closed_exactly(observation):
        _fail("V42r3 read-only inspection did not close exactly")
    raw = _strip_canonical_stdout(
        observation.stdout_raw, "V42r3 read-only inspection"
    )
    inspection = formal.verify_read_only_inspection_v42r3(
        raw, formal_transport_plan=plan
    )
    if (
        inspection["operation"] != operation
        or inspection["attempt_id"] != attempt_id
        or inspection["inspection_ordinal"] != inspection_ordinal
    ):
        _fail("V42r3 inspection identity changed")
    _publish_once(
        INSPECTION_PREFIX + operation + f".{inspection_ordinal:08d}.json",
        raw,
    )
    recovered = inspection["recovered_documents"]
    if "scientific_prepare_receipt" in recovered:
        recovered_raw = _canonical_json_bytes(
            recovered["scientific_prepare_receipt"]
        )
        recovered_receipt = _verify_scientific_prepare_receipt(recovered_raw)
        if any(
            recovered_receipt[field] != plan[field]
            for field in (
                "source_commit", "source_tree", "source_manifest_id",
                "transport_manifest_id",
            )
        ):
            _fail("recovered prepare receipt differs from V42r3 plan")
        _publish_or_verify(LOCAL_PREPARE_RECEIPT_NAME, recovered_raw)
    if "launch_admission_receipt" in recovered:
        _receipt, _receipt_raw, _local, transport_attempt = (
            _retained_launch_context_v42r3(plan)
        )
        recovered_raw = _canonical_json_bytes(
            recovered["launch_admission_receipt"]
        )
        formal.verify_launch_admission_receipt_v42r3(
            recovered_raw,
            formal_transport_plan=plan,
            launch_transport_attempt=transport_attempt,
        )
        _publish_or_verify(LOCAL_LAUNCH_ADMISSION_NAME, recovered_raw)
    exact_receipt = True
    try:
        if operation == "PREPARE":
            _retained_prepare_v42r3(plan)
        else:
            _receipt, _receipt_raw, _local, transport_attempt = (
                _retained_launch_context_v42r3(plan)
            )
            admission_raw = _read_journal_artifact(
                LOCAL_LAUNCH_ADMISSION_NAME, MAX_LOCAL_ARTIFACT_BYTES
            )
            formal.verify_launch_admission_receipt_v42r3(
                admission_raw,
                formal_transport_plan=plan,
                launch_transport_attempt=transport_attempt,
            )
    except (FileNotFoundError, V42FormalTransportSuccessorLauncherError):
        exact_receipt = False
    classification = formal.classify_formal_operation_v42r3(
        formal_transport_plan=plan,
        operation=operation,
        attempt_id=attempt_id,
        marker_present=True,
        exact_receipt_present=exact_receipt,
        inspection=inspection,
    )
    _publish_once(
        CLASSIFICATION_PREFIX + operation + f".{inspection_ordinal:08d}.json",
        _canonical_json_bytes(classification),
    )
    return classification


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="native V42r3 formal transport successor launcher"
    )
    parser.add_argument(
        "--predecessor-activation-evidence-root", required=True
    )
    parser.add_argument("--successor-evidence-root", required=True)
    parser.add_argument(
        "--expected-successor-final-evidence-index-id", required=True
    )
    parser.add_argument("--expected-controller-commit", required=True)
    parser.add_argument("--expected-controller-tree", required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-inputs-only", action="store_true")
    modes.add_argument("--probe-host-epoch-v42r3", action="store_true")
    modes.add_argument("--prepare-once-v42r3", action="store_true")
    modes.add_argument("--admit-launch-v42r3", action="store_true")
    modes.add_argument("--inspect-prepare-v42r3", action="store_true")
    modes.add_argument("--inspect-launch-v42r3", action="store_true")
    parser.add_argument("--inspection-ordinal", type=int, default=1)
    return parser


def _summary(
    manifest: Mapping[str, Any],
    verified: Any,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42_formal_transport_successor_input_summary.v42r3",
        "schema_version": "42.3.0",
        "controller_source_manifest_id": manifest[
            "controller_source_manifest_id"
        ],
        "native_activation_binding_id": binding["native_activation_binding_id"],
        "activation_successor_final_evidence_index_id": verified.successor.ids[
            SUCCESSOR_FINAL_FILE
        ],
        "predecessor_formal_effect_may_have_started": verified.predecessor_formal_prefix[
            "predecessor_formal_effect_may_have_started"
        ],
        "formal_admission_claim_scope": (
            "CONDITIONAL_ON_UNATTESTED_EXTERNAL_LOCAL_SSH_AND_REMOTE_PATH_TCB"
        ),
        "external_ingress_assumptions_observed_or_attested": False,
        "remote_path_noninterference_observed_or_attested": False,
        "network_operation_performed": False,
        "local_journal_mutated": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    _require_sealed_stage_materials()
    arguments = _parser().parse_args(argv)
    inspection_mode = (
        arguments.inspect_prepare_v42r3 or arguments.inspect_launch_v42r3
    )
    if inspection_mode:
        if not 1 <= arguments.inspection_ordinal <= 4096:
            _fail("V42r3 inspection ordinal exceeded its fixed range")
    elif arguments.inspection_ordinal != 1:
        _fail("inspection ordinal is accepted only by inspection modes")
    predecessor = _absolute(
        arguments.predecessor_activation_evidence_root,
        "predecessor activation evidence root",
    )
    successor = _absolute(
        arguments.successor_evidence_root, "successor evidence root"
    )
    if predecessor == successor or predecessor.parent != successor.parent:
        _fail("predecessor and successor evidence roots are not distinct siblings")
    if (
        _HEX64.fullmatch(
            arguments.expected_successor_final_evidence_index_id
        )
        is None
    ):
        _fail("expected native successor final ID changed")
    manifest, verified, binding = verify_controller_and_native_inputs_v42r3(
        predecessor_activation_evidence_root=predecessor,
        successor_evidence_root=successor,
        expected_successor_final_evidence_index_id=(
            arguments.expected_successor_final_evidence_index_id
        ),
        expected_controller_commit=arguments.expected_controller_commit,
        expected_controller_tree=arguments.expected_controller_tree,
    )
    exit_code = 0
    if arguments.verify_inputs_only:
        result = _summary(manifest, verified, binding)
    elif arguments.probe_host_epoch_v42r3:
        result = _probe_host_epoch_v42r3(
            controller_manifest=manifest,
            verified_native_inputs=verified,
            native_activation_binding=binding,
        )
    else:
        native_module = _verified_module(NATIVE_DRIVER_MODULE)
        if native_module.verify_failed_v42r1_formal_prefix_read_only() != (
            verified.predecessor_formal_prefix
        ):
            _fail("failed V42r1 formal prefix changed before V42r3 operation")
        _probe_plan, _host_receipt, plan = (
            _build_retained_formal_context_v42r3(
                controller_manifest=manifest,
                native_activation_binding=binding,
                allow_plan_publication=not inspection_mode,
            )
        )
        if arguments.prepare_once_v42r3:
            result = _execute_prepare_once_v42r3(
                controller_manifest=manifest,
                formal_transport_plan=plan,
                expected_predecessor_formal_prefix=(
                    verified.predecessor_formal_prefix
                ),
            )
            if result["outcome_class"] != (
                _authority().OUTCOME_COMPLETE_EXACT_RECEIPT
            ):
                exit_code = 2
        elif arguments.admit_launch_v42r3:
            result = _execute_launch_once_v42r3(
                controller_manifest=manifest,
                formal_transport_plan=plan,
                expected_predecessor_formal_prefix=(
                    verified.predecessor_formal_prefix
                ),
            )
            if result["outcome_class"] != (
                _authority().OUTCOME_COMPLETE_EXACT_RECEIPT
            ):
                exit_code = 2
        elif arguments.inspect_prepare_v42r3:
            result = _inspect_and_classify_v42r3(
                controller_manifest=manifest,
                formal_transport_plan=plan,
                operation="PREPARE",
                inspection_ordinal=arguments.inspection_ordinal,
            )
        else:
            assert arguments.inspect_launch_v42r3
            result = _inspect_and_classify_v42r3(
                controller_manifest=manifest,
                formal_transport_plan=plan,
                operation="LAUNCH",
                inspection_ordinal=arguments.inspection_ordinal,
            )
        if native_module.verify_failed_v42r1_formal_prefix_read_only() != (
            verified.predecessor_formal_prefix
        ):
            _fail("failed V42r1 formal prefix changed across V42r3 operation")
    raw = json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")
    view = memoryview(raw + b"\n")
    while view:
        written = os.write(1, view)
        if written <= 0:
            _fail("V42r3 launcher stdout write made no progress")
        view = view[written:]
    return exit_code


if __name__ == "__main__":
    if dict(os.environ) != EXACT_ENVIRONMENT:
        raise RuntimeError("V42r3 launcher environment changed")
    raise SystemExit(main())
